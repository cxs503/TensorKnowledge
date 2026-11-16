-- PROD-RA m22760 返修独立复审 verdict（m22923）
-- scope: ra-rereview-m22760
-- verdict: changes_requested, level=2

INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES (
    'TensorKnowledge',
    'ra-rereview-m22760',
    22760,
    2,
    '{"review_report": "docs/m22923/REVIEW-REPORT.md", "six_checks": {"artifact_identity": "partial", "criteria_frozen_before_run": "not_run", "evidence_traceability": "not_run", "independent_rerun": "partial", "failure_record": "not_run", "regression_scope": "partial"}, "d1_d12_status": {"D1": "unfixed_on_main", "D2": "unfixed_on_main", "D3": "unfixed_on_main", "D4": "unfixed_on_main", "D5": "unfixed_on_main", "D6": "unfixed_on_main", "D7": "confirmed", "D8": "unfixed_on_main", "D9": "unfixed_on_main", "D10": "partially_confirmed", "D11": "unfixed_on_main", "D12": "unfixed_on_main"}, "verdict": "changes_requested", "reason": "D7 confirmed; D1-D6/D8-D12 evidence files filtered by pusher gate (runs/ blacklist), not on origin/main; six_checks 3 not_run + 3 partial; delivery layout violation (runs/ blacklist)"}',
    'tp-native-1'
);
