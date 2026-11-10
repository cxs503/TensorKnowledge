# AnchorCard: AC-slamming-wagner-001 — Wagner砰击理论验证锚卡

## 元数据
- **Card ID**: AC-slamming-wagner-001
- **Cross-ref**: xref-11
- **Domain**: 结构水动力 × 砰击 (structural-hydro-slamming-wagner)
- **Method**: 解析解+Wagner理论
- **Method Repo**: TensorPhysics
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
Wagner理论对二维楔形体入水的精度？

## 验证判据

| 验证项 | 判据 | 目标值 |
|--------|------|--------|
| 入水初期压力峰值 | 误差(t<0.01s) | < 10% |
| 附加质量系数 | 误差 | < 5% |
| 适用范围 | 楔角 | < 10° |

## 参考基准
- Wagner (1932) 原始理论解
- Zhao & Faltinsen (1993) 修正解
- 二维楔形体入水试验数据

## 适用范围
- 楔角 β: 2° - 10°
- 入水速度 V: 1 - 20 m/s
- 时间: 入水初期(t < 0.1s)

## 注意事项
- Wagner理论假设小楔角、不可压、无重力
- 大楔角需修正(Zhao-Faltinsen)
- 三维效应需单独考虑
