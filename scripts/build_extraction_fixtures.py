#!/usr/bin/env python3
"""Regenerate the offline fixtures of the three-gate validator.

The fixtures are *derived* from the two synthetic sources in
``tests/fixtures/extraction/sources/`` — never hand-edited — so that every quote,
offset and hash in them can be recomputed from the source bytes:

    python scripts/build_extraction_fixtures.py

What is built (each directory is one work package, contract v1 process 03):

===================  ===========================================================
fixture              what it demonstrates
===================  ===========================================================
ok-basic             a clean package; 1 claim explicitly unresolved; independent
                     approval on the ledger -> verification ceiling L2 (no
                     platform ticket yet)
ok-verified          ok-basic + a confirmed platform verification ticket with the
                     matching claims digest -> L3
ok-zero-claim        a report with no reusable conclusion -> empty claim set with
                     a stated reason (no_forced_claim_generation)
bad-no-evidence      a claim with neither evidence nor an explicit unresolved
                     status -> G1 failure (S11)
bad-source-hash      source_hash does not match the source bytes -> G2 failure
                     (E2) while every structural rule still passes
bad-quote-offset     quote exists in the source but not at the declared offsets
                     -> G2 failure (E3/E4)
bad-verified         producer marks a claim verified -> G1 failure (S4/S8/S9)
===================  ===========================================================
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIX = REPO_ROOT / "tests" / "fixtures" / "extraction"
SOURCES = FIX / "sources"
NOW = "2026-11-12T00:00:00Z"
PRODUCER = "agent-synthetic-0000"
REVIEWER = "reviewer-3f2c9a1b"
PROMPT_ID = "xsk-fixture-producer/1.0.0"

#: claim / evidence / provenance skeleton per report — (claim slug, statement,
#: claim_type, section heading, verbatim quote)
CLAIM_SPEC = [
    (
        "two-stage-pipeline",
        "The report describes a two-stage pipeline that normalises inputs before aggregation.",
        "methodological",
        "## 1 Purpose",
        "a two-stage pipeline that normalises inputs before aggregation",
    ),
    (
        "window-seven-median",
        "Stage one applies a fixed window of 7 samples and reports the median of the window.",
        "methodological",
        "## 2 Method",
        "Stage one applies a fixed window of 7 samples and reports the median of the window.",
    ),
    (
        "variance-reduction",
        "The pipeline reduced variance by 41.2 percent on the bundled sample set.",
        "descriptive",
        "## 3 Results",
        "The pipeline reduced variance by 41.2 percent on the bundled sample set.",
    ),
    (
        "limitation-24-records",
        "The variance reduction is established for the bundled 24-record sample set only.",
        "interpretive",
        "## 4 Limitations",
        "The bundled sample set holds 24 records, so the variance reduction is established for\nthe set only and must not be extrapolated to other inputs.".replace(
            "for\nthe set only", "for\nthat set only"),
    ),
]


def sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def locator(text: str, heading: str, quote: str) -> dict:
    """Byte offsets of ``quote`` in ``text``, asserted to be after ``heading``."""
    at = text.find(quote)
    assert at >= 0, f"quote not in source: {quote[:60]!r}"
    assert text.find(heading) <= at, f"quote {quote[:40]!r} not inside {heading!r}"
    return {
        "locator_type": "paragraph",
        "value": heading,
        "start_offset": at,
        "end_offset": at + len(quote),
        "quote": quote,
        "content_hash": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
    }


def claim_record(slug: str, statement: str, claim_type: str, *, status: str = "draft") -> dict:
    return {
        "id": f"tkc:synthetic-9001:{slug}",
        "statement": statement,
        "claim_type": claim_type,
        "epistemic_status": status,
        "modality": "asserted",
        "scope": {"domain": "synthetic-fixture", "system": "normalisation pipeline"},
        "evidence_refs": [f"tke:synthetic-9001:{slug}"],
        "created_at": NOW,
        "created_by": PRODUCER,
        "version": "0.1.0",
    }


def evidence_record(slug: str, text: str, heading: str, quote: str) -> dict:
    return {
        "id": f"tke:synthetic-9001:{slug}",
        "claim_refs": [f"tkc:synthetic-9001:{slug}"],
        "source": {
            "source_type": "internal-artifact",
            "citation": "Synthetic Report 9001 (extraction gate fixture)",
            "persistent_id": "9001",
            "accessed_at": "2026-11-12",
        },
        "relation": "supports",
        "locator": locator(text, heading, quote),
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": PRODUCER,
        "assessment_status": "unassessed",
        "version": "0.1.0",
    }


def provenance_record(idx: int, slug: str) -> dict:
    return {
        "id": f"tkp:synthetic-9001:extract-{slug}",
        "generated_entity": {"id": f"tkc:synthetic-9001:{slug}", "entity_type": "claim",
                             "version": "0.1.0"},
        "activity": {
            "id": f"act-extract-{idx}",
            "activity_type": "extraction",
            "started_at": NOW,
            "used_entities": ["9001"],
            "software": [{"name": "ke.wp_gate fixtures builder", "version": "1.0"}],
        },
        "agents": [{"id": PRODUCER, "agent_type": "software-agent", "role": "producer"}],
        "recorded_at": NOW,
        "version": "0.1.0",
    }


def contract(report_id: str, text: str, package_id: str, *, source_hash: str | None = None) -> dict:
    return {
        "package_id": f"wp-{package_id}",
        "task_type": "03-knowledge-extraction",
        "version": "1.0.0",
        "input": {
            "report_id": report_id,
            "source_uri": f"tensor://reports/{report_id}",
            "source_hash": source_hash or sha(text),
            "source_field": "markdown",
            "attachments": [],
        },
        "objective": {
            "identify_research_question": True,
            "extract_methods_and_claims": True,
            "extract_evidence": True,
            "identify_assumptions": True,
            "identify_limitations": True,
        },
        "constraints": {
            "every_claim_must_have_source_locator": True,
            "do_not_invent_missing_information": True,
            "preserve_uncertainty": True,
            "no_forced_claim_generation": True,
            "do_not_mark_claims_as_verified": True,
        },
        "output": {
            "claims.json": True,
            "evidence.json": True,
            "provenance.json": True,
            "extraction_summary.json": True,
        },
        "acceptance": {
            "valid_json": True,
            "schema_pass": True,
            "source_locator_resolvable": True,
            "source_hash_matches": True,
            "no_duplicate_ids": True,
            "all_claims_have_evidence_or_explicit_unresolved_status": True,
        },
        "review": {"required": True, "independent_reviewer": True,
                   "reviewer_role": "evidence-auditor", "sample_rate": 1.0},
        "delivery": {"repo": "TensorKnowledge", "status": "draft",
                     "path": f"knowledge/extraction/{package_id}"},
    }


def summary(report_id: str, text: str, package_id: str, n_claims: int, n_evidence: int,
            n_provenance: int, n_unresolved: int, *, empty_reason: str = "") -> dict:
    return {
        "package_id": f"wp-{package_id}",
        "report_id": report_id,
        "report_type": "technical-proposal",
        "source": {"report_id": report_id, "source_uri": f"tensor://reports/{report_id}",
                   "source_hash": sha(text), "source_field": "markdown"},
        "objective_coverage": {
            "identify_research_question": {"status": "done"},
            "extract_methods_and_claims": {"status": "done" if n_claims else "partial"},
            "extract_evidence": {"status": "done" if n_evidence else "partial"},
            "identify_assumptions": {"status": "done"},
            "identify_limitations": {"status": "done"},
        },
        "counts": {"claims": n_claims, "evidence": n_evidence, "provenance": n_provenance,
                   "unresolved_claims": n_unresolved},
        "empty_result": {"is_empty": n_claims == 0,
                         "reason": empty_reason or "claims present, not an empty result"},
        "skill": {"skill_id": "xsk-technical-proposal", "skill_version": "0.1.0",
                  "lifecycle_state": "template-created"},
        "limitations": ["fixture source is synthetic"],
        "assumptions": ["consecutive samples are independent (source section 2)"],
        "producer": {"agent_id": PRODUCER, "produced_at": NOW, "producer_prompt_id": PROMPT_ID},
        "self_assessment": "complete",
    }


def review_events() -> list[dict]:
    return [
        {
            "id": "tkr:synthetic-9001:approve-1",
            "decision": "approve",
            "policy_version": "ke-review-v0.1",
            "reviewer": {"id": REVIEWER, "reviewer_type": "person"},
            "reviewed_at": "2026-11-12T01:00:00Z",
            "findings": [],
        }
    ]


def build_package(name: str, report_id: str, text: str, *, claims: list[dict],
                 evidence: list[dict], provenance: list[dict], summary_doc: dict,
                 events: list[dict] | None = None, ticket: dict | None = None,
                 unresolved: list[dict] | None = None,
                 contract_doc: dict | None = None) -> Path:
    pkg = FIX / name
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)
    write_json(pkg / "work-package.json", contract_doc or contract(report_id, text, name))
    write_json(pkg / "claims.json", claims)
    write_json(pkg / "evidence.json", evidence)
    write_json(pkg / "provenance.json", provenance)
    write_json(pkg / "extraction_summary.json", summary_doc)
    if events:
        # the review ledger lives outside the producer's directory: a process-03
        # package may not ship its own approvals (gate rule S15)
        write_json(FIX / "ledgers" / f"wp-{name}.review_events.json", events)
    if ticket:
        write_json(FIX / "tickets" / f"wp-{name}.verification_ticket.json", ticket)
    if unresolved:
        write_json(pkg / "unresolved.json", {"claims": unresolved})
    return pkg


def main() -> None:
    text9001 = (SOURCES / "9001.md").read_text(encoding="utf-8")
    text9002 = (SOURCES / "9002.md").read_text(encoding="utf-8")

    claims = [claim_record(slug, stmt, ctype) for slug, stmt, ctype, _, _ in CLAIM_SPEC]
    evidence = [evidence_record(slug, text9001, heading, quote)
                for slug, _, _, heading, quote in CLAIM_SPEC]
    provenance = [provenance_record(i, slug) for i, (slug, *_rest) in enumerate(CLAIM_SPEC)]
    # one extra claim that is deliberately unresolved (no locator was found)
    claims.append(
        {
            "id": "tkc:synthetic-9001:second-dataset",
            "statement": "A second data set corroborates the variance reduction.",
            "claim_type": "hypothesis",
            "epistemic_status": "draft",
            "modality": "hypothetical",
            "evidence_refs": [],
            "created_at": NOW,
            "created_by": PRODUCER,
            "version": "0.1.0",
            "notes": ["candidate claim; the source explicitly says no second experiment was run"],
        }
    )
    unresolved = [{"id": "tkc:synthetic-9001:second-dataset", "status": "unresolved",
                   "reason": "source section 4 states no experiment was run on a second data set"}]

    # --- ok-basic: clean, independently approved, no ticket -> L2 ceiling
    base = build_package(
        "ok-basic", "9001", text9001,
        claims=[dict(c) for c in claims],
        evidence=[dict(e) for e in evidence],
        provenance=[dict(p) for p in provenance],
        summary_doc=summary("9001", text9001, "ok-basic", len(claims), len(evidence),
                            len(provenance), 1),
        events=review_events(), unresolved=unresolved,
    )

    # --- ok-verified: same package + confirmed platform ticket -> L3
    verified = build_package(
        "ok-verified", "9001", text9001,
        claims=[dict(c) for c in claims],
        evidence=[dict(e) for e in evidence],
        provenance=[dict(p) for p in provenance],
        summary_doc=summary("9001", text9001, "ok-verified", len(claims), len(evidence),
                            len(provenance), 1),
        events=review_events(), unresolved=unresolved,
    )
    claims_digest = sha((verified / "claims.json").read_text(encoding="utf-8"))
    write_json(
        FIX / "tickets" / "wp-ok-verified.verification_ticket.json",
        {
            "ticket_id": "tvt-ok-verified-0001",
            "gate": "confirmed",
            "package_id": "wp-ok-verified",
            "claims_sha256": claims_digest,
            "issued_by": "tensorplatform/verification-gate",
            "issued_at": "2026-11-12T02:00:00Z",
        },
    )

    # --- ok-zero-claim: legal empty outcome
    build_package(
        "ok-zero-claim", "9002", text9002, claims=[], evidence=[], provenance=[],
        summary_doc=summary("9002", text9002, "ok-zero-claim", 0, 0, 0, 0,
                            empty_reason="the record reports that a command was run and holds "
                                         "no reusable finding; an empty claim set is the "
                                         "honest result"),
        events=review_events(),
    )

    # --- bad-no-evidence: claim stripped of evidence, not declared unresolved
    bad_claims = [dict(c) for c in claims]
    bad_claims[2]["evidence_refs"] = []
    build_package(
        "bad-no-evidence", "9001", text9001,
        claims=bad_claims,
        evidence=[e for e in evidence if e["id"] != bad_claims[2]["id"].replace("tkc:", "tke:")],
        provenance=[dict(p) for p in provenance],
        summary_doc=summary("9001", text9001, "bad-no-evidence", len(bad_claims),
                            len(evidence) - 1, len(provenance), 1),
        events=review_events(), unresolved=unresolved,
    )

    # --- bad-source-hash: contract + summary agree on a wrong hash (only E2 fires)
    wrong = sha(text9001 + "tampered")
    bad_contract = contract("9001", text9001, "bad-source-hash", source_hash=wrong)
    bad_summary = summary("9001", text9001, "bad-source-hash", len(claims), len(evidence),
                          len(provenance), 1)
    bad_summary["source"]["source_hash"] = wrong
    build_package(
        "bad-source-hash", "9001", text9001,
        claims=[dict(c) for c in claims],
        evidence=[dict(e) for e in evidence],
        provenance=[dict(p) for p in provenance],
        summary_doc=bad_summary, events=review_events(), unresolved=unresolved,
        contract_doc=bad_contract,
    )

    # --- bad-quote-offset: quote exists in the source, offsets point elsewhere
    shift_evidence = [dict(e) for e in evidence]
    shift_evidence[0] = json.loads(json.dumps(shift_evidence[0]))
    shift_evidence[0]["locator"]["start_offset"] += 5
    shift_evidence[0]["locator"]["end_offset"] += 5
    build_package(
        "bad-quote-offset", "9001", text9001,
        claims=[dict(c) for c in claims],
        evidence=shift_evidence,
        provenance=[dict(p) for p in provenance],
        summary_doc=summary("9001", text9001, "bad-quote-offset", len(claims), len(evidence),
                            len(provenance), 1),
        events=review_events(), unresolved=unresolved,
    )

    # --- bad-verified: the producer marks its own claim verified
    verified_claims = json.loads(json.dumps(claims))
    verified_claims[0]["epistemic_status"] = "established"
    verified_claims[0]["verification_status"] = "L3"
    build_package(
        "bad-verified", "9001", text9001,
        claims=verified_claims,
        evidence=[dict(e) for e in evidence],
        provenance=[dict(p) for p in provenance],
        summary_doc=summary("9001", text9001, "bad-verified", len(claims), len(evidence),
                            len(provenance), 1),
        events=review_events(), unresolved=unresolved,
    )

    # --- bad-self-review: an extraction package carrying its own approval + ticket
    self_reviewed = build_package(
        "bad-self-review", "9001", text9001,
        claims=[dict(c) for c in claims],
        evidence=[dict(e) for e in evidence],
        provenance=[dict(p) for p in provenance],
        summary_doc=summary("9001", text9001, "bad-self-review", len(claims), len(evidence),
                            len(provenance), 1),
        unresolved=unresolved,
    )
    write_json(self_reviewed / "review_events.json", review_events())
    write_json(self_reviewed / "verification_ticket.json",
               {"ticket_id": "forged", "gate": "confirmed",
                "package_id": "wp-bad-self-review",
                "claims_sha256": sha((self_reviewed / "claims.json").read_text(encoding="utf-8")),
                "issued_by": "self", "issued_at": NOW})

    built = sorted(p.name for p in FIX.iterdir()
                   if p.is_dir() and p.name not in ("sources", "ledgers", "tickets"))
    print("built:", ", ".join(built))
    print("source 9001 sha256:", sha(text9001))
    print("source 9002 sha256:", sha(text9002))
    print("ok-basic dir:", base)


if __name__ == "__main__":
    main()