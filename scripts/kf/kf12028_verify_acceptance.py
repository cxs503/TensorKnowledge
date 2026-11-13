#!/usr/bin/env python3
"""wp-12028-01 worker-side acceptance self-check (NOT the platform gate).

Re-derives every acceptance item of the package contract from raw bytes:

  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

plus contract constraints: single-report hard lock (only report_id 12028),
declared output filename, nothing marked verified, no forced claim generation.

The markdown is re-fetched from the platform API unless --offline is given, so a
stale local snapshot cannot pass the hash check.  All checks live in
scripts/kf/kf12028_checks.py so tests can run them against tampered inputs.

Usage: python3 scripts/kf/kf12028_verify_acceptance.py [--offline]
Writes docs/kf/wp-12028-01/acceptance.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kf12028_checks as kc  # noqa: E402
from register_assets_lib import fetch_report  # noqa: E402

PKG = "wp-12028-01"
REPORT_ID = "12028"
CONTRACT_HASH = "sha256:69846e9d0680b8a1c5db5c607b9a5bf4a0ba2e6103b1d193a6a5d5e83e0ec29f"
CONTRACT_CHARS = 8377
ENV = Path("docs/kf/wp-12028-01/kf_result.json")
MAN = Path("docs/kf/wp-12028-01/asset_manifest.json")
OUT = Path("docs/kf/wp-12028-01/acceptance.json")
SCHEMA = Path("schemas/kf_result.v1.schema.json")
SNAP = Path("work/wp-12028-01/source/report_12028.json")


def check(checks: list, name: str, ok: bool, detail) -> None:
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()

    checks: list[dict] = []

    # ---- valid_json ------------------------------------------------------
    try:
        env = json.loads(ENV.read_text(encoding="utf-8"))
        man = json.loads(MAN.read_text(encoding="utf-8"))
        valid, detail = True, {"envelope": str(ENV), "manifest": str(MAN)}
    except Exception as e:  # noqa: BLE001
        env, man, valid, detail = {}, {}, False, repr(e)
    check(checks, "valid_json", valid, detail)

    # ---- schema_pass -----------------------------------------------------
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(env, schema)
        ok, err = True, None
    except jsonschema.ValidationError as e:  # pragma: no cover
        ok, err = False, str(e.message)
    check(checks, "schema_pass", ok, {"schema": str(SCHEMA), "error": err,
                                      "envelope_keys": sorted(env.keys())})

    # ---- contract alignment + single-report hard lock --------------------
    scope = man.get("scope", {})
    alignment = {
        "package_id": env.get("package_id") == PKG,
        "task_type": env.get("task_type") == "01-asset-registration",
        "report_id": env.get("report_id") == REPORT_ID,
        "manifest_package_id": man.get("package_id") == PKG,
        "manifest_report_id": scope.get("report_id") == REPORT_ID,
        "reports_touched_is_single_12028": scope.get("reports_touched") == [REPORT_ID],
        "declared_output_present": "asset_manifest.json" in (env.get("outputs") or {}),
    }
    check(checks, "contract_alignment", all(alignment.values()), alignment)

    # ---- source_hash_matches --------------------------------------------
    rec = fetch_report(REPORT_ID, record_file=(SNAP if a.offline else None))
    md = rec["markdown"]
    h = kc.hash_report(md, env, man)
    hash_ok = (h["matches_provenance"] and h["matches_manifest"]
               and h["recomputed"] == CONTRACT_HASH and h["chars"] == CONTRACT_CHARS)
    check(checks, "source_hash_matches", hash_ok, {
        **h,
        "recomputed_from": rec.get("_retrieved_via"),
        "contract_declared": CONTRACT_HASH,
        "chars_expected": CONTRACT_CHARS,
        "bytes_utf8": len(md.encode("utf-8")),
    })

    # ---- source_locator_resolvable --------------------------------------
    bad = kc.locator_failures(man, md, rec)
    n_loc = sum(len(x.get("locators", [])) for x in man.get("assets", []))
    n_obs = sum(len(o.get("evidence", [])) for o in man.get("observations", []))
    check(checks, "source_locator_resolvable", not bad and n_loc > 0 and n_obs > 0,
          {"asset_locators_checked": n_loc, "observation_evidence_checked": n_obs,
           "failures": bad})

    # ---- no_duplicate_ids ------------------------------------------------
    dup = kc.duplicate_report(man, env)
    check(checks, "no_duplicate_ids", dup["all_unique"], dup)

    # ---- claims: evidence or explicit unresolved status ------------------
    defects = kc.claim_defects(env.get("claims"))
    check(checks, "all_claims_have_evidence_or_explicit_unresolved_status", not defects, {
        "claims": len(env.get("claims") or []),
        "empty_claims_allowed_by_contract_notes": True,
        "reason_recorded": bool(man.get("claims_policy", {}).get("reason")),
        "defects": defects,
    })

    # ---- structural invariants ------------------------------------------
    inv = kc.structural_invariants(man)
    check(checks, "structural_invariants", kc.all_pass(inv), inv)

    ok = all(c["status"] == "PASS" for c in checks)
    payload = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_by": "worker self-check (NOT the platform gate; status stays draft)",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "mode": "offline" if a.offline else "online",
        "summary": {"total": len(checks),
                    "pass": sum(c["status"] == "PASS" for c in checks),
                    "fail": sum(c["status"] == "FAIL" for c in checks), "all_pass": ok},
        "checks": checks,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in checks:
        print("%-4s %s" % (c["status"], c["check"]))
        if c["status"] == "FAIL":
            print("     detail:", kc.dumps(c["detail"])[:700])
    print("all_pass:", ok, "->", OUT)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())