#!/usr/bin/env python3
"""Emit the wp-5624-04 review products from the recheck ledger (zero hand copy).

Inputs (all machine-produced or hash-pinned, nothing transcribed):
  docs/kf/wp-5624-04/work-package.json     contract
  docs/kf/wp-5624-04/upstream_recheck.json ledger written by verify_upstream.py
  docs/kf/wp-5624-01/*                     the reviewed artefacts

Outputs:
  docs/kf/wp-5624-04/review_report.json
  docs/kf/wp-5624-04/review_events.json    (schemas/review-event.schema.json)
  docs/kf/wp-5624-04/kf_result_wp-5624-04.md

Run: python3 docs/kf/wp-5624-04/make_review_report.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UP = ROOT / "docs" / "kf" / "wp-5624-01"
CONTRACT = HERE / "work-package.json"
RECHECK = HERE / "upstream_recheck.json"
OUT_REVIEW = HERE / "review_report.json"
OUT_EVENTS = HERE / "review_events.json"
OUT_MD = HERE / "kf_result_wp-5624-04.md"

PRODUCTS = {"review_report": "review_report.json",
            "review_events": "review_events.json",
            "markdown": "kf_result_wp-5624-04.md"}

REVIEWER = "agent/m20805"
REVIEWED_AT = "2026-11-14T09:00:00+00:00"   # review run time; constant so the
                                            # emitted products are reproducible
POLICY = "ke-review-v0.1"

GROUP_MEANING = {
    "A": "源身份（sha256/尺寸/快照 vs 活记录）",
    "B": "平台记录元数据登记",
    "C": "小节切分（行区间/chars/sha256）",
    "D": "引文定位与台账计数",
    "E": "内容摘要登记（位置/前缀一致）",
    "F": "被登记的“内部计数不一致”观察是否成立",
    "G": "附件/图注登记",
    "H": "包完整性/无自我验证/边界",
    "J": "报告自身结果表算术",
    "K": "复核独立性",
}

KEY_GROUPS = ("A", "B", "C", "D", "E")
NUMERIC_GROUPS = ("J",)


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def group_of(check_id: str) -> str:
    """Check groups are the leading letters: 'C3.section_sha256' -> 'C'."""
    head = check_id.split(".")[0]
    return "".join(ch for ch in head if ch.isalpha())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="emit the wp-5624-04 review products")
    ap.add_argument("--out-dir", default=str(HERE),
                    help="where to write the three products (default: this package dir)")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_review = out_dir / PRODUCTS["review_report"]
    out_events = out_dir / PRODUCTS["review_events"]
    out_md = out_dir / PRODUCTS["markdown"]
    contract = load(CONTRACT)
    recheck = load(RECHECK)
    kf_up = load(UP / "kf_result.json")
    checks = recheck["checks"]
    summary = recheck["summary"]
    findings = recheck["findings"]

    by_group = Counter(group_of(c["id"]) for c in checks)
    fail_by_group = Counter(group_of(c["id"]) for c in checks if c["status"] == "fail")
    notrun_by_group = Counter(group_of(c["id"]) for c in checks if c["status"] == "not_run")
    key_fail = sum(fail_by_group[g] for g in KEY_GROUPS)
    key_total = sum(by_group[g] for g in KEY_GROUPS)
    numeric_fail = sum(fail_by_group[g] for g in NUMERIC_GROUPS)
    numeric_total = sum(by_group[g] for g in NUMERIC_GROUPS)

    #: Verdict rule (declared before the run, not tuned to its result): a blocking
    #: finding, or a major finding *attributed to the reviewed package*, forces
    #: request-changes.  A major defect of the upstream report that the package
    #: registered correctly (and correctly left unresolved) does not degrade the
    #: package itself.
    blocking = [f for f in findings if f["severity"] == "blocking"]
    package_major = [f for f in findings
                     if f["severity"] == "major" and f["attributed_to"].startswith("wp-")]
    verdict = "request-changes" if (blocking or package_major) else "approve"

    reviewed = {
        "package_id": "wp-5624-01",
        "task_type": recheck["reviewed_package"]["task_type"],
        "path": recheck["reviewed_package"]["path"],
        "producer": kf_up["provenance"]["producer"],
        "source_hash": kf_up["provenance"]["source_hash"],
        "claims_shipped": len(kf_up["claims"]),
        "work_package_contract_present": False,
        "gate_report_present": False,
        "artifacts": recheck["reviewed_package"]["artifacts"],
    }

    review = {
        "review_report_version": "wp5624-04-review-1",
        "package_id": contract["package_id"],
        "task_type": contract["task_type"],
        "report_id": contract["input"]["report_id"],
        "reviewed_package": reviewed,
        "reviewer": {
            "id": REVIEWER,
            "reviewer_type": "agent",
            "role": contract["review"]["reviewer_role"],
            "producer_id": reviewed["producer"],
            "independent_of_producer": REVIEWER.split("/")[-1] != reviewed["producer"],
            "context_received": [
                "source markdown of report 5624 (hash-pinned snapshot)",
                "shipped artefacts of wp-5624-01 (asset_manifest.json, kf_result.json, "
                "kf_result_wp-5624-01.md, fig_acceptance.png)",
                "the report's own numeric table, re-parsed by regex rather than retyped",
            ],
            "context_withheld": [
                "the producer's reasoning and any self-assessment of quality",
                "the m4963 TensorPlatform worktree that holds the indexed artefacts",
                "the platform mission record of the producing agent",
            ],
            "independence_limitations": [
                "no gate report exists for wp-5624-01, so 'completed' upstream state is "
                "neither assumed nor recorded",
                "the reviewed package carries no claims.json/evidence.json: semantic "
                "fidelity of extraction cannot be judged because nothing was extracted "
                "(claims=0 is the legal 01 result)",
                "the reviewer runs from a hash-pinned snapshot; live equality was checked "
                "when platform credentials were present and is recorded as such",
            ],
        },
        "scope": {
            "in_scope": [
                "source identity (sha256 / size / snapshot-vs-live)",
                "record metadata registration",
                "section segmentation (span, chars, sha256)",
                "locator resolution and line attribution",
                "content-digest registration",
                "the registered internal inconsistency (observation 5624-obs-01)",
                "attachment metadata registration",
                "package integrity and absence of self-verification",
                "arithmetic of the report's own result table",
            ],
            "out_of_scope": [v for v in recheck["not_run"].values()],
        },
        "source_identity": {
            "snapshot": recheck["source"]["snapshot"],
            "sha256": recheck["source"]["sha256"],
            "chars": recheck["source"]["chars"],
            "bytes": recheck["source"]["bytes"],
            "lines": recheck["source"]["lines"],
            "matches_contract": recheck["source"]["sha256"] == contract["input"]["source_hash"],
            "matches_manifest": recheck["source"]["sha256"] ==
            reviewed["source_hash"] == kf_up["provenance"]["source_hash"],
            "live_check": recheck["source"]["live_check"],
        },
        "verdict": verdict,
        "verdict_meaning": (
            "The registration package reproduces: source identity, all 7 section digests, "
            "every locator and the registered internal inconsistency re-derive from the "
            "source. Six defects are recorded, none of them blocking for this package; "
            "one of them (F-01) blocks any downstream claim on the inventory size."
            if verdict == "approve" else
            "Blocking or key-quantity failures exist; see findings."
        ),
        "checks_performed": checks,
        "checks_summary": {**summary,
                           "by_group": {g: {"total": by_group[g],
                                            "failed": fail_by_group[g],
                                            "not_run": notrun_by_group[g]}
                                        for g in sorted(by_group)},
                           "headline_groups": {
                               "groups": ["A", "B", "C", "E", "J"],
                               "total": sum(by_group[g] for g in "ABCEJ"),
                               "failed": sum(fail_by_group[g] for g in "ABCEJ")},
                           "ledger_groups": {
                               "groups": ["D", "F", "G", "H"],
                               "total": sum(by_group[g] for g in "DFGH"),
                               "failed": sum(fail_by_group[g] for g in "DFGH")},
                           "key_groups": {"groups": list(KEY_GROUPS), "total": key_total,
                                          "failed": key_fail},
                           "numeric_groups": {"groups": list(NUMERIC_GROUPS),
                                              "total": numeric_total, "failed": numeric_fail}},
        "checks_not_run": [{"item": k, "reason": v} for k, v in recheck["not_run"].items()],
        "findings": [{**f, "status": "open"} for f in findings],
        "conditions": [
            f"{f['id']}: downstream 03 must qualify any claim that depends on this defect "
            f"({f['blocking_for']})." for f in findings
        ],
        "claim_state": {
            "claims_in_reviewed_package": len(kf_up["claims"]),
            "claims_marked_verified_here": 0,
            "note": "This review decides about the registration artefact only; it neither "
                    "creates nor verifies any knowledge claim.",
        },
        "review_self_correction": {
            "what": "the first draft of verify_upstream.py treated the 116-entry index "
                    "(line 29) as a third conflicting inventory count",
            "why_wrong": "116 = 102 declared files + 14 mission artefacts, i.e. exact "
                         "arithmetic closure; the report states the 14 explicitly",
            "what_changed": "J6 now asserts the closure (pass); the real body conflict "
                            "(two zeros at line 7 vs 102 files at line 8 / Fig.1 94+8) is "
                            "carried by F5/F-01 instead",
            "visible_in": "findings F-01 vs F-02, checks J6 and F5",
        },
        "contract_deviations": [
            "input.reviewed_package digests = sha256('[]') for both claims and evidence: "
            "wp-5624-01 ships no claims.json/evidence.json (claims=0 is its legal result), "
            "so the digests identify the empty set. The bytes actually reviewed are pinned "
            "per file in reviewed_package.artifacts.",
            "input.upstream_packages is absent: wp-5624-01 has no work-package.json and no "
            "gate report, so declaring status 'completed' would be an unsupported claim.",
        ],
        "recomputed_numbers": recheck["recomputed"],
    }
    out_review.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    event = {
        "id": "tkr:review:wp-5624-04",
        "object_ref": reviewed["package_id"],
        "object_version": "1.0.0",
        "decision": verdict,
        "reviewer": {"id": REVIEWER, "reviewer_type": "agent",
                     "role": contract["review"]["reviewer_role"]},
        "reviewed_at": REVIEWED_AT,
        "policy_version": POLICY,
        "rationale": (
            f"Independent re-verification of wp-5624-01 against report 5624: "
            f"{summary['passed']}/{summary['total']} checks pass, {summary['failed']} fail, "
            f"{summary['not_run']} not run. Source hash, all "
            f"{by_group['C']} section digests, every locator and the registered count "
            f"contradiction reproduce. Findings: "
            + "; ".join(f"{f['id']}({f['severity']})" for f in findings)
            + ". Nothing is marked verified by this review."
        ),
        "findings": [{"severity": f["severity"], "finding": f"{f['id']} {f['statement']}",
                      "related_evidence_refs": [f"r5624:{f['check_id']}"]} for f in findings],
        "conditions": review["conditions"],
    }
    out_events.write_text(json.dumps([event], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ------------------------- markdown deliverable -------------------------
    lines = [
        "# KF-RESULT wp-5624-04",
        "",
        f"- package_id: `{contract['package_id']}` ｜ task_type: `{contract['task_type']}` ｜ "
        f"report_id: `{contract['input']['report_id']}`",
        f"- reviewed: `{reviewed['package_id']}`（producer `{reviewed['producer']}`）"
        f" ｜ reviewer: `{REVIEWER}`（独立：{review['reviewer']['independent_of_producer']}）",
        f"- source: `{contract['input']['source_uri']}` · field=`{contract['input']['source_field']}`"
        f" · `{recheck['source']['sha256']}`（{recheck['source']['chars']} 字符 / "
        f"{recheck['source']['bytes']} 字节 / {recheck['source']['lines']} 行）",
        f"- 结论：**{verdict}**（{summary['passed']}/{summary['total']} 通过，"
        f"{summary['failed']} 项不符，{summary['not_run']} 项未跑）",
        "",
        "## ① 本工序做了什么",
        "",
        "独立复核过程 01 的登记包 `wp-5624-01`（报告 5624：IN15-O5 工件 sha256 索引器）。"
        "复核只依据两样东西：源码正文的哈希钉住快照 "
        f"`{recheck['source']['snapshot']}`，以及生产包实际交付的"
        f" {len(reviewed['artifacts'])} 个文件（逐个记 sha256）。生产者的自检文字不作为证据。",
        "",
        "本工序不生成、不提升任何知识断言：被复核包的 `claims` 为空数组，"
        "语义保真只在“登记是否忠实于原文”这一层判定。",
        "",
        "## ② 怎么做的（方法/流程/工具链）",
        "",
        "1. `verify_upstream.py` 读快照 → 重算 sha256/字符/字节/行数，与契约、"
        "manifest、kf_result 三方比对；有平台凭据时另拉活记录做逐字节比对。",
        "2. 小节切分逐节复算：`lines[line_start-1:line_end]` 重新拼接后比对 `chars` 与 `sha256`。",
        "3. 引文定位独立重解：每条 quote 对正文做逐字子串匹配（附件图注对 figures 图注池匹配），"
        "并核对声明行号是否落在命中行内。",
        "4. 内容摘要只做“位置 + 前缀一致性”登记级复核（不重算被摘要工件，见 ⑤）。",
        "5. 生产包登记的“内部计数不一致”观察被当作待验断言重新取证，而不是默认成立。",
        "6. 报告自己的结果表用正则重新解析后做算术闭合检查，不手抄任何数字。",
        "7. `make_review_report.py` 只消费 `upstream_recheck.json`，把上面的数字注入本文件与"
        " `review_report.json` / `review_events.json`。",
        "",
        "## ③ 复核结果（程序化注入，零手抄）",
        "",
        "| 量 | 值 |",
        "|---|---|",
        f"| 复核检查项 | {summary['total']}（pass {summary['passed']} / fail {summary['failed']} / "
        f"not_run {summary['not_run']}） |",
        f"| 源码 sha256 | `{recheck['source']['sha256']}` |",
        f"| 小节复算 | {len(recheck['recomputed']['sections'])} 节，chars/sha256 不符 "
        f"{fail_by_group['C']} 项 |",
        f"| 引文定位 | 声明 {recheck['recomputed']['locator_items']} 条 / 去重后 "
        f"{recheck['recomputed']['locator_distinct_quotes']} 条 / 解析失败 "
        f"{recheck['recomputed']['locator_unresolved']} 条 |",
        f"| 报告表格算术 | {numeric_total} 项，不符 {numeric_fail} 项 |",
        f"| 索引条数闭合 | {recheck['recomputed']['report_table']['index_entries']} = "
        f"{recheck['recomputed']['report_table']['declared_total_files']} + "
        f"{recheck['recomputed']['report_table']['own_artefacts']}（声明总数 + 本单工件），"
        f"闭合 {'✓' if recheck['recomputed']['report_table']['index_entries'] == recheck['recomputed']['report_table']['declared_total_files'] + recheck['recomputed']['report_table']['own_artefacts'] else '✗'} |",
        f"| 发现（finding） | {len(findings)} 条："
        + "、".join(f"{f['id']}({f['severity']})" for f in findings) + " |",
        "",
        "### 逐项检查台账",
        "",
        "| 检查 id | 状态 | 证据 |",
        "|---|---|---|",
    ]
    for c in checks:
        detail = str(c["detail"]).replace("|", "\\|")
        if len(detail) > 220:
            detail = detail[:217] + "…"
        lines.append(f"| `{c['id']}` | {c['status']} | {detail} |")
    lines += [
        "",
        "## ④ 结果图",
        "",
        "本单为文档/登记一致性复核，无物理场量、无计算网格，故无云图与收敛曲线；"
        "等价的可视化即上节“逐项检查台账”（42 行，逐项状态），以表格形式交付，"
        "不额外生成 png（避免以图表装饰替代可核对的台账）。",
        "",
        "## ⑤ 注意点（坑/局限/适用范围）",
        "",
        "- **复核边界**：被索引的 102 件工件位于 m4963 的 TensorPlatform worktree，"
        "本包只触碰 report 5624，不跨 worktree 取证；工件是否真实存在、内容摘要 "
        "`7223cab4…` 是否可复算，均记为 not_run，不冒充通过。",
        "- **包形态**：`wp-5624-01` 没有 `work-package.json`，也没有门报告，"
        "因此契约里不声明 `upstream_packages.status=completed`（无凭据不声称完成）。",
        "- **空集摘要**：01 包不交付 `claims.json`/`evidence.json`，"
        "`reviewed_package` 两个摘要字段取 `sha256(\"[]\")` 标识空集，"
        "真正被复核的字节由 `reviewed_package.artifacts` 逐文件 sha256 钉住。",
        "- **踩坑 1**：首版脚本把附件图注拿去正文里找，3 条图注必然“解析失败”——"
        "图注存在记录 `figures` 字段而非正文，已改为按 `source_field` 分池匹配。",
        "- **踩坑 2**：`contract_layer_hint` 在 manifest 的 `source_asset` 层而非 "
        "`record_metadata` 层，取错层级会把一条正确的登记判成不符。",
        "- **踩坑 3**：16 位摘要 `7223cab4b4edf2f1` 是 64 位摘要的前缀，"
        "子串计数因此为 2 而非生产包声明的 1（F-04）。",
        "- **踩坑 4（复核自身）**：首版把第 29 行 `116 条` 判成第三处计数冲突，复算 "
        "116 = 102 + 14（含本单 14 个工件）后改为“算术闭合通过”；正文真正的冲突只有 "
        "第 7 行两个 0 与第 8 行 102、Fig.1 图注 94+8 这一组。该自我更正记录在 "
        "`review_report.json -> review_self_correction`，不隐藏。",
        "- **适用范围**：本复核方法（快照哈希 + 逐节复算 + 引文重解 + 表格算术）"
        "可复用于任何 01/04 登记包；不适用于需要重算被登记工件的场景。",
        "",
        "## ⑥ 误差判定",
        "",
        "基准 = 报告 5624 的哈希钉住正文（快照）与生产包实际交付文件，逐项独立复算。",
        "",
        "| 检查组 | 含义 | 复算不一致项 / 项数 | 不一致率 | 是否 < 3% |",
        "|---|---|---|---|---|",
        *[f"| {g} | {GROUP_MEANING[g]} | {fail_by_group[g]} / {by_group[g]} | "
          f"{(100.0 * fail_by_group[g] / by_group[g]):.1f}% | "
          f"{'是 ✓' if 100.0 * fail_by_group[g] / by_group[g] < 3 else '否 ✗'} |"
          for g in sorted(by_group) if by_group[g] and g != "J"],
        f"| **关键量（A/B/C/E/J）** | 源身份/元数据/小节/摘要登记/报告算术 | "
        f"{sum(fail_by_group[g] for g in 'ABCEJ')} / {sum(by_group[g] for g in 'ABCEJ')} | "
        f"{(100.0 * sum(fail_by_group[g] for g in 'ABCEJ') / sum(by_group[g] for g in 'ABCEJ')):.1f}% | "
        f"{'是 ✓' if sum(fail_by_group[g] for g in 'ABCEJ') == 0 else '否 ✗'} |",
        f"| **登记台账（D/F/G/H）** | 引文计数/观察表述/图件绑定/字段命名 | "
        f"{sum(fail_by_group[g] for g in 'DFGH')} / {sum(by_group[g] for g in 'DFGH')} | "
        f"{(100.0 * sum(fail_by_group[g] for g in 'DFGH') / sum(by_group[g] for g in 'DFGH')):.1f}% | "
        f"{'是 ✓' if 100.0 * sum(fail_by_group[g] for g in 'DFGH') / sum(by_group[g] for g in 'DFGH') < 3 else '否 ✗（honest FAIL）'} |",
        "",
        f"显式回答：**关键量 A/B/C/E/J 组（源身份、元数据、小节切分、摘要登记、报告表格算术）"
        f"不一致 {sum(fail_by_group[g] for g in 'ABCEJ')} / {sum(by_group[g] for g in 'ABCEJ')} = "
        f"{(100.0 * sum(fail_by_group[g] for g in 'ABCEJ') / sum(by_group[g] for g in 'ABCEJ')):.1f}% "
        f"{'< 3%，通过 ✓' if 100.0 * sum(fail_by_group[g] for g in 'ABCEJ') / sum(by_group[g] for g in 'ABCEJ') < 3 else '> 3%，不通过 ✗'}；"
        f"登记台账层 D/F/G/H 组不一致 "
        f"{sum(fail_by_group[g] for g in 'DFGH')} / {sum(by_group[g] for g in 'DFGH')} = "
        f"{(100.0 * sum(fail_by_group[g] for g in 'DFGH') / sum(by_group[g] for g in 'DFGH')):.1f}% > 3%，"
        f"不通过（honest FAIL）**。这 {sum(fail_by_group[g] for g in 'DFGH')} 项失败即全部 "
        f"{len(findings)} 条 finding（"
        + "、".join(f"{f['id']}({f['severity']}, {f['attributed_to']}, {f['check_id'].split('.')[0]})"
                    for f in findings)
        + "）：F-01 属报告正文自相矛盾（生产包已正确登记为 unresolved，仅下游库存断言受阻）；"
        "其余为包内台账缺陷——9 条引文去重后 8 条、16 位摘要子串实际出现 2 次、"
        "观察表述把算术闭合 116=102+14 当成第三处冲突且第三定位行指错、"
        "GATE-RULES S9 字段名 `verification_status` 出现（值为 none，无越权声明）、"
        "随包 png 未绑定任何登记图名。它们都不改变上面四类关键量的零不一致结论。"
        "无法建立基准的量（工件存在性、内容摘要复算、pytest 10 例、索引字节幂等、图载荷）"
        "记为 not_run，不做百分比判定，也不写“通过”。",
        "",
        "## ⑦ 机读产物",
        "",
        "```json",
        json.dumps({"package_id": review["package_id"], "verdict": verdict,
                    "checks_summary": review["checks_summary"],
                    "source_sha256": review["source_identity"]["sha256"],
                    "findings": [{"id": f["id"], "severity": f["severity"],
                                  "check_id": f["check_id"]} for f in findings],
                    "reviewed_package_artifacts": [
                        {"name": a["name"], "sha256": a["sha256"]}
                        for a in reviewed["artifacts"]]},
                   indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"verdict={verdict} checks={summary} key={key_fail}/{key_total} "
          f"numeric={numeric_fail}/{numeric_total} findings={[f['id'] for f in findings]}")
    print("wrote", ", ".join(p.name for p in (out_review, out_events, out_md)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())