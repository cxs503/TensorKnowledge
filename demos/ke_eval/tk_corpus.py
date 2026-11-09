"""Build the shared evaluation corpus for the Knowledge-Engine selection study.

Two real sources, no invented content:

A. `platform-test/epistemic-benchmark/cases/case-01..12.json` — the repository's
   own schema-validation fixtures (12 claims, 14 evidence, 12 provenance,
   12 review events). Domain: `benchmark-fixtures`.
B. Statements extracted verbatim from three internal landscape documents, with
   locators computed by searching for a marker string (so the recorded
   file:line can never drift from the document). Domains:
   `knowledge-engineering`, `standards`.

The corpus is intentionally *not* a knowledge base we claim is true: every
claim keeps its conservative status (provisional / contested / not-assessed)
and no review event is created by this builder (no self-approval).

Usage:
  python tk_corpus.py --repo . --out artifacts/ke_eval/corpus.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

# --------------------------------------------------------------------------
# B. document-derived claims.  (doc, marker, statement, relation, claim_type, domain)
# `marker` must occur exactly once in the document; the locator line number is
# derived from it at build time.
# --------------------------------------------------------------------------
DOC_CLAIMS = [
    (
        "research/global-landscape/GLOBAL_LANDSCAPE.md",
        "| 1 | Cognee |",
        "Cognee is positioned in the landscape study as an open-source ingestion/index "
        "backend rather than as a canonical governance layer.",
        "supports", "interpretive", "knowledge-engineering",
    ),
    (
        "research/global-landscape/GLOBAL_LANDSCAPE.md",
        "| 2 | Graphiti |",
        "Graphiti is positioned in the landscape study as a temporal knowledge graph for "
        "evolving facts, suitable for studying time-aware facts and relationship history.",
        "supports", "interpretive", "knowledge-engineering",
    ),
    (
        "research/global-landscape/GLOBAL_LANDSCAPE.md",
        "Cognee, Graphiti, Mem0, Letta, Hindsight and LangMem solve different",
        "External memory frameworks optimize session continuity, personalization or "
        "retrieval, whereas the platform invariant is inspectable, sourced, versioned and "
        "governed claims, so they are replaceable components.",
        "contextualizes", "normative", "knowledge-engineering",
    ),
    (
        "research/global-landscape/COMPETITIVE_ANALYSIS.md",
        "| Cognee | Core | Partial graph/source links",
        "Cognee's provenance coverage is characterized as partial graph/source links and "
        "pipeline-dependent, which qualifies any assumption of native provenance fidelity.",
        "qualifies", "descriptive", "knowledge-engineering",
    ),
    (
        "research/global-landscape/COMPETITIVE_ANALYSIS.md",
        "| Graphiti | Core | Fact/edge-level",
        "Graphiti's provenance coverage is characterized as fact/edge-level with a core "
        "temporal graph, which supports edge-scoped (not object-scoped) provenance.",
        "supports", "descriptive", "knowledge-engineering",
    ),
    (
        "research/global-landscape/STRATEGIC_GAP_ANALYSIS.md",
        "Graph ingestion/retrieval: Cognee, Graphiti, GraphRAG as replaceable backends",
        "Graph ingestion and retrieval are classified as replaceable backends, so the "
        "selection decision must be reversible.",
        "supports", "normative", "knowledge-engineering",
    ),
    (
        "research/global-landscape/STRATEGIC_GAP_ANALYSIS.md",
        "Benchmark lexical, vector and graph retrieval over approved objects",
        "Retrieval backends must be benchmarked over approved objects such that every "
        "result carries object ID/version, evidence status and provenance.",
        "supports", "methodological", "knowledge-engineering",
    ),
    (
        "research/global-landscape/STANDARDS_MAPPING.md",
        "| W3C PROV-O | Provenance of entities, activities, agents |",
        "PROV-O is one of the public specifications used as the source-discovery anchor "
        "for provenance modelling in this repository.",
        "supports", "definition", "standards",
    ),
]


def _line_of(path: Path, marker: str) -> int:
    hits = [i for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if marker in ln]
    if len(hits) != 1:
        raise SystemExit(f"marker {marker!r} occurs {len(hits)}x in {path}")
    return hits[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(repo: Path) -> dict:
    claims, evidence, prov, reviews, objects = [], [], [], [], []

    # ---- A. benchmark fixtures -------------------------------------------------
    case_paths = sorted(repo.glob("platform-test/epistemic-benchmark/cases/case-*.json"))
    if not case_paths:
        raise SystemExit("benchmark cases not found")
    for p in case_paths:
        d = json.loads(p.read_text(encoding="utf-8"))
        claims.extend(d["claims"])
        evidence.extend(d["evidence"])
        prov.append(d["provenance"])
        reviews.extend(d.get("review_events", []))
        for c in d["claims"]:
            objects.append({
                "id": f"tko:benchmark:{d['case_id'].split(':')[-1]}",
                "title": f"Benchmark case {d['case_id']} ({d['category']})",
                "object_type": "concept",
                "domains": ["benchmark-fixtures"],
                "summary": d["description"],
                "evidence_status": c.get("epistemic_status", "not-assessed"),
                "review_status": "in-review",
                "version": "0.1.0",
                "claim_refs": [c["id"]],
                "evidence_refs": list(c.get("evidence_refs", [])),
                "sources": [{"source_type": "internal-artifact",
                             "citation": f"benchmark case fixture {p.name}",
                             "locator": f"{p.relative_to(repo)}",
                             "accessed_at": "2026-11-09"}],
            })

    # ---- B. document-derived claims -------------------------------------------
    for i, (rel_path, marker, statement, relation, ctype, domain) in enumerate(DOC_CLAIMS, 1):
        doc = repo / rel_path
        line = _line_of(doc, marker)
        cid = f"tkc:landscape:{Path(rel_path).stem.lower().replace('_', '-')}-{i:02d}"
        eid = f"tke:landscape:{Path(rel_path).stem.lower().replace('_', '-')}-{i:02d}-ev"
        pid = f"tkp:landscape:{Path(rel_path).stem.lower().replace('_', '-')}-{i:02d}-prov"
        oid = f"tko:landscape:{Path(rel_path).stem.lower().replace('_', '-')}-{i:02d}"
        claims.append({
            "id": cid,
            "statement": statement,
            "claim_type": ctype,
            "scope": {"domain": domain, "system": "TensorKnowledge",
                      "conditions": ["internal landscape document, as of repo HEAD"]},
            "modality": "asserted",
            "epistemic_status": "provisional",
            "evidence_refs": [eid],
            "created_at": "2026-11-09T00:00:00Z",
            "created_by": "ke-eval-agent",
            "version": "0.1.0",
        })
        evidence.append({
            "id": eid,
            "claim_refs": [cid],
            "source": {
                "source_type": "internal-artifact",
                "citation": f"TensorKnowledge {rel_path} line {line}",
                "url": f"repo://{rel_path}",
            },
            "relation": relation,
            "locator": {"locator_type": "code-location", "value": f"{rel_path}:{line}",
                        "content_hash": _sha256(doc)},
            "extraction_method": "manual-paraphrase",
            "captured_at": "2026-11-09T00:00:00Z",
            "captured_by": "ke-eval-agent",
            "assessment_status": "unassessed",
            "version": "0.1.0",
        })
        prov.append({
            "id": pid,
            "generated_entity": {"id": cid, "entity_type": "claim", "version": "0.1.0"},
            "activity": {
                "id": f"activity-ke-eval-{i:02d}",
                "activity_type": "extraction",
                "description": "Paraphrase extraction of one statement from an internal "
                               "landscape document for engine evaluation.",
                "started_at": "2026-11-09T00:00:00Z",
                "used_entities": [f"repo-doc:{rel_path}"],
                "software": [
                    {"name": "demos/ke_eval/tk_corpus.py", "version": "0.1.0"},
                    {"name": "python", "version": "3.11.6"},
                ],
            },
            "agents": [{"id": "ke-eval-agent", "agent_type": "software-agent",
                        "name": "TensorKnowledge KE evaluation agent",
                        "role": "extractor"}],
            "derived_from": [eid, f"repo-doc:{rel_path}"],
            "recorded_at": "2026-11-09T00:00:00Z",
            "version": "0.1.0",
        })
        # provenance record for the evidence entity itself, so the stored
        # provenance graph has depth 2 (claim <- evidence <- repository document)
        prov.append({
            "id": pid + "-ev",
            "generated_entity": {"id": eid, "entity_type": "evidence", "version": "0.1.0"},
            "activity": {
                "id": f"activity-ke-eval-extract-{i:02d}",
                "activity_type": "extraction",
                "description": "Locator resolution: marker string -> line number in the document.",
                "started_at": "2026-11-09T00:00:00Z",
                "used_entities": [f"repo-doc:{rel_path}"],
                "software": [{"name": "demos/ke_eval/tk_corpus.py", "version": "0.1.0"}],
            },
            "agents": [{"id": "ke-eval-agent", "agent_type": "software-agent",
                        "name": "TensorKnowledge KE evaluation agent", "role": "locator-resolver"}],
            "derived_from": [f"repo-doc:{rel_path}"],
            "recorded_at": "2026-11-09T00:00:00Z",
            "version": "0.1.0",
        })
        objects.append({
            "id": oid,
            "title": f"{Path(rel_path).stem} statement {i:02d}",
            "object_type": "concept",
            "domains": [domain],
            "summary": statement,
            "evidence_status": "provisional",
            "review_status": "draft",
            "version": "0.1.0",
            "claim_refs": [cid],
            "evidence_refs": [eid],
            "provenance_refs": [pid],
            "sources": [{"source_type": "internal-artifact",
                         "citation": f"TensorKnowledge {rel_path} line {line}",
                         "locator": f"{rel_path}:{line}#sha256={_sha256(doc)}",
                         "accessed_at": "2026-11-09"}],
        })

    return {"claims": claims, "evidence": evidence, "provenance": prov,
            "review_events": reviews, "objects": objects}


def validate(repo: Path, corpus: dict) -> dict:
    """Validate every record against the repository's own JSON Schemas."""
    import jsonschema

    mapping = {"claims": "claim-record", "evidence": "evidence-record",
               "provenance": "provenance-record", "review_events": "review-event",
               "objects": "knowledge-object"}
    report = {}
    for key, schema_name in mapping.items():
        schema = json.loads((repo / "schemas" / f"{schema_name}.schema.json").read_text())
        ok = 0
        errors = []
        for rec in corpus[key]:
            try:
                jsonschema.validate(rec, schema)
                ok += 1
            except jsonschema.ValidationError as exc:  # pragma: no cover - evidence
                errors.append({"record": rec.get("id"), "error": str(exc)[:300]})
        report[key] = {"records": len(corpus[key]), "valid": ok, "errors": errors[:5]}
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="artifacts/ke_eval/corpus.json")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    corpus = build(repo)
    report = validate(repo, corpus)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"corpus": corpus, "validation": report}, indent=1))
    print(json.dumps({"counts": {k: len(v) for k, v in corpus.items()},
                      "validation": {k: {kk: vv for kk, vv in v.items() if kk != "errors"}
                                     for k, v in report.items()}}, indent=1))
    bad = {k: v["errors"] for k, v in report.items() if v["errors"]}
    if bad:
        print("VALIDATION ERRORS:", json.dumps(bad, indent=1)[:2000])


if __name__ == "__main__":
    main()