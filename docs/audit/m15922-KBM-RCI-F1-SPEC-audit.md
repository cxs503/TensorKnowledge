# m15922 交差核验报告 —— m15913（KBM-RCI-F1-SPEC / RCI Knowledge Factory 生产规范+工作包）

**核验对象**：TensorKnowledge · mission 15913 · branch `agent/m15913` · commit `355218c357bfc65734c99caf54ffa4710e61cce7`
（`m15913: 生产线执行面 wp_line（五工序 DAG + 门禁绑定 + 综合准入）与参考-实测基准`，2026-11-12 04:34:55Z）
**核验单**：mission 15922（board-audit，只读被审工作树 `/root/tp-agent/work/m15913`，产物只写本工作树）
**原始报告**：tensor_reports id=15052（6 段齐全，1 图）
**复算脚本**：`docs/audit/verify_m15913.py` → 机器可读结果 `docs/audit/repro/verify_result.json`
**判决**：实级 **L4（基准验证）**；平台门禁机器级 **预计 L2**（原因 F1：分支未并入 main，门禁 grep 看不见调用方）。
**裁量**：approve with notes（批准 + 5 条须记录的限制/缺陷，其中 2 条属平台门禁面而非本单交付面）。

---

## 1. 判据（先于动手声明，可机器判）

| 项 | 判据 | 取证手段 | 结果 |
|---|---|---|---|
| A1 基准可复现 | 重跑 `ke.wp_line.run_benchmark()`，9 个字段（metrics/fixtures/mutations/…）与仓内 `benchmark.json` 全等 | `verify_m15913.py` A1 | **PASS** 全等 |
| A2 基准可证伪 | 篡改参考表 1 行 → 指标掉分且退出码非 0 | A2 负对照 | **PASS** verdict_agreement 1.0→0.875，exit=3 |
| A3 平台基准注册 | `tensor_benchmark_cases WHERE anchor_slug='KBM-RCI-F1-SPEC'` 有行 | psql | **FAIL（0 行）** → 平台侧无该锚点基准，见 F2 |
| A4 运行工件 | 6 件 run_artifacts 存在且 JSON 合法 | A4 | **PASS** 4 JSON 全合法 |
| A5 真平台回环 | process 01 登记的 5 份报告，按平台 live markdown 重算 sha256 全等 | A5 | **PASS** 5/5 hash + length 全等 |
| A6 报告六段 | ①…⑥ 齐全 + 显式回答“是否<3%” | A6 | **PASS**（6/6，含“误差判定”表） |
| A7 测试 | `pytest tests/test_wp_line.py tests/test_wp_gate.py -q` | 独立执行 | **PASS** 72 passed / 4.35s |

## 2. 三件套逐项核验（不是看报告，是看工件）

**run_artifacts（真实运行工件）**：`docs/production/run-artifacts/{benchmark,line_report,synthesis_input,asset_registration}.json + RESULTS.md + RUN-LOG.md`。
其中 `asset_registration.json` 的 5 个 `source_hash` **由核验方用平台 live 正文重算**（A5）：15044/15045/15047/15048/15050 五份报告
`sha256` 与 `length_chars` 全等 → 工件不是手抄，是当时真调用平台产物。

**benchmark（ref vs got 数值）**：`benchmark.json` 声明 5 指标、阈值先声明后测：

| 指标 | 阈值 | 声明 got | 核验方复算 got | 判 |
|---|---|---|---|---|
| verdict_agreement（8 夹具） | 1.00 | 1.0（8/8） | 1.0（8/8） | PASS |
| rule_agreement | 1.00 | 1.0 | 1.0 | PASS |
| level_agreement | 1.00 | 1.0 | 1.0 | PASS |
| mutation_detection（21 变异） | 1.00 | 21/21 | 21/21 | PASS |
| rule_coverage（27 规则） | 0.90 | 27/27 | 27/27 | PASS |

参考标签来源核验：`docs/production/GATE-RULES.md` 的夹具矩阵，提交 `a1c0c76`（m15494）**先于**实现提交 `355218c`（m15913）
——`git log -- docs/production/GATE-RULES.md` 只显示 a1c0c76，故“先声明后测”成立（时间独立性）。

**repro_cmd（可执行）**：`RUNNER.md §1` 四条命令，核验方实跑 3 条：
`pytest … → 72 passed`；`python -m ke.wp_line bench → exit 0 且与仓内工件逐字段相同`；
`python -m ke.wp_line run --root tests/fixtures/extraction … → exit 2`（设计上 5 个 bad 包红，3 清 5 败，
`05 synthesis blocked: base processing incomplete`）。第三条**真退出码=2**（与 mission result 声明一致）。

## 3. 复算带来的额外证据（原报告没有的）

1. **负对照**（A2）：把 `bad-no-evidence` 的参考 verdict 改成 `PASS_PROGRAMMATIC_PENDING_REVIEW` 后，
   `verdict_agreement` 掉到 0.875、`below_threshold` 非空、进程退出码 3 → 基准对参考标签敏感，
   不是“恒 1.0 的自我确认”。
2. **工件全量重建对照**：`python scripts/wp_line_artifacts.py --out /tmp/…`（离线）重建后
   `benchmark.json`、`line_report.json` 与仓内版本**逐字节相同**；`synthesis_input.json` 仅临时目录名不同。
   → 运行工件可重建，非一次性快照。
3. **同源缺陷探测**（见 F3）：离线重建退出码 0，却写出 `n_reachable=0 / n_unreachable=5` 的资产登记，
   工件里没有 mode 字段区分 online/offline。

## 4. 级别判定（L0–L5，级别=功能实质）

| 级 | 判据 | 本单证据 | 判 |
|---|---|---|---|
| L0 | 文档成果 | 不止文档 | — |
| L1 | 数学/单元验证 | 72 例单测（38 例 wp_line + 33 例 wp_gate 函数） | 过 |
| L2 | 独立功能实现（输入→计算→输出） | `ke/wp_line.py` 1337 行：`build_contract/plan_report/discover/spine_gate/register_assets/run_line/assemble_synthesis_input/run_benchmark` + CLI 8 子命令；输入=夹具根目录，输出=line_report/benchmark JSON | **过** |
| L3 | 系统集成 | `scripts/run_wp_line.py:22 from ke.wp_line import main`（平台派发入口，同一入口两表面，测试 `test_platform_wrapper_exposes_the_same_entry` 断言）；`ke/wp_line.py` 调既有 `ke/wp_gate.run_gates`（不另立门禁真源）；process 01 真打平台 API（5/5 哈希核验） | **过（限 F1）** |
| L4 | 基准验证（完整算例+误差分析+可复现） | 8 夹具算例 + 21 变异算例 + 5 指标对照先声明阈值 + 逐项误差（0 不一致）+ 核验方独立复算全等 + 负对照可证伪 | **过** |
| L5 | 科研工程成果 | 无外部科学基准/跨机构对照，属工程交付 | 不主张 |

**为什么不是 L2/L3**：有完整算例集（8+21）、有预声明阈值、有第三方（本核验）逐字段复算、有负对照证伪力。
**为什么不给 L5**：参考标签与门禁同一血脉（详见 F4），本质是自洽性/规范一致性验证，不是物理/实验基准，也不含规模压测。

### 4.1 级别裁量的两种读法（显式声明，不藏）

- **读法 A（本单采纳，L4）**：本生态的“平台接入面”惯例=脚本入口（如 `scripts/ko_v1.py`、`kf_submit_wp*.py` 等
  派发单入口），本单 `scripts/run_wp_line.py` 即该表面，且实际消费平台 live 报告（A5 5/5 哈希核验）
  与既有门禁模块 `ke/wp_gate.run_gates`（不另立真源）→ L3 成立；其上再有 8+21 算例、预声明阈值、独立复算、
  负对照 → L4。
- **读法 B（更严）**：把 L3 读作“被平台服务调用”（HTTP 路由/调度器注册），则本单只有 CLI 包装，
  L3 不成立，应判 L2。差异根源=生态缺“生产线 runner 是否要注册进 ke/api.py”的成文规定。
- 两种读法下 **L2 是共同下界**（真代码+入口+真工件），机器门禁本轮也落在 L2（F1）。
  级别分歧不影响“不是 STUB/MOCK”的结论：A1/A2/A5 已证实现与工件是真的。

## 5. 缺陷与限制（按严重度）

- **F1（中，平台面）** 生态仓 main 未含本单代码：`git merge-base --is-ancestor agent/m15913 main` → NOT_MERGED；
  ECO 检出 main 连 m15494 的 `ke/wp_gate.py` 都没有。门禁 `maturity_gate.callers_verified()` 用
  `grep -rl --include=*.py` 在 ECO/{repo}（main 工作树）里找调用方 → **必然找不到**，L3/L4 的 `integration_callers`
  键会被判缺失、机器降到 L2。这不是本单交付缺陷，是“先裁后并”时序 + 门禁 grep 口径的组合盲区。
- **F2（中，锚点面）** `tensor_benchmark_cases` 全表 25 行/25 锚点，**无 KBM-RCI-F1-SPEC**（0 行）。
  交差单预设“对照 tensor_benchmark_cases 逐项核 got”，现实无可对照行；本次核验改用仓内预注册参考表
  （先于实现提交）+ 独立复算 + 负对照，等价达到“基准裁判”目的，但平台侧该锚点仍缺登记 → 建议补一行（ref=GATE-RULES 夹具矩阵）。
- **F3（低，交付面）** 离线重建 `scripts/wp_line_artifacts.py --out …` 退出码 0，`asset_registration.json` 落
  `n_reachable=0,n_unreachable=5`，工件无 `mode=online|offline` 字段：读者可能把“离线空登记”误当“平台不可达”。
  建议：落 mode 标记；要求 online 而源不可达时非零退出。
- **F4（低，方法面）** 基准的 ref 标签（GATE-RULES 夹具矩阵）与 got 的产生器（`ke/wp_gate.py`）出自同一项目血脉，
  独立性仅靠“提交时序先声明”+变异矩阵。变异矩阵（21 个单点破坏→27 条规则全红）与本次负对照部分补足，
  但仍属规范一致性，不是外部真值。
- **F5（低，覆盖面）** 夹具根只含 03 类包，01/02/04/05 各 0 包（`line_report.json`）：04/05 的 DAG 阻断由单测
  （合成包）证明，非端到端；报告 §⑤ 与 RUNNER §5 已如实披露，不算隐瞒。
- **F6（提示）** `rule_coverage=27/27` 的分母来自 `implemented_rules()` 正则解析 `wp_gate.py` 源码（自指口径），
  度量的是“规则 id 是否都被弄红”，不等于“规则语义完备”。

## 6. 未跑 / 未判（unknown，不是 pass）

- 万份规模吞吐、并行调度、断点重试：**未跑**（交付自认未测，夹具 8 包不是压测）。
- process 01 附件内容抽取、技能库 K5/K6 接工序出口：**未跑**（交付列为下一轮）。
- GitHub CI（x86）与 loong64 一致性：**未跑**。
- 平台侧 merge/发布链路：**未干预**（不改 .git、不 push）。

## 7. 声明偏高的地方（overstated claims）

1. “平台派发入口”——实为 24 行 CLI 包装（`scripts/run_wp_line.py`），无 HTTP 路由、无 dispatcher 注册；
   接入强度=“脚本入口 + 同一实现两表面”，不宜读作“平台服务已接入”。
2. 报告 §⑥ 的“是否<3% ✓”是**一致率**口径（0 不一致），非数值误差；对工程/契约类交付成立，但与物理算例的 3% 含义不同，
   报告已声明口径，判为“表述需带口径”，不算造假。
3. mission result 的“integration_callers grep 'ke.wp_line' 命中 3 个 .py”——实测 3 处指向
   `scripts/run_wp_line.py:22`、`scripts/wp_line_artifacts.py:16`、`tests/test_wp_line.py:352`，其中 1 处是测试断言字符串，
   计数口径偏宽（不影响“存在真调用”结论）。

## 8. 处置（disposition）

**Approve with notes**：实级 L4，纳入台账；F1/F2 属平台门禁/基准登记面，另开小单（补基准注册行、门禁 grep 支持分支树或“先并后裁”）；
F3 建议随下轮返修（低风险，不影响本轮判定）。