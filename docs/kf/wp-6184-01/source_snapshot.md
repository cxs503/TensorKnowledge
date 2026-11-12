## 1 案例
MARPOL 附则 VI 对现有船的两条约束：**EEXI**（设计侧，75% MCR 参考工况 → g CO2/(t·nm)）与 **CII**（营运侧，年油耗/年航程 + 逐年收紧 Z% → A–E 评级）。12 只代表船覆盖任务书 10 类（Handymax/Panamax/Capesize/MR/Aframax/VLCC/Feeder/Sub-Panamax/Panamax/Post-Panamax）+ LNG + 客船，主尺度/载重/装机/设计点全部写入 `fleet.py` 的 `provenance`。
## 2 怎么做的
`backend/modules/eexi_cii_compliance`：`regulatory`（参考线/削减率分档/适用门槛/Z%/dd，逐条带置信度）、`eexi`（达到值 MEPC.333(76)、要求值 MEPC.328(76)、EPL 反解 MEPC.335(76)）、`cii`（G1–G4 + Z% 法定/外推/未适用三态）、`fleet`（几何三关）、`route`（Holtrop 指数 + STAWAVE-1 增阻 + 风阻，功率锚点法）、`benchmarks`（文献区间，WITHHELD）。EEXI ∝ P_ME^(2/3)，所需限功率用二分法解，不用一次方近似。
## 3 结果
- 判据 **15/15 通过**（见 `artifacts/in28_i1/checks.json`）。
- 几何：12/12 过 Cb/L·B·T、DWT/Δ 包络、L/B·B/T 包络、高 Cb+高 Fn 组合检查。
- EEXI：适用 11/12（客船无参考线 → NOT_SUPPORTED），不装 EPL 达标 **2/11**；不达标船所需 EPL 5.5–34.2% 全部可行。例：82k 散货 attained 4.219 vs required 3.486（−21.0%，需 EPL 27.4%）。
| 船型 | EEXI | 要求 | 裕度% | AER | 2024 评级 |
|---|---|---|---|---|---|
| handymax_56 | 5.198 | 4.181 | -24.3 | 4.64 | C |
| panamax_82 | 4.219 | 3.486 | -21.0 | 3.70 | C |
| capesize_180 | 3.085 | 2.396 | -28.8 | 2.67 | D |
| mr2_50 | 5.325 | 4.965 | -7.2 | 5.04 | A |
| aframax_110 | 3.819 | 3.379 | -13.0 | 3.51 | A |
| vlcc_320 | 2.397 | 2.007 | -19.4 | 2.06 | C |
| feeder_1700teu | 16.417 | 20.161 | +18.6 | 10.95 | A |
| subpanamax_3500teu | 18.345 | 17.707 | -3.6 | 11.86 | D |
| panamax_4500teu | 17.632 | 17.015 | -3.6 | 11.07 | E |
| postpanamax_8500teu | 15.723 | 13.005 | -20.9 | 9.25 | E |
| lng_174k | 5.157 | 7.960 | +35.2 | 4.91 | A |

- CII：2023→2026 评级随 Z% 收紧单调下降（如 Post-Panamax 8500TEU：E→E，比值 1.35→1.44）；LNG（C_F=2.75）全程 A。
- 文献区间：AER 11/12 落在行业区间（区间锚点 WITHHELD）。

## 4 图
四联图内嵌（figures）：EEXI attained vs required｜CII 评级矩阵 2023–2027｜AER vs 文献区间｜Holtrop n_eff vs n=3。

## 5 注意点
系数层整体 WITHHELD（离线未回读决议原文）；箱船/气体船削减率分档置信度最低；STAWAVE-1 短波支路为线性桥接（低估短波）；营运画像（经济航速 0.86–0.93、年海上天数）是 AER 的主导输入；客船 EEXI 显式 NOT_SUPPORTED 不借邻类系数。

## 6 误差判定
| 量 | 基准 | 相对误差 | <3%？ |
|---|---|---|---|
| 达到 EEXI（11 船） | 独立闭式手算 | 0.0e+00 | **是** |
| 达到 CII（12 船） | 独立闭式手算 | 0.0e+00 | **是** |
| 要求 EEXI | 双实现互校 | 0.0e+00 | **是** |
| 要求 CII | 双实现互校 | 0.0e+00 | **是** |
| 年度 AER | 文献区间(±25–30%) | 11/12 落区间 | **否**（区间不构成精度） |
| 逐船 AER | GISIS/VeriFuel 点值 | **离线不可得** | **无法判定（WITHHELD 欠账）** |

## 7 发现项
1) `backend/api/green_shipping.py` 集装箱船 EEXI 削减率未按吨位分档（一律 20%），68,600 容量处要求值偏低 12.5%。2) 客船 CII 参考线 9309·GT^−0.383 给出 required≈115 g/(GT·nm)，比游轮实测高一个数量级 → 引擎量级闸门拦为 WITHHELD 并拒发评级。
