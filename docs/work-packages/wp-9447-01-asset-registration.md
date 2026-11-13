# wp-9447-01 — Matured mission deliverables → knowledge assets (asset registration)

* 任务类型：`01-asset-registration`（本仓 `docs/kf/` 之外的通用工作包目录）
* 代码：`ke/mission_assets.py`（库）+ `ke/cli.py`（`assets register-mission|mission-report|verify-mission`）
* 测试：`tests/test_wp_9447_01_asset_registration.py`（39 项，sqlite + pg 双后端）
* 演示工件：`scripts/kf/wp9447_01_register.py` → `artifacts/wp-9447-01/registration_report.json`；
  成本基准 `artifacts/wp-9447-01/bench_register.py` → `bench.json` + `docs/figures/wp-9447-01-registration.png`；
  进展报告已发布到平台报告 API（mission 18426，report id 17239）
* 前身：PR#167 已由 owner 2026-11-05 裁定关闭（该分支只含一篇文档、一份断言不存在对象的测试、
  以及两个 `ke/__pycache__/*.pyc` 字节码文件，无任何实现）。本包从当前 `main` 重做，
  **功能 + 测试 + 证据齐备**；并把「字节码不算交付物」写成了机器校验（见下 §3 A4）。

## 1. 背景与缺口

`ke/assets.py` 规定了知识对象（KO）怎么存：不可变版本、状态机
`draft → in_review → published → deprecated`、只有 `review_events` 里的 `approve`
才能让版本发布、数据集资产按 `sha256` 钉死。但它**不管一件事**：一个任务（mission）跑完之后，
它的交付物凭什么能进注册表。现实中这一步靠手写 manifest 脚本，代价是三类老问题：

1. **空壳洗白**：`MOCK`/`STUB` 级交付物只要能写进 manifest 就变成"知识对象"，
   证据等级只剩作者自述；
2. **自证自发布**：生产者在注册时直接写 `state=published`，绕开 reviewer 门；
3. **字节漂移**：manifest 里的 `sha256` 是手抄的，注册后又改了文件，
   注册表钉住的其实是"当时的字符串"而不是"当时的字节"。

本工作包设计的是**成熟度闸门 + 字节重算 + 只出生在 `in_review`** 的注册路径。

## 2. 规则（全部由代码执行，不是约定）

| # | 规则 | 实现点 |
|---|---|---|
| A1 | 只有 `evidence_grade == REAL` 的交付物可入册；`MOCK/STUB/WITHHELD/NOT_SUPPORTED` 拒绝并给出理由 | `MATURE_GRADES = {"REAL"}` |
| A2 | 必须给出非空 `acceptance`（验收判据）；"做完了"不等于成熟 | `normalise_deliverables` |
| A3 | 文件必须存在、位于 `base_dir` 内（拒绝 `..` 越界）、非空、≤5 MiB | `_resolve` |
| A4 | `__pycache__` 段与 `*.pyc` 一律拒收（构建垃圾不是交付物） | `_resolve` |
| A5 | 批量内 `deliverable_id` 不得重复；校验**全量先跑完**，任一项失败整批不写行 | `DeliverableError` + 先校验后写 |
| A6 | `sha256` 由本模块从字节重算，**调用方传入的 `sha256` 被忽略** | `sha256_file` |
| A7 | 出生状态只允许 `draft`/`in_review`；`published` 被拒（发布只能是 review 决定） | `ALLOWED_BIRTH_STATES` |
| A8 | 幂等：同 `mission+deliverable+version` 且字节相同 → `skipped_idempotent`；字节不同 → `ValueError`（bump version） | 写入前比对 `ko_versions.content.sha256` |
| A9 | 标识确定：`ko_id = mission.<mission_id>.<deliverable_id>`，`vid = ko_id:v<version>` | `ko_id_for` |
| A10 | 可复核：`mission-report` 按任务列交付物（后端中立，Python 侧过滤）；`verify-mission` 重算磁盘字节报 `ok/drift/missing` | `mission_deliverable_report` / `verify_mission_deliverables` |

`register_matured_deliverables()` 返回 `mission-assets-report.v1`：逐条
`{ko_id, version_id, path, sha256, evidence_grade, status}`，统计块，以及
`batch_sha256` = 对全部 `(ko_id, 内容 sha256)` 的规范摘要——批次级见证，
换一台机器重跑同一批交付物得到同一个值。

## 3. 验收证据

| 验收项 | 机器证据（测试名） |
|---|---|
| 报告结构与批次见证 | `test_report_shape_and_witness` |
| 摘要重算、不信调用方 | `test_hash_is_recomputed_not_trusted` |
| 只出生 `in_review`，发布须经 review | `test_versions_born_in_review` |
| `published` 出生被拒 | `test_draft_birth_allowed_but_published_forbidden` |
| 幂等重跑 | `test_rerun_is_idempotent` |
| 字节不可变 + version bump 合法路径 | `test_reconfigured_bytes_raise` |
| 成熟度闸门（4 个非 REAL 等级） | `test_non_matured_grades_rejected` |
| 未知等级拒收 | `test_unknown_grade_rejected` |
| 批次原子性（1 个 MOCK 污染整批） | `test_failed_batch_writes_nothing` |
| 字节码拒收（PR#167 教训） | `test_bytecode_artefacts_rejected` |
| 缺失文件 / 目录穿越 | `test_missing_file_and_traversal_rejected` |
| 重复 id / 缺 acceptance / 非法 id | `test_duplicate_ids_rejected`、`test_acceptance_and_id_required` |
| 任务过滤 + 版本取最新 | `test_mission_report_scopes_and_orders` |
| 漂移与丢失检测 | `test_verify_detects_drift_and_missing` |
| CLI 运维路径端到端（含非零退出码） | `test_cli_roundtrip` |

运行：`python -m pytest tests/test_wp_9447_01_asset_registration.py -q`
→ 39 passed（`sqlite` 与 `pg` 各一份，`new_conn` 工厂参数化）。

## 4. 边界与不做的部分

* 不替代 review：本模块**只**负责把成熟交付物放到 `in_review`；
  `approve` 仍必须走 `ke.assets.record_review`（reviewer 与 policy_version 入账）。
* 不做语义评分：`evidence_grade` 由上游任务验收结论给出，本模块只**校验等级取值范围**
  并按成熟度闸门拒绝——它挡的是"把 MOCK 写进册"，不是"判断是不是 REAL"。
* 不做内容抽取：交付物以字节 + 元数据入册，`content` 不解析正文；正文抽取归
  `ke.kbm_extract` / `ke.sediment_extract` 线。
* 后端中立：所有 SQL 都经 `ke.assets` 既有函数（`?` 占位符、`Store.collate` 排序），
  `mission_deliverable_report` 在 Python 侧按前缀过滤，避免 `LIKE` 方言差异。
* 热文件重叠声明：本包改动 `ke/cli.py`（仅新增 3 个 `assets` 子命令 + 1 行 import，
  未触碰既有命令实现），其余为新增文件；`ke/assets.py` 未修改。

## 5. 与既有能力的关系（不重复造轮子，差异逐条声明）

仓内已有一个**包级**注册脚本 `scripts/register_assets.py`（扫描含 `claims/evidence/provenance/gaps`
的 KE 记录包 → 内容摘要 → 注册 + `supersede_ko` 血缘 → `--verify` 漂移检测）。本包与它是**不同粒度、
不同策略**，重叠处如实标注：

| 维度 | `scripts/register_assets.py`（既有，脚本级） | `ke/mission_assets.py`（本包，库级） |
|---|---|---|
| 对象 | KE 记录包（`*.json` 记录目录） | 任务交付物任意文件（md/csv/…），按 `(mission, deliverable)` 定址 |
| 版本 | 内容寻址，摘要变 → 自动新版本 | 显式版本；**同版本字节变 = `ValueError`**（要求人工 bump，绝不静默替换） |
| 成熟度闸门 | 无 | 仅 `evidence_grade=REAL` + acceptance 必填 |
| 路径安全 | 无穿越/垃圾检查 | `base_dir` 越界拒绝 + `__pycache__`/`*.pyc` 拒收 + 5 MiB 上限 |
| 原子性 | 逐包写 | 批量校验先跑完，任一失败整批不写 |
| 漂移检测 | `--verify`（对 index 工件）**重叠** | `verify_mission_deliverables`（对注册表行，无需 index 工件）**重叠** |
| 调用面 | 仓库脚本 | 库函数 + `ke assets` CLI，可被 `ke.api` 等复用；双后端测试参数化 |

选择新增库而非改脚本的理由：成熟度/验收判据是**平台共性契约**（需要被 API、CLI、任务机共同调用，
并按后端参数化测试），而 `register_assets.py` 是扫描本仓 `knowledge/` 目录的运维脚本，粒度与职责不同；
把两者合一会让「记录包扫描」与「交付物闸门」耦合。漂移检测能力两处都有，是**有意保留**的
（一处对工件、一处对注册表），已在能力台账中标注为重叠。

## 6. 未完成 / 已知限制

* 全仓 `pytest tests/` 单进程在本机 120 s 内跑不完，故按文件名单分 4 批跑完（155 个测试文件，
  `tests/test_kf_wp11107_01.py` 除外，见下条），并与**pristine HEAD（c3b67b8）导出树**逐批对表：

  | 批次 | 本分支 (passed/failed/errors) | HEAD 基线 (passed/failed/errors) | 判定 |
  |---|---|---|---|
  | 1 | 478 / 23 / 65 | 478 / 23 / 65 | 一致 |
  | 2 | 308 / 65 / 88 | 308 / 65 / 88 | 一致 |
  | 3 | 386 / 58 / 102 | 386 / 58 / 102 | 一致 |
  | 4 | 392 / 52 / 66 | 353 / 52 / 66 | 一致，+39 = 本包新增测试 |

  failed/errors 全部为 HEAD 已存在的预存缺陷（多为 `runs/`、`docs/kf/` 下未被 git 跟踪的快照缺失），
  与前四列逐位相同即证明**零回归**；本单不修这些无关缺陷以保持 diff 聚焦。
* 本包与相关套件（`test_assets`/`test_ke_proto`/`test_ke_api`/本包）合跑 = **145 passed**。
* `tests/test_kf_wp11107_01.py` 在 HEAD 即因缺 `runs/wp-11107-01/source_11107.md`（未被 git 跟踪）
  而 collection error —— 预存缺陷，与本包无关，未在本单修（避免扩大 diff）。
* 集群全量作业 `cj1925` 排队 7 分钟后由本单主动 kill（本地分批 + 基线对表已给出更强的逐批证据）。
* `evidence_grade` 的判定归上游验收，本模块只做取值与闸门校验（不做自动鉴定）。
