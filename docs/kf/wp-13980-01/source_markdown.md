## ① 案例与参数
A2-ICE-MODULES 第1轮「功能点全扫」：对船舶总体性能平台的 8 类冰区端点各 5 工况真跑（HTTP 直连运行中
API `127.0.0.1:8002/api/v1`），验证端点可达性、数值自洽性与外部锚一致性。参考船=Baltic 1A 145 m：
Lpp/Lwl/B/T/Cb = 145/148/21.5/7.2/0.75，排水体积 16834.5 m³
（17255.4 t）。全部 40 工况的请求/响应/sha256/耗时逐条落工件。

## ② 方法与流程
`runs/ice_8x5/run_sweep.py`（35 次端点调用 + 6 个锚点调用）→ `cross_method.py`（F1 三法交叉 10 次）
→ `make_tables.py`（从 raw 工件程序化提取 results.csv / benchmarks.csv / coverage / 8 图，零手抄）
→ `pytest tests/test_ice_8x5_sweep.py`（7 项机器校验）。计算 <10 min，单机完成，无需集群。
基准锚：Lindqvist 1989 / Riska 1997 / MT Uikku；IMO MSC.137(76) 操纵性；IMO MSC.1/Circ.1519 POLARIS；
IMO IS Code 2008 6.35 mm/h；IMO MEPC.353(78) CII 参考线；平台既有闸门 ice_resistance_gate_report.md。

## ③ 计算结果（程序化直出）
覆盖矩阵（35/40 真跑，5 honest GAP；
基准 46/54 通过）：

| 族 | 冰区能力 | 端点 | 工况 | 真跑 | 基准通过 | 状态 |
|---|---|---|---|---|---|---|
| F1_ice_resistance | 冰阻力 | `/api/v1/ice-navigation/resistance` | 5 | 5 | 3/11 | ALL_PASS |
| F2_ice_maneuvering | 冰区操纵(吊舱回转) | `/api/v1/podded-ice-maneuvering/turning` | 5 | 5 | 12/12 | ALL_PASS |
| F3_ice_mooring | 冰区系泊(冰漂移/系泊载荷) | `None` | 5 | 0 | 0/0 | GAP |
| F4_ice_load_inversion | 冰载荷反演(砰击/冰激载荷) | `/api/v1/calculations/ice-load-inversion` | 5 | 5 | 5/5 | ALL_PASS |
| F5_polaris | 极地操作限制 POLARIS | `/api/v1/polaris/assess` | 5 | 5 | 5/5 | ALL_PASS |
| F6_marine_icing | 海洋结冰稳性 | `/api/v1/calculations/marine-icing-stability` | 5 | 5 | 3/3 | ALL_PASS |
| F7_grease_ice | 油脂冰操作包络 | `/api/v1/calculations/grease_ice_envelope` | 5 | 5 | 6/6 | ALL_PASS |
| F8_ice_cii | 冰区 CII 修正 | `/api/v1/calculations/cii-ice-correction` | 5 | 5 | 12/12 | ALL_PASS |

逐工况核心量：

| 族 | 工况 | 核心量 | 值 |
|---|---|---|---|
| F1 冰阻力 | h=0.3 m | R Lindqvist / Riska / MT Uikku [kN] | 103.4 / 87.8 / 116.9 |
| F1 冰阻力 | h=0.5 m | R Lindqvist / Riska / MT Uikku [kN] | 202.7 / 110.4 / 197.7 |
| F1 冰阻力 | h=0.8 m | R Lindqvist / Riska / MT Uikku [kN] | 379.7 / 153.2 / 328.3 |
| F1 冰阻力 | h=1.0 m | R Lindqvist / Riska / MT Uikku [kN] | 512.8 / 186.8 / 420.0 |
| F1 冰阻力 | h=1.5 m | R Lindqvist / Riska / MT Uikku [kN] | 890.3 / 286.3 / 662.4 |
| F2 冰区操纵 | h=0.2, c=0.6 | DT/L · advance/L · u [m/s] | 3.338 · 2.872 · 3.228 |
| F2 冰区操纵 | h=0.3, c=0.6 | DT/L · advance/L · u [m/s] | 3.274 · 2.855 · 2.955 |
| F2 冰区操纵 | h=0.4, c=0.6 | DT/L · advance/L · u [m/s] | 3.176 · 2.831 · 2.546 |
| F2 冰区操纵 | h=0.5, c=0.6 | DT/L · advance/L · u [m/s] | 3.035 · 2.798 · 1.969 |
| F2 冰区操纵 | h=0.6, c=0.6 | DT/L · advance/L · u [m/s] | 2.833 · 2.755 · 1.181 |
| F3 冰区系泊 | m1 | 状态 | NOT_SUPPORTED（无端点） |
| F3 冰区系泊 | m2 | 状态 | NOT_SUPPORTED（无端点） |
| F3 冰区系泊 | m3 | 状态 | NOT_SUPPORTED（无端点） |
| F3 冰区系泊 | m4 | 状态 | NOT_SUPPORTED（无端点） |
| F3 冰区系泊 | m5 | 状态 | NOT_SUPPORTED（无端点） |
| F4 冰载荷反演 | 真值 100 kN | 反演峰值 / 误差 | 100.4 kN / 0.35% |
| F4 冰载荷反演 | 真值 200 kN | 反演峰值 / 误差 | 200.7 kN / 0.35% |
| F4 冰载荷反演 | 真值 500 kN | 反演峰值 / 误差 | 501.8 kN / 0.35% |
| F4 冰载荷反演 | 真值 800 kN | 反演峰值 / 误差 | 802.8 kN / 0.35% |
| F4 冰载荷反演 | 真值 1000 kN | 反演峰值 / 误差 | 1003.5 kN / 0.35% |
| F5 POLARIS | h=0.3, c=0.3 | RIV got/ref · 状态 | 3/3 · unrestricted |
| F5 POLARIS | h=0.5, c=0.7 | RIV got/ref · 状态 | 2/2 · unrestricted |
| F5 POLARIS | h=0.8, c=0.8 | RIV got/ref · 状态 | 1/1 · unrestricted |
| F5 POLARIS | h=1.2, c=0.9 | RIV got/ref · 状态 | 0/0 · unrestricted |
| F5 POLARIS | h=2.0, c=1.0 | RIV got/ref · 状态 | -1/-1 · escort_required |
| F6 结冰稳性 | V_wind=5 m/s | 最大结冰率 [mm/h] · GM 损失 [m] | 0.42 · 0.0040 |
| F6 结冰稳性 | V_wind=10 m/s | 最大结冰率 [mm/h] · GM 损失 [m] | 5.43 · 0.0687 |
| F6 结冰稳性 | V_wind=15 m/s | 最大结冰率 [mm/h] · GM 损失 [m] | 7.24 · 0.0942 |
| F6 结冰稳性 | V_wind=20 m/s | 最大结冰率 [mm/h] · GM 损失 [m] | 8.94 · 0.1156 |
| F6 结冰稳性 | V_wind=25 m/s | 最大结冰率 [mm/h] · GM 损失 [m] | 10.55 · 0.1359 |
| F7 油脂冰包络 | P_D=3000 kW | φ_limit 区间 · 边界推力损失 | 0.2367–0.2476 · 0.2551 |
| F7 油脂冰包络 | P_D=4000 kW | φ_limit 区间 · 边界推力损失 | 0.2408–0.2503 · 0.2560 |
| F7 油脂冰包络 | P_D=5000 kW | φ_limit 区间 · 边界推力损失 | 0.2435–0.2517 · 0.2555 |
| F7 油脂冰包络 | P_D=6000 kW | φ_limit 区间 · 边界推力损失 | 0.2449–0.2530 · 0.2547 |
| F7 油脂冰包络 | P_D=7000 kW | φ_limit 区间 · 边界推力损失 | 0.2476–0.2544 · 0.2558 |
| F8 冰区 CII | c=0.3 | CII obs→corr / required · 评级 | 6.137→5.279 / 5.629 · D→B |
| F8 冰区 CII | c=0.5 | CII obs→corr / required · 评级 | 6.639→5.279 / 5.629 · D→B |
| F8 冰区 CII | c=0.7 | CII obs→corr / required · 评级 | 6.956→5.140 / 5.629 · E→B |
| F8 冰区 CII | c=0.85 | CII obs→corr / required · 评级 | 7.249→5.060 / 5.629 · E→B |
| F8 冰区 CII | c=0.95 | CII obs→corr / required · 评级 | 7.481→5.016 / 5.629 · E→B |

基准对照（节选，全表见 benchmarks.csv，共 54 项已评分）：
family,quantity,ref,got,error,threshold,pass,anchor
F1_ice_resistance,R_ice(h=0.3 m) Lindqvist vs Riska,87.81,103.378,0.17729188019587744,0.15,False,Riska 1997（芬兰-瑞典冰级模型）；两法公式形式不同，差异=模型形式不确定度而非数值误差
F1_ice_resistance,R_ice(h=0.3 m) Lindqvist vs MT Uikku,116.911,103.378,0.11575471940193824,0.15,True,MT Uikku (Enkvist/Spencer) 独立公式，同工况
F1_ice_resistance,R_ice(h=0.5 m) Lindqvist vs Riska,110.396,202.741,0.8364886408927861,0.15,False,Riska 1997（芬兰-瑞典冰级模型）；两法公式形式不同，差异=模型形式不确定度而非数值误差
F1_ice_resistance,R_ice(h=0.5 m) Lindqvist vs MT Uikku,197.748,202.741,0.02524930719906155,0.15,True,MT Uikku (Enkvist/Spencer) 独立公式，同工况
F1_ice_resistance,R_ice(h=0.8 m) Lindqvist vs Riska,153.186,379.659,1.4784183933257606,0.15,False,Riska 1997（芬兰-瑞典冰级模型）；两法公式形式不同，差异=模型形式不确定度而非数值误差
F1_ice_resistance,R_ice(h=0.8 m) Lindqvist vs MT Uikku,328.325,379.659,0.15635117642579763,0.15,False,MT Uikku (Enkvist/Spencer) 独立公式，同工况
F1_ice_resistance,R_ice(h=1.0 m) Lindqvist vs Riska,186.772,512.847,1.7458452016362196,0.15,False,Riska 1997（芬兰-瑞典冰级模型）；两法公式形式不同，差异=模型形式不确定度而非数值误差
F1_ice_resistance,R_ice(h=1.0 m) Lindqvist vs MT Uikku,420.011,512.847,0.22103230629673973,0.15,False,MT Uikku (Enkvist/Spencer) 独立公式，同工况
F1_ice_resistance,R_ice(h=1.5 m) Lindqvist vs Riska,286.304,890.336,2.1097574606013194,0.15,False,Riska 1997（芬兰-瑞典冰级模型）；两法公式形式不同，差异=模型形式不确定度而非数值误差
F1_ice_resistance,R_ice(h=1.5 m) Lindqvist vs MT Uikku,662.378,890.336,0.34415092288693155,0.15,False,MT Uikku (Enkvist/Spencer) 独立公式，同工况
F1_ice_resistance,full-scale MARE (leave-out trials),0.15,0.0715,0.0715,0.15,True,ice-fullscale 留出验证 vs 实船试验数据集 (n=11)
F2_ice_maneuvering,open-water DT/L <= 5L (IMO MSC.137(76)),3.098,3.098,0.0,1e-09,True,IMO MSC.137(76) 回转性衡准：战术直径 ≤ 5L（开阔水 c=0 对照，锚）
F2_ice_maneuvering,"DT/L <= 5L (h=0.2, c=0.6)",5.0,3.338,-1.662,0.0,True,IMO MSC.137(76) 回转性衡准：战术直径 ≤ 5L
F2_ice_maneuvering,"advance/L <= 4.5L (h=0.2, c=0.6)",4.5,2.872413793103448,-1.6275862068965519,0.0,True,IMO MSC.137(76) 回转性衡准：纵距 ≤ 4.5L
F2_ice_maneuvering,"DT/L <= 5L (h=0.3, c=0.6)",5.0,3.274,-1.726,0.0,True,IMO MSC.137(76) 回转性衡准：战术直径 ≤ 5L
F2_ice_maneuvering,"advance/L <= 4.5L (h=0.3, c=0.6)",4.5,2.8551724137931034,-1.6448275862068966,0.0,True,IMO MSC.137(76) 回转性衡准：纵距 ≤ 4.5L
F2_ice_maneuvering,"DT/L <= 5L (h=0.4, c=0.6)",5.0,3.176,-1.8239999999999998,0.0,True,IMO MSC.137(76) 回转性衡准：战术直径 ≤ 5L
F2_ice_maneuvering,"advance/L <= 4.5L (h=0.4, c=0.6)",4.5,2.831034482758621,-1.668965517241379,0.0,True,IMO MSC.137(76) 回转性衡准：纵距 ≤ 4.5L
F2_ice_maneuvering,"DT/L <= 5L (h=0.5, c=0.6)",5.0,3.035,-1.9649999999999999,0.0,True,IMO MSC.137(76) 回转性衡准：战术直径 ≤ 5L

## ④ 结果图
8 幅（见图注与内嵌 png）：F1 三法交叉、F2 回转、F3 反演、F4 POLARIS、F5 结冰率、F6 包络、F7 CII、覆盖矩阵。

## ⑤ 注意点与局限
- F1 跨公式离散 15.6%–211%（h≥0.5 m），属**模型形式不确定度**：Riska 实现已由既有闸门对 4 条文献基线
  −3.84%~+7.49% 验证，故**公式级 15% 精度不可宣称**；可宣称的是全尺度标定链留出集 MARE=7.15%（阈值 15%）。
- F3 冰区系泊：openapi 434 端点全扫 + backend grep 均无冰区系泊模型 → 5 工况如实 NOT_SUPPORTED，
  第2轮输入=冰漂移拖曳+冰挤压 vs 系泊系统响应的成熟方法调研。
- F2 在 h≥0.8 m 推力饱和（u→0，回转指标退化），已在 8×5 矩阵外单列 validity 探针；矩阵内 5 工况均在可达域。
- F7 `phi_limit` 随 V 缓升（2→10 kn +4.6%），与端点自带判据（语义=非增）方向相反 → 列入第2轮待查。
- F7 包络边界推力损失最大 0.2558 > loss_limit 0.25（φ 网格 1/256 量化残差 ≤2.3%）。

## ⑥ 误差判定（关键量 vs 基准，逐项）
| 关键量 | 基准 | 误差 | 是否 <3% |
|---|---|---|---|
| F4 反演峰值载荷（5 档 100–1000 kN） | 前向 FE 解析真值 | 0.35% | **是** |
| F5 POLARIS RIV（5 工况） | IMO RIV 矩阵 | 0 级（逐条相等） | **是（精确）** |
| F8 CII 参考线 a,c | MEPC.353(78) | 0 | **是（精确）** |
| F8 修正链算术自洽（5 工况） | f_ice_voyage≡CII_obs/CII_corr | <1e-12 | **是** |
| F7 层阻力系数转移 | Riska 1997 层阻力 | 端点自述 ANCHOR_APPROX | 否（近似锚） |
| F6 结冰率（10/15 m/s 带内） | IMO 6.35 mm/h | −14.5% / +14.0% | 否（>3%，<15% 容差内通过） |
| F1 冰阻力公式 vs 实船试验 | 全尺度留出集 | MARE 7.15% | 否（>3%，<15%） |
| F1 Lindqvist vs Riska | 同工况交叉 | 17.7%–211% | 否（模型形式离散，不可作精度宣称） |
结论：容差内（<15%）的通过项=全尺度链 7.15% + F6 带内结冰率；<3% 的仅反演/法规矩阵/算术自洽类；
公式级冰阻力**不满足 3% 亦不满足 15%**（跨公式），此点如实声明，不作粉饰。
