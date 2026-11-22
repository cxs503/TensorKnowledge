# PR: TensorData 架构与资产模型知识卡（m27036 · W3 GLM 扩编道）

## 概要
从 TensorData 3 份架构/API 文档挖掘 4 张 code-pointer-card（schema: code-pointer-card.schema.json，全部通过 jsonschema 机器校验），落盘 `cards/TensorData/`。

## 卡片清单（同批 name 唯一）
1. `tkc:tensordata:arch-overview` — TensorData 架构总览（有界上下文/7 层逻辑架构/生命周期状态机/5 类资产）← docs/architecture/overview.md L1-51
2. `tkc:tensordata:data-asset-model` — 规范数据资产模型（11 核心实体/15 类资产分类/标识版本规则/互操作标准）← docs/architecture/data-asset-model.md L1-53
3. `tkc:tensordata:api-quickstart` — 本地 Quickstart 与 API 契约（MVP 状态/X-API-Key 认证/14 端点/内容寻址存储/Python 客户端）← docs/api/quickstart.md L1-209
4. `tkc:tensordata:quality-gate-lineage` — 质量门与血缘强制语义边界（强制 vs 未实现能力清单）← docs/api/quickstart.md L139-182

## 纪律遵守
- 每卡 source 均为具体文件路径+小节标题+行号（evidence_refs），关键句原文入 verification.source_quote；无出处推断为零
- 不确定内容：无（全部直接引文，confidence: high 已在每卡 notes 注明）
- 逐卡独立作业：读一个文件→当场产卡→落盘 commit（4 个独立 commit）
