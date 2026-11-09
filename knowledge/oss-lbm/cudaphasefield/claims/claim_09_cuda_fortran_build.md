# Claim 09: CUDA Fortran Build with nvfortran and maxregcount Fix

**claim_id**: CUDAPF-009
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
The solver is built using NVIDIA's nvfortran compiler with CUDA Fortran support (-cuda flag). The Makefile includes a permanent fix for a register-overshoot bug in the collision_h kernel by limiting max register count to 64 (maxregcount:64).

## Evidence
**Source**: `Makefile` (lines 3-5, 40-42)
```makefile
cc := nvfortran
# -cuda enables CUDA Fortran (this nvfortran version has retired -Mcuda in favor
# of -cuda + -gpu=...).
```

```makefile
# maxregcount:64 is not a diagnostic flag -- it's the permanent fix for the
# collision_h register-overshoot bug documented above, and applies to every
# build mode so no kernel can silently fail to launch regardless of BUILD.
cudaflags := -cuda -gpu=$(gpu_target),maxregcount:64$(gpu_extra) $(optflags) -module $(objdir)
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `Makefile`

## Notes
The maxregcount:64 fix indicates the collision_h kernel was previously exceeding the GPU's register limit, causing silent launch failures. This is a known issue in CUDA Fortran when kernels have many local variables. The build supports both release (-O3 -fast) and debug (-O0 -g -Mbounds -Mchkptr) modes.
