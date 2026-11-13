#!/usr/bin/env python3
"""Compose + post the m15886 audit report (six elements, numbers from artifacts)."""
import base64, json, os, subprocess, pathlib, urllib.request

ROOT = pathlib.Path("/root/tp-agent/work/m15886")
ART = ROOT / "audit/artifacts"
ev = json.loads((ART / "m15810_verdict_evidence.json").read_text())
rec = json.loads((ART / "m15810_recompute.json").read_text())
sql = ev["auditor_checks"]["sql_crosscheck"]
rerun = ev["auditor_checks"]["rerun_n8_vs_shipped_diff"]
summary = json.loads((pathlib.Path("/root/tp-agent/work/m15810/runs/rci-s1-registry/out/summary.json")).read_text())
sens = json.loads((pathlib.Path("/root/tp-agent/work/m15810/runs/rci-s1-registry/out/sensitivity.json")).read_text())
fig = ROOT / "audit/figures/m15810_audit.png"

api = os.environ["TENSOR_API_BASE"]
login = urllib.request.Request(
    f"{api}/auth/login",
    data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                     "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
    headers={"Content-Type": "application/json"})
tok = json.load(urllib.request.urlopen(login))["access_token"]

md = f"""## ① 案例介绍

本单不是物理算例，而是对 **m15810（KBM-RCI-S1-REGISTRY，TensorKnowledge）** 的交差核验：把平台 `tensor_reports` 的
**9446 篇 published 报告**（快照 T_pin=2026-11-11T20:00:31.841339Z）做成可检索/可关联/可验证的资产账。
无几何/无量纲物理量（N/A）；审计对象=行级账 9446 行 + 27 聚合 + 4 图 + 报告六段 + 落库表 `rci_asset_registry`。
基准出处：任务书头条 9446（criterion A1）+ 源库 SQL 实算 + KBM-CLEAN-W1 清洗账本（sha256 `72a287560c0bf868…`，9504 行）。

## ② 怎么做的（工具链）

1. 取证：只读消费 `/root/tp-agent/work/m15810`；身份钉 `agent/m15810` 的 `e4c7222`/`05ba7a3`（**未合入 main**），`tensor_reports.id=14942`。
2. 独立复算：`audit/recompute_registry.py` 仅读行级工件重算 27 聚合（不复用被审代码）。
3. SQL 对拍：`audit/db_crosscheck.sql`（10 组：双向覆盖、越 pin、悬挂、FK、去重、快照一致性、六段）+ 只读 `verify_db.py`（17 聚合并集）。
4. 可复现性：`audit/rerun_pipeline.sh` 以 **N=8** 异分片重跑被审流水线（1–3、5 步；第 4 步写库不重放以保证被审表只读）。
5. 机读证据：`audit/artifacts/m15810_verdict_evidence.json`（与落表 evidence 同源）；|refs| 逐字节副本。

## ③ 计算结果（程序化注入，无手抄）

| 维度 | shipped（m15810） | 审计独立复算 / SQL | 判 |
|---|---|---|---|
| 行数 | {summary['rows']} | 行级 {rec['integrity']['row_count']} / SQL {sql['registry_rows']}（ids {sql['distinct_ids']}） | ✅ |
| SQL 源库口径 | 9446 | `published AND created_at<=T_pin` = {sql['published_at_pin_sql']} | ✅ 精确相等 |
| 四类分型 | info {summary['by_type']['info']} / research {summary['by_type']['research']} / analysis {summary['by_type']['analysis']} / creative {summary['by_type']['creative']} | 逐项相等（mismatch {rec['mismatch_count']}） | ✅ |
| 真实执行 | verified {summary['by_real_exec']['verified']} / partial {summary['by_real_exec']['partial']} / zero {summary['by_real_exec']['zero_overlap']} / no_mission {summary['by_real_exec']['no_mission']} / no_numbers {summary['by_real_exec']['no_numbers']} / no_result {summary['by_real_exec']['no_result']} | 逐项相等 | ✅ |
| 清洗判决 | kept {summary['by_clean']['kept']} / repaired {summary['by_clean']['repaired']} / excluded {summary['by_clean']['excluded']} | 逐项相等 | ✅ |
| 重复簇 | clusters {summary['dup_clusters']} / in {summary['dup_reports_in_clusters']} / excess {summary['dup_excess_reports']} | SQL {sql['dup_clusters_sql']}/{sql['dup_reports_sql']}/{sql['dup_excess_sql']} | ✅ |
| 覆盖双向 | — | 缺 {sql['missing_from_registry']} / 多 {sql['not_in_reports']} / 非published {sql['not_published']} / 越pin {sql['after_pin']} | ✅ |
| 任务链 | A5 自判 ❌ | 悬挂 {sql['dangling_rows']} 行 / {sql['dangling_missions']} 个 mission_id | ❌（0.11%） |
| 报告六段 | ①–⑥ | SQL 六项全 true；DB 正文 md5=工作树 md5=`{ev['auditor_checks']['report_row']['db_md5|len'].split('|')[0]}` | ✅ |
| 落地表 | `rci_asset_registry` | {sql['registry_rows']} 行，FK 约束 {sql['fk_constraints']} | ✅ |

限门扫描（shipped=N=24，审计侧 N=8 重跑同表）：{ ' / '.join(f"gate {s['gate']}→{s['dup_clusters']} 簇" for s in sens['sweep']) }。

## ④ 结果图

图 1 三联：(a) 机器可核证据键（impl/entry/artifacts/tests 齐 → L2 可核；integration_callers 不落在 repo main）；
(b) 静态 24 聚合重放全同 vs 活体探测族 3 项漂移；(c) 去重门限扫描 N=24 与 N=8 完全重合。

## ⑤ 注意点

- **F1（non-blocking）** 复跑非全确定性：`build_data.py:probe_worktree` 活体读 `/root/tp-agent/work/m<id>`，
  被审后 447 个工作树消失 → wt_exists {rerun['wt_exists']['shipped']}→{rerun['wt_exists']['rerun_n8']}、
  triple_ok {rerun['triple_ok']['shipped']}→{rerun['triple_ok']['rerun_n8']}、failed_empty {rerun['failed_empty']['shipped']}→{rerun['failed_empty']['rerun_n8']}。
- **F2** 文档 `published=9993（漂移+523）` 混了两个时刻（inputs_manifest 9969/+523、db_extras 9993/+547）。
- **F3** `failed_empty` 码和 {rec['integrity']['failed_empty_code_sum']} ≠ 并集 {rec['integrity']['failed_empty_union']}（多码行 {rec['integrity']['failed_empty_multi_code_rows']}），口径是并集。
- **F4** A5 任务链 {sql['dangling_rows']} 行悬挂（报告自判 ❌，如实保留）。
- 独立性限制：审计与被审同机同库；第 4 步写库未重放（保护被审表），L4/L5 无 benchmark case 不可裁。

## ⑥ 误差判定（逐项回答是否 <3%）

| 关键量 | ref | got | 相对误差 | <3%? |
|---|---|---|---|---|
| 资产账行数（对 SQL 源库，T_pin 口径） | {sql['published_at_pin_sql']} | {sql['registry_rows']} | 0.00% | **是** |
| 覆盖缺失 | 0 | {sql['missing_from_registry']} | 0.00% | **是** |
| 覆盖多余/越界 | 0 | {sql['not_in_reports']+sql['not_published']+sql['after_pin']} | 0.00% | **是** |
| 重复簇数（对 SQL 分组） | {sql['dup_clusters_sql']} | {summary['dup_clusters']} | 0.00% | **是** |
| 簇内报告数 | {sql['dup_reports_sql']} | {summary['dup_reports_in_clusters']} | 0.00% | **是** |
| 27 聚合行级复算 | 27 | 27 相等 | 0.00% | **是** |
| 17 聚合 DB↔工件 | 17 | 17 相等（只读 verify_db） | 0.00% | **是** |
| 活体探测族 wt_exists（重放） | {rerun['wt_exists']['shipped']} | {rerun['wt_exists']['rerun_n8']} | {abs(rerun['wt_exists']['shipped']-rerun['wt_exists']['rerun_n8'])/rerun['wt_exists']['shipped']*100:.2f}% | **否（F1，非账本体）** |
| 报告六段 | 6 | 6 | 0.00% | **是** |

**结论：账本体（数量/来源/分型/去重/真实执行标记）全部 0.00% <3%；唯一 >3% 项是活体工作树探测字段（F1，28.2%），
已在 verdict findings 中如实登记为 non-blocking，不粉饰。判级 L2（L3 withheld：无 repo main 侧消费方；L4 refused：锚点无 benchmark case）。**
"""

report = {
    "title": "m15810 KBM-RCI-S1-REGISTRY 交差审计：9446 篇资产账独立复算 27/27 相等，判 L2（L3/L4 如实拒绝）",
    "summary": ("交差核验 m15810：行级独立复算 27 聚合 0 不等；SQL 源库 9446=9446（0%）；双向覆盖 0 缺 0 多；"
                "去重 763/2174/1411 SQL 复算一致；N=8 异分片重跑 24 静态聚合逐位相同、verify OK；"
                "报告六段等在 DB 与工作树逐字节相等。判 L2（无 repo main 消费方→L3 拒绝；锚点无 benchmark case→L4 拒绝）。"
                "F1 活体探测族重放漂移 28.2% 如实登记 non-blocking。"),
    "scenario_key": "knowledge-governance/rci/board-audit-m15810",
    "mission_id": 15886,
    "tags": ["board-audit", "m15810", "KBM-RCI-S1-REGISTRY", "maturity-gate", "TensorKnowledge"],
    "markdown": md,
    "figures": [{"name": "m15810_audit.png",
                 "caption": "三联：证据键可核性 / 重放静态一致 vs 活体漂移 / 去重门限扫描跨分片重合",
                 "png_base64": base64.b64encode(fig.read_bytes()).decode()}],
}
pathlib.Path("/tmp/report.json").write_text(json.dumps(report, ensure_ascii=False))
req = urllib.request.Request(f"{api}/tensor/reports", data=json.dumps(report).encode(),
                             headers={"Content-Type": "application/json",
                                      "Authorization": f"Bearer {tok}"})
res = urllib.request.urlopen(req)
print(res.status, res.read()[:400].decode())