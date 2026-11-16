# PROD-RA R4 复审报告：`origin/main@ca99e79f0` 上 m22059 D1–D12 返修的独立复核

- 复审役：m23090（独立席；未参与 m22059 试点、m22760 修复、m23017 三轮复审）
- 被审对象：`TensorKnowledge` `origin/main` @ `ca99e79f02f4e7bb0f7d9075d5b8838e5a1127a4`
- 构成：PR#503（`a168dec`，证据 38 文件落到 `docs/m22059/`）+ PR#508（`ca99e79f0`，D1–D12 修复增量 21 文件）+ `docs/review_m22059_prod_ra/` 全量审阅包
- 判据基准：`tensor_maturity_verdicts` 行 903（`m22059 PROD-RA 试点验收`, level 2, verdict `changes_requested`, defects=12）＋ `docs/review_m22059_prod_ra/REPAIR-NOTES.md` 自述
- 契约源：`TensorBench` @ `7008f52`（`docs/FOUR_PRODUCT_ACCEPTANCE_MATRIX.md`、`products/research-audit/PRD.md`、`schemas/evidence-item.schema.json`、`tensorbench.criteria.canonical_sha256`）
- 环境：3.11.6 / linux，只读审阅树，所有派生工件写在本复审席自身工作树
- **处置：`changes_requested`（窄口径）** —— D1–D12 **实质全部修复**且六检全部通过（`regression_scope` 带注记），但审阅包自身仍有 5 项可机械修复的残余缺陷（R4-1…R4-5），其中两项直接让"从被引来源复现每条 finding"这条 PRD 条款在本仓树内不成立。`scenario_validated` 本席**不置位**，交由协调者依裁决执行。

## 1. 独立性与范围

**独立性声明**：本席未编写被审的任何文件（`git log` 作者的 mission 域为 m22059/m22760/m23017），未接触作者推理轨迹；本文所有数字由 `docs/review_m22059_prod_ra/recheck_r4.py` 从被审树重算生成（`docs/review_m22059_prod_ra/recheck_r4_output.json`，脚本自生成 markdown 数字，无手抄）。

**独立性局限（如实声明）**：
1. 复跑在同一物理机上完成，与作者同 CPU/Python；确定性审计器的输出不依赖时序，但**未做跨机/跨 Python 版本复跑**。
2. 判据原文核对只**抽验** 7 条（矩阵 L15/L21/L38/L39 + PRD L34/L35/L36），未逐字核对全部 15 条。
3. 语料语义支持判定（PRD 精度 / macro-F1）**本席未做**，属 auditor 声明范围外，也无带标签 holdout。
4. `docs/review_m22059_prod_ra/recheck_output.json`（首轮审阅包产物）只能作为**历史**工件比对，其 `reviewed_commit` 是 `96ff584`，不是本轮被审 commit。

**审**：`docs/m22059/`（REPORT、criteria、validation-report、两审计器输出、11 claim/11 evidence、负向语料、台账、回归范围、kb10k 负例）、`docs/review_m22059_prod_ra/`（REVIEW-RECEIPT、review-report、recheck.py、recheck_output、raw 日志、SHA256SUMS、verdict_insert）。
**不审**：语料本身（`work/wp-2506-04/`）的科学结论、`scripts/research_audit/*.py` 的算法取舍（仅作为执行器复跑）、L3/L4 晋级条件（不在本轮问题域）。

## 2. 方法与工具链

1. **六检**按 `adversarial-review` 流程独立重建执行路径，不复用作者自证脚本；数字全部从被审树重算。
2. **判据基准**取 `tensor_maturity_verdicts` 行 903 的 12 条 defect 原文 + `REPAIR-NOTES.md` 的逐条自述，**双向对照**：既查"缺陷是否消失"，也查"自述是否成立"。
3. **复跑**：`recheck_r4.py`（本席新写，见 R4-2 说明为何不能直接用作者交付的 `recheck.py`）。命令与退出码：

```
python3 docs/review_m22059_prod_ra/recheck_r4.py \
    --out docs/review_m22059_prod_ra/recheck_r4_output.json      # exit_code = 2
```

退出码语义：0=六检全过且无残余/open；1=六检有失败；2=D1–D12 实质修复但仍有残余缺陷（本轮）。本轮 **exit_code = 2**。

4. 复跑明细（原始工件在 `docs/review_m22059_prod_ra/raw_r4/`）：

| 命令 | 本轮 exit | 在册 exit | 状态复现 |
|---|---|---|---|
| `citation_audit.py docs/m22059/audit_corpus/source/kf_result_wp-2506-04.md` | 1 | 1 | inconclusive（在册 inconclusive）；summary 全等=True |
| `citation_audit.py docs/m22059/negative_test/corpus/kf_result_bad.md` | 1 | 1 | inconclusive；unresolved=['0', '999'] |
| `claim_evidence_audit.py --claims …/claims --evidence …/evidence --source-root …/source` | 0 | 0 | passed（在册 passed），findings=[] |
| `claim_evidence_audit.py --claims …/negative_test/claims …` | 1 | 1 | failed；检出 ['missing_evidence_record', 'missing_claim_record'] |
| `claim_evidence_audit.py --claims knowledge/kb10k/claims …`（R4-4 复现） | 1 | 1 | failed，20 × `invalid_record`，与在册 `kb10k_incompatibility.json` 逐项一致 |
| `pytest tests/test_research_audit_citations.py tests/test_research_audit_claim_evidence.py -q` | 0 | — | 12 passed, 1 warning |

## 3. D1–D12 逐项裁决（判据=行 903 缺陷原文 + REPAIR-NOTES 自述）

| 缺陷 | 级别 | 缺陷原文（行 903） | 本轮判定方法 | 实测证据 | 状态 |
|---|---|---|---|---|---|
| D1 | blocking | criteria_sha256 非 canonical_sha256 口径，契约函数下不可解析 | tensorbench.criteria.canonical_sha256(criteria.json) 与 criteria_freeze.criteria_sha256 逐字节比对；同时检验 sha256(indent=2) 是否误命中 | `canonical_sha256=0808bd1c459cc393 declared=0808bd1c459cc393` | **fixed** |
| D2 | blocking | 判据未从矩阵/PRD 抄录、缺 source-span 条款（自证） | 15 条判据的 source 是否指向 TensorBench 矩阵/PRD；RA-SOURCE-SPAN 是否存在；statement 与原文逐字比对（抽验 L15/L21/L38/L39 + PRD L34–L36） | `15 criteria, sources=13, RA-SOURCE-SPAN present` | **fixed** |
| D3 | blocking | claim-f1 只绑零长度证据（quote="", sha256("")） | 11 条 evidence 记录的 quote 长度、content_hash==sha256(quote) | `11 locators, empty quotes=0` | **fixed** |
| D4 | blocking | 11/11 evidence 声明 start_offset=0，回切片不命中 | src[start:end] == quote 逐条回切片；start_offset==0 计数 | `start_offset=0 count=0, slice mismatches=0` | **fixed** |
| D5 | blocking | ledger 2/3 记录 evidence_refs 缺 sha256、repro_cmd 缺 commit SHA | §5 十字段齐全性；evidence_refs 每条带 #sha256:<64hex> 且摘要与仓内文件实测一致；repro_cmd 内 commit 在仓内可解析 | `3 records, missing fields=0, no-sha refs=0, no-commit=0` | **fixed** |
| D6 | medium | 3/4 evidence item 无输入指纹；item 形状不满足 evidence-item.schema.json | 5 条 evidence item 逐条 jsonschema.validate(item, TensorBench:schemas/evidence-item.schema.json)；provenance 输入指纹存在性 | `5/5 items validate vs evidence-item.schema.json; items without input_sha256=['ev-kb10k-incompatibility']` | **fixed_with_residual** |
| D7 | low | citation_audit.json 的 input_refs 指向不存在的外部 worktree（m19455） | input_refs 是否为仓内相对路径且文件存在 | `input_refs=['work/wp-2506-04/kf_result_wp-2506-04.md']` | **fixed** |
| D8 | low | frozen_at == created_at 且晚于审计输出，冻结先于运行不可证 | frozen_at vs earliest_audit_output_created_at vs report created_at；首轮时间线是否留档未回填 | `frozen_at=2026-11-16T02:20:12+00:00 earliest_output=2026-11-16T02:20:18+00:00 report=2026-11-16T02:21:04+00:00` | **fixed** |
| D9 | low | 负向测试 status 级零判别力；缺 exit_code 语义 | 负向/正向 exit_code 与 overall_status 对比；discrimination_level 字段；悬空指针是否 status 级检出 | `{"bad_citation_injection": {"exit": 1, "pos_exit": 1, "level": "finding", "degenerate": true}, "dangling_evidence_injection": {"exit": 1, "pos_exit": 0, "level": "status", "degenerate": false}}` | **fixed** |
| D10 | medium | 报告无回归范围声明，作者从未跑既有审计器单测 | regression-scope.json 存在性 + REPORT.md「回归范围」节 + 本席重跑相邻单测 | `regression-scope.json present=True, adjacent rerun: 12 passed, 1 warning` | **fixed** |
| D11 | low | 六维价值记录三处字段不合规 | summary.value 六维字段化（automation.steps/ratio、quality.ratio/miss_rate、cost.stages） | `{"problem": ["decision_changed", "stakeholder", "statement"], "automation": ["auto_steps", "ratio", "steps", "total_steps"], "quality": ["assessed_by", "baseline_comparison", "calibrated_gate_criteria", "calibrated_gate_` | **fixed** |
| D12 | low | 三分报数分母不一致（15 vs 11） | claims_triage_summary 分母口径 + entries_without_claim_record 是否具名 | `{"triage_entries": 15, "claim_records_in_corpus": 11, "entries_without_claim_record": ["check-cross-report", "check-bitwise", "check-affine", "check-solver"]}` | **fixed** |

**汇总**：fixed = D1, D2, D3, D4, D5, D7, D8, D9, D10, D11, D12；fixed_with_residual = D6；open = 无。

关键复算值：
- **D1** 判据哈希：`canonical_sha256(criteria.json)` = `0808bd1c459cc3934d4b32f9dc7fd613bf03aed87981c855c99c697083e8e947`，与 `criteria_freeze.criteria_sha256` **逐字节一致**；且**不**是 `sha256(indent=2)`（`False`）。首轮错值 `f60695e1…` 已在 `superseded_timeline` 留档（未倒填）。
- **D4** 11 条 evidence 的 `src[start:end] == quote` **全部命中**，`start_offset==0` 计数 0；`claim_evidence_audit` 独立回切片复核后 `source_locator_integrity` = passed，全库 findings = 0（首轮 11 条 `quote_offset_mismatch` 归零，审计器判据代码未放宽）。
- **D5** 台账 3 条记录：缺字段 0、无 sha256 的 ref 0、无 commit SHA 的 repro_cmd 0；每条 `#sha256:` 摘要与仓内文件**实测一致**，commit `c5d46f5d…` 在仓内可解析。
- **D6** 5 个 evidence item **5/5** 通过 `evidence-item.schema.json`；`ev-kb10k-incompatibility` 无 `input_sha256`（输入是目录树，见 R4-4）。
- **D8** 时间线：`frozen_at=2026-11-16T02:20:12+00:00` ≤ 最早审计输出 `2026-11-16T02:20:18+00:00` ≤ 报告 `2026-11-16T02:21:04+00:00`，冻结先于运行**可证**；首轮同刻时间线原样留档。
- **D9** `claim_evidence_audit` 负向 exit 1 / 正向 exit 0，状态 failed vs passed → **status + exit_code 双级判别**；`citation_audit` 两语料同为 inconclusive+exit 1，只剩 finding 级判别，作者以 `discrimination_level=finding`、`status_degenerate=true` 加书面理由声明（见 R4-5，接受为诚实限制）。
- **D12** triage 条目 15 = 3+4+8，claim 记录 11，差额 4 条具名（`check-cross-report`/`check-bitwise`/`check-affine`/`check-solver`），本席从语料重建计数**复现 15/11**（`True`）。

## 4. 六检实测

| 检查 | 做法 | 结果 |
|---|---|---|
| `artifact_identity` | 两处 scenario 输入 + 5 条 evidence item 的 sha256 是否与仓内字节一致；审阅包 SHA256SUMS 清单可核性 | **passed** |
| `criteria_frozen_before_run` | 判据文件在审计输出之前冻结：canonical 哈希可解析 + frozen_at ≤ 最早输出时间 | **passed** |
| `evidence_traceability` | 每条 finding 能否沿 claim→evidence→源偏移逐跳回溯；审计器 source_locator_integrity 状态 | **passed** |
| `independent_rerun` | 两审计器在正/负语料上独立复跑，exit_code/状态/checks/findings 与在册输出比对 | **passed** |
| `failure_record` | §5 台账字段与摘要可核；失败是否被吞；evidence bundle 缺项 | **passed** |
| `regression_scope` | 回归范围文件 + 相邻单测重跑 + 全量测试是否如实记 not_run | **passed_with_notes** |

- `artifact_identity`：2/2 scenario 输入指纹一致（`0` 处不符）；语料副本 sha256 `2745f3a8aa8db04e…` 与主输入同字节；5 条 evidence item 摘要**全部匹配**，但**仅在本席按 `runs/m22059→docs/m22059` 重根后**才解析得到（见 R4-1）。
- `regression_scope` 打 `passed_with_notes` 的唯一原因：全量 pytest 仍 `not_run`（作者记 `cj4351` 排队，`not_run`），作者**未声明通过数**，符合"未知=未跑"纪律；相邻单测本席重跑 12 passed, 1 warning（首轮 11 → 本轮 12，新增 1 条 D7 回归用例）。

## 5. 残余缺陷（不在 D1–D12 单内，全部在审阅包/迁移层）

| # | 严重度 | 范围 | 缺陷 | 实测 |
|---|---|---|---|---|
| R4-1 | major | docs/m22059 (whole bundle) | every file-level locator cites runs/m22059/... while the artifacts ship at docs/m22059/; a fresh reader cannot resolve criteria_ref, evidence source_ref, ledger evidence_refs, negative_test output_ref or any repro_cmd path in this tree (offset-level locators into the corpus copy do resolve) | `{"evidence_items_resolved_only_after_reroot": 5, "reference_worktree_present": "/srv/tensor/agent/work/m22059/runs/m22059 exists=False"}` |
| R4-2 | major | docs/review_m22059_prod_ra/recheck.py | the shipped reviewer entry point cannot execute on ca99e79: it hardcodes RUN='runs/m22059' and reads evidence_items[].item_id, which D6's repair renamed to evidence_id; it aborts with KeyError: 'item_id' before writing any output, so the committed recheck_output.json still describes 96ff584, not the reviewed commit | `{"as_shipped_exit_code": 1, "as_shipped_error": "KeyError: 'item_id' (recheck.py:214)"}` |
| R4-3 | major | docs/review_m22059_prod_ra/SHA256SUMS | the reviewer bundle manifest itself has 5 of 18 entries unsound: 4 listed raw logs are absent from the tree (untracked and not shipped) and raw/SHA256SUMS is listed with the sha256 of the empty string instead of its own digest - the same zero-length-artifact class as defect D3 | `{"entries": 18, "missing": ["raw/adjacent_unit_tests.log", "raw/evidence_schema_validation.log", "raw/pytest_collect_base.log", "raw/pytest_collect_reviewed.log"], "self_digest_wrong_for": ["raw/SHA256SUMS"], "raw_sha256sums_actual": "ac75e22446cc451facbc7e4ef` |
| R4-4 | minor | docs/m22059/validation-report.json#evidence_bundle | ev-kb10k-incompatibility provenance.source_root is the absolute path /srv/tensor/agent/work/m22760 (a foreign worktree) and the item carries no input digest; REPAIR-NOTES' 'every provenance carries input_sha256' is therefore overstated for 1/5 items. Reproduced identically here (20 invalid_record, exit 1), so the finding itself stands | `{"item": "ev-kb10k-incompatibility", "rerun_findings": 20, "rerun_exit_code": 1}` |
| R4-5 | info | docs/m22059/validation-report.json#negative_test_results | citation_audit stays inconclusive+exit 1 on both corpora, so only the finding set discriminates; declared as discrimination_level=finding with status_degenerate=true and a written reason - accepted as an honest limitation, not a pass | `{"bad_citation_injection": {"injected": "[999]", "command": "python3 scripts/research_audit/citation_audit.py runs/m22059/negative_test/corpus/kf_result_bad.md --output runs/m22059/negative_test/citation_audit_negative.json", "output_ref": "runs/m22059/negativ` |
| R4-6 | info | full pytest suite | still not_run (cluster cj4351 queued); the repair declares not_run instead of a pass count - accepted, recorded as passed_with_notes for regression_scope | `{"full_suite": "not_run"}` |

**R4-1 影响面**：`criteria_freeze.criteria_ref/amendments_ref`、5 条 evidence item 的 `source_ref`、台账 3 条 `evidence_refs` 与 `repro_cmd`、`negative_test_results.*.output_ref/command`、`regression_scope_ref`、`REPAIR-NOTES.md` 引用的路径，全部写成 `runs/m22059/...`；而 main 里这些字节在 `docs/m22059/...`。作者侧参考工作树 `/srv/tensor/agent/work/m22059/runs/m22059` 在本机**已不存在**，即这些 locator 现在没有任何一处能解析。**内容级 locator（偏移+quote+hash）不受影响**，故 RA-RECORD-INPUTS 的"源定位"实质仍成立；受影响的是"文件级指针可解析"。
**R4-2 影响面**：作者交付的复审入口 `recheck.py` 在 `ca99e79` 上 `exit=1`（`KeyError: 'item_id'`，`recheck.py:214`；D6 把 `item_id` 改名为 `evidence_id` 后未回改脚本），且硬编码 `RUN="runs/m22059"`；因此仓内 `recheck_output.json` 描述的是 `96ff584`，**不是被审 commit**。
**R4-3 影响面**：审阅包 `SHA256SUMS` 18 条里 5 条不成立——4 条 raw 日志（`adjacent_unit_tests.log`、`evidence_schema_validation.log`、`pytest_collect_base.log`、`pytest_collect_reviewed.log`）未随仓交付（未被 git 跟踪），`raw/SHA256SUMS` 自身被登记为空串摘要 `e3b0c442…`（实际 `ac75e22446cc451f…`）——与缺陷 D3 同一"零长度工件摘要"类错误复发在审阅包上。

## 6. 自述与实测的偏差（夸大项）

| REPAIR-NOTES 自述 | 实测 | 判定 |
|---|---|---|
| "evidence 5/5 过 schema" | 5/5 validate 属实 | 成立 |
| "11 处 locator 实测重写" | 11/11 `src[start:end]==quote` 且 hash 一致 | 成立 |
| "每条 provenance 带 input_sha256" | 4/5 带 `input_sha256`；`ev-kb10k-incompatibility` 只有目录型 `input_refs`（无摘要），且 `source_root=/srv/tensor/agent/work/m22760` 为域外绝对路径 | **部分不实**（1/5）→ R4-4 |
| "相邻审计器单测 12 passed（首轮 11）" | 本席重跑 12 passed, 1 warning | 成立 |
| "全量执行递交 cj4351 排队 → 记 not_run" | regression-scope 里确实 `state=not_run`、无通过计数 | 成立（诚实项） |
| "负向-坏引用 检出 exit 1（finding 级判别，写明退化原因）" | 属实，且作者主动标注 `status_degenerate=true` | 成立 |
| 证据路径（`runs/m22059/...`） | main 中文件在 `docs/m22059/...`；自述与 manifest 均未随之更新 | **不成立**（路径层）→ R4-1/R4-3 |

## 7. 未跑 / 未知（标记为未跑，不是通过）

- 全量 pytest（`python3 -m pytest tests -q`）：**not_run**（作者 `cj4351` 排队；本席按计算调度令不在本机跑全量，也未另递重计算）。
- 跨机 / 跨 Python 版本复跑：**not_run**。
- 15 条判据与矩阵/PRD 的**逐字全量**核对：仅抽验 7 条。
- PRD 精度门（citation metadata precision ≥0.98、support macro-F1 ≥0.80）：**not_measured**（无带标签 holdout），作者在 `criteria.json` 标 `not_measured` 未冒充通过，本席认同不放行。
- 首轮审阅包 `raw/` 下 4 条缺失日志的内容：**未知**（文件不存在，无法核）。

## 8. 残余风险与回滚

- 若把 R4-1 视为纯迁移噪声而不修：任何下游集成方/外部审计按 locator 取文件都会失败，产品的可追溯性卖点在该树内不成立；影响可逆（纯字符串重写，不动内容字节）。
- R4-2 不修则"独立复审可复现"退化为口头声明：下一轮复审必须自带脚本（本轮即如此）。
- R4-3 不修则审阅包自证链有缺口（4 条日志缺失 + 1 条假摘要）；补齐日志或删表项并写明缺失原因，两者都可接受，但不能保留"清单声称存在"的状态。
- 回滚：本轮只新增文件（`docs/review_m22059_prod_ra/` 下的 `REVIEW-R4.md`、`recheck_r4.py`、`recheck_r4_output.json`、`raw_r4/*`、`figures/r4-*.png`、`verdict_insert_r4.sql`），不改被审字节；删除即回滚。

## 9. 最小修复建议（供协调者派单，均机械可验）

1. **R4-1**：把 `docs/m22059/` 内所有 `runs/m22059/` 前缀重写为 `docs/m22059/`（`criteria.json`、`validation-report.json`、`citation_audit.json`、`claim_evidence_audit.json`、11 条 evidence/claim、`negative_test/*.json`、`regression-scope.json`、`REPORT.md`、`REPAIR-NOTES.md`），重算 `criteria_sha256`（若 `criteria.json` 被改，需在 `superseded_timeline` 留档而非覆盖），然后重跑两审计器 + `recheck_r4.py` 应得 exit=0。
2. **R4-2**：`recheck.py` 改 `evidence_id`、`RUN` 改为按候选根解析（本席 `recheck_r4.py` 已实现，可直接采纳或对齐），并重生成 `recheck_output.json` 指向 `ca99e79`。
3. **R4-3**：补 4 条 raw 日志或从 `SHA256SUMS` 删项并注明；`raw/SHA256SUMS` 自摘要改写为真实值（或从清单移除自身）。
4. **R4-4**：`ev-kb10k-incompatibility.provenance.source_root` 改为仓内相对（`.`）并对 claims/evidence 目录逐文件记摘要，或明写"目录型输入无摘要"。

## 10. 复现清单（工件 SHA256）

| 工件 | sha256 |
|---|---|
| `docs/review_m22059_prod_ra/recheck_r4.py` | `4b5c4a606029e3d0ce3e348f7c9fa9e3acc45a60761853f029d8f40e5fe7f94a` |
| `docs/review_m22059_prod_ra/recheck_r4_output.json` | `7cd3327ec7fd4ebf387257229942151e76ab31abcfcaa81693b9ee591d22570a` |
| `docs/m22059/validation-report.json` | `466f22995fd85dc718a257fc8abeeda5a956a7269f1a48f0c0cea94e933d7bd7` |
| `docs/m22059/criteria.json` | `c12873d308294508116dc623ff162f125b49ce251d3f3d86099e81421052d74a` |
| `docs/m22059/claim_evidence_audit.json` | `dc117e6e41e17cba61e4e4537d2cf7cf5356f7e8623f43a25c275e1a03ae5827` |
| `docs/m22059/citation_audit.json` | `d523660b6035b64da6774cf32c11d5e7b6955b306e6b557625e77740436d7e7c` |
| `docs/m22059/negative_knowledge_ledger.json` | `d52690b288e002817a2b096d672f1457009965248f0e22fcc20649ec2cd644e6` |
| `docs/m22059/regression-scope.json` | `dc23bfbaa669d4dd8777c98e27aae5775a20505ff13b18992765724917401279` |

## 11. 处置

**`changes_requested`**（窄口径、可机械修复）：
- D1–D12：**实质修复成立**，六检均过（`regression_scope` 带 not_run 注记）。这是三轮返修第一次在被审主线上被独立复现的完整修复。
- 阻断点只有审阅包/迁移层 3 项（R4-1 路径重根、R4-2 复审脚本失效、R4-3 清单不成立）+ 1 项轻微（R4-4）。四者都不触及审计结论与计数器，修完重跑 `recheck_r4.py` 预期 `exit_code = 0`。
- `scenario_validated` **不由本复审单置位**；本席不建议在 R4-1/R4-2 修复前放行下游集成方引用本包 locator。

## 12. 交付登记

| 件 | 标识 |
|---|---|
| 台账行 | `tensor_maturity_verdicts` id=918，`repo=TensorKnowledge`，`scope=ra-rereview4-m22059-fixes`，`mission_id=23090`，level=2，`gate_state=pending`（level 沿用行 903 的 L2 判级，本轮未主张升级） |
| 平台报告（双件） | `tensor_reports` id=20718（`prod_ra_rereview4_m22059_r4review`，论文级进展报告）+ id=20719（`prod_ra_rereview4_m22059_verdict`，裁决报告） |
| 复跑工件 | `docs/review_m22059_prod_ra/recheck_r4_output.json`（exit_code=2）、`raw_r4/`（8 个原始输出/退出码）、`SHA256SUMS.r4` |
| 图 | `figures/r4-d-status-six-checks.png`、`figures/r4-rerun-exitcodes.png`（两张均随报告以 base64 内嵌，服务端可 `GET /tensor/reports/<id>/figures/<name>` 取回原字节） |
