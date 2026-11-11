# m15247 · 交差核验：m15181 / KBM-CONSUME-W1（KB 消费研究 v1）

- 核验对象：mission 15181（TensorKnowledge，status=succeeded，2026-11-11 20:18:06），交付 = 3 脚本 + 2 类工件 + 1 份设计文档 + 报告 id=14295
- 核验单：m15247（本单，board-audit 席位），工作树 `/root/tp-agent/work/m15247`，分支 `agent/m15247`
- 唯一裁判：`tensor_benchmark_cases` 注册行 + 平台 `tensorbench_results` 复算行（报告好看不算数）
- 复核工具（本单新增，零手抄）：`scripts/m15247_audit_kbm_consume.py` → `artifacts/audit_m15247/{evidence.json,checks.json,fig_ab_passrate.png}`；
  落表 `scripts/m15247_verdict.py` → `tensor_maturity_verdicts` id=256

## ① 案例介绍（核验对象是什么）

m15181 是 **知识库消费研究**（不是求解器算例，无几何/无物理场）：diagnose「31 条 KB 卡为何全史仅注入 3 次、被引 2 次」，
再做调用级受控 A/B（3 臂 × 3 锚 × 4 重复 = 32 次主调用 + 12 次粒度子臂），最后给设计建议 R1-R8 + 计量快照。

| 项 | 值（取自工件，程序化注入） |
|---|---|
| 臂 | A=无 KB；B=被动注入整卡；C=主动检索（目录 + RETRIEVE 二轮） |
| 锚 | K1=ITTC-1957 C_F（闭式可判）；K2=平台纪律；K3=capability 卡事实（m14687 收敛率/力误差/等级） |
| 模型/温控 | qwen3.7-plus，temperature=0，确定性规则判分（无 LLM 裁判） |
| prereg 冻结 | sha256 `e90109f2…1f8254`，与实测复算**一致** |
| 主结果 | 臂通过率 A 0.333 / B 0.667 / C 0.667；K3 A 0/4→B 4/4；K3/B_long 4/4 vs B_short 0/4 |

## ② 怎么做的（核验方法）

1. `tensor_benchmark_cases WHERE anchor_slug='KBM-CONSUME-W1'` → **0 行**（全表 14 个 anchor，无 KBM-*）。
2. `GET /api/v1/tensor/bench/l4-verdict/15181` → `CLAIMED_NOT_PROVEN`，`rows=0`，`failed_checks` 五项全挂（执行/集群/绑定/ref-got/容差）。
3. 工件存在性 + sha256 重算（7 个文件全在）。
4. 复算：从 `results.jsonl`（44 行）逐格重算 15 个 cell 的 n/pass_rate，与 `summary.json` 对比 → **0 处不一致**（summary 未被手改）。
5. 判分器确定性：载入 `scripts/kb_ab_experiment.py` 的 `grade_*()`，对 44 条保存文本重跑 → 0 处翻转；同输入两次同输出；对故意偏离 5% 的数拒判。
6. 复现：`python3 scripts/kb_consume_audit.py --out <dir>` 实跑 exit=0；`injected_total=3`、`cited_total=2` 稳定复现。
7. 集成面取证：`kb_consumption_snapshots` 1 行；调度器/端点/CI 消费方 grep = 0；`pg_proc` 引用 = 0；`tests/` 覆盖 = 0。
8. 报告六段与显式「<3%」回答检查（`artifacts/kb_consumption/report_m15181.json`，markdown 9908 字符）。

## ③ 计算结果（核验数字表）

| 检查项 | 结果 | 证据 |
|---|---|---|
| 注册基准行 | **0 行** | SQL + `table_anchors` 14 项 |
| 平台 L4 复算行 | **0 行**（CLAIMED_NOT_PROVEN） | `/tensor/bench/l4-verdict/15181` |
| run_artifacts | 7/7 存在 | 见 evidence.json sha256 表 |
| prereg 钉扎 | 一致 | `e90109f2…` |
| A/B 逐格复算 | 44 行 / 15 cell / 0 不一致 | summary vs results.jsonl |
| 判分器重跑 | 0 翻转 + 判别力通过 | `grade_k1(0.0022 0.0016)=False` |
| repro_cmd | exit=0；计数事实稳定；3 个时变字段漂移 | 见 ⑤ |
| 集成消费方 | 0 | grep + pg_proc + tests |
| 报告六段 | ①-⑥ 全在，含「<3%」显式回答与无图理由 | markdown 检查 |
| 外部锚 | ITTC-1957 闭式独立重算 0.00208333 / 0.00153061 | 数学恒等式 |

## ④ 结果图

`artifacts/audit_m15247/fig_ab_passrate.png`：左=臂×锚通过率（n=4/cell），右=粒度子臂（整卡 vs 280 字符前缀摘要）。
图由 `scripts/m15247_audit_kbm_consume.py` 从 `results.jsonl`/`summary.json` 程序化生成（非手抄）。

## ⑤ 注意点（对手视角的缺陷清单）

- **F1 无基准行 → L4 不可判**：`KBM-CONSUME-W1` 没有注册 ref/metric/tolerance。m15181 报告也没有自称 L4/L5，属**未虚标**；
  但本仓历史 verdict 曾被批量判 0，需要按功能实质重新裁（本轮判 **L2**）。
- **F2 集成面薄**：`kb_consumption_snapshots` 只有 1 行且是手跑写入，无调度器/HTTP 端点/CI 消费方 → **不到 L3**。
  设计文档 §④ 的「周期快照进 chronicle」仍是方案，未实施。
- **F3 伪重复（方法）**：temperature=0 下 K1/A 的 rep0 与 rep1 文本/token/时延（12.35s）完全相同 → reps=4 近似复制，
  有效 n≈1；报告以 4/4、0/4 呈现但未给不确定区间。方向性结论（K3 无卡必编 → 有卡 4/4）不受影响，量级推断需谨慎。
- **F4 判分脆弱（低危）**：`grade_k3` 接受带 32.3±1.5pp，只覆盖卡内 4 个 level 的最小值（32.288/34.304/34.723/35.135）；
  只答 35.135% 的**正确答案会被判错**。实测 B 臂是整串引用故未被触发。
- **F5 计数时变**：本轮复跑 48 分钟后 `kb_total 31→38`、暴露分母 `132→209`、引用率 `1.52%→0.96%`。
  报告数字是带 `taken_at` 的快照值，不可当永久值引用；这正是「快照未进周期调度」的直接后果。
- **F6 已达标的诚实项**：K2 三臂 0/4 主动判无效锚并行文声明「不得据此评价纪律卡」；任务级双臂未跑如实标注；
  六段齐全、显式回答<3%、无图理由写明。

## ⑥ 误差判定（vs 基准）

| 关键量 | 基准 | got | 误差 | 是否 <3% |
|---|---|---|---|---|
| 注册基准 case 数 | ≥1（L4 前提） | 0 | 不适用 | **否**（无法对照，L4 判否） |
| 平台复算行 | ≥1 | 0 | 不适用 | **否** |
| K1 C_F(Re=1e8) | 0.00208333（ITTC 闭式） | 0.00208333（A/B/C 各 rep） | <0.01% | **是** |
| K1 C_F(Re=1e9) | 0.00153061 | 0.00153061 | <0.01% | **是** |
| A/B 汇总一致性 | summary.json | 逐格复算 | 0 处 | 是（一致性检验，非物理误差） |
| 计数事实复用 | audit 记录 | 本轮实跑 | injected 3=3、cited 2=2；kb_total 差 7 | 部分是（时变字段超容差） |

## 裁定

**L2**（独立功能实现：真代码 输入→计算→输出，可复跑、可复算、判分确定性）。
L3 未达（无平台消费方）；L4 不可判（无注册基准，且平台复算行 0）；L5 未达（调用级单模型对照 + 设计建议未实施）。
落表：`tensor_maturity_verdicts` id=256（repo=TensorKnowledge, scope='m15181 KBM-CONSUME-W1', mission_id=15247,
level=2, verdict_by='board-audit', gate_state=pending → 由常驻 maturity_gate 守护进程自动裁定）。