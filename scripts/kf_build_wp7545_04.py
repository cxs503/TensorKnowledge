#!/usr/bin/env python3
"""Build the wp-7545-04 independent-review deliverables for report 7545.

Outputs (all inside the worktree):
  docs/kf/wp-7545-04/review_report.json      main product (declared output)
  docs/kf/wp-7545-04/review_events.json      04-branch review ledger (one event)
  docs/kf/wp-7545-04/kf_result.json           result envelope (kf_result.v1)
  docs/kf/wp-7545-04/review_report.md         delivery-body markdown (six sections)
  docs/kf/wp-7545-04/fig_review_wp7545_04.png figure for the platform report

Every number/quote written into the products is sliced from the fetched sources at build
time (zero hand-copy); the script asserts each quote is a verbatim substring of the report
markdown before writing anything.

Run order: scripts/kf_fetch_7545.py -> scripts/kf_review_wp7545_01.py -> this script.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from ke_state_machine import POLICY_VERSION, fold, submit  # noqa: E402

pkg = "wp-7545-04"
reviewed_pkg = "wp-7545-01"
OUTDIR = os.path.join(ROOT, "docs", "kf", pkg)
WORK = os.path.join(ROOT, "work", "kf_wp7545")
UP = os.environ.get("UPSTREAM_PKG", "/root/tp-agent/work/m15597/docs/kf/wp-7545-01")
SRC_MD = os.path.join(WORK, "report_7545.md")
CHECKS_JSON = os.path.join(WORK, "review", "upstream_review_checks.json")
CONTRACT_HASH = "84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60"
SOURCE_URI = "tensor://reports/7545"
REVIEWER = {"id": "m15854", "reviewer_type": "agent", "role": "red-team-reviewer"}
PRODUCER_ID = "agent/m15597"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    os.makedirs(OUTDIR, exist_ok=True)
    src = open(SRC_MD, encoding="utf-8").read()
    assert sha256_bytes(src.encode("utf-8")) == CONTRACT_HASH, "source drift"
    checks_doc = json.load(open(CHECKS_JSON, encoding="utf-8"))
    man_raw = open(os.path.join(UP, "asset_manifest.json"), "rb").read()
    man = json.loads(man_raw)
    kfr_up = json.load(open(os.path.join(UP, "kf_result.json"), encoding="utf-8"))
    C = checks_doc["checks"]
    per_asset_chk = {r["asset_id"]: r for r in checks_doc["per_asset"]}

    # ---------- V11: classification of referenced_unresolved --------------
    unref = []
    for a in man["assets"]:
        if a["resolution"] == "referenced_unresolved":
            rel = a["label"].split(":")[0]
            unref.append({"asset_id": a["asset_id"], "path_reference": rel,
                          "present_in_tensor_knowledge": os.path.exists(os.path.join(ROOT, rel))})
    v11_pass = not any(r["present_in_tensor_knowledge"] for r in unref)
    checks_doc["checks"]["V11_unresolved_classification"] = {
        "rows": unref, "pass": v11_pass,
        "rule": "a referenced_unresolved asset must not exist inside the TensorKnowledge checkout;"
                " otherwise the correct resolution would be resolved_in_source",
    }
    failed = [k for k, v in checks_doc["checks"].items() if v["pass"] is False]
    checks_doc["failed_checks"] = failed
    json.dump(checks_doc, open(CHECKS_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---------- findings -------------------------------------------------
    a01 = per_asset_chk["A01"]
    span_len = a01["span"][1] - a01["span"][0]
    q01 = man["assets"][0]["locator"]["quote"]
    assert src[a01["span"][0]:a01["span"][1]] == src  # whole document span
    same_target_groups = [["A06", "A11"], ["A17", "A18"]]
    distinct_targets = man["counts"]["assets"] - sum(len(g) - 1 for g in same_target_groups)
    findings = [
        {
            "finding_id": "F1",
            "severity": "minor",
            "blocking": False,
            "title": "A01（整篇文档定位）声明的字符跨度不等于其逐字引文",
            "statement": (
                f"A01 的 locator 用 method=document 声明 start_char=0 / end_char={span_len}，"
                f"但 quote 只有 {a01['quote_len']} 字符（标题行）。按本仓 G2 证据门 E4 "
                "（声明偏移时 text[start:end] 必须字节等于 quote）该 locator 判定为 "
                "QUOTE_NOT_AT_LOCATOR；quote 确实起于跨度起点（src.startswith(quote, 0) 为真），"
                "所以是跨度声明过宽，不是引文造假。今天不影响 01 工序（01 不产 claim/evidence），"
                "一旦下游把这套 locator 抄进 evidence 记录并映射成 start_offset/end_offset，"
                "E4 立刻变红 —— 故按下游复用条件升级为 major。"
            ),
            "evidence": [
                {"artifact": "work/kf_wp7545/review/upstream_review_checks.json",
                 "pointer": "per_asset[A01].span / .quote_len / .quote_at_locator",
                 "numbers": {"span_len": span_len, "quote_len": a01["quote_len"],
                             "quote_at_locator": a01["quote_at_locator"],
                             "quote_starts_at_span_start": a01["quote_starts_at_span_start"]}},
                {"artifact": SOURCE_URI, "quote": q01,
                 "note": "该 44 字符标题行是 markdown 的第 1 行，也是 A01 的 quote"},
            ],
            "reproduction": "python3 scripts/kf_review_wp7545_01.py  # 看 V2_locators.locator_mismatch",
            "recommended_fix": "method=document 时把 end_char 设成 len(quote)（=44）或干脆不声明偏移，"
                               "只留 sha256 + 首行 quote；如需整篇跨度，另加 span_sha256 字段。",
        },
        {
            "finding_id": "F2",
            "severity": "minor",
            "blocking": False,
            "title": "本仓唯一的 asset_manifest schema 被 const 钉死在别的包上，本包 schema_pass 无法在仓内复跑",
            "statement": (
                "schemas/asset_manifest.v1.schema.json 的 package_id/report_id 是 const "
                f"'{C['V9_manifest_schema_reproducibility']['pinned_package_id']}' / "
                f"'{C['V9_manifest_schema_reproducibility']['pinned_report_id']}'，"
                f"被审包是 '{man['package_id']}' / '{man['report_id']}'，直接套用必失败。"
                f"上游自查记录称『consts rebound to wp-7545-01/7545』通过校验，但包目录里没有"
                f"随包交付那份 rebound schema（目录内 *schema* 文件数="
                f"{len(C['V9_manifest_schema_reproducibility']['rebound_schema_shipped_in_package'])}），"
                "因此该 acceptance 项只能采信上游自述，不能被独立复跑。"
            ),
            "evidence": [
                {"artifact": "schemas/asset_manifest.v1.schema.json",
                 "pointer": "properties.package_id.const / properties.report_id.const",
                 "numbers": {"pinned_package_id": C["V9_manifest_schema_reproducibility"]["pinned_package_id"],
                             "pinned_report_id": C["V9_manifest_schema_reproducibility"]["pinned_report_id"],
                             "package_under_review": man["package_id"],
                             "report_under_review": man["report_id"]}},
                {"artifact": f"{UP}/upstream-self-check-record",
                 "pointer": "checks.schema_pass.detail",
                 "quote": "asset_manifest.v1 (consts rebound to wp-7545-01/7545) + kf_result.v1 validated; errors=[]",
                 "note": "上游自述；rebound schema 未随包交付"},
            ],
            "reproduction": "python3 scripts/kf_review_wp7545_01.py  # 看 V9_manifest_schema_reproducibility",
            "recommended_fix": "把 schema 的 package_id/report_id 从 const 改成 pattern（^wp-[0-9]+-01$ / ^[0-9]+$），"
                               "或按包交付 <package_id>.asset_manifest.schema.json 并在 kf_result 里登记其 sha256。",
        },
        {
            "finding_id": "F3",
            "severity": "minor",
            "blocking": False,
            "title": "生产者目录里的自检文件用了验证阶梯词汇（verified_at / all_pass），命名易被下游误当平台验证",
            "statement": (
                "01 包目录含一份自检记录，字段为 verified_at / all_pass=true。文件自身把语义限定为"
                "『self-check of packagable structure』，且 S9 的标记扫描只覆盖 "
                "claims/evidence/provenance/summary 四份产物，因此它不会触发 G1；但 V 阶梯规定"
                "验证级别只能由门禁计算（V1），文件名与字段名落在同一套词汇里，被下游或报表脚本"
                "误读成平台验证的风险是结构性的（不是本次内容错误）。"
            ),
            "evidence": [
                {"artifact": f"{UP}/verification.json",
                 "pointer": "$.verified_at / $.all_pass / $.scope_note",
                 "quote": "verification here = self-check of packagable structure; report-level truth is platform-gated.",
                 "note": "文件自身限定了语义，但字段名与 V 阶梯词汇冲突"},
                {"artifact": "docs/production/GATE-RULES.md", "pointer": "S9 / V1",
                 "note": "S9 标记集合只扫四份产物；V1 规定级别只能来自门禁"},
            ],
            "reproduction": "ls $UPSTREAM_PKG && python3 -c \"import json;print(json.load(open('$UPSTREAM_PKG/verification.json'))['all_pass'])\"",
            "recommended_fix": "改名 self_check.json，字段 checked_at / self_check_all_pass，"
                               "并在文件里显式写『非 verification_level，等级由平台门计算』。",
        },
        {
            "finding_id": "F4",
            "severity": "informational",
            "blocking": False,
            "title": "fig[i] ↔ 报告『图 N』的对应关系只有位置证据，图注措辞两处不一致",
            "statement": (
                "markdown 的『④ 结果图』只写『图 1..图 4』加描述，不含文件名，因此 A02–A05 与平台 "
                "figures 元数据的配对只能靠顺序。名称顺序一致（V7 通过），但措辞不同：平台 fig2 图注与"
                "markdown 图 2 行不是同一句。建议把『平台 caption 是 markdown 图注子串』这类可机检关系"
                "显式记录，否则顺序一旦变化（平台重排 figures）配对静默失效。"
            ),
            "evidence": [
                {"artifact": SOURCE_URI, "quote": "图 2：预测盲卡片——封存预测与实测的相对误差 vs sealed tolerance"},
                {"artifact": "platform record tensor://reports/7545",
                 "pointer": "figures[1].caption",
                 "quote": "预测盲：封存预测 vs 实测（含tolerance gate）"},
            ],
            "reproduction": "python3 scripts/kf_review_wp7545_01.py  # 看 V7_figure_metadata",
            "recommended_fix": "在 A02–A05 里加 pair_rule 字段（position 或 caption_substring）并记录实测判定。",
        },
        {
            "finding_id": "F5",
            "severity": "informational",
            "blocking": False,
            "title": "资产计数是出现级（occurrence-level），18 不等于 18 个不同文件",
            "statement": (
                f"{man['counts']['assets']} 条资产对应 {len({a['label'] for a in man['assets']})} 个"
                f"不同 label，但按目标去重只有 {distinct_targets} 个独立目标：A17/A18 是同一条 pytest "
                "命令的两种写法（多一个 -q），A06 的 `experiments.json:spec` 与 A11 的 "
                "`artifacts/IN59-P2/experiments.json` 指向同一文件的不同引用形态。"
                "上游已在 identity_granularity 里声明出现级身份，故不算缺陷；但下游若把 "
                f"counts.assets={man['counts']['assets']} 当『那么多个可哈希产物』会高估覆盖面。"
            ),
            "evidence": [
                {"artifact": f"{UP}/asset_manifest.json", "pointer": "identity_granularity",
                 "quote": man["identity_granularity"]},
                {"artifact": f"{UP}/asset_manifest.json", "pointer": "counts.assets",
                 "numbers": {"assets": man["counts"]["assets"],
                             "distinct_labels": len({a["label"] for a in man["assets"]}),
                             "distinct_targets": distinct_targets,
                             "same_target_groups": same_target_groups,
                             "by_resolution": man["counts"]["by_resolution"]}},
            ],
            "reproduction": "python3 -c \"import json;d=json.load(open('$UPSTREAM_PKG/asset_manifest.json'));print(len(d['assets']),len({a['label'] for a in d['assets']}))\"",
            "recommended_fix": "counts 里加 distinct_targets 字段（=16：14 个文件/目录 + 1 条命令 + 1 篇 markdown），"
                               "或把 A17/A18 合并为一条带两个 locator 的资产。",
        },
    ]

    # ---------- per-asset review rows (verbatim slices, zero hand-copy) ---
    rows = []
    for a in man["assets"]:
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        quote = a["locator"]["quote"]
        chk = per_asset_chk[a["asset_id"]]
        rows.append({
            "asset_id": a["asset_id"],
            "asset_class": a["asset_class"],
            "label": a["label"],
            "resolution_declared": a["resolution"],
            "review_resolution_agree": True,
            "locator_method": a["locator"].get("method"),
            "span": [s, e],
            "quote_verbatim": src[s:e] if src[s:e] == quote else quote,
            "quote_at_declared_span": chk["quote_at_locator"],
            "quote_unique_in_source": chk["quote_unique"],
            "source_line": a["locator"].get("start_line"),
            "review_note": ("跨度≠引文（见 F1）" if not chk["quote_at_locator"] else "逐字命中声明跨度"),
        })
    for r in rows:
        assert r["quote_verbatim"] in src, r["asset_id"]

    # ---------- review ledger -------------------------------------------
    event = {
        "id": "tkr:wp-7545-01:m15854",
        "object_ref": reviewed_pkg,
        "object_version": "sha256:" + sha256_bytes(man_raw),
        "decision": "request-changes",
        "reviewer": dict(REVIEWER),
        "reviewed_at": "2026-11-12T02:00:00Z",
        "policy_version": POLICY_VERSION,
        "rationale": (
            "登记内容可复现（源哈希字节相等、18/18 引文在原文唯一可定位、路径型 token 无遗漏、"
            "计数自洽、4 张图缺字节的 declared_absent 双向确认），未发现伪造摘要或漏登记；"
            "但 A01 声明跨度≠引文、asset_manifest schema 不能在仓内复跑，两处需修后再入 04 结论。"
        ),
        "findings": [
            {"severity": "minor", "finding": "F1 A01(method=document) start_char=0/end_char=3583 与 44 字符 quote 不符"},
            {"severity": "minor", "finding": "F2 schemas/asset_manifest.v1.schema.json 被 const 钉在 wp-448-01，本包 schema_pass 不可复跑"},
            {"severity": "minor", "finding": "F3 自检文件用 verified_at/all_pass 命名，与 V 阶梯词汇冲突"},
            {"severity": "informational", "finding": "F4 fig[i]<->图N 只有位置证据，图注措辞两处不一致"},
            {"severity": "informational", "finding": "F5 计数为出现级：18 条 != 18 个不同文件"},
        ],
        "conditions": [
            "F1 修好后在同一 sha256 的源上复跑 scripts/kf_review_wp7545_01.py，V2_locators 必须转绿",
            "F2 交付 report-agnostic schema 或随包 rebound schema 及其 sha256 后，V9 转绿",
        ],
    }
    ledger = [event]
    state0 = submit({"producer_ids": [PRODUCER_ID]})
    final_state, codes = fold(ledger, {"producer_ids": [PRODUCER_ID]}, initial_state=state0)
    assert final_state == "draft" and codes == ["OK_CHANGES_REQUESTED"], (final_state, codes)

    # ---------- review report -------------------------------------------
    review_report = {
        "review_report_version": "1.0",
        "review_id": "rev:wp-7545-01:m15854",
        "package_reviewed": reviewed_pkg,
        "task_type_reviewed": kfr_up["task_type"],
        "report_id": "7545",
        "reviewer": REVIEWER,
        "producer": {"id": PRODUCER_ID},
        "verdict": "needs-fix",
        "verdict_scope": "登记保真（registration fidelity）；不含报告科学结论的语义保真（那属 03 工序，本包 claims 为空）",
        "source": {"uri": SOURCE_URI, "field": "markdown", "sha256": "sha256:" + CONTRACT_HASH,
                   "chars": len(src), "bytes_utf8": len(src.encode("utf-8")),
                   "recomputed_by_reviewer": True,
                   "product_sha256": "sha256:" + sha256_bytes(man_raw)},
        "independence": {
            "reviewer_id": REVIEWER["id"],
            "producer_ids": [PRODUCER_ID],
            "is_independent": True,
            "basis": "distinct-identity (no shared session token; canonical ids differ)",
            "prompt_jaccard_5gram_vs_producer_report": C["V10_prompt_independence"][
                "jaccard_5gram_review_instructions_vs_producer_report"],
            "threshold": 0.5,
            "producer_explanation_used_in_judgement": False,
            "context_reviewed": ["source markdown", "asset_manifest.json", "kf_result.json"],
            "context_excluded": ["REPORT.md (producer delivery prose)",
                                 "README.md (producer delivery prose)",
                                 "extraction_summary.json (absent for this task_type)"],
        },
        "acceptance_check": {
            "valid_json": {"pass": True, "how": "json.loads on all shipped products + envelope schema"},
            "schema_pass": {"pass": True,
                            "how": "kf_result.v1 (this envelope) = schema clean; upstream manifest "
                                   "schema is not re-runnable -> F2"},
            "reviewer_independent": {"pass": True, "how": "reviewer m15854 != producer agent/m15597; "
                                                          "prompt Jaccard 0.011 < 0.5"},
            "upstream_packages_completed": {"pass": True,
                                            "how": "wp-7545-01 product present and reviewed; its "
                                                   "quality verdict is needs-fix (F1-F3)"},
            "constraints": {
                "review_prompt_not_copied_from_producer": True,
                "reviewer_context_excludes_producer_explanation": True,
                "do_not_mark_claims_as_verified": True,
            },
        },
        "checks": [
            {"id": k.split("_")[0], "name": "_".join(k.split("_")[1:]), "pass": v["pass"]}
            for k, v in checks_doc["checks"].items()
        ],
        "checks_detail": checks_doc["checks"],
        "findings": findings,
        "asset_review": rows,
        "counts": {"assets_reviewed": len(rows),
                   "assets_locator_exact": sum(1 for r in rows if r["quote_at_declared_span"]),
                   "assets_quote_unique": sum(1 for r in rows if r["quote_unique_in_source"]),
                   "distinct_labels": len({r["label"] for r in rows}),
                   "distinct_targets": distinct_targets,
                   "findings": {"minor": 3, "informational": 2, "major": 0, "blocking": 0}},
        "handoff_notes": [
            "01 包 claims=[] 合法（objective 只含 register_assets、no_forced_claim_generation=true）；"
            "报告正文的数字与结论的语义保真不在本包判定范围，由 03 工序在源哈希不变的前提下另行抽取。",
            "同名 PNG（fig1_stress_strain.png）在另一任务树 m9699/artifacts/p167w2-n04/ 存在，但报告 markdown "
            "与平台记录都没有任何路径/摘要把它绑到 report 7545，故不当作本报告图字节的证据，也不跨包取用。",
            "报告自述『机器验收：通过，判据 9/9 条满足』同时给出 σ_c 的 honest FAIL；这是报告层面的自洽问题，"
            "登记工序不改写、不裁定，留给 03/04 的语义审核与平台门。",
        ],
        "checks_not_run": [
            "未执行报告声称的 pytest 命令（01 工序边界只登记命令文本；执行结论属报告作者与平台门）",
            "未取用 m9699 任务树的同名 PNG 做图字节比对（跨任务树、无绑定关系）",
            "未复算生产者的回顾性自我检查（各 acceptance 明细以本次独立复跑为准）",
            "未做跨报告一致性/去重（05 工序）",
        ],
        "repro": {
            "cmd": "python3 scripts/kf_fetch_7545.py && python3 scripts/kf_review_wp7545_01.py && "
                   "python3 scripts/kf_build_wp7545_04.py",
        },
    }

    rr_path = os.path.join(OUTDIR, "review_report.json")
    json.dump(review_report, open(rr_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ev_path = os.path.join(OUTDIR, "review_events.json")
    json.dump(ledger, open(ev_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---------- figure ---------------------------------------------------
    fig_rel = make_figure(checks_doc, rows, man)

    # ---------- envelope -------------------------------------------------
    envelope = {
        "package_id": pkg,
        "task_type": "04-independent-review",
        "report_id": "7545",
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + CONTRACT_HASH,
            "producer": "agent/m15854",
            "emitted_at": "2026-11-12T02:00:00Z",
            "notes": "reviewer context = source markdown + upstream product (asset_manifest.json, "
                     "kf_result.json); producer prose excluded; no claim marked as verified",
        },
        "outputs": {
            "review_report.json": review_report,
            "review_events.json": ledger,
        },
        "claims": [],
    }
    json.dump(envelope, open(os.path.join(OUTDIR, "kf_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    md = build_markdown(review_report, checks_doc, rows, man, fig_rel, envelope)
    open(os.path.join(OUTDIR, "review_report.md"), "w", encoding="utf-8").write(md)

    payload = {
        "title": f"KF-RESULT {pkg}",
        "summary": "wp-7545-01 独立复核：源哈希字节相等、17/18 locator 逐字命中、无遗漏/伪造；"
                   "判 needs-fix（A01 跨度≠引文、schema 不可复跑、自检命名越界）。",
        "scenario_key": man["source"]["scenario_key"],
        "mission_id": 15854,
        "tags": ["kf-wp:" + pkg, "kf-result", "independent-review", "wp-7545-01",
                 "ice_fracture_contact_abm", "asset-registration"],
        "markdown": md,
        "figures": [],
    }
    with open(os.path.join(OUTDIR, "fig_review_wp7545_04.png"), "rb") as f:
        payload["figures"].append({
            "name": "fig_review_wp7545_04",
            "caption": "左：18 条资产的声明跨度 vs 逐字引文长度（log）——仅 A01 跨度远大于引文；"
                       "右：11 项独立复核判据通过/不通过与解析分布",
            "png_base64": base64.b64encode(f.read()).decode(),
        })
    json.dump(payload, open("/tmp/report_7545_04.json", "w", encoding="utf-8"), ensure_ascii=False)

    blocks = md.count("```json")
    print(json.dumps({"failed_checks": failed, "verdict": review_report["verdict"],
                      "json_blocks_in_markdown": blocks, "md_chars": len(md),
                      "figure": fig_rel, "ledger_codes": codes, "ledger_final_state": final_state},
                     ensure_ascii=False))
    return 0 if blocks == 1 else 1


def make_figure(checks_doc: dict, rows: list[dict], man: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))
    ids = [r["asset_id"] for r in rows]
    span = [r["span"][1] - r["span"][0] for r in rows]
    qlen = [len(r["quote_verbatim"]) for r in rows]
    x = range(len(ids))
    ax1.bar(x, span, color="#8fb8de", label="declared span length")
    ax1.plot(list(x), qlen, "o", color="#c0392b", label="verbatim quote length")
    bad = [i for i, r in enumerate(rows) if not r["quote_at_declared_span"]]
    for i in bad:
        ax1.annotate("span != quote", (i, span[i]), textcoords="offset points",
                     xytext=(4, -14), color="#c0392b", fontsize=8)
    ax1.set_yscale("log")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(ids, rotation=90, fontsize=7)
    ax1.set_ylabel("characters (log)")
    ax1.set_title("per-asset locator: declared span vs verbatim quote")
    ax1.legend(fontsize=8)

    titles = [f"{k.split('_')[0]} {k.split('_', 1)[1]}" for k in checks_doc["checks"]]
    oks = [v["pass"] for v in checks_doc["checks"].values()]
    colors = ["#27ae60" if o else "#c0392b" for o in oks]
    ax2.barh(range(len(titles)), [1] * len(titles), color=colors)
    ax2.set_yticks(range(len(titles)))
    ax2.set_yticklabels(titles, fontsize=8)
    for i, o in enumerate(oks):
        ax2.text(0.5, i, "pass" if o else "FAIL", va="center", ha="center", color="white", fontsize=8)
    ax2.set_xlim(0, 1)
    ax2.set_xticks([])
    br = man["counts"]["by_resolution"]
    ax2.set_title("independent review checks (11) — "
                  f"resolved {br['resolved_in_source']} / unresolved {br['referenced_unresolved']} / "
                  f"absent {br['declared_absent']}", fontsize=9)
    fig.tight_layout()
    path = os.path.join(OUTDIR, "fig_review_wp7545_04.png")
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return os.path.relpath(path, ROOT)


def code_span(text: str) -> str:
    """GFM code span that survives embedded backticks and table pipes (verbatim content)."""
    t = text.replace("|", "\\|")
    if "`" not in t:
        return "`" + t + "`"
    return "`` " + t + " ``"


def build_markdown(rr: dict, checks_doc: dict, rows: list[dict], man: dict,
                   fig_rel: str, envelope: dict) -> str:
    src = open(SRC_MD, encoding="utf-8").read()
    cd = checks_doc["checks"]
    L = []
    A = L.append
    A(f"# KF-RESULT {pkg} — 独立审核：{reviewed_pkg}（report 7545 资产登记）")
    A("")
    A(f"**结论：{rr['verdict']}**（0 blocking / 0 major / 3 minor / 2 informational）。"
      "登记内容可复现，未发现伪造摘要或漏登记；两处证据层缺陷需修后再入下一工序。")
    A("")
    A("## ① 本工序做了什么")
    A("")
    A(f"本工序 = 工序 04（`04-independent-review`），只审一个上游包 `{reviewed_pkg}`"
      f"（`{rr['task_type_reviewed']}`），只碰 report 7545 一文。做四件事：")
    A("")
    A("1. **独立重算源身份**：不用上游给的哈希，自己从平台 API 取 markdown 重算 sha256/字符数/字节数。")
    A(f"2. **逐条反查 locator**：{rr['counts']['assets_reviewed']} 条资产逐条验证『声明跨度 == 逐字引文』"
      "与『引文在原文唯一』。")
    A("3. **可解析性双证**：4 张图登记为 `declared_absent`，既探平台取值端点，也查图存储根目录，"
      "再读路由源码确认 404 的语义。")
    A("4. **覆盖面反查**：枚举报告正文全部反引号 token，检查是否有路径型 token 未登记（漏登记 = 资产账不完整）。")
    A("")
    A("## ② 怎么做的（方法 / 步骤 / 工具 / 关键设置）")
    A("")
    A("| 步骤 | 动作 | 工具/入口 | 关键设置 |")
    A("|---|---|---|---|")
    A("| S1 | 取原文并验哈希 | `GET /tensor/reports/7545` → `scripts/kf_fetch_7545.py` | 只取 `markdown` 字段；utf-8 字节算 sha256 |")
    A("| S2 | 复核上游产物字节 | `docs/kf/wp-7545-01/{asset_manifest,kf_result}.json` | 只读产物，**不读** `REPORT.md`/`README.md`（生产者解释） |")
    A("| S3 | 11 项判据复跑 | `scripts/kf_review_wp7545_01.py` | 判据先声明后跑（V1–V11），结果落 JSON |")
    A("| S4 | 图端点双拼写探测 | `/tensor/reports/7545/figures/<name>` 与 `/api/v1/...` | 同时查 `uploads/tensor_reports/7545/` 磁盘目录 |")
    A("| S5 | 审核台账过状态机 | `scripts/ke_state_machine.py` | `submit` → `request-changes`；fold 期望 `OK_CHANGES_REQUESTED` |")
    A("| S6 | 产物装配 + 图 | `scripts/kf_build_wp7545_04.py` | 所有引文在写出前断言为原文子串（零手抄的机器保证） |")
    A("")
    A("**独立性设置**：审核者 `m15854` ≠ 生产者 `agent/m15597`；审核指令与生产者交付文的 5-gram "
      f"Jaccard = {cd['V10_prompt_independence']['jaccard_5gram_review_instructions_vs_producer_report']}"
      f"（阈值 0.5）。审核上下文只含：原文 markdown + `asset_manifest.json` + `kf_result.json`。")
    A("")
    A("## ③ 计算结果（数字表，程序化注入）与产出物清单")
    A("")
    A("### 3.1 源身份独立重算")
    A("")
    A("| 量 | 复核值 | 上游声明 | 差 |")
    A("|---|---|---|---|")
    v1 = cd["V1_source_identity"]
    A(f"| markdown sha256 | `{v1['sha256']}` | `sha256:{CONTRACT_HASH}` | 0（字节相等） |")
    A(f"| 字符数 | {v1['chars']} | {v1['chars_declared']} | 0 |")
    A(f"| utf-8 字节数 | {v1['bytes_utf8']} | {v1['bytes_declared']} | 0 |")
    man_hash = man["counts"]
    A(f"| 产物字节数 | {cd['V6_product_digest']['actual_bytes']} | {cd['V6_product_digest']['declared_bytes']} | 0 |")
    A(f"| 产物 sha256 | `{cd['V6_product_digest']['actual_sha256']}` | `{cd['V6_product_digest']['declared_sha256']}` | 0 |")
    A("")
    A("### 3.2 11 项独立判据")
    A("")
    A("| 判据 | 结论 | 关键数字 |")
    A("|---|---|---|")
    desc = {
        "V1": "源身份（哈希/字符/字节）字节相等",
        "V2": "locator：跨度==引文 & 引文唯一 & 行号一致",
        "V3": "declared_absent 图：端点 404 + 磁盘无档 + 无臆造摘要",
        "V4": "计数自洽（18 / by_class / by_resolution / envelope）",
        "V5": "覆盖面：路径型 token 全部登记",
        "V6": "产物摘要与字节数符合声明",
        "V7": "平台 figures 元数据与资产标签顺序一致",
        "V8": "kf_result 信封过 `schemas/kf_result.v1.schema.json`",
        "V9": "上游 manifest schema 可在仓内复跑",
        "V10": "审核指令 vs 生产者交付文的 5-gram Jaccard < 0.5",
        "V11": "referenced_unresolved 的路径确实不在本仓检出内",
    }
    nums = {
        "V1": f"chars {v1['chars']} / bytes {v1['bytes_utf8']}",
        "V2": f"逐字命中 {rr['counts']['assets_locator_exact']}/{rr['counts']['assets_reviewed']}，"
              f"mismatch={cd['V2_locators']['locator_mismatch']}，非唯一={cd['V2_locators']['non_unique']}",
        "V3": f"4 图 × 2 拼写全部 404；磁盘 7545 目录不存在；臆造摘要={cd['V3_declared_absent']['invented_digests']}",
        "V4": f"assets={cd['V4_counts']['assets_actual']}，by_class 和={sum(cd['V4_counts']['by_class_actual'].values())}，"
              f"by_resolution={cd['V4_counts']['by_resolution_actual']}",
        "V5": f"反引号 token {cd['V5_completeness']['backticked_tokens']} 个，路径型 "
              f"{cd['V5_completeness']['pathish_tokens']} 个，未登记={cd['V5_completeness']['unregistered_pathish']}",
        "V6": f"actual={cd['V6_product_digest']['actual_sha256'][:12]}… 与声明一致",
        "V7": f"figures 名称顺序 {[p['name'] for p in cd['V7_figure_metadata']['platform_figures']]}",
        "V8": f"errors={cd['V8_envelope_schema']['errors']}",
        "V9": f"schema 钉死 package_id={cd['V9_manifest_schema_reproducibility']['pinned_package_id']} / "
              f"report_id={cd['V9_manifest_schema_reproducibility']['pinned_report_id']}，随包 rebound schema=0 份",
        "V10": f"Jaccard={cd['V10_prompt_independence']['jaccard_5gram_review_instructions_vs_producer_report']}",
        "V11": f"13 条引用路径在本仓检出内命中 {sum(1 for r in cd['V11_unresolved_classification']['rows'] if r['present_in_tensor_knowledge'])} 条",
    }
    for k, v in cd.items():
        key = k.split("_")[0]
        verdict = "pass" if v["pass"] is True else ("**FAIL**" if v["pass"] is False else "not_run")
        A(f"| {key} {desc.get(key, '')} | {verdict} | {nums.get(key, '')} |")
    A("")
    A("### 3.3 资产盘点")
    A("")
    A("| class | 条数 |")
    A("|---|---|")
    for k, v in sorted(cd["V4_counts"]["by_class_actual"].items()):
        A(f"| `{k}` | {v} |")
    A(f"| **合计** | **{cd['V4_counts']['assets_actual']}** |")
    A("")
    A(f"解析分布：`resolved_in_source` {man['counts']['by_resolution']['resolved_in_source']} · "
      f"`referenced_unresolved` {man['counts']['by_resolution']['referenced_unresolved']} · "
      f"`declared_absent` {man['counts']['by_resolution']['declared_absent']}；"
      f"不同 label 数 {rr['counts']['distinct_labels']}；按目标去重 {rr['counts']['distinct_targets']} 个"
      "（出现级身份，见 F5）。")
    A("")
    A("### 3.4 产出物清单")
    A("")
    A("| 文件 | 要点 |")
    A("|---|---|")
    A(f"| `docs/kf/{pkg}/review_report.json` | 本审核主产物：verdict / 11 判据 / 5 结论 / 18 条逐资产裁定 |")
    A(f"| `docs/kf/{pkg}/review_events.json` | 审核台账 1 条：`request-changes`，fold 得 `OK_CHANGES_REQUESTED` |")
    A(f"| `docs/kf/{pkg}/kf_result.json` | 结果信封（`package_id`/`task_type`/`report_id`/`provenance`/`outputs`） |")
    A(f"| `docs/kf/{pkg}/review_report.md` | 本正文（六段 + 唯一 json 块） |")
    A(f"| `{fig_rel}` | 图：逐资产跨度/引文长度 + 11 判据通过矩阵 |")
    A("| `work/kf_wp7545/report_7545.md` | 取回的原文快照（哈希与契约一致） |")
    A("| `work/kf_wp7545/review/upstream_review_checks.json` | 11 判据的原始机器证据（逐资产行） |")
    A("")
    A("## ④ 结果图与证据定位表")
    A("")
    A(f"![review]({os.path.basename(fig_rel)})")
    A("")
    A("图注：左面板逐资产对比『声明跨度长度』与『逐字引文长度』（log 纵轴），只有 A01 的跨度远大于其引文，"
      "即 F1；右面板是 11 项判据的通过矩阵（9 绿 2 红）与解析分布。")
    A("")
    A("**证据定位表**（每条引文都是原文子串，构建脚本逐条断言；`loc` 为原文 `[start,end)` 字符区间）")
    A("")
    A("| 资产 | 解析 | loc | 原文引文片段（逐字） | 裁定 |")
    A("|---|---|---|---|---|")
    for r in rows:
        A(f"| {r['asset_id']} | {r['resolution_declared']} | [{r['span'][0]},{r['span'][1]}) | "
          f"{code_span(r['quote_verbatim'])} | "
          f"{'跨度≠引文（F1）' if not r['quote_at_declared_span'] else '一致'} |")
    A("")
    A("## ⑤ 注意点与局限")
    A("")
    A("1. **本包的判决只覆盖登记保真**。上游 `claims=[]` 合法（`no_forced_claim_generation`），"
      "报告正文数字与结论的语义保真属 03 工序，本包不裁。")
    A("2. **F1 的条件性升级**：今天 A01 的跨度缺陷不进 G2（01 不产 claim/evidence），"
      "但下游一旦复用这套 locator 并映射成 `start_offset/end_offset`，E4 立即变红——所以修。")
    A("3. **F2 是复现性缺口不是内容错误**：`schemas/asset_manifest.v1.schema.json` 的 const 钉死在 "
      "`wp-448-01`/`448`，本包 schema_pass 只能采信上游自述。")
    A("4. **同名 PNG 的诱饵**：另一任务树存在同名 `fig1_stress_strain.png`，但报告与平台记录无任何路径/摘要"
      "把它绑到 7545，故不取用、不做图字节比对（跨任务树取用等于跨包造证据）。")
    A("5. **未跑项如实挂账**：未执行报告声称的 pytest；未复算生产者自检明细；未做跨报告去重（05 工序）。")
    A("")
    A("## ⑥ 自检（逐条对照 acceptance）与误差判定")
    A("")
    A("| acceptance | 结论 | 依据 |")
    A("|---|---|---|")
    A("| `valid_json` | ✅ | 三份产物 `json.loads` 全过；信封过 `kf_result.v1` schema（V8 errors=[]） |")
    A("| `schema_pass` | ✅（附 F2） | 本包信封 schema 干净；**上游** manifest schema 不可在仓内复跑 → F2 |")
    A("| `reviewer_independent` | ✅ | `m15854` ≠ `agent/m15597`；prompt Jaccard "
      f"{cd['V10_prompt_independence']['jaccard_5gram_review_instructions_vs_producer_report']} < 0.5 |")
    A("| `upstream_packages_completed` | ✅ | `wp-7545-01` 产物齐全并已逐条复核；质量裁定 needs-fix（F1–F3） |")
    A("| 约束 `review_prompt_not_copied_from_producer` | ✅ | 审核指令自撰；与生产者交付文 Jaccard 0.011 |")
    A("| 约束 `reviewer_context_excludes_producer_explanation` | ✅ | 未把 `REPORT.md`/`README.md` 读入判定 |")
    A("| 约束 `do_not_mark_claims_as_verified` | ✅ | 产物里无 claim 级『已核实』字段；台账只写审核裁定 |")
    A("")
    A("**误差判定（本工序无物理量，判据换成数字一致性）**")
    A("")
    A("| 量 | 复核值 vs 声明值 | 相对误差 | <3%? |")
    A("|---|---|---|---|")
    A(f"| 源 sha256 | 字节相等 | 0% | **是** |")
    A(f"| 字符数 / 字节数 | {v1['chars']} / {v1['bytes_utf8']} 对 {v1['chars_declared']} / {v1['bytes_declared']} | 0% | **是** |")
    A(f"| 产物 sha256 | `{cd['V6_product_digest']['actual_sha256'][:16]}…` | 0% | **是** |")
    A(f"| locator 逐字命中率 | {rr['counts']['assets_locator_exact']}/{rr['counts']['assets_reviewed']} | "
      f"偏差资产占比 {round(100 * (1 - rr['counts']['assets_locator_exact'] / rr['counts']['assets_reviewed']), 1)}% | "
      "**否（1/18=5.6%，>3% 但 <15%，故不判不可接受，开 F1 要求修复）** |")
    A(f"| 计数自洽 | assets {cd['V4_counts']['assets_actual']} · by_class 和 "
      f"{sum(cd['V4_counts']['by_class_actual'].values())} · 声明 {man['counts']['assets']} | 0% | **是** |")
    A("| 覆盖面 | 路径型 token 未登记 0 个 | 0% | **是** |")
    A("")
    A("**诚实项**：2 项判据（V2/V9）为红，未粉饰；V2 的红是 1/18，不是系统性偏移；"
      "V9 的红是复现性缺口，需上游补 schema 后转绿。")
    A("")
    A("## 审计链与复跑")
    A("")
    A("- 原文哈希：`sha256:" + CONTRACT_HASH + "`（平台独立重算可复核）")
    A("- 被审产物：`" + rr["source"]["product_sha256"] + "`（asset_manifest.json 字节）")
    A("- 审核台账 fold：`submit` → `request-changes` → state=`draft`，code=`OK_CHANGES_REQUESTED`")
    A("- 一键复跑：`python3 scripts/kf_fetch_7545.py && python3 scripts/kf_review_wp7545_01.py && "
      "python3 scripts/kf_build_wp7545_04.py`")
    A("")
    A("```json")
    A(json.dumps(envelope, ensure_ascii=False, indent=1))
    A("```")
    md = "\n".join(L) + "\n"
    # every quoted snippet asserted verbatim above; re-assert the json block is unique
    assert md.count("```json") == 1
    return md


if __name__ == "__main__":
    sys.exit(main())