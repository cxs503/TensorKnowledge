"""KE prototype — typed queries over the ingested pilot package.

All queries return plain dicts/lists, sorted by record id, so results are
deterministic and reproducible (pytest pins the exact expected sets).

Query classes (>=4 required by the task):
  Q1 claims_by_status      — by claim epistemic_status
  Q2 evidence_by_relation  — by evidence relation (supports/refutes/...)
  Q3 provenance_chain      — claim -> evidence -> source chain
  Q4 claims_by_domain      — by scope.domain
  Q5 evidence_for_claim    — evidence attached to one claim (with relation)
  Q6 stats                 — aggregate counts
"""
from __future__ import annotations

import json
import sqlite3


def _rows(conn: sqlite3.Connection, sql: str, *args) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def claims_by_status(conn: sqlite3.Connection, status: str) -> list[dict]:
    """Q1: claims with the given epistemic_status."""
    return _rows(
        conn,
        """SELECT id, statement, claim_type, epistemic_status, domain,
                  evidence_refs_json, source_file
           FROM claims WHERE epistemic_status = ? ORDER BY id""",
        status,
    )


def evidence_by_relation(conn: sqlite3.Connection, relation: str) -> list[dict]:
    """Q2: evidence with the given relation (supports/refutes/qualifies/...)."""
    return _rows(
        conn,
        """SELECT id, relation, assessment_status, source_type, source_url,
                  locator_type, locator_value, source_file
           FROM evidence WHERE relation = ? ORDER BY id""",
        relation,
    )


def claims_by_domain(conn: sqlite3.Connection, domain: str, exact: bool = True) -> list[dict]:
    """Q4: claims whose scope.domain matches (exact by default, else LIKE %domain%)."""
    if exact:
        return _rows(
            conn,
            """SELECT id, statement, claim_type, epistemic_status, domain, source_file
               FROM claims WHERE domain = ? ORDER BY id""",
            domain,
        )
    return _rows(
        conn,
        """SELECT id, statement, claim_type, epistemic_status, domain, source_file
           FROM claims WHERE domain LIKE ? ORDER BY id""",
        f"%{domain}%",
    )


def evidence_for_claim(conn: sqlite3.Connection, claim_id: str) -> list[dict]:
    """Q5: evidence linked to a claim via claim.evidence_refs, with relation."""
    return _rows(
        conn,
        """SELECT e.id, e.relation, e.assessment_status, e.source_type,
                  e.source_url, e.locator_value
           FROM claim_evidence ce JOIN evidence e ON e.id = ce.evidence_id
           WHERE ce.claim_id = ? ORDER BY e.id""",
        claim_id,
    )


def provenance_chain(conn: sqlite3.Connection, claim_id: str) -> dict:
    """Q3: full provenance chain claim -> evidence -> source for one claim.

    Returns {"claim": {...}, "links": [{evidence, source, locator}, ...]}.
    Raises KeyError if the claim is unknown.
    """
    claim = conn.execute(
        "SELECT id, statement, claim_type, epistemic_status, domain, source_file "
        "FROM claims WHERE id = ?",
        (claim_id,),
    ).fetchone()
    if claim is None:
        raise KeyError(f"unknown claim id: {claim_id}")
    links = _rows(
        conn,
        """SELECT e.id AS evidence_id, e.relation, e.assessment_status,
                  e.source_type, e.source_citation, e.source_url,
                  e.source_persistent_id, e.locator_type, e.locator_value,
                  e.locator_quote, e.source_file AS evidence_source_file
           FROM claim_evidence ce JOIN evidence e ON e.id = ce.evidence_id
           WHERE ce.claim_id = ? ORDER BY e.id""",
        claim_id,
    )
    for link in links:
        link["source"] = {
            "source_type": link.pop("source_type"),
            "citation": link.pop("source_citation"),
            "url": link.pop("source_url"),
            "persistent_id": link.pop("source_persistent_id"),
        }
        link["locator"] = {
            "locator_type": link.pop("locator_type"),
            "value": link.pop("locator_value"),
            "quote": link.pop("locator_quote"),
        }
    return {"claim": dict(claim), "links": links}


def stats(conn: sqlite3.Connection) -> dict:
    """Q6: aggregate counts (records, edges, status/relation distributions)."""
    def dist(table: str, col: str) -> dict:
        return {
            r[0]: r[1]
            for r in conn.execute(
                f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} ORDER BY {col}"
            )
        }

    return {
        "claims": conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0],
        "evidence": conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],
        "provenance": conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0],
        "claim_evidence_edges": conn.execute(
            "SELECT COUNT(*) FROM claim_evidence"
        ).fetchone()[0],
        "evidence_claims_edges": conn.execute(
            "SELECT COUNT(*) FROM evidence_claims"
        ).fetchone()[0],
        "claims_by_status": dist("claims", "epistemic_status"),
        "evidence_by_relation": dist("evidence", "relation"),
        "evidence_by_assessment": dist("evidence", "assessment_status"),
    }


def all_claims(conn: sqlite3.Connection) -> list[dict]:
    return _rows(
        conn,
        """SELECT id, statement, claim_type, epistemic_status, domain, source_file
           FROM claims ORDER BY id"""
    )


def all_evidence(conn: sqlite3.Connection) -> list[dict]:
    return _rows(
        conn,
        """SELECT id, relation, assessment_status, source_type, source_file
           FROM evidence ORDER BY id"""
    )


def all_provenance(conn: sqlite3.Connection) -> list[dict]:
    return _rows(
        conn,
        """SELECT id, generated_entity_id, entity_type, activity_type, recorded_at,
                  source_file
           FROM provenance ORDER BY id"""
    )


def raw_record(conn: sqlite3.Connection, kind: str, record_id: str) -> dict:
    """Fetch the exact ingested JSON document for a record (traceability)."""
    row = conn.execute(
        f"SELECT raw_json FROM {kind} WHERE id = ?", (record_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"unknown {kind[:-1]} id: {record_id}")
    return json.loads(row["raw_json"])
