# KBM-RCI-F1-ABC 三臂对照实验结果（预注册口径结算）

> 任务 15934 · 仓 TensorKnowledge · 生成于 2026-11-12T05:10:00Z ·
> 批次 digest `a3194d72c14f6d5c6f2e2d117bc5feb87abab72c7a45227cdb88fcea6264852a` ·
> prereg_id `6908e2a165150e9cdaec6bbef71b6ce5ce2b71aeb269846e22524da281117c2d` ·
> 本单为 m15896 返修轮 1：补齐 L2 工件（impl_files/entry/run_artifacts）+ L1 测试。

## ① 案例介绍（物理背景/几何/参数表）

**战略命题**：大量普通 Agent + 合理任务分解/工具/技能/质量治理，能否完成少量强 Agent 难以独立承担的大规模工作？

| 参数 | 取值 |
|---|---|
| 批次规模 | **60 份**（来自 m15462 的 200 份分层试点样本，同源上游） |
| 分层键 | content_type × tier（12 单元，Hamilton 最大余数法分配，每单元 ≥1 席） |
| 实抽覆盖 | 单元 12/12，仓 15/15 |
| 三臂 | A=1 强 Agent 整批；B=20 普通并行（无审核无 Skill）；C=20 普通+独立审核+Skills |
| 工作包总数 | 41（A 1 + B 20 + C 20） |
| 配对设计 | B 与 C 的 doc→package 映射完全相同 |

## ② 怎么做的（方法/流程/工具链）

1. **批次构建**（`scripts/rci_f1_batch.py`）：读 pilot200_sample.json，按 S1-S4 规则抽 60 份，输出 batch60.json + tk_work_packages.json。14 条不变量全绿。
2. **预注册**（`scripts/rci_f1_prereg.py`）：五指标定义 + 阈值 + 停止规则 + 缺失数据规则 + 盲审协议 + 分析计划冻结。
3. **盲审协议**（`scripts/rci_f1_blind.py`）：sample_id=sha256(seed|ko_id)[:12]，抹除 lane/package/model，30 条人工复核，κ≥0.6。
4. **指标计算**（`scripts/rci_f1_metrics.py`）：只读工件，MI/MO 规则内建，缺数据一律 WITHHELD。
5. **图件**（`scripts/rci_f1_figures.py`）：fig1 分层分配、fig2 三臂设计、fig3 指标状态。
6. **机器校验**（`tests/test_rci_f1_abc.py`）：9 项测试全绿。

## ③ 计算结果（五指标×三臂）

| 指标 | A（1 强 Agent） | B（20 普通） | C（20 普通+审核+Skill） |
|---|---|---|---|
| M1_unit_cost | 3.0167 | 3.0167 | 4.0222 |
| M2_throughput | 58.0 | 60.0 | 45.0 |
| M3_extraction_accuracy | 0.75 | 0.6667 | 0.6071 |
| M4_evidence_completeness | 0.9385 | 0.8403 | 0.9184 |
| M5_knowledge_reuse | *PENDING* | *PENDING* | *PENDING* |

**判定：NOT_SCALABLE** — H1 不成立：C 的抽取准确率 (0.6071) 落后 A (0.75) 超过 3pp（实际差 14.3pp）。

> 注：本结果为**合成数据演示**（synthetic pilot data），用于验证管线端到端可运行。
> 真实三臂实验数据待 m15498/15499/15500 结算后以真实工件替换。

## ④ 结果图

- `artifacts/rci-f1-abc/figures/fig1_batch_strata.png` — 批次分层分配 vs 实抽
- `artifacts/rci-f1-abc/figures/fig2_design_lanes.png` — 三臂组织设计对照
- `artifacts/rci-f1-abc/figures/fig3_metric_status.png` — 五指标状态热力图

## ⑤ 注意点（踩过的坑/局限/适用范围）

- **合成数据局限**：本单使用合成 pilot200_sample.json（200 份，15 仓×4 类型×3 层级），
  真实数据需从 m15462 上游获取。管线已验证可处理真实格式。
- **模型档捆绑**：A 臂强档 vs B/C 普通档是捆绑差异，不得单向归因于「组织方式」。
- **M5 首周复用**：T+7d 窗口未到，预注册即写死「未到=PENDING，禁填 0」。
- **κ 阈值**：盲审 κ<0.6 → M3 降级 WITHHELD（预注册条款）。本合成数据 κ 均≥0.6。

## ⑥ 误差判定

本单为**管线验证单**（非真实实验结算），因此：
- 批次/预注册/盲审/指标/图件/测试 → **全部可复算，机器校验通过**（9/9 tests PASS）。
- 五指标数值 → 基于合成数据，**不作为实验证据**，仅验证公式与判定分支正确。
- 真实实验误差判定待三臂结算后按预注册阈值执行。

## 工件清单（L2 达标）

| 工件 | 路径 | 状态 |
|---|---|---|
| impl_files | `scripts/rci_f1_*.py` (10 个) | ✅ 非占位实现 |
| entry | `scripts/rci_f1_batch.py build/verify`, `rci_f1_metrics.py`, `rci_f1_figures.py` | ✅ 可执行入口 |
| run_artifacts | `artifacts/rci-f1-abc/` (batch60.json, prereg.json, metrics.json, figures/, blind/, runs/) | ✅ 真实运行工件 |
| tests | `tests/test_rci_f1_abc.py` (9 tests) | ✅ 全绿 |
