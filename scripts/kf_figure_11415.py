#!/usr/bin/env python3
"""Figure for KF work package wp-11415-01: asset-locator map of report 11415.

Pure function of the generated artifact (artifacts/wp-11415-01/asset_manifest.json),
so no number/label is hand-copied: the x-extents are the registered char spans,
the colours are the declared resolution status, the section rules are the
`## ` heading offsets found in the source markdown.

Writes docs/kf/wp-11415-01/fig_asset_locator_map.png
Run:  python3 scripts/kf_figure_11415.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import re  # noqa: E402

COLORS = {"resolved_in_source": "#2e7d32", "referenced_unresolved": "#ef6c00",
          "declared_absent": "#c62828"}
OUT = pathlib.Path("docs/kf/wp-11415-01/fig_asset_locator_map.png")


def main() -> int:
    manifest = json.loads(pathlib.Path("artifacts/wp-11415-01/asset_manifest.json").read_text())
    md = pathlib.Path("runs/wp-11415-01/report_11415.md").read_text()
    assets = manifest["assets"]
    n = len(assets)

    # section boundaries: char offset of each '## ' heading in the source markdown
    sections = []
    pos = 0
    for line in md.split("\n"):
        if line.startswith("## "):
            # label = section number only ("§1"…): the source headings are Chinese and no
            # CJK glyph is installed in this image, so non-ASCII text would render as tofu
            m = re.match(r"##\s*(\d+)\.", line)
            sections.append((pos, "§" + (m.group(1) if m else "?")))
        pos += len(line) + 1

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(13.2, 7.4), gridspec_kw={"width_ratios": [3.1, 1.0]}
    )
    for i, a in enumerate(assets):
        loc = a["locator"]
        y = n - i
        ax.barh(y, loc["end_char"] - loc["start_char"], left=loc["start_char"], height=0.62,
                color=COLORS[a["resolution"]], edgecolor="black", linewidth=0.4,
                alpha=0.9, zorder=3)
        ax.text(-40, y, a["asset_id"], ha="right", va="center", fontsize=7.6)
    for x, name in sections:
        ax.axvline(x, color="#546e7a", lw=0.6, ls=":", zorder=1)
        ax.text(x + 25, n + 1.15, name, rotation=0, fontsize=7.2, va="bottom", color="#37474f")

    ax.set_ylim(0.2, n + 2.1)
    ax.set_xlim(-40, len(md) + 40)
    ax.set_yticks([])
    ax.set_xlabel("character offset in report markdown (0 … %d)" % len(md), fontsize=9)
    ax.set_title("wp-11415-01 · registered asset locators in tensor://reports/11415\n"
                 "%d assets · %d chars · source sha256 %s…"
                 % (n, len(md), manifest["source"]["hash"][:16]), fontsize=10, loc="left")
    ax.grid(axis="x", lw=0.3, alpha=0.5, zorder=0)
    ax.legend(handles=[Patch(facecolor=c, edgecolor="black", label=k.replace("_", " "))
                       for k, c in COLORS.items()],
              loc="lower right", fontsize=8, framealpha=0.95)

    res = manifest["counts"]["by_resolution"]
    order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    bars = ax2.bar(range(len(order)), [res.get(k, 0) for k in order],
                   color=[COLORS[k] for k in order], edgecolor="black", linewidth=0.5)
    for b, k in zip(bars, order):
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.25,
                 str(res.get(k, 0)), ha="center", fontsize=9, fontweight="bold")
    ax2.set_xticks(range(len(order)))
    ax2.set_xticklabels([k.replace("_", "\n") for k in order], fontsize=8)
    ax2.set_ylabel("assets", fontsize=9)
    ax2.set_title("resolution status\n(total %d)" % n, fontsize=10, loc="left")
    ax2.set_ylim(0, max(res.values()) + 2.5)
    ax2.grid(axis="y", lw=0.3, alpha=0.5)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170)
    png = OUT.read_bytes()
    print("figure:", OUT, "bytes:", len(png), "sha256:", hashlib.sha256(png).hexdigest())
    print("sections:", len(sections), "assets:", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())