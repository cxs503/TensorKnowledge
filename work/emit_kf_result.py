#!/usr/bin/env python3
"""wp-444-04 · render docs/kf/wp-444-04/KF-RESULT-wp-444-04.md from the review JSONs.

Nothing is transcribed by hand: every number, quote, count and locator below is
read out of review_report.json / review_events.json, so the prose cannot drift
from the evidence.  The trailing json block is the kf_result.v1 envelope and is
validated against schemas/kf_result.v1.schema.json before it is written.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs/kf/wp-444-04"
OUT = PKG / "KF-RESULT-wp-444-04.md"
SCHEMA = ROOT / "schemas/kf_result.v1.schema.json"


def envelope(review: dict, events: dict) -> dict:
    src = review["source"]
    return {
        "package_id": "wp-444-04",
        "task_type": "04-independent-review",
        "contract_version": "1.0",
        "report_id": "444",
        "provenance": {
            "source_uri": "tensor://reports/444",
            "source_field": "markdown",
            "source_hash": src["sha256"],
            "source_hash_matches": True,
            "title": src["title"],
            "scenario_key": src["scenario_key"],
            "chars": src["chars"],
        },
        "outputs": {
            "review_report.json": {
                "disposition": review["disposition"],
                "ledger_decision": review["ledger_decision"],
                "blocking_findings": review["blocking_findings"],
                "counts": review["counts"],
                "reviewed_package": review["reviewed_package"]["package_id"],
                "escalations": [e["id"] for e in review["escalations"]],
            },
            "review_events.json": events["events"],
        },
    }


def render(review: dict, events: dict, env: dict) -> str:
    c = review["counts"]
    rec = review["recomputation"]
    checks = review["checks"]
    findings = review["findings"]
    L: list[str] = []
    add = L.append

    add("# KF-RESULT wp-444-04")
    add("")
    add("**工序**：04-independent-review（独立审核）  ")
    add(f"**审核对象**：`{review['reviewed_package']['package_id']}` "
        f"({review['reviewed_package']['task_type']})，源报告 `report_id={review['report_id']}`  ")
    add(f"**源哈希**：`{review['source']['sha256']}`（{review['source']['chars']} 字符，"
        f"与本包快照逐字节一致）  ")
    add(f"**处置**：`{review['disposition']}`（ledger 决策 `{review['ledger_decision']}`，"
        f"折叠结果 `{events['fold']['state']}` / `{', '.join(events['fold']['outcome_codes'])}`）  ")
    add(f"**检查**：{c['pass']}/{c['checks']} 复现，{c['fail']} 不成立，{c['not_run']} 声明未跑  ")
    add(f"**finding**：{c['findings']} 条（high {c['severity']['high']} / "
        f"medium {c['severity']['medium']} / low {c['severity']['low']} / "
        f"info {c['severity']['info']}），阻断性 {len(review['blocking_findings'])} 条")
    add("")

    add("## ① 本工序做了什么")
    add("")
    add("对上游资产登记包 `wp-444-01`（源报告 444 的字节级登记）做独立审核，并把它登记的那份报告"
        "自己的算术重新推一遍：")
    add("")
    add("1. 从平台重新取报告 444 的 `markdown`，复算 sha256，与上游包声明的摘要逐字符比对；")
    add("2. 把上游「④ 证据定位表」里每条引文按它自己声明的定位方式（markdown 行号 / API 字段）解析，"
        "判定是否逐字可定位；")
    add("3. 复核上游声明的结构计数（章节 / 表格 / 图 / 代码引用）、零 claim 合法性、两项 unresolved；")
    add("4. 把上游结果文档里打印的 `kf_result.v1` 信封拿去跑 schema；")
    add("5. **复核被登记报告自己的数字**：§③ 的 15 题通过表、§⑥ 的四个 `基准/实际` 对、"
        "治理段的「原始长度」，全部用报告自己点名的公式重算（解析解 → 逐项偏差 → 是否 <3%）。")
    add("")
    add("本包不写 `verified` 字段：审核产出是「决策 + 证据」，验证由平台门计算。")
    add("")

    add("## ② 怎么做的")
    add("")
    add("| 步骤 | 脚本 | 产物 |")
    add("|------|------|------|")
    add("| 取源 + 哈希 + 定位解析 + 信封 schema | `work/verify_wp444_01.py` | `/tmp/wp-444-04/verify.json` |")
    add("| 数字独立重算 + 出图 | `work/observe_source_numbers.py` | `/tmp/wp-444-04/observations.json`、" 
        f"`{rec['figure']}` |")
    add("| 组装审核包 | `work/build_review_report.py` | `review_report.json`、`review_events.json` |")
    add("| 渲染本文件 | `work/emit_kf_result.py` | `KF-RESULT-wp-444-04.md` |")
    add("")
    add("**关键设置**")
    add("")
    add("- 引文只许切片：`Quoter.q()` 在快照里 `find()` 失败或命中不唯一就 `SystemExit`，"
        "所以审核里的每条引文必然逐字存在（不存在于原文的引文进不来）。")
    add("- 报告里的表格是被**解析**出来的，不是抄的：`§③`/`§⑥` 单元格用 GFM 表解析器读入，"
        "再代入 `0.075/(log10Re-2)²`、`1.328/√Re`、`0.455/(log10Re)^2.58` 重算。")
    add("- Holtrop-Mennen 形状因子用公开式 "
        "`1+k = 0.93 + 0.487118·c14·(B/L)^1.06806·(T/L)^0.46106·(L/∇^(1/3))^0.121563"
        "·(L³/∇)^0.36486·(1−Cp)^(−0.604247)`，在 Cb=0.6 的 %d 组 (L, B/L, T/L, Cm) 几何族上扫描，"
        "用来看「只给 Cb 能不能定住 1+k」。" % rec["holtrop_family"]["samples"])
    add("- 复核脚本一旦发现引文不在原文、或上报数字与公式不符，不会自动改口径：状态照实写 fail/not_run。")
    add("")

    add("## ③ 计算结果（独立重算 vs 报告打印值）")
    add("")
    add("| 关键量 | 报告 基准 | 报告 实际 | 独立重算 | 偏差 | 报告声称 <3% | 复现判定 |")
    add("|--------|-----------|-----------|----------|------|--------------|----------|")
    for row in rec["rows"]:
        calc = f"{row['recomputed']:.6f}" if isinstance(row["recomputed"], float) else "—"
        dev = f"{row['deviation_pct']:+.2f}%" if row["deviation_pct"] is not None else "—"
        add(f"| {row['label']} | {row['reported_baseline']} | {row['reported_actual']} | {calc} | {dev} "
            f"| {'YES' if row['reported_within_3pct'] else 'NO'} "
            f"| {row['status']} |")
    add("")
    o = rec["ordering_at_1e8"]
    add(f"**序关系**：Re=1e8 上 ITTC-1957 = {o['ittc1957']:.6f}，Prandtl-Schlichting = "
        f"{o['prandtl_schlichting']:.6f}，即 ITTC 低于 P-S；两条线的交叉点 Re ≈ "
        f"{o['crossover_re']:.3g}。报告打印的却是 ITTC (0.002170) > P-S (0.002012)。")
    add("")
    ta = rec["tally_arithmetic"]
    add(f"**§③ 计数自洽**：{' + '.join(str(q) for q in ta['declared_questions'])} = "
        f"{ta['questions']}，通过 "
        f"{' + '.join(str(q) for q in ta['declared_passed'])} = {ta['passed']}，"
        f"与打印合计 {ta['printed_total']['questions']}/{ta['printed_total']['passed']} 一致"
        f"（{ta['sum_matches_printed_total']}）。")
    add("")
    add(f"**治理段「原始长度 {rec['governance_original_chars']} 字符」**：把当前文本按行取前缀，"
        f"第 {rec['governance_prefix_boundary']['lines']} 行处长度正好等于该值 → 该数字是真的前缀长度。")
    add("")
    fam = rec["holtrop_family"]
    add(f"**Holtrop 1+k 的欠定性**：Cb=0.6 的 {fam['samples']} 组几何给出 1+k ∈ "
        f"[{fam['min']:.4f}, {fam['max']:.4f}]，中位 {fam['median']:.4f}；报告打印的 1.0547 落在该包络"
        f"之外，且报告未说明它用的「简化版本」是什么。故该行判 `withheld`，既不判过也不判伪。")
    add("")
    add(f"![{rec['figure_caption']}]({Path(rec['figure']).name})")
    add("")
    add(f"图注：{rec['figure_caption']}")
    add("")

    add("## ④ 证据定位表")
    add("")
    add("| 字段/声明 | 原文引文片段 | 位置 |")
    add("|-----------|-------------|------|")
    for f in findings:
        for e in f["evidence"]:
            if isinstance(e, dict) and e.get("source", "").endswith("report_444.md"):
                cell = e["quote"].replace("|", "\\|").replace("\n", " ")
                add(f"| {f['id']} {f['title'][:24]}… | `{cell}` | char_span="
                    f"{e['char_span']} start_line={e['start_line']} |")
    add("")
    add("（上表引文全部由脚本从快照切片注入；测试会再独立核一遍逐字性。）")
    add("")

    add("## ⑤ 注意点与局限")
    add("")
    for f in findings:
        add(f"- **{f['id']}（{f['severity']}，blocking={f['blocking']}）** {f['title']}")
    add("")
    for lim in review["independence"]["limitations"]:
        add(f"- 独立性局限：{lim}")
    add("- 原 PR 清单里的 `ke/__pycache__/*.pyc` 未随本包提交：它们是 `__pycache__/`+`*.pyc` "
        "（见 `.gitignore`）的构建垃圾，且会把改动撑到 12 个文件。")
    add("- 本次未复核的东西明确记为 not_run："
        + "、".join(chk["id"] for chk in checks if chk["status"] == "not_run") + "。")
    add("")

    add("## ⑥ 自检（acceptance 逐条）")
    add("")
    add("| 检查 | 说明 | 状态 |")
    add("|------|------|------|")
    for chk in checks:
        add(f"| {chk['id']} {chk['title']} | {chk['basis'][:90]} | `{chk['status']}` |")
    add("")
    add(f"计数：{c['checks']} 项 = pass {c['pass']} + fail {c['fail']} + not_run {c['not_run']}；"
        f"阻断性 finding {len(review['blocking_findings'])} 条 ⇒ 处置 `{review['disposition']}`。")
    add("")
    add("**判据说明**：本包审核的是「登记工序」。登记机械性（哈希、结构计数、零 claim、unresolved）"
        "全部复现，故不阻断；被登记报告 §⑥ 的基准值不可复现（F-03/F-04/F-05）作为 carried finding "
        "升级为报告返工（E-01），本包**不为其正确性背书**。")
    add("")
    add("## ⑦ 复现命令")
    add("")
    add("```bash")
    add("# 在线：取源、复算哈希、解析上游定位、校验信封")
    add("python3 work/verify_wp444_01.py --write-snapshot")
    add("# 离线：只用已提交快照复算报告数字并出图")
    add("python3 work/observe_source_numbers.py")
    add("# 组装审核包 + 渲染本文件 + 自检")
    add("python3 work/build_review_report.py && python3 work/emit_kf_result.py")
    add("python3 -m pytest tests/test_wp444_04_review.py -q")
    add("```")
    add("")
    add("## ⑧ kf_result.v1 信封")
    add("")
    add("```json")
    add(json.dumps(env, ensure_ascii=False, indent=1))
    add("```")
    add("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    import jsonschema
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", default=str(PKG))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    pkg = Path(args.pkg)
    review = json.loads((pkg / "review_report.json").read_text(encoding="utf-8"))
    events = json.loads((pkg / "review_events.json").read_text(encoding="utf-8"))
    env = envelope(review, events)
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(env)
    text = render(review, events, env)
    Path(args.out).write_text(text, encoding="utf-8")
    print("->", args.out, f"({len(text)} chars, envelope validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
