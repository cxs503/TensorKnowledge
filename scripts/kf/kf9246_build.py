"""wp-9246-02 主流水线：取源自证 -> 信号探针 -> 类型判定 -> 结构切分 -> 自检落盘。

用法（工作树根 = 仓库检出）：
  python3 scripts/kf/kf9246_build.py                    # 从平台 API 取源
  python3 scripts/kf/kf9246_build.py --markdown-file X  # 用本地 md（仍强制校验哈希）
  python3 scripts/kf/kf9246_build.py --check-only       # 只重跑自检（读已落盘信封）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kf9246_spec as S  # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def login_token() -> str:
    import os
    req = urllib.request.Request(
        S.api_base() + "/auth/login",
        data=json.dumps({"username": os.environ.get("TENSOR_AGENT_USER", ""),
                         "password": os.environ.get("TENSOR_AGENT_PASS", "")}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def fetch_record() -> dict:
    req = urllib.request.Request(
        S.api_base() + f"/tensor/reports/{S.REPORT_ID}",
        headers={"Authorization": "Bearer " + login_token()})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def char_to_byte(md: str, idx: int) -> int:
    return len(md[:idx].encode("utf-8"))


def line_of(md: str, idx: int) -> int:
    return md.count("\n", 0, max(0, idx)) + 1


def resolve_anchor(md: str, anchor: str) -> tuple[int, int]:
    first = md.find(anchor)
    if first < 0:
        raise SystemExit(f"FATAL: anchor not found verbatim in source: {anchor!r}")
    if md.find(anchor, first + 1) >= 0:
        raise SystemExit(f"FATAL: anchor not unique in source: {anchor!r}")
    return first, first + len(anchor)


def sections(md: str) -> list[dict]:
    import re
    heads = [(m.start(), len(m.group(1)), m.group(2).strip())
             for m in re.finditer(r"(?m)^(#{1,6})\s+(.+)$", md)]
    out = []
    for i, (start, level, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(md)
        body = md[start:end]
        out.append({
            "index": i + 1, "level": level, "title": title,
            "start_offset": start, "end_offset": end,
            "byte_start": char_to_byte(md, start), "byte_end": char_to_byte(md, end),
            "line_start": line_of(md, start), "line_end": line_of(md, end - 1),
            "chars": end - start, "sha256": sha256_text(body),
        })
    return out


def scan_signals(md: str) -> dict:
    import re
    result = {}
    for rtype, probes in S.PROBES.items():
        rows = []
        for signal, pattern in probes:
            if pattern == "@DERIVED@":
                cites = len(re.findall(r"\((?:19|20)\d{2}\)", md))
                density = cites * 1000.0 / len(md)
                rows.append({"signal": signal, "kind": "derived",
                             "formula": "count(year-in-parens) * 1000 / len(markdown)",
                             "count": cites, "value": round(density, 4),
                             "threshold": 5.0, "hit": density >= 5.0})
                continue
            matches = list(re.finditer(pattern, md))
            row = {"signal": signal, "kind": "regex", "pattern": pattern,
                   "count": len(matches), "hit": bool(matches)}
            if matches:
                m = matches[0]
                row["first_hit"] = {"quote": m.group(0), "start_offset": m.start(),
                                    "end_offset": m.end(), "line": line_of(md, m.start())}
            rows.append(row)
        hits = sum(1 for r in rows if r["hit"])
        result[rtype] = {"signals": rows, "hits": hits, "total": len(rows),
                         "coverage": round(hits / len(rows), 4)}
    return result


def branch_jump_probe(md: str) -> dict:
    """自检探针：按原文逐字公式复算原文自述的 ε=0.8 处拖曳系数跳变量级。

    两种 Re 约定都算（原文写 C_D(εRe) 但未给 Re 定义）：
      A: Re = ρ_f|u|d/μ（字面读法）   B: Re = ρ_f ε|u| d/μ（按 C_D(εRe) 读法）
    u 扫描区间取原文自身出现的两个工况端点 2.0×10⁻³ … 5.0×10⁻² 并外延到 1.0×10⁻¹。
    本探针只复算原文公式的量级，不改报告结论。
    """
    mu, rho_f, d, eps = 1.0e-3, 998.0, 1.0e-3, 0.8
    v_p = math.pi * d ** 3 / 6.0
    a_p = math.pi * d ** 2 / 4.0

    def c_ergun(u):
        return v_p * (150 * mu * (1 - eps) / (eps ** 3 * d ** 2)
                      + 1.75 * rho_f * u / (eps ** 3 * d))

    def c_wenyu(u, use_eps_re):
        re_p = rho_f * (eps * u if use_eps_re else u) * d / mu
        cd = 24.0 / re_p * (1 + 0.15 * re_p ** 0.687)
        return 0.5 * rho_f * cd * u * a_p * eps ** (-1.65)

    def jump(u, use_eps_re):
        return (c_wenyu(u, use_eps_re) - c_ergun(u)) / c_ergun(u) * 100.0

    cases = []
    for u in (2.0e-3, 5.0e-2):
        cases.append({"u": u, "c_ergun": c_ergun(u), "c_wenyu_A": c_wenyu(u, False),
                      "c_wenyu_B": c_wenyu(u, True), "jump_A_percent": jump(u, False),
                      "jump_B_percent": jump(u, True)})
    lo, hi, n = 1.0e-3, 1.0e-1, 400
    sweep_a = [jump(lo * (hi / lo) ** (i / (n - 1)), False) for i in range(n)]
    sweep_b = [jump(lo * (hi / lo) ** (i / (n - 1)), True) for i in range(n)]
    mag_lo = min(min(abs(x) for x in sweep_a), min(abs(x) for x in sweep_b))
    mag_hi = max(max(abs(x) for x in sweep_a), max(abs(x) for x in sweep_b))
    return {
        "purpose": "只复算原文自述跳变的量级，不改报告结论，供 03/04 复核",
        "inputs": {"mu": mu, "rho_f": rho_f, "d": d, "epsilon": eps,
                   "input_source": "μ/ρ_f/d 取原文 Packed Bed 配置；ε=0.8 为原文 Gidaspow 切换点"},
        "re_conventions": {"A": "Re = ρ_f|u|d/μ（字面读法）",
                           "B": "Re = ρ_f ε|u|d/μ（按原文 C_D(εRe) 读法）"},
        "cases": cases,
        "sweep": {"u_min": lo, "u_max": hi, "samples": n,
                  "abs_jump_min_percent": mag_lo, "abs_jump_max_percent": mag_hi},
        "report_claim_percent": 25.0,
        "report_claim_inside_probe_range": bool(mag_lo <= 25.0 <= mag_hi),
        "status": "unresolved_probe",
        "implication": ("按原文 §2 逐字分支公式与原文自身参数，ε=0.8 处线性拖曳系数的跳变幅度"
                        "落在上面 sweep 区间内、符号为负；原文正文称 ~25%。两者不一致，"
                        "可能原因：原文公式行是摘要（实现里的 A_p/V_p 归一或 ε 幂次不同），"
                        "或 ~25% 指未说明的工况。本包不下断言，登记为 UR-03 交 03/04 复核。"),
    }


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def build(md: str, record: dict) -> tuple[dict, dict]:
    if sha256_text(md) != S.SOURCE_HASH or len(md) != S.SOURCE_CHARS:
        raise SystemExit(f"FATAL: source hash/chars mismatch: {sha256_text(md)} "
                         f"chars={len(md)} (contract {S.SOURCE_HASH} chars={S.SOURCE_CHARS})")

    secs = sections(md)
    sig = scan_signals(md)

    evidence = []
    for eid, (anchor, field) in S.ANCHORS.items():
        start, end = resolve_anchor(md, anchor)
        quote = md[start:end]
        evidence.append({
            "id": eid, "field": field,
            "locator": {"locator_type": "char_span", "start_offset": start, "end_offset": end,
                        "byte_start": char_to_byte(md, start), "byte_end": char_to_byte(md, end),
                        "line_start": line_of(md, start), "line_end": line_of(md, end - 1),
                        "quote": quote, "content_hash": sha256_text(quote), "chars": len(quote)},
            "bound_section": next((s["title"] for s in secs
                                   if s["start_offset"] <= start < s["end_offset"]), None),
            "epistemic_status": "draft", "assessment_status": "unassessed",
        })
    ev_ids = {e["id"] for e in evidence}

    eligible = [t for t in S.PROBES if sig[t]["hits"] >= 2]
    stepfit = {}
    for t in S.PROBES:
        rows = S.STEP_FIT[t]
        ok = sum(1 for r in rows if r[1] == "satisfiable")
        evaluated = sum(1 for r in rows if r[1] != "not_evaluated")
        stepfit[t] = {"steps": [{"step_id": r[0], "verdict": r[1], "evidence": r[2]} for r in rows],
                      "satisfiable": ok, "evaluated": evaluated,
                      "all_satisfiable": bool(evaluated and ok == evaluated)}
        for r in rows:
            if r[2]:
                assert r[2] in ev_ids or r[2].startswith("UR-"), r[2]

    finals = [t for t in eligible if stepfit[t]["all_satisfiable"]]
    primary = max(finals, key=lambda t: sig[t]["hits"]) if finals else "unclassified"
    r3 = len(finals) > 1

    alt = []
    for t in sorted((x for x in S.PROBES if x != primary),
                    key=lambda x: (-sig[x]["hits"], x)):
        if t in eligible and not stepfit[t]["all_satisfiable"]:
            why = "R2 不满足：registry step 无法由原文满足（见 signals.step_fit）"
        elif t not in eligible:
            why = "R1 未达标：registry identify_signals 命中 < 2 条"
        else:
            why = "R2 打平后被 R3/R4 排除"
        alt.append({"report_type": t, "signals_hit": sig[t]["hits"],
                    "signals_total": sig[t]["total"],
                    "stepfit_all_satisfiable": stepfit[t]["all_satisfiable"],
                    "why_not_primary": why})

    registry = json.loads(S.REGISTRY.read_text())
    skill = next(s for s in registry["skills"] if s["report_type"] == primary)
    sec_map = {"method": ["Methodology"],
               "numerical setup": ["Geometry and Parameters", "Methodology"],
               "results": ["Computational Results"],
               "convergence": ["Criterion 6: Time-Step Convergence"],
               "introduction": ["Case Introduction"],
               "validation": ["Computational Results", "Error Assessment"],
               "uncertainty": ["Error Assessment"],
               "setup": ["Case Introduction"],
               "comparison": ["Computational Results"]}
    mapped = []
    for w in skill["applies_to"]["sections"]:
        hits = [s for s in secs if s["title"] in sec_map.get(w, [])]
        mapped.append({"skill_section": w,
                       "matched_report_sections": [h["title"] for h in hits],
                       "locators": [{"title": h["title"], "start_offset": h["start_offset"],
                                     "end_offset": h["end_offset"], "line_start": h["line_start"],
                                     "line_end": h["line_end"]} for h in hits],
                       "status": "mapped" if hits else "not_found"})

    classification = {
        "schema": "kf-classification.v1",
        "package_id": S.PACKAGE_ID, "task_type": S.TASK_TYPE, "report_id": S.REPORT_ID,
        "source": {"source_uri": S.SOURCE_URI, "source_field": S.SOURCE_FIELD,
                   "declared_source_hash": S.SOURCE_HASH,
                   "recomputed_source_hash": sha256_text(md), "source_hash_matches": True,
                   "declared_chars": S.SOURCE_CHARS, "chars": len(md),
                   "bytes_utf8": len(md.encode("utf-8")), "lines": md.count("\n") + 1,
                   "title_line_evidence": "EV-01",
                   "record_title": record.get("title"),
                   "scenario_key_in_contract": S.SCENARIO_KEY,
                   "scenario_key_in_record": record.get("scenario_key"),
                   "record_mission_id": record.get("mission_id"),
                   "record_status": record.get("status")},
        "taxonomy": {"registry": "extraction-skills/registry.json",
                     "registry_version": registry["registry_version"],
                     "candidate_types": registry["report_types"],
                     "identity_signals_source": "registry.skills[].identify_signals",
                     "note": registry["note"]},
        "report_type": {"primary": primary,
                        "status": "classified" if primary != "unclassified" else "unclassified",
                        "confidence": "medium",
                        "classification_is_hypothesis": True,
                        "reversible_by_review": True,
                        "declared_alternatives": alt,
                        "decision_trace": {
                            "rule": S.DECISION_RULE,
                            "eligible_after_R1": eligible,
                            "all_steps_satisfiable": finals,
                            "R3_triggered": r3,
                            "note": ("R2 唯一决胜，R3 未被触发；EV-02/EV-18 仍登记为自述目的逐字证据"
                                     if not r3 else "R2 打平，按 R3 以自述目的句决定")}},
        "selected_skill": {"skill_id": skill["skill_id"], "skill_version": skill["skill_version"],
                           "lifecycle_state": skill["lifecycle_state"],
                           "applies_to_sections": skill["applies_to"]["sections"],
                           "steps": [s["step_id"] for s in skill["steps"]],
                           "section_mapping": mapped,
                           "lifecycle_caveat": ("registry.note 明示所有 skill 仍为 template-created，"
                                                "尚无真实代表性报告走通全链；本包只登记选中，不宣称已验证。")},
        "signals": {"method": "正则探针扫描 + 派生量公式；命中次数与首次命中逐字切片见各行",
                    "per_type": sig, "step_fit": stepfit,
                    "probe_disclosure": ("探针是按 registry identify_signals 语义设计的字符串/正则，"
                                         "不是原文自带元数据；命中计数可复核，语义等价性留给 04 审核。")},
        "structure": {"segmentation_rule": "按 1–6 级 ATX 标题行切段，行首到下一标题行前为一段（含标题行）",
                      "heading_count": len(secs), "sections": secs},
        "probe_result": branch_jump_probe(md),
        "decision_basis": DECISION_BASIS,
        "evidence": evidence,
        "unresolved": UNRESOLVED,
        "claims_note": ("task_type=02-classification-parse 不做知识抽取：本包不产生 claims，"
                        "也绝不给报告任何结论打 verified；report_type 同样只是可反驳的假设"),
        "scope_guard": {"report_ids_read": [S.REPORT_ID], "report_ids_written": [S.REPORT_ID],
                        "upstream_artifacts_modified": [], "other_work_packages_touched": []},
    }
    result = {"package_id": S.PACKAGE_ID, "task_type": S.TASK_TYPE,
              "contract_version": S.CONTRACT_VERSION, "report_id": S.REPORT_ID,
              "provenance": {"source_uri": S.SOURCE_URI, "source_field": S.SOURCE_FIELD,
                             "source_hash": S.SOURCE_HASH, "source_hash_matches": True,
                             "title": S.SOURCE_TITLE, "scenario_key": S.SCENARIO_KEY,
                             "chars": S.SOURCE_CHARS},
              "outputs": {"classification.json": classification}}
    return classification, result


DECISION_BASIS = [
    {"id": "DB-01", "evidence": ["EV-02"],
     "statement": "报告自述目的是验证两条闭合关系（Ergun 压降、Richardson-Zaki 沉降），不是提出新方法或新方案。",
     "epistemic_status": "draft", "assessment_status": "unassessed"},
    {"id": "DB-02", "evidence": ["EV-04", "EV-05"],
     "statement": "原文含可执行闭合关系式（Gidaspow 混合拖曳、单位体积空隙率积分式），scientific-computation 的 governing-equations 信号命中。",
     "epistemic_status": "draft", "assessment_status": "unassessed"},
    {"id": "DB-03", "evidence": ["EV-06", "EV-07"],
     "statement": "原文给出时间离散格式与步长（explicit Euler；dt = 0.1 τ），discretisation 信号命中。",
     "epistemic_status": "draft", "assessment_status": "unassessed"},
    {"id": "DB-04", "evidence": ["EV-08", "EV-09"],
     "statement": "原文含独立收敛性判据章节（Criterion 6，dt → dt/2），convergence-study 信号命中。",
     "epistemic_status": "draft", "assessment_status": "unassessed"},
    {"id": "DB-05", "evidence": ["EV-10", "EV-11", "EV-12", "EV-13"],
     "statement": "原文的误差陈述都配有明确参照（Ergun 关联式、Schiller-Naumann 解析解、Richardson-Zaki 关联式），满足 extract-accuracy-statements 的前提。",
     "epistemic_status": "draft", "assessment_status": "unassessed"},
    {"id": "DB-06", "evidence": ["EV-15"],
     "statement": "原文含建模假设/局限清单，满足 extract-assumptions step。",
     "epistemic_status": "draft", "assessment_status": "unassessed"},
    {"id": "DB-07", "evidence": ["EV-03", "EV-10", "EV-20"],
     "statement": "experimental-validation 虽在 test-matrix / validation-case / baseline-comparison 三条信号命中，但其 registry step extract-uncertainty 要求逐字照抄不确定度与包含因子，原文只有数值误差来源讨论，step-fit 不满足。",
     "epistemic_status": "draft", "assessment_status": "unassessed"},
    {"id": "DB-08", "evidence": ["EV-16", "EV-17"],
     "statement": "software-engineering 只在 Audit Trail 出现模块/测试字样，changed-files/commit/interface/regression/API 信号 0 命中，不是变更说明类报告。",
     "epistemic_status": "draft", "assessment_status": "unassessed"},
    {"id": "DB-09", "evidence": ["EV-19"],
     "statement": "原文引用密度远低于 literature-review 阈值（见 signals 派生量），且无 related work / survey / bibliography 结构。",
     "epistemic_status": "draft", "assessment_status": "unassessed"},
]

UNRESOLVED = [
    {"id": "UR-01",
     "question": "主类型 scientific-computation 与备选 experimental-validation 在 registry 信号命中上同为 3/5，分类结论是否会被独立审核推翻？",
     "reason": "两型语义相邻（数值实验的验证）；本包只按事先声明的 R2（step-fit）定胜负，未做语义投票。",
     "status": "unresolved", "suggested_handler": "工序 04 独立审核（reviewer_role=document-analyst）"},
    {"id": "UR-02",
     "question": "报告是否含测量不确定度与包含因子（experimental-validation 的 extract-uncertainty 前提）？",
     "reason": "全文探针 'measurement uncertainty|coverage factor|uncertainty budget' 0 命中；仅在 Error Sources 讨论数值误差来源，不能等同于测量不确定度声明。",
     "status": "unresolved",
     "suggested_handler": "若审核者认为数值误差来源等价于不确定度声明，则类型结论需复议"},
    {"id": "UR-03",
     "question": "报告称 ε=0.8 处拖曳系数有 ~25% 跳变；按原文逐字分支公式复算，|跳变| 落在 39.8%–70.4%（见 probe_result），两者不一致。",
     "reason": "原文未给 ~25% 的计算过程与工况；本包只对原文公式行做量级探针，不下断言、不改报告结论。可能原因：公式行是摘要（A_p/V_p 归一或 ε 幂次不同），或该 25% 指未说明的工况。",
     "status": "unresolved", "suggested_handler": "工序 03/04 复核（需 closure 实现与原文公式一致）"},
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown-file", type=Path)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args(argv)

    S.OUT_DIR.mkdir(parents=True, exist_ok=True)
    S.MIRROR_DIR.mkdir(parents=True, exist_ok=True)

    if args.check_only:
        saved = json.loads((S.OUT_DIR / "kf_result.json").read_text())
        md = (S.MIRROR_DIR / "source_markdown.md").read_text()
        classification = saved["outputs"]["classification.json"]
    else:
        if args.markdown_file:
            md = args.markdown_file.read_text()
            record = {"title": S.SOURCE_TITLE, "scenario_key": S.SCENARIO_KEY,
                      "mission_id": S.MISSION_ID, "status": "local-file"}
        else:
            rec = fetch_record()
            md = rec.get("markdown", "")
            record = {k: v for k, v in rec.items() if k != "markdown"}
        classification, saved = build(md, record)
        (S.OUT_DIR / "classification.json").write_text(
            json.dumps(classification, ensure_ascii=False, indent=2) + "\n")
        (S.OUT_DIR / "kf_result.json").write_text(
            json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
        (S.MIRROR_DIR / "source_markdown.md").write_text(md)
        # 离线测试夹具：带哈希的源快照（fresh clone 也能跑回归，不取网）
        S.FIXTURE_MD.parent.mkdir(parents=True, exist_ok=True)
        S.FIXTURE_MD.write_text(md)
        (S.FIXTURE_MD.parent / "meta.json").write_text(json.dumps(
            {"report_id": S.REPORT_ID, "source_uri": S.SOURCE_URI, "field": S.SOURCE_FIELD,
             "sha256": sha256_text(md), "chars": len(md)}, ensure_ascii=False, indent=2) + "\n")

    import kf9246_checks as CHK
    checks = CHK.run_checks(saved, classification, md, S.OUT_DIR)
    (S.OUT_DIR / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")

    import kf9246_figure as FIG
    png = FIG.make_figure(classification, S.OUT_DIR / "figures" / "classification_decision.png")

    import kf9246_report as RPT
    text = RPT.build_report(saved, classification, checks, png)
    (S.OUT_DIR / f"KF-RESULT-{S.PACKAGE_ID}.md").write_text(text)

    # A9 依赖报告文件已存在 -> 重跑一次报告相关检查
    checks = CHK.run_checks(saved, classification, md, S.OUT_DIR)
    (S.OUT_DIR / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")

    # 镜像到 artifacts/
    for name in ("classification.json", "kf_result.json", "checks.json"):
        (S.MIRROR_DIR / name).write_text((S.OUT_DIR / name).read_text())
    (S.MIRROR_DIR / "figures").mkdir(exist_ok=True)
    (S.MIRROR_DIR / "figures" / "classification_decision.png").write_bytes(png.read_bytes())
    (S.MIRROR_DIR / "kf_result_wp-9246-02.json").write_text(
        (S.OUT_DIR / "kf_result.json").read_text())

    print(json.dumps({"ok": checks["ok"],
                      "primary": classification["report_type"]["primary"],
                      "checks": [{"c": c["check"], "s": c["status"]} for c in checks["checks"]]},
                     ensure_ascii=False, indent=2))
    return 0 if checks["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())