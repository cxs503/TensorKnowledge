# KB 消费研究 v1：31 条卡为什么没人引（诊断 + 双臂 A/B + 设计建议 + 消费计量）

任务：m15181 / 锚点 KBM-CONSUME-W1（owner 2026-11-12 报告洗掘令：agent 消费研究——KB 如何被真用）
仓库：TensorKnowledge ｜ 证据源：本仓脚本产出（零手抄，全部可 SQL/工件溯源）
- `scripts/kb_consume_audit.py` → `artifacts/kb_consumption/{audit,summary}.json`
- `scripts/kb_ab_experiment.py` → `runs/kb_ab_20261111T201329Z/{prereg.json,prereg.sha256,results.jsonl,summary.json}`
- `scripts/kb_consumption_snapshot.py` → `artifacts/kb_consumption/snapshots.jsonl` + `kb_consumption_snapshots` 表

一句话结论：**KB 不是「注入了却不被引」，而是「根本进不去上下文」——检索面（读路径）不可达是主因（本轮实测复现），
其次才是相关性/粒度/格式设计问题。** 被动注入在真实任务上只发生过 1 次（3 张卡），而 31 张卡里 28 张从未被注入过。

---

## ① 诊断：逐维归因（正例 2 条 vs 负例抽样）

### 观测事实（`audit.json` 各 block 带 SQL 原文）

| 量 | 值 | 来源 |
|---|---|---|
| knowledge_base 总条数 | 31（16 条 ops 型 trap/lesson/pattern/fact + 15 条 capability） | `inventory` |
| 全历史注入次数（injected_count 合计） | **3** | `inventory.total_injected` |
| 全历史被引次数（cited_count 合计） | **2** | `inventory.total_cited` |
| 注入台账行数 / 涉及任务数 | 3 行 / **1 个任务（m14357）** | `injections` |
| 任务 result 文本里出现 `cited_kb` 的任务 | 5 / 14179 | `citations` |
| 卡创建后同域任务数（引用率分母） | 132 | `exposure` |
| 暴露归一化引用率 | 2/132 = **1.52%** | `summary.embedded_citation_rate` |

**正例（唯一被引的 2 条）**：`KB-SELFRESULT-DISTRUST`、`KB-CLUSTER-FIRST`，同一时刻
`2026-11-11T07:01:33Z`、同一任务 `m14357`，citation_ref 都指向
`artifacts/knowledge_injection/counter_reconcile.json` + `cluster job cj822`。
即：**引用只发生在「有人把 3 张卡打包成 injection package 硬塞进上下文」的那一次**，不是自然检索的结果。

**负例（抽样，任务自报原话，`citations.negative_mentions`）**：
- m14549：「KB：knowledge engine 离线（8021 拒连）无可引用条目…cited_kb=[]」
- m14678：「/tensor/knowledge/search 因 KB 引擎 8021 离线不可用（engine_offline）…故无 cited_kb」
- m14689：「knowledge_base(capability) 与 oss_solutions **未能查询**——psql 直连 permission denied，
  /tensor/kb、/tensor/capabilities、/tensor/oss-solutions 均 404，故本轮无 cited_kb」
- m15062：「KB 查询被拒（psql: permission denied for table knowledge_base），故无 cited_kb」
- m15063：「开工三查的 KB/OSS 查询因 psql 权限与 /tensor/kb、/tensor/oss-solutions 404 未能完成，无 cited_kb」

**5 次「cited_kb」里 4 次是自报「无」**——owner 看到的「5 次」是文本提及数，不是引用数。

### 维度归因

| 维度 | 结论 | 证据（可复算） |
|---|---|---|
| **检索面（读路径）** | **主因：不可达**。存 31 张卡的 `knowledge_base` 表**没有任何可用的 HTTP 读面**；psql 默认角色被拒 | `access_probe`：`psql -U root` / `-U kb` → `permission denied for table knowledge_base`（postgres/ship/foundation 才有 SELECT）；`/tensor/knowledge/status|search|assets` → `engine_offline`(8021 拒连) / `asset_dir_missing`；`/knowledge/search?q=ITTC` → 200 但 `count:0`（读的是 `knowledge_sediment/knowledge.jsonl`，空仓） |
| **注入时机/机制** | 「开工三查」是 prompt 里**一段让你自己连库的 SQL 文本**，不是自动注入；无本机 DSN 教学、无失败降级 | `taskboard.py` 任务 goal 原文（`ktype='capability' AND domain='{repo}'`）；台账 3 行全在一次人工打包内（`injections.distinct_missions=['14357']`） |
| **相关性/检索精度** | 现网唯一一次检索是**通用词重叠**，无域过滤 | `injections.match_terms` = `["worker","列空","派发"]`/`["agent","owner","任务","派发"]`/`["agent","不可","报告","验收"]`，match_score 3–4；这类词任何任务都命中 |
| **域词表** | 16 条 ops 卡（trap/lesson/pattern/fact）**结构上不可达**于三查查询① | `exposure.domains_not_a_repo` = `[build, ci, github, physics, platform, shell, verif]`；`ktype='capability' AND domain=<repo>` 只能命中 15 条 capability 卡；ops 卡 domain 全部不是仓名 |
| **粒度** | capability 卡 1,775–7,059 字符（JSON blob，含 evidence 指针）；ops 卡中位数 ~106 字符（短卡） | `inventory.by_ktype` / 各卡 `content_chars` |
| **格式** | capability 卡是 `{"scope","level","usage","evidence":{...}}` 的**机器结构**，人读要二次解析；`usage` 是同一句样板话，没有「何时适用/何时不适用」 | 原始 content（`inventory.items`） |
| **信任层** | 无 review 状态语义：31 条全部 `status='active'`，来源 `platform-ops` / `maturity_gate#v*`；**含评测 FAIL 的卡也被当经验注入**（cap:TensorFEM:m14687 内容里写着 `overall FAIL with exit code 1`） | `inventory.items[].status/source` |
| **新鲜度** | 卡与推翻性证据无结构关联：`negative_knowledge_ledger` 121 条，无一条指向 kb_key | `staleness`（按 domain 模糊匹配只有噪声级关联） |

> 诚实标注：本次**没有**做「同一张卡，被引 vs 未被引」的配对统计——因为被引样本 n=2 且都来自同一次人工打包，
> 统计上不可分辨。替代做法是下面的受控 A/B（直接注入，绕过坏掉的检索面），把「设计质量」和「可达性」解耦测量。

---

## ② A/B 实验（真跑真数字）

**决策**：KB 卡以什么形态/时机进入 agent 上下文才被真用（决定 v1 设计取舍）。
**对照**：A=无 KB（现状真实情形——检索面不可达时 agent 实际拿到的上下文）；B=被动注入（三查命中的同域卡原文 verbatim）；
C=主动检索（只给「标题+类型+域」目录，模型自行 `RETRIEVE: <kb_key>`，二轮取卡再答）。
**锚**：K1=ITTC-1957 摩擦系数（数值可判）；K2=平台纪律（集群递交/不在 99 压重算/架构分判）；K3=capability 卡事实（m14687 收敛率/力误差/等级）。
**单位/重复**：单次 LLM 调用（temperature=0），每（锚×臂）reps=4；判分为确定性规则，无 LLM 裁判。
**环境**：model=qwen3.7-plus，LLM endpoint 平台统一入口，token 数取 provider `usage`；prereg 先冻结
`sha256=e90109f283351d48…`（`runs/kb_ab_20261111T201329Z/prereg.sha256`）。

| 锚×臂 | n | 通过率 | prompt tok 均值 | completion tok 均值 | 时延 s |
|---|---|---|---|---|---|
| K1/A | 4 | **1.00** | 85 | 728 | 12.4 |
| K1/B | 4 | **1.00** | 186 | 871 | 14.7 |
| K1/C | 4 | **1.00** | 1247 | 790 | 13.7 |
| K2/A | 4 | 0.00 | 85 | 1005 | 17.4 |
| K2/B | 4 | 0.00 | 467 | 1019 | 16.9 |
| K2/C | 4 | 0.00 | 1247 | 897 | 15.3 |
| K3/A | 4 | **0.00** | 82 | 1641 | 27.1 |
| K3/B | 4 | **1.00** | 1408 | 1093 | 18.3 |
| K3/C | 4 | **1.00** | 2648 | 1242 | 21.9 |
| K3/B_long（整卡） | 4 | **1.00** | 1395 | 825 | 13.9 |
| K3/B_short（前缀摘要 280 字符） | 4 | **0.00** | 260 | 1262 | 21.0 |
| **臂总计 A/B/C** | 12/12/12 | 0.333 / 0.667 / 0.667 | 84 / 687 / 1714 | 1125 / 994 / 976 | 19.0 / 16.6 / 17.0 |

主动检索行为（C 臂 12 次调用）：`retrieved_any=4, hit=4, hit_rate=0.333`，
请求的 key 只有 `cap:TensorFEM:m14687_GAP-FEM-MORTAR`——**K1/K2（trap/fact/pattern 类）零次检索**。

**读法（含反面结果）**
1. **KB 对「模型不可能知道的内部事实」是决定性的**：K3 A 臂 0/4（模型编数字）→ B/C 臂 4/4。这是 KB 存在的正当性来源。
2. **对「模型参数知识已覆盖的公共事实」，注入是纯成本**：K1 三臂全 1.0，B 臂多付 101 prompt token、C 臂多付 1162 token，收益 0。
3. **"只给目录、让模型主动检索"在纪律类问题上不触发**：C 臂 K2 零检索；标题+域不足以让模型意识到"这里有我要的东西"。
4. **粒度：摘要化必须保留可判据数字**：K3/B_long 4/4 vs B_short 0/4（260 vs 1395 prompt token）。注意这是**前缀截断摘要**，
   不是人工提炼摘要——它证明的是"砍掉 evidence 数字的摘要等于没给"，**不能**外推为"精炼摘要无效"。
5. **K2 是无效锚（honest）**：三臂全 0/4。判分器要求同时出现「集群递交 / 不在 99 控制面 / loong64 vs x86」三要素，
   实测三臂输出都缺要素或表述不同（如用"本地容器"而非"99"）。**本轮不能据此评价平台纪律卡的效力**，需第 2 轮改判分口径或改题型。

---

## ③ KB 设计建议 v1（逐条挂证据 + 可证伪条件）

| # | 建议 | 证据 | 证伪条件（哪条数据会否掉它） |
|---|---|---|---|
| R1 | **先修读路径，再谈内容**：给 `knowledge_base` 一个 HTTP 读面（`GET /tensor/kb/search?repo=&ktype=&q=`，返回卡片正文+证据指针），检索失败必须降级为「卡片目录」。没有这层，其余设计都不可测 | 本轮实测：`psql -U root/-U kb → permission denied`；3 个 `/tensor/knowledge/*` 端点 engine_offline；`/knowledge/search` 读空 sediment 仓 count=0；5 个任务自报 "无法查询故无 cited_kb" | 读面上线后 2 周，`knowledge_injections` 新增行数仍为 0 |
| R2 | **域词表统一**：卡片增加 `repos[]`（可多值），检索按 `repos @> [repo]`；保留 `domain` 作学科标签 | 7 个 domain 值不是仓名（build/ci/github/physics/platform/shell/verif），16 条 ops 卡对三查查询① 结构不可达 | 加 `repos[]` 后同域任务注入曝光率不上升（分母 132 量级可测） |
| R3 | **注入时机：派发时自动注入 top-3 卡正文**（按 repo+任务关键词打分），而不是在 prompt 里让 agent 自己查 | 全历史注入 3 次全在一次人工打包内；K3/A 0/4 证明"没有卡就编"；K1 证明"有卡但无用"需靠选择器门槛 | 自动注入后 2 周内 cited 率 <10% |
| R4 | **粒度：卡=可判据条目，不是文档**。正文必须保留指标数字与证据指针；**禁止用前缀截断摘要替代**；capability 卡 1.7–7k 字符应先抽 `key_numbers[]` 字段（收敛率/误差/等级）做注入主载荷 | K3 B_long 1.00 vs B_short 0.00；capability 卡原文是 JSON blob，数字埋在 `evidence.benchmark` 长句里 | 若 `key_numbers[]` 抽取后 K3 类锚正确率仍 1.00 且 prompt token < 600 → 整卡不必注入 |
| R5 | **事实卡分级：`param_known=true` 的公共事实卡不进默认注入面**（ITTC-1957、ITTC 公式类），只留给小模型/离线场景 | K1 三臂全 1.0，B +101 / C +1162 prompt token 零收益 | 换小模型（如 27B）后 K1/A 掉到 <0.5 → 必须保留 |
| R6 | **检索面形态：被动注入为主、主动检索为辅**；主动检索的目录必须带「适用场景」一行摘要，否则不触发 | C 臂 12 次仅 K3 触发检索（4/4 命中），K1/K2 零检索 | 目录加场景摘要后，K2 类锚检索触发率仍为 0 |
| R7 | **信任层：只有 `reviewed`/`published` 状态的卡可进注入面；评测 FAIL 的 capability 卡只能以「已证伪/薄弱」标注形态出现**（沿用训练集口径：published/reviewed 才可入训练语料） | 31 条全部 `status='active'`；cap:TensorFEM:m14687 正文写 `overall FAIL with exit code 1`，A/B 中 B 臂 4/4 把它当既成事实复述 | 若上线 review 门槛后 KM 类「未知事实」锚正确率从 1.00 掉到 <0.6 → 门槛过严，需分级而非一刀切 |
| R8 | **新鲜度：卡增 `supersedes`/`superseded_by` + 检索按 `valid_from/valid_to` 过滤**；verdict 推翻旧卡时自动写 supersede 边并把旧卡移出注入面 | `negative_knowledge_ledger` 121 条与卡无任何结构关联；卡被引后无失效路径（cited 2 条均无后续复核记录） | 加 supersede 边后 2 周内 0 次失效事件 → 说明新鲜度不是当前瓶颈，优先级下调 |

**优先级**：R1 → R3 → R2 → R4 → R7 → R5/R6 → R8。
理由：R1 决定"能不能测"，R3 决定"会不会被用"，R2/R4 决定"注入了有没有用"，其余为质量闸。

---

## ④ 消费计量：cited_kb 周期快照进 chronicle（落地方案）

**现状缺口**：`cited_count`/`injected_count` 是**人工回写**的计数器（无事件溯源），`knowledge_injections` 只有 3 行；
`compound_meter.py` 只读"capability 类的 cited 合计"一个标量，看不出"谁没被引、为什么"。

**落地件（本仓已实现并跑过）**：`scripts/kb_consumption_snapshot.py`
- 产出 `schema=kb-consumption/1` 快照：`kb_total / injected_total / cited_total / cited_rows /
  injection_rows / injection_missions / exposure_denominator / citation_rate /
  by_ktype / by_domain / unretrieved_top（暴露高但零引用的卡）/ access_ok`；
- 落两处：`artifacts/kb_consumption/snapshots.jsonl`（append，一周期一行，sha256 校验）+ Postgres 表
  `kb_consumption_snapshots`（便于 SQL 追溯）；
- 纯 SQL 零 LLM，随 chronicle 六源钟同拍跑即可（chronicle 在 TensorPlatform 仓，接线一行：
  `payload["s7_kb_consumption"] = json.loads(subprocess.run([sys.executable,"scripts/kb_consumption_snapshot.py","--print"]).stdout)`）。

**告警（机制化，不依赖人看）**：
1. `access_ok=false`（读面不可达）→ 红线：KB 处于"设计失效"态，任何 cited 统计都不足信；
2. `injected_7d==0` 而同期同域任务数 >10 → 注入回路断；
3. `cited_rate_7d==0` 连续 3 期而注入 >0 → 内容/格式问题，进第 2 轮设计。

---

## ⑤ 注意点 / 局限（honest）

- **任务级双臂 A/B（真 dispatch 两条任务）没跑**：派发池当前 12+ 任务在跑（`tensor_dev_missions` 中 `status='running'`），
  新任务排队时延不可控，无法在本单墙钟内拿到成对结果。本轮 A/B 是**调用级**对照（真实 LLM、真实 token 计量、prereg 冻结），
  它隔离了"KB 内容质量"，但**没有**覆盖"agent 在完整任务里是否愿意引用"这一环——该环目前只有 5 条任务自报的正/负例观测。
- **K2 锚无结论**（三臂 0/4，判分口径问题），不得据此评价纪律类卡。
- **K3/B_short 是前缀截断摘要**，结论限定为"砍掉数字的摘要无效"，不外推。
- 网关侧 `reasoning_tokens` 计入 completion，故 completion 数偏高（K1/A 728 tok 里大部分是推理），比较时只看同锚内相对差。
- 两次完整运行（`201329Z`、`200924Z`）同配置；`201126Z` 被外部超时截断未入账。

## ⑥ 误差判定（vs 基准）
- 判分器基准：K1 真值由公式 `0.075/(log10Re−2)²` 程序化算出（Re=1e8→0.00208333，Re=1e9→0.00153061），
  通过判据 ≤1% 相对误差；K1/A 实测输出与真值相对误差 <0.01% → **<3% 达标**。
- K3 基准取自卡内 evidence（收敛率 0.07、force err 32.288–35.135%），判据 ±0.005 / ±1.5pp；B 臂 4/4 命中 → **<3% 达标**。
- K2 无有效基准（判分口径不可裁）→ 无误差可报，按无效锚处理。
- 消费率指标本身无外部基准，仅与"设计目标 cited 率"对照：现状 1.52% vs 目标 ≥10% → **不达标**。