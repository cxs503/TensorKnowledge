"""生成 wp-9632-02 的图示（数据全部读 classification.json，零手抄）。

Panel A：六分型候选的信号覆盖（matched / partial / absent 与加权得分）
Panel B：报告结构切分（20 个标题块）与 scientific-computation 命中信号的位置

字体稳妥起见图中用英文标签，中文说明写在报告图注里。
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PKG = Path(__file__).resolve().parent
OUT = PKG / "figures" / "classification_overview.png"


def main() -> int:
    cls = json.loads((PKG / "classification.json").read_text(encoding="utf-8"))
    matrix = cls["candidate_matrix"]
    labels = [r["report_type"] for r in matrix][::-1]
    m = [r["matched"] for r in matrix][::-1]
    p = [r["partial"] for r in matrix][::-1]
    a = [r["absent"] for r in matrix][::-1]
    score = [r["score"] for r in matrix][::-1]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11.5, 8.4), gridspec_kw={"height_ratios": [1.0, 1.25]}
    )

    y = range(len(labels))
    ax1.barh(y, m, color="#2b7a4b", label="matched (1.0)")
    ax1.barh(y, p, left=m, color="#e0a800", label="partial (0.5)")
    ax1.barh(y, a, left=[i + j for i, j in zip(m, p)], color="#cfd4d8", label="absent (0.0)")
    for i, (s, lab) in enumerate(zip(score, labels)):
        ax1.text(5.25, i, f"score={s:.2f}", va="center", fontsize=9)
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(labels, fontsize=9)
    ax1.set_xlim(0, 6.6)
    ax1.set_xlabel("number of identify_signals")
    ax1.set_title(
        "A. Report-type hypothesis test: registry identify_signals coverage "
        f"(selected: {cls['report_type']}, confidence={cls['confidence']['label']})",
        fontsize=10,
    )
    ax1.legend(fontsize=8, loc="lower right")
    ax1.grid(axis="x", alpha=0.3)

    secs = cls["structure"]["sections"]
    text_len = cls["structure"]["chars"]
    for s in secs:
        yy = 0 if s["level"] == 1 else (0.45 if s["level"] == 2 else 0.9)
        width = s["end_offset"] - s["start_offset"]
        ax2.barh(yy, width, left=s["start_offset"], height=0.32,
                 color={1: "#1f4e79", 2: "#2e75b6", 3: "#9dc3e6"}[s["level"]])
        if width > 600:
            # 图中只用 ASCII 标签（本机无 CJK 字体）；标题中文对照见报告结构表
            ax2.text(s["start_offset"] + 40, yy + 0.22, s["id"], fontsize=7, va="bottom")
    hits = [s for s in cls["signals"]
            if s["report_type"] == "scientific-computation" and s["evidence_id"]]
    ev = {e["id"]: e for e in cls["evidence"]}
    for s in hits:
        e = ev[s["evidence_id"]]
        ax2.axvline(e["start_offset"], color="#c00000", lw=1.0, ls="--", alpha=0.8)
        ax2.text(e["start_offset"], 1.35, s["signal"].replace(" ", "\n", 1), fontsize=6.5,
                 color="#c00000", rotation=0, ha="center", va="bottom")
    ax2.set_ylim(-0.35, 1.95)
    ax2.set_xlim(0, text_len)
    ax2.set_yticks([0, 0.45, 0.9])
    ax2.set_yticklabels(["h1", "h2", "h3"], fontsize=8)
    ax2.set_xlabel(f"character offset in report markdown (chars={text_len})")
    ax2.set_title(
        "B. Structure segmentation (20 heading blocks) and positions of the four "
        f"matched scientific-computation signals (dashed), n_tables={cls['structure']['table_blocks']} "
        f"n_figures_ref={cls['structure']['figure_refs']}",
        fontsize=10,
    )
    ax2.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())