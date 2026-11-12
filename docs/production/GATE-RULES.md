# 三道门校验规则清单（GATE-RULES v1）

对应规范：`docs/production/PRODUCTION-LINE-v1.md`｜实现：`ke/wp_gate.py`｜
CLI：`scripts/validate_work_package.py`｜测试：`tests/test_wp_gate.py`（40 项）

**可执行优先**：下表每条规则都有一个稳定 id、一段代码判定、一个夹具或测试证明它能红。
凡是无法程序化的（语义保真、验证单签发）明确标 `not_run` / 外部依赖，**不伪装成通过**。

图例：`FAILS` = 哪个夹具包让它红；`NOTES` = 边界与已知局限。

---

## G1 结构门（程序化，`_gate_structural`）

| id | 检查名 | 判据 | 失败即 | FAILS |
|---|---|---|---|---|
| S1 | `files_present` | `work-package.json` + 契约 `output` 声明的四文件存在 | 包不完整 | 任意删文件 |
| S2 | `valid_json` | 每个文件可 `json.loads` | 语法错 | 手工破坏 |
| S3 | `contract_schema` | 契约过 `work-package-contract.schema.json`（含 03/04/05 分支、恒真约束、附件 manifest、03 锁 draft） | 契约不合规 | `test_process_03_*`、`test_constraints_cannot_be_turned_off`、`test_attachments_require_a_manifest` |
| S4 | `record_schema` | claims/evidence/provenance 逐条过各自 schema（复用 `schemas/claim-record|evidence-record|provenance-record`） | 记录结构错 | `bad-verified`（多余 `verification_status` 字段） |
| S5 | `summary_schema` | `extraction_summary.json` 过 `extraction-summary.schema.json`，且空集/非空集与 `empty_result` 自洽 | 覆盖度自述不可信 | 0 claims 但 `is_empty:false` |
| S6 | `unique_ids` | claim/evidence/provenance **跨类型**无重复 id，无空 id | id 冲突 | 复制一条 claim |
| S7 | `output_declaration` | 磁盘上的知识文件集合 == 契约 `output` 声明（多/少都不行） | 悄悄夹带或漏交 | 加 `summary.md` |
| S8 | `producer_draft_only` | 每条 claim `epistemic_status == "draft"` | 生产者自定档 | `bad-verified` |
| S9 | `no_self_verification` | 任何产物记录里出现 `verified/verification_status/verification_level/is_verified/gate_confirmed` 字段即失败 | 自封验证 | `bad-verified` |
| S10 | `xref_closure` | `claim.evidence_refs ↔ evidence.claim_refs` 双向闭合，无孤儿 evidence，无悬空引用 | 引用账不闭合 | `bad-no-evidence` 的变体会同时触发 |
| S11 | `claim_evidence_or_unresolved` | 每条 claim 有 evidence_refs，**或**在 `unresolved.json` 里 `status:"unresolved"` | 裸断言或静默丢弃 | `bad-no-evidence` |
| S12 | `zero_claim_legality` | 0 claim ⇒ `empty_result.is_empty=true` 且 `reason≥20` 字符；>0 claim ⇒ `is_empty=false` | 编造知识或空集不解释 | `ok-zero-claim`（绿）/ 删 reason（红） |
| S13 | `counts_consistent` | summary 的 counts 与文件真实条数一致（claims/evidence/provenance） | 自述掺水 | 改 summary 计数 |
| S14 | `source_identity` | 契约 `input.report_id/source_hash` == summary `source.*`，且 evidence `source.persistent_id` 若无则为该 report_id | 张冠李戴（拿了别的报告的证据） | 改 summary report_id |
| S15 | `no_self_supplied_review_material` | 03 工序包内**不得**出现 `review_events.json`/`verification_ticket.json`/`review_report.json`（否则生产者可自批自证）；04 工序包必须带 `review_events.json` | 自批自证 | `bad-self-review` |

---

## G2 证据门（程序化，`_gate_evidence` / `_gate_evidence_coverage`）

| id | 检查名 | 判据 | FAILS |
|---|---|---|---|
| E1 | `source_reachable` | resolver 能取到 `input.report_id` 的原文（离线目录或平台 API）；取不到 = FAIL（**不 skip**） | `test_unreachable_source_fails_closed` |
| E2 | `source_hash_matches` | 重算 `sha256(source_field 文本)` == 契约 `source_hash`（字节精确，不做换行归一） | `bad-source-hash`（唯一失败项） |
| E3 | `locator_resolvable` | 每个 locator 能在原文定位：声明了偏移 ⇒ 偏移在界内；未声明 ⇒ quote 逐字可搜到 | `bad-quote-offset` |
| E4 | `quote_matches_source` | 声明偏移时 `text[start:end] == quote` **字节相等** | `bad-quote-offset`（`QUOTE_NOT_AT_LOCATOR`） |
| E5 | `quote_hash_consistent` | 若给了 `locator.content_hash`，必须等于 `sha256(quote)` | 篡改 quote 不改哈希 |
| E6 | `quote_not_trivial` | quote 长度 ≥ `--min-quote-chars`（默认 12） | 用 "the" 之类当证据 |
| E7 | `evidence_covers_claims` | 每条 claim 至少一条 evidence 通过 E3+E6 | claim 挂在不可解析证据上 |

定位码（`locator_matches` 返回值）：`OK_OFFSETS` / `OK_SEARCH` / `LOCATOR_EMPTY` /
`LOCATOR_BAD_OFFSETS` / `LOCATOR_OUT_OF_RANGE` / `QUOTE_NOT_AT_LOCATOR` /
`QUOTE_NOT_FOUND` / `VALUE_NOT_AT_LOCATOR` / `VALUE_NOT_FOUND` / `NO_SOURCE`。

---

## G3 语义门（**不可程序化**；本节全部是"准备与边界"，不是"通过"）

| id | 检查名 | 性质 | 说明 |
|---|---|---|---|
| M1 | `review_required_declared` | 程序化 | 契约 `review.required` 与 `independent_reviewer` 均 `true` |
| M2 | `review_ledger_legal` | 程序化（复用状态机） | `review_events.json` 按 `scripts/ke_state_machine.py` 折叠：非法转移/缺 findings/自审（含别名 token）一律拒绝并给码（如 `SELF_APPROVAL_BLOCKED`） |
| M3 | `reviewer_independent` | 程序化 | 批准者身份 ≠ 任何生产者身份（fail-closed） |
| M4 | `prompt_independent` | 程序化（度量） | 生产 prompt vs 审核 prompt 字符 5-gram Jaccard < 0.5；实测 shipped 对 0.126；复制生产 prompt ⇒ 红 |
| M5 | `reviewer_context_no_producer_explanation` | 程序化（上下文隔离） | 审核包 `context` 只允许 `source/claims/evidence/provenance`；递归扫禁字段（`extraction_summary`/`self_assessment`/`producer_rationale`/`notes`…） |
| **M6** | **`semantic_fidelity`** | **`not_run`（天然不可程序化）** | "claim 是否真表达原文/有无过度推断"由独立审核 Agent（+抽样强模型）判定。门禁只输出 `semantic.pass = null`、`status = pending-independent-review`；代码**永不**给 G3 通过 |

审核抽样：`review.sample_rate`（默认 1.0）与 `strong_model_sample_rate` 记在契约里，
审核包 `sample.claims_to_open` 按比例算出；"抽样强模型"的执行与结果回收属平台调度（本单未实现）。

---

## V 验证阶梯（`verification_level`，三状态分离律的机器实现）

| id | 规则 | 说明 |
|---|---|---|
| V1 | 门禁计算，生产者不得写 | S9 已禁生产者字段；级别只来自门禁 |
| V2 | L0→L1 需 G1 全过 | 失败即 `STRUCTURAL_GATE_FAILED` |
| V3 | L1→L2 需 G2 全过**且 ≥1 claim** | 空包封顶 L1（`EMPTY_PACKAGE_NO_CLAIM_TO_VERIFY`）；G2 红则 `EVIDENCE_GATE_FAILED` |
| V4 | L2→L3 需审核轴 `approved` | 否则 `REVIEW_NOT_APPROVED`；缺单 `MISSING_PLATFORM_VERIFICATION_TICKET` |
| V5 | L3 需**平台验证单**：`issued_by` 非空、`gate=confirmed`、`package_id` 与 `claims_sha256` 双匹配 | 不匹配分别给 `TICKET_UNSIGNED` / `TICKET_NOT_CONFIRMED` / `TICKET_PACKAGE_MISMATCH` / `TICKET_CLAIMS_DIGEST_MISMATCH`；验证单只能从**调用方指定目录**读（`--tickets-dir`），包内自带一律 S15 失败；签发与防伪**不在本仓**（外部依赖，标 `not_run`） |
| V6 | 任务轴不参与 | 门禁从不读 mission 状态；`axes.mission_state` 记录"未消费"；测试 `test_mission_state_is_not_consumed_by_the_gate` |

---

## K 技能库生命周期（`validate_skill_registry`）

| id | 检查名 | 判据 |
|---|---|---|
| K1 | `valid_json` | `extraction-skills/registry.json` 可解析且含 `skills` 数组 |
| K2 | `skill_schema` | 每条过 `extraction-skill.schema.json` |
| K3 | `unique_skill_ids` | `skill_id` 唯一（同型重复=缺陷） |
| K4 | `lifecycle_preconditions` | `sample-tested` 及以上需 ≥1 `outcome:"pass"` 样本；`independent-review` 及以上需 `review`；`registered` 需 `reuse_count` |
| K5 | `review_auditable` | `registered` 需 `review_event_id`；`reviewer_id` ≠ `created_by`（自审阻断） |
| K6 | `six_type_coverage` | 六类报告分型各有 ≥1 非 `deprecated` skill |

---

## 夹具矩阵（每个包只触发它要证明的那一类失败）

| 夹具包 | 设计 verdict | 失败规则 | 验证级别 | 证明 |
|---|---|---|---|---|
| `ok-basic` | `PASS_PROGRAMMATIC_PENDING_REVIEW` | — | **L2**（缺验证单） | 双门全绿、审核轴 approved、语义仍 pending |
| `ok-verified` | 同上 | — | **L3** | 验证单 confirmed + claims 摘要匹配才到 L3 |
| `ok-zero-claim` | 同上 | — | **L1**（空包） | 零 claim 合法且不冒充"证据绑定" |
| `bad-no-evidence` | `FAIL_STRUCTURAL` | S11 | L0 | 裸断言被挡 |
| `bad-source-hash` | `FAIL_EVIDENCE` | **仅** E2 | L1 | 哈希门独立可红，结构面不受牵连 |
| `bad-quote-offset` | `FAIL_EVIDENCE` | E3/E4/E7 | L1 | 引文存在但不在声明偏移 = 造假等价物 |
| `bad-verified` | `FAIL_STRUCTURAL` | S4/S8/S9 | L0 | 生产者自封验证被挡 |
| `bad-self-review` | `FAIL_STRUCTURAL` | S15 | L0 | 包内自带审核台账/验证单被挡（对抗性自审发现的漏洞） |

复现：`python -m pytest tests/test_wp_gate.py -q`（40 passed）。
审核台账与验证单放在夹具的 `ledgers/`、`tickets/` 目录（包外），由测试/CLI 显式传入。

---

## 已知局限（不掩盖）

1. **M6 无法自动化**：任何"语义门通过"的说法若不由独立审核 Agent 产生，即为越权。
2. **E2 的 `source_field` 语义**：`record` 字段用 canonical JSON（`sort_keys`）计算；若平台
   改序列化方式，历史哈希会失配——需要用 `source_field` 记录并重算，不能静默放宽。
3. **字符偏移 vs 码点**：当前偏移是 Python 字符串下标（码点）。含 emoji/代理对的正文需
   前后端统一口径，否则 E4 会误判（中文 BMP 字符无此问题）。
4. **中文标点/全角空格**：E4 是字节级相等，不做标点归一——这是设计选择（防"顺手改标点"
   改语义），代价是生产者必须逐字复制。
5. **附件内容未验**：`attachments_manifest` 只校验清单与哈希声明，未实现附件（图/表）内容抽取。|
6. **吞吐未测**：未见万份规模的并发/源拉取压测。
7. **验证单无签名**：`issued_by` 只是自报字段，防伪依赖平台签发与目录权限；本仓只能做到
   "不从生产者目录读 + 必填 + 摘要匹配"。