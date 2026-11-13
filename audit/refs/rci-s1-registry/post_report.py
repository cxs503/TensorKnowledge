#!/usr/bin/env python3
"""Post the RCI-S1 progress report to the platform report API (figures inlined)."""
import base64
import json
import os
import subprocess

ROOT = "/root/tp-agent/work/m15810"
OUT = f"{ROOT}/runs/rci-s1-registry/out"
S = json.load(open(f"{OUT}/summary.json", encoding="utf-8"))
X = json.load(open(f"{OUT}/db_extras.json", encoding="utf-8"))
V = json.load(open(f"{OUT}/sensitivity.json", encoding="utf-8"))
M = json.load(open(f"{OUT}/inputs_manifest.json", encoding="utf-8"))
md = open(f"{ROOT}/docs/rci-s1-registry.md", encoding="utf-8").read()

figs = []
caps = {
    "fig1_typing_clean.png": "图1 四类分型与 KBM-CLEAN-W1 清洗判决分布（9446 篇快照）",
    "fig2_real_exec.png": "图2 真实执行标记与报告/任务 result 数字重合率分布",
    "fig3_duplicates.png": "图3 重复簇规模分布与 Jaccard 门限敏感性（0.4/0.5/0.7/LSH-only）",
    "fig4_traceability_length.png": "图4 工件三件套漏斗与正文长度分位",
}
for fn, cap in caps.items():
    p = f"{ROOT}/runs/rci-s1-registry/figures/{fn}"
    figs.append({"name": fn, "caption": cap,
                 "png_base64": base64.b64encode(open(p, "rb").read()).decode()})

summary = (
    f"RCI 阶段1 资产账落地：钉快照 T_pin={M['t_pin']} 得 {S['rows']} 篇 published 报告（与任务书 9446 逐字相等，"
    f"SQL 复算 {M['pinned_published_reports']}），落库 rci_asset_registry {X['snapshot_rows']} 行，"
    f"DB↔工件 17 聚合全等。四类分型 {json.dumps(S['by_type'], ensure_ascii=False)}；"
    f"重复簇 {S['dup_clusters']} 个覆盖 {S['dup_reports_in_clusters']} 篇（冗余 {S['dup_excess_reports']} 篇）；"
    f"空洞/失败账 {S['failed_empty']} 篇；真实执行 verified={S['by_real_exec']['verified']} / partial={S['by_real_exec']['partial']}"
    f"（数字重合率 mean={X['overlap_stats']['mean']}）；任务链 {S['with_mission']}/{S['rows']} 有 mission、"
    f"悬空 {X['reports_mission_missing_row']} 行。敏感性：gate 0.4→0.7 簇数 764→758（对阈值不敏感）。"
)

body = {
    "title": f"KBM-RCI-S1-REGISTRY｜9446 篇报告资产账（快照 {S['snapshot_id']}）",
    "summary": summary,
    "scenario_key": "knowledge-governance/rci/asset-registry",
    "mission_id": 15810,
    "tags": ["TensorKnowledge", "RCI", "KBM-RCI-S1-REGISTRY", "asset-registry", "dedup",
             "minhash", "lsh", "honest-report"],
    "markdown": md,
    "figures": figs,
}
json.dump(body, open("/tmp/report.json", "w", encoding="utf-8"), ensure_ascii=False)
print("report.json", len(json.dumps(body)), "bytes; figures:", [f["name"] for f in figs])
print("lt3pct: 判据为计数一致性（0 误差，见 §④）；无物理量基准，已在报告内声明原因")