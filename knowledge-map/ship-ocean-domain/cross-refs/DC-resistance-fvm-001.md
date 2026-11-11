# DecisionCard: DC-resistance-fvm-001 — 阻力CFD计算FVM选型决策

## 元数据
- **Card ID**: DC-resistance-fvm-001
- **Cross-ref**: xref-05
- **Domain**: 阻力 × 粘压阻力 (resistance-viscous-cfd)
- **Method**: FVM (有限体积CFD)
- **Method Repo**: TensorFVM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
RANS/LES/DES在船体阻力计算中的选择？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| 工程预报(误差<5%) | RANS SST k-ω优先 | 成熟可靠，计算成本可接受 |
| 分离流/涡脱落 | DES/LES优先 | RANS无法准确捕捉非定常分离 |
| 网格独立性: y+<1 | 壁面解析 | 边界层全解析，精度高 |
| 网格独立性: 30<y+<300 | 壁面函数 | 计算成本低，工程可接受 |

## 验证锚点
- **来源**: SUBOFF阻力验证
- **内容**: SUBOFF潜艇标准体阻力计算与实验对比(误差<3%)
- **证据路径**: TensorLBM/docs/SUBOFF_VALIDATION.md, TensorPlatform/docs/SUBOFF_RESISTANCE_VALIDATION.md

## 参数范围
- 雷诺数 Re: 10^6 - 10^9
- 傅汝德数 Fn: 0.1 - 0.4
- 湍流强度: 1% - 5%

## 注意事项
- 自由面需VOF或刚性壁面近似
- 网格量: 2M-10M(工程), 20M+(高精度)
- 收敛判据: 残差<10^-5, 力系数波动<0.5%
