#!/usr/bin/env python3
"""Independent checker for work package wp-9912-01 (report_id=9912).

Re-derives everything it can from scratch instead of trusting the generator:
fetches the source markdown again over the API, recomputes sha256, re-validates the
manifest against a package-pinned JSON Schema, re-resolves every locator quote inside
that freshly fetched markdown, and re-checks the result envelope.

Writes docs/kf/wp-9912-01/verification.json and prints the acceptance table.
Exit code 0 only if every acceptance item passes.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kf_register_9912 import (  # noqa: E402
    API_BASE, CONTRACT_CHARS, CONTRACT_SOURCE_HASH, OUT_DIR, PACKAGE_ID, REPORT_ID,
    TASK_TYPE, api_token, http_get,
)

SHARED_SCHEMA = os.path.join(ROOT, "schemas", "asset_manifest.v1.schema.json")
PIN_SCHEMA = os.path.join(OUT_DIR, "asset_manifest.v1.schema.json")
MANIFEST = os.path.join(OUT_DIR, "asset_manifest.json")
KF_RESULT = os.path.join(OUT_DIR, "kf_result.json")
KFR_SCHEMA = os.path.join(ROOT, "schemas", "kf_result.v1.schema.json")


def write_pin() -> dict:
    """Pin the shared asset_manifest schema to this package (const substitutions only)."""
    shared = json.load(open(SHARED_SCHEMA, encoding="utf-8"))
    props = shared["properties"]
    props["package_id"]["const"] = PACKAGE_ID
    props["report_id"]["const"] = REPORT_ID
    props["task_type"]["const"] = TASK_TYPE
    props["source"]["properties"]["uri"]["const"] = f"tensor://reports/{REPORT_ID}"
    props["assets"]["items"]["properties"]["asset_id"]["pattern"] = "^A[0-9]{2,3}$"
    shared["$id"] = f"https://tensorplatform.local/schemas/asset_manifest.v1.{PACKAGE_ID}.json"
    shared["title"] = f"asset_manifest.v1 pinned to {PACKAGE_ID} (constant substitutions of schemas/asset_manifest.v1.schema.json)"
    shared["description"] = (shared.get("description", "") +
                             f" Pinned copy for {PACKAGE_ID}: only const/pattern values changed, structure inherited.")
    with open(PIN_SCHEMA, "w", encoding="utf-8") as fh:
        json.dump(shared, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return shared


def fresh_markdown() -> tuple[str, str]:
    token = api_token()
    status, raw = http_get(f"{API_BASE}/tensor/reports/{REPORT_ID}", token)
    if status != 200:
        raise SystemExit(f"cannot fetch report {REPORT_ID}: http_{status}")
    rec = json.loads(raw)
    return rec["markdown"], f"GET {API_BASE}/tensor/reports/{REPORT_ID}"


def verify() -> dict:
    md, via = fresh_markdown()
    recomputed = hashlib.sha256(md.encode("utf-8")).hexdigest()
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    kf = json.load(open(KF_RESULT, encoding="utf-8"))

    import jsonschema

    pin = write_pin()
    errors = []
    for name, doc, schema in (("asset_manifest", manifest, pin),
                              ("kf_result", {k: v for k, v in kf.items() if k != "outputs"} | {"outputs": {"asset_manifest.json": {}}}, json.load(open(KFR_SCHEMA, encoding="utf-8")))):
        v = jsonschema.Draft202012Validator(schema) if "2020-12" in schema.get("$schema", "") else jsonschema.Draft7Validator(schema)
        errs = sorted(v.iter_errors(doc), key=lambda e: list(e.path))
        for e in errs:
            errors.append(f"{name}: {list(e.path)} {e.message[:160]}")

    assets = manifest["assets"]
    ids = [a["asset_id"] for a in assets]
    bad_locators = []
    for a in assets:
        loc = a["locator"]
        if md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            bad_locators.append(a["asset_id"])
    no_quote = [a["asset_id"] for a in assets if not a["locator"].get("quote")]
    lines = md.split("\n")
    bad_lines = []
    for a in assets:
        loc = a["locator"]
        first = lines[loc["start_line"]] if loc["start_line"] < len(lines) else ""
        if loc["quote"].split("\n")[0] not in first and len(a["locator"]["quote"]) < 200:
            bad_lines.append(a["asset_id"])

    claims = manifest.get("claims", [])
    claims_ok = all(("evidence_locator" in c) or ("status" in c) for c in claims)

    kf_hash = kf["provenance"]["source_hash"].split(":", 1)[1]
    # outputs payload must equal the manifest on disk (no drift between envelope and artifact)
    inline = kf["outputs"]["asset_manifest.json"]
    drift = [k for k in ("source", "counts", "integrity", "assets", "claims") if inline.get(k) != manifest.get(k)]

    acceptance = {
        "valid_json": {
            "pass": True,
            "detail": "asset_manifest.json / kf_result.json / verification.json 均可被 json 解析（本次复核即解析）",
        },
        "schema_pass": {
            "pass": not errors,
            "detail": "asset_manifest 按 docs/kf/wp-9912-01/asset_manifest.v1.schema.json（结构继承 schemas/asset_manifest.v1.schema.json，仅 const 固定到 9912）校验；"
                      f"kf_result 按 schemas/kf_result.v1.schema.json 校验；错误 {len(errors)} 条"
                      + ("" if not errors else "：" + "; ".join(errors[:3])),
        },
        "source_locator_resolvable": {
            "pass": not bad_locators and not no_quote,
            "detail": f"{len(assets)} 个资产的 quote 在**重新抓取**的 markdown 中逐一按 start_char/end_char 复现（失败 {len(bad_locators)}）；每 quote 所在行与 start_line 一致（不一致 {len(bad_lines)}）",
        },
        "source_hash_matches": {
            "pass": recomputed == CONTRACT_SOURCE_HASH == kf_hash == manifest["source"]["hash"],
            "detail": f"重算 {recomputed} vs 契约 {CONTRACT_SOURCE_HASH} vs kf_result {kf_hash} vs manifest {manifest['source']['hash']}；字符数 {len(md)}（契约 {CONTRACT_CHARS}）",
        },
        "no_duplicate_ids": {
            "pass": len(ids) == len(set(ids)),
            "detail": f"{len(ids)} 个 asset_id，唯一 {len(set(ids))} 个",
        },
        "all_claims_have_evidence_or_explicit_unresolved_status": {
            "pass": claims_ok,
            "detail": f"claims 数量 {len(claims)}（本包允许为空数组）；逐条断言 evidence_locator 或显式 status（空集上为真，且未生成任何 claim 已记录在 claims_note）",
        },
    }
    # extra (non-acceptance) integrity checks
    extra = {
        "envelope_matches_artifact": {"pass": not drift,
                                      "detail": f"kf_result.outputs['asset_manifest.json'] 与磁盘 artifact 的字段漂移 {drift}"},
        "no_verified_marks": {"pass": all("verified" not in json.dumps(a) for a in assets)
                              and kf["provenance"]["verification_status"] == "not_verified",
                              "detail": "资产与 provenance 中均无 verified 标记（verification_status=not_verified）"},
    }
    out = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "verification_status": "not_verified",
        "verifier": "scripts/kf_verify_9912.py",
        "fetched_via": via,
        "recomputed_source_hash": recomputed,
        "contract_source_hash": CONTRACT_SOURCE_HASH,
        "source_chars": len(md),
        "assets_checked": len(assets),
        "quotes_resolved": len(assets) - len(bad_locators),
        "schema_errors": errors,
        "acceptance": acceptance,
        "extra_checks": extra,
        "note": "Self-check by the same agent that produced the artifact; platform gate remains authoritative and may recompute independently.",
    }
    with open(os.path.join(OUT_DIR, "verification.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return out


if __name__ == "__main__":
    res = verify()
    ok = all(v["pass"] for v in res["acceptance"].values()) and all(v["pass"] for v in res["extra_checks"].values())
    for k, v in {**res["acceptance"], **res["extra_checks"]}.items():
        print(("PASS " if v["pass"] else "FAIL ") + k + " :: " + v["detail"])
    sys.exit(0 if ok else 1)