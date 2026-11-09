# Claim 03: D2Q9 Lattice with Standard Weights

**claim_id**: CUDAPF-003
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
The solver uses the standard D2Q9 lattice Boltzmann velocity set with isotropic weights [16,4,4,4,4,1,1,1,1]/36. The discrete velocities are ex = [0,1,0,-1,0,1,-1,-1,1] and ey = [0,0,1,0,-1,1,1,-1,-1].

## Evidence
**Source**: `src/device_var.f90` (lines ~15-18)
```fortran
integer, constant, parameter :: ex(0:8) = [0, 1, 0,-1, 0, 1,-1,-1, 1]
integer, constant, parameter :: ey(0:8) = [0, 0, 1, 0,-1, 1, 1,-1,-1]
real(fp_kind), constant, parameter :: wa(0:8) = [16,4, 4, 4, 4, 1, 1, 1, 1] / 36._fp_kind
```

**Source**: `src/host_var.f90` (lines ~12-14)
```fortran
integer,parameter :: exhost(0:8) = [0, 1, 0,-1, 0, 1,-1,-1, 1]
integer,parameter :: eyhost(0:8) = [0, 0, 1, 0,-1, 1, 1,-1,-1]
real(fp_kind),parameter :: wahost(0:8) = [16,4, 4, 4, 4, 1, 1, 1, 1] / 36._fp_kind
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/device_var.f90`, `src/host_var.f90`

## Notes
The D2Q9 lattice is the standard 2D nine-velocity model. The weights sum to 1: (16+4*4+4*1)/36 = 36/36 = 1. The lattice speed of sound is cs = 1/sqrt(3) in lattice units.
