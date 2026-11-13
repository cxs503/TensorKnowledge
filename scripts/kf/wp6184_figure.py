#!/usr/bin/env python3
"""Figure for wp-6184-04: evidence map of the independent review.

Left  — per-check status of the 10 review probes (pass / fail / not_run), with the
        single non-blocking failure (R10 asset completeness) visible instead of hidden.
Right — the source report's published margin column against the value recomputed
        from its own EEXI / required columns, with the print-rounding band.

Reads only committed artifacts (review_checks.json), so it is reproducible offline.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "docs/kf/wp-6184-04"
data = json.loads((PKG / "review_checks.json").read_text(encoding="utf-8"))

COLOR = {"pass": "#2e7d32", "fail": "#c62828", "not_run": "#9e9e9e"}
LABEL = {"pass": "pass", "fail": "fail (non-blocking)", "not_run": "not run"}

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2),
                               gridspec_kw={"width_ratios": [1.15, 1]})

checks = data["checks"]
ys = list(range(len(checks)))[::-1]
for y, c in zip(ys, checks):
    ax1.barh(y, 1, color=COLOR[c["status"]], alpha=0.88, height=0.72)
    ax1.text(0.02, y, f'{c["id"]}  {c["name"]}', va="center", ha="left",
             fontsize=8.5, color="white", fontweight="bold")
ax1.set_yticks([])
ax1.set_xticks([])
ax1.set_xlim(0, 1)
ax1.set_title("review probes against the source bytes\n"
              f'{data["source_hash"][:23]}…  ({len(checks)} checks)', fontsize=10)
ax1.legend(handles=[Patch(color=COLOR[k], label=LABEL[k]) for k in ("pass", "fail", "not_run")],
           loc="lower right", fontsize=8, frameon=True)

rows = next(c for c in checks if c["id"].startswith("R7"))["evidence"]["rows"]
rep = [r["margin_reported"] for r in rows]
rec = [r["margin_recomputed_pointwise"] for r in rows]
band = [max(abs(a - b) for a, b in
            zip(r["feasible_band_from_print_rounding"], [r["margin_recomputed_pointwise"]] * 2))
        for r in rows]
ax2.errorbar(rec, rep, xerr=None,
             yerr=[[max(0.0, r["margin_reported"] - r["feasible_band_from_print_rounding"][0]) for r in rows],
                   [max(0.0, r["feasible_band_from_print_rounding"][1] - r["margin_reported"]) for r in rows]],
             fmt="o", ms=6, color="#1565c0", ecolor="#90caf9", capsize=3,
             label="published vs recomputed (band = print rounding)")
lim = [min(rep + rec) - 3, max(rep + rec) + 3]
ax2.plot(lim, lim, "--", color="#616161", lw=1, label="identity")
for r in rows:
    ax2.annotate(r["ship"], (r["margin_recomputed_pointwise"], r["margin_reported"]),
                 textcoords="offset points", xytext=(5, 4), fontsize=7, color="#37474f")
ax2.set_xlabel("margin % recomputed from published EEXI / required columns", fontsize=9)
ax2.set_ylabel("margin % as published in report §3", fontsize=9)
ax2.set_title("source-report arithmetic: 11/11 inside the print-rounding band", fontsize=10)
ax2.grid(alpha=0.25)
ax2.legend(fontsize=8)

fig.suptitle("wp-6184-04 independent review — report 6184 / upstream wp-6184-01",
             fontsize=11.5, y=0.99)
fig.tight_layout(rect=(0, 0, 1, 0.95))
out = PKG / "figures/review_6184_evidence.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=150)
print(out)