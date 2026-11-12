#!/usr/bin/env python3
"""Render the wp-946-01 result figure from asset_manifest.json (no hand-typed numbers).

fig1_asset_registration.png
  left  : asset count per kind, stacked resolvable vs unresolved
  right : verification face of the registration — locator evidence verified vs
          assets that stay unresolved (with the hash/span check counters)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures" / "fig1_asset_registration.png"


def main() -> int:
    man = json.loads((HERE / "asset_manifest.json").read_text(encoding="utf-8"))
    sc = json.loads((HERE / "selfcheck.json").read_text(encoding="utf-8"))
    assets = man["assets"]

    kinds = sorted({a["kind"] for a in assets})
    res = [sum(1 for a in assets if a["kind"] == k and a["resolvable"]) for k in kinds]
    unres = [sum(1 for a in assets if a["kind"] == k and not a["resolvable"]) for k in kinds]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 6.2))

    y = range(len(kinds))
    ax1.barh(list(y), res, color="#2a7f62", label="resolvable (bytes in report store)")
    ax1.barh(list(y), unres, left=res, color="#b5651d", label="unresolved (reference only)")
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(kinds, fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("number of registered assets")
    ax1.set_title(
        f"report 946 asset registration: {len(assets)} assets "
        f"({sum(res)} resolvable / {sum(unres)} unresolved)",
        fontsize=10,
    )
    for i, (r, u) in enumerate(zip(res, unres)):
        ax1.text(r + u + 0.05, i, f"{r + u}", va="center", fontsize=8)
    ax1.legend(fontsize=8, loc="lower right")
    ax1.grid(axis="x", alpha=0.3)

    md_loc = sc["markdown_locators_verified"]
    rec_loc = sc["record_locators_verified"]
    bars = [
        ("markdown locators\n(md[start:end] == quote)", md_loc, "#2a7f62"),
        ("record locators\n(field value re-read)", rec_loc, "#2a7f62"),
        ("unresolved assets\n(with explicit reason)", sum(unres), "#b5651d"),
    ]
    ax2.bar([b[0] for b in bars], [b[1] for b in bars], color=[b[2] for b in bars], width=0.55)
    for i, b in enumerate(bars):
        ax2.text(i, b[1] + 0.3, str(b[1]), ha="center", fontsize=10)
    ax2.set_ylabel("count")
    ax2.set_title(
        "verification face (validator re-derived, not self-assigned)\n"
        f"hash match={man['source']['hash_check']['match']} · "
        f"chars match={man['source']['chars_check']['match']} · "
        f"failures={len(sc['failures'])}",
        fontsize=10,
    )
    ax2.set_ylim(0, max(b[1] for b in bars) * 1.25)
    ax2.grid(axis="y", alpha=0.3)
    ax2.tick_params(axis="x", labelsize=8)

    fig.suptitle(
        "wp-946-01 / report 946 — asset registration (no extraction, no verification marks)",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())