# 报告→知识生产线规范 v1（PRODUCTION-LINE-v1）

**锚点**：`KBM-RCI-F1-SPEC`｜**单号**：m15494｜**状态**：v1 规范 + 可执行门禁落地（2026-11-12）
**适用**：近万份平台报告的批量知识加工。本文件是**架构层规范**，不含任何领域词条/领域判据；
领域内容（船舶、冰区、求解器语义）归领域仓与本仓 `knowledge/` 数据面，不进规范与代码。

**为什么需要规范**：万份报告的加工必须可拆解、可并行、可机器验收。没有契约就没法并派，
没有门禁就没法并收，没有独立审核就会把"任务成功"当成"知识正确"。本规范同时给出
**四种产物**：契约 JSON Schema、可执行门禁（`ke/wp_gate.py`）、规则清单
（`docs/production/GATE-RULES.md`）、抽取技能库（`extraction-skills/`）。

---

## 0. 一句话架构

> 一份报告 → 一个工作包（§1）→ 走五工序（§2）→ 过三道门（§3）→ 入 KE 四契约
> （claim / evidence / provenance / review-event，**复用**现有 `schemas/`）→ 综合研究只在
> 基础加工完成后启动（§2.5）。

三层职责分离，且由代码强制：

| 层 | 谁做 | 产物 | 不能做的事 |
|---|---|---|---|
| 生产 | 普通 Agent（标准工序） | claims/evidence/provenance/summary | 不能自称已验证、不能编造缺失信息 |
| 机器验收 | `scripts/validate_work_package.py` | `gate-report.json` | 不能判定语义保真、不能给 L3 |
| 独立审核 + 综合 | 独立审核 Agent / 强模型抽样 / 综合 Agent | `review_events.json`、`synthesis.json` | 不能看生产者解释；不能越级给 L3（平台验证单才行） |

---

## 1. 标准工作包契约 v1

**机读定义**：`schemas/work-package-contract.schema.json`（JSON Schema 2020-12，
校验器可直接 `$ref`）。owner YAML 是规范源，schema 是其可执行编码；两者冲突时以 owner YAML
为准并回改 schema。

一个工作包 = 一个目录 = `work-package.json`（契约）+ 声明的产物：

```
<package_id>/
  work-package.json          # 本文 §1 的契约实例
  claims.json                # 03 工序产物：claim-record 数组
  evidence.json              # 03 工序产物：evidence-record 数组
  provenance.json            # 03 工序产物：provenance-record 数组
  extraction_summary.json    # 03 工序产物：覆盖度/计数/空集理由（producer 自述）
  unresolved.json            # 可选：已识别但定不到位的 claim（显式挂账）
```

**生产者可写的目录里不允许出现审核台账与验证单**（S15）：`review_events.json` 属 04 工序包，
`verification_ticket.json` 属平台。03 包若自带这两者 → G1 直接失败（否则生产者可以自批自证）。
生产 runner 从**调用方指定**的路径读它们：

```
<ledger_dir>/<package_id>.review_events.json      # 审核台账（04 工序 / 平台审核存储）
<tickets_dir>/<package_id>.verification_ticket.json  # 平台验证单（L3 唯一入口）
```

### 1.1 字段（03 knowledge-extraction 分支为完整规格）

| 字段 | 取值 | 机检 |
|---|---|---|
| `package_id` | `^wp-[a-z0-9-]{3,64}$`，一报告一工序一包，**不复用** | S3 |
| `task_type` | 五工序之一（§2） | S3 |
| `version` | 契约版本（semver），当前 `"1.0.0"` | S3 |
| `input.report_id` | `tensor_reports.id` | S14（+ E1 解析） |
| `input.source_uri` | `tensor://reports/<id>` / `file://` / `https://` | S3 |
| `input.source_hash` | `sha256:<64hex>`，覆盖 `source_field` 指定的文本，**字节精确（不做换行归一）** | E2 |
| `input.source_field` | 03 分支固定 `markdown`（报告正文；只有它能出 claim） | S3 |
| `input.attachments` | 附件数组；**非空必须给 `attachments_manifest`**（按 manifest 解析，不猜） | S3 |
| `objective` | 03 固定五项且全 `true`：`identify_research_question / extract_methods_and_claims / extract_evidence / identify_assumptions / identify_limitations` | S3 |
| `output` | 03 固定四文件：`claims.json / evidence.json / provenance.json / extraction_summary.json`（多一个少一个都不行） | S3, S7 |
| `constraints` | 五项恒 `true`：`every_claim_must_have_source_locator / do_not_invent_missing_information / preserve_uncertainty / no_forced_claim_generation / do_not_mark_claims_as_verified` | S3, S8, S9 |
| `acceptance` | 六项恒 `true`：`valid_json / schema_pass / source_locator_resolvable / source_hash_matches / no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status` | S2, S4/S5, S6, S11, E2/E3 |
| `review` | `required:true`、`independent_reviewer:true`；可选 `reviewer_role`/`sample_rate`/`strong_model_sample_rate` | M1–M3 |
| `delivery` | `repo:"TensorKnowledge"`、`status:"draft"`（03 分支锁死 draft，交付不等于验证） | S3 |

### 1.2 `no_forced_claim_generation` = 零 Claim 合法

无价值结论的报告返回**空集**，不得为 KPI 编造知识。机器判据：

* `claims.json == []` → `extraction_summary.empty_result.is_empty` 必须 `true` 且
  `reason` ≥ 20 字符（S12）；
* 空包可以过 G1+G2，但验证级别被钉在 **L1**（`EMPTY_PACKAGE_NO_CLAIM_TO_VERIFY`）——
  没有 claim 就没有"证据绑定"可言（V 阶梯 §3.4）；
* 已识别但定不到位证据的 claim 进 `unresolved.json`（`status:"unresolved"` + 理由），
  既不算编造也不算丢弃；`counts.unresolved_claims` 必须与之一致。

---

## 2. 五工序

| 工序 | task_type | 难度 | 并行度 | 输入 | 产物 | 出口门 |
|---|---|---|---|---|---|---|
| 01 资产登记 | `01-asset-registration` | 低 | **极高**（纯 I/O，可按 id 分片） | 报告 id + 附件 manifest | `asset_manifest.json`（源哈希、附件清单、可达性） | G1 |
| 02 分类解析 | `02-classification-parse` | 低 | 高 | asset_manifest + 正文 | `classification.json`（六分型 + 结构切分 + 选中 skill_id） | G1 |
| 03 知识抽取 | `03-knowledge-extraction` | 中 | 高（一报告一包） | 正文 + skill | 四契约文件 + summary + unresolved | **G1+G2** |
| 04 独立审核 | `04-independent-review` | 中 | 高 | **原文 + 知识对象** | `review_events.json` + `review_report.json` | **G3** |
| 05 综合研究 | `05-synthesis-research` | 高 | 低（依赖收敛） | 多个**已完成**上游包 | `synthesis.json` | G1 + G3 |

### 2.1 工序 01 资产登记（低难 / 极高并行）

只做可程序化的事：拉取报告记录、算 `source_hash`、解析附件 manifest、标记不可达。
**不做判断**：不分类、不抽取、不改写。失败模式=把不可达源标成"已完成"，让下游在 G2 才发现。

### 2.2 工序 02 分类解析

按 `extraction-skills/registry.json` 的 `identify_signals` 决定报告类型并选中 skill。
分类是**可反驳的假设**：`report_type:"unclassified"` 是合法值，必须如实标注（禁止硬猜）；
错分会导致用错 skill，G3 会以"claim 与原文类型不符"暴露。

### 2.3 工序 03 知识抽取（一报告一包）

* 每条 claim 必有 locator：`locator_type` + `value` + `start_offset` + `end_offset` +
  **逐字 `quote`** + `content_hash`（quote 的 sha256）。数字必须出现在 quote 里，
  自己格式化=编造（G2 逐字比对）。
* statement 不得比原文强：条件、范围、不确定性词原样保留（"preserve_uncertainty"）。
* `epistemic_status` 一律 `draft`；`assessment_status` 一律 `unassessed`——
  生产者没有资格给证据定性（S8/S9 机检）。

### 2.4 工序 04 独立审核（G3）

**审核者上下文 = 原文 + 知识对象，禁看生产者解释**：
`ke/wp_gate.build_review_request()` 只带 `source / claims / evidence / provenance`，
并把 `extraction_summary`（含 `self_assessment`、`producer_rationale` 一类自由散文）
列入 `excluded`；`context_leaks()` 递归扫描，出现禁字段即 **M5 失败**（测试
`test_context_leaks_detects_injected_producer_explanation`）。

**审核 prompt 不得复制生产 prompt**：生产 `extraction-skills/prompts/producer-v1.md`
（要逐字抽取）与 `reviewer-v1.md`（要从原文反驳）分开维护；`prompt_similarity()`
用字符 5-gram Jaccard 计量，**要求 < 0.5**（实测 0.126）。把生产 prompt 塞给审核者
→ M4 失败（测试 `test_reviewer_prompt_is_not_the_producer_prompt`）。

审核结论以 append-only `review_events.json` 落账，状态机**复用**
`scripts/ke_state_machine.py`（不重写）：`draft→in-review` 是系统转移（任务完成），
`approve/request-changes/reject/revoke/deprecate` 是审核决定；自审（含别名/同会话 token）
一律 `SELF_APPROVAL_BLOCKED`。

### 2.5 工序 05 综合研究（高难，禁全交普通 Agent）

* 准入：`input.upstream_packages` 非空，且每个上游包在 `gate-report.json` 里
  `verdict=PASS_PROGRAMMATIC_PENDING_REVIEW` 且 `review_state=approved`；
  schema 要求 `acceptance.upstream_packages_completed:true`，G1 复核声明与报告是否一致。
* **必须在基础加工完成后**：否则缺全局信息，反复得出重复结论（这是上一轮的真实浪费）。
  机器判据=上游未完成则拒绝启动，而不是"边跑边补"。
* 综合产物只允许**跨报告**断言（contradiction / gap / 一致性），单报告 claim 的复述
  退回 03。

---

## 3. 三道门

规则逐条清单（含每条对应的代码位置与测试）见 **`docs/production/GATE-RULES.md`**。
可执行实现：`ke/wp_gate.py`，CLI `scripts/validate_work_package.py`。

| 门 | 名称 | 性质 | 规则 | 判定者 |
|---|---|---|---|---|
| G1 | 结构门 | 程序化 | S1–S15：JSON 合法 / 契约与记录过 schema / ID 唯一 / 字段完整 / xref 闭合 / 计数一致 / 源身份一致 / 零 claim 合法 / 生产者不得自称验证 / 不得自带审核材料 | 校验器 |
| G2 | 证据门 | 程序化 | E1–E7：源可达 → `source_hash` 一致 → locator 反查原文可达 → 片段逐字匹配（偏移精确）→ quote 哈希一致 → quote 非平凡 → 每条 claim 有可解析证据 | 校验器 |
| G3 | 语义门 | **不可程序化** | M1–M5：审核必配且必须独立 / 台账合法（复用状态机）/ 审核者独立 / prompt 不复制生产 prompt / 审核上下文不含生产者解释；**语义保真判定=独立审核 Agent + 抽样强模型，代码只能 `not_run`** | 独立审核 Agent |

三条铁律：

1. **程序化门不给"通过"以外的自由度**：源不可达、locator 定不到位、哈希不一致 → FAIL，
   不允许 skip（`test_unreachable_source_fails_closed`）。
2. **G3 不由代码通过**：`semantic.pass` 恒为 `null`，`status` 恒为
   `pending-independent-review`；CLI 成功只输出 `PASS_PROGRAMMATIC_PENDING_REVIEW`。
3. **门禁产物是证据工件**：`gate-report.json` 逐条记录规则/结论/detail，零手抄。

### 3.4 三状态分离律（写死）与 `verification_status` 状态机

> **mission succeeded ≠ KO 审核通过 ≠ 科学结论验证通过**

三条轴各自记账，任何一条都不得由另一条推导：

| 轴 | 载体 | 取值 | 谁能写 |
|---|---|---|---|
| 任务轴 | TensorPlatform mission | running / succeeded / failed | 平台 |
| 审核轴 | `review_events.json` → fold → `review_status` | draft / in-review / approved / rejected / deprecated | 独立审核者（状态机复用） |
| 验证轴 | `verification_status`（**门禁计算，禁止生产者写**） | L0 / L1 / L2 / L3 | 门禁 + 平台验证单 |

`verification_status` 阶梯（`ke/wp_gate.verification_level`，规则 V1–V5）：

| 级别 | 名称 | 机器前置条件 | 典型封顶理由码 |
|---|---|---|---|
| **L0** | declared | 记录存在，未过任何门 | `STRUCTURAL_GATE_FAILED` |
| **L1** | structural | G1 全过 | `EVIDENCE_GATE_FAILED` / `EMPTY_PACKAGE_NO_CLAIM_TO_VERIFY` |
| **L2** | evidence-bound | G1 + G2 全过 | `REVIEW_NOT_APPROVED` / `MISSING_PLATFORM_VERIFICATION_TICKET` |
| **L3** | verified | L2 + `review_status=approved` + **平台验证单** `gate=confirmed`、`issued_by` 非空、`package_id` 与 `claims_sha256` 均匹配 | `TICKET_UNSIGNED` / `TICKET_NOT_CONFIRMED` / `TICKET_PACKAGE_MISMATCH` / `TICKET_CLAIMS_DIGEST_MISMATCH` |

**L3 只经平台验证单 + gate confirmed**：本仓任何 Agent（含架构 Agent、审核 Agent）都不能
把级别写成 L3；生产者在记录里写 `verification_status`/`verified` 字段 → G1 直接失败
（S9）。验证单结构见 `verification_ticket.json`（`ticket_id / gate / package_id /
claims_sha256 / issued_by / issued_at`），缺字段或摘要不符一律封顶 L2 并给出理由码。

---

## 4. Extraction Skill Library（抽取技能库）

目录 `extraction-skills/`，注册表 `registry.json`（schema：
`schemas/extraction-skill.schema.json`）。

六类报告分型（初始模板骨架已落地，六份 skill 文件 + `_TEMPLATE.md`）：

| report_type | skill_id | 识别信号（示例） |
|---|---|---|
| literature-review | `xsk-literature-review` | related work / survey / bibliography / 引文密度 |
| scientific-computation | `xsk-scientific-computation` | 控制方程 / 离散 / 收敛研究 / 参数表 |
| algorithm-implementation | `xsk-algorithm-implementation` | 伪代码 / 复杂度 / 函数签名 |
| software-engineering | `xsk-software-engineering` | 变更文件 / commit / 接口 / 回归 |
| technical-proposal | `xsk-technical-proposal` | proposal / design / specification |
| experimental-validation | `xsk-experimental-validation` | test matrix / 不确定度 / 基线对比 |

**生命周期**（`ke.wp_gate.validate_skill_registry` 规则 K1–K6 强制）：

```
candidate → template-created → sample-tested → independent-review → registered → deprecated
             (有文件)          (≥1 真实样本包过 G1+G2+G3) (他审)        (review_event_id+reuse_count)
```

* **先识别有无**：新建前必须按 `report_type` + `identify_signals` 查重（同型同信号两套 skill
  = 缺陷）；`scripts/build_ke_mapping.py` 时代的教训：不查重就重复造。
* **无则建模板**：拷贝 `_TEMPLATE.md`，状态 `template-created`。
* **代表样本测试**：必须跑**真实报告**整线（G1+G2+G3）；`sample_tests[]` 记 report_id +
  source_hash + outcome。合成 fixture 不算样本（它测门禁，不测技能适用性）。
* **独立审核**：作者以外的人记录审核事件 → `independent-review`。
* **入库 + 复用计数**：`reuse_count` 由生产 runner 递增；`deprecated` 必须写理由（负知识不删）。
* **方向参考 CACHE-ED2**：对新文档格式先生成可复用抽取程序，同类后续**确定性执行**——
  skill 文件是抽取程序的规格，`ke/wp_gate.py` 是验收执行器。

**诚实状态**：六个 skill 全部停在 `template-created`。尚无任何真实报告走完 G3，
因此没有任何 skill 声称 `sample-tested` / `registered`；生命周期转移本身在
`tests/test_wp_gate.py` 里用注册表副本验证（验证规则，不是验证技能）。

---

## 5. 角色组织（两层）

**第一层：六个职业角色**（职责，不是头衔；`work-package-contract.schema.json`
的 `review.reviewer_role` 枚举）：

| 角色 | 负责 | 不得 |
|---|---|---|
| Document Analyst | 工序 01/02：登记、分型、切分 | 不出 claim |
| Scientific Extractor | 工序 03：抽 claim/evidence | 不自审、不写 validation 字段 |
| Evidence Auditor | 工序 04：locator 反查、逐字比对 | 不看生产 summary；不与生产者同一人 |
| Domain Specialist | 高危/专业 claim 的领域裁定 | 不代写知识（只裁定） |
| Knowledge Integrator | 工序 05：跨报告综合、去重、矛盾登记 | 不在基础加工未完成时启动 |
| Red Team Reviewer | 对抗性抽样：过度推断、范围漂移、伪造风险 | 不复用生产 prompt |

**第二层：同职业多独立工作者**——同角色可并行 N 人，**保留个体差异**（不要求同一模型、
同一措辞），但**任务契约统一**（同一 `work-package.json` 结构、同一门禁、同一产出格式）；
审核者与生产者身份由 `ke_state_machine.is_independent` 判独立（同会话 token/别名一律阻断）。

**初始配比 80/20**：生产（01–03）: 审查（04+红队）= 80:20。抽样策略：
`review.sample_rate`（默认 1.0 首轮全审；稳定后可 >0 小于 1 抽样）+
`strong_model_sample_rate`（抽样里再由强模型复核的比例，首轮 1.0）。
配比可调，但"审核者≠生产者"和"prompt 不复制"不可关（schema `const true`）。

---

## 6. 范围令（不扩充治理、不另建平台）

* **复用**：KE（`ke/` 存储/查询/校验）、四契约（`schemas/claim-record | evidence-record |
  provenance-record | review-event`）、审核状态机（`scripts/ke_state_machine.py`）、
  checks/schema 工具（`scripts/sediment_lib.py`）。本规范**不新增存储引擎、不新增数据库表、
  不新增治理文档体系**：`governance/` 不动。
* **新增仅四类交付物**：①契约 schema 三件（work-package / extraction-summary /
  extraction-skill）；②门禁实现 `ke/wp_gate.py` + CLI；③规则清单 + 本规范（`docs/production/`）；
  ④技能库骨架（`extraction-skills/`）。测试与 fixture 属其验证面。
* **不做**：不启动万份批跑（需 m15462 分层清单 + 平台调度）；不实现 05 综合调度器；
  不接管 TensorPlatform 的 mission/DAG（那是平台共性机制）。
* **对接**：m15461（Schema v1）定稿后以本仓三 schema 为准做字段对齐（本单未就绪，
  按 owner YAML 先行，schema 已按 YAML 逐字落码）；m15462 分层清单=试点批次输入。

---

## 7. 怎么跑（可执行面）

```bash
# 单包（离线源；默认读 <package>/../sources）
python scripts/validate_work_package.py tests/fixtures/extraction/ok-basic \
    --sources tests/fixtures/extraction/sources

# 批量扫（生产 runner 用这个；在线解析 $TENSOR_API_BASE 的报告原文）
python scripts/validate_work_package.py --root knowledge/extraction \
    --online --review-ledger-dir knowledge/reviews --tickets-dir knowledge/tickets \
    --skills extraction-skills/registry.json --json runs/gate-report.json

# 重新生成离线 fixture（由两份合成源推导，禁止手改）
python scripts/build_extraction_fixtures.py

# 门禁自测
python -m pytest tests/test_wp_gate.py -q
```

退出码：`0` 两门程序化全过（语义门仍 pending）、`2` 有 G1 失败、`3` 有 G2 失败、
`4` 技能库校验失败、`5` 用法错误。

---

## 8. 诚实状态与未完成项（2026-11-12）

**已完成并机器验证**

| 项 | 证据 |
|---|---|
| 契约 v1 落成可 $ref 的 JSON Schema（含 03/04/05 分支、附件 manifest、恒真约束） | `schemas/work-package-contract.schema.json`，测试 8 项 |
| 结构门 + 证据门可执行（S1–S15 / E1–E7，22 条规则） | `ke/wp_gate.py`，8 个夹具包各触发一类失败 |
| 三状态分离 + V 阶梯（L3 需已签发的平台验证单，且不得来自生产者目录） | `verification_level()` + S15 + 7 项测试 |
| 审核包上下文隔离 + prompt 独立性可度量 | `build_review_request/context_leaks/prompt_similarity`，Jaccard 实测 0.126 |
| 技能库六分型骨架 + 生命周期机检（K1–K6） | `extraction-skills/`，注册表 6/6 检查通过 |
| 规则清单可执行优先 | `docs/production/GATE-RULES.md`，40 项 pytest 全绿 |
| 对抗性自审发现并修复的漏洞 | 生产者自带 `review_events.json`/`verification_ticket.json` 原可自批自证 → 新增 S15 + 台账/验证单改由调用方路径提供（测试 `test_producer_cannot_ship_its_own_approval_or_ticket`） |

**未完成（如实报告，不粉饰）**

1. **没有真实报告跑完整线**：本单交付规范与门禁，夹具是合成源。真实样本的
   `source_hash`/locator 行为（尤其中文 markdown 的字符偏移、图表附件）尚未实测。
2. **G3 未自动化**：语义门由 Agent 执行；本单只给审核包生成器与独立性检查，
   没有审核 Agent 的排产与结果回收（待平台调度）。
3. **工序 01/02/05 只有契约分支与规则，没有 runner 实现**：本单是"定规则"，
   runner 属后续平行 Worker 任务。
4. **与 m15461 Schema v1 未合并**：本单按 owner YAML 先行，字段若与 m15461 冲突需对齐一轮。
5. **未做万份规模压测**：批量扫的吞吐/并发未测（预计瓶颈在 G2 的源拉取，非校验逻辑）。
6. **验证单无密码学签名**：现在只能校验 `issued_by` 非空 + 摘要匹配 + 不得来自生产者目录；
   真正防伪要靠平台侧签发与存储权限（本仓无权实施）。

## 9. 判据自检（本规范可被反驳的地方）

| 判据 | 结论 |
|---|---|
| 关键量 vs 基准误差 | 本单无数值求解；**量化判据替代为**：门禁规则可执行率、夹具期望行为命中率。40/40 测试通过；8 个夹具包的 verdict 与设计一致（见 GATE-RULES 表） |
| 精度标准（>15% 不可接受） | 不适用（无物理量）；但 `prompt_similarity` 阈值 0.5 与 `min_quote_chars=12` 是**可调判据**，不是物理精度 |
| 诚实 FAIL | 无：未达标项已列入 §8，未包装成"已完成" |
| 零手抄 | 夹具由 `scripts/build_extraction_fixtures.py` 从源文本推导；本文件所有数字来自该脚本输出与 pytest 输出 |