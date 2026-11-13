# KF-RESULT wp-10602-01

**工序** 01-asset-registration ｜ **report_id** 10602 ｜ **package_id** wp-10602-01 ｜ **lane** C ｜ **mission** 15686
**源** `tensor://reports/10602` · field=`markdown` · sha256=`55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687` · chars=6037 · bytes_utf8=9768
**源报告标题** P162W1-N04 EEDI 设计变量灵敏度与约束优化：五维 Pareto 前沿 + 可微 IMO 公式链 + 几何门禁 ｜ **scenario_key** `ship_performance` ｜ **平台 mission_id** 9073 · status=published

## 一、本工序做了什么

只做一件事：把 report_id=10602 的**源资产登记成册**（asset registration），不做抽取、不做分类、不做核验。
本包只读写 report 10602 这一份报告，未触碰任何其它 report_id。

- 登记资产 **45** 项：其中 markdown 内可原文定位 **30** 项（`resolved_in_source`）、
  报告点名但本体不在 payload 内 **12** 项（`referenced_unresolved`）、
  报告**自行声明不做/未含** **3** 项（`declared_absent`）。
- `claims` 数组**为空**：契约 `objective.register_assets=true` / `objective.classify_report_type=false`，
  且 `no_forced_claim_generation=true`——本工序不生成知识对象，不为凑指标造 claim。
- **没有任何条目被标成 verified**：`resolution` 只描述「定位/资产能否解析」，不代表报告结论为真；
  报告里 C1-C8「全部 PASS」是**报告作者的判定（claim）**，由平台门计算 verification，本包只登记其原文位置（A03 / A15）。
- 内容覆盖率：markdown 字符被「内联资产 span」覆盖 **92.3%**（A02-A30；A01=全文本身不计）。

## 二、怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/10602`（Bearer 登录 token），只取 `markdown` 字段，
   落盘为 `runs/wp-10602-01/report_10602.md`；同时保存整份 payload 供 figures/tags/mission 元信息登记。
2. **哈希门**：本地重算 `sha256(markdown.encode('utf-8'))` = `55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687`，与契约 `source_hash`
   **逐字符相等**；`chars=6037` 与契约 `chars: 6037` 相等。不等则脚本直接退出（不发任何产物）。
3. **零手抄定位**：每个资产给一个**唯一锚点串**，脚本在 markdown 行索引里查锚点（要求命中数 = 1，否则硬失败），
   再按行偏移切出 `quote`，用 `md.find(quote)` 求 `start_char/end_char`，"unique" 由 `md.count(quote)==1` 程序判定。
   → 引文全部是**运行时切出来的字节**，不是人写的字符串。
4. **外部资产探测**（只读、有界）：对被点名的文件/代码路径在固定根
   `/root/ship-performance-platform`、`/root/tp-agent/work/m9073` 做存在性探测，并另外做过一次
   `find /root -maxdepth 4 -type d -name eedi_opt`（无命中）。探测明细逐项写进 `resolution_check.probe`。
5. **结构门**：envelope 用它自己的 `schemas/kf_result.v1.schema.json` 校验；manifest 用本包新增的
   `schemas/asset_manifest.v1.1.schema.json`（把 v1 里写死的 `wp-448-01`/`448` 常量换成 pattern，其余同形，
   v1 不动、不影响别的包）。
6. **独立复核**：`scripts/kf_verify_10602.py` **重新从 API 取一次 markdown**（不信任产物缓存），
   逐项重算哈希、逐条 `md[start:end]==quote`、行号与字符偏移互校、id 唯一性、claims 纪律、计数自洽。

## 三、产出物清单

| 文件 | 要点 |
|---|---|
| `docs/wp-10602-01/asset_manifest.json` | 本工序正式产物：45 项资产 + source 元信息 + counts + integrity；`claims=[]` |
| `docs/wp-10602-01/kf_result.wp-10602-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims），即下方唯一 json 块 |
| `docs/wp-10602-01/fig1_asset_coverage.png` | 图 1：资产 span 沿源文本分布 + 按 asset_class 计数（统计数字由 manifest 程序化注入） |
| `docs/wp-10602-01/KF-RESULT-wp-10602-01.md` | 本报告正文（唯一 json 块 = 结果信封） |
| `scripts/kf_fetch_10602.py` | 取原文 + 哈希校验（凭据只走环境变量） |
| `scripts/kf_register_10602.py` | 登记器：锚点定位/唯一性断言/外部探测/schema 校验/落盘 |
| `scripts/kf_verify_10602.py` | 独立复核器：重取原文后逐项复验验收条目，输出 PASS/FAIL |
| `scripts/kf_report_10602.py` | 本报告生成器（正文数字与表格全部由 manifest/verifier 输出格式化） |
| `schemas/asset_manifest.v1.1.schema.json` | 新增**可复用**（package-agnostic）资产册 schema |

可复用增量说明：仓内既有 `schemas/asset_manifest.v1.schema.json` 把 `package_id`/`report_id`/`uri` 写成
本包专属 `const`（只服务 wp-448-01）；本包新增 v1.1 为同形但用 pattern 泛化，后续 01 工序可直接复用，且不改动 v1。

## 四、证据定位表（claim/字段 → 原文引文片段）

下表每行的引文都是运行时从 markdown 切出的**逐字片段**（长行取单行前缀，末尾 `…` 为截断标记，非原文）；
完整 `quote`（含多行）与精确 `start_char/end_char` 见 `docs/wp-10602-01/asset_manifest.json` 对应 asset 的 `locator`。
表中 span 列可独立复算：`md[start:end] == quote`。

| 登记项（asset_id / 字段） | 原文引文片段（逐字，单行前缀） | char span | 解析结果 |
|---|---|---|---|
| A01 | # P162W1-N04 \| EEDI 设计变量灵敏度与约束优化：五维设计空间 Pareto 前沿 + 可微 IMO 公式链 + 几何可行… ⟨+155 行⟩ | 0-6037 | resolved_in_source/resolved |
| A02 | # P162W1-N04 \| EEDI 设计变量灵敏度与约束优化：五维设计空间 Pareto 前沿 + 可微 IMO 公式链 + 几何可行… | 0-72 | resolved_in_source/resolved |
| A03 | **仓** ship-performance-platform \| **模块** `backend/physics/eedi_opt/` … ⟨+1 行⟩ | 74-200 | resolved_in_source/resolved |
| A04 | \| 变量 \| 含义 \| 区间 \| ⟨+6 行⟩ | 339-555 | resolved_in_source/resolved |
| A05 | 设计点参数：V_ref = 14.0 kn、SFC = 190.0 g/kWh、 ⟨+1 行⟩ | 557-628 | resolved_in_source/resolved |
| A06 | 约束门限：DWT >= 25000 t、GM >= 0.5 m、 ⟨+2 行⟩ | 629-711 | resolved_in_source/resolved |
| A07 | **参考设计点**（L=180 m / B=30 m / T=10.5 m / Cb=0.82）： ⟨+4 行⟩ | 713-959 | resolved_in_source/resolved |
| A08 | （IMO Phase-3 参考线 4.38 g CO2/(t nm)，仅作合规性上下文， ⟨+2 行⟩ | 960-1031 | resolved_in_source/resolved |
| A09 | 1. **公式链（REAL，全部复用仓内单一实现，本包不重写任何回归式）** ⟨+5 行⟩ | 1058-1430 | resolved_in_source/resolved |
| A10 | 2. **筛选级工程代理（显式标注，非规范计算）**：DWT = Δ - 0.98·Δ^0.85（LWT 单点标定： ⟨+3 行⟩ | 1431-1697 | resolved_in_source/resolved |
| A11 | 3. **可微近似**：对 R_T(L,B,T,Cb) 与 eta_D(L,B,T,Cb) 拟合**张量积 Chebyshev 样条** ⟨+3 行⟩ | 1698-1863 | resolved_in_source/resolved |
| A12 | 4. **灵敏度**：四阶中心差分（Richardson 外推）求真值链梯度作对照；无量纲弹性系数； ⟨+2 行⟩ | 1864-2001 | resolved_in_source/resolved |
| A13 | 5. **优化**：约束 NSGA-II（可行性优先非支配排序 + 拥挤度 + SBX/多项式变异，种群 120， ⟨+1 行⟩ | 2002-2114 | resolved_in_source/resolved |
| A14 | 6. **门禁**：几何可行性（L/B >= 3、B/T <= 6、Cb <= Cp）+ DWT/GM/sigma/功率平衡； ⟨+1 行⟩ | 2115-2215 | resolved_in_source/resolved |
| A15 | \| 判据 \| 指标 \| 数值 \| 判定 \| ⟨+9 行⟩ | 2234-2841 | resolved_in_source/resolved |
| A16 | **Pareto 前沿**：N = 120，EEDI 区间 [4.652, 11.344] g CO2/(t nm)， ⟨+3 行⟩ | 2843-3050 | resolved_in_source/resolved |
| A17 | \| 收紧方式 \| 参数序列 \| 全局 min EEDI \| 包络逐箱上移 \| 包络平均位移 \| ⟨+3 行⟩ | 3164-3448 | resolved_in_source/resolved |
| A18 | 方向解释：①收紧容量上界 -> 只允许更小的船 -> 前沿整体向高 EEDI 移动（与判据 C6 文字一致）； ⟨+3 行⟩ | 3450-3661 | resolved_in_source/resolved |
| A19 | **局部灵敏度（参考设计点，设计点面弹性系数 E_i = (dEEDI/dx_i)(x_i/EEDI)）**： ⟨+5 行⟩ | 3663-3784 | resolved_in_source/resolved |
| A20 | **自由功率面弹性系数（含 P）**： ⟨+6 行⟩ | 3786-3887 | resolved_in_source/resolved |
| A21 | **全局灵敏度 Sobol（设计点面 4D）**：一阶 S = { L: 0.000, B: 0.000, T: 0.000, Cb: 1.… ⟨+3 行⟩ | 3889-4130 | resolved_in_source/resolved |
| A22 | ## 四、结果图 ⟨+3 行⟩ | 4132-4247 | resolved_in_source/resolved |
| A23 | 1. **公式链非规范全量**：EEDI 用简化面 `P·SFC·C_F/(DWT·V_ref)`（无 P_AE、f_j、f_i、f_w | 4289-4357 | resolved_in_source/resolved |
| A24 | 2. **重量/稳性/强度是筛选级代理**：LWT、KG、剖面模数、静水/波浪弯矩比均为单点标定的 ⟨+2 行⟩ | 4436-4574 | resolved_in_source/resolved |
| A25 | 3. **差分量化噪声（实测坑）**：`Holtrop1984Output` 把 R_T 舍入到 0.01 kN，差分步长 ⟨+2 行⟩ | 4575-4760 | resolved_in_source/resolved |
| A26 | 4. **两种导数面必须区分**：固定装机功率时 dEEDI/dCb\|_P < 0（只经 DWT 分母起作用）， ⟨+1 行⟩ | 4761-4870 | resolved_in_source/resolved |
| A27 | 5. **局限**：代理仅在给定盒约束内有效（Cb 0.74-0.86、L 150-210 m 等）；单一 V_ref = 14 kn； ⟨+2 行⟩ | 4871-5039 | resolved_in_source/resolved |
| A28 | \| 关键量 \| 基准 \| 误差 \| 是否 < 3% \| ⟨+7 行⟩ | 5052-5439 | resolved_in_source/resolved |
| A29 | 对「有基准的量」逐项显式回答：上述五项相对误差均 < 3%（最严者 ⟨+3 行⟩ | 5441-5565 | resolved_in_source/resolved |
| A30 | ## 七、审计链 ⟨+9 行⟩ | 5567-6037 | resolved_in_source/resolved |
| A31 | 逐解明细见 `artifacts/m9073_eedi_opt/pareto_front.csv`（含 DWT/GM/sigma/P_req… | 2964-3050 | referenced_unresolved/unresolved |
| A32 | - 判据与全部中间量：`artifacts/m9073_eedi_opt/acceptance.json`、`sensitivity.jso… ⟨+1 行⟩ | 5577-5702 | referenced_unresolved/unresolved |
| A33 | - 判据与全部中间量：`artifacts/m9073_eedi_opt/acceptance.json`、`sensitivity.jso… | 5577-5650 | referenced_unresolved/unresolved |
| A34 | - 图：`artifacts/m9073_eedi_opt/figures/fig1..fig5*.png`。 | 5703-5758 | referenced_unresolved/unresolved |
| A35 | - 复现：`python scripts/eedi_opt_m9073.py`（固定 seed = 20261009）； | 5759-5819 | referenced_unresolved/unresolved |
| A36 | `pytest tests/test_eedi_optimization_m9073.py -q` 覆盖 C1-C8 与门禁/投影。 | 5820-5888 | referenced_unresolved/unresolved |
| A37 | - 代码：`backend/physics/eedi_opt/`（design_space / hydro / chain / surrog… | 5889-5964 | referenced_unresolved/unresolved |
| A38 | sensitivity / pareto / gates）、API：`backend/api/eedi_optimization.py`。 | 5965-6036 | referenced_unresolved/unresolved |
| A39 | - 阻力：`backend/physics/holtrop.holtrop1984_resistance`（Holtrop-Mennen 1… | 1097-1190 | referenced_unresolved/unresolved |
| A40 | - 敞水：`src/b_series`（Oosterveld & van Oossanen 1975 回归）解工作点 | 1191-1252 | referenced_unresolved/unresolved |
| A41 | 与创新技术抵扣），与 `api/extended_calculations.calculate_energy_efficiency_v2` … | 4358-4435 | referenced_unresolved/unresolved |
| A42 | 5 张内嵌图：Pareto 前沿与全链复核（1:1 对比）、收敛历史（min EEDI + 超体积）、 | 4142-4193 | referenced_unresolved/unresolved |
| A43 | 1. **公式链非规范全量**：EEDI 用简化面 `P·SFC·C_F/(DWT·V_ref)`（无 P_AE、f_j、f_i、f_w ⟨+1 行⟩ | 4289-4435 | declared_absent/absent |
| A44 | 完整判定需船级社规范计算与 IS Code 2008 六项衡准 + 天气衡准。 | 4532-4574 | declared_absent/absent |
| A45 | 不含设备价格、钢材价格与批量效应；未含破舱稳性与纵倾/吃水差耦合。 | 5003-5039 | declared_absent/absent |

### 4.1 资产册全量清单

| asset_id | asset_class | resolution | 位置（char span / line） | label |
|---|---|---|---|---|
| A01 | document | resolved_in_source | 0-6037（全文） | 报告正文（markdown 全文） |
| A02 | heading | resolved_in_source | 0-72 / L0-0 | 报告标题行 |
| A03 | declaration | resolved_in_source | 74-200 / L2-3 | 仓/模块归属与运行耗时声明 |
| A04 | design_space | resolved_in_source | 339-555 / L10-16 | 设计变量与盒约束表（5 变量） |
| A05 | parameter_set | resolved_in_source | 557-628 / L18-19 | 设计点参数（V_ref/SFC/C_F/eta_S） |
| A06 | constraint_set | resolved_in_source | 629-711 / L20-22 | 约束门限（DWT/GM/sigma/L_B/B_T/Cb-Cp） |
| A07 | result_block | resolved_in_source | 713-959 / L24-28 | 参考设计点结果（DWT/GM/sigma/R_T/eta_D/J/n/P/EEDI） |
| A08 | context_reference | resolved_in_source | 960-1031 / L29-31 | IMO Phase-3 参考线与「不做合规判定」声明 |
| A09 | method_chain | resolved_in_source | 1058-1430 / L34-39 | 公式链（阻力/敞水/排水量，REAL） |
| A10 | method_proxy | resolved_in_source | 1431-1697 / L40-43 | 筛选级工程代理（DWT/GM/sigma 单点标定） |
| A11 | method_surrogate | resolved_in_source | 1698-1863 / L44-47 | 可微近似（张量积 Chebyshev 样条） |
| A12 | method_sensitivity | resolved_in_source | 1864-2001 / L48-50 | 灵敏度方法（四阶差分/弹性系数/Saltelli + Sobol） |
| A13 | method_optimizer | resolved_in_source | 2002-2114 / L51-52 | 优化器设置（约束 NSGA-II） |
| A14 | method_gates | resolved_in_source | 2115-2215 / L53-54 | 门禁与全链复核/投影 |
| A15 | acceptance_table | resolved_in_source | 2234-2841 / L58-67 | 验收判据表 C1-C8（数值 + PASS 判定） |
| A16 | result_block | resolved_in_source | 2843-3050 / L69-72 | Pareto 前沿汇总（N/EEDI 区间/成本区间/偏差） |
| A17 | table | resolved_in_source | 3164-3448 / L78-81 | C6 约束负控明细表 |
| A18 | interpretation | resolved_in_source | 3450-3661 / L83-86 | C6 方向解释与被否定的镜像对称假设 |
| A19 | sensitivity_block | resolved_in_source | 3663-3784 / L88-93 | 局部灵敏度弹性系数（设计点面 4D） |
| A20 | sensitivity_block | resolved_in_source | 3786-3887 / L95-101 | 自由功率面弹性系数（5D，含 P） |
| A21 | sensitivity_block | resolved_in_source | 3889-4130 / L103-106 | 全局灵敏度 Sobol 指数（4D / 5D） |
| A22 | figure_reference | resolved_in_source | 4132-4247 / L108-111 | 结果图声明（5 张内嵌图） |
| A23 | caveat | resolved_in_source | 4289-4357 / L116-116 | 注意点 1：EEDI 简化面（非规范全量） |
| A24 | caveat | resolved_in_source | 4436-4574 / L118-120 | 注意点 2：重量/稳性/强度为筛选级代理 |
| A25 | caveat | resolved_in_source | 4575-4760 / L121-123 | 注意点 3：差分量化噪声实测坑 |
| A26 | caveat | resolved_in_source | 4761-4870 / L124-125 | 注意点 4：两种导数面必须区分 |
| A27 | caveat | resolved_in_source | 4871-5039 / L126-128 | 注意点 5：适用范围与局限 |
| A28 | error_table | resolved_in_source | 5052-5439 / L132-139 | 误差判定表（6 个关键量 vs 基准） |
| A29 | error_statement | resolved_in_source | 5441-5565 / L141-144 | 无实验基准量的显式声明 |
| A30 | audit_chain | resolved_in_source | 5567-6037 / L146-155 | 审计链（判据/图/复现/代码位置） |
| A31 | artifact_file | referenced_unresolved | 2964-3050 / L72-72 | Pareto 逐解明细 CSV |
| A32 | artifact_file | referenced_unresolved | 5577-5702 / L148-149 | 审计链整条：判据与全部中间量（acceptance.json + sensitivity.json + pareto_front.csv 说明） |
| A33 | artifact_file | referenced_unresolved | 5577-5650 / L148-148 | 灵敏度 JSON（sensitivity.json） |
| A34 | artifact_glob | referenced_unresolved | 5703-5758 / L150-150 | 结果图 PNG（fig1..fig5） |
| A35 | repro_command | referenced_unresolved | 5759-5819 / L151-151 | 一键复跑脚本（seed = 20261009） |
| A36 | test_file | referenced_unresolved | 5820-5888 / L152-152 | C1-C8 与门禁/投影测试 |
| A37 | code_module | referenced_unresolved | 5889-5964 / L153-153 | 优化实现包（design_space/hydro/chain/...） |
| A38 | code_module | referenced_unresolved | 5965-6036 / L154-154 | 优化 API 端点模块 |
| A39 | code_dependency | referenced_unresolved | 1097-1190 / L35-35 | 阻力实现（Holtrop-Mennen 1984） |
| A40 | code_dependency | referenced_unresolved | 1191-1252 / L36-36 | 敞水实现（Wageningen B 系列） |
| A41 | code_dependency | referenced_unresolved | 4358-4435 / L117-117 | EEDI 同口径函数 |
| A42 | figure_binary | referenced_unresolved | 4142-4193 / L110-110 | 5 张内嵌图（fig1..fig5 PNG 二进制） |
| A43 | missing_term_set | declared_absent | 4289-4435 / L116-117 | EEDI 修正项 P_AE/f_j/f_i/f_w/创新技术抵扣 |
| A44 | missing_analysis | declared_absent | 4532-4574 / L120-120 | 船级社规范计算 + IS Code 2008 六项衡准+天气衡准 |
| A45 | missing_analysis | declared_absent | 5003-5039 / L128-128 | 破舱稳性与纵倾/吃水差耦合 |

### 4.2 外部引用探测明细（只读）

| asset_id | 引用路径（原文） | 探测根 | 结果 |
|---|---|---|---|
| A31 | artifacts/m9073_eedi_opt/pareto_front.csv | /root/ship-performance-platform/artifacts/m9073_eedi_opt/pareto_front.csv → exists=False<br>/root/tp-agent/work/m9073/artifacts/m9073_eedi_opt/pareto_front.csv → exists=False | unresolved |
| A32 | artifacts/m9073_eedi_opt/acceptance.json | /root/ship-performance-platform/artifacts/m9073_eedi_opt/acceptance.json → exists=False<br>/root/tp-agent/work/m9073/artifacts/m9073_eedi_opt/acceptance.json → exists=False | unresolved |
| A33 | artifacts/m9073_eedi_opt/sensitivity.json | /root/ship-performance-platform/artifacts/m9073_eedi_opt/sensitivity.json → exists=False<br>/root/tp-agent/work/m9073/artifacts/m9073_eedi_opt/sensitivity.json → exists=False | unresolved |
| A34 | artifacts/m9073_eedi_opt/figures | /root/ship-performance-platform/artifacts/m9073_eedi_opt/figures → exists=False<br>/root/tp-agent/work/m9073/artifacts/m9073_eedi_opt/figures → exists=False | unresolved |
| A35 | scripts/eedi_opt_m9073.py | /root/ship-performance-platform/scripts/eedi_opt_m9073.py → exists=False<br>/root/tp-agent/work/m9073/scripts/eedi_opt_m9073.py → exists=False | unresolved |
| A36 | tests/test_eedi_optimization_m9073.py | /root/ship-performance-platform/tests/test_eedi_optimization_m9073.py → exists=False<br>/root/tp-agent/work/m9073/tests/test_eedi_optimization_m9073.py → exists=False | unresolved |
| A37 | backend/physics/eedi_opt | /root/ship-performance-platform/backend/physics/eedi_opt → exists=False<br>/root/tp-agent/work/m9073/backend/physics/eedi_opt → exists=False | unresolved |
| A38 | backend/api/eedi_optimization.py | /root/ship-performance-platform/backend/api/eedi_optimization.py → exists=False<br>/root/tp-agent/work/m9073/backend/api/eedi_optimization.py → exists=False | unresolved |
| A39 | backend/physics/holtrop.py | /root/ship-performance-platform/backend/physics/holtrop.py → exists=False<br>/root/tp-agent/work/m9073/backend/physics/holtrop.py → exists=False | unresolved |
| A40 | src/b_series | /root/ship-performance-platform/src/b_series → exists=False<br>/root/tp-agent/work/m9073/src/b_series → exists=False | unresolved |
| A41 | api/extended_calculations.py | /root/ship-performance-platform/api/extended_calculations.py → exists=False<br>/root/tp-agent/work/m9073/api/extended_calculations.py → exists=False | unresolved |

## 五、注意点与局限

1. **图二进制不可解析（登记发现）**：报告正文声明「5 张内嵌图」，但平台 payload 的 `figures` 只有
   `name` + `caption` 两条元数据（fig1_pareto_front / fig2_convergence / fig3_surrogate_error /
   fig4_sensitivity / fig5_constraint_shift），**没有 png 字段**；markdown 里也没有内联图引用。
   → 5 张图登记为 `referenced_unresolved`（A42，metadata present / binary unresolved）。
2. **被点名的工件与代码在本登记环境不可达（登记发现，非报告错误）**：A31-A41 共 11 项
   （`artifacts/m9073_eedi_opt/*`、`scripts/eedi_opt_m9073.py`、`tests/test_eedi_optimization_m9073.py`、
   `backend/physics/eedi_opt/`、`backend/api/eedi_optimization.py`、`backend/physics/holtrop.*`、`src/b_series`）
   在两个探测根下**均不存在**，`find /root -maxdepth 4 -name eedi_opt` 亦无命中。
   影响：下游抽取工序（02/03）无法取到 Pareto 逐解明细/判据 JSON/测试文件来交叉核对，
   这类交叉核对只能标 `unresolved`，**不得**凭正文数字重述为已验证。
3. **登记过程中观察到一处报告内部不自洽（只登记，不判定）**：A21 引文里一阶 Sobol 指数
   `Cb: 1.902`，而方差分解的一阶指数定义域为 [0,1]、一阶指数和 ≤ 1；同段文字又写「一阶指数和 = 1.902
   （<1 说明变量间存在交互作用）」，与数值方向相反。本包容量为登记：已把该段原文位置固定（A21），
   该数值是否成立由平台门/领域复核决定，本包**不**给结论、不标 verified。
4. **`declared_absent` 三项是给下游的护栏**：EEDI 修正项（P_AE/f_j/f_i/f_w/创新技术抵扣，A43）、
   船级社规范计算 + IS Code 2008 六项衡准与天气衡准（A44）、破舱稳性与纵倾/吃水差耦合（A45）——
   报告自己声明「未含/域外」。下游抽取若越界生成这些结论，即为越过报告能力边界。
5. **「PASS」不是本包的结论**：A03/A15 登记的是报告作者的判据判定文字，本包只保证「这句话在原文这个位置」。
   本包自己也**没有任何 verified 标记**（`integrity.verified_claims = 0`）。
6. **探测有界**：外部存在性只在 2 个固定根 + 一次 `maxdepth 4` 的 find 内做过，未做全盘扫描；
   若这些工件存在于其它机器/分支，A31-A41 的 `unresolved` 应被更新（`resolution_check.probe` 保留了我探测过的每个路径）。
7. **边界**：只碰 report 10602；未改上游产物、未改 `schemas/asset_manifest.v1.schema.json`、未 push。

## 六、自检（逐条对照 acceptance）

自动复核器 `scripts/kf_verify_10602.py`（重新取原文后独立复验）输出：

| verdict | 检查项与实测细节 |
|---|---|
| PASS | valid_json envelope 54530 B, manifest 49246 B parsed |
| PASS | schema_pass envelope vs kf_result.v1: ok \| manifest(in envelope) vs asset_manifest.v1.1: ok \| manifest(standalone) vs asset_manifest.v1.1: ok |
| PASS | envelope_matches_manifest outputs['asset_manifest.json'] byte-identical to docs copy |
| PASS | source_hash_matches fresh=55cb6ccf85a7c340… contract=55cb6ccf85a7c340… manifest=55cb6ccf85a7c340… envelope=sha256:55cb6ccf85a7c340… |
| PASS | chars_match_contract fresh chars=6037, contract=6037, manifest=6037 |
| PASS | source_locator_resolvable 45/45 locators re-resolve on fresh markdown |
| PASS | no_duplicate_ids 45 unique ids / 45 assets; contiguous=True |
| PASS | all_claims_have_evidence_or_explicit_unresolved_status claims=0 manifest / 0 envelope (empty = allowed for task_type 01); violations=none |
| PASS | no_claim_marked_verified envelope contains no 'verified' status marker |
| PASS | report_scope_10602_only envelope/manifest report_id = 10602/10602, uri=tensor://reports/10602 |
| PASS | package_identity package_id=wp-10602-01, task_type=01-asset-registration |
| PASS | counts_self_consistent {"assets": 45, "by_class": {"acceptance_table": 1, "artifact_file": 3, "artifact_glob": 1, "audit_chain": 1, "caveat": 5, "code_dependency": 3, "code_module": 2, "constraint_set": 1, "context_reference": 1, "declaration": 1, "design_space": 1, "document": 1, "error_statement": 1, "error_table": 1, "figure_binary": 1, "figure_reference": 1, "heading": 1, "interpretation": 1, "method_chain": 1, "method_gates": 1, "method_optimizer": 1, "method_proxy": 1, "method_sensitivity": 1, "method_surrogate": 1, "missing_analysis": 2, "missing_term_set": 1, "parameter_set": 1, "repro_command": 1, "result_block": 2, "sensitivity_block": 3, "table": 1, "test_file": 1}, "by_resolution": {"declared_absent": 3, "referenced_unresolved": 12, "resolved_in_source": 30}, "resolved_in_source": 30, "referenced_unresolved": 12, "declared_absent": 3} |

- `valid_json`：envelope 与 manifest 均可解析 → **PASS**
- `schema_pass`：envelope vs `kf_result.v1`、manifest vs `asset_manifest.v1.1`（含 envelope 内嵌 manifest 与独立文件字节一致）→ **PASS**
- `source_locator_resolvable`：45/45 条 locator 在**重取**的原文上 `md[start:end]==quote` 且 unique 成立 → **PASS**
- `source_hash_matches`：`55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687` = 契约 = manifest = envelope provenance.source_hash → **PASS**
- `no_duplicate_ids`：45 个 id 唯一且连续 A01..A45 → **PASS**
- `all_claims_have_evidence_or_explicit_unresolved_status`：claims 为空（契约允许），无缺失证据项 → **PASS**

**如实声明的未完成/不可完成部分**：① 5 张图的二进制、② 11 个被点名工件与代码
（A31-A41）在本环境不可解析，登记为 `referenced_unresolved` 并附探测记录——这是**已知未闭合项**，
不是 PASS；下游若需这些资产须另行从源仓（ship-performance-platform, mission 9073）取回后再登记。

## 七、repro_cmd（一键复跑）

**repro_cmd**: `cd <worktree> && python3 scripts/kf_fetch_10602.py && python3 scripts/kf_register_10602.py && python3 scripts/kf_verify_10602.py && python3 scripts/kf_report_10602.py`

- 前置：环境变量 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`（不落盘、不写进任何产物）。
- 期望：fetch 打印的 sha256 = `55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687`；register 打印 assets=45、哈希匹配；
  verify 全部 12 项 PASS 且退出码 0；report 重建同一份 markdown（含同一 json 块）。
- 注：`artifacts/` 与 `runs/` 会被仓推送门禁过滤，`*.png` 亦被过滤——故正式副本落在
  `docs/wp-10602-01/`，图 1 同时以 base64 内嵌在本报告 `figures` 字段。

## 图

内嵌 1 张（`fig1_asset_coverage`）：左图 = 每项资产的 locator span 沿源文本字符轴的分布
（斜线填充 = 本体不在 payload 的 `referenced_unresolved`/`declared_absent`），右图 = 按 asset_class 计数。
图中所有数字由 `docs/wp-10602-01/asset_manifest.json` 程序化注入。
（本工序为登记/文档工序，唯一有意义的可视图是「资产覆盖图」；报告物理结果图属上游 10602 的能力，
且其二进制本次不可解析——见第五节 1/2，故不重绘、不臆造。）

## 结果信封（唯一 json 块）

```json
{
  "package_id": "wp-10602-01",
  "task_type": "01-asset-registration",
  "report_id": "10602",
  "provenance": {
    "source_hash": "sha256:55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687",
    "source_field": "markdown",
    "producer": "scripts/kf_register_10602.py (agent m15686)",
    "emitted_at": "2026-11-12T01:46:53+00:00",
    "notes": "asset registration only; no extraction, no claim verification; 45 assets registered (resolved_in_source=30, referenced_unresolved=12, declared_absent=3)"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-10602-01",
      "task_type": "01-asset-registration",
      "report_id": "10602",
      "source": {
        "uri": "tensor://reports/10602",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687",
        "chars": 6037,
        "bytes_utf8": 9768,
        "title": "P162W1-N04 EEDI 设计变量灵敏度与约束优化：五维 Pareto 前沿 + 可微 IMO 公式链 + 几何门禁",
        "scenario_key": "ship_performance",
        "platform_mission_id": 9073,
        "platform_status": "published",
        "platform_figures": [
          {
            "name": "fig1_pareto_front",
            "caption": "Left: final NSGA-II population and Pareto front (N=120), grey = constraint-violating; right: surrogate vs full-chain EEDI of every front solution (max |d| = 0.03%)."
          },
          {
            "name": "fig2_convergence",
            "caption": "Convergence history (min feasible EEDI and 2-objective hypervolume): converged at generation 201, EEDI change over the last 50 generations = 0.0579% (<0.1%)."
          },
          {
            "name": "fig3_surrogate_error",
            "caption": "Relative error of the Chebyshev spline surrogate vs the original formulas over 100 random samples: R_T max 0.021%, eta_D max 0.006%, EEDI max 0.027% (criterion 1%)."
          },
          {
            "name": "fig4_sensitivity",
            "caption": "Saltelli Sobol indices: 4D design-point surface (L,B,T,Cb) and 5D free-power surface (including P)."
          },
          {
            "name": "fig5_constraint_shift",
            "caption": "Left: DWT constraint negative control (capacity cap tightening shifts the front up, raising the deadweight floor shifts it down); right: design-point EEDI rising monotonically with Cb, surrogate on top of the full chain."
          }
        ],
        "platform_tags": [
          "EEDI",
          "Holtrop-Mennen",
          "NSGA-II",
          "Pareto",
          "Sobol",
          "灵敏度分析",
          "可微代理",
          "ship-performance-platform",
          "P162W1-N04"
        ]
      },
      "counts": {
        "assets": 45,
        "by_class": {
          "acceptance_table": 1,
          "artifact_file": 3,
          "artifact_glob": 1,
          "audit_chain": 1,
          "caveat": 5,
          "code_dependency": 3,
          "code_module": 2,
          "constraint_set": 1,
          "context_reference": 1,
          "declaration": 1,
          "design_space": 1,
          "document": 1,
          "error_statement": 1,
          "error_table": 1,
          "figure_binary": 1,
          "figure_reference": 1,
          "heading": 1,
          "interpretation": 1,
          "method_chain": 1,
          "method_gates": 1,
          "method_optimizer": 1,
          "method_proxy": 1,
          "method_sensitivity": 1,
          "method_surrogate": 1,
          "missing_analysis": 2,
          "missing_term_set": 1,
          "parameter_set": 1,
          "repro_command": 1,
          "result_block": 2,
          "sensitivity_block": 3,
          "table": 1,
          "test_file": 1
        },
        "by_resolution": {
          "declared_absent": 3,
          "referenced_unresolved": 12,
          "resolved_in_source": 30
        },
        "resolved_in_source": 30,
        "referenced_unresolved": 12,
        "declared_absent": 3
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文）",
          "in_report_section": "全文（markdown 整体）",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 6037,
            "start_line": 0,
            "end_line": 155,
            "quote": "# P162W1-N04 | EEDI 设计变量灵敏度与约束优化：五维设计空间 Pareto 前沿 + 可微 IMO 公式链 + 几何可行性门禁\n\n**仓** ship-performance-platform | **模块** `backend/physics/eedi_opt/` | **验收 C1-C8：全部 PASS**\n（运行 80.7 s，代理拟合 7.57 s，主优化 9.89 s）\n\n## 一、案例介绍（物理背景 / 几何 / 参数）\n\n以 **EEDI_attained 最小化** 为目标的散货船主尺度—丰满度联合设计优化。设计变量与盒约束\n（取自在运营船族中段带宽，保证 Holtrop-Mennen 与 Wageningen B 系列回归域内）：\n\n| 变量 | 含义 | 区间 |\n|---|---|---|\n| L [m] | 垂线间长 | [150.0, 210.0] |\n| B [m] | 型宽 | [24.0, 36.0] |\n| T [m] | 吃水 | [8.5, 13.0] |\n| Cb [-] | 方型系数 | [0.74, 0.86] |\n| P [kW] | 主机装机功率（约束 P >= P_required） | [1000.0, 20000.0] |\n\n设计点参数：V_ref = 14.0 kn、SFC = 190.0 g/kWh、\nC_F = 3.114（HFO）、eta_S = 0.99。\n约束门限：DWT >= 25000 t、GM >= 0.5 m、\nsigma <= 175 MPa、L/B >= 3.0、\nB/T <= 6.0、Cb <= Cp。\n\n**参考设计点**（L=180 m / B=30 m / T=10.5 m / Cb=0.82）：\nDWT = 38375 t，GM = 3.09 m，sigma = 156.6 MPa，\nR_T = 575.7 kN，eta_D = 0.637（eta_H = 1.070 · eta_0 = 0.595\n· eta_R = 1.00），J = 0.590，n = 71.4 rpm，\nP_ME,req = 6574 kW，设计点 EEDI = **7.240 g CO2/(t nm)**\n（IMO Phase-3 参考线 4.38 g CO2/(t nm)，仅作合规性上下文，\n本节点的目标是 EEDI 最小化，不做合规判定）。\n\n## 二、怎么做的（方法 / 流程 / 工具链）\n\n1. **公式链（REAL，全部复用仓内单一实现，本包不重写任何回归式）**\n   - 阻力：`backend/physics/holtrop.holtrop1984_resistance`（Holtrop-Mennen 1982 + Holtrop 1984）；\n   - 敞水：`src/b_series`（Oosterveld & van Oossanen 1975 回归）解工作点\n     `K_T(J) = T_req·J²/(rho·D²·V_a²)`（brentq 求根）；eta_H=(1-t)/(1-w)、eta_R=1、\n     eta_D = eta_H·eta_0·eta_R（代码内数值断言 eta_D ≡ P_E/P_D，相对差 < 1e-6）；\n   - 排水量：Δ = Cb·L·B·T·rho（几何恒等）。\n2. **筛选级工程代理（显式标注，非规范计算）**：DWT = Δ - 0.98·Δ^0.85（LWT 单点标定：\n   Δ=40 000 t -> 8 000 t）；GM = KB + BM_T - 0.60·D，BM_T = C_IT·B²/(Cb·T)、C_IT 由\n   水线面族解析积分 B(1/2, 3p+1)/24 给出；总纵应力 sigma = 1.45·M_wh/Z，\n   M_wh = 0.19·C1·L²·B·Cb（IACS UR S11 拟合形式），Z = k_Z·B·D²·(Cb+0.7)/1.52。\n3. **可微近似**：对 R_T(L,B,T,Cb) 与 eta_D(L,B,T,Cb) 拟合**张量积 Chebyshev 样条**\n   （Chebyshev-Lobatto 节点 8^4 = 4096 个，\n   度数 4，正规方程 + 微小岭项）；EEDI 的代数部分保持解析，\n   故 5 维梯度全解析（无需差分）。\n4. **灵敏度**：四阶中心差分（Richardson 外推）求真值链梯度作对照；无量纲弹性系数；\n   Saltelli/Jansen 估计量 + Sobol 低差异序列的全局 Sobol 指数（作用在代理上，\n   N = 4096 基样本、24576 次模型评估）。\n5. **优化**：约束 NSGA-II（可行性优先非支配排序 + 拥挤度 + SBX/多项式变异，种群 120，\n   上限 1000 代），目标 f1 = EEDI_attained、f2 = 建造成本代理 L·B·T。\n6. **门禁**：几何可行性（L/B >= 3、B/T <= 6、Cb <= Cp）+ DWT/GM/sigma/功率平衡；\n   每个前沿解用**全链**复核，必要时投影（repair）到可行域。\n\n## 三、计算结果（判据数字）\n\n| 判据 | 指标 | 数值 | 判定 |\n|---|---|---|---|\n| C1 | 代理 vs 原公式最大相对误差 R_T / eta_D / EEDI | 0.021% / 0.006% / 0.027%（判据 <1%） | PASS |\n| C2 | min dEEDI/dP（20 点差分 / 解析） | 8.823e-04 / 8.823e-04 | PASS |\n| C3 | min dEEDI/dCb（设计点面，20 点） | 3.845（<0 即 FAIL） | PASS |\n| C4 | Pareto 非支配解数 | 120（判据 >=50） | PASS |\n| C5 | 前沿解满足几何+全链约束比例 | 100.0%（投影前已可行 120/120，投影 0 个） | PASS |\n| C6 | 收紧 DWT_max -> min EEDI 严格单调升 + 全成本箱包络上移；抬高 DWT_min -> 全局 min 不变但包络逐箱上移 | True / True / True | PASS |\n| C7 | 收敛代 / 末 50 代 EEDI 变化 | 第 201 代 / 0.0579%（判据 <0.1%） | PASS |\n| C8 | 解析梯度 vs 差分梯度最大相对误差（5D / 4D 设计点） | 0.000% / 0.855%（判据 <5%） | PASS |\n\n**Pareto 前沿**：N = 120，EEDI 区间 [4.652, 11.344] g CO2/(t nm)，\n成本代理 L·B·T 区间 [36302, 98273] m³；\n前沿解代理与全链 EEDI 最大相对偏差 0.03%。\n逐解明细见 `artifacts/m9073_eedi_opt/pareto_front.csv`（含 DWT/GM/sigma/P_req/L_B/B_T 与复核标志）。\n\n**C6 负控明细**（固定 Sobol 候选集 131072 点，只改约束 -> 可行集是子集关系，\n故 min 的单调性由集合包含严格保证，不依赖优化器是否收敛；成本分箱最小 EEDI 包络作为前沿的\n确定性估计）：\n\n| 收紧方式 | 参数序列 | 全局 min EEDI | 包络逐箱上移 | 包络平均位移 |\n|---|---|---|---|---|\n| 容量上界 DWT_max | [None, 50000.0, 40000.0, 32000.0] | [4.852, 5.194, 5.729, 6.586] | True | [0.0155, 0.0113, 0.0202] |\n| 载重下限 DWT_min | [25000.0, 31000.0, 37000.0] | [4.852, 4.852, 4.852] | True | [0.1884, 0.1586] |\n\n方向解释：①收紧容量上界 -> 只允许更小的船 -> 前沿整体向高 EEDI 移动（与判据 C6 文字一致）；\n②抬高载重下限 -> 全局 min EEDI 不变（最优船本来就大），但固定成本箱内要装更多载重只能加丰满度\nCb，而 Cb 升高使 EEDI 升高 -> 包络逐箱上移。**原先假设的「镜像对称（抬高下限→EEDI 下降）」被实测\n否定**，此处如实报告机制差异（这也是本节点唯一的假设修正，不影响判据通过）。\n\n**局部灵敏度（参考设计点，设计点面弹性系数 E_i = (dEEDI/dx_i)(x_i/EEDI)）**：\n\n- E_L = -0.7382\n- E_B = -0.2307\n- E_T = -0.9734\n- E_Cb = +2.1036\n\n**自由功率面弹性系数（含 P）**：\n\n- E_L = -1.0363\n- E_B = -1.0363\n- E_T = -1.0363\n- E_Cb = -1.0363\n- E_P = +1.0000\n\n**全局灵敏度 Sobol（设计点面 4D）**：一阶 S = { L: 0.000, B: 0.000, T: 0.000, Cb: 1.902 }；\n总效应 ST = { L: 0.000, B: 0.000, T: 0.000, Cb: 1.902 }；一阶指数和 = 1.902\n（<1 说明变量间存在交互作用）。**自由功率面 5D**：P 的一阶 S_P = 0.000、\nST_P = 0.000——装机功率自由度主导方差，这正是「P 必须由功率平衡钉住」的定量理由。\n\n## 四、结果图\n\n5 张内嵌图：Pareto 前沿与全链复核（1:1 对比）、收敛历史（min EEDI + 超体积）、\n代理 vs 原公式误差分布、Sobol 灵敏度（4D/5D）、DWT 约束负控与 Cb 单调性曲线（含全链\nvs 代理曲线对比）。\n\n## 五、注意点（踩过的坑 / 局限 / 适用范围）\n\n1. **公式链非规范全量**：EEDI 用简化面 `P·SFC·C_F/(DWT·V_ref)`（无 P_AE、f_j、f_i、f_w\n   与创新技术抵扣），与 `api/extended_calculations.calculate_energy_efficiency_v2` 同口径。\n2. **重量/稳性/强度是筛选级代理**：LWT、KG、剖面模数、静水/波浪弯矩比均为单点标定的\n   工程量级估计，只用于判断「门禁是否可能被突破」，**不可作为结构或稳性设计依据**；\n   完整判定需船级社规范计算与 IS Code 2008 六项衡准 + 天气衡准。\n3. **差分量化噪声（实测坑）**：`Holtrop1984Output` 把 R_T 舍入到 0.01 kN，差分步长\n   h_rel < 1e-2 时梯度被量化噪声污染（h=1e-3 时设计点梯度误差可达 6%，h=1e-2 时 <=2%），\n   故 C8 取 h_rel=1e-2 + Richardson 外推。这是共享模块的输出精度问题，本包不改其行为。\n4. **两种导数面必须区分**：固定装机功率时 dEEDI/dCb|_P < 0（只经 DWT 分母起作用），\n   而设计点面（P = P_req(Cb)）总导数 > 0（C3 采用后者，见上表注释与图 5 右）。\n5. **局限**：代理仅在给定盒约束内有效（Cb 0.74-0.86、L 150-210 m 等）；单一 V_ref = 14 kn；\n   固定螺旋桨几何（P/D=0.95、Ae/A0=0.55、Z=4、D/T=0.68）；成本目标为 L·B·T 体积代理，\n   不含设备价格、钢材价格与批量效应；未含破舱稳性与纵倾/吃水差耦合。\n\n## 六、误差判定\n\n| 关键量 | 基准 | 误差 | 是否 < 3% |\n|---|---|---|---|\n| 代理 EEDI vs 全链 EEDI（100 点随机） | Holtrop + B 系列真值链 | 最大 0.027% | 是 |\n| 代理 R_T vs Holtrop | Holtrop-Mennen 原式 | 最大 0.021% | 是 |\n| 代理 eta_D vs 敞水工作点解 | brentq 工作点 + eta 分解 | 最大 0.006% | 是 |\n| 解析梯度 vs 四阶差分（4D 设计点） | 真值链差分 | 最大 0.855% | 是 |\n| 解析梯度 vs 四阶差分（5D 自由功率） | 真值链差分 | 最大 0.000% | 是 |\n| 前沿解代理 vs 全链 EEDI | Holtrop + B 系列真值链 | 最大 0.03% | 是 |\n\n对「有基准的量」逐项显式回答：上述五项相对误差均 < 3%（最严者\n0.85%）。**无实验基准的量**（DWT/GM/sigma\n代理、成本代理）不给误差数字而是标注为筛选级代理——因为它们没有可对标实验或规范计算，\n按纪律声明原因而非含糊给数。\n\n## 七、审计链\n\n- 判据与全部中间量：`artifacts/m9073_eedi_opt/acceptance.json`、`sensitivity.json`、\n  `pareto_front.csv`（每行含设计变量、目标、约束量、复核标志、代理-真值相对差）。\n- 图：`artifacts/m9073_eedi_opt/figures/fig1..fig5*.png`。\n- 复现：`python scripts/eedi_opt_m9073.py`（固定 seed = 20261009）；\n  `pytest tests/test_eedi_optimization_m9073.py -q` 覆盖 C1-C8 与门禁/投影。\n- 代码：`backend/physics/eedi_opt/`（design_space / hydro / chain / surrogate /\n  sensitivity / pareto / gates）、API：`backend/api/eedi_optimization.py`。\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "整篇 markdown 即源资产；sha256 见 source.hash"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题行",
          "in_report_section": "P162W1-N04 | EEDI 设计变量灵敏度与约束优化：五维设计空间 Pareto 前沿 + 可微 IMO 公式链 + 几何可行性门禁",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 72,
            "start_line": 0,
            "end_line": 0,
            "quote": "# P162W1-N04 | EEDI 设计变量灵敏度与约束优化：五维设计空间 Pareto 前沿 + 可微 IMO 公式链 + 几何可行性门禁",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "标题行；与 API title 字段同源"
        },
        {
          "asset_id": "A03",
          "asset_class": "declaration",
          "label": "仓/模块归属与运行耗时声明",
          "in_report_section": "P162W1-N04 | EEDI 设计变量灵敏度与约束优化：五维设计空间 Pareto 前沿 + 可微 IMO 公式链 + 几何可行性门禁",
          "locator": {
            "method": "char_span",
            "start_char": 74,
            "end_char": 200,
            "start_line": 2,
            "end_line": 3,
            "quote": "**仓** ship-performance-platform | **模块** `backend/physics/eedi_opt/` | **验收 C1-C8：全部 PASS**\n（运行 80.7 s，代理拟合 7.57 s，主优化 9.89 s）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "含「验收 C1-C8：全部 PASS」声明与三段耗时；本包只登记位置，不核验判定"
        },
        {
          "asset_id": "A04",
          "asset_class": "design_space",
          "label": "设计变量与盒约束表（5 变量）",
          "in_report_section": "一、案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 339,
            "end_char": 555,
            "start_line": 10,
            "end_line": 16,
            "quote": "| 变量 | 含义 | 区间 |\n|---|---|---|\n| L [m] | 垂线间长 | [150.0, 210.0] |\n| B [m] | 型宽 | [24.0, 36.0] |\n| T [m] | 吃水 | [8.5, 13.0] |\n| Cb [-] | 方型系数 | [0.74, 0.86] |\n| P [kW] | 主机装机功率（约束 P >= P_required） | [1000.0, 20000.0] |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "表头+分隔行+5 行数据；区间为原文边界，未做单位换算"
        },
        {
          "asset_id": "A05",
          "asset_class": "parameter_set",
          "label": "设计点参数（V_ref/SFC/C_F/eta_S）",
          "in_report_section": "一、案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 557,
            "end_char": 628,
            "start_line": 18,
            "end_line": 19,
            "quote": "设计点参数：V_ref = 14.0 kn、SFC = 190.0 g/kWh、\nC_F = 3.114（HFO）、eta_S = 0.99。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "四个设计点常量原文"
        },
        {
          "asset_id": "A06",
          "asset_class": "constraint_set",
          "label": "约束门限（DWT/GM/sigma/L_B/B_T/Cb-Cp）",
          "in_report_section": "一、案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 629,
            "end_char": 711,
            "start_line": 20,
            "end_line": 22,
            "quote": "约束门限：DWT >= 25000 t、GM >= 0.5 m、\nsigma <= 175 MPa、L/B >= 3.0、\nB/T <= 6.0、Cb <= Cp。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "六项门限原文；可执行实现体未随报告提供（见 A35/A37）"
        },
        {
          "asset_id": "A07",
          "asset_class": "result_block",
          "label": "参考设计点结果（DWT/GM/sigma/R_T/eta_D/J/n/P/EEDI）",
          "in_report_section": "一、案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 713,
            "end_char": 959,
            "start_line": 24,
            "end_line": 28,
            "quote": "**参考设计点**（L=180 m / B=30 m / T=10.5 m / Cb=0.82）：\nDWT = 38375 t，GM = 3.09 m，sigma = 156.6 MPa，\nR_T = 575.7 kN，eta_D = 0.637（eta_H = 1.070 · eta_0 = 0.595\n· eta_R = 1.00），J = 0.590，n = 71.4 rpm，\nP_ME,req = 6574 kW，设计点 EEDI = **7.240 g CO2/(t nm)**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "参考点全部数字原文；本包不重算、不换算"
        },
        {
          "asset_id": "A08",
          "asset_class": "context_reference",
          "label": "IMO Phase-3 参考线与「不做合规判定」声明",
          "in_report_section": "一、案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 960,
            "end_char": 1031,
            "start_line": 29,
            "end_line": 31,
            "quote": "（IMO Phase-3 参考线 4.38 g CO2/(t nm)，仅作合规性上下文，\n本节点的目标是 EEDI 最小化，不做合规判定）。\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "明确声明仅作上下文、不做合规判定 -> 下游不得据此生成合规结论"
        },
        {
          "asset_id": "A09",
          "asset_class": "method_chain",
          "label": "公式链（阻力/敞水/排水量，REAL）",
          "in_report_section": "二、怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1058,
            "end_char": 1430,
            "start_line": 34,
            "end_line": 39,
            "quote": "1. **公式链（REAL，全部复用仓内单一实现，本包不重写任何回归式）**\n   - 阻力：`backend/physics/holtrop.holtrop1984_resistance`（Holtrop-Mennen 1982 + Holtrop 1984）；\n   - 敞水：`src/b_series`（Oosterveld & van Oossanen 1975 回归）解工作点\n     `K_T(J) = T_req·J²/(rho·D²·V_a²)`（brentq 求根）；eta_H=(1-t)/(1-w)、eta_R=1、\n     eta_D = eta_H·eta_0·eta_R（代码内数值断言 eta_D ≡ P_E/P_D，相对差 < 1e-6）；\n   - 排水量：Δ = Cb·L·B·T·rho（几何恒等）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "含槽内实现引用与 eta_D ≡ P_E/P_D 数值断言"
        },
        {
          "asset_id": "A10",
          "asset_class": "method_proxy",
          "label": "筛选级工程代理（DWT/GM/sigma 单点标定）",
          "in_report_section": "二、怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1431,
            "end_char": 1697,
            "start_line": 40,
            "end_line": 43,
            "quote": "2. **筛选级工程代理（显式标注，非规范计算）**：DWT = Δ - 0.98·Δ^0.85（LWT 单点标定：\n   Δ=40 000 t -> 8 000 t）；GM = KB + BM_T - 0.60·D，BM_T = C_IT·B²/(Cb·T)、C_IT 由\n   水线面族解析积分 B(1/2, 3p+1)/24 给出；总纵应力 sigma = 1.45·M_wh/Z，\n   M_wh = 0.19·C1·L²·B·Cb（IACS UR S11 拟合形式），Z = k_Z·B·D²·(Cb+0.7)/1.52。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "报告自标「显式标注，非规范计算」；误差判定章同样声明无基准"
        },
        {
          "asset_id": "A11",
          "asset_class": "method_surrogate",
          "label": "可微近似（张量积 Chebyshev 样条）",
          "in_report_section": "二、怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1698,
            "end_char": 1863,
            "start_line": 44,
            "end_line": 47,
            "quote": "3. **可微近似**：对 R_T(L,B,T,Cb) 与 eta_D(L,B,T,Cb) 拟合**张量积 Chebyshev 样条**\n   （Chebyshev-Lobatto 节点 8^4 = 4096 个，\n   度数 4，正规方程 + 微小岭项）；EEDI 的代数部分保持解析，\n   故 5 维梯度全解析（无需差分）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "节点数 8^4=4096、度数 4 等设置原文"
        },
        {
          "asset_id": "A12",
          "asset_class": "method_sensitivity",
          "label": "灵敏度方法（四阶差分/弹性系数/Saltelli + Sobol）",
          "in_report_section": "二、怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1864,
            "end_char": 2001,
            "start_line": 48,
            "end_line": 50,
            "quote": "4. **灵敏度**：四阶中心差分（Richardson 外推）求真值链梯度作对照；无量纲弹性系数；\n   Saltelli/Jansen 估计量 + Sobol 低差异序列的全局 Sobol 指数（作用在代理上，\n   N = 4096 基样本、24576 次模型评估）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "N=4096 基样本、24576 次评估原文"
        },
        {
          "asset_id": "A13",
          "asset_class": "method_optimizer",
          "label": "优化器设置（约束 NSGA-II）",
          "in_report_section": "二、怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2002,
            "end_char": 2114,
            "start_line": 51,
            "end_line": 52,
            "quote": "5. **优化**：约束 NSGA-II（可行性优先非支配排序 + 拥挤度 + SBX/多项式变异，种群 120，\n   上限 1000 代），目标 f1 = EEDI_attained、f2 = 建造成本代理 L·B·T。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "种群 120、上限 1000 代、SBX/多项式变异原文"
        },
        {
          "asset_id": "A14",
          "asset_class": "method_gates",
          "label": "门禁与全链复核/投影",
          "in_report_section": "二、怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2115,
            "end_char": 2215,
            "start_line": 53,
            "end_line": 54,
            "quote": "6. **门禁**：几何可行性（L/B >= 3、B/T <= 6、Cb <= Cp）+ DWT/GM/sigma/功率平衡；\n   每个前沿解用**全链**复核，必要时投影（repair）到可行域。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "几何可行性 + DWT/GM/sigma/功率平衡，前沿解全链复核原文"
        },
        {
          "asset_id": "A15",
          "asset_class": "acceptance_table",
          "label": "验收判据表 C1-C8（数值 + PASS 判定）",
          "in_report_section": "三、计算结果（判据数字）",
          "locator": {
            "method": "char_span",
            "start_char": 2234,
            "end_char": 2841,
            "start_line": 58,
            "end_line": 67,
            "quote": "| 判据 | 指标 | 数值 | 判定 |\n|---|---|---|---|\n| C1 | 代理 vs 原公式最大相对误差 R_T / eta_D / EEDI | 0.021% / 0.006% / 0.027%（判据 <1%） | PASS |\n| C2 | min dEEDI/dP（20 点差分 / 解析） | 8.823e-04 / 8.823e-04 | PASS |\n| C3 | min dEEDI/dCb（设计点面，20 点） | 3.845（<0 即 FAIL） | PASS |\n| C4 | Pareto 非支配解数 | 120（判据 >=50） | PASS |\n| C5 | 前沿解满足几何+全链约束比例 | 100.0%（投影前已可行 120/120，投影 0 个） | PASS |\n| C6 | 收紧 DWT_max -> min EEDI 严格单调升 + 全成本箱包络上移；抬高 DWT_min -> 全局 min 不变但包络逐箱上移 | True / True / True | PASS |\n| C7 | 收敛代 / 末 50 代 EEDI 变化 | 第 201 代 / 0.0579%（判据 <0.1%） | PASS |\n| C8 | 解析梯度 vs 差分梯度最大相对误差（5D / 4D 设计点） | 0.000% / 0.855%（判据 <5%） | PASS |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "8 条判据原文；PASS 是报告作者的判定（claim），本包不做 verification"
        },
        {
          "asset_id": "A16",
          "asset_class": "result_block",
          "label": "Pareto 前沿汇总（N/EEDI 区间/成本区间/偏差）",
          "in_report_section": "三、计算结果（判据数字）",
          "locator": {
            "method": "char_span",
            "start_char": 2843,
            "end_char": 3050,
            "start_line": 69,
            "end_line": 72,
            "quote": "**Pareto 前沿**：N = 120，EEDI 区间 [4.652, 11.344] g CO2/(t nm)，\n成本代理 L·B·T 区间 [36302, 98273] m³；\n前沿解代理与全链 EEDI 最大相对偏差 0.03%。\n逐解明细见 `artifacts/m9073_eedi_opt/pareto_front.csv`（含 DWT/GM/sigma/P_req/L_B/B_T 与复核标志）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "含逐解明细 CSV 的引用（A31）"
        },
        {
          "asset_id": "A17",
          "asset_class": "table",
          "label": "C6 约束负控明细表",
          "in_report_section": "三、计算结果（判据数字）",
          "locator": {
            "method": "char_span",
            "start_char": 3164,
            "end_char": 3448,
            "start_line": 78,
            "end_line": 81,
            "quote": "| 收紧方式 | 参数序列 | 全局 min EEDI | 包络逐箱上移 | 包络平均位移 |\n|---|---|---|---|---|\n| 容量上界 DWT_max | [None, 50000.0, 40000.0, 32000.0] | [4.852, 5.194, 5.729, 6.586] | True | [0.0155, 0.0113, 0.0202] |\n| 载重下限 DWT_min | [25000.0, 31000.0, 37000.0] | [4.852, 4.852, 4.852] | True | [0.1884, 0.1586] |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "两组参数序列、全局 min EEDI、包络位移原文"
        },
        {
          "asset_id": "A18",
          "asset_class": "interpretation",
          "label": "C6 方向解释与被否定的镜像对称假设",
          "in_report_section": "三、计算结果（判据数字）",
          "locator": {
            "method": "char_span",
            "start_char": 3450,
            "end_char": 3661,
            "start_line": 83,
            "end_line": 86,
            "quote": "方向解释：①收紧容量上界 -> 只允许更小的船 -> 前沿整体向高 EEDI 移动（与判据 C6 文字一致）；\n②抬高载重下限 -> 全局 min EEDI 不变（最优船本来就大），但固定成本箱内要装更多载重只能加丰满度\nCb，而 Cb 升高使 EEDI 升高 -> 包络逐箱上移。**原先假设的「镜像对称（抬高下限→EEDI 下降）」被实测\n否定**，此处如实报告机制差异（这也是本节点唯一的假设修正，不影响判据通过）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "报告自述唯一假设修正（镜像对称被实测否定）；否定性结果，如实登记"
        },
        {
          "asset_id": "A19",
          "asset_class": "sensitivity_block",
          "label": "局部灵敏度弹性系数（设计点面 4D）",
          "in_report_section": "三、计算结果（判据数字）",
          "locator": {
            "method": "char_span",
            "start_char": 3663,
            "end_char": 3784,
            "start_line": 88,
            "end_line": 93,
            "quote": "**局部灵敏度（参考设计点，设计点面弹性系数 E_i = (dEEDI/dx_i)(x_i/EEDI)）**：\n\n- E_L = -0.7382\n- E_B = -0.2307\n- E_T = -0.9734\n- E_Cb = +2.1036",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "E_L/E_B/E_T/E_Cb 四条"
        },
        {
          "asset_id": "A20",
          "asset_class": "sensitivity_block",
          "label": "自由功率面弹性系数（5D，含 P）",
          "in_report_section": "三、计算结果（判据数字）",
          "locator": {
            "method": "char_span",
            "start_char": 3786,
            "end_char": 3887,
            "start_line": 95,
            "end_line": 101,
            "quote": "**自由功率面弹性系数（含 P）**：\n\n- E_L = -1.0363\n- E_B = -1.0363\n- E_T = -1.0363\n- E_Cb = -1.0363\n- E_P = +1.0000",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "五条弹性系数"
        },
        {
          "asset_id": "A21",
          "asset_class": "sensitivity_block",
          "label": "全局灵敏度 Sobol 指数（4D / 5D）",
          "in_report_section": "三、计算结果（判据数字）",
          "locator": {
            "method": "char_span",
            "start_char": 3889,
            "end_char": 4130,
            "start_line": 103,
            "end_line": 106,
            "quote": "**全局灵敏度 Sobol（设计点面 4D）**：一阶 S = { L: 0.000, B: 0.000, T: 0.000, Cb: 1.902 }；\n总效应 ST = { L: 0.000, B: 0.000, T: 0.000, Cb: 1.902 }；一阶指数和 = 1.902\n（<1 说明变量间存在交互作用）。**自由功率面 5D**：P 的一阶 S_P = 0.000、\nST_P = 0.000——装机功率自由度主导方差，这正是「P 必须由功率平衡钉住」的定量理由。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "一阶/总效应指数；原文自注「一阶指数和 = 1.902 <1」——该数值本身存疑，本包只登记不解释"
        },
        {
          "asset_id": "A22",
          "asset_class": "figure_reference",
          "label": "结果图声明（5 张内嵌图）",
          "in_report_section": "四、结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4132,
            "end_char": 4247,
            "start_line": 108,
            "end_line": 111,
            "quote": "## 四、结果图\n\n5 张内嵌图：Pareto 前沿与全链复核（1:1 对比）、收敛历史（min EEDI + 超体积）、\n代理 vs 原公式误差分布、Sobol 灵敏度（4D/5D）、DWT 约束负控与 Cb 单调性曲线（含全链",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "markdown 内只有文字声明，无图内联；二进制见 A42"
        },
        {
          "asset_id": "A23",
          "asset_class": "caveat",
          "label": "注意点 1：EEDI 简化面（非规范全量）",
          "in_report_section": "五、注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 4289,
            "end_char": 4357,
            "start_line": 116,
            "end_line": 116,
            "quote": "1. **公式链非规范全量**：EEDI 用简化面 `P·SFC·C_F/(DWT·V_ref)`（无 P_AE、f_j、f_i、f_w",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "简化面公式与同口径函数位置；缺失修正项另见 A43"
        },
        {
          "asset_id": "A24",
          "asset_class": "caveat",
          "label": "注意点 2：重量/稳性/强度为筛选级代理",
          "in_report_section": "五、注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 4436,
            "end_char": 4574,
            "start_line": 118,
            "end_line": 120,
            "quote": "2. **重量/稳性/强度是筛选级代理**：LWT、KG、剖面模数、静水/波浪弯矩比均为单点标定的\n   工程量级估计，只用于判断「门禁是否可能被突破」，**不可作为结构或稳性设计依据**；\n   完整判定需船级社规范计算与 IS Code 2008 六项衡准 + 天气衡准。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "明确「不可作为结构或稳性设计依据」；规范判定缺失另见 A44"
        },
        {
          "asset_id": "A25",
          "asset_class": "caveat",
          "label": "注意点 3：差分量化噪声实测坑",
          "in_report_section": "五、注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 4575,
            "end_char": 4760,
            "start_line": 121,
            "end_line": 123,
            "quote": "3. **差分量化噪声（实测坑）**：`Holtrop1984Output` 把 R_T 舍入到 0.01 kN，差分步长\n   h_rel < 1e-2 时梯度被量化噪声污染（h=1e-3 时设计点梯度误差可达 6%，h=1e-2 时 <=2%），\n   故 C8 取 h_rel=1e-2 + Richardson 外推。这是共享模块的输出精度问题，本包不改其行为。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "R_T 舍入 0.01 kN 导致梯度污染；报告声明本包不改共享模块行为"
        },
        {
          "asset_id": "A26",
          "asset_class": "caveat",
          "label": "注意点 4：两种导数面必须区分",
          "in_report_section": "五、注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 4761,
            "end_char": 4870,
            "start_line": 124,
            "end_line": 125,
            "quote": "4. **两种导数面必须区分**：固定装机功率时 dEEDI/dCb|_P < 0（只经 DWT 分母起作用），\n   而设计点面（P = P_req(Cb)）总导数 > 0（C3 采用后者，见上表注释与图 5 右）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "固定 P 与设计点面 dEEDI/dCb 符号相反；C3 采用后者"
        },
        {
          "asset_id": "A27",
          "asset_class": "caveat",
          "label": "注意点 5：适用范围与局限",
          "in_report_section": "五、注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 4871,
            "end_char": 5039,
            "start_line": 126,
            "end_line": 128,
            "quote": "5. **局限**：代理仅在给定盒约束内有效（Cb 0.74-0.86、L 150-210 m 等）；单一 V_ref = 14 kn；\n   固定螺旋桨几何（P/D=0.95、Ae/A0=0.55、Z=4、D/T=0.68）；成本目标为 L·B·T 体积代理，\n   不含设备价格、钢材价格与批量效应；未含破舱稳性与纵倾/吃水差耦合。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "代理有效域、固定螺旋桨几何、成本代理口径、未含耦合项"
        },
        {
          "asset_id": "A28",
          "asset_class": "error_table",
          "label": "误差判定表（6 个关键量 vs 基准）",
          "in_report_section": "六、误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 5052,
            "end_char": 5439,
            "start_line": 132,
            "end_line": 139,
            "quote": "| 关键量 | 基准 | 误差 | 是否 < 3% |\n|---|---|---|---|\n| 代理 EEDI vs 全链 EEDI（100 点随机） | Holtrop + B 系列真值链 | 最大 0.027% | 是 |\n| 代理 R_T vs Holtrop | Holtrop-Mennen 原式 | 最大 0.021% | 是 |\n| 代理 eta_D vs 敞水工作点解 | brentq 工作点 + eta 分解 | 最大 0.006% | 是 |\n| 解析梯度 vs 四阶差分（4D 设计点） | 真值链差分 | 最大 0.855% | 是 |\n| 解析梯度 vs 四阶差分（5D 自由功率） | 真值链差分 | 最大 0.000% | 是 |\n| 前沿解代理 vs 全链 EEDI | Holtrop + B 系列真值链 | 最大 0.03% | 是 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "误差数字与「是否 < 3%」原文；本包不重算"
        },
        {
          "asset_id": "A29",
          "asset_class": "error_statement",
          "label": "无实验基准量的显式声明",
          "in_report_section": "六、误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 5441,
            "end_char": 5565,
            "start_line": 141,
            "end_line": 144,
            "quote": "对「有基准的量」逐项显式回答：上述五项相对误差均 < 3%（最严者\n0.85%）。**无实验基准的量**（DWT/GM/sigma\n代理、成本代理）不给误差数字而是标注为筛选级代理——因为它们没有可对标实验或规范计算，\n按纪律声明原因而非含糊给数。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "明示 DWT/GM/sigma/成本代理无基准 -> 不给误差数字（符合精度纪律）"
        },
        {
          "asset_id": "A30",
          "asset_class": "audit_chain",
          "label": "审计链（判据/图/复现/代码位置）",
          "in_report_section": "七、审计链",
          "locator": {
            "method": "char_span",
            "start_char": 5567,
            "end_char": 6037,
            "start_line": 146,
            "end_line": 155,
            "quote": "## 七、审计链\n\n- 判据与全部中间量：`artifacts/m9073_eedi_opt/acceptance.json`、`sensitivity.json`、\n  `pareto_front.csv`（每行含设计变量、目标、约束量、复核标志、代理-真值相对差）。\n- 图：`artifacts/m9073_eedi_opt/figures/fig1..fig5*.png`。\n- 复现：`python scripts/eedi_opt_m9073.py`（固定 seed = 20261009）；\n  `pytest tests/test_eedi_optimization_m9073.py -q` 覆盖 C1-C8 与门禁/投影。\n- 代码：`backend/physics/eedi_opt/`（design_space / hydro / chain / surrogate /\n  sensitivity / pareto / gates）、API：`backend/api/eedi_optimization.py`。\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique substring of source markdown (md.count(quote) == 1)",
            "result": "resolved"
          },
          "note": "列出 artifacts、figures、repro 命令、代码模块；各条逐一登记为 A31-A41"
        },
        {
          "asset_id": "A31",
          "asset_class": "artifact_file",
          "label": "Pareto 逐解明细 CSV",
          "in_report_section": "三、计算结果（判据数字）",
          "locator": {
            "method": "char_span",
            "start_char": 2964,
            "end_char": 3050,
            "start_line": 72,
            "end_line": 72,
            "quote": "逐解明细见 `artifacts/m9073_eedi_opt/pareto_front.csv`（含 DWT/GM/sigma/P_req/L_B/B_T 与复核标志）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "artifacts/m9073_eedi_opt/pareto_front.csv",
            "probe": [
              {
                "path": "/root/ship-performance-platform/artifacts/m9073_eedi_opt/pareto_front.csv",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/artifacts/m9073_eedi_opt/pareto_front.csv",
                "exists": false
              }
            ]
          },
          "note": "报告称每行含设计变量/目标/约束量/复核标志/代理-真值差；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A32",
          "asset_class": "artifact_file",
          "label": "审计链整条：判据与全部中间量（acceptance.json + sensitivity.json + pareto_front.csv 说明）",
          "in_report_section": "七、审计链",
          "locator": {
            "method": "char_span",
            "start_char": 5577,
            "end_char": 5702,
            "start_line": 148,
            "end_line": 149,
            "quote": "- 判据与全部中间量：`artifacts/m9073_eedi_opt/acceptance.json`、`sensitivity.json`、\n  `pareto_front.csv`（每行含设计变量、目标、约束量、复核标志、代理-真值相对差）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "artifacts/m9073_eedi_opt/acceptance.json",
            "probe": [
              {
                "path": "/root/ship-performance-platform/artifacts/m9073_eedi_opt/acceptance.json",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/artifacts/m9073_eedi_opt/acceptance.json",
                "exists": false
              }
            ]
          },
          "note": "C1-C8 判据与中间量；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A33",
          "asset_class": "artifact_file",
          "label": "灵敏度 JSON（sensitivity.json）",
          "in_report_section": "七、审计链",
          "locator": {
            "method": "char_span",
            "start_char": 5577,
            "end_char": 5650,
            "start_line": 148,
            "end_line": 148,
            "quote": "- 判据与全部中间量：`artifacts/m9073_eedi_opt/acceptance.json`、`sensitivity.json`、",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "artifacts/m9073_eedi_opt/sensitivity.json",
            "probe": [
              {
                "path": "/root/ship-performance-platform/artifacts/m9073_eedi_opt/sensitivity.json",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/artifacts/m9073_eedi_opt/sensitivity.json",
                "exists": false
              }
            ]
          },
          "note": "局部/全局灵敏度原始数值；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A34",
          "asset_class": "artifact_glob",
          "label": "结果图 PNG（fig1..fig5）",
          "in_report_section": "七、审计链",
          "locator": {
            "method": "char_span",
            "start_char": 5703,
            "end_char": 5758,
            "start_line": 150,
            "end_line": 150,
            "quote": "- 图：`artifacts/m9073_eedi_opt/figures/fig1..fig5*.png`。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "artifacts/m9073_eedi_opt/figures",
            "probe": [
              {
                "path": "/root/ship-performance-platform/artifacts/m9073_eedi_opt/figures",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/artifacts/m9073_eedi_opt/figures",
                "exists": false
              }
            ]
          },
          "note": "glob 形式引用，5 个图文件；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A35",
          "asset_class": "repro_command",
          "label": "一键复跑脚本（seed = 20261009）",
          "in_report_section": "七、审计链",
          "locator": {
            "method": "char_span",
            "start_char": 5759,
            "end_char": 5819,
            "start_line": 151,
            "end_line": 151,
            "quote": "- 复现：`python scripts/eedi_opt_m9073.py`（固定 seed = 20261009）；",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "scripts/eedi_opt_m9073.py",
            "probe": [
              {
                "path": "/root/ship-performance-platform/scripts/eedi_opt_m9073.py",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/scripts/eedi_opt_m9073.py",
                "exists": false
              }
            ]
          },
          "note": "报告声明固定 seed = 20261009；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A36",
          "asset_class": "test_file",
          "label": "C1-C8 与门禁/投影测试",
          "in_report_section": "七、审计链",
          "locator": {
            "method": "char_span",
            "start_char": 5820,
            "end_char": 5888,
            "start_line": 152,
            "end_line": 152,
            "quote": "  `pytest tests/test_eedi_optimization_m9073.py -q` 覆盖 C1-C8 与门禁/投影。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "tests/test_eedi_optimization_m9073.py",
            "probe": [
              {
                "path": "/root/ship-performance-platform/tests/test_eedi_optimization_m9073.py",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/tests/test_eedi_optimization_m9073.py",
                "exists": false
              }
            ]
          },
          "note": "报告声明覆盖 C1-C8；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A37",
          "asset_class": "code_module",
          "label": "优化实现包（design_space/hydro/chain/...）",
          "in_report_section": "七、审计链",
          "locator": {
            "method": "char_span",
            "start_char": 5889,
            "end_char": 5964,
            "start_line": 153,
            "end_line": 153,
            "quote": "- 代码：`backend/physics/eedi_opt/`（design_space / hydro / chain / surrogate /",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "backend/physics/eedi_opt",
            "probe": [
              {
                "path": "/root/ship-performance-platform/backend/physics/eedi_opt",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/backend/physics/eedi_opt",
                "exists": false
              }
            ]
          },
          "note": "7 个子模块名原文：design_space / hydro / chain / surrogate / sensitivity / pareto / gates；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A38",
          "asset_class": "code_module",
          "label": "优化 API 端点模块",
          "in_report_section": "七、审计链",
          "locator": {
            "method": "char_span",
            "start_char": 5965,
            "end_char": 6036,
            "start_line": 154,
            "end_line": 154,
            "quote": "  sensitivity / pareto / gates）、API：`backend/api/eedi_optimization.py`。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "backend/api/eedi_optimization.py",
            "probe": [
              {
                "path": "/root/ship-performance-platform/backend/api/eedi_optimization.py",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/backend/api/eedi_optimization.py",
                "exists": false
              }
            ]
          },
          "note": "HTTP 接口层；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A39",
          "asset_class": "code_dependency",
          "label": "阻力实现（Holtrop-Mennen 1984）",
          "in_report_section": "二、怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1097,
            "end_char": 1190,
            "start_line": 35,
            "end_line": 35,
            "quote": "   - 阻力：`backend/physics/holtrop.holtrop1984_resistance`（Holtrop-Mennen 1982 + Holtrop 1984）；",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "backend/physics/holtrop.py",
            "probe": [
              {
                "path": "/root/ship-performance-platform/backend/physics/holtrop.py",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/backend/physics/holtrop.py",
                "exists": false
              }
            ]
          },
          "note": "公式链第一环，报告称复用仓内单一实现；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A40",
          "asset_class": "code_dependency",
          "label": "敞水实现（Wageningen B 系列）",
          "in_report_section": "二、怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1191,
            "end_char": 1252,
            "start_line": 36,
            "end_line": 36,
            "quote": "   - 敞水：`src/b_series`（Oosterveld & van Oossanen 1975 回归）解工作点",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "src/b_series",
            "probe": [
              {
                "path": "/root/ship-performance-platform/src/b_series",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/src/b_series",
                "exists": false
              }
            ]
          },
          "note": "敞水回归 + brentq 工作点求解；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A41",
          "asset_class": "code_dependency",
          "label": "EEDI 同口径函数",
          "in_report_section": "五、注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 4358,
            "end_char": 4435,
            "start_line": 117,
            "end_line": 117,
            "quote": "   与创新技术抵扣），与 `api/extended_calculations.calculate_energy_efficiency_v2` 同口径。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem existence probe at /root/ship-performance-platform, /root/tp-agent/work/m9073",
            "result": "unresolved",
            "searched": "api/extended_calculations.py",
            "probe": [
              {
                "path": "/root/ship-performance-platform/api/extended_calculations.py",
                "exists": false
              },
              {
                "path": "/root/tp-agent/work/m9073/api/extended_calculations.py",
                "exists": false
              }
            ]
          },
          "note": "报告称与简化面同口径；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A42",
          "asset_class": "figure_binary",
          "label": "5 张内嵌图（fig1..fig5 PNG 二进制）",
          "in_report_section": "四、结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4142,
            "end_char": 4193,
            "start_line": 110,
            "end_line": 110,
            "quote": "5 张内嵌图：Pareto 前沿与全链复核（1:1 对比）、收敛历史（min EEDI + 超体积）、",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform payload figure binaries",
            "result": "unresolved",
            "searched": "payload.figures[].png_base64"
          },
          "note": "平台 payload.figures 只有 name+caption（fig1_pareto_front … fig5_constraint_shift），无 png_base64 字段 -> 图二进制不可从 API 解析；资产本体不在 markdown payload 内，登记为 referenced_unresolved"
        },
        {
          "asset_id": "A43",
          "asset_class": "missing_term_set",
          "label": "EEDI 修正项 P_AE/f_j/f_i/f_w/创新技术抵扣",
          "in_report_section": "五、注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 4289,
            "end_char": 4435,
            "start_line": 116,
            "end_line": 117,
            "quote": "1. **公式链非规范全量**：EEDI 用简化面 `P·SFC·C_F/(DWT·V_ref)`（无 P_AE、f_j、f_i、f_w\n   与创新技术抵扣），与 `api/extended_calculations.calculate_energy_efficiency_v2` 同口径。",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report text explicitly declares the item out of scope / not included",
            "result": "absent"
          },
          "note": "报告明示公式链未含这些项 -> 下游不得据此生成规范 EEDI 值"
        },
        {
          "asset_id": "A44",
          "asset_class": "missing_analysis",
          "label": "船级社规范计算 + IS Code 2008 六项衡准+天气衡准",
          "in_report_section": "五、注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 4532,
            "end_char": 4574,
            "start_line": 120,
            "end_line": 120,
            "quote": "   完整判定需船级社规范计算与 IS Code 2008 六项衡准 + 天气衡准。",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report text explicitly declares the item out of scope / not included",
            "result": "absent"
          },
          "note": "报告明示这部分判定在域外（未做）"
        },
        {
          "asset_id": "A45",
          "asset_class": "missing_analysis",
          "label": "破舱稳性与纵倾/吃水差耦合",
          "in_report_section": "五、注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 5003,
            "end_char": 5039,
            "start_line": 128,
            "end_line": 128,
            "quote": "   不含设备价格、钢材价格与批量效应；未含破舱稳性与纵倾/吃水差耦合。",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report text explicitly declares the item out of scope / not included",
            "result": "absent"
          },
          "note": "报告局限第 5 条明示未含"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "all quotes are unique substrings of the markdown (md.count(quote) == 1 for 45/45 assets); pairwise-distinct quote strings: 45/45",
        "hash_recomputed_locally": "55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687",
        "hash_matches_contract": true,
        "contract_chars_match": true,
        "content_span_coverage": "92.3% of markdown characters are covered by the spans of the markdown-resident assets (A02-A30; A01=whole doc excluded)",
        "verified_claims": 0,
        "verification_note": "no claim is marked verified: verification is computed by the platform gate, not by this work package"
      }
    }
  },
  "claims": []
}
```
