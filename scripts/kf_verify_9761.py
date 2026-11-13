#!/usr/bin/env python3
"""Independent verification of wp-9761-01 against the six acceptance items.

Independence measures: the markdown is **re-fetched from the platform API** (the local
copy under runs/ is only a fallback), the sha256 is recomputed from scratch, and every
locator is re-resolved by slicing the freshly fetched text. Nothing here writes back
into the manifest.

Checks (exactly the contract acceptance list):
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
Extras: result envelope shape (kf_result.v1), claim discipline (no "verified" markers),
counts consistency, artifact<->durable-mirror byte equality, report_id scoping.

Outputs: artifacts/wp-9761-01/verification.json ; prints PASS/FAIL per check;
exit code 0 iff every check passes (degraded-by-environment items are reported as
"unknown", never as "pass").

Usage: python3 scripts/kf_verify_9761.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

REPORT_ID = "9761"
PACKAGE_ID = "wp-9761-01"
EXPECTED_HASH = "4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a"
MANIFEST = pathlib.Path("artifacts/wp-9761-01/asset_manifest.json")
MIRROR = pathlib.Path("docs/wp-9761-01/asset_manifest.json")
SCHEMA = pathlib.Path("schemas/asset_manifest.v1.wp-9761-01.schema.json")
ENVELOPE_SCHEMA = pathlib.Path("schemas/kf_result.v1.schema.json")
RESULT = pathlib.Path("runs/wp-9761-01/kf_result.wp-9761-01.json")
BLOCK = pathlib.Path("runs/wp-9761-01/kf_result_block.wp-9761-01.json")
LOCAL_MD = pathlib.Path("runs/wp-9761-01/report_9761.md")
OUT = pathlib.Path("artifacts/wp-9761-01/verification.json")
MIRROR = pathlib.Path("docs/wp-9761-01/verification.json")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

RESOLUTION_TO_CHECK = {"resolved_in_source": "resolved",
                       "referenced_unresolved": "unresolved",
                       "declared_absent": "absent"}


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
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


def fetch_report() -> tuple[str, dict]:
    tok = login()
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok} if tok else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    if "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    return d.get("markdown", ""), d


# ---------------- reusable checks (also imported by tests/test_kf_wp9761.py) ----------------
def check_locators(md: str, manifest: dict) -> list[tuple[str, str]]:
    """Return [(asset_id, reason)] for every locator that does not re-resolve in ``md``."""
    bad = []
    lines = md.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        if md[loc["start_char"]:loc["end_char"]] != quote:
            bad.append((a["asset_id"], "slice_mismatch"))
        if md.count(quote) != 1:
            bad.append((a["asset_id"], "quote_not_unique:%d" % md.count(quote)))
        if not loc["unique"]:
            bad.append((a["asset_id"], "unique_flag_false"))
        if "\n".join(lines[loc["start_line"]:loc["end_line"] + 1]) != quote:
            bad.append((a["asset_id"], "line_span_mismatch"))
        if a["resolution_check"]["result"] != RESOLUTION_TO_CHECK[a["resolution"]]:
            bad.append((a["asset_id"], "resolution_check_mismatch:%s!=%s"
                        % (a["resolution_check"]["result"], RESOLUTION_TO_CHECK[a["resolution"]])))
    return bad


def check_duplicate_ids(manifest: dict) -> list[str]:
    ids = [a["asset_id"] for a in manifest["assets"]]
    obs = [o["id"] for o in manifest.get("observations", [])]
    dup = sorted({i for i in ids if ids.count(i) > 1}) + \
          sorted({i for i in obs if obs.count(i) > 1})
    # an observation referring to a non-existent asset is also an id-integrity defect
    have = set(ids)
    dup += sorted({o["evidence_asset"] for o in manifest.get("observations", [])
                   if o["evidence_asset"] not in have})
    return dup


def check_claims(claims: list) -> list:
    return [c.get("claim_id") for c in claims
            if "evidence_locator" not in c and "evidence" not in c and "status" not in c]


def main() -> int:
    checks = []

    def rec(name, ok, detail, status="pass"):
        checks.append(dict(check=name, result=(status if not ok else "pass"), detail=detail))

    # ---------- C1 valid_json ----------
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        mirror = json.loads(MIRROR.read_text(encoding="utf-8"))
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        block = json.loads(BLOCK.read_text(encoding="utf-8"))
        rec("valid_json", True,
            {"manifest": str(MANIFEST), "mirror": str(MIRROR), "result": str(RESULT),
             "block_equals_result": block == result,
             "mirror_equals_manifest": mirror == manifest,
             "artifact_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest()})
    except Exception as exc:
        rec("valid_json", False, str(exc), status="fail")
        OUT.write_text(json.dumps(dict(checks=checks, overall="FAIL"), ensure_ascii=False, indent=2))
        print("FAIL valid_json:", exc)
        return 1

    # ---------- C2 schema_pass ----------
    try:
        pkg_schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, pkg_schema)
        env_schema = json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(result, env_schema)
        rec("schema_pass", True,
            {"package_schema": str(SCHEMA),
             "envelope_schema": str(ENVELOPE_SCHEMA),
             "envelope_top_level_keys": sorted(result.keys()),
             "outputs_keys": sorted(result["outputs"].keys())})
    except Exception as exc:
        rec("schema_pass", False, "%s: %s" % (type(exc).__name__, exc), status="fail")

    # ---------- C4 source_hash_matches (independent re-fetch) ----------
    md, payload, fetched_via = "", {}, "local_copy"
    try:
        md, payload = fetch_report()
        fetched_via = "api"
    except Exception as exc:
        rec("source_hash_matches", False, "API fetch failed: %s" % exc, status="unknown")
        md = LOCAL_MD.read_text(encoding="utf-8")
    if md:
        fresh = hashlib.sha256(md.encode()).hexdigest()
        ok = (fresh == EXPECTED_HASH
              and manifest["source"]["hash"] == fresh
              and result["provenance"]["source_hash"] == "sha256:" + fresh
              and manifest["source"]["chars"] == len(md))
        rec("source_hash_matches", ok,
            {"fetched_via": fetched_via, "api_sha256": fresh, "contract_sha256": EXPECTED_HASH,
             "manifest_sha256": manifest["source"]["hash"],
             "result_sha256": result["provenance"]["source_hash"],
             "api_chars": len(md), "manifest_chars": manifest["source"]["chars"],
             "api_bytes_utf8": len(md.encode()),
             "platform_figures": len(payload.get("figures") or [])})

    # ---------- C3 source_locator_resolvable ----------
    if md:
        bad = check_locators(md, manifest)
        rec("source_locator_resolvable", not bad,
            {"assets_checked": len(manifest["assets"]), "defects": bad,
             "resolved_in_source": sum(1 for a in manifest["assets"]
                                       if a["resolution"] == "resolved_in_source"),
             "referenced_unresolved": sum(1 for a in manifest["assets"]
                                          if a["resolution"] == "referenced_unresolved")},
            status="fail")

    # ---------- C5 no_duplicate_ids ----------
    dup = check_duplicate_ids(manifest)
    rec("no_duplicate_ids", not dup,
        {"asset_ids": len(manifest["assets"]), "observation_ids": len(manifest["observations"]),
         "duplicates_or_dangling": dup}, status="fail")

    # ---------- C6 claims discipline ----------
    claims = result.get("claims") or []
    missing = check_claims(claims)
    ok = not missing
    rec("all_claims_have_evidence_or_explicit_unresolved_status", ok,
        {"claims": len(claims), "missing_evidence_or_status": missing,
         "note": "claims 为空数组是契约允许的完整结果（不做抽取）"}, status="fail")

    # ---------- extras ----------
    blob = json.dumps({"m": manifest, "r": result}, ensure_ascii=False)
    forbidden = [t for t in ('"verified": true', '"status": "verified"', '"verified_by"')
                 if t in blob]
    rec("no_premature_verification_marks", not forbidden,
        {"markers_found": forbidden,
         "integrity_verified_flags": manifest["integrity"]["verified_flags"],
         "provenance_verification_status": result["provenance"]["verification_status"]},
        status="fail")

    by_res, n = {}, len(manifest["assets"])
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    ok_counts = (c["assets"] == n and c["by_resolution"] == by_res
                 and c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
                 and c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
                 and c["unique_quotes"] == sum(1 for a in manifest["assets"]
                                               if a["locator"]["unique"]))
    rec("counts_consistent", ok_counts, {"declared": c, "recomputed": by_res, "assets": n},
        status="fail")

    ok_scope = (manifest["report_id"] == REPORT_ID and result["report_id"] == REPORT_ID
                and manifest["source"]["uri"].endswith("/" + REPORT_ID)
                and result["provenance"]["source_uri"].endswith("/" + REPORT_ID))
    rec("report_scope_isolated", ok_scope,
        {"manifest_report_id": manifest["report_id"], "result_report_id": result["report_id"],
         "source_uri": manifest["source"]["uri"]}, status="fail")

    overall = "PASS" if all(c["result"] == "pass" for c in checks) else "FAIL"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(dict(package_id=PACKAGE_ID, report_id=REPORT_ID,
                           source_sha256="sha256:" + EXPECTED_HASH,
                           fetched_via=fetched_via, checks=checks, overall=overall),
                      ensure_ascii=False, indent=2) + "\n"
    OUT.write_text(blob, encoding="utf-8")
    # durable mirror: the repo push gate drops artifacts/**, so keep a byte-identical copy
    MIRROR.parent.mkdir(parents=True, exist_ok=True)
    MIRROR.write_text(blob, encoding="utf-8")
    assert MIRROR.read_bytes() == OUT.read_bytes()
    for c in checks:
        print("%-6s %s" % (c["result"].upper(), c["check"]))
    print("overall:", overall, "->", OUT)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())