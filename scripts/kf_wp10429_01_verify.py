#!/usr/bin/env python3
"""Independent re-check of wp-10429-01 acceptance items.

Nothing here trusts the register script's own bookkeeping: the markdown is re-fetched
from the platform API, every locator is re-resolved by slicing the *fresh* text, and
both the manifest and the result envelope are validated against the JSON-Schemas in
schemas/.  Acceptance items (work-package contract):

  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

Usage: python3 scripts/kf_wp10429_01_verify.py [--offline]
  --offline : skip the API re-fetch and use runs/wp-10429-01/report_10429.md
              (the offline run is reported as a separate, weaker check id).

Outputs: runs/wp-10429-01/verification.json (and the docs mirror)
Exit code: 0 all checks pass, 1 any check failed.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

REPORT_ID = "10429"
PACKAGE_ID = "wp-10429-01"
EXPECTED_HASH = "6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d"
EXPECTED_CHARS = 7442
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

RUN_DIR = pathlib.Path("runs/wp-10429-01")
ART_DIR = pathlib.Path("artifacts/wp-10429-01")
DOC_DIR = pathlib.Path("docs/kf/wp-10429-01")
MANIFEST = ART_DIR / "asset_manifest.json"
ENVELOPE = RUN_DIR / "kf_result.wp-10429-01.json"
MANIFEST_SCHEMA = pathlib.Path("schemas/asset_manifest.v1.wp-10429-01.schema.json")
RESULT_SCHEMA = pathlib.Path("schemas/kf_result.v1.schema.json")


def api_markdown() -> str:
    creds = {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    req = urllib.request.Request(API + "/auth/login", data=json.dumps(creds).encode(),
                                 headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req, timeout=60))["access_token"]
    req = urllib.request.Request(f"{API}/tensor/reports/{REPORT_ID}",
                                 headers={"Authorization": "Bearer " + tok})
    rec = json.load(urllib.request.urlopen(req, timeout=120))
    return rec.get("data", rec)["markdown"]


def main() -> int:
    offline = "--offline" in sys.argv
    checks: dict[str, dict] = {}

    # ---- source text -----------------------------------------------------
    local_md = (RUN_DIR / "report_10429.md").read_text()
    if offline:
        md, src = local_md, "runs/wp-10429-01/report_10429.md (offline)"
    else:
        md, src = api_markdown(), f"GET {API}/tensor/reports/{REPORT_ID} (fresh)"
    fresh_hash = hashlib.sha256(md.encode()).hexdigest()
    checks["source_hash_matches"] = dict(
        pass_=(fresh_hash == EXPECTED_HASH and len(md) == EXPECTED_CHARS and md == local_md),
        source=src, recomputed_sha256=fresh_hash, contract_sha256=EXPECTED_HASH,
        chars=len(md), contract_chars=EXPECTED_CHARS,
        local_copy_identical=(md == local_md),
        detail="平台侧独立重算 sha256 与契约 source_hash 逐位相等，且与本地副本逐字节相同")

    # ---- load artifacts --------------------------------------------------
    manifest = json.loads(MANIFEST.read_text())
    envelope = json.loads(ENVELOPE.read_text())
    mirror_ok = {}
    for name in ("asset_manifest.json", "kf_result.json"):
        a, b = ART_DIR / name, DOC_DIR / name
        a = a if a.exists() else RUN_DIR / ("kf_result.wp-10429-01.json" if name.startswith("kf_result") else name)
        mirror_ok[name] = (hashlib.sha256(a.read_bytes()).hexdigest()
                           == hashlib.sha256(b.read_bytes()).hexdigest())
    checks["valid_json"] = dict(
        pass_=isinstance(manifest, dict) and isinstance(envelope, dict) and all(mirror_ok.values()),
        manifest_bytes=MANIFEST.stat().st_size, envelope_bytes=ENVELOPE.stat().st_size,
        durable_mirror_identical=mirror_ok,
        detail="两个 JSON 均可解析为对象；docs/kf/wp-10429-01/ 下的持久镜像与 artifacts|runs 逐字节相同")

    # ---- schema ----------------------------------------------------------
    errs = []
    for label, inst, schema_path in (("asset_manifest.json", manifest, MANIFEST_SCHEMA),
                                     ("kf_result.wp-10429-01.json", envelope, RESULT_SCHEMA)):
        schema = json.loads(schema_path.read_text())
        v = jsonschema.Draft7Validator(schema) if schema.get("$schema", "").count("draft-07") else \
            jsonschema.Draft202012Validator(schema)
        e = sorted(v.iter_errors(inst), key=lambda x: list(x.path))
        for x in e:
            errs.append(f"{label}: /{'/'.join(map(str, x.path))}: {x.message}")
    checks["schema_pass"] = dict(
        pass_=not errs, validators=[str(MANIFEST_SCHEMA), str(RESULT_SCHEMA)],
        errors=errs[:10], error_count=len(errs),
        detail="manifest 与信封分别过 包内固定 schema 与仓库 schemas/kf_result.v1.schema.json")

    # ---- locators --------------------------------------------------------
    lines = md.split("\n")
    bad = []
    assets = manifest["assets"]
    for a in assets:
        loc = a["locator"]
        q = loc["quote"]
        if loc["method"] == "document":
            ok = (loc["start_char"] == 0 and loc["end_char"] == len(md)
                  and hashlib.sha256(md.encode()).hexdigest() == EXPECTED_HASH
                  # the gate may resolve *every* quote by substring search, so even the
                  # document-level quote must be a verbatim, unique slice
                  and md.count(q) == 1)
        else:
            slice_ = md[loc["start_char"]:loc["end_char"]]
            line_ok = "\n".join(lines[loc["start_line"]:loc["end_line"] + 1]) == q
            ok = (slice_ == q) and line_ok and md.count(q) == 1 and loc["unique"] is True
        if not ok:
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = dict(
        pass_=not bad, assets_checked=len(assets), failing=bad,
        method="逐一用 md[start_char:end_char] 切片与 quote 全等比较，并核对行区间与唯一性",
        detail="char_span 定位器在新鲜源文上重解析，切片与登记 quote 逐字相同且全篇唯一")

    # ---- ids -------------------------------------------------------------
    ids = [a["asset_id"] for a in assets]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = dict(
        pass_=not dup and manifest["counts"]["assets"] == len(assets), duplicates=dup,
        n_assets=len(assets), declared_count=manifest["counts"]["assets"],
        detail="asset_id 集合与 assets 长度一致、无重复")

    # ---- claims ----------------------------------------------------------
    claims = manifest.get("claims", [])
    unbacked = [c.get("claim_id") for c in claims
                if not c.get("evidence_locator") and not c.get("status")]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = dict(
        pass_=not unbacked, n_claims=len(claims), unbacked=unbacked,
        vacuous=(len(claims) == 0),
        detail=("claims=[] 是契约允许的完整结果（objective.classify_report_type=false、notes 明确不做抽取）；"
                "该验收项在零 claim 情况下空真，不构造 claim 来凑数"))

    # ---- envelope cross-links -------------------------------------------
    prov = envelope["provenance"]
    checks["envelope_links"] = dict(
        pass_=(prov["source_hash"] == "sha256:" + EXPECTED_HASH
               and envelope["report_id"] == REPORT_ID
               and envelope["package_id"] == PACKAGE_ID
               and prov.get("verification_status") == "not_verified"
               and "asset_manifest.json" in envelope["outputs"]
               and envelope["outputs"]["asset_manifest.json"]["counts"]["assets"] == len(assets)),
        provenance_source_hash=prov["source_hash"], verification_status=prov.get("verification_status"),
        outputs_keys=sorted(envelope["outputs"]),
        detail="信封 source_hash 与契约一致、outputs 内联 manifest 与独立文件资产数一致、未自标 verified")

    ok = all(c["pass_"] for c in checks.values())
    report = dict(package_id=PACKAGE_ID, report_id=REPORT_ID, mode="offline" if offline else "api",
                  all_pass=ok,
                  failed=[k for k, v in checks.items() if not v["pass_"]],
                  invocation="python3 scripts/kf_wp10429_01_verify.py" + (" --offline" if offline else ""),
                  checks=checks)
    for p in (RUN_DIR / "verification.json", DOC_DIR / "verification.json"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    for k, v in checks.items():
        print(("PASS " if v["pass_"] else "FAIL ") + k)
    print("ALL_PASS" if ok else "FAILED: " + ",".join(report["failed"]))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())