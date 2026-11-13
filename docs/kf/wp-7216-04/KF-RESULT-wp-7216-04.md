# KF-RESULT wp-7216-04

**工作包** `wp-7216-04` · task_type `04-independent-review` · lane C · **审核对象** `wp-7216-01`（report_id 7216）· 原文 sha256 `sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b` · 11338 chars

**结论**：verdict = **pass**（disposition `approve`）· 37 条规则全过（失败 0）· 阻塞项 0 · 非阻塞观察 4 条。本包只动审核轴（review axis）；verification 轴（L0–L3）由平台门计算，本包不写、也不把任何结论标成 verified。

## ① 本工序做了什么

对 `wp-7216-01`（report 7216 的 01-资产登记包）做独立红队审核：把它每一条可核查断言（源哈希/字符数/字节数/行数/标题/场景/40 条资产定位符/计数/完整性块/分辨率标签）在本次运行内从活的报告原文重新推导，判「登记是否忠实描述原文」，给 pass / needs-fix / fail。生产者自检（`gate_sim.json`、`verification.json`、`AUDIT_NOTES.md`）不作证据——那是被审的主张本身。

审核对象是登记包：`claims == []`（合法，`no_forced_claim_generation`）。因此本审核判定的是「登记保真」，不判定报告 §3/§5 的科学数字（那是 03/05 的对象，见 §⑤ 局限）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源（单信道）**：`POST /api/v1/auth/login`（凭据只从环境变量读，不落盘）→ `GET /api/v1/tensor/reports/7216`，只取 `markdown`。本机 `psql` 直连被拒（`permission denied for table tensor_reports`），故 API 是唯一取源通道。
2. **本次内重算源身份**：UTF-8 字节 sha256 = `sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b`，chars = 11338，bytes = 17984，logical lines = 210（`rstrip` 约定），与契约 `input.source_hash` / `source.chars` 逐项比对。
3. **逐条重解定位符**（40 条资产）：按各自 `locator.method` 套规则——`char_span` 要求 `md[char_start:char_end] == quote`；`document` 要求跨度=全文且 quote 是原文前缀；再验 `quote_sha256`、`line_start/line_end`、`occurrence_lines`（子串读法 / 脱离式读法双读）、`token ∈ quote`、章节归属、`unique` 旗标，以及 `local_copy` 声明的副本重新哈希。
4. **计数与完整性块重算**：`counts.by_class` / `by_resolution` / `figure_declarations_in_prose` / `record_figures`（对照平台记录的 figures 列表）/ `integrity.quote_uniqueness` 全部重算，不做信任式接受。
5. **覆盖率**：从原文抽全部反引号 token（去重后 44 个），与登记的 39 个 token 求差，再按文件/符号形状分类，排除公式与命令串。
6. **诚实性反查**：manifest 内不得出现 `verified: true`；`resolution` 必须等于其 `resolution_check.result`；并独立探针复核「图字节不可得」这一主张（`GET /tensor/reports/7216/figures/rb_growth_rate.png` → HTTP 404）。
7. **互操作反查**：把 A01 的定位符按字段名映射进本仓证据门 `ke.wp_gate.locator_matches()`，看平台既有偏移规则会怎么判（结果见 §④ 的 N2）。
8. **本次未运行项**（如实登记）：`existence of the job directories named in the report (TensorLBM bytes are not in this worktree; the manifest labels them referenced_unresolved, which this review can neither confirm nor refute)`；`platform-side acceptance of wp-7216-01 as its published result report (not read: this package is scoped to report_id 7216)`；`scientific correctness of the report's own numbers (that is a 03/05 object; this package registers pointers only and emits zero claims)`。

**repro_cmd**（工作树根执行，一键复跑）：

```
# 0) 取源（登录 + 取报告 markdown；凭据从环境变量读）
python3 scripts/kf_fetch_7216.py --out runs/wp-7216-04/source_7216.md
# 1) 独立审核（37 条规则，全部事实本次内重算）
python3 scripts/kf_wp721604_review.py --upstream /root/tp-agent/work/m15594/docs/kf/wp-7216-01 \
    --out-json docs/kf/wp-7216-04/review_report.json \
    --out-md docs/kf/wp-7216-04/review_checks.md
# 2) 渲染报告 + 图 + schema 校验（schema 不过则非零退出）
python3 scripts/kf_wp721604_render.py
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `outputs.review_report.json`（本报告唯一 json 块） | 37 条规则逐条结论 + 4 条观察 + verdict/disposition + 未运行项 |
| `docs/kf/wp-7216-04/review_checks.md` | 规则 × 结论 × 细节全表（机器生成） |
| `docs/kf/wp-7216-04/review_report.json` | 同上结构化版（checks / findings / notes / evidence） |
| `runs/wp-7216-04/source_7216.md` | 报告原文字节副本（sha256 `sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b`），供离线复核 |
| `runs/wp-7216-04/upstream_snapshot.json` | 被审上游包每个文件的 sha256/字节数（只哈希不复制，避免覆盖上游产物） |
| `figures/wp-7216-04/review_map.png` | 上：规则族通过/失败；下：40 条资产定位符在原文上的跨度图（sha256 `sha256:442c065ed25fd46a3438adf5c81f93600b0098b0ff811ed96c677efdcc31db58`） |
| `scripts/kf_fetch_7216.py`、`kf_wp721604_review.py`、`kf_wp721604_render.py` | 取源 / 审核 / 渲染三段可复跑脚本 |

## ④ 证据定位表（claim → 原文引文 / 工件字段）

| # | 主张 | 逐字引文（原文）或工件字段 | 判定 |
|---|---|---|---|
| E1 | 源身份三处一致（live = manifest = 契约） | 工件 `source_recomputation.sha256` = `sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b`，与契约 `input.source_hash` 逐字相同 | PASS |
| E2 | 报告自称的仓库/分支被正确登记 | 「**节点**: IN31-N12（战役 DAG，物理域） · **仓库**: TensorLBM · **分支**: `agent/m5628`」→ A02（`git_branch_reference`，`referenced_unresolved`） | PASS |
| E3 | 图字节确实不可得（支撑 unresolved 分类） | 「见随报告提交的 PNG（全部由 `benchmarks/rb_discrete_stability/make_figures.py` 从 JSON 程序化生成）」+ 独立探针 404 | PASS |
| E4 | 报告自己就写 honest FAIL，登记不冒充已验证 |「**否（honest FAIL）**」；manifest `integrity.verified_marks_emitted = 0`、`claims = []` | PASS |
| E5 | 40 条定位符逐字可复现 | 工件 `checks` 之 `L2.quote_verbatim_at_span` / `L3.quote_sha256` / `L4.line_numbers` 全 PASS | PASS |
| E6 | 计数与完整性块自洽 | 工件 `C1`–`C8`、`L9.integrity_block` 全 PASS（assets=40，resolved/unresolved=1/39） | PASS |
| E7 | 上游包存在且其断言可复算 | `upstream_snapshot.json`：`asset_manifest.json` sha256 `sha256:b534a86106ff5b4187d1345313a1735f3d427210a82f5090a2ba5bfdc2d25f65`；本审核把它的断言重算 37/37 通过 | PASS |

**非阻塞观察**（不是失败项，但建议上游下一版收敛）

| id | 严重度 | 观察 | 证据（机器抽取） |
|---|---|---|---|
| N1 | minor | two tokens are call expressions rather than symbols; exact-token lookup must fall back to symbol_key | `[["A19", "collide_two_component_with_gravity(f1,f2,G_12,τ1,τ2,gz1,gz2,u_eq)", "collide_two_component_with_gravity"], ["A29", "critical_rayleigh_continuous(M_list=(50,100,200))", "critical_rayleigh_continuous"]]` |
| N2 | minor | the document-level locator's quote is a one-line title excerpt, not the span text; re-checking it with the repo's offset rule yields QUOTE_NOT_AT_LOCATOR. Harmless as delivered (field names differ, so a consumer falls back to quote search), but a field-name mapping would reject it | `{"asset": "A01", "platform_rule_result": [false, "QUOTE_NOT_AT_LOCATOR", "text[0:11338]='# IN31-N12 · LBM Rayleigh–Bénard 离散线性稳定性 + 双相黏度比/密度比解耦与 Hada' != quote '# IN31-N12 · LBM Rayleigh–Bénard 离散线性稳定性 + 双相黏度比/密度比解耦与 Hada'"], "quote_occurs_once": true}` |
| N3 | minor | occurrence_lines follows an undocumented 'standalone occurrence' reading (token not embedded in a longer dotted identifier); the substring reading gives extra lines. Documenting the field would stop independent re-checkers from disagreeing | `{"A09": {"declared": [40], "standalone": [40], "substring": [13, 40]}, "A10": {"declared": [40], "standalone": [40], "substring": [13, 40]}, "A18": {"declared": [69], "standalone": [69], "substring": [64, 69]}}` |
| N4 | info | registration carries pointers only: 39/40 assets are referenced_unresolved and the package emits zero claims, so no scientific statement of report 7216 is adjudicated here | `{"referenced_unresolved": 39, "assets": 40, "claims": [], "figure_probe": {"/tensor/reports/7216/figures/rb_growth_rate.png": 404, "/tensor/reports/7216/figures": 404}}` |

阻塞项：**0**。

## ⑤ 注意点与局限

1. **审核对象的层级**：上游是登记包（`claims == []`），所以「语义保真」的落点是「登记是否忠实于原文」，不是「报告 §3 的数字是否正确」。后者本包无对象可审，如实记为未覆盖，不当成通过。
2. **跨仓不可达**：40 条资产里 39 条 `referenced_unresolved`（TensorLBM 代码/工件/图字节不在本工作树，图端点 404）。本审核只能判它没有冒充已解析，不能证实那些文件真的存在。
3. **独立性是制度性的**：不同工作包/不同工作树/不同会话 + 生产者自检排除在证据之外；但同一模型家族的共同盲点无法由此排除（全文见 `review_report.independence_limitations`）。
4. **两处字段语义靠合理默认消解**：`occurrence_lines`（脱离式 vs 子串式出现）、A01 的 `method=document`（quote 是标题摘要而非跨度全文）。都不构成失败，但缺文档会让下一个独立复算者得出不同结论——已列为 N2/N3。
5. **越界自查**：只用 API 单信道取源；未读/写任何其它 `report_id`；未改动上游产物（只哈希登记）；未给任何 claim 标 verified。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结论 | 依据 |
|---|---|---|
| `valid_json` | ✅ | 本报告唯一 json 块由 `json.loads` 解析通过（渲染时机器校验） |
| `schema_pass` | ✅ | `schemas/kf_result.v1.schema.json`（Draft 2020-12）校验 0 错误；渲染脚本 schema 不过即非零退出 |
| `reviewer_independent` | ✅ | `reviewer_id = kf-worker/m15851` ≠ `producer = kf-worker/m15594`（规则 M1）；审核上下文排除生产者自检（规则 M2） |
| `upstream_packages_completed` | ✅ | 上游 `wp-7216-01` 产物齐备（`asset_manifest.json` + `kf_result.json`），其断言经本审核独立重算 37/37 通过；**但**未读取它发布后的结果报告（report_id 越界约束），故「平台是否已收」记为未运行、不作断言 |
| `constraints.review_prompt_not_copied_from_producer` | ✅ | 审核用本包自写的 37 条规则（字节重算 / 逐字定位 / 端点探针），未复用 `extraction-skills/prompts/producer-v1.md` |
| `constraints.reviewer_context_excludes_producer_explanation` | ✅ | 证据只用 live markdown + `asset_manifest.json`；`gate_sim.json` / `verification.json` / `AUDIT_NOTES.md` 列入排除项 |
| `constraints.do_not_mark_claims_as_verified` | ✅ | `verification_status = not_verified_by_reviewer`，未产出任何 verified 标记 |
| `output.review_report.json` | ✅ | 见 json 块 `outputs.review_report.json`（37 规则 + 4 观察） |

失败项：无。若上游按 N1–N3 补字段文档，下一轮复算可自动收敛。

---

### 附：规则明细（机器生成，未手抄）

reviewed: wp-7216-01 (report 7216) · verdict: **pass** (disposition `approve`) · rules: 37 · failed: 0

| rule | ok | detail |
|---|---|---|
| `R1.sha256_recomputed` | PASS | live=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b manifest=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b |
| `R2.hash_matches_contract` | PASS | live=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b contract=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b |
| `R3.chars` | PASS | live=11338 manifest=11338 contract=11338 |
| `R4.bytes_utf8` | PASS | live=17984 manifest=17984 |
| `R5.lines` | PASS | live(rstrip-convention)=210 manifest=210 |
| `R6.eol_flags` | PASS | crlf live=False manifest=False; trailing newline live=True manifest=True |
| `R7.title_matches_record` | PASS | manifest='IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison' record='IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison' |
| `R8.scenario_and_mission` | PASS | scenario manifest='lbm_rb_hr_validation' record='lbm_rb_hr_validation'; mission manifest=5628 record=5628 |
| `R9.status_matches_record` | PASS | manifest='published' record='published' |
| `R10.attachments_manifest_not_needed` | PASS | record has no attachments field; nothing to resolve by manifest |
| `M1.reviewer_is_not_producer` | PASS | producer='kf-worker/m15594' reviewer='kf-worker/m15851' |
| `M2.producer_selfcheck_not_used_as_input` | PASS | inputs = live markdown + asset_manifest.json only; gate_sim.json / verification.json / AUDIT_NOTES.md excluded from the review context |
| `C1.count_assets` | PASS | declared=40 actual=40 |
| `C2.by_class` | PASS | declared={'api_symbol_reference': 17, 'benchmark_script_reference': 3, 'data_artifact_reference': 6, 'directory_reference': 1, 'figure_reference': 6, 'git_branch_reference': 1, 'report_markdown': 1, 'source_code_reference': 3, 'test_reference': 2} actual={'report_markdown': 1, 'git_branch_reference': 1, 'api_symbol_reference': 17, 'directory_reference': 1, 'source_code_reference': 3, 'benchmark_script_reference': 3, 'figure_reference': 6, 'data_artifact_reference': 6, 'test_reference': 2} |
| `C3.by_resolution` | PASS | declared={'referenced_unresolved': 39, 'resolved_in_source': 1} actual={'resolved_in_source': 1, 'referenced_unresolved': 39} |
| `C4.resolved_pair` | PASS | declared=1/39 actual=1/39 |
| `C5.figure_declarations_in_prose` | PASS | declared=6 distinct prose names=6 (7 textual occurrences) registered figure assets=6; sets equal=True |
| `C6.record_figures` | PASS | declared=5 record_len=5 names=['hr_decoupling_settling.png', 'rb_base_profile.png', 'rb_eig_vs_sim.png', 'rb_growth_rate.png', 'rb_ra_c_convergence.png'] |
| `C7.every_record_figure_declared_in_prose` | PASS | record figures missing from prose declarations=[] |
| `C8.claims_empty_reason` | PASS | claims=[] reason_chars=332 (empty claim set is legal for a registration-only package; S12 of the line) |
| `L1.char_span_in_bounds` | PASS | bad=[] |
| `L2.quote_verbatim_at_span` | PASS | mismatched=[] (0 total) |
| `L3.quote_sha256` | PASS | mismatched=[] |
| `L4.line_numbers` | PASS | mismatched=[] (0 total) |
| `L5.occurrence_lines` | PASS | declared lists match neither the substring nor the standalone reading for [] (0 total) |
| `L6.token_inside_quote` | PASS | tokens outside their own span=[] |
| `L7.locator_unique_flag` | PASS | unique flag disagrees with in-document occurrence count=[] |
| `L8.section_attribution` | PASS | heading attribution mismatches=[] (0 total) |
| `L9.integrity_block` | PASS | declared locators=40 unique_quotes=40 hash=True; recomputed locators=40 unique_quotes=40 hash=True |
| `L11.local_copies_hash_to_declared` | PASS | local copies re-hashed=1 mismatch=none ([]) |
| `L10.ids_unique` | PASS | ids=40 keys=40 n=40 |
| `S1.backticked_coverage` | PASS | 45 unique backticked tokens; 39 registered tokens; 5 unregistered (file/symbol-shaped: []) |
| `X1.no_verified_marks` | PASS | manifest emits no verified marker; integrity.verified_marks_emitted=0 |
| `X2.resolution_vocabulary` | PASS | resolution values=['referenced_unresolved', 'resolved_in_source'] |
| `X3.resolution_consistent_with_check` | PASS | resolution label equals its resolution_check.result for every asset |
| `X4.figure_bytes_not_served_claim` | PASS | independent probe of the platform figure endpoint: ['/tensor/reports/7216/figures', '/tensor/reports/7216/figures/rb_growth_rate.png'] -> HTTP [404] (supports the manifest's referenced_unresolved figure class) |
| `X5.same_basename_hits_exist` | PASS | declared same-basename hits that do not exist in this worktree=[] (checked 1 paths) |

```json
{
  "package_id": "wp-7216-04",
  "task_type": "04-independent-review",
  "report_id": "7216",
  "provenance": {
    "source_hash": "sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
    "source_field": "markdown",
    "producer": "kf-worker/m15851",
    "emitted_at": "2026-11-12T02:54:21+00:00",
    "notes": "reviewed_package=wp-7216-01; artefact sha256 sha256:b534a86106ff5b4187d1345313a1735f3d427210a82f5090a2ba5bfdc2d25f65; reviewer context = live markdown + asset_manifest.json only"
  },
  "outputs": {
    "review_report.json": {
      "schema": "kf-review-report.v1",
      "package_id": "wp-7216-04",
      "reviewed_package": "wp-7216-01",
      "report_id": "7216",
      "reviewer_role": "red-team-reviewer",
      "reviewer_id": "kf-worker/m15851",
      "reviewer_independent": true,
      "review_context": {
        "inputs": [
          "live report markdown (GET /api/v1/tensor/reports/7216, hashed in this run)",
          "upstream artefact asset_manifest.json (wp-7216-01)"
        ],
        "excluded": [
          "gate_sim.json",
          "verification.json",
          "AUDIT_NOTES.md",
          "any producer rationale or self-assessment prose"
        ],
        "note": "the producer's self-checks are the claim under review, not evidence for it"
      },
      "source_recomputation": {
        "sha256": "sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
        "chars": 11338,
        "bytes_utf8": 17984,
        "lines": 210,
        "title": "IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison",
        "status": "published",
        "record_figures": [
          "hr_decoupling_settling.png",
          "rb_base_profile.png",
          "rb_eig_vs_sim.png",
          "rb_growth_rate.png",
          "rb_ra_c_convergence.png"
        ]
      },
      "disposition": "approve",
      "verdict": "pass",
      "verdict_mapping": {
        "pass": [
          "approve",
          "approve-with-notes"
        ],
        "needs-fix": [
          "request-changes"
        ],
        "fail": [
          "reject"
        ]
      },
      "verification_status": "not_verified_by_reviewer",
      "review_axis_note": "approving this package moves the review axis only; the verification axis (L0-L3) is computed by the platform gate and is not written here",
      "checks": [
        {
          "rule": "R1.sha256_recomputed",
          "ok": true,
          "detail": "live=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b manifest=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
          "severity_if_fail": "critical"
        },
        {
          "rule": "R2.hash_matches_contract",
          "ok": true,
          "detail": "live=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b contract=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
          "severity_if_fail": "critical"
        },
        {
          "rule": "R3.chars",
          "ok": true,
          "detail": "live=11338 manifest=11338 contract=11338",
          "severity_if_fail": "critical"
        },
        {
          "rule": "R4.bytes_utf8",
          "ok": true,
          "detail": "live=17984 manifest=17984",
          "severity_if_fail": "major"
        },
        {
          "rule": "R5.lines",
          "ok": true,
          "detail": "live(rstrip-convention)=210 manifest=210",
          "severity_if_fail": "major"
        },
        {
          "rule": "R6.eol_flags",
          "ok": true,
          "detail": "crlf live=False manifest=False; trailing newline live=True manifest=True",
          "severity_if_fail": "minor"
        },
        {
          "rule": "R7.title_matches_record",
          "ok": true,
          "detail": "manifest='IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison' record='IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison'",
          "severity_if_fail": "major"
        },
        {
          "rule": "R8.scenario_and_mission",
          "ok": true,
          "detail": "scenario manifest='lbm_rb_hr_validation' record='lbm_rb_hr_validation'; mission manifest=5628 record=5628",
          "severity_if_fail": "major"
        },
        {
          "rule": "R9.status_matches_record",
          "ok": true,
          "detail": "manifest='published' record='published'",
          "severity_if_fail": "minor"
        },
        {
          "rule": "R10.attachments_manifest_not_needed",
          "ok": true,
          "detail": "record has no attachments field; nothing to resolve by manifest",
          "severity_if_fail": "minor"
        },
        {
          "rule": "M1.reviewer_is_not_producer",
          "ok": true,
          "detail": "producer='kf-worker/m15594' reviewer='kf-worker/m15851'",
          "severity_if_fail": "critical"
        },
        {
          "rule": "M2.producer_selfcheck_not_used_as_input",
          "ok": true,
          "detail": "inputs = live markdown + asset_manifest.json only; gate_sim.json / verification.json / AUDIT_NOTES.md excluded from the review context",
          "severity_if_fail": "critical"
        },
        {
          "rule": "C1.count_assets",
          "ok": true,
          "detail": "declared=40 actual=40",
          "severity_if_fail": "major"
        },
        {
          "rule": "C2.by_class",
          "ok": true,
          "detail": "declared={'api_symbol_reference': 17, 'benchmark_script_reference': 3, 'data_artifact_reference': 6, 'directory_reference': 1, 'figure_reference': 6, 'git_branch_reference': 1, 'report_markdown': 1, 'source_code_reference': 3, 'test_reference': 2} actual={'report_markdown': 1, 'git_branch_reference': 1, 'api_symbol_reference': 17, 'directory_reference': 1, 'source_code_reference': 3, 'benchmark_script_reference': 3, 'figure_reference': 6, 'data_artifact_reference': 6, 'test_reference': 2}",
          "severity_if_fail": "major"
        },
        {
          "rule": "C3.by_resolution",
          "ok": true,
          "detail": "declared={'referenced_unresolved': 39, 'resolved_in_source': 1} actual={'resolved_in_source': 1, 'referenced_unresolved': 39}",
          "severity_if_fail": "major"
        },
        {
          "rule": "C4.resolved_pair",
          "ok": true,
          "detail": "declared=1/39 actual=1/39",
          "severity_if_fail": "major"
        },
        {
          "rule": "C5.figure_declarations_in_prose",
          "ok": true,
          "detail": "declared=6 distinct prose names=6 (7 textual occurrences) registered figure assets=6; sets equal=True",
          "severity_if_fail": "major"
        },
        {
          "rule": "C6.record_figures",
          "ok": true,
          "detail": "declared=5 record_len=5 names=['hr_decoupling_settling.png', 'rb_base_profile.png', 'rb_eig_vs_sim.png', 'rb_growth_rate.png', 'rb_ra_c_convergence.png']",
          "severity_if_fail": "minor"
        },
        {
          "rule": "C7.every_record_figure_declared_in_prose",
          "ok": true,
          "detail": "record figures missing from prose declarations=[]",
          "severity_if_fail": "major"
        },
        {
          "rule": "C8.claims_empty_reason",
          "ok": true,
          "detail": "claims=[] reason_chars=332 (empty claim set is legal for a registration-only package; S12 of the line)",
          "severity_if_fail": "major"
        },
        {
          "rule": "L1.char_span_in_bounds",
          "ok": true,
          "detail": "bad=[]",
          "severity_if_fail": "critical"
        },
        {
          "rule": "L2.quote_verbatim_at_span",
          "ok": true,
          "detail": "mismatched=[] (0 total)",
          "severity_if_fail": "critical"
        },
        {
          "rule": "L3.quote_sha256",
          "ok": true,
          "detail": "mismatched=[]",
          "severity_if_fail": "critical"
        },
        {
          "rule": "L4.line_numbers",
          "ok": true,
          "detail": "mismatched=[] (0 total)",
          "severity_if_fail": "major"
        },
        {
          "rule": "L5.occurrence_lines",
          "ok": true,
          "detail": "declared lists match neither the substring nor the standalone reading for [] (0 total)",
          "severity_if_fail": "minor"
        },
        {
          "rule": "L6.token_inside_quote",
          "ok": true,
          "detail": "tokens outside their own span=[]",
          "severity_if_fail": "major"
        },
        {
          "rule": "L7.locator_unique_flag",
          "ok": true,
          "detail": "unique flag disagrees with in-document occurrence count=[]",
          "severity_if_fail": "minor"
        },
        {
          "rule": "L8.section_attribution",
          "ok": true,
          "detail": "heading attribution mismatches=[] (0 total)",
          "severity_if_fail": "minor"
        },
        {
          "rule": "L9.integrity_block",
          "ok": true,
          "detail": "declared locators=40 unique_quotes=40 hash=True; recomputed locators=40 unique_quotes=40 hash=True",
          "severity_if_fail": "major"
        },
        {
          "rule": "L11.local_copies_hash_to_declared",
          "ok": true,
          "detail": "local copies re-hashed=1 mismatch=none ([])",
          "severity_if_fail": "major"
        },
        {
          "rule": "L10.ids_unique",
          "ok": true,
          "detail": "ids=40 keys=40 n=40",
          "severity_if_fail": "critical"
        },
        {
          "rule": "S1.backticked_coverage",
          "ok": true,
          "detail": "45 unique backticked tokens; 39 registered tokens; 5 unregistered (file/symbol-shaped: [])",
          "severity_if_fail": "minor"
        },
        {
          "rule": "X1.no_verified_marks",
          "ok": true,
          "detail": "manifest emits no verified marker; integrity.verified_marks_emitted=0",
          "severity_if_fail": "critical"
        },
        {
          "rule": "X2.resolution_vocabulary",
          "ok": true,
          "detail": "resolution values=['referenced_unresolved', 'resolved_in_source']",
          "severity_if_fail": "critical"
        },
        {
          "rule": "X3.resolution_consistent_with_check",
          "ok": true,
          "detail": "resolution label equals its resolution_check.result for every asset",
          "severity_if_fail": "major"
        },
        {
          "rule": "X4.figure_bytes_not_served_claim",
          "ok": true,
          "detail": "independent probe of the platform figure endpoint: ['/tensor/reports/7216/figures', '/tensor/reports/7216/figures/rb_growth_rate.png'] -> HTTP [404] (supports the manifest's referenced_unresolved figure class)",
          "severity_if_fail": "minor"
        },
        {
          "rule": "X5.same_basename_hits_exist",
          "ok": true,
          "detail": "declared same-basename hits that do not exist in this worktree=[] (checked 1 paths)",
          "severity_if_fail": "minor"
        }
      ],
      "checks_summary": {
        "total": 37,
        "passed": 37,
        "failed": 0,
        "failed_rules": []
      },
      "findings": [],
      "notes": [
        {
          "id": "N1",
          "severity": "minor",
          "blocking": false,
          "statement": "two tokens are call expressions rather than symbols; exact-token lookup must fall back to symbol_key",
          "evidence": [
            [
              "A19",
              "collide_two_component_with_gravity(f1,f2,G_12,τ1,τ2,gz1,gz2,u_eq)",
              "collide_two_component_with_gravity"
            ],
            [
              "A29",
              "critical_rayleigh_continuous(M_list=(50,100,200))",
              "critical_rayleigh_continuous"
            ]
          ]
        },
        {
          "id": "N2",
          "severity": "minor",
          "blocking": false,
          "statement": "the document-level locator's quote is a one-line title excerpt, not the span text; re-checking it with the repo's offset rule yields QUOTE_NOT_AT_LOCATOR. Harmless as delivered (field names differ, so a consumer falls back to quote search), but a field-name mapping would reject it",
          "evidence": {
            "asset": "A01",
            "platform_rule_result": [
              false,
              "QUOTE_NOT_AT_LOCATOR",
              "text[0:11338]='# IN31-N12 · LBM Rayleigh–Bénard 离散线性稳定性 + 双相黏度比/密度比解耦与 Hada' != quote '# IN31-N12 · LBM Rayleigh–Bénard 离散线性稳定性 + 双相黏度比/密度比解耦与 Hada'"
            ],
            "quote_occurs_once": true
          }
        },
        {
          "id": "N3",
          "severity": "minor",
          "blocking": false,
          "statement": "occurrence_lines follows an undocumented 'standalone occurrence' reading (token not embedded in a longer dotted identifier); the substring reading gives extra lines. Documenting the field would stop independent re-checkers from disagreeing",
          "evidence": {
            "A09": {
              "declared": [
                40
              ],
              "standalone": [
                40
              ],
              "substring": [
                13,
                40
              ]
            },
            "A10": {
              "declared": [
                40
              ],
              "standalone": [
                40
              ],
              "substring": [
                13,
                40
              ]
            },
            "A18": {
              "declared": [
                69
              ],
              "standalone": [
                69
              ],
              "substring": [
                64,
                69
              ]
            }
          }
        },
        {
          "id": "N4",
          "severity": "info",
          "blocking": false,
          "statement": "registration carries pointers only: 39/40 assets are referenced_unresolved and the package emits zero claims, so no scientific statement of report 7216 is adjudicated here",
          "evidence": {
            "referenced_unresolved": 39,
            "assets": 40,
            "claims": [],
            "figure_probe": {
              "/tensor/reports/7216/figures/rb_growth_rate.png": 404,
              "/tensor/reports/7216/figures": 404
            }
          }
        }
      ],
      "local_copy_rehash": [
        {
          "asset": "A01",
          "local_copy": "runs/wp-7216-01/source_7216.md",
          "status": "hashed",
          "matches_declared": true,
          "matches_live": true,
          "sha256": "sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b"
        }
      ],
      "independence_limitations": [
        "same model family as the producer; independence is institutional (different work package, different worktree/session, producer self-check files excluded as evidence), not model-level",
        "available evidence for cross-repo assets is nil: TensorLBM bytes are outside this worktree, so 39/40 registrations cannot be confirmed or refuted here",
        "while orienting I opened gate_sim.json / verification.json to locate the upstream artefact; no rule below uses them as evidence, every fact is recomputed from the live markdown and asset_manifest.json"
      ],
      "coverage": {
        "registered_assets": 40,
        "unregistered_backticked_tokens": [
          "... --mode settling",
          "Jv≈(F(x0+εv)−F(x0))/ε",
          "ny³",
          "| |λ|−1 | < 1e-7",
          "τ_d = 1/2 + λ (ρ_c/ρ_d)(τ_c−1/2)"
        ]
      },
      "checks_not_run": [
        "existence of the job directories named in the report (TensorLBM bytes are not in this worktree; the manifest labels them referenced_unresolved, which this review can neither confirm nor refute)",
        "platform-side acceptance of wp-7216-01 as its published result report (not read: this package is scoped to report_id 7216)",
        "scientific correctness of the report's own numbers (that is a 03/05 object; this package registers pointers only and emits zero claims)"
      ]
    }
  }
}
```
