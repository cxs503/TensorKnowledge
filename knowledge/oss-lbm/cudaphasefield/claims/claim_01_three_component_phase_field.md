# Claim 01: Three-Component Phase-Field LBM Solver

**claim_id**: CUDAPF-001
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
CudaPhaseField implements a three-component (three-phase) lattice Boltzmann phase-field solver on NVIDIA GPUs using CUDA Fortran. The three phase fields satisfy the constraint phi1 + phi2 + phi3 = 1, with phi3 computed implicitly as `phi3 = 1 - phi1 - phi2`.

## Evidence
**Source**: `src/global_subroutines.f90` (lines ~30-45 in `phi_cal` kernel)
```fortran
phi1(x,y)= h1(x,y,0) + h1(x,y,1) + h1(x,y,2) + h1(x,y,3) + h1(x,y,4) + h1(x,y,5)+ h1(x,y,6)+ h1(x,y,7)+ h1(x,y,8)
phi2(x,y)= h2(x,y,0) + h2(x,y,1) + h2(x,y,2) + h2(x,y,3) + h2(x,y,4) + h2(x,y,5)+ h2(x,y,6)+ h2(x,y,7)+ h2(x,y,8)
phi3(x,y) = 1._fp_kind - phi1(x,y) - phi2(x,y)
```

**Source**: `src/main.f90` (header comment)
```fortran
!    CudaPhaseField is three-component flow solver based on th lattice Boltzmann method which runs on the NVIDIA GPU.
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/global_subroutines.f90`, `src/main.f90`

## Notes
The solver tracks only two independent phase-field distribution functions (h1, h2) on the device; the third phase is derived from the sum constraint. This is a standard approach for N-phase phase-field models to reduce memory and computational cost.
