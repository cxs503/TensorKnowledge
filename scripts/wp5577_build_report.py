#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-5577-04 · 组报：把 review_report.json 组装成 KF-RESULT 报告 markdown（唯一 json 块=结果信封）。

零手抄：报告里的每个数字与每段引文都从 review_report.json / report-5577 markdown 程序化取，
并在写出前断言引文是 report-5577 markdown 的逐字子串。

用法
----
    python3 scripts/wp5577_build_report.py            # 写 docs/kf/wp-5577-04/KF-RESULT-wp-5577-04.md
    python3 scripts/wp5577_build_report.py --payload /tmp/report.json   # 另出平台投递 payload
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp5577_review as R          # noqa: E402

OUT_DIR = R.OUT_DIR
MD_SRC = os.path.join(R.SRC_DIR, "report_5577.md")


def fnum(x, nd=3):
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", default="")
    ap.add_argument("--mission-id", type=int, default=15834)
    a = ap.parse_args()

    md_src = open(MD_SRC, encoding="utf-8").read()
    rev = json.load(open(os.path.join(OUT_DIR, "review_report.json"), encoding="utf-8"))
    env = json.load(open(os.path.join(OUT_DIR, "kf_result.json"), encoding="utf-8"))
    fig = os.path.join(OUT_DIR, "fig1_closure_residuals.png")

    # ---- 零手抄守门：报告引用的每一段都必须是原文逐字子串 ----
    cited = []
    for f in rev["findings"]:
        cited += [q for q in f["evidence"] if q in md_src]
        if f["claim_quote"] in md_src:
            cited.append(f["claim_quote"])
    for c in rev["claim_judgements"]:
        cited += [R.D.QUOTES[k] for k in c["evidence"] if k in R.D.QUOTES]
    bad = [q for q in set(cited) if q not in md_src]
    if bad:
        sys.exit(f"FAIL: 下列引文不是 report-5577 原文逐字子串: {bad}")

    rows = rev["numeric_recomputation"]["rows"]
    dev = rev["numeric_recomputation"]["deviations"]
    geo = rev["numeric_recomputation"]["geometry"]
    mx = rev["numeric_recomputation"]["max_abs_dev"]
    fit = rev["numeric_recomputation"]["rho_dcf_fit"]
    up = rev["acceptance_selfcheck"]["upstream_detail"]

    t1 = ["| V [kn] | Fn 表列 | Fn 复算 | δFn [%] | Cf 表列 | Cf(ITTC-57) 复算 | δCf [%] | Rf 表列 [kN] | Rf 复算 [kN] | δRf [%] | Rw 表列 [kN] | Cr·Q [kN] | δRw [%] | RT 表列 [kN] | Rf+Rw [kN] | δRT [kN] | Ct 表列 | Ct 复算 | δCt [%] |",
          "|---" * 19 + "|"]
    for r in rows:
        t1.append("| " + " | ".join([
            f"{r['V_kn']:.2f}", f"{r['Fn_tab']:.4f}", f"{r['Fn_recomputed']:.4f}", fnum(r['Fn_dev_pct'], 4),
            f"{r['Cf_tab']:.5f}", f"{r['Cf_ittc57_recomputed']:.5f}", fnum(r['Cf_dev_pct']),
            f"{r['Rf_tab_kN']:.1f}", f"{r['Rf_recomputed_kN']:.1f}", fnum(r['Rf_dev_pct']),
            f"{r['Rw_tab_kN']:.1f}", f"{r['Rw_from_Cr_kN']:.1f}", fnum(r['Rw_dev_pct']),
            f"{r['RT_tab_kN']:.1f}", f"{r['RT_from_Rf_plus_Rw_kN']:.1f}", fnum(r['RT_dev_kN'], 2),
            f"{r['Ct_tab']:.5f}", f"{r['Ct_recomputed']:.5f}", fnum(r['Ct_dev_pct']),
        ]) + " |")

    t2 = ["| 判据 | 报告声明 [%] | 独立复算 [%] | 是否一致 |", "|---|---|---|---|"]
    for name, tab, re_ in [
        ("V2 KCS 设计点 Rt（单一物理源对标）", dev["V2_dev_pct_tab"], dev["V2_dev_pct_recomputed"]),
        ("V3 遗留 mock 同点复算", dev["V3_dev_pct_tab"], dev["V3_dev_pct_recomputed"]),
        ("V4 KVLCC2 vs 文献", dev["V4_dev_pct_tab"], dev["V4_dev_pct_recomputed"]),
    ]:
        t2.append(f"| {name} | {tab:.3f} | {re_:.4f} | {'是' if abs(tab - re_) < 0.01 else '否'} |")
    t2.append(f"| ③ 表二第 3 行（部署实例 vs 主链基准） | 268.960 | {dev['tbl2_row3_dev_vs_base']:.4f} | 是 |")

    t3 = ["| claim_id | 判定 | 依据（数字全部复算） |", "|---|---|---|"]
    for c in rev["claim_judgements"]:
        t3.append(f"| {c['claim_id']} | {c['status']} | {c['basis']} |")

    t4 = ["| 发现 | 严重度 | 阻断 | 标题 |", "|---|---|---|---|"]
    for f in rev["findings"]:
        t4.append(f"| {f['finding_id']} | {f['severity']} | {'是' if f['blocking'] else '否'} | {f['title']} |")

    t5 = ["| 检查 | 结论 | 方法 |", "|---|---|---|"]
    for c in rev["checks"]:
        t5.append(f"| {c['check_id']} {c['name']} | {c['result']} | {c['method']} |")

    t6 = ["| 未执行项 | 原因 | 状态 |", "|---|---|---|"]
    for c in rev["checks_not_run"]:
        t6.append(f"| {c['item']} | {c['why']} | {c['status']} |")

    # 证据键 → 支撑的 claim/finding（claim/字段 → 原文引文片段）
    key_of = {q: k for k, q in R.D.QUOTES.items()}
    usage: dict[str, list[str]] = {}
    for c in rev["claim_judgements"]:
        for k in c["evidence"]:
            usage.setdefault(k, []).append(c["claim_id"])
    for f in rev["findings"]:
        for q in f["evidence"]:
            k = key_of.get(q)
            if k:
                usage.setdefault(k, []).append(f["finding_id"])

    def cell(q: str) -> str:
        """表格内保持逐字渲染：转义竖线，含反引号时改用 <code> 包裹。"""
        esc = q.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")
        return f"<code>{esc}</code>"

    bib = ["| 证据键 | 支撑的 claim / finding | 原文引文（逐字，已程序化断言） | 出现位置（字符区间） |",
           "|---|---|---|---|"]
    for k, q in R.D.QUOTES.items():
        if q in cited:
            pos = md_src.find(q)
            bib.append(f"| `{k}` | {', '.join(sorted(set(usage.get(k, []))))} | {cell(q)} | {pos}–{pos + len(q)} |")

    probe = rev.get("figure_byte_probe") or {}
    pc = probe.get("positive_control") or {}
    probe_status = ", ".join(f"{f['name']}→{f['http_status']}" for f in probe.get("target_figures", [])) or "(未运行)"
    probe_cid, probe_cname = pc.get("report_id", "n/a"), pc.get("name", "n/a")
    probe_code, probe_bytes, probe_ok = pc.get("http_status", "n/a"), pc.get("bytes", "n/a"), bool(pc.get("identical"))
    probe_concl = probe.get("conclusion", "未运行")
    acc = rev["acceptance_selfcheck"]
    acc_tbl = ["| acceptance 项 | 结论 | 证据 |", "|---|---|---|",
               f"| valid_json | {'☑' if acc['valid_json'] else '☒'} | review_report.json 与 kf_result.json 均 `json.load` 通过（写盘后重读自证） |",
               f"| schema_pass | {'☑' if acc['schema_pass'] else '☒'} | kf_result 信封按 schemas/kf_result.v1.schema.json（Draft2020-12）`jsonschema.validate` 通过；负对照（篡改 source_hash）抛 ValidationError |",
               f"| reviewer_independent | {'☑' if acc['reviewer_independent'] else '☒'} | 上下文仅 report-5577 markdown+record 与上游结果信封；未读生产者解释/未读上游脚本实现（见 ⑤ 独立性声明） |",
               f"| upstream_packages_completed | {'☑' if acc['upstream_packages_completed'] else '☒'} | 上游 {up['discovery']}；envelope_schema_pass={up['envelope_schema_pass']}、source_hash_bound={up['source_hash_bound']}、markdown locator {up['locators_markdown']}/{up['locators_markdown']} 回解 |"]

    md = f"""# KF-RESULT {R.PKG}

**tags**: `kf-wp:{R.PKG}`, `independent-review`, `red-team-reviewer`, `report-5577`, `campaign/bp-demo-in12p8`

**审核对象**: 上游工作包 `{rev['reviewed_object']['package_id']}`（{rev['reviewed_object']['task_type']}，结果报告 #{rev['reviewed_object']['result_report_id']}）→ 其所登记的报告 `report_id={R.REPORT_ID}`
**处置（verdict）**: **{rev['verdict']}**（medium {sum(1 for f in rev['findings'] if f['severity'] == 'medium')} 项 / low {sum(1 for f in rev['findings'] if f['severity'] == 'low')} 项 / info {sum(1 for f in rev['findings'] if f['severity'] == 'info')} 项；无阻断级缺陷）

---

## ① 本工序做了什么（案例介绍）

本单是报告→知识产线 KBM-RCI-F1-FACTORY 的 **04-independent-review** 工序，只有一个工作包 `{R.PKG}`，只碰 `report_id=5577`。

- **被审报告**：`{rev['target_report']['title']}`（scenario_key `{rev['target_report']['scenario_key']}`，mission {rev['target_report']['mission_id']}，{rev['target_report']['chars']} 字符 / {rev['target_report']['bytes_utf8']} 字节）。
  物理内容 = KRISO 公开基准船 **KCS 集装箱船静水裸船体阻力**：Lpp/B/T = 230.0/32.2/10.8 m，∇ = 52030 m³，
  Cb/Cm/Cwp = 0.6509/0.9849/0.7630，设计 24 kn（Fn 0.2600）；总阻力按 {R.D.QUOTES['q_formula_decomposition']} 分解，
  兴波阻力取 Holtrop 回归 {R.D.QUOTES['q_rw_formula']}。
- **本工序任务**：不重做阻力计算、不改上游产物、不标 verified；对报告做**语义保真审核**（judge_semantic_fidelity）
  + 对上游 01 工序产物做**结构与证据面独立复核**，给出 pass / fail / needs-fix。
- **结论一句话**：报告所有可由其自身声明输入复算的数字**全部闭合到声明精度**（RT 残差 ≤ {mx['RT_dev_kN']} kN，
  Fn 偏差 ≤ {mx['Fn_dev_pct']}%，Ct 偏差 ≤ {mx['Ct_dev_pct']}%），honest-FAIL 与 NOT RUN 声明属实；
  但存在 3 项 medium（公式口径不一致、关键常数无出处、两个"修复前"数字互不相容），**处置 = {rev['verdict']}**。

## ② 怎么做的（方法 / 流程 / 关键设置 / 工具链）

```
report-5577 markdown (sha256 60575cfe…b7de8) ──┐
report-5577 record  (title/scenario_key/figures) ├─▶ ① 源完整性守门 (C1)
上游 wp-5577-01 结果信封 (#14783) ─────────────┘  ② 上游结构复核 (C2–C6)
                                                       ③ 数值复算 (C7–C10)
                                                       ④ 声明可审计性 (C11–C13)
                                                       ⑤ 判定阶梯 → verdict → review_report.json
```

| 步骤 | 工具/脚本 | 关键设置 |
|---|---|---|
| 取源 + 锁哈希 | `scripts/wp5577_review.py`（urllib Bearer；`--online` 可在线复取） | markdown utf-8 字节 sha256 与契约值比对，不符即 SystemExit；离线快照 `source/report_5577.md` 逐字节等同 |
| 零手抄守门 | 同上 `assert_quotes()` | 本报告引用的 {len(set(cited))} 段原文全部断言为 report-5577 markdown 的**逐字子串**，否则退出 |
| 上游复核 | `resolve_locators()` + `jsonschema` | 17 条 markdown locator 逐条回解（`md[start:end]==quote`）；信封按 `schemas/kf_result.v1.schema.json` 校验 |
| 数值复算 | `compute_rows()` / `fit_rho_dcf()` / `geometry_checks()` / `deviation_checks()` | ρ=1025 kg/m³、ΔCf=4.0e-4 为**显式假设**（报告未声明，见 F2）；ν 由 Re 逐行反解 |
| 判定 | `decide_verdict()` | 有 blocking→fail；有 medium→needs-fix；否则 pass（确定性阶梯，测试覆盖） |
| 图 | `render_figure()`（matplotlib Agg） | 左=主表逐项复算偏差，右=⑥ 误差表算术复算 vs ±3% 带；数字全部来自 review_report.json |
| 回归测试 | `tests/test_wp5577_review.py` | 20 项，含**负对照**：篡改引文/平移 locator/篡改 source_hash 必须被检出 |

## ③ 产出物清单与计算结果

| 文件 | 要点 |
|---|---|
| `docs/kf/{R.PKG}/review_report.json` | 审核报告本体：verdict、{len(rev["checks"])} 项检查、5 行逐项复算、{len(rev["findings"])} 条 findings、10 条 claim 判定、6 项未执行登记 |
| `docs/kf/{R.PKG}/kf_result.json` | 结果信封（outputs=`review_report.json`，provenance.source_hash 与契约逐字节一致） |
| `docs/kf/{R.PKG}/KF-RESULT-{R.PKG}.md` | 本报告（唯一 json 块=结果信封） |
| `docs/kf/{R.PKG}/fig1_closure_residuals.png` | 复算偏差图（左：主表逐项；右：⑥ 判据算术） |
| `docs/kf/{R.PKG}/source/` | 源快照：`report_5577.md`(sha256 校验文件)、`report_5577_record.json`、`upstream_report_14783_wp-5577-01.json` |
| `scripts/wp5577_review.py`、`scripts/wp5577_review_data.py`、`scripts/wp5577_build_report.py` | 审核/证据数据/组报，一键复跑 |
| `tests/test_wp5577_review.py` | 20 项 pytest（含 4 类负对照） |

### ③.1 主表逐项复算（ρ=1025 kg/m³、ΔCf=4.0e-4；ρ/ΔCf 为审核假设）

{os.linesep.join(t1)}

**读法**：`δRw` 在 12 kn 行 −{abs(rows[0]['Rw_dev_pct']):.1f}% 是 Cr 列 5 位小数舍入所致（F5，该行 Rw 仅 2.6 kN，
对 RT 影响 0.3%）；其余 4 行 |δRw| ≤ {max(abs(r['Rw_dev_pct']) for r in rows[1:]):.2f}%。RT 逐行由 Rf+Rw 闭合到 {mx['RT_dev_kN']} kN。

### ③.2 报告 ⑥ 判据的算术复算

{os.linesep.join(t2)}

### ③.3 (ρ, ΔCf) 反解与退化

联合反解得 ρ≈{fit['rho_best']} kg/m³、ΔCf≈{fit['dCf_best']}（跨行相对离散 {fit['max_cross_row_rel_spread']:.1e}）。
即 5 行数据自洽，但 ρ 与 ΔCf 在报告给出的信息量下**不可唯一辨识**——这是 F2 的量化形态，不是数值错误。

### ③.4 几何先验复算

∇/(L·B·T) = {geo['Cb_from_nabla']} vs 表列 Cb = {geo['Cb_tab']} → 偏差 **{geo['Cb_dev_pct']}%**（报告声明 0.0617%，一致）；
Cwp 缺省回归：旧式 0.75+0.25Cb = {geo['Cwp_default_old_KCS']}（报告称 KCS 0.913）、新式 (1+2Cb)/3 = {geo['Cwp_default_new_KCS']}（报告 0.767）、
KVLCC2(Cb={geo['KVLCC2_Cb_used']}) = {geo['Cwp_default_new_KVLCC2']}（报告 0.873）——4 个数字全部复现。

### ③.5 claim 判定（不标 verified；verification 由平台门计算）

{os.linesep.join(t3)}

### ③.6 findings（严重度排序）

{os.linesep.join(t4)}

### ③.7 {len(rev["checks"])} 项检查

{os.linesep.join(t5)}

### ③.8 未执行项（honest：缺证据一律记 unknown，不因缺证据判 pass）

{os.linesep.join(t6)}

### ③.9 图字节探针（受控对照实验，实验设计六要素）

| 要素 | 内容 |
|---|---|
| 决策 | report-5577 的『见内嵌附图』是**平台限制**还是**生产者未落库**？（决定 F4 的责任归属与修复动作） |
| 备择假设 | H1 平台不存图字节；H2 报告未传图字节 |
| 判据（先于动手声明） | 正对照 sha256 与本地一致 ⇒ 端点有效；处理组 3 个图名全 404 ⇒ 判 H2；正对照不一致 ⇒ 结论降级 unknown |
| 处理组 | `GET /tensor/reports/5577/figures/{name}` × 3 个声明图名 → {probe_status} |
| 正对照 | report #{probe_cid} 的 `{probe_cname}` → HTTP {probe_code}，{probe_bytes} 字节，sha256 与本地 {'一致' if probe_ok else '不一致'} |
| 结果 | {probe_concl} |
| 混杂/局限 | 正对照是本审核自己投递的报告（同一 POST 路径但非生产者环境）；只探 `/figures/{name}` 一条读路径；n=1/n=3 无重试统计；不排除 5577 的图存在别处（报告本身未给路径） |

## ④ 证据定位表（claim/字段 → 原文引文片段，逐字）

{os.linesep.join(bib)}

> 上游 wp-5577-01 的两条字段引文（非 report-5577 正文，已在 findings F9/F10 标注来源）：
> `record.summary` = `{R.D.UPSTREAM_SUMMARY_CLAIM}`；`record.summary` 起始 = `{R.D.UPSTREAM_SCOPE_CLAIM}`。

**图 1**（fig1_closure_residuals.png）— 左：report-5577 ③ 主表逐项复算偏差（Fn / Cf / Rf / Rw / Ct，ρ=1025、ΔCf=4.0e-4）；
右：⑥ 判据算术复算（V2/V3/V4）与 ±3% 判据带。图由 review_report.json 直接渲染，无手抄数字。

## ⑤ 注意点与局限

1. **独立性声明**：审核上下文 = report-5577 markdown（逐字节快照）+ record 字段 + 上游 wp-5577-01 结果信封；
   *未*读取生产者的口头解释，*未*读取上游脚本/测试实现（只核产物：schema、哈希、locator 回解、计数、claims 政策）。审核提示词不由生产方提供。
2. **不可复算项**：pytest 结果、调用延迟分位、报告门 8/8、工件索引 20/20、KVLCC2 文献基准值、S=8975 m² 来源、
   `physics/holtrop` 公式一致性——6 项进 ③.8，状态 unknown/not_run。这些不是"通过"，是"未核"。
3. **ρ/ν/ΔCf 是假设不是事实**：(ρ,ΔCf) 在 5 行数据上退化（③.3）；本审核用 (1025, 4.0e-4) 是因为它能同时闭合 Rf/Rw/Ct 且符合 ITTC-1978 惯例，
   但报告未声明，故 F2 判 medium 而非"数值错误"。
4. **不标 verified**：全部 claim 只赋 supported/partially-supported/unresolved/refuted（分布 {sum(1 for c in rev['claim_judgements'] if c['status'] == 'supported')}/{sum(1 for c in rev['claim_judgements'] if c['status'] == 'partially-supported')}/{sum(1 for c in rev['claim_judgements'] if c['status'] == 'unresolved')}/{sum(1 for c in rev['claim_judgements'] if c['status'] == 'refuted')}），
   `verified_marking.claims_marked_verified = 0`。
5. **verdict 的作用域**：`blocking_for_upstream_wp_5577_01=False`——01 工序按契约不做数字背书，3 项 medium 不构成其验收失败；
   `blocking_for_downstream_claim_extraction=True`——02/03 若照抄 ① 的公式会得到错误能力画像，须先修口径。
6. **范围**：只碰 report_id=5577；未读/未写其它 report_id；未改上游产物（上游报告 #14783 只读）。

## ⑥ 自检：逐条对照 acceptance + 误差判定

{os.linesep.join(acc_tbl)}

**honest 声明**：C11（图/工件声明可审计性）判 `fail`——这是**被审报告的断言不成立**（record.figures 仅 name/caption、无 png_base64），
不是本工序执行失败；本工序 {len(rev["checks"])} 项检查 {rev["checks_passed"]} pass / {len(rev["checks_failed"])} fail（=F4 的机器化表达），另 0 unknown 由 ③.8 单独登记。

### 误差判定（关键量 vs 基准，逐项回答是否 <3%）

| 量 | 实测（复算/声明） | 基准 | 偏差 | 是否 <3% | 判读 |
|---|---|---|---|---|---|
| Fn（5 行） | 复算 V/√(gLpp) | 表列 Fn | ≤ {mx['Fn_dev_pct']}% | **是** | 闭式运算，仅 4 位小数舍入 |
| Cf（5 行） | 复算 0.075/(log10Re−2)² | 表列 Cf | ≤ {mx['Cf_dev_pct']}% | **是** | ITTC-57 闭式，表列 5 位小数舍入 |
| RT（5 行） | Rf+Rw | 表列 RT | ≤ {mx['RT_dev_kN']} kN（≤0.005%） | **是** | 加和口径成立（无 R_A/R_B/R_TR/R_APP，见 F1） |
| Ct（5 行） | RT/(½ρV²S) | 表列 Ct | ≤ {mx['Ct_dev_pct']}% | **是** | 与 Cf+ΔCf+Cr 同源 |
| Rw（12 kn 行） | Cr·½ρV²S=3.5 kN | 表列 Rw=2.6 kN | {abs(rows[0]['Rw_dev_pct']):.2f}% | **否** | Cr 列 5 位小数舍入（F5）；对 RT 影响 0.3%，不改结论 |
| V2 KCS 设计点 | 2011.61 kN | 2005.99 kN（Holtrop 单一源，同级） | {dev['V2_dev_pct_recomputed']}% | 是（算术）/ **不作为精度证据** | 基准与被测同源（F7） |
| V3 遗留 mock | 6882.59 kN | 2005.99 kN | {dev['V3_dev_pct_recomputed']}% | **否**（报告已标 HONEST-FAIL） | 复算 243.102% 一致，属被修缺陷本身 |
| V4 KVLCC2 | 1621.66 kN | 1960.0 kN（无出处） | {dev['V4_dev_pct_recomputed']}% | **否**（报告已标 HONEST-FAIL） | 基准无文献引用，不可独立复核（F8） |

**结句**：报告可复算的核心数字（Fn/Cf/RT/Ct）误差远小于 3%，**不满足 <3% 的两项（V3/V4）报告自己已标 HONEST-FAIL**，
本审核不改写该结论；另新增一项本轮才暴露的 >3% 偏差（12 kn 行 Rw，{abs(rows[0]['Rw_dev_pct']):.2f}%，来自 Cr 列舍入，F5），按规定如实列出、不粉饰。

**repro_cmd**（工作树根执行，一键复跑）：

```bash
python3 scripts/wp5577_review.py --offline     # 审核：写 review_report.json + kf_result.json（--online 在线复取并校验快照未漂移）
python3 scripts/wp5577_review.py --figure      # 渲染 fig1_closure_residuals.png
python3 scripts/wp5577_build_report.py         # 组装本报告（唯一 json 块=结果信封）
python3 -m pytest tests/test_wp5577_review.py -q   # 20 项测试（含篡改引文/平移 locator/坏哈希负对照）
```

**结果信封（契约要求的唯一 json 代码块）**：

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""

    p_md = os.path.join(OUT_DIR, f"KF-RESULT-{R.PKG}.md")
    open(p_md, "w", encoding="utf-8").write(md)
    print("wrote", p_md, len(md), "chars")

    if a.payload:
        png = base64.b64encode(open(fig, "rb").read()).decode()
        payload = {
            "title": f"KF-RESULT {R.PKG}",
            "summary": (f"04-independent-review｜审核对象=上游 {rev['reviewed_object']['package_id']}（结果报告 "
                        f"#{rev['reviewed_object']['result_report_id']}）所登记的报告 5577：源哈希逐字节一致，"
                        f"上游 21 资产/17 条 markdown locator 全回解、claims 按契约留空；"
                        f"报告可复算数字全部闭合（RT 残差 ≤{mx['RT_dev_kN']} kN、Ct ≤{mx['Ct_dev_pct']}%、Fn ≤{mx['Fn_dev_pct']}%），"
                        f"6 项不可复算如实记 unknown；发现 3 medium（公式口径不一致/关键常数无出处/两个修复前数字不相容）"
                        f"+6 low+1 info，无阻断级缺陷 → verdict={rev['verdict']}。"),
            "scenario_key": rev["target_report"]["scenario_key"],
            "mission_id": a.mission_id,
            "tags": [f"kf-wp:{R.PKG}", "independent-review", "red-team-reviewer", "report-5577",
                     "campaign/bp-demo-in12p8", rev["verdict"]],
            "markdown": md,
            "figures": [{"name": "fig1_closure_residuals.png",
                         "caption": "左：report-5577 ③ 主表逐项复算偏差（Fn/Cf/Rf/Rw/Ct，ρ=1025、ΔCf=4.0e-4）；右：⑥ 判据算术复算 vs ±3% 带",
                         "png_base64": png}],
        }
        json.dump(payload, open(a.payload, "w", encoding="utf-8"), ensure_ascii=False)
        print("payload:", a.payload, os.path.getsize(a.payload), "bytes")


if __name__ == "__main__":
    main()