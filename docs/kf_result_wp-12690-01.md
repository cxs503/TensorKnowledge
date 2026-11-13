# KF-RESULT wp-12690-01

- **工作包**: wp-12690-01 · task_type `01-asset-registration` · lane C · 报告 report_id=`12690`
- **源**: `tensor://reports/12690` 字段 `markdown` · 2034 字符 / 2034 字节 · sha256=`c7ffa8c80de7dacf0f20da21051c644731ee7e82649101b0922b3830796d9d28`
- **标题**: P158W3-N03: TensorDEM CFD-DEM Two-Way Coupling Verification
- **场景键**: `P158W3-N03` · 分层=CFD-DEM · mission_id=15752

## ① 本工序做了什么

只做 01-asset-registration（资产登记），不做抽取、不做类型分类（契约 `objective.register_assets=true` / `classify_report_type=false`）：

1. 从平台接口取回 report_id=12690 的 `markdown`，本地重算 sha256 并与契约 `c7ffa8c80de7dacf0f20da21051c644731ee7e82649101b0922b3830796d9d28` 逐字比对（一致）。
2. 在 markdown 上定位并登记 **26** 个源资产：20 个在正文内可解析、1 个被正文引用但无地址、5 个声明存在但无载荷。
3. 每个资产的 `quote` 都是运行时从 markdown 切片得到的原文行，脚本复核其为**唯一子串**且 char span 重切片一致；没有任何一个字是手抄的。
4. `claims` 有意为空数组：本包不做知识抽取，契约注记明确允许；不为了凑指标造 claim，也不把任何结论标成 verified（verification 由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 工具 | 关键设置 |
|---|---|---|
| 取源 | `urllib` → `GET /api/v1/tensor/reports/12690`（Bearer 登录 token） | 失败时降级读本机缓存 `runs/wp-12690-01/report_12690.md`，并在 verify_report 里写明来源 |
| 定址 | `scripts/kf_register_12690.py` | 锚点=**唯一行子串**；span=行偏移；quote=行切片；`md.count(quote)==1` 且 `md[start_char:end_char]==quote` 才落盘 |
| 结构 | `jsonschema` | manifest vs `schemas/asset_manifest.v1.schema.json`；envelope vs `schemas/kf_result.v1.schema.json` |
| 重验 | `scripts/kf_verify_12690.py` | **重新**从 API 拉 markdown 重算哈希，重做全部验收项，不信任登记脚本的自述 |
| 反证 | `tests/test_kf_wp12690_01.py`（8 例） | 5 个负对照：篡改 quote / 篡改 char span / 篡改哈希 / 重复 asset_id / 伪造 resolution=verified，逐项必须变红 |

本地 schema 说明：`schemas/asset_manifest.v1.schema.json` 是历史包 wp-448-01 的落地版，把 package_id/report_id/uri 钉成 const。本包**不改它**，而是用 `derive_generic_schema()` 做确定性派生——只把这三个身份字段放松为 pattern，其余结构要求原样继承，派生件落 `artifacts/wp-12690-01/asset_manifest.generic.schema.json` 供审计。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `artifacts/wp-12690-01/asset_manifest.json` | 登记表本体：26 资产，by_resolution={"resolved_in_source": 20, "referenced_unresolved": 1, "declared_absent": 5}，claims=[] |
| `runs/wp-12690-01/kf_result.wp-12690-01.json` | 结果信封（kf_result.v1）；`provenance.source_hash` 与契约同值 |
| `runs/wp-12690-01/verify_report.json` | 8 项验收 + 2 项诚实性检查的机器判定与细节 |
| `artifacts/wp-12690-01/asset_manifest.generic.schema.json` | 由本地 schema 派生的包无关版（审计用） |
| `artifacts/wp-12690-01/asset_manifest.json`, `runs/wp-12690-01/*` | 运行期副本（推送门会丢弃 artifacts/** 与 runs/**，故在 `docs/wp-12690-01/` 留字节相同镜像） |
| `docs/wp-12690-01/published_check.json` | 服务端副本复核：唯一 json 块、与信封等价、平台重算哈希一致 |
| `docs/wp-12690-01/report_12690.md` | 源 markdown 的持久镜像（推送门丢弃 runs/**，离线复跑靠它） |
| `scripts/kf_register_12690.py` / `kf_verify_12690.py` / `kf_publish_12690.py` / `kf_check_published_12690.py` | 一键复跑：登记 → 独立重验 → 反证测试 → 发报 → 服务端复核 |

## ④ 证据定位表（资产 → 原文引文片段，全部运行时切片）

| asset_id | 类别 | 章节 | 解析 | 原文引文（唯一子串，char span） |
|---|---|---|---|---|
| A01 | document | §preamble (before first ## section) | resolved_in_source | `# P158W3-N03: TensorDEM CFD-DEM Two-Way Coupling Verification / ## 1. C…` (document) |
| A02 | heading | §preamble (before first ## section) | resolved_in_source | `# P158W3-N03: TensorDEM CFD-DEM Two-Way Coupling Verification` (0–61) |
| A03 | section_heading | §1. Case Introduction | resolved_in_source | `## 1. Case Introduction` (63–86) |
| A04 | physical_model_statement | §1. Case Introduction | resolved_in_source | `Dilute point-particle Lagrangian tracking with two-way CFD-DEM coupling…` (88–308) |
| A05 | closure_spec | §1. Case Introduction | resolved_in_source | `Drag: Schiller-Naumann, Added mass: C_A=0.5, Dense limit: Gidaspow/Ergu…` (235–308) |
| A06 | parameter_set | §1. Case Introduction | resolved_in_source | `Parameters: d_p=1e-4m (A1-A4) / 2e-3m (A5), rho_p=2500, rho_f=1000, mu=…` (310–403) |
| A07 | section_heading | §2. Method | resolved_in_source | `## 2. Method` (405–417) |
| A08 | verification_plan | §2. Method | resolved_in_source | `- A1: RK4 integration of Stokes relaxation, 10 checkpoints vs exponenti…` (419–757) |
| A09 | result_block | §3. Results | resolved_in_source | `### A1: Stokes Relaxation / - tau_p = 1.6667e-03 s, Re_max = 1.0000e-02…` (773–902) |
| A10 | result_block | §3. Results | resolved_in_source | `### A2: Terminal Velocity / - v_t_Stokes = 8.1722e-04 m/s, v_t_num = 8.…` (903–1046) |
| A11 | result_block | §3. Results | resolved_in_source | `### A3: Added Mass Coefficient / - C_m_recovered = 0.500000, error = 0.…` (1047–1150) |
| A12 | result_block | §3. Results | resolved_in_source | `### A4: Momentum Conservation / - Single particle residual = 0.0000e+00…` (1151–1294) |
| A13 | result_block | §3. Results | resolved_in_source | `### A5: Dense Limit Ergun / - phi>0.4 max error = 0.000% (threshold <= …` (1295–1380) |
| A14 | section_heading | §4. Figures | resolved_in_source | `## 4. Figures` (1381–1394) |
| A15 | figure_declaration | §4. Figures | resolved_in_source | `See embedded figures (5 plots).` (1396–1427) |
| A16 | section_heading | §5. Notes | resolved_in_source | `## 5. Notes` (1429–1440) |
| A17 | notes_list | §5. Notes | resolved_in_source | `1. Stokes relaxation requires Re<0.05 for S-N correction <1% / 2. Termi…` (1442–1760) |
| A18 | section_heading | §6. Error Assessment | resolved_in_source | `## 6. Error Assessment` (1762–1784) |
| A19 | criteria_table | §6. Error Assessment | resolved_in_source | `| Criterion | Measured | Threshold | Pass | / |-----------|----------|-…` (1786–2013) |
| A20 | verdict_statement | §6. Error Assessment | resolved_in_source | `**All passed: YES**` (2015–2034) |
| A21 | code_reference | §2. Method | referenced_unresolved | `## 2. Method` (405–417) |
| A22 | figure_payload | §4. Figures | declared_absent | `See embedded figures (5 plots).` (1396–1427) |
| A23 | figure_payload | §4. Figures | declared_absent | `See embedded figures (5 plots).` (1396–1427) |
| A24 | figure_payload | §4. Figures | declared_absent | `See embedded figures (5 plots).` (1396–1427) |
| A25 | figure_payload | §4. Figures | declared_absent | `See embedded figures (5 plots).` (1396–1427) |
| A26 | figure_payload | §4. Figures | declared_absent | `See embedded figures (5 plots).` (1396–1427) |

全部 26 条 quote 的唯一性与 char span 一致性由 `source_locator_resolvable` 检查逐条复核：**26/26 locators resolve**。

## ⑤ 注意点与局限

1. **5 幅图无载荷**：报告记录 `figures` 只有 name/caption 元数据，markdown 内也无 `![](...)`/`<img>`（程序化计数 = 0）。故 A22–A26 记 `declared_absent`，不编造路径。
2. **实现体无地址**：正文以方法名（RK4 积分、传递函数反演、动量台账、Gidaspow/Ergun）指向上游代码，但全文无仓库路径/commit/URL/文件名（正则 `(https?://|github\.com|git@|commit\s+[0-9a-f]{7,40}|[\w./-]+\.py\b|TensorDEM/[\w./-]+)` 命中 0 次）。A21 记 `referenced_unresolved`。
3. **只登记不判定**：报告自述 5/5 PASS（A20），但本包不据此升级任何结论；数值正确性、是否达到验收线都留给平台门与下游工序。
4. **`resolution` 语义收窄**：它只表示"该资产能否在源里被定位/取到"，与"这条科学结论是否成立"无关。
5. **内容深度**：源 markdown 仅 2034 字符、无独立附录/数据文件，资产粒度只能到"节/结果块/表"一级；更细的参数卡/方法卡属下游工序（03 抽取），本包不做。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据 |
|---|---|---|
| `valid_json` | ✅ pass | asset_manifest.json + kf_result envelope parse as JSON |
| `schema_pass` | ✅ pass | manifest errors=0, envelope errors=0 |
| `source_locator_resolvable` | ✅ pass | 26/26 locators resolve |
| `source_hash_matches` | ✅ pass | contract=c7ffa8c80de7dacf… api=c7ffa8c80de7dacf… cached=c7ffa8c80de7dacf… envelope=sha256:c7ffa8c80de7dacf… manifest=c7ffa8c80de7dacf… |
| `no_duplicate_ids` | ✅ pass | 26 ids, 26 distinct |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ pass | claims=0 (registration-only package; 空数组=契约允许), unbacked=0 |

额外诚实性检查：`no_asset_marked_verified` ✅ （verified-labelled assets=0）；`counts_consistent` ✅（counts.assets=26 actual=26 by_resolution_sum=26）。

**总判定**：8 项检查全绿，`all_pass=true`；无失败项，无粉饰。

## 复跑命令

工作树根执行（一键：登记 → 独立重验 → 反证测试 → 发报）：

`python3 scripts/kf_register_12690.py && python3 scripts/kf_verify_12690.py && python3 -m pytest tests/test_kf_wp12690_01.py -q && python3 scripts/kf_publish_12690.py --publish && python3 scripts/kf_check_published_12690.py`

> 说明：本包为文档/登记类工序，无场量云图可画，故不附 figures（图载荷本身即 A22–A26 的 declared_absent 结论）。

## 结果信封（唯一 JSON 块）

```json
{
  "package_id": "wp-12690-01",
  "task_type": "01-asset-registration",
  "report_id": "12690",
  "provenance": {
    "source_hash": "sha256:c7ffa8c80de7dacf0f20da21051c644731ee7e82649101b0922b3830796d9d28",
    "source_field": "markdown",
    "producer": "TensorKnowledge scripts/kf_register_12690.py (m15752)",
    "emitted_at": "2026-11-12T02:27:48.771172+00:00",
    "notes": "registration only: 26 assets located by char span in the report markdown; claims intentionally empty (objective.classify_report_type=false); no asset marked verified -- verification is computed by the platform gate"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-12690-01",
      "task_type": "01-asset-registration",
      "report_id": "12690",
      "source": {
        "uri": "tensor://reports/12690",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "c7ffa8c80de7dacf0f20da21051c644731ee7e82649101b0922b3830796d9d28",
        "chars": 2034,
        "bytes_utf8": 2034,
        "title": "P158W3-N03: TensorDEM CFD-DEM Two-Way Coupling Verification",
        "scenario_key": "P158W3-N03",
        "platform_figures": [
          {
            "name": "A1_stokes_relaxation",
            "caption": "Stokes relaxation exponential decay"
          },
          {
            "name": "A2_terminal_velocity",
            "caption": "Terminal velocity settling and error"
          },
          {
            "name": "A3_added_mass",
            "caption": "Added mass transfer function"
          },
          {
            "name": "A4_momentum",
            "caption": "Momentum exchange conservation"
          },
          {
            "name": "A5_ergun",
            "caption": "Dense limit Ergun verification"
          }
        ],
        "platform_tags": [
          "CFD-DEM",
          "two-way-coupling",
          "Lagrangian",
          "point-particle",
          "verification"
        ]
      },
      "counts": {
        "assets": 26,
        "by_class": {
          "document": 1,
          "heading": 1,
          "section_heading": 5,
          "physical_model_statement": 1,
          "closure_spec": 1,
          "parameter_set": 1,
          "verification_plan": 1,
          "result_block": 5,
          "figure_declaration": 1,
          "notes_list": 1,
          "criteria_table": 1,
          "verdict_statement": 1,
          "code_reference": 1,
          "figure_payload": 5
        },
        "by_resolution": {
          "resolved_in_source": 20,
          "referenced_unresolved": 1,
          "declared_absent": 5
        },
        "resolved_in_source": 20,
        "referenced_unresolved": 1,
        "declared_absent": 5
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文，含 6 节）",
          "in_report_section": "preamble (before first ## section)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 2034,
            "start_line": 0,
            "end_line": 65,
            "quote": "# P158W3-N03: TensorDEM CFD-DEM Two-Way Coupling Verification\n\n## 1. Case Introduction\n\nDilute point-particle Lagrangian tracking with two-way CFD-DEM coupling.\nParticle equation: m_p * du_p/dt = F_drag + F_added + F_pressure + m_p*g.\nDrag: Schiller-Naumann, Added mass: C_A=0.5, Dense limit: Gidaspow/Ergun.\n\nParameters: d_p=1e-4m (A1-A4) / 2e-3m (A5), rho_p=2500, rho_f=1000, mu=1e-3/1e-2(A2), g=9.81.\n\n## 2. Method\n\n- A1: RK4 integration of Stokes relaxation, 10 checkpoints vs exponential decay\n- A2: Forward Euler settling, high viscosity ensures Re<<1\n- A3: Transfer function H(omega) at characteristic frequency extracts C_A\n- A4: Momentum ledger per-channel accumulation, Newton's 3rd law audit\n- A5: Phi sweep comparing Gidaspow with Ergun Model-A\n\n## 3. Results\n\n### A1: Stokes Relaxation\n- tau_p = 1.6667e-03 s, Re_max = 1.0000e-02\n- Max relative error = 0.886% (threshold <= 2%)\n- **PASS**\n\n### A2: Terminal Velocity\n- v_t_Stokes = 8.1722e-04 m/s, v_t_num = 8.1275e-04 m/s\n- Re_t = 0.0081, error = 0.547% (threshold <= 3%)\n- **PASS**\n\n### A3: Added Mass Coefficient\n- C_m_recovered = 0.500000, error = 0.000% (threshold <= 5%)\n- **PASS**\n\n### A4: Momentum Conservation\n- Single particle residual = 0.0000e+00\n- Multi particle (20) residual = 0.0000e+00 (threshold <= 1%)\n- **PASS**\n\n### A5: Dense Limit Ergun\n- phi>0.4 max error = 0.000% (threshold <= 10%)\n- **PASS**\n\n## 4. Figures\n\nSee embedded figures (5 plots).\n\n## 5. Notes\n\n1. Stokes relaxation requires Re<0.05 for S-N correction <1%\n2. Terminal velocity needs high viscosity to ensure Re_t<<1 so S-N -> Stokes\n3. Added mass extracted from transfer function at characteristic frequency\n4. Momentum conservation is at machine precision level\n5. Gidaspow equals Ergun in dense regime (eps<0.8)\n\n## 6. Error Assessment\n\n| Criterion | Measured | Threshold | Pass |\n|-----------|----------|-----------|------|\n| A1 | 0.886% | <=2% | Y |\n| A2 | 0.547% | <=3% | Y |\n| A3 | 0.000% | <=5% | Y |\n| A4 | 0.0000e+00 | <=1% | Y |\n| A5 | 0.000% | <=10% | Y |\n\n**All passed: YES**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "整篇 markdown 即源资产本体；sha256 见 source.hash，平台独立重算比对"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题行（H1）",
          "in_report_section": "preamble (before first ## section)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 61,
            "start_line": 0,
            "end_line": 0,
            "quote": "# P158W3-N03: TensorDEM CFD-DEM Two-Way Coupling Verification",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "与报告记录 title 字段同源（title 属 record 字段，本包只登记 markdown 内出现处）"
        },
        {
          "asset_id": "A03",
          "asset_class": "section_heading",
          "label": "§1 Case Introduction 节标题",
          "in_report_section": "1. Case Introduction",
          "locator": {
            "method": "char_span",
            "start_char": 63,
            "end_char": 86,
            "start_line": 2,
            "end_line": 2,
            "quote": "## 1. Case Introduction",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "节边界锚点，供后续工序按节抽取"
        },
        {
          "asset_id": "A04",
          "asset_class": "physical_model_statement",
          "label": "物理模型声明 + 颗粒动量方程（无量纲化前原式）",
          "in_report_section": "1. Case Introduction",
          "locator": {
            "method": "char_span",
            "start_char": 88,
            "end_char": 308,
            "start_line": 4,
            "end_line": 6,
            "quote": "Dilute point-particle Lagrangian tracking with two-way CFD-DEM coupling.\nParticle equation: m_p * du_p/dt = F_drag + F_added + F_pressure + m_p*g.\nDrag: Schiller-Naumann, Added mass: C_A=0.5, Dense limit: Gidaspow/Ergun.",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "含模型声明行与颗粒方程行；公式为排版文本，无独立公式文件"
        },
        {
          "asset_id": "A05",
          "asset_class": "closure_spec",
          "label": "受力闭合式选择（S-N 阻力 / C_A=0.5 / Gidaspow-Ergun）",
          "in_report_section": "1. Case Introduction",
          "locator": {
            "method": "char_span",
            "start_char": 235,
            "end_char": 308,
            "start_line": 6,
            "end_line": 6,
            "quote": "Drag: Schiller-Naumann, Added mass: C_A=0.5, Dense limit: Gidaspow/Ergun.",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "闭合方案选择声明；数值 C_A=0.5 只登记不换算"
        },
        {
          "asset_id": "A06",
          "asset_class": "parameter_set",
          "label": "算例参数表（d_p/rho_p/rho_f/mu/g）",
          "in_report_section": "1. Case Introduction",
          "locator": {
            "method": "char_span",
            "start_char": 310,
            "end_char": 403,
            "start_line": 8,
            "end_line": 8,
            "quote": "Parameters: d_p=1e-4m (A1-A4) / 2e-3m (A5), rho_p=2500, rho_f=1000, mu=1e-3/1e-2(A2), g=9.81.",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "单行内联参数表；A1-A4 与 A5 粒径分开声明"
        },
        {
          "asset_id": "A07",
          "asset_class": "section_heading",
          "label": "§2 Method 节标题",
          "in_report_section": "2. Method",
          "locator": {
            "method": "char_span",
            "start_char": 405,
            "end_char": 417,
            "start_line": 10,
            "end_line": 10,
            "quote": "## 2. Method",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "节边界锚点"
        },
        {
          "asset_id": "A08",
          "asset_class": "verification_plan",
          "label": "校验方案 A1-A5（5 条方法条目）",
          "in_report_section": "2. Method",
          "locator": {
            "method": "char_span",
            "start_char": 419,
            "end_char": 757,
            "start_line": 12,
            "end_line": 17,
            "quote": "- A1: RK4 integration of Stokes relaxation, 10 checkpoints vs exponential decay\n- A2: Forward Euler settling, high viscosity ensures Re<<1\n- A3: Transfer function H(omega) at characteristic frequency extracts C_A\n- A4: Momentum ledger per-channel accumulation, Newton's 3rd law audit\n- A5: Phi sweep comparing Gidaspow with Ergun Model-A\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "5 条校验面方法；可执行实现体未随报告提供（见 A20）"
        },
        {
          "asset_id": "A09",
          "asset_class": "result_block",
          "label": "A1 结果块：Stokes 松弛（tau_p/Re_max/误差/判定）",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 773,
            "end_char": 902,
            "start_line": 20,
            "end_line": 24,
            "quote": "### A1: Stokes Relaxation\n- tau_p = 1.6667e-03 s, Re_max = 1.0000e-02\n- Max relative error = 0.886% (threshold <= 2%)\n- **PASS**\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "含 tau_p、Re_max、最大相对误差 0.886% 与 PASS 判定；数值仅登记"
        },
        {
          "asset_id": "A10",
          "asset_class": "result_block",
          "label": "A2 结果块：终端速度（v_t 解析/数值/Re_t/误差）",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 903,
            "end_char": 1046,
            "start_line": 25,
            "end_line": 29,
            "quote": "### A2: Terminal Velocity\n- v_t_Stokes = 8.1722e-04 m/s, v_t_num = 8.1275e-04 m/s\n- Re_t = 0.0081, error = 0.547% (threshold <= 3%)\n- **PASS**\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "含 v_t_Stokes、v_t_num、Re_t、0.547% 误差与 PASS 判定"
        },
        {
          "asset_id": "A11",
          "asset_class": "result_block",
          "label": "A3 结果块：附加质量系数反演（C_m）",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 1047,
            "end_char": 1150,
            "start_line": 30,
            "end_line": 33,
            "quote": "### A3: Added Mass Coefficient\n- C_m_recovered = 0.500000, error = 0.000% (threshold <= 5%)\n- **PASS**\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "含 C_m_recovered=0.500000、0.000% 误差与 PASS 判定"
        },
        {
          "asset_id": "A12",
          "asset_class": "result_block",
          "label": "A4 结果块：动量守恒残差（单颗粒/20 颗粒）",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 1151,
            "end_char": 1294,
            "start_line": 34,
            "end_line": 38,
            "quote": "### A4: Momentum Conservation\n- Single particle residual = 0.0000e+00\n- Multi particle (20) residual = 0.0000e+00 (threshold <= 1%)\n- **PASS**\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "含单颗粒与 20 颗粒残差 0.0000e+00、阈值 1% 与 PASS 判定"
        },
        {
          "asset_id": "A13",
          "asset_class": "result_block",
          "label": "A5 结果块：稠密极限 Ergun 对比（phi>0.4）",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 1295,
            "end_char": 1380,
            "start_line": 39,
            "end_line": 42,
            "quote": "### A5: Dense Limit Ergun\n- phi>0.4 max error = 0.000% (threshold <= 10%)\n- **PASS**\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "含 phi>0.4 最大误差 0.000%、阈值 10% 与 PASS 判定"
        },
        {
          "asset_id": "A14",
          "asset_class": "section_heading",
          "label": "§4 Figures 节标题",
          "in_report_section": "4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1381,
            "end_char": 1394,
            "start_line": 43,
            "end_line": 43,
            "quote": "## 4. Figures",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "节边界锚点"
        },
        {
          "asset_id": "A15",
          "asset_class": "figure_declaration",
          "label": "图声明（5 幅图，正文仅指向，无图注/路径）",
          "in_report_section": "4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1396,
            "end_char": 1427,
            "start_line": 45,
            "end_line": 45,
            "quote": "See embedded figures (5 plots).",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown image embed syntax ![](...)/<img> (hits=0)",
            "result": "resolved"
          },
          "note": "正文唯一图相关语句；仅声明数量，未给出文件名/路径/URL"
        },
        {
          "asset_id": "A16",
          "asset_class": "section_heading",
          "label": "§5 Notes 节标题",
          "in_report_section": "5. Notes",
          "locator": {
            "method": "char_span",
            "start_char": 1429,
            "end_char": 1440,
            "start_line": 47,
            "end_line": 47,
            "quote": "## 5. Notes",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "节边界锚点"
        },
        {
          "asset_id": "A17",
          "asset_class": "notes_list",
          "label": "适用条件与备注 1-5（Re 界限/S-N→Stokes/反演方法/机器精度/稠密等价）",
          "in_report_section": "5. Notes",
          "locator": {
            "method": "char_span",
            "start_char": 1442,
            "end_char": 1760,
            "start_line": 49,
            "end_line": 53,
            "quote": "1. Stokes relaxation requires Re<0.05 for S-N correction <1%\n2. Terminal velocity needs high viscosity to ensure Re_t<<1 so S-N -> Stokes\n3. Added mass extracted from transfer function at characteristic frequency\n4. Momentum conservation is at machine precision level\n5. Gidaspow equals Ergun in dense regime (eps<0.8)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "5 条备注原文；含 Re_t<<1 等适用条件，属登记不属抽取"
        },
        {
          "asset_id": "A18",
          "asset_class": "section_heading",
          "label": "§6 Error Assessment 节标题",
          "in_report_section": "6. Error Assessment",
          "locator": {
            "method": "char_span",
            "start_char": 1762,
            "end_char": 1784,
            "start_line": 55,
            "end_line": 55,
            "quote": "## 6. Error Assessment",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "节边界锚点"
        },
        {
          "asset_id": "A19",
          "asset_class": "criteria_table",
          "label": "判定表（Criterion/Measured/Threshold/Pass，5 行）",
          "in_report_section": "6. Error Assessment",
          "locator": {
            "method": "char_span",
            "start_char": 1786,
            "end_char": 2013,
            "start_line": 57,
            "end_line": 63,
            "quote": "| Criterion | Measured | Threshold | Pass |\n|-----------|----------|-----------|------|\n| A1 | 0.886% | <=2% | Y |\n| A2 | 0.547% | <=3% | Y |\n| A3 | 0.000% | <=5% | Y |\n| A4 | 0.0000e+00 | <=1% | Y |\n| A5 | 0.000% | <=10% | Y |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "表头+分隔行+5 条判据原文；数值仅登记，复审由平台门计算"
        },
        {
          "asset_id": "A20",
          "asset_class": "verdict_statement",
          "label": "总判定语句 All passed: YES",
          "in_report_section": "6. Error Assessment",
          "locator": {
            "method": "char_span",
            "start_char": 2015,
            "end_char": 2034,
            "start_line": 65,
            "end_line": 65,
            "quote": "**All passed: YES**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown[start_char:end_char] resliced and unique",
            "result": "resolved"
          },
          "note": "报告自述判定；本包不据此标 verified（verification 由平台门计算）"
        },
        {
          "asset_id": "A21",
          "asset_class": "code_reference",
          "label": "A1-A5 校验面实现体（TensorDEM 求解器代码）",
          "in_report_section": "2. Method",
          "locator": {
            "method": "char_span",
            "start_char": 405,
            "end_char": 417,
            "start_line": 10,
            "end_line": 10,
            "quote": "## 2. Method",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "regex (https?://|github\\.com|git@|commit\\s+[0-9a-f]{7,40}|[\\w./-]+\\.py\\b|TensorDEM/[\\w./-]+) over markdown (hits=0)",
            "result": "unresolved"
          },
          "note": "报告以方法名指向实现，但全文不含仓库路径/commit/URL/文件名，无法给出可解析地址"
        },
        {
          "asset_id": "A22",
          "asset_class": "figure_payload",
          "label": "图 A1_stokes_relaxation（图像本体）",
          "in_report_section": "4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1396,
            "end_char": 1427,
            "start_line": 45,
            "end_line": 45,
            "quote": "See embedded figures (5 plots).",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "record.figures[].png_base64|url|path present",
            "result": "absent"
          },
          "note": "报告记录 figures[0] 仅含 name/caption 元数据，无 png_base64/URL；markdown 内无图路径"
        },
        {
          "asset_id": "A23",
          "asset_class": "figure_payload",
          "label": "图 A2_terminal_velocity（图像本体）",
          "in_report_section": "4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1396,
            "end_char": 1427,
            "start_line": 45,
            "end_line": 45,
            "quote": "See embedded figures (5 plots).",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "record.figures[].png_base64|url|path present",
            "result": "absent"
          },
          "note": "figures[1] 仅元数据，无图字节"
        },
        {
          "asset_id": "A24",
          "asset_class": "figure_payload",
          "label": "图 A3_added_mass（图像本体）",
          "in_report_section": "4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1396,
            "end_char": 1427,
            "start_line": 45,
            "end_line": 45,
            "quote": "See embedded figures (5 plots).",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "record.figures[].png_base64|url|path present",
            "result": "absent"
          },
          "note": "figures[2] 仅元数据，无图字节"
        },
        {
          "asset_id": "A25",
          "asset_class": "figure_payload",
          "label": "图 A4_momentum（图像本体）",
          "in_report_section": "4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1396,
            "end_char": 1427,
            "start_line": 45,
            "end_line": 45,
            "quote": "See embedded figures (5 plots).",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "record.figures[].png_base64|url|path present",
            "result": "absent"
          },
          "note": "figures[3] 仅元数据，无图字节"
        },
        {
          "asset_id": "A26",
          "asset_class": "figure_payload",
          "label": "图 A5_ergun（图像本体）",
          "in_report_section": "4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1396,
            "end_char": 1427,
            "start_line": 45,
            "end_line": 45,
            "quote": "See embedded figures (5 plots).",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "record.figures[].png_base64|url|path present",
            "result": "absent"
          },
          "note": "figures[4] 仅元数据，无图字节"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": true,
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "quote_count": 26,
        "quotes_unique_count": 26,
        "char_spans_resliced": true,
        "claims_count": 0,
        "checks": {
          "figure_payload": {
            "figures_declared": 5,
            "figures_with_payload": 0,
            "result": "absent"
          },
          "code_reference": {
            "pattern": "(https?://|github\\.com|git@|commit\\s+[0-9a-f]{7,40}|[\\w./-]+\\.py\\b|TensorDEM/[\\w./-]+)",
            "hits": 0,
            "result": "unresolved"
          },
          "markdown_image_embeds": 0
        }
      }
    }
  },
  "claims": []
}
```
