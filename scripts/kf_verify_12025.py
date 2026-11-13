"""Independent verification of work package wp-12025-01 (acceptance-gate self-check).

Independence discipline:
  * the markdown is re-fetched from the platform API in THIS process (new login) instead of trusting
    runs/wp-12025-01/report_12025.md from the producer run;
  * the sha256 is recomputed from scratch and compared both to the contract literal and to the hash
    recorded in the manifest;
  * every locator is re-resolved by slicing the freshly fetched text at (start_char, end_char) — a
    locator passes only if the slice equals locator.quote AND quote occurs exactly once in the source;
  * nothing here writes back into the manifest (verification is read-only w.r.t. the product).

Checks = the contract's acceptance list, no more, no less:
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
Extras (reported separately, do not gate): result-envelope schema, single-json-block discipline of the
KF-RESULT markdown, "no verified marker" discipline, counts consistency.

Outputs: artifacts/wp-12025-01/verification.json ; PASS/FAIL per check on stdout;
exit code 0 iff every gating check passes and no check is left unknown.

Usage: python3 scripts/kf_verify_12025.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

import jsonschema

REPORT_ID = "12025"
PACKAGE_ID = "wp-12025-01"
EXPECTED_HASH = "6ebcceb70d4aa23bd429e13496cfa2ac2fc933c83461eef0a0c58a29321df0ed"
SOURCE_URI = "tensor://reports/12025"

MANIFEST = pathlib.Path("artifacts/wp-12025-01/asset_manifest.json")
SCHEMA = pathlib.Path("schemas/asset_manifest.v2.schema.json")
SCHEMA_V1 = pathlib.Path("schemas/asset_manifest.v1.schema.json")
ENVELOPE_SCHEMA = pathlib.Path("schemas/kf_result.v1.schema.json")
RESULT = pathlib.Path(f"runs/wp-12025-01/kf_result.{PACKAGE_ID}.json")
BLOCK = pathlib.Path(f"runs/wp-12025-01/kf_result_block.{PACKAGE_ID}.json")
KFRESULT_MD = pathlib.Path(f"docs/wp-12025-01/KF-RESULT-{PACKAGE_ID}.md")
OUT = pathlib.Path("artifacts/wp-12025-01/verification.json")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        req = urllib.request.Request(BASE + path,
                                     data=json.dumps({"username": u, "password": p}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token")
        if tok:
            return tok
    return None


def fetch_markdown() -> tuple[str, dict]:
    tok = login()
    req = urllib.request.Request(f"{BASE}/tensor/reports/{REPORT_ID}",
                                 headers={"Authorization": "Bearer " + tok} if tok else {})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    return d["markdown"], d


def main() -> int:
    checks: dict[str, dict] = {}

    def record(name, ok, **detail):
        checks[name] = dict(status="PASS" if ok else "FAIL", **detail)

    # ---- load artefacts ---------------------------------------------------
    try:
        manifest = json.loads(MANIFEST.read_text())
        record("valid_json", True, path=str(MANIFEST))
    except Exception as exc:
        record("valid_json", False, error=str(exc))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"checks": checks}, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(checks, ensure_ascii=False, indent=2))
        return 1

    rev = json.loads(ENVELOPE_SCHEMA.read_text())["properties"]["provenance"]
    record("valid_json_envelope", isinstance(rev, dict))

    # ---- independent source fetch ----------------------------------------
    md, payload = fetch_markdown()
    md_hash = hashlib.sha256(md.encode()).hexdigest()

    # ---- source_hash_matches ---------------------------------------------
    contract_ok = md_hash == EXPECTED_HASH
    manifest_ok = md_hash == manifest["source"]["hash"]
    envelope = json.loads(RESULT.read_text())
    env_ok = envelope["provenance"]["source_hash"] == "sha256:" + md_hash
    record("source_hash_matches", contract_ok and manifest_ok and env_ok,
           recomputed="sha256:" + md_hash, contract="sha256:" + EXPECTED_HASH,
           manifest=manifest["source"]["hash"], envelope=envelope["provenance"]["source_hash"],
           method="re-fetched in this process; hash recomputed from the fetched bytes")

    # ---- schema_pass ------------------------------------------------------
    schema = json.loads(SCHEMA.read_text())
    errs = sorted(jsonschema.Draft7Validator(schema).iter_errors(manifest), key=lambda e: list(e.path))
    v1 = json.loads(SCHEMA_V1.read_text())
    v1_errs = sorted(jsonschema.Draft7Validator(v1).iter_errors(manifest), key=lambda e: list(e.path))
    record("schema_pass", not errs, schema=str(SCHEMA),
           errors=[f"{list(e.path)}: {e.message}" for e in errs],
           note_v1=(f"v1 (const report_id=448) rejects this package with {len(v1_errs)} error(s): "
                    + "; ".join(e.message for e in v1_errs[:3])) if v1_errs else "v1 also passes")

    # ---- source_locator_resolvable ---------------------------------------
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        slice_ok = 0 <= s < e <= len(md) and md[s:e] == loc["quote"]
        uniq = md.count(loc["quote"]) == 1
        lines = md.split("\n")
        # start_line/end_line must agree with the char offsets (1 extra guard, cheap)
        line_ok = md[:s].count("\n") == loc["start_line"] and md[:e].count("\n") in (
            loc["end_line"], loc["end_line"] + 1)
        if not (slice_ok and uniq and line_ok and loc["unique"]):
            bad.append(dict(asset_id=a["asset_id"], slice_ok=slice_ok, unique=uniq,
                            line_ok=line_ok, declared_unique=loc["unique"]))
    record("source_locator_resolvable", not bad, assets=len(manifest["assets"]),
           resolved=len(manifest["assets"]) - len(bad), failures=bad)

    # ---- no_duplicate_ids -------------------------------------------------
    ids = [a["asset_id"] for a in manifest["assets"]]
    claims_ids = [c.get("claim_id") for c in manifest.get("claims", [])]
    dup_assets = sorted({i for i in ids if ids.count(i) > 1})
    dup_claims = sorted({i for i in claims_ids if claims_ids.count(i) > 1})
    overlap = sorted(set(ids) & set(claims_ids))
    record("no_duplicate_ids", not (dup_assets or dup_claims or overlap),
           asset_ids=len(ids), duplicate_assets=dup_assets, duplicate_claims=dup_claims,
           asset_claim_overlap=overlap)

    # ---- all_claims_have_evidence_or_explicit_unresolved_status ----------
    claims = manifest.get("claims", [])
    unresolved_claims = [c for c in claims
                         if not (c.get("evidence_locator") or c.get("status") or c.get("evidence"))]
    record("all_claims_have_evidence_or_explicit_unresolved_status", not unresolved_claims,
           claims=len(claims), naked_claims=[c.get("claim_id") for c in unresolved_claims],
           note=("empty claims array (task_type=01 does no extraction) => condition holds vacuously; "
                 "reported as PASS not as evidence of claim quality"))

    # ---- extras (non-gating) ---------------------------------------------
    env_errs = sorted(jsonschema.Draft7Validator(json.loads(ENVELOPE_SCHEMA.read_text())).iter_errors(envelope),
                      key=lambda e: list(e.path))
    checks["extra_result_envelope_schema"] = dict(
        status="PASS" if not env_errs else "FAIL",
        errors=[f"{list(e.path)}: {e.message}" for e in env_errs],
        provenance_has=[k for k in ("source_uri", "source_field", "source_hash") if k in envelope["provenance"]])

    block = json.loads(BLOCK.read_text())
    checks["extra_block_equals_envelope"] = dict(
        status="PASS" if block == envelope else "FAIL",
        note="single json-fence block content must be the envelope verbatim")

    # "do not mark claims as verified" discipline: no verified flags anywhere in the product
    blob = MANIFEST.read_text()
    verified_hits = re.findall(r'"(verified|verification|claim_status)"\s*:', blob)
    env_verif = envelope["provenance"].get("verification_status")
    checks["extra_no_verified_marker"] = dict(
        status="PASS" if (not verified_hits and env_verif == "not_verified") else "FAIL",
        forbidden_keys_found=verified_hits, provenance_verification_status=env_verif,
        note="producer does not label anything verified; gate computes verification")

    # counts consistency
    m = manifest
    counts_ok = (m["counts"]["assets"] == len(m["assets"])
                 and m["counts"]["resolved_in_source"] + m["counts"]["referenced_unresolved"]
                 + m["counts"]["declared_absent"] == len(m["assets"]))
    checks["extra_counts_consistent"] = dict(status="PASS" if counts_ok else "FAIL",
                                             counts=m["counts"], assets=len(m["assets"]))

    # research-report block discipline (docs md): exactly one ```json fence, title/tag right
    if KFRESULT_MD.exists():
        txt = KFRESULT_MD.read_text()
        fences = txt.count("```json")
        title_ok = txt.lstrip().split("\n", 1)[0].startswith(f"# KF-RESULT {PACKAGE_ID}") or \
            f"KF-RESULT {PACKAGE_ID}" in txt.split("\n")[0]
        checks["extra_kfresult_md_single_json_block"] = dict(
            status="PASS" if (fences == 1 and title_ok) else "FAIL", json_fences=fences,
            title_ok=title_ok, path=str(KFRESULT_MD))
    else:
        checks["extra_kfresult_md_single_json_block"] = dict(
            status="not_run", reason=f"{KFRESULT_MD} not built yet (scripts/kf_report_12025.py)")

    # ---- summary ---------------------------------------------------------
    gating = ["valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
              "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"]
    all_pass = all(checks[k]["status"] == "PASS" for k in gating)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(
        package_id=PACKAGE_ID, report_id=REPORT_ID, source_hash="sha256:" + md_hash,
        source_chars=len(md), gating=gating, checks=checks,
        verdict="PASS" if all_pass else "FAIL",
    ), ensure_ascii=False, indent=2) + "\n")

    for k in gating:
        print(f"{checks[k]['status']:4s} {k}")
    for k in checks:
        if k.startswith("extra_"):
            print(f"{checks[k]['status']:9s} {k}")
    print("verdict:", "PASS" if all_pass else "FAIL", "->", OUT)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())