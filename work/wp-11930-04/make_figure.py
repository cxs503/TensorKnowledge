#!/usr/bin/env python3
"""Figure for wp-11930-04: (A) published vs independently recomputed numbers,
(B) the Brun-index finding, (C) the 'local m' label finding. English axis labels
(CJK glyphs are not guaranteed in the headless font set); captions are Chinese.
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fig_review_reproducibility.png")

# (label, published, recomputed) — every pair taken from the report text / verify ledger
PAIRS = [
    ("cond(J)", 9.063, 9.0588),
    ("sigma_1", 5.848, 5.8499),
    ("sigma_2", 2.151, 2.1483),
    ("sigma_3", 0.645, 0.6458),
    ("pred t=0.05 [MPa]", 0.376, 0.3753),
    ("pred t=0.80 [MPa]", 0.372, 0.3713),
    ("CI width m", 721.537, 721.537),
    ("err t=0.05 [%]", -5.4, -5.47),
    ("err t=0.80 [%]", 2.6, 2.57),
    ("AC5 dev -2.705 [%]", 9.8, 9.833),
    ("AC5 dev -26.642 [%]", 788.1, 788.07),
    ("AC4b uc 2x [%]", -15.2, -15.24),
    ("AC4b uc 4x [%]", -33.4, -33.37),
    ("AC6 violation [%]", 83.5, 83.5),
]

fig = plt.figure(figsize=(15.5, 5.0))
ax1 = fig.add_subplot(1, 3, 1)
rel = [abs((c - p) / p) * 100 if p else 0.0 for _, p, c in PAIRS]
ax1.barh(range(len(PAIRS)), np.maximum(rel, 1e-6), color="#2b6cb0")
ax1.set_yticks(range(len(PAIRS)))
ax1.set_yticklabels([p[0] for p in PAIRS], fontsize=8)
ax1.set_xscale("log")
ax1.axvline(2.0, color="crimson", ls="--", lw=1)
ax1.set_xlabel("|recomputed - published| / published  [%]")
ax1.set_title("A  recomputability of published numbers\n(red = 2% band; 14/14 inside, max 1.30%)")
ax1.invert_yaxis()

ax2 = fig.add_subplot(1, 3, 2)
defs = ["published\n(report)", "Brun\n1/sqrt(1-rho^2)", "Belsley\nsqrt((1+rho)/(1-rho))", "1/sqrt(1-rho)\n(non-standard)"]
vals = [6.71, 4.796, 9.486, 6.745]
cols = ["#c53030", "#2f855a", "#2f855a", "#b7791f"]
ax2.bar(defs, vals, color=cols)
for x, v in enumerate(vals):
    ax2.text(x, v + 0.15, f"{v:.2f}", ha="center", fontsize=9)
ax2.set_ylabel("Brun collinearity index gamma")
ax2.set_title("B  worst pair ['k_c','k_p'], rho=0.978\npublished gamma=6.71 matches no standard formula")
ax2.tick_params(axis="x", labelsize=7.5)

ax3 = fig.add_subplot(1, 3, 3)
labels = ["report\n'local m'\ncolumn", "implied local m\n= 1/0.080, 1/0.045", "global m\n(fit, same paragraph)"]
x = [0, 1, 2]
ax3.bar([0], [0.080], color="#c53030", width=0.5)
ax3.bar([0.45], [0.045], color="#c53030", width=0.5)
ax3.bar([1], [12.5], color="#b7791f", width=0.5)
ax3.bar([1.45], [22.2], color="#b7791f", width=0.5)
ax3.bar([2], [262.976], color="#2f855a", width=0.6)
ax3.set_yscale("log")
ax3.set_xticks([0.225, 1.225, 2])
ax3.set_xticklabels(["report 'local m'\n0.080 / 0.045", "implied m\n12.5 / 22.2", "global m\n262.98"], fontsize=8)
ax3.set_ylabel("value (log)")
ax3.set_title("C  'local m' column is 1/m-like\n0.080 vs global 263 = 3 orders apart")
for xx, v in [(0, 0.080), (0.45, 0.045), (1, 12.5), (1.45, 22.2), (2, 262.976)]:
    ax3.text(xx, v * 1.25, f"{v:g}", ha="center", fontsize=8)

fig.suptitle("wp-11930-04 independent audit of report 11930 (BPM calibration feasibility) — "
             "recomputed vs published, and the two unrecomputable published quantities", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUT, dpi=130)
print(json.dumps({"figure": OUT, "bytes": os.path.getsize(OUT),
                  "max_rel_dev_pct": max(rel)}, ensure_ascii=False))