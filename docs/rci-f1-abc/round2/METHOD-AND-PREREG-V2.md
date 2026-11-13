# KBM-RCI-F1-ABC 第二轮 · 方法选型 + 预注册 v2 补遗（追加，不改 v1）

> 追加件纪律：v1（`docs/rci-f1-abc/frozen/prereg.json`，prereg_id
> `9e4e0bf551c63599548c2f9d9ef19b562c1eed0bdbeab5a614ac75a8d18a201f`）**一字不改**。
> 本文件只追加「怎样使 v1 的门可被判定」，不含任何臂间比较结果，也不使用臂结果数据定参数
> （把握度测算只用批次规模 n=60、门 margin=3pp、假设参照率 p_ref=0.90 —— 全部来自设计，不来自产出）。

## 1. 选型（三个候选 → 一个采用）

| 维度 | 候选 A：沿用 v1 的 Wilson CI 重叠规则 | 候选 B：正式非劣效 z 检验（NI） | 候选 C：贝叶斯后验 ROPE | 采用 |
|---|---|---|---|---|
| 可判定性 | 不可判定（半宽 7.7pp ≫ 门 3pp） | 可判定，且给出「需多少 n」 | 可判定但需先验，跨臂先验难对齐 | |
| 与 v1 兼容 | 是 | 是（同一 margin、同一 α 语义） | 否（换推断框架） | |
| 可复算/可审计 | 是 | 是（解析式 + 蒙特卡洛双路径） | 先验选择即审计面 | |
| 结论 | 保留为**次要**口径 | **主要口径** | 不采用 | **B 为主 + A 为副** |

配套选型：
- **κ 区间**：百分位自举（n≥120 时实测覆盖率 0.944，优于 Fleiss 近似 0.888@n=30）；
  自举种子与重复次数固定，结果可复算。
- **配对比较**：B/C 共用 doc→package 映射（v1 已冻结），允许 McNemar 配对检验；A 与 B/C 不成对，只能用独立两样本 NI。
- **分析单元**：主分析用**文档级**（n=60，保守）；claim 级按 deff 折算作敏感性分析（不替代主分析）。
- **成本口径**：M1 的 token 分量缺失即 WITHHELD（MO2），不得以 0 计入 —— 本轮修了 `rci_f1_metrics.py`
  的这个缺陷（修复前：`tokens=None` 被当 0 累加，无计量臂的成本被系统性低估，H3 判定失真）。

## 2. 预注册 v2 补遗（追加条款，编号 P1–P6）

- **P1（主判定）**：H1 质量非劣改为「非劣效检验」：单侧 α=0.025，margin=3pp，
  按文档级率计算；拒绝 H0（p_B−p_A ≤ −3pp）才算「非劣」。同时报 Wilson 95% CI（v1 口径）作参考。
- **P2（把握度前置）**：任何臂在跑之前，须报「本次 n 下 3pp 门的把握度」与「最小可证明界」。
  n=60/臂 时：把握度（真实差 0）**0.079**、最小可证明界 **15.3pp** → 该批次**不足以**判定 3pp 门。
- **P3（规模）**：若坚持 3pp 门且真实差 ≈0，需 n/臂 ≈ **1570**；真实差 −2pp 需 ≈ **15353**。
  现实路径二选一：(a) 扩批到 ≥1570 份/臂；(b) 把门放宽到 **≥15pp** 并在报告中明示门值。
  **不得**在 n=60 上宣称「3pp 非劣成立/不成立」。
- **P4（盲审可靠性）**：人工复核量按 κ 区间定：目标半宽 0.10 → **201** 条；下限
  `human_sample_min` 由 30 提为 **≥120**（实测自举覆盖率 0.944）。κ 区间用自举，不用 Fleiss 近似。
- **P5（臂身份门）**：每份回执必须带 `agent_count` / `mode` / `llm_used`；
  实测与设计不符（如 B 臂 `agent_count=1` vs 设计 20）→ 该臂指标降级 `DESCRIPTIVE_ONLY`，
  不得进入 H1–H3。此门由 `scripts/rci_f1_settle.py::arm_identity` 机器执行。
- **P6（不可得）**：M3/M5 不可得一律 WITHHELD/PENDING（v1 已有，本轮加了执行体与回归测试）。

## 3. 迁移方案（落到本仓的哪个执行体）

| 条款 | 执行体 | 机器验证 |
|---|---|---|
| P1/P2/P3 | `scripts/rci_f1_power.py`（`ni_power` / `ni_min_margin` / `ni_n_required`） | `tests/test_rci_f1_round2.py::test_power_invariants_and_independent_recompute`（恒等/单调/蒙特卡洛双路径） |
| P4 | `scripts/rci_f1_power.py`（`kappa_halfwidth` / `mc_kappa_coverage` / `mc_kappa_coverage_bootstrap`） | `::test_kappa_coverage_small_n_undercovered` |
| P5 | `scripts/rci_f1_settle.py::arm_identity` | `::test_settlement_withholds_and_audits_identity` |
| P6 | `scripts/rci_f1_metrics.py`（MO2 修复） | `::test_m1_withheld_when_tokens_missing` + v1 的 9 项测试 |
| 证据反查 | `scripts/rci_f1_verify.py`（独立重读快照字节） | `::test_verifier_kills_injected_faults`（篡改引文/sha/错行/缺文件四类注入必须判死） |
| 语料入版本 | `scripts/rci_f1_corpus.py` + `docs/rci-f1-abc/{frozen,snapshot}` | `::test_corpus_is_versioned_and_verifies`、`::test_corpus_detects_tampered_snapshot` |

## 4. oss_solutions 沉淀（feature_slug = `KBM-RCI-F1-ABC`）

| tag | 内容 |
|---|---|
| `ni-decidability-instrument` | 非劣效把握度/最小可证明界/样本量求解 + 蒙特卡洛独立复算 + κ 自举区间；用「设计参数」而非结果数据定参 |
| `independent-evidence-recheck` | 逐字节快照 sha256 + 行区间逐字引文反查，回执由反查器产出，抽取器自报仅作偏差对照 |
| `arm-identity-audit` | 回执 agent_count/mode 与预注册设计比对，不符即降级 DESCRIPTIVE_ONLY（防止「单进程跑出三臂结论」） |
| `negative:no-oss-reference` | ~/oss-cache 与 oss_inventory 无「批量抽取产线/评审可靠性」类实现可抄结构；方法走教科书/监管口径，缺口登记 |

迁移面：任何「多臂 / 多产线对照 + 人审质量指标」的实验（本生态里 A/B 实验、Skills 边际贡献、模型档位对照）
都可直接复用上述三件仪器；它们与领域无关，属 TensorKnowledge 的通用治理能力。