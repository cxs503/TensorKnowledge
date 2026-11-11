#!/usr/bin/env python3
"""Generate run artifacts for knowledge/sediment/m5490.

This script extracts necessary data from the pinned TensorLBM commit and
generates visualization artifacts. It serves as the entry point for reproducing
the knowledge extraction deliverables.

Usage:
    TENSORLBM_REPO=/path/to/TensorLBM python3 scripts/generate_m5490_artifacts.py
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
OUT = REPO_ROOT / "knowledge" / "sediment" / "m5490"
SOURCE_SHA = "f561cd88f22522280907c208f151412238d7c6f8"
TENSORLBM = Path(os.environ.get("TENSORLBM_REPO", "/root/tp-agent/work/m8492/TensorLBM"))


def extract_results_json() -> dict:
    """Extract results.json from the pinned commit."""
    out = subprocess.run(
        ["git", "-C", str(TENSORLBM), "show", f"{SOURCE_SHA}:artifacts/wave_tank/results.json"],
        capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def extract_npz(name: str) -> np.lib.npyio.NpzFile:
    """Extract a specific npz file from the pinned commit."""
    out = subprocess.run(
        ["git", "-C", str(TENSORLBM), "show", f"{SOURCE_SHA}:artifacts/wave_tank/{name}.npz"],
        capture_output=True, check=True
    )
    import io
    return np.load(io.BytesIO(out.stdout), allow_pickle=True)


def fig_criteria_summary(results: dict) -> Path:
    """Generate criteria summary figure from results.json."""
    crit = results["criteria"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), constrained_layout=True)

    # C1b: two-probe phase speed
    c1b = crit["C1b_wavemaker_phase_speed"]
    names = list(c1b["values"])
    vals = [100 * c1b["values"][n] for n in names]
    axes[0].bar(range(len(names)), vals, color="#c0504d")
    axes[0].axhline(100 * c1b["tol"], color="k", ls="--", lw=1.0,
                    label=f"C1b tol = {100 * c1b['tol']:.0f} %")
    axes[0].set_xticks(range(len(names)), [n.replace("_", "\n") for n in names], fontsize=7)
    axes[0].set_ylabel("phase-speed error [%]")
    axes[0].set_title("C1b two-probe phase speed (FAIL)", fontsize=9)
    axes[0].legend(fontsize=7)

    # C7: cost
    c7 = crit["C7_cost"]
    names = list(c7["values"])
    axes[1].bar(range(len(names)), [c7["values"][n] / 60 for n in names], color="#4f81bd")
    axes[1].axhline(c7["tol_s"] / 60, color="k", ls="--", lw=1.0,
                    label=f"C7 tol = {c7['tol_s'] / 60:.0f} min")
    axes[1].set_xticks(range(len(names)), [n.replace("_", "\n") for n in names], fontsize=6)
    axes[1].set_ylabel("wall clock [min]")
    axes[1].set_title(f"C7 cost (pass={c7['pass']})", fontsize=9)
    axes[1].legend(fontsize=7)

    # C4: mass conservation
    c4 = crit["C4_mass"]
    names = list(c4["values"])
    axes[2].bar(range(len(names)), [100 * abs(c4["values"][n]) for n in names], color="#9bbb59")
    axes[2].axhline(100 * c4["tol"], color="k", ls="--", lw=1.0,
                    label=f"C4 tol = {100 * c4['tol']:.1f} %/period")
    axes[2].set_xticks(range(len(names)), [n.replace("_", "\n") for n in names], fontsize=6)
    axes[2].set_ylabel("|mass drift| [%/period]")
    axes[2].set_title(f"C4 mass conservation (pass={c4['pass']})", fontsize=9)
    axes[2].legend(fontsize=7)

    fig.suptitle("TensorLBM wave tank @ f561cd8 — machine criteria from results.json", fontsize=10)
    path = OUT / "fig_criteria.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def fig_mass_drift(results: dict) -> Path:
    """Generate mass drift history figure."""
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    
    for name in sorted(results["cases"]):
        try:
            d = extract_npz(name)
            mass = np.asarray(d["mass"], dtype=float)
            mass0 = float(np.asarray(d["mass0"]))
            rel = (mass - mass0) / mass0 * 1e4  # 0.01 % units
            ax.plot(np.asarray(d["t"], dtype=float), rel, lw=1.0, label=name)
        except Exception as e:
            print(f"Warning: could not load {name}: {e}")
            continue
    
    tol_up = results["criteria"]["C4_mass"]["tol"] * 1e4
    ax.axhline(tol_up, color="r", ls="--", lw=1.0, label=f"C4 threshold +-{tol_up:.0f}e-4 M0")
    ax.axhline(-tol_up, color="r", ls="--", lw=1.0)
    ax.set_xlabel("step")
    ax.set_ylabel("mass drift (M(t) - M0)/M0  [1e-4 = 0.01 %]")
    ax.set_title("CAC two-phase wave tank: liquid mass history vs C4 threshold")
    ax.legend(fontsize=7, ncol=2)
    path = OUT / "fig_mass_drift.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def fig_knowledge_summary(results: dict) -> Path:
    """Generate knowledge extraction summary figure."""
    crit = results["criteria"]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Summary table of criteria
    criteria_data = []
    for key in ["C1_dispersion", "C1b_wavemaker_phase_speed", "C4_mass", "C7_cost"]:
        c = crit[key]
        criteria_data.append({
            "name": key,
            "pass": c["pass"],
            "tol": c["tol"] if "tol" in c else c.get("tol_s", 0)
        })
    
    y_pos = np.arange(len(criteria_data))
    colors = ["#9bbb59" if c["pass"] else "#c0504d" for c in criteria_data]
    
    ax.barh(y_pos, [1 if c["pass"] else 0 for c in criteria_data], color=colors)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([c["name"] for c in criteria_data])
    ax.set_xlabel("Pass (1) / Fail (0)")
    ax.set_title("Mission m5490 Knowledge Extraction: Criteria Summary")
    ax.axvline(0.5, color="k", ls="--", lw=0.5)
    
    # Add text annotations
    for i, c in enumerate(criteria_data):
        status = "PASS" if c["pass"] else "FAIL"
        ax.text(0.5, i, status, ha="center", va="center", fontweight="bold")
    
    path = OUT / "fig_knowledge_summary.png"
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> int:
    """Main entry point."""
    print("=" * 70)
    print("Mission m5490 Knowledge Extraction - Artifact Generation")
    print("=" * 70)
    print(f"Source: TensorLBM @ {SOURCE_SHA}")
    print(f"Output: {OUT}")
    print()
    
    OUT.mkdir(parents=True, exist_ok=True)
    
    # Extract results
    print("[1/3] Extracting results.json from pinned commit...")
    results = extract_results_json()
    print(f"      Found {len(results['cases'])} cases, {len(results['criteria'])} criteria")
    
    # Generate figures
    print("[2/3] Generating criteria summary figure...")
    p1 = fig_criteria_summary(results)
    print(f"      ✓ {p1.name} ({p1.stat().st_size} bytes)")
    
    print("[3/3] Generating mass drift history figure...")
    p2 = fig_mass_drift(results)
    print(f"      ✓ {p2.name} ({p2.stat().st_size} bytes)")
    
    print("[bonus] Generating knowledge summary figure...")
    p3 = fig_knowledge_summary(results)
    print(f"      ✓ {p3.name} ({p3.stat().st_size} bytes)")
    
    print()
    print("=" * 70)
    print("Artifact generation complete.")
    print(f"Knowledge entries: {len(list(OUT.glob('claim-*.json')))} claims, "
          f"{len(list(OUT.glob('evidence-*.json')))} evidence, "
          f"{len(list(OUT.glob('provenance-*.json')))} provenance")
    print(f"Run artifacts: {len(list(OUT.glob('fig_*.png')))} figures")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
