# RCI S2b · Schema 修订清单与阶段 3 全量预案

> 来源：`artifacts/rci/pilot200/`（278 KO / 200 文档 / 108 条人工逐字段判定 / 3 轮配置迭代）。
> 修订清单按「证据 → 修订 → 验收判据」三段式写，避免凭感觉改 Schema。

## A. Schema 修订清单（按严重度排序）

### R1〔阻断级〕KO 类型词表覆盖不足 —— 类型适配仅 35.2%（38/108）
- **证据**：三轮人工判定中类型误配的主导族：治理/流程/ops 散文被塞进 innovation/technical-plan/algorithm（~29% 的失败项）；
  负知识（gotcha/failure）、code-pointer（`file:line` 证据行）、changelog/log、文档状态块、audit 指标表**无对应类型**。
- **修订**：
  1. `ko_type` 增补 `failure`（负知识/陷阱）、`code-pointer`（模块→file:line）、`governance-rule`（规则/契约）、`record`（日志/状态/清单）；
     与 KBM 既有 `failure-card` / `code-pointer-card` 对齐，避免两套词表。
  2. 新增必填 `ko_type_confidence: {score: 0..1, basis: "section-intent"|"cue"|"fallback"|"manual"}`；
     `basis != "section-intent"` 的对象进入人工分流队列，**不进类型统计、不进阶段 3 训练集**。
  3. 兜底（fallback）对象必须打 `provenance.generator = "…-fallback"`（本轮已实现）且 `ko_type_confidence.score ≤ 0.4`。
- **验收判据**：新一轮 36 条抽验中类型适配 ≥90%，且 `basis` 标注 100% 存在。

### R2〔阻断级〕conditions 允许「非限制语句」→ 88.9% 未臆造
- **证据**：R1/R2 各 4 例臆造式条件：把 `航速限制 v_max(h)=…`（模型公式）、`Scope` 章节的项目自述、License 段落、祈使句指令当范围。
  R3 改为「有效性线索硬门（cannot/only for/assumes/lower bound/仅适/下界…）+ 祈使句与许可段落过滤」后 36/36 通过，
  代价是自述率降到 29.1%。
- **修订**：
  1. `conditions` 增加 `evidence_kind: "limit-sentence"|"limit-section"|"abstained"` 与 `cue: string`（命中的有效性线索原文），
     没有 `cue` 一律不得 `stated_in_source=true`。
  2. 新增 `conditions.absence_reason`：`{not-stated, formula-only, instruction-only, licence-only, out-of-section}`，
     把「为什么弃权」变成可统计的信号，而不是沉默的空字段。
- **验收判据**：36 条抽验 conditions 未臆造 = 100%（本轮 R3 已达成），且 `absence_reason` 字段 100% 填写。

### R3〔高〕「删减式复述」需在 Schema 内显式化
- **证据**：claim 忠实原文三轮 108/108，靠的是抽取器「标题 + 引文子串」的构造式复述，而不是事后校对。
  该约束目前只写在代码里，Schema 未表达，外部工具无法自检。
- **修订**：`claim.faithfulness` 增必填 `restatement_mode: "verbatim"|"deletion-only"|"paraphrase"`；
  仅前两种允许 `epistemic_status=confirmed`，`paraphrase` 必须带 reviewer 记录。
- **验收判据**：Schema 校验器可仅凭对象本身判定 `deletion-only` 合法性（token 包含 + 数字包含）。

### R4〔高〕证据指针需支持「跨文件/跨仓」与「工件类型」
- **证据**：本轮 100% 指针可达是因为全部指向仓内冻结快照；语料中大量结论指向 `artifacts/…png`、`runs/…json`、外部仓库 `file:line`，
  当前 `pointer{path,lines,sha256}` 无法表达「另一仓 + 提交 + 符号」。
- **修订**：`pointer` 增加可选 `repo`,`commit`,`symbol`,`artifact_type`；`kind` 增 `figure` 与 `code-line`。
- **验收判据**：新样本中≥10 条跨仓指针可被独立脚本解析并通过/给出明确 `unreachable` 原因。

### R5〔中〕六维打分需与「文档级」证据解耦
- **证据**：六维分可复算 100%，但 `evidence_completeness` 均值 4.55、`problem_clarity` 均值 2.63：
  前者对「有指针/有表格」高度饱和，后者对以验证报告为主的语料天然偏低；两维区分度不足。
- **修订**：`evidence_completeness` 拆成「指针数量/指针类型多样性/数值可复核性」三子项；
  `problem_clarity` 接受「问题由任务锚点外部给出」的替代证据（`problem_source: internal|external-anchor`）。
- **验收判据**：维分与人工判定的一致性（Kendall τ）≥0.6，且单维方差 > 0.8。

### R6〔中〕样本代表性需在 Schema/清单里登记权重
- **证据**：分层保底使信息类过采样（样本 12.5% vs 语料 2.0%），直接用样本均值会高估质量。
- **修订**：`sample.json` 增 `design_weight = corpus_share / sample_share` 字段；统计聚合必须携带权重。
- **验收判据**：阶段 3 报告的总体均值可由加权脚本复算，权重和不为 1 时降级为「样本内结论」。

## B. 阶段 3 全量预案（失败重试 / 自动分级 / 批次吞吐）

### B1 失败重试
- 逐文档 `try/except`，失败入隔离台账（本轮已实现 `docs_extract_error` + 原因），**绝不静默丢文档**。
- 重试策略：同配置 3 次（间隔 30 s/2 min/10 min），仍失败则降级到兜底 KO 并标 `basis=fallback`；
  兜底也失败 → 标记 `quarantined`，进人工队列，计入覆盖率分母（诚实覆盖率）。
- 语料漂移：清单 sha ≠ 快照 sha 时（本轮 1 篇）以快照为权威，`corpus_drift` 计数进 manifest，供全量时定位「活仓库」影响面。

### B2 自动分级
- 一级（规则，本轮实测）：RQS 分级 A/B/C = **规则条件**而非分数切阈（A 需 problem≥3 且 method/evidence/truth≥4 且 repro/innovation≥3）。
- 二级（类型置信度）：`ko_type_confidence` 低于阈值（建议 0.7）→ 人工分流；本轮兜底占比 29% 即预计分流规模。
- 三级（人工抽验门）：每批 200 份抽 36 条逐字段核验，**门禁** = claim/evidence ≥98%、conditions 100%、类型适配 ≥90%；
  未过门则该批停线，不进入下一批。
- 分级产出：`tier`（质量）+ `type_confidence`（类型）+ `needs_review`（分流标记），三者正交，禁止用质量分代替置信度。

### B3 批次吞吐
- 实测单核规则管线 **~2000 篇/分钟**（200 篇 5.9 s，中位 14 ms/篇）；全量语料 5228 篇约 2.6 分钟单核，
  10 万篇级（含 PDF 转写与 LLM 类型判别）需按下面分片：
  - 分片键 = 仓 × 类型（15×4）；每片独立 seed，产出自带 `pipeline_run` 与快照 sha，可并行可重放；
  - 幂等键 = `(repo, path, snapshot_sha)`，重跑同片产出逐字节一致（本轮已验证：同配置二次运行 objects.jsonl 相同）；
  - 追加 LLM 环节时按「规则先行 + LLM 只处理 `basis=fallback` 与 `needs_review`」的原型，本轮兜底占比 29% 给出上界估计：
    LLM 调用量 ≈ 语料文档数 × 29%，而非全量。
- 容量纪律：全量跑不在控制面 99 上做，递交集群 `run_cluster`（分片 `--cmd-tpl`），日志按 shard 落盘。

### B4 交付物契约（阶段 3 每批必须产出）
`inventory.json`（含 sha/sha_drift）、`sample.json`（含 design_weight）、`corpus/`（冻结快照）、
`objects.jsonl`（Schema v2 校验通过）、`manifest.json`（吞吐/兜底/漂移/校验错误）、
`review/`（机械 + 人工逐字段 + 失败分类），缺一不得晋级。