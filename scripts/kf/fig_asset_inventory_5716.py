#!/usr/bin/env python3
"""Figure for wp-5716-01: asset inventory by class x resolution status (read from the manifest).

Numbers are read from docs/kf/wp-5716-01/asset_manifest.json — nothing is retyped.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PKG = "wp-5716-01"
MANIFEST = REPO / "docs" / "kf" / PKG / "asset_manifest.json"
OUT = REPO / "docs" / "kf" / PKG / "fig_asset_inventory.png"

STATUS_COLOR = {"resolved": "#2f7d32", "unresolved": "#b23c17", "metadata_only": "#8a6d00"}


def main() -> int:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = m["assets"]
    kinds = sorted({a["kind"] for a in assets})
    counts = Counter((a["kind"], a["resolution"]["status"]) for a in assets)
    statuses = [s for s in ("resolved", "unresolved", "metadata_only") if any(k[1] == s for k in counts)]

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    top = 0
    for kind in kinds:
        row = [counts.get((kind, s), 0) for s in statuses]
        total = sum(row)
        ax.barh(top, total, color="#d8d8d8")
        left = 0
        for s, v in zip(statuses, row):
            if v:
                ax.barh(top, v, left=left, color=STATUS_COLOR[s])
            left += v
        ax.text(total + 0.3, top, str(total), va="center", fontsize=9)
        top += 1
    ax.set_yticks(range(len(kinds)))
    ax.set_yticklabels(kinds, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("asset count")
    ax.set_title(
        "wp-5716-01 asset inventory (report 5716): %d assets, source sha256 %s..."
        % (len(assets), m["provenance"]["source_hash"].split("sha256:")[-1][:12]),
        fontsize=10,
    )
    handles = [plt.Rectangle((0, 0), 1, 1, color=STATUS_COLOR[s]) for s in statuses]
    ax.legend(handles, statuses, fontsize=8, loc="lower right", frameon=True)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=140)
    print("wrote %s" % OUT.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())