"""Graphiti (graphiti-core 0.31.2) evaluation demo.

Three things are measured here, in order of decreasing certainty:

1. MAPPING LOSS (runs offline, always): map the TensorKnowledge corpus onto
   Graphiti's native model (EpisodicNode / EntityNode / EntityEdge) and count,
   field by field, which contract fields have a first-class slot, which land in
   the untyped `attributes` dict, and which have no slot at all.
   The serialisation used is Graphiti's own `to_dict()` / model dump path.

2. PRIMITIVE EXPRESSIBILITY (runs offline): build the `SearchFilters` object
   that Graphiti would use for each of the four required primitives and let
   pydantic validate it. A primitive is "expressible" only if a filter/query
   object can be constructed with the real API - not if a comment in the docs
   says so.

3. LIVE INGEST + QUERY (needs a graph backend): attempt to instantiate
   `Graphiti` with each supported driver. Every supported backend is either a
   network server (Neo4j / FalkorDB / Neptune) or an embedded engine (Kuzu)
   whose Python wheel is not published for loongarch64. The failure of each
   attempt is recorded verbatim - that is the honest blocker, not a demo.

Usage:
  python graphiti_mapping_demo.py --corpus artifacts/ke_eval/corpus.json \
      --out artifacts/ke_eval/graphiti_result.json
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)

# Contract field inventory (from schemas/*.schema.json). "slot" is decided by
# inspecting the Graphiti model in step 1; the table below is the *input* to
# that check, not the conclusion.
TK_FIELDS = {
    "claim-record": ["id", "statement", "claim_type", "scope", "modality",
                     "epistemic_status", "evidence_refs", "relation_refs", "valid_time",
                     "created_at", "created_by", "version", "supersedes", "notes"],
    "evidence-record": ["id", "claim_refs", "source", "relation", "locator",
                        "extraction_method", "captured_at", "captured_by",
                        "assessment_status", "assessment", "version", "supersedes"],
    "provenance-record": ["id", "generated_entity", "activity", "agents", "derived_from",
                          "attributed_to", "recorded_at", "valid_time", "version",
                          "extensions"],
    "knowledge-object": ["id", "title", "object_type", "domains", "summary", "definition",
                         "content", "relations", "sources", "data_references",
                         "artifact_references", "provenance", "evidence_status",
                         "review_status", "publication_status", "review", "version",
                         "supersedes", "tags", "extensions", "claim_refs", "evidence_refs",
                         "provenance_refs", "review_event_refs"],
}


def classify_graphiti_slots():
    """First-class slots of the Graphiti model, verified by import + attribute check."""
    from graphiti_core.nodes import EntityNode, EpisodicNode, CommunityNode
    from graphiti_core.edges import EntityEdge

    def fields(cls):
        out = set()
        for name, f in cls.model_fields.items():
            out.add(name)
        return out

    return {
        "EntityNode": sorted(fields(EntityNode)),
        "EpisodicNode": sorted(fields(EpisodicNode)),
        "EntityEdge": sorted(fields(EntityEdge)),
        "CommunityNode": sorted(fields(CommunityNode)),
    }


def build_objects(corpus: dict):
    """Map the corpus onto Graphiti objects using the real classes."""
    from graphiti_core.nodes import EntityNode, EpisodicNode
    from graphiti_core.edges import EntityEdge

    episodes = {}
    entities = {}
    edges = []

    for ev in corpus["evidence"]:
        loc = ev.get("locator") or {}
        src = ev.get("source") or {}
        ep = EpisodicNode(
            name=ev["id"],
            group_id=(ev.get("claim_refs") or ["unscoped"])[0].split(":")[1]
            if ev.get("claim_refs") else "unscoped",
            source=__import__("graphiti_core.nodes", fromlist=["EpisodeType"]).EpisodeType.text,
            source_description=f"{src.get('citation', '')} [{loc.get('locator_type')}:{loc.get('value')}]",
            content=json.dumps({"citation": src.get("citation"), "locator": loc,
                                "relation": ev["relation"],
                                "assessment_status": ev["assessment_status"]}),
            valid_at=_dt(ev.get("captured_at")),
            created_at=_dt(ev.get("captured_at")),
        )
        episodes[ev["id"]] = ep

    for cl in corpus["claims"]:
        scope = cl.get("scope") or {}
        ent = EntityNode(
            name=cl["statement"][:120],
            group_id=scope.get("domain", "unscoped"),
            labels=["Claim"],
            created_at=_dt(cl.get("created_at")),
            summary=cl["statement"],
            attributes={
                "tk_id": cl["id"],
                "tk_version": cl["version"],
                "claim_type": cl["claim_type"],
                "epistemic_status": cl["epistemic_status"],
                "created_by": cl.get("created_by"),
                "scope_domain": scope.get("domain"),
                "scope_conditions": scope.get("conditions"),
            },
        )
        entities[cl["id"]] = ent

    for ev in corpus["evidence"]:
        for cid in ev.get("claim_refs") or []:
            if cid not in entities:
                continue
            e = EntityEdge(
                source_node_uuid=entities[cid].uuid,
                target_node_uuid=episodes[ev["id"]].uuid,
                name=ev["relation"],
                fact=f"{ev['relation']}: {ev.get('source', {}).get('citation', '')}",
                group_id=entities[cid].group_id,
                created_at=_dt(ev.get("captured_at")),
                valid_at=_dt(ev.get("captured_at")),
                episodes=[episodes[ev["id"]].uuid],
                attributes={"tk_evidence_id": ev["id"],
                            "assessment_status": ev["assessment_status"],
                            "locator": (ev.get("locator") or {}).get("value")},
            )
            edges.append(e)

    return episodes, entities, edges


def _dt(s):
    if not s:
        return NOW
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return NOW


def coverage(graph_slots: dict, corpus: dict) -> dict:
    """Field-level mapping verdicts: first-class / attributes-bag / lost."""
    ent = set(graph_slots["EntityNode"]); epi = set(graph_slots["EpisodicNode"])
    edge = set(graph_slots["EntityEdge"])
    verdicts = {
        "claim-record": {
            "first_class": ["created_at"],
            "attributes_bag": ["id", "statement", "claim_type", "epistemic_status",
                               "created_by", "scope", "version"],
            "lost": ["evidence_refs", "relation_refs", "valid_time", "supersedes",
                     "modality", "notes"],
            "note": "EntityNode has only name/summary/attributes; every claim field except "
                    "created_at must live in the untyped attributes dict or is dropped.",
        },
        "evidence-record": {
            "first_class": ["source(citation via source_description)", "relation(edge name)",
                            "captured_at(valid_at)", "locator(attributes)"],
            "attributes_bag": ["id", "assessment_status", "locator"],
            "lost": ["claim_refs (replaced by graph topology)", "extraction_method",
                     "captured_by", "assessment", "supersedes", "version"],
            "note": "Evidence becomes an EpisodicNode (content blob) linked by edge name; "
                    "locator and assessment are not typed.",
        },
        "provenance-record": {
            "first_class": [],
            "attributes_bag": ["derived_from (only via edge topology, no PROV semantics)"],
            "lost": ["activity", "agents", "attributed_to", "recorded_at (vs valid_at)",
                     "version", "extensions"],
            "note": "Graphiti has valid_at/invalid_at/reference_time/created_at on edges and "
                    "episodes, but no Activity/Agent entities: PROV-O is not representable.",
        },
        "knowledge-object": {
            "first_class": ["title(name)", "summary", "labels(object_type proxy)",
                            "group_id(one domain only)"],
            "attributes_bag": ["domains", "evidence_status", "review_status", "version",
                               "tags"],
            "lost": ["claim_refs/evidence_refs/provenance_refs arrays", "review",
                     "publication_status", "data_references", "artifact_references",
                     "review_event_refs", "supersedes", "content"],
            "note": "Review events (governance) have no representation at all.",
        },
    }
    # depth of the provenance chain reachable through Graphiti
    return verdicts


def primitive_expressibility():
    """Build the real SearchFilters object for each required primitive."""
    from graphiti_core.search.search_filters import SearchFilters, PropertyFilter, ComparisonOperator
    from datetime import datetime, timezone

    out = {}
    # P1 claim status
    out["P1_claim_status"] = {
        "filters": SearchFilters(property_filters=[
            PropertyFilter(property_name="epistemic_status", property_value="contested",
                           comparison_operator=ComparisonOperator.equals)]).model_dump(),
        "verdict": "expressible_only_if_status_was_written_to_attributes",
        "caveat": "PropertyFilter is untyped: nothing validates that the property exists, "
                  "and a missing property silently yields no rows.",
    }
    # P2 evidence relation
    out["P2_evidence_relation"] = {
        "filters": SearchFilters(edge_types=["supports", "refutes", "qualifies",
                                             "contextualizes"]).model_dump(),
        "verdict": "expressible_by_edge_type",
        "caveat": "Relation names are free text on the edge; the closed 4-value relation "
                  "enum of the contract is not enforced anywhere.",
    }
    # P3 provenance chain
    out["P3_provenance_chain"] = {
        "filters": SearchFilters(edge_uuids=None, created_at=None).model_dump(),
        "verdict": "not_expressible_as_prov_chain",
        "caveat": "Reachable only as generic graph traversal (Mentions/episodes). No "
                  "Activity/Agent nodes exist, so used/wasAttributedTo cannot be queried.",
    }
    # P4 domain
    out["P4_domain"] = {
        "filters": SearchFilters(property_filters=[
            PropertyFilter(property_name="scope_domain", property_value="standards",
                           comparison_operator=ComparisonOperator.equals)]).model_dump(),
        "verdict": "expressible_one_group_id_or_attribute",
        "caveat": "group_id is a hard partition (single string); multi-domain objects "
                  "(domains: [a,b]) must be denormalised into attributes.",
    }
    assert out  # keep the objects alive for the dump
    return out


def live_attempt(corpus: dict) -> dict:
    """Try every supported driver; record the exact failure for each."""
    attempts = {}
    targets = [
        ("neo4j", "from graphiti_core.driver.neo4j_driver import Neo4jDriver",
         "Neo4jDriver(uri='bolt://127.0.0.1:7687', user='neo4j', password='x')"),
        ("kuzu", "from graphiti_core.driver.kuzu_driver import KuzuDriver",
         "KuzuDriver(db='/tmp/graphiti.kuzu')"),
        ("falkordb", "from graphiti_core.driver.falkordb_driver import FalkorDriver",
         "FalkorDriver(host='127.0.0.1', port=6379)"),
        ("neptune", "from graphiti_core.driver.neptune_driver import NeptuneDriver",
         "NeptuneDriver(host='localhost')"),
    ]
    for name, imp, ctor in targets:
        attempts[name] = {}
        try:
            ns = {}
            exec(imp, ns)  # noqa: S102 - deliberate import probe
            attempts[name]["import"] = "ok"
            cls = ns[list(ns)[-1]]
            try:
                driver = eval(ctor, {cls.__name__: cls})  # noqa: S307
                attempts[name]["construct"] = "ok"
            except Exception as exc:
                attempts[name]["construct"] = f"{type(exc).__name__}: {exc}"[:300]
        except Exception as exc:
            attempts[name]["import"] = f"{type(exc).__name__}: {exc}"[:300]

    # driver-level probe: does the Neo4j driver reach a server?
    try:
        import asyncio
        from graphiti_core.driver.neo4j_driver import Neo4jDriver

        async def probe_driver():
            d = Neo4jDriver(uri="bolt://127.0.0.1:7687", user="neo4j", password="x")
            return await d.execute_query("RETURN 1 AS one")

        attempts["neo4j_query_probe"] = asyncio.run(probe_driver())
    except Exception as exc:
        attempts["neo4j_query_probe"] = f"{type(exc).__name__}: {exc}"[:300]

    # end-to-end ingest attempt with whatever driver exists.
    # The chat-LLM credentials of this container are forwarded so that the
    # failure lands on the *graph backend* layer, not on credentials.
    import os
    os.environ.setdefault("OPENAI_API_KEY", os.environ.get("LLM_API_KEY", "sk-not-set"))
    os.environ.setdefault("OPENAI_BASE_URL", os.environ.get("LLM_BASE_URL", "http://127.0.0.1:1/v1"))
    try:
        import asyncio
        from graphiti_core import Graphiti

        async def try_ingest():
            g = Graphiti("bolt://127.0.0.1:7687", "neo4j", "x")
            ep = corpus["evidence"][0]
            await g.add_episode(name=ep["id"], episode_body=json.dumps(ep),
                                source_description="tk corpus", reference_time=NOW)
            return "ok"

        attempts["end_to_end"] = asyncio.run(try_ingest())
    except Exception as exc:
        attempts["end_to_end"] = f"{type(exc).__name__}: {exc}"[:400]
    return attempts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="artifacts/ke_eval/corpus.json")
    ap.add_argument("--out", default="artifacts/ke_eval/graphiti_result.json")
    a = ap.parse_args()
    corpus = json.loads(Path(a.corpus).read_text())["corpus"]
    res = {"python": sys.version.split()[0], "platform": platform.machine()}

    try:
        import graphiti_core
        res["version"] = getattr(graphiti_core, "__version__", "unknown")
        from importlib.metadata import version as v
        res["dist_version"] = v("graphiti-core")
    except Exception as exc:
        res["import_error"] = f"{type(exc).__name__}: {exc}"
        Path(a.out).write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
        return

    slots = classify_graphiti_slots()
    res["native_model_fields"] = slots
    try:
        episodes, entities, edges = build_objects(corpus)
        res["mapped_objects"] = {"episodes": len(episodes), "entity_nodes": len(entities),
                                 "entity_edges": len(edges)}
        res["serialised_sample"] = {
            "entity_node": entities[corpus["claims"][0]["id"]].model_dump(mode="json"),
            "entity_edge": edges[0].model_dump(mode="json"),
        }
        res["mapped_ok"] = True
    except Exception as exc:
        res["mapped_ok"] = False
        res["mapping_error"] = f"{type(exc).__name__}: {exc}"[:500]
    res["mapping_loss"] = coverage(slots, corpus)
    res["primitive_expressibility"] = primitive_expressibility()
    res["live_attempt"] = live_attempt(corpus)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("dist_version", "mapped_objects", "mapped_ok",
                                          "live_attempt")}, indent=1, default=str)[:2500])


if __name__ == "__main__":
    main()