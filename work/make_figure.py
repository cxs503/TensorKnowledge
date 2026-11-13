#!/usr/bin/env python3
"""Figure for the wp-444-04 review report (two panels, both from measured artifacts).

Panel A: declared vs independently recomputed structure counts of wp-444-01.
Panel B: the source report's ⑥ "baseline" values re-evaluated against the analytic
         formulas it names (out-of-scope observation, informs downstream 03/05).

Run: python3 work/make_figure.py
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "artifacts", "wp-444-04")


def main() -> int:
    ver = json.load(open(os.path.join(ART, "verification.json"), encoding="utf-8"))
    obs = json.load(open(os.path.join(ART, "out_of_scope_observations.json"),
                         encoding="utf-8"))
    c = ver["checks"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    labels = ["sections", "tables", "figures", "code refs"]
    declared = [c["H2_sections_count"]["declared"], c["H3_tables_count"]["declared"],
                c["H4_figures_count"]["declared"], c["H5_code_references_count"]["declared"]]
    recomputed = [c["H2_sections_count"]["recomputed"], c["H3_tables_count"]["recomputed"],
                  c["H4_figures_count"]["recomputed"],
                  c["H5_code_references_count"]["recomputed"]]
    x = range(len(labels))
    ax1.bar([i - 0.2 for i in x], declared, width=0.4, label="declared (wp-444-01)")
    ax1.bar([i + 0.2 for i in x], recomputed, width=0.4, label="recomputed (wp-444-04)")
    for i, (d, r) in enumerate(zip(declared, recomputed)):
        ax1.text(i - 0.2, d + 0.1, str(d), ha="center", fontsize=8)
        ax1.text(i + 0.2, r + 0.1, str(r), ha="center", fontsize=8)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels)
    ax1.set_ylabel("count")
    ax1.set_title("A. Asset-registration counts: declared vs recomputed")
    ax1.legend(fontsize=8)
    ax1.set_ylim(0, max(declared + recomputed) * 1.3)

    rows = [r for r in obs["rows"] if r.get("formula")]
    names = [r["row"] for r in rows]
    devs = [r["rel_error_vs_formula_pct"] for r in rows]
    colors = ["tab:red" if abs(d) > 0 else "tab:green" for d in devs]
    ax2.barh(range(len(rows)), devs, color=colors)
    ax2.set_yticks(range(len(rows)))
    ax2.set_yticklabels(names, fontsize=8)
    ax2.axvline(0, color="k", lw=0.8)
    ax2.axvline(15, color="tab:orange", ls="--", lw=0.9, label="15% tolerance")
    ax2.axvline(-15, color="tab:orange", ls="--", lw=0.9)
    for i, d in enumerate(devs):
        ax2.text(d, i, " %+.2f%%" % d, va="center", fontsize=8)
    ax2.set_xlabel("table baseline vs analytic formula (%), + = table higher")
    ax2.set_title("B. Source §6 baselines re-evaluated (observation)")
    ax2.legend(fontsize=8)

    fig.suptitle("wp-444-04 independent review of wp-444-01 (report 444)", fontsize=10)
    fig.tight_layout()
    out = os.path.join(ART, "review_checks.png")
    fig.savefig(out, dpi=140)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())