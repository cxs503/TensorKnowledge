# DecisionCard: DC-propeller-cfd-001 — 螺旋桨CFD计算网格策略决策

## 元数据
- **Card ID**: DC-propeller-cfd-001
- **Cross-ref**: xref-09
- **Domain**: 推进 × 螺旋桨CFD (propulsion-propeller-cfd)
- **Method**: FVM滑移网格/重叠网格
- **Method Repo**: TensorFVM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
螺旋桨敞水性能CFD网格与湍流模型选择？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| 稳态敞水 | MRF滑移网格 | 计算快，适合K_T/K_Q/η扫描 |
| 非定常脉动 | 滑移网格瞬态 | 捕捉叶频脉动 |
| 桨-舵干扰 | 重叠网格 | 网格独立，相对运动灵活 |

## 验证锚点
- **来源**: ITTC螺旋桨敞水试验规程
- **内容**: ITTC Recommended Procedures 7.5-02-03-02.2
- **证据路径**: ITTC 2021 Proceedings

## 参数范围
- 进速系数 J: 0.0 - 1.2
- 雷诺数 Re: 2×10^5 - 10^7
- 空化数 σ: 0.5 - 10 (非空化工况)
- 螺距比 P/D: 0.6 - 1.4

## 注意事项
- 叶梢间隙网格需加密(y+<1)
- 网格量: 5M-15M(单桨)
- 收敛判据: 力系数波动<0.2%
