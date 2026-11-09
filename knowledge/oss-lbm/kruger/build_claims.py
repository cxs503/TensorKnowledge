#!/usr/bin/env python3
"""Build the OSS-LBM / Kruger claim package from the pinned upstream checkout.

Design rule (mission m8676): no quotation is ever typed by hand.  Every evidence
record is produced by locating an anchor string in the upstream file and slicing
`n_lines` lines starting at that anchor; the resulting text is stored verbatim
together with the resolved 1-based line span.  A machine-readable
`kruger_source_index.json` (path, sha256, quoted spans) is emitted alongside so the
validator and the tests can re-check the quotations offline.

Usage:
    KRUGER_REPO=/path/to/lbm-principles-practice-code python build_claims.py
    python build_claims.py --repo /path/to/checkout --check   # verify only

Requires a git checkout of github.com/lbm-principles-practice/code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # repository root
ARTIFACTS = ROOT / "artifacts" / "oss-lbm-kruger"
RUNS = ROOT / "runs" / "oss-lbm-kruger-8676"

REPO_SLUG = "lbm-principles-practice/code"
REPO_URL = "https://github.com/lbm-principles-practice/code"
CACHE_CANDIDATES = [
    "/root/oss-cache/lbm-principles-practice-code",
    "/root/oss-cache/code",
    "/tmp/lpp-code",
]
GAP_ANCHOR = "GAP-LBM-BENCH-METHODOLOGY"
CREATED_AT = "2026-11-09T15:20:00Z"
AGENT = "agent-m8676"

# ---------------------------------------------------------------------------
# Evidence specifications: (evidence id, file, anchor string, n_lines, relation)
# ---------------------------------------------------------------------------
EVIDENCE_SPECS = [
    # --- chapter5: Poiseuille / Couette with bounce-back and wet nodes --------
    ("kruger-poiseuille-bb-tau", "chapter5/poiseuille_BB.m",
     "tau=sqrt(3/16)+0.5;", 1, "supports"),
    ("kruger-poiseuille-bb-analytic", "chapter5/poiseuille_BB.m",
     "ybottom=0;", 3, "supports"),
    ("kruger-poiseuille-bb-pbbc", "chapter5/poiseuille_BB.m",
     "f(1,:,k) = w(k)*(rho_inlet+...", 3, "supports"),
    ("kruger-poiseuille-bb-linear-eq", "chapter5/poiseuille_BB.m",
     "feq(:,:,k)=w(k)*(rho + 3*(u*cx(k)+v*cy(k)));", 1, "supports"),
    ("kruger-couette-wetnode-variants", "chapter5/couette_wetnode.m",
     "% 1) Equilibrium scheme:", 3, "supports"),
    ("kruger-couette-bb-moving-wall", "chapter5/couette_BB.m",
     "% Top wall (moving with tangential velocity u_max)", 3, "supports"),
    ("kruger-couette-bb-analytic", "chapter5/couette_BB.m",
     "u_analy=u_max/NY.*y;", 1, "supports"),
    ("kruger-poiseuille-wetnode-gradp", "chapter5/poiseuille_wetnode.m",
     "gradP=8*nu*u_max/(ytop-ybottom)^2;", 3, "supports"),
    ("kruger-poiseuille-wetnode-wallpos", "chapter5/poiseuille_wetnode.m",
     "% Wall locations", 3, "supports"),
    # --- chapter6: body-force models and force/pressure splits ---------------
    ("kruger-force-model-axes", "chapter6/force_poiseuille_BB.m",
     "force_spatial_order=1", 3, "supports"),
    ("kruger-force-split-matrix", "chapter6/force_poiseuille_BB.m",
     "select_combination=1", 3, "supports"),
    ("kruger-force-init-shift", "chapter6/force_poiseuille_BB.m",
     "feq(i,:,k)=w(k)-0.5*w(k)*3*(cx(k)*forcex(i)+cy(k)*forcey(i));", 1, "supports"),
    # --- chapter13: Taylor-Green vortex decay -------------------------------
    ("kruger-tg-analytic-td", "chapter13/python3/vortexdecay.py",
     "td = 1/(nu*(kx*kx+ky*ky))", 1, "supports"),
    ("kruger-tg-analytic-velocity", "chapter13/python3/vortexdecay.py",
     "u = np.array([-u_max*np.sqrt(ky/kx)", 2, "supports"),
    ("kruger-tg-l2-norms", "chapter13/python3/vortexdecay.py",
     "L2rho = np.sqrt( sumrhoe2  / sumrhoa2 )", 3, "supports"),
    ("kruger-tg-cpu-constants", "chapter13/cpu/LBM.h",
     "const double nu = 1.0/6.0;", 2, "supports"),
    ("kruger-tg-cpu-domain", "chapter13/cpu/LBM.h",
     "const unsigned int NX = 32*scale;", 2, "supports"),
    ("kruger-tg-gpu-backend", "chapter13/gpu/compile.sh",
     "nvcc -arch sm_20", 1, "supports"),
    ("kruger-tg-mpi-backend", "chapter13/mpi/blocking/compile.sh",
     "mpic++ ${CXXFLAGS} -c LBM.cpp -o LBM.o", 1, "supports"),
    ("kruger-tg-openmp-backend", "chapter13/openmp/compile.sh",
     "g++ ${CXXFLAGS} -fopenmp -c LBM.cpp -o LBM.o", 1, "supports"),
    # --- chapter9: Shan-Chen multiphase / Laplace pressure -------------------
    ("kruger-sc-pseudopotential", "chapter9/shanchen.cpp",
     "double psi(double dens) {", 3, "supports"),
    ("kruger-sc-force", "chapter9/shanchen.cpp",
     "fxtemp *= (-g[s][ss] * psiloc);", 2, "supports"),
    ("kruger-sc-pressure", "chapter9/shanchen.cpp",
     "press[k] += (g[s][ss] * psi(rho[s][k]) * psi(rho[ss][k]) / 6.);", 1, "supports"),
    ("kruger-sc-laplace", "chapter9/shanchen.cpp",
     "const double gamma = delta_press * rad;", 1, "supports"),
    ("kruger-sc-setup", "chapter9/shanchen.cpp",
     "const double radius = 15.;", 1, "supports"),
    # --- chapter11: immersed-boundary LBM -----------------------------------
    ("kruger-ib-lbm-header", "chapter11/IBLBM_2D_Poiseuille.cpp",
     "It uses the D2Q9 lattice with Guo's forcing term.", 1, "supports"),
    ("kruger-ib-lbm-stencil", "chapter11/IBLBM_2D_Poiseuille.cpp",
     "int IBM_stencil = 2;", 1, "supports"),
    ("kruger-ib-lbm-wall", "chapter11/IBLBM_2D_Poiseuille.cpp",
     "const double wall_stiffness = 1;", 1, "supports"),
    ("kruger-ib-lbm-nodes", "chapter11/IBLBM_2D_Poiseuille.cpp",
     "const int wall_num_nodes = 19;", 1, "supports"),
    # --- chapter8: TRT magic parameter --------------------------------------
    ("kruger-trt-magic-formula", "chapter8/gaussian_1d_magic12.cpp",
     "double omega_plus_phase=1.0/(magic/(1.0/omega-0.5)+0.5);", 1, "supports"),
    ("kruger-trt-magic6-values", "chapter8/gaussian_1d_magic6.cpp",
     "double magic=1.0/6.0;", 2, "supports"),
    ("kruger-trt-magic12-values", "chapter8/gaussian_1d_magic12.cpp",
     "double magic=1.0/12.0;", 2, "supports"),
    ("kruger-trt-cylinder", "chapter8/cylinder.cpp",
     "double omega=1.0/(0.5+0.5/32.0);", 2, "supports"),
    ("kruger-trt-cylinder-plus", "chapter8/cylinder.cpp",
     "double omega_plus=2.0-omega;", 2, "supports"),
    ("kruger-trt-cylinder-domain", "chapter8/cylinder.cpp",
     "NY=129;", 2, "supports"),
    ("kruger-trt-cylinder-geometry", "chapter8/cylinder.cpp",
     "radius=40;", 1, "supports"),
]

# ---------------------------------------------------------------------------
# Run-level evidence (products of the verification runs, not upstream code)
# ---------------------------------------------------------------------------
RUN_EVIDENCE = [
    ("kruger-run-chapter5-port", "port_chapter5",
     "validation_summary.json#port_chapter5 (NumPy port of chapter5/poiseuille_BB.m and "
     "chapter5/couette_BB.m; MATLAB/Octave unavailable in this image)"),
    ("kruger-run-taylor-green", "taylor_green",
     "validation_summary.json#taylor_green (chapter13/python3/vortexdecay.py executed at "
     "NX=32/64/128, L2 norms vs analytic Taylor-Green solution)"),
    ("kruger-run-young-laplace", "young_laplace",
     "validation_summary.json#young_laplace (chapter9/shanchen.cpp compiled and executed for "
     "initial droplet radii 15 and 12; Laplace pressure and gamma = dp*r)"),
    ("kruger-run-ib-lbm", "ib_lbm_poiseuille",
     "validation_summary.json#ib_lbm_poiseuille (chapter11/IBLBM_2D_Poiseuille.cpp executed 2000 "
     "steps; mid-channel profile vs the analytic value printed by the code itself)"),
]

# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------
CLAIMS = [
    dict(
        id="tkc:oss-lbm:kruger-poiseuille-bb-tau",
        statement=(
            "chapter5/poiseuille_BB.m simulates the pressure-driven plane Poiseuille benchmark with "
            "half-way bounce-back walls using the BGK relaxation time tau = sqrt(3/16) + 0.5, which the "
            "source itself documents as the value that gives the exact solution."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["D2Q9", "BGK collision", "half-way bounce-back walls", "steady state"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-poiseuille-bb-tau",
                       "tke:oss-lbm:kruger-poiseuille-bb-analytic"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 泊肃叶标准算例的壁面精度基准点（τ 魔数）",
               "TensorLBM 可服务改进点: 可作为 TensorLBM 通道流回归测试的参考 τ 与参考剖面，"
               "在 CI 中断言稳态剖面对解析抛物线的 L2 误差量级。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-poiseuille-bb-linear-equilibrium",
        statement=(
            "The Poiseuille benchmark uses a linearised (incompressible-limit) D2Q9 equilibrium, "
            "feq = w_k (rho + 3 c_k.u), and obtains the macroscopic velocity from population sums without "
            "dividing by the density."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["BGK", "incompressible-limit equilibrium", "momentum from populations"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-poiseuille-bb-linear-eq"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 宏观量提取约定（u 未除 rho）必须与解析解比较口径一致",
               "TensorLBM 可服务改进点: 基准对比时必须统一宏观量定义（ρu 与 u 的差异在 ρ≠1 时成为系统性偏差）。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-poiseuille-pbbc-inout",
        statement=(
            "Inlet and outlet of the Poiseuille channel are closed with a pressure boundary condition "
            "(the source labels it 'PBBC'): the incoming population is set to the equilibrium at the target "
            "density plus the non-equilibrium part copied from the adjacent fluid layer, with density "
            "contrast rho_inlet = 3 (NX-1) gradP + rho_outlet."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["PBBC / non-equilibrium extrapolation", "inlet and outlet are non-periodic",
                              "two virtual layers i=1 and i=NX"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-poiseuille-bb-pbbc",
                       "tke:oss-lbm:kruger-poiseuille-wetnode-gradp"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 压差驱动算例的进出口边界口径（勿以周期驱动冒充压力驱动）",
               "TensorLBM 可服务改进点: 压力边界 + 非平衡外推的组合可直接作为 TensorLBM 进出口实现的对照实现。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-couette-wetnode-family",
        statement=(
            "chapter5/couette_wetnode.m exposes three wet-node wall schemes selected by an integer flag: "
            "1 = equilibrium scheme, 2 = non-equilibrium extrapolation, other = non-equilibrium bounce-back, "
            "all applied on wall nodes that lie inside the computational domain."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["wet-node boundary conditions", "Couette flow", "switch by integer flag"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-couette-wetnode-variants",
                       "tke:oss-lbm:kruger-poiseuille-wetnode-wallpos"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 库特标准算例上的壁面条件族对照（湿节点三式 vs 反弹）",
               "TensorLBM 可服务改进点: 壁面条件应以「族」形式实现并共用同一基准，便于逐个量误差阶。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-couette-bb-moving-wall",
        statement=(
            "chapter5/couette_BB.m drives Couette flow by a moving half-way bounce-back wall: the reflected "
            "diagonal populations receive the momentum offset -/+ (1/6) u_max, and the analytic reference is "
            "the linear profile u = u_max y / NY with wall planes at y = 0 and y = NY."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["moving wall", "half-way bounce-back", "D2Q9", "steady state"]},
        modality="asserted", epistemic_status="well-supported",
        evidence_refs=["tke:oss-lbm:kruger-couette-bb-moving-wall",
                       "tke:oss-lbm:kruger-couette-bb-analytic",
                       "tke:oss-lbm:kruger-run-chapter5-port"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 库特算例的运动壁动量注入基准",
               "TensorLBM 可服务改进点: 运动壁动量偏移 6 w_k rho c_k.u_wall 应由权重推导，不要硬编码 1/6。",
               "运行佐证: 逐行 NumPy 移植 (runs/oss-lbm-kruger-8676) 得 L2 = 2.3e-15，与解析线性剖面机器精度一致。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-poiseuille-wetnode-setup",
        statement=(
            "The wet-node Poiseuille variant places the walls on lattice nodes y = 1 and y = NY inside the "
            "domain and drives the flow with gradP = 8 nu u_max / (ytop - ybottom)^2, giving the density "
            "difference rho_inlet = 3 (NX-1) gradP + rho_outlet."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["wet-node walls", "pressure-driven channel", "tau = 0.7"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-poiseuille-wetnode-wallpos",
                       "tke:oss-lbm:kruger-poiseuille-wetnode-gradp"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 湿节点壁面位置（通道宽度定义）必须与解析解一致",
               "TensorLBM 可服务改进点: 通道宽度定义（节点中心距 vs 物理壁面距）在湿节点与反弹壁下不同，"
               "基准脚本需显式区分，否则引入 O(1/NY) 的系统偏差。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-force-model-axes",
        statement=(
            "chapter6/force_poiseuille_BB.m separates the body-force discretisation into two independent "
            "axes: the spatial (time/configuration) order, 1st or 2nd, and the velocity-space order, 1st "
            "(Buick and Greated) or 2nd (Guo et al.), each selected by its own flag."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["body force", "Guo forcing", "Buick-Greated forcing", "flag-selected variants"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-force-model-axes"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 体积力驱动算例的力项离散口径（一/二阶 × 一/二阶）",
               "TensorLBM 可服务改进点: 力项实现应参数化为 (spatial_order, velocity_order) 两轴，"
               "并以同一泊肃叶基准交叉验证四种组合。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-force-pressure-split",
        statement=(
            "The forced Poiseuille code splits the driving between body force and pressure gradient in three "
            "selectable ways: constant body force only; 50/50 constant force plus constant pressure gradient; "
            "or 50/50 linearly varying force plus linearly varying pressure gradient."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["body force", "pressure gradient", "steady state"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-force-split-matrix"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 驱动力分配方式的等价性检查（三种分配应给出同一稳态剖面）",
               "TensorLBM 可服务改进点: 可作为力项实现的等价性回归测试用例。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-force-init-shift",
        statement=(
            "Initialisation in the forced Poiseuille code carries a half-force offset in the equilibrium, "
            "feq = w_k - 0.5 w_k 3 c_k.F, i.e. the populations are initialised consistently with the force "
            "to O(dt) rather than to the force-free equilibrium."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["forced flow", "initial condition", "Guo-type force"]},
        modality="asserted", epistemic_status="provisional",
        evidence_refs=["tke:oss-lbm:kruger-force-init-shift"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 初始条件与力项的一致性（影响瞬态误差而非稳态）",
               "保守定级理由: 代码事实已逐字核实，但其对收敛速度/瞬态误差的收益本单未做对照实验，故 provisional。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-tg-analytic-solution",
        statement=(
            "chapter13/python3/vortexdecay.py validates the D2Q9 BGK solver against the analytic Taylor-Green "
            "vortex solution: velocity components decay as exp(-t/t_d) with t_d = 1/(nu (kx^2+ky^2)), and the "
            "L2 norms of density, ux and uy are computed against that solution every NMSG steps."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["Taylor-Green vortex", "periodic domain", "BGK tau = 1", "u_max = 0.04/scale"]},
        modality="asserted", epistemic_status="well-supported",
        evidence_refs=["tke:oss-lbm:kruger-tg-analytic-td",
                       "tke:oss-lbm:kruger-tg-analytic-velocity",
                       "tke:oss-lbm:kruger-tg-l2-norms",
                       "tke:oss-lbm:kruger-run-taylor-green"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 有解析解的标准算例（Taylor-Green 衰减）作为精度与收敛阶基准",
               "TensorLBM 可服务改进点: 该解析解与 L2 归一化口径可直接作为 TensorLBM 时间推进器的二阶收敛测试。",
               "运行佐证: NX=32/64/128 三档执行，L2(ux) = 7.69e-3 / 1.92e-3 / 4.79e-4，实测收敛阶 2.00。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-tg-multi-backend-ladder",
        statement=(
            "The same Taylor-Green case ships in seven implementations (python3, cpu, cpu_intro, openmp, "
            "mpi/blocking, mpi/nonblocking, gpu), all built from identical constants (nu = 1/6, tau = 3 nu + 0.5, "
            "NX = 32 scale, NSTEPS = 200 scale^2) and compiled with g++, mpic++ or nvcc respectively, so the "
            "repository doubles as a performance-ladder benchmark."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["identical physical parameters across backends", "CUDA / MPI / OpenMP / serial"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-tg-cpu-constants",
                       "tke:oss-lbm:kruger-tg-cpu-domain",
                       "tke:oss-lbm:kruger-tg-gpu-backend",
                       "tke:oss-lbm:kruger-tg-mpi-backend",
                       "tke:oss-lbm:kruger-tg-openmp-backend"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 同一算例跨后端可比性（Mlups 阶梯）",
               "TensorLBM 可服务改进点: 异构后端基准应固定物理参数与输出口径，只替换内核，避免「换参数换结果」。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-shanchen-laplace",
        statement=(
            "chapter9/shanchen.cpp implements single-component Shan-Chen multiphase flow with the exponential "
            "pseudopotential psi = rho0 (1 - exp(-rho/rho0)), nearest-neighbour force summation, pressure "
            "p = rho/3 + g psi psi/6, and then measures surface tension from the Young-Laplace law as "
            "gamma = (p_liquid - p_gas) * r, with the interface radius r located by linear interpolation of the "
            "density profile along the centre line."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["D2Q9", "Shan-Chen pseudopotential", "g = -4.7", "64x64 periodic box",
                              "droplet initial radius 15"]},
        modality="asserted", epistemic_status="well-supported",
        evidence_refs=["tke:oss-lbm:kruger-sc-pseudopotential",
                       "tke:oss-lbm:kruger-sc-force",
                       "tke:oss-lbm:kruger-sc-pressure",
                       "tke:oss-lbm:kruger-sc-laplace",
                       "tke:oss-lbm:kruger-sc-setup",
                       "tke:oss-lbm:kruger-run-young-laplace"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— Young-Laplace 定律作为多相/界面算例的验证面",
               "TensorLBM 可服务改进点: 表面张力应从 Laplace 压强差反演并与 Laplace 定律交叉校验，"
               "且应在两个以上半径上验证 gamma 不变性。",
               "运行佐证: 半径 16.32 与 12.29 两算例给出 gamma = 0.02072 / 0.02039（相对差 1.61%）。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-ib-lbm-poiseuille",
        statement=(
            "chapter11/IBLBM_2D_Poiseuille.cpp combines D2Q9 with Guo forcing and an immersed-boundary method: "
            "each wall is discretised with 19 Lagrangian nodes of stiffness 1, the interpolation stencil is "
            "switchable between 2 and 4 points, forces are spread/interpolated every step, and the code prints "
            "its own analytic expectation for the Poiseuille centre-line velocity."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["immersed boundary method", "Guo forcing", "periodic in x", "gravity-driven",
                              "wall_width = 15.3"]},
        modality="asserted", epistemic_status="well-supported",
        evidence_refs=["tke:oss-lbm:kruger-ib-lbm-header",
                       "tke:oss-lbm:kruger-ib-lbm-stencil",
                       "tke:oss-lbm:kruger-ib-lbm-wall",
                       "tke:oss-lbm:kruger-ib-lbm-nodes",
                       "tke:oss-lbm:kruger-run-ib-lbm"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 浸没边界算例的解析基准与分辨率敏感性",
               "TensorLBM 可服务改进点: IBM 力扩散/插值核（2 点 vs 4 点）应以同一基准分别量误差，"
               "并注意低分辨率下中心线速度的系统性偏低。",
               "运行佐证: Ny=20 时中心线速度 1.642e-3 vs 代码自带解析期望 1.756e-3（-6.5%）。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-trt-magic-parameter",
        statement=(
            "The chapter8 two-relaxation-time examples compute one relaxation frequency from a magic parameter "
            "Lambda as omega = 1/(Lambda/(1/omega_other - 0.5) + 0.5), and ship the same 1D Gaussian "
            "advection-diffusion case twice with Lambda = 1/6 and Lambda = 1/12 so that the effect of the magic "
            "parameter can be isolated."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["TRT collision", "1D advection-diffusion of a Gaussian",
                              "magic parameter 1/6 vs 1/12"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-trt-magic-formula",
                       "tke:oss-lbm:kruger-trt-magic6-values",
                       "tke:oss-lbm:kruger-trt-magic12-values"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 魔数参数（TRT 壁面/边界精度自由度）的成对对照实验设计",
               "TensorLBM 可服务改进点: TRT 两个松弛频率应由 (omega, Lambda) 参数化，"
               "并提供成对算例分辨 Lambda 对边界精度的影响。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-cylinder-trt-karman",
        statement=(
            "chapter8/cylinder.cpp sets up a D2Q9 TRT flow past a circular cylinder in a 129x129 box with "
            "radius 40 lattice units (diameter 80), omega = 1/(0.5 + 0.5/32) and omega_plus = 2 - omega, i.e. "
            "the magic-parameter pair Lambda = 1/4, and marks the geometry (fluid / wall / boundary layer) in an "
            "integer mask before time stepping."
        ),
        claim_type="descriptive",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code",
               "conditions": ["TRT", "cylinder in cross-flow", "129x129 lattice", "radius 40"]},
        modality="asserted", epistemic_status="established",
        evidence_refs=["tke:oss-lbm:kruger-trt-cylinder",
                       "tke:oss-lbm:kruger-trt-cylinder-plus",
                       "tke:oss-lbm:kruger-trt-cylinder-domain",
                       "tke:oss-lbm:kruger-trt-cylinder-geometry"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 绕流标准算例（圆柱/卡门涡街）的几何与分辨率口径",
               "TensorLBM 可服务改进点: 圆柱绕流算例必须固定 D（晶格单位）、阻塞比与 Re 定义，"
               "否则 Strouhal/Cd/Cl 无法跨实现比对。"],
    ),
    dict(
        id="tkc:oss-lbm:kruger-poiseuille-bb-exactness-scope",
        statement=(
            "The documented exactness of the half-way bounce-back Poiseuille solution at tau = sqrt(3/16) + 0.5 "
            "was reproduced only for part of the tested channel widths: a line-by-line NumPy port reaches "
            "L2 = 7.6e-16 at NY = 5 and 6.8e-13 at NY = 15, but 4.0e-3 at NY = 10 and 1.1e-3 at NY = 20 "
            "(u_max = 0.1/scale, tau fixed), so as an unrestricted statement it is not supported by this evidence."
        ),
        claim_type="hypothesis",
        scope={"domain": "lattice-Boltzmann-method", "system": "lbm-principles-practice/code (port)",
               "conditions": ["BGK", "half-way bounce-back", "linear equilibrium", "PBBC inlet/outlet",
                              "tau = sqrt(3/16)+0.5", "steady state", "u_max scaled as 0.1/scale"]},
        modality="hypothetical", epistemic_status="contested",
        evidence_refs=["tke:oss-lbm:kruger-poiseuille-bb-tau",
                       "tke:oss-lbm:kruger-run-chapter5-port"],
        notes=["GAP 锚: GAP-LBM-BENCH-METHODOLOGY —— 「精确解」结论的适用范围必须随分辨率登记（negative result）",
               "诚实的负面结果: 偶数宽度（NY=10/20）未达机器精度；可能源于 PBBC 进出口非平衡外推项与偶数宽度"
               "的奇偶耦合，也可能源于本移植与 MATLAB 原码的差异（原码本机不可执行，无法对拍）。"
               "在拿到 MATLAB/Octave 原码结果之前，本条保持 contested。"],
    ),
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_repo(arg: str | None) -> Path:
    cand = [arg, os.environ.get("KRUGER_REPO")] + CACHE_CANDIDATES
    for c in cand:
        if c and Path(c, "chapter5").is_dir():
            return Path(c).resolve()
    raise SystemExit(
        "FATAL: no checkout of lbm-principles-practice/code found. Looked at: "
        + ", ".join(str(c) for c in cand if c)
        + "\nSet KRUGER_REPO=/path/to/checkout (see runs/oss-lbm-kruger-8676/run_upstream_cases.sh).")


def _extract(repo: Path, rel: str, anchor: str, n_lines: int, index: dict) -> tuple[str, int, int]:
    path = repo / rel
    if not path.is_file():
        raise SystemExit(f"FATAL: missing upstream file {rel}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"FATAL: anchor {anchor!r} in {rel} matched {len(hits)} lines (need exactly 1)")
    start = hits[0]
    span = lines[start:start + n_lines]
    if len(span) != n_lines:
        raise SystemExit(f"FATAL: quote for {rel} runs past end of file")
    if n_lines > 3:
        raise SystemExit("FATAL: quotes are limited to 3 lines")
    quote = "\n".join(span)
    entry = index.setdefault(rel, {"sha256": _sha256(path), "lines": len(lines), "quoted_spans": []})
    entry["quoted_spans"].append({"line_start": start + 1, "line_end": start + n_lines, "quote": quote})
    return quote, start + 1, start + n_lines


def build(repo: Path, commit: str, verify_only: bool = False) -> dict:
    index: dict = {}
    evidence: list[dict] = []
    for eid, rel, anchor, n, relation in EVIDENCE_SPECS:
        quote, l0, l1 = _extract(repo, rel, anchor, n, index)
        evidence.append({
            "id": f"tke:oss-lbm:{eid}",
            "claim_refs": [],                      # filled below from CLAIMS
            "source": {
                "source_type": "other",
                "citation": f"{REPO_SLUG} {rel} (Kruger et al., The Lattice Boltzmann Method: "
                            f"Principles and Practice, Springer 2017; MIT-licensed accompanying code)",
                "url": REPO_URL,
                "accessed_at": "2026-11-09",
            },
            "relation": relation,
            "locator": {
                "locator_type": "code-location",
                "value": f"{REPO_SLUG}@{commit[:7]} {rel}:{l0}-{l1}",
                "quote": quote,
                "quote_language": Path(rel).suffix.lstrip("."),
            },
            "extraction_method": "direct-quotation",
            "captured_at": CREATED_AT,
            "captured_by": AGENT,
            "assessment_status": "unassessed",
            "version": "1.0.0",
        })

    summary_path = RUNS / "validation_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text())
        for eid, key, label in RUN_EVIDENCE:
            if key not in summary:
                print(f"WARN: {key} not in validation_summary.json -> evidence {eid} skipped", file=sys.stderr)
                continue
            payload = summary[key]
            if eid == "kruger-run-chapter5-port":
                quote = (f"poiseuille L2={payload['poiseuille']['L2']:.3e} "
                         f"(tau={payload['poiseuille']['tau']:.6f}), "
                         f"couette L2={payload['couette']['L2']:.3e}")
            elif eid == "kruger-run-taylor-green":
                quote = "; ".join(f"NX={c['NX']} L2(ux)={c['L2_ux']:.3e}" for c in payload["runs"])
            elif eid == "kruger-run-young-laplace":
                quote = (f"gamma={payload['cases']['radius15']['gamma']:.5f} / "
                         f"{payload['cases']['radius12']['gamma']:.5f}, "
                         f"rel diff {payload['gamma_rel_diff_pct']:.2f}%")
            else:
                quote = (f"u_centre={payload['u_centre_measured']:.6f} vs expected "
                         f"{payload['u_max_expected']:.6f} ({payload['centreline_error_pct']:+.2f}%)")
            evidence.append({
                "id": f"tke:oss-lbm:{eid}",
                "claim_refs": [],
                "source": {"source_type": "other",
                           "citation": f"m8676 verification run: {label}",
                           "url": "local:runs/oss-lbm-kruger-8676",
                           "accessed_at": "2026-11-09"},
                "relation": "supports",
                "locator": {"locator_type": "other",
                            "value": f"runs/oss-lbm-kruger-8676/validation_summary.json#{key}",
                            "quote": quote},
                "extraction_method": "simulation",
                "captured_at": CREATED_AT,
                "captured_by": AGENT,
                "assessment_status": "unassessed",
                "version": "1.0.0",
            })
    else:
        print(f"WARN: {summary_path} missing -> run-level evidence skipped", file=sys.stderr)

    ev_by_id = {e["id"]: e for e in evidence}
    claims = []
    for c in CLAIMS:
        for ref in c["evidence_refs"]:
            if ref not in ev_by_id:
                raise SystemExit(f"FATAL: claim {c['id']} references unknown evidence {ref}")
            ev_by_id[ref]["claim_refs"].append(c["id"])
        claims.append({
            "id": c["id"],
            "statement": c["statement"],
            "claim_type": c["claim_type"],
            "scope": c["scope"],
            "modality": c["modality"],
            "epistemic_status": c["epistemic_status"],
            "evidence_refs": list(c["evidence_refs"]),
            "created_at": CREATED_AT,
            "created_by": AGENT,
            "version": "1.0.0",
            "notes": list(c["notes"]),
        })

    provenance = [{
        "id": "tkp:oss-lbm:kruger-ingestion-2026-11-09",
        "generated_entity": {"id": "knowledge/oss-lbm/kruger", "entity_type": "knowledge-object",
                             "version": "1.0.0"},
        "activity": {
            "id": "activity-oss-lbm-kruger-ingest",
            "activity_type": "extraction",
            "description": (
                f"Source-driven extraction of {len(claims)} claims about {REPO_SLUG} at commit {commit}. "
                "Every quote is machine-sliced from the upstream file at the recorded line span "
                "(build_claims.py); no quotation was transcribed by hand. Four upstream programs were "
                "additionally compiled and executed (chapter9, chapter11, chapter13 python3) and the two "
                "MATLAB scripts of chapter5 were ported line-by-line, to attach execution evidence to the "
                "benchmark-methodology claims."
            ),
            "started_at": "2026-11-09T14:48:00Z",
            "ended_at": CREATED_AT,
            "used_entities": [f"{REPO_SLUG}@{commit}",
                              "chapter5/poiseuille_BB.m", "chapter5/couette_BB.m",
                              "chapter6/force_poiseuille_BB.m", "chapter8/gaussian_1d_magic6.cpp",
                              "chapter8/gaussian_1d_magic12.cpp", "chapter8/cylinder.cpp",
                              "chapter9/shanchen.cpp", "chapter11/IBLBM_2D_Poiseuille.cpp",
                              "chapter13/python3/vortexdecay.py", "chapter13/cpu/LBM.h"],
            "software": [{"name": "python", "version": "3.12"},
                         {"name": "jsonschema", "version": "4.26"},
                         {"name": "numpy", "version": "2.4"},
                         {"name": "g++", "version": "system"}],
        },
        "agents": [{"id": AGENT, "agent_type": "software-agent",
                    "name": "TensorKnowledge builder agent", "role": "knowledge extractor"}],
        "derived_from": [f"{REPO_URL} (Kruger, Kusumaatmaja, Kuzmin, Shardt, Silva, Viggen, "
                         f"The Lattice Boltzmann Method: Principles and Practice, Springer 2017)",
                         "local verification runs: runs/oss-lbm-kruger-8676"],
        "recorded_at": CREATED_AT,
        "version": "1.0.0",
        "extensions": {
            "gap_anchors": [GAP_ANCHOR],
            "gap_anchor_owner": ("TensorKnowledge / OSS-LBM ingestion line (m8676); anchor registered in "
                                 "knowledge/oss-lbm/kruger/GAP-ANCHORS.md"),
            "source_cache_status": (
                "insufficient: /root/oss-cache/ does not exist in this image (no directory name matches the "
                "repo slug). Deviation: the checkout was obtained from the upstream remote at the commit "
                "recorded above; every quoted span is pinned by line number and sha256 in "
                "artifacts/oss-lbm-kruger/kruger_source_index.json, so the quotes remain auditable."
            ),
            "epistemic_note": "All claims are draft (evidence assessment_status = unassessed, no review events).",
        },
    }]

    package = {"claims": claims, "evidence": evidence, "provenance": provenance, "source_index": index}
    if not verify_only:
        for sub in ("claims", "evidence", "provenance"):
            (HERE / sub).mkdir(exist_ok=True)
        (HERE / "claims" / "claims.json").write_text(
            json.dumps(claims, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (HERE / "evidence" / "evidence.json").write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (HERE / "provenance" / "provenance.json").write_text(
            json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "kruger_source_index.json").write_text(
            json.dumps({"repo": REPO_SLUG, "commit": commit, "commit_short": commit[:7],
                        "files": index}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (HERE / "CLAIMS.md").write_text(render_markdown(claims, evidence, commit), encoding="utf-8")
    return package


def render_markdown(claims: list[dict], evidence: list[dict], commit: str) -> str:
    ev = {e["id"]: e for e in evidence}
    out = [
        "# Kruger (lbm-principles-practice/code) — claim table",
        "",
        f"Generated by `build_claims.py` from `{REPO_SLUG}@{commit[:7]}`. Do not edit by hand.",
        "",
        "| # | claim id | status | evidence (file:lines) | quote (verbatim, truncated) |",
        "|---|----------|--------|-----------------------|-------|",
    ]
    for i, c in enumerate(claims, 1):
        locators, quotes = [], []
        for ref in c["evidence_refs"]:
            e = ev[ref]
            locators.append(e["locator"]["value"])
            q = e["locator"]["quote"].replace("|", "\\|").replace("\n", " / ")
            quotes.append(textwrap.shorten(q, 100, placeholder=" …"))
        out.append(f"| {i} | `{c['id']}` | {c['epistemic_status']} | {('<br>'.join(locators))} | "
                   f"{('<br>'.join(quotes))} |")
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=None)
    ap.add_argument("--check", action="store_true", help="verify only, do not write")
    args = ap.parse_args()
    repo = _resolve_repo(args.repo)
    try:
        commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        commit = "unknown"
    pkg = build(repo, commit, verify_only=args.check)
    print(f"repo       : {repo}")
    print(f"commit     : {commit}")
    print(f"claims     : {len(pkg['claims'])}")
    print(f"evidence   : {len(pkg['evidence'])}")
    print(f"provenance : {len(pkg['provenance'])}")
    print(f"files quoted: {len(pkg['source_index'])}")
    if not args.check:
        print(f"written    : {HERE}/claims|evidence|provenance, {ARTIFACTS}/kruger_source_index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())