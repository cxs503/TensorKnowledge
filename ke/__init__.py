"""TensorKnowledge Knowledge Engine — one contract, two backends (m8800).

The KE is a thin, dependency-light layer over the epistemic record package:

    ingest (JSON -> store)  ->  typed queries (Q1-Q7)  ->  xref validation

Storage is *one* data contract with *one* query interface:

* **PostgreSQL is authoritative** (``psycopg``, DSN from ``KE_PG_DSN``) — every
  produced KE state lives there;
* **SQLite is the unit-test / offline fixture** (``sqlite3``, ``:memory:``) —
  same contract, same queries, same validator, so it cannot drift.

No third dialect is allowed; the complete difference list lives in
``docs/ke/backends.md``.

Public API:
    ke.contract  — the data contract (DDL, discovery, row normalization, digests)
    ke.store.connect / ke.store.ingest_pilot
    ke.queries.*
    ke.validate.xref_report / ke.validate.validate_package
    ke.migrate.main  — SQLite staging -> PostgreSQL migration + reconciliation
"""

__version__ = "0.2.0"