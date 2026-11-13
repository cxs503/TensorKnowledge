-- m15922 交差核验落表（board-audit）
-- 对象：m15913 / TensorKnowledge / 锚点 KBM-RCI-F1-SPEC
-- 判级：实级 L4（基准验证）；平台门禁机器级预计 L2（F1：branch agent/m15913 未并入 main，callers_verified grep 盲）
INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES (
  'TensorKnowledge',
  'm15913 KBM-RCI-F1-SPEC',
  15922,
  4,
  jsonb_build_object(
    'impl_files', jsonb_build_array(
      '/root/tp-agent/work/m15913/ke/wp_line.py',
      '/root/tp-agent/work/m15913/scripts/run_wp_line.py',
      '/root/tp-agent/work/m15913/scripts/wp_line_artifacts.py',
      '/root/tp-agent/work/m15913/tests/test_wp_line.py',
      '/root/tp-agent/work/m15913/tests/test_wp_gate.py'
    ),
    'entry', '/root/tp-agent/work/m15913/scripts/run_wp_line.py',
    'run_artifacts', jsonb_build_array(
      '/root/tp-agent/work/m15913/docs/production/run-artifacts/benchmark.json',
      '/root/tp-agent/work/m15913/docs/production/run-artifacts/line_report.json',
      '/root/tp-agent/work/m15913/docs/production/run-artifacts/synthesis_input.json',
      '/root/tp-agent/work/m15913/docs/production/run-artifacts/asset_registration.json',
      '/root/tp-agent/work/m15913/docs/production/run-artifacts/RESULTS.md'
    ),
    'tests', jsonb_build_array(
      'pytest tests/test_wp_line.py tests/test_wp_gate.py -q -> 72 passed (auditor re-ran 2026-11-12, 4.35s)',
      'tests/test_wp_line.py:194 test_line_reproduces_the_declared_fixture_verdicts',
      'tests/test_wp_line.py:207 test_line_does_not_run_a_downstream_package_on_a_failed_upstream',
      'tests/test_wp_line.py:228 test_line_reports_synthesis_blocked_on_incomplete_base',
      'tests/test_wp_line.py:295 test_benchmark_meets_its_predeclared_thresholds',
      'tests/test_wp_line.py:304 test_one_mutation_reddens_exactly_the_declared_rule'
    ),
    'integration_callers', '/root/tp-agent/work/m15913/scripts/run_wp_line.py:22 "from ke.wp_line import main" (platform dispatch entry; NOTE grep on ECO main fails because branch agent/m15913 is NOT merged: git merge-base --is-ancestor agent/m15913 main -> false)',
    'benchmark',
      'docs/production/run-artifacts/benchmark.json (ref=docs/production/GATE-RULES.md fixture matrix, committed a1c0c76 BEFORE impl 355218c): '
      'verdict_agreement 1.0/1.0 (8/8), rule_agreement 1.0/1.0, level_agreement 1.0/1.0, mutation_detection 21/21=1.0, rule_coverage 27/27=1.0 vs threshold 0.90; '
      'auditor re-ran run_benchmark(): all 9 JSON fields byte-equal to stored artifact (docs/audit/repro/verify_result.json A1); '
      'negative control: tampered one ref row -> verdict_agreement 0.875, exit=3 (A2); '
      'tensor_benchmark_cases rows for anchor KBM-RCI-F1-SPEC = 0 (table has 25 rows / 25 anchors) -> no platform-registered case (finding F2)',
    'repro_cmd',
      'cd /root/tp-agent/work/m15913 && python -m pytest tests/test_wp_line.py tests/test_wp_gate.py -q '
      '&& python -m ke.wp_line bench --json /tmp/bench.json '
      '&& python -m ke.wp_line run --root tests/fixtures/extraction --sources tests/fixtures/extraction/sources '
      '--review-ledger-dir tests/fixtures/extraction/ledgers --tickets-dir tests/fixtures/extraction/tickets '
      '(auditor re-executed 2026-11-12: 72 passed / exit 0 with identical benchmark / exit 2 as designed)',
    'external_anchor',
      'commit 355218c357bfc65734c99caf54ffa4710e61cce7 on branch agent/m15913 (present in /root/tensor-ecosystem/TensorKnowledge, NOT merged into main); '
      'tensor_reports id=15052 (six sections + 1 figure, auditor verified)',
    'live_platform_roundtrip',
      'process 01 asset_registration.json: 5 reports (15044/15045/15047/15048/15050) re-hashed by auditor from live platform markdown -> 5/5 sha256 + length match (verify_result.json A5)',
    'level_basis',
      'L2: 1337-line ke/wp_line.py real implementation + 8-subcommand CLI + JSON run artifacts. '
      'L3: platform dispatch wrapper + reuse of existing ke/wp_gate.run_gates + live platform API consumption (5/5 hash match). '
      'L4: 8 fixture cases + 21 mutation cases against pre-registered labels, predeclared thresholds, 0 inconsistency, independently re-run bit-identical, falsifiable via negative control.',
    'known_gaps', jsonb_build_array(
      'F1 branch not merged into main -> maturity_gate callers_verified() cannot see the caller (expected machine gate_level=2, not a delivery defect)',
      'F2 no tensor_benchmark_cases row for anchor KBM-RCI-F1-SPEC (0 rows)',
      'F3 offline wp_line_artifacts.py run exits 0 while writing n_reachable=0/n_unreachable=5 asset registration, no mode stamp',
      'F4 reference labels and gate share the same project lineage; independence rests on commit ordering (a1c0c76 < 355218c) + mutation matrix + auditor negative control',
      'F5 fixture root holds only 03 packages (0 packages for 01/02/04/05); DAG blocking for 04/05 proven by unit tests with synthetic packages, not end-to-end',
      'F6 rule_coverage denominator parsed from wp_gate.py source (self-referential metric)',
      'not_run: 10k-report throughput/parallel scheduling, process-01 attachment extraction, K5/K6 skill registry wiring, GitHub CI x86 vs loong64'
    ),
    'audit_artifacts', jsonb_build_array(
      'docs/audit/m15922-KBM-RCI-F1-SPEC-audit.md',
      'docs/audit/verify_m15913.py',
      'docs/audit/repro/verify_result.json'
    )
  ),
  'board-audit'
)
ON CONFLICT (repo, scope, verdict_by) DO UPDATE
  SET mission_id = EXCLUDED.mission_id,
      level = EXCLUDED.level,
      evidence = EXCLUDED.evidence,
      gate_state = 'pending',
      gate_level = NULL,
      gate_note = NULL;