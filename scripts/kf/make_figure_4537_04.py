#!/usr/bin/env python3
"""Generate review overview figure for wp-4537-04.

Reads the upstream asset manifest and produces a two-panel figure:
  Left: asset status distribution (resolved / declared_metadata_only / declared_shorthand / declared_only)
  Right: asset kind distribution

Usage:
    python3 scripts/kf/make_figure_4537_04.py [--out <dir>]

Zero hand-copied numbers: every value is counted from
docs/kf/wp-4537-01/asset_manifest.json at render time.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "kf" / "wp-4537-01" / "asset_manifest.json"


def main():
    parser = argparse.ArgumentParser(description="Make wp-4537-04 review figure")
    parser.add_argument("--out", default="docs/kf/wp-4537-04", help="output directory")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = m["assets"]
    by_status = Counter(a["status"] for a in assets)
    by_kind = Counter(a["kind"] for a in assets)
    kinds = sorted(by_kind, key=lambda k: (-by_kind[k], k))

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12, 4.5), gridspec_kw={"width_ratios": [1, 1.2]}
    )

    # Left: status distribution
    status_order = ["resolved", "declared_metadata_only", "declared_shorthand", "declared_only"]
    colors = {
        "resolved": "#2e7d32",
        "declared_metadata_only": "#f9a825",
        "declared_shorthand": "#ef6c00",
        "declared_only": "#6d4c41",
    }
    st = [s for s in status_order if s in by_status]
    ax1.bar(range(len(st)), [by_status[s] for s in st], color=[colors[s] for s in st])
    ax1.set_xticks(range(len(st)))
    ax1.set_xticklabels([s.replace("_", "\n") for s in st], fontsize=7)
    ax1.set_ylabel("assets")
    ax1.set_title(f"wp-4537-01 asset status (total {len(assets)})", fontsize=10)
    for i, s in enumerate(st):
        ax1.text(i, by_status[s] + 0.1, str(by_status[s]), ha="center", fontsize=9)
    ax1.set_ylim(0, max(by_status.values()) + 1.5)

    # Right: kind distribution
    y = range(len(kinds))
    ax2.barh(list(y), [by_kind[k] for k in kinds], color="#1565c0")
    ax2.set_yticks(list(y))
    ax2.set_yticklabels([k.replace("_", " ") for k in kinds], fontsize=7)
    ax2.invert_yaxis()
    ax2.set_xlabel("assets")
    ax2.set_title("by kind", fontsize=10)
    for i, k in enumerate(kinds):
        ax2.text(by_kind[k] + 0.1, i, str(by_kind[k]), va="center", fontsize=8)

    # Annotation box
    checks = m.get("checks", {})
    ok = sum(1 for v in checks.values() if v is True)
    src = m.get("source", {})
    ax2.text(
        1.02,
        0.98,
        f"source sha256 {src.get('sha256', '')[:23]}…\n"
        f"chars {src.get('chars', 0)} (contract {src.get('contract_declared_chars', 0)})\n"
        f"self-checks {ok}/{len(checks)} true\n"
        f"claims {len(m.get('claims', []))} (extraction not performed)",
        transform=ax2.transAxes,
        va="top",
        ha="left",
        fontsize=7,
        family="monospace",
        bbox=dict(boxstyle="round", fc="#f5f5f5", ec="#9e9e9e"),
    )

    fig.suptitle("wp-4537-04 review: upstream asset registration overview", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))

    out_path = out / "fig1_review_4537_04.png"
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"Figure saved: {out_path}")


if __name__ == "__main__":
    main()
