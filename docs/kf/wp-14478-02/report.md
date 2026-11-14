# KF-RESULT wp-14478-02

工作包 `wp-14478-02`（工序 02 分类解析，lane B，契约 1.0）对报告 `14478` 的判定结果。
本工序只做**分类/解析**，不做抽取、不做证据定性、不盖 verified。

## ① 本工序做了什么

对报告 `tensor://reports/14478` 的 `markdown` 字段（6156 字符 / 9430 字节 UTF-8 /
145 行，重算哈希 `sha256:8fbd643e2e79…` 与契约一致）做三件可机检的事：

1. **判类型**：按 `extraction-skills/<type>.md` §1 的 `identify_signals` 逐条判六分型，结论
   **`scientific-computation`**（置信 **medium**），选中 skill
   `xsk-scientific-computation` v0.1.0
   （lifecycle `template-created`）；
2. **给主题标签**：9 条检索标签（学科域/方法/状态/平台/工具链），每条锚在原文逐字引文；
3. **切结构**：按行首 `#` 切成 8 段、首尾相接覆盖 `0–6156` 全文。

交付物 `classification.json` 中 21 条判定信号 + 26 个 locator（字符偏移 + 逐字引文 +
引文 sha256），**0 条无证据的判定**：无引文的项一律显式 `unresolved` 并写理由。

**本工序不产生任何物理结果数字**（无 C_D / C_L / p_diff 的 got），也不复制源报告的 got 数字。

### 案例背景（源报告自述，逐字引用；本工序不做二次叙述）

- 状态：`> 状态：**honest-FAIL / fail_stage = compute_wait（集群排队未取回结果）**`
- 算例：`二维通道内静止圆柱绕流（Schäfer & Turek 1996 基准，DFG 2D-1）`
- 判定口径来自源报告而非本工序：`**判据（先于计算声明）**：三个参考量（$C_D$、$C_L$、$p_{diff}$）在**最细网格**上相对误差均 <5%，`

源报告 §③ 参数表（**程序化整行注入，未重打任何数字**）：

| 量 | 符号 | 值 | 说明 |
|---|---|---|---|
| 密度 | $\rho$ | 1 kg/m³ | 基准规定 |
| 运动黏度 | $\nu$ | 0.001 m²/s | 基准规定 |
| 入口最大速度 | $U_{max}$ | 0.3 m/s | 抛物线峰值 |
| 入口平均速度 | $U_{mean}$ | 0.2 m/s | $=2U_{max}/3$ |
| 圆柱直径 | $D=2r$ | 0.1 m | 特征长度 |
| 域尺寸 | $L\times H$ | 2.2 × 0.41 m | DFG 通道 |
| 阻塞比 | $D/H$ | 0.2439 | 通道约束强度 |
| 域长径比 | $L/D$ | 22 | 尾迹长度 |
| Reynolds（直径） | $Re_D$ | 20 | 算例定义 |
| Reynolds（通道高） | $Re_H$ | 82 | 通道尺度参考 |
| 网格 | $n_x\times n_y$ | 64×24 / 128×48 / 256×96 | 三档细化，级距比 ≈2 |
| 收敛判据 | — | 残差 1e-6 / 迭代上限 1500–3000 | `SolverConfig.tolerance` |

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文（不许凭记忆）**：`GET $TENSOR_API_BASE/tensor/reports/14478` 取 `markdown`，
   落字节快照 `docs/kf/wp-14478-02/source/report_14478.md`（`byte snapshot of platform API markdown field`）；
   `psql` 直读被权限拒绝（`permission denied for table tensor_reports`），故走 API。
2. **源身份门**：`sha256(markdown.encode('utf-8'))` 重算 = `sha256:8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0`，与契约
   `sha256:8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0` **逐字节相等**，字符数 6156 = 契约 `chars`。
3. **逐条判定**：对六型共 6 组注册表信号写死 `signal` 文本（抄自 skill 文档 §1）+ 逐字 `quote`；
   生成器用 `md.index(quote)` 求偏移、断言 `md[s:e] == quote`、要求**全文唯一**（否则报错退出），
   并算 `sha256(quote)` 作为 `content_hash`（对齐 GATE-RULES E3/E5）。
4. **结构切分**：行首 `#` 行切段，断言相邻段 `end_offset == next.start_offset` 且末段到文末。
5. **schema 门**：产物对 `schemas/classification.v1.schema.json`（本仓新增）与
   `schemas/kf_result.v1.schema.json` 用 `jsonschema`(Draft 2020-12) 校验。
6. **确定性复跑**：pytest 里把生成器跑到 tmp 目录，断言两份 JSON 与入库版本**逐字段相等**。

一键复跑（工作树根）：

```bash
# 平台重取 + 全链路自检 + 测试 + 报告再生成
python3 scripts/kf/wp14478_02_classify.py --fetch --check
python3 -m pytest tests/test_kf_wp14478_02.py -q
python3 scripts/kf/wp14478_02_report.py
# 无平台凭据时的离线口径（用已入库的字节快照）
python3 scripts/kf/wp14478_02_classify.py --check --snapshot docs/kf/wp-14478-02/source/report_14478.md && python3 -m pytest tests/test_kf_wp14478_02.py -q && python3 scripts/kf/wp14478_02_report.py
```

关键设置：`unique=True`（引文必须唯一）、`Draft202012Validator`、`minLength` 约束（quote ≥1、
unresolved.reason ≥20 字符）、`epistemic_status=draft` / `assessment_status=unassessed`。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-14478-02/classification.json` | 工序 02 产物：类型 = **scientific-computation**（confidence medium）、21 条信号、9 条主题标签、8 段结构切分、26 个 locator |
| `docs/kf/wp-14478-02/kf_result.json` | KF-RESULT 信封：`source_hash` = `sha256:8fbd643e2e79…`（=契约）、`chars` = 6156 |
| `docs/kf/wp-14478-02/source/report_14478.md` | 源字节快照（9430 字节），哈希与平台一致，供离线复算 |
| `docs/kf/wp-14478-02/figures/classification_map.png` | 图：结构分段轴 + 信号命中位置 + 六分型信号命中分布 |
| `schemas/classification.v1.schema.json` | 工序 02 产物的可机检 schema（本仓新增，见 ⑤ 局限） |
| `scripts/kf/wp14478_02_classify.py` | 生成器 + acceptance 自检（`--check` 失败即非零退出） |
| `tests/test_kf_wp14478_02.py` | 14 项独立不变量测试（哈希/偏移/唯一性/schema/确定性/边界） |

### 六分型信号命中统计（程序化统计自 `classification.json`）

| 候选类型 | matched | partial | not_found | 判定 |
|---|---|---|---|---|
| scientific-computation | 3 | 2 | 0 | accepted |
| experimental-validation | 1 | 1 | 1 | rejected |
| algorithm-implementation | 0 | 1 | 1 | rejected |
| software-engineering | 0 | 2 | 1 | rejected |
| technical-proposal | 0 | 1 | 1 | rejected |
| literature-review | 0 | 1 | 2 | rejected |

判定依据：`按 extraction-skills/<type>.md §1 的 identify_signals 逐条判定：scientific-computation 5 条中 3 条 matched（discretisation / convergence study / mesh refinement）、2 条 partial（governing equation / timing table）；最接近的竞争类型 experimental-validation 亦有 1 条 matched（validation case）+ 1 条 partial（baseline comparison），但其三条定义性信号全缺；其余四型无 matched。故类型取 scientific-computation，置信 medium（因竞争类型存在 matched 信号）。注意：SC 的 convergence/mesh 两条 matched 是**设计层声明**（§⑤ 自述“待计算”），不是“已跑出收敛阶”。`

### 结构切分（8 段，覆盖全文）

| 段 ID | 层级 | 标题 | 偏移 | 长度 |
|---|---|---|---|---|
| SEC-01 | 1 | CASE-CYLINDER-DRAG-FVM: DFG 2D-1 圆柱阻力算例（TensorFVM）—— honest-FAIL（计算未取回） | 0–328 | 328 |
| SEC-02 | 2 | ① 问题与参考值出处 | 328–1577 | 1249 |
| SEC-03 | 2 | ② 方法与实现（已完成的真实部分） | 1577–3063 | 1486 |
| SEC-04 | 2 | ③ 参数表（无量纲数完整） | 3063–3634 | 571 |
| SEC-05 | 2 | ④ 对照表（ref vs got + 逐项误差）—— **FAIL：无 got** | 3634–4186 | 552 |
| SEC-06 | 2 | ⑤ 收敛性/参数敏感性 —— **FAIL：待计算** | 4186–4545 | 359 |
| SEC-07 | 2 | ⑥ 失败模式与工件 | 4545–5509 | 964 |
| SEC-08 | 2 | 生态摩擦（如实记） | 5509–6156 | 647 |

## ④ 证据定位表（claim / 字段 → 原文引文片段）

偏移口径：UTF-8 解码后字符下标，0 基、end 开区间；`content_hash` = `sha256(quote)`，全部在
`classification.json` 内逐条给出。下表引文为**原文逐字片段**：表格内 `|` 按 Markdown 需转义为 `\|`、过长处截断并以 `…` 结尾——
转义/截断只发生在本表渲染层，**完整逐字引文与偏移以 `classification.json` 的 `quote` 字段为准**。

### 4.1 判定信号（21 条）

| 信号 ID | 注册表信号 | 判定 | 字符偏移 | 原文引文（逐字） |
|---|---|---|---|---|
| SIG-SC-01 | governing equation | partial | 523–577 | ` $\rho=1$、$\nu=0.001$ m²/s，$Re_D=U_{mean}D/\nu=20$ 定常层流 ` |
| SIG-SC-02 | discretisation | matched | 1645–1668 | ` 贴体网格 + SIMPLE/Rhie–Chow ` |
| SIG-SC-03 | convergence study | matched | 4346–4384 | ` Richardson 外推 $C_{D,\infty}$、最细网格 GCI； `（共 2 条 locator） |
| SIG-SC-04 | mesh refinement | matched | 4262–4311 | ` 1. **网格细化**：64×24 → 128×48 → 256×96（级距减半），输出观测收敛阶 ` |
| SIG-SC-05 | timing table | partial | 4080–4137 | ` 控制面（99）实测不可承担：64×24 网格 200 次迭代 >120 s（shell 单次上限），无法本地兜底。 ` |
| SIG-EV-01 | validation case | matched | 343–388 | ` 二维通道内静止圆柱绕流（Schäfer & Turek 1996 基准，DFG 2D-1） ` |
| SIG-EV-02 | baseline comparison | partial | 239–303 | ` **判据（先于计算声明）**：三个参考量（$C_D$、$C_L$、$p_{diff}$）在**最细网格**上相对误差均 <5%， `（共 2 条 locator） |
| SIG-EV-03 | test matrix / facility description / measurement uncertainty | not_found | — | （无引文：显式 unresolved，见 classification.json） |
| SIG-AI-01 | pseudocode block / complexity statement / `O(` in results section | not_found | — | （无引文：显式 unresolved，见 classification.json） |
| SIG-AI-02 | function signature | partial | 1761–1819 | `` 本单新增算例级 harness `scripts/case_cylinder_drag_fvm.py`（三个入口）： `` |
| SIG-SE-01 | changed files | partial | 4897–4916 | ` 工件（worktree 内真实路径）： ` |
| SIG-SE-02 | regression statement | partial | 5302–5358 | `` `pytest tests/test_case_cylinder_drag_fvm.py` → 1 passed `` |
| SIG-SE-03 | commit reference / interface/API change | not_found | — | （无引文：显式 unresolved，见 classification.json） |
| SIG-TP-01 | proposal / roadmap / specification | not_found | — | （无引文：显式 unresolved，见 classification.json） |
| SIG-TP-02 | design / plan | partial | 4218–4260 | `` 设计已完成、待数据即可出数（`analyze` 已实现并已用合成数据契约测试验证）： `` |
| SIG-LR-01 | bibliography | partial | 1046–1120 | ` Turek & Schaefer, *Benchmark computations of laminar flow around cylinder* ` |
| SIG-LR-02 | related work / state of the art / survey | not_found | — | （无引文：显式 unresolved，见 classification.json） |
| SIG-LR-03 | citation density >= 5 per 1000 chars | not_found | — | （无引文：显式 unresolved，见 classification.json） |
| SIG-ST-01 | honest-FAIL verdict | matched | 75–134 | ` > 状态：**honest-FAIL / fail_stage = compute_wait（集群排队未取回结果）** ` |
| SIG-ST-02 | results absent (no got) | matched | 3812–3859 | ` \| 64×24 \| 未取回 \| — \| 未取回 \| — \| 未取回 \| — \| ❌ 无数据 \| ` |
| SIG-ST-03 | failure cause: queue wait | matched | 3972–4023 | `` 三个作业递交后一直处于 `queued` 状态（递交 23:22 UTC 时队列前方 312 个作业； `` |

### 4.2 主题标签（9 条）

| 标签 ID | 标签 | 体系 | 字符偏移 | 原文引文（逐字） |
|---|---|---|---|---|
| TOP-DOM-01 | 阻力 / drag (C_D) | subject-domain | 642–702 | ` \| $C_D$ \| 5.57953523384 \| DFG 2D-1 官网页 “Reference results”… ` |
| TOP-DOM-02 | 圆柱绕流 / flow around a cylinder | subject-domain | 343–388 | ` 二维通道内静止圆柱绕流（Schäfer & Turek 1996 基准，DFG 2D-1） ` |
| TOP-DOM-03 | 定常层流 / steady laminar, Re_D=20 | subject-domain | 3422–3459 | ` \| Reynolds（直径） \| $Re_D$ \| 20 \| 算例定义 \| ` |
| TOP-MTH-01 | 有限体积 + SIMPLE/Rhie–Chow | method | 1645–1668 | ` 贴体网格 + SIMPLE/Rhie–Chow ` |
| TOP-MTH-02 | 网格收敛 / Richardson / GCI | method | 4262–4311 | ` 1. **网格细化**：64×24 → 128×48 → 256×96（级距减半），输出观测收敛阶 ` |
| TOP-STS-01 | honest-FAIL / compute_wait | status | 75–134 | ` > 状态：**honest-FAIL / fail_stage = compute_wait（集群排队未取回结果）** ` |
| TOP-PLT-01 | 集群排队 / 调度不确定性 | platform | 4817–4869 | ` 4. **排队/调度不确定性**：本单即被队列阻塞——重算依赖集群派发，算例池批量铺开时这是系统性风险， ` |
| TOP-PLT-02 | 平台缺项：知识检索离线 / oss_solutions 无端点 | platform | 5523–5588 | `` 1. **knowledge_base 检索引擎离线**：`/api/v1/tensor/knowledge/search… `` |
| TOP-TLS-01 | 算例 harness / 契约测试 | tooling | 1761–1819 | `` 本单新增算例级 harness `scripts/case_cylinder_drag_fvm.py`（三个入口）： `` |

### 4.3 图

![classification_map](attachment:classification_map.png)

图注：上半为源报告 6156 字符的结构分段（竖线=段边界，标注段 ID 与标题）与分类信号命中位置
（▲ 绿=matched、橙=partial，竖排为信号 ID）；下半为六分型候选按注册表 `identify_signals` 的命中计数
（绿/橙/红=matched/partial/not_found）——`scientific-computation` 是唯一有 matched 的类型。
图由 `scripts/kf/wp14478_02_report.py` 从 `classification.json` 程序化生成，无手绘数字。

## ⑤ 注意点与局限

1. **信号判定是文本层判定，不是执行状态判定**：`SIG-SC-03`（convergence study）与 `SIG-SC-04`
   （mesh refinement）判 matched，指源报告**声明了**这两件事；源报告 §⑤ 自述“设计已完成、待数据即可出数”，
   并不表示已算出收敛阶。本工序不评价执行状态。
2. **竞争类型确实存在 matched 信号**：`experimental-validation` 的 `validation case` 也 matched
   （本算例本身就是一个基准算例），故 confidence 取 **medium** 而非 high；区分依据是该型三条定义性信号
   （test matrix / facility description / measurement uncertainty）全为 `not_found`，且对照侧是文献数值基准
   而非测量值。
3. **`governing equation` 与 `timing table` 只到 partial**：源报告未写出控制方程显式形式，也只有单点耗时
   陈述（无耗时表）。两项均记 `unresolved` + 理由 + “什么能解决它”，**未补写方程/耗时表**。
4. **schema 是自建的**：平台侧 `kf_result.v1.schema.json` 只把 `outputs.classification.json` 声明为无约束
   `object`，仓内没有官方 02 产物 schema，因此 `schema_pass` 由本次新增的
   `schemas/classification.v1.schema.json` 自查给出——这是自查，不等于平台认可的口径。
5. **结构解析器不做代码栅栏感知**：按行首 `#` 切段；本源文件代码块内无行首 `#`（段连续性断言已覆盖），
   但用于其它报告时可能误切。
6. **注册表本身未校准**：`extraction-skills/registry.json` 全部 skill 的生命周期是 `template-created`、
   `reuse_count = 0`，`citation density ≥ 5/1000` 这类阈值没被真实报告校准过；`SIG-LR-03` 是按可见条目
   人工判断，未做机器引文计数。
7. **零手抄的边界**：本报告所有数字/引文由脚本从 `classification.json` / `kf_result.json` / 源快照注入，
   没有一处凭记忆重述；正文里唯一的人工文字是判定理由与局限说明。
8. **不越界**：只读/写 `report_id=14478`；未读取其它报告、未改写上游产物、未把任何对象标为
   verified（`epistemic_status=draft`、`assessment_status=unassessed`、
   `verification_performed_by_producer=false`）。

### 误差判定（本工序口径，如实记）

本工序是文档分类工序，**不产生计算量**，因此没有“本工序结果 vs 基准”的误差可列；源报告的
5% 判据（`<5%`，见 4.1 中 `SIG-EV-02`）在其自身 ④ 对照表里**无 got**（`SIG-ST-02`），本工序不补、不估、
不引用任何历史数字。回答“是否 <3%”：**NOT_APPLICABLE — 无本工序计算量，且源报告无 got 值可判**。

### 对抗性自查（作者自审，不独立）

- 严重度 High：无（未发现可导致错分/伪证的未披露缺陷）；**Medium-1**：竞争类型 matched 信号未降级为
  unresolved，仅用 confidence + rationale 承载 → 处置：保留为 matched（文本确实存在）并下调 confidence，
  rationale 明写拒绝依据；**Medium-2**：`schema_pass` 自建 schema → 处置：在 ⑤.4 显式披露，交由平台门复核；
  **Low**：主题标签命名粒度为主观 → 已在 `uncertainty` 记录。
- 未做的检查：类型判定的**语义**正确性无机器判据（需 04 工序/人工）；未做跨报告引文密度机器计数。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json+schema_pass(classification) | ✅ | ok |
| valid_json+schema_pass(kf_result) | ✅ | ok |
| source_hash_matches | ✅ | recomputed=sha256:8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0 |
| source_locator_resolvable | ✅ | 26 个 locator 全部可由偏移+逐字引文解析 |
| no_duplicate_ids | ✅ | 44 ids, 44 unique |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | 全部 signal 均有 locator 或 unresolved |
| report_type_in_registry | ✅ | report_type=scientific-computation ∈ ['algorithm-implementation', 'experimental-validation', 'literature-revie |
| skill_id_in_registry | ✅ | skill=xsk-scientific-computation report_type=scientific-computation |
| structure_covers_source | ✅ | 8 sections, span=0-6156 / 6156 |
| not_marked_verified | ✅ | draft / unassessed / producer 未做 verification |
| scope_only_report_14478 | ✅ | report_id=14478 |

**失败项：0**。全部通过（自检口径见上表）。

补充说明（不含在 acceptance 但本单要求的纪律）：

- ✅ 本报告只有一个 JSON 代码块（围栏语言标记为 json）= `kf_result.json` 原文，逐字节同
  `docs/kf/wp-14478-02/kf_result.json`；标题 `KF-RESULT wp-14478-02`，tags 含 `kf-wp:wp-14478-02`；
- ✅ `provenance.source_hash` 与源报告 markdown 字节哈希一致（平台独立重算）；
- ✅ honest 项：源报告 ④ 无 got、`governing equation`/`timing table` 仅 partial、schema 自建——均已写在 ⑤。

## 附：kf_result.json（本报告唯一的 JSON 代码块）

```json
{
 "package_id": "wp-14478-02",
 "task_type": "02-classification-parse",
 "contract_version": "1.0",
 "report_id": "14478",
 "provenance": {
  "source_uri": "tensor://reports/14478",
  "source_field": "markdown",
  "source_hash": "sha256:8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0",
  "source_hash_matches": true,
  "title": "CASE-CYLINDER-DRAG-FVM: TensorFVM DFG 2D-1 cylinder drag case (per-quantity <5% verdict)",
  "scenario_key": "case-cylinder-drag-fvm",
  "chars": 6156
 },
 "outputs": {
  "classification.json": {
   "schema": "classification.v1",
   "package_id": "wp-14478-02",
   "task_type": "02-classification-parse",
   "report_id": "14478",
   "generated_at": "2026-11-14T00:00:00+00:00",
   "objective": {
    "classify_report_type": true,
    "register_assets": false,
    "extract_claims": false
   },
   "source": {
    "uri": "tensor://reports/14478",
    "field": "markdown",
    "contract_hash": "sha256:8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0",
    "recomputed_hash": "sha256:8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0",
    "source_hash_matches": true,
    "chars": 6156,
    "bytes_utf8": 9430,
    "lines": 145,
    "title": "CASE-CYLINDER-DRAG-FVM: TensorFVM DFG 2D-1 cylinder drag case (per-quantity <5% verdict)",
    "scenario_key": "case-cylinder-drag-fvm",
    "snapshot_path": "docs/kf/wp-14478-02/source/report_14478.md",
    "fetched_via": "byte snapshot of platform API markdown field"
   },
   "layer": {
    "family": "CASE-CYLINDER-DRAG-FVM",
    "scenario_key": "case-cylinder-drag-fvm",
    "tier": "m"
   },
   "report_type": {
    "id": "scientific-computation",
    "chosen_skill_id": "xsk-scientific-computation",
    "skill_version": "0.1.0",
    "skill_lifecycle_state": "template-created",
    "confidence": "medium",
    "decision_basis": "按 extraction-skills/<type>.md §1 的 identify_signals 逐条判定：scientific-computation 5 条中 3 条 matched（discretisation / convergence study / mesh refinement）、2 条 partial（governing equation / timing table）；最接近的竞争类型 experimental-validation 亦有 1 条 matched（validation case）+ 1 条 partial（baseline comparison），但其三条定义性信号全缺；其余四型无 matched。故类型取 scientific-computation，置信 medium（因竞争类型存在 matched 信号）。注意：SC 的 convergence/mesh 两条 matched 是**设计层声明**（§⑤ 自述“待计算”），不是“已跑出收敛阶”。",
    "secondary_aspect": [
     {
      "id": "benchmark-verification",
      "note": "与 DFG 2D-1 参考值逐量判 5% 门，属 code verification 而非实验验证",
      "signal_ids": [
       "SIG-EV-02",
       "SIG-SC-03"
      ]
     },
     {
      "id": "honest-fail-report",
      "note": "报告终态为 honest-FAIL（结果未取回），分类针对报告结构/意图，不针对结果",
      "signal_ids": [
       "SIG-ST-01",
       "SIG-ST-02",
       "SIG-ST-03"
      ]
     }
    ],
    "candidates": [
     {
      "id": "scientific-computation",
      "verdict": "accepted",
      "rationale": "注册表 5 条信号：discretisation / convergence study / mesh refinement 3 条 matched，governing equation / timing table 2 条 partial（均记 unresolved）。报告主体是数值算例的求解设定、离散、网格细化与收敛/误差判定——计算类的核心标志齐备。",
      "signal_ids": [
       "SIG-SC-01",
       "SIG-SC-02",
       "SIG-SC-03",
       "SIG-SC-04",
       "SIG-SC-05"
      ]
     },
     {
      "id": "experimental-validation",
      "verdict": "rejected",
      "rationale": "最接近的竞争类型：'validation case' matched、'baseline comparison' partial，但其定义性信号（test matrix / facility description / measurement uncertainty）全部 not_found——对照量来自文献级数值基准而非测量值，故不立型为实验验证。",
      "signal_ids": [
       "SIG-EV-01",
       "SIG-EV-02",
       "SIG-EV-03"
      ]
     },
     {
      "id": "algorithm-implementation",
      "verdict": "rejected",
      "rationale": "无伪码/复杂度/O(·)；'function signature' 只到 partial（三个 CLI 入口名），报告主题不是算法实现本身。",
      "signal_ids": [
       "SIG-AI-01",
       "SIG-AI-02"
      ]
     },
     {
      "id": "software-engineering",
      "verdict": "rejected",
      "rationale": "'changed files' 与 'regression statement' 只到 partial（工件清单 + 一条契约测试记录），无提交引用、无接口变更；工程支撑是交付物而非报告主题。",
      "signal_ids": [
       "SIG-SE-01",
       "SIG-SE-02",
       "SIG-SE-03"
      ]
     },
     {
      "id": "literature-review",
      "verdict": "rejected",
      "rationale": "'bibliography' 仅 partial（1 条基准出处），无综述段，引文密度不达阈值。",
      "signal_ids": [
       "SIG-LR-01",
       "SIG-LR-02",
       "SIG-LR-03"
      ]
     },
     {
      "id": "technical-proposal",
      "verdict": "rejected",
      "rationale": "'design / plan' 只到 partial（§⑤ 的待计算设计属报告内待办），无提案/路线图/规格主体。",
      "signal_ids": [
       "SIG-TP-01",
       "SIG-TP-02"
      ]
     }
    ]
   },
   "signals": [
    {
     "id": "SIG-SC-01",
     "report_type": "scientific-computation",
     "signal": "governing equation",
     "verdict": "partial",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:523-577",
       "start_offset": 523,
       "end_offset": 577,
       "quote": "$\\rho=1$、$\\nu=0.001$ m²/s，$Re_D=U_{mean}D/\\nu=20$ 定常层流",
       "content_hash": "sha256:d953ceaa992596ad63f5bd7689036ceb6dbe6d43564a718fee72b94fefa09410"
      }
     ],
     "unresolved": {
      "reason": "正文只给出物性、Reynolds 定义与“定常层流”定性声明，没有写出控制方程的显式形式；把基准名/文献标题当作方程来源即为推断，故记 partial。",
      "what_would_resolve": "原文写出连续性/动量方程，或明确声明所求解的方程（如“求解不可压 N–S 方程”）。"
     }
    },
    {
     "id": "SIG-SC-02",
     "report_type": "scientific-computation",
     "signal": "discretisation",
     "verdict": "matched",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:1645-1668",
       "start_offset": 1645,
       "end_offset": 1668,
       "quote": "贴体网格 + SIMPLE/Rhie–Chow",
       "content_hash": "sha256:285fd00653fe04ea2ea76417100c0a6f03f8b99d8cb64e25af89043694cabedb"
      }
     ]
    },
    {
     "id": "SIG-SC-03",
     "report_type": "scientific-computation",
     "signal": "convergence study",
     "verdict": "matched",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:4346-4384",
       "start_offset": 4346,
       "end_offset": 4384,
       "quote": "Richardson 外推 $C_{D,\\infty}$、最细网格 GCI；",
       "content_hash": "sha256:c466e2076d3435cfd9d1aba1dc5742d8abbfc97713a047cb4575592f660feb3b"
      },
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:3566-3632",
       "start_offset": 3566,
       "end_offset": 3632,
       "quote": "| 收敛判据 | — | 残差 1e-6 / 迭代上限 1500–3000 | `SolverConfig.tolerance` |",
       "content_hash": "sha256:912d0d17ebfbc07ef69fe5d4a4f81e7dd1be1ab42cf6b0bbcc51c05f53694c1d"
      }
     ]
    },
    {
     "id": "SIG-SC-04",
     "report_type": "scientific-computation",
     "signal": "mesh refinement",
     "verdict": "matched",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:4262-4311",
       "start_offset": 4262,
       "end_offset": 4311,
       "quote": "1. **网格细化**：64×24 → 128×48 → 256×96（级距减半），输出观测收敛阶",
       "content_hash": "sha256:5a0ae839b81d35fe6854c4cea4cecfa0550de8770c190d86190149c28fe5bfd0"
      }
     ]
    },
    {
     "id": "SIG-SC-05",
     "report_type": "scientific-computation",
     "signal": "timing table",
     "verdict": "partial",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:4080-4137",
       "start_offset": 4080,
       "end_offset": 4137,
       "quote": "控制面（99）实测不可承担：64×24 网格 200 次迭代 >120 s（shell 单次上限），无法本地兜底。",
       "content_hash": "sha256:7a1e766bbbb7e71f0a9069119fe9449c4cc92b6458faf5e32854e5d99f2a7955"
      }
     ],
     "unresolved": {
      "reason": "原文只有一处单点耗时陈述（200 次迭代 >120 s），没有按网格/作业列出的耗时表。",
      "what_would_resolve": "原文出现逐网格或逐作业的耗时表。"
     }
    },
    {
     "id": "SIG-EV-01",
     "report_type": "experimental-validation",
     "signal": "validation case",
     "verdict": "matched",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:343-388",
       "start_offset": 343,
       "end_offset": 388,
       "quote": "二维通道内静止圆柱绕流（Schäfer & Turek 1996 基准，DFG 2D-1）",
       "content_hash": "sha256:671d974319c2bfd4c84166894e88e8b63302111fed205ba688523d4fdd6ed25b"
      }
     ]
    },
    {
     "id": "SIG-EV-02",
     "report_type": "experimental-validation",
     "signal": "baseline comparison",
     "verdict": "partial",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:239-303",
       "start_offset": 239,
       "end_offset": 303,
       "quote": "**判据（先于计算声明）**：三个参考量（$C_D$、$C_L$、$p_{diff}$）在**最细网格**上相对误差均 <5%，",
       "content_hash": "sha256:ac41f907d8ba7a9ca97942b7df98866d529188da5fe6269138a81de6728fbd31"
      },
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:3634-3678",
       "start_offset": 3634,
       "end_offset": 3678,
       "quote": "## ④ 对照表（ref vs got + 逐项误差）—— **FAIL：无 got**",
       "content_hash": "sha256:cdd52fa50bcd264106d522e2131638c5ddc6f330fd4a503a393adaae5a70bd1a"
      }
     ],
     "unresolved": {
      "reason": "对照表结构齐全（有基准侧 ref），但 got 侧全为“未取回”，比较的另一侧不存在。",
      "what_would_resolve": "对照表填入任一网格档的 C_D/C_L/p_diff 实测值。"
     }
    },
    {
     "id": "SIG-EV-03",
     "report_type": "experimental-validation",
     "signal": "test matrix / facility description / measurement uncertainty",
     "verdict": "not_found",
     "evidence": [],
     "unresolved": {
      "reason": "全文无实验装置、试验矩阵、测量不确定度；对照量取自文献级数值基准参考值，不是测量值（成本类报告与实验验证型的分界）。",
      "what_would_resolve": "原文出现设施/工况矩阵/测量不确定度任一项。"
     }
    },
    {
     "id": "SIG-AI-01",
     "report_type": "algorithm-implementation",
     "signal": "pseudocode block / complexity statement / `O(` in results section",
     "verdict": "not_found",
     "evidence": [],
     "unresolved": {
      "reason": "原文无伪码块、无复杂度陈述、结果段无 O(·) 记号；壁面重构只作方法性描述。",
      "what_would_resolve": "原文出现伪码、复杂度或 O(·) 量级陈述。"
     }
    },
    {
     "id": "SIG-AI-02",
     "report_type": "algorithm-implementation",
     "signal": "function signature",
     "verdict": "partial",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:1761-1819",
       "start_offset": 1761,
       "end_offset": 1819,
       "quote": "本单新增算例级 harness `scripts/case_cylinder_drag_fvm.py`（三个入口）：",
       "content_hash": "sha256:be4f56fe08b9e82214286d88a03a10e728f463d90b2a88cfc6848131395d91b7"
      }
     ],
     "unresolved": {
      "reason": "原文只列三个 CLI 入口名（solve/analyze/report），未给函数签名、参数类型或返回契约。",
      "what_would_resolve": "原文给出函数/接口签名与参数、返回契约。"
     }
    },
    {
     "id": "SIG-SE-01",
     "report_type": "software-engineering",
     "signal": "changed files",
     "verdict": "partial",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:4897-4916",
       "start_offset": 4897,
       "end_offset": 4916,
       "quote": "工件（worktree 内真实路径）：",
       "content_hash": "sha256:5f1f3e2d1da5786df787fd6bbe7f58b38a454b2de53e83f0aba559ee32ed6204"
      }
     ],
     "unresolved": {
      "reason": "§⑥ 以工件清单形式提到文件路径，但不是变更集（无 diff、无受影响模块、无提交引用）。",
      "what_would_resolve": "原文给出变更文件列表及提交号/差异摘要。"
     }
    },
    {
     "id": "SIG-SE-02",
     "report_type": "software-engineering",
     "signal": "regression statement",
     "verdict": "partial",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:5302-5358",
       "start_offset": 5302,
       "end_offset": 5358,
       "quote": "`pytest tests/test_case_cylinder_drag_fvm.py` → 1 passed",
       "content_hash": "sha256:464e17f4df1d15897d79f56e033ebabfa228b6305a4e9b1a38ad6f534a9247ee"
      }
     ],
     "unresolved": {
      "reason": "仅一条合成数据契约测试通过记录；无回归范围、无对既有行为的保护陈述，且非物理结果。",
      "what_would_resolve": "原文给出回归测试范围与受影响既有行为。"
     }
    },
    {
     "id": "SIG-SE-03",
     "report_type": "software-engineering",
     "signal": "commit reference / interface/API change",
     "verdict": "not_found",
     "evidence": [],
     "unresolved": {
      "reason": "原文无提交号、无接口/API 变更叙述；缺陷修复与会话过程被明确排除在报告内容外。",
      "what_would_resolve": "原文出现 commit 引用或 API 变更说明。"
     }
    },
    {
     "id": "SIG-TP-01",
     "report_type": "technical-proposal",
     "signal": "proposal / roadmap / specification",
     "verdict": "not_found",
     "evidence": [],
     "unresolved": {
      "reason": "无提案、路线图或规格章节；§⑤ 的后续步骤属同一算例的待办，不构成对外提案。",
      "what_would_resolve": "原文出现提案/路线图/规格章节。"
     }
    },
    {
     "id": "SIG-TP-02",
     "report_type": "technical-proposal",
     "signal": "design / plan",
     "verdict": "partial",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:4218-4260",
       "start_offset": 4218,
       "end_offset": 4260,
       "quote": "设计已完成、待数据即可出数（`analyze` 已实现并已用合成数据契约测试验证）：",
       "content_hash": "sha256:bc728d1c42457cdbd7fbeb9e34043de0ba8098f2380a152aebb55360af9f49d5"
      }
     ],
     "unresolved": {
      "reason": "§⑤ 有一节“待计算”的设计/计划文字，但它是报告内部待办，不是报告的主目的。",
      "what_would_resolve": "该设计/计划成为报告主体并提出面向他方的行动项。"
     }
    },
    {
     "id": "SIG-LR-01",
     "report_type": "literature-review",
     "signal": "bibliography",
     "verdict": "partial",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:1046-1120",
       "start_offset": 1046,
       "end_offset": 1120,
       "quote": "Turek & Schaefer, *Benchmark computations of laminar flow around cylinder*",
       "content_hash": "sha256:e72fcaf5c1d1d67ee4be05afbec27c8dd50da28808e0cc3909fc817537e6f95b"
      }
     ],
     "unresolved": {
      "reason": "全文只有 1 条文献条目（基准原始出处，并转引 Nabh 1998 preprint）；不构成文献目录。",
      "what_would_resolve": "原文出现多条独立文献条目构成的目录。"
     }
    },
    {
     "id": "SIG-LR-02",
     "report_type": "literature-review",
     "signal": "related work / state of the art / survey",
     "verdict": "not_found",
     "evidence": [],
     "unresolved": {
      "reason": "无相关工作/综述段；文献引用只用于确立参考值出处。",
      "what_would_resolve": "原文出现 related work 或综述段。"
     }
    },
    {
     "id": "SIG-LR-03",
     "report_type": "literature-review",
     "signal": "citation density >= 5 per 1000 chars",
     "verdict": "not_found",
     "evidence": [],
     "unresolved": {
      "reason": "6156 字符正文仅有 1 条文献条目（见 SIG-LR-01），密度远低于 5/1000 字符；本工序未做机器引文计数，只按可见条目判定。",
      "what_would_resolve": "机器引文计数达到阈值。"
     }
    },
    {
     "id": "SIG-ST-01",
     "report_type": "(report-status)",
     "signal": "honest-FAIL verdict",
     "verdict": "matched",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:75-134",
       "start_offset": 75,
       "end_offset": 134,
       "quote": "> 状态：**honest-FAIL / fail_stage = compute_wait（集群排队未取回结果）**",
       "content_hash": "sha256:5ac067e0ac7120e39cda7bd0c182a54bae94954c2752a786f2fd927ec9378e32"
      }
     ]
    },
    {
     "id": "SIG-ST-02",
     "report_type": "(report-status)",
     "signal": "results absent (no got)",
     "verdict": "matched",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:3812-3859",
       "start_offset": 3812,
       "end_offset": 3859,
       "quote": "| 64×24 | 未取回 | — | 未取回 | — | 未取回 | — | ❌ 无数据 |",
       "content_hash": "sha256:b87ffaef83c7fb85f4369fe8bb1957abff1d26a523bd2d5b0997f5bda284bc54"
      }
     ]
    },
    {
     "id": "SIG-ST-03",
     "report_type": "(report-status)",
     "signal": "failure cause: queue wait",
     "verdict": "matched",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:3972-4023",
       "start_offset": 3972,
       "end_offset": 4023,
       "quote": "三个作业递交后一直处于 `queued` 状态（递交 23:22 UTC 时队列前方 312 个作业；",
       "content_hash": "sha256:d961ca612fef424d70000100086473322d8bb710910b0637a4c8bfdbd4769007"
      }
     ]
    }
   ],
   "topics": [
    {
     "id": "TOP-DOM-01",
     "tag": "阻力 / drag (C_D)",
     "scheme": "subject-domain",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:642-702",
       "start_offset": 642,
       "end_offset": 702,
       "quote": "| $C_D$ | 5.57953523384 | DFG 2D-1 官网页 “Reference results” |",
       "content_hash": "sha256:b86abb96229f794417799f9f794bc8fe4edeae5b8a2a165a4f4e61a630ef1970"
      }
     ]
    },
    {
     "id": "TOP-DOM-02",
     "tag": "圆柱绕流 / flow around a cylinder",
     "scheme": "subject-domain",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:343-388",
       "start_offset": 343,
       "end_offset": 388,
       "quote": "二维通道内静止圆柱绕流（Schäfer & Turek 1996 基准，DFG 2D-1）",
       "content_hash": "sha256:671d974319c2bfd4c84166894e88e8b63302111fed205ba688523d4fdd6ed25b"
      }
     ]
    },
    {
     "id": "TOP-DOM-03",
     "tag": "定常层流 / steady laminar, Re_D=20",
     "scheme": "subject-domain",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:3422-3459",
       "start_offset": 3422,
       "end_offset": 3459,
       "quote": "| Reynolds（直径） | $Re_D$ | 20 | 算例定义 |",
       "content_hash": "sha256:f0289666c655912b06db9c5904bdf30d76f34158c1345973d53148d5a84ab22f"
      }
     ]
    },
    {
     "id": "TOP-MTH-01",
     "tag": "有限体积 + SIMPLE/Rhie–Chow",
     "scheme": "method",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:1645-1668",
       "start_offset": 1645,
       "end_offset": 1668,
       "quote": "贴体网格 + SIMPLE/Rhie–Chow",
       "content_hash": "sha256:285fd00653fe04ea2ea76417100c0a6f03f8b99d8cb64e25af89043694cabedb"
      }
     ]
    },
    {
     "id": "TOP-MTH-02",
     "tag": "网格收敛 / Richardson / GCI",
     "scheme": "method",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:4262-4311",
       "start_offset": 4262,
       "end_offset": 4311,
       "quote": "1. **网格细化**：64×24 → 128×48 → 256×96（级距减半），输出观测收敛阶",
       "content_hash": "sha256:5a0ae839b81d35fe6854c4cea4cecfa0550de8770c190d86190149c28fe5bfd0"
      }
     ]
    },
    {
     "id": "TOP-STS-01",
     "tag": "honest-FAIL / compute_wait",
     "scheme": "status",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:75-134",
       "start_offset": 75,
       "end_offset": 134,
       "quote": "> 状态：**honest-FAIL / fail_stage = compute_wait（集群排队未取回结果）**",
       "content_hash": "sha256:5ac067e0ac7120e39cda7bd0c182a54bae94954c2752a786f2fd927ec9378e32"
      }
     ]
    },
    {
     "id": "TOP-PLT-01",
     "tag": "集群排队 / 调度不确定性",
     "scheme": "platform",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:4817-4869",
       "start_offset": 4817,
       "end_offset": 4869,
       "quote": "4. **排队/调度不确定性**：本单即被队列阻塞——重算依赖集群派发，算例池批量铺开时这是系统性风险，",
       "content_hash": "sha256:c56a0701c635d35d4c852cac9513e39139678931528482bf3039e44e89e9cd56"
      }
     ]
    },
    {
     "id": "TOP-PLT-02",
     "tag": "平台缺项：知识检索离线 / oss_solutions 无端点",
     "scheme": "platform",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:5523-5588",
       "start_offset": 5523,
       "end_offset": 5588,
       "quote": "1. **knowledge_base 检索引擎离线**：`/api/v1/tensor/knowledge/search` 返回",
       "content_hash": "sha256:11bbd8d73507fcc8b878aa6d3f4ec0c104995a94329d365d6a164e61229a7c65"
      }
     ]
    },
    {
     "id": "TOP-TLS-01",
     "tag": "算例 harness / 契约测试",
     "scheme": "tooling",
     "evidence": [
      {
       "locator_type": "char_offsets",
       "value": "report_14478.md#chars:1761-1819",
       "start_offset": 1761,
       "end_offset": 1819,
       "quote": "本单新增算例级 harness `scripts/case_cylinder_drag_fvm.py`（三个入口）：",
       "content_hash": "sha256:be4f56fe08b9e82214286d88a03a10e728f463d90b2a88cfc6848131395d91b7"
      }
     ]
    }
   ],
   "structure": {
    "offsets_basis": "以 UTF-8 解码后的 markdown 字符为下标，0 基，end 开区间；分段由 '#' 起始行切分，首尾相接覆盖全文。",
    "sections": [
     {
      "id": "SEC-01",
      "level": 1,
      "heading": "CASE-CYLINDER-DRAG-FVM: DFG 2D-1 圆柱阻力算例（TensorFVM）—— honest-FAIL（计算未取回）",
      "start_offset": 0,
      "end_offset": 328,
      "fills_report": true
     },
     {
      "id": "SEC-02",
      "level": 2,
      "heading": "① 问题与参考值出处",
      "start_offset": 328,
      "end_offset": 1577,
      "fills_report": true
     },
     {
      "id": "SEC-03",
      "level": 2,
      "heading": "② 方法与实现（已完成的真实部分）",
      "start_offset": 1577,
      "end_offset": 3063,
      "fills_report": true
     },
     {
      "id": "SEC-04",
      "level": 2,
      "heading": "③ 参数表（无量纲数完整）",
      "start_offset": 3063,
      "end_offset": 3634,
      "fills_report": true
     },
     {
      "id": "SEC-05",
      "level": 2,
      "heading": "④ 对照表（ref vs got + 逐项误差）—— **FAIL：无 got**",
      "start_offset": 3634,
      "end_offset": 4186,
      "fills_report": true
     },
     {
      "id": "SEC-06",
      "level": 2,
      "heading": "⑤ 收敛性/参数敏感性 —— **FAIL：待计算**",
      "start_offset": 4186,
      "end_offset": 4545,
      "fills_report": true
     },
     {
      "id": "SEC-07",
      "level": 2,
      "heading": "⑥ 失败模式与工件",
      "start_offset": 4545,
      "end_offset": 5509,
      "fills_report": true
     },
     {
      "id": "SEC-08",
      "level": 2,
      "heading": "生态摩擦（如实记）",
      "start_offset": 5509,
      "end_offset": 6156,
      "fills_report": true
     }
    ]
   },
   "uncertainty": [
    "类型判定口径=extraction-skills/<type>.md §1 的 identify_signals 文本是否存在；该注册表生命周期为 template-created（尚无真实代表报告跑通全线），故“matched”是信号文本层面的判定，未经产线校准。",
    "SIG-SC-03（convergence study）与 SIG-SC-04（mesh refinement）的 matched 指原文**声明了**该做法：§⑤ 自述为“仅设计、待数据”；本工序不判断其是否已执行，也不补写收敛阶/GCI。",
    "experimental-validation 是最接近的竞争类型（'validation case' 亦 matched——本算例确实是一个基准算例），故 confidence 取 medium 而非 high；区分依据是其三条定义性信号全缺，且对照侧为文献数值基准。",
    "报告终态 honest-FAIL（④ 对照表无 got）：分类判定的是报告**意图与结构**，不评价结果是否达标；本工序不产生、不传播任何 C_D/C_L/p_diff 的结果数字。",
    "SIG-SC-01（governing equation）与 SIG-SC-05（timing table）仅 partial、SIG-EV-02（baseline comparison）仅 partial，均已显式记 unresolved；不补写方程或耗时表。",
    "主题标签（topics）只作检索用：每条都锚在原文逐字引文上，但标签名本身是人工命名的检索词，非原文用语。",
    "structure.sections 由行首 '#' 切分得到，未做代码栅栏感知；本报告代码块内无行首 '#'（已由自检的段连续性断言覆盖），但同一解析器用于其它报告时可能把栅栏内 '#' 误切为小节。",
    "类型判定的语义正确性无法机检：测试只验证可机检的不变量（哈希、偏移、唯一性、schema、确定性），“这份报告该不该判为 scientific-computation”仍需 04 工序/人工复核。",
    "schema_pass 依据本仓新增的 schemas/classification.v1.schema.json：平台侧 kf_result.v1 只把 outputs.classification.json 声明为无约束 object，没有官方 02 产物 schema，故本次校验是自建 schema 自查。"
   ],
   "verification": {
    "epistemic_status": "draft",
    "assessment_status": "unassessed",
    "verification_performed_by_producer": false,
    "note": "verification 由平台门计算；本产物不自行判定为 verified。"
   }
  }
 }
}
```
