# KBM-GOV-W1 多 Agent 知识治理规模化 v1 —— 交付报告（程序化生成）

> 锚点 KBM-TKC-GOV-SCALE · mission 19208 · run_at=2026-11-12T02:30:00Z · config=1.0.0 · policy=ke-review-v0.1
> 本文件由 `scripts/kbm_gov_report.py` 从 `runs/kbm-gov-w1/` 工件注入生成，**零手抄**。

## ① 案例介绍

**物理/工程背景**：TensorKnowledge 已沉淀 claim/evidence/provenance/review-event 四契约与评审状态机，但缺少规模化治理层——同一物理量的多来源数值没有对照口径、同一结论的重复陈述没有聚簇、矛盾既无判定阈值也无标定，评审未池化，且历史上同一批知识出现「20 vs 257」式口径病（分母不一致）。本层把治理做成可复算的机器裁决流程，并在平台真实报告语料上产出三个可复核的真数。

**语料（固定切片，可证伪）**：平台 `tensorplatform.tensor_reports` 中 `status='published' AND length(markdown)>=1500 ORDER BY id ASC LIMIT 200`，快照身份 `snapshot.json:snapshot_digest`（逐篇 sha256），复核时按 id 重取逐篇比对。本批 B0=200 篇。

**参数表（`governance/gov-config-v1.json`，预注册，代码不硬编码）**

| 参数 | 值 | 含义 |
|---|---|---|
| entity vocab | 21 实体 / 95 别名 | 实体解析闭世界词表（不模糊匹配） |
| agree_rel | 0.05 | 跨来源一致判定门（对齐平台精度标准口径） |
| contradict_rel | 0.15 | 矛盾判定门（>15% 且条件齐备才判矛盾） |
| min_entity_confidence | 1 | 实体解析最低置信（闭世界→1.0；基名+限定词→0.9 被拒） |
| near_dup_hamming | 6 | simhash 汉明门（本语料惰性，见 ⑤） |
| near_dup_jaccard | 0.5 | 语义去重：数字掩码后词集 Jaccard 门 |
| value_significant_digits | 6 | 数值比较的有效位（避免浮点尾部噪声） |
| review pool | 8 reviewer（4 泳道 × 2 实例） | consistency / entity / provenance / units |
| review policy | dual-blind-quorum-v1 | 双盲仲裁 + quorum 折叠 |
| policy_version | ke-review-v0.1 | 复用仓内评审状态机，不另建并行状态机 |

## ② 怎么做的

```
tensor_reports(固定切片) → 数量语句抽取(正则 name=value[unit])
  → 实体解析(别名闭世界, 置信 1.0 / 基名+限定词 0.9)
  → 去重(L1 精确指纹 / L2 语义 Jaccard) → 交叉验证(同实体+限定词+单位, 跨报告配对)
  → 矛盾发现(需双方齐备数值条件, 否则 unverified_comparison)
  → 评审池(双实例 + 仲裁 + 状态机 fold, 逐行 sha256 链)
  → 三口径统计 B0/B1/B2（Counting.reconcile() 硬校验, 非法 bucket 抛异常）
```

**工具链**：`ke/gov.py`（治理内核，纯 Python 无外部服务依赖）· `scripts/kbm_gov_w1.py`（跑批/verify/queue）· `scripts/kbm_gov_ablation.py`（注入标定 + 阈值扫描 + 5 图）· `tests/test_kbm_gov.py`（25 用例）· matplotlib 3.10 出图、psql COPY 取语料、pytest 判据、ruff 静态检查。

**关键设计选择**（决定误差性质）

1. 评审事件只写 `review_status`，不改写 `epistemic_status`（证据等级由证据面独立判定，A3 轴不混淆）。
2. 矛盾判定必须钉住物理算例：需 ≥1 个数值条件（Re/Fr/α…）双方齐备，几何单独成立不算条件 → no silent promotion。
3. 同报告内配对不进交叉验证（那是去重的职责）；`err`（相对误差）标为 `document_local` 不参与跨报告比对。
4. 三口径互斥：每个报出的数字必须声明 bucket，五个对账不变量任一不成立即抛异常。

## ③ 计算结果

**验收三真数（口径随数）**

| 指标 | 值 | 分母（口径） | 公式 |
|---|---|---|---|
| 重复率 | 16.34% | B1=153 | (B1 − 簇数 128)/B1 = 25/153 |
| 可裁定矛盾对数 | 0 | 跨报告配对 796 | 同条件且 abs(Δ)/max > 15% |
| 评审通过率 | 69.93% | B1=153 | pass 107/B1 |

**三口径分离**

| 口径 | 定义 | 值 | 对账 |
|---|---|---|---|
| B0 原始记录 | 切片内源文档数 | 200 | 逐篇 sha256（snapshot.json） |
| — 候选数量语句 | 正则抽取（含被丢弃） | 2870 | = 丢弃 2303 + 上下文 414 + KO 153 |
| B1 待评审 KO | 通过实体解析与零手抄复算者 | 153 | = 评审队列长度 |
| B2 经治理 KO | 评审通过且为去重簇代表 | 89 | pass 107 = 代表 89 + 重复成员 18 |

**分解**

| 项 | 数 | 说明 |
|---|---|---|
| 丢弃：entity_unresolved | 1910 | 词表外符号（闭世界，宁缺勿滥） |
| 丢弃：value_is_expression | 236 | 如 `Cd = 24/Re`，公式非观测值 |
| 丢弃：not_quantity_name | 157 | 如 snake_case 配置键 |
| 实体解析率 | 22.89% | 候选名 → 实体 |
| 去重簇 | 128（L1 精确 13 / L2 语义 6） | 簇规模 1:109 2:14 3:4 4:1 |
| 评审 | pass 107 / needs-fix 46 / fail 0 | needs-fix 全部来自实体限定词未注册（ENTITY_QUALIFIER_UNVERIFIED） |
| 评审拒绝事件 | 0 | 自批拦截记 refused.json（本批 0 次，用例覆盖该路径） |
| 引用账本 | 逐行 sha256 链 | review/ledger.jsonl，verify 逐行复算 |

**交叉验证分组判定**

| pair 判定 | 对数 | 含义 |
|---|---|---|
| agree | 132 | 跨来源一致（≤5%） |
| incomparable_conditions | 332 | 条件键不可比 |
| unverified_comparison | 332 | 高分歧但条件不全 → 不判 |

**矛盾检测器标定（受控注入，母体=真实 KO）**

| 注入倍率 | 诱导相对分歧 |Δ|/max | 期望判定 | 命中/注入 | recall | 旁生对 |
|---|---|---|---|---|---|
| 1.02 | 1.96% | agree | 0/19 | 0.00 | 0 |
| 1.05 | 4.76% | agree | 0/19 | 0.00 | 0 |
| 1.10 | 9.09% | divergent | 0/19 | 0.00 | 0 |
| 1.20 | 16.67% | contradicted | 19/19 | 1.00 | 0 |
| 1.35 | 25.93% | contradicted | 19/19 | 1.00 | 0 |
| 1.50 | 33.33% | contradicted | 19/19 | 1.00 | 0 |
| 2.00 | 50.00% | contradicted | 19/19 | 1.00 | 0 |

**阈值扫描**

| contradict_rel | 矛盾对数 | 注入 recall | 旁生对 |
|---|---|---|---|
| 5% | 19 | 1.00 | 0 |
| 10% | 19 | 1.00 | 0 |
| 15% | 19 | 1.00 | 0 |
| 20% | 19 | 1.00 | 0 |
| 30% | 19 | 1.00 | 0 |
| 50% | 0 | 0.00 | 0 |

**去重敏感性**

| near_dup_jaccard | 簇数 | 重复率 |
|---|---|---|
| 0.3 | 118 | 22.88% |
| 0.4 | 121 | 20.91% |
| 0.5 | 128 | 16.34% |
| 0.6 | 131 | 14.38% |
| 0.7 | 133 | 13.07% |
| 0.8 | 134 | 12.42% |
| 0.9 | 134 | 12.42% |
| 0.0 | 128 | 16.34% |
| 2.0 | 128 | 16.34% |
| 4.0 | 128 | 16.34% |
| 6.0 | 128 | 16.34% |
| 8.0 | 128 | 16.34% |
| 10.0 | 128 | 16.34% |
| 12.0 | 128 | 16.34% |

**复核（verify 8 项）**

| 检查 | 结果 |
|---|---|
| all_ko_relocate | True |
| buckets_reconcile | True |
| crossval_recomputes | True |
| dedupe_recomputes | True |
| ledger_chain_ok | True |
| refusals_accounted | True |
| slice_sha256_matches | True |
| writeback_matches_ledger | True |

## ④ 结果图

| 图 | 内容 | 读法 |
|---|---|---|
| f1-funnel | B0→候选→B1→pass→B2 | 数量级落差来自闭世界实体解析（2870→153），是「宁缺勿滥」的直接代价 |
| f2-dedup | 簇规模 + 去重层级 | 重复簇里精确层与语义层各占一部分 |
| f3-contradiction-calibration | recall vs 诱导分歧 | 曲线在 9.1%→16.7% 之间跳变，与 15% 阈值一致 |
| f4-review-lanes | 泳道票型堆叠 | provenance/units 全绿；entity 泳道是 needs-fix 唯一来源 |
| f5-sensitivity | 两个阈值的扫描曲线 | near_dup_jaccard 单调（阈值有效）；contradict_rel 0.15 处 recall=1 且零旁生 |

## ⑤ 注意点（坑 · 局限 · 适用范围）

1. **条件覆盖是本层天花板**：B1=153 中仅 19 条（12.4%）带数值条件，故 664 对高分歧只能判不可裁定。真实语料「可裁定矛盾 = 0」是数据条件不足的诚实结论，不是检测器失效（注入实验 recall=1.00 已证）。W2：从表格表头/小节标题结构化抽条件。
2. **跨语言改写不去重**：中英同一结论不合并（用例 `test_cross_language_rewording_is_a_known_non_merge` 固化为已知边界）。
3. **simhash 层在本语料惰性**：153 条小语料 3-gram simhash 稀疏（同义改写汉明距离 23–37），语义召回实际由 Jaccard 承担——如实登记，不夸大「双层」。
4. **审批独立性靠状态机**：approve 需身份不冲突，冲突即 SELF_APPROVAL_BLOCKED 记 refused；不依赖 agent 自觉。
5. **切片是固定 id 切片而非时间片**：对新报告免疫；报告正文若被编辑，verify 的 slice_sha256_matches 会红——设计意图（快照可证伪）。
6. **口径纪律**：三个验收数都挂 B1；B0 与 B2 不可与 B1 混用，代码层已拦截。

## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3%）

| 关键量 | 基准 | 实测 | 误差 | 是否 <3% |
|---|---|---|---|---|
| 重复率 | 可复算真值 25/153 | 16.3399% | 0（verify dedupe_recomputes=true） | ✅ 是 |
| 可裁定矛盾对数 | 控制组真值 0 / 注入组期望 19 | 0 / 19 | 0 | ✅ 是 |
| 评审通过率 | 可复算真值 107/153 | 69.9346% | 0（verify writeback_matches_ledger=true） | ✅ 是 |
| 零手抄复算率 | 153/153 可回原文复算 | 153/153 | 0 | ✅ 是 |
| 检测器 recall | 预注册阈值语义（≥15% 必中） | 1.00 | 边界一致 | ✅ 是 |
| 检测器假阳性 | 真实语料矛盾 = 0 | 0 | 0 | ✅ 是 |
| 条件覆盖 | 无基准（本层自报） | 12.42% | — | ⚠ 无基准，原因：语料自身不陈述条件，属能力边界非计算误差 |

**说明**：上表前 6 项均为**确定性复算**（同一工件重算差 0，两次跑批 19 个工件 sha256 全等），不存在统计误差；第 7 项是覆盖度而非精度，无外部基准可比，故不填 3%。

## 复现

```bash
python scripts/kbm_gov_w1.py run    --out runs/kbm-gov-w1 --limit 200 --min-chars 1500
python scripts/kbm_gov_w1.py verify --out runs/kbm-gov-w1     # 8/8 all_ok
python scripts/kbm_gov_ablation.py  --out runs/kbm-gov-w1     # 标定+敏感性+5 图
python -m pytest tests/test_kbm_gov.py -q                     # 25 passed
python scripts/kbm_gov_report.py    --out runs/kbm-gov-w1     # 生成本报告 + 平台 payload
```
