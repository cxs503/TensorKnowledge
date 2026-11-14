# KF-RESULT wp-9265-02 · report 9265 分类解析（02-classification-parse）

> 本报告是工序结果信道：正文里**只有一个 json 围栏代码块**，即 KF-RESULT v1 结果信封原样提交。结论一律 `draft`，**不标 verified**（verification 由平台门计算）。
>
> 修订：v2 把产物落点由工作区 `artifacts/`（被仓库 `.gitignore` 忽略、不随分支提交）改为随仓库提交的 `docs/kf/wp-9265-02/`；分类结论、定位与哈希均未变，仅路径与图名对齐。

## ① 本工序做了什么（案例介绍 / 物理与文档背景）

只处理 `report_id=9265`（`tensor://reports/9265`，字段 `markdown`，场景 `dp_capability_assessment`），只做 02 工序的两件事：**给报告打类型/主题标签** + **结构切分（parse）**，并给出每条判定的**逐字原文定位**。不做资产登记（`objective.register_assets=false`）、不做知识抽取（无 claims）、不改写上游产物、不跨报告。

报告主题（原文自述，非本人概括）：「DP（dynamic positioning）系统靠推进器合成力/力矩抵消风、浪、流载荷，在无锚条件下保持船位与艏向。」

| 项目 | 值 |
|---|---|
| report_id | `9265` |
| 源 URI / 字段 | `tensor://reports/9265` / `markdown` |
| 标题 | DP 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图（IN144-N05 / m7890） |
| 字符数（UTF-8 解码后） | 9599（契约声明 9599，一致） |
| 字节数 | 15943 |
| sha256（本工序独立复算） | `sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c` |
| 契约声明哈希 | `sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c` |
| 哈希一致 | `true` |
| 上游产线标识 | 节点 IN144-N05 / 仓库 `ship-performance-platform` / 分支 `agent/m7890` |
| 研究对象（原文） | 「本节点评估一艘典型 **DP-2 海工供应船（PSV, UT-755 级）** 的 DP 能力」；主尺度 「| LOA × B × T | 76.5 × 18.6 × 6.3 m | `reference_psv()` |」 |

**一句话结果**：主型 `scientific-computation`（confidence=medium，可反驳假设），副型 `algorithm-implementation`, `software-engineering`；排除 `experimental-validation`, `literature-review`, `technical-proposal`；选中 skill `xsk-scientific-computation`；7 个主题标签、20 条逐字定位、13 个结构段全部可解析。

## ② 怎么做的（方法 / 流程 / 关键设置 / 工具链）

1. **取源（不许凭记忆）**：`GET $TENSOR_API_BASE/tensor/reports/9265`（Bearer 登录 token），取 `markdown` 字段，原始字节落 `docs/kf/wp-9265-02/report_9265.md`；**不用平台算好的哈希**，本工序自己 `hashlib.sha256(bytes)` 复算。
2. **哈希门**：复算值与契约 `source_hash` 比对，同时比对 `chars=9599`；不一致则脚本直接退出、不产出 （`raise SystemExit`）。
3. **结构切分（parse）**：按 ATX 标题正则 `^#{1,6}\s` 切段，记 `start_offset/end_offset/chars/body_lines/tables/code_blocks`；断言首段从 0 开始、末段到 `len(text)`、相邻段无缝隙无重叠、段长求和等于全文长度。
4. **类型判定**：读 `extraction-skills/registry.json` 的六分型与各 skill 的 `identify_signals`；先做**字面命中**统计（如实记录，见 ④ 表），再以**中文语义证据**（逐字定位）为主判定，并把“为何不是其它型”也写成带定位的排除理由。分类显式标成 `classification_is_hypothesis=true`，`unclassified` 为合法值但本次未触发。
5. **零手抄定位器**：每条判定用 `_loc(id, supports, quote)` → `str.find(quote)` 得到字符偏移；取不到就抛错。落盘前再断言 `text[start:end] == quote`、`content_hash == sha256(quote)`、id 唯一。
6. **工具链**：Python 3.11 / `hashlib` / `json` / `re` / `urllib`（仅标准库取源）+ matplotlib（图）。脚本：`scripts/kf/build_classification_9265_02.py`（产物）、`scripts/kf/emit_wp9265_02_report.py`（本报告）、`tests/test_wp9265_02_classification.py`（验收门复算）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9265-02/classification.json` | 工序产物本体：`report_type=scientific-computation`、2 个副型、3 个排除型、7 个主题标签、20 条逐字定位、13 段结构切分、4 条显式不确定项 |
| `docs/kf/wp-9265-02/kf_result.json` | KF-RESULT v1 信封（`package_id/task_type/report_id/provenance/outputs`），即正文唯一 json 块的内容 |
| `docs/kf/wp-9265-02/report_9265.md` | 源原文快照（9599 字符），离线复跑与定位复算用 |
| `docs/kf/wp-9265-02/fig_locator_map.png` | 图 1：证据定位在原文坐标上的分布（按 topic/type/exclude/provenance 着色） |
| `docs/kf/wp-9265-02/classification_figure.png` | 图 2：结构切分段长 + registry 信号覆盖（字面 vs 语义） |
| `scripts/kf/build_classification_9265_02.py` | 一键生成 `classification.json` + `kf_result.json` + 图 2 |
| `scripts/kf/emit_wp9265_02_report.py` | 生成本报告 + 递交载荷（含 png_base64） |
| `tests/test_wp9265_02_classification.py` | 11 项验收门复算（哈希/定位/唯一性/结构覆盖/类型合法性/工序边界） |

**结构切分（parse 结果，程序化）**：

| # | level | 标题（截断） | chars | 表格行 | 代码块 |
|---|---|---|---|---|---|
| 0 | H1 | 动力定位 (DP) 系统能力评估：推力分配 QP × 环境力平衡 ×… | 352 | 0 | 0 |
| 1 | H2 | ① 案例介绍（物理背景 / 几何 / 参数表） | 1146 | 16 | 0 |
| 2 | H2 | ② 怎么做的（方法 / 流程 / 关键设置 / 工具链） | 1893 | 0 | 1 |
| 3 | H2 | ③ 计算结果（数字表，程序注入） | 21 | 0 | 0 |
| 4 | H3 | 3.1 10 个工况点的 3-DOF 平衡（判据：残差 ≤1%） | 816 | 12 | 0 |
| 5 | H3 | 3.2 操作包线（可用推力 0.6 × 装机，Hs 3 m / Tp… | 569 | 4 | 0 |
| 6 | H3 | 3.3 单推力器失效能力降级（DP-2 最坏单点失效，1 kn=0.… | 619 | 6 | 0 |
| 7 | H3 | 3.4 QP 数值性质 | 607 | 8 | 0 |
| 8 | H3 | 3.5 图 | 278 | 0 | 0 |
| 9 | H2 | ④ 与 DNV 规范的对照（定性） | 616 | 9 | 0 |
| 10 | H2 | ⑤ 注意点（踩坑 / 局限 / 适用范围） | 1086 | 0 | 0 |
| 11 | H2 | ⑥ 误差判定（逐项，显式回答"是否 <3%"） | 1195 | 15 | 0 |
| 12 | H3 | 复现 | 401 | 0 | 1 |

报告自报的六段章节（①②③④⑤⑥）在切分中全部命中：`true`，映射 {'①': 1, '②': 2, '③': 3, '④': 9, '⑤': 10, '⑥': 11}。

## ④ 证据定位表（判定 → 原文逐字引文 + 字符偏移）

每条判定挂的引文都能在 `docs/kf/wp-9265-02/report_9265.md` 的对应偏移逐字取出；`content_hash` 是引文自身的 sha256（平台可独立重算）。表内引文原样保留报告里的 Markdown 记号与 `−`(U+2212) 等字符。

| id | 支持的判定 | 偏移 [start,end) | content_hash（前 16 位） | 原文引文（逐字） |
|---|---|---|---|---|
| `L01-domain-dp-definition` | `topic.domain` | 380–439 | `16ef8754a902739f` | DP（dynamic positioning）系统靠推进器合成力/力矩抵消风、浪、流载荷，在无锚条件下保持船位与艏向。 |
| `L02-vessel-type-psv` | `topic.vessel_type` | 440–487 | `feaaca2b8f1f63f9` | 本节点评估一艘典型 **DP-2 海工供应船（PSV, UT-755 级）** 的 DP 能力 |
| `L03-main-dimensions` | `topic.geometry` | 612–669 | `9ff7dd49520f55e9` | \| LOA × B × T \| 76.5 × 18.6 × 6.3 m \| `reference_psv()` \| |
| `L04-campaign-node-branch` | `provenance.campaign` | 44–118 | `47f54e0dde418073` | **战役节点** IN144-N05 ｜ **仓库** ship-performance-platform ｜ **分支** agent/m7890 |
| `L10-numerical-kernel-modules` | `type.software-engineering` | 119–214 | `e2685b0203c224f6` | **落库模块** `backend/physics/dp_core.py`（物理/数值内核）、`backend/api/dynamic_positioning.py`（FastAPI 端点） |
| `L11-test-suite` | `type.software-engineering` | 215–272 | `c2acc07e40d97e3b` | **验证** `tests/test_dp_capability.py`（40 项 pytest，22 s 全绿） |
| `L12-governing-laws` | `type.scientific-computation` | 1592–1653 | `eba21c9b1d603c07` | 螺旋桨定律 `T = ρD⁴K_Tn²`、`P = 2πρD⁵K_Qn³` ⇒ 消去转速得 **`T ∝ P^{2/3}` |
| `L13-layered-physics-model` | `type.scientific-computation` | 1852–1864 | `a803b6cc1f51bfd9` | **L2 环境力模型** |
| `L14-optimisation-problem` | `type.algorithm-implementation` | 2520–2564 | `a04f996db40f4472` | min_e  Σ (w_i (e_i − r_i)²)        (二次型, 良态) |
| `L15-solver-iterations` | `type.scientific-computation` | 5581–5614 | `d79ef54b2924d56a` | \| 受约束（0.5× 推力）工况 QP 迭代数 \| 最大 29 \| |
| `L16-two-level-loops` | `type.algorithm-implementation` | 3085–3112 | `a4a0f16583a74eee` | **对风速二分**（容差 5e-3 m/s）求可行上界 |
| `L17-error-table` | `type.scientific-computation` | 8435–8480 | `96e3258f028efdf8` | \| QP 解 vs KKT 闭式解 \| 解析 \| 7.1e-15 kN \| **是** \| |
| `L18-regulation-comparison` | `type.scientific-computation` | 6301–6321 | `6f105aa7d32e51be` | ## ④ 与 DNV 规范的对照（定性） |
| `L19-failure-analysis` | `topic.dp2-redundancy` | 4797–4845 | `c4165be0dfa16500` | ### 3.3 单推力器失效能力降级（DP-2 最坏单点失效，1 kn=0.5 m/s 共线流） |
| `L20-figures` | `type.scientific-computation` | 6064–6116 | `547f0a7e58d65ac0` | `capability_polar.png` — 极坐标操作包线图（5 条等电流曲线 + 最坏失效虚线） |
| `L21-repro-commands` | `type.software-engineering` | 9214–9289 | `226770a5606ada69` | python3 -m pytest tests/test_dp_capability.py -q          # 40 passed, 22 s |
| `L30-no-referenced-benchmark` | `exclude.experimental-validation` | 7593–7648 | `f7820b6c94c8f356` | 仓库内没有风洞、模型试验或 OCIMF/Isherwood 回归表可对标 ⇒ **数值层 WITHHELD** |
| `L31-withheld-numeric-layer` | `exclude.experimental-validation` | 8656–8675 | `fe665da9db83b7d0` | **无基准，声明 WITHHELD** |
| `L32-static-3dof-limitation` | `exclude.dynamic-simulation` | 7472–7523 | `3d0a4d0f469d362a` | - 静力 3-DOF：无低频/波频动态、无控制器、无瞬态与推力器再分配过程（只用速率限做静态可行性）。 |
| `L33-no-published-envelope-data` | `exclude.literature-review` | 6323–6378 | `10d2f05a1cb747ca` | 仓库内没有可引用的 DNV 已发表包线数值数据集，故**只做方法与定性特征对照**（数值层 WITHHELD） |

**信号覆盖（registry `identify_signals` 是英文关键词，报告是中文正文）**：

| skill_id | 对应 report_type | 字面命中总数 | 语义定位证据数 | skill 生命周期 |
|---|---|---|---|---|
| `xsk-literature-review` | literature-review | 0 | 0 | template-created |
| `xsk-scientific-computation` | scientific-computation | 0 | 6 | template-created |
| `xsk-algorithm-implementation` | algorithm-implementation | 0 | 2 | template-created |
| `xsk-software-engineering` | software-engineering | 5 | 3 | template-created |
| `xsk-technical-proposal` | technical-proposal | 0 | 0 | template-created |
| `xsk-experimental-validation` | experimental-validation | 0 | 0 | template-created |

其中 `xsk-software-engineering` 的 5 次字面命中全部来自同一个 ASCII 子串 `api`：3 次在 `FastAPI`、1 次在 `backend/api/`、1 次在 URL 路径 `api/v1/`，属噪声命中而非证据；这说明**字面关键词匹配在中文报告上不可用**，本工序因此以语义证据为主 （方法学局限见 ⑤-1）。

**主题标签（每条挂定位）**：

- `dynamic-positioning-capability` ← `L01-domain-dp-definition`
- `thrust-allocation-qp` ← `L14-optimisation-problem`
- `environmental-loads-wind-current-wave-drift` ← `L13-layered-physics-model`
- `operability-envelope-polar` ← `L20-figures`
- `dp2-single-point-failure-redundancy` ← `L19-failure-analysis`
- `dnv-st-0111-classification-comparison` ← `L18-regulation-comparison`
- `static-3dof-conservative-scope` ← `L32-static-3dof-limitation`

## ⑤ 注意点与局限（踩坑 / 适用范围）

1. **registry 信号是英文、报告是中文**：`identify_signals` 六型全部为英文关键词（`governing equations`/`pseudocode`/`changed files`…），中文正文几乎不字面命中（主型命中数 0）。若按字面命中打分会把本报告判成 `unclassified`——本工序选择“语义证据 + 逐字定位 + 显式置信度”，并把字面命中如实留档，供下游反驳。
2. **分类是可反驳假设，不是事实**：`report_type_confidence=medium`；主型与副型共享同一批数值证据（QP 是实现层，物理与环境载荷才是报告主体），换一个读者完全可能把主副型对调。错分会在 03/04 工序以“claim 与原文类型不符”暴露。
3. **registry 全部 skill 仍是 `template-created`**：所选 skill 的步骤只是骨架，尚无代表报告跑通全流程，03 工序不应把它当作已校验的方法学。
4. **只做定位，不下数值结论**：报告自述数值层 WITHHELD（无风洞/模型试验/回归表对标），本工序不碰任何数值判断，也不把其自述结论升级为知识。
5. **不补缺失信息**：研究对象是 `reference_psv()` 工程模型船，是否对应某实船、是否有人工标注的分类ground truth，原文都没有 → 记为 `unresolved`，不猜。
6. **图**：本工序是纯文档/解析工序，没有物理场量 → **不产场量云图**（无场可画，如实说明）；改出两张**可程序化复算**的诊断图：证据定位坐标分布（图 1）与结构/信号覆盖（图 2）。
7. **只碰 report 9265**：脚本硬编码 `report_id=9265` 与契约哈希，读到不一致立即退出；不读写其它 report_id，不改上游产物。

## ⑥ 自检（逐条对照 acceptance，honest 记录）

| acceptance 项 | 判定 | 依据 |
|---|---|---|
| `valid_json` | ✅ | `json.loads` 通过（`classification.json` 与 `kf_result.json`），`tests/test_wp9265_02_classification.py::test_valid_json` |
| `schema_pass` | ✅ | 手工核 `schemas/kf_result.v1.schema.json` 的 required / additionalProperties / enum / pattern（未引入 jsonschema 依赖，逐键比对 `test_schema_pass`） |
| `source_locator_resolvable` | ✅ | 20/20 条引文在原文偏移处逐字相等（`test_source_locator_resolvable` + `test_locator_content_hash`） |
| `source_hash_matches` | ✅ | 独立复算 `sha256:d2ab3780127b…` 与契约一致（`test_source_hash_matches`） |
| `no_duplicate_ids` | ✅ | 20 条定位 id、7 个标签、13 个结构段均唯一（`test_no_duplicate_ids`） |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅（本包无 claims） | 本工序不产 claims；**每条分类/主题判断**都挂可解析定位，不确定项显式标 `hypothesis/withheld_by_source/declared_limitation/unresolved`，且无悬空、无未引用的注入式证据（`test_every_judgement_has_evidence_or_explicit_unresolved`） |
| 额外：结构切分覆盖全文 | ✅ | 首段从 0、末段到 `len(text)`、无缝隙无重叠、段长求和 = 全文长度（`test_structure_parse_covers_whole_body`） |
| 额外：类型合法 + skill 与类型一致 | ✅ | `report_type` ∈ registry 六分型，`xsk-scientific-computation.report_type == scientific-computation`（`test_report_type_is_legal_and_skill_matches`） |
| 额外：工序边界 | ✅ | `outputs` 只有 `classification.json`；无 claims；未标 verified（`test_no_claims_extracted_and_not_verified`） |
| 额外：report_id 不越界 | ✅ | 全部引用 `9265` / `tensor://reports/9265`（`test_only_touches_report_9265`） |

失败项：**无**（11/11 通过）。但需如实说明两处**已知不确定**（非失败）：分类置信度只有 medium；registry 信号字面命中在中文正文上不可用，判定依赖人工语义映射——两者都写进了产物字段，可被下游反驳。

## ⑦ 误差判定（关键量 vs 基准，逐项回答“是否 <3%”）

本工序的可核量都能用**精确相等**（误差 0）判定，不需要 3% 容差；唯一不可核的是“分类本身对不对”。

| 关键量 | 基准 | 实测误差 | <3%？ |
|---|---|---|---|
| 源 markdown sha256 | 契约声明 `sha256:d2ab3780127bff47…` | 0（逐位相等） | **是**（精确） |
| 字符数 | 契约 9599 | 0（9599） | **是**（精确） |
| 引文可解析率 | 全部应可逐字定位 | 20/20 = 0 缺口 | **是**（精确） |
| 引文 content_hash | `sha256(quote)` 重算 | 0 不一致 | **是**（精确） |
| 结构切分覆盖 | 段长求和 = 全文 9599 | 0（9599） | **是**（精确） |
| 步骤章节命中 | 报告自报 ①②③④⑤⑥ | 6/6 | **是** |
| **分类正确性** | 需人工标注的 report_type ground truth | **无基准**（`extraction-skills/registry.json` 自述全部 skill 仍为 template-created、无代表报告跑通全流程；本工序只做了目录级查看，未做全仓穷举检索） | **无基准，声明 WITHHELD**（不粉饰；只声明证据强度与 confidence=medium） |

结论：可机检项全部**精确为 0 误差**；分类本身的准确性**无基准**，故只声明为可反驳假设，不声称 <3%。

### 图

![fig_wp9265_02_locator_map.png](figures/fig_wp9265_02_locator_map.png)

*图 1：20 条逐字证据定位在 report 9265 原文坐标上的分布（灰底为结构切分段，编号见 ③ 表）。*

![fig_wp9265_02_structure_signal.png](figures/fig_wp9265_02_structure_signal.png)

*图 2：左=结构切分各段字符数；右=registry 信号覆盖（灰=英文字面命中，红=语义定位证据），显示字面命中在中文正文上失效。*

### 复跑（repro_cmd）

`cd <worktree> && python3 scripts/kf/build_classification_9265_02.py --fetch && python3 scripts/kf/emit_wp9265_02_report.py && python3 -m pytest tests/test_wp9265_02_classification.py -q`

（无网络时去掉 `--fetch`，用已缓存的 `docs/kf/wp-9265-02/report_9265.md`；脚本仍会自己复算 sha256 并与契约比对，不一致直接退出。）

### KF-RESULT（正文唯一的 json 围栏块，原样提交）

```json
{
  "package_id": "wp-9265-02",
  "task_type": "02-classification-parse",
  "contract_version": "1.0",
  "report_id": "9265",
  "provenance": {
    "source_uri": "tensor://reports/9265",
    "source_field": "markdown",
    "source_hash": "sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c",
    "source_hash_matches": true,
    "title": "DP 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图（IN144-N05 / m7890）",
    "scenario_key": "dp_capability_assessment",
    "chars": 9599
  },
  "outputs": {
    "classification.json": {
      "schema": "classification.v1",
      "package_id": "wp-9265-02",
      "task_type": "02-classification-parse",
      "contract_version": "1.0",
      "report_id": "9265",
      "source": {
        "uri": "tensor://reports/9265",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c",
        "hash_expected_from_contract": "d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c",
        "hash_matches_contract": true,
        "chars": 9599,
        "bytes_utf8": 15943,
        "title": "DP 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图（IN144-N05 / m7890）",
        "scenario_key": "dp_capability_assessment",
        "campaign": {
          "node": "IN144-N05",
          "repo": "ship-performance-platform",
          "agent_branch": "agent/m7890",
          "evidence": [
            "L04-campaign-node-branch"
          ],
          "note": "上游产线标识，仅用于溯源；本工序不改写上游产物。"
        }
      },
      "report_type": "scientific-computation",
      "report_type_confidence": "medium",
      "classification_is_hypothesis": true,
      "unclassified_is_legal": true,
      "used_unclassified_fallback": false,
      "report_type_decision": {
        "rule": "取语义证据覆盖报告核心贡献（物理模型 + 数值方法 + 误差判定表 + 图）最多的报告类型为主型；只有当同一批证据同时满足其 skill 的步骤前提时才列为副型。分类是可反驳假设，非 verified。",
        "primary_evidence": [
          "L12-governing-laws",
          "L13-layered-physics-model",
          "L15-solver-iterations",
          "L17-error-table",
          "L18-regulation-comparison",
          "L20-figures"
        ],
        "why_not_only_algorithm": "报告主体是物理量（风/流/波浪漂移力、包线风速）与其自洽性/误差判定，算法（QP）是为物理服务的一层（② 明列 L1~L4 四层，L3 才是 QP）；见 L13-layered-physics-model 与 L17-error-table。",
        "why_not_software-engineering": "软件工程证据（模块/端点/40 项 pytest）是交付形态，不是报告的知识贡献；见 L10/L11/L21。"
      },
      "secondary_types": [
        {
          "report_type": "algorithm-implementation",
          "confidence": "medium",
          "evidence": [
            "L14-optimisation-problem",
            "L16-two-level-loops"
          ],
          "note": "QP 推力分配（无量纲化、等式约束解析消去、三种目标模式）+ 外层对风速二分。"
        },
        {
          "report_type": "software-engineering",
          "confidence": "low",
          "evidence": [
            "L10-numerical-kernel-modules",
            "L11-test-suite",
            "L21-repro-commands"
          ],
          "note": "落库模块/端点/测试/分支信息齐备，但只占报告的外壳。"
        }
      ],
      "excluded_types": [
        {
          "report_type": "experimental-validation",
          "reason": "报告自述无风洞/模型试验/回归表可对标，数值层 WITHHELD；无试验对象、无测量不确定度。",
          "evidence": [
            "L30-no-referenced-benchmark",
            "L31-withheld-numeric-layer"
          ]
        },
        {
          "report_type": "literature-review",
          "reason": "无文献综述节、无参考文献列表；DNV 对照仅定性且自述无可引数据集。",
          "evidence": [
            "L33-no-published-envelope-data",
            "L18-regulation-comparison"
          ]
        },
        {
          "report_type": "technical-proposal",
          "reason": "主体是已完成的计算与结果，不是方案/路线图；仅 ⑥ 末尾留下一句改进方向。",
          "evidence": [
            "L32-static-3dof-limitation"
          ]
        }
      ],
      "domain": {
        "discipline": "船舶总体性能",
        "subdomain": "操纵性 · 动力定位（DP）能力评估",
        "lane": "B",
        "tier": "l",
        "scenario_key": "dp_capability_assessment",
        "vessel": {
          "type": "DP-2 海工供应船（PSV, UT-755 级）",
          "principal_dimensions": "76.5 × 18.6 × 6.3 m",
          "evidence": [
            "L02-vessel-type-psv",
            "L03-main-dimensions"
          ]
        },
        "topic_tags": [
          {
            "tag": "dynamic-positioning-capability",
            "evidence": [
              "L01-domain-dp-definition"
            ]
          },
          {
            "tag": "thrust-allocation-qp",
            "evidence": [
              "L14-optimisation-problem"
            ]
          },
          {
            "tag": "environmental-loads-wind-current-wave-drift",
            "evidence": [
              "L13-layered-physics-model"
            ]
          },
          {
            "tag": "operability-envelope-polar",
            "evidence": [
              "L20-figures"
            ]
          },
          {
            "tag": "dp2-single-point-failure-redundancy",
            "evidence": [
              "L19-failure-analysis"
            ]
          },
          {
            "tag": "dnv-st-0111-classification-comparison",
            "evidence": [
              "L18-regulation-comparison"
            ]
          },
          {
            "tag": "static-3dof-conservative-scope",
            "evidence": [
              "L32-static-3dof-limitation"
            ]
          }
        ]
      },
      "skill_selection": {
        "skill_id": "xsk-scientific-computation",
        "skill_version": "0.1.0",
        "registry_version": "1.0",
        "lifecycle_state": "template-created",
        "selection_basis": "report_type 主型 → registry 按 report_type 一对一映射。",
        "registry_state_caveat": "registry 自述全部 skill 为 template-created（无代表报告跑通全流程），故所选 skill 的步骤仅为骨架，03 工序前不应视为已校验的方法学。"
      },
      "signal_table": [
        {
          "skill_id": "xsk-literature-review",
          "report_type": "literature-review",
          "registry_identify_signals": [
            "related work",
            "state of the art",
            "survey",
            "bibliography",
            "citation density >= 5 per 1000 chars"
          ],
          "literal_signal_hits_in_source": 0,
          "literal_hits_detail": [
            {
              "signal": "related work",
              "literal_hits": 0
            },
            {
              "signal": "state of the art",
              "literal_hits": 0
            },
            {
              "signal": "survey",
              "literal_hits": 0
            },
            {
              "signal": "bibliography",
              "literal_hits": 0
            },
            {
              "signal": "citation density >= 5 per 1000 chars",
              "literal_hits": 0
            }
          ],
          "semantic_evidence_locators": [],
          "semantic_evidence_count": 0,
          "skill_lifecycle_state": "template-created"
        },
        {
          "skill_id": "xsk-scientific-computation",
          "report_type": "scientific-computation",
          "registry_identify_signals": [
            "governing equations",
            "discretisation",
            "convergence study",
            "mesh refinement",
            "timing table"
          ],
          "literal_signal_hits_in_source": 0,
          "literal_hits_detail": [
            {
              "signal": "governing equations",
              "literal_hits": 0
            },
            {
              "signal": "discretisation",
              "literal_hits": 0
            },
            {
              "signal": "convergence study",
              "literal_hits": 0
            },
            {
              "signal": "mesh refinement",
              "literal_hits": 0
            },
            {
              "signal": "timing table",
              "literal_hits": 0
            }
          ],
          "semantic_evidence_locators": [
            "L12-governing-laws",
            "L13-layered-physics-model",
            "L15-solver-iterations",
            "L17-error-table",
            "L18-regulation-comparison",
            "L20-figures"
          ],
          "semantic_evidence_count": 6,
          "skill_lifecycle_state": "template-created"
        },
        {
          "skill_id": "xsk-algorithm-implementation",
          "report_type": "algorithm-implementation",
          "registry_identify_signals": [
            "pseudocode",
            "complexity",
            "algorithm block",
            "function signature",
            "O(n"
          ],
          "literal_signal_hits_in_source": 0,
          "literal_hits_detail": [
            {
              "signal": "pseudocode",
              "literal_hits": 0
            },
            {
              "signal": "complexity",
              "literal_hits": 0
            },
            {
              "signal": "algorithm block",
              "literal_hits": 0
            },
            {
              "signal": "function signature",
              "literal_hits": 0
            },
            {
              "signal": "O(n",
              "literal_hits": 0
            }
          ],
          "semantic_evidence_locators": [
            "L14-optimisation-problem",
            "L16-two-level-loops"
          ],
          "semantic_evidence_count": 2,
          "skill_lifecycle_state": "template-created"
        },
        {
          "skill_id": "xsk-software-engineering",
          "report_type": "software-engineering",
          "registry_identify_signals": [
            "changed files",
            "commit",
            "interface",
            "regression",
            "API"
          ],
          "literal_signal_hits_in_source": 5,
          "literal_hits_detail": [
            {
              "signal": "changed files",
              "literal_hits": 0
            },
            {
              "signal": "commit",
              "literal_hits": 0
            },
            {
              "signal": "interface",
              "literal_hits": 0
            },
            {
              "signal": "regression",
              "literal_hits": 0
            },
            {
              "signal": "API",
              "literal_hits": 5
            }
          ],
          "semantic_evidence_locators": [
            "L10-numerical-kernel-modules",
            "L11-test-suite",
            "L21-repro-commands"
          ],
          "semantic_evidence_count": 3,
          "skill_lifecycle_state": "template-created"
        },
        {
          "skill_id": "xsk-technical-proposal",
          "report_type": "technical-proposal",
          "registry_identify_signals": [
            "proposal",
            "design",
            "roadmap",
            "specification",
            "plan"
          ],
          "literal_signal_hits_in_source": 0,
          "literal_hits_detail": [
            {
              "signal": "proposal",
              "literal_hits": 0
            },
            {
              "signal": "design",
              "literal_hits": 0
            },
            {
              "signal": "roadmap",
              "literal_hits": 0
            },
            {
              "signal": "specification",
              "literal_hits": 0
            },
            {
              "signal": "plan",
              "literal_hits": 0
            }
          ],
          "semantic_evidence_locators": [],
          "semantic_evidence_count": 0,
          "skill_lifecycle_state": "template-created"
        },
        {
          "skill_id": "xsk-experimental-validation",
          "report_type": "experimental-validation",
          "registry_identify_signals": [
            "test matrix",
            "facility",
            "measurement uncertainty",
            "validation case",
            "baseline comparison"
          ],
          "literal_signal_hits_in_source": 0,
          "literal_hits_detail": [
            {
              "signal": "test matrix",
              "literal_hits": 0
            },
            {
              "signal": "facility",
              "literal_hits": 0
            },
            {
              "signal": "measurement uncertainty",
              "literal_hits": 0
            },
            {
              "signal": "validation case",
              "literal_hits": 0
            },
            {
              "signal": "baseline comparison",
              "literal_hits": 0
            }
          ],
          "semantic_evidence_locators": [],
          "semantic_evidence_count": 0,
          "skill_lifecycle_state": "template-created"
        }
      ],
      "signal_method_note": "registry.identify_signals 全部为英文关键词，本报告为中文正文，字面命中数（literal_signal_hits_in_source）系统性偏低甚至为 0，不能作为分类依据；因此以逐字定位的中文语义证据为主，字面命中只作诊断量如实记录（这是本工序的方法学局限，不是分类结果的证据强度）。",
      "structure": {
        "parser": "ATX heading 切分（^#{1,6}\\s），偏移为 UTF-8 解码后的字符偏移",
        "self_declared_six_sections": {
          "①": 1,
          "②": 2,
          "③": 3,
          "④": 9,
          "⑤": 10,
          "⑥": 11
        },
        "self_declared_six_sections_complete": true,
        "section_count": 13,
        "sections": [
          {
            "index": 0,
            "level": 1,
            "heading": "动力定位 (DP) 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图",
            "start_offset": 0,
            "end_offset": 352,
            "chars": 352,
            "body_lines": 9,
            "tables": 0,
            "code_blocks": 0
          },
          {
            "index": 1,
            "level": 2,
            "heading": "① 案例介绍（物理背景 / 几何 / 参数表）",
            "start_offset": 352,
            "end_offset": 1498,
            "chars": 1146,
            "body_lines": 29,
            "tables": 16,
            "code_blocks": 0
          },
          {
            "index": 2,
            "level": 2,
            "heading": "② 怎么做的（方法 / 流程 / 关键设置 / 工具链）",
            "start_offset": 1498,
            "end_offset": 3391,
            "chars": 1893,
            "body_lines": 46,
            "tables": 0,
            "code_blocks": 1
          },
          {
            "index": 3,
            "level": 2,
            "heading": "③ 计算结果（数字表，程序注入）",
            "start_offset": 3391,
            "end_offset": 3412,
            "chars": 21,
            "body_lines": 2,
            "tables": 0,
            "code_blocks": 0
          },
          {
            "index": 4,
            "level": 3,
            "heading": "3.1 10 个工况点的 3-DOF 平衡（判据：残差 ≤1%）",
            "start_offset": 3412,
            "end_offset": 4228,
            "chars": 816,
            "body_lines": 18,
            "tables": 12,
            "code_blocks": 0
          },
          {
            "index": 5,
            "level": 3,
            "heading": "3.2 操作包线（可用推力 0.6 × 装机，Hs 3 m / Tp 8 m，共线环境）",
            "start_offset": 4228,
            "end_offset": 4797,
            "chars": 569,
            "body_lines": 16,
            "tables": 4,
            "code_blocks": 0
          },
          {
            "index": 6,
            "level": 3,
            "heading": "3.3 单推力器失效能力降级（DP-2 最坏单点失效，1 kn=0.5 m/s 共线流）",
            "start_offset": 4797,
            "end_offset": 5416,
            "chars": 619,
            "body_lines": 14,
            "tables": 6,
            "code_blocks": 0
          },
          {
            "index": 7,
            "level": 3,
            "heading": "3.4 QP 数值性质",
            "start_offset": 5416,
            "end_offset": 6023,
            "chars": 607,
            "body_lines": 16,
            "tables": 8,
            "code_blocks": 0
          },
          {
            "index": 8,
            "level": 3,
            "heading": "3.5 图",
            "start_offset": 6023,
            "end_offset": 6301,
            "chars": 278,
            "body_lines": 9,
            "tables": 0,
            "code_blocks": 0
          },
          {
            "index": 9,
            "level": 2,
            "heading": "④ 与 DNV 规范的对照（定性）",
            "start_offset": 6301,
            "end_offset": 6917,
            "chars": 616,
            "body_lines": 18,
            "tables": 9,
            "code_blocks": 0
          },
          {
            "index": 10,
            "level": 2,
            "heading": "⑤ 注意点（踩坑 / 局限 / 适用范围）",
            "start_offset": 6917,
            "end_offset": 8003,
            "chars": 1086,
            "body_lines": 23,
            "tables": 0,
            "code_blocks": 0
          },
          {
            "index": 11,
            "level": 2,
            "heading": "⑥ 误差判定（逐项，显式回答\"是否 <3%\"）",
            "start_offset": 8003,
            "end_offset": 9198,
            "chars": 1195,
            "body_lines": 26,
            "tables": 15,
            "code_blocks": 0
          },
          {
            "index": 12,
            "level": 3,
            "heading": "复现",
            "start_offset": 9198,
            "end_offset": 9599,
            "chars": 401,
            "body_lines": 8,
            "tables": 0,
            "code_blocks": 1
          }
        ]
      },
      "evidence_locators": [
        {
          "id": "L01-domain-dp-definition",
          "supports": "topic.domain",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=380-439",
          "start_offset": 380,
          "end_offset": 439,
          "quote": "DP（dynamic positioning）系统靠推进器合成力/力矩抵消风、浪、流载荷，在无锚条件下保持船位与艏向。",
          "content_hash": "sha256:16ef8754a902739fb32eb849420225f79e5d90d2741e4c0823678bf8eb8d61e6"
        },
        {
          "id": "L02-vessel-type-psv",
          "supports": "topic.vessel_type",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=440-487",
          "start_offset": 440,
          "end_offset": 487,
          "quote": "本节点评估一艘典型 **DP-2 海工供应船（PSV, UT-755 级）** 的 DP 能力",
          "content_hash": "sha256:feaaca2b8f1f63f9589e9727227411265d2d4260bef5d707590e3d3a28ce15ec"
        },
        {
          "id": "L03-main-dimensions",
          "supports": "topic.geometry",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=612-669",
          "start_offset": 612,
          "end_offset": 669,
          "quote": "| LOA × B × T | 76.5 × 18.6 × 6.3 m | `reference_psv()` |",
          "content_hash": "sha256:9ff7dd49520f55e9bc49e696c0e0732aeed44eaa3114ef8f1ba87beebfa2f6a7"
        },
        {
          "id": "L04-campaign-node-branch",
          "supports": "provenance.campaign",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=44-118",
          "start_offset": 44,
          "end_offset": 118,
          "quote": "**战役节点** IN144-N05 ｜ **仓库** ship-performance-platform ｜ **分支** agent/m7890",
          "content_hash": "sha256:47f54e0dde4180730f7494ff86742d541fbe971d293f4efd7714ea63de19aaf3"
        },
        {
          "id": "L10-numerical-kernel-modules",
          "supports": "type.software-engineering",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=119-214",
          "start_offset": 119,
          "end_offset": 214,
          "quote": "**落库模块** `backend/physics/dp_core.py`（物理/数值内核）、`backend/api/dynamic_positioning.py`（FastAPI 端点）",
          "content_hash": "sha256:e2685b0203c224f6fc018c6dcd30445adde016fae1cc2e130f8ac20d0c8ab4bc"
        },
        {
          "id": "L11-test-suite",
          "supports": "type.software-engineering",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=215-272",
          "start_offset": 215,
          "end_offset": 272,
          "quote": "**验证** `tests/test_dp_capability.py`（40 项 pytest，22 s 全绿）",
          "content_hash": "sha256:c2acc07e40d97e3bbd5bfe85e5ab36516adaece94c9e5cddf99f3a532a7054e0"
        },
        {
          "id": "L12-governing-laws",
          "supports": "type.scientific-computation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=1592-1653",
          "start_offset": 1592,
          "end_offset": 1653,
          "quote": "螺旋桨定律 `T = ρD⁴K_Tn²`、`P = 2πρD⁵K_Qn³` ⇒ 消去转速得 **`T ∝ P^{2/3}`",
          "content_hash": "sha256:eba21c9b1d603c072ce33db4920ddf84161ee5b44fc65cf7b61a42e4b2302a10"
        },
        {
          "id": "L13-layered-physics-model",
          "supports": "type.scientific-computation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=1852-1864",
          "start_offset": 1852,
          "end_offset": 1864,
          "quote": "**L2 环境力模型**",
          "content_hash": "sha256:a803b6cc1f51bfd9141ac8a73faacb4377ae94296e0a368ea0374b41018b56fd"
        },
        {
          "id": "L14-optimisation-problem",
          "supports": "type.algorithm-implementation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=2520-2564",
          "start_offset": 2520,
          "end_offset": 2564,
          "quote": "min_e  Σ (w_i (e_i − r_i)²)        (二次型, 良态)",
          "content_hash": "sha256:a04f996db40f44722248f501cea9cfe23d06e802c18db875248b5ed21fd241b5"
        },
        {
          "id": "L15-solver-iterations",
          "supports": "type.scientific-computation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=5581-5614",
          "start_offset": 5581,
          "end_offset": 5614,
          "quote": "| 受约束（0.5× 推力）工况 QP 迭代数 | 最大 29 |",
          "content_hash": "sha256:d79ef54b2924d56a80de2d35c6d260d58ac1da315a679e7f5d9995e56d5461cd"
        },
        {
          "id": "L16-two-level-loops",
          "supports": "type.algorithm-implementation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=3085-3112",
          "start_offset": 3085,
          "end_offset": 3112,
          "quote": "**对风速二分**（容差 5e-3 m/s）求可行上界",
          "content_hash": "sha256:a4a0f16583a74eee370b173b33cc61ead0059a85a8bba03b2f5c1bc1fa59111e"
        },
        {
          "id": "L17-error-table",
          "supports": "type.scientific-computation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=8435-8480",
          "start_offset": 8435,
          "end_offset": 8480,
          "quote": "| QP 解 vs KKT 闭式解 | 解析 | 7.1e-15 kN | **是** |",
          "content_hash": "sha256:96e3258f028efdf83b72daf74ee918406d7b772854299b8d488e64c9b900882d"
        },
        {
          "id": "L18-regulation-comparison",
          "supports": "type.scientific-computation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=6301-6321",
          "start_offset": 6301,
          "end_offset": 6321,
          "quote": "## ④ 与 DNV 规范的对照（定性）",
          "content_hash": "sha256:6f105aa7d32e51bea0d1480e8c2f302d6f723ef7f0d27396ae01223e2029abee"
        },
        {
          "id": "L19-failure-analysis",
          "supports": "topic.dp2-redundancy",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=4797-4845",
          "start_offset": 4797,
          "end_offset": 4845,
          "quote": "### 3.3 单推力器失效能力降级（DP-2 最坏单点失效，1 kn=0.5 m/s 共线流）",
          "content_hash": "sha256:c4165be0dfa165007a8a6e0b68187e3127874fe5c2ec8fcb93dceb429dba1fcd"
        },
        {
          "id": "L20-figures",
          "supports": "type.scientific-computation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=6064-6116",
          "start_offset": 6064,
          "end_offset": 6116,
          "quote": "`capability_polar.png` — 极坐标操作包线图（5 条等电流曲线 + 最坏失效虚线）",
          "content_hash": "sha256:547f0a7e58d65ac0a61cc1ff220204a276ed551ead659d2b12f0499efe898eb3"
        },
        {
          "id": "L21-repro-commands",
          "supports": "type.software-engineering",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=9214-9289",
          "start_offset": 9214,
          "end_offset": 9289,
          "quote": "python3 -m pytest tests/test_dp_capability.py -q          # 40 passed, 22 s",
          "content_hash": "sha256:226770a5606ada69fb39617fba00a9b1537e42f27e18f4058620522ba78d45a4"
        },
        {
          "id": "L30-no-referenced-benchmark",
          "supports": "exclude.experimental-validation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=7593-7648",
          "start_offset": 7593,
          "end_offset": 7648,
          "quote": "仓库内没有风洞、模型试验或 OCIMF/Isherwood 回归表可对标 ⇒ **数值层 WITHHELD**",
          "content_hash": "sha256:f7820b6c94c8f356835c2f7cba2899affcaca53fd1319061b3cc03346a9f6d61"
        },
        {
          "id": "L31-withheld-numeric-layer",
          "supports": "exclude.experimental-validation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=8656-8675",
          "start_offset": 8656,
          "end_offset": 8675,
          "quote": "**无基准，声明 WITHHELD**",
          "content_hash": "sha256:fe665da9db83b7d0c8b56db8ecd14be8dc7d2c7d5adf0c4dfe852e9bbb0a3cb3"
        },
        {
          "id": "L32-static-3dof-limitation",
          "supports": "exclude.dynamic-simulation",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=7472-7523",
          "start_offset": 7472,
          "end_offset": 7523,
          "quote": "- 静力 3-DOF：无低频/波频动态、无控制器、无瞬态与推力器再分配过程（只用速率限做静态可行性）。",
          "content_hash": "sha256:3d0a4d0f469d362abd86317b07cdd48cb75e0a098b7181a96f649544b96fd63e"
        },
        {
          "id": "L33-no-published-envelope-data",
          "supports": "exclude.literature-review",
          "locator_type": "char_range",
          "value": "tensor://reports/9265#chars=6323-6378",
          "start_offset": 6323,
          "end_offset": 6378,
          "quote": "仓库内没有可引用的 DNV 已发表包线数值数据集，故**只做方法与定性特征对照**（数值层 WITHHELD）",
          "content_hash": "sha256:10d2f05a1cb747ca9748264ce19853dbaf89b17b4ad6f13e51ffad88d8819693"
        }
      ],
      "uncertainty": [
        {
          "item": "类型判定为可反驳假设，未经验证",
          "status": "hypothesis",
          "note": "confidence=medium：主型与副型共享同一批数值证据，registry 的英文关键词无法字面判定。"
        },
        {
          "item": "报告数值层缺基准，能力包线绝对值不可复核",
          "status": "withheld_by_source",
          "evidence": [
            "L31-withheld-numeric-layer"
          ],
          "note": "原文自述 WITHHELD；本工序只分类，不对数值下任何结论。"
        },
        {
          "item": "报告为静力 3-DOF 模型，动态/控制器未建模",
          "status": "declared_limitation",
          "evidence": [
            "L32-static-3dof-limitation"
          ]
        },
        {
          "item": "报告对象是 reference_psv() 工程模型船，是否对应某实船未声明",
          "status": "unresolved",
          "evidence": [
            "L03-main-dimensions",
            "L02-vessel-type-psv"
          ],
          "note": "原文只给主尺度与模型函数名，absent 信息不补（do_not_invent_missing_information）。"
        }
      ],
      "not_done": [
        "不做知识抽取（claims/evidence/provenance 属 03 工序，本包 objective.register_assets=false 亦未登记附件）",
        "不判 verified：verified 由平台门计算，本产物仅 draft"
      ],
      "generated_by": "scripts/kf/build_classification_9265_02.py"
    }
  }
}
```
