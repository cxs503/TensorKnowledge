"""KE data contract — one schema, one ingest path, two backends.

This module is the *single* definition of the Knowledge Engine's persistence
contract.  ``ke.store`` (the facade) provides the backend-specific connection
handling (psycopg for PostgreSQL, sqlite3 for the lightweight fixture); this
module never talks dialect-specific SQL beyond the tiny subset that both
engines accept verbatim (``TEXT`` / ``NOT NULL`` / ``PRIMARY KEY`` /
``CREATE TABLE IF NOT EXISTS``).

Four record contracts are ingested (the four payload classes that exist in
``knowledge/oss-lbm/``):

===========  ==============================  =================================
kind         source glob                      table(s)
===========  ==============================  =================================
claims       ``**/claims(.json|/*.json)``     ``claims``
evidence     ``**/evidence(.json|/*.json)``   ``evidence``
provenance   ``**/provenance(.json|/*.json)`` ``provenance``
gaps         ``**/gaps/*.json``, ``**/gap-anchors.json``
                                             ``gap_anchors`` + ``gap_claims``
===========  ==============================  =================================

Cross references (``claim.evidence_refs``, ``evidence.claim_refs``,
``claim.gap_anchors``, ``gap.resolved_by_claims``) are normalized into join
tables so the xref invariants of ``ke.validate`` (mirroring
``pilots/m8554/validate_pilot.py`` §2) can be checked with plain SQL.  No FK
constraints on purpose: unresolvable references must be *storable* so the
validator can detect and report them instead of the store rejecting them.

Every row keeps ``raw_json`` = the exact ingested document, so each query
result is traceable back to the source bytes (zero hand-copying).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, NamedTuple

# --------------------------------------------------------------------------
# 1. The contract: tables, columns, primary keys
# --------------------------------------------------------------------------
#: table -> [(column, sql_type_spec), ...].  All payload columns are TEXT so
#: that SQLite and PostgreSQL return byte-identical values (no numeric/JSON
#: coercion differences between the two backends).
COLUMNS: dict[str, list[tuple[str, str]]] = {
    "claims": [
        ("id", "TEXT PRIMARY KEY"),
        ("statement", "TEXT NOT NULL"),
        ("claim_type", "TEXT NOT NULL"),
        ("epistemic_status", "TEXT NOT NULL"),
        ("modality", "TEXT"),
        ("domain", "TEXT"),
        ("scope_json", "TEXT"),
        ("evidence_refs_json", "TEXT NOT NULL"),
        ("gap_anchors_json", "TEXT"),
        ("valid_time_json", "TEXT"),
        ("created_at", "TEXT NOT NULL"),
        ("created_by", "TEXT"),
        ("version", "TEXT NOT NULL"),
        ("notes_json", "TEXT"),
        ("source_file", "TEXT NOT NULL"),
        ("raw_json", "TEXT NOT NULL"),
    ],
    "evidence": [
        ("id", "TEXT PRIMARY KEY"),
        ("relation", "TEXT NOT NULL"),
        ("assessment_status", "TEXT NOT NULL"),
        ("source_type", "TEXT"),
        ("source_citation", "TEXT"),
        ("source_url", "TEXT"),
        ("source_persistent_id", "TEXT"),
        ("locator_type", "TEXT"),
        ("locator_value", "TEXT"),
        ("locator_quote", "TEXT"),
        ("extraction_method", "TEXT"),
        ("captured_at", "TEXT NOT NULL"),
        ("captured_by", "TEXT"),
        ("version", "TEXT NOT NULL"),
        ("source_file", "TEXT NOT NULL"),
        ("raw_json", "TEXT NOT NULL"),
    ],
    "provenance": [
        ("id", "TEXT PRIMARY KEY"),
        ("generated_entity_id", "TEXT"),
        ("entity_type", "TEXT"),
        ("activity_id", "TEXT"),
        ("activity_type", "TEXT"),
        ("attributed_to_json", "TEXT"),
        ("derived_from_json", "TEXT"),
        ("recorded_at", "TEXT NOT NULL"),
        ("version", "TEXT NOT NULL"),
        ("source_file", "TEXT NOT NULL"),
        ("raw_json", "TEXT NOT NULL"),
    ],
    "gap_anchors": [
        ("id", "TEXT PRIMARY KEY"),
        ("title", "TEXT"),
        ("declared_by", "TEXT"),
        ("summary", "TEXT"),
        ("next_step_json", "TEXT"),
        ("resolved_by_claims_json", "TEXT"),
        ("source_file", "TEXT NOT NULL"),
        ("raw_json", "TEXT NOT NULL"),
    ],
    "claim_evidence": [
        ("claim_id", "TEXT NOT NULL"),
        ("evidence_id", "TEXT NOT NULL"),
    ],
    "evidence_claims": [
        ("evidence_id", "TEXT NOT NULL"),
        ("claim_id", "TEXT NOT NULL"),
    ],
    "gap_claims": [
        ("gap_id", "TEXT NOT NULL"),
        ("claim_id", "TEXT NOT NULL"),
    ],
    "ingest_meta": [
        ("key", "TEXT PRIMARY KEY"),
        ("value", "TEXT"),
    ],
}

#: primary key columns per table (used for deterministic dumps / upserts)
PK: dict[str, tuple[str, ...]] = {
    "claims": ("id",),
    "evidence": ("id",),
    "provenance": ("id",),
    "gap_anchors": ("id",),
    "claim_evidence": ("claim_id", "evidence_id"),
    "evidence_claims": ("evidence_id", "claim_id"),
    "gap_claims": ("gap_id", "claim_id"),
    "ingest_meta": ("key",),
}

#: the four record contracts, in copy order (payload first, joins last)
KINDS: tuple[str, ...] = ("claims", "evidence", "provenance", "gaps")

#: order used by DELETE / INSERT / migration (join tables after payload rows)
TABLE_ORDER: tuple[str, ...] = (
    "claim_evidence",
    "evidence_claims",
    "gap_claims",
    "claims",
    "evidence",
    "provenance",
    "gap_anchors",
    "ingest_meta",
)


def schema_ddl() -> str:
    """Dialect-neutral DDL generated from :data:`COLUMNS` (single source)."""
    out: list[str] = []
    for table, cols in COLUMNS.items():
        parts = [f"{name} {spec}" for name, spec in cols]
        pk = PK[table]
        if len(pk) > 1:
            parts.append(f"PRIMARY KEY ({', '.join(pk)})")
        out.append(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(parts)})")
    return ";\n".join(out) + ";\n"


#: kept for backwards compatibility (``ke.store.SCHEMA``)
SCHEMA = schema_ddl()


# --------------------------------------------------------------------------
# 2. Source discovery: both on-disk layouts
# --------------------------------------------------------------------------
#: file stem (without .json) -> kind
_STEM_KIND = {
    "claims": "claims",
    "evidence": "evidence",
    "provenance": "provenance",
    "gaps": "gaps",
    "gap-anchors": "gaps",
}
#: directory name -> kind
_DIR_KIND = {
    "claims": "claims",
    "evidence": "evidence",
    "provenance": "provenance",
    "gaps": "gaps",
}


def _kind_of(rel: Path) -> str | None:
    """Classify ``rel`` by its stem first, then by the nearest parent dir."""
    stem = rel.name[:-5] if rel.name.endswith(".json") else rel.name
    if stem in _STEM_KIND:
        return _STEM_KIND[stem]
    for parent in rel.parts[-2::-1]:
        if parent in _DIR_KIND:
            return _DIR_KIND[parent]
    return None


def _iter_records(path: Path) -> list[dict]:
    """Read one JSON file as a list of record dicts (per-record or aggregate)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, list):
        recs = doc
    elif isinstance(doc, dict) and "id" in doc:
        recs = [doc]
    elif isinstance(doc, dict) and all(isinstance(v, dict) for v in doc.values()):
        recs = list(doc.values())
    else:  # pragma: no cover - defensive
        raise ValueError(f"unsupported record container: {path}")
    for rec in recs:
        if not isinstance(rec, dict) or not rec.get("id"):
            raise ValueError(f"record without id in {path}")
    return recs


class Discovery(NamedTuple):
    """Result of scanning a package tree."""

    records: dict[str, dict[str, tuple[dict, str]]]  # kind -> {id: (record, rel_src)}
    unclassified: list[str]                          # JSON files outside the contract
    duplicates: list[dict]                           # byte-identical re-publications


def discover(source_root: str | Path) -> Discovery:
    """Load all records under ``source_root``.

    ``rel_source_file`` is always relative to ``source_root`` so that digests
    are machine-independent (never absolute paths).

    Aggregate packages (``knowledge/oss-lbm``) re-publish a sub-package's
    records in a roll-up file (``claims/claims.json`` also lists
    ``mflbm/claims.json``).  Byte-identical duplicates are collapsed — the
    first occurrence in sorted path order wins and every collapsed pair is
    reported in :attr:`Discovery.duplicates`.  Records that share an id but
    *differ* in content are a hard error: silently picking one would be data
    loss.
    """
    root = Path(source_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"source root not found: {root}")
    out: dict[str, dict[str, tuple[dict, str]]] = {k: {} for k in KINDS}
    unclassified: list[str] = []
    duplicates: list[dict] = []
    for path in sorted(root.rglob("*.json")):
        rel = path.relative_to(root)
        kind = _kind_of(rel)
        if kind is None:
            unclassified.append(str(rel))
            continue
        for rec in _iter_records(path):
            rid = rec["id"]
            bucket = out[kind]
            if rid in bucket:
                kept, kept_path = bucket[rid]
                if _raw(kept) != _raw(rec):
                    raise ValueError(
                        f"conflicting {kind} record id {rid!r}: {kept_path} != {rel} "
                        f"(resolve the divergence at the source; nothing was ingested)"
                    )
                duplicates.append({"kind": kind, "id": rid, "kept": kept_path,
                                   "collapsed": str(rel)})
                continue
            bucket[rid] = (rec, str(rel))
    return Discovery(out, unclassified, duplicates)


# --------------------------------------------------------------------------
# 3. Record -> row normalization
# --------------------------------------------------------------------------
def _jdump(obj: Any) -> str | None:
    return None if obj is None else json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _raw(rec: dict) -> str:
    return json.dumps(rec, ensure_ascii=False, sort_keys=True)


def _claim_row(rid: str, rec: dict, src: str) -> tuple:
    scope = rec.get("scope") or {}
    return (
        rid,
        rec["statement"],
        rec["claim_type"],
        rec["epistemic_status"],
        rec.get("modality"),
        scope.get("domain"),
        _jdump(scope),
        json.dumps(rec.get("evidence_refs", []), ensure_ascii=False),
        _jdump(rec.get("gap_anchors")),
        _jdump(rec.get("valid_time")),
        rec["created_at"],
        rec.get("created_by"),
        rec["version"],
        _jdump(rec.get("notes")),
        src,
        _raw(rec),
    )


def _evidence_row(rid: str, rec: dict, src: str) -> tuple:
    src_obj = rec.get("source") or {}
    loc = rec.get("locator") or {}
    return (
        rid,
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
        _raw(rec),
    )


def _ref(obj: Any) -> dict:
    """PROV fields may be an inline object or a bare reference id (str)."""
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        return {"id": obj}
    return {}


def _provenance_row(rid: str, rec: dict, src: str) -> tuple:
    ge = _ref(rec.get("generated_entity"))
    act = _ref(rec.get("activity"))
    return (
        rid,
        ge.get("id"),
        ge.get("entity_type"),
        act.get("id"),
        act.get("activity_type"),
        _jdump(rec.get("attributed_to")),
        _jdump(rec.get("derived_from")),
        rec["recorded_at"],
        rec["version"],
        src,
        _raw(rec),
    )


def _gap_row(rid: str, rec: dict, src: str) -> tuple:
    return (
        rid,
        rec.get("title"),
        rec.get("declared_by"),
        rec.get("summary"),
        _jdump(rec.get("next_step")),
        _jdump(rec.get("resolved_by_claims")),
        src,
        _raw(rec),
    )


_ROW_BUILDER = {
    "claims": _claim_row,
    "evidence": _evidence_row,
    "provenance": _provenance_row,
    "gaps": _gap_row,
}

_TABLE_OF_KIND = {
    "claims": "claims",
    "evidence": "evidence",
    "provenance": "provenance",
    "gaps": "gap_anchors",
}


def _insert_sql(table: str) -> str:
    cols = ", ".join(name for name, _ in COLUMNS[table])
    marks = ", ".join("?" for _ in COLUMNS[table])
    return f"INSERT INTO {table} ({cols}) VALUES ({marks})"


def table_columns(table: str) -> list[str]:
    return [name for name, _ in COLUMNS[table]]


# --------------------------------------------------------------------------
# 4. Ingest (backend-agnostic: only ``?`` placeholders + INSERT..ON CONFLICT)
# --------------------------------------------------------------------------
def ingest_source(source_root: str | Path, conn, *, strict: bool = True) -> dict[str, int]:
    """Ingest every record under ``source_root`` into ``conn``.

    Idempotent: the previous state of the KE tables is replaced inside a
    single transaction, so re-ingesting the same source is a no-op
    (``strict=False`` tolerates unclassified files instead of reporting them).
    Returns per-kind record counts.
    """
    found = discover(source_root)
    records, unclassified, duplicates = found.records, found.unclassified, found.duplicates
    # Not fatal: knowledge packages legitimately carry run artefacts next to
    # their records; they are recorded in ingest_meta, never silently dropped.
    counts = {kind: len(records[kind]) for kind in KINDS}

    with conn:  # single transaction (SQLite and psycopg both support this)
        for table in TABLE_ORDER:
            conn.execute(f"DELETE FROM {table}")

        for kind in KINDS:
            table = _TABLE_OF_KIND[kind]
            sql = _insert_sql(table)
            build = _ROW_BUILDER[kind]
            for rid, (rec, src) in records[kind].items():
                conn.execute(sql, build(rid, rec, src))

        # join tables last: base rows exist by now
        ins_ce = "INSERT OR IGNORE INTO claim_evidence (claim_id, evidence_id) VALUES (?,?)"
        for rid, (rec, _src) in records["claims"].items():
            for eref in rec.get("evidence_refs", []):
                conn.execute(ins_ce, (rid, eref))

        ins_ec = "INSERT OR IGNORE INTO evidence_claims (evidence_id, claim_id) VALUES (?,?)"
        for eid, (rec, _src) in records["evidence"].items():
            for cref in rec.get("claim_refs", []):
                conn.execute(ins_ec, (eid, cref))

        ins_gc = "INSERT OR IGNORE INTO gap_claims (gap_id, claim_id) VALUES (?,?)"
        for rid, (rec, _src) in records["claims"].items():
            for gap_id in rec.get("gap_anchors") or []:
                conn.execute(ins_gc, (gap_id, rid))
        for gid, (rec, _src) in records["gaps"].items():
            for cid in rec.get("resolved_by_claims") or []:
                conn.execute(ins_gc, (gid, cid))

        meta = {
            "source_root": str(Path(source_root).name),
            "record_counts": json.dumps(counts, sort_keys=True),
            "unclassified_files": json.dumps(unclassified, sort_keys=True),
            "collapsed_duplicates": json.dumps(duplicates, sort_keys=True),
        }
        for key, value in meta.items():
            conn.execute("INSERT INTO ingest_meta (key, value) VALUES (?,?)", (key, value))

    return counts


# --------------------------------------------------------------------------
# 5. Digests (backend-independent reconciliation evidence)
# --------------------------------------------------------------------------
def table_digest(conn, table: str) -> tuple[int, str]:
    """Return ``(row_count, sha256)`` of a table's canonical row dump.

    The dump is ordered by primary key and JSON-encodes each row's columns in
    contract order, so the digest is identical on SQLite and PostgreSQL and
    stable across machines (no absolute paths are stored in payload columns).
    """
    cols = table_columns(table)
    sel = ", ".join(cols)
    per_row: list[str] = []
    for row in conn.execute(f"SELECT {sel} FROM {table}"):
        blob = json.dumps([row[c] for c in cols], ensure_ascii=False).encode("utf-8")
        per_row.append(hashlib.sha256(blob).hexdigest())
    # Order in Python, not in SQL: PostgreSQL sorts TEXT by database locale
    # while SQLite uses byte order, so an ``ORDER BY`` digest would be
    # machine-dependent.  Sorting hex digests is locale-proof; the row count is
    # folded in so multiplicity can never collide.
    per_row.sort()
    h = hashlib.sha256("\n".join(per_row).encode("ascii"))
    h.update(f"\n#rows={len(per_row)}".encode("ascii"))
    return len(per_row), h.hexdigest()


def digests(conn) -> dict[str, dict[str, Any]]:
    """Digest every table in :data:`TABLE_ORDER` (reconciliation basis)."""
    out: dict[str, dict[str, Any]] = {}
    for table in TABLE_ORDER:
        n, digest = table_digest(conn, table)
        out[table] = {"rows": n, "sha256": digest}
    return out


def dump_table(conn, table: str) -> Iterable[tuple]:
    cols = ", ".join(table_columns(table))
    order = ", ".join(f"{c} {conn.collate_c}" for c in PK[table])
    for row in conn.execute(f"SELECT {cols} FROM {table} ORDER BY {order}"):
        yield tuple(row[c] for c in table_columns(table))