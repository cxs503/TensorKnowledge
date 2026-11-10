# AnchorCard: AC-FREDERKING-001 — Frederking冻结强度验证锚卡

## 元数据
- **Card ID**: AC-FREDERKING-001
- **Domain**: 冰区航行 × 冰力学 (ice-mechanics-frederking)
- **Type**: Experimental Anchor
- **Created**: 2026-11-10
- **Mission**: m8817

## 公式 (Frederking 1984)
```
τ_adfreeze = τ₀ · f(T) · f(t) · f(S)
```
其中:
- τ₀: 参考冻结强度 (MPa)
- f(T): 温度修正因子
- f(t): 时间渐近因子
- f(S): 盐度修正因子

## 校准结果
| 参数 | 值 | 单位 |
|------|-----|------|
| 参考强度 τ₀ | 0.5 - 1.5 | MPa |
| 校准误差 | 3.3% | % |
| 适用温度 | -20°C - 0°C | °C |
| 饱和时间 | 24 - 72 | h |

## 验证判据
- Frederking 1984原始数据拟合误差 < 5%
- TensorPhysics校准误差 3.3%
- 盐水冰强度衰减因子与试验一致

## KPI对齐
- 对齐 KPI-KB-10K: 冰区航行 KPI-ICE-001

## 证据溯源
- Frederking, R. (1984) "Adfreeze bond strength of saline ice"
- TensorPhysics benchmarks/icebreaking/adfreeze_breakout.py
- TensorPhysics artifacts/ice_anchor/validation_report.json
