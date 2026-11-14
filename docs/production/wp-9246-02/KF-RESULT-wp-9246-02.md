# KF-RESULT wp-9246-02

> 工作包 `wp-9246-02` · 工序 `02-classification-parse` · lane B · mission 19786 · 仓库 TensorKnowledge
> 源资产：`tensor://reports/9246`（report_id=9246）· 源哈希 `sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5`
> 本报告是唯一结果信道：正文唯一一个 json 代码块 = 完整结果信封（`kf_result.json` 原样）。

## ① 本工序做了什么

对 `report_id=9246` 这**一份**报告做类型分类 + 结构切分：给报告打类型/主题标签、给出判定依据的原文逐字定位。**不抽 claim、不判真伪、不打 verified**（契约 `objective.classify_report_type: true`、`objective.register_assets: false`、notes「不做抽取」）。

结论（可反驳的假设，不是裁定）：

| 项 | 值 |
|---|---|
| `report_type.primary` | `scientific-computation` |
| `status` / `confidence` | `classified` / `medium` |
| 选中 skill | `xsk-scientific-computation` v0.1.0（lifecycle=`template-created`） |
| 声明备选类型 | 5 个，逐个给出不选理由 |
| 结构切分 | 29 个标题段（h1×1 + h2×7 + h3×21） |
| 逐字证据 | 22 条 char-span 定位，9 条判断全部绑定证据 |
| 显式 unresolved | 3 条（含两型相邻的争议点） |

报告实际标题行（原文首行，证据 EV-01）：`# IN144-N09: Granular Bed Fluid-Solid Coupling Minimum Verifiable Unit`；契约 `input.title` 为 `IN144-N09: Granular Bed Fluid-Solid Coupling - Ergun Pressure Drop & Richardson-Zaki Settling Validation`。两者措辞不同，本包只登记差异、不改写任何一方。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET /tensor/reports/9246`（Bearer token 由 `/auth/login` 换取），只取 record 与 `markdown` 字段。本包只读这一个 report_id，脚本内 `scope_guard.report_ids_read` 只有 `9246`。
2. **源自证**：对 markdown 的 UTF-8 字节算 sha256，与契约 `input.source_hash` 比对；现算 `sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5`，字符数 11250（契约 11250）。不一致则脚本以退出码 1 终止、不产出结果。
3. **信号探针**：读 `extraction-skills/registry.json` 的 `report_types`（6 类）与每个 skill 的 `identify_signals`，逐条编译成正则/派生量（citation density 用公式），统计命中次数与首次命中位置。
4. **决策规则**（打分前写定，未按结果回调）：R1 信号命中 ≥2 才合格 → R2 合格者中 registry skill 的**全部 steps 都能由原文满足**者为胜 → R3 打平看自述目的句 → R4 仍平则 `unclassified`（禁止硬猜）。
5. **逐字定位**：证据只登记「锚串」，真实 quote / 偏移 / `content_hash` 由脚本从原文切出；锚串必须在原文恰好出现一次，否则报错退出（不猜、不近似、不回述记忆）。
6. **结构切分**：按 1–6 级 ATX 标题行切段，逐段记 char/byte 偏移、行号区间与 sha256。
7. **自检**：`scripts/kf/kf9246_checks.py` 对 acceptance 逐条校验（JSON/ schema/ 哈希/ 定位/ 去重/ 证据绑定/ 不标 verified/ 单 id 锁/ 唯一 json 块），结果落 `checks.json`。
8. **独立复核**：`scripts/kf/kf9246_verify_independent.py` 不复用 build 模块，独立重新取源、重算哈希、回切每条 quote、复核 schema 与围栏数；回归用例 `tests/test_kf_wp9246_02.py`（11 项，离线，直接断言落盘产物的 acceptance 不变量）。

关键设置：`min_quote_chars=12`；`report_type` 只允许 registry 6 类或 `unclassified`；`claims` 不产生（工序 02 不做抽取）。一键复跑见文末 `repro_cmd`。

决策规则原文（`report_type.decision_trace.rule`）：

| 规则 | 内容 |
|---|---|
| declared | before signal scoring; not tuned after seeing results |
| R1_eligibility | 候选类型必须在其 registry identify_signals 中命中 >= 2 条（citation density 这类派生信号按公式计算）。 |
| R2_step_fit | 合格候选中，registry skill 的全部 steps 都能由原文满足者为胜（step-fit 计数，越高越好）。 |
| R3_stated_purpose | R2 打平时，以报告自述目的句（逐字证据）定胜负。 |
| R4_residual | 仍打平则比目的性证据条数；依旧打平则 report_type='unclassified'，禁止硬猜。 |
| admissible_types | registry.report_types 的 6 类 + 'unclassified' |
| used_in_this_package | R1 + R2（R2 唯一决胜，R3/R4 未触发，见 decision_trace） |

本次实际使用：`R1 + R2（R2 唯一决胜，R3/R4 未触发，见 decision_trace）`（R3_triggered=False）。

## ③ 产出物清单（数字由脚本注入）

| 文件 | 要点 |
|---|---|
| `docs/production/wp-9246-02/KF-RESULT-wp-9246-02.md` | 本报告（六段 + 唯一 json 块） |
| `docs/production/wp-9246-02/kf_result.json` | 结果信封（`schemas/kf_result.v1.schema.json` 校验通过） |
| `docs/production/wp-9246-02/classification.json` | 分类/结构/证据/unresolved 全部内容（信封 `outputs` 同一对象） |
| `docs/production/wp-9246-02/checks.json` | 9 项自检逐条结果 |
| `docs/production/wp-9246-02/figures/classification_decision.png` | 判定输入可视化（信号命中矩阵 + step-fit） |
| `artifacts/wp-9246-02/` | 镜像：同上 JSON + 图 + `source_markdown.md`（取源快照，便于离线复算） |

**信号命中（registry identify_signals × 6 类候选）**，右列 `hits/total`：

| 候选类型 | 命中/总数 | 逐条信号 |
|---|---|---|
| `literature-review` | 0/5 | related work=miss(0)；state of the art=miss(0)；survey=miss(0)；bibliography=miss(0)；citation density >= 5 per 1000 chars=miss(derived=0.1778) |
| `scientific-computation` | 3/5 | governing equations=hit(3)；discretisation=hit(4)；convergence study=hit(3)；mesh refinement=miss(0)；timing table=miss(0) |
| `algorithm-implementation` | 1/5 | pseudocode=miss(0)；complexity=miss(0)；algorithm block=miss(0)；function signature=hit(1)；O(n=miss(0) |
| `software-engineering` | 0/5 | changed files=miss(0)；commit=miss(0)；interface=miss(0)；regression=miss(0)；API=miss(0) |
| `technical-proposal` | 0/5 | proposal=miss(0)；design=miss(0)；roadmap=miss(0)；specification=miss(0)；plan=miss(0) |
| `experimental-validation` | 3/5 | test matrix=hit(2)；facility=miss(0)；measurement uncertainty=miss(0)；validation case=hit(6)；baseline comparison=hit(8) |

**step-fit（registry skill 的 steps 是否可由原文满足）**：

| 候选类型 | 可满足/已评 | 逐 step |
|---|---|---|
| `literature-review` | 0/0 | (registry steps not evaluated: type eliminated at R1)=not_evaluated |
| `scientific-computation` | 3/3 | extract-equations-and-parameters=satisfiable；extract-accuracy-statements=satisfiable；extract-assumptions=satisfiable |
| `algorithm-implementation` | 0/0 | (registry steps not evaluated: type eliminated at R1)=not_evaluated |
| `software-engineering` | 0/0 | (registry steps not evaluated: type eliminated at R1)=not_evaluated |
| `technical-proposal` | 0/0 | (registry steps not evaluated: type eliminated at R1)=not_evaluated |
| `experimental-validation` | 2/3 | extract-conditions=satisfiable；extract-comparison-pairs=satisfiable；extract-uncertainty=not_satisfiable |

**结构切分（标题段，偏移为 markdown 字符下标）**：

| # | 级别 | 标题 | 行 | 字符区间 | chars |
|---|---|---|---|---|---|
| 1 | h1 | IN144-N09: Granular Bed Fluid-Solid Coupling Minimum Verifiable Unit | 1–2 | 0–72 | 72 |
| 2 | h2 | 1. Case Introduction | 3–4 | 72–97 | 25 |
| 3 | h3 | Physical Background | 5–10 | 97–641 | 544 |
| 4 | h3 | Implementation Scope | 11–16 | 641–1023 | 382 |
| 5 | h3 | Geometry and Parameters | 17–32 | 1023–1598 | 575 |
| 6 | h2 | 2. Methodology | 33–34 | 1598–1617 | 19 |
| 7 | h3 | Numerical Approach | 35–58 | 1617–2512 | 895 |
| 8 | h3 | Verification Strategy | 59–69 | 2512–2994 | 482 |
| 9 | h2 | 3. Computational Results | 70–71 | 2994–3023 | 29 |
| 10 | h3 | Criterion 1: Random Packing Porosity | 72–83 | 3023–3568 | 545 |
| 11 | h3 | Criterion 2: Ergun Pressure Drop | 84–96 | 3568–4226 | 658 |
| 12 | h3 | Criterion 3: Single-Particle Terminal Velocity | 97–109 | 4226–4645 | 419 |
| 13 | h3 | Criterion 4: Richardson-Zaki Hindered Settling | 110–121 | 4645–5153 | 508 |
| 14 | h3 | Criterion 5: Static Bed Force Residual | 122–132 | 5153–5582 | 429 |
| 15 | h3 | Criterion 6: Time-Step Convergence | 133–143 | 5582–6021 | 439 |
| 16 | h2 | 4. Results Visualization | 144–145 | 6021–6050 | 29 |
| 17 | h3 | Figure 1: Fixed Bed Pressure Drop | 146–148 | 6050–6371 | 321 |
| 18 | h3 | Figure 2: Local Voidage Field | 149–151 | 6371–6663 | 292 |
| 19 | h3 | Figure 3: Richardson-Zaki Correlation | 152–154 | 6663–6946 | 283 |
| 20 | h3 | Figure 4: Acceptance Criteria Summary | 155–157 | 6946–7195 | 249 |
| 21 | h3 | Figure 5: Terminal Velocity Comparison | 158–160 | 7195–7427 | 232 |
| 22 | h2 | 5. Limitations and Applicability | 161–162 | 7427–7464 | 37 |
| 23 | h3 | Current Limitations | 163–174 | 7464–8442 | 978 |
| 24 | h3 | Applicability Domain | 175–184 | 8442–8900 | 458 |
| 25 | h2 | 6. Error Assessment | 185–186 | 8900–8924 | 24 |
| 26 | h3 | Quantitative Error Summary | 187–199 | 8924–9631 | 707 |
| 27 | h3 | Error Sources | 200–209 | 9631–10450 | 819 |
| 28 | h3 | Conclusion | 210–213 | 10450–10790 | 340 |
| 29 | h2 | Audit Trail | 214–222 | 10790–11250 | 460 |

**选中 skill 的章节映射**：

| skill.applies_to.sections | 命中的报告章节 | 状态 |
|---|---|---|
| method | — | not_found |
| numerical setup | Geometry and Parameters | mapped |
| results | — | not_found |
| convergence | Criterion 6: Time-Step Convergence | mapped |

**自检探针（量级复算，不改报告结论）**：原文称 ε=0.8 处 Gidaspow 分支切换有 25% 拖曳系数跳变。用原文 §2 逐字分支公式 + 原文自身参数（μ=0.001 Pa·s、ρ_f=998.0 kg/m³、d=0.001 m、ε=0.8）复算，两种 Re 约定都算（原文写 `C_D(εRe)` 但未定义 Re）：

| u [m/s] | c_Ergun | c_WenYu (Re 约定 A) | c_WenYu (Re 约定 B) | 跳变 A | 跳变 B |
|---|---|---|---|---|---|
| 0.002 | 3.42517e-05 | 1.69044e-05 | 2.0547e-05 | -50.65% | -40.01% |
| 0.05 | 0.000119983 | 4.36017e-05 | 4.91756e-05 | -63.66% | -59.01% |

u ∈ [0.001, 0.1] 取 400 点扫描：|跳变| ∈ [39.84%, 70.43%]，是否覆盖原文的 25% = False（status=`unresolved_probe`）。

读法：按原文 §2 逐字分支公式与原文自身参数，ε=0.8 处线性拖曳系数的跳变幅度落在上面 sweep 区间内、符号为负；原文正文称 ~25%。两者不一致，可能原因：原文公式行是摘要（实现里的 A_p/V_p 归一或 ε 幂次不同），或 ~25% 指未说明的工况。本包不下断言，登记为 UR-03 交 03/04 复核。

**图**：`figures/classification_decision.png`（左：信号命中矩阵；右：命中数与 step-fit 比例，红色虚线为 R1 门槛 2）。说明：本工序是文档分类/解析，无场量可画云图，故给判定输入的可复核视图，而不是物理结果图。

## ④ 证据定位表（字段 → 原文逐字片段）

所有 quote 由脚本从原文切出，`start_offset`/`end_offset` 为 markdown 字符下标，`content_hash` 是 quote 的 sha256；下表行号指 markdown 行号。

| 证据 | 归属字段 | 行 | 原文逐字片段 |
|---|---|---|---|
| EV-01 | classification.source.title_line | 1 | # IN144-N09: Granular Bed Fluid-Solid Coupling Minimum Verifiable Unit |
| EV-02 | classification.report_type.primary / stated purpose | 6 | The implementation validates two fundamental closure relations |
| EV-03 | signals.experimental-validation.test matrix | 61 | Six machine-checkable criteria validate the implementation: |
| EV-04 | signals.scientific-computation.governing equations | 39 | F_drag = c(ε, \|u\|) · u_slip |
| EV-05 | signals.scientific-computation.governing equations (closure form) | 42 | **Ergun branch** (ε < 0.8): c = V_p [150μ(1-ε)/(ε³d²) + 1.75ρ_f\|u\|/(ε³d)] |
| EV-06 | signals.scientific-computation.discretisation | 54 | Semi-coupled batch settling with explicit Euler integration: |
| EV-07 | signals.scientific-computation.discretisation (dt) | 56 | - Time step: dt = 0.1 τ (τ = drag relaxation time) |
| EV-08 | signals.scientific-computation.convergence study | 133 | ### Criterion 6: Time-Step Convergence |
| EV-09 | signals.scientific-computation.convergence study (detail) | 142 | The steady-state pressure drop is invariant to time-step halving |
| EV-10 | signals.experimental-validation.baseline comparison (headline error) | 93 | **Maximum relative error:** 1.47% (threshold: 15%) |
| EV-11 | signals.experimental-validation.baseline comparison (measured vs reference row) | 90 | \| Laminar \| 2.0×10⁻³ \| 2180.55 \| 2212.71 \| 1.47% \| |
| EV-12 | signals.experimental-validation.baseline comparison (analytical reference) | 108 | The simulated terminal velocity matches the Schiller-Naumann analytical solution to within 0.013% |
| EV-13 | signals.experimental-validation.baseline comparison (correlation reference) | 120 | The DEM settling simulations recover the Richardson-Zaki exponent to within 0.035 |
| EV-14 | step-fit.experimental-validation.extract-conditions (configuration) | 20 | - Particle diameter: d = 1.0 mm (monodisperse) |
| EV-15 | step-fit.scientific-computation.extract-assumptions | 165 | 1. **Unresolved fluid**: The fluid is a single uniform velocity |
| EV-16 | signals.software-engineering (audit-trail only) | 216 | - **Module**: `tensordem.bedcoupling` (closures, packing, bed, study) |
| EV-17 | signals.software-engineering (audit-trail only) | 217 | - **Tests**: `tests/test_bedcoupling_*.py` (4 test files, 28 tests, all passing) |
| EV-18 | classification.rationale (conclusion sentence) | 212 | The implementation passes all six acceptance criteria with substantial margin |
| EV-19 | signals.literature-review (citation marker) | 8 | **Ergun pressure drop correlation** (1952) |
| EV-20 | step-fit.experimental-validation.extract-uncertainty (no coverage factor) | 200 | ### Error Sources |
| EV-21 | signals.algorithm-implementation.function signature | 218 | - **Acceptance study**: `run_acceptance_study()` (deterministic, seed-controlled) |
| EV-22 | classification.applicability_scope | 175 | ### Applicability Domain |

**判断 → 证据绑定（decision_basis）**：

| 判断 | 绑定证据 | 陈述 |
|---|---|---|
| DB-01 | EV-02 | 报告自述目的是验证两条闭合关系（Ergun 压降、Richardson-Zaki 沉降），不是提出新方法或新方案。 |
| DB-02 | EV-04, EV-05 | 原文含可执行闭合关系式（Gidaspow 混合拖曳、单位体积空隙率积分式），scientific-computation 的 governing-equations 信号命中。 |
| DB-03 | EV-06, EV-07 | 原文给出时间离散格式与步长（explicit Euler；dt = 0.1 τ），discretisation 信号命中。 |
| DB-04 | EV-08, EV-09 | 原文含独立收敛性判据章节（Criterion 6，dt → dt/2），convergence-study 信号命中。 |
| DB-05 | EV-10, EV-11, EV-12, EV-13 | 原文的误差陈述都配有明确参照（Ergun 关联式、Schiller-Naumann 解析解、Richardson-Zaki 关联式），满足 extract-accuracy-statements 的前提。 |
| DB-06 | EV-15 | 原文含建模假设/局限清单，满足 extract-assumptions step。 |
| DB-07 | EV-03, EV-10, EV-20 | experimental-validation 虽在 test-matrix / validation-case / baseline-comparison 三条信号命中，但其 registry step extract-uncertainty 要求逐字照抄不确定度与包含因子，原文只有数值误差来源讨论，step-fit 不满足。 |
| DB-08 | EV-16, EV-17 | software-engineering 只在 Audit Trail 出现模块/测试字样，changed-files/commit/interface/regression/API 信号 0 命中，不是变更说明类报告。 |
| DB-09 | EV-19 | 原文引用密度远低于 literature-review 阈值（见 signals 派生量），且无 related work / survey / bibliography 结构。 |

**显式 unresolved**：

| id | 问题 | 原因 | 建议处理 |
|---|---|---|---|
| UR-01 | 主类型 scientific-computation 与备选 experimental-validation 在 registry 信号命中上同为 3/5，分类结论是否会被独立审核推翻？ | 两型语义相邻（数值实验的验证）；本包只按事先声明的 R2（step-fit）定胜负，未做语义投票。 | 工序 04 独立审核（reviewer_role=document-analyst） |
| UR-02 | 报告是否含测量不确定度与包含因子（experimental-validation 的 extract-uncertainty 前提）？ | 全文探针 'measurement uncertainty\|coverage factor\|uncertainty budget' 0 命中；仅在 Error Sources 讨论数值误差来源，不能等同于测量不确定度声明。 | 若审核者认为数值误差来源等价于不确定度声明，则类型结论需复议 |
| UR-03 | 报告称 ε=0.8 处拖曳系数有 ~25% 跳变；按原文逐字分支公式复算，\|跳变\| 落在 39.8%–70.4%（见 probe_result），两者不一致。 | 原文未给 ~25% 的计算过程与工况；本包只对原文公式行做量级探针，不下断言、不改报告结论。可能原因：公式行是摘要（A_p/V_p 归一或 ε 幂次不同），或该 25% 指未说明的工况。 | 工序 03/04 复核（需 closure 实现与原文公式一致） |

## ⑤ 注意点与局限

1. **主/备两型信号打平**：`scientific-computation` 与 `experimental-validation` 各命中 3/5 与 3/5，胜负完全由事先声明的 R2（step-fit：`extract-uncertainty` 需逐字不确定度+包含因子，原文没有）决定。审核者若认为「数值误差来源」等价于不确定度声明，本结论应被复议（UR-01/UR-02）。
2. **探针是语义近似，不是原文元数据**：信号命中来自我按 registry 语义写的正则，命中计数可复核，但「正则是否等价于 registry 语义」本身需 04 审核判断。缺信号的证据只能是「探针 0 命中」，无法逐字引用「原文没有写 X」。
3. **skill 仍是 template-created**：`registry.note` 明示尚无真实代表性报告走通全链；本包只登记「选中」，不宣称该 skill 已被验证有效。
4. **标题措辞不一致**：平台 record 标题用「-」，原文标题行用「Minimum Verifiable Unit」表述；信封 `provenance.title` 抄契约值，原文标题另以 EV-01 定位，二者不混用。
5. **不做的事**：不抽 claim、不评估六个判据是否成立、不复算报告数值（除 ③ 末的跳变量级探针）、不把任何结论标 verified（verification 由平台门计算）。
6. **边界**：只读/只写 report_id=9246；未改上游 01 包与其它工作包产物；`claims` 为空是契约允许的完整结果。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 证据摘要 |
|---|---|---|
| `valid_json` | ✓ | `{"artifacts": ["kf_result.json", "classification.json"], "roundtrip": "json.dumps -> json.loads OK"}` |
| `schema_pass` | ✓ | `{"schema": "schemas/kf_result.v1.schema.json", "schema_sha256": "sha256:5692e1a3e1ccc7e191753a63505243955aad56184b005eb3c3ecf7c9e1c9f817", "errors": []}` |
| `source_hash_matches` | ✓ | `{"declared": "sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5", "recomputed": "sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5", "chars": {"contract": 11250, "actual": 11250}}` |
| `source_locator_resolvable` | ✓ | `{"char_span_locators": 22, "section_locators": 29, "mismatches": [], "empty_sections": []}` |
| `no_duplicate_ids` | ✓ | `{"ids": 34, "duplicates": []}` |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✓ | `{"decision_basis": 9, "unbound_statements": [], "dangling_refs": [], "claims_emitted": 0}` |
| `no_claims_marked_verified` | ✓ | `{"offending": []}` |
| `scope_lock_single_report_id` | ✓ | `{"guard": {"report_ids_read": ["9246"], "report_ids_written": ["9246"], "upstream_artifacts_modified": [], "other_work_packages_touched": []}}` |
| `single_json_block_matches_envelope` | ✓ | `{"json_blocks": 1, "fence_markers": 2, "parses_equal": true}` |

总体：`checks.ok = True`（9/9 项 passed）。失败项如实列出，未粉饰。

**honest-FAIL 与不适用声明**：

- `all_claims_have_evidence_or_explicit_unresolved_status`：本工序**不产生 claims**，该项按「本包每条判断都绑定逐字证据或显式 unresolved」执行并校验为 passed；若下游理解为本包必须产 claim，则该理解与契约 notes「不做抽取」冲突——此点如实登记为口径差异，不予敷衍。
- 无独立的 A9 之外的外部校验：平台门会独立重算 sha256 与子串定位，本报告的 `checks.json` 是自检，不是平台裁定。

## repro_cmd

命令（复制即跑；正文不另开代码围栏，保证全文只有唯一一个 json 代码块）：

    # 工作树根 = 仓库检出；需 TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE
    python3 scripts/kf/kf9246_build.py               # 取源+构造+自检+出图+出报告
    python3 scripts/kf/kf9246_build.py --check-only  # 只重跑自检（读已落盘信封）
    cat docs/production/wp-9246-02/checks.json

## 结果信封（唯一一个 json 代码块，原样提交）

```json
{
  "package_id": "wp-9246-02",
  "task_type": "02-classification-parse",
  "contract_version": "1.0",
  "report_id": "9246",
  "provenance": {
    "source_uri": "tensor://reports/9246",
    "source_field": "markdown",
    "source_hash": "sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5",
    "source_hash_matches": true,
    "title": "IN144-N09: Granular Bed Fluid-Solid Coupling - Ergun Pressure Drop & Richardson-Zaki Settling Validation",
    "scenario_key": "IN144-N09",
    "chars": 11250
  },
  "outputs": {
    "classification.json": {
      "schema": "kf-classification.v1",
      "package_id": "wp-9246-02",
      "task_type": "02-classification-parse",
      "report_id": "9246",
      "source": {
        "source_uri": "tensor://reports/9246",
        "source_field": "markdown",
        "declared_source_hash": "sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5",
        "recomputed_source_hash": "sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5",
        "source_hash_matches": true,
        "declared_chars": 11250,
        "chars": 11250,
        "bytes_utf8": 11440,
        "lines": 223,
        "title_line_evidence": "EV-01",
        "record_title": "IN144-N09: Granular Bed Fluid-Solid Coupling - Ergun Pressure Drop & Richardson-Zaki Settling Validation",
        "scenario_key_in_contract": "IN144-N09",
        "scenario_key_in_record": "IN144-N09",
        "record_mission_id": 7894,
        "record_status": "published"
      },
      "taxonomy": {
        "registry": "extraction-skills/registry.json",
        "registry_version": "1.0",
        "candidate_types": [
          "literature-review",
          "scientific-computation",
          "algorithm-implementation",
          "software-engineering",
          "technical-proposal",
          "experimental-validation"
        ],
        "identity_signals_source": "registry.skills[].identify_signals",
        "note": "Extraction Skill Library registry. All skills are template-created (skeleton + identification signals exist, no real representative report has passed the full line yet). Promotion rules are enforced by ke.wp_gate.validate_skill_registry (K1-K6)."
      },
      "report_type": {
        "primary": "scientific-computation",
        "status": "classified",
        "confidence": "medium",
        "classification_is_hypothesis": true,
        "reversible_by_review": true,
        "declared_alternatives": [
          {
            "report_type": "experimental-validation",
            "signals_hit": 3,
            "signals_total": 5,
            "stepfit_all_satisfiable": false,
            "why_not_primary": "R2 不满足：registry step 无法由原文满足（见 signals.step_fit）"
          },
          {
            "report_type": "algorithm-implementation",
            "signals_hit": 1,
            "signals_total": 5,
            "stepfit_all_satisfiable": false,
            "why_not_primary": "R1 未达标：registry identify_signals 命中 < 2 条"
          },
          {
            "report_type": "literature-review",
            "signals_hit": 0,
            "signals_total": 5,
            "stepfit_all_satisfiable": false,
            "why_not_primary": "R1 未达标：registry identify_signals 命中 < 2 条"
          },
          {
            "report_type": "software-engineering",
            "signals_hit": 0,
            "signals_total": 5,
            "stepfit_all_satisfiable": false,
            "why_not_primary": "R1 未达标：registry identify_signals 命中 < 2 条"
          },
          {
            "report_type": "technical-proposal",
            "signals_hit": 0,
            "signals_total": 5,
            "stepfit_all_satisfiable": false,
            "why_not_primary": "R1 未达标：registry identify_signals 命中 < 2 条"
          }
        ],
        "decision_trace": {
          "rule": {
            "declared": "before signal scoring; not tuned after seeing results",
            "R1_eligibility": "候选类型必须在其 registry identify_signals 中命中 >= 2 条（citation density 这类派生信号按公式计算）。",
            "R2_step_fit": "合格候选中，registry skill 的全部 steps 都能由原文满足者为胜（step-fit 计数，越高越好）。",
            "R3_stated_purpose": "R2 打平时，以报告自述目的句（逐字证据）定胜负。",
            "R4_residual": "仍打平则比目的性证据条数；依旧打平则 report_type='unclassified'，禁止硬猜。",
            "admissible_types": "registry.report_types 的 6 类 + 'unclassified'",
            "used_in_this_package": "R1 + R2（R2 唯一决胜，R3/R4 未触发，见 decision_trace）"
          },
          "eligible_after_R1": [
            "scientific-computation",
            "experimental-validation"
          ],
          "all_steps_satisfiable": [
            "scientific-computation"
          ],
          "R3_triggered": false,
          "note": "R2 唯一决胜，R3 未被触发；EV-02/EV-18 仍登记为自述目的逐字证据"
        }
      },
      "selected_skill": {
        "skill_id": "xsk-scientific-computation",
        "skill_version": "0.1.0",
        "lifecycle_state": "template-created",
        "applies_to_sections": [
          "method",
          "numerical setup",
          "results",
          "convergence"
        ],
        "steps": [
          "extract-equations-and-parameters",
          "extract-accuracy-statements",
          "extract-assumptions"
        ],
        "section_mapping": [
          {
            "skill_section": "method",
            "matched_report_sections": [],
            "locators": [],
            "status": "not_found"
          },
          {
            "skill_section": "numerical setup",
            "matched_report_sections": [
              "Geometry and Parameters"
            ],
            "locators": [
              {
                "title": "Geometry and Parameters",
                "start_offset": 1023,
                "end_offset": 1598,
                "line_start": 17,
                "line_end": 32
              }
            ],
            "status": "mapped"
          },
          {
            "skill_section": "results",
            "matched_report_sections": [],
            "locators": [],
            "status": "not_found"
          },
          {
            "skill_section": "convergence",
            "matched_report_sections": [
              "Criterion 6: Time-Step Convergence"
            ],
            "locators": [
              {
                "title": "Criterion 6: Time-Step Convergence",
                "start_offset": 5582,
                "end_offset": 6021,
                "line_start": 133,
                "line_end": 143
              }
            ],
            "status": "mapped"
          }
        ],
        "lifecycle_caveat": "registry.note 明示所有 skill 仍为 template-created，尚无真实代表性报告走通全链；本包只登记选中，不宣称已验证。"
      },
      "signals": {
        "method": "正则探针扫描 + 派生量公式；命中次数与首次命中逐字切片见各行",
        "per_type": {
          "literature-review": {
            "signals": [
              {
                "signal": "related work",
                "kind": "regex",
                "pattern": "related\\s+work",
                "count": 0,
                "hit": false
              },
              {
                "signal": "state of the art",
                "kind": "regex",
                "pattern": "state\\s+of\\s+the\\s+art",
                "count": 0,
                "hit": false
              },
              {
                "signal": "survey",
                "kind": "regex",
                "pattern": "\\bsurvey\\b",
                "count": 0,
                "hit": false
              },
              {
                "signal": "bibliography",
                "kind": "regex",
                "pattern": "\\bbibliograph",
                "count": 0,
                "hit": false
              },
              {
                "signal": "citation density >= 5 per 1000 chars",
                "kind": "derived",
                "formula": "count(year-in-parens) * 1000 / len(markdown)",
                "count": 2,
                "value": 0.1778,
                "threshold": 5.0,
                "hit": false
              }
            ],
            "hits": 0,
            "total": 5,
            "coverage": 0.0
          },
          "scientific-computation": {
            "signals": [
              {
                "signal": "governing equations",
                "kind": "regex",
                "pattern": "(F_drag\\s*=|ε_i\\s*=\\s*1|C_D\\s*=\\s*24/Re)",
                "count": 3,
                "hit": true,
                "first_hit": {
                  "quote": "F_drag =",
                  "start_offset": 1680,
                  "end_offset": 1688,
                  "line": 39
                }
              },
              {
                "signal": "discretisation",
                "kind": "regex",
                "pattern": "(explicit Euler|Time step:|dt = 0\\.1)",
                "count": 4,
                "hit": true,
                "first_hit": {
                  "quote": "explicit Euler",
                  "start_offset": 2273,
                  "end_offset": 2287,
                  "line": 54
                }
              },
              {
                "signal": "convergence study",
                "kind": "regex",
                "pattern": "(Time-Step Convergence|time-step convergence|dt → dt/2)",
                "count": 3,
                "hit": true,
                "first_hit": {
                  "quote": "Time-Step Convergence",
                  "start_offset": 5599,
                  "end_offset": 5620,
                  "line": 133
                }
              },
              {
                "signal": "mesh refinement",
                "kind": "regex",
                "pattern": "(mesh\\s+(refinement|independence)|grid\\s+convergence)",
                "count": 0,
                "hit": false
              },
              {
                "signal": "timing table",
                "kind": "regex",
                "pattern": "(wall[- ]?clock|\\bruntime\\b|elapsed|speed-?up)",
                "count": 0,
                "hit": false
              }
            ],
            "hits": 3,
            "total": 5,
            "coverage": 0.6
          },
          "algorithm-implementation": {
            "signals": [
              {
                "signal": "pseudocode",
                "kind": "regex",
                "pattern": "pseudo-?\\s?code",
                "count": 0,
                "hit": false
              },
              {
                "signal": "complexity",
                "kind": "regex",
                "pattern": "(computational\\s+complexity|algorithmic\\s+complexity)",
                "count": 0,
                "hit": false
              },
              {
                "signal": "algorithm block",
                "kind": "regex",
                "pattern": "(?i)\\balgorithm\\s+(block|listing)",
                "count": 0,
                "hit": false
              },
              {
                "signal": "function signature",
                "kind": "regex",
                "pattern": "\\b[a-z_][a-z0-9_]*\\(\\)",
                "count": 1,
                "hit": true,
                "first_hit": {
                  "quote": "run_acceptance_study()",
                  "start_offset": 10982,
                  "end_offset": 11004,
                  "line": 218
                }
              },
              {
                "signal": "O(n",
                "kind": "regex",
                "pattern": "O\\(n",
                "count": 0,
                "hit": false
              }
            ],
            "hits": 1,
            "total": 5,
            "coverage": 0.2
          },
          "software-engineering": {
            "signals": [
              {
                "signal": "changed files",
                "kind": "regex",
                "pattern": "(changed\\s+files?|files\\s+changed)",
                "count": 0,
                "hit": false
              },
              {
                "signal": "commit",
                "kind": "regex",
                "pattern": "\\bcommit",
                "count": 0,
                "hit": false
              },
              {
                "signal": "interface",
                "kind": "regex",
                "pattern": "\\binterface",
                "count": 0,
                "hit": false
              },
              {
                "signal": "regression",
                "kind": "regex",
                "pattern": "\\bregression",
                "count": 0,
                "hit": false
              },
              {
                "signal": "API",
                "kind": "regex",
                "pattern": "\\bAPI\\b",
                "count": 0,
                "hit": false
              }
            ],
            "hits": 0,
            "total": 5,
            "coverage": 0.0
          },
          "technical-proposal": {
            "signals": [
              {
                "signal": "proposal",
                "kind": "regex",
                "pattern": "\\bproposal\\b",
                "count": 0,
                "hit": false
              },
              {
                "signal": "design",
                "kind": "regex",
                "pattern": "\\bdesign\\b",
                "count": 0,
                "hit": false
              },
              {
                "signal": "roadmap",
                "kind": "regex",
                "pattern": "\\broadmap\\b",
                "count": 0,
                "hit": false
              },
              {
                "signal": "specification",
                "kind": "regex",
                "pattern": "\\bspecification\\b",
                "count": 0,
                "hit": false
              },
              {
                "signal": "plan",
                "kind": "regex",
                "pattern": "\\bplan\\b",
                "count": 0,
                "hit": false
              }
            ],
            "hits": 0,
            "total": 5,
            "coverage": 0.0
          },
          "experimental-validation": {
            "signals": [
              {
                "signal": "test matrix",
                "kind": "regex",
                "pattern": "(machine-checkable criteria|acceptance criteria)",
                "count": 2,
                "hit": true,
                "first_hit": {
                  "quote": "machine-checkable criteria",
                  "start_offset": 2543,
                  "end_offset": 2569,
                  "line": 61
                }
              },
              {
                "signal": "facility",
                "kind": "regex",
                "pattern": "(facility|apparatus|test\\s+rig|laborator)",
                "count": 0,
                "hit": false
              },
              {
                "signal": "measurement uncertainty",
                "kind": "regex",
                "pattern": "(measurement\\s+uncertainty|coverage\\s+factor|uncertainty\\s+budget)",
                "count": 0,
                "hit": false
              },
              {
                "signal": "validation case",
                "kind": "regex",
                "pattern": "validat",
                "count": 6,
                "hit": true,
                "first_hit": {
                  "quote": "validat",
                  "start_offset": 256,
                  "end_offset": 263,
                  "line": 6
                }
              },
              {
                "signal": "baseline comparison",
                "kind": "regex",
                "pattern": "(Relative error|relative error|analytical solution|Ergun correlation)",
                "count": 8,
                "hit": true,
                "first_hit": {
                  "quote": "relative error",
                  "start_offset": 3904,
                  "end_offset": 3918,
                  "line": 93
                }
              }
            ],
            "hits": 3,
            "total": 5,
            "coverage": 0.6
          }
        },
        "step_fit": {
          "literature-review": {
            "steps": [
              {
                "step_id": "(registry steps not evaluated: type eliminated at R1)",
                "verdict": "not_evaluated",
                "evidence": ""
              }
            ],
            "satisfiable": 0,
            "evaluated": 0,
            "all_satisfiable": false
          },
          "scientific-computation": {
            "steps": [
              {
                "step_id": "extract-equations-and-parameters",
                "verdict": "satisfiable",
                "evidence": "EV-04"
              },
              {
                "step_id": "extract-accuracy-statements",
                "verdict": "satisfiable",
                "evidence": "EV-10"
              },
              {
                "step_id": "extract-assumptions",
                "verdict": "satisfiable",
                "evidence": "EV-15"
              }
            ],
            "satisfiable": 3,
            "evaluated": 3,
            "all_satisfiable": true
          },
          "algorithm-implementation": {
            "steps": [
              {
                "step_id": "(registry steps not evaluated: type eliminated at R1)",
                "verdict": "not_evaluated",
                "evidence": ""
              }
            ],
            "satisfiable": 0,
            "evaluated": 0,
            "all_satisfiable": false
          },
          "software-engineering": {
            "steps": [
              {
                "step_id": "(registry steps not evaluated: type eliminated at R1)",
                "verdict": "not_evaluated",
                "evidence": ""
              }
            ],
            "satisfiable": 0,
            "evaluated": 0,
            "all_satisfiable": false
          },
          "technical-proposal": {
            "steps": [
              {
                "step_id": "(registry steps not evaluated: type eliminated at R1)",
                "verdict": "not_evaluated",
                "evidence": ""
              }
            ],
            "satisfiable": 0,
            "evaluated": 0,
            "all_satisfiable": false
          },
          "experimental-validation": {
            "steps": [
              {
                "step_id": "extract-conditions",
                "verdict": "satisfiable",
                "evidence": "EV-14"
              },
              {
                "step_id": "extract-comparison-pairs",
                "verdict": "satisfiable",
                "evidence": "EV-11"
              },
              {
                "step_id": "extract-uncertainty",
                "verdict": "not_satisfiable",
                "evidence": "UR-02"
              }
            ],
            "satisfiable": 2,
            "evaluated": 3,
            "all_satisfiable": false
          }
        },
        "probe_disclosure": "探针是按 registry identify_signals 语义设计的字符串/正则，不是原文自带元数据；命中计数可复核，语义等价性留给 04 审核。"
      },
      "structure": {
        "segmentation_rule": "按 1–6 级 ATX 标题行切段，行首到下一标题行前为一段（含标题行）",
        "heading_count": 29,
        "sections": [
          {
            "index": 1,
            "level": 1,
            "title": "IN144-N09: Granular Bed Fluid-Solid Coupling Minimum Verifiable Unit",
            "start_offset": 0,
            "end_offset": 72,
            "byte_start": 0,
            "byte_end": 72,
            "line_start": 1,
            "line_end": 2,
            "chars": 72,
            "sha256": "sha256:46c08b1f0ba145e509eb6a39da8a582fc5e527ef6d604cf00b5bb1072be277ba"
          },
          {
            "index": 2,
            "level": 2,
            "title": "1. Case Introduction",
            "start_offset": 72,
            "end_offset": 97,
            "byte_start": 72,
            "byte_end": 97,
            "line_start": 3,
            "line_end": 4,
            "chars": 25,
            "sha256": "sha256:c6466e95de7320e428542fd83fca71503d26451e1872a89f2ed958e95dc7d8bf"
          },
          {
            "index": 3,
            "level": 3,
            "title": "Physical Background",
            "start_offset": 97,
            "end_offset": 641,
            "byte_start": 97,
            "byte_end": 641,
            "line_start": 5,
            "line_end": 10,
            "chars": 544,
            "sha256": "sha256:e0a38ecd11bb7458f26e8a4dacbd0df46ec884898fd7ed1c2ac6a5452b11c4d7"
          },
          {
            "index": 4,
            "level": 3,
            "title": "Implementation Scope",
            "start_offset": 641,
            "end_offset": 1023,
            "byte_start": 641,
            "byte_end": 1029,
            "line_start": 11,
            "line_end": 16,
            "chars": 382,
            "sha256": "sha256:b0a9256415a85a64a5ed822e26040566a0e34591ed5b9136cd9367b84002d3c5"
          },
          {
            "index": 5,
            "level": 3,
            "title": "Geometry and Parameters",
            "start_offset": 1023,
            "end_offset": 1598,
            "byte_start": 1029,
            "byte_end": 1622,
            "line_start": 17,
            "line_end": 32,
            "chars": 575,
            "sha256": "sha256:3722496f70fb3d5ee4427f921014e1666c8b55c7ebfdb1d30916d411ec8ad175"
          },
          {
            "index": 6,
            "level": 2,
            "title": "2. Methodology",
            "start_offset": 1598,
            "end_offset": 1617,
            "byte_start": 1622,
            "byte_end": 1641,
            "line_start": 33,
            "line_end": 34,
            "chars": 19,
            "sha256": "sha256:0429626abf6c5b07e4dd23e3dd39c10323a5efd1bb56ebc41c28e3753ee46d36"
          },
          {
            "index": 7,
            "level": 3,
            "title": "Numerical Approach",
            "start_offset": 1617,
            "end_offset": 2512,
            "byte_start": 1641,
            "byte_end": 2568,
            "line_start": 35,
            "line_end": 58,
            "chars": 895,
            "sha256": "sha256:746d13570aa0594220c71701f8ec3df0967f0febf3a6b6b31d87f80460e8dc59"
          },
          {
            "index": 8,
            "level": 3,
            "title": "Verification Strategy",
            "start_offset": 2512,
            "end_offset": 2994,
            "byte_start": 2568,
            "byte_end": 3077,
            "line_start": 59,
            "line_end": 69,
            "chars": 482,
            "sha256": "sha256:5f7dbd79d7292bdfc638cd978c66e18f034bc6976ba6bc359bfa66a1fe4742b9"
          },
          {
            "index": 9,
            "level": 2,
            "title": "3. Computational Results",
            "start_offset": 2994,
            "end_offset": 3023,
            "byte_start": 3077,
            "byte_end": 3106,
            "line_start": 70,
            "line_end": 71,
            "chars": 29,
            "sha256": "sha256:7a78026e31202e2102b47cc332be2034853482610ed1dc948a0ecb8c5ffee3d3"
          },
          {
            "index": 10,
            "level": 3,
            "title": "Criterion 1: Random Packing Porosity",
            "start_offset": 3023,
            "end_offset": 3568,
            "byte_start": 3106,
            "byte_end": 3665,
            "line_start": 72,
            "line_end": 83,
            "chars": 545,
            "sha256": "sha256:1dee049e749dd308a767284b8fa50e7c904497457227ee61d21de83cc9d34aa4"
          },
          {
            "index": 11,
            "level": 3,
            "title": "Criterion 2: Ergun Pressure Drop",
            "start_offset": 3568,
            "end_offset": 4226,
            "byte_start": 3665,
            "byte_end": 4336,
            "line_start": 84,
            "line_end": 96,
            "chars": 658,
            "sha256": "sha256:56c7e319d53768f2c2151d346ad1697cfc91f64b3d38bc9d3dc93f9dd6fd6895"
          },
          {
            "index": 12,
            "level": 3,
            "title": "Criterion 3: Single-Particle Terminal Velocity",
            "start_offset": 4226,
            "end_offset": 4645,
            "byte_start": 4336,
            "byte_end": 4757,
            "line_start": 97,
            "line_end": 109,
            "chars": 419,
            "sha256": "sha256:03b29d8c877e137566d6e03a18ad717fe8c4879ccb361f6ee580a35b9bc69686"
          },
          {
            "index": 13,
            "level": 3,
            "title": "Criterion 4: Richardson-Zaki Hindered Settling",
            "start_offset": 4645,
            "end_offset": 5153,
            "byte_start": 4757,
            "byte_end": 5268,
            "line_start": 110,
            "line_end": 121,
            "chars": 508,
            "sha256": "sha256:e35141545f4365a4100ae2b56808c59b15b0924873f5a274346cbb6bf1d4dcea"
          },
          {
            "index": 14,
            "level": 3,
            "title": "Criterion 5: Static Bed Force Residual",
            "start_offset": 5153,
            "end_offset": 5582,
            "byte_start": 5268,
            "byte_end": 5705,
            "line_start": 122,
            "line_end": 132,
            "chars": 429,
            "sha256": "sha256:91250c106d44cd5fd9f5dcad426247efdf18a3762f2912df02112fa46bec0086"
          },
          {
            "index": 15,
            "level": 3,
            "title": "Criterion 6: Time-Step Convergence",
            "start_offset": 5582,
            "end_offset": 6021,
            "byte_start": 5705,
            "byte_end": 6156,
            "line_start": 133,
            "line_end": 143,
            "chars": 439,
            "sha256": "sha256:c283cc55b7153243a145b3cfd9900854279077f9802a766443e722c83d3e077e"
          },
          {
            "index": 16,
            "level": 2,
            "title": "4. Results Visualization",
            "start_offset": 6021,
            "end_offset": 6050,
            "byte_start": 6156,
            "byte_end": 6185,
            "line_start": 144,
            "line_end": 145,
            "chars": 29,
            "sha256": "sha256:26e3bfc353876462490c276b80b22b51b8802239b2774c60c4f4ba0a578774d1"
          },
          {
            "index": 17,
            "level": 3,
            "title": "Figure 1: Fixed Bed Pressure Drop",
            "start_offset": 6050,
            "end_offset": 6371,
            "byte_start": 6185,
            "byte_end": 6506,
            "line_start": 146,
            "line_end": 148,
            "chars": 321,
            "sha256": "sha256:1c77f5c45a5c5653bb104d78bc453fb1d33881b2ed3d6316b5b56d166b04ae61"
          },
          {
            "index": 18,
            "level": 3,
            "title": "Figure 2: Local Voidage Field",
            "start_offset": 6371,
            "end_offset": 6663,
            "byte_start": 6506,
            "byte_end": 6798,
            "line_start": 149,
            "line_end": 151,
            "chars": 292,
            "sha256": "sha256:22568822f6e4f349fdae4adec57bbd578b52733e1863daeaf794a63b6db1fed5"
          },
          {
            "index": 19,
            "level": 3,
            "title": "Figure 3: Richardson-Zaki Correlation",
            "start_offset": 6663,
            "end_offset": 6946,
            "byte_start": 6798,
            "byte_end": 7081,
            "line_start": 152,
            "line_end": 154,
            "chars": 283,
            "sha256": "sha256:71b51391d78e1a6231f30379e0457fec343ff392264dad6fcb7196fb95af9748"
          },
          {
            "index": 20,
            "level": 3,
            "title": "Figure 4: Acceptance Criteria Summary",
            "start_offset": 6946,
            "end_offset": 7195,
            "byte_start": 7081,
            "byte_end": 7330,
            "line_start": 155,
            "line_end": 157,
            "chars": 249,
            "sha256": "sha256:636b984a7d4f3fe4cf4832a76ada2f0641194fd778b784aebf9a9d04d6b8f7f4"
          },
          {
            "index": 21,
            "level": 3,
            "title": "Figure 5: Terminal Velocity Comparison",
            "start_offset": 7195,
            "end_offset": 7427,
            "byte_start": 7330,
            "byte_end": 7562,
            "line_start": 158,
            "line_end": 160,
            "chars": 232,
            "sha256": "sha256:80f9b6e961a894057eeec023dd420378b8640340d46be15d5feadf8a8dbc4b7f"
          },
          {
            "index": 22,
            "level": 2,
            "title": "5. Limitations and Applicability",
            "start_offset": 7427,
            "end_offset": 7464,
            "byte_start": 7562,
            "byte_end": 7599,
            "line_start": 161,
            "line_end": 162,
            "chars": 37,
            "sha256": "sha256:201b3ec8c9892bbd4401f64b9951d9bf2f3669813bc831f8a6ca2df190101979"
          },
          {
            "index": 23,
            "level": 3,
            "title": "Current Limitations",
            "start_offset": 7464,
            "end_offset": 8442,
            "byte_start": 7599,
            "byte_end": 8582,
            "line_start": 163,
            "line_end": 174,
            "chars": 978,
            "sha256": "sha256:5417046734060b98a63d55020077487647f88d8f3fc7dc3edd0b6a8e7f34b64a"
          },
          {
            "index": 24,
            "level": 3,
            "title": "Applicability Domain",
            "start_offset": 8442,
            "end_offset": 8900,
            "byte_start": 8582,
            "byte_end": 9051,
            "line_start": 175,
            "line_end": 184,
            "chars": 458,
            "sha256": "sha256:292d5dde5aa937929a41ce2d2e5a845a64442f8a671b5a52e82bd09512462d93"
          },
          {
            "index": 25,
            "level": 2,
            "title": "6. Error Assessment",
            "start_offset": 8900,
            "end_offset": 8924,
            "byte_start": 9051,
            "byte_end": 9075,
            "line_start": 185,
            "line_end": 186,
            "chars": 24,
            "sha256": "sha256:4af2129bc0060e67ea9792c0efe1e20db91319210e0ecbfefdf56babbb094d00"
          },
          {
            "index": 26,
            "level": 3,
            "title": "Quantitative Error Summary",
            "start_offset": 8924,
            "end_offset": 9631,
            "byte_start": 9075,
            "byte_end": 9808,
            "line_start": 187,
            "line_end": 199,
            "chars": 707,
            "sha256": "sha256:49de28df371151203e95efe83d1499fd3c201236436891c0bf1aac37569b482b"
          },
          {
            "index": 27,
            "level": 3,
            "title": "Error Sources",
            "start_offset": 9631,
            "end_offset": 10450,
            "byte_start": 9808,
            "byte_end": 10640,
            "line_start": 200,
            "line_end": 209,
            "chars": 819,
            "sha256": "sha256:580944b72afc9dece9d640309c510736887157934234d4e2c6923d03d71f580a"
          },
          {
            "index": 28,
            "level": 3,
            "title": "Conclusion",
            "start_offset": 10450,
            "end_offset": 10790,
            "byte_start": 10640,
            "byte_end": 10980,
            "line_start": 210,
            "line_end": 213,
            "chars": 340,
            "sha256": "sha256:4227c11e5772dd3daa377b4a9aca55367a56faab9d8b2cd51e9e8b38a5498584"
          },
          {
            "index": 29,
            "level": 2,
            "title": "Audit Trail",
            "start_offset": 10790,
            "end_offset": 11250,
            "byte_start": 10980,
            "byte_end": 11440,
            "line_start": 214,
            "line_end": 222,
            "chars": 460,
            "sha256": "sha256:432e4ad5fc2e5365e7e26ca735f00f58eb857e003a4138cb8b4117b2f4242225"
          }
        ]
      },
      "probe_result": {
        "purpose": "只复算原文自述跳变的量级，不改报告结论，供 03/04 复核",
        "inputs": {
          "mu": 0.001,
          "rho_f": 998.0,
          "d": 0.001,
          "epsilon": 0.8,
          "input_source": "μ/ρ_f/d 取原文 Packed Bed 配置；ε=0.8 为原文 Gidaspow 切换点"
        },
        "re_conventions": {
          "A": "Re = ρ_f|u|d/μ（字面读法）",
          "B": "Re = ρ_f ε|u|d/μ（按原文 C_D(εRe) 读法）"
        },
        "cases": [
          {
            "u": 0.002,
            "c_ergun": 3.425174568576917e-05,
            "c_wenyu_A": 1.6904397460169922e-05,
            "c_wenyu_B": 2.0546968589616752e-05,
            "jump_A_percent": -50.64661049613795,
            "jump_B_percent": -40.011908361933344
          },
          {
            "u": 0.05,
            "c_ergun": 0.00011998286395912187,
            "c_wenyu_A": 4.3601748535864516e-05,
            "c_wenyu_B": 4.917562765731647e-05,
            "jump_A_percent": -63.660020191950395,
            "jump_B_percent": -59.01445753614399
          }
        ],
        "sweep": {
          "u_min": 0.001,
          "u_max": 0.1,
          "samples": 400,
          "abs_jump_min_percent": 39.844605067294516,
          "abs_jump_max_percent": 70.42867809826971
        },
        "report_claim_percent": 25.0,
        "report_claim_inside_probe_range": false,
        "status": "unresolved_probe",
        "implication": "按原文 §2 逐字分支公式与原文自身参数，ε=0.8 处线性拖曳系数的跳变幅度落在上面 sweep 区间内、符号为负；原文正文称 ~25%。两者不一致，可能原因：原文公式行是摘要（实现里的 A_p/V_p 归一或 ε 幂次不同），或 ~25% 指未说明的工况。本包不下断言，登记为 UR-03 交 03/04 复核。"
      },
      "decision_basis": [
        {
          "id": "DB-01",
          "evidence": [
            "EV-02"
          ],
          "statement": "报告自述目的是验证两条闭合关系（Ergun 压降、Richardson-Zaki 沉降），不是提出新方法或新方案。",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "DB-02",
          "evidence": [
            "EV-04",
            "EV-05"
          ],
          "statement": "原文含可执行闭合关系式（Gidaspow 混合拖曳、单位体积空隙率积分式），scientific-computation 的 governing-equations 信号命中。",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "DB-03",
          "evidence": [
            "EV-06",
            "EV-07"
          ],
          "statement": "原文给出时间离散格式与步长（explicit Euler；dt = 0.1 τ），discretisation 信号命中。",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "DB-04",
          "evidence": [
            "EV-08",
            "EV-09"
          ],
          "statement": "原文含独立收敛性判据章节（Criterion 6，dt → dt/2），convergence-study 信号命中。",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "DB-05",
          "evidence": [
            "EV-10",
            "EV-11",
            "EV-12",
            "EV-13"
          ],
          "statement": "原文的误差陈述都配有明确参照（Ergun 关联式、Schiller-Naumann 解析解、Richardson-Zaki 关联式），满足 extract-accuracy-statements 的前提。",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "DB-06",
          "evidence": [
            "EV-15"
          ],
          "statement": "原文含建模假设/局限清单，满足 extract-assumptions step。",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "DB-07",
          "evidence": [
            "EV-03",
            "EV-10",
            "EV-20"
          ],
          "statement": "experimental-validation 虽在 test-matrix / validation-case / baseline-comparison 三条信号命中，但其 registry step extract-uncertainty 要求逐字照抄不确定度与包含因子，原文只有数值误差来源讨论，step-fit 不满足。",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "DB-08",
          "evidence": [
            "EV-16",
            "EV-17"
          ],
          "statement": "software-engineering 只在 Audit Trail 出现模块/测试字样，changed-files/commit/interface/regression/API 信号 0 命中，不是变更说明类报告。",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "DB-09",
          "evidence": [
            "EV-19"
          ],
          "statement": "原文引用密度远低于 literature-review 阈值（见 signals 派生量），且无 related work / survey / bibliography 结构。",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        }
      ],
      "evidence": [
        {
          "id": "EV-01",
          "field": "classification.source.title_line",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 0,
            "end_offset": 70,
            "byte_start": 0,
            "byte_end": 70,
            "line_start": 1,
            "line_end": 1,
            "quote": "# IN144-N09: Granular Bed Fluid-Solid Coupling Minimum Verifiable Unit",
            "content_hash": "sha256:0d9644b969e03237730ade31e993849824e40a65d2b1b2e1c621e20696a4e081",
            "chars": 70
          },
          "bound_section": "IN144-N09: Granular Bed Fluid-Solid Coupling Minimum Verifiable Unit",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-02",
          "field": "classification.report_type.primary / stated purpose",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 237,
            "end_offset": 299,
            "byte_start": 237,
            "byte_end": 299,
            "line_start": 6,
            "line_end": 6,
            "quote": "The implementation validates two fundamental closure relations",
            "content_hash": "sha256:9480c5825bfe1407fdb2b58cbf2da07e53dfa854cd30444e737f15b7fcbdd5ff",
            "chars": 62
          },
          "bound_section": "Physical Background",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-03",
          "field": "signals.experimental-validation.test matrix",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 2539,
            "end_offset": 2598,
            "byte_start": 2595,
            "byte_end": 2654,
            "line_start": 61,
            "line_end": 61,
            "quote": "Six machine-checkable criteria validate the implementation:",
            "content_hash": "sha256:66a265a93a9e26edc85c4db5aab8ae33beb48110616b148a9f19faf5bd56d9db",
            "chars": 59
          },
          "bound_section": "Verification Strategy",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-04",
          "field": "signals.scientific-computation.governing equations",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 1680,
            "end_offset": 1707,
            "byte_start": 1704,
            "byte_end": 1733,
            "line_start": 39,
            "line_end": 39,
            "quote": "F_drag = c(ε, |u|) · u_slip",
            "content_hash": "sha256:690b0218cc9d4f5f87daa370f9868e08b0a60b6e84096626dff5e39979b5bc5f",
            "chars": 27
          },
          "bound_section": "Numerical Approach",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-05",
          "field": "signals.scientific-computation.governing equations (closure form)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 1768,
            "end_offset": 1841,
            "byte_start": 1794,
            "byte_end": 1876,
            "line_start": 42,
            "line_end": 42,
            "quote": "**Ergun branch** (ε < 0.8): c = V_p [150μ(1-ε)/(ε³d²) + 1.75ρ_f|u|/(ε³d)]",
            "content_hash": "sha256:ce4c6bdda8f38af47f56cb3495bb6eff97f81ae0a2d17fbd68d92e12ad70a493",
            "chars": 73
          },
          "bound_section": "Numerical Approach",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-06",
          "field": "signals.scientific-computation.discretisation",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 2240,
            "end_offset": 2300,
            "byte_start": 2287,
            "byte_end": 2347,
            "line_start": 54,
            "line_end": 54,
            "quote": "Semi-coupled batch settling with explicit Euler integration:",
            "content_hash": "sha256:ccccdb31b6197f60a5a21366392fbc68842f541e81e789a6dae5c585880541ce",
            "chars": 60
          },
          "bound_section": "Numerical Approach",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-07",
          "field": "signals.scientific-computation.discretisation (dt)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 2378,
            "end_offset": 2428,
            "byte_start": 2432,
            "byte_end": 2484,
            "line_start": 56,
            "line_end": 56,
            "quote": "- Time step: dt = 0.1 τ (τ = drag relaxation time)",
            "content_hash": "sha256:455079bde8d5d2f135d1fa5cb295a4df1b5383c8ac8c2b5ab2b9f60ab1977a81",
            "chars": 50
          },
          "bound_section": "Numerical Approach",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-08",
          "field": "signals.scientific-computation.convergence study",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 5582,
            "end_offset": 5620,
            "byte_start": 5705,
            "byte_end": 5743,
            "line_start": 133,
            "line_end": 133,
            "quote": "### Criterion 6: Time-Step Convergence",
            "content_hash": "sha256:22b0227807d9535790f21cc2f24eff68e5748d9df5165285a94e8b3389fb8883",
            "chars": 38
          },
          "bound_section": "Criterion 6: Time-Step Convergence",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-09",
          "field": "signals.scientific-computation.convergence study (detail)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 5762,
            "end_offset": 5826,
            "byte_start": 5891,
            "byte_end": 5955,
            "line_start": 142,
            "line_end": 142,
            "quote": "The steady-state pressure drop is invariant to time-step halving",
            "content_hash": "sha256:1c51f27876be6cde2b4c3dcb43237e9f7a08798ecdc92bc47d9492fa9636d172",
            "chars": 64
          },
          "bound_section": "Criterion 6: Time-Step Convergence",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-10",
          "field": "signals.experimental-validation.baseline comparison (headline error)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 3894,
            "end_offset": 3944,
            "byte_start": 4003,
            "byte_end": 4053,
            "line_start": 93,
            "line_end": 93,
            "quote": "**Maximum relative error:** 1.47% (threshold: 15%)",
            "content_hash": "sha256:39a536bf61ee736e3e9e2ba5af7d8e8be0e48d371a9f31f2a2343d04f6726df4",
            "chars": 50
          },
          "bound_section": "Criterion 2: Ergun Pressure Drop",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-11",
          "field": "signals.experimental-validation.baseline comparison (measured vs reference row)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 3784,
            "end_offset": 3834,
            "byte_start": 3885,
            "byte_end": 3939,
            "line_start": 90,
            "line_end": 90,
            "quote": "| Laminar | 2.0×10⁻³ | 2180.55 | 2212.71 | 1.47% |",
            "content_hash": "sha256:c4a00e977f0af96576b4a5463ad7dc26f276e891a2fbd3d4289321cc092a5a1e",
            "chars": 50
          },
          "bound_section": "Criterion 2: Ergun Pressure Drop",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-12",
          "field": "signals.experimental-validation.baseline comparison (analytical reference)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 4472,
            "end_offset": 4569,
            "byte_start": 4584,
            "byte_end": 4681,
            "line_start": 108,
            "line_end": 108,
            "quote": "The simulated terminal velocity matches the Schiller-Naumann analytical solution to within 0.013%",
            "content_hash": "sha256:2418f8588406b46952c26e79952f1a4ae5437ed281d77ad5e028ee454c05256d",
            "chars": 97
          },
          "bound_section": "Criterion 3: Single-Particle Terminal Velocity",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-13",
          "field": "signals.experimental-validation.baseline comparison (correlation reference)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 4854,
            "end_offset": 4935,
            "byte_start": 4968,
            "byte_end": 5049,
            "line_start": 120,
            "line_end": 120,
            "quote": "The DEM settling simulations recover the Richardson-Zaki exponent to within 0.035",
            "content_hash": "sha256:c1a734fa165fa4a48569f52f84e1ef99e20e1da127cbd27cc5bc552ab149fbdf",
            "chars": 81
          },
          "bound_section": "Criterion 4: Richardson-Zaki Hindered Settling",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-14",
          "field": "step-fit.experimental-validation.extract-conditions (configuration)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 1082,
            "end_offset": 1128,
            "byte_start": 1088,
            "byte_end": 1134,
            "line_start": 20,
            "line_end": 20,
            "quote": "- Particle diameter: d = 1.0 mm (monodisperse)",
            "content_hash": "sha256:a32532e1b064a119468e4be24ba8388949972e28b7c18fdc24183579b340ac57",
            "chars": 46
          },
          "bound_section": "Geometry and Parameters",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-15",
          "field": "step-fit.scientific-computation.extract-assumptions",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 7489,
            "end_offset": 7552,
            "byte_start": 7624,
            "byte_end": 7687,
            "line_start": 165,
            "line_end": 165,
            "quote": "1. **Unresolved fluid**: The fluid is a single uniform velocity",
            "content_hash": "sha256:9301d90260e2bc983e3541074e7e9203939b840cf11a3f55ba04af08de2d54e2",
            "chars": 63
          },
          "bound_section": "Current Limitations",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-16",
          "field": "signals.software-engineering (audit-trail only)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 10806,
            "end_offset": 10875,
            "byte_start": 10996,
            "byte_end": 11065,
            "line_start": 216,
            "line_end": 216,
            "quote": "- **Module**: `tensordem.bedcoupling` (closures, packing, bed, study)",
            "content_hash": "sha256:abcfe35b581ca13b2f589225ea778922ee678334ae223839693ab10efddf8608",
            "chars": 69
          },
          "bound_section": "Audit Trail",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-17",
          "field": "signals.software-engineering (audit-trail only)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 10876,
            "end_offset": 10956,
            "byte_start": 11066,
            "byte_end": 11146,
            "line_start": 217,
            "line_end": 217,
            "quote": "- **Tests**: `tests/test_bedcoupling_*.py` (4 test files, 28 tests, all passing)",
            "content_hash": "sha256:bdd53acf8bbaf7fe50714ff25838b78e07c2ad9009958535dcc0c11a21a8ff0e",
            "chars": 80
          },
          "bound_section": "Audit Trail",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-18",
          "field": "classification.rationale (conclusion sentence)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 10466,
            "end_offset": 10543,
            "byte_start": 10656,
            "byte_end": 10733,
            "line_start": 212,
            "line_end": 212,
            "quote": "The implementation passes all six acceptance criteria with substantial margin",
            "content_hash": "sha256:876d6394a69626385c66890b887c54d325bb251fd2ce8c63ae0f4d2ec5eddd35",
            "chars": 77
          },
          "bound_section": "Conclusion",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-19",
          "field": "signals.literature-review (citation marker)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 305,
            "end_offset": 347,
            "byte_start": 305,
            "byte_end": 347,
            "line_start": 8,
            "line_end": 8,
            "quote": "**Ergun pressure drop correlation** (1952)",
            "content_hash": "sha256:a11b1d9ef518c273619b74c673b08dbad530ea9e2fc7cd1b602460760c00c328",
            "chars": 42
          },
          "bound_section": "Physical Background",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-20",
          "field": "step-fit.experimental-validation.extract-uncertainty (no coverage factor)",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 9631,
            "end_offset": 9648,
            "byte_start": 9808,
            "byte_end": 9825,
            "line_start": 200,
            "line_end": 200,
            "quote": "### Error Sources",
            "content_hash": "sha256:aeab6335669a697108a941d81a7c585e37eb570f3f5ba9db54a8a4e52891b7c8",
            "chars": 17
          },
          "bound_section": "Error Sources",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-21",
          "field": "signals.algorithm-implementation.function signature",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 10957,
            "end_offset": 11038,
            "byte_start": 11147,
            "byte_end": 11228,
            "line_start": 218,
            "line_end": 218,
            "quote": "- **Acceptance study**: `run_acceptance_study()` (deterministic, seed-controlled)",
            "content_hash": "sha256:2550ae4de7586710a74fe07d0142984eb97dc3f173f19ec498759be427ab7c08",
            "chars": 81
          },
          "bound_section": "Audit Trail",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        },
        {
          "id": "EV-22",
          "field": "classification.applicability_scope",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 8442,
            "end_offset": 8466,
            "byte_start": 8582,
            "byte_end": 8606,
            "line_start": 175,
            "line_end": 175,
            "quote": "### Applicability Domain",
            "content_hash": "sha256:21c08f604c8d6f53f06dc528a027e745f4f4d8645e8878668dab3b8a02d4db0f",
            "chars": 24
          },
          "bound_section": "Applicability Domain",
          "epistemic_status": "draft",
          "assessment_status": "unassessed"
        }
      ],
      "unresolved": [
        {
          "id": "UR-01",
          "question": "主类型 scientific-computation 与备选 experimental-validation 在 registry 信号命中上同为 3/5，分类结论是否会被独立审核推翻？",
          "reason": "两型语义相邻（数值实验的验证）；本包只按事先声明的 R2（step-fit）定胜负，未做语义投票。",
          "status": "unresolved",
          "suggested_handler": "工序 04 独立审核（reviewer_role=document-analyst）"
        },
        {
          "id": "UR-02",
          "question": "报告是否含测量不确定度与包含因子（experimental-validation 的 extract-uncertainty 前提）？",
          "reason": "全文探针 'measurement uncertainty|coverage factor|uncertainty budget' 0 命中；仅在 Error Sources 讨论数值误差来源，不能等同于测量不确定度声明。",
          "status": "unresolved",
          "suggested_handler": "若审核者认为数值误差来源等价于不确定度声明，则类型结论需复议"
        },
        {
          "id": "UR-03",
          "question": "报告称 ε=0.8 处拖曳系数有 ~25% 跳变；按原文逐字分支公式复算，|跳变| 落在 39.8%–70.4%（见 probe_result），两者不一致。",
          "reason": "原文未给 ~25% 的计算过程与工况；本包只对原文公式行做量级探针，不下断言、不改报告结论。可能原因：公式行是摘要（A_p/V_p 归一或 ε 幂次不同），或该 25% 指未说明的工况。",
          "status": "unresolved",
          "suggested_handler": "工序 03/04 复核（需 closure 实现与原文公式一致）"
        }
      ],
      "claims_note": "task_type=02-classification-parse 不做知识抽取：本包不产生 claims，也绝不给报告任何结论打 verified；report_type 同样只是可反驳的假设",
      "scope_guard": {
        "report_ids_read": [
          "9246"
        ],
        "report_ids_written": [
          "9246"
        ],
        "upstream_artifacts_modified": [],
        "other_work_packages_touched": []
      }
    }
  }
}
```
