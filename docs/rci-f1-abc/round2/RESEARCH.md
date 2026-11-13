# KBM-RCI-F1-ABC 第二轮 · 调研（开源横向 + 方法谱系）

> 任务 m15896 · 上一轮 m15585 在本锚点 honest-FAIL（fail_stage / failure_reason 均未留）。
> 本文件按「失败=排序信号」先做调研，再决定这一轮动什么。所有数字由脚本产出，命令见文末。

## 0. 为什么上一轮会死在「测量仪器」而不是「实验本身」

对第一轮交付物做独立复核（不采信其结论文本），发现三个可复现的硬事实：

| # | 事实 | 复现方式 | 后果 |
|---|---|---|---|
| F1 | 干净检出里 `tests/test_rci_f1_abc.py` **5 failed / 4 passed** | `python -m pytest tests/test_rci_f1_abc.py -q`（修复前） | 锚点的全部断言依赖 `artifacts/`，而 `.gitignore` 忽略 `artifacts/` → 语料不入版本 |
| F2 | 语料（60 份冻结快照）、batch60、prereg、工作包台账全在 `artifacts/` 或未合并分支上 | `ls artifacts/rci-f1-abc` → 不存在；`docs/rci-f1-abc/snapshot` → 不存在 | 证据门（M4）无从反查 → 五指标只能 WITHHELD |
| F3 | 注释承诺的 `scripts/rci_f1_verify.py` 在主干上**不存在**（只在 m15499/m15500 工作树里） | `ls scripts/rci_f1_verify.py` | 「不采信抽取器自报」这条纪律没有执行体；B 臂回执里 `claims_with_locator_inprocess` 是抽取器自己数的 |
| F4 | B 臂实际执行 `mode=degraded-single-agent`、`agent_count=1`、`llm_used=false` | `docs/rci-f1-abc/arms/B/*/\_exec_metrics.json`、`provenance.json` | 臂身份 = 设计（B=20 普通并行）已被破坏，但没有任何代码检查这件事 |

结论：**上一轮不是「实验失败」，是「仪器从未存在」**。所以本轮先造仪器、先证仪器会判死，再谈跑臂。

## 1. 开源横向调研（集群节点 ~/oss-cache + oss_inventory）

`SELECT * FROM oss_inventory WHERE feature_slug ILIKE '%ABC%'` —— **该列不存在**，现表结构是
`repo / tier / focus / methods / summary`（共 33 行）。按任务给的口径调整后实测：

- 两节点 `~/oss-cache/` 缓存内容：`pylbm`、`hschwane/GraSPH`、`Maarten-vd-Sande_lbm` ——
  全部是 LBM/SPH 求解器缓存，**没有任何多智能体编排 / 批量抽取 / 评审一致性框架的实现**。
- `oss_inventory` 覆盖的是领域求解器仓（LBM/FEM/BEM 系），不含本次要的「产线组织 + 评审可靠性」类实现。
- `oss_solutions` 里同仓已有两条可迁移沉淀：`KPI-KB-10K / four-contract-extractive-harvest`（分层抽取口径）、
  `KBM-RCI-S1-REGISTRY / selected`（确定性规则 + 可审计分型），本轮的仪器沿用其「确定性 + 可复算」结构。

**诚实结论**：本轮**没有**现成 OSS 实现可直接抄结构（缓存里没有这类仓）。
所以方法谱系部分改走教科书/监管口径（第 2 节），并把「本类实现无 OSS 覆盖」作为缺口登记，
而不是编一个「参考了某仓」的说法。这一条本身进 `oss_solutions` 的 `evidence` 字段（见 §4）。

## 2. 方法谱系（标准做法 + 标准算例出处）

| 要做的事 | 成熟方法 | 出处（ref 原文，不引用未见全文的数字） | 迁移点 |
|---|---|---|---|
| 判「不劣于」而不是「相等」 | 非劣效（non-inferiority）检验：H0: p_B−p_A ≤ −δ，单侧 α=0.025 | Blackwelder 1982, *Control. Clin. Trials* 3:345–353；Farrington & Manning 1990, *Stat. Med.* 9:1447–1454；FDA 2016 NI 指导原则 | 把 prereg v1 的「CI 重叠即未分胜负」换成显式 NI 检验 + 把握度 |
| 样本量够不够 | 把握度分析 Power = Φ((Δ+δ)/√v − z_{1−α})，v 用替代假设方差 | 同上 + Cohen 1988 的效应量/把握度框架 | 先算 n，再跑臂；不够就扩批，而不是跑完再说 |
| 评审者一致性 | Cohen's κ + 区间估计；小样本用自举而非渐近 SE | Cohen 1960；Fleiss 1981 *Stat. Methods for Rates and Proportions*（近似 SE）；Donner & Eliasziw 1992, *Stat. Med.* 11:1511–1519 | 人工复核量按 κ 区间半宽定，不按「越多越好」 |
| 配对二分比较 | McNemar 检验（同一批文档、两臂产出配对） | McNemar 1947, *Psychometrika* 12:153–157 | B/C 共用同一 doc→package 映射 → 配对差分可用 |
| claim 为分析单元 | 聚类设计效应 deff = 1+(m−1)ρ，有效 n 折算 | Kish 1965 *Survey Sampling*；Donner & Klar 2000 | 把「540 条 claim」折算成有效 n，避免虚假功效 |
| 大批量组织的工程谱系 | 划分 → 独立工作者 → 确定性归并 | Dean & Ghemawat 2004, MapReduce, OSDI | B/C 的 20×3 分包与 A 的单包，本质是 map 粒度差异 |

**标准算例的自校验**（没有外部数据集可用，所以用不依赖外部数据的强不变量 + 独立复算）：

- 恒等极限：δ→0 且两臂真实率相等 → 把握度 = α（脚本 `test_power_invariants...` 断言 0.025±0.003）。
- 单调性：把握度对 n、对 δ 单调不减。
- 独立复算：解析式 vs 蒙特卡洛（两套代码路径、同一判定定义）。
  实测偏差：n=60 时 模拟 − 解析 = **+0.016…+0.021**（Wald 方差估计在小 n 下使实测把握度更高）；
  n=200 时降到 **+0.0006…+0.0025** → 偏差随 n 收敛，同时说明解析式是**渐近**口径（对 n=60 略保守，不夸大把握度）。
- κ 覆盖率独立复算：Fleiss 近似 CI 的名义 95% 覆盖率在 n=30 实测 **0.888**（覆盖不足）；
  百分位自举在 n=30 为 **0.923**、n=120 为 **0.944** → 选型用自举。

## 3. 调研对设计的直接结论（这些是本轮要写进产物的）

1. **prereg v1 的判定规则不可判定**：p≈0.90、n=60/臂 时 Wilson 95% 半宽 **7.7pp**，
   而判定门是 3pp → 任何 3pp 真实差异都埋在 CI 里；「CI 重叠即未分胜负」几乎恒真。
2. **n=60 能证明的最小非劣效界 ≈ 15.3pp**（真实差 0，80% 把握度）；真实差 2pp 时要 18.0pp。
   也就是说：**这个批次的规模只支持「粗劣效」判断，不支持 3pp 门**。
3. **要撑起 3pp 门**：真实差 0 → n/臂 ≈ **1570**；真实差 −2pp → ≈ **15353**（脚本给出，二分求解）。
4. **κ 抽样**：30 条人工复核的 κ 半宽 **0.258** → 判「κ ≥ 0.6」没有分辨力；
   半宽 ≤0.10 需 **201** 条。prereg v1 的 `human_sample_min=30` 只能做存在性检查，不能做可靠性判定。
5. **claim 级分析不自动提功效**：claims/doc 实测 **6.84**，ρ=0.2 时 deff=2.17、有效 n≈189，
   3pp/差 2pp 的把握度仍只有 **0.050** → 换分析单元救不了 3pp。

## 4. 复现命令

```bash
python scripts/rci_f1_corpus.py verify                      # 60/60 逐字节 sha256
python scripts/rci_f1_verify.py --lane B                    # 独立证据反查 → 回执
python scripts/rci_f1_settle.py                             # 五指标 + 臂身份审计 + 判定
python scripts/rci_f1_power.py                              # 可判定性测算表
python scripts/rci_f1_round2_figures.py                     # 图件
python -m pytest tests/test_rci_f1_abc.py tests/test_rci_f1_round2.py -q   # 23 passed
```