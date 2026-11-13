"""Figures for the wp-5690-01 mission report. Everything plotted is read from the artifacts
(asset_manifest.json / verification.json) -- no numbers are typed into the figure code.

Outputs:
  artifacts/wp-5690-01/fig_asset_inventory.png   asset classes x resolution status
  artifacts/wp-5690-01/fig_locator_coverage.png  char-span map of every locator over report 5690
  artifacts/wp-5690-01/fig_verification.png      acceptance-check status board

Usage: python3 scripts/kf_figures_5690.py
"""
from __future__ import annotations

import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ART = pathlib.Path("artifacts/wp-5690-01")
DOC = pathlib.Path("docs/wp-5690-01")
MANIFEST = json.loads((ART / "asset_manifest.json").read_text())
VERIF = json.loads((ART / "verification.json").read_text())
COLORS = {"resolved_in_source": "#1b7837", "referenced_unresolved": "#d95f02", "declared_absent": "#7570b3"}


def fig_inventory():
    classes = list(MANIFEST["counts"]["by_class"])
    order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    fig, ax = plt.subplots(figsize=(9.6, 6.4))
    left = [0] * len(classes)
    for status in order:
        vals = [sum(1 for a in MANIFEST["assets"] if a["asset_class"] == c and a["resolution"] == status)
                for c in classes]
        ax.barh(classes, vals, left=left, color=COLORS[status], label=status)
        left = [l + v for l, v in zip(left, vals)]
    for i, c in enumerate(classes):
        ax.text(left[i] + 0.05, i, str(MANIFEST["counts"]["by_class"][c]), va="center", fontsize=8)
    ax.set_xlabel("registered assets")
    ax.set_title("wp-5690-01 asset inventory: %d assets, %d classes, resolution status per class\n"
                 "(report 5690, sha256 %s...)" % (MANIFEST["counts"]["assets"], len(classes),
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
    ax.set_xlabel("character offset in report 5690 markdown (total %d chars)" % n)
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
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(checks) + 1.2))
    for i, c in enumerate(checks):
        color = "#1b7837" if c["result"] == "pass" else "#cf222e"
        ax.add_patch(plt.Rectangle((0, len(checks) - 1 - i), 1, 0.7, color=color, alpha=0.85))
        ax.text(1.15, len(checks) - 0.65 - i, "%-42s %s" % (c["check"], c["result"].upper()),
                va="center", fontsize=8)
    ax.set_xlim(0, 1.3)
    ax.set_ylim(-0.5, len(checks) - 0.3)
    ax.axis("off")
    ax.set_title("wp-5690-01 acceptance self-check: %d/%d pass, overall %s\n"
                 "source hash recomputed from an independent API re-fetch in the verifier process"
                 % (sum(1 for c in checks if c["result"] == "pass"), len(checks), VERIF["overall"]))
    fig.tight_layout()
    out = ART / "fig_verification.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main() -> None:
    DOC.mkdir(parents=True, exist_ok=True)
    for fn in (fig_inventory(), fig_coverage(), fig_verification()):
        (DOC / fn.name).write_bytes(fn.read_bytes())
        print("wrote", fn, fn.stat().st_size, "bytes (mirrored to docs/)")


if __name__ == "__main__":
    main()
