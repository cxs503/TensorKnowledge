#!/usr/bin/env python3
"""Collect and analyse the validation runs for mission m8676 (OSS LBM / Kruger).

Inputs are the logs produced by ``run_upstream_cases.sh`` (upstream code, executed
unmodified apart from the compile-time knobs the sources themselves expose) and by
``kruger_bench_port.py`` (language port of chapter5/*.m, used as the verification
surface for the MATLAB-only codes -- MATLAB/Octave is not available in this image).

Outputs
  validation_summary.json   numbers used in the platform report (programmatic, no hand copy)
  figures/validation_runs.png  energy decay + convergence + Young-Laplace + IBM profile

Run:  python analyze_validation.py [--dir .]
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np


def parse_tg(log_path: Path) -> dict:
    """Parse chapter13/python3/vortexdecay.py stdout."""
    text = log_path.read_text()
    nx = int(re.search(r"domain size: (\d+)x(\d+)", text).group(1))
    nu = float(re.search(r"nu: ([0-9.eE+-]+)", text).group(1))
    nsteps = int(re.search(r"timesteps: (\d+)", text).group(1))
    samples = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 5 and parts[0].isdigit():
            samples.append([float(p) for p in parts])
    k = 2 * math.pi / nx
    td = 1.0 / (nu * (k * k + k * k))
    e0 = samples[0][1] if samples and samples[0][0] == 0 else None
    for s in samples:
        s.append(math.exp(-2 * s[0] / td))
    return {"nx": nx, "nu": nu, "nsteps": nsteps, "td": td, "samples": samples,
            "columns": ["t", "E", "L2rho", "L2ux", "L2uy", "E_over_E0_analytic"]}


def parse_shanchen(log_path: Path) -> dict:
    """Parse the final Young-Laplace block printed by chapter9/shanchen.cpp."""
    text = log_path.read_text()
    blocks = re.findall(
        r"Densities: rho_g = ([0-9.eE+-]+), rho_l = ([0-9.eE+-]+)\s+"
        r"Pressure difference: dp = ([0-9.eE+-]+)\s+"
        r"Droplet radius: r = ([0-9.eE+-]+)\s+"
        r"Surface tension: gamma = ([0-9.eE+-]+)", text)
    assert blocks, f"no Laplace block in {log_path}"
    rhog, rhol, dp, rad, gam = (float(x) for x in blocks[-1])
    mlups = re.search(r"corresponds to ([0-9.]+) MLUPS", text)
    cpu = re.search(r"Overall CPU time required: ([0-9.]+) sec", text)
    return {"rho_gas": rhog, "rho_liquid": rhol, "delta_p": dp, "radius": rad,
            "gamma": gam, "mlups": float(mlups.group(1)) if mlups else None,
            "cpu_s": float(cpu.group(1)) if cpu else None}


def parse_iblog(log_path: Path) -> dict:
    text = log_path.read_text()
    umax = float(re.search(r"Expected maximum velocity for Poiseuille flow: ([0-9.eE+-]+)", text).group(1))
    re_num = float(re.search(r"Reynolds number for Poiseuille flow: ([0-9.eE+-]+)", text).group(1))
    nu = float(re.search(r"Viscosity: ([0-9.eE+-]+)", text).group(1))
    return {"expected_u_max": umax, "Re": re_num, "nu": nu}


def analyse_ib_profile(dat_path: Path, expected_umax: float) -> dict:
    """Mid-channel profile of chapter11/IBLBM_2D_Poiseuille.cpp at the last time step."""
    d = np.loadtxt(dat_path, skiprows=1)
    x, y, rho, ux, uy = d.T
    nx, ny = len(np.unique(x)), len(np.unique(y))
    prof = ux.reshape(nx, ny).mean(axis=0)  # average over the periodic x direction
    centre = float(prof[ny // 2])
    return {"nx": nx, "ny": ny, "u_max_measured": float(prof.max()),
            "u_centre_measured": centre,
            "u_max_expected": expected_umax,
            "centreline_error_pct": (centre - expected_umax) / expected_umax * 100,
            "wall_values": [float(prof[0]), float(prof[-1])],
            "profile_u": prof.tolist(),
            "profile_y": np.unique(y).tolist()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).parent))
    args = ap.parse_args()
    here = Path(args.dir)
    logs = here / "logs"

    summary: dict = {"mission": "m8676", "repo": "lbm-principles-practice/code",
                     "note": "all numbers parsed programmatically from run logs"}

    # --- Taylor-Green vortex decay (upstream python3 code, 3 resolutions) ---
    tg_runs = {}
    for scale in (1, 2, 4):
        p = logs / f"tg_scale{scale}.log"
        if p.exists():
            tg_runs[scale] = parse_tg(p)
    conv = []
    if tg_runs:
        for scale, r in tg_runs.items():
            final = r["samples"][-1]
            e_ratio_num = final[1] / r["samples"][0][1]
            conv.append({
                "scale": scale, "NX": r["nx"], "steps": int(final[0]),
                "L2_rho": final[2], "L2_ux": final[3], "L2_uy": final[4],
                "E_over_E0_measured": e_ratio_num,
                "E_over_E0_analytic": final[5],
                "E_rel_dev_pct": (e_ratio_num - final[5]) / final[5] * 100,
                "max_L2ux_t_gt_0": max(s[3] for s in r["samples"] if s[0] > 0),
            })
        conv.sort(key=lambda d: d["NX"])
        for a, b in zip(conv, conv[1:]):
            b["L2ux_ratio_prev_over_this"] = a["L2_ux"] / b["L2_ux"]
            b["observed_order"] = math.log(b["L2ux_ratio_prev_over_this"], (b["NX"] / a["NX"]))
        summary["taylor_green"] = {"runs": conv,
                                   "analytic": "E(t)/E(0)=exp(-2t/t_d), t_d=1/(nu(kx^2+ky^2))"}

    # --- Young-Laplace (upstream chapter9/shanchen.cpp, two droplet radii) ---
    sc = {}
    for tag, name in (("radius15", "shanchen_radius15.log"), ("radius12", "shanchen_radius12.log")):
        p = logs / name
        if p.exists():
            sc[tag] = parse_shanchen(p)
    if sc:
        summary["young_laplace"] = {"cases": sc}
        if len(sc) == 2:
            a, b = sc["radius15"], sc["radius12"]
            g1, g2 = a["gamma"], b["gamma"]
            summary["young_laplace"]["gamma_rel_diff_pct"] = abs(g1 - g2) / (0.5 * (g1 + g2)) * 100
            summary["young_laplace"]["dp_ratio"] = a["delta_p"] / b["delta_p"]
            summary["young_laplace"]["radius_ratio"] = a["radius"] / b["radius"]

    # --- IBM-LBM Poiseuille (upstream chapter11 code) ---
    p_ib = logs / "iblbm_poiseuille.log"
    p_dat = logs / "iblbm_fluid_t2000.dat"
    if p_ib.exists() and p_dat.exists():
        ib = parse_iblog(p_ib)
        ib.update(analyse_ib_profile(p_dat, ib["expected_u_max"]))
        # analytic parabola through 0 and the printed channel width, for reference only
        summary["ib_lbm_poiseuille"] = ib

    # --- port of chapter5/*.m (Poiseuille / Couette with half-way bounce-back) ---
    p_port = here / "kruger_bench_results.json"
    if p_port.exists():
        port = json.loads(p_port.read_text())
        p_pois = next(r for r in port["runs"] if r["case"] == "poiseuille_BB")
        c_cou = next(r for r in port["runs"] if r["case"] == "couette_BB")
        summary["port_chapter5"] = {
            "poiseuille": {"tau": p_pois["tau"], "L2": p_pois["L2"], "steps": p_pois["steps"],
                           "u_centre_num": p_pois["u_center_num"],
                           "u_centre_analytic": p_pois["u_center_analytic"]},
            "couette": {"tau": c_cou["tau"], "L2": c_cou["L2"], "steps": c_cou["steps"],
                        "u_top_num": c_cou["u_top_num"], "u_top_analytic": c_cou["u_top_analytic"]},
            "tau_sweep": port["tau_sweep"],
            "resolution_study": port["resolution_study"],
            "magic_tau": math.sqrt(3 / 16) + 0.5,
        }

    (here / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # ------------------------------ figures ------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.3))

        # (a) TG kinetic-energy decay vs analytic
        if tg_runs:
            styles = {1: "o", 2: "s", 4: "^"}
            for scale, r in sorted(tg_runs.items()):
                t = np.array([s[0] for s in r["samples"]]) / r["td"]
                e = np.array([s[1] for s in r["samples"]]) / r["samples"][0][1]
                ax[0].semilogy(t, e, styles[scale] + "-", ms=4,
                               label=f"LBM NX={r['nx']}")
            tmax = 0.0
            for rr in tg_runs.values():
                tmax = max(tmax, float((np.array([s[0] for s in rr["samples"]]) / rr["td"]).max()))
            t = np.linspace(0, tmax, 100)
            ax[0].semilogy(t, np.exp(-2 * t), "k--", lw=1.2, label=r"analytic $e^{-2t/t_d}$")
            ax[0].set_xlabel(r"$t/t_d$"); ax[0].set_ylabel(r"$E(t)/E(0)$")
            ax[0].set_title("Taylor-Green decay (chapter13 python3)")
            ax[0].legend(fontsize=8); ax[0].grid(alpha=.3, which="both")

        # (b) second-order convergence of L2(ux)
        if len(conv) >= 2:
            nx = np.array([c["NX"] for c in conv], float)
            l2 = np.array([max(c["L2_ux"], 1e-18) for c in conv])
            ax[1].loglog(nx, l2, "o-", label="$L_2(u_x)$ at $t/t_d$ = const")
            ax[1].loglog(nx, l2[0] * (nx / nx[0]) ** -2, "k--", lw=1, label="slope -2 (2nd order)")
            for c in conv:
                ax[1].annotate(f"{c['L2_ux']:.1e}", (c["NX"], c["L2_ux"]), textcoords="offset points",
                               xytext=(4, 6), fontsize=7)
            ax[1].set_xlabel("NX"); ax[1].set_ylabel("$L_2(u_x)$")
            ax[1].set_title("Taylor-Green convergence")
            ax[1].legend(fontsize=8); ax[1].grid(alpha=.3, which="both")

        # (c) Young-Laplace: dp vs 1/r and the two gamma values
        if "young_laplace" in summary and len(summary["young_laplace"]["cases"]) == 2:
            cases = summary["young_laplace"]["cases"]
            invr = np.array([1 / cases["radius15"]["radius"], 1 / cases["radius12"]["radius"]])
            dp = np.array([cases["radius15"]["delta_p"], cases["radius12"]["delta_p"]])
            g = np.array([cases["radius15"]["gamma"], cases["radius12"]["gamma"]])
            gmean = g.mean()
            ax[2].plot(invr, dp, "o", ms=7, label="chapter9/shanchen.cpp")
            xs = np.linspace(0, invr.max() * 1.1, 10)
            ax[2].plot(xs, gmean * xs, "k--", lw=1.2, label=r"Young-Laplace $\Delta p=\gamma/r$")
            for xx, dd, gg in zip(invr, dp, g):
                ax[2].annotate(f"$\\gamma$={gg:.4f}", (xx, dd), textcoords="offset points",
                               xytext=(-10, 10), fontsize=7)
            ax[2].set_xlabel("$1/r$ [1/lattice]"); ax[2].set_ylabel(r"$\Delta p$ [lattice]")
            ax[2].set_title("Young-Laplace (Shan-Chen droplet)")
            ax[2].legend(fontsize=8); ax[2].grid(alpha=.3)

        fig.tight_layout()
        figdir = here / "figures"
        figdir.mkdir(exist_ok=True)
        fig.savefig(figdir / "validation_runs.png", dpi=140)
        plt.close(fig)

        # separate IBM profile figure
        if "ib_lbm_poiseuille" in summary:
            ib = summary["ib_lbm_poiseuille"]
            fig2, ax2 = plt.subplots(figsize=(5.2, 4.2))
            yy = np.array(ib["profile_y"])
            h = 15.3
            nu = ib["nu"]
            uan = -1e-5 / (2 * nu) * (yy - 0.0) * (yy - h)
            ax2.plot(uan, yy, "k--", lw=1.2, label="analytic (wall_width=15.3)")
            ax2.plot(ib["profile_u"], yy, "o", ms=5, mfc="none", label="IBM-LBM (chapter11)")
            ax2.set_xlabel("$u_x$"); ax2.set_ylabel("$y$")
            ax2.set_title("IBM-LBM Poiseuille, t=2000")
            ax2.legend(fontsize=8); ax2.grid(alpha=.3)
            fig2.tight_layout()
            fig2.savefig(figdir / "ib_lbm_profile.png", dpi=140)
            plt.close(fig2)
    except Exception as exc:  # pragma: no cover
        print(f"figure generation skipped: {exc}")

    # console digest
    if "taylor_green" in summary:
        for c in summary["taylor_green"]["runs"]:
            print(f"TG NX={c['NX']:3d}  L2(ux)={c['L2_ux']:.3e}  "
                  f"E/E0 num={c['E_over_E0_measured']:.6f} ana={c['E_over_E0_analytic']:.6f} "
                  f"({c['E_rel_dev_pct']:+.2f}%)"
                  + (f"  order={c['observed_order']:.2f}" if "observed_order" in c else ""))
    if "young_laplace" in summary and "gamma_rel_diff_pct" in summary["young_laplace"]:
        yl = summary["young_laplace"]
        print(f"Young-Laplace: gamma={yl['cases']['radius15']['gamma']:.5f} / "
              f"{yl['cases']['radius12']['gamma']:.5f} (rel diff {yl['gamma_rel_diff_pct']:.2f}%), "
              f"dp ratio {yl['dp_ratio']:.4f} vs r ratio {yl['radius_ratio']:.4f}")
    if "ib_lbm_poiseuille" in summary:
        ib = summary["ib_lbm_poiseuille"]
        print(f"IBM-LBM: u_centre={ib['u_centre_measured']:.6f} vs expected {ib['u_max_expected']:.6f} "
              f"({ib['centreline_error_pct']:+.2f}%)")
    if "port_chapter5" in summary:
        p = summary["port_chapter5"]
        print(f"port chapter5: Poiseuille L2={p['poiseuille']['L2']:.3e} (tau={p['poiseuille']['tau']:.6f}), "
              f"Couette L2={p['couette']['L2']:.3e}")
    print(f"written: {here/'validation_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())