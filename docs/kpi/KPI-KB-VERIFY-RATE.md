# KPI-KB-VERIFY-RATE 计量报告（m19250 返修轮：L2 实现 + L4 基准）

> 本文件是 `runs/kpi_kb_verify_rate/KPI-KB-VERIFY-RATE.md`（程序化生成）的入库版，
> 正文由 `python -m tools.kpi_kb_verify_rate report` 注入，**数字零手抄**；
> 采集快照 `snapshot_sha256=348c9e05c8f2fa2769b9bdc06206938dcbd04cbda41c1662b6e3f09db67d64d6`，口径 `spec_sha256=22ee258a5afb3444f29ddecf7c3b7e811569ce1997d07c156f9411db1b86c943`。

## 0. 本单做了什么（能力位置，非自声明）

| 层 | 判据 | 本单证据 |
|---|---|---|
| L1 数学/单元 | 语义不变量机器判 | `tests/test_kpi_kb_verify_rate.py`（26 passed，含 0/0→null、分子>分母拒绝、指纹绑值、只读护栏） |
| L2 独立功能 | 真代码 输入→计算→输出 + 入口 + 运行工件 | `tools/kpi_kb_verify_rate/`（spec/backend/collect/compute/oracle/report/cli，`python -m tools.kpi_kb_verify_rate`）+ `runs/kpi_kb_verify_rate/{snapshot.json,result.json,KPI-KB-VERIFY-RATE.md,figures/*.png,data/*.tsv}` |
| L3 系统集成 | 存在非测试的调用方消费 result | `.github/workflows/kpi-kb-verify-rate.yml`（CI 闸门：selftest → pytest → bench，消费 result/bench 判定，失败即红）；`scripts/` 侧无 DB 写入（本单禁改数据） |
| L4 基准 | ref vs got 数值对照 + repro_cmd | `benchmarks/kpi_kb_verify_rate/`（三层基准，见 §L4 表）+ `result.json.repro_cmd` |

### L4 基准台账（ref vs got）

# KPI-KB-VERIFY-RATE ref vs got（程序化生成，勿手改）

| tier | case | ref (num/den/current) | got (num/den/current) | abs err | pass |
|---|---|---|---|---|---|
| A | mixed-10ko | 1/8/0.125 | 1/8/0.125 | 0 | PASS |
| A | empty-db | 0/0/None | 0/0/None | 0 | PASS |
| A | two-of-three | 2/3/0.6666666666666666 | 2/3/0.6666666666666666 | 0 | PASS |
| B | mixed-10ko | 1/8/0.125 | 1/8/0.125 | 0.0 | PASS |
| B | empty-db | 0/0/None | 0/0/None | None | PASS |
| B | two-of-three | 2/3/0.6666666666666666 | 2/3/0.6666666666666666 | 0.0 | PASS |
| C | live | 0/5338 | 0/5338 |  | PASS |


- Tier A：ref=显式集合枚举+Fraction（手工推导，写在 `cases.json` 的 `derivation` 字段），got=计量器算术；容差 0。
- Tier B：ref=`cases.json.expect`，got=**计量器自己的 spec SQL** 跑在一次性 scratch 库（`kpi_verify_rate_bench`，前缀护栏防误删真库）上；容差 0。
- Tier C：ref=`oracle.py` 独立写法（状态机事件表 + EXISTS 半连接，返回 id 集合），got=spec 主路；判等=计数相等且分母 id 集合相等。
- `not_run ≠ pass`：无 PG 的节点上 Tier B/C 标 not_run 并在 summary 里显式说明。

## 0.1 发布记录

- 平台报告：`tensor_reports#17676`（title=KPI-KB-VERIFY-RATE 周期复测…，figures=3 内嵌 PNG）。
- 复现方式：`runs/kpi_kb_verify_rate/result.json.repro_cmd` 五条命令（collect/measure/verify/bench/pytest），
  活库现值随快照 `snapshot_sha256` 绑定，引用时必须带指纹。

## 1. 数值结论（一句话）

**KPI-KB-VERIFY-RATE 现值 = 0.0000%（0/5338），
target = null（NOT_CALIBRATED），gap 无法计算 —— 目标未定标，按总账口径只报现值、不消账。**

---

# KPI-KB-VERIFY-RATE 周期复测计量（只读计量单）

- 锚点：`feature_ledger#164` `KPI-KB-VERIFY-RATE`（分子=L3候选中经平台验证单+gate confirmed 通过数，分母=进入验证流程的KO数；目标值由 RCI-F1 试点评估定标）
- 口径 spec：`kpi-kb-verify-rate/spec@1` / `spec_sha256=22ee258a5afb3444f29ddecf7c3b7e811569ce1997d07c156f9411db1b86c943`
- 快照：`snapshot_sha256=348c9e05c8f2fa2769b9bdc06206938dcbd04cbda41c1662b6e3f09db67d64d6` 采集于 2026-11-13T21:08:43Z
- **现值 current = 0.0000%**（分子 0 / 分母 5338）
- 目标 target = `null`（NOT_CALIBRATED）：docs/rci-f1-abc/REPORT.md（RCI-F1 试点评估，未结算前不定标）

## ① 案例介绍（KPI 口径与数据面）

本单计量的是「知识对象（KO）从进入验证流程到经平台验证通过」的转化率，它衡量知识治理链路是否真的把 KO 推到可验证状态，而不是衡量文档/代码产量。

| 量 | 定义（冻结） |
|---|---|
| 分子 | ko_object.storage_level='L3' AND ko_object.verification_status='platform_verified' AND EXISTS(ko_verification.gate_state='confirmed' AND gate_level>=2) |
| 分母 | ko_compiler_v1.ko_object.verification_status IN ('report_claimed','platform_verified') |
| 目标 | 由 RCI-F1 试点评估定标（当前 `NOT_CALIBRATED`） |

数据面（两个库、全部只读）：

| 逻辑库 | 表 | 作用 |
|---|---|---|
| `ke_service` | `ko_compiler_v1.ko_object` | diagnostic |
| `ke_service` | `ko_compiler_v1.ko_state_event` | diagnostic |
| `ke_service` | `ko_compiler_v1.ko_object+ko_verification` | numerator |
| `ke_service` | `ko_compiler_v1.ko_verification` | diagnostic |
| `ke_service` | `ko_compiler_v1.ko_evidence` | diagnostic |
| `tensorplatform` | `tensor_maturity_verdicts` | crosscheck |
| `tensorplatform` | `tensor_benchmark_cases` | crosscheck |
| `tensorplatform` | `feature_ledger` | meta |

## ② 怎么做的（方法 / 工具链 / 可复算设计）

1. **采集**：`python -m tools.kpi_kb_verify_rate collect` 以只读连接（服务端 `default_transaction_read_only=on` + 静态 SELECT 校验）执行 spec 登记的 26 条 SQL，落 `snapshot.json`（含每条 SQL 原文与 sha256 指纹）。
2. **算核**：`compute.build_result()` 是纯函数（不连库、不读时钟），把 snapshot 变成 result JSON；`0/0` 判为**未定义**（null），绝不写 0。
3. **双路径复核**：`oracle.py` 用另一种写法（状态机事件表数分母、`EXISTS` 半连接取分子 id 集）独立复算，判等不只是数字相等，还比 id 集合相等。
4. **基准（ref vs got）**：`bench.py` 三层（口径语义 / scratch 库真 SQL / 活库双路径）。
5. **工件**：result JSON + 六要素报告 + 三张图，全部由同一次采样程序化生成。

```bash
python -m tools.kpi_kb_verify_rate collect --out runs/kpi_kb_verify_rate
python -m tools.kpi_kb_verify_rate measure --snapshot runs/kpi_kb_verify_rate/snapshot.json --out runs/kpi_kb_verify_rate
python -m tools.kpi_kb_verify_rate verify --snapshot runs/kpi_kb_verify_rate/snapshot.json
python -m tools.kpi_kb_verify_rate bench --out benchmarks/kpi_kb_verify_rate
python -m pytest tests/test_kpi_kb_verify_rate.py -q
```

## ③ 计算结果（程序化注入，零手抄）

### 3.1 KPI 现值

| 项 | 值 | 推导 |
|---|---|---|
| 分子 numerator | 0 | `num_l3_gate_confirmed`：`storage_level='L3' ∧ verification_status='platform_verified' ∧ 验证单 confirmed(gate_level≥2)` |
| 分母 denominator | 5338 | `ko_enter_flow`：`verification_status ∈ {report_claimed, platform_verified}` |
| current | 0.0000% | 分子/分母（分母=0 → null） |
| 95% Wilson 区间 | [0.0000%, 0.0719%] | 分子=0、n=5338 |
| target / gap | `null` / `null` | 目标未定标 -> 不消账（NOT_CALIBRATED） |

### 3.2 链路逐级漏斗（原始计数，全部可 SQL 复算）

| 环节 | 计数 | 字段 |
|---|---|---|
| KO 总数 | 5338 | `ko_total` |
| 进入验证流程 | 5338 | `ko_enter_flow` |
| 状态机事件显示已进入流程 | 5338 | `ko_enter_flow_events` |
| L3 候选 | 0 | `ko_l3_candidates` |
| 平台已验证 | 0 | `ko_platform_verified` |
| 验证单总数 | 0 | `verification_tickets` |
| L3 且 gate confirmed（=分子） | 0 | `num_l3_gate_confirmed` |

### 3.3 灵敏度（同数据、不同口径解释；headline 只引主口径）

| 口径 | 分子 | 分母 | 现值 |
|---|---|---|---|
| PRIMARY: L3 ∧ platform_verified ∧ confirmed(>=2) / report_claimed∪platform_verified | 0 | 5338 | 0.0000% |
| MOLECULE-RELAXED: 任意 storage_level 的 confirmed(>=2) / 同分母 | 0 | 5338 | 0.0000% |
| TICKET-ONLY: confirmed 验证单数 / 分母=开过验证单的 KO 数（未开单则未定义） | 0 | 0 | 未定义(0/0) |
| ALL-KO: 同分子 / ko_total（把未进入流程的 KO 也算分母） | 0 | 5338 | 0.0000% |

### 3.4 状态分布

| verification_status | 计数 |
|---|---|
| `report_claimed` | 5338 |

| storage_level | 计数 |
|---|---|
| `L2` | 5338 |

## ④ 结果图

![fig1](figures/fig1_funnel.png)
**图1** 验证链路逐级漏斗：从 KO 总数到 gate confirmed 分子，每级都标注计数；断点位置直接指出分子为 0 的机制性原因。

![fig2](figures/fig2_sensitivity.png)
**图2** 四条口径的现值对照（主口径带 95% Wilson 区间）。任何口径下现值都不被「好看」地放大。

![fig3](figures/fig3_data_quality.png)
**图3** 分母与证据层的数据质量画像：证据 `artifact_kind` 分布、平台 verdict gate 状态分布，以及单 producer 批量灌入的窗口。

## ⑤ 注意点（坑 / 局限 / 适用范围）

- **分母质量**：`5338` 条 KO 由 1 个 producer 在 146.0 秒内写入、覆盖 181 个 domain ——分母真实性未证，现值应连同该画像一起引用。
- **证据层**：`artifact_kind='none'` 证据 5338 条 / 总 5338 条，可解析工件证据的 KO 数为 0——gate 若要求工件证据，则分子在结构上无法抬升。
- **验证单通道**：`ko_verification` 共 0 张，confirmed 0 张。
- **口径敏感性**：分母若改按「已开验证单的 KO」计，则 0/0 → KPI 未定义（不是 0%）；本报告因此始终把口径与数字一起引用。
- **只读边界**：本单不改任何代码/数据，不对平台库写入；缺口修复建议以派生锚点形式提出，由后续改进单执行。

## ⑥ 误差判定（逐项显式回答「是否 <3%」）

| 项 | ref（参照） | got（本计量器） | 偏差 | 是否 <3% |
|---|---|---|---|---|
| Tier A mixed-10ko：口径语义 | {'numerator': 1, 'denominator': 8, 'current': 0.125} | {'numerator': 1, 'denominator': 8, 'current': 0.125} | 0 | 是（精确 0） |
| Tier A empty-db：口径语义 | {'numerator': 0, 'denominator': 0, 'current': None} | {'numerator': 0, 'denominator': 0, 'current': None} | 0 | 是（精确 0） |
| Tier A two-of-three：口径语义 | {'numerator': 2, 'denominator': 3, 'current': 0.6666666666666666} | {'numerator': 2, 'denominator': 3, 'current': 0.6666666666666666} | 0 | 是（精确 0） |
| Tier B mixed-10ko：scratch 库真 SQL | {'numerator': 1, 'denominator': 8, 'current': 0.125, 'target_status': 'NOT_CALIBRATED', 'top_gap_ids': ['GAP-KO-DENOMINATOR-PROVENANCE']} | {'numerator': 1, 'denominator': 8, 'current': 0.125, 'target_status': 'NOT_CALIBRATED', 'top_gap_ids': ['GAP-KO-DENOMINATOR-PROVENANCE']} | counts Δ=0/0 | 是（精确 0） |
| Tier B empty-db：scratch 库真 SQL | {'numerator': 0, 'denominator': 0, 'current': None, 'target_status': 'NOT_CALIBRATED', 'top_gap_ids': ['GAP-KO-VERIFY-TICKET-ZERO', 'GAP-KPI-BENCH-REFEREE', 'GAP-PLATFORM-KO-SCOPE-VERDICT']} | {'numerator': 0, 'denominator': 0, 'current': None, 'target_status': 'NOT_CALIBRATED', 'top_gap_ids': ['GAP-KO-VERIFY-TICKET-ZERO', 'GAP-KPI-BENCH-REFEREE', 'GAP-PLATFORM-KO-SCOPE-VERDICT']} | counts Δ=0/0 | 是（精确 0） |
| Tier B two-of-three：scratch 库真 SQL | {'numerator': 2, 'denominator': 3, 'current': 0.6666666666666666, 'target_status': 'NOT_CALIBRATED', 'top_gap_ids': ['GAP-KO-DENOMINATOR-PROVENANCE']} | {'numerator': 2, 'denominator': 3, 'current': 0.6666666666666666, 'target_status': 'NOT_CALIBRATED', 'top_gap_ids': ['GAP-KO-DENOMINATOR-PROVENANCE']} | counts Δ=0/0 | 是（精确 0） |
| Tier C 活库双路径 | num/den=0/5338 | num/den=0/5338 | Δ=0/0 | 是（精确 0） |

**结论**：本次计量的数值本身没有「误差」之说（分子/分母都是精确计数，current 由整数除法得到），能判的是**两路独立实现是否给同一答案**：当前主路与独立 oracle 在活库上一致。**是否 <3%**：计数类判据为精确相等（0 偏差），故远小于 3%；但**目标值未定标**，因此「现状离目标差多少」这一项**无基准可判**，不以任何估计值填充。

## ⑦ 缺口与派生锚点（由 snapshot 程序化派生）

| 缺口 | 严重度 | 发现 | 推导式 |
|---|---|---|---|
| `GAP-KO-VERIFY-TICKET-ZERO` | blocking | 验证单通道零投产：ko_verification 无任何单据，分子在结构上只能是 0 | `verification_tickets(0) == 0 -> num_l3_gate_confirmed == 0` |
| `GAP-KO-EVIDENCE-ARTIFACT-NONE` | blocking | 证据层全是占位证据：artifact_kind='none' 覆盖全部证据行，gate 无物可确认 | `evidence_artifact_none(5338)/evidence_total(5338) = 100.0000%；ko_with_artifact_evidence=0` |
| `GAP-KO-L3-POOL-EMPTY` | blocking | L3 候选池为空：全部 KO 停在 L2，分子定义域本身为空 | `ko_l3_candidates(0) == 0（ko_total=5338）` |
| `GAP-KO-DENOMINATOR-PROVENANCE` | major | 分母质量存疑：单一 producer 在极短窗口内批量灌入全部 KO，真实性未证 | `producers(1)==1 且 span_seconds(146.0)<600，n=5338` |
| `GAP-KPI-BENCH-REFEREE` | major | 机器裁判缺位：tensor_benchmark_cases 对本锚点 0 行，KPI 型锚点无 ref-vs-got 基线可判 | `benchmark_cases_for_anchor(0) == 0` |
| `GAP-PLATFORM-KO-SCOPE-VERDICT` | minor | 平台 gate verdict 无 KO 作用域名，KPI 分子无法从平台侧交叉确认 | `verdicts_ko_scope(0) == 0` |

| 建议锚点 | derived_from | acceptance |
|---|---|---|
| `GAP-KO-VERIFY-TICKET-WIRE` | `verification_tickets=0` | ko_verification 出现 >=1 张由真实调用方（非测试夹具）写入的验证单，且 ko_state_event 有对应 to_status 流转事件；KPI 分子随之可非零 |
| `GAP-KO-EVIDENCE-ARTIFACT` | `ko_with_artifact_evidence=0/5338` | artifact_kind<>'none' 的 KO 数从 0 提升到 >=1%·ko_total（即 >=53 条）且抽查可解析 |
| `GAP-KO-L3-PROMOTION-RULE` | `ko_l3_candidates=0` | 定义并落库 L2->L3 提升判据（验证单 + 工件证据 + gate_level>=2），在 >=10 条 KO 上演练通过 |
| `CASE-KPI-KB-VERIFY-RATE-BENCH` | `benchmark_cases_for_anchor=0` | 在 tensor_benchmark_cases 登记 anchor_slug='KPI-KB-VERIFY-RATE'，metric='current+denominator'，tolerance='双路(SQL 主路 vs 独立 oracle)复算一致 0 偏差'；CI 每次跑 tools/kpi_kb_verify_rate bench 判绿 |

