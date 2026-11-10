# DecisionCard: DC-ice-dem-001 — 冰-船相互作用DEM选型决策

## 元数据
- **Card ID**: DC-ice-dem-001
- **Cross-ref**: xref-01
- **Domain**: 冰区航行 × 冰阻力 (ice-resistance-dem)
- **Method**: DEM (离散元方法)
- **Method Repo**: TensorDEM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
何时选用DEM而非连续介质方法模拟冰-船作用？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| 冰厚 > 0.3m 且需捕捉破碎模式 | DEM优先 | 离散元天然捕捉裂纹扩展与碎冰运动 |
| 船速 < 5kn 且关注冰载荷峰值 | DEM优先 | 低速下冰-船接触力主导，DEM可输出接触力时间历程 |
| 实时性要求 > 100×加速 | 降阶模型/经验公式 | DEM计算成本高，Lindqvist/Riska公式快但精度有限 |
| 冰厚 < 0.1m (薄冰) | 连续介质/板壳理论 | 薄冰弯曲破坏为主，连续介质更高效 |

## 验证锚点
- **来源**: TensorPhysics `benchmarks/icebreaking/adfreeze_breakout.py`
- **内容**: W3-N02冻结强度与被困船脱困基准
- **Frederking 1984校准误差**: 3.3%
- **证据路径**: `TensorPhysics/artifacts/ice_anchor/validation_report.json`

## 参数范围
- 冰厚: 0.1 - 2.0 m
- 冰弯曲强度: 300 - 800 kPa
- 船速: 0 - 10 kn
- 冰-船摩擦系数: 0.05 - 0.20

## 注意事项
- DEM时间步需满足CFL条件: Δt < 0.2·√(m/k)
- 接触刚度需标定: 通过单轴压缩试验反演
- 碎冰尺寸分布影响计算规模
