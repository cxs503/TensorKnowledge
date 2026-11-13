# 四维检索投影（concept / problem / method / evidence）

任务 KBM-TKC-INDEX-API ①。KE 原有六类查询（Q1–Q6）是**记录形状**查询：按状态、
按 relation、按 domain、按 claim→evidence 链。它们回答"记录里写了什么"，不回答
"agent 会怎么搜"。本层补的是**面向检索的投影**：`ke/facets.py` 从同一条 KO 记录
派生四维 facet，`ke/apistore.py` 落 `ke_facet` 表并提供查询，`ke/api.py` 暴露
`/by-concept`、`/by-problem`、`/by-method`、`/by-evidence`、`/facets`。

## 1. 四维定义与派生规则

投影是**确定性的纯函数**（`ke.facets.project_doc`）：同一条记录字节 → 同一组
facet 行；值统一小写、折叠空白、截断 240 字符；按 `(dim, value, field)` 去重保留
最高权重。每行保留 `field`，任何命中都能回到源字段。

| dim | 回答什么 | 来源字段（field） | 权重阶梯 |
|---|---|---|---|
| concept | 这是什么/关于什么 | `scope.domain`(1.0) `scope.system`(1.0) `tags/concepts/keywords`(1.0) `scope.conditions[i]`(0.6) `statement` tokens(0.5) | 精确标识符 > 自由文本 |
| problem | 触及什么开放问题/缺口 | `problem/question/hypothesis/gap/limitations/next_actions`(1.0)、`notes[i]`(0.8)、其 tokens(0.4)、`claim_type∈{question,hypothesis}`→`unresolved:<type>`(1.0) 及其 statement tokens(0.4) | 说明：本语料的 notes 承载 GAP 锚/服务改进点，故归 problem 而非 concept |
| method | 结论是怎么得到的 | evidence：`extraction_method`(1.0) `source.source_type`(0.6) `locator.locator_type`(0.6)；provenance：`activity.activity_type`(1.0)；claim：`method/methods`(1.0) | `/by-method` 会沿 `claim_evidence` 边把证据上的 method 归到 claim |
| evidence | 哪些证据支撑 | claim：`evidence_refs[i]`(1.0)；evidence：`relation`(1.0) `source_type`(1.0) `assessment_status`(0.6) `locator_type`(0.6)；provenance：`generated_entity.id`/`derived_from`(1.0) | 支持用证据 id 反查 claim |

**生产者覆盖面**：记录里若带 `facets: {"concept": [...], "problem": [...]}`，按
最高权重 1.5 追加，无需改代码即可加人工概念。**零领域语义硬编码**：本模块不含任何
船舶/LBM 词表，全部来自记录字段与共享分词器（`ke.consume.tokenize`：ASCII 词 +
中文 bigram）。

## 2. HTTP 契约

| method | path | 说明 |
|---|---|---|
| GET | `/by-concept?concept=&field=&kind=&domain=&limit=&offset=` | 概念维检索（子串、大小写不敏感） |
| GET | `/by-problem?problem=...` | 问题维检索 |
| GET | `/by-method?method=...` | 方法维检索；沿 claim→evidence 边归并 |
| GET | `/by-evidence?evidence=<id 或 facet 值>` | 证据维检索；精确 id 直接命中对象 |
| GET | `/facets?dim=concept|problem|method|evidence&q=&field=` | 单维浏览：值 + 对象数 + 权重 |
| POST | `/index/rebuild` | 从 `ke_ko` 全量重建投影（写鉴权） |

响应统一含 `dim/value/total/items[]`；每个 item 带 `matched[]`（命中值 + 来源
field + 权重），claim 另带 `statement` 与 `snippet`。`log=true` 时把本次返回的
对象写成 `ke_usage` 的 `inject` 事件（`event_type=inject`，带 mission_id /
consumer），是 KPI 的分母来源。

**鉴权对齐平台**：写面沿用 Bearer（`KE_API_TOKEN`，未配置=503 而非开放）；读面
新增可选锁 `KE_REQUIRE_READ_AUTH=1`，token 取 `KE_READ_TOKEN`（回退
`KE_API_TOKEN`），未配置=503、token 错=401，与写面同构。默认不锁以兼容现网。

## 3. 一致性/可复算保证

- 创建/更新/删除在**同一事务**里维护 `ke_facet`；`ensure_schema` 对旧库做一次性
  回填（facet 表为空且 ke_ko 非空时重建），迁移零人工。
- 删除 draft 对象同时清 facet 与 usage，避免悬空计量。
- 所有查询 `ORDER BY id` + 分页，重跑逐字节可复现。

## 4. 局限（诚实声明）

- 分面是**检索投影**，不是真值断言：`problem` 来自 notes 是语料约定，换语料需
  重新审视频谱。
- 子串匹配对 CJK 依赖完整词/整句值；中文 bigram token 只到二元，`分辨率` 这类
  三字词需落在 notes 原文值里才能命中原句（测试覆盖了这一点）。
- 无向量语义检索：同义词（poiseuille/管道流）不自动互搜；需要时由生产者写
  `facets` 别名。

## 5. 验收与证据

- `tests/test_ke_index.py`：12 项（派生规则、显式覆盖、四端点、method 边归并、
  浏览、重建幂等、注入→引用 KPI、unknown cite 404、读鉴权开关）。
- `tests/test_ke_api.py`：25 项既有回归全绿（写鉴权/四状态机/六查询/并发）。
- 实证：`artifacts/tk-agent-cases/` 三案例全部 PASS，见
  `docs/ke/tp-worker-consumption.md` §4。
