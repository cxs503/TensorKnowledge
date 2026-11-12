#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 图件（只从工件读数字，零手抄）。

fig1_batch_strata.png : 60 份批次的分层分配与实抽（12 单元）+ 仓覆盖
fig2_design_lanes.png : 三臂工作包/并发/门禁设计对照
fig3_metric_status.png: 五指标×三臂的数据可得性状态矩阵（执行期实时更新，
                        未结算=WITHHELD 用灰色，完成=绿，失败=红）

用法: python scripts/rci_f1_figures.py --dir artifacts/rci-f1-abc
"""
from __future__ import annotations

import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rci_f1_metrics import METRIC_KEYS, load_runs, compute

STATUS_COLOR = {"REAL": "#2e7d32", "PENDING": "#9e9e9e", "WITHHELD": "#757575",
                "FAILED": "#c62828", "NOT_STARTED": "#bdbdbd"}


def fig_batch(batch: dict, path: str) -> None:
    alloc = batch["allocation"]
    obs = {}
    for d in batch["documents"]:
        obs[d["stratum"]] = obs.get(d["stratum"], 0) + 1
    cells = sorted(alloc)
    x = np.arange(len(cells))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [2.1, 1]})
    ax1.bar(x - 0.2, [alloc[c] for c in cells], width=0.4, label="prereg allocation", color="#90a4ae")
    ax1.bar(x + 0.2, [obs.get(c, 0) for c in cells], width=0.4, label="realized", color="#1565c0")
    ax1.set_xticks(x)
    ax1.set_xticklabels([c.replace("|", "\n") for c in cells], fontsize=7)
    ax1.set_ylabel("documents")
    ax1.set_title(f"Batch60 strata (n={batch['n']}, cells={batch['observed']['cells_covered']}, "
                  f"repos={batch['observed']['repos_covered']})", fontsize=10)
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.3)

    repos = batch["observed"]["by_repo"]
    names = list(repos)[::-1]
    ax2.barh(names, [repos[n] for n in names], color="#00897b")
    ax2.set_xlabel("documents")
    ax2.set_title("repo coverage", fontsize=10)
    ax2.tick_params(labelsize=7)
    ax2.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


def fig_design(wps: dict, path: str) -> None:
    lanes = ["A", "B", "C"]
    labels = {"A": "A: 1 strong agent\n(whole batch)",
              "B": "B: 20 ordinary agents\n(no review, no skills)",
              "C": "C: 20 ordinary agents\n+ independent review + skills"}
    n_agents = {l: len({p["agent_slot"] for p in wps["packages"] if p["lane"] == l}) for l in lanes}
    n_pkgs = {l: len([p for p in wps["packages"] if p["lane"] == l]) for l in lanes}
    docs = {l: sum(p["n_docs"] for p in wps["packages"] if p["lane"] == l) for l in lanes}
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    x = np.arange(3)
    w = 0.26
    ax.bar(x - w, [n_agents[l] for l in lanes], w, label="agents", color="#5c6bc0")
    ax.bar(x, [n_pkgs[l] for l in lanes], w, label="work packages", color="#26a69a")
    ax.bar(x + w, [docs[l] for l in lanes], w, label="doc slots (=60 each)", color="#ef6c00")
    for i, l in enumerate(lanes):
        ax.text(i - w, n_agents[l] + 1.0, str(n_agents[l]), ha="center", fontsize=8)
        ax.text(i, n_pkgs[l] + 1.0, str(n_pkgs[l]), ha="center", fontsize=8)
        ax.text(i + w, docs[l] + 1.0, str(docs[l]), ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([labels[l] for l in lanes], fontsize=8)
    ax.set_ylabel("count")
    ax.set_title("Three-arm design: sole variable = organisation "
                 "(model tier / review / skills)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


def fig_status(metrics: dict, path: str) -> None:
    keys = METRIC_KEYS
    arms = ["A", "B", "C"]
    grid = np.zeros((len(keys), 3))
    stat = []
    for i, k in enumerate(keys):
        row = []
        for j, a in enumerate(arms):
            cell = (metrics.get("arms", {}).get(a) or {}).get(k) or {}
            s = cell.get("status", "NOT_STARTED")
            row.append(s)
            grid[i, j] = {"REAL": 3, "PENDING": 2, "WITHHELD": 1, "FAILED": 0,
                          "NOT_STARTED": 0.5}.get(s, 0.5)
        stat.append(row)
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    cmap = matplotlib.colors.ListedColormap(["#c62828", "#9e9e9e", "#90caf9", "#2e7d32"])
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(range(3))
    ax.set_xticklabels(["A", "B", "C"], fontsize=10)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([k.split("_", 1)[1] for k in keys], fontsize=8)
    for i in range(len(keys)):
        for j in range(3):
            ax.text(j, i, stat[i][j], ha="center", va="center", fontsize=7, color="black")
    ax.set_title("metric data availability (green=measured, grey=withheld/pending)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/rci-f1-abc")
    args = ap.parse_args()
    out = os.path.join(args.dir, "figures")
    os.makedirs(out, exist_ok=True)
    batch = json.load(open(os.path.join(args.dir, "batch60.json"), encoding="utf-8"))
    wps = json.load(open(os.path.join(args.dir, "tk_work_packages.json"), encoding="utf-8"))
    fig_batch(batch, os.path.join(out, "fig1_batch_strata.png"))
    fig_design(wps, os.path.join(out, "fig2_design_lanes.png"))
    runs = load_runs(os.path.join(args.dir, "runs"))
    metrics = compute(batch, runs, os.path.join(args.dir, "blind"))
    fig_status(metrics, os.path.join(out, "fig3_metric_status.png"))
    for f in sorted(os.listdir(out)):
        print(f, os.path.getsize(os.path.join(out, f)))


if __name__ == "__main__":
    main()