# DecisionCard: DC-resistance-lbm-001 — LBM阻力计算选型决策

## 元数据
- **Card ID**: DC-resistance-lbm-001
- **Cross-ref**: xref-14
- **Domain**: 阻力 × CFD直接计算 (resistance-prediction-cfd)
- **Method**: LBM (格子Boltzmann)
- **Method Repo**: TensorLBM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
LBM用于船体阻力计算的适用性？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| Re < 10^6 且几何简单 | LBM D3Q19可行 | 低Re下LBM精度可接受 |
| 高Re湍流 | LBM需LES亚格子模型 | 标准LBM无法解析高Re湍流 |
| 复杂几何+边界层 | FVM优先 | LBM曲面边界处理复杂 |

## 验证锚点
- **来源**: SUBOFF LBM验证
- **内容**: SUBOFF潜艇标准体LBM阻力计算验证
- **证据路径**: TensorLBM/docs/SUBOFF_VALIDATION.md

## 参数范围
- 雷诺数 Re: 10^4 - 10^6 (标准LBM)
- 马赫数 Ma: < 0.3 (不可压假设)
- 网格: 均匀/自适应

## 注意事项
- LBM边界条件需特殊处理(曲面插值)
- 高Re需LES或混合RANS-LBM
- GPU加速效率高(天然并行)
