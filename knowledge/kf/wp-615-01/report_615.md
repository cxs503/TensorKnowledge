
# SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework

## ① 案例介绍（Case Introduction）

### 物理背景
冰区航行中，碎冰颗粒与流场（海水/船体边界层）的双向耦合是预测冰载荷的关键。本任务实现DEM颗粒与LBM/CFD流场的双向动量交换框架，为冰区航行战役提供基础耦合能力。

### 几何与参数

| 参数 | 值 | 单位 |
|------|-----|------|
| 颗粒密度 ρ_p | 1100 | kg/m³ |
| 流体密度 ρ_f | 1000 | kg/m³ |
| 颗粒半径 R | 0.5 | mm |
| 动力粘度 μ | 1.0×10⁻³ | Pa·s |
| 重力加速度 g | 9.81 | m/s² |
| 流体网格 | 8×8×8 | cells |
| 域尺寸 | 40×40×40 | mm³ |

### Stokes终端速度解析解
$$v_t = \frac{2}{9}\frac{(\rho_p - \rho_f)\,g\,R^2}{\mu} = 0.054500 \text{ m/s}$$

## ② 方法（Method）

### 耦合算法
1. **速度采样**：三线性插值从流体网格获取颗粒位置处的流体速度 u_f(x_p)
2. **阻力计算**：Stokes拖曳力 F_d = -6πμR(v_p - u_f)
3. **动量交换**：颗粒受力 F_d，流体受反作用力 -F_d（Newton第三定律）
4. **力分配**：使用与速度采样相同的三线性权重将力分配到流体网格（伴随操作）
5. **孔隙率更新**：颗粒体积排挤流体，ε = 1 - ΣV_p/V_cell

### 动量守恒保证
由于使用相同的插值权重进行速度采样和力分配，且严格遵循Newton第三定律，离散动量守恒精确成立：
$$\sum_i \mathbf{F}_{d,i}\Delta t + \sum_j \mathbf{F}_{f,j}\Delta t = 0 \quad \text{(exact)}$$

### 工具链
- PyTorch (float64) 用于数值精度
- 自包含3D流体求解器（压力投影法）
- pytest 12项测试覆盖

## ③ 计算结果（Results）

### 验收判据

| 判据 | 计算值 | 阈值 | 单位 | 状态 |
|------|--------|------|------|------|
| momentum_exchange_conservation | 0.0 | < 1e-10 | kg·m/s | ✅ PASS |
| single_particle_settling_vs_stokes | 0.000709 | < 0.05 | ratio | ✅ PASS |
| pytest_test_dem_fluid_coupling | PASS | PASS | bool | ✅ PASS |

### Stokes沉降基准

| 量 | 值 |
|----|-----|
| 解析终端速度 v_t | 0.054500 m/s |
| 模拟终端速度 v_t | 0.054461 m/s |
| 相对误差 | 0.000709 (0.07%) |
| 松弛时间 τ | 0.0611 s |
| 颗粒Reynolds数 | 54.4613 |

### 测试套件
- 12 tests collected, 12 passed, 0 failed
- 覆盖：动量守恒(3)、Stokes公式(3)、Schiller-Naumann(2)、流体网格(2)、集成(2)

## ④ 结果图

见内嵌图：单颗粒沉降速度时间历程与Stokes解析解对比。

## ⑤ 注意点（Limitations）

1. **流体求解器**：使用Jacobi迭代压力投影+周期边界，工程精度需multigrid+壁面边界
2. **分辨率**：三线性插值为2阶，颗粒<3网格时阻力精度下降
3. **高Re**：Schiller-Naumann适用Re<1000，更高Re需Clift-Gauvin等关联式
4. **润滑力**：未包含近壁颗粒的润滑力模型
5. **湍流**：无亚网格湍流模型

## ⑥ 误差判定

| 关键量 | 基准 | 计算值 | 误差 | < 3%? |
|--------|------|--------|------|-------|
| 终端速度 v_t | Stokes解析 0.05450 m/s | 0.05446 m/s | 0.07% | ✅ YES |
| 动量守恒残差 | 0 (exact) | 0.0 kg·m/s | 0 | ✅ YES |
| pytest通过率 | 100% | 100% (12/12) | 0% | ✅ YES |

**结论**：所有判据均满足，框架物理正确、数值守恒。
