#!/usr/bin/env python3
"""Append CudaPhaseField claims to the OSS-LBM knowledge JSON files."""

import json
from datetime import datetime, timezone

NOW = "2026-11-09T16:00:00Z"
COMMIT = "d6181e6"
REPO = "AminZar69/CudaPhaseField"
REPO_URL = "https://github.com/AminZar69/CudaPhaseField"

claims = json.load(open("knowledge/oss-lbm/claims/claims.json"))
evidence = json.load(open("knowledge/oss-lbm/evidence/evidence.json"))
provenance = json.load(open("knowledge/oss-lbm/provenance/provenance.json"))

# ---- Claims ----
new_claims = [
    {
        "id": "tkc:oss-lbm:cudaphasefield-three-component",
        "statement": "CudaPhaseField implements a three-component (three-phase) lattice Boltzmann phase-field solver on NVIDIA GPUs using CUDA Fortran. The three phase fields satisfy phi1 + phi2 + phi3 = 1, with phi3 computed implicitly as phi3 = 1 - phi1 - phi2, tracking only two independent distribution function sets (h1, h2).",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["CUDA Fortran", "NVIDIA GPU", "three-phase flow"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-three-component-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: 三相相场约束 phi3=1-phi1-phi2 的隐式实现可作为 TensorLBM 多相流模块的参考设计，减少内存占用。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-gpl3",
        "statement": "CudaPhaseField is licensed under GPL-3, imposing reference-only boundaries for any derivative or integrated use: the code cannot be incorporated into proprietary/closed-source software without also releasing the derivative work under GPL-3.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["GPL-3 license", "reference-only boundary"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-gpl3-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: GPL-3 边界要求任何集成必须保持开源兼容，或仅作为参考/灵感使用而非逐字复制。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-d2q9",
        "statement": "CudaPhaseField uses the standard D2Q9 lattice with velocities ex=[0,1,0,-1,0,1,-1,-1,1], ey=[0,0,1,0,-1,1,1,-1,-1] and isotropic weights [16,4,4,4,4,1,1,1,1]/36.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["D2Q9 lattice", "2D simulation"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-d2q9-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: D2Q9 标准权重和速度集可直接用于 TensorLBM 的 2D 多相流验证算例。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-cahn-hilliard",
        "statement": "The chemical potential follows a three-component Cahn-Hilliard form with pairwise interfacial energy parameters lambda(i) derived from surface tension matrix sigma(3,3), and a three-phase coupling term lambdat = 3/(1/lambda1 + 1/lambda2 + 1/lambda3). The double-well potential is phi*(1-phi)*(1-2*phi) with gradient energy term -(3/4)*w*lambda*Laplacian(phi).",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["three-component Cahn-Hilliard", "phase-field model"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-cahn-hilliard-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: 三相 Cahn-Hilliard 化学势公式（含 lambdat 耦合项）可作为 TensorLBM 相场模型的参考实现。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-shared-memory",
        "statement": "Gradient and Laplacian computations use shared-memory tiling with 32x32 thread blocks, padded with 1-cell halo ring for 8-neighbor stencil reads. The Laplacian uses a 9-point stencil with weights [1,4,1,4,-20,4,1,4,1]/6.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["CUDA shared memory", "32x32 tile", "higher-order Laplacian"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-shared-memory-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: 共享内存分块策略和 9 点 Laplacian 模板可直接用于 TensorLBM CUDA 内核优化。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-phase-relaxation",
        "statement": "The hydrodynamic relaxation time tauu is spatially varying via Heaviside functions: tauu = (tau1-tau3)*H(phi1) + (tau2-tau3)*H(phi2) + tau3, where H(phi) = 0.5 + sign(0.5, phi), allowing each phase to have its own viscosity.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["phase-dependent viscosity", "Heaviside interpolation"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-phase-relaxation-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: 相依赖松弛时间的 Heaviside 插值方法可用于 TensorLBM 多粘度比流动模拟。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-periodic-bc",
        "statement": "All four domain edges use periodic boundary conditions, applied to all distribution functions (h1, h2, g) and phase fields (phi1, phi2, phi3) by copying halo cells from opposite boundaries. No solid wall or inlet/outlet BCs are implemented in the base code.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["periodic BC only", "no solid walls"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-periodic-bc-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: CudaPhaseField 仅支持周期性边界，TensorLBM 需补充壁面/入口/出口边界条件以覆盖更多物理场景。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-precision-warning",
        "statement": "Double precision is the default; single precision is explicitly warned against by the author for quantitative results due to 'gradual drift in phi3_min and unphysical wobble in total mass conservation' from accumulated rounding errors.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["double precision default", "single precision mass drift"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-precision-warning-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: 单精度质量漂移的自文档化警告提示 TensorLBM 在多相流模拟中应默认使用双精度或提供质量守恒监控。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-nvfortran-build",
        "statement": "Built with NVIDIA nvfortran compiler using -cuda flag for CUDA Fortran. The Makefile includes maxregcount:64 as a permanent fix for the collision_h kernel register-overshoot bug that previously caused silent launch failures.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["nvfortran compiler", "maxregcount:64 fix"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-nvfortran-build-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: maxregcount 限制是 CUDA Fortran 内核寄存器溢出的常见修复手段，TensorLBM CUDA 内核开发需注意此问题。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-vtk-output",
        "statement": "Results output as VTK RectilinearGrid (.vtr) files in ASCII format every 8000 timesteps over 1,500,000 total steps (187 output files), including Density, phi1, phi2, phi3, ux, uy, and pressure fields. Console output monitors phi3_min/max, velocity maxima, and total mass every 1000 steps.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["VTK output", "ASCII format", "Float32 output"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-vtk-output-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: VTK RectilinearGrid 输出格式和守恒量监控模式可作为 TensorLBM 后处理模块的参考。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-three-distributions",
        "statement": "The solver maintains three distribution function sets on GPU: h1 (phase-field for component 1), h2 (phase-field for component 2), and g (hydrodynamic pressure/population), each with dimensions (0:nx+1, 0:ny+1, 0:8). For nx=ny=254, each set uses ~4.7 MB in double precision.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["three distribution sets", "GPU memory layout"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-three-distributions-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: 三套分布函数的内存布局设计可作为 TensorLBM 多相流 GPU 内存管理的参考。"
        ]
    },
    {
        "id": "tkc:oss-lbm:cudaphasefield-interface-params",
        "statement": "Default interface width w=4 lattice units and mobility m=0.01. The phase-field relaxation parameter w_c = 1/(0.5 + 3*m) ≈ 1.887. The interface width controls diffuse interface thickness; mobility controls Cahn-Hilliard evolution timescale.",
        "claim_type": "descriptive",
        "scope": {
            "domain": "lattice-Boltzmann-method",
            "system": "CudaPhaseField",
            "conditions": ["w=4", "m=0.01", "diffuse interface"]
        },
        "modality": "asserted",
        "epistemic_status": "established",
        "evidence_refs": ["tke:oss-lbm:cudaphasefield-interface-params-src"],
        "created_at": NOW,
        "created_by": "agent-m8690",
        "version": "1.0.0",
        "notes": [
            "TensorLBM 可服务改进点: 界面宽度 w=4 和迁移率 m=0.01 是相场 LBM 的典型参数，可作为 TensorLBM 多相流验证算例的基准配置。"
        ]
    }
]

# ---- Evidence ----
new_evidence = [
    {
        "id": "tke:oss-lbm:cudaphasefield-three-component-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-three-component"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/global_subroutines.f90 and src/main.f90",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/global_subroutines.f90:30-45 (phi_cal kernel)",
            "quote": "phi1(x,y)= h1(x,y,0) + h1(x,y,1) + ... + h1(x,y,8)\nphi2(x,y)= h2(x,y,0) + h2(x,y,1) + ... + h2(x,y,8)\nphi3(x,y) = 1._fp_kind - phi1(x,y) - phi2(x,y)"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-gpl3-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-gpl3"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, LICENSE and src/main.f90 header",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} LICENSE; src/main.f90:1-12",
            "quote": "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007\n!    CudaPhaseField is three-component flow solver based on th lattice Boltzmann method\n!    Copyright (C) 2021 Amin Zar\n!    This program is free software: you can redistribute it and/or modify\n!    it under the terms of the GNU General Public License as published by\n!    the Free Software Foundation, either version 3 of the License, or\n!    (at your option) any later version."
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-d2q9-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-d2q9"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/device_var.f90",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/device_var.f90:15-18",
            "quote": "integer, constant, parameter :: ex(0:8) = [0, 1, 0,-1, 0, 1,-1,-1, 1]\ninteger, constant, parameter :: ey(0:8) = [0, 0, 1, 0,-1, 1, 1,-1,-1]\nreal(fp_kind), constant, parameter :: wa(0:8) = [16,4, 4, 4, 4, 1, 1, 1, 1] / 36._fp_kind"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-cahn-hilliard-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-cahn-hilliard"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/global_subroutines.f90 (chemical_potential kernel)",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/global_subroutines.f90:330-345",
            "quote": "mu1(x,y) = (12._fp_kind / w) * (lambda(1) * s_phi1(tx,ty) * (1._fp_kind- s_phi1(tx,ty)) * (1._fp_kind - 2._fp_kind * s_phi1(tx,ty)) - 2._fp_kind * lambdat * s_phi1(tx,ty) * s_phi2(tx,ty) * (1._fp_kind - s_phi1(tx,ty) - s_phi2(tx,ty))) - (3._fp_kind / 4._fp_kind) * w * lambda(1) * d2phi1(x,y)"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-shared-memory-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-shared-memory"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/global_subroutines.f90 (gradient_cal and chemical_potential kernels)",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/global_subroutines.f90:70-80 (gradient_cal), 318-322 (Laplacian)",
            "quote": "integer, parameter :: TILE = 32\nreal(fp_kind), shared :: s_phi1(0:TILE+1, 0:TILE+1)\nd2phi1(x,y) = (s_phi1(tx-1,ty-1)+s_phi1(tx+1,ty-1)+s_phi1(tx-1,ty+1)+s_phi1(tx+1,ty+1) +4._fp_kind*(s_phi1(tx,ty-1)+s_phi1(tx-1,ty)+s_phi1(tx+1,ty)+s_phi1(tx,ty+1)) - 20._fp_kind*s_phi1(tx,ty))/6._fp_kind"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-phase-relaxation-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-phase-relaxation"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/global_subroutines.f90 (hydro_cal kernel)",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/global_subroutines.f90:355-358",
            "quote": "heav1(x,y) = 0.5_fp_kind + sign(0.5_fp_kind,phi1(x,y))\nheav2(x,y) = 0.5_fp_kind + sign(0.5_fp_kind,phi2(x,y))\ntauu(x,y) = (tau1 - tau3) * heav1(x,y) + (tau2 - tau3) * heav2(x,y) + tau3"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-periodic-bc-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-periodic-bc"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/global_subroutines.f90 (periodic_phi and periodic_f kernels)",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/global_subroutines.f90:48-65 (periodic_phi), ~700+ (periodic_f)",
            "quote": "phi1(x,0) = phi1(x,nyd)\nphi1(x,nyd+1) = phi1(x,1)\nphi1(0,y) = phi1(nxd,y)\nphi1(nxd+1,y) = phi1(1,y)"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-precision-warning-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-precision-warning"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/precision_m.f90 and README.md",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/precision_m.f90:1-6; README.md (Precision section)",
            "quote": "integer, parameter :: fp_kind = doublePrecision\n**Single precision** runs faster and uses half the memory, but it comes at a real cost to numerical stability: over long runs it shows a gradual drift (a slow decrease in phi3_min, small unphysical wobble in total mass conservation)"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-nvfortran-build-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-nvfortran-build"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, Makefile",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} Makefile:3-5, 40-42",
            "quote": "cc := nvfortran\n# -cuda enables CUDA Fortran\n# maxregcount:64 is not a diagnostic flag -- it's the permanent fix for the collision_h register-overshoot bug\ncudaflags := -cuda -gpu=$(gpu_target),maxregcount:64$(gpu_extra)"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-vtk-output-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-vtk-output"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/host_subroutines.f90 (results_output_host) and src/host_var.f90",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/host_subroutines.f90:430-470; src/host_var.f90:8-9",
            "quote": "write (1,'(A)') '<VTKFile type=\"RectilinearGrid\" version=\"0.1\" byte_order=\"LittleEndian\">'\ninteger,parameter :: tf = 1500000\ninteger,parameter :: step = 8000"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-three-distributions-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-three-distributions"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/device_var.f90",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/device_var.f90:30-35",
            "quote": "real(fp_kind),device, dimension(0:nxd+1,0:nyd+1,0:8) :: h1\nreal(fp_kind),device, dimension(0:nxd+1,0:nyd+1,0:8) :: h2\nreal(fp_kind),device, dimension(0:nxd+1,0:nyd+1,0:8) :: g"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    },
    {
        "id": "tke:oss-lbm:cudaphasefield-interface-params-src",
        "claim_refs": ["tkc:oss-lbm:cudaphasefield-interface-params"],
        "source": {
            "source_type": "other",
            "citation": f"{REPO} source code, src/device_var.f90",
            "url": REPO_URL,
            "accessed_at": "2026-11-09"
        },
        "relation": "supports",
        "locator": {
            "locator_type": "code-location",
            "value": f"{REPO}@{COMMIT} src/device_var.f90:12-14",
            "quote": "real(fp_kind),constant, parameter :: w = 4._fp_kind\nreal(fp_kind),constant, parameter :: m = 0.01_fp_kind\nreal(fp_kind),constant, parameter :: w_c = 1._fp_kind/(0.5_fp_kind + 3._fp_kind*m)"
        },
        "extraction_method": "direct-quotation",
        "captured_at": NOW,
        "captured_by": "agent-m8690",
        "assessment_status": "unassessed",
        "version": "1.0.0"
    }
]

# Append
claims.extend(new_claims)
evidence.extend(new_evidence)

# Update provenance
provenance.append({
    "id": "tkp:oss-lbm:cudaphasefield-ingest-2026-11-09",
    "generated_entity": {
        "id": "knowledge/oss-lbm/cudaphasefield",
        "entity_type": "knowledge-object",
        "version": "1.0.0"
    },
    "activity": {
        "id": "activity-cudaphasefield-ingest",
        "activity_type": "extraction",
        "description": f"Source-code-driven extraction of 12 claims about {REPO} (three-phase phase-field LBM CUDA solver, GPL-3). Each claim verified against actual source code cloned from GitHub with file:line locators and verbatim quotes. Commit {COMMIT}.",
        "started_at": "2026-11-09T15:30:00Z",
        "ended_at": "2026-11-09T16:00:00Z",
        "used_entities": [
            f"{REPO}@{COMMIT}"
        ],
        "software": [
            {"name": "python", "version": "3.12"},
            {"name": "git", "version": "2.x"}
        ]
    },
    "agents": [
        {
            "id": "agent-m8690",
            "agent_type": "software-agent",
            "name": "TensorKnowledge builder agent",
            "role": "knowledge extractor"
        }
    ],
    "derived_from": [
        f"{REPO} source code ({REPO_URL})"
    ],
    "recorded_at": NOW,
    "version": "1.0.0"
})

# Write back
json.dump(claims, open("knowledge/oss-lbm/claims/claims.json", "w"), indent=2, ensure_ascii=False)
json.dump(evidence, open("knowledge/oss-lbm/evidence/evidence.json", "w"), indent=2, ensure_ascii=False)
json.dump(provenance, open("knowledge/oss-lbm/provenance/provenance.json", "w"), indent=2, ensure_ascii=False)

print(f"Appended {len(new_claims)} claims, {len(new_evidence)} evidence, 1 provenance")
print(f"Total: {len(claims)} claims, {len(evidence)} evidence, {len(provenance)} provenance")
