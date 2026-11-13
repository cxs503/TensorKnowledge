#!/usr/bin/env python3
"""Figure for wp-3076-04: claimed vs recomputed H1 deviation + coth root-existence map.

Reads artifacts/wp-3076-04/independent_check.json (produced by
independent_dispersion_check.py) so the plot cannot show numbers that the
reconstruction did not compute.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "wp-3076-04"
OUT = PKG / "fig_deviation_boundary.png"


def load_mod():
    spec = importlib.util.spec_from_file_location("idc_fig", PKG / "independent_dispersion_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    check = json.loads((PKG / "independent_check.json").read_text(encoding="utf-8"))
    dev = check["deviation_series"]["per_T"]
    Tc = check["no_root_probe"]["T_crit_analytic_s"]
    Ts = sorted(int(t) for t in dev)
    claimed = [dev[str(t)]["dev_claimed_pct"] for t in Ts]
    recomputed = [dev[str(t)]["dev_recomputed_pct"] for t in Ts]

    mod = load_mod()
    p = mod.parse_params(mod.load_md())
    grid = [10.0 + 0.05 * i for i in range(0, 201)]          # 10 .. 20 s
    roots = []
    for T in grid:
        r = mod.find_roots(p, "coth", T, n_scan=4000)
        roots.append(r[0][0] if r else None)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    ax1.semilogy(Ts, claimed, "o", ms=7, label="claimed in report 3076")
    ax1.semilogy(Ts, recomputed, "-", lw=1.8, label="recomputed (independent solver)")
    for t, c, r in zip(Ts, claimed, recomputed):
        ax1.annotate(f"{r:.3f}%", (t, r), textcoords="offset points", xytext=(4, 6), fontsize=8)
    ax1.axhline(3.0, color="0.6", ls="--", lw=1)
    ax1.text(Ts[0], 3.3, "3% line", fontsize=8, color="0.4")
    ax1.set_xlabel("wave period T (s)")
    ax1.set_ylabel("wavenumber deviation coth vs tanh (%)")
    ax1.set_title("H1 deviation series: claimed vs independently recomputed")
    ax1.set_xticks(Ts)
    ax1.grid(alpha=0.3, which="both")
    ax1.legend(fontsize=8)

    have = [(T, k) for T, k in zip(grid, roots) if k is not None]
    none = [T for T, k in zip(grid, roots) if k is None]
    if have:
        ax2.semilogy([t for t, _ in have], [k for _, k in have], lw=1.8,
                     label="coth root k in (0,10] 1/m")
    if none:
        ax2.axvspan(min(none), max(none), color="tab:red", alpha=0.12,
                    label="no coth root (k in (0,10])")
    ax2.axvline(Tc, color="k", ls="--", lw=1.2, label=f"analytic T_c={Tc:.2f} s")
    ax2.axvline(14.0, color="tab:orange", ls=":", lw=1.2, label="claim boundary T=14 s")
    ax2.set_xlabel("wave period T (s)")
    ax2.set_ylabel("coth-branch root k (1/m)")
    ax2.set_title("coth branch: root existence vs period")
    ax2.grid(alpha=0.3, which="both")
    ax2.legend(fontsize=7, loc="lower left")

    fig.suptitle("wp-3076-04 independent review of report 3076 (manuscript_gate H1)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())