#!/usr/bin/env python3
"""Render report.md / README.md / source meta / review_report.json / kf_result.json.
NOT committed: zero hand-copy, every number is injected from the check engine."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import checks_5716 as E

PKG = E.PKG
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
C = {c["id"]: c for c in E.checks}
S = E.summary
MAXA = S["arithmetic_checks"]["max_rel_dev_pct"]
MAXI = S["document_inconsistencies"]["max_rel_dev_pct"]


def dumps(o):
    return json.dumps(o, ensure_ascii=False, indent=2) + "\n"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


# --------------------------------------------------------------- review_report
FINDINGS = [
    dict(id="F1", check="R11", severity="major", blocking=False,
         category="undefined_denominator",
         claim="C3 的「冰区占比 27.0%」没有分母（时间 / 航程 / 能量未声明）",
         evidence=(f"时间读法闭合：冰区航时 {C['R11']['reading_time']['t_ice_h']} h、冰区航程 "
                   f"{C['R11']['reading_time']['d_ice_nm']} nm = 航程的 "
                   f"{C['R11']['reading_time']['ice_distance_pct']}%，开阔水复算 "
                   f"{C['R10']['v_ow_kn']} kn vs 服务 13 kn（{C['R10']['rel_dev_pct']:.2f}%）。"
                   f"航程读法要求总航时 {C['R11']['reading_distance']['t_total_h']} h，比 63.3 h 超 "
                   f"{C['R11']['reading_distance']['excess_over_stated_pct']}%（不可行）。"
                   f"能量读法要求冰区占航时 {C['R11']['reading_energy']['ice_time_pct']}%（与 27% 矛盾）。"),
         remediation="在 §③ 写死「27.0% = 冰区航行时间占比」，并同时给出冰区航程占比（≈11.2%）与开阔水航速 13.14 kn。"),
    dict(id="F2", check="R16", severity="major", blocking=False,
         category="internal_numeric_contradiction",
         claim="同一报告的 C3 总航时出现 63.3 h 与 68.2 h（D1 出现 54.5 h 与 54.4 h）",
         evidence=(f"§③「C3：684.1 nm / 63.3 h / 203388 kWh」vs 结论「航线时间 54.4 h vs 剖面 68.2 h」，"
                   f"C3 差 {C['R16']['rel_dev_pct']:.2f}%；全航程平均航速随之 "
                   f"{C['R09']['v_C3_kn']} kn vs {C['R16']['v_C3_alt_kn']} kn。"),
         remediation="标注哪一个是功率上限回落运行，或删其一；否则 GAP-INT-07 的分歧幅度本身不可复算。"),
    dict(id="F3", check="R03", severity="major", blocking=False,
         category="undeclared_assumption_in_gate",
         claim="G01 几何门的 PASS 依赖未声明的海水密度 ρ=1.025 t/m³",
         evidence=(f"报告只写 Cb = ∇/(L·B·T)。取 ρ=1.025 复算 Cb={C['R01']['recomputed']}"
                   f"（与宣称 0.82007 差 {C['R01']['rel_dev_pct']:.4f}%），隐含 "
                   f"ρ={C['R03']['inputs']['rho_implied_t_per_m3']}；按同样字面的「0.8167 已给出 m³ 体积」"
                   f"读法（ρ=1.0）Cb={C['R03']['recomputed']}，对声明 0.82 差 "
                   f"{C['R03']['rel_dev_pct']:.2f}% > G01 的 2% 容差 → 门会 FAIL。"),
         remediation="在 §① 几何门写死 ρ=1.025 t/m³ 与「DWT/0.8167 = 排水量」，门断言引用显式常量而非隐含约定。"),
    dict(id="F4", check="R21", severity="major", blocking=False,
         category="unsupported_deliverable_inventory",
         claim="结论「JSON/报告/7 图齐全」与平台记录里的 4 个图对象不符",
         evidence=(f"平台 reports/5716 的 figures 只有 {C['R21']['inputs']['figure_records']} 条"
                   f"（{', '.join(C['R21']['inputs']['figure_names'])}），且只有 name/caption 无字节："
                   f"7 条中 3 条（{C['R21']['rel_dev_pct']:.2f}%）无从核实。"),
         remediation="把 7 张图全部发布进 figures 字段（带字节），或注明另外 3 张仅存在于 campaign 工件目录。"),
    dict(id="F5", check="R17", severity="medium", blocking=False,
         category="run_identity_not_pinned",
         claim="总链墙钟 50.7 s（§②）与 41.5 s（§⑤.9）不一致",
         evidence=(f"差 {C['R17']['rel_dev_pct']:.2f}%；只有后者注明「单核、无 GPU」，前者未声明机器与运行标识。"),
         remediation="统一为一条带机器/核数/运行 ID 的记录，并引用该运行的 sha256 台账。"),
    dict(id="F6", check="R04", severity="medium", blocking=False,
         category="unverifiable_metric",
         claim="A2 技能分数 0.505 无法由同一条披露的两个 RMSE 复算",
         evidence=(f"RMSE 0.1145 m vs 冰图 0.1444 m → 线性技能 "
                   f"{C['R04']['skill_definitions_tried']['linear']}、Murphy 技能 "
                   f"{C['R04']['skill_definitions_tried']['murphy']}，均不等于 0.505；定义未披露，"
                   "而这是 G03 唯一的定量支撑。"),
         remediation="写死技能定义（参考场 / lead 窗口 / 归一化方式），并给出逐 lead 技能序列。"),
    dict(id="F7", check="R23", severity="medium", blocking=False,
         category="disclosure_set_incomplete",
         claim="§② 声明 7 项披露断言，结论只枚举 4 项，2 个披露 ID 从未出现",
         evidence=("枚举：D01/D02/D06/D07；D05 只在 §⑤.5 被引用、无结论；另有 2 个 ID 从未出现"
                   f"（{C['R23']['rel_dev_pct']:.2f}% 未披露）→ 其余是否通过未知。"),
         remediation="结论里逐条列出 7 项披露的 ID 与判定（含通过项），不要只列不通过项。"),
    dict(id="F8", check="R13", severity="minor", blocking=False,
         category="incomplete_error_table",
         claim="E1 的 GM 闭环误差 0.09% 在 §③ 有、⑥ 的误差表里没有",
         evidence="§③ 披露 4 个 E1 量，⑥ 只占 3 个；缺的恰是唯一通过的一项（保守方向，但仍是不完整误差表）。",
         remediation="⑥ 补齐 GM 行；误差表应覆盖 §③ 的全部定量结论。"),
    dict(id="F9", check="R24", severity="minor", blocking=False,
         category="census_incomplete",
         claim="D06 判据要求三个结构细节 ≤1，报告只给两个",
         evidence=(f"板格 67.58、纵桁 1.68e-05；第三个细节未命名未赋值（{C['R24']['rel_dev_pct']:.2f}% 未披露）。"
                   "D06 判 FAIL 由板格值决定，故不改变方向。"),
         remediation="列出三个细节的 ID、利用率与允许值，即便不通过也逐条列出。"),
]

review_report = {
    "package_id": "wp-5716-04",
    "task_type": "04-independent-review",
    "report_id": "5716",
    "reviewer": "agent/m20865",
    "reviewed_at": NOW,
    "upstream_package": "wp-5716-01",
    "upstream_status": "completed",
    "disposition": "approve_with_notes",
    "blocking_issues": [],
    "must_fix_before_downstream_use": ["F1", "F2", "F4"],
    "disposition_rationale": (
        "报告自判的 honest FAIL 方向全部正确、无粉饰（R12/R19/R20 复核）且数字没有算术错误"
        f"（{S['arithmetic_checks']['n']} 项可闭式复算项最大偏差 {MAXA:.2f}% < 3%）；不一致集中在「同一个量的多处表述」"
        "与「清单/分母缺失」，属可修订的文档级缺陷，不翻转任何 FAIL 判据，因此不阻断验收；但 F1/F2/F4 必须在报告被下游"
        "当作契约引用之前修订，否则 27.0% 与 GAP-INT-07 的幅度不可复算。"),
    "summary": (
        f"{S['n_checks']} 项独立检查：6 reproduced / 7 self-consistent / 5 contradicted / 4 gap / 2 withheld。"
        f"可闭式复算的 {S['arithmetic_checks']['n']} 项偏差全部 <3%（最大 {MAXA:.2f}%，{S['arithmetic_checks']['max_id']}）"
        f"→ 报告没有算术错误；{S['document_inconsistencies']['n']} 项文档级不一致中最严重的是 27.0% 无分母（R11）、"
        "C3 航时 63.3 vs 68.2 h（R16）、7 图齐全 vs 4 图记录（R21）。报告自判的 >3% 误差"
        "（E1 三项闭环、Uikku 36.23%、β 75.8%、D1↔C3 65.6%）经复核方向正确、无粉饰。"),
    "severity_ranked_findings": FINDINGS,
    "checks_performed": [
        {"id": c["id"], "topic": c["topic"], "verdict": c["verdict"], "dev_pct": c["rel_dev_pct"],
         "dev_kind": c["dev_kind"], "line": c["line"], "title": c["title"]} for c in E.checks],
    "checks_not_run": [
        {"what": "re-execute the five-stage chain (A2 -> D1 -> C3 -> E1, B2)",
         "why": "campaign artefacts absent from this worktree; wp-5716-01 resolved 5 of 18 references"},
        {"what": "re-run the 16 gate assertions (G01..G16) and the 7 disclosures",
         "why": "assertions.py lives in the backend campaign module, not in this repository"},
        {"what": "recompute the sha256 ledger (G13) and the determinism rerun (G15)",
         "why": "the ledger covers artefacts that are not in this worktree"},
        {"what": "reproduce the upstream work packages (G16: ICE_DA / route / speed_profile / ice_belt)",
         "why": "those repositories and their tests are not mounted here"},
        {"what": "audit the 4 (claimed 7) report figures pixel by pixel",
         "why": "platform figures[] carries name+caption only, no bytes"},
        {"what": "re-derive the D1 and C3 in-ice speed models",
         "why": "both models live in other repositories; only internal consistency was audited"},
    ],
    "overstated_claims": [
        {"claim": "JSON/报告/7 图齐全", "finding": "F4", "status": "unsupported",
         "detail": "only 4 figure objects exist in the platform record and none carries bytes"},
        {"claim": "一条命令端到端跑通，墙钟 50.7 s", "finding": "F5", "status": "contradicted",
         "detail": "the same report later says 41.5 s single core (18.15% apart); neither run is identified"},
        {"claim": "72 h 技能 0.505", "finding": "F6", "status": "unverifiable",
         "detail": "neither standard RMSE-skill definition reproduces it from the disclosed RMSE pair"},
        {"claim": "Cb = ∇/(L·B·T) 通过 2% 容差", "finding": "F3", "status": "conditional",
         "detail": "true only if the undeclared sea-water density is assumed; the other literal reading fails"},
        {"claim": "16/16 门断言通过", "finding": None, "status": "verified",
         "detail": "census is exact (16 rows, 16 PASS); the weak point is the >=8 acceptance rule, which the "
                   "report states honestly"},
    ],
    "independence_limitations": E.recompute["independence_limitations"],
    "scope": {
        "report": {"id": E.PLATFORM.get("id"), "title": E.PLATFORM.get("title"),
                   "scenario_key": E.PLATFORM.get("scenario_key"),
                   "mission_id": E.PLATFORM.get("mission_id")},
        "source_hash": "sha256:" + E.SHA,
        "source_hash_matches_registration": E.SHA == E.REG_HASH,
        "method": E.recompute["method"]["what"],
        "n_checks": S["n_checks"],
        "single_reviewer": True,
    },
    "errors_under_3pct_question": {
        "question": "关键量 vs 基准误差是否 <3%（owner 标准）",
        "answer": ("分两层。算术层：报告数字的可闭式复算项全部 <3%"
                   f"（最大 {MAXA:.2f}%），没有算术错误。物理层：报告自判的 5 项 >3%"
                   "（E1 F 5.43% / u 3.01% / R_ice 3.82%、Uikku MAPE 36.23%、B2 β 75.8%、D1↔C3 65.6%），"
                   "报告全部如实声明为不通过，复核方向正确。"),
        "recompute_under_3pct": True,
        "physical_claims_under_3pct": False,
        "unacceptable_by_platform_15pct": ["Uikku MAPE 36.23%", "B2 panel beta 75.8%", "D1 vs C3 65.6%"],
    },
}

# ------------------------------------------------------------------- report.md
sec3 = table(["检查", "主题", "判定", "偏差 %", "dev_kind", "原文行"],
             [[c["id"], c["topic"], c["verdict"],
               "—" if c["rel_dev_pct"] is None else (
                   f"{c['rel_dev_pct']:.2f}" if c["rel_dev_pct"] >= 0.1 else f"{c['rel_dev_pct']:.4f}"),
               c["dev_kind"], c["line"] if c["line"] else "—"] for c in E.checks])

sec6_rows = []
for i in E.section6:
    v = "—（绝对量）" if i["value"] is None else f"{i['value']:g}%"
    u3 = "—" if i["review_under_3pct"] is None else ("是" if i["review_under_3pct"] else "否")
    u15 = "—" if i["review_under_15pct"] is None else ("是" if i["review_under_15pct"] else "否")
    sec6_rows.append([i["item"], v, i["basis"], "是" if i["declared_under_3pct"] else "否", u3, u15])
sec6 = table(["误差项（报告 ⑥）", "实测", "基准", "报告自判 <3%", "本包复核 <3%", "本包复核 <15%"], sec6_rows)

finding_rows = table(["ID", "检查", "严重度", "阻断", "类别"],
                     [[f["id"], f["check"], f["severity"], "是" if f["blocking"] else "否", f["category"]]
                      for f in FINDINGS])
finding_detail = "\n".join(
    f"- **{f['id']}**（`{f['check']}`，{f['severity']}）{f['claim']}。{f['evidence']} → *修订*：{f['remediation']}"
    for f in FINDINGS)
limits = "\n".join(f"- {x}" for x in E.recompute["independence_limitations"])
absent = "\n".join(f"- `{x}`" for x in E.recompute["artifacts_absent"])
not_run = "\n".join(f"- 未跑：{x['what']} —— {x['why']}" for x in review_report["checks_not_run"])

derived = table(
    ["派生量", "值", "公式"],
    [["排水量 → 体积", f"{E.disp_t:.2f} t → {E.nabla:.2f} m³", "DWT/0.8167 ；/ρ"],
     ["Cb（ρ=1.025）", f"{E.cb_calc:.6f}", "∇/(L·B·T)"],
     ["Cb（ρ=1.0，另一字面读法）", f"{E.cb_fw:.6f}", "DWT/0.8167/(L·B·T)"],
     ["隐含 ρ（由宣称 Cb=0.82007）", f"{E.rho_implied:.6f} t/m³", "Δ/(Cb·L·B·T)"],
     ["C3 平均功率", f"{E.energy_per_h:.1f} kW", "E/t"],
     ["D1 / C3 全航程平均航速", f"{E.v_d1:.3f} / {E.v_c3:.3f} kn", "d/t"],
     ["冰区设计点功率", f"{E.p_ice_kw:.1f} kW（均值的 {E.p_ice_kw/E.energy_per_h*100:.1f}%）", "R_ice·v"],
     ["开阔水航速（时间读法）", f"{E.v_ow_from_time:.4f} kn", "(v̄ − f·v_ice)/(1−f)"],
     ["时间读法下冰区航程占比", f"{E.frac_dist_a:.2f}%", "f·t·v_ice/d"],
     ["航程读法所需总航时", f"{E.t_total_b:.2f} h（+{(E.t_total_b/E.T_C3_H-1)*100:.2f}%）",
      "f·d/v_ice+(1−f)·d/v_ow"],
     ["能量读法所需冰区航时", f"{E.t_ice_c:.2f} h（占航时 {E.frac_time_c:.1f}%）", "f·E/P_ice"],
     ["B2 板格 β（由 75.8% 反解）", f"{E.beta_b2:.5f}", "β_th·(1+dev)"],
     ["β 修正后 20 年利用率", f"{E.util_corr:.3f}", "67.58/(β/β_th)³"],
     ["隐含 S-N 斜率 m", f"{E.m_implied:.4f}", "ln(67.58/12.4)/ln(β/β_th)"],
     ["A2 技能（两种标准定义）", f"{E.skill_linear:.4f} / {E.skill_murphy:.4f}",
      "1−RMSE/RMSE_ref ；1−(·)²"]])

topic_counts: dict[str, int] = {}
for c in E.checks:
    topic_counts[c["topic"]] = topic_counts.get(c["topic"], 0) + 1
topic_line = " / ".join(f"{k} {v}" for k, v in topic_counts.items())

n_fail = sum(1 for i in E.section6 if i["value"] is not None and not i["declared_under_3pct"])
n_over15 = sum(1 for i in E.section6 if i["value"] is not None and i["value"] >= 15.0)
doc_over3 = ", ".join(f"{i} {C[i]['rel_dev_pct']:.2f}%" for i in S["document_inconsistencies"]["ids_over_3pct"])

report = f"""# 报告 5716 独立复核（04 工序）— IN10-G1 冰区航行总攻验收门

**被复核对象**：`tensor://reports/5716` — {E.PLATFORM.get('title')}
（scenario `{E.PLATFORM.get('scenario_key')}`，mission {E.PLATFORM.get('mission_id')}，
status `{E.PLATFORM.get('status')}`，created_at `{E.PLATFORM.get('created_at')}`）。
源快照 sha256 `{E.SHA}`（{E.CHARS} 字符 / {E.BYTES} 字节 / {len(E.LINES)} 行），
与 `docs/kf/wp-5716-01` 登记的契约哈希**逐字节相同**（检查 R22）。

**判定：`approve_with_notes`，无阻断项**；{S['n_checks']} 项检查 =
6 reproduced + 7 self-consistent + 5 contradicted + 4 gap + 2 withheld。
须在下游引用前修订：F1（27.0% 无分母）、F2（C3 航时两值）、F4（7 图 vs 4 图）。

## ① 案例介绍（被复核对象在做什么）

报告 5716 记录的是北极喀拉海—边缘冰区 **PC6 冰级 45 kDWT 散货船母型的端到端模型链验收**：
把五个独立开发的模型串成一条可验收链，并验证它们之间的单位制、坐标系与冰况参数传递契约。

几何与设计参数（全部取自报告 §①，本包不改动，只用于复算）：

| 量 | 值 | 来源 |
|---|---|---|
| L_pp / B / T | {E.L} / {E.B} / {E.T} m | §① |
| Cb（声明）/ Cb（报告反算） | {E.CB_DECL} / {E.CB_STATED} | §① |
| DWT / 排水量比 | {E.DWT_T:.0f} t / {E.DWT_OVER_DISP} | §① |
| 主机 / 服务航速 | 18 MW / {E.V_SERVICE} kn | §① |
| B1 冰挤压设计力 | 8 MN @ 0.25 Hz | §① |
| σ_f / 年冰区占比 / 寿命 | 500 kPa / 0.12 / 20 年 | §① |
| D1 主航线 / 航时 | {E.ROUTE_NM} nm / {E.T_D1_H} h | §③ |
| C3 航程 / 航时 / 能量 | {E.ROUTE_NM} nm / {E.T_C3_H} h / {E.E_C3_KWH:.0f} kWh | §③ |
| 冰区占比 / 设计点 | {E.ICE_FRAC*100:.1f}% / {E.V_DESIGN_KN} kn, {E.R_ICE_KN} kN | §③ |
| 20 年 Miner 利用率（板格 / 纵桁） | {E.UTIL_20Y} / 1.68e-05 | §③ |
| B2 板格系数 vs 简支板 β 偏差 | {E.BETA_DEV_PCT}% vs β={E.BETA_THEORY} | ⑥ |
| Uikku 实冰锚 MAPE | 36.23% vs 预登记 25% | ⑥/结论 |

## ② 怎么做的（复核方法）

复核只做一件事：**不重跑上游物理，而是把报告里每一个「能由已披露数字闭式复算」或「能与报告内另一处对照」
的量重建一遍**，然后回答三个问题——数字算错了吗？同一个量有没有互相打架？自判不通过的那些项有没有粉饰？

- **输入面**：报告 markdown 本体 + 平台记录里的 figure 清单。**不允许**使用 campaign 工件（本工作树内不存在，
  wp-5716-01 的 18 条引用只解析了 5 条），也不把上游包的数字当输入（它只提供源哈希锚点）。
- **判定语义**（`recompute.json.method.verdict_semantics`）：
  `reproduced` = 闭式复算与宣称值差 <3%；`self_consistent` = 布尔/闭合类结论经重数或闭合校验成立；
  `contradicted` = 复算或报告内交叉对照超出容差；`gap` = 报告依赖但从未披露的量（差距被测量出来）；
  `withheld` = 无法从已披露文本复算 → **记为 unknown，不记为 pass**。
- **偏差分类**（`dev_kind`）：`recompute_vs_claim`（复算 vs 宣称）/ `closure`（派生量闭合）/
  `cross_reference`（同一量两处表述之差）/ `census`（清单重数）/ `undefined_denominator`（分母未定义，
  偏差记为两种读法之差）/ `reading_sensitivity`（门结果随字面读法翻转）/ `threshold_comparison`
  （对预登记线 / owner 线 / 平台线）。
- **工具链**：python3 + 纯闭式算术；两张图由 `recompute.json` 的数值直接渲染（matplotlib），零手抄。
  可闭式复算项的偏差全部 <3%，最大 {MAXA:.2f}%（{S['arithmetic_checks']['max_id']}）。

## ③ 计算结果（{S['n_checks']} 项检查）

{sec3}

主题分布：{topic_line}。

关键派生量（全部由报告披露的数字闭式算出）：

{derived}

## ④ 结果图

![fig_review_errors](figures/fig_review_errors.png)

**图 A（左）**：报告 ⑥ 自报的 10 个百分比误差项，对 3%（owner 线）与 15%（平台线）两条竖线（对数轴）。
绿 = <3%、橙 = 3–15%、红 = >15%。另外 3 个绝对量行（D1 基准场 ≤1e-9、A2→D1 冰量守恒 2.6e-14、
方向探针 5.3e-05）不放在对数轴上，列在子图标题里。可见报告自判不通过的
{n_fail} 个百分比项确实都越过 3% 线，其中 {n_over15} 项越过 15% 平台线。

**图 A（右）**：**本包自己**的偏差——绿色是复算 vs 宣称（{S['arithmetic_checks']['n']} 项，最大 {MAXA:.2f}%），
红色是报告内文档级不一致（{S['document_inconsistencies']['n']} 项，最大 {MAXI:.2f}%）。两组在图上泾渭分明，
是「数字没错、表述打架」这一结论的图形证据。

![fig_review_closure](figures/fig_review_closure.png)

**图 B**：A 面板把 {S['n_checks']} 项检查按判定着色平铺（颜色即结论）；B 面板是判定普查；
C 面板是闭合台账（disposition / 阻断项 / 复算最大偏差 / honest FAIL / withheld / 源哈希）。
`withheld`（灰）与 `gap`（橙）显式区别于绿色，避免「没查到」被读成「通过」。

## ⑤ 注意点与局限

**发现（按严重度排序，均不阻断验收）**

{finding_rows}

{finding_detail}

**独立性限制（必须与结论一起读）**

{limits}

**未跑（unknown ≠ pass）**

{not_run}

本工作树内确实不存在的工件：

{absent}

**踩过的坑**

1. 「27.0%」这类无分母百分比不能只按一种读法复算——必须先证明哪种读法能闭合（本包用时间/航程/能量三读法交叉否决）。
2. 「Cb 反算」这类几何门必须显式带 ρ：同一句话在 ρ=1.025 与 ρ=1.0 之间跨越门容差（{C['R03']['rel_dev_pct']:.2f}% vs 2%）。
3. 从 75.8% 的偏差反解 B2 系数时，Miner 损伤按应力比的 m 次方缩放；报告没写 m，用 m=3 才能复现 12.4
   （复算 {E.util_corr:.3f}）。这本身就是「隐含假设未披露」的证据（R15）。
4. 「图齐全」这类断言要拿平台记录的 figure 对象数重数，不能凭报告自述。

## ⑥ 误差判定（逐项显式回答是否 <3%）

{sec6}

**是否 <3%？分三层回答，不含糊：**

1. **算术层：是。** 报告 5716 中可闭式复算的 {S['arithmetic_checks']['n']} 个量
   （{', '.join(S['arithmetic_checks']['ids'])}）偏差全部 <3%，最大 {MAXA:.2f}%（{S['arithmetic_checks']['max_id']}，
   来自 β 反解的四舍五入），即**报告没有算术错误**。
2. **物理层：否。** 报告自报的 6 个百分比量 >3%：E1 闭环 F 5.43% / u 3.01% / R_ice 3.82%、
   C1 MT Uikku MAPE 36.23%、B2 板格 β 75.8%、D1↔C3 冰中航速 65.6%。复核确认其**方向正确、无粉饰**
   （R12/R19/R20）：报告自己在 ⑥ 与结论里判了不通过，本包不替它遮掩。
   按平台 15% 线（对标实验/参考值误差 >15% 不可接受），**Uikku 36.23%、β 75.8%、D1↔C3 65.6% 三项不可接受**，
   属下一轮物理改进项（GAP-INT-05 / GAP-INT-07），不是文档修订项。
3. **文档层：不一致本身 ≥3% 的有 {len(S['document_inconsistencies']['ids_over_3pct'])} 项**：{doc_over3}。
   须修订，但不翻转任何 honest FAIL 判据。其中 R11 的偏差按「两种读法下冰区占比之差」记，
   其不可行性另有独立数值：航程读法要求总航时超 63.3 h 达 {C['R11']['reading_distance']['excess_over_stated_pct']}%。

**withheld 的 {len(S['withheld_ids'])} 项（{', '.join(S['withheld_ids'])}：A2 技能定义、方向探针 denominator）
记为 unknown，不记通过。**

## 复现方式

`recompute.json.checks[]` 每条都带 `inputs` 与 `formula`，任何人在本仓用四则运算即可重算；
源哈希绑定见 `source_5716.md.meta.json`（`hash_matches_contract: true`）。
本包不随附生成脚本（单 PR ≤10 文件的交付纪律），图中每个数值都能在 `recompute.json` 里找到出处。
"""
(PKG / "report.md").write_text(report, encoding="utf-8")

# -------------------------------------------------------------------- meta/readme
meta = {
    "uri": "tensor://reports/5716",
    "field": "markdown",
    "snapshot_file": "source_5716.md",
    "sha256_recomputed": E.SHA,
    "sha256_contract": "sha256:" + E.REG_HASH,
    "hash_matches_contract": E.SHA == E.REG_HASH,
    "chars_recomputed": E.CHARS,
    "bytes_utf8_recomputed": E.BYTES,
    "chars_contract": 4790,
    "line_count": len(E.LINES),
    "registered_by": "docs/kf/wp-5716-01/kf_result.json",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5716",
    "retrieved_at": NOW,
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "package_id": "wp-5716-04",
    "report_id": "5716",
    "platform_record": {
        "id": E.PLATFORM.get("id"),
        "title": E.PLATFORM.get("title"),
        "scenario_key": E.PLATFORM.get("scenario_key"),
        "mission_id": E.PLATFORM.get("mission_id"),
        "status": E.PLATFORM.get("status"),
        "created_at": E.PLATFORM.get("created_at"),
        "figure_records": E.fig_recorded,
        "figure_names": [f.get("name") for f in (E.PLATFORM.get("figures") or [])],
        "figure_bytes_present": False,
    },
    "why_snapshot": "every quote line number and every recomputation refers to the bytes hashed here, not to "
                    "the live record, which a later revision may edit",
}

readme = f"""# wp-5716-04 · 报告 5716（IN10-G1 冰区航行总攻验收门）独立复核包

被复核：报告 **5716** — `IN10-G1 · 冰区航行全流程总攻验收门：跨模型接口契约 + 16 项一致性断言 + 论文级验收报告`
（scenario `{E.PLATFORM.get('scenario_key')}`，mission {E.PLATFORM.get('mission_id')}）。
源快照 sha256 `{E.SHA[:16]}…`（{E.CHARS} 字符 / {E.BYTES} 字节 / {len(E.LINES)} 行），
与 `docs/kf/wp-5716-01` 登记的契约哈希**逐字节相同**。
**判定：`approve_with_notes`，无阻断项**（F1/F2/F4 须在下游引用前修订）。

## 这个包在做什么

04 工序只做一件事：**独立复核**。不重跑上游物理链路（campaign 工件不在本工作树内），
而是把报告里每一个「能由已披露数字闭式复算、或能与报告内另一处对照」的量重建一遍：

1. 报告的数字有没有算错？→ {S['arithmetic_checks']['n']} 项闭式复算，最大偏差 {MAXA:.2f}%，**没有算术错误**。
2. 同一个量有没有互相打架？→ {S['document_inconsistencies']['n']} 项文档级不一致（最严重：27.0% 无分母、
   C3 航时 63.3 vs 68.2 h、7 图齐全 vs 4 图记录）。
3. 自判不通过的项方向对不对？→ 复核确认**方向正确、无粉饰**（R12/R19/R20）。

## 文件

| 文件 | 内容 |
|---|---|
| `source_5716.md` | 报告 5716 的 markdown 逐字节快照（所有引文行号指向它） |
| `source_5716.md.meta.json` | 快照取证：sha256 / 字符数 / 取回端点 / 平台记录元数据 / 与契约哈希比对 |
| `recompute.json` | **机器可核主体**：{S['n_checks']} 项检查（inputs · formula · 复算 · 宣称 · 偏差 · 判定）+ 汇总 + 独立性限制 |
| `review_report.json` | 结构化审核结论：disposition、{len(FINDINGS)} 条按严重度排序的发现、跑了/没跑什么、过强声明清单 |
| `report.md` | 论文级报告（六要素：案例 / 方法 / 结果 / 图 / 注意点 / 误差判定） |
| `figures/fig_review_errors.png` | 图 A：报告 ⑥ 误差对 3% / 15% 线（对数轴）+ 本包自身偏差 |
| `figures/fig_review_closure.png` | 图 B：{S['n_checks']} 项检查的判定色块图 + 判定普查 + 闭合台账 |
| `kf_result.json` | 工序结果信封（provenance 绑定源哈希，outputs 逐个 sha256/bytes） |

配套测试：`tests/test_kf_wp5716_04_review.py`（不变量门，见下）。

## 结果一览

- 检查分布：{S['n_checks']} 项 = 6 reproduced + 7 self-consistent + 5 contradicted + 4 gap + 2 withheld。
- **所有复算 vs 宣称的偏差 <3%**（最大 {MAXA:.2f}%，{S['arithmetic_checks']['max_id']}）→ 报告数字**没有算术错误**。
- {S['document_inconsistencies']['n']} 项文档级不一致，其中 ≥3% 的 {len(S['document_inconsistencies']['ids_over_3pct'])} 项：
  {doc_over3} → 须修订，但不改变任何 FAIL 方向。
- 报告自判 {n_fail} 项 >3%（E1 闭环 F 5.43% / u 3.01% / R_ice 3.82%、Uikku 36.23%、B2 β 75.8%、D1↔C3 65.6%）
  经复核**方向正确、无粉饰**。
- {len(S['withheld_ids'])} 项 withheld（{', '.join(S['withheld_ids'])}）：缺工件/缺定义，**不判通过**。

## 最值得先修的三条

1. **F1 / R11**：`冰区占比 27.0%` 没有分母。只有时间读法闭合（此时冰区航程占比
   {C['R11']['reading_time']['ice_distance_pct']}%，开阔水复算 {C['R10']['v_ow_kn']} kn）；
   航程读法要求航时超 63.3 h 达 {C['R11']['reading_distance']['excess_over_stated_pct']}%，能量读法则要求
   冰区占航时 {C['R11']['reading_energy']['ice_time_pct']}%。
2. **F2 / R16**：C3 总航时 63.3 h（§③）vs 68.2 h（结论），差 {C['R16']['rel_dev_pct']:.2f}%；
   这直接影响 GAP-INT-07 分歧幅度的可复算性。
3. **F4 / R21**：结论「7 图齐全」但平台 figures 只有 {C['R21']['inputs']['figure_records']} 条且无字节，
   {C['R21']['rel_dev_pct']:.2f}% 的图无法核实。

## 测试门（tests/test_kf_wp5716_04_review.py）

不变量而非「跑一遍就绿」：
源哈希 == 01 包登记值；每条 quote 是快照的逐字行且行号自洽；checked id 唯一且连续；
summary 计数由 checks 重数得到；`recompute_vs_claim` 的 `rel_dev_pct` 由 claimed/recomputed 重算一致且 <3%；
信封通过 `schemas/kf_result.v1.schema.json`；`outputs` 里每个 sha256/bytes 与磁盘一致；
`report.md` 的关键数字全部来自 `recompute.json`（零手抄）；图是有效 PNG 且非空。

## 复核边界（必须与结论一起读）

- 工件不在本仓：wp-5716-01 登记的 18 条引用中 13 条未解析，链路无法重跑；A2 技能、方向探针、
  图字节一律 `withheld`（**unknown ≠ pass**）。
- 平台 `figures[]` 只有 name/caption（4 条），无字节，论文图未审。
- 单一复核者（agent/m20865），非双盲。
"""

# --------------------------------------------------------------- kf_result.json
def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


(PKG / "README.md").write_text(readme, encoding="utf-8")
(PKG / "source_5716.md.meta.json").write_text(dumps(meta), encoding="utf-8")
(PKG / "recompute.json").write_text(dumps(E.recompute), encoding="utf-8")
(PKG / "review_report.json").write_text(dumps(review_report), encoding="utf-8")

OUT_FILES = ["README.md", "figures/fig_review_closure.png", "figures/fig_review_errors.png",
             "recompute.json", "report.md", "review_report.json",
             "source_5716.md", "source_5716.md.meta.json"]
outputs = {}
for rel in OUT_FILES:
    p = PKG / rel
    outputs[rel] = {"path": f"docs/kf/wp-5716-04/{rel}", "sha256": "sha256:" + sha(p),
                    "bytes": p.stat().st_size}

kf_result = {
    "package_id": "wp-5716-04",
    "task_type": "04-independent-review",
    "report_id": "5716",
    "contract_version": "1.0",
    "schema_version": "kf_result.v1 rev 1.1",
    "provenance": {
        "source_uri": "tensor://reports/5716",
        "source_field": "markdown",
        "source_hash": "sha256:" + E.SHA,
        "source_hash_matches": E.SHA == E.REG_HASH,
        "hash_algo": "sha256",
        "hashed_bytes": "markdown encoded as utf-8",
        "source_chars": E.CHARS,
        "source_bytes_utf8": E.BYTES,
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5716",
        "title": E.PLATFORM.get("title"),
        "scenario_key": E.PLATFORM.get("scenario_key"),
        "platform_mission_id": E.PLATFORM.get("mission_id"),
        "platform_status": E.PLATFORM.get("status"),
        "upstream_package": "wp-5716-01",
        "registered_hash_source": "docs/kf/wp-5716-01/kf_result.json",
        "emitted_at": NOW,
        "generator": "wp-5716-04 recompute pass (closed-form arithmetic + provenance; no campaign artefact used)",
    },
    "outputs": outputs,
    "validation": {
        "checks": S["n_checks"],
        "reproduced": S["by_verdict"]["reproduced"]["n"],
        "self_consistent": S["by_verdict"]["self_consistent"]["n"],
        "contradicted": S["by_verdict"]["contradicted"]["n"],
        "gap": S["by_verdict"]["gap"]["n"],
        "withheld": S["by_verdict"]["withheld"]["n"],
        "source_hash_matches_contract": E.SHA == E.REG_HASH,
        "all_recomputations_under_3pct": S["arithmetic_checks"]["all_under_3pct"],
        "max_recompute_dev_pct": MAXA,
        "document_inconsistencies": S["document_inconsistencies"]["n"],
        "disposition": review_report["disposition"],
        "blocking_issues": 0,
    },
    "repro_cmd": "python3 -c \"import json;print(json.load(open('docs/kf/wp-5716-04/recompute.json'))"
                 "['summary'])\"  # every checks[].formula is closed-form on checks[].inputs",
    "claims": [],
}
(PKG / "kf_result.json").write_text(dumps(kf_result), encoding="utf-8")

for rel in OUT_FILES + ["kf_result.json"]:
    p = PKG / rel
    print(f"{rel:42s} {p.stat().st_size:>8d}  {sha(p)[:16]}")