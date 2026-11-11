# m15255 KBM-CONSUME-W1 交差审计报告

**审计任务**: m15270 (board-audit)
**审计对象**: m15255 (KBM-CONSUME-W1·报告洗掘·agent消费研究A/B+KB设计建议v1·TensorKnowledge)
**审计日期**: 2026-11-11

---

## ① 取证：验收三件套核验

### 1.1 run_artifacts 文件存在性 ✅

| 工件路径 | 大小 | 状态 |
|---|---|---|
| artifacts/kb_retrieval/bench.json | 存在 | ✅ |
| artifacts/kb_retrieval/bench.md | 存在 | ✅ |
| artifacts/kb_retrieval/cards_snapshot.json | 存在 | ✅ |
| artifacts/kb_retrieval/holdout/bench.json | 存在 | ✅ |
| artifacts/kb_consumption/summary.json | 存在 | ✅ |
| artifacts/kb_consumption/audit.json | 存在 | ✅ |
| runs/kb_ab_20261111T210100Z/summary.json | 存在 | ✅ |
| runs/kb_ab_20261111T210100Z/results.jsonl | 存在 | ✅ |
| runs/kb_ab_20261111T210100Z/prereg.json | 存在 | ✅ |

### 1.2 benchmark ref vs got 数值核验 ✅

**基准裁判**（benchmarks/kb_retrieval_gold_v1.json 预注册阈值）:
- precision_at_1 ≥ 0.8
- recall_at_5 ≥ 0.9
- mrr_at_5 ≥ 0.7

**got 实测值**（artifacts/kb_retrieval/bench.json）:
| 指标 | ref（旧行为） | got（新读路径） | 阈值 | 判定 |
|---|---|---|---|---|
| precision_at_1 | 0.65 | **0.85** | ≥0.8 | ✅ PASS |
| recall_at_5 | 0.70 | **0.90** | ≥0.9 | ✅ PASS |
| mrr_at_5 | 0.675 | **0.875** | ≥0.7 | ✅ PASS |

**holdout 集**（n=10，独立题集）:
- precision_at_1: PASS
- recall_at_5: PASS
- mrr_at_5: PASS

**改进幅度**: 三项指标均比旧行为（naive_overlap）提升 +0.20。

### 1.3 repro_cmd 可执行性 ✅

```bash
cd /root/tp-agent/work/m15255 && python3 scripts/kb_retrieve_bench.py --cards artifacts/kb_retrieval/cards_snapshot.json
```

已实际执行，退出码 0，输出与 bench.json 一致。

### 1.4 报告六段完整性 ⚠️

m15255 工作树中**无 report_m15255.json**。存在的报告文件为其他任务（m14522/m15180/m8813）。
但 artifacts/kb_retrieval/bench.md 提供了完整的基准报告（六要素中的①③⑤⑥），
docs/ke/kb-consumption-v1.md 提供了方法说明（②）。
**缺失**: 正式 tensor_reports API 发布记录（report_m15255.json）。

---

## ② 判级（L0-L5）

| 级别 | 标准 | 是否满足 | 证据 |
|---|---|---|---|
| L0 | 文档成果 | ✅ | docs/ke/kb-consumption-v1.md, bench.md |
| L1 | 数学/单元验证 | ✅ | 14+7+25=46 个单元测试全部通过 |
| L2 | 独立功能实现 | ✅ | ke/consume.py (374行) + ke/api.py (433行)，真实输入→计算→输出 |
| L3 | 系统集成 | ✅ | /kb/search HTTP 端点集成到 KE API，FastAPI TestClient 验证 |
| L4 | 基准验证 | ✅ | 20题预注册基准 + holdout集，ref vs got 对照，全部阈值达标 |
| L5 | 科研工程成果 | ❌ | 未接入主求解器/平台核心流程，属平台工具层 |

**判定: L4** — 完整基准验证（预注册题集+阈值+可复现+误差分析），但未达到 L5 的科研工程成果级别。

---

## ③ 落表

SQL 已生成: `verdict_m15255.sql`
因权限限制无法直接 INSERT，SQL 已写入工作树供平台执行。

---

## ④ 发现与备注

### 正面发现
1. **预注册纪律严格**: 阈值在看到任何 bench 数字前写定，sha256 入档
2. **对照组设计合理**: naive_overlap 作为 ref 臂，精确复现旧行为
3. **测试覆盖全面**: 46 个测试覆盖 tokenize/rank/retrieve/endpoint/injection
4. **honest-FAIL 保留**: q16/q17/q20 未命中如实记录，未调阈值粉饰

### 待改进
1. **report_m15255.json 缺失**: 未通过 tensor/reports API 发布正式报告
2. **got_domain 表现差**: precision@1=0.0（仅2题，q17/q20），说明 capability 卡缺少 keywords 面
3. **负例题 n02 假阳性**: got 臂返回了不相关卡（score=3.0），词面检索的已知局限

---

## ⑤ 最终裁定

**gate_state**: confirmed（消账）
**理由**: 三件套齐全（run_artifacts/benchmark/repro_cmd），基准数值经独立复算确认达标，
测试全部通过，代码为真实功能实现（非桩/非硬编码）。L4 判级合理。
唯一缺失（report_m15255.json）不阻塞功能实质判定。
