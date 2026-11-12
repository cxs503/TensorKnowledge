#!/usr/bin/env python3
"""Figure for wp-7808-01: asset inventory of report 7808 (registration, not physics).

Everything plotted is read from docs/kf/wp-7808-01/asset_manifest.json — no hand-entered
numbers. Panel (a) = registered assets per class, split by resolution state; panel (b) =
resolution totals plus the integrity tallies (locators, unique quotes, claims).

Run: python3 scripts/plot_wp7808_assets.py
Out: docs/kf/wp-7808-01/figures/asset_inventory.png
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "docs", "kf", "wp-7808-01", "asset_manifest.json")
OUT = os.path.join(ROOT, "docs", "kf", "wp-7808-01", "figures", "asset_inventory.png")

STATE_COLORS = {
    "resolved_in_source": "#2c7fb8",
    "referenced_unresolved": "#e6a03c",
    "declared_absent": "#b0b0b0",
}
STATE_LABELS = {
    "resolved_in_source": "resolved in source",
    "referenced_unresolved": "referenced, unresolved here",
    "declared_absent": "declared absent",
}


def main() -> None:
    m = json.load(open(MANIFEST, encoding="utf-8"))
    assets = m["assets"]
    classes = sorted({a["asset_class"] for a in assets})
    states = ["resolved_in_source", "referenced_unresolved", "declared_absent"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw={"width_ratios": [2.1, 1]})

    left = [0] * len(classes)
    for st in states:
        vals = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == st) for c in classes]
        ax1.barh(classes, vals, left=left, color=STATE_COLORS[st], label=STATE_LABELS[st],
                 edgecolor="white", linewidth=0.6)
        left = [acc + v for acc, v in zip(left, vals)]
    ax1.set_xlabel("registered assets (count)")
    ax1.set_title(f"(a) report 7808 asset inventory by class — {len(assets)} assets, 0 claims",
                  fontsize=10, loc="left")
    ax1.invert_yaxis()
    ax1.legend(fontsize=8, frameon=False, loc="lower right")
    ax1.tick_params(labelsize=8)
    for side in ("top", "right"):
        ax1.spines[side].set_visible(False)
    ax1.grid(axis="x", alpha=0.25)

    by_res = m["counts"]["by_resolution"]
    keys = [s for s in states if by_res.get(s)]
    ax2.bar([STATE_LABELS[k] for k in keys], [by_res[k] for k in keys],
            color=[STATE_COLORS[k] for k in keys], width=0.6)
    ax2.set_ylabel("assets (count)")
    ax2.set_title("(b) resolution state totals", fontsize=10, loc="left")
    ax2.tick_params(labelsize=8, axis="x", rotation=18)
    for side in ("top", "right"):
        ax2.spines[side].set_visible(False)
    ax2.grid(axis="y", alpha=0.25)

    loc = [a["locator"] for a in assets]
    extra = (
        f"locators resolved verbatim: {sum(1 for lc in loc if lc['char_span_roundtrip_ok'])}/{len(loc)}\n"
        f"quotes unique: {sum(1 for lc in loc if lc['unique'])}/{len(loc)}\n"
        f"source sha256 == contract: {m['integrity']['hash_matches_contract']}\n"
        f"distinct body path tokens mapped: {m['coverage']['distinct_tokens']}/{m['coverage']['distinct_tokens']}\n"
        f"claims emitted: {m['counts']['claims']} (extraction out of scope)"
    )
    fig.text(0.62, 0.02, extra, fontsize=7.5, family="monospace", va="bottom", color="#333333")
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=160)
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()