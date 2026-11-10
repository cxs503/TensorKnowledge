# TensorKnowledge

**AI 时代的知识治理基础设施** — 把信息和经验转化为可追溯、可评估、可复用、可演进的知识资产。

TensorKnowledge 不是文档库、不是向量仓、不是 Agent 私有记忆。它提供**四契约**（claim / evidence / provenance / review-event）治理框架、知识引擎投影与检索服务、以及面向 Agent 应用和物理 AI 训练的双出水口。完整愿景见 [VISION.md](VISION.md)，路线图见 [ROADMAP.md](ROADMAP.md)。

---

## 核心能力

| 层 | 能力 | 状态 |
|---|---|---|
| **L1 · 生产沉淀** | 被动沉淀（Agent 任务完成→四契约）+ 主动收集（OSS/文献扫描） | in-progress |
| **L2 · 治理契约** | 四契约 schema + 知识对象聚合 + 评审状态机（禁止自批） | done |
| **L3 · 知识引擎** | 实体/边/facet 投影 + 六类查询 + 一致性校验 | in-progress |
| **L4 · 应用出口** | KE API 检索/上下文组装 + 训练语料分层导出 | planned |

## 快速开始

```bash
# 验证知识资产完整性
python scripts/validate_knowledge_assets.py

# KE 映射验证
python scripts/validate_ke_mapping.py

# KE 原型 demo（ingest → 查询 → 校验）
python -m ke.cli demo platform-test/epistemic-benchmark/pilots/m8554
```

## 项目结构

| 路径 | 内容 |
|---|---|
| `schemas/` | 四契约 schema + KE 查询/映射 schema |
| `docs/ke/` | 知识引擎规格（mapping-spec / 选型评估 / 原型文档） |
| `scripts/` | 验证器、映射构建器、状态机可执行形式 |
| `mappings/` | 试点包映射结果（含损耗登记） |
| `knowledge/` | 知识包（如 oss-lbm 试点） |
| `platform-test/` | 认知基准测试与试点包 |
| `architecture/` | 系统架构与集成契约 |
| `curriculum/` | 人类能力框架与学习路径 |

## 与 Tensor 生态的关系

- **TensorPlatform**：Agent 运行共性平台 → TensorKnowledge 委托执行，不重复构建运行时
- **TensorData**：规范数据资产 → TensorKnowledge 引用数据集，不吸收原始数据
- **TensorPhysics**：科学计算流程 → 评审后的发现可成为知识对象，原始代码留在领域仓
- **领域仓**（TensorLBM/FEM/BEM/…）：领域求解器 → 领域知识经四契约沉淀后进入 TensorKnowledge

详见 [VISION.md §5](VISION.md#5-与-tensor-生态的边界)。

## 知识引擎

四契约到知识引擎的存储/检索映射规格 v0.1 在 [docs/ke/mapping-spec.md](docs/ke/mapping-spec.md)。
原型实现（SQLite + 六类查询 + 一致性校验）在 `ke/` 目录，详见 [docs/ke/proto.md](docs/ke/proto.md)。
选型评估（Cognee vs Graphiti vs 自研薄层）在 [docs/ke/evaluation.md](docs/ke/evaluation.md)。

## 治理原则

1. 出处必引 · 2. 零手抄 · 3. 禁止自批 · 4. 损耗显式 · 5. 诚实申报 · 6. 可回滚

完整原则与长期愿景见 [VISION.md](VISION.md)。

## License

See [LICENSE](LICENSE) for the software license and [LICENSE_SCOPE.md](LICENSE_SCOPE.md) for the boundary between project software and third-party or content assets. Dataset, paper, model, customer, and other non-software assets retain their own rights and restrictions.
