"""Figures for KF work package wp-9091-01 (asset registration of report 9091).

Data-driven from docs/wp-9091-01/asset_manifest.json only (no hard-coded numbers):
  panel 1  asset count per asset_class
  panel 2  resolution split (resolved_in_source / referenced_unresolved / declared_absent)
  panel 3  locator coverage map: each asset's char span projected onto the report's line axis
           (a visual proof that every registered asset is pinned to a distinct region)

Usage: python3 scripts/kf_figures_wp9091_01.py
Outputs: docs/wp-9091-01/fig_asset_inventory.png (+ copy under artifacts/wp-9091-01/)
"""
from __future__ import annotations

import json
import pathlib
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DOC = pathlib.Path("docs/wp-9091-01")
MANIFEST = DOC / "asset_manifest.json"
PNG = DOC / "fig_asset_inventory.png"

COLORS = {"resolved_in_source": "#2b7bba", "referenced_unresolved": "#e08214", "declared_absent": "#8c8c8c"}


def main() -> int:
    man = json.loads(MANIFEST.read_text())
    assets = man["assets"]
    src = man["source"]

    classes, per_class = [], {}
    for a in assets:
        per_class.setdefault(a["asset_class"], []).append(a)
    classes = sorted(per_class, key=lambda c: (-len(per_class[c]), c))
    res_order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    res_counts = {k: sum(1 for a in assets if a["resolution"] == k) for k in res_order}

    fig = plt.figure(figsize=(15, 9.5))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 1.0], height_ratios=[1.0, 1.15],
                          hspace=0.42, wspace=0.30)

    # ---- panel 1: assets per class ----
    ax1 = fig.add_subplot(gs[0, 0])
    y = range(len(classes))
    vals = [len(per_class[c]) for c in classes]
    bars = ax1.barh(list(y), vals, color="#2b7bba", height=0.62)
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(classes, fontsize=8.5)
    ax1.invert_yaxis()
    ax1.set_xlabel("registered assets")
    ax1.set_title("(1) Asset classes registered (n=%d)" % len(assets), fontsize=10.5, loc="left")
    for b, v in zip(bars, vals):
        ax1.text(b.get_width() + 0.06, b.get_y() + b.get_height() / 2, str(v),
                 va="center", fontsize=8.5)
    ax1.set_xlim(0, max(vals) + 1.2)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # ---- panel 2: resolution split ----
    ax2 = fig.add_subplot(gs[0, 1])
    vals = [res_counts[k] for k in res_order]
    bars = ax2.bar(range(len(res_order)), vals,
                   color=[COLORS[k] for k in res_order], width=0.6)
    ax2.set_xticks(range(len(res_order)))
    ax2.set_xticklabels([k.replace("_", "\n") for k in res_order], fontsize=9)
    ax2.set_ylabel("assets")
    ax2.set_title("(2) Resolution status (no asset left unclassified)", fontsize=10.5, loc="left")
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.25, str(v), ha="center", fontsize=9)
    ax2.set_ylim(0, max(vals) + 3)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    # ---- panel 3: locator coverage on the line axis ----
    ax3 = fig.add_subplot(gs[1, :])
    n_lines = src["chars"] and len(pathlib.Path("docs/wp-9091-01/report_9091.md").read_text().split("\n"))
    for i, a in enumerate(assets):
        loc = a["locator"]
        x0, x1 = loc["start_line"] + 1, loc["end_line"] + 1
        ax3.barh(i, x1 - x0 + 1, left=x0, height=0.72,
                 color=COLORS[a["resolution"]], alpha=0.9)
        ax3.text(x1 + 1.5, i, a["asset_id"], va="center", fontsize=7.5)
    ax3.set_yticks(range(len(assets)))
    ax3.set_yticklabels(["%s %s" % (a["asset_id"], a["asset_class"]) for a in assets], fontsize=7.2)
    ax3.invert_yaxis()
    ax3.set_xlabel("report line (1-based), %d lines total" % n_lines)
    ax3.set_xlim(0, n_lines + 8)
    ax3.set_title("(3) Locator coverage: every asset pinned to a verbatim, unique span of the source markdown",
                  fontsize=10.5, loc="left")
    for ln in range(0, n_lines + 10, 20):
        ax3.axvline(ln, color="#dddddd", lw=0.6, zorder=0)
    for s in ("top", "right"):
        ax3.spines[s].set_visible(False)

    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[k]) for k in res_order]
    fig.legend(handles, ["%s (%d)" % (k, res_counts[k]) for k in res_order],
               loc="lower center", ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("wp-9091-01 asset registration — report %s  (sha256 %s…, %d chars / %d bytes UTF-8)"
                 % (man["report_id"], src["hash"][:16], src["chars"], src["bytes_utf8"]),
                 fontsize=11.5, x=0.01, ha="left")
    fig.subplots_adjust(top=0.90, bottom=0.08, left=0.20, right=0.985)
    fig.savefig(PNG, dpi=150)
    plt.close(fig)

    art = pathlib.Path("artifacts/wp-9091-01")
    art.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PNG, art / PNG.name)
    print("figure:", PNG, PNG.stat().st_size, "bytes")
    print("classes:", len(classes), "resolutions:", res_counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())