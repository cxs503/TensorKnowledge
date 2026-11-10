# AnchorCard: AC-ITTC57-001 — ITTC-1957摩擦线验证锚卡

## 元数据
- **Card ID**: AC-ITTC57-001
- **Domain**: 实船与实验锚 × ITTC规程 (seatrial-experiment-ittc-78)
- **Type**: Standard/Procedure Anchor
- **Created**: 2026-11-10
- **Mission**: m8817

## 公式
```
Cf = 0.075 / (log10(Re) - 2)²
```

## 适用范围
| 参数 | 范围 | 单位 |
|------|------|------|
| 雷诺数 Re | 10^6 - 10^9 | - |
| 船型 | 常规排水型船 | - |

## 参考值
| Re | Cf(ITTC-1957) | 备注 |
|----|---------------|------|
| 10^6 | 0.00440 | 模型尺度 |
| 10^7 | 0.00303 | 模型尺度 |
| 10^8 | 0.00219 | 实船尺度 |
| 10^9 | 0.00165 | 大型实船 |

## 验证判据
- 与Prandtl-Schlichting公式偏差 < 2%
- 在ITTC-1978外推规程中作为标准摩擦线

## KPI对齐
- 对齐 KPI-KB-10K: 阻力预报 KPI-RES-001, 能效 KPI-ENE-001

## 证据溯源
- ITTC 1957 Conference Proceedings
- ITTC Recommended Procedures 7.5-02-02-01
- ship-performance-platform-incoming frontend-vue/src/views/methods/ITTC57Method.vue
