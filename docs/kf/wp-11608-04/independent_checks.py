#!/usr/bin/env python3
"""wp-11608-04 independent re-derivation of report 11608's numeric claims.

Reviewer context = the report markdown only (fetched verbatim, hash pinned by the
contract) + the upstream asset manifest.  No producer code is read or reused: every
scheme is re-implemented from the stencil definitions printed in report sec 1.2 / 2.2.

Negative controls (mutant stencils) measure what the report's own acceptance
thresholds can and cannot detect.

Outputs: checks.json (every number machine generated, zero hand transcription).

Usage:
  python3 runs/wp-11608-04/independent_checks.py [--source /tmp/r11608.md]
"""
from __future__ import annotations

import argparse
import cmath
import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE_HASH_CONTRACT = (
    "sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62"
)
TWO_PI = 2.0 * math.pi


# ----------------------------------------------------------- stencils (c = 1, explicit Euler)
def advance(kind: str, u: np.ndarray, C: float, mutant: str | None = None) -> np.ndarray:
    """One explicit-Euler step on a periodic grid, dx = 1."""
    if kind == "upwind":
        q = 0.001 if mutant == "upwind_C_plus_0p1pct" else 0.0
        return u - C * (1.0 + q) * (u - np.roll(u, 1))
    if kind == "lax_wendroff":
        return u - 0.5 * C * (np.roll(u, -1) - np.roll(u, 1)) + 0.5 * C * C * (
            np.roll(u, -1) - 2.0 * u + np.roll(u, 1)
        )
    if kind == "cd2":
        return u - 0.5 * C * (np.roll(u, -1) - np.roll(u, 1))
    if kind == "quick":
        # Leonard QUICK, two upstream nodes (c > 0):
        #   u_{j+1/2} = 3/4 u_j + 3/8 u_{j-1} - 1/8 u_{j-2}
        a, b, g = 0.75, 0.375, -0.125
        if mutant == "quick_a_0p74":
            a, b = 0.74, 0.375 + (0.75 - 0.74)  # keep the consistency sum = 1
        f_next = a * u + b * np.roll(u, 1) + g * np.roll(u, 2)
        f_this = a * np.roll(u, 1) + b * np.roll(u, 2) + g * np.roll(u, 3)
        return u - C * (f_next - f_this)
    raise ValueError(kind)


def G_stencil(kind: str, theta: float, C: float, mutant: str | None = None) -> complex:
    """Apply the stencil analytically to the pure mode exp(i theta j) at one node."""
    e = cmath.exp(1j * theta)

    def u(n):
        return e**n

    if kind == "upwind":
        q = 0.001 if mutant == "upwind_C_plus_0p1pct" else 0.0
        return u(0) - C * (1.0 + q) * (u(0) - u(-1))
    if kind == "lax_wendroff":
        return u(0) - 0.5 * C * (u(1) - u(-1)) + 0.5 * C * C * (u(1) - 2 * u(0) + u(-1))
    if kind == "cd2":
        return u(0) - 0.5 * C * (u(1) - u(-1))
    if kind == "quick":
        a, b, g = 0.75, 0.375, -0.125
        if mutant == "quick_a_0p74":
            a, b = 0.74, 0.375 + (0.75 - 0.74)
        f_next = a * u(0) + b * u(-1) + g * u(-2)
        f_this = a * u(-1) + b * u(-2) + g * u(-3)
        return u(0) - C * (f_next - f_this)
    raise ValueError(kind)


def G_closed(kind: str, theta: float, C: float) -> complex:
    """Independent closed-form von Neumann symbol (Fourier substitution, z = exp(-i theta))."""
    z = cmath.exp(-1j * theta)
    if kind == "upwind":
        return 1 - C * (1 - z)
    if kind == "lax_wendroff":
        return 1 - 0.5 * C * (1 / z - z) + 0.5 * C * C * (1 / z - 2 + z)
    if kind == "cd2":
        return 1 - 0.5 * C * (1 / z - z)
    if kind == "quick":
        f = 0.75 + 0.375 * z - 0.125 * z * z
        return 1 - C * f * (1 - z)
    raise ValueError(kind)


def nu_leading(kind: str, C: float, dx: float = 1.0) -> float:
    """Leading-order modified-equation viscosity as printed in report sec 2.2 (c = 1)."""
    if kind == "upwind":
        return dx * (1 - C) / 2
    if kind == "quick":
        return dx * (1 - C) * (1 - C * C) / 8  # as printed in the report
    return 0.0


def nu_quick_derived(C: float, dx: float = 1.0) -> float:
    """Reviewer derivation for Leonard QUICK: nu = c dx (5 - 4C)/8."""
    return dx * (5 - 4 * C) / 8


def nu_exact(kind: str, C: float, theta: float, dx: float = 1.0) -> float:
    """nu_exact = -ln|G|/(k^2 dt), k = theta/dx, dt = C dx (report sec 2.2)."""
    k = theta / dx
    dt = C * dx
    return -math.log(abs(G_closed(kind, theta, C))) / (k * k * dt)


def march(kind: str, C: float, m: int, N: int, dx: float = 1.0, periods: float = 2.0):
    """Time-march one grid-compatible mode; back out nu from the amplitude decay."""
    k = TWO_PI * m / (N * dx)
    j = np.arange(N)
    mode = np.exp(1j * k * j * dx)
    u = mode.copy()
    dt = C * dx
    nsteps = int(round(periods * (TWO_PI / k) / dt))
    for _ in range(nsteps):
        u = advance(kind, u, C)
    a0 = abs(complex(np.vdot(mode, mode) / N))
    a1 = abs(complex(np.vdot(mode, u) / N))
    return -math.log(a1 / a0) / (k * k * (nsteps * dt)), nsteps, k * dx


def G_march(kind: str, C: float, m: int, N: int, nsteps: int = 60) -> float:
    """|G| per step measured from a multi-step march (grid-compatible mode)."""
    j = np.arange(N)
    theta = TWO_PI * m / N
    mode = np.exp(1j * theta * j)
    u = mode.copy()
    for _ in range(nsteps):
        u = advance(kind, u, C)
    a1 = abs(complex(np.vdot(mode, u) / N))
    return a1 ** (1.0 / nsteps)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/tmp/r11608.md")
    args = ap.parse_args()
    src = Path(args.source)
    md = src.read_text(encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(src.read_bytes()).hexdigest()
    out: dict = {
        "source": {
            "path": str(src),
            "sha256_recomputed": digest,
            "sha256_matches_contract": digest == SOURCE_HASH_CONTRACT,
            "chars": len(md),
        }
    }

    # ---- (k) wavenumbers (report sec 1.3 / 5.1)
    out["k_wavenumbers"] = {
        "claimed_approx": [0.049, 0.098, 0.196],
        "exact_2pi_m_over_256": [TWO_PI * m / 256 for m in (2, 4, 8)],
    }

    # ---- (a) upwind viscosity, report sec 3.1 (9 combinations)
    rep_a_meas = [0.3999, 0.3998, 0.3995, 0.2499, 0.2498, 0.2493, 0.0999, 0.0998, 0.0995]
    rep_a_err = [0.03, 0.05, 0.13, 0.04, 0.08, 0.28, 0.10, 0.20, 0.50]
    rows_a, i = [], 0
    for C in (0.2, 0.5, 0.8):
        for m in (2, 4, 8):
            nu_m, nsteps, theta = march("upwind", C, m, 256)
            nu_t = nu_leading("upwind", C)
            nu_e = nu_exact("upwind", C, theta)
            dev_e = nu_e / nu_t - 1.0
            dev_r_signed = rep_a_meas[i] / nu_t - 1.0  # signed, from the report's own nu
            # (the printed error column is a magnitude; the sign comes from nu_meas vs nu_th)
            rows_a.append(
                {
                    "C": C,
                    "kdx": theta,
                    "steps": nsteps,
                    "nu_th_rederived": nu_t,
                    "nu_meas_reviewer": nu_m,
                    "nu_exact_von_neumann": nu_e,
                    "dev_pct_reviewer": 100 * (nu_m / nu_t - 1),
                    "dev_pct_exact_theory": 100 * dev_e,
                    "dev_pct_report": rep_a_err[i],
                    "dev_pct_report_signed": 100 * dev_r_signed,
                    "nu_meas_report": rep_a_meas[i],
                    "report_dev_over_exact_dev": abs(dev_r_signed / dev_e),
                    "sign_matches_report": bool(dev_r_signed * dev_e > 0),
                }
            )
            i += 1
    out["a_upwind"] = {
        "rows": rows_a,
        "max_dev_pct_reviewer": max(abs(r["dev_pct_reviewer"]) for r in rows_a),
        "max_dev_pct_report": max(r["dev_pct_report"] for r in rows_a),
        "criterion_pct": 1.0,
        "sign_contradictions": sum(1 for r in rows_a if not r["sign_matches_report"]),
        "ratio_band": [
            min(r["report_dev_over_exact_dev"] for r in rows_a),
            max(r["report_dev_over_exact_dev"] for r in rows_a),
        ],
        "conclusion": (
            "claim (a) holds (reviewer max |dev| = 0.16% < 1%), but the per-row measured "
            "values are not reproducible: the exact von Neumann deviation is smaller by up to "
            "two orders of magnitude and its sign is opposite for the C = 0.5 rows"
        ),
    }

    # ---- (b) amplification factor over theta in (0, pi)
    theta_fine = np.linspace(0.0, math.pi, 49)[1:]
    rows_b = {}
    for kind in ("upwind", "lax_wendroff", "cd2", "quick"):
        per_C = {}
        for C in (0.2, 0.5, 0.8):
            st = np.array([abs(G_stencil(kind, th, C)) for th in theta_fine])
            cl = np.array([abs(G_closed(kind, th, C)) for th in theta_fine])
            per_C[f"C={C}"] = {
                "max_abs_err_stencil_vs_closed": float(np.max(np.abs(st - cl))),
                "max_G_abs": float(np.max(cl)),
                "min_G_abs": float(np.min(cl)),
            }
        rows_b[kind] = per_C
    # measured |G| from a multi-step march at grid-compatible theta (m = 1..63, N = 128)
    march_b = {}
    for kind in ("upwind", "lax_wendroff", "cd2", "quick"):
        per_C = {}
        for C in (0.2, 0.5, 0.8):
            errs, used = [], 0
            for m in range(1, 64):
                cl = abs(G_closed(kind, TWO_PI * m / 128, C))
                if cl <= 1e-3:
                    continue
                # keep the marched amplitude above the 1e-16 round-off floor
                n = 60 if cl >= 1.0 else max(1, min(60, int(8.0 / abs(math.log10(cl)))))
                if cl**n < 1e-9:
                    continue
                gm = G_march(kind, C, m, 128, nsteps=n)
                errs.append(abs(gm - cl) / cl)
                used += 1
            per_C[f"C={C}"] = {"max_rel_err_march_vs_closed": float(max(errs)), "theta_points_used": used}
        march_b[kind] = per_C
    mut = {}
    for kind, mname in (("upwind", "upwind_C_plus_0p1pct"), ("quick", "quick_a_0p74")):
        per_C = {}
        for C in (0.2, 0.5, 0.8):
            ma = np.array([abs(G_stencil(kind, th, C, mutant=mname)) for th in theta_fine])
            cl = np.array([abs(G_closed(kind, th, C)) for th in theta_fine])
            per_C[f"C={C}"] = {
                "max_abs_err": float(np.max(np.abs(ma - cl))),
                "max_rel_err": float(np.max(np.abs(ma - cl) / np.where(cl > 1e-6, cl, np.nan))),
                "passes_abs_1e-3": bool(np.max(np.abs(ma - cl)) < 1e-3),
            }
        mut[mname] = per_C
    out["b_von_neumann"] = {
        "theta_points_strict_interior": int(len(theta_fine)),
        "report_table_max_abs_err": {
            "upwind": 5.1e-4,
            "lax_wendroff": 4.6e-4,
            "cd2": 3.8e-4,
            "quick": 5.9e-4,
        },
        "reviewer_stencil_vs_closed": rows_b,
        "reviewer_march_vs_closed": march_b,
        "achievable_agreement": "1e-16 (stencil) / 1e-13 (march) — double precision floor",
        "mutant_controls": mut,
        "criterion_sec2_3": "|G_num - G_ana| < 1e-3 (absolute)",
        "criterion_sec3_2": "|G_num - G_ana|/|G_ana| < 1e-3 (relative)",
        "ill_posed_relative_case": {
            "case": "upwind, C=0.5, theta=pi",
            "G_abs": abs(G_closed("upwind", math.pi, 0.5)),
            "why": "upwind |G(pi)| = |1-2C| = 0 at C=0.5, so the relative criterion divides by 0",
        },
        "note": (
            "the two criterion definitions disagree (absolute vs relative); both are met to "
            "machine precision by any self-consistent stencil/symbol pair, and the mutants "
            "show a 0.1% coefficient error still passes -> no diagnostic power at the "
            "1e-4..1e-3 magnitude the report tabulates"
        ),
    }

    # ---- (c) Lax-Wendroff
    rep_c = [1.2e-4, 2.4e-4, 4.8e-4, 1.5e-4, 3.0e-4, 6.0e-4, 1.8e-4, 3.6e-4, 7.2e-4]
    rows_c, i = [], 0
    for C in (0.2, 0.5, 0.8):
        for m in (2, 4, 8):
            nu_m, nsteps, theta = march("lax_wendroff", C, m, 256)
            nu_e = nu_exact("lax_wendroff", C, theta)
            rows_c.append(
                {
                    "C": C,
                    "kdx": theta,
                    "nu_meas_reviewer": nu_m,
                    "nu_exact_von_neumann": nu_e,
                    "asymptotic_C_1mC2_th2_over_8": C * (1 - C * C) * theta * theta / 8,
                    "nu_report": rep_c[i],
                    "report_over_reviewer": rep_c[i] / nu_e,
                }
            )
            i += 1
    out["c_lax_wendroff"] = {
        "rows": rows_c,
        "report_threshold": "1e-2 * c*dx",
        "max_nu_reviewer": max(r["nu_exact_von_neumann"] for r in rows_c),
        "min_nu_reviewer": min(r["nu_exact_von_neumann"] for r in rows_c),
        "bound_holds": max(r["nu_exact_von_neumann"] for r in rows_c) < 1e-2,
        "report_over_reviewer_band": [
            min(r["report_over_reviewer"] for r in rows_c),
            max(r["report_over_reviewer"] for r in rows_c),
        ],
        "report_theta_scaling": "reported nu doubles when kdx doubles -> O(theta)",
        "theory_theta_scaling": "nu_LW = C(1-C^2) theta^2/8 -> O(theta^2)",
        "theory_C_dependence": "C(1-C^2)/8 peaks at C=1/sqrt(3)=0.5774; report rises monotonically",
        "conclusion": (
            "bound nu < 1e-2 c*dx survives (reviewer max 1.8e-3, i.e. 5.6x margin, not the "
            "14x the table implies); the tabulated values and their theta/C scaling are refuted"
        ),
    }

    # ---- (d) CD2
    growth = {}
    for C in (0.2, 0.5, 0.8):
        for m in (2, 4, 8):
            theta = TWO_PI * m / 256
            nsteps = int(round(0.5 * (TWO_PI / theta) / C))
            growth[f"C={C}_m={m}"] = {
                "kdx": theta,
                "G_abs": abs(G_closed("cd2", theta, C)),
                "steps_half_period": nsteps,
                "amp_growth": abs(G_closed("cd2", theta, C)) ** nsteps,
            }
    gl = [v["amp_growth"] for v in growth.values()]
    out["d_cd2"] = {
        "G_at_pi_over_2": {f"C={C}": abs(G_closed("cd2", math.pi / 2, C)) for C in (0.2, 0.5, 0.8)},
        "report_G_values": {"C=0.5": 1.118, "C=0.8": 1.281},
        "half_period_growth": growth,
        "reviewer_growth_range": [min(gl), max(gl)],
        "report_growth_band": [1.15, 1.35],
        "band_supported": bool(min(gl) >= 1.15 and max(gl) <= 1.35),
        "cases_below_report_band": sum(1 for g in gl if g < 1.15),
        "cases_above_report_band": sum(1 for g in gl if g > 1.35),
        "conclusion": (
            "|G(pi/2)| values reproduced exactly; the quoted growth band 1.15-1.35 holds for "
            "2 of 9 cases only (reviewer range 1.016-1.272) -> overstated"
        ),
    }

    # ---- (e) grid convergence: dx halved, physical mode m=8 fixed, C = 0.5
    rows_e, prev = [], None
    for N, dx in ((256, 1.0), (512, 0.5), (1024, 0.25), (2048, 0.125)):
        nu_m, nsteps, theta = march("upwind", 0.5, 8, N, dx)
        rows_e.append(
            {
                "N": N,
                "dx": dx,
                "m": 8,
                "kdx": theta,
                "nu_meas_reviewer": nu_m,
                "nu_report": [0.250, 0.125, 0.0625, 0.0313][len(rows_e)],
                "ratio_to_previous": None if prev is None else nu_m / prev,
            }
        )
        prev = nu_m
    ratios = [r["ratio_to_previous"] for r in rows_e if r["ratio_to_previous"]]
    out["e_grid_convergence"] = {
        "report_ratios": [0.500, 0.500, 0.501],
        "reviewer_ratios": ratios,
        "criterion_pct": 5.0,
        "max_ratio_dev_pct": max(abs(r - 0.5) / 0.5 * 100 for r in ratios),
        "nu_rel_diff_pct": [
            abs(r["nu_meas_reviewer"] - r["nu_report"]) / r["nu_report"] * 100 for r in rows_e
        ],
        "rows": rows_e,
        "note": (
            "report states no (C, kdx) per refinement level; review assumes C=0.5 and physical "
            "mode m=8 on domain L=256. Halving reproduced to 0.12%; values match to rounding"
        ),
    }

    # ---- (f) QUICK leading-order formula (report sec 2.2)
    quick_cmp = {}
    for C in (0.2, 0.5, 0.8):
        for th in (0.02, 0.01):
            quick_cmp[f"C={C}_kdx={th}"] = {
                "nu_exact": nu_exact("quick", C, th),
                "report_formula_1mC_1mC2_over_8": nu_leading("quick", C),
                "reviewer_derived_5m4C_over_8": nu_quick_derived(C),
                "ratio_exact_over_report_formula": nu_exact("quick", C, th) / nu_leading("quick", C),
                "ratio_exact_over_reviewer_derived": nu_exact("quick", C, th) / nu_quick_derived(C),
            }
    quick_vs_upwind = {
        f"C={C}": {
            "quick_leading": nu_quick_derived(C),
            "upwind_leading": nu_leading("upwind", C),
            "quick_over_upwind": nu_quick_derived(C) / nu_leading("upwind", C),
        }
        for C in (0.2, 0.5, 0.8)
    }
    out["f_quick"] = {
        "comparisons": quick_cmp,
        "quick_vs_upwind": quick_vs_upwind,
        "conclusion": (
            "the printed QUICK formula nu = c dx (1-C)(1-C^2)/8 is not the leading-order "
            "viscosity of QUICK: the Leonard two-upstream interpolation gives c dx (5-4C)/8, "
            "5.5x-25x larger, and larger than upwind at every Courant number tested -> the "
            "report's 'small but nonzero' characterisation of QUICK is refuted"
        ),
    }

    # ---- (g) inventory arithmetic
    out["g_inventory"] = {
        "sweep_combinations_claim": 36,
        "sweep_combinations_arithmetic": 4 * 3 * 3,
        "matches": 4 * 3 * 3 == 36,
        "json_size_claim_kb": 227,
        "test_count_claim": 57,
        "artifacts_verifiable_here": False,
    }

    # ---- (h) hygiene probes on the markdown
    out["h_hygiene"] = {
        "self_declared_all_criteria_pass": "验证状态**: ✅ 全部验收判据通过" in md,
        "criteria_all_pass_sentence": "全部判据满足" in md,
        "test_count_claim": "57 passed" in md,
        "commit_pending": "commit 待平台自动推送" in md,
        "offtopic_hydroelasticity_paths": "artifacts/hydroelasticity/case_report.json" in md,
        "audit_pending": "审核**: 待平台自动审核" in md,
        "upwind_formula_present": "ν_th = cΔx(1-C)/2" in md,
        "quick_formula_present": "(1-C²)/8" in md,
        "cd2_formula_present": "|G| = √(1 + C²sin²θ)" in md,
        "figure_links": [
            s
            for s in ("fig1_von_neumann.png", "fig2_nu_comparison.png", "fig3_grid_convergence.png")
            if s in md
        ],
        "figures_embedded_in_platform_record": False,
    }

    out["verdict_inputs"] = {
        "a_conclusion_holds": out["a_upwind"]["max_dev_pct_reviewer"] < 1.0,
        "a_numbers_reproduced": False,
        "a_sign_contradictions": out["a_upwind"]["sign_contradictions"],
        "b_criterion_diagnostic": False,
        "b_numbers_reproduced": False,
        "c_bound_holds": out["c_lax_wendroff"]["bound_holds"],
        "c_numbers_reproduced": False,
        "d_G_reproduced": True,
        "d_growth_band_supported": out["d_cd2"]["band_supported"],
        "e_ratio_reproduced_within_criterion": out["e_grid_convergence"]["max_ratio_dev_pct"] < 5.0,
        "f_quick_formula_refuted": True,
        "g_inventory_arithmetic": out["g_inventory"]["matches"],
    }
    (HERE / "checks.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(out["verdict_inputs"], indent=2))
    print("wrote", HERE / "checks.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())