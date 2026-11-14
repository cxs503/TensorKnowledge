"""Audit structured claim/evidence bundles without pretending to judge semantics.

Checks bidirectional references, source confinement, exact quote offsets and hashes,
and consistency between declared evidence relations and independent review status.
A structurally valid, unassessed evidence item is NOT treated as support.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_RELATION_TO_STATUS = {
    "supports": "reviewed-supports",
    "refutes": "reviewed-refutes",
    "qualifies": "reviewed-qualifies",
}


def _load_records(directory: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    records: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []
    if not directory.is_dir():
        return records, [{"code": "directory_missing", "path": str(directory)}]
    for path in sorted(directory.glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append({"code": "invalid_json", "path": str(path), "detail": str(exc)})
            continue
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            errors.append({"code": "invalid_record", "path": str(path), "detail": "record must be an object with a string id"})
            continue
        if item["id"] in records:
            errors.append({"code": "duplicate_id", "path": str(path), "detail": item["id"]})
            continue
        records[item["id"]] = item
    return records, errors


def audit_claim_evidence(claims_dir: str | Path, evidence_dir: str | Path, source_root: str | Path) -> dict[str, Any]:
    claims, errors = _load_records(Path(claims_dir))
    evidence, evidence_errors = _load_records(Path(evidence_dir))
    errors.extend(evidence_errors)
    root = Path(source_root).resolve()
    findings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    pending_review = 0

    def finding(code: str, message: str, severity: str = "high", **details: Any) -> None:
        findings.append({
            "finding_id": f"{code}:{len(findings) + 1}",
            "check_id": code,
            "status": "confirmed",
            "severity": severity,
            "summary": message,
            "details": details,
        })

    def check(code: str, state: str, details: str, required: bool = True) -> None:
        checks.append({
            "check_id": code,
            "version": "0.2.0",
            "method": "deterministic_rule",
            "state": state,
            "required": required,
            "details": details,
        })

    for error in errors:
        finding(error["code"], error.get("detail", error["path"]), path=error["path"])

    broken_links = 0
    for claim_id, claim in claims.items():
        refs = claim.get("evidence_refs", [])
        if not isinstance(refs, list):
            finding("invalid_claim_evidence_refs", f"{claim_id} evidence_refs must be an array.")
            broken_links += 1
            continue
        for evidence_id in refs:
            item = evidence.get(evidence_id)
            if item is None:
                finding("missing_evidence_record", f"{claim_id} references missing evidence {evidence_id}.")
                broken_links += 1
            elif claim_id not in item.get("claim_refs", []):
                finding("nonreciprocal_evidence_link", f"{claim_id} references {evidence_id}, but the evidence does not reference the claim.")
                broken_links += 1
    for evidence_id, item in evidence.items():
        refs = item.get("claim_refs", [])
        if not isinstance(refs, list) or not refs:
            finding("evidence_without_claim", f"{evidence_id} has no claim_refs.")
            broken_links += 1
            continue
        for claim_id in refs:
            claim = claims.get(claim_id)
            if claim is None:
                finding("missing_claim_record", f"{evidence_id} references missing claim {claim_id}.")
                broken_links += 1
            elif evidence_id not in claim.get("evidence_refs", []):
                finding("nonreciprocal_claim_link", f"{evidence_id} references {claim_id}, but the claim does not reference the evidence.")
                broken_links += 1
    check("bidirectional_references", "failed" if broken_links else "passed",
          f"{broken_links} broken or non-reciprocal links across {len(claims)} claims and {len(evidence)} evidence records.")

    locator_errors = 0
    for evidence_id, item in evidence.items():
        source = item.get("source", {})
        citation = source.get("citation") if isinstance(source, dict) else None
        locator = item.get("locator", {})
        if not isinstance(citation, str) or not citation:
            finding("missing_source_citation", f"{evidence_id} has no source citation.")
            locator_errors += 1
            continue
        candidate = (root / citation).resolve()
        if candidate != root and root not in candidate.parents:
            finding("source_path_escape", f"{evidence_id} source path escapes the declared source root.")
            locator_errors += 1
            continue
        if not candidate.is_file():
            finding("source_file_missing", f"{evidence_id} source file does not exist: {citation}.")
            locator_errors += 1
            continue
        quote = locator.get("quote") if isinstance(locator, dict) else None
        start = locator.get("start_offset") if isinstance(locator, dict) else None
        end = locator.get("end_offset") if isinstance(locator, dict) else None
        content_hash = locator.get("content_hash") if isinstance(locator, dict) else None
        if not isinstance(quote, str) or not quote:
            finding("quote_missing", f"{evidence_id} has no exact quote; locator cannot be content-verified.")
            locator_errors += 1
            continue
        try:
            source_text = candidate.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            finding("source_not_readable_utf8", f"{evidence_id} source cannot be read as UTF-8.")
            locator_errors += 1
            continue
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start or end > len(source_text):
            finding("invalid_quote_offsets", f"{evidence_id} has invalid character offsets.")
            locator_errors += 1
            continue
        actual = source_text[start:end]
        if actual != quote:
            finding("quote_offset_mismatch", f"{evidence_id} quote does not match the source at its declared offsets.",
                    expected_quote=quote, actual_text=actual, citation=citation)
            locator_errors += 1
            continue
        actual_hash = hashlib.sha256(actual.encode("utf-8")).hexdigest()
        if content_hash != actual_hash:
            finding("quote_hash_mismatch", f"{evidence_id} quote hash does not match its extracted text.",
                    expected_hash=content_hash, actual_hash=actual_hash)
            locator_errors += 1
    check("source_locator_integrity", "failed" if locator_errors else "passed",
          f"{locator_errors} source/quote locator errors across {len(evidence)} evidence records.")

    relation_conflicts = 0
    for evidence_id, item in evidence.items():
        relation = item.get("relation")
        status = item.get("assessment_status")
        expected = _RELATION_TO_STATUS.get(relation)
        if status == "unassessed":
            pending_review += 1
        elif expected and status != expected:
            finding("relation_review_conflict",
                    f"{evidence_id} declares relation '{relation}' but review status is '{status}'.",
                    relation=relation, assessment_status=status)
            relation_conflicts += 1
        elif status not in {"reviewed-supports", "reviewed-refutes", "reviewed-qualifies", "insufficient", "disputed"}:
            finding("unknown_assessment_status", f"{evidence_id} has unsupported assessment_status '{status}'.")
            relation_conflicts += 1
    check("review_relation_consistency", "failed" if relation_conflicts else "passed",
          f"{relation_conflicts} relation/review conflicts; {pending_review} evidence items remain unassessed.")

    required_failures = any(item["state"] == "failed" for item in checks if item["required"])
    overall = "failed" if required_failures or errors else ("inconclusive" if pending_review else "passed")
    return {
        "schema_version": "0.2.0",
        "product_id": "research-audit",
        "product_version": "0.2.0",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {"claims_dir": str(Path(claims_dir)), "evidence_dir": str(Path(evidence_dir)), "source_root": str(root)},
        "counts": {"claims": len(claims), "evidence": len(evidence), "pending_review": pending_review},
        "checks": checks,
        "findings": findings,
        "overall_status": overall,
        "limitations": [
            "This audit verifies record linkage, source paths, exact quote offsets and quote hashes.",
            "It does not determine whether a source semantically entails, supports or refutes a claim.",
            "A structurally valid unassessed relation is reported as inconclusive, never as verified support.",
            "External URLs are not fetched; only local source files under source_root are checked.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit structured TensorKnowledge claim/evidence records.")
    parser.add_argument("--claims", required=True, help="Directory containing claim JSON records")
    parser.add_argument("--evidence", required=True, help="Directory containing evidence JSON records")
    parser.add_argument("--source-root", required=True, help="Root directory that confines local source citations")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()
    result = audit_claim_evidence(args.claims, args.evidence, args.source_root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
