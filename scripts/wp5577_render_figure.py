#!/usr/bin/env python3
"""Render fig1_asset_resolution.png for wp-5577-01 from asset_manifest.json.

All numbers are read from the manifest at runtime (zero hand-copy).
Usage: python3 scripts/wp5577_render_figure.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-5577-01"


def main() -> None:
    m = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    assets = m["assets"]
    n = len(assets)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6),
                                   gridspec_kw={"width_ratios": [2.2, 1]})
    colors = {"resolved": "#2e8b57", "unresolved": "#c0392b"}
    for i, a in enumerate(assets):
        ax1.barh(i, 1, color=colors[a["status"]], height=0.72)
        ax1.text(1.02, i, f"{a['asset_id'][-2:]} {a['kind']}",
                 va="center", fontsize=7.5)
    ax1.set_ylim(-0.6, n - 0.4)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 1.6)
    ax1.set_xticks([])
    ax1.set_title("wp-5577-01 asset resolution (report 5577)", fontsize=10)
    ax1.set_xlabel("status: green=resolved, red=unresolved (declared, no byte payload)",
                  fontsize=8)

    kinds = Counter(a["kind"] for a in assets)
    ax2.barh(list(kinds.keys()), list(kinds.values()), color="#34699a", height=0.6)
    for i, v in enumerate(kinds.values()):
        ax2.text(v + 0.05, i, str(v), va="center", fontsize=8)
    ax2.set_title(f"asset kinds (total={n})", fontsize=10)
    ax2.set_xlabel("count", fontsize=8)

    fig.tight_layout()
    out = PKG / "fig1_asset_resolution.png"
    fig.savefig(out, dpi=140)
    print(out)


if __name__ == "__main__":
    main()
