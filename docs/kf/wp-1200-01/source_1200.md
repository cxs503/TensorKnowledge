# m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告

## ① 案例介绍（问题背景 / 对象 / 参数）
TensorPlatform `main` 自 dd66cb0c 起 control-plane job 连红，5 例 FAILED（非单 PR 引入），签名：

```
psycopg2.errors.UndefinedColumn: column "report_id" / "fail_stage"
of relation "tensor_dev_missions" does not exist
```

对象为 `tests/factory` 集成测试库（真实 PostgreSQL，临时集群，`tests/factory/conftest.py`）。失败签名点名的 8 个 schema 元素（本次审计的判据集）：

| # | 表.列 | 声明它的迁移 | 生产库 | 修复前测试库 |
|---|-------|--------------|--------|--------------|
| 1 | tensor_dev_missions.report_id | 096_report_gate.sql:12 | 有 | 缺 |
| 2 | tensor_dev_missions.report_owed | 096_report_gate.sql:8 / 095_mission_lifecycle.sql:38 | 有 | 缺 |
| 3 | tensor_dev_missions.fail_stage | 095_mission_lifecycle.sql:35 | 有 | 缺 |
| 4 | tensor_dev_missions.suspended_at | 095_mission_lifecycle.sql:19 | 有 | 缺 |
| 5 | tensor_dev_missions.worktree_recyclable | 095_mission_lifecycle.sql:41 | 有 | 缺 |
| 6 | tensor_dev_missions.budget_used | 095_mission_lifecycle.sql:30 | 有 | 缺 |
| 7 | campaign_plans.name | 095_campaign_plans.sql / 097 | 有 | 整表缺 |
| 8 | campaign_plans.campaign_id | 095_campaign_plans.sql / 097 | 有 | 整表缺 |

## ② 怎么做的（方法 / 流程 / 工具链）
1. 复现：本地起真实 PostgreSQL（无外网，用 `/tmp` 下**未入库**的 `pgserver` 替身，`initdb/pg_ctl` 以 postgres 用户在 unix socket 上起集群）+ `psycopg2`/`bcrypt` 兼容 shim，跑出与 CI 逐字相同的 `UndefinedColumn: report_id`。
2. 定根因（读代码 + `git log -S`，不猜）：`backend/services/factory_bootstrap.py` 用**手写文件名元组**（084 基线 + 086..093 + soul 094）喂测试库；生产侧 `backend/migrations/run_migration.py` 用 glob 全量 + 版本登记 → **生产有列、测试库没有**。手写元组引入于 2f7d2fe（2026-10-21），此后新增迁移从未回补：090_tensor_reports（PR #16，2ea470b）、095_mission_lifecycle（PR #223 agent/m597，1f5f711）、096_report_gate（966ea2e 并入 main），而 API 侧 tensor_missions.py（m641/PR #229，0e7686f）、tensor_mission_lifecycle.py（m597）已按正确 schema 读写这些列。
3. 选修复面：**补迁移通道，不改测试列名**（列名与模型/生产一致，改测试=把漂移固化成契约）。
   - `factory_bootstrap.factory_migration_files()`：glob `[0-9][0-9][0-9]_*.sql` 取编号 >84、按文件名序（与生产同序），删手写清单；`PRODUCTION_ONLY` 白名单强制写理由。
   - `097_campaign_plans_superset.sql`：补通道后暴露链上第二个断点——遗留 m611 列回填在全新库上 `column "title" does not exist`；改为 `information_schema.columns` 存在性判断的条件回填（遗留库行为逐字不变）。
   - 新增 `tests/factory/test_schema_migrations.py`（4 例）：迁移清单完整性 + 迁移声明列必须在测试库真实存在。
4. 证据采集脚本：`artifacts/m1625/probe_schema.py` 建两个一次性集群（before=修复前手写清单行为 / after=bootstrap），数字全部从 `information_schema` 读回，零手抄。

## ③ 计算结果
| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 应用到测试库的迁移文件数 | 9 | 19 |
| `public` schema 表数 | 15 | 43 |
| 签名 8 个 schema 元素缺失数 | 8 | 0 |
| `tests/factory` 结果 | 5 FAILED（report_id / fail_stage UndefinedColumn） | **168 passed**（34.3 s） |

## ④ 结果图
左：迁移文件应用数 9→19；右：CI 签名点名的列在测试库中的存在性（1=present）。数据源 `artifacts/m1625/schema_coverage.json`（probe_schema.py 程序化生成）。

## ⑤ 注意点 / 局限
- 094_factory_soul.sql 现经两条通道各执行一次（glob + soul 版本登记器），DDL 全 `IF NOT EXISTS` 且登记器幂等，实测无副作用，属已知冗余。
- 097 文件内的 `BEGIN; ... COMMIT;` 保留未动（外层事务下 PostgreSQL 仅告警，与生产行为一致）。
- `backend/tests` 抽样：test_abtest_unit/test_audit_unit/test_agent_routing/test_tensor_repro_redteam 全绿；test_alert_unit/test_api_key_unit 在净树上同样 FAILED（`'Depends' object has no attribute 'query'`，本地 FastAPI 0.136 依赖注入版本漂移，预存在）；test_auth_guard 缺 pytest-asyncio；24 模块因离线缺 redis 等包 collection ERROR——均为环境限制，非本改动引入。
- 未审计生产库 `schema_migrations` 登记与 `backend/migrations/versions/`（alembic 仅一个空壳 initial）的关系，留待平台审计项。
- 无外网 → CI 官方 `pgserver` 未在本地复现；用等价替身跑真实 PostgreSQL，DDL 路径一致。

## ⑥ 误差判定
本单判据为**二值一致性**，无可比标量基准：签名 schema 元素缺失数 8 → 0（等价误差 0/8 项 = 0%）；`tests/factory` 失败 5 → 0（等价误差 0%）。变异验证：把手写清单还原后新守护测试 3 failed 并逐列点名缺失列，证明门禁有效。因此「关键量是否 <3%」= **是（0%，且为离散一致性判据，不是连续物理量）**；连续量误差不适用，原因：本任务为 CI/schema 契约修复，不产生物理场量或标量基准。
