"""Figures for the wp-448-01 mission report. Everything plotted is read from the artifacts
(asset_manifest.json / verification.json) -- no numbers are typed into the figure code.

Outputs:
  artifacts/wp-448-01/fig_asset_inventory.png   asset classes x resolution status
  artifacts/wp-448-01/fig_locator_coverage.png  char-span map of every locator over report 448
  artifacts/wp-448-01/fig_verification.png      acceptance-check status board

Usage: python3 scripts/kf_figures_448.py
"""
from __future__ import annotations

import json
import pathlib
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ART = pathlib.Path("artifacts/wp-448-01")
DOC = pathlib.Path("docs/wp-448-01")
MANIFEST = json.loads((ART / "asset_manifest.json").read_text())
VERIF = json.loads((ART / "verification.json").read_text())
COLORS = {"resolved_in_source": "#1b7837", "referenced_unresolved": "#d95f02", "declared_absent": "#7570b3"}


def fig_inventory():
    classes = list(MANIFEST["counts"]["by_class"])
    order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    fig, ax = plt.subplots(figsize=(9.2, 6.0))
    left = [0] * len(classes)
    for status in order:
        vals = [sum(1 for a in MANIFEST["assets"] if a["asset_class"] == c and a["resolution"] == status)
                for c in classes]
        ax.barh(classes, vals, left=left, color=COLORS[status], label=status)
        left = [l + v for l, v in zip(left, vals)]
    for i, c in enumerate(classes):
        ax.text(left[i] + 0.05, i, str(MANIFEST["counts"]["by_class"][c]), va="center", fontsize=8)
    ax.set_xlabel("registered assets")
    ax.set_title("wp-448-01 asset inventory: %d assets, %d classes, resolution status per class\n"
                 "(report 448, sha256 %s...)" % (MANIFEST["counts"]["assets"], len(classes),
                                                  MANIFEST["source"]["hash"][:12]))
    ax.legend(title="resolution", loc="lower right", fontsize=8)
    ax.invert_yaxis()
    fig.tight_layout()
    out = ART / "fig_asset_inventory.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_coverage():
    n = MANIFEST["source"]["chars"]
    fig, ax = plt.subplots(figsize=(10, 7))
    items = [a for a in MANIFEST["assets"] if a["asset_class"] != "document"]
    for a in sorted(items, key=lambda x: x["locator"]["start_char"]):
        loc = a["locator"]
        ax.plot([loc["start_char"], loc["end_char"]], [a["asset_id"]] * 2, lw=4,
                color=COLORS[a["resolution"]], solid_capstyle="butt")
        ax.text(n + 30, a["asset_id"], "%d-%d" % (loc["start_char"], loc["end_char"]),
                fontsize=6, va="center")
    lanes = {}
    for a in MANIFEST["assets"]:
        lanes.setdefault(a["in_report_section"], []).append(a["locator"]["start_char"])
    # union over the span-level assets only: the document-level asset A01 trivially covers 100%
    covered = set()
    for a in items:
        covered |= set(range(a["locator"]["start_char"], a["locator"]["end_char"]))
    ax.set_xlim(-20, n + 190)
    ax.set_xlabel("character offset in report 448 markdown (total %d chars)" % n)
    ax.set_title("locator map: every registered asset re-resolves to a unique char span\n"
                 "%d span-level assets (document-level A01 not drawn); union coverage = %d/%d chars "
                 "(%.1f%%); %d sections touched"
                 % (len(items), len(covered), n, 100.0 * len(covered) / n, len(lanes)))
    handles = [plt.Line2D([0], [0], color=c, lw=4, label=s) for s, c in COLORS.items()]
    ax.legend(handles=handles, fontsize=7, loc="lower left")
    ax.tick_params(axis="y", labelsize=7)
    ax.invert_yaxis()
    fig.tight_layout()
    out = ART / "fig_locator_coverage.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_verification():
    checks = VERIF["checks"]
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(checks) + 1.6))
    ax.axis("off")
    for i, c in enumerate(checks):
        y = len(checks) - i
        color = {"pass": "#1b7837", "fail": "#b2182b"}.get(c["result"], "#7570b3")
        ax.add_patch(plt.Rectangle((0, y - 0.34), 0.06, 0.7, color=color))
        ax.text(0.09, y, c["check"], fontsize=8.5, family="monospace", va="center")
        ax.text(1.30, y, c["result"].upper(), fontsize=8.5, family="monospace", va="center", color=color)
    ax.set_xlim(0, 1.6)
    ax.set_ylim(0.4, len(checks) + 0.9)
    ax.set_title("wp-448-01 acceptance self-check (scripts/kf_verify_448.py) -- overall %s\n"
                 "source hash recomputed independently: %s"
                 % (VERIF["overall"], VERIF["source_hash_recomputed"][:32] + "..."), fontsize=9)
    fig.tight_layout()
    out = ART / "fig_verification.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


if __name__ == "__main__":
    pathlib.Path("docs/wp-448-01").mkdir(parents=True, exist_ok=True)
    for f in (fig_inventory(), fig_coverage(), fig_verification()):
        shutil.copyfile(f, pathlib.Path("docs/wp-448-01") / f.name)
        print("wrote", f, f.stat().st_size, "bytes -> docs/wp-448-01/" + f.name)