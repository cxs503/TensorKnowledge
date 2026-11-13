"""wp-11478-01 · figure + metrics for the platform report (all numbers computed, none hand-written).

Panel A: where each registered asset sits along the report's character axis (char-span bars,
         coloured by resolution status) — makes "locator resolvable" visible.
Panel B: assets per resolution class (recounted from the manifest).
Panel C: assets per report section ①-⑥.

Outputs:
  docs/wp-11478-01/asset_span_map.png
  runs/wp-11478-01/figure_metrics_11478.json  (coverage ratio etc., consumed by the report text)
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PKG = "wp-11478-01"
RUN_DIR = pathlib.Path("runs") / PKG
DOC_DIR = pathlib.Path("docs") / PKG   # tracked (artifacts/ is gitignored)
MANIFEST = DOC_DIR / "asset_manifest.json"
PNG = DOC_DIR / "asset_span_map.png"
METRICS = RUN_DIR / "figure_metrics_11478.json"

COLORS = {
    "resolved_in_source": "#2c7fb8",
    "referenced_unresolved": "#d95f0e",
    "declared_absent": "#999999",
    "resolved_in_platform_record": "#31a354",
}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    md = (RUN_DIR / "report_11478.md").read_text()
    assets = manifest["assets"]

    spans = [(a["locator"]["start_char"], a["locator"]["end_char"]) for a in assets]
    covered = set()
    for s, e in spans:
        covered.update(range(s, e))
    coverage = len(covered) / len(md)

    by_res = manifest["counts"]["by_resolution"]
    sec_order = ["## ① 案例介绍", "## ② 怎么做的", "## ③ 计算结果", "## ④ 结果图",
                 "## ⑤ 注意点", "## ⑥ 误差判定"]
    short = {s: s.split()[1] for s in sec_order}
    by_sec = {short[s]: 0 for s in sec_order}
    for a in assets:
        key = short.get(a["in_report_section"])
        if key:
            by_sec[key] += 1

    fig, axes = plt.subplots(3, 1, figsize=(11, 9.6), gridspec_kw=dict(height_ratios=[2.6, 1.0, 1.0]))
    ax = axes[0]
    for i, a in enumerate(assets):
        y = len(assets) - i
        loc = a["locator"]
        ax.broken_barh([(loc["start_char"], max(loc["end_char"] - loc["start_char"], 12))], (y - 0.4, 0.8),
                       facecolors=COLORS.get(a["resolution"], "#555555"), edgecolor="none")
        ax.text(-120, y, a["asset_id"], ha="right", va="center", fontsize=7.5)
    ax.set_xlim(0, len(md))
    ax.set_ylim(0.3, len(assets) + 0.8)
    ax.set_yticks([])
    ax.set_xlabel(f"report character offset (markdown, {len(md)} chars)")
    ax.set_title("A · asset locators along the source text axis "
                 f"(n={len(assets)}, span coverage={coverage * 100:.1f}% of chars)", fontsize=10)
    handles = [plt.Line2D([], [], marker="s", linestyle="", markersize=7, color=c, label=k)
               for k, c in COLORS.items()]
    ax.legend(handles=handles, fontsize=7, loc="upper center", ncol=4, frameon=False,
              bbox_to_anchor=(0.5, -0.28))

    ax = axes[1]
    keys = list(by_res)
    ax.bar(keys, [by_res[k] for k in keys], color=[COLORS.get(k, "#555555") for k in keys])
    for x, k in enumerate(keys):
        ax.text(x, by_res[k] + 0.1, str(by_res[k]), ha="center", fontsize=8)
    ax.set_ylim(0, max(by_res.values()) + 1.2)
    ax.set_title("B · assets by resolution status (recount from manifest)", fontsize=10)
    ax.tick_params(axis="x", labelsize=7.5)

    ax = axes[2]
    secs = list(by_sec)
    ax.bar(secs, [by_sec[s] for s in secs], color="#756bb1")
    for x, s in enumerate(secs):
        ax.text(x, by_sec[s] + 0.1, str(by_sec[s]), ha="center", fontsize=8)
    ax.set_ylim(0, max(by_sec.values()) + 2)
    ax.set_title("C · assets per report section (①-⑥)", fontsize=10)
    ax.set_xlabel("report section")

    fig.tight_layout()
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG, dpi=140)
    metrics = dict(chars=len(md), assets=len(assets), span_coverage=round(coverage, 4),
                   covered_chars=len(covered), by_resolution=by_res, by_section=by_sec,
                   png=str(PNG), png_bytes=PNG.stat().st_size)
    METRICS.write_text(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(json.dumps({k: metrics[k] for k in ("assets", "span_coverage", "covered_chars", "png_bytes")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())