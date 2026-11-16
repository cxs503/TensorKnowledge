-- PROD-RA R7 terminal review verdict (m24007). Independent third-party close-out.
-- Verdict: changes_requested (blocking). R6 self-report (all_six_pass=True, R5-1/2/3 closed)
-- is FALSE for the committed state: the fix's verification (status_after.json) was generated
-- on the unmerged agent/m23814 branch (543881ac); main@53959af still carries the R5-1/2/3
-- residuals verbatim (82/139 locators resolve cold, 51 legacy runs/ prefix, 6 absolute foreign,
-- manifest sound=False with 4 raw files missing, D6 ev-kb10k-incompatibility still lacks
-- input_sha256 with 3 absolute foreign input_refs and 0/5 source_ref resolving cold).
--
-- NOTE: this role has no INSERT/SELECT on tensor_maturity_verdicts (permission denied, same as
-- R5/R6). This file is the in-repo verdict record; the coordinator with write access applies it.

INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, gate_state, verdict_by, evidence)
VALUES (
  'TensorKnowledge',
  'ra-rereview7-m22059-fixes',
  24007,
  2,
  'changes_requested',
  'm24007-r7-independent',
  '{"verdict":"changes_requested","scenario_validated":false,
    "reviewed_head":"53959aff766167da7bd5b8aec849d37e06974bdd",
    "r6_merge":"53b5154be85f2fccd1ff37eef9dcb922aa96478b",
    "r6_claimed_after_head":"543881ac789fd1623cd4d47771dd1eb8fd62b9a6 (NOT in main)",
    "frozen_verifier":"docs/m23257/verify_status.py (unchanged)",
    "residuals":[
      {"id":"R5-1","severity":"blocking","status":"NOT_CLOSED",
       "evidence":{"pure_path_fields":139,"resolved_cold":82,"legacy_runs_prefix":51,
                   "absolute_foreign":6,"unresolvable_after_repair":2}},
      {"id":"R5-2","severity":"major","status":"NOT_CLOSED",
       "evidence":{"manifest_sound":false,"missing":["raw/adjacent_unit_tests.log",
                   "raw/evidence_schema_validation.log","raw/pytest_collect_base.log",
                   "raw/pytest_collect_reviewed.log"]}},
      {"id":"R5-3","severity":"major","status":"NOT_CLOSED",
       "evidence":{"items_without_input_sha256":["ev-kb10k-incompatibility"],
                   "items_with_absolute_foreign_input_refs":["ev-claim-evidence-audit",
                   "ev-negative-claim-evidence","ev-kb10k-incompatibility"],
                   "source_ref_resolve_cold":0,"sha256_matches":0}}
    ],
    "root_cause":"R6 fix ran on agent/m23814 branch (543881ac/d6cceb3f, never merged); "
                "Merge #525 only shipped docs/m23814 report + partial docs/review_m22059_prod_ra "
                "changes, NOT the docs/m22059/ locator/D6/raw repairs. Verification evidence "
                "disconnected from committed state.",
    "checks_not_run":["tensor_maturity_verdicts direct write (role lacks permission)",
                      "full pytest suite in cold clone","cross-machine rerun"],
    "review_report":"docs/m24007/TERMINAL_REVIEW.md"}'
)
ON CONFLICT (repo, scope, verdict_by) DO UPDATE SET
  mission_id=EXCLUDED.mission_id, level=EXCLUDED.level, gate_state=EXCLUDED.gate_state,
  evidence=EXCLUDED.evidence, created_at=now()
RETURNING id, level, gate_state;
