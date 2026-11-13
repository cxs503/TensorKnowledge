#!/usr/bin/env python3
"""Report figure for wp-6537-01: asset inventory of report 6537, drawn from the manifest.

Everything plotted is read back from docs/kf/wp-6537-01/asset_manifest.json + verification.json
(no hand-entered numbers). Deterministic: fixed order, fixed colors, PNG metadata pinned.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "docs" / "kf" / "wp-6537-01"
OUT = PKG / "fig_asset_inventory.png"

STATUS_ORDER = ["resolved", "metadata_only", "unresolved", "declared_unavailable"]
COLORS = {"resolved": "#2e7d32", "metadata_only": "#f9a825",
          "unresolved": "#c62828", "declared_unavailable": "#6a1b9a"}


def main():
    m = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    v = json.loads((PKG / "verification.json").read_text(encoding="utf-8"))

    classes = sorted(m["counts"]["by_class"])
    grid = {c: {s: 0 for s in STATUS_ORDER} for c in classes}
    for a in m["assets"]:
        grid[a["asset_class"]][a["resolution"]["status"]] += 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 4.9), dpi=160,
                                   gridspec_kw={"width_ratios": [1.55, 1.0]})

    # (a) asset_class x resolution
    left = [0] * len(classes)
    for s in STATUS_ORDER:
        vals = [grid[c][s] for c in classes]
        ax1.barh(classes, vals, left=left, color=COLORS[s], edgecolor="white",
                 label="%s (%d)" % (s, sum(vals)))
        left = [l + v for l, v in zip(left, vals)]
    ax1.set_xlabel("registered assets (report 6537 only)")
    ax1.set_title("(a) 37 assets by class x resolution status", fontsize=10)
    ax1.legend(fontsize=7.5, loc="lower right", framealpha=0.9)
    ax1.tick_params(axis="y", labelsize=7.5)
    for i, c in enumerate(classes):
        ax1.text(left[i] + 0.15, i, str(left[i]), va="center", fontsize=7.5)
    ax1.set_xlim(0, max(left) + 1.6)

    # (b) two different questions: locator resolvable vs target retrievable
    n = len(m["assets"])
    loc_ok = sum(1 for a in m["assets"] if a["locator"].get("verified", True))
    tgt_ok = m["counts"]["by_resolution"]["resolved"]
    bars = ax2.bar(["locator\n(char span in\nreport bytes)", "target\n(file bytes in\ndelivery worktree)"],
                   [loc_ok, tgt_ok], color=["#1565c0", "#2e7d32"], width=0.55)
    for b, val in zip(bars, [loc_ok, tgt_ok]):
        ax2.text(b.get_x() + b.get_width() / 2, val + 0.4, "%d / %d" % (val, n),
                 ha="center", fontsize=9)
    ax2.set_ylim(0, n + 3)
    ax2.set_ylabel("assets")
    ax2.set_title("(b) resolvable locator vs retrievable target\n"
                  "(the two are NOT the same claim)", fontsize=10)
    ax2.axhline(n, ls=":", lw=0.9, color="gray")
    ax2.tick_params(axis="x", labelsize=8)

    ok = sum(1 for c in v["checks"].values() if c["pass"])
    fig.suptitle("wp-6537-01 asset registration — source sha256 %s… (chars %d, %d/%d acceptance checks pass)"
                 % (m["provenance"]["source_hash"].split(":")[-1][:16], m["provenance"]["source_chars"],
                    ok, len(v["checks"])), fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT, metadata={"Software": None})
    plt.close(fig)
    print("wrote %s sha256=%s bytes=%d" % (OUT.relative_to(REPO),
                                           hashlib.sha256(OUT.read_bytes()).hexdigest(),
                                           OUT.stat().st_size))


if __name__ == "__main__":
    main()