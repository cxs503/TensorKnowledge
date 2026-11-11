# KE 存储后端路线：PostgreSQL 权威 + SQLite 测试夹具（m8800）

**锚点**：FEAT-TK-KNOWLEDGE-ENGINE —— KE 存储双轨收口
**外评定谳**：`docs/ke/evaluation.md` §0「决策：以**自研薄层**作为 TensorKnowledge
的权威存储（canonical store），不把 Cognee 或 Graphiti 作为主库」；薄层实测运行面即
PostgreSQL。因此本仓的权威路线 = **自研薄层 + PostgreSQL**。

## 0. 结论（三行）

1. **PG 是唯一权威存储**：生产/迁移/验收数据一律落在 PostgreSQL（psycopg 薄层，
   `ke/contract.py` 的同一份 DDL）。
2. **SQLite 只是单测 / 离线夹具**：同一个契约、同一套查询、同一个校验器，用于
   `:memory:` 级单测与无 PG 的离线环境，**不是第二套知识系统**。
3. **禁止第三种方言**：ORM、向量库直连、SQLite 生产部署、第二份手写 DDL 都不允许；
   新增后端 = 先在本文档登记差异清单并补双后端对拍测试，否则退回。

## 1. 代码结构（一套契约 / 一套查询 / 两个后端）

| 模块 | 职责 | 与后端的关系 |
|---|---|---|
| `ke/contract.py` | **数据契约唯一来源**：四契约的列定义、DDL 生成、源包发现（两种磁盘布局）、记录→行归一化、行级摘要 | 只用两端都接受的 SQL 子集（`TEXT` / `NOT NULL` / `PRIMARY KEY` / `CREATE TABLE IF NOT EXISTS` / `?` 占位符） |
| `ke/store.py` | **门面**：`connect()` 选后端；`Store` 做方言翻译（占位符 / `INSERT OR IGNORE` / 事务语义 / 行对象 / 排序排序规则 / 编码门） | `sqlite3` ↔ `psycopg` 的全部差异**只在这里** |
| `ke/queries.py` | 查询接口 Q1–Q6（+ Q7 gap 扩展） | 不含方言；排序与大小写语义用门面提供的原语固定 |
| `ke/validate.py` | schema 校验（jsonschema）+ xref 不变量 I1–I4（+ I5 gap） | 纯 SQL，两端一致 |
| `ke/migrate.py` | SQLite 暂存 → PG 迁移 + 对账表（对象数/关系数/断言数/行级摘要） | 源=sqlite，目标=pg |
| `ke/cli.py` | `ingest / query / validate / demo`，`--backend {sqlite,pg} --dsn --schema` | 两端共用同一命令 |

## 2. 数据契约（四个记录契约）

`knowledge/oss-lbm/` 里的四类记录，全部入表：

| 契约 | 表 | 主键 | 关键列 |
|---|---|---|---|
| claim-record | `claims` | `id` | `epistemic_status`、`scope_json`、`domain`、`evidence_refs_json`、`gap_anchors_json`、`raw_json` |
| evidence-record | `evidence` | `id` | `relation`、`assessment_status`、`source_*`、`locator_*`、`raw_json` |
| provenance-record | `provenance` | `id` | `generated_entity_id`、`activity_type`、`attributed_to_json`、`raw_json` |
| gap-anchor | `gap_anchors` | `id` | `title`、`declared_by`、`resolved_by_claims_json`、`raw_json` |
| 关系（连接表） | `claim_evidence` / `evidence_claims` / `gap_claims` | 复合主键 | 显示 xref 边；供 I1–I5 断言 |
| 元数据 | `ingest_meta` | `key` | 源包名、记录数、未归类文件、被折叠的重复发布 |

设计要点：

- **`raw_json` 零手抄**：每行保留入库原文（`sort_keys` 规范化），任何查询结果都能回溯到源字节。
- **载荷列一律 `TEXT`**：不引入 `JSONB`/numeric，避免两端在类型/精度/序列化上分叉；
  JSON 语义在应用层解析（`queries.raw_record`、`scope_json` 等）。
- **连接表不加外键（两端一致）**：解析不到的引用必须**存得进来**，否则
  `ke/validate.py` 的 xref 断言就成了空转（vacuous）。悬空引用由 I1–I5 报告，而不是由存储层拒绝。
- **聚合包去重**：`knowledge/oss-lbm` 的 `claims/claims.json` 是 roll-up，重复发布了
  `mflbm/claims.json` 的 10 条 claim。字节相同的重复按「排序路径先者胜」折叠并登记
  `ingest_meta.collapsed_duplicates`；**id 相同而内容不同 = 硬错误**（报错不静默取一）。

## 3. 连接与部署

### 3.1 连接串

```bash
# 默认（容器内 peer auth，无凭据入仓）
KE_PG_DSN='postgresql+psycopg:///tensorknowledge?host=/var/run/postgresql'
```

- 解析顺序：`--dsn` / 显式 `dsn=` > 环境变量 `KE_PG_DSN` > 内置默认值（同上）。
- `postgresql+psycopg://`（SQLAlchemy 风格）由门面归一为 `postgresql://` 再交给 psycopg。
- **任何凭据都不进代码、不进工件**：`ke/migrate.py:mask_dsn()` 会把口令打码后才写对账表。

### 3.2 容器内一次性引导（peer auth）

镜像默认没有 `root` 角色、也没有 KE 库，需要在宿主侧补一次（已在本机构建时执行）：

```bash
su postgres -c "psql -c \"CREATE ROLE root LOGIN CREATEDB\""
su postgres -c "createdb -E UTF8 -T template0 -O root tensorknowledge"
```

**UTF8 是硬性要求**：若库不是 UTF8（本镜像默认 `SQL_ASCII`），psycopg 对 `TEXT` 列返回
`bytes` 而不是 `str`，同一句 SQL 在两端会给出**不同类型**。`store.connect()` 因此带编码门：

```text
RuntimeError: KE requires a UTF8 PostgreSQL database, got server_encoding='SQL_ASCII'
             (...); create it with: createdb -E UTF8 -T template0 <db>
```

（实测教训：首轮双后端对拍 9 条红的直接原因就是库建成 `SQL_ASCII`。）

### 3.3 schema 隔离（测试用）

`connect(backend="pg", schema="ke_test_xxx", create_schema=True)` 会
`CREATE SCHEMA IF NOT EXISTS` + `SET search_path`，测试结束 `drop_schema()` 级联删除。
生产默认 schema 是 `ke`（`python -m ke.migrate` 默认值）。

## 4. 后端差异清单（全部已归一化）

| # | 差异 | SQLite | PostgreSQL | 归一化位置 |
|---|---|---|---|---|
| 1 | 参数占位符 | `?` | `%s`（pyformat，`%` 需转义） | `Store._sql()` |
| 2 | 冲突忽略 | `INSERT OR IGNORE` | `INSERT … ON CONFLICT DO NOTHING` | `Store._sql()` |
| 3 | `with conn:` 语义 | 只提交，连接保持打开 | **会关闭连接** | `Store.__enter__/__exit__`（显式 commit/rollback） |
| 4 | 行对象 | `sqlite3.Row`（int+name 下标） | `dict_row`（仅 name） | `KeRow`（两种下标都支持） |
| 5 | 多语句 DDL | `executescript()` | 逐条 `execute()` | `Store.scripts()` |
| 6 | 字符串编码 | 始终 `str` | 非 UTF8 库返回 `bytes` | 编码门（§3.2），失败即报错 |
| 7 | 排序规则 | `BINARY`（字节序） | 库 locale（`en_US.UTF-8` 忽略标点） | `Store.collate()` → `COLLATE "C"` / `COLLATE BINARY`；摘要改为**行哈希在 Python 侧排序**，不依赖 DB 排序 |
| 8 | `LIKE` 大小写 | ASCII 不敏感 | **敏感** | 查询层统一 `LOWER(col) LIKE LOWER(?)` |
| 9 | `SELECT DISTINCT` + `ORDER BY` | 允许 | 报错（ORDER BY 表达式必须在 select list） | 连接表有复合主键，去掉冗余 `DISTINCT` |
| 10 | 表存在性/DDL 幂等 | `CREATE TABLE IF NOT EXISTS` | 同（PG 9.1+ 支持） | 契约 DDL 两端共用 |

**不允许**的差异：上述之外的任何行为差异都算缺陷 —— `tests/` 的双后端参数化对拍
（同一组断言跑两遍）+ `ke/migrate.py` 的逐表行级摘要（sha256）就是发现它的手段。

## 5. 迁移：SQLite 暂存 → PostgreSQL 权威

```bash
# 全量迁移 knowledge/oss-lbm 的四契约数据（默认 schema ke）
python -m ke.migrate
# 只对账、不写库
python -m ke.migrate --check
# 迁移一份已存在的 SQLite KE 库
python -m ke.migrate --source-db /path/to/ke.db
```

- **幂等**：单事务内先 `DELETE` 再全量 `INSERT`，重跑收敛到同一状态（实测连跑两次
  摘要不变，`--check` 仍 PASS）。
- **对账表**：`docs/ke/migration-reconcile.json`（机器判定）+
  `docs/ke/migration-reconcile.md`（人读）。放在 `docs/` 而不是 `artifacts/`，
  是因为推送门禁把 `artifacts/**` 判为运行记录而滤除（见 `docs/ops/filter-audit.md`）。字段含义：
  - `objects.*`：四契约逐表行数 + 行级 sha256（**不是**只比行数）；
  - `relations.*`：三张连接表的边数与摘要；
  - `assertions.*`：xref 不变量 I1–I5 的违例数（源 vs 目标）与 `stats` 分布是否一致；
  - `totals`：对象数 / 关系数 / 断言违例数合计；`verdict`：全部一致才 `PASS`，CLI 退出码同步。
- **本次实跑（2026-11-10）**：对象数 257 → 257（claims 102、evidence 142、provenance 7、
  gap anchors 6）；关系数 327 → 327（150 / 150 / 27）；摘要逐表一致；`verdict=PASS`。
- **已知数据缺口（如实登记，不是迁移失败）**：`GAP-LBM-HPC-SCALING` 被 10 条 mflbm claim
  在 `gap_anchors` 字段引用，但该 gap anchor 未在本包内定义 → I5 报 10 条悬空引用，
  源/目标**同为 10**（parity 成立）。修法在数据侧（补 gap anchor 定义或改引用），不在存储层。

## 6. 测试与 CI

| 项 | 内容 |
|---|---|
| 原型对拍 | `tests/test_ke_proto.py`：15 个原型测试 × 2 后端（`conn` / `backend` 夹具参数化） |
| 迁移对拍 | `tests/test_ke_migrate.py`：10 个测试（清单钉死、重复折叠、冲突拒绝、逐表摘要、幂等、六类查询跨后端 parity、CLI 工件、DSN 打码） |
| 夹具 | `tests/fixtures/ke-pilot/`：m8554 试点包（`ba59c4e` 字节级拷贝，附 `PROVENANCE.md`） |
| 无 PG 环境 | 默认 skip（`KE_PG_REQUIRE` 未设）；**CI 设 `KE_PG_REQUIRE=1`**，PG 消失即红，杜绝「静默跳过=假绿」 |
| CI | `.github/workflows/ke-backends.yml`：postgres:16 service → `python -m ke.migrate`（对账门）→ 双后端 pytest → 既有知识资产校验器 |

## 7. 非目标（明确不做）

- 不做 SQLite→生产的双写 / 复制 / 事件溯源；SQLite 只在测试与离线夹具里存在。
- 不做 ORM（等价于引入第三套方言与第三份 DDL）。
- 不把 `JSONB`、`pgvector`、全文索引塞进契约（当前四契约无此需求；要加须先补差异清单与对拍）。
- 不在本仓承载领域语义（KE 只存/查/校验记录，域内容来自 `knowledge/**` 工件）。