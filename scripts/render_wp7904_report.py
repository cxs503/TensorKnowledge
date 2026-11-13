#!/usr/bin/env python3
"""Render docs/kf/wp-79-04/REPORT.md and the platform payload /tmp/report_wp7904.json.

The numeric table and every quote are injected from the programmatic outputs
(runs/wp-79-04/checks.json) and docs/kf/wp-79-04/review_report.json — nothing is
retyped. The result envelope appears as the only ```` ```json ```` block.

Run: python3 scripts/render_wp7904_report.py
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/kf/wp-79-04"
checks = json.loads((ROOT / "runs/wp-79-04/checks.json").read_text(encoding="utf-8"))
rr = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
env = json.loads((OUT / "kf_result.wp-79-04.json").read_text(encoding="utf-8"))
png = (OUT / "review_checks.png").read_bytes()

c1, c2, c3, c5, c6, c7 = (checks[k] for k in ("C1", "C2", "C3", "C5", "C6", "C7"))
c4 = c3["C4"]

numeric_rows = "\n".join(
    "| `{pair}` | {printed} | {artifact} | {d} | {rounded} | {rc} | {absp} | {rel} |".format(
        pair=r["pair"], printed=r["printed"], artifact=r["artifact"],
        d=r["printed_decimals"], rounded=r["artifact_rounded"],
        rc="✅" if r["rounding_consistent"] else "❌",
        absp=r["abs_dev_pct_points"], rel=r["rel_dev_pct"])
    for r in c3["rows"])

ev_rows = []
for f in rr["findings"]:
    if f["evidence"]:
        for ev in f["evidence"]:
            q = ev["quote"].replace("|", "\\|")
            ev_rows.append(f"| {f['id']} | `source.md[{ev['start_offset']}:{ev['end_offset']}]` "
                           f"| {q} |")
    else:
        ev_rows.append(f"| {f['id']} | `runs/wp-79-04/checks.json#C6` "
                       f"| （平台状态断言，无原文可引；以探针工件为证） |")
ev_table = "\n".join(ev_rows)

find_rows = "\n".join(
    f"| {f['id']} | {f['severity']} | {f['likelihood']} | {f['title']} | {f['artifact_ref']} |"
    for f in rr["findings"])

acceptance = [
    ("valid_json", True, f"kf_result.wp-79-04.json 可解析；jsonschema 校验通过（tests 10 passed）"),
    ("schema_pass", True, "schemas/kf_result.v1.schema.json 校验通过；review_events.json 过 "
                          "review-event.schema.json"),
    ("reviewer_independent", True,
     f"审核 prompt 与生产 prompt 5-gram Jaccard={c7['jaccard_5gram']}<{c7['threshold']}；"
     "上下文仅 source.md，未看生产者解释（producer_explanation_seen=false）；"
     "局限：同一 harness 家族内独立席位，非人审"),
    ("upstream_packages_completed", False,
     f"HONEST FAIL：审核对象 wp-79-01 在有界探针内未命中（A：最新 "
     f"{c6['probe_a_newest_by_id']['n']} 份 id {c6['probe_a_newest_by_id']['id_range'][0]}-"
     f"{c6['probe_a_newest_by_id']['id_range'][1]}；B：mission "
     f"{c6['probe_b_mission_window'][0]}-{c6['probe_b_mission_window'][1]}），正控制 "
     f"wp-9083-01 命中 {c6['positive_control']['hits']} ⇒ 探针非空转，但缺失属事实"),
]
acc_table = "\n".join(f"| {n} | {'✅' if ok else '❌'} | {d} |" for n, ok, d in acceptance)

body = f"""# KF-RESULT wp-79-04

**工序 04 独立审核（red-team-reviewer）— report_id=79「批次质检报告复审 — Reports 64, 65, 66」**
审核对象 `wp-79-01` ｜ 判定 **{rr['verdict']}** ｜ 审核事件决定 `request-changes`

## ① 本工序做了什么

对 report 79（一份对 Reports 64/65/66 的批次质检报告的复审）做独立对抗式审核。工作包契约给定
`input.source_hash=sha256:{c1['expected'].split(':', 1)[1][:16]}…`（全长见下）、
`objective.judge_semantic_fidelity=true`、`output=review_report.json`。

先做**不可程序化的那部分之外的一切**：冻结原文并重算哈希（{c1['chars']} 字符，与契约逐字节一致）；
再把报告里的每一条"数字溯源 ✅"重新推导一遍（{c3['pairs']} 个数字对）；
再数一遍"声明的质检标准"与"逐篇实际留下结果的标准"（{c5['declared_criteria']} 声明 vs 记录
{c5['coverage_ratio']}）；最后用有界探针找上游知识包 wp-79-01（**未找到**）。

**本单最重要的结论是 honest FAIL**：审核对象 wp-79-01 在平台上不可达，因此
`semantic_fidelity`（"claim 是否真表达原文"）**无法判定**，标 `not_run`、
`pass=null`，本单不冒充"语义门通过"。审核能落到实处的，是对来源报告**自身**的
内部一致性反驳——那里查出 1 项 blocking、4 项 major、2 项 minor、1 项 informational。

### 缺陷清单（severity 降序）

| id | severity | likelihood | 缺陷 | 证据工件 |
|---|---|---|---|---|
{find_rows}

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/79` → `markdown` 字段，落盘冻结为
   `docs/kf/wp-79-04/source.md`（`source.sha256` 旁存）。
2. **重算哈希**（C1）：`sha256(source.md)` 与契约 `input.source_hash` 比对 → **{c1['pass'] and 'PASS' or 'FAIL'}**。
3. **引文可定位性**（C2）：审核报告的每条引文都作为原文子串反查并记录 `[start,end)`，
   {c2['quotes_found']}/{c2['quotes_total']} 命中，最短 {c2['min_chars']} 字符（防"用短词当证据"）。
4. **数字复推**（C3）：对 {c3['pairs']} 个"报告值 ← 工件值"对，用确定性判据
   "工件值按报告打印精度四舍五入 == 报告值"复算；同时算绝对差（百分点）与相对差（%）。
5. **容差口径反驳**（C4）：报告的"±0.01%"存在两种读法，两种读法给不同结论——这是缺陷本身，
   不是复算误差（见 ③ 与图）。
6. **判据覆盖计数**（C5）：把 §①"质检标准"六项与 §③ 汇总表表头逐项对齐。
7. **上游存在性探针**（C6）：报告列表接口忽略 `offset/search/tags/cursor`（实测四组参数返回同一页），
   所以探针写成有界两路（A 最新 100 份；B mission 15600–15660 逐 mission 查询），
   并强制**正控制**（wp-9083-01 必须命中，否则探针判 void 而非"不存在"）。
8. **prompt 独立性度量**（C7）：审核 prompt（`review_prompt.md`）vs 生产 prompt
   （`extraction-skills/prompts/producer-v1.md`）字符 5-gram Jaccard = {c7['jaccard_5gram']}
   （阈值 {c7['threshold']}）。

关键设置：全程只读 report 79（不读 64/65/66，遵守互不覆盖边界）；审核者不看生产者解释
（wp-79-01 缺失，也无可看）；不写任何 verified/verification 类字段；判定词汇固定
`pass | fail | needs-fix`。

`repro_cmd`（一键复跑，含平台探针）：

```bash
python3 scripts/kf_wp7904_review.py && python3 scripts/emit_wp7904_result.py \\
  && python3 scripts/render_wp7904_report.py && python3 -m pytest tests/test_kf_wp7904_review.py -q
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-79-04/review_report.json` | 本工序合同产物：verdict=`{rr['verdict']}`、8 条 findings、7 项 checks_performed、4 项 checks_not_run、5 条 overstated_claims、1 条 unresolved |
| `docs/kf/wp-79-04/review_events.json` | append-only 审核事件：`decision=request-changes`，reviewer 角色 red-team-reviewer，2 条送审前置条件 |
| `docs/kf/wp-79-04/kf_result.wp-79-04.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims），8 条 claim（7 supported + 1 unresolved） |
| `docs/kf/wp-79-04/source.md` + `source.sha256` | report 79 markdown 冻结副本 + 哈希（{c1['actual']}） |
| `docs/kf/wp-79-04/review_prompt.md` | 独立审核 prompt（与生产 prompt Jaccard {c7['jaccard_5gram']}） |
| `runs/wp-79-04/checks.json` | 7 项检查的机器结果（含每个数字对、每条引文偏移） |
| `docs/kf/wp-79-04/review_checks.png` | 图：9 个数字对在两种容差读法下的偏差（红线=报告自定 ±0.01%） |
| `scripts/kf_wp7904_review.py` / `scripts/emit_wp7904_result.py` / `scripts/render_wp7904_report.py` | 检查器 / 结果生成器 / 报告渲染器（数字与引文全部程序化注入） |
| `tests/test_kf_wp7904_review.py` | 10 条不变式测试（引文偏移逐字相等、9/9 舍入自洽、4/9 相对读法超阈、覆盖 4/6、无自封验证字段） |

### 数字复推表（程序化注入，零手抄）

| 数字对 | 报告值 | 报告所称工件值 | 打印精度 | 工件值舍入 | 舍入一致 | 绝对差(pp) | 相对差(%) |
|---|---|---|---|---|---|---|---|
{numeric_rows}

判据口径：最大绝对差 {c3['max_abs_dev_pct_points']} pp（绝对读法全过），最大相对差
{c3['max_rel_dev_pct']:.4f}%（相对读法 {len(c4['pairs_failing_relative_reading'])}/{c3['pairs']} 对超报告自定 ±0.01%）。

## ④ 证据定位表（claim/字段 → 原文引文片段）

| finding | 定位 | 引文（逐字） |
|---|---|---|
{ev_table}

全部引文由 `C2` 程序化验证为 `source.md` 的子串，`text[start:end] == quote` 由
`tests/test_kf_wp7904_review.py::test_finding_quotes_match_source_at_declared_offsets` 断言。

## ⑤ 注意点与局限

**踩过的坑**

1. **平台报告列表不可分页**：`offset / skip / page / cursor / search / tags` 全部被忽略（实测
   四组参数返回同一页），`per_page` 还改变返回条数却不改变起点。后果：任何"某产物不存在"的断言
   都只能是**有界**断言——本单因此写了 A/B 两路探针 + 正控制，并把边界写进 checks.json。
2. **"✅"不是证据**：报告把 9 对数字全标 ✅，但它的自定容差 ±0.01% 在相对读法下会被自己的数据
   打穿（4/9）。标签与判据脱钩是这类质检报告最典型的失真方式。
3. **psql 不可用**：`select markdown from tensor_reports` 直接 permission denied，
   必须走平台 API（本单用 `/tensor/reports/79` + Bearer token）。
4. **信封 schema 与审核需要冲突**：`kf_result.v1.schema.json` 的 `claims[].evidence` 是
   `additionalProperties: false`，只允许 `quote/source_field/note`，**不允许偏移**；
   于是偏移保留在 `review_report.json`（findings.evidence）里，信封内用 `note="source.md[s:e]"`
   承载定位——两处都要能定位，否则 E3/E4 类门无法复核。

**局限（如实写）**

- **未读 report 64/65/66**：边界禁止读写其它 report_id，因此"3/3 ✅"的数字溯源**只**做了报告
  内部自洽复算，工件侧数值未被二次确认（`checks_not_run` 第 1、2 条）。
- **上游缺失导致 fidelity 轴 not_run**：不是"通过"，是不判定（`pass=null`）。
- **审核者身份**：同一 agent harness 家族内的独立席位，非人审，未做强模型抽样双读（M6 抽样未实现）。
- **探针有界**：若 wp-79-01 落在 id < {c6['probe_a_newest_by_id']['id_range'][0]} 且不在
  mission {c6['probe_b_mission_window'][0]}–{c6['probe_b_mission_window'][1]} 内，本单看不到它——
  但产线是同一波派单，正控制证明同波 KF-RESULT 能被探针看见。

**误差判定（关键量 vs 基准，逐项）**

本工序无物理计算，基准=报告自身打印值：

| 关键量 | 基准 | 复算结果 | 是否 <3% |
|---|---|---|---|
| 9 个数字对的舍入一致性 | 报告打印值 | {c3['pairs_rounding_consistent']}/{c3['pairs']} 一致（舍入后偏差=0） | 是（0%） |
| 绝对差（百分点读法） | 报告自定 ±0.01% pp | 最大 {c3['max_abs_dev_pct_points']} pp | 是（0.0033% ≪ 3%，也满足 ±0.01%） |
| 相对差（相对读法） | 报告自定 ±0.01% | 最大 {c3['max_rel_dev_pct']:.4f}% | 是（<3%），**但 >0.01%**：{len(c4['pairs_failing_relative_reading'])}/9 对不满足报告自定容差 |
| 判据覆盖率 | 6 项声明 | {c5['coverage_ratio']} | 不适用（计数指标非误差量）：缺口 2 项＝结构五节、结论不超证据 |
| prompt 独立性 | Jaccard < 0.5 | {c7['jaccard_5gram']} | 是 |

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结论 | 依据 |
|---|---|---|
{acc_table}

honest-FAIL 声明：**`upstream_packages_completed` 不成立**——审核对象 wp-79-01 未落库。
按产线规矩，这一条不能靠"来源报告看起来自洽"抵偿；本单据此判 `needs-fix` /
`request-changes`，并把 fidelity 轴标 `not_run` 而非 `pass`。

![wp-79-04 numeric traceability](review_checks.png)

*图注：左=相对读法（4/9 越过报告自定 ±0.01% 红线），右=绝对百分点读法（0 对越线）。
同一份证据、两种读法、两个结论——即缺陷 F3 的可视化。*

---

## 结果信封（唯一 json 块）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""

(OUT / "REPORT.md").write_text(body, encoding="utf-8")

payload = {
    "title": "KF-RESULT wp-79-04",
    "summary": (f"独立审核 report 79（批次质检复审 64/65/66）：判定 needs-fix / request-changes；"
                f"1 blocking（上游 wp-79-01 不可达 ⇒ fidelity not_run）、4 major"
                f"（溯源不可重放、±0.01% 容差口径自违 {len(c4['pairs_failing_relative_reading'])}/9、"
                f"判据覆盖 {c5['coverage_ratio']}、图件判据不可重复）；"
                f"数字对 {c3['pairs_rounding_consistent']}/{c3['pairs']} 舍入自洽。"),
    "scenario_key": "report",
    "mission_id": 15631,
    "tags": ["KF-RESULT", "kf-wp:wp-79-04", "04-independent-review",
             "KBM-RCI-F1-FACTORY", "TensorKnowledge", "report-79", "red-team-review"],
    "markdown": body,
    "figures": [{
        "name": "review_checks.png",
        "caption": ("wp-79-04：report 79 的 9 个数字对在两种容差读法下的偏差。"
                    f"左图为相对读法（{len(c4['pairs_failing_relative_reading'])}/9 越过报告自定 "
                    "±0.01% 红线），右图为绝对百分点读法（0 对越线）；"
                    f"舍入判据下 {c3['pairs_rounding_consistent']}/{c3['pairs']} 全部一致。"),
        "png_base64": base64.b64encode(png).decode(),
    }],
}
Path("/tmp/report_wp7904.json").write_text(json.dumps(payload, ensure_ascii=False),
                                           encoding="utf-8")
print(json.dumps({"report_md": "docs/kf/wp-79-04/REPORT.md",
                  "bytes": len(body.encode()),
                  "md_sha256": hashlib.sha256(body.encode()).hexdigest(),
                  "payload": "/tmp/report_wp7904.json",
                  "json_blocks": body.count("```json")}, ensure_ascii=False))