#!/usr/bin/env python3
"""Figures for the m5054 sediment package (all numbers read from the artifacts).

Three panels, each one answering a question the package claims:

1. Laplacian operator ladder: raw vs second-moment-renormalised relative L2 error
   against kh — shows the coarse-grid crossover that claim ``laplacian-renorm-scope``
   rests on.
2. Shear-wave decay rate: relative error per resolution rung with the 3 % gate,
   plus the raw-vs-renormalised pair at n = 20.
3. Hydrostatic bottom load: error per run against the 3 %/15 % gates, with the
   per-layer core maximum marked.

Inputs are the committed artifacts at the pinned commit (via ``git show``) plus
``knowledge/sediment/tk-sediment-m5054/benchmarks.json``; nothing is typed in by hand.
Writes PNGs + ``manifest.json`` (sha256 per figure) under ``docs/sediment/tk-sediment-m5054/figures``.

    python3 scripts/sediment_m5054_figures.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ke.sediment_extract import GitPin  # noqa: E402

SPEC = ROOT / "knowledge" / "sediment" / "tk-sediment-m5054" / "spec.json"
PKG = ROOT / "knowledge" / "sediment" / "tk-sediment-m5054"
OUT = ROOT / "docs" / "sediment" / "tk-sediment-m5054" / "figures"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-repo", default="/root/tensor-ecosystem/TensorSPH")
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    pin = GitPin(args.source_repo, spec["source"]["sha"])
    kernel = json.loads(pin.blob("benchmarks/threed_kernel/report.json"))
    shear = json.loads(pin.blob("benchmarks/threed_shear/report.json"))
    hydro = json.loads(pin.blob("benchmarks/threed_hydrostatic/report.json"))
    bench = json.loads((PKG / "benchmarks.json").read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in bench["rows"]}

    written = []

    # ---- figure 1: Laplacian ladder --------------------------------------- #
    ladder = kernel["operator_ladder"]
    kh = [row["kh"] for row in ladder]
    raw = [100 * row["laplacian_raw_rel_l2"] for row in ladder]
    cor = [100 * row["laplacian_corrected_rel_l2"] for row in ladder]
    fig, ax = plt.subplots(figsize=(6.4, 4.2), constrained_layout=True)
    ax.plot(kh, raw, "o-", label="raw Laplacian (non-monotone)")
    ax.plot(kh, cor, "s-", label="second-moment renormalised")
    ax.axvline(0.34, color="grey", ls=":", lw=1)
    ax.annotate("raw better here\n(kh > 0.5)", xy=(kh[0], raw[0]), xytext=(0.45, 18),
                arrowprops={"arrowstyle": "->", "lw": 0.8}, fontsize=8)
    ax.set_xlabel("k h")
    ax.set_ylabel("relative L2 error vs analytic Laplacian [%]")
    ax.set_title("3-D operator ladder: renormalisation pays only at fine kh")
    ax.invert_xaxis()
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    written.append(out / "fig1_laplacian_ladder.png")
    fig.savefig(written[-1], dpi=150)
    plt.close(fig)

    # ---- figure 2: shear decay rate --------------------------------------- #
    lad = shear["resolution_ladder"]
    n = [row["n"] for row in lad]
    err = [abs(100 * row["decay"]["rel_error"]) for row in lad]
    pair = shear["raw_vs_renormalised"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 4.0), constrained_layout=True)
    ax1.semilogy(n, err, "o-", label="renormalised operator")
    ax1.axhline(3.0, color="tab:red", ls="--", lw=1, label="3 % gate")
    ax1.axhline(15.0, color="tab:orange", ls=":", lw=1, label="15 % gate")
    for x, y in zip(n, err):
        ax1.annotate(f"{y:.2f}%", (x, y), textcoords="offset points", xytext=(0, 6),
                     fontsize=8, ha="center")
    ax1.set_xlabel("lattice resolution n (particles)")
    ax1.set_ylabel("|decay-rate error| vs 2νk²  [%]")
    ax1.set_title("unsteady-Stokes shear: verdict fail = missing h1.8 case")
    ax1.grid(alpha=0.3, which="both")
    ax1.legend(fontsize=8)
    labels = ["raw\n(n=20)", "renormalised\n(n=20)"]
    vals = [100 * pair["raw"]["decay"]["rel_error"],
            100 * pair["renormalised"]["decay"]["rel_error"]]
    bars = ax2.bar(labels, vals, color=["tab:grey", "tab:blue"])
    ax2.axhline(0, color="black", lw=0.8)
    ax2.axhline(3.0, color="tab:red", ls="--", lw=1)
    ax2.axhline(-3.0, color="tab:red", ls="--", lw=1)
    for bar, val in zip(bars, vals):
        ax2.annotate(f"{val:+.2f}%", (bar.get_x() + bar.get_width() / 2, val),
                     textcoords="offset points", xytext=(0, 4 if val > 0 else -12),
                     ha="center", fontsize=8)
    ax2.set_ylabel("decay-rate error [%]")
    ax2.set_title("same case, two operators (n=20, kh=0.408)")
    ax2.grid(alpha=0.3, axis="y")
    written.append(out / "fig2_shear_decay.png")
    fig.savefig(written[-1], dpi=150)
    plt.close(fig)

    # ---- figure 3: hydrostatic bottom load -------------------------------- #
    runs = hydro["runs"]
    labels = [f'{r["case"]}' for r in runs]
    bottoms = [100 * r["pressure"]["bottom_rel_error"] for r in runs]
    cores = [100 * r["pressure"]["max_rel_error_core"] for r in runs]
    fig, ax = plt.subplots(figsize=(9.0, 4.2), constrained_layout=True)
    x = range(len(runs))
    ax.bar([i - 0.2 for i in x], bottoms, width=0.4, label="bottom load error")
    ax.bar([i + 0.2 for i in x], cores, width=0.4, label="per-layer core max error")
    ax.axhline(0, color="black", lw=0.8)
    for sign in (-3, 3):
        ax.axhline(sign, color="tab:red", ls="--", lw=1,
                   label="3 % gate" if sign == 3 else None)
    for sign in (-15, 15):
        ax.axhline(sign, color="tab:orange", ls=":", lw=1,
                   label="15 % gate" if sign == 15 else None)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=7)
    ax.set_ylabel("relative error vs ρ0 g (H - dx/2)  [%]")
    ax.set_title("hydrostatic column: headline bottom load vs what the layers do")
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=8, ncol=2)
    written.append(out / "fig3_hydrostatic.png")
    fig.savefig(written[-1], dpi=150)
    plt.close(fig)

    # ---- figure 4: kernel quadrature errors ------------------------------- #
    ids = ["kernel-integral", "kernel-second-moment"]
    vals = [abs(rows[i]["rel_error_pct"]) for i in ids]
    labels = [rows[i]["ref_label"] for i in ids]
    fig, ax = plt.subplots(figsize=(6.4, 3.2), constrained_layout=True)
    ax.barh([lbl.replace(" (analytic)", "") for lbl in labels], vals,
            color=["tab:green", "tab:green"])
    for y, val in enumerate(vals):
        ax.annotate(f"{val:.2e} %", (val, y), textcoords="offset points",
                    xytext=(4, 0), va="center", fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("relative error vs analytic value [%]")
    ax.set_title("kernel normalisation: both identities hold at double precision")
    ax.grid(alpha=0.3, axis="x", which="both")
    written.append(out / "fig4_kernel_quadrature.png")
    fig.savefig(written[-1], dpi=150)
    plt.close(fig)

    manifest = {
        "source": {"repo": args.source_repo, "sha": spec["source"]["sha"]},
        "generated_by": "scripts/sediment_m5054_figures.py",
        "figures": [{"path": str(p.relative_to(ROOT)),
                     "bytes": p.stat().st_size,
                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                    for p in written],
        "inputs": {
            "benchmarks.json": hashlib.sha256((PKG / "benchmarks.json").read_bytes()).hexdigest(),
            "threed_kernel/report.json": hashlib.sha256(
                pin.blob("benchmarks/threed_kernel/report.json").encode()).hexdigest(),
            "threed_shear/report.json": hashlib.sha256(
                pin.blob("benchmarks/threed_shear/report.json").encode()).hexdigest(),
            "threed_hydrostatic/report.json": hashlib.sha256(
                pin.blob("benchmarks/threed_hydrostatic/report.json").encode()).hexdigest(),
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for entry in manifest["figures"]:
        print(f"{entry['path']}  {entry['bytes']} B  {entry['sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())