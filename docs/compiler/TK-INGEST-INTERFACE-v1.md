# draft → TK 入库接口契约 v1（factory 03 产出 → 四契约/KO 治理面）

> 锚点 **KBM-TKC-COMPILER-ALIGN** | 版本 1.0.0 | 2026-11-12
> 对齐：`schemas/kf_result.v1.schema.json`（工序结果信封）× `schemas/knowledge-object-v1.schema.json`（KO v1）
> 实现在 `ke/ko_store.py`（KO v1 落库）+ `ke/contract.py`（四契约落库）。

## 1. 一句话

factory 的工序 03 交 `kf_result.v1` 信封（四文件：claims/evidence/provenance/extraction_summary）；
TK 侧把它**投影**成两类持久形态：① 四契约记录（claim/evidence/provenance 原样，字节不改）
② KO v1 对象（带 `report_id + 小节锚` 的断言聚合，才是可检索/可评审单元）。
**不存报告正文副本**（正文永远在 `tensor_reports`，只传 ID 与哈希）。

## 2. 字段映射表（逐字段，实测列名）

| kf_result / 四契约 | KO v1 | 库列（`schemas/sql/knowledge_object_v1.sql`） | 规则 |
|---|---|---|---|
| `report_id` | `evidence[].report_id` | `ko_evidence.report_id BIGINT >0` | 必须是真实 `tensor_reports.id`；无报告的代码面知识不得升 KO（§5） |
| `provenance.source_hash` | `provenance.derived_from` 的前置校验 | — | `sha256:` 前缀 + 平台独立重算 `markdown` 哈希，不一致判门失败 |
| `outputs.claims[i].statement` | `claim` | `ko_object.claim` | 逐字保留报告句子；**不改写、不翻译、不合并** |
| `outputs.claims[i].claim_type` | `type`（映射表见 SPEC §4） | `ko_object.type` | 词表并为 KBM-SCHEMA-W1 11 类 |
| `outputs.evidence[i].locator.quote` | `evidence[0].section.excerpt` | `ko_evidence.excerpt` | 必须是报告 markdown 的逐字子串 |
| `locator.section_sha256` | `section.section_sha256` | `ko_evidence.section_sha256` | 由 `iter_sections` 重算命中才算 `section_resolved` |
| `locator.char_span` | `section.span` / `payload.char_span` | `ko_evidence.section_start/section_end` | 声明偏移必须精确命中，避免锚点同名内容漂移 |
| `outputs.provenance[i].activity` | `provenance.pipeline` + `generator_version` | `ko_object.provenance`(JSONB) | `pipeline` 是机器可读的来源族：`knowledge-compiler-v1` / `legacy-migration` |
| — | `verification_status` | `ko_object.verification_status` | 上限 `report_claimed`；写入前 `ko_store.ingest_document` 直接拒 `platform_verified` |
| — | `storage_level` | `ko_object.storage_level` | 有 `relations` ⇒ `L2`，否则 `L1`；DDL 双向 CHECK 兜底 |

## 3. 幂等、去重、冲突

| 情形 | 规则 | 机器表现 |
|---|---|---|
| 同 `knowledge_id` 重复入库 | `ON CONFLICT DO NOTHING`（append-only，不改写已入库对象） | `ingest_document()` 返回 `exists` |
| 同 `(domain, subject, md5(claim))` 不同 `knowledge_id` | DDL 唯一索引 `ko_object_claim_uniq` = 同域同主体同断言即同一对象（防手抄） | 返回 `duplicate_claim`，不抛错、不重复存 |
| 同 id 内容变了（claim 修订） | **不许原地改**：新 `knowledge_id` + `relations.supersedes` 边 | 无 UPDATE 路径 |
| 证据重复 | `UNIQUE (knowledge_id, ordinal)` | 幂等 |
| 版本 | `ko_object.version` 单调 +1，语义变化才 +1 | 编译面固定 1 |

## 4. 状态机与不允许的动作

```
unverified --(agent/管线, 需 ko_evidence ≥1 行且 report+section 可解析)--> report_claimed
report_claimed --(仅平台：ko_verification.gate_state=confirmed 且 gate_level≥2 + 三闸全绿)--> platform_verified
platform_verified --(仅平台 reopen 票据)--> report_claimed
```

- 应用层闸：`ko_store.ingest_document()` 对 `verification_status ∉ {unverified, report_claimed}` 抛 `KOWriteError`。
- 数据库闸：`ko_object` 双向 CHECK（`platform_verified ⟺ storage_level='L3'`）+ `ko_state_event` L3 通道 CHECK。
- 评审轴独立：`scripts/ke_state_machine.py` fold；产出方不能批自己的包（`is_independent`）。

## 5. 已知结构缺口（不静默绕过，不私改 schema）

存量 257 条 PG 迁移记录的证据全是 `code-location`（源码快照），**没有 `tensor_reports.id`**；
而 KO v1 的 `EvidenceRef.report_id` 是必填 `integer ≥ 1`、`ko_evidence.report_id CHECK (>0)`。
因此：legacy 记录**停在四契约层**（claim/evidence/provenance 表），`provenance.pipeline='legacy-migration'`
为机器可读标记；只有锚得到报告的断言才升 KO。
修法（待 KBM-RCI schema v1.1，需 owner 侧批准）：`EvidenceRef` 增 `report_kind='external'` +
`external_ref{repo,commit,path,span}`；在此之前不写伪 `report_id`。

## 6. 复跑

```bash
# 历史记录收编（真实 PG 数据 → 四契约统一管线）
KO_DSN="dbname=ke_service user=postgres" python scripts/legacy_ingest_257.py
# 试点批全链（真实报告 → KO → 入库 → 检索）
KO_DSN="dbname=ke_service user=postgres" python scripts/compiler_pilot200.py --out runs/compiler-v1
```
