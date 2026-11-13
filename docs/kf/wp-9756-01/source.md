# P78-N03 · 船舶 EEXI/CII 绿色合规机器判决门（成熟化）

**节点**：战役 DAG `P78-N03`（物理域 · 绿色航行）　**仓**：ship-performance-platform
**代码**：`backend/services/green_compliance.py`（判决核心）+
`backend/api/green_shipping.py`（端点薄壳 `/api/v1/green-shipping/{eexi_full,cii_rating,compliance_report,rating_boundaries}`）
**用例**：`backend/tests/test_green_compliance.py`（53 例，含 6 例端点）　
**产物**：`artifacts/p78n03_green_compliance/`（results.json + 4 图，png sha256 入 results.json）

---

## 1. 案例介绍（物理背景 / 几何 / 参数表）

EEXI（MEPC.335(76)）与 CII（MEPC.353(78)/MEPC.354(78)）是 MARPOL 附则 VI 第 4 章的两条
**营运合规线**：前者是"一次性设计发证"指标（gCO2/(t·nm)，对应参考航速下的功率-能效比），
后者是"逐年收紧"的营运碳强度指标（AER，gCO2/(t·nm)，配 A–E 评级与纠正行动计划义务）。
平台此前只提供达到值/要求值比值，**无 A–E 评级、无 EEXI 功率限制解、无年度报告装配**，
且迁移版 EEXI 达到值存在量纲缺陷（见 §5 D1）。

算例船 **KVLCC2**（MOERI/KRISO 公开油船，满载设计工况）：

| 量 | 值 | 出处/说明 |
|---|---|---|
| Lpp × B × T | 320 × 58 × 20.8 m | 公开船型主尺度 |
| Cb / ∇ | 0.8098 / 312,622 m³ | Cb·L·B·T |
| Δ | 320,438 t | ρ∇（ρ=1025 kg/m³） |
| DWT（Capacity） | 300,000 t | Δ − 空船 ~20 400 t（**声明**） |
| V_ref | 15.5 kn | Fn=0.142 @ Lpp=320 m（自洽） |
| R_T（Holtrop-1984 本平台链） | 2,047.3 kN | `api.holtrop1984` |
| P_E / η_D / 海况裕度 | 16,325 kW / 0.7 / 0.15 | P_D=23,321 kW（**声明**假定） |
| **P_ME（MCR）** | **26,819 kW** | =P_D×(1+0.15)，**声明输入** |
| P_AE | 920.5 kW | MEPC.335(76)：0.025·ΣMCR+250 |
| SFC_ME / SFC_AE | 175 / 215 g/kWh | 二冲程/辅机典型值（声明） |
| C_F (HFO) | 3.114 gCO2/gFuel | MEPC.364(79)（与化学计量派生互证 <3%） |
| 年营运假设 | 60,000 nm / 年；14,250 t HFO | 声明营运场景 |

## 2. 怎么做的（方法 / 流程 / 工具链）

1. **达到值（逐项）**：实现 MEPC.335(76) Annex 2 完整式

   `attained_EEXI = f_j·(f_i·P_ME·SFC_ME·C_F_ME + P_AE·SFC_AE·C_F_AE + P_PTI·SFC_ME·C_F_ME − f_eff·P_eff·SFC_ME·C_F_ME) / (f_i·f_c·f_l·Capacity·f_w·V_ref)`

   每个因子单独回传（`terms` / `denominator_t_nm` / `inputs`），可逐项审计；主/辅机燃料
   分别取 C_F（不得复用主机 C_F）。
2. **要求值**：`a·Capacity^(−c)·(1−RF)`，a/c 取 EEDI 参考线（MEPC.308(73) Table 2），
   RF 取 MEPC.328(76)；表值全部置于模块顶部常量，替换不改逻辑。
3. **CII 要求值**：复用 `services/cii_required_value.required_cii` 的**显式 regime**
   （2023–2026 确定值；2027+ 带 `z_extrapolated` 标记；<2023 抛 `InapplicableYearError`），
   不重复实现、不静默默认。
4. **A–E 评级**：G4 dd 向量左闭右开（E 右闭）分割，`x = attained/required`；
   船型/尺度带未登记即报错（不拿近似值冒充规则值）。
5. **处置结论**：A/B/C 合规；D 需改进且**连续三年 D** 触发纠正行动计划；E 单年即触发。
6. **功率限制解**：解 `attained(P_ME)=required` 的线性方程给 `P_limit`（ShaPoLi/EPL 路径），
   使合规路径可操作。
7. **年度报告装配**：航次表 → 逐燃料聚合油耗/CO2/航程 → AER → 评级 → 处置 → 字段完整性自检
   （32 个必填字段，逐字段取值，缺失即报缺）。
8. **验证工具链**：pytest（双实现对照）+ matplotlib（4 图）+ results.json（png sha256）。

## 3. 计算结果（数字表，程序化注入）

### 3.1 EEXI（KVLCC2，未限功率）

| 量 | 值 |
|---|---|
| ME 项 f_i·P_ME·SFC_ME·C_F | 14,615,015 gCO2/h |
| AE 项 P_AE·SFC_AE·C_F | 616,267 gCO2/h |
| 分子 Σ | 15,231,282 gCO2/h |
| 分母 Capacity·V_ref | 4,650,000 t·nm |
| **attained EEXI** | **3.2755** gCO2/(t·nm) |
| required EEXI（tanker, 20% 削减） | 2.0710 |
| ratio / margin | 1.5816 / -58.16 % |
| 判决 | **non_compliant** |
| 所需 P_limit | 16,541 kW = 61.7 % MCR |
| 限功率后 attained / 判决 | 2.0710 / compliant |

### 3.2 要求值三船型（C2）

| 船型 | Capacity (t) | a | c | 参考线 | RF | required | 独立复算误差 |
|---|---|---|---|---|---|---|---|
| bulk_carrier | 180,000 | 961.79 | 0.477 | 2.9944 | 0.20 | 2.3956 | 0.00e+00 % |
| tanker | 300,000 | 1218.80 | 0.488 | 2.5888 | 0.20 | 2.0710 | 0.00e+00 % |
| container_ship | 100,000 | 174.22 | 0.201 | 17.2226 | 0.20 | 13.7781 | 0.00e+00 % |

### 3.3 CII（2026 年，年营运 60,000 nm）

| 量 | 值 |
|---|---|
| 年 CO₂ | 44,415.9 t |
| AER = Σ(m·C_F)/(Capacity·Distance) | 2.4676 gCO2/(t·nm) |
| required CII（Z=0.11, determined） | 2.1294 |
| x = attained/required | 1.1588 |
| dd 向量（tanker） | {'dd1': 0.82, 'dd2': 0.93, 'dd3': 1.08, 'dd4': 1.28} |
| **评级** | **D**（需改进） |
| 纠正行动计划 | 不需要 |

### 3.4 评级随年份收紧（Z 折减）

| 年 | required CII | Z | x | 评级 | Z 外推 |
|---|---|---|---|---|---|
| 2023 | 2.2730 | 0.05 | 1.0856 | D | 否 |
| 2024 | 2.2251 | 0.07 | 1.1090 | D | 否 |
| 2025 | 2.1773 | 0.09 | 1.1333 | D | 否 |
| 2026 | 2.1294 | 0.11 | 1.1588 | D | 否 |
| 2027 | 2.1294 | 0.11 | 1.1588 | D | 是 |
| 2028 | 2.1294 | 0.11 | 1.1588 | D | 是 |
| 2029 | 2.1294 | 0.11 | 1.1588 | D | 是 |
| 2030 | 2.1294 | 0.11 | 1.1588 | D | 是 |

### 3.5 年度合规报告（KVLCC2-DEMO，2026）

| 字段 | 值 |
|---|---|
| schema / 生成时刻 | P78-N03/1.0 / 2026-01-15T00:00:00Z |
| EEXI attained / required / 判决 | 3.2755 / 2.0710 / non_compliant |
| CII AER / 评级 | 2.4676 / D |
| 年油耗 / 年航程 / 年 CO₂ / 航次数 | 14,250 t / 60,000 nm / 44,415.9 t / 3 |
| 总体状态 | non_compliant |
| 处置动作 | EEXI 未达标：需采取能效改进（降功率限制/节能装置/改烧低碳燃料）后重新发证 |
| 字段完整性 | 32/32 = 100.0%（complete=True） |

### 3.6 灵敏度（声明输入的传导）

| 场景 | SFC_ME | attained | ratio | P_limit (kW) |
|---|---|---|---|---|
| SFC_ME −10% | 157.5 | 2.9612 | 1.4298 | 18,379 |
| base | 175.0 | 3.2755 | 1.5816 | 16,541 |
| SFC_ME +10% | 192.5 | 3.5898 | 1.7334 | 15,037 |

## 4. 结果图

![fig1_eexi_vs_dwt.png](artifacts/p78n03_green_compliance/fig1_eexi_vs_dwt.png)
![fig2_cii_rating_bands.png](artifacts/p78n03_green_compliance/fig2_cii_rating_bands.png)
![fig3_power_limit.png](artifacts/p78n03_green_compliance/fig3_power_limit.png)
![fig4_grade_vs_year.png](artifacts/p78n03_green_compliance/fig4_grade_vs_year.png)

* **fig1**：三船型 required EEXI 随 Capacity 的幂律 vs KVLCC2 达到值（星）/要求值（空心圈）——直观显示未限功率的 VLCC 超标幅度。
* **fig2**：G4 dd 向量分级色带（三船型并列）+ KVLCC2 的 x 落点。
* **fig3**：attained EEXI 对 P_ME 的线性响应与 required 水平线的交点 = 功率限制解。
* **fig4**：固定营运场景下评级随年份（Z 收紧）的演化，2027+ 灰区=外推。

## 5. 注意点（踩过的坑 / 局限 / 适用范围）

**D1（缺陷修复）**：迁移版 `_gn_attained_index`（m2083）先 `V_kn→m/s` 再乘 3600，
分母成了 `t·m/h`，**达到值整体偏小 1852 倍**，导致 `/eexi` 与 `/eedi` 对任何船都判"合规"。
基线实测 ratio = 0.000540（=1/1852）。已修（分母用 `V_ref[kn]`，1 kn ≡ 1 nm/h），
回归用例 `TestD1AttainedIndexDimension` 在复原旧式时**红**、修复后**绿**。

**D2（缺陷修复）**：`api/green_shipping._gn_required_cii` 原实现对 year<2023 **静默取 z=0**
（规则未适用却给出"要求值"）、对 year≥2027 **静默沿用 0.11**（无外推标记）。已改为委托
`services/cii_required_value.required_cii` 的显式 regime：<2023 → `InapplicableYearError`（端点 422）、
≥2027 → 带 `z_extrapolated=True` 的显式外推。2023–2026 数值逐位不变（回归用例守卫）。

**局限（诚实边界）**
1. 参考线 / 削减率 / Z 表 / dd 向量均为**离线转录**（WITHHELD），未回读规则 PDF；
   dd 向量只登记了散货/油船/集装箱全尺度带 + 气体船 ≥65 000 t、LNG ≥100 000 t，
   其余尺度带**故意不登记**（KeyError 而非近似值）。整体合规结论的系数层不可离线复核。
2. KVLCC2 的 P_ME 由本平台 Holtrop 链 + 声明假定（η_D=0.70、海况裕度 15%）导出，
   非该船实测 MCR；§3.6 给出 SFC ±10% 的传导。C1/C5 判据检验的是**公式实现**
   （与手写展开式的双实现对照），不检验船舶功率本身。
3. CII 的 Capacity 取 DWT（油船规则口径），未处理 GT 口径船型（客船/滚装）；
   f_w 未接入耐波增阻（取 1.0，适用于平静水 V_ref）；未做 EEDI 的 f_c/f_l 舱容修正船型分支。
4. 未接 DCS 实测数据、未做多船队画像；连续年 D/E 判定要求调用方提供历史等级（不臆造历史）。

## 6. 误差判定（逐项 vs 基准）

| 判据 | 内容 | 结果 | 是否达标 |
|---|---|---|---|
| C1 | EEXI 达到值 vs Annex 2 手写展开式（逐项 + 整式） | 整式相对误差 0.00e+00 %；各项 rel≈1e-12 级 | **是（<0.1%）** |
| C2 | 三船型要求值 vs 独立复算 | 最大 0.00e+00 % | **是（<1%）** |
| C3 | A–E 评级 vs 独立 bisect 分类器 | 60,003 点网格，误判 0 例；边界左闭右开语义逐边界验证 | **是（0 误判）** |
| C4 | 负控 | P_ME=0 → EEXI=0 且判合规；Capacity=0/V=0/Distance=0/负功率/未知船型燃料/2022 年均报错 | **是** |
| C5 | KVLCC2 端到端 vs 手算 | 相对误差 0.00e+00 %；限功率解回代命中 required（rel<1e-9） | **是（<0.1%）** |
| C6 | 判决逻辑 | 边界闭合（att=req → compliant）、四级→处置映射、连续三年 D / 单年 E 触发计划 | **是** |
| C7 | 报告字段完整性 | 32/32 = 100.0%（删字段负控可检出） | **是（100%）** |

> **是否 <3% 的显式回答**：C1/C5 达到值与手写展开式偏差 0.00e+00% ≪3%
> （0.00e+00 表示两写法在 float64 下逐位一致；量化判据在测试侧用 Decimal(40 位)/独立表达式
> 断言 rel<1e-3 与 <1%，见 `backend/tests/test_green_compliance.py`）；
> C2 要求值与高精度复算偏差 0.00e+00% ≪3%。
> 但**对规则原文**的偏差不可评估（系数层 WITHHELD，无原文基准）——这一条如实声明为
> "无基准"，不做粉饰。

## 7. 审计链与复现

```
python3 artifacts/p78n03_green_compliance/gen_artifacts.py     # 生成 results.json + 4 图 + 本文档
cd backend && python -m pytest tests/test_green_compliance.py -q   # 53 passed
cd backend && python -m pytest tests/test_green_shipping.py -q     # 18 passed（原有用例不回归）
```

* 结果 JSON：`artifacts/p78n03_green_compliance/results.json`（含 png sha256、全部中间量）
* **未跑**：`backend/main.py` 全量装配（本地缺 `openpyxl`，属既有环境缺口，与本改动无关）；
  `tests/test_api.py`（需 :8001 活服务，基线即失败）。已跑：本节点 49 例 + 原 green_shipping 18 例全绿。
* 端点自检：`GET /api/v1/green-shipping/rating_boundaries`、
  `POST /api/v1/green-shipping/eexi_full`、`POST /api/v1/green-shipping/cii_rating`、
  `POST /api/v1/green-shipping/compliance_report`


---

## 发布注记（诚实披露）
* 本报告正文由 `artifacts/p78n03_green_compliance/gen_artifacts.py` 程序化生成（零手抄），
  图与数字同源 `results.json`（含 4 张 png 的 sha256）。
* `/tmp/report.json` 为跨智能体共享路径，本次观测到被其它节点覆盖（2026-11-09 08:08 一次
  TensorBEM 阴极保护报告写入同名文件），导致本节点先前两次投递把他人正文写进了
  mission 8439 的占位行（id 9754，标题为本节点、正文为他人）。本行由唯一文件名重新投递，
  以本行正文为准；id 9750（ingress 探针）、9754（串稿占位）为此次共享路径冲突的副产物，
  建议平台侧清理。
