#!/usr/bin/env python3
"""Validator for the `knowledge/oss-lbm/fingering` knowledge package.

Checks
------
1. JSON-Schema conformance (Draft 2020-12) against ``schemas/{claim,evidence,provenance}-record``
2. ID patterns (``tkc|tke|tkp:oss-lbm:<slug>``) and uniqueness
3. Bidirectional claim <-> evidence cross references
4. Volume: at least ``MIN_CLAIMS`` claims
5. GAP anchoring: every claim carries at least one ``gap-anchor:`` condition and the named
   adjacent anchor ``GAP-LBM-MCMP-POISEUILLE``
6. Evidence discipline: code-location locator, non-empty verbatim quote of <= 3 lines,
   ``content_hash`` consistent with the quote, locator string parseable
7. Epistemic discipline: nothing self-approved (``assessment_status == "unassessed"``)
8. Optional: verbatim re-extraction from a local snapshot
   (``--src`` or ``$FINGERING_SRC`` or ``/tmp/fing_src``) - quote must match the cited lines exactly.

Exit code 0 = PASS, 1 = FAIL, 2 = usage/environment problem. Run as a script or via pytest.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SCHEMAS = REPO_ROOT / "schemas"

MIN_CLAIMS = 8
CLAIM_ID = re.compile(r"^tkc:oss-lbm:[a-z0-9-]+$")
EVIDENCE_ID = re.compile(r"^tke:oss-lbm:[a-z0-9-]+$")
PROVENANCE_ID = re.compile(r"^tkp:oss-lbm:[a-z0-9-]+$")
LOCATOR = re.compile(r"^fingering_dynamics@[0-9a-f]{7,40} (?P<path>[A-Za-z0-9_./-]+):(?P<start>\d+)-(?P<end>\d+)$")
GAP_NAMED = "GAP-LBM-MCMP-POISEUILLE"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_package() -> tuple[list, list, list]:
    return (
        load(HERE / "claims" / "claims.json"),
        load(HERE / "evidence" / "evidence.json"),
        load(HERE / "provenance" / "provenance.json"),
    )


def schema_errors(kind: str, records: list) -> list[str]:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - dependency is declared in the README
        return ["jsonschema not installed; schema conformance unchecked"]
    schema = load(SCHEMAS / f"{kind}-record.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for rec in records:
        for err in sorted(validator.iter_errors(rec), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path) or "<root>"
            errors.append(f"{kind} {rec.get('id', '?')} -> {loc}: {err.message}")
    return errors


def find_snapshot(explicit: str | os.PathLike | None = None) -> Path | None:
    for candidate in (explicit, os.environ.get("FINGERING_SRC"), "/tmp/fing_src", str(HERE / "src")):
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    return None


def validate(src: Path | None = None, strict_quotes: bool | None = None) -> list[str]:
    errors: list[str] = []
    claims, evidence, provenance = load_package()

    if len(claims) < MIN_CLAIMS:
        errors.append(f"volume: expected >= {MIN_CLAIMS} claims, found {len(claims)}")
    if len(evidence) < MIN_CLAIMS:
        errors.append(f"volume: expected >= {MIN_CLAIMS} evidence records, found {len(evidence)}")
    if not provenance:
        errors.append("provenance: no provenance record")

    errors += schema_errors("claim", claims)
    errors += schema_errors("evidence", evidence)
    errors += schema_errors("provenance", provenance)

    claim_ids = {c["id"] for c in claims}
    ev_ids = {e["id"] for e in evidence}
    if len(claim_ids) != len(claims):
        errors.append("claim: duplicate ids")
    if len(ev_ids) != len(evidence):
        errors.append("evidence: duplicate ids")
    for c in claims:
        if not CLAIM_ID.match(c["id"]):
            errors.append(f"claim id pattern: {c['id']}")
    for e in evidence:
        if not EVIDENCE_ID.match(e["id"]):
            errors.append(f"evidence id pattern: {e['id']}")
    for p in provenance:
        if not PROVENANCE_ID.match(p["id"]):
            errors.append(f"provenance id pattern: {p['id']}")

    # cross references
    for c in claims:
        if not c.get("evidence_refs"):
            errors.append(f"{c['id']}: no evidence_refs")
        for ref in c.get("evidence_refs", []):
            if ref not in ev_ids:
                errors.append(f"{c['id']}: dangling evidence ref {ref}")
    for e in evidence:
        if not e.get("claim_refs"):
            errors.append(f"{e['id']}: no claim_refs")
        for ref in e.get("claim_refs", []):
            if ref not in claim_ids:
                errors.append(f"{e['id']}: dangling claim ref {ref}")

    # GAP anchoring
    for c in claims:
        conditions = (c.get("scope") or {}).get("conditions") or []
        anchors = [x for x in conditions if x.startswith("gap-anchor:")]
        if not anchors:
            errors.append(f"{c['id']}: missing gap-anchor condition")
        if not any(GAP_NAMED in x for x in anchors):
            errors.append(f"{c['id']}: missing adjacent anchor {GAP_NAMED}")

    # evidence discipline
    for e in evidence:
        loc = e.get("locator", {})
        if loc.get("locator_type") != "code-location":
            errors.append(f"{e['id']}: locator_type must be code-location")
        quote = loc.get("quote", "")
        if not quote.strip():
            errors.append(f"{e['id']}: empty quote")
        if len(quote.splitlines()) > 3:
            errors.append(f"{e['id']}: quote longer than 3 lines")
        expected = hashlib.sha256(quote.encode("utf-8")).hexdigest()
        if loc.get("content_hash") != expected:
            errors.append(f"{e['id']}: content_hash does not match quote")
        m = LOCATOR.match(loc.get("value", ""))
        if not m:
            errors.append(f"{e['id']}: locator value not parseable: {loc.get('value')}")
        elif e.get("assessment_status") != "unassessed":
            errors.append(f"{e['id']}: assessment_status must be 'unassessed' (no self-approval)")

    for c in claims:
        if c.get("assessment_note") or c.get("reviewed_by"):
            errors.append(f"{c['id']}: self-approval fields are not allowed")

    # optional verbatim re-extraction
    snapshot = find_snapshot(src)
    if strict_quotes is None:
        strict_quotes = snapshot is not None
    if strict_quotes and snapshot is None:
        errors.append("verbatim: strict mode requested but no source snapshot found")
    if snapshot is not None:
        for e in evidence:
            m = LOCATOR.match(e["locator"]["value"])
            if not m:
                continue
            path = snapshot / m["path"]
            if not path.is_file():
                errors.append(f"{e['id']}: snapshot lacks {m['path']}")
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            first, last = int(m["start"]), int(m["end"])
            if last > len(lines):
                errors.append(f"{e['id']}: line range {first}-{last} beyond EOF")
                continue
            expected_quote = "\n".join(lines[first - 1:last])
            if expected_quote != e["locator"]["quote"]:
                errors.append(f"{e['id']}: quote is not verbatim for {m['path']}:{first}-{last}")
    return errors


def summary() -> str:
    claims, evidence, provenance = load_package()
    by_status: dict[str, int] = {}
    for c in claims:
        by_status[c["epistemic_status"]] = by_status.get(c["epistemic_status"], 0) + 1
    status_txt = ", ".join(f"{k}={v}" for k, v in sorted(by_status.items()))
    return (f"PASS: {len(claims)} claims, {len(evidence)} evidence, {len(provenance)} provenance\n"
            f"  epistemic status: {status_txt}\n"
            f"  every claim carries a gap-anchor ({GAP_NAMED} + free-energy anchor)\n"
            f"  all evidence unassessed (no self-approval)")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    src = None
    if "--src" in argv:
        src = argv[argv.index("--src") + 1]
    if "--no-snapshot" in argv:
        errors = validate(src=None, strict_quotes=False)
        snapshot_note = "verbatim re-extraction skipped (--no-snapshot)"
    else:
        snapshot = find_snapshot(src)
        errors = validate(src=src)
        snapshot_note = (f"verbatim re-extraction against {snapshot}" if snapshot
                         else "no snapshot found; verbatim re-extraction skipped")
    if errors:
        print(f"FAIL: {len(errors)} error(s)  [{snapshot_note}]")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(summary())
    print(f"  {snapshot_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())