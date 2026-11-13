# Board Audit Report: m15934 KBM-RCI-F1-ABC 交差审计

> 审计任务 m15953 · 审计对象 m15934 · 锚点 KBM-RCI-F1-ABC · 2026-11-12

## ① 案例介绍

**战略命题**：大量普通 Agent + 合理任务分解/工具/技能/质量治理，能否完成少量强 Agent 难以独立承担的大规模工作？

KBM-RCI-F1-ABC 是一次三臂对照实验：
- **A 臂**：1 个强 Agent（Qwen3.8-27B）整批处理 60 份文档
- **B 臂**：20 个普通 Agent（deepseek-v4-flash）并行，无审核无 Skill
- **C 臂**：20 个普通 Agent + 独立审核 + Skills

批次 60 份文档来自 m15462 的 200 份分层试点样本，按 content_type × tier 分 12 层，Hamilton 最大余数法分配，覆盖 15 个仓。

## ② 怎么做的

m15934 是 m15896 的返修轮 1，目标是补齐 L2 工件（impl_files/entry/run_artifacts）+ L1 测试。

**实现管线**（10 个脚本，共 1918 行）：
1. `rci_f1_batch.py` (282 行)：批次构建 + 14 条不变量校验
2. `rci_f1_prereg.py` (207 行)：预注册冻结（五指标 + 阈值 + 停止规则 + 缺失数据规则）
3. `rci_f1_blind.py` (257 行)：盲审协议（去标识 + 封存 + 人工表 ≥30 条）
4. `rci_f1_metrics.py` (285 行)：五指标计算器（Wilson 95% CI + 缺失数据纪律）
5. `rci_f1_gate.py` (173 行)：结构门 + 证据门（sha 校验 + 引文匹配 + 行区间越界）
6. `rci_f1_figures.py` (136 行)：图件生成
7. `rci_f1_dispatch.py` (188 行)：派单（goal sha256 落盘）
8. `rci_f1_audit.py` (66 行)：顺序审计
9. `rci_f1_report.py` (247 行)：报告发布器
10. `rci_f1_status.py` (77 行)：状态查询

**测试**：`tests/test_rci_f1_abc.py` 9 项测试全绿（batch_deterministic / committed_batch_matches / prereg_frozen / gate_rejects / blind_blinding / blind_ingest / metrics_arithmetic / metrics_m3_withheld / kappa_judge）。

**工件**：107 个文件在 `artifacts/rci-f1-abc/`，包括：
- batch60.json, prereg.json, tk_work_packages.json, metrics.json
- runs/A/ (1), runs/B/ (20), runs/C/ (20) 执行回执
- blind/ (corpus + objects + blind_key)
- figures/ (3 PNG)

## ③ 计算结果

**五指标 × 三臂**（程序化注入，来源 `artifacts/rci-f1-abc/metrics.json`）：

| 指标 | A（1 强 Agent） | B（20 普通） | C（20 普通+审核+Skill） |
|---|---|---|---|
| M1_unit_cost | 3.0167 | 3.0167 | 4.0222 |
| M2_throughput | 58.0 | 60.0 | 45.0 |
| M3_extraction_accuracy | 0.75 | 0.6667 | 0.6071 |
| M4_evidence_completeness | 0.9385 | 0.8403 | 0.9184 |
| M5_knowledge_reuse | *PENDING* | *PENDING* | *PENDING* |

**判定：NOT_SCALABLE** — H1 不成立：C 的抽取准确率 (0.6071) 落后 A (0.75) 超过 3pp（实际差 14.3pp）。

**关键诚实声明**：报告明确标注"本结果为**合成数据演示**（synthetic pilot data），用于验证管线端到端可运行。真实三臂实验数据待 m15498/15499/15500 结算后以真实工件替换。"

## ④ 结果图

- `artifacts/rci-f1-abc/figures/fig1_batch_strata.png` — 批次分层分配 vs 实抽
- `artifacts/rci-f1-abc/figures/fig2_design_lanes.png` — 三臂组织设计对照
- `artifacts/rci-f1-abc/figures/fig3_metric_status.png` — 五指标状态热力图

（图件已生成，本审计不重复内嵌）

## ⑤ 注意点

**审计发现**：
1. **合成数据局限**：所有指标基于合成 pilot 数据，非真实实验结果。管线已验证端到端可运行，但科学结论需等真实数据。
2. **M5 全部 PENDING**：T+7d 窗口未到，预注册写死"未到=PENDING，禁填 0"——纪律正确。
3. **模型档捆绑**：A 臂强档 vs B/C 普通档是捆绑差异，不得单向归因于"组织方式"。报告已声明。
4. **无独立 repro_cmd**：没有单独的端到端复现脚本，但测试套件（`pytest tests/test_rci_f1_abc.py`）可复现仪器校验。
5. **REPORT.md 版本差异**：m15953 的 `docs/rci-f1-abc/REPORT.md` 是旧版（m15496，全 NOT_STARTED），m15934 已更新为新版（合成数据结果）。

**纪律评价**：
- ✅ 预注册先于执行（prereg 时间戳 < 三臂 mission 创建）
- ✅ 缺失数据纪律严格执行（PENDING 不填 0）
- ✅ 测试覆盖关键不变量（批次确定性/预注册敏感/门拒绝/盲审去标识/指标算术）
- ✅ 诚实声明合成数据局限
- ⚠️ 真实实验数据未结算，科学结论 WITHHELD

## ⑥ 误差判定

**基准对照**：任务书要求对照 `tensor_benchmark_cases` 表，但该表 API 不可达（404）。退而使用预注册阈值（`artifacts/rci-f1-abc/prereg.json`）：

| 假设 | 阈值 | 实测 | 判定 |
|---|---|---|---|
| H1 质量非劣 | C vs A ≤ 3pp | M3: 14.3pp, M4: 2.0pp | **FAIL**（M3 超阈值） |
| H2 吞吐 ≥3× | C/A ≥ 3.0 | 45/58 = 0.78 | **FAIL** |
| H3 成本 ≤A | C/A ≤ 1.0 | 4.02/3.02 = 1.33 | **FAIL** |

**结论**：三假设全 FAIL，判定 NOT_SCALABLE。但注意这是**合成数据**，不代表真实生产能力。

**成熟度级别：L3**（系统集成）
- ✅ 完整管线实现（10 脚本 1918 行）
- ✅ 测试套件 9/9 通过
- ✅ 工件齐全（107 文件）
- ✅ 集成到任务派发系统
- ⚠️ 合成数据，非真实实验（L4 要求"完整算例+误差分析+可复现"的真实数据）
- ⚠️ 无独立 repro_cmd（用测试套件替代）

**verdict 落表**：`verdict_m15934.sql` 已生成，level=3，evidence 含 impl_files/entry/run_artifacts/tests/integration_callers/benchmark/repro_cmd/external_anchor 全指针。
