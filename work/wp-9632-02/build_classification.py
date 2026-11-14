"""wp-9632-02 · 02-classification-parse 产物构建器（report_id=9632 单一报告）。

设计原则（对齐工作包契约 constraints）：
* **零手抄**：所有 quote 由本脚本按「选择器」从源 markdown 机器切片所得，
  人只给定位模式（行内片段 / 小节标题），从不在代码里重述原文数字或公式。
* **偏移量即契约**：每条证据给出 start_offset/end_offset（Python str 字符偏移，
  与 ke.wp_gate.locator_matches 的语义一致）+ content_hash（quote 的 sha256）。
* **不做抽取**：本包只产出报告类型、主题标签与结构切分；不产生 claim/evidence 知识对象。
* **不标 verified**：状态一律 classified_draft / not_found_in_source，verification 由平台门计算。

用法：
    python work/wp-9632-02/build_classification.py [--source work/wp-9632-02/source_9632.md]
缺省 source 由 $TENSOR_API_BASE/tensor/reports/9632 拉取（Bearer 登录），
并与契约声明的 source_hash 比对，不一致直接退出（fail-closed）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPORT_ID = "9632"
PACKAGE_ID = "wp-9632-02"
TASK_TYPE = "02-classification-parse"
SRC_URI = "tensor://reports/9632"
EXPECTED_HASH = "sha256:b2c5eb5dad0b6db25574338b37aa5be1c8fdf20bbc7d3c75640e1c1727756841"
EXPECTED_CHARS = 10749
PKG = Path(__file__).resolve().parent


# --------------------------------------------------------------------------- 源文本
def _token() -> str:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        base + "/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def fetch_markdown() -> str:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    req = urllib.request.Request(
        f"{base}/tensor/reports/{REPORT_ID}",
        headers={"Authorization": "Bearer " + _token()},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        record = json.loads(r.read())
    assert str(record["id"]) == REPORT_ID, record.get("id")
    return record["markdown"]


def load_source(path: Path | None) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8") if path and path.is_file() else fetch_markdown()
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != EXPECTED_HASH:
        sys.exit(f"FAIL source_hash_mismatch: recomputed {digest} != contract {EXPECTED_HASH}")
    if len(text) != EXPECTED_CHARS:
        sys.exit(f"FAIL chars_mismatch: {len(text)} != contract {EXPECTED_CHARS}")
    return text, digest


# --------------------------------------------------------------------------- 选择器
def _line_span(text: str, needle: str) -> tuple[int, int]:
    """整行切片：包含 needle 的唯一一行（含行首，不含换行符）。"""
    hits = [m.start() for m in re.finditer(re.escape(needle), text)]
    if len(hits) != 1:
        sys.exit(f"FAIL selector not unique ({len(hits)} hits): {needle!r}")
    start = text.rfind("\n", 0, hits[0]) + 1
    end = text.find("\n", hits[0])
    end = len(text) if end < 0 else end
    return start, end


def _block_span(text: str, heading_needle: str) -> tuple[int, int]:
    """小节整块：从 heading 行首到下一个同级或更高级标题之前。"""
    start, _ = _line_span(text, heading_needle)
    level = len(heading_needle) - len(heading_needle.lstrip("#"))
    pat = re.compile(r"^#{1,%d} " % level, re.M)
    nxt = pat.search(text, start + 1)
    end = nxt.start() if nxt else len(text)
    return start, end.rstrip("\n").__len__() + start


def span(text: str, sel: dict) -> tuple[int, int]:
    kind = sel["type"]
    if kind == "line":
        return _line_span(text, sel["contains"])
    if kind == "block":
        return _block_span(text, sel["heading"])
    if kind == "section_between":
        s, _ = _line_span(text, sel["start"])
        e, _ = _line_span(text, sel["end"])
        return s, e
    sys.exit(f"FAIL unknown selector {kind}")


def evidence(text: str, ev_id: str, locator_type: str, value: str, sel: dict,
             covers: list[str] | None = None) -> dict:
    s, e = span(text, sel)
    quote = text[s:e]
    if len(quote) < 12:
        sys.exit(f"FAIL quote too short for {ev_id}: {quote!r}")
    if text.find(quote) != s:
        sys.exit(f"FAIL quote not verbatim at offsets for {ev_id}")
    return {
        "id": ev_id,
        "locator_type": locator_type,
        "value": value,
        "quote": quote,
        "start_offset": s,
        "end_offset": e,
        "content_hash": "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "covers": [],  # 由 signals 表反推，不在证据处手写（防止陈旧 id 混入）
    }


# --------------------------------------------------------------------------- 结构切分
def _count_table_blocks(text: str) -> int:
    """连续 >=2 行的 pipe 表行记为一个表块。"""
    blocks, run = 0, 0
    for line in text.splitlines():
        if line.startswith("|") and line.rstrip().endswith("|"):
            run += 1
        else:
            blocks += 1 if run >= 2 else 0
            run = 0
    return blocks + (1 if run >= 2 else 0)


def sections(text: str) -> list[dict]:
    heads = [(m.start(), m.group(0)) for m in re.finditer(r"^#{1,3} .*$", text, re.M)]
    out: list[dict] = []
    for i, (pos, line) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        heading = line.lstrip("#").strip()
        out.append(
            {
                "id": f"sec-{i + 1:02d}",
                "level": len(line) - len(line.lstrip("#")),
                "heading": heading,
                "start_offset": pos,
                "end_offset": end,
                "chars": end - pos,
            }
        )
    return out


def build(text: str, digest: str) -> dict:
    # ---- 候选报告类型判据（extraction-skills/registry.json 的 identify_signals）
    EV: list[dict] = []

    def add(ev_id, ltype, value, sel, covers=None):
        EV.append(evidence(text, ev_id, ltype, value, sel))

    # scientific-computation
    add("ev-sc-eq", "equation_block", "Stefan 定律（含孔隙率修正）核心方程",
        {"type": "line", "contains": r"$$h_c=\sqrt{"}, ["sig-sc-01"])
    add("ev-sc-disc", "method_paragraph", "一维焓法离散方案",
        {"type": "line", "contains": "是显式守恒焓法"}, ["sig-sc-02"])
    add("ev-sc-conv", "result_paragraph", "网格收敛与相对误差",
        {"type": "line", "contains": "网格数值解"}, ["sig-sc-03", "sig-sc-04"])
    add("ev-sc-mesh", "table_header", "网格加密表",
        {"type": "line", "contains": "| 网格 N |"}, ["sig-sc-04"])
    add("ev-sc-tool", "toolchain_paragraph", "工具链（无计时表）",
        {"type": "line", "contains": "matplotlib 出图"}, ["sig-sc-05"])
    # experimental-validation
    add("ev-ev-base", "baseline_comparison", "k_eff 与 Maxwell-Eucken 并联参照逐行对比",
        {"type": "line", "contains": "| 0.30 | 1.6296 |"}, ["sig-ev-05"])
    add("ev-ev-case", "validation_case", "独立算术路径的手算校核",
        {"type": "line", "contains": "手算是一条独立算术路径"}, ["sig-ev-04"])
    add("ev-ev-matrix", "parameter_sweep", "参数扫描矩阵",
        {"type": "line", "contains": "最大相对偏差 = "}, ["sig-ev-01"])
    add("ev-ev-uncert", "uncertainty_statement", "文献观测分散量级",
        {"type": "line", "contains": "观测分散本身"}, ["sig-ev-03"])
    # algorithm-implementation
    add("ev-alg-fn", "code_identifier", "求解器函数标识符",
        {"type": "line", "contains": "`thermal.solve_porous_stefan_1d`"}, ["sig-alg-04"])
    # software-engineering
    add("ev-swe-test", "test_evidence", "测试套件规模",
        {"type": "line", "contains": "tests/test_ice_ridge_consolidation.py"}, ["sig-swe-04"])
    # literature-review（引用密度）
    add("ev-lit-cite", "citation", "唯一文献锚（Leppäranta & Hakala 1992）",
        {"type": "line", "contains": "Leppäranta & Hakala 1992"}, ["sig-lit-04"])

    # ---- 主题标签证据
    add("ev-top-01", "section_paragraph", "固结层为控制量（学科问题界定）",
        {"type": "line", "contains": "真正挡住它的是"}, ["top-01"])
    add("ev-top-02", "method_paragraph", "Neumann 相似解形式",
        {"type": "line", "contains": r"h_c(t)=2\lambda\sqrt{\kappa t}"}, ["top-02"])
    add("ev-top-03", "method_paragraph", "冰骨架+卤水通道并联导热网络",
        {"type": "line", "contains": "并联（等应变）网络"}, ["top-03"])
    add("ev-top-04", "method_paragraph", "阻力两项分解",
        {"type": "line", "contains": "阻力按单位宽度分解为两项"}, ["top-04"])
    # ---- 不确定性 / 局限保留（preserve_uncertainty）
    add("ev-cav-01", "limitation", "文献锚是导出带而非数字化观测",
        {"type": "line", "contains": "文献锚值是「导出带」"}, ["cav-01"])
    add("ev-cav-02", "limitation", "雪敏感性导致落到文献带下方",
        {"type": "line", "contains": "雪的敏感性很大"}, ["cav-02"])
    add("ev-cav-03", "limitation", "强度为上界值",
        {"type": "line", "contains": "为小试样单轴抗压"},
        ["cav-03"])
    add("ev-cav-04", "limitation", "阻力模型为平面应变塑性极限载荷",
        {"type": "line", "contains": "阻力模型是平面应变塑性极限载荷"}, ["cav-04"])

    CITES = len(re.findall(r"(?:19|20)\d{2}", text))
    CITE_DENSITY = CITES * 1000.0 / len(text)

    signals = [
        # report_type, signal(registry 原文), match, evidence_id, note[, context_ev_id]
        ("scientific-computation", "governing equations", "matched", "ev-sc-eq",
         "核心控制方程为含孔隙率修正的 Stefan 平衡（registry 信号为英文，源报告为中文，按语义比对）"),
        ("scientific-computation", "discretisation", "matched", "ev-sc-disc",
         "显式守恒焓法、固定网格、Dirichlet 冷面 + 远端零通量"),
        ("scientific-computation", "convergence study", "matched", "ev-sc-conv",
         "50→400 网格的前缘与相对误差序列"),
        ("scientific-computation", "mesh refinement", "matched", "ev-sc-mesh",
         "网格加密表（N、Δx、Δt、前缘、误差）"),
        ("scientific-computation", "timing table", "absent", None,
         "源报告无计时/性能表；最近似段落为工具链描述，不足以判定 matched", "ev-sc-tool"),
        ("experimental-validation", "test matrix", "partial", "ev-ev-matrix",
         "有 φ×饱和度 参数扫描矩阵，但不是实验试次矩阵（无试件/工况编号）"),
        ("experimental-validation", "facility", "absent", None,
         "无试验设施、量测布置或台架描述", None),
        ("experimental-validation", "measurement uncertainty", "partial", "ev-ev-uncert",
         "仅有文献观测分散量级，非本工作的测量不确定度评定"),
        ("experimental-validation", "validation case", "partial", "ev-ev-case",
         "以手算/解析解为参照的验证算例，非实测验证案例"),
        ("experimental-validation", "baseline comparison", "matched", "ev-ev-base",
         "并列给出模型/并联/串联/ME-1 与相对偏差的基线比较行"),
        ("algorithm-implementation", "pseudocode", "absent", None, "无伪代码"),
        ("algorithm-implementation", "complexity", "absent", None, "无复杂度分析"),
        ("algorithm-implementation", "algorithm block", "partial", "ev-alg-fn",
         "有求解器模块/函数划分，非算法块", None),
        ("algorithm-implementation", "function signature", "partial", "ev-alg-fn",
         "仅出现点分函数名，无签名（参数/返回）"),
        ("algorithm-implementation", "O(n", "absent", None, "无 Big-O 记号"),
        ("software-engineering", "changed files", "absent", None, "无变更文件清单"),
        ("software-engineering", "commit", "absent", None, "无提交号/分支"),
        ("software-engineering", "interface", "absent", None, "无对外接口契约描述"),
        ("software-engineering", "regression", "partial", "ev-swe-test",
         "有测试套件与全通过陈述，但无回归对比基线"),
        ("software-engineering", "API", "absent", None, "无 API 端点/协议描述"),
        ("technical-proposal", "proposal", "absent", None, "非立项/建议文档"),
        ("technical-proposal", "design", "absent", None, "无设计规格章节"),
        ("technical-proposal", "roadmap", "absent", None, "无路线图"),
        ("technical-proposal", "specification", "absent", None, "无需求规格"),
        ("technical-proposal", "plan", "absent", None, "无实施计划"),
        ("literature-review", "related work", "absent", None, "无相关工作综述"),
        ("literature-review", "state of the art", "absent", None, "无现状梳理"),
        ("literature-review", "survey", "absent", None, "非综述"),
        ("literature-review", "bibliography", "absent", None, "无参考文献表"),
        ("literature-review", "citation density >= 5 per 1000 chars", "absent", None,
         f"程序化统计：年份式引用 {CITES} 次 / {len(text)} 字符 = "
         f"{CITE_DENSITY:.3f} 次/千字符，远低于 5 次/千字符信号阈值", "ev-lit-cite"),
    ]

    sig_records: list[dict] = []
    for i, row in enumerate(signals, 1):
        rtype, signal, match, ev_id, note = row[:5]
        ctx = row[5] if len(row) > 5 else None
        if match == "absent":
            assert ev_id is None, signal
        else:
            assert ev_id is not None, signal
        rec = {
            "id": f"sig-{i:02d}",
            "report_type": rtype,
            "signal": signal,
            "match": match,
            "evidence_id": ev_id,
            "context_evidence_id": ctx,
            "status": "evidenced" if ev_id else "explicitly_absent",
            "note": note,
        }
        sig_records.append(rec)

    score_of = {"matched": 1.0, "partial": 0.5, "absent": 0.0}
    matrix = []
    for rtype in (
        "scientific-computation",
        "experimental-validation",
        "algorithm-implementation",
        "software-engineering",
        "technical-proposal",
        "literature-review",
    ):
        rs = [s for s in sig_records if s["report_type"] == rtype]
        m = sum(1 for s in rs if s["match"] == "matched")
        p = sum(1 for s in rs if s["match"] == "partial")
        a = sum(1 for s in rs if s["match"] == "absent")
        matrix.append(
            {
                "report_type": rtype,
                "skill_id": "xsk-" + rtype,
                "signals_total": len(rs),
                "matched": m,
                "partial": p,
                "absent": a,
                "score": round((m + 0.5 * p) / len(rs), 3),
                "signal_ids": [s["id"] for s in rs],
            }
        )
    matrix.sort(key=lambda r: (-r["score"], r["report_type"]))
    for rank, row in enumerate(matrix, 1):
        row["rank"] = rank
        row["decision"] = (
            "selected" if rank == 1 else "rejected_secondary"
        )
    if matrix[0]["score"] <= 0.0:
        sys.exit("FAIL no candidate report type reached a positive signal score")

    top, second = matrix[0], matrix[1]
    assert top["report_type"] == "scientific-computation", matrix

    # 覆盖关系反向补全：evidence.covers -> 由信号表推导
    covers: dict[str, list[str]] = {ev["id"]: list(ev["covers"]) for ev in EV}
    for s in sig_records:
        for key in ("evidence_id", "context_evidence_id"):
            ev_id = s[key]
            if ev_id:
                assert ev_id in covers, (s["id"], ev_id)
                covers[ev_id].append(s["id"])
    for ev in EV:
        ev["covers"] = sorted(set(covers[ev["id"]]))

    body = {
        "schema_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "taxonomy": {
            "name": "extraction-skill-report-type",
            "version": "1.0",
            "source": "extraction-skills/registry.json",
            "report_types": [r["report_type"] for r in matrix],
        },
        "report_type": top["report_type"],
        "status": "classified_draft",
        "selected_skill": {
            "skill_id": top["skill_id"],
            "skill_version": "0.1.0",
            "lifecycle_state": "template-created",
            "selection_basis": (
                f"identify_signals 命中 {top['matched']}/{top['signals_total']} "
                f"(score {top['score']}), 次优 {second['report_type']} score {second['score']}"
            ),
        },
        "confidence": {
            "label": "high",
            "score": top["score"],
            "margin_over_second": round(top["score"] - second["score"], 3),
            "basis": (
                "四个独立 registry 信号（控制方程/离散/收敛研究/网格加密）均有可定位原文；"
                "唯一未命中信号(timing table)不改变类型判定；次优类型仅在验证方法上有部分重合"
            ),
            "falsifier": (
                "若下游定位到本报告主体为实测试验（设施/试次/测量不确定度）而非数值基准，"
                "则应为 experimental-validation"
            ),
        },
        "candidate_matrix": matrix,
        "signals": sig_records,
        "structure": {
            "language": "zh",
            "chars": len(text),
            "lines": text.count("\n") + 1,
            "sections": sections(text),
            "headings": len(re.findall(r"^#{1,3} ", text, re.M)),
            "table_rows": len(re.findall(r"^\|.*\|$", text, re.M)),
            "table_blocks": _count_table_blocks(text),
            "figure_refs": len(re.findall(r"!\[", text)),
            "display_equations": len(re.findall(r"\$\$", text)) // 2,
        },
        "topics": [
            {"id": "top-01", "label": "冰脊固结（consolidated layer）", "kind": "domain",
             "evidence_id": "ev-top-01"},
            {"id": "top-02", "label": "Stefan / Neumann 相变传热", "kind": "method",
             "evidence_id": "ev-top-02"},
            {"id": "top-03", "label": "多孔介质有效导热系数", "kind": "method",
             "evidence_id": "ev-top-03"},
            {"id": "top-04", "label": "冰脊阻力（固结层挤压 + 碎石排开）", "kind": "result",
             "evidence_id": "ev-top-04"},
        ],
        "preserved_uncertainty": [
            {"id": "cav-01", "kind": "evidence_strength",
             "note": "文献锚为导出带（derived_from_literature, exact=False），一致性检验非逐点实验验证",
             "evidence_id": "ev-cav-01"},
            {"id": "cav-02", "kind": "applicability",
             "note": "重雪工况下模型值降到文献带下方；报告未做参数回标，属已知保守侧偏差",
             "evidence_id": "ev-cav-02"},
            {"id": "cav-03", "kind": "upper_bound",
             "note": "强度取小试样单轴抗压上界，未含尺寸效应与应变率软化",
             "evidence_id": "ev-cav-03"},
            {"id": "cav-04", "kind": "model_scope",
             "note": "阻力为平面应变塑性极限载荷，不含船体几何与动力放大，不可用于详细结构设计载荷",
             "evidence_id": "ev-cav-04"},
        ],
        "unresolved": [
            {"id": "unr-01", "item": "timing table 信号",
             "status": "not_found_in_source",
             "note": "全文检索无计时/性能表；不作为分类阻断项"},
            {"id": "unr-02", "item": "facility / 试次矩阵",
             "status": "not_found_in_source",
             "note": "无试验设施与试次描述；据此外推 experimental-validation 的判据缺失"},
            {"id": "unr-03", "item": "图件文件可达性",
             "status": "out_of_scope_deferred",
             "note": "正文引用的 ../artifacts/... 路径属工序 01 资产可达性核验，本包不做"},
            {"id": "unr-04", "item": "上游 asset_manifest.json",
             "status": "out_of_scope_deferred",
             "note": "工序 02 契约声明 register_assets=false，未读取也未改写 01 产物"},
        ],
        "producer_notes": {
            "scope": "02-classification-parse：仅报告类型判定 + 主题标签 + 结构切分；不做 claim 抽取、不做资产登记",
            "method": (
                "以 extraction-skills/registry.json 的 identify_signals 为判据逐条比对："
                "matched=1.0 / partial=0.5 / absent=0.0 加权得分，最高分类型入选，其余显式记 rejected_secondary"
            ),
            "locator_basis": (
                "start_offset/end_offset 为 markdown 字段（Python str）的字符偏移，"
                "语义与 ke.wp_gate.locator_matches 一致；quote 由脚本按选择器机器切片，非手抄"
            ),
            "quote_policy": "每条 quote 均为源 markdown 的逐字子串，content_hash=sha256(quote)",
        },
        "claims_produced": [],
        "claims_status": "not_produced_by_this_process",
        "not_performed": [
            "claim_extraction",
            "asset_registration",
            "verification_verdict",
            "parameter_recomputation",
        ],
        "provenance": {
            "source_uri": SRC_URI,
            "source_field": "markdown",
            "source_hash": digest,
            "source_hash_matches": True,
            "title": "IN101-N07 冰脊固结热力学：龙骨大孔隙再冻结与固结度-阻力耦合",
            "scenario_key": "ice_ridge_consolidation",
            "chars": len(text),
        },
    }
    # 主题 / 局限也走同一套证据账本：covers 统一在此反推，避免两处手写不同步
    extra: dict[str, list[str]] = {ev["id"]: [] for ev in EV}
    for rec in (*body["topics"], *body["preserved_uncertainty"]):
        assert rec["evidence_id"] in extra, rec
        extra[rec["evidence_id"]].append(rec["id"])
    for ev in EV:
        ev["covers"] = sorted(set(ev["covers"]) | set(extra[ev["id"]]))
    body["evidence"] = EV
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=PKG / "source_9632.md")
    ap.add_argument("--out", type=Path, default=PKG / "classification.json")
    args = ap.parse_args()
    text, digest = load_source(args.source)
    body = build(text, digest)
    args.out.write_text(
        json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.out} ({args.out.stat().st_size} bytes) report_type={body['report_type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())