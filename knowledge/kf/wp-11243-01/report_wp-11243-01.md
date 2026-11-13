## ① 本工序做了什么

对 report_id=**11243**（DEM Coarse-Graining Scaling Law & Fine-Coarse Cross-Validation）做**资产登记**（task_type `01-asset-registration`，lane C）：
确认报告 markdown 的字节哈希与契约 `source_hash` 一致，并把该报告所携带的附件/工件逐件登记进
`asset_manifest.json`——**只登记，不抽取**（objective.register_assets=true、
classify_report_type=false），claims 按契约保持空数组，任何结论都未标 verified。

登记结果：**15** 件资产 = {'source_document': 1, 'figure_attachment': 5, 'specification_block': 5, 'data_table': 2, 'test_suite_evidence': 1, 'quantitative_result_statement': 1}；其中 {'resolved_in_source': 13, 'referenced_unresolved': 2}。
源文档 sha256 = `d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598`，字符数 2701、UTF-8 字节数 2828，
与契约 `sha256:d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598` / chars=2701 **逐项相符**。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：只走平台 API `GET /tensor/reports/11243`（Bearer token 由
   `$TENSOR_AGENT_USER/$TENSOR_AGENT_PASS` 登录换取）。本机 `psql` 对该表无权限
   （`permission denied for table tensor_reports`），因此 API 是唯一信道；脚本内
   `assert str(record["id"]) == "11243"` 守住「只碰这一份报告」的边界。
2. **冻源**：markdown 原样落盘 `knowledge/kf/wp-11243-01/source_report_11243.md`（2828 字节），
   作为后续一切引文的只读快照。
3. **零手抄定位**：脚本不写任何一句引文——所有 `quote` 都由**字符偏移切片**从 markdown
   字符串里取出（section 由标题唯一匹配 → 到下一个标题前截断；record 字段由 needle
   命中后按句边界切片）。因此「引文逐字来自原文」是**机制**而非承诺。
4. **附件字节核验**：对 record 声明的 5 个图逐个 `GET /tensor/reports/11243/figures/<name>`，
   记录 HTTP 状态、字节数、PNG 宽高与 sha256，并把字节落到 `figures/`。注意：`/figures`
   列表端点返回 404，但**按名取字节的端点是 200**，故 5 张图全部登记为
   `resolved_in_source`（带字节），而非过往包常见的「有名字无载荷」。
5. **定位复核**：建完之后独立回验一遍——`markdown[start_char:end_char] == quote`、
   `quote in markdown`、行号一致（0 基）、以及引文在源中的出现次数必须为 1；
   复核失败则脚本 `exit 1`。
6. **结构门**：result 信封按 `schemas/kf_result.v1.schema.json`、manifest 按
   `schemas/asset_manifest.v1.wp-11243-01.schema.json` 用 `jsonschema` 校验（见 ③ validation.json）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `knowledge/kf/wp-11243-01/asset_manifest.json` | 主产物：15 件资产、15 条定位、claims=[]、integrity 全绿 |
| `knowledge/kf/wp-11243-01/source_report_11243.md` | 源快照（2828 字节，sha256 `d278a86d919c8f90…`） |
| `knowledge/kf/wp-11243-01/figures/fig1..fig5*.png` | 5 个附件字节本体（共 460012 字节），逐个带 sha256 |
| `knowledge/kf/wp-11243-01/result.json` | kf_result.v1 信封（outputs.asset_manifest.json 内嵌全量 manifest） |
| `knowledge/kf/wp-11243-01/validation.json` | 两道 schema 门 + 6 条 acceptance 的机读判定 |
| `knowledge/kf/wp-11243-01/selfcheck.json` | 登记脚本的 integrity/checks 段 |
| `knowledge/kf/wp-11243-01/publish_verification.json` | 发布后回读校验（json 块唯一性、回读哈希、图字节可取） |
| `scripts/kf_wp_11243_01_register.py` / `_deliver.py` | 一键复跑（下方 repro_cmd） |
| `tests/test_kf_wp_11243_01.py` | 10 条离线不变量断言（哈希/引文逐字且唯一/表结构与块内容一致/id 唯一/schema） |
| `schemas/asset_manifest.v1.wp-11243-01.schema.json` | 本包 manifest 的结构 schema（schema_pass 的可复现依据） |

平台侧 5 个附件（登记元数据，非本包生成）：

| 附件名 | HTTP | 字节 | sha256 | 尺寸 |
|---|---|---|---|---|
| fig1_scaling_laws | 200 | 131699 | f60910faf8f7570912485036dde4c89f766275a19cf62dbe991bf24acc6d1d43 | 2233×579 |
| fig2_cross_validation | 200 | 100966 | 951d1d9fb40981bc96413395639e8e43c8108d9edaf7c11012801f79e64d91e0 | 2234×579 |
| fig3_macro_error_budget | 200 | 106086 | d9ec56b4abf6758df63d91c068809477c51f7349a7b544d8b1e6a2a26d0e1c53 | 2234×579 |
| fig4_stability_gate | 200 | 56766 | 2466bbb8a89e484edf2862ce909961806a22ab975273b70cd96762b67a1f5773 | 1184×729 |
| fig5_pareto_front | 200 | 64495 | 072a5eeb62e23091c67eab89d20c11f59d73bcb91317b5948e98b0c27e53d0bb | 1177×731 |

## ④ 证据定位表（artifact / claim 字段 → 原文引文片段）

源 = `tensor://reports/11243#markdown`（sha256 `d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598`）。行号为 0 基；`pointer` 形式指向 record 字段。

| id | 类别 | 解析状态 | 定位 | 原文片段（逐字，脚本切片） |
|---|---|---|---|---|
| A01 | source_document | resolved_in_source | whole field | `# DEM Coarse-Graining Scaling Rule Table` |
| A02 | figure_attachment | resolved_in_source | /figures/0/name | `fig1_scaling_laws` |
| A03 | figure_attachment | resolved_in_source | /figures/1/name | `fig2_cross_validation` |
| A04 | figure_attachment | resolved_in_source | /figures/2/name | `fig3_macro_error_budget` |
| A05 | figure_attachment | resolved_in_source | /figures/3/name | `fig4_stability_gate` |
| A06 | figure_attachment | resolved_in_source | /figures/4/name | `fig5_pareto_front` |
| A07 | specification_block | resolved_in_source | L8–L13 (char 255–475) | `### 口径 A: Contact-Time Invariance (k_n ∝ f³) ⏎ - Derived from t_c = π·√(m_eff/k_n) = invariant …` |
| A08 | specification_block | resolved_in_source | L14–L19 (char 476–693) | `### 口径 B: Sound-Speed Invariance (k_n ∝ f) ⏎ - Derived from c = √(k_n/m_eff)·L_char = invariant…` |
| A09 | data_table | resolved_in_source | L20–L37 (char 694–1263) | `## Scaling Rule Table ⏎  ⏎ \| Quantity \| 口径 A (Contact-Time) \| 口径 B (Sound-Speed) \| ⏎ \|----…` |
| A10 | specification_block | resolved_in_source | L38–L49 (char 1264–1760) | `## Applicability Domains ⏎  ⏎ ### A_contact_time_invariant ⏎ - **Best for**: Contact dynamics, …` |
| A11 | data_table | resolved_in_source | L50–L58 (char 1761–2124) | `## Failure Boundaries ⏎  ⏎ \| Factor f \| 口径 A Valid? \| 口径 B Valid? \| Notes \| ⏎ \|----------…` |
| A12 | specification_block | resolved_in_source | L59–L63 (char 2125–2312) | `## Negative Controls ⏎  ⏎ 1. **Mass-only scaling** (m → f³m, k_n unchanged): breaks contact tim…` |
| A13 | specification_block | resolved_in_source | L64–L72 (char 2313–2701) | `## Recommendations ⏎  ⏎ - Use **口径 A** when contact dynamics, force-displacement curves, and re…` |
| U01 | test_suite_evidence | referenced_unresolved | /summary | `56 pytest items pass including negative controls.` |
| U02 | quantitative_result_statement | referenced_unresolved | /summary | `All macro-invariance criteria met: shear friction angle deviation 0%, repose angle deviation 0°…` |

## ⑤ 注意点与局限

- **不抽取**：本包只登记「有什么」，不判断「内容对不对」。`Scaling Rule Table` 只登记
  表结构与行数（{"pipe_rows_total": 15, "columns": ["Quantity", "口径 A (Contact-Time)", "口径 B (Sound-Speed)"], "data_rows": 13, "column_count": 3}），
  不把 f³/f 这类标度关系升格为 claim。
- **两处只能到 referenced_unresolved**：摘要里的
  `56 pytest items pass including negative controls.` 与
  `All macro-invariance criteria met: shear friction angle deviation 0%,…`
  在 markdown 正文中**不存在对应数字/路径**：正文 `pytest` 出现
  0 次、
  `0%` 出现 0 次、
  `56` 出现 0 次
  （`deviation` 只作为定性用语 `deviations` 出现
  2 次，不带任何测量值）。
  这两条属平台 record.summary，登记为未解析，**不得**当作已验证证据使用。
- **正文不引图**：markdown 正文没有任何 figure/路径引用，5 张图仅由 record 声明；
  图与正文段落的对应关系不做断言（caption 由 record 字段逐字复制）。
- **未做的验证**：未运行 TensorDEM 的 pytest 套件、未复核任何标度关系的数值正确性、
  未比对图 3 的误差预算——这些都超出本工序契约（review.required=false）。
- **版本关系**：平台 `/tensor/reports` 只有 POST（PATCH/PUT/DELETE 均 405），故同包早前的
  中间版本以追加方式留档；本报告为**最终版**（含离线测试证据），其 `asset_manifest.json`
  与 worktree 中 `knowledge/kf/wp-11243-01/asset_manifest.json` 逐字节一致。
- 边界合规：全程只读 report_id=11243，未写回该报告，未触碰任何其它 report_id，
  未改写上游产物，未把任何条目标为 verified。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✓ | `json.loads` 往返成功，result.json 可解析 |
| schema_pass | ✓ | kf_result.v1=pass；asset_manifest.v1.wp-11243-01=pass |
| source_locator_resolvable | ✓ | 15/15 条定位回验通过（切片相等 + 子串 + 行号一致 + 唯一） |
| source_hash_matches | ✓ | 本地重算 `d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598` = 契约值 |
| no_duplicate_ids | ✓ | 15 个 id 无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims=[] 空数组（契约允许），空集真值为真；未造 claim 填空 |

补充机检（离线不变量测试，`pytest -q tests/test_kf_wp_11243_01.py`，exit=0）：`10 passed, 1 warning in 0.15s`。

失败项：无。

repro_cmd：

```bash
cd <worktree> && python3 scripts/kf_wp_11243_01_register.py && python3 scripts/kf_wp_11243_01_deliver.py
```

## 结果信封（唯一 json 块）

```json
{
  "package_id": "wp-11243-01",
  "task_type": "01-asset-registration",
  "report_id": "11243",
  "provenance": {
    "source_hash": "sha256:d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598",
    "source_field": "markdown",
    "producer": "scripts/kf_wp_11243_01_register.py",
    "emitted_at": "2026-11-12T01:52:17+00:00",
    "notes": "read-only on report_id=11243; assets registered, nothing extracted, no claim marked verified; every quote sliced by character offset from the source markdown / record summary"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-11243-01",
      "task_type": "01-asset-registration",
      "report_id": "11243",
      "lane": "C",
      "source": {
        "uri": "tensor://reports/11243",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598",
        "chars": 2701,
        "bytes_utf8": 2828,
        "title": "DEM Coarse-Graining Scaling Law & Fine-Coarse Cross-Validation",
        "scenario_key": "tensordem-cg-upscaling",
        "report_status": "published",
        "platform_figures": [
          {
            "name": "fig1_scaling_laws",
            "http_status": 200,
            "bytes": 131699,
            "sha256": "f60910faf8f7570912485036dde4c89f766275a19cf62dbe991bf24acc6d1d43",
            "png_width": 2233,
            "png_height": 579
          },
          {
            "name": "fig2_cross_validation",
            "http_status": 200,
            "bytes": 100966,
            "sha256": "951d1d9fb40981bc96413395639e8e43c8108d9edaf7c11012801f79e64d91e0",
            "png_width": 2234,
            "png_height": 579
          },
          {
            "name": "fig3_macro_error_budget",
            "http_status": 200,
            "bytes": 106086,
            "sha256": "d9ec56b4abf6758df63d91c068809477c51f7349a7b544d8b1e6a2a26d0e1c53",
            "png_width": 2234,
            "png_height": 579
          },
          {
            "name": "fig4_stability_gate",
            "http_status": 200,
            "bytes": 56766,
            "sha256": "2466bbb8a89e484edf2862ce909961806a22ab975273b70cd96762b67a1f5773",
            "png_width": 1184,
            "png_height": 729
          },
          {
            "name": "fig5_pareto_front",
            "http_status": 200,
            "bytes": 64495,
            "sha256": "072a5eeb62e23091c67eab89d20c11f59d73bcb91317b5948e98b0c27e53d0bb",
            "png_width": 1177,
            "png_height": 731
          }
        ],
        "platform_tags": [
          "DEM",
          "coarse-graining",
          "scaling-law",
          "verification",
          "TensorDEM"
        ],
        "snapshot_path": "knowledge/kf/wp-11243-01/source_report_11243.md",
        "record_summary": {
          "field": "summary",
          "chars": 314,
          "sha256": "fe328494a4b5f9dfe5bea2dcf2b389abd2bb0eb60385cdd8d682a5e617d95e6e",
          "text": "Implemented and verified two coarse-graining scaling approaches (contact-time invariant k_n∝f³ and sound-speed invariant k_n∝f) across f∈{1,2,4,8}. All macro-invariance criteria met: shear friction angle deviation 0%, repose angle deviation 0°, E_eff deviation 0%. 56 pytest items pass including negative controls.",
          "why": "carried verbatim so that the two record-derived locators (U01/U02) stay verifiable offline instead of being taken on trust"
        }
      },
      "counts": {
        "assets": 15,
        "by_class": {
          "source_document": 1,
          "figure_attachment": 5,
          "specification_block": 5,
          "data_table": 2,
          "test_suite_evidence": 1,
          "quantitative_result_statement": 1
        },
        "by_resolution": {
          "resolved_in_source": 13,
          "referenced_unresolved": 2
        },
        "sections_in_source": 11,
        "toplevel_sections": 6,
        "figure_attachments_declared": 5,
        "figure_attachments_with_bytes": 5,
        "data_tables": 2,
        "locators": 15,
        "locators_resolved": 15,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "report markdown (report_id=11243, field=markdown)",
          "in_report_section": "document",
          "locator": {
            "method": "document",
            "source_field": "markdown",
            "start_char": 0,
            "end_char": 2701,
            "start_line": 0,
            "end_line": 71,
            "quote": "# DEM Coarse-Graining Scaling Rule Table",
            "unique": true,
            "char_len": 2701
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(utf-8 bytes) equals contract source_hash",
            "result": "resolved"
          },
          "byte_len_utf8": 2828,
          "char_len": 2701,
          "sha256": "d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598",
          "note": "identity anchor of the package; snapshot frozen at knowledge/kf/wp-11243-01/source_report_11243.md"
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_attachment",
          "label": "fig1_scaling_laws",
          "in_report_section": "record.figures",
          "locator": {
            "method": "record_field",
            "source_field": "record",
            "pointer": "/figures/0/name",
            "quote": "fig1_scaling_laws"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/11243/figures/fig1_scaling_laws",
            "result": "resolved",
            "http_status": 200,
            "bytes": 131699
          },
          "sha256": "f60910faf8f7570912485036dde4c89f766275a19cf62dbe991bf24acc6d1d43",
          "png_width": 2233,
          "png_height": 579,
          "saved_path": "knowledge/kf/wp-11243-01/figures/fig1_scaling_laws.png",
          "declared_caption": "Scaling laws for k_n, γ, and t_c under both approaches",
          "note": "caption text is copied from the record field, not from prose; the markdown body carries no figure reference, so no figure<->prose mapping is asserted"
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_attachment",
          "label": "fig2_cross_validation",
          "in_report_section": "record.figures",
          "locator": {
            "method": "record_field",
            "source_field": "record",
            "pointer": "/figures/1/name",
            "quote": "fig2_cross_validation"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/11243/figures/fig2_cross_validation",
            "result": "resolved",
            "http_status": 200,
            "bytes": 100966
          },
          "sha256": "951d1d9fb40981bc96413395639e8e43c8108d9edaf7c11012801f79e64d91e0",
          "png_width": 2234,
          "png_height": 579,
          "saved_path": "knowledge/kf/wp-11243-01/figures/fig2_cross_validation.png",
          "declared_caption": "Cross-validation: ratios between approaches match analytic predictions",
          "note": "caption text is copied from the record field, not from prose; the markdown body carries no figure reference, so no figure<->prose mapping is asserted"
        },
        {
          "asset_id": "A04",
          "asset_class": "figure_attachment",
          "label": "fig3_macro_error_budget",
          "in_report_section": "record.figures",
          "locator": {
            "method": "record_field",
            "source_field": "record",
            "pointer": "/figures/2/name",
            "quote": "fig3_macro_error_budget"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/11243/figures/fig3_macro_error_budget",
            "result": "resolved",
            "http_status": 200,
            "bytes": 106086
          },
          "sha256": "d9ec56b4abf6758df63d91c068809477c51f7349a7b544d8b1e6a2a26d0e1c53",
          "png_width": 2234,
          "png_height": 579,
          "saved_path": "knowledge/kf/wp-11243-01/figures/fig3_macro_error_budget.png",
          "declared_caption": "Macro-invariance error budget for shear, repose, and UCS",
          "note": "caption text is copied from the record field, not from prose; the markdown body carries no figure reference, so no figure<->prose mapping is asserted"
        },
        {
          "asset_id": "A05",
          "asset_class": "figure_attachment",
          "label": "fig4_stability_gate",
          "in_report_section": "record.figures",
          "locator": {
            "method": "record_field",
            "source_field": "record",
            "pointer": "/figures/3/name",
            "quote": "fig4_stability_gate"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/11243/figures/fig4_stability_gate",
            "result": "resolved",
            "http_status": 200,
            "bytes": 56766
          },
          "sha256": "2466bbb8a89e484edf2862ce909961806a22ab975273b70cd96762b67a1f5773",
          "png_width": 1184,
          "png_height": 729,
          "saved_path": "knowledge/kf/wp-11243-01/figures/fig4_stability_gate.png",
          "declared_caption": "Stability gate: timestep vs coarse-graining factor",
          "note": "caption text is copied from the record field, not from prose; the markdown body carries no figure reference, so no figure<->prose mapping is asserted"
        },
        {
          "asset_id": "A06",
          "asset_class": "figure_attachment",
          "label": "fig5_pareto_front",
          "in_report_section": "record.figures",
          "locator": {
            "method": "record_field",
            "source_field": "record",
            "pointer": "/figures/4/name",
            "quote": "fig5_pareto_front"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/11243/figures/fig5_pareto_front",
            "result": "resolved",
            "http_status": 200,
            "bytes": 64495
          },
          "sha256": "072a5eeb62e23091c67eab89d20c11f59d73bcb91317b5948e98b0c27e53d0bb",
          "png_width": 1177,
          "png_height": 731,
          "saved_path": "knowledge/kf/wp-11243-01/figures/fig5_pareto_front.png",
          "declared_caption": "Pareto front: speedup vs deviation trade-off",
          "note": "caption text is copied from the record field, not from prose; the markdown body carries no figure reference, so no figure<->prose mapping is asserted"
        },
        {
          "asset_id": "A07",
          "asset_class": "specification_block",
          "label": "口径 A: Contact-Time Invariance",
          "in_report_section": "### 口径 A: Contact-Time Invariance (k_n ∝ f³)",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 255,
            "end_char": 475,
            "start_line": 8,
            "end_line": 13,
            "quote": "### 口径 A: Contact-Time Invariance (k_n ∝ f³)\n- Derived from t_c = π·√(m_eff/k_n) = invariant\n- Since m ∝ f³, we need k_n ∝ f³\n- Preserves contact dynamics exactly\n- Sound speed scales as f·c (may affect dynamic loading)\n",
            "char_len": 220
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim char-span slice of markdown, re-verified as substring",
            "result": "resolved"
          },
          "note": "derivation block of scaling approach A (contact-time invariant)",
          "structure": {
            "subsections": [
              "### 口径 A: Contact-Time Invariance (k_n ∝ f³)"
            ],
            "subsection_count": 1
          }
        },
        {
          "asset_id": "A08",
          "asset_class": "specification_block",
          "label": "口径 B: Sound-Speed Invariance",
          "in_report_section": "### 口径 B: Sound-Speed Invariance (k_n ∝ f)",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 476,
            "end_char": 693,
            "start_line": 14,
            "end_line": 19,
            "quote": "### 口径 B: Sound-Speed Invariance (k_n ∝ f)\n- Derived from c = √(k_n/m_eff)·L_char = invariant\n- k_n ∝ f preserves macroscopic wave propagation\n- Contact time grows linearly: t_c ∝ f\n- Force peaks may smear at large f\n",
            "char_len": 217
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim char-span slice of markdown, re-verified as substring",
            "result": "resolved"
          },
          "note": "derivation block of scaling approach B (sound-speed invariant)",
          "structure": {
            "subsections": [
              "### 口径 B: Sound-Speed Invariance (k_n ∝ f)"
            ],
            "subsection_count": 1
          }
        },
        {
          "asset_id": "A09",
          "asset_class": "data_table",
          "label": "Scaling Rule Table",
          "in_report_section": "## Scaling Rule Table",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 694,
            "end_char": 1263,
            "start_line": 20,
            "end_line": 37,
            "quote": "## Scaling Rule Table\n\n| Quantity | 口径 A (Contact-Time) | 口径 B (Sound-Speed) |\n|----------|----------------------|---------------------|\n| radius | f·R | f·R |\n| mass | f³·m | f³·m |\n| inertia | f⁵·I | f⁵·I |\n| kn | f³·k_n | f·k_n |\n| kt | f³·k_t | f·k_t |\n| kr | f⁵·k_r | f³·k_r |\n| gamma | f³·γ | f²·γ |\n| contact_time | t_c (invariant) | f·t_c |\n| sound_speed | f·c | c (invariant) |\n| restitution | e (invariant) | e (invariant) |\n| mu | μ (invariant) | μ (invariant) |\n| mu_rolling | μ_r (invariant) | μ_r (invariant) |\n| gravity | g (invariant) | g (invariant) |\n",
            "char_len": 569
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim char-span slice of markdown, re-verified as substring",
            "result": "resolved"
          },
          "note": "the quantity->scaling table for both approaches",
          "structure": {
            "pipe_rows_total": 15,
            "columns": [
              "Quantity",
              "口径 A (Contact-Time)",
              "口径 B (Sound-Speed)"
            ],
            "data_rows": 13,
            "column_count": 3
          }
        },
        {
          "asset_id": "A10",
          "asset_class": "specification_block",
          "label": "Applicability Domains",
          "in_report_section": "## Applicability Domains",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1264,
            "end_char": 1760,
            "start_line": 38,
            "end_line": 49,
            "quote": "## Applicability Domains\n\n### A_contact_time_invariant\n- **Best for**: Contact dynamics, force-displacement curves, restitution\n- **Valid range**: f ≤ 4 (f=8 may show minor deviations)\n- **Failure mode**: Wave speed scales as f·c, may affect dynamic loading\n\n### B_sound_speed_invariant\n- **Best for**: Wave propagation, dynamic loading, seismic response\n- **Valid range**: f ≤ 4 (f=8 contact time grows, may need larger dt)\n- **Failure mode**: Contact time grows as f·t_c, force peaks may smear\n",
            "char_len": 496
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim char-span slice of markdown, re-verified as substring",
            "result": "resolved"
          },
          "note": "per-approach suitable use / valid f range / failure mode",
          "structure": {
            "subsections": [
              "### A_contact_time_invariant",
              "### B_sound_speed_invariant"
            ],
            "subsection_count": 2
          }
        },
        {
          "asset_id": "A11",
          "asset_class": "data_table",
          "label": "Failure Boundaries",
          "in_report_section": "## Failure Boundaries",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1761,
            "end_char": 2124,
            "start_line": 50,
            "end_line": 58,
            "quote": "## Failure Boundaries\n\n| Factor f | 口径 A Valid? | 口径 B Valid? | Notes |\n|----------|--------------|--------------|-------|\n| 1 | ✓ | ✓ | Baseline |\n| 2 | ✓ | ✓ | Both approaches within tolerance |\n| 4 | ✓ (borderline) | ✓ | A: minor wave speed drift; B: contact time 4× |\n| 8 | ⚠ (may fail) | ⚠ (may fail) | A: wave speed 8×; B: contact time 8×, force smearing |\n",
            "char_len": 363
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim char-span slice of markdown, re-verified as substring",
            "result": "resolved"
          },
          "note": "validity gate table indexed by coarse-graining factor f",
          "structure": {
            "pipe_rows_total": 6,
            "columns": [
              "Factor f",
              "口径 A Valid?",
              "口径 B Valid?",
              "Notes"
            ],
            "data_rows": 4,
            "column_count": 4
          }
        },
        {
          "asset_id": "A12",
          "asset_class": "specification_block",
          "label": "Negative Controls",
          "in_report_section": "## Negative Controls",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 2125,
            "end_char": 2312,
            "start_line": 59,
            "end_line": 63,
            "quote": "## Negative Controls\n\n1. **Mass-only scaling** (m → f³m, k_n unchanged): breaks contact time by f^(3/2)\n2. **Wrong k_n scaling** (k_n ∝ f³ for sound-speed intent): breaks wave speed by f\n",
            "char_len": 187
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim char-span slice of markdown, re-verified as substring",
            "result": "resolved"
          },
          "note": "the two controls that must fail if scaling is wrong"
        },
        {
          "asset_id": "A13",
          "asset_class": "specification_block",
          "label": "Recommendations",
          "in_report_section": "## Recommendations",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 2313,
            "end_char": 2701,
            "start_line": 64,
            "end_line": 72,
            "quote": "## Recommendations\n\n- Use **口径 A** when contact dynamics, force-displacement curves, and restitution\n  are the primary concern (f ≤ 4 recommended).\n- Use **口径 B** when wave propagation, dynamic loading, and seismic response\n  are the primary concern (f ≤ 4 recommended).\n- For f > 4, both approaches show increasing deviations; consider hybrid\n  approaches or full-resolution simulation.\n",
            "char_len": 388
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim char-span slice of markdown, re-verified as substring",
            "result": "resolved"
          },
          "note": "approach-selection guidance, including the f>4 caveat"
        }
      ],
      "unresolved_references": [
        {
          "asset_id": "U01",
          "asset_class": "test_suite_evidence",
          "label": "pytest suite behind the pass count",
          "in_report_section": "record.summary",
          "locator": {
            "method": "record_field",
            "source_field": "record",
            "pointer": "/summary",
            "quote": "56 pytest items pass including negative controls."
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "search markdown for the same statement / a repo path",
            "result": "absent",
            "markdown_occurrences": 0
          },
          "note": "the count exists only in the record summary; no test path, commit or log is carried by this report, so the suite is not resolvable from the source and is NOT registered as verified evidence"
        },
        {
          "asset_id": "U02",
          "asset_class": "quantitative_result_statement",
          "label": "macro-invariance deviations stated in the record summary",
          "in_report_section": "record.summary",
          "locator": {
            "method": "record_field",
            "source_field": "record",
            "pointer": "/summary",
            "quote": "All macro-invariance criteria met: shear friction angle deviation 0%, repose angle deviation 0°, E_eff deviation 0%."
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "search markdown for the same numbers",
            "result": "absent",
            "markdown_occurrences": {
              "0%": 0,
              "56": 0,
              "deviation": 2
            },
            "note_on_token_deviation": "the word occurs only as the qualitative phrase 'deviations' in the failure-boundary notes; no measured error value is carried by the prose"
          },
          "note": "the 0%/0°/0% deviations are record-level prose only; the markdown table states scaling rules and validity bands, not measured errors, so the numbers stay unverified here and no claim is derived from them"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "every markdown quote occurs exactly once; record-field quotes are checked as substrings of the field",
        "hash_recomputed_locally": {
          "source_hash_matches_contract": true,
          "chars_match_contract": true,
          "all_locators_resolved": true,
          "all_markdown_quotes_unique": true,
          "no_duplicate_ids": true,
          "claims_empty_by_contract": true,
          "no_verified_marks_emitted": true,
          "single_report_scope": true,
          "no_extraction_performed": true
        },
        "hash_matches_contract": true,
        "locator_verification": [
          {
            "asset_id": "A01",
            "source_field": "markdown",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 40,
            "line_consistent": true
          },
          {
            "asset_id": "A02",
            "source_field": "record",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 17
          },
          {
            "asset_id": "A03",
            "source_field": "record",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 21
          },
          {
            "asset_id": "A04",
            "source_field": "record",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 23
          },
          {
            "asset_id": "A05",
            "source_field": "record",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 19
          },
          {
            "asset_id": "A06",
            "source_field": "record",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 17
          },
          {
            "asset_id": "A07",
            "source_field": "markdown",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 220,
            "line_consistent": true
          },
          {
            "asset_id": "A08",
            "source_field": "markdown",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 217,
            "line_consistent": true
          },
          {
            "asset_id": "A09",
            "source_field": "markdown",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 569,
            "line_consistent": true
          },
          {
            "asset_id": "A10",
            "source_field": "markdown",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 496,
            "line_consistent": true
          },
          {
            "asset_id": "A11",
            "source_field": "markdown",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 363,
            "line_consistent": true
          },
          {
            "asset_id": "A12",
            "source_field": "markdown",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 187,
            "line_consistent": true
          },
          {
            "asset_id": "A13",
            "source_field": "markdown",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 388,
            "line_consistent": true
          },
          {
            "asset_id": "U01",
            "source_field": "record",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 49
          },
          {
            "asset_id": "U02",
            "source_field": "record",
            "resolved": true,
            "uniqueness_count": 1,
            "quote_len": 116
          }
        ],
        "duplicate_ids": [],
        "checks": {
          "source_hash_matches_contract": true,
          "chars_match_contract": true,
          "all_locators_resolved": true,
          "all_markdown_quotes_unique": true,
          "no_duplicate_ids": true,
          "claims_empty_by_contract": true,
          "no_verified_marks_emitted": true,
          "single_report_scope": true,
          "no_extraction_performed": true
        },
        "scope_statement": "read-only on report_id=11243; no other report touched; no upstream artifact rewritten; nothing marked verified"
      }
    }
  },
  "claims": []
}
```
