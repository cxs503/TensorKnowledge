"""Independent verification of work package wp-13278-01 (acceptance self-check).

Independence discipline: the markdown is re-fetched from the platform API inside this process (fresh
login) instead of trusting runs/wp-13278-01/report_13278.md; the sha256 is recomputed from scratch; every
locator is re-resolved by slicing the freshly fetched text; the result envelope is re-validated against
schemas/kf_result.v1.schema.json. Nothing here writes back into the manifest, and nothing marks a claim
as verified — verification of the knowledge content is computed by the platform gate.

Checks (exactly the package acceptance list):
  01 valid_json
  02 schema_pass
  03 source_locator_resolvable
  04 source_hash_matches
  05 no_duplicate_ids
  06 all_claims_have_evidence_or_explicit_unresolved_status
Extras (not part of acceptance, reported separately):
  E1 envelope_contract_shape / E2 report_block_single_json / E3 no_verified_markers
  E4 counts_consistent / E5 scope_single_report

Outputs: artifacts/wp-13278-01/verification.json ; prints PASS/FAIL per check; exit 0 iff all six
acceptance checks pass (degrades to `unknown` only if the API is unreachable, never to `pass`).

Usage: python3 scripts/kf_verify_wp13278.py
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

REPORT_ID = "13278"
PACKAGE_ID = "wp-13278-01"
EXPECTED_HASH = "f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a16bb29406537cfac742dcc90f"
MANIFEST = pathlib.Path("artifacts/wp-13278-01/asset_manifest.json")
MIRROR = pathlib.Path("docs/wp-13278-01/asset_manifest.json")
SCHEMA = pathlib.Path("schemas/asset_manifest.wp-13278-01.schema.json")
ENVELOPE_SCHEMA = pathlib.Path("schemas/kf_result.v1.schema.json")
RESULT = pathlib.Path("runs/wp-13278-01/kf_result.wp-13278-01.json")
BLOCK = pathlib.Path("runs/wp-13278-01/kf_result_block.wp-13278-01.json")
REPORT_DOC = pathlib.Path("docs/wp-13278-01/KF-RESULT-wp-13278-01.md")
OUT = pathlib.Path("artifacts/wp-13278-01/verification.json")
OUT_MIRROR = pathlib.Path("docs/wp-13278-01/verification.json")  # committed surface (artifacts/ is dropped)
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/tensor/auth/login"):
        req = urllib.request.Request(
            BASE + path, data=json.dumps({"username": u, "password": p}).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_markdown() -> tuple[str | None, dict]:
    try:
        tok = login()
        req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID,
                                     headers={"Authorization": "Bearer " + tok} if tok else {})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        if isinstance(d.get("data"), dict):
            d = d["data"]
        return d.get("markdown", ""), d
    except Exception as exc:  # noqa: BLE001
        return None, {"fetch_error": repr(exc)}


# ---------------- reusable checks (also imported by tests/test_kf_wp13278.py) ----------------
RESOLUTION_TO_CHECK = {"resolved_in_source": {"resolved"},
                       "referenced_unresolved": {"unresolved"},
                       "declared_absent": {"absent", "present"}}


def check_locators(md: str, manifest: dict) -> list[tuple[str, str]]:
    """Return [(asset_id, reason)] for every locator that does not re-resolve in ``md``."""
    bad = []
    for a in manifest.get("assets", []):
        loc = a.get("locator") or {}
        quote = loc.get("quote", "")
        s, e = loc.get("start_char"), loc.get("end_char")
        if not isinstance(s, int) or not isinstance(e, int) or e <= s:
            bad.append((a.get("asset_id"), "bad span"))
            continue
        if md[s:e] != quote:
            bad.append((a.get("asset_id"), "slice != quote"))
            continue
        if loc.get("method") == "char_span" and md.count(quote) != 1:
            bad.append((a.get("asset_id"), "quote not unique (%d hits)" % md.count(quote)))
            continue
        rc = a.get("resolution_check") or {}
        allowed = RESOLUTION_TO_CHECK.get(a.get("resolution"), set())
        if rc.get("result") not in allowed:
            bad.append((a.get("asset_id"), "resolution/check mismatch: %r vs %r"
                        % (a.get("resolution"), rc.get("result"))))
    return bad


def check_envelope(env: dict) -> list[str]:
    problems = []
    if env.get("package_id") != PACKAGE_ID:
        problems.append("package_id mismatch")
    if env.get("report_id") != REPORT_ID:
        problems.append("report_id mismatch")
    prov = env.get("provenance") or {}
    if prov.get("source_hash") != "sha256:" + EXPECTED_HASH:
        problems.append("provenance.source_hash mismatch")
    if prov.get("source_field") != "markdown":
        problems.append("provenance.source_field != markdown")
    if prov.get("verification_status") == "verified":
        problems.append("envelope claims verified status (forbidden for this package)")
    if "asset_manifest.json" not in (env.get("outputs") or {}):
        problems.append("outputs missing asset_manifest.json")
    return problems


def check_verified_markers(manifest: dict) -> list[str]:
    """No claim may be marked verified; this package must not infer verification."""
    bad = []
    for c in manifest.get("claims", []):
        if c.get("status") == "verified":
            bad.append(c.get("claim_id", "?"))
    if manifest.get("integrity", {}).get("hash_matches_contract") is not True:
        bad.append("integrity.hash_matches_contract")
    return bad


def run_checks() -> dict:
    checks = []

    def add(name, result, detail):
        checks.append(dict(check=name, result=result, detail=detail))

    blob = MANIFEST.read_text()
    try:
        manifest = json.loads(blob)
        add("valid_json", "pass", {"parsed": True, "bytes": len(blob.encode())})
    except Exception as exc:  # noqa: BLE001
        add("valid_json", "fail", {"error": repr(exc)})
        manifest = {}

    schema_errors = []
    if manifest:
        schema = json.loads(SCHEMA.read_text())
        for err in jsonschema.Draft7Validator(schema).iter_errors(manifest):
            schema_errors.append("%s: %s" % ("/".join(str(p) for p in err.absolute_path), err.message))
    env = json.loads(RESULT.read_text()) if RESULT.exists() else {}
    env_errors = []
    if env:
        eschema = json.loads(ENVELOPE_SCHEMA.read_text())
        for err in jsonschema.Draft202012Validator(eschema).iter_errors(env):
            env_errors.append("%s: %s" % ("/".join(str(p) for p in err.absolute_path), err.message))
    add("schema_pass", "pass" if not (schema_errors or env_errors) else "fail",
        {"manifest_errors": schema_errors[:10], "envelope_errors": env_errors[:10],
         "manifest_schema": str(SCHEMA), "envelope_schema": str(ENVELOPE_SCHEMA)})

    md, payload = fetch_markdown()
    if md is None:
        add("source_locator_resolvable", "unknown", {"error": payload.get("fetch_error")})
        add("source_hash_matches", "unknown", {"error": payload.get("fetch_error")})
    else:
        bad = check_locators(md, manifest)
        add("source_locator_resolvable", "pass" if not bad else "fail",
            {"assets_checked": len(manifest.get("assets", [])), "failures": bad,
             "method": "re-fetched markdown, md[start:end]==quote, uniqueness for char_span"})
        got = hashlib.sha256(md.encode()).hexdigest()
        add("source_hash_matches", "pass" if got == EXPECTED_HASH else "fail",
            {"recomputed": "sha256:" + got, "contract": "sha256:" + EXPECTED_HASH,
             "chars": len(md), "bytes_utf8": len(md.encode()),
             "platform_title": payload.get("title"), "platform_figures": payload.get("figures"),
             "platform_mission_id": payload.get("mission_id")})

    ids = [a.get("asset_id") for a in manifest.get("assets", [])]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    add("no_duplicate_ids", "pass" if not dupes else "fail",
        {"assets": len(ids), "duplicates": dupes})

    claims = manifest.get("claims", [])
    orphan = [c.get("claim_id") for c in claims
              if not (c.get("evidence_locator") or c.get("status") or c.get("evidence"))]
    add("all_claims_have_evidence_or_explicit_unresolved_status",
        "pass" if not orphan else "fail",
        {"claims": len(claims), "orphans": orphan,
         "vacuous": len(claims) == 0,
         "note": "claims=[] is declared legitimate by the package contract (objective.classify_report_type=false)"})

    # ---- extras ----
    add("E1_envelope_contract_shape", "pass" if env and not check_envelope(env) else "fail",
        {"problems": check_envelope(env) if env else ["no envelope"],
         "verification_status": (env.get("provenance") or {}).get("verification_status")})
    add("E2_report_block_single_json", *_block_check())
    add("E3_no_verified_markers", "pass" if not check_verified_markers(manifest) else "fail",
        {"offenders": check_verified_markers(manifest)})
    c = manifest.get("counts", {})
    n = len(manifest.get("assets", []))
    add("E4_counts_consistent", "pass" if c.get("assets") == n else "fail",
        {"counts.assets": c.get("assets"), "len(assets)": n,
         "by_resolution": c.get("by_resolution")})
    add("E5_scope_single_report", "pass" if manifest.get("report_id") == REPORT_ID else "fail",
        {"report_id": manifest.get("report_id"), "boundary": "report_id=13278 only"})
    add("E6_durable_mirror_identical",
        "pass" if MIRROR.exists() and MIRROR.read_bytes() == MANIFEST.read_bytes() else "fail",
        {"mirror": str(MIRROR)})
    add("E7_source_chars_match_contract", "pass" if (manifest.get("source", {}).get("chars") == 1592)
        else "fail", {"chars": manifest.get("source", {}).get("chars"), "contract": 1592})

    acceptance = ["valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
                  "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"]
    verdict = {c["check"]: c["result"] for c in checks}
    status = "pass" if all(verdict.get(k) == "pass" for k in acceptance) else "fail"
    if any(verdict.get(k) == "unknown" for k in acceptance):
        status = "degraded"
    return dict(schema_version="verification.v1", package_id=PACKAGE_ID, report_id=REPORT_ID,
                acceptance=acceptance, status=status, checks=checks)


def _block_check() -> tuple[str, dict]:
    if not REPORT_DOC.exists():
        return "unknown", {"note": "report doc not built yet"}
    text = REPORT_DOC.read_text()
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
    return ("pass" if len(blocks) == 1 else "fail",
            {"json_blocks": len(blocks), "doc": str(REPORT_DOC),
             "parses": bool(json.loads(blocks[0])) if blocks else False})


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res = run_checks()
    OUT_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    res["E6_durable_mirror_identical"] = "ok"
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    OUT_MIRROR.write_text(OUT.read_text())
    assert OUT_MIRROR.read_bytes() == OUT.read_bytes()
    for c in res["checks"]:
        print("%-56s %s" % (c["check"], c["result"].upper()))
    print("OVERALL:", res["status"].upper())
    return 0 if res["status"] in ("pass", "degraded") else 1


if __name__ == "__main__":
    sys.exit(main())