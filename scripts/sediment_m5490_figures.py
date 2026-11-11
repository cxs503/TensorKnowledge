#!/usr/bin/env python3
"""Figures for knowledge/sediment/m5490 (source mission 5490, TensorLBM wave tank).

Everything is redrawn from the artefacts committed at the pinned source sha:
``artifacts/wave_tank/*.npz`` (phase field, mass history, probe elevations) and
``artifacts/wave_tank/results.json`` (criterion values).  No number is typed by
hand; the analytic reference curve is evaluated with the source solver's own
``tensorlbm.wave_tank.stokes2`` at the same ``g_eff``.

Usage:
    TENSORLBM_REPO=/root/tp-agent/work/m5490 python3 scripts/sediment_m5490_figures.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "knowledge" / "sediment" / "m5490" / "figures"
SOURCE_SHA = "f561cd88f22522280907c208f151412238d7c6f8"
TENSORLBM = Path(os.environ.get("TENSORLBM_REPO", "/root/tp-agent/work/m5490"))
ART = TENSORLBM / "artifacts" / "wave_tank"

sys.path.insert(0, str(TENSORLBM / "src"))
from tensorlbm.wave_tank import stokes2  # noqa: E402

_RES = json.loads(subprocess.run(
    ["git", "-C", str(TENSORLBM), "show", f"{SOURCE_SHA}:artifacts/wave_tank/results.json"],
    capture_output=True, text=True, check=True).stdout)


def wave_of_config(cfg: dict) -> "stokes2.Stokes2Wave":
    g_eff = cfg["g"] * (1.0 - cfg["rho_g"] / cfg["rho_l"])
    return stokes2.Stokes2Wave.from_kh(cfg["kh"], cfg["eps"], cfg["h"], g_eff)


def load_case(name: str):
    d = np.load(ART / f"{name}.npz", allow_pickle=True)
    cfg = json.loads(str(d["config"]))
    return d, cfg


def fig_field_surface() -> Path:
    names = ["kh1.5_eps0.08", "kh3.0_eps0.08"]
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.2), constrained_layout=True)
    for ax, name in zip(axes, names):
        d, cfg = load_case(name)
        phi = np.asarray(d["phi"], dtype=float)
        eta = np.asarray(d["eta_final"], dtype=float)
        t_end = float(np.asarray(d["t"])[-1])
        w = wave_of_config(cfg)
        x = np.arange(phi.shape[1], dtype=float)
        mesh = ax.pcolormesh(x, np.arange(phi.shape[0]), phi, cmap="RdBu_r",
                             vmin=0.0, vmax=1.0, shading="auto")
        ax.set_ylabel("y [cells]")
        ax.set_title(f"{name}: final phase field phi + gauged surface vs Stokes-2nd analytic "
                     f"(t = {t_end:.1f} steps)", fontsize=9)
        twin = ax.twinx()
        twin.plot(x, eta - eta.mean(), color="k", lw=1.2, label="gauged (liquid-column integral, mean removed)")
        eta_a = w.eta(x, t_end)
        twin.plot(x, eta_a - eta_a.mean(), color="limegreen", lw=1.0, ls="--",
                  label="Stokes-2nd analytic, g_eff = 0.9 g (mean removed)")
        twin.set_ylabel("surface elevation [cells]")
        twin.set_ylim(-3.0, 3.0)
        twin.legend(loc="upper right", fontsize=7)
        fig.colorbar(mesh, ax=twin, pad=0.01, fraction=0.025, label="phi (1 = liquid)")
    fig.suptitle("TensorLBM phase-field (CAC) wave tank @ f561cd88 — free surface vs analytic", fontsize=10)
    path = OUT / "fig_field_surface.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def fig_mass_drift() -> Path:
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    for name in sorted(_RES["cases"]):
        d, _ = load_case(name)
        mass = np.asarray(d["mass"], dtype=float)
        mass0 = float(np.asarray(d["mass0"]))
        rel = (mass - mass0) / mass0 * 1e4          # 0.01 % units
        ax.plot(np.asarray(d["t"], dtype=float), rel, lw=1.0, label=name)
    tol_up = _RES["criteria"]["C4_mass"]["tol"] * 1e4
    ax.axhline(tol_up, color="r", ls="--", lw=1.0, label=f"C4 threshold +-{tol_up:.0f}e-4 M0")
    ax.axhline(-tol_up, color="r", ls="--", lw=1.0)
    ax.set_xlabel("step")
    ax.set_ylabel("mass drift (M(t) - M0)/M0  [1e-4 = 0.01 %]")
    ax.set_title("CAC two-phase wave tank: liquid mass history vs C4 threshold (tol 0.5 %/period)")
    ax.legend(fontsize=7, ncol=2)
    path = OUT / "fig_mass_drift.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def fig_criteria() -> Path:
    crit = _RES["criteria"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), constrained_layout=True)

    c1b = crit["C1b_wavemaker_phase_speed"]
    names = list(c1b["values"])
    vals = [100 * c1b["values"][n] for n in names]
    axes[0].bar(range(len(names)), vals, color="#c0504d")
    axes[0].axhline(100 * c1b["tol"], color="k", ls="--", lw=1.0,
                    label=f"C1 tol = {100 * c1b['tol']:.0f} %")
    axes[0].set_xticks(range(len(names)), [n.replace("_", "\n") for n in names], fontsize=7)
    axes[0].set_ylabel("phase-speed error [%]")
    axes[0].set_title("C1b two-probe phase speed (FAIL)", fontsize=9)
    axes[0].legend(fontsize=7)

    c7 = crit["C7_cost"]
    names = list(c7["values"])
    axes[1].bar(range(len(names)), [c7["values"][n] / 60 for n in names], color="#4f81bd")
    axes[1].axhline(c7["tol_s"] / 60, color="k", ls="--", lw=1.0,
                    label=f"C7 tol = {c7['tol_s'] / 60:.0f} min")
    axes[1].set_xticks(range(len(names)), [n.replace("_", "\n") for n in names], fontsize=6)
    axes[1].set_ylabel("wall clock [min]")
    axes[1].set_title(f"C7 cost (pass={c7['pass']}: 1 case over budget)", fontsize=9)
    axes[1].legend(fontsize=7)

    c4 = crit["C4_mass"]
    names = list(c4["values"])
    axes[2].bar(range(len(names)), [100 * abs(c4["values"][n]) for n in names], color="#9bbb59")
    axes[2].axhline(100 * c4["tol"], color="k", ls="--", lw=1.0,
                    label=f"C4 tol = {100 * c4['tol']:.1f} %/period")
    axes[2].set_xticks(range(len(names)), [n.replace("_", "\n") for n in names], fontsize=6)
    axes[2].set_ylabel("|mass drift| [%/period]")
    axes[2].set_title(f"C4 mass conservation (pass={c4['pass']})", fontsize=9)
    axes[2].legend(fontsize=7)

    fig.suptitle("TensorLBM wave tank @ f561cd88 — machine criteria straight from results.json", fontsize=10)
    path = OUT / "fig_criteria.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def fig_probes() -> Path:
    name = "kh1.5_eps0.08"
    d, cfg = load_case(name)
    t = np.asarray(d["t"], dtype=float)
    eta = np.asarray(d["probe_eta"], dtype=float)
    cols = [int(c) for c in np.asarray(d["probe_cols"])]
    w = wave_of_config(cfg)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), constrained_layout=True)
    for j, ax in enumerate(axes):
        ax.plot(t, eta[:, j], color="k", lw=1.0, label=f"gauge x = {cols[j]} cells")
        eta_a = w.eta(cols[j], t)
        ax.plot(t, eta_a, color="limegreen", lw=0.9, ls="--", label="Stokes-2nd analytic (g_eff)")
        ax.set_xlabel("step")
        ax.set_ylabel("eta [cells]")
        ax.set_title(f"{name} gauge {j + 1} vs analytic", fontsize=9)
        ax.legend(fontsize=7)
    path = OUT / "fig_probes.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (fig_field_surface, fig_mass_drift, fig_criteria, fig_probes):
        p = fn()
        print(f"wrote {p.relative_to(REPO_ROOT)} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())