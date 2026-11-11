"""KE query interface — six query classes, backend-neutral.

Every query is a single SQL statement over the shared contract
(:mod:`ke.contract`) executed through the facade (:class:`ke.store.Store`), so
results are identical on the authoritative PostgreSQL backend and on the
SQLite fixture.  Results are plain dicts/lists, sorted by record id, hence
deterministic and reproducible.

Two cross-backend semantics are pinned here rather than left to the engine
(see ``docs/ke/backends.md``):

* **ordering** — every ``ORDER BY`` uses :meth:`Store.collate`, i.e. byte
  order on both backends.  PostgreSQL otherwise sorts by database locale
  (``en_US.UTF-8`` ignores punctuation), which would reorder ids containing
  ``:`` or ``-``;
* **substring matching** — ``LOWER(col) LIKE LOWER(?)``: SQLite's ``LIKE`` is
  ASCII case-insensitive, PostgreSQL's is case-sensitive.

Query classes (>=4 required by the task):
  Q1 claims_by_status      — by claim epistemic_status
  Q2 evidence_by_relation  — by evidence relation (supports/refutes/...)
  Q3 provenance_chain      — claim -> evidence -> source chain
  Q4 claims_by_domain      — by scope.domain
  Q5 evidence_for_claim    — evidence attached to one claim (with relation)
  Q6 stats                 — aggregate counts

Extensions (same interface, no extra dialect):
  Q7 gap_anchors / claims_for_gap — gap anchors and the claims they resolve
"""
from __future__ import annotations

import json

from .store import Store


def _rows(conn: Store, sql: str, *args) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def claims_by_status(conn: Store, status: str) -> list[dict]:
    """Q1: claims with the given epistemic_status."""
    order = conn.collate("id")
    return _rows(
        conn,
        f"""SELECT id, statement, claim_type, epistemic_status, domain,
                   evidence_refs_json, source_file
            FROM claims WHERE epistemic_status = ? ORDER BY {order}""",
        status,
    )


def evidence_by_relation(conn: Store, relation: str) -> list[dict]:
    """Q2: evidence with the given relation (supports/refutes/qualifies/...)."""
    order = conn.collate("id")
    return _rows(
        conn,
        f"""SELECT id, relation, assessment_status, source_type, source_url,
                   locator_type, locator_value, source_file
            FROM evidence WHERE relation = ? ORDER BY {order}""",
        relation,
    )


def claims_by_domain(conn: Store, domain: str, exact: bool = True) -> list[dict]:
    """Q4: claims whose scope.domain matches (exact by default, else substring).

    Substring mode case-folds both sides so SQLite (case-insensitive ``LIKE``)
    and PostgreSQL (case-sensitive ``LIKE``) agree on the result set.
    """
    order = conn.collate("id")
    if exact:
        return _rows(
            conn,
            f"""SELECT id, statement, claim_type, epistemic_status, domain, source_file
                FROM claims WHERE domain = ? ORDER BY {order}""",
            domain,
        )
    return _rows(
        conn,
        f"""SELECT id, statement, claim_type, epistemic_status, domain, source_file
            FROM claims WHERE LOWER(domain) LIKE LOWER(?) ORDER BY {order}""",
        f"%{domain}%",
    )


def evidence_for_claim(conn: Store, claim_id: str) -> list[dict]:
    """Q5: evidence linked to a claim via claim.evidence_refs, with relation."""
    order = conn.collate("e.id")
    return _rows(
        conn,
        f"""SELECT e.id, e.relation, e.assessment_status, e.source_type,
                   e.source_url, e.locator_value
            FROM claim_evidence ce JOIN evidence e ON e.id = ce.evidence_id
            WHERE ce.claim_id = ? ORDER BY {order}""",
        claim_id,
    )


def provenance_chain(conn: Store, claim_id: str) -> dict:
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
    order = conn.collate("e.id")
    links = _rows(
        conn,
        f"""SELECT e.id AS evidence_id, e.relation, e.assessment_status,
                   e.source_type, e.source_citation, e.source_url,
                   e.source_persistent_id, e.locator_type, e.locator_value,
                   e.locator_quote, e.source_file AS evidence_source_file
            FROM claim_evidence ce JOIN evidence e ON e.id = ce.evidence_id
            WHERE ce.claim_id = ? ORDER BY {order}""",
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


def stats(conn: Store) -> dict:
    """Q6: aggregate counts (records, edges, status/relation distributions)."""
    def dist(table: str, col: str) -> dict:
        return {
            r[0]: r[1]
            for r in conn.execute(
                f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} "
                f"ORDER BY {conn.collate(col)}"
            )
        }

    def count(table: str) -> int:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    return {
        "claims": count("claims"),
        "evidence": count("evidence"),
        "provenance": count("provenance"),
        "gap_anchors": count("gap_anchors"),
        "claim_evidence_edges": count("claim_evidence"),
        "evidence_claims_edges": count("evidence_claims"),
        "gap_claims_edges": count("gap_claims"),
        "claims_by_status": dist("claims", "epistemic_status"),
        "evidence_by_relation": dist("evidence", "relation"),
        "evidence_by_assessment": dist("evidence", "assessment_status"),
    }


def all_claims(conn: Store) -> list[dict]:
    order = conn.collate("id")
    return _rows(
        conn,
        f"""SELECT id, statement, claim_type, epistemic_status, domain, source_file
            FROM claims ORDER BY {order}""",
    )


def all_evidence(conn: Store) -> list[dict]:
    order = conn.collate("id")
    return _rows(
        conn,
        f"""SELECT id, relation, assessment_status, source_type, source_file
            FROM evidence ORDER BY {order}""",
    )


def all_provenance(conn: Store) -> list[dict]:
    order = conn.collate("id")
    return _rows(
        conn,
        f"""SELECT id, generated_entity_id, entity_type, activity_type, recorded_at,
                   source_file
            FROM provenance ORDER BY {order}""",
    )


def gap_anchors(conn: Store) -> list[dict]:
    """Q7: gap anchors (acceptance gaps declared against the knowledge base)."""
    order = conn.collate("id")
    return _rows(
        conn,
        f"""SELECT id, title, declared_by, summary, resolved_by_claims_json, source_file
            FROM gap_anchors ORDER BY {order}""",
    )


def claims_for_gap(conn: Store, gap_id: str) -> list[dict]:
    """Q7b: claims that resolve (or are anchored to) one gap."""
    order = conn.collate("c.id")
    return _rows(
        conn,
        f"""SELECT c.id, c.epistemic_status, c.statement, c.source_file
            FROM gap_claims gc JOIN claims c ON c.id = gc.claim_id
            WHERE gc.gap_id = ? ORDER BY {order}""",
        gap_id,
    )


def raw_record(conn: Store, kind: str, record_id: str) -> dict:
    """Fetch the exact ingested JSON document for a record (traceability)."""
    table = {"gaps": "gap_anchors"}.get(kind, kind)
    row = conn.execute(
        f"SELECT raw_json FROM {table} WHERE id = ?", (record_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"unknown {kind[:-1]} id: {record_id}")
    return json.loads(row["raw_json"])