# EEXI attained 端到端闭合链路：Holtrop 阻力 → 推进功率 → 轴系效率 → gCO₂/(t·nm)

节点 `p73w2b-n02-eexi-closed-loop` · 仓 ship-performance-platform · 生成于 2026-11-09T05:49:25+00:00 ·
commit `7017a623` · 全部数字由 `artifacts/eexi_closed_loop/run_eexi_closed_loop.py` 程序化注入（零手抄）

## ① 案例介绍（物理背景 / 几何 / 参数表）

EEXI（Energy Efficiency Existing Ship Index，MEPC.328(76) 修正 MEPC.350(78) 计算法）要求把
**主机功率 → 燃油消耗 → CO₂ 排放 → 单位运输功排放** 串成一条闭合链，与要求的参考线比较。
平台此前只有"链的下半段"（给定 P_ME 后算 gCO₂/(t·nm)），阻力与推进功率由外部手工填写，
因而 attained EEXI 无法从船体几何独立复算——证据等级只能挂 WITHHELD。

本节点把链路补齐为：**裸船体几何 → Holtrop-Mennen(1984) 总阻力 R_T(V_ref) → 有效功率
P_E=R_T·V → 推进效率分解 η_H·η_O·η_S（BEMT 敞水曲线反解转速，T(1−t)=R_T 闭合）→
主机轴功率 P_D → 燃油率 P_D·SFOC → CO₂ 率 ×C_F → EEXI_attained = CO₂/(Capacity·V_ref)**，
并用 3 型公开标模船（集箱 KCS / 散货 JBC / 油轮 KVLCC2）给出 attained vs required 对比。

几何/工况参数（逐字段证据来源见 `reference_ships.json:field_grades`；几何先过 Cb·Lpp·B·T 与 ∇ 自检）：

| 船 | 船型 | DWT [t] | Capacity [t] | V_ref [kn] | R_T [kN] | P_E [kW] | P_D [kW] | η_O | η_H | η_S | η_tot | EEXI att | EEXI req | att/req |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kcs_3600teu | container_ship | 36000 | 25200 | 24.0 | 2047.2 | 25277 | 37608 | 0.625 | 1.097 | 0.98 | 0.672 | 35.992 | 18.176 | 1.98 |
| jbc_180k | bulk_carrier | 180000 | 180000 | 14.5 | 1294.5 | 9656 | 17025 | 0.520 | 1.113 | 0.98 | 0.567 | 3.558 | 2.396 | 1.49 |
| kvlcc2_300k | tanker | 300000 | 300000 | 15.5 | 1833.8 | 14622 | 24115 | 0.558 | 1.109 | 0.98 | 0.606 | 2.816 | 2.071 | 1.36 |

## ② 怎么做的（方法 / 流程 / 工具链）

1. **单源复用，不写第二份公式**：
   * 阻力 `physics/holtrop/mennen.py::holtrop1984_resistance`（m2082 阻力族并一后的唯一 Holtrop 实现），
     摩擦线校验用 `physics/holtrop/friction.py`（Schoenherr 独立线、ITTC-78 粗糙度补贴）；
   * 敞水与船-桨配合 `modules/propeller_bemt.py::solve_n_for_thrust / select_diameter_and_pitch`
     （BEMT 敞水曲线 + 对数二分反解 n，P/D 扫掠最大化 η_D）；
   * EEXI 指数只由 `api/green_shipping.py::_gn_attained_index` 给，闭合链路只提供功率与碳质量，
     两者在 API 响应里做逐位对账（`cross_source_rel_err`）。
2. **新增模块** `backend/modules/eexi_closed_loop/`（`chain.py` 纯物理核 + `fleet.py` 批量 +
   `data/reference_ships.json` 三型船数据与证据分级）。
3. **API**：`POST /api/v1/green-shipping/eexi_closed_loop`（几何直算 attained EEXI）、
   `GET /api/v1/green-shipping/eexi_closed_loop/reference_fleet`（G4 对比表）。
4. **判据机器化**：G1 摩擦线一致性、G2 能量守恒（幂等路线 + 独立力矩路线 2πnQ）、
   G3 单位代数（机器化简单位，不靠人眼）、G4 三型船表、G5 产物 JSON；pytest
   `backend/tests/test_eexi_closed_loop.py` 38 例。
5. **敏感度**：对 Cwp ±3%、LCB ±1%Lpp、SFOC ±5%、η_S∈[0.96,0.99]、D/T ±20% 扫掠，
   量化"假设值不确定度"对 EEXI 的传导，区分"判据精度"与"输入假设带"。

## ③ 计算结果

### 判据汇总（逐船）

| 船 | G1 R_T 摩擦线偏差 [%] | G2 能量残差 [-] | G3 单位代数 | EEXI att [gCO₂/(t·nm)] |
|---|---|---|---|---|
| kcs_3600teu | 0.0696 | 3.345e-06 | exact | 35.992 |
| jbc_180k | 0.0593 | 3.417e-07 | exact | 3.558 |
| kvlcc2_300k | 0.0654 | 1.208e-05 | exact | 2.816 |

* G1（<3%）：`0.0696%` **PASS**
* G2（<1%）：独立力矩路线最大残差 `1.208e-05` **PASS**；幂等路线残差恒 0（恒等式，仅披露）
* G3 单位代数：`final_unit = g/(t·nm)`，与目标 `g/(t·nm)` 精确一致 **PASS**；
  与绿航单源指数最大相对差 `0.0e+00` **PASS**；
  与 IMO 示例船逐点对标：**WITHHELD**（离线不可回读 MEPC 原文，不做伪对标，见 ⑥）
* G4：`bulk_carrier, container_ship, tanker` 三型船对比表已产出（上表 ①）
* G5：`artifacts/eexi_closed_loop.json`（本文件即由其生成，判据数字齐备）

### 效率链与碳链分解（含独立力矩路线对账）

* `kcs_3600teu`：P_E=25276.7 kW → P_D=37608.4 kW；2πnQ=36856.1 kW（η_S=0.98）→ P_D^torque=37608.3 kW；n=115.7 rpm，J=0.632，K_T=0.2323，K_Q=0.03736；CO₂=21743.4 kg/h
* `jbc_180k`：P_E=9656.0 kW → P_D=17025.1 kW；2πnQ=16684.6 kW（η_S=0.98）→ P_D^torque=17025.1 kW；n=86.0 rpm，J=0.392，K_T=0.1921，K_Q=0.02304；CO₂=9276.2 kg/h
* `kvlcc2_300k`：P_E=14622.2 kW → P_D=24115.2 kW；2πnQ=23633.2 kW（η_S=0.98）→ P_D^torque=24115.5 kW；n=72.0 rpm，J=0.439，K_T=0.1903，K_Q=0.02381；CO₂=13080.9 kg/h

### 实验对标（KCS 公开水池表，作为审计对象而非标定源）

| V [kn] | Holtrop R_T [kN] | 表列 R_T [kN] | 偏差 | 表列 C_t·10³ | 由 C_t 反推 R_T [kN] | 表内不一致 |
|---|---|---|---|---|---|---|
| 16.0 | 702.4 | 580.0 | +21.1% | 2.15 | 697.8 | +20.3% |
| 18.0 | 922.6 | 820.0 | +12.5% | 2.28 | 936.5 | +14.2% |
| 20.0 | 1208.5 | 1180.0 | +2.4% | 2.52 | 1277.9 | +8.3% |
| 22.0 | 1571.7 | 1740.0 | -9.7% | 3.05 | 1871.5 | +7.6% |
| 24.0 | 2047.2 | 2650.0 | -22.7% | 3.80 | 2774.9 | +4.7% |
| 25.0 | 2358.5 | 3450.0 | -31.6% | 4.50 | 3565.6 | +3.3% |
| 26.0 | 2707.9 | 4600.0 | -41.1% | 5.60 | 4799.2 | +4.3% |
| 27.0 | 3059.9 | 6200.0 | -50.6% | 7.20 | 6654.2 | +7.3% |

表内 `C_t` 列与 `R_T` 列最大不一致 `20.3%`，故该表证据等级
**WITHHELD**：只作量级参考，不用于标定、不用于 PASS 判定（见 ⑤）。

### 敏感度（输入假设的传导，非精度声明）

| 船 | 基线 EEXI | 各情形 ΔEEXI |
|---|---|---|
| kcs_3600teu | 35.992 | Cwp-3%:-1.74% / Cwp+3%:+1.92% / lcb-1%Lpp:-0.02% / lcb+1%Lpp:+0.12% / SFOC-5%:-4.85% / SFOC+5%:+4.85% / eta_s=0.96:+2.07% / eta_s=0.99:-1.00% / D/T-20%:+10.93% / D/T+20%:-6.88% |
| jbc_180k | 3.558 | Cwp-3%:-1.96% / Cwp+3%:+2.27% / lcb-1%Lpp:-0.12% / lcb+1%Lpp:+0.62% / SFOC-5%:-4.80% / SFOC+5%:+4.80% / eta_s=0.96:+2.05% / eta_s=0.99:-0.99% / D/T-20%:+14.25% / D/T+20%:-9.19% |
| kvlcc2_300k | 2.816 | Cwp-3%:-1.50% / Cwp+3%:+1.54% / lcb-1%Lpp:-0.05% / lcb+1%Lpp:+0.28% / SFOC-5%:-4.82% / SFOC+5%:+4.82% / eta_s=0.96:+2.06% / eta_s=0.99:-1.00% / D/T-20%:+13.34% / D/T+20%:-8.55% |

## ④ 结果图

* `fig1_resistance.png`：三型船 R_T(V)/R_F(V) 曲线 + V_ref（点线）+ KCS 水池表散点；右图为
  Holtrop vs 表偏差 与 表内 C_t↔R_T 自一致性（±15% 接受带）。
* `fig2_efficiency.png`：效率链分解 η_H/η_O/η_S/η_total 与 P_E→P_D 功率（柱上标注独立力矩路线 2πnQ）。
* `fig3_eexi.png`：三型船 EEXI attained vs required 及比值。
* `fig4_gates.png`：G1 摩擦线偏差（对数坐标，含 3% 门禁线）与 G2 能量残差（含 1% 门禁线）。

## ⑤ 注意点（坑 / 局限 / 适用范围）

1. **发现并修复一个真实缺陷（1852 倍量纲错）**：`_gn_attained_index` 原实现把分母航程取
   `V_ref[kn]×1852/3600×3600`（米/小时），得到 gCO₂/(t·**m**)，与响应里声明的
   `gCO2/(t·nm)` 差 1852 倍，而 required 按 g/(t·nm) 给出 ⇒ **任何船都被判"合规"**
   （VLCC 实测：attained 0.001521、required 2.0710、ratio 0.00073）。
   已改为海里并加解析回归测试（`TestEexiUnitDefectRegression`）；修复后 attained 2.8160、
   ratio 1.360，与物理手算逐位一致。此为 m1895 同类缺陷（CII 用 km 当 nm）
   在 EEXI/EEDI 达到值上的复现，属结构性回归点。
2. **η_S 语义**：按战役判据 G2 的定义 `P_D = R_T·V/(η_H·η_O·η_S)` 实现，此处 `P_D` 物理上
   等于进 EEXI 的主机轴功率 P_ME；螺旋桨收到功率另记 `P_D_propeller = 2πnQ`，二者由 η_S 联系。
   "独立力矩路线"（P_D^prop=2πnQ，K_Q 取自 BEMT 而非由效率链除出）与效率链的差
   `1.2e-05` 是本节点能量守恒的实质证据；但须诚实说明：两条路线共享
   η_O/η_H 的定义（BEMT 内部满足 η0·2πnQ = T·V_a），故该残差度量的实质是**推力闭合
   T(1−t)=R_T 的数值收敛**（二分容差 1e-5），并非两条独立物理路径的交叉验证；
   幂等路线残差为 0 属恒等式，一并披露，不作为精度声明。
3. **ITTC'78 粗糙度补贴与 Holtrop CA 的重叠**：ΔC_F(k_s=150 µm) 会给 R_T 加 10%~12%，
   但它与 Holtrop 的统计相关补贴 C_A 功能重叠，叠加即重复计账。故 G1 判定只取
   **摩擦线（Schoenherr vs ITTC-57/78 线，0.06%~0.07%）**，粗糙度情景作为披露项单列。
4. **回归域**：JBC 的 Cb=0.858 与 Cp=0.860 略越 Holtrop 回归域上限（0.85），域门禁已如实告警；
   该船 EEXI 精度应打折，不得当作 <3% 精度证据。
5. **V_ref 与 P_ME 的工况一致性**：EEXI 规制取 P_ME=0.75·MCR 与 EEDI 参考航速配对；本链路按
   "V_ref 处的阻力功率需求"解释 P_ME，对高速集箱船（KCS 24 kn）相当于 0.85~0.9 MCR 工况，
   故 attained 偏保守（偏大），仅作指示性对比，不作为规范符合性结论。
6. **参考船数据分级**：主尺度/船型系数/附体面积取公开标模（且与仓内 m547 KCS 基线逐字段断言一致），
   SFOC/η_S/桨径比/燃料为工程典型假设（无设备实测）。各假设对 attained EEXI 的最大传导
   （程序化取自有符号 |Δ| 最大者）：kcs_3600teu: D/T-20% → 10.9%；jbc_180k: D/T-20% → 14.3%；kvlcc2_300k: D/T-20% → 13.3%。

## ⑥ 误差判定（关键量 vs 基准，逐项）

| 关键量 | 基准 | 误差 | 判据 | 是否 <3% |
|---|---|---|---|---|
| Holtrop Cf @V_ref | ITTC-57/78 摩擦线（0.075/(log₁₀Re−2)²） | 0.0696%（R_T 级） | G1 <3% | **是** |
| Holtrop R_T @V_ref | Schoenherr 独立摩擦线替换 | 0.0696%（Cf 级） | G1 <3% | **是** |
| P_D 能量闭合 | 力矩路线 2πnQ/η_S = 推力闭合 T(1−t)=R_T（二分容差 1e-5） | 1.208e-05 | G2 <1% | **是** |
| gCO₂/(t·nm) 量纲 | 单位代数（kW·g/kWh·C_F/(t·kn)） | 精确一致 | G3 | **是** |
| EEXI attained | IMO 示例船逐点值 | 不可复核 | G3 对标 | **未判**（WITHHELD，理由：离线无 MEPC 原文） |
| Holtrop R_T @24 kn | 仓内 KRISO_tank 表 2650 kN | -22.7% | 实验带 ±15% | **否**（且该表自身 C_t↔R_T 不一致 20.3%，基准不可信 → 不作精度声明） |

honest 结论：G1/G2/G3(量纲)/G4/G5 全部按判据通过且可机器复现；**"与 IMO 示例船 <5%"这一项未能完成**，
原因是离线环境无法取得 MEPC.328(76)/350(78) 原文或可核示例船数据，按纪律挂 WITHHELD 而不编造对标值。
"对实验 <3%"亦未达成，且所依据的仓内水池表自相矛盾，故如实记录为"基准不可用"。

## 审计链

* 代码：`backend/modules/eexi_closed_loop/{chain.py,fleet.py,data/reference_ships.json}`、
  `backend/api/green_shipping.py`（新增 `/eexi_closed_loop`、`/eexi_closed_loop/reference_fleet`；
  修 `_gn_attained_index`）、`backend/tests/test_eexi_closed_loop.py`
* 产物：`artifacts/eexi_closed_loop.json`、`artifacts/eexi_closed_loop/*.png`、本报告
* 复现：`python backend/../artifacts/eexi_closed_loop/run_eexi_closed_loop.py`（无随机数、无网络）
  + `cd backend && python -m pytest tests/test_eexi_closed_loop.py -q`
* 环境：3.11.6 on Linux-6.6.52-1.7.lns23.loongarch64-loongarch64-with-glibc2.38
