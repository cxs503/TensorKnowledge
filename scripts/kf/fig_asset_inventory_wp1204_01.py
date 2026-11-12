#!/usr/bin/env python3
"""Figure for wp-1204-01: asset inventory by kind × resolution status.

Numbers are read straight out of artifacts/wp-1204-01/asset_manifest.json —
nothing is typed by hand.  Writes artifacts/wp-1204-01/fig_asset_inventory.png
and docs/kf/wp-1204-01/fig_asset_inventory.png.
"""
from __future__ import annotations

import collections
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

MAN = "artifacts/wp-1204-01/asset_manifest.json"
OUT = "artifacts/wp-1204-01/fig_asset_inventory.png"
OUT2 = "docs/kf/wp-1204-01/fig_asset_inventory.png"

STATUS_ORDER = ["resolved", "metadata_only", "unresolved"]
COLORS = {"resolved": "#2f7d4f", "metadata_only": "#c9a227", "unresolved": "#9c3b3b"}


def main() -> None:
    man = json.load(open(MAN, encoding="utf-8"))
    kinds = [a["kind"] for a in man["assets"]]
    order = list(dict.fromkeys(kinds))
    grid = collections.Counter((a["kind"], a["resolution"]["status"]) for a in man["assets"])

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    left = [0] * len(order)
    for status in STATUS_ORDER:
        vals = [grid[(k, status)] for k in order]
        ax.barh(order, vals, left=left, color=COLORS[status], label=status)
        left = [a + b for a, b in zip(left, vals)]
    ax.set_xlabel("assets registered")
    ax.set_title(f"report {man['report_id']} asset inventory: "
                 f"{man['counts']['assets_total']} assets by kind / resolution")
    ax.legend(loc="lower right", fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.invert_yaxis()

    counts = man["counts"]
    ax2.bar(STATUS_ORDER, [counts[s] for s in STATUS_ORDER],
            color=[COLORS[s] for s in STATUS_ORDER])
    for i, s in enumerate(STATUS_ORDER):
        ax2.text(i, counts[s] + 0.1, str(counts[s]), ha="center", fontsize=9)
    ax2.set_ylabel("assets")
    ax2.set_title("resolution status "
                  f"(source sha256 {man['provenance']['source_hash'][7:19]}…)")
    ax2.set_ylim(0, max(counts.values()) + 2)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT2), exist_ok=True)
    for path in (OUT, OUT2):
        fig.savefig(path, dpi=130)
    print("wrote", OUT, "and", OUT2)


if __name__ == "__main__":
    main()