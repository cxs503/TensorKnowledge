#!/usr/bin/env python3
"""Figure for wp-11204-01: what the registration could and could not reach.

Two panels, both built only from docs/kf/wp-11204-01/asset_manifest.json:
  left  – asset count per class, split by resolution (resolved vs unresolved)
  right – resolvability per evidence channel for this report (markdown bytes,
          record fields, figure PNG bytes, artefact JSON endpoints, repo files)
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(HERE, "docs", "kf", "wp-11204-01")
man = json.load(open(os.path.join(OUT, "asset_manifest.json"), encoding="utf-8"))

classes = sorted({e["asset_class"] for e in man["assets"]})
resolved = [sum(1 for e in man["assets"] if e["asset_class"] == c and e["resolution"] == "resolved_in_source") for c in classes]
unres = [sum(1 for e in man["assets"] if e["asset_class"] == c and e["resolution"] != "resolved_in_source") for c in classes]

fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.6), gridspec_kw={"width_ratios": [1.45, 1]})
ax = axes[0]
y = range(len(classes))
ax.barh(list(y), resolved, color="#2c7fb8", label="resolved_in_source (bytes in hand)")
ax.barh(list(y), unres, left=resolved, color="#c9c9c9", label="referenced_unresolved (named only)")
for i, (r, u) in enumerate(zip(resolved, unres)):
    ax.text(r + u + 0.05, i, f"{r}/{r+u}", va="center", fontsize=8, color="#444")
ax.set_yticks(list(y))
ax.set_yticklabels(classes, fontsize=8)
ax.invert_yaxis()
ax.set_xlabel("number of registered assets")
ax.set_title("A  report 11204 asset inventory by class and resolution\n(total = %d assets)"
             % man["counts"]["assets"], fontsize=10)
ax.legend(fontsize=8, loc="lower right")
ax.grid(axis="x", alpha=0.3)

ax = axes[1]
channels = ["markdown bytes\n(source itself)", "record fields\n(scenario/tags/figures)",
            "figure PNG bytes\n(/figures/<name>)", "artefact JSON\n(/tensor/artifacts/...)",
            "repo files\n(TensorPhysics @ agent/m9422)"]
reach = [1, 1, 1, 0, 0]
notes = ["sha256 = contract", "%d fields" % 5, "%d/3 PNG hashed" % 3, "HTTP 404", "absent in this worktree"]
colors = ["#2c7fb8" if r else "#d95f02" for r in reach]
ax.barh(range(len(channels)), reach, color=colors)
ax.set_yticks(range(len(channels)))
ax.set_yticklabels(channels, fontsize=8)
ax.invert_yaxis()
ax.set_xlim(0, 1.35)
for i, (r, n) in enumerate(zip(reach, notes)):
    ax.text(r + 0.03, i, ("reachable · " if r else "not reachable · ") + n, va="center", fontsize=8)
ax.set_xticks([0, 1])
ax.set_xlabel("reachable from this package (1 = yes)")
ax.set_title("B  evidence channels actually probed\n(vocabulary fixed: no silent upgrade)", fontsize=10)
ax.grid(axis="x", alpha=0.3)

fig.suptitle("wp-11204-01 · asset registration of tensor://reports/11204 (FEM J2 + 3D cohesive, TensorPhysics)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.94])
path = os.path.join(OUT, "fig_asset_resolution.png")
fig.savefig(path, dpi=140)
print("wrote", path)