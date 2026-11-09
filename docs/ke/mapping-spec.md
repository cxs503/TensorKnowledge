# 四契约 → 知识引擎存储/检索映射规格 v0.1

**状态**：draft for review（本仓 review 状态独立于 TensorPlatform 任务验收，见 §4.6）
**锚点**：FEAT-TK-KNOWLEDGE-ENGINE（mission m8619，branch `agent/m8619`）
**适用契约**：`schemas/claim-record.schema.json`、`schemas/evidence-record.schema.json`、
`schemas/provenance-record.schema.json`、`schemas/review-event.schema.json`（均 v1.0.0），
以及聚合体 `schemas/knowledge-object.schema.json`
**规范词**：MUST / MUST NOT / SHOULD / MAY 按 RFC 2119 语义使用。

配套制品（全部在仓内，可复核）：

| 制品 | 内容 |
|---|---|
| `scripts/ke_mapping_lib.py` | **可执行的投影规范**：字段级规则表 `RULES`、保守性阶梯、双时态、身份解析、四类查询的参考实现 |
| `scripts/ke_state_machine.py` | 状态机可执行形式 + 9 例一致性用例（§4） |
| `scripts/build_ke_mapping.py` | 由冻结快照生成 `mappings/m8554.json`（零手抄） |
| `scripts/validate_ke_mapping.py` | 18 项门槛校验（结构/语义/接口），产出 `runs/ke_mapping_validation.json` |
| `scripts/render_ke_audit.py` | 由上述两份 JSON 生成 `docs/ke/m8554-audit.md` |
| `mappings/m8554.json` | m8554 试点包 19 条记录（4 claim + 8 evidence + 3 provenance + 3 KO + 1 envelope）的逐条映射 + 损耗登记 + 检索演示 |
| `mappings/source/m8554/` | 试点包只读冻结快照（分支 `agent/m8554` @ `727ac18`），每记录 `raw_sha256` 钉死 |
| `schemas/ke-mapping.schema.json` / `schemas/ke-query.schema.json` | 映射文档结构 / 检索接口请求-响应 schema |

> 本文档是**规范**；`scripts/ke_mapping_lib.py:RULES` 是**可执行形式**。二者不重复叙述：
> 逐字段的完备清单以规则表为准，`validate_ke_mapping.py` 的 A3 检查每次都用规则表**重新推导**
> 一遍映射并与提交的 `mappings/m8554.json` 比对，规则与文档漂移即 CI 红。

---

## 0. 范围与非目标

**范围**：给定一条已通过契约 schema 校验的记录，规定它在知识引擎里**存成什么**
（实体 / 边 / 向量 facet）、**检索时能回答什么**、以及**什么信息会掉**（损耗登记）。

**非目标（v0.1 明确不做）**：

1. 不引入数据库选型。本文档只定义逻辑模型（§1），关系库/文档库/图库/向量库都必须能满足。
2. 不实现服务。§8 是接口草案；参考实现是进程内 `Projection` 类，跑的是真实记录（§9 有实测输出）。
3. 不做嵌入模型选型，也不建索引（`index_status = declared-not-built`）。
4. 不做自动蕴涵判定（NLI）。v0.1 明确禁止把相似度当支撑（§7.3）。
5. 不改四个契约 schema。凡是契约表达不了的信息，一律进损耗登记（§9.3），
   不靠"引擎侧补字段"打补丁——补字段等于偷偷扩契约。

---

## 1. 逻辑存储模型

四个契约是**记录**（record），引擎里是**实体**（entity）+ **边**（edge）+ **facet**（向量）。
记录本身永远整份保留：

```
ke.entity      (entity_id, entity_kind, contract, contract_version, raw, raw_sha256,
                recorded_at, valid_time_start, valid_time_end, valid_time_resolution,
                status_epistemic, status_review, status_evidence, status_publication,
                flags[])
ke.edge        (edge_id, subject, predicate, object, attrs, recorded_at, append_only = true)
ke.facet       (facet_id, entity_id, facet, text, text_sha256, language, embedding, filters)
ke.review_event(id, object_ref, object_version, decision, reviewer, reviewed_at,
                policy_version, supersedes_event, findings[])          -- 只追加
ke.source      (source_key, source_type, citation, published_at, accessed_at, rights)
ke.identity    (identity_key, aliases[], tokens[], source_of_alias)
```

**MUST-1.1** `raw` 必须逐字保留原记录；`raw_sha256` 对规范化 JSON（`sort_keys`、UTF-8）取 SHA-256，
并可由快照复算（校验项 A2）。投影是**派生的、可重建的**；`raw` 才是权威。
**MUST-1.2** `entity_id` 逐字等于契约的 `id`，不重写、不加前缀、不转小写。
**MUST-1.3** 引擎不得创建契约未定义的实体种类去承载"更好的模型"；派生节点只有三类：
`activity`、`agent`、`source-node`——它们**由** provenance/evidence 记录机械展开，不带自有断言。
**MUST-1.4** `edge_id` 由 `sha256(subject|predicate|object|discriminator)` 截断 16 位生成，
使导入幂等：同一记录重复导入不产生平行边。

契约 ↔ 实体种类（T-2.1）：

| 契约 | `entity_kind` | 主键 | 备注 |
|---|---|---|---|
| claim-record | `claim` | `id` (`tkc:*`) | 契约**无** `review_status` 字段（见 D-09） |
| evidence-record | `evidence` | `id` (`tke:*`) | 契约**无** `valid_time` 字段（见 D-01） |
| provenance-record | `provenance` | `id` (`tkp:*`) | 派生 `activity` / `agent` 节点 |
| review-event | `review-event`（账本，非实体表） | `id` (`tkr:*`) | 只追加；`review_status` 是它的 fold（§4.1） |
| knowledge-object | `knowledge-object` | `id` (`tko:*`) | 聚合体，`review_status` 的**唯一**载体 |
| production-result | `production-result` | `tkm:platform:<mission>` | 平台侧信封；其 `execution_state` **不得**用于 review（§4.6） |

每条记录的**叶子字段路径**（含数组下标）必须落在以下五类之一（T-2.2）：

| 类别 | 含义 | m8554 实测（19 记录 / 509 叶子） |
|---|---|---|
| L0 | 逐字可查询 | 304 |
| L1 | 归一化后可查询，原值在 `raw` 里 | 41 |
| L2 | 展开为图结构（节点+边承载同一信息） | 128 |
| L3 | 仅存 `raw`，按政策不做查询列（自由散文、去规范化副本） | 36 |
| L4 | 引擎模型**表达不了**（语义损耗，必须进登记册） | 0 叶子；10 条记录级损耗（§9.3） |

**MUST-1.5** 任何叶子路径若既未命中投影规则、也未进损耗登记，构建器必须报失败
（`build_ke_mapping.py` 以非零退出）；这是"无损耗或有显式披露"的机器化形式。

---

## 2. 实体投影（字段级语义）

### 2.1 claim-record

| 契约字段 | 引擎落点 | 类 | 语义要点 |
|---|---|---|---|
| `id` | `entity.entity_id` | L0 | 主键 |
| `statement` | `claim.statement` | L0 | 向量 facet `claim.statement` |
| `claim_type` | `claim.claim_type` | L0 | 闭集，不做同义归并 |
| `scope.domain/population/system/geography` | `claim.scope.*` | L0 | by-domain 的域面 |
| `scope.conditions[*]` | `claim.scope.conditions[]` | L0 | **MUST-2.1** 命中即随结果返回，不得被检索层裁掉 |
| `scope.exclusions[*]` | `claim.scope.exclusions[]` | L0 | 同上 |
| `modality` | `claim.modality` | L0 | |
| `epistemic_status` | `status.epistemic_status` | L0 | **as-authored**，另存 `policy_cap`/`over_grade`（§5） |
| `evidence_refs[*]` | 边 `EVIDENCE_OF` | L2 | **MUST-2.2** 与 evidence 侧 `claim_refs` 双向对称性必须校验；不对称→导入告警 |
| `relation_refs[*]` | 边 `CLAIM_RELATED` | L2 | |
| `valid_time.start/end` | `bitemporal.valid_time.*` | L1 | 归一化到 UTC |
| `valid_time.description` | `bitemporal.valid_time.description` | L0 | 散文有效性说明（§6.3） |
| `created_at` | `bitemporal.recorded_at` | L1 | 事务时间轴 |
| `created_by` | `recorded.created_by.raw` | L0 | 同时解析出 `identity_key`（§4.4） |
| `supersedes[*]` | 边 `SUPERSEDES` | L2 | 追加式：不修改被取代行 |
| `notes[*]` | `claim.notes[]` | L0 | 作者自述局限随记录走 |

### 2.2 evidence-record

| 契约字段 | 引擎落点 | 类 | 语义要点 |
|---|---|---|---|
| `source.persistent_id / url / citation` | `ke.source` 节点键（按此优先序，末位退化 `sha256(citation)`） | L0 | 源节点**去重**，多证据共享一节点 |
| `source.published_at` | `source.published_at` | L1 | **MUST-2.3** 日精度→`date@00:00Z` 并记 `precision=date`；**不得**当作 validity 边界（§6.1） |
| `source.accessed_at` | `source.accessed_at` | L1 | 抓取时点 |
| `source.rights` | `source.rights` | L0 | 引用/权利限制随引文一起返回 |
| `relation` | `edge.relation` | L0 | **MUST-2.4** 关系在**边**上，不在实体上（一条证据可支撑多个命题） |
| `locator.locator_type/value` | `evidence.locator_*` | L0 | 定位器必须可人工复核 |
| `locator.quote` | `evidence.quote` + facet `evidence.quote` | L0 | `quote_sha256` 取**抓取时**引文（含省略号），不做"修复" |
| `locator.quote_language` | `evidence.quote_language` | L0 | **MUST-2.5** 检索不得假定引文与命题同语种（本试点引文 8/8 为 en、命题 4/4 为 zh） |
| `extraction_method` | `evidence.extraction_method` | L0 | §5 阶梯的"直引"门 |
| `captured_at` / `captured_by` | `bitemporal.recorded_at` / `recorded.captured_by.raw` | L1/L0 | |
| `assessment_status` | `evidence.assessment_status` | L0 | **必须**与 `review_status` 分轴（§4.6） |
| `assessment.*` | `evidence.assessment.*` | L0 | 本试点 8/8 缺该块（D-05 相关，见 §9.3） |

### 2.3 provenance-record（PROV-O 对齐）

| 契约字段 | 引擎落点 | 类 | 语义要点 |
|---|---|---|---|
| `generated_entity.id/entity_type/version` | `prov.generated_entity.*` + 边 `GENERATED` | L0/L2 | **MUST-2.6** 粒度如实保留：本试点指向 scenario 包，不是单条 claim（D-05） |
| `activity.id/type/description/started_at/ended_at` | `activity` 节点 + `prov.activity.*` | L0/L1 | PROV `prov:Activity` |
| `activity.used_entities[*]` | 边 `USED` | L2 | 本地 id→实体节点；外部 URL→`external` 节点（未解析即进 `gaps[]`） |
| `activity.software[*].version` | `prov.software[].version` | L0 | **MUST-2.7** 空串→`version_unknown=true`，**不得**编造版本 |
| `agents[*]` | `agent` 节点 + 边 `WAS_ASSOCIATED_WITH` | L0/L2 | `external_id` 参与身份别名解析（§4.4） |
| `attributed_to[*]` | 边 `ATTRIBUTED_TO` | L2 | 归责≠著作，两条边并存 |
| `derived_from[*]` | 边 `DERIVED_FROM` | L2 | |
| `recorded_at` / `valid_time.*` | `bitemporal.*` | L1 | |
| `extensions` | `raw` only | L3 | 开放包不做查询面 |

### 2.4 knowledge-object（聚合体）

`review_status` 只存在于这一层（加上 review-event 账本）。KO 的 `evidence_status` 是**聚合信封态**，
**MUST-2.8** 不得反向覆盖其所含 claim 的 `epistemic_status`（两者不同轴、不同粒度）。
KO 的链接既可能写在 schema 指定的 `claim_refs/evidence_refs`，也可能写在开放词表的
`relations[{relation_type,target_id}]`（本试点 3/3 用后者、0/3 用前者，见 D-08）。
引擎两条都接受，开放词表按固定映射归一到闭集，并**在边上保留原文** `relation_type_raw`：

| `relation_type` 原文 | 归一后谓词 | `intent` |
|---|---|---|
| `supported-by-claim` | `KO_INCLUDES_CLAIM` | `supported-by` |
| `contested-claim` | `KO_INCLUDES_CLAIM` | `contested` |
| `status-claim` | `KO_INCLUDES_CLAIM` | `status-of` |
| `narrowed-claim` | `KO_NARROWS_TO` | `narrows` |
| 其它 | `KO_REL_UNMAPPED` | `unmapped`（不猜，进告警） |

---

## 3. 关系与边（含"两边保留"的结构性保证）

### 3.1 谓词表（T-3.1）

| 谓词 | subject → object | 基数 | 边属性 | 不变量 |
|---|---|---|---|---|
| `EVIDENCE_OF` | evidence → claim | N:1 | `relation`, `assessment_status`, `extraction_method`, `capture_quality` | 双向引用对称（MUST-2.2） |
| `CLAIM_RELATED` | claim → claim | N:N | | 不传递闭包 |
| `SUPERSEDES` | any → any | N:N | | 追加式；被取代行不改不删 |
| `GENERATED` | activity → entity/artifact | N:1 | | 粒度如实（MUST-2.6） |
| `USED` | activity → entity/source | N:N | | 外链未解析→`gaps[]` |
| `WAS_ASSOCIATED_WITH` | agent → activity | N:N | `role` | PROV-O 语义 |
| `ATTRIBUTED_TO` | record → agent | N:N | | 与著作权分离 |
| `DERIVED_FROM` | record → source/entity | N:N | | |
| `KO_INCLUDES_CLAIM` / `KO_INCLUDES_EVIDENCE` / `KO_INCLUDES_PROVENANCE` | KO → 子记录 | N:N | `intent`, `relation_type_raw` | |
| `KO_NARROWS_TO` | KO → 窄化 claim | N:N | | §3.3 的载体 |
| `HAS_REVIEW_EVENT` | object → review-event | 1:N | | 事件另存账本，边仅为索引 |
| `ARTIFACT_REF` | envelope → 路径 | N:N | `is_directory_hint` | 目录/文件混排如实标注 |

### 3.2 六种证据关系的检索语义（T-3.2）

| `relation` | 能抬高 `epistemic_status`？ | 说明 |
|---|---|---|
| `supports` | 可以（受 §5 阶梯约束） | 需 `capture_quality>=2`（定位器/引文/稳定标识三项至少占二） |
| `qualifies` | **不抬高，且压顶** | 使命题只能停在 `provisional`（窄化解读） |
| `refutes` | 不抬高，**改判为 `contested`** | 只要引文锚定且未被判 `insufficient` |
| `contextualizes` | 不抬高 | 语境，非蕴涵 |
| `mentions` | **不抬高** | 出现≠支撑（D-10 的坑：规划表里写"P0 export profile"不等于已实现） |
| `derived_from` | 不抬高 | 派生链，非证据 |

**MUST-3.1** `mentions` / `contextualizes` 永不参与"支撑计数"；把提及当支撑是本生态最贵的一类错误。

### 3.3 contested：两边保留的结构性保证（T-3.3）

本试点暴露了一个真实结构陷阱：宽命题 `tkc:fair:requires-open-access` 的边全是
`refutes`/`qualifies`/`contextualizes`，**它自己没有 `supports` 边**——可辩护的一侧是**另一条窄化命题**
`tkc:fair:a1-protocol-conditions`。因此"两边保留"不是某条 claim 的内部属性，而是**一个问题的属性**：

**MUST-3.2** 引擎表达 contested 的单元是「KO + `contested` 意图 + `KO_NARROWS_TO`」三元组；
`contested_pairs()` 输出必须同时带 `against[]`（反驳/限定/语境侧）与 `surviving_narrowed_sides[]`
（存活窄化侧及其支撑证据），并给出 `both_sides_retained` 布尔。

**MUST-3.3** 检索层**不得提供**任何"只要支撑侧"的参数。实现方式是 schema 层禁止：
`anchorRequest.expand` 的键集合里没有 `only_support`（`validate_ke_mapping.py` B8 每次检查），
`epistemic_view` 与 `evidence_partition` 的 7 个分片键是 `required`——空也必须出现，
这样"只返回一边"在结构上不可能通过校验。

**MUST-3.4** 反驳侧被判 `insufficient`（=已评估、不蕴涵）时不得再撑起 `contested`；
反之 `unassessed` 的锚定反驳侧**必须**撑起 `contested`（保守方向：未知的反向证据要压低置信，不能抬高）。

---

## 4. review-event 状态机：不自批

### 4.1 状态与决策（T-4.1）

`review_status` 是**账本的 fold**，不是可写列：

```
review_status(object) = fold( ledger[object_ref == object], initial = "draft" )
```

状态：`draft` · `in-review` · `approved` · `rejected` · `deprecated`
决策：`approve` · `request-changes` · `reject` · `revoke` · `deprecate`
进入评审（`draft → in-review`）是**系统转移**，故意不在 `DECISIONS` 里：它不能被写成一条"批准"，
也不能由评审者身份发起（`submit()`，见 `scripts/ke_state_machine.py`）。

### 4.2 转移表（T-4.2）——表外一律拒绝

| 当前态 | 决策 | 次态 | 结果码 | 额外前置 |
|---|---|---|---|---|
| `in-review` | `approve` | `approved` | `OK_APPROVED` | 独立性（SR-1..SR-5） |
| `in-review` | `request-changes` | `draft` | `OK_CHANGES_REQUESTED` | 必须带 `findings` |
| `in-review` | `reject` | `rejected` | `OK_REJECTED` | 必须带 `findings` |
| `approved` | `revoke` | `in-review` | `OK_REVOKED` | 独立性 + `supersedes_event` 指向该 approve |
| `draft`/`in-review`/`approved`/`rejected` | `deprecate` | `deprecated` | `OK_DEPRECATED` | — |
| 其它任意组合 | — | **状态不变** | `INVALID_TRANSITION` / `UNKNOWN_DECISION` | 记入 `refused_events`（可审计）但不改状态 |

**MUST-4.1** 未列出的组合必须**显式拒绝**（机器可读码），禁止静默 no-op。
**MUST-4.2** 事件 `policy_version` ≠ 生效政策时必须 `POLICY_MISMATCH` 拒绝应用（入账、状态不变），
避免用旧政策批准的结论悄悄生效。

### 4.3 不自批：身份规则（T-4.3）

评审者的"独立性"是对**对象及其可见生产者集合**而言的：

```
producer_ids(object) = { claim.created_by, evidence.captured_by,
                         KO.recorded.created_by,
                         provenance.agents[].id  (凡 GENERATED/USED 可达该对象者) }
```

| 规则 | 内容 | 结果码 |
|---|---|---|
| **SR-1** | `reviewer.identity_key ∉ producer_ids`（按 §4.4 别名闭包比较） | 违反→`SELF_APPROVAL_BLOCKED` |
| **SR-2** | `reviewer_type ∈ {organization, committee}` 视为独立 | 豁免 token 比较 |
| **SR-3** | 会话 token 与任一生产者 token 相同即视为同一生产者（**fail-closed**） | `SELF_APPROVAL_BLOCKED` |
| **SR-4** | `revoke`（撤回一次批准）同样要求独立评审者 | 违反→`SELF_APPROVAL_BLOCKED` |
| **SR-5** | SR-1/SR-4 未通过时**不得**写入 approve/revoke 边；尝试本身进 `refused_events` | 审计留痕 |

### 4.4 身份解析：本试点实测的别名漏洞（D-03）

m8554 的真实数据里，同一生产者出现了三个写法：

| 出现处 | 记录值 | 规范化 identity_key | 会话 token |
|---|---|---|---|
| 4 条 claim `.created_by` / 8 条 evidence `.captured_by` | `claude-code-session-6f76cd3d (glm-5.3, owner 亲自接管线)` | `claude-code-session-6f76cd3d` | `6f76cd3d` |
| 3 条 provenance `agents[0].id` | `cc-session-6f76cd3d` | `cc-session-6f76cd3d` | `6f76cd3d` |
| 3 条 provenance `agents[0].external_id` | `bg-job-6f76cd3d` | `bg-job-6f76cd3d` | `6f76cd3d` |

**MUST-4.3** 若用字符串相等判"是否同一人"，`cc-session-6f76cd3d` 批准 `tkc:...`
会以**通过**的方式被放行（两个字符串不同），不自批规则形同虚设。故引擎必须：

1. 抽取 8 位十六进制会话 token，做**别名闭包**；
2. token 相交即判同一生产者（SR-3，fail-closed）；
3. 别名关系落 `ke.identity`，可审计、可回滚；
4. `validate_ke_mapping.py` B1 对三条真实写法各发一次 approve，**全部必须被拒**（实测 3/3 拒绝）。

### 4.5 一致性用例（9 例，`scripts/ke_state_machine.py`）

| 用例 | 期望 |
|---|---|
| C1 生产者批自己 | `SELF_APPROVAL_BLOCKED` |
| C2 生产者的别名批自己 | `SELF_APPROVAL_BLOCKED` |
| C3 从 `draft` 直接 approve | `INVALID_TRANSITION` |
| C4 独立评审者在 `in-review` 批准 | `OK_APPROVED`（终态 `approved`） |
| C5 request-changes 缺 findings | `FINDINGS_REQUIRED` |
| C6 事件试图写 `epistemic_status` | `AXIS_VIOLATION_A3` |
| C7 revoke（带 supersedes_event） | `OK_REVOKED`（回到 `in-review`） |
| C8 旧 `policy_version` | `POLICY_MISMATCH` |
| C9 `rejected` 未经重提直接 approve | `INVALID_TRANSITION` |

### 4.6 三轴分离：平台态 / 评审态 / 证据态（T-4.5）

| 轴 | 取值 | 权威来源 | 谁不得写 |
|---|---|---|---|
| Platform mission state | `queued/running/awaiting_acceptance/succeeded/failed` | TensorPlatform | TensorKnowledge |
| `review_status` | `draft/in-review/approved/rejected/deprecated` | **只有** review-event 账本 fold | Platform 验收、证据评估、作者 |
| `evidence_status` / `assessment_status` | `established…not-assessed` / `unassessed…disputed` | 证据评估 | 评审决策（A3） |

**MUST-4.4** 信封 `execution_state`、`outcome` 只能存在于 `envelope.platform_state` 这类只读镜像位，
**不得**参与 `review_status` 推导。本试点实测：信封 `execution_state=completed`、
`outcome=accepted-for-review`，而 3 个 KO 的 `review_status` 全为 `draft`、账本 0 条事件——
校验项 B3 每次比对这三者，任何"任务完成即视为通过"的实现都会红。
**MUST-4.5** claim/evidence/provenance **契约本身没有 `review_status` 字段**，因此
"未评审"只能表达为 `fold(空账本) = draft` 并显式标注 `review_status_source=fold(empty-review-event-ledger)`；
**不得**渲染为 `approved`，也不得因缺字段而渲染为 `null`（D-09）。

---

## 5. epistemic_status 的保守性

### 5.1 阶梯与证据等级（T-5.1）

```
not-assessed  <  speculative  <  provisional  <  well-supported  <  established
（contested / superseded 为阶梯外状态：表达"有争议"/"已被取代"，不参与强弱比较）
```

证据侧输入两个正交量：**锚定质量** `capture_quality ∈ 0..3`（定位器 / 引文 / 稳定标识 各 1）
与**评估态** `assessment_status`。

### 5.2 封顶表（T-5.2，规范）

| 证据情形 | 允许的最高 `epistemic_status` |
|---|---|
| 无边，或仅 `insufficient` | `not-assessed` |
| 仅 `mentions`/`contextualizes`（哪怕锚定良好） | `not-assessed` |
| ≥1 `supports`，锚定(cq≥2)、`unassessed`、且 `extraction_method ∈ {direct-quotation, manual-paraphrase, calculation}` | `provisional` |
| ≥1 `supports` 且 `reviewed-supports`（锚定） | `well-supported` |
| ≥2 个**独立源**均为 `reviewed-supports` | `established` |
| 存在锚定的 `qualifies` | 封顶再压到 `provisional`（窄化解读） |
| 存在锚定的 `refutes` 且未被判 `insufficient` | **`contested`**（阶梯外） |

**MUST-5.1** 未经独立评估的证据**不能**把命题推到 `well-supported` 以上。理由：`unassessed`
意味着"有人抓到了这段话，还没人裁定它是否真的蕴涵该命题"；把它当强支撑就是把"出现"当"成立"。
这条是 §3.2 的 `mentions` 禁令在等级维度上的延伸。

### 5.3 超标如何处理：只标记，不改写（T-5.3）

**MUST-5.2** 引擎**永不**改写 as-authored 的 `epistemic_status`。计算出的封顶值与被判定超标的
事实分别存 `policy_cap` / `over_grade` / `delta`，并在结果里打 `OVER_GRADE_VS_CONSERVATIVE_CAP` 标记；
变更必须走 review event（§4），且 A3 禁止评审事件直接写 epistemic 轴——真正降级要由**新版本记录**
（`supersedes`）完成。

本试点实测（`docs/ke/m8554-audit.md` §3）：

| claim | 记录值 | 封顶 | 超标 | 理由 |
|---|---|---|---|---|
| `tkc:prov-o:wasattributedto-signature` | `established` | `provisional` | +2 | 两条支撑证据均 `unassessed` |
| `tkc:fair:a1-protocol-conditions` | `well-supported` | `provisional` | +1 | 单条支撑证据 `unassessed` |
| `tkc:fair:requires-open-access` | `contested` | `contested` | — | 锚定反驳侧成立 |
| `tkc:tkrepo:rocrate-export-production` | `not-assessed` | `not-assessed` | — | 仅提及/语境证据 |

**诚实声明**：这两条超标**不是**说试点记录错。`established` 对"逐字直引一条 REC 规范定义句"
在人工阅读下是可辩护的；争议在**政策口径**——v0.1 选择"没有独立评估就不给 established"。
因此处置是**标记 + 提请评审裁定**（D-06），不是自动降级、也不是掩盖。
这正是本规格想暴露的张力：一旦引擎要自动化，作者的个人判断必须显式化、可裁定。

### 5.4 `not-assessed` 的表达（T-5.4）

**MUST-5.3** `not-assessed` 是**显式值**，与"字段缺失"、`null`、"空数组"三者**严格区分**：

| 情形 | 引擎行为 |
|---|---|
| `epistemic_status = "not-assessed"` | 入库，打 `NOT_ASSESSED_EXPLICIT`，并存 `insufficiency` 块：`insufficient_evidence_refs[]`、`non_entailing_relations[]`、`basis`（封顶计算依据串） |
| `epistemic_status` 字段**缺失** | **拒收**（`INVALID_REQUEST`），不做默认填充——缺失是契约违规，不是知识空白 |
| `epistemic_status` 为 `null` | **拒收**（schema 已要求非空 enum） |
| 默认检索是否返回 not-assessed | **返回**（空白也是知识，人要能知道"这题没证据"）；要隐藏必须显式 `include_not_assessed=false` |

本试点唯一一条 `not-assessed`（`tkc:tkrepo:rocrate-export-production`）正是"诱人但不蕴涵"的样板：
`research/global-landscape/STANDARDS_MAPPING.md` 表里把 RO-Crate 1.3 列为 **P0 export profile**，
那是**规划优先级**，不是"已实现并投产"。规格把这条陷阱固化成机器规则：
`mentions` 永不抬高 → 封顶 `not-assessed` → 检索层以 `NOT_ASSESSED_EXPLICIT` 明示，
而不是让它以"低置信"混在结果里、被下游当弱证据。

---

## 6. valid_time 与 recorded_at：双时态

### 6.1 三只时钟（T-6.1）

| 时钟 | 来源字段 | 含义 | 可变性 |
|---|---|---|---|
| **recorded（事务时间）** | claim.`created_at` / evidence.`captured_at` / provenance.`recorded_at` / KO.`completed_at` | 我们**何时**写下这条判断 | 不可变（`supersedes` 出新记录） |
| **valid（领域时间）** | claim.`valid_time.{start,end,description}` / provenance.`valid_time.*` | 这条判断**何时为真** | 可窄化/关闭，不回改历史 |
| **source（源时间）** | evidence.`source.published_at` / `accessed_at` | **源**何时发表/被抓取 | 事实，不是有效性边界 |

**MUST-6.1** 源发表时间**不得**被提升为任何对象的 `valid_time`。本试点存在一处巧合
（claim 的 `valid_time.start=2013-04-30` 与 evidence 的 `published_at=2013-04-30` 同日），
但只要实现"看到 published_at 就填 valid_time"就必然在别处造假——所以规则写成禁止，不写成例外。

### 6.2 有效性分辨率（T-6.2）

| `valid_time_resolution` | 触发条件 | 查询语义 |
|---|---|---|
| `closed-interval` | 有 start 且有 end | 闭区间内为真 |
| `open-start` | 只有 start | start 之后为真，end 未知 |
| `open-end` | 只有 end | 仅历史区间 |
| `prose-only` | 仅 `description` | **有效期为 UNKNOWN**，不得解析散文里的日期 |
| `unrecorded` | 字段缺失 | UNKNOWN |
| `not-applicable` | evidence-record（契约无此字段） | UNKNOWN（D-01） |

**MUST-6.2** 引擎**不得**从 `valid_time.description` 或 `scope.conditions` 散文里猜时间戳。
散文原样保留，查询里显示 `valid_time_resolution=prose-only`；把散文解析成时间戳等于**编造时点**。

### 6.3 两种 as-of 查询必须分开（T-6.3）

**MUST-6.3** 每个请求至多一个时间轴，`as_of.axis ∈ {recorded, valid}`，同时给两个轴 → `409 CONFLICTING_AS_OF_AXES`。

* `axis=recorded`：回答"**那时我们认为什么**"（审计、复现、追责）。
* `axis=valid`：回答"**那时为真的是什么**"（学科使用）。UNKNOWN 有效性的记录**不得**被当作 false 或 true，
  必须单独标注为 unknown-validity。

实测（校验项 B6，m8554 真实数据）：

| 查询 | 结果 |
|---|---|
| `recorded@2026-11-09T23:59:59Z` | 4 条 claim 全命中 |
| `recorded@2026-11-09T00:00:00Z` | 0 条（尚未写入） |
| `valid@2020-01-01` | 1 条命中（`tkc:prov-o:wasattributedto-signature`，2013 起），3 条 unknown-validity |

**MUST-6.4** 两种轴的结果集**不得**被缓存归并成同一份（否则"当时不知道"会被静默升格为"当时就是假的"）。

### 6.4 契约缺陷（D-01）

evidence-record 没有 `valid_time` 字段，因此"这段引文所陈述的内容在何时为真"在引擎里恒为 UNKNOWN。
这不是实现疏漏，是契约缺口；v0.1 的选择是**如实标注 not-applicable 并在损耗登记里挂账**，
而不是给 evidence 造一个 `valid_time`（那等于偷偷扩契约，且没有作者授权的取值可言）。

---

## 7. 向量映射

### 7.1 什么进向量，什么不进（T-7.1）

| 实体 | facet | 进？ | 理由 |
|---|---|---|---|
| claim | `claim.statement` | ✅ | 命题文本 |
| evidence | `evidence.quote` | ✅ | 原文片段（含省略号，`elided` 标记） |
| knowledge-object | `ko.summary` | ✅ | 聚合摘要 |
| provenance / review-event / envelope | — | ❌ | 相似度对结构与流程文本无检索价值，且易把"流程相似"误读为"内容相关" |

**MUST-7.1** 一条 facet 只装**一个字段**。禁止把 claim 与它的证据拼成一段再嵌入——
那会把"命题"和"支撑它的引文"融成一个语义团，检索命中时无法区分"问到了命题"还是"问到了证据"，
也就正好制造了 §3.2 的 `mentions`→`supports` 误判。

### 7.2 facet 记录与过滤（T-7.2）

```
facet_id        = fct:sha256(entity_id|facet)[:12]
entity_id, facet, source_field_path, text_sha256, text_chars
language        = claim.statement→zh, evidence.quote→quote_language, ko.summary→zh
elided          = 文本含 "…"/"[…]"（引文被裁剪，不可当作连续原文）
embedding       = null（v0.1 未选型）
index_status    = declared-not-built
filters         = {entity_kind, review_status, epistemic_status}
```

**MUST-7.2** 向量检索**必须**先过硬过滤再取近邻，且过滤维度至少包含
`review_status`（默认只读 `draft`+`in-review`+`approved`，`rejected`/`deprecated` 需显式打开）、
`epistemic_status`（`superseded` 默认排除）、`entity_kind`。
**MUST-7.3** 结果必须带 `quote_elided`，让客户端知道这不是可整段复用的原文。
**MUST-7.4** 本试点引文 8/8 为英文、命题 4/4 为中文：跨语种检索在 v0.1 **未做验证**，
不得对外声明"支持跨语种语义检索"（§11）。

### 7.3 相似度永不等于支撑（T-7.3）

**MUST-7.5** `similarity_score` 是**检索分**，不得写入任何 `EVIDENCE_OF` 边，也不得参与 §5 的封顶计算。
支撑只能来自人工/独立评审产生的 `assessment_status ∈ {reviewed-supports, ...}`。
**MUST-7.6** 接口不得提供 `similarity_as_support=true` 之类的开关；若客户端请求"按相似度判支撑"，
返回 `422 POLICY_REJECTED`，错误码 `SIMILARITY_IS_NOT_SUPPORT`。
**MUST-7.7** 生成式摘要必须携带所依据的实体 id 与证据 id，且**不**自动成为新的 approved 对象
（与 `architecture/system-architecture.md` §3.4 一致）。

---

## 8. 检索接口草案（四类查询）

机器可读定义：`schemas/ke-query.schema.json`（Draft 2020-12，`$defs` 内 P*/R* 成对）。
公共信封：

```jsonc
"policy_view": {
  "policy_version": "ke-mapping-v0.1",
  "projection_version": "ke-projection-v0.1",
  "review_policy_version": "ke-review-v0.1",
  "records_as_recorded": true,        // as-authored 值从不被改写
  "withheld_fields": [],              // 本次投影刻意未返回的字段（诚实披露）
  "degraded": false                   // 向量索引不可用时 true，结果退化为词法
}
```

`policy_view` 出现在**每个**响应里（schema `required`）：任何响应都必须自证"我是哪套投影产出的、
隐瞒了什么、是否降级"。

### 8.1 按域：`POST /v1/knowledge/query/by-domain`

```jsonc
{ "query_class": "by-domain", "domain": "research data stewardship principles",
  "domain_match": "exact|prefix", "entity_kinds": ["claim","knowledge-object"],
  "epistemic_status": ["contested","not-assessed"], "review_status": ["draft"],
  "as_of": {"axis": "recorded", "instant": "2026-11-09T23:59:59Z"},
  "include_not_assessed": true, "limit": 50, "cursor": null }
```

响应 `items[]` 每项含 `entity_id/kind/label/domains/epistemic_status/review_status/recorded_at/
valid_time_resolution/evidence_count/flags`，`next_cursor` 为不透明游标，排序确定性为
`recorded_at desc, entity_id asc`。

### 8.2 按锚点：`POST /v1/knowledge/query/by-anchor`

```jsonc
{ "query_class": "by-anchor", "entity_id": "tkc:fair:requires-open-access",
  "expand": {"claims": true, "evidence": true, "provenance": true,
             "review_events": false, "sources": false}, "depth": 1 }
```

响应：`nodes[]` + `edges[]` + `epistemic_view{ claim_id → {supports, refutes, qualifies,
contextualizes, mentions, derived_from, insufficient} }`（**7 键必备，空也要有**）+ `policy_view`。
锚点为 claim 时 `expand.provenance` 带出 `USED` 边指向的 activity 与其 provenance 记录。
**无 `only_support` 参数**（MUST-3.3）。

### 8.3 按证据状态：`POST /v1/knowledge/query/by-evidence-status`

```jsonc
{ "query_class": "by-evidence-status",
  "assessment_status": ["insufficient","unassessed"],
  "relation": ["supports","refutes","qualifies"],
  "require_contested_pair": true }
```

响应：`items[]`（`claim_id` + `matched_evidence[]` + `evidence_partition` + `flags` + `two_sided`）；
`require_contested_pair=true` 时附 `contested_pairs[]`：
`{question_ref, contested_claim, against[], surviving_narrowed_sides[], both_sides_retained}`（MUST-3.2）。

### 8.4 按溯源链：`POST /v1/knowledge/query/by-provenance-chain`

```jsonc
{ "query_class": "by-provenance-chain",
  "entity_id": "tkc:prov-o:wasattributedto-signature",
  "direction": "upstream|downstream|both", "max_depth": 3,
  "include_agents": true, "include_activities": true,
  "require_software_versions": false,
  "as_of": {"axis": "recorded", "instant": "2026-11-09T23:59:59Z"} }
```

响应：`steps[]`（`edge_id/subject/predicate/object/depth/from/to`）+ **`gaps[]`**（未解析外链、
`version_unknown` 工具版本——链**不得**被静默截断）+ `policy_view`。
`require_software_versions=true` 时，缺版本的链以 `partial=true` 返回并在 `gaps[]` 说明。

### 8.5 错误模型（T-8.5）

| HTTP | `error.code` | 触发 |
|---|---|---|
| 400 | `INVALID_REQUEST` | schema 不符、字段缺失（含记录缺 `epistemic_status` 的入库请求） |
| 404 | `ANCHOR_NOT_FOUND` | 锚点 id 不存在 |
| 409 | `CONFLICTING_AS_OF_AXES` | 同时给 recorded 与 valid |
| 422 | `POLICY_REJECTED` / `SIMILARITY_IS_NOT_SUPPORT` | 请求违反 §5/§7.3 政策（如"按相似度判支撑"） |

**MUST-8.1** 错误响应**不得**回退成"返回部分结果 + 200"。

### 8.6 已实测的演示（真实记录，非构造样例）

`mappings/m8554.json` 的 `retrieval_demonstrations` 里 7 条请求-响应用**真实映射数据**跑出，
并由校验项 C1 逐条过 `schemas/ke-query.schema.json`：by-domain（域命中 2 条 FAIR claim）、
by-anchor（contested 命题带出 refutes/qualifies/contextualizes 三侧）、
by-evidence-status（insufficient → not-assessed 命题，7 个分片全空仍齐全）、
by-evidence-status(two-sided)（`contested_pairs[]`，`both_sides_retained=true`）、
by-anchor(KO)（聚合体同时给出 contested 与 narrowed 两条 claim）、
by-provenance-chain（claim → activity → agent，`gaps[]` 指向空版本）、以及 404 错误样例。---

## 9. Worked example：m8554 全量映射

### 9.1 做法

1. `mappings/source/m8554/`：从 `agent/m8554` @ `727ac18` 取 15 条契约记录 + 1 份 production-result，
   冻结为只读快照（scenario 包与试点验证脚本不进引擎，故不入快照）。
2. `scripts/build_ke_mapping.py` 逐记录展平叶子路径 → 命中 `RULES` → 生成投影 / 边 / facet / 损耗 /
   检索演示；**所有数字由代码计算**（零手抄）。
3. `scripts/validate_ke_mapping.py` 跑 18 项门槛；`scripts/render_ke_audit.py` 生成
   `docs/ke/m8554-audit.md`（逐记录表、阶梯表、损耗登记、校验结果、检索演示）。

### 9.2 结果（实测，见 `runs/ke_mapping_validation.json`）

| 指标 | 值 |
|---|---|
| 记录数 | 19（4 claim + 8 evidence + 3 provenance + 3 KO + 1 envelope，**超出**任务要求的 4+8+3） |
| 叶子路径 | 509，**投影 509，未覆盖 0** |
| 语义损耗登记 | 11 条（L4 10 条 + L1 表示注记 1 条） |
| 边 | 55 |
| 向量 facet | 15（claim 4 + evidence 8 + KO 3），全部 `declared-not-built` |
| review event | 0 条（与试点一致：全 `draft`，无自批） |
| claim↔evidence 引用对称 | 4/4 |
| provenance 覆盖 | 12/12 契约记录可达 `activity.used_entities`（粒度=scenario 级） |
| 门槛校验 | 18/18 PASS |

判据"**试点包全记录映射无损耗，或有显式损耗披露清单**"的达成方式是**两者同时**：
叶子级 0 损耗（机器可复算，A2/A3/A4 三项）＋ 语义级 11 条显式披露（每条带实测证据与处置）。

### 9.3 损耗登记（全文见 `docs/ke/m8554-audit.md` §5）

| id | 级 | 严重度 | 要点 |
|---|---|---|---|
| D-01 | L4 | major | evidence 契约无 `valid_time`：引文"何时为真"恒 UNKNOWN |
| D-02 | L4 | major | 3/8 引文含省略号、0/8 有 `start_offset`：引文不可当作可复验的连续片段 |
| D-03 | L4 | major | 生产者身份碎裂为 3 个写法（同一会话 token），字符串相等判不自批会被绕过 |
| D-04 | L4 | minor | 9/9 工具版本为空：工具链版本无法钉死 |
| D-05 | L4 | major | provenance 粒度=scenario 级；8/8 evidence 缺 `assessment` 块 |
| D-06 | L4 | major | 2 条 claim 的 `epistemic_status` 超过保守封顶（`established`→`provisional`、`well-supported`→`provisional`），标记不改写 |
| D-07 | L4 | minor | 3/4 claim 的有效期只有散文（`prose-only`），不得解析成时间戳 |
| D-08 | L4 | minor | KO 用开放词表 `relations[]` 而非 schema 的 `claim_refs`（3/3 vs 0/3） |
| D-09 | L4 | info | 0 条 review event；`draft` 来自空账本 fold，契约本身无 `review_status` 字段 |
| D-10 | L4 | info | `not-assessed` 是显式值：仅 `mentions`/`insufficient` 证据，不能混作弱支撑 |
| D-11 | L1 | info | `source.published_at` 是日期非时刻，归一化到 00:00Z 属表示约定 |

### 9.4 逐条映射示例（`tkc:fair:requires-open-access`，17 个叶子 → 17 行投影，0 未覆盖）

| 源字段 | 引擎落点 | 类 |
|---|---|---|
| `id` | `entity.entity_id` | L0 |
| `statement` | `claim.statement` + facet | L0 |
| `claim_type` | `claim.claim_type` | L0 |
| `scope.domain` | `claim.scope.domain` | L0 |
| `scope.conditions[0]` | `claim.scope.conditions[]` | L0 |
| `modality` | `claim.modality` | L0 |
| `epistemic_status` | `status.epistemic_status` + `policy_cap` | L0 |
| `evidence_refs[0..2]` | 3 条 `EVIDENCE_OF` 边 | L2 |
| `valid_time.description` | `bitemporal.valid_time.description` | L0 |
| `created_at` | `bitemporal.recorded_at` | L1 |
| `created_by` | `recorded.created_by.raw` + `identity_key` | L0 |
| `version` | `entity.version` | L0 |
| `notes[0..2]` | `claim.notes[]` | L0 |

（其余 18 条记录的同类逐行清单由 `mappings/m8554.json` → `records[].projection` 给出，
`docs/ke/m8554-audit.md` §2 给出逐记录汇总。）

---

## 10. 验证与门槛

```bash
python -m pip install -r requirements-validation.txt
python scripts/ke_state_machine.py          # 9/9 状态机一致性用例
python scripts/build_ke_mapping.py          # 重新推导；未覆盖叶子将导致非零退出
python scripts/validate_ke_mapping.py       # 18 项门槛，写 runs/ke_mapping_validation.json
python scripts/render_ke_audit.py --check    # 审计文档与数据同步
python scripts/validate_epistemic_benchmark.py   # 既有门槛，未回归
python scripts/validate_knowledge_assets.py      # 既有门槛，未回归
```

| 组 | 检查 | 判据 |
|---|---|---|
| A1 | 映射文档过 `schemas/ke-mapping.schema.json` | 结构 |
| A2 | 每记录 `raw_sha256` 与冻结快照一致 | 源不被偷改 |
| A3 | 规则表**重新推导**结果与提交映射逐路径一致 | 映射不陈旧 |
| A4 | 无叶子路径被静默丢弃 | 无损 |
| A5/A6 | 每条超标标记都有 D-06 条目；披露 id 连续 | 披露不漏 |
| B1 | 三种真实生产者写法各自 approve 均被拒 | 不自批 |
| B2 | 状态机 9 例全过 | 转移表 |
| B3 | 平台态不参与 `review_status` | 三轴分离 |
| B4 | 记录值不被改写、封顶与差值齐备 | 保守性 |
| B5 | 缺 `epistemic_status` 的记录被拒收 | not-assessed 表达 |
| B6 | recorded 轴与 valid 轴结果不同且不编造 | 双时态 |
| B7 | evidence 无 validity，published_at 未升格 | 时钟分离 |
| B8 | contested 两边齐备且接口无单边参数 | 两边保留 |
| B9 | facet 种类与计数受限，相似度不写成支撑 | 向量政策 |
| B10 | 每记录 `raw` 可取 | 权威保留 |
| C1 | 7 条演示响应过 `schemas/ke-query.schema.json` | 接口草案可机器校验 |
| D1 | 投影数 + 未覆盖数 = 叶子总数 | 账目平衡 |

CI：`.github/workflows/validate-ke-mapping.yml` 在 push/PR 时重算映射、比对提交版本（拒绝陈旧映射）、
跑状态机与 18 项校验，并检查审计文档是否过期。**"规格不漂移"是机制，不是承诺。**

---

## 11. 局限与未完成（honest）

1. **没有服务，只有参考实现。** 四类查询由进程内 `Projection` 类对真实映射数据执行，
   HTTP 语义（鉴权、分页、限流、并发、幂等）**未实现也未经压力验证**；`schemas/ke-query.schema.json`
   是草案，未经客户端联调。
2. **没有向量索引，也没有嵌入模型。** 15 条 facet 全部 `declared-not-built`、`embedding=null`。
   本文对向量层的规定是**政策**（能/不能做什么），不是**实测性能**（召回率、延迟、维度均未测）。
3. **跨语种未验证**：命题 zh、引文 en；不做同语种假设，但也没有证明跨语种检索可用。
4. **无 NLI/蕴涵自动化**：`assessment_status` 只能由人/独立评审产生；v0.1 不做自动裁定，
   因此"来源是否真的蕴涵命题"仍需人工复核。
5. **身份注册表是临时的**：`ke.identity` 的别名闭包由会话 token 推导，能挡住本试点的别名绕过，
   但对"同一模型换会话 id""同一人换账号"无能为力；多智能体并发审批前必须先有持久身份注册表（D-03）。
6. **一个试点，19 条记录**：m8554 是三场景小样本，"0 未覆盖"只证明**规则表覆盖了这 19 条**，
   不证明新契约版本或新字段自动被覆盖——新字段会以未覆盖形式让构建器失败（这是有意的），
   但需要有人补规则并升 `projection_version`。
7. **两处政策口径未定**（提请评审裁定）：
   (a) D-06 的超标处置（是调政策还是降记录）；
   (b) `unassessed` 锚定证据的封顶是否一律 `provisional`——本试点 2/4 claim 因此被标记。
8. **契约缺口未闭合**：evidence 无 `valid_time`（D-01）、引文无字符偏移（D-02）、
   KO 的 `claim_refs` 未被使用（D-08）。这些需要契约变更，不在本任务权限内。
9. **未测规模**：单机 19 记录；10^5 量级的查询计划、索引维护、`contested_pairs()` 的复杂度
   （当前 O(KO×边)）均未评估。

---

## 12. 变更与政策版本

| 版本 | 日期 | 变更 |
|---|---|---|
| ke-mapping-v0.1 / ke-projection-v0.1 / ke-review-v0.1 / spec 0.1 | 2026-11-09 | 首版：四契约→实体/边/facet 映射、状态机（不自批 + 别名闭包 fail-closed）、保守封顶表、双时态、四类检索接口、m8554 全量 worked example + 11 条损耗登记 |

**版本规则**：改规则表必须同时升 `projection_version` 并重算 `mappings/*.json`（CI 会拦陈旧映射）；
改状态机或封顶表必须升 `ke-review-v0.1` / 本文档版本，并在 `review-event.policy_version` 上体现——
历史事件按当时政策解释，不追认。---

## 13. 自我对抗评审（adversarial review of this specification）

本节由作者对上面的规格做独立挑战，明确列出**最强反驳**、证据、以及哪些检查**没有做**。
独立性限制见 §13.5。

### 13.1 最强反驳（按严重度排序）

| # | 反驳 | 严重度 | 证据 / 该反驳能走多远 | 处置 |
|---|---|---|---|---|
| R1 | **"0 未覆盖"可能是规则表太宽松造出来的**：只要给某类路径写一条 L3（仅存 raw）规则，叶子就"覆盖"了，无损耗成了自证。 | **blocking（针对判据有效性）** | 属实且是本规格最脆弱的地方。缓解：L3 规则必须逐条写"理由"，且规格 §1 T-2.2 把 L3 限定在两类（自由散文、去规范化副本）；实测 L3 只落在这两类（KO `sources[]`/`content`、envelope `summary`/`limitations`/`confidence_statement`/`agent_attribution`/`evidence_and_sources`）。**但**这只由作者判断背，没有第三方核对"哪些路径该是 L3"。 | 保留判据，但把结论口径收紧为"**在声明的 L3 政策下**叶子零遗漏"；L3 清单已逐条可见（`mappings/m8554.json` → `records[].projection[].loss_class=L3`），谁不同意可直接挑战清单，不必信任结论。 |
| R2 | **L2（展开为图）可能名不副实**：写着"边承载同一信息"，实际可能只建了边没建全属性。 | major | 边属性逐条可见：`EVIDENCE_OF` 带 `relation/assessment_status/extraction_method/capture_quality`，`KO_*` 带 `relation_type_raw/intent`，`ARTIFACT_REF` 带 `is_directory_hint`。反例风险：`CLAIM_RELATED`、`SUPERSEDES` 在本试点 0 条实例，**该路径未被真实数据检验**（见 §13.4）。 | 承认；给"未被实例化的谓词"单列限制。 |
| R3 | **保守封顶表（T-5.2）是作者拍的，不是学界共识**。 | major | 属实。它是**政策**而非事实，且直接导致 2/4 claim 被标超标。反证：对"逐字直引一条 REC 规范定义句"这种证据，要求"独立评估"才能给 `established` 有过度形式主义之嫌。 | 规格把它写成 `ke-mapping-v0.1` 政策 + 标记而非改写 + D-06 提请裁定；政策可换版本，历史事件按当时政策解释（§12）。**不**声称该表是唯一正确口径。 |
| R4 | **19 条记录的样本无统计意义**，泛化到全仓/新契约不可推。 | major | 属实。规格未做规模测试（§11.9）。 | 结论只限定"这 19 条 + 当前契约版本"；新字段会让构建器失败（有意设计），不假装自动适应。 |
| R5 | **不自批只挡了"同一 token"这一种绕过**。同模型换会话、同一人换账号、人被冒充为 agent、committee 类型被冒用（SR-2 豁免 token 比较）都能过。 | major | 属实。SR-2 对 `organization`/`committee` 直接判独立，这是**故意留的信任锚**，但意味着"自称 committee"可绕过。 | 明确写出：SR-2 依赖上游身份可信（`reviewer.id` 不可自证）；持久身份注册表 + 签名审查在 v0.2 范围。当前实现**不是**多租户安全边界。 |
| R6 | **`contested` 判据把 `unassessed` 反驳侧也算数**，可能造成"随便贴一条反向引文就 contested"的滥用。 | minor | 属实，方向是保守的（压低而非抬高置信）。滥用代价：把命题人为降格。 | 保留（fail-safe 方向正确），但记录：`contested` 不是"有争议已成立"，只是"存在未裁定的锚定反向证据"，检索层必须同时给 `against[]` 供人判断。 |
| R7 | **接口草案未跑过并发/分页/鉴权**，"接口设计"可能一落地就变形。 | major | 属实（§11.1）。7 条演示是进程内调用，不是 HTTP。 | 明确标注"草案 + 参考实现"；`policy_view`、排序确定性、错误码是不可回退的最小契约面。 |
| R8 | **审计文档由脚本生成，脚本与映射同源**，若构建器 bug 系统性漏算，校验也跟着漏。 | major | 属实（同源风险）。缓解：A3 **独立重算**一遍投影再比对（仍同库，但至少抓陈旧/手工改动）；A2 用快照 SHA-256 独立于规则表。 | 承认这是**同源校验的固有上限**；真正的独立验证需要第二套实现（未做，见 §13.4）。 |

### 13.2 已被证据否掉的反驳（诚实记录）

| 反驳 | 为何不成立 |
|---|---|
| "claim↔evidence 引用不对称会导致边丢失" | 实测 4/4 对称（`cross_checks.evidence_ref_symmetry`），本试点无此风险 |
| "`not-assessed` 会被检索漏掉" | 实测 by-evidence-status 与 by-domain 均返回该 claim 并带 `NOT_ASSESSED_EXPLICIT`；隐藏需显式 `include_not_assessed=false` |
| "平台 completed 会被当 approved" | 实测空账本 → `draft`；B3 每次比对平台态/KO 态/账本三者 |

### 13.3 被夸大风险最高的三句表述（自查）

1. "**无损耗**" —— 只在叶子字段层面成立，且在声明的 L3 政策下；语义层面有 11 条挂账。文中已同时写明，禁止单独引用前半句。
2. "**不自批已实现**" —— 指"状态机拒绝 + 三种真实身份写法被拒"，不指"不可绕过"（R5）。
3. "**接口草案已验证**" —— 指"响应结构过 schema + 用真实数据跑通语义"，不指"服务可用/性能达标"（R7）。

### 13.4 本次**没有做**的检查（not_run，不得视为通过）

| 检查 | 状态 |
|---|---|
| 第二套独立实现的交叉验证（避免 R8 同源风险） | **not run** |
| 服务端 HTTP 行为（鉴权、分页、限流、幂等、并发） | **not run**（服务未实现） |
| 向量索引召回/延迟/维度、跨语种检索质量 | **not run**（无嵌入模型） |
| `CLAIM_RELATED` / `SUPERSEDES` / `HAS_REVIEW_EVENT` 谓词的真实实例验证 | **not run**（本试点 0 实例） |
| 真实 review event 的端到端流转（目前只有合成演示 + 一致性用例） | **not run**（试点 0 条事件） |
| 10^5 量级导入与查询性能、`contested_pairs()` 复杂度 | **not run** |
| 与 TensorPlatform 的实测联调（本任务不涉及执行面） | **not run** |
| 契约变更提案（D-01/D-02/D-08 的修复方案） | **not run**（越权） |

### 13.5 独立性限制与处置

作者同时是：试点作者团队同一会话生态的智能体、规格作者、映射构建器作者、校验器作者。**不存在独立评审**；
本文的"对抗"是自查，不能替代 §4 要求的独立 review event。据此：

**处置：approve with notes（请求评审裁定）**

1. 规格可作为 Engine v0.2 实现的输入（R1/R2 的 L2/L3 清单可直接被挑战）；
2. **不建议**在任何对外材料中声称"无损耗"或"不自批不可绕过"，除非 §13.4 的未做项补齐；
3. 请评审优先裁定：D-06 政策口径（R3）、SR-2 信任锚（R5）、L3 清单是否接受（R1）。

---

## 14. 设计取舍记录（为什么不是别的做法）

| 决策点 | 采纳 | 被否方案 | 否掉的理由 |
|---|---|---|---|
| 记录落地形态 | raw 权威 + 派生投影 | 只存结构化字段（不留 raw） | 无法证明"无损耗"，且契约升级会丢历史信息 |
| 关系存放位置 | 边 | 实体属性 | 一条证据支撑多命题，属性会互相覆盖；两边保留也无处安放 |
| review 状态 | 账本 fold | 可写列 `review_status` | 可写列无法审计"谁在何时改的"，也无法阻止自批（改了就是改了） |
| 不自批判据 | 会话 token 别名闭包 + fail-closed | 字符串相等 | 本试点三种真实写法即可绕过（D-03） |
| 超标处理 | 标记不改写 | 引擎自动降级 | 等于让机器改作者断言，且降级动作本身无法追溯；正确路径是新版本记录 + 评审 |
| contested 载体 | KO 聚合 + 窄化边 | 单条 claim 的 supports/refutes 计数 | 本试点宽命题自身无 supports 边，"两边"分属两条 claim |
| 无 validity 的 evidence | 标 `not-applicable` | 用 `published_at` 兜底 | 会把"源何时发表"伪造成"命题何时为真"（§6.1） |
| 散文有效期 | 存原文 + 标 prose-only | 解析成时间区间 | 解析=编造时点（§6.2） |
| 向量 | 只 3 类 facet、一字段一 facet | 命题+证据合并嵌入 | 会把"提及"混成"支撑"（§7.1） |
| 判据 | 叶子级 0 遗漏 + 语义级披露双轨 | 只报"全部映射完成" | 单一指标可被 R1 那类规则宽松度自证 |

**预先声明的门槛（动手前即定，事后未调）**：叶子未覆盖 = 0；18 项校验全过；状态机 9/9；
不自批 3/3 拒绝；披露条目必须与实测计数一致（A5 强制）。上述门槛在 `scripts/validate_ke_mapping.py`
里是硬断言，未因结果不好看而下调。