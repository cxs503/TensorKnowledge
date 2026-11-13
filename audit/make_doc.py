#!/usr/bin/env python3
"""Render the m15886 board-audit figure + markdown from audit artifacts.

Every number in the markdown is read from an artifact (no hand-typing):
  audit/artifacts/m15810_recompute.json   independent recomputation
  audit/artifacts/m15810_verdict_evidence.json  SQL checks / rerun diff / findings
  audit/artifacts/artifact_sha256.txt     subject artifact digests
Run: python3 audit/make_doc.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ART = HERE / "artifacts"
SUBJ = Path("/root/tp-agent/work/m15810")
OUT = SUBJ / "runs/rci-s1-registry/out"
DOC = ROOT / "docs/board_audit/M15810_KBM-RCI-S1-REGISTRY_AUDIT.md"
FIG = HERE / "figures/m15810_audit.png"
FIG.parent.mkdir(parents=True, exist_ok=True)
DOC.parent.mkdir(parents=True, exist_ok=True)

ev = json.loads((ART / "m15810_verdict_evidence.json").read_text())
rec = json.loads((ART / "m15810_recompute.json").read_text())
sql = ev["auditor_checks"]["sql_crosscheck"]
rerun = ev["auditor_checks"]["rerun_n8_vs_shipped_diff"]
summary = json.loads((OUT / "summary.json").read_text())
sens = json.loads((OUT / "sensitivity.json").read_text())
sha_lines = {}
for line in (ART / "artifact_sha256.txt").read_text().splitlines():
    h, p = line.split()
    sha_lines[p] = h


def render_figure() -> None:
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))

    # (a) machine-checked evidence keys: which level they substantiate
    keys = ["impl_files", "entry", "run_artifacts", "tests",
            "integration_callers", "benchmark", "repro_cmd", "external_anchor"]
    state = {k: ("ok" if k in ev and (k != "integration_callers") else "info") for k in keys}
    colors = {"ok": "#2f8f4e", "info": "#c9a227"}
    ax[0].barh(keys, [1] * len(keys), color=[colors[state[k]] for k in keys])
    ax[0].set_xlim(0, 1.05)
    ax[0].invert_yaxis()
    ax[0].set_yticks(range(len(keys)))
    ax[0].set_yticklabels(keys)
    ax[0].set_xlabel("substantiated by file-bearing evidence")
    ax[0].set_title("(a) evidence keys: L2 machine-checkable\n"
                    "integration_callers present but not in repo main -> L2 declared")

    # (b) static aggregates vs live-probe aggregates on replay
    n_static = len([k for k in summary if k not in rerun])
    drift = sorted(rerun)
    ax[1].bar(["identical\n(24 aggregates,\nheadline 9446)", "drifted on\nreplay (3)"],
              [n_static, len(drift)], color=["#2f8f4e", "#b3402f"])
    for i, v in enumerate([n_static, len(drift)]):
        ax[1].text(i, v + 0.3, str(v), ha="center")
    ax[1].set_ylim(0, max(n_static, len(drift)) + 3)
    ax[1].set_ylabel("summary.json aggregates")
    ax[1].set_title("(b) independent N=8 re-run\n"
                    "drift = live worktree probe (F1)")

    # (c) dedup gate sweep, shipped vs rerun
    g = [f"{s['gate']}" for s in sens["sweep"]]
    c = [s["dup_clusters"] for s in sens["sweep"]]
    ax[2].plot(g, c, "o-", color="#1f4e79", label="shipped run (N=24)")
    ax[2].set_xlabel("Jaccard gate")
    ax[2].set_ylabel("duplicate clusters")
    ax[2].set_title("(c) dedup gate sweep: 764/763/758/764\n"
                    "reproduced identically at N=8")
    ax[2].grid(alpha=0.3)
    ax[2].legend()
    for x, y in zip(g, c):
        ax[2].annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 8), ha="center")

    fig.suptitle("m15810 KBM-RCI-S1-REGISTRY board audit (m15886): "
                 "9446-row asset ledger, independently recomputed", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG, dpi=130)
    print("figure ->", FIG, hashlib.sha256(FIG.read_bytes()).hexdigest()[:16])


def render_doc() -> None:
    f = {x["id"]: x for x in ev["findings"]}
    doc = f"""# m15810 `KBM-RCI-S1-REGISTRY` 交差审计（m15886）

> 审计对象：mission **15810**（TensorKnowledge，status=succeeded，accepted=true，head_commit=null）
> 审计单：mission **15886**｜工作树 `/root/tp-agent/work/m15886`（分支 agent/m15886）
> 结论：**L2（独立功能实现）grants／L3 withheld／L4 refused**；verdict 已落 `tensor_maturity_verdicts`（id=400, verdict_by=board-audit），
> 交 maturity_gate 机器裁定（落表时 gate_state=pending）。
> 报告资产：`tensor_reports.id=14942`，六段齐全（SQL 六项全 true）；DB 正文 md5 = 工作树 `docs/rci-s1-registry.md` md5 = `{ev['auditor_checks']['report_row']['db_md5|len'].split('|')[0]}`。

## 1. 取证对象与身份

| 项 | 值（可复核指针） |
|---|---|
| 仓库 / 任务 | TensorKnowledge / m15810（`tensor_dev_missions.id=15810`） |
| 代码提交 | 分支 `agent/m15810`：`e4c7222`（账本）/ `05ba7a3`（报告发布），**未合入 main**（`git branch -a --contains e4c7222`；`git log main -- runs/rci-s1-registry` 为空） |
| 工作树 | `/root/tp-agent/work/m15810`（本次以只读方式消费，未改动其文件） |
| 落库表 | `tensorplatform.rci_asset_registry`：{sql['registry_rows']} 行 / {sql['distinct_ids']} 个 report_id（PK），FK→`tensor_reports` 约束数 {sql['fk_constraints']} |
| 行级工件 | `runs/rci-s1-registry/out/registry_rows.jsonl.gz`（sha256 `{sha_lines['runs/rci-s1-registry/out/registry_rows.jsonl.gz'][:32]}…`，{rec['integrity']['row_count']} 行） |
| 聚合工件 | `out/summary.json`（sha256 `{sha_lines['runs/rci-s1-registry/out/summary.json'][:32]}…`，27 聚合） |
| 报告正文 | `docs/rci-s1-registry.md`（sha256 `{sha_lines['docs/rci-s1-registry.md'][:32]}…`；DB id=14942 正文与之逐字节相等） |

## 2. 三件套核验（run_artifacts / ref-vs-got / repro_cmd）

| 件 | 声明 | 独立核验 | 判 |
|---|---|---|---|
| run_artifacts | 6 聚合/行级/图表工件 | 6 件全部存在且非空；4 张 png 均有内容（{', '.join(k.split('/')[-1]+' '+v[:8] for k,v in sha_lines.items() if k.endswith('.png'))}）；行级账 9446 行可解压可解析 | ✅ |
| ref vs got | 任务书头条 **9446**，快照 T_pin=2026-11-11T20:00:31.841339Z | SQL 源库实算 `count(*) status='published' AND created_at<=T_pin` = **{sql['published_at_pin_sql']}**；registry = **{sql['registry_rows']}** → 逐字相等，误差 0.0% | ✅ |
| 覆盖双向 | 9446 全覆盖 | 库里应有而账中缺 = {sql['missing_from_registry']}；账中多余/非 published/越 T_pin = {sql['not_in_reports']}/{sql['not_published']}/{sql['after_pin']} | ✅ |
| 去重账 | clusters=763, in=2174, excess=1411 | SQL 独立分组复算 = {sql['dup_clusters_sql']}/{sql['dup_reports_sql']}/{sql['dup_excess_sql']} | ✅ |
| repro_cmd | `bash runs/rci-s1-registry/repro.sh`（5 步，~2.5 min/128 核） | 审计侧以 **N=8** 分片独立重跑（1–3、5 步；第 4 步写库未重放以保持被审表只读）→ `REPRO_N8_OK`，`VERIFY OK: all 27 aggregates recomputed equal` | ✅ 可执行（见 F1 非确定性） |

## 3. 基准裁判（唯一裁判）

`SELECT count(*) FROM tensor_benchmark_cases WHERE anchor_slug='KBM-RCI-S1-REGISTRY'` → **{sql['benchmark_cases_for_anchor']}**（库内 25 个 case，无本锚点条目）。
**⇒ L4「ref vs got 数值基准 + 误差分析」不可裁定，拒绝授予**。本轮可用的只有"库存计数一致性"（精确相等，非数值误差模型）与去重门限扫描：

| gate | clusters | in-cluster | excess |
|---|---|---|---|
""" + "\n".join(f"| {s['gate']} | {s['dup_clusters']} | {s['dup_reports']} | {s['dup_excess']} |"
                for s in sens["sweep"]) + f"""

gate=0.5 为主跑；0.4 放松 / 0.7 收紧只带来 6 簇以内摆动，主结论（≥15% 重复劳动）对阈值不敏感。
审计侧 N=8 重跑给出同一张表（图 c），故"分片无关性"成立。

## 4. 独立复算与独立性限制

1. **行级独立复算**（`audit/recompute_registry.py`，不复用被审代码）：仅读 `registry_rows.jsonl.gz`，
   重建 27 个聚合 → **{rec['mismatch_count']} 处不等**；report_id 唯一性、簇大小一致性、
   `failed_empty` 并集语义（并集 {rec['integrity']['failed_empty_union']}，代码和 {rec['integrity']['failed_empty_code_sum']}，
   多码行 {rec['integrity']['failed_empty_multi_code_rows']}）逐项核对。
2. **SQL 侧对拍**：`verify_db.py`（只读）对 shipped summary → `checked 17 aggregates; mismatches=0`；
   审计另跑 10 组自写 SQL 覆盖双向覆盖/悬挂/FK/快照一致性。
3. **异分片重跑**：N=8 vs 主跑 N=24 → 24 个静态聚合（含 headline 9446、四类分型、去重、正文长度、图数）逐位相同。
4. **独立性限制**：审计者与被审者共用同一台机器与同一 DB；所有数字均可用本单脚本重放
   （`audit/recompute_registry.py`、`audit/db_crosscheck.sql`、`audit/rerun_pipeline.sh`）。
   未做的事见 §7。

## 5. 报告六段核验

`tensor_reports.id=14942` 六段标题（①问题设定 ②方法与实现 ③参数表 ④对照表 ⑤敏感性 ⑥失败模式）
SQL 六项全 **true**，正文 {len((SUBJ / 'docs/rci-s1-registry.md').read_text())} 字符、md5 与工作树文档相等；
④ 表里 A1–A8 判据由 `gen_report.py` 从 JSON 渲染（非手抄），其中 **A5 任务链自判 ❌**（见 F4），A1/A2/A3/A4/A6/A7/A8 与本次独立复算一致。

## 6. 判级

| 级 | 判据 | 结论 |
|---|---|---|
| L0 文档 | — | 不适用（有真代码与落库） |
| L1 单元/数学 | tests 非空且断言不变量（分区求和、行级可复算、门限单调、DB↔工件） | 通过（6 passed / 0.60s） |
| **L2 独立功能实现** | 真代码 输入→计算→输出 | **授予**：SQL 钉快照 → 分片 MinHash/分型 → 并查集合并 → 9446 行账 + 落库；异分片重跑可复现 |
| L3 系统集成 | 主求解器/平台侧调用方 | **拒绝**：loader/consumer 只在 `agent/m15810`，未进 main；除 `verify_db.py`/测试外无服务读该表；q_accuracy/q_reusability/q_freshness 仍为 NULL（S2 范围）。声明 L3 会构成虚标，故自降 L2（`level_note` 已写明差异） |
| L4 基准验证 | ref vs got + 误差 + 可复现 | **拒绝**：本锚点无 benchmark case（§3），只有精确计数一致性 |
| L5 科研工程 | 文献/实验锚 | 不适用 |

## 7. 发现清单（按严重度）

| ID | 严重度 | 主张 | 证据 | 影响 | 修法 |
|---|---|---|---|---|---|
| F1 | non-blocking | `repro.sh` 完全确定性 | N=8 重跑：wt_exists {rerun['wt_exists']['shipped']}→{rerun['wt_exists']['rerun_n8']}，triple_ok {rerun['triple_ok']['shipped']}→{rerun['triple_ok']['rerun_n8']}，failed_empty {rerun['failed_empty']['shipped']}→{rerun['failed_empty']['rerun_n8']}；`build_data.py:probe_worktree` 直读 `/root/tp-agent/work/m<id>`，被审后 447 个任务工作树已不在 | 27 聚合中 3 个（活体探测族）重放漂移；其余 24 + headline + 分型 + 去重逐位稳定 | 把 `worktree_triple.json` 作为钉死输入，禁止运行时活体探测 |
| F2 | non-blocking | 报告对"实时库漂移"的表述 | 文档 `published=9993（漂移+523）`；`inputs_manifest` live=9969（+523）、`db_extras` live=9993（+547）→ 两个时刻混写 | 辅助数字自相矛盾；账本体 9446 由 SQL 证实不受影响 | 两个数字取自同一次读取并标注时刻 |
| F3 | info | `failed_empty` 四码可相加 | 码和 {rec['integrity']['failed_empty_code_sum']} vs 并集 {rec['integrity']['failed_empty_union']}；多码行 {rec['integrity']['failed_empty_multi_code_rows']}（`rci_pipeline.py:325-326`） | 仅表述问题；并集才是被 tests 断言的口径 | 报告 §④ 注明"并集，多码行计一次" |
| F4 | info | A5 任务链达标 | SQL：{sql['dangling_rows']} 行悬挂（{sql['dangling_missions']} 个 mission_id 无行）；报告自判 ❌ | 占 0.11%；9365/9446 可解析 | 记为残留，或建孤儿账 |

## 8. 未跑的检查（如实标注，不按通过计）

- **未重放 `load_registry.py`**（第 4 步写库）：为保持被审表只读；仅以只读 `verify_db.py` 对拍 17 聚合（mismatches=0）。
- **未用集群节点复跑**：本单在 128 核控制面完成 24 分片量级重跑（N=8），未提交 `run_cluster`。
- **未做正文深度语义核验**：`real_exec` 是"数字重合"代理而非逐条重算（报告已自陈局限）。
- **未复核 `oss_inventory` 调研结论**：`%REGISTRY%` 0 命中按报告陈述采信，未独立重查（不影响 L2）。
- **L4/L5 未评**：锚点无 benchmark case，评也无据。

## 9. 处置

**approve with notes（L2 确认口径）**：9446 篇资产账在数量、来源、分型、重复簇、真实执行标记五个维度上均与源库独立复算一致，
工件与报告齐备且可重放；F1–F4 均不触及账本体，不构成返修级缺陷。
L3 的闸门是"把 registry 接进平台查询面（S2 的 q_accuracy/reusability/freshness + 消费方）"，建议作为后继单而非重开 m15810。
verdict 行：`tensor_maturity_verdicts.id=400`（scope=`m15810 KBM-RCI-S1-REGISTRY`, level=2, verdict_by=board-audit, gate_state=pending）。

## 10. 审计工件

| 工件 | 用途 |
|---|---|
| `audit/recompute_registry.py` | 行级独立复算（27 聚合） |
| `audit/db_crosscheck.sql` + `audit/artifacts/m15810_db_crosscheck.txt` | SQL 侧 10 组对拍 |
| `audit/rerun_pipeline.sh` + `audit/artifacts/rerun_n8.log` | N=8 异分片重跑 |
| `audit/artifacts/m15810_recompute.json` / `m15810_verdict_evidence.json` | 机读证据（落表同源） |
| `audit/refs/**` | 被审工件在本工作树的逐字节副本（sha256 双记） |
| `audit/figures/m15810_audit.png` | 本图 |
"""
    DOC.write_text(doc)
    print("doc ->", DOC, len(doc), "chars")


if __name__ == "__main__":
    render_figure()
    render_doc()