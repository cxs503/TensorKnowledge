#!/usr/bin/env python3
"""Scan every kf_result envelope in a worktree against a kf_result schema.

Why: `schemas/kf_result.v1.schema.json` is a shared contract file consumed by
~130 packages (01..05 工序).  Envelope producers kept adding optional producer
fields (claims / provenance.producer / provenance.notes / emitted_at) while the
schema kept `additionalProperties: false`, so envelopes that were generated
correctly still failed `jsonschema` validation — a silent contract drift that a
single package test only reported one error at a time.

This scanner is the repo-wide counterpart of a per-package schema test: it
validates every envelope, groups the failures by (validator, offending path)
and (optionally) diffs two schemas, so a schema change can be audited as
additive vs. breaking before it lands.

Determinism: no wall-clock, no absolute paths, sorted ordering -> the emitted
JSON is byte-reproducible for a given worktree + schema pair.

Usage
-----
    python3 scripts/kf/schema_conformance_scan.py \
        --schema schemas/kf_result.v1.schema.json \
        --baseline-schema /tmp/kf_result.v1.baseline.json \
        --out docs/kf/wp-459-01/schema_conformance.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:  # keep the scanner usable without jsonschema installed
    import jsonschema
except ImportError:  # pragma: no cover - dependency is present in CI
    jsonschema = None

DEFAULT_ROOTS = ("docs/kf", "runs", "work")
ENVELOPE_MARKERS = ("package_id", "task_type", "report_id")
# the scan targets kf_result envelopes only: the file name is part of the
# contract for locating them (kf_result.json / kf_result.<pkg>.json), while
# asset_manifest.json / review_report.json are different contracts that happen
# to reuse package_id / report_id / provenance keys.
ENVELOPE_STEM = "kf_result"


def iter_envelope_paths(roots, repo_root: Path):
    """Yield envelope candidate paths, sorted, without following symlinks."""
    seen = set()
    for root in roots:
        base = repo_root / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.json")):
            if not path.is_file():
                continue
            if path.name.endswith(".schema.json"):
                continue  # a schema file, not an envelope instance
            rel = path.relative_to(repo_root).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            yield rel, path


def classify(path: Path) -> tuple[str, dict | None]:
    """Return ("envelope"|"not_envelope"|"invalid_json", parsed)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "invalid_json", None
    if not path.name.startswith(ENVELOPE_STEM):
        return "not_envelope", data
    if not isinstance(data, dict):
        return "not_envelope", data
    if not any(marker in data for marker in ENVELOPE_MARKERS):
        return "not_envelope", data
    return "envelope", data


def error_key(err) -> tuple[str, str, str]:
    """Group errors by (validator, json-pointer-ish path, message family)."""
    where = "/".join(str(p) for p in err.absolute_path) or "<root>"
    message = err.message
    # keep the message, but cut volatile property lists so grouping is stable
    return err.validator, where, message


def scan(schema_path: Path, repo_root: Path, roots) -> dict:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    total_envelopes = 0
    valid = 0
    valid_paths: list[str] = []
    groups: dict[tuple[str, str, str], list[str]] = {}
    not_envelope: list[str] = []
    invalid_json: list[str] = []
    for rel, path in iter_envelope_paths(roots, repo_root):
        kind, data = classify(path)
        if kind == "invalid_json":
            invalid_json.append(rel)
            continue
        if kind == "not_envelope":
            not_envelope.append(rel)
            continue
        total_envelopes += 1
        errors = sorted(validator.iter_errors(data), key=lambda e: (list(map(str, e.absolute_path)), e.validator, e.message))
        if not errors:
            valid += 1
            valid_paths.append(rel)
            continue
        for err in errors:
            groups.setdefault(error_key(err), []).append(rel)
    findings = [
        {
            "validator": key[0],
            "path": key[1],
            "message": key[2],
            "count": len(paths),
            "examples": sorted(set(paths))[:5],
        }
        for key, paths in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]
    return {
        "schema": schema_path.name,
        "envelopes_scanned": total_envelopes,
        "envelopes_valid": valid,
        "envelopes_invalid": total_envelopes - valid,
        "valid_paths": sorted(valid_paths),
        "invalid_json": sorted(invalid_json),
        "skipped_not_envelope": len(not_envelope),
        "finding_count": len(findings),
        "findings": findings,
    }


def summarize(scan_result: dict) -> dict:
    """Compact digest used when comparing two schemas (drops per-file detail)."""
    return {
        "schema": scan_result["schema"],
        "envelopes_scanned": scan_result["envelopes_scanned"],
        "envelopes_valid": scan_result["envelopes_valid"],
        "envelopes_invalid": scan_result["envelopes_invalid"],
        "finding_count": scan_result["finding_count"],
        "invalid_json": len(scan_result["invalid_json"]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", required=True, help="schema to validate against")
    ap.add_argument("--baseline-schema", default=None, help="older schema to diff against (additive check)")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--roots", nargs="*", default=list(DEFAULT_ROOTS))
    ap.add_argument("--out", default=None, help="write the JSON report here (else stdout)")
    ap.add_argument("--package-id", default=None, help="label stamped into the report")
    ap.add_argument("--max-findings", type=int, default=40)
    args = ap.parse_args(argv)

    if jsonschema is None:  # pragma: no cover
        print("jsonschema is required", file=sys.stderr)
        return 2

    repo_root = Path(args.repo_root).resolve()
    current = scan(Path(args.schema), repo_root, args.roots)
    report: dict = {
        "report": "kf_result schema conformance scan",
        "package_id": args.package_id,
        "roots": list(args.roots),
        "current": {**summarize(current), "findings": current["findings"][: args.max_findings]},
    }
    if args.baseline_schema:
        baseline = scan(Path(args.baseline_schema), repo_root, args.roots)
        report["baseline"] = {**summarize(baseline), "findings": baseline["findings"][: args.max_findings]}
        reverted = sorted(set(baseline["valid_paths"]) - set(current["valid_paths"]))
        report["delta"] = {
            "valid_before": baseline["envelopes_valid"],
            "valid_after": current["envelopes_valid"],
            "newly_valid": current["envelopes_valid"] - baseline["envelopes_valid"],
            "scanned_before": baseline["envelopes_scanned"],
            "scanned_after": current["envelopes_scanned"],
            "findings_before": baseline["finding_count"],
            "findings_after": current["finding_count"],
            # additive-only evidence: an envelope that validated before must still validate
            "regressions": reverted,
            "additive_only": not reverted,
        }

    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"wrote {out_path} ({current['envelopes_valid']}/{current['envelopes_scanned']} envelopes valid)")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())