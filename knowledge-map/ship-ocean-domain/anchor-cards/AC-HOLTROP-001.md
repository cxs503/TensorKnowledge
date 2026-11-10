# AnchorCard: AC-HOLTROP-001 — Holtrop-Mennen阻力预报验证锚卡

## 元数据
- **Card ID**: AC-HOLTROP-001
- **Domain**: 阻力 × 阻力预报方法 (resistance-prediction-holtrop)
- **Type**: Method Validation Anchor
- **Created**: 2026-11-10
- **Mission**: m8817

## 方法概述
Holtrop-Mennen (1982, 1984) 半经验阻力预报方法，适用于常规排水型船。

## 输入参数
| 参数 | 范围 | 单位 |
|------|------|------|
| 船长 L | 20 - 300 | m |
| 型宽 B | 3 - 45 | m |
| 吃水 T | 1.5 - 15 | m |
| 方形系数 Cb | 0.45 - 0.85 | - |
| 傅汝德数 Fn | 0.1 - 0.35 | - |

## 参考值
| 船型 | 误差范围 | 来源 |
|------|---------|------|
| 油船 | ±5% | Holtrop 1984 |
| 散货船 | ±5% | Holtrop 1984 |
| 集装箱船 | ±8% | Holtrop 1984 |
| 客船 | ±10% | Holtrop 1984 |

## 验证判据
- 与试验数据误差 < 8%(常规船型)
- 预注册测试通过: backend/tests/test_holtrop1984_prereg.py
- Golden数据匹配: backend/tests/data/holtrop1984_golden.json

## KPI对齐
- 对齐 KPI-KB-10K: 阻力预报 KPI-RES-001

## 证据溯源
- Holtrop, J. & Mennen, G.G.J. (1982) "An Approximate Power Prediction Method"
- Holtrop, J. (1984) "A Statistical Re-analysis of Resistance and Propulsion Data"
- ship-performance-platform-incoming backend/api/holtrop1984.py
