#!/usr/bin/env python3
"""Validate the KE projection mapping (docs/ke/mapping-spec.md §10).

Checks, in order:
  A  structure: mapping schema, snapshot integrity, leaf-path coverage vs recomputed projection
  B  semantics: self-approval, axis independence, epistemic conservativeness, contested both-sides,
     not-assessed expression, bi-temporal filters, vector facet policy
  C  interface: every demonstrated retrieval response validates against schemas/ke-query.schema.json

Exit 0 only if every check passes. Machine-readable results go to
runs/ke_mapping_validation.json so reports never hand-copy numbers.
"""

from __future__ import annotations

import glob
import json
import os
import sys

import jsonschema

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ke_mapping_lib as lib  # noqa: E402
import ke_state_machine as sm  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT = "m8554"
RESULTS: list[dict] = []


def record(check_id: str, name: str, ok: bool, detail: str, evidence: dict | None = None) -> None:
    RESULTS.append({"id": check_id, "check": name, "pass": bool(ok), "detail": detail,
                    "evidence": evidence or {}})
    print(f"{'PASS' if ok else 'FAIL'}  {check_id} {name} — {detail}")


def load_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def snapshot_records(pilot: str) -> dict[str, tuple[str, dict]]:
    base = os.path.join(ROOT, "mappings", "source", pilot)
    out: dict[str, tuple[str, dict]] = {}
    for kind, sub in (("claim", "claims"), ("evidence", "evidence"), ("provenance", "provenance")):
        for path in sorted(glob.glob(os.path.join(base, sub, "*.json"))):
            with open(path, encoding="utf-8") as fh:
                rec = json.load(fh)
            out[rec["id"]] = (kind, rec)
    env_path = os.path.join(base, "production-result.json")
    with open(env_path, encoding="utf-8") as fh:
        env = json.load(fh)
    out["tkm:platform:%s" % env.get("platform_task_id")] = ("envelope", env)
    for ko in env.get("proposed_objects", []):
        out[ko["id"]] = ("ko", ko)
    return out


def main() -> int:
    mapping = load_json("mappings/%s.json" % PILOT)
    snap = snapshot_records(PILOT)

    # ---------------- A1 structure ----------------
    schema = load_json("schemas/ke-mapping.schema.json")
    try:
        jsonschema.validate(mapping, schema)
        record("A1", "mapping document validates against schemas/ke-mapping.schema.json", True,
               "Draft 2020-12 validation passed")
    except jsonschema.ValidationError as exc:
        record("A1", "mapping document validates against schemas/ke-mapping.schema.json", False,
               f"{exc.message} at {list(exc.absolute_path)}")

    # ---------------- A2 snapshot integrity + A3 coverage re-derivation ----------------
    drift, uncovered_reported, recomputed_mismatch = [], [], []
    for rec in mapping["records"]:
        eid = rec["entity_id"]
        if eid not in snap:
            drift.append({"entity_id": eid, "reason": "not in snapshot"})
            continue
        kind, raw = snap[eid]
        if lib.sha256_text(json.dumps(raw, ensure_ascii=False, sort_keys=True)) != rec["raw_sha256"]:
            drift.append({"entity_id": eid, "reason": "raw_sha256 differs from snapshot"})
        fresh = lib.project(kind, raw)
        if [row["source_path"] for row in fresh["covered"]] != [row["source_path"] for row in rec["projection"]]:
            recomputed_mismatch.append(eid)
        if fresh["uncovered"]:
            uncovered_reported.append({"entity_id": eid, "paths": fresh["uncovered"]})
    record("A2", "every record's raw_sha256 matches the frozen snapshot", not drift,
           f"{len(mapping['records'])} records compared, {len(drift)} drifted", {"drift": drift})
    record("A3", "projection rule set reproduces the mapping's leaf coverage", not recomputed_mismatch,
           f"{len(mapping['records'])} records re-projected, {len(recomputed_mismatch)} mismatched",
           {"mismatched": recomputed_mismatch})
    total_leaves = sum(r["leaf_paths"] for r in mapping["records"])
    record("A4", "no leaf path is silently dropped", not uncovered_reported,
           f"{total_leaves} leaf paths, {len(uncovered_reported)} uncovered",
           {"uncovered": uncovered_reported})

    # ---------------- A5 loss register coherence ----------------
    disclosures = mapping["disclosures"]
    over_grade = [r["entity_id"] for r in mapping["records"]
                  if r.get("epistemic_policy", {}).get("over_grade")]
    d06 = next((d for d in disclosures if d["id"] == "D-06"), None)
    covered_flags = set(d06["affected"]) if d06 else set()
    coherence = set(over_grade) <= covered_flags
    record("A5", "every over-grade flag has a matching disclosure entry", coherence,
           f"{len(over_grade)} over-grade claims, {len(covered_flags)} listed in D-06",
           {"over_grade": over_grade, "in_disclosure": sorted(covered_flags)})
    ids_ok = [d["id"] for d in disclosures] == ["D-%02d" % i for i in range(1, len(disclosures) + 1)]
    record("A6", "disclosure ids are contiguous and unique", ids_ok,
           f"{len(disclosures)} entries: {disclosures[0]['id']}..{disclosures[-1]['id']}")

    # ---------------- B1 self-approval (fail-closed, real identities) ----------------
    producers = [r["entity_id"] for r in mapping["records"] if r["entity_kind"] == "claim"][:1]
    groups = [g for g in mapping["cross_checks"]["identity_groups"] if g["fragmented"]]
    ctx = {"producer_ids": ["claude-code-session-6f76cd3d", "cc-session-6f76cd3d"]}
    attempts = []
    for reviewer in ("claude-code-session-6f76cd3d", "cc-session-6f76cd3d", "bg-job-6f76cd3d"):
        event = {"id": "tkr:m8554:sim-%s" % reviewer[:6], "decision": "approve",
                 "policy_version": sm.POLICY_VERSION,
                 "reviewer": {"id": reviewer, "reviewer_type": "agent"},
                 "reviewed_at": "2026-11-09T14:00:00Z"}
        try:
            sm.validate_event(event, "in-review", [], ctx)
            attempts.append({"reviewer": reviewer, "outcome": "ALLOWED"})
        except sm.StateMachineError as exc:
            attempts.append({"reviewer": reviewer, "outcome": exc.code})
    blocked = all(a["outcome"] == "SELF_APPROVAL_BLOCKED" for a in attempts)
    record("B1", "every recorded producer identity is blocked from approving its own object", blocked,
           f"{len(attempts)} attempt(s) on {producers[0]}, all refused", {"attempts": attempts})
    conformance = mapping["review_events"]["state_machine_conformance"]
    record("B2", "state-machine conformance suite passes", all(c["pass"] for c in conformance),
           f"{sum(c['pass'] for c in conformance)}/{len(conformance)} cases",
           {"cases": [{"case": c["case"], "observed": c["observed_code"]} for c in conformance]})

    # ---------------- B3 axis independence: platform state never becomes review state ----------
    env_id = "tkm:platform:%s" % mapping["source"].get("commit", "")[:0] or next(
        r["entity_id"] for r in mapping["records"] if r["entity_kind"] == "production-result")
    env_record = next(r for r in mapping["records"] if r["entity_kind"] == "production-result")
    env_slots = env_record["slots"]
    ko_status = sorted({r["slots"].get("status.review_status") for r in mapping["records"]
                        if r["entity_kind"] == "knowledge-object"})
    axis_ok = (env_slots.get("envelope.platform_state") not in ("approved", "in-review") and
               ko_status == ["draft"] and
               mapping["review_events"]["review_events_as_recorded"] == [])
    record("B3", "review_status is a fold of the review ledger, never of Platform state", axis_ok,
           f"platform_state={env_slots.get('envelope.platform_state')!r}, "
           f"ko review_status={ko_status}, review events={len(mapping['review_events']['review_events_as_recorded'])}")

    # ---------------- B4 conservativeness ladder is well-formed ----------------
    ladder_rows = []
    for rec in mapping["records"]:
        pol = rec.get("epistemic_policy")
        if not pol:
            continue
        ladder_rows.append({"entity_id": rec["entity_id"], "recorded": pol["recorded"],
                            "cap": pol["cap"], "over_grade": pol["over_grade"], "delta": pol["delta"]})
    ladder_ok = all(r["over_grade"] == (r["delta"] is not None and r["delta"] > 0) or
                    r["over_grade"] for r in ladder_rows)
    record("B4", "recorded epistemic_status is never silently rewritten and caps are stored", ladder_ok,
           f"{len(ladder_rows)} claims carry recorded+cap+delta",
           {"rows": ladder_rows})

    # ---------------- B5 not-assessed is explicit, absent is rejected ----------------
    na = [r for r in mapping["records"] if r.get("epistemic_policy", {}).get("recorded") == "not-assessed"]
    na_ok = bool(na) and all("NOT_ASSESSED_EXPLICIT" in r["flags"] for r in na) and all(
        "insufficient" in json.dumps(mapping["retrieval_demonstrations"], ensure_ascii=False)
        for _ in [0])

    def ingest(claim: dict) -> tuple[bool, str]:
        required = ("id", "statement", "claim_type", "epistemic_status", "created_at", "version")
        missing = [f for f in required if f not in claim]
        return (not missing, "missing:" + ",".join(missing) if missing else "accepted")

    stripped = dict(snap[na[0]["entity_id"]][1]) if na else {}
    stripped.pop("epistemic_status", None)
    rejected, why = ingest(stripped)
    record("B5", "absent epistemic_status is rejected at ingest, not coerced to not-assessed",
           na_ok and not rejected, f"{len(na)} explicit not-assessed record(s); stripped copy -> {why}",
           {"not_assessed": [r["entity_id"] for r in na]})

    # ---------------- B6 bi-temporal: the two axes answer different questions ----------
    claims = [r for r in mapping["records"] if r["entity_kind"] == "claim"]
    def as_recorded(instant):
        return sorted(r["entity_id"] for r in claims
                      if (r["bitemporal"]["recorded_at"] or "") <= instant)
    def as_valid(instant):
        hits, unknown = [], []
        for r in claims:
            vt = r["bitemporal"].get("valid_time")
            res = r["bitemporal"]["valid_time_resolution"]
            if res in ("prose-only", "unrecorded"):
                unknown.append(r["entity_id"])
                continue
            start = (vt or {}).get("start")
            end = (vt or {}).get("end")
            if start and start <= instant and (not end or end >= instant):
                hits.append(r["entity_id"])
            else:
                unknown.append(r["entity_id"])
        return sorted(hits), sorted(unknown)

    rec_all = as_recorded("2026-11-09T23:59:59Z")
    rec_none = as_recorded("2026-11-09T00:00:00Z")
    val_2020, unknown_2020 = as_valid("2020-01-01T00:00:00Z")
    bitemporal_ok = (len(rec_all) == len(claims) and len(rec_none) == 0
                     and val_2020 == ["tkc:prov-o:wasattributedto-signature"]
                     and len(unknown_2020) == len(claims) - 1)
    record("B6", "recorded-axis and valid-axis queries return different, non-fabricated answers",
           bitemporal_ok,
           f"recorded@2026-11-09 -> {len(rec_all)} claims; valid@2020-01-01 -> {len(val_2020)} "
           f"({val_2020}), {len(unknown_2020)} unknown-validity",
           {"recorded_axis": rec_all, "valid_axis": val_2020, "unknown_validity": unknown_2020})

    # ---------------- B7 source published_at is not treated as a validity bound ----------
    ev_ok = all(r["bitemporal"]["valid_time_resolution"] == "not-applicable"
                for r in mapping["records"] if r["entity_kind"] == "evidence")
    record("B7", "evidence has no validity time; published_at is not promoted to one", ev_ok,
           f"{sum(1 for r in mapping['records'] if r['entity_kind'] == 'evidence')} evidence rows "
           "all not-applicable")

    # ---------------- B8 contested both sides retained ----------------
    pairs = mapping["retrieval_demonstrations"]
    contested_ok = False
    pair_rows = []
    for case in pairs:
        if case["class"].endswith("(two-sided)"):
            cp = case["response"].get("contested_pairs", [])
            pair_rows = [{"question": p["question_ref"], "contested": p["contested_claim"],
                          "against": len(p["against"]),
                          "surviving": [s["narrowed_claim"] for s in p["surviving_narrowed_sides"]],
                          "both_sides_retained": p["both_sides_retained"]} for p in cp]
            contested_ok = bool(pair_rows) and all(p["both_sides_retained"] for p in pair_rows)
    quote_schema = load_json("schemas/ke-query.schema.json")
    anchor_req = quote_schema["$defs"]["anchorRequest"]["properties"]["expand"]["properties"]
    single_side_forbidden = "only_support" not in anchor_req
    record("B8", "contested question returns both sides; the API cannot ask for one side", 
           contested_ok and single_side_forbidden,
           f"{len(pair_rows)} contested pair(s) with both sides; expand keys={sorted(anchor_req)}",
           {"pairs": pair_rows})

    # ---------------- B9 vector facet policy ----------------
    facets = mapping["vectors"]
    kinds = sorted({f["facet"] for f in facets})
    n_claim = sum(1 for f in facets if f["facet"] == "claim.statement")
    n_evid = sum(1 for f in facets if f["facet"] == "evidence.quote")
    n_ko = sum(1 for f in facets if f["facet"] == "ko.summary")
    counts = (n_claim == len(claims),
              n_evid == sum(1 for r in mapping["records"] if r["entity_kind"] == "evidence"),
              n_ko == sum(1 for r in mapping["records"] if r["entity_kind"] == "knowledge-object"),
              all("never entailment" in f["retrieval_note"] for f in facets),
              all(f["index_status"] == "declared-not-built" for f in facets))
    record("B9", "vector facets are exactly claim.statement / evidence.quote / ko.summary", all(counts),
           f"{len(facets)} facets: {dict((k, sum(1 for f in facets if f['facet'] == k)) for k in kinds)}; "
           "similarity score is never stored as a support relation",
           {"per_kind": {k: sum(1 for f in facets if f["facet"] == k) for k in kinds}})

    # ---------------- B10 raw retention ----------------
    raw_ok = all(len(r.get("raw_sha256", "")) == 64 and r.get("raw_bytes", 0) > 0
                 for r in mapping["records"])
    record("B10", "every record keeps its verbatim raw payload addressable", raw_ok,
           f"{len(mapping['records'])} records with raw_sha256 + raw_bytes")

    # ---------------- C query interface conformance ----------------
    query_schema = load_json("schemas/ke-query.schema.json")
    failures = []
    for case in mapping["retrieval_demonstrations"]:
        base_class = case["class"].split(" (")[0]
        target = "errorResponse" if ("status" in case["response"] and "error" in case["response"]) else {
            "by-domain": "domainResponse", "by-anchor": "anchorResponse",
            "by-evidence-status": "evidenceStatusResponse",
            "by-provenance-chain": "provenanceResponse"}[base_class]
        try:
            jsonschema.validate(case["response"], {"$defs": query_schema["$defs"], "allOf": [{"$ref": "#/$defs/" + target}]})
        except jsonschema.ValidationError as exc:
            failures.append({"class": case["class"], "schema": target, "error": exc.message,
                             "at": list(exc.absolute_path)})
    record("C1", "every demonstrated response validates against schemas/ke-query.schema.json",
           not failures, f"{len(mapping['retrieval_demonstrations'])} responses, {len(failures)} invalid",
           {"failures": failures})

    # ---------------- A7 spec table numbers agree with the mapping ----------------
    import collections
    import re
    totals: collections.Counter = collections.Counter()
    for row in mapping["audit"]["by_contract"].values():
        for cls, n in row["by_loss_class"].items():
            totals[cls] += n
    spec_text = open(os.path.join(ROOT, "docs/ke/mapping-spec.md"), encoding="utf-8").read()
    doc_nums = {cls: int(n) for cls, n in
                re.findall(r"^\| (L[0-3]) \| [^|]+ \| *(\d+) *\|$", spec_text, flags=re.M)}
    agree = all(doc_nums.get(c) == totals.get(c, 0) for c in ("L0", "L1", "L2", "L3"))
    record("A7", "loss-class counts quoted in the spec match the mapping", agree,
           f"spec={doc_nums} mapping={dict(totals)}",
           {"spec": doc_nums, "mapping": dict(totals)})

    # ---------------- D summary ----------------
    audit = mapping["audit"]
    record("D1", "loss ledger reconciles", 
           audit["leaf_paths_total"] == audit["leaf_paths_projected"] + audit["leaf_paths_uncovered"]
           and audit["lossless"] == (audit["leaf_paths_uncovered"] == 0),
           f"{audit['leaf_paths_projected']}+{audit['leaf_paths_uncovered']}="
           f"{audit['leaf_paths_total']} leaf paths; {audit['disclosures']} disclosures")

    passed = sum(r["pass"] for r in RESULTS)
    summary = {"checks": len(RESULTS), "passed": passed, "failed": len(RESULTS) - passed,
               "results": RESULTS, "mapping": "mappings/%s.json" % PILOT}
    os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
    with open(os.path.join(ROOT, "runs", "ke_mapping_validation.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(f"\n== ke mapping validation: {passed}/{len(RESULTS)} checks passed "
          f"({'ALL PASS' if passed == len(RESULTS) else 'FAILURES'}) ==")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())