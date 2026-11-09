# Provenance: CudaPhaseField Analysis

## Source Repository
- **URL**: https://github.com/AminZar69/CudaPhaseField
- **Commit**: d6181e677c413bbec443570010bca60d896022b5
- **Branch**: main
- **Clone date**: 2026-11-09
- **Clone method**: `git clone --depth=1`

## File Manifest
| File | Lines | Description |
|---|---|---|
| src/main.f90 | 97 | Main program entry, kernel launch sequence |
| src/device_var.f90 | 106 | Device-side variable declarations |
| src/host_var.f90 | 63 | Host-side variable declarations |
| src/global_subroutines.f90 | 1245 | CUDA kernels (phi_cal, gradient_cal, chemical_potential, hydro_cal, collision_h, collision_g1, collision_g2, periodic_*, propagation_*) |
| src/host_subroutines.f90 | 652 | Host-side initialization, equilibrium, output |
| src/precision_m.f90 | 7 | Precision kind definitions |
| Makefile | ~70 | Build system (nvfortran, CUDA Fortran) |
| LICENSE | ~674 | GPL-3 license text |
| README.md | ~200 | Documentation, usage, citations |

## Analysis Method
- Direct source code reading of all .f90 files and Makefile
- Line-number-verified evidence extraction
- Cross-referenced between host and device variable declarations
- Kernel call sequence traced from main.f90

## Integrity
- All claims include verbatim source quotes with file:line references
- No claims based on inference without source evidence
- GPL-3 license boundary explicitly noted
