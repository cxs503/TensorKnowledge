# DecisionCard: DC-bubble-lbm-001 — 气泡动力学LBM-MCMP选型决策

## 元数据
- **Card ID**: DC-bubble-lbm-001
- **Cross-ref**: xref-02
- **Domain**: 多相流 × 气泡动力学 (multiphase-bubble-lbm)
- **Method**: LBM-MCMP (多组分多相格子Boltzmann)
- **Method Repo**: TensorLBM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
LBM-MCMP模拟气泡聚并/破裂的适用条件？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| Re_bubble < 500 且关注界面拓扑 | LBM-MCMP优先 | 界面自动捕捉，无需追踪 |
| 多气泡相互作用 (>10个) | LBM-MCMP可扩展 | 天然并行，适合GPU加速 |
| 高Re湍流气泡 | VOF/LevelSet优先 | LBM-MCMP在高Re下数值耗散大 |
| 密度比 > 100 | 改进MCMP或VOF | 标准MCMP密度比受限 |

## 验证锚点
- **来源**: TensorLBM `docs/SUBOFF_VALIDATION.md`
- **内容**: SUBOFF潜艇标准体验证
- **证据路径**: `TensorLBM/docs/SUBOFF_VALIDATION.md`

## 参数范围
- 气泡直径: 0.1 - 10 mm
- 密度比: 1 - 100 (标准MCMP)
- 表面张力系数: 可调节
- Re_bubble: 1 - 500

## 注意事项
- MCMP模型需校准伪势函数参数
- 网格分辨率需满足界面厚度 > 4Δx
- 大密度比需使用改进的MCMP或颜色梯度模型
