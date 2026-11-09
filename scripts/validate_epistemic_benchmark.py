#!/usr/bin/env python3
"""Validate TensorKnowledge epistemic schemas and benchmark fixture integrity."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
CASES = ROOT / "platform-test" / "epistemic-benchmark" / "cases"

SCHEMA_NAMES = [
    "claim-record.schema.json",
    "evidence-record.schema.json",
    "provenance-record.schema.json",
    "review-event.schema.json",
    "benchmark-case.schema.json",
]

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> int:
    errors: list[str] = []
    try:
        import jsonschema
    except ImportError:
        print("ERROR: install validation dependencies: python -m pip install -r requirements-validation.txt")
        return 2

    schemas = {}
    for name in SCHEMA_NAMES:
        path = SCHEMAS / name
        try:
            schema = load(path)
            jsonschema.Draft202012Validator.check_schema(schema)
            schemas[name] = schema
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid schema: {exc}")

    if len(schemas) != len(SCHEMA_NAMES):
        print("\n".join(errors))
        return 1

    files = sorted(CASES.glob("case-*.json"))
    if len(files) != 10:
        errors.append(f"expected 10 benchmark cases, found {len(files)}")

    seen_case_ids: set[str] = set()
    category_seen: set[str] = set()
    all_cases = []
    for path in files:
        try:
            case = load(path)
            jsonschema.validate(case, schemas["benchmark-case.schema.json"])
            all_cases.append(case)
            if case["case_id"] in seen_case_ids:
                errors.append(f"{path.name}: duplicate case_id {case['case_id']}")
            seen_case_ids.add(case["case_id"])
            category_seen.add(case["category"])
            claims = case["claims"]
            evidence = case["evidence"]
            claim_ids = {item["id"] for item in claims}
            evidence_ids = {item["id"] for item in evidence}
            if len(claim_ids) != len(claims):
                errors.append(f"{path.name}: duplicate claim IDs")
            if len(evidence_ids) != len(evidence):
                errors.append(f"{path.name}: duplicate evidence IDs")
            for item in claims:
                jsonschema.validate(item, schemas["claim-record.schema.json"])
                for ref in item.get("evidence_refs", []):
                    if ref not in evidence_ids:
                        errors.append(f"{path.name}: claim {item['id']} references missing evidence {ref}")
            for item in evidence:
                jsonschema.validate(item, schemas["evidence-record.schema.json"])
                for ref in item["claim_refs"]:
                    if ref not in claim_ids:
                        errors.append(f"{path.name}: evidence {item['id']} references missing claim {ref}")
            jsonschema.validate(case["provenance"], schemas["provenance-record.schema.json"])
            for event in case["review_events"]:
                jsonschema.validate(event, schemas["review-event.schema.json"])
                if event["object_ref"] not in claim_ids:
                    errors.append(f"{path.name}: review event references missing claim {event['object_ref']}")
                if event["decision"] == "approve":
                    errors.append(f"{path.name}: producer benchmark fixtures must not self-approve")
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    by_category = {case["category"]: case for case in all_cases}
    contested = by_category.get("contested-claim")
    if contested:
        relations = {item["relation"] for item in contested["evidence"]}
        if not {"supports", "refutes"}.issubset(relations):
            errors.append("contested-claim case must retain both supports and refutes evidence")
    insufficient = by_category.get("insufficient-evidence")
    if insufficient and any(item["assessment_status"] != "insufficient" for item in insufficient["evidence"]):
        errors.append("insufficient-evidence case must not label its evidence as sufficient")
    temporal = by_category.get("temporal-change")
    if temporal and not any(item.get("valid_time") for item in temporal["claims"]):
        errors.append("temporal-change case must include claim valid_time")
    if len(category_seen) != 10:
        errors.append(f"expected 10 distinct scenario categories, found {len(category_seen)}")

    if errors:
        print("FAIL: epistemic benchmark validation")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: {len(files)} benchmark cases; {len(SCHEMA_NAMES)} Draft 2020-12 schemas; cross-references and epistemic invariants valid.")
    print("NOTE: structural validation does not establish factual correctness or claim-evidence entailment.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
