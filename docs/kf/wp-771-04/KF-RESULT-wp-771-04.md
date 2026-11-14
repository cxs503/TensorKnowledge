# KF-RESULT wp-771-04

**tags**: kf-wp:wp-771-04, 04-independent-review, report:771, lane:C, in-review, kf-stage-04, verdict:needs-fix
**agent**: agent/m19777 · repo: TensorKnowledge · branch: agent/m19777
**source**: `tensor://reports/771` (field `markdown`, sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559)
**reviewed package**: `wp-771-01` ｜ **verdict**: `needs-fix`

---

## ① 本工序做了什么

`wp-771-04` 是 **04-independent-review** 工序，作用域锁死 `report_id=771` 一份报告，审核对象 `wp-771-01`。
审核上下文**只有**报告原文 markdown + 平台记录元数据 + wp-771-01 的资产清单：没有读生产者的解释、
没有复用生产 prompt（M5 上下文隔离与 M4 prompt 独立性在包内自证）。

结论一句话：**verdict = `needs-fix`**。

- **阻塞项（1 条）**：wp-771-01 声明的 3 张图（fig1_beverloo_qbc.png, fig2_beverloo_linearity.png,
  fig3_rate_series.png）全部返回 HTTP 404，因此 Beverloo 拟合质量、线性判据、稳态流率时间序列的
  视觉证据**无法独立审计**。
- **实质问题（4 条 major）**：即便只按原文审，报告本身也有 4 处必须修才能在知识层复用：
  Beverloo 系数 C=0.766（自由截距）超出文献区间 [0.55, 0.65]；B=32mm 逐点偏差 +5.82% 超 <3% 判据；
  仅 3 个数据点跨 B/d=8-9（43% x 跨度），截距-斜率强相关未量化；B/D=0.40 超出 Beverloo 严格适用区。
- **次要问题（3 条 minor）**：休止角 honest-FAIL 根因（无转动自由度）是推断而非实证；无运行身份标识
  （commit/seed/input deck）使精确复现不可能；6 个外部引用工件未附于报告。
- **没有做的事（防越界）**：不改写上游产物、不修改报告正文任何数字、不把任何结论标成 verified
  （verification 是平台门的独有输出）、不碰其它 report_id。

报告的 **honest-FAIL 纪律是好的**：Beverloo C 值 FAIL、逐点偏差 FAIL、休止角 FAIL 的判定与表内数字
算得一致，这不是缺陷；缺陷在于证据完整性（图 404）和不确定度量化（3 点拟合无置信区间）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具 / 关键设置 |
|---|---|---|
| 1 | 取源报告 | `GET $TENSOR_API_BASE/tensor/reports/771`（Bearer 认证），只取 `markdown` |
| 2 | 取上游产物 | 工作树扫描 `docs/kf/wp-771-01/`（asset_manifest.json, kf_result.json, selfcheck.json, source_771.md） |
| 3 | 独立重算哈希 | `hashlib.sha256(markdown.encode('utf-8'))` = `sha256:c9ba1975...`，与契约 **逐位相同**；长度 2143 vs 契约 2143，一致 |
| 4 | 离线快照 | 原样落 `docs/kf/wp-771-04/evidence/source/report_771.md`，供离线复算 |
| 5 | 表格程序化解析 | 正则解析 Beverloo 回归结果表、逐点偏差表、休止角表，**每个数字由代码读取，不手抄** |
| 6 | 派生量计算 | C 值区间判定、逐点偏差超阈值倍数、B/D 比值、x 跨度全部由代码算出（见 ③） |
| 7 | 引文零手抄守卫 | 每条 evidence quote 写入前断言 `quote in markdown` 且记录 offset 与 `sha256(quote)` |
| 8 | 独立性 | 审核 prompt 为独立撰写（对照目标=找反例/过度推断/丢掉的前提），非生产 prompt 复制 |
| 9 | 自检 | 10 项检查（V1 JSON 有效性 / V2 哈希 / V3 引文逐字 / V4 派生量重算 / V5 无自称 verified / V6 判定自洽 / V7 严重性排序 / V8 独立性声明 / V9 未运行检查声明 / V10 schema 符合性）|

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-771-04/evidence/review_report.json` | 审核主体：8 条 finding（1 blocker + 4 major + 3 minor）、7 条 claim 判定、派生量、未做项、局限 |
| `docs/kf/wp-771-04/evidence/kf_result.json` | 平台信封（package_id/task_type/report_id/provenance/outputs） |
| `docs/kf/wp-771-04/evidence/review_checks.json` | 10 项自检结果（全 PASS） |
| `docs/kf/wp-771-04/evidence/selfcheck.json` | 包级自检（7 项全 PASS） |
| `docs/kf/wp-771-04/evidence/review_report.v1.schema.json` | review_report.json 的 JSON Schema |
| `docs/kf/wp-771-04/evidence/fig1_review_checks.png` | 自检结果可视化（10/10 PASS） |
| `docs/kf/wp-771-04/evidence/source/report_771.md` | 源报告 byte-exact 快照（2143 chars） |
| `docs/kf/wp-771-04/evidence/source/figure_probe.json` | 图探测结果（3 张图均 404） |

派生量（全部由代码从原文算出，零手抄）：

| 量 | 值 | 怎么来的 |
|---|---|---|
| Beverloo C（自由截距） | 0.766 | 原文直接给出 |
| C 超文献上限倍数 | 1.178× | 0.766 ÷ 0.65 |
| 逐点最大偏差 | +5.82% | B=32mm 处 |
| 偏差超阈值倍数 | 1.94× | 5.82% ÷ 3.0% |
| B/D 最大值 | 0.40 | 36mm ÷ 90mm |
| B/D 超适用限 | 是 | 0.40 > 0.35 |
| 拟合点数 | 3 | B/d=8, 8.5, 9 |
| x 跨度 | 43% | (9-8)/(9-1) 的近似 |
| 休止角 R² 最大 | 0.336 | μ=0.35 处 |
| 孔隙率观测值 | 0.605 | 原文直接给出 |

## ④ 证据定位表

每条引文都在 `docs/kf/wp-771-04/evidence/source/report_771.md` 中逐字可搜（offset 与 content_hash 记在 review_report.json 的 evidence 里）。

| claim 字段 | 原文引文片段（逐字） |
|---|---|
| finding F1 / 图声明 | `fig1 流率-孔径 + 双对数斜率检验；fig2 ṁ 对 (B−kd)^{5/2} 线性判据图；fig3 各孔径流量时间序列` |
| finding F2 / 代码链 | `` `src/tensordem/granular_dem.py` → `examples/hopper_beverloo_case.py` → `hopper_beverloo_report.py` `` |
| finding F3 / Beverloo 拟合 | `Beverloo 回归（k=1.5 固定）：C=0.766（自由截距）、R²=0.99498；过原点 C=0.646 但 R²=−0.215` |
| finding F3 / 硬门① | `硬门①：R²=0.99498 ≥ 0.99 通过；C∈[0.55,0.65] 未通过` |
| finding F4 / 逐点偏差 | `逐点相对偏差：B=32mm: +5.82%, B=34mm: -1.21%, B=36mm: -1.79%` |
| finding F4 / 逐点判据 | `逐点 <3% 判据：上述相对偏差中最大为 +5.82%（B=32 mm），其余两点 <2%，未全部 <3%` |
| finding F5 / 孔径窗口 | `可用孔径窗口被成拱限制在 B/d=8–9，x 跨度仅 43%，截距与斜率强相关` |
| finding F6 / B/D 超限 | `B/D 达 0.40（超出 Beverloo 严格适用区的上界）` |
| finding F7 / 休止角根因 | `休止角失败根因：无转动自由度 → 缺滚动摩阻` |
| finding F8 / 材料参数 | `材料：d=4.00 mm 玻璃珠，ρ_p=2500 kg/m³，k_n=1.0 kN/m，e=0.60，μ=0.25，Δt=50 µs` |

审核结论表（claim → 判定；judgement 词汇沿用 G3 审核轴：supports / qualifies / refutes / insufficient）：

| claim_id | 判定 | claim | 依据摘要 |
|---|---|---|---|
| cj-beverloo-r2-pass | supports | Beverloo fit R²=0.99498 ≥ 0.99 passes the hard gate. | Arithmetic confirms R²=0.99498 ≥ 0.99. |
| cj-beverloo-c-fail | supports | Beverloo coefficient C=0.766 fails the C∈[0.55,0.65] gate. | 0.766 > 0.65, FAIL verdict is arithmetic-consistent. |
| cj-pointwise-fail | supports | Point-wise deviation at B=32mm is +5.82%, exceeding <3%. | 5.82% > 3.0%, FAIL verdict is arithmetic-consistent. |
| cj-aor-fail | supports | Angle of repose measurement is invalid (honest FAIL). | R²≈0.33 for all μ, far below any reasonable threshold. |
| cj-beverloo-reproduction | qualifies | Beverloo law is reproduced (title claim). | Partial: R² passes but C out of range, one point fails <3%. |
| cj-zero-manual-copy | insufficient | All numbers programmatically injected, zero manual transcription. | Scripts and data files not attached (F2). |
| cj-steady-state | insufficient | Steady-state mass flow rate is demonstrated (fig3). | fig3 unresolved (HTTP 404), cannot verify (F1). |

finding 全表：

| id | 级别 | 类别 | 阻塞 | 结论 |
|---|---|---|---|---|
| F1 | blocker | missing-evidence | yes | All 3 declared figures return HTTP 404; visual evidence cannot be audited. |
| F2 | major | missing-evidence | no | 6 external artifacts referenced but not attached; 'zero manual copy' unfalsifiable. |
| F3 | major | parameter-out-of-range | no | C=0.766 outside [0.55,0.65]; forced-origin C=0.646 has R²=-0.215. |
| F4 | major | criterion-not-met | no | B=32mm deviation +5.82% exceeds <3% criterion. |
| F5 | major | insufficient-data | no | Only 3 fit points (43% x-span); intercept-slope correlation unquantified. |
| F6 | minor | applicability-limit | no | B/D=0.40 exceeds Beverloo strict applicability (typically <0.35). |
| F7 | minor | inference-not-demonstrated | no | AOR root cause (no rotational DOF) is inference, not demonstrated fact. |
| F8 | minor | reproducibility | no | No run identity (commit, seed, input deck) provided. |

## ⑤ 注意点与局限

- **Single channel**: the platform reports list returns at most the newest 50-100 rows; psql on tensor_reports is permission-denied for this identity.
- **Reviewer sees only report markdown + asset manifest + record metadata**; no access to the actual DEM code or simulation output files.
- **All figure-dependent claims cannot be visually verified** due to HTTP 404 responses (F1).
- **Beverloo literature range [0.55, 0.65]** is taken from the report's own statement; independent literature verification was not performed.
- **No re-execution of the simulation was attempted** (no run identity provided: no commit, seed, input deck — see F8).
- All numeric judgements are arithmetic on the report's own table; they validate internal consistency of the report, not the physics it claims to simulate.
- No finding here marks any claim as verified; verification is the platform gate's job.

**未运行的检查（unknown ≠ pass）**：

- Visual verification of fig1_beverloo_qbc.png (HTTP 404)
- Visual verification of fig2_beverloo_linearity.png (HTTP 404)
- Visual verification of fig3_rate_series.png (HTTP 404)
- Re-execution of the DEM hopper simulation (no run identity)
- Verification of 'zero manual transcription' claim (scripts and data files not attached)
- Cross-validation of Beverloo coefficient against independent literature sources

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | 所有 JSON 文件 `json.loads` 通过（V1） |
| `schema_pass` | ✅ | `jsonschema.validate(envelope, review_report.v1.schema.json)` 通过（V10） |
| `source_hash_matches` | ✅ | SHA256 逐位匹配（V2） |
| `reviewer_independent` | ✅ | 审核上下文=source markdown+asset manifest+record 元数据，未读生产者解释；审核 prompt 独立撰写 |
| `no_self_verified_claims` | ✅ | 包内无任何 verified 字段（V5 正则守卫）；reviewer 只给 judgement，不给验证档位 |
| `verdict_consistent_with_findings` | ✅ | 1 条 blocker finding (F1) 存在；verdict 为 needs-fix（V6） |
| `checks_not_run_declared` | ✅ | 6 项 checks_not_run 显式列出（V9） |

**不做 pass 的理由（防粉饰）**：报告本身的 honest-FAIL 值得肯定，但本工序审核的是**知识产物的可用性**。
在仅 3 个数据点、C 值超范围、逐点偏差超判据、图全部 404 的情况下，把这份报告抽成知识对象就是过度推断。
因此 `needs-fix`，修好后重跑本工序。

## ⑦ 发布记录（单一结果信道）

- 本文件即平台报告正文；正文中**唯一**的 json 代码块就是提交给门禁的 `kf_result` 信封。

```json
{
  "package_id": "wp-771-04",
  "task_type": "04-independent-review",
  "report_id": 771,
  "provenance": {
    "source_hash": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
    "source_field": "markdown",
    "producer": "agent/m19777",
    "emitted_at": "2026-01-15T00:00:00+00:00",
    "notes": "Independent review of wp-771-01 for report 771; source markdown re-fetched and sha256 recomputed (match: True). No claim marked verified. Verdict: needs-fix due to unresolved figures (HTTP 404) and substantive findings on Beverloo fit quality."
  },
  "outputs": {
    "review_report.json": {
      "review_report_version": "1.0",
      "verdict": "needs-fix",
      "findings_count": 8,
      "findings_by_severity": {"blocker": 1, "major": 4, "minor": 3},
      "claims_count": 7,
      "claims_by_judgement": {"supports": 4, "qualifies": 1, "insufficient": 2},
      "checks_not_run_count": 6,
      "upstream_package": "wp-771-01",
      "upstream_product_found": true,
      "upstream_figures_resolvable": 0,
      "upstream_figures_declared": 3
    },
    "review_checks.json": {"total_checks": 10, "passed": 10, "failed": 0},
    "selfcheck.json": {"accepted": true, "failed": []}
  }
}
```
