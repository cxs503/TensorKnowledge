# TensorKnowledge Roadmap

本路线图按 owner 2026-11 优先级表重排。
状态标注纪律：**done** = 已完成可验证、**in-progress** = 在建有可追踪工件、**planned** = 未建。
禁止把 planned 写成已有。

**统计口径三分离**（全文档统一）：
- **原始记录**（Raw Records）：Agent 任务产出的原始 claim/evidence/provenance，未经评审
- **待评审知识对象**（Pending Review KO）：已聚合但未经独立评审的知识对象
- **经治理知识对象**（Governed KO）：通过独立评审（approved）的知识对象，可进入训练集

---

## P0 · 海量成果接入 / 知识编译器 / 多 Agent 治理 / 知识资产索引

### m8800 · 存储统一（in-progress）

**目标**：统一知识引擎存储层，从 ke-proto（SQLite 原型）演进为生产级存储。

- [x] ke-proto 原型完成（SQLite + 六类查询 + 一致性校验）— [docs/ke/proto.md](docs/ke/proto.md)
- [x] 选型评估完成（Cognee vs Graphiti vs 自研薄层）— [docs/ke/evaluation.md](docs/ke/evaluation.md)
- [x] 决策：自研薄层作为权威存储（canonical store）
- [x] PostgreSQL 生产存储实现（替代 SQLite 原型）— [docs/ke/backends.md](docs/ke/backends.md)
- [x] SQLite→PG 迁移工具 + 双后端对拍测试
- [ ] 多包 ingest 与包间 xref
- [ ] review-event 接入存储层
- [ ] 与 production-result 信封的联动校验

**验收**：PostgreSQL 存储通过 ke-proto 全部 15 个测试 + 新增多包/增量测试。

### m8801 · KE API（in-progress）

**目标**：知识引擎对外提供可检索 API，支持 Agent 任务引用。

- [x] 映射规格 v0.1 完成 — [docs/ke/mapping-spec.md](docs/ke/mapping-spec.md)
- [x] 六类查询原语定义（Q1–Q6）
- [x] KE 查询接口草案 schema（`schemas/ke-query.schema.json`）
- [ ] REST API 实现（/ke/query, /ke/claim/{id}, /ke/evidence/{id}, /ke/chain/{id}）
- [ ] 上下文组装端点（为 Agent 任务返回带出处的知识片段）
- [ ] API 鉴权与速率限制
- [ ] 查询性能基准（P95 < 50ms）

**验收**：API 通过集成测试，m8802 旗舰闭环可成功调用。

### m8802 · 旗舰闭环（in-progress）

**目标**：验证「任务引用 KE → 产出新 claim → 回流沉淀」完整闭环。

- [ ] 任务侧 KE 引用机制（Agent 在任务中检索知识引擎）
- [ ] 产出 claim 自动封装为四契约格式
- [ ] 回流沉淀管线（新 claim → 知识对象 → 评审状态机）
- [ ] 端到端测试（至少一个完整任务闭环）
- [ ] 闭环延迟与可靠性度量

**验收路径**（m15723 补充）：
1. **锚点**：m8802 旗舰闭环验收
2. **判据**：
   - 端到端测试通过：Agent 任务 → KE 检索 → 产出新 claim → 四契约封装 → 回流沉淀 → 评审状态机流转
   - 闭环延迟可度量：从任务完成到新 claim 入库 < 5s（P95）
   - 可靠性度量：10 次连续闭环成功率 ≥ 90%
   - 负结果如实入账：honest-FAIL 进入知识对象，标记 `epistemic_status: refuted` 或 `failed`
3. **验收方法**：
   - 运行 `tests/test_m8802_e2e.py`（待实现）
   - 检查 `runs/m8802/closure-report.json` 中的延迟与成功率指标
   - 确认至少 1 条新 claim 完成全流程（claim → evidence → provenance → review-event）

### 知识编译器（planned）

**目标**：将原始记录自动编译为待评审知识对象。

- [ ] 原始记录 → 知识对象聚合规则
- [ ] 自动提取 claim-evidence 关系
- [ ] 生成待评审 KO 清单
- [ ] 编译损耗登记（无法聚合的信息显式记录）

**验收**：100 条原始记录编译为 ≥ 80 条 KO，损耗率 < 20%。

### 多 Agent 治理（planned）

**目标**：支持多 Agent 协同评审知识对象。

- [ ] 评审任务分发机制
- [ ] 禁止自批强制（状态机）
- [ ] 跨 Agent 评审记录（review-event）
- [ ] 评审冲突解决策略

**验收**：3 个 Agent 对同一 KO 独立评审，状态机正确流转。

### 知识资产索引（planned）

**目标**：建立知识资产的全局索引与检索服务。

- [ ] 知识对象全文索引
- [ ] 多维度检索（domain / status / relation / provenance chain）
- [ ] 检索质量度量（recall@k / precision）
- [ ] 索引增量更新

**验收**：1000 条 KO 检索 P95 < 50ms，recall@10 ≥ 90%。

---

## P1 · TP 集成 / 缺口发现 / 知识演进

### TensorPlatform 集成（planned）

**目标**：与 TensorPlatform 任务机/战役 DAG 集成。

- [ ] 任务完成自动触发四契约生成
- [ ] 战役 DAG 节点与知识对象关联
- [ ] 任务侧 KE 引用 SDK
- [ ] 负结果（honest-FAIL）自动入账

**验收**：TensorPlatform 任务完成后，KE 自动收到四契约记录。

### 缺口发现（planned）

**目标**：从知识对象中自动发现研究缺口。

- [ ] gap-anchor 自动提取
- [ ] 缺口优先级排序
- [ ] 缺口与战役节点关联
- [ ] 缺口闭合追踪

**验收**：从 100 条 KO 中自动提取 ≥ 10 条 gap-anchor。

### 知识演进（planned）

**目标**：支持知识对象的版本演进与冲突检测。

- [ ] KO 版本追踪
- [ ] SUPERSEDES 追加式更新
- [ ] 冲突检测与合并策略
- [ ] 知识衰减与过期策略

**验收**：KO 版本演进历史可追溯，冲突检测准确率 ≥ 95%。

---

## P2 · 物理 AI 出口 / 跨领域发现

### 物理 AI 训练出口（planned）

**目标**：epistemic 分层导出，支持物理 AI 训练。

- [ ] published / reviewed / draft 三层导出
- [ ] 训练语料格式转换（JSON → 训练框架输入）
- [ ] 评测集构建（从 published KO 生成问答/判断题）
- [ ] 结构化监督信号导出（claim-evidence 对作为训练标签）

**验收**：1000 条 published KO 导出为训练语料，格式兼容主流训练框架。

### 跨领域发现（planned）

**目标**：支持跨领域知识发现与迁移。

- [ ] 跨域知识对象关联
- [ ] 领域迁移学习信号提取
- [ ] 跨域类比发现
- [ ] 跨域知识图谱可视化

**验收**：从 LBM 域 KO 中发现 ≥ 5 条可迁移到 FEM 域的知识。

---

## 历史里程碑（被动沉淀）

### 进水口

#### 被动沉淀管线（planned）

- [ ] 任务完成自动触发四契约生成（claim + evidence + provenance）
- [ ] 负结果（honest-FAIL / falsified_hypothesis）自动入账
- [ ] 定谳/证伪/基准类知识优先沉淀
- [ ] 四契约 schema 校验自动化（CI 门禁）

#### 主动收集扫描线

- [x] OSS 生态扫描试点（`knowledge/oss-lbm/`，17 条 claim，4 仓库）— done
- [ ] SPH/DG 生态扫描（在飞）
- [ ] 文献结构化抽取管线
- [ ] 数据集元数据注册
- [ ] 标准/规范映射为知识对象

#### 知识包规范

- [x] 知识包目录结构约定（claims/ evidence/ provenance/）— done
- [x] 自验证脚本约定（`validate_*.py`）— done
- [ ] 知识包发布与版本管理
- [ ] 跨包 xref 解析

### 出水口

#### Agent 应用出口（KE API 消费侧）

- [ ] KE API 文档与 SDK
- [ ] 上下文组装模板（不同任务类型的知识片段格式）
- [ ] Agent 任务引用 KE 的最佳实践
- [ ] 检索质量度量（recall@k / precision）

#### 人类学习应用

- [x] 人类能力框架（`curriculum/human-capabilities-ai-era.md`）— done
- [x] 机器可读能力摘要（`curriculum/human-capabilities-framework.json`）— done
- [ ] 学习路径与知识对象关联
- [ ] 教程与知识对象双向链接

### 多模态（planned）

#### 多模态知识对象

- [ ] 图像/图表作为 evidence 载体（含 sha256 钉死）
- [ ] 代码片段作为 evidence 载体（repo@commit:line 定位）
- [ ] 仿真结果作为 evidence 载体（含复现参数）
- [ ] 多模态 facet 投影（向量 + 结构化元数据）

#### 规模与性能

- [ ] 10K 知识对象规模基准
- [ ] 分布式存储与查询
- [ ] 全文检索集成
- [ ] 缓存与 CDN 策略

---

## KPI 追踪

| 指标 | 目标 | 当前 | 状态 |
|---|---|---|---|
| 原始记录 | 100,000 条 | ~257 条（试点） | in-progress |
| 待评审 KO | 10,000 条 | ~20 条（试点） | planned |
| 经治理 KO（published） | 8,000 条 | 0 条 | planned |
| 独立评审率 | ≥80% | 0%（规模化待 P0） | planned |
| KE API P95 延迟 | < 50ms | < 1ms（15 条规模） | in-progress |
| 溯源链完整度 | ≥90% | 100%（试点规模） | done（试点） |
| OSS 扫描覆盖 | ≥10 生态 | 1（LBM） | in-progress |

---

## 历史里程碑

| 日期 | 事件 | 状态 |
|---|---|---|
| 2026-11-09 | ke-proto 原型完成（15 测试全绿） | done |
| 2026-11-09 | KE 选型评估完成（自研薄层胜出） | done |
| 2026-11-09 | mapping-spec v0.1 完成 | done |
| 2026-11-09 | oss-lbm 知识包试点完成（17 claim） | done |
| 2026-11-10 | VISION/README/ROADMAP 重写（本任务 m8808） | done |
| 2026-11-10 | PostgreSQL 权威存储实现 + 双后端对拍 | done |
| 2026-11-12 | 文档-实现一致性修 + 领域边界审计（m15723） | in-progress |
