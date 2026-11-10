# DecisionCard: DC-maneuvering-mmg-001 — MMG操纵模型参数获取决策

## 元数据
- **Card ID**: DC-maneuvering-mmg-001
- **Cross-ref**: xref-08
- **Domain**: 操纵 × MMG模型 (maneuvering-model-mmg)
- **Method**: 系统辨识+CFD
- **Method Repo**: TensorFVM + TensorPlatform
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
MMG模型水动力导数如何获取？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| 已有船模试验数据 | 系统辨识优先 | 直接拟合，精度最高 |
| 新船型无试验 | CFD captive model test | 数值试验替代物理试验 |
| 早期设计阶段 | 经验公式估算 | 快速但误差15-25% |

## 验证锚点
- **来源**: IMO Res.757操纵性标准
- **内容**: IMO操纵性标准判据(Z形操舵/回转/停船)
- **证据路径**: IMO Resolution MSC.137(76)

## 参数范围
- 船长 L: 50 - 300 m
- 傅汝德数 Fn: 0.1 - 0.3
- 舵角 δ: ±35°
- 漂角 β: -10° - +10°

## 注意事项
- MMG模型需分离船体/桨/舵水动力
- 浅水效应需额外修正
- 四象限桨/舵特性需完整覆盖
