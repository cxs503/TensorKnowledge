# Claim 05: Shared-Memory Tiled Gradient and Laplacian Computation

**claim_id**: CUDAPF-005
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
The gradient and Laplacian computations use shared-memory tiling with 32×32 thread blocks. Each tile is padded with a 1-cell halo ring on all sides (indices 0 and TILE+1) to enable 8-neighbor stencil reads entirely from shared memory without additional global memory traffic.

## Evidence
**Source**: `src/global_subroutines.f90` (gradient_cal kernel, lines ~70-80)
```fortran
integer, parameter :: TILE = 32
real(fp_kind), shared :: s_phi1(0:TILE+1, 0:TILE+1)
real(fp_kind), shared :: s_phi2(0:TILE+1, 0:TILE+1)
real(fp_kind), shared :: s_phi3(0:TILE+1, 0:TILE+1)
```

**Source**: `src/global_subroutines.f90` (gradient stencil, lines ~120-125)
```fortran
dphi1dx(x,y) = (s_phi1(tx+1,ty) - s_phi1(tx-1,ty))/3._fp_kind + &
    (s_phi1(tx+1,ty-1) + s_phi1(tx+1,ty+1) - s_phi1(tx-1,ty-1) - s_phi1(tx-1,ty+1))/12._fp_kind
```

**Source**: `src/global_subroutines.f90` (Laplacian stencil, lines ~318-322)
```fortran
d2phi1(x,y) = (s_phi1(tx-1,ty-1)+s_phi1(tx+1,ty-1)+s_phi1(tx-1,ty+1)+s_phi1(tx+1,ty+1) &
    +4._fp_kind*(s_phi1(tx,ty-1)+s_phi1(tx-1,ty)+s_phi1(tx+1,ty)+s_phi1(tx,ty+1)) - 20._fp_kind*s_phi1(tx,ty))/6._fp_kind
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/global_subroutines.f90`

## Notes
The gradient uses an isotropic finite-difference scheme (central difference for axis-aligned neighbors, diagonal correction). The Laplacian uses a 9-point stencil with weights [1,4,1,4,-20,4,1,4,1]/6, which is a higher-order approximation than the standard 5-point stencil.
