-- Verdict for m15462 KBM-RCI-S2-PILOT200
-- Audited by m15812 (board-audit) on 2026-11-12
-- Level: L2 (独立功能实现)
-- Disposition: confirmed (消账)

INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES (
    'TensorKnowledge',
    'm15462 KBM-RCI-S2-PILOT200',
    '15812',
    2,
    '{"impl_files":"scripts/rci_corpus.py:1, scripts/rci_sampling.py:1, scripts/rci_ko.py:1, scripts/rci_pilot200.py:1, scripts/rci_review.py:1, scripts/rci_report.py:1","entry":"scripts/rci_pilot200.py","run_artifacts":"knowledge/rci-pilot200/","tests":"tests/test_rci_pilot200.py:15 passed","integration_callers":"none","benchmark":"field-level accuracy: claim=100%, evidence=100%, quality=100%, conditions=92.6%(FAIL), type_fit=35.2%(FAIL)","repro_cmd":"python scripts/rci_pilot200.py --corpus-root /root/tensor-ecosystem --n 200","external_anchor":"KBM-RCI-S2-PILOT200"}',
    'board-audit'
);
