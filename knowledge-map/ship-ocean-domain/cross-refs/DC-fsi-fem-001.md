# DecisionCard: DC-fsi-fem-001 — 双向流固耦合FEM选型决策

## 元数据
- **Card ID**: DC-fsi-fem-001
- **Cross-ref**: xref-04
- **Domain**: 结构水动力 × 流固耦合 (structural-hydro-fsi-two)
- **Method**: FEM (有限元方法)
- **Method Repo**: TensorFEM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
双向FSI中结构侧FEM离散策略？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| 薄板/壳结构 | Mindlin/Kirchhoff板单元 | 厚度/跨度比 < 1/10适用 |
| 大变形几何非线性 | 非线性FEM+更新Lagrange | 需考虑几何刚度矩阵 |
| 湿模态分析 | 附加质量矩阵耦合 | 流体附加质量显著改变固有频率 |

## 验证锚点
- **来源**: TensorFEM plate_mindlin曲率收敛校验
- **内容**: Mindlin板单元收敛性验证
- **证据路径**: TensorFEM tests/plate_mindlin/

## 参数范围
- 板厚/跨度比: 1/50 - 1/5
- 材料: 钢/铝/复合材料
- 边界条件: 简支/固支/自由

## 注意事项
- Mindlin板需剪切锁定修正(减缩积分)
- 湿模态需附加质量矩阵(势流或CFD提取)
- 时间积分: Newmark-β或HHT-α
