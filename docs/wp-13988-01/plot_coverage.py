"""Figure for wp-13988-01: what the manifest actually covers of report 13988.

Left panel  : each asset's char span on the source markdown (colored by resolution
              class) -> makes gaps/overlaps and over-claims visible at a glance.
Right panel : resolution-class counts and the classes that carry evidence.

Labels are ASCII on purpose: the only font installed in this container is
Noto Sans Regular (no CJK glyphs), so Chinese axis labels would render as tofu.

Usage: python3 docs/wp-13988-01/plot_coverage.py
Out   : docs/wp-13988-01/fig_manifest_coverage.png
"""
from __future__ import annotations

import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

WT = pathlib.Path(".").resolve()
MAN = WT / "artifacts" / "wp-13988-01" / "asset_manifest.json"
OUT = WT / "docs" / "wp-13988-01" / "fig_manifest_coverage.png"

COLOR = {"resolved_in_source": "#1f77b4",
         "referenced_unresolved": "#d62728",
         "declared_absent": "#7f7f7f"}


def main() -> int:
    man = json.loads(MAN.read_text())
    n = man["source"]["chars"]
    assets = man["assets"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 7.6),
                                   gridspec_kw={"width_ratios": [2.5, 1]})
    ys = list(range(len(assets)))
    for y, a in zip(ys, assets):
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        ax1.barh(y, e - s, left=s, height=0.62,
                 color=COLOR.get(a["resolution"], "#999999"),
                 edgecolor="black", linewidth=0.4)
    ax1.set_yticks(ys)
    ax1.set_yticklabels(["%s %s" % (a["asset_id"], a["asset_class"]) for a in assets], fontsize=7)
    ax1.invert_yaxis()
    ax1.set_xlim(0, n)
    ax1.set_xlabel("character offset in source markdown (%d chars, sha256-pinned)" % n, fontsize=9)
    ax1.set_title("wp-13988-01 asset spans over report 13988\n"
                  "(blue = resolved_in_source, red = referenced_unresolved)", fontsize=10)
    ax1.grid(axis="x", alpha=0.3)

    counts = man["counts"]["by_resolution"]
    labels = list(counts.keys())
    vals = [counts[k] for k in labels]
    bars = ax2.bar(range(len(labels)), vals,
                   color=[COLOR.get(k, "#999999") for k in labels])
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels([l.replace("_", "\n") for l in labels], fontsize=8)
    ax2.set_ylabel("number of assets", fontsize=9)
    ax2.set_title("resolution classes (%d assets, %d claims)"
                  % (man["counts"]["assets"], len(man.get("claims", []))), fontsize=10)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.1, str(v), ha="center", fontsize=9)
    ax2.set_ylim(0, max(vals) + 2)
    top = sorted(man["counts"]["by_class"].items(), key=lambda kv: -kv[1])[:8]
    ax2.text(0.02, 0.97, "top classes:\n" + "\n".join("%-22s %d" % kv for kv in top),
             transform=ax2.transAxes, va="top", fontsize=7, family="monospace")

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print("wrote", OUT.relative_to(WT), OUT.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())