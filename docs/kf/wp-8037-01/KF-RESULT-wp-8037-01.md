# KF-RESULT wp-8037-01

- package_id: `wp-8037-01` · task_type: `01-asset-registration` · lane: `C`
- report_id: `8037` · source: `tensor://reports/8037` (field `markdown`)
- source sha256: `sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0` — contract `sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0` → **match: True**
- chars 1223 / bytes 1252 / lines 30 · title: DEM Contact Mechanics Dual Verification (P27W3-N06)
- status: **draft**（verification 由平台门计算；本包不标 verified）
- tags: `kf-wp:wp-8037-01` · repro_cmd: `python3 scripts/kf_wp8037_01_register.py all`（等价分步：
  `build` → `envelope` → `verify` → `figure` → `report`；`verify` 会回活报告重算 6 项验收）

## ① 本工序做了什么

01-asset-registration（登记，不抽取）：核对 report 8037 的 markdown 字节哈希与契约一致，然后把报告内
**22 个可定位资产**逐一登记并给出可复算定位器（字符区间 + 行区间 + 逐字引文 + 唯一性）：

| 分辨率 | 数量 | 含义 |
|---|---|---|
| `resolved_in_source` | 17 | 引文在本报告 markdown 内逐字可定位 |
| `referenced_unresolved` | 4 | 报告声明的外部工件（源码/测试/报告/verdict JSON）未随报告附上 |
| `declared_absent` | 1 | 报告声明存在但载荷内确实缺失（图集 figures=[]） |

`claims` 为空数组并写明理由：契约 `objective.register_assets=true`、`classify_report_type=false`、
`constraints.no_forced_claim_generation=true`；抽取是后续独立工作包。9 条判据行与 6 条 findings
已登记为可定位资产，供下游直接引用，不必重读原文。

**未做**：不做分类、不做知识抽取、不判证据等级、不标 verified、不复算任何数值、不重跑任何仿真/测试。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `GET $TENSOR_API_BASE/tensor/reports/8037`（Bearer 登录令牌，环境变量注入）取 `markdown` 字段，
   按 UTF-8 原字节落盘（不做换行/空白修补），本地重算 sha256；
2. 身份四项对表：哈希 / 字符数 / title / scenario_key 全部与契约一致（见 `runs/wp-8037-01/fetch_meta.json`）；
3. 建立**锚点表**：每个资产用「文档内唯一子串」做锚，锚出现次数 ≠1 直接 `SystemExit`
   （模糊锚会静默位移定位器，这是本工序最该防的失效模式）；行区间由锚行 + 相对偏移得到，
   再反算字符区间，并当场断言 `md[start:end] == quote`；
4. 外部工件用 `Path.glob` 在工作树内做**机械探测**，不存在就记 `referenced_unresolved` 并附探测记录，
   绝不编造地址；`figures` 以平台 record 的 `figures[]` 长度 + 工作树 glob 双证据判 `declared_absent`；
5. 产物：`asset_manifest.json` → 包一层 `kf_result.v1` 信封 → `verify` 子命令**回到活报告**重算 6 项验收
   （不信任 manifest 自述）→ matplotlib 出定位图 → 渲染本报告。

关键设置：JSON 全部 `ensure_ascii=False`（保留 `n₁`/`R²` 等 unicode 原字节）；行号在内部 0-based、
定位器对外 1-based，并在 manifest 的 `source.line_counting` 里写明口径。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-8037-01/asset_manifest.json` | 主产物：22 资产 + source 身份块 + counts + integrity + observations/limitations |
| `docs/kf/wp-8037-01/kf_result.json` | `kf_result.v1` 信封（`outputs["asset_manifest.json"]` 内嵌上文，`provenance.source_hash`=活哈希） |
| `docs/kf/wp-8037-01/verification.json` | 6 项验收逐项结果 + `not_verified` 清单（gate=PASS） |
| `docs/kf/wp-8037-01/figures/asset_locator_map.png` | 资产定位图：横轴=源行号，颜色=分辨率；下panel=分辨率计数+哈希身份 |
| `docs/kf/wp-8037-01/KF-RESULT-wp-8037-01.md` | 本报告（正文末唯一一个 json fenced 结果块） |
| `artifacts/wp-8037-01/asset_manifest.json`, `kf_result.json` | 字节同源镜像（推送门会丢弃 artifacts/，故正本在 docs/） |
| `scripts/kf_wp8037_01_register.py` | 一键复跑（build/envelope/verify/figure/report） |

## ④ 证据定位表（资产 → 原文逐字片段）

| asset_id | class | 行（1-based） | 原文引文（首行，逐字） |
|---|---|---|---|
| A01 | `document` | 1 | `# DEM Contact Mechanics Dual Verification (P27W3-N06)` |
| A02 | `heading` | 3 | `## Results` |
| A03 | `criteria_table` | 4 | `\| Criterion \| Key Metric \| Error \| Pass \|` |
| A04 | `criterion_result` | 6 | `\| C1 \| Tangential force deviation \| 0% (exact) \| ✅ \|` |
| A05 | `criterion_result` | 7 | `\| C2 \| Rolling torque \| <1e-10% \| ✅ \|` |
| A06 | `criterion_result` | 8 | `\| C3 \| Damping fit R² \| >0.999 \| ✅ \|` |
| A07 | `criterion_result` | 9 | `\| C4 \| Sphere R_eff \| 0% (exact) \| ✅ \|` |
| A08 | `criterion_result` | 10 | `\| C5 \| Surface error monotone \| Yes \| ✅ \|` |
| A09 | `criterion_result` | 11 | `\| C6 \| Dissipation finite \| Yes \| ✅ \|` |
| A10 | `criterion_result` | 12 | `\| C7 \| Repose monotone \| Yes \| ✅ \|` |
| A11 | `criterion_result` | 13 | `\| C8 \| Verdict JSON \| Generated \| ✅ \|` |
| A12 | `criterion_result` | 14 | `\| C9 \| Tests passing \| 32/32 \| ✅ \|` |
| A13 | `heading` | 16 | `## Key Findings` |
| A14 | `finding_set` | 16 | `## Key Findings` |
| A15 | `numeric_anchor` | 22 | `- Shape verdict: clump acceptable for n₁ ≤ 4 with N ≥ 32 spheres` |
| A16 | `heading` | 24 | `## Files` |
| A17 | `file_reference` | 25 | `- Module: src/tensordem/dem_contact_verification.py` |
| A18 | `file_reference` | 26 | `- Tests: tests/test_dem_contact_mechanics_verification.py (32 tests)` |
| A19 | `file_reference` | 27 | `- Full report: docs/dem_contact_mechanics_verification_report.md` |
| A20 | `file_reference` | 28 | `- Verdict: artifacts/dem/shape_representation_verdict.json` |
| A21 | `figure_declaration` | 29 | `- Figures: artifacts/dem/figures/c1_*.png through c5_*.png` |
| A22 | `platform_record` | 1 | `# DEM Contact Mechanics Dual Verification (P27W3-N06)` |

完整清单（含多行资产全文、唯一性、外部探测）见 `asset_manifest.json.assets[]`。图：见 `docs/kf/wp-8037-01/figures/asset_locator_map.png`（图未内嵌于 markdown，由平台 figures 通道单独上传）。

## ⑤ 注意点与局限

1. **本报告只说结论，不说证据**：正文 30 行、1223 字符，无几何、无参数表、无方法节、无逐判据误差序列。
   下游 03 抽取能提的东西天生很薄——这是**源的性质**，不是本包的省略。
2. **`Pass` 列是生产方自述**：9 行 ✅ 全部登记为"数据"，本包不复核（未重跑）。
   把自述当验证是产线最危险的误读，故 manifest 里 `verification_status=not_verified`。
3. **`Error` 列语义混杂**：C1/C2/C4 是误差量级、C3 是拟合统计量 `R²`、C5–C7 是布尔 `Yes`。
   若下游把该列当同质误差序列会用错统计方法。
4. **`0% (exact)` 出现两次**（C1 切向力、C4 球 R_eff）：子串级去重会把两个不同结论并成一个，
   故一律用整行定位。
5. **图形证据缺失**：Files 声明 `c1_*.png through c5_*.png`，但 record `figures=[]`、工作树无 PNG
   → 判 `declared_absent`；C8 声称 verdict JSON "Generated" 但同样未附内容 → 判 `referenced_unresolved`。
6. **外部工件只在本地工作树探测过**（TensorKnowledge）：这里找不到**不等于** TensorDEM 里没有。
7. **本包没有数值精度结论**：不涉及与基准的误差比较，"是否 <3%" 对本工序无定义（见 §⑥ 说明）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 说明 |
|---|---|---|
| valid_json | ✅ | asset_manifest.json and kf_result.json both parse as JSON |
| schema_pass | ✅ | asset_manifest.json valid against asset_manifest.wp-8037-01.schema.json; kf_result.json valid against canonical kf_result.v1.schema.json |
| source_locator_resolvable | ✅ | 22/22 locators re-resolved verbatim (char span + substring + uniqueness + line span) |
| source_hash_matches | ✅ | live=sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0 contract=sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0 manifest=sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0 |
| no_duplicate_ids | ✅ | 22 asset ids, 0 claim ids, duplicates assets=[] claims=[], A\d{2} pattern ok |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[] with an explicit claims_empty_reason (no_forced_claim_generation) - vacuously satisfied and declared, not silently omitted |
| scope_single_report_id | ✅ | no foreign report_id in the manifest |

- **误差判定（必答项）**：本工序为资产登记，**不产生任何物理量或误差数字**，因此不存在"关键量 vs 基准误差是否 <3%"
  的对象；此处不做数值精度声明，也不拿报告自述的 0% / <1e-10% 充当本包结论（它们是源文本的引文，不是本包的测量）。
  需要精度判定的是下游抽取+验证包。
- **honest 声明**：未完成/未做的部分是「数值复算、测试重跑、外部工件内容核验」——三项均如实登记为 `not_verified`，
  未粉饰为通过。若平台门判 `schema_pass` 失败，原因是本地 schema 实例与平台侧 schema 口径差异，
  正本以平台门为准（已在 `schema_source` 写明）。

```json
{
  "package_id": "wp-8037-01",
  "task_type": "01-asset-registration",
  "report_id": "8037",
  "provenance": {
    "source_hash": "sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0",
    "source_field": "markdown",
    "source_uri": "tensor://reports/8037",
    "producer": "kf-worker/m15606",
    "emitted_at": "2026-11-12T01:33:38.691950+00:00",
    "contract_source_hash": "sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0",
    "source_chars": 1223,
    "source_bytes_utf8": 1252,
    "source_title": "DEM Contact Mechanics Dual Verification (P27W3-N06)",
    "scenario_key": "dem_contact_mechanics_verification",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-8037-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/8037",
    "local_copy": "runs/wp-8037-01/source_8037.md",
    "generator": "scripts/kf_wp8037_01_register.py",
    "verifier": "scripts/kf_wp8037_01_register.py verify",
    "verification_status": "not_verified",
    "manifest_path": "docs/kf/wp-8037-01/asset_manifest.json",
    "manifest_sha256": "sha256:38a94d89feda8fdc15e4c3fd1dcf369444ecc9baef6a5c283a3b1fa35660c913",
    "manifest_bytes": 21294
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "schema_source": "schemas/asset_manifest.wp-8037-01.schema.json (package-local instance of asset_manifest.v1; the repo-wide schemas/asset_manifest.v1.schema.json pins report 448 and is left untouched)",
      "package_id": "wp-8037-01",
      "task_type": "01-asset-registration",
      "report_id": "8037",
      "lane": "C",
      "generated_at": "2026-11-12T01:33:38.688049+00:00",
      "producer": "kf-worker/m15606",
      "source": {
        "uri": "tensor://reports/8037",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0",
        "hash_hex": "1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0",
        "contract_hash": "1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0",
        "hash_matches_contract": true,
        "chars": 1223,
        "bytes_utf8": 1252,
        "lines": 30,
        "has_crlf": false,
        "trailing_newline": true,
        "title": "DEM Contact Mechanics Dual Verification (P27W3-N06)",
        "scenario_key": "dem_contact_mechanics_verification",
        "contract_chars": 1223,
        "contract_title": "DEM Contact Mechanics Dual Verification (P27W3-N06)",
        "contract_scenario_key": "dem_contact_mechanics_verification",
        "chars_matches_contract": true,
        "title_matches_contract": true,
        "scenario_key_matches_contract": true,
        "platform_id": 8037,
        "platform_mission_id": 6732,
        "platform_status": "published",
        "platform_tags": [
          "DEM",
          "contact-mechanics",
          "verification"
        ],
        "platform_figures": [],
        "platform_figure_count": 0,
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/8037",
        "local_copy": "runs/wp-8037-01/source_8037.md",
        "committed_copy": "docs/kf/wp-8037-01/source_8037.md",
        "hash_scope": "UTF-8 bytes of the markdown field as served by GET /api/v1/tensor/reports/8037",
        "line_counting": "logical lines = markdown.split(chr(10)); 0-based internally, 1-based in locators"
      },
      "counts": {
        "assets": 22,
        "by_class": {
          "document": 1,
          "heading": 3,
          "criteria_table": 1,
          "criterion_result": 9,
          "finding_set": 1,
          "numeric_anchor": 1,
          "file_reference": 4,
          "figure_declaration": 1,
          "platform_record": 1
        },
        "by_resolution": {
          "resolved_in_source": 17,
          "referenced_unresolved": 4,
          "declared_absent": 1
        },
        "resolved_in_source": 17,
        "referenced_unresolved": 4,
        "declared_absent": 1,
        "unique_quotes": 22
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "report markdown (full body)",
          "in_report_section": "(document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 1223,
            "start_line": 1,
            "end_line": 30,
            "quote": "# DEM Contact Mechanics Dual Verification (P27W3-N06)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256 of the markdown field recomputed locally equals the contract hash",
            "result": "resolved"
          },
          "note": "Whole markdown is the primary asset; see source.hash / source.bytes_utf8."
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "section heading 'Results'",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 55,
            "end_char": 65,
            "start_line": 3,
            "end_line": 3,
            "quote": "## Results",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading line found verbatim",
            "result": "resolved"
          },
          "note": "Opens the acceptance-criteria table section."
        },
        {
          "asset_id": "A03",
          "asset_class": "criteria_table",
          "label": "acceptance criteria table C1-C9 (header + 9 rows)",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 66,
            "end_char": 503,
            "start_line": 4,
            "end_line": 14,
            "quote": "| Criterion | Key Metric | Error | Pass |\n|-----------|-----------|-------|------|\n| C1 | Tangential force deviation | 0% (exact) | ✅ |\n| C2 | Rolling torque | <1e-10% | ✅ |\n| C3 | Damping fit R² | >0.999 | ✅ |\n| C4 | Sphere R_eff | 0% (exact) | ✅ |\n| C5 | Surface error monotone | Yes | ✅ |\n| C6 | Dissipation finite | Yes | ✅ |\n| C7 | Repose monotone | Yes | ✅ |\n| C8 | Verdict JSON | Generated | ✅ |\n| C9 | Tests passing | 32/32 | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table header + separator + 9 criterion rows found verbatim",
            "result": "resolved"
          },
          "note": "The verdict column is the report author's self-declaration; registered as data, not re-verified here."
        },
        {
          "asset_id": "A04",
          "asset_class": "criterion_result",
          "label": "criterion C1 row",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 149,
            "end_char": 201,
            "start_line": 6,
            "end_line": 6,
            "quote": "| C1 | Tangential force deviation | 0% (exact) | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "row found verbatim",
            "result": "resolved"
          },
          "note": "Numeric string '0% (exact)' is not unique in the document - the row is the unique locator."
        },
        {
          "asset_id": "A05",
          "asset_class": "criterion_result",
          "label": "criterion C2 row",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 202,
            "end_char": 239,
            "start_line": 7,
            "end_line": 7,
            "quote": "| C2 | Rolling torque | <1e-10% | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "row found verbatim",
            "result": "resolved"
          },
          "note": "Bound expressed as a strict inequality ('<1e-10%')."
        },
        {
          "asset_id": "A06",
          "asset_class": "criterion_result",
          "label": "criterion C3 row",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 240,
            "end_char": 276,
            "start_line": 8,
            "end_line": 8,
            "quote": "| C3 | Damping fit R² | >0.999 | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "row found verbatim",
            "result": "resolved"
          },
          "note": "Column labelled 'Error' carries a fit statistic (R^2), not an error - mixed column semantics."
        },
        {
          "asset_id": "A07",
          "asset_class": "criterion_result",
          "label": "criterion C4 row",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 277,
            "end_char": 315,
            "start_line": 9,
            "end_line": 9,
            "quote": "| C4 | Sphere R_eff | 0% (exact) | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "row found verbatim",
            "result": "resolved"
          },
          "note": "Same numeric string '0% (exact)' as C1; only the row context disambiguates."
        },
        {
          "asset_id": "A08",
          "asset_class": "criterion_result",
          "label": "criterion C5 row",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 316,
            "end_char": 357,
            "start_line": 10,
            "end_line": 10,
            "quote": "| C5 | Surface error monotone | Yes | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "row found verbatim",
            "result": "resolved"
          },
          "note": "Boolean metric ('Yes'); no numeric value is given."
        },
        {
          "asset_id": "A09",
          "asset_class": "criterion_result",
          "label": "criterion C6 row",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 358,
            "end_char": 395,
            "start_line": 11,
            "end_line": 11,
            "quote": "| C6 | Dissipation finite | Yes | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "row found verbatim",
            "result": "resolved"
          },
          "note": "Boolean metric ('Yes'); no numeric value is given."
        },
        {
          "asset_id": "A10",
          "asset_class": "criterion_result",
          "label": "criterion C7 row",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 396,
            "end_char": 430,
            "start_line": 12,
            "end_line": 12,
            "quote": "| C7 | Repose monotone | Yes | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "row found verbatim",
            "result": "resolved"
          },
          "note": "Boolean metric ('Yes'); no numeric value is given."
        },
        {
          "asset_id": "A11",
          "asset_class": "criterion_result",
          "label": "criterion C8 row",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 431,
            "end_char": 468,
            "start_line": 13,
            "end_line": 13,
            "quote": "| C8 | Verdict JSON | Generated | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "row found verbatim",
            "result": "resolved"
          },
          "note": "States the verdict JSON is 'Generated' but the artefact itself is not attached to the report."
        },
        {
          "asset_id": "A12",
          "asset_class": "criterion_result",
          "label": "criterion C9 row",
          "in_report_section": "Results",
          "locator": {
            "method": "char_span",
            "start_char": 469,
            "end_char": 503,
            "start_line": 14,
            "end_line": 14,
            "quote": "| C9 | Tests passing | 32/32 | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "row found verbatim",
            "result": "resolved"
          },
          "note": "'32/32' is the only unit-bearing count in the table; no run id or commit accompanies it."
        },
        {
          "asset_id": "A13",
          "asset_class": "heading",
          "label": "section heading 'Key Findings'",
          "in_report_section": "Key Findings",
          "locator": {
            "method": "char_span",
            "start_char": 505,
            "end_char": 520,
            "start_line": 16,
            "end_line": 16,
            "quote": "## Key Findings",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading line found verbatim",
            "result": "resolved"
          },
          "note": "Opens the prose finding list."
        },
        {
          "asset_id": "A14",
          "asset_class": "finding_set",
          "label": "key findings list (6 bullets)",
          "in_report_section": "Key Findings",
          "locator": {
            "method": "char_span",
            "start_char": 505,
            "end_char": 908,
            "start_line": 16,
            "end_line": 22,
            "quote": "## Key Findings\n- Cundall-Strack tangential spring is exact (machine precision)\n- EPSD rolling spring converges to analytic limit M_r = μ_r·F_n·R_eff\n- Rotational damping follows exponential decay with R² > 0.999\n- Hertz contact for sphere-plane is exact at the sphere limit\n- Clump surface error decreases monotonically with sphere count\n- Shape verdict: clump acceptable for n₁ ≤ 4 with N ≥ 32 spheres",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "6 bullet lines found verbatim",
            "result": "resolved"
          },
          "note": "Each bullet is a candidate knowledge statement for a later extraction package; not extracted here."
        },
        {
          "asset_id": "A15",
          "asset_class": "numeric_anchor",
          "label": "shape-representation verdict criterion (n1 <= 4, N >= 32)",
          "in_report_section": "Key Findings",
          "locator": {
            "method": "char_span",
            "start_char": 844,
            "end_char": 908,
            "start_line": 22,
            "end_line": 22,
            "quote": "- Shape verdict: clump acceptable for n₁ ≤ 4 with N ≥ 32 spheres",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "line found verbatim",
            "result": "resolved"
          },
          "note": "Only quantitative shape recommendation in the report; unicode subscripts preserved as bytes."
        },
        {
          "asset_id": "A16",
          "asset_class": "heading",
          "label": "section heading 'Files'",
          "in_report_section": "Files",
          "locator": {
            "method": "char_span",
            "start_char": 910,
            "end_char": 918,
            "start_line": 24,
            "end_line": 24,
            "quote": "## Files",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading line found verbatim",
            "result": "resolved"
          },
          "note": "Declares 5 external artefacts."
        },
        {
          "asset_id": "A17",
          "asset_class": "file_reference",
          "label": "declared module path",
          "in_report_section": "Files",
          "locator": {
            "method": "char_span",
            "start_char": 919,
            "end_char": 970,
            "start_line": 25,
            "end_line": 25,
            "quote": "- Module: src/tensordem/dem_contact_verification.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path probed in this worktree (TensorKnowledge checkout)",
            "result": "unresolved",
            "probe": {
              "probe": "Path.glob('src/tensordem/dem_contact_verification.py') under m15606",
              "hits": [],
              "exists": false
            }
          },
          "note": "Declared path belongs to the TensorDEM repository, not to this worktree; no attachment on the record."
        },
        {
          "asset_id": "A18",
          "asset_class": "file_reference",
          "label": "declared test module path",
          "in_report_section": "Files",
          "locator": {
            "method": "char_span",
            "start_char": 971,
            "end_char": 1039,
            "start_line": 26,
            "end_line": 26,
            "quote": "- Tests: tests/test_dem_contact_mechanics_verification.py (32 tests)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path probed in this worktree (TensorKnowledge checkout)",
            "result": "unresolved",
            "probe": {
              "probe": "Path.glob('tests/test_dem_contact_mechanics_verification.py') under m15606",
              "hits": [],
              "exists": false
            }
          },
          "note": "Declared path belongs to the TensorDEM repository; no test-run identity (run id / commit) is given."
        },
        {
          "asset_id": "A19",
          "asset_class": "file_reference",
          "label": "declared full-report path",
          "in_report_section": "Files",
          "locator": {
            "method": "char_span",
            "start_char": 1040,
            "end_char": 1104,
            "start_line": 27,
            "end_line": 27,
            "quote": "- Full report: docs/dem_contact_mechanics_verification_report.md",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path probed in this worktree (TensorKnowledge checkout)",
            "result": "unresolved",
            "probe": {
              "probe": "Path.glob('docs/dem_contact_mechanics_verification_report.md') under m15606",
              "hits": [],
              "exists": false
            }
          },
          "note": "Declared full report is cited as the source of the numbers; it is not attached."
        },
        {
          "asset_id": "A20",
          "asset_class": "file_reference",
          "label": "declared verdict JSON path",
          "in_report_section": "Files",
          "locator": {
            "method": "char_span",
            "start_char": 1105,
            "end_char": 1163,
            "start_line": 28,
            "end_line": 28,
            "quote": "- Verdict: artifacts/dem/shape_representation_verdict.json",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path probed in this worktree (TensorKnowledge checkout)",
            "result": "unresolved",
            "probe": {
              "probe": "Path.glob('artifacts/dem/shape_representation_verdict.json') under m15606",
              "hits": [],
              "exists": false
            }
          },
          "note": "Its content is asserted by criterion C8 but never quoted; unverifiable from this report alone."
        },
        {
          "asset_id": "A21",
          "asset_class": "figure_declaration",
          "label": "declared figure set c1_*.png .. c5_*.png",
          "in_report_section": "Files",
          "locator": {
            "method": "char_span",
            "start_char": 1164,
            "end_char": 1222,
            "start_line": 29,
            "end_line": 29,
            "quote": "- Figures: artifacts/dem/figures/c1_*.png through c5_*.png",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "platform record figures[] length + worktree glob probe",
            "result": "absent",
            "probe": {
              "probe": "Path.glob('artifacts/dem/figures/*.png') under m15606",
              "hits": [],
              "exists": false
            }
          },
          "note": "Figures are declared as a glob range but the payload carries none (figures=[]); no PNG bytes in scope."
        },
        {
          "asset_id": "A22",
          "asset_class": "platform_record",
          "label": "platform record metadata (title/scenario_key/tags/figures)",
          "in_report_section": "(document header)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 53,
            "start_line": 1,
            "end_line": 1,
            "quote": "# DEM Contact Mechanics Dual Verification (P27W3-N06)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "record fields read from the API response for report 8037",
            "result": "present"
          },
          "note": "Record-level metadata; not part of the markdown body, so its locator is the title line."
        }
      ],
      "claims": [],
      "claims_empty_reason": "Contract for wp-8037-01 sets objective.register_assets=true and objective.classify_report_type=false; extraction is a separate package. constraints.no_forced_claim_generation=true, so no knowledge statement is emitted. The 9 criterion rows and the 6 finding bullets are registered as locatable assets so that a later extraction package can cite them without re-reading the report.",
      "integrity": {
        "quote_uniqueness": {
          "checked": 22,
          "unique": 22,
          "all_unique": true
        },
        "hash_recomputed_locally": "sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0",
        "hash_matches_contract": true,
        "chars_matches_contract": true,
        "asset_id_unique": true,
        "char_spans_reproduce_quotes": true,
        "verification_status": "not_verified"
      },
      "observations": [
        "The report is a 30-line result summary: no geometry, no parameter table, no method section and no per-criterion numeric error series. Downstream extraction is thin by construction, and that is a property of the source, not of this package.",
        "The 'Pass' column is a self-declaration of the producing mission; this package registers the strings and does not confirm them (verification is the platform gate's job).",
        "The column labelled 'Error' mixes three kinds of value: error magnitudes (C1, C2, C4), a fit statistic (C3, R^2) and booleans (C5-C7, 'Yes'). Treating the column uniformly would be a modelling error.",
        "'0% (exact)' occurs twice (C1 tangential force, C4 sphere R_eff) with different meanings; substring-level dedup would merge two distinct results, hence row-level locators.",
        "C9 '32/32' and the files line '(32 tests)' agree, but neither carries a run id or commit: the count is internally consistent and externally unverifiable from this report.",
        "No figure bytes are attached (record figures=[]), while the Files section declares c1_*.png through c5_*.png: the graphical evidence is absent from the source of record."
      ],
      "limitations": [
        "Only report_id=8037 was read; no other report was touched.",
        "External artefact paths (A17-A20) are declared inside the TensorDEM repository and were probed only within this TensorKnowledge worktree: absence here is not evidence of absence there.",
        "Registration is not verification: no claim in this manifest is marked verified and the manifest carries no knowledge-object or evidence-grade judgement."
      ]
    }
  },
  "claims": []
}
```
