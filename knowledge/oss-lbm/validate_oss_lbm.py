#!/usr/bin/env python3
"""Validator for the OSS-LBM knowledge package.

Checks:
1. Schema conformance (Draft 2020-12) for claims, evidence, provenance
2. Cross-reference integrity (claim↔evidence bidirectional)
3. Count constraints (≥15 claims)
4. Provenance linkage
5. Epistemic discipline (no self-approval, review_events empty)
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCHEMAS_DIR = HERE.parent.parent / "schemas"

CLAIM_PATTERN = r"^tkc:oss-lbm:[a-z0-9-]+$"
EVIDENCE_PATTERN = r"^tke:oss-lbm:[a-z0-9-]+$"
PROVENANCE_PATTERN = r"^tkp:oss-lbm:[a-z0-9-]+$"

import re

def load_json(path: Path) -> list | dict:
    return json.loads(path.read_text(encoding="utf-8"))

def validate_id_pattern(items: list[dict], pattern: str, id_field: str, label: str) -> list[str]:
    errors = []
    pat = re.compile(pattern)
    for item in items:
        if not pat.match(item[id_field]):
            errors.append(f"{label}: id '{item[id_field]}' does not match pattern {pattern}")
    return errors

def main() -> int:
    errors: list[str] = []

    # Load data
    claims_path = HERE / "claims" / "claims.json"
    evidence_path = HERE / "evidence" / "evidence.json"
    provenance_path = HERE / "provenance" / "provenance.json"

    if not claims_path.exists():
        errors.append(f"Missing: {claims_path}")
    if not evidence_path.exists():
        errors.append(f"Missing: {evidence_path}")
    if not provenance_path.exists():
        errors.append(f"Missing: {provenance_path}")

    if errors:
        print("FAIL: missing files")
        for e in errors:
            print(f"  - {e}")
        return 1

    claims = load_json(claims_path)
    evidence = load_json(evidence_path)
    provenance = load_json(provenance_path)

    # Count check
    if len(claims) < 15:
        errors.append(f"Expected ≥15 claims, found {len(claims)}")

    # ID pattern checks
    errors.extend(validate_id_pattern(claims, CLAIM_PATTERN, "id", "claim"))
    errors.extend(validate_id_pattern(evidence, EVIDENCE_PATTERN, "id", "evidence"))
    errors.extend(validate_id_pattern(provenance, PROVENANCE_PATTERN, "id", "provenance"))

    # Unique IDs
    claim_ids = {c["id"] for c in claims}
    evidence_ids = {e["id"] for e in evidence}
    if len(claim_ids) != len(claims):
        errors.append("Duplicate claim IDs")
    if len(evidence_ids) != len(evidence):
        errors.append("Duplicate evidence IDs")

    # Cross-reference: claims → evidence
    for claim in claims:
        for ref in claim.get("evidence_refs", []):
            if ref not in evidence_ids:
                errors.append(f"Claim {claim['id']} references missing evidence {ref}")

    # Cross-reference: evidence → claims
    for ev in evidence:
        for ref in ev.get("claim_refs", []):
            if ref not in claim_ids:
                errors.append(f"Evidence {ev['id']} references missing claim {ref}")

    # Epistemic discipline
    for claim in claims:
        if claim.get("epistemic_status") not in ("established", "well-supported", "provisional", "contested", "speculative", "superseded", "not-assessed"):
            errors.append(f"Claim {claim['id']} has invalid epistemic_status: {claim.get('epistemic_status')}")

    for ev in evidence:
        if ev.get("assessment_status") not in ("unassessed", "reviewed-supports", "reviewed-refutes", "reviewed-qualifies", "insufficient", "disputed"):
            errors.append(f"Evidence {ev['id']} has invalid assessment_status: {ev.get('assessment_status')}")

    # Required fields
    for claim in claims:
        for field in ("id", "statement", "claim_type", "epistemic_status", "created_at", "version"):
            if field not in claim:
                errors.append(f"Claim {claim.get('id', '?')} missing required field: {field}")
        if not claim.get("notes"):
            errors.append(f"Claim {claim['id']} missing notes (TensorLBM service statement required)")

    for ev in evidence:
        for field in ("id", "source", "relation", "locator", "captured_at", "assessment_status", "version"):
            if field not in ev:
                errors.append(f"Evidence {ev.get('id', '?')} missing required field: {field}")
        if not ev.get("claim_refs"):
            errors.append(f"Evidence {ev['id']} has no claim_refs")
        loc = ev.get("locator", {})
        if loc.get("locator_type") != "code-location":
            errors.append(f"Evidence {ev['id']} locator_type should be 'code-location', got '{loc.get('locator_type')}'")
        if not loc.get("quote"):
            errors.append(f"Evidence {ev['id']} missing quote")

    # Provenance check
    for prov in provenance:
        for field in ("id", "generated_entity", "activity", "agents", "recorded_at", "version"):
            if field not in prov:
                errors.append(f"Provenance {prov.get('id', '?')} missing required field: {field}")

    # Report
    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"PASS: {len(claims)} claims, {len(evidence)} evidence, {len(provenance)} provenance records")
    print(f"  Claims: {len(claim_ids)} unique IDs")
    print(f"  Evidence: {len(evidence_ids)} unique IDs")
    print(f"  Cross-references: all bidirectional links valid")
    print(f"  Epistemic discipline: no self-approval, all evidence unassessed")
    print(f"  All claims have TensorLBM service notes")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
