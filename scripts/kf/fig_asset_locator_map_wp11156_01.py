#!/usr/bin/env python3
"""wp-11156-01 figure: where the 21 registered assets sit in the 4478-char source.

Every x coordinate is read from docs/kf/wp-11156-01/asset_manifest.json
(locator.start_char / end_char, or the full-document span for the document-level
locator); nothing is hand-typed, so the figure cannot drift from the manifest.

Output: docs/kf/wp-11156-01/asset_locator_map.png (artifacts/ is git-ignored in this repo)
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-11156-01")
OUT = os.path.join(ROOT, "docs", "kf", "wp-11156-01", "asset_locator_map.png")

COLORS = {
    "resolved_in_source": "#1f77b4",
    "referenced_unresolved": "#d62728",
    "declared_only": "#ff7f0e",
}


def main() -> None:
    manifest = json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))
    source = open(os.path.join(PKG, "source.md"), encoding="utf-8").read()
    total = len(source)

    # section boundaries from the markdown headings (char offsets)
    bounds = []
    for line in source.split("\n"):
        if line.startswith("## "):
            bounds.append((source.index("\n" + line + "\n") + 1, line[3:]))

    assets = manifest["assets"]
    fig, ax = plt.subplots(figsize=(11, 7))
    for row, a in enumerate(assets):
        loc = a["locator"]
        x0, x1 = loc["start_char"], loc["end_char"]
        if x0 is None:  # record-level locator: no markdown span exists, drawn hatched
            ax.barh(row, total, left=0, color="white", edgecolor=COLORS["declared_only"],
                    hatch="///", height=0.5, lw=0.5)
            ax.text(total * 0.5, row, "record.figures (no markdown span)",
                    va="center", ha="center", fontsize=6, color="#8a4b00")
            continue
        ax.barh(row, max(x1 - x0, total * 0.004), left=x0,
                color=COLORS.get(a["resolution"], "grey"), height=0.62)
        ax.text(x1 + total * 0.006, row, a["kind"], va="center", fontsize=7, color="#333333")

    for x, name in bounds:
        ax.axvline(x, color="#bbbbbb", lw=0.7, ls=":")
        ax.text(x, len(assets) - 0.2, name, rotation=90, fontsize=6,
                va="bottom", ha="right", color="#777777")

    ax.set_yticks(range(len(assets)))
    ax.set_yticklabels([a["asset_id"] for a in assets], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, total)
    ax.set_xlabel("character offset in report 11156 markdown (len = %d chars)" % total)
    ax.set_title("wp-11156-01 asset locators in source (n=%d; quote-verified spans)" % len(assets))
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COLORS.values()]
    ax.legend(handles, list(COLORS), fontsize=7, loc="lower right")
    ax.grid(axis="x", color="#eeeeee", lw=0.5)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print("wrote", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()