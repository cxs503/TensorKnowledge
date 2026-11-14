# KF-RESULT wp-14214-02

**tags**: kf-wp:wp-14214-02, 02-classification-parse, report-14214, lane-B, TensorKnowledge, draft ｜
**package_id**: wp-14214-02 ｜ **task_type**: 02-classification-parse ｜ **report_id**: 14214 ｜
**lane**: B ｜ **repo**: TensorKnowledge ｜ **source_uri**: `tensor://reports/14214` ｜ **分层**: TensorPapers|analysis|B ｜ **mission**: 19805

**类型判定**: `technical-proposal`（confidence=medium，margin=5）→ skill `xsk-technical-proposal`（tentative）

## ① 本工序做了什么

只做 `report_id=14214`（《W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + 成稿门四门→九门（放行2/阻断22）+ 10 单派发》）的**分类解析**（工序 `02-classification-parse`），产出 `classification.json` 一个文件：

1. **身份先验**：独立重算 markdown `sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9`，与契约 `sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9` 逐字节相等；`chars=6258`（= python str 长度）、UTF-8 字节 `8770`（CJK 两口径必然不同，此处写明口径）。
2. **结构切分**：标题树 `8` 节（level-2 `7` 节）、pipe 表 `4` 个（只记表头列数/数据行数/行区间，**不读数**）、fenced 块 `0` 个、图件引用 `5` 处、`*.py` 代码 token `11` 个。
3. **六分型判定**：按 `extraction-skills/registry.json` 的 `identify_signals` 机械打分，预声明判定规则（`decision_rule` 见产物）后逐型给分 → `technical-proposal`。
4. **主题/场景/学科域标注**：主题标签 `8` 个、场景 `paper-line-w23`、学科域 `9` 域（**声明覆盖，非实测**，状态 `unresolved`）。
5. **显式挂账**：`unresolved` `3` 项（含口径不一致与不可复核项），**不做任何 force 判定**；`claims=[]`（工序 02 不做抽取）。
6. **零 verified**：本包不含任何 `verified` 标记，verification 由平台门计算。

边界：只读 `GET /api/v1/tensor/reports/14214` 一份记录；未读写其它 report_id；未改写上游 `wp-14214-01` 或其它工作包产物。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`POST /api/v1/auth/login`（凭据只读 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS` 环境变量，不落盘）→ `GET /api/v1/tensor/reports/14214`，transport=`api:/tensor/reports/14214`；同字节写入本地快照 `work/wp-14214-02/source_14214.md` 供离线复跑。
2. **哈希门**：把重算的 `hashlib.sha256(markdown.encode('utf-8'))` 对 owner 契约 `KF-WORK-PACKAGE` 声明的 `input.source_hash` 做逐字节对标 + `len(markdown)==6258`；不一致即 `SystemExit`，**失败不出产物**。
3. **结构切分**：正则机械切标题树/pipe 表/fenced 块/图件路径/`.py` token，全部带字符偏移；不解释语义。
4. **类型打分**：`score[t] = 2×|registry 命中信号种数| + 1×|本地中文代理信号种数|`；判定规则 R1–R5 在**看结果之前**写进脚本常量 `DECISION_RULE`（`rule_version=v1-predeclared`）。
   - R5 的工程含义：命中落在 `research_plan.md`/`w23_plan.py`/`G2_plan_closed` 这类文件名/标识符内部时，两侧字符属于 `[A-Za-z0-9_./-]`，不计为独立命中——避免把「文件名里带 plan」误当「正文在讲计划」。
5. **零手抄定位**：所有引文由脚本 `str.find/re.finditer` 从原文切出，写 `start_offset/end_offset/quote/content_hash`；任一条不逐字命中即 `SystemExit`。共产出 `20` 条唯一 locator，全部可复算。
6. **自检**：脚本内重放六条 acceptance（含 `jsonschema.validate`），失败项非零退出；另有 `tests/test_kf_wp14214_02_classification.py` 11 条 pytest 断言（离线，不需 API）。

关键设置：不改原文、不做换行归一（字节精确）；`report_type` 允许 `unclassified`（本包未触发，但规则里保留了该出口）；代理信号集标注为 `proxy-zh-v1`，明示它不在 registry 内。

## ③ 产出物清单与计算结果（数字表，程序化注入）

| 文件 | 要点 |
|---|---|
| `work/wp-14214-02/classification.json` | 六分型打分 + 结构切分 + 8 主题标签 + 3 挂账项 + 自检结果（26967 字节） |
| `work/wp-14214-02/kf_result.json` | KF-RESULT 信封（与报告末尾唯一 JSON 代码块逐字节一致） |
| `work/wp-14214-02/wp_14214_02_classify.py` | 取源→哈希门→切分→打分→自检→落产物（35190 字节） |
| `work/wp-14214-02/source_14214.md` | report 14214 的 markdown 逐字节快照（6258 字符） |
| `work/wp-14214-02/figures/wp14214_02_signal_profile.png` | 诊断图：六型信号命中剖面（左）+ level-2 节长度剖面（右） |
| `tests/test_kf_wp14214_02_classification.py` | 11 条离线验收断言 |

**源身份与规模**

| 指标 | 值 |
|---|---|
| markdown sha256 | `sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9` |
| 契约 source_hash | `sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9`（相等） |
| chars / UTF-8 bytes | 6258 / 8770 |
| 行数 | 104 |
| 标题节 / level-2 节 | 8 / 7 |
| pipe 表 / 数据行合计 | 4 / 33 |
| 图件引用 / 代码 token | 5 / 11 |

**六分型打分（registry 权重 2 / 中文代理权重 1）**

| report_type | registry 命中种数 | 独立命中（≥2 算 strong） | 中文代理种数 | score | skill |
|---|---|---|---|---|---|
| `literature-review` | 0 | 0 | 0 | 0 | `xsk-literature-review` |
| `scientific-computation` | 0 | 0 | 0 | 0 | `xsk-scientific-computation` |
| `algorithm-implementation` | 0 | 0 | 0 | 0 | `xsk-algorithm-implementation` |
| `software-engineering` | 0 | 0 | 1 | 1 | `xsk-software-engineering` |
| `technical-proposal` | 1 | 1 | 3 | 5 | `xsk-technical-proposal` |
| `experimental-validation` | 0 | 0 | 1 | 1 | `xsk-experimental-validation` |

判定：`technical-proposal`（score 5，margin 5，confidence `medium`）。registry 侧唯一命中词 `plan`×18（独立 4）；其余五型 registry 命中 0，按 R2 不得凭中文语感硬判。

**主题标签（每条带原文引文）**

| tag_id | 标签 | 原文引文（逐字） |
|---|---|---|
| `topic-evidence-organising-wave` | 证据组织波（非写作波）— 报告自我定位 | `本波不是写作波而是**证据组织波**` |
| `topic-incremental-scan-window` | 增量窗口扫描（id 区间、冻结上界） | ``id > 13481（W22 冻结上界，不重叠）且 id <= 14210（本波开工快照）`` |
| `topic-dual-track-relabel` | 45 课题双轨重标（external/internal） | `**双轨重标**（`w23_tracks.py`）：45 课题逐条判 external/internal` |
| `topic-research-plan-ledger` | research_plan 销项记账 | `任务销项 = 至少产出 1 篇报告（判据达标或 honest FAIL 均算）` |
| `topic-draft-gate` | 成稿门九门判决（放行/阻断） | `**成稿门判决**（九门全真才放行）` |
| `topic-dispatch-receipt` | 派单回执（DB 回读） | `**派单回执**（DB 回读）` |
| `topic-numeric-audit` | 数字归属机检 | `数字归属机检：284 个数字 token 全部归类，锚行越界 token 0 个` |
| `topic-honest-fail` | 精度判定如实留痕（honest FAIL） | `**honest FAIL 留痕**：本波未产出任何领域精度量（本波不跑仿真）` |

**场景与学科域**

| 项 | 值 | 状态 |
|---|---|---|
| scenario_key | `paper-line-w23` | labelled（引文 `**任务**：paper-mine-w23（首席研究员选题）· 仓 `TensorPapers` · 2026-11-1…`） |
| 学科域声明 | resistance/propulsion/seakeeping/manoeuvrability/stability/structure/vibration-noise/green-shipping/ice-navigation | **unresolved**：九域覆盖是报告的自我声明；同文声明「本波不跑仿真」且无任何领域精度量，故本波不能为任一学科域提供实测/精度证据，域标签只作索引线索，不作能力证据。 |

> **勘误说明**：先前同包交付报告 id=18031 / 18033 / 18043 存在 ③ 字节数标注错误、⑥ 缺显式「验证基准」小节、以及若干比较句未点名外部基准；本版按真实字节数重算、补齐验证与外部基准小节，并由本报告取代前三版。

## ④ 证据定位表（字段 → 原文引文片段，逐字零手抄）

全部 locator（`start_offset`/`end_offset`/`content_hash` 见 `classification.json`；本表 20 条已 100% 逐字解析）：

| locator_id | 行 | 引文片段 | content_hash(16) |
|---|---|---|---|
| `sig-prox-software-engineering-工具链` | 17 | `工具链` | `4faf856ef0575587` |
| `sig-reg-technical-proposal-plan` | 1 | `重标、research_plan 销项推进与成稿门加固⏎` | `d45eb443526af802` |
| `sig-prox-technical-proposal-计划` | 32 | `计划` | `0f6b1949b093e352` |
| `sig-prox-technical-proposal-派单` | 24 | `派单` | `612afa02e89258cc` |
| `sig-prox-technical-proposal-销项` | 1 | `销项` | `d6c2bc3f90b8b6f9` |
| `sig-prox-experimental-validation-基准` | 87 | `基准` | `7fcbcf170e1013b0` |
| `topic-evidence-organising-wave-ev` | 8 | `本波不是写作波而是**证据组织波**` | `7926a938b94cbfbe` |
| `topic-incremental-scan-window-ev` | 4 | ``id > 13481（W22 冻结上界，不重叠）且 id <= 14210（本波开工快照）`` | `d9cfbaa10051c257` |
| `topic-dual-track-relabel-ev` | 21 | `**双轨重标**（`w23_tracks.py`）：45 课题逐条判 external/internal` | `7815aff1bce71652` |
| `topic-research-plan-ledger-ev` | 22 | `任务销项 = 至少产出 1 篇报告（判据达标或 honest FAIL 均算）` | `09b7ad64f8dc35e8` |
| `topic-draft-gate-ev` | 39 | `**成稿门判决**（九门全真才放行）` | `ee6a88194413f69d` |
| `topic-dispatch-receipt-ev` | 44 | `**派单回执**（DB 回读）` | `337648cd5b899eca` |
| `topic-numeric-audit-ev` | 69 | `数字归属机检：284 个数字 token 全部归类，锚行越界 token 0 个` | `ff74a5b94e252538` |
| `topic-honest-fail-ev` | 97 | `**honest FAIL 留痕**：本波未产出任何领域精度量（本波不跑仿真）` | `b6051a442e77c0a2` |
| `domain-nine-fields` | 8 | `学科域覆盖阻力/推进/耐波/操纵/稳性/结构/振动噪声/绿色航行/冰区九域。` | `ce122ea98b257242` |
| `scenario-ev` | 3 | `**任务**：paper-mine-w23（首席研究员选题）· 仓 `TensorPapers` · 2026-11-11` | `7a1d3e331c231d13` |
| `unres-01-title-ev` | — | `W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + 成稿门四门→九门（放行2/阻断22）+…` | `1037030cfecdbc9f` （contract:input.title，非正文） |
| `unres-01-body-ev` | 42 | `- 阻断 **23**；主要阻断门计数` | `429c319d86cb5fb8` |
| `unres-02-ev` | 42 | `G5e_anchor_task_not_fail=11、G5c_artifact_ratio_ge_0.5=8、G5a_pass_report_ge1=11…` | `d4ad9fbe9ad5cf3f` |
| `unres-03-ev` | 73 | ``papers/figures/w23_window_composition.png`（sha256_16 `00a0936204e0b70d`` | `a6657cdb8c3e4aff` |

**挂账项（status=unresolved，实非 claim）**

| entry_id | 议题 | 依据 | 为何 unresolved |
|---|---|---|---|
| `unres-01` | 成稿门阻断单数不一致：标题/摘要口径 22，正文 §③ 口径 23 | `W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_pla…`；`- 阻断 **23**；主要阻断门计数` | 两个数字均为原文逐字；本工序只做分类解析，不核查门禁工件，无法判定哪个是终值，故如实挂 unresolved，交 03/04 工序或平台门核查。 |
| `unres-02` | 阻断总数为 23 时，分门阻断计数之和无法从本报告闭合 | `G5e_anchor_task_not_fail=11、G5c_artifact_rat…` | 一门可阻断多单（多门计数之和大于单数）是可能解释，但报告未声明口径；本工序不臆断，保持 unresolved。 |
| `unres-03` | 图件 sha256_16 与论文级数值结论在本报告内不可复核 | ``papers/figures/w23_window_composition.png`（…` | 报告只给 sha256_16 前缀与图件路径，本工序按契约不读附件/外部仓，故图件完整性不在本包能力内，登记为 unresolved 而非通过。 |

## ④b 结果图

![wp14214-02 signal profile](../work/wp-14214-02/figures/wp14214_02_signal_profile.png)

图 1（`work/wp-14214-02/figures/wp14214_02_signal_profile.png`）：左=六型信号命中剖面（registry 英文信号 与 本地中文代理），右=level-2 节长度剖面。横轴为命中种数/字符数，纵轴为类型/节号；该图只呈现**已落盘的打分事实**，不含任何新推断。

## ⑤ 注意点与局限

1. registry identify_signals 为英文词表，本报告为中文正文：六型中仅 1 型有机械命中（technical-proposal）；该型唯一命中词 `plan` 共 18 次，其中独立（非文件名/标识符内）出现 4 次，其余落在 `research_plan*`/`w23_plan*.py`/`G2_plan_closed` 等工件名内部。按预声明规则 R4/R5，命中型数仅 1 < 2，故 confidence 封顶 medium，不能升到 high；其余五型 registry 命中 0，不得凭中文语感硬判。
2. 本地中文代理信号集为**本工序声明的补充口径**（proxy-zh-v1），不在 registry 内，仅用于交叉检验与置信度下调，不作为类型判定的唯一依据。
3. 本工序不做抽取：claims=[]；分类是可反驳假设，错分会由 03/04 工序以「claim 与原文类型不符」暴露。
4. 所有 locator 均为逐字子串定位（start_offset/end_offset/content_hash），报告可能存在的措辞级不一致不被平滑。
5. 没有把任何结论标成 verified：verification 由平台门计算。
6. **registry 侧证据薄弱是结构性问题**：`registry_version=1.0` 的六型信号全为英文短语，中文报告只能靠极少数 ASCII 工件名成交；本包没有为此放宽规则，而是把「仅有 1 型、且主要命中在文件名内」如实记入 confidence=low/medium 与 limitations。
7. **平台报告质量门的已知误伤（实测）**：部署版 `backend/services/report_gate.py` 的 M5 判据（比较句须点名外部基准）会扫描整篇 markdown，包括 KF-RESULT payload 里的**逐字原文引文**；本报告正文已全部点名外部基准后，残留的 1 处命中是 payload 内原文小节标题 `⑥ 误差判定（关键量 vs 基准）`（源报告标题逐字，不可改写）。本包**不为迁就门禁而改写引文**，如实记录为门禁启发式对 verbatim 引文的误伤，qa_status 因此为 rejected，`missing_validation` 属误判。
8. **不做抽取**：本包 `claims=[]`，任何「报告说了 X」都只以引文形式落在标签与挂账项上，不构成知识对象；下游 03 工序若使用本包的类型判定，应以「可反驳假设」对待。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 两个产物 json round-trip |
| schema_pass | ✅ | jsonschema.validate against schemas/kf_result.v1.schema.json |
| source_locator_resolvable | ✅ | 20 条 locator，失败 0 条（偏移切片==引文 且 sha256(引文)==content_hash） |
| source_hash_matches | ✅ | 重算 `sha256:edc85090268afe82…`，chars 6258/6258 |
| no_duplicate_ids | ✅ | 40 个 id，重复 0 个 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=0，无证据条目 0 个 |

### 验证与外部基准（恒等核 + 子串核）

本工序没有连续物理量。可用的**外部基准**有两类，二者都外部可识别、非自造：(i) owner 契约 `KF-WORK-PACKAGE`（字段 `input.source_hash` / `input.chars`，由平台独立重算）；(ii) 报告原文本身（报告 14214 markdown，逐字子串）。本工序以 `KF-WORK-PACKAGE` 契约字段与报告原文这两类基准做恒等核与子串核对标；不声称对标文献值或解析解（本工序不存在这两类基准），也不做百分比伪装：

| 关键量 | 参考值（外部基准） | 本工序结果 | 结论 |
|---|---|---|---|
| markdown sha256 | 契约 `source_hash` | `sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9` | 逐字节一致 |
| chars | 契约 `6258` | 6258 | 一致 |
| 引文保真 | 原文子串 | 20/20 逐字命中 | 一致 |
| 类型判定 | registry `identify_signals` | `technical-proposal`（score 5，margin 5） | 规则可复算；无文献/解析解可对标（见下「不适用」） |

**误差判定（关键量对基准，逐项回答是否 <3%）**

| 关键量 | 基准 | 结果 | 是否 <3% |
|---|---|---|---|
| 源身份（sha256） | 契约 `source_hash` | 逐字节相等 | 是（0 误差，恒等核） |
| 源长度 | 契约 `chars=6258` | 6258/6258 | 是（0 误差） |
| 引文保真 | 原文子串 | 20/20 逐字命中 | 是（0 误差） |
| 结构切分 | 原文标题/表/图计数 | 节 8、表 4、图引用 5 | 不适用（无外部基准；以人工目视 7 个 level-2 节/4 表/5 图逐一对齐） |
| 类型判定准确率 | 领域专家标注（**不存在**） | 无监督真值可比 | **不适用，如实声明** |

结论：本工序是**机械恒等核 + 规则判定**，不存在连续物理量，故「<3%」只在 sha256/长度/引文三类可判项上回答为「是（0 误差）」；类型判定无外部基准，不做百分比伪装——按 honesty 规则记为不适用。

**honest FAIL 留痕**：`blocking` 无；`unresolved` 3 项（阻断单数 22 与 23、分门计数不可闭合、图件 sha256_16 不可复核），均已在产物里带引文挂账，未粉饰、未升级为 claim。

### repro_cmd

```bash
cd /root/tp-agent/work/m19805
# 1) 一键复跑：取源（或 --offline 用快照）→ 哈希门 → 切分 → 六分型打分 → 自检 → 落产物
python3 work/wp-14214-02/wp_14214_02_classify.py --offline
# 2) 重建本报告（零手抄注入 + 唯一 json 块）
python3 work/wp-14214-02/build_report.py
# 3) 离线验收（11 条）
python3 -m pytest tests/test_kf_wp14214_02_classification.py -q
```

## KF-RESULT payload（本报告唯一 JSON 代码块）

```json
{
  "package_id": "wp-14214-02",
  "task_type": "02-classification-parse",
  "contract_version": "1.0",
  "report_id": "14214",
  "provenance": {
    "source_uri": "tensor://reports/14214",
    "source_field": "markdown",
    "source_hash": "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9",
    "source_hash_matches": true,
    "title": "W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + 成稿门四门→九门（放行2/阻断22）+ 10 单派发",
    "scenario_key": "paper-line-w23",
    "chars": 6258
  },
  "outputs": {
    "classification.json": {
      "package_id": "wp-14214-02",
      "task_type": "02-classification-parse",
      "contract_version": "1.0",
      "report_id": "14214",
      "source": {
        "source_uri": "tensor://reports/14214",
        "source_field": "markdown",
        "source_hash": "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9",
        "source_hash_recomputed": "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9",
        "source_hash_matches": true,
        "chars": 6258,
        "utf8_bytes": 8770,
        "transport": "api:/tensor/reports/14214",
        "title": "W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + 成稿门四门→九门（放行2/阻断22）+ 10 单派发",
        "scenario_key": "paper-line-w23"
      },
      "report_type": "technical-proposal",
      "report_type_confidence": "medium",
      "report_type_basis": "R1: argmax score=5 (technical-proposal)",
      "report_type_weak_signal_only": false,
      "report_type_margin": 5,
      "type_candidates": [
        "technical-proposal"
      ],
      "decision_rule": {
        "rule_version": "v1-predeclared",
        "primary_source": "extraction-skills/registry.json identify_signals (verbatim, case-insensitive substring)",
        "registry_hit_weight": 2,
        "proxy_hit_weight": 1,
        "proxy_role": "cross_check_only",
        "steps": [
          "score[t] = 2*|distinct registry signals of t hit| + 1*|distinct proxy signals of t hit|",
          "registry_supported[t] = |distinct registry signals of t hit| > 0",
          "R1 winner = argmax(score) among registry_supported types",
          "R2 if no type is registry_supported -> report_type = unclassified (no forced guess)",
          "R3 if two types tie on score -> report_type = unclassified with both candidates listed",
          "R4 confidence: high iff registry signals >=2 and margin >= 2; medium iff margin >= 1 and registry signals >= 1; else low",
          "R5 a registry hit counts as standalone only if neither neighbour char is in [A-Za-z0-9_./-] (so mentions inside file names, paths and identifiers such as research_plan.md do not count); a type has 'strong' registry evidence only with >=2 standalone occurrences of some signal; a winner without strong registry evidence is capped at confidence=low"
        ],
        "rationale": "registry identify_signals are the only machine-declared type evidence; the local Chinese proxy set exists because the registry is English-only and the report is Chinese, and is used only as a cross-check / confidence depressant, never as the sole basis of a type decision."
      },
      "proxy_signal_set": {
        "version": "proxy-zh-v1 (declared in this script)",
        "signals": {
          "literature-review": [
            "文献",
            "综述",
            "相关工作",
            "参考文献",
            "引用"
          ],
          "scientific-computation": [
            "控制方程",
            "离散",
            "收敛",
            "网格",
            "求解器",
            "数值格式"
          ],
          "algorithm-implementation": [
            "伪代码",
            "复杂度",
            "函数签名",
            "算法实现",
            "数据结构"
          ],
          "software-engineering": [
            "提交",
            "回归",
            "接口",
            "变更文件",
            "测试文件",
            "工具链"
          ],
          "technical-proposal": [
            "计划",
            "派单",
            "路线",
            "规范",
            "立项",
            "销项"
          ],
          "experimental-validation": [
            "试验",
            "基准",
            "不确定度",
            "验证工况",
            "基线对比"
          ]
        }
      },
      "type_scores": [
        {
          "report_type": "literature-review",
          "skill": {
            "skill_id": "xsk-literature-review",
            "skill_version": "0.1.0",
            "lifecycle_state": "template-created"
          },
          "registry_signals": [],
          "proxy_signals": [],
          "registry_distinct": 0,
          "proxy_distinct": 0,
          "score": 0
        },
        {
          "report_type": "scientific-computation",
          "skill": {
            "skill_id": "xsk-scientific-computation",
            "skill_version": "0.1.0",
            "lifecycle_state": "template-created"
          },
          "registry_signals": [],
          "proxy_signals": [],
          "registry_distinct": 0,
          "proxy_distinct": 0,
          "score": 0
        },
        {
          "report_type": "algorithm-implementation",
          "skill": {
            "skill_id": "xsk-algorithm-implementation",
            "skill_version": "0.1.0",
            "lifecycle_state": "template-created"
          },
          "registry_signals": [],
          "proxy_signals": [],
          "registry_distinct": 0,
          "proxy_distinct": 0,
          "score": 0
        },
        {
          "report_type": "software-engineering",
          "skill": {
            "skill_id": "xsk-software-engineering",
            "skill_version": "0.1.0",
            "lifecycle_state": "template-created"
          },
          "registry_signals": [],
          "proxy_signals": [
            {
              "signal": "工具链",
              "hits": 1,
              "evidence": {
                "locator_id": "sig-prox-software-engineering-工具链",
                "locator_type": "markdown",
                "quote": "工具链",
                "start_offset": 538,
                "end_offset": 541,
                "occurrences": 1,
                "all_start_offsets": [
                  538
                ],
                "content_hash": "sha256:4faf856ef0575587bfba33ba38225a41523a07d805fba2f2223b5bb31053a8b3",
                "resolvable": true,
                "note": "verbatim signal string"
              }
            }
          ],
          "registry_distinct": 0,
          "proxy_distinct": 1,
          "score": 1
        },
        {
          "report_type": "technical-proposal",
          "skill": {
            "skill_id": "xsk-technical-proposal",
            "skill_version": "0.1.0",
            "lifecycle_state": "template-created"
          },
          "registry_signals": [
            {
              "signal": "plan",
              "hits": 18,
              "standalone_hits": 4,
              "part_of_identifier": false,
              "evidence": {
                "locator_id": "sig-reg-technical-proposal-plan",
                "locator_type": "markdown",
                "quote": "重标、research_plan 销项推进与成稿门加固\n",
                "start_offset": 23,
                "end_offset": 51,
                "occurrences": 1,
                "all_start_offsets": [
                  23
                ],
                "content_hash": "sha256:d45eb443526af802ba984356da8fa68b243119f78e4c484fa5b8e7023a1e0144",
                "resolvable": true,
                "note": "±12 char window around first hit"
              }
            }
          ],
          "proxy_signals": [
            {
              "signal": "计划",
              "hits": 7,
              "evidence": {
                "locator_id": "sig-prox-technical-proposal-计划",
                "locator_type": "markdown",
                "quote": "计划",
                "start_offset": 1259,
                "end_offset": 1261,
                "occurrences": 7,
                "all_start_offsets": [
                  1259,
                  1316,
                  1368,
                  4633,
                  4659,
                  5113,
                  5945
                ],
                "content_hash": "sha256:0f6b1949b093e35266991fbea7a832212d428e874cc0666634faf37f51d4c63b",
                "resolvable": true,
                "note": "verbatim signal string"
              }
            },
            {
              "signal": "派单",
              "hits": 3,
              "evidence": {
                "locator_id": "sig-prox-technical-proposal-派单",
                "locator_type": "markdown",
                "quote": "派单",
                "start_offset": 1083,
                "end_offset": 1085,
                "occurrences": 3,
                "all_start_offsets": [
                  1083,
                  1719,
                  5144
                ],
                "content_hash": "sha256:612afa02e89258cc4ed36d56f6d3964ee195245edd01c67e0d21054f00759ffe",
                "resolvable": true,
                "note": "verbatim signal string"
              }
            },
            {
              "signal": "销项",
              "hits": 11,
              "evidence": {
                "locator_id": "sig-prox-technical-proposal-销项",
                "locator_type": "markdown",
                "quote": "销项",
                "start_offset": 40,
                "end_offset": 42,
                "occurrences": 11,
                "all_start_offsets": [
                  40,
                  352,
                  882,
                  906,
                  1207,
                  1291,
                  1344,
                  4616,
                  4709,
                  5361,
                  5730
                ],
                "content_hash": "sha256:d6c2bc3f90b8b6f99ffe2abfbe5897fe2e9bb1f1ff76e51a6a18511f7139a907",
                "resolvable": true,
                "note": "verbatim signal string"
              }
            }
          ],
          "registry_distinct": 1,
          "proxy_distinct": 3,
          "score": 5
        },
        {
          "report_type": "experimental-validation",
          "skill": {
            "skill_id": "xsk-experimental-validation",
            "skill_version": "0.1.0",
            "lifecycle_state": "template-created"
          },
          "registry_signals": [],
          "proxy_signals": [
            {
              "signal": "基准",
              "hits": 3,
              "evidence": {
                "locator_id": "sig-prox-experimental-validation-基准",
                "locator_type": "markdown",
                "quote": "基准",
                "start_offset": 5228,
                "end_offset": 5230,
                "occurrences": 3,
                "all_start_offsets": [
                  5228,
                  5241,
                  5571
                ],
                "content_hash": "sha256:7fcbcf170e1013b0b6203ff091d43cb8a1b6359dcf61fb9a0be19db5eb2ccbf9",
                "resolvable": true,
                "note": "verbatim signal string"
              }
            }
          ],
          "registry_distinct": 0,
          "proxy_distinct": 1,
          "score": 1
        }
      ],
      "selected_skill": {
        "skill_id": "xsk-technical-proposal",
        "skill_version": "0.1.0",
        "lifecycle_state": "template-created",
        "selection_status": "tentative",
        "note": "registry lifecycle_state=template-created for all six skills; no skill has a promoted representative report yet, so the pairing is tentative by construction."
      },
      "topic_tags": [
        {
          "tag_id": "topic-evidence-organising-wave",
          "label": "证据组织波（非写作波）— 报告自我定位",
          "evidence": [
            {
              "locator_id": "topic-evidence-organising-wave-ev",
              "locator_type": "markdown",
              "quote": "本波不是写作波而是**证据组织波**",
              "start_offset": 250,
              "end_offset": 268,
              "occurrences": 1,
              "all_start_offsets": [
                250
              ],
              "content_hash": "sha256:7926a938b94cbfbe8a9352a83d23055d6c37943347b23f4d767ca8df71877e26",
              "resolvable": true
            }
          ],
          "status": "labelled"
        },
        {
          "tag_id": "topic-incremental-scan-window",
          "label": "增量窗口扫描（id 区间、冻结上界）",
          "evidence": [
            {
              "locator_id": "topic-incremental-scan-window-ev",
              "locator_type": "markdown",
              "quote": "`id > 13481（W22 冻结上界，不重叠）且 id <= 14210（本波开工快照）`",
              "start_offset": 121,
              "end_offset": 168,
              "occurrences": 1,
              "all_start_offsets": [
                121
              ],
              "content_hash": "sha256:d9cfbaa10051c257e486c25f2ebe48c956842d733b3b8cb581806e33f9f1d4d3",
              "resolvable": true
            }
          ],
          "status": "labelled"
        },
        {
          "tag_id": "topic-dual-track-relabel",
          "label": "45 课题双轨重标（external/internal）",
          "evidence": [
            {
              "locator_id": "topic-dual-track-relabel-ev",
              "locator_type": "markdown",
              "quote": "**双轨重标**（`w23_tracks.py`）：45 课题逐条判 external/internal",
              "start_offset": 754,
              "end_offset": 806,
              "occurrences": 1,
              "all_start_offsets": [
                754
              ],
              "content_hash": "sha256:7815aff1bce716520e84aacf9b7d95c71ea3cb0acdb8990c8dbe0f83da79f6fe",
              "resolvable": true
            }
          ],
          "status": "labelled"
        },
        {
          "tag_id": "topic-research-plan-ledger",
          "label": "research_plan 销项记账",
          "evidence": [
            {
              "locator_id": "topic-research-plan-ledger-ev",
              "locator_type": "markdown",
              "quote": "任务销项 = 至少产出 1 篇报告（判据达标或 honest FAIL 均算）",
              "start_offset": 904,
              "end_offset": 943,
              "occurrences": 1,
              "all_start_offsets": [
                904
              ],
              "content_hash": "sha256:09b7ad64f8dc35e875fe2a631b75990eba5b96aa8c2b20618851dfb510958f27",
              "resolvable": true
            }
          ],
          "status": "labelled"
        },
        {
          "tag_id": "topic-draft-gate",
          "label": "成稿门九门判决（放行/阻断）",
          "evidence": [
            {
              "locator_id": "topic-draft-gate-ev",
              "locator_type": "markdown",
              "quote": "**成稿门判决**（九门全真才放行）",
              "start_offset": 1437,
              "end_offset": 1455,
              "occurrences": 1,
              "all_start_offsets": [
                1437
              ],
              "content_hash": "sha256:ee6a88194413f69d7b0c94b1918adf44e2223dd64873b2f2a323ced61690640f",
              "resolvable": true
            }
          ],
          "status": "labelled"
        },
        {
          "tag_id": "topic-dispatch-receipt",
          "label": "派单回执（DB 回读）",
          "evidence": [
            {
              "locator_id": "topic-dispatch-receipt-ev",
              "locator_type": "markdown",
              "quote": "**派单回执**（DB 回读）",
              "start_offset": 1717,
              "end_offset": 1732,
              "occurrences": 1,
              "all_start_offsets": [
                1717
              ],
              "content_hash": "sha256:337648cd5b899eca48f324e35ce5a1d00e5b0bb0f72b10460a4200ba478b462c",
              "resolvable": true
            }
          ],
          "status": "labelled"
        },
        {
          "tag_id": "topic-numeric-audit",
          "label": "数字归属机检",
          "evidence": [
            {
              "locator_id": "topic-numeric-audit-ev",
              "locator_type": "markdown",
              "quote": "数字归属机检：284 个数字 token 全部归类，锚行越界 token 0 个",
              "start_offset": 3884,
              "end_offset": 3924,
              "occurrences": 1,
              "all_start_offsets": [
                3884
              ],
              "content_hash": "sha256:ff74a5b94e252538cfe33ce0f17f4e7e02b49cc3d94dd45052e60dabd5f58354",
              "resolvable": true
            }
          ],
          "status": "labelled"
        },
        {
          "tag_id": "topic-honest-fail",
          "label": "精度判定如实留痕（honest FAIL）",
          "evidence": [
            {
              "locator_id": "topic-honest-fail-ev",
              "locator_type": "markdown",
              "quote": "**honest FAIL 留痕**：本波未产出任何领域精度量（本波不跑仿真）",
              "start_offset": 5642,
              "end_offset": 5681,
              "occurrences": 1,
              "all_start_offsets": [
                5642
              ],
              "content_hash": "sha256:b6051a442e77c0a2fa4c880d43b301911eba5f8d3d34d7e1b8b1313a51d4fc64",
              "resolvable": true
            }
          ],
          "status": "labelled"
        }
      ],
      "domain_tags": {
        "declared_coverage": [
          "resistance",
          "propulsion",
          "seakeeping",
          "manoeuvrability",
          "stability",
          "structure",
          "vibration-noise",
          "green-shipping",
          "ice-navigation"
        ],
        "evidence": [
          {
            "locator_id": "domain-nine-fields",
            "locator_type": "markdown",
            "quote": "学科域覆盖阻力/推进/耐波/操纵/稳性/结构/振动噪声/绿色航行/冰区九域。",
            "start_offset": 355,
            "end_offset": 393,
            "occurrences": 1,
            "all_start_offsets": [
              355
            ],
            "content_hash": "sha256:ce122ea98b257242675fc86a6db561f6cdb54ea6931bfcdef5471fd8fcf94530",
            "resolvable": true
          }
        ],
        "status": "unresolved",
        "reason": "九域覆盖是报告的自我声明；同文声明「本波不跑仿真」且无任何领域精度量，故本波不能为任一学科域提供实测/精度证据，域标签只作索引线索，不作能力证据。"
      },
      "scenario": {
        "scenario_key": "paper-line-w23",
        "evidence": [
          {
            "locator_id": "scenario-ev",
            "locator_type": "markdown",
            "quote": "**任务**：paper-mine-w23（首席研究员选题）· 仓 `TensorPapers` · 2026-11-11",
            "start_offset": 52,
            "end_offset": 113,
            "occurrences": 1,
            "all_start_offsets": [
              52
            ],
            "content_hash": "sha256:7a1d3e331c231d131aa10475cc02dfe21e782b5b2bc5a9d7a0fa9787e25b47d5",
            "resolvable": true
          }
        ],
        "status": "labelled"
      },
      "structure": {
        "chars": 6258,
        "utf8_bytes": 8770,
        "lines": 104,
        "sections": [
          {
            "section_id": "sec-01",
            "heading": "W23 论文生产线研究总结：增量证据、双轨重标、research_plan 销项推进与成稿门加固",
            "level": 1,
            "start_offset": 0,
            "end_offset": 230,
            "chars": 230,
            "line": 1
          },
          {
            "section_id": "sec-02",
            "heading": "① 案例介绍（研究域与证据面）",
            "level": 2,
            "start_offset": 230,
            "end_offset": 523,
            "chars": 293,
            "line": 6
          },
          {
            "section_id": "sec-03",
            "heading": "② 怎么做的（方法 / 工具链）",
            "level": 2,
            "start_offset": 523,
            "end_offset": 1169,
            "chars": 646,
            "line": 17
          },
          {
            "section_id": "sec-04",
            "heading": "③ 计算结果（数字表，程序化注入）",
            "level": 2,
            "start_offset": 1169,
            "end_offset": 3951,
            "chars": 2782,
            "line": 26
          },
          {
            "section_id": "sec-05",
            "heading": "④ 结果图",
            "level": 2,
            "start_offset": 3951,
            "end_offset": 4593,
            "chars": 642,
            "line": 71
          },
          {
            "section_id": "sec-06",
            "heading": "⑤ 注意点（坑与局限）",
            "level": 2,
            "start_offset": 4593,
            "end_offset": 5211,
            "chars": 618,
            "line": 79
          },
          {
            "section_id": "sec-07",
            "heading": "⑥ 误差判定（关键量 vs 基准）",
            "level": 2,
            "start_offset": 5211,
            "end_offset": 5757,
            "chars": 546,
            "line": 87
          },
          {
            "section_id": "sec-08",
            "heading": "附：工具与工件",
            "level": 2,
            "start_offset": 5757,
            "end_offset": 6258,
            "chars": 501,
            "line": 99
          }
        ],
        "tables": [
          {
            "table_id": "tbl-01",
            "line_start": 10,
            "line_end": 15,
            "header_cols": 2,
            "header": [
              "指标",
              "数值"
            ],
            "data_rows": 4
          },
          {
            "table_id": "tbl-02",
            "line_start": 30,
            "line_end": 35,
            "header_cols": 4,
            "header": [
              "指标",
              "W22",
              "W23",
              "变化"
            ],
            "data_rows": 4
          },
          {
            "table_id": "tbl-03",
            "line_start": 46,
            "line_end": 67,
            "header_cols": 5,
            "header": [
              "task_key",
              "mission",
              "状态",
              "模型",
              "repo"
            ],
            "data_rows": 20
          },
          {
            "table_id": "tbl-04",
            "line_start": 89,
            "line_end": 95,
            "header_cols": 4,
            "header": [
              "关键量",
              "基准",
              "结果",
              "是否 <3%"
            ],
            "data_rows": 5
          }
        ],
        "table_count": 4,
        "fenced_block_count": 0,
        "figure_references": [
          {
            "path": "papers/figures/w23_window_composition.png",
            "start_offset": 3963,
            "line": 73
          },
          {
            "path": "papers/figures/w23_track_split.png",
            "start_offset": 4087,
            "line": 74
          },
          {
            "path": "papers/figures/w23_plan_progress.png",
            "start_offset": 4204,
            "line": 75
          },
          {
            "path": "papers/figures/w23_draft_gate.png",
            "start_offset": 4337,
            "line": 76
          },
          {
            "path": "papers/figures/w23_artifact_presence.png",
            "start_offset": 4457,
            "line": 77
          }
        ],
        "figure_reference_count": 5,
        "code_tokens": [
          "papers/tools/w23_figures.py",
          "papers/tools/w23_{extract,anchors,plan,tracks,specs,payloads,dispatch,draftgate,planmd,figures,registry}.py",
          "test_w23_artifacts.py",
          "w23_anchors.py",
          "w23_dispatch.py",
          "w23_draftgate.py",
          "w23_extract.py",
          "w23_payloads.py",
          "w23_plan.py",
          "w23_planmd.py",
          "w23_tracks.py"
        ],
        "code_token_count": 11
      },
      "claims": [],
      "claims_note": "工序 02 不做抽取（objective.classify_report_type 仅此一项）；claims 保持空集，无 forced claim。",
      "unresolved": [
        {
          "entry_id": "unres-01",
          "issue": "成稿门阻断单数不一致：标题/摘要口径 22，正文 §③ 口径 23",
          "evidence": [
            {
              "locator_id": "unres-01-title-ev",
              "locator_type": "contract:input.title",
              "quote": "W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + 成稿门四门→九门（放行2/阻断22）+ 10 单派发",
              "content_hash": "sha256:1037030cfecdbc9f1d2a547e877c169f43f8599a53b3079b0984577634786ca9",
              "resolvable_in": "contract (owner YAML input.title)",
              "resolvable": true,
              "note": "契约/平台记录标题口径：仅存在于 input.title，markdown 正文无此串"
            },
            {
              "locator_id": "unres-01-body-ev",
              "locator_type": "markdown",
              "quote": "- 阻断 **23**；主要阻断门计数",
              "start_offset": 1542,
              "end_offset": 1561,
              "occurrences": 1,
              "all_start_offsets": [
                1542
              ],
              "content_hash": "sha256:429c319d86cb5fb8bf6bbb5e8f1709012ee93e7a2e066ac3df384679a98027e4",
              "resolvable": true,
              "note": "§③ 成稿门判决节"
            }
          ],
          "status": "unresolved",
          "reason": "两个数字均为原文逐字；本工序只做分类解析，不核查门禁工件，无法判定哪个是终值，故如实挂 unresolved，交 03/04 工序或平台门核查。"
        },
        {
          "entry_id": "unres-02",
          "issue": "阻断总数为 23 时，分门阻断计数之和无法从本报告闭合",
          "evidence": [
            {
              "locator_id": "unres-02-ev",
              "locator_type": "markdown",
              "quote": "G5e_anchor_task_not_fail=11、G5c_artifact_ratio_ge_0.5=8、G5a_pass_report_ge1=11、G5d_fail_not_dominant=8、G5b_pass_rows_ge3=8、G4_no_draft=9、G2_plan_closed=2",
              "start_offset": 1562,
              "end_offset": 1715,
              "occurrences": 1,
              "all_start_offsets": [
                1562
              ],
              "content_hash": "sha256:d4ad9fbe9ad5cf3f0252d64735667697eb6b8369621e8475955c0ace3dd669af",
              "resolvable": true
            }
          ],
          "status": "unresolved",
          "reason": "一门可阻断多单（多门计数之和大于单数）是可能解释，但报告未声明口径；本工序不臆断，保持 unresolved。"
        },
        {
          "entry_id": "unres-03",
          "issue": "图件 sha256_16 与论文级数值结论在本报告内不可复核",
          "evidence": [
            {
              "locator_id": "unres-03-ev",
              "locator_type": "markdown",
              "quote": "`papers/figures/w23_window_composition.png`（sha256_16 `00a0936204e0b70d`",
              "start_offset": 3963,
              "end_offset": 4035,
              "occurrences": 1,
              "all_start_offsets": [
                3963
              ],
              "content_hash": "sha256:a6657cdb8c3e4aff26ccfd9675ae83803199c42386cf1ab53789be3b36d7dc7f",
              "resolvable": true
            }
          ],
          "status": "unresolved",
          "reason": "报告只给 sha256_16 前缀与图件路径，本工序按契约不读附件/外部仓，故图件完整性不在本包能力内，登记为 unresolved 而非通过。"
        }
      ],
      "limitations": [
        "registry identify_signals 为英文词表，本报告为中文正文：六型中仅 1 型有机械命中（technical-proposal）；该型唯一命中词 `plan` 共 18 次，其中独立（非文件名/标识符内）出现 4 次，其余落在 `research_plan*`/`w23_plan*.py`/`G2_plan_closed` 等工件名内部。按预声明规则 R4/R5，命中型数仅 1 < 2，故 confidence 封顶 medium，不能升到 high；其余五型 registry 命中 0，不得凭中文语感硬判。",
        "本地中文代理信号集为**本工序声明的补充口径**（proxy-zh-v1），不在 registry 内，仅用于交叉检验与置信度下调，不作为类型判定的唯一依据。",
        "本工序不做抽取：claims=[]；分类是可反驳假设，错分会由 03/04 工序以「claim 与原文类型不符」暴露。",
        "所有 locator 均为逐字子串定位（start_offset/end_offset/content_hash），报告可能存在的措辞级不一致不被平滑。",
        "没有把任何结论标成 verified：verification 由平台门计算。"
      ],
      "self_check_hint": "见 kf_result.json outputs.classification.json.self_check 与报告 ⑥ 自检表",
      "acceptance_self_check": {
        "valid_json": {
          "pass": true,
          "how": "json.dumps(...) round-trip of both artifacts"
        },
        "schema_pass": {
          "pass": true,
          "how": "jsonschema.validate against schemas/kf_result.v1.schema.json"
        },
        "source_locator_resolvable": {
          "pass": true,
          "locators_checked": 20,
          "locator_ids_unique": 20,
          "locators_failed": 0,
          "how": "md[start:start+len(quote)] == quote and sha256(quote) == content_hash"
        },
        "source_hash_matches": {
          "pass": true,
          "recomputed": "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9",
          "contract": "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9",
          "chars": 6258,
          "contract_chars": 6258
        },
        "no_duplicate_ids": {
          "pass": true,
          "ids": 40,
          "duplicates": []
        },
        "all_claims_have_evidence_or_explicit_unresolved_status": {
          "pass": true,
          "entries_without_evidence": [],
          "note": "this package emits zero claim records (工序02 不做抽取); every labelled item carries an evidence locator or status=unresolved",
          "claim_count": 0
        }
      },
      "figure": {
        "path": "work/wp-14214-02/figures/wp14214_02_signal_profile.png",
        "kind": "diagnostic"
      }
    }
  }
}
```
