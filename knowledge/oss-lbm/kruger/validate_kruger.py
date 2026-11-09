#!/usr/bin/env python3
"""Validator for the Kruger (OSS-LBM A-line extension) knowledge package.

Checks
  1. JSON parse + JSON Schema (Draft 2020-12) conformance against ../.../schemas
  2. Identifier patterns and uniqueness
  3. Bidirectional claim <-> evidence cross-references
  4. Count / shape constraints: >= 8 claims, every claim has evidence and a GAP anchor
  5. Epistemic discipline: no self-approval (assessment_status unassessed / insufficient),
     no review events, draft-only package
  6. Verbatim integrity: each code-location quote must equal the span recorded in
     artifacts/oss-lbm-kruger/kruger_source_index.json, and the locator line numbers
     must match that span
  7. Provenance linkage: generated_entity, gap anchor registration, cache status

Exit code 0 = PASS.  No network access, no upstream checkout required.
Run:  python validate_kruger.py [-v]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCHEMAS = ROOT / "schemas"
INDEX = ROOT / "artifacts" / "oss-lbm-kruger" / "kruger_source_index.json"
GAP_FILE = HERE / "GAP-ANCHORS.md"

CLAIM_RE = re.compile(r"^tkc:oss-lbm:[a-z0-9][a-z0-9-]*$")
EVIDENCE_RE = re.compile(r"^tke:oss-lbm:[a-z0-9][a-z0-9-]*$")
PROVENANCE_RE = re.compile(r"^tkp:oss-lbm:[a-z0-9][a-z0-9-]*$")
LOCATOR_RE = re.compile(r"^(?P<repo>[^\s@]+)@(?P<commit>[0-9a-f]{7,40}) (?P<path>\S+):(?P<l0>\d+)-(?P<l1>\d+)$")
ALLOWED_STATUS = {"established", "well-supported", "provisional", "contested", "speculative",
                  "superseded", "not-assessed"}
ALLOWED_ASSESSMENT = {"unassessed", "reviewed-supports", "reviewed-refutes", "reviewed-qualifies",
                      "insufficient", "disputed"}
MIN_CLAIMS = 8
MAX_QUOTE_LINES = 3
MAX_QUOTE_CHARS = 1200


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_schema(obj, schema_name: str, errors: list[str], label: str) -> None:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        errors.append("jsonschema not installed; schema conformance unchecked")
        return
    schema = load(SCHEMAS / schema_name)
    validator = jsonschema.Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
        errors.append(f"{label}: schema violation at {list(err.path)}: {err.message}")


def main(argv: list[str] | None = None) -> int:
    verbose = "-v" in (argv if argv is not None else sys.argv[1:])
    errors: list[str] = []
    notes: list[str] = []

    claims = load(HERE / "claims" / "claims.json")
    evidence = load(HERE / "evidence" / "evidence.json")
    provenance = load(HERE / "provenance" / "provenance.json")
    index = load(INDEX) if INDEX.exists() else {"files": {}}
    if not INDEX.exists():
        errors.append(f"missing source index {INDEX.relative_to(ROOT)} (run build_claims.py)")

    for c in claims:
        check_schema(c, "claim-record.schema.json", errors, f"claim {c.get('id', '?')}")
    for e in evidence:
        check_schema(e, "evidence-record.schema.json", errors, f"evidence {e.get('id', '?')}")
    for p in provenance:
        check_schema(p, "provenance-record.schema.json", errors, f"provenance {p.get('id', '?')}")

    # counts
    if len(claims) < MIN_CLAIMS:
        errors.append(f"expected >= {MIN_CLAIMS} claims, found {len(claims)}")
    notes.append(f"claims: {len(claims)}, evidence: {len(evidence)}, provenance: {len(provenance)}")

    # ids
    for c in claims:
        if not CLAIM_RE.match(c["id"]):
            errors.append(f"claim id malformed: {c['id']}")
    for e in evidence:
        if not EVIDENCE_RE.match(e["id"]):
            errors.append(f"evidence id malformed: {e['id']}")
    for p in provenance:
        if not PROVENANCE_RE.match(p["id"]):
            errors.append(f"provenance id malformed: {p['id']}")
    if len({c["id"] for c in claims}) != len(claims):
        errors.append("duplicate claim ids")
    if len({e["id"] for e in evidence}) != len(evidence):
        errors.append("duplicate evidence ids")

    claim_ids = {c["id"] for c in claims}
    ev_ids = {e["id"] for e in evidence}

    # cross references
    for c in claims:
        refs = c.get("evidence_refs") or []
        if not refs:
            errors.append(f"claim {c['id']} has no evidence_refs")
        for r in refs:
            if r not in ev_ids:
                errors.append(f"claim {c['id']} references missing evidence {r}")
    for e in evidence:
        refs = e.get("claim_refs") or []
        if not refs:
            errors.append(f"evidence {e['id']} has no claim_refs")
        for r in refs:
            if r not in claim_ids:
                errors.append(f"evidence {e['id']} references missing claim {r}")
            else:
                owner = next(c for c in claims if c["id"] == r)
                if e["id"] not in owner.get("evidence_refs", []):
                    errors.append(f"asymmetric link: {r} does not list {e['id']}")

    # epistemic discipline
    for c in claims:
        if c.get("epistemic_status") not in ALLOWED_STATUS:
            errors.append(f"claim {c['id']} has invalid epistemic_status {c.get('epistemic_status')!r}")
    for e in evidence:
        if e.get("assessment_status") not in ALLOWED_ASSESSMENT:
            errors.append(f"evidence {e['id']} has invalid assessment_status")
        if e.get("assessment_status") not in ("unassessed", "insufficient"):
            errors.append(f"evidence {e['id']} carries a self-assessment ({e['assessment_status']}); "
                          "the package must stay draft until an independent reviewer signs off")
        loc = e.get("locator", {})
        quote = loc.get("quote", "")
        if len(quote.splitlines()) > MAX_QUOTE_LINES:
            errors.append(f"evidence {e['id']} quote exceeds {MAX_QUOTE_LINES} lines")
        if len(quote) > MAX_QUOTE_CHARS:
            errors.append(f"evidence {e['id']} quote exceeds {MAX_QUOTE_CHARS} chars")
        if loc.get("locator_type") == "code-location" and not LOCATOR_RE.match(loc.get("value", "")):
            errors.append(f"evidence {e['id']} locator value not repo@commit path:l0-l1: {loc.get('value')!r}")
    if (HERE / "review-events").exists():
        errors.append("review-events directory present; the package must remain draft-only")

    # GAP anchors: every claim must name one, and it must be registered
    gap_registry = GAP_FILE.read_text(encoding="utf-8") if GAP_FILE.exists() else ""
    if not GAP_FILE.exists():
        errors.append(f"missing {GAP_FILE.name} (GAP anchor registry)")
    anchors_used = set()
    for c in claims:
        txt = " ".join(c.get("notes", []))
        found = re.findall(r"GAP-[A-Z0-9-]+", txt)
        if not found:
            errors.append(f"claim {c['id']} has no GAP anchor in notes")
            continue
        for a in found:
            anchors_used.add(a)
            if a not in gap_registry:
                errors.append(f"claim {c['id']} uses unregistered GAP anchor {a}")
        if "GAP-LBM-BENCH-METHODOLOGY" not in found:
            errors.append(f"claim {c['id']} must anchor to GAP-LBM-BENCH-METHODOLOGY")
    if anchors_used:
        notes.append(f"GAP anchors used: {', '.join(sorted(anchors_used))}")

    # verbatim integrity against the source index
    files = index.get("files", {})
    commit_prefix = index.get("commit_short") or (index.get("commit") or "")[:7]
    checked = 0
    for e in evidence:
        loc = e.get("locator", {})
        if loc.get("locator_type") != "code-location":
            continue
        m = LOCATOR_RE.match(loc.get("value", ""))
        if not m:
            continue
        path, l0, l1 = m.group("path"), int(m.group("l0")), int(m.group("l1"))
        if commit_prefix and m.group("commit") != commit_prefix:
            errors.append(f"evidence {e['id']} locator commit {m.group('commit')} != index {commit_prefix}")
        entry = files.get(path)
        if entry is None:
            errors.append(f"evidence {e['id']} path {path} absent from source index")
            continue
        span = next((s for s in entry["quoted_spans"]
                     if s["line_start"] == l0 and s["line_end"] == l1), None)
        if span is None:
            errors.append(f"evidence {e['id']} locator {path}:{l0}-{l1} not found in source index")
            continue
        if span["quote"] != loc.get("quote"):
            errors.append(f"evidence {e['id']} quote differs from the recorded upstream span "
                          f"({path}:{l0}-{l1})")
        checked += 1
    notes.append(f"verbatim quotes re-checked against source index: {checked}")

    # provenance linkage
    entity = provenance[0].get("generated_entity", {}).get("id")
    if entity != "knowledge/oss-lbm/kruger":
        errors.append(f"provenance generated_entity {entity!r} != knowledge/oss-lbm/kruger")
    ext = provenance[0].get("extensions", {})
    if "GAP-LBM-BENCH-METHODOLOGY" not in ext.get("gap_anchors", []):
        errors.append("provenance extensions.gap_anchors must list GAP-LBM-BENCH-METHODOLOGY")
    cache = ext.get("source_cache_status", "")
    if not cache:
        errors.append("provenance extensions.source_cache_status missing (cache availability must be recorded)")
    elif "insufficient" not in cache:
        notes.append("cache status recorded as available")
    used = " ".join(provenance[0].get("activity", {}).get("used_entities", []))
    if index.get("commit") and index["commit"] not in used:
        errors.append("provenance used_entities does not pin the full upstream commit")

    if verbose or errors:
        print(f"package: {HERE.relative_to(ROOT)}")
        print(f"upstream: {index.get('repo')}@{index.get('commit_short')} "
              f"({len(files)} files quoted, sha256 pinned)")
        for n in notes:
            print(f"  - {n}")
    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  ! {e}")
        return 1
    print("PASS: Kruger claim package is schema-valid, cross-referenced, draft-only, "
          "quote-verified and GAP-anchored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())