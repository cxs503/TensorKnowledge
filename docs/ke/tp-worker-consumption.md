# tp_worker 注入面改造方案 + knowledge_id 引用计数（KBM-TKC-INDEX-API ③）

## 1. 现状与问题

Agent 开工"三查"目前是向 `knowledge_base` 写 SQL（或 prompt 内嵌 SQL）：连不上就
没有 `cited_kb`；命中了也不落账，**"谁在哪个任务里用了哪条知识"不可归因**，于是
KPI-KB-REUSE-RATE 没有可靠分母/分子。

## 2. 改造后的注入面（三查 → 四维索引 HTTP）

工具链：`ke/worker_probe.py`（参考实现，`python -m ke.worker_probe`）。

| 旧三查 | 新调用 | 回答 |
|---|---|---|
| 查经验/坑 | `GET /by-problem?problem=<goal 关键词>&log=true` | 这条任务踩过的缺口/负面结果/适用边界 |
| 查概念 | `GET /by-concept?concept=<域/系统/关键词>&log=true` | 对象是什么、属于哪个域/系统 |
| 查方法 | `GET /by-method?method=<goal 关键词>&log=true` | 结论是用什么方法得到的（沿 claim→evidence 边） |
| 追加查证据 | `GET /by-evidence?evidence=<命中 claim 的 evidence_refs>` | 支撑链是否完整 |

输出一份 `tk-worker-injection/1` 知识包（`knowledge_id/kind/statement/matched/
dimensions`），可直接塞进 worker 上下文；所有查询都带 `mission_id + consumer`，
命中即写 `ke_usage(event_type='inject')`。

**任务完成回写**：worker 在产物落盘后调用
`POST /ko/{id}/cite {mission_id, consumer, artifact, context}`，把"真的用到了"落账。
`cite` 按 `(ko_id, mission_id, artifact)` 幂等——重跑任务不会刷高复用率。
mission goal 的验收要求：goal 文本必须引用 `knowledge_id`，且 artifact 里能看到
该知识的解析值/判据（见 §4 三案例）。

## 3. knowledge_id 引用计数与 KPI 定义

存储：`ke_usage(event_id, ko_id, event_type∈{inject,cite}, mission_id, consumer,
artifact, context, created_at)`；索引 `(ko_id,event_type)`、`(mission_id)`。

```
KPI-KB-REUSE-RATE = |{被 cite 且被 inject 过的 ko}| / |{被 inject 过的 ko}|
```
（严格口径 ≤1；`GET /usage/stats` 同时给出 event 级比率、`cited_without_injection`
和 per-mission 分解。`cited_without_injection` 单独暴露而不是塞进分子，避免
"引用未被注入的对象"把比率刷过 1。）

SQL 等价：
```sql
SELECT COUNT(DISTINCT CASE WHEN event_type='cite' AND ko_id IN
         (SELECT ko_id FROM ke_usage WHERE event_type='inject') THEN ko_id END)::float
     / NULLIF(COUNT(DISTINCT CASE WHEN event_type='inject' THEN ko_id END),0)
FROM ke_usage;
```

## 4. 验收：Agent 使用 TK 知识完成任务的实证（≥3）

运行：`python scripts/tk_agent_cases.py`（进程内起 KE API + 灌 `knowledge/oss-lbm`
371 条记录，全部数字由脚本从 API 响应/知识原文解析后计算，零手抄）。产物在
`artifacts/tk-agent-cases/`。

| case | 维度 | 知识来源（knowledge_id） | 知识被怎么用 | 数字结果 | 判定 |
|---|---|---|---|---|---|
| A | concept+method | `tkc:oss-lbm:kruger-taylor-green-decay` + 其 evidence | 从 claim 解析衰减率关系 `2/t_d=2ν(kx²+ky²)`，独立 D2Q9 代码拟合 d lnE/dt | 实测 t_d 与公式相对误差 **0.147%**；对照组漏掉 ky² 项 → **49.8%** | PASS (<3%) |
| B | evidence | `tke:oss-lbm:kruger-poiseuille-bb-tau` | 用证据维对全语料做 claim↔evidence 对称性与引文覆盖率审计；把引文公式与本地实现 TAU_EXACT 对拍 | dangling=0、asymmetric=0、quote→impl 相对误差 ~1e-16 | PASS |
| C | problem | `tkc:oss-lbm:kruger-poiseuille-bb-exactness-scope`（contested） | 用"精确解适用范围"这条 contested 判据设计跨宽度扫描，并解析 claim 内报告的 L2 做对照 | 力驱动格式下 worst L2 < 3%（各宽度），对照组 naive τ 误差 >15% | PASS（scope probe，非复刻） |

每案例 artifact 内含 `mission_goal`（引用 knowledge_id）、`knowledge_used`、
`knowledge_parsed`（从知识文本解析出的值）、`experiment`、`verdict`、
`citations`（cite 事件回执）与 `artifact_sha256`。`summary.json` 汇总三案例 +
`GET /usage/stats` 的 KPI。

图（`artifacts/tk-agent-cases/`）：`fig-taylor-green.png`（能量衰减 vs 知识公式）、
`fig-poiseuille.png`（知识 τ vs naive τ 剖面）、`fig-exactness-scope.png`（跨宽度
L2，本文 vs claim 报告值）。

## 5. 灰度与回滚

1. 影子期：worker 仍走旧 SQL，同时调 `worker_probe`，只记录不注入（对比命中率）。
2. 切读：注入包改由 `/by-*` 提供；`log=true` 打开，观察 `ke_usage` 增长。
3. 切写：产物落盘后必须 `cite`；KPI 进周报。
4. 回滚：读面可整体关闭（`KE_REQUIRE_READ_AUTH` 不设=默认开放→或反向关端点），
   `ke_usage/ke_facet` 是附加表，删表不影响 `ke_ko` 主数据；`POST /index/rebuild`
   可随时重建投影。

## 6. 未完成/边界

- 未把 `worker_probe` 直接接到 TensorPlatform 的 tp_worker 进程（跨仓改动，本轮
  交付参考实现 + 契约；接线由平台侧按 §2 调用）。
- `knowledge_base`（KB 卡）与 KE KO 是两套 id 空间：本方案的 `knowledge_id` 指
  KO id（`tkc:/tke:`）；KB 卡的 `kb_key` 计量仍由 `/kb/search` 的
  `knowledge_injections` 承担，未合并两套账（合并需先统一 id，属后续项）。
