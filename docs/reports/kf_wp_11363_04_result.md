# KF-RESULT wp-11363-04

**工作包** `wp-11363-04` ｜ **工序** `04-independent-review` ｜ **审核对象** `wp-11363-01`（`01-asset-registration`） ｜ **report_id** `11363` ｜ **lane** C ｜ **状态** in-review

**源** `tensor://reports/11363` · field=`markdown` · sha256=`sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23`（6902 chars / 9618 字节 UTF-8 / 124 行；本工序独立重算，与契约哈希一致）

**报告标题** ESD 节能装置收益评估成熟化（p228w1-N09）：分项+能量上界门+自航点耦合

**审核裁定** `needs-fix` —— 阻塞项 F3；非阻塞项 F4, F1, F5, F2。本工序**不**把任何结论标成 verified（verification 由平台门计算）。

## ① 本工序做了什么

对 report_id=11363 的 `01-asset-registration` 包做**独立红队审核**：不看生产者的解释与自检，只用两份主证据——(a) 平台 `GET /tensor/reports/11363` 的 `markdown` 原文（独立重算 sha256），(b) 被审包的两份产物 `kf_result.json` / `asset_manifest.json`——把包里的每一个可验证断言**从原始字节重算一遍**，判 pass / needs-fix / fail。

重算覆盖：源哈希与字符/字节/行数、25 条定位（子串命中 + 偏移回读 + 行号 + 全局出现次数 + token 在引文内）、计数直方图与 id 完整性、bundle 清单算术（6 个具名文件 + 4 张 png = 10）、4 张图的字节端点重新探活并重算 sha256、「unresolved」负向声明的反查、信封与清单的 schema 校验、以及 claims/verified 的越界检查。

结论：登记实质**站得住**（25/25 定位逐字命中，源哈希与契约一致，负向声明全部反查成立）；但**有 1 项阻塞**：信封 `kf_result.json` 的顶层 `claims` 键违反 `schemas/kf_result.v1.schema.json` 的 `additionalProperties=false`，因此被审包自报的 `schema_pass=true` **不可复现**（全产线普遍同病：83/118 个包同形，仅 7 个通过该 schema）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源（唯一信道）**：`GET $TENSOR_API_BASE/tensor/reports/11363`，只取 `markdown`；对 UTF-8 字节算 sha256，与契约 `sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23` 比对（不一致即停，不写产物）。快照落 `runs/m19810/source_11363.md`。
2. **信道隔离**：本包只读 report 11363；`C12` 扫全部产物里的 report-id 型 token，除 11363 外无其它 report_id。生产者自检 `report_selfcheck.json` 被**排除**在证据之外（`C16`）。
3. **定位重解（25 条）**：对每条资产做四项独立校验——`markdown[start:end] == quote`、`line == 1 + count('\n', 0, start)`、`markdown.count(quote) == count_occurrences`、`token in quote`；失败 0 条。
4. **字节端点重探**：4 张图各 `GET /tensor/reports/11363/figures/<name>`，重算 `http_status`/`bytes`/`payload sha256`/PNG magic，与包内 `platform_attachment_probes` 逐字段比对（命中 4/4，合计 373525 字节）；`/figures` 列表端点 404 亦复现。
5. **schema 与越界**：`jsonschema` 校验信封（draft 2020-12）与清单（draft-07）；扫 `claims`/`verified` 语义，确认 `claims==[]`、能力声明为 `declared_reference_only` 且写明「does NOT verify」。
6. **变异自检**：`tests/test_kf_wp11363_04.py` 12 个不变式测试，含 2 个变异用例（挪偏移、改引文必须被判红），证明检查真的会红；其中一条直接断言**被审包信封信封会被 canonical schema 拒绝**，让阻塞项 F3 可复现而不是靠叙述。
7. **工具链**：`runs/m19810/fetch_source.py` → `verify_wp11363_04.py` → `build_review_report.py` → 本渲染器；报告正文所有数字与引文由脚本注入（零手抄）。

## ③ 产出物清单（输出文件名 → 要点）

| 产出 | 路径 | 要点 |
|---|---|---|
| `review_report.json`（契约声明输出） | `docs/kf/wp-11363-04/review_report.json` | 裁定 `needs-fix`；17 项检查；5 条 finding（阻塞 1）；9 条证据定位；verified_marks=0 |
| `review_events.json` | `docs/kf/wp-11363-04/review_events.json` | 审核事件账本（取源 → 逐项检查 → 提 finding → 裁定 → 无 verified 标记） |
| 结果信封 | `docs/kf/wp-11363-04/kf_result.json` | package_id/task_type/report_id/provenance/outputs；本页唯一 json 块 |
| 检查账本 | `docs/kf/wp-11363-04/check_ledger.json` | 16 项检查的完整明细（含 25 条定位逐条结果、4 图重探字段、schema 覆盖率） |
| 图 1 | `docs/kf/wp-11363-04/figures/fig1_review_evidence.png` | 三联：F3 产线覆盖率 / 被审清单 25 资产状态 / 报告 §③ 组合 vs Σ 自洽散点 |
| 源快照 | `runs/m19810/source_11363.md` | markdown 原样字节（9618 B），离线复跑用 |
| 脚本 | `runs/m19810/{fetch_source,verify_wp11363_04,build_review_report}.py` | 一键复跑 |
| 测试 | `tests/test_kf_wp11363_04.py` | 12 个不变式 + 2 个变异用例 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

每条引文由脚本在源 markdown 中逐字匹配并重算字符区间与行号（`C3`/测试 `test_review_evidence_locators_resolve` 双重把关）。

| # | 用于 | 行 | 字符区间 | 原文引文（逐字） |
|---|---|---|---|---|
| Q1 | reviewed asset r11363:ref:upstream-resistance (upstream dependency: R_T from the resistance endpoint) | 15 | [722, 892) | `几何先验全通过：Cb 与 ∇/(L·B·T) 偏差 <0.02，L/B∈[4,11]、B/T∈[1.8,6]、D/T∈[0.35,0.90]、P/D∈[0.5,1.6]、Ae/Ao∈[0.3,1.2]；任一越界即拒绝（API 422），不外推。R_T 由阻力端点同源 Holtrop-1984 核注入（ESD 模块不重复算阻力，避免双源）。` |
| Q2 | finding F2: the §③ combined table's own data pointer, cited at line 44 outside the audit chain | 44 | [2483, 2556) | `**组合节能与 Σ 分项（节选：全 4 装置 + 两个代表性双装置；全表见 artifacts/esd/combined_table.csv）**` |
| Q3 | figure registration: 4 embedded figures declared in §④; live byte probe in check C7 | 87 | [5056, 5117) | `- 图 1 `fig1_per_device_savings.png`：3 船型 × 4 装置分项节能柱状图（数值标注）。` |
| Q4 | reviewed asset r11363:ref:09 + bundle_consistency (6 named files + 4 png = 10) | 119 | [6383, 6530) | `- 工件：`artifacts/esd/`（benchmark_results.json、golden_regression.json、per_device_table.csv、combined_table.csv、report_tables.md、4 张 png、manifest.json）` |
| Q5 | finding F4: the '10 文件' count that bundle_consistency.declared_in_manifest_line holds (line 120) | 120 | [6531, 6579) | `- 清单 sha256：`artifacts/esd/manifest.json`（10 文件）` |
| Q6 | reviewed assets r11363:ref:12..ref:16; check C17 re-probes the negative resolution claim | 122 | [6639, 6779) | `- 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_api.py`、`test_esd_regression.py`）` |
| Q7 | reviewed asset r11363:ref:18/ref:19: capability declaration registered as declared_reference_only, NOT verified (check C11) | 124 | [6820, 6901) | `- 能力：`propulsion.esd_energy_saving = REAL`（`artifacts/esd/capability_delta.json`）` |
| Q8 | informational only: the 45-case gate is a domain claim of the report, outside 01's registration scope | 70 | [4461, 4541) | `全网格 45 例（3 船 × 15 组合）：能量上界门**全部 PASS**，最大交互余量 1.42 个百分点，最大 Δn/n = 2.90%（判据 <5%）。` |
| Q9 | informational only: literature benchmark summary; no claim-grade endorsement is given by this review | 83 | [4990, 5044) | `max_rel_error = 9.33%（<15% 判据），mean_rel_error = 4.13%。` |

补充：源哈希/字符数不是 markdown 里的字符串，而是对原文**字节**独立重算的结果 （`sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23`，6902 chars / 9618 B / 124 行）。

## ⑤ 注意点与局限（含 finding 分级）

### 审核发现

| id | 严重度 | 阻塞 | 标题 |
|---|---|---|---|
| F3 | high | 是 | envelope kf_result.json fails the canonical schema: top-level 'claims' is an additional property (additionalProperties=false) — the declared schema_pass is not reproducible with schemas/kf_result.v1.schema.json |
| F1 | medium | 否 | manifest.observations contradicts manifest.platform_attachment_probes (figure byte status/hash) |
| F2 | low | 否 | artefacts cited outside the audit-chain line are registered only implicitly (no per-file asset row, no further_occurrences entry) |
| F4 | low | 否 | bundle_consistency.declared_in_manifest_line holds a file COUNT (10), not a line number |
| F5 | low | 否 | 'verified' tokens in the package are quote-resolution flags (quote_verified / all_verified), which a naive scanner can misread as claim verification |

**F3（high，阻塞）** envelope kf_result.json fails the canonical schema: top-level 'claims' is an additional property (additionalProperties=false) — the declared schema_pass is not reproducible with schemas/kf_result.v1.schema.json

- 影响范围：lane-wide contract drift, not a defect unique to this package: 83/118 packages under docs/kf/*/kf_result.json carry the same top-level 'claims' key and only 7/118 validate. Consequence for 01: its acceptance item schema_pass=true (report_selfcheck.json) cannot be reproduced with the committed canonical schema; the review therefore records schema_pass as NOT CONFIRMED. Remediation is a schema/convention decision (add 'claims' to the canonical root, or move it into outputs.claims) and belongs to the lane owner, not to package 01.
- 复现：`python3 -c "import json,jsonschema;d=json.load(open('docs/kf/wp-11363-01/kf_result.json'));jsonschema.validate(d,json.load(open('schemas/kf_result.v1.schema.json')))"`

**F1（medium，非阻塞）** manifest.observations contradicts manifest.platform_attachment_probes (figure byte status/hash)

- 影响范围：narrative observation field only; the numeric probe block is correct, so no asset hash or asset count is wrong. Downstream consumers that read observations instead of probes would wrongly conclude the figure bytes are unavailable.
- 复现：`python3 runs/m19810/verify_wp11363_04.py (C8) — re-probes the four figure endpoints and compares http_status/bytes/sha256 with the manifest probe block`

**F2（low，非阻塞）** artefacts cited outside the audit-chain line are registered only implicitly (no per-file asset row, no further_occurrences entry)

- 影响范围：registration granularity only; the citation is still locatable verbatim inside the directory quote at line 119, so no citation is lost or mis-attributed
- 复现：`python3 runs/m19810/verify_wp11363_04.py (C13)`

**F4（low，非阻塞）** bundle_consistency.declared_in_manifest_line holds a file COUNT (10), not a line number

- 影响范围：naming/ambiguity only; the arithmetic (6 named files + 4 png = 10) is correct and matches the report at line 120, so no count is misstated
- 复现：`python3 runs/m19810/verify_wp11363_04.py (C6) — resolves the field as a line index and finds the '10 文件' count phrase instead of a line reference`

**F5（low，非阻塞）** 'verified' tokens in the package are quote-resolution flags (quote_verified / all_verified), which a naive scanner can misread as claim verification

- 影响范围：no claim is marked verified in the substantive sense: claims==[] and the capability declaration is declared_reference_only with a 'does NOT verify' reason. This note is about scanner ambiguity, not about a false verification claim
- 复现：`python3 runs/m19810/verify_wp11363_04.py (C11) — collects every key containing 'verified'`

### 局限（如实）

- Review is document-level: the upstream artefact bytes (artifacts/esd/*, ship-performance-platform sources) are outside the delivery worktree and are therefore reviewed as references, not as content.
- Live re-probe of the 4 figure endpoints was performed once (single time point); a payload swap after this review would invalidate the recorded payload_sha256 values.
- The platform work-package registry is not exposed (404), so upstream_packages_completed stays unknown_not_run instead of being marked passed.
- No claim-grade verification is performed: verification is computed by the platform gate.

### 未跑/未确认的检查（记 unknown，不记 pass）

- upstream_packages_completed (C15): no registry route, upstream packages for 11363 absent from the worktree
- byte-level verification of the 10-file artifacts/esd bundle and of the ship-performance-platform source files: outside the delivery worktree by construction (registered as unresolved by 01)
- the report's full 45-combination grid (only the 21 printed rows are recomputable from the markdown text)

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | kf_result.json / asset_manifest.json / review_report.json all parse via json.loads (checks C9 ran on the parsed documents); reviewed envelope and manifest re-parsed here |
| `schema_pass` | ❌ | manifest validates against schemas/asset_manifest_wp11363_01.schema.json, but the envelope kf_result.json is REJECTED by schemas/kf_result.v1.schema.json: top-level 'claims' is an additional property (additionalProperties=false). See finding F3. The package's own schema_pass=true is therefore not reproducible -> NOT CONFIRMED. |
| `reviewer_independent` | ✅（含披露） | context = live report markdown (sha256 sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23) + the two reviewed artefacts only; the producer's self-check report_selfcheck.json is excluded from evidence. Disclosure: docs/reports/kf_wp11363_01_result.md was opened for its first 40 lines to copy the house report layout; none of its assertions is used as evidence here (figure status/bytes/sha256 come from this package's own live re-probe, check C7). |
| `upstream_packages_completed` | ⬜ 未确认 | no platform route enumerates work packages per report (8 probed paths: 404) and the delivery worktree holds only wp-11363-01 for report 11363 (wp-11363-02/-03 absent). Pipeline completeness is therefore NOT confirmed here rather than assumed true. |

**honest-FAIL**：`schema_pass` 判 ❌ —— 被审包 `wp-11363-01` 的 `kf_result.json` 顶层带 `claims`，在 `schemas/kf_result.v1.schema.json`（`additionalProperties=false`）下被拒（83/118 个同类包同样被拒，仅 7 个通过），因此其自报 `schema_pass=true` 不可复现；这是**产线级契约漂移**，不是本包的孤立错误，修法属 lane owner（把 `claims` 挪进 `outputs.claims`，或扩充 canonical schema）。`upstream_packages_completed` 判 ⬜ —— 平台无按 report 枚举工作包的路由（8 条候选路径全 404），工作树内只有 wp-11363-01，`wp-11363-02/-03` 不存在，故**不予假定为真**。

被审包内部质量的对账（informational，非本工序验收项）：`C14` 用报告 §③ 的 12 行分项重算 21 行组合——Σ 与印刷值最大偏差 0.01 个百分点（2 位小数舍入量级），全部组合 ≤ Σ 成立，最大 Δn/n=2.9% < 5%；文献相对误差**均值**由 2 位小数反算得 4.13%（报告值 max 9.33%/mean 4.13%，差异 ≤0.02pp，源于报告用未舍入值算误差）。

## 复跑

```bash
cd <worktree> && python3 runs/m19810/fetch_source.py && python3 runs/m19810/verify_wp11363_04.py && python3 runs/m19810/build_review_report.py && python3 -m pytest tests/test_kf_wp11363_04.py -q
```

## KF-RESULT wp-11363-04

```json
{
 "package_id": "wp-11363-04",
 "task_type": "04-independent-review",
 "contract_version": "1.0",
 "report_id": "11363",
 "provenance": {
  "source_uri": "tensor://reports/11363",
  "source_field": "markdown",
  "source_hash": "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23",
  "source_hash_matches": true,
  "title": "ESD 节能装置收益评估成熟化（p228w1-N09）：分项+能量上界门+自航点耦合",
  "scenario_key": "p228w1-N09",
  "chars": 6902
 },
 "outputs": {
  "review_report.json": {
   "review_report_version": "1.0",
   "package_id": "wp-11363-04",
   "task_type": "04-independent-review",
   "report_id": "11363",
   "reviewer_role": "red-team-reviewer",
   "reviewed_package": {
    "package_id": "wp-11363-01",
    "task_type": "01-asset-registration",
    "artefact_hashes": {
     "kf_result.json": "sha256:3347e4c40d00a416584f4ea879b46ebc5c4f6821ab353347a27baa2b4743f41a",
     "asset_manifest.json": "sha256:a0c199c40dbcd9bee70dba7d086279dafcf7395e956a3f7f306c60fb2b88f711",
     "report_selfcheck.json": "sha256:ad4ddefa7400ad2bd52301a1e0f61fec3fefa11132751dedaf34d2a9a39a8fc6"
    }
   },
   "verdict": "needs-fix",
   "verdict_reason": "1 blocking finding (F3: the envelope fails the canonical schema, so the reviewed package's schema_pass cannot be reproduced) + 4 non-blocking findings (F1 observation/probe contradiction, F2 registration granularity, F4 ambiguous bundle_consistency field, F5 'verified' token ambiguity). The registration substance itself holds: source hash, char/byte/line counts, all 25 verbatim locators, counts, id integrity and the negative (unresolved) claims were independently recomputed and confirmed.",
   "blocking_findings": [
    "F3"
   ],
   "non_blocking_findings": [
    "F4",
    "F1",
    "F5",
    "F2"
   ],
   "acceptance": {
    "valid_json": {
     "status": "pass",
     "detail": "kf_result.json / asset_manifest.json / review_report.json all parse via json.loads (checks C9 ran on the parsed documents); reviewed envelope and manifest re-parsed here"
    },
    "schema_pass": {
     "status": "fail",
     "detail": "manifest validates against schemas/asset_manifest_wp11363_01.schema.json, but the envelope kf_result.json is REJECTED by schemas/kf_result.v1.schema.json: top-level 'claims' is an additional property (additionalProperties=false). See finding F3. The package's own schema_pass=true is therefore not reproducible -> NOT CONFIRMED."
    },
    "reviewer_independent": {
     "status": "pass_with_disclosure",
     "detail": "context = live report markdown (sha256 sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23) + the two reviewed artefacts only; the producer's self-check report_selfcheck.json is excluded from evidence. Disclosure: docs/reports/kf_wp11363_01_result.md was opened for its first 40 lines to copy the house report layout; none of its assertions is used as evidence here (figure status/bytes/sha256 come from this package's own live re-probe, check C7)."
    },
    "upstream_packages_completed": {
     "status": "unknown_not_run",
     "detail": "no platform route enumerates work packages per report (8 probed paths: 404) and the delivery worktree holds only wp-11363-01 for report 11363 (wp-11363-02/-03 absent). Pipeline completeness is therefore NOT confirmed here rather than assumed true."
    }
   },
   "independence": {
    "context_used": [
     "live GET /api/v1/tensor/reports/11363 -> markdown, sha256 sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23, 6902 chars / 9618 bytes / 124 lines",
     "docs/kf/wp-11363-01/asset_manifest.json (sha256 sha256:a0c199c40dbcd9bee70dba7d086279dafcf7395e956a3f7f306c60fb2b88f711)",
     "docs/kf/wp-11363-01/kf_result.json (sha256 sha256:3347e4c40d00a416584f4ea879b46ebc5c4f6821ab353347a27baa2b4743f41a)",
     "schemas/kf_result.v1.schema.json + schemas/asset_manifest_wp11363_01.schema.json (validation only)"
    ],
    "excluded": [
     "docs/kf/wp-11363-01/report_selfcheck.json — the producer's own self-check; never used as evidence",
     "the producer's task prompt / any producer narrative or explanation of the results",
     "all other report_ids (this package reads and writes report 11363 only)"
    ],
    "limitations": [
     "Review is document-level: the upstream artefact bytes (artifacts/esd/*, ship-performance-platform sources) are outside the delivery worktree and are therefore reviewed as references, not as content.",
     "Live re-probe of the 4 figure endpoints was performed once (single time point); a payload swap after this review would invalidate the recorded payload_sha256 values.",
     "The platform work-package registry is not exposed (404), so upstream_packages_completed stays unknown_not_run instead of being marked passed.",
     "No claim-grade verification is performed: verification is computed by the platform gate."
    ]
   },
   "checks": {
    "C1_source_identity": {
     "status": "pass",
     "detail": "live recompute vs manifest.source vs contract: hash=sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23 chars=6902 bytes=9618 lines=124"
    },
    "C2_report_identity": {
     "status": "pass",
     "detail": "live record title/scenario == manifest.record_fields; package_id/task_type/report_id consistent between envelope and manifest"
    },
    "C3_locator_resolution": {
     "status": "pass",
     "detail": "25/25 asset locators re-resolved byte-exact against the live markdown (slice==quote, line, global occurrence count, token-in-quote)"
    },
    "C4_counts_recompute": {
     "status": "pass",
     "detail": "assets_total/histogram/by_status/locators/claims recomputed from the assets array: assert(assets_total=25, histogram==True, by_status==True, sum==total)"
    },
    "C5_id_integrity": {
     "status": "pass",
     "detail": "25 ids, 25 unique, pattern r11363:* ok=True"
    },
    "C6_bundle_consistency": {
     "status": "pass",
     "detail": "quote re-resolved at line 119; enumerated members expand to 10 files (list length 7, one entry being a '4 png' group) == member_file_count 10; the report's own '（10 文件）' phrase re-resolved at line 10"
    },
    "C7_figure_probe_recheck": {
     "status": "pass",
     "detail": "4 figure endpoints re-probed live; status/bytes/sha256 re-derived and compared with the manifest's payload_sha256 (mismatches=[])"
    },
    "C8_observation_vs_probe": {
     "status": "fail",
     "detail": "observations[1] states the /figures byte endpoints answer 404 and that no figure hash is claimed; the same manifest records http_status=200 + payload_sha256 for 4 figure endpoints (fig1_per_device_savings.png,fig2_combined_vs_sum.png,fig3_selfprop_coupling.png,fig4_benchmark.png)"
    },
    "C9_schema_validation": {
     "status": "fail",
     "detail": "jsonschema: envelope vs schemas/kf_result.v1.schema.json (draft 2020-12, additionalProperties=false on the root) and manifest vs schemas/asset_manifest_wp11363_01.schema.json (draft-07); errors=[\"kf_result.json: Additional properties are not allowed ('claims' was unexpected) at []\"]; prevalence over docs/kf/*/kf_result.json = {'packages': 118, 'with_toplevel_claims': 83, 'schema_ok': 7}"
    },
    "C10_envelope_manifest_identity": {
     "status": "pass",
     "detail": "envelope.outputs['asset_manifest.json'] is byte-equal (deep) to docs/kf/wp-11363-01/asset_manifest.json; envelope.provenance.source_hash == manifest.source.source_hash == live recompute"
    },
    "C11_verification_scope": {
     "status": "pass",
     "detail": "claims==[] in manifest and envelope with claims_empty_reason present; the single capability declaration is status=declared_reference_only with an explicit 'does NOT verify' reason; the only 'verified' keys are quote-resolution flags (29 paths, e.g. ['/assets[0]/locator/quote_verified', '/assets[10]/locator/quote_verified']) — no claim-grade verification asserted (claim_level_hits=[])"
    },
    "C12_cross_report_isolation": {
     "status": "pass",
     "detail": "all report-id-shaped tokens in the package are '11363'; other 5-digit numbers found: [] (checked in context: mission_id/values, not report ids)"
    },
    "C13_registration_completeness": {
     "status": "pass_with_notes",
     "detail": "artefacts named in the report's audit chain vs registered assets: 8 individually registered, 5 covered only by the artifacts/esd/ directory quote, 0 uncovered"
    },
    "C17_negative_resolution_claims": {
     "status": "pass",
     "detail": "14 unresolved artefacts re-probed by basename across the delivery worktree; the manifest's claim that none is present (same_basename_hits=[]) is confirmed for 14/14"
    },
    "C14_report_arithmetic": {
     "status": "pass",
     "detail": "informational (outside 01's scope): Σ分项 recomputed from the 12 component rows vs the 21 combined rows printed in §③ — max |drift| = 0.01 pp; margin = Σ−combined within 0.01 pp; combined ≤ Σ holds for all printed rows; Δn/n max 2.9% < 5%; implied P_D per ship from kW/% is {'KVLCC2': [24.1, 24.1, 24.0, 24.0], 'KCS': [36.2, 36.2, 36.2, 36.1], 'Bulk180': [7.4, 7.4, 7.4, 7.4]}"
    },
    "C15_upstream_packages": {
     "status": "unknown_not_run",
     "detail": "platform work-package registry endpoints answer {'/tensor/work_packages?report_id=11363': 404, '/tensor/reports/11363/work_packages': 404} (no route to enumerate packages for a report, so pipeline completeness cannot be read from the platform). In the delivery worktree only wp-11363-01 exists for report 11363: {'wp-11363-01': True, 'wp-11363-02': False, 'wp-11363-03': False}"
    },
    "C16_independence": {
     "status": "pass",
     "detail": "context used = live report markdown (GET /tensor/reports/11363, sha256 sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23) + the two reviewed package artefacts only. docs/kf/wp-11363-01/report_selfcheck.json (the producer's own self-check) is excluded as evidence; every check above is recomputed here. Neither the producer's task prompt nor any producer narrative was used."
    }
   },
   "checks_not_run": [
    "upstream_packages_completed (C15): no registry route, upstream packages for 11363 absent from the worktree",
    "byte-level verification of the 10-file artifacts/esd bundle and of the ship-performance-platform source files: outside the delivery worktree by construction (registered as unresolved by 01)",
    "the report's full 45-combination grid (only the 21 printed rows are recomputable from the markdown text)"
   ],
   "findings": [
    {
     "id": "F4",
     "severity": "low",
     "blocking": false,
     "title": "bundle_consistency.declared_in_manifest_line holds a file COUNT (10), not a line number",
     "evidence": {
      "field": "bundle_consistency.declared_in_manifest_line",
      "value": 10,
      "field_named_line_but_means": "the '（10 文件）' file count declared on report line 120",
      "quote_at_that_line": "- 清单 sha256：`artifacts/esd/manifest.json`（10 文件）",
      "semantically_correct_home": "bundle_consistency.member_file_count == 10"
     },
     "reproduction": "python3 runs/m19810/verify_wp11363_04.py (C6) — resolves the field as a line index and finds the '10 文件' count phrase instead of a line reference",
     "affected_scope": "naming/ambiguity only; the arithmetic (6 named files + 4 png = 10) is correct and matches the report at line 120, so no count is misstated",
     "overstated_claim": false
    },
    {
     "id": "F1",
     "severity": "medium",
     "blocking": false,
     "title": "manifest.observations contradicts manifest.platform_attachment_probes (figure byte status/hash)",
     "evidence": {
      "observation_text": "All four figures are declared in the platform record with captions, but the /figures byte endpoints answer 404, so no figure hash is claimed.",
      "probes": {
       "fig1_per_device_savings.png": {
        "http_status": 200,
        "payload_sha256": "sha256:333035f7049386bfd7c41fb2dc1099285296075aebfdb10c55a1237cd43ff187",
        "png_magic_ok": true
       },
       "fig2_combined_vs_sum.png": {
        "http_status": 200,
        "payload_sha256": "sha256:411fb6d7836e18fc70f49acc268cc0561a30e628727f79e2b39d57df39b5fa2e",
        "png_magic_ok": true
       },
       "fig3_selfprop_coupling.png": {
        "http_status": 200,
        "payload_sha256": "sha256:5221d33b542e11ebb45b444d8d51b600922bd260ab2be8383734bcafeb3fedf9",
        "png_magic_ok": true
       },
       "fig4_benchmark.png": {
        "http_status": 200,
        "payload_sha256": "sha256:135db99c731212ff89f52a2853670ac0ea35a478e669e181670ba064fa9edc1d",
        "png_magic_ok": true
       }
      },
      "live_reprobe": {
       "fig1_per_device_savings.png": {
        "http_status": 200,
        "bytes": 55500,
        "sha256": "sha256:333035f7049386bfd7c41fb2dc1099285296075aebfdb10c55a1237cd43ff187",
        "png_magic_ok": true
       },
       "fig2_combined_vs_sum.png": {
        "http_status": 200,
        "bytes": 192545,
        "sha256": "sha256:411fb6d7836e18fc70f49acc268cc0561a30e628727f79e2b39d57df39b5fa2e",
        "png_magic_ok": true
       },
       "fig3_selfprop_coupling.png": {
        "http_status": 200,
        "bytes": 53786,
        "sha256": "sha256:5221d33b542e11ebb45b444d8d51b600922bd260ab2be8383734bcafeb3fedf9",
        "png_magic_ok": true
       },
       "fig4_benchmark.png": {
        "http_status": 200,
        "bytes": 71694,
        "sha256": "sha256:135db99c731212ff89f52a2853670ac0ea35a478e669e181670ba064fa9edc1d",
        "png_magic_ok": true
       },
       "figures_endpoint": {
        "http_status": 404,
        "entries": 0
       }
      }
     },
     "reproduction": "python3 runs/m19810/verify_wp11363_04.py (C8) — re-probes the four figure endpoints and compares http_status/bytes/sha256 with the manifest probe block",
     "affected_scope": "narrative observation field only; the numeric probe block is correct, so no asset hash or asset count is wrong. Downstream consumers that read observations instead of probes would wrongly conclude the figure bytes are unavailable.",
     "overstated_claim": false
    },
    {
     "id": "F3",
     "severity": "high",
     "blocking": true,
     "title": "envelope kf_result.json fails the canonical schema: top-level 'claims' is an additional property (additionalProperties=false) — the declared schema_pass is not reproducible with schemas/kf_result.v1.schema.json",
     "evidence": {
      "schema_root_properties": [
       "contract_version",
       "outputs",
       "package_id",
       "provenance",
       "report_id",
       "task_type"
      ],
      "schema_additionalProperties": false,
      "validator_error": [
       "kf_result.json: Additional properties are not allowed ('claims' was unexpected) at []"
      ],
      "envelope_top_level_keys": [
       "claims",
       "outputs",
       "package_id",
       "provenance",
       "report_id",
       "task_type"
      ],
      "where_claims_is_allowed": "outputs.claims (array)",
      "lane_prevalence": {
       "packages": 118,
       "with_toplevel_claims": 83,
       "schema_ok": 7
      }
     },
     "reproduction": "python3 -c \"import json,jsonschema;d=json.load(open('docs/kf/wp-11363-01/kf_result.json'));jsonschema.validate(d,json.load(open('schemas/kf_result.v1.schema.json')))\"",
     "affected_scope": "lane-wide contract drift, not a defect unique to this package: 83/118 packages under docs/kf/*/kf_result.json carry the same top-level 'claims' key and only 7/118 validate. Consequence for 01: its acceptance item schema_pass=true (report_selfcheck.json) cannot be reproduced with the committed canonical schema; the review therefore records schema_pass as NOT CONFIRMED. Remediation is a schema/convention decision (add 'claims' to the canonical root, or move it into outputs.claims) and belongs to the lane owner, not to package 01.",
     "overstated_claim": true
    },
    {
     "id": "F5",
     "severity": "low",
     "blocking": false,
     "title": "'verified' tokens in the package are quote-resolution flags (quote_verified / all_verified), which a naive scanner can misread as claim verification",
     "evidence": {
      "occurrences": 29,
      "distinct_paths": [
       "/assets[0]/locator/quote_verified",
       "/assets[10]/locator/quote_verified",
       "/assets[11]/locator/quote_verified",
       "/assets[12]/locator/quote_verified"
      ],
      "claim_grade_flags": [],
      "capability_asset_status": [
       {
        "status": "declared_reference_only",
        "scope": "declared_in_prose_only",
        "reason": "the report declares this capability grade; this 工序 records the declaration verbatim and does NOT verify it (the platform gate computes verification), so no grade is endorsed here"
       }
      ]
     },
     "reproduction": "python3 runs/m19810/verify_wp11363_04.py (C11) — collects every key containing 'verified'",
     "affected_scope": "no claim is marked verified in the substantive sense: claims==[] and the capability declaration is declared_reference_only with a 'does NOT verify' reason. This note is about scanner ambiguity, not about a false verification claim",
     "overstated_claim": false
    },
    {
     "id": "F2",
     "severity": "low",
     "blocking": false,
     "title": "artefacts cited outside the audit-chain line are registered only implicitly (no per-file asset row, no further_occurrences entry)",
     "evidence": {
      "cited_only_inside_directory_quote": [
       "benchmark_results.json",
       "golden_regression.json",
       "per_device_table.csv",
       "combined_table.csv",
       "report_tables.md"
      ],
      "example": "line 44 names artifacts/esd/combined_table.csv as the full table behind the §③ combined-savings table; the only registration of that file is inside the line-119 directory quote of asset r11363:ref:09",
      "first_citation": {
       "benchmark_results.json": {
        "line": 119,
        "occurrences": 1
       },
       "golden_regression.json": {
        "line": 119,
        "occurrences": 1
       },
       "per_device_table.csv": {
        "line": 119,
        "occurrences": 1
       },
       "combined_table.csv": {
        "line": 44,
        "occurrences": 2
       },
       "report_tables.md": {
        "line": 119,
        "occurrences": 1
       }
      }
     },
     "reproduction": "python3 runs/m19810/verify_wp11363_04.py (C13)",
     "affected_scope": "registration granularity only; the citation is still locatable verbatim inside the directory quote at line 119, so no citation is lost or mis-attributed",
     "overstated_claim": false
    }
   ],
   "check_ledger": {
    "package_id": "wp-11363-04",
    "reviewed_package_id": "wp-11363-01",
    "report_id": "11363",
    "checks": {
     "C1_source_identity": {
      "status": "pass",
      "detail": "live recompute vs manifest.source vs contract: hash=sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23 chars=6902 bytes=9618 lines=124",
      "recomputed": {
       "sha256": "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23",
       "chars": 6902,
       "bytes": 9618,
       "lines": 124,
       "has_crlf": false,
       "has_trailing_newline": true
      }
     },
     "C2_report_identity": {
      "status": "pass",
      "detail": "live record title/scenario == manifest.record_fields; package_id/task_type/report_id consistent between envelope and manifest"
     },
     "C3_locator_resolution": {
      "status": "pass",
      "detail": "25/25 asset locators re-resolved byte-exact against the live markdown (slice==quote, line, global occurrence count, token-in-quote)",
      "failures": [],
      "per_asset": [
       {
        "asset_id": "r11363:source-markdown",
        "ok": true,
        "line": 1,
        "reasons": [],
        "label": "report-11363-markdown",
        "kind": "report_markdown"
       },
       {
        "asset_id": "r11363:figure:01",
        "ok": true,
        "line": 87,
        "reasons": [],
        "label": "fig1_per_device_savings.png",
        "kind": "embedded_figure"
       },
       {
        "asset_id": "r11363:figure:02",
        "ok": true,
        "line": 88,
        "reasons": [],
        "label": "fig2_combined_vs_sum.png",
        "kind": "embedded_figure"
       },
       {
        "asset_id": "r11363:figure:03",
        "ok": true,
        "line": 89,
        "reasons": [],
        "label": "fig3_selfprop_coupling.png",
        "kind": "embedded_figure"
       },
       {
        "asset_id": "r11363:figure:04",
        "ok": true,
        "line": 90,
        "reasons": [],
        "label": "fig4_benchmark.png",
        "kind": "embedded_figure"
       },
       {
        "asset_id": "r11363:ref:01",
        "ok": true,
        "line": 3,
        "reasons": [],
        "label": "backend/physics/esd/",
        "kind": "source_directory_reference"
       },
       {
        "asset_id": "r11363:ref:02",
        "ok": true,
        "line": 19,
        "reasons": [],
        "label": "physics/esd/devices.py",
        "kind": "source_code_reference"
       },
       {
        "asset_id": "r11363:ref:03",
        "ok": true,
        "line": 19,
        "reasons": [],
        "label": "DEVICE_SPECS",
        "kind": "symbol_reference"
       },
       {
        "asset_id": "r11363:ref:04",
        "ok": true,
        "line": 20,
        "reasons": [],
        "label": "selfprop.py",
        "kind": "source_code_reference"
       },
       {
        "asset_id": "r11363:ref:05",
        "ok": true,
        "line": 20,
        "reasons": [],
        "label": "modules.propeller_bemt.bem_point",
        "kind": "symbol_reference"
       },
       {
        "asset_id": "r11363:ref:06",
        "ok": true,
        "line": 20,
        "reasons": [],
        "label": "solve_n_for_thrust",
        "kind": "symbol_reference"
       },
       {
        "asset_id": "r11363:ref:07",
        "ok": true,
        "line": 22,
        "reasons": [],
        "label": "energy_upper_bound.satisfied",
        "kind": "symbol_reference"
       },
       {
        "asset_id": "r11363:ref:08",
        "ok": true,
        "line": 23,
        "reasons": [],
        "label": "tools/gen_esd_artifacts.py",
        "kind": "source_code_reference"
       },
       {
        "asset_id": "r11363:ref:09",
        "ok": true,
        "line": 119,
        "reasons": [],
        "label": "artifacts/esd/",
        "kind": "source_directory_reference"
       },
       {
        "asset_id": "r11363:ref:10",
        "ok": true,
        "line": 120,
        "reasons": [],
        "label": "artifacts/esd/manifest.json",
        "kind": "data_artifact_reference"
       },
       {
        "asset_id": "r11363:ref:11",
        "ok": true,
        "line": 121,
        "reasons": [],
        "label": "test_golden_grid_reproducible",
        "kind": "symbol_reference"
       },
       {
        "asset_id": "r11363:ref:12",
        "ok": true,
        "line": 122,
        "reasons": [],
        "label": "tests/test_esd_energy_upper_bound.py",
        "kind": "source_code_reference"
       },
       {
        "asset_id": "r11363:ref:13",
        "ok": true,
        "line": 122,
        "reasons": [],
        "label": "test_esd_devices.py",
        "kind": "source_code_reference"
       },
       {
        "asset_id": "r11363:ref:14",
        "ok": true,
        "line": 122,
        "reasons": [],
        "label": "test_esd_benchmark.py",
        "kind": "source_code_reference"
       },
       {
        "asset_id": "r11363:ref:15",
        "ok": true,
        "line": 122,
        "reasons": [],
        "label": "test_esd_api.py",
        "kind": "source_code_reference"
       },
       {
        "asset_id": "r11363:ref:16",
        "ok": true,
        "line": 122,
        "reasons": [],
        "label": "test_esd_regression.py",
        "kind": "source_code_reference"
       },
       {
        "asset_id": "r11363:ref:17",
        "ok": true,
        "line": 123,
        "reasons": [],
        "label": "docs/ESD_ENERGY_SAVING.md",
        "kind": "document_reference"
       },
       {
        "asset_id": "r11363:ref:18",
        "ok": true,
        "line": 124,
        "reasons": [],
        "label": "propulsion.esd_energy_saving = REAL",
        "kind": "capability_declaration_reference"
       },
       {
        "asset_id": "r11363:ref:19",
        "ok": true,
        "line": 124,
        "reasons": [],
        "label": "artifacts/esd/capability_delta.json",
        "kind": "data_artifact_reference"
       },
       {
        "asset_id": "r11363:ref:upstream-resistance",
        "ok": true,
        "line": 15,
        "reasons": [],
        "label": "Holtrop-1984 resistance kernel feeding R_T",
        "kind": "upstream_dependency_reference"
       }
      ]
     },
     "C4_counts_recompute": {
      "status": "pass",
      "detail": "assets_total/histogram/by_status/locators/claims recomputed from the assets array: assert(assets_total=25, histogram==True, by_status==True, sum==total)"
     },
     "C5_id_integrity": {
      "status": "pass",
      "detail": "25 ids, 25 unique, pattern r11363:* ok=True"
     },
     "C6_bundle_consistency": {
      "status": "pass",
      "detail": "quote re-resolved at line 119; enumerated members expand to 10 files (list length 7, one entry being a '4 png' group) == member_file_count 10; the report's own '（10 文件）' phrase re-resolved at line 10",
      "list_length": 7,
      "count_phrase": true,
      "declared_line_text": "- 清单 sha256：`artifacts/esd/manifest.json`（10 文件）",
      "count_phrase_lines": [
       120
      ]
     },
     "C7_figure_probe_recheck": {
      "status": "pass",
      "detail": "4 figure endpoints re-probed live; status/bytes/sha256 re-derived and compared with the manifest's payload_sha256 (mismatches=[])",
      "reprobe": {
       "figures_endpoint": {
        "declared": {
         "endpoint": "/tensor/reports/11363/figures",
         "http_status": 404,
         "bytes": 0
        },
        "recomputed": {
         "http_status": 404,
         "entries": 0
        }
       },
       "fig1_per_device_savings.png": {
        "declared": {
         "http_status": 200,
         "bytes": 55500,
         "payload_sha256": "sha256:333035f7049386bfd7c41fb2dc1099285296075aebfdb10c55a1237cd43ff187"
        },
        "recomputed": {
         "http_status": 200,
         "bytes": 55500,
         "sha256": "sha256:333035f7049386bfd7c41fb2dc1099285296075aebfdb10c55a1237cd43ff187",
         "png_magic_ok": true
        }
       },
       "fig2_combined_vs_sum.png": {
        "declared": {
         "http_status": 200,
         "bytes": 192545,
         "payload_sha256": "sha256:411fb6d7836e18fc70f49acc268cc0561a30e628727f79e2b39d57df39b5fa2e"
        },
        "recomputed": {
         "http_status": 200,
         "bytes": 192545,
         "sha256": "sha256:411fb6d7836e18fc70f49acc268cc0561a30e628727f79e2b39d57df39b5fa2e",
         "png_magic_ok": true
        }
       },
       "fig3_selfprop_coupling.png": {
        "declared": {
         "http_status": 200,
         "bytes": 53786,
         "payload_sha256": "sha256:5221d33b542e11ebb45b444d8d51b600922bd260ab2be8383734bcafeb3fedf9"
        },
        "recomputed": {
         "http_status": 200,
         "bytes": 53786,
         "sha256": "sha256:5221d33b542e11ebb45b444d8d51b600922bd260ab2be8383734bcafeb3fedf9",
         "png_magic_ok": true
        }
       },
       "fig4_benchmark.png": {
        "declared": {
         "http_status": 200,
         "bytes": 71694,
         "payload_sha256": "sha256:135db99c731212ff89f52a2853670ac0ea35a478e669e181670ba064fa9edc1d"
        },
        "recomputed": {
         "http_status": 200,
         "bytes": 71694,
         "sha256": "sha256:135db99c731212ff89f52a2853670ac0ea35a478e669e181670ba064fa9edc1d",
         "png_magic_ok": true
        }
       }
      }
     },
     "C8_observation_vs_probe": {
      "status": "fail",
      "detail": "observations[1] states the /figures byte endpoints answer 404 and that no figure hash is claimed; the same manifest records http_status=200 + payload_sha256 for 4 figure endpoints (fig1_per_device_savings.png,fig2_combined_vs_sum.png,fig3_selfprop_coupling.png,fig4_benchmark.png)",
      "contradictory": true
     },
     "C9_schema_validation": {
      "status": "fail",
      "detail": "jsonschema: envelope vs schemas/kf_result.v1.schema.json (draft 2020-12, additionalProperties=false on the root) and manifest vs schemas/asset_manifest_wp11363_01.schema.json (draft-07); errors=[\"kf_result.json: Additional properties are not allowed ('claims' was unexpected) at []\"]; prevalence over docs/kf/*/kf_result.json = {'packages': 118, 'with_toplevel_claims': 83, 'schema_ok': 7}",
      "errors": [
       "kf_result.json: Additional properties are not allowed ('claims' was unexpected) at []"
      ],
      "prevalence": {
       "packages": 118,
       "with_toplevel_claims": 83,
       "schema_ok": 7
      }
     },
     "C10_envelope_manifest_identity": {
      "status": "pass",
      "detail": "envelope.outputs['asset_manifest.json'] is byte-equal (deep) to docs/kf/wp-11363-01/asset_manifest.json; envelope.provenance.source_hash == manifest.source.source_hash == live recompute"
     },
     "C11_verification_scope": {
      "status": "pass",
      "detail": "claims==[] in manifest and envelope with claims_empty_reason present; the single capability declaration is status=declared_reference_only with an explicit 'does NOT verify' reason; the only 'verified' keys are quote-resolution flags (29 paths, e.g. ['/assets[0]/locator/quote_verified', '/assets[10]/locator/quote_verified']) — no claim-grade verification asserted (claim_level_hits=[])",
      "quote_level_paths": [
       "/assets[0]/locator/quote_verified",
       "/assets[10]/locator/quote_verified",
       "/assets[11]/locator/quote_verified",
       "/assets[12]/locator/quote_verified",
       "/assets[13]/further_occurrences[0]/quote_verified",
       "/assets[13]/further_occurrences[1]/quote_verified",
       "/assets[13]/further_occurrences[2]/quote_verified",
       "/assets[13]/locator/quote_verified",
       "/assets[14]/locator/quote_verified",
       "/assets[15]/locator/quote_verified",
       "/assets[16]/locator/quote_verified",
       "/assets[17]/locator/quote_verified",
       "/assets[18]/locator/quote_verified",
       "/assets[19]/locator/quote_verified",
       "/assets[1]/locator/quote_verified",
       "/assets[20]/locator/quote_verified",
       "/assets[21]/locator/quote_verified",
       "/assets[22]/locator/quote_verified",
       "/assets[23]/locator/quote_verified",
       "/assets[24]/locator/quote_verified",
       "/assets[2]/locator/quote_verified",
       "/assets[3]/locator/quote_verified",
       "/assets[4]/locator/quote_verified",
       "/assets[5]/locator/quote_verified",
       "/assets[6]/locator/quote_verified",
       "/assets[7]/locator/quote_verified",
       "/assets[8]/locator/quote_verified",
       "/assets[9]/locator/quote_verified",
       "/locators/all_verified"
      ]
     },
     "C12_cross_report_isolation": {
      "status": "pass",
      "detail": "all report-id-shaped tokens in the package are '11363'; other 5-digit numbers found: [] (checked in context: mission_id/values, not report ids)",
      "other_numbers": []
     },
     "C13_registration_completeness": {
      "status": "pass_with_notes",
      "detail": "artefacts named in the report's audit chain vs registered assets: 8 individually registered, 5 covered only by the artifacts/esd/ directory quote, 0 uncovered",
      "first_citation": {
       "benchmark_results.json": {
        "line": 119,
        "occurrences": 1
       },
       "golden_regression.json": {
        "line": 119,
        "occurrences": 1
       },
       "per_device_table.csv": {
        "line": 119,
        "occurrences": 1
       },
       "combined_table.csv": {
        "line": 44,
        "occurrences": 2
       },
       "report_tables.md": {
        "line": 119,
        "occurrences": 1
       },
       "manifest.json": {
        "line": 119,
        "occurrences": 2
       },
       "capability_delta.json": {
        "line": 124,
        "occurrences": 1
       },
       "ESD_ENERGY_SAVING.md": {
        "line": 123,
        "occurrences": 1
       },
       "test_esd_energy_upper_bound.py": {
        "line": 122,
        "occurrences": 1
       },
       "test_esd_devices.py": {
        "line": 122,
        "occurrences": 1
       },
       "test_esd_benchmark.py": {
        "line": 122,
        "occurrences": 1
       },
       "test_esd_api.py": {
        "line": 122,
        "occurrences": 1
       },
       "test_esd_regression.py": {
        "line": 122,
        "occurrences": 1
       }
      },
      "only_inside_dir": [
       "benchmark_results.json",
       "golden_regression.json",
       "per_device_table.csv",
       "combined_table.csv",
       "report_tables.md"
      ],
      "uncovered": []
     },
     "C17_negative_resolution_claims": {
      "status": "pass",
      "detail": "14 unresolved artefacts re-probed by basename across the delivery worktree; the manifest's claim that none is present (same_basename_hits=[]) is confirmed for 14/14",
      "probed": {
       "physics/esd/devices.py": [],
       "selfprop.py": [],
       "modules.propeller_bemt.bem_point": [],
       "energy_upper_bound.satisfied": [],
       "tools/gen_esd_artifacts.py": [],
       "artifacts/esd/manifest.json": [
        "docs/sediment/tk-sediment-m5054/figures/manifest.json",
        "knowledge/kb10k/manifest.json",
        "knowledge/sediment/sloshing-impact-lbm/manifest.json"
       ],
       "tests/test_esd_energy_upper_bound.py": [],
       "test_esd_devices.py": [],
       "test_esd_benchmark.py": [],
       "test_esd_api.py": [],
       "test_esd_regression.py": [],
       "docs/ESD_ENERGY_SAVING.md": [],
       "propulsion.esd_energy_saving = REAL": [],
       "artifacts/esd/capability_delta.json": []
      },
      "contradicted": []
     },
     "C14_report_arithmetic": {
      "status": "pass",
      "detail": "informational (outside 01's scope): Σ分项 recomputed from the 12 component rows vs the 21 combined rows printed in §③ — max |drift| = 0.01 pp; margin = Σ−combined within 0.01 pp; combined ≤ Σ holds for all printed rows; Δn/n max 2.9% < 5%; implied P_D per ship from kW/% is {'KVLCC2': [24.1, 24.1, 24.0, 24.0], 'KCS': [36.2, 36.2, 36.2, 36.1], 'Bulk180': [7.4, 7.4, 7.4, 7.4]}",
      "sum_drift": [
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.01,
       0.0,
       0.01,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0
      ],
      "margin_drift": [
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.01,
       0.0,
       0.01,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0,
       0.0
      ],
      "literature_rel_err_from_rounded": [
       {
        "case": "KVLCC2_preswirl",
        "recomputed_pct": 0.5
       },
       {
        "case": "KCS_pbcf",
        "recomputed_pct": 3.67
       },
       {
        "case": "KVLCC2_rudder_bulb",
        "recomputed_pct": 3.75
       },
       {
        "case": "Bulk180_mewis",
        "recomputed_pct": 3.6
       },
       {
        "case": "KCS_hubcap",
        "recomputed_pct": 9.17
       }
      ],
      "literature_reported": {
       "max": 9.33,
       "mean": 4.13,
       "mean_recomputed_from_rounded": 4.14
      },
      "note": "reported 3.68/3.69/3.52/9.33/0.46 and mean 4.13 are consistent with errors evaluated on unrounded model values and then rounded to 2 dp; recomputation from the printed 2-dp values reproduces them within 0.02 pp"
     },
     "C15_upstream_packages": {
      "status": "unknown_not_run",
      "detail": "platform work-package registry endpoints answer {'/tensor/work_packages?report_id=11363': 404, '/tensor/reports/11363/work_packages': 404} (no route to enumerate packages for a report, so pipeline completeness cannot be read from the platform). In the delivery worktree only wp-11363-01 exists for report 11363: {'wp-11363-01': True, 'wp-11363-02': False, 'wp-11363-03': False}",
      "registry_probe": {
       "/tensor/work_packages?report_id=11363": 404,
       "/tensor/reports/11363/work_packages": 404
      },
      "worktree": {
       "wp-11363-01": true,
       "wp-11363-02": {
        "found": false,
        "hits": []
       },
       "wp-11363-03": {
        "found": false,
        "hits": []
       }
      }
     },
     "C16_independence": {
      "status": "pass",
      "detail": "context used = live report markdown (GET /tensor/reports/11363, sha256 sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23) + the two reviewed package artefacts only. docs/kf/wp-11363-01/report_selfcheck.json (the producer's own self-check) is excluded as evidence; every check above is recomputed here. Neither the producer's task prompt nor any producer narrative was used."
     }
    },
    "findings": [
     {
      "id": "F4",
      "severity": "low",
      "blocking": false,
      "title": "bundle_consistency.declared_in_manifest_line holds a file COUNT (10), not a line number",
      "evidence": {
       "field": "bundle_consistency.declared_in_manifest_line",
       "value": 10,
       "field_named_line_but_means": "the '（10 文件）' file count declared on report line 120",
       "quote_at_that_line": "- 清单 sha256：`artifacts/esd/manifest.json`（10 文件）",
       "semantically_correct_home": "bundle_consistency.member_file_count == 10"
      },
      "reproduction": "python3 runs/m19810/verify_wp11363_04.py (C6) — resolves the field as a line index and finds the '10 文件' count phrase instead of a line reference",
      "affected_scope": "naming/ambiguity only; the arithmetic (6 named files + 4 png = 10) is correct and matches the report at line 120, so no count is misstated",
      "overstated_claim": false
     },
     {
      "id": "F1",
      "severity": "medium",
      "blocking": false,
      "title": "manifest.observations contradicts manifest.platform_attachment_probes (figure byte status/hash)",
      "evidence": {
       "observation_text": "All four figures are declared in the platform record with captions, but the /figures byte endpoints answer 404, so no figure hash is claimed.",
       "probes": {
        "fig1_per_device_savings.png": {
         "http_status": 200,
         "payload_sha256": "sha256:333035f7049386bfd7c41fb2dc1099285296075aebfdb10c55a1237cd43ff187",
         "png_magic_ok": true
        },
        "fig2_combined_vs_sum.png": {
         "http_status": 200,
         "payload_sha256": "sha256:411fb6d7836e18fc70f49acc268cc0561a30e628727f79e2b39d57df39b5fa2e",
         "png_magic_ok": true
        },
        "fig3_selfprop_coupling.png": {
         "http_status": 200,
         "payload_sha256": "sha256:5221d33b542e11ebb45b444d8d51b600922bd260ab2be8383734bcafeb3fedf9",
         "png_magic_ok": true
        },
        "fig4_benchmark.png": {
         "http_status": 200,
         "payload_sha256": "sha256:135db99c731212ff89f52a2853670ac0ea35a478e669e181670ba064fa9edc1d",
         "png_magic_ok": true
        }
       },
       "live_reprobe": {
        "fig1_per_device_savings.png": {
         "http_status": 200,
         "bytes": 55500,
         "sha256": "sha256:333035f7049386bfd7c41fb2dc1099285296075aebfdb10c55a1237cd43ff187",
         "png_magic_ok": true
        },
        "fig2_combined_vs_sum.png": {
         "http_status": 200,
         "bytes": 192545,
         "sha256": "sha256:411fb6d7836e18fc70f49acc268cc0561a30e628727f79e2b39d57df39b5fa2e",
         "png_magic_ok": true
        },
        "fig3_selfprop_coupling.png": {
         "http_status": 200,
         "bytes": 53786,
         "sha256": "sha256:5221d33b542e11ebb45b444d8d51b600922bd260ab2be8383734bcafeb3fedf9",
         "png_magic_ok": true
        },
        "fig4_benchmark.png": {
         "http_status": 200,
         "bytes": 71694,
         "sha256": "sha256:135db99c731212ff89f52a2853670ac0ea35a478e669e181670ba064fa9edc1d",
         "png_magic_ok": true
        },
        "figures_endpoint": {
         "http_status": 404,
         "entries": 0
        }
       }
      },
      "reproduction": "python3 runs/m19810/verify_wp11363_04.py (C8) — re-probes the four figure endpoints and compares http_status/bytes/sha256 with the manifest probe block",
      "affected_scope": "narrative observation field only; the numeric probe block is correct, so no asset hash or asset count is wrong. Downstream consumers that read observations instead of probes would wrongly conclude the figure bytes are unavailable.",
      "overstated_claim": false
     },
     {
      "id": "F3",
      "severity": "high",
      "blocking": true,
      "title": "envelope kf_result.json fails the canonical schema: top-level 'claims' is an additional property (additionalProperties=false) — the declared schema_pass is not reproducible with schemas/kf_result.v1.schema.json",
      "evidence": {
       "schema_root_properties": [
        "contract_version",
        "outputs",
        "package_id",
        "provenance",
        "report_id",
        "task_type"
       ],
       "schema_additionalProperties": false,
       "validator_error": [
        "kf_result.json: Additional properties are not allowed ('claims' was unexpected) at []"
       ],
       "envelope_top_level_keys": [
        "claims",
        "outputs",
        "package_id",
        "provenance",
        "report_id",
        "task_type"
       ],
       "where_claims_is_allowed": "outputs.claims (array)",
       "lane_prevalence": {
        "packages": 118,
        "with_toplevel_claims": 83,
        "schema_ok": 7
       }
      },
      "reproduction": "python3 -c \"import json,jsonschema;d=json.load(open('docs/kf/wp-11363-01/kf_result.json'));jsonschema.validate(d,json.load(open('schemas/kf_result.v1.schema.json')))\"",
      "affected_scope": "lane-wide contract drift, not a defect unique to this package: 83/118 packages under docs/kf/*/kf_result.json carry the same top-level 'claims' key and only 7/118 validate. Consequence for 01: its acceptance item schema_pass=true (report_selfcheck.json) cannot be reproduced with the committed canonical schema; the review therefore records schema_pass as NOT CONFIRMED. Remediation is a schema/convention decision (add 'claims' to the canonical root, or move it into outputs.claims) and belongs to the lane owner, not to package 01.",
      "overstated_claim": true
     },
     {
      "id": "F5",
      "severity": "low",
      "blocking": false,
      "title": "'verified' tokens in the package are quote-resolution flags (quote_verified / all_verified), which a naive scanner can misread as claim verification",
      "evidence": {
       "occurrences": 29,
       "distinct_paths": [
        "/assets[0]/locator/quote_verified",
        "/assets[10]/locator/quote_verified",
        "/assets[11]/locator/quote_verified",
        "/assets[12]/locator/quote_verified"
       ],
       "claim_grade_flags": [],
       "capability_asset_status": [
        {
         "status": "declared_reference_only",
         "scope": "declared_in_prose_only",
         "reason": "the report declares this capability grade; this 工序 records the declaration verbatim and does NOT verify it (the platform gate computes verification), so no grade is endorsed here"
        }
       ]
      },
      "reproduction": "python3 runs/m19810/verify_wp11363_04.py (C11) — collects every key containing 'verified'",
      "affected_scope": "no claim is marked verified in the substantive sense: claims==[] and the capability declaration is declared_reference_only with a 'does NOT verify' reason. This note is about scanner ambiguity, not about a false verification claim",
      "overstated_claim": false
     },
     {
      "id": "F2",
      "severity": "low",
      "blocking": false,
      "title": "artefacts cited outside the audit-chain line are registered only implicitly (no per-file asset row, no further_occurrences entry)",
      "evidence": {
       "cited_only_inside_directory_quote": [
        "benchmark_results.json",
        "golden_regression.json",
        "per_device_table.csv",
        "combined_table.csv",
        "report_tables.md"
       ],
       "example": "line 44 names artifacts/esd/combined_table.csv as the full table behind the §③ combined-savings table; the only registration of that file is inside the line-119 directory quote of asset r11363:ref:09",
       "first_citation": {
        "benchmark_results.json": {
         "line": 119,
         "occurrences": 1
        },
        "golden_regression.json": {
         "line": 119,
         "occurrences": 1
        },
        "per_device_table.csv": {
         "line": 119,
         "occurrences": 1
        },
        "combined_table.csv": {
         "line": 44,
         "occurrences": 2
        },
        "report_tables.md": {
         "line": 119,
         "occurrences": 1
        }
       }
      },
      "reproduction": "python3 runs/m19810/verify_wp11363_04.py (C13)",
      "affected_scope": "registration granularity only; the citation is still locatable verbatim inside the directory quote at line 119, so no citation is lost or mis-attributed",
      "overstated_claim": false
     }
    ],
    "artefact_hashes": {
     "kf_result.json": "sha256:3347e4c40d00a416584f4ea879b46ebc5c4f6821ab353347a27baa2b4743f41a",
     "asset_manifest.json": "sha256:a0c199c40dbcd9bee70dba7d086279dafcf7395e956a3f7f306c60fb2b88f711",
     "report_selfcheck.json": "sha256:ad4ddefa7400ad2bd52301a1e0f61fec3fefa11132751dedaf34d2a9a39a8fc6"
    }
   },
   "evidence_locators": [
    {
     "claim_id": "Q1",
     "quote": "几何先验全通过：Cb 与 ∇/(L·B·T) 偏差 <0.02，L/B∈[4,11]、B/T∈[1.8,6]、D/T∈[0.35,0.90]、P/D∈[0.5,1.6]、Ae/Ao∈[0.3,1.2]；任一越界即拒绝（API 422），不外推。R_T 由阻力端点同源 Holtrop-1984 核注入（ESD 模块不重复算阻力，避免双源）。",
     "char_span": [
      722,
      892
     ],
     "line": 15,
     "occurrences_in_source": 1,
     "byte_exact": true,
     "used_for": "reviewed asset r11363:ref:upstream-resistance (upstream dependency: R_T from the resistance endpoint)"
    },
    {
     "claim_id": "Q2",
     "quote": "**组合节能与 Σ 分项（节选：全 4 装置 + 两个代表性双装置；全表见 artifacts/esd/combined_table.csv）**",
     "char_span": [
      2483,
      2556
     ],
     "line": 44,
     "occurrences_in_source": 1,
     "byte_exact": true,
     "used_for": "finding F2: the §③ combined table's own data pointer, cited at line 44 outside the audit chain"
    },
    {
     "claim_id": "Q3",
     "quote": "- 图 1 `fig1_per_device_savings.png`：3 船型 × 4 装置分项节能柱状图（数值标注）。",
     "char_span": [
      5056,
      5117
     ],
     "line": 87,
     "occurrences_in_source": 1,
     "byte_exact": true,
     "used_for": "figure registration: 4 embedded figures declared in §④; live byte probe in check C7"
    },
    {
     "claim_id": "Q4",
     "quote": "- 工件：`artifacts/esd/`（benchmark_results.json、golden_regression.json、per_device_table.csv、combined_table.csv、report_tables.md、4 张 png、manifest.json）",
     "char_span": [
      6383,
      6530
     ],
     "line": 119,
     "occurrences_in_source": 1,
     "byte_exact": true,
     "used_for": "reviewed asset r11363:ref:09 + bundle_consistency (6 named files + 4 png = 10)"
    },
    {
     "claim_id": "Q5",
     "quote": "- 清单 sha256：`artifacts/esd/manifest.json`（10 文件）",
     "char_span": [
      6531,
      6579
     ],
     "line": 120,
     "occurrences_in_source": 1,
     "byte_exact": true,
     "used_for": "finding F4: the '10 文件' count that bundle_consistency.declared_in_manifest_line holds (line 120)"
    },
    {
     "claim_id": "Q6",
     "quote": "- 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_api.py`、`test_esd_regression.py`）",
     "char_span": [
      6639,
      6779
     ],
     "line": 122,
     "occurrences_in_source": 1,
     "byte_exact": true,
     "used_for": "reviewed assets r11363:ref:12..ref:16; check C17 re-probes the negative resolution claim"
    },
    {
     "claim_id": "Q7",
     "quote": "- 能力：`propulsion.esd_energy_saving = REAL`（`artifacts/esd/capability_delta.json`）",
     "char_span": [
      6820,
      6901
     ],
     "line": 124,
     "occurrences_in_source": 1,
     "byte_exact": true,
     "used_for": "reviewed asset r11363:ref:18/ref:19: capability declaration registered as declared_reference_only, NOT verified (check C11)"
    },
    {
     "claim_id": "Q8",
     "quote": "全网格 45 例（3 船 × 15 组合）：能量上界门**全部 PASS**，最大交互余量 1.42 个百分点，最大 Δn/n = 2.90%（判据 <5%）。",
     "char_span": [
      4461,
      4541
     ],
     "line": 70,
     "occurrences_in_source": 1,
     "byte_exact": true,
     "used_for": "informational only: the 45-case gate is a domain claim of the report, outside 01's registration scope"
    },
    {
     "claim_id": "Q9",
     "quote": "max_rel_error = 9.33%（<15% 判据），mean_rel_error = 4.13%。",
     "char_span": [
      4990,
      5044
     ],
     "line": 83,
     "occurrences_in_source": 1,
     "byte_exact": true,
     "used_for": "informational only: literature benchmark summary; no claim-grade endorsement is given by this review"
    }
   ],
   "verified_marks": {
    "count": 0,
    "policy": "This review marks no claim as verified; it records verdicts on registration/integrity only. Verification of the report's domain claims is computed by the platform gate."
   },
   "repro_cmd": "cd <worktree> && python3 runs/m19810/fetch_source.py && python3 runs/m19810/verify_wp11363_04.py && python3 runs/m19810/build_review_report.py && python3 -m pytest tests/test_kf_wp11363_04.py -q",
   "generated_at": "2026-11-14T04:01:58.245942+00:00"
  },
  "review_events.json": [
   {
    "event_id": "wp-11363-04:ev-00",
    "type": "review_started",
    "actor": "reviewer/wp-11363-04",
    "reviewer_role": "red-team-reviewer",
    "reviewed_package_id": "wp-11363-01",
    "report_id": "11363"
   },
   {
    "event_id": "wp-11363-04:ev-01",
    "type": "independent_source_refetch",
    "source_uri": "tensor://reports/11363",
    "field": "markdown",
    "sha256": "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23",
    "chars": 6902,
    "bytes": 9618,
    "lines": 124,
    "contract_hash_matched": true
   },
   {
    "event_id": "wp-11363-04:ev-10",
    "type": "check",
    "check_id": "C10_envelope_manifest_identity",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-11",
    "type": "check",
    "check_id": "C11_verification_scope",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-12",
    "type": "check",
    "check_id": "C12_cross_report_isolation",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-13",
    "type": "check",
    "check_id": "C13_registration_completeness",
    "status": "pass_with_notes"
   },
   {
    "event_id": "wp-11363-04:ev-14",
    "type": "check",
    "check_id": "C14_report_arithmetic",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-15",
    "type": "check",
    "check_id": "C15_upstream_packages",
    "status": "unknown_not_run"
   },
   {
    "event_id": "wp-11363-04:ev-16",
    "type": "check",
    "check_id": "C16_independence",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-17",
    "type": "check",
    "check_id": "C17_negative_resolution_claims",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-18",
    "type": "check",
    "check_id": "C1_source_identity",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-19",
    "type": "check",
    "check_id": "C2_report_identity",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-20",
    "type": "check",
    "check_id": "C3_locator_resolution",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-21",
    "type": "check",
    "check_id": "C4_counts_recompute",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-22",
    "type": "check",
    "check_id": "C5_id_integrity",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-23",
    "type": "check",
    "check_id": "C6_bundle_consistency",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-24",
    "type": "check",
    "check_id": "C7_figure_probe_recheck",
    "status": "pass"
   },
   {
    "event_id": "wp-11363-04:ev-25",
    "type": "check",
    "check_id": "C8_observation_vs_probe",
    "status": "fail"
   },
   {
    "event_id": "wp-11363-04:ev-26",
    "type": "check",
    "check_id": "C9_schema_validation",
    "status": "fail"
   },
   {
    "event_id": "wp-11363-04:fv-00",
    "type": "finding_raised",
    "finding_id": "F4",
    "severity": "low",
    "blocking": false,
    "title": "bundle_consistency.declared_in_manifest_line holds a file COUNT (10), not a line number"
   },
   {
    "event_id": "wp-11363-04:fv-01",
    "type": "finding_raised",
    "finding_id": "F1",
    "severity": "medium",
    "blocking": false,
    "title": "manifest.observations contradicts manifest.platform_attachment_probes (figure byte status/hash)"
   },
   {
    "event_id": "wp-11363-04:fv-02",
    "type": "finding_raised",
    "finding_id": "F3",
    "severity": "high",
    "blocking": true,
    "title": "envelope kf_result.json fails the canonical schema: top-level 'claims' is an additional property (additionalProperties=false) — the declared schema_pass is not reproducible with schemas/kf_result.v1.schema.json"
   },
   {
    "event_id": "wp-11363-04:fv-03",
    "type": "finding_raised",
    "finding_id": "F5",
    "severity": "low",
    "blocking": false,
    "title": "'verified' tokens in the package are quote-resolution flags (quote_verified / all_verified), which a naive scanner can misread as claim verification"
   },
   {
    "event_id": "wp-11363-04:fv-04",
    "type": "finding_raised",
    "finding_id": "F2",
    "severity": "low",
    "blocking": false,
    "title": "artefacts cited outside the audit-chain line are registered only implicitly (no per-file asset row, no further_occurrences entry)"
   },
   {
    "event_id": "wp-11363-04:ev-90",
    "type": "verdict",
    "verdict": "needs-fix",
    "blocking_findings": [
     "F3"
    ],
    "non_blocking_findings": [
     "F4",
     "F1",
     "F5",
     "F2"
    ]
   },
   {
    "event_id": "wp-11363-04:ev-91",
    "type": "no_verified_marks",
    "verified_marks": 0,
    "note": "verification is computed by the platform gate"
   }
  ]
 }
}
```
