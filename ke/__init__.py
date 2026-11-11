"""TensorKnowledge Knowledge Engine.

Two layers:

* prototype (m8620, stdlib only): ``ke.store`` (JSON -> SQLite ingest),
  ``ke.queries`` (six deterministic queries), ``ke.validate`` (xref invariants
  mirroring ``pilots/m8554/validate_pilot.py``), ``ke.cli``.
* service (m8801): ``ke.api`` (FastAPI HTTP surface), ``ke.apistore``
  (transactional Postgres/SQLite store with the four-state status machine),
  ``ke.ingest_client`` (push a package into the API).

Public API:
    ke.store.connect / ke.store.ingest_pilot
    ke.queries.*
    ke.validate.xref_report / ke.validate.validate_package
    ke.api.app                      (uvicorn ke.api:app, port 8021)
    ke.apistore.Store               (CRUD, review/publication state machine)
    ke.ingest_client.ingest_package (bulk import of a knowledge package)
"""

__version__ = "1.0.0"