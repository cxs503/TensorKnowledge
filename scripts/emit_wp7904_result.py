#!/usr/bin/env python3
"""Emit docs/kf/wp-79-04/review_report.json + review_events.json (wp-79-04).

Zero hand-copy by construction: a quote is referenced by a unique substring and the
exact bytes + character offsets are looked up in ``runs/wp-79-04/checks.json``
(produced by ``scripts/kf_wp7904_review.py``, which verified every quote as a
verbatim substring of the frozen source). Numbers come from the checks file.

Run:  python3 scripts/kf_wp7904_review.py && python3 scripts/emit_wp7904_result.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import kf_wp7904_review as chk  # noqa: E402

OUT_DIR = ROOT / "docs/kf/wp-79-04"
CHECKS = ROOT / "runs/wp-79-04/checks.json"
PACKAGE_ID = "wp-79-04"
REPORT_ID = "79"
SOURCE = OUT_DIR / "source.md"

checks = json.loads(CHECKS.read_text(encoding="utf-8"))
src_bytes = SOURCE.read_bytes()
source_hash = "sha256:" + hashlib.sha256(src_bytes).hexdigest()
assert source_hash == chk.CONTRACT_HASH, source_hash
assert checks["C1"]["pass"] and checks["C2"]["pass"], "C1/C2 must be green to cite quotes"


def Q(fragment: str, note: str | None = None) -> dict:
    """Locate the verified quote containing ``fragment``; return quote + offsets."""
    hits = [r for r in checks["C2"]["rows"] if r.get("found") and fragment in r["quote"]]
    if len({r["quote"] for r in hits}) != 1:
        raise SystemExit(f"fragment not unique/verified ({len(hits)}): {fragment!r}")
    row = hits[0]
    out = {"quote": row["quote"], "source_field": "markdown",
           "start_offset": row["start"], "end_offset": row["end"]}
    if note:
        out["note"] = note
    return out


numeric, tol, prompt_sim = checks["C3"], checks["C3"]["C4"], checks["C7"]
upstream, coverage = checks["C6"], checks["C5"]
id_lo, id_hi = upstream["probe_a_newest_by_id"]["id_range"]
win_lo, win_hi = upstream["probe_b_mission_window"]
rel_fail = tol["pairs_failing_relative_reading"]

FINDINGS = [
    {
        "id": "F1", "severity": "blocking", "likelihood": "certain",
        "title": "上游知识包 wp-79-01 在平台上不可达 ⇒ fidelity 判据无从施加",
        "detail": (
            "契约把审核对象钉在 wp-79-01，产线要求 04 的上下文=原文+知识对象。"
            f"有界探针（A：最新 {upstream['probe_a_newest_by_id']['n']} 份报告，id "
            f"{id_lo}-{id_hi}；B：mission {win_lo}-{win_hi} 共 "
            f"{upstream['probe_b_reports_found']} 份）未命中任何 wp-79-01 产物；"
            f"正控制 wp-9083-01 命中 {upstream['positive_control']['hits']}，证明探针不是空转。"
            "因此 acceptance.upstream_packages_completed 不成立，semantic_fidelity 只能 not_run。"
        ),
        "evidence": [],
        "artifact_ref": "runs/wp-79-04/checks.json#C6",
        "impact": "知识对象身份不可确认；此时任何'审核通过'都越权。",
        "remediation": "先产出并落库 wp-79-01，再重跑本包；平台侧报告列表需可用分页/按 tag 过滤。",
    },
    {
        "id": "F2", "severity": "major", "likelihood": "certain",
        "title": "数字溯源不可重放：只给绝对本机路径通配，无工件文件名/内容哈希",
        "detail": (
            "报告把数字溯源建立在 `/root/tp-agent/work/m{mission_id}/artifacts/*.json` 上，"
            "既无具体文件名也无工件哈希；换机或换任务目录即无法定位同一份工件。"
            f"本次能独立复算的只有报告内部四舍五入自洽性：{numeric['pairs_rounding_consistent']}"
            f"/{numeric['pairs']} 对通过；工件侧数值无法二次确认，且报告自承只抽查 3 个数字/篇。"
        ),
        "evidence": [Q("工件目录", "溯源来源只到目录通配"),
                     Q("图件检查依赖工作目录文件搜索"),
                     Q("仅抽查 3 个数字/篇")],
        "artifact_ref": "runs/wp-79-04/checks.json#C3",
        "impact": "质检结论不可由第三方重放，'可核验'退化为'作者自述'。",
        "remediation": "溯源写成 artifactId#<file>.json@sha256:<hash>，或把工件登记进 asset_manifest。",
    },
    {
        "id": "F3", "severity": "major", "likelihood": "certain",
        "title": "自定容差 ±0.01% 未定义口径，且按相对误差读法被自身数据违反",
        "detail": (
            "报告写'需用近似匹配（±0.01%）'并在 §⑥ 断言'数字溯源误差 < 0.01%'，未说明是绝对"
            f"百分点还是相对误差。复算：绝对百分点读法最大偏差 {numeric['max_abs_dev_pct_points']} pp"
            f"（全部通过）；相对误差读法最大 {numeric['max_rel_dev_pct']:.4f}%，"
            f"{len(rel_fail)}/{numeric['pairs']} 对超阈值（{', '.join(rel_fail)}），"
            "而这些对在报告中全部标 ✅。"
        ),
        "evidence": [Q("需用近似匹配"), Q("数字溯源误差 < 0.01%"),
                     Q("SDAA CV: 报告 1.34%")],
        "artifact_ref": "runs/wp-79-04/checks.json#C3.C4 + docs/kf/wp-79-04/review_checks.png",
        "impact": "判定标签与自定判据不自洽；同一证据换读法即翻结论，不可复现。",
        "remediation": "判据改为确定性表述（工件值按打印精度四舍五入 == 打印值），并列出绝对差/相对差两列。",
    },
    {
        "id": "F4", "severity": "major", "likelihood": "certain",
        "title": "声明 6 项质检标准，逐篇只记录 4 项（含报告自己的'结论不超证据'）",
        "detail": (
            f"§① 声明六项标准，§③ 汇总表逐篇记录覆盖 {coverage['coverage_ratio']}；"
            f"未记录：{', '.join(coverage['declared_but_unrecorded'])}（结构五节、结论不超证据）。"
            "报告用自己都没执行的判据去担保他人，属未被证实的覆盖声明。"
        ),
        "evidence": [Q("质检标准"), Q("| 报告 ID |"), Q("| 64 | 121 | MINOR |")],
        "artifact_ref": "runs/wp-79-04/checks.json#C5",
        "impact": "两处判定（三篇结构完整性、结论是否超证据）无任何留痕。",
        "remediation": "汇总表补'结构'与'超证据'两列（逐篇结果+定位），或收缩标准清单到实际执行的 4 项。",
    },
    {
        "id": "F5", "severity": "major", "likelihood": "likely",
        "title": "同一'图件齐备'判据出现三种结论且无 rubric；65 的 PASS 依赖未被引用的'理由'",
        "detail": (
            "64→'比较曲线✅/云图N/A'、65→'缺失但有理由'（仍 PASS）、66→'❌ 未嵌入'（RESUBMIT）。"
            "同一判据下 65 与 66 都缺图却结论相反，差别全在'有理由'三字，而该理由在报告里从未被引用。"
            "换人复审会得到不同结论，判定不可重复。"
        ),
        "evidence": [Q("| 64 | 121 | MINOR |"), Q("| 65 | 42 | PASS |"), Q("| 66 | 40 | RESUBMIT |")],
        "artifact_ref": "docs/kf/wp-79-04/source.md#③ 计算结果",
        "impact": "RESUBMIT 与 PASS 的边界由未记录的隐性标准决定。",
        "remediation": "先定义图件 rubric（仿真类必须有场量图；纯文档须写出无图理由并定位），"
                       "并逐字引用 65 的理由，否则 65 与 66 同档处置。",
    },
    {
        "id": "F6", "severity": "minor", "likelihood": "certain",
        "title": "跨系统断言（返工单 #155、质检文档）无 locator/哈希",
        "detail": "报告称'已派返工单 #155'并指向 `docs/qa_batch_64_65_66.md`，"
                  "但未给工单 id 体系、状态查询方式或文档内容哈希，外部无法确认其存在或已执行。",
        "evidence": [Q("已派返工单 #155"), Q("完整质检文档见")],
        "artifact_ref": "docs/kf/wp-79-04/source.md#⑥ 误差判定",
        "impact": "处置动作是否真的发生不可核验，可能导致返工空转。",
        "remediation": "写工单 id + 平台路径；文档给 sha256 或仓内相对路径。",
    },
    {
        "id": "F7", "severity": "minor", "likelihood": "certain",
        "title": "报告 64 的误差列只有'参考值来源不明'，无任何数字，无法套用 15% 精度标准",
        "detail": "判定 MINOR 的依据未量化：既无 64 的实际误差值，也无参考值候选与差值，"
                  "'误差是否 >15% 不可接受'在该篇处于未判定状态（不是通过）。",
        "evidence": [Q("| 64 | 121 | MINOR |"), Q("报告 64 → MINOR")],
        "artifact_ref": "docs/kf/wp-79-04/source.md#③ 计算结果",
        "impact": "MINOR 档位缺少数值支撑，可能掩盖真实超差。",
        "remediation": "补误差数值/参考值来源；来源不明时显式写 not_applicable 及理由。",
    },
    {
        "id": "F8", "severity": "informational", "likelihood": "certain",
        "title": "无图理由可接受，但措辞把表格称作'比较曲线'",
        "detail": "§④ 已写明质检任务无场量云图（符合'无图须写明理由'），"
                  "但接着说'比较曲线为质检判定表'——判定表不是曲线。",
        "evidence": [Q("比较曲线为质检判定表")],
        "artifact_ref": "docs/kf/wp-79-04/source.md#④ 结果图",
        "impact": "措辞级失真，不影响判定结论。",
        "remediation": "改为'无比较曲线；判定依据为 §③ 汇总表'。",
    },
]

CLAIMS = [
    {"claim_id": "wp79-04-c01", "text": "报告声明了六项质检标准（结构五节/数字溯源/honest-FAIL/图件/误差判定/结论不超证据）",
     "status": "supported", "evidence": [Q("质检标准")]},
    {"claim_id": "wp79-04-c02", "text": "逐篇汇总表只记录四项判据结果，'结构五节'与'结论不超证据'无留痕",
     "status": "supported", "evidence": [Q("质检标准"), Q("| 报告 ID |"), Q("| 64 | 121 | MINOR |")]},
    {"claim_id": "wp79-04-c03", "text": f"报告所列 9 个数字对中 {numeric['pairs_rounding_consistent']}/9 满足'工件值按打印精度四舍五入 == 打印值'",
     "status": "supported", "evidence": [Q("SDAA CV: 报告 1.34%"), Q("L2(ρ) nx2000")]},
    {"claim_id": "wp79-04-c04", "text": f"报告的'±0.01%'容差若按相对误差读，{len(rel_fail)}/9 对被自身数据判失（最大 {numeric['max_rel_dev_pct']:.4f}%）",
     "status": "supported", "evidence": [Q("需用近似匹配"), Q("数字溯源误差 < 0.01%"), Q("SDAA CV: 报告 1.34%")]},
    {"claim_id": "wp79-04-c05", "text": "数字溯源只给绝对本机路径通配，未给工件文件名/哈希，第三方无法重放",
     "status": "supported", "evidence": [Q("工件目录"), Q("仅抽查 3 个数字/篇")]},
    {"claim_id": "wp79-04-c06", "text": "同一'图件齐备'判据在 64/65/66 上得到 N/A / 缺失但有理由(PASS) / 未嵌入(RESUBMIT) 三种结论且无 rubric",
     "status": "supported", "evidence": [Q("| 64 | 121 | MINOR |"), Q("| 65 | 42 | PASS |"), Q("| 66 | 40 | RESUBMIT |")]},
    {"claim_id": "wp79-04-c07", "text": "返工单 #155 与质检文档 docs/qa_batch_64_65_66.md 均无 locator/哈希",
     "status": "supported", "evidence": [Q("已派返工单 #155"), Q("完整质检文档见")]},
    {"claim_id": "wp79-04-c08", "text": "审核对象 wp-79-01 的知识对象内容忠实于原文",
     "status": "unresolved",
     "unresolved_reason": "上游包 wp-79-01 在平台上不可达（C6 有界探针未命中、正控制通过），"
                          "无 claim 可供与原文逐条对照；本审核只反驳了来源报告自身的内部一致性。",
     "evidence": []},
]

UNRESOLVED = [{"claim_id": "wp79-04-c08", "status": "unresolved",
               "reason": CLAIMS[-1]["unresolved_reason"],
               "probe": "runs/wp-79-04/checks.json#C6"}]

review_report = {
    "package_id": PACKAGE_ID,
    "task_type": "04-independent-review",
    "report_id": REPORT_ID,
    "reviewer_role": "red-team-reviewer",
    "review_target": {"package_id": "wp-79-01", "upstream_available": upstream["upstream_available"]},
    "verdict": "needs-fix",
    "verdict_vocabulary": ["pass", "fail", "needs-fix"],
    "verdict_basis": [
        "blocking F1：审核对象 wp-79-01 不可达 ⇒ semantic_fidelity 轴 not_run，不得判 pass",
        "major F2/F3/F4/F5：溯源不可重放、容差口径自违、判据覆盖 4/6、图件判据不可重复",
        "minor F6/F7 + informational F8：跨系统断言无 locator、误差未量化、措辞失真",
        "来源报告未发现被推翻的事实性断言：9 个数字对在四舍五入判据下全部自洽（numeric_rounding=pass）",
    ],
    "axes": {
        "source_integrity": {"status": "pass", "detail": {k: checks["C1"][k] for k in
                                                          ("expected", "actual", "chars")}},
        "structural": {"status": "fail", "detail": f"判据覆盖 {coverage['coverage_ratio']}（C5）"},
        "evidence": {"status": "fail",
                     "detail": "数字溯源不可重放（无工件文件名/哈希）+ 容差口径自违（C3.C4）"},
        "semantic_fidelity": {
            "status": "not_run", "pass": None,
            "reason": "上游知识对象 wp-79-01 不存在于平台（C6 有界探针 + 正控制），"
                      "没有 claim 可与原文逐条对照；本审核只反驳来源报告自身的内部一致性。",
        },
        "level_ownership": "platform_gate_only_reviewer_never_assigns",
    },
    "independence": {
        "producer_explanation_seen": False,
        "context_used": ["docs/kf/wp-79-04/source.md (report_id=79, markdown, byte-exact)"],
        "context_excluded": ["extraction_summary", "self_assessment", "producer_rationale", "notes"],
        "review_prompt_file": "docs/kf/wp-79-04/review_prompt.md",
        "review_prompt_vs_producer_prompt_jaccard_5gram": prompt_sim["jaccard_5gram"],
        "prompt_independence_threshold": prompt_sim["threshold"],
        "prompt_independence_pass": prompt_sim["pass"],
        "limitation": "同一 agent harness 家族内的独立席位；非人审，也未做强模型抽样双读。",
    },
    "findings": FINDINGS,
    "checks_performed": [
        {"id": "C1", "name": "source_integrity", "result": "pass",
         "detail": f"sha256(source.md)={source_hash} 与契约一致"},
        {"id": "C2", "name": "quote_locatability", "result": "pass",
         "detail": f"{checks['C2']['quotes_found']}/{checks['C2']['quotes_total']} 条引文逐字可定位，"
                   f"最短 {checks['C2']['min_chars']} 字符"},
        {"id": "C3", "name": "numeric_rounding", "result": "pass",
         "detail": f"{numeric['pairs_rounding_consistent']}/{numeric['pairs']} 对满足四舍五入判据"},
        {"id": "C4", "name": "tolerance_readings", "result": "fail",
         "detail": f"相对读法 {len(rel_fail)}/{numeric['pairs']} 对超 ±0.01%；绝对 pp 读法 0 对超；口径未定义"},
        {"id": "C5", "name": "criteria_coverage", "result": "fail",
         "detail": f"声明 {coverage['declared_criteria']} 项，逐篇记录 {coverage['coverage_ratio']}"},
        {"id": "C6", "name": "upstream_probe", "result": "fail",
         "detail": f"wp-79-01 未命中（A：最新 {upstream['probe_a_newest_by_id']['n']} 份 id {id_lo}-{id_hi}；"
                   f"B：mission {win_lo}-{win_hi}），正控制命中 {upstream['positive_control']['hits']}"},
        {"id": "C7", "name": "prompt_similarity",
         "result": "pass" if prompt_sim["pass"] else "fail",
         "detail": f"审核 vs 生产 prompt 5-gram Jaccard={prompt_sim['jaccard_5gram']} < {prompt_sim['threshold']}"},
    ],
    "checks_not_run": [
        {"check": "独立复核报告 64/65/66 原文数字",
         "reason": "工作包边界禁止读写其它 report_id（互不覆盖），只能核 report 79 自身"},
        {"check": "核对上游工件 json 数值（6.9438ms / 1.122209 …）",
         "reason": "工件在其它任务绝对路径 /root/tp-agent/work/m{121,42,40}/artifacts，"
                   "超出本包边界，且报告未给文件名与哈希"},
        {"check": "平台全量穷举'wp-79-01 是否存在'",
         "reason": "reports 列表忽略 offset/search/tags/cursor（实测同页返回），探针只能有界"},
        {"check": "强模型抽样双读（M6 抽样）", "reason": "不在本工作包范围，且无 claim 可抽"},
    ],
    "overstated_claims": [
        {"claim": "数字溯源 3/3 ✅（三篇）",
         "why": "工件值不可由第三方重导出（无文件名/哈希），'✅'只能视为作者自述 + 内部舍入自洽"},
        {"claim": "数字溯源误差 < 0.01%（舍入误差范围内）",
         "why": f"相对读法下最大偏差 {numeric['max_rel_dev_pct']:.4f}%，{len(rel_fail)}/9 对超该阈值"},
        {"claim": "质检标准：结构五节 … 结论不超证据（六项）", "why": "逐篇只留 4 项结果，两项无留痕"},
        {"claim": "65 → PASS（图件缺失但有理由）", "why": "理由未被引用，无法与 66 的 RESUBMIT 区分"},
        {"claim": "已派返工单 #155", "why": "无工单 locator/状态证据"},
    ],
    "remediation": [
        "阻断：先产出并落库 wp-79-01（report 79 的知识对象/资产登记），本包重跑",
        "数字溯源改成可重放格式：artifactId#<file>.json@sha256:<hash>",
        "容差判据改为确定性表述（按打印精度四舍五入相等），输出绝对差/相对差两列",
        "汇总表补齐'结构五节'与'结论不超证据'两列，或把标准收缩到实际执行的 4 项",
        "图件判据写成 rubric 并逐字引用 65 的理由，否则 65 与 66 同档处置",
        "返工单/质检文档给 locator 或内容哈希；报告 64 的误差给数值或显式 not_applicable",
    ],
    "unresolved": UNRESOLVED,
    "artifacts": {
        "source_frozen": {"path": "docs/kf/wp-79-04/source.md", "sha256": source_hash,
                          "chars": len(src_bytes.decode("utf-8"))},
        "checks": "runs/wp-79-04/checks.json",
        "figure": "docs/kf/wp-79-04/review_checks.png",
        "review_prompt": "docs/kf/wp-79-04/review_prompt.md",
        "repro_cmd": "python3 scripts/kf_wp7904_review.py && python3 scripts/emit_wp7904_result.py",
    },
    "emitted_at": datetime.now(timezone.utc).isoformat(),
}

OUT_DIR.joinpath("review_report.json").write_text(
    json.dumps(review_report, ensure_ascii=False, indent=2), encoding="utf-8")

event = {
    "id": "tkr:review-report:wp-79-04",
    "object_ref": "wp-79-01",
    "object_version": f"report_id=79@{source_hash}",
    "decision": "request-changes",
    "reviewer": {"id": "m15631", "reviewer_type": "agent", "role": "red-team-reviewer"},
    "reviewed_at": review_report["emitted_at"],
    "policy_version": "GATE-RULES-v1 (M1-M6) / PRODUCTION-LINE-v1 2.4",
    "rationale": "上游 wp-79-01 不可达使 fidelity 轴 not_run；来源报告自身 1 blocking + 4 major 缺陷。",
    "findings": [{"severity": f["severity"], "finding": f"{f['id']} {f['title']}"} for f in FINDINGS],
    "conditions": ["wp-79-01 落库后重跑本包",
                   "溯源与容差按 remediation 修正后才可再次送审"],
}
OUT_DIR.joinpath("review_events.json").write_text(
    json.dumps([event], ensure_ascii=False, indent=2), encoding="utf-8")

def _claim_ev(ev: list[dict]) -> list[dict]:
    """Envelope claims: schema allows only quote/source_field/note (no offsets)."""
    return [{"quote": e["quote"], "source_field": e["source_field"],
             "note": f"source.md[{e['start_offset']}:{e['end_offset']}]"} for e in ev]


envelope = {
    "package_id": PACKAGE_ID,
    "task_type": "04-independent-review",
    "report_id": REPORT_ID,
    "provenance": {
        "source_hash": source_hash,
        "source_field": "markdown",
        "producer": "m15631 (red-team-reviewer, independent of wp-79-01 producer)",
        "emitted_at": review_report["emitted_at"],
        "notes": "provenance.source_hash recomputed from docs/kf/wp-79-04/source.md; "
                 "equals the contract input.source_hash",
    },
    "outputs": {"review_report.json": review_report},
    "claims": [dict(c, evidence=_claim_ev(c["evidence"])) for c in CLAIMS],
}
OUT_DIR.joinpath("kf_result.wp-79-04.json").write_text(
    json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps({"verdict": review_report["verdict"], "findings": len(FINDINGS),
                  "by_severity": {s: sum(1 for f in FINDINGS if f["severity"] == s)
                                  for s in ("blocking", "major", "minor", "informational")},
                  "claims": len(CLAIMS),
                  "out": ["docs/kf/wp-79-04/review_report.json",
                          "docs/kf/wp-79-04/review_events.json",
                          "docs/kf/wp-79-04/kf_result.wp-79-04.json"]}, ensure_ascii=False))