# MF-LBM OSS Knowledge

**Source**: [lanl/MF-LBM](https://github.com/lanl/MF-LBM) @ `11be324a97fe6331b2271102da370460715355e8`
**License**: BSD-3-Clause (Triad National Security, LLC / LANL)
**Language**: Fortran 90
**Parallel Model**: MPI-OpenACC/OpenMP hybrid

## Overview

MF-LBM is a high-performance lattice Boltzmann code for direct numerical simulation (DNS) of flow in porous media, primarily developed by Dr. Yu Chen at Los Alamos National Laboratory. It implements a color-gradient multiphase model with Continuum-Surface-Force (CSF) and geometrical wetting models.

## Claims Summary (10 claims)

| ID | Statement | Epistemic Status |
|---|---|---|
| `tkc:oss-lbm:mflbm-csf-multiphase` | CSF + geometrical wetting multiphase model for scCO2-brine DNS | established |
| `tkc:oss-lbm:mflbm-aa-streaming` | AA pattern pull streaming for memory efficiency | established |
| `tkc:oss-lbm:mflbm-mpi-openacc-hybrid` | MPI-OpenACC/OpenMP hybrid for cross-platform portability | established |
| `tkc:oss-lbm:mflbm-comm-compute-overlap` | Async OpenACC + MPI_Isend/Irecv communication-computation overlap | established |
| `tkc:oss-lbm:mflbm-soa-layout` | Structure of Arrays layout for coalesced GPU memory access | established |
| `tkc:oss-lbm:mflbm-mrt-collision` | MRT collision in moment space with 19 moments | established |
| `tkc:oss-lbm:mflbm-domain-decomposition` | Y/Z-only MPI decomposition with face+edge+corner halos | established |
| `tkc:oss-lbm:mflbm-contact-angle-akail` | Akai et al. (2018) contact angle scheme for arbitrary angles | established |
| `tkc:oss-lbm:mflbm-checkpoint-restart` | Checkpoint/restart via job_status.txt and binary files | established |
| `tkc:oss-lbm:mflbm-bsd3-license` | BSD-3-Clause license by LANL | established |

## GAP Anchors

All claims are anchored to **GAP-LBM-HPC-SCALING** (HPC scaling patterns reusable under BSD-3).

## TensorLBM Service Notes

Each claim includes a `notes` field with specific TensorLBM improvement suggestions.
