-- PROD-RA m22059 证据最终复审 verdict（m23017）
-- scope: ra-rereview3-m22059-evidence
-- verdict: changes_requested, level=2
-- 前史: m22923=changes_requested level2（runs/ 黑名单滤除）；m22059 证据已并 main（a168dec）
-- 本单: 以 origin/main 实际文件复核，迁移未修复底层缺陷

INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES (
    'TensorKnowledge',
    'ra-rereview3-m22059-evidence',
    23017,
    2,
    '{"review_report": "docs/m23017/REVIEW-REPORT.md", "six_checks": {"artifact_identity": "partial", "criteria_frozen_before_run": "not_run", "evidence_traceability": "partial", "independent_rerun": "partial", "failure_record": "partial", "regression_scope": "not_run"}, "d1_d12_status": {"D1": "unfixed", "D2": "unfixed", "D3": "unfixed", "D4": "unfixed", "D5": "unfixed", "D6": "unfixed", "D7": "confirmed", "D8": "unfixed", "D9": "unfixed", "D10": "unfixed", "D11": "unfixed", "D12": "unfixed"}, "verdict": "changes_requested", "reason": "m22059 evidence migrated to docs/m22059/ (resolves runs/ blacklist) but migration did NOT fix underlying defects; D1-D6/D8-D12 still present on origin/main; six_checks 0 passed + 4 partial + 2 not_run; D7 confirmed fixed; scenario_validated=false", "scenario_validated": false}',
    'tp-native-1'
);
