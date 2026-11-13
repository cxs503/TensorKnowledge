# EEXI attained 闭合链路：Holtrop 阻力 → 推进功率 → 轴系效率 → gCO₂/(t·nm)

节点 `p73w3-n02-eexi-maturity` · 任务 `m10589` · 仓 ship-performance-platform ·
生成时 HEAD `7017a6235`（提交后可能落后一代）· 生成于 2026-11-10T18:30:44+00:00 ·
**本文件由 `artifacts/eexi_closed_loop/run_eexi_closed_loop.py` 从 `artifacts/eexi_closed_loop.json`
程序化生成，表内所有数字零手抄。**

---

## ① 案例介绍（物理背景 / 几何 / 参数表）

EEXI（MEPC.328(76)，修正 MEPC.350(78) 计算法）要求把 **主机功率 → 燃油消耗 → CO₂ 排放 →
单位运输功排放** 串成闭合链。平台此前只覆盖链的下半段：给定主机功率后算 gCO₂/(t·nm)，
而 R_T 与 P_D 由人工填写，因而 attained EEXI 无法由船体几何独立复算，证据等级只能挂 WITHHELD。

本节点把上半段补齐：**几何 → Holtrop-Mennen(1984) 裸船体总阻力 → 有效功率 →
推进效率分解（η_H, η_O, η_S）→ 主机交付功率 → 燃油/CO₂ 质量流 → EEXI attained**，
并用三型公开标模船（集装箱 KCS / 散货 JBC / 油轮 KVLCC1）做端到端精度传递。

几何与工况（逐字段出处见 `artifacts/eexi_closed_loop.json` 的 `ships[*].provenance`；
几何先过 Cb·L·B·T 与 ∇ 自洽闸门，JBC 的库值 ∇ 与 Cb·L·B·T 差 2.96% 已按定义式校正并登记）：

| 船 | 船型 | Lpp [m] | Cb | V_ref [kn] | Fn | R_T [kN] | P_E [kW] | P_D [kW] | η_H | η_O | η_D | rpm | ṁ_CO₂ [kg/h] | EEXI att | 参考线 | required | att/req |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kcs_3600teu | container_ship | 230.0 | 0.6509 | 24.0 | 0.2600 | 1999.8 | 24691 | 34795 | 1.0966 | 0.6473 | 0.7096 | 95.5 | 19483 | 32.215 | 22.720 | 18.176 | 1.772 |
| jbc_180k | bulk_carrier | 280.0 | 0.8580 | 14.5 | 0.1424 | 1321.3 | 9856 | 17977 | 1.1127 | 0.5028 | 0.5483 | 82.1 | 10066 | 3.857 | 2.994 | 2.396 | 1.610 |
| kvlcc1_300k | tanker | 320.0 | 0.8098 | 15.5 | 0.1423 | 1892.7 | 15092 | 24956 | 1.1085 | 0.5512 | 0.6047 | 71.8 | 13974 | 3.005 | 2.589 | 2.071 | 1.451 |

## ② 怎么做的（方法 / 流程 / 工具链）

链路（每段**单一来源**，不写第二份公式）：

```
R_T(V) = R_F(1+k_1) + R_W + R_B + R_TR + R_A + R_APP        ← physics.holtrop.mennen
P_E    = R_T · V
η_H    = (1-t)/(1-w)     （Taylor；与 modules.propeller_bemt 同源）
η_O    ← modules.propeller_bemt.solve_n_for_thrust（BEMT 敞水，T(1-t)=R_T 闭合反解 n）
P_D    = P_E / (η_H·η_O·η_R·η_S)
ṁ_CO₂  = P_D · SFOC · C_F                                   ← C_F 由 api.green_shipping 化学计量
EEXI   = ṁ_CO₂ / (Capacity · V_ref)     [gCO₂/(t·nm)]
```

判据机器化：

* **L1 恒等/守恒**：阻力分项求和 = R_T（相对误差 0）；推力闭合 T(1-t)=R_T（≤1.6e-5）；
  效率链 η_D=η_H·η_O·η_R·η_S；双路线对账（效率路线 vs 2πnQ/η_S÷η_R，残差 ≤1.6e-5）；
  EEXI 单位代数与 IMO 公式路径逐位一致（rel_err = 0）。
* **L2 参考数据审计闸门**（关键：先审计再判精度）：R1 波阻系数 >0、R4 C_W ≤
  max(3×Holtrop C_W, 0.8e-3)、R5 功率列自洽（P_D×公开 QPC 反演的 R_T 也过闸门）、
  R2/R3 两列联合反演 QPC 是否落在物理带并与公开 QPC 一致。**未过闸门的参考点不参与任何精度判定**，
  只作为数据质量问题登记（见 ③ 审计表）。
* **L3 误差预算**：各段独立相对误差 → RSS（ε=√Σε_i²）。实测优先（有审计通过的参考即取实测），
  无实测的段用文献/工程带宽并标注 `method_band` + `WITHHELD`，绝不把估计说成实测。
* **缺陷回归**：`api.green_shipping._gn_attained_index` 的 1852 倍单位缺陷（V_ref 误转 m/s×3600，
  商为 g/(t·m)）已修复，`unit_conformance()` 与 `tests/test_eexi_closed_loop.py` 双侧锁定。

## ③ 计算结果

### 3.1 链路逐段（程序化注入）

| 船 | 船型 | Lpp [m] | Cb | V_ref [kn] | Fn | R_T [kN] | P_E [kW] | P_D [kW] | η_H | η_O | η_D | rpm | ṁ_CO₂ [kg/h] | EEXI att | 参考线 | required | att/req |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kcs_3600teu | container_ship | 230.0 | 0.6509 | 24.0 | 0.2600 | 1999.8 | 24691 | 34795 | 1.0966 | 0.6473 | 0.7096 | 95.5 | 19483 | 32.215 | 22.720 | 18.176 | 1.772 |
| jbc_180k | bulk_carrier | 280.0 | 0.8580 | 14.5 | 0.1424 | 1321.3 | 9856 | 17977 | 1.1127 | 0.5028 | 0.5483 | 82.1 | 10066 | 3.857 | 2.994 | 2.396 | 1.610 |
| kvlcc1_300k | tanker | 320.0 | 0.8098 | 15.5 | 0.1423 | 1892.7 | 15092 | 24956 | 1.1085 | 0.5512 | 0.6047 | 71.8 | 13974 | 3.005 | 2.589 | 2.071 | 1.451 |

### 3.2 参考数据审计（谁有资格当"试验值"）

| 船 | V [kn] | R_T 参考 [kN] | P_D 参考 [kW] | C_W(阻力列) | C_W(功率列反演) | 反演 QPC | R1 波阻>0 | R4 量级 | R5 功率列 |
|---|---|---|---|---|---|---|---|---|---|
| kcs_3600teu | 20.0 | 980.0 | 12500.0 | 9.342e-05 | -2.250e-05 | 0.807 | True | True | False |
| kcs_3600teu | 22.0 | 1350.0 | 18500.0 | 3.894e-04 | 2.074e-04 | 0.826 | True | True | True |
| kcs_3600teu | 24.0 | 1850.0 | 27000.0 | 7.517e-04 | 4.847e-04 | 0.846 | True | True | True |
| kcs_3600teu | 26.0 | 2520.0 | 40000.0 | 1.189e-03 | 8.896e-04 | 0.843 | True | True | True |
| jbc_180k | 14.5 | 3800.0 | 18000.0 | 4.787e-03 | — | 1.575 | True | False | None |
| kvlcc1_300k | 12.0 | 1800.0 | 12000.0 | 1.359e-03 | 3.357e-04 | 0.926 | True | False | True |
| kvlcc1_300k | 14.0 | 2500.0 | 18000.0 | 1.464e-03 | 2.370e-04 | 1.000 | True | False | True |
| kvlcc1_300k | 15.5 | 3200.0 | 25000.0 | 1.641e-03 | 3.127e-04 | 1.021 | True | False | True |
| kvlcc1_300k | 17.0 | 4200.0 | 35000.0 | 1.994e-03 | 4.751e-04 | 1.049 | True | False | True |

审计要点：

* **KCS**：阻力列 4 点中 3 点通过 R1+R4（20 kn 点 C_W=9.34e-05 过闸门但功率列反演 C_W<0 ⇒ R5 False）；
  设计点 24 kn 的 C_W=7.52e-04 与其自航功率列反演值 4.85e-04 同量级 ⇒ 阻力/功率两列**可判**。
  但该点反演 QPC=0.846 比公开 QPC 0.76 高 11.3% ⇒ (b) 的分辨率被参考数据自身噪声吃掉。
* **KVLCC1**：阻力列 C_W=1.36e-03…1.99e-03（Fn=0.13~0.15 的 VLCC 实际波阻系数应在 0.2e-03 量级）
  ⇒ R4 全部不过；而自航功率列 × 公开 QPC=0.65 反演出的 R_T 过闸门 ⇒ **R5 把可疑列定位到阻力列**，
  该船阻力参考降级为 DERIVED（反演值），(b) 反而可判。
* **JBC**：阻力列 C_W=4.79e-03（比合理值高一个量级）、两列联合反演 QPC=1.575（>1，物理不可能），
  且该船无公开 QPC 锚点 ⇒ 阻力/功率双列全部 WITHHELD，**不参与判据**。

### 3.3 误差预算（逐段独立测量 + RSS）

| 船 | 逐段相对误差 | 总 RSS |
|---|---|---|
| kcs_3600teu | resistance=8.10%(measured)<br>hull_efficiency=0.63%(measured)<br>open_water=4.80%(measured)<br>shaft=1.00%(method_band)<br>sfoc=3.00%(method_band)<br>carbon_factor=0.10%(measured) | **9.95%** |
| jbc_180k | resistance=5.00%(method_band)<br>hull_efficiency=2.00%(method_band)<br>open_water=3.00%(method_band)<br>shaft=1.00%(method_band)<br>sfoc=3.00%(method_band)<br>carbon_factor=0.10%(measured) | **6.93%** |
| kvlcc1_300k | resistance=7.13%(measured)<br>hull_efficiency=9.93%(measured)<br>open_water=0.21%(measured)<br>shaft=1.00%(method_band)<br>sfoc=3.00%(method_band)<br>carbon_factor=0.10%(measured) | **12.63%** |

### 3.4 判据裁决表

| 船 | (a) 阻力 vs 参考 <5% | (b) P_D vs 试航 <8% | (c) IMO 公式一致性 <5% | (d) 总误差 RSS <5% |
|---|---|---|---|---|
| kcs_3600teu | +8.10% / FAIL | +28.87% / FAIL | 0.00e+00% / PASS | +9.95% / FAIL |
| jbc_180k | —（WITHHELD） / WITHHELD | —（WITHHELD） / WITHHELD | 0.00e+00% / PASS | +6.93% / FAIL |
| kvlcc1_300k | -7.13% / FAIL | -0.18% / PASS | 0.00e+00% / PASS | +12.63% / FAIL |

聚合：`{"a": {"per_ship": {"kcs_3600teu": "FAIL", "jbc_180k": "WITHHELD", "kvlcc1_300k": "FAIL"}, "all_pass": false, "any_fail": true}, "b": {"per_ship": {"kcs_3600teu": "FAIL", "jbc_180k": "WITHHELD", "kvlcc1_300k": "PASS"}, "all_pass": false, "any_fail": true}, "c": {"per_ship": {"kcs_3600teu": "PASS", "jbc_180k": "PASS", "kvlcc1_300k": "PASS"}, "all_pass": true, "any_fail": false}, "d": {"per_ship": {"kcs_3600teu": "FAIL", "jbc_180k": "FAIL", "kvlcc1_300k": "FAIL"}, "all_pass": false, "any_fail": true}}`

## ④ 图

1. `artifacts/eexi_closed_loop/figs/fig1_resistance_breakdown.png` — 三型船 R_T(V) 分项堆叠 +
   参考点审计标记（空心圆=过审计、红叉=未过审计不入判据）。
2. `artifacts/eexi_closed_loop/figs/fig2_efficiency_chain.png` — 推进效率分解 η_H/η_O/η_D 与公开 QPC、
   公开 w/t 推出的 η_H（黑短线）。
3. `artifacts/eexi_closed_loop/figs/fig3_error_budget.png` — 逐段误差 + RSS 总误差 + 5% 目标线。
4. `artifacts/eexi_closed_loop/figs/fig4_eexi_levels.png` — EEXI attained/参考线/要求值 +
   单位代数回归闸门（1852 倍缺陷对照）。

## ⑤ 注意点（踩过的坑 / 局限 / 适用范围）

* Holtrop-Mennen 为统计回归方法：其自身精度带（≈±5%，域外更大）构成端到端天花板；本节点用实测参考点量化该天花板，而不是事后标定。
* 标模库参考列存在物理不一致（KVLCC1/JBC 的阻力列与自航功率列互相矛盾），审计闸门已把它们降级为 WITHHELD/DERIVED，结论不建立在不可靠参考上。
* BEMT 敞水效率与公开桨模效率仍有偏差（见 error_budget.open_water 的 signed_pct）。
* 容量与 SFOC 属工程假设（T4）：只影响 EEXI 绝对水平，不影响闭合精度。
* 规则侧系数（参考线/削减率）离线不可回读原文，证据等级 WITHHELD。

* **平台标模库参考列不是"试验值"，必须先审计**：KVLCC1 与 JBC 的 `total_resistance_kN` 与
  `delivered_power_kW` 两列互相矛盾（反演 QPC 1.02 / 1.575），若直接拿来当"试验值"会得出
  虚假的 -43% / -66% 阻力误差，或（更糟）用"参考值"反推标定系数把误差抹平。本节点把这条
  写成机器闸门，不靠自觉。
* **Holtrop 的适用域**：本链在 Fn≈0.26（集装箱设计点）的阻力误差 +8.1%，其中波阻系数
  Holtrop≈9.2e-04 vs 参考 7.5e-04（+22%），是方法在高速方尾/大球鼻船型上的已知弱势；
  肥大船（Fn≈0.14）阻力误差在 -7% 量级。
* **Taylor 伴流/减额经验式对肥大型船偏差大**：KVLCC1 的 η_H 用 Taylor 得 1.1085，
  公开 w=0.35/t=0.20 得 1.2308，偏差 -9.9% ⇒ 该段是肥大船的第二大误差源（见 3.3）。
* **容量与 SFOC 敏感度**见 JSON `sensitivity`（EEXI ∝ 1/Capacity ∝ SFOC 的一次齐次关系）。
* **规则侧系数**（EEDI/EEXI 参考线、削减率）离线不可回读原文，证据等级 WITHHELD；
  本节点不据此宣称合规性结论。

## ⑥ 误差判定（关键量 vs 基准，逐项显式回答"是否<5%"）

* **kcs_3600teu**：阻力 +8.10%（<5%？**否**）、交付功率 +28.87%（<8%？**否**）、IMO 公式一致性 0.00e+00%（<5%？**是**）、总误差 9.95%（<5%？**否**）。
* **jbc_180k**：阻力 —（<5%？**无法判定（参考不可用）**）、交付功率 —（<8%？**无法判定**）、IMO 公式一致性 0.00e+00%（<5%？**是**）、总误差 6.93%（<5%？**否**）。
* **kvlcc1_300k**：阻力 -7.13%（<5%？**否**）、交付功率 -0.18%（<8%？**是**）、IMO 公式一致性 0.00e+00%（<5%？**是**）、总误差 12.63%（<5%？**否**）。

* 判据 (c) 口径说明：IMO 公式路径一致性 = 8.0074 gCO₂/(t·nm)（修复后）
  与缺陷口径（×1852）对照，rel_err = 0 ⇒ **<5% 成立（精确一致）**。
  「attained vs 参考线 <5%」若按字面理解，则在任何合规船上都不可能成立：
  required = 参考线×(1−0.20)，attained/required 见 3.1 表（1.45~1.77），
  该命题属**设计余量**而非精度，故本节点单列为诊断量，不冒充精度判据。
**(b) 判据的偏差分解（把单一数字拆成"阻力段 vs 效率段"）**

* **kcs_3600teu**：P_D 链=34795 kW vs 参考=27000 kW；本链 η_D=0.7096，参考口径 η_D=0.846 ⇒ 效率段差 -16.12%，阻力段差 +8.10%。
* **jbc_180k**：无可用试航功率参考 ⇒ (b) WITHHELD（不猜）。
* **kvlcc1_300k**：P_D 链=24956 kW vs 参考=25000 kW；本链 η_D=0.6047，参考口径 η_D=0.650 ⇒ 效率段差 -6.96%，阻力段差 -7.13%。

注意 KCS 的 (b) 偏差不能只归给本链：该船参考列自身反演 QPC=0.846 比其公开 QPC 0.76
高 11.3%，即参考数据内部已有 >10% 的矛盾，8% 的判据分辨率在该数据上不可达。

* **诚实结论**：链路实现与单位/恒等层面全部闭合（L1 全 PASS），但端到端**绝对精度 <5% 未达成**：
  (a) 集装箱 +8.10% FAIL、油轮 −7.13% FAIL、散货 WITHHELD；(b) 集装箱 +28.87% FAIL、
  油轮 −0.18% PASS、散货 WITHHELD；(d) 三船 9.95% / 6.93% / 12.63% 全 FAIL。
  误差预算的**下界由阻力段决定**（RSS ≥ ε_R），因此"Holtrop 输入下 EEXI 端到端 <5%"这一假设
  被本节点**否证**：要 <5% 必须把阻力段换成试验/CFD 输入（链已支持，
  `reference_input_mode` 给出该模式下的残差），或换用低 Fn 船型。
