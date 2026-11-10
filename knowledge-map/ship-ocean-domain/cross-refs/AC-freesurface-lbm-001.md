# AnchorCard: AC-freesurface-lbm-001 — LBM自由面方法验证锚卡

## 元数据
- **Card ID**: AC-freesurface-lbm-001
- **Cross-ref**: xref-06
- **Domain**: 多相流 × 自由面 (multiphase-freesurface-lbm)
- **Method**: LBM自由面
- **Method Repo**: TensorLBM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
LBM自由面方法精度与适用范围？

## 验证判据

| 验证项 | 判据 | 目标值 |
|--------|------|--------|
| 静水压力分布 | 误差 | < 2% |
| 波浪传播色散关系 | 相速度误差 | < 5% |
| 质量守恒 | 总质量漂移/1000步 | < 0.1% |
| 表面张力平衡 | Laplace定律偏差 | < 3% |

## 参考基准
- 静水压力: p = ρgh，线性分布
- 线性波色散: ω² = gk·tanh(kh)
- Laplace定律: Δp = σ/R

## 适用范围
- 密度比: < 10 (标准自由面LBM)
- 表面张力: 小到中等
- 波浪陡度: H/λ < 1/20

## 注意事项
- 自由面LBM需处理空网格填充
- 大密度比需使用多相LBM(MCMP/颜色梯度)
- 表面张力模型需校准
