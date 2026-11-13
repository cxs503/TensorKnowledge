# 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09）

## ① 案例介绍

精确动刚度法（DSM）把等截面 Timoshenko 梁的模态误差压到只剩求根误差——插值误差结构性消失，从而给出任意阶（含 ≥3 节点）可信频率，供振动判级与 whipping/springing 当锚。

| 算例 | 用途 | 参数 |
|---|---|---|
| A 深梁 | 计数/有限元对拍 | 0.2×0.4 m、L=10 m（L/h=25）、E=2.06e11 Pa、ν=0.3、ρ=7850、κ=5/6 |
| A′ 细长梁 | Euler–Bernoulli 极限 | 1×1 mm、L=10 m（L/h=1e4） |
| C 深梁 | 剪切闭式对拍 | 0.4×1.0 m、L=5 m（L/h=5）简支，剪切使 1–5 阶相对 EB 降低 6.03%, 18.52%, 30.81%, 40.94%, 48.96% |
| B 船体梁（m6117） | 6.28 % 债务清算 | L=230 m、I=394.453 m⁴、A_s=1.52 m²、EI=8.1257e+13 N·m²、κGA=1.0036e+11 N、m=2.31873e+05 kg/m、C_W=0.5 |

## ② 怎么做的

- **精确单元**：λ 四次色散方程四个根构复指数基，精确能量泛函的 Gram 矩阵给 `K(ω)=H⁻ᵀQH⁻¹`，1 单元即精确；
- **Wittrick–Williams 计数**：`J(ω)=n·J₀+s{K}−刚体数−谱阈值伪零`，求根全程用 J 阶梯做括号（不漏根），括号内 Brent–Dekker 精化，接受前用 J(ω∓) 复核；
- **三个独立对拍面**：闭式（Hu–Timoshenko 简支 / Euler–Bernoulli 超越根）、位移有限元加密+Richardson、独立行列式根普查（区分零点与元素极点）；
- **本单在 dsbeam.py 修三处缺陷**：(1) 删 `scipy.optimize.brentq` 改纯 Python Brent–Dekker（判据要求只依赖 math+numpy.linalg）；(2) 惯性容差由 1e-12‖K‖ 改为 eigvalsh 向后误差界 + J≥0 钳位（原 `J(1e-6·f₁)=−2`）；(3) 元素固端极点处显式抛 ValueError 而非静默错计数；并新增两场模态振型 `mode_shape_full`（w, ψ, w′, ψ′）；
- **工具链**：numpy+math，审计脚本 `artifacts/m8404_dsm/audit_acceptance.py` 把所有数字程序化写入 `results.json`（零手抄），pytest 36 条全绿。

## ③ 计算结果（全部来自 results.json）

| 判据 | 数值 | 判据式 | 结论 |
|---|---|---|---|
| (a) 自由-自由 (βL)² 前3阶（L/h=1e4） | max rel = 2.065e-07 | ≤1e-6 | PASS |
| (b) 简支 Timoshenko L/h=5 前5阶 | max rel = 2.991e-13 | ≤1e-8 | PASS |
| (b′) 单元数不变性 1 vs 4 单元 | 0.0e+00 | — | 无离散误差 |
| (c) WW 计数 vs 独立根普查 0–10f₁ | 不一致 0 点；漏根 0；伪根 0 | 0/0 | PASS |
| (d) FEM n=160 + Richardson vs DSM（3/4/5 阶） | max rel = 1.169e-05（纯 n=160：1.18e-03） | ≤0.5% | PASS |
| (e) m6117 6.28 % 复现 | 6.2827 %（差 0.0027 个百分点） | ±0.2 | PASS |
| (f) 100 组随机样本 | 漏根 0 / 伪根 0 / 单调违背 0；最差闭式差 4.63e-13 | 0/0/0 | PASS |
| (g) scipy 禁用重算 + 单链耗时 | 差 0.0；0.462 s | <1 s | PASS |

### m6117 归因（算例 B）

- 精确 DSM(ρI=0，m6117 自身假设) 前4阶：1.15557, 2.65579, 4.29617, 5.91972 Hz
- m6117 交付：1.15589, 2.65952, 4.31160, 5.95924 Hz → 与其自身假设下精确解差 +0.027 %
- m6117 闭式锚点：1.087561 Hz → -5.886 %
- 精确 DSM(物理 ρI, A=29.538 m²)：1.15050, 2.64101, 4.27412, 5.89240 Hz；独立裁判 FEM 128 单元相对差 7.84e-04
- 6.28 % 归因恒等式闭合残差 0.0e+00
- 裁决：6.28 % reproduced (6.2827 %), and it closes algebraically to 0.0e+00: it is the difference of two biases, not an error estimate. (1) It is not discretisation error -- m6117's own mesh sequence 12/24/48/96/192 converges to 1.15558 Hz, not towards the anchor. (2) Under m6117's own assumption rho I = 0 the exact DSM gives 1.15557 Hz and m6117's 24-element model is +0.027 % away, so its element is sound. (3) The closed-form anchor is the biased number: -5.89 % against the exact shear-only solution, because a single-wave beta = 4.7300 shear correction over-corrects a free--free boundary. (4) The one parameter the m6117 record never states -- the section area that fixes rho I -- moves the physical dry first frequency between 1.0651 and 1.1526 Hz, so the rho I question stays WITHHELD.

## ④ 结果图

图1 两个极限下的精确 DSM 频谱；图2 自由-自由 1–3 阶两场精确振型（w/ψ/曲率）；图3 J(ω) 阶梯 vs 独立根普查（极点处阶梯不跳）；图4 m6117 归因；图5 100 组随机样本鲁棒性。

## ⑤ 注意点

1. **判据线可能因物理而非实现失败**：L/h=2000 的细长梁 3 阶仍有 5.16e-06 的 Timoshenko 剪切余项，大于本节点 1e-6 判据；判据 (a) 必须用 L/h≥5000（本单 1e4，实测 2.07e-07，已到双精度地板）。
2. **动刚度矩阵同时有零点与极点**：极点（单元固端频率）也让 det K 变号；朴素“变号=根”扫描把极点当根（随机样本中 6/100 例）。必须用括号内 |det| 塌陷量分类。
3. **惯性容差不能拍脑袋**：1e-12‖K‖ 会吞掉 ω²M 量级的刚体特征值，使 J 出现 −2；应用 eigvalsh 向后误差界并在定义层面保证 J≥0。
4. **m6117 的 ρI 口径是证据缺口（WITHHELD）**：记录未给截面面积 A，而 ρI=(m/A)I；A=1.52 m²→1.0651 Hz、A=29.538 m²→1.1505 Hz、ρI→0→1.1556 Hz，8.5 % 带宽内。
5. **与前序单 m7170 数字冲突（honest finding）**：其报的 1.22783/1.19143 Hz 无法由同组 EI/κGA/m 复现（ρI→0 的精确上界是 1.15557 Hz，剪切只降不升）；其定性结论（6.28 % 非离散误差、闭式锚点过修正）与本审计一致。
6. 适用范围：等截面、无轴力、平面弯曲；第二谱阈值处基函数退化需移位求值；ω 落在元素极点 1e-5 邻域内抛错。

## ⑥ 误差判定（是否 <3%）

| 关键量 | 基准 | 误差 | <3%? |
|---|---|---|---|
| 自由-自由 (βL)² 前3阶 | Euler–Bernoulli 常数 | 2.06e-07 | 是 |
| 简支前5阶 ω（含剪切） | Hu–Timoshenko 闭式 | 2.99e-13 | 是 |
| 自由-自由 3/4/5 阶 ω | FEM n=160+Richardson | 1.17e-05 | 是 |
| 100 组随机前5阶 ω | 简支闭式 | 4.63e-13 | 是 |
| m6117 交付（ρI=0 口径） | 精确 DSM(ρI=0) | +0.027% | 是 |
| m6117 交付（物理 ρI 口径） | 精确 DSM(物理) | 0.47%, 0.70%, 0.88%, 1.13% | 是 |
| **m6117 闭式锚点** | 精确 DSM(ρI=0) | **-5.89%** | **否（>3%，债务本体）** |
| 裁判 FEM 128 单元 | 精确 DSM | 7.84e-04 | 是 |

结论：DSM 自身对三个独立基准的误差 1e-13…1e-5 量级，全部 ≪3 %；m6117 的闭式锚点偏低 5.5–5.9 %，超过 3 %，且 6.28 % 恰为“FEM(+0.03 %) − 锚点(−5.89 %)”之差——债务归属明确落在闭式近似，而非有限元或网格。
