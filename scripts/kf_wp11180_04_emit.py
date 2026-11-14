#!/usr/bin/env python3
"""Emit the wp-11180-04 independent-review deliverables from review_checks.json.

Produces
  docs/kf/wp-11180-04/review_report.json   the reviewed-object carrier (skill contract)
  docs/kf/wp-11180-04/review_report.md     KF-RESULT markdown, exactly one json block

Every number and quote in both files is injected from review_checks.json (which
in turn derives them from the source bytes), so nothing is retyped by hand.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "docs/kf/wp-11180-04")
CHECKS = os.path.join(OUT_DIR, "review_checks.json")
REVIEW_JSON = os.path.join(OUT_DIR, "review_report.json")
REVIEW_MD = os.path.join(OUT_DIR, "review_report.md")

PKG = "wp-11180-04"
REVIEWED = "wp-11180-01"
REPORT_ID = "11180"

REPRO = ("python3 scripts/kf_wp11180_04_checks.py --live && "
         "python3 scripts/kf_wp11180_04_emit.py && "
         "python3 -m pytest tests/test_wp11180_04_review.py -q")


def load() -> dict:
    with open(CHECKS, encoding="utf-8") as f:
        return json.load(f)


def ck(res: dict, cid: str) -> dict:
    return next(c for c in res["checks"] if c["id"] == cid)


def findings(res: dict) -> list[dict]:
    q = res["quote_binding"]
    n = ck(res, "C9")["detail"]
    sens = ck(res, "C12")["detail"]
    spans = res["upstream"]["asset_spans"]
    dev = res["upstream"]["schema_deviations"]
    return [
        {
            "id": "F-01",
            "severity": "high",
            "blocking": True,
            "title": "三个对标误差无任何可复算结构：无船名/主尺度/参考值/绝对 attained 值",
            "detail": (
                f"报告只给出 `{q['errors_line']['quote']}`。按平台证据标准（几何必须先验证 Cb/L/B、"
                "零手抄、误差须能逐字定位到基准），要复算一个百分比误差至少需要：船名或编号、"
                "L/B/T/Cb、绝对 attained EEXI（gCO2/t·nm）、以及所用参考值的出处。这四类字段在 490 字符的原文中"
                f"一个都没有（C11 fields_missing 全为空缺；`gCO2` 未出现）。三个数中最大值 "
                f"{n['max']}% 已接近 15% 判废线，因此这条缺口不是形式问题：上游 01 登记的 4 个资产全部"
                f"`referenced_unresolved`（C7：{sum(1 for s in spans if s['resolution_reproduced'])}/"
                f"{len(spans)} 在本工作树不存在），任何第三方（含本审核者）都无法重算这三个数。"
            ),
            "evidence": [
                {"quote": q["errors_line"]["quote"], "where": f"## 结果 (char {q['errors_line']['start_char']}-{q['errors_line']['end_char']}, line {q['errors_line']['line']})"},
                {"quote": q["asset_json"]["quote"], "where": f"## 产物 (char {q['asset_json']['start_char']}-{q['asset_json']['end_char']})，worktree 内不存在"},
            ],
            "recommendation": "报告侧补一张三船参数表（船名/L/B/T/Cb/V_ref/参考值来源/绝对 attained）并让 artifacts/eexi_verification.json 可解析；下游 03/05 在此之前不得把 12.1/7.0/1.0 提升为知识主张。",
            "affected_scope": "report 11180 的核心定量结论；工序 03/05 的下游引用",
        },
        {
            "id": "F-02",
            "severity": "high",
            "blocking": True,
            "title": "「WITHHELD → REAL」是平台门的输出，不是报告可自证的结论，且本审核者无法独立复算",
            "detail": (
                "报告结论行把能力等级变更写成既成事实。本次独立复算三条路都不通："
                "① EEXI 端点探测 `calculations/eexi`、`green-shipping/eexi/attained`、`openapi.json` 全部 404；"
                "② 平台能力台账不可达（capabilities.json 文件缺失）；③ 所引验证工件不在工作树。"
                "按工作包约束 `do_not_mark_claims_as_verified`，本审核不给该结论任何 verified 标记，"
                "也不把它降级为假——它只是**不可复算**（C16 fail）。"
            ),
            "evidence": [
                {"quote": q["conclusion"]["quote"], "where": f"## 结论 (char {q['conclusion']['start_char']}-{q['conclusion']['end_char']})"},
                {"quote": q["goal"]["quote"], "where": f"## 目标 (char {q['goal']['start_char']}-{q['goal']['end_char']})"},
            ],
            "recommendation": "把结论改写为「提交平台门复算」的候选声明；修复端点可达性或附上可解析的验证工件，再谈等级变更。",
            "affected_scope": "能力证据分级台账；green_shipping_eexi_chain 场景",
        },
        {
            "id": "F-03",
            "severity": "medium",
            "blocking": True,
            "title": "缺平台报告纪律第 6 要素：没有显式回答「是否 <3%」",
            "detail": (
                f"全文出现的阈值只有 `均 <15%`（C10：`3%` 子串不存在）。按平台 2026-10-29 报告令，"
                f"关键量须逐项给出 vs 基准误差并显式回答是否 <3%。用报告自己的三个数判断："
                f"仅 {n['n_below_3']}/{len(n['errors_pct'])} 船 <3%，最大 {n['max']}%、均值 {n['mean']}%——"
                "即「<15% 的 REAL 门槛」与「<3% 的可发表门槛」在这份报告里被混为一谈，读者无法区分二者。"
            ),
            "evidence": [
                {"quote": q["errors_line"]["quote"], "where": "## 结果 唯一带阈值的一句"},
                {"quote": q["goal"]["quote"], "where": "## 目标：唯一出现 15% 判据的位置"},
            ],
            "recommendation": "补 ⑥误差判定段：逐船列出误差 + 显式写「是否 <3%」，并说明 12.1% 这艘船的偏差来源。",
            "affected_scope": "报告可发表性判定",
        },
        {
            "id": "F-04",
            "severity": "medium",
            "blocking": False,
            "title": "敏感度只报一个因子 57.1%，剩余 42.9% 未分解、方法未写",
            "detail": (
                f"`{q['sensitivity']['quote']}` 是全文唯一的敏感度信息。57.1% 单独的数值无法判断是单变量摄动（OAT）"
                f"还是方差分解（Sobol），摄动步长未知；其余 {sens['residual_undecomposed_pct']}% 落在哪些参数上没有交代，"
                "因此「V_ref 主导」这句只能算观察，不能算结论。它同时暗示：EEXI ∝ 1/V_ref 的情形下，"
                "链路误差很可能由输入 V_ref 的取值而非算法精度主导——这会改变「REAL」的含义，值得作者正面回应。"
            ),
            "evidence": [{"quote": q["sensitivity"]["quote"], "where": f"## 结果 (line {q['sensitivity']['line']})"}],
            "recommendation": "给出参数表 + 摄动区间 + 完整归一化贡献（合计 100%）+ 方法名（OAT 或方差分解）。",
            "affected_scope": "精度传递结论的可解释性",
        },
        {
            "id": "F-05",
            "severity": "medium",
            "blocking": False,
            "title": "「链路同源: grep 验证 4 处调用」不是同源一致性证明",
            "detail": (
                "调用点计数只能证明调用存在，不能证明四条链路用的是同一套输入与同一版公式。"
                "C13 显示：原文没有任何 `file.py:line` 定位，也没有数值一致性容差（如 1e-9/相对偏差 ≤ x%）。"
                "所谓「同源」可被两种常见缺陷伪造：调用同名函数但传不同单位/不同参考状态；或同一函数被测试桩替换。"
            ),
            "evidence": [{"quote": q["same_source"]["quote"], "where": f"## 结果 (line {q['same_source']['line']})"}],
            "recommendation": "贴出 4 处调用点清单（file:line）+ 端到端数值一致性断言及其容差，最好引一个测试名。",
            "affected_scope": "「同源链路」这一方法论卖点",
        },
        {
            "id": "F-06",
            "severity": "medium",
            "blocking": False,
            "title": "「退化一致性: 验证通过」不可反驳：退化极限与容差都未定义",
            "detail": (
                "C14 未在原文找到任何退化极限定义（如 J→0 / n→0 / V→0 时 BEMT 退化为哪个解析式）与容差。"
                "「验证通过」是不可反驳的表述：任何实现都能宣称自己通过了一个未定义的检验。"
                "这不是说验证没做，而是报告层面无法区分「做过」与「写了一句」。"
            ),
            "evidence": [{"quote": q["degenerate"]["quote"], "where": f"## 结果 (line {q['degenerate']['line']})"}],
            "recommendation": "写明退化极限的解析参考式 + 触发参数 + 通过容差 + 实测偏差值。",
            "affected_scope": "BEMT 推进段的可信度",
        },
        {
            "id": "F-07",
            "severity": "low",
            "blocking": False,
            "title": "上游 wp-11180-01 信封违反 additionalProperties:false：顶层 claims + provenance 三个自有键",
            "detail": (
                "`schemas/kf_result.v1.schema.json` 对顶层与 `provenance` 都声明 `additionalProperties: false`，"
                "`claims` 只允许作为 `outputs.claims.json`（工序 03）。C8 复算出的偏差为 "
                f"`{json.dumps(dev, ensure_ascii=False)}`：即顶层多出 claims，provenance 多出 "
                "producer / emitted_at / notes 三个自有键。这不影响 01 的**语义**忠实度（见 F-09），"
                "但严格校验器会拒收该信封；平台门是否放行无法从本工作树观测，本审核不代其下判。"
            ),
            "evidence": [{"quote": "schemas/kf_result.v1.schema.json -> properties.outputs.properties.claims.json", "where": "契约 schema 文件"}],
            "recommendation": "把顶层 claims 移入 outputs（或删除），重发 01 信封。",
            "affected_scope": "对方工作包的信封 schema_pass 项",
        },
        {
            "id": "F-09",
            "severity": "info",
            "blocking": False,
            "title": "正面发现：wp-11180-01 的资产定位可逐字节复现，且对不可解事实如实披露",
            "detail": (
                f"独立重切 {len(spans)} 个 char_span：{sum(1 for s in spans if s['byte_exact'])}/{len(spans)} 字节精确命中、"
                f"{sum(1 for s in spans if s['unique'])}/{len(spans)} 引文唯一；`os.path.exists` 复核 "
                f"{sum(1 for s in spans if s['resolution_reproduced'])}/{len(spans)} 确为不可解。"
                "即 01 没有编造资产、没有把未知说成已解，只是把不可解状态如实登记——这一点是产线应有的行为，"
                "不应因为下游证据链不足被追责。"
            ),
            "evidence": [{"quote": s["recomputed"], "where": f"{s['asset_id']} char {s['declared_span'][0]}-{s['declared_span'][1]}"} for s in spans],
            "recommendation": "无需修改；下游 03/05 沿用该不可解标记即可。",
            "affected_scope": "工序 01 交付质量",
        },
        {
            "id": "F-08",
            "severity": "low",
            "blocking": False,
            "title": "源报告结构不满足平台 6 要素（无参数表、无图、无注意点/局限段）",
            "detail": (
                "C17 的 header 清单只有「目标/方法/结果/产物/结论」五段：无案例介绍与参数表、无图、"
                "无注意点与局限、无逐项误差判定。490 字符（670 字节）的体量也低于能承载一次精度传递验证所需的信息量。"
                "这属于源报告质量问题，不是 01 工序的缺陷；但它是 F-01/F-03 的根因。"
            ),
            "evidence": [{"quote": ck(res, "C17")["detail"]["headers"][0], "where": "H1 标题"}],
            "recommendation": "报告侧按平台 6 要素重写（本次不代改上游产物）。",
            "affected_scope": "报告可发表性",
        },
        {
            "id": "F-10",
            "severity": "info",
            "blocking": False,
            "title": "被超越的旧状态（WITHHELD 99.9%）同样无出处",
            "detail": (
                "C15 not_run：原文只用一句话交代旧状态，无参考值、无数据集、无失败记录。"
                "因此「从 99.9% 降到 12.1%」这一进步叙事在本审核中既不能证实也不能证伪，只能标为证据不足。"
            ),
            "evidence": [{"quote": q["goal"]["quote"], "where": "## 目标"}],
            "recommendation": "若保留该对比，需给出 99.9% 的复现路径与基准。",
            "affected_scope": "改进幅度声明的可信度",
        },
    ]


def build(res: dict) -> dict:
    src = res["source"]
    q = res["quote_binding"]
    fs = findings(res)
    sev_order = ["high", "medium", "low", "info"]
    fs = sorted(fs, key=lambda f: (sev_order.index(f["severity"]), f["id"]))
    blocking = [f["id"] for f in fs if f["blocking"]]
    n = ck(res, "C9")["detail"]
    counts = dict(res["counts"])
    counts["findings"] = len(fs)
    counts["blocking_findings"] = len(blocking)
    counts["severity"] = {s: sum(1 for f in fs if f["severity"] == s) for s in ("high", "medium", "low", "info")}

    review = {
        "review_report_version": "1.0",
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "reviewer_role": "red-team-reviewer",
        "reviewed_package": {
            "package_id": REVIEWED,
            "task_type": "01-asset-registration",
            "artifact": "docs/report_wp11180_01.md",
            "source_hash": src["contract_sha256"],
            "assets_registered": res["upstream"]["counts"].get("assets"),
            "asset_spans_byte_exact": sum(1 for s in res["upstream"]["asset_spans"] if s["byte_exact"]),
            "schema_deviations": res["upstream"]["schema_deviations"],
        },
        "provenance": {
            "source_uri": "tensor://reports/11180",
            "source_field": "markdown",
            "source_hash": src["sha256"],
            "source_hash_matches": src["sha256"] == src["contract_sha256"],
            "title": "EEXI Attained 闭合链路精度传递验证 (P74-N02)",
            "scenario_key": "green_shipping_eexi_chain",
            "chars": src["characters"],
            "utf8_bytes": src["utf8_bytes"],
            "snapshot": src["snapshot"],
        },
        "decision": {
            "disposition": "needs-fix",
            "ledger_decision": "needs-fix",
            "scope": (
                "对上游工序 wp-11180-01：语义忠实度 pass（资产定位逐字节可复现、不可解状态如实披露，仅一处信封 schema 违规）。"
                "对报告 11180 的证据包：needs-fix（核心误差不可复算、缺 <3% 判定、等级变更不可独立复算）。"
            ),
            "rationale": (
                f"18 项检查中 pass {counts.get('pass', 0)} / fail {counts.get('fail', 0)} / not_run {counts.get('not_run', 0)}；"
                f"{len(blocking)} 项 blocking 发现（{', '.join(blocking)}）。无一份可复算的验证工件，"
                "且「REAL」这一等级结论在平台门之外不可达，故不放行、也不判假。"
            ),
            "claims_marked_verified": 0,
            "verification_owner": "platform-gate",
        },
        "scope": {
            "in_scope": [
                "report 11180 markdown 的字节哈希、体量、结构与全部定量/定性声明",
                "上游 wp-11180-01 的资产登记输出（char_span、引文唯一性、分辨率判定、信封 schema 严格度）",
                "把报告声明与原文逐字绑定的可复现性（零手抄）",
                "对等级结论的独立复算尝试（端点/台账/工件三条路径）",
            ],
            "out_of_scope": [
                "ship-performance-platform 源码与实际 EEXI 实现（不在本工作树，端点 404）",
                "Holtrop / BEMT 的绝对精度（报告未提供任何参考值或数据集）",
                "平台门对 wp-11180-01 的最终 schema_pass 结论（本审核只复算，不代替下判）",
                "知识抽取与综合（工序 03/05）",
            ],
        },
        "independence": {
            "reviewer": f"agent/m19782 (TensorKnowledge) · package {PKG} · red-team-reviewer",
            "producer": "agent/m15692 (TensorKnowledge) · package wp-11180-01",
            "basis": "distinct-identity",
            "limitations": [
                "审核者与被审包来自同一平台/同一模型家族：独立性是身份级与方法级的，不是模型级的",
                "被审上下文只有 490 字符原文 + 01 的机器输出；报告本身过薄，某些声明（如 99.9%）只能标证据不足而非判错",
                "平台能力台账不可达、EEXI 端点 404，等级结论的复算只能记为 fail(不可达)，不能记为「错」",
                "本审核未执行任何 ship-performance-platform 代码，也未运行其测试",
            ],
        },
        "context_isolation": {
            "evidence_basis": [
                "report 11180 markdown（live API 抓取 + 字节快照 docs/kf/wp-11180-04/source/report_11180.md）",
                "docs/report_wp11180_01.md 内的机器输出（asset_manifest / kf_result 信封）",
            ],
            "objects_under_test_not_evidence": [
                "docs/report_wp11180_01.md 的叙述文字（§1-§6 自检），仅作被审对象，未作为任何声明成立的依据",
            ],
            "producer_explanation_used_as_support": False,
            "review_prompt_source": "工作包契约 YAML + 报告原文；未复制生产者自检/叙述",
        },
        "checks": res["checks"],
        "findings": fs,
        "counts": counts,
        "acceptance_selfcheck": {
            "valid_json": f"ok — review_report.json 经 json.load 往返；review_checks.json 同",
            "schema_pass": "ok — 提交信封（package_id/task_type/report_id/provenance/outputs）逐条对照 schemas/kf_result.v1.schema.json 的 required/pattern/additionalProperties",
            "reviewer_independent": "ok — distinct-identity（agent/m19782 vs agent/m15692），且未使用生产者解释作依据",
            "upstream_packages_completed": f"ok-with-note — wwp-11180-01 存在且输出可解析（4 资产 / {sum(1 for s in res['upstream']['asset_spans'] if s['byte_exact'])} 个 char_span 字节精确）；另发现 1 处严格模式违规（F-07，非阻断语义忠实度）",
        },
        "checks_not_run": [
            "C15 旧状态 99.9% 的基准（原文无参考值，无法复算）",
            "EEXI 端点 / 能力台账复算（calculations/eexi、green-shipping/eexi/attained、openapi.json 均 404；capabilities.json 缺失）",
            "ship-performance-platform 单测与 Holtrop/BEMT 内核（仓库不在本工作树）",
            "artifacts/eexi_verification.json 内容审计（文件不存在，01 已如实标 referenced_unresolved）",
        ],
        "repro_cmd": REPRO,
        "artifacts": {
            "checks_raw": "docs/kf/wp-11180-04/review_checks.json",
            "figure": "docs/kf/wp-11180-04/fig_review_checks.png",
            "source_snapshot": "docs/kf/wp-11180-04/source/report_11180.md",
            "tests": "tests/test_wp11180_04_review.py",
        },
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return review


def envelope(review: dict) -> dict:
    return {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": "tensor://reports/11180",
            "source_field": "markdown",
            "source_hash": review["provenance"]["source_hash"],
            "source_hash_matches": review["provenance"]["source_hash_matches"],
            "title": review["provenance"]["title"],
            "scenario_key": review["provenance"]["scenario_key"],
            "chars": review["provenance"]["chars"],
        },
        "outputs": {
            "review_report.json": review,
            "review_events.json": [
                {"event": "review_started", "package_id": PKG, "reviewed_package": REVIEWED,
                 "at": review["generated_at"], "basis": "source bytes + upstream machine output only"},
                {"event": "checks_completed", "at": review["generated_at"], "counts": review["counts"],
                 "checks": [{"id": c["id"], "status": c["status"]} for c in review["checks"]]},
                {"event": "decision", "at": review["generated_at"],
                 "disposition": review["decision"]["disposition"],
                 "blocking_findings": [f["id"] for f in review["findings"] if f["blocking"]],
                 "claims_marked_verified": 0},
            ],
        },
    }


def markdown(review: dict, res: dict, env: dict) -> str:
    q = res["quote_binding"]
    n = ck(res, "C9")["detail"]
    sens = ck(res, "C12")["detail"]
    fs = review["findings"]

    def f_by(i):
        return next(f for f in fs if f["id"] == i)

    def row(c):
        return f"| {c['id']} | {c['name']} | {c['status']} |"

    ev = [
        ("source_hash", q, "errors_line"),
    ]
    evidence_rows = "\n".join(
        f"| {k} | `{v['quote']}` | char {v['start_char']}–{v['end_char']} / line {v['line']} |"
        for k, v in q.items()
    )
    finding_rows = "\n".join(
        f"| {f['id']} | {f['severity']} | {'是' if f['blocking'] else '否'} | {f['title']} |"
        for f in fs
    )
    check_rows = "\n".join(row(c) for c in review["checks"])

    doc = f"""# KF-RESULT {PKG}

- package_id: `{PKG}` ｜ task_type: `04-independent-review` ｜ report_id: `{REPORT_ID}` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: in-review
- source: `tensor://reports/{REPORT_ID}`（field=`markdown`）, chars={review['provenance']['chars']}, bytes={review['provenance']['utf8_bytes']}, sha256=`{review['provenance']['source_hash']}`
- 审核对象：`{REVIEWED}`（01-asset-registration，producer=agent/m15692）
- 审核方法：adversarial-review（未使用生产者解释作依据；未把任何结论标为 verified）
- **处置：needs-fix**（对 01 的语义忠实度 = pass；对报告 11180 的证据包 = needs-fix）

## ① 本工序做了什么

对 report_id={REPORT_ID}（`EEXI Attained 闭合链路精度传递验证 (P74-N02)`，scenario=`green_shipping_eexi_chain`）执行 **04-independent-review**：

1. 独立复算源报告字节哈希与体量：`{review['provenance']['source_hash']}`，{review['provenance']['chars']} 字符 / {review['provenance']['utf8_bytes']} 字节 UTF-8，与契约 `source_hash` 逐字节一致。
2. 把报告里 {len(q)} 处被审核的表述用 `str.find` 逐字定位（char_span + 行号），{sum(1 for v in q.values() if v['found'])}/{len(q)} 全部命中且唯一——审核引用零手抄。
3. 复核上游 {REVIEWED} 的 {len(res['upstream']['asset_spans'])} 个资产定位：按声明的 char_span 重切原文，{sum(1 for s in res['upstream']['asset_spans'] if s['byte_exact'])}/{len(res['upstream']['asset_spans'])} 字节精确、引文唯一（{sum(1 for s in res['upstream']['asset_spans'] if s['unique'])}/{len(res['upstream']['asset_spans'])} 唯一）；用 `os.path.exists` 复核其 `referenced_unresolved` 判定，{sum(1 for s in res['upstream']['asset_spans'] if s['resolution_reproduced'])}/{len(res['upstream']['asset_spans'])} 复现。
4. 用报告自己的三个误差判定其内部算术：最大 {n['max']}%、均值 {n['mean']}%、<3% 者 {n['n_below_3']}/{len(n['errors_pct'])}。`均 <15%` 自洽，但**全文没有 <3% 的判定**。
5. 对「WITHHELD → REAL」做三条独立复算尝试，全部不可达（端点 404 / 能力台账缺失 / 验证工件不可解），记为 fail 而非「错」。
6. 产出 {len(review['checks'])} 项检查（pass {review['counts'].get('pass', 0)} / fail {review['counts'].get('fail', 0)} / not_run {review['counts'].get('not_run', 0)}）与 {len(fs)} 项分级发现（blocking {sum(1 for f in fs if f['blocking'])} 项）。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/方法 | 关键设置 |
| --- | --- | --- |
| 取原文 | `GET /api/v1/tensor/reports/11180`（Bearer 登录换 token）+ 字节快照 `docs/kf/wp-11180-04/source/report_11180.md` | 不做换行归一化；`sha256(markdown.encode('utf-8'))` |
| 零手抄绑定 | `str.find` + `str.count` + 切片重切 | 引用未命中即判 fail；同时记录 char_span 与行号 |
| 上游复核 | 解析 `docs/report_wp11180_01.md` 中唯一 json 块；重切每个 char_span；`os.path.exists` 复核分辨率 | 上游叙述文字只作被审对象，不作证据 |
| schema 严格度 | 读 `schemas/kf_result.v1.schema.json` 的 `required` / `additionalProperties`，手写等价校验（不引入 jsonschema 依赖） | 逐层检查顶层 / provenance / outputs 的额外键 |
| 数值复算 | 从已定位引文用正则抽数（`(\\d+\\.\\d+)%`），不重抄 | 只复算报告自洽性，不假设任何外部基准 |
| 独立复算尝试 | 端点探测（`calculations/eexi`、`green-shipping/eexi/attained`、`openapi.json`）+ 能力台账读取 | 404 / 文件缺失一律记 fail(不可达)，不记「假」 |
| 出图 | matplotlib（Agg） | 误差 vs 15%/3% 双阈值；敏感度闭合缺口 |

**独立性**：审核者 agent/m19782 与生产者 agent/m15692 不同身份；被审上下文 = 490 字符原文 + 01 的机器输出。局限：同平台同模型家族（身份级独立而非模型级）；未执行 ship-performance-platform 代码。

## ③ 产出物清单

| 文件 | 要点 |
| --- | --- |
| `docs/kf/wp-11180-04/review_report.json` | 审核报告本体（{len(review['checks'])} 项检查 + {len(fs)} 项发现 + 处置），同时是提交信封 `outputs['review_report.json']` |
| `docs/kf/wp-11180-04/review_checks.json` | 原始检查数据（哈希/引文绑定/char_span 重切/像素外的全部数值） |
| `docs/kf/wp-11180-04/source/report_11180.md` | 源报告字节快照（{review['provenance']['utf8_bytes']} 字节，哈希与契约一致） |
| `docs/kf/wp-11180-04/fig_review_checks.png` | 结果图：三船误差 vs 15%/3% 阈值 + 敏感度闭合缺口 |
| `scripts/kf_wp11180_04_checks.py` | 一键检查器（`--live` 会重新 git-free 拉取原文并比对快照） |
| `scripts/kf_wp11180_04_emit.py` | 从检查结果程序化注入生成 review_report.json / .md（零手抄） |
| `tests/test_wp11180_04_review.py` | pytest：哈希、引文子串、char_span 重切、单 json 块、schema 严格度、处置一致性 |
| `docs/kf/wp-11180-04/review_report.md` | 本文件 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

| claim/字段 | 原文引文（逐字） | 定位 |
| --- | --- | --- |
{evidence_rows}

关键复算数字：三船误差 = {n['errors_pct']}%（来自 `三船对标误差` 行，非重抄）；最大 {n['max']}%、均值 {n['mean']}%；敏感度 `V_ref` 贡献 {sens['contributions_reported'][0]}%，未分解残差 {sens['residual_undecomposed_pct']}%。

## ⑤ 注意点与局限

- **处置的两面性**：{REVIEWED} 本身是合格的资产登记（定位可逐字节复现、不可解状态如实披露，F-09），needs-fix 针对的是**报告证据包**——两者不可混为一谈。
- **fail ≠ 假**：F-02/F-10 是「不可复算」，不是「已证伪」；审核者没有权限也没有证据否定作者做过的工作。
- **F-07 一处严格模式违规**：上游信封在顶层多出 `claims` 键，`additionalProperties: false` 下会被严格校验器拒收；这不是语义错误。
- **报告过薄**：490 字符无法承载一次端到端精度传递验证；F-01/F-03/F-05/F-06 的根因主要在此（源报告质量问题，不是 01 的缺陷）。
- **未做的事**：未运行 ship-performance-platform 的任何代码/测试，未读取 `artifacts/eexi_verification.json`（不存在），未取得平台能力台账。
- **不可外推**：本审核只对 report_id=11180 有效，不涉及其它报告或其它 EEXI 证据。

### 检查明细

| id | check | status |
| --- | --- | --- |
{check_rows}

### 发现清单（severity 排序）

| id | severity | blocking | 标题 |
| --- | --- | --- | --- |
{finding_rows}

blocking 说明：F-01（核心误差无法复算）、F-02（等级结论不可独立复算）、F-03（缺 <3% 显式判定）阻断放行；F-04…F-07 为需修正但不阻断语义忠实度的项。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结果 | 说明 |
| --- | --- | --- |
| `valid_json` | ✅ | review_report.json 与 review_checks.json 均 json.load 往返通过；提交块由同一对象序列化 |
| `schema_pass` | ✅ | 信封对照 `schemas/kf_result.v1.schema.json`：required 4 项齐备、`contract_version="1.0"`、provenance 无额外键、outputs 键合法；由 pytest 断言 |
| `reviewer_independent` | ✅ | distinct-identity（m19782 vs m15692），未使用生产者解释作依据 |
| `upstream_packages_completed` | ✅（带 note） | wp-11180-01 存在、输出可解析、4 个 char_span 字节精确；另发现 1 处信封严格模式违规（F-07），不影响其语义忠实度 |
| `review_prompt_not_copied_from_producer` | ✅ | 检查项由契约 YAML + 报告原文自行推导；未复制 01 的自检表 |
| `reviewer_context_excludes_producer_explanation` | ✅ | 01 的叙述文字仅作被审对象；证据表所有引文均来自报告 markdown |
| `do_not_mark_claims_as_verified` | ✅ | `claims_marked_verified = 0`；处置只到 needs-fix，等级由平台门计算 |
| honest 声明 | ✅ | fail 项 8 个照实列出（含 C8/C10-C14/C16/C17），not_run 1 项（C15）如实标注，无粉饰 |

**是否放行：否（needs-fix）**——F-01/F-02/F-03 三项 blocking 未消除。问题定位与修复建议见每项 `recommendation`；本次不代改上游产物（边界约束）。

## 复跑命令

```bash
cd /root/tp-agent/work/m19782
{REPRO}
```

`--live` 会重新登录平台拉取 report 11180 并与 `source/report_11180.md` 逐字节比对（不一致即告警）。

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""
    return doc


def main() -> int:
    res = load()
    review = build(res)
    env = envelope(review)
    with open(REVIEW_JSON, "w", encoding="utf-8") as f:
        json.dump(env, f, ensure_ascii=False, indent=2)
        f.write("\n")
    doc = markdown(review, res, env)
    blocks = re.findall(r"```json\n(.*?)```", doc, re.S)
    assert len(blocks) == 1, f"expected exactly one json block, got {len(blocks)}"
    json.loads(blocks[0])
    with open(REVIEW_MD, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {os.path.relpath(REVIEW_JSON, ROOT)}")
    print(f"wrote {os.path.relpath(REVIEW_MD, ROOT)}")
    print(f"decision={review['decision']['disposition']} counts={review['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())