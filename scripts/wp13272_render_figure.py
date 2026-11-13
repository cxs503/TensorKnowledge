#!/usr/bin/env python3
"""wp-13272-01 · render fig1_asset_resolution.png from asset_manifest.json.

Left: per-asset locator counts, green=resolved / red=unresolved.
Right: asset kind distribution.
All numbers read from the manifest at run time (zero hand-copy).
"""
from __future__ import annotations

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

WT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = WT / "docs" / "kf" / "wp-13272-01"


def main() -> int:
    m = json.loads((OUT_DIR / "asset_manifest.json").read_text())
    assets = m["assets"]
    counts = m["counts"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.5), dpi=140)

    ids = [a["asset_id"].replace("ast-13272-", "") for a in assets]
    nloc = [len(a["locators"]) for a in assets]
    colors = ["#2e7d32" if a["status"] == "resolved" else "#c62828" for a in assets]
    ax1.bar(range(len(assets)), nloc, color=colors)
    ax1.set_xticks(range(len(assets)))
    ax1.set_xticklabels(ids, rotation=90, fontsize=7)
    ax1.set_ylabel("locators")
    ax1.set_title(f"assets={counts['assets']}  resolved={counts['resolved']}  unresolved={counts['unresolved']}")
    ax1.grid(axis="y", alpha=0.3)

    kinds: dict[str, int] = {}
    for a in assets:
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
    items = sorted(kinds.items(), key=lambda kv: -kv[1])
    ax2.barh([k for k, _ in items], [v for _, v in items], color="#1565c0")
    ax2.set_xlabel("assets")
    ax2.set_title("asset kind distribution")
    ax2.grid(axis="x", alpha=0.3)

    fig.suptitle(
        "wp-13272-01 · report 13272 asset registration\n"
        f"sha256={m['source']['sha256'][:19]}…  chars={m['source']['chars']}",
        fontsize=10,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    out = OUT_DIR / "fig1_asset_resolution.png"
    fig.savefig(out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
