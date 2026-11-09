# Claim 07: Periodic Boundary Conditions on All Edges

**claim_id**: CUDAPF-007
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
The solver applies periodic boundary conditions on all four edges of the 2D computational domain. This is implemented by copying halo cells from opposite boundaries for all distribution functions (h1, h2, g) and phase fields (phi1, phi2, phi3).

## Evidence
**Source**: `src/global_subroutines.f90` (periodic_phi kernel, lines ~48-65)
```fortran
!-- bottom and top boundaries
    phi1(x,0) = phi1(x,nyd)  
    phi1(x,nyd+1) = phi1(x,1)
!-- left and right boundaries
    phi1(0,y) = phi1(nxd,y)   
    phi1(nxd+1,y) = phi1(1,y)
```

**Source**: `src/global_subroutines.f90` (periodic_f kernel, lines ~700+)
```fortran
!-- left and right boundaries
g(0,y,0)=g(nxd,y,0) 
g(nxd+1,y,0)=g(1,y,0) 
!-- bottom and top boundaries
g(x,0,0) = g(x,nyd,0) 
g(x,nyd+1,0) = g(x,1,0)
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/global_subroutines.f90`

## Notes
The periodic boundary is applied to all three distribution function sets (h1, h2, g) and all three phase fields. The domain size is nx=254, ny=254 with halo cells at indices 0 and nxd+1/nyd+1. No solid wall or inlet/outlet boundary conditions are implemented in the base code (is_solid_node is initialized to all zeros).
