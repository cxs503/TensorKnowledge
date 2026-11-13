# Knowledge Compiler 规范 v1（S1–S7）

> 锚点 **KBM-TKC-COMPILER-ALIGN** | 版本 1.0.0 | 2026-11-12 | 仓：TensorKnowledge（契约与治理权威面）
> 上游不另立：四契约 = `schemas/claim-record|evidence-record|provenance-record`；
> KO = `schemas/knowledge-object-v1.schema.json`（`docs/rci/schema-v1.md`，勿另立）；
> 工序 = Knowledge Factory `tk_work_packages` 01–05（执行面在 TensorPlatform）。

## 1. 分工与不改的东西

| 面 | 归属 | 本规范的态度 |
|---|---|---|
| 工序调度/派工/工作包 | TensorPlatform `ops/knowledge_factory` | **不改**，本规范只给 03/04 的机器契约 |
| 四契约 / KO v1 / 门判据 | TensorKnowledge（本仓） | 复用，不新增 schema 家族 |
| 知识对象存储 | `schemas/sql/knowledge_object_v1.sql`（`ko_object`/`ko_evidence`/`ko_relation`） | 复用 DDL，编译产物按此落库 |
| 缺口登记 | `knowledge/oss-lbm/**/gaps/*.json` | 复用；缺口→研究任务的接口见 §6 |

**铁律**：编译面只产出**候选**知识对象。`verification_status` 上限 = `report_claimed`
（有可解析的报告小节证据），L3 只走平台验证单（`ko_verification` + `maturity_gate`）。
编译面永不写 `established`/`verified`，永不判定 claim 真假（那是工序 04 与平台门的活）。

## 2. 七段流水线（每段都有机器可裁产物）

| 段 | 名称 | 做什么 | 产物 | 机器判据 |
|---|---|---|---|---|
| S1 | 输入规范化 | 读报告/论文/代码分析/仿真结果；sha256（UTF-8 字节口径，不规范化换行）；标题切小节 | `source_hash`、`sections[{heading,anchor,span,section_sha256}]` | 偏移与 sha256 可由源文重算命中（`verify_kobject` E-section） |
| S2 | 主题与研究问题识别 | 一级标题=题名；含 `?/？` 或"研究问题/目标/方法/结论"的标题与问句=研究问题；无词典主题词统计 | `topic{title, questions[], terms[], n_sections}` | 每条 question 必须能回指标题原文（`source: heading-rule|question-mark-rule`） |
| S3 | 概念与知识单元拆解 | 小节 × 主题词 × 断言计数 = 知识单元（KU）；不做本体建模 | `units[{unit_id, section, anchor, terms[], n_claims}]` | unit 的 anchor 必须存在于 S1 小节集 |
| S4 | Claim/Evidence 抽取 | 段内切句（段落以空行为界；表格行/代码块/标题行不计）；含数值或判定词的句子成 claim；引文逐字 | `claims[]`、`evidence[]` | E1 引文逐字子串且偏移一致；E2 落在声明小节 span 内；E3 数值在引文内可重算 |
| S5 | 关系与来源 | claim → 来源小节（`derived_from`）；矛盾候选对（`contradicts`）；`storage_level=L2` 当且仅当有关系边 | `relations[]`、KO `relations` | 关系目标必须是可解析引用（`report:<id>#<anchor>` 或同批 `knowledge_id`） |
| S6 | 重复与矛盾识别 | 报告内：精确重复=弃取并登记；`数值掩码模板` 相同但数值集合不同=矛盾候选；批级：同模板跨报告 = 跨报告矛盾候选 | `duplicates[]`、`contradictions[]`、批级 `contradictions_cross` | 矛盾一律 `status=needs-independent-review`，编译面不下结论 |
| S7 | 待评审 KO | claim→KO v1（type 映射见 §4）；证据=filed 小节引用；入库前过 `validate_ko_v1.validate_document` | `kobjects[]`（`report_claimed`，L1/L2） | schema 不过=缺陷（抛错，不静默降级）；0 条 claim 是合法完整结果 |

实现：`ke/compiler.py`（`compile_report()` = S1–S7；`verify_kobject()` = 证据三闸复核）。
CLI：`python -m ke.compiler --report-id <id> --out-dir <dir>`。

## 3. 与 factory 工序 01–05 的对齐

| factory 工序 | 契约状态 | Compiler 对应 | 说明 |
|---|---|---|---|
| 01 资产登记 | active | S1（输入规范化） | 报告正文按 `source_field=markdown` 计哈希；附件走 manifest，编译面不猜 |
| 02 分类解析 | active | S2 + S3（主题/KU） | 分类结果只用于选 facet/domain，不做质量裁定 |
| **03 知识抽取** | **本规范交付**（`contracts/kf/03-knowledge-extraction.contract.json`） | S2–S7（S1 复用 01 的 source_hash） | 输出 `claims/evidence/provenance/extraction_summary.json` 四文件 + KO 文档 |
| **04 独立评审** | 本规范交付（`contracts/kf/04-independent-review.contract.json`） | 无（评审不进编译面） | 评审人只看源文 + KO，不看产出方解释；自批被 `ke_state_machine.is_independent` 拒 |
| 05 综合研究 | 契约已有 | 无 | 只消费已评审 KO；不得跨过 03/04 |

契约文件本身受 `schemas/work-package-contract.schema.json` 约束（`task_type=03` 分支
要求 5 目标 / 4 输出 / 6 验收 / 独立评审 / `delivery.status=draft`）。

## 4. claim → KO 类型映射（并入 KBM-SCHEMA-W1 词表，不另立）

| 编译判定（规则） | `claim_type` | KO `type` |
|---|---|---|
| 含数值（描述/测量） | descriptive / mathematical | `measurement` |
| 方法/流程词且无数值 | methodological | `procedure` |
| 定义词（"定义为/称为"）且无数值 | definition | `definition` |
| 负知识词（不支持/失败/局限） | interpretive | `negative_result` |
| 能力词（支持/实现/提供）且无数值 | descriptive | `capability_claim` |

`knowledge_id = ko:<facet>:r<report_id>-c<NNN>`：report_id 是稳定锚，slug 低熵；
重编译同报告得到同 id ⇒ 入库幂等（`ON CONFLICT (knowledge_id) DO NOTHING`）。

## 5. 门判据（与 GATE-RULES 同义，不自造）

| 闸 | 规则 | 实现 |
|---|---|---|
| G1 结构 | JSON 可解析 / schema 通过 / id 唯一 / 必填字段齐 | `validate_ko_v1.validate_document`（S7 出库前强制执行） |
| G2 证据 | 报告可解析（report_id 存在）+ 小节可解析（heading/anchor/span/section_sha256 重算命中）+ 引文逐字 | `compiler.verify_kobject`，逐条记录 `{report_resolved, section_resolved, quote_verbatim, artifact_resolved}` |
| G3 语义 | 独立评审（工序 04）+ 强模型抽样 | **不在本规范内**；编译面只准备评审请求，`contradictions[].status=needs-independent-review` |

## 6. 缺口算子接口（TK 缺口 → TP 研究任务）

编译面的 S6 与 `gaps/*.json` 产出两种缺口，**只登记、不自行派生研究任务**（任务归 TP）：

```json
{"gap_id": "<string>", "kind": "unresolved-claim | contradiction | coverage-hole",
 "statement": "<原文/模板>", "evidence_refs": ["report:<id>#<anchor>"],
 "provenance_kind": "factory-compile | legacy-migration",
 "research_task": {"title": "<string>", "acceptance": "<机器可裁判据>", "repo_hint": "<仓名|空>"}}
```

- TK 侧：`knowledge/legacy-migration/gap-queue.json`（存量缺口）、`runs/compiler-v1/contradictions*.json`（新缺口）。
- TP 侧：任务榜按 `gap_id` 去重收养；未收养的缺口留在队列里可审计（不静默丢弃）。
- 反向：研究任务完成后产出的报告被 03 再编译，`evidence` 回链同一 `report_id`，缺口由 `resolved_by_claims` 闭合。

## 7. 限界（honest）

1. 抽取是**规则级**（数值/判定词触发），不做语义蕴含判断；`confidence.basis=unassessed`。
2. 表格行、代码块不产 claim（避免不可读断言），因此表内数值只经正文叙述进入知识面。
3. 矛盾判定是**结构规则**（同模板异值），会含假阳性（不同条件的两条数），故一律转 04 评审。
4. 跨报告同域同主体同断言会被 DDL 唯一索引合并（防手抄），第二份报告的回链登记在运行工件里，
   尚未落成 `ko_evidence` 的多报告边——已在 `RESULTS-v1.md` 记为缺口。
5. 代码分析类输入只支持"给出处"（`code-location`），KO v1 目前要求 `report_id`，
   故代码面知识停在四契约层（见 `TK-INGEST-INTERFACE-v1.md` §5）。
