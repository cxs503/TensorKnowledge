#!/usr/bin/env python3
"""Knowledge Engine (KE) projection library — mapping spec v0.1.

Single source of truth for *how* the four TensorKnowledge epistemic contracts
(claim / evidence / provenance / review-event) plus the Knowledge Object
aggregate are projected into the engine entity-graph-vector model.

Implements docs/ke/mapping-spec.md §2 (entities), §3 (edges), §4 (state machine
-> scripts/ke_state_machine.py), §5 (epistemic conservativeness), §6 (bi-temporal
split), §7 (vector facets), §8 (retrieval classes, executed on real records).

Audit contract: the source record is authoritative and stored verbatim in `raw`.
Every leaf field path must be covered by a projection rule (L0..L3) or listed as
an explicit L4 semantic-loss disclosure. scripts/validate_ke_mapping.py enforces
this, so "no loss, or a disclosed loss register" is machine-checked.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

POLICY_VERSION = "ke-mapping-v0.1"
REVIEW_POLICY_VERSION = "ke-review-v0.1"
PROJECTION_VERSION = "ke-projection-v0.1"
CONTRACT_VERSIONS = {"claim": "1.0.0", "evidence": "1.0.0", "provenance": "1.0.0",
                     "ko": "1.0.0", "envelope": "0.1.0"}

LOSS_CLASSES = {
    "L0": "verbatim, queryable 1:1",
    "L1": "queryable after documented normalization (original kept in raw)",
    "L2": "expanded into graph structure (node/edge set carries the information)",
    "L3": "retained in raw only, deliberately not a queryable column",
    "L4": "not representable in the engine model (semantic loss, must be disclosed)",
}

# (kind, path pattern, engine slot, loss class, note, vector facet)
RULES: list[tuple[str, str, str, str, str, str | None]] = [
    # ------------------------------ claim-record
    ("claim", "id", "entity.entity_id", "L0", "primary key, verbatim, never rewritten", None),
    ("claim", "statement", "claim.statement", "L0", "vector facet claim.statement", "claim.statement"),
    ("claim", "claim_type", "claim.claim_type", "L0", "closed enum from contract", None),
    ("claim", "scope.domain", "claim.scope.domain", "L0", "domain facet for by-domain query", None),
    ("claim", "scope.population", "claim.scope.population", "L0", "", None),
    ("claim", "scope.system", "claim.scope.system", "L0", "", None),
    ("claim", "scope.geography", "claim.scope.geography", "L0", "", None),
    ("claim", "scope.conditions[*]", "claim.scope.conditions[]", "L0", "scope returned with every hit; never silently dropped", None),
    ("claim", "scope.exclusions[*]", "claim.scope.exclusions[]", "L0", "", None),
    ("claim", "modality", "claim.modality", "L0", "", None),
    ("claim", "epistemic_status", "status.epistemic_status", "L0", "as recorded + policy_cap + over_grade flag (§5)", None),
    ("claim", "evidence_refs[*]", "edges:EVIDENCE_OF", "L2", "resolved to edge; symmetry with evidence.claim_refs checked", None),
    ("claim", "relation_refs[*]", "edges:CLAIM_RELATED", "L2", "", None),
    ("claim", "valid_time.start", "bitemporal.valid_time.start", "L1", "normalized to UTC instant", None),
    ("claim", "valid_time.end", "bitemporal.valid_time.end", "L1", "", None),
    ("claim", "valid_time.description", "bitemporal.valid_time.description", "L0", "prose validity note; resolution=prose-only when start/end absent", None),
    ("claim", "created_at", "bitemporal.recorded_at", "L1", "transaction time, immutable", None),
    ("claim", "created_by", "recorded.created_by.raw", "L0", "canonical identity parsed alongside raw (§4)", None),
    ("claim", "version", "entity.version", "L0", "", None),
    ("claim", "supersedes[*]", "edges:SUPERSEDES", "L2", "append-only; superseded row is not mutated", None),
    ("claim", "notes[*]", "claim.notes[]", "L0", "author limitations stay attached to the claim", None),
    # --------------------------- evidence-record
    ("evidence", "id", "entity.entity_id", "L0", "", None),
    ("evidence", "claim_refs[*]", "edges:EVIDENCE_OF", "L2", "direction stored once, indexed both ways", None),
    ("evidence", "source.source_type", "source.source_type", "L0", "", None),
    ("evidence", "source.citation", "source.citation", "L0", "source node key fallback = sha256(citation)", None),
    ("evidence", "source.url", "source.url", "L0", "", None),
    ("evidence", "source.persistent_id", "source.persistent_id", "L0", "preferred source node key", None),
    ("evidence", "source.publisher", "source.publisher", "L0", "", None),
    ("evidence", "source.published_at", "source.published_at", "L1", "date -> date@00:00Z; NOT a validity bound", None),
    ("evidence", "source.accessed_at", "source.accessed_at", "L1", "", None),
    ("evidence", "source.rights", "source.rights", "L0", "quotation/rights limit travels with the quote", None),
    ("evidence", "relation", "edge.relation", "L0", "edge attribute, never an entity attribute (multi-claim safe)", None),
    ("evidence", "locator.locator_type", "evidence.locator_type", "L0", "", None),
    ("evidence", "locator.value", "evidence.locator_value", "L0", "", None),
    ("evidence", "locator.quote", "evidence.quote", "L0", "verbatim excerpt; facet evidence.quote", "evidence.quote"),
    ("evidence", "locator.quote_language", "evidence.quote_language", "L0", "language tag; retrieval must not assume claim/evidence same language", None),
    ("evidence", "locator.start_offset", "evidence.locator_start_offset", "L0", "absent here -> no char-level anchor", None),
    ("evidence", "locator.end_offset", "evidence.locator_end_offset", "L0", "", None),
    ("evidence", "extraction_method", "evidence.extraction_method", "L0", "direct-quotation gate for §5 cap", None),
    ("evidence", "captured_at", "bitemporal.recorded_at", "L1", "", None),
    ("evidence", "captured_by", "recorded.captured_by.raw", "L0", "", None),
    ("evidence", "assessment_status", "evidence.assessment_status", "L0", "independent of review_status (A3)", None),
    ("evidence", "assessment.assessor", "evidence.assessment.assessor", "L0", "", None),
    ("evidence", "assessment.assessed_at", "bitemporal.assessed_at", "L1", "", None),
    ("evidence", "assessment.rationale", "evidence.assessment.rationale", "L0", "", None),
    ("evidence", "assessment.confidence", "evidence.assessment.confidence", "L0", "", None),
    ("evidence", "version", "entity.version", "L0", "", None),
    ("evidence", "supersedes[*]", "edges:SUPERSEDES", "L2", "", None),
    # ------------------------- provenance-record
    ("provenance", "id", "entity.entity_id", "L0", "", None),
    ("provenance", "generated_entity.id", "prov.generated_entity.id", "L0", "", None),
    ("provenance", "generated_entity.entity_type", "prov.generated_entity.entity_type", "L0", "", None),
    ("provenance", "generated_entity.version", "prov.generated_entity.version", "L0", "", None),
    ("provenance", "activity.id", "prov.activity.id", "L0", "PROV-O prov:Activity node", None),
    ("provenance", "activity.activity_type", "prov.activity.activity_type", "L0", "", None),
    ("provenance", "activity.description", "prov.activity.description", "L0", "", None),
    ("provenance", "activity.started_at", "bitemporal.activity.started_at", "L1", "", None),
    ("provenance", "activity.ended_at", "bitemporal.activity.ended_at", "L1", "", None),
    ("provenance", "activity.used_entities[*]", "edges:USED", "L2", "local id -> entity node, else external_source node", None),
    ("provenance", "activity.software[*].name", "prov.software[].name", "L0", "", None),
    ("provenance", "activity.software[*].version", "prov.software[].version", "L0", "empty -> version_unknown=true, never invented", None),
    ("provenance", "agents[*].id", "prov.agent.id", "L0", "agent node; feeds the identity alias set (§4)", None),
    ("provenance", "agents[*].agent_type", "prov.agent.agent_type", "L0", "", None),
    ("provenance", "agents[*].name", "prov.agent.name", "L0", "", None),
    ("provenance", "agents[*].role", "prov.agent.role", "L0", "", None),
    ("provenance", "agents[*].external_id", "prov.agent.external_id", "L0", "external job id, not resolvable platform-side", None),
    ("provenance", "attributed_to[*]", "edges:ATTRIBUTED_TO", "L2", "accountability, distinct from authorship", None),
    ("provenance", "derived_from[*]", "edges:DERIVED_FROM", "L2", "", None),
    ("provenance", "recorded_at", "bitemporal.recorded_at", "L1", "", None),
    ("provenance", "valid_time.start", "bitemporal.valid_time.start", "L1", "", None),
    ("provenance", "valid_time.end", "bitemporal.valid_time.end", "L1", "", None),
    ("provenance", "version", "entity.version", "L0", "", None),
    ("provenance", "extensions", "raw:extensions", "L3", "open extension bag kept raw-only by policy", None),
    # -------------------------- knowledge-object
    ("ko", "id", "entity.entity_id", "L0", "", None),
    ("ko", "title", "ko.title", "L0", "", None),
    ("ko", "object_type", "ko.object_type", "L0", "", None),
    ("ko", "domains[*]", "ko.domains[]", "L0", "", None),
    ("ko", "summary", "ko.summary", "L0", "vector facet ko.summary", "ko.summary"),
    ("ko", "evidence_status", "status.evidence_status", "L0", "aggregate envelope status; never overwrites a claim's status", None),
    ("ko", "review_status", "status.review_status", "L0", "must equal fold(review-event ledger) (§4)", None),
    ("ko", "publication_status", "status.publication_status", "L0", "", None),
    ("ko", "version", "entity.version", "L0", "", None),
    ("ko", "relations[*].relation_type", "edges:KO_REL.relation_type_raw", "L1", "open vocabulary normalized to a closed enum; raw token kept on the edge", None),
    ("ko", "relations[*].target_id", "edges:KO_REL", "L2", "", None),
    ("ko", "relations[*].note", "edges:KO_REL.note", "L0", "", None),
    ("ko", "sources[*]/**", "ko.sources[]", "L3", "envelope source list; canonical source nodes come from evidence", None),
    ("ko", "definition", "ko.definition", "L0", "", None),
    ("ko", "provenance.created_by", "recorded.created_by.raw", "L0", "KO-level author, parsed like claim.created_by", None),
    ("ko", "provenance.created_at", "bitemporal.recorded_at", "L1", "", None),
    ("ko", "provenance.method", "ko.provenance.method", "L0", "", None),
    ("ko", "provenance.agent_assisted", "ko.provenance.agent_assisted", "L0", "declares machine involvement under human accountability", None),
    ("ko", "provenance.work_package_id", "ko.provenance.work_package_id", "L0", "links the object back to the work package", None),
    ("ko", "provenance.parent_versions[*]", "edges:SUPERSEDES", "L2", "", None),
    ("ko", "content", "ko.content", "L3", "free-form body raw-only", None),
    ("ko", "claim_refs[*]", "edges:KO_INCLUDES_CLAIM", "L2", "schema-sanctioned link field", None),
    ("ko", "evidence_refs[*]", "edges:KO_INCLUDES_EVIDENCE", "L2", "", None),
    ("ko", "provenance_refs[*]", "edges:KO_INCLUDES_PROVENANCE", "L2", "", None),
    ("ko", "review_event_refs[*]", "edges:HAS_REVIEW_EVENT", "L2", "", None),
    # --------------------- production-result envelope
    ("envelope", "contract_version", "envelope.contract_version", "L0", "", None),
    ("envelope", "package_id", "envelope.package_id", "L0", "", None),
    ("envelope", "platform_task_id", "envelope.platform_mission_ref", "L0", "namespaced platform:mission:<id>; never joined into review_status (A3)", None),
    ("envelope", "execution_state", "envelope.platform_state", "L0", "read-only mirror of Platform state; never a review input", None),
    ("envelope", "completed_at", "bitemporal.recorded_at", "L1", "", None),
    ("envelope", "outcome", "envelope.outcome", "L0", "", None),
    ("envelope", "summary", "envelope.summary", "L3", "prose; raw-only", None),
    ("envelope", "proposed_objects[*]", "entity:knowledge-object", "L2", "each element projected as its own entity", None),
    ("envelope", "artifact_references[*]", "edges:ARTIFACT_REF", "L2", "", None),
    ("envelope", "evidence_and_sources[*]", "envelope.evidence_and_sources[]", "L3", "denormalized duplicate of evidence records; canonical = evidence nodes", None),
    ("envelope", "checks[*]/**", "envelope.checks[]", "L0", "machine-checkable run evidence (check/status/evidence)", None),
    ("envelope", "proposed_objects[*]/**", "entity:knowledge-object", "L2",
     "leaf projected through the KO entity; its own coverage is audited on that record", None),
    ("envelope", "unresolved_issues[*]", "envelope.unresolved_issues[]", "L0", "", None),
    ("envelope", "limitations[*]", "envelope.limitations[]", "L3", "prose; raw-only", None),
    ("envelope", "confidence_statement", "envelope.confidence_statement", "L3", "", None),
    ("envelope", "agent_attribution[*]", "envelope.agent_attribution[]", "L3", "prose attribution; canonical agents come from provenance", None),
]

# ---------------------------------------------------------------------------
# leaf paths + rule matching
# ---------------------------------------------------------------------------

def leaves(obj: Any, prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        if not obj:
            out.append((prefix, {}))
        for key, val in obj.items():
            out.extend(leaves(val, key if not prefix else f"{prefix}.{key}"))
    elif isinstance(obj, list):
        if not obj:
            out.append((prefix, []))
        for idx, val in enumerate(obj):
            out.extend(leaves(val, f"{prefix}[{idx}]"))
    else:
        out.append((prefix, obj))
    return out


def _regex(pattern: str) -> re.Pattern[str]:
    body = re.escape(pattern).replace(r"\[\*\]", r"\[\d+\]")
    if pattern.endswith("/**"):
        body = body[: -len(r"/\*\*")] + r"(\..*)?"
    return re.compile(f"^{body}$")


def _specificity(pattern: str) -> int:
    return len(pattern.replace("[*]", "").replace("/**", ""))


_COMPILED = [(_regex(p), _specificity(p), r) for r in RULES for p in [r[1]]]


def match_rule(kind: str, path: str):
    best = None
    for regex, spec, rule in _COMPILED:
        if rule[0] != kind or not regex.match(path):
            continue
        if best is None or spec > best[0]:
            best = (spec, rule[2], rule[3], rule[4], rule[5])
    if best is None:
        return None
    return best[1], best[2], best[3], best[4]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def project(kind: str, record: dict[str, Any]) -> dict[str, Any]:
    covered, uncovered, slots = [], [], {}
    for path, value in leaves(record):
        rule = match_rule(kind, path)
        if rule is None:
            uncovered.append({"source_path": path, "value_preview": str(value)[:80]})
            continue
        slot, loss, note, facet = rule
        covered.append({"source_path": path, "engine_slot": slot,
                        "loss_class": loss, "note": note, "facet": facet})
        if slot.endswith("[]"):
            slots.setdefault(slot, []).append(value)
        elif "/" not in slot and ":" not in slot:
            slots[slot] = value
    return {
        "kind": kind,
        "raw_sha256": sha256_text(json.dumps(record, ensure_ascii=False, sort_keys=True)),
        "raw_bytes": len(json.dumps(record, ensure_ascii=False).encode("utf-8")),
        "leaf_paths": len(covered) + len(uncovered),
        "covered": covered,
        "uncovered": uncovered,
        "slots": slots,
    }


# ---------------------------------------------------------------------------
# epistemic conservativeness (§5)
# ---------------------------------------------------------------------------
LADDER = {"not-assessed": 0, "speculative": 1, "provisional": 2,
          "well-supported": 3, "established": 4}
OFF_LADDER = {"contested", "superseded"}
ASSESSMENT_GRADE = {"insufficient": 0, "unassessed": 1, "disputed": 2,
                    "reviewed-qualifies": 2, "reviewed-refutes": 3, "reviewed-supports": 3}


def capture_quality(evidence: dict[str, Any]) -> int:
    score = 0
    locator = evidence.get("locator", {}) or {}
    if locator.get("value"):
        score += 1
    if locator.get("quote"):
        score += 1
    source = evidence.get("source", {}) or {}
    if source.get("persistent_id") or source.get("url"):
        score += 1
    return score


def conservative_cap(claim: dict[str, Any], evidences: list[dict[str, Any]]) -> dict[str, Any]:
    """Highest epistemic_status the evidence projection can justify (spec §5, T-5.2)."""
    if not evidences:
        return {"cap": "not-assessed", "basis": "no evidence edges"}
    grade = lambda ev: ASSESSMENT_GRADE.get(str(ev.get("assessment_status")), 1)
    anchored = [ev for ev in evidences if capture_quality(ev) >= 2]

    if any(ev.get("relation") == "refutes" and grade(ev) >= 1 and capture_quality(ev) >= 2
           for ev in evidences):
        return {"cap": "contested",
                "basis": "anchored refuting evidence retained on the claim (an excerpt judged "
                         "insufficient cannot contend; an unassessed anchored excerpt can)"}

    assessed_sources = {
        (ev.get("source", {}).get("persistent_id") or ev.get("source", {}).get("url")
         or ev.get("source", {}).get("citation"))
        for ev in evidences
        if ev.get("relation") == "supports" and grade(ev) >= 3 and capture_quality(ev) >= 2
    }
    unassessed_anchored = [
        ev for ev in evidences
        if ev.get("relation") == "supports" and grade(ev) == 1 and capture_quality(ev) >= 2
        and ev.get("extraction_method") in ("direct-quotation", "manual-paraphrase", "calculation")
    ]
    qualifying = [ev for ev in anchored if ev.get("relation") == "qualifies"]

    if len(assessed_sources) >= 2:
        cap, basis = "established", ">=2 independently assessed supporting sources"
    elif len(assessed_sources) == 1:
        cap, basis = "well-supported", "1 independently assessed supporting source"
    elif unassessed_anchored:
        cap, basis = "provisional", "anchored but unassessed supporting evidence"
    elif any(ev.get("relation") in ("mentions", "contextualizes") for ev in anchored):
        cap, basis = "not-assessed", "only mentions/contextualizes evidence; nothing entails"
    else:
        cap, basis = "provisional", "evidence present but weakly anchored"

    if qualifying and LADDER.get(cap, 0) > LADDER["provisional"]:
        cap, basis = "provisional", basis + "; narrowed by qualifying evidence"
    return {"cap": cap, "basis": basis}


def grade_check(claim: dict[str, Any], cap_info: dict[str, Any]) -> dict[str, Any]:
    recorded, cap = str(claim.get("epistemic_status")), cap_info["cap"]
    if recorded in OFF_LADDER or cap in OFF_LADDER:
        over = recorded in ("established", "well-supported") and cap == "contested"
        return {"recorded": recorded, "cap": cap, "over_grade": over,
                "basis": cap_info["basis"], "delta": None}
    delta = LADDER.get(recorded, 0) - LADDER.get(cap, 0)
    return {"recorded": recorded, "cap": cap, "over_grade": delta > 0,
            "basis": cap_info["basis"], "delta": delta}


# ---------------------------------------------------------------------------
# bi-temporal split (§6)
# ---------------------------------------------------------------------------

def valid_time_resolution(valid_time: Any, present: bool) -> str:
    if not present or not isinstance(valid_time, dict):
        return "unrecorded"
    if valid_time.get("start") and valid_time.get("end"):
        return "closed-interval"
    if valid_time.get("start"):
        return "open-start"
    if valid_time.get("end"):
        return "open-end"
    if valid_time.get("description"):
        return "prose-only"
    return "unrecorded"


def bitemporal(record: dict[str, Any], kind: str) -> dict[str, Any]:
    if kind == "claim":
        vt = record.get("valid_time")
        return {"recorded_at": record.get("created_at"), "recorded_at_field": "created_at",
                "valid_time": vt if isinstance(vt, dict) else None,
                "valid_time_resolution": valid_time_resolution(vt, "valid_time" in record)}
    if kind == "evidence":
        return {"recorded_at": record.get("captured_at"), "recorded_at_field": "captured_at",
                "valid_time": None, "valid_time_resolution": "not-applicable",
                "note": "contract has no valid_time field: engine can express when the quote "
                        "was captured, not when the quoted statement was true",
                "source_published_at": (record.get("source") or {}).get("published_at"),
                "source_accessed_at": (record.get("source") or {}).get("accessed_at"),
                "assessment_time": (record.get("assessment") or {}).get("assessed_at")}
    if kind == "provenance":
        vt = record.get("valid_time")
        return {"recorded_at": record.get("recorded_at"), "recorded_at_field": "recorded_at",
                "valid_time": vt if isinstance(vt, dict) else None,
                "valid_time_resolution": valid_time_resolution(vt, "valid_time" in record),
                "activity_started_at": (record.get("activity") or {}).get("started_at"),
                "activity_ended_at": (record.get("activity") or {}).get("ended_at")}
    return {"recorded_at": record.get("completed_at"), "recorded_at_field": "completed_at",
            "valid_time": None, "valid_time_resolution": "not-applicable"}


# ---------------------------------------------------------------------------
# identity resolution (§4 A2)
# ---------------------------------------------------------------------------
_TOKEN = re.compile(r"[0-9a-f]{8}")


def canonical_identity(raw: str) -> str:
    return re.split(r"[\s(（]", str(raw).strip(), maxsplit=1)[0] if raw else ""


def identity_groups(mentions: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """Group identity strings sharing an 8-hex session token.

    A group with >1 distinct id is a fragmented identity: one producer recorded
    under several names, so naive string equality in the no-self-approval check
    would not fire. Detected mechanically from the records, not asserted.
    """
    seen: dict[str, dict[str, Any]] = {}
    for raw, where in mentions:
        canon = canonical_identity(raw)
        for token in _TOKEN.findall(str(raw).lower()):
            entry = seen.setdefault(token, {"token": token, "ids": set(), "mentions": []})
            entry["ids"].add(canon)
            entry["mentions"].append({"raw": raw, "canonical": canon, "where": where})
    groups = [{"token": e["token"], "ids": sorted(e["ids"]), "fragmented": len(e["ids"]) > 1,
               "mentions": e["mentions"]} for e in seen.values()]
    return sorted(groups, key=lambda g: g["token"])


# ---------------------------------------------------------------------------
# query engine over the projection (§8 draft API, executed on real records)
# ---------------------------------------------------------------------------

class Projection:
    def __init__(self, entities: dict[str, dict[str, Any]], edges: list[dict[str, Any]]):
        self.entities, self.edges = entities, edges

    def out_edges(self, eid, pred=None):
        return [e for e in self.edges if e["subject"] == eid and (pred is None or e["predicate"] == pred)]

    def in_edges(self, eid, pred=None):
        return [e for e in self.edges if e["object"] == eid and (pred is None or e["predicate"] == pred)]

    def node(self, eid):
        return self.entities.get(eid, {"entity_id": eid, "kind": "external",
                                       "resolution": "unresolved-external-id"})

    def evidence_of(self, claim_id):
        return [(self.node(e["subject"]), e) for e in self.in_edges(claim_id, "EVIDENCE_OF")]

    def epistemic_view(self, claim_id):
        """Partitioned evidence view; never returns one side only (§3 invariant)."""
        view = {k: [] for k in ("supports", "refutes", "qualifies", "contextualizes",
                                "mentions", "derived_from", "insufficient")}
        for ev, edge in self.evidence_of(claim_id):
            row = {"entity_id": ev.get("entity_id"), "relation": edge["attrs"].get("relation"),
                   "assessment_status": ev.get("assessment_status"),
                   "locator_value": ev.get("locator_value"),
                   "quote_sha256": ev.get("quote_sha256")}
            view.setdefault(str(edge["attrs"].get("relation")), []).append(row)
            if ev.get("assessment_status") == "insufficient":
                view["insufficient"].append(row)
        return view

    def policy_view(self, req):
        return {"policy_version": POLICY_VERSION, "projection_version": PROJECTION_VERSION,
                "review_policy_version": REVIEW_POLICY_VERSION,
                "records_as_recorded": True, "withheld_fields": [],
                "requested_at": req.get("_now", "build-time"),
                "degraded": False}

    def by_domain(self, req):
        domain = req["domain"]
        match = req.get("domain_match", "exact")
        kinds = req.get("entity_kinds") or ["claim", "knowledge-object"]
        epistemics = req.get("epistemic_status") or []
        reviews = req.get("review_status") or []
        include_gaps = req.get("include_not_assessed", True)
        items = []
        for eid, ent in sorted(self.entities.items()):
            if ent["kind"] not in kinds:
                continue
            domains = ent.get("domains") or []
            hit = domain in domains if match == "exact" else any(
                d == domain or d.startswith(domain + "/") for d in domains)
            if not hit:
                continue
            if ent.get("epistemic_status") == "not-assessed" and not include_gaps:
                continue
            if epistemics and ent.get("epistemic_status") not in epistemics:
                continue
            if reviews and ent.get("review_status") not in reviews:
                continue
            items.append({"entity_id": eid, "kind": ent["kind"], "label": ent.get("label"),
                          "domains": domains, "epistemic_status": ent.get("epistemic_status"),
                          "review_status": ent.get("review_status"),
                          "recorded_at": ent.get("recorded_at"),
                          "valid_time_resolution": ent.get("valid_time_resolution"),
                          "evidence_count": len(self.evidence_of(eid)) if ent["kind"] == "claim" else None,
                          "flags": ent.get("flags", [])})
        return {"query_class": "by-domain", "items": items, "total": len(items),
                "policy_view": self.policy_view(req), "next_cursor": None}

    def by_anchor(self, req):
        eid = req["entity_id"]
        if eid not in self.entities:
            return {"status": 404, "error": {"code": "ANCHOR_NOT_FOUND", "entity_id": eid}}
        root = self.node(eid)
        expand = req.get("expand") or {}
        nodes = [{"entity_id": eid, "kind": root["kind"], "label": root.get("label"),
                  "epistemic_status": root.get("epistemic_status"),
                  "review_status": root.get("review_status"), "role": "anchor"}]
        edges, claims = [], []
        if root["kind"] == "claim":
            claims = [eid]
            for edge in self.in_edges(eid, "EVIDENCE_OF"):
                edges.append(edge)
                ev = self.node(edge["subject"])
                nodes.append({"entity_id": edge["subject"], "kind": "evidence",
                              "label": ev.get("locator_value"),
                              "relation": edge["attrs"].get("relation"),
                              "assessment_status": ev.get("assessment_status"),
                              "role": "evidence"})
        else:
            for pred in ("KO_INCLUDES_CLAIM", "KO_NARROWS_TO", "KO_REL"):
                for edge in self.out_edges(eid, pred):
                    edges.append(edge)
                    claims.append(edge["object"])
                    tgt = self.node(edge["object"])
                    nodes.append({"entity_id": edge["object"], "kind": tgt["kind"],
                                  "label": tgt.get("label"),
                                  "epistemic_status": tgt.get("epistemic_status"),
                                  "intent": edge["attrs"].get("intent"),
                                  "role": "related"})
        if expand.get("provenance"):
            for edge in self.in_edges(eid, "USED"):
                edges.append(edge)
                act = self.node(edge["subject"])
                nodes.append({"entity_id": edge["subject"], "kind": act["kind"],
                              "label": act.get("label"), "role": "provenance"})
                prov_id = edge["attrs"].get("provenance_record")
                if prov_id:
                    nodes.append({"entity_id": prov_id, "kind": "provenance-record",
                                  "role": "provenance-record"})
        epistemic = {cid: self.epistemic_view(cid) for cid in claims if cid in self.entities}
        return {"query_class": "by-anchor", "anchor": eid, "nodes": nodes, "edges": edges,
                "epistemic_view": epistemic, "policy_view": self.policy_view(req)}

    def by_evidence_status(self, req):
        statuses = set(req.get("assessment_status") or [])
        relations = set(req.get("relation") or [])
        require_pair = bool(req.get("require_contested_pair", False))
        hits = []
        for edge in self.edges:
            if edge["predicate"] != "EVIDENCE_OF":
                continue
            ev = self.node(edge["subject"])
            if statuses and str(ev.get("assessment_status")) not in statuses:
                continue
            if relations and str(edge["attrs"].get("relation")) not in relations:
                continue
            hits.append((edge["object"], edge["subject"]))
        items = []
        for cid in sorted({c for c, _ in hits}):
            claim = self.node(cid)
            view = self.epistemic_view(cid)
            entry = {"claim_id": cid, "epistemic_status": claim.get("epistemic_status"),
                     "review_status": claim.get("review_status"),
                     "matched_evidence": sorted(e for c, e in hits if c == cid),
                     "evidence_partition": view, "flags": claim.get("flags", [])}
            if require_pair:
                entry["two_sided"] = bool(view["refutes"] or view["qualifies"]) and bool(view["supports"])
            items.append(entry)
        resp = {"query_class": "by-evidence-status", "items": items, "total": len(items),
                "policy_view": self.policy_view(req)}
        if require_pair:
            resp["contested_pairs"] = self.contested_pairs()
        return resp

    def contested_pairs(self):
        """Both sides retained: a contested claim and the narrowed claim that
        survives, joined through the aggregate that holds them together (§3 T-3.3).

        Two-sidedness is a property of the *question*, not of one claim's evidence
        list: in this pilot the broad claim has only refutes/qualifies edges, while
        the defensible side is a separate narrowed claim.
        """
        pairs = []
        for eid, ent in sorted(self.entities.items()):
            if ent["kind"] != "knowledge-object":
                continue
            included = [e for e in self.out_edges(eid, "KO_INCLUDES_CLAIM")]
            narrowed = [e for e in self.out_edges(eid, "KO_NARROWS_TO")]
            if not narrowed:
                continue
            for wide in included:
                wide_id = wide["object"]
                wide_view = self.epistemic_view(wide_id)
                sides = []
                for edge in narrowed:
                    narrow_id = edge["object"]
                    narrow_view = self.epistemic_view(narrow_id)
                    sides.append({"narrowed_claim": narrow_id,
                                  "epistemic_status": self.node(narrow_id).get("epistemic_status"),
                                  "supporting_evidence": narrow_view["supports"]})
                pairs.append({
                    "question_ref": eid,
                    "contested_claim": wide_id,
                    "contested_epistemic_status": self.node(wide_id).get("epistemic_status"),
                    "against": wide_view["refutes"] + wide_view["qualifies"]
                               + wide_view["contextualizes"],
                    "surviving_narrowed_sides": sides,
                    "both_sides_retained": bool(wide_view["refutes"] + wide_view["qualifies"])
                                           and all(s["supporting_evidence"] for s in sides),
                    "note": "no query may return the against-side alone: the response carries both "
                            "the challenged claim and the narrowed claim that survives (§3 T-3.3)",
                })
        return pairs

    def by_provenance_chain(self, req):
        eid = req["entity_id"]
        if eid not in self.entities:
            return {"status": 404, "error": {"code": "ANCHOR_NOT_FOUND", "entity_id": eid}}
        max_depth = int(req.get("max_depth", 3))
        direction = req.get("direction", "upstream")
        include_agents = bool(req.get("include_agents", True))
        chain, gaps = [], []
        frontier, seen = [(eid, 0)], {eid}
        while frontier:
            current, depth = frontier.pop(0)
            if depth >= max_depth:
                continue
            edges = []
            if direction in ("upstream", "both"):
                edges += self.in_edges(current, "USED") + self.in_edges(current, "GENERATED")
                edges += self.in_edges(current, "DERIVED_FROM")
                if include_agents:
                    edges += self.in_edges(current, "WAS_ASSOCIATED_WITH")
                    edges += self.in_edges(current, "ATTRIBUTED_TO")
            if direction in ("downstream", "both"):
                edges += self.out_edges(current, "USED") + self.out_edges(current, "GENERATED")
                edges += self.out_edges(current, "DERIVED_FROM")
            for edge in edges:
                other = edge["subject"] if edge["object"] == current else edge["object"]
                chain.append({**edge, "depth": depth + 1, "from": current, "to": other})
                if other not in seen:
                    seen.add(other)
                    frontier.append((other, depth + 1))
        for ent in self.entities.values():
            for sw in ent.get("software", []) if isinstance(ent.get("software"), list) else []:
                if not sw.get("version"):
                    gaps.append({"kind": "software-version-unknown",
                                 "software": sw.get("name"), "owner": ent.get("entity_id")})
        for row in chain:
            node = self.node(row["to"])
            if node["kind"] == "external":
                gaps.append({"kind": "unresolved-external-entity", "id": row["to"],
                             "via": row["predicate"]})
        return {"query_class": "by-provenance-chain", "entity_id": eid,
                "direction": direction, "steps": chain, "gaps": gaps,
                "policy_view": self.policy_view(req)}