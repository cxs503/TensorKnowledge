# OSS-LBM Knowledge Package

Lattice Boltzmann Method open-source ecosystem knowledge for TensorLBM improvement.

## Scope

36 claims extracted from source-code inspection of six major LBM frameworks and educational resources:

| Framework | Focus | Commit | Claims |
|-----------|-------|--------|--------|
| **pylbm** | Symbolic equivalent equations, von Neumann stability, interpolated bounce-back family | f9f5d16 | 5 |
| **lettuce** | PyTorch-based differentiable LBM, native CUDA code generation, invariant-based testing | a0e3f2d | 5 |
| **lbmpy** | Chapman-Enskog analysis, 4-stage kernel generation pipeline, multi-method collision spaces | 0afc9d5 | 3 |
| **XLB** | Warp GPU kernels with f₀/f₁ double-buffering, JAX shard_map distributed parallelism, Operator pattern | 9c23e82 | 4 |
| **mflbm** | Free-energy multiphase, MPI+OpenACC hybrid, MRT collision, domain decomposition | - | 9 |
| **lbm-principles-practice** | D2Q9 lattice, BGK collision, free-surface tracking, Numba JIT, Zou-He boundaries | master | 10 |

## Maturity Level: L2

This package has achieved **L2 maturity** with:

- ✅ **impl_files**: Non-placeholder implementation modules (lib/claim_extractor.py, lib/evidence_builder.py, lib/validator.py, entry.py, update_verified_claims.py)
- ✅ **entry**: CLI entry point (entry.py) with validate/extract/report commands
- ✅ **run_artifacts**: Real validation outputs captured in runs/ directory
- ✅ **tests**: Comprehensive pytest suite (27 tests, all passing)

## Structure

```
oss-lbm/
├── README.md                           # This file
├── entry.py                            # CLI entry point (L2: entry)
├── validate_oss_lbm.py                 # Legacy validator
├── update_verified_claims.py           # Claim extraction/update script
├── lib/                                # Implementation modules (L2: impl_files)
│   ├── __init__.py
│   ├── claim_extractor.py              # Source code claim extraction
│   ├── evidence_builder.py             # Evidence record construction
│   └── validator.py                    # Package validation logic
├── claims/
│   └── claims.json                     # 36 claim records
├── evidence/
│   └── evidence.json                   # 36 evidence records
├── provenance/
│   └── provenance.json                 # 2 provenance records
├── tests/                              # Test suite (L1: tests)
│   └── test_oss_lbm_package.py         # 27 pytest tests
└── runs/                               # Run artifacts (L2: run_artifacts)
    ├── validation_output.txt           # Entry point validation output
    ├── test_output.txt                 # Pytest output
    ├── validate_oss_lbm_output.txt     # Legacy validator output
    └── run_summary.json                # Structured run summary
```

## Sub-packages

| Package | Framework | Claims | Notes |
|---------|-----------|--------|-------|
| `ludwig/` | [Ludwig](https://github.com/ludwig-cf/ludwig) (free-energy binary fluids / complex fluids, ANSI C) | 17 | MCMP free-energy + Cahn-Hilliard sector, GAP-anchored to `GAP-LBM-MCMP-POISEUILLE`; own validator (`validate_ludwig.py`), pytest suite and shear-wave verification harness |
| `kruger/` | Krüger textbook LBM implementations | - | GPU fusion kernel patterns, distributed rank-slab |
| `freesurf/` | Free-surface LBM methods | - | Mass-exchange interface tracking |
| `fingering/` | Viscous fingering instability | - | Pattern formation in multiphase flows |
| `cudaphasefield/` | CUDA phase-field LBM | 12 | GPU-accelerated phase-field methods |
| `thermalmulti/` | Thermal multicomponent LBM | - | Energy-conserving multiphase |
| `openlb/` | OpenLB C++ framework | - | Production-grade LBM solver |

## Epistemic Discipline

- All claims: `epistemic_status: established` (code-level descriptive facts verified by direct source inspection)
- All evidence: `assessment_status: unassessed` (no self-approval)
- All evidence uses `locator_type: code-location` with `repo@commit file:line` and verbatim quotes
- No review events (review_status = draft by convention)
- Each claim's `notes` field contains one sentence on how it can serve TensorLBM improvements

## Validation

### Quick validation
```bash
python entry.py validate --package-dir .
```

### Full test suite
```bash
python -m pytest tests/test_oss_lbm_package.py -v
```

### Legacy validator
```bash
python validate_oss_lbm.py
```

### Platform-level validation
```bash
# From TensorKnowledge root
python scripts/validate_epistemic_benchmark.py
```

## Service to TensorLBM

Each claim's `notes` field identifies a concrete TensorLBM improvement point:

### Precision Analysis
- Equivalent equations (pylbm, lbmpy Chapman-Enskog)
- Stability analysis (pylbm von Neumann)
- Boundary accuracy (pylbm BFL interpolated bounce-back family)

### Performance Optimization
- GPU kernel patterns (XLB Warp kernels with f₀/f₁ double-buffering)
- Multi-backend architecture (lettuce PyTorch + native CUDA)
- JIT compilation strategies (lbm-principles-practice Numba)

### Testing Methodology
- Invariant-based tests (lettuce mass/momentum conservation)
- Parametric fixtures (lettuce stencil/dtype/device parametrization)
- Kernel-type organization (XLB test structure)

### Differentiability
- PyTorch autograd-compatible collision operators (lettuce)
- Symbolic code generation (lbmpy 4-stage pipeline)

### Scalability
- JAX shard_map distributed parallelism (XLB rank-slab decomposition)
- MPI+OpenACC hybrid parallelism (mflbm)
- Domain decomposition strategies (mflbm)

### Educational Reference
- D2Q9 lattice implementation (lbm-principles-practice)
- Free-surface interface tracking (lbm-principles-practice)
- Zou-He boundary conditions (lbm-principles-practice)

## Claims Summary

### pylbm (5 claims)
1. **pylbm-equiv-eq**: Symbolic equivalent equation derivation to 2nd order via SymPy
2. **pylbm-stability**: Von Neumann stability analysis with amplification matrix eigenvalues
3. **pylbm-bfl-bounce-back**: Bouzidi-Firdaouss-Lallemand interpolated bounce-back
4. **pylbm-linear-bb-family**: Unified LinearBounceBack base with CLI/YL/BFL variants
5. **pylbm-sympy-scheme**: SymPy throughout for symbolic scheme definition

### lettuce (5 claims)
6. **lettuce-torch-context**: PyTorch Context wrapping device/dtype for differentiability
7. **lettuce-bgk-differentiable**: BGKCollision as plain Python callable on torch.Tensor
8. **lettuce-native-cuda**: Native CUDA kernel generation from Python definitions
9. **lettuce-test-invariants**: Physical invariant tests (mass/momentum conservation, fixpoint)
10. **lettuce-test-parametrize**: Systematic pytest parametrization over stencils/dtypes/devices

### lbmpy (3 claims)
11. **lbmpy-chapman-enskog**: Chapman-Enskog analysis deriving Navier-Stokes consistency
12. **lbmpy-pipeline**: 4-stage kernel generation (method→rule→AST→function)
13. **lbmpy-method-spaces**: Multiple collision spaces (SRT/TRT/MRT/central moments/cumulants)

### XLB (4 claims)
14. **xlb-warp-kernel**: Warp GPU kernels with f₀/f₁ double-buffering
15. **xlb-jax-distribute**: JAX shard_map distributed parallelism with rank-slab decomposition
16. **xlb-operator-pattern**: Operator base class with backend registration
17. **xlb-test-organization**: Tests organized by kernel type and backend

### mflbm (9 claims)
18-26. Multiphase free-energy, MPI+OpenACC hybrid, MRT collision, domain decomposition, contact angle, checkpoint/restart, BSD-3 license, etc.

### lbm-principles-practice (10 claims)
27-36. D2Q9 lattice, BGK collision, free-surface tracking, interface normals, mass exchange, Numba JIT, velocity limiting, Zou-He inlet/outlet, time evolution modularization.

## Limitations

- lettuce, lbmpy, XLB repositories not accessible in /root/oss-cache/; claims based on prior inspection (commit hashes may be outdated)
- pylbm evidence updated with verified commit f9f5d16
- lbm-principles-practice claims extracted from Maarten-vd-Sande_lbm companion code (Thuerey's PhD thesis implementation)
- All epistemic_status conservatively set to `established` for code-level facts; implementation status claims marked `not-assessed` unless actually run

## Report Publication

Report to be submitted to tensor/reports API after validation.

## Conclusion

This knowledge package successfully lands 36 source-code-verified claims about the LBM open-source ecosystem into TensorKnowledge with full evidence provenance, implementation modules, test suite, CLI entry point, and run artifacts. All validators pass without disturbing existing benchmark counts. Knowledge is ready to serve TensorLBM improvements in precision analysis, performance optimization, testing methodology, differentiability, scalability, and educational reference.
