#!/usr/bin/env python3
"""Build docs/review_m22059_prod_ra/verdict_insert_r4.sql from recheck_r4_output.json.

Idempotent: the row is keyed by (repo, scope, verdict_by); re-running UPDATEs it.
scope = ra-rereview4-m22059-fixes, mission_id = 23090.
"""
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
R = D.parent.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
o = json.loads((D / "recheck_r4_output.json").read_text(encoding="utf-8"))
ir, ai, cfz, et, fr, rsx = (o["independent_rerun"], o["artifact_identity"],
                            o["criteria_frozen_before_run"], o["evidence_traceability"],
                            o["failure_record"], o["regression_scope"])

ev = {
    "reviewed_commit": o["reviewed_commit"],
    "reviewed_repo": "TensorKnowledge",
    "review_repository_head": o["repository_head"],
    "reviewer": {"handle": "m23090-r4-independent", "independence": "independent_party",
                 "statement": "未编写被审文件；全部数字由 recheck_r4.py 从被审树重算"},
    "baseline": {"source": "tensor_maturity_verdicts row 903", "scope": "m22059 PROD-RA 试点验收",
                 "level": 2, "verdict": "changes_requested", "defects": 12,
                 "self_report": "docs/review_m22059_prod_ra/REPAIR-NOTES.md"},
    "d1_d12": {k: {"status": v["status"], "measurement": v["evidence"]} for k, v in o["d1_d12"].items()},
    "d1_d12_summary": o["d1_d12_summary"],
    "six_checks": o["six_checks"],
    "six_checks_measurement": {
        "artifact_identity": {"scenario_inputs_mismatch": ai["scenario_inputs_mismatch"],
                              "evidence_items_sha256_match": "5/5 (resolved only after re-rooting runs/m22059 -> docs/m22059)",
                              "corpus_copy_equals_primary_input": ai["corpus_copy_equals_primary_input"],
                              "reviewer_bundle_manifest_entries": ai["reviewer_bundle_manifest"]["entries"],
                              "reviewer_bundle_manifest_missing": ai["reviewer_bundle_manifest"]["entries_missing_file"]},
        "criteria_frozen_before_run": {"declared": cfz["declared_sha256"],
                                       "recomputed_canonical": cfz["recomputed_canonical_sha256"],
                                       "match_canonical": cfz["match_canonical"],
                                       "frozen_at": cfz["frozen_at"],
                                       "earliest_audit_output": cfz["earliest_audit_output_created_at"]},
        "evidence_traceability": {"locators": et["locators_total"],
                                  "slice_mismatch": len(et["locators_slice_mismatch"]),
                                  "empty_quotes": len(et["locators_with_empty_quote"]),
                                  "auditor_status": et["auditor_overall_status"],
                                  "auditor_findings": 0},
        "independent_rerun": {"citation_audit_exit": ir["citation_audit_positive"]["exit_code"],
                              "claim_evidence_audit_exit": ir["claim_evidence_audit_positive"]["exit_code"],
                              "claim_evidence_audit_negative_exit": ir["claim_evidence_audit_negative"]["exit_code"],
                              "status_reproduced": [ir["claim_evidence_audit_positive"]["status_rerun"],
                                                    ir["claim_evidence_audit_negative"]["status"]],
                              "triage_counts_reproduced": ir["claims_triage_counts"]},
        "failure_record": {"ledger_records": fr["ledger_records"],
                           "missing_fields": fr["records_missing_fields"],
                           "refs_without_sha256": fr["records_with_ref_without_sha256"],
                           "repro_cmd_without_commit": fr["records_without_commit_sha"]},
        "regression_scope": {"regression_scope_file": rsx["file_present"],
                             "adjacent_rerun": rsx["adjacent_rerun_tail"],
                             "full_suite": rsx["full_suite"]}},
    "residual_findings": o["residual_findings"],
    "verdict": o["verdict"],
    "scenario_validated": False,
    "scenario_validated_note": "复审单不抢跑；由协调者依裁决置位",
    "rerun": {"command": "python3 docs/review_m22059_prod_ra/recheck_r4.py --out "
                         "docs/review_m22059_prod_ra/recheck_r4_output.json",
              "exit_code": o["exit_code"],
              "exit_code_semantics": o["exit_code_semantics"],
              "as_shipped_recheck_py_exit": 1,
              "as_shipped_recheck_py_error": "KeyError: 'item_id' (recheck.py:214)"},
    "checks_not_run": ["full pytest suite (author cj4351 queued; not re-submitted by this reviewer)",
                       "cross-machine / cross-python rerun",
                       "verbatim audit of all 15 criteria against matrix/PRD (7 sampled)",
                       "PRD semantic precision / support macro-F1 (no labelled holdout)"],
    "artifacts": {str(p.relative_to(R)): sha(p) for p in (
        D / "REVIEW-R4.md", D / "recheck_r4.py", D / "recheck_r4_output.json",
        D / "figures/r4-d-status-six-checks.png", D / "figures/r4-rerun-exitcodes.png",
        R / "docs/m22059/validation-report.json", R / "docs/m22059/criteria.json")},
    "review_report": "docs/review_m22059_prod_ra/REVIEW-R4.md",
    "review_figure": "docs/review_m22059_prod_ra/figures/r4-d-status-six-checks.png",
}

sql = ("INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by) VALUES "
       "('TensorKnowledge','ra-rereview4-m22059-fixes',23090,2,$json$" + json.dumps(ev, ensure_ascii=False) +
       "$json$,'m23090-r4-independent') ON CONFLICT (repo, scope, verdict_by) DO UPDATE SET "
       "mission_id=EXCLUDED.mission_id, level=EXCLUDED.level, evidence=EXCLUDED.evidence, created_at=now() "
       "RETURNING id, level, gate_state;\n")
(D / "verdict_insert_r4.sql").write_text(sql, encoding="utf-8")
print("wrote verdict_insert_r4.sql", len(sql), "bytes")