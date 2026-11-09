"""TensorKnowledge Knowledge Engine — minimal closed-loop prototype (m8620).

Thin, stdlib-only layer over the epistemic pilot package (m8554):
ingest (JSON -> SQLite), typed queries, and cross-reference invariants
mirroring pilots/m8554/validate_pilot.py.

Public API:
    ke.store.connect / ke.store.ingest_pilot
    ke.queries.*
    ke.validate.xref_report / ke.validate.validate_package
"""

__version__ = "0.1.0"
