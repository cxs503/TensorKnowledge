# DecisionCard: DC-slamming-coupled-001 — 砰击载荷流固耦合决策

## 元数据
- **Card ID**: DC-slamming-coupled-001
- **Cross-ref**: xref-12
- **Domain**: 耐波 × 砰击载荷 (seakeeping-motion-slamming)
- **Method**: CFD+结构响应耦合
- **Method Repo**: TensorFVM + TensorFEM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
砰击载荷计算中何时需要双向耦合？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| 弹性响应时间 < 砰击持续时间 | 双向耦合必须 | 结构变形改变流场 |
| 刚性假设下压力峰值 | 单向CFD→FEM可接受 | 结构变形可忽略 |
| 湿甲板砰击 | VOF自由面+结构瞬态响应 | 自由面变形显著 |

## 验证锚点
- **来源**: ITTC耐波性试验规程
- **内容**: ITTC Recommended Procedures 7.5-02-07-04.2
- **证据路径**: ITTC 2021 Proceedings

## 参数范围
- 砰击速度 V: 2 - 15 m/s
- 结构固有频率: 5 - 100 Hz
- 砰击持续时间: 1 - 50 ms

## 注意事项
- 双向耦合需子迭代保证界面平衡
- 时间步需满足CFL和结构稳定性
- 湿甲板砰击需VOF捕捉自由面
