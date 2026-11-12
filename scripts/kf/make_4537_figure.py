#!/usr/bin/env python3
"""Figure for the wp-4537-01 report: asset register composition, read from the manifest.

Zero hand-copied numbers: every value is counted from
docs/kf/wp-4537-01/asset_manifest.json at render time.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "kf" / "wp-4537-01" / "asset_manifest.json"
OUT = ROOT / "docs" / "kf" / "wp-4537-01" / "asset_status.png"

STATUS_ORDER = ["resolved", "declared_metadata_only", "declared_only", "declared_shorthand"]
COLORS = {
    "resolved": "#2e7d32",
    "declared_metadata_only": "#f9a825",
    "declared_only": "#ef6c00",
    "declared_shorthand": "#6d4c41",
}


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = m["assets"]
    by_status = Counter(a["status"] for a in assets)
    by_kind = Counter(a["kind"] for a in assets)
    kinds = sorted(by_kind, key=lambda k: (-by_kind[k], k))

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12.4, 4.8), gridspec_kw={"width_ratios": [1, 1.35]}
    )

    st = [s for s in STATUS_ORDER if s in by_status]
    ax1.bar(range(len(st)), [by_status[s] for s in st], color=[COLORS[s] for s in st])
    ax1.set_xticks(range(len(st)))
    ax1.set_xticklabels([s.replace("_", "\n") for s in st], fontsize=8)
    ax1.set_ylabel("assets")
    ax1.set_title(f"wp-4537-01 asset register by status (total {len(assets)})", fontsize=10)
    for i, s in enumerate(st):
        ax1.text(i, by_status[s] + 0.2, str(by_status[s]), ha="center", fontsize=9)
    ax1.set_ylim(0, max(by_status.values()) + 2)

    y = range(len(kinds))
    ax2.barh(list(y), [by_kind[k] for k in kinds], color="#1565c0")
    ax2.set_yticks(list(y))
    ax2.set_yticklabels(kinds, fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlabel("assets")
    ax2.set_title("by kind (bytes available only for what is really present)", fontsize=10)
    for i, k in enumerate(kinds):
        ax2.text(by_kind[k] + 0.15, i, str(by_kind[k]), va="center", fontsize=9)

    checks = m["checks"]
    ok = sum(1 for v in checks.values() if v is True)
    ax2.text(
        1.02,
        0.98,
        f"source sha256 {m['source']['sha256'][:23]}…\n"
        f"chars {m['source']['chars']} (contract {m['source']['contract_declared_chars']})\n"
        f"locators resolved {ok}/{len(checks)} self-checks true\n"
        f"claims {len(m['claims'])} (extraction not performed)",
        transform=ax2.transAxes,
        va="top",
        ha="left",
        fontsize=8,
        family="monospace",
        bbox=dict(boxstyle="round", fc="#f5f5f5", ec="#9e9e9e"),
    )

    fig.suptitle("Report 4537 asset registration — declared vs. byte-available", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT, dpi=140)
    print(OUT)


if __name__ == "__main__":
    main()
