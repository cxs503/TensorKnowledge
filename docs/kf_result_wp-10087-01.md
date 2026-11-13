# KF-RESULT wp-10087-01

> 工作包 `wp-10087-01` · 工序 `01-asset-registration` · lane C · 源 `tensor://reports/10087`（report_id=10087）
> 交付仓库 TensorKnowledge · status=draft · 本报告未把任何结论标为 verified（verification 由平台门计算）
> tags: `kf-wp:wp-10087-01` · `01-asset-registration` · `report:10087` · `lane:C` · `draft`

## ① 本工序做了什么

登记 report_id=10087 这一份报告的**源资产**：确认 report_id 与其 markdown 的字节哈希，把 markdown 中可解析的章节/公式/表格/图/声明工件切出定位区间，产出 `asset_manifest.json` 与 `kf_result.v1` 信封。**不做抽取、不生成 claim**（契约 `objective.classify_report_type=false`，`claims` 允许为空数组，故 `claims=[]`：不为凑指标造知识）。

## ② 怎么做的（步骤/工具/关键设置）

1. `GET http://127.0.0.1:8010/api/v1/tensor/reports/10087`（Bearer=agent token）取 `markdown`；脚本先断言返回记录的 `id` 等于 10087，否则拒绝继续——从根上杜绝读到/写到别的 report_id。
2. 对 markdown 的 UTF-8 字节重算 sha256，与契约 `source_hash` 比对（相等才继续）。
3. 资产清单以**行区间**声明，引文由 `md[start:end]` **机器切片**得到，绝不重敲；切片后再要求 `md.count(quote)==1`（唯一）与 `md.find(quote)==start_char`（唯一命中同一位置），否则脚本报错退出。
4. 图资产（A20–A23）的图本体在平台记录 `figures[]`，正文只有一行占位（A19）；因此其 markdown 定位共用 A19 的 span，图身份由 `platform_figure` 字段（index/name/caption）绑定。
5. 原文声明但不在报告记录内的工件（`src/tensordem/granule_crush.py`、`tests/test_granule_crush.py`）标 `referenced_unresolved`：只登记「原文这样说」，不主张文件存在、不主张行数/用例数属实。
6. 输出 `asset_manifest.json` / `locator_check.json` / `source.md`（逐字副本）/ `sha256.txt` / `kf_result.json`，再用 `schemas/kf_result.v1.schema.json`（jsonschema 4.26.0）校验信封并跑 26 项验收不变量（脚本级 + 报告级，逐条见 verify 输出）。

工具链：Python 3.11 + jsonschema 4.26.0 + matplotlib（图）；无网络外呼，除平台自身 API。

### 资产计数

| 指标 | 值 |
|---|---|
| 资产总数 | 24 |
| by_class: code_artifact | 1 |
| by_class: figure | 4 |
| by_class: figure_reference | 1 |
| by_class: formula | 4 |
| by_class: method | 4 |
| by_class: result_statement | 2 |
| by_class: section_heading | 1 |
| by_class: table | 6 |
| by_class: test_artifact | 1 |
| by_resolution: referenced_unresolved | 2 |
| by_resolution: resolved_in_source | 22 |
| 引用但不可解析（referenced_unresolved） | 2 |
| 声明缺失（declared_absent） | 0 |

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-10087-01/asset_manifest.json` | 契约声明的唯一输出：24 条资产 + 计数 + integrity 三元组 + `claims=[]` |
| `docs/kf/wp-10087-01/locator_check.json` | 24 条引文的可解析性明细（char 区间/行区间/出现次数/切片一致性） |
| `docs/kf/wp-10087-01/kf_result.json` | `kf_result.v1` 信封（package_id/task_type/report_id/provenance/outputs/claims） |
| `docs/kf/wp-10087-01/source.md` | 源 markdown 逐字副本（离线复核用，sha256 见 `sha256.txt`） |
| `docs/kf/wp-10087-01/sha256.txt` | 重算摘要：`6ed122a8092e41f05bebbb099ce1406a77ae3504f97785c7501c220f79310f72  source.md` |
| `docs/kf/wp-10087-01/fig1_asset_inventory.png` | 资产计数条形图（按 class / resolution，数值全部来自 manifest） |
| `docs/kf/wp-10087-01/fig2_source_coverage.png` | markdown 139 行 × 字符轴上的定位覆盖条带（哪段被登记、哪段未登记） |
| `docs/kf_result_wp-10087-01.md` | 本报告（正文 + 唯一一个 json 代码块） |

## ④ 证据定位表

| claim/字段 | 原文引文片段（逐字，机器切片） | 定位 |
|---|---|---|
| A01 section_heading | `## ① 案例介绍` | char [64,74) / L4–4 |
| A02 formula | `$$\sigma_f(V) = \sigma_0 \left(\frac{V}{V_0}\right)^{-1/m}$$` | char [169,230) / L9–9 |
| A03 formula | `$$P_f(\sigma, V) = 1 - \exp\left[-\left(\frac{\sigma}{\sigma_0}\right)^m \frac{V}{V_0}\right]$$` | char [231,327) / L11–11 |
| A04 formula | `子粒粒径服从Gaudin-Schuhmann分布：F(d) = (d/d_max)^α` | char [475,519) / L19–19 |
| A05 table | `| 参数 | 石英砂 | 石灰岩 | ⏎ |------|--------|--------| ⏎ | 密度 ρ [kg/m³] | 2650 | 2500 | ⏎ | 杨氏模量 E [GPa] | 37.0 | 50.…` | char [529,823) / L23–32 |
| A06 formula | `- Hertz接触：F_c = (4/3)E*√r · δ^(3/2)，E* = E/(2(1-ν²))` | char [861,914) / L38–38 |
| A07 method | `- 每次试验一次均匀随机数 U ~ Uniform(0,1) ⏎ - 颗粒在 P_f(σ(t)) ≥ U 的首个时间步破坏（单调加载路径的精确逆CDF采样）` | char [1001,1078) / L43–44 |
| A08 method | `- 均匀缩放使 Σr_i³ = r_parent³（质量守恒精确到浮点精度）` | char [1131,1170) / L49–49 |
| A09 method | `- 子粒速度 = 母粒速度 + 质量加权零均值随机散布（动量守恒精确到浮点精度）` | char [1170,1211) / L50–50 |
| A10 method | `- MLE估计：α̂ = n / Σln(d_max/d_i)` | char [1226,1258) / L53–53 |
| A11 code_artifact | `` - 代码：`src/tensordem/granule_crush.py`（850行） `` | char [1369,1413) / L59–59 |
| A12 test_artifact | `` - 测试：`tests/test_granule_crush.py`（21条） `` | char [1413,1453) / L60–60 |
| A13 table | `| 粒径 d [mm] | 模拟中位强度 [MPa] | 解析中位强度 [MPa] | 偏差 | ⏎ |-------------|-------------------|-------------------|----…` | char [1488,1759) / L66–72 |
| A14 table | `| 守恒量 | 最大相对残差 | 阈值 | 判定 | ⏎ |--------|-------------|------|------| ⏎ | 质量 | 8.99×10⁻¹⁶ | 0.1% | ✓ (机器精度) | ⏎ …` | char [1940,2082) / L80–83 |
| A15 table | `| 估计方法 | α̂ | 偏差 | ⏎ |----------|---|------| ⏎ | 直接MLE | 1.5023 | 0.16% | ⏎ | 直接CDF | 1.5048 | 0.32% | ⏎ | 管线C…` | char [2102,2282) / L87–93 |
| A16 table | `| 平板速度 [m/s] | 应变率 [1/s] | α̂_CDF | 偏差 | ⏎ |---------------|-------------|-------|------| ⏎ | 0.001 | 0.5 | 1.…` | char [2325,2510) / L99–103 |
| A17 result_statement | `- 50次试验，零载荷运行50ms → **0次破碎** ✓` | char [2546,2577) / L109–109 |
| A18 result_statement | `- 21条新增pytest全绿 ⏎ - 相关模块（fracture_gen, fracture_events, fragmentation_statistics）共58条全绿` | char [2592,2678) / L113–114 |
| A19 figure_reference | `见内嵌figures（4张PNG）。` | char [2689,2708) / L118–118 |
| A20 figure | （正文占位与 A19 同行；图本体名 fig1_weibull_size_effect，figures[0]） | char [2689,2708) / L118–118 |
| A21 figure | （正文占位与 A19 同行；图本体名 fig2_gaudin_spectrum，figures[1]） | char [2689,2708) / L118–118 |
| A22 figure | （正文占位与 A19 同行；图本体名 fig3_conservation_ledger，figures[2]） | char [2689,2708) / L118–118 |
| A23 figure | （正文占位与 A19 同行；图本体名 fig4_strain_rate_study，figures[3]） | char [2689,2708) / L118–118 |
| A24 table | `| 判据 | 关键量 | 基准值 | 计算值 | 误差 | 是否<3% | ⏎ |------|--------|--------|--------|------|---------| ⏎ | C1 | R² | ≥0.…` | char [3064,3392) / L130–137 |

## ⑤ 注意点与局限

1. **哈希相等 ≠ 内容正确**：sha256 只机械证明「我读到的字节 = 契约指的字节」，不证明报告任何数值成立。本工序不做数值复算。
2. **claims 为空是刻意的**：契约 `no_forced_claim_generation=true`；登记工序抽 claim 会把「登记」和「抽取」两道工序的验收面混在一起。
3. **两个工件 unresolved**：`src/tensordem/granule_crush.py`（850 行）与 `tests/test_granule_crush.py`（21 条）只以「原文声明」入账；它们属 TensorDEM 仓，不在本工作包范围，故不验证存在性与行数/用例数。
4. **图资产双重定位**：4 张 PNG 的正文定位共用一行占位文字；若下游按图行号抽图会失败，必须走 `platform_figure` 字段。
5. **未覆盖段落**：⑥ 结论行、⑤ 局限 5 条、③ 各节标题等未逐条登记（只登记表与结论性语句）；覆盖率见 `fig2_source_coverage.png`，缺口是公开的、不是隐藏的。
6. **仓内既有 `schemas/asset_manifest.v1.schema.json` 不适用**：它把 `package_id` 钉成 `const: wp-448-01`，是上一包的自用 schema。本包不篡改它，改用 `kf_result.v1` 结构校验 + 脚本内显式不变量（26 项）作为 `schema_pass` 的可复现证据。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 判据 | 证据（verify 检查名） | 结果 |
|---|---|---|---|
| `valid_json` | kf_result.json / asset_manifest.json 均可被 json.load 解析 | verify: kf_result_schema_pass + outputs_payload_identical_to_manifest_file | ✓ |
| `schema_pass` | kf_result.v1 结构校验（jsonschema）通过 | verify: kf_result_schema_pass | ✓ |
| `source_locator_resolvable` | 24/24 引文是源 markdown 的精确切片且唯一命中 | verify: source_locator_resolvable + locator_quotes_unique | ✓ |
| `source_hash_matches` | 重算 sha256 与契约 source_hash 相等 | verify: source_hash_matches + envelope_source_hash_equals_recomputed | ✓ |
| `no_duplicate_ids` | asset_id 无重复且符合 A[0-9]{2} | verify: no_duplicate_ids + asset_id_pattern | ✓ |
| `all_claims_have_evidence_or_explicit_unresolved_status` | claims=[]（契约允许），无 claim 缺证据；两条声明工件已显式 referenced_unresolved | verify: claims_empty_or_evidenced + counts_by_resolution_matches_assets | ✓ |

### 误差判定（本工序不适用，附原因）

本工序不产生任何数值结果，只做身份登记，因此**没有可对标的基准值，也就没有「<3%」这类误差量**。唯一的定量判据是字节/字符级恒等，逐项如下：

| 判据 | 基准 | 计算值 | 误差 | 是否<3% |
|---|---|---|---|---|
| 源 markdown sha256 | 契约 `source_hash` = `sha256:6ed122a8092e41f05bebbb099ce1406a77ae3504f97785c7501c220f79310f72` | 重算 = `sha256:6ed122a8092e41f05bebbb099ce1406a77ae3504f97785c7501c220f79310f72` | 0（完全相等） | 不适用（恒等判据，非近似量） |
| 源 markdown 字符数 | 契约 `chars` = 3454 | `3454` | 0 | 不适用 |
| 引文定位 | `md[start:end]` 切片 | 24/24 条切片等于引文且唯一命中 | 0 | 不适用 |
| 覆盖率（公开缺口） | — | 2073/3454 chars = 60.0% | — | 不适用 |

声明原因：被登记报告（10087）内部的工程误差（如 C1 的 1.7%、C4 的 0.16–2.92% 等）属于该报告自身结论，本工序**不重算、不背书**，也不把它们搬进本报告冒充自己的误差判定。

**结论**：6/6 acceptance 项通过；脚本级不变量 26/26 PASS

### repro_cmd（一键复跑）

```bash
cd <worktree-root>   # TensorKnowledge 检出
python3 scripts/kf_wp10087_01_register.py emit      # 取源 + 重算哈希 + 生成 manifest/信封
python3 scripts/kf_wp10087_01_figures.py            # 生成两张图（数值来自 manifest）
python3 scripts/kf_wp10087_01_register.py render    # 渲染本报告（注入表格与唯一 json 块）
python3 scripts/kf_wp10087_01_register.py verify    # 26 项验收不变量 + schema 校验
python3 -m pytest tests/test_kf_wp10087_01_register_assets.py -q
```

## kf_result.v1 信封（唯一 json 代码块）

```json
{
  "package_id": "wp-10087-01",
  "task_type": "01-asset-registration",
  "report_id": "10087",
  "provenance": {
    "source_hash": "sha256:6ed122a8092e41f05bebbb099ce1406a77ae3504f97785c7501c220f79310f72",
    "source_field": "markdown",
    "producer": "scripts/kf_wp10087_01_register.py (lane C, 01-asset-registration)",
    "emitted_at": "2026-11-12T01:41:26+00:00",
    "source_uri": "tensor://reports/10087",
    "notes": "hash recomputed from the fetched markdown UTF-8 bytes; all 24 locator quotes are machine-sliced from that markdown and unique; claims=[] (no extraction in this work package); no claim marked verified."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-10087-01",
      "task_type": "01-asset-registration",
      "report_id": "10087",
      "source": {
        "uri": "tensor://reports/10087",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "6ed122a8092e41f05bebbb099ce1406a77ae3504f97785c7501c220f79310f72",
        "chars": 3454,
        "bytes_utf8": 5341,
        "title": "P97-N02: DEM单颗粒压碎验证面——Weibull强度-尺寸效应+子粒替换守恒账本+Gaudin破碎谱",
        "scenario_key": "P97-N02",
        "platform_figures": [
          {
            "index": 0,
            "name": "fig1_weibull_size_effect",
            "caption": "Weibull size-effect: (a) σ_f vs d log-log, R²=0.9998, m_fit=6.93; (b) P_f(σ) showing volume effect."
          },
          {
            "index": 1,
            "name": "fig2_gaudin_spectrum",
            "caption": "Gaudin-Schuhmann spectrum: (a) CDF match (n=20000); (b) PDF log-log confirming power law."
          },
          {
            "index": 2,
            "name": "fig3_conservation_ledger",
            "caption": "Conservation ledger (1000 events): (a) mass residual <9e-16; (b) momentum residual <8e-16."
          },
          {
            "index": 3,
            "name": "fig4_strain_rate_study",
            "caption": "Gaudin α vs strain rate (limestone): α recovered within 3% across 0.5–50 1/s."
          }
        ],
        "platform_tags": [
          "DEM",
          "Weibull",
          "Gaudin",
          "fragmentation",
          "crushing",
          "conservation",
          "P97"
        ]
      },
      "counts": {
        "assets": 24,
        "by_class": {
          "section_heading": 1,
          "formula": 4,
          "table": 6,
          "method": 4,
          "code_artifact": 1,
          "test_artifact": 1,
          "result_statement": 2,
          "figure_reference": 1,
          "figure": 4
        },
        "by_resolution": {
          "resolved_in_source": 22,
          "referenced_unresolved": 2
        },
        "resolved_in_source": 22,
        "referenced_unresolved": 2,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "section_heading",
          "label": "案例介绍章标题（① 案例介绍）",
          "in_report_section": "① 案例介绍",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading level-2 present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 64,
            "end_char": 74,
            "start_line": 4,
            "end_line": 4,
            "quote": "## ① 案例介绍",
            "unique": true
          },
          "note": "顶层章节锚点，供下游抽取定位章节边界。"
        },
        {
          "asset_id": "A02",
          "asset_class": "formula",
          "label": "Weibull 特征强度-尺寸效应式 σ_f(V)",
          "in_report_section": "① 案例介绍 / 物理背景",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "display-math block present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 169,
            "end_char": 230,
            "start_line": 9,
            "end_line": 9,
            "quote": "$$\\sigma_f(V) = \\sigma_0 \\left(\\frac{V}{V_0}\\right)^{-1/m}$$",
            "unique": true
          },
          "note": "LaTeX 原文保留（含 \\left(\\frac{V}{V_0}\\right)^{-1/m}），未做符号改写。"
        },
        {
          "asset_id": "A03",
          "asset_class": "formula",
          "label": "Weibull 破坏概率式 P_f(σ, V)",
          "in_report_section": "① 案例介绍 / 物理背景",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "display-math block present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 231,
            "end_char": 327,
            "start_line": 11,
            "end_line": 11,
            "quote": "$$P_f(\\sigma, V) = 1 - \\exp\\left[-\\left(\\frac{\\sigma}{\\sigma_0}\\right)^m \\frac{V}{V_0}\\right]$$",
            "unique": true
          },
          "note": "与 A02 同源的累积破坏概率表达式；参数含义见原文第 13 行。"
        },
        {
          "asset_id": "A04",
          "asset_class": "formula",
          "label": "Gaudin-Schuhmann 破碎谱 CDF F(d)=(d/d_max)^α",
          "in_report_section": "① 案例介绍 / 物理背景",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "inline formula sentence present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 475,
            "end_char": 519,
            "start_line": 19,
            "end_line": 19,
            "quote": "子粒粒径服从Gaudin-Schuhmann分布：F(d) = (d/d_max)^α",
            "unique": true
          },
          "note": "行内公式，原文用 α（U+03B1）而非 alpha 字样。"
        },
        {
          "asset_id": "A05",
          "asset_class": "table",
          "label": "双材料参数表（石英砂 / 石灰岩，9 项）",
          "in_report_section": "① 案例介绍 / 参数表",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown pipe table with 2 data columns present at the span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 529,
            "end_char": 823,
            "start_line": 23,
            "end_line": 32,
            "quote": "| 参数 | 石英砂 | 石灰岩 |\n|------|--------|--------|\n| 密度 ρ [kg/m³] | 2650 | 2500 |\n| 杨氏模量 E [GPa] | 37.0 | 50.0 |\n| 泊松比 ν | 0.17 | 0.25 |\n| Weibull模量 m | 7.0 | 5.0 |\n| 特征强度 σ₀ [MPa] | 100 | 30 |\n| 参考体积 V₀ [m³] | (4/3)π(1mm)³ | (4/3)π(1mm)³ |\n| Gaudin指数 α | 1.5 | 1.5 |\n| 最大子粒直径 d_max [mm] | 10 | 8 |",
            "unique": true
          },
          "note": "参数表整体登记为一条资产（不抽取单元格值：本工序不做抽取）。参考体积以表达式给出而非数值。"
        },
        {
          "asset_id": "A06",
          "asset_class": "formula",
          "label": "Hertz 接触力式 F_c 与等效模量 E*",
          "in_report_section": "② 方法 / 加载模拟",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "inline formula line present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 861,
            "end_char": 914,
            "start_line": 38,
            "end_line": 38,
            "quote": "- Hertz接触：F_c = (4/3)E*√r · δ^(3/2)，E* = E/(2(1-ν²))",
            "unique": true
          },
          "note": "含 E* = E/(2(1-ν²)) 定义。"
        },
        {
          "asset_id": "A07",
          "asset_class": "method",
          "label": "Weibull 采样规则（单次均匀随机数 + 首个越界步破坏）",
          "in_report_section": "② 方法 / Weibull采样",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "two-line method block present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1001,
            "end_char": 1078,
            "start_line": 43,
            "end_line": 44,
            "quote": "- 每次试验一次均匀随机数 U ~ Uniform(0,1)\n- 颗粒在 P_f(σ(t)) ≥ U 的首个时间步破坏（单调加载路径的精确逆CDF采样）",
            "unique": true
          },
          "note": "登记为两条连续行构成的采样规则资产；第 45 行（300 次试验取中位数）未并入，保持 span 最小。"
        },
        {
          "asset_id": "A08",
          "asset_class": "method",
          "label": "子粒均匀缩放质量守恒规则",
          "in_report_section": "② 方法 / 子粒替换",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "method line present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1131,
            "end_char": 1170,
            "start_line": 49,
            "end_line": 49,
            "quote": "- 均匀缩放使 Σr_i³ = r_parent³（质量守恒精确到浮点精度）",
            "unique": true
          },
          "note": "原文声明精确到浮点精度；本工序仅登记该声明，不验证。"
        },
        {
          "asset_id": "A09",
          "asset_class": "method",
          "label": "子粒速度零均值随机散布（动量守恒）规则",
          "in_report_section": "② 方法 / 子粒替换",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "method line present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1170,
            "end_char": 1211,
            "start_line": 50,
            "end_line": 50,
            "quote": "- 子粒速度 = 母粒速度 + 质量加权零均值随机散布（动量守恒精确到浮点精度）",
            "unique": true
          },
          "note": "同上：只登记声明，不做数值复算（复算属验证工作包）。"
        },
        {
          "asset_id": "A10",
          "asset_class": "method",
          "label": "Gaudin 谱 α 的 MLE 估计式",
          "in_report_section": "② 方法 / Gaudin谱拟合",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "inline formula line present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1226,
            "end_char": 1258,
            "start_line": 53,
            "end_line": 53,
            "quote": "- MLE估计：α̂ = n / Σln(d_max/d_i)",
            "unique": true
          },
          "note": "原文使用 α̂（带 hat 组合字符），切片逐字保留。"
        },
        {
          "asset_id": "A11",
          "asset_class": "code_artifact",
          "label": "声明代码文件 src/tensordem/granule_crush.py（850 行）",
          "in_report_section": "② 方法 / 工具链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path existence cannot be decided from the report record; producing repo (TensorDEM) is outside this package's scope",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1369,
            "end_char": 1413,
            "start_line": 59,
            "end_line": 59,
            "quote": "- 代码：`src/tensordem/granule_crush.py`（850行）",
            "unique": true
          },
          "note": "只登记「原文声明了该路径与行数」，不主张文件存在、也不主张 850 行属实。"
        },
        {
          "asset_id": "A12",
          "asset_class": "test_artifact",
          "label": "声明测试文件 tests/test_granule_crush.py（21 条）",
          "in_report_section": "② 方法 / 工具链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path existence cannot be decided from the report record; test suite not executed here",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1413,
            "end_char": 1453,
            "start_line": 60,
            "end_line": 60,
            "quote": "- 测试：`tests/test_granule_crush.py`（21条）",
            "unique": true
          },
          "note": "21 条用例数来自原文自述，未经本工序执行复核。"
        },
        {
          "asset_id": "A13",
          "asset_class": "table",
          "label": "C1 Weibull 尺寸效应拟合结果表（5 个粒径）",
          "in_report_section": "③ 计算结果 / C1",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown pipe table present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1488,
            "end_char": 1759,
            "start_line": 66,
            "end_line": 72,
            "quote": "| 粒径 d [mm] | 模拟中位强度 [MPa] | 解析中位强度 [MPa] | 偏差 |\n|-------------|-------------------|-------------------|------|\n| 0.5 | 174.86 | 171.90 | 1.7% |\n| 1.0 | 128.44 | 127.72 | 0.6% |\n| 2.0 | 94.83 | 94.90 | 0.1% |\n| 4.0 | 71.00 | 70.51 | 0.7% |\n| 8.0 | 52.47 | 52.39 | 0.2% |",
            "unique": true
          },
          "note": "含模拟/解析中位强度与偏差列；数值未在本工序复算。"
        },
        {
          "asset_id": "A14",
          "asset_class": "table",
          "label": "C2/C3 质量与动量守恒残差表（1000 次事件）",
          "in_report_section": "③ 计算结果 / C2/C3",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown pipe table present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1940,
            "end_char": 2082,
            "start_line": 80,
            "end_line": 83,
            "quote": "| 守恒量 | 最大相对残差 | 阈值 | 判定 |\n|--------|-------------|------|------|\n| 质量 | 8.99×10⁻¹⁶ | 0.1% | ✓ (机器精度) |\n| 动量 | 7.94×10⁻¹⁶ | 0.1% | ✓ (机器精度) |",
            "unique": true
          },
          "note": "残差以科学计数法给出（×10⁻¹⁶ 上标字符）。"
        },
        {
          "asset_id": "A15",
          "asset_class": "table",
          "label": "C4 Gaudin 谱五种估计方法的 α̂ 表",
          "in_report_section": "③ 计算结果 / C4",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown pipe table present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2102,
            "end_char": 2282,
            "start_line": 87,
            "end_line": 93,
            "quote": "| 估计方法 | α̂ | 偏差 |\n|----------|---|------|\n| 直接MLE | 1.5023 | 0.16% |\n| 直接CDF | 1.5048 | 0.32% |\n| 管线CDF | 1.4970 | 0.20% |\n| 逐事件MLE | 1.5296 | 1.97% |\n| 逐事件CDF | 1.5397 | 2.64% |",
            "unique": true
          },
          "note": "表头用 α̂ 组合字符，逐字保留。"
        },
        {
          "asset_id": "A16",
          "asset_class": "table",
          "label": "C4-rate 应变率工况表（石灰岩，3 档平板速度）",
          "in_report_section": "③ 计算结果 / C4-rate",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown pipe table present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2325,
            "end_char": 2510,
            "start_line": 99,
            "end_line": 103,
            "quote": "| 平板速度 [m/s] | 应变率 [1/s] | α̂_CDF | 偏差 |\n|---------------|-------------|-------|------|\n| 0.001 | 0.5 | 1.4888 | 0.75% |\n| 0.01 | 5.0 | 1.4617 | 2.55% |\n| 0.1 | 50.0 | 1.5439 | 2.92% |",
            "unique": true
          },
          "note": "应变率列为换算值，原文与平板速度并列给出。"
        },
        {
          "asset_id": "A17",
          "asset_class": "result_statement",
          "label": "C5 负控结论（零载荷 50 次 → 0 次破碎）",
          "in_report_section": "③ 计算结果 / C5",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "single bullet present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2546,
            "end_char": 2577,
            "start_line": 109,
            "end_line": 109,
            "quote": "- 50次试验，零载荷运行50ms → **0次破碎** ✓",
            "unique": true
          },
          "note": "负控结论以单行列表项给出，含 ✓ 字符。"
        },
        {
          "asset_id": "A18",
          "asset_class": "result_statement",
          "label": "C6 回归测试结论（21 条 + 相关模块 58 条）",
          "in_report_section": "③ 计算结果 / C6",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "two-line bullet block present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2592,
            "end_char": 2678,
            "start_line": 113,
            "end_line": 114,
            "quote": "- 21条新增pytest全绿\n- 相关模块（fracture_gen, fracture_events, fragmentation_statistics）共58条全绿",
            "unique": true
          },
          "note": "测试通过数按原文自述登记，本工序未执行该测试集。"
        },
        {
          "asset_id": "A19",
          "asset_class": "figure_reference",
          "label": "结果图占位说明（见内嵌figures（4张PNG））",
          "in_report_section": "④ 结果图",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figure placeholder line present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2689,
            "end_char": 2708,
            "start_line": 118,
            "end_line": 118,
            "quote": "见内嵌figures（4张PNG）。",
            "unique": true
          },
          "note": "正文用一行占位引用 4 张图；图本体不在 markdown 内，见 A20–A23（平台记录 figures[]）。"
        },
        {
          "asset_id": "A20",
          "asset_class": "figure",
          "label": "fig1_weibull_size_effect（PNG，平台记录 figures[0]）",
          "in_report_section": "④ 结果图",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figure present in the platform record figures[] (index 0)",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2689,
            "end_char": 2708,
            "start_line": 118,
            "end_line": 118,
            "quote": "见内嵌figures（4张PNG）。",
            "unique": true
          },
          "note": "图本体在平台报告的 figures[] 字段；正文定位到 A19 同一行（故 span 与 A19 相同）。",
          "platform_figure": {
            "index": 0,
            "name": "fig1_weibull_size_effect",
            "caption": "Weibull size-effect: (a) σ_f vs d log-log, R²=0.9998, m_fit=6.93; (b) P_f(σ) showing volume effect."
          }
        },
        {
          "asset_id": "A21",
          "asset_class": "figure",
          "label": "fig2_gaudin_spectrum（PNG，平台记录 figures[1]）",
          "in_report_section": "④ 结果图",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figure present in the platform record figures[] (index 1)",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2689,
            "end_char": 2708,
            "start_line": 118,
            "end_line": 118,
            "quote": "见内嵌figures（4张PNG）。",
            "unique": true
          },
          "note": "同上。",
          "platform_figure": {
            "index": 1,
            "name": "fig2_gaudin_spectrum",
            "caption": "Gaudin-Schuhmann spectrum: (a) CDF match (n=20000); (b) PDF log-log confirming power law."
          }
        },
        {
          "asset_id": "A22",
          "asset_class": "figure",
          "label": "fig3_conservation_ledger（PNG，平台记录 figures[2]）",
          "in_report_section": "④ 结果图",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figure present in the platform record figures[] (index 2)",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2689,
            "end_char": 2708,
            "start_line": 118,
            "end_line": 118,
            "quote": "见内嵌figures（4张PNG）。",
            "unique": true
          },
          "note": "同上。",
          "platform_figure": {
            "index": 2,
            "name": "fig3_conservation_ledger",
            "caption": "Conservation ledger (1000 events): (a) mass residual <9e-16; (b) momentum residual <8e-16."
          }
        },
        {
          "asset_id": "A23",
          "asset_class": "figure",
          "label": "fig4_strain_rate_study（PNG，平台记录 figures[3]）",
          "in_report_section": "④ 结果图",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figure present in the platform record figures[] (index 3)",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2689,
            "end_char": 2708,
            "start_line": 118,
            "end_line": 118,
            "quote": "见内嵌figures（4张PNG）。",
            "unique": true
          },
          "note": "同上。",
          "platform_figure": {
            "index": 3,
            "name": "fig4_strain_rate_study",
            "caption": "Gaudin α vs strain rate (limestone): α recovered within 3% across 0.5–50 1/s."
          }
        },
        {
          "asset_id": "A24",
          "asset_class": "table",
          "label": "⑥ 误差判定表（6 项判据 vs 基准）",
          "in_report_section": "⑥ 误差判定",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown pipe table present at the recorded line span",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3064,
            "end_char": 3392,
            "start_line": 130,
            "end_line": 137,
            "quote": "| 判据 | 关键量 | 基准值 | 计算值 | 误差 | 是否<3% |\n|------|--------|--------|--------|------|---------|\n| C1 | R² | ≥0.95 | 0.9998 | — | ✓ |\n| C1 | m偏差 | ≤20% | 1.0% | 1.0% | ✓ |\n| C2 | 质量残差 | ≤0.1% | 9×10⁻¹⁴% | ~0% | ✓ |\n| C3 | 动量残差 | ≤0.1% | 8×10⁻¹⁴% | ~0% | ✓ |\n| C4 | α偏差 | ≤15% | 0.16–2.92% | <3% | ✓ |\n| C5 | 零载荷破碎数 | 0 | 0 | 0% | ✓ |",
            "unique": true
          },
          "note": "含「是否<3%」列与阈值列；判定结论由平台门复核，本工序不改写。"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": true,
        "hash_recomputed_locally": "sha256:6ed122a8092e41f05bebbb099ce1406a77ae3504f97785c7501c220f79310f72",
        "hash_matches_contract": true,
        "chars_match_contract": true
      }
    }
  },
  "claims": []
}
```
