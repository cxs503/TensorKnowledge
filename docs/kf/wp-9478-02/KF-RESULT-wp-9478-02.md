# KF-RESULT wp-9478-02

**工序** `02-classification-parse` ｜ **报告** 9478 ｜ **源哈希** `sha256:133dbe58a74bd7549b66b2b86e5dc2e517f603c3ea65af45947d4cb5c1599e28` ｜ **主判类型** `scientific-computation` （confidence=medium）

一句话：报告 9478（FSI 强耦合 / Turek-Hron FSI-2 基准校验）被判为 `scientific-computation`，选中 skill `xsk-scientific-computation`；13 条分类/解析判定全部带可解析 locator（30/30 逐字命中，字符偏移精确），另有 8 条显式 unresolved。分类是**可反驳假设**，未标 verified。

## ① 本工序做了什么

只做**工序 02（分类解析）**：给报告 9478 打类型/主题标签并给出判定依据的原文片段定位，**不做知识抽取**（claims 全是分类/解析判定，不含报告的技术结论）。正文 144 行 / 5748 字符（UTF-8 5875 字节），切成 7 个二级章节、h3 标题 10 个、markdown 表 3 张、Figures 章节 4 条图注（名称位全空）。

**正文首行标题**（逐字）：`P153W2-N03: FSI Strong Coupling — Turek-Hron FSI-2 + Flutter + Energy Conservation`

注意：记录 metadata 的 title 含 `TensorFEM×TensorLBM`，正文 H1 不含——该差异见判定 `cls-9478-02-12` 与 `cls-9478-02-13`（含正文中两个 solver 名的出现次数），原文引文见 ④ 表。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源并先证哈希**：`GET /api/v1/tensor/reports/9478` 取 `markdown`，本地重算 UTF-8 字节 sha256 与契约比对，不一致即中止（不做任何写入）。`verify_result.py` 再**独立登录+重取一次**，用新取到的字节重算哈希并重解 locator，不复用缓存文件。
2. **结构切分**：正则识别 `#`~`######` 标题并算每个 span 的字符区间；markdown 表按连续 `|` 行聚合成 3 张；Figures 章节内编号项识别为图注，并检测名称位是否为空；Audit Chain 字段逐个解析出值/空值。
3. **类型判定（先定权重，后算分）**：候选=registry 六类 skill；三类证据加权——registry 关键词信号 ×1.0、`applies_to.sections` 命中 ×0.5（弱，因为 method/results 是通用标题）、语义锚点 ×2.0（弱锚 ×1.0）。缺失类锚点不参与计分，只记为 unresolved——「没有」无法用 locator 证明。
4. **零手抄的 locator**：每条证据的 `quote` 都是源码**行切片**（`lines[a-1:b]`），偏移/字节偏移/`content_hash` 全部由脚本算；写入前断言 `text[start:end] == quote`。
5. **自检 + 独立复核**：`generate_classification.py` 出 `checks.json`（验收逐条），`verify_result.py` 对交付 `kf_result.json` 跑 `schemas/kf_result.v1.schema.json` 并重解内嵌 locator。

**一键复跑**（工作树根执行）：

`bash docs/kf/wp-9478-02/repro.sh`

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `classification.json` | 工序 02 主工件：report_type=`scientific-computation`、selected_skill、13 claims / 30 evidence / 8 unresolved、结构切分、六类候选评分 |
| `checks.json` | 验收自检 8 条，hard-fail 项 全过 |
| `verify.json` | 独立复核 8 条（重取源、重解 locator、schema） |
| `kf_result.json` | 交付载荷（71006 字节），provenance.source_hash_matches=True |
| `classification_table.md` | 30 条证据的 quote/偏移/哈希定位表（即 ④） |
| `figures/fig1_structure_map.png` | 章节字符区间图（结构切分可核验） |
| `figures/fig2_candidate_scores.png` | 六类候选加权评分图（判定可复核） |
| `source/report_9478.md` + `source/record.json` | 源 markdown 与记录元数据（哈希钉住） |
| `scripts/*.py` + `repro.sh` | 取源/分类/复核/出报告，一键复跑 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

全部 30 条证据均满足：`text[start_offset:end_offset] == quote`（unicode 码点口径），并附 UTF-8 字节区间与 `sha256(quote)`；`verify_result.py` 用**重新取回**的字节复核。

**判定与对应原文（每条取首条引文；完整表见 `classification_table.md`）**

| claim | 类型 | 原文引文片段（逐字） | 证据数 |
|---|---|---|---|
| `cls-9478-02-01` | classification-decision |    - ω^{k+1} = -ω^k · (r^{k-1})^T · (r^k - r^{k-1}) / \|\|r^k - r^{k-1}\|\|² | 4 条 |
| `cls-9478-02-02` | classification-decision | The Turek-Hron FSI-2 benchmark (2006) is the gold standard for validating fluid-structure interaction solve… | 3 条 |
| `cls-9478-02-03` | classification-decision | \| Young's modulus E \| 1.3×10⁷ \| Pa \| | 3 条 |
| `cls-9478-02-04` | classification-decision | ### Reference Values (Turek & Hron 2006) | 2 条 |
| `cls-9478-02-05` | classification-decision | **C7: Interface Conservation** | 2 条 |
| `cls-9478-02-06` | parse-observation | ## 1. Case Introduction | 3 条 |
| `cls-9478-02-07` | parse-observation | 1. : Tip displacement and CL/CD time history ⏎ 2. : Energy conservation verification ⏎ 3. : Flutter analysi… | 2 条 |
| `cls-9478-02-08` | parse-observation | \| C3: CL/CD \| error ≤ 10% \| tracked \| ✅ PASS \| | 3 条 |
| `cls-9478-02-09` | parse-observation | - Computed: A = 53.07 mm ⏎ - Reference: A_ref = 50.0 mm ⏎ - Error: 6.13% ≤ 10% ✓ | 2 条 |
| `cls-9478-02-10` | parse-observation | \| Flutter U_cr (μ=10) \| 6.325 \| 6.325 \| <2% \| ✅ Yes \| | 2 条 |
| `cls-9478-02-11` | parse-observation | - Tests:  (38 tests, all pass) ⏎ - Full FSI suite: 162 tests, all pass | 1 条 |
| `cls-9478-02-12` | parse-observation | # P153W2-N03: FSI Strong Coupling — Turek-Hron FSI-2 + Flutter + Energy Conservation | 1 条 |
| `cls-9478-02-13` | parse-observation | 5. **Fluid Model**: Quasi-steady vortex shedding at Strouhal frequency St=0.16, with added mass and fluid d… | 2 条 |

<details><summary>完整 locator 表（claim/evidence → quote + 字符区间 + 哈希；点击展开）</summary>

| claim / evidence | quote (verbatim, line range) | char offsets | sha256(quote)[:16] |
|---|---|---|---|
| cls-9478-02-01<br>ev-9478-02-01 | `   - ω^{k+1} = -ω^k · (r^{k-1})^T · (r^k - r^{k-1}) / \|\|r^k - r^{k-1}\|\|²` | [1316,1388) (L34-34) | `fea4b1c6f7fb2189` |
| cls-9478-02-01<br>ev-9478-02-02 | `\| Young's modulus E \| 1.3×10⁷ \| Pa \|` | [678,714) (L16-16) | `18640f5f0f565aa8` |
| cls-9478-02-01<br>ev-9478-02-03 | `\| Frequency f [Hz] \| 3.0163 \| 3.0000 \| 0.54% \| ✅ Yes \|` | [5203,5257) (L131-131) | `95970ec4224c76ce` |
| cls-9478-02-01<br>ev-9478-02-04 | `- Frequency change from Δt=0.002 to Δt=0.001: 0.01% ≤ 3% ✓` | [3643,3701) (L93-93) | `7be985724b3b5909` |
| cls-9478-02-02<br>ev-9478-02-05 | `The Turek-Hron FSI-2 benchmark (2006) is the gold standard for validating fluid-structure interaction solvers. It involves a 2D laminar channel flow (Re≈100) past a rigid cylinder with an elastic beam attached to its trailing edge. The beam undergoes vortex-induced vibration (VIV) due to periodic vortex shedding from the cylinder.` | [136,468) (L7-7) | `90423b28024ffb0c` |
| cls-9478-02-02<br>ev-9478-02-06 | `\| C1: Frequency \| error ≤ 5% \| 0.54% \| ✅ PASS \|` | [2552,2599) (L61-61) | `4d15600c5a02c78a` |
| cls-9478-02-02<br>ev-9478-02-07 | `We implement a partitioned Dirichlet-Neumann coupling with:` | [1090,1149) (L31-31) | `d919ef0d6f057cec` |
| cls-9478-02-03<br>ev-9478-02-08 | `\| Young's modulus E \| 1.3×10⁷ \| Pa \|` | [678,714) (L16-16) | `18640f5f0f565aa8` |
| cls-9478-02-03<br>ev-9478-02-09 | `\| Frequency f [Hz] \| 3.0163 \| 3.0000 \| 0.54% \| ✅ Yes \|` | [5203,5257) (L131-131) | `95970ec4224c76ce` |
| cls-9478-02-03<br>ev-9478-02-10 | `3. **Single-mode approximation**: Only the first bending mode is considered. Higher modes may be important for some FSI problems.` | [4528,4657) (L113-113) | `c9daf04509e36f3e` |
| cls-9478-02-04<br>ev-9478-02-11 | `### Reference Values (Turek & Hron 2006)` | [855,895) (L22-22) | `de42687ff53f6521` |
| cls-9478-02-04<br>ev-9478-02-12 | `Theodorsen (1935) analytical solution for 2-DOF typical section (plunge + pitch):` | [2145,2226) (L50-50) | `908d2a3ca5ad6e8e` |
| cls-9478-02-05<br>ev-9478-02-13 | `**C7: Interface Conservation**` | [3757,3787) (L96-96) | `ef45fcaca2ca8bf4` |
| cls-9478-02-05<br>ev-9478-02-14 | `- Code: <br>- Tests:  (38 tests, all pass)<br>- Full FSI suite: 162 tests, all pass<br>- Figures: ` | [5658,5747) (L140-143) | `cafd93ff81351817` |
| cls-9478-02-06<br>ev-9478-02-15 | `## 1. Case Introduction` | [87,110) (L4-4) | `ac5670ab730f4d4e` |
| cls-9478-02-06<br>ev-9478-02-16 | `## 6. Error Assessment` | [5077,5099) (L127-127) | `0a03a738c694e464` |
| cls-9478-02-06<br>ev-9478-02-17 | `## Audit Chain` | [5643,5657) (L139-139) | `a1324df931ce8a01` |
| cls-9478-02-07<br>ev-9478-02-18 | `1. : Tip displacement and CL/CD time history<br>2. : Energy conservation verification<br>3. : Flutter analysis (U_cr vs μ, growth rate vs U)<br>4. : Time-step convergence study` | [3934,4101) (L103-106) | `ec74d5d17c0a321d` |
| cls-9478-02-07<br>ev-9478-02-19 | `- Code: <br>- Tests:  (38 tests, all pass)<br>- Full FSI suite: 162 tests, all pass<br>- Figures: ` | [5658,5747) (L140-143) | `cafd93ff81351817` |
| cls-9478-02-08<br>ev-9478-02-20 | `\| C3: CL/CD \| error ≤ 10% \| tracked \| ✅ PASS \|` | [2649,2695) (L63-63) | `6c5f47e5baab415b` |
| cls-9478-02-08<br>ev-9478-02-21 | `\| C4: Flutter \| error ≤ 8% \| <2% \| ✅ PASS \|` | [2696,2739) (L64-64) | `0032429f7eae9547` |
| cls-9478-02-08<br>ev-9478-02-22 | `\| C8: Honest FAIL \| root cause \| all pass \| ✅ PASS \|` | [2888,2940) (L68-68) | `3cf8bfd22923aa3e` |
| cls-9478-02-09<br>ev-9478-02-23 | `- Computed: A = 53.07 mm<br>- Reference: A_ref = 50.0 mm<br>- Error: 6.13% ≤ 10% ✓` | [3080,3156) (L78-80) | `004ecdaf9b1fa496` |
| cls-9478-02-09<br>ev-9478-02-24 | `- Amplitude change: 6.07% (within 10% soft tolerance)` | [3702,3755) (L94-94) | `19dccf1a0248915a` |
| cls-9478-02-10<br>ev-9478-02-25 | `\| Flutter U_cr (μ=10) \| 6.325 \| 6.325 \| <2% \| ✅ Yes \|` | [5320,5373) (L133-133) | `8fa15f714b99ae2d` |
| cls-9478-02-10<br>ev-9478-02-26 | `- For μ=10: U_cr = 6.325 (reference), numerical match within 2%` | [3255,3318) (L84-84) | `7b502b51fcd79227` |
| cls-9478-02-11<br>ev-9478-02-27 | `- Tests:  (38 tests, all pass)<br>- Full FSI suite: 162 tests, all pass` | [5667,5735) (L141-142) | `07ae070b00bfa3a2` |
| cls-9478-02-12<br>ev-9478-02-28 | `# P153W2-N03: FSI Strong Coupling — Turek-Hron FSI-2 + Flutter + Energy Conservation` | [1,85) (L2-2) | `77df46ad49dfeeb1` |
| cls-9478-02-13<br>ev-9478-02-29 | `5. **Fluid Model**: Quasi-steady vortex shedding at Strouhal frequency St=0.16, with added mass and fluid damping effects.` | [2000,2122) (L47-47) | `5f9765a8396d9c1a` |
| cls-9478-02-13<br>ev-9478-02-30 | `- Full Navier-Stokes fluid solver (TensorLBM integration)` | [4926,4983) (L122-122) | `b8a9f443d67d56a8` |

</details>

## ⑤ 注意点与局限（踩过的坑）

1. **类型边界是假设，不是事实**：主判 `scientific-computation` 12.0 分 vs 次高 `algorithm-implementation` 4.5 分；领先主要来自本包自设的语义锚点（存在自我实现风险），故 confidence 只给 medium，`experimental-validation`（基准校验语义）保留为竞争假设。
2. **关键词信号几乎全军覆没**：registry 的 identify_signals 是实验室/工程语汇（facility、measurement uncertainty、commit…），本报告是数值计算报告，字面命中仅 `convergence study`（scientific-computation）与 `interface`（software-engineering，而此处指 FSI 界面）。纯关键词分类会判错，必须补语义锚点。
3. **通用章节名会灌水**：`method`/`results`/`limitations` 几乎任何报告都有，故章节命中权重压到 0.5；若不压，`technical-proposal` 会凭空升到与真候选同级。
4. **报告本体的可核验性缺口**（本工序只记录、不代修）：Figures 章节 4 条图注名称位全空、正文无内嵌图、记录 metadata 有 4 条具名图，而正文图注名称位全空、正文出现 'fsi2' 0 次；Audit Chain 的 Code/Figures 两行为空；测试规模只有文字断言。
5. **验收表里有无数值的 PASS**：C3 计算列写 `tracked` 却标 PASS，C4/C5 只给不等式，C8（Honest FAIL 条目）也标 PASS —— PASS 并非处处由数值支撑。
6. **表内算术轻微不一致**：C2 幅度误差记 6.13%，按报告自身数值复算为 6.14%；C6 又写幅度变化 6.07%。本工序只复算，不判定哪一值为真。
7. **Flutter 项自我比较**：计算列与参考列同为 6.325 却标 `<2%`，表内无两者之差，该误差无表内证据。
8. **无 ground truth**：没有任何平台侧标注告诉我们 9478 的『真类型』，因此类型判定的正确率不可测（见 unresolved `unres-9478-02-U7`）；只能说判定规则可复现、依据可定位。

**显式 unresolved（不猜、不补）**

| id | 关于 | 为什么无法定位 |
|---|---|---|
| `unres-9478-02-U1` | experimental-validation 缺失锚点 | 设施/测量不确定度/重复试验三类锚点是负向发现，locator 只能证明'有'，无法证明'无'；仅记录为全文检索 0 命中的负向发现，不作可定位断言。 |
| `unres-9478-02-U2` | 测试规模断言（38 / 162 tests） | 报告未给命令/链接/提交号，工序 02 不访问代码仓，故不可核验。 |
| `unres-9478-02-U3` | 图注 ↔ 图文件绑定 | 正文 4 条图注名称位为空、正文 'fsi2' 出现 0 次；记录 metadata 有 4 条具名图。两者只能按出现顺序对齐，本工序不建立未经原文支持的绑定，也不对图像内容作断言。 |
| `unres-9478-02-U4` | C3（CL/CD）数值缺失 | 报告只写 'tracked'，未给数值；工序 02 不做抽取，交 03 工序判定是否可抽取。 |
| `unres-9478-02-U5` | algorithm-implementation 缺失锚点 | 伪代码/复杂度/函数签名均为负向发现，无法用 locator 证明缺失。 |
| `unres-9478-02-U6` | 参照值的外部正确性 | 报告把 f_ref=3.0 Hz、A_ref=0.05 m 等归因于 Turek & Hron (2006)，工序 02 不核对外部文献（超出本工序范围且禁止凭记忆断言），仅按原文记录。 |
| `unres-9478-02-U7` | report_type 无 ground truth | 平台未给报告 9478 的类型标注，本工序也不读其它工序结论，因此类型判定正确率不可测；只能声明规则可复现、依据可定位。 |
| `unres-9478-02-U8` | 记录 summary 的『all 8 criteria verified』措辞 | 记录 summary 出现 'verified' 字样，但正文 C3 只写 'tracked'（无计算值），该措辞在正文中找不到数值支撑；summary 属平台元数据，无法用 markdown locator 定位，本工序既不采信也不改写，仅登记差异。 |

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 勾/叉 | 依据 |
|---|---|---|
| valid_json | ✅ | classification.json / checks.json parsed by json.load |
| schema_pass | ➖ | no classification schema exists in schemas/ (only kf_result.v1.schema.json, validated against the delivered result by verify_result.py); structural shape checks below stand in |
| source_locator_resolvable | ✅ | 30/30 locators resolve byte-exactly at declared char offsets; failing=[] |
| source_hash_matches | ✅ | recomputed sha256:133dbe58a74bd7549b66b2b86e5dc2e517f603c3ea65af45947d4cb5c1599e28 |
| no_duplicate_ids | ✅ | 51 ids across claims/evidence/unresolved; duplicates=[] |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | 13 claims, each with >=1 resolvable quote; 8 records explicitly unresolved; missing=[] |
| do_not_mark_claims_as_verified | ✅ | every claim is draft/unassessed |
| chars_match_contract | ✅ | chars=5748 |

独立复核（`verify_result.py`，重取源+重解 locator+schema）：8/8 通过。

**误差判定（逐项给出基准与是否 <3%）**

| 量 | 本包结果 | 基准 | 偏差 | 是否 <3%？ |
|---|---|---|---|---|
| 源 markdown 哈希 | sha256:133dbe58a74bd7549b66b2b86e5dc2e517f603c3ea65af45947d4cb5c1599e28 | 契约声明 hash | 0（逐字节相等） | ✅ 是 |
| locator 逐字命中 | 30/30 | 全部证据 | 0 条失配 | ✅ 是 |
| locator 越界/哈希自洽 | 0 失配 | content_hash = sha256(quote) | 0 | ✅ 是 |
| C2 幅度误差（报告正文 vs 本包复算） | 6.13%（原文） | 6.14%（(53.07−50.0)/50.0） | 0.16% | ✅ 是 |
| report_type 判定准确率 | 判定=scientific-computation | **无 ground truth** | 不可计算 | ➖ 无基准，声明原因 |

结论：可量化的三项（哈希、locator 命中、正文算术复算）偏差均在 <3% 内且哈希/命中为精确相等；`report_type` 正确率**无基准可对**（平台未给该报告的类型标注，本工序也未获准读其它工序结论），故如实记 NOT_MEASURED，不写成『通过』。

**图件说明**：本工序是纯文书分类任务，没有物理场量，因此不给场量云图；改用两张可核验工件图（结构切分字符区间图、六类候选加权评分图），数值全部来自 `classification.json`。
