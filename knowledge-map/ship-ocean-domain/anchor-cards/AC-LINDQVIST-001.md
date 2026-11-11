# AnchorCard: AC-LINDQVIST-001 — Lindqvist冰阻力验证锚卡

## 元数据
- **Card ID**: AC-LINDQVIST-001
- **Domain**: 冰区航行 × 冰阻力 (ice-resistance-lindqvist)
- **Type**: Method Validation Anchor
- **Created**: 2026-11-10
- **Mission**: m8817

## 公式 (Lindqvist)
```
R_ice = R_c + R_s + R_m
```
其中:
- R_c: 船首破碎阻力 (crushing)
- R_s: 次破碎阻力 (submersion)
- R_m: 弯矩阻力 (bending moment)

## 适用范围
| 参数 | 范围 | 单位 |
|------|------|------|
| 冰厚 h | 0.3 - 2.0 | m |
| 船速 V | 0 - 10 | kn |
| 船宽 B | 10 - 40 | m |
| 冰弯曲强度 σ_f | 300 - 800 | kPa |

## 参考值
| 工况 | 冰阻力 | 来源 |
|------|--------|------|
| h=1.0m, V=5kn | ~500-800 kN | Lindqvist 1989 |
| h=0.5m, V=3kn | ~100-200 kN | Lindqvist 1989 |
| h=1.5m, V=8kn | ~1500-2500 kN | Lindqvist 1989 |

## 验证判据
- 与模型试验误差 < 15%
- 与Riska方法对比一致性 < 20%
- IACS冰级参数匹配

## KPI对齐
- 对齐 KPI-KB-10K: 冰区航行 KPI-ICE-001

## 证据溯源
- Lindqvist, G. (1989) "A Simplified Method for Calculation of Ice Resistance"
- ship-performance-platform-incoming ch08_polar/ice_resistance.py
- IACS Unified Requirements for Polar Ships
