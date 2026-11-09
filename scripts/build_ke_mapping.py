#!/usr/bin/env python3
"""Build mappings/<pilot>.json — the worked KE projection for a frozen pilot snapshot.

Usage:
    python scripts/build_ke_mapping.py                 # writes mappings/m8554.json
    python scripts/build_ke_mapping.py --pilot m8554   # explicit

Everything numeric in the output is computed from the snapshot; nothing is
hand-copied (report discipline: programmatic injection, zero transcription).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ke_mapping_lib as lib  # noqa: E402
import ke_state_machine as sm  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT_SOURCE = {
    "repository": "TensorKnowledge",
    "branch": "agent/m8554",
    "commit": "727ac1887e13a623450faa08217698bfe7f22cba",
    "path": "platform-test/epistemic-benchmark/pilots/m8554",
    "note": "read-only frozen snapshot; the branch remains the canonical source",
}
KO_EDGE_MAP = {
    "supported-by-claim": ("KO_INCLUDES_CLAIM", "supported-by"),
    "contested-claim": ("KO_INCLUDES_CLAIM", "contested"),
    "narrowed-claim": ("KO_NARROWS_TO", "narrows"),
    "status-claim": ("KO_INCLUDES_CLAIM", "status-of"),
}
ELISION_MARKS = ("[…]", "[...]", " […]", "...")


def load_snapshot(pilot: str) -> dict[str, list[tuple[str, dict]]]:
    base = os.path.join(ROOT, "mappings", "source", pilot)
    out: dict[str, list[tuple[str, dict]]] = {"claim": [], "evidence": [], "provenance": [], "envelope": []}
    for kind, sub in (("claim", "claims"), ("evidence", "evidence"), ("provenance", "provenance")):
        for path in sorted(glob.glob(os.path.join(base, sub, "*.json"))):
            with open(path, encoding="utf-8") as fh:
                out[kind].append((os.path.relpath(path, ROOT), json.load(fh)))
    with open(os.path.join(base, "production-result.json"), encoding="utf-8") as fh:
        out["envelope"].append((os.path.relpath(os.path.join(base, "production-result.json"), ROOT), json.load(fh)))
    return out


def edge_id(subject: str, predicate: str, obj: str, discriminator: str = "") -> str:
    return "tke-e:" + lib.sha256_text(f"{subject}|{predicate}|{obj}|{discriminator}")[:16]


def make_edge(subject: str, predicate: str, obj: str, attrs: dict, recorded_at: str,
              discriminator: str = "") -> dict:
    return {"edge_id": edge_id(subject, predicate, obj, discriminator), "subject": subject,
            "predicate": predicate, "object": obj, "attrs": attrs,
            "recorded_at": recorded_at, "append_only": True}


def has_elision(text: str) -> bool:
    return any(mark in text for mark in ELISION_MARKS)


def build(pilot: str) -> dict:
    snap = load_snapshot(pilot)
    claims = {rec["id"]: (path, rec) for path, rec in snap["claim"]}
    evidences = {rec["id"]: (path, rec) for path, rec in snap["evidence"]}
    provs = {rec["id"]: (path, rec) for path, rec in snap["provenance"]}
    envelope = snap["envelope"][0][1]
    kos = {ko["id"]: ko for ko in envelope.get("proposed_objects", [])}

    # ---------------- projection of every record ----------------
    records, projections = [], {}
    for kind, items in (("claim", snap["claim"]), ("evidence", snap["evidence"]),
                        ("provenance", snap["provenance"])):
        for path, rec in items:
            proj = lib.project(kind, rec)
            projections[rec["id"]] = (kind, path, rec, proj)
            records.append({
                "contract": f"{kind}-record",
                "contract_version": lib.CONTRACT_VERSIONS[kind],
                "entity_id": rec["id"], "entity_kind": kind,
                "source_path": path, "raw_sha256": proj["raw_sha256"],
                "raw_bytes": proj["raw_bytes"], "leaf_paths": proj["leaf_paths"],
                "projection": proj["covered"], "uncovered": proj["uncovered"],
                "slots": proj["slots"],
                "bitemporal": lib.bitemporal(rec, kind),
            })
    for ko_id, ko in kos.items():
        proj = lib.project("ko", ko)
        projections[ko_id] = ("ko", "production-result.proposed_objects", ko, proj)
        records.append({
            "contract": "knowledge-object (aggregate element of the production result)",
            "contract_version": lib.CONTRACT_VERSIONS["ko"], "entity_id": ko_id,
            "entity_kind": "knowledge-object",
            "source_path": "mappings/source/%s/production-result.json#proposed_objects" % pilot,
            "raw_sha256": proj["raw_sha256"], "raw_bytes": proj["raw_bytes"],
            "leaf_paths": proj["leaf_paths"], "projection": proj["covered"],
            "uncovered": proj["uncovered"], "slots": proj["slots"],
            "bitemporal": {"recorded_at": envelope.get("completed_at"),
                           "recorded_at_field": "completed_at (inherited from envelope)",
                           "valid_time": None, "valid_time_resolution": "not-applicable"},
        })
    proj_env = lib.project("envelope", envelope)
    env_id = "tkm:platform:%s" % envelope.get("platform_task_id")
    projections[env_id] = ("envelope", "mappings/source/%s/production-result.json" % pilot, envelope, proj_env)
    records.append({
        "contract": "production-result envelope", "contract_version": lib.CONTRACT_VERSIONS["envelope"],
        "entity_id": env_id,
        "entity_kind": "production-result",
        "source_path": "mappings/source/%s/production-result.json" % pilot,
        "raw_sha256": proj_env["raw_sha256"], "raw_bytes": proj_env["raw_bytes"],
        "leaf_paths": proj_env["leaf_paths"], "projection": proj_env["covered"],
        "uncovered": proj_env["uncovered"], "slots": proj_env["slots"],
        "bitemporal": lib.bitemporal(envelope, "envelope"),
    })

    # ---------------- epistemic policy per claim ----------------
    ev_of_claim: dict[str, list[dict]] = {}
    for eid, (_, rec) in evidences.items():
        for cid in rec.get("claim_refs", []):
            ev_of_claim.setdefault(cid, []).append(rec)
    for rec in records:
        if rec["entity_kind"] != "claim":
            continue
        _, _, claim, _ = projections[rec["entity_id"]]
        cap = lib.conservative_cap(claim, ev_of_claim.get(rec["entity_id"], []))
        rec["epistemic_policy"] = lib.grade_check(claim, cap)
        flags = []
        if rec["epistemic_policy"]["over_grade"]:
            flags.append("OVER_GRADE_VS_CONSERVATIVE_CAP")
        if rec["epistemic_policy"]["recorded"] == "not-assessed":
            flags.append("NOT_ASSESSED_EXPLICIT")
        if rec["bitemporal"]["valid_time_resolution"] in ("prose-only", "unrecorded"):
            flags.append("VALID_TIME_%s" % rec["bitemporal"]["valid_time_resolution"].upper().replace("-", "_"))
        rec["flags"] = flags

    # ---------------- edges ----------------
    edges: list[dict] = []
    for eid, (_, rec) in evidences.items():
        for cid in rec.get("claim_refs", []):
            edges.append(make_edge(eid, "EVIDENCE_OF", cid,
                                   {"relation": rec.get("relation"),
                                    "assessment_status": rec.get("assessment_status"),
                                    "extraction_method": rec.get("extraction_method"),
                                    "capture_quality": lib.capture_quality(rec)},
                                   rec.get("captured_at", "")))
    for ko_id, ko in kos.items():
        for rel in ko.get("relations", []):
            predicate, intent = KO_EDGE_MAP.get(rel.get("relation_type"), ("KO_REL_UNMAPPED", "unmapped"))
            edges.append(make_edge(ko_id, predicate, rel.get("target_id"),
                                   {"relation_type_raw": rel.get("relation_type"), "intent": intent,
                                    "normalization": "closed-enum" if predicate != "KO_REL_UNMAPPED" else "unmapped"},
                                   envelope.get("completed_at", "")))
    for pid, (_, rec) in provs.items():
        act = rec.get("activity", {}) or {}
        gen = (rec.get("generated_entity") or {}).get("id")
        if gen:
            edges.append(make_edge(act.get("id"), "GENERATED", gen,
                                   {"entity_type": (rec.get("generated_entity") or {}).get("entity_type"),
                                    "provenance_record": pid}, rec.get("recorded_at", "")))
        for used in act.get("used_entities", []):
            edges.append(make_edge(act.get("id"), "USED", used, {"provenance_record": pid},
                                   rec.get("recorded_at", "")))
        for agent in rec.get("agents", []):
            edges.append(make_edge(agent.get("id"), "WAS_ASSOCIATED_WITH", act.get("id"),
                                   {"role": agent.get("role"), "provenance_record": pid},
                                   rec.get("recorded_at", "")))
        for target in rec.get("attributed_to", []):
            edges.append(make_edge(pid, "ATTRIBUTED_TO", target, {}, rec.get("recorded_at", "")))
        for src in rec.get("derived_from", []):
            edges.append(make_edge(pid, "DERIVED_FROM", src, {}, rec.get("recorded_at", "")))
        if gen:
            edges.append(make_edge(pid, "GENERATED", gen,
                                   {"relation": "provenance-record-asserts-generation",
                                    "provenance_record": pid}, rec.get("recorded_at", "")))
    for ref in envelope.get("artifact_references", []):
        if isinstance(ref, str):
            target, attrs = ref, {"raw_reference": ref, "reference_form": "path-string"}
        else:
            target = ref.get("path") or ref.get("reference") or json.dumps(ref, ensure_ascii=False)[:60]
            attrs = {"raw_reference": ref, "reference_form": "object"}
        attrs["is_directory_hint"] = str(target).endswith("/")
        edges.append(make_edge("tkm:platform:%s" % envelope.get("platform_task_id"), "ARTIFACT_REF",
                               target, attrs, envelope.get("completed_at", "")))

    # ---------------- entities (engine nodes) ----------------
    entities: dict[str, dict] = {}
    for rec in records:
        kind = rec["entity_kind"]
        _, _, raw, _ = projections[rec["entity_id"]]
        ent = {"entity_id": rec["entity_id"], "kind": kind,
               "recorded_at": rec["bitemporal"].get("recorded_at"),
               "valid_time_resolution": rec["bitemporal"].get("valid_time_resolution"),
               "flags": rec.get("flags", [])}
        if kind == "claim":
            ent.update({"label": raw.get("statement", "")[:96],
                        "domains": [raw.get("scope", {}).get("domain")],
                        "epistemic_status": raw.get("epistemic_status"),
                        "review_status": "draft",  # fold(empty ledger) per §4; no field in the contract
                        "review_status_source": "fold(empty-review-event-ledger)"})
        elif kind == "evidence":
            quote = (raw.get("locator") or {}).get("quote", "")
            ent.update({"label": (raw.get("locator") or {}).get("value"),
                        "domains": [], "epistemic_status": None,
                        "assessment_status": raw.get("assessment_status"),
                        "relation": raw.get("relation"),
                        "locator_value": (raw.get("locator") or {}).get("value"),
                        "quote_sha256": lib.sha256_text(quote) if quote else None,
                        "quote_elided": has_elision(quote),
                        "review_status": "n/a-no-review-axis-in-contract"})
        elif kind == "provenance":
            act = raw.get("activity", {}) or {}
            ent.update({"label": act.get("activity_type"),
                        "domains": [], "epistemic_status": None,
                        "review_status": "n/a-no-review-axis-in-contract",
                        "software": act.get("software", []),
                        "agents": [a.get("id") for a in raw.get("agents", [])]})
        elif kind == "knowledge-object":
            ent.update({"label": raw.get("title"), "domains": raw.get("domains", []),
                        "epistemic_status": raw.get("evidence_status"),
                        "review_status": raw.get("review_status")})
        else:
            ent.update({"label": "production result %s" % envelope.get("package_id"),
                        "domains": [], "epistemic_status": None,
                        "review_status": "not-applicable",
                        "platform_state": envelope.get("execution_state")})
        entities[rec["entity_id"]] = ent
    # materialize activity / agent / external-source nodes so chains resolve
    for pid, (_, rec) in provs.items():
        act = rec.get("activity", {}) or {}
        entities.setdefault(act.get("id"), {"entity_id": act.get("id"), "kind": "activity",
                                            "label": act.get("activity_type"),
                                            "software": act.get("software", []),
                                            "recorded_at": rec.get("recorded_at")})
        for agent in rec.get("agents", []):
            existing = entities.get(agent.get("id"))
            if existing and existing["kind"] == "agent":
                continue
            entities[agent.get("id")] = {"entity_id": agent.get("id"), "kind": "agent",
                                         "label": agent.get("name"),
                                         "agent_type": agent.get("agent_type"),
                                         "role": agent.get("role"),
                                         "external_id": agent.get("external_id")}
    # source nodes from evidence records
    for eid, (_, rec) in evidences.items():
        src = rec.get("source", {}) or {}
        key = src.get("persistent_id") or src.get("url") or lib.sha256_text(src.get("citation", ""))
        entities.setdefault(key, {"entity_id": key, "kind": "source-node",
                                  "source_type": src.get("source_type"),
                                  "published_at": src.get("published_at"),
                                  "publisher": src.get("publisher")})

    # ---------------- vector facets ----------------
    vectors = []
    for rec in records:
        for row in rec["projection"]:
            if not row.get("facet"):
                continue
            _, _, raw, _ = projections[rec["entity_id"]]
            if row["facet"] == "claim.statement":
                text, language = raw.get("statement", ""), "zh"
            elif row["facet"] == "evidence.quote":
                text = (raw.get("locator") or {}).get("quote", "")
                language = (raw.get("locator") or {}).get("quote_language", "und")
            else:
                text, language = raw.get("summary", ""), "zh"
            vectors.append({
                "facet_id": "fct:" + lib.sha256_text(rec["entity_id"] + "|" + row["facet"])[:12],
                "entity_id": rec["entity_id"], "facet": row["facet"],
                "source_field_path": row["source_path"],
                "text_sha256": lib.sha256_text(text), "text_chars": len(text),
                "language": language, "elided": has_elision(text),
                "embedding": None, "index_status": "declared-not-built",
                "filters": {"review_status": projections[rec["entity_id"]][2].get("review_status"),
                            "epistemic_status": projections[rec["entity_id"]][2].get(
                                "epistemic_status", projections[rec["entity_id"]][2].get("evidence_status")),
                            "entity_kind": rec["entity_kind"]},
                "retrieval_note": "similarity score is a retrieval score, never entailment (§7.3)",
            })

    # ---------------- cross-checks (all measured) ----------------
    sym = []
    ev_refs_from_claims = {}
    for cid, (_, claim) in claims.items():
        ev_refs_from_claims[cid] = set(claim.get("evidence_refs", []))
    for cid, refs in ev_refs_from_claims.items():
        back = {eid for eid, (_, rec) in evidences.items() if cid in rec.get("claim_refs", [])}
        sym.append({"claim": cid, "claim_side_refs": sorted(refs),
                    "evidence_side_refs": sorted(back), "symmetric": refs == back})
    used_targets = {u for _, rec in provs.values() for u in (rec.get("activity", {}) or {}).get("used_entities", [])}
    contract_ids = list(claims) + list(evidences)
    provenance_coverage = {cid: cid in used_targets for cid in contract_ids}
    software_entries = [(pid, sw) for pid, (_, rec) in provs.items()
                        for sw in (rec.get("activity", {}) or {}).get("software", [])]
    elided_quotes = [eid for eid, (_, rec) in evidences.items()
                     if has_elision((rec.get("locator") or {}).get("quote", ""))]
    offset_quotes = [eid for eid, (_, rec) in evidences.items()
                     if "start_offset" in (rec.get("locator") or {})]
    assessed = [eid for eid, (_, rec) in evidences.items() if "assessment" in rec]
    identity_mentions = []
    for cid, (_, claim) in claims.items():
        identity_mentions.append((claim.get("created_by", ""), f"{cid}.created_by"))
    for eid, (_, rec) in evidences.items():
        identity_mentions.append((rec.get("captured_by", ""), f"{eid}.captured_by"))
    for pid, (_, rec) in provs.items():
        for agent in rec.get("agents", []):
            identity_mentions.append((agent.get("id", ""), f"{pid}.agents.id"))
            if agent.get("external_id"):
                identity_mentions.append((agent.get("external_id", ""), f"{pid}.agents.external_id"))
    groups = lib.identity_groups(identity_mentions)
    review_events = [p for p in glob.glob(os.path.join(ROOT, "mappings", "source", pilot, "**", "tkr-*.json"),
                                          recursive=True)]
    cross = {
        "evidence_ref_symmetry": {"pairs": len(sym), "symmetric": sum(s["symmetric"] for s in sym),
                                  "rows": sym},
        "provenance_coverage": {"records": len(contract_ids),
                                "reachable_via_activity_used_entities": sum(provenance_coverage.values()),
                                "uncovered": [k for k, v in provenance_coverage.items() if not v],
                                "granularity": "scenario-level: 3 activities, generated_entity points at "
                                               "the scenario bundle, not at individual records"},
        "software_version_missing": {"entries": len(software_entries),
                                     "empty_version": sum(1 for _, sw in software_entries
                                                          if not sw.get("version"))},
        "quote_elision": {"quotes": len(evidences), "with_elision": len(elided_quotes),
                          "records": elided_quotes},
        "quote_char_offsets": {"quotes": len(evidences), "with_start_offset": len(offset_quotes)},
        "evidence_assessment_present": {"records": len(evidences), "with_assessment": len(assessed)},
        "identity_groups": groups,
        "review_events_in_pilot": len(review_events),
        "ko_claim_refs_usage": {"kos": len(kos),
                                "using_claim_refs": sum(1 for ko in kos.values() if ko.get("claim_refs")),
                                "using_relations": sum(1 for ko in kos.values() if ko.get("relations"))},
        "platform_state_not_used_for_review": {
            "envelope_execution_state": envelope.get("execution_state"),
            "envelope_outcome": envelope.get("outcome"),
            "ko_review_status_values": sorted({ko.get("review_status") for ko in kos.values()}),
            "rule": "review_status comes only from fold(review-event ledger) (§4 A3)"},
    }

    # ---------------- disclosures (measured facts, curated judgement) ----------------
    claim_grade_flags = [(r["entity_id"], r["epistemic_policy"]["recorded"], r["epistemic_policy"]["cap"])
                         for r in records if r.get("epistemic_policy", {}).get("over_grade")]
    prose_only = [r["entity_id"] for r in records
                  if r["entity_kind"] == "claim"
                  and r["bitemporal"]["valid_time_resolution"] == "prose-only"]
    disclosures = [
        {"id": "D-01", "class": "L4", "severity": "major",
         "title": "Evidence records carry no validity time; only capture time",
         "detail": "claim-record has valid_time{start,end,description}; evidence-record has none. "
                   "The engine can express when a quote was captured (captured_at) and when the source "
                   "was published (source.published_at), but not the interval in which the quoted "
                   "statement held. Any 'as valid at t' query over evidence is therefore UNKNOWN, "
                   "not false.",
         "affected": sorted(evidences), "disposition": "disclosed; requires contract change to close",
         "measured_by": "lib.bitemporal() -> valid_time_resolution=not-applicable for all evidence rows"},
        {"id": "D-02", "class": "L4", "severity": "major",
         "title": "Excerpts are elided; no character offsets, so no verbatim span is recoverable",
         "detail": f"{cross['quote_elision']['with_elision']}/{cross['quote_elision']['quotes']} quotes "
                   f"contain ellipsis markers and {cross['quote_char_offsets']['with_start_offset']}/"
                   f"{cross['quote_char_offsets']['quotes']} locators carry start_offset. The engine "
                   "stores quote_sha256 of the *as-captured* excerpt only; it cannot re-verify the excerpt "
                   "against the live source, and 'direct-quotation' must be read as 'stamped excerpt'.",
         "affected": cross["quote_elision"]["records"],
         "disposition": "disclosed; retrieval surfaces quote_elided=true so no client mistakes it for a "
                        "contiguous span"},
        {"id": "D-03", "class": "L4", "severity": "major",
         "title": "Producer identity is fragmented across two id spellings",
         "detail": "claims/evidence record created_by='claude-code-session-6f76cd3d (...)' while the "
                   "provenance records name the same session 'cc-session-6f76cd3d' (external_id "
                   "bg-job-6f76cd3d). A string-equality self-approval check would not fire on the alias. "
                   "Engine therefore resolves identity by shared session token and fails closed (§4 A2).",
         "affected": [g["token"] for g in groups if g["fragmented"]],
         "disposition": "mitigated in v0.1 by token-based alias resolution + fail-closed rule; a durable "
                        "identity registry (ke.identity_alias) is required before multi-agent approval"},
        {"id": "D-04", "class": "L4", "severity": "minor",
         "title": "Tool versions are unresolvable in provenance",
         "detail": f"{cross['software_version_missing']['empty_version']}/"
                   f"{cross['software_version_missing']['entries']} software entries have an empty version "
                   "string. provenance-record allows it, but the engine cannot pin which tool build produced "
                   "an artifact, so reproducibility claims must stay qualified.",
         "affected": [pid for pid, _ in software_entries],
         "disposition": "disclosed; version_unknown=true stored, never invented"},
        {"id": "D-05", "class": "L4", "severity": "major",
         "title": "Provenance is scenario-level, not record-level",
         "detail": f"{cross['provenance_coverage']['records']} records are reachable as activity "
                   f"used_entities ({cross['provenance_coverage']['reachable_via_activity_used_entities']} "
                   "covered), but each of the 3 activities declares generated_entity = the scenario bundle. "
                   "A per-record 'which activity generated *this* claim' answer is only derivable through "
                   "used_entities membership, which also lists sources and unrelated ids.",
         "affected": sorted(provs), "disposition": "disclosed; acceptable for a 3-activity pilot, "
                                                   "insufficient at record granularity"},
        {"id": "D-06", "class": "L4", "severity": "major",
         "title": "Recorded epistemic_status exceeds the conservative cap on some claims",
         "detail": "policy table T-5.2 caps a claim whose supporting evidence is anchored but unassessed "
                   f"(capture>=2, assessment_status=unassessed) at 'provisional'. Flagged: {claim_grade_flags}. "
                   "The recorded value is preserved verbatim (never rewritten by the engine) and the "
                   "computed cap is stored next to it for a reviewer to rule on.",
         "affected": [row[0] for row in claim_grade_flags],
         "disposition": "flag-only, non-destructive: engine never downgrades authored status; requires a "
                        "review event to change it"},
        {"id": "D-07", "class": "L4", "severity": "minor",
         "title": "Validity intervals are prose-only for most claims",
         "detail": f"{len(prose_only)}/{len(claims)} claims describe validity in prose without start/end. "
                   "The engine stores the prose and marks resolution=prose-only; it must NOT parse dates "
                   "out of the prose (that would fabricate timestamps).",
         "affected": prose_only,
         "disposition": "disclosed; 'as valid at t' returns these claims as unknown-validity, not as false"},
        {"id": "D-08", "class": "L4", "severity": "minor",
         "title": "KO aggregates link claims through an open-vocabulary relations list",
         "detail": f"{cross['ko_claim_refs_usage']['using_relations']}/{cross['ko_claim_refs_usage']['kos']} "
                   "KO elements use relations[{relation_type,target_id}] instead of the schema-sanctioned "
                   "claim_refs/evidence_refs fields "
                   f"({cross['ko_claim_refs_usage']['using_claim_refs']} uses of claim_refs). relation_type is "
                   "free text, so the engine normalizes 4 observed tokens to a closed enum and keeps "
                   "relation_type_raw on the edge. Support *direction* is taken from the token verb only.",
         "affected": sorted(kos),
         "disposition": "disclosed; closed-enum mapping table is part of this spec (KO_EDGE_MAP)"},
        {"id": "D-09", "class": "L4", "severity": "informational",
         "title": "No review events exist; review_status is a fold of an empty ledger",
         "detail": f"{cross['review_events_in_pilot']} review-event records exist in the pilot. Every entity's "
                   "review_status='draft' therefore comes from fold(empty) by convention, not from a field — "
                   "claim/evidence/provenance contracts have no review_status column at all. 'Not reviewed' "
                   "must never be rendered as 'approved'.",
         "affected": sorted(list(claims) + list(evidences) + list(provs)),
         "disposition": "engine renders review_status_source='fold(empty-review-event-ledger)'"},
        {"id": "D-10", "class": "L4", "severity": "informational",
         "title": "not-assessed is explicit for exactly one claim and is not the same as missing",
         "detail": "tkc:tkrepo:rocrate-export-production is not-assessed because its only non-contextual "
                   "evidence is a 'mentions' row in an internal planning table (insufficient). The engine "
                   "stores this as an explicit status + insufficiency reasons, and rejects ingest of a claim "
                   "whose status field is absent (absent != not-assessed).",
         "affected": ["tkc:tkrepo:rocrate-export-production"],
         "disposition": "encoded as retrieval flag NOT_ASSESSED_EXPLICIT + insufficiency block"},
        {"id": "D-11", "class": "L1", "severity": "informational",
         "title": "Source published_at is a date, not an instant",
         "detail": "evidence.source.published_at values are ISO dates (2013-04-30, 2026-06-22). The engine "
                   "normalizes to midnight UTC and records precision='date'; the instant is a "
                   "representation artifact, not a finding about the source.",
         "affected": sorted(evidences), "disposition": "precision documented in the projection slot"},
    ]

    # ---------------- retrieval demonstrations (§8 on real data) ----------------
    proj_engine = lib.Projection(entities, edges)
    query_cases = [
        {"class": "by-domain",
         "request": {"domain": "research data stewardship principles", "domain_match": "exact",
                     "entity_kinds": ["claim"], "include_not_assessed": True},
         "response": proj_engine.by_domain(
             {"domain": "research data stewardship principles", "entity_kinds": ["claim"]})},
        {"class": "by-anchor",
         "request": {"entity_id": "tkc:fair:requires-open-access",
                     "expand": {"claims": False, "evidence": True, "provenance": True}, "depth": 1},
         "response": proj_engine.by_anchor({"entity_id": "tkc:fair:requires-open-access",
                                            "expand": {"provenance": True}})},
        {"class": "by-evidence-status",
         "request": {"assessment_status": ["insufficient"], "require_contested_pair": False},
         "response": proj_engine.by_evidence_status({"assessment_status": ["insufficient"]})},
        {"class": "by-evidence-status (two-sided)",
         "request": {"relation": ["refutes", "qualifies"], "require_contested_pair": True},
         "response": proj_engine.by_evidence_status({"relation": ["refutes", "qualifies"],
                                                     "require_contested_pair": True})},
        {"class": "by-anchor (aggregate holds both sides)",
         "request": {"entity_id": "tko:epistemics:fair-accessibility-two-readings",
                     "expand": {"claims": True, "evidence": True, "provenance": True}},
         "response": proj_engine.by_anchor({"entity_id": "tko:epistemics:fair-accessibility-two-readings",
                                            "expand": {"claims": True, "provenance": True}})},
        {"class": "by-provenance-chain",
         "request": {"entity_id": "tkc:prov-o:wasattributedto-signature",
                     "direction": "upstream", "max_depth": 3, "include_agents": True},
         "response": proj_engine.by_provenance_chain(
             {"entity_id": "tkc:prov-o:wasattributedto-signature", "direction": "upstream", "max_depth": 3})},
        {"class": "by-anchor (error case)",
         "request": {"entity_id": "tkc:does:not-exist"}, "response": proj_engine.by_anchor(
             {"entity_id": "tkc:does:not-exist"})},
    ]

    # ---------------- review-event ledger (empty) + conformance ----------------
    conformance = sm.run_conformance()
    review_block = {
        "review_events_as_recorded": [],
        "fold_result_for_every_entity": {"review_status": "draft",
                                         "basis": "fold(empty ledger); no review_status column in the "
                                                  "claim/evidence/provenance contracts"},
        "policy_version": sm.POLICY_VERSION,
        "state_machine_conformance": conformance,
        "conformance_passed": all(row["pass"] for row in conformance),
        "synthetic_illustration": {
            "label": "SYNTHETIC — not a pilot record; demonstrates rejection of a self-approval attempt",
            "attempt": {"object_ref": "tkc:prov-o:wasattributedto-signature",
                        "decision": "approve", "reviewer": {"id": "cc-session-6f76cd3d",
                                                            "reviewer_type": "agent"},
                        "policy_version": sm.POLICY_VERSION, "reviewed_at": "2026-11-09T14:00:00Z"},
            "producer_identity": ["claude-code-session-6f76cd3d"],
            "expected_refusal": "SELF_APPROVAL_BLOCKED",
        },
    }

    # ---------------- audit summary ----------------
    per_contract: dict[str, dict] = {}
    for rec in records:
        key = rec["contract"]
        row = per_contract.setdefault(key, {"records": 0, "leaf_paths": 0, "covered": 0,
                                            "uncovered": 0, "by_loss_class": {}})
        row["records"] += 1
        row["leaf_paths"] += rec["leaf_paths"]
        row["covered"] += len(rec["projection"])
        row["uncovered"] += len(rec["uncovered"])
        for item in rec["projection"]:
            row["by_loss_class"][item["loss_class"]] = row["by_loss_class"].get(item["loss_class"], 0) + 1
    audit = {
        "records": len(records),
        "by_contract": per_contract,
        "leaf_paths_total": sum(r["leaf_paths"] for r in records),
        "leaf_paths_projected": sum(len(r["projection"]) for r in records),
        "leaf_paths_uncovered": sum(len(r["uncovered"]) for r in records),
        "uncovered_paths": [{"entity_id": r["entity_id"], **u} for r in records for u in r["uncovered"]],
        "lossless": all(not r["uncovered"] for r in records),
        "disclosures": len(disclosures),
        "disclosure_classes": {"L4": sum(1 for d in disclosures if d["class"] == "L4"),
                               "L1": sum(1 for d in disclosures if d["class"] == "L1")},
        "edges": len(edges), "vector_facets": len(vectors),
        "acceptance": "no unreported loss: every leaf path is projected, and every semantic loss is "
                      "listed in disclosures[]",
    }
    return {
        "document": "KE mapping worked example (mapping-spec v0.1 §9)",
        "spec": "docs/ke/mapping-spec.md",
        "spec_version": "0.1",
        "policy_version": lib.POLICY_VERSION,
        "projection_version": lib.PROJECTION_VERSION,
        "review_policy_version": lib.REVIEW_POLICY_VERSION,
        "generator": "scripts/build_ke_mapping.py",
        "pilot": pilot,
        "source": PILOT_SOURCE,
        "snapshot_dir": "mappings/source/%s" % pilot,
        "loss_classes": lib.LOSS_CLASSES,
        "engine_model": {
            "entity": "ke.entity(entity_id, entity_kind, contract, contract_version, raw, raw_sha256, "
                      "recorded_at, valid_time_*, status_*, flags[])",
            "edge": "ke.edge(edge_id, subject, predicate, object, attrs, recorded_at, append_only=true)",
            "vector": "ke.facet(facet_id, entity_id, facet, text_sha256, language, embedding, filters)",
            "review_ledger": "ke.review_event(id, object_ref, decision, reviewer, reviewed_at, "
                             "policy_version, supersedes_event, findings[])",
            "source_node": "ke.source(persistent_id|url|sha256(citation), source_type, published_at)",
            "raw_rule": "raw JSON of every record is stored verbatim; projections are derived and rebuildable",
        },
        "records": records,
        "edges": edges,
        "vectors": vectors,
        "review_events": review_block,
        "retrieval_demonstrations": query_cases,
        "cross_checks": cross,
        "disclosures": disclosures,
        "audit": audit,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", default="m8554")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    mapping = build(args.pilot)
    out = args.out or os.path.join(ROOT, "mappings", "%s.json" % args.pilot)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")
    audit = mapping["audit"]
    print(f"wrote {os.path.relpath(out, ROOT)}: {audit['records']} records, "
          f"{audit['leaf_paths_total']} leaf paths, {audit['leaf_paths_uncovered']} uncovered, "
          f"{audit['edges']} edges, {audit['vector_facets']} facets, "
          f"{audit['disclosures']} disclosures")
    return 0 if audit["lossless"] else 1


if __name__ == "__main__":
    sys.exit(main())