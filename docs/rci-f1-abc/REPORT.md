# KBM-RCI-F1-ABC 三臂对照实验结果（预注册口径结算）

> 任务 15496 · 批次 digest `82f698cf0738271cea0b6af7b59edf631e002c27aa266acda00bae7a5266900d` · prereg_id `9e4e0bf551c63599548c2f9d9ef19b562c1eed0bdbeab5a614ac75a8d18a201f` ·
> 五指标冻结口径见预注册报告（先于执行发布）。

## ① 案例介绍
同批 60 份文档（12 分层单元 / 15 仓），三臂organizaton 对照：A=1 强 Agent 整批，B=20 普通并行（无审核无 Skill），
C=20 普通 + 独立审核 + Skills。判定规则预注册冻结：H1 质量非劣（≤3pp）、H2 吞吐 ≥3×A、H3 单位成本 ≤A。

## ② 怎么做的
派单记录（goal 全文 sha256 可复算）：

| 臂 | mission_id | 模型 | goal 字符 | goal sha256 |
|---|---|---|---|---|
| A | 15498 | Qwen3.8-27B | 7487 | `e078050f641720df` |
| B | 15499 | deepseek-v4-flash | 9348 | `518f314113199147` |
| C | 15500 | deepseek-v4-flash | 9364 | `9ee0afa9cc507bbc` |

## ③ 计算结果（程序化注入，artifacts/rci-f1-abc/metrics.json）

| 臂 | 指标 | 状态 | 值 | 分量 |
|---|---|---|---|---|
| A | M1_unit_cost | NOT_STARTED | None | {} |
| A | M2_throughput | NOT_STARTED | None | {} |
| A | M3_extraction_accuracy | NOT_STARTED | None | {} |
| A | M4_evidence_completeness | NOT_STARTED | None | {} |
| A | M5_knowledge_reuse | NOT_STARTED | None | {} |
| B | M1_unit_cost | NOT_STARTED | None | {} |
| B | M2_throughput | NOT_STARTED | None | {} |
| B | M3_extraction_accuracy | NOT_STARTED | None | {} |
| B | M4_evidence_completeness | NOT_STARTED | None | {} |
| B | M5_knowledge_reuse | NOT_STARTED | None | {} |
| C | M1_unit_cost | NOT_STARTED | None | {} |
| C | M2_throughput | NOT_STARTED | None | {} |
| C | M3_extraction_accuracy | NOT_STARTED | None | {} |
| C | M4_evidence_completeness | NOT_STARTED | None | {} |
| C | M5_knowledge_reuse | NOT_STARTED | None | {} |

**预注册先于执行**：prereg 报告落盘于 `2026-11-12T00:42:43.035152+00:00`，三臂 mission 创建于 A=2026-11-12T00:42:44.934187+00:00、B=2026-11-12T00:42:44.996036+00:00、C=2026-11-12T00:42:45.049823+00:00；顺序审计 = True（工件 `artifacts/rci-f1-abc/prereg_ordering_audit.json`，可由 `scripts/rci_f1_audit.py` 复算）

**判定**：`WITHHELD` — 关键质量指标不可得（A/C 的 M3/M4 未结算）→ WITHHELD，不判成立与否
假设逐项：{}

## ④ 结果图
图1 批次分层；图2 三臂设计；图3 五指标×三臂数据可得性矩阵（绿=实测，灰=WITHHELD/未结算）。

## ⑤ 注意点
- 模型档捆绑（A 强档 vs B/C 普通档），见预注册混淆变量声明。
- 允许失败不允许伪造：不可得指标写 WITHHELD（禁填 0）；诚实 FAIL 不改数。
- 生产口径：mission succeeded ≠ KO 审核通过 ≠ 科学验证通过（三状态分离）。

## ⑥ 误差判定
实验数值 vs 预注册阈值逐项对照在③表与判定段落列明；本报告不引入任何未在工作中的数字。
若某指标不可得，已显式标 WITHHELD 并写明原因（不宣称 <3% 之类无法支撑的结论）。
