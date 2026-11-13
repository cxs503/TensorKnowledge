# KF-RESULT wp-771-04

> 工序：`04-independent-review` ｜ 报告：`771` ｜ 审核对象：`wp-771-01`（源资产登记）
> 分层=DEM|dem_granular_hopper_beverloo|m ｜ 状态：in-review ｜ 结论：**pass**（0 条 blocking 发现）
> 审核者：`agent/m15802`（mission 15802）｜ 生产者：mission 15518

## ① 本工序做了什么

只碰 `report_id=771` 这一份报告，对上游工作包 `wp-771-01` 的产物（源资产登记 `asset_manifest.json`）
做一次**独立审核**：不采信上游自述，而是把它当断言集合，逐条从报告 771 的 markdown 字节与
record 字段重算。共 **18 项检查**（16 pass /
2 fail，其中 blocking fail **0** 项）、
**6 条发现**（blocking 0 条；low 2 条、
info 4 条），结论 **pass**。

- 上游 01 工序契约的 6 项验收（valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status）**逐项重算全部 pass**（见 §③ 表 A）。
- 语义层：01 不携带 claim（`env.claims=[]`），所以可判的语义保真度是「manifest 是否忠实登记了报告 771 真实
  含有的东西」——资产集合完整、可解析/未解析判定诚实、无编造资产。判定：**faithful**。
- 未标 verified：本审核只给 disposition（pass），verification 等级由平台门计算
  （`review_report.verification.self_marked_verified=false`）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/771`（agent token），只取 `markdown` + record 字段；
   另取上游结果报告 `id=14569` 的 markdown，从其中
   **唯一一个** json 代码块解析出上游信封（块数≠1 即拒绝）。
2. **算身份**：对 markdown 的 UTF-8 字节重算 sha256 =
   `sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559`，与契约 `input.source_hash` 比对；
   字符数 2143 与 `input.chars` 比对（RC1）。
3. **定位符反查（核心）**：上游登记的每个 markdown 定位符都用 `source[char_start:char_end] == quote`
   **精确切片**校验，并要求该 quote 在全文**唯一出现**（`re.finditer` 出现的偏移集合必须恰为 `[char_start]`）；
   每个 record 定位符按 `figures[0].name` 这类路径在 live record 上重解析后逐字比对。共反查
   **6 条 markdown + 6 条 record** 定位符。
4. **计数独立重算**：total/resolvable/unresolved/by_kind 全部从 assets 数组重新统计，与 manifest 声明比对（RC9）；
   asset_id 唯一性（RC10）；单报告范围（RC11，扫描全部 string 里的 `reports/(\d+)`）。
5. **诚实验证**：未解析资产必须带非空 `unresolved_reason`（RC13）；源文中出现的每个文件类 token 是否都已登记
   （RC14，防漏资产）；三条 record 图名是否都已登记。
6. **图字节可达性独立重探**：逐张 `GET /tensor/reports/771/figures/<name>` 记录 HTTP 状态；
   并用平台 OpenAPI 判定「列表路由是否存在」，以区分**路由缺失**与**资产缺失**（RC18）。
7. **结构与形状**：上游信封按仓库唯一适用 schema `schemas/kf_result.v1.schema.json` 校验（RC3）；
   资产记录键覆盖统计（RC16）；最短引文长度 vs 平台 `min_quote_chars=12`（RC17）。
8. **上下文隔离**：审核输入 = 源文档 + record + 上游 outputs；上游报告正文的解释性叙述**不作为证据**，
   本报告每条证据都指回源字节/源字段。上游 prompt 从未读取（审核 prompt 按 04 契约自写）。

工具链：Python 3.11 + `jsonschema` + `matplotlib`；无外部数据依赖。

一键复跑：

```
python3 scripts/kf_wp771_04_review.py            # 联网重算 + 重写产物
python3 scripts/kf_wp771_04_review.py --offline  # 仅凭 artifacts 快照重放
python3 scripts/kf_wp771_04_emit_report.py       # 重出本报告与图
python3 -m pytest tests/test_kf_wp771_04_review.py -q
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/kf/wp-771-04/review_report.json` | 本工序正式交付物（review_report.v1）：18 项检查 + 6 条发现 + disposition |
| `artifacts/kf/wp-771-04/kf_result.json` | KF-RESULT 信封（`schemas/kf_result.v1` 0 error），`outputs.review_report.json` |
| `artifacts/kf/wp-771-04/review_checks.json` | 检查/发现机读明细（含每项 evidence 原始值） |
| `artifacts/kf/wp-771-04/upstream_asset_manifest.json` | 从上游信封抽出的 manifest 快照（审核对象） |
| `artifacts/kf/wp-771-04/source/` | 报告 771 markdown/record、上游结果报告 markdown、图字节探测原始结果（离线重放用） |
| `artifacts/kf/wp-771-04/review_report.v1.schema.json` | 本工序结构自校（0 error） |
| `artifacts/kf/wp-771-04/selfcheck.json` | 验收项逐条自检明细 |
| `artifacts/kf/wp-771-04/fig1_review_checks.png` | 图 1：独立重算的资产分布 + 定位符反查结果 |
| `scripts/kf_wp771_04_review.py` | 一键复跑：取原文→重算→反查→出产物 |
| `scripts/kf_wp771_04_emit_report.py` | 生成本报告与图（数字/引文程序化注入） |
| `tests/test_kf_wp771_04_review.py` | 离线断言：哈希、定位符逐字唯一、计数、范围、未标 verified、结构 |

**表 A：上游 01 契约验收项的独立重算结果**

| 上游验收项 | 重算结果 | 依据检查 |
|---|---|---|
| valid_json | pass | RC2 |
| schema_pass | pass | RC3 |
| source_hash_matches | pass | RC5 |
| source_locator_resolvable | pass | RC7, RC8 |
| no_duplicate_ids | pass | RC10 |
| all_claims_have_evidence_or_explicit_unresolved_status | pass | RC12 |

**表 B：图字节可达性（本工序独立重探）**

| 图名 | 探针结果 |
|---|---|
| fig1_beverloo_qbc.png | HTTP 404 |
| fig2_beverloo_linearity.png | HTTP 404 |
| fig3_rate_series.png | HTTP 404 |

## ④ 证据定位表（claim → 原文逐字片段；偏移由程序 `find` 得出）

源文件 `tensor://reports/771`，字段 `markdown`，sha256=`sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559`，
chars=2143。

| id | 主张 | 原文引文（逐字） | 实测偏移 | 上游声明偏移 | 反查结论 |
|---|---|---|---|---|---|
| C1 | ast-771-20 源引用定位 | ``src/tensordem/granular_dem.py`` | 482 | 482..513 | 逐字一致且唯一 |
| C2 | ast-771-21 源引用定位 | ``examples/hopper_beverloo_case.py`` | 516 | 516..550 | 逐字一致且唯一 |
| C3 | ast-771-22 源引用定位 | ``hopper_beverloo_report.py`` | 553 | 553..580 | 逐字一致且唯一 |
| C4 | ast-771-23 源引用定位 | `outputs/*.json` | 590 | 590..604 | 逐字一致且唯一 |
| C5 | ast-771-24 源引用定位（最短 7 字符） | `CASE.md` | 608 | 608..615 | 逐字一致且唯一 |
| C6 | 报告声称图已内嵌（图字节却不可取） | `见图内嵌` | 1558 | - | 未登记/不匹配 |

**record 字段定位符（源字段路径 → 值，逐字相等）**

| asset_id | 字段路径 | 声明值 | 反查结论 |
|---|---|---|---|
| ast-771-02 | `id` | `771` | 从 live record 解析后逐字相等 |
| ast-771-02 | `title` | `TensorDEM：料仓卸料 Beverloo 标度复现 + 休止角（honest 部分失败）` | 从 live record 解析后逐字相等 |
| ast-771-02 | `scenario_key` | `dem_granular_hopper_beverloo` | 从 live record 解析后逐字相等 |
| ast-771-10 | `figures[0].name` | `fig1_beverloo_qbc.png` | 从 live record 解析后逐字相等 |
| ast-771-11 | `figures[1].name` | `fig2_beverloo_linearity.png` | 从 live record 解析后逐字相等 |
| ast-771-12 | `figures[2].name` | `fig3_rate_series.png` | 从 live record 解析后逐字相等 |

**检查明细（18 项）**

| id | 检查 | 结果 | 映射上游验收项 | 说明 |
|---|---|---|---|---|
| RC1 | contract_source_identity | pass | — | recomputed sha256:c9ba197538ee chars=2143 bytes=3623 vs contract sha256:c9ba197538ee chars=2143 |
| RC2 | upstream_single_json_block | pass | valid_json | upstream markdown carries exactly 1 json block, parsed as envelope with keys ['package_id', 'task_type', 'report_id', 'provenance', 'outputs', 'claims'] |
| RC3 | envelope_schema_pass | pass | schema_pass | schemas/kf_result.v1.schema.json validation: 0 error(s) |
| RC4 | envelope_identity | pass | — | package_id='wp-771-01' report_id='771' task_type='01-asset-registration' |
| RC5 | provenance_hash_matches_recomputed | pass | source_hash_matches | claimed sha256:c9ba197538ee vs recomputed sha256:c9ba197538ee, field='markdown' |
| RC6 | manifest_source_block_vs_recomputed | pass | — | hash=True chars=2143==2143 bytes=3623==3623 title_match=True scenario_match=True |
| RC7 | markdown_locators_resolve | pass | source_locator_resolvable | 6 markdown locators re-resolved against source bytes: exact-slice + unique-offset failures = 0 |
| RC8 | record_locators_resolve | pass | source_locator_resolvable | 6 record locators re-read from the live record fields: mismatches = 0 |
| RC9 | counts_recomputed | pass | — | declared total/resolvable/unresolved=10/2/8 vs recomputed 10/2/8; by_kind equal=True |
| RC10 | no_duplicate_asset_ids | pass | no_duplicate_ids | 10 asset ids, duplicates=[], declared duplicate_asset_ids=[] |
| RC11 | single_report_scope | pass | — | source_uri report ids referenced = ['771']; scope.reports_touched=['771'] |
| RC12 | constraints_zero_claim_zero_self_verification | pass | all_claims_have_evidence_or_explicit_unresolved_status | env.claims=[], claims_registered=0, extraction.performed=False, verification.performed=False |
| RC13 | unresolved_assets_carry_reason | pass | — | 8 unresolved assets, 0 without a non-empty unresolved_reason |
| RC14 | asset_coverage_of_source_references | pass | — | 5 file-like tokens found in source, unregistered=[]; record figures ['fig1_beverloo_qbc.png', 'fig2_beverloo_linearity.png', 'fig3_rate_series.png'] all declared=True |
| RC15 | figure_bytes_unreachable_independently_reprobed | pass | — | re-probed GET /tensor/reports/771/figures/<name> -> {'fig1_beverloo_qbc.png': 404, 'fig2_beverloo_linearity.png': 404, 'fig3_rate_series.png': 404}; supports 'unresolved… |
| RC16 | asset_record_shape_uniform | fail | — | core keys ['asset_id', 'kind', 'role', 'name', 'resolvable', 'resolution', 'locators'] present on all 10 assets? missing={}; partially covered keys (present on some asse… |
| RC17 | shortest_locator_quote_vs_min_quote_chars | fail | — | shortest markdown quote = {'asset_id': 'ast-771-24', 'quote': 'CASE.md', 'chars': 7}; quotes below platform min_quote_chars=12: [('ast-771-24', 7)] (that threshold gover… |
| RC18 | figure_list_route_existence | pass | — | upstream recorded list route GET /tensor/reports/771/figures -> HTTP 404; that list route present in platform OpenAPI = False (only /figures/{name} exists) -> list-route… |

**发现（6 条，按严重度）**

| id | 严重度 | blocking | 陈述 | 建议修复 |
|---|---|---|---|---|
| F1 | low | 否 | asset records are not shape-uniform: status (8/10), unresolved_reason (8/10). The two resolvable assets carry no status/unresolved_reason while the eight unresolved ones do, so a downstream consumer that reads status on every asset breaks on exactly the two it most needs; the core keys themselves are complete. | normalise every asset record to one key set (resolvable ones also carry status='resolved' plus a resolution text) before 02/03 consume the manifest. |
| F2 | low | 否 | shortest markdown locator is 7 chars (quote 'CASE.md'), below the platform min_quote_chars=12; it resolves here only because the token is unique in this 2143-char report. Reused as claim evidence at 03 it would be rejected by g5_source_locator_resolvable. | for short file names quote a longer span (the surrounding clause) so the locator stays above the platform threshold. |
| F3 | info | 否 | the source-document asset is anchored on a 43-char prefix (2.0% of the document); its 'resolvable: true' cannot be derived from the asset locator alone - document identity is carried by the manifest.source block instead. | declare source-document assets with a whole-document locator (0..chars) and keep a short anchor only for display. |
| F4 | info | 否 | upstream bundles a figures-list route 404 with the per-figure 404s; that list route does not exist in the platform OpenAPI, so the two are not the same kind of evidence (route absence vs missing bytes). The 'unresolved' verdict still stands on the per-figure probes. | label route-absence probes as such or drop them from the evidence bundle. |
| F5 | info | 否 | the platform evidence gate resolves locators only inside `claims`; with claims=[] it reports g5 checked=0, so the asset locators are never resolved by the gate. This review is the only evidence-grade check of the 01 output. | extend g5 to walk asset locators when claims are empty, or make the 04 review a required gate for 01 on lane C. |
| F6 | info | 否 | there is no general schema for the asset_manifest.json body; the only asset-manifest schema in the repo pins package_id const 'wp-448-01', so it cannot validate this package. Upstream 'schema_pass' is provable only at envelope level (RC3). | generalise the asset_manifest schema (package/report as pattern instead of const) so 01 outputs are machine-checkable across reports. |

## ⑤ 注意点与局限

- **只审 01，不审数值**：`wp-771-01` 是登记工序，不承载任何数值断言，故本工序没有可复算的数字；
  报告 771 的 Beverloo 拟合（C=0.766、R²=0.99498）与休止角 honest FAIL 属于后续抽取/数值审核的对象。
- **可解析性口径**：判定「resolvable」限定在报告存储（附件/字节可取）内。只在生产仓里存在的文件按口径
  记为 unresolved，这不等于文件不存在；本次未跨仓核对（见 §⑥ not_run）。
- **上游正文只作定向阅读**：本报告的每条证据都指回源字节/源字段，没有一条依赖上游的解释性叙述。
- **形状与阈值两条非阻断发现**：资产记录键不全覆盖（`status`/`unresolved_reason` 8/10，缺的正是两条可解析资产）
  与最短定位符 7 字符低于平台 `min_quote_chars=12`——两者都不违反 01 契约，但会让下游 02/03 或未来的 claim
  引文复用踩坑，建议在上游修复而不是等下游兜。
- **门覆盖缺口（机制级，F5）**：平台证据门只在 `claims` 内反查定位符，`claims=[]` 时 g5 报 `checked=0`
  （只读观测：`runuser -u postgres -- psql -d tensorplatform -tA -c "select package_id,status,gates_ok,gates from tk_work_packages where report_id='771'"`）；
  也就是说本次审核反查的 12 条资产定位符，
  平台门自己一条都没查过。这条不归上游，归产线机制。
- **谁都没跑过的检查**：见 `review_report.checks_not_run`（跨仓文件存在性、DEM 复算、平台门端到端重跑）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结论 | 依据 |
|---|---|---|
| valid_json | ✓ | kf_result.json and review_report.json round-trip through json.load and validate against schemas/kf_result.v1.schema.json and review_report.v1 |
| schema_pass | ✓ | kf_result envelope: 0 jsonschema errors; review_report: 0 jsonschema errors |
| reviewer_independent | ✓ | producer mission 15518 != reviewer mission 15802; reviewer identity agent/m15802 never produced wp-771-01 |
| upstream_packages_completed | ✓ | wp-771-01 result report id 14569 fetched and its envelope re-validated (RC2/RC3) |
| do_not_mark_claims_as_verified | ✓ | review_report.verification.self_marked_verified=false; the upstream claims list is empty so nothing could be verified |
| review_prompt_not_copied_from_producer | ✓ | the 04 review prompt was authored for this package from the contract text; the 01 producer prompt was never read |
| reviewer_context_excludes_producer_explanation | ✓ | review inputs = source markdown, record fields, upstream envelope outputs; producer narrative excluded from every finding's evidence chain |
| single_report_scope_771_only | ✓ | report 771 + wp-771-01 only; RC11 confirms the upstream manifest itself references no other report_id |
| source_hash_matches_source_uri | ✓ | sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559 == contract input.source_hash |

- 未完成/不适用项如实登记：`checks_not_run` 3 项（跨仓文件存在性、DEM 案例复算、平台门端到端重跑），
  原因均为超出本工序范围或本工作树无外网/仓访问，**不记作 pass**。
- 本工序**不**把任何上游结论标为 verified：`verification.self_marked_verified=false`。

## 结果信封（唯一一个 json 代码块）

```json
{
 "package_id": "wp-771-04",
 "task_type": "04-independent-review",
 "report_id": "771",
 "provenance": {
  "source_hash": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
  "source_field": "markdown",
  "producer": "agent/m15802",
  "emitted_at": "2026-11-12T02:44:15+00:00",
  "notes": "independent review of wp-771-01 (result report 14569); source hash recomputed from report 771 markdown bytes; disposition=pass; nothing marked verified (verification is computed by the platform gate)"
 },
 "outputs": {
  "review_report.json": {
   "schema": "review_report.v1",
   "package_id": "wp-771-04",
   "task_type": "04-independent-review",
   "report_id": "771",
   "reviewed_package": "wp-771-01",
   "reviewed_package_id": "wp-771-01",
   "reviewed_artifacts": {
    "source_hash": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
    "source_chars": 2143,
    "upstream_result_report_id": 14569,
    "upstream_envelope_sha256": "2086d4d70dd25cddc73cfe3259478f8e01239eb428b5f74e903835aff9d0f7dc",
    "upstream_result_markdown_sha256": "f824b7a859777cb6b0fc15f6f34d7b170ab09fd690adecb393be5508ddb8f846",
    "upstream_output_key": "asset_manifest.json"
   },
   "reviewer": {
    "role": "red-team-reviewer",
    "identity": "agent/m15802",
    "mission_id": 15802,
    "independence": {
     "producer_mission_id": 15518,
     "reviewer_mission_id": 15802,
     "independent": true
    },
    "context_policy": "source markdown + report record + upstream envelope outputs only; the producer's narrative explanation is not used as evidence, and every upstream assertion is re-derived from raw bytes/fields by scripts/kf_wp771_04_review.py",
    "review_prompt_origin": "written for this work package from the 04 contract (not copied from the 01 producer prompt)"
   },
   "semantic_fidelity": {
    "applicable_scope": "task_type=01 carries no claims (env.claims=[]), so no claim-level semantic fidelity exists to judge; the applicable semantic question is whether the manifest faithfully registers what report 771 actually contains - asset set complete, resolvable/unresolved verdicts truthful, no invented assets.",
    "judgement": "faithful",
    "basis": [
     "all 6 markdown locators re-slice exactly at the declared offsets and each quote is unique in the source (RC7)",
     "all 6 record locators re-read equal to the live record fields (RC8)",
     "asset counts recomputed exactly: 10 total / 2 resolvable / 8 unresolved (RC9)",
     "every unresolved asset carries a non-empty unresolved_reason; none is dressed up as resolvable (RC13)",
     "no asset is invented: every file-like token in the source is registered, and the three record figures are all declared (RC14)",
     "the unresolved verdict on the three figures is independently reproduced by re-probing the figure bytes (RC15)"
    ]
   },
   "checks": [
    {
     "id": "RC1",
     "name": "contract_source_identity",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": null,
     "detail": "recomputed sha256:c9ba197538ee chars=2143 bytes=3623 vs contract sha256:c9ba197538ee chars=2143",
     "evidence": {
      "observed_hash": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
      "observed_chars": 2143,
      "observed_bytes_utf8": 3623,
      "contract_hash": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
      "contract_chars": 2143
     }
    },
    {
     "id": "RC2",
     "name": "upstream_single_json_block",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": "valid_json",
     "detail": "upstream markdown carries exactly 1 json block, parsed as envelope with keys ['package_id', 'task_type', 'report_id', 'provenance', 'outputs', 'claims']",
     "evidence": {
      "block_count": 1,
      "envelope_keys": [
       "package_id",
       "task_type",
       "report_id",
       "provenance",
       "outputs",
       "claims"
      ]
     }
    },
    {
     "id": "RC3",
     "name": "envelope_schema_pass",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": "schema_pass",
     "detail": "schemas/kf_result.v1.schema.json validation: 0 error(s)",
     "evidence": {
      "schema": "schemas/kf_result.v1.schema.json",
      "errors": []
     }
    },
    {
     "id": "RC4",
     "name": "envelope_identity",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": null,
     "detail": "package_id='wp-771-01' report_id='771' task_type='01-asset-registration'",
     "evidence": {
      "package_id": "wp-771-01",
      "report_id": "771",
      "task_type": "01-asset-registration"
     }
    },
    {
     "id": "RC5",
     "name": "provenance_hash_matches_recomputed",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": "source_hash_matches",
     "detail": "claimed sha256:c9ba197538ee vs recomputed sha256:c9ba197538ee, field='markdown'",
     "evidence": {
      "claimed": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
      "recomputed": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
      "source_field": "markdown"
     }
    },
    {
     "id": "RC6",
     "name": "manifest_source_block_vs_recomputed",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": null,
     "detail": "hash=True chars=2143==2143 bytes=3623==3623 title_match=True scenario_match=True",
     "evidence": {
      "declared": {
       "sha256": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
       "chars": 2143,
       "byte_length_utf8": 3623,
       "title": "TensorDEM：料仓卸料 Beverloo 标度复现 + 休止角（honest 部分失败）",
       "scenario_key": "dem_granular_hopper_beverloo"
      },
      "recomputed": {
       "sha256": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
       "chars": 2143,
       "byte_length_utf8": 3623,
       "title": "TensorDEM：料仓卸料 Beverloo 标度复现 + 休止角（honest 部分失败）",
       "scenario_key": "dem_granular_hopper_beverloo"
      }
     }
    },
    {
     "id": "RC7",
     "name": "markdown_locators_resolve",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": "source_locator_resolvable",
     "detail": "6 markdown locators re-resolved against source bytes: exact-slice + unique-offset failures = 0",
     "evidence": {
      "checked": 6,
      "failures": []
     }
    },
    {
     "id": "RC8",
     "name": "record_locators_resolve",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": "source_locator_resolvable",
     "detail": "6 record locators re-read from the live record fields: mismatches = 0",
     "evidence": {
      "checked": 6,
      "failures": []
     }
    },
    {
     "id": "RC9",
     "name": "counts_recomputed",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": null,
     "detail": "declared total/resolvable/unresolved=10/2/8 vs recomputed 10/2/8; by_kind equal=True",
     "evidence": {
      "declared": {
       "total": 10,
       "resolvable": 2,
       "unresolved": 8,
       "by_kind": {
        "source_document": 1,
        "record_metadata": 1,
        "figure": 3,
        "source_code": 1,
        "example_script": 1,
        "report_generator": 1,
        "data_artifact_glob": 1,
        "case_markdown": 1
       },
       "duplicate_asset_ids": []
      },
      "recomputed": {
       "total": 10,
       "resolvable": 2,
       "unresolved": 8,
       "by_kind": {
        "source_document": 1,
        "record_metadata": 1,
        "figure": 3,
        "source_code": 1,
        "example_script": 1,
        "report_generator": 1,
        "data_artifact_glob": 1,
        "case_markdown": 1
       }
      }
     }
    },
    {
     "id": "RC10",
     "name": "no_duplicate_asset_ids",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": "no_duplicate_ids",
     "detail": "10 asset ids, duplicates=[], declared duplicate_asset_ids=[]",
     "evidence": {
      "ids": [
       "ast-771-01",
       "ast-771-02",
       "ast-771-10",
       "ast-771-11",
       "ast-771-12",
       "ast-771-20",
       "ast-771-21",
       "ast-771-22",
       "ast-771-23",
       "ast-771-24"
      ],
      "duplicates": []
     }
    },
    {
     "id": "RC11",
     "name": "single_report_scope",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": null,
     "detail": "source_uri report ids referenced = ['771']; scope.reports_touched=['771']",
     "evidence": {
      "report_ids_referenced": [
       "771"
      ],
      "reports_touched": [
       "771"
      ]
     }
    },
    {
     "id": "RC12",
     "name": "constraints_zero_claim_zero_self_verification",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": "all_claims_have_evidence_or_explicit_unresolved_status",
     "detail": "env.claims=[], claims_registered=0, extraction.performed=False, verification.performed=False",
     "evidence": {
      "claims": [],
      "claims_registered": 0,
      "extraction": {
       "performed": false,
       "reason": "contract objective is register_assets only (classify_report_type false); extraction belongs to a separate work package"
      },
      "verification": {
       "performed": false,
       "reason": "verification status is computed by the platform gate, never self-assigned"
      }
     }
    },
    {
     "id": "RC13",
     "name": "unresolved_assets_carry_reason",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": null,
     "detail": "8 unresolved assets, 0 without a non-empty unresolved_reason",
     "evidence": {
      "offenders": []
     }
    },
    {
     "id": "RC14",
     "name": "asset_coverage_of_source_references",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": null,
     "detail": "5 file-like tokens found in source, unregistered=[]; record figures ['fig1_beverloo_qbc.png', 'fig2_beverloo_linearity.png', 'fig3_rate_series.png'] all declared=True",
     "evidence": {
      "tokens_in_source": [
       "CASE.md",
       "examples/hopper_beverloo_case.py",
       "hopper_beverloo_report.py",
       "outputs/*.json",
       "src/tensordem/granular_dem.py"
      ],
      "unregistered": [],
      "record_figures": [
       "fig1_beverloo_qbc.png",
       "fig2_beverloo_linearity.png",
       "fig3_rate_series.png"
      ]
     }
    },
    {
     "id": "RC15",
     "name": "figure_bytes_unreachable_independently_reprobed",
     "result": "pass",
     "blocking": true,
     "maps_to_upstream_acceptance": null,
     "detail": "re-probed GET /tensor/reports/771/figures/<name> -> {'fig1_beverloo_qbc.png': 404, 'fig2_beverloo_linearity.png': 404, 'fig3_rate_series.png': 404}; supports 'unresolved' for all 3 figures = True",
     "evidence": {
      "probe": {
       "list_route_status": 404,
       "list_route_in_openapi": false,
       "binary_status": {
        "fig1_beverloo_qbc.png": 404,
        "fig2_beverloo_linearity.png": 404,
        "fig3_rate_series.png": 404
       }
      }
     }
    },
    {
     "id": "RC16",
     "name": "asset_record_shape_uniform",
     "result": "fail",
     "blocking": false,
     "maps_to_upstream_acceptance": null,
     "detail": "core keys ['asset_id', 'kind', 'role', 'name', 'resolvable', 'resolution', 'locators'] present on all 10 assets? missing={}; partially covered keys (present on some assets only) = {'status': 8, 'unresolved_reason': 8}; full presence counts = {'asset_id': 10, 'kind': 10, 'role': 10, 'name': 10, 'resolvable': 10, 'resolution': 10, 'locators': 10, 'status': 8, 'unresolved_reason': 8, 'caption': 3, 'caption_equals_name': 3, 'values': 1, 'content_ref': 1, 'byte_length_utf8': 1}",
     "evidence": {
      "core_keys": [
       "asset_id",
       "kind",
       "role",
       "name",
       "resolvable",
       "resolution",
       "locators"
      ],
      "presence_counts": {
       "asset_id": 10,
       "kind": 10,
       "role": 10,
       "name": 10,
       "resolvable": 10,
       "resolution": 10,
       "locators": 10,
       "status": 8,
       "unresolved_reason": 8,
       "caption": 3,
       "caption_equals_name": 3,
       "values": 1,
       "content_ref": 1,
       "byte_length_utf8": 1
      },
      "missing_core": {},
      "partial": {
       "status": 8,
       "unresolved_reason": 8
      }
     }
    },
    {
     "id": "RC17",
     "name": "shortest_locator_quote_vs_min_quote_chars",
     "result": "fail",
     "blocking": false,
     "maps_to_upstream_acceptance": null,
     "detail": "shortest markdown quote = {'asset_id': 'ast-771-24', 'quote': 'CASE.md', 'chars': 7}; quotes below platform min_quote_chars=12: [('ast-771-24', 7)] (that threshold governs claim evidence, not asset locators - recorded as robustness risk, not a gate breach)",
     "evidence": {
      "quotes": [
       {
        "asset_id": "ast-771-01",
        "quote": "# 料仓卸料(Beverloo)+休止角双案例 —— TensorDEM 跨方法吸收线",
        "chars": 43
       },
       {
        "asset_id": "ast-771-20",
        "quote": "`src/tensordem/granular_dem.py`",
        "chars": 31
       },
       {
        "asset_id": "ast-771-21",
        "quote": "`examples/hopper_beverloo_case.py`",
        "chars": 34
       },
       {
        "asset_id": "ast-771-22",
        "quote": "`hopper_beverloo_report.py`",
        "chars": 27
       },
       {
        "asset_id": "ast-771-23",
        "quote": "outputs/*.json",
        "chars": 14
       },
       {
        "asset_id": "ast-771-24",
        "quote": "CASE.md",
        "chars": 7
       }
      ],
      "min_quote_chars": 12
     }
    },
    {
     "id": "RC18",
     "name": "figure_list_route_existence",
     "result": "pass",
     "blocking": false,
     "maps_to_upstream_acceptance": null,
     "detail": "upstream recorded list route GET /tensor/reports/771/figures -> HTTP 404; that list route present in platform OpenAPI = False (only /figures/{name} exists) -> list-route 404 is route-absence, per-figure 404 is the real evidence",
     "evidence": {
      "probe": {
       "list_route_status": 404,
       "list_route_in_openapi": false,
       "binary_status": {
        "fig1_beverloo_qbc.png": 404,
        "fig2_beverloo_linearity.png": 404,
        "fig3_rate_series.png": 404
       }
      }
     }
    }
   ],
   "findings": [
    {
     "id": "F1",
     "severity": "low",
     "blocking": false,
     "scope": "asset_manifest.json: 10 asset records",
     "statement": "asset records are not shape-uniform: status (8/10), unresolved_reason (8/10). The two resolvable assets carry no status/unresolved_reason while the eight unresolved ones do, so a downstream consumer that reads status on every asset breaks on exactly the two it most needs; the core keys themselves are complete.",
     "evidence": "per-key presence counts over 10 assets = {'asset_id': 10, 'kind': 10, 'role': 10, 'name': 10, 'resolvable': 10, 'resolution': 10, 'locators': 10, 'status': 8, 'unresolved_reason': 8, 'caption': 3, 'caption_equals_name': 3, 'values': 1, 'content_ref': 1, 'byte_length_utf8': 1}; core keys = ['asset_id', 'kind', 'role', 'name', 'resolvable', 'resolution', 'locators']",
     "remediation": "normalise every asset record to one key set (resolvable ones also carry status='resolved' plus a resolution text) before 02/03 consume the manifest."
    },
    {
     "id": "F2",
     "severity": "low",
     "blocking": false,
     "scope": "asset ast-771-24 locator",
     "statement": "shortest markdown locator is 7 chars (quote 'CASE.md'), below the platform min_quote_chars=12; it resolves here only because the token is unique in this 2143-char report. Reused as claim evidence at 03 it would be rejected by g5_source_locator_resolvable.",
     "evidence": "quotes ascending by length: [('ast-771-24', 7), ('ast-771-23', 14), ('ast-771-22', 27), ('ast-771-20', 31), ('ast-771-21', 34), ('ast-771-01', 43)]",
     "remediation": "for short file names quote a longer span (the surrounding clause) so the locator stays above the platform threshold."
    },
    {
     "id": "F3",
     "severity": "info",
     "blocking": false,
     "scope": "asset ast-771-01 (source_document)",
     "statement": "the source-document asset is anchored on a 43-char prefix (2.0% of the document); its 'resolvable: true' cannot be derived from the asset locator alone - document identity is carried by the manifest.source block instead.",
     "evidence": "locator quote = '# 料仓卸料(Beverloo)+休止角双案例 —— TensorDEM 跨方法吸收线' at chars 0..43, document chars = 2143",
     "remediation": "declare source-document assets with a whole-document locator (0..chars) and keep a short anchor only for display."
    },
    {
     "id": "F4",
     "severity": "info",
     "blocking": false,
     "scope": "figure_probe in upstream manifest",
     "statement": "upstream bundles a figures-list route 404 with the per-figure 404s; that list route does not exist in the platform OpenAPI, so the two are not the same kind of evidence (route absence vs missing bytes). The 'unresolved' verdict still stands on the per-figure probes.",
     "evidence": "list route status=404, route in OpenAPI=False, per-figure status={'fig1_beverloo_qbc.png': 404, 'fig2_beverloo_linearity.png': 404, 'fig3_rate_series.png': 404}",
     "remediation": "label route-absence probes as such or drop them from the evidence bundle."
    },
    {
     "id": "F5",
     "severity": "info",
     "blocking": false,
     "scope": "platform gate coverage of task_type=01 (not an upstream defect)",
     "statement": "the platform evidence gate resolves locators only inside `claims`; with claims=[] it reports g5 checked=0, so the asset locators are never resolved by the gate. This review is the only evidence-grade check of the 01 output.",
     "evidence": "store row for wp-771-01: g5_source_locator_resolvable ok=true with checked=0; this review re-resolved 12 locators (RC7/RC8).",
     "remediation": "extend g5 to walk asset locators when claims are empty, or make the 04 review a required gate for 01 on lane C."
    },
    {
     "id": "F6",
     "severity": "info",
     "blocking": false,
     "scope": "repository schema coverage for 01 outputs",
     "statement": "there is no general schema for the asset_manifest.json body; the only asset-manifest schema in the repo pins package_id const 'wp-448-01', so it cannot validate this package. Upstream 'schema_pass' is provable only at envelope level (RC3).",
     "evidence": "schemas/asset_manifest.v1.schema.json properties.package_id.const = 'wp-448-01'; schemas/ has no asset_manifest schema parameterised by report/package.",
     "remediation": "generalise the asset_manifest schema (package/report as pattern instead of const) so 01 outputs are machine-checkable across reports."
    }
   ],
   "verdict": "pass",
   "disposition": "pass",
   "verification": {
    "self_marked_verified": false,
    "note": "this review reports a disposition only; the verification level is computed by the platform gate. Nothing here marks any upstream claim as verified."
   },
   "checks_not_run": [
    {
     "check": "existence of the referenced external artifacts in the producing repo",
     "reason": "out of scope for a report-scoped review and no repo/network access in this worktree; 01 only claims registration inside the report store, which was probed directly"
    },
    {
     "check": "re-execution of the TensorDEM hopper/Beverloo case itself",
     "reason": "wp-771-01 is a registration task and asserts no numeric result, so there is nothing to re-run at this stage (numeric review belongs to a later work package)"
    },
    {
     "check": "platform gate re-run (g1..g7) end to end",
     "reason": "the gate is the platform's own computation over the submitted envelope; this review re-derives every gate input independently instead of invoking the gate"
    }
   ],
   "limitations": [
    "the producer's narrative report text was read for orientation only; no finding rests on it, and every quote/number here is re-derived from source bytes or record fields",
    "single-document scope: only report 771 and wp-771-01 were touched; no other report_id was read or written, so cross-package consistency claims are out of scope",
    "asset resolvability is judged within the report store (attachment/byte reachability); a file that exists only in the producing repo is correctly registered as unresolved here, which does not mean the file does not exist"
   ],
   "summary": {
    "checks_total": 18,
    "checks_pass": 16,
    "checks_fail": 2,
    "findings_total": 6,
    "findings_blocking": 0,
    "checks_failed_blocking": 0,
    "upstream_acceptance_recomputed": {
     "valid_json": {
      "checks": [
       "RC2"
      ],
      "result": "pass"
     },
     "schema_pass": {
      "checks": [
       "RC3"
      ],
      "result": "pass"
     },
     "source_hash_matches": {
      "checks": [
       "RC5"
      ],
      "result": "pass"
     },
     "source_locator_resolvable": {
      "checks": [
       "RC7",
       "RC8"
      ],
      "result": "pass"
     },
     "no_duplicate_ids": {
      "checks": [
       "RC10"
      ],
      "result": "pass"
     },
     "all_claims_have_evidence_or_explicit_unresolved_status": {
      "checks": [
       "RC12"
      ],
      "result": "pass"
     }
    }
   }
  }
 }
}
```
