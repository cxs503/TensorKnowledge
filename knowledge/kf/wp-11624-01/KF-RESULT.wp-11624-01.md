# KF-RESULT wp-11624-01

- report_id: 11624 ｜ source_uri: tensor://reports/11624 ｜ source_field: `markdown`
- source_hash: `sha256:a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33`（本地重算，与契约 source_hash 一致）
- chars: 4253 ｜ bytes_utf8: 5676
- package_id: `wp-11624-01` ｜ task_type: `01-asset-registration` ｜ lane: C ｜ status: draft
- 分层: EEXI | P187-W1-N06 | m

## ① 本工序做了什么

只做一件事：把 report_id=11624 这份报告**登记为资产**——确认它的 markdown 字节哈希、列出正文里
可解析的资产（表格/公式/判据清单/声明/引用），并把记录 metadata 里 4 条只有名字和图注、没有字节也
没有正文锚点的图件声明按缺口登记。**不做抽取**：按契约 `objective.register_assets=true`、
`classify_report_type=false`、`no_forced_claim_generation=true`，`claims` 为空数组；
也**没有**给任何对象打 `verified`（verification 由平台门计算，`provenance.verification_status`
=`not_verified`）。

登记结果：资产 27 条 —— `resolved_in_source` 21 条、
`referenced_unresolved` 2 条（审计链里的代码路径与测试文件，
属 ship-performance-platform 仓，本工作树内不存在）、`declared_absent` 4 条
（4 条图件声明：`figures_with_bytes=0`，正文 0 处锚点）。定位器 27 条，全部复解成功。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/11624`（Bearer token 由 `/auth/login` 取得），
   只取 `markdown` 字段；psql 对本角色 permission denied，故 API 是唯一信道。
2. **落冻结快照**：快照写 `knowledge/kf/wp-11624-01/source_report_11624.md`（UTF-8，仅 json 解码，
   不做换行/空白规整），并断言写回后再读的 sha256 不变。
3. **行号锚定**：以 1-based 行号表登记每条资产（`ASSET_TABLE`），引文由
   `md[start_char:end_char]` 现算，不手抄；每条都校验 `md[start:end] == quote` 且
   `md.count(quote) == 1`（唯一性），失败即整包 FAIL。
4. **记录侧资产**：图件走 JSON pointer（`/figures/0..3`），并机器检查 name/caption 是否出现在正文
   （结果：0/4 出现）以及是否有 png/url/path 字段（无）。
5. **出厂自检**：manifest 过本包钉版 schema（`schemas/asset_manifest.v1.wp-11624-01.schema.json`），
   result 信封过平台 `schemas/kf_result.v1.schema.json`（`additionalProperties:false` 下无多余键）。
6. **独立复核器**：`scripts/kf_wp_11624_01_verify.py` 不读 manifest 自带的 checks，从快照与文件
   重新推导六项验收；`tests/test_kf_wp_11624_01.py` 用 12 条负例证明这些检查真的会红
   （改引文/移 char span/换非唯一引文/加一字节/改 hash/重复 id/无出处 claim/打 verified 章/
   改 package_id/断 pointer/引用他报告）。

一键复跑：

```text
python3 scripts/kf_wp_11624_01_register.py
python3 scripts/kf_wp_11624_01_verify.py
python3 -m pytest tests/test_kf_wp_11624_01.py -q
python3 scripts/kf_wp_11624_01_report.py            # 重建本报告正文与图
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `knowledge/kf/wp-11624-01/asset_manifest.json` | 本工序唯一交付物：27 条资产 + 27 条定位器 + 4 条图件缺口 + 空 claims（sha256 `3c4ab994158ebe61…`） |
| `knowledge/kf/wp-11624-01/kf_result.json` | kf_result.v1 结果信封（outputs.asset_manifest.json 内嵌 manifest 副本＋工件哈希） |
| `knowledge/kf/wp-11624-01/source_report_11624.md` | 源报告冻结快照（4253 字符 / 5676 字节） |
| `knowledge/kf/wp-11624-01/source_record.json` | 记录侧字段（title/scenario/mission/tags/figures，不含 markdown） |
| `knowledge/kf/wp-11624-01/verification_report.json` | 独立复核器输出（逐项 pass/fail + 每条资产的复解明细） |
| `scripts/kf_wp_11624_01_register.py` / `_verify.py` / `_report.py` | 登记 / 复核 / 出图出报告，三个脚本可离线复跑 |
| `schemas/asset_manifest.v1.wp-11624-01.schema.json` | 本包钉版 schema（把 `schema_pass` 变成可复算项，且不动别包已钉死的 schema） |
| `tests/test_kf_wp_11624_01.py` | 6 正例 + 12 负例 |
| `docs/wp-11624-01/*` | push gate 会丢 `artifacts/**`，故以上文档类工件在 docs/ 留字节一致镜像 |

图：`docs/wp-11624-01/figs/wp11624_01_fig1_eexi_cii.png`（sha256 `f7dae60165465567…`，138709 字节）。图为**登记内容的可视化**：
数值逐字解析自资产 A12 的表格引文，A–E 分档系数解析自资产 A11 的判据引文，不是对上游数字的复核。

## ④ 证据定位表（字段 → 原文引文片段）

多行资产在上表只显示**首行**（保持逐字，不截断中段语义）；完整逐字引文与 char span 见 JSON 块中
`outputs.asset_manifest.json.assets[].locator.quote`。

| 资产 | 族 | 解析状态 | 行区间 | 定位 | 原文引文（首行，逐字） |
|---|---|---|---|---|---|
| A01 | report_markdown | resolved_in_source | 1–159（全文） | `md[0:4253]` | # EEXI/CII 合规验证面报告 |
| A02 | heading | resolved_in_source | 1–1 | `md[0:18]` | # EEXI/CII 合规验证面报告 |
| A03 | scenario_anchor | resolved_in_source | 3–3 | `md[20:84]` | ## P187-W1-N06: MEPC.392(81) Attained vs Required + CII 年度评级 A-E |
| A04 | background_statement | resolved_in_source | 11–11 | `md[117:213]` | 国际海事组织（IMO）海上环境保护委员会第 81 届会议（MEPC.392(81)）通过了现有船舶能效指数（EEXI）和碳强度指标（CII）的强制性要求。本验证面建立完整的合规计算与判定能力： |
| A05 | definition_pair | resolved_in_source | 13–14 | `md[215:372]` | - **EEXI（Existing Ship Energy Efficiency Index）**：衡量船舶设计能效，Attained EEXI 须 ≤ Required EEXI |
| A06 | table | resolved_in_source | 18–24 | `md[388:605]` | \| 法规 \| 内容 \| 状态 \| |
| A07 | parameter_set | resolved_in_source | 28–32 | `md[622:879]` | \| 船型 \| DWT [t] \| MCR [kW] \| V_ref [kn] \| 年航程 [nm] \| |
| A08 | formula_block | resolved_in_source | 44–44 | `md[973:1041]` | EEXI = Σ(P_i × SFOC_i × CF_i) / (f_i × f_c × f_l × Capacity × V_ref) |
| A09 | formula_block | resolved_in_source | 49–49 | `md[1082:1155]` | EEXI = Σ_i [(P_i × SFOC_i × CF_i) / (f_i × f_c × f_l × Capacity × V_ref)] |
| A10 | tolerance_declaration | resolved_in_source | 52–52 | `md[1161:1188]` | 两种算法应给出完全相同的结果（相对差 < 1e-9）。 |
| A11 | decision_rule | resolved_in_source | 57–61 | `md[1236:1424]` | - A: CII ≤ 0.86 × Required |
| A12 | result_table | resolved_in_source | 69–73 | `md[1468:1826]` | \| 船型 \| Attained EEXI \| Required EEXI \| 合规 \| Attained CII \| Required CII \| 评级 \| |
| A13 | criterion_test_log | resolved_in_source | 77–92 | `md[1846:3123]` | - **C1**: ✓ PASS — V_ref=1e-6kn → EEXI=4.54e+07 (expect >1e6) |
| A14 | count_statement | resolved_in_source | 94–94 | `md[3125:3143]` | **总结**: 16/16 判据通过 |
| A15 | capability_declaration | resolved_in_source | 120–123 | `md[3426:3513]` | - EEXI 双算法互裁（直接公式法 + 分项累加法） |
| A16 | limitation_set | resolved_in_source | 127–130 | `md[3527:3685]` | 1. **参考线系数**：转录自 MEPC.308(73)，离线环境未回读规则原文，证据等级 WITHHELD |
| A17 | scope_declaration | resolved_in_source | 134–136 | `md[3701:3836]` | - 船型：bulk_carrier, tanker, container_ship, gas_carrier, lng_carrier 等 |
| A18 | error_table | resolved_in_source | 142–147 | `md[3855:4095]` | \| 判据 \| 基准 \| 计算值 \| 误差 \| 是否 <3% \| |
| A19 | conclusion_statement | resolved_in_source | 149–149 | `md[4097:4119]` | **结论**: 全部判据通过，算法实现正确。 |
| A20 | code_path_reference | referenced_unresolved | 155–155 | `md[4134:4180]` | - 代码路径: `backend/modules/eexi_cii_compliance/` |
| A21 | test_reference | referenced_unresolved | 156–156 | `md[4181:4224]` | - 测试文件: `tests/test_eexi_cii_compliance.py` |
| A22 | count_statement | resolved_in_source | 157–157 | `md[4225:4241]` | - 测试数量: 26 项全部通过 |
| A23 | provenance_statement | resolved_in_source | 158–158 | `md[4242:4252]` | - 生成时间: 自动 |
| A24 | figure_declaration | declared_absent | — | `record /figures/0` | 三船型 EEXI 达到值与要求值对比 |
| A25 | figure_declaration | declared_absent | — | `record /figures/1` | CII 评级边界与典型船型位置 |
| A26 | figure_declaration | declared_absent | — | `record /figures/2` | 双算法互裁验证（直接公式法 vs 分项累加法） |
| A27 | figure_declaration | declared_absent | — | `record /figures/3` | 参数敏感性分析 |

CII/Required 比值（由 A12 引文程序化相除，非手算）＋用 A11 分档系数反推档位与报告评级列对照
（这是**登记内容的内部一致性检查**，不是对上游计算正确性的复核）：

| 船型 | Attained CII | Required CII | CII/Required | 按 A11 分档反推 | 报告评级 | 一致 |
|---|---|---|---|---|---|---|
| Capesize Bulk Carrier | 2.820 | 2.274 | 1.240 | E | E | ✓ |
| 18000TEU Container Ship | 6.762 | 4.516 | 1.497 | E | E | ✓ |
| VLCC Oil Tanker | 2.371 | 2.047 | 1.158 | D | D | ✓ |

## ⑤ 注意点与局限

1. **只登记不抽取**：`claims=[]` 是契约要求，不等于报告没有结论句——结论句已作为资产 A19 登记，
   其成立与否不由本工序判定。
2. **两处计数口径不同，并列登记不解释**：A14「16/16 判据通过」与 A22「测试数量: 26 项全部通过」
   是判据集合与测试集合两回事，本工序不合并、不换算、不裁定。
3. **审计链不可解析**：`backend/modules/eexi_cii_compliance/` 与 `tests/test_eexi_cii_compliance.py`
   在本工作树内不存在（属 ship-performance-platform 仓），因此「测试真的跑过」无法在本包内取证，
   登记为 `referenced_unresolved`，不做存在性断言。
4. **4 条图件声明是缺口不是资产**：记录 metadata 有 name/caption，但无 png/url/path，正文 0 处提及
   （机器检索 name 与 caption 均 0 命中），故 `declared_absent`；本工序不声称图件曾产出。
5. **上游数值未复核**：A12/A13/A18 的数值一律按原文登记；报告 A16 自报「离线环境未回读规则原文，
   证据等级 WITHHELD」，该不确定度原样保留在本清单里，未被本工序消解。
6. **生成时间不可溯源**：A23「生成时间: 自动」是字面文本而非时间戳，无法作为时间证据。
7. **schema 本地钉版**：仓库内 `schemas/asset_manifest.v1.schema.json` 把 package_id/report_id
   钉死为 `wp-448-01`/`448`，直接用会把本包判红；本包另立钉版 schema（结构同源），
   若平台侧 canonical schema 另有规定，以平台门为准、本工件再修。

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 结果 | 证据 |
|---|---|---|
| valid_json | ✓ 通过 | 三个 JSON 均 `json.loads` 严格解析成功（verifier 直接读文件） |
| schema_pass | ✓ 通过 | manifest 过本包钉版 schema；result 过 `schemas/kf_result.v1.schema.json`（平台 schema `additionalProperties:false`，顶层键只有 package_id/task_type/report_id/provenance/outputs/claims，且 claims 为空数组） |
| source_locator_resolvable | ✓ 通过 | 27/27 条：markdown 侧 `md[start:end]==quote` 且 `count==1`；record 侧 pointer 可解析且 quote 在 pointer 值内 |
| source_hash_matches | ✓ 通过 | 快照 sha256 = 契约 `sha256:a5a0885e7f86a7d7…`；manifest 与 provenance 三处一致；chars 4253 = 契约 4253 |
| no_duplicate_ids | ✓ 通过 | 27 个 asset_id 无重复，且 locators 的 id 集与资产集完全相同 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ 通过（空集，契约允许） | claims=0；12 条负例证明「无出处 claim」会被判红；无任何对象带 verified 章，provenance.verification_status=`not_verified` |

补充：`single_report_scope` ✓（全包只出现 `tensor://reports/11624`，
无他 report_id 引用）、`durable_mirror` ✓（docs/ 镜像与 knowledge/ 字节一致）。
测试：`python3 -m pytest tests/test_kf_wp_11624_01.py -q` → 18 passed。
无失败项（honest-FAIL 无需粉饰）。

## 结果 JSON（唯一一个 json 代码块，原样提交）

```json
{
  "package_id": "wp-11624-01",
  "task_type": "01-asset-registration",
  "report_id": "11624",
  "provenance": {
    "source_uri": "tensor://reports/11624",
    "source_field": "markdown",
    "source_hash": "sha256:a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33",
    "source_chars": 4253,
    "source_bytes_utf8": 5676,
    "source_title": "EEXI/CII 合规验证面：MEPC.392(81) Attained vs Required + CII 年度评级 A-E",
    "scenario_key": "P187-W1-N06",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-11624-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/11624 -> field `markdown`",
    "local_copy": "knowledge/kf/wp-11624-01/source_report_11624.md",
    "generator": "scripts/kf_wp_11624_01_register.py",
    "verifier": "scripts/kf_wp_11624_01_verify.py",
    "emitted_at": "2026-11-12T02:23:18+00:00",
    "producer": "scripts/kf_wp_11624_01_register.py",
    "verification_status": "not_verified",
    "notes": "verification is computed by the platform gate; this envelope only declares provenance and the registered asset manifest"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-11624-01",
      "task_type": "01-asset-registration",
      "report_id": "11624",
      "lane": "C",
      "generated_at": "2026-11-12T02:23:18+00:00",
      "producer": "scripts/kf_wp_11624_01_register.py",
      "repro_cmd": "python3 scripts/kf_wp_11624_01_register.py",
      "source": {
        "uri": "tensor://reports/11624",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33",
        "chars": 4253,
        "bytes_utf8": 5676,
        "title": "EEXI/CII 合规验证面：MEPC.392(81) Attained vs Required + CII 年度评级 A-E",
        "scenario_key": "P187-W1-N06",
        "record_id": 11624,
        "record_mission_id": 9810,
        "record_status": "published",
        "record_created_at": "2026-11-10T14:51:38.013541+00:00",
        "record_tags": [
          "EEXI",
          "CII",
          "IMO",
          "MEPC.392(81)",
          "compliance",
          "dual-algorithm"
        ],
        "stored_as": "UTF-8 text, exactly the bytes returned in field `markdown` (json decode only; no normalisation, no newline rewriting)",
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/11624 -> field `markdown`",
        "local_copy": "knowledge/kf/wp-11624-01/source_report_11624.md",
        "hash_matches_contract": true
      },
      "counts": {
        "assets": 27,
        "by_kind": {
          "report_markdown": 1,
          "heading": 1,
          "scenario_anchor": 1,
          "background_statement": 1,
          "definition_pair": 1,
          "table": 1,
          "parameter_set": 1,
          "formula_block": 2,
          "tolerance_declaration": 1,
          "decision_rule": 1,
          "result_table": 1,
          "criterion_test_log": 1,
          "count_statement": 2,
          "capability_declaration": 1,
          "limitation_set": 1,
          "scope_declaration": 1,
          "error_table": 1,
          "conclusion_statement": 1,
          "code_path_reference": 1,
          "test_reference": 1,
          "provenance_statement": 1,
          "figure_declaration": 4
        },
        "by_resolution": {
          "resolved_in_source": 21,
          "referenced_unresolved": 2,
          "declared_absent": 4
        },
        "resolved_in_source": 21,
        "referenced_unresolved": 2,
        "declared_absent": 4,
        "locators": 27,
        "locators_resolved": 27,
        "figures_declared_in_record": 4,
        "figures_with_bytes": 0,
        "figures_with_body_anchor": 0,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "kind": "report_markdown",
          "label": "报告全文（markdown，唯一字节资产）",
          "locator": {
            "source_field": "markdown",
            "method": "document",
            "start_char": 0,
            "end_char": 4253,
            "start_line": 1,
            "end_line": 159,
            "line_base": 1,
            "quote": "# EEXI/CII 合规验证面报告",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "document_scope",
            "result": "resolved",
            "sha256": "a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33",
            "chars": 4253,
            "bytes_utf8": 5676,
            "byte_identical_to_contract_hash": true
          },
          "note": "整篇 markdown 即源资产；method=document 覆盖 [0,len)，quote 为 H1 首行",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A02",
          "kind": "heading",
          "label": "报告标题行",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 0,
            "end_char": 18,
            "start_line": 1,
            "end_line": 1,
            "line_base": 1,
            "quote": "# EEXI/CII 合规验证面报告",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "H1 标题；与 API title 字段同源",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A03",
          "kind": "scenario_anchor",
          "label": "场景锚点标题（P187-W1-N06）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 20,
            "end_char": 84,
            "start_line": 3,
            "end_line": 3,
            "line_base": 1,
            "quote": "## P187-W1-N06: MEPC.392(81) Attained vs Required + CII 年度评级 A-E",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "H2 场景行：MEPC.392(81) Attained vs Required + CII 年度评级 A-E",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A04",
          "kind": "background_statement",
          "label": "物理背景陈述：EEXI/CII 强制性要求",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 117,
            "end_char": 213,
            "start_line": 11,
            "end_line": 11,
            "line_base": 1,
            "quote": "国际海事组织（IMO）海上环境保护委员会第 81 届会议（MEPC.392(81)）通过了现有船舶能效指数（EEXI）和碳强度指标（CII）的强制性要求。本验证面建立完整的合规计算与判定能力：",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "单段背景陈述，登记原文不复核法条",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A05",
          "kind": "definition_pair",
          "label": "EEXI 与 CII 定义（合规方向 / 评级逻辑）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 215,
            "end_char": 372,
            "start_line": 13,
            "end_line": 14,
            "line_base": 1,
            "quote": "- **EEXI（Existing Ship Energy Efficiency Index）**：衡量船舶设计能效，Attained EEXI 须 ≤ Required EEXI\n- **CII（Carbon Intensity Indicator）**：衡量营运能效，年度评级 A-E，D/E 级须提交改进计划",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "两条定义原文；D/E 级须提交改进计划",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A06",
          "kind": "table",
          "label": "法规框架表（5 项 MEPC 决议 + 状态列）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 388,
            "end_char": 605,
            "start_line": 18,
            "end_line": 24,
            "line_base": 1,
            "quote": "| 法规 | 内容 | 状态 |\n|------|------|------|\n| MEPC.308(73) | EEDI 参考线系数 | 已实现 |\n| MEPC.328(76) | EEXI 削减率 | 已实现 |\n| MEPC.353(78) | CII 参考线（G2） | 已实现 |\n| MEPC.354(78) | CII 评级（G4） | 已实现 |\n| MEPC.338(76) | CII 年度折减率 | 已实现 |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表头+分隔+5 行；状态列为上游自报「已实现」，本工序只登记不复核",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A07",
          "kind": "parameter_set",
          "label": "三船型参数表（DWT / MCR / V_ref / 年航程）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 622,
            "end_char": 879,
            "start_line": 28,
            "end_line": 32,
            "line_base": 1,
            "quote": "| 船型 | DWT [t] | MCR [kW] | V_ref [kn] | 年航程 [nm] |\n|------|---------|----------|------------|-------------|\n| Capesize Bulk Carrier | 180,000 | - | 14.0 | - |\n| 18000TEU Container Ship | 200,000 | - | 22.0 | - |\n| VLCC Oil Tanker | 320,000 | - | 15.0 | - |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表头+分隔+3 行；MCR 与年航程两列原文字面为「-」，属报告未给出的字段",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A08",
          "kind": "formula_block",
          "label": "EEXI 直接公式法（Direct Formula）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 973,
            "end_char": 1041,
            "start_line": 44,
            "end_line": 44,
            "line_base": 1,
            "quote": "EEXI = Σ(P_i × SFOC_i × CF_i) / (f_i × f_c × f_l × Capacity × V_ref)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "fenced code 块内的公式行；围栏行见 43/45",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A09",
          "kind": "formula_block",
          "label": "EEXI 分项累加法（Itemized Summation）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1082,
            "end_char": 1155,
            "start_line": 49,
            "end_line": 49,
            "line_base": 1,
            "quote": "EEXI = Σ_i [(P_i × SFOC_i × CF_i) / (f_i × f_c × f_l × Capacity × V_ref)]",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "与 A08 数学等价、代码路径不同的第二实现公式",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A10",
          "kind": "tolerance_declaration",
          "label": "双算法等价判据（相对差 < 1e-9）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1161,
            "end_char": 1188,
            "start_line": 52,
            "end_line": 52,
            "line_base": 1,
            "quote": "两种算法应给出完全相同的结果（相对差 < 1e-9）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "可执行判据的阈值原文",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A11",
          "kind": "decision_rule",
          "label": "CII 评级边界（G4 dd 向量 A-E）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1236,
            "end_char": 1424,
            "start_line": 57,
            "end_line": 61,
            "line_base": 1,
            "quote": "- A: CII ≤ 0.86 × Required\n- B: 0.86 × Required < CII ≤ 0.94 × Required\n- C: 0.94 × Required < CII ≤ 1.06 × Required\n- D: 1.06 × Required < CII ≤ 1.18 × Required\n- E: CII > 1.18 × Required",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "五档边界不等式原文；用于 A12 评级判定的规则集",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A12",
          "kind": "result_table",
          "label": "三船型 EEXI/CII 计算结果表",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1468,
            "end_char": 1826,
            "start_line": 69,
            "end_line": 73,
            "line_base": 1,
            "quote": "| 船型 | Attained EEXI | Required EEXI | 合规 | Attained CII | Required CII | 评级 |\n|------|---------------|---------------|------|--------------|--------------|------|\n| Capesize Bulk Carrier | 3.396 | 2.396 | ✗ | 2.820 | 2.274 | E |\n| 18000TEU Container Ship | 7.433 | 11.986 | ✓ | 6.762 | 4.516 | E |\n| VLCC Oil Tanker | 2.531 | 2.007 | ✗ | 2.371 | 2.047 | D |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表头+分隔+3 行；数值为上游自报结果，本工序只登记不作二次计算",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A13",
          "kind": "criterion_test_log",
          "label": "机器可算判据 C1–C6c 逐条结果（16 条）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1846,
            "end_char": 3123,
            "start_line": 77,
            "end_line": 92,
            "line_base": 1,
            "quote": "- **C1**: ✓ PASS — V_ref=1e-6kn → EEXI=4.54e+07 (expect >1e6)\n- **C2**: ✓ PASS — Fuel=0 → CII=0.0\n- **C3_bulk_carrier**: ✓ PASS — Capesize Bulk Carrier: direct=3.3964166667, itemized=3.3964166667, rel_diff=0.00e+00\n- **C3_container_ship**: ✓ PASS — 18000TEU Container Ship: direct=7.4327522727, itemized=7.4327522727, rel_diff=0.00e+00\n- **C3_tanker**: ✓ PASS — VLCC Oil Tanker: direct=2.5305200000, itemized=2.5305200000, rel_diff=1.75e-16\n- **C4**: ✓ PASS — Required EEXI (200000 DWT bulk) = 2.2781 (expect [2.0, 3.0])\n- **C5_A_bulk_carrier**: ✓ PASS — Capesize Bulk Carrier: CII=1.82 < 1.96 → A (expect A)\n- **C5_E_bulk_carrier**: ✓ PASS — Capesize Bulk Carrier: CII=2.96 > 2.68 → E (expect E)\n- **C5_A_container_ship**: ✓ PASS — 18000TEU Container Ship: CII=3.61 < 3.88 → A (expect A)\n- **C5_E_container_ship**: ✓ PASS — 18000TEU Container Ship: CII=5.87 > 5.33 → E (expect E)\n- **C5_A_tanker**: ✓ PASS — VLCC Oil Tanker: CII=1.64 < 1.76 → A (expect A)\n- **C5_E_tanker**: ✓ PASS — VLCC Oil Tanker: CII=2.66 > 2.42 → E (expect E)\n- **C6a**: ✓ PASS — DWT=0.01t → EEXI=5.84e+07 (expect >1e6)\n- **C6b_EEXI**: ✓ PASS — CF=0 → EEXI=0.0 (expect 0)\n- **C6b_CII**: ✓ PASS — CO2=0 → CII=0.0 (expect 0)\n- **C6c**: ✓ PASS — V_ref×2 → EEXI ratio=0.500000 (expect 0.5, rel_diff=0.00e+00)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "16 行判据原文；每行含判据号、期望与实测字面值，属上游自报通过",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A14",
          "kind": "count_statement",
          "label": "判据汇总计数（16/16 判据通过）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 3125,
            "end_char": 3143,
            "start_line": 94,
            "end_line": 94,
            "line_base": 1,
            "quote": "**总结**: 16/16 判据通过",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "计数声明；与 A21 的「26 项全部通过」口径不同（判据 vs 测试），本工序并列登记不解释",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A15",
          "kind": "capability_declaration",
          "label": "5.1 已实现能力清单（4 条）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 3426,
            "end_char": 3513,
            "start_line": 120,
            "end_line": 123,
            "line_base": 1,
            "quote": "- EEXI 双算法互裁（直接公式法 + 分项累加法）\n- CII A-E 五档评级（MEPC.354(78) G4）\n- 三船型闭环验证\n- 六项机器可算判据（C1-C6）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "上游自报能力清单原文",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A16",
          "kind": "limitation_set",
          "label": "5.2 局限（4 条，含 WITHHELD 自报）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 3527,
            "end_char": 3685,
            "start_line": 127,
            "end_line": 130,
            "line_base": 1,
            "quote": "1. **参考线系数**：转录自 MEPC.308(73)，离线环境未回读规则原文，证据等级 WITHHELD\n2. **营运剖面**：使用典型值，实际船舶营运条件可能显著不同\n3. **创新技术**：未考虑 f_eff 修正（创新技术节能效果）\n4. **冰区修正**：f_i 默认 1.0，冰区航行船舶需额外修正",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "含「离线环境未回读规则原文，证据等级 WITHHELD」原文，属重要不确定度声明",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A17",
          "kind": "scope_declaration",
          "label": "5.3 适用范围（船型 / 燃料 / 年份）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 3701,
            "end_char": 3836,
            "start_line": 134,
            "end_line": 136,
            "line_base": 1,
            "quote": "- 船型：bulk_carrier, tanker, container_ship, gas_carrier, lng_carrier 等\n- 燃料：HFO, LFO, MDO, LNG, Methanol, LPG\n- 年份：2023-2026（CII 折减率已定义）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "适用域声明的三条原文",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A18",
          "kind": "error_table",
          "label": "误差判定表（4 行，基准 vs 计算值 vs <3%）",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 3855,
            "end_char": 4095,
            "start_line": 142,
            "end_line": 147,
            "line_base": 1,
            "quote": "| 判据 | 基准 | 计算值 | 误差 | 是否 <3% |\n|------|------|--------|------|----------|\n| C3 双算法差 | <1e-9 | 见 3.2 | ~0 | ✓ |\n| C4 Required EEXI | [2.0, 3.0] | 见 3.2 | - | ✓ |\n| C5 评级一致性 | A/E 边界 | 见 3.2 | - | ✓ |\n| C6c V_ref 加倍 | 0.5 | 见 3.2 | <1% | ✓ |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表头+分隔+4 行；判据值一列原文指向 3.2 节而非具体数字",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A19",
          "kind": "conclusion_statement",
          "label": "误差判定结论句",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 4097,
            "end_char": 4119,
            "start_line": 149,
            "end_line": 149,
            "line_base": 1,
            "quote": "**结论**: 全部判据通过，算法实现正确。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "上游结论原文；本工序只登记，结论成立与否由平台门判定",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A20",
          "kind": "code_path_reference",
          "label": "审计链：代码路径 backend/modules/eexi_cii_compliance/",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 4134,
            "end_char": 4180,
            "start_line": 155,
            "end_line": 155,
            "line_base": 1,
            "quote": "- 代码路径: `backend/modules/eexi_cii_compliance/`",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "worktree_relative_path": "backend/modules/eexi_cii_compliance",
            "worktree_root": "/root/tp-agent/work/m15728",
            "exists_in_worktree": false,
            "detail": "path named by the report is not present in this worktree (it belongs to the ship-performance-platform repository), so this package cannot resolve it; existence is not asserted"
          },
          "note": "属 ship-performance-platform 仓；本工作树内不存在（见 resolution_check.exists_in_worktree=false）",
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A21",
          "kind": "test_reference",
          "label": "审计链：测试文件 tests/test_eexi_cii_compliance.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 4181,
            "end_char": 4224,
            "start_line": 156,
            "end_line": 156,
            "line_base": 1,
            "quote": "- 测试文件: `tests/test_eexi_cii_compliance.py`",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "worktree_relative_path": "tests/test_eexi_cii_compliance.py",
            "worktree_root": "/root/tp-agent/work/m15728",
            "exists_in_worktree": false,
            "detail": "path named by the report is not present in this worktree (it belongs to the ship-performance-platform repository), so this package cannot resolve it; existence is not asserted"
          },
          "note": "本工作树内不存在，无法在本包内解析测试代码本体",
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A22",
          "kind": "count_statement",
          "label": "审计链：测试数量 26 项全部通过",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 4225,
            "end_char": 4241,
            "start_line": 157,
            "end_line": 157,
            "line_base": 1,
            "quote": "- 测试数量: 26 项全部通过",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "上游自报计数原文；与 A14 的 16/16 判据属不同集合，本工序不合并计数",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A23",
          "kind": "provenance_statement",
          "label": "审计链：生成时间「自动」",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 4242,
            "end_char": 4252,
            "start_line": 158,
            "end_line": 158,
            "line_base": 1,
            "quote": "- 生成时间: 自动",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "生成时间字段原文字面为「自动」，非可解析时间戳，无法作为时间溯源",
          "existence_asserted_by_worker": true
        },
        {
          "asset_id": "A24",
          "kind": "figure_declaration",
          "label": "图件声明（记录 metadata）：eexi_comparison — 三船型 EEXI 达到值与要求值对比",
          "locator": {
            "source_field": "record",
            "method": "record_pointer",
            "start_char": 0,
            "end_char": 0,
            "start_line": 0,
            "end_line": 0,
            "line_base": 1,
            "pointer": "/figures/0",
            "quote": "三船型 EEXI 达到值与要求值对比",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "record_figure_has_bytes_and_body_anchor",
            "result": "absent",
            "bytes_present": false,
            "body_tokens_found": [],
            "body_anchor_found": false,
            "detail": "记录里有 name/caption，但无 png/url/path 字段，且 name 与 caption 在 markdown 正文中均无出现（body_tokens_found 为空）"
          },
          "note": "记录 metadata 中的图件声明：无 png/字节、无正文坐标（figures_with_bytes=0），登记为 declared_absent，存在性不由本工序断言",
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A25",
          "kind": "figure_declaration",
          "label": "图件声明（记录 metadata）：cii_rating — CII 评级边界与典型船型位置",
          "locator": {
            "source_field": "record",
            "method": "record_pointer",
            "start_char": 0,
            "end_char": 0,
            "start_line": 0,
            "end_line": 0,
            "line_base": 1,
            "pointer": "/figures/1",
            "quote": "CII 评级边界与典型船型位置",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "record_figure_has_bytes_and_body_anchor",
            "result": "absent",
            "bytes_present": false,
            "body_tokens_found": [],
            "body_anchor_found": false,
            "detail": "记录里有 name/caption，但无 png/url/path 字段，且 name 与 caption 在 markdown 正文中均无出现（body_tokens_found 为空）"
          },
          "note": "记录 metadata 中的图件声明：无 png/字节、无正文坐标（figures_with_bytes=0），登记为 declared_absent，存在性不由本工序断言",
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A26",
          "kind": "figure_declaration",
          "label": "图件声明（记录 metadata）：dual_algorithm — 双算法互裁验证（直接公式法 vs 分项累加法）",
          "locator": {
            "source_field": "record",
            "method": "record_pointer",
            "start_char": 0,
            "end_char": 0,
            "start_line": 0,
            "end_line": 0,
            "line_base": 1,
            "pointer": "/figures/2",
            "quote": "双算法互裁验证（直接公式法 vs 分项累加法）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "record_figure_has_bytes_and_body_anchor",
            "result": "absent",
            "bytes_present": false,
            "body_tokens_found": [],
            "body_anchor_found": false,
            "detail": "记录里有 name/caption，但无 png/url/path 字段，且 name 与 caption 在 markdown 正文中均无出现（body_tokens_found 为空）"
          },
          "note": "记录 metadata 中的图件声明：无 png/字节、无正文坐标（figures_with_bytes=0），登记为 declared_absent，存在性不由本工序断言",
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A27",
          "kind": "figure_declaration",
          "label": "图件声明（记录 metadata）：sensitivity — 参数敏感性分析",
          "locator": {
            "source_field": "record",
            "method": "record_pointer",
            "start_char": 0,
            "end_char": 0,
            "start_line": 0,
            "end_line": 0,
            "line_base": 1,
            "pointer": "/figures/3",
            "quote": "参数敏感性分析",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "record_figure_has_bytes_and_body_anchor",
            "result": "absent",
            "bytes_present": false,
            "body_tokens_found": [],
            "body_anchor_found": false,
            "detail": "记录里有 name/caption，但无 png/url/path 字段，且 name 与 caption 在 markdown 正文中均无出现（body_tokens_found 为空）"
          },
          "note": "记录 metadata 中的图件声明：无 png/字节、无正文坐标（figures_with_bytes=0），登记为 declared_absent，存在性不由本工序断言",
          "existence_asserted_by_worker": false
        }
      ],
      "record_figures": [
        {
          "pointer": "/figures/0",
          "name": "eexi_comparison",
          "caption": "三船型 EEXI 达到值与要求值对比",
          "body_tokens_found": []
        },
        {
          "pointer": "/figures/1",
          "name": "cii_rating",
          "caption": "CII 评级边界与典型船型位置",
          "body_tokens_found": []
        },
        {
          "pointer": "/figures/2",
          "name": "dual_algorithm",
          "caption": "双算法互裁验证（直接公式法 vs 分项累加法）",
          "body_tokens_found": []
        },
        {
          "pointer": "/figures/3",
          "name": "sensitivity",
          "caption": "参数敏感性分析",
          "body_tokens_found": []
        }
      ],
      "identity_facts": [
        {
          "field": "/title",
          "value": "EEXI/CII 合规验证面：MEPC.392(81) Attained vs Required + CII 年度评级 A-E",
          "matches_contract_title": true,
          "locator": {
            "source_field": "record",
            "pointer": "/title"
          }
        },
        {
          "field": "/scenario_key",
          "value": "P187-W1-N06",
          "matches_contract_scenario": true,
          "locator": {
            "source_field": "record",
            "pointer": "/scenario_key"
          }
        },
        {
          "field": "/id",
          "value": 11624,
          "locator": {
            "source_field": "record",
            "pointer": "/id"
          }
        },
        {
          "field": "/mission_id",
          "value": 9810,
          "locator": {
            "source_field": "record",
            "pointer": "/mission_id"
          }
        },
        {
          "field": "/status",
          "value": "published",
          "locator": {
            "source_field": "record",
            "pointer": "/status"
          }
        }
      ],
      "locators": [
        {
          "id": "A01",
          "check": "document_scope",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 18
        },
        {
          "id": "A02",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 18
        },
        {
          "id": "A03",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 64
        },
        {
          "id": "A04",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 96
        },
        {
          "id": "A05",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 157
        },
        {
          "id": "A06",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 217
        },
        {
          "id": "A07",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 257
        },
        {
          "id": "A08",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 68
        },
        {
          "id": "A09",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 73
        },
        {
          "id": "A10",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 27
        },
        {
          "id": "A11",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 188
        },
        {
          "id": "A12",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 358
        },
        {
          "id": "A13",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 1277
        },
        {
          "id": "A14",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 18
        },
        {
          "id": "A15",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 87
        },
        {
          "id": "A16",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 158
        },
        {
          "id": "A17",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 135
        },
        {
          "id": "A18",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 240
        },
        {
          "id": "A19",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 22
        },
        {
          "id": "A20",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 46
        },
        {
          "id": "A21",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 43
        },
        {
          "id": "A22",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 16
        },
        {
          "id": "A23",
          "check": "substring_unique_char_span",
          "resolved": true,
          "char_span_matches_quote": true,
          "occurrences": 1,
          "line_in_range": true,
          "quote_len": 10
        },
        {
          "id": "A24",
          "check": "record_pointer_present",
          "resolved": true,
          "char_span_matches_quote": null,
          "occurrences": 1,
          "line_in_range": null,
          "quote_len": 18
        },
        {
          "id": "A25",
          "check": "record_pointer_present",
          "resolved": true,
          "char_span_matches_quote": null,
          "occurrences": 1,
          "line_in_range": null,
          "quote_len": 15
        },
        {
          "id": "A26",
          "check": "record_pointer_present",
          "resolved": true,
          "char_span_matches_quote": null,
          "occurrences": 1,
          "line_in_range": null,
          "quote_len": 23
        },
        {
          "id": "A27",
          "check": "record_pointer_present",
          "resolved": true,
          "char_span_matches_quote": null,
          "occurrences": 1,
          "line_in_range": null,
          "quote_len": 7
        }
      ],
      "claims": [],
      "claims_empty_reason": "工作包契约 objective.register_assets=true / objective.classify_report_type=false / constraints.no_forced_claim_generation=true，notes 明确 claims 允许为空数组：本工序只登记资产与定位，不作 claim 抽取，也不给任何对象打 verified 标记（verification 由平台门计算）。",
      "unresolved": [
        {
          "asset_id": "A20",
          "label": "审计链：代码路径 backend/modules/eexi_cii_compliance/",
          "resolution": "referenced_unresolved",
          "reason": "属 ship-performance-platform 仓；本工作树内不存在（见 resolution_check.exists_in_worktree=false）"
        },
        {
          "asset_id": "A21",
          "label": "审计链：测试文件 tests/test_eexi_cii_compliance.py",
          "resolution": "referenced_unresolved",
          "reason": "本工作树内不存在，无法在本包内解析测试代码本体"
        },
        {
          "asset_id": "A24",
          "label": "图件声明（记录 metadata）：eexi_comparison — 三船型 EEXI 达到值与要求值对比",
          "resolution": "declared_absent",
          "reason": "记录 metadata 中的图件声明：无 png/字节、无正文坐标（figures_with_bytes=0），登记为 declared_absent，存在性不由本工序断言"
        },
        {
          "asset_id": "A25",
          "label": "图件声明（记录 metadata）：cii_rating — CII 评级边界与典型船型位置",
          "resolution": "declared_absent",
          "reason": "记录 metadata 中的图件声明：无 png/字节、无正文坐标（figures_with_bytes=0），登记为 declared_absent，存在性不由本工序断言"
        },
        {
          "asset_id": "A26",
          "label": "图件声明（记录 metadata）：dual_algorithm — 双算法互裁验证（直接公式法 vs 分项累加法）",
          "resolution": "declared_absent",
          "reason": "记录 metadata 中的图件声明：无 png/字节、无正文坐标（figures_with_bytes=0），登记为 declared_absent，存在性不由本工序断言"
        },
        {
          "asset_id": "A27",
          "label": "图件声明（记录 metadata）：sensitivity — 参数敏感性分析",
          "resolution": "declared_absent",
          "reason": "记录 metadata 中的图件声明：无 png/字节、无正文坐标（figures_with_bytes=0），登记为 declared_absent，存在性不由本工序断言"
        }
      ],
      "integrity": {
        "quote_uniqueness": "每条 markdown 引文均已本地校验：md[start_char:end_char] == quote 且 md.count(quote) == 1（见 locators[].check=substring_unique_char_span）",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "no_duplicate_ids": true,
        "duplicate_ids": [],
        "no_verified_marks": true
      },
      "checks": {
        "source_hash_matches_contract": true,
        "chars_match_contract": true,
        "all_locators_resolved": true,
        "no_duplicate_ids": true,
        "claims_empty_by_contract": true,
        "no_verified_marks_emitted": true,
        "single_report_scope": true
      },
      "limitations": [
        "只登记、不抽取：claims 为空是契约要求，不代表报告没有结论句（A19 已登记结论原文）。",
        "referenced_unresolved 的两条审计链路径属 ship-performance-platform，本工作树无法解析；本工序不断言其存在，也不复核上游测试是否真的运行过。",
        "记录 figures 有 4 条声明但无字节、无正文锚点；本工序只登记缺口，不判定图件是否曾产出。",
        "报告自报的数值（A12/A13/A18）一律按原文登记，未做二次计算或外部法规回读。"
      ],
      "schema_check": {
        "schema_file": "schemas/asset_manifest.v1.wp-11624-01.schema.json",
        "passed": true,
        "error": null
      },
      "artifact_path": "knowledge/kf/wp-11624-01/asset_manifest.json",
      "artifact_sha256": "3c4ab994158ebe61243556e9e5e8eb21f59e26f7ae28efa4203f6aced0b211cf",
      "artifact_bytes": 40188
    }
  },
  "claims": []
}
```
