# KF-RESULT wp-9763-01

## ① 本工序做了什么

**工作包**：`wp-9763-01` · 工序 `01-asset-registration`（lane A）· 只服务 report_id=`9763`。
**源报告**：《TensorFEM FSI 验证面：弹性平板颤振临界速度（Theodorsen 1935 对标）》，scenario_key=`fsi-flutter-theodorsen-verification`，平台 mission=8461，平台状态 `published`。

本工序只做一件事：把这份报告的**源资产登记成可被下游工序机器定位的清单**——确认字节哈希、把每个资产在原文里的位置钉成字符区间、逐条给出「能不能解析到本体」的机器判定与失败探针。**不做**知识抽取、**不做**报告类型分类、**不做**数值判读、**不把任何结论标成 verified（verification 由平台门计算）**。

结果规模：登记 **32 个资产 / 22 类**，其中 resolved_in_source **28** 个、referenced_unresolved **4** 个、declared_absent **0** 个。
另附 **6 项源级交叉检查**（3 consistent / 2 inconsistent / 1 unresolved），不一致项**只登记不改写**，留给下游工序裁断。

**边界自证**：`scope_boundary.report_ids_touched = ['9763']`，`upstream_artifacts_modified = false`；本单未读、未写任何其它 report_id 的报告。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证（不许凭记忆）**：`python3 scripts/kf_fetch_9763.py` → `GET {TENSOR_API_BASE}/tensor/reports/9763`，取 `markdown` 字段原样落盘 `runs/wp-9763-01/report_9763.md`。
   本地重算 `sha256 = ca29ba6f428001ddc1546e10c82b71ad1a18dcbf1c2bd09a1abd96e9760b1df3`，与契约 `source_hash` 逐字节相同；字符数 **3884** 与契约 `chars` 相同（UTF-8 字节 5848）。两项不一致则脚本直接 `FATAL` 退出（已内置硬门）。
2. **锚点定位而非抄写**：`scripts/kf_register_9763.py` 维护 32 行锚点表（asset_id / asset_class / 唯一行锚点 / 终止锚点 / 预声明 resolution）。运行时用锚点在 markdown 中做**唯一行匹配**（命中≠1 即 `SystemExit`）→ 由行偏移求 `[start_char, end_char)` → **直接从原文切片**得到 `quote`；再断言 `md.count(quote) == 1`。脚本不接受任何手写引文，也不做物理量换算。
3. **可解析性判定（探针，不猜地址）**：每个资产跑一次机器检查 `resolution_check`，结果与 `resolution` 强绑定：
   - 文本类资产 → `char_span_in_source_markdown`；
   - 代码/测试指针（A30/A31）→ 在本工作树与 TensorFEM 检出分别 `os.path.isfile` 探针；**判据 = 本工作树内能否拿到本体**，跨仓命中只作信息性证据；
   - 工具链声明（A12）→ 只有 basename，无法形成唯一地址，登记为 `unresolved` 并写明原因；
   - 图件集（A25）→ 平台 `figures` 字段条数 + 本机磁盘 glob `artifacts/fsi_flutter/fig*.png`；元数据 7 条、png 字节 0、磁盘文件 0 → `referenced_unresolved`；
   - 运行记录（A32）→ 本工作树无该测试集，不可复现 → `referenced_unresolved`。
4. **独立校验（不信本地副本）**：`scripts/kf_verify_9763.py` 在**新进程、新登录**下重新拉取 markdown，重算哈希；把 32 个 locator 逐条从**新拉取的原文**重新切片比对（`quote == md[start:end]`、行号与字符区间互证、唯一性），再跑双 schema、查 id 唯一、查 claim 证据策略、结构化扫描「verified」标记、比对产物 sha256 与信封内嵌对象、比对 docs 镜像字节一致。输出 `artifacts/wp-9763-01/verification.json`，本次 **14/14 项 pass，overall=PASS**。
5. **不变量测试（含反向对照）**：`pytest tests/test_kf_wp9763.py -q` → **24 passed**。除正向断言外含 10 个**反向对照**：篡改引文里的一个数字（4.4721→4.4722）、平移字符区间 1 位、行号漂移、制造重复 id、给 claim 去掉证据、塞入 `verified` 标记、改动信封内嵌 manifest、删掉 `integrity` 段、把 resolution 写成非法枚举值——每一种都被对应检查判红，证明这些检查是活的而不是只跑通。
6. **出图与复现**：`scripts/kf_figures_9763.py` 从 manifest / verification 读数生成 3 张图（无手输数字）；`asset_manifest.json` 的 sha256 为 `f5d18ed17c8602b83af807602abfe6eb614a51909b01e20c402e9947fd550870`，清空产物后按复跑命令重建逐字节相同（无时间戳/随机量污染）。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/wp-9763-01/asset_manifest.json` | 主产物（5848 字节源文本 → 32 资产，28 resolved / 4 unresolved / 0 absent，6 项交叉检查）；sha256 `f5d18ed17c8602b83af807602abfe6eb614a51909b01e20c402e9947fd550870` |
| `docs/kf/wp-9763-01/asset_manifest.json` | 主产物的**字节一致**镜像（push 门会滤除 `artifacts/**` 与 `runs/**`，`docs/` 才进仓） |
| `runs/wp-9763-01/kf_result.wp-9763-01.json` / `docs/kf/wp-9763-01/kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs），`verification_status = not_verified` |
| `artifacts/wp-9763-01/verification.json` / `docs/kf/wp-9763-01/verification.json` | 14 项验收自检逐项结果，overall=PASS |
| `docs/kf/wp-9763-01/figures/fig1_asset_inventory.png` | 图1 资产类别 × 可解析状态（32 资产 / 22 类） |
| `docs/kf/wp-9763-01/figures/fig2_locator_coverage.png` | 图2 32 条 locator 在 3884 字符原文上的覆盖地图 |
| `docs/kf/wp-9763-01/figures/fig3_verification_board.png` | 图3 验收自检状态板 + 交叉检查状态板 |
| `runs/wp-9763-01/report_9763.md` / `report_9763.json` | 源证据快照（markdown 与 API 原始响应，逐字节） |
| `schemas/asset_manifest.v1.wp-9763-01.schema.json` | 本工序 manifest 形状约束（版本化源码，供 `schema_pass` 可复现；不改动 448 工序的既有 schema） |
| `scripts/kf_fetch_9763.py` / `kf_register_9763.py` / `kf_verify_9763.py` / `kf_figures_9763.py` / `kf_report_9763.py` | 取证 / 登记 / 校验 / 出图 / 报报告，一键可复跑 |
| `tests/test_kf_wp9763.py` | 24 项不变量测试（含 10 个反向对照） |
| `docs/kf/wp-9763-01/KF-RESULT-wp-9763-01.md` | 本报告正文 |

**资产类别计数**：`{"document": 1, "heading": 1, "provenance_lineage": 1, "narrative": 1, "parameter_table": 1, "parameter_set": 1, "method_statement": 2, "formula": 3, "code_pointer": 2, "results_table": 4, "acceptance_criterion": 4, "numeric_anchor": 1, "convergence_statement": 1, "negative_control": 1, "figure_declaration": 1, "figure_set": 1, "limitation_set": 1, "pitfall_set": 1, "roadmap": 1, "criteria_table": 1, "test_pointer": 1, "run_command": 1}`

## ④ 证据定位表（claim/字段 → 原文引文）

下表每一行的 `quote` 都是报告 9763 markdown 的**唯一子串**（`md.count(quote) == 1`，由 `kf_verify_9763.py` 在重新拉取的原文上二次确认），并给出 `[start_char, end_char)` 与行区间。长引文在此处截断显示，完整 quote 见 `asset_manifest.json`（本表由脚本从 manifest 读数生成，未经手工转写）。

| asset_id | class | resolution | 定位 | 原文片段（逐字取自 report 9763） |
|---|---|---|---|---|
| A01 | document | resolved_in_source | L0-161 · [0, 3884) | `# TensorFEM 流固耦合（FSI）验证面：弹性平板颤振临界速度 ⏎  ⏎ ## P87W2-N05 \| Mission 8461 ⏎  ⏎ ## 1. 案例介绍 ⏎  ⏎ ### 物理…` |
| A02 | heading | resolved_in_source | L0-0 · [0, 35) | `# TensorFEM 流固耦合（FSI）验证面：弹性平板颤振临界速度` |
| A03 | provenance_lineage | resolved_in_source | L2-2 · [37, 64) | `## P87W2-N05 \| Mission 8461` |
| A04 | narrative | resolved_in_source | L7-7 · [87, 257) | `颤振是飞行器/桥梁/涡轮叶片等柔性结构在气流中发生的自激振动失稳现象。Theodorsen (1935) 首次给出了二维典型截面（plunge + pitch）的精确颤振解析解，Dowell …` |
| A05 | parameter_table | resolved_in_source | L10-20 · [269, 545) | `\| 参数 \| 符号 \| 值 \| 单位 \| ⏎ \|---\|---\|---\|---\| ⏎ \| 平板长度 \| L \| 1.0 \| m \| ⏎ \| 平板宽度 \| b \| 0.2 \| m \| ⏎ \| 平…` |
| A06 | parameter_set | resolved_in_source | L22-26 · [547, 665) | `### 典型截面参数（无量纲） ⏎ - 质量比 μ = m/(πρ_f b²) ∈ {5, 10, 20, 50} ⏎ - 频率比 σ = ω_h/ω_α = 0.2 ⏎ - 回转半径比 r_…` |
| A07 | method_statement | resolved_in_source | L30-34 · [677, 905) | `### 耦合策略 ⏎ 分区弱耦合（partitioned weak coupling）： ⏎ 1. **气动力模型**：Theodorsen 函数 C(k) = H₁⁽²⁾(k)/[H₁⁽²⁾…` |
| A08 | method_statement | resolved_in_source | L36-37 · [907, 958) | `### 颤振判据 ⏎ 特征值分析：求解 4×4 状态空间特征值问题，当最大实部 > 0 时判定为颤振失稳。` |
| A09 | formula | resolved_in_source | L40-40 · [969, 1020) | `- Theodorsen 颤振速度：U_cr/(bω_α) = 2√μ（canonical case）` |
| A10 | formula | resolved_in_source | L41-41 · [1021, 1057) | `- 颤振频率：ω_fl/ω_α ≈ √σ = √0.2 ≈ 0.4472` |
| A11 | formula | resolved_in_source | L42-42 · [1058, 1114) | `- 增长率：σ ≈ 0.3(U/U_cr - 1)（超临界），σ ≈ -0.1(1 - U/U_cr)（亚临界）` |
| A12 | code_pointer | resolved_in_source | L44-48 · [1116, 1268) | `### 工具链 ⏎ - TensorFEM `theodorsen.py`：Theodorsen 函数、特征值求解器、时间推进 ⏎ - TensorFEM `fsi_flutter.py`：F…` |
| A13 | results_table | resolved_in_source | L54-59 · [1316, 1528) | `\| μ \| U_cr (TensorFEM) \| U_cr (Theodorsen 2√μ) \| 误差 \| ⏎ \|---\|---\|---\|---\| ⏎ \| 5 \| 4.4721 \| 4.472…` |
| A14 | acceptance_criterion | resolved_in_source | L61-61 · [1530, 1569) | `**判据 (a)：误差 < 5% → ✅ PASS（最大误差 0.00%）**` |
| A15 | results_table | resolved_in_source | L65-70 · [1585, 1802) | `\| μ \| ω_fl/ω_α (TensorFEM) \| ω_fl/ω_α (Theodorsen √σ) \| 误差 \| ⏎ \|---\|---\|---\|---\| ⏎ \| 5 \| 0.4472 …` |
| A16 | acceptance_criterion | resolved_in_source | L72-72 · [1804, 1843) | `**判据 (b)：误差 < 3% → ✅ PASS（最大误差 0.00%）**` |
| A17 | results_table | resolved_in_source | L76-81 · [1865, 2082) | `\| U/U_cr \| σ (TensorFEM) \| σ (Dowell 线性) \| 误差 \| ⏎ \|---\|---\|---\|---\| ⏎ \| 1.1 \| 0.030000 \| 0.03000…` |
| A18 | acceptance_criterion | resolved_in_source | L83-83 · [2084, 2124) | `**判据 (c)：误差 < 10% → ✅ PASS（最大误差 0.00%）**` |
| A19 | results_table | resolved_in_source | L87-91 · [2141, 2256) | `\| U/U_cr \| σ \| 稳定性 \| ⏎ \|---\|---\|---\| ⏎ \| 0.5 \| -0.050000 \| ✅ 衰减 \| ⏎ \| 0.7 \| -0.030000 \| ✅ 衰减 \| ⏎…` |
| A20 | acceptance_criterion | resolved_in_source | L93-93 · [2258, 2283) | `**判据 (d)：σ < 0 → ✅ PASS**` |
| A21 | numeric_anchor | resolved_in_source | L95-102 · [2285, 2410) | `### (e) 质量比标度律 ⏎  ⏎ 对 μ ∈ [1, 100] 进行 log-log 线性拟合： ⏎ - 拟合指数：**0.500000** ⏎ - 理论值：0.5 ⏎ - 误差：**0…` |
| A22 | convergence_statement | resolved_in_source | L104-108 · [2412, 2495) | `### (f) 时间步收敛性 ⏎  ⏎ 时间步 Δt 从 0.05 减半至 0.002，增长率变化 < 0.001（远小于 2%）。 ⏎  ⏎ **判据 (f)：→ ✅ PASS**` |
| A23 | negative_control | resolved_in_source | L110-114 · [2497, 2572) | `### (g) 负控 ⏎  ⏎ μ = 10⁶（ρ_f → 0 极限）：U_cr = 2000.0 → ∞，无颤振。 ⏎  ⏎ **判据 (g)：→ ✅ PASS**` |
| A24 | figure_declaration | resolved_in_source | L118-118 · [2585, 2607) | `见内嵌 figures（7 张论文级图表）。` |
| A25 | figure_set | referenced_unresolved | L159-159 · [3788, 3831) | `- 图表：`artifacts/fsi_flutter/fig[1-7]_*.png`` |
| A26 | limitation_set | resolved_in_source | L122-127 · [2620, 2871) | `### 局限性与适用范围 ⏎ 1. **2D 典型截面**：本验证基于无限展长假设，不考虑三维效应（展向模态、翼尖涡） ⏎ 2. **线性气动力**：Theodorsen 理论仅适用于小扰动、…` |
| A27 | pitfall_set | resolved_in_source | L129-132 · [2873, 3018) | `### 踩过的坑 ⏎ 1. Theodorsen 函数的符号约定：不同文献对 G(k) 的符号定义不同（Hankel 函数 H⁽¹⁾ vs H⁽²⁾），需统一 ⏎ 2. 无量纲化：确保所有物理…` |
| A28 | roadmap | resolved_in_source | L134-138 · [3020, 3124) | `### 后续改进方向 ⏎ 1. 实现完整的 TensorLBM D2Q9 流场求解器替代 Theodorsen 代理模型 ⏎ 2. 加入结构阻尼项 ⏎ 3. 扩展到 3D 平板颤振（有限展长）…` |
| A29 | criteria_table | resolved_in_source | L142-153 · [3138, 3546) | `\| 判据 \| 要求 \| 实际 \| 结果 \| ⏎ \|---\|---\|---\|---\| ⏎ \| (a) U_cr 误差 \| < 5% \| 0.00% \| ✅ PASS \| ⏎ \| (b) ω_fl…` |
| A30 | code_pointer | referenced_unresolved | L157-157 · [3556, 3622) | `- 代码：`src/tensorfem/theodorsen.py`, `src/tensorfem/fsi_flutter.py`` |
| A31 | test_pointer | referenced_unresolved | L158-158 · [3623, 3787) | `- 测试：`tests/test_fsi_flutter_critical_speed.py`, `tests/test_fsi_flutter_frequency.py`, `tests/t…` |
| A32 | run_command | referenced_unresolved | L160-160 · [3832, 3883) | `- 测试运行：`pytest tests/test_fsi_*.py -v` → 104 passed` |

### ④b 源级交叉检查（6 项）

| check_id | result | 检查内容 | 证据（原文行） |
|---|---|---|---|
| C1_contract_source_identity | consistent | 契约 source_hash / chars 与实测 markdown 一致 | — |
| C2_figure_count_agreement | consistent | A24 正文声明 7 张 vs 平台 figures 字段条数 vs A25 fig[1-7] 命名 | `见内嵌 figures（7 张论文级图表）。` (L118)<br>`- 图表：`artifacts/fsi_flutter/fig[1-7]_*.png`` (L159) |
| C3_pytest_count_conflict | inconsistent | 判据 (h) 与审计链的 pytest 计数互相矛盾（60 vs 104） | `\| (h) pytest 覆盖 \| 4 文件全 PASS \| 60 tests PASS \| ✅ PASS \|` (L151)<br>`- 测试运行：`pytest tests/test_fsi_*.py -v` → 104 passed` (L160) |
| C4_metric_naming_drift | inconsistent | 第 (f) 节标题「时间步收敛性」与第 6 节表行「网格收敛」用词不一致 | `### (f) 时间步收敛性` (L104)<br>`\| (f) 网格收敛 \| < 2% \| < 0.01% \| ✅ PASS \|` (L149) |
| C5_arith_reproduction | consistent | 表 (a)(b)(c)(d)(g) 数值 vs 报告自述公式的算术复算（4-6 位小数内） | `- Theodorsen 颤振速度：U_cr/(bω_α) = 2√μ（canonical case）` (L40)<br>`- 增长率：σ ≈ 0.3(U/U_cr - 1)（超临界），σ ≈ -0.1(1 - U/U_cr)（亚临界）` (L42)<br>`\| 5 \| 4.4721 \| 4.4721 \| 0.0000% \|` (L56)<br>`μ = 10⁶（ρ_f → 0 极限）：U_cr = 2000.0 → ∞，无颤振。` (L112) |
| C6_reference_column_circularity | unresolved | 表 (a)(b) 的「解析解/Theodorsen」列与报告关键公式① ② 同式，数值逐位相同：0.0000% 误差可能来自公式自比较而非独立求解 | `- Theodorsen 颤振速度：U_cr/(bω_α) = 2√μ（canonical case）` (L40)<br>`- 颤振频率：ω_fl/ω_α ≈ √σ = √0.2 ≈ 0.4472` (L41)<br>`\| 5 \| 4.4721 \| 4.4721 \| 0.0000% \|` (L56)<br>`\| 5 \| 0.4472 \| 0.4472 \| 0.0000% \|` (L67) |

要点（只登记事实，不下结论）：
- **C3**：第 6 节判据 (h) 写「60 tests PASS」，审计链写「104 passed」，同文互不一致 —— 本工序**不取舍、不改写上游**。
- **C4**：第 (f) 节标题「时间步收敛性」，第 6 节表行却写「网格收敛」——用词漂移，需下游确认所指。
- **C5**：把表 (a)(b)(c)(d)(g) 的数字按**报告自己写的公式**（关键公式①②③与负控 2√μ）复算，最大偏差 0（4-6 位小数内）——这只说明报告内部算术自洽，**不构成对物理/方法的独立验证**。
- **C6**（unresolved，留给下游）：表 (a)(b) 的「解析解」列与关键公式①②**同式**，两列在 4 位小数上逐项相同，因此 0.0000% 误差存在「公式自比较」的可能；本工序不做判读，仅保留可定位证据。

## ⑤ 注意点与局限

1. **工序边界**：本单只登记资产，不做抽取与判读。`cross_checks` 里 `inconsistent` / `unresolved` 的条目是**交给下游的证据包，不是本工序的结论**；报告的 ✅ PASS 自评一律**未采信、未改判**。
2. **解析判据是「本工作树可达性」**：A30/A31 指向的 TensorFEM 源码与测试在**工作树外的同级检出**中探针命中（信息性证据），但按本工序判据仍登记为 `referenced_unresolved`；A25 的 7 张 png 在平台 payload（仅 name+caption，无 png 字节）与本机磁盘都拿不到，图件本体不可核。**下游若要做图件级核验，须先解决 png 取回。**
3. **未执行的检查**：TensorFEM 侧 `pytest tests/test_fsi_*.py` 未在本工序执行（跨仓、超出工作包范围），因此报告宣称的「104 passed / 60 tests」**本工序无法证实也无法证伪**，只登记矛盾。
4. **平台字段依赖**：`figures` 条数（7）与 mission 号取自平台 payload，未与 mission 表交叉断言。
5. **图件字体**：容器无中文字体，图中标签使用 ASCII；中文说明在本报告与 manifest 的 `label`/`note` 字段。
6. **不做的事**：未在任何产物里写 `verified`（`nothing_marked_verified` 检查覆盖 manifest 与信封两棵树）；未修改上游与本工序外任何文件；未 push。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 判据 | 结果 |
|---|---|---|
| valid_json | 产物为合法 JSON（manifest + 信封） | ✅ |
| schema_pass | 按 schemas/asset_manifest.v1.wp-9763-01.schema.json 与 schemas/kf_result.v1.schema.json 双 schema 校验通过 | ✅ |
| source_locator_resolvable | 32 个 locator 逐条从**重新拉取**的原文切片复现，且 quote 在全文唯一 | ✅ |
| source_hash_matches | 重新登录重新拉取 markdown，sha256 = 契约 source_hash | ✅ |
| no_duplicate_ids | 32 个 asset_id 无重复 | ✅ |
| all_claims_have_evidence_or_explicit_unresolved_status | claims 为空数组（契约允许），策略检查空集通过；cross_checks 中不确定项显式标 unresolved | ✅ |

**补充自检（非契约项，14 项全量）**

| check | result |
|---|---|
| valid_json | ✅ pass |
| schema_pass | ✅ pass |
| source_hash_matches | ✅ pass |
| source_locator_resolvable | ✅ pass |
| all_assets_span_within_source | ✅ pass |
| no_duplicate_ids | ✅ pass |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ pass |
| nothing_marked_verified | ✅ pass |
| artifact_hash_matches_envelope | ✅ pass |
| durable_mirror_identical | ✅ pass |
| envelope_source_hash_equals_manifest_hash | ✅ pass |
| scope_single_report | ✅ pass |
| cross_checks_present | ✅ pass |
| cross_check_quotes_locate | ✅ pass |

无失败项；`wp-9763-01` 验收自检 overall=PASS。若上述任一项为 ❌，本段会如实标红而不粉饰（本单无此情况）。

## ⑦ 误差判定（关键量 vs 基准，逐项）

本工序不产生物理量，因此**没有物理基准可比**；可判定的量是完整性度量，逐项列如下（基准=契约声明值/平台原文，实际=程序化实测）：

| 量 | 基准 | 实测 | 偏差 | 是否 <3% |
|---|---|---|---|---|
| markdown sha256 | 契约 `ca29ba6f428001dd…` | 独立重取 `ca29ba6f428001dd…` | 0（逐字节相同） | ✅ 是（0%） |
| markdown 字符数 | 契约 3884 | 实测 3884 | 0 | ✅ 是（0%） |
| locator 可解析率 | 32/32 | 32/32（重新切片全部复现） | 0 失败 | ✅ 是（0%） |
| quote 唯一性 | 100% | 100%（32/32） | 0 | ✅ 是（0%） |
| schema 校验 | 0 违规 | 0 违规（双 schema） | 0 | ✅ 是（0%） |
| 产物镜像一致性 | 字节一致 | 字节一致（sha256 `f5d18ed17c8602b8…`） | 0 | ✅ 是（0%） |

**显式回答「是否 <3%」**：上述完整性度量**全部为精确 0 偏差**（<3% 成立）。但必须同时声明：**这 6 项不是精度指标**——报告 9763 声称的 U_cr / ω_fl / 增长率 0.00% 误差**本工序未复算、未采信**，其与 Theodorsen 解析解的对比是否成立属下游核验工序的职责（见 ④b 的 C6 线索）。

## 复跑命令（工作树根）

```bash
python3 scripts/kf_fetch_9763.py && python3 scripts/kf_register_9763.py && python3 scripts/kf_verify_9763.py && python3 scripts/kf_figures_9763.py && python3 scripts/kf_report_9763.py && python3 -m pytest tests/test_kf_wp9763.py -q
```

## 结果信封（本报告唯一 json 代码块，门禁按此解析）

```json
{
  "package_id": "wp-9763-01",
  "task_type": "01-asset-registration",
  "report_id": "9763",
  "provenance": {
    "source_uri": "tensor://reports/9763",
    "source_field": "markdown",
    "source_hash": "sha256:ca29ba6f428001ddc1546e10c82b71ad1a18dcbf1c2bd09a1abd96e9760b1df3",
    "source_chars": 3884,
    "source_bytes_utf8": 5848,
    "source_title": "TensorFEM FSI 验证面：弹性平板颤振临界速度（Theodorsen 1935 对标）",
    "scenario_key": "fsi-flutter-theodorsen-verification",
    "contract_version": "1.0",
    "lane": "A",
    "work_package": "wp-9763-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9763",
    "local_copy": "runs/wp-9763-01/report_9763.md",
    "generator": "scripts/kf_register_9763.py",
    "verifier": "scripts/kf_verify_9763.py",
    "verification_status": "not_verified",
    "artifact_path": "artifacts/wp-9763-01/asset_manifest.json",
    "artifact_sha256": "f5d18ed17c8602b83af807602abfe6eb614a51909b01e20c402e9947fd550870",
    "artifact_bytes": 45223,
    "notes": "asset registration only; no claim extraction, nothing marked verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-9763-01",
      "task_type": "01-asset-registration",
      "report_id": "9763",
      "source": {
        "uri": "tensor://reports/9763",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "ca29ba6f428001ddc1546e10c82b71ad1a18dcbf1c2bd09a1abd96e9760b1df3",
        "chars": 3884,
        "bytes_utf8": 5848,
        "title": "TensorFEM FSI 验证面：弹性平板颤振临界速度（Theodorsen 1935 对标）",
        "scenario_key": "fsi-flutter-theodorsen-verification",
        "platform_id": 9763,
        "platform_mission_id": 8461,
        "platform_status": "published",
        "platform_tags": [
          "FSI",
          "flutter",
          "Theodorsen",
          "TensorFEM",
          "aeroelasticity",
          "verification",
          "P87W2-N05"
        ],
        "platform_figures": [
          {
            "name": "fig1_critical_velocity",
            "caption": "Flutter critical velocity U_cr/(b·ω_α) vs mass ratio μ. Red circles: TensorFEM FSI; dashed: Theodorsen (1935) U_cr = 2√μ. Error < 0.01%."
          },
          {
            "name": "fig2_flutter_frequency",
            "caption": "Flutter frequency ratio ω_fl/ω_α vs mass ratio. Blue: TensorFEM; dashed: Theodorsen √σ = 0.4472. Error < 0.01%."
          },
          {
            "name": "fig3_growth_rate",
            "caption": "Growth rate σ/ω_α vs U/U_cr for μ=10. Blue: TensorFEM; red dashed: Dowell (1995). Green: subcritical (stable); red: supercritical (unstable)."
          },
          {
            "name": "fig4_mass_ratio_scaling",
            "caption": "Log-log U_cr vs μ: scaling exponent = 0.500000 (error < 0.01% vs theoretical 0.5)."
          },
          {
            "name": "fig5_time_histories",
            "caption": "Pitch response α(t) at four velocities showing decay (U/U_cr=0.7) and growth (U/U_cr=1.1, 1.5)."
          },
          {
            "name": "fig6_theodorsen_function",
            "caption": "Theodorsen function C(k) = F(k) + iG(k): (a) F(k) and |G(k)|; (b) |C(k)| and phase."
          },
          {
            "name": "fig7_eigenvalue_map",
            "caption": "Eigenvalue map: blue=stable (U<U_cr), green=critical, red=unstable (U>U_cr)."
          }
        ],
        "contract_hash_match": true,
        "contract_chars_match": true,
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9763",
        "local_copy": "runs/wp-9763-01/report_9763.md"
      },
      "counts": {
        "assets": 32,
        "by_class": {
          "document": 1,
          "heading": 1,
          "provenance_lineage": 1,
          "narrative": 1,
          "parameter_table": 1,
          "parameter_set": 1,
          "method_statement": 2,
          "formula": 3,
          "code_pointer": 2,
          "results_table": 4,
          "acceptance_criterion": 4,
          "numeric_anchor": 1,
          "convergence_statement": 1,
          "negative_control": 1,
          "figure_declaration": 1,
          "figure_set": 1,
          "limitation_set": 1,
          "pitfall_set": 1,
          "roadmap": 1,
          "criteria_table": 1,
          "test_pointer": 1,
          "run_command": 1
        },
        "by_resolution": {
          "resolved_in_source": 28,
          "referenced_unresolved": 4
        },
        "resolved_in_source": 28,
        "referenced_unresolved": 4,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文）",
          "in_report_section": "# TensorFEM 流固耦合（FSI）验证面：弹性平板颤振临界速度",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 3884,
            "start_line": 0,
            "end_line": 161,
            "quote": "# TensorFEM 流固耦合（FSI）验证面：弹性平板颤振临界速度\n\n## P87W2-N05 | Mission 8461\n\n## 1. 案例介绍\n\n### 物理背景\n颤振是飞行器/桥梁/涡轮叶片等柔性结构在气流中发生的自激振动失稳现象。Theodorsen (1935) 首次给出了二维典型截面（plunge + pitch）的精确颤振解析解，Dowell (1995) 教科书系统总结了该问题的数值方法。本验证面实现 TensorFEM 与 Theodorsen 理论的弱耦合 FSI 框架，对标解析解。\n\n### 几何与参数\n| 参数 | 符号 | 值 | 单位 |\n|---|---|---|---|\n| 平板长度 | L | 1.0 | m |\n| 平板宽度 | b | 0.2 | m |\n| 平板厚度 | h | 0.01 | m |\n| 弹性模量 | E | 70 | GPa |\n| 结构密度 | ρ_s | 2700 | kg/m³ |\n| 泊松比 | ν | 0.33 | - |\n| 流体密度 | ρ_f | 1.225 | kg/m³ |\n| 动力粘度 | μ | 1.8×10⁻⁵ | Pa·s |\n| 流速范围 | U | [5, 50] | m/s |\n\n### 典型截面参数（无量纲）\n- 质量比 μ = m/(πρ_f b²) ∈ {5, 10, 20, 50}\n- 频率比 σ = ω_h/ω_α = 0.2\n- 回转半径比 r_α = 0.5\n- 静不平衡 x_α = 0（对称截面）\n\n## 2. 方法\n\n### 耦合策略\n分区弱耦合（partitioned weak coupling）：\n1. **气动力模型**：Theodorsen 函数 C(k) = H₁⁽²⁾(k)/[H₁⁽²⁾(k) + iH₀⁽²⁾(k)]，基于 Bessel 函数精确计算\n2. **结构模型**：2-DOF 典型截面（plunge h + pitch α），Euler-Bernoulli 梁单元\n3. **时间推进**：Staggered 格式，Δt = 0.01（无量纲）\n\n### 颤振判据\n特征值分析：求解 4×4 状态空间特征值问题，当最大实部 > 0 时判定为颤振失稳。\n\n### 关键公式\n- Theodorsen 颤振速度：U_cr/(bω_α) = 2√μ（canonical case）\n- 颤振频率：ω_fl/ω_α ≈ √σ = √0.2 ≈ 0.4472\n- 增长率：σ ≈ 0.3(U/U_cr - 1)（超临界），σ ≈ -0.1(1 - U/U_cr)（亚临界）\n\n### 工具链\n- TensorFEM `theodorsen.py`：Theodorsen 函数、特征值求解器、时间推进\n- TensorFEM `fsi_flutter.py`：FSI 验证框架\n- NumPy/SciPy：Bessel 函数、FFT、多项式拟合\n- Matplotlib：论文级图表\n\n## 3. 计算结果\n\n### (a) 颤振临界速度 vs Theodorsen 解析解\n\n| μ | U_cr (TensorFEM) | U_cr (Theodorsen 2√μ) | 误差 |\n|---|---|---|---|\n| 5 | 4.4721 | 4.4721 | 0.0000% |\n| 10 | 6.3246 | 6.3246 | 0.0000% |\n| 20 | 8.9443 | 8.9443 | 0.0000% |\n| 50 | 14.1421 | 14.1421 | 0.0000% |\n\n**判据 (a)：误差 < 5% → ✅ PASS（最大误差 0.00%）**\n\n### (b) 颤振频率\n\n| μ | ω_fl/ω_α (TensorFEM) | ω_fl/ω_α (Theodorsen √σ) | 误差 |\n|---|---|---|---|\n| 5 | 0.4472 | 0.4472 | 0.0000% |\n| 10 | 0.4472 | 0.4472 | 0.0000% |\n| 20 | 0.4472 | 0.4472 | 0.0000% |\n| 50 | 0.4472 | 0.4472 | 0.0000% |\n\n**判据 (b)：误差 < 3% → ✅ PASS（最大误差 0.00%）**\n\n### (c) 振幅增长律（超临界）\n\n| U/U_cr | σ (TensorFEM) | σ (Dowell 线性) | 误差 |\n|---|---|---|---|\n| 1.1 | 0.030000 | 0.030000 | 0.00% |\n| 1.2 | 0.060000 | 0.060000 | 0.00% |\n| 1.3 | 0.090000 | 0.090000 | 0.00% |\n| 1.5 | 0.150000 | 0.150000 | 0.00% |\n\n**判据 (c)：误差 < 10% → ✅ PASS（最大误差 0.00%）**\n\n### (d) 亚临界响应\n\n| U/U_cr | σ | 稳定性 |\n|---|---|---|\n| 0.5 | -0.050000 | ✅ 衰减 |\n| 0.7 | -0.030000 | ✅ 衰减 |\n| 0.9 | -0.010000 | ✅ 衰减 |\n\n**判据 (d)：σ < 0 → ✅ PASS**\n\n### (e) 质量比标度律\n\n对 μ ∈ [1, 100] 进行 log-log 线性拟合：\n- 拟合指数：**0.500000**\n- 理论值：0.5\n- 误差：**0.0000%**\n\n**判据 (e)：指数误差 < 2% → ✅ PASS**\n\n### (f) 时间步收敛性\n\n时间步 Δt 从 0.05 减半至 0.002，增长率变化 < 0.001（远小于 2%）。\n\n**判据 (f)：→ ✅ PASS**\n\n### (g) 负控\n\nμ = 10⁶（ρ_f → 0 极限）：U_cr = 2000.0 → ∞，无颤振。\n\n**判据 (g)：→ ✅ PASS**\n\n## 4. 结果图\n\n见内嵌 figures（7 张论文级图表）。\n\n## 5. 注意点\n\n### 局限性与适用范围\n1. **2D 典型截面**：本验证基于无限展长假设，不考虑三维效应（展向模态、翼尖涡）\n2. **线性气动力**：Theodorsen 理论仅适用于小扰动、不可压（Ma < 0.3）\n3. **无阻尼**：未考虑结构阻尼，实际结构中阻尼会提高颤振速度\n4. **弱耦合**：分区求解可能存在耦合误差，强耦合（monolithic）方法更精确但计算代价更高\n5. **经验近似**：增长率公式 σ = 0.3(U/U_cr - 1) 是临界点附近的线性近似，远离临界时误差增大\n\n### 踩过的坑\n1. Theodorsen 函数的符号约定：不同文献对 G(k) 的符号定义不同（Hankel 函数 H⁽¹⁾ vs H⁽²⁾），需统一\n2. 无量纲化：确保所有物理量正确归一化，特别是质量比 μ 的定义\n3. FFT 频率提取：时间窗口长度影响频率分辨率，需跳过初始瞬态\n\n### 后续改进方向\n1. 实现完整的 TensorLBM D2Q9 流场求解器替代 Theodorsen 代理模型\n2. 加入结构阻尼项\n3. 扩展到 3D 平板颤振（有限展长）\n4. 强耦合 FSI 实现\n\n## 6. 误差判定\n\n| 判据 | 要求 | 实际 | 结果 |\n|---|---|---|---|\n| (a) U_cr 误差 | < 5% | 0.00% | ✅ PASS |\n| (b) ω_fl 误差 | < 3% | 0.00% | ✅ PASS |\n| (c) σ 误差 | < 10% | 0.00% | ✅ PASS |\n| (d) 亚临界 σ < 0 | σ < 0 | σ = -0.01 ~ -0.05 | ✅ PASS |\n| (e) 标度指数误差 | < 2% | 0.00% | ✅ PASS |\n| (f) 网格收敛 | < 2% | < 0.01% | ✅ PASS |\n| (g) 负控 | U_cr → ∞ | U_cr = 2000 | ✅ PASS |\n| (h) pytest 覆盖 | 4 文件全 PASS | 60 tests PASS | ✅ PASS |\n\n**全部 8 项判据通过。**\n\n## 审计链\n\n- 代码：`src/tensorfem/theodorsen.py`, `src/tensorfem/fsi_flutter.py`\n- 测试：`tests/test_fsi_flutter_critical_speed.py`, `tests/test_fsi_flutter_frequency.py`, `tests/test_fsi_amplitude_growth.py`, `tests/test_fsi_mass_ratio_scaling.py`\n- 图表：`artifacts/fsi_flutter/fig[1-7]_*.png`\n- 测试运行：`pytest tests/test_fsi_*.py -v` → 104 passed\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "整篇 markdown 即源资产本体；sha256 见 source.hash，与契约 source_hash 一致"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题（H1）",
          "in_report_section": "# TensorFEM 流固耦合（FSI）验证面：弹性平板颤振临界速度",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 35,
            "start_line": 0,
            "end_line": 0,
            "quote": "# TensorFEM 流固耦合（FSI）验证面：弹性平板颤振临界速度",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "标题行；与平台 title 字段同源（逐字一致）"
        },
        {
          "asset_id": "A03",
          "asset_class": "provenance_lineage",
          "label": "任务谱系行（P87W2-N05 / Mission 8461）",
          "in_report_section": "## P87W2-N05 | Mission 8461",
          "locator": {
            "method": "char_span",
            "start_char": 37,
            "end_char": 64,
            "start_line": 2,
            "end_line": 2,
            "quote": "## P87W2-N05 | Mission 8461",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "报告内声明的节点号与 mission 号；仅登记，不与平台 mission 表交叉断言"
        },
        {
          "asset_id": "A04",
          "asset_class": "narrative",
          "label": "物理背景（颤振现象 + Theodorsen 1935 / Dowell 1995 出处）",
          "in_report_section": "### 物理背景",
          "locator": {
            "method": "char_span",
            "start_char": 87,
            "end_char": 257,
            "start_line": 7,
            "end_line": 7,
            "quote": "颤振是飞行器/桥梁/涡轮叶片等柔性结构在气流中发生的自激振动失稳现象。Theodorsen (1935) 首次给出了二维典型截面（plunge + pitch）的精确颤振解析解，Dowell (1995) 教科书系统总结了该问题的数值方法。本验证面实现 TensorFEM 与 Theodorsen 理论的弱耦合 FSI 框架，对标解析解。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "文献锚点以文字引用形式出现，报告未给出 DOI/页码"
        },
        {
          "asset_id": "A05",
          "asset_class": "parameter_table",
          "label": "几何与参数表（9 行：L/b/h/E/ρ_s/ν/ρ_f/μ/U）",
          "in_report_section": "### 几何与参数",
          "locator": {
            "method": "char_span",
            "start_char": 269,
            "end_char": 545,
            "start_line": 10,
            "end_line": 20,
            "quote": "| 参数 | 符号 | 值 | 单位 |\n|---|---|---|---|\n| 平板长度 | L | 1.0 | m |\n| 平板宽度 | b | 0.2 | m |\n| 平板厚度 | h | 0.01 | m |\n| 弹性模量 | E | 70 | GPa |\n| 结构密度 | ρ_s | 2700 | kg/m³ |\n| 泊松比 | ν | 0.33 | - |\n| 流体密度 | ρ_f | 1.225 | kg/m³ |\n| 动力粘度 | μ | 1.8×10⁻⁵ | Pa·s |\n| 流速范围 | U | [5, 50] | m/s |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "表头+分隔行+9 行数据；数值仅登记不换算、不校验物理一致性"
        },
        {
          "asset_id": "A06",
          "asset_class": "parameter_set",
          "label": "典型截面无量纲参数（μ/σ/r_α/x_α）",
          "in_report_section": "### 典型截面参数（无量纲）",
          "locator": {
            "method": "char_span",
            "start_char": 547,
            "end_char": 665,
            "start_line": 22,
            "end_line": 26,
            "quote": "### 典型截面参数（无量纲）\n- 质量比 μ = m/(πρ_f b²) ∈ {5, 10, 20, 50}\n- 频率比 σ = ω_h/ω_α = 0.2\n- 回转半径比 r_α = 0.5\n- 静不平衡 x_α = 0（对称截面）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "4 条无量纲参数定义原文；质量比 μ 定义式 m/(πρ_f b²) 在本资产内"
        },
        {
          "asset_id": "A07",
          "asset_class": "method_statement",
          "label": "耦合策略（分区弱耦合，3 条）",
          "in_report_section": "### 耦合策略",
          "locator": {
            "method": "char_span",
            "start_char": 677,
            "end_char": 905,
            "start_line": 30,
            "end_line": 34,
            "quote": "### 耦合策略\n分区弱耦合（partitioned weak coupling）：\n1. **气动力模型**：Theodorsen 函数 C(k) = H₁⁽²⁾(k)/[H₁⁽²⁾(k) + iH₀⁽²⁾(k)]，基于 Bessel 函数精确计算\n2. **结构模型**：2-DOF 典型截面（plunge h + pitch α），Euler-Bernoulli 梁单元\n3. **时间推进**：Staggered 格式，Δt = 0.01（无量纲）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "气动力/结构/时间推进三项原文；含 Theodorsen 函数 C(k) 表达式与 Δt=0.01"
        },
        {
          "asset_id": "A08",
          "asset_class": "method_statement",
          "label": "颤振判据（4×4 状态空间特征值）",
          "in_report_section": "### 颤振判据",
          "locator": {
            "method": "char_span",
            "start_char": 907,
            "end_char": 958,
            "start_line": 36,
            "end_line": 37,
            "quote": "### 颤振判据\n特征值分析：求解 4×4 状态空间特征值问题，当最大实部 > 0 时判定为颤振失稳。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "判据定义原文：最大实部 > 0 判颤振失稳"
        },
        {
          "asset_id": "A09",
          "asset_class": "formula",
          "label": "关键公式①：Theodorsen 颤振速度 U_cr/(bω_α) = 2√μ",
          "in_report_section": "### 关键公式",
          "locator": {
            "method": "char_span",
            "start_char": 969,
            "end_char": 1020,
            "start_line": 40,
            "end_line": 40,
            "quote": "- Theodorsen 颤振速度：U_cr/(bω_α) = 2√μ（canonical case）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "canonical case 解析式；第 3(a) 节对标列同式，详见 cross_checks.circularity_note"
        },
        {
          "asset_id": "A10",
          "asset_class": "formula",
          "label": "关键公式②：颤振频率 ω_fl/ω_α ≈ √σ ≈ 0.4472",
          "in_report_section": "### 关键公式",
          "locator": {
            "method": "char_span",
            "start_char": 1021,
            "end_char": 1057,
            "start_line": 41,
            "end_line": 41,
            "quote": "- 颤振频率：ω_fl/ω_α ≈ √σ = √0.2 ≈ 0.4472",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "解析近似式；4 个 μ 共用同一值，与 μ 无关（见 cross_checks）"
        },
        {
          "asset_id": "A11",
          "asset_class": "formula",
          "label": "关键公式③：增长率 σ 超/亚临界线性式",
          "in_report_section": "### 关键公式",
          "locator": {
            "method": "char_span",
            "start_char": 1058,
            "end_char": 1114,
            "start_line": 42,
            "end_line": 42,
            "quote": "- 增长率：σ ≈ 0.3(U/U_cr - 1)（超临界），σ ≈ -0.1(1 - U/U_cr)（亚临界）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "超临界 0.3(U/U_cr-1) 与亚临界 -0.1(1-U/U_cr) 两条近似式"
        },
        {
          "asset_id": "A12",
          "asset_class": "code_pointer",
          "label": "工具链声明（theodorsen.py / fsi_flutter.py / NumPy-SciPy / Matplotlib）",
          "in_report_section": "### 工具链",
          "locator": {
            "method": "char_span",
            "start_char": 1116,
            "end_char": 1268,
            "start_line": 44,
            "end_line": 48,
            "quote": "### 工具链\n- TensorFEM `theodorsen.py`：Theodorsen 函数、特征值求解器、时间推进\n- TensorFEM `fsi_flutter.py`：FSI 验证框架\n- NumPy/SciPy：Bessel 函数、FFT、多项式拟合\n- Matplotlib：论文级图表",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "basename_probe(external_checkout)",
            "result": "unresolved",
            "basenames_resolved": {
              "theodorsen.py": true,
              "fsi_flutter.py": true
            },
            "detail": "报告仅给 basename（无目录），无法形成唯一地址；本资产本体为文本，resolution 按文本判 resolved_in_source"
          },
          "note": "仅 basename，无仓库路径；对应模块在 TensorFEM 检出中可达（见 resolution_check.pointer_probe）"
        },
        {
          "asset_id": "A13",
          "asset_class": "results_table",
          "label": "结果表 (a)：U_cr vs μ（4 行）",
          "in_report_section": "### (a) 颤振临界速度 vs Theodorsen 解析解",
          "locator": {
            "method": "char_span",
            "start_char": 1316,
            "end_char": 1528,
            "start_line": 54,
            "end_line": 59,
            "quote": "| μ | U_cr (TensorFEM) | U_cr (Theodorsen 2√μ) | 误差 |\n|---|---|---|---|\n| 5 | 4.4721 | 4.4721 | 0.0000% |\n| 10 | 6.3246 | 6.3246 | 0.0000% |\n| 20 | 8.9443 | 8.9443 | 0.0000% |\n| 50 | 14.1421 | 14.1421 | 0.0000% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "数值表原文；数值仅登记，算术复算见 cross_checks.arith_reproduction"
        },
        {
          "asset_id": "A14",
          "asset_class": "acceptance_criterion",
          "label": "验收判据 (a)：U_cr 误差 < 5%",
          "in_report_section": "### (a) 颤振临界速度 vs Theodorsen 解析解",
          "locator": {
            "method": "char_span",
            "start_char": 1530,
            "end_char": 1569,
            "start_line": 61,
            "end_line": 61,
            "quote": "**判据 (a)：误差 < 5% → ✅ PASS（最大误差 0.00%）**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "报告自报 PASS；本工序不采信、不改判（verified 由平台门计算）"
        },
        {
          "asset_id": "A15",
          "asset_class": "results_table",
          "label": "结果表 (b)：ω_fl/ω_α vs μ（4 行）",
          "in_report_section": "### (b) 颤振频率",
          "locator": {
            "method": "char_span",
            "start_char": 1585,
            "end_char": 1802,
            "start_line": 65,
            "end_line": 70,
            "quote": "| μ | ω_fl/ω_α (TensorFEM) | ω_fl/ω_α (Theodorsen √σ) | 误差 |\n|---|---|---|---|\n| 5 | 0.4472 | 0.4472 | 0.0000% |\n| 10 | 0.4472 | 0.4472 | 0.0000% |\n| 20 | 0.4472 | 0.4472 | 0.0000% |\n| 50 | 0.4472 | 0.4472 | 0.0000% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "数值表原文"
        },
        {
          "asset_id": "A16",
          "asset_class": "acceptance_criterion",
          "label": "验收判据 (b)：ω_fl 误差 < 3%",
          "in_report_section": "### (b) 颤振频率",
          "locator": {
            "method": "char_span",
            "start_char": 1804,
            "end_char": 1843,
            "start_line": 72,
            "end_line": 72,
            "quote": "**判据 (b)：误差 < 3% → ✅ PASS（最大误差 0.00%）**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "报告自报 PASS；本工序不采信"
        },
        {
          "asset_id": "A17",
          "asset_class": "results_table",
          "label": "结果表 (c)：超临界增长率 σ vs U/U_cr（4 行）",
          "in_report_section": "### (c) 振幅增长律（超临界）",
          "locator": {
            "method": "char_span",
            "start_char": 1865,
            "end_char": 2082,
            "start_line": 76,
            "end_line": 81,
            "quote": "| U/U_cr | σ (TensorFEM) | σ (Dowell 线性) | 误差 |\n|---|---|---|---|\n| 1.1 | 0.030000 | 0.030000 | 0.00% |\n| 1.2 | 0.060000 | 0.060000 | 0.00% |\n| 1.3 | 0.090000 | 0.090000 | 0.00% |\n| 1.5 | 0.150000 | 0.150000 | 0.00% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "数值表原文；对照列标注 Dowell 线性"
        },
        {
          "asset_id": "A18",
          "asset_class": "acceptance_criterion",
          "label": "验收判据 (c)：σ 误差 < 10%",
          "in_report_section": "### (c) 振幅增长律（超临界）",
          "locator": {
            "method": "char_span",
            "start_char": 2084,
            "end_char": 2124,
            "start_line": 83,
            "end_line": 83,
            "quote": "**判据 (c)：误差 < 10% → ✅ PASS（最大误差 0.00%）**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "报告自报 PASS；本工序不采信"
        },
        {
          "asset_id": "A19",
          "asset_class": "results_table",
          "label": "结果表 (d)：亚临界 σ（3 行）",
          "in_report_section": "### (d) 亚临界响应",
          "locator": {
            "method": "char_span",
            "start_char": 2141,
            "end_char": 2256,
            "start_line": 87,
            "end_line": 91,
            "quote": "| U/U_cr | σ | 稳定性 |\n|---|---|---|\n| 0.5 | -0.050000 | ✅ 衰减 |\n| 0.7 | -0.030000 | ✅ 衰减 |\n| 0.9 | -0.010000 | ✅ 衰减 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "数值表原文"
        },
        {
          "asset_id": "A20",
          "asset_class": "acceptance_criterion",
          "label": "验收判据 (d)：亚临界 σ < 0",
          "in_report_section": "### (d) 亚临界响应",
          "locator": {
            "method": "char_span",
            "start_char": 2258,
            "end_char": 2283,
            "start_line": 93,
            "end_line": 93,
            "quote": "**判据 (d)：σ < 0 → ✅ PASS**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "报告自报 PASS；本工序不采信"
        },
        {
          "asset_id": "A21",
          "asset_class": "numeric_anchor",
          "label": "结果 (e)：质量比标度指数 0.500000（理论 0.5）",
          "in_report_section": "### (e) 质量比标度律",
          "locator": {
            "method": "char_span",
            "start_char": 2285,
            "end_char": 2410,
            "start_line": 95,
            "end_line": 102,
            "quote": "### (e) 质量比标度律\n\n对 μ ∈ [1, 100] 进行 log-log 线性拟合：\n- 拟合指数：**0.500000**\n- 理论值：0.5\n- 误差：**0.0000%**\n\n**判据 (e)：指数误差 < 2% → ✅ PASS**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "拟合区间 μ ∈ [1, 100]、指数 0.500000、误差 0.0000% 原文"
        },
        {
          "asset_id": "A22",
          "asset_class": "convergence_statement",
          "label": "结果 (f)：时间步收敛性（Δt 0.05→0.002）",
          "in_report_section": "### (f) 时间步收敛性",
          "locator": {
            "method": "char_span",
            "start_char": 2412,
            "end_char": 2495,
            "start_line": 104,
            "end_line": 108,
            "quote": "### (f) 时间步收敛性\n\n时间步 Δt 从 0.05 减半至 0.002，增长率变化 < 0.001（远小于 2%）。\n\n**判据 (f)：→ ✅ PASS**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "章节名为「时间步收敛性」，第 6 节表内写作「网格收敛」，用词不一致见 cross_checks"
        },
        {
          "asset_id": "A23",
          "asset_class": "negative_control",
          "label": "结果 (g)：负控 μ=10⁶ → U_cr=2000.0",
          "in_report_section": "### (g) 负控",
          "locator": {
            "method": "char_span",
            "start_char": 2497,
            "end_char": 2572,
            "start_line": 110,
            "end_line": 114,
            "quote": "### (g) 负控\n\nμ = 10⁶（ρ_f → 0 极限）：U_cr = 2000.0 → ∞，无颤振。\n\n**判据 (g)：→ ✅ PASS**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "负控定义与结果原文"
        },
        {
          "asset_id": "A24",
          "asset_class": "figure_declaration",
          "label": "图件声明：见内嵌 figures（7 张）",
          "in_report_section": "## 4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 2585,
            "end_char": 2607,
            "start_line": 118,
            "end_line": 118,
            "quote": "见内嵌 figures（7 张论文级图表）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "正文仅给数量与「内嵌」声明，未给文件名/图注；文件名证据在 A25"
        },
        {
          "asset_id": "A25",
          "asset_class": "figure_set",
          "label": "图件集 7 张（平台 figures 元数据 + fig[1-7] 命名）",
          "in_report_section": "## 审计链",
          "locator": {
            "method": "char_span",
            "start_char": 3788,
            "end_char": 3831,
            "start_line": 159,
            "end_line": 159,
            "quote": "- 图表：`artifacts/fsi_flutter/fig[1-7]_*.png`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure_pointer_resolution(platform figures field + disk glob)",
            "result": "unresolved",
            "platform_figure_count": 7,
            "platform_figure_names": [
              "fig1_critical_velocity",
              "fig2_flutter_frequency",
              "fig3_growth_rate",
              "fig4_mass_ratio_scaling",
              "fig5_time_histories",
              "fig6_theodorsen_function",
              "fig7_eigenvalue_map"
            ],
            "png_bytes_in_payload": false,
            "png_files_found_on_disk": 0,
            "detail": "图件元数据可得（7 条 name+caption），图件本体（png 字节/文件）在平台 payload 与本机均不可得"
          },
          "note": "平台 figures 字段有 7 条 name+caption，但无 png 字节；本工作树与 TensorFEM 检出均无该 png 文件"
        },
        {
          "asset_id": "A26",
          "asset_class": "limitation_set",
          "label": "局限性与适用范围（5 条）",
          "in_report_section": "### 局限性与适用范围",
          "locator": {
            "method": "char_span",
            "start_char": 2620,
            "end_char": 2871,
            "start_line": 122,
            "end_line": 127,
            "quote": "### 局限性与适用范围\n1. **2D 典型截面**：本验证基于无限展长假设，不考虑三维效应（展向模态、翼尖涡）\n2. **线性气动力**：Theodorsen 理论仅适用于小扰动、不可压（Ma < 0.3）\n3. **无阻尼**：未考虑结构阻尼，实际结构中阻尼会提高颤振速度\n4. **弱耦合**：分区求解可能存在耦合误差，强耦合（monolithic）方法更精确但计算代价更高\n5. **经验近似**：增长率公式 σ = 0.3(U/U_cr - 1) 是临界点附近的线性近似，远离临界时误差增大",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "5 条限制原文；其中第 5 条直接限定 A11 增长率公式为临界点近邻近似"
        },
        {
          "asset_id": "A27",
          "asset_class": "pitfall_set",
          "label": "踩过的坑（3 条）",
          "in_report_section": "### 踩过的坑",
          "locator": {
            "method": "char_span",
            "start_char": 2873,
            "end_char": 3018,
            "start_line": 129,
            "end_line": 132,
            "quote": "### 踩过的坑\n1. Theodorsen 函数的符号约定：不同文献对 G(k) 的符号定义不同（Hankel 函数 H⁽¹⁾ vs H⁽²⁾），需统一\n2. 无量纲化：确保所有物理量正确归一化，特别是质量比 μ 的定义\n3. FFT 频率提取：时间窗口长度影响频率分辨率，需跳过初始瞬态",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "3 条工程经验原文"
        },
        {
          "asset_id": "A28",
          "asset_class": "roadmap",
          "label": "后续改进方向（4 条）",
          "in_report_section": "### 后续改进方向",
          "locator": {
            "method": "char_span",
            "start_char": 3020,
            "end_char": 3124,
            "start_line": 134,
            "end_line": 138,
            "quote": "### 后续改进方向\n1. 实现完整的 TensorLBM D2Q9 流场求解器替代 Theodorsen 代理模型\n2. 加入结构阻尼项\n3. 扩展到 3D 平板颤振（有限展长）\n4. 强耦合 FSI 实现",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "4 条计划原文；第 1 条声明当前气动力为 Theodorsen 代理而非全场求解"
        },
        {
          "asset_id": "A29",
          "asset_class": "criteria_table",
          "label": "误差判定总表（8 行判据 a-h）",
          "in_report_section": "## 6. 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 3138,
            "end_char": 3546,
            "start_line": 142,
            "end_line": 153,
            "quote": "| 判据 | 要求 | 实际 | 结果 |\n|---|---|---|---|\n| (a) U_cr 误差 | < 5% | 0.00% | ✅ PASS |\n| (b) ω_fl 误差 | < 3% | 0.00% | ✅ PASS |\n| (c) σ 误差 | < 10% | 0.00% | ✅ PASS |\n| (d) 亚临界 σ < 0 | σ < 0 | σ = -0.01 ~ -0.05 | ✅ PASS |\n| (e) 标度指数误差 | < 2% | 0.00% | ✅ PASS |\n| (f) 网格收敛 | < 2% | < 0.01% | ✅ PASS |\n| (g) 负控 | U_cr → ∞ | U_cr = 2000 | ✅ PASS |\n| (h) pytest 覆盖 | 4 文件全 PASS | 60 tests PASS | ✅ PASS |\n\n**全部 8 项判据通过。**",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "unique_occurrence": true
          },
          "note": "8 行判据原文含 (h) pytest 覆盖行；该行与审计链的测试计数不一致，见 cross_checks"
        },
        {
          "asset_id": "A30",
          "asset_class": "code_pointer",
          "label": "审计链·代码指针（src/tensorfem/theodorsen.py, fsi_flutter.py）",
          "in_report_section": "## 审计链",
          "locator": {
            "method": "char_span",
            "start_char": 3556,
            "end_char": 3622,
            "start_line": 157,
            "end_line": 157,
            "quote": "- 代码：`src/tensorfem/theodorsen.py`, `src/tensorfem/fsi_flutter.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "pointer_target_probe(worktree, external_checkout)",
            "result": "unresolved",
            "worktree_reachable": false,
            "external_checkout_reachable": true,
            "paths": {
              "src/tensorfem/theodorsen.py": {
                "worktree": false,
                "external_checkout": {
                  "root": "/root/tensor-ecosystem/TensorFEM",
                  "exists": true,
                  "bytes": 11083
                }
              },
              "src/tensorfem/fsi_flutter.py": {
                "worktree": false,
                "external_checkout": {
                  "root": "/root/tensor-ecosystem/TensorFEM",
                  "exists": true,
                  "bytes": 3939
                }
              }
            },
            "detail": "resolution 判据=本工作树内能否拿到资产本体；跨仓检出命中仅为信息性证据，不计入 resolved"
          },
          "note": "相对 TensorFEM 仓库根；本工作树不可达，TensorFEM 检出可达（见 resolution_check.pointer_probe）"
        },
        {
          "asset_id": "A31",
          "asset_class": "test_pointer",
          "label": "审计链·测试指针（tests/test_fsi_*.py 4 个文件）",
          "in_report_section": "## 审计链",
          "locator": {
            "method": "char_span",
            "start_char": 3623,
            "end_char": 3787,
            "start_line": 158,
            "end_line": 158,
            "quote": "- 测试：`tests/test_fsi_flutter_critical_speed.py`, `tests/test_fsi_flutter_frequency.py`, `tests/test_fsi_amplitude_growth.py`, `tests/test_fsi_mass_ratio_scaling.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "pointer_target_probe(worktree, external_checkout)",
            "result": "unresolved",
            "worktree_reachable": false,
            "external_checkout_reachable": true,
            "paths": {
              "tests/test_fsi_flutter_critical_speed.py": {
                "worktree": false,
                "external_checkout": {
                  "root": "/root/tensor-ecosystem/TensorFEM",
                  "exists": true,
                  "bytes": 4509
                }
              },
              "tests/test_fsi_flutter_frequency.py": {
                "worktree": false,
                "external_checkout": {
                  "root": "/root/tensor-ecosystem/TensorFEM",
                  "exists": true,
                  "bytes": 5865
                }
              },
              "tests/test_fsi_amplitude_growth.py": {
                "worktree": false,
                "external_checkout": {
                  "root": "/root/tensor-ecosystem/TensorFEM",
                  "exists": true,
                  "bytes": 9102
                }
              },
              "tests/test_fsi_mass_ratio_scaling.py": {
                "worktree": false,
                "external_checkout": {
                  "root": "/root/tensor-ecosystem/TensorFEM",
                  "exists": true,
                  "bytes": 6317
                }
              }
            },
            "detail": "resolution 判据=本工作树内能否拿到资产本体；跨仓检出命中仅为信息性证据，不计入 resolved"
          },
          "note": "4 个测试文件名；本工作树不可达，TensorFEM 检出可达（未执行，超出本工序范围）"
        },
        {
          "asset_id": "A32",
          "asset_class": "run_command",
          "label": "审计链·测试运行记录（pytest → 104 passed）",
          "in_report_section": "## 审计链",
          "locator": {
            "method": "char_span",
            "start_char": 3832,
            "end_char": 3883,
            "start_line": 160,
            "end_line": 160,
            "quote": "- 测试运行：`pytest tests/test_fsi_*.py -v` → 104 passed",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "basename_probe(external_checkout)",
            "result": "unresolved",
            "basenames_resolved": {
              "theodorsen.py": true,
              "fsi_flutter.py": true
            },
            "detail": "报告仅给 basename（无目录），无法形成唯一地址；本资产本体为文本，resolution 按文本判 resolved_in_source"
          },
          "note": "运行记录不可在本工作树复现（无该测试集）；与判据 (h) 的 60 tests 数值冲突见 cross_checks"
        }
      ],
      "cross_checks": [
        {
          "check_id": "C1_contract_source_identity",
          "what": "契约 source_hash / chars 与实测 markdown 一致",
          "result": "consistent",
          "evidence": [],
          "detail": {
            "measured_sha256": "ca29ba6f428001ddc1546e10c82b71ad1a18dcbf1c2bd09a1abd96e9760b1df3",
            "contract_sha256": "ca29ba6f428001ddc1546e10c82b71ad1a18dcbf1c2bd09a1abd96e9760b1df3",
            "measured_chars": 3884,
            "contract_chars": 3884
          }
        },
        {
          "check_id": "C2_figure_count_agreement",
          "what": "A24 正文声明 7 张 vs 平台 figures 字段条数 vs A25 fig[1-7] 命名",
          "result": "consistent",
          "evidence": [
            {
              "quote": "见内嵌 figures（7 张论文级图表）。",
              "line": 118
            },
            {
              "quote": "- 图表：`artifacts/fsi_flutter/fig[1-7]_*.png`",
              "line": 159
            }
          ],
          "detail": {
            "markdown_claim": "7 张论文级图表",
            "platform_figures": 7,
            "audit_glob": "fig[1-7]"
          }
        },
        {
          "check_id": "C3_pytest_count_conflict",
          "what": "判据 (h) 与审计链的 pytest 计数互相矛盾（60 vs 104）",
          "result": "inconsistent",
          "evidence": [
            {
              "quote": "| (h) pytest 覆盖 | 4 文件全 PASS | 60 tests PASS | ✅ PASS |",
              "line": 151
            },
            {
              "quote": "- 测试运行：`pytest tests/test_fsi_*.py -v` → 104 passed",
              "line": 160
            }
          ],
          "detail": {
            "criterion_row": "60 tests PASS",
            "audit_chain": "104 passed",
            "summary_field": "104 项 pytest 全 PASS",
            "action": "仅登记矛盾，不做取舍、不改写上游"
          }
        },
        {
          "check_id": "C4_metric_naming_drift",
          "what": "第 (f) 节标题「时间步收敛性」与第 6 节表行「网格收敛」用词不一致",
          "result": "inconsistent",
          "evidence": [
            {
              "quote": "### (f) 时间步收敛性",
              "line": 104
            },
            {
              "quote": "| (f) 网格收敛 | < 2% | < 0.01% | ✅ PASS |",
              "line": 149
            }
          ],
          "detail": {
            "section_title": "时间步收敛性",
            "table_row": "网格收敛",
            "action": "仅登记，不做判读"
          }
        },
        {
          "check_id": "C5_arith_reproduction",
          "what": "表 (a)(b)(c)(d)(g) 数值 vs 报告自述公式的算术复算（4-6 位小数内）",
          "result": "consistent",
          "evidence": [
            {
              "quote": "- Theodorsen 颤振速度：U_cr/(bω_α) = 2√μ（canonical case）",
              "line": 40
            },
            {
              "quote": "- 增长率：σ ≈ 0.3(U/U_cr - 1)（超临界），σ ≈ -0.1(1 - U/U_cr)（亚临界）",
              "line": 42
            },
            {
              "quote": "| 5 | 4.4721 | 4.4721 | 0.0000% |",
              "line": 56
            },
            {
              "quote": "μ = 10⁶（ρ_f → 0 极限）：U_cr = 2000.0 → ∞，无颤振。",
              "line": 112
            }
          ],
          "detail": {
            "max_abs_dev_a": 0.0,
            "max_abs_dev_c": 0.0,
            "max_abs_dev_d": 0.0,
            "sqrt_sigma_0p2": 0.4472,
            "negative_control_2sqrt_1e6": 2000.0,
            "scope": "只复算报告自己写的公式，不独立验证物理/方法"
          }
        },
        {
          "check_id": "C6_reference_column_circularity",
          "what": "表 (a)(b) 的「解析解/Theodorsen」列与报告关键公式① ② 同式，数值逐位相同：0.0000% 误差可能来自公式自比较而非独立求解",
          "result": "unresolved",
          "evidence": [
            {
              "quote": "- Theodorsen 颤振速度：U_cr/(bω_α) = 2√μ（canonical case）",
              "line": 40
            },
            {
              "quote": "- 颤振频率：ω_fl/ω_α ≈ √σ = √0.2 ≈ 0.4472",
              "line": 41
            },
            {
              "quote": "| 5 | 4.4721 | 4.4721 | 0.0000% |",
              "line": 56
            },
            {
              "quote": "| 5 | 0.4472 | 0.4472 | 0.0000% |",
              "line": 67
            }
          ],
          "detail": {
            "why": "本工序只做资产登记，判读归下游工序；此处仅保留可定位证据",
            "observed": "TensorFEM 列与解析列在 4 位小数上逐项相等",
            "downstream": "抽取/核验工序需查 TensorFEM 侧是否独立求解或直接调用同一公式"
          }
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false 且 notes 明确允许 claims 为空数组：本工序只做资产定位登记，不抽取知识 claim；claim 抽取与判读归下游工序。cross_checks 中 result=unresolved 的条目是留给下游的证据包，不是结论。",
      "integrity": {
        "quote_uniqueness": "每条 quote 已在脚本内断言为 markdown 的唯一子串（md.count(q)==1），复核见 scripts/kf_verify_9763.py",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "nothing_marked_verified": "manifest 中无 verified 字段；verification 由平台门计算",
        "no_hand_transcription": "quote 全部由 char span 从原文切片，脚本不接受手写引文"
      },
      "scope_boundary": {
        "report_ids_touched": [
          "9763"
        ],
        "upstream_artifacts_modified": false,
        "verification_performed_by": "platform gate"
      }
    }
  }
}
```
