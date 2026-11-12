# TK ↔ TP ↔ TD 接口规范 v1（RCI 阶段 2a）

> 锚点 **KBM-RCI-S2-SCHEMA** | 版本 1.0.0 | 2026-11-12
> 依据：三仓摸底实测（`docs/rci/recon-three-repos.md`）；对象定义 `docs/rci/schema-v1.md`

一句话分工：**TP 产出报告与验证结论，TD 保存原件，TK 保存"可证伪的断言 + 回链"**。三者之间**只传 ID 与哈希，不传正文副本**。

## 1. 责任边界（谁拥有什么）

| 数据 | 唯一所有者 | 其他两方如何获取 |
|---|---|---|
| 原始工件（数据/场文件/图） | TensorData `data_artifacts`（内容寻址，只增不覆盖） | 按 `artifact_id`/`sha256` 取内容 |
| 进展报告正文 + 图元数据 | TensorPlatform `tensor_reports` | 按 `report_id` 读取，**不复制进 TK** |
| 平台验证结论（maturity/benchmark/xval/repro） | TensorPlatform 三张门表 | 按 `verdict_id` 引用，写入 TK 只读票据 `ko_verification` |
| 知识对象（断言/条件/证据链/局限） | TensorKnowledge `ko_object` | 通过 KE API 查询；报告侧只存 `knowledge_id` 回引 |

**反模式（明令禁止）**：① 在 TK 里存报告 markdown 副本；② 在 TP `knowledge_base` 里再存一份知识对象结构化正文；③ 在 TD 里存知识断言；④ 任何一方复制另一方的 ID 生成规则。

## 2. 标识符与关联字段（实测列名，逐项对应）

### 2.1 主键与关联

| 方向 | 本侧字段 | 对侧字段 | 基数 | 实测状态 |
|---|---|---|---|---|
| TK → TP 报告 | `ko_evidence.report_id` (BIGINT) | `tensor_reports.id` (SERIAL) | N:1 | 9637 行可回链 |
| TK → TP 验证 | `ko_verification.maturity_verdict_id` | `tensor_maturity_verdicts.id` | N:1 | 286 行，其中 confirmed 51 |
| TK → TP 案例 | `payload.linked_keys`（benchmark_card） | `tensor_benchmark_cases.anchor_slug` | N:1 | 16 行 |
| TK → TD 原件 | `ko_evidence.artifact_ref.ref` + `sha256` | `data_artifacts.id` + `sha256` | N:1 | **TD 无运行实例、无 `data/` 库 → 现网 0 条可核**，见 §7 |
| TP 报告 → TK | `tensor_reports.tags` 内含 `ko:<facet>:<slug>`（约定） | `ko_object.knowledge_id` | N:N | **未落地**（现网 tags 无此约定），本轮给出规范、不改 TP |
| TP KB → TK | `knowledge_base.kb_key` | `ko_object.knowledge_id`（迁移期映射） | 1:1 | 66 条 legacy，映射规则见 §5.3 |

### 2.2 报告小节锚（跨库最脆弱的一环）

TK 侧 `section` 三元组（`heading` 原文 / `anchor` slug / `span`+`section_sha256`）必须由**TP 报告正文**解析得出，规则：

```
heading := markdown 中 ^#{1,6}\s+(.+)$ 的原文（逐字，含 ①②③/emoji/编号）
anchor  := 去前导序号与符号 → 小写 → 非[\w\u4e00-\u9fff]折叠为 '-' → 去首尾 '-'
span    := [标题行起始偏移, 下一个同级或更高级标题起始偏移)
section_sha256 := sha256(markdown[span_start:span_end])
```

实测标题风格分布（`tensor_reports` id>9500 抽样）：`④ 结果图` 1200、`4. 结果图` 786、`① 案例介绍` 741、`3. Results` 257 …… ⇒ **禁止把"六要素"写成固定枚举匹配**，必须"抽原文 + 存原文 + 用锚点查"。

## 3. 接口清单（按现网可调用性排序）

| # | 接口 | 方向 | 契约 | 现网可用性 |
|---|---|---|---|---|
| I1 | `GET /api/v1/tensor/reports?limit=&mission_id=` | TK → TP 读 | 列表（不含正文） | 服务在跑（:8010，root-path `/tp`），需 token |
| I2 | `GET /api/v1/tensor/reports/{id}` | TK → TP 读 | 单份正文+`figures[]` | 同上 |
| I3 | `GET /api/v1/tensor/knowledge/status` / `/overview` / `/chain` | TK → TP 读 | KB 消费与链视图 | 路由存在（`backend/api/knowledge_hub.py`） |
| I4 | `POST /api/v1/tensor/reports` | TP ← 写 | 报告发布（mission_id/tags/figures） | 在用（9637 份） |
| I5 | KE `POST /ko`、`GET /ko/{id}`、`GET /query/chain`、`GET /kb/search` | 外部 → TK | 见 `docs/ke/api.md` | **KE 服务未运行**（8021/8801 无监听）→ 本轮为契约态 |
| I6 | TD `POST /api/v1/assets`、`POST /assets/{id}/artifacts`、`GET /artifacts/{id}/content` | TK → TD | 注册/上传/取回（API-key 鉴权） | **未部署、无 `data/` 库** |
| I7 | 验证回流任务榜 | TP → TK | 平台把验证结论作为**任务**下发（锚点即本单 `KBM-RCI-S2-SCHEMA`） | 在用（任务榜） |

**为什么验证回流走任务榜而不是直推 API**：KE 服务当前未常驻；且 owner 铁则要求 L3 只由平台门产生。以「平台验证单 = 队列里的一条任务」实现，天然带 mission_id/artifactId/审计，KE 侧只需幂等消费（`ticket_id` 主键去重）。直推 API 会引入"谁有写权限"的第二个真相源。

## 4. 三条主流程（含失败降级）

### 4.1 沉淀（Agent 完成一单 → 知识对象）

```
1. Agent 提交报告到 TP，得 report_id
2. Agent 抽取知识对象：evidence[].report_id + section.heading
3. 解析器回填：anchor / span / section_sha256 / resolution{report,section,artifact}_resolved
   · 报告闸失败 → 该证据作废，不得写入（宁缺不假）
   · 小节闸失败 → 允许写入但 resolution.section_resolved=false，并在 next_actions 加 check_source
   · 工件闸失败 → 同上，加 provide_artifact
4. E-TR ≥ 0.8 → storage_level='L2'（入关系表）；< 0.8 → 停留 L1
5. 全部 resolution 由解析器写，人工/Agent 不得手填（DB 列权限 + 摄取管线单一写者）
```

### 4.2 验证回流（L2 → L3）

```
平台门确认（tensor_maturity_verdicts.gate_state='confirmed' 且 gate_level>=2）
  → 平台侧写 ko_verification 票据（ticket_id = 'mv:<verdict_id>'，source='maturity_gate'）
  → TK 消费：UPDATE ko_object SET verification_status='platform_verified', storage_level='L3'
  → 触发器校验：票据 confirmed/level>=2 + 至少一条三闸全绿证据
  → 自动写 ko_state_event(actor_role='platform', ticket_id) → ko_l3_audit 对账
reopen（gate_state='reopened'）→ 反向一格回 report_claimed，原地失败不删数据
```

### 4.3 消费（检索面）

- 只返回 `verification_status <> 'unverified'` **且** `R1≥0.5` 的对象；L3 对象带票据回执。
- 返回体必须含 `evidence[].report_id`/`section.anchor`/`artifact_ref` 三件套，使调用方可自行复核（可证伪性随结果一起交付）。
- 命中记注入台账（对齐 TP `knowledge_injections` 的 `injection_id/mission_id/kb_key/match_score/injected_at`），使 KB 消费可计量。

## 5. 数据映射（既有列 → v1 字段）

### 5.1 `tensor_reports`（TP）

| v1 字段 | 来源 |
|---|---|
| `evidence[].report_id` | `id` |
| `evidence[].section.*` | `markdown` 解析（§2.2） |
| `evidence[].artifact_ref{kind:'report_figure'}` | `figures[].name` |
| `provenance.mission_id` / `node_id` | `mission_id` / `scenario_key` |
| 质量提示（不进 v1） | `qa_status`（passed 27 / pending 9603 / rejected 7）——**pending 占 99.6%，不能当"已审"用** |

### 5.2 `negative_knowledge_ledger`（TP，151 行）→ `type='negative_result'`

`entry_id→provenance.derived_from`；`hypothesis→claim`；`applicable_conditions→conditions.description`；`falsification_evidence→evidence[]`（需补 report_id+section，现为自由文本 ⇒ **当前不可直接晋级**）；`failure_kind→payload.failure_kind`；`confidence→confidence.score`。

实测两处口径漂移，映射时必须归一：`schema_version` 有 `1.0`(150) 与 `v1`(1) 两种写法；`failure_kind` 有 `hypothesis_falsified`(25) 与 `falsified_hypothesis`(1) 两种拼法。归一表放摄取管线枚举，不改历史行。

### 5.3 `knowledge_base`（TP，66 行）→ `type=capability_claim`

`kb_key`（形如 `cap:TensorFEM:m15325_CASE-LAME-CYLINDER`）→ `knowledge_id = ko:<repo 小写>:<mission/case slug>`；`ktype` 见 schema-v1 §2 映射；`evidence` 现为 2.8–8.3 KB 自由文本 ⇒ **不可直接当 evidence[]**，必须先拆成带 report_id+section 的条目才能进 L2。

## 6. 变更与一致性

| 场景 | 契约 |
|---|---|
| 报告被编辑（TP 允许 PATCH） | TK 侧 `section_sha256` 失配 → 该证据 `section_resolved=false`，落 `ko_state_event` 变更事件；L3 对象触发 reopen 复核（不自动降级，等平台裁定） |
| 知识对象改断言 | 新 `version` + `relations.supersedes`；L3 旧版保留只读 |
| 报告的 `mission_id` 归属变更 | 不允许：`report_id` 是不可变锚；需要改归属=新报告 |
| 幂等 | 所有写入以 `knowledge_id` / `ticket_id` / `evidence_id` 为幂等键；重放安全 |
| 鉴权 | TP：Bearer token；TD：`X-API-Key`；KE：`Authorization: Bearer $KE_API_TOKEN`（未设=写面 503，失败关闭） |

## 7. 现网差距（实测，不含推测）

| 差距 | 证据 | 影响 |
|---|---|---|
| KE 服务未运行 | 8021/8801 无监听；`ps` 无 `ke.api` 进程 | L1/L2 落库链路无端到端证据，本轮契约态交付 |
| TD 未部署且无数据 | 无 `data/` 目录、无服务进程、仅 2 个 migration | 工件闸只能结构校验（sha256 在位），核不了内容 |
| KB 消费几乎为零 | `sum(knowledge_base.injected_count)=3`、`sum(cited_count)=2`（66 条中仅 3 条被注入过） | 「知识回流」当前是空转，接口建成后需先测通 1 条闭环（m8802） |
| 报告无结构化证据引用 | 仅 5319/9637 含 `artifacts/`\|`runs/` 路径 | E-TR 上界 ≈ 0.47 |
| legacy KB evidence 为自由文本 | 66/66 行 | 需二次抽取才能进 L2 |
| neg ledger 口径漂移 | `schema_version` 两写法、`failure_kind` 两拼法 | 映射层必须归一，否则统计口径分裂 |

## 8. 验收自检（本单）

```bash
python -m pytest tests/test_ko_v1_schema.py -q     # 25 passed（含真 PG 约束 5 条）
psql -d tensorknowledge -f schemas/sql/knowledge_object_v1.sql   # scratch schema 内验证后 DROP
```
未做什么：未改 TP/TD 任何代码；未在生产库建表；未部署 KE 服务。以上均如实登记在 `docs/rci/recon-three-repos.md` 与 finish 报告。