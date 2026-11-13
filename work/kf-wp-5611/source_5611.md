## ① 案例介绍

**节点**：IN15-O1「自回归O1·饱和脉搏度量管线成熟化」（战役计划 16「饱和推进·平台自优化军」，自回归燃料①=测规模）。
**仓库/分支**：TensorPlatform · `agent/m4959` · commit `77ed9bae`。
**物理/工程背景**：本节点不是水动力算例，而是**闭环调度的量测学**——自主派发器按负载信号决定每波释放多少 DAG 节点，信号若不可复算，整条自回归回路（测量→决策→放行→再测量）就是空转。本单之前 `saturation_pulse` 表里只有一行**人手抄写**的数字（`note='online=43 busy=34 queued=2 idle=7 held16=11'`），无任何代码可复现 → 证据等级按 MOCK（硬编码）处理。目标是把这条证据升级为 REAL：可用数据库独立复算、阈值显式、带回归测试。
**几何/参数表**：不适用（非船舶几何算例；无 Cb/L/B 校验对象）。量测参数表如下：

| 参数 | 值 | 含义 |
|---|---|---|
| 心跳新鲜窗 | 300 s | worker `heartbeat_at` 在窗内即"在线"（边界含等号） |
| 活 claim 窗 | 150 s | mission `heartbeat_at` 在窗内即"忙碌"（沿用工厂 API 口径） |
| 时钟倾斜容差 | 60 s | 未来心跳计为新鲜但打 `skewed` 标记 |
| held 状态词表 | `held`, `blocked` | `campaign_nodes` + `campaign_plan_nodes` 两表并集 |
| 采集频率建议 | 每 5 min 一次 `--commit` | 与新鲜窗同量级 |

## ② 怎么做的（方法/流程/工具链）

1. **三态采集器** `tools/pulse/saturation_pulse.py`
   - 只读阶段：`BEGIN` + `connection.read_only=True`，仅 SELECT（`factory_resident_workers` / `tensor_dev_missions` / 两张 node 表 / 上一行 pulse），
     **无 `FOR UPDATE`、无 `LOCK TABLE`、无 DML**；写阶段只有一条 INSERT。
   - 语义：`online` = 心跳新鲜 worker **∪** 活 claim 主体；`busy` = 活 claim 主体（∪ 自报 running）；
     `queued` = status=queued 的 mission；`held` = held/blocked 节点（带 id，供下一采样算 `released` 差集）；
     辅助 `stale_claims` = 心跳超 150 s 的活 mission（"看着在跑其实不跳了"）。
   - 默认 **dry-run**（不写库），`--commit` 才落库；负值/零窗/超长窗一律 `PulseInputError` → 退出码 2，绝不 clamp。
2. **幂等建表（本节点唯一 schema 动作）**：`tools/pulse/sql/001_saturation_pulse.sql`，两条 `CREATE ... IF NOT EXISTS`
   （表 + ts 索引），列集与生产库**现有**表逐列一致（`ts,online,busy,held,released,note`），不做任何 ALTER；
   `--ensure-schema` 跑完再核对 information_schema 列集，漂移即 `PulseSchemaError`（拒绝写进非预期形状）。
   **只增不改落地方式**：头部三列放 online/busy/held，`released` 放本轮放行 id，完整机器可读快照（queued/idle/running_missions/held_ids/窗口…）以单行 JSON v1 存进 `note`——不改既有表结构也拿到全字段。
3. **趋势报表 CLI** `tools/pulse/pulse_report.py`：近 N 次 ASCII 火花线 + 明细表；旧自由文本 note 行标 `legacy`，其 queued 显示 `—`（不猜数字）。
4. **证据链一键重建** `tools/pulse/acceptance_evidence.py`（自带 `--dry-run`）：建表跑两遍验幂等 → 固定时刻 dry-run vs commit 比对 → 连续落库样本 →
   独立 SQL 对账 → pytest → 出图 → 写 `acceptance_IN15-O1.json`。
5. **测试** `tests/pulse/test_saturation_pulse.py`：24 条（22 纯逻辑 + 2 连库）。

## ③ 计算结果（程序化注入，零手抄）

**落库样本（从 `saturation_pulse` 读回，共 24 条 pulse-v1；另 1 条人手 legacy 行原样保留）**

| # | ts(UTC) | window/s | online | busy | queued | idle | running_missions | held | released |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 00:44:03.017368 | 300 | 53 | 40 | 1 | 13 | 40 | 16 | 0 |
| 2 | 00:44:03.468113 | 300 | 53 | 40 | 1 | 13 | 40 | 16 | 0 |
| 3 | 00:44:26.252598 | 300 | 53 | 40 | 1 | 13 | 40 | 16 | 0 |
| 4 | 00:46:16.248253 | 300 | 53 | 40 | 1 | 13 | 40 | 16 | 0 |
| 5 | 00:46:16.770406 | 300 | 53 | 40 | 1 | 13 | 40 | 16 | 0 |
| 6 | 00:47:02.229878 | 300 | 53 | 39 | 1 | 14 | 39 | 16 | 0 |
| 7 | 00:47:47.618499 | 300 | 53 | 37 | 3 | 16 | 37 | 16 | 0 |
| 8 | 00:48:00.333351 | 300 | 53 | 35 | 3 | 18 | 35 | 16 | 0 |
| 9 | 00:48:00.734179 | 300 | 53 | 35 | 3 | 18 | 35 | 16 | 0 |
| 10 | 00:49:01.297562 | 300 | 53 | 34 | 2 | 19 | 34 | 16 | 0 |
| 11 | 00:50:03.588005 | 300 | 52 | 32 | 2 | 20 | 32 | 16 | 0 |
| 12 | 00:50:03.946849 | 300 | 52 | 32 | 2 | 20 | 32 | 16 | 0 |
| 13 | 00:50:09.351735 | 300 | 52 | 32 | 2 | 20 | 32 | 16 | 0 |
| 14 | 00:50:14.798399 | 300 | 52 | 32 | 2 | 20 | 32 | 16 | 0 |
| 15 | 00:50:35.426548 | 300 | 52 | 32 | 2 | 20 | 32 | 16 | 0 |
| 16 | 00:50:36.086474 | 300 | 52 | 32 | 2 | 20 | 32 | 16 | 0 |
| 17 | 00:50:42.544186 | 300 | 52 | 32 | 2 | 20 | 32 | 16 | 0 |
| 18 | 00:50:49.136065 | 300 | 52 | 32 | 3 | 20 | 32 | 16 | 0 |
| 19 | 00:52:06.343394 | 300 | 52 | 30 | 3 | 22 | 30 | 16 | 0 |
| 20 | 00:52:06.741750 | 300 | 52 | 30 | 3 | 22 | 30 | 16 | 0 |
| 21 | 00:52:11.087867 | 300 | 52 | 30 | 3 | 22 | 30 | 16 | 0 |
| 22 | 00:52:30.759701 | 300 | 52 | 30 | 3 | 22 | 30 | 16 | 0 |
| 23 | 00:52:31.279776 | 300 | 52 | 30 | 3 | 22 | 30 | 16 | 0 |
| 24 | 00:52:35.644189 | 300 | 52 | 30 | 3 | 22 | 30 | 16 | 0 |

**判据数字**

| 判据 | 要求 | 实测 | 结论 |
|---|---|---|---|
| 连续两次采集落库 | ≥2 | 2 | PASS |
| dry-run 输出 == 实跑 | 相等 | snapshot_equal=True，note 字符串亦相等，dry-run 未写行 | PASS |
| pytest | ≥5 | 24 | PASS |
| 时间窗边界 | 有专门用例 | 边界含等号 + 边界+1s 过期 + 未来心跳 skew 标记 | PASS |
| 空表 | 有专门用例 | 全零快照 + CLI "no samples" 正常退出 | PASS |
| 负值拒收 | 有专门用例 | window∈{-1,0,-300,86401}、负计数、naive ts 全部 PulseInputError；CLI 退出码 2 | PASS |
| 采集不锁表 | 证据 | 读期仅 AccessShareLock；并发 UPDATE 在 1.5 s lock_timeout 内完成 | PASS |
| schema 动作 | 仅新增 1 张表、0 改 | DDL 2 条 IF NOT EXISTS、重跑 rc=0、列契约无漂移、无 ALTER、冻结 API 零 diff | PASS |

**独立 SQL 对账（与采集器不共享代码路径，同进程背靠背）**

| 指标 | 独立 SQL 真值 | 采集器 | delta | 相对误差 |
|---|---|---|---|---|
| `online` | 52 | 52 | +0 | 0.000 % |
| `busy` | 30 | 30 | +0 | 0.000 % |
| `queued` | 3 | 3 | +0 | 0.000 % |
| `running_missions` | 30 | 30 | +0 | 0.000 % |
| `held` | 16 | 16 | +0 | 0.000 % |
| `stale_claims` | 0 | 0 | +0 | — |

## ④ 结果图

![](fig1_pulse_trend.png)

![](fig2_verification.png)

![](fig3_state_reconciliation.png)

## ⑤ 注意点（踩过的坑 / 局限）

1. **worker 表不记录占用**：落库时刻全部 `factory_resident_workers` 行 `state='idle'`、`current_mission_id IS NULL`，而 30 条 mission 在 running 且心跳新鲜。
   若只读 worker 表得到 `online=24/busy=0`（满载舰队报 busy=0）→ 必须并入活 claim；这是本节点最重要的定标决策（见 Fig.3）。
2. **`online` 与工厂 API 的 `agents.online` 不是同一个定义**（API 用 90 s 窗口且不并集），两条序列不可混用。
3. **DDL 注释里的分号会切坏语句**：最初按 `;` 切 SQL 文件，注释里的分号被切成假语句 → 语法错。
   修法：先按行剥 `--` 注释再切分；`--ensure-schema` 重跑两遍验证幂等（已入测试与证据）。
4. **psycopg3 在事务中拒绝改 `read_only`**：连接若带着一次隐式事务交付（`SELECT 1` 之后），`conn.read_only=True` 抛 `ProgrammingError: can't change 'read_only' now: INTRANS`。
   修法：进入只读块前若 `transaction_status != IDLE` 先 rollback。
5. **`pg_locks` 里的 virtualxid 会伪装成"有锁"**：每个在事务中的 backend 都持有 virtualxid 的 ExclusiveLock；证据必须过滤 `locktype='relation'`，否则误报"锁表"。
6. **pytest 汇总行是 `23 passed, 1 warning`**：按 token 找 `passed` 会漏（token 是 `passed,`），改用正则 `(\d+) passed`。
7. **样本秒级相邻时数值完全相同**（本轮多条 00:50 样本 online=52/busy=32）：无平滑/de-dup，**相邻两行不等于两次独立稳态观测**。
8. **`held` 源自节点状态而非放行阀模型**：只统计 `held/blocked` 节点，不重实现派发策略；`released` 是相邻两次采样的状态差集，不是"阀会放行的集合"。
   且 `campaign_plan_nodes` 目前全为 `planned`（陈旧），held 实际来自 `campaign_nodes.blocked`（16 个）。
9. **未接入冻结的 harness**：按冻结纪律只做工具（手工或 cron `*/5 * * * * python3 -m tools.pulse.saturation_pulse --commit`），未新增任何 API 端点、未改 `backend/`、`api/`、`ops/`。

## ⑥ 误差判定（逐项 vs 基准，显式回答"是否<3%"）

| 关键量 | 基准 | 实测误差 | 是否 <3% |
|---|---|---|---|
| online | 独立手写 SQL | delta=+0，相对误差 0.000 % | **是** |
| busy | 独立手写 SQL | delta=+0，0.000 % | **是** |
| queued | 独立手写 SQL | delta=+0，0.000 % | **是** |
| running_missions | 独立手写 SQL | delta=+0，0.000 % | **是** |
| held | 独立手写 SQL | delta=+0，0.000 % | **是** |
| stale_claims | 独立手写 SQL | delta=+0（真值 0，相对误差不适用） | **是** |
| dry-run 快照 vs commit 快照 | 同一固定时刻 | 逐字段完全相同（dict 与 note 字符串均相等） | **是（精确相等）** |

**关于"<3%"的显式声明**：本节点是**遥测/度量管线**，不存在实验或文献参考值可比对，因此"vs 实验/参考值误差 <3%"这一条**不适用（NOT APPLICABLE）**——不拿"计算精确相等"冒充"物理精度达标"。
替代判据有二：(a) 可复算恒等性（dry-run ≡ commit，逐字段相等）；(b) 与独立 SQL 真值对账（6/6 指标 delta=0）。
**局限**：`busy`/`online` 的**定义**本身是建模选择（活 claim 窗 150 s、心跳窗 300 s），定义改变会改变数值；该定义与工厂 API 对齐，但未与任何"线缆级真值"（如 worker 进程 CPU/占用表）对标——平台上不存在这样的真值表，故如实记录为未覆盖项。

## 审计链

- 采集器/报表/证据/DDL/测试路径：`tools/pulse/{saturation_pulse,pulse_report,acceptance_evidence,gen_pulse_figures}.py`、`tools/pulse/sql/001_saturation_pulse.sql`、`tests/pulse/test_saturation_pulse.py`
- 证据：`artifacts/m4959/acceptance_IN15-O1.json`（判据数字+产物路径）、`cross_check_psql.json`、`pulse_samples.jsonl`（追加式样本日志）、`pytest_pulse.txt`、`fig1..3.png`
- 复现命令：`python3 -m tools.pulse.acceptance_evidence --samples 2 --interval 4`（`--dry-run` 只打印计划）
- 冻结面：`backend/` `api/` `ops/` 零改动；唯一 schema 动作=新增/幂等确认 `saturation_pulse` 表
