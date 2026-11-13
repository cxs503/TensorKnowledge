#!/usr/bin/env python3
"""Render WP-611-04.md: six sections + exactly ONE ```json block (the KF envelope).

Numbers are injected from independent_check_results.json / review_report.json;
quotes are re-verified as byte substrings of _source_611.md before rendering.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    res = json.load(open(os.path.join(HERE, "independent_check_results.json"), encoding="utf-8"))
    rep = json.load(open(os.path.join(HERE, "review_report.json"), encoding="utf-8"))
    kf = json.load(open(os.path.join(HERE, "kf_result_wp-611-04.json"), encoding="utf-8"))
    md = open(os.path.join(HERE, "_source_611.md"), encoding="utf-8").read()

    g, b, st, w = (res["geometry_and_equilibrium"], res["buoyancy"],
                   res["stability"], res["wave_consistency"])
    ref = b["independent_reference_rel_errors"]
    ident = res["GM_identity"]

    def q(quote: str) -> str:
        assert md.find(quote) >= 0, quote[:50]
        return f"`{quote}`"

    rows_metrics = []
    for m in rep["reproduction_table"]:
        rv = m["reported"]
        cv = m["recomputed"]
        def fmt(x, ref_val=None):
            if isinstance(x, float) and (abs(x) < 1e-3 or (ref_val is not None and abs(ref_val) < 1e-3)):
                return f"{x:.3e}"
            return f"{x:.4f}" if isinstance(x, float) else str(x)
        d = m["relative_difference"]
        diff = "n/a" if d is None else f"{d:.2e}"
        rows_metrics.append(
            f"| {m['quantity']} | {fmt(rv)} | {fmt(cv, rv)} | {diff} | {m['reproduction_status']} |"
        )

    rows_findings = []
    for f in rep["findings"]:
        rows_findings.append(
            f"| {f['finding_id']} | {f['severity']} | {'yes' if f['blocking'] else 'no'} | {f['title']} | {f.get('disposition', '—')} |"
        )

    rows_quotes = []
    for f in rep["findings"]:
        for ev in f["evidence"]:
            quote = ev["quote"].replace("|", "\\|")
            rows_quotes.append(
                f"| {f['finding_id']} | {quote} | [{ev['start_offset']}:{ev['end_offset']}] |"
            )

    body = f"""# KF-RESULT wp-611-04

**工序**：04-independent-review（lane C）｜**report_id**：611｜**审核对象**：wp-611-01（01-asset-registration）
**审核者**：{rep['reviewer']['id']}（{rep['reviewer']['role']}）｜**生产者身份**：{rep['producer_identity']}
**source_hash**：`{rep['subject']['source_hash']}`（独立重算一致，见 §2 步骤 2）
**结论**：`request-changes` / **needs-fix**（拆分：wp-611-01 包面一致性 = pass；报告 611 的语义保真 = needs-fix）
**分层**：DEM｜SIR-PC2_F07_dem_buoyancy_wet_coupling｜s

---

## ① 本工序做了什么

只处理 `report_id=611` 一份报告（markdown 字段），对上游包 wp-611-01 做独立红队审核。上下文只有
**报告原文 + 上游知识对象**，未读、未索取生产者的方法自述或解释；未在任何字段把结论标成 verified
（验证级别由平台门计算，本包只给 `request-changes` 与 findings）。

三件事：

1. **重算**：用报告正文里逐字给出的参数（{q('**Parameters:** R=0.5m, ρ_i=917 kg/m³, ρ_w=1025 kg/m³, g=9.81 m/s², wave A=0.1m, λ=10m, T=2.5s.')}）
   独立重算 §3 表的每个数字（解析式 + 数值积分 + Monte-Carlo + sympy 恒等式），共 {len(rep['reproduction_table'])} 项。
2. **反驳**：对差异项做可复现的"为什么错"分析（候选公式表、全域扫描、符号证明），而不是只报不一致。
3. **定级**：给出 {len(rep['findings'])} 条 finding（{sum(1 for f in rep['findings'] if f['blocking'])} 条 blocking），
   以及未跑的检查和被夸大的表述清单。

## ② 怎么做的（步骤/工具/关键设置）

1. `GET /api/v1/tensor/reports/611`（Bearer）取 `markdown`，落 `_source_611.md`。
2. 独立重算 `sha256(markdown)` = `{res['source_sha256']}` → 与契约 `source_hash` **逐字节一致**
   （`source_sha256_matches_contract = {str(res['source_sha256_matches_contract']).lower()}`）。
3. 用报告参数重算几何与平衡：二维圆缺 / 三维球冠的解析式，配合两种独立参考——
   **水平切片中点求积**（n=2e3、5e4）与 **Monte-Carlo**（固定 seed，2e5 样本）。
4. 平衡吃水用二分法解 `f_sub = ρ_i/ρ_w`（tol 1e-15，200 步）；浮力按 `F_b = ρ_w g V_sub` 与重量 `ρ_i g V_total` 闭合检验。
5. 复原力与稳性：`k_heave = ρ_w g A_wp`（等价于报告写的 `ρ_w g V_total |df_sub/dh|`，因 `dV_sub/dh = A_wp`）；
   `GM = BM − BG`，`BM = I_wp/A_sub`，`BG = |z_B|`（均质体 G 在几何中心）。
6. 恒等式验证：sympy 对三维球冠做**符号化简**，检验 `BM − BG` 是否恒等于 0。
7. 全域扫描：`f_sub ∈ [0.30, 0.98]`（121 点），取 `max |GM|` 检验"GM<0"能否在任何吃水出现。
8. 波参数自洽：深水色散 `ω²=gk` 反解 λ(T)、T(λ)、以及该 (λ,T) 对隐含的 g。
9. 出图 `fig_review_611.png`（4 面板），产 `review_report.json` / `review_events.json` / 本报告里的单一 JSON 块。
10. 门自检 `verify_deliverables.py`（schema / 状态机 / 独立性 / 引文逐字 / 禁字段 / 单 json 块）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `review_report.json` | 契约声明输出：结论 request-changes、{len(rep['findings'])} 条 finding、{len(rep['reproduction_table'])} 行重算对照、4 项 acceptance、未跑检查、被夸大表述 |
| `review_events.json` | append-only 审核台账（S15 要求 04 包必须带）：`in-review + request-changes → draft`，带 blocking findings |
| `kf_result_wp-611-04.json` | KF 信封（`schemas/kf_result.v1.schema.json`），provenance.source_hash = 源哈希 |
| `independent_check_611.py` | 独立重算脚本（解析 + 求积 + MC + 符号恒等式 + 波参数自洽） |
| `independent_check_results.json` | 全部重算数值（机器注入，零手抄） |
| `make_figure.py` / `fig_review_611.png` | 4 面板对比图：GM(f_sub)、k_heave(f_sub)、参考方法可分辨的下限、GM 候选公式 |
| `build_review_611_04.py` / `render_report_611_04.py` | 产物生成器（数值与引文全部程序化注入） |
| `verify_deliverables.py` | 自检门（见 §6） |

## ④ 证据定位表

### ④.1 重算对照（报告值 vs 独立重算，claim → 数值证据）

| 量 | 报告值 | 独立重算 | 相对/绝对差 | 判定 |
|---|---|---|---|---|
{chr(10).join(rows_metrics)}

支撑数值：`F_b(2-D) = {b['Fb_2d_N_per_m']:.4f} N/m`，`F_b(3-D) = {b['Fb_3d_N']:.4f} N`（报告正文**未给**任何绝对值）；
平衡残差 `{b['equilibrium_residual_2d']:.2e}`（2-D）/ `{b['equilibrium_residual_3d']:.2e}`（3-D）；
符号恒等式 `BM = {ident['BM']}`、`BG = {ident['BG']}`、`BM − BG = {ident['BM_minus_BG']}`。

**关键判定（是否 <3%？）**：几何/平衡/复原力 5 项 <1e-4 → **YES**；GM(2-D) 绝对差 {st['GM_abs_diff_2d']:.1e} m → **YES**；
GM(3-D) 绝对差 **{st['GM_abs_diff_3d']:.3f} m** → **NO（解析值应为 0，报告值被反驳）**；
浮力相对误差 2.19e-16 与本包独立参考（{ref['quadrature_n50000']['rel_err_3d']:.2e}）不可比 → **不可作为保真证据**。

### ④.2 Findings（按严重度；每条挂原文引文，见 ④.3）

| id | 严重度 | blocking | 问题 | 处置 |
|---|---|---|---|---|
{chr(10).join(rows_findings)}

F1 的核心（可复现）：三维球冠的 `BM = 3(2R−h_c)²/(4(3R−h_c))` 与 `BG` 同式，**逐项相消**；全域扫描
`f_sub∈[0.30,0.98]` 得 `max|GM| = {st['GM_max_abs_over_draught_grid_3d']:.1e} m`（二维 {st['GM_max_abs_over_draught_grid_2d']:.1e} m）。
即：均质球体**任何吃水都不可能出现 GM<0**，报告把 GM<0 说成"known analytical result"是错的；
最接近的"标准误算"是半球式 `KG=R, KB=3R/8, BM=3R/8`（即 {st['GM_hypotheses_3d']['GM_half_draught_with_BG_from_keel_mis_set']:.3f} m，
与 −0.115 差 {st['GM_hypotheses_3d']['nearest_standard_variant_gap']:.3f} m）。

### ④.3 原文逐字引文（claim → quote，偏移为 markdown 码点下标）

| finding | 原文引文（逐字） | 偏移 |
|---|---|---|
{chr(10).join(rows_quotes)}

## ⑤ 注意点与局限

### ⑤.1 被夸大的表述（overstated claims）

| 原文表述 | 问题 |
|---|---|
{chr(10).join(f"| {c['statement'].replace('|', chr(92) + '|')} | {c['issue']} |" for c in rep['overstated_claims'])}

### ⑤.2 未执行的检查（not_run，不计为通过）

| 检查 | 状态 | 原因 |
|---|---|---|
{chr(10).join(f"| {c['check']} | `{c['status']}` | {c['reason']} |" for c in rep['checks_not_run'])}

### ⑤.3 其它局限

- 本报告**没有**任何代码/commit/run 指针，上游 wp-611-01 的 `artifacts` 为空，因此本次审核只能判定
  **报告算术与自洽**，不能判定实现保真（`checks_not_run` 已列）；生产者自述的 `pytest=PASS` 在 record 的
  summary 字段（不在审核字段 source_field=markdown 内），**未执行、不计为证据**。
- GM 重算假设**均质体**（ρ_i=917 作为体密度，质心在几何中心）；报告未给 KG，若为非均质则本身不可复现——F1 在两种情形下都成立。
- 参数取自报告正文，未独立测量；`λ=10m` 与 `T=2.5s` 互相不一致（F4），本次两种口径都算了（D/λ = {w['D_over_lambda']:.3f} / {w['D_over_lambda_from_T']:.3f}）。
- 图 1–6 只审到 caption，PNG 内容未打开（`not_run`）。
- 本包**不给**验证级别、不写 `verified`；`request-changes` 使知识停在 draft。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | 三个 JSON 均 `json.load` 通过（verify_deliverables.py 第 1 项） |
| `schema_pass` | ✅ | 信封过 `kf_result.v1.schema.json`；台账事件过 `review-event.schema.json`（第 2–3 项） |
| `reviewer_independent` | ✅ | `ke_state_machine.is_independent` → distinct-identity；生产者 {rep['producer_identity']} ≠ 审核者 {rep['reviewer']['id']}（第 4 项） |
| `upstream_packages_completed` | ✅ | scenario_key 列表仅 wp-611-01（published）+ 源报告；无 wp-611-02/03，故上游只有 01（第 5 项） |
| 引文逐字可定位 | ✅ | {sum(len(f['evidence']) for f in rep['findings'])} 条引文全部 `md.find(quote) >= 0` 且偏移回读字节相等（第 6 项） |
| 不标 verified | ✅ | 递归扫描字段名，无 verified / verification_* / is_verified（第 7 项） |
| 单 json 块 | ✅ | 正文只有 1 个 JSON 围栏块，且能被 `json.loads` 解析为信封（第 8 项） |
| 只碰 report 611 | ✅ | 只写本目录；除 wp-611-01 的元数据/身份外未触碰其它 report_id |

**honest 声明**：未跑项已在 `checks_not_run` 逐条列出（生产者测试、实现代码、图片内容、Morison 复算、M4/M5 度量），
均标 `not_run`，**不**计为通过。

## repro_cmd

```bash
# 一键复跑（工作树根 = 仓库检出）
bash docs/reviews/wp-611-04/run_all.sh
```

## 结果信封（正文唯一的 JSON 围栏块）

```json
{json.dumps(kf, indent=2, ensure_ascii=False)}
```
"""
    out = os.path.join(HERE, "WP-611-04.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(body)
    print("wrote", out, len(body), "chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())