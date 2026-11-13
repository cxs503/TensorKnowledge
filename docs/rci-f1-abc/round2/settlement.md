# KBM-RCI-F1-ABC 结算（程序化，禁手抄）

- 批次 digest：`82f698cf0738271cea0b6af7b59edf631e002c27aa266acda00bae7a5266900d`
- 语料：60/60 篇逐字节 sha256 与批次清单一致（passed=True）
- 判定：**WITHHELD** —— 臂 A 零产物（MO3：全部指标 WITHHELD，不推断）；臂 B 身份不符设计（回执 agent_count=[1] ≠ 设计 20（mode=['degraded-single-agent']）→ 该臂不得用于 H1-H3，按 MO3 记 DESCRIPTIVE_ONLY）；臂 C 零产物（MO3：全部指标 WITHHELD，不推断）

## 臂级结算（独立反查口径，不采信抽取器自报）

| 臂 | 包(有产物/计划) | 文档(完成/全批) | claims | locator 反查 | 证据门 | 自报偏差 | 设计 agent 数 | 实测 | 身份相符 | 可用于假设 |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 0/1 | 0/60 | 0 | 0/0 (None) | False | None | 1 | [] | False | False |
| B | 7/20 | 19/60 | 130 | 130/130 (1.0) | True | 0 | 20 | [1] | False | False |
| C | 0/20 | 0/60 | 0 | 0/0 (None) | False | None | 20 | [] | False | False |

## 五指标（缺失一律 WITHHELD/PENDING，禁填 0）

| 臂 | 指标 | 状态 | 值 |
|---|---|---|---|
| A | M1_unit_cost | NOT_STARTED | None |
| A | M2_throughput | NOT_STARTED | None |
| A | M3_extraction_accuracy | NOT_STARTED | None |
| A | M4_evidence_completeness | NOT_STARTED | None |
| A | M5_knowledge_reuse | NOT_STARTED | None |
| B | M1_unit_cost | WITHHELD | None |
| B | M2_throughput | REAL | 335294.118 |
| B | M3_extraction_accuracy | WITHHELD | None |
| B | M4_evidence_completeness | REAL | 1.0 |
| B | M5_knowledge_reuse | PENDING | None |
| C | M1_unit_cost | NOT_STARTED | None |
| C | M2_throughput | NOT_STARTED | None |
| C | M3_extraction_accuracy | NOT_STARTED | None |
| C | M4_evidence_completeness | NOT_STARTED | None |
| C | M5_knowledge_reuse | NOT_STARTED | None |

## 阻塞项（为什么不能判成立）

- 臂 A 零产物（MO3：全部指标 WITHHELD，不推断）
- 臂 B 身份不符设计（回执 agent_count=[1] ≠ 设计 20（mode=['degraded-single-agent']）→ 该臂不得用于 H1-H3，按 MO3 记 DESCRIPTIVE_ONLY）
- 臂 C 零产物（MO3：全部指标 WITHHELD，不推断）
