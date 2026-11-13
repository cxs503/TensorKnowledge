# KF-RESULT wp-12445-01 — report 12445 资产登记（01-asset-registration）

报告标题：**P269W2-N07 EEXI/CII 端到端不确定度传播：六因子蒙特卡洛 · 合规概率 · Sobol 分解** ｜ scenario_key=`green_navigation` ｜ 契约 input.report_id=`12445`

## ① 本工序做了什么

按标准工作包契约 `wp-12445-01`（task_type=`01-asset-registration`, lane C）对 **report_id=12445 一份报告**做源资产登记，
不做知识抽取、不做报告分类（契约 `objective.classify_report_type: false`）：

1. 从平台读取 `tensor://reports/12445` 的 `markdown` 字段，独立重算字节哈希，与契约 `source_hash` 逐字节比对；
2. 把报告正文所声明的**附件/工件**（5 张图、产物目录、源码/测试/脚本/文档、分支与 commit 指针、被点名的缺陷函数、以及报告自陈缺失的规则要求值层）逐条登记为 asset，每条带**逐字引文 + 字符区间 + 行号**定位；
3. 另登记 10 条正文锚点（anchor），供下游工序引用时不靠记忆重述；
4. 按 `no_forced_claim_generation`，**claims = 0**（空数组是本工序的合法完整结果，不是缺项）。

分母边界：只碰 report_id=12445，未读/写任何其它 report_id；不改写上游产物；**不标注任何结论为 verified**
（verification 由平台门计算）。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/脚本 | 关键设置 |
|---|---|---|
| 取源 | `scripts/kf_wp12445_fetch.py` | `GET /tensor/reports/12445`，Bearer 取自 env（无硬编码凭据），落 `runs/wp-12445-01/report_12445.md`（原始 UTF-8 字节） |
| 登记 | `scripts/kf_wp12445_register.py` | 每个 quote 断言 `md.count(quote)==1`；char_span 写入前回读校验；jsonschema(Draft 2020-12) 校 `schemas/kf_result.v1.schema.json` 与本包 pin 的 `docs/kf/wp-12445-01/asset_manifest.schema.json` |
| 独立复核 | `scripts/kf_wp12445_verify.py` | **不信任本地副本**：重新拉取 API 原文 + 重算 sha256 + 重解每个定位；11 项门全绿才退出 0 |
| 回归测试 | `pytest -q tests/test_kf_wp12445_01.py` | 10 例：哈希/字数钉死、定位精确解析且唯一、envelope 内嵌 manifest 逐字节相等、claim 规则、schema、单报告边界 |
| 作图 | `scripts/kf_wp12445_figure.py` | matplotlib Agg；A 面板=资产按类别×resolution 堆叠，B 面板=每条资产在正文 char 轴上的实测区间 |

**定位口径（可复核）**：`start_char/end_char` 是对 markdown **解码后字符串**（非字节）的偏移，
`unique=true` 的判定是 `md.count(quote)==1`；因此任何正文改动都会让定位"漂移可检测"而非静默错位。

## ③ 产出物清单（文件名 → 要点）

| 产物 | 要点 |
|---|---|
| `docs/kf/wp-12445-01/asset_manifest.json` | asset_manifest.v1 主产物：source(哈希/chars/bytes) + 14 条资产 + 10 条锚点 + counts + integrity + claims=[] |
| `docs/kf/wp-12445-01/kf_result.json` | 交付信封 kf_result.v1（package_id/task_type/report_id/provenance/outputs），outputs 内嵌上述 manifest |
| `docs/kf/wp-12445-01/asset_manifest.schema.json` | 本包 pin 的 manifest schema（仓内 `schemas/asset_manifest.v1.schema.json` 的 const 钉死在 wp-448-01，无法复用；字段名/枚举保持一致，仅重钉 package/report const） |
| `docs/kf/wp-12445-01/verify_log.json` | 登记期机器日志：哈希/字数/定位唯一性/图数一致性/两套 schema 结果 + acceptance 逐项布尔 |
| `runs/wp-12445-01/report_12445.md`、`report_12445.json`、`fetch_meta.json` | 源原文原始字节副本与抓取元数据（含平台 title/figures/tags） |
| `runs/wp-12445-01/verify_independent.json` | 独立复核日志（live API 重取 + 重算哈希 + 重解定位） |
| `docs/kf/wp-12445-01/figures/asset_registration_overview.png` | 图 1：资产类别×resolution 分布 + 正文 char 轴定位图 |
| `docs/kf/KF-RESULT-wp-12445-01.md` | 本报告（含唯一 JSON 结果块） |
| `scripts/kf_wp12445_{fetch,register,verify,figure,report}.py`、`tests/test_kf_wp12445_01.py` | 一键复跑链 + 回归测试 |

**复跑（worktree 根）**：

```bash
python3 scripts/kf_wp12445_fetch.py && python3 scripts/kf_wp12445_register.py \
  && python3 scripts/kf_wp12445_verify.py && python3 scripts/kf_wp12445_figure.py \
  && python3 -m pytest -q tests/test_kf_wp12445_01.py \
  && python3 scripts/kf_wp12445_report.py --publish
```

## ④ 证据定位表（claim/字段 → 原文引文片段）

### 4.1 源身份（字段 → 引文/哈希）

| 字段 | 值 | 依据 |
|---|---|---|
| source_uri | `tensor://reports/12445` | 契约 input.source_uri |
| source_field | `markdown` | 契约 input.source_field |
| source_hash（契约） | `sha256:f86e8247d5dff43152a883b11207b09d96d5dd70892d7f62cab187746f85f23f` | 平台原文重算 = 契约值（`hash_matches_contract=True`） |
| chars / bytes_utf8 | 3554 / 5388 | 契约 chars=3554 一致（中文 1 字符=3 字节，故 bytes>chars） |
| title | P269W2-N07 EEXI/CII 端到端不确定度传播：六因子蒙特卡洛 · 合规概率 · Sobol 分解 | 平台 record title 与契约 title 相等：`True` |
| scenario_key | `green_navigation` | 平台 record scenario_key 相等：`True` |
| 图 | 5 张（record figures[]） | 正文自陈「（JSON + 5 图）」 ⇒ 图数与 record 5 张一致 |

### 4.2 资产清单（14 条，全部逐字定位且唯一）

| asset_id | class | object | section | line | char span | resolution | check result |
|---|---|---|---|---|---|---|---|
| A01 | figure | `fig1_eexi_pdf.png` | 产物（§3/§4 之后，第 43 行） | L43 | [3485,3519) | referenced_unresolved | unresolved |
| A02 | figure | `fig2_cii_pdf.png` | 产物（第 43 行） | L43 | [3485,3519) | referenced_unresolved | unresolved |
| A03 | figure | `fig3_sobol.png` | 产物（第 43 行） | L43 | [3485,3519) | referenced_unresolved | unresolved |
| A04 | figure | `fig4_convergence_negative_control.png` | 产物（第 43 行） | L43 | [3485,3519) | referenced_unresolved | unresolved |
| A05 | figure | `fig5_surrogate_verification.png` | 产物（第 43 行） | L43 | [3485,3519) | referenced_unresolved | unresolved |
| A06 | artifact_bundle | `artifacts/P269W2_N07/ (JSON + 5 图)` | 产物（第 43 行） | L43 | [3484,3519) | referenced_unresolved | unresolved |
| A07 | source_module | `backend/services/green_uncertainty.py` | 产物（第 43 行） | L43 | [3259,3298) | referenced_unresolved | unresolved |
| A08 | api_router | `backend/api/green_uncertainty.py` | 产物（第 43 行） | L43 | [3299,3333) | referenced_unresolved | unresolved |
| A09 | test_module | `backend/tests/test_green_uncertainty.py` | 产物（第 43 行）；§3 判据 A7 | L43 | [3334,3375) | referenced_unresolved | unresolved |
| A10 | repro_script | `scripts/run_green_uncertainty_p269w2_n07.py` | 产物（第 43 行） | L43 | [3376,3421) | referenced_unresolved | unresolved |
| A11 | documentation | `docs/green_navigation/P269W2_N07_uncertainty_propagation.md` | 产物（第 43 行） | L43 | [3422,3483) | referenced_unresolved | unresolved |
| A12 | provenance_pointer | `branch agent/m10831 @ commit 98efbb418` | 产物（第 43 行） | L43 | [3520,3552) | resolved_in_source | resolved |
| A13 | code_pointer | `api/green_shipping._gn_attained_index` | §4 顺带修掉的真缺陷 | L28 | [2112,2151) | referenced_unresolved | unresolved |
| A14 | withheld_dependency | `规则要求值层（EEXI_required / CII_required 的规则依据）` | §5 注意点 / 局限（末句） | L31 | [2769,2809) | declared_absent | absent |

resolution 口径：`resolved_in_source`=对象在 markdown 内可解析（本包仅 commit 指针文本）；
`referenced_unresolved`=报告点名了它，但其字节/对象不在 markdown 内（图与源仓路径属此类）；
`declared_absent`=报告自陈缺失、本工序不得补齐（规则要求值层）。

### 4.3 正文锚点（10 条）

| field | 原文引文（逐字） | char span | line |
|---|---|---|---|
| report_title | P269W2-N07 EEXI/CII 端到端不确定度传播成熟化 | [3,35) | L1 |
| design_point | Lpp×B×T = 180×32×11.5 m，Cb=0.82，Capacity=35000 DWT | [103,153) | L4 |
| eexi_required | EEXI_required = 5.2318 gCO2/(t·nm) | [217,251) | L6 |
| cii_required | CII_required(2025) = 6.4397 gCO2/(t·nm) | [252,291) | L6 |
| mc_settings | MC N=20000（seed=20261110） | [1019,1044) | L13 |
| reduction_chain | 归约误差对**全 Holtrop+二分**逐样本复算实测 | [980,1008) | L12 |
| figure_count | （JSON + 5 图） | [3507,3519) | L43 |
| deliverable_list | 产物：`backend/services/green_uncertainty.py` | [3256,3298) | L43 |
| withheld_scope | **要求值层与合规概率按 WITHHELD 处理** | [2769,2795) | L31 |
| provenance | 分支 agent/m10831，commit 98efbb418 | [3520,3552) | L43 |

### 4.4 反查（claim → 证据）

本工序**无 claim**（`claims=[]`，契约允许）。理由：task_type=01 只登记资产、`classify_report_type=false`、
`no_forced_claim_generation=true`——为凑指标而造 claim 会污染下游抽取工序的证据链。故「所有 claim 均有证据或显式
unresolved 状态」在本包是**空集真值**（vacuously true），并已由 `tests/test_kf_wp12445_01.py::test_claims_empty_or_evidenced_and_never_verified` 机器断言。

## ⑤ 注意点与局限

1. **登记 ≠ 核验**。14 条资产里 12 条 `referenced_unresolved`：报告点名了它们的路径，但字节不在 markdown 内，也不在本工作树
   （本工作树是 TensorKnowledge，源仓是 ship-performance-platform）。本工序没有跨仓拉取，也没有把"路径存在"冒充"内容正确"。
2. **图片只到 record 级身份**。5 张图的文件名/图注由平台 record 的 `figures[]` 给出，PNG 字节未随 markdown；
   所以本文只声明"图数一致 + 身份可对齐"，不声明图内容与正文数值一致（那属下游核验工序）。
3. **commit 指针只有 9 位**。报告给的是短哈希 `98efbb418` + 分支 `agent/m10831`；仅登记指针文本逐字定位命中，
   未在本仓解析 commit 对象，故**不可**据此宣称复现过源仓代码状态。
4. **规则要求值层是 WITHHELD**。报告自陈"规则系数离线转录不可复核"，故 `EEXI_required`/`CII_required` 的规则依据
   登记为 `declared_absent`。任何"合规概率"结论的**规则符合性**均不在本工序可判范围内（契约 `do_not_invent_missing_information`）。
5. **char 偏移依赖解码口径**。定位是对 UTF-8 解码后字符串的偏移；若下游用字节偏移复用，必须先按同口径换算，否则错位。
6. **schema 权威性**。仓内 `schemas/asset_manifest.v1.schema.json` 的 const 钉在 wp-448-01（不可复用），本包另 pin 了一份；
   若平台侧存在权威 asset_manifest schema 且与本 pin 有差异，**以平台为准**，本产物须回改。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | manifest/envelope 均由 `json.loads` 读回并通过 schema 校验 |
| schema_pass | ✅ | kf_result.v1.schema.json 校验 `True`；本包 manifest schema 校验 `True` |
| source_locator_resolvable | ✅ | 登记期断言 + live API 独立复核：`verify_independent.asset_locators.all_resolve=True`，`anchor_locators.all_resolve=True`（14+10 条） |
| source_hash_matches | ✅ | 本地重算 `f86e8247d5dff43152a883b11207b09d96d5dd70892d7f62cab187746f85f23f` == 契约；live 重取重算 `f86e8247d5dff43152a883b11207b09d96d5dd70892d7f62cab187746f85f23f` 同一值（`hash_contract_match=True`） |
| no_duplicate_ids | ✅ | A01–A14 唯一；`counts` 与明细互校（`counts_consistent=True`） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[] ⇒ 空集真；pytest 断言 claim 不得带 "verified" |
| 边界：只碰 report_id=12445 | ✅ | 脚本仅请求 `/tensor/reports/12445`；`test_no_cross_report_reference_in_scripts` 扫 scripts 目录 |
| 不标 verified | ✅ | manifest/envelope 中无 "verified" 字样（pytest 断言） |

### 误差判定（本工序无物理算例，按等价判据逐项）

本工序产出的是**登记物**，不计算阻力/推进/耐波等物理量，故"关键量 vs 基准 <3%"映射为可机检的等价判据：

| 关键量 vs 基准 | 实测偏差 | 门限 | 是否达标 |
|---|---|---|---|
| markdown sha256 vs 契约 source_hash | 0 bit（f86e8247d5dff431… 完全相同） | 逐位相等 | 是 |
| chars vs 契约 chars（3554） | 0 | 逐字相等 | 是 |
| 定位解析失败数 vs 24 条定位 | 0 | 0 | 是 |
| 图数（正文「5 图」vs record figures[] vs 登记条目） | 0（5/5/5） | 0 | 是 |
| schema 违例数（两套 schema） | 0 | 0 | 是 |

**显式回答"是否<3%"**：本工序**无数值物理量可供 3% 判定**（无基准即无 3% 结论），替代判据全部为 0 偏差/零违例，
故自检全绿；但这**不等于**对报告 12445 的 EEXI/CII 数值链做过复核——那需要复跑源仓计算，不在本工作包范围（见 ⑤.1/⑤.4）。

## 结果块（本报告唯一 JSON 代码块）

```json
{
  "package_id": "wp-12445-01",
  "task_type": "01-asset-registration",
  "report_id": "12445",
  "provenance": {
    "source_hash": "sha256:f86e8247d5dff43152a883b11207b09d96d5dd70892d7f62cab187746f85f23f",
    "source_field": "markdown",
    "producer": "TENSOR_AGENT_USER via scripts/kf_wp12445_fetch.py + scripts/kf_wp12445_register.py",
    "emitted_at": "2026-11-12",
    "notes": "按 char_span 逐字定位；claims=[] 为契约允许（本工序不抽取、不分类）。"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-12445-01",
      "task_type": "01-asset-registration",
      "report_id": "12445",
      "source": {
        "uri": "tensor://reports/12445",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "f86e8247d5dff43152a883b11207b09d96d5dd70892d7f62cab187746f85f23f",
        "chars": 3554,
        "bytes_utf8": 5388,
        "title": "P269W2-N07 EEXI/CII 端到端不确定度传播：六因子蒙特卡洛 · 合规概率 · Sobol 分解",
        "platform_title": "P269W2-N07 EEXI/CII 端到端不确定度传播：六因子蒙特卡洛 · 合规概率 · Sobol 分解",
        "title_matches_contract": true,
        "scenario_key": "green_navigation",
        "platform_scenario_key": "green_navigation",
        "platform_figures": [
          {
            "name": "fig1_eexi_pdf.png",
            "caption": "EEXI_attained 概率密度与累积分布：MC 直方图（N=20000）+ 对数正态拟合（σ_ln=0.0378）+ 要求值线（标定后与名义值重合）；CDF 在要求值处的高度即合规概率"
          },
          {
            "name": "fig2_cii_pdf.png",
            "caption": "CII_attained 概率密度与累积分布：分布显著更宽（CV=17.1%），因气象服务增阻与营运航速剖面全部进入"
          },
          {
            "name": "fig3_sobol.png",
            "caption": "Sobol 方差分解：EEXI 由主机（0.759）与阻力（0.185）主导、几何 <1%；CII 由操作航速剖面（0.599）与气象（0.224）主导；绿柱为一阶 delta 法解析份额"
          },
          {
            "name": "fig4_convergence_negative_control.png",
            "caption": "左：A5 收敛性（均值 ±1SE 收敛到 N=2e5 参考）；右：A6 负控（CV 随 σ 线性归零，σ=0 时 PDF 为 δ 函数）"
          },
          {
            "name": "fig5_surrogate_verification.png",
            "caption": "归约链自证：随机样本上归约链 vs 全 Holtrop+二分的相对偏差（EEXI 6.3e-5、CII 2.5e-4，判据 1e-3）"
          }
        ],
        "platform_tags": [
          "EEXI",
          "CII",
          "不确定度传播",
          "蒙特卡洛",
          "合规概率",
          "Sobol",
          "P269W2-N07",
          "green-shipping"
        ]
      },
      "counts": {
        "assets": 14,
        "by_class": {
          "figure": 5,
          "artifact_bundle": 1,
          "source_module": 1,
          "api_router": 1,
          "test_module": 1,
          "repro_script": 1,
          "documentation": 1,
          "provenance_pointer": 1,
          "code_pointer": 1,
          "withheld_dependency": 1
        },
        "by_resolution": {
          "referenced_unresolved": 12,
          "resolved_in_source": 1,
          "declared_absent": 1
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 12,
        "declared_absent": 1,
        "anchors": 10
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "figure",
          "label": "fig1_eexi_pdf.png",
          "in_report_section": "产物（§3/§4 之后，第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform record figures[] entry name=='fig1_eexi_pdf.png' present with caption; PNG bytes not embedded in markdown",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3485,
            "end_char": 3519,
            "start_line": 43,
            "end_line": 43,
            "quote": "artifacts/P269W2_N07/`（JSON + 5 图）",
            "unique": true
          },
          "note": "EEXI PDF/CDF 图。身份与图注由平台 record（figures[]）给出；逐图字节不可从 markdown 取得，本工序不做图内容核验（属下游抽取/审计工序）。"
        },
        {
          "asset_id": "A02",
          "asset_class": "figure",
          "label": "fig2_cii_pdf.png",
          "in_report_section": "产物（第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform record figures[] entry name=='fig2_cii_pdf.png' match; PNG bytes not in markdown",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3485,
            "end_char": 3519,
            "start_line": 43,
            "end_line": 43,
            "quote": "artifacts/P269W2_N07/`（JSON + 5 图）",
            "unique": true
          },
          "note": "CII PDF/CDF 图；同为 record 级身份，字节未随 markdown。"
        },
        {
          "asset_id": "A03",
          "asset_class": "figure",
          "label": "fig3_sobol.png",
          "in_report_section": "产物（第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform record figures[] entry name=='fig3_sobol.png' match; PNG bytes not in markdown",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3485,
            "end_char": 3519,
            "start_line": 43,
            "end_line": 43,
            "quote": "artifacts/P269W2_N07/`（JSON + 5 图）",
            "unique": true
          },
          "note": "Sobol 方差分解图；与正文 Sobol 表存在对应关系，但对应关系核验不属本工序。"
        },
        {
          "asset_id": "A04",
          "asset_class": "figure",
          "label": "fig4_convergence_negative_control.png",
          "in_report_section": "产物（第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform record figures[] entry name=='fig4_convergence_negative_control.png' match; PNG bytes not in markdown",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3485,
            "end_char": 3519,
            "start_line": 43,
            "end_line": 43,
            "quote": "artifacts/P269W2_N07/`（JSON + 5 图）",
            "unique": true
          },
          "note": "A5 收敛 + A6 负控图；record 级身份。"
        },
        {
          "asset_id": "A05",
          "asset_class": "figure",
          "label": "fig5_surrogate_verification.png",
          "in_report_section": "产物（第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform record figures[] entry name=='fig5_surrogate_verification.png' match; PNG bytes not in markdown",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3485,
            "end_char": 3519,
            "start_line": 43,
            "end_line": 43,
            "quote": "artifacts/P269W2_N07/`（JSON + 5 图）",
            "unique": true
          },
          "note": "归约链自证图；record 级身份。图数合计 5，与正文“5 图”声明一致。"
        },
        {
          "asset_id": "A06",
          "asset_class": "artifact_bundle",
          "label": "artifacts/P269W2_N07/ (JSON + 5 图)",
          "in_report_section": "产物（第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('artifacts/P269W2_N07') in this worktree",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3484,
            "end_char": 3519,
            "start_line": 43,
            "end_line": 43,
            "quote": "`artifacts/P269W2_N07/`（JSON + 5 图）",
            "unique": true
          },
          "note": "产物目录：JSON 数值工件 + 5 图。本工作树（TensorKnowledge）只持有报告登记物，该目录属源仓 ship-performance-platform；未跨仓拉取，不冒充已核验。"
        },
        {
          "asset_id": "A07",
          "asset_class": "source_module",
          "label": "backend/services/green_uncertainty.py",
          "in_report_section": "产物（第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('backend/services/green_uncertainty.py') in this worktree",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3259,
            "end_char": 3298,
            "start_line": 43,
            "end_line": 43,
            "quote": "`backend/services/green_uncertainty.py`",
            "unique": true
          },
          "note": "六因子 MC / Sobol / 归约链实现。路径相对源仓根；本工作树无 backend/ 目录。"
        },
        {
          "asset_id": "A08",
          "asset_class": "api_router",
          "label": "backend/api/green_uncertainty.py",
          "in_report_section": "产物（第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('backend/api/green_uncertainty.py') in this worktree",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3299,
            "end_char": 3333,
            "start_line": 43,
            "end_line": 43,
            "quote": "`backend/api/green_uncertainty.py`",
            "unique": true
          },
          "note": "绿色航行不确定度 API 路由。"
        },
        {
          "asset_id": "A09",
          "asset_class": "test_module",
          "label": "backend/tests/test_green_uncertainty.py",
          "in_report_section": "产物（第 43 行）；§3 判据 A7",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('backend/tests/test_green_uncertainty.py') in this worktree",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3334,
            "end_char": 3375,
            "start_line": 43,
            "end_line": 43,
            "quote": "`backend/tests/test_green_uncertainty.py`",
            "unique": true
          },
          "note": "37 例 pytest 的载体（A7 判据）；本工序未执行该测试（跨仓），不得视为已复现。"
        },
        {
          "asset_id": "A10",
          "asset_class": "repro_script",
          "label": "scripts/run_green_uncertainty_p269w2_n07.py",
          "in_report_section": "产物（第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('scripts/run_green_uncertainty_p269w2_n07.py') in this worktree",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3376,
            "end_char": 3421,
            "start_line": 43,
            "end_line": 43,
            "quote": "`scripts/run_green_uncertainty_p269w2_n07.py`",
            "unique": true
          },
          "note": "一键复现脚本（重计算入口）。"
        },
        {
          "asset_id": "A11",
          "asset_class": "documentation",
          "label": "docs/green_navigation/P269W2_N07_uncertainty_propagation.md",
          "in_report_section": "产物（第 43 行）",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('docs/green_navigation/P269W2_N07_uncertainty_propagation.md') in this worktree",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3422,
            "end_char": 3483,
            "start_line": 43,
            "end_line": 43,
            "quote": "`docs/green_navigation/P269W2_N07_uncertainty_propagation.md`",
            "unique": true
          },
          "note": "长文报告（本 markdown 为其摘要版）。"
        },
        {
          "asset_id": "A12",
          "asset_class": "provenance_pointer",
          "label": "branch agent/m10831 @ commit 98efbb418",
          "in_report_section": "产物（第 43 行）",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "pointer string present verbatim and unique in markdown (commit object itself is in the source repo, not resolvable here)",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3520,
            "end_char": 3552,
            "start_line": 43,
            "end_line": 43,
            "quote": "分支 agent/m10831，commit 98efbb418",
            "unique": true
          },
          "note": "仅登记指针文本本身可解（逐字定位命中）。commit 对象未在本仓拉取，故其内容与 40 位全哈希不在本工序核验范围（报告只给 9 位短哈希）。"
        },
        {
          "asset_id": "A13",
          "asset_class": "code_pointer",
          "label": "api/green_shipping._gn_attained_index",
          "in_report_section": "§4 顺带修掉的真缺陷",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('backend/api/green_shipping.py') in this worktree",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2112,
            "end_char": 2151,
            "start_line": 28,
            "end_line": 28,
            "quote": "`api/green_shipping._gn_attained_index`",
            "unique": true
          },
          "note": "被点名的分母量纲缺陷函数（报告称已改为 kn 口径并加回归守卫）。本工序不评判该修复，只登记指针与定位。"
        },
        {
          "asset_id": "A14",
          "asset_class": "withheld_dependency",
          "label": "规则要求值层（EEXI_required / CII_required 的规则依据）",
          "in_report_section": "§5 注意点 / 局限（末句）",
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report text declares the requirement-value layer WITHHELD; no rule document/coefficient table is attached in markdown",
            "result": "absent"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2769,
            "end_char": 2809,
            "start_line": 31,
            "end_line": 31,
            "quote": "**要求值层与合规概率按 WITHHELD 处理**（规则系数离线转录不可复核）",
            "unique": true
          },
          "note": "报告自陈：规则系数离线转录不可复核。按 preserve_uncertainty 如实登记为缺失依赖，不补齐、不推断。"
        }
      ],
      "anchors": [
        {
          "anchor_id": "report_title",
          "field": "报告标题",
          "quote": "P269W2-N07 EEXI/CII 端到端不确定度传播成熟化",
          "start_char": 3,
          "end_char": 35,
          "start_line": 1,
          "unique": true
        },
        {
          "anchor_id": "design_point",
          "field": "算例几何/参数",
          "quote": "Lpp×B×T = 180×32×11.5 m，Cb=0.82，Capacity=35000 DWT",
          "start_char": 103,
          "end_char": 153,
          "start_line": 4,
          "unique": true
        },
        {
          "anchor_id": "eexi_required",
          "field": "EEXI 要求值",
          "quote": "EEXI_required = 5.2318 gCO2/(t·nm)",
          "start_char": 217,
          "end_char": 251,
          "start_line": 6,
          "unique": true
        },
        {
          "anchor_id": "cii_required",
          "field": "CII 要求值(2025)",
          "quote": "CII_required(2025) = 6.4397 gCO2/(t·nm)",
          "start_char": 252,
          "end_char": 291,
          "start_line": 6,
          "unique": true
        },
        {
          "anchor_id": "mc_settings",
          "field": "MC 规模与种子",
          "quote": "MC N=20000（seed=20261110）",
          "start_char": 1019,
          "end_char": 1044,
          "start_line": 13,
          "unique": true
        },
        {
          "anchor_id": "reduction_chain",
          "field": "归约链自证口径",
          "quote": "归约误差对**全 Holtrop+二分**逐样本复算实测",
          "start_char": 980,
          "end_char": 1008,
          "start_line": 12,
          "unique": true
        },
        {
          "anchor_id": "figure_count",
          "field": "图数声明",
          "quote": "（JSON + 5 图）",
          "start_char": 3507,
          "end_char": 3519,
          "start_line": 43,
          "unique": true
        },
        {
          "anchor_id": "deliverable_list",
          "field": "产物清单起始",
          "quote": "产物：`backend/services/green_uncertainty.py`",
          "start_char": 3256,
          "end_char": 3298,
          "start_line": 43,
          "unique": true
        },
        {
          "anchor_id": "withheld_scope",
          "field": "WITHHELD 范围",
          "quote": "**要求值层与合规概率按 WITHHELD 处理**",
          "start_char": 2769,
          "end_char": 2795,
          "start_line": 31,
          "unique": true
        },
        {
          "anchor_id": "provenance",
          "field": "来源分支/commit",
          "quote": "分支 agent/m10831，commit 98efbb418",
          "start_char": 3520,
          "end_char": 3552,
          "start_line": 43,
          "unique": true
        }
      ],
      "claims": [],
      "claims_note": "任务类型 01 只登记资产，不做抽取与分类（objective.classify_report_type=false）；按 no_forced_claim_generation，claims=[] 为合法完整结果。",
      "integrity": {
        "quote_uniqueness": true,
        "hash_recomputed_locally": "f86e8247d5dff43152a883b11207b09d96d5dd70892d7f62cab187746f85f23f",
        "hash_matches_contract": true,
        "locator_method": "char_span over utf-8 decoded markdown; uniqueness = exact match count == 1",
        "no_cross_report_access": true
      }
    }
  }
}
```
