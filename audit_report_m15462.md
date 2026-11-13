# 交差审计报告：m15462 KBM-RCI-S2-PILOT200

> 审计任务 m15812 · 审计人 board-audit · 日期 2026-11-12
> 被审计对象：m15462（KBM-RCI-S2-PILOT200·RCI·200 份分层抽样试点加工+人工核验·TensorKnowledge）
> 审计性质：交差核验（非重做）

## ① 审计范围与方法

### 审计对象
- 工作树：`/root/tp-agent/work/m15462`（分支 agent/m15462，commit 867ffad）
- 核心工件：`knowledge/rci-pilot200/`（inventory / sample / corpus / objects.jsonl / manifest / review）
- 报告：`docs/rci-s2b-pilot200-report.md`
- 测试：`tests/test_rci_pilot200.py`（15 项）
- 管线脚本：`scripts/rci_{corpus,sampling,ko,pilot200,review,report}.py`

### 审计方法
1. **数字溯源**：逐项核对报告中 13 个关键数字与 manifest.json / review_manual_summary.json 的一致性
2. **Schema 机检**：对 objects.jsonl 全部 278 条 KO 执行 JSON Schema Draft 2020-12 校验
3. **证据指针抽样**：抽样 11 条 KO 验证 corpus 快照 sha256 一致 + claim quote 唯一可达
4. **测试执行**：`pytest tests/test_rci_pilot200.py -v`（15/15 passed）
5. **三件套核验**：run_artifacts 存在性 / benchmark 数值对照 / repro_cmd 可执行性

## ② 三件套核验结果

| 验收项 | 状态 | 详情 |
|---|---|---|
| run_artifacts | ✅ 存在 | knowledge/rci-pilot200/ 含 inventory.json(2.3MB), sample.json(102KB), objects.jsonl(1MB), manifest.json(75KB), corpus/ 快照, review/ 9 文件 |
| benchmark ref vs got | ✅ 一致 | 报告 13 个关键数字与工件 100% 匹配（见下方数字对照表） |
| repro_cmd | ✅ 可执行 | `python scripts/rci_pilot200.py --corpus-root /root/tensor-ecosystem --n 200` + `python scripts/rci_report.py` |

### 数字对照表（报告 vs 工件）

| 指标 | 报告值 | 工件值 | 状态 |
|---|---|---|---|
| docs_processed | 200 | 200 | ✅ |
| sample_selected | 200 | 200 | ✅ |
| knowledge_objects | 278 | 278 | ✅ |
| schema_validation_errors | 0 | 0 | ✅ |
| fallback_docs | 58 | 58 | ✅ |
| evidence_verified_rate | 1.0 | 1.0 | ✅ |
| conditions_stated_rate | 0.2914 | 0.2914 | ✅ |
| rci_score_mean | 67.59 | 67.59 | ✅ |
| rci_score_median | 69.0 | 69.0 | ✅ |
| claim_faithful_pooled | 1.0 | 1.0 | ✅ |
| evidence_reachable_pooled | 1.0 | 1.0 | ✅ |
| conditions_not_fabricated_pooled | 0.9259 | 0.9259 | ✅ |
| ko_type_fit_pooled | 0.3519 | 0.3519 | ✅ |

## ③ 报告六段完整性

| 段落 | 状态 | 说明 |
|---|---|---|
| ① 案例介绍 | ✅ | 背景/范围/参数表齐全（语料 5228 篇、分层 131 层、抽样 200 份） |
| ② 怎么做的 | ✅ | 七步流程完整（语料清单→分层抽样→冻结快照→KO 抽取→RQS 打分→Schema 机检→核验） |
| ③ 计算结果 | ✅ | 数字表齐全（加工总览 + 分字段准确率），程序化注入零手抄 |
| ④ 结果图 | ✅ | 三张图（ko_quality_by_type.png, review_field_accuracy.png, rqs_distribution.png） |
| ⑤ 注意点 | ✅ | 六条局限/踩坑/适用范围（conditions 风险、类型适配天花板、兜底占比、活仓库漂移、智能体人工局限、语料口径） |
| ⑥ 误差判定 | ✅ | 五项关键量 vs 基准逐项列出，显式回答是否<3%（claim/evidence/quality 达标；conditions 92.6% 未达标；type_fit 35.2% 严重未达标） |

## ④ 基准裁判核验

> 注：`tensor_benchmark_cases` 表中无 `anchor_slug='KBM-RCI-S2-PILOT200'` 记录。
> 本轮基准判据以报告自声明的字段级准确率 95% 验收线为准。

| 字段 | 验收线 | 实测 | 判定 |
|---|---|---|---|
| claim 忠实原文 | ≥95% | 100.0% | ✅ 通过 |
| evidence 指针可达 | ≥95% | 100.0% | ✅ 通过 |
| 六维分可复算 | ≥95% | 100.0% | ✅ 通过 |
| conditions 未臆造 | ≥95% | 92.6% | ❌ 未通过（差 2.4pp） |
| KO 类型适配 | ≥95% | 35.2% | ❌ 严重未通过（差 59.8pp） |
| Schema 校验错误 | =0 | 0 | ✅ 通过 |

**结论**：Schema 稳定性与三条真实性字段中的两条验收通过；conditions 与 KO 类型适配未通过。
m15462 自报「有条件通过」——与审计结论一致。

## ⑤ 成熟度判级（L0-L5）

| 级别 | 定义 | 是否满足 |
|---|---|---|
| L0 文档成果 | 有文档输出 | ✅ |
| L1 数学/单元验证 | 有单元测试 | ✅（15 项测试） |
| L2 独立功能实现 | 真代码：输入→计算→输出 | ✅（6 脚本管线，278 KO 产出） |
| L3 系统集成 | 接入主求解器/平台 | ❌（standalone pipeline，无 API 调用方） |
| L4 基准验证 | 完整算例+误差分析+可复现 | ⚠️ 部分（有误差分析，但基准为内部人工判定非外部参考值） |
| L5 科研工程成果 | — | ❌ |

**判定级别：L2**

理由：m15462 实现了完整的 RCI 知识加工管线（语料扫描→分层抽样→冻结快照→五类 KO 抽取→六维 RQS 打分→Schema 校验→报告生成），有 15 项自动化测试覆盖核心不变量，278 条 KO 全部通过 Schema 校验，证据指针 100% 可达。但管线尚未接入主平台 API 或求解器（无 integration_callers），且基准验证为内部人工判定而非外部参考值对照，故不满足 L3/L4。

## ⑥  adversarial review 发现

### Blocking（无）
无阻塞性正确性问题。

### Non-blocking 建议
1. **tensor_benchmark_cases 缺失**：任务要求对照 `tensor_benchmark_cases` 表核验，但该表不存在。建议平台侧补建此表或明确 KBM-RCI-S2-PILOT200 的基准判据存储位置。
2. **repro_cmd 未落盘**：manifest.json 中无 `repro_cmd` 字段，建议补充以便机器复现。
3. **integration_callers 为空**：管线尚未接入平台，建议在阶段 3 全量处理时同步考虑 API 化。

### 未发现夸大声明
- 报告数字与工件 100% 一致
- honest FAIL（conditions 92.6%、type_fit 35.2%）如实披露未粉饰
- 「有条件通过」结论与数据一致

## ⑦ 落表

```sql
INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES ('TensorKnowledge', 'm15462 KBM-RCI-S2-PILOT200', '15812', 2,
'{"impl_files":"scripts/rci_corpus.py:1, scripts/rci_sampling.py:1, scripts/rci_ko.py:1, scripts/rci_pilot200.py:1, scripts/rci_review.py:1, scripts/rci_report.py:1","entry":"scripts/rci_pilot200.py","run_artifacts":"knowledge/rci-pilot200/","tests":"tests/test_rci_pilot200.py:15 passed","integration_callers":"none","benchmark":"field-level accuracy: claim=100%, evidence=100%, quality=100%, conditions=92.6%(FAIL), type_fit=35.2%(FAIL)","repro_cmd":"python scripts/rci_pilot200.py --corpus-root /root/tensor-ecosystem --n 200","external_anchor":"KBM-RCI-S2-PILOT200"}',
'board-audit');
```

**已执行**：verdict 已写入 `/root/tp-agent/tensor.db`（rowid=14）。

## ⑧ 裁定建议

**confirmed**（消账）——m15462 交付物完整、数字可溯源、测试全绿、honest FAIL 如实披露。
conditions 与 type_fit 未达标已在报告中诚实披露并附修订计划（`docs/rci-s2b-schema-revisions.md`），
不影响本轮「有条件通过」的验收结论。
