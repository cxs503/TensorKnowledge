# TensorKnowledge Vision

> **定位**：AI 时代的知识治理基础设施（Knowledge Governance Infrastructure for the AI Era）
> 不是文档库、不是向量仓、不是 Agent 私有记忆。

---

## 1. 为什么需要知识治理

AI Agent 正在大规模执行检索、编码、仿真、协调等任务。瓶颈不再是「获取信息」，而是
**把信息和经验转化为可追溯、可评估、可复用、可演进的知识**。

TensorKnowledge 回答的核心问题：
> 当 Agent 产出海量 claim/evidence/provenance 时，如何保证每一条知识都有出处、有证据、
> 有评审、有版本、可被下游可靠消费？

---

## 2. 四层飞轮（Four-Layer Flywheel）

```
┌─────────────────────────────────────────────────────────────┐
│                    L4 · 应用与训练层                         │
│   ③ Agent 应用（KE API 检索/溯源/上下文组装）                │
│   ④ 物理 AI 训练（训练语料/评测集/结构化监督导出）            │
├─────────────────────────────────────────────────────────────┤
│                    L3 · 知识引擎层                           │
│   实体/边/facet 投影 · 六类查询 · 一致性校验 · 状态机        │
│   （mapping-spec v0.1 · ke-proto 原型 · 选型评估已完成）      │
├─────────────────────────────────────────────────────────────┤
│                    L2 · 治理与契约层                         │
│   四契约（claim / evidence / provenance / review-event）      │
│   知识对象聚合 · 评审状态机（禁止自批）· 双时态 · 损耗登记    │
├─────────────────────────────────────────────────────────────┤
│                    L1 · 生产与沉淀层                         │
│   ① 被动沉淀：Agent 任务完成 → 四契约沉淀（定谳/证伪/基准）   │
│   ② 主动收集：OSS 生态/文献/数据集扫描线（oss-lbm 已试点）    │
└─────────────────────────────────────────────────────────────┘
```

**飞轮运转**：L1 进水 → L2 契约化治理 → L3 引擎投影与检索 → L4 消费反哺 → 新任务触发 L1 再沉淀。
每一轮循环都增加可追溯知识资产，推动 KPI-KB-10K（10,000 条治理知识对象）目标。

---

## 3. 双进水口

### ① 被动沉淀（Passive Precipitation）

每次 Agent 完成任务后，按**四契约**格式沉淀知识：

| 契约 | 内容 | 高价值类型 |
|---|---|---|
| claim-record | 可验证断言（含 epistemic_status） | 定谳（established）、证伪（refuted）、基准（benchmark） |
| evidence-record | 支撑/反驳断言的证据（含 source/locator/quote） | 源码级证据、实验数据、文献锚点 |
| provenance-record | 知识产生的活动/Agent/软件溯源（PROV-O 对齐） | 完整复现链 |
| review-event | 独立评审决策（approve/reject/request-changes） | 跨 Agent 互审记录 |

**负结果也是知识**：honest-FAIL、被否定假设、不可复现记录，全部进入知识对象，
标记相应 epistemic_status，不惩罚诚实。

### ② 主动收集（Active Collection）

常设扫描线主动收集外部知识源：

- **OSS 生态扫描**：已试点 `knowledge/oss-lbm/`（17 条源码级 claim，4 个仓库）；SPH/DG 波在飞
- **文献/数据集**：结构化抽取 claim + evidence + provenance
- **标准/规范**：映射为可查询知识对象

---

## 4. 双出水口

### ③ 面向 Agent 应用（KE API）

知识引擎提供检索/溯源/上下文组装服务：

- **六类查询**：按 claim 状态、证据关系、溯源链、域过滤、claim 证据、统计分布
- **上下文组装**：为 Agent 任务提供带出处的知识片段（非裸文本）
- **旗舰闭环**：m8802 正在验证「任务引用 KE → 产出新 claim → 回流沉淀」闭环

### ④ 面向物理 AI 训练（Training Corpus Export）

epistemic 分层导出：

| 层级 | 准入条件 | 用途 |
|---|---|---|
| published | 通过独立评审（approved） | 训练语料、评测集 |
| reviewed | 至少一轮评审（含 request-changes） | 结构化监督信号 |
| draft | 未经评审 | 不进入训练集 |

**铁律**：只有 published/reviewed 层级的知识对象才进入训练集，draft 层仅用于内部迭代。

---

## 5. 与 Tensor 生态的边界

| 仓 | 职责 | TensorKnowledge 不做什么 |
|---|---|---|
| **TensorPlatform** | Agent 运行共性平台（任务机/战役 DAG/证据/台账/舰队/度量） | 不做 Agent 运行时、不做任务调度、不做执行环境 |
| **TensorKnowledge** | 知识对象治理、四契约、知识引擎、人类学习应用 | 不硬编码领域语义（域数据经 API/配置/工件注入） |
| **TensorData** | 规范数据资产与数据生命周期 | 不吸收原始数据，只引用数据集和计算产出 |
| **TensorPhysics** | 科学计算流程组织（科研循环状态机/验收判据/求解器调度） | 不做求解器调度、不做数值方法实现 |
| **领域仓**（TensorLBM/FEM/BEM/…） | 领域求解器库（数值方法/内核/解析解/战役节点） | 领域知识经四契约沉淀后进入 TensorKnowledge，原始代码留在领域仓 |

**铁律**：TensorKnowledge 零领域语义硬编码。领域词条/判据/算例一律通过 API/配置/工件注入，
测试夹具使用合成域名。

**领域边界审计**（m15723 · 2026-11-12）：
- ✅ `knowledge/oss-lbm/`、`knowledge/sediment/`、`knowledge-map/ship-ocean-domain/` 为知识资产，合规
- ✅ `data/eval_benchmarks.json` 为领域数据配置文件，合规
- ✅ `ke/export.py` 已修复：硬编码 LBM 基准 → 运行时从数据文件加载
- 详见 [`docs/domain-boundary-audit-m15723.md`](docs/domain-boundary-audit-m15723.md)

---

## 6. 统计口径三分离（全文档统一）

知识治理的三个层次，不可混淆：

| 层次 | 定义 | 准入条件 | 用途 |
|---|---|---|---|
| **原始记录**（Raw Records） | Agent 任务产出的原始 claim/evidence/provenance | 任务完成即入库 | 审计溯源、编译输入 |
| **待评审知识对象**（Pending Review KO） | 已聚合但未经独立评审的知识对象 | 通过知识编译器聚合 | 评审输入、内部迭代 |
| **经治理知识对象**（Governed KO） | 通过独立评审（approved）的知识对象 | 通过独立评审（禁止自批） | 训练语料、评测集、对外服务 |

**KPI 对齐**：
- 原始记录目标：100,000 条
- 待评审 KO 目标：10,000 条
- 经治理 KO 目标：8,000 条（published 层）

---

## 7. KPI-KB-10K 对齐

| 指标 | 目标 | 当前状态 |
|---|---|---|
| 治理知识对象（Knowledge Objects） | 10,000 条 | 建设中（见 ROADMAP P0） |
| 四契约记录覆盖率 | 每条 KO 关联 ≥1 claim + ≥1 evidence + ≥1 provenance | mapping-spec v0.1 已定义 |
| 独立评审率 | ≥80% published 层 KO 有独立 review-event | 状态机已实现，规模化待 P0 完成 |
| 溯源链完整度 | ≥90% KO 可回溯到原始 source（URL/commit/citation） | ke-proto 原型已验证 |
| KE API 查询延迟 | P95 < 50ms（单包规模） | ke-proto 实测 < 1ms（15 条记录规模） |

---

## 8. 核心原则

1. **出处必引**：每条 claim 必须有 evidence 支撑，每条 evidence 必须有 source 锚点
2. **零手抄**：所有数字/结论必须可溯源到原始记录（raw_sha256 钉死）
3. **禁止自批**：评审者不得评审自己生产的知识对象（状态机强制）
4. **损耗显式**：引擎模型表达不了的信息必须进损耗登记，不偷偷扩契约
5. **诚实申报**：honest-FAIL 不可覆盖，负面结果与正面结果同等入账
6. **可回滚**：所有知识对象版本化，SUPERSEDES 追加式（不修改被取代行）

---

## 9. 长期愿景

一个人（或 Agent）应该能够：
从一个有意义的问题出发 → 识别所需知识 → 与合适的 Agent 和人协作 →
开展可信的调查 → 将结果转化为有用的、可解释的、可复现的知识资产。

TensorKnowledge 的目标不是让每个人成为每个领域的专家，
而是扩展每个人（和每个 Agent）进入陌生领域、负责任地学习、参与创造的能力。
