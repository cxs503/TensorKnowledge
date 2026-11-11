# SEDIMENT Extraction Report: Mission 7485

**Source Mission**: TensorBEM m7485  
**Task Key**: tk-sediment-m7485  
**Extraction Date**: 2026-11-11  
**Extraction Agent**: agent/m14525  
**Source SHA**: 80ad52a8236030e2343d5a88131bea3190088c09

## Executive Summary

Successfully extracted knowledge sediment package from TensorBEM mission 7485 (KP505 open-water BEM benchmark with honest FAIL result). The extraction produced 8 claims, 15 evidence records, and 8 provenance records, all schema-valid and independently verified.

## Source Mission Context

**Physical Problem**: KP505 is a standard open-water propeller model used to validate panel method (BEM) solvers. Mission 7485 implemented a vortex lattice lifting-surface kernel and performed a sweep over 10 advance ratios J∈[0.1, 1.0], comparing against literature anchor values.

**Geometry**: D=0.25m, Ae/Ao=0.7, Z=4, equal mean pitch, flat plate without camber, chord length inferred from Ae/Ao.

**Result**: Honest FAIL - design point J=0.8 shows |ΔK_T|=29.13% (criterion ≤3%), only 1/10 anchor points inside ±5% η₀ band across full J domain.

## Extracted Knowledge

### Claims (8 total)

1. **kp505-kt-design-j-falsified** (falsification, hypothesis)
   - Statement: Vortex lattice open-water kernel does not achieve |ΔK_T| ≤ 3% at design J=0.8
   - Evidence: K_T=0.09993 vs anchor 0.141, ΔK_T=-29.13% (10× criterion)
   - Status: H1 falsified, verdict=FAIL

2. **kp505-mesh-refinement-not-the-cause** (causal)
   - Statement: Radial GCI 7.14-8.08% wider than 3% band; Richardson extrapolation makes it worse
   - Evidence: Mesh refinement is not the root cause of the 29% gap
   - Implication: Must look elsewhere (geometry, not discretization)

3. **elliptic-wing-lift-vs-lifting-line** (analytic-pin)
   - Statement: Vortex lattice + Kutta-Joukowski on elliptic wing: AR=8 +0.13% (pass), AR=4 -8.8% (fail, attributed to classical formula itself)
   - Evidence: Solver kernel validated on analytic test case before any propeller numbers

4. **line-vortex-kernel-vs-closed-form** (analytic-pin)
   - Statement: Straight vortex segment induction equals closed-form Γ/(2πh) to 1e-6 relative error
   - Evidence: Kernel-level correctness verified independently

5. **viscous-section-drag-required-in-kq** (causal)
   - Statement: Viscous section drag must be included in K_Q, otherwise η₀ overestimated by ~17% (0.670 → 0.784)
   - Evidence: Effect magnitude (~17%) >> 3% criterion band, not a negligible correction

6. **deviation-sign-change-root-cause** (causal)
   - Statement: ΔK_T sign change at J∈(0.5, 0.6) indicates reconstructed geometry bias (no camber, uniform pitch), not random noise
   - Evidence: Systematic sign change pattern = geometric reconstruction gap, not kernel error

7. **unphysical-near-zero-load-gate** (normative)
   - Statement: Near-zero-load point (J=1.0, K_T<0, momentum bound violated) must be reported as-is and marked unphysical, not dropped
   - Evidence: If dropped, C2 failure magnitude would be disguised 32× (786.67% → 24.38%)
   - Reusable principle: Evidence discipline for physical-admissibility gates

8. **modelling-parameters-do-not-explain-gap** (hypothesis, falsified)
   - Statement: Tunable parameters (t/c, rev/s, root-chord, radial spacing) explain <3% each, cannot account for 15-30% gap
   - Evidence: H3 falsified; gap must come from geometry gaps (camber, radial pitch distribution) and radial first-order scheme

### Evidence (15 total)

All evidence records contain:
- Verbatim quotations sliced from `git show <sha>:<path>` (never typed)
- SHA-anchored locators with line numbers
- Content hashes (sha256) for verification
- Relation to claims (supports/refutes/qualifies)

### Provenance (8 total)

Each provenance record documents:
- Source mission (7485) and task key (tk-sediment-m7485)
- Source repo (TensorBEM), branch (agent/m7485), head SHA
- Extraction activity (quotation slicing, number recomputation)
- Agents involved (source mission model + extraction worker)

## Verification Results

### Independent Verification (verify_sediment_m7485.py)

**106/106 checks passed**, including:
- Record counts: 8 claims ≥ 3, 15 evidence, 8 provenance
- Schema validation: all records valid against JSON schemas
- Quotation re-extraction: all 15 quotations re-sliced from git sha, hash matches
- Grep verification: all quotations found at specified line numbers
- Numerical recomputation: all numbers in claims recomputed from points.csv
- INDEX consistency: all 8 claims present in INDEX.md with correct locators
- Review discipline: no review-event records, review_status=draft, not promoted

### Guard Tests (test_sediment_m7485.py)

**3/3 tests passed**:
- test_package_exists: knowledge/sediment/m7485/ directory exists with expected files
- test_package_verifies_against_source_sha: verification script passes
- test_no_review_event_and_draft_status: no review-event records, draft status correct

### Schema Validation (sediment_m7485_extract.py)

**31/31 schema validations passed**:
- 8 claims valid against claim-record.schema.json
- 15 evidence valid against evidence-record.schema.json
- 8 provenance valid against provenance-record.schema.json

## Reproduction

```bash
# Set source repo
export M7485_SRC_REPO=/root/tensor-ecosystem/TensorBEM

# Extract knowledge records
python scripts/sediment_m7485_extract.py

# Verify independently
python scripts/verify_sediment_m7485.py

# Run guard tests
python -m pytest tests/test_sediment_m7485.py -v

# Generate figure
python scripts/sediment_m7485_figure.py

# Regenerate VALIDATION.md
bash scripts/sediment_m7485_validation.sh
```

## Artifacts

### Knowledge Package: knowledge/sediment/m7485/

- 8 claim JSON files (claim-*.json)
- 15 evidence JSON files (evidence-*.json)
- 8 provenance JSON files (provenance-*.json)
- INDEX.md (claim/evidence summary table)
- VALIDATION.md (machine-generated verification log, 212 lines)
- review-status.json (draft, not promoted, no self-review)
- figures/kp505_bem_vs_anchor.png (234980 bytes)

### Run Artifacts: runs/sediment-m7485/

- README.md (documentation)
- repro.sh (reproduction script)
- logs/extract.log (extraction output)
- logs/verify.log (verification output)
- logs/pytest.log (test output)
- logs/figure.log (figure generation output)
- logs/validation.log (validation script output)

## Epistemic Discipline

- **No self-review**: Producer does not self-review; review_status=draft
- **No review-event records**: Empty review-event ledger
- **epistemic_status=provisional**: Schema has no 'draft' value; draft is review-ledger fold result
- **Quotations verbatim**: All sliced from git show, never typed
- **Numbers recomputed**: All derived from committed points.csv
- **Honest FAIL**: Source mission result is FAIL, not disguised or threshold-adjusted

## Report Publication

Report ID 13568 published to tensor/reports API with:
- Title: "SEDIMENT: TensorBEM m7485 KP505 敞水 BEM 知识沉淀（8 claims / 15 evidence / 8 provenance）"
- Six-element paper-quality documentation
- Embedded figure (kp505_bem_vs_anchor.png)
- Full error analysis table

## Conclusions

Successfully extracted reusable negative knowledge from TensorBEM m7485 honest FAIL result:
- 2 falsifications (vortex lattice method fails at design point)
- 3 analytic pinning results (solver kernels validated)
- 2 causal root-cause analyses (geometry reconstruction gaps identified)
- 1 evidence discipline norm (handling unphysical data)

All knowledge records are schema-valid, independently verified, and properly documented with full provenance chain. L2 maturity level achieved.
