# RCI 阶段 2a · 三仓存储接口摸底（真实位置 / 格式 / 关联字段）

> 锚点 **KBM-RCI-S2-SCHEMA**（第 1 轮任务榜）| 2026-11-12 | 取证方式：直连只读查询 + 源码阅读
> 纪律：本文每个数字都能用文中给出的 SQL/命令重放（零手抄）。无法确证的一律标 UNKNOWN，不猜。

## 0. 结论速览

| 仓 | 真实数据在哪 | 现状 | 对 Schema v1 的关键约束 |
|---|---|---|---|
| **TensorPlatform (TP)** | PostgreSQL `tensorplatform` @ localhost:5432（服务 :8010，root-path `/tp`） | 活的、在写：`tensor_reports` **9637** 行 / 7897 个 mission | 报告是证据的一级锚：`report_id` 稳定，但**小节标题风格高度异质** |
| **TensorKnowledge (TK)** | `ke_ko`/`ke_edge`/`ke_review`（KE_DSN；无 KE_DSN 时 SQLite） | **服务未运行**（8021/8801 无监听）；生产库无表、无数据 | v1 需自建约束；不能假设已有 L1 存量 |
| **TensorData (TD)** | 默认 `sqlite:///./data/tensordata.db` | **未部署**：无 `data/` 库、无进程、仅 2 个 migration | L0 原件链路当前只有契约，无实例 |

## 1. TensorPlatform（清理后逐一实测）

### 1.1 位置与连接

```
进程：/root/tensor-ecosystem/TensorPlatform/.venv/bin/python -m uvicorn main:app --port 8010 --root-path /tp
DB  ：postgres://…@localhost:5432/tensorplatform   (backend/config.py: DATABASE_URL 默认值，实测口令为部署值)
健康：GET /api/v1/health → {"status":"healthy",…,"capability_ledger":{…"unverified":17,"overclaim":2,"status":"DEGRADED"}}
```

### 1.2 `tensor_reports`（报告 = 证据一级锚）

来源：`backend/migrations/090_tensor_reports.sql` + `096_report_gate.sql`，**实测列与迁移文件一致**：

| 列 | 型 | 用途（接口规范中的用法） |
|---|---|---|
| `id` SERIAL | int | 证据锚 `ko_evidence.report_id` |
| `organization_id` / `created_by` | int | 归属与作者（审计） |
| `title` / `summary` | text | 检索面 |
| `scenario_key` | text | 战役/场景键（可作 `provenance.node_id`） |
| `mission_id` | int | 任务号 → `provenance.mission_id` |
| `stage` | text | 阶段 |
| `tags` JSONB | jsonb | 预留 `ko:` 回引槽（**现网未使用**，见 interface-spec §2.1） |
| `markdown` | text | **小节锚的唯一来源** |
| `figures` JSONB | jsonb | `[{name, caption}]` → `artifact_ref{kind:'report_figure'}`；PNG 落 `TENSOR_REPORT_FIGURE_DIR/<report_id>/<name>.png` |
| `status` | text | 发布态（默认 published） |
| `qa_status` VARCHAR(20) CHECK(pending/passed/rejected) | varchar | 质量门（见 1.3） |
| `qa_rejection_reason` / `qa_checked_at` | — | 质量门审计 |

实测统计（`2026-11-12 00:2x`，SQL 见 §5）：

```
总报告 9637 | 不同 mission_id 7897 | 最早 2026-10-29 | 最新 2026-11-12
qa_status: passed 27 / pending 9603 / rejected 7
figures 为空 2015 / 非空 7622
markdown 含 artifacts/ 或 runs/ 路径 5319
六要素标题齐全且带工件路径 4515  (46.9%)
有方法节 8447 | 有结果节 8067 | 有误差节 8485
```

### 1.3 报告可作为证据的现实约束（关键发现）

- **`qa_status='pending'` 占 99.6%**：不能把"报告存在"当"报告已审"。
- **小节标题异质**（id>9500 抽样，按出现次数）：`④ 结果图` 1200、`4. 结果图` 786、`① 案例介绍` 741、`② 怎么做的` 615、`3. 计算结果` 553、`1. 案例介绍` 533、`③ 计算结果` 521、`⑥ 误差判定` 448、`⑤ 注意点` 336、`6. 误差判定` 302、`3. Results` 257 …
  ⇒ 任何"固定六要素标题匹配"的抽取器会漏掉一半以上；v1 一律「抽原文 heading + 派生 anchor + 存 span/sha256」。
- **工件引用是自由文本**：`artifacts/…`/`runs/…` 出现在 markdown 里，TP 无 artifact 登记表（`information_schema` 无 `%artifact%` 业务表）⇒ 目前**没有**从 `report_id` 到 sha256 的结构化路径。这是 L0→L1 断点（改进项见 §4）。

### 1.4 知识相关既有表（跨仓映射的落点）

| 表 | 行数 | 关键列（实测） | 与 v1 的关系 |
|---|---|---|---|
| `knowledge_base` | **66** | `kb_key,ktype,domain,title,content,evidence,source,status,injected_count,last_hit_at,cited_count,last_cited_at` | `ktype`: capability 50 / trap 6 / pattern 4 / lesson 4 / fact 2 → 映射 `type`（schema-v1 §2）；`evidence` 为 2.8–8.3 KB 自由文本 |
| `knowledge_injections` | **3** | `injection_id,mission_id,kb_id,kb_key,kb_domain,consumer,source,package_sha256,match_score,match_terms,injected_at,cited_at,citation_count,citation_ref` | 消费计量口径的现成落点（interface-spec §4.3） |
| `negative_knowledge_ledger` | **151** | `entry_id,mission_id,node_id,hypothesis,falsification_evidence,failure_kind,applicable_conditions,keywords,domain_tags,confidence,schema_version,status` | → `type='negative_result'`；`schema_version` 实测两写法 `1.0`(150)/`v1`(1)，`failure_kind` `hypothesis_falsified`(25)/`falsified_hypothesis`(1) |
| `tensor_maturity_verdicts` | **286** | `repo,scope,mission_id,level,evidence jsonb,verdict_by,gate_state,gate_level,gate_note jsonb` | **L3 唯一通道的真源**：`gate_state='confirmed'` 51 行（gate_level 2/3/4 = 31/7/13），`reopened` 111，`unmapped` 106，`pending` 12，`no-reopen(orig=awaiting_pr_merge)` 3 |
| `tensor_benchmark_cases` | 16 | `anchor_slug,case_name,ref_source,metric,tolerance,repo,status,passed_at` | benchmark_card `linked_keys` |
| `tensor_xval_cases` | 7 | `case_key,anchor_slug,paired_paper,target_repo,metrics jsonb,xval_table jsonb,bug_suspects jsonb` | xval_gate 票据来源 |
| `tensor_repro_verdicts` / `tensor_capability_deltas` | — | 复现裁定 / 能力增量台账 | repro_gate 票据来源、能力台账关联 |

**KB 消费实测几乎为零**：`sum(injected_count)=3`、`sum(cited_count)=2`（66 条中仅 3 条被注入过）。即"知识回流"当前基本空转——接口建成后第一件事是打通 1 条闭环（m8802），而不是继续扩充卡片数量。

## 2. TensorKnowledge（本仓）

### 2.1 真实存储接口（源码确证）

`ke/apistore.py` DDL：`ke_ko(id,kind,doc,domain,producer,version,production_status,evidence_status,review_status,publication_status,search_text,created_at,updated_at)`、`ke_edge(src_id,dst_id,relation,edge_kind)`、`ke_review(...)`；`kind` 由 ID 前缀推断（`tkc:`claim/`tke:`evidence/`tkp:`provenance/`tkr:`review）。

`ke/api.py`：默认 `:8021`，端点 `/ko*`、六类查询 `/query/by-status|by-evidence-relation|chain|by-domain|claim-evidence|stats`、`/search`、`/kb/search`；写面需 `KE_API_TOKEN`，未配置=503（失败关闭）。

**实测状态**：8021/8801 均无监听、`ps` 无 `ke.api` 进程、`tensorplatform` 库内无 `ke_%` 表 ⇒ **KE 服务未部署运行，L1 表在现网无数据**。

### 2.2 本仓已有 schema 资产（不重复造）

`schemas/`：`knowledge-object.schema.json`（通用 KO，19 类 object_type，`tko:` 命名）、`claim-record`/`evidence-record`/`provenance-record`/`review-event`、KBM-SCHEMA-W1 五类卡 `method/parameter/failure/benchmark/code-pointer-card.schema.json`、`ke-query.schema.json`、`ke-mapping.schema.json`。

`knowledge/kbm/`：仅 `demo-sample`（1 份 demo 抽取）。即**五类卡尚无规模存量**，本轮 v1 只需把词表接上，不需要迁移数据。

## 3. TensorData

| 项 | 实测 |
|---|---|
| 表（`tensordata/models.py`） | `data_assets`(id, owner, lifecycle_state, provenance_status, rights_status, allowed_purposes, metadata_json)、`data_artifacts`(id, asset_id, role, filename, media_type, size_bytes, **sha256**, storage_uri)、`datasets`/`dataset_versions`(manifest_json, **manifest_sha256**)、`provenance_records`(activity_type, inputs_json, outputs_json, code_digest, environment_digest)、`quality_reports`(artifact_id, artifact_sha256, profile, status, findings_json) |
| API | `/api/v1/assets`、`/assets/{id}/artifacts`、`/artifacts/{id}/content`、`/datasets…`、`/provenance`、/quality；API-key 鉴权 |
| 存储 | `TENSORDATA_DATABASE_URL` 默认 `sqlite:///./data/tensordata.db`；`TENSORDATA_STORAGE_ROOT` 默认 `./data/artifacts` |
| **现网状态** | **服务未运行、`data/` 目录不存在**（迁移仅 `0001_initial_schema`、`0002_quality_reports`）⇒ 已注册资产 = 0，可核 sha256 = 0 |

结论：TD 是"设计就绪、实例未起"。因此本轮工件闸只能做**结构性校验**（`kind='tensor_data_artifact'` 必须带 64 位 hex sha256；`report_figure` 必须命中 `figures[].name`），并把它如实记为"弱校验"，不给假绿灯。

## 4. 由此确定的改进项（下一轮，非本单交付）

| # | 缺口 | 建议动作 | 验收判据 |
|---|---|---|---|
| G1 | 报告→工件无结构化链 | TP 增加报告级 `artifact_refs`（或复用 TD 注册 + 回写 `report_id`） | 至少 100 份报告可从 `report_id` 走到 sha256 |
| G2 | KE 未部署 | 起 KE 服务 + 迁移 v1 DDL（本文 scratch 验证已就绪） | `GET /healthz` 200 且 `ko_object` 有 >0 行 |
| G3 | TD 未起 | 起 TD（sqlite 或 PG）+ 导入 10 个真实工件 | 工件闸从"结构校验"升为"内容校验" |
| G4 | KB 空转 | 打 1 条 TK→TP 注入闭环并计量 | `knowledge_injections` 增量 ≥1 且 `citation_count` 可读 |
| G5 | legacy 口径漂移 | 映射层归一枚举（`schema_version`/`failure_kind`） | 归一后统计口径唯一，历史行不改 |

## 5. 复现命令（只读取证）

```bash
# TP 报告规模与质量门
psql -U postgres -d tensorplatform -Atc "select count(*), count(distinct mission_id), min(created_at)::date, max(created_at)::date from tensor_reports;"
psql -U postgres -d tensorplatform -Atc "select count(*) filter (where qa_status='passed'), count(*) filter (where qa_status='pending'), count(*) filter (where qa_status='rejected'), count(*) filter (where figures='[]'::jsonb) from tensor_reports;"
# 小节标题分布（异质性证据）
psql -U postgres -d tensorplatform -Atc "select h, count(*) from (select unnest(regexp_matches(markdown,'(?m)^#{1,3} (.+)\$','g')) h from tensor_reports where id>9500) t group by h order by 2 desc limit 15;"
# 知识类既有表
psql -U postgres -d tensorplatform -Atc "select ktype, count(*), sum(injected_count), sum(cited_count) from knowledge_base group by 1 order by 2 desc;"
psql -U postgres -d tensorplatform -Atc "select gate_state, gate_level, count(*) from tensor_maturity_verdicts group by 1,2 order by 3 desc;"
# KE 是否在跑
curl -s -m 2 http://127.0.0.1:8021/healthz ; curl -s -m 2 http://127.0.0.1:8801/healthz
```

## 6. 证据分级（按仓）

| 结论 | 级别 | 依据 |
|---|---|---|
| TP `tensor_reports` 列/行数/QA 分布/标题分布 | **REAL** | 直连 SQL，可重放 |
| TP 三张知识表行数与口径漂移 | **REAL** | 同上 |
| TK `ke_ko` 表结构与端点集 | REAL（源码）/ **WITHHELD**（运行态） | 源码确证 + 无进程 |
| TD 表结构与 API | REAL（源码）/ **WITHHELD**（运行态） | 源码确证 + 无实例、无 `data/` |
| 报告→工件 sha256 链路 | **NOT_SUPPORTED** | 两侧均无结构化字段 |
| 「E-TR 现网上界 ≈0.47」 | REAL（下界估计） | 六要素+工件路径齐全 4515/9637=46.9%，是乐观上界 |

## 7. 未完成 / 未做

- 未在 TP 生产库建任何表（只读）；未改 TP/TD 一行代码。
- 未部署 KE/TD 服务；未做 v1 DDL 的生产迁移与 `ke_ko` 存量回填。
- 未做抽取器质量评测（需独立评测集，另立锚点）。
- TP `tensor_reports` 的 `organization_id` 多租户语义未展开核查（与本单无关，登记为 UNKNOWN）。