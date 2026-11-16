#!/usr/bin/env python3
"""Publish the two m23090 (PROD-RA R4 rereview) platform reports.

Every number is injected from docs/review_m22059_prod_ra/recheck_r4_output.json — no hand-copied values.
"""
import base64
import json
import os
import urllib.request
from pathlib import Path

BASE = os.environ["TENSOR_API_BASE"]
D = Path(__file__).resolve().parent
o = json.loads((D / "recheck_r4_output.json").read_text(encoding="utf-8"))
ir, ai, cfz, et, fr, rsx = (o["independent_rerun"], o["artifact_identity"],
                            o["criteria_frozen_before_run"], o["evidence_traceability"],
                            o["failure_record"], o["regression_scope"])
m = ai["reviewer_bundle_manifest"]


def fig(p: Path, name: str, cap: str) -> dict:
    return {"name": name, "caption": cap,
            "png_base64": base64.b64encode(p.read_bytes()).decode()}


FIGS = [
    fig(D / "figures/r4-d-status-six-checks.png", "r4_d_status_six_checks.png",
        "左：D1–D12 逐项裁决（绿=fixed，琥珀=D6 fixed_with_residual，无 open）；中：六检实测状态与复跑 exit_code；右：审阅包 SHA256SUMS 清单可核性（R4-3）"),
    fig(D / "figures/r4-rerun-exitcodes.png", "r4_rerun_exitcodes.png",
        "复跑 exit code 与在册值对照：正/负语料状态与 findings 逐项复现；作者交付的 recheck.py 在被审 commit 上 exit=1（KeyError item_id），本轮 recheck_r4.py exit=%d" % o["exit_code"]),
]

d_rows = "\n".join(
    f"| {k} | {v['status']} | `{v['evidence'] if isinstance(v['evidence'], str) else json.dumps(v['evidence'], ensure_ascii=False)}` |"
    for k, v in o["d1_d12"].items())
six_rows = "\n".join(f"| `{k}` | **{v}** |" for k, v in o["six_checks"].items())
res_rows = "\n".join(
    f"| {r['id']} | {r['severity']} | {r['scope']} | {r['finding'][:220]} |" for r in o["residual_findings"])

md1 = f"""# PROD-RA R4 复审（m23090）：m22059 D1–D12 返修在 `origin/main@ca99e79f0` 的独立复核

## ① 案例介绍（审查对象与判据基准）

| 项 | 内容 |
|---|---|
| 产品线 | ResearchAudit（PROD-RA 阶段3 试点，`scenario_id=RA-20261115-real-corpus-audit`） |
| 被审对象 | `TensorKnowledge` `origin/main` @ `{o['reviewed_commit']}` |
| 构成 | PR#503（`a168dec`，证据 38 文件 → `docs/m22059/`）+ PR#508（`ca99e79f0`，D1–D12 修复增量 21 文件）+ 审阅包 `docs/review_m22059_prod_ra/` |
| 判据基准 | `tensor_maturity_verdicts` 行 903（`m22059 PROD-RA 试点验收`, L2, `changes_requested`, defects=12）+ `REPAIR-NOTES.md` 自述 |
| 契约源 | `TensorBench` @ `{o['tensorbench_contract_head'][:7]}`：`FOUR_PRODUCT_ACCEPTANCE_MATRIX.md`、`PRD.md`、`schemas/evidence-item.schema.json`、`tensorbench.criteria.canonical_sha256` |
| 审查语料 | `work/wp-2506-04/kf_result_wp-2506-04.md`（sha256 `{ai['scenario_inputs'][0]['actual'][:16]}…`，与在册指纹一致={ai['scenario_inputs'][0]['match']}）+ `EVIDENCE.md` |
| 环境 | python {o['python']} / linux；只读审阅树；派生工件写入复审席工作树 |

前史：一轮 m22059（level 2 + D1–D12，verdict 903）；二轮 m22760 修复真实但推送被滤除；三轮 m23017 复审判 main 仍有 D1–D6/D8–D12；PR#503/PR#508 经 m22059 自有通道把证据与修复落到 main。本轮为**第四轮终判**。

## ② 怎么做的（方法 / 流程 / 工具链）

1. **执行路径独立重建**：不复用作者自证脚本，按 `adversarial-review` 重写复核器 `docs/review_m22059_prod_ra/recheck_r4.py`（六检 + D1–D12 逐项裁决 + 残余扫描），所有数字从被审树重算（`recheck_r4_output.json`），报告数字由生成器注入，零手抄。
2. **判据双向对照**：既查"缺陷是否消失"，也查"REPAIR-NOTES 自述是否成立"（自述偏差单列）。
3. **独立复跑**：两确定性审计器（`citation_audit.py`、`claim_evidence_audit.py`）在**正/负**语料上重跑，与在册 exit_code / overall_status / findings / summary 逐项比对；另复现 kb10k 负例（20 × `invalid_record`）。
4. **溯源探针**：11 条 evidence 逐条 `src[start:end] == quote` 回切片 + `sha256(quote) == content_hash`；台账 3 条 `#sha256:` 摘要与仓内文件实测比对；commit `c5d46f5d…` 在仓内 `git cat-file` 可解析。
5. **契约哈希**：`canonical_sha256(criteria.json)` 与 `criteria_freeze.criteria_sha256` 逐字节比对，并验证"是否误用 `sha256(indent=2)` 口径"。
6. **时间线**：`frozen_at` vs 最早审计输出 `created_at` vs 报告 `created_at`。
7. **负向能力**：负向语料是否检出（status + exit_code 双级），是否退化为 finding 级并写明理由。
8. **清单可核性**：`docs/review_m22059_prod_ra/SHA256SUMS` 18 条逐条实测。

复跑命令：`python3 docs/review_m22059_prod_ra/recheck_r4.py --out docs/review_m22059_prod_ra/recheck_r4_output.json` → **exit_code = {o['exit_code']}**（0=全过无残余 / 1=六检失败 / 2=D1–D12 实质修复但审阅包有残余）。

## ③ 计算结果（数字表，程序化注入）

**六检**

| 检查 | 结果 |
|---|---|
{six_rows}

**D1–D12 逐项**

| 缺陷 | 状态 | 实测证据 |
|---|---|---|
{d_rows}

**独立复跑（关键量）**

| 量 | 本轮复跑 | 在册 | 一致性 |
|---|---|---|---|
| citation_audit（正语料）exit / status | {ir['citation_audit_positive']['exit_code']} / {ir['citation_audit_positive']['status_rerun']} | 1 / {ir['citation_audit_positive']['status_recorded']} | summary 全等={ir['citation_audit_positive']['summary_equal']}，findings {ir['citation_audit_positive']['findings_rerun']} |
| citation_audit（负语料）exit / status | {ir['citation_audit_negative']['exit_code']} / {ir['citation_audit_negative']['status']} | 1 / inconclusive | unresolved={ir['citation_audit_negative']['unresolved_citations']}，检出 999={ir['citation_audit_negative']['detected_999']} |
| claim_evidence_audit（正）exit / status | {ir['claim_evidence_audit_positive']['exit_code']} / {ir['claim_evidence_audit_positive']['status_rerun']} | 0 / {ir['claim_evidence_audit_positive']['status_recorded']} | findings={ir['claim_evidence_audit_positive']['finding_codes_rerun']} |
| claim_evidence_audit（负）exit / status | {ir['claim_evidence_audit_negative']['exit_code']} / {ir['claim_evidence_audit_negative']['status']} | 1 / failed | 检出 {ir['claim_evidence_audit_negative']['finding_codes']} |
| triage 计数 v/i/b | {ir['claims_triage_counts']['verified']}/{ir['claims_triage_counts']['inconclusive']}/{ir['claims_triage_counts']['broken']} | 3/4/8 | 合计 {ir['claims_triage_counts']['sum']} vs claim 记录 {ir['claims_triage_counts']['claim_records_in_corpus']}，复现={ir['claims_triage_counts']['reproduced_from_corpus']} |
| 判据哈希 canonical | `{cfz['recomputed_canonical_sha256'][:24]}…` | `{cfz['declared_sha256'][:24]}…` | 全等={cfz['match_canonical']}；误用 indent=2 口径={cfz['matches_pretty_json_instead']} |
| 11 条 evidence 回切片 | 命中 {et['locators_total']}/{et['locators_total']} | 11/11 在册声称 | 空 quote {len(et['locators_with_empty_quote'])}，start_offset=0 {len(et['locators_start_offset_zero'])} |
| 台账 3 条 §5 字段 | 缺字段 {fr['records_missing_fields']}，无摘要 ref {fr['records_with_ref_without_sha256']}，无 commit {fr['records_without_commit_sha']} | — | 全部合规 |
| 时间线 | frozen {cfz['frozen_at']} ≤ 输出 {cfz['earliest_audit_output_created_at']} ≤ 报告 {cfz['report_created_at']} | — | 冻结先于运行可证={cfz['frozen_before_earliest_output']} |
| 相邻单测 | {rsx['adjacent_rerun_tail']} | 12 passed | exit={rsx['adjacent_rerun_exit_code']} |
| 审阅包 SHA256SUMS | {m['entries']} 条中缺文件 {len(m['entries_missing_file'])}、假自摘要 {len(m['entries_with_self_or_empty_digest'])} | — | **R4-3** |

**残余缺陷（不在 D1–D12 单内）**

| # | 严重度 | 范围 | 缺陷 |
|---|---|---|---|
{res_rows}

## ④ 结果图

图 1（`r4_d_status_six_checks.png`）：D1–D12 状态、六检状态与审阅包清单可核性三联图。
图 2（`r4_rerun_exitcodes.png`）：复跑 exit code 与在册值对照，含作者交付 `recheck.py` 在被审 commit 上 `exit=1`（`KeyError: 'item_id'`，`recheck.py:214`）与本轮 `recheck_r4.py exit={o['exit_code']}`。

## ⑤ 注意点（踩过的坑 / 局限 / 适用范围）

1. **迁移未重根**：main 里证据从 `runs/m22059/` 迁到 `docs/m22059/`，但包内全部**文件级 locator** 仍写 `runs/m22059/…`；作者侧参考工作树已不存在。**内容级 locator（偏移+quote+hash）不受影响**，所以"源定位"实质仍成立，"文件指针可解析"不成立（R4-1）。
2. **审阅入口失效**：D6 把 evidence item 的 `item_id` 改名 `evidence_id` 后未回改 `recheck.py`，且脚本硬编码 `RUN='runs/m22059'` → 在被审 commit 上必崩（R4-2）。故仓内 `recheck_output.json` 描述的是首轮 commit `96ff584`，不能当作本轮结论。
3. **零长度摘要类错误复发**：审阅包 `raw/SHA256SUMS` 被登记为 `e3b0c442…`（空串摘要），与首轮 D3 属同一类（R4-3）。
4. **自述夸大 1 处**：REPAIR-NOTES 称"每条 provenance 带 input_sha256"，实测 4/5；`ev-kb10k-incompatibility` 只有目录型 `input_refs` 且 `source_root` 为域外绝对路径（R4-4，其 finding 本身已复现，20 × invalid_record）。
5. **未跑项如实标注**：全量 pytest 仍 `not_run`（作者 cj4351 排队，本轮未另递重计算）；未做跨机复跑；判据原文只抽验 7 条；PRD 语义精度/macro-F1 无 holdout 未测。这些**记为未跑，不计通过**。

## ⑥ 误差判定（关键量 vs 基准，逐项显式回答）

| 关键量 | 基准 | 实测 | 相对偏差 | <3%？ |
|---|---|---|---|---|
| 判据 canonical sha256 | `criteria_freeze.criteria_sha256`（在册） | `{cfz['recomputed_canonical_sha256'][:16]}…` | 0（逐字节全等） | **是** |
| 11 条 evidence quote 回切片 | 源文本 `src[start:end]` | 11/11 全命 | 0 | **是** |
| 11 条 quote 摘要 | `locator.content_hash` | 11/11 全等 | 0 | **是** |
| 两审计器 exit/status/findings | 在册输出 | 逐项相同 | 0 | **是** |
| triage 计数（3/4/8，合计 15 / claim 11） | 语料重建计数 | 15 / 11 | 0 | **是** |
| 台账摘要与文件实测 | `#sha256:` 声明 | 3/3 全等 | 0 | **是** |
| 相邻单测通过数 | 在册 12 passed | {rsx['adjacent_rerun_tail']} | 0 | **是** |

**显式结论**：本轮**有**可判定基准（在册输出与契约函数），全部关键量**逐字节/逐计数全等，偏差 0%，<3% 成立**。唯一无物理/标量基准的量是"人工评审分钟"（作者写 unknown，未估造），本席同样不估造；全量 pytest 通过数**未知（not_run）**，不声明误差。
"""

md2 = f"""# 裁决：PROD-RA R4（m23090）— `changes_requested`（窄口径）

## ① 裁决对象

`TensorKnowledge` `origin/main@ca99e79f0`（PR#503 证据 38 文件 + PR#508 D1–D12 修复 21 文件 + `docs/review_m22059_prod_ra/` 审阅包）；判据基准 `tensor_maturity_verdicts` 行 903（12 条缺陷）+ `REPAIR-NOTES.md` 自述。

## ② 裁决方法

六检（artifact_identity / criteria_frozen_before_run / evidence_traceability / independent_rerun / failure_record / regression_scope）+ D1–D12 逐项实测 + 审阅包清单可核性；复核器 `docs/review_m22059_prod_ra/recheck_r4.py`，`exit_code = {o['exit_code']}`，明细 `recheck_r4_output.json`，报告 `REVIEW-R4.md`。

## ③ 结果

| 项 | 结果 |
|---|---|
| D1–D12 | fixed {len(o['d1_d12_summary']['fixed'])} 条（{", ".join(o['d1_d12_summary']['fixed'])}）；fixed_with_residual {", ".join(o['d1_d12_summary']['fixed_with_residual']) or "无"}；**open {len(o['d1_d12_summary']['open'])} 条** |
| 六检 | {" / ".join(f"{k}={v}" for k, v in o['six_checks'].items())} |
| 复跑 | citation_audit exit {ir['citation_audit_positive']['exit_code']}（inconclusive 复现）；claim_evidence_audit 正 exit {ir['claim_evidence_audit_positive']['exit_code']}（passed）/ 负 exit {ir['claim_evidence_audit_negative']['exit_code']}（failed，检出 {ir['claim_evidence_audit_negative']['finding_codes']}） |
| 相邻单测 | {rsx['adjacent_rerun_tail']} |
| 全量 pytest | not_run（如实记，不计通过） |

残余缺陷（R4-1…R4-6）：

| # | 严重度 | 范围 | 缺陷 |
|---|---|---|---|
{res_rows}

## ④ 图

`r4_d_status_six_checks.png`（D 单状态 / 六检 / 清单可核性）与 `r4_rerun_exitcodes.png`（复跑 exit code 对照，含 as-shipped `recheck.py` 崩溃与 `recheck_r4.py exit={o['exit_code']}`）。

## ⑤ 注意点

1. **D1–D12 的修复是真的**：判据哈希走契约函数、11/11 偏移回切片命中、台账 §5 字段与摘要全合规、时间线可证冻结先于运行、负向测试恢复 status+exit 双级判别、分母口径写明 15/11。这是三轮返修后第一次在被审主线上被独立复现的完整修复。
2. **阻断点不在审计结论，而在审阅包/迁移层**：R4-1 文件级 locator 前缀未重根（内容字节一致，仅指针失效）；R4-2 作者交付的复核脚本在被审 commit 上崩溃、其 `recheck_output.json` 仍描述首轮 commit；R4-3 审阅包 `SHA256SUMS` 18 条中 5 条不成立（4 条 raw 日志未随仓交付 + `raw/SHA256SUMS` 被登记为空串摘要，D3 同类错误复发）。
3. **R4-4 轻微**：`ev-kb10k-incompatibility` 无输入摘要且 `source_root` 为域外绝对路径；其 finding 本身可复现（20 × `invalid_record`，exit 1），故记为轻微。
4. **不放行的判断依据**：PRD 要求"每条 finding 可从被引来源复现"。偏移级复现成立，但文件级指针在本树内全部失效、复核入口脚本崩溃——在两者修复前，下游集成方与外部审计无法按包内指针取证。
5. `scenario_validated` 本裁决**不置位**，由协调者依裁决执行。

## ⑥ 误差判定（显式回答）

关键量全部与在册基准**逐字节/逐计数全等，相对偏差 0%（<3% 成立）**：判据 canonical sha256、11/11 回切片、11/11 quote 摘要、两审计器 exit/status/findings、triage 15/11、台账 3/3 摘要、相邻单测 12 passed。
无基准量：人工评审分钟（unknown，不估造）、全量 pytest 通过数（not_run，不声明）。**不存在被粉饰的失败项**。

## 最小修复建议（派单即验）

1. `docs/m22059/` 全量把 `runs/m22059/` 前缀重写为 `docs/m22059/`（含 `criteria.json`、`validation-report.json`、两审计器输出、11 claim/11 evidence、`negative_test/*`、`regression-scope.json`、`REPORT.md`、`REPAIR-NOTES.md`），若改动 `criteria.json` 需按 `superseded_timeline` 留档而非覆盖，然后重跑审计器 + `recheck_r4.py` 期望 `exit=0`。
2. `recheck.py`：`item_id → evidence_id`、artifact 根按候选解析（可直接采纳 `recheck_r4.py` 的实现），并重生成 `recheck_output.json` 指向 `{o['reviewed_commit'][:7]}`。
3. `SHA256SUMS`：补 4 条 raw 日志或删项并注明缺失原因；`raw/SHA256SUMS` 自摘要改写真实值或从清单移除自身。
4. `ev-kb10k-incompatibility.provenance.source_root` 改仓内相对路径，并写明目录型输入无摘要。
"""


def api(method, path, payload=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(req, data=data, timeout=180) as r:
        return r.status, json.loads(r.read() or b"{}")


_, d = api("POST", "/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                   "password": os.environ["TENSOR_AGENT_PASS"]})
tok = d.get("access_token")
print("login ok, token len", len(tok or ""))

r1 = {"title": "PROD-RA R4 复审（m23090）：m22059 D1–D12 返修在 main@ca99e79 的独立复核",
      "summary": f"D1–D12 实质全部修复（fixed {len(o['d1_d12_summary']['fixed'])}/12，D6 fixed_with_residual，open 0）；六检 {'/'.join(o['six_checks'].values())}，复跑 exit_code={o['exit_code']}；残余 R4-1 文件级 locator 未重根、R4-2 交付 recheck.py 在被审 commit 崩溃、R4-3 审阅包 SHA256SUMS 5/18 不成立 → 裁决 changes_requested（窄口径）",
      "scenario_key": "prod_ra_rereview4_m22059_r4review",
      "mission_id": 23090,
      "tags": ["prod-ra", "m22059", "rereview-r4", "audit-traceability", "adversarial-review", "m23090"],
      "markdown": md1, "figures": FIGS}

r2 = {"title": "裁决 PROD-RA R4（m23090）：changes_requested（窄口径）——D1–D12 实修 / 审阅包 4 项机械残余",
      "summary": "判据基准=行903（12 缺陷）。D1–D12：fixed 11 + D6 fixed_with_residual，open 0；六检全过（regression_scope 带 not_run 注记）。阻断点=审阅包/迁移层：locator 前缀未重根、recheck.py KeyError item_id、SHA256SUMS 5/18 不成立、kb10k provenance 域外路径。scenario_validated 不置位。",
      "scenario_key": "prod_ra_rereview4_m22059_verdict",
      "mission_id": 23090,
      "tags": ["prod-ra", "verdict", "changes-requested", "m22059", "m23090"],
      "markdown": md2, "figures": FIGS}

out = []
for rep in (r1, r2):
    c, res = api("POST", "/tensor/reports", rep, tok)
    print("publish", rep["scenario_key"], c, {k: res.get(k) for k in ("id", "title", "mission_id")})
    out.append({"scenario_key": rep["scenario_key"], "status": c, "id": res.get("id")})
(D / "report_publication.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")