# OSS-LBM Knowledge Package

Lattice Boltzmann Method open-source ecosystem knowledge for TensorLBM improvement.

## Scope

17 claims extracted from source-code inspection of four major LBM frameworks:

| Framework | Focus | Commit |
|-----------|-------|--------|
| **pylbm** | Symbolic equivalent equations, von Neumann stability, interpolated bounce-back family | 48c19da |
| **lettuce** | PyTorch-based differentiable LBM, native CUDA code generation, invariant-based testing | a0e3f2d |
| **lbmpy** | Chapman-Enskog analysis, 4-stage kernel generation pipeline, multi-method collision spaces | 0afc9d5 |
| **XLB** | Warp GPU kernels with f₀/f₁ double-buffering, JAX shard_map distributed parallelism, Operator pattern | 9c23e82 |

## Structure

```
oss-lbm/
├── README.md
├── claims/claims.json          # 17 claim records (schema: claim-record.schema.json)
├── evidence/evidence.json      # 17 evidence records (schema: evidence-record.schema.json)
├── provenance/provenance.json  # 1 provenance record (schema: provenance-record.schema.json)
└── validate_oss_lbm.py         # Self-validator
```

## Epistemic Discipline

- All claims are `epistemic_status: established` (code-level descriptive facts verified by direct source inspection)
- All evidence has `assessment_status: unassessed` (no self-approval)
- All evidence uses `locator_type: code-location` with `repo@commit file:line` and verbatim quotes
- No review events (review_status = draft by convention)
- Each claim's `notes` field contains one sentence on how it can serve TensorLBM improvements

## Validation

```bash
python validate_oss_lbm.py
```

Checks:
1. Schema conformance (Draft 2020-12)
2. Cross-reference integrity (claim↔evidence bidirectional)
3. Count constraints (≥15 claims)
4. Provenance linkage

## Service to TensorLBM

Each claim's `notes` field identifies a concrete TensorLBM improvement point:
- Precision analysis (equivalent equations, Chapman-Enskog)
- Performance (GPU kernel patterns, multi-backend architecture)
- Testing (invariant-based tests, parametric fixtures, kernel-type organization)
- Boundary accuracy (interpolated bounce-back family)
- Differentiability (PyTorch autograd-compatible collision operators)
- Scalability (JAX shard_map distributed parallelism)
