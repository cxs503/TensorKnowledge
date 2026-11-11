# KPI-KB-10K — 一万条治理知识对象（第 2 轮：调研结合）

**锚点**：`KPI-KB-10K`（总账判据：结构化知识样本 ≥ 10,000 条）
**交付**：`knowledge/kb10k/`（10,000 KO = 10,000 claim + 10,000 evidence + 10,000 provenance，31 个文件，18.3 MB）
**裁判**：`python scripts/kb10k_verify.py` → 10 项机器检查，`verdict=PASS`（见 `docs/kb10k/verification.json`）
**前轮**：m15123 在本锚点 honest-FAIL（未留 fail_stage/failure_reason）。本轮先调研再施工，并把
前轮死法写进排雷表（§6）。

---

## 1. 问题设定

`VISION.md` §6 把 KPI-KB-10K 定义为「10,000 条治理知识对象（Knowledge Object）」，并给出四条
硬性口径：四契约覆盖率（每条 KO ≥1 claim + ≥1 evidence + ≥1 provenance）、独立评审率、
溯源链完整度、KE 查询延迟。本轮只做**第一口径的规模达标**（其余三口径现状见 §5 与
`docs/kb10k/verification.json`，不虚报）。

手工撰写一万条 = 伪造。因此本轮的产出口径是：

> **每一条知识对象都是抽取的，不是编写的**——claim 语句由固定机器模板参数化生成，evidence
> 引文是源字节的**逐字连续切片**（钉 `content_hash` + 字符偏移），provenance 记录抽取活动与
> 生产 agent。

判据先于动手：10,000 条 KO × 四契约 ≥1:1:1，且每条 KO 的引文可被第三方从钉死的
`repo@commit` 逐字节复算。

## 2. 调研：方法谱系与开源横向

### 2.1 方法谱系（external_anchor，教科书/标准做法）

| # | 出处 | 借鉴的做法 | 落到本仓 |
|---|---|---|---|
| 1 | PROV-O, W3C Recommendation 2013-04-30 (https://www.w3.org/TR/prov-o/) | Entity / Activity / Agent 三元 + `wasGeneratedBy`/`used` 关系 | `provenance` 记录结构（`generated_entity` / `activity` / `agents`），沿用 `schemas/provenance-record.schema.json` |
| 2 | Groth, Gibson & Velterop, "The anatomy of a Nanopublication", *Information Services & Use* 30(1-2), 2010, doi:10.3233/ISU-2010-0613 | 断言 / 支撑 / 发布信息三件套，断言必须绑定可核对出处 | 每条 KO 强制 claim+evidence 捆绑，禁止裸断言入库 |
| 3 | Vrandečić & Krötzsch, "Wikidata: A Free Collaborative Knowledgebase", *CACM* 57(10), 2014, doi:10.1145/2629489 | statement + reference 模型（每陈述独立可引用） | evidence 一对一 supports 单 claim（本包 10,000 条 edge 全为 1:1） |
| 4 | Jaradeh et al., "Open Research Knowledge Graph", ISWC 2019, doi:10.1007/978-3-030-30796-7_21 | 论文级断言结构化、以引文锚定 | Tier B 文档段落 KO |
| 5 | JSON Schema 2020-12 (https://json-schema.org/draft/2020-12/) + 本仓 `schemas/*.schema.json` | 记录级机检 | C2 检查 30,000 条记录全量 schema 校验 |
| 6 | Python `ast` 模块（标准库）与 git object model（`git show commit:path`） | 静态符号抽取；以 commit 钉死整棵树 | Tier A 抽取 + C9 在线复算 |

### 2.2 开源横向（`oss_inventory` / 集群 `~/oss-cache`）

- 平台台账 `oss_inventory`（SQL 溯源：`SELECT repo,tier,focus FROM oss_inventory`）收录的是
  **求解器/数值内核**为主的仓库（ludwig、LUMA、HemoCell、openLB、lbm-principles…），**没有**
  同类"知识对象规模化"实现可直接抄结构；`oss_solutions` 226 行里也没有 `feature_slug` 命中
  `KPI-KB-10K` 的先例（本轮为其首条）。
- 集群 `~/oss-cache` 横向扫描作业 `cj993` 已递交（`run_cluster`，因队列 212 排队）；
  结论以台账查询为准：**没有**现成的 10k 级四契约知识库可直接借鉴，方法谱系（§2.1）是主参考。
- 结论：选型 = **自建抽取器 + 复用本仓既有四契约 schema/校验器**，不引入外部框架
  （避免新依赖、避免第二套契约——`ke/contract.py` 铁律"一种契约，两个后端"）。

## 3. 方法与实现（关键可复算点）

### 3.1 三层抽取（tier）

| tier | 源 | 一条 KO 对应 | 数量 |
|---|---|---|---|
| A | 生态 Python 源码（15 仓，`/root/tensor-ecosystem`） | 模块级**公开** class/def | 8,804 |
| B | 生态 Markdown 文档 | `## ` 小节（标题 + 首段逐字引文） | 850 |
| C | 平台治理表 | `negative_knowledge_ledger` 行 / `oss_solutions` 行（整行冻结） | 346 |

代码：`scripts/kb10k_harvest.py`（抽取 + 分片 + manifest）、`scripts/kb10k_verify.py`（裁判）、
`ke/validate.py: schema_report_records()`（聚合分片感知的 schema 校验，本轮新增）。

### 3.2 选择规则（为什么是 10,000 而不是 98,688）

实测生态公开模块级符号 **98,688** 个（15 仓，2026-11-11）——约 10 倍于 KPI。全量落库会产出
~140 MB 提交，且触碰推送门禁 4 MiB/文件上限。因此采用**确定性、跨仓均衡的 round-robin**
（每仓轮流取一条，直到配额），同输入重跑字节一致（`captured_at` 为固定任务日 2026-11-11，
不读墙钟）。配额：A 88%、B 8.5%、C 3.5%，B/C 未用满的余量全部回填 A，使总数**精确** 10,000。

### 3.3 零手抄与可复算

- `evidence.locator.quote` = 源字节连续切片（A/B 带 `start_offset`/`end_offset`）；Tier C 是
  冻结的 DB 行 JSON，**不伪造文件偏移**（本轮首跑此处误报 345 条，已修）。
- `evidence.locator.content_hash` = `sha256(quote)`。
- `evidence.source.persistent_id` = `git:<repo>@<full commit>:<path>` → 整棵树被 commit 钉死。
- claim 语句 = 模板 × 源字段（`scripts/kb10k_harvest.py:claim_statement`）。
- 敏感串防护：含 `password|token|api_key|private_key = "…"` 形态的候选切片整条丢弃；
  点文件（`.m8641_api.py` 类）不采。

### 3.4 诚实性

- 全部 claim 的 `epistemic_status = provisional`、evidence 的 `assessment_status = unassessed`：
  机器抽取尚未经独立评审，**不冒充 established**（`VISION.md` §7-3 禁止自批）。
- 不写 review-event：生产者不得评审自己（同上）。独立评审率口径本轮**未达标**，如实留白。

## 4. 结果（数字全部来自 `docs/kb10k/verification.json`）

| 检查 | 结果 |
|---|---|
| C1 四契约覆盖 | PASS — 10,000/10,000 每条 KO 齐 claim+evidence+provenance |
| C2 schema（30,000 条全量） | PASS — 0 失败 |
| C3 xref 不变量 I1-I5 | PASS — 0 悬挂引用 / 0 孤儿 evidence |
| C4 id 唯一 | PASS — 30,000/30,000 |
| C5 引文 hash+偏移 | PASS — 10,000/10,000 |
| C6 目标数 | PASS — 10,000 ≥ 10,000 |
| C7 推送预算 | PASS — 31 文件，最大 0.93 MiB |
| C8 manifest 对账 | PASS — 分片 sha256 全对 |
| C9 在线复算 | PASS — 9,602 条引文由 `git show <commit>:<path>` 逐字节复现，0 不符；52 条源文件不可解码（`errors="replace"` 后仍不可取），**未计入 PASS** |
| C10 折叠重复 | PASS — 0 |

KE 入库统计（`ke.queries.stats`）：claims 10,000 / evidence 10,000 / provenance 10,000 /
claim↔evidence 边 10,000 / 状态分布 {provisional: 10,000}。

## 5. 未完成与局限（不粉饰）

1. **独立评审率 0%**：本轮只做规模与可溯源性，review-event 需他单/他人产出。
2. **Tier C 无文件偏移**（DB 行非文件切片）；Tier C 引文为行 JSON 截断（≤1200 字符），完整行需回表。
3. **52 条在线复算不可用**：源文件解码失败（非 UTF-8 字节），已从 PASS 分母中剔除并计数。
4. **语义深度有限**：Tier A 是"符号存在性/位置"知识（definition 型），不是物理结论；
   物理结论仍走领域仓 → 四契约沉淀（如 `knowledge/sediment/*`）。
5. **查询延迟口径未测**：10k 规模下的 P95 见 `docs/kb10k/query-bench.json`（另单）。

## 6. 排雷（本轮踩到的坑，供后来者）

- **推送门禁**：`tp_pusher.py` `MAX_FILES=80`、`MAX_FILE=4 MiB`、丢弃 `artifacts/|runs/|*.png|*.log`。
  前轮多单"包在分支上但合并后为空"即死于按记录一文件（上万个文件）。→ 必须用**聚合分片**。
- **聚合分片 vs `ke.validate.schema_report`**：后者按「一文件一记录」glob `claims/*.json`，
  遇到 list 分片会整体判失败 → 本轮新增 `schema_report_records()`（按记录校验，同一套 schema）。
- **id 句点陷阱**：schema 的 id 模式只允许 `[a-z0-9-]`，源路径/符号名里的 `_`、`.` 必须 slug 化；
  Tier C 行键非数字时若用"伪行号"做去重键会**静默丢 KO**（本轮实测丢 34 条，已修）。
- **验证必须离线可跑**：外部仓在某台机器上可能不存在（前轮 0 检查执行）。C1-C8 纯本仓可跑，
  C9 才需要外部仓，且缺失时判 `NOT_RUN` 而非 `PASS`。
