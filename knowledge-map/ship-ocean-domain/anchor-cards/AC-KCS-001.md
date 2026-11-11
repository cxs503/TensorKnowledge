# AnchorCard: AC-KCS-001 — KCS集装箱船验证锚卡

## 元数据
- **Card ID**: AC-KCS-001
- **Domain**: 实船与实验锚 × 标准算例 (seatrial-experiment-benchmark-kcs)
- **Type**: Experimental Anchor
- **Created**: 2026-11-10
- **Mission**: m8817

## 几何参数
| 参数 | 值 | 单位 |
|------|-----|------|
| 总长 L | 230.0 | m (实船) |
| 水线长 Lwl | 220.0 | m |
| 型宽 B | 32.2 | m |
| 型深 D | 19.0 | m |
| 吃水 T | 10.8 | m |
| 方形系数 Cb | 0.6505 | - |
| 缩尺比 | 1:52.5 | - |

## 试验条件
| 参数 | 范围 | 单位 |
|------|------|------|
| 傅汝德数 Fn | 0.10 - 0.30 | - |
| 雷诺数 Re | 2.0×10^6 - 8.0×10^6 | (模型) |
| 航速 V | 12 - 24 | kn (实船) |

## 参考值
| 量 | 参考值 | 来源 |
|----|--------|------|
| 模型阻力系数 Ct | 0.0038 - 0.0045 | SIMMAN 2008 |
| 自航点 | J ≈ 0.6 | 试验测量 |
| 伴流分数 w | 0.25 - 0.35 | 试验测量 |

## 验证判据
- 模型阻力误差 < 3%
- 推力减额误差 < 5%
- 伴流分数误差 < 5%
- 实船外推误差 < 5%

## KPI对齐
- 对齐 KPI-KB-10K: 阻力预报 KPI-RES-001, 推进 KPI-PRO-001

## 证据溯源
- SIMMAN 2008 Workshop on Verification and Validation
- Tokyo 2015 Workshop data
- ship-performance-platform-incoming docs/prereg/ex1_kcs/
