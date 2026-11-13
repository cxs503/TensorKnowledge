-- m15887 board-audit verdict for m15858 (KBM-RCI-S2-SCHEMA)
-- Independent re-verification 2026-11-12: pytest 34 passed; bench re-run PASS (C1 1.0/1.0, C2 1.0/1.0, C3 0.0/0.0);
-- evidence_run re-run gate_level=4 why=[]; DDL gate probe: gate_level=1 confirmed ticket REJECTED by ko_ver_confirmed_shape.
INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES (
 'TensorKnowledge',
 'm15858 KBM-RCI-S2-SCHEMA',
 15887,
 4,
 '{
  "impl_files": [
   "ke/ko_ingest.py:246L (ingest@134, add_ticket@201, promote@219, traceability@234)",
   "ke/ko_v1_api.py:76L (POST /ko/v1/ingest, GET /ko/v1/{id}/traceability, POST /ko/v1/{id}/promote)",
   "scripts/ko_v1.py:225L (8 subcommands: validate/ddl/ingest/ticket/promote/etr/bench/gatecheck)",
   "scripts/ko_v1_evidence_run.py:206L",
   "benchmarks/ko_v1_conformance/cases.py:183L (11 doc + 6 transition + 3 E-TR corpus)",
   "benchmarks/ko_v1_conformance/run_benchmark.py:144L",
   "schemas/knowledge-object-v1.schema.json:354L",
   "schemas/sql/knowledge_object_v1.sql:333L (5 tables + check constraints + triggers)"
  ],
  "entry": "scripts/ko_v1.py (exit codes 0/1 machine-readable; bench/ingest/promote/etr/gatecheck subcommands)",
  "run_artifacts": [
   "docs/rci/m15858/bench.json (criteria C1-C4 ref/got/limit/pass + 20 case rows)",
   "docs/rci/m15858/ingest_run.json (ingest+promote+gate_level_1_ticket_rejected+state_events)",
   "docs/rci/m15858/etr_live.json (E-TR 1.0 before/after promotion)",
   "docs/rci/m15858/ke_api_live_call.json (ASGI live calls)",
   "docs/rci/m15858/gate_selfcheck.json (gate_level=4, why=[])",
   "docs/rci/m15858/pytest_junit.xml (34 tests, 0 failures)"
  ],
  "tests": [
   "tests/test_ko_v1_schema.py (25 tests, incl. real-PostgreSQL DDL constraint cases)",
   "tests/test_ko_v1_ingest.py (9 tests)"
  ],
  "integration_callers": "ke/api.py:440-442 app.include_router(ko_v1_api.router); live ASGI: ingest=201, promote=200, no-token=401, invalid-doc=422; DEFECT: GET /ko/v1/{id}/traceability=500 (shadowed by legacy ke/api.py:293 /ko/{ko_id:path}, reproduced by auditor)",
  "benchmark": "docs/rci/m15858/bench.json: C1_doc_conformance 1.0/1.0 (=1.0), C2_transition 1.0/1.0 (=1.0), C3_etr_abs_err_max 0.0/0.0 (<=1e-4), C4_throughput 594.9 val/s (informational); auditor re-run 2026-11-12 PASS; tensor_benchmark_cases: 0 rows for anchor KBM-RCI-S2-SCHEMA (schema task, ref=spec clause annotation, not physics reference)",
  "repro_cmd": "python3 -m pytest tests/test_ko_v1_schema.py tests/test_ko_v1_ingest.py -q && python3 scripts/ko_v1.py bench && python3 scripts/ko_v1_evidence_run.py (all three re-executed by auditor 2026-11-12: 34 passed / PASS / gate_level=4)",
  "external_anchor": "git commit c0c89b748d4739893b4eac953008e2b13f4c8d20 (branch agent/m15858); tensor_reports id=15002 (6 sections complete)",
  "defects": [
   "GET /ko/v1/{id}/traceability returns 500: legacy route ke/api.py:293 /ko/{ko_id:path} registered before router mount at ke/api.py:442, so the new route is unreachable (auditor reproduced; honestly disclosed in report 15002)",
   "mission result server_quality_audit: gate_valid=false, key_present=false (gate_missing_warning)"
  ],
  "audit_note": "L4 = complete conformance case (20 cases) + error analysis (max abs err 0.0) + reproducibility (repro_cmd re-executed). L3 integration real but one read endpoint broken (disclosed). L3 promotion path enforced by DDL: auditor probe insert gate_level=1 confirmed ticket rejected by ko_ver_confirmed_shape."
 }'::jsonb,
 'board-audit'
)
ON CONFLICT (repo, scope, verdict_by) DO UPDATE SET
  mission_id = EXCLUDED.mission_id,
  level = EXCLUDED.level,
  evidence = EXCLUDED.evidence,
  gate_state = 'pending',
  gate_level = NULL,
  gate_note = NULL;
