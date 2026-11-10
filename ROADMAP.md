# TensorKnowledge Roadmap

本路线图按「地基 → 进水口 → 出水口 → 多模态」分层排期。
状态标注纪律：**done** = 已完成可验证、**in-progress** = 在建有可追踪工件、**planned** = 未建。
禁止把 planned 写成已有。

---

## P0 · 地基（in-flight）

三条 P0 单并行推进，构成知识治理基础设施的最小可用闭环。

### m8800 · 存储统一（in-progress）

**目标**：统一知识引擎存储层，从 ke-proto（SQLite 原型）演进为生产级存储。

- [x] ke-proto 原型完成（SQLite + 六类查询 + 一致性校验）— [docs/ke/proto.md](docs/ke/proto.md)
- [x] 选型评估完成（Cognee vs Graphiti vs 自研薄层）— [docs/ke/evaluation.md](docs/ke/evaluation.md)
- [x] 决策：自研薄层作为权威存储（canonical store）
- [ ] PostgreSQL 生产存储实现（替代 SQLite 原型）
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

**验收**：端到端测试通过，闭环延迟可度量，负结果如实入账。

---

## P1 · 进水口（planned）

### 被动沉淀管线

- [ ] 任务完成自动触发四契约生成（claim + evidence + provenance）
- [ ] 负结果（honest-FAIL / falsified_hypothesis）自动入账
- [ ] 定谳/证伪/基准类知识优先沉淀
- [ ] 四契约 schema 校验自动化（CI 门禁）

### 主动收集扫描线

- [x] OSS 生态扫描试点（`knowledge/oss-lbm/`，17 条 claim，4 仓库）— done
- [ ] SPH/DG 生态扫描（在飞）
- [ ] 文献结构化抽取管线
- [ ] 数据集元数据注册
- [ ] 标准/规范映射为知识对象

### 知识包规范

- [x] 知识包目录结构约定（claims/ evidence/ provenance/）
- [x] 自验证脚本约定（`validate_*.py`）
- [ ] 知识包发布与版本管理
- [ ] 跨包 xref 解析

---

## P2 · 出水口（planned）

### Agent 应用出口（KE API 消费侧）

- [ ] KE API 文档与 SDK
- [ ] 上下文组装模板（不同任务类型的知识片段格式）
- [ ] Agent 任务引用 KE 的最佳实践
- [ ] 检索质量度量（recall@k / precision）

### 物理 AI 训练出口

- [ ] epistemic 分层导出（published / reviewed / draft）
- [ ] 训练语料格式转换（JSON → 训练框架输入）
- [ ] 评测集构建（从 published 知识对象生成问答/判断题）
- [ ] 结构化监督信号导出（claim-evidence 对作为训练标签）

### 人类学习应用

- [x] 人类能力框架（`curriculum/human-capabilities-ai-era.md`）— done
- [x] 机器可读能力摘要（`curriculum/human-capabilities-framework.json`）— done
- [ ] 学习路径与知识对象关联
- [ ] 教程与知识对象双向链接

---

## P3 · 多模态（planned）

### 多模态知识对象

- [ ] 图像/图表作为 evidence 载体（含 sha256 钉死）
- [ ] 代码片段作为 evidence 载体（repo@commit:line 定位）
- [ ] 仿真结果作为 evidence 载体（含复现参数）
- [ ] 多模态 facet 投影（向量 + 结构化元数据）

### 知识演化

- [ ] 知识对象版本演进追踪
- [ ] 冲突检测与合并策略
- [ ] 知识衰减与过期策略
- [ ] 社区贡献与评审流程

### 规模与性能

- [ ] 10K 知识对象规模基准
- [ ] 分布式存储与查询
- [ ] 全文检索集成
- [ ] 缓存与 CDN 策略

---

## KPI 追踪

| 指标 | 目标 | 当前 | 状态 |
|---|---|---|---|
| 治理知识对象 | 10,000 条 | ~20 条（试点） | in-progress |
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
