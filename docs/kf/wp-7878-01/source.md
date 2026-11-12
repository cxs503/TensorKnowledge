# P151-N05 完整干舷与吨位丈量验证链（ICLL 1966 + IMO Tonnage 1969）

> 生成方式：`python3 artifacts/p151n05/run_verification.py`（本文件所有数字由脚本从
> `artifacts/p151n05/*.json` 程序化注入，零手抄）。实验：`pytest -q
> tests/test_freeboard_tonnage_p151n05.py` → **47 passed**。

## ① 案例介绍（物理背景 / 几何 / 参数表）

干舷（freeboard）是稳性与航行安全的**第一道几何闸门**：干舷决定储备浮力、甲板开口
淹没角、吃水与载重线合法性。ICLL 1966 把"最小干舷"定义为一条**链**：表列干舷
f0(L, 船型) 经五项修正得到本船最小干舷；IMO Tonnage 1969 则把船体围蔽容积换算为
GT/NT，二者共同构成"稳性—丈量"验证面（台账键 STAB-FREEBOARD）。

典型干舷链（ICLL 1966 附则 I 第 I 部分）：

```
f0(L, type)  --Reg30-->  +ΔCb(Cb>0.68)  --Reg32-->  −Δss(E/L)  --Reg31-->  +ΔD(D vs L/15)
             --Reg38-->  +Δsheer(舷弧欠缺/超量)  =  assign 最小干舷
```

本节点验证的 5 条船型几何（3 个公开 benchmark 船型取自
`backend/data/standard_models_detailed.py`，2 个参数化参考船型覆盖 L=120 m 网格
切换点与 90 m 小型船端）：

| 船型 | 类型 | ICLL 型 | L [m] | B [m] | T [m] | D [m] | Cb(申报) | Cb(排水量反算) | Cb 偏差 | f0 [mm] | 修正 ΔCb/Δss/ΔD/Δsheer [mm] | assign [m] | 实船型干舷 D−T [m] | 裕度 [m] | 首高 实/最小 [m] | GT* | NT* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KCS | container_ship | B | 230 | 32.2 | 10.80 | 19.00 | 0.6509 | 0.6346 | 2.50% | 3312 | 0/-509/917/0 | 3.720 | 8.20 | 4.480 | 10.37/6.96 OK | 27407 | 10105 |
| KVLCC2 | tanker | A | 320 | 58.0 | 20.80 | 30.00 | 0.8098 | 0.7900 | 2.44% | 4242 | 405/-869/2167/0 | 5.945 | 9.20 | 3.255 | 12.12/7.00 OK | 141167 | 77480 |
| JBC | bulk_carrier | B | 280 | 45.0 | 16.50 | 25.00 | 0.8580 | 0.8619 | 0.45% | 4228 | 553/-649/1583/0 | 5.716 | 8.50 | 2.784 | 11.08/7.00 OK | 83415 | 41479 |
| PARAM-CARGO | general_cargo(reference) | B | 120 | 18.5 | 7.50 | 10.50 | 0.7200 | 0.7200 | 0.00% | 1476 | 43/-227/625/0 | 1.918 | 3.00 | 1.082 | 4.25/5.11 DEFICIT | 4775 | 2900 |
| PARAM-COASTER | coaster(reference) | B | 90 | 14.0 | 5.20 | 7.20 | 0.7000 | 0.6998 | 0.02% | 1033 | 15/-159/225/0 | 1.114 | 2.00 | 0.886 | 3.00/4.13 DEFICIT | 1753 | 1042 |

\* GT/NT 由参数化围蔽容积 V=Cb·L·B·D（V 的下界，**不含**上层建筑/甲板室容积）代入
Reg 3/4 得到，仅作链机制演示，绝对量级为下界估计（见 ⑤ 局限）。

## ② 怎么做的（方法 / 流程 / 工具链）

1. **表列干舷**：`tabular_freeboard_mm(L, type)` 在合并结点序列上分段线性插值
   （L≤120 m 用 0.5 m 步长、L>120 m 用 1 m 步长，切换点 L=120 m 共用同一结点），
   域 [24, 425] m 外**不外推**（ICLL 仅对 L≥24 m 生效）→ 域外如实拒算。
2. **五项修正**：全部按 IMO 规定式实现（Reg 30 Cb 因子 `(Cb+0.68)/1.36`；Reg 31
   型深增量 `(D−L/15)·R`，`R=L/0.48`(L<120)/`250`(L≥120)；Reg 32 封闭上层建筑减除
   `f0·pct(E/L, type)` 双线性面；Reg 38 舷弧欠缺按 Simpson 3/8 半船积分均值 ×0.75；
   Reg 39 最小首高 `56L(1−L/500)`/7000 mm 分段）。
3. **可加性**：链内既算"逐步累加"也算 `math.fsum` 一次性求和，残差入账。
4. **几何前置门**：`Cb = Δ/(ρ·L·B·T)` 反算与申报值比较，超容差（默认 3%）拒算（422）；
   另拒 D<T、D<L/15、Cb∉[0.30, 0.92]。
5. **IMO Tonnage 1969**：`GT=K1·V`，`K1=0.2+0.02·log10V`；`NT=K2·Vc·(4d/3D)²+K3·(N1+N2/10)`，
   `K2=0.2+0.02·log10Vc`，`K3=1.25(GT+10000)/10000`，`(4d/3D)²≤1`，`NT≥0.30GT`。
6. **工具链**：`backend/api/freeboard_tonnage.py`（纯函数 + FastAPI 路由，已注册
   `/api/v1/freeboard-tonnage/*`）→ `tests/test_freeboard_tonnage_p151n05.py`（47 用例，
   含 8 个负控 + 2 个边界）→ `artifacts/p151n05/run_verification.py`（判据 JSON + 5 图 +
   台账写回 + 本报告）。

## ③ 计算结果（判据数字，全部程序化注入）

| 判据 | 阈值 | 实测 | 结论 |
|---|---|---|---|
| (a) 表列插值连续性 L=90/120/180/250 | <0.5% | 最大结点跳变 2.75e-04% | PASS |
| (b) 修正项可加性残差 | <1e-9 m | 标准舷弧 0.0e+00 m / 零舷弧 0.0e+00 m | PASS |
| (c) 单位口径 mm vs m | 1000× | 1000.000000 | PASS |
| (d) 舷弧三工况符号 | 0 / + / − | std 0.0e+00 m, zero 0.3752 m, excess -0.3752 m | PASS |
| (e) h_b(L) 单调不减（自相似族） | 单调 | 0.632 → 7.520 m（10 点） | PASS |
| (f) 分段点连续 | <0.1% | NT 下界切换 0.0e+00；R(L=120) 8.3e-09；首高(L=250) 1.3e-16；K1/K2 十倍阶跃 3.1e-09 | PASS |
| (g) 几何前置门 Cb 扰动 3.5% | 拒算 | GEOMETRY_GATE_CB_MISMATCH / 偏差 3.50% | PASS |
| (h) pytest | ≥22 全绿 | 47 passed（8 负控 + 2 边界） | PASS |

### (a) 结点连续性逐点

| L [m] | f0 [mm] | 左极限相对差 | 右极限相对差 | 跳变 | 阈值 |
|---|---|---|---|---|---|
| 90 | 1032.7 | 1.38e-06 | 1.38e-06 | 2.75e-06 | 0.5% |
| 120 | 1476.2 | 1.03e-06 | 1.04e-06 | 2.07e-06 | 0.5% |
| 180 | 2442.6 | 6.92e-07 | 6.92e-07 | 1.38e-06 | 0.5% |
| 250 | 3673.2 | 4.98e-07 | 4.95e-07 | 9.94e-07 | 0.5% |

### (d) 舷弧修正三工况（Reg 38）

| L [m] | 标准舷弧 [m] | 零舷弧 [m] | 双倍舷弧 [m] |
|---|---|---|---|
| 100.0 | 0.000e+00 | 0.2710 | -0.2710 |
| 150.0 | 0.000e+00 | 0.3752 | -0.3752 |
| 200.0 | 0.000e+00 | 0.4794 | -0.4794 |
| 250.0 | 0.000e+00 | 0.5836 | -0.5836 |
| 300.0 | 0.000e+00 | 0.6878 | -0.6878 |

## ④ 结果图

1. `docs/figures/p151n05/fig1_tabular_freeboard_continuity.png` —— f0(L) 双船型 + 四个
   判据结点（标注实测跳变），灰色区为 1 m 网格区段。
2. `docs/figures/p151n05/fig2_correction_chain.png` —— 干舷链各项修正随 L 的分解
   （自相似船型族），可见 Reg 31 率的分段点 L=120 m 无折角跳变。
3. `docs/figures/p151n05/fig3_tonnage_piecewise.png` —— GT=K1·V（右轴 K1）与 NT 的
   `0.30·GT` 下界切换（max 函数在切换点连续）。
4. `docs/figures/p151n05/fig4_five_hull_closure.png` —— 五船型 assign vs 实船型干舷
   并排对比 + Cb 闭合偏差对 3% 门的余量。
5. `docs/figures/p151n05/fig5_sheer_three_cases.png` —— 舷弧三工况 Δsheer(L) 符号分离。

（纯解析/几何任务，无场量云图：干舷与 GT/NT 均为代数规定式，不存在空间场；
上述曲线即"与解析解/基线比较曲线"本体。）

## ⑤ 注意点（坑 / 局限 / 适用范围）

1. **表值来源（最重要的诚实边界）**：`backend/data/icll1966_freeboard_table.json`
   的 `provenance.status = "SURROGATE"`。构建环境无外网，无法对 IMO 授权文本
   （表 28.1/28.2）逐点核对，故表列干舷由**代理曲线**生成（过 L=24 m→200 mm、
   L=425 m→7100 mm 两个公开记忆锚点；Type A = 0.85·Type B）。因此：
   **链机制 = REAL；绝对干舷 = WITHHELD**。换权威数字化数据只需替换该 JSON，代码零改动。
2. **战役简报的 GT 公式非规定式**：简报写 `GT=K1·V_total+K2·V_above+K3·N`，
   但 IMO Tonnage 1969 Reg 3 是**单项** `GT=K1·V`（旅客只进 NT 的 K3 项）。
   本实现按规定式执行，偏差如实登记（方法自主权：以规定文本为准）。
3. **舷弧修正的 0.75 比例因子**为文献转述值（规约给出积分方法，比例因子在
   二次文本间表述不一），已做成数据工件可调常数 `corrections.sheer.correction_factor`。
4. **Reg 32 减除面**为 cap·(2x−x²) 形式（凹、单调、E/L=1 上限 cap_A=0.32/cap_B=0.24），
   非授权表逐格数字化；结论只依赖其"单调 + E=0 为零 + 连续"三条结构性质。
5. **Reg 39 首高：2 个参考船型裸船型不足（诚实结果，未粉饰）**：`PARAM-CARGO、PARAM-COASTER` 的裸船型首高
   分别短 0.857 m（L=120 m） / 1.133 m（L=90 m）（隐藏的物理事实：真实小型货船/近海船都设首楼）。等价于补足首楼后
   Reg 39 判定全部通过（`bow_compliant_with_forecastle = True`），干舷链本身不变。
   3 个 benchmark 船型（KCS/KVLCC2/JBC）裸船型即满足。
6. **适用范围**：L∈[24, 425] m；D≥L/15；不含 Type B 减额条款（B-60/B-100 等强度
   减额）、不含甲板货/木材干舷（Table 28.3 起）、不含破舱稳性与进水点；GT 用参数化
   容积估计（下界），未含上层建筑与甲板室容积。
7. **几何闭合 2.5% 残差**来自数据库内 `displacement`（可能含附体/Lwl 口径）与
   `Cb·L·B·T` 定义差异，非本链误差：KCS 2.50%、KVLCC2 2.44%、JBC 0.45%。

## ⑥ 误差判定（逐项回答"是否 <3%"）

| 关键量 | 基准 | 误差 | <3%? |
|---|---|---|---|
| 表列插值结点跳变 L=90/120/180/250 | 结点表值 | 2.75e-04% | 是 |
| 修正项可加性残差 | 一次性 fsum | 0.0e+00 m（相对 ~1e-16） | 是 |
| 单位口径 mm/m | 严格 1000× | 0.0e+00 | 是 |
| 分段点连续（R、首高、NT 下界、K1/K2） | 分段闭式 | ≤8.33e-07% | 是 |
| 五船型 Cb 几何闭合 | 申报 Cb | 最大 2.50% | 是 |
| Reg 31/39 分段自洽（120/0.48=250；56·250·0.5=7000） | 算术恒等 | 0（精确） | 是 |
| Reg 39 首高（裸船型） | 规定式最小值 | 3/5 满足；2 个参考船型短 0.857 m（L=120 m） / 1.133 m（L=90 m） m（补首楼后全通过） | 见注（结构合规，非数值精度） |
| **绝对干舷 vs ICLL 授权表值** | 无可用基准 | **无法判定**：环境无外网、无授权数字化表 | **否（WITHHELD，原因如上，不粉饰）** |
| **GT/NT 绝对值 vs 实船吨位** | 无基准（容积为下界估计） | 不可比（V_total 缺上层建筑容积） | 否（WITHHELD） |

## 审计链

- 代码：`backend/api/freeboard_tonnage.py`（纯函数 + 路由）、
  `backend/data/icll1966_freeboard_table.json`（数据工件，含 provenance）、
  `tools/gen_icll1966_surrogate_table.py`（表值生成器，可复现）。
- 用例：`tests/test_freeboard_tonnage_p151n05.py`（47 passed：规定式闭式 12、连续性 8、
  可加性/单位 4、负控 8、边界 2、五船型闭合 1、端点 API 1、其余结构性质）。
- 判据 JSON：`artifacts/p151n05/acceptance.json`、`five_hull_closure.json`、`tonnage.json`。
- 台账：`artifacts/ledger/STAB-FREEBOARD.jsonl`（键 STAB-FREEBOARD，含判据逐条 pass 与 figure 路径）。
- 图：docs/figures/p151n05/fig1_tabular_freeboard_continuity.png, docs/figures/p151n05/fig2_correction_chain.png, docs/figures/p151n05/fig3_tonnage_piecewise.png, docs/figures/p151n05/fig4_five_hull_closure.png, docs/figures/p151n05/fig5_sheer_three_cases.png。
