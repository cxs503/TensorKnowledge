#!/usr/bin/env python3
"""Figure for KF wp-4129-01 (asset registration): report structure + locator map.

Pure documentation/registration task -> no physical field variables exist, so the
图 is a structure/locator map instead of a contour plot (reason recorded in the
report). Everything plotted is read from the committed artefacts, nothing is typed
in by hand:

  * panel A — report 4129 markdown line-length profile with every registered locator
    drawn at its declared line, coloured by asset kind;
  * panel B — asset kind x resolution-status histogram from the manifest counts;
  * panel C — the seven contract self-checks of the manifest (all must be true).

Output: docs/kf/figures/wp-4129-01.png
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "knowledge" / "kf" / "wp-4129-01"
OUT = ROOT / "docs" / "kf" / "figures" / "wp-4129-01.png"

KIND_COLORS = {
    "report_markdown": "#1f77b4",
    "file_reference": "#ff7f0e",
    "data_artifact_reference": "#9467bd",
    "source_code_reference": "#2ca02c",
    "test_reference": "#d62728",
    "directory_reference": "#8c564b",
    "worktree_path_reference": "#7f7f7f",
    "figure_reference": "#17becf",
    "embedded_figure": "#bcbd22",
}


def main() -> int:
    md = (PKG / "source_report_4129.md").read_text(encoding="utf-8")
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    lines = md.rstrip("\n").split("\n")

    # locator line -> kind (asset capitalises its own locator line number)
    line_kind: dict[int, str] = {}
    for asset in manifest["assets"]:
        n = asset["locator"].get("line")
        if n:
            line_kind.setdefault(n, []).append(asset["kind"])
    for sym in manifest["symbol_references"] + manifest["vcs_references"]:
        n = sym["locator"].get("line")
        if n:
            line_kind.setdefault(n, []).append("symbol/vcs")

    fig = plt.figure(figsize=(13.2, 8.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0], hspace=0.42, wspace=0.24)

    # ---------------- panel A: line profile + locator markers
    ax = fig.add_subplot(gs[0, :])
    xs = list(range(1, len(lines) + 1))
    ys = [len(li) for li in lines]
    ax.bar(xs, ys, width=0.9, color="#d9dde3", label="chars per line")
    section_lines = [i + 1 for i, li in enumerate(lines) if li.startswith("## ")]
    for sl in section_lines:
        ax.axvline(sl, color="#999999", lw=0.7, ls=":")
    ytop = max(ys) * 1.18
    for n, kinds in sorted(line_kind.items()):
        kinds_sorted = sorted(set(kinds))
        for k, kind in enumerate(kinds_sorted):
            color = KIND_COLORS.get(kind, "#111111")
            ax.plot([n], [ytop - k * (ytop * 0.045)], marker="v", ms=6, color=color)
    ax.set_ylim(0, ytop * 1.02)
    ax.set_xlim(0.2, len(lines) + 0.8)
    ax.set_xlabel("markdown line (1-based; dotted = `## ` section heading)")
    ax.set_ylabel("characters in line")
    ax.set_title(
        "A · report 4129 structure (%d lines / %d chars / %d bytes) with %d registered locators"
        % (len(lines), len(md), len(md.encode("utf-8")), len(manifest["locators"])),
        loc="left", fontsize=10,
    )
    present = sorted({k for ks in line_kind.values() for k in ks})
    handles = [Line2D([], [], marker="v", ls="", color=KIND_COLORS.get(k, "#111111"), label=k)
               for k in present]
    ax.legend(handles=handles, fontsize=7, ncol=min(5, len(handles)), loc="upper center",
              frameon=False)

    # ---------------- panel B: kind/status histogram
    ax2 = fig.add_subplot(gs[1, 0])
    hist = manifest["counts"]["kind_status_histogram"]
    labels = list(hist.keys())
    vals = [hist[k] for k in labels]
    colors = [KIND_COLORS.get(k.split("/")[0], "#555555") for k in labels]
    ax2.barh(range(len(labels)), vals, color=colors)
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels(labels, fontsize=7)
    ax2.invert_yaxis()
    for i, v in enumerate(vals):
        ax2.text(v + 0.05, i, str(v), va="center", fontsize=7)
    ax2.set_xlabel("assets")
    ax2.set_title("B · asset kind / resolution status (claims = 0 by contract)",
                  loc="left", fontsize=10)

    # ---------------- panel C: contract self-checks
    ax3 = fig.add_subplot(gs[1, 1])
    checks = manifest["checks"]
    names = list(checks.keys())
    ok = [1 if checks[k] else 0 for k in names]
    # a check with a False value is a real problem; a *missing* check is not "pass"
    ax3.barh(range(len(names)), [1] * len(names),
             color=["#2ca02c" if v else "#d62728" for v in ok])
    ax3.set_yticks(range(len(names)))
    ax3.set_yticklabels(names, fontsize=7)
    ax3.invert_yaxis()
    ax3.set_xlim(0, 1.0)
    ax3.set_xticks([])
    for i, v in enumerate(ok):
        ax3.text(0.5, i, "PASS" if v else "FAIL", ha="center", va="center",
                 color="white", fontsize=8, weight="bold")
    ax3.set_title("C · manifest self-checks (%d/%d true)" % (sum(ok), len(ok)),
                  loc="left", fontsize=10)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())