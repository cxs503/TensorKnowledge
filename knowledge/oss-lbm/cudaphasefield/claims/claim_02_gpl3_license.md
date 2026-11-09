# Claim 02: GPL-3 License

**claim_id**: CUDAPF-002
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
CudaPhaseField is licensed under the GNU General Public License version 3 (GPL-3). This imposes reference-only boundaries for any derivative or integrated use: the code cannot be incorporated into proprietary/closed-source software without also releasing the derivative work under GPL-3.

## Evidence
**Source**: `LICENSE` (file root)
```
GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007
```

**Source**: `src/main.f90` (header, lines 1-12)
```fortran
!============================== License GPLv3 ===================================
!    CudaPhaseField is three-component flow solver based on th lattice Boltzmann method which runs on the NVIDIA GPU.
!    Copyright (C) 2021 Amin Zar, aminpopjoury@gmail.com
!    This program is free software: you can redistribute it and/or modify
!    it under the terms of the GNU General Public License as published by
!    the Free Software Foundation, either version 3 of the License, or
!    (at your option) any later version.
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `LICENSE`, `src/main.f90`, `src/host_var.f90`, `src/host_subroutines.f90`

## Notes
GPL-3 is a strong copyleft license. Any integration into TensorLBM or other platform components must respect the GPL-3 boundary: the integrated work would need to be GPL-3 compatible, or the CudaPhaseField code must be used only as a reference/inspiration (not copied verbatim).
