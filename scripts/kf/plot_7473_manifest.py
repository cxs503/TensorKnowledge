#!/usr/bin/env python3
"""Figure for wp-7473-01 delivery report: asset registry composition, plotted straight
from docs/kf/wp-7473-01/asset_manifest.json (no hand-copied numbers)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "docs" / "kf" / "wp-7473-01" / "asset_manifest.json"
OUT = REPO / "docs" / "kf" / "wp-7473-01" / "fig_asset_resolution.png"

RES_ORDER = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
COLORS = {"resolved_in_source": "#2a7ae2", "referenced_unresolved": "#9aa5b1", "declared_absent": "#c0392b"}


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = m["assets"]
    classes = sorted({a["asset_class"] for a in assets},
                     key=lambda c: (-sum(1 for a in assets if a["asset_class"] == c), c))

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.2), gridspec_kw={"width_ratios": [2.4, 1]})
    left = [0] * len(classes)
    for res in RES_ORDER:
        vals = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"]["status"] == res) for c in classes]
        ax.barh(classes, vals, left=left, color=COLORS[res], label="%s (%d)" % (res, sum(vals)))
        left = [x + y for x, y in zip(left, vals)]
    ax.set_xlabel("assets")
    ax.set_title("report %s asset registry: %d assets by class x resolution" % (m["report_id"], len(assets)))
    ax.legend(loc="lower right", fontsize=8)
    ax.invert_yaxis()
    for i, c in enumerate(classes):
        ax.text(left[i] + 0.2, i, str(left[i]), va="center", fontsize=8)
    ax.grid(axis="x", alpha=0.3)

    by_res = m["counts"]["by_resolution"]
    vals = [by_res.get(r, 0) for r in RES_ORDER]
    ax2.bar([r.replace("_", "\n") for r in RES_ORDER], vals, color=[COLORS[r] for r in RES_ORDER])
    for i, v in enumerate(vals):
        ax2.text(i, v + 0.3, str(v), ha="center", fontsize=9)
    ax2.set_ylabel("assets")
    ax2.set_title("resolution of %d locators" % len(assets))
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle(
        "wp-7473-01 — source sha256 %s…%s, %d chars / %d bytes, claims=%d"
        % (m["source"]["source_hash"][7:19], m["source"]["source_hash"][-8:],
           m["source"]["chars"], m["source"]["bytes_utf8"], len(m["claims"])),
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT, dpi=140)
    print("wrote %s (%d bytes)" % (OUT.relative_to(REPO), OUT.stat().st_size))


if __name__ == "__main__":
    main()