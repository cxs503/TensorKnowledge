# 交差核验报告 · m15494 / KBM-RCI-F1-SPEC（TensorKnowledge）

- 被审任务：`tensor_dev_missions.id=15494`，repo=`TensorKnowledge`，task_key=`kbm-rci-f1-spec`，status=`succeeded`
- 被审分支：`agent/m15494`，成果提交 `56d5a68`（"matured mission deliverables"）+ `d87dd72`（生产线 v1 本体）
- 合入情况：`e186a37 Merge #62 (m15494) via push-merge`；同提交的 `a1c0c76 …（7 个文件被门禁滤除）`
- 审计席位：本任务 m15895（`verdict_by='board-audit'`），审计工作树 `/root/tp-agent/work/m15895`（main HEAD `3d43e3c`）
- 审计产物：`artifacts/audit_m15895/{mutation_report.json,gate_audit.png,run_mutations.py,figures_gate_audit.py}`、`artifacts/audit_m15895/evidence.json`
- 结论：**L2（独立功能实现），machine gate 预计 confirmed**；L3/L4 未成立（详见 §6.3），并附 1 项必须在下一轮修的整合缺陷（§5.1）

---

## ① 案例介绍

**被审对象**：TensorKnowledge「报告→知识生产线 v1」——把平台 `tensor_reports` 的论文级报告蒸馏成知识对象的标准工件体系。交付物四件：

| # | 交付件 | 物理载体（`work/m15494`） | 规模 |
|---|---|---|---|
| 1 | 工作包契约 JSON Schema（03 知识抽取工序完整规格） | `schemas/work-package-contract.schema.json` | 405 行，4 处 `if/then` 任务类型分支（:245/:321/:359/:381/:398） |
| 2 | 三道门可执行门禁（结构门 S1–S15 + 证据门 E1–E7 + 语义门/验证阶梯） | `ke/wp_gate.py` | 957 行，39 处 `checks.check(...)`，**22 个唯一规则 id** |
| 3 | CLI 执行器（批量扫包 / 在线离线源解析 / 技能库校验） | `scripts/validate_work_package.py:49 main()` | 123 行 |
| 4 | 规则清单 + 生产规范 + 抽取技能库（6 类报告技能 + 生产者/审核者提示词） | `docs/production/GATE-RULES.md`(124 行)、`docs/production/PRODUCTION-LINE-v1.md`(333 行)、`extraction-skills/registry.json`(230 行, 6 skills) | — |

**物理/工程背景**：这不是数值求解器任务，没有几何/物性参数表；被审对象的"场量"是**判定结果**（verdict ∈ {PASS_PROGRAMMATIC_PENDING_REVIEW, FAIL_STRUCTURAL, FAIL_EVIDENCE}）与**验证等级**（L0–L3，由门禁按 V1–V5 规则计算、禁止生产者自填）。因此本报告的数值表是 verdict/level 矩阵与规则命中集，误差判据为**精确匹配**（§6）。

**锚点**：`KBM-RCI-F1-SPEC`（RCI·Knowledge Factory 生产规范 + 工作包）。owner 规格 = 5 目标 / 4 产物 / 5 恒真约束 / 6 验收项 / 必配独立审核 / `delivery=draft`。落表实测：schema 编码 11 个 objective 轴、8 个产物位、`constraints.required` 恰为 5 条恒真约束、8 条 acceptance（= 6 验收项 + 2 独立审核项）——**规格是锚点的超集，无缩水**。

## ② 怎么做的（取证流程）

1. **不读报告先读数据**：`SELECT jsonb_pretty(result) FROM tensor_dev_missions WHERE id=15494` 取 mission 自述（含 `changed_files`/`on_disk_changes`/`checks`/`headline`），确认 15 个已提交文件 + 8 个 `runs/m15494/*` 产物在自述里被声明。
2. **两处对照 git 事实**：`git ls-tree -r --name-only HEAD`（mission 工作树 `56d5a68`）逐项确认产物真实存在于树；再在审计工作树（main `3d43e3c`）用 `git cat-file -e HEAD:<path>` 逐文件判在/不在——这是发现 §5.1 的方法。
3. **基准裁判查询**：`SELECT case_name,metric,tolerance FROM tensor_benchmark_cases WHERE anchor_slug='KBM-RCI-F1-SPEC'` → **0 行**（全表 25 行，TensorKnowledge 仓 0 行）；`SELECT count(*) FROM tensorbench_results WHERE mission_id=15494` → **0**。即该锚点无机器裁判（详见 §6.2 的替代判据）。
4. **重跑 mission 自述的三个复现命令**（不采信自述）：
   - `python -m pytest tests/test_wp_gate.py -q` → **40 passed**（自述 40，一致）；
   - `python scripts/validate_work_package.py --root tests/fixtures/extraction … --skills extraction-skills/registry.json`（mission 工作树）→ 退出码 0，8 包 verdict/level/ceiling_reason 与 `runs/m15494/sweep-report.json` **逐一相同**；
   - 同一条 CLI 在**审计方 main 工作树**（`m15895`，无 mission 分支任何文件）重跑 → 8/8 包 verdict+level+ceiling **再次完全相同**，skills 6/6 pass。
5. **反例实验（adversarial，本审计的核心增量）**：`artifacts/audit_m15895/run_mutations.py` 从**通过态**夹具派生 7 个单字段变异体，各跑一次 shipped CLI：控制组、纯改名、单哈希翻转、伪造引文、自审材料、票据后改 claim、剔除目标轴。用于回答「门禁是在断言不变量，还是仅仅执行了代码」。
6. **证伪 mission 的一条负面自述**：mission 称 "6 failures in test_ke_migrate/test_sediment_ke_relay reproduce identically in a clean HEAD worktree (pre-existing)"——审计方在干净 main（`m15895`）跑同两文件 → **6 failed, 9 passed**，失败集合完全一致 ⇒ 该免责声明成立，不是甩锅。

## ③ 计算结果（全部程序化取自 JSON 工件，零手抄）

### 3.1 三件套存在性核验

| 项 | 声明/自述 | 审计实测 | 判定 |
|---|---|---|---|
| run_artifacts 文件真实存在 | `runs/m15494/{gate-report.json, sweep-report.json, gate_matrix.png, README.md}` | 树内存在：175,844 B / 176,650 B / **PNG 2550×1445 RGBA 242,884 B** / 2,059 B | ✅ 存在（在 `agent/m15494`；main 中缺失，见 §5.1） |
| benchmark ref vs got 数值在容差内 | 未声明 benchmark（spec 型锚点） | `tensor_benchmark_cases` **0 行**、`tensorbench_results` **0 行** | ⚠️ 无裁判可用（§6.2 替代判据） |
| repro_cmd 可执行 | README 给出 3 条命令 | 3 条全部退出码 0，输出与工件一致 | ✅ 可执行 |

### 3.2 工件复现矩阵（mission 工件 vs 审计方 main 重跑）

| package | verdict | level | ceiling_reason | 工件=重跑 |
|---|---|---|---|---|
| `wp-bad-no-evidence` | FAIL_STRUCTURAL | L0 | STRUCTURAL_GATE_FAILED | ✅ |
| `wp-bad-quote-offset` | FAIL_EVIDENCE | L1 | EVIDENCE_GATE_FAILED | ✅ |
| `wp-bad-self-review` | FAIL_STRUCTURAL | L0 | STRUCTURAL_GATE_FAILED | ✅ |
| `wp-bad-source-hash` | FAIL_EVIDENCE | L1 | EVIDENCE_GATE_FAILED | ✅ |
| `wp-bad-verified` | FAIL_STRUCTURAL | L0 | STRUCTURAL_GATE_FAILED | ✅ |
| `wp-ok-basic` | PASS_PROGRAMMATIC_PENDING_REVIEW | L2 | MISSING_PLATFORM_VERIFICATION_TICKET | ✅ |
| `wp-ok-verified` | PASS_PROGRAMMATIC_PENDING_REVIEW | L3 | OK_PLATFORM_VERIFIED | ✅ |
| `wp-ok-zero-claim` | PASS_PROGRAMMATIC_PENDING_REVIEW | L1 | EMPTY_PACKAGE_NO_CLAIM_TO_VERIFY | ✅ |

**不一致数 = 0/8**（程序化比对 `package_id+verdict+level+ceiling_reason`），skills 注册表 6/6 pass 双边一致。

### 3.3 变异敏感度矩阵（`mutation_report.json`，控制组起点 L3=PASS）

| 变异体 | 单字段编辑 | 审计实测 verdict / level | 命中规则 |
|---|---|---|---|
| `m0_control_verified` | 无（原样拷贝） | PASS / **L3** | — |
| `m1_rename_only` | 包目录改名 | PASS / **L3** | —（内容寻址，不认文件名） |
| `m2_content_hash` | `evidence[0].locator.content_hash` 翻转 64 位内一位区段 | FAIL_EVIDENCE / **L1** | `E5.quote_hash_consistent` |
| `m3_fabricated_quote` | 引文替换为编造句并删 offsets | FAIL_EVIDENCE / **L1** | `E3.locator_resolvable`, `E5`, `E7.evidence_covers_claims` |
| `m4_self_review` | `reviewer.id := producer.agent_id` 且材料由包自带 | FAIL_STRUCTURAL / **L0** | `S15.no_self_supplied_review_material` |
| `m5_claim_drift_vs_ticket` | 票据签发后改 claim 文本 | PASS / **L2**（L3→L2 降级） | `TICKET_CLAIMS_DIGEST_MISMATCH` |
| `m6_min_objective` | objective 轴裁到 1 个 | FAIL_STRUCTURAL / **L0** | `S3.contract_schema`（`'extract_methods_and_claims' is a required property`） |

**实质变异 5/5 全部被捕获；假通过 0；对控制组与纯改名 0 误杀。**

### 3.4 六段报告核验（`tensor_reports.id=14560`，mission_id=15494）

标题：《报告→知识生产线 v1：标准工作包契约 + 三道门可执行门禁（22 规则 / 8 夹具 / 40 测试）》，markdown 5,305 字符，figures 1 张，`scenario_key='knowledge/production-line-gates'`。六段齐全：① 案例介绍 / ② 怎么做的 / ③ 计算结果（程序化注入）/ ④ 结果图 / ⑤ 注意点 / ⑥ 误差判定——**含显式「误差<3% 不适用」声明与替代判据表**，符合报告纪律（无基准不许含糊）。

## ④ 结果图

![gate_audit](artifacts/audit_m15895/gate_audit.png)

`artifacts/audit_m15895/gate_audit.png`（2550×1445 级别双面板，数字全部来自 `mutation_report.json` 与 `runs/m15494/sweep-report.json`，无手抄）：
- **左**：变异敏感度——每个变异体从 L3 起步，柱状为编辑后等级；红色=FAIL，绿色=PASS。可见单哈希翻转即掉到 L1，自审/裁轴掉到 L0，票据后改 claim 精确掉到 L2 而非直接 FAIL（阶梯设计正确）。
- **右**：8 个夹具包的 verdict×level 全景——4 个坏包分别停在 L0/L1 且规则命中集互不相同（S11 / E3+E4+E7 / S15 / S4+S8+S9），3 个好包落在 L1/L2/L3 三档，说明**等级阶梯不是单一阈值**而是证据完备度的函数。

## ⑤ 注意点（审计发现的缺陷与局限）

**5.1（阻断级，必须下一轮修）合入过滤把证据链砍断**：`e186a37 Merge #62` 对应的 `a1c0c76` 提交信息自述「7 个文件被门禁滤除」，实测 main HEAD（`3d43e3c`）中 `tests/test_wp_gate.py`（452 行 / 40 测试）与 `runs/m15494/*`（4 个工件）**全部不存在**（`git cat-file -e` 逐项 ABSENT），而 `ke/wp_gate.py`、`schemas/work-package-contract.schema.json` 与 mission 分支**逐字节相同**（`git diff` 空）。后果两条：
   1) mainline 的 `docs/production/GATE-RULES.md:4,108` 与 `PRODUCTION-LINE-v1.md:231,292` 仍在教人跑 `python -m pytest tests/test_wp_gate.py -q`（40 passed）——**指向仓库里不存在的文件**，任何人照文档执行都会失败；
   2) 门禁本体进了主干但**回归网没进主干**，后续任何人改 `wp_gate.py` 不会有 red light。
   修法（已由本审计给出最小路径）：把 `tests/test_wp_gate.py` + `tests/fixtures/extraction/**`（fixtures 已在 main）+ `runs/m15494/*` 重新入库；`tests/fixtures/extraction` 本身在 main 中**存在**（`git cat-file -e HEAD:tests/fixtures/extraction/ok-basic/work-package.json` → YES），故只需补测试文件与运行记录，不需重做夹具。

**5.2（轻）报告与任务记录未互链**：`tensor_reports` 有 id=14560 且 mission_id=15494，但 `tensor_dev_missions.report_id` 为 NULL——欠报守望线若按 `report_id` 判会误记欠账。

**5.3（设计观察）契约 schema 的 `objective`/`output`/`acceptance` 三块 `minProperties=1`**，单看 schema 极宽松；实际由 `if/then` 任务类型分支 + `S3.contract_schema` 兜住（变异体 `m6` 实证：objective 砍到 1 轴 → S3 报 `'extract_methods_and_claims' is a required property`）。这是一个**分层设计而非漏洞**，但意味着「schema 即规范」的说法不能脱离门禁单独引用。

**5.4（适用范围）**语义门是"准备件"不是"判定件**：`build_review_request()/build_review_prompts()` 只产出送审包与提示词，`_gate_semantic` 依赖外部 `review_events` 与平台 `verification_ticket`；即 L3 的"独立审核 + 平台票据"两跳在平台侧，本仓无法自证。这也正是本审计把 L3 判给"未成立"而非"已成立"的原因（见 §6.3）。

**5.5（审计局限，如实申报）**：① 本审计未在集群上做规模/性能测试（该交付物为纯 CPU 文本校验，40 测试 0.93 s，压 99 控制面无意义）；② 未接真实 `tensor_reports` 在线源跑 `--online`（需生产知识包，当前 `knowledge/extraction/` 在 main 中不存在，无在线样本）；③ 变异体只覆盖 7 类编辑，非穷举 22 条规则；④ 未独立重写 `wp_gate.py`，只做行为级黑盒+测试级白盒复核。

## ⑥ 误差判定（关键量 vs 基准，逐项显式回答）

| 判据 | 目标 | 实测 | 是否达标 / 是否 <3% |
|---|---|---|---|
| verdict+level+ceiling 复现一致率（8 包） | 100%（精确匹配，非百分比物理量） | **8/8，不一致 0** | ✅ 达标；「<3%」不适用于离散判定量 |
| 夹具包 verdict 分布 | {PASS,FAIL_STRUCTURAL,FAIL_EVIDENCE} 三类均出现 | 3 / 3 / 2 | ✅ |
| 实质变异捕获率 | 全部捕获、0 假通过 | **5/5，假通过 0** | ✅ |
| 控制组/纯改名误杀率 | 0 | **0/2** | ✅ |
| 规则数 vs 文档声明 | 22 条（S1–S15 + E1–E7） | 唯一规则 id **22**，每包 checks=22 | ✅ 声明与实现零偏差 |
| 测试数 vs 声明 | 40 | `pytest -q` → **40 passed** | ✅ |
| 技能库覆盖 | 6/6 + 6 类报告全覆盖 | `K6.six_type_coverage uncovered=[]`，n_pass 6 | ✅ |
| pre-existing 失败免责 | 6 项在干净 main 同样失败 | 干净 main `6 failed, 9 passed`，同集合 | ✅ 免责成立 |
| 基准裁判（L4 前提） | `tensor_benchmark_cases` 有该锚点行 | **0 行**；`tensorbench_results(15494)` **0 行** | ❌ 无裁判 ⇒ **L4 不可判**（非"通过"，是"无法用基准判"） |

**结论性回答**：「误差 <3%」对本题不适用（无连续物理量、锚点无 benchmark 行）；采用的离散判据是**零不一致 + 5/5 反例捕获 + 0 假通过**，全部达标。故"数值精度"维度不构成降级理由，降级理由只能是证据链整合缺陷（§5.1，不改变功能级别 L2，但必须下一轮修）。

### 6.3 定级论证（L0–L5）

| 级别 | 成立？ | 依据 |
|---|---|---|
| L0 文档成果 | 成立但其上有实码 | 405 行 schema + 333 行规范 + 124 行规则表 |
| L1 数学/单元验证 | 成立 | `tests/test_wp_gate.py` 40 项；变异体单字段敏感性 |
| **L2 独立功能实现** | **成立（本审计判定级别）** | `ke/wp_gate.py:739 run_gates()` 真代码：读包 → 解析 22 规则 → 解源/算 sha256/比对 offsets → 输出 verdict+level JSON；审计方用 shipped CLI 在**审计方 main 树**独立复跑，8/8 一致；5/5 变异捕获证明非空壳 |
| L3 系统集成 | **不成立** | `grep -rn 'wp_gate\|validate_work_package'` 全仓：只有 docs 引用，**0 个平台/主流程调用者**；`knowledge/extraction/` 不存在，无生产工作包流入；语义门 L3 依赖平台票据（外部两跳） |
| L4 基准验证 | **不成立** | 锚点 benchmark **0 行**、tensorbench **0 行**；无外部参考值可对标（§6 表末行） |
| L5 科研工程成果 | 不成立 | 无规模化生产实证（无在线真实报告 ⟶ 知识对象闭环样本） |

**判 L2 而非 L3 的一句话**：交付物是**真的、会判的**门禁（反例 5/5 被抓），但它在生态里**还没有下一个调用者**，且其证据链在 mainline 被 merge filter 削掉（§5.1）——功能实质 L2，整合度未到 L3。

---

## 复现命令

```bash
# 1) 工件复现（在审计方 main 工作树即可，fixtures 在 main）
cd /root/tp-agent/work/m15895
python scripts/validate_work_package.py --root tests/fixtures/extraction \
  --sources tests/fixtures/extraction/sources \
  --review-ledger-dir tests/fixtures/extraction/ledgers \
  --tickets-dir tests/fixtures/extraction/tickets \
  --skills extraction-skills/registry.json --json /tmp/sweep_main.json

# 2) 变异敏感度（harness 从 mission 分支夹具派生变异体）
python artifacts/audit_m15895/run_mutations.py --repo /root/tp-agent/work/m15494 \
  --out artifacts/audit_m15895/mutation_report.json
python artifacts/audit_m15895/figures_gate_audit.py

# 3) mission 侧单元测试（仅 agent/m15494 存在）
cd /root/tp-agent/work/m15494 && python -m pytest tests/test_wp_gate.py -q   # 40 passed
```