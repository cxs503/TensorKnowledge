## ① 案例介绍

北极喀拉海—边缘冰区 PC6 冰级 45k DWT 散货船母型（L_pp=190 m, B=30 m, T=11.5 m, Cb=0.82, 主机 18 MW, 服务航速 13 kn, σ_f=500 kPa, B1 冰挤压设计力 8 MN/0.25 Hz, 年冰区占比 0.12, 20 年寿命）。任务是把五个独立开发的模型（A2 冰况同化预报 / C3 航速剖面 / D1 冰区航线 / E1 数字孪生 / B2 冰带疲劳）串成一条可验收的端到端链，并验证它们之间的单位制、坐标系与冰况参数传递契约。

几何先验门：由独立排水量（DWT/0.8167）反算 Cb=0.82007 vs 声明 0.82（相对差 8.5e-5），L/B=6.333、B/T=2.609 → 通过。

## ② 怎么做的

阶段全部调用上游模块本体（不重写物理），本战役只新增**契约层与验收层**：`contracts.py`（单位表/坐标系/保守重映射/方向探针）、`chain.py`（L1 案例单源注入 + 逐阶段 sha256 台账）、`assertions.py`（16 项门断言 + 7 项披露）、`assets.py`（跨库资产对账）、`figures.py`/`report.py`（图与报告程序化生成）。数据流：L1→A2→[保守重映射]→D1→C3→E1，B2 的 8 MN 与 C3 设计点喂给 E1，D1 航线冰厚分箱喂给 C3。一条命令：`cd backend && python -m modules.campaign_ice_nav.run_campaign`，墙钟 50.7 s。

## ③ 计算结果

门判据 **16/16 通过**（要求 ≥8）：
| ID | 断言 | 结果 |
|---|---|---|
| `G01-GEOM-CB` | L1 船型几何自洽 (Cb = ∇/(L·B·T), 2% 容差) | PASS |
| `G02-HULL-IDENTITY` | B2/C3/E1 与 L1 船型一致性（跨模型参数传递） | PASS |
| `G03-A2-CRIT` | A2 预报/同化判据（技能、质量守恒、观测阶梯单调） | PASS |
| `G04-UNIT-THICK` | 冰厚单位一致性（A2/D1/C3 同一米制，无 cm↔m 混用） | PASS |
| `G05-COORD-ORIENT` | 坐标系方向探针（j→北, i→东, 非转置/非翻转） | PASS |
| `G06-COORD-MASS` | A2→D1 保守重映射冰量守恒 | PASS |
| `G07-ICE-PROP` | 冰况参数贯穿：预报场 → 航线 → 航段（非空冰区） | PASS |
| `G08-RESIST-PARITY` | C1 引擎与 C3 的冰阻力一致性 + 阻力分解闭合 | PASS |
| `G09-FORCE-CHAIN` | 力单位链 MN→N→kN 与闭环回算一致性 | PASS |
| `G10-SPEED-CHAIN` | 航速单位链 kn↔m/s 与孪生回算一致性（设计点） | PASS |
| `G11-FATIGUE-MECHANICS` | B2 Miner 累积与 S-N 交叉校核的机制自洽性（算术 + 双口径） | PASS |
| `G12-ROUTE-LEGAL` | D1 航线合法性与独立复算长度 | PASS |
| `G13-HASH-LEDGER` | 全链工件 sha256 台账可复算 | PASS |
| `G14-API-CONTRACT` | 五个模块 API 端点契约（前缀无冲突、路径齐备） | PASS |
| `G15-DETERMINISM` | 关键阶段数值可复现（C3 剖面两次重算同哈希） | PASS |
| `G16-UPSTREAM-REPRO` | 同输入复现上游工件（A2/B2/D1 基准场） | PASS |

- A2：72 h 技能（vs 持续性）0.505，同化 RMSE 0.1145 m（冰图 0.1444 m），质量误差 0.0e+00，航窗可作业 10/12 lead。
- A2→D1：冰量守恒 2.6e-14，方向探针 5.3e-05，覆盖 20.4%。
- D1：主航线 684.1 nm / 54.5 h，no-go 0 nm，独立 haversine 复算差 0.000%。
- C3：总航程 684.1 nm / 63.3 h / 203388 kWh；冰区占比 27.0%，设计点 4.50 kn, R_ice 464.7 kN。
- E1：闭环误差 F 5.43% / u 3.01% / R_ice 3.82% / GM 0.09%。
- B2：控制细节 `plate_panel_MPa`，20 年利用率 67.58（不通过）；纵桁 1.68e-05。

## ④ 结果图

（4 张图见 figures 字段：契约重映射 / 航速剖面 / 疲劳 S-N 与利用率 / Uikku 实冰锚）

## ⑤ 注意点与局限

1. A2 是 identical-twin OSSE：真值由同一前向模型自洽生成，技能分数不构成对真实冰图预报精度的承诺（无独立观测源）。
2. E1 是闭环回放：真值注入 = C3 设计点工况，误差反映滤波器与单位链，不是对实船数据的验证。
3. B2 载荷谱为 B1 冰挤压谱（F=8 MN, f=0.25 Hz）；A2 最不利 lead 冰厚与 8 MN 设计力之间的对应关系来自 PC6 母型工程约定，不是由规则公式反推。
4. MT Uikku 锚点使用平台既有代理几何（真船主尺度不在本仓库），不能作为物理验证，且 C1 链系数曾对同族参考值标定。
5. D1 与 C3 两套冰中航速模型在同一 (h,C) 下显著分歧（见 D05），本门不改任何模型系数，只登记分歧（GAP-INT-07）。
6. B2 板格细节 20 年 Miner 利用率远超 1 → 结构结论不通过（D06）；上游工件只报纵桁 pass。
7. A2 窗口仅覆盖 D1 域的 20.4%，窗口外为气候态填充（已在 assumed_fields 声明）。
8. plan-12 外部仓库（TensorFEM/TensorDEM/TensorPhysics）若未挂载，对账项自动降级为 WITHHELD，不默认通过。
9. 总链墙钟约 41.5 s（单核 CPU，无 GPU）。

踩坑：A2 双周期直角网格→D1 经纬网若用双线性插值会丢 3.65% 冰量（首版实测），必须面积加权单元平均；A2 无温度/雪深/陆海掩膜字段，只能气候态填充并登记 `assumed_fields`；A2 与 C3 共用 `/api/v1/ship/ice` 前缀，真正的风险是操作路径撞车（用 AST 解析 `include_router` 做 (method,path) 去重）；直接 import main 会拉进 psycopg2 依赖；C3 载荷结构缺 D1 需要的 `table{v_kn,p_kw}` → 功率上限通道静默回落。

## ⑥ 误差判定（显式回答是否 <3%）

| 误差项 | 实测 | 基准 | 是否 <3% |
|---|---|---|---|
| Cb 几何反算 vs 声明值 | 0.0085% | 解析几何 | 是 |
| A2 复现上游工件（同配置） | 0.0000% | artifacts/ice_da_forecast_a2/metrics.json | 是 |
| B2 复现上游工件（同输入） | 0.0000% | artifacts/fatigue_pc6.json | 是 |
| D1 基准场 vs 上游工件 | ≤1e-9 绝对 | artifacts/ice_route_opt/summary.json | 是 |
| A2→D1 冰量守恒 | 2.6e-14 | 面积加权守恒（解析恒等） | 是 |
| A2→D1 方向探针 | 5.3e-05 | 解析 m/deg 斜率 | 是 |
| E1 冰载荷闭环 | 5.43% | 注入真值（闭环） | 否 |
| E1 航速闭环 | 3.01% | 注入真值（闭环） | 否 |
| E1 冰阻力闭环 | 3.82% | 注入真值（闭环） | 否 |
| C1 MT Uikku 链 vs Hu&Zhou 2016（MAPE） | 36.23% | 实冰实验锚（代理几何、系数已标定） | 否 |
| B2 板格系数 vs 简支板理论 β | 75.8% | Navier 级数 0.2874 | 否 |
| TensorFEM Mindlin Q4 vs 闭式 Mindlin | 0.211% | tensorfem.plate 闭式解 | 是 |
| D1 vs C3 冰中航速（独立实现） | 65.6% | 两套生产模型互比 | 否 |

## 结论与 honest FAIL

一致性门 16/16 通过、一条命令端到端跑通、JSON/报告/7 图齐全。**但有 4 项披露项如实不通过，不覆盖：**
- `D01-UIKKU-ANCHOR`：C1 MT Uikku 链 vs Hu&Zhou(2016) 十工况实冰锚 — 判据 预登记筛选线 MAPE ≤ 25%（TensorDEM benchmark README 建议值）
- `D02-PLATE-MINDLIN`：B2 板格系数 vs 板理论 / TensorFEM Q4 Mindlin — 判据 B2 系数与简支板理论 β=0.2874 相对差 ≤5%
- `D07-SPEED-MODEL-DIVERGENCE`：D1 (W3-N11 向量化链) 与 C3 (推力平衡求解器) 的冰中航速分歧 — 判据 两套独立冰中航速模型的相对差 ≤15%
- `D06-STRUCTURAL-VERDICT`：B2 结构校核结论（逐细节如实披露，含不通过项） — 判据 三个结构细节 20 年利用率均 ≤1

其中影响最实质的两条：(a) B2 板格 20 年 Miner 利用率 67.6（上游只报纵桁 pass；即便按简支 β 修正仍为 12.4，即降载/加厚板/提高 S-N 等级是必需工作，不是文档错误）；(b) C1 MT Uikku 链在独立十工况锚上 MAPE 36.2%，薄冰段 55.5% —— 与论文自述的薄冰弹性屈曲机理一致，登记为下一轮物理改进项（GAP-INT-05）。另有 D1↔C3 冰中航速 40–66% 分歧（航线时间 54.4 h vs 剖面 68.2 h）登记为 GAP-INT-07，需上游指定唯一真源。

工件：`artifacts/campaign_ice_nav/campaign_acceptance.json`（含全链 sha256 清单）、`docs/campaign/ice_nav_campaign_report.md`、`artifacts/campaign_ice_nav/figures/*.png`；pytest `backend/tests/test_campaign_ice_nav.py` 13 passed；上游四套测试（ICE_DA 69、route 14、speed_profile 14、ice_belt 19）仍全绿。