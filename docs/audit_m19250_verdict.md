# m19464 交差审计报告：m19250 KPI-KB-VERIFY-RATE

## 审计对象
- **Mission**: m19250 (KPI-KB-VERIFY-RATE · 知识验证通过率 · TensorKnowledge)
- **Repo**: TensorKnowledge
- **Branch**: agent/m19250
- **Status**: succeeded (claimed)
- **审计任务**: m19464 (交差核验单)

## 取证结果

### ① 验收三件套核验

| 项目 | 状态 | 证据 |
|---|---|---|
| run_artifacts | ✅ 存在 | agent/m19250:runs/kpi_kb_verify_rate/ 共 11 文件（result.json, snapshot.json, KPI-KB-VERIFY-RATE.md, 3 PNG 图, 4 TSV 数据, figures_manifest.json） |
| benchmark ref vs got | ⚠️ 自声明存在，**平台裁判缺位** | benchmarks/kpi_kb_verify_rate/bench_results.json 三层 ref-vs-got 0 偏差全绿；但 **tensor_benchmark_cases WHERE anchor_slug='KPI-KB-VERIFY-RATE' = 0 行**（平台唯一裁判无此锚点条目） |
| repro_cmd 可执行 | ✅ 通过 | result.json.repro_cmd 5 条（collect/measure/verify/bench/pytest）——审计实测：measure→0/5338, verify→all pass, bench→tier A/B pass, pytest→26 passed |

### ② 报告六段核验（tensor_reports#17676）

| 要素 | 状态 |
|---|---|
| ①案例介绍 | ✅ 完整（KPI 口径与数据面，分子/分母/目标定义冻结） |
| ②方法流程 | ✅ 完整（采集→算核→双路径复核→三层基准→工件） |
| ③计算结果 | ✅ 完整（数字表，程序化注入零手抄：0/5338=0.00%） |
| ④结果图 | ✅ 3 张 PNG（fig1_funnel / fig2_sensitivity / fig3_data_quality） |
| ⑤注意点 | ✅ 完整（分母质量/证据层/验证单通道/口径敏感性/只读边界） |
| ⑥误差判定 | ✅ 完整（逐项显式回答<3%，计数类精确 0 偏差；目标未定标无基准可判） |

### ③ 基准裁判核验（tensor_benchmark_cases —— 唯一裁判）

```
SELECT case_name, metric, tolerance FROM tensor_benchmark_cases WHERE anchor_slug='KPI-KB-VERIFY-RATE'
=> 0 行（表共 118 行 / 82 锚点，KPI-*/KB-* 锚点均无条目）
```

**关键发现**：m19250 的「L4 三层 ref-vs-got 基准」是**自声明**基准（写在自身 benchmarks/kpi_kb_verify_rate/），**未登记**进平台权威 `tensor_benchmark_cases` 裁判表。m19250 报告第⑦节**自行披露**此缺口：
> `GAP-KPI-BENCH-REFEREE` | major | 机器裁判缺位：tensor_benchmark_cases 对本锚点 0 行 | `benchmark_cases_for_anchor(0) == 0`

并提议派生锚点 `CASE-KPI-KB-VERIFY-RATE-BENCH`（在 tensor_benchmark_cases 登记）。**报告好看不算数，基准判据是唯一裁判**——L4 不可由平台裁判裁定。

## 判级（L0-L5）

**verdict: L3（系统集成）**

| 级别 | 判定 | 理由 |
|---|---|---|
| L0 文档成果 | ❌ | 有真实代码实现 |
| L1 数学/单元验证 | ✅ | 26 项 pytest（0/0→null、分子>分母拒绝、指纹绑值、只读护栏） |
| L2 独立功能实现 | ✅ | tools/kpi_kb_verify_rate/ 真代码：输入(PG)→计算→输出(result.json)，CLI 入口 |
| L3 系统集成 | ✅ | .github/workflows/kpi-kb-verify-rate.yml（CI 闸门消费 result/bench）+ tensor_reports#17676 发布 |
| L4 基准验证 | ❌ | **tensor_benchmark_cases 无本锚点条目（0 行）**——平台裁判缺位，自声明三层基准不构成平台级基准验证 |
| L5 科研工程成果 | ❌ | 未达 L4 故不评 L5 |

**降级说明**：m19250 声称「L4 三层 ref-vs-got 基准全绿」，但平台唯一裁判 `tensor_benchmark_cases` 对本锚点 **0 行**（本单自报 GAP-KPI-BENCH-REFEREE major）。三层 ref-vs-got 属**自声明/自建基准**（口径语义+scratch 库+活库双路径），非平台登记基准，故判 L3 而非 L4。与 m19050（L2）相比，m19250 返修轮补齐了 CI 集成调用方（L3），但基准登记缺口仍未闭合。

## 落表

```sql
INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by)
VALUES ('TensorKnowledge', 'm19250 KPI-KB-VERIFY-RATE', 19464, 3, '<JSON>', 'board-audit');
```

已执行，rowid=786。maturity_gate 自动裁定：**reopened**（L4 基准登记缺口未闭合，需在 tensor_benchmark_cases 登记本锚点后方可消账）。

## 审计独立性说明
- 审计基于 agent/m19250 分支内容（git archive 提取至 /tmp/m19250_audit 独立复算），非 m19250 工作树（越界）。
- 所有数字由审计自身复算（pytest 26 passed、bench tier A/B、measure/verify）或读自平台库（tensor_benchmark_cases 0 行）。
- 未运行：Tier C 活库双路径（需平台库，本节点不可达，标 not_run）。
