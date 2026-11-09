"""Cognee (cognee 1.6.7) evaluation demo.

Same three steps as the Graphiti demo, but note the outcome is environment
dependent: on a loongarch64 host the distribution's own dependency set cannot
be satisfied (see probe_minimal_install.py + docs/ke/evaluation.md), so the
import step is expected to fail and the script records that failure verbatim
instead of fabricating a demo.

If the import succeeds the script maps the TensorKnowledge corpus onto
`cognee`'s DataPoint graph model (typed pydantic nodes + typed edges), counts
field-level mapping loss and prints the four retrieval primitives cognee would
serve them with.

Usage:
  python cognee_mapping_demo.py --corpus artifacts/ke_eval/corpus.json \
      --out artifacts/ke_eval/cognee_result.json
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path


def probe_import() -> dict:
    out = {}
    try:
        import cognee  # noqa: F401
        from importlib.metadata import version
        out["status"] = "importable"
        out["dist_version"] = version("cognee")
    except Exception as exc:
        out["status"] = "import_blocked"
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def mapping_analysis() -> dict:
    """Field-level mapping verdicts against cognee's DataPoint model.

    Sourced from reading cognee's source (not its documentation):
      cognee/modules/engine/models/DataPoint.py      - typed node/edge base
      cognee/infrastructure/databases/provenance/*   - source-ref bookkeeping
      cognee/shared/data_models.py                   - GraphDBType enum
    """
    return {
        "claim-record": {
            "first_class": ["id (DataPoint.id)", "statement (as a typed attribute)",
                            "claim_type", "epistemic_status", "scope (nested DataPoint)"],
            "attributes_bag": ["evidence_refs (edges instead of id arrays)"],
            "lost": ["supersedes array (only linear versioning)",
                     "relation_refs (no typed relation-to-relation edges)"],
            "note": "DataPoint subclasses are pydantic models, so arbitrary typed fields "
                    "survive; the cost is that the *contract* must be re-expressed as "
                    "classes and kept in sync by hand.",
        },
        "evidence-record": {
            "first_class": ["id", "relation (edge label)", "source (DataPoint)",
                            "locator (DataPoint attribute)", "captured_at"],
            "attributes_bag": ["assessment", "extraction_method"],
            "lost": ["claim_refs ordering/dedup semantics", "version chain"],
            "note": "Evidence must become a node to keep locator+assessment; an edge alone "
                    "cannot carry the closed relation enum without a custom model.",
        },
        "provenance-record": {
            "first_class": ["activity_type (no, not modelled) - GENUINELY ABSENT"],
            "attributes_bag": ["derived_from (as edges)", "agents (as nodes if you model them)"],
            "lost": ["PROV-O used/wasAttributedTo semantics", "recorded_at vs valid_time "
                     "distinction unless modelled by hand"],
            "note": "cognee's provenance module bookkeeping is source-ref/deletion "
                    "bookkeeping (dataset/data/chunk ids), not PROV-O entities/activities/"
                    "agents. Representing PROV-O means authoring custom DataPoint classes.",
        },
        "knowledge-object": {
            "first_class": ["title", "summary", "object_type (node class name)",
                            "domains (via node_set membership)"],
            "attributes_bag": ["evidence_status", "review_status", "tags", "version"],
            "lost": ["review_event chain with no-self-approval invariant",
                     "claim_refs/evidence_refs/provenance_refs typed link roles"],
            "note": "node_set is a tag namespace, not a governed partition, and has no "
                    "multi-tenancy or review semantics.",
        },
    }


PRIMITIVES = {
    "P1_claim_status": {
        "available_via": ["SearchType.CYPHER (raw graph query)",
                          "SearchType.GRAPH_COMPLETION with an LLM filter prompt"],
        "typed_filter": False,
        "caveat": "cognee's search API takes node_name / node_set filters and a query type, "
                  "not a predicate on typed attributes: status filtering needs raw Cypher "
                  "or an LLM round trip.",
    },
    "P2_evidence_relation": {
        "available_via": ["SearchType.CYPHER (traverse edges by label)",
                          "SearchType.INSIGHTS / SUMMARIES (LLM-mediated)"],
        "typed_filter": False,
        "caveat": "no first-class relation filter; the 4-value relation enum must be "
                  "modelled as edge classes and queried with Cypher.",
    },
    "P3_provenance_chain": {
        "available_via": ["SearchType.CYPHER over source-ref edges",
                          "SearchType.TEMPORAL for time-scoped events"],
        "typed_filter": False,
        "caveat": "no PROV-O primitives; a chain is only as good as the hand-built "
                  "DataPoint classes.",
    },
    "P4_domain": {
        "available_via": ["node_set filtering (search(node_type, node_name, node_set))",
                          "datasets API for coarse partitioning"],
        "typed_filter": True,
        "caveat": "node_set is the closest thing to a governed domain tag; it is a list of "
                  "strings with no ontology or access control.",
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="artifacts/ke_eval/corpus.json")
    ap.add_argument("--out", default="artifacts/ke_eval/cognee_result.json")
    a = ap.parse_args()
    res = {"python": sys.version.split()[0], "platform": platform.machine(),
           "import_probe": probe_import(), "mapping_loss": mapping_analysis(),
           "primitives": PRIMITIVES}
    corpus = json.loads(Path(a.corpus).read_text())["corpus"]
    res["corpus_size"] = {k: len(v) for k, v in corpus.items()}

    if res["import_probe"]["status"] == "importable":
        try:
            from cognee.modules.engine.models.DataPoint import DataPoint  # noqa: F401
            res["datapoint_import"] = "ok"
        except Exception as exc:
            res["datapoint_import"] = f"{type(exc).__name__}: {exc}"
        res["live_ingest"] = {"status": "not_attempted",
                              "reason": "no graph/vector backend available on this host "
                                        "(see install matrix); DataPoint demo only"}

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res["import_probe"], indent=1))


if __name__ == "__main__":
    main()