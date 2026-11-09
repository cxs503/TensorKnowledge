# Claim 06: Phase-Dependent Relaxation Time via Heaviside Function

**claim_id**: CUDAPF-006
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
The hydrodynamic relaxation time tauu is spatially varying and depends on the local phase composition via Heaviside step functions. This allows each phase to have its own viscosity (relaxation time): tau1 for phase 1, tau2 for phase 2, tau3 for phase 3.

## Evidence
**Source**: `src/global_subroutines.f90` (hydro_cal kernel, lines ~355-358)
```fortran
heav1(x,y) = 0.5_fp_kind + sign(0.5_fp_kind,phi1(x,y))
heav2(x,y) = 0.5_fp_kind + sign(0.5_fp_kind,phi2(x,y))
tauu(x,y) = (tau1 - tau3) * heav1(x,y) + (tau2 - tau3) * heav2(x,y) + tau3
```

**Source**: `src/device_var.f90` (default tau values, lines ~27-29)
```fortran
real(fp_kind),parameter :: tau1  = 0.9_fp_kind
real(fp_kind),parameter :: tau2  = 0.9_fp_kind
real(fp_kind),parameter :: tau3  = 0.9_fp_kind
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/global_subroutines.f90`, `src/device_var.f90`

## Notes
The Heaviside function `0.5 + sign(0.5, phi)` returns 1 when phi > 0 and 0 when phi <= 0. This creates a sharp transition between phases. When all three taus are equal (default 0.9), the mixture has uniform viscosity. The kinematic viscosity in lattice units is nu = (tau - 0.5) * cs^2 = (tau - 0.5)/3.
