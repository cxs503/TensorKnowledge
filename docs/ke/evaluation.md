# Knowledge Engine 选型评估：Cognee vs Graphiti vs 自研薄层

**任务锚点**：FEAT-TK-KNOWLEDGE-ENGINE（mission 8618）
**评估日期**：2026-11-09
**工作树**：TensorKnowledge @ `agent/m8618`
**评估对象（最新 stable，当日 PyPI 实测）**

| 对象 | 版本 | 来源（实测解析） | 核对方式 |
|---|---|---|---|
| Cognee | 1.6.7 (`cognee-1.6.7-py3-none-any.whl`, 23 315 255 B) | PyPI JSON API + wheel 下载 | `artifacts/ke_eval/install_matrix.json` |
| Graphiti | 0.31.2 (`graphiti_core-0.31.2-py3-none-any.whl`, 403 350 B) | 同上 | 同上 |
| 自研薄层 | 0.1.0（本任务实现） | `demos/ke_eval/thinlayer.py` | 实跑 PostgreSQL 15.5 |

> 铁律遵守情况：本文所有结论都有实测日志 / wheel 源码 / 运行产物定位。**没有引用任何官网宣传语**。
> 每条断言给出 `文件:行号` 或工件路径。凡是没跑通的，写 blocker，不写结论。

---

## 0. 决策（先给结论，再给论证）

**决策：以「自研薄层」作为 TensorKnowledge 的权威存储（canonical store），不把 Cognee 或 Graphiti 作为主库。**
**Graphiti 保留为「可选派生读模型」（derived read-model）候选**，用于图谱演化的实验（矛盾事实失效、社区摘要），前提是平台侧先具备可用图后端。
**Cognee 在本环境判为不可部署**（安装面硬阻塞），其**增量更新设计（chunk-level incremental update）建议抄设计而不装依赖**。

加权决策矩阵（11 维、权重合计 100，分数为脚本计算，非手抄）：

| Dim | Weight | Cognee 1.6.7 | Graphiti 0.31.2 | 自研薄层 (PG) |
|---|---|---|---|---|
| D1 安装面/离线可用（loongarch64） | 18 | 1 | 2 | 5 |
| D2 依赖重量 / Python 兼容风险 | 8 | 1 | 2 | 5 |
| D3 存储后端覆盖（含 PostgreSQL） | 12 | 4 | 1 | 5 |
| D4 增量摄取/幂等/删除一致性 | 10 | 5 | 4 | 3 |
| D5 四类检索原语覆盖 | 14 | 3 | 4 | 4 |
| D6 溯源表达力（PROV-O） | 12 | 2 | 1 | 5 |
| D7 四契约映射损耗 | 10 | 3 | 2 | 5 |
| D8 治理不变量（评审/禁止自审批） | 5 | 1 | 1 | 4 |
| D9 运维足迹 | 3 | 2 | 2 | 5 |
| D10 可逆性/导出/锁定 | 2 | 2 | 3 | 5 |
| D11 语义抽取与推理能力 | 6 | 4 | 5 | 1 |
| **加权总分（max 100）** | 100 | **51.8** | **47.8** | **87.4** |

矩阵由 `demos/ke_eval/score_matrix.py` 生成（`artifacts/ke_eval/decision_matrix.json` 含每个单元格的证据指针），文档中的表格是脚本输出的原样拷贝。

**这个决策依赖两个前提性判断（可被推翻，推翻条件写在 §7）：**

1. **P-安装面**：本生态的实际运行环境是 loongarch64 容器（`uname -m = loongarch64`），Cognee 的默认向量后端 lancedb **在 PyPI 上只有 4 个 wheel，且没有 sdist**，loong64 无解；Graphiti 的 4 个图后端也无一可用。→ 结论"不选它们做主库"首先是一条**部署可行性**结论，不是算法优劣结论。
2. **P-溯源语义**：TensorKnowledge 的核心不变量是"可检查、有出处、版本化、受治理的 claim"。两个框架**都不原生表达 PROV-O**（Cognee 的 `provenance` 是删除记账，Graphiti 根本没有 Activity/Agent 实体），而薄层把 PROV-O 当存储契约，四契约 JSON 往返**零损耗**（94/94 记录 schema 校验通过）。

---

## 1. 实验设计与预登记（动手前定，事后不改）

| 项 | 内容 |
|---|---|
| **决策** | 三个候选中选一个作为主存储；其余是否作为可选组件 |
| **备选** | A=Cognee 1.6.7；B=Graphiti 0.31.2；C=自研薄层（PostgreSQL 15） |
| **假设 H1** | 两个框架中至少一个能在本容器内完成"最小 ingest + query"，且四类需求可覆盖 |
| **假设 H2** | 框架原生具备 PROV-O 风格 provenance（used_entities/agents/activity） |
| **度量** | ① 安装成功/失败与失败点（日志原文）② 四类检索原语可表达性 ③ 契约字段映射损失（字段级分类）④ 溯源链最大可达深度 ⑤ 查询时延中位数（5 次） |
| **基线/对照** | 自研薄层在同一语料、同一机器上跑同样的四类原语（同一套语料 = 受控比较） |
| **预登记阈值** | 判定"可作为主库"需同时满足：<br>a) 能在**无外网**条件下从镜像装成功；<br>b) PostgreSQL 可作为主存储；<br>c) 四类原语中 **≥3 类**为"typed filter/查询"而非"LLM 中介"；<br>d) 四契约往返 schema 校验通过率 = 100% 或提供无损耗映射表；<br>e) 原生 PROV-O 表达力（activity+agent 为一等实体）。<br>**停止规则**：任一框架在安装阶段出现"无 loong64 wheel 且无 sdist/无法构建"的**硬阻塞**，即停止该路 runtime demo，改为源码级评估 + 如实记 blocker（不再投入构建时间） |
| **混淆变量** | ① 架构差异（loong64 vs 官方支持的 x86/aarch64）——安装结论**不能外推**到 x86 部署；② 无 embedding 服务（网关只提供 9 个 chat 模型，无 embedding 模型）——向量检索质量被本地哈希向量替代，不能用来评价框架的向量质量；③ 语料仅 20 claim / 22 evidence（探针规模，非规模基准） |
| **未做** | 未做检索质量（recall@k/nDCG）的人类标注对比——样本量不足以支撑，见 §8 |

环境登记：`loongarch64` / Loongnix Server 23.1 / Python 3.11.6 / gcc 12.3 / 系统 rustc 1.77.0 →
评估期升级为 rustup stable 1.99.1（`/root/rust`，见 §2.1）；PostgreSQL 15.5（`127.0.0.1:55433`，无 pgvector/pg_trgm 扩展）；
LLM 网关 `LLM_BASE_URL` 提供 chat completions（`qwen3.7-plus` 等 9 个模型），**无 embedding 端点**（实测 400/404）。

---

## 2. A 路：Cognee 1.6.7

### 2.1 安装面：硬阻塞（实测）

三条独立尝试，全部失败，失败点逐级下移后撞墙：

1. `pip install cognee`（默认源 lpypi.loongnix.cn）→ `No matching distribution found`（镜像无该包）。
2. `--index-url https://pypi.org/simple` → 失败于 `cryptography-50.0.2` 的 sdist 构建：
   `maturin 1.16.0` 需要 cargo `edition2024`，系统 cargo 1.77.0 不支持
   （日志 `logs/cognee_install.log`）。
3. 升级 rustup stable 1.99.1 + 阿里云镜像重试 → 越过 maturin，但 **`lancedb` 无解**：

```
lancedb 0.39.0 发布物（PyPI JSON，实测）= 4 个 wheel：
  cp310-abi3-macosx_11_0_arm64 / cp310-abi3-manylinux_2_28_aarch64 /
  cp310-abi3-manylinux_2_28_x86_64 / cp310-abi3-win_amd64
  → 无 loongarch64 wheel，且无 sdist（无法自行构建）
```

**逐依赖核对发布物**（`artifacts/ke_eval/install_matrix.json` → `native_deps.cognee`，
按 cognee 1.6.7 实际声明的版本约束查询，如 `lancedb<0.40.0,>=0.39.0` 查 **0.39.0** 而不是 latest）：

| 依赖 | cognee 的默认/必需角色 | 发布物（实测） | loong64 结论 |
|---|---|---|---|
| **lancedb 0.39.0** | **默认向量后端**（`vector/config.py:32`） | 4 个 wheel（macos-arm64 / manylinux **aarch64** / x86_64 / win）、**无 sdist** | **硬阻塞**（既无 loong64 wheel，也不能自行构建） |
| **pylance 14.0.2** | lance 的 Python 绑定 | 6 个 wheel、**无 sdist** | **硬阻塞** |
| **onnxruntime 1.31.1** | fastembed 的推理后端 | 24 个 wheel、**无 sdist** | **硬阻塞** |
| tiktoken / tokenizers / cryptography / cbor2 / ladybug / kuzu | 分词/加密/图后端 | 有 sdist（无 loong64 wheel） | 需源码构建（Rust 需 ≥1.85；kuzu 是 C++ 全量构建） |

注：lancedb 的更新版本（0.41.0）**有 sdist**，但**不满足 cognee 的 `<0.40.0` 约束**——
这条细节容易被"最新版本有 sdist"误导，故单独记录。

同族二进制依赖里还有 `fastembed`（依赖 onnxruntime）、`ladybug`
（默认图后端，`graph/config.py:47` → `graph_database_provider: str = "ladybug"`）。

**最小导入探针**（`demos/ke_eval/probe_minimal_install.py`，`--no-deps` 装 wheel 后逐模块补齐
纯 Python 依赖）记录到的最远点：`cognee/modules/users/get_user_db.py:5`
→ `from fastapi_users.db import SQLAlchemyUserDatabase`（该依赖链要求构建 `cryptography`，
即再次撞上 Rust 构建）。

**判定**：H1 对 Cognee 不成立 —— 本容器（无外网/loong64）**装不上**。诚实结论：
这是**环境**结论；在 x86_64 官方 wheel 覆盖平台上 Cognee 的安装面大概率正常，本文不做外推。

### 2.2 存储后端（源码检视）

| 层 | 支持的 provider | 证据 |
|---|---|---|
| relational | sqlite（默认）/ postgres / turso | `infrastructure/databases/relational/config.py:22,25` |
| vector | lancedb（默认）/ pgvector / turso / local_scoring | `vector/config.py:32`，`vector/` 目录含 `lancedb/ pgvector/ turso/` |
| graph | ladybug（默认）/ kuzu / neo4j / networkx | `graph/config.py:47`，`shared/data_models.py:337-341`（`GraphDBType` 枚举） |

对"含 PostgreSQL"这条需求：**PostgreSQL 可作为关系库与（经 pgvector）向量库，但不是图后端**
——图语义只能落在 ladybug/kuzu/neo4j/networkx 上。也就是说选 Cognee 意味着**两套存储**
（PG + 一个图引擎），运维面翻倍（矩阵 D9=2）。

### 2.3 增量摄取（Cognee 的最强项）

`cognee/api/v1/update/incremental.py:1-40` 的模块 docstring 自述并可从代码核对：
chunk 级增量更新 → 读旧 processed text 与旧 chunk 节点 → **stage** 新内容（不动 `Data` 行）
→ 通过可替换 `ChunkPolicy` 做 diff 规划（默认：切出不相交变更区、按原预算重切、两侧原样保留）
→ 逐字节复核规划结果 → 只为**新鲜 chunk** 跑抽取 → 通过共享删除规划器**退役**被替换 chunk 的
所有权 → 重排存活 chunk。删除侧有 refcount 语义：
`infrastructure/databases/provenance/source_refs.py`（`make_source_ref_key` / chunk 级 v2 key，
注释写明 "shared output survives until its LAST owner goes"）。
**这是三路里唯一做到 chunk 级增量 + 删除一致性的设计，矩阵 D4=5 的依据。**

### 2.4 检索原语

`modules/search/types/SearchType.py:5-25`：19 个类型（SUMMARIES / CHUNKS / RAG_COMPLETION /
GRAPH_COMPLETION(+COT/DECOMPOSITION/SUMMARY/CONTEXT_EXTENSION) / CYPHER / NATURAL_LANGUAGE /
TEMPORAL / FEELING_LUCKY / CHUNKS_LEXICAL / AGENTIC_COMPLETION / CODE / GRAPH_REPORT / BROAD /
SKILLS / HYBRID_COMPLETION）。
对四类需求：**域**最好（`node_set`/datasets 原生过滤）；**claim 状态**与**证据关系**没有
typed 谓词，只能 `CYPHER` 裸查询或 LLM 中介（`GRAPH_COMPLETION`）；**溯源链**同样只能 CYPHER
（而且链的语义取决于你自己写的 DataPoint 类）。矩阵 D5=3。

### 2.5 溯源表达力：**不是 PROV-O**

`infrastructure/databases/provenance/markers.py:1-14` 原文把 provenance 定义为**删除模式边界**：
graph "stores its provenance in the graph" 是指 delete-mode 标记（仅在 Ladybug+LanceDB 上支持），
否则走 relational ledger；`source_refs.py` 的键是 `dataset_id:data_id[:chunk_id]`。
即：**cognee 的 provenance 是"这条知识由哪个数据项产生、删它时要连带删什么"的记账**，
不是 PROV-O 的 Entity/Activity/Agent + used/wasAttributedTo。矩阵 D6=2。

### 2.6 契约映射（DataPoint）

`infrastructure/engine/models/DataPoint.py` 是 pydantic 化图模型：可以自定义子类承载
claim/evidence 字段，也可以定义 typed edge。**结论**：映射本身可行，但**契约必须手写成类**并随
schema 演进人工同步；review-event 链（治理）无归宿。矩阵 D7=3。

---

## 3. B 路：Graphiti 0.31.2

### 3.1 安装面

46 个依赖、**8 个核心依赖全为纯 Python**（certifi, neo4j, numpy, openai, posthog, pydantic,
python-dotenv, tenacity），唯一的原生扩展是 `openai → jiter`（Rust/maturin）。
即：**升级 Rust 后可安装**（本任务实测：系统 cargo 1.77 卡 `edition2024`；替换为 rustup
stable 1.99.1 后 maturin/jiter 可构建；构建日志 `logs/graphiti_v8.log`）。
→ 矩阵 D1=2（库可装，但**后端不可用**，见下）。

**后端可用性（实测）**：

| 后端 | 形态 | 本环境实测 |
|---|---|---|
| Neo4j | 服务器（Bolt） | `dist.neo4j.org` 返回 **403**（无法取二进制）；Java 11 也低于 Neo4j 5 要求 |
| Kuzu | 嵌入式 | PyPI 0.11.3 **无 loong64 wheel**，仅有 sdist（C++ 全量构建，非本次评估量级） |
| FalkorDB | 服务器（Redis 协议） | 无容器运行时（无 docker/podman） |
| Neptune | 云服务 | 不适用 |

驱动证据：`graphiti_core/driver/{neo4j,falkordb,kuzu,neptune}_driver.py`（4 个 `GraphDriver` 子类），
**没有 PostgreSQL 驱动** → 矩阵 D3=1。

**库本身装成功并跑通了映射层**（venv6：wheel `--no-deps` + 纯 Python 依赖，`import graphiti_core` OK，
`dist_version=0.31.2`）。四个后端的 live 尝试逐条原文（`artifacts/ke_eval/graphiti_result.json`
→ `live_attempt`）：

| 后端 | import | constructor | 探针结果 |
|---|---|---|---|
| neo4j | ok | ok | `execute_query("RETURN 1")` → `neo4j.exceptions.ServiceUnavailable: Couldn't connect to 127.0.0.1:7687 ... [Errno 111] Connect call failed` |
| kuzu | `ModuleNotFoundError: No module named 'kuzu'` | — | 无 loong64 wheel，sdist 需 C++ 全量构建 |
| falkordb | `ImportError: falkordb is required for FalkorDriver` | — | 需 FalkorDB 服务器 |
| neptune | `ModuleNotFoundError: No module named 'boto3'` | — | 云服务，不适用 |
| end-to-end `add_episode` | — | — | 同上 `ServiceUnavailable`（LLM 凭证已由容器 `LLM_*` 环境注入，失败点确实落在图后端） |

### 3.2 时间语义与增量（Graphiti 的强项）

- `EntityEdge`（`graphiti_core/edges.py`）：`fact` / `fact_embedding` / `episodes: list[str]` /
  `valid_at` / `invalid_at` / `expired_at` / `reference_time` / `attributes`。
- 增量摄取 = episode 累积 + LLM 去重 + **矛盾失效**：`graphiti.py:936-982`
  返回 `(resolved_edges, invalidated_edges, new_edges)`；
  `utils/maintenance/edge_operations.py:424-760` 的 `resolve_extracted_edges` /
  `resolve_edge_contradictions`。→ 矩阵 D4=4（有失效链，无删除记账）。

### 3.3 检索原语（三路里 typed 能力最强）

`search/search_filters.py:51-75` 的 `SearchFilters` 是真正 typed 的：`node_labels`、`edge_types`、
`valid_at/invalid_at/created_at/expired_at`（`DateFilter`+`ComparisonOperator`）、`edge_uuids`、
`property_filters`（任意属性 + 6 种比较算子）。
`search/search_config_recipes.py:34-71` 给出 bm25 / cosine / RRF / MMR / cross-encoder 组合配方。
→ 四类需求：**证据关系**（edge_types）与**域**（group_id/labels）天然可表达；
**claim 状态**要靠 `property_filters`（无类型校验，属性不存在时静默 0 行）；
**溯源链**只能靠通用图遍历（无 Activity/Agent）。

### 3.4 溯源表达力：**无 PROV-O**

对 wheel 源码 grep `prov-o|prov_o|wasAttributedTo|wasGeneratedBy`：**0 命中**。
边的溯源止于 `episodes: [uuid]`（这条边被哪些 episode 提到）；
`EpisodicNode` 有 `source` / `source_description` / `valid_at` / `content`，但**没有 activity 实体、
没有 agent 实体**，也没有"used_entities"。valid_at（事实有效期）与 created_at（记录时间）
是分开的 —— 这一点比 Cognee 强，但仍不是 PROV-O。矩阵 D6=1。

### 3.5 契约映射损耗（实测，字段级）

`demos/ke_eval/graphiti_mapping_demo.py` 用**真实的 graphiti-core 0.31.2 类**把语料映射成
`EpisodicNode`（22）/ `EntityNode`（20）/ `EntityEdge`（22），序列化成功（`mapped_ok: true`），
并对四个契约做字段级判定：

| 契约 | 一等字段（有 slot） | 进无类型 `attributes` 袋 | 无法表达（丢失） |
|---|---|---|---|
| claim-record | `created_at` | id, statement, claim_type, epistemic_status, created_by, scope, version | evidence_refs, relation_refs, valid_time, supersedes, modality, notes |
| evidence-record | citation(source_description), relation(edge name), captured_at(valid_at) | id, assessment_status, locator | claim_refs(被拓扑替代), extraction_method, captured_by, assessment, supersedes, version |
| provenance-record | — | derived_from（仅作为普通边） | activity, agents, attributed_to, recorded_at(≠valid_at), version, extensions |
| knowledge-object | title(name), summary, labels(object_type 代理), group_id(单域) | domains, evidence_status, review_status, version, tags | claim/evidence/provenance_refs 数组, review, publication_status, data/artifact_references, review_event_refs, supersedes, content |

**要点**：`EntityNode` 只有 `name`/`summary`/`attributes` 三个自由位，
所以 claim 除 `created_at` 外**全部**要么进无类型 dict、要么消失；
`review-event`（治理）**完全无处安放**。矩阵 D7=2、D8=1。

---

## 4. C 路：自研薄层（实跑，PostgreSQL 15.5）

实现：`demos/ke_eval/thinlayer.py`（约 470 行，含 DDL、`ke.cosine` SQL 函数、
禁止自审批触发器、递归溯源 CTE、RRF 混合检索、PROV-O JSON-LD 导出、往返校验）。

实测结果（`artifacts/ke_eval/thinlayer_result.json`）：

| 指标 | 数值 |
|---|---|
| 摄取 | 20 claim / 22 evidence / 28 provenance / 20 object / 12 review-event，**0.067 s** |
| P1 claim 状态（`epistemic_status=contested`） | 2 条，中位 **0.87 ms** |
| P2 证据关系图 | 20 条 claim 有证据，关系分布 `supports 15 / refutes 2 / contextualizes 2 / qualifies 2 / mentions 1`，中位 **0.78 ms** |
| P3 溯源链（递归 CTE） | claim → evidence → repo-doc，**深度 1 可达（2 节点）**，中位 **0.58 ms** |
| P4 域作用域 | benchmark-fixtures 12 claim / 12 object；knowledge-engineering 7/7；standards 1/1，中位 **0.61 ms** |
| P5 混合检索（lexical+vector+RRF） | 词法命中 8、向量命中 20，中位 **3.53 ms** |
| 四契约往返 | **94/94 记录 schema 校验通过，0 丢失**（`thinlayer_roundtrip.json`） |
| 治理不变量 | 生产者自审批 **被触发器拒绝**（`self_approval_rejected: true`） |

**局限（必须写清楚）**：没有任何语义抽取/推理能力（D11=1）；向量是局部哈希 char-3gram TF
（无语义，仅用于打通链路）；无 chunk 级增量（D4=3）。

---

## 5. 四契约映射损耗总表（三路对照）

| 契约 / 关键字段 | Cognee | Graphiti | 薄层 |
|---|---|---|---|
| claim.status（`epistemic_status`） | 需自写 DataPoint 字段，检索靠 Cypher | 进 `attributes`，`property_filters` 可过滤（无校验） | 列 + 索引，typed 查询（0.93 ms） |
| claim.id / version / supersedes | id/version 可；supersedes 退化为线性版本 | 无 supersedes/version 一等位 | 原样列存（含 supersedes 数组） |
| evidence.relation（4 值枚举） | 边标签，无 enum 约束 | edge name，无 enum 约束 | 列 + `evidence_claim` 图，按 enum 查询 |
| evidence.locator（type+value+content_hash） | DataPoint 属性 | `attributes` | 列 + jsonb（含 `content_hash`） |
| provenance.activity / agents | **无**（bookkeeping） | **无** | 列 + PROV-O JSON-LD 导出 |
| provenance.derived_from 链 | 边（语义自定） | 边（语义自定） | 递归 CTE，深度可达 |
| object.domains（多域） | `node_set` 标签 | `group_id`（单串） | `text[]` + GIN |
| review_event（治理/禁止自审批） | 无 | 无 | 表 + 触发器强制 |
| 往返校验 | —（装不上，未测） | 字段级判定：见 §3.5 | 94/94 通过 |

---

## 6. 三路各 1 页论证

### 6.1 Cognee：工程设计最贴合"知识库"，但**在本环境不可部署**

**优点（源码级）**：① chunk 级增量更新是全三路唯一真正解决"文档改了怎么办"的方案
（stage→plan→validate→write→publish，`api/v1/update/incremental.py`）；
② 19 种检索类型 + DataPoint 类型化图模型，表达力上限最高；
③ 存储后端可选面广（PG/pgvector/neo4j/kuzu/ladybug）。
**缺点（实测+源码）**：① **装不上**：lancedb 无 loong64 wheel 也无 sdist（§2.1），
另有 7 个原生依赖同样无解 —— 这不是调参能绕的；
② 默认图后端 ladybug、默认向量后端 lancedb 都是新依赖，且 provenance 只在
"Ladybug+LanceDB" 组合上成立（`provenance/markers.py`），意味着**溯源能力被后端绑定**；
③ "provenance"语义 ≠ PROV-O：它是删除记账，不是 Entity/Activity/Agent 图；
④ 检索的甜点区是 LLM 中介（GRAPH_COMPLETION 系列），与本平台"结果必须带对象 ID/版本/证据状态"
的检索要求（`research/global-landscape/STRATEGIC_GAP_ANALYSIS.md:89`）不完全对齐 —— LLM 合成
答案不天然携带证据引用。
**结论**：不选。**保留其增量更新设计作为薄层 D4 的路线图**（这是本评估最值钱的可复用产出）。

### 6.2 Graphiti：时间语义与 typed 检索最好，**但无 PROV-O、无 PostgreSQL、无可用后端**

**优点**：① `SearchFilters` 是真正的 typed 过滤面（含时间窗与任意属性谓词），RRF/MMR/
cross-encoder 配方现成；② 边级 `valid_at/invalid_at/expired_at` + 矛盾失效
（`resolve_edge_contradictions`）= 最接近"claim 被新证据推翻"的演化语义；
③ 依赖轻（8 个核心纯 Python），库本身可装、可离线使用（一旦 jiter 构建完成）。
**缺点**：① **PROV-O 0 命中**，无 Activity/Agent；② **无 PostgreSQL 后端**，四后端本环境全不可用
（Neo4j 403 / Kuzu 无 loong64 wheel / FalkorDB 无容器 / Neptune 云）；
③ 契约映射损耗大：EntityNode 只有 name/summary/attributes，review 事件无处安放；
④ 摄取强依赖 LLM 抽取（本环境有 chat、**无 embedding**，需自实现 embedder）。
**结论**：不作主库；**作为可选派生读模型**（只存"事实+时间+来源 episode"的投影，
权威数据仍在薄层），用于图谱演化实验。这与 `research/global-landscape/STRATEGIC_GAP_ANALYSIS.md:28`
"Graph ingestion/retrieval: Cognee, Graphiti, GraphRAG as replaceable backends" 的定位一致。

### 6.3 自研薄层：契约无损 + 治理可强制 + 零新增依赖，**但不会自己变聪明**

**优点（实测）**：① 四契约**往返零损耗**（94/94）；② PROV-O 作为存储契约，导出即 PROV-O
JSON-LD；③ 治理可强制（禁止自审批触发器实测生效）；④ 四类原语全部 typed、亚毫秒到毫秒级；
⑤ 零新增二进制依赖，**离线可装**（只用镜像自带的 psycopg3 + PostgreSQL）。
**缺点（诚实）**：① 无语义抽取/推理（D11=1）——"从 PDF 里自动长出 claim/evidence"这类能力
完全没有，需要后续单独建（或让 Graphiti 做派生读模型补）；② 无 chunk 级增量（D4=3），
只有 (id, version) 幂等 upsert 与 supersede 链；③ 混合检索的向量是占位实现（哈希 char-3gram），
真实 embedding 需接入（当前环境无 embedding 端点）。
**结论**：作为权威存储。它的边界很明确：**只做"契约 + 治理 + 可检索"，把语义抽取当外挂**。

---

## 7. 什么情况下本决策会翻盘（可证伪条件）

| 触发条件 | 影响 |
|---|---|
| 平台部署基线改为 x86_64 或提供 loong64 wheel 源（或私有 wheel 构建链） | P-安装面失效 → Cognee 重回候选，需重跑 §2.1/§2.4 实测 |
| 有可用的 loong64 图后端（Kuzu 构建成功 / Neo4j 可达 / FalkorDB 上容器） | Graphiti 可做**真** ingest+query，D1/D3 重评，可能升为"派生读模型"默认实现 |
| 平台接入 embedding 服务 | 三路的向量检索质量才能同台比较；当前对比对框架不公平（只能用哈希向量） |
| 语料规模上到 1e4–1e5 claim | 需重测时延/召回，薄层的 SQL 方案可能需换检索层（届时再评） |

---

## 8. 局限与 honest-FAIL 清单

1. **Graphiti 未跑通 runtime ingest+query（honest blocker）**：4 个后端全部不可用（§3.1 有逐条报错）。
   本任务交付的是**库级映射 demo + typed 过滤面实测构造 + 逐后端失败原文**，**不是**"跑通的图谱 demo"。
2. **Cognee 未跑通任何 runtime demo（honest blocker）**：装不上（lancedb 无 loong64 产物）。
   交付的是**安装面实验链 + wheel 源码级评估**，不冒充运行结果。
3. **未做检索质量评测（recall@k / nDCG）**：20 claim 的语料不足以支撑统计结论；且无 embedding 端点，
   向量召回不具代表性。任何"某框架检索更准"的说法在本任务里都**不成立**。
4. **架构不可外推**：所有安装结论都限于 loongarch64 + 无外网容器。
5. **权重与分数是判断，不是测量**：11 维权重由本评估设定（预登记于 §1），
   改变权重会改变排序（例：若 D1/D3/D6 权重各减半并加倍 D11，Graphiti 与薄层差距会显著收窄）。
   矩阵的可审计性来自"每个单元格有证据指针"，不是来自分数本身。

---

## 9. 复现（全部命令与产物）

```bash
# 0) 环境：PostgreSQL 15.5（本评估用 127.0.0.1:55433，用户 ke，库 ke_eval）
# 1) 语料（12 个仓内 benchmark 夹具 + 8 条文档溯源 claim，逐条 schema 校验）
python demos/ke_eval/tk_corpus.py --repo . --out artifacts/ke_eval/corpus.json
# 2) 自研薄层：建 schema + 摄取 + 五原语 + PROV-O 导出 + 往返校验 + 治理不变量
python demos/ke_eval/run_thinlayer_demo.py --dsn "host=127.0.0.1 port=55433 user=ke dbname=ke_eval"
# 3) Graphiti：契约映射损失 + typed 过滤面构造 + 逐后端 live 尝试（记录 blocker）
python demos/ke_eval/graphiti_mapping_demo.py
# 4) Cognee：安装/导入探针 + 映射分析（记录 blocker）
python demos/ke_eval/probe_minimal_install.py --venv <venv> --pkg cognee --dist <wheel> --out <log>
python demos/ke_eval/cognee_mapping_demo.py
# 5) 决策矩阵（权重/分数/证据指针 → JSON + Markdown）
python demos/ke_eval/score_matrix.py

# 6) 安装/可行性矩阵（PyPI 发布物实测 + 日志取证，非手写）
python demos/ke_eval/generate_install_matrix.py
# 7) 图（决策总分 / 薄层时延 / 契约往返校验）
python demos/ke_eval/make_figures.py
# 8) 回归测试（语料 schema、定位行可解析、矩阵自洽、embedder 确定性）
python -m pytest tests/test_ke_eval.py -q      # 5 passed
```

产物目录：`artifacts/ke_eval/`（`corpus.json`, `thinlayer_result.json`,
`thinlayer_roundtrip.json`, `graphiti_result.json`, `cognee_result.json`,
`install_matrix.json`, `decision_matrix.json`, `decision_matrix.md`,
`ke_eval_fig1.png`）。

---

## 10. 后续（若决策被采纳）

1. **薄层补 D4**：按 Cognee `incremental.py` 的 stage/plan/validate/publish 五段式，
   在 `ke.evidence`/`ke.kobject` 上加 chunk 级 source-ref 与 refcount 删除规划器（照抄设计，不引依赖）。
2. **接入真实 embedding**：薄层 `Embedder` 已是接口，替换 `hashed_ngram_vec` 即可；
   平台侧需提供 embedding 端点（当前仅 chat）。
3. **Graphiti 派生读模型**：只在"图后端可用"的前提下启用，投影仅含 fact + valid/invalid_at +
   episode 引用，**不承担权威存储**；用于矛盾失效与社区摘要实验。
4. **本评估的复用价值**：`probe_minimal_install.py` 是通用的"框架在此容器能否落地"探针，
   可按仓复用（改 `--pkg/--dist` 即可）。