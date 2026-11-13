# m15906 交差审计报告：m15721 KBM-TKC-GOV-SCALE

## 审计对象
- **Mission**: m15721 (KBM-TKC-GOV-SCALE · TK校正 · 多Agent知识治理规模化)
- **Repo**: TensorKnowledge
- **Branch**: agent/m15721
- **Status**: succeeded (claimed)

## 取证结果

### ① 验收三件套核验

| 项目 | 状态 | 证据 |
|---|---|---|
| run_artifacts | ✅ 存在 | runs/kbm-gov-w1/ 共 1.7MB，16个文件（ko.jsonl 165KB, crossval.json 382KB, dedup-clusters.json 53KB, entity-resolution.jsonl 344KB, discarded.jsonl 375KB, review/ledger.jsonl 124KB, review/votes.jsonl 190KB, 4张PNG图） |
| benchmark ref vs got | ⚠️ 无正式基准 | tensor_benchmark_cases 表中无 KBM-TKC-GOV-SCALE 条目；替代验证：pilot批200篇+矛盾检测器受控注入标定（recall=1.00@≥15%，0假阳性）+ dedup敏感性扫描 |
| repro_cmd 可执行 | ✅ 通过 | `python scripts/kbm_gov_w1.py verify --out runs/kbm-gov-w1` → 8项复核全绿 |

### ② 报告六段核验

| 要素 | 状态 |
|---|---|
| ①案例介绍 | ✅ 完整（物理背景/几何/参数表） |
| ②方法流程 | ✅ 完整（六阶段管线+关键设计选择） |
| ③计算结果 | ✅ 完整（数字表，程序化注入零手抄） |
| ④结果图 | ✅ 4张PNG（漏斗/去重/标定/泳道） |
| ⑤注意点 | ✅ 完整（6条坑/局限/适用范围） |
| ⑥误差判定 | ✅ 完整（6项逐项vs基准，显式回答<3%） |

### ③ 测试核验
- `tests/test_kbm_gov.py`: **25/25 passed** (0.24s)
- 覆盖：实体解析、去重双层、交叉验证、矛盾检测、评审池、桶对账、端到端确定性、pilot工件复算

### ④ verify 复核
- 8项检查全绿：ledger_chain_ok / dedupe_recomputes / crossval_recomputes / slice_sha256_matches / all_ko_relocate(153/153) / buckets_reconcile / writeback_matches_ledger / refusals_accounted

## 判级（L0-L5）

** verdict: L3（系统集成）**

| 级别 | 判定 | 理由 |
|---|---|---|
| L0 文档成果 | ❌ | 有真实代码实现 |
| L1 数学/单元验证 | ✅ | 25项单元测试覆盖核心逻辑 |
| L2 独立功能实现 | ✅ | ke/gov.py 1303行，输入→计算→输出完整 |
| L3 系统集成 | ✅ | 接入平台 tensor_reports，有清晰入口，pilot批端到端运行 |
| L4 基准验证 | ❌ | 无 tensor_benchmark_cases 正式基准用例；矛盾检测标定属集成验证 |
| L5 科研工程成果 | ❌ | 未达L4故不评L5 |

**降级说明**：声称可能为L4+，但无正式基准用例（tensor_benchmark_cases 表中无对应条目），矛盾检测器标定（受控注入）属集成验证而非数值基准验证，故判L3。

## 落表

```sql
INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES ('TensorKnowledge', 'm15721 KBM-TKC-GOV-SCALE', 15906, 3, '<JSON>', 'board-audit');
```

已执行，rowid=29。

## 独立性声明

本审计由 m15906 独立执行，非 m15721 作者。核验基于工作树文件、测试运行结果、verify命令输出、数据库落表。未修改 m15721 任何文件。
