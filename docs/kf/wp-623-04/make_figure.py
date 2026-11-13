#!/usr/bin/env python3
"""Figure for the wp-623-04 review: per-step cost and local scaling exponent,
re-derived from the report's own table (no hand-typed numbers).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PKG = Path(__file__).resolve().parent
SRC = PKG.parents[2] / "work/w623/source_623.md"
OUT = PKG / "figures" / "kf_wp623_04_scaling.png"

lines = SRC.read_text().rstrip("\n").split("\n")
rows = {}
for ln in lines:
    m = re.match(r"^\| (scale_\d+k) \| ([\d,]+) \| ([\d.]+) \| (\d+) \| ([\d.]+) \| ([\d,]+) \|$", ln)
    if m:
        rows[m.group(1)] = {"n": int(m.group(2).replace(",", "")), "steps": int(m.group(4)),
                            "ms": float(m.group(5)) * 1000.0 / int(m.group(4))}
names = ["scale_10k", "scale_50k", "scale_100k"]
n = [rows[k]["n"] for k in names]
ms = [rows[k]["ms"] for k in names]
ideal = [ms[0] * x / n[0] for x in n]
ratio = ms[-1] / ideal[-1]
e1 = math.log(ms[1] / ms[0]) / math.log(n[1] / n[0])
e2 = math.log(ms[2] / ms[1]) / math.log(n[2] / n[1])

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].loglog(n, ms, "o-", label="measured ms/step")
ax[0].loglog(n, ideal, "--", label=f"ideal O(N) from 10k (x{ratio:.3f} at 100k)")
for x, y, k in zip(n, ms, names):
    ax[0].annotate(f"{k}\n{y:,.0f} ms/step, {rows[k]['steps']} timed steps",
                   (x, y), textcoords="offset points", xytext=(-10, 10), fontsize=7)
ax[0].set_xlabel("particles N")
ax[0].set_ylabel("wall-clock per step [ms]")
ax[0].set_title("(a) per-step cost re-derived from report table")
ax[0].legend(fontsize=7)
ax[0].grid(True, which="both", alpha=0.3)

ax[1].bar([f"10k->50k\n(N x{n[1]/n[0]:.2f})", f"50k->100k\n(N x{n[2]/n[1]:.2f})"],
          [e1, e2], color=["tab:blue", "tab:red"])
for i, e in enumerate((e1, e2)):
    ax[1].annotate(f"{e:.3f}", (i, e), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=8)
ax[1].axhline(1.0, ls="--", c="k", lw=0.8, label="perfect O(N)")
ax[1].set_ylabel("local scaling exponent")
ax[1].set_title("(b) local exponent: 1.12x chord hides the top-end jump")
ax[1].set_ylim(0, 2)
ax[1].legend(fontsize=7)
fig.tight_layout()
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=130)
sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
print(json.dumps({"png": str(OUT.relative_to(PKG.parents[2])), "sha256": "sha256:" + sha,
                  "bytes": OUT.stat().st_size, "ratio_vs_ideal": round(ratio, 4),
                  "exponent_10k_50k": round(e1, 3), "exponent_50k_100k": round(e2, 3),
                  "ms_per_step": {k: round(rows[k]['ms'], 1) for k in names}}, indent=1))
