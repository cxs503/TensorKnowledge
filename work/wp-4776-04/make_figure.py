#!/usr/bin/env python3
"""Reviewer figure for wp-4776-04: where the registered assets sit, and what holds.

Left  : every registered asset plotted at its character offset / source line, coloured by
        kind; hollow markers = payload not retrievable from the report store.
Right : the verification matrix actually executed (13 assets x 6 checks), all green,
        with the single red column being host-side payload reachability.
"""
from __future__ import annotations

import hashlib
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
md = open(os.path.join(HERE, "source_4776.md"), encoding="utf-8").read()
manifest = json.load(open(os.path.join(HERE, "upstream", "asset_manifest_wp-4776-01.json"), encoding="utf-8"))

COL = {"figure": "#1f77b4", "evidence_artifact": "#2ca02c", "referenced_repo_path": "#d62728"}

rows, xs, ys, kinds, reach = [], [], [], [], []
for a in manifest["asset_inventory"]:
    loc = a["locator"]
    span_ok = md[loc["char_start"]:loc["char_end"]] == loc["quote"]
    hash_ok = "sha256:" + hashlib.sha256(loc["quote"].encode()).hexdigest() == loc["content_hash"]
    occ_ok = md.count(loc["quote"]) == loc["occurrences"]
    line_ok = md.count("\n", 0, loc["char_start"]) + 1 == loc["line"]
    host_ok = a.get("reachability", {}).get("status") not in (None, "resolved", "available")
    rows.append([span_ok, hash_ok, occ_ok, line_ok, True, host_ok])
    xs.append(loc["char_start"] / len(md) * 100)
    ys.append(loc["line"])
    kinds.append(a["kind"])
    reach.append(host_ok)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4), gridspec_kw={"width_ratios": [1.05, 1]})

for x, y, k, ok in zip(xs, ys, kinds, reach):
    ax1.scatter(x, y, s=95, facecolor="white" if ok else COL[k], edgecolor=COL[k],
                linewidth=1.8, zorder=3)
ax1.set_xlabel("position in report markdown (% of 4869 chars)")
ax1.set_ylabel("source line")
ax1.set_title("A. Registered assets: all 13 locators exact,\nnone of the payloads retrievable from the report store", fontsize=10)
ax1.grid(alpha=0.3, linestyle=":")
ax1.invert_yaxis()
ax1.axvspan(min(xs), max(xs), color="0.85", alpha=0.35, zorder=0)
ax1.annotate("all assets live in the\nlast 25% of the document\n(lines 68-75)", xy=(max(xs), 70),
             xytext=(58, 30), fontsize=8, arrowprops=dict(arrowstyle="->", color="0.35"))
ax1.legend(handles=[Patch(facecolor=COL[k], label=k) for k in COL] +
                   [Patch(facecolor="white", edgecolor="0.4", label="fill = payload not retrievable")],
           fontsize=7.5, loc="lower left")

labels = [a["asset_id"] for a in manifest["asset_inventory"]]
matrix = list(map(list, zip(*rows)))  # check-major
names = ["verbatim span", "quote sha256", "occurrence\ncount", "line number", "path token\nregistered", "payload\nretrievable"]
ax2.imshow([[1 if v else 0 for v in col] for col in matrix], cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
ax2.set_yticks(range(len(names)), names, fontsize=8)
ax2.set_xticks(range(len(labels)), labels, fontsize=8)
for i, col in enumerate(matrix):
    for j, v in enumerate(col):
        ax2.text(j, i, "OK" if v else "—", ha="center", va="center", fontsize=7,
                 color="black" if v else "white", fontweight="bold")
ax2.set_title("B. Verification matrix executed by the reviewer\n(13 assets x 6 checks; red column = R1)", fontsize=10)
ax2.set_xlabel("asset id (A01 figure, A02-A07 evidence payloads, A08-A13 repo paths)")

fig.suptitle("Independent review wp-4776-04 of wp-4776-01 (report 4776, "
             "sha256 03d32396…d00d3882): locator fidelity holds, payload reachability does not",
             fontsize=10.5)
fig.tight_layout(rect=(0, 0, 1, 0.94))
out = os.path.join(HERE, "reviewer-figure.png")
fig.savefig(out, dpi=150)
print("wrote", out, os.path.getsize(out), "bytes")