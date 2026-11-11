"""KE storage facade — one contract, one query interface, two backends.

The Knowledge Engine persists into exactly two places:

``pg`` (authoritative, production)
    PostgreSQL via ``psycopg`` (v3).  This is the *authoritative* track: every
    produced KE state lives here.  Connection string comes from the
    ``KE_PG_DSN`` environment variable — no credentials are ever hard-coded::

        KE_PG_DSN=postgresql+psycopg:///tensorknowledge?host=/var/run/postgresql

``sqlite`` (lightweight fixture, unit tests / offline)
    ``sqlite3`` from the standard library, ``:memory:`` or a file.  This is a
    *test/offline fixture*, not a second knowledge system: it shares the same
    contract (:mod:`ke.contract`), the same six query classes and the same
    validator, so it can never drift away from what production runs.

No third dialect is allowed (``docs/ke/backends.md`` records the rationale and
the complete list of behavioural differences).

Usage::

    from ke import store, queries, validate

    conn = store.connect(":memory:")                     # sqlite fixture
    conn = store.connect(backend="pg")                   # KE_PG_DSN
    conn = store.connect(backend="pg", schema="ke_test", create_schema=True)

    store.ingest_pilot("path/to/package", conn)
    queries.stats(conn)
    validate.validate_package("path/to/package", conn)

Dialect translation is confined to :class:`Store`:

* ``?`` placeholders  -> ``%s`` (psycopg pyformat), literal ``%`` escaped;
* ``INSERT OR IGNORE`` -> ``INSERT ... ON CONFLICT DO NOTHING``;
* ``KeRow`` rows expose both integer (``row[0]``) and name (``row["id"]``)
  access so every query/validator line is written once, for both backends.
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from . import contract

#: default authoritative DSN (peer auth inside the container)
DEFAULT_PG_DSN = "postgresql+psycopg:///tensorknowledge?host=/var/run/postgresql"

#: kept for backwards compatibility
SCHEMA = contract.SCHEMA

BACKENDS = ("sqlite", "pg")

_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def default_pg_dsn() -> str:
    """``KE_PG_DSN`` (env) or :data:`DEFAULT_PG_DSN`. Read at call time."""
    return os.environ.get("KE_PG_DSN") or DEFAULT_PG_DSN


def _normalize_dsn(dsn: str) -> str:
    """Accept SQLAlchemy-style ``postgresql+psycopg://`` as well as libpq form."""
    return dsn.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres+psycopg://", "postgres://"
    )


class KeRow(dict):
    """Row supporting both ``row["col"]`` and ``row[0]`` (sqlite3.Row parity)."""

    __slots__ = ("_order",)

    def __init__(self, data: dict):
        super().__init__(data)
        self._order = tuple(data)

    def __getitem__(self, key):
        if isinstance(key, int):
            key = self._order[key]
        return super().__getitem__(key)

    def keys(self):  # keep dict(row) / iteration semantics explicit
        return self._order


class KeCursor:
    """Thin cursor wrapper normalizing result rows to :class:`KeRow`."""

    def __init__(self, cur):
        self._cur = cur

    def fetchone(self) -> KeRow | None:
        row = self._cur.fetchone()
        return None if row is None else KeRow(dict(row))

    def fetchall(self) -> list[KeRow]:
        return [KeRow(dict(r)) for r in self._cur.fetchall()]

    def __iter__(self):
        for row in self._cur:
            yield KeRow(dict(row))

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount


class Store:
    """Backend-neutral connection handle used by queries/validate/migrate."""

    def __init__(self, raw, backend: str, *, db_path: str | None = None,
                 dsn: str | None = None, schema: str | None = None):
        self._raw = raw
        self.backend = backend
        self.db_path = db_path
        self.dsn = dsn
        self.schema = schema
        self._ctx = None

    # -- dialect shim ------------------------------------------------------
    def _sql(self, sql: str) -> str:
        if self.backend == "sqlite":
            return sql
        stripped = sql.lstrip()
        if stripped.upper().startswith("INSERT OR IGNORE"):
            sql = re.sub(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql,
                         flags=re.I | re.S)
            if "ON CONFLICT" not in sql.upper():
                sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
        return sql.replace("%", "%%").replace("?", "%s")

    # -- query interface ---------------------------------------------------
    @property
    def collate_c(self) -> str:
        """Collation clause giving byte-order sorting on *this* backend.

        PostgreSQL sorts TEXT with the database locale (e.g. ``en_US.UTF-8``,
        where punctuation is ignored); SQLite sorts with ``BINARY`` (byte
        order).  Pinning both to C / BINARY is what makes ``ORDER BY id``
        return the same sequence on both backends.  Used as
        ``ORDER BY {conn.collate("id")}``.
        """
        return 'COLLATE "C"' if self.backend == "pg" else "COLLATE BINARY"

    def collate(self, expr: str) -> str:
        """``expr`` ordered by byte value on either backend (see collate_c)."""
        return f"{expr} {self.collate_c}"

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> KeCursor:
        cur = self._raw.cursor()
        if params is None:
            cur.execute(self._sql(sql))
        else:
            cur.execute(self._sql(sql), tuple(params))
        return KeCursor(cur)

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> None:
        cur = self._raw.cursor()
        cur.executemany(self._sql(sql), [tuple(p) for p in seq_of_params])

    def scripts(self, script: str) -> None:
        """Run a multi-statement DDL script (dialect-neutral statements)."""
        statements = [s.strip() for s in script.split(";") if s.strip()]
        if self.backend == "sqlite":
            self._raw.executescript(";\n".join(statements) + ";\n")
            return
        cur = self._raw.cursor()
        for stmt in statements:
            cur.execute(stmt)

    # -- transaction / lifecycle ------------------------------------------
    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def __enter__(self) -> "Store":
        """Begin a transaction block (``with store: ...``).

        Implemented explicitly instead of delegating to the driver context
        managers: ``with psycopg.connect(...)`` *closes* the connection on
        exit, while ``with sqlite3.Connection`` only commits — the KE needs
        one semantic on both backends (commit on success, rollback on error,
        connection stays open).
        """
        self._raw.commit()  # close any pending implicit transaction
        self._ctx = True
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self._raw.commit()
            else:
                self._raw.rollback()
        finally:
            self._ctx = None
        return False

    def close(self) -> None:
        self._raw.close()

    def drop_schema(self) -> None:
        """Drop the PG schema created for this store (test isolation)."""
        if self.backend != "pg" or not self.schema:
            return
        cur = self._raw.cursor()
        cur.execute(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE')
        self._raw.commit()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        where = self.db_path if self.backend == "sqlite" else f"{self.dsn} schema={self.schema}"
        return f"<Store backend={self.backend} {where}>"


def _check_ident(name: str, what: str) -> str:
    if not _SAFE_IDENT.match(name):
        raise ValueError(f"unsafe {what} identifier: {name!r}")
    return name


def connect(db_path: str | Path = ":memory:", *, backend: str | None = None,
            dsn: str | None = None, schema: str | None = None,
            create_schema: bool = False) -> Store:
    """Open (and initialize) the KE store.

    ``backend`` defaults to ``"pg"`` when ``db_path`` looks like a PostgreSQL
    DSN, else ``"sqlite"``.  For ``pg`` the DSN is ``dsn`` > ``KE_PG_DSN`` >
    :data:`DEFAULT_PG_DSN`; the tables are created in ``schema`` when given
    (``search_path``), which is how tests isolate themselves.
    """
    if backend is None:
        backend = "pg" if str(db_path).startswith(("postgres", "postgresql")) else "sqlite"
    if backend == "sqlite":
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        store = Store(conn, "sqlite", db_path=str(db_path))
        store.scripts(contract.SCHEMA)
        conn.commit()
        return store
    if backend != "pg":
        raise ValueError(f"unknown backend {backend!r}; allowed: {BACKENDS}")

    import psycopg
    from psycopg.rows import dict_row

    resolved = dsn or default_pg_dsn()
    raw = psycopg.connect(_normalize_dsn(resolved), row_factory=dict_row)
    # Encoding gate: on a non-UTF8 database psycopg returns bytes for TEXT
    # columns, i.e. the same query would yield different *types* than SQLite.
    # That is a contract violation, so fail fast instead of silently drifting.
    enc = raw.execute("SHOW server_encoding").fetchone()["server_encoding"]
    if enc.upper() not in ("UTF8", "UTF-8"):
        raw.close()
        raise RuntimeError(
            f"KE requires a UTF8 PostgreSQL database, got server_encoding={enc!r} "
            f"({resolved!r}); create it with: createdb -E UTF8 -T template0 <db>"
        )
    store = Store(raw, "pg", dsn=resolved, schema=schema)
    if schema:
        _check_ident(schema, "schema")
        cur = raw.cursor()
        if create_schema:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        cur.execute(f'SET search_path TO "{schema}"')
    raw.commit()
    store.scripts(contract.SCHEMA)
    raw.commit()
    return store


def pg_available(dsn: str | None = None, timeout: int = 3) -> bool:
    """True iff the configured PostgreSQL server accepts a connection."""
    try:
        import psycopg

        with psycopg.connect(_normalize_dsn(dsn or default_pg_dsn()),
                             connect_timeout=timeout):
            return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# backwards-compatible ingest entry point (the contract owns the logic)
# --------------------------------------------------------------------------
def ingest_pilot(pilot_dir: str | Path, conn: Store) -> dict[str, int]:
    """Ingest one package directory into ``conn``. Returns per-kind counts.

    Kept as ``store.ingest_pilot`` for the original KE prototype API; the
    implementation (and therefore the contract) lives in :mod:`ke.contract`.
    """
    return contract.ingest_source(pilot_dir, conn)