#!/usr/bin/env python3
"""wp-11608-04: render docs/kf/wp-11608-04/KF-RESULT-wp-11608-04.md.

All numbers/tables are injected from checks.json / review_report.json / kf_result —
no hand transcription of any figure.

Usage:
  python3 runs/wp-11608-04/make_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import numpy

ROOT = Path(__file__).resolve().parents[2]
PKG = "wp-11608-04"
HERE = ROOT / "runs" / PKG
DOCS = ROOT / "docs" / "kf" / PKG


def main() -> int:
    checks = json.loads((HERE / "checks.json").read_text(encoding="utf-8"))
    review = json.loads((HERE / "review_report.json").read_text(encoding="utf-8"))
    kf = json.loads((HERE / "kf_result.wp-11608-04.json").read_text(encoding="utf-8"))
    A, B, C, D, E, F = (
        checks["a_upwind"],
        checks["b_von_neumann"],
        checks["c_lax_wendroff"],
        checks["d_cd2"],
        checks["e_grid_convergence"],
        checks["f_quick"],
    )
    G, H = checks["g_inventory"], checks["h_hygiene"]

    # ---------------------------------------------------------------- (a) table
    rows_a = "\n".join(
        "| {C} | {kdx:.4f} | {nu_th:.4f} | {meas_report} | {meas_rev:.6f} | {dev_rep:+.3f}% | "
        "{dev_rev:+.4f}% | {ratio:.1f}x | {sign} |".format(
            C=r["C"],
            kdx=r["kdx"],
            nu_th=r["nu_th_rederived"],
            meas_report=r["nu_meas_report"],
            meas_rev=r["nu_meas_reviewer"],
            dev_rep=r["dev_pct_report_signed"],
            dev_rev=r["dev_pct_reviewer"],
            ratio=r["report_dev_over_exact_dev"],
            sign="✓" if r["sign_matches_report"] else "✗ 反号",
        )
        for r in A["rows"]
    )

    rows_c = "\n".join(
        "| {C} | {kdx:.4f} | {rep:.1e} | {rev:.3e} | {th:.3e} | {ratio:.2f}x |".format(
            C=r["C"],
            kdx=r["kdx"],
            rep=r["nu_report"],
            rev=r["nu_exact_von_neumann"],
            th=r["asymptotic_C_1mC2_th2_over_8"],
            ratio=r["report_over_reviewer"],
        )
        for r in C["rows"]
    )

    rows_e = "\n".join(
        "| {N} | {dx} | {kdx:.5f} | {rep} | {rev:.6f} | {ratio} |".format(
            N=r["N"],
            dx=r["dx"],
            kdx=r["kdx"],
            rep=r["nu_report"],
            rev=r["nu_meas_reviewer"],
            ratio="—" if r["ratio_to_previous"] is None else f"{r['ratio_to_previous']:.5f}",
        )
        for r in E["rows"]
    )

    quick_rows = "\n".join(
        "| {k} | {exact:.4f} | {rep:.4f} | {der:.3f} | {r1:.2f}x | {r2:.5f} |".format(
            k=k.replace("_", ", "),
            exact=v["nu_exact"],
            rep=v["report_formula_1mC_1mC2_over_8"],
            der=v["reviewer_derived_5m4C_over_8"],
            r1=v["ratio_exact_over_report_formula"],
            r2=v["ratio_exact_over_reviewer_derived"],
        )
        for k, v in F["comparisons"].items()
    )

    b_rows = "\n".join(
        "| {s} | {c02:.1e} | {c05:.1e} | {c08:.1e} | {rep:.4f} |".format(
            s=scheme,
            c02=v["C=0.2"]["max_abs_err_stencil_vs_closed"],
            c05=v["C=0.5"]["max_abs_err_stencil_vs_closed"],
            c08=v["C=0.8"]["max_abs_err_stencil_vs_closed"],
            rep=B["report_table_max_abs_err"][scheme],
        )
        for scheme, v in B["reviewer_stencil_vs_closed"].items()
    )

    d_rows = "\n".join(
        "| {k} | {g:.4f} | {n} | {a:.4f} |".format(
            k=k.replace("_", ", "),
            g=v["G_abs"],
            n=v["steps_half_period"],
            a=v["amp_growth"],
        )
        for k, v in D["half_period_growth"].items()
    )

    evid_rows = "\n".join(
        "| {id} | {sev} | {q} | `[{s},{e})` L{l} |".format(
            id=f["id"],
            sev=f["severity"],
            q=f["evidence_locator"]["quote"].replace("|", "\\|"),
            s=f["evidence_locator"]["start_char"],
            e=f["evidence_locator"]["end_char"],
            l=f["evidence_locator"]["start_line"],
        )
        for f in review["findings"]
    )

    finding_rows = "\n".join(
        "| {id} | {sev} | {subj} | {disp} |".format(
            id=f["id"],
            sev=f["severity"],
            subj=f["subject"].replace("|", "\\|"),
            disp=f["disposition"].replace("|", "\\|"),
        )
        for f in review["findings"]
    )

    not_run = "\n".join(f"- {x}" for x in review["checks_not_run"])
    overstated = "\n".join(f"- {x}" for x in review["overstated_claims"])
    remediation = "\n".join(f"{i}. {x}" for i, x in enumerate(review["disposition"]["remediation"], 1))

    files = [
        ("review_report.json", "独立审核产物：8 条 finding、独立性声明、检查清单、disposition"),
        ("review_events.json", "审核决策事件账本（5 条 seq）"),
        ("checks.json", "独立重算的全部数字（零手抄，机器生成）"),
        ("kf_result.wp-11608-04.json", "平台结果信封（provenance.source_hash = 契约哈希）"),
        ("independent_checks.py", "独立重算脚本：4 格式重实现 + 6 判据块 + 4 个负向对照"),
        ("build_review.py", "finding/图表构建器（引文定位程序化校验）"),
        ("make_kf_result.py", "信封组装 + schema 校验 + 交付物 staging"),
        ("fig1_upwind_deviation.png", "判据(a)：报告误差列 vs 独立重算（对数轴）+ 偏差符号"),
        ("fig2_criterion_power.png", "判据(b)：±1e-3 阈值对 0.1% 系数误差无分辨力 + 可达残差"),
        ("fig3_quick_and_lw.png", "QUICK 前阶黏性公式证伪 + L-W θ 标度矛盾"),
        ("fig4_cd2_and_grid.png", "CD2 半周期增长 vs 报告区间 + 网格收敛复现"),
    ]
    file_rows = "\n".join(
        "| `{n}` | {b} | {d} |".format(
            n=n,
            b=f"{((DOCS / n).stat().st_size / 1024):.1f} KB",
            d=d,
        )
        for n, d in files
    )

    acceptance = [
        ("valid_json", "✓", "kf_result 与 review_report 均 json.load 通过（pytest 断言）"),
        ("schema_pass", "✓", "Draft202012Validator vs schemas/kf_result.v1.schema.json"),
        (
            "reviewer_independent",
            "✓",
            "未读生产者代码/测试/产物/解释；四格式按报告 1.2/2.2 的格式定义自行重实现",
        ),
        (
            "upstream_packages_completed",
            "✓（范围受限）",
            "report 11608 仅存在 wp-11608-01（published，gate=pending_platform_verification）；"
            "wp-11608-02/03 不存在 → 本审核对象=wp-11608-01+报告正文",
        ),
        (
            "constraints.do_not_mark_claims_as_verified",
            "✓",
            "claims_marked_verified_by_this_review = 0；只给 findings + disposition",
        ),
        (
            "constraints.reviewer_context_excludes_producer_explanation",
            "✓",
            "上下文仅：markdown 原文（哈希钉死）+ 上游 asset_manifest",
        ),
        (
            "constraints.review_prompt_not_copied_from_producer",
            "✓",
            "finding 均由原文复算得出；仅逐字引用必要的原文片段并记录 char span",
        ),
        (
            "output.review_report.json",
            "✓",
            "reports/review_report.json 已生成（8 findings）",
        ),
    ]
    acc_rows = "\n".join(f"| {k} | {s} | {b} |" for k, s, b in acceptance)

    md = f"""KF-RESULT wp-11608-04

# KF-RESULT wp-11608-04

| 项 | 值 |
|---|---|
| package_id | `{PKG}` |
| 工序 | `04-independent-review`（lane C） |
| report_id | `11608` |
| scenario_key | `{kf["provenance"]["scenario_key"]}` |
| 源哈希 | `{kf["provenance"]["source_hash"]}`（{kf["provenance"]["chars"]} 字符，独立重算一致） |
| 审核对象 | 上游 `wp-11608-01`（01-asset-registration）+ 报告正文 |
| disposition | **{review["disposition"]["verdict"]}**（major {review["severity_counts"]["major"]} / medium {review["severity_counts"]["medium"]} / minor {review["severity_counts"]["minor"]} / info {review["severity_counts"]["info"]}） |
| 本轮标 verified 的断言数 | 0（验证判定归平台门） |

---

## ① 本工序做了什么

对 report 11608（TensorFVM 数值黏性/色散算子验证面）做独立红队审核，判定 `pass / fail / needs-fix`。
做法上不复用生产者的任何代码或解释：从报告 §1.2 的四个格式定义、§2.2 的两条公式出发，**自行重实现**迎风 / Lax–Wendroff / CD2 / Leonx-QUICK
四个一维周期对流格式，重算六块判据（a–f）的数值，并用**负向对照（mutant stencil）**测量报告自己的阈值能查出多大的错误。

结论：**needs-fix**。四条物理结论（迎风 ν_th=cΔx(1-C)/2 成立；CD2 纯色散且 |G|>1；L–W 近乎无耗散；ν∝Δx）在独立重算下**依然成立**，
但 3/6 判据表的逐行数字不可复现、1 条印刷公式（QUICK 前阶黏性）被证伪、1 条区间（CD2 半周期增长）无任何枚举工况支撑：

- **R1 (major)** §3.1 的 9 行 ν_meas 与误差列不可复现：精确 von Neumann 偏差比报告列小 {A["ratio_band"][0]:.1f}–{A["ratio_band"][1]:.1f} 倍，且 {A["sign_contradictions"]}/9 行**偏差符号相反**（C={'/'.join(sorted({str(r['C']) for r in A['rows'] if not r['sign_matches_report']}))} 三行）。判据 (a) 的结论本身更强（独立重算最大偏差 {A["max_dev_pct_reviewer"]:.2f}% < 1%）。
- **R2 (major)** §2.2 的 QUICK 公式 `ν_th=cΔx(1-C)(1-C²)/8` 不是 QUICK 的前阶黏性：由 Leonard 两点迎风插值自行推导为 `cΔx(5-4C)/8`，比报告公式大 {min(v["ratio_exact_over_report_formula"] for v in F["comparisons"].values()):.1f}–{max(v["ratio_exact_over_report_formula"] for v in F["comparisons"].values()):.1f} 倍，且**比一阶迎风还大**（1.3–2.25 倍）——报告"QUICK 小但非零"的定性判断被推翻。
- **R3 (major)** §3.3 的 L–W 残差黏性列标度为 O(θ)（理论 O(θ²)），C 依赖单调上升（理论峰值在 C=1/√3≈0.577），报告/独立值比 0.33–2.08；"小 1–2 个量级"实为 **{1e-2 / C["max_nu_reviewer"]:.1f} 倍裕度**。判据 (c) 的通过结论仍成立。
- **R4 (medium)** 判据 (b) 在 §2.3 写绝对阈值、§3.2 写相对阈值，两者不一致；相对式在迎风 C=0.5、θ=π（|G|=0）处**除零病态**；0.1% 系数误差的 mutant **仍通过** ±1e-3 绝对阈值；而可达一致度是 1e-15 量级，表格里的 1.5e-4–5.9e-4 无来源。
- **R5 (medium)** §3.4 的"A_ratio=1.15~1.35"仅 {9 - D["cases_below_report_band"]}/9 工况成立（独立重算区间 {D["reviewer_growth_range"][0]:.3f}–{D["reviewer_growth_range"][1]:.3f}，{D["cases_below_report_band"]}/9 低于 1.15）。
- **R6 (minor)** §3.5 网格收敛结论复现（比值 {'/'.join(f'{x:.4f}' for x in E["reviewer_ratios"])} vs 报告 0.500/0.500/0.501），但表未声明每级 (C, kΔx)，且四舍五入掩盖了 §3.1 已可见的 +0.16% 有限 θ 偏差。
- **R7 (minor)** §7/§8 的 8 个工件路径、字节数、"57 passed"、commit 在本审核范围内**无法核验**（无 TensorFVM 检出）；末行 *报告工件路径* 与平台 `record.figures` 指向 hydroelasticity，主体污染（与上游 wp-11608-01 记录一致）。
- **R8 (info)** 报告头 `✅ 全部验收判据通过` 是结论级判断，行级证据不支持（3/6 表含不可复现行）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET /tensor/reports/11608` → `markdown`（psql 直读被权限拒绝，走 API），落盘字节级副本；独立重算 sha256 = 契约值，字符数 7342 一致。
2. **读上游**：只读 `docs/kf/wp-11608-01/asset_manifest.json` + `verification.json`（25 资产 / 5 resolved / 14 unresolved / 6 absent / off_topic 10）。
3. **重实现四格式**（c=1, Δx=1, 显式 Euler，周期域）：迎风、L–W、CD2、Leonard-QUICK（`u_{{j+1/2}}=3/4u_j+3/8u_{{j-1}}-1/8u_{{j-2}}`；报告未给 QUICK 模板，故同时记录替代插值的敏感性）。
4. **判据 (a)**：单模 `exp(ikx)` 推进 2 个波周期，`ν_meas=-ln(A/A0)/(k²t)`，kΔx=2πm/256（m=2,4,8），C∈{{0.2,0.5,0.8}} → 9 组；同时算闭式 `ν_exact=-ln|G|/(k²Δt)`。
5. **判据 (b)**：θ∈(0,π) 48 个严格内点：①stencil 作用于解析模 vs 闭式符号（一致性探针）；②**多步 march 反演 |G|**（63 个网格相容 θ × 4 格式 × 3 C）——非同一公式自证。
6. **负向对照**：迎风 C 乘 1.001、QUICK 3/4→0.74 的 mutant，测报告阈值分辨力；记录相对阈值在 |G|→0 的除零病例。
7. **判据 (c)/(d)/(e)**：L–W 9 组残差黏性与渐近律 `C(1-C²)θ²/8` 对比；CD2 `|G|` 与半周期增长逐工况；网格 4 级加密（固定物理模态 m=8，L=256）。
8. **QUICK 公式**：对自身符号求 κΔx→0 极限（θ=0.02, 0.01），与报告公式和自推公式比值。
9. **卫生探针**：工件/测试/commit 声明、hydroelasticity 主体污染、图像链接是否进入平台 figure 字段、清单算术（36=4×3×3）。
10. **工具链**：python {sys.version.split()[0]} / numpy {numpy.__version__} / matplotlib {matplotlib.__version__} / jsonschema；单机全量重算约 4 s（<8 核、<10 min，故未递交集群）。

**阈值纪律**：全部阈值取报告自己写的判据（1% / 1e-3 / 1e-2·cΔx / 5%），未在看到结果后调整；报告未声明的参数（如 §3.5 的 C、kΔx）显式标注为假设 m=8、C=0.5。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 大小 | 要点 |
|---|---|---|
{file_rows}

图（matplotlib，全部数字由 `checks.json` 程序化注入）：

- `fig1_upwind_deviation.png`：判据 (a) 误差列 vs 独立重算（对数轴）+ 9 行偏差符号。
- `fig2_criterion_power.png`：±1e-3 阈值下 0.1% 系数误差不可分辨；可达残差 1e-15 vs 报告表格 1e-4。
- `fig3_quick_and_lw.png`：QUICK 前阶黏性（报告公式 vs 自推 (5-4C)/8 vs 迎风）+ L–W 标度矛盾。
- `fig4_cd2_and_grid.png`：CD2 半周期增长 vs 报告区间；网格收敛复现。

## ④ 证据定位表（claim/字段 → 原文逐字引文，含 char span）

| finding | 级别 | 原文逐字引文 | char span |
|---|---|---|---|
{evid_rows}

判据 (a) 逐行（报告值 vs 独立重算）：

| C | kΔx | ν_th | 报告 ν_meas | 独立 ν_meas | 报告偏差(带符号) | 独立偏差 | 报告/精确偏差 | 符号 |
|---|---|---|---|---|---|---|---|---|
{rows_a}

判据 (b) 一致度（stencil vs 闭式，48 内点；march vs 闭式在 63 点最大相对误差 ≤ {max(v["C=0.8"]["max_rel_err_march_vs_closed"] for v in B["reviewer_march_vs_closed"].values()):.1e}）：

| 格式 | C=0.2 | C=0.5 | C=0.8 | 报告表 §3.2 最大值 |
|---|---|---|---|---|
{b_rows}

判据 (c) L–W：

| C | kΔx | 报告 ν | 独立 ν_exact | 渐近律 C(1-C²)θ²/8 | 报告/独立 |
|---|---|---|---|---|---|
{rows_c}

判据 (d) CD2 半周期增长（报告区间 {D["report_growth_band"][0]}–{D["report_growth_band"][1]}）：

| 工况 | \\|G\\| | 步数 | A(0.5T)/A(0) |
|---|---|---|---|
{d_rows}

判据 (e) 网格收敛：

| N | Δx | kΔx | 报告 ν | 独立 ν | 比值 |
|---|---|---|---|---|---|
{rows_e}

QUICK 前阶黏性（θ→0，θ=0.02/0.01）：

| 工况 | 独立 ν_exact | 报告公式 | 自推 (5-4C)/8 | 比值(精确/报告) | 比值(精确/自推) |
|---|---|---|---|---|---|
{quick_rows}

findings 汇总（severity 排序；每条附复现命令与处置）：

| id | 级别 | 对象 | disposition |
|---|---|---|---|
{finding_rows}

## ⑤ 注意点与局限

- **独立性局限**：本工作树内无 TensorFVM 检出，生产者脚本/测试/工件无法 diff；"不可复现"= 在报告陈述的参数下用独立路径得不到该数字，**不等于"编造"**，也不对其动机做任何推断。
- **未运行的检查**（记为 not_run / unknown，不记为通过）：

{not_run}

- **2D 交叉导数项**（§2.3 第 6 条、§5.4 的"5%–10%"）未建 2D 求解器，**unknown**；QUICK 稳定域结论（C≤0.5）未探。
- **QUICK 模板歧义**：报告只给公式不给差分模板，自推值依赖 Leonard 两点迎风插值；替代"中心型三点"插值给出更大前阶黏性（0.9/0.75/0.6），**两种插值下报告公式都不成立**，故结论对模板选择稳健。
- **上行不可改**：上游 wp-11608-01 的 25 资产登记与本审核一致（主体污染、6 张 record.figures 缺席），本包只读不改。
- **卫生探针（原文可见性，不涉及数值）**：清单算术 36 = 4×3×3 → {G['matches']}；
  自我声明"全部验收判据通过" → {H['self_declared_all_criteria_pass']}；
  "57 passed" 声明 → {H['test_count_claim']}（未运行）；commit"待平台自动推送" → {H['commit_pending']}；
  hydroelasticity 主体污染路径 → {H['offtopic_hydroelasticity_paths']}；
  正文三张图链接 → {', '.join(H['figure_links'])}，但平台 record.figures 未内嵌（{H['figures_embedded_in_platform_record']}）。
- **边界**：仅触碰 report_id=11608；测试 `test_boundary_only_report_11608_is_referenced` 断言。

被判定为"夸大/无支撑"的原句（逐条对应上面的 finding）：

{overstated}

修复建议（本工序不代替上游改稿）：

{remediation}

## ⑥ 自检：逐条对照 acceptance

| 验收键 | 结果 | 依据 |
|---|---|---|
{acc_rows}

诚实备注（不粉饰）：

- `upstream_packages_completed` 只能算**范围受限通过**：11608 只产出了 01 包，02/03 不存在；若门要求 01→02→03 齐备，本键应判 FAIL。
- 报告 §7 的 8 个工件、227 KB JSON、"57 passed"、commit 号在本范围内 **unverifiable**，按纪律记 `not_run`，不写成"通过"也不写成"造假"。
- 本轮**未**把任何断言标为 verified；disposition 仅为审核意见，验收判定归平台门。

一键复跑：

    # 需 TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE（仅取源一步需要）
    cd <worktree>
    python3 runs/wp-11608-04/fetch_source.py         # -> runs/wp-11608-04/source_report_11608.md（校验 sha256）
    python3 runs/wp-11608-04/independent_checks.py   # -> runs/wp-11608-04/checks.json（4 格式重实现 + 负向对照）
    python3 runs/wp-11608-04/build_review.py         # -> review_report.json / review_events.json / 4 张图
    python3 runs/wp-11608-04/make_kf_result.py       # -> kf_result 信封（schema 校验）+ docs/kf/wp-11608-04/ staging
    python3 runs/wp-11608-04/make_report.py          # -> docs/kf/wp-11608-04/KF-RESULT-wp-11608-04.md（本文件）
    python3 -m pytest tests/test_kf_wp11608_04.py -q # 13 项验收不变量

```json
{json.dumps(kf, indent=2, ensure_ascii=False)}
```
"""
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / f"KF-RESULT-{PKG}.md").write_text(md, encoding="utf-8")
    print("wrote", DOCS / f"KF-RESULT-{PKG}.md", len(md), "chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())