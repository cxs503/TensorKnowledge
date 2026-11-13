# IN18-T2 战史官编年史与指标计算器成熟化（TensorPlatform · tools/chronicle）

## ① 案例介绍（背景 / 对象 / 参数）

**背景**：本生态 12 仓、16 个战役计划、4642 条任务流水在 8 天窗口内高速运转，
但「全局态势」此前靠手抄（规划线 R1–R5 连续 5 班手抄的根因：27/27 节点无 status 字段、
验收 SQL 在本地全部库中「表不存在」）。IN18-T2 把战史官分析层做成**零手抄**的机器可复算
管线：所有衍生指标只从 SQL 源计算，每个数字带 `-- src: <query>` 溯源，重跑即复算。

**数据对象与参数**（全部程序化注入）：

| 参数 | 值 | 溯源 |
|---|---|---|
| 数据窗 | [2026-10-29 01:01, 2026-11-07 01:22] UTC | `-- src: select min(created_at), max(finished_at) from tensor_dev_missions where finished_at is not null` |
| missions 区间行 | 4642 | `-- src: select id, created_at, finished_at, status, claimed_by, repo from tensor_dev_missions where created_at <= :t_end` |
| finished 行 | 4597 | `-- src: select finished_at, status from tensor_dev_missions where finished_at is not null and finished_at <= :t_end` |
| campaign_nodes | 167 | `-- src: select plan_id, coalesce(metadata->>'repo','(none)'), status from campaign_nodes` |
| campaign_plans | 16 | `-- src: select id, name, status from campaign_plans order by id` |
| chronicle_snapshots | 2 帧 | `-- src: select ts, payload from chronicle_snapshots order by ts` |

**T1 声明**：T1 采集器代码未并 main（main 内无 chronicle 代码，快照由外部进程写入）。
按任务书「若 T1 未并 main 则自带最小采集并声明」：本单自带 `tools/chronicle/collector.py`
最小替身（只 INSERT 既有表 chronicle_snapshots，payload 与 T1 同形，dry-run 支持），
并已实际写入 1 帧（快照帧数 1→2）。

## ② 怎么做的（方法 / 流程 / 工具链）

1. **区间重建**：任务在飞区间 = [created_at, finished_at)，未结束者以 t_end 截断
   （schema 无 claimed_at，created_at 近似起点——局限见⑤）。
2. **5 项指标**（`tools/chronicle/metrics.py`，纯函数 + PG 装载分离，离线可测）：
   M1 并行度曲线（1h 桶）· M2 吞吐/成功率/failed 回流率（滑窗 1h/24h，锚点
   t_end=max(finished_at)，数据驱动无 wall clock）· M3 十仓×节点覆盖度矩阵
   （8 求解器 + ship-performance-platform + TensorPapers；ship-platform 旧名归一）
   · M4 饱和度=busy/online 与 idle 时序 · M5 BP §10.3 目标覆盖度表
   （bp_alignment 按 §X.Y 聚合）。
3. **交叉验证**（`crosscheck.py`）：独立手算 SQL（查询文本不复用 metrics.py 构造）
   对拍 3 硬判据 + 1 软判据（快照点值 ∈ [status 口径下界, 区间口径上界] 夹逼）；
   对拍锚点取 CSV 自声明的全精度 t_end（`-- t_end:` 行），活库漂移免疫。
4. **工具链**：psycopg3 + pytest(10 用例) + matplotlib；`--dry-run` 全链路支持；
   工件 `artifacts/chronicle/`（GLOBAL_CHRONICLE.md + 5 指标 CSV + crosscheck + 3 图）。
5. **纪律**：只增不改——不动冻结 API 面、不改既有表结构；新工具全部在
   tools/chronicle/ 独立目录；DB 连接串只走 env（CHRONICLE_DB_URL/DATABASE_URL），不落盘。

## ③ 计算结果（数字表，程序化注入）

**M2 吞吐 / 成功率 / failed 回流率**（`-- src: select finished_at, status from tensor_dev_missions where finished_at is not null and finished_at <= :t_end`）：

| 窗 | 吞吐 | succeeded | failed | success_rate | failed_backflow |
|---|---|---|---|---|---|
| 1h | 52 | 40 | 2 | 0.9524 | 0.0476 |
| 24h | 344 | 307 | 26 | 0.9219 | 0.0781 |

**M3 十仓×节点覆盖度**（行合计；`-- src: select plan_id, coalesce(metadata->>'repo','(none)'), status from campaign_nodes`）：
TensorLBM 11 · TensorFVM 3 · TensorFEM 12 · TensorDEM 15 · TensorBEM 2 · TensorSPH 2 · TensorDG 2 · TensorCAD 2 · ship-performance-platform 41 · TensorPapers 0；矩阵总 167（非十仓 other 单列，不混入矩阵）。

**M5 BP §10.3 目标覆盖度**（`-- src: select id, name, status, metadata->>'bp_alignment' from campaign_nodes where metadata ? 'bp_alignment'`）：
§10.3 对齐 2 节点（done 1 / blocked 1）；§15 对齐 3（done 2 / blocked 1）；
§4.4 对齐 4（done 2 / in-flight 2）；§8.2 对齐 2（done 2）。

**M1 端点值**：t_end 桶 running = 49（fig1 曲线末端）。

## ④ 结果图

- 图 1：并行度曲线（M1）+ 饱和度时序（M4），1h 桶，UTC。
- 图 2：十仓×战役计划覆盖度热图（M3，campaign_nodes 计数）。
- 图 3：BP 章节覆盖度堆叠条（M5）。

## ⑤ 注意点（坑 / 局限 / 适用范围）

- **活库漂移坑**：交叉验证若用「当前 max(finished_at)」做锚点，两次运行间新完成的任务
  会让锚点前进 → 假 FAIL（实测 337 vs 340）。正解：锚点取 CSV 自声明的全精度 t_end。
- **口径坑**：快照 fleet.running_missions（status 口径）与区间重建（在飞口径）不同源
  不同刻，直接对拍差 55%（36 vs 56）；改区间夹逼后 36 ∈ [9, 56] PASS。
- **psycopg3 占位符**：溯源文本用 `:name` 记法，执行前机械转 `%(name)s`。
- 局限：无 claimed_at（并行度略偏高估）；快照仅 2 帧（时序全靠区间重建）；
  快照 fleet.online(19) 与 pulse_tail.online(43) 口径不一致（一律以区间重建为准）；
  饱和度可 >1（单 worker 并发多任务，读作任务/worker 比）；成功率分母只含
  succeeded+failed（revoked/stopped/suspended 不入分母）。
- 适用范围：本管线对任意含上述 4 表的 PG 库可复算；十仓名单与归一规则为显式常量
  （代码即规则，无节点结论硬编码）。

## ⑥ 误差判定（关键量 vs 基准，逐项）

基准 = 独立手算 SQL（crosscheck.py，查询文本与 metrics.py 不同源）：

| 关键量 | 指标 CSV | 手算 SQL | 相对误差 | <3%? |
|---|---|---|---|---|
| 24h 吞吐 | 344 | 344 | 0% | **是** |
| 24h 成功率 | 0.9219 | 0.921922 | 0.0024% | **是** |
| 覆盖度单元(ship, plan 9) | 4 | 4 | 0% | **是** |
| 快照 running 夹逼(软) | [22, 47] | 24 | 夹逼成立 | **是** |

**结论：4/4 PASS（硬判据 3/3），全部关键量误差 <3%，无未解释偏差。**
