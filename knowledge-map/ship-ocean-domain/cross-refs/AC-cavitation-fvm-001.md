# AnchorCard: AC-cavitation-fvm-001 — 空化CFD验证锚卡

## 元数据
- **Card ID**: AC-cavitation-fvm-001
- **Cross-ref**: xref-10
- **Domain**: 多相流 × 片状空化 (multiphase-cavitation-sheet)
- **Method**: FVM+空化模型
- **Method Repo**: TensorFVM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
空化模型(Schnerr-Sauer/Zwart)的验证判据？

## 验证判据

| 验证项 | 判据 | 目标值 |
|--------|------|--------|
| 空化区域长度 | 对应空化数σ的长度误差 | < 10% |
| 升力系数 CL | 误差 | < 5% |
| 空化脱落频率 | Strouhal数误差 | < 15% |
| 空化体积 | 时均空化体积误差 | < 15% |

## 参考基准
- NACA0015/66水翼空化试验数据
- Clark-Y水翼空化基准
- 空化数 σ = (p-p_v)/(0.5ρV²)

## 适用范围
- 空化数 σ: 0.5 - 4.0
- 攻角 α: 2° - 12°
- Re: 10^5 - 10^7

## 注意事项
- Schnerr-Sauer模型需校准汽化/凝结系数
- 网格需在空化区加密
- 非定常空化需瞬态模拟
