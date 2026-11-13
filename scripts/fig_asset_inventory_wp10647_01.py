"""Inventory figure for work package wp-10647-01 (asset registration of report 10647).

Three panels, all numbers read from artifacts/wp-10647-01/asset_manifest.json (no hand input):
  (a) assets by resolution class (resolved_in_source / referenced_unresolved / declared_absent)
  (b) assets by asset_class
  (c) locator map: char span of every asset along the report document, shaded by resolution

Output: artifacts/wp-10647-01/fig1_asset_resolution.png (and docs/kf/wp-10647-01/ copy)
Usage : python3 scripts/fig_asset_inventory_wp10647_01.py
"""
from __future__ import annotations

import json
import pathlib
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MANIFEST = pathlib.Path("artifacts/wp-10647-01/asset_manifest.json")
OUT = pathlib.Path("artifacts/wp-10647-01/fig1_asset_resolution.png")
DOC_COPY = pathlib.Path("docs/kf/wp-10647-01/fig1_asset_resolution.png")
COLORS = {"resolved_in_source": "#2b7a3d", "referenced_unresolved": "#c98a00",
          "declared_absent": "#a83232"}


def main() -> int:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = m["assets"]
    res_labels = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    res_vals = [m["counts"]["by_resolution"].get(k, 0) for k in res_labels]
    cls = sorted(m["counts"]["by_class"].items(), key=lambda kv: (-kv[1], kv[0]))

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 6.2),
                             gridspec_kw={"width_ratios": [1.0, 1.5, 1.5]})
    ax = axes[0]
    bars = ax.bar(range(3), res_vals, color=[COLORS[k] for k in res_labels])
    ax.set_xticks(range(3))
    ax.set_xticklabels(["resolved\nin source", "referenced\nunresolved", "declared\nabsent"], fontsize=9)
    ax.set_ylabel("assets")
    ax.set_title("(a) resolution class (%d assets)" % m["counts"]["assets"], fontsize=11)
    for b, v in zip(bars, res_vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, str(v), ha="center", fontsize=10)
    ax.set_ylim(0, max(res_vals) * 1.25)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    names = [k for k, _ in cls][::-1]
    vals = [v for _, v in cls][::-1]
    ax.barh(range(len(names)), vals, color="#3b5f8a")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("assets")
    ax.set_title("(b) asset_class distribution (%d classes)" % len(names), fontsize=11)
    for i, v in enumerate(vals):
        ax.text(v + 0.1, i, str(v), va="center", fontsize=8)
    ax.set_xlim(0, max(vals) * 1.2)
    ax.grid(axis="x", alpha=0.3)

    ax = axes[2]
    md_len = m["source"]["chars"]
    for i, a in enumerate(assets):
        loc = a["locator"]
        ax.barh(i, loc["end_char"] - loc["start_char"], left=loc["start_char"], height=0.7,
                color=COLORS[a["resolution"]])
    ax.set_ylim(-0.6, len(assets) - 0.4)
    ax.set_yticks(range(len(assets)))
    ax.set_yticklabels([a["asset_id"] for a in assets], fontsize=7)
    ax.set_xlabel("char offset in source markdown (len=%d)" % md_len)
    ax.set_title("(c) locator spans (verbatim char slices)", fontsize=11)
    ax.axvline(md_len, color="k", lw=0.8, ls=":")
    for k, c in COLORS.items():
        ax.plot([], [], color=c, lw=6, label=k)
    ax.legend(fontsize=7, loc="lower right", framealpha=0.9)
    ax.grid(axis="x", alpha=0.3)

    fig.suptitle("report 10647 asset registration - package wp-10647-01 - "
                 "sha256 aa10fd7a..bf31 - claims=0 (registration only, no extraction); "
                 "labels in ASCII because no CJK font is installed in this image",
                 fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    DOC_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUT, DOC_COPY)
    print("wrote", OUT, OUT.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
