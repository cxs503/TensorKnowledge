#!/usr/bin/env python3
"""Figure for wp-5716-04: review-side recomputation, not a re-plot of the report.

Panel A: every row of the report's ⑥ error table that is expressed in percent,
         parsed straight out of the fetched markdown (no hand-typed numbers),
         against the predeclared 3% acceptance line and the report's own 25%
         screening line (D01).
Panel B: first-order time/speed closure reconstructed from the report's totals
         (read from docs/kf/wp-5716-04/recompute.json, produced by
         scripts/kf/review_wp_5716_04.py).

Usage: python3 scripts/kf/fig_wp_5716_04.py
Writes docs/kf/wp-5716-04/figures/{fig_review_errors.png,fig_review_closure.png}
"""
from __future__ import annotations

import json
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SNAP = "docs/kf/wp-5716-04/source_5716.md"
RECOMP = "docs/kf/wp-5716-04/recompute.json"
OUT = "docs/kf/wp-5716-04/figures"

ROW_RE = re.compile(r"^\| ([^|]+?) \| ([^|]+?) \| ([^|]+?) \| (是|否) \|$", re.M)
PCT_RE = re.compile(r"^\s*(≤)?\s*([0-9.]+(?:[eE][-+]?[0-9]+)?)\s*%\s*$")

# Reviewer-side English labels for the report's §6 row names.  Only the LABELS are
# translated (this host has no CJK font); every NUMBER is parsed from the markdown.
LABEL_EN = {
    "Cb 几何反算 vs 声明值": "Cb back-calc vs declared",
    "A2 复现上游工件（同配置）": "A2 reproduces upstream artifact",
    "B2 复现上游工件（同输入）": "B2 reproduces upstream artifact",
    "E1 冰载荷闭环": "E1 ice-load closed loop",
    "E1 航速闭环": "E1 speed closed loop",
    "E1 冰阻力闭环": "E1 ice-resistance closed loop",
    "C1 MT Uikku 链 vs Hu&Zhou 2016（MAPE）": "C1 Uikku chain vs Hu&Zhou 2016",
    "B2 板格系数 vs 简支板理论 β": "B2 plate coeff vs plate theory beta",
    "TensorFEM Mindlin Q4 vs 闭式 Mindlin": "TensorFEM Mindlin Q4 vs closed form",
    "D1 vs C3 冰中航速（独立实现）": "D1 vs C3 speed in ice",
}


def parse_error_rows(md: str) -> list[dict]:
    rows = []
    for item, meas, base, ok in ROW_RE.findall(md):
        item, meas, base = item.strip(), meas.strip(), base.strip()
        m = PCT_RE.match(meas)
        if not m:
            continue  # absolute / exponent-only quantities are listed in text, not plotted
        val = float(m.group(2))
        if val == 0.0:
            val = 1e-9  # 0.0000% -> floor for log axis, flagged in caption
        rows.append({"item": item, "label_en": LABEL_EN.get(item, "row %d" % len(rows)),
                     "value_pct": val, "raw": meas,
                     "baseline": base, "ok": ok == "是"})
    return rows


def fig_errors(rows: list[dict], path: str) -> None:
    rows = sorted(rows, key=lambda r: r["value_pct"])
    labels = [r["label_en"] for r in rows]
    vals = [r["value_pct"] for r in rows]
    colors = ["#2b7a3d" if r["ok"] else "#b3261e" for r in rows]
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.barh(range(len(vals)), vals, color=colors, alpha=0.85)
    ax.set_xscale("log")
    ax.set_yticks(range(len(vals)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.axvline(3.0, color="k", ls="--", lw=1.4, label="3% acceptance line (mandated)")
    ax.axvline(25.0, color="#1f5fa8", ls=":", lw=1.4, label="25% predeclared screen (D01 Uikku)")
    for i, r in enumerate(rows):
        ax.text(r["value_pct"] * 1.12, i, r["raw"] + ("" if r["ok"] else "  (<3%: NO)"),
                va="center", fontsize=7.2)
    ax.set_xlim(1e-9, 4e2)
    ax.set_xlabel("reported / recomputed value [%] (log scale; 0.0000% rows plotted at 1e-9 floor)")
    ax.set_title("Report 5716 section-6 error table vs acceptance lines\n"
                 "(review side: values parsed from the markdown, labels reviewer-translated)",
                 fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="x", which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_closure(r: dict, path: str) -> None:
    c = r["a6_ice_segment_speed_reconstruction"]
    speeds = c["implied_mean_ice_kn"]
    names = list(speeds) + ["design point (as reported)"]
    vals = list(speeds.values()) + [c["reported_design_point_kn"]]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    bars = ax.bar(range(len(vals)), vals,
                  color=["#b3261e", "#d98b00", "#d98b00", "#1f5fa8"], alpha=0.85)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(names, fontsize=9)
    ax.axhline(c["reported_design_point_kn"], color="#1f5fa8", ls="--", lw=1.2)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_ylabel("mean ice-segment speed [kn]")
    ax.set_title("Time/speed closure reconstructed from report totals\n"
                 "(684.1 nm, 27.0% ice, 13 kn open water -> required ice speed)",
                 fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> int:
    md = open(SNAP, encoding="utf-8").read()
    r = json.load(open(RECOMP, encoding="utf-8"))["recompute"]
    os.makedirs(OUT, exist_ok=True)
    rows = parse_error_rows(md)
    fig_errors(rows, os.path.join(OUT, "fig_review_errors.png"))
    fig_closure(r, os.path.join(OUT, "fig_review_closure.png"))
    print("percent rows parsed:", len(rows))
    for x in rows:
        print(" ", x["raw"], "|", x["ok"], "|", x["item"][:52])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())