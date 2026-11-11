# AnchorCard: AC-SUBOFF-001 — SUBOFF潜艇标准体验证锚卡

## 元数据
- **Card ID**: AC-SUBOFF-001
- **Domain**: 实船与实验锚 × 标准算例 (seatrial-experiment-benchmark-suboff)
- **Type**: Experimental Anchor
- **Created**: 2026-11-10
- **Mission**: m8817

## 几何参数
| 参数 | 值 | 单位 |
|------|-----|------|
| 总长 L | 4.356 | m |
| 直径 D | 0.508 | m |
| L/D | 8.57 | - |
| 附体 | 帆翼+尾十字舵 | - |
| 几何验证 | exact match 100%+水密全流形 | - |

## 试验条件
| 参数 | 范围 | 单位 |
|------|------|------|
| 雷诺数 Re | 1.0×10^6 - 1.2×10^7 | - |
| 速度 V | 1.5 - 15 | m/s |
| 湍流强度 | 0.5% - 2% | - |

## 参考值
| 量 | 参考值 | 来源 |
|----|--------|------|
| 阻力系数 Cd | 0.0035 - 0.0045 | Groves et al. (1989) |
| 边界层厚度 δ/L | 0.02 - 0.05 | 试验测量 |

## 验证判据
- 阻力系数误差 < 3%
- 压力分布误差 < 5%
- 边界层速度剖面误差 < 5%

## KPI对齐
- 对齐 KPI-KB-10K: 阻力预报精度 KPI-RES-001

## 证据溯源
- TensorLBM/docs/SUBOFF_VALIDATION.md
- TensorPlatform/docs/SUBOFF_RESISTANCE_VALIDATION.md
- Groves, N.C. et al. (1989) "A Submarine Body with Appendages"
