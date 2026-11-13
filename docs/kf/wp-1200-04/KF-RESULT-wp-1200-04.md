# KF-RESULT wp-1200-04

**独立审核（04）· 被审对象 wp-1200-01（01-asset-registration，report 1200）· 判定：needs-fix**

## ① 本工序做了什么

对 report_id=1200 的上游工作包 `wp-1200-01`（01 资产登记，结果报告 14598）做独立红队审核：
不看生产者解释，只用「原文 + 平台记录 + 上游结果 JSON 块」重建事实，逐条判定其登记面（源身份、locator、
附件可达性、claim 引文、计数、状态词表）是否成立，并给出 pass/fail/needs-fix。

判定 **needs-fix**：源身份与定位面全过：sha256 逐字节重算一致（3612 chars / 5396 bytes）、21 个 locator 独立重切零偏差、10 条 claim 引文逐字且数字全部可在引文中追溯、无 verified 宣称、8 个附件一律老实标 resolvable=false。判 needs-fix 的唯一实质缺陷是 F1：平台记录声明的唯一结果图（schema_drift_coverage.png）既未登记也未标不可达，而独立探测该图 HTTP 404——①工序「登记+可达性标注」的职责在此漏了一项。F2/F3 为集合口径与词表一致性问题。

- 源身份：`sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48`（重算，与契约逐字节一致），
  3612 chars / 5396 bytes / 53 行。
- 证据绑定：21 个 locator 独立重切零偏差（`c4`）；10 条 claim 引文全部逐字、
  数字 24/24 可在其引文中追溯（`c5`/`c5b`）；`stats` 由列表长度与状态重算后与声明完全一致（`c6`）。
- 关键缺陷 **F1**：平台记录声明的唯一结果图 `schema_drift_coverage.png` 未被登记、也未标不可达，
  独立探测 `http://127.0.0.1:8010/api/v1/tensor/reports/1200/figures/schema_drift_coverage.png` 返回 **HTTP 404**
  （`{"detail":"figure not found"}`）。
- 结论未标 verified：`verified`/`verification_status` 在结果信封中出现 **0** 次（规则 `c7`）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文字节**：`GET http://127.0.0.1:8010/api/v1/tensor/reports/1200` → `markdown`，
   落盘 `artifacts/wp-1200-04/source_report_1200.md`，独立重算 sha256 并与契约比对（不一致即判失败，不做「跳过」）。
2. **取被审对象**：`GET /tensor/reports/14598`（KF-RESULT wp-1200-01），**只程序化抽取其中唯一一个 fenced json 代码块**
   （正则逐块抽取，块数=1 已断言），保存为
   `artifacts/wp-1200-04/subject_wp-1200-01_envelope.json`；散文段落未解析、未引用（上下文隔离要求）。
3. **上下文隔离**：审核者 mission 15819 ≠ 生产者 mission 15523；
   审核提示词由本工序自建（未复制生产 prompt）；未采用生产者自述作为任何 finding 的依据。
4. **重定位**：对 manifest 的 21 个 locator 逐条**独立重切**——
   偏移切片必须与 quote 字节相等、行号跨度自洽、quote 必须在原文中可检索（不信任上游给出的 offset）。
5. **可达性探测**：对平台记录 `figures[]` 逐项 `GET /tensor/reports/1200/figures/<name>`，
   记录 HTTP 码与字节数；8 个仓库路径属 TensorPlatform，按边界不跨仓取证，未把它们标成可达。
6. **计数重算**：`stats.*` 全部由列表长度/状态重算后比对（declared vs derived）。
7. **一键复跑**：`python3 artifacts/wp-1200-04/verify_review.py --check`（离线可跑，输入全在工作树内）；
   图：`python3 artifacts/wp-1200-04/make_figure.py`；本文件：`python3 artifacts/wp-1200-04/render_report.py`。

## ③ 产出物清单

| 工件 | 要点 |
|---|---|
| `artifacts/wp-1200-04/review_report.json` | 交付物（kf-review-report.v1）：16 条 checks、3 条 findings、5 条 not_run、verdict=needs-fix |
| `artifacts/wp-1200-04/kf_result_wp-1200-04.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），过 `schemas/kf_result.v1.schema.json` |
| `artifacts/wp-1200-04/review_events.json`（信封内 outputs） | 审核轴事件：request-changes（in-review→draft），findings 随事件留痕；未触碰 epistemic/verification 轴 |
| `artifacts/wp-1200-04/checks_log.json` | 逐条 check 的机器可读证据轨迹 |
| `artifacts/wp-1200-04/verify_review.py` | 复核器（不引用上游生成器常量，全部重算） |
| `artifacts/wp-1200-04/platform_probe.json` | 平台读取快照：report 1200 记录、其 figures 探测结果、两条 mission 的时间与状态 |
| `artifacts/wp-1200-04/subject_wp-1200-01_envelope.json` | 被审对象（上游结果 JSON 块原样） |
| `artifacts/wp-1200-04/source_report_1200.md` + `source_1200.sha256` | 源字节与其哈希（3612 chars） |
| `artifacts/wp-1200-04/review_coverage.png` | 图：证据绑定重切结果 + 登记覆盖率（F1/F2 的缺口可视化） |
| `docs/kf/wp-1200-04/KF-RESULT-wp-1200-04.md` | 本报告（唯一一个 json 块=结果信封） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段/断言 | 原文引文（逐字） | 字符区间 | quote sha256 | 命中 | 备注 |
|---|---|---|---|---|---|
| source_identity.source_hash | `# m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告` | 0–67 | c6a2769c0f26… | ✓ | H1=manifest.title |
| F1 / ④ 结果图 | `## ④ 结果图⏎左：迁移文件应用数 9→19；右：CI 签名点名的列在测试库中的存在性（1=present）。` | 2598–2654 | be3754df8743… | ✓ | 图只在平台记录 figures 留名 |
| F2 / 判据表 #1 | `\| 1 \| tensor_dev_missions.report_id \| 096_report_gate.sql:12 \| 有 \| 缺 \|` | 499–569 | f50bba9d11f3… | ✓ | 096 未进 attachments |
| F2 / 判据表 #3 | `\| 3 \| tensor_dev_missions.fail_stage \| 095_mission_lifecycle.sql:35 \| 有 \| 缺 \|` | 673–750 | 75fcbce4f89b… | ✓ | 095 未进 attachments |
| F2 / 判据表 #7 | `\| 7 \| campaign_plans.name \| 095_campaign_plans.sql / 097 \| 有 \| 整表缺 \|` | 997–1065 | ab5ff0e65c8d… | ✓ | 095 未进 attachments |
| metric:mig_files | `\| 应用到测试库的迁移文件数 \| 9 \| 19 \|` | 2407–2432 | 66c760d9e92b… | ✓ | 04 复核同源 |
| metric:tables | `\| `public` schema 表数 \| 15 \| 43 \|` | 2433–2465 | 564ea9d896b2… | ✓ | 04 复核同源 |
| metric:missing_cols | `\| 签名 8 个 schema 元素缺失数 \| 8 \| 0 \|` | 2466–2497 | 9e6dea52a1d2… | ✓ | 04 复核同源 |
| metric:factory_tests | `\| `tests/factory` 结果 \| 5 FAILED（report_id / fail_stage UndefinedColumn） \| **168 passe…` | 2498–2596 | 1ad1c69e84db… | ✓ | 04 复核同源 |

平台侧数值（非 markdown，来自 `platform_probe.json`）：
`report_record.figures` 命中 1 项（name=schema_drift_coverage.png）、`figure_probe.status=404`、
`report_record.chars=3612`、producer_mission=15523/succeeded、
reviewer_mission=15819/running。

## ⑤ 注意点与局限

### 被判缺陷（按严重度）

### F1 · 平台记录声明的唯一结果图未登记为资产，可达性也未标注（实测 HTTP 404）

- 严重度：**medium**；blocking：**True**
- 被审断言：outputs.asset_manifest.json: attachments[] 共 8 项 + stats.attachments_resolvable=0，即「本报告的资产已登记完毕、可达性已知」
- 影响：①工序的职责是「登记资产并标注不可达」。报告的④结果图只在平台记录 figures 里留名，正文未写文件名，因此 manifest 里既没有该资产、也没有 unreachable(404) 标记；下游 03/05 无从得知该报告的图示字节缺失，结果图相关结论无法被证据绑定。
- 修复建议：在 attachments 中补一条 {kind:'figure', ref:'schema_drift_coverage.png', resolvable:false, status:'unreachable', probe:'HTTP 404 figure not found', probe_url:...}；stats.attachments_listed 8→9。

### F2 · 判据表点名 3 个迁移 SQL 文件未进 attachments（仅以 declared_by_migration 文本出现）

- 严重度：**low**；blocking：**False**
- 被审断言：attachments[] = 8 项，与「本报告引用的仓库工件」全集
- 影响：这三个文件是「声明列」的根因证据（096/095/095）。它们在 registered_schema_elements.declared_by_migration 里以自由文本出现，未按附件口径登记（无 asset_id/kind/resolvable），附件清单因此不是可查询集合的完备表示。
- 修复建议：在 attachments 补 096_report_gate.sql / 095_mission_lifecycle.sql / 095_campaign_plans.sql，或声明「migration 文件由 registered_schema_elements.declared_by_migration 承载，不进 attachments」的口径。

### F3 · claim 状态词表使用不一致：引文全覆盖的报告自述，一条标 supported、一条标 partially-supported

- 严重度：**low**；blocking：**False**
- 被审断言：claims[].status 的语义（supported 是否=独立确认）
- 影响：两处对比说明 status 字段混用了两种口径（引文覆盖度 vs 独立可验证度）。本 manifest 在 unresolved[] 里披露了「claims 仅为报告原文陈述的登记定位，不含独立复核结论」，因此不构成虚假声明；但下游无法用该字段做机器判定。
- 修复建议：在 manifest 增 status_semantics 字段（例如 supported='引文逐字覆盖且仅登记原文陈述'），或把 c09 同 c08 一样标 partially-supported。

### 下游须知（非阻塞）

- **D1**（blocking=False）：正文的 commit 短哈希 / PR 号 / 日期只出现在 attachments[].mentioned_at 的整行切片引文里（c11 判定为可追溯），manifest 没有为它们建结构化索引（无 asset/metric 条目）——03 抽取必须自建 locator，不得把整行切片当单点证据。
- **D2**（blocking=False）：manifest.source.title 取的是 H1（「m1625 — …修复报告」），而平台记录/契约 title 是「m1625 · …（5 FAILED → 168 passed）」。两者措辞不同、都逐字存在于平台记录，manifest 只留 H1。下游若做 title 等值校验会误报，建议同时记 record_title。
- **D3**（blocking=False）：report 1200 的 ⑥ 自评「关键量是否 <3% = 是」是离散一致性判据下的自评（8→0、5→0），非连续物理量误差；本审核不重复其结论真伪（未跑 TensorPlatform 测试），只确认该自评在文中逐字存在且被标为自评。

### 未做的检查（not_run，不当作通过）

- `n1_tensorplatform_tests`：边界：本审核只碰 report 1200 与本仓；TensorPlatform 的 tests/factory 168 passed 无法在本仓复跑，未复核（不判真伪）。
- `n2_gate_ledger`：tk_work_packages 对当前角色 permission denied；上游完成度以 mission 15523 status=succeeded + 报告 14598 可取回来判定。
- `n3_attachment_bytes`：8 个附件路径属 TensorPlatform 仓，跨仓不取证；沿用上游 conservative 的 resolvable=false，未逐字节核验。
- `n4_strong_model_sample`：抽样强模型复核属平台调度（GATE-RULES M6 未实现）。
- `n5_cross_report`：边界硬约束：不得读其它 report_id，未与同族报告对表。

### 口径问题

- `stats` 重算：declared `{'attachments_listed': 8, 'attachments_resolvable': 0, 'schema_elements_registered': 8, 'claims_total': 10, 'claims_supported': 8, 'claims_partially_supported': 1, 'claims_unresolved': 1, 'claims_refuted': 0}` vs derived `{'attachments_listed': 8, 'attachments_resolvable': 0, 'schema_elements_registered': 8, 'claims_total': 10, 'claims_supported': 8, 'claims_partially_supported': 1, 'claims_unresolved': 1, 'claims_refuted': 0}` → 完全一致（清单长度与状态计数均被独立复算）。
- 上游 manifest 的 `source.title` 取 H1，与平台记录/契约 title 措辞不同（D2）；这在「零手抄」下是合法选择，但下游做 title 等值校验会误报。
- 本审核**不**判定 report 1200 的技术结论真伪（TensorPlatform 的 tests/factory 168 passed 无法在本仓复跑），只判定其被登记方式是否忠实。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✓ | 信封与 review_report.json 均 `json.loads` 通过；`jsonschema` 校验 `schemas/kf_result.v1.schema.json` 通过 |
| schema_pass | ✓ | 同上（Draft 2020-12） |
| reviewer_independent | ✓ | reviewer 15819 ≠ producer 15523；未复用生产 prompt |
| upstream_packages_completed | ✓ | mission 15523 status=succeeded；结果报告 14598 可取回（门禁台账 `tk_work_packages` 对当前角色 permission denied → 该行记 not_run，未当成通过） |
| do_not_mark_claims_as_verified | ✓ | 信封内 `verified`/`verification_status` 命中 0；verification 轴留给平台门 |
| reviewer_context_excludes_producer_explanation | ✓ | 只解析上游报告的单一 fenced json 代码块；散文未解析（局限见 independence.limitation） |
| review_prompt_not_copied_from_producer | ✓ | 审核提示面=本报告 ②，独立撰写 |

**诚实项**：本单没有把任何上游结论标成 verified；F1 的 404 是本审核自己探测得到的，
但**未**验证 report 1200 的技术修复本身（无法在本仓复跑），该部分如实记 not_run。

### 逐条 check 轨迹

| check | 名称 | 结果 | detail |
|---|---|---|---|
| c1_source_identity | source_hash 逐字节重算与契约一致 | PASS | recomputed=sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48 contract=sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ed |
| c2_metadata_fidelity | manifest 的 sha256/chars/bytes/line_count/title 与独立重算一致且 title 逐字等于 H1 | PASS | sha=True chars=3612/3612 bytes=5396/5396 lines=53/53 title==H1:True (H1='m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告') |
| c2b_title_wording | manifest.title 取 H1；平台记录 title / 契约 title 与 H1 措辞不同，manifest 未记录该差异 | PASS | H1='m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告' record_title='m1625 · tests/factory schema 漂移根因与修复：手写迁移清单 vs 生产 glob（5 FAILED → 168 passe |
| c3_subject_frame_integrity | 上游结果信封：package_id/task_type/report_id/provenance.source_hash 自洽 | PASS | package=wp-1200-01 task=01-asset-registration report=1200 hash_match=True |
| c4_locators_resolvable | 全部 locator 独立重切：偏移切片 == quote（字节相等） | PASS | 21 locators checked, failures={} |
| c5_claim_evidence_verbatim | 每条 claim 的 evidence 引文逐字存在于原文 | PASS | claims=10 not-verbatim=[] |
| c5b_claim_numbers_traced | claim 文本里的每个数字都出现在其引文中（零手抄） | PASS | untraced=[] |
| c6_counts_consistent | manifest.stats 与列表长度/状态计数一致（独立重算） | PASS | declared={'attachments_listed': 8, 'attachments_resolvable': 0, 'schema_elements_registered': 8, 'claims_total': 10, 'claims_supported': 8, 'claims_partially_su |
| c7_no_verified_marking | 信封内无 verified / verification_status 宣称；unresolved 均带理由 | PASS | tokens=[] unresolved_with_reason=True |
| c8_attachment_reachability_honest | 8 个附件一律 resolvable=false（跨仓不取证），无「取不到字节却标可达」 | PASS | listed=8 resolvable=0 |
| c9_platform_figure_registered | 平台记录里声明的结果图被登记为资产（或显式标不可达） | FAIL | record figures=['schema_drift_coverage.png'] unregistered=['schema_drift_coverage.png'] probe={'url': 'http://127.0.0.1:8010/api/v1/tensor/reports/1200/figures/ |
| c10_prose_paths_registered | 正文出现的仓库路径全部登记（附件 refs 或结构化字段） | PASS | paths_in_prose=14 unregistered=[] |
| c11_provenance_anchors | 正文的 commit / PR 锚点可在结构化字段中追溯 | PASS | anchors=9 untracked=[] |
| c12_status_vocabulary_consistency | 同一「引文全覆盖但仅报告自述」的 claim 集合使用一致状态标签 | FAIL | fully_quoted_but_partial=['wp-1200-01-c08'] coverage={'wp-1200-01-c01': ('supported', 1.0), 'wp-1200-01-c02': ('supported', 1.0), 'wp-1200-01-c03': ('supported' |
| c13_reviewer_independent | 审核者 mission ≠ 生产者 mission，且审核者未参与该包生产 | PASS | reviewer=15819 producer=15523 |
| c14_upstream_completed | 上游包任务轴 = succeeded，且其结果报告（JSON 块）可取回 | PASS | producer_mission.status=succeeded finished_at=2026-11-12T00:56:37.012920+00:00 subject_result_report_id=14598 gate_record=not_run (tk_work_packages 不可读: permiss |

## repro_cmd

```bash
cd "$(git rev-parse --show-toplevel)" && python3 artifacts/wp-1200-04/verify_review.py --check && python3 artifacts/wp-1200-04/make_figure.py && python3 artifacts/wp-1200-04/render_report.py && python3 -m pytest tests/test_kf_wp_1200_04_review.py -q
```

## 结果信封

```json
{
 "package_id": "wp-1200-04",
 "task_type": "04-independent-review",
 "report_id": "1200",
 "provenance": {
  "source_uri": "tensor://reports/1200",
  "source_field": "markdown",
  "source_hash": "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48",
  "producer": "agent/m15819 (TensorKnowledge)",
  "emitted_at": "2026-11-12T02:36:33.317291+00:00",
  "reviewed_package_id": "wp-1200-04",
  "subject_package_id": "wp-1200-01",
  "subject_result_report_id": 14598,
  "reviewed_source_hash": "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48",
  "notes": "independent review only; no conclusion marked verified; verification axis left to platform gate"
 },
 "outputs": {
  "review_report.json": {
   "schema": "kf-review-report.v1",
   "reviewed_package_id": "wp-1200-04",
   "subject_package_id": "wp-1200-01",
   "reviewed_task_type": "01-asset-registration",
   "subject_result_report_id": 14598,
   "gate_interop": {
    "r2_reviews_this_package": "审核单与被审单不同：platform 的 r2 review_gate 把 04 行当作 pkg 传入，故 reviewed_package_id 按门口径=本审核单 wp-1200-04，真正被审对象见 subject_package_id=wp-1200-01。",
    "review_axis_effect": "本审对上游包提出 request-changes（needs-fix）；review_events.json 仅写审核轴，不改任何 epistemic_status / verification_status（A3 三状态分离）。"
   },
   "report_id": "1200",
   "reviewer_mission_id": 15819,
   "producer_mission_id": 15523,
   "reviewer_role": "red-team-reviewer",
   "verdict": "needs-fix",
   "verdict_reason": "源身份与定位面全过：sha256 逐字节重算一致（3612 chars / 5396 bytes）、21 个 locator 独立重切零偏差、10 条 claim 引文逐字且数字全部可在引文中追溯、无 verified 宣称、8 个附件一律老实标 resolvable=false。判 needs-fix 的唯一实质缺陷是 F1：平台记录声明的唯一结果图（schema_drift_coverage.png）既未登记也未标不可达，而独立探测该图 HTTP 404——①工序「登记+可达性标注」的职责在此漏了一项。F2/F3 为集合口径与词表一致性问题。",
   "independence": {
    "context_used": [
     "report 1200 markdown (source bytes, hashed)",
     "platform report record 1200 (title / scenario_key / figures)",
     "subject envelope JSON block from report 14598 (outputs + provenance + claims)",
     "platform mission records 15523 / 15819 (status, timestamps)"
    ],
    "producer_explanation_used_for_findings": false,
    "limitation": "报告 14598 的 markdown 含生产者的过程散文；本审核只程序化抽取其中唯一一个 fenced json 块，未解析、未引用其散文部分；严格做法应只取结果 JSON 文件本体（该分支尚未合入本仓）。",
    "review_prompt_copied_from_producer": false,
    "tools": [
     "python3 + hashlib/json/re（逐字定位、偏移重切、计数重算）",
     "TensorPlatform REST API（/tensor/reports/1200, /14598, /missions, /reports/1200/figures/…）"
    ]
   },
   "checks": [
    {
     "id": "c1_source_identity",
     "name": "source_hash 逐字节重算与契约一致",
     "status": "pass",
     "detail": "recomputed=sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48 contract=sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48 chars=3612 bytes=5396 lines=53"
    },
    {
     "id": "c2_metadata_fidelity",
     "name": "manifest 的 sha256/chars/bytes/line_count/title 与独立重算一致且 title 逐字等于 H1",
     "status": "pass",
     "detail": "sha=True chars=3612/3612 bytes=5396/5396 lines=53/53 title==H1:True (H1='m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告')"
    },
    {
     "id": "c2b_title_wording",
     "name": "manifest.title 取 H1；平台记录 title / 契约 title 与 H1 措辞不同，manifest 未记录该差异",
     "status": "pass",
     "detail": "H1='m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告' record_title='m1625 · tests/factory schema 漂移根因与修复：手写迁移清单 vs 生产 glob（5 FAILED → 168 passed）'"
    },
    {
     "id": "c3_subject_frame_integrity",
     "name": "上游结果信封：package_id/task_type/report_id/provenance.source_hash 自洽",
     "status": "pass",
     "detail": "package=wp-1200-01 task=01-asset-registration report=1200 hash_match=True"
    },
    {
     "id": "c4_locators_resolvable",
     "name": "全部 locator 独立重切：偏移切片 == quote（字节相等）",
     "status": "pass",
     "detail": "21 locators checked, failures={}"
    },
    {
     "id": "c5_claim_evidence_verbatim",
     "name": "每条 claim 的 evidence 引文逐字存在于原文",
     "status": "pass",
     "detail": "claims=10 not-verbatim=[]"
    },
    {
     "id": "c5b_claim_numbers_traced",
     "name": "claim 文本里的每个数字都出现在其引文中（零手抄）",
     "status": "pass",
     "detail": "untraced=[]"
    },
    {
     "id": "c6_counts_consistent",
     "name": "manifest.stats 与列表长度/状态计数一致（独立重算）",
     "status": "pass",
     "detail": "declared={'attachments_listed': 8, 'attachments_resolvable': 0, 'schema_elements_registered': 8, 'claims_total': 10, 'claims_supported': 8, 'claims_partially_supported': 1, 'claims_unresolved': 1, 'claims_refuted': 0} derived={'attachments_listed': 8, 'attachments_resolvable': 0, 'schema_elements_registered': 8, 'claims_total': 10, 'claims_supported': 8, 'claims_partially_supported': 1, 'claims_unresolved': 1, 'claims_refuted': 0}"
    },
    {
     "id": "c7_no_verified_marking",
     "name": "信封内无 verified / verification_status 宣称；unresolved 均带理由",
     "status": "pass",
     "detail": "tokens=[] unresolved_with_reason=True"
    },
    {
     "id": "c8_attachment_reachability_honest",
     "name": "8 个附件一律 resolvable=false（跨仓不取证），无「取不到字节却标可达」",
     "status": "pass",
     "detail": "listed=8 resolvable=0"
    },
    {
     "id": "c9_platform_figure_registered",
     "name": "平台记录里声明的结果图被登记为资产（或显式标不可达）",
     "status": "fail",
     "detail": "record figures=['schema_drift_coverage.png'] unregistered=['schema_drift_coverage.png'] probe={'url': 'http://127.0.0.1:8010/api/v1/tensor/reports/1200/figures/schema_drift_coverage.png', 'name': 'schema_drift_coverage.png', 'status': 404, 'bytes': 0, 'detail': '{\"detail\":\"figure not found\"}'}"
    },
    {
     "id": "c10_prose_paths_registered",
     "name": "正文出现的仓库路径全部登记（附件 refs 或结构化字段）",
     "status": "pass",
     "detail": "paths_in_prose=14 unregistered=[]"
    },
    {
     "id": "c11_provenance_anchors",
     "name": "正文的 commit / PR 锚点可在结构化字段中追溯",
     "status": "pass",
     "detail": "anchors=9 untracked=[]"
    },
    {
     "id": "c12_status_vocabulary_consistency",
     "name": "同一「引文全覆盖但仅报告自述」的 claim 集合使用一致状态标签",
     "status": "fail",
     "detail": "fully_quoted_but_partial=['wp-1200-01-c08'] coverage={'wp-1200-01-c01': ('supported', 1.0), 'wp-1200-01-c02': ('supported', 1.0), 'wp-1200-01-c03': ('supported', 1.0), 'wp-1200-01-c04': ('supported', 1.0), 'wp-1200-01-c05': ('supported', 1.0), 'wp-1200-01-c06': ('supported', 1.0), 'wp-1200-01-c07': ('supported', 1.0), 'wp-1200-01-c08': ('partially-supported', 1.0), 'wp-1200-01-c09': ('supported', 1.0), 'wp-1200-01-c10': ('unresolved', 1.0)}"
    },
    {
     "id": "c13_reviewer_independent",
     "name": "审核者 mission ≠ 生产者 mission，且审核者未参与该包生产",
     "status": "pass",
     "detail": "reviewer=15819 producer=15523"
    },
    {
     "id": "c14_upstream_completed",
     "name": "上游包任务轴 = succeeded，且其结果报告（JSON 块）可取回",
     "status": "pass",
     "detail": "producer_mission.status=succeeded finished_at=2026-11-12T00:56:37.012920+00:00 subject_result_report_id=14598 gate_record=not_run (tk_work_packages 不可读: permission denied)"
    }
   ],
   "findings": [
    {
     "id": "F1",
     "severity": "medium",
     "blocking": true,
     "title": "平台记录声明的唯一结果图未登记为资产，可达性也未标注（实测 HTTP 404）",
     "claim_under_review": "outputs.asset_manifest.json: attachments[] 共 8 项 + stats.attachments_resolvable=0，即「本报告的资产已登记完毕、可达性已知」",
     "evidence": [
      {
       "quote": "## ④ 结果图\n左：迁移文件应用数 9→19；右：CI 签名点名的列在测试库中的存在性（1=present）。",
       "occurrences": 1,
       "start_offset": 2598,
       "end_offset": 2654,
       "line_start": 41,
       "line_end": 42,
       "chars": 56,
       "quote_sha256": "be3754df8743d544c44edd9056f1ac763bca0923a6d635e7b9c1be9784277c63"
      },
      {
       "source": "platform",
       "probe": {
        "url": "http://127.0.0.1:8010/api/v1/tensor/reports/1200/figures/schema_drift_coverage.png",
        "name": "schema_drift_coverage.png",
        "status": 404,
        "bytes": 0,
        "detail": "{\"detail\":\"figure not found\"}"
       },
       "note": "GET /api/v1/tensor/reports/1200/figures/schema_drift_coverage.png"
      }
     ],
     "why_it_matters": "①工序的职责是「登记资产并标注不可达」。报告的④结果图只在平台记录 figures 里留名，正文未写文件名，因此 manifest 里既没有该资产、也没有 unreachable(404) 标记；下游 03/05 无从得知该报告的图示字节缺失，结果图相关结论无法被证据绑定。",
     "remediation": "在 attachments 中补一条 {kind:'figure', ref:'schema_drift_coverage.png', resolvable:false, status:'unreachable', probe:'HTTP 404 figure not found', probe_url:...}；stats.attachments_listed 8→9。"
    },
    {
     "id": "F2",
     "severity": "low",
     "blocking": false,
     "title": "判据表点名 3 个迁移 SQL 文件未进 attachments（仅以 declared_by_migration 文本出现）",
     "claim_under_review": "attachments[] = 8 项，与「本报告引用的仓库工件」全集",
     "evidence": [
      {
       "quote": "| 1 | tensor_dev_missions.report_id | 096_report_gate.sql:12 | 有 | 缺 |",
       "occurrences": 1,
       "start_offset": 499,
       "end_offset": 569,
       "line_start": 15,
       "line_end": 15,
       "chars": 70,
       "quote_sha256": "f50bba9d11f3b71f84ff773cd9bb198377c74876ae68d6e16e17194863b10e67"
      },
      {
       "quote": "| 3 | tensor_dev_missions.fail_stage | 095_mission_lifecycle.sql:35 | 有 | 缺 |",
       "occurrences": 1,
       "start_offset": 673,
       "end_offset": 750,
       "line_start": 17,
       "line_end": 17,
       "chars": 77,
       "quote_sha256": "75fcbce4f89bdf90a0ec34a87a75aaa6821aae55bf8da27fa08e4ff7c51c8bd8"
      },
      {
       "quote": "| 7 | campaign_plans.name | 095_campaign_plans.sql / 097 | 有 | 整表缺 |",
       "occurrences": 1,
       "start_offset": 997,
       "end_offset": 1065,
       "line_start": 21,
       "line_end": 21,
       "chars": 68,
       "quote_sha256": "ab5ff0e65c8d254d26574e6e1acab77c2d8aa4cfe3361973e2c674337c495d1b"
      }
     ],
     "why_it_matters": "这三个文件是「声明列」的根因证据（096/095/095）。它们在 registered_schema_elements.declared_by_migration 里以自由文本出现，未按附件口径登记（无 asset_id/kind/resolvable），附件清单因此不是可查询集合的完备表示。",
     "remediation": "在 attachments 补 096_report_gate.sql / 095_mission_lifecycle.sql / 095_campaign_plans.sql，或声明「migration 文件由 registered_schema_elements.declared_by_migration 承载，不进 attachments」的口径。"
    },
    {
     "id": "F3",
     "severity": "low",
     "blocking": false,
     "title": "claim 状态词表使用不一致：引文全覆盖的报告自述，一条标 supported、一条标 partially-supported",
     "claim_under_review": "claims[].status 的语义（supported 是否=独立确认）",
     "evidence": [
      {
       "source": "subject envelope",
       "pointer": "outputs.asset_manifest.json.claims[wp-1200-01-c09]",
       "status": "supported",
       "quote": "本单判据为**二值一致性**，无可比标量基准：签名 schema 元素缺失数 8 → 0（等价误差 0/8 项 = 0%）；`tests/factory` 失败 5 → 0（等价误差 0%）。变异验证：把手写清单还原后新守护测试 3 failed 并逐列点名缺失列，证明门禁有效。因此「关键量是否 <3%」= **是（0%，且为离散一致性判据，不是连续物理量）**；连续量误差不适用，原因：本任务为 CI/schema 契约修复，不产生物理场量或标量基准。",
       "note": "c09 是对报告自评（<3% 判定）的登记，与 c08 同属「无法独立复核的报告自述」"
      },
      {
       "source": "subject envelope",
       "pointer": "outputs.asset_manifest.json.claims[wp-1200-01-c08]",
       "status": "partially-supported",
       "quote": "- `backend/tests` 抽样：test_abtest_unit/test_audit_unit/test_agent_routing/test_tensor_repro_redteam 全绿；test_alert_unit/test_api_key_unit 在净树上同样 FAILED（`'Depends' object has no attribute 'query'`，本地 FastAPI 0.136 依赖注入版本漂移，预存在）；test_auth_guard 缺 pytest-asyncio；24 模块因离线缺 redis 等包 collection ERROR——均为环境限制，非本改动引入。",
       "note": "c08 引文完整覆盖其 claim 文本，却被标 partially-supported"
      }
     ],
     "why_it_matters": "两处对比说明 status 字段混用了两种口径（引文覆盖度 vs 独立可验证度）。本 manifest 在 unresolved[] 里披露了「claims 仅为报告原文陈述的登记定位，不含独立复核结论」，因此不构成虚假声明；但下游无法用该字段做机器判定。",
     "remediation": "在 manifest 增 status_semantics 字段（例如 supported='引文逐字覆盖且仅登记原文陈述'），或把 c09 同 c08 一样标 partially-supported。"
    }
   ],
   "overstated_claims": [
    "stats.attachments_resolvable=0 的「可达性已知」口径：报告的唯一结果图未登记，故「已登记完毕」不成立（F1）。",
    "claims[].status=supported 被 c09 用于一条仅报告自述的自评（<3% = 是），与 c08 的 partially-supported 口径冲突（F3）。"
   ],
   "checks_not_run": [
    {
     "id": "n1_tensorplatform_tests",
     "why": "边界：本审核只碰 report 1200 与本仓；TensorPlatform 的 tests/factory 168 passed 无法在本仓复跑，未复核（不判真伪）。"
    },
    {
     "id": "n2_gate_ledger",
     "why": "tk_work_packages 对当前角色 permission denied；上游完成度以 mission 15523 status=succeeded + 报告 14598 可取回来判定。"
    },
    {
     "id": "n3_attachment_bytes",
     "why": "8 个附件路径属 TensorPlatform 仓，跨仓不取证；沿用上游 conservative 的 resolvable=false，未逐字节核验。"
    },
    {
     "id": "n4_strong_model_sample",
     "why": "抽样强模型复核属平台调度（GATE-RULES M6 未实现）。"
    },
    {
     "id": "n5_cross_report",
     "why": "边界硬约束：不得读其它 report_id，未与同族报告对表。"
    }
   ],
   "downstream_notes": [
    {
     "id": "D1",
     "blocking": false,
     "note": "正文的 commit 短哈希 / PR 号 / 日期只出现在 attachments[].mentioned_at 的整行切片引文里（c11 判定为可追溯），manifest 没有为它们建结构化索引（无 asset/metric 条目）——03 抽取必须自建 locator，不得把整行切片当单点证据。",
     "evidence": [
      {
       "source": "recomputed",
       "anchors": [
        "0e7686f",
        "1f5f711",
        "2ea470b",
        "2f7d2fe",
        "966ea2e",
        "PR #16",
        "PR #223",
        "PR #229",
        "dd66cb0c"
       ],
       "untracked": []
      }
     ]
    },
    {
     "id": "D2",
     "blocking": false,
     "note": "manifest.source.title 取的是 H1（「m1625 — …修复报告」），而平台记录/契约 title 是「m1625 · …（5 FAILED → 168 passed）」。两者措辞不同、都逐字存在于平台记录，manifest 只留 H1。下游若做 title 等值校验会误报，建议同时记 record_title。",
     "evidence": [
      {
       "source": "platform",
       "record_title": "m1625 · tests/factory schema 漂移根因与修复：手写迁移清单 vs 生产 glob（5 FAILED → 168 passed）",
       "manifest_title": "m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告"
      }
     ]
    },
    {
     "id": "D3",
     "blocking": false,
     "note": "report 1200 的 ⑥ 自评「关键量是否 <3% = 是」是离散一致性判据下的自评（8→0、5→0），非连续物理量误差；本审核不重复其结论真伪（未跑 TensorPlatform 测试），只确认该自评在文中逐字存在且被标为自评。",
     "evidence": [
      {
       "quote": "本单判据为**二值一致性**，无可比标量基准：签名 schema 元素缺失数 8 → 0（等价误差 0/8 项 = 0%）",
       "occurrences": 1,
       "start_offset": 3383,
       "end_offset": 3444,
       "line_start": 52,
       "line_end": 52,
       "chars": 61,
       "quote_sha256": "eb9d8975bf7c703b32bf6a6c771c315293fa67288e7111a43fc979618772bd11"
      }
     ]
    }
   ],
   "source_identity": {
    "report_id": "1200",
    "chars": 3612,
    "bytes_utf8": 5396,
    "lines": 53,
    "source_hash_recomputed": "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48",
    "source_hash_contract": "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48",
    "source_hash_matches": true,
    "title_record": "m1625 · tests/factory schema 漂移根因与修复：手写迁移清单 vs 生产 glob（5 FAILED → 168 passed）",
    "scenario_key_record": "tensorplatform_ci_quality",
    "markdown_h1": "# m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告",
    "title_matches_h1_verbatim": true
   },
   "subject_manifest_snapshot": {
    "package_id": "wp-1200-01",
    "task_type": "01-asset-registration",
    "manifest_version": "1.0",
    "stats": {
     "attachments_listed": 8,
     "attachments_resolvable": 0,
     "schema_elements_registered": 8,
     "claims_total": 10,
     "claims_supported": 8,
     "claims_partially_supported": 1,
     "claims_unresolved": 1,
     "claims_refuted": 0
    },
    "stats_recomputed": {
     "attachments_listed": 8,
     "attachments_resolvable": 0,
     "schema_elements_registered": 8,
     "claims_total": 10,
     "claims_supported": 8,
     "claims_partially_supported": 1,
     "claims_unresolved": 1,
     "claims_refuted": 0
    },
    "attachment_refs": [
     "094_factory_soul.sql",
     "097_campaign_plans_superset.sql",
     "artifacts/m1625/probe_schema.py",
     "artifacts/m1625/schema_coverage.json",
     "backend/migrations/run_migration.py",
     "backend/services/factory_bootstrap.py",
     "tests/factory/conftest.py",
     "tests/factory/test_schema_migrations.py"
    ],
    "unresolved": [
     "附件可解析性（8 项）均为 unknown/unresolved：路径属 TensorPlatform 仓，本工序不跨仓取证。",
     "报告 c10 声明的生产库 schema_migrations / alembic 关系未审计，本工序保持未决。",
     "本工序不做抽取，claims 仅为报告原文陈述的登记定位，不含独立复核结论。"
    ]
   },
   "subject_provenance": {
    "source_hash": "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48",
    "source_field": "markdown",
    "producer": "agent m15523 / wp-1200-01 (TensorKnowledge)",
    "emitted_at": "2026-11-12T00:54:56+00:00",
    "notes": "asset registration only; quotes are programmatic line-slices of the source markdown; no extraction, no verification marking"
   },
   "platform_probe": {
    "report_record": {
     "id": 1200,
     "title": "m1625 · tests/factory schema 漂移根因与修复：手写迁移清单 vs 生产 glob（5 FAILED → 168 passed）",
     "scenario_key": "tensorplatform_ci_quality",
     "figures": [
      {
       "name": "schema_drift_coverage.png",
       "caption": "左：测试库迁移文件应用数 9→19；右：CI 签名点名的 8 个 schema 元素存在性 before/after（information_schema 程序化读回）"
      }
     ],
     "chars": 3612
    },
    "figure_probe": {
     "url": "http://127.0.0.1:8010/api/v1/tensor/reports/1200/figures/schema_drift_coverage.png",
     "name": "schema_drift_coverage.png",
     "status": 404,
     "bytes": 0,
     "detail": "{\"detail\":\"figure not found\"}"
    },
    "producer_mission": {
     "id": 15523,
     "status": "succeeded",
     "created_at": "2026-11-12T00:46:59.012376+00:00",
     "finished_at": "2026-11-12T00:56:37.012920+00:00",
     "started_at": null,
     "finished_status": null,
     "agent_name": null,
     "goal_package_id": "wp-1200-01"
    },
    "reviewer_mission": {
     "id": 15819,
     "status": "running",
     "created_at": "2026-11-12T02:36:33.317291+00:00",
     "finished_at": null,
     "started_at": null,
     "finished_status": null,
     "agent_name": null,
     "goal_package_id": "wp-1200-04"
    }
   },
   "acceptance_self_check": {
    "valid_json": true,
    "schema_pass": true,
    "reviewer_independent": true,
    "upstream_packages_completed": true,
    "do_not_mark_claims_as_verified": true,
    "reviewer_context_excludes_producer_explanation": true,
    "review_prompt_not_copied_from_producer": true
   }
  },
  "review_events.json": {
   "policy_version": "ke-review-v0.2",
   "events": [
    {
     "id": "tkr:wp-1200-01:1",
     "package_id": "wp-1200-01",
     "decision": "request-changes",
     "policy_version": "ke-review-v0.1",
     "reviewer": {
      "id": "agent-m15819",
      "reviewer_type": "agent"
     },
     "reviewed_at": "2026-11-12T02:36:33.317291+00:00",
     "from_state": "in-review",
     "to_state": "draft",
     "findings": [
      {
       "id": "F1",
       "severity": "medium",
       "title": "平台记录声明的唯一结果图未登记为资产，可达性也未标注（实测 HTTP 404）"
      },
      {
       "id": "F2",
       "severity": "low",
       "title": "判据表点名 3 个迁移 SQL 文件未进 attachments（仅以 declared_by_migration 文本出现）"
      },
      {
       "id": "F3",
       "severity": "low",
       "title": "claim 状态词表使用不一致：引文全覆盖的报告自述，一条标 supported、一条标 partially-supported"
      }
     ],
     "review_report": "artifacts/wp-1200-04/review_report.json"
    }
   ]
  }
 }
}
```
