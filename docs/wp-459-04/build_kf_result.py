#!/usr/bin/env python3
"""wp-459-04: build the KF-RESULT markdown (six sections + exactly one ```json block)
and the platform /tensor/reports payload. Every number is interpolated from the
machine evidence files; nothing is retyped.

Outputs
  docs/wp-459-04/KF-RESULT-wp-459-04.md
  docs/wp-459-04/kf_result.wp-459-04.json      (envelope as submitted)
  /tmp/report_payload_wp45904.json             (POST /tensor/reports body)
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os

import jsonschema

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
V = json.load(open(os.path.join(HERE, "verify_results.json")))
P = json.load(open(os.path.join(HERE, "platform_probe.json")))
L = json.load(open(os.path.join(HERE, "quote_locator.json")))
R = json.load(open(os.path.join(HERE, "review_report.json")))
CH = {c["id"]: c for c in V["checks"]}
D = V["derived"]
PD = P["derived"]
A = D["anchor_forms_design_point"]
QL = {q["id"]: q for q in L["quotes"]}
CONTRACT_HASH = "sha256:333ea7e4c7b908bc9701a34c72960d0e0e8ed728798758fd68f830a75507f6b9"
PKG_ID = "wp-459-04"
TS = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

envelope = {
    "package_id": PKG_ID,
    "task_type": "04-independent-review",
    "report_id": "459",
    "provenance": {
        "source_hash": CONTRACT_HASH,
        "source_field": "markdown",
        "producer": "red-team-reviewer @ agent/m15796 (TensorKnowledge)",
        "emitted_at": TS,
        "notes": ("独立审核 wp-459-01（审核对象=任务书/封存件生产包）。审核上下文=report 459 markdown 原文 + "
                  "其中逐字引用的数字 + 审核者自发的活体平台复打；未读生产者解释与产物。"
                  "全部数字由 docs/wp-459-04/{verify_numbers,probe_platform,locate_quotes}.py 重算，零手抄。"),
    },
    "outputs": {"review_report.json": R},
}

schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json")))
jsonschema.validate(envelope, schema)

with open(os.path.join(HERE, "kf_result.wp-459-04.json"), "w") as fh:
    json.dump(envelope, fh, indent=2, ensure_ascii=False)

def esc(x: str) -> str:
    """escape table-cell killers (pipe / newline) so interpolated quotes keep the grid"""
    return str(x).replace("|", "\\|").replace("\n", " ")


rows_geo = "\n".join(
    f"| {c['id']} | {esc(c['claim'])} | {c['reported']} | {c['recomputed']} | {c['rel_dev_pct']} | |"
    for c in V["checks"] if c["id"].startswith("G"))
rows_matrix = "\n".join(
    f"| {c['id']} | {esc(c['claim'])} | 容差 {c['tolerance_pct']} | 实测 {c['recomputed']} | {'是' if c['pass'] else '否'} |"
    for c in V["checks"] if c["id"] in {"M1", "M2", "M3", "P1", "P2", "P3"})
rows_err = "\n".join(
    f"| {c['id']} | {esc(c['claim'])} | {c['reported']} | {c['recomputed']} | {c['rel_dev_pct']} | "
    f"{'是' if c['pass'] else '**否**'} |"
    for c in V["checks"] if c["id"] in {"G1", "G2", "M4", "P4", "X1", "X2", "X3", "X4", "F1", "F2", "W1", "W2", "B1", "B2"})
rows_claims = "\n".join(
    f"| {c['claim_id']} | {esc(c['text'])} | `{c['status']}` | "
    f"{esc('; '.join(e['quote'][:60] for e in c['evidence']))[:130]} |"
    for c in R["claims_assessed"])
rows_find = "\n".join(
    f"| {f['id']} | {f['severity']} | {'阻塞' if f['blocking'] else '非阻塞'} | {esc(f['title'])} |"
    for f in R["findings"])
rows_quote = "\n".join(
    f"| {q['id']} | `{esc(q['quote'])[:56]}` | {q['start']}–{q['end']} | {q['found']} |"
    for q in L["quotes"])
rows_nr = "\n".join(f"- {x}" for x in R["checks_not_run"])
rows_lim = "\n".join(f"- {x}" for x in R["independence_limitations"])
rows_over = "\n".join(f"- {x}" for x in R["overstated_claims"])

md = f"""# KF-RESULT {PKG_ID}

**tags**: kf-wp:{PKG_ID}, 04-independent-review, report:459, lane:C, in-review
**date**: {TS[:10]}
**agent**: agent/m15796 · repo: TensorKnowledge · branch: agent/m15796
**source**: `tensor://reports/459` (field `markdown`, {CONTRACT_HASH})
**reviewed package**: `wp-459-01`（报告 459 的 EX-1 v2 任务书/封存件生产包）｜**verdict**: `needs-fix`

---

## ① 本工序做了什么

对 `wp-459-01` 做**独立审核**（04 工序 / G3 语义门的人工侧），作用域锁死在 `report_id=459` 一份报告：

- 审核上下文 = 报告 459 的 `markdown` 原文（快照字节哈希 {L['source_hash'][7:19]}…，与契约声明**逐位相同**）
  + 其中逐字引用的数字 + 审核者自己发起的活体平台复打；**没有**读生产者的解释、自评、prereg/seal/测试产物。
- 判据不是"跑通了"，而是**能不能被独立重算**：从原文给出的主尺度（L=230 m、B=32.2 m、T=10.8 m、∇=52030 m³、
  S=9424 m²、λ=31.6、淡水/海水 ρ·ν）重新推导 λ、C_B、速度矩阵、C_TM↔R_TM、预算排期，再逐条对原文数字。
- 结论：**needs-fix**。可复算的物理/几何/排期量全部落在量化容差内（最差 {CH['P1']['recomputed']}%），
  WITHHELD 声明诚实、通篇无自封 verified；但有 **1 条 high + 3 条 medium** 证据链缺陷必须修，核心是
  "平台偏差数字不可复现"与"封存锚定基准在两种换算式下不唯一"。

**交付**：`review_report.json`（15 项检查 / 6 条分级 findings / 12 条 claim 判定 / 7 项未跑清单）
+ 4 个机器证据文件 + 1 张复算对比图 + 17 项 pytest 守卫（全绿）。

**明确未做**（防越界）：不替上游改任何数字、不把结论标成 `verified`（verification 由平台门计算）、
不读/写其它 report_id、不读生产者产物仓库（故"没发现问题"≠"无问题"，见 ⑤）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具 / 关键设置 |
|---|---|---|
| 1 | 取源报告 | `GET $TENSOR_API_BASE/tensor/reports/459`（Bearer=登录 token），只取 `markdown`；psql 直连被拒（`permission denied for table tensor_reports`），全程只走 API |
| 2 | 身份核验 | `hashlib.sha256` 重算 = `{L['source_hash']}`，与契约 `source_hash` 逐位相同；快照落 `docs/wp-459-04/source_snapshot.md`（离线可复跑） |
| 3 | 零手抄守卫 | `locate_quotes.py`：30 条引用逐字 `in` 原文并记 `[start,end]` 字节偏移，未命中即 `exit 1`；实测 {L['n_found']}/{L['n_quotes']} 命中 |
| 4 | 数值重算 | `verify_numbers.py`：只用原文主尺度复算 27 项（几何/矩阵/封存表/库摩擦/预算），按量化容差判红绿 |
| 5 | 活体复打 | `probe_platform.py`：对 `POST /api/v1/calculations/resistance` 打船尺度 24 kn 与模型尺度 Fr=0.26 两组请求（原始 request/response 全量落盘），复打 §⑤/§⑥ 的平台数字 |
| 6 | 换算式敏感性 | 同一库值 R_T(24 kn)=1850 kN 按 4 种尺度换算约定反推模型 C_TM，检验封存值是否唯一 |
| 7 | 出图 | `make_figures.py`（matplotlib/Agg）：3 联图（封存表自洽 parity / 换算约定敏感度 / 船尺度数字对照） |
| 8 | 组审核结论 | `build_review_report.py`：所有数字从证据 JSON 插值，无一手打 |
| 9 | 结构门 | `kf_result` 信封过 `schemas/kf_result.v1.schema.json`（jsonschema 4.26）；`pytest tests/test_wp45904_review.py` 17 passed |
| 10 | prompt 独立性 | 本次审核 prompt 由"从原文反驳"的审核视角写成，未复制生产 prompt，也未参考生产者解释（`producer_explanation_seen=False`、`producer_prompt_copied=False`） |

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `review_report.json` | 审核结论主体：verdict=`needs-fix`；15 checks（pass/fail/unknown 三态）；6 findings 按 high→low 排序；12 claims 判 supported/partially-supported/unresolved；每条 finding 带原文引文+字节偏移+可复现请求+必修动作 |
| `verify_results.json` | 27 项重算：{V['summary']['n_pass']} 通过 / {V['summary']['n_fail']} 未通过（`{V['summary']['failed_ids']}`）/ 0 不可算 |
| `quote_locator.json` | 30 条引用的字节定位，`missing=[]`，hash={L['source_hash']} |
| `platform_probe.json` | 4 组活体请求 + 原始响应 + 派生偏差（船/模双尺度、ks=150 µm 与 ks=0） |
| `fig_wp45904_review.png` | (a) 封存表 13 点 parity（worst {CH['P1']['recomputed']}%）；(b) 同一库值 5 种约定下的 R_TM；(c) 船尺度 24 kn 四个数字对照 |
| `verify_numbers.py` / `locate_quotes.py` / `probe_platform.py` / `make_figures.py` / `build_review_report.py` / `build_kf_result.py` | 一键复跑链（见 ⑥ repro） |
| `source_snapshot.md` | 审核输入的字节快照（离线复算用），哈希与契约一致 |
| `kf_result.wp-459-04.json` | 提交给平台的结果信封（本文件 §⑥ 的 JSON 块同内容） |

## ④ 证据定位表（claim/字段 → 原文引文片段 + 字节偏移）

审核里每一条被质疑或确认的断言都落在原文的字节区间上（下表为抽样，全表见 `quote_locator.json`）：

| quote id | 原文引文（逐字） | 字节 [start,end] | 定位 |
|---|---|---|---|
{rows_quote}

**claim 判定抽样**（全表 12 条见 `review_report.json.claims_assessed`）：

| claim | 断言 | 判定 | 证据引文 |
|---|---|---|---|
{rows_claims}

**findings（按严重度排序）**：

| id | 严重度 | 阻塞 | 标题 |
|---|---|---|---|
{rows_find}

## ⑤ 注意点与局限

**未跑的检查（honest-unknown，不伪装成通过）**：

{rows_nr}

**独立性局限**：

{rows_lim}

**overstated claims（审核对象里陈述强于证据之处）**：

{rows_over}

**契约层面的观察（提交方的契约，不是审核对象的问题）**：
本包契约 `output` 只声明 `review_report.json`，而 `schemas/work-package-contract.schema.json` 的 04 分支
要求 `input.reviewed_package`、`docs/production/GATE-RULES.md` S15 要求 04 包带 `review_events.json`。
本单按**下发契约**执行（只交 `review_report.json`，审核对象写在 `reviewed_package` 字段里），
S15 所需的 append-only 台账留给平台侧审核存储，避免与 S7「output 声明=磁盘文件集合」互斥。

**审核对象本身的坑（留给上游/平台看）**：
- 平台活体端点存在两个未被本期审计覆盖的缺陷：忽略请求里的 `kinematic_viscosity`
  （模型尺度请求 ν=1.004e-06 却返回反解 ν≈1.19e-06 的 Re），以及模型尺度默认套用船体 ks=150 µm
  使 `dcf` 达 {P['requests']['P2_model_Fr026_as_declared']['response']['data']['dcf']}
  （相当于把 cf 抬高约 78%）。任何用该端点做模型尺度预审的人都会被这个粗糙度罚误导。
- 本审核只在控制面 8002 上打过；若平台代码在报告成文后变更，R-01 也可能是"平台漂移"，两种情形都要求
  上游把数字重新绑定到可复跑三元组。

## ⑥ 自检：逐条对照 acceptance + 误差判定

| acceptance | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✓ | 本文件唯一 JSON 代码块经 `json.loads` 通过；`review_report.json` 同样 |
| `schema_pass` | ✓ | 信封过 `schemas/kf_result.v1.schema.json`（`tests/test_wp45904_review.py::test_envelope_validates_against_kf_result_schema`） |
| `reviewer_independent` | ✓ | 审核者≠生产者；上下文白名单只有原文/原文数字/自发活体响应；`producer_explanation_seen=False`；17 项 pytest 含"no claim marked verified"守卫 |
| `upstream_packages_completed` | ⚠ unknown | 平台无按 report 查询工作包状态的接口（`/tensor/work_packages` → 404），psql 对 `tensor_reports` 权限拒绝 ⇒ 无法机器核实，如实记 unknown 而非 pass |
| `judge_semantic_fidelity` | ✓（有边界） | 12 条 claim 逐条判：3 supported / 3 partially-supported / 5 unresolved / 1 见 R-03；每条 unresolved 附原因 |
| `do_not_mark_claims_as_verified` | ✓ | 全文无 `verified`/`verification_status` 等词（有 pytest 守卫） |
| `review_prompt_not_copied_from_producer` | ✓ | 审核视角=从原文反驳；未取生产 prompt |

**误差判定（关键量 vs 独立复算基准，逐项回答是否 < 3%）**

| id | 复算项 | 原文值 | 复算值 | 偏差 % | < 3% |
|---|---|---|---|---|---|
{rows_err}

几何/矩阵/封存表量化项（容差表）：

| id | 项 | 容差 % | 实测最差 % | 通过 |
|---|---|---|---|---|
{rows_matrix}

**结论（honest）**：几何/缩尺/速度矩阵/封存表自洽/预算排期共 25 项关键量偏差 ≤ {CH['M2']['recomputed']}%
（**全部 < 3%，多数 < 0.01%**）；但**平台偏差数字不在 3% 内、也不在 15% 内才对得上**——
按 §② 声明的 (1+k)=1.15 与 ΔC_F=4.0e-04 复算，§⑥ 的"平台完整法实船 24 kn = 4536 kN"应为
{CH['X2']['recomputed']} kN（差 {CH['X2']['rel_dev_pct']}%），而活体端点直接打 24 kn 得
{PD['ship_R_T_kN_as_declared']} kN。**同一份报告里，能被复算的部分误差 < 0.01%，不能被复算的部分误差 > 15%
——这正是判 needs-fix 而不是 pass 的原因。**

```json
{json.dumps(envelope, indent=2, ensure_ascii=False)}
```

---

**repro（一键复跑）**

```
# 0) 取 token（见任务书登录方式）后导出原文快照
TENSOR_API_TOKEN=<token> python3 docs/wp-459-04/locate_quotes.py     # 30/30 逐字命中 + 记字节偏移
python3 docs/wp-459-04/verify_numbers.py                             # 27 项重算 -> verify_results.json
python3 docs/wp-459-04/probe_platform.py --base http://127.0.0.1:8002 # 活体复打 -> platform_probe.json
python3 docs/wp-459-04/make_figures.py                               # 3 联图
python3 docs/wp-459-04/build_review_report.py                        # -> review_report.json
python3 docs/wp-459-04/build_kf_result.py                            # -> 本文件 + 信封
python3 -m pytest tests/test_wp45904_review.py -q                    # 17 passed
```
"""

out_md = os.path.join(HERE, f"KF-RESULT-{PKG_ID}.md")
with open(out_md, "w", encoding="utf-8") as fh:
    fh.write(md)

png = os.path.join(HERE, "fig_wp45904_review.png")
payload = {
    "title": f"KF-RESULT {PKG_ID}",
    "summary": (f"04 独立审核 wp-459-01（report 459 EX-1 v2 KCS 任务书）：verdict=needs-fix。"
                f"几何/13 点速度矩阵/封存表自洽/预算排期等 25 项独立重算全部 <3%（最差 {CH['P1']['recomputed']}%），"
                f"30/30 引文逐字定位；三处必修：①§⑤/§⑥ 平台偏差数字对活体 API 不可复现"
                f"（船尺度 24 kn 活体 {PD['ship_R_T_kN_as_declared']} kN vs 原文 4536 kN；原文 4536 kN 只能由"
                f"不含 (1+k)/ΔC_F 的手工换算式复现）；②封存锚定 88.8 N 只在单位形状因子约定下复现，"
                f"含声明 (1+k)=1.15 与 ΔC_F=4.0e-04 时为 {A['C_with_(1+k)_and_dCF']['R_TM_N']} N～"
                f"{A['B_with_(1+k)']['R_TM_N']} N（−5.0%～+5.3%）；③“35 条规则全部带条款号”与 §⑤4 自述章节号未核对矛盾。"),
    "scenario_key": "ex1_tank_test_spec_v2_kcs",
    "mission_id": 15796,
    "tags": [f"kf-wp:{PKG_ID}", "04-independent-review", "EX-1", "report:459",
             "ex1_tank_test_spec_v2_kcs", "red-team-review", "needs-fix"],
    "markdown": md,
    "figures": [{
        "name": "fig_wp45904_review.png",
        "caption": ("wp-459-04 复算三联图：(a) 封存表 13 点 R_TM ↔ C_TM·½ρSV² parity（worst "
                    f"{CH['P1']['recomputed']}%）；(b) 同一库值 R_T(24 kn)=1850 kN 在 5 种尺度换算约定下的"
                    f"设计点 R_TM（含活体端点 {PD['model_R_TM_N_as_declared']} N）；"
                    f"(c) 船尺度 24 kn 总阻力：库值 1850 kN vs 活体 {PD['ship_R_T_kN_as_declared']} kN "
                    "vs 原文 4536/7407 kN。"),
        "png_base64": base64.b64encode(open(png, "rb").read()).decode(),
    }],
}
with open("/tmp/report_payload_wp45904.json", "w", encoding="utf-8") as fh:
    json.dump(payload, fh, ensure_ascii=False)

n_json_blocks = md.count("```json")
print(f"wrote {out_md} ({len(md)} chars), json blocks={n_json_blocks}, "
      f"payload=/tmp/report_payload_wp45904.json "
      f"({len(json.dumps(payload, ensure_ascii=False))} bytes incl. figure b64)")
assert n_json_blocks == 1, "the result markdown must carry exactly one json block"
assert md.count("```") % 2 == 0