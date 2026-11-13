"""Figure + coverage metrics for work package wp-9706-01 (report 9706 asset registration).

Everything is computed from artifacts/wp-9706-01/asset_manifest.json -- no hand-entered numbers.
Emits:
  docs/wp-9706-01/fig_asset_coverage.png   (left: locator map over the source char axis;
                                            right: asset classes by resolution status)
  runs/wp-9706-01/coverage.json            (coverage numbers quoted verbatim in the KF report)

Notes / limitations:
  * The whole-document entry (A01, method="document") is excluded from the coverage metric on
    purpose: counting it would make coverage 100% by construction (tautology).
  * This environment has no CJK font (DejaVu Sans only), so every figure label is ASCII.

Usage: python3 scripts/kf_figures_9706.py
"""
from __future__ import annotations

import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

PKG = "wp-9706-01"
ROOT = pathlib.Path(__file__).resolve().parents[1]
MAN = ROOT / "artifacts" / PKG / "asset_manifest.json"
OUT_PNG = ROOT / "docs" / PKG / "fig_asset_coverage.png"
OUT_JSON = ROOT / "runs" / PKG / "coverage.json"

COLORS = {"resolved_in_source": "#2a6f97",
          "referenced_unresolved": "#e07a5f",
          "declared_absent": "#8d99ae"}


def merge_spans(spans):
    merged = []
    for s, e in sorted(spans):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


def main() -> int:
    man = json.loads(MAN.read_text(encoding="utf-8"))
    md = (ROOT / "runs" / PKG / "report_9706.md").read_text(encoding="utf-8")
    n = len(md)
    assets = man["assets"]

    spans = [(a["locator"]["start_char"], a["locator"]["end_char"]) for a in assets
             if a["resolution"] == "resolved_in_source" and a["locator"]["method"] == "char_span"]
    merged = merge_spans(spans)
    covered = sum(e - s for s, e in merged)
    gaps, prev = [], 0
    for s, e in merged:
        if s > prev:
            gaps.append([prev, s])
        prev = max(prev, e)
    if prev < n:
        gaps.append([prev, n])

    # '## ' section boundaries (guide lines; ASCII labels -- no CJK font available here)
    sec_offsets, off = [], 0
    for ln in md.split("\n"):
        if ln.startswith("## ") and off > 0:
            sec_offsets.append(off)
        off += len(ln) + 1

    metrics = dict(
        source_chars=n,
        assets=len(assets),
        resolved_in_source=sum(1 for a in assets if a["resolution"] == "resolved_in_source"),
        referenced_unresolved=sum(1 for a in assets if a["resolution"] == "referenced_unresolved"),
        declared_absent=sum(1 for a in assets if a["resolution"] == "declared_absent"),
        coverage_excludes_whole_document_entry=True,
        chars_covered_by_section_level_locators=covered,
        coverage_fraction=round(covered / n, 4),
        uncovered_regions=len(gaps),
        uncovered_chars=sum(e - s for s, e in gaps),
        largest_uncovered_gap=max(((e - s), s, e) for s, e in gaps) if gaps else None,
        median_quote_chars=sorted(len(a["locator"]["quote"]) for a in assets)[len(assets) // 2],
        total_quote_chars=sum(len(a["locator"]["quote"]) for a in assets),
        sections_with_boundaries=len(sec_offsets),
    )
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 0.28 * len(assets) + 2.2),
                                   gridspec_kw={"width_ratios": [3.1, 1.0]})
    order = [a["asset_id"] for a in assets]
    ypos = {aid: i for i, aid in enumerate(order[::-1])}
    for a in assets:
        y = ypos[a["asset_id"]]
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        ax1.barh(y, max(e - s, n * 0.0015), left=s, height=0.72,
                 color=COLORS[a["resolution"]], edgecolor="none")
    ax1.set_yticks(list(ypos.values()))
    ax1.set_yticklabels(list(ypos.keys()), fontsize=6.5)
    ax1.set_xlim(0, n)
    ax1.set_xlabel("source markdown character offset (0 - %d)" % n, fontsize=9)
    ax1.set_title("A. Locator map: where each registered asset sits in report 9706\n"
                  "(%d assets; S1..S%d = '## ' sections; %.1f%% of source chars covered by "
                  "section-level locators)" % (len(assets), len(sec_offsets),
                                               100.0 * covered / n), fontsize=9.5)
    for k, o in enumerate(sec_offsets, start=1):
        ax1.axvline(o, color="#999999", linewidth=0.5, linestyle=":")
        ax1.annotate("S%d" % k, xy=(o + n * 0.002, len(assets) - 0.6), fontsize=6,
                     rotation=90, va="top", color="#666666")
    ax1.grid(axis="x", color="#dddddd", linewidth=0.5, zorder=0)
    ax1.set_axisbelow(True)
    ax1.legend(handles=[Patch(color=COLORS[k], label=k) for k in COLORS],
               fontsize=7.5, loc="lower right")

    classes = {}
    for a in assets:
        classes.setdefault(a["asset_class"], []).append(a["resolution"])
    cls_names = sorted(classes, key=lambda c: (-len(classes[c]), c))
    for i, c in enumerate(cls_names):
        left = 0
        for res in COLORS:
            k = sum(1 for r in classes[c] if r == res)
            if k:
                ax2.barh(i, k, left=left, color=COLORS[res], height=0.7)
                left += k
    ax2.set_yticks(range(len(cls_names)))
    ax2.set_yticklabels(cls_names, fontsize=7)
    ax2.invert_yaxis()
    ax2.set_xlabel("assets", fontsize=9)
    ax2.set_title("B. Asset classes by resolution status", fontsize=10)
    ax2.grid(axis="x", color="#dddddd", linewidth=0.5)
    ax2.set_axisbelow(True)

    fig.tight_layout()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150)
    print("figure:", OUT_PNG, OUT_PNG.stat().st_size, "bytes")
    print("metrics:", json.dumps(metrics, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())