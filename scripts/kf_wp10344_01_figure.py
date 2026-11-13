#!/usr/bin/env python3
"""wp-10344-01 | figure: source-locator map of the registered assets.

Panel (a): every registered asset's char span on the report markdown (0..2898 chars),
           section boundaries drawn from the headings parsed out of source.md.
Panel (b): registry composition by resolution class and by asset class.

All numbers come from docs/kf/wp-10344-01/asset_manifest.json (+ source.md); nothing is
typed in by hand. Output: docs/kf/wp-10344-01/figures/wp10344_01_locator_map.png
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-10344-01")
OUT = os.path.join(PKG, "figures", "wp10344_01_locator_map.png")

CLASS_COLOR = {
    "figure": "#1f77b4",
    "source_module": "#2ca02c",
    "test_file": "#9467bd",
    "benchmark_entrypoint": "#8c564b",
    "result_table": "#ff7f0e",
    "repro_command": "#d62728",
    "scope_declaration": "#7f7f7f",
    "dataset": "#bcbd22",
}


def main() -> None:
    man = json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))
    md = open(os.path.join(PKG, "source.md"), encoding="utf-8").read()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14, 6.4),
                                  gridspec_kw={"width_ratios": [2.6, 1.0]})

    # ---- panel (a): spans ----
    heads = man["headings"]
    for h in heads:
        pos = md.find(h)
        ax.axvline(pos, color="#cccccc", lw=0.8, zorder=0)
        label = h.lstrip("# ").split(" ")[0]
        ax.text(pos + 8, -1.35, h[:34], rotation=90, fontsize=6.2, color="#666666",
                va="bottom", ha="left")

    assets = sorted(man["assets"], key=lambda a: a["locator"]["start_char"])
    y = 0
    for a in assets:
        loc = a["locator"]
        c = CLASS_COLOR.get(a["asset_class"], "#000000")
        style = "-" if a["resolution"] == "resolved_in_source" else ("--" if a["resolution"] == "referenced_unresolved" else ":")
        ax.hlines(y, loc["start_char"], loc["end_char"], color=c, lw=5, linestyle=style,
                  alpha=0.95 if a["resolution"] == "resolved_in_source" else 0.6)
        ax.text(-30, y, f"{a['asset_id']}", fontsize=7, ha="right", va="center", color=c)
        ax.text(loc["end_char"] + 18, y, a["label"][:38], fontsize=6.6, va="center", color="#333333")
        y += 1

    ax.set_xlim(-40, len(md) * 1.28)
    ax.set_ylim(-2.2, y - 0.2)
    ax.set_yticks([])
    ax.set_xlabel(f"char offset in report markdown (total {len(md)} chars, sha256 {man['source_hash'][7:19]}...)")
    ax.set_title("(a) wp-10344-01 asset locators on report 10344 (solid=resolved_in_source, dashed=referenced_unresolved)")
    ax.grid(axis="x", color="#eeeeee", lw=0.5, zorder=0)
    handles = [plt.Line2D([0], [0], color=c, lw=4, label=k) for k, c in CLASS_COLOR.items()
               if any(a["asset_class"] == k for a in assets)]
    handles.append(plt.Line2D([0], [0], color="#444444", lw=2, linestyle="--", label="referenced_unresolved"))
    ax.legend(handles=handles, fontsize=6.4, loc="lower right", ncol=2, framealpha=0.9)

    # ---- panel (b): registry composition ----
    res = man["counts"]["by_resolution"]
    order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    vals = [res.get(k, 0) for k in order]
    colors = ["#2e7d32", "#c62828", "#616161"]
    bars = ax2.barh(range(len(order)), vals, color=colors, height=0.55)
    ax2.set_yticks(range(len(order)))
    ax2.set_yticklabels(order, fontsize=7.5)
    ax2.invert_yaxis()
    for b, v in zip(bars, vals):
        ax2.text(b.get_width() + 0.12, b.get_y() + b.get_height() / 2, str(v),
                 va="center", fontsize=8)
    ax2.set_xlim(0, max(vals) + 2)
    ax2.set_xlabel("assets")
    ax2.set_title(f"(b) resolution classes, {man['counts']['assets']} assets total")
    ax2.grid(axis="x", color="#eeeeee", lw=0.5)

    fig.suptitle(f"report 10344 · scenario {man['scenario_key']} · quotes "
                 f"{man['integrity']['quote_uniqueness']['unique_quotes']}/"
                 f"{man['integrity']['quote_uniqueness']['quotes']} unique-resolvable",
                 fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT, dpi=190)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()