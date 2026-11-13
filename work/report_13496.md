# p447w2-n04 · TensorFEM 弹塑性 J2 流动验证面：单轴硬化 / 纯剪屈服 / 厚壁筒弹塑性膨胀

- 构型：TensorPhysics 仓 · 模块 `tensorphysics.fem_elastoplastic`（新建领域目录）
- 运行：`python benchmarks/elastoplastic_j2/run_p447w2_n04.py`（33.9 s，commit `5c273c8b2789`，python 3.11.6 / numpy 2.4.6）
- 机器验收：**全部 PASS**（判据 a–e 逐项见 §3）
- 证据分级：全部为 REAL（闭式解 + 独立有限元实现互裁，无硬编码/随机数）；本文所有表格数字由 `results.json` 程序化注入

## 1. 案例介绍（物理背景 / 几何 / 参数）

船体结构（舱壁、耐压壳、冰带板、局部补强）的极限承载力与残余变形依赖弹塑性本构；本节点建立 J2（von Mises）流动理论 + 线性各向同性硬化的**三算例验证面**，并用一个真正求解边值问题的轴对称有限元核（而非仅点态return mapping）承担厚壁筒算例，从而把“本构正确”升级为“本构 + 单元 + 装配 + 边界条件都正确”。

| 算例 | 几何 | 材料 | 加载 | 参照解 |
|---|---|---|---|---|
| A 单轴拉伸 | 均质点态路径 | E=200 GPa, ν=0.3, σ_y=250 MPa, H=2.0 GPa | ε: 0→5% 应变控制 | σ = σ_y + H ε_p（闭式） |
| B 纯剪 | 均质点态路径 | 同上 | γ_xy: 0→0.4% | τ_y = σ_y/√3 = 144.338 MPa |
| C 厚壁筒 | a=1.00 m 内径, b=8 m 外径（b/a=8），平面应变（u_z≡0） | E=200 GPa, ν=0.3, σ_y=250 MPa, H=0（理想塑性） | 内压 p = 1.2/1.5/2.0 σ_y = 300, 375, 500 MPa | Lamé/Hill 弹塑性闭式解，p_y=142.1 MPa, p_lim=600.3 MPa |
| D 加载-卸载 | 均质点态路径 | 同 A | ε: 0→3%→卸载至 σ=0 | ε_res = ε_max − σ_max/E |

厚壁筒是本节点唯一需要边值求解的算例：内压 σ_rr(a) = −p，外表面自由，轴向位移全约束（ε_zz≡0，广义平面应变）。理想塑性假设使 Lamé/Hill 闭式解严格成立（含硬化时无闭式解），故算例 C 用 H=0；硬化能力由算例 A/D 覆盖。

## 2. 怎么做的（方法 / 流程 / 关键设置）

**本构核**（`constitutive.py`，Mandel 记法）

- 采用 Mandel 度量让内积直化为欧氏点积：`e_M = [ε_xx, ε_yy, ε_zz, √2ε_xy, √2ε_yz, √2ε_xz]`，等效应力 `σ_eq = √(3/2)‖s_M‖`，流动方向 `n = s_M/‖s_M‖`，塑性增量 `Δε_p = √(3/2)Δγ n`、`Δα = Δγ`。
- 径向回映（closest-point projection）闭式：`Δγ = (q_tr − σ_y(α_n))/(3G+H)`；一致切线 `C_ep = K m mᵀ + 2Gβ P_dev − 2Gγ̄ n nᵀ`，`β = 1 − 3GΔγ/q_tr`，`γ̄ = 3Gσ_y(α_n)/((3G+H)q_tr)`。
- 一致切线经中心差分核对（相对误差 < 1e-6，见 pytest），弹性切线剪切对角元为 G（工程剪应变口径）。
- 单轴算例**不用 1D 简化冒充 3D 核**：给定 ε_xx 后对 ε_yy=ε_zz 做局部 Newton（σ_yy=σ_zz=0），每一步都调用完整 3D return mapping；1D 特化（`Δγ = f/(E+H)`）仅作交叉验证，两条路径在 pytest 中一致到 1e-12。

**轴对称有限元核**（`axisym.py`）

- 单元：Q8 serendipity（3×3 Gauss，**生产单元**）/ Q4（2×2 Gauss，仅作对照）；应变分量 `[ε_rr, ε_zz, ε_θθ, γ_rz]`，`ε_θθ = u_r/r`，`ε_zz ≡ 0`（全部节点 u_z 固定）。
- 装配：`K_e = ∫ BᵀCB r dr dz`、`f_int = ∫ Bᵀσ r dr dz`（统一省去 2π，按每弧度计）。
- 内压载荷：内表面外法向 n = −e_r，故 t = −p n = +p e_r，`f_i = +p a ∫N_i dz`（每弧度）。
- 求解：等增量加载 + 全 Newton（历史量 (ε_p, α) 存于每个 Gauss 点，每步从上一收敛步提交）；收敛判据 ‖R‖/‖F_ext‖ < 1e-10，实测 2–7 次迭代收敛。
- 网格：径向几何渐变（首末单元长度比 3，随 n_rad 固定），`n_axial=1`；平面应变下解与 z 无关（pytest 中对 `n_axial=1` 与 2 做了等价性断言）。

**闭式参照解**（`thick_cylinder.py`，自行推导并写成可复算代码）

塑性区（a≤r≤r_p，σ_zz=(σ_rr+σ_θθ)/2，s_zz=0 → σ_eq=(√3/2)(σ_θθ−σ_rr)）：`σ_rr = −p + 2k ln(r/a)`，`σ_θθ = σ_rr + 2k`，`k = σ_y/√3`。

弹性区（r_p≤r≤b）：Lamé `σ_rr = A − B/r²`、`σ_θθ = A + B/r²`，`A = p_p r_p²/(b²−r_p²)`、`B = A b²`。

界面匹配（径向平衡 + 弹性侧屈服，`u = (r_p/b)²`）：

```
p(r_p) = 2k ln(r_p/a) + σ_y (1−u) / sqrt(3 + u² (1−2ν)²)
p_y    = σ_y (1 − (a/b)²) / sqrt(3 + (a/b)⁴ (1−2ν)²)   ≈ σ_y(b²−a²)/(√3 b²)
p_lim  = 2k ln(b/a)
```

界面半径的反算用二分（200 次，容差 1e-15·b）。`ν→1/2` 时上式退化为经典 Hill 形式 `p = 2k[ln(r_p/a) + (1−u)/2]`，本仓代码对三档压力与该经典式的偏差分别为 0.0031%, 0.0094%, 0.0714%，证明推导与文献一致。

**界面半径的 FEM 后处理**（本节点的关键方法学投入）

直接用 Gauss 点等效应力找 `σ_eq = σ_y` 会被界面附近的单元级应力振荡污染（Q4 尤甚）。改用**纯偏量量的弹性区 Lamé 拟合**：弹性区 `d(r)=|σ_rr−σ_θθ| = 2B/r²`，塑性条件 `d = 2σ_y/√3`，故 `r_p = √(B/k)`，B 由「α=0 且离界面与外边界各≥1 个特征宽度」的 Gauss 点最小二乘拟合。该估计对平均应力误差免疫（见 §5 的 Q4/Q8 对照）。

## 3. 计算结果

### 3.1 判据总表（机器可裁）

| 判据 | 要求 | 实测 | 判定 |
|---|---|---|---|
| (a) 单轴 ε=0/1%/2%/5% 四点 | ≤3% | 最大 5.16e-14% | PASS |
| (b) 纯剪 τ_y vs σ_y/√3 | ≤2% | 0.000000% | PASS |
| (c) 厚壁筒 r_p vs 闭式（三档压力 × 4/8/16 网格） | ≤5% | 最大 4.433%（n=4, p=2.0σ_y；n=16 时 ≤0.137%） | PASS |
| (d) 加载 3% 后卸载残余应变 | ≤3% | 0.000000% | PASS |
| (e) r_p 4/8/16 单调收敛 + GCI_fine | ≤5% | 三档压力均单调；GCI_fine 最大 1.124% | PASS |
| (f) 六要素报告 + 图（曲线/云图/界面位置） | 齐备 | 7 图（§4）+ 本文 + `results.json` | PASS |

### 3.2 算例 A：单轴拉伸硬化曲线

| ε | σ 数值 [MPa] | σ 解析 [MPa] | 相对误差 | ε_p 数值 | ε_p 解析 |
|---|---|---|---|---|---|
| 0.000 | 0.0000 | 0.0000 | 0.000% | 0.000000 | 0.000000 |
| 0.010 | 267.3267 | 267.3267 | 2.23e-14% | 0.008663 | 0.008663 |
| 0.020 | 287.1287 | 287.1287 | 4.15e-14% | 0.018564 | 0.018564 |
| 0.050 | 346.5347 | 346.5347 | 5.16e-14% | 0.048267 | 0.048267 |

硬化律 σ = σ_y + H·ε_p 的代回残差（按 σ_y 归一）：7.15e-16。

### 3.3 算例 B：纯剪首屈服

| 量 | 数值 | 参照 |
|---|---|---|
| τ_y（数值首屈服，应力插值） | 144.3376 MPa | 144.3376 MPa（σ_y/√3） |
| γ_y（首屈服剪应变） | 0.001880 | τ_y/G = 0.001876（G=E/2(1+ν)=76.923 GPa） |
| 屈服后斜率 dτ/dγ | 6.61e+08 Pa | GH/(3G+H) = 6.61e+08 Pa（相对差 6.84e-14） |

### 3.4 算例 C：厚壁筒弹塑性膨胀（FEM vs Lamé/Hill）

| p [MPa] | p/σ_y | r_p 闭式 [m] | r_p FEM 4 单元 | r_p FEM 8 单元 | r_p FEM 16 单元 | 最大误差 |
|---|---|---|---|---|---|---|
| 300 | 1.20 | 1.7566 | 1.7269（1.690%） | 1.7523（0.242%） | 1.7575（0.055%） | 1.690% |
| 375 | 1.50 | 2.3190 | 2.2930（1.121%） | 2.3013（0.763%） | 2.3222（0.137%） | 1.121% |
| 500 | 2.00 | 3.8516 | 3.6809（4.433%） | 3.8124（1.018%） | 3.8528（0.030%） | 4.433% |

屈服压力 p_y = 142.08 MPa，极限压力 p_lim = 600.28 MPa；三档压力分别位于弹塑性区 p/p_lim = 0.500, 0.625, 0.833。

### 3.5 算例 D：加载—卸载残余应变

| 量 | 数值 |
|---|---|
| ε_max | 0.03 |
| σ_max | 306.9307 MPa |
| ε_res 数值（σ=0 插值） | 0.02846535 |
| ε_res 解析 = ε_max − σ_max/E | 0.02846535 |
| 相对误差 | 0.000 |

### 3.6 算例 E：网格收敛与 GCI

| p [MPa] | r_p(4) | r_p(8) | r_p(16) | 单调 | 观测阶 p_obs | GCI_fine |
|---|---|---|---|---|---|---|
| 300 | 1.7269 | 1.7523 | 1.7575 | PASS | 2.28 | 0.096% |
| 375 | 2.2930 | 2.3013 | 2.3222 | PASS | -1.33（非渐近，取 p=1） | 1.124% |
| 500 | 3.6809 | 3.8124 | 3.8528 | PASS | 1.70 | 0.580% |

### 3.7 附带诊断：单元族精度（弹性 Lamé 问题）

| 单元 | n_rad=4 | 8 | 16 |
|---|---|---|---|
| Q4 max\|σ_rr−σ_rr^Lamé\|/p | 30.19% | 19.07% | 10.80% |
| Q8 max\|σ_rr−σ_rr^Lamé\|/p | 10.37% | 4.34% | 1.62% |

该诊断解释了为何生产单元选 Q8：Q4 在 n_rad=16 时仍有 10.80% 的应力误差（平面应变下 λ 放大了插值应变误差），会污染界面半径判断。

### 3.8 既有实现一致性审计（附带发现，不覆盖原模块）

本仓 `tensorphysics.plasticity.j2_flow.thick_cylinder_vonmises_rp` 采用“无限介质”近似 `r_p = a·exp(√3 p/(2σ_y))`，忽略弹性区项。本节点用同一闭式体系的正确解给出量化对照：

| p/σ_y | r_p 正确解 [m] | r_p 旧式 [m] | 旧式相对误差 | 经典 ν→1/2 式误差 |
|---|---|---|---|---|
| 1.20 | 1.7566 | 2.8270 | 60.9% | 0.0031% |
| 1.50 | 2.3190 | 3.6658 | 58.1% | 0.0094% |
| 2.00 | 3.8516 | 5.6522 | 46.7% | 0.0714% |

自洽性反证：在首次屈服压力 p_y = 1.42e+08 Pa 处，精确解必为 r_p = a = 1.00 m，而旧式给出 r_p = 1.6359 m（>a），即在屈服门槛处即已不自洽。本节点**未改动**该既有模块（其单测仍绿），而是把正确参照解与新实现放在新目录内，并把该差异登记为后续修复项。

## 4. 结果图

![fig_a_uniaxial.png](../artifacts/j2_elastoplastic/fig_a_uniaxial.png)

*Case A: uniaxial tension hardening curve (numerical vs analytic) and anchor-point relative errors against the 3% acceptance line.*  
`artifacts/j2_elastoplastic/fig_a_uniaxial.png` · sha256 `4578af0384de8ce9…`

![fig_b_pure_shear.png](../artifacts/j2_elastoplastic/fig_b_pure_shear.png)

*Case B: pure shear stress-strain curve with the von Mises first-yield stress sigma_y/sqrt(3) and the detected yield point.*  
`artifacts/j2_elastoplastic/fig_b_pure_shear.png` · sha256 `8ee414e0652e2eed…`

![fig_d_unloading.png](../artifacts/j2_elastoplastic/fig_d_unloading.png)

*Case D: loading to 3% axial strain followed by unloading to zero stress; residual strain vs the analytic value.*  
`artifacts/j2_elastoplastic/fig_d_unloading.png` · sha256 `7b34841afb89403e…`

![fig_c_thick_cylinder_profiles.png](../artifacts/j2_elastoplastic/fig_c_thick_cylinder_profiles.png)

*Case C: radial stress distribution, yield-ratio indicator, equivalent plastic strain and axial reaction stress of the pressurised cylinder (FEM vs closed form), with the elastoplastic boundary marked.*  
`artifacts/j2_elastoplastic/fig_c_thick_cylinder_profiles.png` · sha256 `5d1d646ebcd685fd…`

![fig_c_eq_stress_cloud.png](../artifacts/j2_elastoplastic/fig_c_eq_stress_cloud.png)

*Case C: equivalent-stress cloud over the meridian section and the equivalent-stress distribution across the wall (yield plateau = yield stress, kink at the elastoplastic boundary).*  
`artifacts/j2_elastoplastic/fig_c_eq_stress_cloud.png` · sha256 `274a0c5d78fb5989…`

![fig_e_mesh_convergence.png](../artifacts/j2_elastoplastic/fig_e_mesh_convergence.png)

*Case E: monotone mesh convergence of the interface radius for the three pressures and the Roache GCI of the finest grid against the 5% limit.*  
`artifacts/j2_elastoplastic/fig_e_mesh_convergence.png` · sha256 `3a37db2c2de1496c…`

![fig_elast_element_accuracy.png](../artifacts/j2_elastoplastic/fig_elast_element_accuracy.png)

*Diagnostic: elastic Lame thick-cylinder stress error of the bilinear Q4 and serendipity Q8 elements (justifies the Q8 production element).*  
`artifacts/j2_elastoplastic/fig_elast_element_accuracy.png` · sha256 `ee2c5776db5a4b2a…`

## 5. 注意点（踩过的坑 / 局限 / 适用范围）

1. **Mandel 与工程剪应变的不对称换算**：`ε_eng,shear = √2 ε_M`，但 `σ_eng,shear = σ_M/√2`；早期把同一 `√2` 用于应力，导致纯剪 τ 恰好放大 2 倍（144.3 → 288.6 MPa）而被判据抓住。切线同理：`C_eng = D·C_M·S`，剪切行列各带 1/√2，使弹性剪切对角元为 G 而非 2G。
2. **等效应力归一化**：Mandel 范数 `‖s_M‖ = √(2/3)σ_eq`，忘记 √(3/2) 会让屈服面放大 √1.5 倍；pytest 用 `σ_eq(return) = σ_y(α)` 与切线中心差分双重锁定。
3. **一致切线里 σ_y 取 α_n 而非 α_{n+1}**：`γ̄ = 3G/(3G+H) − 3GΔγ/q_tr` 化简后是 `3Gσ_y(α_n)/((3G+H)q_tr)`；误用 α_{n+1} 会造成约 H Δγ/σ_y 量级（本材料约 3e-4）的切线误差，中心差分立刻暴露。
4. **1D 简化不能替代 3D 核**：单轴应力下一致性条件给 `Δγ = f/(E+H)`，而全应变受控时是 `f/(3G+H)`；用错会带来约 1.2% 的系统偏差。本节点主路径全部走 3D 核，1D 特化只做交叉验证（pytest 中断言二者一致）。
5. **Q4 单元在平面应变弹塑性下不足**：内压载荷符号错（应为 +p e_r）是筛查中先被修掉的硬错；随后 Q4 在 n_rad=16 的应力误差仍达 10.8%，把 λ 放大的插值误差带进了界面判断，才改用 Q8。
6. **界面半径不能用 σ_eq = σ_y 的 Gauss 点插值**：Q4/Q8 在界面附近存在单元级应力振荡，逐点插值偏差可达 20–35%；改用弹性区偏量量 Lamé 拟合 `r_p = √(B/k)` 后收敛干净（n=16 误差 ≤0.14%）。
7. **平面应变 σ_zz 在界面处有跳变**：塑性区 σ_zz→(σ_rr+σ_θθ)/2，弹性区 σ_zz = ν(σ_rr+σ_θθ)，仅当 ν=1/2 时无跳变。这是理想弹塑性平面应变模型的固有性质，不影响 σ_rr/σ_θθ/r_p（三者连续，见 §4 第四子图与 pytest 连续性断言），但**不能**把 σ_zz 当作验证量。
8. **适用范围**：小应变、率无关、各向同性硬化、单调或简单卸载路径；未覆盖随动硬化（Bauschinger）、大变形、循环塑性与损伤耦合。厚壁筒算例限于理想塑性与轴对称（无偏心/无端部效应）。
9. **网格收敛判据的非渐近性**：p=1.5σ_y 的 4/8/16 序列虽单调，但观测阶为负（粗网格未进入渐近区），此时按 p=1 取 GCI 上界 1.12%，而不是给出无意义的负值。

## 6. 误差判定（逐项回答“是否 <3%”）

| 关键量 | 基准 | 误差 | 是否 <3% |
|---|---|---|---|
| 单轴 σ(ε=1%) | 闭式 σ=σ_y+Hε_p | 2.23e-14% | 是 |
| 单轴 σ(ε=5%) | 闭式 | 5.16e-14% | 是 |
| 纯剪 τ_y | σ_y/√3 | 0.000000% | 是 |
| 厚壁筒 r_p(p=1.2σ_y) | Lamé/Hill | 0.055%（n=16） | 是 |
| 厚壁筒 r_p(p=1.5σ_y) | Lamé/Hill | 0.137%（n=16） | 是 |
| 厚壁筒 r_p(p=2.0σ_y) | Lamé/Hill | 0.030%（n=16） | 是 |
| 残余应变 ε_res | ε_max−σ_max/E | 0.000000% | 是 |
| 厚壁筒 r_p 最粗网格（判据 c 的守门值） | Lamé/Hill | 4.433%（n=4, p=2.0σ_y） | 否（4.4%<5%，判据 c 的门限为 5%） |

结论：**判据 a–e 全部满足**；其中判据 c 的唯一“>3%”值是 n=4 的粗网格守门值 4.43%，仍低于该项 5% 的验收门限，且细化到 n=16 后降至 ≤0.14%。无 honest-FAIL 项。

## 7. 可复现与审计链

| 项 | 值 |
|---|---|
| 源码 | `src/tensorphysics/fem_elastoplastic/{constitutive,axisym,thick_cylinder,verification}.py` |
| 测试 | `tests/test_fem_elastoplastic_j2.py`（18 用例，9.1 s 全绿） |
| 运行器 | `benchmarks/elastoplastic_j2/run_p447w2_n04.py` |
| 数字工件 | `artifacts/j2_elastoplastic/results.json`（判据/曲线/剖面全量） |
| 溯源 | `artifacts/j2_elastoplastic/provenance.json`（commit `5c273c8b2789`, python 3.11.6, numpy 2.4.6, 2026-11-11T07:09:37Z） |
| 图 | `artifacts/j2_elastoplastic/fig_*.png`（每图 sha256 记入 results.json） |

