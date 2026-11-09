# Claim 11: Three Distribution Function Sets (h1, h2, g)

**claim_id**: CUDAPF-011
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
The solver maintains three sets of distribution functions on the GPU: h1 (phase-field for component 1), h2 (phase-field for component 2), and g (hydrodynamic pressure/population). The h-distributions evolve the phase fields via a Cahn-Hilliard-type collision, while the g-distribution evolves the hydrodynamics via a Navier-Stokes-type collision with phase-field forcing.

## Evidence
**Source**: `src/device_var.f90` (lines 30-35)
```fortran
real(fp_kind),device, dimension(0:nxd+1,0:nyd+1,0:8) :: h1
real(fp_kind),device, dimension(0:nxd+1,0:nyd+1,0:8) :: h2
real(fp_kind),device, dimension(0:nxd+1,0:nyd+1,0:8) :: g
```

**Source**: `src/main.f90` (kernel call sequence, lines 35-45)
```fortran
call collision_h<<<grid,tblock>>>
call collision_g1<<<grid,tblock>>>
call collision_g2<<<grid,tblock>>>
call periodic_f<<<grid,tblock>>>
call propagation_gather<<<grid,tblock>>>
call propagation_scatter<<<grid,tblock>>>
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/device_var.f90`, `src/main.f90`

## Notes
Each distribution function array has dimensions (0:nxd+1, 0:nyd+1, 0:8), i.e., the full domain with halo cells and 9 velocity directions. For nx=ny=254, this is 256×256×9 ≈ 590K elements per distribution set. With double precision, each set uses ~4.7 MB. The total device memory footprint is significant due to the many intermediate arrays.
