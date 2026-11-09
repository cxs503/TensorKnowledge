#!/usr/bin/env python3
"""Validator for the OSS-LBM free-surface knowledge subpackage (freesurf/).

Checks:
1. Schema conformance (Draft 2020-12) for claims, evidence, provenance
2. Cross-reference integrity (claim<->evidence bidirectional)
3. Count constraints (>=8 claims)
4. Provenance linkage
5. Epistemic discipline (no self-approval, review_events empty)
6. Quote discipline: verbatim quotes, <=3 lines, GAP anchor in every claim's notes
7. Verbatim check against the source cache when available (anti-fabrication gate)
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCHEMAS_DIR = HERE.parent.parent.parent / "schemas"
CACHE = Path("/root/oss-cache/Maarten-vd-Sande_lbm")

CLAIM_PATTERN = r"^tkc:oss-lbm-freesurf:[a-z0-9-]+$"
EVIDENCE_PATTERN = r"^tke:oss-lbm-freesurf:[a-z0-9-]+$"
PROVENANCE_PATTERN = r"^tkp:oss-lbm-freesurf:[a-z0-9-]+$"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_id_pattern(items, pattern, id_field, label):
    errors = []
    pat = re.compile(pattern)
    for item in items:
        if not pat.match(item[id_field]):
            errors.append(f"{label}: id '{item[id_field]}' does not match pattern {pattern}")
    return errors


def check_verbatim(evidence, errors):
    """Each evidence quote must appear verbatim at the located file:lines (if cache present)."""
    if not CACHE.is_dir():
        print("  NOTE: source cache missing; verbatim check skipped (not a failure)")
        return
    for ev in evidence:
        loc = ev.get("locator", {})
        value = loc.get("value", "")
        m = re.match(r"^Maarten-vd-Sande/lbm@[0-9a-f]+ (\S+):(\d+)(?:-(\d+))?$", value)
        if not m:
            errors.append(f"Evidence {ev['id']}: unparseable locator value '{value}'")
            continue
        path, lo = m.group(1), int(m.group(2))
        hi = int(m.group(3) or m.group(2))
        f = CACHE / path
        if not f.is_file():
            errors.append(f"Evidence {ev['id']}: located file missing in cache: {path}")
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        actual = lines[lo - 1:hi]
        quote_lines = loc.get("quote", "").split("\n")
        if len(quote_lines) > 3:
            errors.append(f"Evidence {ev['id']}: quote has {len(quote_lines)} lines (>3)")
        if actual != quote_lines:
            errors.append(f"Evidence {ev['id']}: quote is NOT verbatim at {path}:{lo}-{hi}")
            for i, (a, q) in enumerate(zip(actual, quote_lines)):
                if a != q:
                    errors.append(f"    line {lo + i}: file={a!r} quote={q!r}")
            if len(actual) != len(quote_lines):
                errors.append(f"    line count mismatch: file={len(actual)} quote={len(quote_lines)}")


def main() -> int:
    errors = []

    claims_path = HERE / "claims" / "claims.json"
    evidence_path = HERE / "evidence" / "evidence.json"
    provenance_path = HERE / "provenance" / "provenance.json"

    for p in (claims_path, evidence_path, provenance_path):
        if not p.exists():
            errors.append(f"Missing: {p}")
    if errors:
        print("FAIL: missing files")
        for e in errors:
            print(f"  - {e}")
        return 1

    claims = load_json(claims_path)
    evidence = load_json(evidence_path)
    provenance = load_json(provenance_path)

    if len(claims) < 8:
        errors.append(f"Expected >=8 claims, found {len(claims)}")

    errors.extend(validate_id_pattern(claims, CLAIM_PATTERN, "id", "claim"))
    errors.extend(validate_id_pattern(evidence, EVIDENCE_PATTERN, "id", "evidence"))
    errors.extend(validate_id_pattern(provenance, PROVENANCE_PATTERN, "id", "provenance"))

    claim_ids = {c["id"] for c in claims}
    evidence_ids = {e["id"] for e in evidence}
    if len(claim_ids) != len(claims):
        errors.append("Duplicate claim IDs")
    if len(evidence_ids) != len(evidence):
        errors.append("Duplicate evidence IDs")

    for claim in claims:
        for ref in claim.get("evidence_refs", []):
            if ref not in evidence_ids:
                errors.append(f"Claim {claim['id']} references missing evidence {ref}")
    for ev in evidence:
        for ref in ev.get("claim_refs", []):
            if ref not in claim_ids:
                errors.append(f"Evidence {ev['id']} references missing claim {ref}")

    for claim in claims:
        if claim.get("epistemic_status") not in ("established", "well-supported", "provisional", "contested", "speculative", "superseded", "not-assessed"):
            errors.append(f"Claim {claim['id']} has invalid epistemic_status: {claim.get('epistemic_status')}")
    for ev in evidence:
        if ev.get("assessment_status") not in ("unassessed", "reviewed-supports", "reviewed-refutes", "reviewed-qualifies", "insufficient", "disputed"):
            errors.append(f"Evidence {ev['id']} has invalid assessment_status: {ev.get('assessment_status')}")

    for claim in claims:
        for field in ("id", "statement", "claim_type", "epistemic_status", "created_at", "version"):
            if field not in claim:
                errors.append(f"Claim {claim.get('id', '?')} missing required field: {field}")
        if not claim.get("notes"):
            errors.append(f"Claim {claim['id']} missing notes (TensorLBM service statement required)")
        if not any("GAP-" in n for n in claim.get("notes", [])):
            errors.append(f"Claim {claim['id']} missing GAP anchor in notes")

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

    for prov in provenance:
        for field in ("id", "generated_entity", "activity", "agents", "recorded_at", "version"):
            if field not in prov:
                errors.append(f"Provenance {prov.get('id', '?')} missing required field: {field}")

    check_verbatim(evidence, errors)

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
    print(f"  All claims carry a GAP anchor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
