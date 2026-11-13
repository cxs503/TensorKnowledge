#!/usr/bin/env python3
"""Figure for wp-9840-01: where in the source document the 33 registered assets sit,
and how they resolve. All numbers are read from artifacts/wp-9840-01/asset_manifest.json
(programmatic injection, nothing hand-typed).
"""
import json
import pathlib
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

DOC_DIR = pathlib.Path("docs/wp-9840-01")
ART = pathlib.Path("artifacts/wp-9840-01/asset_manifest.json")
RUN = pathlib.Path("runs/wp-9840-01")

COLORS = {"resolved_in_source": "#2b6cb0", "referenced_unresolved": "#dd6b20", "declared_absent": "#718096"}

m = json.loads(ART.read_text())
md = (RUN / "report_9840.md").read_text()
lines = md.split("\n")
line_start = []
pos = 0
for ln in lines:
    line_start.append(pos)
    pos += len(ln) + 1

fig = plt.figure(figsize=(13, 8.2))
gs = fig.add_gridspec(2, 2, width_ratios=[2.25, 1], height_ratios=[1, 1], hspace=0.32, wspace=0.22)
ax = fig.add_subplot(gs[:, 0])
axr = fig.add_subplot(gs[0, 1])
axc = fig.add_subplot(gs[1, 1])

assets = m["assets"]
for i, a in enumerate(assets):
    loc = a["locator"]
    y = len(assets) - i
    if loc["method"] == "document":
        ax.barh(y, loc["end_char"], left=0, height=0.72,
                color=COLORS[a["resolution"]], alpha=0.22, edgecolor="k", linewidth=0.4)
    else:
        ax.barh(y, loc["end_char"] - loc["start_char"], left=loc["start_char"], height=0.72,
                color=COLORS[a["resolution"]], alpha=0.9, edgecolor="k", linewidth=0.4)
    ax.text(-120, y, a["asset_id"], ha="right", va="center", fontsize=6.5)

# section boundaries from the source document itself
for ln_i, ln in enumerate(lines):
    if ln.startswith("## "):
        ax.axvline(line_start[ln_i], color="0.6", lw=0.6, ls=":")
        tag = re.match(r"##\s*(\d+)\.", ln)
        label = ("S" + tag.group(1)) if tag else "repro"
        ax.text(line_start[ln_i] + 40, len(assets) + 1.6, label, rotation=0, fontsize=7, color="0.35")
ax.set_xlim(0, len(md))
ax.set_ylim(0, len(assets) + 2.4)
ax.set_yticks([])
ax.set_xlabel("character offset in tensor://reports/9840 markdown (total %d chars)" % m["source"]["chars"])
ax.set_title("wp-9840-01 asset locator map — 33 registered spans over the source document\n"
             "(quote bytes sliced at build time; every span re-sliced and uniqueness-rechecked by the gate)",
             fontsize=10, loc="left")
ax.legend(handles=[Patch(facecolor=c, edgecolor="k", label=k) for k, c in COLORS.items()],
          loc="lower right", fontsize=7.5, framealpha=0.95)

res = m["counts"]["by_resolution"]
keys = list(COLORS)
vals = [res.get(k, 0) for k in keys]
axr.barh(range(len(keys)), vals, color=[COLORS[k] for k in keys], edgecolor="k", linewidth=0.4)
for i, v in enumerate(vals):
    axr.text(v + 0.3, i, str(v), va="center", fontsize=8)
axr.set_yticks(range(len(keys)))
axr.set_yticklabels(keys, fontsize=7.5)
axr.invert_yaxis()
axr.set_xlabel("assets", fontsize=8)
axr.set_title("resolution status (%d assets)" % m["counts"]["assets"], fontsize=9, loc="left")

cls = sorted(m["counts"]["by_class"].items(), key=lambda kv: (-kv[1], kv[0]))
names = [k for k, _ in cls]
counts = [v for _, v in cls]
axc.barh(range(len(names)), counts, color="#4a5568", edgecolor="k", linewidth=0.4)
for i, v in enumerate(counts):
    axc.text(v + 0.1, i, str(v), va="center", fontsize=7)
axc.set_yticks(range(len(names)))
axc.set_yticklabels(names, fontsize=5.6)
axc.invert_yaxis()
axc.set_xlabel("assets", fontsize=8)
axc.set_title("asset classes (tables=%d)" % m["counts"]["by_class"].get("table", 0), fontsize=9, loc="left")

fig.suptitle("KF wp-9840-01 · report 9840 asset registration (sha256 %s…, %d chars)"
             % (m["source"]["hash"][:12], m["source"]["chars"]), fontsize=11, x=0.01, ha="left")
DOC_DIR.mkdir(parents=True, exist_ok=True)
out = DOC_DIR / "fig_asset_locator_map.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
fig.savefig(RUN / "fig_asset_locator_map.png", dpi=150, bbox_inches="tight")
print("figure:", out, out.stat().st_size, "bytes")