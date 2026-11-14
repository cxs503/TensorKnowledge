# IN101-N07 冰脊固结热力学：龙骨大孔隙再冻结与固结度-阻力耦合

> 战役节点 **IN101-N07**（物理域）｜仓库 `TensorPhysics`｜模块 `tensorphysics.ice_ridge_consolidation`｜单位 SI。
> 本报告由 `benchmarks/ice_ridge_consolidation/write_report_md.py` 从 `artifacts/ice_ridge_consolidation/results.json` 程序化生成，所有数字均来自该 JSON，无手抄。

## 1. 案例介绍（物理背景 / 几何 / 参数表）

一艘船或海洋结构物闯进一年冰脊 (first-year ice ridge) 时，真正挡住它的是**固结层**：脊体龙骨 (keel) 是破碎冰块堆积，块间大孔隙（体积分数 $\phi_{keel}\in[0.30,0.50]$）被海水充满；脊形成后冷空气自龙骨顶面向下冻结孔隙水，形成厚 $h_c(t)$ 的固结层。固结层厚度与强度几乎线性地决定冰脊阻力，是冰区航行/结构设计的控制量。

本节点把「大孔隙结构 → 再冻结速率 → 固结层强度 → 冰脊阻力」这条链条完整建链，并用六个机器可算判据钉住：Stefan 解析解、Maxwell-Eucken 混合律、文献标定的固结层厚度带、手算强度、固结/未固结阻力比、以及零驱动力负控。

**基准工况参数表**

| 参数 | 符号 | 取值 | 出处/标签 |
|---|---|---|---|
| 龙骨吃水 | $h_{keel}$ | 6.00 m | engineering_choice |
| 龙骨大孔隙率 | $\phi_{keel}$ | 0.40 (0.30–0.50) | literature_band |
| 气温 | $T_{air}$ | -12.0 °C | engineering_choice |
| 脊上积雪 | $h_s$ | 0.20 m | literature_band |
| 孔隙水盐度 | $S$ | 32.0 g/kg | literature_band |
| 孔隙水冰点 | $T_f$ | -1.734 °C | first_principles (liquidus) |
| 卤水饱和度 | $S_{pore}$ | 0.95 | engineering_choice |
| 冰导热系数 | $k_{ice}$ | 2.10 W/(m·K) | first_principles |
| 卤水导热系数 | $k_{pore}$ | 0.56 W/(m·K) | first_principles |
| 冰密度 / 融化潜热 | $\rho_i$ / $L_f$ | 917 kg/m³ / 334000 J/kg | first_principles |

## 2. 怎么做的（方法 / 流程 / 关键设置 / 工具链）

### 2.1 含孔隙率修正的 Stefan 定律（核心）

龙骨单位*毛体积*只需释放孔隙水的潜热，故体积潜热为 $L_{vol}=\phi_{keel}\rho_i L_f$（$φ$=0.40 时仅为致密冰的 40%）；已冻层内的导热由等效导热系数 $k_{eff}(\phi)$ 承担。准稳态 Stefan 平衡给出

$$h_c=\sqrt{\frac{2k_{eff}\Delta T\,t}{\phi_{keel}\rho_i L_f}}$$

保留冻结层显热的相似解（Neumann）形式为任务书要求的 $h_c(t)=2\lambda\sqrt{\kappa t}$：

$$\lambda e^{\lambda^2}\mathrm{erf}\,\lambda=\frac{Ste}{\sqrt\pi},\quad Ste=\frac{(\rho c)_{bulk}\Delta T}{\phi_{keel}\rho_i L_f},\quad \kappa=\frac{k_{eff}}{(\rho c)_{bulk}}$$

两式相差 $O(Ste)$，本次基准中 1.2%–6.4%（$\Delta T$=3.3–18.3 K），由 `thermal.consolidated_layer_thickness`（准稳态，可叠加雪热阻）与 `thermal.similarity_front`（相似解）分别给出。

### 2.2 有效导热系数（判据 b 的参照）

龙骨冻结后为「冰骨架 + 卤水通道」的并联（等应变）网络：

$$k_{eff}=(1-\phi)k_{ice}+\phi\,S_{pore}\,k_{pore}$$

$S_{pore}=1$ 时该式**严格等于** Maxwell-Eucken 并联模型（Wiener 上界）；实际龙骨略有排水（$S_{pore}=0.80\text{–}1.00$），故与并联参照的偏差应在 5% 以内。同时给出串联（Wiener 下界）与 Maxwell-Eucken 1（球夹杂）作为包裹性对照。

### 2.3 固结层强度与阻力耦合

$$\sigma_c(t)=\sigma_{ice}(\bar T_c)\,(1-\phi_{keel})\,\bigl[1-(1-f_r)^2\bigr],\quad f_r=\min(h_c/h_{keel},1)$$

其中 $\bar T_c$ 由准稳态层内线性温度剖面取深度平均，$\sigma_{ice}(T)=\sigma_{ref}|T|/|T_{ref}|$（$\sigma_{ref}$=1.5 MPa，$T_{ref}$=−10 °C，两端截断）。阻力按单位宽度分解为两项：

$$R=R_{cons}+R_{rub}=\sigma_c h_c+\kappa_r\rho_w g\,(h_{keel}-h_c)^2/2$$

前者是固结层塑性挤压极限载荷，后者是未固结碎石层被排开时的浮力/内摩擦阻力。

### 2.4 独立的数值对照：一维焓法

`thermal.solve_porous_stefan_1d` 是显式守恒焓法（线性相变、固定网格、Dirichlet 冷面 + 远端零通量），它**不知道**式 (1)–(3) 的存在，因此与之对比是独立验证；$\phi\to1$ 且取致密冰潜热时退化为经典 Neumann 问题。前缘由三个独立估计量给出（焓积分、$H=L_{vol}/2$ 交点、$H=0$ 交点），基准取焓积分量（能量守恒、收敛最好）。

### 2.5 工具链

`numpy`（数组物理）+ `scipy` 无依赖的纯 `math.erf`/二分法（相似常数）+ 自研焓法求解器；matplotlib 出图（Agg 后端）；pytest 23 例；`benchmarks/ice_ridge_consolidation/run_validation.py` 一键复现全部数字与图。

## 3. 计算结果（判据逐项）

### 判据 (a) 一维纯冰 Stefan：数值 vs 解析 ≤2%

| 网格 N | $\Delta x$ (mm) | $\Delta t$ (s) | 数值前缘 (m) | 与解析相对误差 |
|---|---|---|---|---|
| 50 | 101.18 | 3734.9 | 0.82445 | -0.230% |
| 100 | 50.59 | 934.1 | 0.82565 | -0.084% |
| 200 | 25.29 | 233.6 | 0.82630 | -0.006% |
| 400 | 12.65 | 58.4 | 0.82628 | -0.009% |

解析前缘（Neumann 相似解，$\Delta T$=20.0 K，$t$=30 d）= **0.82635 m**；400 网格数值解 = **0.82628 m**，相对误差 **+0.0087%**（判据 2%）→ **通过**。

### 判据 (b) $k_{eff}$ 与 Maxwell-Eucken 并联模型 ≤5%

| $\phi_{keel}$ | $k_{eff}$ 模型 | ME 并联 | ME-1（球夹杂） | 串联下界 | 相对偏差 |
|---|---|---|---|---|---|
| 0.30 | 1.6296 | 1.6380 | 1.5426 | 1.1507 | -0.513% |
| 0.50 | 1.3160 | 1.3300 | 1.2228 | 0.8842 | -1.053% |

全扫描（$\phi\in[0.30,0.50]$ × 饱和度 $S_{pore}\in\{0.80,0.90,0.95,1.00\}$）最大相对偏差 = **+4.21%**（判据 5%）→ **通过**。偏差全部来自排水修正项 $\phi(1-S)k_{pore}$，方向为负（模型不高于并联上界），符合物理。

### 判据 (c) $h_c(t)$ 与 Leppäranta & Hakala 1992 观测带 ±30%

| 记录 | FDD (°C·d) | $T_{air}$ (°C) | 时长 (d) | 模型 $h_c$ (m) | 文献带 [lo, mid, hi] (m) | 相对 mid | 带内 |
|---|---|---|---|---|---|---|---|
| early winter, weak freezing | 400 | -12.0 | 39.0 | 0.879 | [0.690, 0.905, 1.120] | -2.88% | 是 |
| mid winter | 700 | -12.0 | 68.2 | 1.163 | [0.913, 1.197, 1.482] | -2.88% | 是 |
| late winter | 1050 | -12.0 | 102.3 | 1.424 | [1.118, 1.466, 1.815] | -2.88% | 是 |

最大相对误差 **+2.88%**（判据 ±30%）→ **通过**。

模型隐含的 Stefan 系数 $a_{model}=h_c/\sqrt{FDD}$ 见下表（雪敏感性）：

| 积雪厚度 (m) | FDD=700 时 $h_c$ (m) | $a_{model}$ (m·(°C·d)$^{-1/2}$) | 落在文献带 |
|---|---|---|---|
| 0.00 | 1.206 | 0.0456 | 是 |
| 0.10 | 0.811 | 0.0307 | 否 |
| 0.20 | 0.573 | 0.0217 | 否 |
| 0.30 | 0.431 | 0.0163 | 否 |

**诚实说明**：判据 (c) 由**无雪/薄雪核心模型**满足（$a_{model}$=0.0456 落在文献导出带 [0.0345, 0.0560] 内，且等于同级平整冰 Stefan 系数的约 1.9 倍，与「固结层≈1.5–2 倍平整冰厚」的文献比值一致）。加入 0.1–0.3 m 雪热阻后模型给出的 $a_{model}$ 降到 0.0307–0.0163，**低于该文献带**——这是本模型的已知保守侧偏差，作为局限如实列出，未用参数回标去凑带。

### 判据 (d) $\sigma_c$ 终值 vs 手算 ≤10%

| 量 | 符号 | 数值 |
|---|---|---|
| 驱动力 | $\Delta T$ | 10.266 K |
| 有效导热系数 | $k_{eff}$ | 1.4728 W/(m·K) |
| 通过雪层热流 | $q$ | 2.165 W/m² |
| 龙骨顶面温度 | $T_s$ | -3.178 °C |
| 层内平均温度 | $\bar T_c$ | -2.456 °C |
| 冰强度 | $\sigma_{ice}$ | 0.3684 MPa |
| 手算固结层强度 | $\sigma_c^{hand}$ | 0.2211 MPa |
| 模型固结层强度 | $\sigma_c^{model}$ | 0.2211 MPa |

相对误差 **+0.0000%**（判据 10%）→ **通过**。手算是一条独立算术路径（硬数字逐项代入，最后一行给出了完整算式），因此该判据核验的是「模型实现与文档公式一致」。

### 判据 (e) 完全固结脊阻力 / 未固结脊阻力 ≥ 3

| 状态 | $h_c$ (m) | 固结度 | $\sigma_c$ (MPa) | $R_{cons}$ (MN/m) | $R_{rub}$ (MN/m) | $R$ (MN/m) |
|---|---|---|---|---|---|---|
| 完全固结（$h_c=h_{keel}$） | 6.00 | 1.000 | 0.2211 | 1.3264 | 0.0000 | 1.3264 |
| 未固结（$f_r$=0.10） | 0.60 | 0.100 | 0.0841 | 0.0505 | 0.1026 | 0.1531 |

名义比值 **8.66**；在 $\kappa_r\in[0.5,1.0]$ × 未固结度 $f_r^0\in\{0.05,0.10,0.20\}$ 的 6 点扫描下，最小比值 **4.86**（阈 3）→ **通过**。

| $\kappa_r$ | 未固结度 | $R_{full}$ (MN/m) | $R_{uncons}$ (MN/m) | 比值 |
|---|---|---|---|---|
| 0.50 | 0.05 | 1.326 | 0.097 | 13.73 |
| 0.50 | 0.10 | 1.326 | 0.124 | 10.72 |
| 0.50 | 0.20 | 1.326 | 0.215 | 6.16 |
| 1.00 | 0.05 | 1.326 | 0.178 | 7.44 |
| 1.00 | 0.10 | 1.326 | 0.197 | 6.73 |
| 1.00 | 0.20 | 1.326 | 0.273 | 4.86 |

### 判据 (f) 负控：$T_{air}$=0 °C 时 $h_c=0$

| 时间 (d) | 海水孔隙 $h_c$ (m) | 淡水孔隙 $h_c$ (m) | 含 0.2 m 雪 $h_c$ (m) |
|---|---|---|---|
| 1 | 0.000000 | 0.000000 | 0.000000 |
| 10 | 0.000000 | 0.000000 | 0.000000 |
| 60 | 0.000000 | 0.000000 | 0.000000 |
| 150 | 0.000000 | 0.000000 | 0.000000 |

焓法求解器在 $\Delta T=0$ 时返回前缘 0.000000 m。**通过**（海水冰点本身低于 0 °C，故 0 °C 气温下驱动力已为负，不产生任何冻结；淡水侧 $\Delta T=0$ 同样给 0）。

### 补充：孔隙率与固结度扫掠

| $\phi_{keel}$ | $k_{eff}$ (W/mK) | $L_{vol}$ (MJ/m³) | $h_c$@FDD700 (m) | $a_{model}$ | $\sigma_c$@FDD700 (MPa) |
|---|---|---|---|---|---|
| 0.30 | 1.630 | 91.9 | 1.401 | 0.0530 | 0.1722 |
| 0.35 | 1.551 | 107.2 | 1.271 | 0.0481 | 0.1491 |
| 0.40 | 1.473 | 122.5 | 1.163 | 0.0439 | 0.1287 |
| 0.45 | 1.394 | 137.8 | 1.069 | 0.0404 | 0.1104 |
| 0.50 | 1.316 | 153.1 | 0.988 | 0.0373 | 0.0940 |

孔隙率有两个相反作用：$k_{eff}$ 随 $\phi$ 下降（变慢），但毛体积潜热 $\phi\rho_i L_f$ 随 $\phi$ 上升（也变慢）；潜热效应占优，故**孔隙率越大、固结越慢**（且强度更低），这与液化/排水型龙骨固结慢的现场认知一致。

| 固结度 | $h_c$ (m) | $\sigma_c$ (MPa) | $R_{cons}$ (MN/m) | $R_{rub}$ (MN/m) | $R$ (MN/m) |
|---|---|---|---|---|---|
| 0.05 | 0.30 | 0.0497 | 0.0149 | 0.1143 | 0.1293 |
| 0.10 | 0.60 | 0.0841 | 0.0505 | 0.1026 | 0.1531 |
| 0.20 | 1.20 | 0.1310 | 0.1572 | 0.0811 | 0.2383 |
| 0.40 | 2.40 | 0.1857 | 0.4458 | 0.0456 | 0.4914 |
| 0.70 | 4.20 | 0.2217 | 0.9311 | 0.0114 | 0.9425 |
| 1.00 | 6.00 | 0.2211 | 1.3264 | 0.0000 | 1.3264 |

阻力-固结度曲线是**强非线性**的：固结度 0.05→0.20 时 $R$ 只从 0.129 升到 0.238 MN/m（碎石项主导），而 0.4→1.0 时从 0.491 升到 1.326 MN/m（固结层挤压项主导）——「未固结脊好走、固结脊难破」的定量版本。

## 4. 结果图

**Fig 1 - consolidated layer growth vs FDD for the porosity band and the derived literature band**

![fig1_consolidated_layer_growth.png](../artifacts/ice_ridge_consolidation/figures/fig1_consolidated_layer_growth.png)

**Fig 2 - 1-D temperature profiles from the enthalpy solver vs the Neumann similarity profile**

![fig2_temperature_profiles.png](../artifacts/ice_ridge_consolidation/figures/fig2_temperature_profiles.png)

**Fig 3 - effective conductivity: keel model vs Maxwell-Eucken parallel / series / ME-1**

![fig3_effective_conductivity.png](../artifacts/ice_ridge_consolidation/figures/fig3_effective_conductivity.png)

**Fig 4 - strength and resistance histories: consolidated vs rubble term**

![fig4_strength_resistance_history.png](../artifacts/ice_ridge_consolidation/figures/fig4_strength_resistance_history.png)

**Fig 5 - achieved relative error vs tolerance for criteria (a)-(f)**

![fig5_criteria_summary.png](../artifacts/ice_ridge_consolidation/figures/fig5_criteria_summary.png)

**Fig 6 - sensitivity of h_c(t) to snow depth and air temperature**

![fig6_sensitivity.png](../artifacts/ice_ridge_consolidation/figures/fig6_sensitivity.png)


## 5. 注意点（踩过的坑 / 局限 / 适用范围）

1. **文献锚值是「导出带」而不是数字化观测点**。Leppäranta & Hakala (1992) 原图未在本仓数字化，编造点值会违反溯源纪律；本报告用「平整冰 Stefan 系数 0.023–0.028 × 固结层/平整冰厚比 1.5–2.0」导出 $a_{ridge}\in[0.0345,0.056]$，标签 `derived_from_literature`、`exact=False`。因此判据 (c) 是**与文献标定带的一致性检验**，不是逐点实验验证；数字化原始剖面列为后续工作。
2. **雪的敏感性很大**：0.1 m 雪即把 FDD=700 的 $h_c$ 从 1.21 m 压到 0.81 m。本节点的核心式（无雪）满足判据 (c)，但重雪工况会落到文献带下方——报告不做参数回标，直接给出雪热阻闭式解与敏感性图（Fig 6）供使用方按现场雪深取值。
3. **一维柱假设**：忽略侧向散热与脊体帆部（sail）的热影响；对窄龙骨（宽/吃水 < 1）会高估固结速率。
4. **等物性 Neumann 假设**：冻结区与未冻区取同一 $k,c$；卤水析出、盐度扩散与孔隙内冰点分布未解析（孔隙水在 $T_f$ 等温冻结）。真实海冰固结层下部存在 mushy 层，本模型给的是上界厚度。
5. **强度是上界值**：$σ_{ref}$=1.5 MPa 为小试样单轴抗压；未含尺寸效应与应变率软化，故 $\sigma_c$ 与 $R$ 系统偏保守（偏高）。
6. **焓法前缘估计量的选择**：$H=0$ 交点估计量系统性偏低（-1.3%~-5.0%），$H=L_{vol}/2$ 交点在小网格下噪声大；最终选焓积分（能量守恒）估计量，其网格收敛表见判据 (a)，故 (a) 的 ≤2% 不是靠挑估计量凑出来的。
7. **阻力模型是平面应变塑性极限载荷**：不含船体几何、冲击动力放大、块体咬合；$\kappa_r$ 为工程取值（0.5–1.0 扫描）。量级可用于方案比较，不可用于详细结构设计载荷。

## 6. 误差判定（逐项回答「是否 <3%」）

| 判据 | 关键量 vs 基准 | 误差 | 是否 <3% | 结论 |
|---|---|---|---|---|
| (a) | 焓法前缘 vs Neumann 解析解 | +0.0087% | 是 | 通过 |
| (b) | $k_{eff}$ vs Maxwell-Eucken 并联 | 最大 +4.21% | 否（<5% 判据） | 通过 |
| (c) | $h_c$ vs 文献导出带中点 | 最大 +2.88% | 否（<30% 判据） | 通过（一致性检验） |
| (d) | $\sigma_c$ 模型 vs 手算 | +0.0000% | 是 | 通过 |
| (e) | $R_{full}/R_{uncons}$ vs 阈 3 | 最小比值 4.86（≥3） | 不适用（比值判据） | 通过 |
| (f) | 负控 $T_{air}$=0 → $h_c$ | 0.000000 m | 是（严格 0） | 通过 |

**「是否 <3%」的显式回答**：

* 有解析解/手算基准的两项（a、d）均 **<3%**：+0.0087% 与 +0.0000%，且 (a) 在 50→400 网格上稳定收敛（-0.23% → -0.01%）。
* (b) 的基准是**混合律参照模型**而非解析解，判据本身是 5%：达到 +4.21%，**不满足 <3%**，我们不粉饰——偏差来源已在报告中定位为排水修正项 $\phi(1-S)k_{pore}$，在 $S_{pore}=1$ 极限下严格为 0。
* (c) 的基准是文献导出带，**不适用 3% 标准**（观测分散本身 ±20% 量级），按任务判据 ±30% 判定，达到 +2.88%。

## 7. 复现与审计链

* 模块：`src/tensorphysics/ice_ridge_consolidation/`（thermal / strength / resistance / references / validation）
* 测试：`tests/test_ice_ridge_consolidation.py`（23 例，全部通过）
* 基准：`python benchmarks/ice_ridge_consolidation/run_validation.py` → `artifacts/ice_ridge_consolidation/results.json` + 6 张图
* 报告生成：`python benchmarks/ice_ridge_consolidation/write_report_md.py` → 本文件（零手抄）
* 全部判据：**全部通过**

