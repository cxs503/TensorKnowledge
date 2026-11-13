#!/usr/bin/env python3
"""Figure for wp-611-04: independent re-computation vs the numbers in report 611.

Panels
  A  GM vs submerged fraction for both geometries (recomputed) + reported points
  B  heave stiffness vs submerged fraction + reported points
  C  discriminative power of the buoyancy check: reference method vs relative error
  D  candidate formulas for the reported GM(3-D) = -0.115
"""
from __future__ import annotations

import json
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import independent_check_611 as ic  # noqa: E402

OUT = os.path.join(HERE, "fig_review_611.png")


def main() -> int:
    res = json.load(open(os.path.join(HERE, "independent_check_results.json"), encoding="utf-8"))
    f_eq = res["geometry_and_equilibrium"]["target_f_sub"]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    # ---- A: GM(f_sub) ----
    ax = axes[0][0]
    for dim, style, label in ((2, "-", "2-D disk"), (3, "--", "3-D sphere")):
        rows = ic.gm_scan(dim, 121)
        ax.plot([r["f_sub"] for r in rows], [r["GM"] for r in rows], style, lw=2, label=label)
    ax.axvline(f_eq, color="0.5", ls=":", lw=1.2)
    ax.text(f_eq, 0.03, " f_sub=ρ_i/ρ_w", fontsize=8, color="0.35")
    ax.plot([f_eq], [res["stability"]["2d"]["GM"]], "o", ms=7, mfc="w", label="recomputed @eq (2-D)")
    ax.plot([f_eq], [res["stability"]["3d"]["GM"]], "s", ms=7, mfc="w", label="recomputed @eq (3-D)")
    ax.plot([f_eq], [-0.115], "rx", ms=11, mew=2.2, label="report: 3-D GM = -0.115")
    ax.plot([f_eq], [0.0], "g+", ms=11, mew=2.0, label="report: 2-D GM ≈ 0")
    ax.set_xlabel("submerged volume/area fraction  f_sub")
    ax.set_ylabel("GM  (m)")
    ax.set_title("A  GM: BM≡BG ⇒ GM≡0 for a homogeneous sphere\n(no draught gives GM<0)")
    ax.set_ylim(-0.20, 0.05)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="lower left")

    # ---- B: k_heave(f_sub) ----
    ax = axes[0][1]
    for dim, style, label in ((2, "-", "2-D disk [N/m²]"), (3, "--", "3-D sphere [N/m]")):
        rows = ic.gm_scan(dim, 121)
        ks = [ic.stability(r["h"], dim)["k_heave"] for r in rows]
        ax.plot([r["f_sub"] for r in rows], ks, style, lw=2, label=label)
    ax.plot([f_eq], [7414.0], "g+", ms=11, mew=2, label="report 7414 (2-D)")
    ax.plot([f_eq], [5081.0], "rx", ms=10, mew=2, label="report 5081 (3-D)")
    ax.set_xlabel("f_sub")
    ax.set_ylabel("k_heave")
    ax.set_title("B  heave stiffness: recomputed vs reported\n(7414.02 vs 7414; 5081.15 vs 5081)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    # ---- C: discriminative power ----
    ax = axes[1][0]
    ref = res["buoyancy"]["independent_reference_rel_errors"]
    methods = [
        ("closed form\n(same expression)", max(ref["closed_form_same_expression"]["rel_err_2d"],
                                               1e-18)),
        ("report claim", 2.19e-16),
        ("quadrature n=50k", max(ref["quadrature_n50000"]["rel_err_2d"],
                                ref["quadrature_n50000"]["rel_err_3d"])),
        ("quadrature n=2k", max(ref["quadrature_n2000"]["rel_err_2d"],
                               ref["quadrature_n2000"]["rel_err_3d"])),
        ("Monte-Carlo 2e5", ref["monte_carlo_3d"]["rel_err_3d"]),
    ]
    vals = [max(v, 1e-18) for _, v in methods]
    cols = ["0.25", "crimson", "tab:blue", "tab:blue", "tab:orange"]
    ax.bar([m for m, _ in methods], vals, color=cols)
    ax.set_yscale("log")
    ax.axhline(0.03, color="k", ls="--", lw=1)
    ax.text(0.02, 0.035, "declared tolerance 0.03", transform=ax.get_yaxis_transform(), fontsize=8)
    ax.set_ylabel("relative error of buoyancy force")
    ax.set_title("C  what each reference can resolve\n(2.19e-16 ⇒ the reference is the formula itself)")
    ax.tick_params(axis="x", labelsize=7)
    for i, v in enumerate(vals):
        ax.text(i, v * 1.6, f"{v:.1e}", ha="center", fontsize=7)
    ax.set_ylim(1e-18, 10)

    # ---- D: GM hypotheses ----
    ax = axes[1][1]
    hyp = res["stability"]["GM_hypotheses_3d"]
    keys = [k for k in hyp if k != "nearest_standard_variant_gap"]
    vals = [hyp[k] for k in keys]
    short = [k.replace(" (BM=I/A_sub, BG=|zB|, G=centre)", "").replace("_", " ") for k in keys]
    cols = ["crimson" if k == "reported_by_producer" else ("tab:green" if abs(v) < 1e-6 else "tab:gray")
            for k, v in zip(keys, vals)]
    ax.barh(short, vals, color=cols)
    ax.axvline(0, color="k", lw=1)
    for i, v in enumerate(vals):
        ax.text(v + (0.004 if v >= 0 else -0.004), i, f"{v:+.4f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=8)
    ax.set_xlabel("GM (m), 3-D sphere")
    ax.set_title("D  candidate formulas vs reported GM = -0.115\nexact identity gives 0; nearest mis-set variant -0.125")
    ax.tick_params(axis="y", labelsize=7)
    ax.set_xlim(-0.22, 0.12)

    fig.suptitle(
        "wp-611-04 independent re-computation of report 611 "
        "(SIR-PC2|F07 DEM buoyancy & wet coupling; R=0.5 m, ρi/ρw=917/1025, g=9.81)",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT, dpi=135)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())