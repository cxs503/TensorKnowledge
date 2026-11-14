# KF-RESULT wp-11557-04

**工序**：04-independent-review ｜ **报告**：11557 ｜ **审核对象**：wp-11557-01 ｜ **结论**：`needs-fix`
**源哈希**：`sha256:471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3`（本地重算 = 契约声明 ✅，1953 字符）

## ① 本工序做了什么

对报告 11557《DEM多面体颗粒与冰-结构混合模式失效验证面》(P180W2-N05) 做**独立红队审核**，判定其验收结论（9 条判据、35 项测试）是否语义保真。审核对象为上游工序产物 wp-11557-01，审核上下文**只有**三样东西：报告原文 markdown、上游 KO（asset_manifest / verification）、以及报告所引用的交付代码（TensorDEM `b99c206f`）。**未打开**生产者解释脚本（`scripts/kf_*_11557.py`），以保证独立性。

结论：**needs-fix**。数字没有造假——报告里每个头条数字都能从交付代码逐位复现，`35/35 通过` 也经独立执行证实（`35 passed`，29.55 s）。问题全部在**判定层**：3 条判据被标 PASS 而报告自己的数字已越阈，同一份文档的 §6 又对同 3 条写了「否」；C4 的「Timco 基准」就是模型自身的解析式；C5 的偏差把无量纲比值当百分数印，低报了 100 倍。

## ② 怎么做的（步骤/工具/关键设置）

1. **钉源**：`GET $TENSOR_API_BASE/tensor/reports/11557` 取 `markdown`，本地重算 sha256 与契约比对（1953 字符 / 3262 字节，一致）。
2. **上游 KO 保真度**（`probe.py` A 段）：11 个资产引文逐条做「子串 + 唯一性 + 字符区间切片」三重校验 → 11/11 逐字命中、11/11 唯一、10/11 区间精确；`by_class`/`by_resolution` 计数与资产数自洽（11=11=11）。
3. **闭式复算**（`probe.py` B1 段）：用报告 §1 自报的参数（σc=3 MPa、σf=σt=0.7 MPa、h=1 m、E=5 GPa、D=10 m）与 §2 自报的公式，独立复算 L_b、V_c、R_crush/R_bend/R_split，再与报告数字对照。
4. **跑交付代码**（`probe.py` B2、`probe2.py`、`probe3.py`）：在只读兄弟检出 TensorDEM `b99c206f` 上直接调用 `ice_mixed_mode` 与 `polyhedron`，取回 `validate_against_timco` / `validate_against_lindqvist` / `compute_phase_diagram` 的真实返回值与 4000 个相图格子的模式普查。
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
| F1 | `quote_verdict_row` | `| C4 | V_c vs Timco<30% | PASS | V_c_model=1.3 m/s, V_c_timco=2.76 m/s |` |
| F1 | `quote_error_row` | `| V_c | Timco 2.76 m/s | 53% | 否（经验公式） |` |
| F1 | `quote_verdict_row` | `| C4 | V_c vs Timco<30% | PASS | V_c_model=1.3 m/s, V_c_timco=2.76 m/s |` |
| F1 | `quote_error_row` | `| V_c | Timco 2.76 m/s | 53% | 否（经验公式） |` |
| F2 | `quote_verdict_row` | `| C5 | 阻力vs Lindqvist<20% | PASS | R_model=70.9 MN, R_lindqvist=1.1 MN |` |
| F2 | `quote_error_row` | `| R_total | Lindqvist 1.1 MN | 63% | 否（不同标度） |` |
| F3 | `quote_verdict_row` | `| C1 | 休止角<10%偏差 | PASS | 0-70°范围（角状颗粒典型值） |` |
| F3 | `quote_error_row` | `| 休止角 | 实验30-45° | 0-70° | 否（简化模型） |` |
| F4 | `quote_summary` | `**说明**：误差较大是因为使用简化工程公式。物理机制正确，测试全部通过。` |
| F4 | `quote_test_stats` | `- 总测试数：35` |
| F5 | `quote_verdict_row` | `| C8 | 能量守恒<5% | PASS | 弹性碰撞能量变化<1e-3 J |` |
| F6 | `quote_verdict_row` | `| C3 | 相图≥3模式区域 | PASS | (V,L,σ_f)空间识别出压溃/弯曲/混合区域 |` |
| F7 | `quote_verdict_row` | `| C6 | 单一模式误差检测 | PASS | 低速→压溃，高速→弯曲正确识别 |` |

支撑这些发现的实测值：

| 量 | 报告值 | 独立复算/代码实测 | 判定 |
|----|--------|------------------|------|
| C4 V_c 偏差 vs 自报阈值 30% | `V_c_model=1.3`, `V_c_timco=2.76`（自报行内即 52.9%） | 代码 `relative_error=0.5295` → **52.9%** | PASS 不成立；且基准 `V_c_timco = compute_critical_velocity(config)` 与模型同式 → 循环 |
| C4 基准值来源 | 「Timco 2.76 m/s」 | 同式代入 ρ=917 得 **2.7629 m/s**（相对差 0.105%） | 所谓文献值 = 模型自身输出 |
| C4 偏移构成 | 53% | 1 − 1.3/2.7629 = 52.95%；分类器阈值 0.5·Vc=1.3814，网格 0.1 m/s | 二分之一阈值 + 网格量化，非物理误差 |
| C5 偏差 vs 自报阈值 20% | R_model=70.9 MN, R_lindqvist=1.1 MN | 代码 `R_model=70.9475 MN`, `R_lindqvist=1.1068 MN`, `relative_error=63.1016` → **6310%**（比值当百分数则 63%→100× 低报） | PASS 不成立，且 §6 的 63% 是比值误当百分数 |
| C1 休止角 10% 偏差 | 结果只写「0-70°范围」 | 10% 容差带 = 3.0–4.5°，被报范围宽 15.6–23.3 倍；测试只断言 `0 <= angle < 70` | 无基准比较 → PASS 无据 |
| C8 能量守恒 <5% | 「能量变化<1e-3 J」 | 测试速度下总动能 2.536e-05 J；|ΔE|≤2KE₀=5.072e-05 J ≪ 1e-3 J，断言恒真 | 相对判据未被检验 |
| C3 相图模式 | 「压溃/弯曲/混合区域」 | 4000 格普查：{"crushing": 3020, "splitting": 270, "bending": 710} | 无 mixed 格；劈裂 270 格未提 |
| 测试统计 | 总测试数 35 / 通过 35 | 独立执行 `35 passed`（29.55 s） | ✅ 属实 |
| 上游 KO | 11 资产 | 引文 11/11 逐字唯一；A01 区间[0,1953]≠标题引文 | 基本保真，1 处区间记账瑕疵 |

## ⑤ 注意点与局限

- **未跑**：动态 DEM 积分的收敛/恢复系数研究（C8 是唯一能量证据且为空断言）；休止角对真实实验的比对（无实验数据在范围内）；非默认参数下的 35 项测试；TensorDEM `origin/main` 最新提交（本地 blob:none 检出为 `b99c206f`）；相图 transition_boundaries（空时返回占位 `[0,0]`）；GJK/EPA 接触精度对解析基准。
- **独立性局限**：单人复核，无第二意见，无法访问生产者运行日志与 claim 集；交付代码读自兄弟检出，生产者实际构建不可从报告复原（但所有数字逐位复现，说明漂移不大）；审核只覆盖报告点名的 2 个模块与 1 个测试文件。
- **上游缺口**：`wp-11557-02`（分类解析）与 `wp-11557-03`（知识抽取）在仓库中不存在，上游 KO `claims=[]`，故本次审核无 02/03 产物可依。若门要求 01–03 全链，`upstream_packages_completed` 应判未满足（已如实写入 acceptance 的 caveat）。
- **未把任何结论标 verified**；verification 由平台门计算。
- 本单只碰 report_id=11557，未读写其它 report。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|------------|------|------|
| `valid_json` | ✅ | 结果 JSON 可解析，`checks.json` schema.valid=True |
| `schema_pass` | ✅ | jsonschema Draft2020 校验 0 错误 |
| `reviewer_independent` | ✅ | 只读报告+上游 KO+交付代码，未打开生产者解释；且结论与生产者 PASS 判定相反（F1/F2/F4/F6） |
| `upstream_packages_completed` | ✅（有条件） | 申报上游 wp-11557-01 在库、`verification.json all_pass=true`、源哈希独立重算一致；但 02/03 缺失，见 caveat |
| 约束 `do_not_mark_claims_as_verified` | ✅ | 全文无 verified 标记 |
| 约束 `reviewer_context_excludes_producer_explanation` | ✅ | 未读 `scripts/kf_*_11557.py` |
| 约束 `review_prompt_not_copied_from_producer` | ✅ | 审核问题清单由本工序自拟（判据/阈值/基准独立性/断言强度） |
| 零手抄（引文逐字定位） | ✅ | 11 条引文由 `build_review.py` 从 source.md 按行锚点抽取，再验唯一子串；`quote_check.json all_pass=true` |
| 零手抄（数字程序化注入） | ✅ | 正文 28 处数字全部溯源至 probe 产物，`numeric_provenance.all_ok=True` |

**honest-FAIL**：`upstream_packages_completed` 只在「申报上游=wp-11557-01」口径下判 ✅；若口径为 01–03 全链，本项为 ❌（02/03 不存在）。此外 `checks_not_run` 中 6 项未执行，不冒充通过。

repro_cmd：
```
cd <worktree> && python3 work/wp-11557-04/fetch_source.py && python3 work/wp-11557-04/probe.py && python3 work/wp-11557-04/probe2.py && python3 work/wp-11557-04/probe3.py && python3 work/wp-11557-04/probe4.py && python3 work/wp-11557-04/build_review.py && python3 work/wp-11557-04/gate_check.py && python3 work/wp-11557-04/make_figures.py && python3 work/wp-11557-04/make_kf_md.py
```

## 结果 JSON（本报告唯一 json 代码块）

```json
{
  "package_id": "wp-11557-04",
  "task_type": "04-independent-review",
  "contract_version": "1.0",
  "report_id": "11557",
  "provenance": {
    "source_uri": "tensor://reports/11557",
    "source_field": "markdown",
    "source_hash": "sha256:471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3",
    "source_hash_matches": true,
    "title": "DEM多面体颗粒与冰-结构混合模式失效验证面 (P180W2-N05)",
    "scenario_key": "P180W2-N05",
    "chars": 1953
  },
  "outputs": {
    "review_report.json": {
      "reviewer_role": "red-team-reviewer",
      "reviewed_package": "wp-11557-01",
      "reviewed_report_id": "11557",
      "reviewed_source_hash": "sha256:471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3",
      "verdict": "needs-fix",
      "judge_semantic_fidelity": true,
      "semantic_fidelity": {
        "outcome": "needs-fix",
        "numbers_fabricated": false,
        "summary": "No fabricated number: every headline figure in the report reproduces exactly from the shipped TensorDEM code (V_c_model 1.3, V_c_timco 2.7629, R_model 70.95 MN, R_lindqvist 1.107 MN) and the '35 tests' statistic is confirmed by an independent run (35 passed). The defect is at the interpretive layer: three acceptance rows (C1, C4, C5) are labelled PASS while the report's own numbers violate the report's own thresholds, the same document withdraws all three in section 6, the 'Timco' reference is the model's own closed form, and one deviation (C5) is a dimensionless ratio printed as a percentage, understating it 100x. Two further rows (C3, C8) carry result text that the shipped code contradicts or that cannot bear on the stated criterion.",
        "severity_counts": {
          "high": 3,
          "medium": 4,
          "low": 1
        },
        "blocking_findings": [
          "F1",
          "F2",
          "F3",
          "F4"
        ]
      },
      "scope_reviewed": {
        "report_markdown": "1953 chars, 3262 bytes UTF-8, sha256 recomputed and matched",
        "upstream_ko": "docs/kf/wp-11557-01/{kf_result.wp-11557-01.json,asset_manifest.json,verification.json}",
        "shipped_code": "TensorDEM @ b99c206f: src/tensordem/ice_mixed_mode/__init__.py (731 lines), src/tensordem/polyhedron/__init__.py (708 lines), tests/test_dem_ice.py (662 lines)",
        "read_only": true,
        "not_read_by_design": "producer-side explanation scripts (scripts/kf_*_11557.py) were deliberately not opened, so the review rests on the report text, the upstream KO and the shipped code only"
      },
      "supported_claims": [
        "title/scenario_key/tags of the source report match the contract metadata",
        "the 35-test count and the 35/35 pass statistic reproduce (independent pytest run, 32.24 s)",
        "every headline number in sections 3-6 is a faithful transcription of what the shipped code returns",
        "the upstream KO quotes all 11 assets verbatim and uniquely from the source markdown",
        "C2 (force-chain statistics) is implemented and its asserts are non-degenerate (4 contacts, coordination number > 0, empty case -> 0)",
        "C7 negative controls are implemented as real branches (V->0 pure crushing, sigma_f->inf, D->inf)",
        "the report's own limitation list (sections 5) is honest about the model being an engineering approximation"
      ],
      "findings": [
        {
          "id": "F1",
          "severity": "high",
          "blocking": true,
          "type": "false PASS verdict / criterion violated by the report's own numbers",
          "criterion": "C4",
          "quote_verdict_row": "| C4 | V_c vs Timco<30% | PASS | V_c_model=1.3 m/s, V_c_timco=2.76 m/s |",
          "quote_error_row": "| V_c | Timco 2.76 m/s | 53% | 否（经验公式） |",
          "claim": "C4 (V_c vs Timco <30%) is marked PASS with V_c_model=1.3 m/s vs V_c_timco=2.76 m/s.",
          "measured": {
            "deviation_pct_from_report_numbers": 52.9,
            "criterion_pct": 30.0,
            "criterion_met": false,
            "shipped_validator_relative_error": 0.5295,
            "shipped_V_c_model": 1.3,
            "shipped_V_c_timco": 2.7629
          },
          "why_it_matters": "The report's own two numbers give 52.9% deviation against a declared <30% threshold, and the report's own section 6 already answers 否 for this row. The PASS label in the acceptance table therefore contradicts the same document.",
          "independent_finding_on_the_comparison_itself": {
            "reference_is_the_model": "validate_against_timco() sets V_c_timco = compute_critical_velocity(config), i.e. the 'Timco (2001) reference' is the model's own closed form 0.1*sqrt(sigma_f/(rho_ice*h)); no literature value is stored anywhere.",
            "reference_value": 2.7629,
            "reported_reference": 2.76,
            "reconstruction_rel_err": 0.001049,
            "definitional_offset": "determine_dominant_mode() switches out of crushing at V = 0.5*V_c, so the sweep-reported 'model' critical velocity is a half-threshold quantised to its own grid (0.5*2.7629 = 1.3814 -> reported 1.3 on a 0.1 m/s grid). The residual 53% is 1 - 1.3/2.7629, i.e. factor-two plus grid quantisation, not physics.",
            "rho_needed_to_return_1.3_kg_m3": 4142.0
          },
          "recommendation": "Relabel C4 as FAIL/not-met (53% > 30%), and replace the circular 'Timco reference' with an externally sourced V_c value before any PASS verdict is claimed. If the intent was to test the classifier threshold, state that the compared quantity is 0.5*V_c by construction and the comparison cannot validate anything."
        },
        {
          "id": "F2",
          "severity": "high",
          "blocking": true,
          "type": "false PASS verdict + unit error (ratio reported as percent)",
          "criterion": "C5",
          "quote_verdict_row": "| C5 | 阻力vs Lindqvist<20% | PASS | R_model=70.9 MN, R_lindqvist=1.1 MN |",
          "quote_error_row": "| R_total | Lindqvist 1.1 MN | 63% | 否（不同标度） |",
          "claim": "C5 (resistance vs Lindqvist <20%) is marked PASS with R_model=70.9 MN vs R_lindqvist=1.1 MN.",
          "measured": {
            "deviation_pct_from_report_numbers": 6345.5,
            "deviation_pct_relative_to_model": 98.4,
            "criterion_pct": 20.0,
            "criterion_met": false,
            "shipped_validator_relative_error": 63.1016,
            "shipped_relative_error_as_percent": 6310.2
          },
          "why_it_matters": "C5's stated threshold is exceeded by a factor of ~316 (6310% vs 20%) yet the row says PASS. Section 6 reports '63%', which is exactly the shipped validator's returned value 63.1016 - a dimensionless ratio - printed as if it were a percentage: a silent 100x understatement. The report is internally inconsistent about its own percentage convention (C4's 0.5295 is correctly shown as 53%).",
          "code_docstring_vs_implementation": {
            "docstring_formula": "R = 0.5 · σ_f · h² · (1 + 0.5 · B/h) · f(shape)",
            "implementation": "R_lindqvist = C_L * config.sigma_f * config.h**2 * math.sqrt(config.D / config.h)",
            "detail": "the shipped validator's docstring and body disagree: the body drops the (1 + 0.5*B/h) geometry factor and substitutes sqrt(D/h), with D being the structure width, not a ship beam B"
          },
          "recommendation": "Mark C5 FAIL, report 6310% (or state the alternative basis 98.4% of the model), and make the validator return percent consistently. Note that the Lindqvist expression in the shipped code is a custom stand-in (0.5*sigma_f*h^2*sqrt(D/h)), not the published Lindqvist (1989) level-ice formulation, so this pair is not a valid accuracy benchmark even after the unit fix."
        },
        {
          "id": "F3",
          "severity": "high",
          "blocking": true,
          "type": "PASS verdict with no benchmark comparison at all",
          "criterion": "C1",
          "quote_verdict_row": "| C1 | 休止角<10%偏差 | PASS | 0-70°范围（角状颗粒典型值） |",
          "quote_error_row": "| 休止角 | 实验30-45° | 0-70° | 否（简化模型） |",
          "claim": "C1 (angle of repose within 10% deviation) is marked PASS with '0-70° range (typical for angular particles)'.",
          "measured": {
            "reported_range_deg": 70.0,
            "ten_percent_band_width_deg": [
              3.0,
              4.5
            ],
            "reported_range_over_tolerance_band": [
              23.3,
              15.6
            ],
            "worst_case_deviation_pct_vs_upper_benchmark": 55.6,
            "test_assertions_that_touch_the_repose_angle": [
              "assert result.angle >= 0",
              "assert result.angle < 90",
              "assert result_low.angle >= 0",
              "assert result_high.angle >= 0",
              "assert 0 <= result.angle < 70"
            ]
          },
          "why_it_matters": "C1 declares a relative-deviation criterion but reports only a 0-70° range: no measured value, no reference value, hence no deviation exists to compare. The tolerance band implied by the benchmark (30-45°) is 3.0-4.5° wide, i.e. 15.6-23x narrower than the range offered as evidence. The shipped tests assert only 0 <= angle < 90 / < 70, so nothing in the suite can falsify C1 either.",
          "recommendation": "Report FAIL/not-demonstrated for C1 until a measured repose angle is compared to a cited experimental value; a range spanning 0-70° cannot be inside a +/-10% band."
        },
        {
          "id": "F4",
          "severity": "medium",
          "blocking": true,
          "type": "self-contradiction between acceptance table and error verdict",
          "criterion": "section 3 vs section 6",
          "quote_summary": "**说明**：误差较大是因为使用简化工程公式。物理机制正确，测试全部通过。",
          "quote_test_stats": "- 总测试数：35",
          "claim": "Section 3 marks C1/C4/C5 PASS; section 6 answers 否 for the same three quantities; the closing sentence states conclusions as 'physical mechanism correct, all tests passed'.",
          "measured": {
            "criteria_rows": 9,
            "rows_marked_PASS_but_section6_says_no": [
              "C1",
              "C4",
              "C5"
            ],
            "rows_marked_NA": [
              "C9"
            ],
            "test_count_reported": 35,
            "test_count_verified_in_shipped_suite": 35,
            "pytest_result": "35 passed, returncode 0, wall 29.55 s (independent run, TensorDEM b99c206f)"
          },
          "why_it_matters": "A downstream consumer reading only section 3 would take three criteria as met that the document itself withdraws 20 lines later. The test statistic (35/35) is true but does not support those three verdicts, because the corresponding tests assert only key presence/positivity (see F1/F2/F3).",
          "recommendation": "Derive section 3 verdicts mechanically from the numbers, and either scope the closing sentence to what the tests assert or drop it."
        },
        {
          "id": "F5",
          "severity": "medium",
          "blocking": false,
          "type": "criterion/evidence incommensurable; test assertion is vacuous",
          "criterion": "C8",
          "quote_verdict_row": "| C8 | 能量守恒<5% | PASS | 弹性碰撞能量变化<1e-3 J |",
          "claim": "C8 (energy conservation <5%) is marked PASS on the evidence 'elastic collision energy change <1e-3 J'.",
          "measured": {
            "criterion": "relative (<5%)",
            "evidence_given": "absolute (<1e-3 J)",
            "shipped_test_assertion": "assert energy_change < 1e-3 or KE_initial < 1e-10",
            "particle_mass_kg": 0.0025361507101204104,
            "KE_total_at_test_velocity_J": 2.536150710120411e-05,
            "quoted_1eJ_as_fraction_of_KE_pct": 3943.0,
            "speed_below_which_5pct_band_is_tighter_than_1eJ_m_s": 3.97
          },
          "why_it_matters": "At the test's own velocities the total kinetic energy is 2.54e-5 J, i.e. 39x below the 1e-3 J bound; since |dE| <= 2*KE0 = 5.07e-5 J for any bounded outcome, the assertion cannot fail and says nothing about the <5% relative criterion. A 1e-3 J absolute change would in fact be 78.9% of the kinetic energy at 1 m/s and 3943% of it at 0.1 m/s, so the quoted evidence is compatible with gross violation of C8.",
          "recommendation": "Re-express C8 as a relative drift over a stated impact speed and assert it; keep one absolute row only if the energy scale is printed next to it."
        },
        {
          "id": "F6",
          "severity": "medium",
          "blocking": false,
          "type": "result description contradicted by the shipped code",
          "criterion": "C3",
          "quote_verdict_row": "| C3 | 相图≥3模式区域 | PASS | (V,L,σ_f)空间识别出压溃/弯曲/混合区域 |",
          "claim": "C3 PASS with '(V,L,sigma_f) space identifies crushing / bending / mixed regions'.",
          "measured": {
            "phase_diagram_cell_census": {
              "crushing": 3020,
              "splitting": 270,
              "bending": 710
            },
            "cells_total": 4000,
            "mixed_cells": 0,
            "splitting_cells": 270,
            "mixed_present": false,
            "splitting_present": true
          },
          "why_it_matters": "The criterion (>=3 mode regions) is in fact met by 3 modes, so the PASS verdict is defensible - but the region list in the verdict cell is wrong twice: the 'mixed' region does not occur in any of the 4000 cells, and the splitting region that does occur (270 cells) is never mentioned, although section 2 defines splitting as one of the three failure modes.",
          "recommendation": "Correct the C3 cell to crushing/bending/splitting with cell counts, and state that no mixed region was found at the default configuration."
        },
        {
          "id": "F7",
          "severity": "medium",
          "blocking": false,
          "type": "tautological verification (result restates a hardcoded branch)",
          "criterion": "C6",
          "quote_verdict_row": "| C6 | 单一模式误差检测 | PASS | 低速→压溃，高速→弯曲正确识别 |",
          "claim": "C6 PASS: 'low speed -> crushing, high speed -> bending correctly identified'.",
          "measured": {
            "classifier": "V < 0.5*V_c -> crushing; V > 2.0*V_c -> bending; else min-resistance mode",
            "mode_below_half_Vc_eps": "crushing",
            "mode_above_half_Vc_eps": "bending",
            "V_c_used_by_classifier_m_s": 2.7629,
            "R_crush_at_V0_MN_range": [
              75.0,
              112.5
            ],
            "R_bend_at_V0_MN": 7.2,
            "V_needed_for_a_genuine_resistance_crossover_m_s": 94.2
          },
          "why_it_matters": "The 'identification' is the if-branch itself, and the threshold is derived from the very formula F1 shows to be circular, so C6 is confirmed by construction and is not a test of the physics. In the intermediate band the 'dominant' mode is defined as the lowest-resistance mode, and because R_bend (7.2 MN) is an order below R_crush (75-112.5 MN) for all speeds, bending wins there by that rule alone; a genuine resistance crossover would need ~94 m/s, far outside the ice-structure range the report claims to cover.",
          "recommendation": "Either state C6 as a structural unit test of the branch logic, or drive the mode selection by an independently justified criterion instead of the same V_c."
        },
        {
          "id": "F8",
          "severity": "low",
          "blocking": false,
          "type": "upstream bookkeeping (KO fidelity otherwise clean)",
          "scope": "wp-11557-01 asset_manifest.json",
          "measured": {
            "assets_declared": 11,
            "assets_present": 11,
            "by_class_sum": 11,
            "by_resolution_sum": 11,
            "quotes_total": 11,
            "quotes_verbatim": 11,
            "quotes_unique": 11,
            "quotes_char_range_exact": 10,
            "claimed_claims_extracted": 0
          },
          "detail": "All 11 asset quotes are exact unique substrings of the source markdown and the class/resolution counts sum correctly. One asset (A01, the whole-document asset) declares locator range [0,1953] while its quote is only the title line, so the declared slice is not equal to the declared quote. claims[] is empty, so no claim-level evidence exists downstream of this report.",
          "recommendation": "For document-class assets either store the title-line range or declare the range as covering the whole document explicitly."
        }
      ],
      "acceptance_check": {
        "valid_json": {
          "pass": true,
          "evidence": "validated against schemas/kf_result.v1.schema.json (see checks.json)"
        },
        "schema_pass": {
          "pass": true,
          "evidence": "jsonschema validation of this bundle, 0 errors"
        },
        "reviewer_independent": {
          "pass": true,
          "evidence": "review derived from report markdown + upstream KO + shipped code; producer explanation scripts not opened; findings F1/F2/F4/F6 contradict the producer's PASS verdicts, which a non-independent review would not do"
        },
        "upstream_packages_completed": {
          "pass": true,
          "evidence": "declared upstream wp-11557-01 (01-asset-registration) is present with verification.json all_pass=true and its source hash independently recomputed to the contract value",
          "caveat": "wp-11557-02 (classification/parse) and wp-11557-03 (knowledge extraction) do not exist anywhere in the repository for report 11557, and the upstream KO carries claims=[] - so this review had no 02/03 products to build on. If the gate requires the full 01-03 chain, this acceptance item is unmet."
        }
      },
      "checks_not_run": [
        "dynamic DEM integration quality: no time-stepping convergence or restitution study was run; C8 is the only energy evidence and it is vacuous (F5)",
        "angle of repose against real experimental data: no experimental dataset is in scope, and none is cited with a value",
        "the 35 tests beyond the default IceMixedModeConfig (parameter sweeps / other configurations)",
        "TensorDEM at origin/main tip: the local blob:none checkout is b99c206f (2026-11-14); the producer's exact build is not recoverable from the report",
        "phase-diagram transition boundaries (transition_boundaries returned as a placeholder [0,0] when empty - not audited further)",
        "polyhedron GJK/EPA contact accuracy against analytic sphere-sphere or Minkowski references"
      ],
      "independence_limitations": [
        "single reviewer, no second opinion and no access to the producer's run logs or claim set",
        "shipped code was read from a sibling worktree clone (blob:none, commit b99c206f) rather than from a producer-pinned commit, so drift between the producer's tree and the audited tree cannot be excluded; all reported numbers nevertheless reproduce exactly, which argues against material drift",
        "the code review was limited to the two modules and the test file named in the report; helper modules of tensordem were not audited"
      ],
      "reproduction": {
        "repro_cmd": "cd <worktree> && python3 work/wp-11557-04/fetch_source.py && python3 work/wp-11557-04/probe.py && python3 work/wp-11557-04/probe2.py && python3 work/wp-11557-04/probe3.py && python3 work/wp-11557-04/build_review.py",
        "artifacts": [
          "work/wp-11557-04/source.md",
          "work/wp-11557-04/probe_results.json",
          "work/wp-11557-04/probe2_results.json",
          "work/wp-11557-04/probe3_results.json",
          "work/wp-11557-04/quote_check.json"
        ],
        "requires": "local psql-free access to GET $TENSOR_API_BASE/tensor/reports/11557; sibling TensorDEM checkout at /root/tp-agent/work/m19513 for probes 2/3"
      },
      "disposition": "request-changes"
    },
    "review_events.json": [
      {
        "seq": 1,
        "event": "source_pinned",
        "detail": "GET tensor/reports/11557; sha256 recomputed sha256:471f8b21be2b8a49... match=True; 1953 chars"
      },
      {
        "seq": 2,
        "event": "upstream_ko_ingested",
        "detail": "wp-11557-01 kf_result + asset_manifest + verification.json; claims=[]; verification all_pass=true"
      },
      {
        "seq": 3,
        "event": "probe_quotes",
        "detail": "11/11 upstream quotes verbatim, 11/11 unique, 10/11 char-range exact"
      },
      {
        "seq": 4,
        "event": "probe_closed_form",
        "detail": "C1/C4/C5/C8 re-derived from the report's own formulas and parameters; L_b=14.6848 m, V_c(rho=917)=2.7629 m/s"
      },
      {
        "seq": 5,
        "event": "probe_shipped_code",
        "detail": "TensorDEM b99c206f ice_mixed_mode executed: V_c=2.7629, R_model=70.9475 MN, R_lindqvist=1.1068 MN, relative_error=63.1016 (ratio)"
      },
      {
        "seq": 6,
        "event": "probe_phase_diagram",
        "detail": "4000 cells: {\"crushing\": 3020, \"splitting\": 270, \"bending\": 710}"
      },
      {
        "seq": 7,
        "event": "probe_test_suite",
        "detail": "pytest tests/test_dem_ice.py -> 35 passed (independent run); C1/C4/C5 assertions are presence/positivity only"
      },
      {
        "seq": 8,
        "event": "verdict_issued",
        "detail": "needs-fix; blocking=F1,F2,F3,F4; 3 high / 3 medium / 1 medium-low + 1 low findings"
      }
    ]
  }
}
```
