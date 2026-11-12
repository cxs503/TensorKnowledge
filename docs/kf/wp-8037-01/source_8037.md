# DEM Contact Mechanics Dual Verification (P27W3-N06)

## Results
| Criterion | Key Metric | Error | Pass |
|-----------|-----------|-------|------|
| C1 | Tangential force deviation | 0% (exact) | ✅ |
| C2 | Rolling torque | <1e-10% | ✅ |
| C3 | Damping fit R² | >0.999 | ✅ |
| C4 | Sphere R_eff | 0% (exact) | ✅ |
| C5 | Surface error monotone | Yes | ✅ |
| C6 | Dissipation finite | Yes | ✅ |
| C7 | Repose monotone | Yes | ✅ |
| C8 | Verdict JSON | Generated | ✅ |
| C9 | Tests passing | 32/32 | ✅ |

## Key Findings
- Cundall-Strack tangential spring is exact (machine precision)
- EPSD rolling spring converges to analytic limit M_r = μ_r·F_n·R_eff
- Rotational damping follows exponential decay with R² > 0.999
- Hertz contact for sphere-plane is exact at the sphere limit
- Clump surface error decreases monotonically with sphere count
- Shape verdict: clump acceptable for n₁ ≤ 4 with N ≥ 32 spheres

## Files
- Module: src/tensordem/dem_contact_verification.py
- Tests: tests/test_dem_contact_mechanics_verification.py (32 tests)
- Full report: docs/dem_contact_mechanics_verification_report.md
- Verdict: artifacts/dem/shape_representation_verdict.json
- Figures: artifacts/dem/figures/c1_*.png through c5_*.png
