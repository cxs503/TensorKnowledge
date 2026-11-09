"""KE prototype — consistency validation.

``xref_report`` implements, in SQL over the ingested DB, exactly the
cross-reference invariants of
``platform-test/epistemic-benchmark/pilots/m8554/validate_pilot.py``
(section 2, "cross-reference integrity"):

  I1  every claim.evidence_refs entry resolves to an existing evidence id
  I2  every evidence.claim_refs entry resolves to an existing claim id
  I3  no orphan evidence: every evidence is referenced by >=1 claim
  I4  no claim without evidence: every claim is referenced by >=1 evidence

``schema_report`` mirrors section 1 (jsonschema against the repo schemas,
same five schema files). ``validate_package`` combines both and returns
PASS/FAIL lines in the same (name, ok, detail) shape as the reference
validator, so the two can be diffed line by line.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

try:
    import jsonschema
    from referencing import Registry, Resource
except ImportError:  # pragma: no cover
    jsonschema = None
    Registry = Resource = None

SCHEMA_NAMES = (
    "claim-record",
    "evidence-record",
    "provenance-record",
    "knowledge-object",
    "production-result",
)


def xref_report(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Check invariants I1-I4. Each value is a sorted list of offending ids
    (empty list = invariant holds)."""
    unresolved_claim_refs = [
        (r[0], r[1])
        for r in conn.execute(
            """SELECT DISTINCT ce.claim_id, ce.evidence_id
               FROM claim_evidence ce LEFT JOIN evidence e ON e.id = ce.evidence_id
               WHERE e.id IS NULL ORDER BY 1, 2"""
        )
    ]
    unresolved_evidence_refs = [
        (r[0], r[1])
        for r in conn.execute(
            """SELECT DISTINCT ec.evidence_id, ec.claim_id
               FROM evidence_claims ec LEFT JOIN claims c ON c.id = ec.claim_id
               WHERE c.id IS NULL ORDER BY 1, 2"""
        )
    ]
    orphan_evidence = [
        r[0]
        for r in conn.execute(
            """SELECT e.id FROM evidence e
               WHERE NOT EXISTS (SELECT 1 FROM claim_evidence ce
                                 WHERE ce.evidence_id = e.id)
               ORDER BY e.id"""
        )
    ]
    claims_without_evidence = [
        r[0]
        for r in conn.execute(
            """SELECT c.id FROM claims c
               WHERE NOT EXISTS (SELECT 1 FROM evidence_claims ec
                                 WHERE ec.claim_id = c.id)
               ORDER BY c.id"""
        )
    ]
    return {
        "unresolved_claim_refs": sorted(unresolved_claim_refs),
        "unresolved_evidence_refs": sorted(unresolved_evidence_refs),
        "orphan_evidence": sorted(orphan_evidence),
        "claims_without_evidence": sorted(claims_without_evidence),
    }


def xref_ok(report: dict[str, list[str]]) -> bool:
    return all(len(v) == 0 for v in report.values())


def schema_report(pilot_dir: str | Path) -> list[tuple[str, bool, str]]:
    """Validate every record against its TensorKnowledge schema (same five
    schema files as validate_pilot.py). Returns [(name, ok, detail), ...]."""
    pilot = Path(pilot_dir).resolve()
    repo_root = pilot.parents[3]  # .../pilots/m8554 -> repo root
    schemas_dir = repo_root / "schemas"
    if jsonschema is None:
        return [("deps:jsonschema", False, "jsonschema not installed")]
    if not schemas_dir.is_dir():
        return [("schemas:dir", False, f"schemas dir not found: {schemas_dir}")]

    out: list[tuple[str, bool, str]] = []
    # Local registry: every schema is registered under its $id so that
    # relative $refs (e.g. production-result -> knowledge-object) resolve
    # offline instead of hitting the network.
    registry = Registry()
    schema_docs: dict[str, dict] = {}
    for name in SCHEMA_NAMES:
        doc = json.loads((schemas_dir / f"{name}.schema.json").read_text(encoding="utf-8"))
        schema_docs[name] = doc
        rid = doc.get("$id")
        if rid:
            registry = registry.with_resource(rid, Resource.from_contents(doc))

    def _validate(rec: dict, schema: dict) -> None:
        jsonschema.Draft202012Validator(schema, registry=registry).validate(rec)

    for name in SCHEMA_NAMES:
        schema = schema_docs[name]
        sub = {
            "claim-record": "claims",
            "evidence-record": "evidence",
            "provenance-record": "provenance",
        }.get(name)
        if sub:
            prefix = {"claim-record": "claim", "evidence-record": "evidence",
                      "provenance-record": "provenance"}[name]
            for p in sorted((pilot / sub).glob("*.json")):
                rec = json.loads(p.read_text(encoding="utf-8"))
                try:
                    _validate(rec, schema)
                    out.append((f"schema:{prefix}:{p.stem}", True, ""))
                except jsonschema.ValidationError as e:
                    out.append((f"schema:{prefix}:{p.stem}", False, str(e.message)[:200]))
        elif name == "production-result":
            p = pilot / "production-result.json"
            if p.exists():
                rec = json.loads(p.read_text(encoding="utf-8"))
                try:
                    _validate(rec, schema)
                    out.append((f"schema:production-result:{p.stem}", True, ""))
                except jsonschema.ValidationError as e:
                    out.append((f"schema:production-result:{p.stem}", False, str(e.message)[:200]))
    return out


def validate_package(pilot_dir: str | Path, conn: sqlite3.Connection) -> list[tuple[str, bool, str]]:
    """Combined report: schema checks + xref invariants, PASS/FAIL lines in
    the same shape as validate_pilot.py output."""
    lines: list[tuple[str, bool, str]] = list(schema_report(pilot_dir))
    rep = xref_report(conn)
    lines.append((
        "xref:all_evidence_refs_resolve",
        not rep["unresolved_claim_refs"],
        f"unresolved {rep['unresolved_claim_refs']}",
    ))
    lines.append((
        "xref:all_claim_refs_resolve",
        not rep["unresolved_evidence_refs"],
        f"unresolved {rep['unresolved_evidence_refs']}",
    ))
    lines.append((
        "xref:no_orphan_evidence",
        not rep["orphan_evidence"],
        f"orphan evidence: {rep['orphan_evidence']}",
    ))
    lines.append((
        "xref:no_claim_without_evidence",
        not rep["claims_without_evidence"],
        f"claims w/o evidence: {rep['claims_without_evidence']}",
    ))
    return lines
