# KF-RESULT wp-11156-01

工序 `01-asset-registration` · report_id `11156` · repo TensorKnowledge · lane C · status draft

## ① 本工序做了什么

对 report 11156（`DEM Parameter Auto-Calibration Framework: Bayesian Optimization + MCMC UQ`，scenario_key `p284w3-n05-dem-auto-calibration`）执行**资产登记**：把源 markdown 按字节钉住（sha256），
再把报告里可解析的资产（表格、材料预设、被引用的文件路径、量值陈述、发布锚、平台 record 携带的图元数据）逐条登记为
带**逐字定位器**的条目，共 **21** 条（resolved_in_source 9 /
referenced_unresolved 4 / declared_only 8）。

明确**没做**的事（契约 objective）：不做抽取（claims 为空数组）、不做报告类型分类（`classify_report_type=false`）、
不做任何验证结论（每条资产 `verification_status=not_performed`，verification 由平台门计算）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET /api/v1/tensor/reports/11156`（Bearer token），只取 `markdown` 字段；
   `register_assets_lib.fetch_report()` 内置 report_id 硬锁（记录 id 不等于 11156 直接拒绝产出）。
2. **钉字节**：`hashlib.sha256(markdown.encode('utf-8'))` → `sha256:4e34bdac8a446701f339014fec117feea5083ad4ef85543edae87ccb77806d77`，
   与契约声明 `sha256:4e34bdac8a446701f339014fec117feea5083ad4ef85543edae87ccb77806d77` **逐字符相等**；`chars=4478`（与契约 4478 一致），
   `bytes_utf8=4489`（多出的 11 字节来自第 86 行中文“发布锚”）。字节快照落 `source.md`，record 元数据快照落 `record_meta.json`。
3. **定位**：不手打引文。使用 markdown 行索引选择器（H1 / `table:` 表块 / `bullet:` 项目符号 / `token:` 子串 / `document:` 全文），
   每个 char_span 定位器做三重校验：`quote in markdown`、`markdown[start:end] == quote`、`count(quote) == 1`（唯一）。
4. **引用路径探针**：§6 列出的 4 条文件引用，逐条在本 worktree 做 `os.path.exists` 探针；
   不存在就登记 `referenced_unresolved` + `resolution_check={check,result}`，**不代上游补写路径**。
5. **record 图元数据**：`record.figures` 只有 name+caption，无 PNG 字节 → 登记 `declared_only`，
   `method=record_figures_index` / `source_field=record`，**不下载、不算图哈希、不声称看过图**。
6. **发布锚**：ledger/corpus sha256 与 mission/branch/commit 只作 `declared_only` 登记——被引用的字节不在本包范围内，
   **不重算、不确认**。
7. **不改上游**：只写 `docs/kf/wp-11156-01/`、`runs/wp-11156-01/`、`artifacts/wp-11156-01/`，
   只读 report_id=11156。

工具链：Python 3.11 + `scripts/kf/register_assets_lib.py`（复用库）+ jsonschema + pytest + matplotlib。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11156-01/asset_manifest.json` | 主产物，21 条资产 + 4 条观察 + integrity 块；`claims=[]` |
| `docs/kf/wp-11156-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims） |
| `docs/kf/wp-11156-01/locator_check.json` | 逐资产定位回读结果（quote/offset/occurrences） |
| `docs/kf/wp-11156-01/source.md` | 源 markdown 字节快照（哈希钉住，供离线复跑） |
| `docs/kf/wp-11156-01/record_meta.json` | 平台 record 元数据快照（title/figures/tags/mission_id…） |
| `runs/wp-11156-01/verification.json` | 自检结论（acceptance 逐项） |
| `docs/kf/wp-11156-01/asset_locator_map.png` | 图 1：21 条资产在 4478 字符里的定位分布（按 resolution 着色） |
| `scripts/kf/build_asset_manifest_wp11156_01.py` | 一键生成器（取源→哈希→定位→落盘） |
| `scripts/kf/fig_asset_locator_map_wp11156_01.py` | 图 1 生成（x 坐标全部取自 manifest） |
| `scripts/kf/render_report_wp11156_01.py` | 本报告渲染（数字与引文全部来自产物，零手抄） |
| `tests/test_kf_wp_11156_01.py` | 19 项验收测试（离线可跑） |

## ④ 证据定位表（资产 → 原文引文片段，均逐字取自 markdown）

| asset | kind | resolution | 行 | 引文片段（verbatim 前缀） |
|---|---|---|---|---|
| A01 | source_markdown | resolved_in_source | 1-86 | # DEM Parameter Auto-Calibration Framework |
| A02 | table | resolved_in_source | 17-21 | \| Benchmark \| Input Parameters \| Output \| |
| A03 | table | resolved_in_source | 60-67 | \| Criterion \| Target \| Status \| |
| A04 | parameter_preset | resolved_in_source | 54-54 | - **Glass beads**: mu in [0.1, 0.5], mu_r in [0.0, 0.08], e in [0.5, 0.9] |
| A05 | parameter_preset | resolved_in_source | 55-55 | - **Sand**: mu in [0.3, 0.8], mu_r in [0.02, 0.12], e in [0.1, 0.5] |
| A06 | parameter_preset | resolved_in_source | 56-56 | - **Gravel**: mu in [0.4, 0.8], mu_r in [0.05, 0.15], e in [0.1, 0.4] |
| A07 | referenced_path | referenced_unresolved | 78-78 | - src/tensordem/auto_calibration.py - Main calibration framework (forward solver, BO, MCMC, pipe |
| A08 | referenced_path | referenced_unresolved | 79-79 | - tests/test_auto_calibration.py - 30 pytest tests covering all components |
| A09 | referenced_path | referenced_unresolved | 80-80 | - artifacts/fig*.png - Result figures |
| A10 | referenced_path | referenced_unresolved | 81-81 | - runs/calibration_result.json - Calibration run results |
| A11 | reported_quantity | resolved_in_source | 44-44 | The BO framework converges to the optimum within 38 evaluations for a 2D quadratic test function |
| A12 | reported_quantity | resolved_in_source | 47-47 | With experimental repose angle data (25 degrees +/- 3 degrees), the MCMC posterior for mu shows: |
| A13 | reported_quantity | resolved_in_source | 67-67 | \| (f) pytest >= 15 all green \| >= 15 \| 30 tests pass \| |
| A14 | hash_anchor | declared_only | 86-86 | ledger sha256 `16685355b1c97e5a01daa492b9c1c05046b286b2b295773591dcd011a81861d0` |
| A15 | hash_anchor | declared_only | 86-86 | corpus sha256 `4f09e8caa017ce8c1a54170aae734f78f98073ff2cac4ef7fcd23a224a07add9` |
| A16 | publish_anchor | declared_only | 86-86 | mission 9437 / branch agent/m9437 · commit 89b3ec6f |
| A17 | figure_metadata | declared_only | record.figures#0 | 判据族大小分布（对数轴）：冗余集中在少数族上，长尾是单例独立判据 |
| A18 | figure_metadata | declared_only | record.figures#1 | 每新增节点的新增独立判据族 vs 判据实例数（plan_id 序） |
| A19 | figure_metadata | declared_only | record.figures#2 | 独立族 / 冗余族杀伤率分布，标题含 Mann-Whitney p 与均值差 |
| A20 | figure_metadata | declared_only | record.figures#3 | 三种变异体（数值/单位/符号）的杀伤-存活结构（检出包络） |
| A21 | figure_metadata | declared_only | record.figures#4 | 尺寸匹配补充检验：逐条判据杀伤率分布（横线为均值） |

定位总数：md 跨度定位器 **16** 条（唯一性违例 0、
逐字违例 0），record 级定位器 **5** 条（无 markdown 跨度，如实标注）。

**record 与 markdown 的分歧（登记、不解释）**

- **O1 (record_metadata_topic_mismatch)** All 5 figure captions in record.figures discuss criterion-family kill rates / mutants, i.e. a different subject than DEM parameter calibration. Flagged, cause NOT inferred (do_not_invent_missing_information).
- **O2 (information_gap_in_source)** §3.2 reports the MCMC posterior only qualitatively (no posterior mean, no CI numbers); §3.3/§4 numbers exist but posterior quantities do not. Registered as an explicit gap; nothing is filled in.
- **O3 (provenance_pointer_discrepancy)** Platform record mission_id=9416 while the markdown publish anchor reads 'mission 9437'. Both values registered verbatim; discrepancy left open.
- **O4 (unresolvable_scope)** None of the four §6 file references (A07-A10) exists in the TensorKnowledge worktree, so the assets are registered as text locators only; no code/byte level check was possible in this package.

## ⑤ 注意点与局限

1. **本包不产生知识**：`claims=[]` 是契约允许的完整结果；任何后续 claim 都必须由工序 03 从本 manifest 的定位器出发重建，且带引文。
2. **没有验证**：§4 验收表的 “Verified (38 evals) / 30 tests pass” 等字样只是**原文被引用**，不是本包复核的结论；
   本包没有执行 DEM 仿真、没有跑上游 pytest、没有重算任何物理量。
3. **§6 四条文件引用在本 worktree 全部不存在**（TensorKnowledge 不是生产该报告的 TensorDEM 侧检出）：
   资产只到“文本可定位”这一层，代码/字节级核对留给持有该仓的工作包。
4. **图元数据主题不符**：`record.figures` 的 5 条 caption 讲的是“判据族/杀伤率/变异体”，与 DEM 标定不是同一主题；
   本包只把 name+caption 逐字登记并打 `caption_topic_matches_report=false`，**没有推断原因**（可能是 record 挂错图，也可能是别的工序遗留，无权代判）。
5. **mission 指针不一致**：record `mission_id=9416`，markdown 发布锚写 “mission 9437”；两侧原文都已登记，分歧留给平台侧核对。
6. **正文信息缺口**：§3.2 对 MCMC 后验只作定性描述（无后验均值/CI 数字），§3.1 的 38 evals 只对应 2D 二次测试函数而非 DEM 正问题；
   这属于报告本身的证据强度问题，登记为观察 O2，不由本包补数。
7. **哈希同值 ≠ 内容正确**：sha256 相等只证明“这份字节就是契约指向的那份”，不证明报告结论成立。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 |
|---|---|
| valid_json | PASS |
| schema_pass | PASS |
| source_locator_resolvable | PASS |
| source_hash_matches | PASS |
| no_duplicate_ids | PASS |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS |

补充自检（本包自加，比 acceptance 更严）：

| 检查 | 结果 |
|---|---|
| report_id 锁：只读/只写 11156 | PASS |
| 无重复 asset_id（A01–A21 连续） | PASS |
| 每条 md 定位器 quote 逐字且唯一 | PASS（违例 0） |
| 每条资产均未标 verified | PASS（21/21 为 not_performed） |
| 未把 declared_only 锚升级为 confirmed | PASS（A14–A16 均 declared_only） |
| envelope 过 `schemas/kf_result.v1.schema.json` | PASS（pytest `schema_pass`） |

### ⑥bis 误差判定（显式回答“是否 <3%”）

**不适用 —— 本工序没有可对比的数值对象。** 本包只做资产登记（`objective.register_assets=true`，`classifies_report_type=false`），
不产生物理量、不执行 DEM 仿真、不复现 BO/MCMC 结果，因此不存在“计算值 vs 基准”的误差项，**无法也不应**回答 <3%。
原因记录：报告内的量值（38 evals、25±3 度、30 tests）只被**引用**为定位器（A11–A13），本包对它们零复核；
若后续工序（03 抽取 / 04 验证）要就这些量给出误差结论，须自带基准与复现命令，并在那时逐项判 <3%。
本包唯一可量化的自检是**定位器精确度**：quote 与源字节完全一致的比例 = 16/16（md 跨度定位器），哈希一致 = 1/1。

`repro_cmd`：

```text
TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 TENSOR_AGENT_USER=<user> TENSOR_AGENT_PASS=<pass> python3 scripts/kf/build_asset_manifest_wp11156_01.py && python3 scripts/kf/fig_asset_locator_map_wp11156_01.py && python3 scripts/kf/render_report_wp11156_01.py && python3 -m pytest tests/test_kf_wp_11156_01.py -q
```

---

*本报告的每个数字/引文均由 `scripts/kf/render_report_wp11156_01.py` 从
`asset_manifest.json` / `kf_result.json` / `verification.json` 程序化注入；唯一一个 json 代码块为结果信封原文。*

```json
{
 "package_id": "wp-11156-01",
 "task_type": "01-asset-registration",
 "report_id": "11156",
 "provenance": {
  "source_uri": "tensor://reports/11156",
  "source_field": "markdown",
  "source_hash": "sha256:4e34bdac8a446701f339014fec117feea5083ad4ef85543edae87ccb77806d77",
  "producer": "agent/m15691",
  "emitted_at": "2026-11-12T01:51:57+00:00",
  "notes": "01-asset-registration only: markdown fetched live, sha256 recomputed over UTF-8 bytes and matched against the contract hash; 21 assets registered with verbatim locators; figure metadata registered as declared-only; claims intentionally empty; nothing marked verified."
 },
 "outputs": {
  "asset_manifest.json": {
   "manifest_version": "1.0",
   "schema": "asset_manifest.v1",
   "package_id": "wp-11156-01",
   "task_type": "01-asset-registration",
   "report_id": "11156",
   "generated_at": "2026-11-12T01:51:57+00:00",
   "generated_by": "agent/m15691",
   "scope": {
    "registers_assets_only": true,
    "extracts_claims": false,
    "classifies_report_type": false,
    "marks_anything_verified": false,
    "reports_touched": [
     "11156"
    ]
   },
   "contract": {
    "source_uri": "tensor://reports/11156",
    "source_field": "markdown",
    "source_hash_declared": "sha256:4e34bdac8a446701f339014fec117feea5083ad4ef85543edae87ccb77806d77",
    "chars_declared": 4478,
    "title_declared": "DEM Parameter Auto-Calibration Framework: Bayesian Optimization + MCMC UQ",
    "scenario_key_declared": "p284w3-n05-dem-auto-calibration"
   },
   "source": {
    "uri": "tensor://reports/11156",
    "field": "markdown",
    "hash_alg": "sha256",
    "hash": "4e34bdac8a446701f339014fec117feea5083ad4ef85543edae87ccb77806d77",
    "hash_contract": "4e34bdac8a446701f339014fec117feea5083ad4ef85543edae87ccb77806d77",
    "hash_matches_contract": true,
    "hash_method": "sha256 over UTF-8 bytes of the markdown field",
    "retrieved_via": "GET /api/v1/tensor/reports/11156 (Bearer token)",
    "chars": 4478,
    "chars_matches_contract": true,
    "bytes_utf8": 4489,
    "title": "DEM Parameter Auto-Calibration Framework: Bayesian Optimization + MCMC UQ",
    "title_matches_contract": true,
    "scenario_key": "p284w3-n05-dem-auto-calibration",
    "platform_mission_id": 9416,
    "platform_status": "published",
    "platform_tags": [
     "DEM",
     "calibration",
     "bayesian-optimization",
     "MCMC",
     "uncertainty-quantification",
     "repose-angle",
     "shear-box",
     "compression"
    ],
    "line_count": 86,
    "heading_count": 13,
    "headings": [
     "# DEM Parameter Auto-Calibration Framework",
     "## 1. Physical Background",
     "## 2. Method",
     "### 2.1 Forward Problem",
     "### 2.2 Inverse Problem: Bayesian Optimization",
     "### 2.3 Uncertainty Quantification: MCMC",
     "## 3. Results",
     "### 3.1 Bayesian Optimization Convergence",
     "### 3.2 MCMC Posterior Distribution",
     "### 3.3 Material Presets",
     "## 4. Acceptance Criteria",
     "## 5. Limitations",
     "## 6. Files"
    ]
   },
   "counts": {
    "assets": 21,
    "by_kind": {
     "source_markdown": 1,
     "table": 2,
     "parameter_preset": 3,
     "referenced_path": 4,
     "reported_quantity": 3,
     "hash_anchor": 2,
     "publish_anchor": 1,
     "figure_metadata": 5
    },
    "by_resolution": {
     "resolved_in_source": 9,
     "referenced_unresolved": 4,
     "declared_only": 8
    },
    "resolved_in_source": 9,
    "referenced_unresolved": 4,
    "declared_only": 8,
    "claims": 0
   },
   "assets": [
    {
     "asset_id": "A01",
     "kind": "source_markdown",
     "label": "report 11156 markdown (hash-pinned source of record)",
     "section": "document",
     "resolution": "resolved_in_source",
     "verification_status": "not_performed",
     "locator": {
      "method": "document",
      "start_char": 0,
      "end_char": 4478,
      "start_line": 1,
      "end_line": 86,
      "quote": "# DEM Parameter Auto-Calibration Framework",
      "quote_is_first_line_only": true,
      "document_sha256": "4e34bdac8a446701f339014fec117feea5083ad4ef85543edae87ccb77806d77",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true,
      "note": "document-level locator; quote is only the H1 line for readability"
     },
     "note": "sha256 recomputed live over UTF-8 bytes; equals the contract-declared hash. Hash equality is a mechanical identity check only."
    },
    {
     "asset_id": "A02",
     "kind": "table",
     "label": "§2.1 forward-benchmark -> macroscopic-response mapping table",
     "section": "2.1 Forward Problem",
     "resolution": "resolved_in_source",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 952,
      "end_char": 1292,
      "start_line": 17,
      "end_line": 21,
      "quote": "| Benchmark | Input Parameters | Output |\n|-----------|-----------------|--------|\n| Angle of repose | mu, mu_r, e, kt/kn | Heap slope angle (degrees) |\n| Direct shear box | mu, mu_r, e, kt/kn | Internal friction angle phi (degrees), cohesion c (Pa) |\n| Uniaxial compression | mu, mu_r, e, kt/kn | Elastic modulus E (Pa), Poisson ratio nu |",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "table header + 3 data rows quoted verbatim; row count recorded in locator_stats",
     "locator_stats": {
      "data_rows": 3,
      "header": "| Benchmark | Input Parameters | Output |"
     }
    },
    {
     "asset_id": "A03",
     "kind": "table",
     "label": "§4 acceptance-criteria table (targets + status wording)",
     "section": "4. Acceptance Criteria",
     "resolution": "resolved_in_source",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 2944,
      "end_char": 3461,
      "start_line": 60,
      "end_line": 67,
      "quote": "| Criterion | Target | Status |\n|-----------|--------|--------|\n| (a) Repose angle error < 5 degrees | < 5 degrees | Framework supports this |\n| (b) Shear phi error < 3 degrees, c error < 10% | < 3 degrees, < 10% | Framework supports this |\n| (c) Compression E error < 10% | < 10% | Framework supports this |\n| (d) BO convergence < 100 evals | < 100 | Verified (38 evals for test case) |\n| (e) UQ 95% CI contains true value | Yes | Verified with synthetic data |\n| (f) pytest >= 15 all green | >= 15 | 30 tests pass |",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "targets are registered as *declared*; the reported status column is quoted, not re-verified by this package (verification belongs to the platform gate)",
     "locator_stats": {
      "data_rows": 6,
      "header": "| Criterion | Target | Status |"
     }
    },
    {
     "asset_id": "A04",
     "kind": "parameter_preset",
     "label": "material preset: glass beads (mu / mu_r / e ranges)",
     "section": "3.3 Material Presets",
     "resolution": "resolved_in_source",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 2704,
      "end_char": 2777,
      "start_line": 54,
      "end_line": 54,
      "quote": "- **Glass beads**: mu in [0.1, 0.5], mu_r in [0.0, 0.08], e in [0.5, 0.9]",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "verbatim bullet; the numeric ranges are the report's own values, not re-derived"
    },
    {
     "asset_id": "A05",
     "kind": "parameter_preset",
     "label": "material preset: sand (mu / mu_r / e ranges)",
     "section": "3.3 Material Presets",
     "resolution": "resolved_in_source",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 2778,
      "end_char": 2845,
      "start_line": 55,
      "end_line": 55,
      "quote": "- **Sand**: mu in [0.3, 0.8], mu_r in [0.02, 0.12], e in [0.1, 0.5]",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "verbatim bullet; the numeric ranges are the report's own values, not re-derived"
    },
    {
     "asset_id": "A06",
     "kind": "parameter_preset",
     "label": "material preset: gravel (mu / mu_r / e ranges)",
     "section": "3.3 Material Presets",
     "resolution": "resolved_in_source",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 2846,
      "end_char": 2915,
      "start_line": 56,
      "end_line": 56,
      "quote": "- **Gravel**: mu in [0.4, 0.8], mu_r in [0.05, 0.15], e in [0.1, 0.4]",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "verbatim bullet; the numeric ranges are the report's own values, not re-derived"
    },
    {
     "asset_id": "A07",
     "kind": "referenced_path",
     "label": "file reference: main calibration framework",
     "section": "6. Files",
     "resolution": "referenced_unresolved",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 3975,
      "end_char": 4076,
      "start_line": 78,
      "end_line": 78,
      "quote": "- src/tensordem/auto_calibration.py - Main calibration framework (forward solver, BO, MCMC, pipeline)",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "path text quoted verbatim from §6; byte payload NOT available in this package -> existence was probed only against this worktree and is reported as-is",
     "resolution_check": {
      "check": "worktree_probe:src/tensordem/auto_calibration.py",
      "result": "absent",
      "searched_root": "TensorKnowledge worktree (this repo)",
      "note": "report 11156 was produced in a TensorDEM-side worktree; the TensorKnowledge checkout is not expected to carry those bytes"
     }
    },
    {
     "asset_id": "A08",
     "kind": "referenced_path",
     "label": "file reference: 30-test pytest suite",
     "section": "6. Files",
     "resolution": "referenced_unresolved",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 4077,
      "end_char": 4151,
      "start_line": 79,
      "end_line": 79,
      "quote": "- tests/test_auto_calibration.py - 30 pytest tests covering all components",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "path text quoted verbatim from §6; byte payload NOT available in this package -> existence was probed only against this worktree and is reported as-is",
     "resolution_check": {
      "check": "worktree_probe:tests/test_auto_calibration.py",
      "result": "absent",
      "searched_root": "TensorKnowledge worktree (this repo)",
      "note": "report 11156 was produced in a TensorDEM-side worktree; the TensorKnowledge checkout is not expected to carry those bytes"
     }
    },
    {
     "asset_id": "A09",
     "kind": "referenced_path",
     "label": "file reference: result figures (glob, no concrete filenames)",
     "section": "6. Files",
     "resolution": "referenced_unresolved",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 4152,
      "end_char": 4189,
      "start_line": 80,
      "end_line": 80,
      "quote": "- artifacts/fig*.png - Result figures",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "path text quoted verbatim from §6; byte payload NOT available in this package -> existence was probed only against this worktree and is reported as-is",
     "resolution_check": {
      "check": "worktree_probe:artifacts/fig*.png",
      "result": "absent",
      "searched_root": "TensorKnowledge worktree (this repo)",
      "note": "report 11156 was produced in a TensorDEM-side worktree; the TensorKnowledge checkout is not expected to carry those bytes"
     }
    },
    {
     "asset_id": "A10",
     "kind": "referenced_path",
     "label": "file reference: calibration run results",
     "section": "6. Files",
     "resolution": "referenced_unresolved",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 4190,
      "end_char": 4246,
      "start_line": 81,
      "end_line": 81,
      "quote": "- runs/calibration_result.json - Calibration run results",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "path text quoted verbatim from §6; byte payload NOT available in this package -> existence was probed only against this worktree and is reported as-is",
     "resolution_check": {
      "check": "worktree_probe:runs/calibration_result.json",
      "result": "absent",
      "searched_root": "TensorKnowledge worktree (this repo)",
      "note": "report 11156 was produced in a TensorDEM-side worktree; the TensorKnowledge checkout is not expected to carry those bytes"
     }
    },
    {
     "asset_id": "A11",
     "kind": "reported_quantity",
     "label": "BO convergence: 38 evaluations, objective < 0.01 (2D quadratic test)",
     "section": "3.1 Bayesian Optimization Convergence",
     "resolution": "resolved_in_source",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 2248,
      "end_char": 2373,
      "start_line": 44,
      "end_line": 44,
      "quote": "The BO framework converges to the optimum within 38 evaluations for a 2D quadratic test function, achieving objective < 0.01.",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "declared numeric result; not reproduced here (no extraction, no verification)"
    },
    {
     "asset_id": "A12",
     "kind": "reported_quantity",
     "label": "MCMC input data: repose angle 25 deg +/- 3 deg",
     "section": "3.2 MCMC Posterior Distribution",
     "resolution": "resolved_in_source",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 2411,
      "end_char": 2507,
      "start_line": 47,
      "end_line": 47,
      "quote": "With experimental repose angle data (25 degrees +/- 3 degrees), the MCMC posterior for mu shows:",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "declared experimental datum; posterior mean/CI are described only qualitatively in §3.2 (no numbers) -> see observation O2"
    },
    {
     "asset_id": "A13",
     "kind": "reported_quantity",
     "label": "pytest count: 30 tests",
     "section": "4. Acceptance Criteria",
     "resolution": "resolved_in_source",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 3407,
      "end_char": 3461,
      "start_line": 67,
      "end_line": 67,
      "quote": "| (f) pytest >= 15 all green | >= 15 | 30 tests pass |",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "declared test count (acceptance row (f)); suite not executed by this package"
    },
    {
     "asset_id": "A14",
     "kind": "hash_anchor",
     "label": "publish anchor: ledger sha256 (declared)",
     "section": "publish anchor line",
     "resolution": "declared_only",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 4259,
      "end_char": 4339,
      "start_line": 86,
      "end_line": 86,
      "quote": "ledger sha256 `16685355b1c97e5a01daa492b9c1c05046b286b2b295773591dcd011a81861d0`",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "anchor is quoted verbatim but the referenced ledger bytes are outside this package -> hash NOT recomputed, NOT confirmed"
    },
    {
     "asset_id": "A15",
     "kind": "hash_anchor",
     "label": "publish anchor: corpus sha256 (declared)",
     "section": "publish anchor line",
     "resolution": "declared_only",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 4342,
      "end_char": 4422,
      "start_line": 86,
      "end_line": 86,
      "quote": "corpus sha256 `4f09e8caa017ce8c1a54170aae734f78f98073ff2cac4ef7fcd23a224a07add9`",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "same status as A14: declared only, bytes unavailable -> hash NOT recomputed, NOT confirmed"
    },
    {
     "asset_id": "A16",
     "kind": "publish_anchor",
     "label": "publish anchor: mission / branch / commit",
     "section": "publish anchor line",
     "resolution": "declared_only",
     "verification_status": "not_performed",
     "locator": {
      "method": "char_span",
      "start_char": 4425,
      "end_char": 4476,
      "start_line": 86,
      "end_line": 86,
      "quote": "mission 9437 / branch agent/m9437 · commit 89b3ec6f",
      "unique": true,
      "occurrences": 1,
      "quote_verbatim": true
     },
     "note": "provenance pointers declared by the report; NOT resolved against any git repository by this package"
    },
    {
     "asset_id": "A17",
     "kind": "figure_metadata",
     "label": "record figure metadata: fig1_family_size.png",
     "section": "record.figures",
     "resolution": "declared_only",
     "verification_status": "not_performed",
     "locator": {
      "method": "record_figures_index",
      "source_field": "record",
      "record_index": 0,
      "name": "fig1_family_size.png",
      "quote": "判据族大小分布（对数轴）：冗余集中在少数族上，长尾是单例独立判据",
      "resolvable_in_markdown": false,
      "start_char": null,
      "end_char": null,
      "start_line": null,
      "end_line": null,
      "unique": true,
      "occurrences": 1,
      "note": "name/caption live in record.figures; the PNG payload is not carried by the record, so no image bytes and no image hash are claimed"
     },
     "note": "declared only: no payload, no hash, no visual check performed by this package",
     "caption": "判据族大小分布（对数轴）：冗余集中在少数族上，长尾是单例独立判据",
     "caption_topic_matches_report": false
    },
    {
     "asset_id": "A18",
     "kind": "figure_metadata",
     "label": "record figure metadata: fig2_marginal_series.png",
     "section": "record.figures",
     "resolution": "declared_only",
     "verification_status": "not_performed",
     "locator": {
      "method": "record_figures_index",
      "source_field": "record",
      "record_index": 1,
      "name": "fig2_marginal_series.png",
      "quote": "每新增节点的新增独立判据族 vs 判据实例数（plan_id 序）",
      "resolvable_in_markdown": false,
      "start_char": null,
      "end_char": null,
      "start_line": null,
      "end_line": null,
      "unique": true,
      "occurrences": 1,
      "note": "name/caption live in record.figures; the PNG payload is not carried by the record, so no image bytes and no image hash are claimed"
     },
     "note": "declared only: no payload, no hash, no visual check performed by this package",
     "caption": "每新增节点的新增独立判据族 vs 判据实例数（plan_id 序）",
     "caption_topic_matches_report": false
    },
    {
     "asset_id": "A19",
     "kind": "figure_metadata",
     "label": "record figure metadata: fig3_kill_rates.png",
     "section": "record.figures",
     "resolution": "declared_only",
     "verification_status": "not_performed",
     "locator": {
      "method": "record_figures_index",
      "source_field": "record",
      "record_index": 2,
      "name": "fig3_kill_rates.png",
      "quote": "独立族 / 冗余族杀伤率分布，标题含 Mann-Whitney p 与均值差",
      "resolvable_in_markdown": false,
      "start_char": null,
      "end_char": null,
      "start_line": null,
      "end_line": null,
      "unique": true,
      "occurrences": 1,
      "note": "name/caption live in record.figures; the PNG payload is not carried by the record, so no image bytes and no image hash are claimed"
     },
     "note": "declared only: no payload, no hash, no visual check performed by this package",
     "caption": "独立族 / 冗余族杀伤率分布，标题含 Mann-Whitney p 与均值差",
     "caption_topic_matches_report": false
    },
    {
     "asset_id": "A20",
     "kind": "figure_metadata",
     "label": "record figure metadata: fig4_mutant_kinds.png",
     "section": "record.figures",
     "resolution": "declared_only",
     "verification_status": "not_performed",
     "locator": {
      "method": "record_figures_index",
      "source_field": "record",
      "record_index": 3,
      "name": "fig4_mutant_kinds.png",
      "quote": "三种变异体（数值/单位/符号）的杀伤-存活结构（检出包络）",
      "resolvable_in_markdown": false,
      "start_char": null,
      "end_char": null,
      "start_line": null,
      "end_line": null,
      "unique": true,
      "occurrences": 1,
      "note": "name/caption live in record.figures; the PNG payload is not carried by the record, so no image bytes and no image hash are claimed"
     },
     "note": "declared only: no payload, no hash, no visual check performed by this package",
     "caption": "三种变异体（数值/单位/符号）的杀伤-存活结构（检出包络）",
     "caption_topic_matches_report": false
    },
    {
     "asset_id": "A21",
     "kind": "figure_metadata",
     "label": "record figure metadata: fig5_per_criterion.png",
     "section": "record.figures",
     "resolution": "declared_only",
     "verification_status": "not_performed",
     "locator": {
      "method": "record_figures_index",
      "source_field": "record",
      "record_index": 4,
      "name": "fig5_per_criterion.png",
      "quote": "尺寸匹配补充检验：逐条判据杀伤率分布（横线为均值）",
      "resolvable_in_markdown": false,
      "start_char": null,
      "end_char": null,
      "start_line": null,
      "end_line": null,
      "unique": true,
      "occurrences": 1,
      "note": "name/caption live in record.figures; the PNG payload is not carried by the record, so no image bytes and no image hash are claimed"
     },
     "note": "declared only: no payload, no hash, no visual check performed by this package",
     "caption": "尺寸匹配补充检验：逐条判据杀伤率分布（横线为均值）",
     "caption_topic_matches_report": false
    }
   ],
   "observations": [
    {
     "observation_id": "O1",
     "kind": "record_metadata_topic_mismatch",
     "statement": "All 5 figure captions in record.figures discuss criterion-family kill rates / mutants, i.e. a different subject than DEM parameter calibration. Flagged, cause NOT inferred (do_not_invent_missing_information).",
     "evidence": {
      "record_field": "figures[].caption",
      "quotes": [
       "判据族大小分布（对数轴）：冗余集中在少数族上，长尾是单例独立判据",
       "每新增节点的新增独立判据族 vs 判据实例数（plan_id 序）",
       "独立族 / 冗余族杀伤率分布，标题含 Mann-Whitney p 与均值差",
       "三种变异体（数值/单位/符号）的杀伤-存活结构（检出包络）",
       "尺寸匹配补充检验：逐条判据杀伤率分布（横线为均值）"
      ]
     }
    },
    {
     "observation_id": "O2",
     "kind": "information_gap_in_source",
     "statement": "§3.2 reports the MCMC posterior only qualitatively (no posterior mean, no CI numbers); §3.3/§4 numbers exist but posterior quantities do not. Registered as an explicit gap; nothing is filled in.",
     "evidence": {
      "quote": "- Posterior mean calibrated from prior",
      "note": "quoted verbatim from §3.2"
     }
    },
    {
     "observation_id": "O3",
     "kind": "provenance_pointer_discrepancy",
     "statement": "Platform record mission_id=9416 while the markdown publish anchor reads 'mission 9437'. Both values registered verbatim; discrepancy left open.",
     "evidence": {
      "record_field": "mission_id",
      "record_value": 9416,
      "markdown_quote": "mission 9437 / branch agent/m9437",
      "markdown_quote_commit": "commit 89b3ec6f"
     }
    },
    {
     "observation_id": "O4",
     "kind": "unresolvable_scope",
     "statement": "None of the four §6 file references (A07-A10) exists in the TensorKnowledge worktree, so the assets are registered as text locators only; no code/byte level check was possible in this package.",
     "evidence": {
      "asset_ids": [
       "A07",
       "A08",
       "A09",
       "A10"
      ],
      "probes": [
       {
        "check": "worktree_probe:src/tensordem/auto_calibration.py",
        "result": "absent",
        "searched_root": "TensorKnowledge worktree (this repo)",
        "note": "report 11156 was produced in a TensorDEM-side worktree; the TensorKnowledge checkout is not expected to carry those bytes"
       },
       {
        "check": "worktree_probe:tests/test_auto_calibration.py",
        "result": "absent",
        "searched_root": "TensorKnowledge worktree (this repo)",
        "note": "report 11156 was produced in a TensorDEM-side worktree; the TensorKnowledge checkout is not expected to carry those bytes"
       },
       {
        "check": "worktree_probe:artifacts/fig*.png",
        "result": "absent",
        "searched_root": "TensorKnowledge worktree (this repo)",
        "note": "report 11156 was produced in a TensorDEM-side worktree; the TensorKnowledge checkout is not expected to carry those bytes"
       },
       {
        "check": "worktree_probe:runs/calibration_result.json",
        "result": "absent",
        "searched_root": "TensorKnowledge worktree (this repo)",
        "note": "report 11156 was produced in a TensorDEM-side worktree; the TensorKnowledge checkout is not expected to carry those bytes"
       }
      ]
     }
    }
   ],
   "claims": [],
   "claims_note": "intentionally empty: package objective is asset registration only; no claim is generated, none is marked verified (verification stays with the platform gate)",
   "integrity": {
    "hash_recomputed_locally": true,
    "hash_matches_contract": true,
    "quote_uniqueness": "checked per char_span locator (count==1)",
    "md_span_locators": 16,
    "record_locators": 5,
    "quote_uniqueness_violations": [],
    "quote_verbatim_violations": [],
    "duplicate_asset_ids": [],
    "all_claims_have_evidence_or_unresolved_status": true
   }
  }
 },
 "claims": []
}
```
