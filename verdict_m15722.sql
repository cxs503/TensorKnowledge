-- Verdict for m15722 KBM-TKC-INDEX-API (audited by m15907)
INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES (
  'TensorKnowledge',
  'm15722 KBM-TKC-INDEX-API',
  15907,
  4,
  '{"impl_files":["ke/facets.py:208 lines","ke/api.py:604 lines","ke/apistore.py:1187 lines","ke/worker_probe.py:205 lines","scripts/tk_agent_cases.py:683 lines"],"entry":"scripts/tk_agent_cases.py --quick","run_artifacts":["artifacts/tk-agent-cases/case-a-taylor-green.json (rel_error 0.147%)","artifacts/tk-agent-cases/case-b-provenance.json (0 dangling, 0 asymmetric)","artifacts/tk-agent-cases/case-c-exactness-scope.json (worst L2 1.26e-13)","3 PNG figures"],"tests":["tests/test_ke_index.py: 12/12 PASS","tests/test_ke_api.py: 25/25 PASS","tests/test_kb_consume.py: 14/14 PASS"],"benchmark":{"case_A":"Taylor-Green rel_error 0.147% < 3%","case_B":"0 dangling, 0 asymmetric, quote_coverage 98.98%","case_C":"worst L2 1.26e-13 < 3%","kpi_kb_reuse_rate":0.667},"repro_cmd":"cd /root/tp-agent/work/m15722 && python scripts/tk_agent_cases.py --quick","external_anchor":"commit c1f51b41d473b1abbbe84f73986621612d1b3618"}',
  'board-audit'
);
