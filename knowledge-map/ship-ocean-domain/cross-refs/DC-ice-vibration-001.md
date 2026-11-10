# DecisionCard: DC-ice-vibration-001 — 冰致振动锁频DEM-FEM耦合决策

## 元数据
- **Card ID**: DC-ice-vibration-001
- **Cross-ref**: xref-07
- **Domain**: 冰区航行 × 冰致振动 (ice-mechanics-vibration)
- **Method**: DEM+FEM耦合
- **Method Repo**: TensorDEM + TensorFEM
- **Created**: 2026-11-10
- **Mission**: m8817

## 关键问题
冰-结构相互作用中锁频(lock-in)现象的数值捕捉？

## 决策判据

| 条件 | 推荐方法 | 理由 |
|------|---------|------|
| 冰速 0.05-0.3 m/s 且结构固有频率 0.5-5 Hz | 锁频风险高 | 冰力频率与结构频率接近 |
| 需捕捉冰力周期性 | DEM时间步 < 结构周期/20 | 时间分辨率要求 |
| 结构响应 | FEM模态叠加或瞬态直接积分 | 取决于非线性程度 |

## 验证锚点
- **来源**: TensorPhysics冰致振动锁频基准
- **内容**: 冰-结构相互作用锁频现象验证
- **证据路径**: TensorPhysics benchmarks/icebreaking/

## 参数范围
- 冰速: 0.01 - 1.0 m/s
- 结构固有频率: 0.1 - 10 Hz
- 冰-结构接触刚度: 10^7 - 10^10 N/m
- 阻尼比: 0.01 - 0.10

## 注意事项
- 锁频区间: 冰力频率/结构频率 ≈ 0.8 - 1.2
- 需足够长时间模拟以捕捉锁频建立过程
- 冰破坏模式(挤压/弯曲)影响冰力频谱
