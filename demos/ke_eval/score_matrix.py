"""Weighted decision matrix for the Knowledge-Engine selection (FEAT-TK-KNOWLEDGE-ENGINE).

Scores are 1..5 (5 = best fit for TensorKnowledge's requirements). Every cell
carries the evidence pointer that justifies it, so a reviewer can disagree with
a score and see exactly which artefact to argue with. Totals are computed here
(not hand-written) and injected into docs/ke/evaluation.md by the report
generator, so no number in the document is transcribed by hand.

Usage:
  python score_matrix.py --out artifacts/ke_eval/decision_matrix.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# (id, name, weight, what the dimension means, evidence anchor prefix)
DIMENSIONS = [
    ("D1", "Install surface / offline installability on loongarch64", 18,
     "Can the engine be installed today, from wheels, on this container?", "install matrix §1"),
    ("D2", "Dependency weight / Python compatibility risk", 8,
     "Number and nature of transitive deps; pin-conflict and rebuild risk.", "install matrix §1"),
    ("D3", "Storage backend coverage incl. PostgreSQL", 12,
     "Does the deployment-target database (PostgreSQL) work as primary store?", "source §3"),
    ("D4", "Incremental ingestion / idempotency / delete consistency", 10,
     "Re-ingest a changed document without duplicating or orphaning knowledge.", "source §4"),
    ("D5", "Retrieval primitives for the four required queries", 14,
     "claim-status filter, evidence relation, provenance chain, domain scoping.", "demo §2"),
    ("D6", "Provenance expressiveness (PROV-O)", 12,
     "Native entity/activity/agent, used/wasDerivedFrom/wasAttributedTo, valid vs recorded time.", "source §5"),
    ("D7", "Mapping loss to the four TensorKnowledge contracts", 10,
     "How much of schemas/*.schema.json survives a store+read-back round trip.", "demo §3"),
    ("D8", "Governance invariants (review events, no self-approval)", 5,
     "Can the engine enforce or even store the review/attestation model?", "source §6"),
    ("D9", "Operational footprint", 3,
     "Processes to run, services to babysit, failure modes.", "install matrix §2"),
    ("D10", "Reversibility / export / lock-in", 2,
     "Cost of leaving the engine if the decision is revisited.", "demo §3"),
    ("D11", "Semantic extraction & reasoning (graph construction quality)", 6,
     "LLM-based entity/relation extraction, dedupe, contradiction detection, answer synthesis.", "source §7"),
]

# scores[option][dim_id] = (score, justification, evidence pointer)
SCORES = {
    "Cognee 1.6.7": {
        "D1": (1, "Cannot be installed: `pip install cognee` fails because the default vector "
                  "backend lancedb 0.39.0 publishes no loongarch64 wheel and no sdist; "
                  "5 further core deps are binary/Rust-only.",
               "logs/cognee_aliyun.log, artifacts/ke_eval/install_matrix.json"),
        "D2": (1, "141 declared requirements (53 in the core set) incl. tiktoken, tokenizers, "
                  "onnxruntime, fastembed, cryptography, pylance; two Rust build-backend "
                  "failures observed before the wheel wall.",
               "logs/cognee_aliyun.log, logs/cognee_install.log"),
        "D3": (4, "PostgreSQL is a first-class relational backend (db_provider) and pgvector a "
                  "first-class vector backend, but PostgreSQL is not a graph backend: graph is "
                  "kuzu/ladybug/neo4j/networkx only.",
               "cognee/infrastructure/databases/{relational,vector,graph}/config.py"),
        "D4": (5, "Best of the three: chunk-level incremental update with staging, diff policy, "
                  "refcounted source-refs for deletion and per-chunk ownership.",
               "cognee/api/v1/update/incremental.py:1-40, databases/provenance/source_refs.py"),
        "D5": (3, "19 search types, but filtering is node_set/node_name or raw Cypher; no typed "
                  "predicate on claim status or on the closed evidence-relation enum; most "
                  "useful types are LLM-mediated.",
               "modules/search/types/SearchType.py:5-25"),
        "D6": (2, "No PROV-O model. The `provenance` package is delete-mode bookkeeping "
                  "(dataset/data/chunk source refs), and graph-side provenance only exists on "
                  "Ladybug+LanceDB.",
               "databases/provenance/markers.py:1-14"),
        "D7": (3, "Typed pydantic DataPoints can carry contract fields, but every contract must "
                  "be re-authored as classes by hand; review-event chain has no home.",
               "infrastructure/engine/models/DataPoint.py"),
        "D8": (1, "No review/attestation model; no invariant machinery (self-approval is "
                  "representable and undetected).",
               "shared/data_models.py (no review types)"),
        "D9": (2, "Relational + vector + graph store, embedder, LLM pipeline and a FastAPI "
                  "server process to operate.",
               "base_config.py, api/server.py"),
        "D10": (2, "Graph/vector content is adapter-specific; no contract-level export path.",
                "infrastructure/databases/*/adapter.py"),
        "D11": (4, "Strong: LLM entity/relation extraction, summarisation, memify enrichment, "
                   "GLiNER no-LLM alternative extractor.",
                "tasks/extract_graph*.py, memify_pipelines/"),
    },
    "Graphiti 0.31.2": {
        "D1": (2, "Library installs once a modern Rust toolchain exists (jiter builds); but no "
                  "graph backend is installable/runnable here: Kuzu has no loongarch64 wheel, "
                  "Neo4j tarball returns 403, FalkorDB/Neptune need servers.",
               "logs/graphiti_v8.log, artifacts/ke_eval/graphiti_result.json(live_attempt)"),
        "D2": (2, "46 requirements, 8 core, 1 Rust extension (jiter via openai); no conflicts.",
               "PyPI metadata graphiti-core 0.31.2"),
        "D3": (1, "No PostgreSQL backend: Neo4j / FalkorDB / Kuzu / Neptune only.",
               "graphiti_core/driver/{neo4j,falkordb,kuzu,neptune}_driver.py"),
        "D4": (4, "Episode-based incremental ingestion with LLM dedupe and contradiction "
                  "invalidation (invalid_at set, edge superseded); no deletion ledger.",
               "utils/maintenance/edge_operations.py:424-760, graphiti.py:936-982"),
        "D5": (4, "Strongest typed retrieval surface: SearchFilters(node_labels, edge_types, "
                  "valid_at/invalid_at/created_at, property_filters) + bm25/cosine/RRF/MMR/"
                  "cross-encoder recipes.",
               "search/search_filters.py:51-75, search/search_config_recipes.py:34-71"),
        "D6": (1, "Zero PROV-O vocabulary (grep for prov-o/wasAttributedTo: no hits). Edge "
                  "provenance stops at `episodes: [uuid]` mentions; valid_at/invalid_at exist, "
                  "but there is no Activity or Agent entity.",
               "graphiti_core/edges.py (EntityEdge), nodes.py (EpisodicNode)"),
        "D7": (2, "Claims/evidence/knowledge-objects collapse into EntityNode+EntityEdge; "
                  "reference arrays, review events and object-level provenance are unrepresentable.",
               "artifacts/ke_eval/graphiti_result.json(mapping_loss)"),
        "D8": (1, "No review/attestation model at all.",
               "graphiti_core/nodes.py, edges.py"),
        "D9": (2, "Requires a graph server (or embedded Kuzu) plus LLM/embedder services.",
               "graphiti_core/driver/"),
        "D10": (3, "Graph is Cypher-exportable, but the semantic shape is Graphiti's, not the "
                   "contract's.",
                "graphiti_core/driver/neo4j/"),
        "D11": (5, "Best: LLM extraction with dedupe, contradiction resolution, community "
                   "summaries, temporal edge invalidation, cross-encoder reranking.",
                "graphiti.py, utils/maintenance/*.py"),
    },
    "Self-built thin layer (PG)": {
        "D1": (5, "Installs from what the image already has: psycopg3 + PostgreSQL 15; no "
                  "downloads, works with external network disabled.",
               "artifacts/ke_eval/thinlayer_result.json"),
        "D2": (5, "Two runtime deps (psycopg3, jsonschema); no compiled extensions of our own.",
               "demos/ke_eval/thinlayer.py"),
        "D3": (5, "PostgreSQL is the store by design: schema `ke` with claims/evidence/"
                  "provenance/objects/review_event tables and in-DB cosine.",
               "demos/ke_eval/thinlayer.py DDL"),
        "D4": (3, "Idempotent upsert on (id, version) and supersede chains; no chunk-level diff "
                  "or deletion ledger (would have to be built).",
               "thinlayer.py ingest()"),
        "D5": (4, "All five primitives run and are measured: status, relation graph, recursive "
                  "provenance chain (depth 2 observed), domain, hybrid lexical+vector RRF.",
               "artifacts/ke_eval/thinlayer_result.json"),
        "D6": (5, "PROV-O is the storage contract: generated_entity/activity/agents/"
                  "derived_from are columns and export to JSON-LD prov: terms losslessly.",
               "thinlayer.py prov_o_export(), artifacts/ke_eval/thinlayer_result.json"),
        "D7": (5, "Round-trip validated 94/94 records against the four schemas with zero loss "
                  "(full payload kept in jsonb).",
               "artifacts/ke_eval/thinlayer_roundtrip.json"),
        "D8": (4, "Review events stored with a trigger that rejects self-approval (verified).",
               "thinlayer_result.json(governance_invariant)"),
        "D9": (5, "One database schema; no extra service.",
               "demos/ke_eval/thinlayer.py"),
        "D10": (5, "Export is the contract JSON itself: zero migration to leave.",
                "thinlayer.py roundtrip()"),
        "D11": (1, "No extraction/reasoning: no LLM entity linking, no contradiction detection, "
                   "no answer synthesis. Retrieval is lexical+hashed-vector only.",
                "demos/ke_eval/thinlayer.py hashed_ngram_vec()"),
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/ke_eval/decision_matrix.json")
    a = ap.parse_args()
    weights = {d[0]: d[2] for d in DIMENSIONS}
    assert sum(weights.values()) == 100, f"weights must sum to 100, got {sum(weights.values())}"

    out = {"dimensions": [{"id": d[0], "name": d[1], "weight": d[2], "meaning": d[3],
                           "evidence_anchor": d[4]} for d in DIMENSIONS],
           "options": {}, "ranking": []}
    totals = {}
    for opt, per in SCORES.items():
        rows, total = [], 0.0
        for d in DIMENSIONS:
            if d[0] not in per:
                raise SystemExit(f"missing score {opt}/{d[0]}")
            score, why, ref = per[d[0]]
            contribution = score / 5 * d[2]
            total += contribution
            rows.append({"dim": d[0], "score": score, "weight": d[2],
                         "contribution": round(contribution, 2), "why": why, "ref": ref})
        out["options"][opt] = {"rows": rows, "weighted_total": round(total, 2),
                               "normalised_100": round(total, 2)}
        totals[opt] = round(total, 2)
    out["ranking"] = sorted(totals, key=lambda k: -totals[k])
    out["winner"] = out["ranking"][0]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))

    # markdown table for the docs (generated, never hand-edited)
    lines = ["| Dim | Weight | " + " | ".join(SCORES) + " |",
             "|---|---|" + "---|" * len(SCORES)]
    for d in DIMENSIONS:
        cells = " | ".join(f"{SCORES[o][d[0]][0]}" for o in SCORES)
        lines.append(f"| {d[0]} {d[1]} | {d[2]} | {cells} |")
    lines.append("| **Weighted total (max 100)** | 100 | "
                 + " | ".join(f"**{totals[o]}**" for o in SCORES) + " |")
    md = "\n".join(lines)
    (Path(a.out).parent / "decision_matrix.md").write_text(md + "\n")
    print(md)
    print("\nranking:", out["ranking"])


if __name__ == "__main__":
    main()