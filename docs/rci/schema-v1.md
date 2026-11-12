# Knowledge Object Schema v1（RCI 阶段 2a）

> 锚点 **KBM-RCI-S2-SCHEMA** | 版本 1.0.0 | 2026-11-12 | 仓 TensorKnowledge
> 机器可读：`schemas/knowledge-object-v1.schema.json`、`schemas/sql/knowledge_object_v1.sql`
> 校验器/计量器：`scripts/validate_ko_v1.py`；契约测试：`tests/test_ko_v1_schema.py`
> 摸底（真实数据位置/格式/关联字段）：`docs/rci/recon-three-repos.md`；三方接口：`docs/rci/interface-spec.md`

本文只做一件事：把「一条知识」定义成**可机裁、可回溯、不可自我晋级**的对象，并把三条纪律写进数据库约束而不是写进倡议书。

## 0. 设计取舍（与既有体系的关系）

| 既有资产 | 本 Schema v1 的关系 |
|---|---|
| `schemas/knowledge-object.schema.json`（通用 KO，tko: 命名） | **不替换**。它是面向人类学习/概念的宽对象；v1 是**证据驱动**的窄对象，供 RCI 沉淀与平台验证回流使用。v1 对象可作为该宽对象的 `claim_refs` 目标。 |
| 四契约 `claim/evidence/provenance/review-record` | v1 是四契约的**聚合视图**：claim 字段、evidence[]、provenance、review→`ko_state_event`。`ke_ko` 表无需改列，v1 文档作为 `kind='claim'` 的 doc 摄取。 |
| KBM-SCHEMA-W1 五类卡（method/parameter/failure/benchmark/code-pointer） | **并入** v1 `type` 词表（5/11），卡体进 `payload`，且必须通过既有 `schemas/*-card.schema.json`；不另立并行 schema。 |
| TP `knowledge_base` / `negative_knowledge_ledger` / `tensor_reports` | 只读引用：`evidence[].report_id` 指向 `tensor_reports.id`；L3 票据指向 `tensor_maturity_verdicts.id`。不复制正文（贴源原则）。 |
| TD `data_artifacts` | L0 原件唯一归属地。v1 只存 `artifact_ref{kind:'tensor_data_artifact', ref:<uuid>, sha256}`。 |

**架构令遵守**：v1 不引入向量库/图数据库。关联先落关系表（`ko_relation`）+ 版本 + 质量治理；向量/图只在出现真实查询需求（Q2/Q3 类型走查）后作为**派生索引**建设，派生索引可随时重建、不作权威。

## 1. 状态机：verification_status

```
                 + evidence[] 非空
   unverified ─────────────────────▶ report_claimed
       │                                  │   ▲
       │                                  │   │ reopen（平台验证单 gate_state=reopened）
       │      （禁止越级）                 ▼   │
       │                        platform_verified  = L3
       └──────────✗───────────────────────┘
```

| 边 | 触发者 | 前置条件（数据库层强制） |
|---|---|---|
| `unverified → report_claimed` | Agent/管线 | 该对象 `ko_evidence` ≥1 行（report_id + section） |
| `report_claimed → platform_verified` | **仅平台** | ① `ko_verification` 存在 `gate_state='confirmed'` 且 `gate_level>=2` 的票据；② 至少一条三闸全绿证据；③ `storage_level='L3'` |
| `platform_verified → report_claimed` | **仅平台** | reopen 票据（`gate_state='reopened'`），用于基准漂移/复现失败 |
| 其余组合 | — | 触发器 `ko_object_guard` 抛 `illegal verification transition` |

**owner 铁则（唯一通道）**：`platform_verified` 只能由平台验证单写入。校验器对 `actor_role != 'platform'` 一律拒绝（`scripts/validate_ko_v1.py:check_transition`），数据库 `ko_state_event` 上还有 `CHECK (to_status <> 'platform_verified' OR (actor_role='platform' AND ticket_id IS NOT NULL))` 兜底。Agent 能做的最高动作是 `next_actions[].action='request_platform_verification'`。

**验证单来源**（`ko_verification.source`，与平台既有门同键，不另造）：

| source | 平台侧真源 | 现网可用量（2026-11-12 实测） |
|---|---|---|
| `maturity_gate` | `tensor_maturity_verdicts.gate_state='confirmed'` | 51 行（level 2/3/4 各 31/7/13） |
| `benchmark_gate` | `tensor_benchmark_cases.status` | 16 行 |
| `xval_gate` | `tensor_xval_cases.status` | 7 行 |
| `repro_gate` | `tensor_repro_verdicts` | 见 interface-spec §5 |

**L0–L3 四级存储**（与状态正交但强耦合）：

| 级 | 定义 | 权威归属 | v1 表达 |
|---|---|---|---|
| L0 | 原件（原始数据、场文件、日志、图） | TensorData `data_artifacts`（内容寻址 sha256，只增不覆盖） | `artifact_ref{kind:'tensor_data_artifact'}` |
| L1 | 结构化记录（单条知识对象） | TK `ko_object` | `storage_level='L1'`，状态 `unverified/report_claimed` |
| L2 | 关联网络（入边/出边成图） | TK `ko_relation` | `storage_level='L2'`，`relations` 非空（DB CHECK） |
| L3 | 已验证成果（平台门结论） | TK `ko_object` + `ko_verification` | `storage_level='L3'` ⟺ `platform_verified`（DB CHECK 双向） |

> `CHECK ((verification_status='platform_verified') = (storage_level='L3'))` 使「自称 L3」在物理上无法落库。

## 2. type 词表（并入 KBM-SCHEMA-W1，不另立）

| type | 语义 | payload schema | 典型证据类型 |
|---|---|---|---|
| `method_card` | 问题→方法→方程出处→适用域 | `method-card.schema.json` | analytic/code/test |
| `parameter_card` | 无量纲参数/取值/出处 | `parameter-card.schema.json` | literature/measurement |
| `failure_card` | 失效模式+根因+绕法（负知识） | `failure-card.schema.json` | test/simulation |
| `benchmark_card` | case+参考值+容差+历史 | `benchmark-card.schema.json` | analytic/test |
| `code_pointer_card` | 仓/模块/符号→实现了什么 | `code-pointer-card.schema.json` | code/test |
| `capability_claim` | 平台/仓的能力声明（对应 TP `knowledge_base.ktype='capability'`） | 自由 | test/simulation |
| `negative_result` | 被否证的假设（对应 `negative_knowledge_ledger`） | 自由 | simulation/analytic |
| `measurement` | 单次/多次实测量 | 自由 | measurement/dataset |
| `definition` | 术语/口径定义 | 自由 | documentation |
| `procedure` | 可复现操作序列 | 自由 | code/documentation |
| `reference` | 数据/论文/标准指针 | 自由 | literature/dataset |

映射到既有 ktype（TP `knowledge_base`）：`capability`→`capability_claim`；`trap`/`lesson`→`failure_card` 或 `negative_result`；`pattern`→`method_card`；`fact`→`measurement`/`definition`。**单向**：v1 → 既有列，不改既有表语义。

## 3. evidence 溯源规范与可追溯率口径

### 3.1 证据必填四元组

```json
{"report_id": 14521, "section": {"heading": "③ 计算结果", "anchor": "计算结果",
  "span": [1234, 1890], "section_sha256": "…"},
 "evidence_type": "simulation", "artifact_ref": {"kind": "report_figure", "ref": "fig2_diffusion_exact.png"}}
```

- **report_id**：TensorPlatform `tensor_reports.id`（真实在库，实测 9637 份）。跨库只存 ID，正文永远回 TP 取——避免第二份真相。
- **section**：报告内小节。`heading` 必须与 markdown 标题**原文逐字一致**（实测标题风格高度异质：`④ 结果图` 1200 份 / `4. 结果图` 786 份 / `3. Results` 257 份，任何"规范化写死六要素"的方案都会漏），`anchor` 由 `slugify` 派生，`span`/`section_sha256` 由摄取期解析回填（抗篡改，人工不可填）。
- **evidence_type**：measurement/simulation/analytic/literature/code/test/dataset/documentation。
- **artifact_ref**：`tensor_data_artifact`（权威，必须带 sha256）/`repo_path`/`report_figure`/`report_section`/`url`/`none`。

### 3.2 可计算口径（三闸）

```
单条证据可追溯 := 报告闸(report_resolved) ∧ 小节闸(section_resolved) ∧ 工件闸(artifact_resolved)
    · artifact_kind='none' 时工件闸以「小节锚点 + 切片 sha256」代替地址，视为通过
    · url/离线不可核 → artifact_resolved=NULL，计为未通过（诚实计负，不送分）
E-TR := 三闸全绿证据条数 / 证据总条数       ← 取交集，不取平均
辅指标 R1=报告闸通过率, R2=小节闸通过率, R3=工件闸通过率（定位"报告丢了"还是"锚错了"）
```

实现两处、口径一致：`scripts/validate_ko_v1.py:evidence_traceability` 与视图 `ko_evidence_traceability` / `ko_evidence_traceability_global`；`tests/test_ko_v1_schema.py::test_ddl_traceability_view_matches_python_meter` 断两处结果相等（0.5/2/1）。

**晋级门槛**：L3 要求该对象 E-TR = 1.0（至少一条全绿证据，DB 触发器强制）；L2 要求 E-TR ≥ 0.8（工程门，摄取管线强制，见 interface-spec §4）；R1 < 0.5 的知识对象不得进入检索面（不可溯源知识不进知识库）。

**现网基线（本文写作时实测，作为改进起点）**：9637 份报告里 55.2% 引用了 `artifacts/`或`runs/`路径，六要素（方法/结果/误差/工件）齐全的仅 46.9%。即**当前证据链上界**：任何知识对象若先按"报告是否可回链"筛选，E-TR 天花板 ≈ 0.47。这不是缺陷而是事实起点，改进方向写在 §6。

## 4. 字段约束（要点）

- `additionalProperties: false` 全局收紧：未知字段=错误，不做静默丢弃（防字段漂移）。
- `knowledge_id` = `ko:<facet>:<slug>`，与既有 `tko:`/`tk:` 命名空间不冲突；改名不改 ID，退役靠 `relations.supersedes`。
- `version` 单调 +1；L3 对象 `claim`/`doc` 列级不可改（触发器），纠正=新版本 + `supersedes` 边。这是「验证后改内容」漂移的结构性防御。
- `confidence`（产生方评估）≠ `verification_status`（平台结论），禁止互相替代。
- `provenance.content_sha256` = 除自身外规范 JSON（键排序/紧凑分隔）的 sha256；校验器逐次复算。
- `limitations` 字段必须存在（可为空数组）——缺字段=没做局限检查。
- `ko_object_claim_uniq(domain, subject, md5(claim))`：同域同主体同断言只允许一条，防手抄多份与重复沉淀。

## 5. 版本与治理

| 规则 | 落点 |
|---|---|
| 只增不改 | `ko_evidence` / `ko_verification` / `ko_state_event` 三个表 UPDATE/DELETE 直接抛异常 |
| 状态审计 | 任何状态变更自动写 `ko_state_event`（BEFORE/AFTER 触发器，含 actor_role 与票据） |
| L3 对账 | 视图 `ko_l3_audit`：L3 行必须有 confirmed 票据，`missing_ticket` 必须为 0 |
| 分布巡检 | 视图 `ko_state_distribution`（type × status × level） |
| 授权 | 平台验证单只由平台/裁决席写入；TK 服务账号对 `ko_verification` 只读 |

## 6. 已知局限与下一步（honest）

1. **未接活数据**：本次仅在 scratch schema（`ko_v1_test_*`，测后 DROP）验证 DDL，**未在生产 KE 库建表**——生产 DDL 迁移需 owner 令 + 现有 `ke_ko` 数据回填脚本（本轮不含）。KE API 实测**未运行**（8021/8801 无监听），故 L1 落库链路本轮无端到端证据。
2. **工件闸本地化**：`tensor_data_artifact` 现只校验"sha256 在位"，未调 TD API 复核（TD 服务未运行、无 `data/` 库）。interface-spec §4 给了复核调用契约与降级口径。
3. **`url` 类证据离线不可核**：按未通过计负，会低估 E-TR。后续应加"在线复核"批处理而不是放宽口径。
4. **报告小节的解析成本**：`section_sha256` 绑定原文切片，报告一旦被编辑（TP 允许 PATCH）就会失配 → 表现为 R2 下降。这不是 bug，是"证据被改动"的正确信号；处理方式见 interface-spec §6（重新解析 + 变更事件）。
5. **向量/图后置**：未建任何向量索引；L2 关系走 SQL 递归（`WITH RECURSIVE`）即可满足当前 Q3 需求，图库需求待真实查询量证伪。
6. **抽取评测未在本轮**：本文件不提供"抽取质量"结论；抽取器需独立评测集（非通顺度），锚点 KBM-RCI-S2-EXTRACT。

## 7. 复现

```bash
python -m pytest tests/test_ko_v1_schema.py -q         # 25 passed（含 5 条真 PG DDL 约束测试）
python scripts/validate_ko_v1.py --doc ko.json --trace --reports reports.json --repo-root .
python scripts/validate_ko_v1.py --markdown uploads/report.md   # 列出可引用小节锚
psql -d "$KO_DSN" -v ON_ERROR_STOP=1 -f schemas/sql/knowledge_object_v1.sql
```