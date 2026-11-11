"""KE service — transactional storage layer (Postgres / SQLite portable).

Design
------
* One row per knowledge object in ``ke_ko``: the *exact* ingested document in
  ``doc`` (JSON text) plus a denormalised four-axis status block.  The four
  states are deliberately independent columns, per the KE contract:

      production_status   draft | submitted | superseded
      evidence_status     claim.epistemic_status / evidence.assessment_status
      review_status       unreviewed | in-review | approved | changes-requested
                          | rejected | revoked | deprecated
      publication_status  private | published | retracted

* ``ke_edge`` holds the claim<->evidence cross references in both directions
  (``claim_evidence`` from ``claim.evidence_refs``, ``evidence_claim`` from
  ``evidence.claim_refs``) so queries are joins, not JSON scans.
* ``ke_review`` is an append-only review event log (``review-event`` schema
  shape). Nothing here ever mutates or deletes a review event.
* Every write happens inside one transaction.  Postgres gets native
  read-committed transactions; SQLite gets ``BEGIN IMMEDIATE`` plus a busy
  timeout, so concurrent writers serialise instead of corrupting.  Create is
  ``INSERT ... ON CONFLICT (id) DO NOTHING`` in both drivers, which makes it
  race-safe: two concurrent creates of the same id -> exactly one winner.

SQL is written with ``%s`` placeholders and rewritten to ``?`` for SQLite.
Only portable SQL is used (no JSONB operators, no ILIKE): case-insensitive
matching uses ``LOWER(col) LIKE LOWER(%s)``, identical in both engines.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

KINDS = ("claim", "evidence", "provenance", "review")
ID_PREFIX = {"claim": "tkc:", "evidence": "tke:", "provenance": "tkp:", "review": "tkr:"}
KIND_BY_PREFIX = {v: k for k, v in ID_PREFIX.items()}

PRODUCTION_STATUSES = ("draft", "submitted", "superseded")
REVIEW_STATUSES = (
    "unreviewed",
    "in-review",
    "approved",
    "changes-requested",
    "rejected",
    "revoked",
    "deprecated",
)
PUBLICATION_STATUSES = ("private", "published", "retracted")
EVIDENCE_STATUSES = (
    "not-assessed",
    "unassessed",
    "established",
    "well-supported",
    "provisional",
    "contested",
    "speculative",
    "superseded",
    "reviewed-supports",
    "reviewed-refutes",
    "reviewed-qualifies",
    "insufficient",
    "disputed",
)
STATUS_AXES = {
    "production": ("production_status", PRODUCTION_STATUSES),
    "evidence": ("evidence_status", EVIDENCE_STATUSES),
    "review": ("review_status", REVIEW_STATUSES),
    "publication": ("publication_status", PUBLICATION_STATUSES),
}

# decision -> (review_status, publication_status or None)
REVIEW_TRANSITIONS = {
    "approve": ("approved", None),
    "request-changes": ("changes-requested", None),
    "reject": ("rejected", None),
    "revoke": ("revoked", "retracted"),
    "deprecate": ("deprecated", "retracted"),
}

# Fields each contract record cannot do without (subset of schemas/*.schema.json
# "required" — duplicated so validation works with or without jsonschema).
REQUIRED_FIELDS = {
    "claim": ("id", "statement", "claim_type", "epistemic_status", "created_at", "version"),
    "evidence": ("id", "source", "relation", "locator", "captured_at",
                 "assessment_status", "version"),
    "provenance": ("id", "generated_entity", "activity", "agents", "recorded_at", "version"),
    "review": ("id", "object_ref", "decision", "reviewer", "reviewed_at", "policy_version"),
}

DDL = (
    """CREATE TABLE IF NOT EXISTS ke_ko (
        id                 TEXT PRIMARY KEY,
        kind               TEXT NOT NULL,
        doc                TEXT NOT NULL,
        domain             TEXT,
        producer           TEXT NOT NULL,
        version            TEXT NOT NULL,
        production_status  TEXT NOT NULL,
        evidence_status    TEXT NOT NULL,
        review_status      TEXT NOT NULL,
        publication_status TEXT NOT NULL,
        search_text        TEXT NOT NULL,
        created_at         TEXT NOT NULL,
        updated_at         TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS ke_edge (
        src_id    TEXT NOT NULL,
        dst_id    TEXT NOT NULL,
        relation  TEXT NOT NULL,
        edge_kind TEXT NOT NULL,
        PRIMARY KEY (src_id, dst_id, relation, edge_kind)
    )""",
    """CREATE TABLE IF NOT EXISTS ke_review (
        id          TEXT PRIMARY KEY,
        object_ref  TEXT NOT NULL,
        decision    TEXT NOT NULL,
        reviewer    TEXT NOT NULL,
        reviewed_at TEXT NOT NULL,
        doc         TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ke_ko_kind_idx ON ke_ko (kind)",
    "CREATE INDEX IF NOT EXISTS ke_ko_domain_idx ON ke_ko (domain)",
    "CREATE INDEX IF NOT EXISTS ke_ko_review_idx ON ke_ko (review_status)",
    "CREATE INDEX IF NOT EXISTS ke_ko_pub_idx ON ke_ko (publication_status)",
    "CREATE INDEX IF NOT EXISTS ke_edge_dst_idx ON ke_edge (dst_id)",
)


class Conflict(Exception):
    """Write conflicts with current state (-> HTTP 409)."""


class NotFound(Exception):
    """Object does not exist (-> HTTP 404)."""


class Forbidden(Exception):
    """Four-state policy violated (-> HTTP 403)."""


class BadRequest(Exception):
    """Malformed request/record (-> HTTP 422)."""


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def is_postgres(dsn: str) -> bool:
    d = dsn.strip().lower()
    if d.startswith(("sqlite:", "file:", "/", ":")):
        return False
    return d.startswith(("postgres://", "postgresql://")) or "dbname=" in d or "host=" in d


def default_dsn() -> str:
    """``KE_DSN`` wins; otherwise a local SQLite file (dev/test default)."""
    dsn = os.environ.get("KE_DSN")
    if dsn:
        return dsn
    return "sqlite:" + os.environ.get("KE_DB", ":memory:")


def sqlite_path(dsn: str) -> str:
    return dsn[len("sqlite:"):] if dsn.startswith("sqlite:") else dsn


def infer_kind(doc: dict) -> str | None:
    """Map a record id prefix (tkc:/tke:/tkp:/tkr:) to its contract kind."""
    rid = str(doc.get("id", ""))
    for prefix, kind in KIND_BY_PREFIX.items():
        if rid.startswith(prefix):
            return kind
    return None


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _search_text(kind: str, doc: dict) -> str:
    parts: list[str] = []
    if kind == "claim":
        parts.append(str(doc.get("statement") or ""))
        parts += [str(n) for n in (doc.get("notes") or []) if isinstance(n, str)]
        scope = doc.get("scope") or {}
        if isinstance(scope, dict):
            parts += [str(scope.get("domain") or ""), str(scope.get("system") or "")]
            parts += [str(c) for c in (scope.get("conditions") or []) if isinstance(c, str)]
    elif kind == "evidence":
        src = doc.get("source") or {}
        loc = doc.get("locator") or {}
        parts += [str(src.get("citation") or ""), str(src.get("url") or "")]
        parts += [str(loc.get("value") or ""), str(loc.get("quote") or "")]
        parts.append(str(doc.get("relation") or ""))
    elif kind == "provenance":
        act = doc.get("activity") or {}
        parts += [str(act.get("description") or ""), str(act.get("activity_type") or "")]
    elif kind == "review":
        parts += [str(doc.get("rationale") or ""), str(doc.get("decision") or "")]
    return "\n".join(p for p in parts if p)


def _domain(kind: str, doc: dict) -> str | None:
    if kind == "claim":
        scope = doc.get("scope") or {}
        if isinstance(scope, dict):
            return scope.get("domain")
    return doc.get("domain")


def _evidence_status(kind: str, doc: dict) -> str:
    if kind == "claim":
        st = str(doc.get("epistemic_status") or "not-assessed")
    elif kind == "evidence":
        st = str(doc.get("assessment_status") or "unassessed")
    else:
        st = "not-assessed"
    return st if st in EVIDENCE_STATUSES else "not-assessed"


def _edges(kind: str, doc: dict) -> list[tuple[str, str, str, str]]:
    rid = str(doc["id"])
    out: list[tuple[str, str, str, str]] = []
    if kind == "claim":
        for eref in doc.get("evidence_refs") or []:
            if isinstance(eref, str):
                out.append((rid, eref, "refs", "claim_evidence"))
    elif kind == "evidence":
        rel = str(doc.get("relation") or "mentions")
        for cref in doc.get("claim_refs") or []:
            if isinstance(cref, str):
                out.append((rid, cref, rel, "evidence_claim"))
    return out


class _SQLiteConn:
    """sqlite3 connection wrapped with %s -> ? rewriting and dict rows."""

    def __init__(self, raw: sqlite3.Connection) -> None:
        self.raw = raw
        self._last = None

    def execute(self, sql: str, args: tuple = ()) -> "_SQLiteConn":
        self._last = self.raw.execute(re.sub(r"%s", "?", sql), args)
        return self

    def fetchall(self) -> list[dict]:
        return [dict(r) for r in self._last.fetchall()]

    def fetchone(self) -> dict | None:
        row = self._last.fetchone()
        return dict(row) if row is not None else None

    @property
    def rowcount(self) -> int:
        return self._last.rowcount


def _decode_row(row: dict) -> dict:
    """SQL_ASCII databases come back as bytes; normalise to str.

    Container clusters here are initialised with server_encoding=SQL_ASCII, so
    psycopg hands TEXT columns back as ``bytes``.  Status/producer comparisons
    must see ``str`` or the four-state policy silently mis-fires, so decode
    eagerly at the driver boundary (UTF-8, the only encoding we write).
    """
    out = {}
    for k, v in row.items():
        out[k] = v.decode("utf-8", "replace") if isinstance(v, bytes) else v
    return out


class _PGConn:
    """psycopg connection with dict rows (psycopg imported lazily)."""

    def __init__(self, raw) -> None:
        self.raw = raw
        self._last = None

    def execute(self, sql: str, args: tuple = ()) -> "_PGConn":
        self._last = self.raw.execute(sql, args)
        return self

    def fetchall(self) -> list[dict]:
        return [_decode_row(dict(r)) for r in self._last.fetchall()]

    def fetchone(self) -> dict | None:
        row = self._last.fetchone()
        return _decode_row(dict(row)) if row is not None else None

    @property
    def rowcount(self) -> int:
        return self._last.rowcount


class Store:
    """Thin transactional facade over one KE database."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or default_dsn()
        self.driver = "postgres" if is_postgres(self.dsn) else "sqlite"

    # -- connections ----------------------------------------------------
    @contextmanager
    def connect(self, write: bool = False) -> Iterator[Any]:
        if self.driver == "postgres":
            import psycopg
            from psycopg.rows import dict_row

            raw = psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=10)
            conn = _PGConn(raw)
            try:
                yield conn
                raw.commit()
            except BaseException:
                raw.rollback()
                raise
            finally:
                raw.close()
            return

        path = sqlite_path(self.dsn)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(path, timeout=30.0, isolation_level=None, check_same_thread=False)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA busy_timeout = 30000")
        if path != ":memory:":
            try:
                raw.execute("PRAGMA journal_mode = WAL")
            except sqlite3.DatabaseError:  # pragma: no cover
                pass
        conn = _SQLiteConn(raw)
        try:
            raw.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn
            raw.execute("COMMIT")
        except BaseException:
            try:
                raw.execute("ROLLBACK")
            except sqlite3.Error:  # pragma: no cover
                pass
            raise
        finally:
            raw.close()

    def ensure_schema(self) -> None:
        with self.connect(write=True) as conn:
            for stmt in DDL:
                conn.execute(stmt)

    def ping(self) -> bool:
        try:
            with self.connect() as conn:
                conn.execute("SELECT 1 AS ok").fetchone()
            return True
        except Exception:
            return False

    # -- writes ---------------------------------------------------------
    def create_ko(
        self,
        kind: str,
        doc: dict,
        producer: str,
        *,
        domain: str | None = None,
        production_status: str = "draft",
        review_status: str = "unreviewed",
        publication_status: str = "private",
    ) -> dict:
        """Insert one knowledge object. Raises Conflict on duplicate id."""
        rid = str(doc["id"])
        ts = now_iso()
        dom = domain if domain is not None else _domain(kind, doc)
        cols = (
            rid, kind, _dump(doc), dom, producer, str(doc.get("version") or "1.0.0"),
            production_status, _evidence_status(kind, doc), review_status,
            publication_status, _search_text(kind, doc), ts, ts,
        )
        with self.connect(write=True) as conn:
            res = conn.execute(
                """INSERT INTO ke_ko (id, kind, doc, domain, producer, version,
                       production_status, evidence_status, review_status,
                       publication_status, search_text, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (id) DO NOTHING""",
                cols,
            )
            if res.rowcount != 1:
                raise Conflict(f"knowledge object already exists: {rid}")
            for (src, dst, rel, ekind) in _edges(kind, doc):
                conn.execute(
                    """INSERT INTO ke_edge (src_id, dst_id, relation, edge_kind)
                       VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (src, dst, rel, ekind),
                )
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
        assert row is not None
        return self._shape(row)

    def update_doc(self, rid: str, producer: str, doc: dict) -> dict:
        """Replace the document of a *draft* object; producer only."""
        with self.connect(write=True) as conn:
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
            if row is None:
                raise NotFound(rid)
            if row["producer"] != producer:
                raise Forbidden("only the producer may modify a knowledge object")
            if row["production_status"] != "draft":
                raise Conflict(
                    f"object is {row['production_status']}; only drafts are editable"
                )
            if str(doc["id"]) != rid:
                raise Forbidden("id in document does not match path id")
            conn.execute("DELETE FROM ke_edge WHERE src_id = %s", (rid,))
            conn.execute(
                """UPDATE ke_ko SET doc = %s, domain = %s, version = %s,
                       evidence_status = %s, search_text = %s, updated_at = %s
                   WHERE id = %s""",
                (
                    _dump(doc), _domain(row["kind"], doc),
                    str(doc.get("version") or row["version"]),
                    _evidence_status(row["kind"], doc), _search_text(row["kind"], doc),
                    now_iso(), rid,
                ),
            )
            for (src, dst, rel, ekind) in _edges(row["kind"], doc):
                conn.execute(
                    """INSERT INTO ke_edge (src_id, dst_id, relation, edge_kind)
                       VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (src, dst, rel, ekind),
                )
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
        assert row is not None
        return self._shape(row)

    def delete_ko(self, rid: str, producer: str) -> None:
        with self.connect(write=True) as conn:
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
            if row is None:
                raise NotFound(rid)
            if row["producer"] != producer:
                raise Forbidden("only the producer may delete a knowledge object")
            if row["production_status"] != "draft":
                raise Conflict(
                    f"object is {row['production_status']}; only drafts are deletable"
                )
            conn.execute("DELETE FROM ke_edge WHERE src_id = %s OR dst_id = %s", (rid, rid))
            conn.execute("DELETE FROM ke_ko WHERE id = %s", (rid,))

    def submit(self, rid: str, producer: str) -> dict:
        """draft -> submitted (producer only). Other states untouched."""
        with self.connect(write=True) as conn:
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
            if row is None:
                raise NotFound(rid)
            if row["producer"] != producer:
                raise Forbidden("only the producer may submit a knowledge object")
            if row["production_status"] != "draft":
                raise Conflict(f"cannot submit: production_status={row['production_status']}")
            conn.execute(
                "UPDATE ke_ko SET production_status = %s, updated_at = %s WHERE id = %s",
                ("submitted", now_iso(), rid),
            )
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
        assert row is not None
        return self._shape(row)

    def record_review(self, rid: str, event: dict) -> dict:
        """Apply one review decision and append its event.

        Enforced here (not only in the router) so every entry point inherits:
          * reviewer != producer (no self-audit)
          * reviewable objects only
          * no re-approval out of rejected/revoked, nothing after deprecated
        """
        with self.connect(write=True) as conn:
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
            if row is None:
                raise NotFound(rid)
            if event["reviewer"] == row["producer"]:
                raise Forbidden(
                    f"producer {row['producer']!r} may not review its own object"
                )
            decision = event["decision"]
            new_review, new_pub = REVIEW_TRANSITIONS[decision]
            if row["review_status"] == "deprecated":
                raise Conflict("object is deprecated; no further review decisions")
            if row["review_status"] in ("rejected", "revoked") and decision == "approve":
                raise Conflict(f"cannot approve from review_status={row['review_status']}")
            conn.execute(
                """INSERT INTO ke_review (id, object_ref, decision, reviewer,
                       reviewed_at, doc) VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (id) DO NOTHING""",
                (event["id"], rid, decision, event["reviewer"], event["reviewed_at"],
                 _dump(event["doc"])),
            )
            pub = row["publication_status"]
            if new_pub == "retracted" and pub == "published":
                pub = "retracted"
            conn.execute(
                """UPDATE ke_ko SET review_status = %s, publication_status = %s,
                       updated_at = %s WHERE id = %s""",
                (new_review, pub, now_iso(), rid),
            )
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
        assert row is not None
        return self._shape(row)

    def publish(self, rid: str, producer: str | None = None) -> dict:
        # ``producer`` kept for call-site symmetry with the other transitions;
        # publishing is a review-gated action, not a producer action, so the
        # identity is not consulted (the bearer token is the authorisation).
        """private -> published; requires review_status == approved."""
        with self.connect(write=True) as conn:
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
            if row is None:
                raise NotFound(rid)
            if row["review_status"] != "approved":
                raise Conflict(
                    f"cannot publish: review_status={row['review_status']} (need approved)"
                )
            if row["publication_status"] == "retracted":
                raise Conflict("cannot publish: publication_status=retracted")
            if row["publication_status"] == "published":
                return self._shape(row)
            conn.execute(
                "UPDATE ke_ko SET publication_status = %s, updated_at = %s WHERE id = %s",
                ("published", now_iso(), rid),
            )
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
        assert row is not None
        return self._shape(row)

    # -- reads ----------------------------------------------------------
    @staticmethod
    def _shape(row: dict) -> dict:
        return {
            "id": row["id"],
            "kind": row["kind"],
            "domain": row["domain"],
            "producer": row["producer"],
            "version": row["version"],
            "production_status": row["production_status"],
            "evidence_status": row["evidence_status"],
            "review_status": row["review_status"],
            "publication_status": row["publication_status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "doc": json.loads(row["doc"]),
        }

    def get_ko(self, rid: str) -> dict:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (rid,)).fetchone()
        if row is None:
            raise NotFound(rid)
        return self._shape(row)

    def list_ko(
        self,
        *,
        kind: str | None = None,
        axis: str | None = None,
        status: str | None = None,
        domain: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        where: list[str] = []
        args: list[Any] = []
        if kind:
            where.append("kind = %s")
            args.append(kind)
        if axis and status:
            where.append(f"{STATUS_AXES[axis][0]} = %s")
            args.append(status)
        if domain:
            where.append("LOWER(domain) LIKE LOWER(%s)")
            args.append(f"%{domain}%")
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        with self.connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) AS n FROM ke_ko{clause}", tuple(args)).fetchone()
            rows = conn.execute(
                f"SELECT * FROM ke_ko{clause} ORDER BY id LIMIT %s OFFSET %s",
                tuple(args + [limit, offset]),
            ).fetchall()
        return {"total": int(total["n"]) if total else 0,
                "items": [self._shape(r) for r in rows]}

    def by_status(self, axis: str, status: str, kind: str | None = None) -> dict:
        res = self.list_ko(kind=kind, axis=axis, status=status, limit=2000)
        return {"axis": axis, "status": status, "kind": kind, "count": res["total"],
                "items": [{k: v for k, v in it.items() if k != "doc"} for it in res["items"]]}

    def by_evidence_relation(self, relation: str) -> dict:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT e.id AS id, e.doc AS doc, e.evidence_status AS evidence_status,
                          e.review_status AS review_status, ed.dst_id AS claim_id
                   FROM ke_edge ed JOIN ke_ko e ON e.id = ed.src_id
                   WHERE ed.edge_kind = 'evidence_claim' AND ed.relation = %s
                   ORDER BY e.id, ed.dst_id""",
                (relation,),
            ).fetchall()
        items = []
        for r in rows:
            doc = json.loads(r["doc"])
            items.append({
                "evidence_id": r["id"],
                "claim_id": r["claim_id"],
                "relation": doc.get("relation"),
                "assessment_status": r["evidence_status"],
                "review_status": r["review_status"],
                "source": doc.get("source"),
                "locator": doc.get("locator"),
            })
        return {"relation": relation, "count": len(items), "items": items}

    def claims_by_domain(self, domain: str, exact: bool = False, kind: str = "claim") -> dict:
        if exact:
            with self.connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM ke_ko WHERE kind = %s AND domain = %s ORDER BY id",
                    (kind, domain),
                ).fetchall()
            items = [self._shape(r) for r in rows]
        else:
            items = self.list_ko(kind=kind, domain=domain, limit=2000)["items"]
        return {
            "domain": domain,
            "exact": exact,
            "count": len(items),
            "items": [
                {
                    "id": it["id"],
                    "domain": it["domain"],
                    "statement": it["doc"].get("statement"),
                    "evidence_status": it["evidence_status"],
                    "review_status": it["review_status"],
                }
                for it in items
            ],
        }

    def evidence_for_claim(self, claim_id: str) -> dict:
        with self.connect() as conn:
            claim = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (claim_id,)).fetchone()
            if claim is None:
                raise NotFound(claim_id)
            rows = conn.execute(
                """SELECT e.id AS id, e.doc AS doc, e.evidence_status AS evidence_status,
                          e.review_status AS review_status, ed.relation AS relation
                   FROM ke_edge ed JOIN ke_ko e ON e.id = ed.src_id
                   WHERE ed.edge_kind = 'evidence_claim' AND ed.dst_id = %s
                   ORDER BY e.id""",
                (claim_id,),
            ).fetchall()
            refs = conn.execute(
                """SELECT dst_id AS id FROM ke_edge
                   WHERE edge_kind = 'claim_evidence' AND src_id = %s ORDER BY dst_id""",
                (claim_id,),
            ).fetchall()
        items = []
        for r in rows:
            doc = json.loads(r["doc"])
            items.append({
                "evidence_id": r["id"],
                "relation": r["relation"],
                "assessment_status": r["evidence_status"],
                "review_status": r["review_status"],
                "source": doc.get("source"),
                "locator": doc.get("locator"),
            })
        known = {i["evidence_id"] for i in items}
        return {
            "claim_id": claim_id,
            "evidence_status": claim["evidence_status"],
            "count": len(items),
            "items": items,
            "dangling_evidence_refs": [r["id"] for r in refs if r["id"] not in known],
        }

    def provenance_chain(self, claim_id: str) -> dict:
        with self.connect() as conn:
            claim = conn.execute("SELECT * FROM ke_ko WHERE id = %s", (claim_id,)).fetchone()
            if claim is None:
                raise NotFound(claim_id)
            ev_rows = conn.execute(
                """SELECT e.id AS id, e.doc AS doc FROM ke_edge ed
                   JOIN ke_ko e ON e.id = ed.src_id
                   WHERE ed.edge_kind = 'evidence_claim' AND ed.dst_id = %s
                   ORDER BY e.id""",
                (claim_id,),
            ).fetchall()
            prov_rows = conn.execute(
                "SELECT id, doc FROM ke_ko WHERE kind = %s ORDER BY id", ("provenance",)
            ).fetchall()
        links = []
        for r in ev_rows:
            doc = json.loads(r["doc"])
            links.append({
                "evidence_id": r["id"],
                "relation": doc.get("relation"),
                "assessment_status": doc.get("assessment_status"),
                "source": doc.get("source"),
                "locator": doc.get("locator"),
            })
        needles = {claim_id} | {l["evidence_id"] for l in links}
        # A claim id is ``tkc:<namespace>:<slug>``; packages record provenance
        # against the package path (``knowledge/<namespace>[/<subpkg>]``) rather
        # than against individual claims.  Those package-level records are
        # reported separately and *not* counted as per-claim chain links, so a
        # missing per-claim provenance record stays visible.
        namespace = claim_id.split(":")[1] if claim_id.count(":") >= 2 else ""
        prov: list[dict] = []
        package_prov: list[dict] = []
        for r in prov_rows:
            doc = json.loads(r["doc"])
            ge = doc.get("generated_entity")
            ge = ge.get("id") if isinstance(ge, dict) else (ge if isinstance(ge, str) else None)
            raw_derived = doc.get("derived_from") or []
            if isinstance(raw_derived, str):
                raw_derived = [raw_derived]
            derived = {d for d in raw_derived if isinstance(d, str)}
            entry = {
                "provenance_id": r["id"],
                "generated_entity": doc.get("generated_entity"),
                "activity": doc.get("activity"),
                "agents": doc.get("agents"),
            }
            if ge in needles or (derived & needles):
                prov.append(entry)
            elif namespace and isinstance(ge, str) and (
                ge == f"knowledge/{namespace}" or ge.startswith(f"knowledge/{namespace}/")
            ):
                entry["match"] = "package-namespace"
                package_prov.append(entry)
        return {
            "claim_id": claim_id,
            "claim": {
                "id": claim["id"],
                "domain": claim["domain"],
                "evidence_status": claim["evidence_status"],
                "review_status": claim["review_status"],
                "publication_status": claim["publication_status"],
                "statement": json.loads(claim["doc"]).get("statement"),
            },
            "links": links,
            "provenance": prov,
            "package_provenance": package_prov,
            "complete": bool(links) and all(l["source"] for l in links),
        }

    def stats(self) -> dict:
        with self.connect() as conn:
            def dist(col: str) -> dict:
                rows = conn.execute(
                    f"SELECT {col} AS k, COUNT(*) AS n FROM ke_ko GROUP BY {col} ORDER BY {col}"
                ).fetchall()
                return {r["k"]: int(r["n"]) for r in rows}

            total = conn.execute("SELECT COUNT(*) AS n FROM ke_ko").fetchone()
            edges = conn.execute("SELECT COUNT(*) AS n FROM ke_edge").fetchone()
            reviews = conn.execute("SELECT COUNT(*) AS n FROM ke_review").fetchone()
            per_kind = {r["k"]: int(r["n"]) for r in conn.execute(
                "SELECT kind AS k, COUNT(*) AS n FROM ke_ko GROUP BY kind ORDER BY kind"
            ).fetchall()}
            axes = {axis: dist(axis) for axis in
                    ("production_status", "evidence_status", "review_status",
                     "publication_status")}
        return {
            "objects": int(total["n"]) if total else 0,
            "by_kind": per_kind,
            "edges": int(edges["n"]) if edges else 0,
            "review_events": int(reviews["n"]) if reviews else 0,
            "production_status": axes["production_status"],
            "evidence_status": axes["evidence_status"],
            "review_status": axes["review_status"],
            "publication_status": axes["publication_status"],
        }

    def search(
        self,
        q: str,
        *,
        kind: str | None = None,
        domain: str | None = None,
        axis: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict:
        where = ["LOWER(search_text) LIKE LOWER(%s)"]
        args: list[Any] = [f"%{q}%"]
        if kind:
            where.append("kind = %s")
            args.append(kind)
        if domain:
            where.append("LOWER(domain) LIKE LOWER(%s)")
            args.append(f"%{domain}%")
        if axis and status:
            where.append(f"{STATUS_AXES[axis][0]} = %s")
            args.append(status)
        clause = " WHERE " + " AND ".join(where)
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM ke_ko{clause} ORDER BY id LIMIT %s", tuple(args + [limit])
            ).fetchall()
        items = []
        for r in rows:
            obj = self._shape(r)
            doc = obj.pop("doc")
            items.append({
                **obj,
                "statement": doc.get("statement"),
                "snippet": _snippet(r["search_text"], q),
            })
        return {"q": q, "count": len(items), "items": items}

    def reviews_for(self, object_ref: str) -> dict:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT * FROM ke_review WHERE object_ref = %s
                   ORDER BY reviewed_at, id""",
                (object_ref,),
            ).fetchall()
        return {"object_ref": object_ref, "count": len(rows),
                "items": [json.loads(r["doc"]) for r in rows]}


def _snippet(text: str, q: str, width: int = 120) -> str:
    low = text.lower()
    i = low.find(q.lower())
    flat = " ".join(text.split())
    if i < 0:
        return flat[:width]
    start = max(0, i - width // 3)
    return ("..." if start else "") + flat[start:start + width].strip() + (
        "..." if start + width < len(flat) else ""
    )