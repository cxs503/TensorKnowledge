"""Figure for wp-13946-01: what the asset manifest actually covers.

Every number is read from artifacts/wp-13946-01/asset_manifest.json at run time (zero hand
transcription). Labels are ASCII because no CJK font is installed in this image (verified: fc-list
has no Noto CJK / WQY), so Chinese section titles are shown only by their line numbers.

Usage: python3 scripts/kf_figures_13946.py
Output: docs/wp-13946-01/fig1_asset_coverage.png (durable, committed)
        artifacts/wp-13946-01/fig1_asset_coverage.png (mirror for gate fetch)
"""
from __future__ import annotations

import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

MAN = pathlib.Path("artifacts/wp-13946-01/asset_manifest.json")
OUT_DOC = pathlib.Path("docs/wp-13946-01/fig1_asset_coverage.png")
OUT_ART = pathlib.Path("artifacts/wp-13946-01/fig1_asset_coverage.png")

COLORS = {"resolved_in_source": "#2a9d8f",
          "referenced_unresolved": "#e9a13b",
          "declared_absent": "#c44e52"}


def main() -> int:
    m = json.loads(MAN.read_text())
    assets = m["assets"]
    classes = sorted({a["asset_class"] for a in assets},
                     key=lambda c: (-sum(1 for a in assets if a["asset_class"] == c), c))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2),
                                   gridspec_kw={"width_ratios": [1.0, 1.35]})

    # panel A: assets per class, stacked by resolution (counts computed, not eyeballed)
    order = ("resolved_in_source", "referenced_unresolved", "declared_absent")
    ys = list(range(len(classes)))
    stack = {c: {r: sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == r)
                 for r in order} for c in classes}
    assert sum(sum(v.values()) for v in stack.values()) == m["counts"]["assets"]
    for res in order:
        vals = [stack[c][res] for c in classes]
        lefts = [sum(stack[c][r] for r in order[:order.index(res)]) for c in classes]
        ax1.barh(list(ys), vals, left=lefts, color=COLORS[res], height=0.72, label=res)
        for y, l, v in zip(ys, lefts, vals):
            if v:
                ax1.text(l + v / 2, y, str(v), ha="center", va="center", fontsize=7,
                         color="white")
    for res in order:  # cross-check against the manifest's own totals
        assert sum(stack[c][res] for c in classes) == m["counts"]["by_resolution"].get(res, 0)
    ax1.set_yticks(list(ys))
    ax1.set_yticklabels(classes, fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel("number of assets", fontsize=9)
    ax1.set_title("A  %d registered assets by class / resolution" % m["counts"]["assets"],
                  fontsize=10)
    ax1.legend(fontsize=7, loc="lower right", title="resolution", title_fontsize=7)
    ax1.grid(axis="x", alpha=0.25)

    # panel B: where the locators sit in the source document (char offsets)
    for i, a in enumerate(assets):
        loc = a["locator"]
        ax2.plot([loc["start_char"], loc["end_char"]], [i, i],
                 color=COLORS[a["resolution"]], lw=4, solid_capstyle="butt")
        ax2.text(loc["start_char"] - 40, i, a["asset_id"], ha="right", va="center", fontsize=6.5)
    ax2.set_ylim(-1, len(assets))
    ax2.invert_yaxis()
    ax2.set_xlim(-260, m["source"]["chars"] * 1.01)
    ax2.set_xlabel("character offset in report markdown (chars=%d, sha256 %s...)"
                   % (m["source"]["chars"], m["source"]["hash"][:12]), fontsize=8)
    ax2.set_yticks([])
    ax2.set_title("B  locator spans; unique verbatim slices of the source", fontsize=10)
    ax2.grid(axis="x", alpha=0.25)
    handles = [Patch(color=COLORS[k], label="%s (%d)" % (k, m["counts"]["by_resolution"].get(k, 0)))
               for k in COLORS]
    ax2.legend(handles=handles, fontsize=7, loc="lower right")

    fig.suptitle("wp-13946-01 asset manifest coverage (report 13946, %s)"
                 % m["package_id"], fontsize=10.5)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUT_DOC.parent.mkdir(parents=True, exist_ok=True)
    OUT_ART.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DOC, dpi=150)
    fig.savefig(OUT_ART, dpi=150)
    print("wrote", OUT_DOC, OUT_ART)
    print("by_class:", m["counts"]["by_class"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())