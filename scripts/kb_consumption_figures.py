#!/usr/bin/env python3
"""kb_consumption_figures —— KB 消费研究出图（数字全部从工件读，零手抄）。

三块：
  (a) A/B 通过率（锚×臂）：runs/kb_ab_*/summary.json 的 cells
  (b) 检索基准 ref vs got：artifacts/kb_retrieval/{bench.json,holdout/bench.json}
  (c) 消费漏斗：artifacts/kb_consumption/summary.json（卡数/注入总次数/被引总次数）

用法：python3 scripts/kb_consumption_figures.py [--out artifacts/kb_consumption/kb_consumption.png]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(p: pathlib.Path):
    return json.loads(p.read_text()) if p.exists() else None


def latest_ab():
    dirs = sorted((ROOT / "runs").glob("kb_ab_*"), key=lambda p: p.name)
    for d in reversed(dirs):
        s = load(d / "summary.json")
        if s:
            return s, d.name
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/kb_consumption/kb_consumption.png")
    a = ap.parse_args()
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))

    # (a) A/B 通过率
    ab, ab_name = latest_ab()
    ax = axes[0]
    if ab:
        anchors = ["K1", "K2", "K3"]
        arms = ["A", "B", "C"]
        width = 0.26
        for i, arm in enumerate(arms):
            vals = [(ab["cells"].get(f"{an}/{arm}") or {}).get("pass_rate") or 0.0 for an in anchors]
            ax.bar([x + (i - 1) * width for x in range(len(anchors))], vals, width,
                   label=f"arm {arm}", alpha=0.85)
        ax.set_xticks(range(len(anchors)))
        ax.set_xticklabels(["K1 fact\n(ITTC)", "K2 discipline\n(cluster/arch)", "K3 capability\n(card facts)"])
        ax.set_ylim(0, 1.08)
        ax.set_ylabel("pass rate")
        ax.set_title(f"(a) KB arms A/B/C (reps={ab.get('reps')}, {ab.get('model')})")
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(axis="y", alpha=0.3)
    else:
        ax.text(0.5, 0.5, "no A/B run found", ha="center")

    # (b) 检索基准
    ax = axes[1]
    v1 = load(ROOT / "artifacts/kb_retrieval/bench.json")
    ho = load(ROOT / "artifacts/kb_retrieval/holdout/bench.json")
    metrics = ["precision_at_1", "recall_at_5", "mrr_at_5"]
    labels, refv, gotv = [], [], []
    for tag, b in (("v1", v1), ("holdout", ho)):
        if not b:
            continue
        for m in metrics:
            labels.append(f"{tag}\n{m}")
            refv.append(b["ref"][m])
            gotv.append(b["got"][m])
    if labels:
        idx = range(len(labels))
        ax.bar([i - 0.2 for i in idx], refv, 0.4, label="ref: naive overlap", alpha=0.85)
        ax.bar([i + 0.2 for i in idx], gotv, 0.4, label="got: ke.consume.rank", alpha=0.85)
        ax.set_xticks(list(idx))
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("score")
        ax.set_title("(b) KB retrieval ref vs got (prereg thresholds)")
        ax.legend(fontsize=8, loc="lower right")
        ax.grid(axis="y", alpha=0.3)
    else:
        ax.text(0.5, 0.5, "no bench artifacts", ha="center")

    # (c) 消费漏斗
    ax = axes[2]
    s = load(ROOT / "artifacts/kb_consumption/summary.json")
    if s:
        vals = [s["kb_total"], s["injected_total"], s["cited_total"]]
        names = ["KB cards", "injected (all time)", "cited (all time)"]
        bars = ax.bar(names, vals, color=["#4c72b0", "#dd8452", "#c44e52"], alpha=0.9)
        for b_, v in zip(bars, vals):
            ax.text(b_.get_x() + b_.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=9)
        ax.set_ylim(0, max(vals) * 1.25)
        ax.set_ylabel("count")
        ax.set_title("(c) consumption funnel\n(embedded citation rate "
                     f"{s['embedded_citation_rate']:.4f})")
        ax.grid(axis="y", alpha=0.3)
    else:
        ax.text(0.5, 0.5, "no audit summary", ha="center")

    fig.suptitle("KB consumption research (m15255 / KBM-CONSUME-W1): A/B, retrieval bench, funnel",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=130)
    print("wrote", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())