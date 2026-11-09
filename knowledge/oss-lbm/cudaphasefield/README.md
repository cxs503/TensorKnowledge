# CudaPhaseField OSS Knowledge

**Repository**: [AminZar69/CudaPhaseField](https://github.com/AminZar69/CudaPhaseField)
**License**: GPL-3
**Last analyzed commit**: d6181e677c413bbec443570010bca60d896022b5
**Analysis date**: 2026-11-09

## Summary
CudaPhaseField is a three-component (three-phase) lattice Boltzmann phase-field solver implemented in CUDA Fortran for NVIDIA GPUs. It solves the coupled Cahn-Hilliard/Navier-Stokes system for three immiscible fluids using a phase-field approach with D2Q9 lattice.

## Claims Index

| ID | Title | Status | GAP Anchor |
|---|---|---|---|
| CUDAPF-001 | Three-Component Phase-Field LBM Solver | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-002 | GPL-3 License | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-003 | D2Q9 Lattice with Standard Weights | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-004 | Cahn-Hilliard Chemical Potential with Three-Component Coupling | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-005 | Shared-Memory Tiled Gradient and Laplacian Computation | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-006 | Phase-Dependent Relaxation Time via Heaviside Function | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-007 | Periodic Boundary Conditions on All Edges | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-008 | Double Precision Default with Single-Precision Warning | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-009 | CUDA Fortran Build with nvfortran and maxregcount Fix | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-010 | VTK RectilinearGrid Output Format | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-011 | Three Distribution Function Sets (h1, h2, g) | established | GAP-LBM-PHASEFIELD-3PH |
| CUDAPF-012 | Interface Width w=4 and Mobility m=0.01 | established | GAP-LBM-PHASEFIELD-3PH |

## Key Parameters (Default)

| Parameter | Value | Description |
|---|---|---|
| nx, ny | 254 | Grid size (interior) |
| w | 4.0 | Interface width (lattice units) |
| m | 0.01 | Mobility |
| tau1, tau2, tau3 | 0.9 | Phase relaxation times |
| sigma(i,j) | 0.1 | Pairwise surface tension matrix |
| density | [1000, 500, 100] | Phase densities |
| tf | 1,500,000 | Total timesteps |
| step | 8,000 | Output interval |

## Publications
- Zarareh et al. (2021), "Improving the staircase approximation for wettability implementation of phase-field model: Part 1–Static contact angle", Computers & Mathematics with Applications, 98, 218-238.
- Zarareh et al. (2022), "Improving the staircase approximation for wettability implementation of phase-field model: Part 2–Three-component permeation", Computers & Mathematics with Applications, 109, 100-124.
- Zarareh, A. (2024), PhD thesis, Heriot-Watt University.
