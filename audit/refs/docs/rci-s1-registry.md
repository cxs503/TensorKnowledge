# KBM-RCI-S1-REGISTRY · 报告资产盘点（Research Asset Registry）

> 锚点 `KBM-RCI-S1-REGISTRY`｜快照 `m15810@2026-11-11T20:00:31Z`｜行数 **9446**｜裁判：`rci_pipeline.py verify` + `verify_db.py`（两者均机器重算，手改即红）

## ① 问题设定与基准出处

TensorKnowledge 的第一个正式工程 *Research Corpus Intelligence* 的阶段 1：把平台 `tensor_reports` 里的全部 **9446** 篇 published 报告变成可检索/可关联/可验证/可复用的资产账。三铁则（owner 原令）：报告自动入库≠知识；知识必须加工；科学结论必须验证。

**基准（ref）出处**：

- 数量基准 `9446` = 任务书头条数字；本快照以 `created_at <= 2026-11-11 20:00:31.841339+00` 钉死，SQL 复算 `count(*) = 9446`（**逐字相等**）。实时库当前 published = 9993（漂移 +523 篇，属正常增长，账不混算）。
- 清洗判决基准 = KBM-CLEAN-W1 报告面账本 `runs/cleaning-w1/reports/ledger.jsonl`（9504 条，`sha256=72a287560c0bf868…`），本单只消费不重造（协同勿重复造清洗）。
- 方法谱系（external_anchor）：Broder 1997 «On the resemblance and containment of documents»（MinHash 相似度）；Indyk & Motwani 1998 STOC（LSH 分带索引）；Charikar 2002（SimHash，本轮未采用，理由见 §⑤）；W3C PROV-O 2013（溯源三元，字段命名对齐）；`datasketch` 库的 MinHash+LSH 惯例参数（b×r 分带、J≥0.5 门限）。
- 开源横向调研（`oss_inventory` feature 检索 `%REGISTRY%`）：**0 命中**；本机 `~/oss-cache` 仅 3 个 LBM 仓，集群侧同类检索见 cj1186 —— 横向无现成结构可抄，故方法自文献谱系落地（如实记录，不编造对标）。

## ② 方法与实现

四段流水线（纯 stdlib，loong64 安全；数字全部程序化产出）：

| 步 | 脚本 | 做什么 | 关键代码指针 |
|---|---|---|---|
| 1 | `build_data.py` | 钉快照导出 reports/missions CSV + 消费 W1 清洗账本 + 工件三件套探针 | `dump_csv` / `probe_worktree` |
| 2 | `rci_pipeline.py shard` | 逐报告：长度/图/tag、`md_sha256`、标题归一、数字掩码骨架、5-gram MinHash-128、数字集、四类分型、真实执行重合率 | `gram_hashes` / `minhash_sig` / `classify` |
| 3 | `rci_pipeline.py merge` | 并查集：exact-sha ∪ title ∪ skeleton ∪ LSH 候选(J≥0.5 复算)；簇号；六维质量位；汇总 | `run_merge` / `DSU` |
| 4 | `verify_db.py` + `load_registry.py` | 落库 `rci_asset_registry` 后 17 个聚合 DB↔工件全等复核 | `checks{}` |

**分型规则（标题→任务 goal→正文信号 级联，规则号入库）**：

- `R2_title_research` → 2734
- `R5_goal_creative` → 2591
- `R1_title_creative` → 1833
- `R4_title_info` → 806
- `R3_title_analysis` → 770
- `R0_clean_excluded` → 325
- `R6_goal_research` → 141
- `R9_bench_ref` → 106
- `R10_table_numbers` → 80
- `R7_goal_analysis` → 34
- `R8_goal_info` → 18
- `R11_numbers` → 8

## ③ 参数表

| 参数 | 值 | 说明 |
|---|---|---|
| 快照 T_pin | `2026-11-11 20:00:31.841339+00` | 9446 篇 published 的冻结时刻 |
| GRAM / 窗口 | 5 / 50000 | 5-gram，正文尾窗 50k 字符（控成本，见 §⑤） |
| MinHash | N_PERM=128，BANDS=16×ROWS=8 | 128 排列，16×8 分带（保守召回） |
| 精确门限 | J ≥ 0.5 | LSH 候选再算真 Jaccard |
| 真实执行门限 | 数字交集/报告数字集 ≥ 0.5 → verified | 阈值在 `run_shard` 常量 |
| 分片 | 24 分片（id % n） | 分区无关性见 §⑤ |
| 工件三件套定义 | wt_exists → artifacts|runs 有文件 → repro 入口 | 三真才 `triple_ok` |

## ④ 对照表（ref vs got，判据逐条打勾）

| 判据 | got（程序化） | 判定 |
|---|---|---|
| A1 覆盖 9446 篇（数量） | 9446 | ✅ |
| A2 四类分型覆盖 100% | info=1149 + research=2981 + analysis=892 + creative=4424 = 9446 | ✅ |
| A3 分型有可复算规则（无未命中） | R12_fallback=0 | ✅ |
| A4 项目/领域来源（repo/scenario_key） | repo 非空 9355/9446, scenario 非空 6378 种 | ✅ |
| A5 任务链关联（mission_id→tensor_dev_missions） | 有 mission 9365/9446, 任务行 7718, 悬空 10 | ❌ |
| A6 真实执行标记覆盖 100% | no_mission=91 + partial=8326 + verified=863 + zero_overlap=91 + no_numbers=62 + no_result=13 = 9446 | ✅ |
| A7 重复簇 + 空洞账 | clusters=763, dup_reports=2174, failed_empty=1737 | ✅ |
| A8 落库一致性（DB vs 工件） | 17 聚合全等（verify_db.py） | ✅ |

**分项数字（同一快照）**

| 维度 | 分布 |
|---|---|
| asset_type | info=1149, research=2981, analysis=892, creative=4424 |
| clean_decision | excluded=388, kept=7172, repaired=1886 |
| real_exec_flag | no_mission=91, partial=8326, verified=863, zero_overlap=91, no_numbers=62, no_result=13 |
| 重复簇 | clusters=763, reports_in_clusters=2174, excess=1411, largest=66 |
| 空洞/失败账 | no_artifact=1589, clean_X06_process_log=140, clean_X02_empty_or_stub=185, no_numbers=78; failed_empty=1737 |
| 任务状态 | <none>=91, succeeded=8899, awaiting_pr_merge=27, stopped=101, failed=182, revoked=146 |
| repo（前 8） | TensorPlatform=2601, ship-performance-platform=2009, TensorLBM=1160, TensorDEM=755, TensorFEM=465, TensorBEM=423, TensorPhysics=380, TensorPapers=373 |

## ⑤ 敏感性 / 两分辨率

**(a) 去重门限扫描**（同快照、同 LSH 候选，仅动精确门限）：

| gate | LSH 候选 | 通过对数 | 簇数 | 簇内报告 | 冗余(excess) | 最大簇 |
|---|---|---|---|---|---|---|
| 0.4 | 4253 | 4253 | 764 | 2176 | 1412 | 66 |
| 0.5 | 4253 | 4251 | 763 | 2174 | 1411 | 66 |
| 0.7 | 4253 | 4195 | 758 | 2161 | 1403 | 65 |
| 0.0 | 4253 | 4253 | 764 | 2176 | 1412 | 66 |

- 主结论取 gate=0.5（与 merge 一致）：簇 763，簇内 2174 篇 → **冗余 1411 篇**，即账面上至少 15% 的“报告”是重复劳动。
- 0.4 与 0.7 两点的差给出了阈值的有效区间：门限放松只增候选不增真簇 → 主结论对阈值不敏感。
- 未采用 SimHash：其汉明距离阈值（≤3/64）与本文“结构去重”目标对齐度不如 MinHash 的集合相似度，且 MinHash 可直接给出 Jaccard 可解释量（负面可选方案留档）。

**(b) 两分辨率（分区无关性）**：主跑 24 分片（`id % 24`）；同代码 8/16 分片重跑给出相同簇数与相同分型计数（由 `_agg` 从行级重算，与分片数无关；verify 在行级复算 27 个聚合，任一不等即 exit 1）。

**(c) 抽样深核**：按 real_exec_flag 分层、每层等距抽 72 篇，逐篇列出报告数字 top-15 与其在 `tensor_dev_missions.result` 中的命中（`deep_dive.json`，层规模 {"no_mission": 91, "partial": 8326, "verified": 863, "zero_overlap": 91, "no_numbers": 62, "no_result": 13}）。整体重合率 n=9280, mean=0.2413, p50=0.1914, p90=0.4839, max=1.0000。

## ⑥ 失败模式与工件

**失败模式（本轮实测，写下来防复犯）**

1. 前轮 m15460 死法 = `budget_exhausted`：串行全量扫 + 无中间 checkpoint，跑到 02:04 仍无落库。本轮对策：分片并行（24 分片 128 核实测 94s）+ 每步落文件 + 落库幂等 upsert。
2. 时间戳空串 → COPY 报 `invalid input syntax for type timestamptz`：LOAD 侧按列白名单转 `\N`。
3. `psycopg2` 在 loong64 是 stub（无真驱动）→ 全链路改走 `psql` COPY，脚本零第三方依赖。
4. 钱数级坑：`dup_reports_in_clusters` 若对 `dup_cluster_size` 求和会**重复计数**（9459→2174），已改为“簇内有行数”，并单列 `dup_excess_reports`。
5. `reports_csv_rows` 用换行计数会因正文内换行虚高 140×（1321483→9446），改 `csv.reader` 计数。

**工件与复跑**

```bash
# 1) 钉快照导出（约 9s）
python3 runs/rci-s1-registry/build_data.py --out /tmp/rci-s1/data
# 2) 24 分片并行（约 95s，128 核）
bash /tmp/rci-s1/run_shards.sh 24   # 等价: rci_pipeline.py shard --shard i --n 24 --data ... --out ...
# 3) 合并 + 分片内聚合复核
python3 runs/rci-s1-registry/rci_pipeline.py merge  --data /tmp/rci-s1/data --shards /tmp/rci-s1/shards --out /tmp/rci-s1/out --snapshot m15810@2026-11-11T20:00:31Z
python3 runs/rci-s1-registry/rci_pipeline.py verify --out /tmp/rci-s1/out
# 4) 落库 + DB↔工件 17 聚合对拍
python3 runs/rci-s1-registry/load_registry.py  --rows /tmp/rci-s1/out/registry_rows.jsonl
python3 runs/rci-s1-registry/verify_db.py --summary /tmp/rci-s1/out/summary.json --out /tmp/rci-s1/out/db_extras.json
# 5) 敏感性 + 报告渲染
python3 runs/rci-s1-registry/sensitivity.py --shards /tmp/rci-s1/shards --out /tmp/rci-s1/out/sensitivity.json
python3 runs/rci-s1-registry/gen_report.py --out /tmp/rci-s1/out --figdir runs/rci-s1-registry/figures --doc docs/rci-s1-registry.md
```

| 工件 | 路径 | 内容 |
|---|---|---|
| 行级资产账 | `runs/rci-s1-registry/out/registry_rows.jsonl.gz` | 9446 行全字段（= 落库同源） |
| 聚合 | `runs/rci-s1-registry/out/summary.json` | 27 聚合（verify 重算） |
| DB 对拍与分项 | `runs/rci-s1-registry/out/db_extras.json` | SQL 侧重算 + 分项 |
| 敏感性 | `runs/rci-s1-registry/out/sensitivity.json` | gate 0.4/0.5/0.7/LSH-only |
| 抽样深核 | `runs/rci-s1-registry/out/deep_dive.json` | 分层抽样逐篇数字命中 |
| 快照台账 | `runs/rci-s1-registry/out/inputs_manifest.json` | 输入 sha256 + 行数 + 漂移 |
| 落库表 | `tensorplatform.rci_asset_registry` | 9446 行，PK report_id，FK→tensor_reports |

**局限**：q_accuracy / q_reusability / q_freshness 三维为 NULL 占位（S2 才做）；真实执行只做“数字重合”代理而非逐条重算（重算属 benchmark 面）；正文尾窗 50k 字符以外的重复判定盲区未量化。

## 结果图

![四类分型与清洗判决分布](runs/rci-s1-registry/figures/fig1_typing_clean.png)

![真实执行标记与报告/任务 result 数字重合率分布](runs/rci-s1-registry/figures/fig2_real_exec.png)

![重复簇规模分布与 Jaccard 门限敏感性](runs/rci-s1-registry/figures/fig3_duplicates.png)

![工件三件套漏斗与正文长度分布](runs/rci-s1-registry/figures/fig4_traceability_length.png)
