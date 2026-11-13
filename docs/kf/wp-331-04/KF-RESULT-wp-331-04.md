# KF-RESULT wp-331-04

**tags**: kf-wp:wp-331-04, 04-independent-review, report:331, lane:C, in-review, kf-stage-04, verdict:needs-fix
**agent**: agent/m15788 · repo: TensorKnowledge · branch: agent/m15788
**source**: `tensor://reports/331` (field `markdown`, sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717)
**reviewed package**: `wp-331-01` ｜ **verdict**: `needs-fix`

---

## ① 本工序做了什么

`wp-331-04` 是 **04-independent-review** 工序，作用域锁死 `report_id=331` 一份报告，审核对象 `wp-331-01`。
审核上下文**只有**报告原文 markdown + 平台记录元数据：没有读生产者的解释、没有读上游 package 的
self_assessment，也没有复用生产 prompt（M5 上下文隔离与 M4 prompt 独立性在包内自证）。

结论一句话：**verdict = `needs-fix`**。

- **阻塞项（1 条）**：上游 `wp-331-01` 的产物在本身份可触达的四条信道上都取不到（详见 ⑤），
  因此「claim 是否忠实于原文」的逐条审计**做不了**，本包不能判 pass，只能 request_changes。
- **实质问题（5 条 major）**：即便只按原文审，报告本身也有 5 处必须修才能在知识层复用：
  Hertz 对标跑在 δ/R = 0.5（远超 Hertz 小变形适用域）；「离散格点复现不了连续介质 Hertz」
  这一因果归因被动态加载与未校准的 E_dem 混淆；唯一的 PASS（梁 0.0125%）与「二阶收敛」既无参考值也无网格序列；
  58.6% 的能量漂移使产生这些数字的轨迹本身失效；标题宣称的 DEM-FEM 耦合 schema 无工件、无校验记录。
- **没有做的事（防越界）**：不改写上游产物、不修改报告正文任何数字、不把任何结论标成 verified
  （verification 是平台门的独有输出）、不碰其它 report_id。

报告的 **honest-FAIL 纪律是好的**：三个 FAIL 判定与表内数字算得一致，这不是缺陷；缺陷在于这些 FAIL
被当成「格点方法不行」的证据，而证据链撑不起这个因果。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具 / 关键设置 |
|---|---|---|
| 1 | 取源报告 | `GET $TENSOR_API_BASE/tensor/reports/331`（`/auth/login` 取 access_token，Bearer 认证），只取 `markdown` |
| 2 | psql 直连尝试 | `psql -d tensorplatform -tA -c "select markdown from tensor_reports where id=331"` → **permission denied for table tensor_reports**，故全程只走 API |
| 3 | 独立重算哈希 | `hashlib.sha256(markdown.encode('utf-8'))` = `sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717`，与契约 `source_hash` **逐位相同**；长度 1371 vs 契约 1371，一致 |
| 4 | 离线快照 | 原样落 `runs/wp-331-04/source_331.md`，供离线复算与 pytest |
| 5 | 表格程序化解析 | 正则解析 `## ③ Results` 四列表（Metric/Hertz/Target/Beam），**表内每个数字由代码读取，不手抄** |
| 6 | 参数程序化解析 | 从 `**Parameters**` 行与几何行正则取 `k_bond` / `tool_speed` / `max_indent` / `R` |
| 7 | 派生量计算 | 偏差、容忍带超限倍数、δ/R、预算倍数全部由代码算出（见 ③） |
| 8 | 引文零手抄守卫 | 每条 evidence quote 写入前断言 `quote in markdown` 且记录 offset 与 `sha256(quote)`；共 29 条，**0 条失败即构建失败** |
| 9 | 独立性 | 审核 prompt 为独立撰写（对照目标=找反例/过度推断/丢掉的前提），非生产 prompt 复制；上下文只含 source+record |
| 10 | 自检 | `python3 scripts/kf_wp331_04/verify_review.py` 六项（V1 信封 schema / V2 哈希 / V3 引文逐字 / V4 派生量重算 / V5 无自称 verified 字段 / V6 判定自洽）|

一键复跑（工作树根执行）：

    python3 scripts/kf_wp331_04/build_review.py      # 取源→解析→断言→生成 review_report.json + 信封
    python3 scripts/kf_wp331_04/verify_review.py     # 离线六项自检，全绿才 exit 0
    pytest tests/test_kf_wp331_04_review.py -q        # 同上逻辑的 pytest 封装（含一条负例）

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-331-04/review_report.json` | 审核主体：8 条 finding（1 blocker + 5 major + 2 minor）、7 条 claim 判定、派生量、未做项、局限；本包唯一契约输出 |
| `docs/kf/wp-331-04/kf_result.wp-331-04.json` | 平台信封（package_id/task_type/report_id/provenance/outputs），provenance.source_hash 与原文逐字节一致 |
| `docs/kf/wp-331-04/KF-RESULT-wp-331-04.md` | 本文件：六段正文 + 唯一一个 json 代码块（信封原样） |
| `runs/wp-331-04/source_331.md` | 源报告 byte-exact 快照（1371 chars），支撑离线复算 |
| `runs/wp-331-04/review_events.json` | 单条审核状态事件（decision=`request_changes`）；**放在 runs/ 而非输出目录**，使契约 `output`（仅 review_report.json）保持精确 |
| `scripts/kf_wp331_04/*.py` | fetch/list/build/verify/render 五脚本，可复跑 |

派生量（全部由代码从原文表格算出，零手抄）：

| 量 | 值 | 怎么来的 |
|---|---|---|
| Hertz 指数绝对偏差 | 0.0892 | \|1.4108 − 1.5\|，容忍带 ±0.05 |
| 偏差超容忍带倍数 | 1.784× | 偏差 ÷ 0.05 |
| 刚度误差超预算倍数 | 14.7× | 44.1% ÷ 3.0% |
| 能量漂移超预算倍数 | 58.6× | 58.6% ÷ 1.0% |
| 梁 PASS 预算余量 | 240.0× | 3.0% ÷ 0.0125% |
| 末态 δ/R | 0.5 | max_indent 0.05 m ÷ R 0.1 m |

## ④ 证据定位表

每条引文都在 `runs/wp-331-04/source_331.md` 中逐字可搜（offset 与 content_hash 记在 review_report.json 的 evidence 里）。

| claim 字段 | 原文引文片段（逐字） |
|---|---|
| finding F2 / 标题宣称 schema | `Schema  validates against jsonschema` |
| finding F2 / FEM 缺席 | `**Honest-FAIL**: TensorFEM unavailable; DEM lattice ≠ continuum half-space` |
| finding F3 / 几何与压头 | `**Geometry**: DEM3D bonded-sphere assembly (4×3×4 grid) with spherical indenter (R=0.1m)` |
| finding F3,F4,F6 / 参数（speed/indent） | `- **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m` |
| finding F4 / 未推导的模量标定 | `Effective modulus estimated: E_dem ≈ k_bond/(2r)` |
| finding F4 / 被审的因果句 | `- DEM discrete lattice cannot reproduce continuum Hertz contact` |
| finding F5 / 梁 PASS 数值 | `\| Stiffness error \| 44.1% \| ≤3% \| 0.0125% \|` |
| finding F5 / 二阶收敛断言 | `- Beam FD shows second-order convergence (error ∝ 1/n²)` |
| finding F5 / 未定义指标 | `\| Mesh conv \| 8.4% \| <5% \| converging \|` |
| finding F6 / 能量漂移 | `\| Energy drift \| 58.6% \| ≤1% \| — \|` |
| finding F7 / 指数判定措辞 | `- Hertz exponent 1.4108 vs 1.5: **5.9% error, FAIL** (outside ±0.05)` |
| finding F8 / 图无文件名 | `See attached: Hertz F-δ curve + beam deflection comparison` |

审核结论表（claim → 判定；judgement 词汇沿用 G3 审核轴：supports / qualifies / refutes / insufficient）：

| claim_id | 判定 | claim | 依据摘要 |
|---|---|---|---|
| cj-exponent-fail | supports | Hertz exponent 1.4108 vs target 1.5 +- 0.05 is a FAIL. | Arithmetic confirms the FAIL: \|1.4108-1.5\| = 0.0892 > 0.05. The claim is faithful to the source and correctly signed; only its phrasing is imprecise ( |
| cj-stiffness-fail | qualifies | Hertz stiffness error 44.1% vs target <=3% is a FAIL. | The FAIL verdict is arithmetic-consistent (44.1/3 = 14.7x the budget), but the 44.1% itself is not recomputable: E* needs Poisson's ratio and E_dem ne |
| cj-beam-pass | insufficient | Beam FD (n=80) stiffness error 0.0125% vs <=3% is a PASS. | No reference deflection, beam constants or normalisation convention appears in the report, so the PASS is unfalsifiable (F5). It must not be promoted  |
| cj-energy-fail | supports | Energy drift 58.6% vs <=1% target is a FAIL. | 1% target, 58.6% measured: 58.6x over budget. Verdict supported and, per F6, it is the most consequential number in the report because it disqualifies |
| cj-lattice-cannot-hertz | refutes | DEM discrete lattice cannot reproduce continuum Hertz contact. | Refuted as stated (a universal/structural claim drawn from one confounded run). The supported version is narrower: 'in this setup (delta/R = 0.5, tool |
| cj-second-order | insufficient | Beam FD shows second-order convergence (error proportional to 1/n^2). | A convergence order requires errors at >=3 resolutions and a fitted slope; the report shows one undefined 'Mesh conv' number and the word 'converging' |
| cj-schema-validates | insufficient | Schema validates against jsonschema. | No schema file, $id, validator version or exit status; the sentence is not checkable and should stay unresolved in any extraction (F2). |

finding 全表：

| id | 级别 | 类别 | 阻塞 | 结论 |
|---|---|---|---|---|
| F1 | blocker | process/upstream | yes | Upstream package wp-331-01 has no retrievable product, so the claim-level fidelity of the extraction (03 output) cannot be audited; this package can therefore not be approved, only refused/returned. |
| F2 | major | scope-overclaim | no | The title advertises a 'DEM-FEM Coupling Interface Schema', but the body declares TensorFEM unavailable: no coupling is executed, and no schema artifact, path or validator output is given. |
| F3 | major | theory-validity-range | no | The Hertz comparison is run over a load range that violates Hertz's own small-strain condition, so the 1.4108 exponent is not a clean measure of discretisation error and the ±0.05 acceptance band is mis-specified for this range. |
| F4 | major | confounded-causal-attribution | no | 'DEM discrete lattice cannot reproduce continuum Hertz contact' is stated as the cause of the 44.1% stiffness error, but the setup confounds at least four candidate causes that the report never separates. |
| F5 | major | unverifiable-pass | no | The only PASS item (beam stiffness 0.0125%) and the claimed second-order convergence are not reproducible from the report: no reference value, no beam data, no mesh series. |
| F6 | major | numerical-integrity | no | An energy drift of 58.6% against a ≤1% target invalidates the DEM trajectory from which the exponent and stiffness are extracted; the defective trajectory cannot support any contact-law conclusion. |
| F7 | minor | precision-of-statement | no | The FAIL line conflates a relative percentage with an absolute tolerance: 1.4108 vs 1.5 is a 0.0892 absolute shortfall, 1.78x the stated +-0.05 band, not '5.9% outside a 5% band' as the wording suggests. |
| F8 | minor | reproducibility | no | The report carries no run identity: no commit, no input deck path, no seed, no sphere radius / packing fraction / timestep, no figure paths. |

## ⑤ 注意点与局限

- Single channel: the platform reports list returns at most the newest 50-100 rows and ignores ?tag=/?offset=, so absence of a kf-wp:wp-331-01 record is 'not found on the reachable window', not proof of non-existence; psql on tensor_reports is permission-denied for this identity.
- Reviewer sees only report markdown + record metadata; no producer explanation, no prior review events, no code — therefore root-cause statements about the solver (integrator choice, contact model) are inferences from the parameter line, marked as such.
- All numeric judgements are arithmetic on the report's own table; they validate internal consistency of the report, not the physics it claims to simulate.
- No finding here marks any claim as verified; verification is the platform gate's job.

**未运行的检查（unknown ≠ pass）**：

- claim-level extraction fidelity vs wp-331-01 product (product unreachable; see F1)
- review-ledger fold / G3 semantic gate execution (platform gate, out of scope for this package)
- re-execution of the DEM indentation or the beam FD solve (no run identity in the source: no commit, deck path, radius, dt, seed — see F8)
- figure contents (Hertz F-delta curve, beam deflection) — only the record's figure count was read
- cross-report consistency of the M404 series (out of scope: single report_id per contract boundary)

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | 信封与 review_report.json 均 `json.loads` 通过（verify V1） |
| `schema_pass` | ✅ | `jsonschema.validate(envelope, schemas/kf_result.v1.schema.json)` 通过（V1）；review 主体为自由对象（契约未给 04 专用 schema） |
| `reviewer_independent` | ✅ | 审核上下文=source markdown+record 元数据，未读生产者解释；审核 prompt 独立撰写；未复用生产 prompt |
| `upstream_packages_completed` | ❌ **honest-FAIL** | 上游 `wp-331-01` 产物在四条信道（报告列表 tag 扫描 / work-packages 端点 404 / psql permission denied / 工作树 wp-331-* 扫描）均未取到 → 判 FALSE，故 verdict 只能是 `needs-fix` |
| 约束 `do_not_mark_claims_as_verified` | ✅ | 包内无任何 verified/verification_status 字段（V5 正则守卫）；reviewer 只给 judgement，不给验证档位 |
| 约束 `reviewer_context_excludes_producer_explanation` | ✅ | 见 ① 与 reviewer.independence_of_producer / producer_explanation_used 字段 |
| 零手抄 | ✅ | 29 条引文全部子串断言通过（V3）；6 个派生量由代码从原文重算一致（V4） |

**不做 pass 的理由（防粉饰）**：报告本身的 honest-FAIL 值得肯定，但本工序审核的是**知识产物的可用性**。
在 δ/R = 0.5 的工况下，1.4108 的指数既不能证明格点不行，也不能证明方法可行；
58.6% 的能量漂移使同表其它数字失去来源可信度；唯一的 PASS 无参考值。把这些抽成知识对象就是过度推断。
因此 `needs-fix`，修好后重跑本工序。

## ⑦ 发布记录（单一结果信道）

- 本文件即平台报告正文；正文中**唯一**的 json 代码块就是提交给门禁的 `kf_result` 信封。
- 发布时 `POST /tensor/reports` 见 `scripts/kf_wp331_04/publish_report.py`（title=`KF-RESULT wp-331-04`，
  tags 含 `kf-wp:wp-331-04`，scenario_key=`dem_fem_coupling_hertz_cpu`，mission_id=15788，2 张图内嵌 base64）。
- 同 mission 下另有一条由同一 agent 先发的**占位探针记录**（summary 为 `probe`，正文与本文件相同，是
  422 校验（summary≤500 字符）排查过程的副产物）；本文件多出本节，因此正文哈希不同，可据此区分——
  以 tags/summary 完整的那条为准。

```json
{
  "package_id": "wp-331-04",
  "task_type": "04-independent-review",
  "report_id": "331",
  "provenance": {
    "source_hash": "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717",
    "source_field": "markdown",
    "producer": "agent/m15788",
    "emitted_at": "2026-11-12T02:37:49+00:00",
    "notes": "Independent review of wp-331-01 for report 331; source markdown re-fetched and sha256 recomputed (match: True). No claim marked verified."
  },
  "outputs": {
    "review_report.json": {
      "review_report_version": "1.0",
      "package_id": "wp-331-04",
      "task_type": "04-independent-review",
      "report_id": "331",
      "reviewed_package": "wp-331-01",
      "reviewer": {
        "role": "red-team-reviewer",
        "agent": "agent/m15788",
        "repo": "TensorKnowledge",
        "independence_of_producer": true,
        "producer_explanation_used": false,
        "review_prompt_copied_from_producer": false,
        "context_used": [
          "tensor://reports/331#markdown",
          "tensor_reports[331] record metadata"
        ]
      },
      "source": {
        "uri": "tensor://reports/331",
        "field": "markdown",
        "sha256": "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717",
        "contract_sha256": "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717",
        "hash_recomputed_independently": true,
        "hash_matches_contract": true,
        "chars": 1371,
        "contract_chars": 1371,
        "chars_match_contract": true,
        "title": "M404: DEM-FEM Coupling Interface Schema + Hertz/Beam Benchmarks (CPU)",
        "contract_title": "M404: DEM-FEM Coupling Interface Schema + Hertz/Beam Benchmarks (CPU)",
        "scenario_key": "dem_fem_coupling_hertz_cpu",
        "contract_scenario_key": "dem_fem_coupling_hertz_cpu"
      },
      "upstream": {
        "package_id": "wp-331-01",
        "product_found": false,
        "channels_checked": [
          "GET /tensor/reports (client-side tag scan over newest 100; ?tag= and ?offset= ignored server-side)",
          "GET /tensor/work-packages, /tensor/work_packages, /tensor/packages (all HTTP 404)",
          "psql -d tensorplatform 'select markdown from tensor_reports where id=331' (permission denied)",
          "worktree scan for wp-331-* artifacts (none outside this package)"
        ],
        "consequence": "acceptance item upstream_packages_completed = FALSE; verdict cannot be 'approve'. Review executed against the source report as the authoritative evidence so the analysis is still usable once the product is attached."
      },
      "verdict": "needs-fix",
      "verdict_summary": "needs-fix, not pass. Blocking: the reviewed product wp-331-01 is unreachable, so claim-level fidelity cannot be audited. Substantive: even judged on the source alone, four major defects must be fixed before any knowledge object from this report is reusable — (F3) the Hertz comparison runs at delta/R = 0.5, far outside Hertzias validity, (F4) the causal attribution 'lattice cannot reproduce Hertz' is confounded by dynamic loading and an untested E_dem calibration, (F5) the only PASS (beam 0.0125%) and the claimed O(1/n^2) order have no reference value or mesh series, (F6) a 58.6% energy drift disqualifies the trajectory that produced the reported exponent/stiffness. The report's own honest-FAIL discipline is good and its three FAIL verdicts are arithmetic-consistent; they are not the defect.",
      "derived_metrics": {
        "exponent_reported": 1.4108,
        "exponent_target": 1.5,
        "exponent_tolerance": 0.05,
        "exponent_abs_deviation": 0.0892,
        "exponent_relative_deviation_pct": 5.9467,
        "exponent_tolerance_overshoot_factor": 1.784,
        "exponent_verdict": "FAIL",
        "stiffness_error_pct": 44.1,
        "stiffness_target_pct": 3.0,
        "stiffness_budget_overshoot_factor": 14.7,
        "stiffness_verdict": "FAIL",
        "energy_drift_pct": 58.6,
        "energy_target_pct": 1.0,
        "energy_budget_overshoot_factor": 58.6,
        "energy_verdict": "FAIL",
        "beam_error_pct": 0.0125,
        "beam_budget_margin_factor": 240.0,
        "beam_verdict": "PASS",
        "indent_over_R": 0.5,
        "indent_over_R_note": "Hertz small-strain validity needs delta/R << 1; the reported final indentation reaches delta/R =0.50",
        "params": {
          "k_bond": 100000.0,
          "tool_speed": 5.0,
          "max_indent": 0.05,
          "indenter_R": 0.1
        },
        "figures_in_record": 1,
        "derived_consistent_with_report_claims": true
      },
      "findings": [
        {
          "id": "F1",
          "severity": "blocker",
          "category": "process/upstream",
          "statement": "Upstream package wp-331-01 has no retrievable product, so the claim-level fidelity of the extraction (03 output) cannot be audited; this package can therefore not be approved, only refused/returned.",
          "evidence": [
            {
              "quote": "## ③ Results",
              "source_field": "markdown",
              "offset_start": 675,
              "offset_end": 687,
              "content_hash": "sha256:ddb480c6f5e25974476ef8935523eef81112e8908453b0cc0832edaf8fc37ad9"
            }
          ],
          "analysis": "Channels checked: (a) platform report listing — 100 most recent records scanned client-side for the tag kf-wp:wp-331-01, zero hits; the reports endpoint honours neither ?tag= nor ?offset= (both return the newest 50-100 rows), so an exhaustive scan is impossible from here; (b) no work-package endpoint (/tensor/work-packages, /tensor/packages -> HTTP 404); (c) psql: 'permission denied for table tensor_reports'; (d) worktree artifacts: no file matching wp-331-* outside this package. Therefore the review is executed against the only reachable authoritative evidence, the source markdown, and every 03-style claim below is judged for whether the source can support it.",
          "remediation": "Attach the wp-331-01 product (claims/evidence/provenance) to the package and re-run this review; acceptance item upstream_packages_completed stays FALSE until then.",
          "blocking": true
        },
        {
          "id": "F2",
          "severity": "major",
          "category": "scope-overclaim",
          "statement": "The title advertises a 'DEM-FEM Coupling Interface Schema', but the body declares TensorFEM unavailable: no coupling is executed, and no schema artifact, path or validator output is given.",
          "evidence": [
            {
              "quote": "**Honest-FAIL**: TensorFEM unavailable; DEM lattice ≠ continuum half-space",
              "source_field": "markdown",
              "offset_start": 330,
              "offset_end": 404,
              "content_hash": "sha256:1f66bf8da285b7972976488501f7078bfc058f26600cb5ba8e1938c54bc18fbe"
            },
            {
              "quote": "Schema  validates against jsonschema",
              "source_field": "markdown",
              "offset_start": 1154,
              "offset_end": 1190,
              "content_hash": "sha256:5849a2e9b9990c34732f65b5a53e9bace92c4747533a040e45039afe2d0c0293"
            }
          ],
          "analysis": "Two separate assertions are collapsed into one: 'a schema exists' and 'it validates'. The report supplies neither the schema file, its $id/version, nor the validator command and exit status, so 'validates against jsonschema' is unfalsifiable from the text. Any 03 claim asserting a validated DEM-FEM interface schema must be status=unresolved, not supported; a claim naming DEM-FEM *coupling* (as opposed to interface-schema authoring) as demonstrated is scope drift.",
          "remediation": "Either attach the schema file + validator transcript (path, command, exit code, jsonschema version) or restate the delivery as 'interface schema draft, unvalidated; FEM side not available'.",
          "blocking": false
        },
        {
          "id": "F3",
          "severity": "major",
          "category": "theory-validity-range",
          "statement": "The Hertz comparison is run over a load range that violates Hertz's own small-strain condition, so the 1.4108 exponent is not a clean measure of discretisation error and the ±0.05 acceptance band is mis-specified for this range.",
          "evidence": [
            {
              "quote": "**Geometry**: DEM3D bonded-sphere assembly (4×3×4 grid) with spherical indenter (R=0.1m)",
              "source_field": "markdown",
              "offset_start": 170,
              "offset_end": 258,
              "content_hash": "sha256:53f3628af3ab32e6eff1651f9581c8b93d5cc9fae18e43bf75198144154786d5"
            },
            {
              "quote": "- **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m",
              "source_field": "markdown",
              "offset_start": 259,
              "offset_end": 327,
              "content_hash": "sha256:09e0e223cca3e837473630f8acfecacaf5193010dbee4c26ce16f008bc9ee4b5"
            }
          ],
          "analysis": "max_indent / R = 0.05 / 0.1 = 0.5, i.e. delta/R = 0.5 at the end of the stroke. Hertz (F proportional to delta^1.5) assumes delta/R << 1 (single-digit-percent strains); at delta/R = 0.5 both the geometric linearisation and the half-space assumption fail, and the fitted exponent drifts below 1.5 for reasons that have nothing to do with the lattice. The honest FAIL verdict itself is therefore not evidence that the DEM discretisation is inadequate.",
          "remediation": "Restrict the fit window to small strain (e.g. delta/R <= 0.05-0.1), report the fitted exponent per window, and only then compare against 1.5 +/- 0.05; alternatively declare the finite-strain regime and compare against a finite-deformation contact solution instead of Hertz.",
          "blocking": false
        },
        {
          "id": "F4",
          "severity": "major",
          "category": "confounded-causal-attribution",
          "statement": "'DEM discrete lattice cannot reproduce continuum Hertz contact' is stated as the cause of the 44.1% stiffness error, but the setup confounds at least four candidate causes that the report never separates.",
          "evidence": [
            {
              "quote": "- DEM discrete lattice cannot reproduce continuum Hertz contact",
              "source_field": "markdown",
              "offset_start": 1032,
              "offset_end": 1095,
              "content_hash": "sha256:4f41c28d9727da379bfe48393c4cd40a9a7b701036aab10d721a6490c40aae3d"
            },
            {
              "quote": "- **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m",
              "source_field": "markdown",
              "offset_start": 259,
              "offset_end": 327,
              "content_hash": "sha256:09e0e223cca3e837473630f8acfecacaf5193010dbee4c26ce16f008bc9ee4b5"
            },
            {
              "quote": "Effective modulus estimated: E_dem ≈ k_bond/(2r)",
              "source_field": "markdown",
              "offset_start": 541,
              "offset_end": 589,
              "content_hash": "sha256:45062233c931a7b60d4137dd2da6efcde8a03e0c4947626a1b814344d6d51b5a"
            }
          ],
          "analysis": "Candidate causes, none excluded by the reported evidence: (i) the ad-hoc calibration E_dem ~ k_bond/(2r) is not derived and its agreement with the continuum E* of the assembly is never tested; (ii) tool_speed = 5 m/s means the indentation is dynamic — inertial/drag forces superpose on the static contact law, and no ramp/relaxation or quasi-static protocol is documented; (iii) the assembly is 4x3x4 spheres, i.e. the compliant half-space is a few sphere diameters thick, so a stiff far boundary is plausible; (iv) the lattice anisotropy of a bonded-sphere packing. A single-run FAIL cannot attribute the error to (iv) alone, which is what the note asserts.",
          "remediation": "Add a discriminating experiment per candidate: (a) calibrate E_dem against a two-sphere/bulk-modulus test, (b) load at << 5 m/s or with energy-damped relaxation, (c) grow the assembly depth and show convergence of the contact stiffness. Then the residual can be attributed to the lattice.",
          "blocking": false
        },
        {
          "id": "F5",
          "severity": "major",
          "category": "unverifiable-pass",
          "statement": "The only PASS item (beam stiffness 0.0125%) and the claimed second-order convergence are not reproducible from the report: no reference value, no beam data, no mesh series.",
          "evidence": [
            {
              "quote": "| Stiffness error | 44.1% | ≤3% | 0.0125% |",
              "source_field": "markdown",
              "offset_start": 828,
              "offset_end": 871,
              "content_hash": "sha256:053c3916e2760fbde1a9856b5e83bb9a2c6340754e2cc4a53e51b1557d258df4"
            },
            {
              "quote": "- Beam FD shows second-order convergence (error ∝ 1/n²)",
              "source_field": "markdown",
              "offset_start": 1096,
              "offset_end": 1151,
              "content_hash": "sha256:cfc3f3e75c33f8e401ef47e8f9e3e81d4dd0dee0bd44261cd23b457d9cc14937"
            },
            {
              "quote": "| Mesh conv | 8.4% | <5% | converging |",
              "source_field": "markdown",
              "offset_start": 907,
              "offset_end": 946,
              "content_hash": "sha256:caa7ea55b47230a8fa234db9dcf3e4991e1b4163765513c15f6d570c1d8ece18"
            },
            {
              "quote": "- Beam fallback: FD Euler-Bernoulli with simply-supported BCs",
              "source_field": "markdown",
              "offset_start": 612,
              "offset_end": 673,
              "content_hash": "sha256:feb5f36a15d1e5de0ee61c00d0cb721eb813b2d0fe2ea7f81f86bcd24abb327a"
            }
          ],
          "analysis": "A relative error needs a reference. The report gives neither the analytic simply-supported deflection used as reference, nor L, EI, P, nor the grid resolution, so 0.0125% cannot be recomputed or checked for a units/normalisation mistake (a factor-100 slip would look like a superb PASS). The 'second-order convergence' claim likewise rests on a single number (8.4% 'Mesh conv', metric undefined) rather than a mesh sequence with a fitted slope, so it is a hypothesis, not a measurement.",
          "remediation": "Report the numeric reference (delta_ref = 5wL^4/384EI or equivalent), the case constants, and at least three mesh levels n = 40/80/160 with errors and the fitted log-log slope (expected -2).",
          "blocking": false
        },
        {
          "id": "F6",
          "severity": "major",
          "category": "numerical-integrity",
          "statement": "An energy drift of 58.6% against a ≤1% target invalidates the DEM trajectory from which the exponent and stiffness are extracted; the defective trajectory cannot support any contact-law conclusion.",
          "evidence": [
            {
              "quote": "| Energy drift | 58.6% | ≤1% | — |",
              "source_field": "markdown",
              "offset_start": 872,
              "offset_end": 906,
              "content_hash": "sha256:9201583c4155df6d4eb6995e50e4a8bddec7ac56e386d76d16f8e4894b721592"
            },
            {
              "quote": "- **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m",
              "source_field": "markdown",
              "offset_start": 259,
              "offset_end": 327,
              "content_hash": "sha256:09e0e223cca3e837473630f8acfecacaf5193010dbee4c26ce16f008bc9ee4b5"
            }
          ],
          "analysis": "58.6% vs 1.0% is a 58.6x overshoot. Neither the integrator, the timestep, the damping model nor the energy definition ('drift' relative to initial PE?) is stated, so the audit cannot even distinguish a genuine integration error from a wrong energy accounting. Any knowledge object that carries the DEM exponent/stiffness numbers without this defect attached is over-claiming.",
          "remediation": "State integrator and dt, report total (kinetic+potential+contact) energy conservation for a free-flight and a resting-contact control case, and re-run the indentation only after drift < 1%.",
          "blocking": false
        },
        {
          "id": "F7",
          "severity": "minor",
          "category": "precision-of-statement",
          "statement": "The FAIL line conflates a relative percentage with an absolute tolerance: 1.4108 vs 1.5 is a 0.0892 absolute shortfall, 1.78x the stated +-0.05 band, not '5.9% outside a 5% band' as the wording suggests.",
          "evidence": [
            {
              "quote": "- Hertz exponent 1.4108 vs 1.5: **5.9% error, FAIL** (outside ±0.05)",
              "source_field": "markdown",
              "offset_start": 1214,
              "offset_end": 1282,
              "content_hash": "sha256:9ca47176ec640622f0b232fc1c456cd22aeb93886cead7bb17cc1a6bf09f0152"
            }
          ],
          "analysis": "Computed: |1.4108 - 1.5| = 0.0892 (relative 5.9467%), overshoot = 1.784x the 0.05 tolerance. The verdict FAIL is correct and unaffected; only the audit trail is imprecise.",
          "remediation": "State the absolute deviation (0.0892) alongside the percentage.",
          "blocking": false
        },
        {
          "id": "F8",
          "severity": "minor",
          "category": "reproducibility",
          "statement": "The report carries no run identity: no commit, no input deck path, no seed, no sphere radius / packing fraction / timestep, no figure paths.",
          "evidence": [
            {
              "quote": "## ④ Figures",
              "source_field": "markdown",
              "offset_start": 948,
              "offset_end": 960,
              "content_hash": "sha256:cf6e0718d8a4fc43429cebe105ab485736ee79d6581a4038a64ed4d1f83997c9"
            },
            {
              "quote": "See attached: Hertz F-δ curve + beam deflection comparison",
              "source_field": "markdown",
              "offset_start": 961,
              "offset_end": 1019,
              "content_hash": "sha256:db2739f38c45b5bf7793a41a60d23a697c59746a7cdbdf0471af815e3231bb9e"
            }
          ],
          "analysis": "Record carries figures = 1; the text points to 'attached' curves without file names, so a reviewer cannot bind the plotted quantity to the table numbers. The geometry line gives the grid (4x3x4) and the indenter radius but not the sphere radius r that the E_dem ~ k_bond/(2r) calibration needs — the calibration therefore cannot be recomputed at all.",
          "remediation": "Add a run-identity block: repo+commit, input deck path, sphere radius, packing fraction, dt, seed, figure file names.",
          "blocking": false
        }
      ],
      "claim_judgements": [
        {
          "claim_id": "cj-exponent-fail",
          "text": "Hertz exponent 1.4108 vs target 1.5 +- 0.05 is a FAIL.",
          "evidence": [
            {
              "quote": "| Exponent | 1.4108 | 1.5±0.05 | — |",
              "source_field": "markdown",
              "offset_start": 791,
              "offset_end": 827,
              "content_hash": "sha256:62c1b9b20ded4f00882d1046c09e1736d345bef93e16203627dd26ac72a0f0c0"
            },
            {
              "quote": "- Hertz exponent 1.4108 vs 1.5: **5.9% error, FAIL** (outside ±0.05)",
              "source_field": "markdown",
              "offset_start": 1214,
              "offset_end": 1282,
              "content_hash": "sha256:9ca47176ec640622f0b232fc1c456cd22aeb93886cead7bb17cc1a6bf09f0152"
            }
          ],
          "judgement": "supports",
          "reasoning": "Arithmetic confirms the FAIL: |1.4108-1.5| = 0.0892 > 0.05. The claim is faithful to the source and correctly signed; only its phrasing is imprecise (F7). What it may NOT be used to support is the causal reading 'lattice cannot do Hertz' (F3, F4)."
        },
        {
          "claim_id": "cj-stiffness-fail",
          "text": "Hertz stiffness error 44.1% vs target <=3% is a FAIL.",
          "evidence": [
            {
              "quote": "| Stiffness error | 44.1% | ≤3% | 0.0125% |",
              "source_field": "markdown",
              "offset_start": 828,
              "offset_end": 871,
              "content_hash": "sha256:053c3916e2760fbde1a9856b5e83bb9a2c6340754e2cc4a53e51b1557d258df4"
            },
            {
              "quote": "- Hertz stiffness 44.1%: **FAIL** (target ≤3%)",
              "source_field": "markdown",
              "offset_start": 1283,
              "offset_end": 1329,
              "content_hash": "sha256:77fab96e6f0c3cf516306673b28dae9948326fdcf0da6abd7b8c58252991f8e6"
            }
          ],
          "judgement": "qualifies",
          "reasoning": "The FAIL verdict is arithmetic-consistent (44.1/3 = 14.7x the budget), but the 44.1% itself is not recomputable: E* needs Poisson's ratio and E_dem needs the sphere radius r, neither is stated. A knowledge object must carry the number as 'as-reported, base quantities missing', not as a verified material property of the lattice."
        },
        {
          "claim_id": "cj-beam-pass",
          "text": "Beam FD (n=80) stiffness error 0.0125% vs <=3% is a PASS.",
          "evidence": [
            {
              "quote": "| Stiffness error | 44.1% | ≤3% | 0.0125% |",
              "source_field": "markdown",
              "offset_start": 828,
              "offset_end": 871,
              "content_hash": "sha256:053c3916e2760fbde1a9856b5e83bb9a2c6340754e2cc4a53e51b1557d258df4"
            },
            {
              "quote": "- Beam stiffness 0.0125%: **PASS** (<3%)",
              "source_field": "markdown",
              "offset_start": 1330,
              "offset_end": 1370,
              "content_hash": "sha256:41990b6314c3129e2af40f8d70735fdb096a43d0085b169cae44521cc33d4482"
            }
          ],
          "judgement": "insufficient",
          "reasoning": "No reference deflection, beam constants or normalisation convention appears in the report, so the PASS is unfalsifiable (F5). It must not be promoted to a reusable 'FD Euler-Bernoulli is validated to 1e-4' knowledge claim."
        },
        {
          "claim_id": "cj-energy-fail",
          "text": "Energy drift 58.6% vs <=1% target is a FAIL.",
          "evidence": [
            {
              "quote": "| Energy drift | 58.6% | ≤1% | — |",
              "source_field": "markdown",
              "offset_start": 872,
              "offset_end": 906,
              "content_hash": "sha256:9201583c4155df6d4eb6995e50e4a8bddec7ac56e386d76d16f8e4894b721592"
            }
          ],
          "judgement": "supports",
          "reasoning": "1% target, 58.6% measured: 58.6x over budget. Verdict supported and, per F6, it is the most consequential number in the report because it disqualifies the companion results."
        },
        {
          "claim_id": "cj-lattice-cannot-hertz",
          "text": "DEM discrete lattice cannot reproduce continuum Hertz contact.",
          "evidence": [
            {
              "quote": "- DEM discrete lattice cannot reproduce continuum Hertz contact",
              "source_field": "markdown",
              "offset_start": 1032,
              "offset_end": 1095,
              "content_hash": "sha256:4f41c28d9727da379bfe48393c4cd40a9a7b701036aab10d721a6490c40aae3d"
            },
            {
              "quote": "Effective modulus estimated: E_dem ≈ k_bond/(2r)",
              "source_field": "markdown",
              "offset_start": 541,
              "offset_end": 589,
              "content_hash": "sha256:45062233c931a7b60d4137dd2da6efcde8a03e0c4947626a1b814344d6d51b5a"
            }
          ],
          "judgement": "refutes",
          "reasoning": "Refuted as stated (a universal/structural claim drawn from one confounded run). The supported version is narrower: 'in this setup (delta/R = 0.5, tool_speed 5 m/s, 4x3x4 assembly, E_dem = k_bond/(2r) calibration) the fitted law deviates from Hertz'. See F3/F4 for the un-excluded causes."
        },
        {
          "claim_id": "cj-second-order",
          "text": "Beam FD shows second-order convergence (error proportional to 1/n^2).",
          "evidence": [
            {
              "quote": "- Beam FD shows second-order convergence (error ∝ 1/n²)",
              "source_field": "markdown",
              "offset_start": 1096,
              "offset_end": 1151,
              "content_hash": "sha256:cfc3f3e75c33f8e401ef47e8f9e3e81d4dd0dee0bd44261cd23b457d9cc14937"
            },
            {
              "quote": "| Mesh conv | 8.4% | <5% | converging |",
              "source_field": "markdown",
              "offset_start": 907,
              "offset_end": 946,
              "content_hash": "sha256:caa7ea55b47230a8fa234db9dcf3e4991e1b4163765513c15f6d570c1d8ece18"
            }
          ],
          "judgement": "insufficient",
          "reasoning": "A convergence order requires errors at >=3 resolutions and a fitted slope; the report shows one undefined 'Mesh conv' number and the word 'converging'. Order 2 is plausible for the Euler-Bernoulli FD stencil but is unmeasured here."
        },
        {
          "claim_id": "cj-schema-validates",
          "text": "Schema validates against jsonschema.",
          "evidence": [
            {
              "quote": "Schema  validates against jsonschema",
              "source_field": "markdown",
              "offset_start": 1154,
              "offset_end": 1190,
              "content_hash": "sha256:5849a2e9b9990c34732f65b5a53e9bace92c4747533a040e45039afe2d0c0293"
            }
          ],
          "judgement": "insufficient",
          "reasoning": "No schema file, $id, validator version or exit status; the sentence is not checkable and should stay unresolved in any extraction (F2)."
        }
      ],
      "review_event": {
        "event_id": "rev-wp-331-04-01",
        "package_id": "wp-331-01",
        "time": "2026-11-12T02:37:49+00:00",
        "decision": "request_changes",
        "reviewer": {
          "agent": "agent/m15788",
          "role": "red-team-reviewer"
        },
        "blocking_findings": [
          "F1"
        ],
        "major_findings": [
          "F2",
          "F3",
          "F4",
          "F5",
          "F6"
        ],
        "basis": "upstream product not retrievable + 5 major defects in the reviewable source",
        "marks_claims_verified": false
      },
      "acceptance_selfcheck": {
        "valid_json": true,
        "schema_pass": true,
        "reviewer_independent": true,
        "upstream_packages_completed": false,
        "note": "upstream_packages_completed is honestly FALSE (product unreachable, F1); reviewer_independent holds: no producer context was read, no producer prompt used. The reviewer asserts no verification state for any claim: verification is the platform gate's exclusive output and is deliberately absent from this package."
      },
      "checks_not_run": [
        "claim-level extraction fidelity vs wp-331-01 product (product unreachable; see F1)",
        "review-ledger fold / G3 semantic gate execution (platform gate, out of scope for this package)",
        "re-execution of the DEM indentation or the beam FD solve (no run identity in the source: no commit, deck path, radius, dt, seed — see F8)",
        "figure contents (Hertz F-delta curve, beam deflection) — only the record's figure count was read",
        "cross-report consistency of the M404 series (out of scope: single report_id per contract boundary)"
      ],
      "limitations": [
        "Single channel: the platform reports list returns at most the newest 50-100 rows and ignores ?tag=/?offset=, so absence of a kf-wp:wp-331-01 record is 'not found on the reachable window', not proof of non-existence; psql on tensor_reports is permission-denied for this identity.",
        "Reviewer sees only report markdown + record metadata; no producer explanation, no prior review events, no code — therefore root-cause statements about the solver (integrator choice, contact model) are inferences from the parameter line, marked as such.",
        "All numeric judgements are arithmetic on the report's own table; they validate internal consistency of the report, not the physics it claims to simulate.",
        "No finding here marks any claim as verified; verification is the platform gate's job."
      ],
      "repro_cmd": "cd <worktree> && python3 scripts/kf_wp331_04/build_review.py && python3 scripts/kf_wp331_04/verify_review.py"
    }
  }
}
```
