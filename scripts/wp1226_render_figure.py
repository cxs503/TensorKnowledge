#!/usr/bin/env python3
"""Render the wp-1226-01 evidence figure from the registered manifest (no hand-typed numbers).

fig1_asset_resolution.png: per-asset resolution status for report 1226.
Left panel  — 22 registered assets grouped by kind, coloured resolved/unresolved.
Right panel — locator counts per source_field (markdown char-span vs record field).
"""
from __future__ import annotations

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

WT = pathlib.Path(__file__).resolve().parent.parent
PKG = WT / "docs" / "kf" / "wp-1226-01"


def main() -> int:
    man = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    assets = man["assets"]
    labels = [f"{a['asset_id']}  {a['kind']}" for a in assets]
    colors = ["#2b8a3e" if a["status"] == "resolved" else "#c92a2a" for a in assets]
    locs = [len(a["locators"]) for a in assets]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(14, 7.2), gridspec_kw={"width_ratios": [3.1, 1]}
    )
    y = range(len(assets))
    ax1.barh(list(y), locs, color=colors)
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(labels, fontsize=7)
    ax1.invert_yaxis()
    ax1.set_xlabel("number of locators registered per asset")
    ax1.set_title(
        "report 1226 asset registration: %d assets (%d resolved / %d unresolved)"
        % (len(assets), man["asset_counts"]["resolved"], man["asset_counts"]["unresolved"]),
        fontsize=10,
    )
    for yi, n in zip(y, locs):
        ax1.text(n + 0.05, yi, str(n), va="center", fontsize=7)

    from collections import Counter

    field_counts = Counter(
        l.get("source_field") for a in assets for l in a.get("locators", [])
    )
    kinds = sorted(field_counts)
    ax2.bar(kinds, [field_counts[k] for k in kinds], color="#1c7ed6")
    for i, k in enumerate(kinds):
        ax2.text(i, field_counts[k], str(field_counts[k]), ha="center", va="bottom", fontsize=9)
    ax2.set_ylabel("locators")
    ax2.set_title("locator provenance by source_field", fontsize=10)
    ax2.tick_params(axis="x", labelsize=8)

    src = man["source"]
    fig.text(
        0.01,
        0.005,
        "source sha256=%s...  chars=%d  bytes=%d"
        % (src["sha256"][:23], src["chars"], src["byte_length_utf8"]),
        fontsize=7,
        family="monospace",
    )
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    out = PKG / "fig1_asset_resolution.png"
    fig.savefig(out, dpi=150)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())