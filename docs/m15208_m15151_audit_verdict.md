# Maturity Gate Verdict: m15151 KPI-KB-10K

**Audited Mission**: m15151 (KPI-KB-10K · TensorKnowledge)
**Audit Mission**: m15208 (board-audit)
**Date**: 2026-11-11
**Verdict By**: board-audit

## Level: L3 (系统集成)

### Gate Decision: confirmed（消账）

### Evidence

| Check | Result |
|---|---|
| pytest (tests/test_kb10k.py) | 11/11 PASSED (33.80s) |
| verifier (scripts/kb10k_verify.py --offline) | 10/10 PASS |
| KO count | 10,000 ≥ 10,000 ✅ |
| Four-contract coverage | 100% (10,000/10,000) ✅ |
| Schema validation | 30,000/30,000, 0 failures ✅ |
| Unique IDs | 30,000/30,000 ✅ |
| Quote hash correctness | 10,000/10,000 ✅ |
| Push budget | 31 files, max 0.93 MiB < 4 MiB ✅ |
| Manifest reconciliation | PASS, tiers A=8804 B=850 C=346 ✅ |
| Online reproduction | 9,602 checked, 0 mismatched, 52 unavailable ✅ |
| No collapsed duplicates | 0 ✅ |

### Implementation Files
- `scripts/kb10k_harvest.py` (26,111 bytes) — ecosystem-wide KO extraction
- `scripts/kb10k_verify.py` (10,841 bytes) — 10-check machine裁判
- `ke/contract.py` — KE contract integration (discover)
- `ke/validate.py` — aggregate-aware schema validation

### Run Artifacts
- `knowledge/kb10k/manifest.json`
- `knowledge/kb10k/claims/part-000.json` through `part-009.json`
- `knowledge/kb10k/evidence/part-000.json` through `part-009.json`
- `knowledge/kb10k/provenance/part-000.json` through `part-009.json`
- `docs/kb10k/README.md`
- `docs/kb10k/verification.json`

### Reproduction Command
```bash
cd /root/tp-agent/work/m15151 && python3 scripts/kb10k_verify.py --offline
```

### Limitations (honest)
1. All claims `epistemic_status=provisional`, evidence `assessment_status=unassessed` — no independent review completed
2. Knowledge objects are structural code/documentation claims, not ship-type domain knowledge
3. '≥3型船' requirement not directly addressed (corpus covers 15 software repos, not ship types)
4. `tensor_benchmark_cases` table not accessible — benchmark comparison via internal verifier only
5. C9 online reproduction: 52 source files unavailable (non-fatal)

### Level Rationale
**L3** (not L4): Real input→computation→output pipeline integrated with KE contract, but knowledge objects are structural claims about code (definition/descriptive/methodological), not domain-specific benchmark cases with error analysis against experimental anchors.

### SQL Record
```sql
INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES ('TensorKnowledge', 'm15151 KPI-KB-10K', 15208, 3,
'{"impl_files":["scripts/kb10k_harvest.py","scripts/kb10k_verify.py","ke/contract.py","ke/validate.py"],"tests":"11/11 PASSED","benchmark":"10/10 PASS","knowledge_objects":10000,"four_contract":"100%","repro_cmd":"python3 scripts/kb10k_verify.py --offline"}',
'board-audit');
```

### Report
Published as Report #14320 to tensor/reports API.
