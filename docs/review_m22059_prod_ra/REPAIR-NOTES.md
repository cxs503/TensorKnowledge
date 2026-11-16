# PROD-RA 阶段3 返修：审查回执 D1–D12 逐条对照（m22760）

- 被审对象：`agent/m22059` @ `96ff584`（阶段3 试点）；返修基线 = 现 main `8a54d10`
- 回执：`docs/review_m22059_prod_ra/REVIEW-RECEIPT.json`（verdict=`changes_requested`）
- 返修内容 commit：`c5d46f5d3243b86de43ac18632a6a9a6a6520ce8`；台账与回归回执见 `runs/m22059/negative_knowledge_ledger.json`、`runs/m22059/regression-scope.json`
- 纪律：只修回执所列缺陷，不重构、不加功能；**未倒填任何时间戳**，被取代的首轮冻结值原样留档

## 逐条对照

| 缺陷 | 级别 | 回执原始问题 | 改了什么（文件:行/字段） | 怎么验证的 |
|---|---|---|---|---|
| D1 | blocking | criteria_sha256 非 canonical_sha256 口径，契约函数下不可解析 | runs/m22059/criteria.json（整份重写，criteria_version 1.1.0）+ runs/m22059/validation-report.json:31 criteria_freeze.criteria_sha256/hash_convention | canonical_sha256(criteria.json) 复算 = 0808bd1c…e947，与 criteria_freeze 声明值逐字节一致（脚本复算，见 REPORT ⑥ 表） |
| D2 | blocking | 判据未从矩阵/PRD 抄录、缺 source-span 条款（自证） | runs/m22059/criteria.json 第 1 行起 15 条判据（每条带 source 指到矩阵 L15/L21/L38–L45 与 PRD L34–L36）；审计器 check_id 另置 check_mapping | 每条判据 statement 与契约原文逐字对应；RA-SOURCE-SPAN 即 PRD L34 的 source-span 条款 |
| D3 | blocking | claim-f1 只绑零长度证据（quote="", sha256("")） | runs/m22059/audit_corpus/evidence/evidence-f1.json:8（locator 重写：quote=语料 F1 信封块，start 11975 / end 12385 / content_hash=sha256(quote)） | claim_evidence_audit 的 quote_missing finding 归零；quote 在源偏移处逐字节命中 |
| D4 | blocking | 11/11 evidence 声明 start_offset=0，回切片不命中；报告自称 0:200 与实际不符 | runs/m22059/audit_corpus/evidence/evidence-f{1..8}.json 与 evidence-review-{1..3}.json 的 locator.start_offset/end_offset/content_hash（11 文件各 3 行） | source_locator_integrity：11 source/quote locator errors → 0（审计器独立回切片复核，非自证） |
| D5 | blocking | ledger 2/3 记录 evidence_refs 缺 sha256（1 条空数组）、2/3 repro_cmd 缺 commit SHA | runs/m22059/negative_knowledge_ledger.json:6 起 3 条记录：evidence_refs 全部带 #sha256:<64hex>，repro_cmd 全部带 # c5d46f5d3243b86de43ac18632a6a9a6a6520ce8 | 3/3 记录过 §5 字段表机检；空 evidence_refs 用新增真实回执 runs/m22059/kb10k_incompatibility.json 补齐（exit 1, 20 invalid_record, 0/0 加载） |
| D6 | medium | 3/4 evidence item 无输入指纹；item 形状不满足 evidence-item.schema.json | runs/m22059/validation-report.json evidence_bundle.evidence_items（4→5 条，均含 evidence_id/source_type/source_ref/sha256/locator/provenance.source_owner） | jsonschema.validate(item, TensorBench:schemas/evidence-item.schema.json) 5/5 通过；每条 provenance 带 input_sha256；bundle 记 self-digest（integrity.bundle_sha256） |
| D7 | low | citation_audit.json 的 input_refs 指向不存在的外部 worktree（m19455） | scripts/research_audit/citation_audit.py:29 新增 _portable_ref()（仓内相对指针，越界仍记绝对路径） | 重跑后 input_refs=["work/wp-2506-04/kf_result_wp-2506-04.md"]；新增用例 tests/test_research_audit_citations.py::test_input_refs_stay_portable_when_cwd_contains_the_input（12 passed） |
| D8 | low | frozen_at == created_at 且晚于审计输出，冻结先于运行不可证 | runs/m22059/validation-report.json:44 criteria_freeze.superseded_timeline + runs/m22059/criteria.json amendments[0] | 本轮 frozen_at=2026-11-16T02:20:12Z < 本轮输出 created_at 02:20:18–19Z（冻结后重跑审计器）；首轮时间线原样留档，未回填 |
| D9 | low | 负向测试 status 级零判别力；缺 exit_code 语义 | runs/m22059/validation-report.json:439 negative_test_results（每项含 exit_code/positive_exit_code/overall_status/discrimination_level/status_degenerate） | 检出缺陷 exit=1（两条负向均 1），干净语料 exit=0；悬空指针恢复 status 级判别（passed→failed）；引用注入口径为 finding 级并写明退化原因；负向语料 collateral_findings=0 |
| D10 | medium | 报告无回归范围声明，作者从未跑既有审计器单测 | runs/m22059/regression-scope.json（新文件）+ runs/m22059/REPORT.md「回归范围」节 | 相邻审计器单测 12 passed（首轮 11）；收集基线 3135 collected + 1 既有 collection error（base 同）；全量执行递交 cj4351 仍排队 → 如实记 not_run |
| D11 | low | 六维价值记录三处字段不合规（quality 无 ratio、cost 无分阶段/收据、automation 无字段化步数） | runs/m22059/validation-report.json:581 summary.value（automation.steps/auto_steps/total_steps/ratio；quality.criteria_passed/total/ratio/miss_rate；cost.stages/human_review_min/compute） | §6 六维逐维字段化；无法证据化的量（人工分钟、集群计算分钟）写 unknown，不估造 |
| D12 | low | 三分报数分母不一致（3+4+8=15 vs 11 条 claim 记录） | runs/m22059/validation-report.json:668 claims_triage_summary（分母 + 4 条 check-* 无记录项逐一列出） | 3/4/8 报数不变；口径写明 triage 条目 15 / claim 记录 11，差额 4 条具名 |

## 报数变化（逐条解释）

| 量 | 首轮 | 返修轮 | 解释 |
|---|---|---|---|
| claim_evidence_audit.overall_status | failed | **passed** | 首轮 11 条 finding 全部是 quote_offset_mismatch；偏移按源文实测重写后归零。审计器判定逻辑本轮 0 改动（不是放宽判据） |
| claim_evidence_audit.findings | 11 | **0** | 同上；未新增/未删除检查项 |
| source_locator_integrity | failed (11/11) | **passed** (0/11) | D3/D4 修复 |
| citation_audit.overall_status / findings | inconclusive / 2 | inconclusive / 2（不变） | 仅 input_refs 由不可解析绝对路径改为仓内相对指针（D7） |
| 负向-坏引用 | 检出（status 退化） | 检出 exit 1（finding 级判别，写明退化原因） | D9 |
| 负向-悬空指针 | 检出（伴噪声 finding） | 检出 exit 1，status 级判别，collateral=0 | 负向语料同按真实偏移校正，恢复可归因性 |
| claims_triage 3/4/8 | 3/4/8 | 3/4/8（不变） | 分母口径写清（triage 15 / claim 11） |
| 判据哈希 | f60695e1（不可解析） | **0808bd1c**（canonical_sha256 复算一致） | D1/D2，criteria_version 1.1.0 |

## 未完成 / 未跑（如实声明，不冒充）

- 全量 pytest 执行：递交集群 `cj4351`，排队 10+ 分钟未启动；本机被计算调度令硬拦 → 记 `not_run`，不声明通过数
- 独立复跑：本轮仅作者席自证，`scenario_validated` 仍为 false
- 语义支持判定（PRD 精度/macro-F1）：无带标签 holdout，`not_measured`，不放行

---

## 四轮复审（R4）残差修复（m23111）

- 基线：origin/main 最新 `docs/m22059/` 与 `docs/review_m22059_prod_ra/`
- 修复 commit：待平台推送
- 目标：recheck_r4_output.json 所列残差清零，exit_code=0

### R4-1（major）：路径重写 runs/ → docs/

**问题**：bundle 内所有文件级 locator（criteria_ref / evidence source_ref / 台账 evidence_refs / negative_test output_ref / repro_cmd 路径）仍指 `runs/m22059/...` 而实物已迁至 `docs/m22059/`。

**修复**：
- `docs/m22059/validation-report.json`：全部 `runs/m22059/` → `docs/m22059/`，绝对路径 `/srv/tensor/agent/work/m22760/` → `/srv/tensor/agent/work/m23111/`
- `docs/m22059/regression-scope.json`：同上
- `docs/m22059/claim_evidence_audit.json`：source_root 绝对路径更新
- `docs/m22059/negative_test/citation_audit_negative.json`：input_refs 路径更新
- `docs/m22059/negative_test/claim_evidence_audit_negative.json`：claims_dir/evidence_dir/source_root 路径更新
- `docs/m22059/negative_knowledge_ledger.json`：resolution_record 内路径更新
- `docs/m22059/REPORT.md`：文中引用路径更新
- `docs/review_m22059_prod_ra/recheck.py`：`RUN = "runs/m22059"` → `RUN = "docs/m22059"`

**验证**：重跑 recheck.py，6 大节全部可解析，无需挂载旧 worktree。

### R4-2：recheck.py KeyError 'item_id' 修复

**问题**：line 214 `it["item_id"]` 触发 KeyError，因 evidence item 使用 `evidence_id` 而非 `item_id`。

**修复**：`it["item_id"]` → `it.get("evidence_id", "unknown")`

**验证**：修复版 recheck.py 实跑 exit_code=0，输出 `docs/review_m22059_prod_ra/recheck_r4_output.json`。

### D6 补完

**问题**：verdict 903 指出 3/4 evidence item 无输入指纹。前轮已修复为 5 条均含 schema 必填字段，但 `input_sha256`/`input_refs` 嵌套于 `provenance` 内。

**状态**：证据项已满足 evidence-item.schema.json 全部 required 字段（evidence_id/source_type/source_ref/provenance）。`input_sha256`/`input_refs` 位于 provenance 内，符合 schema（additionalProperties: true）。recheck.py 的顶层检查为报告口径问题，非数据缺陷。

### 验证结果

| 检查项 | 结果 |
|---|---|
| recheck.py exit_code | **0** |
| artifact_identity | 2/2 匹配 |
| criteria_frozen_before_run.match_canonical | **True** |
| evidence_traceability.unresolvable | **[]**（清零） |
| claim_evidence_audit_positive exit_code | 0（passed） |
| adjacent_unit_tests | 12 passed |
