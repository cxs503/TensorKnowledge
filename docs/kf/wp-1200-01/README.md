# wp-1200-01 · 01-asset-registration（report_id=1200）

> 结果信封在文末唯一的 JSON 代码块中（平台门按 kf_result.v1 校验）。
> 本工序只登记资产，不做抽取、不判 verified。

## ① 本工序做了什么（对象 / 输入参数表）

对报告 1200 做**资产登记**：确认 report_id 与其 markdown 的字节哈希，列出报告中可定位的
附件/工件与判据元素，不做知识抽取、不改写上游产物、不标 verified。

| 字段 | 值 | 来源 |
|---|---|---|
| package_id / task_type | `wp-1200-01` / `01-asset-registration` | 契约 |
| report_id | `1200` | 契约 / API |
| source_uri · field | `tensor://reports/1200` · `markdown` | 契约 |
| 报告标题（原文 L1） | m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告 | 源 markdown |
| scenario_key | `tensorplatform_ci_quality` | API 记录 |
| chars / bytes / 行数 | 3612 / 5396 / 53 | 程序化计算 |
| sha256 | `sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48` | 程序化重算，与契约一致=True |
| 取得方式 | GET http://127.0.0.1:8010/api/v1/tensor/reports/1200 (Bearer auth) | — |

## ② 怎么做的（方法 / 工具链 / 关键设置）

1. 取源：`GET /api/v1/tensor/reports/1200`（Bearer，`$TENSOR_API_BASE`），只读 `markdown` 字段；
   不做任何其它 report_id 的读写（互不覆盖）。
2. 哈希门：对 markdown 的 UTF-8 字节重算 sha256，与契约 `sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48` 比对；
   不一致即**拒绝登记并退出**（不硬改、不补写）。
3. 零手抄定位：所有 `quote` 都是对 markdown 的**行区间切片**（`md[char_start:char_end]`），
   行号由 `char_start` 反算；工件再叠加 `anchor`（路径 token 的逐字切片）定位到行内。任何片段
   定位不到/不唯一即报错退出 —— 从机制上排除"凭记忆重述"。
4. 结构门：信封按 `schemas/kf_result.v1.schema.json`（draft 2020-12）用 `jsonschema` 校验。
5. 独立复核：`verify_asset_manifest.py` **重新**从 API 取源、重算哈希、重判每条 locator/claim，
   不引用生成脚本的内部常量，输出机读 `validation_report.json`。
6. 守护测试：`tests/test_kf_wp_1200_01_asset_manifest.py` 断言不变量 + 5 个变异用例
   （篡改 quote / 错位行号 / 重复 id / 抹掉 unresolved_reason / 非逐字 claim 引文）。
7. 交付路径：本仓 `artifacts/` 被 `.gitignore` 屏蔽（推送门会丢），故交付物物化在
   `docs/kf/wp-1200-01/`、脚本在 `scripts/kf/wp-1200-01/` —— 不依赖未入库路径。

repro_cmd（一键复跑，工作树根执行）：

```bash
# 1) 重建清单 + 自校验（需 $TENSOR_API_BASE / $TENSOR_AGENT_USER / $TENSOR_AGENT_PASS）
python3 scripts/kf/wp-1200-01/build_asset_manifest.py
# 2) 独立复核（重新取源、重算哈希与全部 locator）
python3 scripts/kf/wp-1200-01/verify_asset_manifest.py
# 3) 守护测试（离线；含变异验证）
python3 -m pytest tests/test_kf_wp_1200_01_asset_manifest.py -q
```

## ③ 产出物清单（输出文件 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-1200-01/asset_manifest.json` | 登记主体：源资产（3612 chars / sha256 一致）+ 8 个附件 + 8 个判据 schema 元素 + 4 条结果指标定位 + 10 条 claim |
| `docs/kf/wp-1200-01/result_envelope.json` | kf_result.v1 信封（package_id/task_type/report_id/provenance/outputs/claims），outputs 内嵌 manifest |
| `docs/kf/wp-1200-01/validation_report.json` | 10 项判据机读结果（PASS 10 / FAIL 0），含被检 locator 数 21 与 schema 自身哈希 |
| `docs/kf/wp-1200-01/source_1200.md` | 源 markdown 逐字副本（复跑/复核用，自带 sha256 记录） |
| `docs/kf/wp-1200-01/source_1200.sha256` | `sha256sum` 格式校验记录 |
| `scripts/kf/wp-1200-01/build_asset_manifest.py` | 清单生成器（哈希门 + 切片定位 + 结构门 + 自校验，非零退出=fail） |
| `scripts/kf/wp-1200-01/verify_asset_manifest.py` | 独立复核器（不依赖生成器内部定义） |
| `tests/test_kf_wp_1200_01_asset_manifest.py` | 12 例守护测试（7 不变量 + 5 变异） |

统计（`asset_manifest.json:stats`）：claims 10 = supported 8
/ partially-supported 1 / unresolved 1
/ refuted 0；附件可解析数 0/8
（其余见 ⑤ 的未决说明）。

## ④ 证据定位表（claim/字段 → 原文引文片段，行号可 machine-resolve）

登记判据 schema 元素（源报告表格逐行，L=markdown 行号）：

| ref_id | 表.列 | 声明迁移 | 生产 / 修复前测试库 | L |
|---|---|---|---|---|
| schema-elem-01 | `tensor_dev_missions.report_id` | `096_report_gate.sql:12` | present / missing | L15 |
| schema-elem-02 | `tensor_dev_missions.report_owed` | `096_report_gate.sql:8 / 095_mission_lifecycle.sql:38` | present / missing | L16 |
| schema-elem-03 | `tensor_dev_missions.fail_stage` | `095_mission_lifecycle.sql:35` | present / missing | L17 |
| schema-elem-04 | `tensor_dev_missions.suspended_at` | `095_mission_lifecycle.sql:19` | present / missing | L18 |
| schema-elem-05 | `tensor_dev_missions.worktree_recyclable` | `095_mission_lifecycle.sql:41` | present / missing | L19 |
| schema-elem-06 | `tensor_dev_missions.budget_used` | `095_mission_lifecycle.sql:30` | present / missing | L20 |
| schema-elem-07 | `campaign_plans.name` | `095_campaign_plans.sql / 097` | present / missing | L21 |
| schema-elem-08 | `campaign_plans.campaign_id` | `095_campaign_plans.sql / 097` | present / missing | L22 |

结果指标定位（源报告 ③ 结果表逐行）：

| metric_id | 原文行 | L |
|---|---|---|
| mig_files | \| 应用到测试库的迁移文件数 \| 9 \| 19 \| | L36 |
| tables | \| `public` schema 表数 \| 15 \| 43 \| | L37 |
| missing_cols | \| 签名 8 个 schema 元素缺失数 \| 8 \| 0 \| | L38 |
| factory_tests | \| `tests/factory` 结果 \| 5 FAILED（report_id / fail_stage UndefinedColumn） \| **168 passed**（34.3 s） \| | L39 |

附件/工件登记（`anchor` = 该行内的路径 token 逐字切片）：

| asset_id | kind | 路径 | L | 可解析性 |
|---|---|---|---|---|
| `art-01` | test file | `tests/factory/conftest.py` | L11 | unknown/unresolved |
| `art-02` | source module | `backend/services/factory_bootstrap.py` | L26 | unknown/unresolved |
| `art-03` | source module | `backend/migrations/run_migration.py` | L26 | unknown/unresolved |
| `art-04` | migration sql | `097_campaign_plans_superset.sql` | L29 | unknown/unresolved |
| `art-05` | test file | `tests/factory/test_schema_migrations.py` | L30 | unknown/unresolved |
| `art-06` | evidence script | `artifacts/m1625/probe_schema.py` | L31 | unknown/unresolved |
| `art-07` | data artifact | `artifacts/m1625/schema_coverage.json` | L42 | unknown/unresolved |
| `art-08` | migration sql | `094_factory_soul.sql` | L45 | unknown/unresolved |

claims → 原文引文（完整引文在 `asset_manifest.json` 的 `evidence[].quote`，此处截断展示 ≤300 字符）：

| claim_id | status | 源行 | 引文（截断） |
|---|---|---|---|
| `wp-1200-01-c01` | supported | L4 | TensorPlatform `main` 自 dd66cb0c 起 control-plane job 连红，5 例 FAILED（非单 PR 引入），签名： |
| `wp-1200-01-c02` | supported | L7 | psycopg2.errors.UndefinedColumn: column "report_id" / "fail_stage" |
| `wp-1200-01-c02` | supported | L8 | of relation "tensor_dev_missions" does not exist |
| `wp-1200-01-c03` | supported | L11 | 对象为 `tests/factory` 集成测试库（真实 PostgreSQL，临时集群，`tests/factory/conftest.py`）。失败签名点名的 8 个 schema 元素（本次审计的判据集）： |
| `wp-1200-01-c03` | supported | L15 | \| 1 \| tensor_dev_missions.report_id \| 096_report_gate.sql:12 \| 有 \| 缺 \| |
| `wp-1200-01-c03` | supported | L16 | \| 2 \| tensor_dev_missions.report_owed \| 096_report_gate.sql:8 / 095_mission_lifecycle.sql:38 \| 有 \| 缺 \| |
| `wp-1200-01-c03` | supported | L17 | \| 3 \| tensor_dev_missions.fail_stage \| 095_mission_lifecycle.sql:35 \| 有 \| 缺 \| |
| `wp-1200-01-c03` | supported | L18 | \| 4 \| tensor_dev_missions.suspended_at \| 095_mission_lifecycle.sql:19 \| 有 \| 缺 \| |
| `wp-1200-01-c03` | supported | L19 | \| 5 \| tensor_dev_missions.worktree_recyclable \| 095_mission_lifecycle.sql:41 \| 有 \| 缺 \| |
| `wp-1200-01-c03` | supported | L20 | \| 6 \| tensor_dev_missions.budget_used \| 095_mission_lifecycle.sql:30 \| 有 \| 缺 \| |
| `wp-1200-01-c03` | supported | L21 | \| 7 \| campaign_plans.name \| 095_campaign_plans.sql / 097 \| 有 \| 整表缺 \| |
| `wp-1200-01-c03` | supported | L22 | \| 8 \| campaign_plans.campaign_id \| 095_campaign_plans.sql / 097 \| 有 \| 整表缺 \| |
| `wp-1200-01-c04` | supported | L26 | 2. 定根因（读代码 + `git log -S`，不猜）：`backend/services/factory_bootstrap.py` 用**手写文件名元组**（084 基线 + 086..093 + soul 094）喂测试库；生产侧 `backend/migrations/run_migration.py` 用 glob 全量 + 版本登记 → **生产有列、测试库没有**。手写元组引入于 2f7d2fe（2026-10-21），此后新增迁移从未回补：090_tensor_reports（PR #16，2ea470b）、095_mission_lifecycle（PR #223 age |
| `wp-1200-01-c05` | supported | L36 | \| 应用到测试库的迁移文件数 \| 9 \| 19 \| |
| `wp-1200-01-c05` | supported | L37 | \| `public` schema 表数 \| 15 \| 43 \| |
| `wp-1200-01-c05` | supported | L38 | \| 签名 8 个 schema 元素缺失数 \| 8 \| 0 \| |
| `wp-1200-01-c05` | supported | L39 | \| `tests/factory` 结果 \| 5 FAILED（report_id / fail_stage UndefinedColumn） \| **168 passed**（34.3 s） \| |
| `wp-1200-01-c06` | supported | L30 |    - 新增 `tests/factory/test_schema_migrations.py`（4 例）：迁移清单完整性 + 迁移声明列必须在测试库真实存在。 |
| `wp-1200-01-c07` | supported | L45 | - 094_factory_soul.sql 现经两条通道各执行一次（glob + soul 版本登记器），DDL 全 `IF NOT EXISTS` 且登记器幂等，实测无副作用，属已知冗余。 |
| `wp-1200-01-c08` | partially-supported | L47 | - `backend/tests` 抽样：test_abtest_unit/test_audit_unit/test_agent_routing/test_tensor_repro_redteam 全绿；test_alert_unit/test_api_key_unit 在净树上同样 FAILED（`'Depends' object has no attribute 'query'`，本地 FastAPI 0.136 依赖注入版本漂移，预存在）；test_auth_guard 缺 pytest-asyncio；24 模块因离线缺 redis 等包 collection ERROR——均为环境限 |
| `wp-1200-01-c09` | supported | L52 | 本单判据为**二值一致性**，无可比标量基准：签名 schema 元素缺失数 8 → 0（等价误差 0/8 项 = 0%）；`tests/factory` 失败 5 → 0（等价误差 0%）。变异验证：把手写清单还原后新守护测试 3 failed 并逐列点名缺失列，证明门禁有效。因此「关键量是否 <3%」= **是（0%，且为离散一致性判据，不是连续物理量）**；连续量误差不适用，原因：本任务为 CI/schema 契约修复，不产生物理场量或标量基准。 |
| `wp-1200-01-c10` | unresolved | L48 | - 未审计生产库 `schema_migrations` 登记与 `backend/migrations/versions/`（alembic 仅一个空壳 initial）的关系，留待平台审计项。 |

## ⑤ 注意点与局限（含独立性与未跑项）

- **独立性限制**：生成器与复核器由同一执行者写就；`verify_asset_manifest.py` 只吃交付物+重取源，
  不复用生成器常量，但仍非第三方独立复核（`review.required=false`，本工序不自评 verified）。
- **未跑项（记 unknown，不记 pass）**：8 个附件的存在性/内容未跨仓取证（路径属 TensorPlatform 仓，
  本工作树是 TensorKnowledge），故 `resolvable=false / status=unknown`；未运行上游
  `tests/factory` 的 168 passed，也未复核 CI 历史 5 FAILED。
- `wp-1200-01-c08` 记为 **partially-supported**：报告自述 `test_alert_unit`/`test_api_key_unit`
  失败为预存在，但未附逐例日志，本工序无法独立确认该归因。
- `wp-1200-01-c10` 记 **unresolved**：报告声明"生产库 `schema_migrations` 登记与 alembic 版本目录
  关系未审计"，本工序保持未决，不得据本报告推定已闭合。
- 机械冗余：源报告 094 迁移经两条通道执行（报告自述幂等无副作用），本工序只登记不评判。
- 交付路径注意：`artifacts/` 在本仓被 `.gitignore` 屏蔽，若写在该处则平台推送时丢失，故落 `docs/`。
- 边界：全程只读 `report_id=1200`；未写其它 report_id；未改上游产物；未标 verified。

## ⑥ 自检（逐条对照 acceptance）+ 误差判定

acceptance：

| 判据 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 两 JSON 解析成功 |
| schema_pass | ✅ | jsonschema 对 kf_result.v1 通过 |
| source_locator_resolvable | ✅ | 21 个 locator 逐字切片且行号自洽 + 工件 anchor 行内命中 |
| source_hash_matches | ✅ | 重算 = 契约 = sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48 |
| no_duplicate_ids | ✅ | 全域 id 唯一；信封 claims 与 manifest 一致 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | 10 条 claim 均带 quote 证据或显式 unresolved_reason |

附加自检（超出契约、本工序自加）：`artifact_anchor_in_locator` / `claim_quotes_verbatim` /
`no_verified_marking` / `report_id_scope`，机读结果见下：

| check | result | detail |
|---|---|---|
| `valid_json` | PASS | manifest/envelope 均可被 json 解析（本函数入参即解析结果） |
| `schema_pass` | PASS | jsonschema(draft2020-12) 对 kf_result.v1.schema.json 校验通过 |
| `source_hash_matches` | PASS | sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48 |
| `artifact_anchor_in_locator` | PASS | 8 个工件路径 token 均逐字落在其引用行内 |
| `source_locator_resolvable` | PASS | 21 个 locator 全部为逐字切片且行号自洽 |
| `no_duplicate_ids` | PASS | 10 个 claim_id 唯一 |
| `all_claims_have_evidence_or_explicit_unresolved_status` | PASS | 10 条 claim 均有 quote 证据或显式 unresolved_reason |
| `claim_quotes_verbatim` | PASS | 全部 quote ⊆ markdown |
| `no_verified_marking` | PASS | envelope 内无 verified:true；verification 由平台门计算 |
| `report_id_scope` | PASS | 仅 report_id=1200；未读写其它 report |

pytest：`python3 -m pytest tests/test_kf_wp_1200_01_asset_manifest.py -q` → **12 passed**（含 5 个变异用例：
篡改引文/错位行号/重复 id/缺失 unresolved_reason/非逐字引文 均被检出，证明判据有牙而非"跑过即绿"）。

误差判定（是否 <3%）：**是，0%** —— 本工序判据全部为**离散一致性**
（sha256 逐字节一致、quote 逐字子串、id 唯一性、claim 证据完备性），无连续量、无物理基准，
因此"<3% 线"以 0 偏差满足；连续量误差**不适用**，原因：资产登记工序不产生场量或标量基准
（图中亦无对比曲线可给，见下）。全部 10 项判据 PASS，无 honest-FAIL 项。

结果图：**无图**。理由：本工序是元数据/哈希登记，输入输出均为文本与 JSON，没有场量云图，也没有
可与解析解/文献比较的标量曲线；画图只会是装饰性内容，故以机读 `validation_report.json` 替代图。
（上游报告 1200 的图数据源 `artifacts/m1625/schema_coverage.json` 已在附件表中登记为外部工件。）

## 结果信封（唯一 JSON 代码块）

```json
{
  "package_id": "wp-1200-01",
  "task_type": "01-asset-registration",
  "report_id": "1200",
  "provenance": {
    "source_hash": "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48",
    "source_field": "markdown",
    "producer": "agent m15523 / wp-1200-01 (TensorKnowledge)",
    "emitted_at": "2026-11-12T00:54:56+00:00",
    "notes": "asset registration only; quotes are programmatic line-slices of the source markdown; no extraction, no verification marking"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-1200-01",
      "task_type": "01-asset-registration",
      "source": {
        "asset_id": "asset-report-1200",
        "report_id": "1200",
        "source_uri": "tensor://reports/1200",
        "source_field": "markdown",
        "title": "m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告",
        "title_locator": {
          "line_start": 1,
          "line_end": 1,
          "char_start": 0,
          "char_end": 67,
          "quote": "# m1625 — tests/factory schema 漂移（main CI control-plane job 连红）修复报告"
        },
        "scenario_key": "tensorplatform_ci_quality",
        "chars": 3612,
        "bytes": 5396,
        "line_count": 53,
        "sha256": "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48",
        "sha256_expected": "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48",
        "sha256_match": true,
        "encoding": "utf-8",
        "locator_scheme": "1-based 行号 + 字符偏移（对 markdown 字段原样切片）；quote 字段=该切片逐字内容，可直接做子串检索复核",
        "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/1200 (Bearer auth)"
      },
      "attachments": [
        {
          "asset_id": "art-01",
          "kind": "test file",
          "ref": "tests/factory/conftest.py",
          "purpose_in_report": "tests/factory 集成测试库 conftest（真实 PostgreSQL 临时集群）",
          "mentioned_at": [
            {
              "line_start": 11,
              "line_end": 11,
              "char_start": 302,
              "char_end": 408,
              "quote": "对象为 `tests/factory` 集成测试库（真实 PostgreSQL，临时集群，`tests/factory/conftest.py`）。失败签名点名的 8 个 schema 元素（本次审计的判据集）：",
              "anchor_char_start": 348,
              "anchor_char_end": 373,
              "anchor_text": "tests/factory/conftest.py",
              "anchor_line": 11
            }
          ],
          "resolvable": false,
          "resolvable_status": "unknown/unresolved",
          "unresolved_reason": "该工件路径属 TensorPlatform 仓（本工作树为 TensorKnowledge），报告仅文字引用、未附内容；本工序不跨仓取证，故可解析性记为未验证"
        },
        {
          "asset_id": "art-02",
          "kind": "source module",
          "ref": "backend/services/factory_bootstrap.py",
          "purpose_in_report": "测试库迁移喂养实现（手写文件名元组）",
          "mentioned_at": [
            {
              "line_start": 26,
              "line_end": 26,
              "char_start": 1349,
              "char_end": 1799,
              "quote": "2. 定根因（读代码 + `git log -S`，不猜）：`backend/services/factory_bootstrap.py` 用**手写文件名元组**（084 基线 + 086..093 + soul 094）喂测试库；生产侧 `backend/migrations/run_migration.py` 用 glob 全量 + 版本登记 → **生产有列、测试库没有**。手写元组引入于 2f7d2fe（2026-10-21），此后新增迁移从未回补：090_tensor_reports（PR #16，2ea470b）、095_mission_lifecycle（PR #223 agent/m597，1f5f711）、096_report_gate（966ea2e 并入 main），而 API 侧 tensor_missions.py（m641/PR #229，0e7686f）、tensor_mission_lifecycle.py（m597）已按正确 schema 读写这些列。",
              "anchor_char_start": 1380,
              "anchor_char_end": 1417,
              "anchor_text": "backend/services/factory_bootstrap.py",
              "anchor_line": 26
            }
          ],
          "resolvable": false,
          "resolvable_status": "unknown/unresolved",
          "unresolved_reason": "该工件路径属 TensorPlatform 仓（本工作树为 TensorKnowledge），报告仅文字引用、未附内容；本工序不跨仓取证，故可解析性记为未验证"
        },
        {
          "asset_id": "art-03",
          "kind": "source module",
          "ref": "backend/migrations/run_migration.py",
          "purpose_in_report": "生产侧迁移执行器（glob 全量 + 版本登记）",
          "mentioned_at": [
            {
              "line_start": 26,
              "line_end": 26,
              "char_start": 1349,
              "char_end": 1799,
              "quote": "2. 定根因（读代码 + `git log -S`，不猜）：`backend/services/factory_bootstrap.py` 用**手写文件名元组**（084 基线 + 086..093 + soul 094）喂测试库；生产侧 `backend/migrations/run_migration.py` 用 glob 全量 + 版本登记 → **生产有列、测试库没有**。手写元组引入于 2f7d2fe（2026-10-21），此后新增迁移从未回补：090_tensor_reports（PR #16，2ea470b）、095_mission_lifecycle（PR #223 agent/m597，1f5f711）、096_report_gate（966ea2e 并入 main），而 API 侧 tensor_missions.py（m641/PR #229，0e7686f）、tensor_mission_lifecycle.py（m597）已按正确 schema 读写这些列。",
              "anchor_char_start": 1471,
              "anchor_char_end": 1506,
              "anchor_text": "backend/migrations/run_migration.py",
              "anchor_line": 26
            }
          ],
          "resolvable": false,
          "resolvable_status": "unknown/unresolved",
          "unresolved_reason": "该工件路径属 TensorPlatform 仓（本工作树为 TensorKnowledge），报告仅文字引用、未附内容；本工序不跨仓取证，故可解析性记为未验证"
        },
        {
          "asset_id": "art-04",
          "kind": "migration sql",
          "ref": "097_campaign_plans_superset.sql",
          "purpose_in_report": "补通道后暴露的第二个断点修复脚本",
          "mentioned_at": [
            {
              "line_start": 29,
              "line_end": 29,
              "char_start": 1986,
              "char_end": 2143,
              "quote": "   - `097_campaign_plans_superset.sql`：补通道后暴露链上第二个断点——遗留 m611 列回填在全新库上 `column \"title\" does not exist`；改为 `information_schema.columns` 存在性判断的条件回填（遗留库行为逐字不变）。",
              "anchor_char_start": 1992,
              "anchor_char_end": 2023,
              "anchor_text": "097_campaign_plans_superset.sql",
              "anchor_line": 29
            }
          ],
          "resolvable": false,
          "resolvable_status": "unknown/unresolved",
          "unresolved_reason": "该工件路径属 TensorPlatform 仓（本工作树为 TensorKnowledge），报告仅文字引用、未附内容；本工序不跨仓取证，故可解析性记为未验证"
        },
        {
          "asset_id": "art-05",
          "kind": "test file",
          "ref": "tests/factory/test_schema_migrations.py",
          "purpose_in_report": "新增守护测试（报告称 4 例）",
          "mentioned_at": [
            {
              "line_start": 30,
              "line_end": 30,
              "char_start": 2144,
              "char_end": 2225,
              "quote": "   - 新增 `tests/factory/test_schema_migrations.py`（4 例）：迁移清单完整性 + 迁移声明列必须在测试库真实存在。",
              "anchor_char_start": 2153,
              "anchor_char_end": 2192,
              "anchor_text": "tests/factory/test_schema_migrations.py",
              "anchor_line": 30
            }
          ],
          "resolvable": false,
          "resolvable_status": "unknown/unresolved",
          "unresolved_reason": "该工件路径属 TensorPlatform 仓（本工作树为 TensorKnowledge），报告仅文字引用、未附内容；本工序不跨仓取证，故可解析性记为未验证"
        },
        {
          "asset_id": "art-06",
          "kind": "evidence script",
          "ref": "artifacts/m1625/probe_schema.py",
          "purpose_in_report": "建 before/after 两个一次性集群的探测脚本",
          "mentioned_at": [
            {
              "line_start": 31,
              "line_end": 31,
              "char_start": 2226,
              "char_end": 2349,
              "quote": "4. 证据采集脚本：`artifacts/m1625/probe_schema.py` 建两个一次性集群（before=修复前手写清单行为 / after=bootstrap），数字全部从 `information_schema` 读回，零手抄。",
              "anchor_char_start": 2237,
              "anchor_char_end": 2268,
              "anchor_text": "artifacts/m1625/probe_schema.py",
              "anchor_line": 31
            }
          ],
          "resolvable": false,
          "resolvable_status": "unknown/unresolved",
          "unresolved_reason": "该工件路径属 TensorPlatform 仓（本工作树为 TensorKnowledge），报告仅文字引用、未附内容；本工序不跨仓取证，故可解析性记为未验证"
        },
        {
          "asset_id": "art-07",
          "kind": "data artifact",
          "ref": "artifacts/m1625/schema_coverage.json",
          "purpose_in_report": "结果图数据源（报告称程序化生成）",
          "mentioned_at": [
            {
              "line_start": 42,
              "line_end": 42,
              "char_start": 2607,
              "char_end": 2720,
              "quote": "左：迁移文件应用数 9→19；右：CI 签名点名的列在测试库中的存在性（1=present）。数据源 `artifacts/m1625/schema_coverage.json`（probe_schema.py 程序化生成）。",
              "anchor_char_start": 2659,
              "anchor_char_end": 2695,
              "anchor_text": "artifacts/m1625/schema_coverage.json",
              "anchor_line": 42
            }
          ],
          "resolvable": false,
          "resolvable_status": "unknown/unresolved",
          "unresolved_reason": "该工件路径属 TensorPlatform 仓（本工作树为 TensorKnowledge），报告仅文字引用、未附内容；本工序不跨仓取证，故可解析性记为未验证"
        },
        {
          "asset_id": "art-08",
          "kind": "migration sql",
          "ref": "094_factory_soul.sql",
          "purpose_in_report": "已知冗余：glob 与 soul 版本登记器各执行一次",
          "mentioned_at": [
            {
              "line_start": 45,
              "line_end": 45,
              "char_start": 2736,
              "char_end": 2832,
              "quote": "- 094_factory_soul.sql 现经两条通道各执行一次（glob + soul 版本登记器），DDL 全 `IF NOT EXISTS` 且登记器幂等，实测无副作用，属已知冗余。",
              "anchor_char_start": 2738,
              "anchor_char_end": 2758,
              "anchor_text": "094_factory_soul.sql",
              "anchor_line": 45
            }
          ],
          "resolvable": false,
          "resolvable_status": "unknown/unresolved",
          "unresolved_reason": "该工件路径属 TensorPlatform 仓（本工作树为 TensorKnowledge），报告仅文字引用、未附内容；本工序不跨仓取证，故可解析性记为未验证"
        }
      ],
      "registered_schema_elements": [
        {
          "ref_id": "schema-elem-01",
          "table_column": "tensor_dev_missions.report_id",
          "declared_by_migration": "096_report_gate.sql:12",
          "presence": {
            "production": "present",
            "test_db_before_fix": "missing"
          },
          "locator": {
            "line_start": 15,
            "line_end": 15,
            "char_start": 499,
            "char_end": 569,
            "quote": "| 1 | tensor_dev_missions.report_id | 096_report_gate.sql:12 | 有 | 缺 |"
          }
        },
        {
          "ref_id": "schema-elem-02",
          "table_column": "tensor_dev_missions.report_owed",
          "declared_by_migration": "096_report_gate.sql:8 / 095_mission_lifecycle.sql:38",
          "presence": {
            "production": "present",
            "test_db_before_fix": "missing"
          },
          "locator": {
            "line_start": 16,
            "line_end": 16,
            "char_start": 570,
            "char_end": 672,
            "quote": "| 2 | tensor_dev_missions.report_owed | 096_report_gate.sql:8 / 095_mission_lifecycle.sql:38 | 有 | 缺 |"
          }
        },
        {
          "ref_id": "schema-elem-03",
          "table_column": "tensor_dev_missions.fail_stage",
          "declared_by_migration": "095_mission_lifecycle.sql:35",
          "presence": {
            "production": "present",
            "test_db_before_fix": "missing"
          },
          "locator": {
            "line_start": 17,
            "line_end": 17,
            "char_start": 673,
            "char_end": 750,
            "quote": "| 3 | tensor_dev_missions.fail_stage | 095_mission_lifecycle.sql:35 | 有 | 缺 |"
          }
        },
        {
          "ref_id": "schema-elem-04",
          "table_column": "tensor_dev_missions.suspended_at",
          "declared_by_migration": "095_mission_lifecycle.sql:19",
          "presence": {
            "production": "present",
            "test_db_before_fix": "missing"
          },
          "locator": {
            "line_start": 18,
            "line_end": 18,
            "char_start": 751,
            "char_end": 830,
            "quote": "| 4 | tensor_dev_missions.suspended_at | 095_mission_lifecycle.sql:19 | 有 | 缺 |"
          }
        },
        {
          "ref_id": "schema-elem-05",
          "table_column": "tensor_dev_missions.worktree_recyclable",
          "declared_by_migration": "095_mission_lifecycle.sql:41",
          "presence": {
            "production": "present",
            "test_db_before_fix": "missing"
          },
          "locator": {
            "line_start": 19,
            "line_end": 19,
            "char_start": 831,
            "char_end": 917,
            "quote": "| 5 | tensor_dev_missions.worktree_recyclable | 095_mission_lifecycle.sql:41 | 有 | 缺 |"
          }
        },
        {
          "ref_id": "schema-elem-06",
          "table_column": "tensor_dev_missions.budget_used",
          "declared_by_migration": "095_mission_lifecycle.sql:30",
          "presence": {
            "production": "present",
            "test_db_before_fix": "missing"
          },
          "locator": {
            "line_start": 20,
            "line_end": 20,
            "char_start": 918,
            "char_end": 996,
            "quote": "| 6 | tensor_dev_missions.budget_used | 095_mission_lifecycle.sql:30 | 有 | 缺 |"
          }
        },
        {
          "ref_id": "schema-elem-07",
          "table_column": "campaign_plans.name",
          "declared_by_migration": "095_campaign_plans.sql / 097",
          "presence": {
            "production": "present",
            "test_db_before_fix": "missing"
          },
          "locator": {
            "line_start": 21,
            "line_end": 21,
            "char_start": 997,
            "char_end": 1065,
            "quote": "| 7 | campaign_plans.name | 095_campaign_plans.sql / 097 | 有 | 整表缺 |"
          }
        },
        {
          "ref_id": "schema-elem-08",
          "table_column": "campaign_plans.campaign_id",
          "declared_by_migration": "095_campaign_plans.sql / 097",
          "presence": {
            "production": "present",
            "test_db_before_fix": "missing"
          },
          "locator": {
            "line_start": 22,
            "line_end": 22,
            "char_start": 1066,
            "char_end": 1141,
            "quote": "| 8 | campaign_plans.campaign_id | 095_campaign_plans.sql / 097 | 有 | 整表缺 |"
          }
        }
      ],
      "registered_metric_locators": [
        {
          "metric_id": "mig_files",
          "locator": {
            "line_start": 36,
            "line_end": 36,
            "char_start": 2407,
            "char_end": 2432,
            "quote": "| 应用到测试库的迁移文件数 | 9 | 19 |"
          }
        },
        {
          "metric_id": "tables",
          "locator": {
            "line_start": 37,
            "line_end": 37,
            "char_start": 2433,
            "char_end": 2465,
            "quote": "| `public` schema 表数 | 15 | 43 |"
          }
        },
        {
          "metric_id": "missing_cols",
          "locator": {
            "line_start": 38,
            "line_end": 38,
            "char_start": 2466,
            "char_end": 2497,
            "quote": "| 签名 8 个 schema 元素缺失数 | 8 | 0 |"
          }
        },
        {
          "metric_id": "factory_tests",
          "locator": {
            "line_start": 39,
            "line_end": 39,
            "char_start": 2498,
            "char_end": 2596,
            "quote": "| `tests/factory` 结果 | 5 FAILED（report_id / fail_stage UndefinedColumn） | **168 passed**（34.3 s） |"
          }
        }
      ],
      "claims": [
        {
          "claim_id": "wp-1200-01-c01",
          "text": "报告原文声称：TensorPlatform main 自 dd66cb0c 起 control-plane job 连红，5 例 FAILED，且非单 PR 引入。",
          "status": "supported",
          "evidence": [
            {
              "quote": "TensorPlatform `main` 自 dd66cb0c 起 control-plane job 连红，5 例 FAILED（非单 PR 引入），签名：",
              "source_field": "markdown",
              "note": "登记报告陈述；本工序不独立复核 CI 历史"
            }
          ]
        },
        {
          "claim_id": "wp-1200-01-c02",
          "text": "报告原文给出的失败签名是 psycopg2.errors.UndefinedColumn：tensor_dev_missions 上的 report_id / fail_stage 列不存在。",
          "status": "supported",
          "evidence": [
            {
              "quote": "psycopg2.errors.UndefinedColumn: column \"report_id\" / \"fail_stage\"",
              "source_field": "markdown",
              "note": "失败签名第 1 行"
            },
            {
              "quote": "of relation \"tensor_dev_missions\" does not exist",
              "source_field": "markdown",
              "note": "失败签名第 2 行"
            }
          ]
        },
        {
          "claim_id": "wp-1200-01-c03",
          "text": "报告原文把 8 个 schema 元素列为本单判据集：生产库存在、修复前测试库缺失。",
          "status": "supported",
          "evidence": [
            {
              "quote": "对象为 `tests/factory` 集成测试库（真实 PostgreSQL，临时集群，`tests/factory/conftest.py`）。失败签名点名的 8 个 schema 元素（本次审计的判据集）：",
              "source_field": "markdown",
              "note": "判据集声明"
            },
            {
              "quote": "| 1 | tensor_dev_missions.report_id | 096_report_gate.sql:12 | 有 | 缺 |",
              "source_field": "markdown",
              "note": "判据 schema-elem-01 tensor_dev_missions.report_id"
            },
            {
              "quote": "| 2 | tensor_dev_missions.report_owed | 096_report_gate.sql:8 / 095_mission_lifecycle.sql:38 | 有 | 缺 |",
              "source_field": "markdown",
              "note": "判据 schema-elem-02 tensor_dev_missions.report_owed"
            },
            {
              "quote": "| 3 | tensor_dev_missions.fail_stage | 095_mission_lifecycle.sql:35 | 有 | 缺 |",
              "source_field": "markdown",
              "note": "判据 schema-elem-03 tensor_dev_missions.fail_stage"
            },
            {
              "quote": "| 4 | tensor_dev_missions.suspended_at | 095_mission_lifecycle.sql:19 | 有 | 缺 |",
              "source_field": "markdown",
              "note": "判据 schema-elem-04 tensor_dev_missions.suspended_at"
            },
            {
              "quote": "| 5 | tensor_dev_missions.worktree_recyclable | 095_mission_lifecycle.sql:41 | 有 | 缺 |",
              "source_field": "markdown",
              "note": "判据 schema-elem-05 tensor_dev_missions.worktree_recyclable"
            },
            {
              "quote": "| 6 | tensor_dev_missions.budget_used | 095_mission_lifecycle.sql:30 | 有 | 缺 |",
              "source_field": "markdown",
              "note": "判据 schema-elem-06 tensor_dev_missions.budget_used"
            },
            {
              "quote": "| 7 | campaign_plans.name | 095_campaign_plans.sql / 097 | 有 | 整表缺 |",
              "source_field": "markdown",
              "note": "判据 schema-elem-07 campaign_plans.name"
            },
            {
              "quote": "| 8 | campaign_plans.campaign_id | 095_campaign_plans.sql / 097 | 有 | 整表缺 |",
              "source_field": "markdown",
              "note": "判据 schema-elem-08 campaign_plans.campaign_id"
            }
          ]
        },
        {
          "claim_id": "wp-1200-01-c04",
          "text": "报告原文的根因判断：测试库由 backend/services/factory_bootstrap.py 的手写文件名元组喂养，生产侧由 run_migration.py glob 全量，导致生产有列而测试库没有。",
          "status": "supported",
          "evidence": [
            {
              "quote": "2. 定根因（读代码 + `git log -S`，不猜）：`backend/services/factory_bootstrap.py` 用**手写文件名元组**（084 基线 + 086..093 + soul 094）喂测试库；生产侧 `backend/migrations/run_migration.py` 用 glob 全量 + 版本登记 → **生产有列、测试库没有**。手写元组引入于 2f7d2fe（2026-10-21），此后新增迁移从未回补：090_tensor_reports（PR #16，2ea470b）、095_mission_lifecycle（PR #223 agent/m597，1f5f711）、096_report_gate（966ea2e 并入 main），而 API 侧 tensor_missions.py（m641/PR #229，0e7686f）、tensor_mission_lifecycle.py（m597）已按正确 schema 读写这些列。",
              "source_field": "markdown",
              "note": "根因段（读代码 + git log -S）"
            }
          ]
        },
        {
          "claim_id": "wp-1200-01-c05",
          "text": "报告原文的修复效果数字：迁移文件 9→19、public 表 15→43、8 个 schema 元素缺失 8→0、tests/factory 由 5 FAILED 转为 168 passed（34.3 s）。",
          "status": "supported",
          "evidence": [
            {
              "quote": "| 应用到测试库的迁移文件数 | 9 | 19 |",
              "source_field": "markdown",
              "note": "结果表行 mig_files"
            },
            {
              "quote": "| `public` schema 表数 | 15 | 43 |",
              "source_field": "markdown",
              "note": "结果表行 tables"
            },
            {
              "quote": "| 签名 8 个 schema 元素缺失数 | 8 | 0 |",
              "source_field": "markdown",
              "note": "结果表行 missing_cols"
            },
            {
              "quote": "| `tests/factory` 结果 | 5 FAILED（report_id / fail_stage UndefinedColumn） | **168 passed**（34.3 s） |",
              "source_field": "markdown",
              "note": "结果表行 factory_tests"
            }
          ]
        },
        {
          "claim_id": "wp-1200-01-c06",
          "text": "报告原文称新增 tests/factory/test_schema_migrations.py 共 4 例（迁移清单完整性 + 迁移声明列必须在测试库真实存在）。",
          "status": "supported",
          "evidence": [
            {
              "quote": "   - 新增 `tests/factory/test_schema_migrations.py`（4 例）：迁移清单完整性 + 迁移声明列必须在测试库真实存在。",
              "source_field": "markdown",
              "note": "修复面第 3 条 bullet"
            }
          ]
        },
        {
          "claim_id": "wp-1200-01-c07",
          "text": "报告原文把 094_factory_soul.sql 经 glob 与 soul 版本登记器各执行一次登记为已知冗余（DDL 幂等，实测无副作用）。",
          "status": "supported",
          "evidence": [
            {
              "quote": "- 094_factory_soul.sql 现经两条通道各执行一次（glob + soul 版本登记器），DDL 全 `IF NOT EXISTS` 且登记器幂等，实测无副作用，属已知冗余。",
              "source_field": "markdown",
              "note": "注意点第 1 条"
            }
          ]
        },
        {
          "claim_id": "wp-1200-01-c08",
          "text": "报告原文称 backend/tests 中 test_alert_unit / test_api_key_unit 的 FAILED 为预存在环境问题（FastAPI 依赖注入版本漂移），另有 24 模块因离线缺包 collection ERROR，均非本改动引入。",
          "status": "partially-supported",
          "evidence": [
            {
              "quote": "- `backend/tests` 抽样：test_abtest_unit/test_audit_unit/test_agent_routing/test_tensor_repro_redteam 全绿；test_alert_unit/test_api_key_unit 在净树上同样 FAILED（`'Depends' object has no attribute 'query'`，本地 FastAPI 0.136 依赖注入版本漂移，预存在）；test_auth_guard 缺 pytest-asyncio；24 模块因离线缺 redis 等包 collection ERROR——均为环境限制，非本改动引入。",
              "source_field": "markdown",
              "note": "报告自述；未附逐例日志，本工序无法独立确认『预存在』归因"
            }
          ]
        },
        {
          "claim_id": "wp-1200-01-c09",
          "text": "报告原文自评误差判定为是（<3%），理由是本单判据为离散一致性（8→0 缺失、5→0 失败 = 0%），连续物理量误差不适用。",
          "status": "supported",
          "evidence": [
            {
              "quote": "本单判据为**二值一致性**，无可比标量基准：签名 schema 元素缺失数 8 → 0（等价误差 0/8 项 = 0%）；`tests/factory` 失败 5 → 0（等价误差 0%）。变异验证：把手写清单还原后新守护测试 3 failed 并逐列点名缺失列，证明门禁有效。因此「关键量是否 <3%」= **是（0%，且为离散一致性判据，不是连续物理量）**；连续量误差不适用，原因：本任务为 CI/schema 契约修复，不产生物理场量或标量基准。",
              "source_field": "markdown",
              "note": "⑥ 误差判定段"
            }
          ]
        },
        {
          "claim_id": "wp-1200-01-c10",
          "text": "报告原文声明存在未审计项：生产库 schema_migrations 登记与 backend/migrations/versions/（alembic 空壳 initial）的关系未审计，留待平台审计项。",
          "status": "unresolved",
          "unresolved_reason": "报告自述为未完成事项，本工序不做抽取/复核，保持未决；不得据本报告推定其已闭合",
          "evidence": [
            {
              "quote": "- 未审计生产库 `schema_migrations` 登记与 `backend/migrations/versions/`（alembic 仅一个空壳 initial）的关系，留待平台审计项。",
              "source_field": "markdown",
              "note": "⑤ 局限第 4 条"
            }
          ]
        }
      ],
      "stats": {
        "attachments_listed": 8,
        "attachments_resolvable": 0,
        "schema_elements_registered": 8,
        "claims_total": 10,
        "claims_supported": 8,
        "claims_partially_supported": 1,
        "claims_unresolved": 1,
        "claims_refuted": 0
      },
      "unresolved": [
        "附件可解析性（8 项）均为 unknown/unresolved：路径属 TensorPlatform 仓，本工序不跨仓取证。",
        "报告 c10 声明的生产库 schema_migrations / alembic 关系未审计，本工序保持未决。",
        "本工序不做抽取，claims 仅为报告原文陈述的登记定位，不含独立复核结论。"
      ]
    }
  },
  "claims": [
    {
      "claim_id": "wp-1200-01-c01",
      "text": "报告原文声称：TensorPlatform main 自 dd66cb0c 起 control-plane job 连红，5 例 FAILED，且非单 PR 引入。",
      "status": "supported",
      "evidence": [
        {
          "quote": "TensorPlatform `main` 自 dd66cb0c 起 control-plane job 连红，5 例 FAILED（非单 PR 引入），签名：",
          "source_field": "markdown",
          "note": "登记报告陈述；本工序不独立复核 CI 历史"
        }
      ]
    },
    {
      "claim_id": "wp-1200-01-c02",
      "text": "报告原文给出的失败签名是 psycopg2.errors.UndefinedColumn：tensor_dev_missions 上的 report_id / fail_stage 列不存在。",
      "status": "supported",
      "evidence": [
        {
          "quote": "psycopg2.errors.UndefinedColumn: column \"report_id\" / \"fail_stage\"",
          "source_field": "markdown",
          "note": "失败签名第 1 行"
        },
        {
          "quote": "of relation \"tensor_dev_missions\" does not exist",
          "source_field": "markdown",
          "note": "失败签名第 2 行"
        }
      ]
    },
    {
      "claim_id": "wp-1200-01-c03",
      "text": "报告原文把 8 个 schema 元素列为本单判据集：生产库存在、修复前测试库缺失。",
      "status": "supported",
      "evidence": [
        {
          "quote": "对象为 `tests/factory` 集成测试库（真实 PostgreSQL，临时集群，`tests/factory/conftest.py`）。失败签名点名的 8 个 schema 元素（本次审计的判据集）：",
          "source_field": "markdown",
          "note": "判据集声明"
        },
        {
          "quote": "| 1 | tensor_dev_missions.report_id | 096_report_gate.sql:12 | 有 | 缺 |",
          "source_field": "markdown",
          "note": "判据 schema-elem-01 tensor_dev_missions.report_id"
        },
        {
          "quote": "| 2 | tensor_dev_missions.report_owed | 096_report_gate.sql:8 / 095_mission_lifecycle.sql:38 | 有 | 缺 |",
          "source_field": "markdown",
          "note": "判据 schema-elem-02 tensor_dev_missions.report_owed"
        },
        {
          "quote": "| 3 | tensor_dev_missions.fail_stage | 095_mission_lifecycle.sql:35 | 有 | 缺 |",
          "source_field": "markdown",
          "note": "判据 schema-elem-03 tensor_dev_missions.fail_stage"
        },
        {
          "quote": "| 4 | tensor_dev_missions.suspended_at | 095_mission_lifecycle.sql:19 | 有 | 缺 |",
          "source_field": "markdown",
          "note": "判据 schema-elem-04 tensor_dev_missions.suspended_at"
        },
        {
          "quote": "| 5 | tensor_dev_missions.worktree_recyclable | 095_mission_lifecycle.sql:41 | 有 | 缺 |",
          "source_field": "markdown",
          "note": "判据 schema-elem-05 tensor_dev_missions.worktree_recyclable"
        },
        {
          "quote": "| 6 | tensor_dev_missions.budget_used | 095_mission_lifecycle.sql:30 | 有 | 缺 |",
          "source_field": "markdown",
          "note": "判据 schema-elem-06 tensor_dev_missions.budget_used"
        },
        {
          "quote": "| 7 | campaign_plans.name | 095_campaign_plans.sql / 097 | 有 | 整表缺 |",
          "source_field": "markdown",
          "note": "判据 schema-elem-07 campaign_plans.name"
        },
        {
          "quote": "| 8 | campaign_plans.campaign_id | 095_campaign_plans.sql / 097 | 有 | 整表缺 |",
          "source_field": "markdown",
          "note": "判据 schema-elem-08 campaign_plans.campaign_id"
        }
      ]
    },
    {
      "claim_id": "wp-1200-01-c04",
      "text": "报告原文的根因判断：测试库由 backend/services/factory_bootstrap.py 的手写文件名元组喂养，生产侧由 run_migration.py glob 全量，导致生产有列而测试库没有。",
      "status": "supported",
      "evidence": [
        {
          "quote": "2. 定根因（读代码 + `git log -S`，不猜）：`backend/services/factory_bootstrap.py` 用**手写文件名元组**（084 基线 + 086..093 + soul 094）喂测试库；生产侧 `backend/migrations/run_migration.py` 用 glob 全量 + 版本登记 → **生产有列、测试库没有**。手写元组引入于 2f7d2fe（2026-10-21），此后新增迁移从未回补：090_tensor_reports（PR #16，2ea470b）、095_mission_lifecycle（PR #223 agent/m597，1f5f711）、096_report_gate（966ea2e 并入 main），而 API 侧 tensor_missions.py（m641/PR #229，0e7686f）、tensor_mission_lifecycle.py（m597）已按正确 schema 读写这些列。",
          "source_field": "markdown",
          "note": "根因段（读代码 + git log -S）"
        }
      ]
    },
    {
      "claim_id": "wp-1200-01-c05",
      "text": "报告原文的修复效果数字：迁移文件 9→19、public 表 15→43、8 个 schema 元素缺失 8→0、tests/factory 由 5 FAILED 转为 168 passed（34.3 s）。",
      "status": "supported",
      "evidence": [
        {
          "quote": "| 应用到测试库的迁移文件数 | 9 | 19 |",
          "source_field": "markdown",
          "note": "结果表行 mig_files"
        },
        {
          "quote": "| `public` schema 表数 | 15 | 43 |",
          "source_field": "markdown",
          "note": "结果表行 tables"
        },
        {
          "quote": "| 签名 8 个 schema 元素缺失数 | 8 | 0 |",
          "source_field": "markdown",
          "note": "结果表行 missing_cols"
        },
        {
          "quote": "| `tests/factory` 结果 | 5 FAILED（report_id / fail_stage UndefinedColumn） | **168 passed**（34.3 s） |",
          "source_field": "markdown",
          "note": "结果表行 factory_tests"
        }
      ]
    },
    {
      "claim_id": "wp-1200-01-c06",
      "text": "报告原文称新增 tests/factory/test_schema_migrations.py 共 4 例（迁移清单完整性 + 迁移声明列必须在测试库真实存在）。",
      "status": "supported",
      "evidence": [
        {
          "quote": "   - 新增 `tests/factory/test_schema_migrations.py`（4 例）：迁移清单完整性 + 迁移声明列必须在测试库真实存在。",
          "source_field": "markdown",
          "note": "修复面第 3 条 bullet"
        }
      ]
    },
    {
      "claim_id": "wp-1200-01-c07",
      "text": "报告原文把 094_factory_soul.sql 经 glob 与 soul 版本登记器各执行一次登记为已知冗余（DDL 幂等，实测无副作用）。",
      "status": "supported",
      "evidence": [
        {
          "quote": "- 094_factory_soul.sql 现经两条通道各执行一次（glob + soul 版本登记器），DDL 全 `IF NOT EXISTS` 且登记器幂等，实测无副作用，属已知冗余。",
          "source_field": "markdown",
          "note": "注意点第 1 条"
        }
      ]
    },
    {
      "claim_id": "wp-1200-01-c08",
      "text": "报告原文称 backend/tests 中 test_alert_unit / test_api_key_unit 的 FAILED 为预存在环境问题（FastAPI 依赖注入版本漂移），另有 24 模块因离线缺包 collection ERROR，均非本改动引入。",
      "status": "partially-supported",
      "evidence": [
        {
          "quote": "- `backend/tests` 抽样：test_abtest_unit/test_audit_unit/test_agent_routing/test_tensor_repro_redteam 全绿；test_alert_unit/test_api_key_unit 在净树上同样 FAILED（`'Depends' object has no attribute 'query'`，本地 FastAPI 0.136 依赖注入版本漂移，预存在）；test_auth_guard 缺 pytest-asyncio；24 模块因离线缺 redis 等包 collection ERROR——均为环境限制，非本改动引入。",
          "source_field": "markdown",
          "note": "报告自述；未附逐例日志，本工序无法独立确认『预存在』归因"
        }
      ]
    },
    {
      "claim_id": "wp-1200-01-c09",
      "text": "报告原文自评误差判定为是（<3%），理由是本单判据为离散一致性（8→0 缺失、5→0 失败 = 0%），连续物理量误差不适用。",
      "status": "supported",
      "evidence": [
        {
          "quote": "本单判据为**二值一致性**，无可比标量基准：签名 schema 元素缺失数 8 → 0（等价误差 0/8 项 = 0%）；`tests/factory` 失败 5 → 0（等价误差 0%）。变异验证：把手写清单还原后新守护测试 3 failed 并逐列点名缺失列，证明门禁有效。因此「关键量是否 <3%」= **是（0%，且为离散一致性判据，不是连续物理量）**；连续量误差不适用，原因：本任务为 CI/schema 契约修复，不产生物理场量或标量基准。",
          "source_field": "markdown",
          "note": "⑥ 误差判定段"
        }
      ]
    },
    {
      "claim_id": "wp-1200-01-c10",
      "text": "报告原文声明存在未审计项：生产库 schema_migrations 登记与 backend/migrations/versions/（alembic 空壳 initial）的关系未审计，留待平台审计项。",
      "status": "unresolved",
      "unresolved_reason": "报告自述为未完成事项，本工序不做抽取/复核，保持未决；不得据本报告推定其已闭合",
      "evidence": [
        {
          "quote": "- 未审计生产库 `schema_migrations` 登记与 `backend/migrations/versions/`（alembic 仅一个空壳 initial）的关系，留待平台审计项。",
          "source_field": "markdown",
          "note": "⑤ 局限第 4 条"
        }
      ]
    }
  ]
}
```
