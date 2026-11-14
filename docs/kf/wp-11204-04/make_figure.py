#!/usr/bin/env python3
"""wp-11204-04 · review figure (no simulated fields: this is a documentation review).

Panel (a): declared vs independently recomputed relative errors for the five J/load rows
           of report 11204, with the report's own 3% / 5% / 8% acceptance lines.
Panel (b): ASTM E399 LEFM elastic J(P) curves for CT and SE(B); the report's J values are
           marked, exposing the evaluation loads (~12.0 kN / ~2.0 kN) that the report never
           states, against the documented peak loads (34 725 N / 7 782 N).

Writes `figures/wp-11204-04_review.png`.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import review_checks as rc  # noqa: E402

PKG = Path(__file__).resolve().parent
OUT = PKG / "figures" / "wp-11204-04_review.png"
CHECKS = PKG / "checks" / "independent_checks.json"


def main() -> None:
    checks = json.loads(CHECKS.read_text(encoding="utf-8"))["checks"]
    arith = checks["C4_table_arithmetic"]["table"]
    labels = ["CT peak\nload", "CT elastic\nJ", "CT elastoplastic\nJ", "SE(B)\nJ", "SE(B) peak\nload"]
    keys = ["ct_peak_load", "ct_J_elastic", "ct_J_elastoplastic", "seb_J", "seb_peak_load"]
    declared = [arith[k]["declared_pct"] for k in keys]
    recomputed = [arith[k]["recomputed_pct"] for k in keys]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.3), dpi=130)

    x = range(len(labels))
    ax1.bar([i - 0.19 for i in x], declared, width=0.38, label="declared in report",
            color="#4C72B0")
    ax1.bar([i + 0.19 for i in x], recomputed, width=0.38, label="recomputed (independent)",
            color="#DD8452")
    for i, (d, r) in enumerate(zip(declared, recomputed)):
        ax1.annotate(f"{d:+.3f}", (i - 0.19, d), ha="center", va="bottom" if d >= 0 else "top",
                     fontsize=7)
        ax1.annotate(f"{r:+.3f}", (i + 0.19, r), ha="center", va="bottom" if r >= 0 else "top",
                     fontsize=7)
    for y, c, tag in ((3.0, "#999999", "3%"), (5.0, "#8172B3", "5%"), (8.0, "#C44E52", "8%")):
        ax1.axhline(y, color=c, ls=":", lw=1)
        ax1.text(len(labels) - 0.45, y, f"{tag} line", fontsize=7, color=c, va="bottom", ha="right")
    ax1.axhline(0, color="k", lw=0.8)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_ylabel("relative error [%]")
    ax1.set_title("(a) 5 reported errors: declared vs recomputed\n(max gap 0.003 pp; signs of C1/C1b differ)", fontsize=9)
    ax1.legend(fontsize=7, loc="upper left")

    # panel (b): elastic J(P) from ASTM E399, with the report's two elastic J values marked
    import numpy as np
    P_ct = np.linspace(0, 40_000, 400)
    J_ct = [rc.lefm_J(rc.ct_K(p), 200e9, 0.3) for p in P_ct]
    P_sb = np.linspace(0, 9_000, 400)
    J_sb = [rc.lefm_J(rc.seb_K(p), 200e9, 0.3) for p in P_sb]
    ax2.plot(P_ct / 1e3, J_ct, lw=1.6, color="#4C72B0", label="CT: $J=K^2(1-\\nu^2)/E$")
    ax2.plot(P_sb / 1e3, J_sb, lw=1.6, color="#55A868", label="SE(B): $J=K^2(1-\\nu^2)/E$")
    p_ct = rc.implied_load(1957.7, "CT")
    p_sb = rc.implied_load(132.11, "SEB")
    ax2.plot([p_ct / 1e3], [1957.7], "o", ms=7, color="#4C72B0")
    ax2.annotate(f"report CT $J$=1957.7\n⇒ P≈{p_ct/1e3:.1f} kN (not stated)",
                 (p_ct / 1e3, 1957.7), textcoords="offset points", xytext=(12, 25), fontsize=7)
    ax2.plot([p_sb / 1e3], [132.11], "o", ms=7, color="#55A868")
    ax2.annotate(f"report SE(B) $J$=132.11\n⇒ P≈{p_sb/1e3:.1f} kN (not stated)",
                 (p_sb / 1e3, 132.11), textcoords="offset points", xytext=(-10, 45), fontsize=7)
    ax2.axvline(34.725, color="#4C72B0", ls="--", lw=1)
    ax2.annotate("CT $P_Q$=34 725 N\n⇒ J≈1.638e4 J/m²", (34.725, 4000),
                 textcoords="offset points", xytext=(-95, 10), fontsize=7, color="#4C72B0")
    ax2.axvline(7.782, color="#55A868", ls="--", lw=1)
    ax2.annotate("SE(B) LEFM peak\n7 782 N", (7.782, 900), textcoords="offset points",
                 xytext=(-70, 0), fontsize=7, color="#55A868")
    ax2.set_xlabel("load P [kN]")
    ax2.set_ylabel("elastic $J$ [J/m²]")
    ax2.set_yscale("log")
    ax2.set_title("(b) finding F1: the elastic-J rows imply an\nunstated evaluation load", fontsize=9)
    ax2.legend(fontsize=7, loc="lower right")

    fig.suptitle("wp-11204-04 independent review · report 11204 "
                 "(J2 elastoplastic + 3D cohesive, CT / SE(B))", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()