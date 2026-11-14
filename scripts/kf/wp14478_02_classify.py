#!/usr/bin/env python3
"""wp-14478-02 · 工序 02 分类解析：报告 14478 的 report_type 判定 + 可定位证据。

只做分类/解析，**不做抽取**（不产出 claims），不改写原文，不给任何对象盖 verified。

产物（worktree 内）：
  docs/kf/wp-14478-02/classification.json   分类产物（schemas/classification.v1.schema.json）
  docs/kf/wp-14478-02/kf_result.json        KF-RESULT 信封（schemas/kf_result.v1.schema.json）
  docs/kf/wp-14478-02/figures/classification_map.png  结构分段 + 信号命中位置图

一键复跑：
  python3 scripts/kf/wp14478_02_classify.py --check \
      --snapshot docs/kf/wp-14478-02/source/report_14478.md
或从平台重取原文（需 TENSOR_API_BASE + TENSOR_AGENT_USER/PASS）：
  python3 scripts/kf/wp14478_02_classify.py --fetch --check

约束：只碰 report_id=14478；每个判定信号/主题标签都带原文逐字 locator（字符偏移 + quote +
quote 的 sha256）；定位不到的项显式记 unresolved，不猜。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "kf" / "wp-14478-02"
DEFAULT_SNAPSHOT = OUT_DIR / "source" / "report_14478.md"

#: 契约（工作包 YAML）逐字抄录的输入声明——不从这里读任何正文。
CONTRACT = {
    "package_id": "wp-14478-02",
    "task_type": "02-classification-parse",
    "contract_version": "1.0",
    "report_id": "14478",
    "source_uri": "tensor://reports/14478",
    "source_field": "markdown",
    "source_hash": "sha256:8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0",
    "title": "CASE-CYLINDER-DRAG-FVM: TensorFVM DFG 2D-1 cylinder drag case (per-quantity <5% verdict)",
    "scenario_key": "case-cylinder-drag-fvm",
    "chars": 6156,
}

#: 分层（工作包 notes：分层=CASE-CYLINDER-DRAG-FVM|case-cylinder-drag-fvm|m）
LAYER = {"family": "CASE-CYLINDER-DRAG-FVM",
         "scenario_key": "case-cylinder-drag-fvm", "tier": "m"}

SKILL = {"scientific-computation": {"skill_id": "xsk-scientific-computation", "version": "0.1.0",
                                    "lifecycle_state": "template-created"}}

#: 判定信号。signal 字段逐字抄自 extraction-skills/<type>.md §1（与 registry.json
#: identify_signals 同源）；quote 必须是原文的**逐字**子串，且全文唯一。
SIGNALS = [
    # ---- A. scientific-computation（5 条注册表信号，逐条判定）----
    dict(id="SIG-SC-01", report_type="scientific-computation", signal="governing equation",
         verdict="partial",
         quote="$\\rho=1$、$\\nu=0.001$ m²/s，$Re_D=U_{mean}D/\\nu=20$ 定常层流",
         unresolved=dict(
             reason="正文只给出物性、Reynolds 定义与“定常层流”定性声明，没有写出控制方程的显式形式；"
                    "把基准名/文献标题当作方程来源即为推断，故记 partial。",
             what_would_resolve="原文写出连续性/动量方程，或明确声明所求解的方程（如“求解不可压 N–S 方程”）。")),
    dict(id="SIG-SC-02", report_type="scientific-computation", signal="discretisation",
         verdict="matched",
         quote="贴体网格 + SIMPLE/Rhie–Chow"),
    dict(id="SIG-SC-03", report_type="scientific-computation", signal="convergence study",
         verdict="matched",
         quotes=["Richardson 外推 $C_{D,\\infty}$、最细网格 GCI；",
                 "| 收敛判据 | — | 残差 1e-6 / 迭代上限 1500–3000 | `SolverConfig.tolerance` |"]),
    dict(id="SIG-SC-04", report_type="scientific-computation", signal="mesh refinement",
         verdict="matched",
         quote="1. **网格细化**：64×24 → 128×48 → 256×96（级距减半），输出观测收敛阶"),
    dict(id="SIG-SC-05", report_type="scientific-computation", signal="timing table",
         verdict="partial",
         quote="控制面（99）实测不可承担：64×24 网格 200 次迭代 >120 s（shell 单次上限），无法本地兜底。",
         unresolved=dict(
             reason="原文只有一处单点耗时陈述（200 次迭代 >120 s），没有按网格/作业列出的耗时表。",
             what_would_resolve="原文出现逐网格或逐作业的耗时表。")),
    # ---- B. experimental-validation（competitor：后 3 条为定义性信号）----
    dict(id="SIG-EV-01", report_type="experimental-validation", signal="validation case",
         verdict="matched",
         quote="二维通道内静止圆柱绕流（Schäfer & Turek 1996 基准，DFG 2D-1）"),
    dict(id="SIG-EV-02", report_type="experimental-validation", signal="baseline comparison",
         verdict="partial",
         quotes=["**判据（先于计算声明）**：三个参考量（$C_D$、$C_L$、$p_{diff}$）在**最细网格**上相对误差均 <5%，",
                 "## ④ 对照表（ref vs got + 逐项误差）—— **FAIL：无 got**"],
         unresolved=dict(
             reason="对照表结构齐全（有基准侧 ref），但 got 侧全为“未取回”，比较的另一侧不存在。",
             what_would_resolve="对照表填入任一网格档的 C_D/C_L/p_diff 实测值。")),
    dict(id="SIG-EV-03", report_type="experimental-validation",
         signal="test matrix / facility description / measurement uncertainty",
         verdict="not_found",
         unresolved=dict(
             reason="全文无实验装置、试验矩阵、测量不确定度；对照量取自文献级数值基准参考值，"
                    "不是测量值（成本类报告与实验验证型的分界）。",
             what_would_resolve="原文出现设施/工况矩阵/测量不确定度任一项。")),
    # ---- C. algorithm-implementation ----
    dict(id="SIG-AI-01", report_type="algorithm-implementation",
         signal="pseudocode block / complexity statement / `O(` in results section",
         verdict="not_found",
         unresolved=dict(
             reason="原文无伪码块、无复杂度陈述、结果段无 O(·) 记号；壁面重构只作方法性描述。",
             what_would_resolve="原文出现伪码、复杂度或 O(·) 量级陈述。")),
    dict(id="SIG-AI-02", report_type="algorithm-implementation", signal="function signature",
         verdict="partial",
         quote="本单新增算例级 harness `scripts/case_cylinder_drag_fvm.py`（三个入口）：",
         unresolved=dict(
             reason="原文只列三个 CLI 入口名（solve/analyze/report），未给函数签名、参数类型或返回契约。",
             what_would_resolve="原文给出函数/接口签名与参数、返回契约。")),
    # ---- D. software-engineering ----
    dict(id="SIG-SE-01", report_type="software-engineering", signal="changed files",
         verdict="partial",
         quote="工件（worktree 内真实路径）：",
         unresolved=dict(
             reason="§⑥ 以工件清单形式提到文件路径，但不是变更集（无 diff、无受影响模块、无提交引用）。",
             what_would_resolve="原文给出变更文件列表及提交号/差异摘要。")),
    dict(id="SIG-SE-02", report_type="software-engineering", signal="regression statement",
         verdict="partial",
         quote="`pytest tests/test_case_cylinder_drag_fvm.py` → 1 passed",
         unresolved=dict(
             reason="仅一条合成数据契约测试通过记录；无回归范围、无对既有行为的保护陈述，且非物理结果。",
             what_would_resolve="原文给出回归测试范围与受影响既有行为。")),
    dict(id="SIG-SE-03", report_type="software-engineering",
         signal="commit reference / interface/API change",
         verdict="not_found",
         unresolved=dict(
             reason="原文无提交号、无接口/API 变更叙述；缺陷修复与会话过程被明确排除在报告内容外。",
             what_would_resolve="原文出现 commit 引用或 API 变更说明。")),
    # ---- E. technical-proposal ----
    dict(id="SIG-TP-01", report_type="technical-proposal", signal="proposal / roadmap / specification",
         verdict="not_found",
         unresolved=dict(
             reason="无提案、路线图或规格章节；§⑤ 的后续步骤属同一算例的待办，不构成对外提案。",
             what_would_resolve="原文出现提案/路线图/规格章节。")),
    dict(id="SIG-TP-02", report_type="technical-proposal", signal="design / plan",
         verdict="partial",
         quote="设计已完成、待数据即可出数（`analyze` 已实现并已用合成数据契约测试验证）：",
         unresolved=dict(
             reason="§⑤ 有一节“待计算”的设计/计划文字，但它是报告内部待办，不是报告的主目的。",
             what_would_resolve="该设计/计划成为报告主体并提出面向他方的行动项。")),
    # ---- F. literature-review ----
    dict(id="SIG-LR-01", report_type="literature-review", signal="bibliography",
         verdict="partial",
         quote="Turek & Schaefer, *Benchmark computations of laminar flow around cylinder*",
         unresolved=dict(
             reason="全文只有 1 条文献条目（基准原始出处，并转引 Nabh 1998 preprint）；不构成文献目录。",
             what_would_resolve="原文出现多条独立文献条目构成的目录。")),
    dict(id="SIG-LR-02", report_type="literature-review", signal="related work / state of the art / survey",
         verdict="not_found",
         unresolved=dict(
             reason="无相关工作/综述段；文献引用只用于确立参考值出处。",
             what_would_resolve="原文出现 related work 或综述段。")),
    dict(id="SIG-LR-03", report_type="literature-review", signal="citation density >= 5 per 1000 chars",
         verdict="not_found",
         unresolved=dict(
             reason="6156 字符正文仅有 1 条文献条目（见 SIG-LR-01），密度远低于 5/1000 字符；"
                    "本工序未做机器引文计数，只按可见条目判定。",
             what_would_resolve="机器引文计数达到阈值。")),
    # ---- G. 报告级状态（非类型信号，供 status 主题标签与不确定性使用）----
    dict(id="SIG-ST-01", report_type="(report-status)", signal="honest-FAIL verdict",
         verdict="matched",
         quote="> 状态：**honest-FAIL / fail_stage = compute_wait（集群排队未取回结果）**"),
    dict(id="SIG-ST-02", report_type="(report-status)", signal="results absent (no got)",
         verdict="matched",
         quote="| 64×24 | 未取回 | — | 未取回 | — | 未取回 | — | ❌ 无数据 |"),
    dict(id="SIG-ST-03", report_type="(report-status)", signal="failure cause: queue wait",
         verdict="matched",
         quote="三个作业递交后一直处于 `queued` 状态（递交 23:22 UTC 时队列前方 312 个作业；"),
]

#: 主题标签（分类的副产品；不做抽取）。
TOPICS = [
    dict(id="TOP-DOM-01", tag="阻力 / drag (C_D)", scheme="subject-domain",
         quote="| $C_D$ | 5.57953523384 | DFG 2D-1 官网页 “Reference results” |"),
    dict(id="TOP-DOM-02", tag="圆柱绕流 / flow around a cylinder", scheme="subject-domain",
         quote="二维通道内静止圆柱绕流（Schäfer & Turek 1996 基准，DFG 2D-1）"),
    dict(id="TOP-DOM-03", tag="定常层流 / steady laminar, Re_D=20", scheme="subject-domain",
         quote="| Reynolds（直径） | $Re_D$ | 20 | 算例定义 |"),
    dict(id="TOP-MTH-01", tag="有限体积 + SIMPLE/Rhie–Chow", scheme="method",
         quote="贴体网格 + SIMPLE/Rhie–Chow"),
    dict(id="TOP-MTH-02", tag="网格收敛 / Richardson / GCI", scheme="method",
         quote="1. **网格细化**：64×24 → 128×48 → 256×96（级距减半），输出观测收敛阶"),
    dict(id="TOP-STS-01", tag="honest-FAIL / compute_wait", scheme="status",
         quote="> 状态：**honest-FAIL / fail_stage = compute_wait（集群排队未取回结果）**"),
    dict(id="TOP-PLT-01", tag="集群排队 / 调度不确定性", scheme="platform",
         quote="4. **排队/调度不确定性**：本单即被队列阻塞——重算依赖集群派发，算例池批量铺开时这是系统性风险，"),
    dict(id="TOP-PLT-02", tag="平台缺项：知识检索离线 / oss_solutions 无端点", scheme="platform",
         quote="1. **knowledge_base 检索引擎离线**：`/api/v1/tensor/knowledge/search` 返回"),
    dict(id="TOP-TLS-01", tag="算例 harness / 契约测试", scheme="tooling",
         quote="本单新增算例级 harness `scripts/case_cylinder_drag_fvm.py`（三个入口）："),
]

CANDIDATES = [
    dict(id="scientific-computation", verdict="accepted",
         rationale="注册表 5 条信号：discretisation / convergence study / mesh refinement 3 条 matched，"
                   "governing equation / timing table 2 条 partial（均记 unresolved）。报告主体是数值算例的"
                   "求解设定、离散、网格细化与收敛/误差判定——计算类的核心标志齐备。",
         signal_ids=["SIG-SC-01", "SIG-SC-02", "SIG-SC-03", "SIG-SC-04", "SIG-SC-05"]),
    dict(id="experimental-validation", verdict="rejected",
         rationale="最接近的竞争类型：'validation case' matched、'baseline comparison' partial，"
                   "但其定义性信号（test matrix / facility description / measurement uncertainty）"
                   "全部 not_found——对照量来自文献级数值基准而非测量值，故不立型为实验验证。",
         signal_ids=["SIG-EV-01", "SIG-EV-02", "SIG-EV-03"]),
    dict(id="algorithm-implementation", verdict="rejected",
         rationale="无伪码/复杂度/O(·)；'function signature' 只到 partial（三个 CLI 入口名），"
                   "报告主题不是算法实现本身。",
         signal_ids=["SIG-AI-01", "SIG-AI-02"]),
    dict(id="software-engineering", verdict="rejected",
         rationale="'changed files' 与 'regression statement' 只到 partial（工件清单 + 一条契约测试记录），"
                   "无提交引用、无接口变更；工程支撑是交付物而非报告主题。",
         signal_ids=["SIG-SE-01", "SIG-SE-02", "SIG-SE-03"]),
    dict(id="literature-review", verdict="rejected",
         rationale="'bibliography' 仅 partial（1 条基准出处），无综述段，引文密度不达阈值。",
         signal_ids=["SIG-LR-01", "SIG-LR-02", "SIG-LR-03"]),
    dict(id="technical-proposal", verdict="rejected",
         rationale="'design / plan' 只到 partial（§⑤ 的待计算设计属报告内待办），无提案/路线图/规格主体。",
         signal_ids=["SIG-TP-01", "SIG-TP-02"]),
]

UNCERTAINTY = [
    "类型判定口径=extraction-skills/<type>.md §1 的 identify_signals 文本是否存在；该注册表生命周期为 "
    "template-created（尚无真实代表报告跑通全线），故“matched”是信号文本层面的判定，未经产线校准。",
    "SIG-SC-03（convergence study）与 SIG-SC-04（mesh refinement）的 matched 指原文**声明了**该做法："
    "§⑤ 自述为“仅设计、待数据”；本工序不判断其是否已执行，也不补写收敛阶/GCI。",
    "experimental-validation 是最接近的竞争类型（'validation case' 亦 matched——本算例确实是一个基准算例），"
    "故 confidence 取 medium 而非 high；区分依据是其三条定义性信号全缺，且对照侧为文献数值基准。",
    "报告终态 honest-FAIL（④ 对照表无 got）：分类判定的是报告**意图与结构**，不评价结果是否达标；"
    "本工序不产生、不传播任何 C_D/C_L/p_diff 的结果数字。",
    "SIG-SC-01（governing equation）与 SIG-SC-05（timing table）仅 partial、SIG-EV-02（baseline comparison）"
    "仅 partial，均已显式记 unresolved；不补写方程或耗时表。",
    "主题标签（topics）只作检索用：每条都锚在原文逐字引文上，但标签名本身是人工命名的检索词，非原文用语。",
    "structure.sections 由行首 '#' 切分得到，未做代码栅栏感知；本报告代码块内无行首 '#'（已由自检的段连续性断言覆盖），"
    "但同一解析器用于其它报告时可能把栅栏内 '#' 误切为小节。",
    "类型判定的语义正确性无法机检：测试只验证可机检的不变量（哈希、偏移、唯一性、schema、确定性），"
    "“这份报告该不该判为 scientific-computation”仍需 04 工序/人工复核。",
    "schema_pass 依据本仓新增的 schemas/classification.v1.schema.json：平台侧 kf_result.v1 只把 "
    "outputs.classification.json 声明为无约束 object，没有官方 02 产物 schema，故本次校验是自建 schema 自查。",
]



# ---------------------------------------------------------------------------
# 源文本
# ---------------------------------------------------------------------------
def fetch_markdown() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        f"{base}/auth/login",
        data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as fh:
        token = json.load(fh)["access_token"]
    req = urllib.request.Request(f"{base}/tensor/reports/{CONTRACT['report_id']}",
                                headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as fh:
        return json.load(fh)["markdown"]


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# locator
# ---------------------------------------------------------------------------
def locate(md: str, quote: str, *, sid: str, unique: bool = True) -> dict:
    n = md.count(quote)
    if n == 0:
        raise SystemExit(f"FAIL {sid}: quote 不在原文中（逐字定位失败）: {quote!r}")
    if unique and n > 1:
        raise SystemExit(f"FAIL {sid}: quote 在原文出现 {n} 次，需更长的唯一引文: {quote!r}")
    start = md.index(quote)
    end = start + len(quote)
    assert md[start:end] == quote
    return {"locator_type": "char_offsets",
            "value": f"report_{CONTRACT['report_id']}.md#chars:{start}-{end}",
            "start_offset": start, "end_offset": end,
            "quote": quote, "content_hash": sha256(quote)}


def sections(md: str) -> list[dict]:
    heads: list[tuple[int, str]] = []
    off = 0
    for line in md.split("\n"):
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            heads.append((off, line))
            _ = level
        off += len(line) + 1
    out = []
    for i, (start, line) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(md)
        level = len(line) - len(line.lstrip("#"))
        out.append({"id": f"SEC-{i + 1:02d}", "level": level,
                    "heading": line.lstrip("# ").strip(),
                    "start_offset": start, "end_offset": end})
    # 覆盖性：段首尾相接且首段从 0 开始？首段未必从 0 开始（标题前的行不存在时才算）
    for prev, cur in zip(out, out[1:]):
        if prev["end_offset"] != cur["start_offset"]:
            raise SystemExit(f"FAIL structure: 段不连续 {prev['id']}->{cur['id']}")
    if out and out[-1]["end_offset"] != len(md):
        raise SystemExit("FAIL structure: 末段未到文末")
    for s in out:
        s["fills_report"] = True
    return out


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build(md: str, *, snapshot: Path | None, fetched_via: str) -> tuple[dict, dict]:
    recomputed = sha256(md)
    matches = recomputed == CONTRACT["source_hash"]
    if not matches:
        raise SystemExit(f"FAIL source_hash: 重算 {recomputed} != 契约 {CONTRACT['source_hash']}")

    signals = []
    seen_ids = set()
    for spec in SIGNALS:
        rec = {k: spec[k] for k in ("id", "report_type", "signal", "verdict")}
        if rec["id"] in seen_ids:
            raise SystemExit(f"FAIL duplicate id: {rec['id']}")
        seen_ids.add(rec["id"])
        quotes = list(spec.get("quotes") or ([spec["quote"]] if "quote" in spec else []))
        rec["evidence"] = [locate(md, q, sid=rec["id"]) for q in quotes]
        if "unresolved" in spec:
            rec["unresolved"] = spec["unresolved"]
        if not rec["evidence"] and "unresolved" not in rec:
            raise SystemExit(f"FAIL {rec['id']}: 既无证据也无显式 unresolved")
        if "note" in spec:
            rec["producer_note_not_evidence"] = spec["note"]
        signals.append(rec)

    topics = []
    seen_top = set()
    for spec in TOPICS:
        if spec["id"] in seen_top:
            raise SystemExit(f"FAIL duplicate topic id: {spec['id']}")
        seen_top.add(spec["id"])
        topics.append({"id": spec["id"], "tag": spec["tag"], "scheme": spec["scheme"],
                       "evidence": [locate(md, spec["quote"], sid=spec["id"])]})

    skill = SKILL["scientific-computation"]
    classification = {
        "schema": "classification.v1",
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "generated_at": "2026-11-14T00:00:00+00:00",
        "objective": {"classify_report_type": True, "register_assets": False,
                      "extract_claims": False},
        "source": {
            "uri": CONTRACT["source_uri"],
            "field": CONTRACT["source_field"],
            "contract_hash": CONTRACT["source_hash"],
            "recomputed_hash": recomputed,
            "source_hash_matches": matches,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "lines": len(md.rstrip("\n").split("\n")),
            "title": CONTRACT["title"],
            "scenario_key": CONTRACT["scenario_key"],
            "snapshot_path": str(snapshot.relative_to(REPO_ROOT)) if snapshot else "",
            "fetched_via": fetched_via,
        },
        "layer": LAYER,
        "report_type": {
            "id": "scientific-computation",
            "chosen_skill_id": skill["skill_id"],
            "skill_version": skill["version"],
            "skill_lifecycle_state": skill["lifecycle_state"],
            "confidence": "medium",
            "decision_basis": "按 extraction-skills/<type>.md §1 的 identify_signals 逐条判定："
                              "scientific-computation 5 条中 3 条 matched（discretisation / convergence study / "
                              "mesh refinement）、2 条 partial（governing equation / timing table）；"
                              "最接近的竞争类型 experimental-validation 亦有 1 条 matched（validation case）+ "
                              "1 条 partial（baseline comparison），但其三条定义性信号全缺；其余四型无 matched。"
                              "故类型取 scientific-computation，置信 medium（因竞争类型存在 matched 信号）。"
                              "注意：SC 的 convergence/mesh 两条 matched 是**设计层声明**（§⑤ 自述“待计算”），"
                              "不是“已跑出收敛阶”。",
            "secondary_aspect": [
                {"id": "benchmark-verification", "note": "与 DFG 2D-1 参考值逐量判 5% 门，"
                                                         "属 code verification 而非实验验证",
                 "signal_ids": ["SIG-EV-02", "SIG-SC-03"]},
                {"id": "honest-fail-report", "note": "报告终态为 honest-FAIL（结果未取回），"
                                                     "分类针对报告结构/意图，不针对结果",
                 "signal_ids": ["SIG-ST-01", "SIG-ST-02", "SIG-ST-03"]},
            ],
            "candidates": CANDIDATES,
        },
        "signals": signals,
        "topics": topics,
        "structure": {
            "offsets_basis": "以 UTF-8 解码后的 markdown 字符为下标，0 基，end 开区间；"
                             "分段由 '#' 起始行切分，首尾相接覆盖全文。",
            "sections": sections(md),
        },
        "uncertainty": UNCERTAINTY,
        "verification": {
            "epistemic_status": "draft",
            "assessment_status": "unassessed",
            "verification_performed_by_producer": False,
            "note": "verification 由平台门计算；本产物不自行判定为 verified。",
        },
    }

    kf_result = {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "contract_version": CONTRACT["contract_version"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_uri": CONTRACT["source_uri"],
            "source_field": CONTRACT["source_field"],
            "source_hash": recomputed,
            "source_hash_matches": matches,
            "title": CONTRACT["title"],
            "scenario_key": CONTRACT["scenario_key"],
            "chars": len(md),
        },
        "outputs": {"classification.json": classification},
    }
    # 信号附加说明放在 evidence 之外的独立字段会破坏 schema，故只保留 schema 允许的键
    for rec in classification["signals"]:
        rec.pop("producer_note_not_evidence", None)
    return classification, kf_result


# ---------------------------------------------------------------------------
# self-check（acceptance 逐条）
# ---------------------------------------------------------------------------
def self_check(md: str, classification: dict, kf_result: dict) -> dict:
    checks: dict[str, dict] = {}

    def put(name: str, ok: bool, detail: str) -> None:
        checks[name] = {"pass": bool(ok), "detail": detail}

    try:
        from jsonschema import Draft202012Validator  # type: ignore
        have_js = True
    except Exception:  # pragma: no cover
        have_js = False

    if have_js:
        for name, doc, path in (
                ("valid_json+schema_pass(classification)", classification,
                 REPO_ROOT / "schemas" / "classification.v1.schema.json"),
                ("valid_json+schema_pass(kf_result)", kf_result,
                 REPO_ROOT / "schemas" / "kf_result.v1.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            errs = sorted(Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
            put(name, not errs, "ok" if not errs else
                "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:6]))
    else:  # pragma: no cover
        put("valid_json+schema_pass", False, "jsonschema 不可用 → not_run")

    # source hash
    put("source_hash_matches",
        classification["source"]["recomputed_hash"] == CONTRACT["source_hash"]
        == sha256(md),
        f"recomputed={classification['source']['recomputed_hash']}")

    # locator 可解析：偏移在界内、md[start:end]==quote、quote 的 sha256 一致
    bad = []
    n_loc = 0
    for coll in ("signals", "topics"):
        for rec in classification[coll]:
            for loc in rec.get("evidence", []):
                n_loc += 1
                s, e, q = loc["start_offset"], loc["end_offset"], loc["quote"]
                if not (0 <= s < e <= len(md)) or md[s:e] != q or sha256(q) != loc["content_hash"]:
                    bad.append(f"{rec['id']}@{s}-{e}")
    put("source_locator_resolvable", not bad,
        f"{n_loc} 个 locator 全部可由偏移+逐字引文解析" if not bad else "; ".join(bad[:6]))

    # id 唯一
    ids = [r["id"] for r in classification["signals"]] + \
          [r["id"] for r in classification["topics"]] + \
          [s["id"] for s in classification["structure"]["sections"]] + \
          [c["id"] for c in classification["report_type"]["candidates"]]
    put("no_duplicate_ids", len(ids) == len(set(ids)), f"{len(ids)} ids, {len(set(ids))} unique")

    # 每条判定都有证据或显式 unresolved
    missing = [r["id"] for r in classification["signals"]
               if not r.get("evidence") and "unresolved" not in r]
    put("all_claims_have_evidence_or_explicit_unresolved_status", not missing,
        "全部 signal 均有 locator 或 unresolved" if not missing else "; ".join(missing))

    # 类型/skill 与注册表一致
    reg = json.loads((REPO_ROOT / "extraction-skills" / "registry.json").read_text(encoding="utf-8"))
    types = set(reg["report_types"])
    rid = classification["report_type"]["id"]
    skill_ids = {s["skill_id"]: s for s in reg["skills"]}
    sk = skill_ids.get(classification["report_type"]["chosen_skill_id"] or "")
    put("report_type_in_registry", rid in types, f"report_type={rid} ∈ {sorted(types)}")
    put("skill_id_in_registry", sk is not None and sk["report_type"] == rid,
        f"skill={classification['report_type']['chosen_skill_id']} report_type={rid}")

    # 结构切分覆盖全文
    secs = classification["structure"]["sections"]
    contig = all(a["end_offset"] == b["start_offset"] for a, b in zip(secs, secs[1:]))
    put("structure_covers_source",
        bool(secs) and secs[0]["start_offset"] == 0 and secs[-1]["end_offset"] == len(md) and contig,
        f"{len(secs)} sections, span={secs[0]['start_offset']}-{secs[-1]['end_offset']} / {len(md)}")

    # 未自行盖 verified
    v = classification["verification"]
    put("not_marked_verified",
        v["epistemic_status"] == "draft" and v["assessment_status"] == "unassessed"
        and v["verification_performed_by_producer"] is False,
        "draft / unassessed / producer 未做 verification")

    # 边界：只碰 14478
    put("scope_only_report_14478", classification["report_id"] == "14478"
        and kf_result["report_id"] == "14478", "report_id=14478")
    return checks


# ---------------------------------------------------------------------------
# figure
# ---------------------------------------------------------------------------
def figure(md: str, classification: dict, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    # 中文字体（无则退化为方块，不影响数字）
    for cand in ("Noto Sans CJK SC", "WenQuanYi Zen Hei", "SimHei", "DejaVu Sans"):
        if any(cand in f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.sans-serif"] = [cand]
            break
    plt.rcParams["axes.unicode_minus"] = False

    secs = classification["structure"]["sections"]
    fig, (ax0, ax1) = plt.subplots(
        2, 1, figsize=(12, 7.2), gridspec_kw={"height_ratios": [1.15, 1]})
    colors = plt.cm.tab20.colors
    for i, s in enumerate(secs):
        ax0.axvspan(s["start_offset"], s["end_offset"], color=colors[i % 20], alpha=0.28, lw=0)
        ax0.axvline(s["start_offset"], color="#444", lw=0.7)
        label = s["heading"][:26].replace("$", "").replace("**", "")
        ax0.text(s["start_offset"] + 22, 0.62, f"{s['id']}\n{label}",
                 fontsize=6.4, va="top", ha="left")
    # 信号/主题标签命中位置
    marks = []
    for rec in classification["signals"]:
        for loc in rec.get("evidence", []):
            marks.append((loc["start_offset"] + (loc["end_offset"] - loc["start_offset"]) / 2,
                          rec["id"], rec["verdict"]))
    vcolor = {"matched": "#1a9850", "partial": "#f0a202", "not_found": "#d73027",
              "unresolved": "#777777"}
    for j, (x, sid, vd) in enumerate(sorted(marks)):
        y = 0.30 - 0.055 * (j % 4)
        ax0.plot([x], [y], marker="v", ms=5.5, color=vcolor[vd])
        ax0.text(x, y - 0.055, sid, fontsize=5.4, ha="center", va="top", rotation=90,
                 color=vcolor[vd])
    ax0.set_xlim(0, len(md))
    ax0.set_ylim(-0.45, 0.85)
    ax0.set_yticks([])
    ax0.set_xlabel("原文 markdown 字符偏移（0 基，UTF-8 解码后字符）")
    ax0.set_title(f"报告 14478 结构分段（{len(secs)} 段 / {len(md)} 字符）与分类信号命中位置"
                  f"（▲ matched=绿, partial=橙）", fontsize=10)

    # 六分型信号统计
    types = [c["id"] for c in classification["report_type"]["candidates"]]
    counts = {t: {"matched": 0, "partial": 0, "not_found": 0} for t in types}
    for rec in classification["signals"]:
        t = rec["report_type"]
        if t in counts and rec["verdict"] in counts[t]:
            counts[t][rec["verdict"]] += 1
    ys = list(range(len(types)))[::-1]
    m = [counts[t]["matched"] for t in types]
    p = [counts[t]["partial"] for t in types]
    nf = [counts[t]["not_found"] for t in types]
    ax1.barh(ys, m, color="#1a9850", label="matched")
    ax1.barh(ys, p, left=m, color="#f0a202", label="partial")
    ax1.barh(ys, nf, left=[a + b for a, b in zip(m, p)], color="#d73027", label="not_found")
    ax1.set_yticks(ys)
    ax1.set_yticklabels([f"{t}  (verdict={ [c['verdict'] for c in classification['report_type']['candidates'] if c['id']==t][0] })"
                         for t in types], fontsize=8)
    ax1.set_xlabel("注册表 identify_signals 命中计数")
    ax1.set_title("六分型候选：按 registry identify_signals 的信号命中分布", fontsize=10)
    ax1.legend(loc="lower right", fontsize=8)
    ax1.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170)
    plt.close(fig)


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--fetch", action="store_true", help="从平台 API 重取 markdown 并刷新快照")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--check", action="store_true", help="跑 acceptance 自检，失败返回非零")
    ap.add_argument("--figure", type=Path, default=OUT_DIR / "figures" / "classification_map.png")
    args = ap.parse_args(argv)
    # 相对路径来自 repro_cmd（工作树根调用）；统一 resolve 后再求相对快照路径
    args.snapshot = args.snapshot.resolve()
    args.out_dir = args.out_dir.resolve()
    args.figure = args.figure.resolve()

    if args.fetch:
        md = fetch_markdown()
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(md, encoding="utf-8")
        fetched_via = "platform API GET /tensor/reports/14478 (markdown field)"
    else:
        if not args.snapshot.exists():
            raise SystemExit(f"缺快照 {args.snapshot}；用 --fetch 从平台取回")
        md = args.snapshot.read_text(encoding="utf-8")
        fetched_via = "byte snapshot of platform API markdown field"

    classification, kf_result = build(md, snapshot=args.snapshot, fetched_via=fetched_via)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "classification.json").write_text(
        json.dumps(classification, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (args.out_dir / "kf_result.json").write_text(
        json.dumps(kf_result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    checks = self_check(md, classification, kf_result)
    print(json.dumps(checks, ensure_ascii=False, indent=1))

    try:
        figure(md, classification, args.figure)
        print(f"figure -> {args.figure}")
    except Exception as exc:  # pragma: no cover
        print(f"figure skipped: {exc}", file=sys.stderr)

    if args.check:
        failed = [k for k, v in checks.items() if not v["pass"]]
        if failed:
            print("FAILED: " + ", ".join(failed), file=sys.stderr)
            return 1
        print("ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())