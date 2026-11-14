"""wp-9246-02 图件：分类判定证据图（仿真量？不是——这是文档判定证据的可视化）。

纯文档/分类任务没有场量云图；这里给的是判定输入的可复核视图：
左 = 6 个候选类型 × 5 条 registry 信号的命中矩阵；右 = 命中数 + step-fit 比例。
"""

from __future__ import annotations

from pathlib import Path

import kf9246_spec as S


def make_figure(classification: dict, out_png: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sig = classification["signals"]["per_type"]
    stepfit = classification["signals"]["step_fit"]
    primary = classification["report_type"]["primary"]
    types = list(S.PROBES)
    width = max(len(sig[t]["signals"]) for t in types)

    grid = [[1 if (j < len(sig[t]["signals"]) and sig[t]["signals"][j]["hit"]) else 0
             for j in range(width)] for t in types]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 4.6), dpi=110,
                                   gridspec_kw={"width_ratios": [1.65, 1]})
    ax1.imshow(grid, cmap="Greens", vmin=0, vmax=1, aspect="auto")
    ax1.set_xticks(range(width))
    ax1.set_xticklabels([f"S{i + 1}" for i in range(width)], fontsize=8)
    ax1.set_yticks(range(len(types)))
    ax1.set_yticklabels([S.SHORT[t] for t in types], fontsize=9)
    for i, t in enumerate(types):
        for j in range(width):
            hit = bool(grid[i][j])
            ax1.text(j, i, "hit" if hit else "miss", ha="center", va="center", fontsize=7.5,
                     color="white" if hit else "#555555")
        ax1.text(width - 0.3, i, f"{sig[t]['hits']}/{sig[t]['total']}", ha="left",
                 va="center", fontsize=8.5)
        if t == primary:
            ax1.text(width - 0.3, i + 0.32, "PRIMARY", ha="left", va="center", fontsize=7.5,
                     color="#0a7", weight="bold")
    ax1.set_xlim(-0.5, width + 1.5)
    ax1.set_title("registry identify_signals x candidate type\n"
                  "(regex probes on report 9246 markdown; right column = hits/total)", fontsize=9.5)

    hits = [sig[t]["hits"] for t in types]
    steps = [(stepfit[t]["satisfiable"] / stepfit[t]["evaluated"])
             if stepfit[t]["evaluated"] else 0.0 for t in types]
    y = list(range(len(types)))
    ax2.barh([i - 0.2 for i in y], hits, height=0.38, color="#3b8", label="signals hit (of 5)")
    ax2.barh([i + 0.2 for i in y], steps, height=0.38, color="#37c",
             label="step-fit fraction (registry steps)")
    ax2.set_yticks(y)
    ax2.set_yticklabels([S.SHORT[t] for t in types], fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 5.8)
    ax2.axvline(2, color="#c33", ls="--", lw=1)
    ax2.text(2.08, -0.72, "R1 floor = 2 signals", color="#c33", fontsize=8)
    ax2.set_title(f"decision inputs -> primary = {S.SHORT[primary]}", fontsize=9.5)
    ax2.legend(fontsize=7.5, loc="lower right")
    ax2.grid(axis="x", alpha=0.3)

    fig.suptitle("wp-9246-02 report-type classification evidence "
                 "(report_id=9246, sha256:80bcb321…165b5)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)
    return out_png