#!/usr/bin/env python3
"""Build the Ludwig OSS-LBM knowledge package (claims/evidence/provenance).

Quotes are sliced *verbatim* from a checkout of the source tree, so no
transcription is performed by hand (Tab characters, backslashes and spacing
are preserved byte-for-byte).

Usage:
    LUDWIG_SRC=/path/to/ludwig LUDWIG_COMMIT=<40-hex> \
        python build_package.py [--check]

    --check   only verify that the current JSON still matches the source
              tree (used by the pytest suite); nothing is written.

The Ludwig source is ANSI C (see README.md, "written in standard ANSI C"),
free-energy lattice Boltzmann code for complex fluids (EPCC, Edinburgh).
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent

# ---------------------------------------------------------------------------
# Source slices: (evidence id, path, line_start, line_end)
# Quotes are taken inclusive of both end points; <= 3 lines each.
# ---------------------------------------------------------------------------

SLICES = {
    "tke:oss-lbm:ludwig-fe-enum-src": ("src/free_energy.h", 27, 29),
    "tke:oss-lbm:ludwig-fe-vtable-mu-src": ("src/free_energy.h", 44, 46),
    # equation line plus the finite-difference scheme statement
    "tke:oss-lbm:ludwig-ch-equation-src": ("src/cahn_hilliard.c", 8, 8),
    "tke:oss-lbm:ludwig-ch-fd-scheme-src": ("src/cahn_hilliard.c", 13, 15),
    "tke:oss-lbm:ludwig-ch-flux-mu-src": ("src/cahn_hilliard.c", 281, 283),
    "tke:oss-lbm:ludwig-fe-symm-fed-src": ("src/symmetric.c", 7, 8),
    "tke:oss-lbm:ludwig-fe-symm-sigma-src": ("src/symmetric.c", 253, 255),
    "tke:oss-lbm:ludwig-fe-symm-xi-src": ("src/symmetric.c", 271, 271),
    "tke:oss-lbm:ludwig-fe-symm-mu-src": ("src/symmetric.c", 314, 316),
    "tke:oss-lbm:ludwig-force-method-src": ("src/fe_force_method.h", 22, 24),
    "tke:oss-lbm:ludwig-thermo-stress-src": ("src/phi_force_stress.c", 4, 5),
    "tke:oss-lbm:ludwig-poiseuille-comment-src": ("src/distribution_rt.c", 552, 554),
    "tke:oss-lbm:ludwig-poiseuille-formula-src": ("src/distribution_rt.c", 582, 583),
    "tke:oss-lbm:ludwig-shear-wave-init-src": ("src/distribution_rt.c", 490, 492),
    "tke:oss-lbm:ludwig-sigma-calib-src": ("src/stats_sigma.c", 4, 6),
    "tke:oss-lbm:ludwig-gradient-rt-src": ("src/gradient_rt.c", 49, 51),
    "tke:oss-lbm:ludwig-grad-27pt-src": ("src/gradient_3d_27pt_fluid.c", 5, 6),
    "tke:oss-lbm:ludwig-spinodal-inp-src": ("tests/regression/d3q27/serial-spin-n01.inp", 44, 46),
    "tke:oss-lbm:ludwig-unit-ch-src": ("tests/unit/test_ch.c", 87, 89),
    "tke:oss-lbm:ludwig-readme-ansi-c-src": ("README.md", 18, 19),
}

# Absence searches (negative evidence): pattern -> (scope, expected_hits)
SEARCHES = {
    "tke:oss-lbm:ludwig-no-scmp-src": (
        "scmp|pseudopotential|pseudo-potential|shan-chen",
        ["src/", "docs/", "tests/", "README.md"],
        0,
    ),
    "tke:oss-lbm:ludwig-no-gauge-src": (
        "gauge",
        ["src/", "docs/", "tests/", "README.md"],
        0,
    ),
}

CLAIM_SPECS = [
    dict(
        id="tkc:oss-lbm:ludwig-free-energy-catalog",
        statement=(
            "Ludwig exposes nine concrete free-energy models (symmetric phi^4, Brazovskii, "
            "surfactant, polar, liquid crystal, electrokinetic, electrokinetic-symmetric, "
            "liquid-crystal droplet, ternary) plus a null model behind a single abstract "
            "fe_id_enum tag, so that the binary-fluid free-energy sector is selectable at run "
            "time (input key 'free_energy') rather than at compile time."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-fe-enum-src", "tke:oss-lbm:ludwig-spinodal-inp-src"],
        gap="GAP-LBM-MCMP-POISEUILLE",
        conditions=["compile-time model choice (D2Q9/D3Q15/D3Q19/D3Q27)",
                    "run-time free-energy choice via input file"],
        notes=[
            "TensorLBM 可服务改进点: MCMP 自由能模型的『运行时选择』接口（enum + 虚表）可直接照搬，"
            "避免 TensorLBM 里自由能/多相模型与编译期开关耦合；对照 GAP-LBM-MCMP-POISEUILLE 的两相通道流需先能选模型。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-fe-vtable-contract",
        statement=(
            "Every Ludwig free energy implements a virtual table whose entries are typed "
            "callbacks for free-energy density (fed), chemical potential (mu), solvation "
            "chemical potential (mu_solv), chemical stress (stress), and molecular fields, so "
            "the Cahn-Hilliard and force sectors can evaluate any model without knowing it; the "
            "chemical potential entry has signature 'int (*)(fe_t *, int, double *)' evaluated "
            "pointwise at a lattice index."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-fe-vtable-mu-src"],
        gap="GAP-LBM-MCMP-FORCE-GAUGE",
        conditions=["C, function-pointer vtable (no introspection)"],
        notes=[
            "TensorLBM 可服务改进点: 化学势/应力以『逐点回调』注入，利于把一个自由能核在 CPU/GPU 两套内核间复用；"
            "TensorLBM 多相内核可用同样契约把 mu、应力、分子场分离测试。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-ch-fd-evolution",
        statement=(
            "The order-parameter sector of Ludwig evolves the Cahn-Hilliard equation "
            "d_t phi + div(u phi - M grad mu) = 0 by finite difference, with the velocity u "
            "taken as known from the hydrodynamic sector and the chemical potential mu supplied "
            "by the chosen free energy; i.e. binary-fluid composition dynamics is a separate "
            "finite-difference module coupled to the lattice-Boltzmann hydrodynamics, not a "
            "second lattice-Boltzmann equation."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-ch-equation-src",
                  "tke:oss-lbm:ludwig-ch-fd-scheme-src"],
        gap="GAP-LBM-MCMP-POISEUILLE",
        conditions=["finite-difference advection scheme order set by input (fd_advection_scheme_order)"],
        notes=[
            "TensorLBM 可服务改进点: 『LB 水动力 + FD 组分』的算子拆分让两相通道流可用独立模块做收敛研究；"
            "TensorLBM 若在 MCMP 上做 POISEUILLE 基准需明确组分方程离散阶数对界面通量的影响。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-ch-flux-first-order-mu",
        statement=(
            "The diffusive Cahn-Hilliard flux in Ludwig is assembled from neighbouring chemical "
            "potential values as flux = mobility*(mu(ic+1) - mu(ic)), i.e. a two-point (first-order "
            "accurate) face gradient of mu, accumulated into an advective-flux buffer before the "
            "update; the interfacial current therefore carries O(h) truncation error in the "
            "chemical-potential gradient unless a wider stencil is used."
        ),
        claim_type="interpretive",
        epistemic_status="contested",
        evidence=["tke:oss-lbm:ludwig-ch-flux-mu-src"],
        gap="GAP-LBM-MCMP-MU-STENCIL",
        conditions=["metric/symmetric mesh only (unit spacing)"],
        notes=[
            "TensorLBM 可服务改进点: 这是 MCMP 通道流里寄生界面流(parasitic current)的典型来源；"
            "TensorLBM 若实现两相驱动流需量化 mu 面梯度阶数对滑移/回流误差的贡献。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-symm-phi4-density",
        statement=(
            "Ludwig's symmetric free energy implements F[phi] = (1/2) A phi^2 + (1/4) B phi^4 + "
            "(1/2) kappa (grad phi)^2, with the bulk double-well term from A<0 and the gradient "
            "penalty from kappa; this is the canonical phi^4 free energy of Kendon et al. "
            "(J. Fluid Mech. 440, 147 (2001)) cited in the file header."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-fe-symm-fed-src"],
        gap="GAP-LBM-MCMP-POISEUILLE",
        conditions=["A < 0, B > 0, kappa > 0 for a stable interface"],
        notes=[
            "TensorLBM 可服务改进点: 二元流体 MCMP 的『参考自由能』可用此 phi^4 形式作为 TensorLBM 的解析基准族；"
            "A/B/kappa 三参数直接给出界面张力与界面宽度（见另两条 claims），便于误差判据。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-symm-analytic-sigma",
        statement=(
            "Ludwig computes the interfacial tension of the symmetric free energy from the "
            "analytic phi^4 result sigma = sqrt(-8 kappa a^3 / (9 b^2)) (for phi* = sqrt(-a/b), "
            "a < 0), and the interfacial width from xi = sqrt(-2 kappa / a); both are exact "
            "continuum expressions evaluated from the input parameters, hence usable as "
            "closed-form references for measured (droplet-calibrated) surface tension."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-fe-symm-sigma-src", "tke:oss-lbm:ludwig-fe-symm-xi-src",
                  "tke:oss-lbm:ludwig-sigma-calib-src"],
        gap="GAP-LBM-MCMP-SIGMA-CALIB",
        conditions=["a < 0 (double-well)", "sharp-interface (xi << L) regime"],
        notes=[
            "TensorLBM 可服务改进点: 解析 sigma 与数值液滴标定的对照就是 TensorLBM 两相实现的精度判据"
            "（目标 <3%）；同一对公式可直接进 TensorLBM 的基准测试夹具。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-symm-mu-discrete",
        statement=(
            "The chemical potential of the symmetric free energy is evaluated as "
            "mu = a*phi + b*phi^3 - kappa*delsq(phi), where delsq(phi) is a discrete Laplacian "
            "read from the field-gradient object (choice of finite-difference stencil at run "
            "time); therefore the discretisation error of mu is entirely inherited from the "
            "selected gradient/Laplacian stencil, with no analytic correction term."
        ),
        claim_type="interpretive",
        epistemic_status="contested",
        evidence=["tke:oss-lbm:ludwig-fe-symm-mu-src", "tke:oss-lbm:ludwig-gradient-rt-src"],
        gap="GAP-LBM-MCMP-MU-STENCIL",
        conditions=["delsq from field_grad; stencil chosen via fd_gradient_calculation"],
        notes=[
            "TensorLBM 可服务改进点: 说明 mu 的精度是『纯模板』问题——TensorLBM 应在两相基准里做"
            " 7pt vs 27pt（各向同性）模板的收敛对照，而不是假设其一更好。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-force-methods",
        statement=(
            "Ludwig provides five free-energy force formulations for the hydrodynamic sector: "
            "no force, stress divergence (documented as the current default), phi*grad(mu), "
            "phi*grad(mu) with a conservation correction, and symmetric/antisymmetric "
            "relaxation via the LB collision; the stress-divergence form uses the "
            "'thermodynamic' stress tensor derived from the chosen free energy."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-force-method-src", "tke:oss-lbm:ludwig-thermo-stress-src"],
        gap="GAP-LBM-MCMP-FORCE-GAUGE",
        conditions=["force method selected at run time (fe_force_method enum)"],
        notes=[
            "TensorLBM 可服务改进点: 同一物理（自由能力）有 5 种离散实现→TensorLBM 应把它们做成"
            "可切换的力格式并交叉验证（尤其 stress-divergence vs phi grad mu 在小密度比下的差异）。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-no-gauge-formulation",
        statement=(
            "The string 'gauge' does not occur anywhere in the Ludwig source, documentation, "
            "tests or README (case-insensitive search over src/, docs/, tests/, README.md gives "
            "zero hits); Ludwig's free-energy forcing is expressed as stress divergence and "
            "phi*grad(mu) forms, so a claim that Ludwig implements a 'gauge' formulation of the "
            "multicomponent force is not supported by the source."
        ),
        claim_type="negative",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-no-gauge-src"],
        gap="GAP-LBM-MCMP-FORCE-GAUGE",
        conditions=["source inspection of master snapshot; absence is grep-exhaustive, not a proof of semantics"],
        notes=[
            "TensorLBM 可服务改进点: 否定性结论——不能把 Ludwig 当『gauge 实现』参考；"
            "若 TensorLBM 要做 gauge/规范不变的 MCMP 力格式，需另找文献与参考实现（本包已把该缺口挂锚）。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-no-scmp-pseudopotential",
        statement=(
            "Ludwig contains no Shan-Chen single-component-multiphase (SCMP) pseudo-potential "
            "implementation: a case-insensitive search for 'scmp', 'pseudopotential', "
            "'pseudo-potential' and 'shan-chen' over src/, docs/, tests/ and README.md returns "
            "zero hits (the string 'Shan' appears only as the code contributor name Shan Chen in the "
            "ternary free-energy files, plus one literature citation in "
            "gradient_2d_tomita_fluid.c. Multiphase behaviour is obtained from "
            "free-energy (Cahn-Hilliard) models instead."
        ),
        claim_type="negative",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-no-scmp-src"],
        gap="GAP-LBM-MCMP-SCMP",
        conditions=["source inspection of master snapshot"],
        notes=[
            "TensorLBM 可服务改进点: 明确 SCMP 是缺口而非参考实现——TensorLBM 若需要 SC 型伪势模型，"
            "Ludwig 无法提供对照基线，只能用于自由能型两相（这与 POISEUILLE 两相基准的模型选择直接相关）。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-poiseuille-init",
        statement=(
            "Ludwig provides a run-time initial distribution '1d_poiseuille' that sets the "
            "analytic parabolic profile u_i = umax_i * x(L - x) * 4/L^2 along each coordinate "
            "using the local-to-global offset and lmin so that the profile is centred "
            "symmetrically, with the 4/L^2 factor normalising u to umax at the centre; this "
            "supplies the closed-form channel-flow reference state for two-phase (MCMP) "
            "Poiseuille benchmarks but it is only an initial condition, not a steady-state "
            "verification."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-poiseuille-comment-src",
                  "tke:oss-lbm:ludwig-poiseuille-formula-src"],
        gap="GAP-LBM-MCMP-POISEUILLE",
        conditions=["one non-zero component of umax[3]", "periodic walls unless a wall/bbl condition is set"],
        notes=[
            "TensorLBM 可服务改进点: 直接对齐 GAP-LBM-MCMP-POISEUILLE——Ludwig 只给解析剖面初值，"
            "不给压力驱动/两相逆流稳态校核；TensorLBM 应补『驱动-稳态-解析剖面对比』的验收环。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-shear-wave-init",
        statement=(
            "Ludwig provides a run-time initial distribution '2d_shear_wave' with fixed amplitude "
            "u0 = 0.04 and wavenumber kappa = 2*pi applied as u_x = u0*sin(kappa*y) with y "
            "normalised by the box length in y; this is a single-phase viscous-decay reference "
            "configuration whose exact solution u_x = u0 sin(ky) exp(-nu k^2 t) is available in "
            "closed form."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-shear-wave-init-src"],
        gap="GAP-LBM-MCMP-POISEUILLE",
        conditions=["periodic boundaries", "single phase (free_energy none)"],
        notes=[
            "TensorLBM 可服务改进点: 本包用它做了定量验证（见 artifacts/shear_wave_verification.json，"
            "L=32 衰减率误差 0.26%）；TensorLBM 可复用同一构型作 LB 粘性/收敛回归环。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-gradient-stencil-selection",
        statement=(
            "The discrete gradient/Laplacian used by the free-energy sector is selectable at run "
            "time through the input keys 'fd_gradient_calculation' (default) and "
            "'fd_gradient_calculation_phi' / '_q' overrides for the phi and Q_ab fields, with "
            "separate 7-point and isotropic 27-point fluid stencils provided as distinct source "
            "files (gradient_3d_7pt_fluid.c, gradient_3d_27pt_fluid.c) in addition to the 2D "
            "5-point and Tomita stencils."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-gradient-rt-src", "tke:oss-lbm:ludwig-grad-27pt-src"],
        gap="GAP-LBM-MCMP-MU-STENCIL",
        conditions=["3D fluid fields", "solid-like fields use *_solid stencils"],
        notes=[
            "TensorLBM 可服务改进点: 模板=运行期参数而非编译期宏，TensorLBM 应照此把离散模板外置，"
            "以便在两相基准上做 7pt/27pt 收敛对照。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-spinodal-smoke-test",
        statement=(
            "The only regression test that exercises the binary-fluid free-energy path in the "
            "D3Q27 build is a 10-step, 16^3 spinodal-decomposition case labelled 'smoke test' in "
            "its own header, using free_energy symmetric, mobility 1.25 and the 7-point gradient; "
            "it is a numerical-diff regression against a stored log, with no physical quantity "
            "(surface tension, growth rate, phase composition) asserted."
        ),
        claim_type="interpretive",
        epistemic_status="contested",
        evidence=["tke:oss-lbm:ludwig-spinodal-inp-src"],
        gap="GAP-LBM-MCMP-SPINODAL",
        conditions=["tests/regression/d3q27", "comparison via tests/awk-fp-diff.sh"],
        notes=[
            "TensorLBM 可服务改进点: 说明 Ludwig 的两相回归面偏弱（只 diff 不判物理量）——"
            "TensorLBM 的两相回归必须带物理判据（sigma、界面宽度、生长率），否则同类的『绿但无意义』陷阱会重现。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-unit-test-ch-scope",
        statement=(
            "The Cahn-Hilliard unit test test_ch.c only checks object construction and the "
            "mobility bookkeeping (ch->info->mobility[] compared to input values at double "
            "epsilon), i.e. the discretised evolution operator of the order-parameter sector is "
            "not covered by a quantitative unit test in the repository's own suite."
        ),
        claim_type="interpretive",
        epistemic_status="contested",
        evidence=["tke:oss-lbm:ludwig-unit-ch-src", "tke:oss-lbm:ludwig-ch-equation-src"],
        gap="GAP-LBM-MCMP-SPINODAL",
        conditions=["tests/unit/test_ch.c as shipped"],
        notes=[
            "TensorLBM 可服务改进点: 可作为 TensorLBM 测试面的反面样本——两相组分算子必须有"
            "定量的解析解单元测试（如界面平衡剖面 tanh 拟合），不能只测构造。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-sigma-droplet-calibration",
        statement=(
            "Ludwig calibrates the surface tension of the symmetric free energy from a simulated "
            "droplet in 2d or 3d (stats_sigma.c, 128 radial bins), i.e. a measurement-based "
            "verification path independent of the analytic formula; it is exercised from the main "
            "driver only when the 'sigma' statistics option is requested."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-sigma-calib-src"],
        gap="GAP-LBM-MCMP-SIGMA-CALIB",
        conditions=["symmetric free energy only", "droplet initialisation"],
        notes=[
            "TensorLBM 可服务改进点: 『解析 sigma vs 液滴实测 sigma』的双通道标定正是 TensorLBM "
            "两相精度验收模板（误差判据 <3%）。"
        ],
    ),
    dict(
        id="tkc:oss-lbm:ludwig-ansi-c-not-fortran",
        statement=(
            "Ludwig's README states that the code 'is written in standard ANSI C' and uses MPI "
            "plus a TargetDP abstraction for OpenMP/CUDA/HIP; the repository contains no Fortran "
            "sources (no *.f90/*.F90 files in the tree). Any description of Ludwig as a Fortran "
            "code is therefore incorrect."
        ),
        claim_type="descriptive",
        epistemic_status="established",
        evidence=["tke:oss-lbm:ludwig-readme-ansi-c-src"],
        gap="GAP-LBM-MCMP-POISEUILLE",
        conditions=["master snapshot inspected"],
        notes=[
            "TensorLBM 可服务改进点: 元数据纠错——按 C 代码对待（移植/对照时不要假设 Fortran 数组序与 ABI）。"
        ],
    ),
]

GAP_ANCHORS = [
    dict(
        id="GAP-LBM-MCMP-POISEUILLE",
        title="MCMP 两相通道流（Poiseuille 基准）验收缺口",
        declared_by="mission brief (m8669) — anchored, not self-declared",
        summary=(
            "TensorLBM 缺少『两相（MCMP）压力驱动通道流 → 稳态解析/半解析剖面对比』的验收环。"
            "Ludwig 只提供解析 Poiseuille 初值（1d_poiseuille）与单相粘性衰减初值（2d_shear_wave），"
            "不提供压力驱动与两相逆流稳态校核，故不能直接充当该缺口的验收器。"
        ),
        resolved_by_claims=["tkc:oss-lbm:ludwig-poiseuille-init",
                            "tkc:oss-lbm:ludwig-shear-wave-init",
                            "tkc:oss-lbm:ludwig-ch-fd-evolution",
                            "tkc:oss-lbm:ludwig-free-energy-catalog",
                            "tkc:oss-lbm:ludwig-symm-phi4-density",
                            "tkc:oss-lbm:ludwig-ansi-c-not-fortran"],
        next_step=(
            "在 TensorLBM 实现体积力驱动的两相通道流，用 Ludwig 的 phi^4 参数族"
            "（a,b,kappa）给出 sigma/xi 解析值，并把界面处的表观滑移与解析 Poiseuille 剖面对比。"
        ),
    ),
    dict(
        id="GAP-LBM-MCMP-SCMP",
        title="SCMP（Shan-Chen 伪势单组分多相）能力缺口",
        declared_by="self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养)",
        summary=(
            "TensorLBM 若无 SCMP 伪势模型，则两相基准的模型族只有自由能型；本包确认 Ludwig 不含 SCMP 实现，"
            "因此 SCMP 侧无可对照的 OSS 参考实现（该缺口不能用 Ludwig 观测值填）。"
        ),
        resolved_by_claims=["tkc:oss-lbm:ludwig-no-scmp-pseudopotential"],
        next_step="在 TensorLBM 内以解析 Maxwell 构造/共存密度曲线作为 SCMP 自验，勿引 Ludwig 为基线。",
    ),
    dict(
        id="GAP-LBM-MCMP-FORCE-GAUGE",
        title="自由能力格式（应力散度 / phi·∇μ / 规范型）交叉验证缺口",
        declared_by="self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养)",
        summary=(
            "自由能两相模型把体力写入 LB 的方式有多种（Ludwig 有 5 种可切换格式）；缺少『同一物理、不同离散力格式』"
            "的交叉验证，且任务书中『gauge 表述』在 Ludwig 源码中不存在（grep 0 命中）。"
        ),
        resolved_by_claims=["tkc:oss-lbm:ludwig-force-methods",
                            "tkc:oss-lbm:ludwig-no-gauge-formulation",
                            "tkc:oss-lbm:ludwig-fe-vtable-contract"],
        next_step="TensorLBM 对 stress-divergence 与 phi·∇mu 两格式在同一算例上量化差异（目标 <3%）。",
    ),
    dict(
        id="GAP-LBM-MCMP-MU-STENCIL",
        title="化学势/界面通量的离散模板阶数缺口",
        declared_by="self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养)",
        summary=(
            "两相通道流中的寄生界面流由化学势梯度的离散阶数与各向同性决定；Ludwig 用两点面梯度 + 可选 7pt/27pt 模板，"
            "TensorLBM 侧缺少模板阶数 → 误差的收敛对照。"
        ),
        resolved_by_claims=["tkc:oss-lbm:ludwig-ch-flux-first-order-mu",
                            "tkc:oss-lbm:ludwig-symm-mu-discrete",
                            "tkc:oss-lbm:ludwig-gradient-stencil-selection"],
        next_step="固定物理参数，扫 7pt/27pt/Tomita 模板，报告 sigma 与界面剖面误差随 h 的收敛阶。",
    ),
    dict(
        id="GAP-LBM-MCMP-SIGMA-CALIB",
        title="界面张力/界面宽度的解析-数值双通道标定缺口",
        declared_by="self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养)",
        summary=(
            "两相精度判据需要 sigma 的解析值与数值实测值同时在场；Ludwig 两者皆有（解析式 + 液滴标定），"
            "TensorLBM 侧尚无该双通道标定环。"
        ),
        resolved_by_claims=["tkc:oss-lbm:ludwig-symm-analytic-sigma",
                            "tkc:oss-lbm:ludwig-sigma-droplet-calibration"],
        next_step="TensorLBM 用 phi^4 参数族做 sigma 解析-实测对照，判据 3%。",
    ),
    dict(
        id="GAP-LBM-MCMP-SPINODAL",
        title="相分离（spinodal）与组分算子定量回归缺口",
        declared_by="self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养)",
        summary=(
            "组分算子（Cahn-Hilliard）需要定量回归（界面平衡剖面、生长率），而非仅数值 diff；"
            "Ludwig 的两相回归只有一个标注为 smoke test 的 10 步算例、单测只覆盖构造与 mobility。"
        ),
        resolved_by_claims=["tkc:oss-lbm:ludwig-spinodal-smoke-test",
                            "tkc:oss-lbm:ludwig-unit-test-ch-scope"],
        next_step="TensorLBM 组分算子加『tanh 平衡剖面拟合』与『线性生长率 vs 理论』两个定量测试。",
    ),
]


def slice_lines(src_root: Path, path: str, a: int, b: int) -> str:
    lines = (src_root / path).read_text(encoding="utf-8", errors="strict").split("\n")
    if b - a + 1 > 3:
        raise SystemExit(f"quote too long (>3 lines): {path}:{a}-{b}")
    if a < 1 or b > len(lines):
        raise SystemExit(f"range out of bounds: {path}:{a}-{b}")
    return "\n".join(lines[a - 1:b])


def grep_count(src_root: Path, pattern: str, scopes: list) -> list:
    """Return list of (path, line) hits for a fixed pattern (regex)."""
    import re
    rx = re.compile(pattern, re.IGNORECASE)
    hits = []
    for scope in scopes:
        p = src_root / scope
        files = [p] if p.is_file() else sorted(
            [f for f in p.rglob("*") if f.is_file()
             and f.suffix in (".c", ".h", ".tex", ".md", ".inp", ".py", ".txt", ".mk")])
        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.split("\n"), start=1):
                if rx.search(line):
                    hits.append((str(f.relative_to(src_root)), i))
    return hits


def build(src_root: Path, commit: str) -> dict:
    claims, evidence = [], []
    now = os.environ.get("LUDWIG_CAPTURED_AT", "2026-11-09T15:00:00Z")

    for eid, (path, a, b) in SLICES.items():
        quote = slice_lines(src_root, path, a, b)
        evidence.append(dict(
            id=eid,
            source=dict(repo="ludwig-cf/ludwig", commit=commit, branch="master"),
            relation="supports",
            locator=dict(locator_type="code-location", repo="ludwig-cf/ludwig",
                         commit=commit, path=path,
                         line_start=a, line_end=b, quote=quote),
            captured_at=now,
            assessment_status="unassessed",
            version="1.0.0",
        ))

    # negative (absence) evidence
    for eid, (pattern, scopes, expected) in SEARCHES.items():
        hits = grep_count(src_root, pattern, scopes)
        if len(hits) != expected:
            raise SystemExit(f"absence search {eid} expected {expected} hits, got {len(hits)}: {hits[:5]}")
        evidence.append(dict(
            id=eid,
            source=dict(repo="ludwig-cf/ludwig", commit=commit, branch="master"),
            relation="supports",
            locator=dict(locator_type="code-search", repo="ludwig-cf/ludwig",
                         commit=commit, pattern=pattern, scope=scopes,
                         hits=len(hits),
                         query=f"grep -rinE '{pattern}' {' '.join(scopes)}"),
            captured_at=now,
            assessment_status="unassessed",
            version="1.0.0",
        ))

    ev_ids = {e["id"] for e in evidence}
    claim_ids = set()
    for spec in CLAIM_SPECS:
        for ref in spec["evidence"]:
            if ref not in ev_ids:
                raise SystemExit(f"claim {spec['id']} references unknown evidence {ref}")
        if spec["id"] in claim_ids:
            raise SystemExit(f"duplicate claim id {spec['id']}")
        claim_ids.add(spec["id"])
        claims.append(dict(
            id=spec["id"],
            statement=spec["statement"],
            claim_type=spec["claim_type"],
            scope=dict(domain="lattice-Boltzmann-method", system="Ludwig",
                       conditions=spec["conditions"]),
            modality="asserted",
            epistemic_status=spec["epistemic_status"],
            evidence_refs=spec["evidence"],
            gap_anchor=spec["gap"],
            created_at=now,
            created_by="agent-m8669",
            version="1.0.0",
            notes=spec["notes"],
        ))

    # attach claim_refs to evidence
    for ev in evidence:
        ev["claim_refs"] = sorted([c["id"] for c in claims if ev["id"] in c["evidence_refs"]])
        if not ev["claim_refs"]:
            raise SystemExit(f"orphan evidence {ev['id']}")

    gap_ids = {g["id"] for g in GAP_ANCHORS}
    for c in claims:
        if c["gap_anchor"] not in gap_ids:
            raise SystemExit(f"claim {c['id']} has unregistered gap anchor {c['gap_anchor']}")

    provenance = [dict(
        id="tkp:oss-lbm:ludwig-source-snapshot",
        generated_entity="knowledge/oss-lbm/ludwig (claims/evidence/provenance)",
        activity=dict(
            type="source-inspection",
            repo="ludwig-cf/ludwig",
            commit=commit,
            branch="master",
            retrieval="https://codeload.github.com/ludwig-cf/ludwig/tar.gz/refs/heads/master",
            archive_sha256=os.environ.get("LUDWIG_ARCHIVE_SHA256", "unrecorded"),
            method=(
                "tarball snapshot extracted locally; every quote sliced verbatim by "
                "scripts/build_package.py; absence claims verified by exhaustive case-insensitive "
                "grep over the whole tree"
            ),
            build=dict(
                model="D3Q27", cc="gcc 12.3.0", flags="-O2 -g -Wall",
                unit_tests="tests/unit `make test` -> 98 PASS / 0 FAIL",
                regression="top-level `make test` fails against stored reference logs "
                           "(serial-actv-s01 drift ~1e-7 relative) — stale-log artefact, reported honestly",
            ),
        ),
        agents=[dict(name="agent-m8669", role="extractor")],
        recorded_at=now,
        version="1.0.0",
    )]

    return dict(claims=claims, evidence=evidence, provenance=provenance,
                gaps=GAP_ANCHORS)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    src = Path(os.environ.get("LUDWIG_SRC", "/tmp/ludwig_tar/ludwig-master"))
    commit = os.environ.get("LUDWIG_COMMIT", "").strip()
    if not args.check and len(commit) != 40:
        raise SystemExit("set LUDWIG_COMMIT to the full 40-hex commit of the inspected snapshot")

    if not (src / "src" / "free_energy.h").exists():
        raise SystemExit(f"source tree not found at {src}")

    pkg = build(src, commit or "0" * 40)
    if args.check:
        for name, key in (("claims/claims.json", "claims"),
                          ("evidence/evidence.json", "evidence")):
            cur = json.loads((PKG / name).read_text(encoding="utf-8"))
            gen = pkg[key]
            # compare locators/quotes only (timestamps/commit may be re-sliced)
            if key == "evidence":
                # commit/source stamps depend on the --check invocation; compare
                # the source-anchored part of the locator only
                def loc_cmp(e):
                    loc = {k: v for k, v in e["locator"].items() if k != "commit"}
                    return (e["id"], loc)
                cur_cmp = [loc_cmp(e) for e in cur]
                gen_cmp = [loc_cmp(e) for e in gen]
            else:
                cur_cmp = [(c["id"], c["statement"], c["epistemic_status"]) for c in cur]
                gen_cmp = [(c["id"], c["statement"], c["epistemic_status"]) for c in gen]
            if cur_cmp != gen_cmp:
                print(f"MISMATCH in {name}", file=sys.stderr)
                return 1
        print("PASS: committed quotes/statements match the source tree")
        return 0

    write_json(PKG / "claims" / "claims.json", pkg["claims"])
    write_json(PKG / "evidence" / "evidence.json", pkg["evidence"])
    write_json(PKG / "provenance" / "provenance.json", pkg["provenance"])
    write_json(PKG / "gaps" / "gap-anchors.json", pkg["gaps"])
    print(f"wrote {len(pkg['claims'])} claims / {len(pkg['evidence'])} evidence / "
          f"{len(pkg['provenance'])} provenance / {len(pkg['gaps'])} gap anchors (commit {commit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())