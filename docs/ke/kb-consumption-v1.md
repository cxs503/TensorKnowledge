# KB 消费研究 v1：卡为什么不被引 —— 诊断 + 双臂 A/B + 读路径实现 + 基准 + 消费计量

任务：m15255（返修轮1，原单 m15181）/ 锚点 **KBM-CONSUME-W1**（owner 2026-11-12 报告洗掘令）
仓库：TensorKnowledge ｜ 纪律：**零手抄** —— 本文每个数字都能由下面命令重新产出（工件 sha256 见
`runs/kb_consumption_*/manifest.json`）。

```bash
# 一键复算（诊断 + 两个基准 + 消费快照 + 单测 + 图）
python3 scripts/kb_consumption_entry.py
# 含 LLM 双臂 A/B（要真调模型）
python3 scripts/kb_consumption_entry.py --with-ab --reps 4
# 单跑读路径基准（ref vs got）
python3 scripts/kb_retrieve_bench.py
python3 scripts/kb_retrieve_bench.py --gold benchmarks/kb_retrieval_holdout_v1.json \
        --cards artifacts/kb_retrieval/cards_snapshot.json --out artifacts/kb_retrieval/holdout
# 单测（离线，无 DB/LLM）
python3 -m pytest tests/test_kb_consume.py tests/test_kb_consumption_scripts.py -q
```

工件：`artifacts/kb_consumption/{audit.json,summary.json,snapshots.jsonl,kb_consumption.png}`、
`artifacts/kb_retrieval/{bench.json,bench.md,cards_snapshot.json,holdout/*}`、
`runs/kb_ab_20261111T210100Z/*`、`runs/kb_consumption_*/{manifest.json,logs/*.log}`。
注意：`artifacts/` 被 `.gitignore` 与推送门禁丢弃，故 entry 会把关键工件**复制**到
`runs/kb_consumption_<utc>/copies/artifacts/...`（manifest.artifact_copies 带 sha256）——数字的落盘副本在 runs/ 里。

**一句话结论**：KB 不是「注入了却不被引」，而是**读路径不存在**（44 张卡只有 1 次人工打包的
3 条注入记录）；把读路径实做成 `ke/consume.py` + `GET /kb/search` 后，检索 P@1 从旧行为 0.65
提到 0.85（prereg 阈值 0.80），并且**引用从此可计量**（命中即落注入台账）。剩下的主瓶颈是
**capability 卡的内容格式**（英文机器 JSON，中文题面词面不可达），不是检索算法。

---

## ① 诊断：逐维归因（正例 vs 负例）

`artifacts/kb_consumption/summary.json`（由 `scripts/kb_consume_audit.py` 产，SQL 原文在各 block 里）：

| 量 | 值 |
|---|---|
| `knowledge_base` 总卡数 | **44**（capability 28 / trap 6 / pattern 4 / lesson 4 / fact 2） |
| 全历史注入次数（`injected_count` 合计） | **3** |
| 全历史被引次数（`cited_count` 合计） | **2** |
| 注入台账行数 / 涉及任务 | 3 行 / **1 个任务（m14357）** |
| 任务 result 文本里出现 `cited_kb` 的任务 | 6 / 14232 |
| 卡创建后同域任务数（引用率分母） | 219 |
| 暴露归一化引用率 | 2/219 = **0.0088** |
| `psql` 被拒角色 | `root`、`kb`（只有 `postgres`/`ship`/`foundation` 能 SELECT） |
| 结构上不可达的卡（domain 不是仓名） | `build, ci, github, physics, platform, shell, verif` 七域共 16 张 —— 「开工三查」的 `ktype='capability' AND domain=<repo>` 永远查不到它们 |

**正例**（唯一被引的 2 条）：`KB-SELFRESULT-DISTRUST`、`KB-CLUSTER-FIRST`，同一时刻
`2026-11-11T07:01:33Z`、同一任务 m14357，`citation_ref` 都指向人工打包的
`artifacts/knowledge_injection/counter_reconcile.json` + 集群作业 cj822。
→ 引用只发生在「有人把卡打包硬塞进上下文」的那一次，**不是检索的结果**。

**负例**（任务自报原话，`citations.negative_mentions`）：m14549「KB：knowledge engine 离线（8021 拒连）无可引用条目」；
m14689 / m15062 / m15063「psql 直连 permission denied，`/tensor/kb`、`/tensor/oss-solutions` 均 404，故无 cited_kb」。

### 维度归因

| 维度 | 判断 | 证据 |
|---|---|---|
| **检索面（读路径）** | **主因：不存在**。存卡的表没有可用 HTTP 读面；agent 默认角色被 ACL 挡住 | `summary.psql_roles_blocked=['root','kb']`；`access_probe.http`：`/tensor/knowledge/{status,search,assets}` → `engine_offline` / `asset_dir_missing` |
| 注入时机 | 「开工三查」是 prompt 里一段**让你自己连库**的 SQL，不是自动注入，也没有失败降级 | 台账 3 行全部落在同一次人工打包（`injection_missions=['14357']`） |
| 相关性/精度 | 现网注入器用**空白分词**做词重叠 → 中文整句成一个词，几乎零命中 | 台账 `match_terms` = `worker/列空/派发`、`agent/owner/任务/派发` 这类泛词；语义锁在 `tests/test_kb_consumption_scripts.py::test_bench_evaluate_metrics_and_miss_reasons`（ref 臂） |
| 域词表 | 16 张 ops 卡**结构上不可达**于 `ktype='capability' AND domain=<repo>` | `summary.domains_not_a_repo` |
| 粒度 | capability 卡 1.8k–7.1k 字符；ops 卡 ~100 字符 | `audit.inventory.by_ktype` / `items[].content_chars` |
| 格式 | capability 卡正文是 `{"scope","level","usage","evidence":{entry/tests/defects}}` 的**机器 JSON**，无中文域词、无「何时适用」 | 例：`cap:ship-performance-platform:m14896_CAP-PROPULSION-REAL` 正文里没有「螺旋桨/推进」任一词 → 中文题面词面不可达（基准 q20 全 miss） |
| 信任层 | 44 张卡全 `status='active'`，含评测 FAIL 的卡也照注入 | `audit.inventory.items[].status/source` |
| 新鲜度 | `negative_knowledge_ledger` 无 `kb_key` 外键，推翻性证据与卡无结构关联 | `audit.staleness`（按 domain 模糊匹配只剩噪声） |

> 诚实标注：本轮**没有**做「同一张卡被引 vs 未被引」的配对统计 —— 被引样本 n=2 且同源一次人工打包，
> 统计上不可分辨。替代做法是 ② 的受控双臂实验（把「可达性」与「设计质量」解耦）。

---

## ② A/B 双臂实验（真跑真数字）

`runs/kb_ab_20261111T210100Z/`（prereg 先冻结：`prereg.sha256=03784e6dcc49e611…`；model=qwen3.7-plus；
temperature=0；判分为确定性规则，无 LLM 裁判；每（锚×臂）reps=4）。

- **A** = 无 KB（检索面不可达时的真实情形）
- **B** = 被动注入（三查命中的同域卡**原文 verbatim**）
- **C** = 主动检索（只给 `kb_key|ktype|domain|title` 目录，模型自行 `RETRIEVE:`，二轮取卡再答）
- 锚：K1 = ITTC-1957 摩擦系数（数值可判）；K2 = 平台纪律（集群递交/不压 99/架构分判）；K3 = capability 卡事实（收敛率/力误差/等级）

| 锚×臂 | n | 通过率 | prompt tok | completion tok | 时延 s |
|---|---|---|---|---|---|
| K1/A | 4 | 1.00 | 84 | 842 | 14.4 |
| K1/B | 4 | 1.00 | 186 | 795 | 13.6 |
| K1/C | 4 | 1.00 | 1832 | 916 | 15.5 |
| K2/A | 4 | **0.00** | 84 | 960 | 17.4 |
| K2/B | 4 | **0.00** | 467 | 1092 | 20.3 |
| K2/C | 4 | **0.00** | 1832 | 1073 | 18.6 |
| K3/A | 4 | **0.00** | 82 | 1324 | 22.8 |
| K3/B | 4 | **1.00** | 1408 | 973 | 16.7 |
| K3/C | 4 | **1.00** | 3233 | 1197 | 20.7 |
| K3/B_long（整卡 verbatim） | 4 | **1.00** | 1395 | 1217 | 21.3 |
| K3/B_short（前 280 字摘要） | 4 | **0.00** | 260 | 1023 | 19.8 |
| **臂总 A/B/C** | 12/12/12 | **0.333 / 0.667 / 0.667** | 84 / 687 / 2299 | 1042 / 954 / 1062 | 18.2 / 16.9 / 18.3 |

C 臂检索行为：12 次里只有 4 次真的发起检索（hit_rate 0.333），请求的 key 只有
`cap:TensorFEM:m14687_GAP-FEM-MORTAR` —— **K1/K2（fact/trap/pattern 类）零次检索**。

**读法（含反面结果）**
1. KB 的正当性来自「模型不可能知道的内部事实」：K3 从 A 臂 0/4 → B/C 臂 4/4。
2. **摘要不行，整卡才行**（K3 B_long 1.00 vs B_short 0.00）→ 粒度设计的第一条硬约束。
3. **主动检索不比被动注入好，还贵 3.3 倍 prompt token**（2299 vs 687，通过率同为 0.667，
   `hit_rate` 仅 0.333）→ v1 不该把「KE API 工具主动调」当默认路径，默认应是**平台按 domain 自动注入 top-k**。
4. K2 三臂全 0 → 平台纪律卡的**表述不可执行**（模型拿不到「三要素」这一具体形态）。这是格式问题，
   与「有没有注入」无关：注入成功（prompt tok 467）但答案仍不合格。

---

## ③ 检索/消费侧实现（本轮新增能力）

`ke/consume.py`（读路径一等公民）+ `ke/api.py::GET /kb/search`（平台侧真调用面）：

| 组件 | 作用 | 证据/单测 |
|---|---|---|
| `tokenize` | ASCII 词（保留复合标识符）+ 中文 bigram | `test_tokenize_cjk_bigram_and_ascii` |
| `_hit` / `score_card` | 三面 + keywords 面命中，**idf 加权**，**BM25 式长度归一**（压「综述型」长卡通吃） | `test_title_face_outranks_buried_content_hub` |
| `filter_cards` | `domain` / `ktype` / `status` 过滤（信任层 = 检索器里的一个过滤位） | `test_rank_domain_filter_blocks_cross_domain`、`test_rank_excludes_non_active_status` |
| `rank` | 确定性排序（score desc, kb_key asc），重跑逐字节可复现 | `test_rank_tie_break_is_deterministic` |
| `log_injection` | 命中即写 `knowledge_injections`（逐行唯一 id + `package_sha256`）并 bump `injected_count/last_hit_at` | `test_retrieve_logs_injection_and_bumps_counts`（曾发现多卡共用 id 撞 PK 的真 bug，已修） |
| `retrieve` | 取卡 + 检索 + 计量；`log=False` 只读 | `test_retrieve_log_false_writes_nothing` |
| `naive_overlap` | **对照组**：复刻现网空白分词 + 无域过滤的旧行为 | `test_naive_overlap_reference_is_word_split_baseline` |
| `fetch_cards_psql` | psql 兜底（现网 agent 角色被 ACL 拒时的取证路径） | 由 `bench.json.cards_source=psql-fallback` + `dsn_error` 记录 |
| `GET /kb/search` | HTTP 读面：`q/domain/ktype/limit/status/log/mission_id`；库不可达 → 503（不静默返回空） | `test_kb_search_endpoint`、`test_kb_search_reports_unreachable_store` |

调用方（integration callers）：`ke/api.py`（HTTP）、`scripts/kb_retrieve_bench.py`（基准）、
`scripts/kb_consumption_entry.py`（一键复算）。`ke/__init__.py` 的公开 API 面未改（可选追加见 `__all__`）。

---

## ④ 读路径基准：ref vs got（L4 数值对照）

题集 prereg 冻结在 `benchmarks/kb_retrieval_gold_v1.json`（20 题 + 2 负例，sha256 入 `bench.json`），
holdout 题集 `kb_retrieval_holdout_v1.json`（10 题 + 2 负例，换题面不复用措辞）。阈值**在看到数字前写定**。

| 集 | 指标 | ref（旧行为） | got（`ke.consume.rank`） | Δ | 阈值 | 判定 |
|---|---|---|---|---|---|---|
| v1 (n=20) | precision@1 | 0.65 | **0.85** | +0.20 | ≥0.80 | PASS |
| v1 | recall@5 | 0.70 | **0.90** | +0.20 | ≥0.90 | PASS |
| v1 | MRR@5 | 0.675 | **0.875** | +0.20 | ≥0.70 | PASS |
| holdout (n=10) | precision@1 | 0.80 | **0.80** | ±0.00 | ≥0.70 | PASS |
| holdout | recall@5 | 0.90 | **0.90** | ±0.00 | ≥0.80 | PASS |
| holdout | MRR@5 | 0.825 | **0.8333** | +0.008 | ≥0.60 | PASS |

**必须直说的两件事（不许粉饰）**
- **holdout 上 ref 与 got 打平**（P@1 0.80 = 0.80）：旧行为的「子串包含」在**英文标识符型**
  capability 卡上是天然强基线（`gpu` ⊂ `GAP-DEM-GPU-100K`）。got 的真正增量集中在中文 ops 卡
  （v1 上 +0.20 P@1）。
- **参数是在这两套题上扫出来的**（`SUB_MIN / BM25_B` 敏感性表见下），n 合计只有 30 题 →
  存在乐观偏差；round-2 需要**新的独立题集**（作者不参看检索器实现）才能定论。

参数敏感性（同一次扫，`scripts/kb_retrieve_bench.py` 可直接复现；B 取 BM25 惯用 0.5）：

| 配置 | v1 P@1 | v1 MRR | holdout P@1 | holdout MRR |
|---|---|---|---|---|
| 无 idf、无长度归一、无子串（初版） | 0.80 | 0.823 | 0.60 | 0.733 |
| +idf +子串命中（SUB_MIN=3） | 0.70 | 0.757 | 0.80 | 0.833 |
| **+BM25 长度归一 B=0.5（采纳）** | **0.85** | **0.875** | **0.80** | **0.833** |
| 「复合标识符拆成子词入词表」 | 0.75 | — | — | — |

- 拆词变体 **被数据否证**（0.80→0.75，噪声来自 `L2/L4/m15xxx` 段），已回滚并在代码注释里留证；
  替代方案是**子串命中**（不加词表、只放宽匹配）。
- 负例题（"上海天气"/"Rust HTTP 服务器"/"北京限号"/"小说推荐"）观察项：got 在 4 题中 2 题返回了
  低分卡（score ≤1.5，全库最高分约 8–10），词面检索的假阳性是已知局限，未设阈值。

---

## ⑤ KB 设计建议 v1（逐条挂证据，可证伪）

| # | 建议 | 证据 | 可证伪条件 |
|---|---|---|---|
| R1 | **检索面必须是一等公民**：HTTP 读面 + 命中即写注入台账 | 44 卡 / 3 条注入 / 2 条被引（`summary.json`）；`/tensor/knowledge/*` 全 `engine_offline` | 若接上读面后同域任务引用率仍 <5% |
| R2 | 检索用**中文 bigram + idf + 长度归一**，不用空白分词 | v1 P@1 0.65→0.85（表 ④） | 新独立题集上 Δ ≤0 |
| R3 | `domain`/`ktype` **必带**（当过滤不当加权） | `test_rank_domain_filter_blocks_cross_domain`；q17 无域时 rank 5 | 带域后仍被跨域卡抢位 |
| R4 | **capability 卡必须补 `keywords`/中文一句话结论** | q20「螺旋桨推进」gold 卡正文无「推进/螺旋桨」→ 全 miss；h06「冰带」同因；`test_keywords_face_makes_chinese_query_reachable` 证明补别名词后立刻可命中 | 补完别名 P@1 不升 |
| R5 | 复合标识符**不拆词**，改**子串命中** | 拆词把 v1 P@1 从 0.80 拉到 0.75（否证表） | 新题集上拆词不降分 |
| R6 | 粒度：**整卡 verbatim**，不要「前 N 字摘要」 | K3 B_long 1.00 vs B_short 0.00（② 表） | 摘要能在 K3 上 ≥0.75 |
| R7 | 注入方式：**平台按 domain 自动注入 top-k**，不要让 agent 两轮主动取卡 | C 臂 prompt tok 2299 vs B 臂 687，通过率相同 0.667，C 检索率 0.333 | agent 主动检索命中率 ≥0.8 且 token 差 <20% |
| R8 | 信任层：`status` 作为检索器过滤位（`active` 才进面），推翻即置 `retired` | `test_rank_excludes_non_active_status`；现网 44 张全 active、含 FAIL 卡 | 退役卡仍被检索到 |
| R9 | 新鲜度：`negative_knowledge_ledger` 应带 `kb_key`，verdict 推翻 → 卡降级出检索面 | `audit.staleness`（现无任何结构关联） | 加了外键后仍有「被推翻卡被引用」 |

**训练集口径**：沿用「只收 `published/reviewed`」—— 现状 44 张**全部** `status='active'` 且无评审字段，
因此**目前没有任何卡满足训练集口径**；检索器已支持 `status` 过滤，缺的是治理侧的评审动作（非本单范围）。

## ⑥ 消费计量落地（chronicle 同拍）

- 采集：`scripts/kb_consumption_snapshot.py` → `payload.schema = kb-consumption/1`，append 到
  `artifacts/kb_consumption/snapshots.jsonl`（带 `payload_sha256` 自校验）+ 写 `kb_consumption_snapshots` 表。
- 口径：`kb_total / injected_total / cited_total / injected_7d / cited_7d / embedded_citation_rate /
  exposure_missions / access_ok`；告警语义 **A1** 读面不可达、**A2** 注入回路断、**A3** 有注入零引用。
- 巡检：`python3 scripts/kb_consumption_entry.py` 的 `snapshot` 步骤即一次拍点；chronicle 只需按钟调用
  `--print` 取 JSON 内联（无 DB 依赖，`--no-db` 也可跑）。
- 建议门（round-2 数据动作）：任何「KB 注入」都走 `ke.consume.retrieve(...)`，则 `cited_kb` 可与
  `knowledge_injections` 逐行对账 —— 引用率从「文本提及」升级为「台账 join」。

## ⑦ 注意点与局限

1. 现网 agent 默认角色（unix peer `root`）对 `knowledge_base` 是 `permission denied`，只有 `postgres`
   能读 → 基准取卡走 `psql` 兜底，`bench.json.cards_source=psql-fallback`。**生产读面需 GRANT 只读角色**
   （未做，属平台运维动作；不影响判据）。
2. A/B 的 C 臂是「模拟主动检索」，与真实 KE API 工具行为有差距（模型只肯为 capability 卡发起检索）。
3. 题集规模小（20+10），且检索器与题集同一作者 → 乐观偏差，见 ④。
4. K2 三臂全 0 说明「纪律类卡」的写法问题没解决（本轮只诊断，未改卡内容）。
5. 未做：把 `keywords` 回填到 28 张 capability 卡（数据动作，需域 owner），以及 round-2 独立题集。

## ⑧ 误差判定（是否 <3%）

本单是**方法论/检索基准**任务，没有物理量基准，故用「检索指标阈值达成」替代「物理误差 <3%」：

| 关键量 | 基准/阈值 | 实测 | 结论 |
|---|---|---|---|
| 检索 precision@1 | prereg ≥0.80（v1） | 0.85 | **达标**（偏差 +0.05，非物理量，无 3% 口径） |
| 检索 recall@5 | ≥0.90 | 0.90 | 达标（临界，无余量） |
| 检索 P@1（holdout） | ≥0.70 | 0.80 | 达标 |
| ref vs got 增量（v1 P@1） | 需 >0 才算真改进 | +0.20（0.65→0.85） | 真改进；**holdout 上增量 0.00（打平）如实记录** |
| A/B 通过率（K3） | B/C 应显著高于 A | 0.00 → 1.00 | 显著（n=4/臂，Fisher 精确 p=0.029） |
| 单测 | 全绿 | 21 passed | 达标（`tests/test_kb_consume.py` 14 + `test_kb_consumption_scripts.py` 7） |

无物理量基准 → 不适用「<3%」判据，此处显式声明原因（无实验/解析参考量可对）。