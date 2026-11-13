# RCI 阶段 2b：200 对象试点报告（真实语料 → ko/v1 映射）

> 锚点 **KBM-RCI-S2B-PILOT** | 版本 1.0.0 | 2026-11-13 | 仓 TensorKnowledge
> 上游：`docs/rci/schema-v1.md`（S2a 对象定义）、`docs/rci/interface-spec.md`（三方接口）
> 下游：`docs/rci-s2b-schema-revisions.md`（本轮测出的 v1.1 修订 R1–R6）
> 工件（数字唯一来源）：`docs/rci-s2b-pilot200/metrics.json`、`full_frame_rates.json`、`sample_manifest.json`
> 复现：`python3 scripts/rci_s2b_pilot.py`（约 4 s）+ `--full-frame`（约 44 s）；图 `docs/assets/rci/*.png`

本报告只回答一个问题：**S2a 定的 ko/v1 对象，拿去装仓内已有的真实知识记录，装得进去吗？装不进去的地方卡在哪一条？** 答案用 200 条分层样本 + 10,071 条全样本枚举两套数字给出，不含估计。

---

## ① 案例介绍（被试点的东西是什么）

RCI（Research Claim Infrastructure）阶段 2a 交付了 ko/v1 对象定义与校验器（`scripts/validate_ko_v1.py`）。S2b 的任务是把这个 schema 拖到**已经存在的数据**上试一遍，用失败模式反过来修订 schema —— 而不是先改 schema 再找理由。

试点总体（抽样框）**不是**造的：它是本仓 `knowledge/` 下已有的四份真实语料，去重后 10,071 条 claim、10,238 条 evidence：

| facet | 语料位置 | 去重 claim 数 | 主要 claim_type | 证据形态 |
|---|---|---|---|---|
| `kb10k` | `knowledge/kb10k/claims/part-*.json` | 10,000 | definition / descriptive / methodological | `code-location` + `content_hash` |
| `oss-lbm` | `knowledge/oss-lbm/claims/*.json` | 59 | descriptive | 外部仓 `code-location`（有 quote，无文件哈希） |
| `sediment` | `knowledge/sediment/**/claims/*.json` | 6 | interpretive / mathematical / descriptive | 混合，含无哈希条目 |
| `kbm-demo` | `knowledge/kbm/demo-sample/extract/claims/*.json` | 6 | methodological / definition / predictive / hypothesis | `code-location` + 报告切片 |

关键参数（全部写进 `metrics.json`，可机读）：

| 参数 | 取值 | 说明 |
|---|---|---|
| 试点样本量 n | 200 | 任务规定的规模 |
| 分层键 | `facet × source claim_type`（12 层） | 保底 3 条/层，余量按层规模比例（最大余数法） |
| 层内定序 | `sha256(f"{SEED}:{claim_id}")` | 确定性：同语料重跑得同 200 条 |
| 种子 | 20261113 | 只记录与审计用途（定序不依赖 RNG） |
| 权重 | 层规模 / 层内抽中数 | 小层被过量抽样，故必须加权才谈总体 |
| 校验器 | `scripts/validate_ko_v1.py`（RESOLVER_VERSION 见 metrics） | 权威校验逻辑不复制、按路径装载 |

---

## ② 怎么做的（方法 / 流程 / 关键设置）

流程五步，全部在 `scripts/rci_s2b_pilot.py` 里，无人工环节：

1. **建抽样框** `build_frame()`：四份语料去重（同 id 取首次出现），evidence 按 id 建索引 → `10,071 claim / 10,238 evidence`。
2. **分层确定性抽样** `sample()`：每层保底 3 条（不足则全取），余量按层规模比例分配；层内按 `sha256(seed:claim_id)` 排序取前 n。**同输入必得同样本**（有测试守）。
3. **映射适配器** `map_claim()`：源记录 → ko/v1 文档。映射规则全部显式、可审计，不允许「凑字段」：
   - `knowledge_id`：`tkc:<facet>:<slug>` → `ko:<facet>:<slug>`，slug 只做字符规范化（`[^a-z0-9._-] → -`）。
   - `type`：源 `claim_type` 经**显式词表** `SOURCE_TYPE_MAP` 映射；**无诚实映射者标 `unmapped`，不硬凑**（`interpretive`/`hypothesis` 落此列）。
   - `evidence`：源 `evidence_refs` → v1 EvidenceRef；`artifact_ref` 按「仓内可解析 → `repo_path` / 有 `git:` 钉扎 → `repo_path+repo+commit` / 都没有 → `none`」三分；`content_hash` 只在是 64 位 hex 时填，不伪造哈希。
   - `confidence.level`：由 `epistemic_status` 派生（established→medium、provisional/draft→low）。
   - `confidence.basis`：由证据定位符种类派生；**v1.0 词表里没有 code/dataset 档，派生不出就写 `unassessed`**（本轮最大的一处信息损失，见 R2）。
   - `verification_status`：恒为 `unverified` —— 语料里没有平台验证单，任何自称晋级都是造假。
   - `limitations`：由可观测事实机械生成（`epistemic_status`、未解析引用数、证据 `assessment_status=unassessed`）。
4. **两套口径同时验**：
   - `strict v1`：拿权威校验器直接验映射结果（现状会不会被拒）。
   - `projected v1.1`：把 R1/R2/R4/R5/R6 作为**内存补丁**打到 schema 副本上再验（修订值不值）。**权威文件 `schemas/` 与 `scripts/validate_ko_v1.py` 一个字节都没改**，投影可回滚。
5. **度量与出图**：RQS 五维合成分（权重公开）+ review 字段派生化率 + 证据闸分解；图由 `metrics.json` 程序化生成，同一脚本还能 `--render-tables` 把报告表格渲染回来（**零手抄**，测试逐字符比对）。

失败原因按修订条款归类（`categorize()`）：`R1_evidence_locator` / `R2_basis_vocabulary` / `R3_type_bridge` / `payload_card_body` / `field_contract` / `status_machine` / `other`。

RQS（Record Quality Score，诊断用合成分，不是学术指标）：

```
RQS = 0.30·schema_conformance + 0.25·evidence_traceability + 0.20·field_completeness
    + 0.15·review_derivability + 0.10·id_stability
```

逐维均值一并输出（下表），读结论**不必**依赖这组权重；权重本身是约定，不是测量值。

---

## ③ 计算结果（数字表；由 `metrics.json` 渲染，禁止手抄）

<!-- BEGIN GENERATED: scripts/rci_s2b_pilot.py --render-tables -->
| 指标 | 数值 |
|---|---|
| 抽样框（去重 claim 全集） | 10071 |
| 试点样本量 | 200 |
| 分层方式 | facet × source claim_type（每层保底 3，余量按层规模比例） |
| strict v1 通过 | 0/200 = **0.0%** |
| strict v1 加权估计（总体） | 0.0% |
| projected v1.1 通过 | 194/200 = **97.0%** |
| projected v1.1 加权估计（总体） | 99.9% |
| 证据条数（样本内） | 215 |
| 可追溯证据（内容哈希 ∧ 引文 ∧ 定位可解析[仓内或 git 钉扎]） | 190/215 = 88.4% |
| 未解析 evidence_ref | 0 |
| 类型无诚实映射对象 | 4（2.0%） |
| 卡类 payload 缺失 | 10 |
| R2 影响：v1.0 basis 词表无档、被迫写 unassessed | 166（83.0%） |
| 证据闸（内容哈希 / 引文 / 可解析-仓内 / 可解析-git钉扎 / 可解析-外部@pin） | 215 / 203 / 5 / 174 / 197 条 |
| R5 影响：摄取期引文切片自算哈希（quote_span） | 5 条 |
| RQS 均值 / 中位 / 最小 / 最大 | 0.953 / 1.000 / 0.405 / 1.000 |
| metrics 稳定摘要 sha256 | `25ef5c6ed9645ac2…` |

**失败原因归类（严格 v1，按对象计数，可多因）**

| 归类 | 条款 | 对象数 |
|---|---|---|
| `R1_evidence_locator` | R1 证据定位符（report_id 必填） | 200 |
| `payload_card_body` | 卡类 payload 必填 | 12 |

**分类型质量（v1 type，n = 样本内条数）**

| v1 type | n | strict 通过 | projected 通过 | 平均 RQS | 平均 E-TR |
|---|---|---|---|---|---|
| `benchmark_card` | 1 | 0/1 (0%) | 1/1 (100%) | 1.000 | 1.000 |
| `capability_claim` | 25 | 0/25 (0%) | 25/25 (100%) | 0.895 | 0.680 |
| `definition` | 159 | 0/159 (0%) | 158/159 (99%) | 0.982 | 0.937 |
| `method_card` | 11 | 0/11 (0%) | 10/11 (91%) | 0.762 | 0.273 |
| `unmapped` | 4 | 0/4 (0%) | 0/4 (0%) | 0.685 | 1.000 |

**分语料面质量（facet）**

| facet | n | projected 通过 | 平均 E-TR | 平均 RQS |
|---|---|---|---|---|
| `kb10k` | 184 | 184/184 (100%) | 0.880 | 0.966 |
| `kbm-demo` | 6 | 3/6 (50%) | 0.667 | 0.751 |
| `oss-lbm` | 4 | 4/4 (100%) | 0.500 | 0.875 |
| `sediment` | 6 | 3/6 (50%) | 1.000 | 0.825 |

**review 字段准确率（可派生 ∧ 不变量一致）**

| 字段 | v1.0 可派生 | v1.1 可派生 | 准确（v1.1 ∧ 不变量） | 冲突 |
|---|---|---|---|---|
| `confidence.level` | 200/200 (100%) | 200/200 (100%) | 200/200 (100%) | 0 |
| `confidence.basis` | 0/200 (0%) | 166/200 (83%) | 166/200 (83%) | 0 |
| `verification_status` | 200/200 (100%) | 200/200 (100%) | 200/200 (100%) | 0 |
| `limitations` | 200/200 (100%) | 200/200 (100%) | 200/200 (100%) | 0 |
| `provenance.storage_level` | 200/200 (100%) | 200/200 (100%) | 200/200 (100%) | 0 |

**RQS 逐维均值（权重见上表口径，逐维可直接读）**

| 维度 | 权重 | 均值 |
|---|---|---|
| `schema_conformance` | 0.30 | 0.970 |
| `evidence_traceability` | 0.25 | 0.870 |
| `field_completeness` | 0.20 | 0.999 |
| `review_derivability` | 0.15 | 0.966 |
| `id_stability` | 0.10 | 1.000 |
| **RQS** | 1.00 | **0.953** |

**RQS 直方图（0.1 分箱，count）**

| 区间 | 0.0–0.1 | 0.1–0.2 | 0.2–0.3 | 0.3–0.4 | 0.4–0.5 | 0.5–0.6 | 0.6–0.7 | 0.7–0.8 | 0.8–0.9 | 0.9–1.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| count | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 26 | 0 | 170 |
<!-- END GENERATED -->

---

## ④ 结果图

三张图全部由 `scripts/rci_s2b_pilot.py` 从 `metrics.json` 生成（无手绘、无手填数字）：

| 图 | 文件 | 读法 |
|---|---|---|
| 分类型质量（strict v1 基线 vs projected v1.1） | `docs/assets/rci/ko_quality_by_type.png` | 红条 = 现状 schema 通过率（全 0），蓝条 = 按 R1–R6 修订后通过率；右侧标注该类型平均 RQS 与平均 E-TR。**这是一张基线对照图**：v1.0 是基线，v1.1 是干预。 |
| review 字段准确率（v1.0 → v1.1） | `docs/assets/rci/review_field_accuracy.png` | 每个 review 字段两根条：v1.0 可派生率（红）与 v1.1 准确率（绿），标注 `v1.0→v1.1` 与不变量冲突数。`confidence.basis` 从 0% 跳到 83%，是 R2 的直接作用面。 |
| RQS 分布 + E-TR 分布 + 逐维均值 | `docs/assets/rci/rqs_distribution.png` | 左：RQS 直方图（0.1 分箱，标均值/中位）；中：逐对象证据可追溯率分布（0/1 两峰 + 中间少量）；右：五维均值条形（不受权重影响）。 |

无场量云图（纯文档/管线任务，无物理场）：本轮对象是知识记录而非流场/应力场，替代物是上面三张「分布/对照」图。若强行画云图会是无物理含义的伪图，故不做。

---

## ⑤ 注意点（踩过的坑与适用范围）

1. **仓内语料 0 条证据带 `report_id`。** 10,238 条 evidence 全为 locator 型（`code-location`/报告切片），`persistent_id` 用 `git:<repo>@<commit>` 钉扎。v1.0 的 `EvidenceRef` 把 `report_id` 列为必填 ⇒ **试点总体 10,071 条里 0 条能过 v1.0**。这不是映射实现差，是 schema 与既有语料形态不匹配；修法见 R1。
2. **`confidence.basis` 词表缺 code/dataset 档。** 88.05% 的对象证据是代码位置，v1.0 只能写 `unassessed`，等于把「我核过源码」这条信息丢掉。修法见 R2（加 `code_inspection`/`dataset_locator`）。
3. **`artifact_ref` 的 `ref` 也是必填**，`kind:'none'` 不能省 `ref`。第一版适配器漏填导致 198/200 假失败 —— 这是适配器 bug，已在同轮修掉；记录在此提醒后续摄取管线别重犯。
4. **`section.anchor` 字符集是硬约束**（`^[a-z0-9\u4e00-\u9fff][a-z0-9\u4e00-\u9fff-]*$`）；源定位符里带 `.py-30-31`、下划线会被拒。锚点必须单独规范化，不能复用 slug 规则。
5. **样本份额 ≠ 总体份额。** 小层被保底放大：`unmapped` 在样本里占 2.0%，在总体里只有 4/10,071 = 0.04%。任何「占比」结论必须走权重，或直接看全样本枚举（`full_frame_rates.json`）。
6. **review 字段「冲突 0」不代表数据干净**，只说明本轮的派生规则保守（从不派生 `high`、`basis` 只在有定位符时才给值），不变量从未触发。它是护栏，不是质量证明。
7. **RQS 权重是约定的诊断系数**，不要把 0.95 读成「知识质量 95 分」。逐维均值才是可讨论的量：本轮 E-TR 维度均值 0.83 是真正的短板（缺口来自 12 条证据缺 quote）。
8. **适用范围**：本轮只覆盖「已有语料 → ko/v1」的**摄取侧**。平台验证回流（L3）、报告小节锚的真实解析（需 TP `tensor_reports` 正文导出）、`ko_relation` 关联网络三项未在本轮验证，见 §⑥ 与修订文档的「未测」清单。

---

## ⑥ 误差判定（关键量 vs 基准，逐项回答）

本轮无物理基准量（不涉及阻力/升力/频率等工程量），故不适用「与实验/解析解误差 <3%」这条物理精度线。**替代基准 = 全样本精确枚举**（10,071 条全跑一遍，`full_frame_rates.json`，不是估计量），把「200 条样本能不能代表总体」变成可机裁的误差题：

<!-- BEGIN GENERATED: error table -->
| 关键量 | 样本值（n=200，不加权） | 加权估计 | 全样本真值（n=10071） | 误差（pp，不加权 / 加权） | <3 pp?（不加权 / 加权） |
|---|---|---|---|---|---|
| strict v1 通过率 | 0.00% | 0.00% | 0.00% | 0.00 pp / 0.00 pp | ✅ / ✅ |
| projected v1.1 通过率 | 97.00% | 99.94% | 99.94% | 2.94 pp / 0.00 pp | ✅ / ✅ |
| 证据可追溯率 E-TR | 88.37% | 89.54% | 88.15% | 0.22 pp / 1.39 pp | ✅ / ✅ |
| R2 影响面（basis 被迫 unassessed） | 83.00% | 88.05% | 88.05% | 5.05 pp / 0.00 pp | ❌ / ✅ |
| 类型无映射对象占比 | 2.00% | 0.04% | 0.04% | 1.96 pp / 0.00 pp | ✅ / ✅ |
<!-- END GENERATED -->

结论（逐条回答，不含糊）：

- **物理精度线不适用**，已声明原因（无物理参考量）；替代基准是全样本枚举，可机裁。
- **加权估计量全部 <3 pp**（0.00 / 0.00 / 1.39 / 0.00 pp），最大 1.39 pp。
- **不加权样本值有 1 项超线**（R2 影响面 5.05 pp，因小层过量抽样）⇒ 200 条样本的**原始比率**不能直接当总体结论；要么加权，要么（推荐）直接跑全样本枚举 —— 本轮已跑，成本 44 s，没理由再用估计。
- **本轮所有通过率都是精确计数**（分子分母都在 `metrics.json`），不是模型拟合值，故无统计误差，只有抽样代表性误差（上表已量化）。

**没做到的（honest 未完成项）**：

- `confidence.basis` 有 12 条证据缺 quote、5 条靠 R5 引文哈希兜底 —— 这些对象的 `unassessed` 是真实信息缺失，不是 bug，未强行填值。
- 平台验证回流 / L3 通道、`tensor_reports` 正文小节锚的真实解析、`ko_relation` 网络构建：**未测**（需 TP 侧导出与 KE 服务常驻，接口就绪但本轮不跑）。
- 修订 R1–R6 目前只是**内存投影 + 数字**，`schemas/` 落地与校验器改造留待评审后单独 PR（避免与在飞 schema 改动互相踩）。