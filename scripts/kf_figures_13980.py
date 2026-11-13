#!/usr/bin/env python3
"""Figures for work package wp-13980-01 — asset-registration coverage of report 13980.

Every plotted number is read from artifacts/wp-13980-01/asset_manifest.json, i.e. from the
registration program's own output; nothing is typed by hand.

Output: docs/kf/wp-13980-01/fig1_asset_registration.png
"""
from __future__ import annotations

import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = pathlib.Path("docs/kf/wp-13980-01")
MAN = pathlib.Path("artifacts/wp-13980-01/asset_manifest.json")

COL = {"resolved_in_source": "#2c7fb8", "referenced_unresolved": "#fdae61",
       "declared_absent": "#d73027"}


def main() -> int:
    m = json.loads(MAN.read_text())
    assets = sorted(m["assets"], key=lambda a: a["locator"]["start_char"])
    n_chars = m["source"]["chars"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7),
                                   gridspec_kw={"width_ratios": [2.1, 1]})

    for i, a in enumerate(assets):
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        ax1.barh(i, e - s, left=s, height=0.62, color=COL[a["resolution"]],
                 edgecolor="black", linewidth=0.4)
        ax1.text(n_chars * 1.005, i, f"{a['asset_class']} · {a['resolution_check']['result']}",
                 va="center", fontsize=7)
    ax1.set_yticks(range(len(assets)))
    ax1.set_yticklabels([a["asset_id"] for a in assets], fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlim(0, n_chars * 1.02)
    ax1.set_xlabel(f"char offset in source markdown (chars={n_chars})")
    ax1.set_title("A: registered asset locator spans in the source markdown (coloured by resolution)", fontsize=9)
    for k, v in COL.items():
        ax1.barh([], [], color=v, label=k)
    ax1.legend(fontsize=7, loc="lower right", framealpha=0.9)

    counts = m["counts"]
    keys = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    vals = [counts[k] for k in keys]
    bars = ax2.bar(range(len(keys)), vals, color=[COL[k] for k in keys],
                   edgecolor="black", linewidth=0.4)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.15, str(v),
                 ha="center", fontsize=10, fontweight="bold")
    ax2.set_xticks(range(len(keys)))
    ax2.set_xticklabels([k.replace("_", "\n") for k in keys], fontsize=8)
    ax2.set_ylabel("number of assets")
    ax2.set_ylim(0, max(vals) + 1.4)
    ax2.set_title("B: resolution distribution (assets=%d)" % counts["assets"], fontsize=10)
    ax2.text(0.5, 0.06,
             "sha256 %s...\nchars %d / bytes %d\nclaims=%d (empty allowed)"
             % (m["source"]["hash"][:16], m["source"]["chars"],
                m["source"]["bytes_utf8"], len(m["claims"])),
             transform=ax2.transAxes, ha="center", fontsize=7.5,
             bbox=dict(boxstyle="round", fc="#f0f0f0", ec="gray"))

    fig.suptitle("wp-13980-01 / report 13980 asset registration coverage (data source: asset_manifest.json)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / "fig1_asset_registration.png"
    fig.savefig(png, dpi=150)
    print("wrote", png, png.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())