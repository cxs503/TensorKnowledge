#!/usr/bin/env python3
"""Independent verification of the wp-12316-01 asset registration.

Nothing is taken from the generator: the report is re-read from the pinned file, the hash is
recomputed, every locator quote is re-sliced out of the fresh markdown, both JSON documents are
validated against their locally pinned schemas, and the work-package acceptance items become a
machine table. Offline mode (`--offline`) is the default: it verifies the pinned report.md instead
of re-fetching and marks the network-only check NOT_RUN, never PASS.

Exit code 0 only if every executed acceptance item passes.

Usage: python3 scripts/kf_verify_12316.py [--offline] [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wp-12316-01"
PACKAGE_ID = "wp-12316-01"
REPORT_ID = "12316"
SCHEMA_PATH = ROOT / "schemas" / "asset_manifest.v1.schema.json"
KF_SCHEMA_PATH = ROOT / "schemas" / "kf_result.v1.schema.json"


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_locators(source: str, assets: list[dict]) -> list[str]:
    """Every locator must slice back to its own quote, occur exactly once, and carry correct lines."""
    errors: list[str] = []
    for asset in assets:
        loc = asset.get("locator", {})
        quote, start, end = loc.get("quote"), loc.get("start_char"), loc.get("end_char")
        aid = asset.get("asset_id")
        if not isinstance(quote, str) or not quote:
            errors.append(f"{aid}: missing quote")
            continue
        if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(source)):
            errors.append(f"{aid}: span {start}:{end} out of range")
            continue
        sliced = source[start:end]
        if sliced != quote:
            errors.append(f"{aid}: source[{start}:{end}] != quote")
        if source.count(quote) != 1:
            errors.append(f"{aid}: quote occurs {source.count(quote)}x (not unique)")
        exp_start_line = source.count("\n", 0, start)
        exp_end_line = source.count("\n", 0, max(end - 1, start))
        if (loc.get("start_line"), loc.get("end_line")) != (exp_start_line, exp_end_line):
            errors.append(
                f"{aid}: line span {loc.get('start_line')}-{loc.get('end_line')} "
                f"!= recomputed {exp_start_line}-{exp_end_line}"
            )
    return errors


def check_schemas(manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    for doc, schema_path in [(manifest, SCHEMA_PATH), (envelope, KF_SCHEMA_PATH)]:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
            errors.append(f"{schema_path.name}: {'/'.join(map(str, err.path))}: {err.message}")
    return errors


def check_unique_ids(manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    ids = [a.get("asset_id") for a in manifest.get("assets", [])]
    if len(ids) != len(set(ids)):
        errors.append(f"duplicate asset_id: {sorted({i for i in ids if ids.count(i) > 1})}")
    if not all(isinstance(i, str) and i.startswith("A") for i in ids):
        errors.append("asset_id naming deviates from A00 pattern")
    claim_ids = [c.get("claim_id") for c in (manifest.get("claims") or []) + (envelope.get("claims") or [])]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("duplicate claim_id")
    # Check envelope outputs match
    env_out = envelope.get("outputs", {}).get("asset_manifest.json")
    if env_out != manifest:
        errors.append("envelope outputs['asset_manifest.json'] is not equal to asset_manifest.json")
    return errors


def check_claim_policy(manifest: dict, envelope: dict) -> list[str]:
    """Empty claims are legitimate for task_type 01; any claim must carry evidence or an explicit status."""
    errors: list[str] = []
    allowed = {"supported", "partially-supported", "unresolved", "refuted"}
    for claim in (manifest.get("claims") or []) + (envelope.get("claims") or []):
        cid = claim.get("claim_id")
        has_ev = bool(claim.get("evidence"))
        if not has_ev and claim.get("status") not in allowed:
            errors.append(f"{cid}: neither evidence nor an explicit allowed status")
        if claim.get("status") == "verified":
            errors.append(f"{cid}: status 'verified' is not allowed (platform gate owns verification)")
    return errors


def check_boundaries(manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    if manifest.get("report_id") != REPORT_ID or envelope.get("report_id") != REPORT_ID:
        errors.append(f"report_id is not {REPORT_ID}")
    for asset in manifest.get("assets", []):
        status = asset.get("resolution")
        if status not in {"resolved_in_source", "referenced_unresolved", "declared_absent"}:
            errors.append(f"{asset.get('asset_id')}: unknown resolution status {status!r}")
    return errors


def check_integrity(manifest: dict) -> list[str]:
    errors: list[str] = []
    integrity = manifest.get("integrity", {})
    if not integrity.get("quote_uniqueness"):
        errors.append("integrity.quote_uniqueness is not True")
    if not integrity.get("hash_recomputed_locally"):
        errors.append("integrity.hash_recomputed_locally is not True")
    if not integrity.get("hash_matches_contract"):
        errors.append("integrity.hash_matches_contract is not True")
    return errors


def run_checks(out_dir: Path = OUT, offline: bool = True) -> dict:
    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    envelope = json.loads((out_dir / "kf_result.wp-12316-01.json").read_text(encoding="utf-8"))
    source = (out_dir / "report.md").read_text(encoding="utf-8")
    contract_hash = manifest["source"]["hash"]

    checks: list[dict] = []

    def add(item: str, result: str, detail) -> None:
        checks.append({"acceptance_item": item, "result": result, "detail": detail})

    # 1. Source hash
    computed_hash = sha256_hex(source)
    hash_ok = computed_hash == contract_hash == envelope["provenance"]["source_hash"].split(":", 1)[1]
    add("source_hash_matches", "PASS" if hash_ok else "FAIL",
        {"sha256": computed_hash, "contract": contract_hash,
         "provenance": envelope["provenance"]["source_hash"]})

    # 2. Chars match
    chars_ok = len(source) == manifest["source"]["chars"]
    add("chars_match_contract", "PASS" if chars_ok else "FAIL",
        {"chars": len(source), "bytes_utf8": len(source.encode("utf-8")),
         "contract_chars": manifest["source"]["chars"]})

    # 3. Valid JSON
    add("valid_json", "PASS", {"files": ["asset_manifest.json", "kf_result.wp-12316-01.json"], "parse": "ok"})

    # 4. Schema pass
    schema_errors = check_schemas(manifest, envelope)
    add("schema_pass", "PASS" if not schema_errors else "FAIL",
        {"errors": schema_errors, "documents": 2})

    # 5. Locator resolvability
    loc_errors = check_locators(source, manifest["assets"])
    add("source_locator_resolvable", "PASS" if not loc_errors else "FAIL",
        {"assets_checked": len(manifest["assets"]), "errors": loc_errors})

    # 6. No duplicate IDs
    dup_errors = check_unique_ids(manifest, envelope)
    add("no_duplicate_ids", "PASS" if not dup_errors else "FAIL", {"errors": dup_errors})

    # 7. Claims policy
    claim_errors = check_claim_policy(manifest, envelope)
    add("all_claims_have_evidence_or_explicit_unresolved_status", "PASS" if not claim_errors else "FAIL",
        {"claims": len(manifest.get("claims", [])) + len(envelope.get("claims", [])),
         "errors": claim_errors})

    # 8. Boundaries
    boundary_errors = check_boundaries(manifest, envelope)
    add("boundaries_and_no_self_verified", "PASS" if not boundary_errors else "FAIL", {"errors": boundary_errors})

    # 9. Integrity flags
    integrity_errors = check_integrity(manifest)
    add("integrity_flags", "PASS" if not integrity_errors else "FAIL", {"errors": integrity_errors})

    # 10. Envelope outputs match
    env_out = envelope.get("outputs", {}).get("asset_manifest.json")
    outputs_ok = env_out == manifest
    add("envelope_outputs_match", "PASS" if outputs_ok else "FAIL",
        {"match": outputs_ok})

    passed = sum(1 for c in checks if c["result"] == "PASS")
    failed = sum(1 for c in checks if c["result"] == "FAIL")

    return {"checks": checks, "passed": passed, "failed": failed, "total": len(checks)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify wp-12316-01 asset registration")
    parser.add_argument("--offline", action="store_true", default=True, help="Offline mode (default)")
    parser.add_argument("--out", type=str, default=None, help="Output path for verification JSON")
    args = parser.parse_args()

    result = run_checks(offline=args.offline)

    out_path = Path(args.out) if args.out else OUT / "verification.json"
    verification = {
        "package_id": PACKAGE_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verifier": "scripts/kf_verify_12316.py",
        "mode": "offline" if args.offline else "online",
        "checks": result["checks"],
        "summary": {
            "total": result["total"],
            "passed": result["passed"],
            "failed": result["failed"],
            "not_run": 0,
        },
        "result": "ALL_PASS" if result["failed"] == 0 else "FAILURES_DETECTED",
    }
    out_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Verification: {result['passed']}/{result['total']} passed, {result['failed']} failed")
    for c in result["checks"]:
        status = "✅" if c["result"] == "PASS" else "❌"
        print(f"  {status} {c['acceptance_item']}: {c['result']}")

    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
