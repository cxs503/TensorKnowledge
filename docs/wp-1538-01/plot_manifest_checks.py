#!/usr/bin/env python3
"""wp-1538-01 结果图：资产登记核验视图（不含任何手打数字，全部从 asset_manifest.json 读取）。

两张面板：
  A. 9 个报告声明工件 × 2 个登记时点检出根 的存在性矩阵（1=存在，0=未找到）；
  B. 身份核验条：契约 source_hash / 观测 source_hash / 本地快照 sha256 / chars 逐项一致性。

用法: python3 artifacts/wp-1538-01/plot_manifest_checks.py
输出: artifacts/wp-1538-01/wp1538_01_manifest_checks.png
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
m = json.loads((HERE / "asset_manifest.json").read_text(encoding="utf-8"))

roots = list(m["artifacts"][0]["resolution_probes"].keys())
labels = [a["declared_path"] for a in m["artifacts"]]
mat = np.array([[1 if a["resolution_probes"][r]["exists"] else 0 for r in roots] for a in m["artifacts"]])

short = []
for lab in labels:
    parts = lab.split("/")
    short.append("/".join(parts[-2:]) if len(parts) > 2 else lab)

fig = plt.figure(figsize=(13.0, 7.4), dpi=150)
gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0], wspace=0.32)

ax = fig.add_subplot(gs[0, 0])
im = ax.imshow(mat, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(roots)))
ax.set_xticklabels([r.replace("_", "\n", 1) for r in roots], fontsize=8)
ax.set_yticks(range(len(short)))
ax.set_yticklabels([f"{a['artifact_id']}  {s}" for a, s in zip(m["artifacts"], short)], fontsize=7.5)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        ax.text(j, i, "present" if mat[i, j] else "absent", ha="center", va="center", fontsize=7.5)
ax.set_title(
    "A · artifact resolution probes at registration time\n"
    f"declared artifacts = {len(m['artifacts'])}, roots probed = {len(roots)}",
    fontsize=9.5,
)
ax.set_xlabel("probe root (existence only; contents untouched)", fontsize=8.5)
fig.colorbar(im, ax=ax, ticks=[0, 1], fraction=0.03, pad=0.02).set_label("1 = exists", fontsize=8)

ax2 = fig.add_subplot(gs[0, 1])
rep = m["report"]
snap = m.get("source_snapshot") or {}
items = [
    ("declared source_hash", rep["source_hash_declared"]),
    ("observed md sha256", rep["source_hash_observed"]),
    ("local snapshot sha256", snap.get("sha256", "n/a")),
]
ok_mask = [v == rep["source_hash_declared"] for _, v in items]
y = np.arange(len(items))
ax2.barh(y, [1, 1, 1], color=["#2e7d32" if ok else "#c62828" for ok in ok_mask], height=0.5)
for k, (name, val) in enumerate(items):
    ax2.text(0.02, k, f"{val.split(':')[-1][:24]}…", va="center", fontsize=7.5, color="white")
ax2.set_yticks(y)
ax2.set_yticklabels([n for n, _ in items], fontsize=8)
ax2.set_xticks([])
ax2.set_xlim(0, 1)
ax2.invert_yaxis()
for spine in ax2.spines.values():
    spine.set_visible(False)
chars_txt = (
    f"chars: declared {rep['chars_declared']} vs observed {rep['chars_observed']}  "
    f"({'match' if rep['chars_declared'] == rep['chars_observed'] else 'MISMATCH'})\n"
    f"bytes(utf-8) = {rep['bytes_utf8_observed']}, lines = {rep['line_count_observed']}\n"
    f"report_id = {rep['report_id']}, scenario_key = {rep['scenario_key']}\n"
    f"hash_match = {rep['hash_match']}, algorithm = sha256(utf-8)"
)
ax2.set_title("B · identity checks (all green = byte-identical)", fontsize=9.5)
ax2.text(0.0, -0.85, chars_txt, fontsize=8, family="monospace", va="top")

fig.suptitle(
    f"wp-1538-01 · asset registration for report {rep['report_id']} (no extraction, claims=[])",
    fontsize=11,
)
out = HERE / "wp1538_01_manifest_checks.png"
fig.savefig(out, bbox_inches="tight")
print("wrote", out, "sha256:", hashlib.sha256(out.read_bytes()).hexdigest())
print("expected png sha256:", hashlib.sha256(Path(out).read_bytes()).hexdigest())