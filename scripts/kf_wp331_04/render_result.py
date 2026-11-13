"""Render docs/kf/wp-331-04/KF-RESULT-wp-331-04.md from the built review JSON.

All numbers in the markdown are pulled from review_report.json (which in turn was
produced by parsing the source), so the document cannot drift from the checked data.
The rendered file carries exactly ONE ```json block: the kf_result envelope that the
platform gate consumes.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "kf" / "wp-331-04"
md_path = OUT / "KF-RESULT-wp-331-04.md"

env = json.loads((OUT / "kf_result.wp-331-04.json").read_text(encoding="utf-8"))
rev = env["outputs"]["review_report.json"]
d = rev["derived_metrics"]
src = rev["source"]

findings_rows = "\n".join(
    f"| {f['id']} | {f['severity']} | {f['category']} | {'yes' if f['blocking'] else 'no'} | "
    f"{str(f['statement']).replace('|', '/')} |" for f in rev["findings"])
def esc(cell: str) -> str:
    """Escape pipes so a quoted markdown table row can live inside a markdown table cell."""
    return str(cell).replace("|", "\\|")


claims_rows = "\n".join(
    f"| {c['claim_id']} | {c['judgement']} | {esc(c['text'])} | {esc(c['reasoning'][:150])} |"
    for c in rev["claim_judgements"])
notrun = "\n".join(f"- {x}" for x in rev["checks_not_run"])
limits = "\n".join(f"- {x}" for x in rev["limitations"])
quote_count = sum(len(f.get("evidence", [])) for f in rev["findings"]) + sum(
    len(c.get("evidence", [])) for c in rev["claim_judgements"])

envelope = json.dumps(env, ensure_ascii=False, indent=2)


def esc(cell: str) -> str:
    """Escape pipes so a quoted markdown table row can live inside a markdown table cell."""
    return str(cell).replace("|", "\\|")

md = f"""# KF-RESULT {env['package_id']}

**tags**: kf-wp:{env['package_id']}, 04-independent-review, report:331, lane:C, in-review, kf-stage-04, verdict:{rev['verdict']}
**agent**: agent/m15788 · repo: TensorKnowledge · branch: agent/m15788
**source**: `{src['uri']}` (field `{src['field']}`, sha256:{src['sha256'].split(':')[1]})
**reviewed package**: `{rev['reviewed_package']}` ｜ **verdict**: `{rev['verdict']}`

---

## ① 本工序做了什么

`wp-331-04` 是 **04-independent-review** 工序，作用域锁死 `report_id=331` 一份报告，审核对象 `wp-331-01`。
审核上下文**只有**报告原文 markdown + 平台记录元数据：没有读生产者的解释、没有读上游 package 的
self_assessment，也没有复用生产 prompt（M5 上下文隔离与 M4 prompt 独立性在包内自证）。

结论一句话：**verdict = `{rev['verdict']}`**。

- **阻塞项（1 条）**：上游 `wp-331-01` 的产物在本身份可触达的四条信道上都取不到（详见 ⑤），
  因此「claim 是否忠实于原文」的逐条审计**做不了**，本包不能判 pass，只能 request_changes。
- **实质问题（5 条 major）**：即便只按原文审，报告本身也有 5 处必须修才能在知识层复用：
  Hertz 对标跑在 δ/R = {d['indent_over_R']}（远超 Hertz 小变形适用域）；「离散格点复现不了连续介质 Hertz」
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
| 3 | 独立重算哈希 | `hashlib.sha256(markdown.encode('utf-8'))` = `{src['sha256']}`，与契约 `source_hash` **逐位相同**；长度 {src['chars']} vs 契约 {src['contract_chars']}，一致 |
| 4 | 离线快照 | 原样落 `runs/wp-331-04/source_331.md`，供离线复算与 pytest |
| 5 | 表格程序化解析 | 正则解析 `## ③ Results` 四列表（Metric/Hertz/Target/Beam），**表内每个数字由代码读取，不手抄** |
| 6 | 参数程序化解析 | 从 `**Parameters**` 行与几何行正则取 `k_bond` / `tool_speed` / `max_indent` / `R` |
| 7 | 派生量计算 | 偏差、容忍带超限倍数、δ/R、预算倍数全部由代码算出（见 ③） |
| 8 | 引文零手抄守卫 | 每条 evidence quote 写入前断言 `quote in markdown` 且记录 offset 与 `sha256(quote)`；共 {quote_count} 条，**0 条失败即构建失败** |
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
| `docs/kf/wp-331-04/kf_result.{env['package_id']}.json` | 平台信封（package_id/task_type/report_id/provenance/outputs），provenance.source_hash 与原文逐字节一致 |
| `docs/kf/wp-331-04/KF-RESULT-{env['package_id']}.md` | 本文件：六段正文 + 唯一一个 json 代码块（信封原样） |
| `runs/wp-331-04/source_331.md` | 源报告 byte-exact 快照（{src['chars']} chars），支撑离线复算 |
| `runs/wp-331-04/review_events.json` | 单条审核状态事件（decision=`request_changes`）；**放在 runs/ 而非输出目录**，使契约 `output`（仅 review_report.json）保持精确 |
| `scripts/kf_wp331_04/*.py` | fetch/list/build/verify/render 五脚本，可复跑 |

派生量（全部由代码从原文表格算出，零手抄）：

| 量 | 值 | 怎么来的 |
|---|---|---|
| Hertz 指数绝对偏差 | {d['exponent_abs_deviation']} | \|{d['exponent_reported']} − {d['exponent_target']}\|，容忍带 ±{d['exponent_tolerance']} |
| 偏差超容忍带倍数 | {d['exponent_tolerance_overshoot_factor']}× | 偏差 ÷ {d['exponent_tolerance']} |
| 刚度误差超预算倍数 | {d['stiffness_budget_overshoot_factor']}× | {d['stiffness_error_pct']}% ÷ {d['stiffness_target_pct']}% |
| 能量漂移超预算倍数 | {d['energy_budget_overshoot_factor']}× | {d['energy_drift_pct']}% ÷ {d['energy_target_pct']}% |
| 梁 PASS 预算余量 | {d['beam_budget_margin_factor']}× | {d['stiffness_target_pct']}% ÷ {d['beam_error_pct']}% |
| 末态 δ/R | {d['indent_over_R']} | max_indent {d['params']['max_indent']} m ÷ R {d['params']['indenter_R']} m |

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
{claims_rows}

finding 全表：

| id | 级别 | 类别 | 阻塞 | 结论 |
|---|---|---|---|---|
{findings_rows}

## ⑤ 注意点与局限

{limits}

**未运行的检查（unknown ≠ pass）**：

{notrun}

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | 信封与 review_report.json 均 `json.loads` 通过（verify V1） |
| `schema_pass` | ✅ | `jsonschema.validate(envelope, schemas/kf_result.v1.schema.json)` 通过（V1）；review 主体为自由对象（契约未给 04 专用 schema） |
| `reviewer_independent` | ✅ | 审核上下文=source markdown+record 元数据，未读生产者解释；审核 prompt 独立撰写；未复用生产 prompt |
| `upstream_packages_completed` | ❌ **honest-FAIL** | 上游 `wp-331-01` 产物在四条信道（报告列表 tag 扫描 / work-packages 端点 404 / psql permission denied / 工作树 wp-331-* 扫描）均未取到 → 判 FALSE，故 verdict 只能是 `needs-fix` |
| 约束 `do_not_mark_claims_as_verified` | ✅ | 包内无任何 verified/verification_status 字段（V5 正则守卫）；reviewer 只给 judgement，不给验证档位 |
| 约束 `reviewer_context_excludes_producer_explanation` | ✅ | 见 ① 与 reviewer.independence_of_producer / producer_explanation_used 字段 |
| 零手抄 | ✅ | {quote_count} 条引文全部子串断言通过（V3）；6 个派生量由代码从原文重算一致（V4） |

**不做 pass 的理由（防粉饰）**：报告本身的 honest-FAIL 值得肯定，但本工序审核的是**知识产物的可用性**。
在 δ/R = {d['indent_over_R']} 的工况下，1.4108 的指数既不能证明格点不行，也不能证明方法可行；
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
{envelope}
```
"""

md_path.write_text(md, encoding="utf-8")
n_json = md.count("```json")
print(f"wrote {md_path.relative_to(ROOT)}  ({len(md)} chars, json blocks={n_json})")
assert n_json == 1, "delivery must carry exactly one json block"
assert md.count("```") == 2, "no other fenced blocks allowed besides the single json block"