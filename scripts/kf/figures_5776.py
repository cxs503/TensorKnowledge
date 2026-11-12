#!/usr/bin/env python3
"""Figures for wp-5776-01 (asset registration lane).

fig1_asset_inventory.png — registered assets by class, split by resolution status,
                           read straight from docs/kf/wp-5776-01/asset_manifest.json.
fig2_consistency.png     — arithmetic self-consistency of the report's sweep table
                           against the report's own closed form, read straight from
                           runs/wp-5776-01/consistency_check.json (no hand-typed numbers).

Usage: python3 scripts/kf/figures_5776.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / "wp-5776-01"
MANIFEST = OUT / "asset_manifest.json"
CONSIST = REPO / "runs" / "wp-5776-01" / "consistency_check.json"


def fig_inventory():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    classes = sorted({a["asset_class"] for a in m["assets"]})
    resolved = [sum(1 for a in m["assets"] if a["asset_class"] == c and a["resolution"] == "resolved_in_source") for c in classes]
    unresolved = [sum(1 for a in m["assets"] if a["asset_class"] == c and a["resolution"] != "resolved_in_source") for c in classes]

    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    y = range(len(classes))
    ax.barh(list(y), resolved, color="#2a7f62", label="resolved_in_source (locator span verified)")
    ax.barh(list(y), unresolved, left=resolved, color="#b5651d", label="referenced_unresolved (bytes/paths outside worktree)")
    ax.set_yticks(list(y))
    ax.set_yticklabels(classes, fontsize=9)
    ax.set_xlabel("registered assets (count)")
    ax.set_title("wp-5776-01 asset inventory — report 5776, %d assets, claims=[]" % len(m["assets"]), fontsize=10)
    for i, (r, u) in enumerate(zip(resolved, unresolved)):
        if r + u:
            ax.text(r + u + 0.05, i, str(r + u), va="center", fontsize=8)
    ax.legend(fontsize=8, loc="lower right")
    ax.set_xlim(0, max(r + u for r, u in zip(resolved, unresolved)) + 1.0)
    fig.tight_layout()
    p = OUT / "fig1_asset_inventory.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def fig_consistency():
    c = json.loads(CONSIST.read_text(encoding="utf-8"))
    rows = c["rows"]
    caps = sorted({r["D"] for r in rows})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.3))

    for d in caps:
        sub = [r for r in rows if r["D"] == d]
        ax1.plot([r["U_current"] for r in sub], [r["U_analytical_table"] for r in sub],
                 marker="o", lw=1.4, label="D=%.2f m (table)" % d)
    us = [r["U_current"] for r in rows]
    ax1.plot([min(us), max(us)], [min(us), max(us)], "k--", lw=1.0, label="U_anchor = U_current (no amplification)")
    ax1.set_xlabel("U_current [m/s]")
    ax1.set_ylabel("U_drift [m/s]")
    ax1.set_title("Reported anchor vs current (factor %.6f)" % c["factor"], fontsize=10)
    ax1.legend(fontsize=7)
    ax1.grid(alpha=0.3)

    labels = ["U=%.1f D=%.1f" % (r["U_current"], r["D"]) for r in rows]
    xs = range(len(rows))
    ax2.bar([x - 0.2 for x in xs], [100 * r["dev_analytical_rel"] for r in rows], width=0.4,
            color="#2a7f62", label="table U_analytical vs recomputed")
    ax2.bar([x + 0.2 for x in xs], [100 * r["dev_sim_rel"] for r in rows], width=0.4,
            color="#4d4d9e", label="table U_sim vs recomputed")
    ax2.axhline(c["summary"]["threshold_pct"], color="r", ls="--", lw=1.0, label="3%% threshold")
    ax2.set_yscale("log")
    ax2.set_xticks(list(xs))
    ax2.set_xticklabels(labels, rotation=60, ha="right", fontsize=6.5)
    ax2.set_ylabel("relative deviation [%] (log)")
    ax2.set_title("Self-consistency: max %.4f%% (analytical), %.4f%% (sim)"
                  % (c["summary"]["max_rel_dev_analytical_pct"], c["summary"]["max_rel_dev_sim_pct"]), fontsize=9)
    ax2.legend(fontsize=7)
    ax2.grid(alpha=0.3, axis="y")

    fig.suptitle("Report 5776 arithmetic self-consistency audit (not a platform verification)", fontsize=10)
    fig.tight_layout()
    p = OUT / "fig2_consistency.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def main():
    ps = [fig_inventory(), fig_consistency()]
    for p in ps:
        print(json.dumps({"figure": str(p.relative_to(REPO)),
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                          "bytes": p.stat().st_size}))


if __name__ == "__main__":
    main()