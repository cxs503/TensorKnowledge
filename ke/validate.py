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
from pathlib import Path

from .store import Store

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


def xref_report(conn: Store) -> dict[str, list[str]]:
    """Check invariants I1-I4. Each value is a sorted list of offending ids
    (empty list = invariant holds)."""
    # byte-order collation on both backends (see ke.store.Store.collate):
    # PostgreSQL would otherwise sort by database locale, not by byte value
    c1, c2 = conn.collate("ce.claim_id"), conn.collate("ce.evidence_id")
    e1, e2 = conn.collate("ec.evidence_id"), conn.collate("ec.claim_id")
    g1, g2 = conn.collate("gc.gap_id"), conn.collate("gc.claim_id")

    unresolved_claim_refs = [
        (r[0], r[1])
        for r in conn.execute(
            f"""SELECT ce.claim_id, ce.evidence_id
                FROM claim_evidence ce LEFT JOIN evidence e ON e.id = ce.evidence_id
                WHERE e.id IS NULL ORDER BY {c1}, {c2}"""
        )
    ]
    unresolved_evidence_refs = [
        (r[0], r[1])
        for r in conn.execute(
            f"""SELECT ec.evidence_id, ec.claim_id
                FROM evidence_claims ec LEFT JOIN claims c ON c.id = ec.claim_id
                WHERE c.id IS NULL ORDER BY {e1}, {e2}"""
        )
    ]
    oe = conn.collate("e.id")
    orphan_evidence = [
        r[0]
        for r in conn.execute(
            f"""SELECT e.id FROM evidence e
                WHERE NOT EXISTS (SELECT 1 FROM claim_evidence ce
                                  WHERE ce.evidence_id = e.id)
                ORDER BY {oe}"""
        )
    ]
    cw = conn.collate("c.id")
    claims_without_evidence = [
        r[0]
        for r in conn.execute(
            f"""SELECT c.id FROM claims c
                WHERE NOT EXISTS (SELECT 1 FROM evidence_claims ec
                                  WHERE ec.claim_id = c.id)
                ORDER BY {cw}"""
        )
    ]
    # I5 (extension): every gap_claims edge must resolve on both sides
    unresolved_gap_refs = [
        (r[0], r[1])
        for r in conn.execute(
            f"""SELECT gc.gap_id, gc.claim_id
                FROM gap_claims gc
                LEFT JOIN gap_anchors g ON g.id = gc.gap_id
                LEFT JOIN claims c ON c.id = gc.claim_id
                WHERE g.id IS NULL OR c.id IS NULL ORDER BY {g1}, {g2}"""
        )
    ]
    return {
        "unresolved_gap_refs": sorted(unresolved_gap_refs),
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
    # repo root = nearest ancestor carrying the schemas/ directory; this keeps
    # validation working for any package location (pilots/, tests/fixtures/, ...)
    schemas_dir = next(
        (a / "schemas" for a in pilot.parents
         if (a / "schemas" / "claim-record.schema.json").is_file()),
        pilot.parents[3] / "schemas",
    )
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


def validate_package(pilot_dir: str | Path, conn: Store) -> list[tuple[str, bool, str]]:
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
        "xref:all_gap_refs_resolve",
        not rep["unresolved_gap_refs"],
        f"unresolved {rep['unresolved_gap_refs']}",
    ))
    lines.append((
        "xref:no_claim_without_evidence",
        not rep["claims_without_evidence"],
        f"claims w/o evidence: {rep['claims_without_evidence']}",
    ))
    return lines
