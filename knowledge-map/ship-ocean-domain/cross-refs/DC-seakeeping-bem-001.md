# DecisionCard: DC-seakeeping-bem-001 — 耐波性势流BEM选型决策

## 元数据
- **Card ID**: DC-seakeeping-bem-001
- **Cross-ref**: xref-03
- **Domain**: 耐波 × 波浪载荷 (seakeeping-wave-3d)
- **Method**: BEM (边界元/势流方法)
- **Method Repo**: TensorBEM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
何时选用势流BEM而非CFD进行耐波性计算？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| Fn < 0.3 且无显著非线性 | 势流BEM优先 | 比CFD快10-100×，线性假设成立 |
| 需RAO全频响 | 势流BEM优先 | 频域求解天然适合频率扫描 |
| 砰击/甲板上浪显著 | CFD优先 | 势流无法捕捉自由面破碎 |
| 浅水效应显著 | CFD或修正势流 | 标准势流浅水修正有限 |

## 验证锚点
- **来源**: ITTC-1978耐波性预报规程
- **内容**: 标准耐波性预报流程与不确定度分析
- **证据路径**: ITTC Recommended Procedures 7.5-02-07-04.2

## 参数范围
- 傅汝德数 Fn: 0 - 0.3
- 遭遇频率: 0.2 - 2.0 rad/s
- 浪向: 0° - 180°
- 波陡: H/λ < 1/30 (线性范围)

## 注意事项
- 不规则频率需消除(高阶面板法或Irregular Frequency Removal)
- 横摇阻尼需粘性修正(经验公式或RANS)
- 前进速度效应需采用Neumann-Kelvin或Rankine源
