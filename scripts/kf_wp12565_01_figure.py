#!/usr/bin/env python3
"""wp-12565-01 / figure: locator map of the registered source (report 12565).

Left panel  : char-axis span map - every registered asset span (bars) and every literal
              anchor (ticks) drawn at its measured char offset on the 648-char markdown,
              so a reviewer can see *where in the document* each asset sits.
Right panel : outcome counts (resolved_in_source vs referenced_unresolved) per asset class,
              read straight out of asset_manifest.json - no hand-entered numbers.

Labels are ASCII-only on purpose: the only font available to matplotlib here is
"Noto Sans" (no CJK coverage), so CJK labels would render as tofu boxes. The quotes
themselves are CJK and live verbatim in the manifest, not in the picture.

Usage: python3 scripts/kf_wp12565_01_figure.py
Output: docs/kf/wp-12565-01/figures/locator_map.png
"""
from __future__ import annotations

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-12565-01"
OUT = PKG / "figures" / "locator_map.png"

COL_RES = {"resolved_in_source": "#2c7bb6", "referenced_unresolved": "#d7191c",
           "declared_absent": "#7b3294"}


def main() -> None:
    m = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    v = json.loads((PKG / "verify_independent.json").read_text(encoding="utf-8"))
    n_chars = m["source"]["chars"]
    assets = m["assets"]
    anchors = m["literal_anchors"]

    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(12.5, 8.2), gridspec_kw={"height_ratios": [1.55, 1.0]}
    )

    # ---------------- panel A: span map ----------------
    ax.set_title(
        "report 12565 markdown (chars=%d, bytes=%d) - registered asset spans and anchor offsets\n"
        "source hash verified: %s  |  independent checks V1-V7: %s"
        % (n_chars, m["source"]["bytes_utf8"], m["source"]["hash"][:16] + "...",
           "all pass" if v["all_pass"] else "FAILED"),
        fontsize=10, loc="left",
    )
    ylabels = []
    for i, a in enumerate(assets):
        y = len(assets) - i
        loc = a["locator"]
        ax.barh(y, max(loc["end_char"] - loc["start_char"], 2), left=loc["start_char"],
                height=0.55, color=COL_RES[a["resolution"]], alpha=0.9)
        ylabels.append("%s  %s (%s)" % (a["asset_id"], a["asset_class"],
                                        a["resolution"].replace("referenced_", "ref_")))
    ax.set_yticks(range(len(assets), 0, -1))
    ax.set_yticklabels(ylabels, fontsize=8)
    ax.set_xlim(-5, n_chars + 5)
    ax.set_xlabel("character offset in markdown (python str indices)", fontsize=9)

    lo = -1.2
    for a in anchors:
        ax.plot([a["start_char"], a["start_char"]], [lo - 0.35, lo + 0.35],
                color="#fdae61", lw=1.4)
        ax.text(a["start_char"], lo - 0.5, a["locator_id"], fontsize=6, rotation=90,
                ha="center", va="top", color="#b35806")
    ax.set_ylim(lo - 1.6, len(assets) + 0.8)
    ax.axhline(lo, color="0.6", lw=0.8, ls=":")
    ax.text(-3, lo - 0.05, "anchors", fontsize=8, ha="right", va="center", color="#b35806")
    ax.grid(axis="x", ls=":", lw=0.5, alpha=0.6)

    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COL_RES.values()]
    ax.legend(handles, list(COL_RES), fontsize=7.5, loc="upper right", frameon=False)

    # ---------------- panel B: outcome counts ----------------
    classes = sorted({a["asset_class"] for a in assets})
    counts = {c: {k: 0 for k in COL_RES} for c in classes}
    for a in assets:
        counts[a["asset_class"]][a["resolution"]] += 1
    x = range(len(classes))
    bottom = [0] * len(classes)
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        vals = [counts[c][res] for c in classes]
        if not any(vals):
            continue
        ax2.bar(x, vals, bottom=bottom, color=COL_RES[res], label=res)
        bottom = [b + v for b, v in zip(bottom, vals)]
    for xi, cls in enumerate(classes):
        ax2.text(xi, bottom[xi] + 0.05, "%d" % bottom[xi], ha="center", va="bottom", fontsize=8)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels([c.replace("_", "\n") for c in classes], fontsize=7.5)
    ax2.set_ylabel("assets", fontsize=9)
    ax2.set_title(
        "asset registration outcome by class  (resolved_in_source=%d, referenced_unresolved=%d, "
        "claims=%d, literal anchors=%d)"
        % (m["counts"]["resolved_in_source"], m["counts"]["referenced_unresolved"],
           len(m["claims"]), len(anchors)),
        fontsize=10, loc="left",
    )
    ax2.legend(fontsize=7.5, frameon=False)
    ax2.grid(axis="y", ls=":", lw=0.5, alpha=0.6)
    ax2.set_axisbelow(True)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print("wrote", OUT, "%d bytes" % OUT.stat().st_size)


if __name__ == "__main__":
    main()