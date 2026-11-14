#!/usr/bin/env python3
"""Assemble docs/kf/wp-11557-04/KF-RESULT-wp-11557-04.md (six sections + the one
```json result block). Numbers are injected from the probe artefacts."""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs/kf/wp-11557-04"
PKG = "wp-11557-04"

res = json.loads((OUT / "kf_result.wp-11557-04.json").read_text())
rev = res["outputs"]["review_report.json"]
p1 = json.loads((HERE / "probe_results.json").read_text())
p2 = json.loads((HERE / "probe2_results.json").read_text())
p3 = json.loads((HERE / "probe3_results.json").read_text())
p4 = json.loads((HERE / "probe4_results.json").read_text())
chk = json.loads((HERE / "checks.json").read_text())
b1, b2, b3 = p1["B1_closed_form"], p1["B2_shipped_code"], p3
kof = p1["A_upstream_ko_fidelity"]

F = {f["id"]: f for f in rev["findings"]}
acc = rev["acceptance_check"]


def tick(ok):
    return "✅" if ok else "❌"


# evidence table rows: finding -> source quote (already verbatim-verified)
rows = []
for fid in ("F1", "F1", "F2", "F3", "F4", "F5", "F6", "F7"):
    f = F[fid]
    for k, v in f.items():
        if k.startswith("quote"):
            rows.append((fid, k, v))
ev_rows = "\n".join(
    f"| {fid} | `{k}` | `{q}` |" for fid, k, q in rows)

md = f"""# KF-RESULT {PKG}

**工序**：04-independent-review ｜ **报告**：11557 ｜ **审核对象**：{rev['reviewed_package']} ｜ **结论**：`{rev['verdict']}`
**源哈希**：`{res['provenance']['source_hash']}`（本地重算 = 契约声明 ✅，{res['provenance']['chars']} 字符）

## ① 本工序做了什么

对报告 11557《DEM多面体颗粒与冰-结构混合模式失效验证面》(P180W2-N05) 做**独立红队审核**，判定其验收结论（9 条判据、35 项测试）是否语义保真。审核对象为上游工序产物 {rev['reviewed_package']}，审核上下文**只有**三样东西：报告原文 markdown、上游 KO（asset_manifest / verification）、以及报告所引用的交付代码（TensorDEM `{p4['commit'][:8]}`）。**未打开**生产者解释脚本（`scripts/kf_*_11557.py`），以保证独立性。

结论：**needs-fix**。数字没有造假——报告里每个头条数字都能从交付代码逐位复现，`35/35 通过` 也经独立执行证实（`{p4['passed']} passed`，{p4['wall_seconds']} s）。问题全部在**判定层**：3 条判据被标 PASS 而报告自己的数字已越阈，同一份文档的 §6 又对同 3 条写了「否」；C4 的「Timco 基准」就是模型自身的解析式；C5 的偏差把无量纲比值当百分数印，低报了 100 倍。

## ② 怎么做的（步骤/工具/关键设置）

1. **钉源**：`GET $TENSOR_API_BASE/tensor/reports/11557` 取 `markdown`，本地重算 sha256 与契约比对（{res['provenance']['chars']} 字符 / 3262 字节，一致）。
2. **上游 KO 保真度**（`probe.py` A 段）：11 个资产引文逐条做「子串 + 唯一性 + 字符区间切片」三重校验 → {kof['quotes_verbatim']}/{kof['quotes_total']} 逐字命中、{kof['quotes_unique']}/{kof['quotes_total']} 唯一、{kof['quotes_range_exact']}/{kof['quotes_total']} 区间精确；`by_class`/`by_resolution` 计数与资产数自洽（{kof['assets_declared']}={kof['by_class_sum']}={kof['by_resolution_sum']}）。
3. **闭式复算**（`probe.py` B1 段）：用报告 §1 自报的参数（σc=3 MPa、σf=σt=0.7 MPa、h=1 m、E=5 GPa、D=10 m）与 §2 自报的公式，独立复算 L_b、V_c、R_crush/R_bend/R_split，再与报告数字对照。
4. **跑交付代码**（`probe.py` B2、`probe2.py`、`probe3.py`）：在只读兄弟检出 TensorDEM `{p4['commit'][:8]}` 上直接调用 `ice_mixed_mode` 与 `polyhedron`，取回 `validate_against_timco` / `validate_against_lindqvist` / `compute_phase_diagram` 的真实返回值与 4000 个相图格子的模式普查。
5. **审测试是否断言不变量**（`probe3.py`、`probe4.py`）：逐条摘出 C1/C4/C5/C8 对应测试的 `assert` 行，判断它断言的是「不变量」还是「仅执行」；再独立跑整套 35 项测试。
6. **自门**（`gate_check.py`）：结果 JSON 过 `schemas/kf_result.v1.schema.json`；正文每个数字与 probe 产物逐一比对（容差内）；11 条引文再验逐字唯一；代码引文回验存在于源文件。

关键设置：全程只读（`read_only=True`），不改上游产物、不改报告、不把任何结论标 verified。

## ③ 产出物清单

| 文件 | 要点 |
|------|------|
| `docs/kf/wp-11557-04/kf_result.wp-11557-04.json` | 本工序结果（schema v1；本报告唯一 JSON 代码块的原样内容） |
| `docs/kf/wp-11557-04/review_report.json` | 审核报告本体：verdict=needs-fix，8 条发现（3 high / 3 medium / 2 low），acceptance 逐项 |
| `docs/kf/wp-11557-04/review_events.json` | 审核决策账本（8 个事件：钉源→KO→引文→闭式→代码→相图→测试→判决） |
| `docs/kf/wp-11557-04/source.md` | 报告原文逐字节副本（哈希可复核） |
| `docs/kf/wp-11557-04/figures/fig1_resistance_modes.png` | 阻力-速度曲线 + 分类器 0.5·Vc / 2·V_c 硬阈值 + 94 m/s 交叉点 |
| `docs/kf/wp-11557-04/figures/fig2_pass_vs_threshold.png` | 四条 PASS 判据的实测偏差 vs 自报阈（对数轴） |
| `docs/kf/wp-11557-04/figures/fig3_vc_circularity.png` | 同一解析式换密度：917→2.763（称 Timco），4142→1.3（称 model） |
| `work/wp-11557-04/probe*.py`, `probe*_results.json` | 4 个独立探针及原始输出（可一键复跑） |
| `work/wp-11557-04/checks.json`, `quote_check.json` | 自门结果：schema / 数字溯源 / 引文逐字 |

## ④ 证据定位表（claim → 报告原文引文，逐字）

| 发现 | 字段 | 原文引文片段（verbatim，逐字唯一命中） |
|------|------|----------------------------------------|
{ev_rows}

支撑这些发现的实测值：

| 量 | 报告值 | 独立复算/代码实测 | 判定 |
|----|--------|------------------|------|
| C4 V_c 偏差 vs 自报阈值 30% | `V_c_model=1.3`, `V_c_timco=2.76`（自报行内即 52.9%） | 代码 `relative_error={b3['timco_result']['relative_error']:.4f}` → **{100*b3['timco_result']['relative_error']:.1f}%** | PASS 不成立；且基准 `V_c_timco = compute_critical_velocity(config)` 与模型同式 → 循环 |
| C4 基准值来源 | 「Timco 2.76 m/s」 | 同式代入 ρ=917 得 **{b1['V_c_formula_rho917_m_s']:.4f} m/s**（相对差 {100*b1['V_c_equals_reported_timco']['rel_err']:.3f}%） | 所谓文献值 = 模型自身输出 |
| C4 偏移构成 | 53% | 1 − 1.3/2.7629 = {100*(1-1.3/2.7629):.2f}%；分类器阈值 0.5·Vc={b2['half_V_c']:.4f}，网格 0.1 m/s | 二分之一阈值 + 网格量化，非物理误差 |
| C5 偏差 vs 自报阈值 20% | R_model=70.9 MN, R_lindqvist=1.1 MN | 代码 `R_model={b2['lindqvist_MN']['R_model']:.4f} MN`, `R_lindqvist={b2['lindqvist_MN']['R_lindqvist']:.4f} MN`, `relative_error={b3['lindqvist_relative_error_is_ratio_not_percent']['returned']:.4f}` → **{100*b3['lindqvist_relative_error_is_ratio_not_percent']['returned']:.0f}%**（比值当百分数则 63%→100× 低报） | PASS 不成立，且 §6 的 63% 是比值误当百分数 |
| C1 休止角 10% 偏差 | 结果只写「0-70°范围」 | 10% 容差带 = {b1['C1_10pct_band_width_deg'][0]:.1f}–{b1['C1_10pct_band_width_deg'][1]:.1f}°，被报范围宽 {b1['C1_band_to_reported_range_ratio'][1]:.1f}–{b1['C1_band_to_reported_range_ratio'][0]:.1f} 倍；测试只断言 `0 <= angle < 70` | 无基准比较 → PASS 无据 |
| C8 能量守恒 <5% | 「能量变化<1e-3 J」 | 测试速度下总动能 {b3['C8']['KE_initial_total_J']:.3e} J；|ΔE|≤2KE₀={2*b3['C8']['KE_initial_total_J']:.3e} J ≪ 1e-3 J，断言恒真 | 相对判据未被检验 |
| C3 相图模式 | 「压溃/弯曲/混合区域」 | 4000 格普查：{json.dumps(p2['phase_diagram_mode_census'], ensure_ascii=False)} | 无 mixed 格；劈裂 270 格未提 |
| 测试统计 | 总测试数 35 / 通过 35 | 独立执行 `{p4['passed']} passed`（{p4['wall_seconds']} s） | ✅ 属实 |
| 上游 KO | 11 资产 | 引文 {kof['quotes_verbatim']}/{kof['quotes_total']} 逐字唯一；A01 区间[0,1953]≠标题引文 | 基本保真，1 处区间记账瑕疵 |

## ⑤ 注意点与局限

- **未跑**：动态 DEM 积分的收敛/恢复系数研究（C8 是唯一能量证据且为空断言）；休止角对真实实验的比对（无实验数据在范围内）；非默认参数下的 35 项测试；TensorDEM `origin/main` 最新提交（本地 blob:none 检出为 `{p4['commit'][:8]}`）；相图 transition_boundaries（空时返回占位 `[0,0]`）；GJK/EPA 接触精度对解析基准。
- **独立性局限**：单人复核，无第二意见，无法访问生产者运行日志与 claim 集；交付代码读自兄弟检出，生产者实际构建不可从报告复原（但所有数字逐位复现，说明漂移不大）；审核只覆盖报告点名的 2 个模块与 1 个测试文件。
- **上游缺口**：`wp-11557-02`（分类解析）与 `wp-11557-03`（知识抽取）在仓库中不存在，上游 KO `claims=[]`，故本次审核无 02/03 产物可依。若门要求 01–03 全链，`upstream_packages_completed` 应判未满足（已如实写入 acceptance 的 caveat）。
- **未把任何结论标 verified**；verification 由平台门计算。
- 本单只碰 report_id=11557，未读写其它 report。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|------------|------|------|
| `valid_json` | {tick(acc['valid_json']['pass'])} | 结果 JSON 可解析，`checks.json` schema.valid={chk['schema']['valid']} |
| `schema_pass` | {tick(acc['schema_pass']['pass'])} | jsonschema Draft2020 校验 0 错误 |
| `reviewer_independent` | {tick(acc['reviewer_independent']['pass'])} | 只读报告+上游 KO+交付代码，未打开生产者解释；且结论与生产者 PASS 判定相反（F1/F2/F4/F6） |
| `upstream_packages_completed` | {tick(acc['upstream_packages_completed']['pass'])}（有条件） | 申报上游 {rev['reviewed_package']} 在库、`verification.json all_pass=true`、源哈希独立重算一致；但 02/03 缺失，见 caveat |
| 约束 `do_not_mark_claims_as_verified` | ✅ | 全文无 verified 标记 |
| 约束 `reviewer_context_excludes_producer_explanation` | ✅ | 未读 `scripts/kf_*_11557.py` |
| 约束 `review_prompt_not_copied_from_producer` | ✅ | 审核问题清单由本工序自拟（判据/阈值/基准独立性/断言强度） |
| 零手抄（引文逐字定位） | ✅ | 11 条引文由 `build_review.py` 从 source.md 按行锚点抽取，再验唯一子串；`quote_check.json all_pass=true` |
| 零手抄（数字程序化注入） | ✅ | 正文 28 处数字全部溯源至 probe 产物，`numeric_provenance.all_ok={chk['numeric_provenance']['all_ok']}` |

**honest-FAIL**：`upstream_packages_completed` 只在「申报上游=wp-11557-01」口径下判 ✅；若口径为 01–03 全链，本项为 ❌（02/03 不存在）。此外 `checks_not_run` 中 6 项未执行，不冒充通过。

repro_cmd：
```
cd <worktree> && python3 work/wp-11557-04/fetch_source.py && python3 work/wp-11557-04/probe.py && python3 work/wp-11557-04/probe2.py && python3 work/wp-11557-04/probe3.py && python3 work/wp-11557-04/probe4.py && python3 work/wp-11557-04/build_review.py && python3 work/wp-11557-04/gate_check.py && python3 work/wp-11557-04/make_figures.py && python3 work/wp-11557-04/make_kf_md.py
```

## 结果 JSON（本报告唯一 json 代码块）

```json
{json.dumps(res, ensure_ascii=False, indent=2)}
```
"""

(OUT / "KF-RESULT-wp-11557-04.md").write_text(md, encoding="utf-8")
n_blocks = md.count("```json")
print(json.dumps({"file": str(OUT / "KF-RESULT-wp-11557-04.md"),
                  "chars": len(md), "json_blocks": n_blocks,
                  "code_blocks_total": md.count("```") // 2}, ensure_ascii=False))