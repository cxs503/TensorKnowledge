# 生产线 Runner（wp-line-v1）——五工序的可执行执行面

**单号**：m15913（返修轮，原 m15494）｜**实现**：`ke/wp_line.py`（1250+ 行）
**入口**：`python -m ke.wp_line` / `python scripts/run_wp_line.py`（同一入口，平台派发用后者）
**规范**：`docs/production/PRODUCTION-LINE-v1.md` §2（五工序）§3（三道门）；
规则 id 归 `docs/production/GATE-RULES.md`；契约 schema 归
`schemas/work-package-contract.schema.json`（**同一份文件**，不另立真源）。
**运行工件**：`docs/production/run-artifacts/`（`RESULTS.md` 由程序生成，零手抄）
**图**：`docs/production/figures/wp_line_benchmark.png`

> 定位：m15494 交了契约 schema + 门禁（`ke/wp_gate.py`）+ 规范文档，但**没有执行面**——
> 谁按什么顺序跑、下游许不许消费上游、05 综合何时才准启动、门禁怎么被机器验收，
> 全停留在文字。本单补的就是这一层，并把"门禁有没有用"变成可复算的基准。

---

## 1. 一条命令复现全部证据

```bash
# 全量重建（含 process 01 打真平台；联网只需 $TENSOR_API_BASE 与 TENSOR_AGENT_USER/PASS）
python scripts/wp_line_artifacts.py --out docs/production/run-artifacts --online

# 离线重建（process 01 走夹具 sources 目录）
python scripts/wp_line_artifacts.py --out docs/production/run-artifacts

# 单独跑基准（参考标签来自 GATE-RULES.md 夹具矩阵，先于本实现写定）
python -m ke.wp_line bench --json /tmp/bench.json

# 单独跑线（五工序按依赖序，未清上游的包不运行）
python -m ke.wp_line run --root tests/fixtures/extraction \
    --sources tests/fixtures/extraction/sources \
    --review-ledger-dir tests/fixtures/extraction/ledgers \
    --tickets-dir tests/fixtures/extraction/tickets

# 测试
python -m pytest tests/test_wp_line.py tests/test_wp_gate.py -q
```

`tests/test_wp_gate.py`（40 例）此前**在 main 上缺失**（m15494 推送时被门禁滤除），
而 `GATE-RULES.md` 一直引用它——本单把它从原分支恢复后 40 passed，文档引用重新可执行。

---

## 2. 五工序：顺序是 DAG，不是菜单

| 工序 | 难度 | 并行度 | Agent 档 | 依赖 | 出口门 |
|---|---|---|---|---|---|
| 01 资产登记 | 低 | 极高 | standard | — | G1 |
| 02 分类解析 | 低 | 高 | standard | 01 | G1 |
| 03 知识抽取 | 中 | 高 | standard | 02 | G1+G2 |
| 04 独立审核 | 中 | 高 | strong | 03 | G3 |
| 05 综合研究 | 高 | 低 | strong | 01+02+03+04 | G1+G3 |

三条机器强制的规则（都有测试）：

1. **上游未清 = 下游不跑**：`run_line` 对依赖未 `cleared` 的包直接判
   `blocked_upstream` 并写明 `blocked_on`，不"先跑起来再说"
   （`test_line_does_not_run_a_downstream_package_on_a_failed_upstream`）。
2. **综合必须在基础加工完成后**：05 的 `depends_on` 声明全部四个基础工序，
   任一 03 包未清 → `base_processing_complete=false`，05 不启动
   （`test_line_reports_synthesis_blocked_on_incomplete_base`）。
   这正是 owner 令里"防缺全局信息反复得出重复结论"的机器形态。
3. **契约来源唯一**：01–05 的契约都由 `build_contract` 按
   `work-package-contract.schema.json` 生成并校验；04 的 `reviewed_package`
   摘要只能从**已存在的** 03 工件算（`derive_reviewed_package`，缺工件即报
   "run 03 first"），禁止在计划期凭空造哈希。

## 3. 05 综合输入：只喂证据绑定的、已独立批准的工作

`assemble_synthesis_input` 的准入 = 出口门 cleared **且** 级别 L2/L3 **且**
review approved。其余全部**带理由码拒收**（`GATE_FAILED` /
`NOT_EVIDENCE_BOUND` / `REVIEW_NOT_APPROVED` / `UPSTREAM_INCOMPLETE`），
不静默丢弃：

* 零 claim 的空包可以合法过门（`no_forced_claim_generation`），但它只有 L1，
  因此**不许**被当作"证据绑定"喂给综合——实测 `wp-ok-zero-claim` 被
  `NOT_EVIDENCE_BOUND` 拒收。
* 跨报告近重复陈述（token Jaccard ≥ 0.9）只**标记**为 `duplicate_candidates`，
  不合并、不删除：判定"两条说的是同一件事"是语义判断，属综合审核者，不属 runner。

## 4. 基准：参考标签 vs 实测判定 + 变异矩阵

**参考标签来源**：`docs/production/GATE-RULES.md` 的"夹具矩阵"表（随夹具写定，
早于本 runner），不是把结果抄回来。指标与阈值**先声明后测**（`wp_line.THRESHOLDS`）。

| 指标 | 阈值 | 实测 |
|---|---|---|
| verdict_agreement（8 夹具） | 1.00 | 1.00（8/8） |
| rule_agreement（失败规则命中） | 1.00 | 1.00（8/8） |
| level_agreement（验证级别） | 1.00 | 1.00（8/8） |
| mutation_detection（21 个单点变异） | 1.00 | 1.00（21/21） |
| rule_coverage（门禁已实现规则被证伪覆盖） | 0.90 | 1.00（27/27） |

变异矩阵每个变异**只破坏一个不变量**，并预先声明应由哪条规则抓（S1/S2/S6/S8/S10/
S11/S12/S13/S14/S15、E1/E2/E4/E5/E6、M1/M2/M3/M4/M5）。这条验证回答了一个
真问题：**门禁里的规则不是摆设，每条都能被具体缺陷弄红**（27 条全红过）。
注意语义门（M*）在变异下会红，但**不会**改变 verdict——G3 只能由独立审核给，
runner 不得伪造通过；`detected` 因此定义为"声明的规则被触发"，`verdict_changed`
另记一列，两者都写进 `benchmark.json`。

## 5. 已知局限（不掩盖）

1. **01/02/04/05 只有脊柱门**：`spine_gate` 校验契约 + 声明工件存在且为合法
   JSON（P1–P4）；S1–S15 是 03 分支专用规则集。把 03 的规则硬套到 01 是错的，
   所以 runner 明说"只查它声明的东西"，不假装同等强度。
2. **04 的语义门无机器判据**：M* 只是"审核包是否合规"的准备检查；G3 通过与否
   由独立审核 Agent 产生，runner 只能报告 `review_state`。
3. **注册表里 K5/K6（技能库）不在本线**：`validate_skill_registry` 已有，但未接进
   runner 的工序出口，属下一轮。
4. **吞吐未测**：夹具 8 包 / 变异 21 个是正确性基准，不是万份规模压测；
   并行调度（分片、重试、断点）留待吞吐战役。
5. **process 01 的附件内容未验**：只登记 manifest 与哈希声明，未做附件内容抽取
   （与 `GATE-RULES.md` 已知局限 5 一致）。