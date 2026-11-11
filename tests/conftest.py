"""Shared pytest fixtures: one contract, both backends.

Every KE test runs twice — once against the authoritative PostgreSQL backend
(``KE_PG_DSN``) and once against the SQLite fixture — so "the two backends are
indistinguishable" is a machine-checked claim, not a promise.

Environment
-----------
``KE_PG_DSN``      PostgreSQL DSN (default: peer-auth socket, db
                   ``tensorknowledge``; see ``docs/ke/backends.md``).
``KE_PG_REQUIRE``  ``1`` -> a missing/unreachable PostgreSQL is a FAILURE
                   instead of a skip.  CI sets this so the PG track can never
                   silently disappear from the suite.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import store  # noqa: E402

BACKENDS = ("sqlite", "pg")


@pytest.fixture(scope="session")
def pg_ok() -> bool:
    """Skip (or fail, when KE_PG_REQUIRE=1) if PostgreSQL is unreachable."""
    if store.pg_available():
        return True
    reason = (f"PostgreSQL not reachable at {store.default_pg_dsn()!r}; "
              f"the pg backend of the KE contract cannot be exercised")
    if os.environ.get("KE_PG_REQUIRE") == "1":
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(params=BACKENDS)
def backend(request) -> str:
    """Direct backend parameter (for tests that manage their own store)."""
    if request.param == "pg":
        request.getfixturevalue("pg_ok")
    return request.param


def _mk_store(backend_name: str):
    if backend_name == "sqlite":
        return store.connect(":memory:")
    schema = f"ke_test_{uuid.uuid4().hex[:10]}"
    return store.connect(backend="pg", schema=schema, create_schema=True)


def _teardown(c, backend_name: str) -> None:
    try:
        if backend_name == "pg":
            c.drop_schema()
    finally:
        c.close()


@pytest.fixture(params=BACKENDS)
def conn(request):
    """Module-scoped store ingested with the module's ``PILOT`` (if any).

    Parameterized over both backends: each KE test therefore runs twice and a
    divergence between PostgreSQL and SQLite shows up as a failure.
    """
    backend_name = request.param
    if backend_name == "pg":
        request.getfixturevalue("pg_ok")
    c = _mk_store(backend_name)
    pilot = getattr(request.module, "PILOT", None)
    if pilot is not None:
        store.ingest_pilot(pilot, c)
    yield c
    _teardown(c, backend_name)


@pytest.fixture
def new_conn(backend):
    """Factory for extra isolated stores on the *same* backend as the test."""
    created = []

    def _mk(backend_name: str | None = None):
        name = backend_name or backend
        if name == "pg":
            base = store.connect(backend="pg",
                                 schema=f"ke_test_{uuid.uuid4().hex[:10]}",
                                 create_schema=True)
        else:
            base = store.connect(":memory:")
        created.append((base, name))
        return base

    yield _mk
    for c, name in created:
        _teardown(c, name)