"""KE prototype — SQLite storage layer (stdlib only, zero hand-copying).

Ingests a pilot package of epistemic records into SQLite:

    <pilot>/claims/*.json       -> claims
    <pilot>/evidence/*.json     -> evidence
    <pilot>/provenance/*.json   -> provenance

Design rules
------------
* ``raw_json`` keeps the exact ingested document, so every query result
  is traceable back to the source bytes (provenance discipline).
* Cross-reference fields (``claim.evidence_refs`` / ``evidence.claim_refs``)
  are normalized into join tables ``claim_evidence`` / ``evidence_claims``
  so the xref invariants of ``pilots/m8554/validate_pilot.py`` can be
  checked with plain SQL.
* Ingest is idempotent per (db, pilot): re-ingesting the same package
  replaces the previous state (DELETE + re-INSERT, single transaction).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    id               TEXT PRIMARY KEY,
    statement        TEXT NOT NULL,
    claim_type       TEXT NOT NULL,
    epistemic_status TEXT NOT NULL,
    modality         TEXT,
    domain           TEXT,
    scope_json       TEXT,
    evidence_refs_json TEXT NOT NULL,
    valid_time_json  TEXT,
    created_at       TEXT NOT NULL,
    created_by       TEXT,
    version          TEXT NOT NULL,
    notes_json       TEXT,
    source_file      TEXT NOT NULL,
    raw_json         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
    id                  TEXT PRIMARY KEY,
    relation            TEXT NOT NULL,
    assessment_status   TEXT NOT NULL,
    source_type         TEXT,
    source_citation     TEXT,
    source_url          TEXT,
    source_persistent_id TEXT,
    locator_type        TEXT,
    locator_value       TEXT,
    locator_quote       TEXT,
    extraction_method   TEXT,
    captured_at         TEXT NOT NULL,
    captured_by         TEXT,
    version             TEXT NOT NULL,
    source_file         TEXT NOT NULL,
    raw_json            TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provenance (
    id                  TEXT PRIMARY KEY,
    generated_entity_id TEXT,
    entity_type         TEXT,
    activity_id         TEXT,
    activity_type       TEXT,
    attributed_to_json  TEXT,
    derived_from_json   TEXT,
    recorded_at         TEXT NOT NULL,
    version             TEXT NOT NULL,
    source_file         TEXT NOT NULL,
    raw_json            TEXT NOT NULL
);
-- NOTE: no FK constraints on the join tables on purpose. Unresolvable refs
-- must be *storable* so the xref invariants (ke.validate.xref_report,
-- mirroring validate_pilot.py) can detect and report them. Enforcing them
-- here would make the validator vacuous.
CREATE TABLE IF NOT EXISTS claim_evidence (
    claim_id    TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (claim_id, evidence_id)
);
CREATE TABLE IF NOT EXISTS evidence_claims (
    evidence_id TEXT NOT NULL,
    claim_id    TEXT NOT NULL,
    PRIMARY KEY (evidence_id, claim_id)
);
CREATE TABLE IF NOT EXISTS ingest_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect(db_path: str | Path = ":memory:") -> sqlite3.Connection:
    """Open (and initialize) the KE database. ``:memory:`` supported."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def _jdump(obj: Any) -> str | None:
    return None if obj is None else json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _load_dir(pilot: Path, sub: str) -> dict[str, tuple[dict, str]]:
    """Load <pilot>/<sub>/*.json -> {record_id: (record, rel_source_file)}."""
    out: dict[str, tuple[dict, str]] = {}
    d = pilot / sub
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        rid = rec.get("id")
        if not rid:
            raise ValueError(f"record without id: {p}")
        if rid in out:
            raise ValueError(f"duplicate record id {rid!r} in {d}")
        out[rid] = (rec, str(p.relative_to(pilot)))
    return out


def ingest_pilot(pilot_dir: str | Path, conn: sqlite3.Connection) -> dict[str, int]:
    """Ingest one pilot package into ``conn``. Returns record counts.

    Idempotent: previous rows for the same pilot are removed first.
    """
    pilot = Path(pilot_dir).resolve()
    if not pilot.is_dir():
        raise FileNotFoundError(f"pilot dir not found: {pilot}")

    claims = _load_dir(pilot, "claims")
    evidence = _load_dir(pilot, "evidence")
    provenance = _load_dir(pilot, "provenance")

    with conn:  # single transaction
        conn.execute("DELETE FROM claim_evidence")
        conn.execute("DELETE FROM evidence_claims")
        conn.execute("DELETE FROM claims")
        conn.execute("DELETE FROM evidence")
        conn.execute("DELETE FROM provenance")
        conn.execute("DELETE FROM ingest_meta")

        for rid, (rec, src) in claims.items():
            scope = rec.get("scope") or {}
            conn.execute(
                """INSERT INTO claims (id, statement, claim_type, epistemic_status,
                       modality, domain, scope_json, evidence_refs_json, valid_time_json,
                       created_at, created_by, version, notes_json, source_file, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rid,
                    rec["statement"],
                    rec["claim_type"],
                    rec["epistemic_status"],
                    rec.get("modality"),
                    scope.get("domain"),
                    _jdump(scope),
                    json.dumps(rec.get("evidence_refs", []), ensure_ascii=False),
                    _jdump(rec.get("valid_time")),
                    rec["created_at"],
                    rec.get("created_by"),
                    rec["version"],
                    _jdump(rec.get("notes")),
                    src,
                    json.dumps(rec, ensure_ascii=False, sort_keys=True),
                ),
            )
        for eid, (rec, src) in evidence.items():
            src_obj = rec.get("source") or {}
            loc = rec.get("locator") or {}
            conn.execute(
                """INSERT INTO evidence (id, relation, assessment_status, source_type,
                       source_citation, source_url, source_persistent_id, locator_type,
                       locator_value, locator_quote, extraction_method, captured_at,
                       captured_by, version, source_file, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    eid,
                    rec["relation"],
                    rec["assessment_status"],
                    src_obj.get("source_type"),
                    src_obj.get("citation"),
                    src_obj.get("url"),
                    src_obj.get("persistent_id"),
                    loc.get("locator_type"),
                    loc.get("value"),
                    loc.get("quote"),
                    rec.get("extraction_method"),
                    rec["captured_at"],
                    rec.get("captured_by"),
                    rec["version"],
                    src,
                    json.dumps(rec, ensure_ascii=False, sort_keys=True),
                ),
            )
        for pid, (rec, src) in provenance.items():
            ge = rec.get("generated_entity") or {}
            act = rec.get("activity") or {}
            conn.execute(
                """INSERT INTO provenance (id, generated_entity_id, entity_type,
                       activity_id, activity_type, attributed_to_json, derived_from_json,
                       recorded_at, version, source_file, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    pid,
                    ge.get("id"),
                    ge.get("entity_type"),
                    act.get("id"),
                    act.get("activity_type"),
                    _jdump(rec.get("attributed_to")),
                    _jdump(rec.get("derived_from")),
                    rec["recorded_at"],
                    rec["version"],
                    src,
                    json.dumps(rec, ensure_ascii=False, sort_keys=True),
                ),
            )

        # join tables last: base rows must exist for FK integrity
        for rid, (rec, _src) in claims.items():
            for eref in rec.get("evidence_refs", []):
                conn.execute(
                    "INSERT OR IGNORE INTO claim_evidence (claim_id, evidence_id) VALUES (?,?)",
                    (rid, eref),
                )
        for eid, (rec, _src) in evidence.items():
            for cref in rec.get("claim_refs", []):
                conn.execute(
                    "INSERT OR IGNORE INTO evidence_claims (evidence_id, claim_id) VALUES (?,?)",
                    (eid, cref),
                )

        conn.execute(
            "INSERT INTO ingest_meta (key, value) VALUES ('pilot_dir', ?)",
            (str(pilot),),
        )
        conn.execute(
            "INSERT INTO ingest_meta (key, value) VALUES ('record_counts', ?)",
            (
                json.dumps(
                    {
                        "claims": len(claims),
                        "evidence": len(evidence),
                        "provenance": len(provenance),
                    },
                    sort_keys=True,
                ),
            ),
        )
    return {
        "claims": len(claims),
        "evidence": len(evidence),
        "provenance": len(provenance),
    }
