#!/usr/bin/env python3
"""Figures for ``docs/ke/sloshing-impact-lbm-sediment.md`` (matplotlib only).

All numbers are read from committed artefacts (``run/benchmark.json``) or from the
pinned source blobs via ``git show`` - no value is typed here.

Usage::

    SLOSHING_SRC_REPO=/root/tensor-ecosystem/TensorLBM \\
        python3 scripts/figures_sediment_sloshing.py --out-dir docs/ke/figures
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import sloshing_reference as REF  # noqa: E402
from sediment_lib import GitSource  # noqa: E402

PKG = ROOT / "knowledge" / "sediment" / "sloshing-impact-lbm"
IMPACT = "artifacts/sloshing_impact_lbm/impact_nx40.json"
REPORT = "artifacts/sloshing_impact_lbm/report.json"


def fig_benchmark(bench: dict, out: Path) -> Path:
    items = [i for i in bench["items"] if i["rel_error"] is not None]
    labels = [i["id"].split("-", 2)[2] for i in items]
    errs = [abs(i["rel_error"]) for i in items]
    exact = [e <= 1e-9 for e in errs]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    floor = 1e-17
    ax.barh(range(len(items)), [max(e, floor) for e in errs],
            color=["#2e7d32" if ok else "#c62828" for ok in exact])
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("|got - ref| / |ref|  (log scale)")
    ax.axvline(1e-9, color="black", ls=":", lw=1, label="exact-reproduction threshold 1e-9")
    ax.axvline(bench["worst_abs_rel_error"], color="#c62828", ls="--", lw=1,
               label=f"worst = {bench['worst_abs_rel_error']:.2e}")
    ax.set_title(
        f"Sediment benchmark: {bench['n_compared']} re-derived quantities vs the values "
        f"recorded by the source at the pinned sha\n"
        f"({len(exact)} exact reproductions to <= 1e-9, worst {bench['worst_abs_rel_error']:.2e})"
    )
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    path = out / "fig01_benchmark_ref_vs_got.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def fig_impact(src: GitSource, out: Path) -> Path:
    impact = src.json(IMPACT)
    report = src.json(REPORT)
    crit = report["criteria"]["b_peak_pressure_band"]
    anchor = report["anchor"]
    t, p = impact["t"], impact["p_wall"]
    filtered = REF.moving_max(p, 6)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.plot(t, p, lw=0.8, color="#1f4e79", label="wall pressure $p/(\\rho g h_l)$")
    ax1.axhline(filtered, color="#c62828", ls="--", lw=1,
                label=f"0.1 s moving-average peak = {crit['value']:.4f}")
    ax1.set_xlabel("t [s]")
    ax1.set_ylabel("$P_{peak}/(\\rho g h_l)$")
    ax1.set_title("Impact case (L/40): wall-pressure history")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    bars = {
        "LBM peak\n(filtered)": crit["value"],
        "SWE surge\nanchor": crit["swe_surge_anchor"],
        "exact bore\nreflection $h_r/h_l$": anchor["p_bore_over_p_hydrostatic"],
        "closed form\n$4\\rho g h_l$": anchor["p_closed_form_over_p_hydrostatic"],
    }
    lo, hi = crit["threshold"]
    ax2.axhspan(lo, hi, color="#e8f5e9", zorder=0, label=f"reference band [{lo:g}, {hi:g}]")
    ax2.bar(list(bars), list(bars.values()),
            color=["#c62828", "#f9a825", "#1565c0", "#1565c0"])
    for i, (k, v) in enumerate(bars.items()):
        ax2.annotate(f"{v:.4f}", (i, v), ha="center", va="bottom", fontsize=8)
    ax2.set_ylabel("$P/(\\rho g h_l)$")
    ax2.set_title("Criterion (b) FAIL: the low-order chain peak is below the band")
    ax2.legend(fontsize=8)
    ax2.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = out / "fig02_impact_peak_vs_reference_band.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def fig_swe_validity(out: Path) -> Path:
    kh = [0.001 * i for i in range(1, 1200)]
    ratio = [REF.swe_ratio(x) for x in kh]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.plot(kh, ratio, color="#1f4e79", label="$\\omega_{SWE}/\\omega_{exact}=\\sqrt{kh/\\tanh kh}$")
    for pct, colour in ((3, "#2e7d32"), (5, "#f9a825"), (10, "#c62828")):
        bound = REF.kh_for_ratio(1.0 + pct / 100.0)
        ax.axvline(bound, color=colour, ls="--", lw=1)
        ax.axhline(1.0 + pct / 100.0, color=colour, ls=":", lw=0.8)
        ax.annotate(f"{pct}% bound: kh={bound:.4f}", (bound, 1.0 + pct / 100.0 + 0.002),
                    rotation=90, fontsize=7, color=colour, ha="right", va="bottom")
    anchor_kh = REF.kh_of(20.0, 4.0)
    ax.plot([anchor_kh], [REF.swe_ratio(anchor_kh)], "o", color="black", ms=5)
    ax.annotate(
        f"IN48-N07: kh={anchor_kh:.4f}, ratio={REF.swe_ratio(anchor_kh):.4f} "
        f"(+{REF.swe_ratio_percent(anchor_kh):.2f}%)",
        (anchor_kh, REF.swe_ratio(anchor_kh)),
        xytext=(-8, 18), textcoords="offset points", fontsize=8, ha="right",
        arrowprops={"arrowstyle": "->", "lw": 0.8},
    )
    ax.set_xlabel("relative depth $kh$")
    ax.set_ylabel("frequency ratio")
    ax.set_title("Low-order chain validity: SWE frequency error vs relative depth")
    ax.set_ylim(0.99, 1.34)
    ax.set_xlim(0, 1.2)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = out / "fig03_swe_validity_bound.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=str(ROOT / "docs" / "ke" / "figures"))
    ap.add_argument("--src-repo", default=None)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
    source = manifest["source"]
    bench = json.loads((PKG / "run" / "benchmark.json").read_text(encoding="utf-8"))
    src_root = Path(args.src_repo or os.environ.get(source["root_env"], source["default_root"]))
    src = GitSource(src_root, source["sha"])

    made = [fig_benchmark(bench, out), fig_swe_validity(out)]
    if src.available:
        made.append(fig_impact(src, out))
    else:
        print(f"source not available at {src_root}: impact figure skipped", file=sys.stderr)
    for path in made:
        print(f"wrote {path.relative_to(ROOT)}")
    return 0 if len(made) == 3 else 4


if __name__ == "__main__":
    raise SystemExit(main())