# P138W2-N09 · CII/EEXI 营运能效动态评级与碳强度漂移预警

**节点**：P138W2-N09（战役 DAG · 物理域）｜**任务号**：7260｜**仓**：ship-performance-platform｜**分支**：`agent/m7260`

**一句话结论**：新增 `backend/modules/operational_energy_efficiency/` 模块，把 「EEXI 法定合规 + 营运剖面 + 海况修正 + 年度 A–E 评级 + 年末预测/漂移预警」接成一条链；四道机器门全部通过（gate_1 3.791e-05、gate_2 1.462e-04、gate_3 4.411%、gate_4 覆盖率 0.845），但**实船油耗锚与船级社评级锚在沙箱内均 WITHHELD**，gate_3 只用 OSSE 模型形式包络替代，gate_4 只用「边界恒等 + 预测校准」替代——不冒充实船验证。

---

## 1 案例介绍（物理背景 / 几何 / 参数表）

CII（碳强度指标）把营运碳排折算成单位运输功：

    attained CII = Σ_j (FC_j · CF_j) / (Capacity · D)      [gCO₂/(dwt·nm)]
    required CII = a · Capacity^(−c) · (1 − Z(year))
    A–E 评级     = 与 dd₁..dd₄ × required 比较（MEPC.354(78)）

与 EEXI（设计口径、静水无风、V_ref 一点）不同，CII 是**全年营运口径**：同一条船在不同海况下的油耗差异可达百分之十几，直接用水尺油耗评级会把「今年风浪大」误判成「效率变差」。因此本节点的核心不是再算一遍法规算术，而是把**天气归因**与**效率漂移**分开，并对年末评级做带区间的预测。

算例母船（VLCC 量级，参数全部入档 `gate_results.json:ship`）：

| 参数 | 取值 | 说明 |
|---|---|---|
| 船型 / 容量 | tanker / 320000 dwt | CII 的 Capacity |
| L_pp / B / T | 320.0 / 58.0 / 20.8 m | 波浪/风阻几何 |
| V_ref / P_ref | 15.50 kn / 22000 kW | 设计点（EEXI 用） |
| SFC / η_D | 175 g/kWh / 0.70 | 能-碳链 |
| 辅机 | 1500 kW | 航行辅机负荷 |
| 燃料 | heavy_fuel_oil (CF=3.114) | MEPC.364(79) 默认值 |

OSSE 真值设置（演示年，`gate_results.json:demo_truth`）：波阻律 `bridged`、模型形式偏置 ×1.10、效率漂移 6.0%/yr、报表噪声 1.5%；真值全年 CII 观测 2.3448、静水口径 2.2086、平均天气功率增量 6.17%。

## 2 怎么做的（方法 / 流程 / 关键设置 / 工具链）

模块 `backend/modules/operational_energy_efficiency/`（新增，附 73 个 pytest 用例）：

| 文件 | 职责 | 证据等级 |
|---|---|---|
| `seastate.py` | 波浪增阻（复用 `api/added_resistance` 的 STAWAVE-1 单源核 + 短波桥接）、视风矢量风阻、浅水效应、集总功率增量份额 | REAL 力律 / DECLARED 系数 |
| `profile.py` | `P₀(V)=P_ref(V/V_ref)^n`、装载率、航线海况/浪向统计、航次油耗聚合、天气归一 | REAL |
| `eexi.py` | attained EEDI 法定链（MEPC.328(76) 形）+ 参考线 1−削减率 → 合规裁决 | attained REAL / required WITHHELD |
| `dynamic.py` | 逐月 CII（观测/归一）、漂移分解、1 谐波季节外推 + 蒙特卡洛年末预测、分级预警 | REAL + OSSE 校准 |
| `osse.py` | 与生产模型**函数形式不同**的真值生成器（波阻律/浪向指数/风系数/形式偏置） | 仿真真值 |
| `gates.py` | 四道门的机器可算实现（pytest 直接断言） | — |
| `api.py` | `POST /api/v1/operational-efficiency/{eexi-compliance,annual-rating}`、`GET /evidence` | — |

关键方法点：

1. **单源复用，零二次转录**：CII/dd/Z 全部委托 `modules.green_navigation_ice.mepc`；EEDI 参考线与 EEXI 削减率直接用 `api.green_shipping` 的唯一转录表；波浪增阻直接用 `api/added_resistance.stawave1` 与 `heading_factor`（m1940 已验收核）。本模块不复制任何系数——这是 gate_2「参考线与外部锚 <1%」能成立的前提。
2. **天气归一的口径声明**：同航速口径 `FC_norm = FC_obs/(1+f_sea)`，`f_sea = (R_aw + R_wind + R_shallow)/R_calm`，`R_calm = η_D·P₀/V`（常 η_D 近似，显式声明）。等功率（固定油门）口径的航速损失不在本链内，两种口径不混用。
3. **漂移分解**：`CII_obs` 与 `CII_norm` 各自对月份做最小二乘，`slope_obs = slope_eff + slope_weather`（一阶加减分解，声明为近似）。
4. **年末预测**：对 `CII_norm` 线性外推 + 对逐月天气因子做 1 谐波季节拟合（避免用年内均值抹掉季节相位），剩余月份运输功按已观测月均值或用户计划；蒙特卡洛含三项不确定性：残差乘性噪声、斜率标准误、天气归因模型形式项（±30% 相对，逐次抽样为整年系统项）。
5. **预警阈值在设计阶段固定**（未据结果回调）：`WARN_RED_P=0.5`、`WARN_AMBER_P=0.1`、`WARN_AMBER_RATIO=0.95`、`WARN_RED_RATIO=0.97`、`WARN_DRIFT_PCT=2.0`。

工具链：Python 3.11 + pytest + matplotlib（图件）+ 外部锚 JSON（跨仓只读）。
重计算（200 个 OSSE 年校准）单机 <15 s，未占用集群。

## 3 计算结果（数字表，程序化注入）

### 3.1 四道机器门

| 门 | 判据 | 实测 | 容差 | 结论 |
|---|---|---|---|---|
| gate_1 | CII 与 MEPC.353(78) 式(1) 一致性 | 3.791e-05 | <1e-3 (0.1%) | PASS |
| gate_2 | EEXI attained / 参考线 vs 外部锚 | 1.462e-04 | <1e-2 (1%) | PASS |
| gate_3 | 海况修正后燃油 vs 真值（OSSE 最差档） | 4.411% | <10% | PASS |
| gate_4 | 评级边界恒等 + 预测校准 | 覆盖率 0.845 / 命中 0.855 | 覆盖率∈[0.65,0.95]、命中≥0.80 | PASS |

外部锚（另一仓工件，只读）：`GATE_GREEN_M1850`，路径 `backend/tests/data/acceptance_gate_m1850.json`，其自身容差 0.02。四个算例逐项偏差：

| 算例 | 船型 | 容量 | attained 偏差 | 参考线偏差 | required 偏差 |
|---|---|---|---|---|---|
| KVLCC2_tanker | tanker | 300000 | 1.964e-05 | 8.007e-05 | 8.007e-05 |
| Capesize_bulk | bulk_carrier | 180000 | 3.303e-05 | 1.462e-04 | 1.462e-04 |
| PostPanamax_container | container_ship | 140000 | 1.352e-05 | 1.914e-05 | 1.914e-05 |
| Handysize_bulk | bulk_carrier | 35000 | 3.791e-05 | 4.133e-05 | 4.133e-05 |

### 3.2 演示年：动态评级与提前预警

| 量 | 数值 | 来源 |
|---|---|---|
| required CII（2026，Z=11%） | 2.0472 | `gate_results.json:annual_rating_full_year` |
| 参考线（2019 基线） | 2.3002 | 同上 |
| A/B·B/C·C/D·D/E 边界 | 1.761 · 1.924 · 2.170 · 2.416 | 同上（dd=[0.86, 0.94, 1.06, 1.18]） |
| 全年观测 CII | 2.3390 → 评级 D | 同上 |
| 全年天气归一 CII | 2.1843 → 评级 D | 同上 |
| 天气超额（观测/归一−1） | 7.08% | 同上 |
| 6 月末年末预测（点） | 2.3200（真值 2.3448，误差 1.06%） | `gate_results.json:midyear_forecast` |
| 80% 预测区间 | [2.2832, 2.3553]（覆盖真值：是） | 同上 |
| 评级概率 | A:0.000、B:0.000、C:0.000、D:0.999、E:0.001｜点预测 D | 同上 |
| 预警级别（6 月末） | **RED**：P(CII>required)=1.00 >= 0.5；ratio=1.133 >= 0.97 且效率漂移 +2.80%/yr | 同上 |
| 漂移分解 | 观测 +4.09%/yr = 效率 +4.99%/yr + 天气 -0.56%/yr | `gate_results.json:drift` |

逐月明细见 `artifacts/op_cii_n09/monthly_series.csv`（12 行，首月 f_sea=0.102211、末月 f_sea=0.094388）。

### 3.3 预测校准（200 个 OSSE 年，前 6 月观测）

| 量 | 数值 | 名义/判据 |
|---|---|---|
| 80% PI 覆盖率（gate_4 配置） | 0.845 | 名义 0.80 |
| 评级命中率（gate_4 配置） | 0.855 | ≥0.80 |
| 点预测平均相对误差（gate_4 配置） | 1.95% | — |
| 80% PI 覆盖率（演示年配置） | 0.910 | 名义 0.80 |
| 评级命中率（演示年配置） | 0.975 | — |
| 点预测平均相对误差（演示年配置） | 1.07% | — |

## 4 结果图

| 图 | 内容 | 文件 |
|---|---|---|
| 图 1 | 年末 CII 预测校准：真值 vs 预测（±80% PI），200 个仿真年 | `fig1_calibration.png` |
| 图 2 | 四道门实测偏差 vs 判据容差（对数轴）+ gate_4 覆盖率 | `fig2_gate_deviation.png` |
| 图 3 | 年度 CII 轨迹（观测/天气归一）叠加 A–E 评级边界与 6 月末年末预测 | `fig3_annual_rating.png` |
| 图 4 | 海况修正逐月功率增量 f_sea + 碳强度漂移分解 | `fig4_weather_decomposition.png` |

（场量云图不适用：本节点是规则算术 + 量-碳链评估，无数值场求解；图件给的是校准/轨迹/分解曲线，均程序化生成，无手抄。）

## 5 注意点（踩过的坑 / 局限 / 适用范围）

1. **OSSE 真值里的浪向律符号写错（自查发现，已修）**：`TruthModel.heading_factor` 初版把「与顶浪夹角」算成 180°，导致真值波浪增阻被压到 1e-61 N，gate_3 一度近乎“轻松通过”，却完全没检验波阻支路。修正后 gate_3 最差档从 2.75% 变为 4.411%（真值天气份额从 4.4% 升到 5.4–12.6%）。教训：OSSE 的真值侧必须与生产侧做**同点对拍**（同一 (Hs,Tp,浪向) 输入下两侧分项应可解释）。
2. **短波域解析核系统性偏低（已登记局限）**：短波桥接核的 Bft6 顶浪波浪增阻份额 2.77% 落在经验量级带 [5%,25%] 之外（未桥接原值 8.86%）；大船短波域需 STAWAVE-2 或模型试验表，本仓无该表 → 回归为已登记局限。
3. **浅水效应是 DECLARED 未标定形式**（`c·(T/h)²/(1−Fr_h²)`，Fr_h≥0.85 冻结并置 critical），只作量级提示，**不参与任何判据**；要用于裁决必须先有标定数据。
4. **天气归因的常数 η_D 近似**：`R_calm = η_D P₀/V` 忽略了附加阻力带来的 η_D 变化（ISO 15016 常 η_D 口径）。若做等功率口径的航速损失预测，需要另一条链，不能复用本链数字。
5. **预报的天气假设**：剩余月份天气用「已观测月份的 1 谐波季节拟合」外推；跨年或异常年（如厄尔尼诺）会偏，且 PI 只覆盖 ±30% 的天气归因模型形式不确定度。
6. **规则系数的证据等级**：参考线 a/c、Z 因子、dd 向量都是决议文本转录（离线不可回读原文），因此 required/compliance 侧继承 WITHHELD；attained 侧才是 REAL。合规结论只能用于工程筛查，不能替代法定验证。
7. **实船锚缺失**：沙箱内没有 noon report / 船级社评级记录，gate_3/gate_4 的「与实船一致」「与船级社评级一致」按 WITHHELD 登记，用 OSSE 包络与预测校准替代——这不是实船验证，报告与返回值都带着这个标签。

## 6 误差判定（关键量 vs 基准，逐项回答「是否 <3%」）

| 关键量 | 基准 | 误差 | <3%？ |
|---|---|---|---|
| attained CII（公式一致性） | 外部锚 GATE_GREEN_M1850 四个算例 | 3.791e-05 | **是** |
| EEXI 参考线 / required / attained | 同上 | 1.462e-04 | **是** |
| gate_3 归一燃油（最差 OSSE 档） | OSSE 真值（形式不同） | 4.411% | **否**（>3%，但满足本节点 10% 判据） |
| 年末 CII 点预测（200 年均值） | OSSE 真值 | 1.95% | **是** |
| 年末 CII 点预测（演示年） | OSSE 真值 | 1.06% | **是** |
| 漂移斜率恢复（合成序列） | 解析设定值 | <1e-6（pytest 断言） | **是** |
| 逐月聚合 vs 年度集总 CII | MEPC.353(78) 式(1) | 1.710e-16 | **是** |

**显式结论**：与**外部锚**（跨仓工件）比对的两个法规量误差量级 1e-4~1e-5（<3%）；与 **OSSE 仿真真值**比对的海况修正燃油误差 4.411%（>3%，<10%）；**实船油耗与船级社评级无法比对（WITHHELD）**，故此两项不出具「<3%」结论。

## 7 复现与审计链

```bash
python3 -m pytest backend/modules/operational_energy_efficiency/tests/ -q   # 73 passed
python3 artifacts/op_cii_n09/run_n09.py      # 生成 gate_results.json + 2 个 CSV + 4 张图
python3 artifacts/op_cii_n09/make_report.py  # 生成本报告（数字来自上面的 JSON/CSV）
```

| 工件 | 内容 |
|---|---|
| `artifacts/op_cii_n09/gate_results.json` | 四道门判据数字、外部锚逐算例偏差、演示年评级/预测/预警、局限登记 |
| `artifacts/op_cii_n09/monthly_series.csv` | 逐月 CII 金标（观测/归一/评级/f_sea） |
| `artifacts/op_cii_n09/forecast_calibration.csv` | 200 个 OSSE 年的预测-真值-PI 明细 |
| `artifacts/op_cii_n09/fig1..fig4*.png` | 校准 / 门偏差 / 年度轨迹 / 天气-漂移分解 |
| `backend/modules/operational_energy_efficiency/tests/` | 73 个 pytest 用例（含四道门回归） |

## 8 与既有能力的关系（不与已验证案例重复）

* `modules/green_navigation_ice/mepc.py`（W5-N08）已实现 CII 法规算术与冰区 f_ice 修正——本节点**复用**它，不重写；新增的是**营运剖面驱动的动态评级 + 天气归一 + 年末预测/预警**。
* `api/green_shipping.py` 的 `/cii` 端点明确把 A–E 评级标为 NOT_SUPPORTED——本节点用 `mepc.rate` 把评级补齐，并给出评级概率与边界恒等回归，但 required 侧证据等级仍继承 WITHHELD，不改变上游的诚实标签。
* `api/added_resistance.py`（m1940 STAWAVE-1）作为波浪增阻单源核被复用；本节点新增的是「增阻 → 功率增量 → 燃油 → CII」的营运链与不确定性预算。
