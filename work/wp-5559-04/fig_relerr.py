#!/usr/bin/env python3
"""wp-5559-04 · figure for the review report.

Panel A: declared relative error vs the error the reviewer recomputed from the two
displayed numbers, for every row of the report's §3.2 verification table - the
anomalous row (floe-slope sampling side) is the one that leaves the diagonal.
Panel B: G3 applicability coverage - which of the four ice states actually had a
domain fraction computed.

Numbers come from work/wp-5559-04/report_side_math.json (programmatic, zero-hand-copy).
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

W = Path("work/wp-5559-04")
MATH = json.loads((W / "report_side_math.json").read_text(encoding="utf-8"))

rows = [(k, v) for k, v in MATH["verification_table_recheck"].items()
        if v and v["stated_rel_err"] is not None and v["reviewer_rel_err_from_displayed"] is not None]
rows = [(k, v["stated_rel_err"], v["reviewer_rel_err_from_displayed"]) for k, v in rows]
EN = {
    "相关长度 L": "corr. length L",
    "磨道宽度 W": "channel width W",
    "浮冰谱斜率（抽样端）": "floe-slope (sampling)",
    "浮冰谱斜率（场反测）": "floe-slope (field)",
    "间距均值 λ": "ridge spacing mean",
    "帆高均值 0.3+λ_s": "sail height mean",
    "龙骨-帆比 k": "keel/sail ratio k",
    "黏度峰 ν/ν_w": "viscosity peak nu/nu_w",
}
rows = [(EN.get(k, k), a, b) for k, a, b in rows]
rows.sort(key=lambda r: r[1])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.4))
labels = [r[0] for r in rows]
stated = [max(r[1], 1e-9) for r in rows]
recomputed = [max(r[2], 1e-9) for r in rows]
y = range(len(rows))
ax1.barh([i - 0.2 for i in y], stated, height=0.38, label="declared (§3.2 table)", color="#4c78a8")
ax1.barh([i + 0.2 for i in y], recomputed, height=0.38, label="reviewer recomputed (from the displayed pair)", color="#f58518")
ax1.set_yticks(list(y))
ax1.set_yticklabels(labels, fontsize=9)
ax1.set_xscale("log")
ax1.set_xlabel("relative error (log scale)")
ax1.axvline(0.03, color="#d62728", ls="--", lw=1)
ax1.axvline(0.15, color="#8c564b", ls=":", lw=1)
ax1.text(0.0305, len(rows) - 0.4, "3%", color="#d62728", fontsize=8)
ax1.text(0.155, len(rows) - 0.4, "15%", color="#8c564b", fontsize=8)
ax1.set_title("A. §3.2 rows: declared vs reviewer-recomputed relative error")
ax1.legend(fontsize=8, loc="lower right")
ax1.grid(axis="x", alpha=0.3)

bad = [i for i, r in enumerate(rows) if abs(r[1] - r[2]) > 1e-3]
for i in bad:
    ax1.annotate("unreconcilable\n(F-02)", xy=(max(stated[i], recomputed[i]), i),
                 xytext=(0.30, i - 0.6), fontsize=8, color="#d62728",
                 arrowprops=dict(arrowstyle="->", color="#d62728", lw=1))

g3 = MATH["g3_applicability"]
states = list(g3["in_domain_fraction_per_state"])
vals = [g3["in_domain_fraction_per_state"][s] for s in states]
colors = ["#d62728" if v is None else "#54a24b" for v in vals]
plot_vals = [0.0 if v is None else v for v in vals]
ax2.bar(states, plot_vals, color=colors)
for s, v in zip(states, vals):
    ax2.text(s, (0.0 if v is None else v) + 0.02,
             "null\n(no fraction computed)" if v is None else f"{v:.4f}", ha="center", fontsize=8)
ax2.set_ylim(0, 1.15)
ax2.set_ylabel("in_domain_fraction (machine JSON, G3)")
ax2.set_title("B. G3 'four states REAL': 2/4 rest on a null fraction (F-01)")
ax2.grid(axis="y", alpha=0.3)

fig.suptitle("wp-5559-04 independent review of wp-5559-01 · report 5559 (IN10-A1 field_synth)", fontsize=11)
fig.tight_layout()
out = W / "fig1_review_relerr.png"
fig.savefig(out, dpi=150)
print("wrote", out, out.stat().st_size, "bytes")