# KF-RESULT wp-3076-04

**工序**：`04-independent-review`（lane C，TensorPapers | analysis）｜**审核对象**：`wp-3076-01`（report 3076）｜
**结论**：**needs-fix**（blocking 0 / major 5 / minor 4 / informational 2）｜
**审核者**：`redteam-reviewer-m15826`（red-team-reviewer，reviewer_type=agent）

## ① 本工序做了什么

对 report 3076（manuscript_gate v1：把 SEAL.md 的 H1–H8 硬伤固化为 11 项机检）做**独立审核**，判 `pass / fail / needs-fix`。
上下文只用两样：报告 markdown 原文（逐字节副本，sha256 自校验）+ 上游 `wp-3076-01` 的产物；**没有读、没有执行**
生产者的 `papers/tools/manuscript_gate.py` 与其测试，也没有取用生产者自写的 review prompt。

打法：凡能在报告文本之外独立重算的量都重算（色散式 → 波数 → coth/tanh 偏差），凡重算不了的一律记 `not_run`，
不当作通过。结论：**核心数字站得住**（H1 偏差序列 5/5 复现），**但汇总与证据口径有 5 处 major 缺陷**，故判 `needs-fix`。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文并自校验**：`GET /api/v1/tensor/reports/3076` 取 `markdown`（首版取数脚本未随本 PR 交付，见附录 B），
   落盘前自算 sha256 = `9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1` 与工单契约逐位比对；同时留档该记录的平台字段。只读 report 3076。
2. **独立重算**：`docs/wp-3076-04/independent_dispersion_check.py` —— 自写二分法（不用生产代码），按报告给出的
   ω²=(gk+Dk⁵/ρ_w)tanh(kh)、D=Eh_i³/(12(1-ν²)) 求解 k；**参数与“声称值”都由正则从原文抓取**
   （`params_quote` / `claimed_quote`），从源头杜绝手抄。再把 tanh 换成 coth 重解，逐周期算相对偏差对照。
3. **反证边界断言**：不采信“T≥14 s 无根”，在 k∈(0,10] 上扫 20001 点找**符号变化**再二分细化，
   并对 14.0/14.1/14.15/14.185/14.2/16/18/20/30/60 s 全列根，另解解析临界期 T_c=2π√(h/g)。
4. **同文自洽性审计**：解析 ③ 的 11 行结果表，重数 HARD 行与 FAIL 数，与汇总句“8/11”“0/11”对数 ——
   这是不依赖生产代码就能推翻的汇总级断言。
5. **引文定位**：15 条引文逐条定位（char_offset / line / occurrences），本包所有 `quote` 字段要求 `occurrences=1`。
6. **审核判据自写**（全文见附录 A；首版为独立文件 `review_prompt.md`，本 PR 折入正文以守 10 文件单元，见附录 B）：先尝试反证每个数字，再判 pass/fail/needs-fix。
7. 工具链：Python 3.11 + jsonschema 4.26（信封校验）+ pytest 9.2（自检，见 ⑥）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/wp-3076-04/review_report.json` | 审核报告本体（契约输出）：decision / findings / claims_assessment / checks_performed / checks_not_run / disposition |
| `docs/wp-3076-04/review_events.json` | append-only 审核台账 1 条：`request-changes`（ke-review-v0.1 词表），带 11 条 findings 与 8 条整改条件 |
| `docs/wp-3076-04/kf_result.wp-3076-04.json` | 平台结果信封（与文末 json 块同源） |
| `docs/wp-3076-04/independent_check.json` | 独立复算原始结果：偏差序列、根扫描、严重度表审计、15 条引文定位 |
| `docs/wp-3076-04/independent_dispersion_check.py` | 独立求解器 + 原文解析器（可一键复跑） |
| `docs/wp-3076-04/source.md` | 报告原文逐字节副本（= 平台记录 `markdown` 字段，sha256 自校验）；记录元数据见附录 C |
| `docs/wp-3076-04/publish_roundtrip.json` | 发布往返回执：markdown 与图件在平台侧的逐字节复核（本地 vs 取回 sha256） |
| 附录 A（本文件） | 本工序自写的 reviewer prompt（声明未复制生产 prompt）；首版独立文件的全文折入此处 |
| `scripts/kf_wp3076_04_*.py`（**未随本 PR 交付**） | 取原文 / 程序化生成全部产物的脚本：体积超出 10 文件单元，影响与替代见附录 B |
| `docs/wp-3076-04/KF-RESULT-wp-3076-04.md` | 本交付正文 |
| `tests/test_kf_wp3076_04.py` | 自检 12 项（含 4 个负控），见 ⑥ |
| `fig_deviation_boundary.png` | 结果图：偏差曲线（声称 vs 复算）+ coth 根存在性条带 |

**独立复算表（tanh 正解 vs coth 误式，k 单位 1/m）**

| T (s) | 声称偏差 | 复算偏差 | abs-delta (pp) | k_tanh | k_coth |
|---|---|---|---|---|---|
| 4 | 0.37% | 0.3689% | 0.001 | 5.582948e-02 | 5.562354e-02 |
| 6 | 1.31% | 1.3104% | 0.0 | 4.523599e-02 | 4.464322e-02 |
| 8 | 3.67% | 3.6656% | 0.004 | 3.778090e-02 | 3.639599e-02 |
| 10 | 9.60% | 9.6023% | 0.002 | 3.182759e-02 | 2.877142e-02 |
| 12 | 25.02% | 25.0179% | 0.002 | 2.689409e-02 | 2.016576e-02 |

**“coth 无根”边界探针**

| T (s) | coth 根（k∈(0,10]） | tanh 根 |
|---|---|---|
| 14.0 | 0.005625 | 0.022883 |
| 14.1 | 0.003803 | 0.022705 |
| 14.15 | 0.002437 | 0.022617 |
| 14.185 | 0.000075 | 0.022556 |
| 14.2 | 无根 | 0.022530 |
| 14.3 | 无根 | 0.022357 |
| 16 | 无根 | 0.019718 |
| 18 | 无根 | 0.017250 |
| 20 | 无根 | 0.015309 |
| 30 | 无根 | 0.009806 |
| 60 | 无根 | 0.004772 |

解析临界期 T_c=2π√(h/g) = 14.1850 s（coth 分支 RHS 在 k→0 的下确界 = g/h）。

**③ 表重数（严重度审计）**：解析到 11 行 = HARD 10 + SOFT 1；sealed HARD FAIL 8、
control HARD FAIL 0（SKIP 3）、sealed WARN 1。

| check | 严重度 | sealed | control |
|---|---|---|---|
| `struct` | HARD | WARN | PASS |
| `figref` | HARD | FAIL | PASS |
| `figdata` | HARD | FAIL | PASS |
| `numtrace` | HARD | FAIL | PASS |
| `formula` | HARD | FAIL | PASS |
| `overclaim` | HARD | FAIL | SKIP |
| `statdof` | HARD | FAIL | SKIP |
| `implmethod` | HARD | PASS | PASS |
| `repro` | HARD | FAIL | PASS |
| `placeholder` | SOFT | WARN | PASS |
| `arith` | HARD | FAIL | SKIP |

## ④ 证据定位表（claim/字段 → 原文逐字引文）

每条引文在 `docs/wp-3076-04/independent_check.json` 的 `locators` 里带 char_offset / line / occurrences=1，平台可独立重切。

| 定位键 | 原文逐字引文 | 行 | 字符偏移 | 出现次数 |
|---|---|---|---|---|
| `deviation_series` | `T=4s: 0.37%, T=6s: 1.31%, T=8s: 3.67%, T=10s: 9.60%, T=12s: 25.0…` | 49 | 2496 | 1 |
| `params` | `h=50.0 m、h_i=2.0 m、E=5.0×10⁹ Pa、ν=0.3、ρ_w=1025.0、ρ_i=917.0 kg/m³…` | 14 | 550 | 1 |
| `no_root` | `T≥14s 时 coth 形式在 k∈(0,10] 1/m 内**无根**` | 49 | 2563 | 1 |
| `eight_classes_all_checkable` | `复盘发现这八类**全部是` | 4 | 146 | 1 |
| `H5_not_machine_judgeable` | `H5 在该树上不可机判，**如实不报**` | 47 | 2441 | 1 |
| `control_pass` | `` control `verdict=PASS`，HARD 失败 0/11（SKIP 3 项） `` | 45 | 2239 | 1 |
| `sealed_verdict` | `HARD 失败 8/11` | 45 | 2226 | 1 |
| `neg_control_recall` | `7/7 复现` | 71 | 3475 | 1 |
| `pytest` | `pytest 19 passed` | 27 | 1347 | 1 |
| `tautological_3pct` | `正控 k vs 更紧容差解` | 70 | 3384 | 1 |
| `implmethod_h5` | `` `implmethod` 未能在封存树上复现 H5 `` | 75 | 3634 | 1 |
| `numtrace_tol` | `证据基 237 值，tol=0.005` | 36 | 1735 | 1 |
| `arith_enKF` | `抓到 EnKF 声称 8.65% vs 同行两量复算 8.33%` | 47 | 2407 | 1 |
| `figdata_proxy` | `` `figdata` 只是合成数据代理判据 `` | 75 | 3660 | 1 |
| `repro_triplet` | `三件套命中 0/3` | 41 | 2065 | 1 |

**结论 → 证据链**

| claim | 判定 | 依据 |
|---|---|---|
| C1-H1-deviation-series | supported | 独立实现复算 5/5 一致，最大 \|Δ\|=0.004 pp；T=8 s k_tanh=3.778090e-02 / k_coth=3.639599e-02 |
| C2-coth-nonphysical-branch | partially-supported | 根消失的临界期 T_c=14.185 s；T=14.0 s 仍有根 k=0.005625，故边界应写 T>14.19 s（F6） |
| C3-neg-control-recall-7of7 | supported | ③ 表中 formula/overclaim/figdata/figref/repro/statdof/arith 对 H1/H2/H3/H4/H6/H7/H8 均 FAIL，逐行可核；H3→figdata 为报告自述的代理判据 |
| C4-pos-control-zero-false-positive | partially-supported | HARD 实为 10 项（分母 11 错，F1），其中 3 项在正控 SKIP，实际执行且未误报的是 7/10（F2） |
| C5-pytest-19-passed | unresolved | 仅声明串，无 log/collector/run id；生产仓不在本工作树，未重跑（F9） |
| C6-control-residual-and-tighter-solve | partially-supported | 残差定义在生产者 solver 内，本工序无法复算；且“占门限 7.09%”与“相对误差 1e-14”两种读法结论相反，后者还是同码收紧容差的自洽（F4） |
| C7-implmethod-pass-on-sealed | refuted | 与“该稿存在 H5 实现-方法不符”冲突：作为 H5 判据它是假阴性，召回 0/1（F3） |

**发现清单（severity 排序）**

| id | severity | 标题 |
|---|---|---|
| F1 | major | HARD 分母与同文表格不一致：8/11、0/11 应为 8/10、0/10 |
| F2 | major | 正控只覆盖 7/10 项 HARD：overclaim/statdof/arith 在正控 SKIP，“0 误报”范围被高估 |
| F3 | major | implmethod 是已证实的假阴性：对已知 H5 硬伤稿判 PASS，召回 0/1 而非“不可机判” |
| F4 | major | ⑥“是否 <3%”列 5 行里 3 行属范畴误用或非独立对照 |
| F5 | major | 11 项判据中 5 处阈值/定义未披露，判据不可被独立复算 |
| F6 | minor | “T≥14 s 时 coth 无根”边界值错：独立复算 T=14.0 s 仍有根 |
| F7 | minor | ① 断言八类硬伤“全部”可机检，与 ③/⑤ 的“H5 不可机判”矛盾 |
| F8 | minor | 参数表列 ρ_i=917 kg/m³，但所给色散式不含 ρ_i |
| F9 | minor | “pytest 19 passed”仅为声明，无日志/哈希可核 |
| F10 | informational | numtrace 是存在性判据且“1 个 token 未溯源即 FAIL”，误报代价未量化 |
| F11 | informational | struct 标 HARD 却在已知 FAIL 稿上只给 WARN |

**执行的检查**

- R1 `source_hash_and_chars` → **PASS**：sha256=9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1 chars=3712 bytes=6092，与工单契约逐位一致
- R2 `quote_locatability` → **PASS**：15/15 条引文在原文逐字命中且 occurrences=1
- R3 `independent_solver_deviation_series` → **PASS**：T=4s 复算 0.3689% vs 声称 0.37%（|Δ|=0.001pp）；T=6s 复算 1.3104% vs 声称 1.31%（|Δ|=0.0pp）；T=8s 复算 3.6656% vs 声称 3.67%（|Δ|=0.004pp）；T=10s 复算 9.6023% vs 声称 9.60%（|Δ|=0.002pp）；T=12s 复算 25.0179% vs 声称 25.02%（|Δ|=0.002pp）
- R4 `coth_no_root_boundary` → **FAIL**：声称 T≥14 s 无根；复算 T=14.0 s 有根、T_c=14.185 s，T=14.2/16/18/20/30/60 s 无根 → 定性成立、边界值错（F6）
- R5 `severity_arithmetic_self_consistency` → **FAIL**：表内 HARD=10、SOFT=1；sealed FAIL=8；control FAIL=0（SKIP 3）；声称分母 11（F1）
- R6 `claim_to_table_crosscheck` → **PASS**：7/7 召回声明与表中 7 个映射类的 FAIL 状态逐行对应；同时暴露 implmethod PASS 与 H5 声明的冲突（F3）
- R7 `no_verified_label_written` → **PASS**：本审核不含 verified 字段/布尔；claim 状态只用 supported/partially-supported/unresolved/refuted
- R8 `report_id_boundary` → **PASS**：只读 report 3076 的 markdown 与其平台记录字段；未读写其它 report_id

**未执行的检查（如实记 not_run，不记 pass）**

- `gate_rerun（11 checks × sealed/control）` — not_run：生产仓 papers/ 不在本工作树；跨仓重跑不属本单授权
- `numtrace/overclaim/statdof/arith 实现复核` — not_run：无生产代码；仅复核其汇总与阈值披露
- `figdata 图-数一致性` — not_run：需封存稿与图件（跨 report_id / 私有稿）
- `pytest 19 passed 复现` — not_run：同上；报告未给 run id/log
- `正控残差 7.09e-14 / 2.48e-14 复算` — not_run：残差定义在生产 solver.py 内；本工序独立复算只能给 k，不能给其残差口径

**整改条件（判 needs-fix 的对价）**

1. F1：8/11、0/11 改为 8/10、0/10（或写“HARD 失败 8 / 检查项 11”），汇总直接从审计 JSON 取 HARD 计数
2. F2：正控补语料让 overclaim/statdof/arith 走 PASS 路径；做不到就把标题与 ⑥ 显式限定为 7/10 并列出 SKIP 项
3. F3：implmethod 在封存稿上的结果改记为 H5 召回 0/1（假阴性），不得与“通过”混列
4. F4：⑥ 每行注明比较对象（残差/门限占比/自洽/计数），改写或删除这 3 处“是”
5. F5：补齐 arith 容差、repro 三件套清单、struct 必需要素、overclaim 升格判据
6. F6：改“T≥14 s”为“T>14.19 s”，并注明 T=14.0 s 仍有根
7. F7：① 改为“其中七类可机检”
8. F8：说明 ρ_i 用途，或补上含板惯性项的式子

## ⑤ 注意点与局限

- **独立性边界**：生产仓不在本工作树，门禁 11 项 checks **没有重跑**。因此“sealed FAIL / control PASS”只作为报告的**自述**处理，
  不当作已证事实；能推翻的只有同文自洽性（F1 分母、F11 HARD/WARN 语义）。
- **跨报告边界**：封存稿正文、Report #823/#961 属其它 report_id 或私有稿，工单硬约束禁止读取，相关核对一律 `not_run`。
- 我重算的是**报告自己给出的式子**；若生产实现与该式不同（F8 的 ρ_i 暗示可能如此），复算只证明“报告式子算得出报告数字”，
  不证明“门禁正控算的就是这个式子”。
- **不越权标注**：本审核不含任何 `verified` 字段，claim 状态只用 supported / partially-supported / unresolved / refuted；
  verification 由平台门计算。
- 工单给本包的契约里 `review.required=false`，而验收项要求 `reviewer_independent=true`（契约层面不一致；我未改契约，仅在此标注）：
  M1 很可能对该包判红，与审核质量无关。
- 一条可复用的方法心得：**“汇总分母”是最廉价的造假探测点** —— 同文表格数出的 HARD 行数与汇总句分母只要对不上，
  就能在零生产代码前提下推翻一条汇总级结论（本包 F1 即由此抓到）。

## ⑥ 自检（逐条对照 acceptance）

### 误差判定（报告纪律要求的“是否 <3%”，逐项显式回答）

| 关键量 | 基准 | 本工序结果 | 是否 <3% |
|---|---|---|---|
| coth/tanh 偏差复算 vs 报告声称值（T=4/6/8/10/12 s 共 5 点） | 报告 ③ 的声称值 | 最大 abs-Δ = 0.004 pp（相当于 0.37–25.02% 各点上的相对偏差 ≤1.1%） | **是** |
| 复算波数 k（T=8 s） | 报告所给色散式的独立解 | k_tanh=3.778090e-02、k_coth=3.639599e-02（与声称 3.67% 一致到 0.004 pp） | **是** |
| coth 形式无根临界期 | 解析 T_c=2π√(h/g)=14.185 s | 扫根：T=14.0 s 有根 / T=14.2 s 无根，边界夹在 14.0–14.2 s | **是**（与解析值一致到 0.02 s） |
| coth 误式波数偏差（T=12 s） | tanh 正解 | 25.018%（报告声称 25.02%） | **否**（>15%）—— 该量是被审稿自身的缺陷量（H1 的定量依据），不是本工序的复算误差 |
| 门禁 11 项 checks 在 sealed/control 上的执行状态 | 生产实测 | 未重跑 | **无基准**：not_run，不判是否 <3% |

结论：本工序所有“可复现性误差”均 <3%（最大 0.004 pp）；表内唯一 >3% 的 25.018% 是**被审稿的缺陷量**，
按要求判“否”并据此给出 H1 的量化依据。门禁执行状态无基准，如实记 not_run，不含糊过关。

### acceptance 逐条

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | `review_report.json`、`review_events.json`、信封三者均可解析（tests T1/T2/T3） |
| `schema_pass` | ✅ | 信封过 `schemas/kf_result.v1.schema.json`；台账过 `schemas/review-event.schema.json`（T2/T3） |
| `reviewer_independent` | ✅ | reviewer `redteam-reviewer-m15826` 与生产者身份/token 无重叠，`ke_state_machine.is_independent` 复算通过（T5）；未读未跑生产代码（声明见附录 A） |
| `upstream_packages_completed` | ✅ | `docs/wp-3076-01/` 齐备（kf_result + asset_manifest + verification.json，自报 acceptance_all_pass=true）；本审核独立重算其源哈希与字符数 |
| 不复制生产 prompt | ✅ | 附录 A 为本工序自写，未取用生产 prompt（`prompt_similarity` 无法在无生产 prompt 时计算，故记 not_run 而非 pass，见下） |
| 不标 verified | ✅ | 全包无 verified 字段（T7 负控：出现 `"verified": true` 即红） |

**未达成的自检项（honest 声明）**：
- `prompt_similarity`（review prompt 与生产 prompt 的字面相似度）**not_run**：生产 prompt 不在本工作树的
  `FORBIDDEN_REVIEW_KEYS` 之外可得之处，工单也要求“reviewer context excludes producer explanation”，
  因此该指标只能在平台侧用双方 prompt 计算；我这边只留下自写 prompt 的全文与哈希供比对。
- 门禁 11 项 checks 的重跑 **not_run**（生产仓缺失），故本包不声称“复现了负控/正控”。

## 复跑（一键，两步，离线）

    python3 docs/wp-3076-04/independent_dispersion_check.py   # 重写 independent_check.json：偏差序列/根扫描/表审计/引文定位
    python3 -m pytest tests/test_kf_wp3076_04.py -q           # 12 项自检，含 4 个负控

首版的「取原文 → 构建 → 发布」三步依赖 `scripts/kf_wp3076_04_*.py` 与平台凭据，这些脚本未随本 PR 交付（附录 B）；
其不可重放性已在 `review_report.json.repro.not_replayable` 里显式记账，不当作已通过。

---

## 附录 A · 本工序自写的 reviewer prompt（逐字，声明未复制生产 prompt）

首版以独立文件 `docs/wp-3076-04/review_prompt.md` 交付（sha256 = `8aa3d727651a1cd7a9404258e182a23389fd2d7281699ec95eb15b51faf40059`）；为守 10 文件单元，本 PR 把该文件
执行逐字折入正文，内容零改动，**哈希仍可用于与任何生产 prompt 做字面比对**（`prompt_similarity` 本身仍记 `not_run`，
原因见 ⑥）。以下为原文全文：

**（原文开始）**

# reviewer prompt — wp-3076-04（本工序自写，未取用生产 prompt）

> 本文件是 `wp-3076-04` 的审核判据与提问方式，由本工序（独立审核者 `redteam-reviewer-m15826`）自写。
> 生产中工序的 prompt 未取用、未参照；按工单 `review_prompt_not_copied_from_producer` 的要求，
> 本文件的存在本身就是可核的物证（可用 sha256 与任何生产 prompt 比对字面相似度）。

## 输入（只读，且只有这两类）

1. `artifacts/wp-3076-04/r3076.md` —— report 3076 的 `markdown` 字段逐字节副本（sha256 自校验）。
2. `docs/wp-3076-01/` —— 上游 01 工序产物（kf_result 信封 + asset_manifest + verification）。

明确排除：生产者的实现代码与测试、生产者自述的实施过程、任何跨 report_id 的私有稿。

## 提问顺序（先反证，再判）

1. **数字可复现吗？** 挑出报告里“能与原文之外的世界对上”的量（本例：色散式 → 波数 → coth/tanh 偏差），
   用**自己写的**求解器重算；参数与声称值都从原文正则抓取，禁止手抄。
2. **同一份材料自洽吗？** 汇总句的数字能否由文内表格重数出来？（分母/分子/计数口径）
3. **“不误报”的证据覆盖了哪些项？** SKIP 不算通过；正控必须真的走过每条检查的 PASS 路径。
4. **假阴性怎么记？** 检查存在、执行了、给出 PASS，而目标缺陷已知存在 → 记假阴性（召回 0/1），
   不得记作“不可机判”或“通过”。
5. **误差口径对得上吗？** “<3%”必须指明比较对象（vs 基准值 / vs 门限 / vs 自洽解 / 计数率），
   量纲不同的行不得统一填“是”。
6. **判据能被第二个人复算吗？** 阈值、清单、定义是否齐全；缺一项即记 cannot-recompute。
7. **边界断言真的成立吗？** 对“T≥14 s 无根”这类区间断言，扫根而不是采信；找出解析临界值。
8. **哪些没做？** 一律记 `not_run`，不记 pass；跨报告/跨仓的核对如实写未执行。

## 判定规则

- `pass`：核心数字可独立复现，且汇总/证据口径无 major 级缺陷。
- `needs-fix`：核心结论站得住，但存在可用改报告/补语料修好的 major 缺陷（默认档）。
- `fail`：核心数字不可复现，或存在无法通过改文字修复的事实错误。

## 红线（自设）

- 不写 `verified`；claim 状态只用 supported / partially-supported / unresolved / refuted。
- 每条 finding 必须绑定原文逐字引文（`occurrences == 1`），否则不写。
- 不因为“honest 声明存在”而降低标准，也不因为“作者已承认”就免去 finding —— 承认不等于修好。

**（原文结束）**

## 附录 B · 交付范围与裁剪说明（10 文件单元）

| 项 | 首版（PR#313，17 文件） | 本 PR（10 文件） | 依据 |
|---|---|---|---|
| reviewer prompt | 独立文件 `review_prompt.md` | 折入本文件附录 A（逐字，sha256 保留） | 10 文件单元纪律 |
| 平台记录元数据 | 独立文件 `source.record.json`（含 `markdown` 全文副本） | 折入附录 C 表格；`markdown` 与 `source.md` 逐字节相同故不重复留档 | 同上 |
| 取数/构建/发布脚本 | `scripts/kf_wp3076_04_{fetch_report,build,figure,publish}.py`（4 个） | **不交付** | 同上 |
| 产物与自检 | 同 | `docs/wp-3076-04/` 9 件 + `tests/test_kf_wp3076_04.py` | — |

**裁剪造成的可核性缺口（如实记账，不粉饰）**：

1. **不能一键重建产物**：`review_report.json` / `review_events.json` / 信封 / 图件由首版构建脚本写出，本 PR 不含该脚本。
   替代守门：自检 T9 断言正文 json 块与信封文件**解析后逐字段等价**、T1–T3 断言三者 schema 通过、T6 断言 15+ 条引文
   在 `source.md` 中逐字可分片、T8 用交付的 `independent_dispersion_check.py` 独立重算并复现 H1 结论。
2. **不能重放发布**：`publish_roundtrip.json` 记录的是本交付体在平台侧的实测往返（本地 sha256 vs 取回 sha256），
   但发布动作本身不可在仓内重放（脚本未交付、且报告不可改写）。
3. **原文可取回**：`source.md` 在复开时再次与平台 `tensor://reports/3076` 对账，sha256 与字符数逐位一致
   （见附录 C），故「审核输入的保真度」这一环仍可被第三方独立复算。
4. 若评审要求完整重建链，可把 4 个脚本作为**独立后续 PR**（单一功能点：可重建性）补入，不并入本 PR。

## 附录 C · 平台记录字段（`tensor://reports/3076`，审核输入留档）

| 字段 | 值 |
|---|---|
| `id` | 3076 |
| `title` | 成稿机检门禁 manuscript_gate v1：把 SEAL.md 的 H1–H8 硬伤固化为 11 项机检（负控复现 8 项 / 正控 0 误报） |
| `scenario_key` | `paper-line-provenance-gate` |
| `mission_id` | 3012 |
| `status` | `published` |
| `created_by` | 1 |
| `created_at` | 2026-11-03T23:35:19.261537+00:00 |
| `tags` | paper-production / provenance-gate / manuscript-conformance / verification-debt / pytest / honest-FAIL |
| 声明图件（3 张，`declared_payload_missing`） | `gate_state_matrix.png`、`gate_numtrace_dev.png`、`gate_coth_tanh.png` |
| `markdown` | **= `source.md` 字节**：chars 3712 / bytes 6092 / sha256 `9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1` |

图件说明：报告自述的 3 张图在平台侧 `GET /tensor/reports/3076/figures/<name>` 均 404（`figure not found`），
故上游 `wp-3076-01` 把它们登记为「有名字和图注、无载荷字节」；本审核沿用该登记，不假设图件存在。

```json
{
  "package_id": "wp-3076-04",
  "task_type": "04-independent-review",
  "report_id": "3076",
  "provenance": {
    "source_hash": "sha256:9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1",
    "source_uri": "tensor://reports/3076",
    "source_field": "markdown",
    "producer": "kf-wp3076-04 independent review",
    "emitted_at": "2026-11-12T02:50:00Z",
    "notes": "source_hash = sha256 of the UTF-8 bytes of report 3076 markdown, recomputed by the reviewer; wp-3076-01 gate statuses are NOT re-executed (producer repo not in this worktree) and are reviewed as claims, never as verified facts; no claim is labelled verified; re-landed on main 2026-11-15 as a 10-file unit: reviewer prompt and platform-record metadata folded into the KF-RESULT body (appendices A/C), fetch/build/publish scripts not shipped (appendix B); no number changed, source.md re-verified byte-identical against tensor://reports/3076 at re-land time"
  },
  "outputs": {
    "review_report.json": {
      "schema": "review_report.v1",
      "package_id": "wp-3076-04",
      "task_type": "04-independent-review",
      "report_id": "3076",
      "reviewed_package": "wp-3076-01",
      "reviewed_object": {
        "source_uri": "tensor://reports/3076",
        "source_field": "markdown",
        "source_hash": "sha256:9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1",
        "chars": 3712,
        "bytes_utf8": 6092,
        "title": "成稿机检门禁 manuscript_gate v1：把 SEAL.md 的 H1–H8 硬伤固化为 11 项机检（负控复现 8 项 / 正控 0 误报）",
        "hash_recomputed_by_reviewer": true
      },
      "reviewer": {
        "id": "redteam-reviewer-m15826",
        "reviewer_type": "agent",
        "role": "red-team-reviewer",
        "reviewed_at": "2026-11-12T02:50:00Z",
        "independence_basis": "distinct-identity：与生产者在身份串与 8-hex session token 上无重叠"
      },
      "independence": {
        "context_used": [
          "docs/wp-3076-04/source.md（report 3076 markdown 逐字节副本，哈希自校验）",
          "docs/wp-3076-01/kf_result.wp-3076-01.json 与 asset_manifest.json（上游 01 工序产物，已在本仓）"
        ],
        "context_excluded": [
          "生产者的 papers/tools/manuscript_gate.py 及其测试：未读、未执行",
          "生产者自写的 review prompt：未取用；本工序 review prompt 自写（全文逐字留档见 KF-RESULT-wp-3076-04.md 附录 A；首版独立文件 review_prompt.md 已折入正文，理由见附录 B）",
          "生产者的解释性对话内容：不可得，也未索取"
        ],
        "limitations": [
          "生产仓（papers/、papers/data/gate-2026-11-03/control/）不在本工作树：门禁 11 项 checks 未重跑，PASS/FAIL/SKIP 状态按报告自述采信，仅用同文表格自洽性推翻可推翻者（F1/F11）",
          "依赖 246 行封存稿正文与 Report #823/#961 的核对未执行：跨 report_id，工单硬约束禁止",
          "仅重算了报告给出的色散式与偏差序列（独立实现），未复核 numtrace/overclaim/statdof/arith/figdata 的实现"
        ]
      },
      "review_events_file": "docs/wp-3076-04/review_events.json",
      "decision": "needs-fix",
      "decision_reason": "核心可验证量成立：H1 偏差序列 5/5 被独立实现复现（最大 |Δ|≤0.004 pp），负控 7/7 映射与表格自洽，源哈希一致，honest 声明真实存在且未把结论标 verified。但确凿缺陷足以要求修改：汇总算术错（HARD 分母 11≠10，F1）；标题级“正控 0 误报”覆盖被高估（3 项 HARD 在正控 SKIP，F2）；implmethod 对目标硬伤类是已证实的假阴性却记 PASS（F3）；⑥ 的“<3%”列 5 行中 3 行范畴误用或非独立对照（F4）；5 处判据阈值/定义未披露使 11 项判据不可独立复算（F5）。这些都能在不动内核的情况下修好，故判 needs-fix 而非 fail。",
      "scorecard": {
        "semantic_fidelity": "partially-faithful",
        "numbers_independently_reproducible": "5/5（H1 偏差序列）；门禁状态 0 项重跑（not_run）",
        "honest_failure_declaration": "present-and-consistent",
        "boundaries_respected": "pass（未读写其它 report_id；未标 verified）",
        "acceptance_items": {
          "valid_json": "pass",
          "schema_pass": "pass",
          "reviewer_independent": "pass",
          "upstream_packages_completed": "pass（wp-3076-01 产物齐备，其 verification.json 自报 acceptance_all_pass=true）"
        }
      },
      "checks_performed": [
        {
          "id": "R1",
          "check": "source_hash_and_chars",
          "result": "PASS",
          "detail": "sha256=9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1 chars=3712 bytes=6092，与工单契约逐位一致"
        },
        {
          "id": "R2",
          "check": "quote_locatability",
          "result": "PASS",
          "detail": "15/15 条引文在原文逐字命中且 occurrences=1"
        },
        {
          "id": "R3",
          "check": "independent_solver_deviation_series",
          "result": "PASS",
          "detail": "T=4s 复算 0.3689% vs 声称 0.37%（|Δ|=0.001pp）；T=6s 复算 1.3104% vs 声称 1.31%（|Δ|=0.0pp）；T=8s 复算 3.6656% vs 声称 3.67%（|Δ|=0.004pp）；T=10s 复算 9.6023% vs 声称 9.60%（|Δ|=0.002pp）；T=12s 复算 25.0179% vs 声称 25.02%（|Δ|=0.002pp）"
        },
        {
          "id": "R4",
          "check": "coth_no_root_boundary",
          "result": "FAIL",
          "detail": "声称 T≥14 s 无根；复算 T=14.0 s 有根、T_c=14.185 s，T=14.2/16/18/20/30/60 s 无根 → 定性成立、边界值错（F6）"
        },
        {
          "id": "R5",
          "check": "severity_arithmetic_self_consistency",
          "result": "FAIL",
          "detail": "表内 HARD=10、SOFT=1；sealed FAIL=8；control FAIL=0（SKIP 3）；声称分母 11（F1）"
        },
        {
          "id": "R6",
          "check": "claim_to_table_crosscheck",
          "result": "PASS",
          "detail": "7/7 召回声明与表中 7 个映射类的 FAIL 状态逐行对应；同时暴露 implmethod PASS 与 H5 声明的冲突（F3）"
        },
        {
          "id": "R7",
          "check": "no_verified_label_written",
          "result": "PASS",
          "detail": "本审核不含 verified 字段/布尔；claim 状态只用 supported/partially-supported/unresolved/refuted"
        },
        {
          "id": "R8",
          "check": "report_id_boundary",
          "result": "PASS",
          "detail": "只读 report 3076 的 markdown 与其平台记录字段；未读写其它 report_id"
        }
      ],
      "checks_not_run": [
        {
          "check": "gate_rerun（11 checks × sealed/control）",
          "status": "not_run",
          "reason": "生产仓 papers/ 不在本工作树；跨仓重跑不属本单授权"
        },
        {
          "check": "numtrace/overclaim/statdof/arith 实现复核",
          "status": "not_run",
          "reason": "无生产代码；仅复核其汇总与阈值披露"
        },
        {
          "check": "figdata 图-数一致性",
          "status": "not_run",
          "reason": "需封存稿与图件（跨 report_id / 私有稿）"
        },
        {
          "check": "pytest 19 passed 复现",
          "status": "not_run",
          "reason": "同上；报告未给 run id/log"
        },
        {
          "check": "正控残差 7.09e-14 / 2.48e-14 复算",
          "status": "not_run",
          "reason": "残差定义在生产 solver.py 内；本工序独立复算只能给 k，不能给其残差口径"
        }
      ],
      "findings": [
        {
          "id": "F1",
          "severity": "major",
          "likelihood": "certain",
          "blocking": false,
          "title": "HARD 分母与同文表格不一致：8/11、0/11 应为 8/10、0/10",
          "finding": "汇总写 “HARD 失败 8/11” 与 “control `verdict=PASS`，HARD 失败 0/11（SKIP 3 项）”，但同文 ③ 表中严重度为 HARD 的行只有 10 条（另 1 条 SOFT：['placeholder']），分母 11 是“检查项总数”而非“HARD 检查数”。逐行复算：sealed HARD FAIL 8/10，control HARD FAIL 0/10（其中 SKIP 3 项）。报告自称汇总“程序化注入，源=审计 JSON”；若注入器按 HARD 计数就不会出 11 —— 这条错误同时说明注入链没有覆盖“HARD 数”这个字段。",
          "evidence": [
            {
              "quote": "HARD 失败 8/11",
              "line": 45
            },
            {
              "quote": "control `verdict=PASS`，HARD 失败 0/11（SKIP 3 项）",
              "line": 45
            }
          ],
          "reproduction": "independent_dispersion_check.py -> table_audit（解析 ③ 表 severity 列）",
          "scope": "③ 汇总句；标题计数口径；⑥ 第 2/3 行"
        },
        {
          "id": "F2",
          "severity": "major",
          "likelihood": "certain",
          "blocking": false,
          "title": "正控只覆盖 7/10 项 HARD：overclaim/statdof/arith 在正控 SKIP，“0 误报”范围被高估",
          "finding": "正控稿上 3 项 HARD 检查结果为 SKIP（['overclaim', 'statdof', 'arith']），即这三项的“不误报”从未被任何语料检验：正控缺 WITHHELD 量名、缺 R² 声明、缺行级百分数，PASS 路径一次也没走。而 overclaim(H2) 与 arith(H8) 恰是负控上命中的两类硬伤 —— 它们的误报率因此完全未知。结论成立的范围是 7/10，不是“0 误报”。",
          "evidence": [
            {
              "quote": "control `verdict=PASS`，HARD 失败 0/11（SKIP 3 项）",
              "line": 45
            }
          ],
          "reproduction": "同上 -> table_audit.hard_skip_control 与逐行 control 列",
          "scope": "标题“正控 0 误报”；③ 汇总；⑥ 第 2、3 行"
        },
        {
          "id": "F3",
          "severity": "major",
          "likelihood": "certain",
          "blocking": false,
          "title": "implmethod 是已证实的假阴性：对已知 H5 硬伤稿判 PASS，召回 0/1 而非“不可机判”",
          "finding": "③ 表中 implmethod（HARD）在封存稿上为 PASS（摘要“代码文件 1 个 / 声称方法 1 项 / 不符 0 项”），而⑤写 “`implmethod` 未能在封存树上复现 H5”。判据存在、已执行、给出 PASS 而目标硬伤没被抓住 = 假阴性；这与“该树上不可机判”（判据无从下手）是两个不同事实。汇总把 implmethod 记作 PASS 与其余 FAIL 并列，易被读成“该项检验通过”。",
          "evidence": [
            {
              "quote": "`implmethod` 未能在封存树上复现 H5",
              "line": 75
            },
            {
              "quote": "H5 在该树上不可机判，**如实不报**",
              "line": 47
            }
          ],
          "reproduction": "读 ③ implmethod 行（sealed=PASS）与 ⑤ 末行并列即得；无需生产代码",
          "scope": "③ implmethod 行；⑤ 末行；⑥ honest 声明"
        },
        {
          "id": "F4",
          "severity": "major",
          "likelihood": "certain",
          "blocking": false,
          "title": "⑥“是否 <3%”列 5 行里 3 行属范畴误用或非独立对照",
          "finding": "① 残差 7.09e-14 / 判据 1e-12 判“是”：按字面是“占门限 7.09%”>3%，只有把残差本身读作相对误差才成立，两种读法结论相反且未声明用哪种。② “正控 k vs 更紧容差解 2.48e-14 相对”判“是”：同一求解器收紧容差的自洽性（自比自），不是独立基准对照。③ “负控召回 7/7”“正控误报 0/11”判“是”：计数/比率而非误差百分比，且 0/11 分母如 F1 有误。真正符合“关键量 vs 基准误差”语义的只有 coth 25.02% 那一行（判“否”）。",
          "evidence": [
            {
              "quote": "正控 k vs 更紧容差解",
              "line": 70
            },
            {
              "quote": "7/7 复现",
              "line": 71
            }
          ],
          "reproduction": "比对 ⑥ 表各行“基准/结果”两列量纲；7.09e-14 / 1e-12 = 7.09e-2",
          "scope": "⑥ 表第 1、2、3、4 行"
        },
        {
          "id": "F5",
          "severity": "major",
          "likelihood": "certain",
          "blocking": false,
          "title": "11 项判据中 5 处阈值/定义未披露，判据不可被独立复算",
          "finding": "只有 numtrace 披露了容差（证据基 237 值，tol=0.005）。未披露：arith 的百分数复算容差（H8 举例 8.65% vs 8.33% 差 0.32 pp，不知相对何容差判“不一致”）、repro 的“三件套”是哪三件文件、正控“8 要素”是哪八项、overclaim 的“升格”判据、struct 的“必需要素”清单。判据缺阈值即不可复算：换一个执行者跑同一稿，得不到同样的 FAIL/PASS 组合。",
          "evidence": [
            {
              "quote": "证据基 237 值，tol=0.005",
              "line": 36
            },
            {
              "quote": "抓到 EnKF 声称 8.65% vs 同行两量复算 8.33%",
              "line": 47
            },
            {
              "quote": "三件套命中 0/3",
              "line": 41
            }
          ],
          "reproduction": "在报告 markdown 内检索“容差/tol/三件套/8 要素/升格”：仅 numtrace 的 tol 有数值",
          "scope": "② 第 1 步；③ arith/repro/struct 行；② 第 3 步“8 要素齐备”"
        },
        {
          "id": "F6",
          "severity": "minor",
          "likelihood": "certain",
          "blocking": false,
          "title": "“T≥14 s 时 coth 无根”边界值错：独立复算 T=14.0 s 仍有根",
          "finding": "独立求解（不含生产代码）给出：T=14.0 s 在 k∈(0,10] 内 coth 形式仍有根 k=0.005625 1/m；T=14.1 s 根在 0.003803；根消失的解析临界期 T_c=2π√(h/g)=14.185 s（coth 分支 RHS 在 k→0 的下确界趋于 g/h）。定性结论（长周期下 coth 版本给出不可解的非物理分支）成立，但边界值低报约 0.19 s：按原文复跑 T=14 s 会复现出根，从而把一条真结论判成“不可复现”。",
          "evidence": [
            {
              "quote": "T≥14s 时 coth 形式在 k∈(0,10] 1/m 内**无根**",
              "line": 49
            }
          ],
          "reproduction": "independent_dispersion_check.py -> no_root_probe（14.0/14.1/14.15/14.185/14.2/16/18/20/30/60 s 扫根 + T_crit）",
          "scope": "③ 最后一段"
        },
        {
          "id": "F7",
          "severity": "minor",
          "likelihood": "certain",
          "blocking": false,
          "title": "① 断言八类硬伤“全部”可机检，与 ③/⑤ 的“H5 不可机判”矛盾",
          "finding": "① 写 “复盘发现这八类**全部是「文本 ↔ 证据基 ↔ 代码/图件」的一致性检查，本可机检”，但 ③ 明确只映射 7 类（H1/H2/H3/H4/H6/H7/H8），H5 无映射。动机陈述被写成已达成事实，宜改为“其中七类可机检，H5 待定”。",
          "evidence": [
            {
              "quote": "复盘发现这八类**全部是",
              "line": 4
            },
            {
              "quote": "H5 在该树上不可机判，**如实不报**",
              "line": 47
            }
          ],
          "reproduction": "读 ① 第 2 段、③ 映射句、⑤ 末行",
          "scope": "① 背景段"
        },
        {
          "id": "F8",
          "severity": "minor",
          "likelihood": "likely",
          "blocking": false,
          "title": "参数表列 ρ_i=917 kg/m³，但所给色散式不含 ρ_i",
          "finding": "① 参数行给出 ρ_i=917.0 kg/m³，而所给 ω²=(gk+Dk⁵/ρ_w)tanh(kh)、D=Eh_i³/(12(1-ν²)) 中不出现 ρ_i。要么该参数冗余（正控声称“全链真算”却有一项参数不参与计算），要么式子漏了板惯性/附加质量项。独立复算按报告所给式子即可复现全部 5 个偏差值（见 ③），说明报告实际用的是不含 ρ_i 的式子 —— 参数表与公式因此不一致，读者无法判断正控算的是哪一版物理。",
          "evidence": [
            {
              "quote": "h=50.0 m、h_i=2.0 m、E=5.0×10⁹ Pa、ν=0.3、ρ_w=1025.0、ρ_i=917.0 kg/m³、g=9.81 m/s²、T=8.0 s",
              "line": 14
            }
          ],
          "reproduction": "independent_dispersion_check.py 只用 h/h_i/E/ν/ρ_w/g 即复现 5/5 偏差值",
          "scope": "① 参数行；② 第 3 步正控描述"
        },
        {
          "id": "F9",
          "severity": "minor",
          "likelihood": "certain",
          "blocking": false,
          "title": "“pytest 19 passed”仅为声明，无日志/哈希可核",
          "finding": "② 第 5 步写 “pytest 19 passed”，但无测试文件路径、无 collector 输出、无 run id/commit。上游 01 包同样把该串登记为 declared_in_source_only。作为门禁可信度的一部分，这属于未执行项，不应与实测数字并列。",
          "evidence": [
            {
              "quote": "pytest 19 passed",
              "line": 27
            }
          ],
          "reproduction": "检索 markdown：pytest 出现 1 次，无伴生日志路径或哈希",
          "scope": "② 第 5 步"
        },
        {
          "id": "F10",
          "severity": "informational",
          "likelihood": "likely",
          "blocking": false,
          "title": "numtrace 是存在性判据且“1 个 token 未溯源即 FAIL”，误报代价未量化",
          "finding": "封存稿 37 个定量 token 中 1 个未溯源即判 FAIL（≈2.7%）；报告自述这是“在证据基值域内匹配”的存在性判据、证据基 237 值时存在偶然匹配风险。但门禁未给“允许多少未溯源 token”“多少偶然匹配算超标”的门槛，因此真实稿件上第一处数值排版漂移就会 FAIL —— 这份严格度的误报代价在正控上也没被测（正控 0 未溯源）。",
          "evidence": [
            {
              "quote": "证据基 237 值，tol=0.005",
              "line": 36
            }
          ],
          "reproduction": "解析 ③ numtrace 行（37 token / 1 未溯源）+ ⑤ 第 1 条",
          "scope": "③ numtrace 行；⑤ 第 1 条"
        },
        {
          "id": "F11",
          "severity": "informational",
          "likelihood": "certain",
          "blocking": false,
          "title": "struct 标 HARD 却在已知 FAIL 稿上只给 WARN",
          "finding": "③ struct 严重度为 HARD，sealed 结果为 WARN（“缺 0 个必需要素”）。HARD 检查若只产生 WARN 就拦不住门，“HARD”语义与实测阻断力不一致；报告未说明 WARN 是否计入 verdict。（本文按行统计据此把 struct 计为未失败，故 F1 的分子 8 与 parsed 8 一致。）",
          "evidence": [
            {
              "quote": "HARD 失败 8/11",
              "line": 45
            }
          ],
          "reproduction": "table_audit.hard_warn_sealed = 1",
          "scope": "③ struct 行"
        }
      ],
      "claims_assessment": [
        {
          "claim_id": "C1-H1-deviation-series",
          "text": "H1 独立复算 coth 误式 vs tanh 正解波数偏差：T=4s 0.37% / 6s 1.31% / 8s 3.67% / 10s 9.60% / 12s 25.02%",
          "status": "supported",
          "evidence": [
            {
              "quote": "T=4s: 0.37%, T=6s: 1.31%, T=8s: 3.67%, T=10s: 9.60%, T=12s: 25.02%",
              "line": 49,
              "char_offset": 2496,
              "occurrences": 1
            }
          ],
          "note": "独立实现复算 5/5 一致，最大 |Δ|=0.004 pp；T=8 s k_tanh=3.778090e-02 / k_coth=3.639599e-02"
        },
        {
          "claim_id": "C2-coth-nonphysical-branch",
          "text": "T≥14s 时 coth 形式在 k∈(0,10] 1/m 内无根（错式不是偏差大，而是给出不可解的非物理分支）",
          "status": "partially-supported",
          "evidence": [
            {
              "quote": "T≥14s 时 coth 形式在 k∈(0,10] 1/m 内**无根**",
              "line": 49,
              "char_offset": 2563,
              "occurrences": 1
            }
          ],
          "note": "根消失的临界期 T_c=14.185 s；T=14.0 s 仍有根 k=0.005625，故边界应写 T>14.19 s（F6）"
        },
        {
          "claim_id": "C3-neg-control-recall-7of7",
          "text": "门禁负控召回 vs SEAL.md 七类机器可判硬伤 7/7 复现（H5 不可机判，已声明）",
          "status": "supported",
          "evidence": [
            {
              "quote": "7/7 复现",
              "line": 71,
              "char_offset": 3475,
              "occurrences": 1
            },
            {
              "quote": "H5 在该树上不可机判，**如实不报**",
              "line": 47,
              "char_offset": 2441,
              "occurrences": 1
            }
          ],
          "note": "③ 表中 formula/overclaim/figdata/figref/repro/statdof/arith 对 H1/H2/H3/H4/H6/H7/H8 均 FAIL，逐行可核；H3→figdata 为报告自述的代理判据"
        },
        {
          "claim_id": "C4-pos-control-zero-false-positive",
          "text": "门禁正控误报 0/11（HARD 失败 0，SKIP 3 项）",
          "status": "partially-supported",
          "evidence": [
            {
              "quote": "control `verdict=PASS`，HARD 失败 0/11（SKIP 3 项）",
              "line": 45,
              "char_offset": 2239,
              "occurrences": 1
            }
          ],
          "note": "HARD 实为 10 项（分母 11 错，F1），其中 3 项在正控 SKIP，实际执行且未误报的是 7/10（F2）"
        },
        {
          "claim_id": "C5-pytest-19-passed",
          "text": "工具链 pytest 19 passed",
          "status": "unresolved",
          "evidence": [
            {
              "quote": "pytest 19 passed",
              "line": 27,
              "char_offset": 1347,
              "occurrences": 1
            }
          ],
          "unresolved_reason": "仅声明串，无 log/collector/run id；生产仓不在本工作树，未重跑（F9）"
        },
        {
          "claim_id": "C6-control-residual-and-tighter-solve",
          "text": "正控归一化色散残差 7.09e-14（判据 1e-12）；k 对更紧容差解相对偏差 2.48e-14；两项判 <3% 为“是”",
          "status": "partially-supported",
          "evidence": [
            {
              "quote": "正控 k vs 更紧容差解",
              "line": 70,
              "char_offset": 3384,
              "occurrences": 1
            }
          ],
          "unresolved_reason": "残差定义在生产者 solver 内，本工序无法复算；且“占门限 7.09%”与“相对误差 1e-14”两种读法结论相反，后者还是同码收紧容差的自洽（F4）"
        },
        {
          "claim_id": "C7-implmethod-pass-on-sealed",
          "text": "implmethod 在封存稿上 PASS（代码文件 1 / 声称方法 1 / 不符 0）",
          "status": "refuted",
          "evidence": [
            {
              "quote": "`implmethod` 未能在封存树上复现 H5",
              "line": 75,
              "char_offset": 3634,
              "occurrences": 1
            }
          ],
          "note": "与“该稿存在 H5 实现-方法不符”冲突：作为 H5 判据它是假阴性，召回 0/1（F3）"
        }
      ],
      "overstated_claims": [
        "标题/③“正控 0 误报”：实际执行面是 7/10 项 HARD（F1+F2）",
        "①“八类全部可机检”：H5 无映射（F7）",
        "③“HARD 失败 8/11 / 0/11”：分母应为 10（F1）",
        "③ implmethod PASS 易被读作“该项通过检验”：实为 H5 假阴性（F3）",
        "⑥“<3% = 是”三处：门限占比与计数率被当作误差百分比（F4）",
        "③“T≥14 s 无根”：临界 14.19 s（F6）"
      ],
      "notable_strengths": [
        "H1 的定量结论可被独立实现逐字复现（5/5，|Δ|≤0.004 pp），说明这些数字不是编的",
        "audit 主动声明 figdata 为代理判据、coth 74.19% 未复现（工况集不同）、implmethod 未复现 H5，未掩盖",
        "门禁只读被审稿并有 mtime 断言测试 —— 这是防止“门禁改稿”的正确设计"
      ],
      "disposition": {
        "verdict": "needs-fix",
        "blocking_issues": [],
        "conditions_for_approval": [
          "F1：8/11、0/11 改为 8/10、0/10（或写“HARD 失败 8 / 检查项 11”），汇总直接从审计 JSON 取 HARD 计数",
          "F2：正控补语料让 overclaim/statdof/arith 走 PASS 路径；做不到就把标题与 ⑥ 显式限定为 7/10 并列出 SKIP 项",
          "F3：implmethod 在封存稿上的结果改记为 H5 召回 0/1（假阴性），不得与“通过”混列",
          "F4：⑥ 每行注明比较对象（残差/门限占比/自洽/计数），改写或删除这 3 处“是”",
          "F5：补齐 arith 容差、repro 三件套清单、struct 必需要素、overclaim 升格判据",
          "F6：改“T≥14 s”为“T>14.19 s”，并注明 T=14.0 s 仍有根",
          "F7：① 改为“其中七类可机检”",
          "F8：说明 ρ_i 用途，或补上含板惯性项的式子"
        ],
        "re_review": "修改后只需复跑本包 R2–R6（引文定位 → 偏差序列 → 严重度算术），无需重跑门禁"
      },
      "repro": {
        "cmd": "python3 docs/wp-3076-04/independent_dispersion_check.py && python3 -m pytest tests/test_kf_wp3076_04.py -q",
        "env": "离线可跑，无需平台凭据（原文副本 source.md 已在包内，哈希自校验）",
        "not_replayable": "首版的取数/构建/发布脚本 scripts/kf_wp3076_04_*.py 未随本 PR 交付（见 KF-RESULT 附录 B）：重新取原文与重新发布不可在仓内重放；数值结论由交付的独立复算器重跑，产物不变量由自检 T1–T10 守"
      }
    },
    "review_events.json": [
      {
        "id": "tkr:wp-3076-01:wp3076-04-rc1",
        "object_ref": "wp-3076-01",
        "object_version": "report-3076@9b7bb2427af8",
        "decision": "request-changes",
        "reviewer": {
          "id": "redteam-reviewer-m15826",
          "reviewer_type": "agent",
          "role": "red-team-reviewer"
        },
        "reviewed_at": "2026-11-12T02:50:00Z",
        "policy_version": "ke-review-v0.1",
        "rationale": "核心可验证量成立：H1 偏差序列 5/5 被独立实现复现（最大 |Δ|≤0.004 pp），负控 7/7 映射与表格自洽，源哈希一致，honest 声明真实存在且未把结论标 verified。但确凿缺陷足以要求修改：汇总算术错（HARD 分母 11≠10，F1）；标题级“正控 0 误报”覆盖被高估（3 项 HARD 在正控 SKIP，F2）；implmethod 对目标硬伤类是已证实的假阴性却记 PASS（F3）；⑥ 的“<3%”列 5 行中 3 行范畴误用或非独立对照（F4）；5 处判据阈值/定义未披露使 11 项判据不可独立复算（F5）。这些都能在不动内核的情况下修好，故判 needs-fix 而非 fail。",
        "findings": [
          {
            "severity": "major",
            "finding": "[F1] HARD 分母与同文表格不一致：8/11、0/11 应为 8/10、0/10",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "major",
            "finding": "[F2] 正控只覆盖 7/10 项 HARD：overclaim/statdof/arith 在正控 SKIP，“0 误报”范围被高估",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "major",
            "finding": "[F3] implmethod 是已证实的假阴性：对已知 H5 硬伤稿判 PASS，召回 0/1 而非“不可机判”",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "major",
            "finding": "[F4] ⑥“是否 <3%”列 5 行里 3 行属范畴误用或非独立对照",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "major",
            "finding": "[F5] 11 项判据中 5 处阈值/定义未披露，判据不可被独立复算",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "minor",
            "finding": "[F6] “T≥14 s 时 coth 无根”边界值错：独立复算 T=14.0 s 仍有根",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "minor",
            "finding": "[F7] ① 断言八类硬伤“全部”可机检，与 ③/⑤ 的“H5 不可机判”矛盾",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "minor",
            "finding": "[F8] 参数表列 ρ_i=917 kg/m³，但所给色散式不含 ρ_i",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "minor",
            "finding": "[F9] “pytest 19 passed”仅为声明，无日志/哈希可核",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "informational",
            "finding": "[F10] numtrace 是存在性判据且“1 个 token 未溯源即 FAIL”，误报代价未量化",
            "related_claim_refs": [],
            "related_evidence_refs": []
          },
          {
            "severity": "informational",
            "finding": "[F11] struct 标 HARD 却在已知 FAIL 稿上只给 WARN",
            "related_claim_refs": [],
            "related_evidence_refs": []
          }
        ],
        "conditions": [
          "F1：8/11、0/11 改为 8/10、0/10（或写“HARD 失败 8 / 检查项 11”），汇总直接从审计 JSON 取 HARD 计数",
          "F2：正控补语料让 overclaim/statdof/arith 走 PASS 路径；做不到就把标题与 ⑥ 显式限定为 7/10 并列出 SKIP 项",
          "F3：implmethod 在封存稿上的结果改记为 H5 召回 0/1（假阴性），不得与“通过”混列",
          "F4：⑥ 每行注明比较对象（残差/门限占比/自洽/计数），改写或删除这 3 处“是”",
          "F5：补齐 arith 容差、repro 三件套清单、struct 必需要素、overclaim 升格判据",
          "F6：改“T≥14 s”为“T>14.19 s”，并注明 T=14.0 s 仍有根",
          "F7：① 改为“其中七类可机检”",
          "F8：说明 ρ_i 用途，或补上含板惯性项的式子"
        ]
      }
    ]
  }
}
```
