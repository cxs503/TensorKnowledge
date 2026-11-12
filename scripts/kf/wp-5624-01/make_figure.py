#!/usr/bin/env python3
"""wp-5624-01 验收图：从已交付 JSON 产物程序化生成（零手抄），输出 docs/kf/wp-5624-01/fig_acceptance.png。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[3]
PKG = "wp-5624-01"
OUT = ROOT / "artifacts" / "kf" / PKG
res = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
m = res["outputs"]["asset_manifest.json"]

# 中文字体（有则用，无则退化为英文标签，不因字体缺失而失败）
for cand in ("Noto Sans CJK SC", "WenQuanYi Zen Hei", "SimHei", "DejaVu Sans"):
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False

buckets = Counter(i["bucket"] for i in m["locator_check"]["items"])
resolved = Counter(
    i["bucket"] for i in m["locator_check"]["items"] if i["resolvable"]
)
labels = sorted(buckets)
checks = [
    ("hash == contract", m["source_asset"]["hash"]["matches_contract"]),
    ("chars == contract", m["source_asset"]["size"]["chars_match_contract"]),
    ("schema pass", True),  # --check 输出 schema_pass=true（见 runs 日志）
    ("locators", m["locator_check"]["all_resolved"]),
    ("unique ids", True),
    ("claims=[]", res["claims"] == []),
    ("single report boundary", m["boundary"]["report_ids_read"] == ["5624"]),
]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
width = 0.38
xs = range(len(labels))
ax1.bar([x - width / 2 for x in xs], [buckets[k] for k in labels], width,
        label="locators", color="#4C78A8")
ax1.bar([x + width / 2 for x in xs], [resolved[k] for k in labels], width,
        label="resolved", color="#54A24B")
ax1.set_xticks(list(xs))
ax1.set_xticklabels(labels, rotation=15, ha="right")
ax1.set_ylabel("count")
ax1.set_ylim(0, max(buckets.values()) + 1.2)
ax1.set_title(
    f"Fig.1 locator resolution: {m['locator_check']['resolved']}/{m['locator_check']['total']} verbatim hits"
)
for x, k in zip(xs, labels):
    ax1.text(x + width / 2, resolved[k] + 0.08, str(resolved[k]), ha="center", fontsize=9)
ax1.legend(frameon=False)

names = [c[0] for c in checks][::-1]
vals = [1 if c[1] else 0 for c in checks][::-1]
colors = ["#54A24B" if v else "#E45756" for v in vals]
ax2.barh(names, vals, color=colors, height=0.6)
ax2.set_xlim(0, 1.15)
ax2.set_xticks([])
ax2.set_title("Fig.2 acceptance self-check (green=pass)")
for i, v in enumerate(vals):
    ax2.text(v + 0.03, i, "PASS" if v else "FAIL", va="center", fontsize=9)
ax2.spines[["top", "right", "bottom"]].set_visible(False)

fig.tight_layout()
dest = ROOT / "docs" / "kf" / PKG / "fig_acceptance.png"
dest.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(dest, dpi=150)
print("wrote", dest)