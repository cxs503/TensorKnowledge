#!/usr/bin/env python3
"""Render the one evidence figure for wp-946-04 from the upstream manifest.

Figure: per-kind asset resolution status of wp-946-01 (what the report store can
actually serve vs what is only a pointer). No plotting of anything not present in
docs/kf/wp-946-04/upstream/wp-946-01.kf_result.json.

Usage: python3 docs/kf/wp-946-04/make_figure.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PKG = Path(__file__).resolve().parent
UP = PKG / "upstream" / "wp-946-01.kf_result.json"
OUT = PKG / "figures" / "fig1_asset_status_by_kind.png"


def main() -> None:
    assets = json.loads(UP.read_text(encoding="utf-8"))["outputs"]["asset_manifest.json"]["assets"]
    kinds = sorted({a["kind"] for a in assets})
    res = Counter(a["kind"] for a in assets if a["status"] == "resolvable")
    unrs = Counter(a["kind"] for a in assets if a["status"] == "unresolved")

    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150)
    y = range(len(kinds))
    ax.barh(list(y), [res[k] for k in kinds], color="#2e7d32", label="resolvable (served by report store)")
    ax.barh(list(y), [unrs[k] for k in kinds], left=[res[k] for k in kinds], color="#c62828",
            label="unresolved (pointer outside report store)")
    ax.set_yticks(list(y))
    ax.set_yticklabels(kinds, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("assets (wp-946-01, n=%d)" % len(assets))
    ax.set_title("wp-946-01 asset registration: what report 946 can actually serve")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="x", alpha=0.3)
    for i, k in enumerate(kinds):
        total = res[k] + unrs[k]
        ax.text(total + 0.05, i, str(total), va="center", fontsize=8)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    print(json.dumps({"figure": str(OUT), "kinds": len(kinds), "assets": len(assets)}))


if __name__ == "__main__":
    main()
