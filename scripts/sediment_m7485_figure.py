#!/usr/bin/env python3
"""Figure for the sediment package report: KP505 open-water BEM vs anchor.

Data source: ``benchmarks/kp505_openwater_bem/points.csv`` at the mission-7485
sha, read through the git object store — no number is typed in.

Panels
  (a) K_T(J), 10K_Q(J), eta_0(J): vortex-lattice result vs transcribed anchor
  (b) deviation vs J with the pre-declared bands (|dK_T| <= 3 %, |d eta_0| <= 5 %)
      and the J = 1.0 point marked unphysical (momentum gate False)

    M7485_SRC_REPO=/root/tp-agent/work/m7485 python scripts/sediment_m7485_figure.py
"""

from __future__ import annotations

import csv
import io
import os
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SHA = "80ad52a8236030e2343d5a88131bea3190088c09"
POINTS = "benchmarks/kp505_openwater_bem/points.csv"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "knowledge" / "sediment" / "m7485" / "figures" / "kp505_bem_vs_anchor.png"
SOURCE_REPO = Path(os.environ.get("M7485_SRC_REPO", "/root/tp-agent/work/m7485"))


def load_rows() -> list[dict[str, str]]:
    text = subprocess.run(["git", "-C", str(SOURCE_REPO), "show", f"{SHA}:{POINTS}"],
                          check=True, capture_output=True).stdout.decode("utf-8")
    return sorted(csv.DictReader(io.StringIO(text)), key=lambda r: float(r["J"]))


def main() -> int:
    rows = load_rows()
    j = [float(r["J"]) for r in rows]
    series = {
        "KT": ([float(r["KT_bem"]) for r in rows], [float(r["KT_anchor"]) for r in rows]),
        "10KQ": ([float(r["10KQ_bem"]) for r in rows], [float(r["10KQ_anchor"]) for r in rows]),
        "eta0": ([float(r["eta0_bem"]) for r in rows], [float(r["eta0_anchor"]) for r in rows]),
    }
    gate = [r["momentum_gate_ok"] == "True" for r in rows]

    fig, axes = plt.subplots(2, 2, figsize=(11.0, 7.6), constrained_layout=True)
    for ax, name in zip(axes.flat[:3], series):
        bem, anchor = series[name]
        ax.plot(j, bem, "o-", color="#1f4e79", label=f"BEM (vortex lattice)")
        ax.plot(j, anchor, "s--", color="#c00000", label="anchor (Iftikhar & Takinaci 2023, Table 2)")
        bad = [i for i, ok in enumerate(gate) if not ok]
        ax.plot([j[i] for i in bad], [bem[i] for i in bad], "x", ms=11, mew=2.2,
                color="k", label="unphysical (momentum gate False)")
        ax.set_xlabel("advance ratio J = V/(nD)")
        ax.set_ylabel(name)
        ax.set_title(f"{name}(J): BEM vs anchor")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)

    ax = axes.flat[3]
    dkt = [float(r["dKT_pct"]) for r in rows]
    deta = [float(r["deta0_pct"]) for r in rows]
    ax.axhspan(-3, 3, color="#c6e0b4", alpha=0.6, label="|dK_T| <= 3 % band")
    ax.axhline(5, color="#f4b183", ls="--", lw=1.0)
    ax.axhline(-5, color="#f4b183", ls="--", lw=1.0, label="|d eta_0| <= 5 % band")
    ax.plot(j, dkt, "o-", color="#1f4e79", label="dK_T")
    ax.plot(j, deta, "^-", color="#7030a0", label="d eta_0")
    ax.set_xlabel("advance ratio J")
    ax.set_ylabel("deviation vs anchor [%]")
    ax.set_title("deviation: honest FAIL at J = 0.8 (dK_T = %.2f %%)" % dkt[j.index(0.8)])
    ax.set_ylim(-80, 90)
    for xi, yi in ((0.8, dkt[j.index(0.8)]), (1.0, deta[j.index(1.0)])):
        if yi > ax.get_ylim()[1]:
            ax.annotate(f"{yi:+.2f}% (off-scale, unphysical point)", (xi, ax.get_ylim()[1] - 8),
                        textcoords="offset points", xytext=(-150, 0), fontsize=8,
                        arrowprops=dict(arrowstyle="->", lw=0.8))
        else:
            ax.annotate(f"{yi:+.2f}%", (xi, yi), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)

    fig.suptitle(
        "KP505 open-water: lifting-surface vortex lattice vs transcribed anchor "
        f"(TensorBEM@{SHA[:8]}, mission 7485)", fontsize=10)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"J=0.8 dK_T = {dkt[j.index(0.8)]:.2f} % (criterion 3 %), "
          f"J=1.0 d_eta0 = {deta[j.index(1.0)]:.2f} % (unphysical)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())