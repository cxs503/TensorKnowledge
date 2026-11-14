KF-RESULT wp-9582-02

tags: kf-wp:wp-9582-02, kf-line, 02-classification-parse, report:9582, ice_rubble_rheology_dem, DEM, ice-rubble, mu(I)-rheology, classification

# KF-RESULT wp-9582-02 — 报告 9582 分类解析（02-classification-parse）

- report_id: `9582`（本包只碰这一份报告）
- package_id: `wp-9582-02` · task_type: `02-classification-parse` · contract_version `1.0` · lane B
- source: `tensor://reports/9582` / field `markdown` / `sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f` / 11293 chars（16772 bytes UTF-8）
- 分类结论：`experimental-validation`（置信度 medium-high）→ skill `xsk-experimental-validation` v0.1.0
- 状态：draft（verification 由平台门计算，本包不自行判 verified）

## ① 本工序做了什么

对报告 9582（P82W2-N02 碎冰堆积体 μ(I) 流变标定）只做了**分类 + 结构解析**这一道工序：

1. 按 `extraction-skills/registry.json` 的 `identify_signals` 对**六分型**逐信号判定，给出主类型、
   五个竞争类型的逐条否决理由（分类是可反驳假设，不是结论）；
2. 对正文做**结构切分**（16 个标题、字符级 offset、覆盖 [0, 11293)），并把切出的
   章节映射到所选 skill 要求的五类章节（setup / measurement / comparison / uncertainty / validation）；
3. **主题打标**（场景键、学科=船舶冰区航行、方法族=DEM、主题标签）；
4. 每条判定依据都带**逐字引文定位**（`start_offset` / `end_offset` / `content_hash`），共 35 条。

**不做**的事（边界）：不抽取 claim、不登记资产、不读不写其它 report_id、不改上游包、不标 verified。
因此 `claims.json` 按设计为空数组（零 claim 是合法包，见 acceptance 第 6 条）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具 / 关键设置 |
|---|---|---|
| 1 | 取原文：`GET $TENSOR_API_BASE/tensor/reports/9582`（Bearer） | 只取 `markdown` 字段；`psql` 直读被权限拒绝（`ERROR: permission denied for table tensor_reports`），故走 API |
| 2 | 落盘原文并独立重算哈希 | `docs/kf/wp-9582-02/source.md`，`sha256=cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f`，与契约 `source_hash` 逐字节一致 |
| 3 | 元数据单独落盘、构建时校验 | `record_meta.json`（title/scenario_key/mission_id/tags/figures/chars/hash）——title 等字段**读取**而非手抄，构建脚本在哈希或字符数不符时直接拒绝构建 |
| 4 | 六分型信号判定 | 信号串取自 registry 原文；中文报告，故每个英文信号配双语检索词，命中即给 locator，未命中即**实测缺失**（记录检索词与命中计数，可一键复跑） |
| 5 | 引文定位 | `build.py` 对每条候选引文要求**在原文中恰好出现 1 次**（0 次或多次直接退出），offset 由 `str.find` 计算，`content_hash = sha256(quote)` |
| 6 | 结构切分 | 逐行扫描 `#`/`##`/`###`（含 ①②③ 与 3.1–3.8），段落 span = 到下一个标题，末段到文末 |
| 7 | 选 skill | 由切分结果按**标题关键词**映射到 skill 章节（映射规则写死在 `build.py`，id 漂移即报错退出） |
| 8 | 验收自查 | `verify.py` 重算哈希、逐条复核 35 个 locator 的 offset/引文/哈希/唯一性、xref 闭合、schema 校验、上游一致性；输出 30 条逐项结论 |

关键设置：`char_offset` 定位单位为 **markdown 字段的 Python 字符索引**（码点，非字节）；`content_hash`
覆盖 quote 的 UTF-8 字节。全部产物由脚本生成，报告本文件亦由 `make_report.py` 程序化拼装。

## ③ 产出物清单（输出文件 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9582-02/source.md` | 报告 9582 markdown 原文（11293 chars / 16772 bytes），哈希与契约一致 |
| `docs/kf/wp-9582-02/record_meta.json` | 参数化元数据（title / scenario_key / mission_id / tags / 6 图名 / chars / sha256），构建与校验的共同输入 |
| `docs/kf/wp-9582-02/build.py` | 生成器：定位 35 条引文、实测缺失信号、切分 16 节、装配 `classification.json` 与 `kf_result.json`（幂等） |
| `docs/kf/wp-9582-02/classification.json` | 本工序主产物：六分型信号表 + 5 条竞争类型否决理由 + 结构切分 + skill 映射 + 主题标签 + 35 条证据 + 2 条 unresolved + 上游一致性 |
| `docs/kf/wp-9582-02/kf_result.json` | 交付信封（schema `kf_result.v1`）：provenance + outputs(`classification.json`, `claims.json`=[]) |
| `docs/kf/wp-9582-02/verify.py` | 独立复验器：30 条检查（哈希 / locator / ID 唯一 / xref / schema / 结构 / 上游 / 交付块） |
| `docs/kf/wp-9582-02/verify.log` | 本次复验原样输出 |
| `docs/kf/wp-9582-02/make_report.py`, `report.md` | 报告生成器与交付 markdown（唯一一个 json 代码块 = `kf_result.json`） |

**图**：本工序是纯文档分类，没有产生任何场量/曲线，故无图（非「忘画」——分类产物是标签与定位，
可视化只会是标签饼图这类无信息量的图，且契约不允许把分类结论包装成测量结果）。

## ④ 证据定位表（判定依据 → 原文逐字引文）

定位格式 `[start,end)` 为 markdown 字符偏移；每条引文在原文中唯一出现，`content_hash` 为引文 UTF-8 的 sha256。
下表由 `classification.json` 直接渲染，未人工誊抄。

| 证据 ID | 判定维度 | 原文引文（逐字） | 偏移 | content_hash |
|---|---|---|---|---|
| ev-9582-02-01 | identity.title | `# P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定` | 0–46 | `sha256:14017a1acb7c…` |
| ev-9582-02-02 | purpose.problem_class | `碎冰（rubble）堆积体是船舶冰阻力与冰载荷模型的等效连续介质来源。` | 59–94 | `sha256:6c14e8491261…` |
| ev-9582-02-03 | type.experimental-validation.test_matrix | `\| 工况数 \| 54 runs，19 个（场景, 固体分数, 速率）条件；剪切/压缩每条件 3 个 seed，航道 2 个 \|` | 510–573 | `sha256:1d89d398070a…` |
| ev-9582-02-04 | type.experimental-validation.measurement_uncertainty | `\| 条件均值 μ 的平均标准误（统计噪声） \| 0.0102 \|` | 5579–5611 | `sha256:ee0aee9d5600…` |
| ev-9582-02-05 | type.experimental-validation.uncertainty_budget | `### 3.6 判据 (c) 的噪声预算：残差是结构性的还是统计的？` | 5435–5469 | `sha256:62d78171d9d6…` |
| ev-9582-02-06 | type.experimental-validation.signal_vs_noise | `\| μ 的条件间标准差（信号） \| 0.0281 \|` | 5525–5551 | `sha256:35f2664855c3…` |
| ev-9582-02-07 | type.experimental-validation.validation_case | `### 3.8 样本外验证（碎冰航道，未参与标定）` | 7002–7027 | `sha256:d2c2595a1c02…` |
| ev-9582-02-08 | type.experimental-validation.validation_result | `6 个航道 run 的实测 μ 与单元试验律预测之差 = -0.1698 ± 0.0182（相对误差均值 -2.25），压力 6186–9191 Pa。` | 7028–7104 | `sha256:87b931bb1848…` |
| ev-9582-02-09 | type.experimental-validation.baseline_comparison | `\| 判据 \| 阈值 \| 实测 \| 结论 \|` | 6464–6485 | `sha256:dabdeb587171…` |
| ev-9582-02-10 | type.experimental-validation.honest_fail | `\| (c) μ(I) 拟合优度（主判据：合并单元试验） \| R²≥0.95, σ≤0.05 \| R²=0.8035, σ=0.0134 \| **FAIL (honest)** \|` | 6603–6692 | `sha256:f3e851bd874d…` |
| ev-9582-02-11 | type.experimental-validation.baseline_semantics | `\| η(0.1 s⁻¹, 10 kPa) vs 文献窗 \| [1e3, 1e5] Pa·s（量级窗，非逐点） \| 2.512e+04 \| 窗内（不作 % 判定，基准为量级窗） \|` | 10146–10235 | `sha256:129704f94fbb…` |
| ev-9582-02-12 | type.scientific-computation.governing_equation_partial | `（3）宏观流变点 (I, μ) 与二次流变律 μ(I) = μ₀ + αI + βI²，并给出等效黏度 η = μP/γ̇ 与文献锚点对照。` | 186–256 | `sha256:47f7d45d03e9…` |
| ev-9582-02-13 | type.scientific-computation.fitted_law | `主判据律：μ(I) = 0.2498 +2.028 I -12.984 I²，覆盖 I ∈ [4.330e-03, 0.0674]。` | 3838–3904 | `sha256:e46ee4c59a33…` |
| ev-9582-02-14 | type.scientific-computation.discretisation_partial | `\| 后处理网格 \| h = 5 d₅₀（单元格精确铺满域，h/d₅₀ = 5.0 ± 0.5%） \|` | 574–624 | `sha256:2ec81ad868ee…` |
| ev-9582-02-15 | type.scientific-computation.postprocess_method | `2. Voronoi/Delaunay：中心点镶嵌（周期像/闭壁镜像）给逐颗粒 φᵢ = 1 − A_disk/A_cell 与 Delaunay 边长/d₅₀。` | 856–937 | `sha256:2627eb9e9242…` |
| ev-9582-02-16 | type.scientific-computation.stress_definition | `4. 宏观量：Love–Weber 位力 σ = −(1/V)Σf⊗b（压为正），P = trσ/2，τ = (σ₁−σ₂)/2，μ = τ/P；I = γ̇d₅₀/√(P/ρ)，γ̇ …` | 1047–1225 | `sha256:1871e496b7f1…` |
| ev-9582-02-17 | type.software-engineering.interface | `- 剪切：x 周期、上下粗糙壁**反向滑动**（±v/2，几何不动）。为此给引擎新增逐段壁面速度 `wall_velocity`（默认 None = 历史行为逐位不变）。γ̇ 由本体切片…` | 1371–1486 | `sha256:1d452bf5414f…` |
| ev-9582-02-18 | type.software-engineering.regression | `- 测试：`tests/test_rubble_postprocess.py`（19 项，含 4 个负控）+ `tests/test_rubble_kinematics.py`（5 项，…` | 11125–11225 | `sha256:60ff045be14b…` |
| ev-9582-02-19 | type.software-engineering.commit_trailer | `<!-- m8301 / FEAT-OSS-INVENTORY-LBM / hemelb commit 432d3386 -->` | 11228–11292 | `sha256:bc922c2decfd…` |
| ev-9582-02-20 | type.literature-review.citation_density | `6. **文献锚点为量级窗**：Guimarães et al. 2022 未数字化逐点数据，逐点对比标注 WITHHELD。` | 9642–9705 | `sha256:83b2cf3de8c7…` |
| ev-9582-02-21 | type.algorithm-implementation.procedure_block | `3. 力链：按接触力分位切分强弱链（互补掩码），方向折叠到 [0,π)，结构张量 R = ⟨nn⟩ 给 A_c = 2(λ₁−λ₂)/(λ₁+λ₂)，强子图连通分量与横跨判定（判据 b …` | 938–1046 | `sha256:c046b9193b40…` |
| ev-9582-02-22 | type.technical-proposal.absent_plan | `- 预注册：`prereg/rubble_rheology_prereg.json`（阈值先声明；Amendment 1 = 等面积压缩 + 航道改作验证；Amendment 2 = 本…` | 10644–10776 | `sha256:33e0e5554314…` |
| ev-9582-02-23 | setup.numerical_cell | `\| 几何/维度 \| 二维平面应变，周期 x（航道场景 x 周期 + 固定船体） \|` | 280–321 | `sha256:762abda83f21…` |
| ev-9582-02-24 | setup.material | `\| 颗粒 \| 双分散刚性圆盘，d₅₀ = 0.02359 m，密度 ρ = 917 kg/m³ \|` | 322–371 | `sha256:7a531f851ff0…` |
| ev-9582-02-25 | setup.contact_model | `\| 接触 \| Hertz–Mindlin 法向/切向 + Coulomb 摩擦 μ_p = 0.5 + 滚动阻力 0.05，kn = 3.0e4 N/m，板厚 0.03 m \|` | 372–460 | `sha256:1c5fca4a5f6f…` |
| ev-9582-02-26 | setup.scenarios | `\| 场景 \| 简单剪切（粗糙滑动壁 Couette）/ 等面积平面应变压缩 / 碎冰航道漂移 \|` | 461–509 | `sha256:c4fb36b7b35f…` |
| ev-9582-02-27 | measurement.result_table_shear | `\| 场景 \| 名义速率 \| seeds \| P [Pa] \| I \| μ \| μ 标准误 \|` | 1928–1974 | `sha256:a559b4bb4ce2…` |
| ev-9582-02-28 | measurement.fit_table | `\| 口径 \| μ₀ \| α \| β \| R² \| 残差标准差 \| n \|` | 3428–3464 | `sha256:d70fd92a18e7…` |
| ev-9582-02-29 | comparison.ablation | `### 3.5 压缩单元试验运动学消融（本次修正的直接证据）` | 4758–4788 | `sha256:a9c1a14e2cb9…` |
| ev-9582-02-30 | limitations.finite_size | `4. **有限尺寸涨落**：N≈400 圆盘，seed 间 μ 标准差 0.01–0.02，条件标准误 0.005–0.010；12 快照平均后的条件均值仍是判据 (c) 的主要噪声源。` | 9484–9577 | `sha256:1478860d7fd5…` |
| ev-9582-02-31 | comparison.honest_conclusion | `**诚实结论**：数值/守恒/拟合器层面误差 ≪3%；物理层面「单一 μ(I) 跨三场景」主判据 honest FAIL（R² = 0.8035 < 0.95，残差 σ = 0.0134）。` | 10296–10391 | `sha256:236c98041fa2…` |
| ev-9582-02-32 | measurement.figures_declared | `**porosity_fields.png** — Porosity field phi(x,t) of one steady snapshot per scenario on the …` | 7165–7282 | `sha256:084f25b805af…` |
| ev-9582-02-33 | toolchain | `**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_ru…` | 1685–1882 | `sha256:9f4d25588e07…` |
| ev-9582-02-34 | comparison.residual_interpretation | `解读：the pooled residual (0.0134) is 1.3x the mean per-condition standard error (0.0102), so it…` | 5743–5884 | `sha256:6d110f80f590…` |
| ev-9582-02-35 | figures.section | `## ④ 结果图\n\n**porosity_fields.png** — Porosity field` | 7155–7205 | `sha256:715f2f4ba63c…` |

### 4.1 六分型信号判定（未命中即实测缺失）

| 报告类型 | 信号 | 判定 | 证据 | 依据 |
|---|---|---|---|---|
| **experimental-validation** | test matrix | present | ev-9582-02-03 | locator |
| **experimental-validation** | facility | absent | ev-9582-02-23, ev-9582-02-24, ev-9582-02-25 | measured absence (terms: facility×0, 实验台×0, 试验台×0, …) |
| **experimental-validation** | measurement uncertainty | present | ev-9582-02-04, ev-9582-02-05, ev-9582-02-06, ev-9582-02-30 | locator |
| **experimental-validation** | validation case | present | ev-9582-02-07, ev-9582-02-08 | locator |
| **experimental-validation** | baseline comparison | present | ev-9582-02-09, ev-9582-02-10, ev-9582-02-11 | locator |
| scientific-computation | governing equations | partial | ev-9582-02-12, ev-9582-02-16 | locator |
| scientific-computation | discretisation | partial | ev-9582-02-14, ev-9582-02-15 | locator |
| scientific-computation | convergence study | absent | — | measured absence (terms: convergence×0, 收敛×0, 收敛性研究×0, …) |
| scientific-computation | mesh refinement | absent | — | measured absence (terms: mesh refinement×0, refinement×0, 网格加密×0, …) |
| scientific-computation | timing table | absent | — | measured absence (terms: timing×0, wall-clock×0, 计时×0, …) |
| software-engineering | changed files | partial | ev-9582-02-33 | locator |
| software-engineering | commit | absent | ev-9582-02-19 | measured absence (terms: commit×1, 提交×0, sha×1, …) |
| software-engineering | interface | present | ev-9582-02-17 | locator |
| software-engineering | regression | present | ev-9582-02-18 | locator |
| software-engineering | API | partial | ev-9582-02-17, ev-9582-02-16 | locator |
| algorithm-implementation | algorithm block | partial | ev-9582-02-21 | locator |
| algorithm-implementation | pseudocode | absent | — | measured absence (terms: pseudocode×0, 伪代码×0, …) |
| algorithm-implementation | complexity | absent | — | measured absence (terms: complexity×0, 时间复杂度×0, 复杂度×0, …) |
| algorithm-implementation | function signature | absent | — | measured absence (terms: def ×0, (×52, ) ->×0, …) |
| literature-review | related work | absent | — | measured absence (terms: related work×0, 相关工作×0, state of the art×0, …) |
| literature-review | survey | absent | — | measured absence (terms: survey×0, 综述×0, …) |
| literature-review | bibliography | absent | — | measured absence (terms: bibliography×0, 参考文献×0, References×0, …) |
| literature-review | citation density >= 5 per 1000 chars | absent | ev-9582-02-20 | measured absence (terms: et al.×1, Guimarães×1, doi×0, …) |
| technical-proposal | roadmap / proposal | absent | — | measured absence (terms: roadmap×0, proposal×0, 路线图×0, …) |
| technical-proposal | specification | absent | — | measured absence (terms: specification×0, 规格书×0, 规格说明×0, …) |
| technical-proposal | design | absent | — | measured absence (terms: design×0, 设计×2, 方案×0, …) |

主类型 `experimental-validation` 命中 4/5（唯一真缺失 = `facility`：本次是二维周期应变**数值**单元试验，
没有物理实验台；缺失如实记 miss，不改写成命中）。次选 `software-engineering` 命中 3/5（引擎新增
`wall_velocity` 且默认值保持历史行为 + 19 项后处理测试含 4 个负控），但它只占 ② 的一小节与审计链，
报告的交付物是 (I, μ) 点集、拟合律与验收判据，故不作主类型。判定理由全文见
`classification.json: classification.alternatives_considered`。

### 4.2 结构切分与 skill 章节映射（16 节，覆盖全文）

| 节 | 级别 | 标题 | 偏移 | 映射 skill 章节 |
|---|---|---|---|---|
| s01 | # | P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定 | 0–48 | — |
| s02 | ## | ① 案例介绍 | 48–672 | setup |
| s03 | ## | ② 怎么做的 | 672–1885 | setup |
| s04 | ## | ③ 计算结果 | 1885–1896 | — |
| s05 | ### | 3.1 各条件的流变点（条件均值，seed 为重复） | 1896–3396 | measurement |
| s06 | ### | 3.2 μ(I) 拟合（三种聚合口径，全部如实列出） | 3396–3907 | comparison |
| s07 | ### | 3.3 等效黏度（η = μP/γ̇，参考态 γ̇ = 0.1 s⁻¹） | 3907–4270 | measurement |
| s08 | ### | 3.4 孔隙率场与力链微结构 | 4270–4758 | measurement |
| s09 | ### | 3.5 压缩单元试验运动学消融（本次修正的直接证据） | 4758–5435 | validation |
| s10 | ### | 3.6 判据 (c) 的噪声预算：残差是结构性的还是统计的？ | 5435–6446 | uncertainty |
| s11 | ### | 3.7 机器可算验收判据 | 6446–7002 | comparison |
| s12 | ### | 3.8 样本外验证（碎冰航道，未参与标定） | 7002–7155 | validation |
| s13 | ## | ④ 结果图 | 7155–9053 | — |
| s14 | ## | ⑤ 注意点 | 9053–9797 | uncertainty |
| s15 | ## | ⑥ 误差判定（是否 < 3%） | 9797–10636 | comparison |
| s16 | ## | 审计链 | 10636–11293 | — |

未映射的 4 节（标题行 / ③ 容器标题 / ④ 图注 / 审计链）均在 `structure.unmapped_sections` 里写明理由。

## ⑤ 注意点与局限

1. **标题三处不一致（如实保留，不调和）**：记录 title 为「…μ(I) 流变标定：孔隙率场、力链网络与**等效黏度（DEM）**」，
   正文 H1 为「…**动态演化与运动学**：孔隙率场、力链网络与 μ(I) 流变标定」。下游必须**按 report_id** 建键，
   不能按标题匹配。已记入 `unresolved: unres-9582-02-02`。
2. **`facility` 是真实缺失**：该信号要求物理实验装置，本报告是数值单元试验；我保留 miss 而不是把
   「数值装置」重解释为命中——否则错分会被 G3 以「claim 与原文类型不符」暴露。
3. **缺失判定是检索词级的，不是语义级的**：缺失项记录了检索词与命中数（可复跑），但中文报告里
   「英文信号串未命中」本身近乎恒真，所以我为每个信号配了双语检索词；仍存在我用词表覆盖不到的同义表述，
   这是本包已知的**残余不确定性**（置信度写作 medium-high 而非 high 的原因之一）。
4. **审计链里唯一的 `commit` 是无关尾注**：`<!-- m8301 / FEAT-OSS-INVENTORY-LBM / hemelb commit 432d3386 -->`
   与本报告的改动（`wall_velocity`）无对应关系，**不得**被下游当作本报告改动的提交号。这是故意记录的陷阱项。
5. **`unresolved` 只记 2 条**（facility 缺失、标题漂移）；其余不确定项写在 confidence_rationale 里，
   没有为了「好看」把不确定项清零，也没有为了「稳妥」虚构 unresolved。
6. **本包不判语义保真**：分类对不对最终由工序 04（独立审核，review.required=false 指本包不带审核）与平台门判定；
   本包的 `status` 一律 `draft`、证据一律 `assessment_status: unassessed`，**没有**把任何判定标成 verified。
7. **上游只读引用**：本包读取 `docs/kf/wp-9582-01/asset_manifest.json` 做源身份交叉核对
   （hash 相同 = True，chars 相同 = True），
   **未改写**该文件；01 包声明 6 张图 `png_bytes_present: false`，与本包「正文只有图注」的观察一致。
### 5.1 自陈局限（机器可读，`classification.json: limitations`）

| ID | 方面 | 说明 |
|---|---|---|
| lim-9582-02-01 | signal_selection_asymmetry | The experimental-validation signal 'facility' misses because the work is computational; the scientific-computation signals 'convergence study' / 'mesh refinement' / 'timing table' miss for the same inapplicability reason. Both are recorded as misses (symmetric treatment). Robustness check: if inapplicable signals are dropped from the denominator, experimental-validation scores 4/4 and scientific-computation 2/5 — the ranking does not change, so the primary type does not hinge on this. |
| lim-9582-02-02 | section_mapping_is_a_judgement | Mapping report sections onto the skill's setup/measurement/comparison/uncertainty/validation slots is a judgement; several sections could serve two slots (e.g. 3.3 equivalent viscosity is both a derived measurement and a literature-window comparison; 3.5 ablation is both comparison and validation). Each section was given its dominant slot only, to keep the downstream extraction instruction unambiguous. Re-slotting is a legitimate downstream revision. |
| lim-9582-02-03 | absence_is_term_based | Absence of a signal is measured with an explicit bilingual term list recorded in the product. A synonymous Chinese phrasing outside that list would be missed; this residual uncertainty is why confidence is medium-high, not high. |
| lim-9582-02-04 | mission_id_not_interpreted | The record carries mission_id 8301 (also echoed in the report footer as m8301). It is recorded verbatim and not interpreted; the work-package contract declares mission_id: null. |
| lim-9582-02-05 | no_semantic_verdict | This package does not judge whether the report's own scientific statements are true. Classification correctness is decided by工序04 / the platform gate; every record here is draft and unassessed. |

8. **来源可复现性**：`psql` 直读 `tensor_reports` 被权限拒绝，产物完全来自 API 响应；若平台 markdown 字段
   未来被改写，`verify.py` 的单检查 `source_hash_matches` 会立刻失败（fail-closed，不 skip）。

## ⑥ 自检：逐条对照 acceptance（honest，不粉饰）

| acceptance | 判定 | 依据 / detail |
|---|---|---|
| valid_json | PASS | `kf_result.json`、`classification.json` 均从磁盘重新解析成功 |
| schema_pass | PASS | `kf_result.json` 过 `schemas/kf_result.v1.schema.json`（jsonschema draft 2020-12） |
| source_locator_resolvable | PASS | 35 条 locator 的 `text[start:end] == quote`、`content_hash` 重算一致、引文唯一 |
| source_hash_matches | PASS | 重算 `sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f` = 契约 = 声明值 |
| no_duplicate_ids | PASS | 证据 35 / 节 16 / unresolved 2 各自无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | `claims.json=[]`（本工序不抽取，零 claim 合法）+ 2 条显式 unresolved |
| （附加）no claim marked verified | PASS | 全部 `epistemic_status=draft`、`assessment_status=unassessed`、`classification.status=draft` |
| （附加）upstream 01 源身份一致 | PASS | 与 `wp-9582-01` 的 source hash / chars 完全相同 |
| （附加）交付块唯一 | PASS | 本文件内 json 代码块计数 = 1，内容与 `kf_result.json` 语义相等 |

`verify.py` 复验结果：**30/30 checks passed**（
全部通过）。

| 状态 | 检查项 | detail |
|---|---|---|
| PASS | `valid_json.kf_result` |  |
| PASS | `valid_json.classification` |  |
| PASS | `schema_pass.kf_result_v1` | jsonschema validated |
| PASS | `source_hash_matches` | recomputed=sha256:cd99f31bff62… contract=sha256:cd99f31bff62… declared=sha256:cd99f31bff62… |
| PASS | `provenance.chars` | 11293 chars |
| PASS | `source_locator_resolvable.offsets` | 35 locators, bad=[] |
| PASS | `source_locator_resolvable.quote_hash` | bad=[] |
| PASS | `source_locator_resolvable.quote_uniqueness` | non-unique=[] |
| PASS | `no_duplicate_ids.evidence` | n=35 |
| PASS | `no_duplicate_ids.sections` | n=16 |
| PASS | `no_duplicate_ids.unresolved` | n=2 |
| PASS | `signals.evidence_xref_closed` | dangling=[] |
| PASS | `all_claims_have_evidence_or_explicit_unresolved_status` | claims.json=[] by design (task_type 02 does not extract); unresolved[] records the 2 open aspects |
| PASS | `no_claim_marked_verified` | all evidence draft/unassessed; classification.status=draft |
| PASS | `classification.report_type_in_registry` | experimental-validation |
| PASS | `classification.selected_skill_exists_and_matches` | xsk-experimental-validation -> experimental-validation |
| PASS | `classification.signal_table_covers_all_six_types` | 6 types |
| PASS | `classification.alternatives_cover_the_other_five` | each competing type has a stated decision |
| PASS | `record_meta_matches_source` | record says 11293 chars |
| PASS | `record_meta_matches_provenance` | title/scenario taken from the fetched record, not retyped |
| PASS | `source_locator_resolvable.nontrivial_quotes` | min len 20 chars, short=[] |
| PASS | `structure.every_section_mapped_or_noted` | mapped=12 noted=4 |
| PASS | `structure.skill_sections_complete` | ['comparison', 'measurement', 'setup', 'uncertainty', 'validation'] |
| PASS | `upstream_01_source_identity_consistent` | wp-9582-01 hash_equal=True chars_equal=True |
| PASS | `structure.section_spans_partition_source` | 16 headings cover [0,11293) |
| PASS | `structure.headings_verbatim` |  |
| PASS | `delivery.single_json_block` | json fences=1 |
| PASS | `delivery.title` |  |
| PASS | `delivery.tag` |  |
| PASS | `delivery.json_block_equals_kf_result` | block byte-equal semantics to kf_result.json |

**诚实说明**：上表最后一行 `delivery.single_json_block` 在 `verify.py` 单独运行时（本文件尚未生成/更新时）
会记为 FAIL/NOT RUN；本报告生成流程先写 `report.md` 再复跑校验，最终以 `verify.log` 的
30/30 checks passed 为准，不做粉饰。所有 `PASS` 均为**本地自查**，
平台门是权威判定者。

## repro_cmd（一键复跑）

cd <worktree-root>   # 以下命令都在仓库检出根目录执行

# 1) 登录拿 token
TOKEN=$(curl -s -X POST "$TENSOR_API_BASE/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$TENSOR_AGENT_USER\",\"password\":\"$TENSOR_AGENT_PASS\"}" \
  | python3 -c 'import json,sys;print(json.load(sys.stdin).get("access_token"))')

# 2) 取报告 9582 原文并按字节落盘（不得改动换行）
curl -s "$TENSOR_API_BASE/tensor/reports/9582" -H "Authorization: Bearer $TOKEN" -o /tmp/r9582.json
python3 -c "import json;m=json.load(open('/tmp/r9582.json'))['markdown'];open('docs/kf/wp-9582-02/source.md','w',encoding='utf-8',newline='').write(m)"

# 3) 重建产物（先分类结果，再自检 + 重写本报告；退出码 0 = 全绿）
python3 docs/kf/wp-9582-02/build.py
python3 docs/kf/wp-9582-02/make_report.py


`source.md` 也可离线复验：只要文件哈希仍是 `sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f`，`build.py` 与 `verify.py` 即可独立跑通
（`record_meta.json` 已随包保存）。注意 `build.py` 里的 `EXPECTED_HASH` 是契约常量：哈希不符即退出，不会静默放行。

## 机器可校验结果（唯一一个 json 代码块）

```json
{
  "package_id": "wp-9582-02",
  "task_type": "02-classification-parse",
  "contract_version": "1.0",
  "report_id": "9582",
  "provenance": {
    "source_uri": "tensor://reports/9582",
    "source_field": "markdown",
    "source_hash": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
    "source_hash_matches": true,
    "title": "P82W2-N02 碎冰堆积体 μ(I) 流变标定：孔隙率场、力链网络与等效黏度（DEM）",
    "scenario_key": "ice_rubble_rheology_dem",
    "chars": 11293
  },
  "outputs": {
    "classification.json": {
      "schema": "classification.v1",
      "package_id": "wp-9582-02",
      "task_type": "02-classification-parse",
      "contract_version": "1.0",
      "report_id": "9582",
      "source": {
        "uri": "tensor://reports/9582",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
        "chars": 11293,
        "bytes_utf8": 16772,
        "title_record": "P82W2-N02 碎冰堆积体 μ(I) 流变标定：孔隙率场、力链网络与等效黏度（DEM）",
        "title_markdown_h1": "P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定",
        "scenario_key": "ice_rubble_rheology_dem",
        "mission_id_record": 8301,
        "record_status": "published",
        "record_tags": [
          "DEM",
          "rubble",
          "mu(I)",
          "force-chain",
          "porosity",
          "rheology",
          "TensorDEM",
          "P82W2-N02",
          "P82W4-N02"
        ],
        "record_figures": [
          "porosity_fields.png",
          "mu_of_I_fit.png",
          "mu_I_residuals.png",
          "force_chain_vs_I.png",
          "contact_orientation.png",
          "viscosity.png"
        ],
        "citation_token_counts": {
          "et al.": 1,
          "et al": 1,
          "Guimarães": 1,
          "doi": 0,
          "(20": 0,
          "（20": 0
        },
        "citation_density_per_kchar": 0.2657
      },
      "classification": {
        "report_type": "experimental-validation",
        "report_type_is_hypothesis": true,
        "status": "draft",
        "confidence": "medium-high",
        "confidence_rationale": "4 of 5 experimental-validation signals are present with locators (test matrix, measurement uncertainty, validation case, baseline comparison); the single miss (physical facility) is a genuine miss because the work is a numerical element-test campaign. The runner-up software-engineering type matches 3 of 5 signals, so the decision is a judgement about what the report is *about* (a calibration/validation study whose code change is instrumental), not a mechanical signal count.",
        "selected_skill_id": "xsk-experimental-validation",
        "skill_version": "0.1.0",
        "skill_lifecycle_state": "template-created",
        "signal_table": {
          "experimental-validation": [
            {
              "signal": "test matrix",
              "presence": "present",
              "evidence_refs": [
                "ev-9582-02-03"
              ]
            },
            {
              "signal": "facility",
              "presence": "absent",
              "evidence_refs": [
                "ev-9582-02-23",
                "ev-9582-02-24",
                "ev-9582-02-25"
              ],
              "basis": "search_terms_measured_on_markdown + cited text",
              "search_terms": {
                "facility": 0,
                "实验台": 0,
                "试验台": 0,
                "水槽": 0,
                "冰池": 0,
                "拖曳水池": 0
              },
              "total_hits": 0,
              "note": "no physical facility: the device is a 2-D periodic-strain numerical cell, and ev-9582-02-23/24/25 give the numerical setup instead. Recorded as a real miss of the signal, not reinterpreted as a hit."
            },
            {
              "signal": "measurement uncertainty",
              "presence": "present",
              "evidence_refs": [
                "ev-9582-02-04",
                "ev-9582-02-05",
                "ev-9582-02-06",
                "ev-9582-02-30"
              ]
            },
            {
              "signal": "validation case",
              "presence": "present",
              "evidence_refs": [
                "ev-9582-02-07",
                "ev-9582-02-08"
              ]
            },
            {
              "signal": "baseline comparison",
              "presence": "present",
              "evidence_refs": [
                "ev-9582-02-09",
                "ev-9582-02-10",
                "ev-9582-02-11"
              ]
            }
          ],
          "scientific-computation": [
            {
              "signal": "governing equations",
              "presence": "partial",
              "evidence_refs": [
                "ev-9582-02-12",
                "ev-9582-02-16"
              ],
              "note": "constitutive/definition relations (mu(I), I, eta, Love-Weber virial) are written; no governing PDE or contact-dynamics evolution equation is stated"
            },
            {
              "signal": "discretisation",
              "presence": "partial",
              "evidence_refs": [
                "ev-9582-02-14",
                "ev-9582-02-15"
              ],
              "note": "only the post-processing grid h = 5 d50 is discretisation-specified; solver time integration is not described"
            },
            {
              "signal": "convergence study",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "convergence": 0,
                "收敛": 0,
                "收敛性研究": 0,
                "网格收敛": 0,
                "收敛阶": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            },
            {
              "signal": "mesh refinement",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "mesh refinement": 0,
                "refinement": 0,
                "网格加密": 0,
                "网格无关性": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            },
            {
              "signal": "timing table",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "timing": 0,
                "wall-clock": 0,
                "计时": 0,
                "耗时": 0,
                "性能表": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            }
          ],
          "software-engineering": [
            {
              "signal": "changed files",
              "presence": "partial",
              "evidence_refs": [
                "ev-9582-02-33"
              ],
              "note": "file paths are listed in the audit chain; no diff/hunk is shown"
            },
            {
              "signal": "commit",
              "presence": "absent",
              "evidence_refs": [
                "ev-9582-02-19"
              ],
              "basis": "search_terms_measured_on_markdown + cited text",
              "search_terms": {
                "commit": 1,
                "提交": 0,
                "sha": 1,
                "git ": 0
              },
              "total_hits": 2,
              "note": "the only 'commit' token is an unrelated hemelb trailer in a footer comment; it cannot be read as the commit of this report's change, so the signal is a miss (and is a trap worth recording for downstream extraction)"
            },
            {
              "signal": "interface",
              "presence": "present",
              "evidence_refs": [
                "ev-9582-02-17"
              ]
            },
            {
              "signal": "regression",
              "presence": "present",
              "evidence_refs": [
                "ev-9582-02-18"
              ]
            },
            {
              "signal": "API",
              "presence": "partial",
              "evidence_refs": [
                "ev-9582-02-17",
                "ev-9582-02-16"
              ],
              "note": "API-level identifiers (wall_velocity, bulk_deformation_rate) appear, but as method description, not as API documentation"
            }
          ],
          "algorithm-implementation": [
            {
              "signal": "algorithm block",
              "presence": "partial",
              "evidence_refs": [
                "ev-9582-02-21"
              ],
              "note": "a numbered procedure block exists, but it is a data-analysis recipe"
            },
            {
              "signal": "pseudocode",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "pseudocode": 0,
                "伪代码": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            },
            {
              "signal": "complexity",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "complexity": 0,
                "时间复杂度": 0,
                "复杂度": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            },
            {
              "signal": "function signature",
              "presence": "absent",
              "evidence_refs": [],
              "basis": "search_terms_measured_on_markdown + cited text",
              "search_terms": {
                "def ": 0,
                "(": 52,
                ") ->": 0
              },
              "total_hits": 52,
              "note": "no function signature appears in the markdown (identifiers only: wall_velocity, bulk_deformation_rate, RubbleNoContactsError)"
            }
          ],
          "literature-review": [
            {
              "signal": "related work",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "related work": 0,
                "相关工作": 0,
                "state of the art": 0,
                "研究现状": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            },
            {
              "signal": "survey",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "survey": 0,
                "综述": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            },
            {
              "signal": "bibliography",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "bibliography": 0,
                "参考文献": 0,
                "References": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            },
            {
              "signal": "citation density >= 5 per 1000 chars",
              "presence": "absent",
              "evidence_refs": [
                "ev-9582-02-20"
              ],
              "basis": "search_terms_measured_on_markdown + cited text",
              "search_terms": {
                "et al.": 1,
                "Guimarães": 1,
                "doi": 0,
                "(20": 0,
                "（20": 0
              },
              "total_hits": 2,
              "note": "measured citation-ish token count 3 over 11.29 kchar -> density 0.2657; one anchor work only, and it is flagged WITHHELD for point-wise comparison"
            }
          ],
          "technical-proposal": [
            {
              "signal": "roadmap / proposal",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "roadmap": 0,
                "proposal": 0,
                "路线图": 0,
                "提案": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            },
            {
              "signal": "specification",
              "presence": "absent",
              "basis": "search_terms_measured_on_markdown",
              "search_terms": {
                "specification": 0,
                "规格书": 0,
                "规格说明": 0
              },
              "total_hits": 0,
              "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, re-runnable via build.py / verify.py"
            },
            {
              "signal": "design",
              "presence": "absent",
              "evidence_refs": [],
              "basis": "search_terms_measured_on_markdown + cited text",
              "search_terms": {
                "design": 0,
                "设计": 2,
                "方案": 0
              },
              "total_hits": 2,
              "note": "the text reports executed runs and measured values; it does not propose a design to be built"
            }
          ]
        },
        "alternatives_considered": [
          {
            "report_type": "software-engineering",
            "decision": "rejected_as_primary",
            "rank": 2,
            "signals_matched": 3,
            "reason": "the report does contain an engine-level change (wall velocity with backward-compatible default) plus regression tests, and one ablation section is devoted to it; but the change occupies part of section ② and the audit chain, while the deliverable quantity of the report is the (I, mu) point set, the fit law and the acceptance criteria. Extracting this report as a software change would miss the measured conditions and their uncertainty.",
            "evidence_refs": [
              "ev-9582-02-17",
              "ev-9582-02-18",
              "ev-9582-02-19",
              "ev-9582-02-29"
            ],
            "residual_risk": "if工序03 wants change-scope claims, run xsk-software-engineering as a secondary skill"
          },
          {
            "report_type": "scientific-computation",
            "decision": "rejected_as_primary",
            "rank": 3,
            "signals_matched": 0,
            "signals_partial": 2,
            "reason": "the constitutive law and the Love-Weber stress definition are written, and a post-processing grid is specified, but there is no governing PDE, no discretisation of a solver, and - measured - zero occurrences of convergence/mesh-refinement/timing terms. A scientific-computation skill would demand a convergence study this report does not have.",
            "evidence_refs": [
              "ev-9582-02-12",
              "ev-9582-02-13",
              "ev-9582-02-14",
              "ev-9582-02-16"
            ]
          },
          {
            "report_type": "algorithm-implementation",
            "decision": "rejected_as_primary",
            "rank": 4,
            "signals_matched": 1,
            "reason": "a numbered post-processing recipe exists, but no pseudocode, complexity statement or function signature; the algorithmic content is a data-analysis recipe, not an algorithm report.",
            "evidence_refs": [
              "ev-9582-02-15",
              "ev-9582-02-21"
            ]
          },
          {
            "report_type": "literature-review",
            "decision": "rejected_as_primary",
            "rank": 5,
            "signals_matched": 0,
            "reason": "one literature anchor (Guimarães et al. 2022), explicitly flagged WITHHELD for point-wise comparison; measured citation-token density far below the >=5 per 1000 chars signal.",
            "evidence_refs": [
              "ev-9582-02-20"
            ]
          },
          {
            "report_type": "technical-proposal",
            "decision": "rejected_as_primary",
            "rank": 6,
            "signals_matched": 0,
            "reason": "no proposal/roadmap/specification; the text reports already-executed runs under pre-registered thresholds rather than proposing future work.",
            "evidence_refs": [
              "ev-9582-02-22"
            ]
          }
        ]
      },
      "topics": {
        "scenario_key": "ice_rubble_rheology_dem",
        "discipline": "ship_ice_navigation",
        "subdiscipline": "ice_resistance_and_loads",
        "method_family": "discrete_element_method",
        "layers": [
          "DEM",
          "ice_rubble_rheology_dem",
          "l"
        ],
        "tags": [
          "DEM",
          "mu(I)-rheology",
          "ice-rubble",
          "porosity-field",
          "force-chain",
          "equivalent-viscosity",
          "couette-shear",
          "biaxial-compression",
          "ice-channel",
          "uncertainty-budget",
          "model-form-error",
          "honest-FAIL",
          "pre-registration"
        ],
        "topic_scope": "calibration and out-of-sample validation of a mu(I) constitutive law for ice rubble, plus micro-structural descriptors (porosity field, force-chain network) usable by continuum ice-load models"
      },
      "structure": {
        "section_count": 16,
        "sections": [
          {
            "section_id": "s01",
            "level": 1,
            "heading": "P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定",
            "start_offset": 0,
            "end_offset": 48,
            "chars": 48
          },
          {
            "section_id": "s02",
            "level": 2,
            "heading": "① 案例介绍",
            "start_offset": 48,
            "end_offset": 672,
            "chars": 624,
            "skill_sections": [
              "setup"
            ]
          },
          {
            "section_id": "s03",
            "level": 2,
            "heading": "② 怎么做的",
            "start_offset": 672,
            "end_offset": 1885,
            "chars": 1213,
            "skill_sections": [
              "setup"
            ]
          },
          {
            "section_id": "s04",
            "level": 2,
            "heading": "③ 计算结果",
            "start_offset": 1885,
            "end_offset": 1896,
            "chars": 11
          },
          {
            "section_id": "s05",
            "level": 3,
            "heading": "3.1 各条件的流变点（条件均值，seed 为重复）",
            "start_offset": 1896,
            "end_offset": 3396,
            "chars": 1500,
            "skill_sections": [
              "measurement"
            ]
          },
          {
            "section_id": "s06",
            "level": 3,
            "heading": "3.2 μ(I) 拟合（三种聚合口径，全部如实列出）",
            "start_offset": 3396,
            "end_offset": 3907,
            "chars": 511,
            "skill_sections": [
              "comparison"
            ]
          },
          {
            "section_id": "s07",
            "level": 3,
            "heading": "3.3 等效黏度（η = μP/γ̇，参考态 γ̇ = 0.1 s⁻¹）",
            "start_offset": 3907,
            "end_offset": 4270,
            "chars": 363,
            "skill_sections": [
              "measurement"
            ]
          },
          {
            "section_id": "s08",
            "level": 3,
            "heading": "3.4 孔隙率场与力链微结构",
            "start_offset": 4270,
            "end_offset": 4758,
            "chars": 488,
            "skill_sections": [
              "measurement"
            ]
          },
          {
            "section_id": "s09",
            "level": 3,
            "heading": "3.5 压缩单元试验运动学消融（本次修正的直接证据）",
            "start_offset": 4758,
            "end_offset": 5435,
            "chars": 677,
            "skill_sections": [
              "validation"
            ]
          },
          {
            "section_id": "s10",
            "level": 3,
            "heading": "3.6 判据 (c) 的噪声预算：残差是结构性的还是统计的？",
            "start_offset": 5435,
            "end_offset": 6446,
            "chars": 1011,
            "skill_sections": [
              "uncertainty"
            ]
          },
          {
            "section_id": "s11",
            "level": 3,
            "heading": "3.7 机器可算验收判据",
            "start_offset": 6446,
            "end_offset": 7002,
            "chars": 556,
            "skill_sections": [
              "comparison"
            ]
          },
          {
            "section_id": "s12",
            "level": 3,
            "heading": "3.8 样本外验证（碎冰航道，未参与标定）",
            "start_offset": 7002,
            "end_offset": 7155,
            "chars": 153,
            "skill_sections": [
              "validation"
            ]
          },
          {
            "section_id": "s13",
            "level": 2,
            "heading": "④ 结果图",
            "start_offset": 7155,
            "end_offset": 9053,
            "chars": 1898
          },
          {
            "section_id": "s14",
            "level": 2,
            "heading": "⑤ 注意点",
            "start_offset": 9053,
            "end_offset": 9797,
            "chars": 744,
            "skill_sections": [
              "uncertainty"
            ]
          },
          {
            "section_id": "s15",
            "level": 2,
            "heading": "⑥ 误差判定（是否 < 3%）",
            "start_offset": 9797,
            "end_offset": 10636,
            "chars": 839,
            "skill_sections": [
              "comparison"
            ]
          },
          {
            "section_id": "s16",
            "level": 2,
            "heading": "审计链",
            "start_offset": 10636,
            "end_offset": 11293,
            "chars": 657
          }
        ],
        "skill_section_map": {
          "setup": [
            "s02",
            "s03"
          ],
          "measurement": [
            "s05",
            "s07",
            "s08"
          ],
          "comparison": [
            "s06",
            "s11",
            "s15"
          ],
          "uncertainty": [
            "s10",
            "s14"
          ],
          "validation": [
            "s09",
            "s12"
          ]
        },
        "unmapped_sections": {
          "s01": "document title (H1), no skill section",
          "s04": "container heading '③ 计算结果'; its content lives in the 3.x subsections",
          "s13": "figure-caption section; figures live in the platform figures field, not in the body",
          "s16": "audit chain (pre-registration / code / artifact pointers), no skill section"
        },
        "notes": "offsets are Python character indices into the markdown field (unicode code points), computed by build.py from the fetched bytes; section spans run to the next heading."
      },
      "classification_evidence": [
        {
          "id": "ev-9582-02-01",
          "aspect": "identity.title",
          "statement": "报告 H1 自述标题（与记录 title 存在措辞差异，见 limitations.title_drift）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "# P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定",
            "start_offset": 0,
            "end_offset": 46,
            "quote": "# P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定",
            "content_hash": "sha256:14017a1acb7c520a06f9dae81a95184b7f5f498fe35913aea2b028a390a23af2"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-02",
          "aspect": "purpose.problem_class",
          "statement": "报告把自身定位为船舶冰阻力/冰载荷连续模型的等效介质来源，属于应用物理量标定类工作",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "碎冰（rubble）堆积体是船舶冰阻力与冰载荷模型的等效连续介质来源。",
            "start_offset": 59,
            "end_offset": 94,
            "quote": "碎冰（rubble）堆积体是船舶冰阻力与冰载荷模型的等效连续介质来源。",
            "content_hash": "sha256:6c14e8491261ebf0f7f2d8ccac28a9b20331ab3901d0f43775b3d88e3eb4aaa4"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-03",
          "aspect": "type.experimental-validation.test_matrix",
          "statement": "test matrix 信号命中：工况矩阵显式给出 runs/条件/seed 重复数",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 工况数 | 54 runs，19 个（场景, 固体分数, 速率）条件；剪切/压缩每条件 3 个 seed，航道 2 个 |",
            "start_offset": 510,
            "end_offset": 573,
            "quote": "| 工况数 | 54 runs，19 个（场景, 固体分数, 速率）条件；剪切/压缩每条件 3 个 seed，航道 2 个 |",
            "content_hash": "sha256:1d89d398070a15cfa92c786aaa1e5b9bf3e16fa3a80bb99731beb897c0ad42b6"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-04",
          "aspect": "type.experimental-validation.measurement_uncertainty",
          "statement": "measurement uncertainty 信号命中之二：条件均值标准误作为统计噪声量化",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 条件均值 μ 的平均标准误（统计噪声） | 0.0102 |",
            "start_offset": 5579,
            "end_offset": 5611,
            "quote": "| 条件均值 μ 的平均标准误（统计噪声） | 0.0102 |",
            "content_hash": "sha256:ee0aee9d5600017b187ad1d1ae0ea2d89bc683cd673ec59423be9e01d1d1acd7"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-05",
          "aspect": "type.experimental-validation.uncertainty_budget",
          "statement": "噪声预算专节（残差 vs 统计噪声的可分辨性判据）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "### 3.6 判据 (c) 的噪声预算：残差是结构性的还是统计的？",
            "start_offset": 5435,
            "end_offset": 5469,
            "quote": "### 3.6 判据 (c) 的噪声预算：残差是结构性的还是统计的？",
            "content_hash": "sha256:62d78171d9d65df7622f77e6199fdc6308cfdab96dd0a1500b4c9b9a32d23b2e"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-06",
          "aspect": "type.experimental-validation.signal_vs_noise",
          "statement": "信号-噪声对照：条件间标准差作为信号量级",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| μ 的条件间标准差（信号） | 0.0281 |",
            "start_offset": 5525,
            "end_offset": 5551,
            "quote": "| μ 的条件间标准差（信号） | 0.0281 |",
            "content_hash": "sha256:35f2664855c384b20ece4fbc70f4664fba5762afcb2f69c67cee80b979a0c693"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-07",
          "aspect": "type.experimental-validation.validation_case",
          "statement": "validation case 信号命中：样本外验证场景显式声明未参与标定",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "### 3.8 样本外验证（碎冰航道，未参与标定）",
            "start_offset": 7002,
            "end_offset": 7027,
            "quote": "### 3.8 样本外验证（碎冰航道，未参与标定）",
            "content_hash": "sha256:d2c2595a1c0218574e6155c15352d59345108da6d01dfc4bf21f6403ac75a8a2"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-08",
          "aspect": "type.experimental-validation.validation_result",
          "statement": "样本外验证给出偏差数值与离散度（含符号），保留为模型形式误差",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "6 个航道 run 的实测 μ 与单元试验律预测之差 = -0.1698 ± 0.0182（相对误差均值 -2.25），压力 6186–9191 Pa。",
            "start_offset": 7028,
            "end_offset": 7104,
            "quote": "6 个航道 run 的实测 μ 与单元试验律预测之差 = -0.1698 ± 0.0182（相对误差均值 -2.25），压力 6186–9191 Pa。",
            "content_hash": "sha256:87b931bb1848206bce7233c913766429071485b78d929f56b08fabd033a12fa6"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-09",
          "aspect": "type.experimental-validation.baseline_comparison",
          "statement": "baseline/threshold 对照信号命中：预注册阈值 vs 实测 vs 结论四列表",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 判据 | 阈值 | 实测 | 结论 |",
            "start_offset": 6464,
            "end_offset": 6485,
            "quote": "| 判据 | 阈值 | 实测 | 结论 |",
            "content_hash": "sha256:dabdeb587171f23b7c4bf013d4282c27d0d5f1b15868d39746124771774a0abd"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-10",
          "aspect": "type.experimental-validation.honest_fail",
          "statement": "主判据被判 FAIL(honest)，报告未把失败改写为通过",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| (c) μ(I) 拟合优度（主判据：合并单元试验） | R²≥0.95, σ≤0.05 | R²=0.8035, σ=0.0134 | **FAIL (honest)** |",
            "start_offset": 6603,
            "end_offset": 6692,
            "quote": "| (c) μ(I) 拟合优度（主判据：合并单元试验） | R²≥0.95, σ≤0.05 | R²=0.8035, σ=0.0134 | **FAIL (honest)** |",
            "content_hash": "sha256:f3e851bd874d769e8fd89adf3273ce4fbe1ef4e8664320c449ba5cce2e28bef9"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-11",
          "aspect": "type.experimental-validation.baseline_semantics",
          "statement": "对照基准的语义被显式限定为量级窗（不是逐点基准），属保留不确定性的写法",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| η(0.1 s⁻¹, 10 kPa) vs 文献窗 | [1e3, 1e5] Pa·s（量级窗，非逐点） | 2.512e+04 | 窗内（不作 % 判定，基准为量级窗） |",
            "start_offset": 10146,
            "end_offset": 10235,
            "quote": "| η(0.1 s⁻¹, 10 kPa) vs 文献窗 | [1e3, 1e5] Pa·s（量级窗，非逐点） | 2.512e+04 | 窗内（不作 % 判定，基准为量级窗） |",
            "content_hash": "sha256:129704f94fbbe86e9bf054cdef97b50bdbc9ac8c0364d17e2ff29c731088adde"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-12",
          "aspect": "type.scientific-computation.governing_equation_partial",
          "statement": "二次流变律与 I/μ/η 定义被写出（构关系式，非控制方程）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "（3）宏观流变点 (I, μ) 与二次流变律 μ(I) = μ₀ + αI + βI²，并给出等效黏度 η = μP/γ̇ 与文献锚点对照。",
            "start_offset": 186,
            "end_offset": 256,
            "quote": "（3）宏观流变点 (I, μ) 与二次流变律 μ(I) = μ₀ + αI + βI²，并给出等效黏度 η = μP/γ̇ 与文献锚点对照。",
            "content_hash": "sha256:47f7d45d03e90925fa25ab47df251965f105d4aa6695d5f9b303e9834fe30833"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-13",
          "aspect": "type.scientific-computation.fitted_law",
          "statement": "拟合得到的本构律及适用 I 区间（含区间端点）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "主判据律：μ(I) = 0.2498 +2.028 I -12.984 I²，覆盖 I ∈ [4.330e-03, 0.0674]。",
            "start_offset": 3838,
            "end_offset": 3904,
            "quote": "主判据律：μ(I) = 0.2498 +2.028 I -12.984 I²，覆盖 I ∈ [4.330e-03, 0.0674]。",
            "content_hash": "sha256:e46ee4c59a33c8b80dbb1b150ae2bee157b7608a86b047f5f278d20482bacac5"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-14",
          "aspect": "type.scientific-computation.discretisation_partial",
          "statement": "仅后处理网格被离散化规定（h=5d50 且给出铺满偏差）——求解器离散/时间积分未描述",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 后处理网格 | h = 5 d₅₀（单元格精确铺满域，h/d₅₀ = 5.0 ± 0.5%） |",
            "start_offset": 574,
            "end_offset": 624,
            "quote": "| 后处理网格 | h = 5 d₅₀（单元格精确铺满域，h/d₅₀ = 5.0 ± 0.5%） |",
            "content_hash": "sha256:2ec81ad868eec89681a0145b84992b294f226b3f40ca8d34168443968142a1e7"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-15",
          "aspect": "type.scientific-computation.postprocess_method",
          "statement": "后处理方法被逐条编号描述（Voronoi/Delaunay 逐颗粒量）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "2. Voronoi/Delaunay：中心点镶嵌（周期像/闭壁镜像）给逐颗粒 φᵢ = 1 − A_disk/A_cell 与 Delaunay 边长/d₅₀。",
            "start_offset": 856,
            "end_offset": 937,
            "quote": "2. Voronoi/Delaunay：中心点镶嵌（周期像/闭壁镜像）给逐颗粒 φᵢ = 1 − A_disk/A_cell 与 Delaunay 边长/d₅₀。",
            "content_hash": "sha256:2627eb9e9242721337194099f55fdb352b9bd4610b4647f77b65278301d314a0"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-16",
          "aspect": "type.scientific-computation.stress_definition",
          "statement": "宏观应力的位力定义与 I 的定义式、无量纲化方式被写出",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "4. 宏观量：Love–Weber 位力 σ = −(1/V)Σf⊗b（压为正），P = trσ/2，τ = (σ₁−σ₂)/2，μ = τ/P；I = γ̇d₅₀/√(P/ρ)，γ̇ 三场景一律取**实测**值：剪切/航道用本体速度剖面斜率，压缩用本体速度梯度 `bulk_deformation_rate` 的 √(2D:D)（本次修正，见 3.5）。",
            "start_offset": 1047,
            "end_offset": 1225,
            "quote": "4. 宏观量：Love–Weber 位力 σ = −(1/V)Σf⊗b（压为正），P = trσ/2，τ = (σ₁−σ₂)/2，μ = τ/P；I = γ̇d₅₀/√(P/ρ)，γ̇ 三场景一律取**实测**值：剪切/航道用本体速度剖面斜率，压缩用本体速度梯度 `bulk_deformation_rate` 的 √(2D:D)（本次修正，见 3.5）。",
            "content_hash": "sha256:1871e496b7f1f78ad08599ae680ca7e0fbcfe72ae43954828618d05a5ce33b60"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-17",
          "aspect": "type.software-engineering.interface",
          "statement": "引擎接口变更被显式声明，并声明默认值保持历史行为（向后兼容）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "- 剪切：x 周期、上下粗糙壁**反向滑动**（±v/2，几何不动）。为此给引擎新增逐段壁面速度 `wall_velocity`（默认 None = 历史行为逐位不变）。γ̇ 由本体切片（离壁 ≥3r̄）速度剖面最小二乘斜率给出。",
            "start_offset": 1371,
            "end_offset": 1486,
            "quote": "- 剪切：x 周期、上下粗糙壁**反向滑动**（±v/2，几何不动）。为此给引擎新增逐段壁面速度 `wall_velocity`（默认 None = 历史行为逐位不变）。γ̇ 由本体切片（离壁 ≥3r̄）速度剖面最小二乘斜率给出。",
            "content_hash": "sha256:1d452bf5414f289249bccbb0850970d13ecfbb6a6123097cf8e7514096ead923"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-18",
          "aspect": "type.software-engineering.regression",
          "statement": "回归证据以测试项数（含负控）形式给出",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "- 测试：`tests/test_rubble_postprocess.py`（19 项，含 4 个负控）+ `tests/test_rubble_kinematics.py`（5 项，运动学一致性）",
            "start_offset": 11125,
            "end_offset": 11225,
            "quote": "- 测试：`tests/test_rubble_postprocess.py`（19 项，含 4 个负控）+ `tests/test_rubble_kinematics.py`（5 项，运动学一致性）",
            "content_hash": "sha256:60ff045be14bcb8801b7d4cdc885f8cf104499a42ccc2d8aa5fed84c8b09203d"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-19",
          "aspect": "type.software-engineering.commit_trailer",
          "statement": "全文唯一出现 commit 的位置是尾部注释里的 hemelb commit，与被分类报告的改动无对应关系——不可当作本报告改动提交号",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "<!-- m8301 / FEAT-OSS-INVENTORY-LBM / hemelb commit 432d3386 -->",
            "start_offset": 11228,
            "end_offset": 11292,
            "quote": "<!-- m8301 / FEAT-OSS-INVENTORY-LBM / hemelb commit 432d3386 -->",
            "content_hash": "sha256:bc922c2decfd223bb238f50544b4f89351922078b52bb1ddda6a9ae9aa3b0076"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-20",
          "aspect": "type.literature-review.citation_density",
          "statement": "全文唯一可解析的文献引证为 Guimarães et al. 2022，且被标注为量级窗/逐点 WITHHELD——不构成综述型引证密度",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "6. **文献锚点为量级窗**：Guimarães et al. 2022 未数字化逐点数据，逐点对比标注 WITHHELD。",
            "start_offset": 9642,
            "end_offset": 9705,
            "quote": "6. **文献锚点为量级窗**：Guimarães et al. 2022 未数字化逐点数据，逐点对比标注 WITHHELD。",
            "content_hash": "sha256:83b2cf3de8c751c6e15bf4760420f33556399c2b9e6d59ba5fff93e9bb7d2445"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-21",
          "aspect": "type.algorithm-implementation.procedure_block",
          "statement": "算法的编号步骤块存在（后处理 1–5 步），但没有伪码/复杂度/函数签名",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "3. 力链：按接触力分位切分强弱链（互补掩码），方向折叠到 [0,π)，结构张量 R = ⟨nn⟩ 给 A_c = 2(λ₁−λ₂)/(λ₁+λ₂)，强子图连通分量与横跨判定（判据 b 双审计：接触数 + 力求和）。",
            "start_offset": 938,
            "end_offset": 1046,
            "quote": "3. 力链：按接触力分位切分强弱链（互补掩码），方向折叠到 [0,π)，结构张量 R = ⟨nn⟩ 给 A_c = 2(λ₁−λ₂)/(λ₁+λ₂)，强子图连通分量与横跨判定（判据 b 双审计：接触数 + 力求和）。",
            "content_hash": "sha256:c046b9193b400bb1144d4311e3e7290a1234fb2219eb016c601b0e253881d64c"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-22",
          "aspect": "type.technical-proposal.absent_plan",
          "statement": "报告以「先声明阈值、后扫描」的预注册执行链呈现，而不是提案/路线图",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "- 预注册：`prereg/rubble_rheology_prereg.json`（阈值先声明；Amendment 1 = 等面积压缩 + 航道改作验证；Amendment 2 = 本次两个运动学修正、被否决的仿射速度重映射、双固体分数设计，均写于生产扫描之前）",
            "start_offset": 10644,
            "end_offset": 10776,
            "quote": "- 预注册：`prereg/rubble_rheology_prereg.json`（阈值先声明；Amendment 1 = 等面积压缩 + 航道改作验证；Amendment 2 = 本次两个运动学修正、被否决的仿射速度重映射、双固体分数设计，均写于生产扫描之前）",
            "content_hash": "sha256:33e0e555431428c67a90b2fbb106f09521573601fdc6428981e7f4a6093429a0"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-23",
          "aspect": "setup.numerical_cell",
          "statement": "实验/数值装置的类型与几何被声明：二维平面应变 + 周期 x，属«数值单元试验»而非物理实验台",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 几何/维度 | 二维平面应变，周期 x（航道场景 x 周期 + 固定船体） |",
            "start_offset": 280,
            "end_offset": 321,
            "quote": "| 几何/维度 | 二维平面应变，周期 x（航道场景 x 周期 + 固定船体） |",
            "content_hash": "sha256:762abda83f21f6f9497d1902409f2c280bf30751b6f93a6a07a9f826ac60ada3"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-24",
          "aspect": "setup.material",
          "statement": "材料/颗粒参数被给出（双分散刚性圆盘、d50、密度）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 颗粒 | 双分散刚性圆盘，d₅₀ = 0.02359 m，密度 ρ = 917 kg/m³ |",
            "start_offset": 322,
            "end_offset": 371,
            "quote": "| 颗粒 | 双分散刚性圆盘，d₅₀ = 0.02359 m，密度 ρ = 917 kg/m³ |",
            "content_hash": "sha256:7a531f851ff0c563b170e4c8ceb2a94a16302d0683df6ae23acef6c95deb197f"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-25",
          "aspect": "setup.contact_model",
          "statement": "接触模型与摩擦/刚度参数被给出（Hertz–Mindlin + Coulomb + 滚动阻力）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 接触 | Hertz–Mindlin 法向/切向 + Coulomb 摩擦 μ_p = 0.5 + 滚动阻力 0.05，kn = 3.0e4 N/m，板厚 0.03 m |",
            "start_offset": 372,
            "end_offset": 460,
            "quote": "| 接触 | Hertz–Mindlin 法向/切向 + Coulomb 摩擦 μ_p = 0.5 + 滚动阻力 0.05，kn = 3.0e4 N/m，板厚 0.03 m |",
            "content_hash": "sha256:1c5fca4a5f6f2719567b2609deb3318cdcb6f789a409d4592c39c03be5712faf"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-26",
          "aspect": "setup.scenarios",
          "statement": "三类场景被显式枚举，决定了 3.1 表的分组结构",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 场景 | 简单剪切（粗糙滑动壁 Couette）/ 等面积平面应变压缩 / 碎冰航道漂移 |",
            "start_offset": 461,
            "end_offset": 509,
            "quote": "| 场景 | 简单剪切（粗糙滑动壁 Couette）/ 等面积平面应变压缩 / 碎冰航道漂移 |",
            "content_hash": "sha256:c4fb36b7b35f3844ee64a8c7c0a98ce82cbfa23700c7ba4e9c86dc9c00d0414e"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-27",
          "aspect": "measurement.result_table_shear",
          "statement": "条件级结果表的列结构（含 seeds 与标准误）——03 抽取的条件/重复单元定义",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 场景 | 名义速率 | seeds | P [Pa] | I | μ | μ 标准误 |",
            "start_offset": 1928,
            "end_offset": 1974,
            "quote": "| 场景 | 名义速率 | seeds | P [Pa] | I | μ | μ 标准误 |",
            "content_hash": "sha256:a559b4bb4ce22e1573f1c83dc65f37b21b0abf2a677518f257afbb68c51bc716"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-28",
          "aspect": "measurement.fit_table",
          "statement": "拟合结果表的列结构（μ₀/α/β/R²/残差/n）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "| 口径 | μ₀ | α | β | R² | 残差标准差 | n |",
            "start_offset": 3428,
            "end_offset": 3464,
            "quote": "| 口径 | μ₀ | α | β | R² | 残差标准差 | n |",
            "content_hash": "sha256:d70fd92a18e77becf7f876b98a71edaeb53b7600a727821cf689bc6a3929ebf5"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-29",
          "aspect": "comparison.ablation",
          "statement": "消融对照设计存在（legacy/piston/remap × 两个名义速率）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "### 3.5 压缩单元试验运动学消融（本次修正的直接证据）",
            "start_offset": 4758,
            "end_offset": 4788,
            "quote": "### 3.5 压缩单元试验运动学消融（本次修正的直接证据）",
            "content_hash": "sha256:a9c1a14e2cb976733a3017dd73b02fa392dc946e39aa0f46a30ce5eec1375f83"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-30",
          "aspect": "limitations.finite_size",
          "statement": "有限尺寸涨落被量化为局限（N≈400，seed 间/条件级离散度）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "4. **有限尺寸涨落**：N≈400 圆盘，seed 间 μ 标准差 0.01–0.02，条件标准误 0.005–0.010；12 快照平均后的条件均值仍是判据 (c) 的主要噪声源。",
            "start_offset": 9484,
            "end_offset": 9577,
            "quote": "4. **有限尺寸涨落**：N≈400 圆盘，seed 间 μ 标准差 0.01–0.02，条件标准误 0.005–0.010；12 快照平均后的条件均值仍是判据 (c) 的主要噪声源。",
            "content_hash": "sha256:1478860d7fd565e31e87ad324f945490d14fa33a1c12bb2ef113c51e2e0f0802"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-31",
          "aspect": "comparison.honest_conclusion",
          "statement": "报告的诚实结论段把数值层误差与物理层 FAIL 分开陈述",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "**诚实结论**：数值/守恒/拟合器层面误差 ≪3%；物理层面「单一 μ(I) 跨三场景」主判据 honest FAIL（R² = 0.8035 < 0.95，残差 σ = 0.0134）。",
            "start_offset": 10296,
            "end_offset": 10391,
            "quote": "**诚实结论**：数值/守恒/拟合器层面误差 ≪3%；物理层面「单一 μ(I) 跨三场景」主判据 honest FAIL（R² = 0.8035 < 0.95，残差 σ = 0.0134）。",
            "content_hash": "sha256:236c98041fa2d51bb92873e89b50762a63182b0e94b8672a88d4da9a42d68b10"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-32",
          "aspect": "measurement.figures_declared",
          "statement": "报告声明了 6 张图并给出英文图注（图为平台侧 figures 字段，正文仅有说明）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "**porosity_fields.png** — Porosity field phi(x,t) of one steady snapshot per scenario on the required grid h = 5 d50.",
            "start_offset": 7165,
            "end_offset": 7282,
            "quote": "**porosity_fields.png** — Porosity field phi(x,t) of one steady snapshot per scenario on the required grid h = 5 d50.",
            "content_hash": "sha256:084f25b805af2bf03aee9417cd0bc05320297ba7be12c3b0a8c1b2947bff6aa3"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-33",
          "aspect": "toolchain",
          "statement": "工具链与产物路径被列出（扫描/分析脚本、summary.json）",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_rubble_rheology.py`（集群 20 并发，60 runs）；拟合/验收/绘图 `scripts/analyse_rubble_rheology.py`；全部数字写入 `summary.json`。",
            "start_offset": 1685,
            "end_offset": 1882,
            "quote": "**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_rubble_rheology.py`（集群 20 并发，60 runs）；拟合/验收/绘图 `scripts/analyse_rubble_rheology.py`；全部数字写入 `summary.json`。",
            "content_hash": "sha256:9f4d25588e073654ef8aa296fff669459b214a790e7132aad68ef9c142db320d"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-34",
          "aspect": "comparison.residual_interpretation",
          "statement": "残差性质的英文判读句（结构性而非抽样噪声）原文保留，不做改写",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "解读：the pooled residual (0.0134) is 1.3x the mean per-condition standard error (0.0102), so it is structural (state/path), not sampling noise;",
            "start_offset": 5743,
            "end_offset": 5884,
            "quote": "解读：the pooled residual (0.0134) is 1.3x the mean per-condition standard error (0.0102), so it is structural (state/path), not sampling noise;",
            "content_hash": "sha256:6d110f80f590d8bf5d6f553f50fbde6edb1f963caba69153aa942311e6bc6d7b"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "ev-9582-02-35",
          "aspect": "figures.section",
          "statement": "④ 结果图章节存在（结构切分锚点），且图注为英文并以所需网格 h = 5 d50 表述",
          "locator": {
            "locator_type": "char_offset",
            "source_field": "markdown",
            "value": "## ④ 结果图\n\n**porosity_fields.png** — Porosity field",
            "start_offset": 7155,
            "end_offset": 7205,
            "quote": "## ④ 结果图\n\n**porosity_fields.png** — Porosity field",
            "content_hash": "sha256:715f2f4ba63cd86c926fb558c59717e5077086847713d8e2b711db44c52b63e8"
          },
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        }
      ],
      "unresolved": [
        {
          "id": "unres-9582-02-01",
          "aspect": "type.facility",
          "status": "unresolved",
          "statement": "experimental-validation signal 'facility' is not satisfied and cannot be resolved from the text: the work is a numerical element-test campaign, so a physical facility is not merely omitted but inapplicable. Recorded unresolved rather than re-labelled.",
          "evidence_refs": [
            "ev-9582-02-23"
          ]
        },
        {
          "id": "unres-9582-02-02",
          "aspect": "identity.title_drift",
          "status": "unresolved",
          "statement": "record title, contract title and markdown H1 differ in wording; the report markdown H1 also names kinematic descriptors, the record title names 'equivalent viscosity (DEM)'. The divergence is preserved, not reconciled; downstream must key on report_id.",
          "evidence_refs": [
            "ev-9582-02-01"
          ]
        }
      ],
      "limitations": [
        {
          "id": "lim-9582-02-01",
          "aspect": "signal_selection_asymmetry",
          "statement": "The experimental-validation signal 'facility' misses because the work is computational; the scientific-computation signals 'convergence study' / 'mesh refinement' / 'timing table' miss for the same inapplicability reason. Both are recorded as misses (symmetric treatment). Robustness check: if inapplicable signals are dropped from the denominator, experimental-validation scores 4/4 and scientific-computation 2/5 — the ranking does not change, so the primary type does not hinge on this.",
          "evidence_refs": [
            "ev-9582-02-23",
            "ev-9582-02-14"
          ]
        },
        {
          "id": "lim-9582-02-02",
          "aspect": "section_mapping_is_a_judgement",
          "statement": "Mapping report sections onto the skill's setup/measurement/comparison/uncertainty/validation slots is a judgement; several sections could serve two slots (e.g. 3.3 equivalent viscosity is both a derived measurement and a literature-window comparison; 3.5 ablation is both comparison and validation). Each section was given its dominant slot only, to keep the downstream extraction instruction unambiguous. Re-slotting is a legitimate downstream revision.",
          "evidence_refs": [
            "ev-9582-02-29",
            "ev-9582-02-11"
          ]
        },
        {
          "id": "lim-9582-02-03",
          "aspect": "absence_is_term_based",
          "statement": "Absence of a signal is measured with an explicit bilingual term list recorded in the product. A synonymous Chinese phrasing outside that list would be missed; this residual uncertainty is why confidence is medium-high, not high.",
          "evidence_refs": []
        },
        {
          "id": "lim-9582-02-04",
          "aspect": "mission_id_not_interpreted",
          "statement": "The record carries mission_id 8301 (also echoed in the report footer as m8301). It is recorded verbatim and not interpreted; the work-package contract declares mission_id: null.",
          "evidence_refs": [
            "ev-9582-02-19"
          ]
        },
        {
          "id": "lim-9582-02-05",
          "aspect": "no_semantic_verdict",
          "statement": "This package does not judge whether the report's own scientific statements are true. Classification correctness is decided by工序04 / the platform gate; every record here is draft and unassessed.",
          "evidence_refs": []
        }
      ],
      "scope": {
        "did": [
          "fetch markdown by id",
          "recompute sha256",
          "six-type signal evaluation with locators",
          "section cut with offsets",
          "select skill_id",
          "topic tagging",
          "absence measurement"
        ],
        "did_not": [
          "extract claims",
          "register assets",
          "read or write any other report_id",
          "mark anything verified",
          "modify upstream or sibling products"
        ],
        "claims_emitted": 0,
        "claims_note": "task_type 02 does not extract; claims.json is emitted as an empty array by design, which satisfies the acceptance rule 'all_claims_have_evidence_or_explicit_unresolved_status' vacuously and explicitly (legitimate zero-claim package)."
      },
      "upstream_check": {
        "package_id": "wp-9582-01",
        "task_type": "01-asset-registration",
        "source_hash": "cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
        "source_chars": 11293,
        "hash_equal_to_this_package": true,
        "chars_equal": true,
        "access": "read-only; not modified by this package",
        "path": "docs/kf/wp-9582-01/asset_manifest.json"
      }
    },
    "claims.json": []
  }
}
```
