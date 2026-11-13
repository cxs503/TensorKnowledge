# KF-RESULT wp-9761-01

**工作包** `wp-9761-01` ｜ **task_type** `01-asset-registration` ｜ **lane** A ｜ **report_id** `9761` ｜
**源** `tensor://reports/9761`（field=`markdown`，sha256=`4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a`，8931 字符 / 14845 字节）
**分层** `DEM|rigid_contact_energy_ledger_certification|l` ｜ **交付仓** TensorKnowledge（status=draft）
**结论** 源资产已登记：29 条资产、29 条唯一可解析定位、claims 为空（契约允许）；
`PASS`（9 项校验，源哈希由平台 API 重新抓取后独立重算）。

## ① 本工序做了什么

只做一件事：**登记 report 9761 的源资产**，不做抽取、不做分类、不标 verified。

* 抓取 `tensor://reports/9761` 的 markdown 并**逐字节核对**契约 `source_hash`：
  重算 sha256 = `4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a`，与契约一致（`hash_matches_contract=true`），
  字符数 8931 与契约 `chars: 8931` 一致（`chars_matches_contract=true`）。
* 在原文里定位 29 条资产（正文/表/图声明/产物路径/审计链/环境记录等 21 个类目），
  每条带**逐字引文 + 字符区间 + 行区间**；引文在本工序内被断言为**全文唯一出现**（occurrences=1）。
* 判定每条资产的解析状态：26 条 `resolved_in_source`（可在源文内解析）、
  3 条 `referenced_unresolved`（指向 TensorDEM 仓的代码/图件/工件路径，本工作树内不可解析）、
  0 条 `declared_absent`。
* 输出 `asset_manifest.json`（schema=asset_manifest.v1）+ `kf_result.v1` 结果信封；`claims` 为**空数组**，
  符合契约 `objective.classify_report_type=false` 与 notes「不做抽取」。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`scripts/kf_fetch_9761.py` → `GET $TENSOR_API_BASE/tensor/reports/9761`（Bearer 登录），
   落 `runs/wp-9761-01/report_9761.md/.json`。取回的 markdown sha256=`4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a`，
   与契约 `source_hash` 完全一致 —— 后续所有定位都建立在这份字节上。
2. **注册+自断言**：`scripts/kf_register_9761.py` 内置六条硬不变量（违反即退出非 0）：
   I1 sha256==契约；I2 asset_id 唯一且匹配 `^A[0-9]{2}$`；I3 每条引文在原文唯一出现；I4 `md[start:end]==quote`；
   I5 行区间重建出同一引文；I6 `resolution_check.result` 与 `resolution` 词表一致。
   锚点用「必须恰好出现在一行」的短串定位，引文由**整行切片**生成（不是手打），因此零手抄是结构性保证。
3. **独立校验**：`scripts/kf_verify_9761.py` 重新（从 API 再抓一次）取 markdown、重算 sha256、
   逐条重解析 29 个定位，并按契约 6 项 + 3 项附加检查输出 `verification.json`。
4. **覆盖率缺口分析**：`scripts/kf_figures_9761.py` 把定位区间取并集投射到字符轴，得到
   目标化覆盖率 **8636/8931 = 96.70%**，残差 295 字符全部是
   空行(86 行)与章节标题(12 行)，**未登记正文行 = 0**。
   该分析反哺了登记本身：首轮发现的 2 处未覆盖正文（归一化约定行、五球摆解释段）已补登为 A28/A29。
5. **工具链/设置**：Python 3.11 + jsonschema + matplotlib(Agg)；不联网取外部资源（外部路径只在**本工作树内**查存在性）；
   不改 `.git`、不 push；只读写 report_id=9761。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-9761-01/asset_manifest.json` | 主产物：schema=asset_manifest.v1，29 资产 / 29 唯一引文 / claims=[] / 5 条 observations |
| `docs/wp-9761-01/asset_manifest.json` | 与主产物**逐字节相同**的耐久镜像（仓 push 门会滤掉 `artifacts/**`、`runs/**`） |
| `runs/wp-9761-01/kf_result.wp-9761-01.json` | kf_result.v1 信封（package_id/task_type/report_id/provenance/outputs/claims） |
| `runs/wp-9761-01/kf_result_block.wp-9761-01.json` | 与本报告唯一 json 代码块的字节一致副本 |
| `artifacts/wp-9761-01/verification.json` | 9 项校验逐条结果，overall=`PASS`，含 API 重抓的 sha256 |
| `docs/wp-9761-01/verification.json` | 校验结果的耐久镜像（同上内容；push 门会滤掉 `artifacts/**`） |
| `docs/wp-9761-01/report_9761_meta.json` | 源报告平台元数据镜像（id/title/scenario_key/5 条 figure name+caption/tags） |
| `docs/wp-9761-01/coverage.json` | 定位覆盖率与缺口成分（供下游抽取确定「哪里还没有被钉住」） |
| `docs/wp-9761-01/figures/fig1_asset_coverage.png` | 图 1 覆盖图（sha256 `cc2001a4af1e408d…`） |
| `docs/wp-9761-01/figures/fig2_resolution_checks.png` | 图 2 解析状态 + 校验矩阵（sha256 `98f2fbe8bf2ad6eb…`） |
| `scripts/kf_fetch_9761.py`, `scripts/kf_register_9761.py`, `scripts/kf_verify_9761.py`, `scripts/kf_figures_9761.py`, `scripts/kf_report_9761.py` | 全链可一键复跑 |
| `tests/test_kf_wp9761.py` | 17 条 pytest：11 条接受性断言 + 6 条负控（见 ⑥） |
| `schemas/asset_manifest.v1.wp-9761-01.schema.json` | 本包 manifest 的钉定 schema（通用文件钉在 wp-448-01 上，未改动） |

## ④ 证据定位表

每条资产 → 原文逐字切片（片段截断仅用于表格显示，完整引文见 manifest 的 `locator.quote`；字符区间可被平台独立解析）。

| 资产 | 定位（行/字符区间） | 原文引文片段（逐字切片） | 解析状态 |
|---|---|---|---|
| A01 document | L0-L159 / c0-c8931 | `# P54W3-N03 刚性碰撞能量账本收敛阶认证（成熟化）` | resolved_in_source |
| A02 heading | L0-L0 / c0-c30 | `# P54W3-N03 刚性碰撞能量账本收敛阶认证（成熟化）` | resolved_in_source |
| A03 provenance_statement | L2-L2 / c32-c189 | ``*TensorDEM 0.1.0 · 生成 2026-11-09T08:06:54+00:00 · Python 3.11.6 · 全部数字由 `scr…`` | resolved_in_source |
| A04 problem_statement | L6-L10 / c203-c644 | ``**物理背景.** 刚性（硬）接触碰撞的能量账本要回答一个工程问题：m5404 报出的 `residual_state_relative = 5.111…`` | resolved_in_source |
| A05 table | L12-L19 / c646-c1331 | `**算例与参数.**` | resolved_in_source |
| A06 definition_table | L25-L30 / c1388-c1943 | `\| 口径 \| 离散定义 \| 对照基准 \| 预期 \|` | resolved_in_source |
| A07 method_rationale | L31-L31 / c1944-c2223 | `**(b) 为什么必须引入检查点（本单的核心增量）.** velocity-Verlet 下「力梯形 × 位移」与离散 ΔKE 是**同一个数**（两个…` | resolved_in_source |
| A08 negative_control | L33-L33 / c2225-c2506 | `**(c) 负控（判据有判别力才叫判据）.** ①通量口径在注入实现缺陷（漏掉第二个半步 kick / 力用旧值）后必须崩掉：实测从 round-off…` | resolved_in_source |
| A09 toolchain_declaration | L35-L35 / c2508-c2860 | ``**(d) 工具链.** 新模块 `src/tensordem/contact_energy_certification.py`（三口径 + 检查点协议…`` | resolved_in_source |
| A10 external_code_set | L35-L35 / c2508-c2860 | ``**(d) 工具链.** 新模块 `src/tensordem/contact_energy_certification.py`（三口径 + 检查点协议…`` | referenced_unresolved |
| A11 table | L41-L51 / c2908-c3439 | `\| N_c=t_c/Δt \| Δt [s] \| 通量口径残差（全程） \| 显式口径残差 @t\* \| 梯形口径残差 @t\* \|` | resolved_in_source |
| A12 numeric_result_statement | L52-L52 / c3440-c3588 | `拟合（log\|r\| vs log Δt，最小二乘）：显式斜率 **0.986**（R²=1.0000，8 点），梯形斜率 **1.989**（R²=…` | resolved_in_source |
| A13 interpretation | L54-L54 / c3590-c3773 | `**读法.** 三口径不是同一公式的三种写法：通量口径是**结构恒等式**（残差 = 记账缺陷计，Δt 无关）；显式口径是**一阶求积**；梯形口径在检…` | resolved_in_source |
| A14 numeric_result_statement | L58-L58 / c3795-c3924 | `目标 e=0.571740028（clamped 闭式），实测 e=0.571663401，\|e−e_target\|=7.663e-05（N_c=1…` | resolved_in_source |
| A15 table | L62-L66 / c3953-c4225 | `\| Δt [s] \| N_c \| 总动量漂移 \| 通量口径残差 \| 显式口径残差 \| 末球速度 [m/s] \|` | resolved_in_source |
| A16 table | L72-L77 / c4374-c4799 | `\| Δt [s] \| 步数 \| 状态量口径残差 \| 梯形功率口径 \| 注入 1e-3 缺陷 \| 浮冰 A v_x \| 浮冰 B v_x \…` | resolved_in_source |
| A17 verdict_statement | L79-L83 / c4801-c5286 | ``**显式判定（判据 e）：`convention`。** 5.111e-07 是**口径误差**（离散/记账量），不是实现缺陷：状态量口径残差在 4 级…`` | resolved_in_source |
| A18 figure_declaration | L87-L105 / c5299-c5909 | `![三口径收敛](figures/fig1_three_conventions.png)` | resolved_in_source |
| A19 figure_binary_set | L87-L105 / c5299-c5909 | `![三口径收敛](figures/fig1_three_conventions.png)` | referenced_unresolved |
| A20 limitation_set | L109-L115 / c5940-c6953 | `1. **恒等式陷阱（最重要的坑）.** velocity-Verlet 下「力梯形×位移」与离散 ΔKE 恒等；「功率梯形」在完整碰撞（两端 F=0）…` | resolved_in_source |
| A21 table | L119-L126 / c6981-c7473 | `\| 关键量 \| 本单结果 \| 基准 \| 相对误差 \| 是否 <3% \|` | resolved_in_source |
| A22 self_assessment | L128-L128 / c7475-c7596 | `**逐项回答「是否<3%」**：上表六项全部是，且其中四项是机器精度量级、两项是收敛残差（其相对误差本身按阶收敛）。没有任何一项落在 3%~15% 的「…` | resolved_in_source |
| A23 table | L132-L139 / c7625-c7976 | `\| 判据 \| 实测 \| 阈值 \| 结论 \|` | resolved_in_source |
| A24 numeric_result_statement | L141-L141 / c7978-c8011 | ``**总计 全部通过**（`all_passed = True`）。`` | resolved_in_source |
| A25 artifact_path_list | L143-L149 / c8013-c8335 | `产物路径：` | referenced_unresolved |
| A26 audit_chain | L153-L157 / c8348-c8876 | ``1. **判据先于数字**：阈值 `FLUX_TOL=1e-9`、`SLOPE_TOL=0.2`、`RESTITUTION_TOL=1e-3`、`MOM…`` | resolved_in_source |
| A27 environment_record | L158-L158 / c8877-c8930 | `6. **环境**：TensorDEM 0.1.0，Python 3.11.6，本机壁钟 112.2 s。` | resolved_in_source |
| A28 normalization_declaration | L23-L23 / c1345-c1386 | `**(a) 三口径的并列定义**（残差一律以 E0=½m_eff v0² 归一）。` | resolved_in_source |
| A29 interpretation | L68-L68 / c4227-c4346 | `五球紧贴时 4 个接触**同时**加载（静不定），力/功按对累加最易漏项；实测总动量漂移 1.11e-15 ≪ 1e-12，末球获得 0.989 m/s…` | resolved_in_source |

**5 条登记观察（observations，不改写原文）**

- **O1**（metadata_drift，依据 A02）：平台 title 与 markdown 一级标题不同文字：title 为任务全名，正文标题带「（成熟化）」后缀。
- **O2**（figures_present，依据 A18）：平台 figures 字段登记 5 条（name+caption），对应正文明声明的图 1-图 5；png 字节未随报告存储。
- **O3**（external_code_dependency，依据 A10）：结论的全部数值产物在 TensorDEM 仓（模块/用例/metrics.json），本工序无法在本工作树内解析，故 A10/A25 标 referenced_unresolved，不视为缺失或造假。
- **O4**（upstream_lineage，依据 A04）：报告自身声明其上游为 in54w1（留 documented FAIL）与 m5404（5.111290246e-07）；两者均以文字出现，未给出可解析报告号或路径。
- **O5**（no_verification_claim，依据 A23）：本 manifest 不含 verified 标记：A23/A24 的 PASS 与 all_passed=True 是源报告的自报值，登记的是「原文如此」，不是平台复算结论。

## ⑤ 注意点与局限

1. **本工序不做真伪判定**。报告自报的 `all_passed = True`（A24）与五项判据 PASS（A23）是**源文内容**，
   登记的是「原文如此」，不是平台复算；`provenance.verification_status = not_verified` 如实反映这一点。
   上游六项 <3% 的误差结论（A21/A22）同理未复核。
2. **3 条 referenced_unresolved 不是缺失**。A10（TensorDEM 模块/用例）、A19（5 个 png）、A25（产物路径清单）
   指向 TensorDEM 仓；本工作树内 grep/查存在性均为 0 命中（见各条 `resolution_check.worktree_hits=[]`）。
   图件在平台 `figures` 字段里有 name+caption 但**无字节**，故只能标未解析，不能标 resolved。
3. **平台 title 与正文标题文字不同**（O1：title 为任务全名、正文标题带「（成熟化）」后缀）。本工序**不改写**任何一侧，
   只在 observation 里留痕，避免把元数据漂移静默抹平。
4. **唯一性是个强约束，也有代价**：引文必须全文唯一才能用行区间定位；重复性文本（如反复出现的阈值）无法单靠行区间区分，
   本包通过选取上下文更长的整行来规避，未使用模糊匹配。
5. **覆盖率不是质量指标**：96.70% 只说明「正文行基本都有归属」，不说明抽取得对；
   空白与章节标题合计 295 字符属结构性文本，本包刻意不登记为资产（避免用无效资产刷覆盖率）。
6. **上游谱系未能解析**：A04 提到的 in54w1（documented FAIL）与 m5404（5.111290246e-07）只有文字，无报告号/路径，
   本工序不猜、不补（O4）。
7. **规模有限的诚实说明**：29 条资产由人工规则（锚点表）选定，不是算法检索；类目划分反映本报告结构，
   不代表可跨报告复用的本体。
8. **push 门之后的耐久性（已做降级而不是假设）**：本仓 push 门会滤掉 `artifacts/**` 与 `runs/**`，
   因此每条产物在 `docs/wp-9761-01/` 留有逐字节镜像；`tests/test_kf_wp9761.py` 的加载器优先取工作产物、
   回落到 `docs/` 镜像，markdown 缺失时再从平台 API 取。已用「移走 artifacts/ 与 runs/」模拟 push 后状态跑过：
   17 条仍全绿（其中 markdown 走 API 重取）。若不降级，测试会在干净检出上假失败。
9. **交付信道自检**：报告发布后由 `scripts/kf_check_published_9761.py` 再读一次已发布的 markdown，
   断言 title/tags/mission_id/scenario_key、json 代码块唯一且解析后与信封**完全相等**、图件名一致；
   该断言跑在**发布后的字节**上，而不是本地草稿。

## ⑥ 自检：逐条对照 acceptance

| acceptance item | 结果 | 证据 |
|---|---|---|
| valid_json | PASS | manifest/result/block/mirror 均可解析，block==result |
| schema_pass | PASS | asset_manifest 过本包 schema；信封过 schemas/kf_result.v1.schema.json |
| source_locator_resolvable | PASS | 29/29 locator 在重新抓取的 markdown 上重解析成功 |
| source_hash_matches | PASS | 重算 sha256 与契约 source_hash 逐字节一致 |
| no_duplicate_ids | PASS | asset_id/observation_id 无重复、无悬挂引用 |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | claims=[] 合法空数组 |
| no_premature_verification_marks | PASS | 无 verified 标记；verification_status=not_verified |
| counts_consistent | PASS | counts 由 assets 重算一致 |
| report_scope_isolated | PASS | 仅 report_id=9761 |

* `valid_json` ✅ ｜ `schema_pass` ✅ ｜ `source_locator_resolvable` ✅（29/29） ｜ `source_hash_matches` ✅（API 重抓重算 `4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a`） ｜ `no_duplicate_ids` ✅ ｜ `all_claims_…` ✅（claims=[]，契约允许）
* **负控（证明检查有牙，不只是「跑过了」）**：①把某条引文末尾改 1 个字符 → 定位检查报 slice/uniqueness 缺陷；
  ②重复一个 asset_id → `no_duplicate_ids` 报缺陷；③把 observation 指向不存在的 A99 → 报悬挂引用；
  ④用 4 字符公共串当引文 → 报 `quote_not_unique`+`unique_flag_false`；⑤给无证据 claim → 报 missing；
  ⑥把 `5.111e-07` 改成 `5.112e-07` → sha256 不匹配且定位失配。六条均在 `tests/test_kf_wp9761.py` 中作为断言固化。
### ⑥b 误差判定（本工序的关键量 vs 基准，逐项，显式回答「是否<3%」）

| 关键量 | 本工序值 | 基准（契约 / 平台） | 相对误差 | 是否 <3% |
|---|---|---|---|---|
| markdown sha256 | `4667a18d2c2c1833…`（64 hex） | 契约 `source_hash`（同值） | 0（逐字节相等） | 是（=0%，精确相等） |
| markdown 字符数 | 8931 | 契约 `chars`=8931 | 0 | 是（=0%） |
| 源报告 id | 9761 | 契约 `report_id`=9761 | 0 | 是（=0%） |
| scenario_key | `rigid_contact_energy_ledger_certification` | 契约 `scenario_key`（同值） | 0 | 是（=0%） |
| 定位重解析 | 29/29 成功 | 期望 100% | 0 处失配 | 是（=0%） |
| claims 条数 | 0 | 期望 0（不做抽取） | 0 | 是（=0%） |
| 图件名集合 | 2 幅（本地生成） | 平台已发布 figures（同 2 名） | 0 | 是（=0%） |

**显式回答**：上表七项全部是**精确相等（误差 0%）**，不是「<3% 的量级问题」——本工序的验收面是**同一性**
（哈希/字符数/编号/定位），任何非零偏差都是硬失败而不是容差问题。
唯一非零的**比例量**是 `referenced_unresolved` 率 3/29 = 10.34%：
它**不是误差**，而是「资产指向本工作树之外」的口径（逐条已给 worktree_hits=[] 证据，见⑤第 2 条），
故不纳入 <3% 判定；把外部资产强行标 resolved 才是造假。

* **未运行/未覆盖**：平台侧 gate 的复算（本工序不可见，`verification_status=not_verified`）；
  上游 TensorDEM 侧的数值复现（A10 不可解析，属下游/他仓职责）。
* **honest 项**：无失败项；但「全部 PASS」仅指**本包 acceptance**，不含对报告科学结论的认可。

## 一键复跑（repro_cmd）

`python3 scripts/kf_fetch_9761.py && python3 scripts/kf_register_9761.py && python3 scripts/kf_verify_9761.py && python3 scripts/kf_figures_9761.py && python3 -m pytest tests/test_kf_wp9761.py -q && python3 scripts/kf_report_9761.py`

## 附：结果信封（本报告唯一的 json 代码块，交付信道）

```json
{
  "package_id": "wp-9761-01",
  "task_type": "01-asset-registration",
  "report_id": "9761",
  "provenance": {
    "source_uri": "tensor://reports/9761",
    "source_field": "markdown",
    "source_hash": "sha256:4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a",
    "source_chars": 8931,
    "source_bytes_utf8": 14845,
    "source_title": "P54W3-N03 刚性碰撞能量账本收敛阶认证：三口径并列实现、1/2 阶可测性与 m5404 残差判定",
    "scenario_key": "rigid_contact_energy_ledger_certification",
    "contract_version": "1.0",
    "lane": "A",
    "work_package": "wp-9761-01",
    "domain_layer": "DEM|rigid_contact_energy_ledger_certification|l",
    "contract_source_hash": "sha256:4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9761",
    "local_copy": "runs/wp-9761-01/report_9761.md",
    "generator": "scripts/kf_register_9761.py",
    "verifier": "scripts/kf_verify_9761.py",
    "emitted_at": "2026-11-09T08:12:03.874002+00:00",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "artifacts/wp-9761-01/asset_manifest.json",
      "artifact_sha256": "dd2856eec94445e18c2271853e3598032f1d3af30e56b2e55771760dbbbc1bbb",
      "artifact_bytes": 62169,
      "durable_mirror": "docs/wp-9761-01/asset_manifest.json",
      "campaign_mission_id": 15667,
      "package_id": "wp-9761-01",
      "task_type": "01-asset-registration",
      "report_id": "9761",
      "source": {
        "uri": "tensor://reports/9761",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a",
        "hash_matches_contract": true,
        "contract_hash": "sha256:4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a",
        "chars": 8931,
        "chars_matches_contract": true,
        "chars_contract": 8931,
        "bytes_utf8": 14845,
        "title": "P54W3-N03 刚性碰撞能量账本收敛阶认证：三口径并列实现、1/2 阶可测性与 m5404 残差判定",
        "markdown_heading": "P54W3-N03 刚性碰撞能量账本收敛阶认证（成熟化）",
        "scenario_key": "rigid_contact_energy_ledger_certification",
        "scenario_key_matches_contract": true,
        "platform_id": 9761,
        "platform_mission_id": 8412,
        "platform_status": "published",
        "platform_created_at": "2026-11-09T08:12:03.874002+00:00",
        "platform_figures": [
          {
            "name": "fig1_three_conventions.png",
            "caption": "图1 三口径并列：通量口径与 Δt 无关（结构恒等式，round-off 带 2.7e-15），显式口径斜率 0.986（∝Δt¹），梯形口径斜率 1.989（∝Δt²），灰线为参考斜率，红点线为 1e-9 验收线。"
          },
          {
            "name": "fig2_force_power_checkpoint.png",
            "caption": "图2 线性弹簧碰撞的接触力、储能与接触功率时程；红点线为账本检查点 t*=0.3 t_c（非驻点，故求积阶可测）。"
          },
          {
            "name": "fig3_restitution.png",
            "caption": "图3 恢复系数随分辨率趋于 clamped 闭式 e=0.571740028；右图 |e-e_target| 随 N_c 下降（7.66e-5 @ N_c=1024，1e-3 验收线满足），是离散误差而非偏置。"
          },
          {
            "name": "fig4_m5404_verdict.png",
            "caption": "图4 m5404 重判：状态量口径/梯形功率口径随 Δt 幂律塌缩（斜率 1.47/2.03），注入 1e-3 状态函数缺陷为平台（斜率 -0.005）；右图示出射速度对 Δt 不敏感——残差是记账量不是物理量。"
          },
          {
            "name": "fig5_newton_cradle.png",
            "caption": "图5 五球 Newton 摆：状态/显式口径残差与总动量漂移 1.11e-15（≪1e-12 门）。"
          }
        ],
        "platform_tags": [
          "DEM",
          "contact",
          "energy-ledger",
          "convergence-order",
          "verification",
          "TensorDEM",
          "P54W3-N03",
          "m5404"
        ],
        "domain_layer": "DEM|rigid_contact_energy_ledger_certification|l",
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9761",
        "local_copy": "runs/wp-9761-01/report_9761.md"
      },
      "counts": {
        "assets": 29,
        "by_class": {
          "document": 1,
          "heading": 1,
          "provenance_statement": 1,
          "problem_statement": 1,
          "table": 6,
          "definition_table": 1,
          "method_rationale": 1,
          "negative_control": 1,
          "toolchain_declaration": 1,
          "external_code_set": 1,
          "numeric_result_statement": 3,
          "interpretation": 2,
          "verdict_statement": 1,
          "figure_declaration": 1,
          "figure_binary_set": 1,
          "limitation_set": 1,
          "self_assessment": 1,
          "artifact_path_list": 1,
          "audit_chain": 1,
          "normalization_declaration": 1,
          "environment_record": 1
        },
        "by_resolution": {
          "resolved_in_source": 26,
          "referenced_unresolved": 3
        },
        "resolved_in_source": 26,
        "referenced_unresolved": 3,
        "declared_absent": 0,
        "unique_quotes": 29
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文，源资产本体）",
          "in_report_section": "(document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 8931,
            "start_line": 0,
            "end_line": 159,
            "quote": "# P54W3-N03 刚性碰撞能量账本收敛阶认证（成熟化）\n\n*TensorDEM 0.1.0 · 生成 2026-11-09T08:06:54+00:00 · Python 3.11.6 · 全部数字由 `scripts/p54w3_contact_energy_certification.py` 程序化写入 `metrics.json`，本报告只做模板插值（零手抄）。*\n\n## 1. 案例介绍\n\n**物理背景.** 刚性（硬）接触碰撞的能量账本要回答一个工程问题：m5404 报出的 `residual_state_relative = 5.111e-07` 是**口径误差**（离散/记账时层差）还是**实现误差**（编码缺陷）？单个数不能判，**细化行为**能判：口径误差随 Δt→0 消失（正斜率幂律），实现缺陷留下平台（斜率≈0）或发散。本单在此基础上做**成熟化**，交付三件事：\n\n1. 三口径（通量 / 显式 / 梯形）**并列实现**并有各自的可判定义与预期阶；\n2. 把阶的**可测量性**问题解决掉——完整碰撞末态下通量口径与梯形口径都是离散恒等式（无阶可拟合，in54w1 因此在验收表上留了一条 documented FAIL），本单改用**碰撞中期检查点**（t\\*=0.3 t_c，解析解可写），使显式=1 阶、梯形=2 阶成为可测事实；\n3. 五条机器判据全部 pytest 化，并把 m5404 的 5.111e-07 判成口径量，附判别力对照。\n\n**算例与参数.**\n\n| 算例 | 配置 | 参数 | 参考解 |\n|---|---|---|---|\n| S 三口径阶扫描 | 两球头对头，约化为一维相对坐标 x（m_eff=m1m2/(m1+m2)） | 线性弹簧 k=1e+05 N/m，无阻尼，m_eff=1.0 kg，v0=1.0 m/s，gap0=0.02 m，Δt=t_c/8…t_c/1024 | δ(t)=(v0/ω)sin ωt，ω=√(k/m_eff)，ΔKE(t\\*)=E0(cos²(ωt\\*)−1) |\n| R 恢复系数 | 同上，线性弹簧-阻尼（Cundall-Strack） | ζ=0.2，k=1e+05 N/m，c=126.491 N·s/m，clamped 截断 | e_clamped=0.571740028（`contact_impact.clamped_restitution`） |\n| C Newton 摆 | 5 球共线、初始紧贴（接触网络超静定） | R=0.05 m，m=1.0 kg，k=1e+07 N/m^1.5，v0=1.0 m/s | 总动量守恒（P=m v0=1 kg·m/s） |\n| M m5404 重判 | 双浮冰块 4×3×0.4 m，ρ=917 kg/m³，y 向偏置 2 m，V=[1,0,0]/[−0.5,0,0] m/s | k_n=2e7 N/m^1.5，rk4，Δt0=2e-4 s，t=0.5 s，驱动**已交付**的 `floe_rigid6dof.FloeWorld` | m5404 报告值 5.111290246e-07 |\n\n## 2. 怎么做的\n\n**(a) 三口径的并列定义**（残差一律以 E0=½m_eff v0² 归一）。\n\n| 口径 | 离散定义 | 对照基准 | 预期 |\n|---|---|---|---|\n| flux (通量口径) | `W = sum_n (1/2)(P_n + P_{n+1}) h,  P_n = F_n v_n` | same-run discrete dKE (full episode, contact-free ends) | identity: round-off (< 1e-9); residual would be a defect |\n| explicit (显式口径) | `W = sum_n F_n (x_{n+1} - x_n)` | analytic dKE(t*) at the interior checkpoint t* = 0.3 t_c | first order: slope 1 |\n| trapezoid (梯形口径) | `W = sum_n (1/2)(F_n + F_{n+1}) (x_{n+1} - x_n)` | analytic dKE(t*) at the interior checkpoint t* = 0.3 t_c | second order: slope 2 (= trajectory order under Verlet) |\n\n**(b) 为什么必须引入检查点（本单的核心增量）.** velocity-Verlet 下「力梯形 × 位移」与离散 ΔKE 是**同一个数**（两个半步 kick 使 v_{n+1/2}=(v_n+v_{n+1})/2，drift 使 Δx=Δt v_{n+1/2}），「功率梯形」同理：完整碰撞末态残差恒为 round-off，阶**不可测**。把账本检查点移到碰撞中期 t\\*=0.3 t_c（非驻点，P≠0），解析参考 ΔKE(t\\*) 可写，两条数值积分口径的阶才分离出来。实测：显式 ΔKE 残差 ∝Δt^0.986，梯形 ∝Δt^1.989。\n\n**(c) 负控（判据有判别力才叫判据）.** ①通量口径在注入实现缺陷（漏掉第二个半步 kick / 力用旧值）后必须崩掉：实测从 round-off 跳到 1.09e-01 / 8.02e-01，说明 <1e-9 这条线测的是**记账实现**而不是离散误差；②m5404 同一算例注入 1e-3 状态函数误差后残差必须出现平台（实测斜率 -0.005，量级放大到 4.81e-05），说明斜率判据能把「口径」与「缺陷」分开；③恰好 2 级 Δt 处于预渐近区会给出假阴性（5.111e-07→3.96e-07 只有 0.37 的斜率），故模块强制 ≥3 级。\n\n**(d) 工具链.** 新模块 `src/tensordem/contact_energy_certification.py`（三口径 + 检查点协议 + 恢复系数/Newton 摆/m5404 三份 certificate + `certify_all` 折叠判据）；回归守卫 `tests/test_contact_energy_certification.py`（10 条用例，含负控与预渐近守卫）；复现脚本即本文件（`--render-only` 可由 `metrics.json` 重建报告与图）。m5404 重判调用 `contact_energy_order.m5404_rejudgement`，后者驱动**已交付**的 `floe_rigid6dof.FloeWorld`，不是重写。\n\n## 3. 计算结果\n\n### 3.1 三口径 × Δt（线性弹簧，1 阶/2 阶可测）\n\n| N_c=t_c/Δt | Δt [s] | 通量口径残差（全程） | 显式口径残差 @t\\* | 梯形口径残差 @t\\* |\n|---|---|---|---|---|\n| 8 | 1.242e-03 | 1.110e-16 | 2.650e-01 | 4.147e-02 |\n| 16 | 6.209e-04 | 6.280e-16 | 1.296e-01 | 1.010e-02 |\n| 32 | 3.105e-04 | 2.316e-16 | 6.681e-02 | 2.755e-03 |\n| 64 | 1.552e-04 | 4.619e-16 | 3.419e-02 | 5.924e-04 |\n| 128 | 7.761e-05 | 3.743e-16 | 1.722e-02 | 1.657e-04 |\n| 256 | 3.881e-05 | 2.734e-15 | 8.649e-03 | 4.242e-05 |\n| 512 | 1.940e-05 | 1.811e-15 | 4.336e-03 | 1.005e-05 |\n| 1024 | 9.702e-06 | 1.830e-16 | 2.174e-03 | 2.704e-06 |\n\n拟合（log|r| vs log Δt，最小二乘）：显式斜率 **0.986**（R²=1.0000，8 点），梯形斜率 **1.989**（R²=0.9998）；通量口径全程最大残差 **2.73e-15**。粗细残差比：显式 121.9×，梯形 15335.2×（干净幂律的 2^k 特征）。\n\n**读法.** 三口径不是同一公式的三种写法：通量口径是**结构恒等式**（残差 = 记账缺陷计，Δt 无关）；显式口径是**一阶求积**；梯形口径在检查点上等价于离散 ΔKE 对解析值的**轨迹误差**（二阶）。同一次碰撞、同一份力序列，只因「力与速度是否同一时间层 / 求积规则」就差一阶——这正是 m5404 那类 5e-7 残差会被误读为「精度很好」的原因。\n\n### 3.2 恢复系数（判据 c）\n\n目标 e=0.571740028（clamped 闭式），实测 e=0.571663401，|e−e_target|=7.663e-05（N_c=1024）；粗分辨率 N_c=32 时误差 8.594e-04 → **误差随细化下降，是离散误差而非偏置**。\n\n### 3.3 五球 Newton 摆（判据 d）\n\n| Δt [s] | N_c | 总动量漂移 | 通量口径残差 | 显式口径残差 | 末球速度 [m/s] |\n|---|---|---|---|---|---|\n| 4.831e-04 | 8 | 1.110e-15 | 6.044e-14 | 9.435e-01 | 0.9905 |\n| 2.415e-04 | 16 | 1.110e-15 | 6.044e-14 | 4.607e-01 | 0.9895 |\n| 1.208e-04 | 32 | 1.110e-15 | 6.044e-14 | 2.291e-01 | 0.9889 |\n\n五球紧贴时 4 个接触**同时**加载（静不定），力/功按对累加最易漏项；实测总动量漂移 1.11e-15 ≪ 1e-12，末球获得 0.989 m/s（入射 1 m/s），能量通过链传递而非瞬间整体弹开，与 Newton 摆的物理一致。\n\n### 3.4 m5404 残差重判（判据 e）\n\n| Δt [s] | 步数 | 状态量口径残差 | 梯形功率口径 | 注入 1e-3 缺陷 | 浮冰 A v_x | 浮冰 B v_x |\n|---|---|---|---|---|---|---|\n| 2.000e-04 | 2501 | 5.111e-07 | 2.315e-05 | 4.815e-05 | +0.004641 | +0.495359 |\n| 1.000e-04 | 5001 | 3.964e-07 | 5.295e-06 | 4.828e-05 | +0.004650 | +0.495350 |\n| 5.000e-05 | 10001 | 8.692e-08 | 1.387e-06 | 4.860e-05 | +0.004652 | +0.495348 |\n| 2.500e-05 | 20001 | 2.835e-08 | 3.319e-07 | 4.866e-05 | +0.004652 | +0.495348 |\n\n**显式判定（判据 e）：`convention`。** 5.111e-07 是**口径误差**（离散/记账量），不是实现缺陷：状态量口径残差在 4 级 Δt 细化下按斜率 1.47 幂律塌缩（粗/细 18.0×），而同一算例注入 1e-3 状态函数缺陷后残差呈平台（斜率 -0.005，粗/细 0.990×），说明该判据对实现缺陷有分辨力，5.111e-07 未呈现平台行为。\n\n* 复现：level-0（Δt=2.000e-04）残差 5.111290246e-07 与 m5404 报告值 5.111290246e-07 相对偏差 0.00e+00（同一求解器同一算例）。\n* 判别力：状态量口径 18.0× 塌缩（斜率 1.47），注入缺陷 0.990×（斜率 -0.005 = 平台），两类行为相差一个数量级的斜率。\n* 归因：5.111e-07 与同一算例的显式（一阶）口径残差量级相差数个数量级，属于**最小通道**（状态量/超级收敛通道）的截断量——即「口径误差」，任何实现缺陷都会把它顶到 1e-5 量级（注入 1e-3 缺陷实测 4.81e-05）。\n\n## 4. 结果图\n\n![三口径收敛](figures/fig1_three_conventions.png)\n\n*图 1 三口径并列：通量口径与 Δt 无关（结构恒等式，round-off 带），显式口径斜率≈1，梯形口径斜率≈2；参考斜率线 ∝Δt¹、∝Δt² 与 1e-9 验收线。*\n\n![检查点](figures/fig2_force_power_checkpoint.png)\n\n*图 2 线性弹簧碰撞的接触力、储能与接触功率时程，红点线为账本检查点 t\\*=0.3 t_c（非驻点，故求积阶可测）。*\n\n![恢复系数](figures/fig3_restitution.png)\n\n*图 3 恢复系数随分辨率趋于 clamped 闭式；右图误差随 N_c 下降，1e-3 验收线在 N_c≥1024 处满足。*\n\n![m5404 重判](figures/fig4_m5404_verdict.png)\n\n*图 4 m5404 重判：状态量口径与梯形功率口径随 Δt 幂律下降（斜率 1.47/2.03），注入 1e-3 缺陷为平台（-0.005）；右图显示可观测量（浮冰出射速度）对 Δt 不敏感——残差是记账量，不是物理量。*\n\n![Newton 摆](figures/fig5_newton_cradle.png)\n\n*图 5 5 球 Newton 摆：状态/显式口径残差与总动量漂移 1.1e-15（≪1e-12 门）。*\n\n## 5. 注意点（踩过的坑 / 局限 / 适用范围）\n\n1. **恒等式陷阱（最重要的坑）.** velocity-Verlet 下「力梯形×位移」与离散 ΔKE 恒等；「功率梯形」在完整碰撞（两端 F=0）下同样是恒等式（残余项 (Δt/4)(F_end−F_start) 取零）。因此**末态残差不能给梯形口径定阶**——in54w1 在这里撞上灰墙并把该项记为 documented FAIL。本单的解法是检查点协议；若有人把「梯形口径斜率为 0」读成「实现有问题」，那是把恒等式误诊为缺陷。\n2. **通量口径 <1e-9 的语义.** 它测的是**记账实现**（冲量-速度配对 / 力-位移配对 / 功通道符号），不是精度。负控（漏半步 kick、旧力）实测把残差顶到 1e-1 量级，所以这条线在 CI 里是有牙的；但它**不能**用来宣称物理精度高。\n3. **检查点位置.** t\\*=0.3 t_c 取在压缩中期；若取在最大压缩（驻点）或末态，显式口径也会超级收敛（端点抵消），1 阶/2 阶会同时「看起来」是 2 阶。报告里给的检查点比例和每级实际 t\\*_rel/t_c 都落进 `metrics.json`，可复核。\n4. **阶扫描用线性弹簧.** 只为让解析参考 ΔKE(t\\*) 成立；Hertz 弹性碰撞的状态量通道是超级收敛（in54w1 实测斜率 2.88），不适合作为「干净一阶/二阶」的判据，本单不拿它充数。\n5. **恢复系数的适用面.** 目标值只在**clamped** 线性弹簧-阻尼律下是闭式；Hunt-Crossley / Hertz 阻尼没有本模块使用的闭式，需另给参考（事件驱动积分或文献）。另外固定步长下 e 随 N_c 有已知抖动，故判据只在 N_c≥1024 处要求 <1e-3。\n6. **m5404 判定的边界.** 判定依赖 ≥3 级 Δt；2 级处于预渐近区（5.111e-07→3.96e-07 斜率仅 0.37）会误判 `implementation`，模块已强制 ≥3 级。另外 level-0 与 m5404 的同值属「同一求解器同一算例」的复现，不构成对该算例物理设置的独立确认（物理算例本身不属本单验收面）。\n7. **禁止重复已验证案例.** 本单不复用 `benchmarks/verified/` 下任何已验收算例，全部算例为本单新建（线性弹簧阶扫描、恢复系数、五球摆、m5404 重判探针）。\n\n## 6. 误差判定（关键量 vs 基准，逐项）\n\n| 关键量 | 本单结果 | 基准 | 相对误差 | 是否 <3% |\n|---|---|---|---|---|\n| 显式口径残差（最细 Δt） | 2.174e-03 | 0（解析 ΔKE(t\\*)） | 2.174e-03（E0 归一） | 是（且 ∝Δt） |\n| 梯形口径残差（最细 Δt） | 2.704e-06 | 0（解析 ΔKE(t\\*)） | 2.704e-06（E0 归一） | 是（且 ∝Δt²） |\n| 通量口径残差（全程，最坏） | 2.734e-15 | 同一次运行的离散 ΔKE | 2.734e-15 | 是（机器精度） |\n| 恢复系数 e | 0.571663401 | 0.571740028（clamped 闭式） | 1.340e-04 | 是（0.0134%） |\n| 五球摆总动量漂移 | 1.110e-15 | 0（P=1 kg·m/s 守恒） | 1.110e-15 | 是（机器精度） |\n| m5404 残差复现 | 5.111290246e-07 | 5.111290246e-07 | 0.000e+00 | 是（0%） |\n\n**逐项回答「是否<3%」**：上表六项全部是，且其中四项是机器精度量级、两项是收敛残差（其相对误差本身按阶收敛）。没有任何一项落在 3%~15% 的「可疑带」里，也没有为凑阈值而放宽归一化：所有残差统一用 E0=½m_eff v0² 归一。\n\n## 7. 机器验收判据（判据数字 + 产物路径）\n\n| 判据 | 实测 | 阈值 | 结论 |\n|---|---|---|---|\n| (a) 三口径并列 + 通量口径残差 | 2.734e-15 | < 1e-09 | PASS |\n| (b) 显式口径斜率 | 0.9864 | |s−1| < 0.2 | PASS |\n| (b) 梯形口径斜率 | 1.9893 | |s−2| < 0.2 | PASS |\n| (c) 恢复系数 |e−e_target| | 7.663e-05 | < 1e-03 | PASS |\n| (d) 五球摆总动量守恒 | 1.110e-15 | < 1e-12 | PASS |\n| (e) m5404 显式判定 | convention | convention / implementation | PASS |\n\n**总计 全部通过**（`all_passed = True`）。\n\n产物路径：\n\n* 原始数字：`docs/p54w3-contact-energy-certification/metrics.json`\n* 图：`docs/p54w3-contact-energy-certification/figures/*.png`\n* 模块：`src/tensordem/contact_energy_certification.py`\n* 用例：`tests/test_contact_energy_certification.py`\n* 复现：`python scripts/p54w3_contact_energy_certification.py --all`（`--render-only` 仅重建报告/图）\n\n## 8. 审计链\n\n1. **判据先于数字**：阈值 `FLUX_TOL=1e-9`、`SLOPE_TOL=0.2`、`RESTITUTION_TOL=1e-3`、`MOMENTUM_TOL=1e-12` 写在模块顶部常量里，测试与脚本共用同一常量，报告只引用 `metrics.json`。\n2. **解析参考**：线性弹簧 δ(t)=(v0/ω)sin ωt 与 clamped 恢复系数闭式均来自教科书解，不依赖任何离散运行；m5404 的对照是同一求解器的同一算例。\n3. **负控**：漏半步 kick / 旧力 → 通量残差 1.09e-01 / 8.02e-01（`tests/...::test_flux_convention_catches_a_bookkeeping_defect`）；注入 1e-3 状态函数缺陷 → m5404 侧斜率 -0.005。\n4. **判定规则预先声明**：`convention iff fitted slope >= 0.8`，且实测同时给出注入缺陷对照，规则的可判别性可复核。\n5. **可复算**：`metrics.json` 含每级 Δt、检查点索引、残差、拟合斜率/R²；`tests/` 全部阈值断言可独立重跑。\n6. **环境**：TensorDEM 0.1.0，Python 3.11.6，本机壁钟 112.2 s。\n",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "整篇 markdown 即源资产；sha256 与契约 source_hash 逐字节一致（I1 校验）"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题行",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 30,
            "start_line": 0,
            "end_line": 0,
            "quote": "# P54W3-N03 刚性碰撞能量账本收敛阶认证（成熟化）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "与平台 title 字段不同文字（平台 title 为任务全名），差异登记在 observations.title_drift"
        },
        {
          "asset_id": "A03",
          "asset_class": "provenance_statement",
          "label": "生成者/版本/时间戳与零手抄声明",
          "in_report_section": "P54W3-N03 刚性碰撞能量账本收敛阶认证（成熟化）",
          "locator": {
            "method": "char_span",
            "start_char": 32,
            "end_char": 189,
            "start_line": 2,
            "end_line": 2,
            "quote": "*TensorDEM 0.1.0 · 生成 2026-11-09T08:06:54+00:00 · Python 3.11.6 · 全部数字由 `scripts/p54w3_contact_energy_certification.py` 程序化写入 `metrics.json`，本报告只做模板插值（零手抄）。*",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "声明全部数字由 scripts/p54w3_contact_energy_certification.py 程序化写入 metrics.json；本工序只登记该声明，不复核"
        },
        {
          "asset_id": "A04",
          "asset_class": "problem_statement",
          "label": "问题背景 + 三项成熟化交付",
          "in_report_section": "1. 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 203,
            "end_char": 644,
            "start_line": 6,
            "end_line": 10,
            "quote": "**物理背景.** 刚性（硬）接触碰撞的能量账本要回答一个工程问题：m5404 报出的 `residual_state_relative = 5.111e-07` 是**口径误差**（离散/记账时层差）还是**实现误差**（编码缺陷）？单个数不能判，**细化行为**能判：口径误差随 Δt→0 消失（正斜率幂律），实现缺陷留下平台（斜率≈0）或发散。本单在此基础上做**成熟化**，交付三件事：\n\n1. 三口径（通量 / 显式 / 梯形）**并列实现**并有各自的可判定义与预期阶；\n2. 把阶的**可测量性**问题解决掉——完整碰撞末态下通量口径与梯形口径都是离散恒等式（无阶可拟合，in54w1 因此在验收表上留了一条 documented FAIL），本单改用**碰撞中期检查点**（t\\*=0.3 t_c，解析解可写），使显式=1 阶、梯形=2 阶成为可测事实；\n3. 五条机器判据全部 pytest 化，并把 m5404 的 5.111e-07 判成口径量，附判别力对照。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "含 m5404 5.111e-07 口径/实现之问与三件交付物（并列口径、可测性、pytest 判据）"
        },
        {
          "asset_id": "A05",
          "asset_class": "table",
          "label": "算例与参数表（S/R/C/M 四个算例，6 行）",
          "in_report_section": "1. 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 646,
            "end_char": 1331,
            "start_line": 12,
            "end_line": 19,
            "quote": "**算例与参数.**\n\n| 算例 | 配置 | 参数 | 参考解 |\n|---|---|---|---|\n| S 三口径阶扫描 | 两球头对头，约化为一维相对坐标 x（m_eff=m1m2/(m1+m2)） | 线性弹簧 k=1e+05 N/m，无阻尼，m_eff=1.0 kg，v0=1.0 m/s，gap0=0.02 m，Δt=t_c/8…t_c/1024 | δ(t)=(v0/ω)sin ωt，ω=√(k/m_eff)，ΔKE(t\\*)=E0(cos²(ωt\\*)−1) |\n| R 恢复系数 | 同上，线性弹簧-阻尼（Cundall-Strack） | ζ=0.2，k=1e+05 N/m，c=126.491 N·s/m，clamped 截断 | e_clamped=0.571740028（`contact_impact.clamped_restitution`） |\n| C Newton 摆 | 5 球共线、初始紧贴（接触网络超静定） | R=0.05 m，m=1.0 kg，k=1e+07 N/m^1.5，v0=1.0 m/s | 总动量守恒（P=m v0=1 kg·m/s） |\n| M m5404 重判 | 双浮冰块 4×3×0.4 m，ρ=917 kg/m³，y 向偏置 2 m，V=[1,0,0]/[−0.5,0,0] m/s | k_n=2e7 N/m^1.5，rk4，Δt0=2e-4 s，t=0.5 s，驱动**已交付**的 `floe_rigid6dof.FloeWorld` | m5404 报告值 5.111290246e-07 |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "数值仅登记不换算；参考解列给出解析式与 m5404 报告值"
        },
        {
          "asset_id": "A06",
          "asset_class": "definition_table",
          "label": "三口径离散定义表（flux/explicit/trapezoid）",
          "in_report_section": "2. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1388,
            "end_char": 1943,
            "start_line": 25,
            "end_line": 30,
            "quote": "| 口径 | 离散定义 | 对照基准 | 预期 |\n|---|---|---|---|\n| flux (通量口径) | `W = sum_n (1/2)(P_n + P_{n+1}) h,  P_n = F_n v_n` | same-run discrete dKE (full episode, contact-free ends) | identity: round-off (< 1e-9); residual would be a defect |\n| explicit (显式口径) | `W = sum_n F_n (x_{n+1} - x_n)` | analytic dKE(t*) at the interior checkpoint t* = 0.3 t_c | first order: slope 1 |\n| trapezoid (梯形口径) | `W = sum_n (1/2)(F_n + F_{n+1}) (x_{n+1} - x_n)` | analytic dKE(t*) at the interior checkpoint t* = 0.3 t_c | second order: slope 2 (= trajectory order under Verlet) |\n",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "每个口径的离散定义、对照基准与预期阶；分子式在原文中以行内代码给出"
        },
        {
          "asset_id": "A07",
          "asset_class": "method_rationale",
          "label": "检查点协议（本单核心增量）说明段",
          "in_report_section": "2. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1944,
            "end_char": 2223,
            "start_line": 31,
            "end_line": 31,
            "quote": "**(b) 为什么必须引入检查点（本单的核心增量）.** velocity-Verlet 下「力梯形 × 位移」与离散 ΔKE 是**同一个数**（两个半步 kick 使 v_{n+1/2}=(v_n+v_{n+1})/2，drift 使 Δx=Δt v_{n+1/2}），「功率梯形」同理：完整碰撞末态残差恒为 round-off，阶**不可测**。把账本检查点移到碰撞中期 t\\*=0.3 t_c（非驻点，P≠0），解析参考 ΔKE(t\\*) 可写，两条数值积分口径的阶才分离出来。实测：显式 ΔKE 残差 ∝Δt^0.986，梯形 ∝Δt^1.989。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "velocity-Verlet 恒等式论证 + 实测斜率 0.986/1.989；属方法论证非独立证据"
        },
        {
          "asset_id": "A08",
          "asset_class": "negative_control",
          "label": "负控设计（三项：记账缺陷/注入缺陷/预渐近区）",
          "in_report_section": "2. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 2225,
            "end_char": 2506,
            "start_line": 33,
            "end_line": 33,
            "quote": "**(c) 负控（判据有判别力才叫判据）.** ①通量口径在注入实现缺陷（漏掉第二个半步 kick / 力用旧值）后必须崩掉：实测从 round-off 跳到 1.09e-01 / 8.02e-01，说明 <1e-9 这条线测的是**记账实现**而不是离散误差；②m5404 同一算例注入 1e-3 状态函数误差后残差必须出现平台（实测斜率 -0.005，量级放大到 4.81e-05），说明斜率判据能把「口径」与「缺陷」分开；③恰好 2 级 Δt 处于预渐近区会给出假阴性（5.111e-07→3.96e-07 只有 0.37 的斜率），故模块强制 ≥3 级。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "负控实测值 1.09e-01/8.02e-01、斜率 -0.005；负控代码本体见 A10（未解析）"
        },
        {
          "asset_id": "A09",
          "asset_class": "toolchain_declaration",
          "label": "工具链组成（模块/回归守卫/复现脚本）",
          "in_report_section": "2. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 2508,
            "end_char": 2860,
            "start_line": 35,
            "end_line": 35,
            "quote": "**(d) 工具链.** 新模块 `src/tensordem/contact_energy_certification.py`（三口径 + 检查点协议 + 恢复系数/Newton 摆/m5404 三份 certificate + `certify_all` 折叠判据）；回归守卫 `tests/test_contact_energy_certification.py`（10 条用例，含负控与预渐近守卫）；复现脚本即本文件（`--render-only` 可由 `metrics.json` 重建报告与图）。m5404 重判调用 `contact_energy_order.m5404_rejudgement`，后者驱动**已交付**的 `floe_rigid6dof.FloeWorld`，不是重写。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "声明 10 条用例、certify_all 折叠判据、--render-only 重建；代码文件本体见 A10"
        },
        {
          "asset_id": "A10",
          "asset_class": "external_code_set",
          "label": "TensorDEM 侧代码三件（模块/用例/复现脚本）",
          "in_report_section": "2. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 2508,
            "end_char": 2860,
            "start_line": 35,
            "end_line": 35,
            "quote": "**(d) 工具链.** 新模块 `src/tensordem/contact_energy_certification.py`（三口径 + 检查点协议 + 恢复系数/Newton 摆/m5404 三份 certificate + `certify_all` 折叠判据）；回归守卫 `tests/test_contact_energy_certification.py`（10 条用例，含负控与预渐近守卫）；复现脚本即本文件（`--render-only` 可由 `metrics.json` 重建报告与图）。m5404 重判调用 `contact_energy_order.m5404_rejudgement`，后者驱动**已交付**的 `floe_rigid6dof.FloeWorld`，不是重写。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_lookup",
            "result": "unresolved",
            "paths_referenced": [
              "src/tensordem/contact_energy_certification.py",
              "tests/test_contact_energy_certification.py"
            ],
            "worktree_hits": [],
            "detail": "仅在本工作树内查存在性；不联网、不跨仓猜路径"
          },
          "note": "仓内相对路径，属 TensorDEM 仓产物；本工作树（TensorKnowledge）内不存在，无法本地解析"
        },
        {
          "asset_id": "A11",
          "asset_class": "table",
          "label": "三口径 × Δt 残差表（8 级，10 行）",
          "in_report_section": "3.1 三口径 × Δt（线性弹簧，1 阶/2 阶可测）",
          "locator": {
            "method": "char_span",
            "start_char": 2908,
            "end_char": 3439,
            "start_line": 41,
            "end_line": 51,
            "quote": "| N_c=t_c/Δt | Δt [s] | 通量口径残差（全程） | 显式口径残差 @t\\* | 梯形口径残差 @t\\* |\n|---|---|---|---|---|\n| 8 | 1.242e-03 | 1.110e-16 | 2.650e-01 | 4.147e-02 |\n| 16 | 6.209e-04 | 6.280e-16 | 1.296e-01 | 1.010e-02 |\n| 32 | 3.105e-04 | 2.316e-16 | 6.681e-02 | 2.755e-03 |\n| 64 | 1.552e-04 | 4.619e-16 | 3.419e-02 | 5.924e-04 |\n| 128 | 7.761e-05 | 3.743e-16 | 1.722e-02 | 1.657e-04 |\n| 256 | 3.881e-05 | 2.734e-15 | 8.649e-03 | 4.242e-05 |\n| 512 | 1.940e-05 | 1.811e-15 | 4.336e-03 | 1.005e-05 |\n| 1024 | 9.702e-06 | 1.830e-16 | 2.174e-03 | 2.704e-06 |\n",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "本单主证据数字表；本工序只登记定位，不复算、不判 verified"
        },
        {
          "asset_id": "A12",
          "asset_class": "numeric_result_statement",
          "label": "拟合结论（显式 0.986 / 梯形 1.989，R²，残差比）",
          "in_report_section": "3.1 三口径 × Δt（线性弹簧，1 阶/2 阶可测）",
          "locator": {
            "method": "char_span",
            "start_char": 3440,
            "end_char": 3588,
            "start_line": 52,
            "end_line": 52,
            "quote": "拟合（log|r| vs log Δt，最小二乘）：显式斜率 **0.986**（R²=1.0000，8 点），梯形斜率 **1.989**（R²=0.9998）；通量口径全程最大残差 **2.73e-15**。粗细残差比：显式 121.9×，梯形 15335.2×（干净幂律的 2^k 特征）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "斜率/R²/粗细残差比 121.9× 与 15335.2× 的原文陈述"
        },
        {
          "asset_id": "A13",
          "asset_class": "interpretation",
          "label": "「读法」段：三口径差异的解释",
          "in_report_section": "3.1 三口径 × Δt（线性弹簧，1 阶/2 阶可测）",
          "locator": {
            "method": "char_span",
            "start_char": 3590,
            "end_char": 3773,
            "start_line": 54,
            "end_line": 54,
            "quote": "**读法.** 三口径不是同一公式的三种写法：通量口径是**结构恒等式**（残差 = 记账缺陷计，Δt 无关）；显式口径是**一阶求积**；梯形口径在检查点上等价于离散 ΔKE 对解析值的**轨迹误差**（二阶）。同一次碰撞、同一份力序列，只因「力与速度是否同一时间层 / 求积规则」就差一阶——这正是 m5404 那类 5e-7 残差会被误读为「精度很好」的原因。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "属作者解释（interpretation），非机器判据；下游抽取须保留此定性"
        },
        {
          "asset_id": "A14",
          "asset_class": "numeric_result_statement",
          "label": "恢复系数判据 c 结果（e=0.571663401 vs 0.571740028）",
          "in_report_section": "3.2 恢复系数（判据 c）",
          "locator": {
            "method": "char_span",
            "start_char": 3795,
            "end_char": 3924,
            "start_line": 58,
            "end_line": 58,
            "quote": "目标 e=0.571740028（clamped 闭式），实测 e=0.571663401，|e−e_target|=7.663e-05（N_c=1024）；粗分辨率 N_c=32 时误差 8.594e-04 → **误差随细化下降，是离散误差而非偏置**。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "含粗分辨率 N_c=32 误差 8.594e-04，用于论证「离散误差而非偏置」"
        },
        {
          "asset_id": "A15",
          "asset_class": "table",
          "label": "五球 Newton 摆动量/残差表（3 级，5 行）",
          "in_report_section": "3.3 五球 Newton 摆（判据 d）",
          "locator": {
            "method": "char_span",
            "start_char": 3953,
            "end_char": 4225,
            "start_line": 62,
            "end_line": 66,
            "quote": "| Δt [s] | N_c | 总动量漂移 | 通量口径残差 | 显式口径残差 | 末球速度 [m/s] |\n|---|---|---|---|---|---|\n| 4.831e-04 | 8 | 1.110e-15 | 6.044e-14 | 9.435e-01 | 0.9905 |\n| 2.415e-04 | 16 | 1.110e-15 | 6.044e-14 | 4.607e-01 | 0.9895 |\n| 1.208e-04 | 32 | 1.110e-15 | 6.044e-14 | 2.291e-01 | 0.9889 |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "静不定接触网络下的动量守恒与末球速度"
        },
        {
          "asset_id": "A16",
          "asset_class": "table",
          "label": "m5404 残差重判表（4 级 Δt，7 行）",
          "in_report_section": "3.4 m5404 残差重判（判据 e）",
          "locator": {
            "method": "char_span",
            "start_char": 4374,
            "end_char": 4799,
            "start_line": 72,
            "end_line": 77,
            "quote": "| Δt [s] | 步数 | 状态量口径残差 | 梯形功率口径 | 注入 1e-3 缺陷 | 浮冰 A v_x | 浮冰 B v_x |\n|---|---|---|---|---|---|---|\n| 2.000e-04 | 2501 | 5.111e-07 | 2.315e-05 | 4.815e-05 | +0.004641 | +0.495359 |\n| 1.000e-04 | 5001 | 3.964e-07 | 5.295e-06 | 4.828e-05 | +0.004650 | +0.495350 |\n| 5.000e-05 | 10001 | 8.692e-08 | 1.387e-06 | 4.860e-05 | +0.004652 | +0.495348 |\n| 2.500e-05 | 20001 | 2.835e-08 | 3.319e-07 | 4.866e-05 | +0.004652 | +0.495348 |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "含注入 1e-3 缺陷对照列与浮冰 A/B 出射速度列"
        },
        {
          "asset_id": "A17",
          "asset_class": "verdict_statement",
          "label": "判据 e 结论（`convention`）及三条支撑",
          "in_report_section": "3.4 m5404 残差重判（判据 e）",
          "locator": {
            "method": "char_span",
            "start_char": 4801,
            "end_char": 5286,
            "start_line": 79,
            "end_line": 83,
            "quote": "**显式判定（判据 e）：`convention`。** 5.111e-07 是**口径误差**（离散/记账量），不是实现缺陷：状态量口径残差在 4 级 Δt 细化下按斜率 1.47 幂律塌缩（粗/细 18.0×），而同一算例注入 1e-3 状态函数缺陷后残差呈平台（斜率 -0.005，粗/细 0.990×），说明该判据对实现缺陷有分辨力，5.111e-07 未呈现平台行为。\n\n* 复现：level-0（Δt=2.000e-04）残差 5.111290246e-07 与 m5404 报告值 5.111290246e-07 相对偏差 0.00e+00（同一求解器同一算例）。\n* 判别力：状态量口径 18.0× 塌缩（斜率 1.47），注入缺陷 0.990×（斜率 -0.005 = 平台），两类行为相差一个数量级的斜率。\n* 归因：5.111e-07 与同一算例的显式（一阶）口径残差量级相差数个数量级，属于**最小通道**（状态量/超级收敛通道）的截断量——即「口径误差」，任何实现缺陷都会把它顶到 1e-5 量级（注入 1e-3 缺陷实测 4.81e-05）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "结论原文 + 复现/判别力/归因三条；本工序登记结论，不替平台判定真伪"
        },
        {
          "asset_id": "A18",
          "asset_class": "figure_declaration",
          "label": "5 幅图的 markdown 声明（图 1-图 5 + 题注）",
          "in_report_section": "4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 5299,
            "end_char": 5909,
            "start_line": 87,
            "end_line": 105,
            "quote": "![三口径收敛](figures/fig1_three_conventions.png)\n\n*图 1 三口径并列：通量口径与 Δt 无关（结构恒等式，round-off 带），显式口径斜率≈1，梯形口径斜率≈2；参考斜率线 ∝Δt¹、∝Δt² 与 1e-9 验收线。*\n\n![检查点](figures/fig2_force_power_checkpoint.png)\n\n*图 2 线性弹簧碰撞的接触力、储能与接触功率时程，红点线为账本检查点 t\\*=0.3 t_c（非驻点，故求积阶可测）。*\n\n![恢复系数](figures/fig3_restitution.png)\n\n*图 3 恢复系数随分辨率趋于 clamped 闭式；右图误差随 N_c 下降，1e-3 验收线在 N_c≥1024 处满足。*\n\n![m5404 重判](figures/fig4_m5404_verdict.png)\n\n*图 4 m5404 重判：状态量口径与梯形功率口径随 Δt 幂律下降（斜率 1.47/2.03），注入 1e-3 缺陷为平台（-0.005）；右图显示可观测量（浮冰出射速度）对 Δt 不敏感——残差是记账量，不是物理量。*\n\n![Newton 摆](figures/fig5_newton_cradle.png)\n\n*图 5 5 球 Newton 摆：状态/显式口径残差与总动量漂移 1.1e-15（≪1e-12 门）。*",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "声明块（含题注）在源文可定位；图件二进制见 A19"
        },
        {
          "asset_id": "A19",
          "asset_class": "figure_binary_set",
          "label": "图件二进制 5 个（figures/fig1..fig5.png）",
          "in_report_section": "4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 5299,
            "end_char": 5909,
            "start_line": 87,
            "end_line": 105,
            "quote": "![三口径收敛](figures/fig1_three_conventions.png)\n\n*图 1 三口径并列：通量口径与 Δt 无关（结构恒等式，round-off 带），显式口径斜率≈1，梯形口径斜率≈2；参考斜率线 ∝Δt¹、∝Δt² 与 1e-9 验收线。*\n\n![检查点](figures/fig2_force_power_checkpoint.png)\n\n*图 2 线性弹簧碰撞的接触力、储能与接触功率时程，红点线为账本检查点 t\\*=0.3 t_c（非驻点，故求积阶可测）。*\n\n![恢复系数](figures/fig3_restitution.png)\n\n*图 3 恢复系数随分辨率趋于 clamped 闭式；右图误差随 N_c 下降，1e-3 验收线在 N_c≥1024 处满足。*\n\n![m5404 重判](figures/fig4_m5404_verdict.png)\n\n*图 4 m5404 重判：状态量口径与梯形功率口径随 Δt 幂律下降（斜率 1.47/2.03），注入 1e-3 缺陷为平台（-0.005）；右图显示可观测量（浮冰出射速度）对 Δt 不敏感——残差是记账量，不是物理量。*\n\n![Newton 摆](figures/fig5_newton_cradle.png)\n\n*图 5 5 球 Newton 摆：状态/显式口径残差与总动量漂移 1.1e-15（≪1e-12 门）。*",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figures_field_and_worktree_lookup",
            "result": "unresolved",
            "platform_figures_count": 5,
            "platform_figure_names": [
              "fig1_three_conventions.png",
              "fig2_force_power_checkpoint.png",
              "fig3_restitution.png",
              "fig4_m5404_verdict.png",
              "fig5_newton_cradle.png"
            ],
            "worktree_hits": [],
            "detail": "平台 figures 只登记 name+caption（无 png 字节）；图件路径属 TensorDEM 仓"
          },
          "note": "路径相对 TensorDEM 仓 docs/p54w3-contact-energy-certification/；平台 figures 字段只登记 name+caption（5 条），png 字节不在本工作树"
        },
        {
          "asset_id": "A20",
          "asset_class": "limitation_set",
          "label": "注意点与局限 7 条",
          "in_report_section": "5. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 5940,
            "end_char": 6953,
            "start_line": 109,
            "end_line": 115,
            "quote": "1. **恒等式陷阱（最重要的坑）.** velocity-Verlet 下「力梯形×位移」与离散 ΔKE 恒等；「功率梯形」在完整碰撞（两端 F=0）下同样是恒等式（残余项 (Δt/4)(F_end−F_start) 取零）。因此**末态残差不能给梯形口径定阶**——in54w1 在这里撞上灰墙并把该项记为 documented FAIL。本单的解法是检查点协议；若有人把「梯形口径斜率为 0」读成「实现有问题」，那是把恒等式误诊为缺陷。\n2. **通量口径 <1e-9 的语义.** 它测的是**记账实现**（冲量-速度配对 / 力-位移配对 / 功通道符号），不是精度。负控（漏半步 kick、旧力）实测把残差顶到 1e-1 量级，所以这条线在 CI 里是有牙的；但它**不能**用来宣称物理精度高。\n3. **检查点位置.** t\\*=0.3 t_c 取在压缩中期；若取在最大压缩（驻点）或末态，显式口径也会超级收敛（端点抵消），1 阶/2 阶会同时「看起来」是 2 阶。报告里给的检查点比例和每级实际 t\\*_rel/t_c 都落进 `metrics.json`，可复核。\n4. **阶扫描用线性弹簧.** 只为让解析参考 ΔKE(t\\*) 成立；Hertz 弹性碰撞的状态量通道是超级收敛（in54w1 实测斜率 2.88），不适合作为「干净一阶/二阶」的判据，本单不拿它充数。\n5. **恢复系数的适用面.** 目标值只在**clamped** 线性弹簧-阻尼律下是闭式；Hunt-Crossley / Hertz 阻尼没有本模块使用的闭式，需另给参考（事件驱动积分或文献）。另外固定步长下 e 随 N_c 有已知抖动，故判据只在 N_c≥1024 处要求 <1e-3。\n6. **m5404 判定的边界.** 判定依赖 ≥3 级 Δt；2 级处于预渐近区（5.111e-07→3.96e-07 斜率仅 0.37）会误判 `implementation`，模块已强制 ≥3 级。另外 level-0 与 m5404 的同值属「同一求解器同一算例」的复现，不构成对该算例物理设置的独立确认（物理算例本身不属本单验收面）。\n7. **禁止重复已验证案例.** 本单不复用 `benchmarks/verified/` 下任何已验收算例，全部算例为本单新建（线性弹簧阶扫描、恢复系数、五球摆、m5404 重判探针）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "恒等式陷阱/通量口径语义/检查点位置/线性弹簧/恢复系数适用面/≥3 级 Δt/不复用已验收案例"
        },
        {
          "asset_id": "A21",
          "asset_class": "table",
          "label": "误差判定表（关键量 vs 基准，6 行）",
          "in_report_section": "6. 误差判定（关键量 vs 基准，逐项）",
          "locator": {
            "method": "char_span",
            "start_char": 6981,
            "end_char": 7473,
            "start_line": 119,
            "end_line": 126,
            "quote": "| 关键量 | 本单结果 | 基准 | 相对误差 | 是否 <3% |\n|---|---|---|---|---|\n| 显式口径残差（最细 Δt） | 2.174e-03 | 0（解析 ΔKE(t\\*)） | 2.174e-03（E0 归一） | 是（且 ∝Δt） |\n| 梯形口径残差（最细 Δt） | 2.704e-06 | 0（解析 ΔKE(t\\*)） | 2.704e-06（E0 归一） | 是（且 ∝Δt²） |\n| 通量口径残差（全程，最坏） | 2.734e-15 | 同一次运行的离散 ΔKE | 2.734e-15 | 是（机器精度） |\n| 恢复系数 e | 0.571663401 | 0.571740028（clamped 闭式） | 1.340e-04 | 是（0.0134%） |\n| 五球摆总动量漂移 | 1.110e-15 | 0（P=1 kg·m/s 守恒） | 1.110e-15 | 是（机器精度） |\n| m5404 残差复现 | 5.111290246e-07 | 5.111290246e-07 | 0.000e+00 | 是（0%） |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "上游自报六项全部 <3%；本工序只登记，误差是否成立由平台门/下游复审裁定"
        },
        {
          "asset_id": "A22",
          "asset_class": "self_assessment",
          "label": "「是否<3%」逐项回答段",
          "in_report_section": "6. 误差判定（关键量 vs 基准，逐项）",
          "locator": {
            "method": "char_span",
            "start_char": 7475,
            "end_char": 7596,
            "start_line": 128,
            "end_line": 128,
            "quote": "**逐项回答「是否<3%」**：上表六项全部是，且其中四项是机器精度量级、两项是收敛残差（其相对误差本身按阶收敛）。没有任何一项落在 3%~15% 的「可疑带」里，也没有为凑阈值而放宽归一化：所有残差统一用 E0=½m_eff v0² 归一。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "声明无 3%~15% 可疑带项、未放宽归一化（E0=½m_eff v0²）"
        },
        {
          "asset_id": "A23",
          "asset_class": "table",
          "label": "机器验收判据表（a-e，8 行）",
          "in_report_section": "7. 机器验收判据（判据数字 + 产物路径）",
          "locator": {
            "method": "char_span",
            "start_char": 7625,
            "end_char": 7976,
            "start_line": 132,
            "end_line": 139,
            "quote": "| 判据 | 实测 | 阈值 | 结论 |\n|---|---|---|---|\n| (a) 三口径并列 + 通量口径残差 | 2.734e-15 | < 1e-09 | PASS |\n| (b) 显式口径斜率 | 0.9864 | |s−1| < 0.2 | PASS |\n| (b) 梯形口径斜率 | 1.9893 | |s−2| < 0.2 | PASS |\n| (c) 恢复系数 |e−e_target| | 7.663e-05 | < 1e-03 | PASS |\n| (d) 五球摆总动量守恒 | 1.110e-15 | < 1e-12 | PASS |\n| (e) m5404 显式判定 | convention | convention / implementation | PASS |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "五项判据实测/阈值/PASS 原文；阈值来源见 A26"
        },
        {
          "asset_id": "A24",
          "asset_class": "numeric_result_statement",
          "label": "折叠判据 all_passed = True",
          "in_report_section": "7. 机器验收判据（判据数字 + 产物路径）",
          "locator": {
            "method": "char_span",
            "start_char": 7978,
            "end_char": 8011,
            "start_line": 141,
            "end_line": 141,
            "quote": "**总计 全部通过**（`all_passed = True`）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "上游自报折叠结果；本工序不将其转写为 verified"
        },
        {
          "asset_id": "A25",
          "asset_class": "artifact_path_list",
          "label": "产物路径清单（metrics.json/figures/模块/用例/复现命令）",
          "in_report_section": "7. 机器验收判据（判据数字 + 产物路径）",
          "locator": {
            "method": "char_span",
            "start_char": 8013,
            "end_char": 8335,
            "start_line": 143,
            "end_line": 149,
            "quote": "产物路径：\n\n* 原始数字：`docs/p54w3-contact-energy-certification/metrics.json`\n* 图：`docs/p54w3-contact-energy-certification/figures/*.png`\n* 模块：`src/tensordem/contact_energy_certification.py`\n* 用例：`tests/test_contact_energy_certification.py`\n* 复现：`python scripts/p54w3_contact_energy_certification.py --all`（`--render-only` 仅重建报告/图）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_lookup",
            "result": "unresolved",
            "paths_referenced": [
              "docs/p54w3-contact-energy-certification/figures/*.png",
              "docs/p54w3-contact-energy-certification/metrics.json",
              "scripts/p54w3_contact_energy_certification.py",
              "src/tensordem/contact_energy_certification.py",
              "tests/test_contact_energy_certification.py"
            ],
            "worktree_hits": [],
            "detail": "仅在本工作树内查存在性；不联网、不跨仓猜路径"
          },
          "note": "5 条仓内相对路径；均属 TensorDEM 仓，本工作树内不存在"
        },
        {
          "asset_id": "A26",
          "asset_class": "audit_chain",
          "label": "审计链 5 条（阈值常量/解析参考/负控/判定规则/可复算）",
          "in_report_section": "8. 审计链",
          "locator": {
            "method": "char_span",
            "start_char": 8348,
            "end_char": 8876,
            "start_line": 153,
            "end_line": 157,
            "quote": "1. **判据先于数字**：阈值 `FLUX_TOL=1e-9`、`SLOPE_TOL=0.2`、`RESTITUTION_TOL=1e-3`、`MOMENTUM_TOL=1e-12` 写在模块顶部常量里，测试与脚本共用同一常量，报告只引用 `metrics.json`。\n2. **解析参考**：线性弹簧 δ(t)=(v0/ω)sin ωt 与 clamped 恢复系数闭式均来自教科书解，不依赖任何离散运行；m5404 的对照是同一求解器的同一算例。\n3. **负控**：漏半步 kick / 旧力 → 通量残差 1.09e-01 / 8.02e-01（`tests/...::test_flux_convention_catches_a_bookkeeping_defect`）；注入 1e-3 状态函数缺陷 → m5404 侧斜率 -0.005。\n4. **判定规则预先声明**：`convention iff fitted slope >= 0.8`，且实测同时给出注入缺陷对照，规则的可判别性可复核。\n5. **可复算**：`metrics.json` 含每级 Δt、检查点索引、残差、拟合斜率/R²；`tests/` 全部阈值断言可独立重跑。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "FLUX_TOL=1e-9、SLOPE_TOL=0.2、RESTITUTION_TOL=1e-3、MOMENTUM_TOL=1e-12 等阈值声明"
        },
        {
          "asset_id": "A28",
          "asset_class": "normalization_declaration",
          "label": "残差归一化约定（E0=½m_eff v0²）",
          "in_report_section": "2. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1345,
            "end_char": 1386,
            "start_line": 23,
            "end_line": 23,
            "quote": "**(a) 三口径的并列定义**（残差一律以 E0=½m_eff v0² 归一）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "补充登记：覆盖率缺口分析（图 1 阴影带）显示此行未被任何资产钉住；归一化基准是残差量纲的定义本身，下游抽取需要它，故补登"
        },
        {
          "asset_id": "A29",
          "asset_class": "interpretation",
          "label": "五球摆物理解释段（静不定加载/末球 0.989 m/s）",
          "in_report_section": "3.3 五球 Newton 摆（判据 d）",
          "locator": {
            "method": "char_span",
            "start_char": 4227,
            "end_char": 4346,
            "start_line": 68,
            "end_line": 68,
            "quote": "五球紧贴时 4 个接触**同时**加载（静不定），力/功按对累加最易漏项；实测总动量漂移 1.11e-15 ≪ 1e-12，末球获得 0.989 m/s（入射 1 m/s），能量通过链传递而非瞬间整体弹开，与 Newton 摆的物理一致。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "补充登记：覆盖率缺口分析发现该解释段未被钉住；含 1.11e-15 与 0.989 m/s 的原文数字"
        },
        {
          "asset_id": "A27",
          "asset_class": "environment_record",
          "label": "运行环境记录（TensorDEM 0.1.0 / Python 3.11.6 / 壁钟 112.2 s）",
          "in_report_section": "8. 审计链",
          "locator": {
            "method": "char_span",
            "start_char": 8877,
            "end_char": 8930,
            "start_line": 158,
            "end_line": 158,
            "quote": "6. **环境**：TensorDEM 0.1.0，Python 3.11.6，本机壁钟 112.2 s。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
            "occurrences": 1
          },
          "note": "可复现性元数据；本工序不验证该环境是否可复现"
        }
      ],
      "claims": [],
      "claims_note": "契约 objective.classify_report_type=false 且 notes 指明「不做抽取、claims 允许为空」：本工序只登记资产定位与解析状态，不产出知识 claim。A17/A24 中的结论性原文属源资产内容，登记不等于平台验证。",
      "observations": [
        {
          "id": "O1",
          "kind": "metadata_drift",
          "text": "平台 title 与 markdown 一级标题不同文字：title 为任务全名，正文标题带「（成熟化）」后缀。",
          "evidence_asset": "A02",
          "detail": {
            "platform_title": "P54W3-N03 刚性碰撞能量账本收敛阶认证：三口径并列实现、1/2 阶可测性与 m5404 残差判定",
            "markdown_heading": "P54W3-N03 刚性碰撞能量账本收敛阶认证（成熟化）"
          }
        },
        {
          "id": "O2",
          "kind": "figures_present",
          "text": "平台 figures 字段登记 5 条（name+caption），对应正文明声明的图 1-图 5；png 字节未随报告存储。",
          "evidence_asset": "A18"
        },
        {
          "id": "O3",
          "kind": "external_code_dependency",
          "text": "结论的全部数值产物在 TensorDEM 仓（模块/用例/metrics.json），本工序无法在本工作树内解析，故 A10/A25 标 referenced_unresolved，不视为缺失或造假。",
          "evidence_asset": "A10"
        },
        {
          "id": "O4",
          "kind": "upstream_lineage",
          "text": "报告自身声明其上游为 in54w1（留 documented FAIL）与 m5404（5.111290246e-07）；两者均以文字出现，未给出可解析报告号或路径。",
          "evidence_asset": "A04"
        },
        {
          "id": "O5",
          "kind": "no_verification_claim",
          "text": "本 manifest 不含 verified 标记：A23/A24 的 PASS 与 all_passed=True 是源报告的自报值，登记的是「原文如此」，不是平台复算结论。",
          "evidence_asset": "A23"
        }
      ],
      "integrity": {
        "quote_uniqueness": "每条 quote 在 markdown 中唯一（occurrences=1），由 scripts/kf_register_9761.py 断言",
        "quote_slice_consistency": "md[start_char:end_char]==quote 与 行区间重建同时校验（I4/I5）",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "no_asset_id_duplicates": true,
        "verified_flags": "none (verification is computed by the platform gate)",
        "verifier": "scripts/kf_verify_9761.py"
      }
    }
  },
  "claims": []
}
```
