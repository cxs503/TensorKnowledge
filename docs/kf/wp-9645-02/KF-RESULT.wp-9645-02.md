## ① 本工序做了什么

本单执行 `02-classification-parse`（Lane B，package_id=`wp-9645-02`），只对 **report_id=9645** 一份报告打**类型 / 主题标签**，并给出判定依据的**原文逐字定位**。按契约 `objective.classify_report_type: true`、`register_assets: false`：不登记资产、不做 claim 抽取、不写任何 verified 标记（验证等级由平台门计算）。

交付物是一个 `classification.json`：六分型主型 + 备选型 + 置信度、结构切分 8 段、选中 skill、9 个主题标签、10 条分类 claim、34 条逐字定位器、3 条显式 unresolved。

判定结论（**可反驳假设**，不是单点断言）：

- **主型 = `scientific-computation`，置信度 0.85** —— 模板 5 信号中 1 精确命中（governing equations）+ 1 部分命中（收敛证据在求解器层）；结构性证据（结果表 / 解析基准 / 敏感性 / 复现脚本）压倒性，见 loc-007/009/011/017/019/027/031。
- **备选型 = `experimental-validation`，0.4** —— 有多路基准对照与负控，但无试验设施、无测量不确定度，故不选为主型。
- **选中 skill = `xsk-scientific-computation` v0.1.0**（`template-created`），由 registry 的 report_type→skill 映射直接决定，不另立 skill。
- **拒绝** `literature-review` / `technical-proposal` / `software-engineering`；其中两条的拒绝依据是"缺失"，如实记为 `unresolved`（见 ⑤）。

学科标签（派生）：冰区航行、结构　场景键：`ice_partial_factors_target_inverse`。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文（不许凭记忆）**：`GET /tensor/reports/9645` 取 `markdown` 字段，落地为 `docs/kf/wp-9645-02/source_9645.md`。
2. **哈希门**：对取回字节重算 sha256，与契约 `source_hash` 逐字比较 → `source_hash_matches=True`（chars=11824，bytes=15967）。
3. **零手抄定位器**：脚本用"行探针"在原文里找行，**引文就是原文该行本身**（不是复述、不是记忆），随后程序化计算 char/byte 偏移、行号与 `content_hash = sha256(quote)`。因此引文不可能漂移，`source_locator_resolvable` 可机械复核。
4. **结构切分**：正则 `^#{1,3} ` 切标题得 8 段，每段给 char/行区间与 role（context_and_parameters / method_and_toolchain / numerical_results / figures / caveats_and_limitations / error_verdict_vs_baseline / provenance_and_audit_chain）。
5. **分类**：以 `extraction-skills/registry.json`（v1.0）的 6 个报告类型与 `identify_signals` 为准，逐条判 `exact / partial / absent / not_applicable`；**没把 absent 当命中**，也没为凑命中编造信号。
6. **不越界**：全程只请求 report 9645；不读其它 report_id，不改上游产物，不给 verified。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9645-02/classification.json` | 主产物：主型+备选型+置信度、结构切分 8 段、选中 skill、9 主题标签、10 claim（8 supported / 2 unresolved）、34 定位器、3 unresolved 挂账。 |
| `docs/kf/wp-9645-02/kf_result.json` | 交付信封（kf_result.v1）：package_id / task_type / report_id / provenance / outputs。 |
| `docs/kf/wp-9645-02/source_9645.md` | 原文快照，供复算 source_hash 与回切引文。 |
| `docs/kf/wp-9645-02/report_selfcheck.json` | 六项 acceptance 逐条自检记录（6/6 PASS）。 |
| `docs/kf/wp-9645-02/KF-RESULT.wp-9645-02.md` | 本报告（正文六段 + 唯一结果代码块）。 |
| `docs/kf/wp-9645-02/platform_payload.json` | 平台发布载荷（title / summary / tags / markdown）。 |
| `scripts/kf_wp9645_02_classify.py` | 取件→哈希→定位→分类→自检→写产物。 |
| `scripts/emit_kf_wp9645_02_report.py` | 由产物生成报告正文与发布载荷（数字全部注入）。 |
| `tests/test_kf_wp9645_02.py` | 断言：定位器按偏移回切一致、哈希一致、id 唯一、claim 均有证据或 unresolved、报告仅一个 json 块。 |

主题标签：

| topic tag | locators |
| ice-load/ISO-19906 | loc-005, loc-020 |
| pressure-area-relation | loc-005, loc-007 |
| reliability-based-calibration/target-beta | loc-002, loc-004 |
| inverse-problem/partial-factors | loc-008, loc-009, loc-019 |
| FORM-IS-MC-crosscheck | loc-010, loc-011, loc-012 |
| Nataf-correlation | loc-034 |
| negative-control | loc-013 |
| sensitivity/adjoint-vs-finite-difference | loc-017, loc-018 |
| secondary-source-table-comparison | loc-020, loc-022 |

类型判定与拒绝理由：

| 类型 | 置信度 | 判定 |
| experimental-validation | 0.40 | 有多路基准对照与负控（loc-010/011/013），但无试验设施、无测量不确定度；此处的 'experimental' 是数值验证而非实验验证，故降为备选型并保留其信号。 |
| algorithm-implementation | 0.20 | 确有阻尼 Newton + 包络定理 Jacobian + 二分独立复核（loc-008/014/015/018），但原文无伪代码、无复杂度陈述，模板判据不满足。 |
| software-engineering | 0.05 | 只出现模块名与复现命令（loc-001/031），无变更文件、无接口/回归变更；拒绝依据是'缺失'，故记 unresolved（cls-9645-006）。 |
| literature-review（rejected） | — | 无 survey/相关工作结构；全篇仅引 ISO 19906 Annex A 且自述为二次文献转录（loc-022），不满足 'citation density >= 5 per 1000 chars' 信号。拒绝依据为缺失，记 unresolved（cls-9645-007）。 |
| technical-proposal（rejected） | — | 交付的是已算出的结果表与机器判据（loc-003/004/019），不是计划/规格/roadmap 结构。 |

registry 信号匹配（exact 1 / partial 1 / absent-or-N-A 3 of 5）：

| report_type | identify_signal（registry 原文） | 匹配 | locators | 说明 |
| scientific-computation | governing equations | exact | loc-005, loc-007, loc-009 | 压力–面积幂律 p(A)=p0(A/A0)^-ex 与极限状态反问题方程组逐字在原文。 |
| scientific-computation | discretisation | not_applicable | loc-009, loc-024 | 无 PDE/网格离散：失效域为 u 空间半空间、FORM 解析精确；模板信号不覆盖此类可靠性问题。 |
| scientific-computation | convergence study | partial | loc-014, loc-015, loc-016 | 收敛证据在求解器层（Newton 残差二次收敛、三初值同根、Jacobian 条件数 4.791），不是网格收敛研究。 |
| scientific-computation | mesh refinement | absent | — | 原文无网格细分；按 no_forced_claim_generation 记为 absent，不补造。 |
| scientific-computation | timing table | absent | — | 原文无运行时间表（无计时行），记为 absent。 |
| （备选型）experimental-validation | baseline comparison | exact | loc-011, loc-012, loc-026 | FORM 对闭式解析、重要性抽样、粗 MC 的多路对照表逐字在原文。 |
| （备选型）experimental-validation | test matrix | partial | loc-020, loc-021 | 有 9 对 ISO 表格 + 1 仓内锚点的算例矩阵，但不是试验/测量矩阵。 |
| （备选型）experimental-validation | measurement uncertainty | partial | loc-033 | 有抽样统计的 1σ/95 % 覆盖判断，属蒙特卡洛统计不确定性，不是测量不确定度。 |
| （备选型）experimental-validation | validation case | partial | loc-013 | 负控（置 ρ=0 重跑）是验证用算例，但不是物理标定试验。 |
| （备选型）experimental-validation | facility | absent | — | 纯数值研究，无试验设施，记为 absent。 |

结构切分：

| segment | 标题 | role | char 区间 | 行 | chars |
| seg-01 | # IN101-N09 — ISO 19906 ice-pressure partial-factor back-calibration at beta_T = 4.0 (mature: target-reliability inverse, FORM/IS/MC cross-checked) | title_and_machine_criteria | [0,652) | L1–L15 | 652 |
| seg-02 | ## ① 案例介绍（物理背景 / 参数表） | context_and_parameters | [652,1486) | L15–L34 | 834 |
| seg-03 | ## ② 怎么做的（方法 / 流程 / 工具链） | method_and_toolchain | [1486,3009) | L34–L47 | 1523 |
| seg-04 | ## ③ 计算结果 | numerical_results | [3009,7553) | L47–L139 | 4544 |
| seg-05 | ## ④ 结果图 | figures | [7553,9265) | L139–L165 | 1712 |
| seg-06 | ## ⑤ 注意点（坑 / 局限 / 适用范围） | caveats_and_limitations | [9265,10598) | L165–L174 | 1333 |
| seg-07 | ## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3 %） | error_verdict_vs_baseline | [10598,11379) | L174–L190 | 781 |
| seg-08 | ## 审计链 | provenance_and_audit_chain | [11379,11824) | L190–L196 | 445 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

分类 claim 账本（每条 supported 至少一条已解析 locator；unresolved 必须有理由）：

| claim id | type | status | conf | locators | statement |
| cls-9645-001 | classification | supported | 0.85 | loc-005, loc-007, loc-009, loc-019, loc-027, loc-028 | 主型为 scientific-computation：以压力–面积幂律与控制方程组为骨架，输出数值结果表，并由脚本零手抄注入数字。 |
| cls-9645-002 | classification | supported | 0.90 | loc-002, loc-006, loc-008, loc-009, loc-019 | 本报告是分项系数（设计格式）标定的反问题研究：目标 β_T=4.00，输出 (γ_f, ψ) 与 κ=γ_f·ψ，属'规范标定'子型而非一般数值算例。 |
| cls-9645-003 | classification | supported | 0.75 | loc-010, loc-011, loc-012, loc-013, loc-033 | 报告具备验证型特征（多路基准对照 + 负控 + 1σ 覆盖判断），故把 experimental-validation 列为备选型（0.40）并叠加标签，但不据此改选 skill。 |
| cls-9645-004 | classification | supported | 0.70 | loc-008, loc-014, loc-015, loc-016, loc-018 | 含算法实现成分（阻尼 Newton、包络定理 Jacobian、二分独立复核），但缺伪代码与复杂度陈述，不足以判为 algorithm-implementation。 |
| cls-9645-005 | classification | supported | 0.80 | loc-003, loc-004, loc-019, loc-032 | 不是 technical-proposal：交付物为已算出的结果表与机器判据汇总（5/5 通过），无计划/规格/roadmap 结构。 |
| cls-9645-006 | classification | unresolved | 0.60 | loc-001, loc-031 | 拒绝 software-engineering 的依据是'缺变更记录/接口变更'，属否定性证据，无法用逐字引文证明。 |
| cls-9645-007 | classification | unresolved | 0.65 | loc-022 | 拒绝 literature-review 同样基于缺失（无 survey/相关工作节，仅一处二次文献引用）。 |
| cls-9645-008 | descriptive | supported | 0.90 | loc-022, loc-020 | 与 ISO 表格比对的裁决依赖二次文献转录（source_tier=secondary, primary_source_verified=False），故相关标签与结论只能标 conditional；下游引用表值必须带此限定。 |
| cls-9645-009 | descriptive | supported | 0.95 | loc-029, loc-030 | 报告引用的图与结果 JSON 位于工作树外的绝对路径（/root/tp-agent/work/m8350/…），本工序无法在 worktree 内解析；按边界不改写、不登记资产，只在下游风险处挂账。 |
| cls-9645-010 | descriptive | supported | 0.90 | loc-023, loc-025 | 适用范围与约定限制由原文显式给出：单一年极值接触面积分布 + 单一幂律指数 + 抗力与冰力独立；且 κ 无约定而 γ_f/ψ 的劈分属约定，故跨来源比对只应以 κ 为准。 |

逐字定位器（char 区间可机械回切；`sha256(quote)[:12]` 为引文哈希前 12 位）：

| locator | 原文引文（逐字，未改写） | char 区间 | 行 | sha256(quote)[:12] |
| loc-001 | 「**仓库** TensorPhysics ｜ **模块** `tensorphysics.ice_partial_factors`」 | [149,214) | L3 | bc899cacb62f |
| loc-002 | 「**目标** $\beta_T$ = 4.00 ($P_f$ = 3.1671e-05)」 | [281,325) | L3 | 29525cc93165 |
| loc-003 | 「\| `a_form_vs_simulation` \| PASS \|」 | [424,457) | L7 | dd21609e457e |
| loc-004 | 「**判据汇总** 5/5 通过」 | [635,650) | L13 | 7a00af3138cc |
| loc-005 | 「ISO 19906 用压力–面积关系描述冰载荷：作用于接触（或整体）面积 $A$ 上的冰压随面积下降，$p(A)=p_0(A/A_0)^{-ex}$。结构承受的冰力因此是 $F=k_F\,p(A)\,A$，而指数为负意味着**产生年极值冰力的冰压与面积负相关**：大面积伴随低压。本节点把「冰压年极…」 | [675,944) | L17 | b5763be94c8a |
| loc-006 | 「\| 特征冰力 $F_k$ \| 23.517 MN \| 100 年超越（年超越概率 1e-2）\|」 | [1256,1303) | L28 | e7faca3b18a2 |
| loc-007 | 「\| $ex$ \| 0.400 \| ISO 压力–面积指数 \|」 | [1011,1041) | L22 | 93d5797fbe74 |
| loc-008 | 「2. **反问题两方程两未知量**（`target_reliability_inverse.py`）。极限状态只通过 $\kappa=\gamma_f\psi$ 依赖分项系数对（构件按 $R_k=\kappa F_k$ 定尺），因此」 | [1991,2107) | L37 | c6ed95dae734 |
| loc-009 | 「$$F_1(\gamma_f,\psi)=\beta(\kappa)-\beta_T=0,\qquad F_2(\gamma_f,\psi)=\gamma_f-F^*(\kappa)/F_k=0$$」 | [2109,2208) | L39 | 4952ebe52966 |
| loc-010 | 「3. **四条独立验证面**：(i) 设计点重要性抽样（$2\times10^5$）；(ii) 粗 Monte Carlo （4e+06 样本，失败数 140）；(iii) 抗力解析积分的 Rao–Blackwell 化粗 MC（同一估计量、方差更小）；(iv) 闭式 $\beta_{ln}$ 解…」 | [2476,2638) | L42 | 394c5bcd75e5 |
| loc-011 | 「**表 2 FORM 的四条独立验证（判据 a）**」 | [3497,3523) | L66 | cdc1b26e72c5 |
| loc-012 | 「\| 闭式 $\beta_{ln}$（解析）\| 4.000000 \| — \| 6.46e-09 \| — \|」 | [3642,3694) | L71 | 6dea61b61f8c |
| loc-013 | 「**表 6 负控（判据 e）：忽略 p–A 负相关**」 | [6457,6484) | L111 | 60f74748299a |
| loc-014 | 「\| Newton 迭代数（三初值） \| [7, 5, 5] \|」 | [3289,3320) | L60 | e07d254408d8 |
| loc-015 | 「\| Jacobian 条件数 \| 4.791 \|」 | [3355,3379) | L62 | de6e1728d615 |
| loc-016 | 「**图 3.** Left: residual norm of the two-equation system from three dispersed starting points (quadratic convergence, same root). Right: the design-va…」 | [8108,8319) | L149 | f45a2771a80f |
| loc-017 | 「**表 8 模型参数敏感性 $\partial\beta/\partial\theta$（在 $\kappa^*$ 处，中心差分）**」 | [7244,7311) | L129 | 920413a35fb4 |
| loc-018 | 「\| 伴随 $\partial\beta/\partial\kappa$ \| 中心差分 \| -3.33e-07 \| 是 \|」 | [10844,10904) | L181 | be3e704ffa67 |
| loc-019 | 「**表 1 反问题解**」 | [3020,3032) | L49 | 7f2bb5529ff0 |
| loc-020 | 「**表 4 与 ISO 19906 表格分项系数偏差（判据 d）**」 | [4247,4281) | L85 | 6dbd8d5e2692 |
| loc-021 | 「\| ice_action_frequent x steel_plate_yielding \| (1.00, 1.10) \| 1.1000 \| -30.41 % \| +10.44 % \| -23.15 % \| 超差/不保守 \| 3.1130 \|」 | [5172,5293) | L95 | 0afa67952bac |
| loc-022 | 「5. **表格值出处受限**：ISO 19906 Annex A 正文不在工作树内，A.2/A.3 为二次文献转录（`source_tier=secondary`, `primary_source_verified=False`），由它得出的裁决一律 `conditional`；仓内锚点 (1.2…」 | [10170,10436) | L171 | dcd1ea684b08 |
| loc-023 | 「6. **适用范围**：年极值接触面积按对数正态建模、冰压遵循单一幂律指数（$ex$ 为常数）、抗力与冰力独立。参数敏感性见表 8：$\partial\beta/\partial ex$ = +1.147 / 单位，即 $ex$ 每增加 0.1，$\beta$ 约上升 0.11 —— 指数是仅次于…」 | [10437,10596) | L172 | ed2915426635 |
| loc-024 | 「2. **该问题的 FORM 是精确的**：失效域 $\{R<F\}$ 在 $z=(\ln x-\mu)/\sigma$ 坐标下是超平面，线性变换到 $u$ 空间仍是超平面，故 Hasofer–Lind 距离即真值。因此「FORM 与 MC 差 3 %」这类常规判据在此**不能**用来检验 FOR…」 | [9524,9737) | L168 | 3a350fc256db |
| loc-025 | 「4. **分项系数对的唯一性依赖劈分约定**。$\kappa$ 由达到目标可靠度唯一确定，但 $\kappa$ 如何在 $\gamma_f$ 与 $\psi$ 之间劈分是约定；本节点采用 JCSS/ISO 2394 设计值劈分，于是 $\psi^*$ = 0.9960 ≈ 1（5 % 分位特征抗力…」 | [9897,10169) | L170 | 2ecc30d39427 |
| loc-026 | 「**结论**：FORM 与解析值、重要性抽样的一致性远优于 3 %（均为 1e-2 % 量级）；反问题残差 1e-11；伴随导数与有限差分一致到 1e-7；唯一未达 3 % 量级的对照是**粗 MC 的统计噪声**（1σ 约 8 %，Rao–Blackwell 化后约 6 %，两者 95 % 带均…」 | [11196,11377) | L188 | 0983f6889d4a |
| loc-027 | 「纯 Python（`tensorphysics.structural` 的 FORM/SORM/IS/MC + Nataf）」 | [2881,2943) | L45 | 78bca6039508 |
| loc-028 | 「所有数字由 `run_study()` 写入 JSON，报告文本从 JSON 注入（零手抄）」 | [2960,3006) | L45 | 69f654ac613a |
| loc-029 | 「![fig1](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig1_pa_joint.png)」 | [7741,7827) | L143 | 773a2a33b8c8 |
| loc-030 | 「- 结果 JSON：`/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/in101_n09_results.json`（本报告所有数字的唯一来源，`run_study()` 直出）」 | [11387,11512) | L192 | cdf4539535d2 |
| loc-031 | 「- 复现：`PYTHONPATH=src python3 benchmarks/iso19906_partial_factors/run_in101_n09.py`」 | [11741,11823) | L195 | d2f216d39de3 |
| loc-032 | 「## ③ 计算结果」 | [3009,3018) | L47 | 725f569a39ae |
| loc-033 | 「3. **±1σ 覆盖率是 68 % 检验**。粗 MC 本次得到 $P_f$=3.500e-05（失败数 140），估计偏高 1σ，1σ 带未覆盖 FORM，但 95 % 带覆盖；同一估计量的 Rao–Blackwell 化版本（抗力解析积分）方差小 10 倍以上，1σ 带覆盖。两者都写进 JS…」 | [9738,9896) | L169 | f3f09dc135f9 |
| loc-034 | 「1. **Nataf 吃物理相关、ISO 幂律给对数相关**。首版把 $\rho_{\ln p,\ln A}$ 直接当物理相关系数传入，结果 FORM 与闭式解析值相差 3 %、而重要性抽样又站在 FORM 一边（两者差 0.07 %）——即「解析基准错了」而不是「FORM 错了」。改为对数正态精…」 | [9290,9523) | L167 | 74d2f2355583 |

关键字段 → 引文映射：`report_type.primary` → loc-005, loc-007, loc-009, loc-027；`report_type.alternatives[experimental-validation]` → loc-010, loc-011, loc-013；`topic_tags[ice-load/ISO-19906]` → loc-005, loc-020；`domain_labels.discipline` → loc-005, loc-021；`selected_skill` → loc-005, loc-009, loc-014；`unresolved[ISO 表值]` → loc-022；`unresolved[附件可达性]` → loc-029, loc-030。

## ⑤ 注意点与局限

1. **模板信号覆盖不足，如实登记**：模板信号是关键词式的，对'可靠度标定 / 反问题'这类报告覆盖不足（据本份报告观察到，未做全库统计）：5 个信号里只有 governing equations 精确命中，收敛与精度证据只能算 partial。本包按结构性证据完成分类并如实登记该缺口，未据此改写 registry（超出本包范围）。
2. **两条拒绝是"否定命题"**：`software-engineering`、`literature-review` 的排除依赖"原文没有变更记录 / 相关工作节"，逐字引文无法证明"不存在"，故 cls-9645-006 / cls-9645-007 状态为 `unresolved` 而非 supported。分类结论因此按"主型 + 置信度"给出，允许 04 独立审核反驳。
3. **ISO 表值是二次文献**：原文自述「5. **表格值出处受限**：ISO 19906 Annex A 正文不在工作树内，A.2/A.3 为二次文献转录（`source_tier=secondary`, `prima…」——依赖 ISO 表值的标签/裁决只能 `conditional`，下游引用表值须带此限定。
4. **附件不可达**：图 1–6 与 `in101_n09_results.json` 都写在 `/root/tp-agent/work/m8350/`（另一工作树）下。本工序**不跨 worktree 取件、不登记资产**（`register_assets: false`），只在 unresolved 挂账，避免下游拿到悬空引用。
5. **本工序不做价值判断**：原文自述「**判据汇总** 5/5 通过」，这**不是**本工序的验证结论。原文同时提示「2. **该问题的 FORM 是精确的**：失效域 $\{R<F\}$ 在 $z=(\ln x-\mu)/\sigma……」——该问题上 "FORM vs MC 差 3 %" 不能当作 FORM 精度判据；此解读约束已写进 `selected_skill.downstream_note`，防止 03 工序误用。
6. **"实验验证"语义**：备选型 `experimental-validation` 的命中来自数值基准对照与负控，**不是**物理试验；若下游据此找试验数据会落空，已在 `secondary_type_signals` 中限定用途（只作标签层叠加）。
7. **未做**：不抽取 claim 知识对象（03 工序）、不做独立审核（04）、不评估报告自身结论正确性、不核算引用密度（需完整引文列表；原文通读只见一处二次文献引用，未做密度核算）。

## ⑥ 自检（逐条对照 acceptance）

| acceptance item | 结果 | 依据 |
| valid_json | PASS | classification.json / kf_result.json 由 json.dump 生成并可回读解析。 |
| schema_pass | PASS | 按 schemas/kf_result.v1.schema.json 的 required/type/enum/pattern/additionalProperties 子集校验：无违规 |
| source_locator_resolvable | PASS | 34 条定位器逐条按 char/byte 偏移回切原文并比对 quote 与 content_hash；失败项=无 |
| source_hash_matches | PASS | 重算 sha256:a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00，契约值 sha256:a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00 |
| no_duplicate_ids | PASS | claims 10/10 unique；locators 34/34 unique |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | supported 均带已解析 locator；unresolved 均带 unresolved_reason；缺证据=无 悬空引用=无 缺理由=无 |

unresolved 挂账：

| unresolved item | status | reason | claims |
| 否定性分类标签（software-engineering / literature-review 的拒绝） | unresolved | '不存在'命题不可由逐字引文证明；保留为可反驳假设。 | cls-9645-006, cls-9645-007 |
| ISO 19906 Annex A 原始表值 | unresolved | 原文自述 A.2/A.3 为二次文献转录且 primary_source_verified=False（loc-022）；本工序不得回溯规范正文，也不得把表值当一手证据。 | cls-9645-008 |
| 报告图 1–6 与 in101_n09_results.json 的可达性 | unresolved | 引用路径指向 /root/tp-agent/work/m8350/（另一工作树），本包不应跨 worktree 取件（loc-029/030）。 | cls-9645-009 |

**结论**：六项 acceptance 全部自检 PASS（6/6）。自检是**生产侧**检查，**不等于**平台验证结论或独立审核结论：本包不含 `verified` 字段，验证等级由平台门计算。

关于误差判定（纪律第 ⑥ 要素）：本工序是**分类解析**，不产生物理量或数值结果，故无"与解析解/文献基线比较的误差"可报；可机械判定的量是**定位保真度**与**哈希一致性**——定位器回切一致率 34/34（100 %），source_hash 与契约值一致，二者均可视为 <3 % 误差（实为 0）。**无图**：本工序无场量云图、无基线比较曲线可画，按纪律声明无图理由——分类任务的唯一结果形态是结构化 JSON 与逐字定位表，若强行出图只会是装饰性内容，故不出图。

## ⑦ 自审（adversarial pass，作者自审，非独立审核）

本工序在交付前对**自己的产物**做了一轮对抗性复核，按下表把发现的问题**就地修好**（修完重跑全部断言）：

| # | 严重度 | 缺陷 | 证据 | 处置 |
|---|---|---|---|---|
| A1 | 高（会是"填充"） | 4 条定位器（loc-006/023/025/032）挂在账上却**没有任何 claim/标签引用**，2 组定位器指向**同一行**（loc-001≡loc-002、loc-027≡loc-028），构成看似充数的重复证据 | 未被引用集合 = {loc-006, loc-023, loc-025, loc-032}；重复引文 2 组 | 改行探针为**子串探针**（引文收窄到该行内精确片段，消除重复）；把 4 条孤儿证据接进 cls-002/005 并新增 cls-010（适用范围与劈分约定）；新增断言 `test_evidence_is_non_redundant_and_fully_wired` 锁死"无重复/无嵌套/无孤儿" |
| A2 | 中（越界断言） | `registry_gap` 写"**平台常见报告族**覆盖不足"，属于没有证据支撑的频率断言 | 本工序只读了 1 份报告，无全库统计 | 收窄为"这类报告覆盖不足（据本份报告观察到，未做全库统计）" |
| A3 | 中（否定命题当已证） | "本 report **仅**一处二次文献引用" | 仅通读所见，未做引用密度核算 | 改为"通读只见一处，未做密度核算"；并把两条否定性分类判据显式记为 `unresolved`（cls-006/007） |
| A4 | 低（解析歧义） | loc-027 引文**包含** loc-028 引文，朴素子串解析可能落到错误区间 | 包含关系检查命中 1 对 | loc-027 收窄为子串探针；断言禁止任何引文互为子串（定位以显式偏移为准，不靠子串搜索） |
| A5 | 低（手工常量漂移） | `counts` 里 claim 数是**手写整数**，加 claim 时会说谎 | 加 cls-010 后手写值立刻过期 | 改为由实际列表计算，并加 `test_counts_are_consistent_with_content` |
| A6 | 低（交付信道风险） | 正文里出现 json 围栏字面量会被当成第二个结果块 | 首版渲染出 3 个 json 围栏出现点 | 正文禁用该字面量；渲染时断言**整篇只有 1 个围栏块**，测试 `test_delivered_markdown_has_exactly_one_json_block_equal_to_envelope` 再验一次 |

**独立性与未跑的检查（如实列出）**：作者=自审者，独立性有限；**未跑**：04 独立审核、全库类型分布对照（验证 0.85 置信度是否系统性偏高）、引用密度核算、`/root/tp-agent/work/m8350/` 下附件跨 worktree 核验（越界，不做）。**处置**：approve with notes —— 产物按 `delivery.status=draft` 交付，建议 04 独立审核重点复核 A2/A3 两条"否定命题"与主型置信度，验证等级留待平台门计算。

## ⑧ 复现


`repro_cmd`（一键，工作树根执行）：

    python3 scripts/kf_wp9645_02_classify.py && python3 scripts/emit_kf_wp9645_02_report.py && python3 -m pytest tests/test_kf_wp9645_02.py -q

产物全部落在 `docs/kf/wp-9645-02/`（worktree 内），无外部依赖；`TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS` 仅用于取原文，已有快照时离线复跑一致（快照哈希受门校验）。

## ⑨ 结果信封（唯一的 JSON 结果代码块，原样提交）

```json
{
  "package_id": "wp-9645-02",
  "task_type": "02-classification-parse",
  "contract_version": "1.0",
  "report_id": "9645",
  "provenance": {
    "source_uri": "tensor://reports/9645",
    "source_field": "markdown",
    "source_hash": "sha256:a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00",
    "source_hash_matches": true,
    "title": "IN101-N09 ISO 19906 冰压设计分项系数目标可靠度反标定（成熟化）",
    "scenario_key": "ice_partial_factors_target_inverse",
    "chars": 11824
  },
  "outputs": {
    "classification.json": {
      "schema": "kf-classification.v1",
      "package_id": "wp-9645-02",
      "task_type": "02-classification-parse",
      "report_id": "9645",
      "taxonomy": {
        "source": "extraction-skills/registry.json",
        "registry_version": "1.0",
        "report_types": [
          "literature-review",
          "scientific-computation",
          "algorithm-implementation",
          "software-engineering",
          "technical-proposal",
          "experimental-validation"
        ],
        "note": "分类是可反驳的假设；unclassified 为合法值。本包给出主型 + 备选型 + 置信度，而不是单点断言。"
      },
      "source": {
        "source_uri": "tensor://reports/9645",
        "source_field": "markdown",
        "source_hash": "sha256:a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00",
        "source_hash_matches": true,
        "chars": 11824,
        "bytes": 15967,
        "title": "IN101-N09 ISO 19906 冰压设计分项系数目标可靠度反标定（成熟化）",
        "scenario_key": "ice_partial_factors_target_inverse"
      },
      "report_type": {
        "primary": "scientific-computation",
        "primary_label_zh": "科学计算 / 可靠度标定（数值反问题 + 基准验证）",
        "confidence": 0.85,
        "confidence_basis": "模板 5 信号中 1 精确命中（governing equations）+ 1 部分命中（收敛证据在求解器层）；结构性证据（结果表 / 解析基准 / 敏感性 / 复现脚本）压倒性，见 loc-007/009/011/017/019/027/031。",
        "alternatives": [
          {
            "report_type": "experimental-validation",
            "confidence": 0.4,
            "why_not_primary": "有多路基准对照与负控（loc-010/011/013），但无试验设施、无测量不确定度；此处的 'experimental' 是数值验证而非实验验证，故降为备选型并保留其信号。",
            "locator_ids": [
              "loc-010",
              "loc-011",
              "loc-013",
              "loc-033"
            ]
          },
          {
            "report_type": "algorithm-implementation",
            "confidence": 0.2,
            "why_not_primary": "确有阻尼 Newton + 包络定理 Jacobian + 二分独立复核（loc-008/014/015/018），但原文无伪代码、无复杂度陈述，模板判据不满足。",
            "locator_ids": [
              "loc-008",
              "loc-014",
              "loc-015",
              "loc-018"
            ]
          },
          {
            "report_type": "software-engineering",
            "confidence": 0.05,
            "why_not_primary": "只出现模块名与复现命令（loc-001/031），无变更文件、无接口/回归变更；拒绝依据是'缺失'，故记 unresolved（cls-9645-006）。",
            "locator_ids": [
              "loc-001",
              "loc-031"
            ]
          }
        ],
        "rejected_types": [
          {
            "report_type": "literature-review",
            "reason": "无 survey/相关工作结构；全篇仅引 ISO 19906 Annex A 且自述为二次文献转录（loc-022），不满足 'citation density >= 5 per 1000 chars' 信号。拒绝依据为缺失，记 unresolved（cls-9645-007）。"
          },
          {
            "report_type": "technical-proposal",
            "reason": "交付的是已算出的结果表与机器判据（loc-003/004/019），不是计划/规格/roadmap 结构。"
          }
        ]
      },
      "topic_tags": [
        {
          "tag": "ice-load/ISO-19906",
          "locator_ids": [
            "loc-005",
            "loc-020"
          ]
        },
        {
          "tag": "pressure-area-relation",
          "locator_ids": [
            "loc-005",
            "loc-007"
          ]
        },
        {
          "tag": "reliability-based-calibration/target-beta",
          "locator_ids": [
            "loc-002",
            "loc-004"
          ]
        },
        {
          "tag": "inverse-problem/partial-factors",
          "locator_ids": [
            "loc-008",
            "loc-009",
            "loc-019"
          ]
        },
        {
          "tag": "FORM-IS-MC-crosscheck",
          "locator_ids": [
            "loc-010",
            "loc-011",
            "loc-012"
          ]
        },
        {
          "tag": "Nataf-correlation",
          "locator_ids": [
            "loc-034"
          ]
        },
        {
          "tag": "negative-control",
          "locator_ids": [
            "loc-013"
          ]
        },
        {
          "tag": "sensitivity/adjoint-vs-finite-difference",
          "locator_ids": [
            "loc-017",
            "loc-018"
          ]
        },
        {
          "tag": "secondary-source-table-comparison",
          "locator_ids": [
            "loc-020",
            "loc-022"
          ]
        }
      ],
      "domain_labels": {
        "discipline": [
          "ice-region-navigation",
          "structures"
        ],
        "discipline_label_zh": [
          "冰区航行",
          "结构"
        ],
        "discipline_basis": "冰压载荷 + 钢构件抗力/分项系数 → 冰区结构可靠度标定。派生标签，由 loc-005（冰压–面积关系）与 loc-021（ice_action × steel_plate 组合）共同支持。",
        "discipline_locator_ids": [
          "loc-005",
          "loc-021"
        ],
        "scenario_key": "ice_partial_factors_target_inverse",
        "language": "mixed zh/en（正文中文，标题/表头/图注英文）"
      },
      "selected_skill": {
        "skill_id": "xsk-scientific-computation",
        "skill_version": "0.1.0",
        "lifecycle_state": "template-created",
        "selection_basis": "主型 = scientific-computation，按 registry 的 report_type→skill 映射选取，不另立 skill。",
        "signal_match": [
          {
            "identify_signal": "governing equations",
            "matched": "exact",
            "locator_ids": [
              "loc-005",
              "loc-007",
              "loc-009"
            ],
            "note": "压力–面积幂律 p(A)=p0(A/A0)^-ex 与极限状态反问题方程组逐字在原文。"
          },
          {
            "identify_signal": "discretisation",
            "matched": "not_applicable",
            "locator_ids": [
              "loc-009",
              "loc-024"
            ],
            "note": "无 PDE/网格离散：失效域为 u 空间半空间、FORM 解析精确；模板信号不覆盖此类可靠性问题。"
          },
          {
            "identify_signal": "convergence study",
            "matched": "partial",
            "locator_ids": [
              "loc-014",
              "loc-015",
              "loc-016"
            ],
            "note": "收敛证据在求解器层（Newton 残差二次收敛、三初值同根、Jacobian 条件数 4.791），不是网格收敛研究。"
          },
          {
            "identify_signal": "mesh refinement",
            "matched": "absent",
            "locator_ids": [],
            "note": "原文无网格细分；按 no_forced_claim_generation 记为 absent，不补造。"
          },
          {
            "identify_signal": "timing table",
            "matched": "absent",
            "locator_ids": [],
            "note": "原文无运行时间表（无计时行），记为 absent。"
          }
        ],
        "signal_coverage": {
          "exact": 1,
          "partial": 1,
          "absent_or_not_applicable": 3,
          "total": 5
        },
        "registry_gap": "模板信号是关键词式的，对'可靠度标定 / 反问题'这类报告覆盖不足（据本份报告观察到，未做全库统计）：5 个信号里只有 governing equations 精确命中，收敛与精度证据只能算 partial。本包按结构性证据完成分类并如实登记该缺口，未据此改写 registry（超出本包范围）。",
        "downstream_note": "03 若沿用本 skill，其 extract-accuracy-statements 可直接吃表 2/表 6（loc-011/013），但须遵守 loc-024 的解读约束：本问题 FORM 精确，'FORM vs MC 差 3 %' 不能当作精度判据。"
      },
      "secondary_type_signals": {
        "report_type": "experimental-validation",
        "signal_match": [
          {
            "identify_signal": "baseline comparison",
            "matched": "exact",
            "locator_ids": [
              "loc-011",
              "loc-012",
              "loc-026"
            ],
            "note": "FORM 对闭式解析、重要性抽样、粗 MC 的多路对照表逐字在原文。"
          },
          {
            "identify_signal": "test matrix",
            "matched": "partial",
            "locator_ids": [
              "loc-020",
              "loc-021"
            ],
            "note": "有 9 对 ISO 表格 + 1 仓内锚点的算例矩阵，但不是试验/测量矩阵。"
          },
          {
            "identify_signal": "measurement uncertainty",
            "matched": "partial",
            "locator_ids": [
              "loc-033"
            ],
            "note": "有抽样统计的 1σ/95 % 覆盖判断，属蒙特卡洛统计不确定性，不是测量不确定度。"
          },
          {
            "identify_signal": "validation case",
            "matched": "partial",
            "locator_ids": [
              "loc-013"
            ],
            "note": "负控（置 ρ=0 重跑）是验证用算例，但不是物理标定试验。"
          },
          {
            "identify_signal": "facility",
            "matched": "absent",
            "locator_ids": [],
            "note": "纯数值研究，无试验设施，记为 absent。"
          }
        ],
        "use": "仅作标签层叠加（validation / negative-control 语义），不改变选中的 skill。"
      },
      "structural_segmentation": [
        {
          "segment_id": "seg-01",
          "heading": "# IN101-N09 — ISO 19906 ice-pressure partial-factor back-calibration at beta_T = 4.0 (mature: target-reliability inverse, FORM/IS/MC cross-checked)",
          "level": 1,
          "role": "title_and_machine_criteria",
          "char_start": 0,
          "char_end": 652,
          "line_start": 1,
          "line_end": 15,
          "chars": 652
        },
        {
          "segment_id": "seg-02",
          "heading": "## ① 案例介绍（物理背景 / 参数表）",
          "level": 2,
          "role": "context_and_parameters",
          "char_start": 652,
          "char_end": 1486,
          "line_start": 15,
          "line_end": 34,
          "chars": 834
        },
        {
          "segment_id": "seg-03",
          "heading": "## ② 怎么做的（方法 / 流程 / 工具链）",
          "level": 2,
          "role": "method_and_toolchain",
          "char_start": 1486,
          "char_end": 3009,
          "line_start": 34,
          "line_end": 47,
          "chars": 1523
        },
        {
          "segment_id": "seg-04",
          "heading": "## ③ 计算结果",
          "level": 2,
          "role": "numerical_results",
          "char_start": 3009,
          "char_end": 7553,
          "line_start": 47,
          "line_end": 139,
          "chars": 4544
        },
        {
          "segment_id": "seg-05",
          "heading": "## ④ 结果图",
          "level": 2,
          "role": "figures",
          "char_start": 7553,
          "char_end": 9265,
          "line_start": 139,
          "line_end": 165,
          "chars": 1712
        },
        {
          "segment_id": "seg-06",
          "heading": "## ⑤ 注意点（坑 / 局限 / 适用范围）",
          "level": 2,
          "role": "caveats_and_limitations",
          "char_start": 9265,
          "char_end": 10598,
          "line_start": 165,
          "line_end": 174,
          "chars": 1333
        },
        {
          "segment_id": "seg-07",
          "heading": "## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3 %）",
          "level": 2,
          "role": "error_verdict_vs_baseline",
          "char_start": 10598,
          "char_end": 11379,
          "line_start": 174,
          "line_end": 190,
          "chars": 781
        },
        {
          "segment_id": "seg-08",
          "heading": "## 审计链",
          "level": 2,
          "role": "provenance_and_audit_chain",
          "char_start": 11379,
          "char_end": 11824,
          "line_start": 190,
          "line_end": 196,
          "chars": 445
        }
      ],
      "claims": [
        {
          "id": "cls-9645-001",
          "claim_type": "classification",
          "status": "supported",
          "confidence": 0.85,
          "statement": "主型为 scientific-computation：以压力–面积幂律与控制方程组为骨架，输出数值结果表，并由脚本零手抄注入数字。",
          "locator_ids": [
            "loc-005",
            "loc-007",
            "loc-009",
            "loc-019",
            "loc-027",
            "loc-028"
          ]
        },
        {
          "id": "cls-9645-002",
          "claim_type": "classification",
          "status": "supported",
          "confidence": 0.9,
          "statement": "本报告是分项系数（设计格式）标定的反问题研究：目标 β_T=4.00，输出 (γ_f, ψ) 与 κ=γ_f·ψ，属'规范标定'子型而非一般数值算例。",
          "locator_ids": [
            "loc-002",
            "loc-006",
            "loc-008",
            "loc-009",
            "loc-019"
          ]
        },
        {
          "id": "cls-9645-003",
          "claim_type": "classification",
          "status": "supported",
          "confidence": 0.75,
          "statement": "报告具备验证型特征（多路基准对照 + 负控 + 1σ 覆盖判断），故把 experimental-validation 列为备选型（0.40）并叠加标签，但不据此改选 skill。",
          "locator_ids": [
            "loc-010",
            "loc-011",
            "loc-012",
            "loc-013",
            "loc-033"
          ]
        },
        {
          "id": "cls-9645-004",
          "claim_type": "classification",
          "status": "supported",
          "confidence": 0.7,
          "statement": "含算法实现成分（阻尼 Newton、包络定理 Jacobian、二分独立复核），但缺伪代码与复杂度陈述，不足以判为 algorithm-implementation。",
          "locator_ids": [
            "loc-008",
            "loc-014",
            "loc-015",
            "loc-016",
            "loc-018"
          ]
        },
        {
          "id": "cls-9645-005",
          "claim_type": "classification",
          "status": "supported",
          "confidence": 0.8,
          "statement": "不是 technical-proposal：交付物为已算出的结果表与机器判据汇总（5/5 通过），无计划/规格/roadmap 结构。",
          "locator_ids": [
            "loc-003",
            "loc-004",
            "loc-019",
            "loc-032"
          ]
        },
        {
          "id": "cls-9645-006",
          "claim_type": "classification",
          "status": "unresolved",
          "confidence": 0.6,
          "statement": "拒绝 software-engineering 的依据是'缺变更记录/接口变更'，属否定性证据，无法用逐字引文证明。",
          "locator_ids": [
            "loc-001",
            "loc-031"
          ],
          "unresolved_reason": "否定命题（原文未出现变更文件/commit/接口变更）不能由正向引文证实；按 do_not_invent_missing_information 保留为 unresolved，不冒充已证。"
        },
        {
          "id": "cls-9645-007",
          "claim_type": "classification",
          "status": "unresolved",
          "confidence": 0.65,
          "statement": "拒绝 literature-review 同样基于缺失（无 survey/相关工作节，仅一处二次文献引用）。",
          "locator_ids": [
            "loc-022"
          ],
          "unresolved_reason": "'不存在某结构'无法由单条引文证明；已用 loc-022 说明其唯一引用来源，但不宣称已完成引用密度核算。"
        },
        {
          "id": "cls-9645-008",
          "claim_type": "descriptive",
          "status": "supported",
          "confidence": 0.9,
          "statement": "与 ISO 表格比对的裁决依赖二次文献转录（source_tier=secondary, primary_source_verified=False），故相关标签与结论只能标 conditional；下游引用表值必须带此限定。",
          "locator_ids": [
            "loc-022",
            "loc-020"
          ]
        },
        {
          "id": "cls-9645-009",
          "claim_type": "descriptive",
          "status": "supported",
          "confidence": 0.95,
          "statement": "报告引用的图与结果 JSON 位于工作树外的绝对路径（/root/tp-agent/work/m8350/…），本工序无法在 worktree 内解析；按边界不改写、不登记资产，只在下游风险处挂账。",
          "locator_ids": [
            "loc-029",
            "loc-030"
          ]
        },
        {
          "id": "cls-9645-010",
          "claim_type": "descriptive",
          "status": "supported",
          "confidence": 0.9,
          "statement": "适用范围与约定限制由原文显式给出：单一年极值接触面积分布 + 单一幂律指数 + 抗力与冰力独立；且 κ 无约定而 γ_f/ψ 的劈分属约定，故跨来源比对只应以 κ 为准。",
          "locator_ids": [
            "loc-023",
            "loc-025"
          ]
        }
      ],
      "unresolved": [
        {
          "id": "unres-9645-001",
          "status": "unresolved",
          "item": "否定性分类标签（software-engineering / literature-review 的拒绝）",
          "reason": "'不存在'命题不可由逐字引文证明；保留为可反驳假设。",
          "related_claims": [
            "cls-9645-006",
            "cls-9645-007"
          ]
        },
        {
          "id": "unres-9645-002",
          "status": "unresolved",
          "item": "ISO 19906 Annex A 原始表值",
          "reason": "原文自述 A.2/A.3 为二次文献转录且 primary_source_verified=False（loc-022）；本工序不得回溯规范正文，也不得把表值当一手证据。",
          "related_claims": [
            "cls-9645-008"
          ]
        },
        {
          "id": "unres-9645-003",
          "status": "unresolved",
          "item": "报告图 1–6 与 in101_n09_results.json 的可达性",
          "reason": "引用路径指向 /root/tp-agent/work/m8350/（另一工作树），本包不应跨 worktree 取件（loc-029/030）。",
          "related_claims": [
            "cls-9645-009"
          ]
        }
      ],
      "constraints_compliance": {
        "every_claim_must_have_source_locator": true,
        "do_not_invent_missing_information": true,
        "preserve_uncertainty": true,
        "no_forced_claim_generation": true,
        "do_not_mark_claims_as_verified": true,
        "verified_flag_absent": true,
        "note": "全部 claim 的 status ∈ {supported, unresolved}；无 verified 字段，验证等级由平台门计算。"
      },
      "evidence_locators": [
        {
          "id": "loc-001",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**仓库** TensorPhysics ｜ **模块** `tensorphysics.ice_partial_factors`",
          "start_char": 149,
          "end_char": 214,
          "byte_start": 151,
          "byte_end": 226,
          "start_line": 3,
          "end_line": 3,
          "content_hash": "sha256:bc899cacb62ff7c0002602c52a13ff81a1b6907b90b704781e36e34dd7772780",
          "resolvable": true
        },
        {
          "id": "loc-002",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**目标** $\\beta_T$ = 4.00 ($P_f$ = 3.1671e-05)",
          "start_char": 281,
          "end_char": 325,
          "byte_start": 305,
          "byte_end": 353,
          "start_line": 3,
          "end_line": 3,
          "content_hash": "sha256:29525cc931657368c1426adc963f1cf6f71806901d110a74287e4bac3c3178bd",
          "resolvable": true
        },
        {
          "id": "loc-003",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "| `a_form_vs_simulation` | PASS |",
          "start_char": 424,
          "end_char": 457,
          "byte_start": 474,
          "byte_end": 507,
          "start_line": 7,
          "end_line": 7,
          "content_hash": "sha256:dd21609e457e828ef7dfd007c94494cbca6ce2334329c93ba9c7b1701c3530b4",
          "resolvable": true
        },
        {
          "id": "loc-004",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**判据汇总** 5/5 通过",
          "start_char": 635,
          "end_char": 650,
          "byte_start": 685,
          "byte_end": 712,
          "start_line": 13,
          "end_line": 13,
          "content_hash": "sha256:7a00af3138ccb4c325d6184c80b0ff8d498b79870f0f2cbdd28245cde0c97279",
          "resolvable": true
        },
        {
          "id": "loc-005",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "ISO 19906 用压力–面积关系描述冰载荷：作用于接触（或整体）面积 $A$ 上的冰压随面积下降，$p(A)=p_0(A/A_0)^{-ex}$。结构承受的冰力因此是 $F=k_F\\,p(A)\\,A$，而指数为负意味着**产生年极值冰力的冰压与面积负相关**：大面积伴随低压。本节点把「冰压年极值分布 → 抗力分布 → 极限状态」串成反问题，求设计格式 $\\gamma_f F_k \\le R_k/\\psi$ 的分项系数对 $(\\gamma_f,\\psi)$，使按该格式设计的构件恰好达到目标年可靠度 $\\beta_T = 4.0$。",
          "start_char": 675,
          "end_char": 944,
          "byte_start": 765,
          "byte_end": 1320,
          "start_line": 17,
          "end_line": 17,
          "content_hash": "sha256:b5763be94c8ac8e562e4dfa2de315d4868a4719e74418086606c481ecaf21efe",
          "resolvable": true
        },
        {
          "id": "loc-006",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "| 特征冰力 $F_k$ | 23.517 MN | 100 年超越（年超越概率 1e-2）|",
          "start_char": 1256,
          "end_char": 1303,
          "byte_start": 1797,
          "byte_end": 1872,
          "start_line": 28,
          "end_line": 28,
          "content_hash": "sha256:e7faca3b18a26d173be8dc0cbe77d0f33955ebde243828c4a38a756d88c0378f",
          "resolvable": true
        },
        {
          "id": "loc-007",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "| $ex$ | 0.400 | ISO 压力–面积指数 |",
          "start_char": 1011,
          "end_char": 1041,
          "byte_start": 1417,
          "byte_end": 1461,
          "start_line": 22,
          "end_line": 22,
          "content_hash": "sha256:93d5797fbe7404bbe047355f8a76df0faaa22f2120de3d3ae07e81b8ca4ad383",
          "resolvable": true
        },
        {
          "id": "loc-008",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "2. **反问题两方程两未知量**（`target_reliability_inverse.py`）。极限状态只通过 $\\kappa=\\gamma_f\\psi$ 依赖分项系数对（构件按 $R_k=\\kappa F_k$ 定尺），因此",
          "start_char": 1991,
          "end_char": 2107,
          "byte_start": 2954,
          "byte_end": 3144,
          "start_line": 37,
          "end_line": 37,
          "content_hash": "sha256:c6ed95dae734d9283cd916f1bec5a0d944010777c6239e1bb731c405135f96fe",
          "resolvable": true
        },
        {
          "id": "loc-009",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "$$F_1(\\gamma_f,\\psi)=\\beta(\\kappa)-\\beta_T=0,\\qquad F_2(\\gamma_f,\\psi)=\\gamma_f-F^*(\\kappa)/F_k=0$$",
          "start_char": 2109,
          "end_char": 2208,
          "byte_start": 3146,
          "byte_end": 3245,
          "start_line": 39,
          "end_line": 39,
          "content_hash": "sha256:4952ebe52966ec568bd61741b53c9da5c02a9623ae197db4caf6224ff1046bd5",
          "resolvable": true
        },
        {
          "id": "loc-010",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "3. **四条独立验证面**：(i) 设计点重要性抽样（$2\\times10^5$）；(ii) 粗 Monte Carlo （4e+06 样本，失败数 140）；(iii) 抗力解析积分的 Rao–Blackwell 化粗 MC（同一估计量、方差更小）；(iv) 闭式 $\\beta_{ln}$ 解析值。四者对照 FORM。",
          "start_char": 2476,
          "end_char": 2638,
          "byte_start": 3721,
          "byte_end": 4009,
          "start_line": 42,
          "end_line": 42,
          "content_hash": "sha256:394c5bcd75e56990e521c23473389b4d8ab426808ad526dca9ab597587956065",
          "resolvable": true
        },
        {
          "id": "loc-011",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**表 2 FORM 的四条独立验证（判据 a）**",
          "start_char": 3497,
          "end_char": 3523,
          "byte_start": 5255,
          "byte_end": 5305,
          "start_line": 66,
          "end_line": 66,
          "content_hash": "sha256:cdc1b26e72c5bac0191547cf24dac182dd2af7f5637f7523e51ff02b7576aa9a",
          "resolvable": true
        },
        {
          "id": "loc-012",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "| 闭式 $\\beta_{ln}$（解析）| 4.000000 | — | 6.46e-09 | — |",
          "start_char": 3642,
          "end_char": 3694,
          "byte_start": 5451,
          "byte_end": 5519,
          "start_line": 71,
          "end_line": 71,
          "content_hash": "sha256:6dea61b61f8c61e0e3edccf200fb894daa2d76360b3e45141191e058325e7bf2",
          "resolvable": true
        },
        {
          "id": "loc-013",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**表 6 负控（判据 e）：忽略 p–A 负相关**",
          "start_char": 6457,
          "end_char": 6484,
          "byte_start": 8665,
          "byte_end": 8720,
          "start_line": 111,
          "end_line": 111,
          "content_hash": "sha256:60f74748299a02a379a3c1442556f3e2516d04cdbaccd50ba3ba28bbd98eec03",
          "resolvable": true
        },
        {
          "id": "loc-014",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "| Newton 迭代数（三初值） | [7, 5, 5] |",
          "start_char": 3289,
          "end_char": 3320,
          "byte_start": 4977,
          "byte_end": 5024,
          "start_line": 60,
          "end_line": 60,
          "content_hash": "sha256:e07d254408d85307a3ccc555d8d7b529ae118b89bd649441646640de4abf9faf",
          "resolvable": true
        },
        {
          "id": "loc-015",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "| Jacobian 条件数 | 4.791 |",
          "start_char": 3355,
          "end_char": 3379,
          "byte_start": 5069,
          "byte_end": 5099,
          "start_line": 62,
          "end_line": 62,
          "content_hash": "sha256:de6e1728d615011bfd3a3e1de038d4a7bd281987ae896048eaaf48deb2be2d83",
          "resolvable": true
        },
        {
          "id": "loc-016",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**图 3.** Left: residual norm of the two-equation system from three dispersed starting points (quadratic convergence, same root). Right: the design-value split curve that makes the second equation non-degenerate.",
          "start_char": 8108,
          "end_char": 8319,
          "byte_start": 10500,
          "byte_end": 10713,
          "start_line": 149,
          "end_line": 149,
          "content_hash": "sha256:f45a2771a80fc1dc656deeae49e491ec7711f0e24e96f00750054aaaa0b7876c",
          "resolvable": true
        },
        {
          "id": "loc-017",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**表 8 模型参数敏感性 $\\partial\\beta/\\partial\\theta$（在 $\\kappa^*$ 处，中心差分）**",
          "start_char": 7244,
          "end_char": 7311,
          "byte_start": 9580,
          "byte_end": 9681,
          "start_line": 129,
          "end_line": 129,
          "content_hash": "sha256:920413a35fb482655094459cfcb01b6399d23be402c80e1ebb6ca1cbcf3b8f91",
          "resolvable": true
        },
        {
          "id": "loc-018",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "| 伴随 $\\partial\\beta/\\partial\\kappa$ | 中心差分 | -3.33e-07 | 是 |",
          "start_char": 10844,
          "end_char": 10904,
          "byte_start": 14585,
          "byte_end": 14659,
          "start_line": 181,
          "end_line": 181,
          "content_hash": "sha256:be3e704ffa672a7eb3e007e3b5da3a2a9a880a82cb5f3ca5e68112a7acab7b82",
          "resolvable": true
        },
        {
          "id": "loc-019",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**表 1 反问题解**",
          "start_char": 3020,
          "end_char": 3032,
          "byte_start": 4668,
          "byte_end": 4690,
          "start_line": 49,
          "end_line": 49,
          "content_hash": "sha256:7f2bb5529ff0e04e7f31a0594b7d8c0e976a4934c21946ef61ec9161d0dab32b",
          "resolvable": true
        },
        {
          "id": "loc-020",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**表 4 与 ISO 19906 表格分项系数偏差（判据 d）**",
          "start_char": 4247,
          "end_char": 4281,
          "byte_start": 6237,
          "byte_end": 6299,
          "start_line": 85,
          "end_line": 85,
          "content_hash": "sha256:6dbd8d5e269241e7fc098be1974545afa52c39d0796d99cfa430ca24abe8a76e",
          "resolvable": true
        },
        {
          "id": "loc-021",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "| ice_action_frequent x steel_plate_yielding | (1.00, 1.10) | 1.1000 | -30.41 % | +10.44 % | -23.15 % | 超差/不保守 | 3.1130 |",
          "start_char": 5172,
          "end_char": 5293,
          "byte_start": 7280,
          "byte_end": 7411,
          "start_line": 95,
          "end_line": 95,
          "content_hash": "sha256:0afa67952bac4b77bb1e823e74b5da5fadd13d14cc577e05f982a58826574e2d",
          "resolvable": true
        },
        {
          "id": "loc-022",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "5. **表格值出处受限**：ISO 19906 Annex A 正文不在工作树内，A.2/A.3 为二次文献转录（`source_tier=secondary`, `primary_source_verified=False`），由它得出的裁决一律 `conditional`；仓内锚点 (1.25, 1.15) 是全可验证的。偏差 >15 % 的行中 SLS（$\\gamma_F$=1.00）行按 ULS 目标 $\\beta_T$ 裁决属于口径错配，算例的物理含义是「若把使用极限状态的分项系数用到极值状态」，不是对规范的指摘。",
          "start_char": 10170,
          "end_char": 10436,
          "byte_start": 13433,
          "byte_end": 13913,
          "start_line": 171,
          "end_line": 171,
          "content_hash": "sha256:dcd1ea684b0815f538ea506099d176217bb79cd42032a0e9a848b21f468581b3",
          "resolvable": true
        },
        {
          "id": "loc-023",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "6. **适用范围**：年极值接触面积按对数正态建模、冰压遵循单一幂律指数（$ex$ 为常数）、抗力与冰力独立。参数敏感性见表 8：$\\partial\\beta/\\partial ex$ = +1.147 / 单位，即 $ex$ 每增加 0.1，$\\beta$ 约上升 0.11 —— 指数是仅次于压力散度的敏感方向。",
          "start_char": 10437,
          "end_char": 10596,
          "byte_start": 13914,
          "byte_end": 14235,
          "start_line": 172,
          "end_line": 172,
          "content_hash": "sha256:ed29154266351e2802172ce4959881a3feff8e45c46eacad72c47d48afff3e96",
          "resolvable": true
        },
        {
          "id": "loc-024",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "2. **该问题的 FORM 是精确的**：失效域 $\\{R<F\\}$ 在 $z=(\\ln x-\\mu)/\\sigma$ 坐标下是超平面，线性变换到 $u$ 空间仍是超平面，故 Hasofer–Lind 距离即真值。因此「FORM 与 MC 差 3 %」这类常规判据在此**不能**用来检验 FORM 的精度，只能检验实现的一致性——本节点如实按此解读（见判据 a 的 `criterion_interpretation`）。",
          "start_char": 9524,
          "end_char": 9737,
          "byte_start": 12200,
          "byte_end": 12601,
          "start_line": 168,
          "end_line": 168,
          "content_hash": "sha256:3a350fc256db05c3a72c59d81272745bd51451d1f3bc104eedfd1b783182dbfd",
          "resolvable": true
        },
        {
          "id": "loc-025",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "4. **分项系数对的唯一性依赖劈分约定**。$\\kappa$ 由达到目标可靠度唯一确定，但 $\\kappa$ 如何在 $\\gamma_f$ 与 $\\psi$ 之间劈分是约定；本节点采用 JCSS/ISO 2394 设计值劈分，于是 $\\psi^*$ = 0.9960 ≈ 1（5 % 分位特征抗力与设计点抗力几乎重合）。换成别的劈分约定会得到不同的 $\\gamma_f$/$\\psi$，但 $\\kappa^*$ 不变——与 ISO 表格比对时以 $\\kappa$ 为准（唯一无约定量），$\\gamma_f$/$\\psi$ 的逐项偏差仅作参考。",
          "start_char": 9897,
          "end_char": 10169,
          "byte_start": 12914,
          "byte_end": 13432,
          "start_line": 170,
          "end_line": 170,
          "content_hash": "sha256:2ecc30d3942707f9b51566d1a7a022e1b82f1e1de253c09c51b56ca6612828ff",
          "resolvable": true
        },
        {
          "id": "loc-026",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "**结论**：FORM 与解析值、重要性抽样的一致性远优于 3 %（均为 1e-2 % 量级）；反问题残差 1e-11；伴随导数与有限差分一致到 1e-7；唯一未达 3 % 量级的对照是**粗 MC 的统计噪声**（1σ 约 8 %，Rao–Blackwell 化后约 6 %，两者 95 % 带均覆盖 FORM），属采样误差而非模型误差，已在表 2 如实列出。",
          "start_char": 11196,
          "end_char": 11377,
          "byte_start": 15052,
          "byte_end": 15430,
          "start_line": 188,
          "end_line": 188,
          "content_hash": "sha256:0983f6889d4a658192da24b214c06be1f7cdd6862886050a6a639129632b79a2",
          "resolvable": true
        },
        {
          "id": "loc-027",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "纯 Python（`tensorphysics.structural` 的 FORM/SORM/IS/MC + Nataf）",
          "start_char": 2881,
          "end_char": 2943,
          "byte_start": 4461,
          "byte_end": 4531,
          "start_line": 45,
          "end_line": 45,
          "content_hash": "sha256:78bca60395082d6d914dd4d11ecb01f48bdee0d638a1bfcf6d5d73cf8065356d",
          "resolvable": true
        },
        {
          "id": "loc-028",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "所有数字由 `run_study()` 写入 JSON，报告文本从 JSON 注入（零手抄）",
          "start_char": 2960,
          "end_char": 3006,
          "byte_start": 4556,
          "byte_end": 4642,
          "start_line": 45,
          "end_line": 45,
          "content_hash": "sha256:69f654ac613a137a875ba4b3a79e14004d285da2dea162286d89df95c3ff2eef",
          "resolvable": true
        },
        {
          "id": "loc-029",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "![fig1](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig1_pa_joint.png)",
          "start_char": 7741,
          "end_char": 7827,
          "byte_start": 10131,
          "byte_end": 10217,
          "start_line": 143,
          "end_line": 143,
          "content_hash": "sha256:773a2a33b8c8a41e5cae200dbb073ebd6efa23088d46042459f452ba8957af6e",
          "resolvable": true
        },
        {
          "id": "loc-030",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "- 结果 JSON：`/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/in101_n09_results.json`（本报告所有数字的唯一来源，`run_study()` 直出）",
          "start_char": 11387,
          "end_char": 11512,
          "byte_start": 15446,
          "byte_end": 15611,
          "start_line": 192,
          "end_line": 192,
          "content_hash": "sha256:cdf4539535d2d3de74d9ae7481b3c3f87356cd158a7cfd16c319bbea8042cab9",
          "resolvable": true
        },
        {
          "id": "loc-031",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "- 复现：`PYTHONPATH=src python3 benchmarks/iso19906_partial_factors/run_in101_n09.py`",
          "start_char": 11741,
          "end_char": 11823,
          "byte_start": 15878,
          "byte_end": 15966,
          "start_line": 195,
          "end_line": 195,
          "content_hash": "sha256:d2f216d39de32633ba5d640db9f77144eabacbe988586fa734f290ebc5efec32",
          "resolvable": true
        },
        {
          "id": "loc-032",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "## ③ 计算结果",
          "start_char": 3009,
          "end_char": 3018,
          "byte_start": 4647,
          "byte_end": 4666,
          "start_line": 47,
          "end_line": 47,
          "content_hash": "sha256:725f569a39ae4b79e0c3d7f6f2747c2eb79f7fba7690c5cf38e8112f68cdf1c7",
          "resolvable": true
        },
        {
          "id": "loc-033",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "3. **±1σ 覆盖率是 68 % 检验**。粗 MC 本次得到 $P_f$=3.500e-05（失败数 140），估计偏高 1σ，1σ 带未覆盖 FORM，但 95 % 带覆盖；同一估计量的 Rao–Blackwell 化版本（抗力解析积分）方差小 10 倍以上，1σ 带覆盖。两者都写进 JSON，不择优隐匿。",
          "start_char": 9738,
          "end_char": 9896,
          "byte_start": 12602,
          "byte_end": 12913,
          "start_line": 169,
          "end_line": 169,
          "content_hash": "sha256:f3f09dc135f909edb7f1cda8507edc6c43eccda65f7800715266a8369fe177ff",
          "resolvable": true
        },
        {
          "id": "loc-034",
          "locator_type": "char_span_line",
          "field": "markdown",
          "quote": "1. **Nataf 吃物理相关、ISO 幂律给对数相关**。首版把 $\\rho_{\\ln p,\\ln A}$ 直接当物理相关系数传入，结果 FORM 与闭式解析值相差 3 %、而重要性抽样又站在 FORM 一边（两者差 0.07 %）——即「解析基准错了」而不是「FORM 错了」。改为对数正态精确关系反解 $\\rho_{phys}$ 后，回代 `rho0` 与目标对数相关一致到 1e-8，FORM 与解析值相对误差 6.5e-09。这是本节点最重要的一次自纠。",
          "start_char": 9290,
          "end_char": 9523,
          "byte_start": 11716,
          "byte_end": 12199,
          "start_line": 167,
          "end_line": 167,
          "content_hash": "sha256:74d2f23555838b74eb7e0bff10853a61baf0cd3fc82cdb3f954a006d1a462aef",
          "resolvable": true
        }
      ],
      "counts": {
        "evidence_locators": 34,
        "claims": 10,
        "claims_supported": 8,
        "claims_unresolved": 2,
        "unresolved_items": 3,
        "segments": 8,
        "topic_tags": 9
      }
    }
  }
}
```
