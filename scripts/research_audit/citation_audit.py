"""Deterministic citation-integrity audit for Markdown research reports.

This first slice checks numeric citation/reference consistency only. It does not
judge whether a cited source semantically supports the claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HEADING_RE = re.compile(r"^#{1,6}\s*(references|bibliography|参考文献)\s*$", re.IGNORECASE)
_REF_RE = re.compile(r"^\s*(?:\[(\d+)\]|(\d+)[.)])\s+(.+?)\s*$")
_CITATION_RE = re.compile(r"\[(\d+(?:\s*[,;，、]\s*\d+)*)\]")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_sections(lines: list[str]) -> tuple[int | None, int | None]:
    start = next((i for i, line in enumerate(lines) if _HEADING_RE.match(line.strip())), None)
    if start is None:
        return None, None
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^#{1,6}\s+", lines[i])),
        len(lines),
    )
    return start, end


def audit_markdown(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"report must be UTF-8 Markdown: {exc}") from exc

    lines = text.splitlines()
    ref_start, ref_end = _parse_sections(lines)
    reference_lines: dict[str, list[int]] = {}
    if ref_start is not None and ref_end is not None:
        for line_no in range(ref_start + 1, ref_end + 1):
            match = _REF_RE.match(lines[line_no - 1])
            if match:
                ref_id = match.group(1) or match.group(2)
                reference_lines.setdefault(ref_id, []).append(line_no)

    cited: dict[str, list[int]] = {}
    body_end = ref_start if ref_start is not None else len(lines)
    for line_no, line in enumerate(lines[:body_end], start=1):
        for match in _CITATION_RE.finditer(line):
            for ref_id in re.split(r"\s*[,;，、]\s*", match.group(1)):
                cited.setdefault(ref_id, []).append(line_no)

    findings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    evidence_ref = f"file:sha256:{digest}"

    def add_check(check_id: str, state: str, details: str, required: bool = True) -> None:
        checks.append({
            "check_id": check_id,
            "version": "0.1.0",
            "method": "deterministic_rule",
            "state": state,
            "required": required,
            "details": details,
        })

    def add_finding(check_id: str, summary: str, line_numbers: list[int], severity: str = "medium") -> None:
        findings.append({
            "finding_id": f"{check_id}:{len(findings) + 1}",
            "check_id": check_id,
            "status": "confirmed",
            "severity": severity,
            "summary": summary,
            "rationale": summary,
            "evidence_refs": [evidence_ref],
            "review_state": "unreviewed",
            "limitations": ["This is a structural citation check, not a semantic source-support judgment."],
            "locator": {"line_numbers": line_numbers},
        })

    if ref_start is None:
        add_check("references_section_present", "inconclusive",
                  "No References/Bibliography/参考文献 heading was found.")
        add_finding("references_section_present",
                    "A recognizable bibliography section is missing; citation resolution cannot be completed.",
                    [], "high")
    else:
        add_check("references_section_present", "passed",
                  f"Bibliography section found at line {ref_start + 1}.")

    duplicates = sorted(ref_id for ref_id, locs in reference_lines.items() if len(locs) > 1)
    if duplicates:
        for ref_id in duplicates:
            add_finding("duplicate_reference_id",
                        f"Reference ID [{ref_id}] is declared more than once.",
                        reference_lines[ref_id], "high")
        add_check("reference_id_uniqueness", "failed",
                  f"Duplicate reference IDs: {', '.join(duplicates)}.")
    elif ref_start is not None:
        add_check("reference_id_uniqueness", "passed", "No duplicate numeric reference IDs.")

    missing = sorted(set(cited) - set(reference_lines))
    if missing:
        for ref_id in missing:
            add_finding("unresolved_citation",
                        f"In-text citation [{ref_id}] has no matching bibliography entry.",
                        cited[ref_id], "high")
        add_check("citation_reference_resolution", "failed",
                  f"Unresolved citation IDs: {', '.join(missing)}.")
    elif ref_start is not None:
        add_check("citation_reference_resolution", "passed",
                  f"All {len(cited)} distinct in-text citation IDs resolve to bibliography entries.")

    unused = sorted(set(reference_lines) - set(cited))
    if unused:
        for ref_id in unused:
            add_finding("unused_reference",
                        f"Bibliography entry [{ref_id}] is not cited in the report body.",
                        reference_lines[ref_id], "low")
        add_check("bibliography_usage", "failed",
                  f"Unused bibliography entries: {', '.join(unused)}.", required=False)
    elif ref_start is not None:
        add_check("bibliography_usage", "passed", "All parsed bibliography entries are cited.", required=False)

    overall = "inconclusive" if ref_start is None else (
        "failed" if missing or duplicates else "passed"
    )
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "schema_version": "0.1.0",
        "product_id": "research-audit",
        "product_version": "0.1.0",
        "run_id": f"researchaudit-{digest[:16]}",
        "created_at": now,
        "input_refs": [str(source.resolve())],
        "input_fingerprints": {"report_sha256": digest},
        "checks": checks,
        "findings": findings,
        "evidence_refs": [evidence_ref],
        "overall_status": overall,
        "summary": {
            "citation_count": sum(len(v) for v in cited.values()),
            "distinct_citations": len(cited),
            "bibliography_entries": len(reference_lines),
            "unresolved_citations": missing,
            "duplicate_reference_ids": duplicates,
            "unused_references": unused,
            "scope": "numeric citation/reference consistency only",
        },
        "provenance": {"input_fingerprints": {"report_sha256": digest}},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit numeric citations in a Markdown report.")
    parser.add_argument("report", help="Markdown report path")
    parser.add_argument("--output", help="Optional JSON report output path")
    args = parser.parse_args()
    try:
        result = audit_markdown(args.report)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
