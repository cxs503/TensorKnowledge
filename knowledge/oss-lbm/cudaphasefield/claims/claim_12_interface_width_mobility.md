# Claim 12: Interface Width w=4 and Mobility m=0.01

**claim_id**: CUDAPF-012
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
The default interface width parameter is w=4 lattice units and the mobility parameter is m=0.01. The interface width controls the thickness of the diffuse interface between phases, and the mobility controls the rate of phase-field evolution (Cahn-Hilliard dynamics).

## Evidence
**Source**: `src/device_var.f90` (lines 12-13)
```fortran
real(fp_kind),constant, parameter :: w = 4._fp_kind
real(fp_kind),constant, parameter :: m = 0.01_fp_kind
real(fp_kind),constant, parameter :: w_c = 1._fp_kind/(0.5_fp_kind + 3._fp_kind*m)
```

**Source**: `src/global_subroutines.f90` (collision_h kernel, lines ~490-495)
```fortran
h1(x,y,0) = h1(x,y,0) * (1._fp_kind-w_c) + heq10(x,y) * w_c + hlph10(x,y)
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/device_var.f90`, `src/global_subroutines.f90`

## Notes
The relaxation parameter w_c = 1/(0.5 + 3*m) = 1/(0.5 + 0.03) = 1/0.53 ≈ 1.887 for m=0.01. This is the relaxation rate for the phase-field distribution functions. The interface width w=4 means the diffuse interface spans approximately 4 lattice units, which is a common choice balancing accuracy and computational cost. The mobility m=0.01 controls the timescale of interface evolution relative to hydrodynamics.
