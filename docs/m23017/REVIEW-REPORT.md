# PROD-RA m22059 证据最终复审报告（m23017）

## 1. 任务与锚点

| 项目 | 值 |
|---|---|
| 复审任务 | m23017（RA 三轮复审\|阶段3 收口） |
| 锚点 | PROD-RA |
| 前史 | m22923 复审 = changes_requested level2（证据被 pusher 门禁滤除不在 main） |
| 补推 | m22059 证据 38 文件已并 main（Merge #503 = a168dec，docs/m22059/ 含 criteria.json/validation-report/negative_knowledge_ledger 等） |
| 本单 | 最终复审：以 origin/main 实际文件逐项复核 m22923 缺口（D1-D12 + six_checks 全六检） |

## 2. 独立性硬门

| 项目 | 值 |
|---|---|
| 被审任务 | m22059（证据作者 chuxuesen / cxs503@163.com） |
| 复审执行者 | tp-native-1（LLM_MODEL=qwen3.7-plus） |
| 同族判定 | m22923 复审已确立 chuxuesen 与 tp-native-1 为**不同 agent、非同族模型** |
| 独立性 | **独立**（不构成 self-review-conflict，硬门通过） |

## 3. 远端对账基线

```
$ git rev-parse HEAD            = a168decbb3024398ecc0df0d8d86f8e5a88e9f72
$ git rev-parse origin/main     = a168decbb3024398ecc0df0d8d86f8e5a88e9f72
$ git log --oneline -1 origin/main = a168dec Merge #503 (m22059) via merge-master
```

**事实基线 = origin/main @ a168dec**。m22059 证据 38 文件已并 main，位于 `docs/m22059/`（此前 m22923 指出的 runs/ 黑名单滤除问题已通过迁移到 docs/ 解决）。

## 4. D1-D12 逐项复核（以 origin/main 实际文件为准）

### 复核方法
以 origin/main（a168dec）实际可访问文件为准，独立复跑两个审计器，逐项比对。

| 缺陷 | 级别 | m22923 状态 | 本单复核结果 | 状态 |
|---|---|---|---|---|
| D1 | blocking | unfixed_on_main | criteria_sha256 声明 `f60695e1…`，经 pretty-json-indent-2 规范化可解析（与原始审查一致）；但**非框架 canonical_sha256 口径**（raw 文件 sha256=`0452efb3…`）。**仍非 canonical**。 | **unfixed** |
| D2 | blocking | unfixed_on_main | criteria.json 仅 4 条判据（bidirectional_links/citation_resolution/review_relation_consistency/source_locator_integrity），**无 source-span 条款**，未指到 FOUR_PRODUCT_ACCEPTANCE_MATRIX/PRD。 | **unfixed** |
| D3 | blocking | unfixed_on_main | evidence-f1.json `locator.quote=""`（零长度），`content_hash=sha256("")=e3b0c442…`。**claim-f1 仍只绑零长度证据**。 | **unfixed** |
| D4 | blocking | unfixed_on_main | 11/11 evidence 文件 `start_offset=0`；独立复跑 claim_evidence_audit 得 **11 条 quote_offset_mismatch**（引文实际位于源文件 2545–20394 字节，均≠0）。 | **unfixed** |
| D5 | blocking | unfixed_on_main | negative_knowledge_ledger 记录 2/3 `evidence_refs` 无 sha256（记录1有，记录2/3无）。 | **unfixed** |
| D6 | medium | unfixed_on_main | validation-report evidence_bundle：ev-citation-audit 有 `input_sha256`；ev-claim-evidence-audit 仅 `input_refs`（无 sha256）。 | **unfixed** |
| D7 | low | confirmed | citation_audit.py 已含 `_portable_ref()`（L29，L162 使用），input_refs 改相对路径。 | **confirmed** |
| D8 | low | unfixed_on_main | `criteria_freeze.frozen_at` == `created_at`（均 `2026-11-15T15:35:22+00:00`）。**未冻结于运行前**。 | **unfixed** |
| D9 | low | unfixed_on_main | validation-report `negative_test_results` 无 `exit_code` 字段（仅 detected 布尔）。 | **unfixed** |
| D10 | medium | unfixed_on_main | **无 regression-scope.json**（docs/m22059/ 下不存在）。 | **unfixed** |
| D11 | low | unfixed_on_main | summary.value 六维字段（problem/automation/quality/cost/reproducibility/delivery）存在，但字段名与框架 §5 要求未对齐（原始审查已标不合规，本单未变）。 | **unfixed** |
| D12 | low | unfixed_on_main | claims_triage：verified=3 + inconclusive=4 + broken=8 = **15**，但语料仅 **11** 条 claim（8 findings + 3 supported）。4 条 inconclusive 为 check 非 claim，**分母不一致**。 | **unfixed** |

### 关键发现

**m22059 证据已迁移到 docs/m22059/（解决 m22923 的 runs/ 黑名单滤除问题），但迁移未修复底层缺陷。** D1-D6、D8-D12 的缺陷在迁移后的文件中**原样保留**。迁移仅使证据可见，未做实质修复。

## 5. Six Checks 全六检复核

| six_checks.check_id | 问题 | 本单复核结果 | 状态 |
|---|---|---|---|
| `artifact_identity` | 被审 commit SHA 和工件指纹是否匹配？ | commit a168dec 确认；criteria_sha256 声明 `f60695e1…` 经 pretty-indent-2 可解析但非 canonical（raw=`0452efb3…`） | **partial** |
| `criteria_frozen_before_run` | criteria_sha256 是否在 created_at 前冻结？ | `frozen_at` == `created_at`（均 15:35:22），**未冻结于运行前**；且非 canonical 口径 | **not_run** |
| `evidence_traceability` | 每个 finding 是否可追溯到可检索的证据项？ | 证据文件在 main 上存在，但 11/11 `start_offset=0` 不命中（引文实际 2545–20394）；claim-f1 零长度 | **partial** |
| `independent_rerun` | 复审者是否自己运行了声明的命令并得到声明的裁决？ | 本单复跑：citation_audit→inconclusive（匹配）；claim_evidence_audit→failed 11 条 offset_mismatch（匹配）；但负向测试文件含旧 worktree 绝对路径 | **partial** |
| `failure_record` | 失败/跳过/未测量检查是否如实记录？ | ledger 3 条记录，记录 2/3 缺 sha256（D5）；repro_cmd 2/3 缺 commit sha（D10） | **partial** |
| `regression_scope` | 受影响范围内先前通过的检查是否仍通过？ | **无 regression-scope.json**，无法验证 | **not_run** |

### 六检总结

- **passed**: 0/6
- **partial**: 4/6 (artifact_identity, evidence_traceability, independent_rerun, failure_record)
- **not_run**: 2/6 (criteria_frozen_before_run, regression_scope)

根据 SCENARIO_ACCEPTANCE_FRAMEWORK.md，`verdict=pass` 需六检全过 + 独立性成立 + rerun.exit_code=0 + 无 blocking_conditions + 报告 overall_status=passed。当前六检 0 过、4 部分、2 未跑，**不满足 pass 条件**。

## 6. 独立复跑验证

```bash
# citation_audit（正语料）
$ python3 scripts/research_audit/citation_audit.py docs/m22059/audit_corpus/source/kf_result_wp-2506-04.md
→ overall_status=inconclusive, unresolved_citations=["0"]（与 validation-report 一致）

# claim_evidence_audit（正语料）
$ python3 scripts/research_audit/claim_evidence_audit.py --claims docs/m22059/audit_corpus/claims --evidence docs/m22059/audit_corpus/evidence --source-root docs/m22059/audit_corpus/source
→ overall_status=failed, 11 条 quote_offset_mismatch（与 validation-report 一致）

# criteria_sha256 规范化验证
$ python3 -c "import json,hashlib; d=json.load(open('docs/m22059/criteria.json')); print(hashlib.sha256(json.dumps(d,indent=2).encode()).hexdigest())"
→ f60695e1…（= 声明值，仅 pretty-indent-2 可解析，非 canonical）
```

## 7. 未运行检查（checks_not_run）

- 全量 pytest 执行（本机被计算调度令硬拦，重计算须集群递交）
- criteria.json canonical_sha256 复算（框架 canonical 口径下不解析，仅 pretty-indent-2 可解析）
- regression-scope 验证（文件不存在）
- 语义支持判定（PRD 精度/macro-F1）：无带标签 holdout

## 8. 残余缺陷清单

| 缺陷 | 状态 | 说明 |
|---|---|---|
| D1 | unfixed | criteria_sha256 非 canonical 口径（仅 pretty-indent-2 可解析） |
| D2 | unfixed | criteria.json 缺 source-span 条款 |
| D3 | unfixed | claim-f1 只绑零长度证据（evidence-f1 quote=""） |
| D4 | unfixed | 11/11 evidence start_offset=0 不命中（独立复跑 11 条 offset_mismatch） |
| D5 | unfixed | ledger 记录 2/3 evidence_refs 缺 sha256 |
| D6 | unfixed | evidence item 无输入指纹（ev-claim-evidence-audit 缺 input_sha256） |
| D8 | unfixed | frozen_at == created_at（未冻结于运行前） |
| D9 | unfixed | 负向测试无 exit_code 语义 |
| D10 | unfixed | 无 regression-scope.json |
| D11 | unfixed | 六维价值记录字段不合规 |
| D12 | unfixed | 三分报数分母不一致（15 vs 11） |
| D7 | **confirmed** | citation_audit.py `_portable_ref()` 已修复 |

## 9. 裁决

| 项目 | 值 |
|---|---|
| verdict | **changes_requested** |
| level | 2（维持 m22059 原始 level，未提升） |
| 理由 | m22059 证据已迁移到 docs/m22059/（解决 runs/ 黑名单滤除），但**迁移未修复底层缺陷**。D1-D6、D8-D12 在迁移后文件中原样保留。六检 0 过、4 部分、2 未跑，不满足 pass 条件。D7 已确认修复。 |
| scenario_validated | **false**（不可置） |

### 下轮返修输入

1. **修复而非仅迁移**：D1-D6、D8-D12 需在 docs/m22059/ 文件中实际修复（非仅移动位置）
   - D1: criteria_sha256 改用框架 canonical_sha256 口径
   - D2: criteria.json 补 source-span 条款（指到矩阵/PRD）
   - D3: evidence-f1 补真实引文（非空 quote）
   - D4: 11 个 evidence locator 重写为真实字节偏移
   - D5: ledger 记录 2/3 补 evidence_refs sha256
   - D6: ev-claim-evidence-audit 补 input_sha256
   - D8: frozen_at 改为 created_at 之前的时间戳
   - D9: negative_test_results 补 exit_code 字段
   - D10: 新增 regression-scope.json
   - D11: 六维字段名对齐框架 §5
   - D12: 三分报数分母改为 11（或明确区分 claim/check）
2. 修复后重新提交 PR，使复审者可基于 origin/main 验证
3. 全量 pytest 执行（集群递交）

## 10. 复审者签名

- 复审者：tp-native-1
- 复审日期：2026-11-16
- 复审 commit：agent/m23017
