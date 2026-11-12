#!/usr/bin/env python3
"""Figure for wp-5760-01: registered asset inventory, computed from the shipped manifest (no hand-typed numbers).

Output: docs/kf/wp-5760-01/figures/asset_inventory.png
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "docs" / "kf" / "wp-5760-01" / "asset_manifest.json"
OUT = REPO / "docs" / "kf" / "wp-5760-01" / "figures" / "asset_inventory.png"

RES_ORDER = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
RES_COLOR = {"resolved_in_source": "#2b7a3d", "referenced_unresolved": "#b5651d",
             "declared_absent": "#5b5b5b"}


def main() -> int:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = m["assets"]
    classes = sorted({a["asset_class"] for a in assets})
    grid = {c: {r: 0 for r in RES_ORDER} for c in classes}
    for a in assets:
        grid[a["asset_class"]][a["resolution"]] += 1
    totals = sorted(((c, sum(grid[c].values())) for c in classes), key=lambda kv: (kv[1], kv[0]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.4), gridspec_kw={"width_ratios": [2.1, 1]})

    names = [t[0] for t in totals]
    offsets = [0] * len(names)
    for res in RES_ORDER:
        vals = [grid[c][res] for c in names]
        ax1.barh(names, vals, left=offsets, color=RES_COLOR[res], label=res)
        offsets = [a + b for a, b in zip(offsets, vals)]
    for i, c in enumerate(names):
        ax1.text(offsets[i] + 0.2, i, str(offsets[i]), va="center", fontsize=9)
    ax1.set_xlabel("assets registered")
    ax1.set_title("wp-5760-01 asset inventory by class and resolution\n(source report 5760, %d assets, %d chars, sha256 %s…)"
                  % (m["counts"]["assets"], m["source"]["chars"], m["source"]["hash"][:12]), fontsize=10)
    ax1.legend(fontsize=8, loc="lower right")
    ax1.grid(axis="x", alpha=0.3)

    sums = [m["counts"][k] for k in RES_ORDER]
    bars = ax2.bar([r.replace("_", "\n") for r in RES_ORDER], sums,
                   color=[RES_COLOR[r] for r in RES_ORDER])
    for b, v in zip(bars, sums):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.3, str(v), ha="center", fontsize=9)
    ax2.set_ylabel("assets")
    ax2.set_title("resolution status\n(unresolved = cited but not byte-addressable here)", fontsize=10)
    ax2.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=140)
    print("wrote", OUT.relative_to(REPO), "bytes", OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())