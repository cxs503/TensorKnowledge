# KF-RESULT wp-6506-04

## ① 本工序做了什么

对被审对象 **wp-6506-01（报告 6506 的资产登记）** 做独立审核（`04-independent-review`，lane C）。
审核只读：报告 6506 的 markdown + 上游结构化 KO + 上游台账工件；不看生产者的叙述性解释，
不修改任何上游产物，不把任何结论标成 verified（verification 由平台门计算）。

结论：**verdict = needs-fix，disposition = request-changes**。
报告 6506 的量化面在独立重算下几乎全对（99 项检查 90 通过，24/24 引文逐字可定位），
但被审的资产清单没有 `assets[]` 条目（下游无从挂证据），且「门禁生效」一条在本环境复现失败。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`GET /tensor/reports/6506` 拿 `markdown`，落盘 17412 bytes / 10846 chars，
   重算 `sha256=1954…4877c`，与契约 `input.source_hash` 逐字节一致（H1/H2 通过）。
2. **取上游 KO**：按 `scenario_key=P34-N7` 枚举到恰好两条记录（6506 原文 + 14673 = wp-6506-01），
   只解析 14673 的 json 结果块（`scripts/kf_extract_result_block.py`），不取叙述。
3. **取上游台账**：从 TensorPlatform 生产者提交 `2fe7f597f` 逐字节复制
   `artifacts/m5496/*.json`（9 个，sha256 记入 `review_evidence.json`）——报告 §3 的每个数字都源自这些文件。
4. **独立重算**（不采信台账自带的汇总字段）：按 `criteria[]` 自行分组累加逐门/逐判据 kill 数、
   M1 按 eps 统计、负控与 survivor 集合、AST 两轮、测试批次、域词扫描、C11 两份门禁台账。
5. **复现**：在 TensorPlatform 检出上跑 `tests/test_criteria_mutation.py`、
   `backend/tests/test_paper_traceability_gate_kills_v3.py`，以及报告附录/CI 的 `--noconftest` 命令；
   用 `git ls-tree/show` 核对报告引用文件在生产者提交与 HEAD 上的存在性。
6. **产物**：`work/wp-6506-04/` 下复算脚本 + 证据 JSON + 上游台账副本；本目录下 review_report.json + 图。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-6506-04/review_report.json` | 审核结论信封（package_id/task_type/report_id/provenance/outputs），内含 verdict、7 条 findings、14 条已核数字、overstated_claims、review_event |
| `work/wp-6506-04/verify_wp6506_04.py` | 一键复算器：hash/quote/arithmetic/replay 四类共 99 项检查 |
| `work/wp-6506-04/review_evidence.json` | 99 项检查的期望/实测/结论/证据路径；90 pass / 7 fail / 2 unknown |
| `work/wp-6506-04/upstream_artifacts/*.json` | 上游台账逐字节副本（9 个，含 sha256），复算的可追溯底座 |
| `work/wp-6506-04/upstream_wp-6506-01.result.json` | 上游 KO（report 14673）的唯一 json 块 + 其 markdown sha256 |
| `docs/kf/wp-6506-04/figures/fig1_claimed_vs_recomputed.png` | 图 1：逐门印刷值 vs 重算值 + 检查面通过率 |

## ④ 证据定位表（claim/字段 → 原文逐字引文）

| 审核断言 | 原文逐字引文 | 独立核验结果 |
|---|---|---|
| 台账规模 12 判据/66 变异体 | `| 台账判据数 | 12 条（含 1 条负控），变异体 66 个 |` | 重算 12/66 ✓ |
| 逐门 kill rate | `| PAPER-TRACE | 3 | 11/18 | 61.1% | ⚠️ |` | 重算 11/18 = 61.1% ✓ |
| 同上（弱门） | `| REPORT-QUALITY | 3 | 7/12 | 58.3% | ⚠️ |` | 重算 7/12 = 58.3% ✓ |
| 合计 kill | `全部判据合计 killed 47/66 = 71.2%` | 重算 47/66 = 71.21% ✓ |
| 扣负控 | `扣除负控后 79.7%` | 重算 47/59 = 79.66% ✓ |
| M1 单调性 | `ε=1%→3 个、3%→3 个、15%→5 个` | 重算 [3,3,5]，违例 0 ✓ |
| 负控 | `且被标为 UNFALSIFIABLE（清单：NEG-TAUTOLOGY）` | 重算 0/7、0/5 类 ✓ |
| AST 现状 | `| 现状 | +51 条杀手测试（含本单 12 条 v3） | 186 | 182 | **97.8%** |` | 重算 182/186 = 97.85% ✓ |
| 残留 survivor | `残留 survivor 4 个：binop_swap[5], binop_swap[6], return_empty[0], return_empty[1]` | 台账 survivors 逐一相符 ✓ |
| 测试批次 | `223 passed / 0 failed / 1 skipped` | test_runs 223/0/1，且 51+172=223 ✓ |
| 域词扫描 | `` `domain_leak_scan.py` 扫 3 个新改文件 / 37 域词条 → 命中 0 `` | 3/37/0 ✓ |
| **C11 门禁生效** | `负控 spec（无 killer test）→ exit 2 `NO_KILLER_TEST`；正控 spec → exit 0，killer 破坏性验证 bites=True` | 台账 ✓，**但本环境用例复现失败 → F2** |
| **IEND 严格度** | `必须以带 CRC 的 IEND 块收尾` | 实现只查「IEND 在流里」→ **F5 轻微夸大** |
| **§⑥ 门槛** | `判据 ≥168/186（90.0%）` | 真值 90.32% → **F4** |
| 诚实申报 | `未跑仓内数万条全量用例` | 与 test_runs.json 只含 2 个批次一致 ✓ |

完整 24 条引文逐字定位见 `review_evidence.json` 的 `kind="quote"` 检查（24/24 pass）。

## ⑤ 注意点与局限

1. **F2 的环境边界**：失败用例在本机（Python 3.11 + pytest 9.2.0）复现；报告时点的 pytest 版本未记录，
   故只断言「本环境可复现 + 代码层 exit 码混用是环境无关的假放行路径」，不断言报告时点即错。
2. **F3 是状态漂移不是造假**：报告的所有数字在生产者提交 `2fe7f597f` 上逐项复现；
   到当前 HEAD `34c9108ca` 时 `tests/test_report_ownership.py` 与 `artifacts/m5496/*` 已不在树里，
   因此「复算入口」在 main 上不可解析（与本仓历史上多次 push-merge 丢文件的模式一致）。
3. **未跑项**：未复跑 `tests/test_report_ownership.py`（HEAD 不存在；生产者提交上 def test_ = 18，
   报告的「21 条」需参数化展开，未实测）；未复跑 223 条完整批次；未校验 4 张 PNG 的像素/图注语义。
4. **审核不做验证**：本审核的 pass/fail 只表示「报表数字 == 台账重算数字」，
   不表示这些数字本身在科学上成立；`verified` 由平台门算，本单不写。
5. **零手抄**：本报告所有数字均由 `verify_wp6506_04.py` 从台账 JSON 重算后写入
   `review_evidence.json`，再由此脚本注入正文；引文一律来自原文逐字子串。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结论 | 依据 |
|---|---|---|
| `valid_json` | ✅ | 结果块经 `json.loads` 通过；本文件正文只有一个 json 代码块 |
| `schema_pass` | ✅ | 信封过 `schemas/kf_result.v1.schema.json`；内嵌 review_event 过 `schemas/review-event.schema.json`（本脚本内 assert） |
| `reviewer_independent` | ✅ | 审核者 `agent/m15845` ≠ 生产者 `tp-agent`(m5496)；输入仅原文+上游 KO+台账；未读生产者解释 |
| `upstream_packages_completed` | ✅ | `scenario_key=P34-N7` 只剩两条：原文 6506 + 上游 wp-6506-01(report 14673, task_type=01-asset-registration, emitted 2026-11-12T01:26:04Z) |
| `do_not_mark_claims_as_verified` | ✅ | 全文只出现 verdict/disposition 与 pass/fail 比对，无 verified 标注 |
| `judge_semantic_fidelity` | ✅（判 needs-fix） | 90/99 检查通过；3 条夸大/口径问题 + 上游清单缺条目 → request-changes |

诚实声明：**未通过项 7 条全部如实列出（F1–F7），没有把 needs-fix 粉饰成 pass**；
其中 F2/F3 的失败只在特定环境/树上复现，已在 ⑤ 限定范围。

## 附录：复算入口（commit 锁定）

```bash
# 1) 取原文 + 重算 sha256（需 TENSOR_AGENT_USER/PASS）
python3 scripts/fetch_report_6506.py
# 2) 取上游 KO（report 14673）的唯一 json 块
python3 scripts/kf_extract_result_block.py --report-id 14673     --out work/wp-6506-04/upstream_wp-6506-01.result.json
# 3) 复算 99 项检查（需要 TensorPlatform 检出；--run-tests 会重跑 pytest）
python3 work/wp-6506-04/verify_wp6506_04.py     --tp-repo /root/tp-agent/work/m12407 --tp-commit 2fe7f597f --run-tests
# 4) 出图 + 组装本报告 + schema 自检（不发布）
python3 work/wp-6506-04/publish_wp6506_04.py --no-post
```

```json
{
 "package_id": "wp-6506-04",
 "task_type": "04-independent-review",
 "report_id": "6506",
 "provenance": {
  "source_hash": "sha256:195447357f5099ba51d2931c4daff233b23098fee7bdf8f53a1569b060f4877c",
  "source_field": "markdown",
  "producer": "wp-6506-04 reviewer (agent, mission 15845, branch agent/m15845)",
  "emitted_at": "2026-11-12T02:56:39Z",
  "notes": "Independent review of wp-6506-01 (asset registration for report 6506). Review input = report 6506 markdown + upstream structured KO only; the producer's narrative explanation was not consulted as evidence. All numbers in this review were recomputed from upstream ledger artifacts (TensorPlatform@2fe7f597f:artifacts/m5496/*.json) by work/wp-6506-04/verify_wp6506_04.py; the reviewer does not mark anything verified."
 },
 "outputs": {
  "review_report.json": {
   "reviewed_package": "wp-6506-01",
   "reviewed_task_type": "01-asset-registration",
   "reviewed_report_id": "6506",
   "verdict": "needs-fix",
   "disposition": "request-changes",
   "verdict_basis": "报告 6506 的核心数字（12 判据 / 66 变异体 / 47 killed / 逐门与逐判据 kill rate / M1 单调性 [3,3,5] / 负控 0/7 / 92→182 of 186 / 223-0-1 测试批次 / 3 文件 37 词条命中 0）在独立重算下逐项成立，24 条引文全部逐字可定位；但被审对象 wp-6506-01 的 asset_manifest 只有计数与类型直方图、没有任何 asset 条目/locator/sha256，无法承载下游证据解析；另有一条与门禁有效性直接相关的用例在 TensorPlatform 检出上复现失败（test_gate_rejects_toothless_killer），故判 needs-fix 而非 pass。",
   "independence": {
    "reviewer_identity": "agent/m15845（与本报告生产者 agent/m5496 不同任务、不同工作树、不同分支）",
    "producer_identity": "tp-agent（report 6506 provenance.producer；wp-6506-01 provenance.producer）",
    "inputs_used": [
     "report 6506 markdown（sha256:195447357f...4877c，10846 chars，平台 API GET /tensor/reports/6506）",
     "wp-6506-01 structured result block（report 14673，仅 json 代码块，不含叙述）",
     "TensorPlatform@2fe7f597f 的 artifacts/m5496/*.json 台账（9 个文件，逐字节复制并记 sha256）"
    ],
    "inputs_withheld": [
     "生产者解释/自评/口径说明（reviewer_context_excludes_producer_explanation=true）",
     "其它 report_id 的正文（只按 scenario_key=P34-N7 枚举 id 与标题以确认上游包存在）"
    ],
    "self_review_check": "审核者与生产者身份不同；本审核不修改任何上游产物，未把任何结论标为 verified"
   },
   "scope_checked": [
    "source_hash 与 chars 与契约一致（字节级）",
    "24 条引文逐字子串可定位（search 定位，非记忆重述）",
    "§3.1/§3.2/§3.4/§⑥ 全部比值由台账 JSON 重新累加比对印刷值",
    "§3.3 点名的 12 个最弱 mutant 逐条落到 survivor 集合，且非负控 survivor 总数 = 12（清单完备）",
    "C11 门禁台账（负控 exit 2 / 正控 exit 0 & bites）与 pytest 复现",
    "上游 wp-6506-01 asset_manifest 的结构完备性",
    "报告引用文件在 TensorPlatform 生产者提交与当前 HEAD 上的存在性"
   ],
   "not_run": [
    "未在报告生产者当时的 pytest 版本上复跑 tests/test_criteria_mutation.py（本机 pytest 9.2.0 下 1 failed / 29 passed；环境差异未消除，故该失败记为「本环境可复现」，不断言为报告时点即错）",
    "未复跑 tests/test_report_ownership.py（该文件在当前 HEAD 不存在；生产者提交上 def test_ 计数为 18，报告的「21 条」需参数化展开才能成立，未实测）",
    "未复跑 223 条批次（批次的精确文件集合只存在于台账 test_runs.json 的命令行文本）",
    "未校验 4 张 PNG 的像素内容与图注语义（只校验文件名与 tracked 状态）",
    "未审计 P34-N7 之外的平台代码（无授权、且与单内范围无关）"
   ],
   "counts": {
    "checks_total": 99,
    "checks_pass": 90,
    "checks_fail": 7,
    "checks_unknown": 2,
    "quotes_verified": 24,
    "quotes_total": 24,
    "arithmetic_verified": 59,
    "arithmetic_total": 61
   },
   "findings": [
    {
     "finding_id": "F1",
     "severity": "major",
     "blocking": false,
     "title": "被审对象 wp-6506-01 的 asset_manifest 没有任何 asset 条目（只有计数与类型直方图）",
     "detail": "上游 outputs['asset_manifest.json'] 的键只有 report_id/source_uri/source_field/source_hash/title/scenario_key/chars/artifact_count(17)/claim_count(0)/artifact_types{script:7,data:2,test:2,source:3,figure:4}。没有 assets[] 数组，因此没有逐项 locator（章节/偏移）、没有类型类别（asset_class）、没有 resolution 与 sha256。下游工序（03 抽取、05 综合）无法据此把任何结论挂到可解析的证据上，也无法复算某个工件是否真被改动。",
     "evidence": [
      "check U3 = fail（observed: keys=artifact_count,artifact_types,chars,claim_count,report_id,scenario_key,source_field,source_hash,source_uri,title）",
      "check U4 = unknown（原文可枚举 16 个互不相同的路径样式记号；asset_count=17 与之相容，但清单未列条目故不可逐条核对）",
      "本地仓 schemas/asset_manifest.v1.schema.json 要求 assets[] 每项含 asset_id/asset_class/label/in_report_section/locator/resolution/resolution_check/note，并要求 integrity{quote_uniqueness,hash_recomputed_locally,hash_matches_contract}"
     ],
     "affected_scope": [
      "wp-6506-01",
      "下游 03/05 工序的证据解析面"
     ],
     "remediation": "把 17 个资产逐条登记：asset_id/asset_class/label/in_report_section（引原文小节标题）/locator（path#pointer 或 quote 偏移）/resolution（tracked@commit 或 untracked）/sha256；补 integrity 三字段；对 4 张图给出可复算的 sha256。"
    },
    {
     "finding_id": "F2",
     "severity": "major",
     "blocking": false,
     "title": "C11「门禁生效」在本环境不可复现：killer 判据把「任何非 0 退出」当成「咬了」",
     "detail": "tools/audit/criteria_mutation.py 的 killer_test_bites() 用 returncode != 0 判定 bites。收集错误（pytest exit 2/4）、用法错误、超时以外的内部错误都会被记成 bites=True，于是「杀手测试根本跑不起来」与「杀手测试真咬」不可区分——这正是门禁要防的假放行。复现：tests/test_criteria_mutation.py 在 TensorPlatform 检出上 1 failed, 29 passed，失败用例 test_gate_rejects_toothless_killer 断言的正是该行为（其 fake killer 指向的节点在 --noconftest 下 import 失败 → exit 非 0 → 被判 bites → accepted=True）。同一 --noconftest 也是报告附录与 CI 里的复跑命令，在本环境收集失败（ModuleNotFoundError: No module named 'tools.audit'）。",
     "evidence": [
      "check R5 = fail（1 failed, 29 passed）",
      "check R6 = fail（FAILED tests/test_criteria_mutation.py::test_gate_rejects_toothless_killer）",
      "check R7 = fail（`pytest tests/test_criteria_mutation.py -q --noconftest` 非 0 退出）",
      "check A21 = pass（台账 gate_c11_positive.json 里 killer_checks 的 exit 均为 1，即当时确是真红；故本条不是「报告造假」，而是「结论未在当前树复现」）",
      "check A22 = pass（把台账的 exit 分布与「必须是 1」的判据分开核对）"
     ],
     "affected_scope": [
      "PR 准入门禁（.github/workflows/criteria-gate.yml）",
      "报告 §3.5 C11 一行的可复现性"
     ],
     "remediation": "killer_test_bites 收窄 bites 的判据：exit 必须为 1（pytest tests failed），并把 exit∈{2,3,4,5} 记为 ERROR/NOT_RUN 而非 bites；同时在 killer 子进程里显式补 PYTHONPATH=<repo> 或使用与正式跑测一致的 conftest，消除 --noconftest 造成的 import 断链。"
    },
    {
     "finding_id": "F3",
     "severity": "major",
     "blocking": false,
     "title": "报告引用的复算入口在当前 TensorPlatform main 上不可解析（只在生产者提交里可复现）",
     "detail": "报告 §1 与附录把 tests/test_report_ownership.py 与 artifacts/m5496/*（criteria_mutation_ledger.json、audit_c6/c7、test_runs.json、probe_kill.py、make_figures.py、make_report_payload.py、pr_new_criteria_*.json）写成「复算入口」。在生产者提交 2fe7f597f 上这些文件都在（artifacts/m5496 入库 12 个）；在当前检出 HEAD 34c9108ca 上 tests/test_report_ownership.py 不存在、artifacts/m5496 入库 0 个（仅 docs/m5496/REPORT.md 与 4 张图）。因此报告的数字在 main 上无法按报告给的命令复算，只能回溯到具体 commit。",
     "evidence": [
      "check R1 = pass（2fe7f597f 上 tests/test_report_ownership.py 存在）",
      "check R2 = pass（2fe7f597f 上 artifacts/m5496 入库 12 个）",
      "check R4 = fail（HEAD 上该测试文件不存在；artifacts/m5496 入库 0 个；HEAD=34c9108ca）",
      "check R3 = unknown（2fe7f597f 上该文件 def test_ 18 个，报告的「21 条」需参数化展开，未实测）"
     ],
     "affected_scope": [
      "报告 6506 的可复现性",
      "CI 门禁 criteria-gate.yml 的 paths 触发与跑测步骤（引用了已不存在的测试文件）"
     ],
     "remediation": "报告里改用 commit 锁定复算入口（tensor://repo/TensorPlatform@2fe7f597f:artifacts/m5496/...）；或在 main 上补回台账与测试文件，并让 CI 的 paths/步骤与实际存在的文件对齐。"
    },
    {
     "finding_id": "F4",
     "severity": "minor",
     "blocking": false,
     "title": "§⑥ 误差表两处算术口径混用（90.0% 与 7.8pp）",
     "detail": "「判据 ≥168/186（90.0%）」的真值是 90.32%；同表下一行「余量 7.8pp」= 97.85-90.0 用的是名义 90.0%，若按表中写明的 168/186 门槛算，余量应为 (182-168)/186 = 7.53pp。两个基准混用，方向不影响结论（超门槛），但误差表述不唯一。",
     "evidence": [
      "check A17 = fail（印刷 90.0% vs 重算 90.32%）",
      "check A17b = fail（印刷 7.8pp vs 重算 7.53pp）"
     ],
     "affected_scope": [
      "报告 §⑥ 误差判定表"
     ],
     "remediation": "统一写成 168/186 = 90.32%，余量 14/186 = 7.53pp。"
    },
    {
     "finding_id": "F5",
     "severity": "minor",
     "blocking": false,
     "title": "§②(b) 对配图门的严格度有轻微夸大：实现是「IEND 出现在流里」而非「以 IEND 收尾」",
     "detail": "报告写「必须以带 CRC 的 IEND 块收尾」。backend/services/report_ownership.py 的实现是 if not raw.endswith(PNG_IEND_CHUNK): if PNG_IEND_CHUNK not in raw: raise ...，即 IEND 之后跟垃圾字节能通过；该实现的注释自称「不宽容后置垃圾」，与代码行为相反。截断（缺 IEND）确实被抓，报告的核心断言成立，但「收尾」二字比实现强。",
     "evidence": [
      "check Q04 = pass（引文逐字可定位：必须以带 CRC 的 IEND 块收尾）",
      "代码定位：backend/services/report_ownership.py（HEAD）validate_png_payload 的 IEND 分支"
     ],
     "scope_note": "代码核对针对当前 HEAD 版本；未取生产者提交版本的该函数做逐行 diff",
     "affected_scope": [
      "报告 §②(b) 表述",
      "配图门 RO-PNG-IEND 的语义边界"
     ],
     "remediation": "报告改为「必须含带 CRC 的 IEND 块；当前实现对 IEND 之后的多余字节宽容」，或实现改为 endswith 严格收尾并补一条 trailing-garbage 用例。"
    },
    {
     "finding_id": "F6",
     "severity": "informational",
     "blocking": false,
     "title": "C11 正控台账里 selected 出现重复 cid",
     "detail": "gate_c11_positive.json 的 selected 为 ['RO-PNG-MAGIC','RO-PNG-MAGIC']，同一 cid 被选两次（pr_gate 未对 selected 去重）。不影响 exit_code 与 bites 判定，但会让 killer 检查次数翻倍、台账可读性下降。",
     "evidence": [
      "check A21 读取的 gate_c11_positive.json#selected"
     ],
     "affected_scope": [
      "准入台账可读性"
     ],
     "remediation": "pr_gate 里对 selected 去重（保持首现顺序）。"
    },
    {
     "finding_id": "F7",
     "severity": "informational",
     "blocking": false,
     "title": "「新增 21 条测试」的条数口径未在报告中说明",
     "detail": "生产者提交 2fe7f597f 上 tests/test_report_ownership.py 的 def test_ 计数为 18；21 只能由 parametrize 展开得到（本审核未实测）。建议在报告里写明「21 条 = 18 个测试函数 + 3 个参数化展开」。",
     "evidence": [
      "check R3 = unknown（git show 2fe7f597f:tests/test_report_ownership.py | grep -c 'def test_' = 18）"
     ],
     "affected_scope": [
      "报告 §1 参数表"
     ],
     "remediation": "补口径或在台账 test_runs.json 里记 collected 数。"
    }
   ],
   "verified_numbers": [
    {
     "value": "12 条判据（含 1 条负控）/ 66 变异体",
     "recomputed_from": "criteria_mutation_ledger.json#criteria",
     "match": true
    },
    {
     "value": "合计 47/66 = 71.2%（重算 71.21%）",
     "recomputed_from": "sum(criteria[].killed)/sum(total)",
     "match": true
    },
    {
     "value": "扣负控 47/59 = 79.7%（重算 79.66%）",
     "recomputed_from": "47/(66-7)",
     "match": true
    },
    {
     "value": "PAPER-TRACE 11/18 = 61.1% / REPORT-QUALITY 7/12 = 58.3% / REPORT-OWNERSHIP 15/15 / CLIENT-PAYLOAD 14/14 / 负控 0/7",
     "recomputed_from": "自行按 gate 分组累加（不采用台账自带 per_gate）",
     "match": true
    },
    {
     "value": "逐判据 12 行 killed/total 与 kill rate 印刷值",
     "recomputed_from": "criteria[].killed/total",
     "match": true
    },
    {
     "value": "M1 单调性 [3,3,5]，违例 0",
     "recomputed_from": "criteria[].mutants[class=M1].eps/killed",
     "match": true
    },
    {
     "value": "负控 killed 0/7、killed 类 0/5、UNFALSIFIABLE 清单 [NEG-TAUTOLOGY]",
     "recomputed_from": "criteria[control]",
     "match": true
    },
    {
     "value": "§3.3 点名 12 个最弱 mutant 全部真在 survivor 集；非负控 survivor 合计 12 = 清单行数",
     "recomputed_from": "criteria[].survivors[].label",
     "match": true
    },
    {
     "value": "AST 基线 92/186 = 49.46%（印 49.5%）/ 现状 182/186 = 97.85%（印 97.8%）",
     "recomputed_from": "audit_c6_baseline.json / audit_c7_v3.json",
     "match": true
    },
    {
     "value": "残留 survivor 4 个且名字逐一相符",
     "recomputed_from": "audit_c7_v3.json#survivors[].name",
     "match": true
    },
    {
     "value": "C5 223 passed / 0 failed / 1 skipped（且 51+172=223）",
     "recomputed_from": "test_runs.json#runs",
     "match": true
    },
    {
     "value": "C12 3 文件 / 37 域词条 / 命中 0",
     "recomputed_from": "domain_leak_scan.json",
     "match": true
    },
    {
     "value": "C11 负控 exit 2 NO_KILLER_TEST / 正控 exit 0 且 bites=True（killer exit 均为 1）",
     "recomputed_from": "gate_c11_negative.json / gate_c11_positive.json",
     "match": true
    },
    {
     "value": "source_hash 与 chars(10846)",
     "recomputed_from": "平台 markdown 字节重算",
     "match": true
    }
   ],
   "overstated_claims": [
    {
     "claim": "C11 门禁生效 … killer 破坏性验证 bites=True｜通过",
     "issue": "本环境不可复现：tests/test_criteria_mutation.py 1 failed/29 passed；且 gate 把任意非 0 退出当 bites，存在假放行路径（F2）"
    },
    {
     "claim": "必须（PNG）以带 CRC 的 IEND 块收尾",
     "issue": "实现只要求 IEND 出现在流里，尾随垃圾可通过（F5）"
    },
    {
     "claim": "判据 ≥168/186（90.0%）/ 余量 7.8pp",
     "issue": "168/186 = 90.32%；按该门槛余量应为 7.53pp（F4）"
    }
   ],
   "conditions": [
    "wp-6506-01 重发 asset_manifest：补 assets[]（逐项 locator + sha256）与 integrity 三字段后，再由下一轮独立审核裁定 pass",
    "C11 的 bites 判据收窄到 exit==1 并修掉 --noconftest 的 import 断链，重跑门禁用例全绿后重述 C11",
    "报告里的复算入口改为 commit 锁定形式，或在 main 上补回台账与测试文件"
   ],
   "checks_artifact": {
    "verifier": "work/wp-6506-04/verify_wp6506_04.py",
    "evidence_json": "work/wp-6506-04/review_evidence.json",
    "untracked_copies_of_upstream_ledgers": "work/wp-6506-04/upstream_artifacts/*.json（逐字节复制，sha256 记在 review_evidence.json#upstream_artifacts.sha256）"
   },
   "review_events": [
    {
     "id": "tkr:wp-6506-04:independent-review",
     "object_ref": "wp-6506-01",
     "object_version": "report-14673@2026-11-12T01:26:04Z",
     "decision": "request-changes",
     "reviewer": {
      "id": "agent/m15845",
      "reviewer_type": "agent",
      "role": "red-team-reviewer"
     },
     "reviewed_at": "2026-11-12T02:56:39Z",
     "policy_version": "wp-6506-04.c1.0",
     "rationale": "报告 6506 的量化部分独立重算逐项成立（90/99 检查通过、24/24 引文逐字可定位），但被审资产清单缺 assets[] 条目、且门禁有效性用例在本环境复现失败，故 request-changes。",
     "findings": [
      {
       "severity": "major",
       "finding": "F1 asset_manifest 无 assets[] 条目（仅计数与类型直方图），下游无法挂证据"
      },
      {
       "severity": "major",
       "finding": "F2 killer_test_bites 把任意非 0 退出当 bites；test_gate_rejects_toothless_killer 复现失败"
      },
      {
       "severity": "major",
       "finding": "F3 报告复算入口在 main HEAD 不可解析（仅生产者提交可复现）"
      },
      {
       "severity": "minor",
       "finding": "F4 §⑥ 90.0% / 7.8pp 两处口径混用"
      },
      {
       "severity": "minor",
       "finding": "F5 PNG IEND「收尾」表述强于实现"
      },
      {
       "severity": "informational",
       "finding": "F6 gate_c11_positive.selected 重复 cid"
      },
      {
       "severity": "informational",
       "finding": "F7 「21 条测试」条数口径未说明"
      }
     ],
     "conditions": [
      "wp-6506-01 重发含 assets[] 与 integrity 的 asset_manifest",
      "修 killer exit 判据与 --noconftest 断链后重跑门禁用例全绿",
      "复算入口 commit 锁定或 main 补回台账"
     ]
    }
   ]
  }
 }
}
```
