# DecisionCard: DC-beset-dem-001 — 被困船脱困DEM决策

## 元数据
- **Card ID**: DC-beset-dem-001
- **Cross-ref**: xref-13
- **Domain**: 冰区航行 × 被困船脱困 (ice-operation-beset)
- **Method**: DEM+热力学耦合
- **Method Repo**: TensorDEM + TensorPhysics
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
脱困力计算中冻结强度与机械阻力的耦合？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| 冻结时间 > 24h | adfreeze强度主导 | Frederking 1984冻结强度公式适用 |
| 船体运动 | DEM冰-船接触力+冻结面剪切 | 需同时考虑机械与冻结阻力 |
| 脱困判据 | 主机推力 > 总阻力(冰+冻结) | 力平衡判据 |

## 验证锚点
- **来源**: TensorPhysics adfreeze_breakout.py
- **内容**: W3-N02冻结强度与被困船脱困基准
- **Frederking 1984校准误差**: 3.3%
- **证据路径**: TensorPhysics/benchmarks/icebreaking/adfreeze_breakout.py

## 参数范围
- 冻结时间: 1 - 168 h
- 冰温: -20°C - 0°C
- 船体接触面积: 10 - 500 m²
- 主机推力: 0.5 - 20 MN

## 注意事项
- 冻结强度随时间渐近饱和
- 盐度影响冻结强度(盐水冰<淡水冰)
- 脱困策略: 前后交替运动可减小冻结面积
