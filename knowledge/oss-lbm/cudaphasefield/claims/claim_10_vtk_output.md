# Claim 10: VTK RectilinearGrid Output Format

**claim_id**: CUDAPF-010
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
Simulation results are output as VTK RectilinearGrid files (.vtr) in ASCII format at intervals defined by the `step` parameter (default 8000 timesteps). Output includes Density, phi1, phi2, phi3, ux, uy, and pressure fields.

## Evidence
**Source**: `src/host_subroutines.f90` (results_output_host, lines ~430-470)
```fortran
write (1,'(A)') '<VTKFile type="RectilinearGrid" version="0.1" byte_order="LittleEndian">'
write (1,*) '<RectilinearGrid WholeExtent="1 ',Nx,' 1 ',Ny,' 1 ','1','">'
write (1,*) '<Piece Extent="1 ',Nx,' 1 ',Ny,' 1 ','1',' ">'
```

```fortran
write (1,'(A)') '<DataArray type="Float32" Name="Density" NumberOfComponents="1" format="ascii">'
write (1,'(A)') '<DataArray type="Float32" Name="phi1" NumberOfComponents="1" format="ascii">'
```

**Source**: `src/host_var.f90` (lines 8-9)
```fortran
integer,parameter :: tf   = 1500000
integer,parameter :: step = 8000
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/host_subroutines.f90`, `src/host_var.f90`

## Notes
The total simulation runs for 1,500,000 timesteps with output every 8,000 steps, producing 187 output files. The VTK files use Float32 (single precision) for output regardless of the computation precision (fp_kind). Console output prints monitoring data every 1,000 steps including phi3_min, phi3_max, velocity maxima, and total mass.
