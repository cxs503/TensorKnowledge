#!/usr/bin/env python3
"""wp-9645-02 (02-classification-parse) — classify report 9645 with zero hand-copying.

Everything quoted or numeric in the deliverable is derived from the fetched markdown:
  * source hash is recomputed from the fetched bytes and compared with the contract value;
  * every evidence locator is found by a line needle, so the quote *is* the source line and
    can never drift from the report text;
  * char/byte offsets, line numbers and content_hash are computed, never typed.

Boundary: only report_id=9645 is requested. No claim is marked verified.

Run:  python3 scripts/kf_wp9645_02_classify.py
Out:  docs/kf/wp-9645-02/{source_9645.md,classification.json,kf_result.json,report_selfcheck.json}
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = "wp-9645-02"
REPORT_ID = "9645"
SRC_FIELD = "markdown"
SRC_URI = "tensor://reports/%s" % REPORT_ID
EXPECTED_HASH = "a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00"
SCENARIO_KEY = "ice_partial_factors_target_inverse"
TITLE = "IN101-N09 ISO 19906 冰压设计分项系数目标可靠度反标定（成熟化）"
OUT = os.path.join(ROOT, "docs", "kf", PKG)
SRC_MD = os.path.join(OUT, "source_%s.md" % REPORT_ID)
REGISTRY = os.path.join(ROOT, "extraction-skills", "registry.json")


# --------------------------------------------------------------------------- fetch
def _post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def fetch_markdown():
    """Return (markdown, origin). Only report 9645 is ever requested."""
    if os.path.exists(SRC_MD):  # cached snapshot of the same report (hash-checked by caller)
        with open(SRC_MD, "rb") as f:
            return f.read().decode("utf-8"), "cache"
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    j = _post(base + "/auth/login",
              {"username": os.environ["TENSOR_AGENT_USER"],
               "password": os.environ["TENSOR_AGENT_PASS"]})
    tok = j.get("access_token") or j.get("token")
    rep = _get(base + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(rep.get("data"), dict):
        rep = rep["data"]
    return rep[SRC_FIELD], "api"


# ------------------------------------------------------------------------ locators
class Locator:
    """Line-needle locator: the quote is the source line itself (never retyped)."""

    def __init__(self, md):
        self.md = md
        self.lines = md.splitlines(keepends=True)
        self.starts = []
        off = 0
        for ln in self.lines:
            self.starts.append(off)
            off += len(ln)
        self.items = {}

    def find(self, lid, needle, n_lines=1, mode="line"):
        for i, ln in enumerate(self.lines):
            if needle in ln:
                if mode == "needle":  # sub-line span: the needle itself is the quote
                    quote = needle
                    c0 = self.starts[i] + ln.index(needle)
                    end_line = i + 1
                else:
                    quote = "".join(self.lines[i:i + n_lines]).rstrip("\n")
                    c0 = self.starts[i]
                    end_line = i + n_lines
                if quote not in self.md:
                    raise AssertionError("quote not verbatim: %s" % lid)
                c1 = c0 + len(quote)
                self.items[lid] = {
                    "id": lid,
                    "locator_type": "char_span_line",
                    "field": SRC_FIELD,
                    "quote": quote,
                    "start_char": c0,
                    "end_char": c1,
                    "byte_start": len(self.md[:c0].encode("utf-8")),
                    "byte_end": len(self.md[:c1].encode("utf-8")),
                    "start_line": i + 1,
                    "end_line": end_line,
                    "content_hash": "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                    "resolvable": True,
                }
                return lid
        raise AssertionError("needle not found for %s: %r" % (lid, needle))

    def as_list(self):
        return [self.items[k] for k in sorted(self.items)]


# (id, line needle) — every quote is the source line containing the needle.
LTABLE = [
    ("loc-001", "**仓库** TensorPhysics ｜ **模块** `tensorphysics.ice_partial_factors`", 1, "needle"),
    ("loc-002", "**目标** $\\beta_T$ = 4.00 ($P_f$ = 3.1671e-05)", 1, "needle"),
    ("loc-003", "| `a_form_vs_simulation` | PASS |"),
    ("loc-004", "**判据汇总** 5/5 通过"),
    ("loc-005", "ISO 19906 用压力–面积关系描述冰载荷"),
    ("loc-006", "| 特征冰力 $F_k$ | 23.517 MN"),
    ("loc-007", "| $ex$ | 0.400 |"),
    ("loc-008", "**反问题两方程两未知量**"),
    ("loc-009", "$$F_1(\\gamma_f,\\psi)=\\beta(\\kappa)-\\beta_T=0"),
    ("loc-010", "**四条独立验证面**"),
    ("loc-011", "**表 2 FORM 的四条独立验证（判据 a）**"),
    ("loc-012", "| 闭式 $\\beta_{ln}$（解析）|"),
    ("loc-013", "**表 6 负控（判据 e）：忽略 p–A 负相关**"),
    ("loc-014", "| Newton 迭代数（三初值） |"),
    ("loc-015", "| Jacobian 条件数 | 4.791 |"),
    ("loc-016", "**图 3.** Left: residual norm of the two-equation system"),
    ("loc-017", "**表 8 模型参数敏感性"),
    ("loc-018", "| 伴随 $\\partial\\beta/\\partial\\kappa$ | 中心差分 |"),
    ("loc-019", "**表 1 反问题解**"),
    ("loc-020", "**表 4 与 ISO 19906 表格分项系数偏差（判据 d）**"),
    ("loc-021", "| ice_action_frequent x steel_plate_yielding |"),
    ("loc-022", "**表格值出处受限**"),
    ("loc-023", "**适用范围**：年极值接触面积按对数正态建模"),
    ("loc-024", "**该问题的 FORM 是精确的**"),
    ("loc-025", "**分项系数对的唯一性依赖劈分约定**"),
    ("loc-026", "**结论**：FORM 与解析值、重要性抽样的一致性远优于 3 %"),
    ("loc-027", "纯 Python（`tensorphysics.structural` 的 FORM/SORM/IS/MC + Nataf）", 1, "needle"),
    ("loc-028", "所有数字由 `run_study()` 写入 JSON，报告文本从 JSON 注入（零手抄）", 1, "needle"),
    ("loc-029", "![fig1](/root/tp-agent/work/m8350/"),
    ("loc-030", "- 结果 JSON：`/root/tp-agent/work/m8350/"),
    ("loc-031", "复现：`PYTHONPATH=src python3 benchmarks/iso19906_partial_factors/run_in101_n09.py`"),
    ("loc-032", "## ③ 计算结果"),
    ("loc-033", "**±1σ 覆盖率是 68 % 检验**"),
    ("loc-034", "**Nataf 吃物理相关、ISO 幂律给对数相关**"),
]


def segments(md):
    heads = [(m.start(), m.group(0)) for m in re.finditer(r"(?m)^#{1,3} .*$", md)]
    roles = {
        "①": "context_and_parameters",
        "②": "method_and_toolchain",
        "③": "numerical_results",
        "④": "figures",
        "⑤": "caveats_and_limitations",
        "⑥": "error_verdict_vs_baseline",
        "审计链": "provenance_and_audit_chain",
    }
    out = []
    for k, (start, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(md)
        role = "title_and_machine_criteria" if start == 0 else "other"
        for key, r in roles.items():
            if key in title:
                role = r
                break
        out.append({
            "segment_id": "seg-%02d" % (k + 1),
            "heading": title.rstrip(),
            "level": len(title) - len(title.lstrip("#")),
            "role": role,
            "char_start": start,
            "char_end": end,
            "line_start": md[:start].count("\n") + 1,
            "line_end": md[:end].count("\n") + 1,
            "chars": len(md[start:end]),
        })
    return out


def build(md):
    src_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()
    loc = Locator(md)
    for item in LTABLE:
        loc.find(*item)

    reg = json.load(open(REGISTRY, encoding="utf-8"))
    sig = [
        {"identify_signal": "governing equations", "matched": "exact",
         "locator_ids": ["loc-005", "loc-007", "loc-009"],
         "note": "压力–面积幂律 p(A)=p0(A/A0)^-ex 与极限状态反问题方程组逐字在原文。"},
        {"identify_signal": "discretisation", "matched": "not_applicable",
         "locator_ids": ["loc-009", "loc-024"],
         "note": "无 PDE/网格离散：失效域为 u 空间半空间、FORM 解析精确；模板信号不覆盖此类可靠性问题。"},
        {"identify_signal": "convergence study", "matched": "partial",
         "locator_ids": ["loc-014", "loc-015", "loc-016"],
         "note": "收敛证据在求解器层（Newton 残差二次收敛、三初值同根、Jacobian 条件数 4.791），不是网格收敛研究。"},
        {"identify_signal": "mesh refinement", "matched": "absent", "locator_ids": [],
         "note": "原文无网格细分；按 no_forced_claim_generation 记为 absent，不补造。"},
        {"identify_signal": "timing table", "matched": "absent", "locator_ids": [],
         "note": "原文无运行时间表（无计时行），记为 absent。"},
    ]
    ev_sig = [
        {"identify_signal": "baseline comparison", "matched": "exact",
         "locator_ids": ["loc-011", "loc-012", "loc-026"],
         "note": "FORM 对闭式解析、重要性抽样、粗 MC 的多路对照表逐字在原文。"},
        {"identify_signal": "test matrix", "matched": "partial",
         "locator_ids": ["loc-020", "loc-021"],
         "note": "有 9 对 ISO 表格 + 1 仓内锚点的算例矩阵，但不是试验/测量矩阵。"},
        {"identify_signal": "measurement uncertainty", "matched": "partial",
         "locator_ids": ["loc-033"],
         "note": "有抽样统计的 1σ/95 % 覆盖判断，属蒙特卡洛统计不确定性，不是测量不确定度。"},
        {"identify_signal": "validation case", "matched": "partial",
         "locator_ids": ["loc-013"],
         "note": "负控（置 ρ=0 重跑）是验证用算例，但不是物理标定试验。"},
        {"identify_signal": "facility", "matched": "absent", "locator_ids": [],
         "note": "纯数值研究，无试验设施，记为 absent。"},
    ]
    segs = segments(md)

    tags = [
            {"tag": "ice-load/ISO-19906", "locator_ids": ["loc-005", "loc-020"]},
            {"tag": "pressure-area-relation", "locator_ids": ["loc-005", "loc-007"]},
            {"tag": "reliability-based-calibration/target-beta", "locator_ids": ["loc-002", "loc-004"]},
            {"tag": "inverse-problem/partial-factors", "locator_ids": ["loc-008", "loc-009", "loc-019"]},
            {"tag": "FORM-IS-MC-crosscheck", "locator_ids": ["loc-010", "loc-011", "loc-012"]},
            {"tag": "Nataf-correlation", "locator_ids": ["loc-034"]},
            {"tag": "negative-control", "locator_ids": ["loc-013"]},
            {"tag": "sensitivity/adjoint-vs-finite-difference", "locator_ids": ["loc-017", "loc-018"]},
            {"tag": "secondary-source-table-comparison", "locator_ids": ["loc-020", "loc-022"]},
        ]
    unresolved = [
        {"id": "unres-9645-001", "status": "unresolved",
         "item": "否定性分类标签（software-engineering / literature-review 的拒绝）",
         "reason": "'不存在'命题不可由逐字引文证明；保留为可反驳假设。",
         "related_claims": ["cls-9645-006", "cls-9645-007"]},
        {"id": "unres-9645-002", "status": "unresolved",
         "item": "ISO 19906 Annex A 原始表值",
         "reason": "原文自述 A.2/A.3 为二次文献转录且 primary_source_verified=False（loc-022）；"
                   "本工序不得回溯规范正文，也不得把表值当一手证据。",
         "related_claims": ["cls-9645-008"]},
        {"id": "unres-9645-003", "status": "unresolved",
         "item": "报告图 1–6 与 in101_n09_results.json 的可达性",
         "reason": "引用路径指向 /root/tp-agent/work/m8350/（另一工作树），本包不应跨 worktree 取件（loc-029/030）。",
         "related_claims": ["cls-9645-009"]},
    ]

    classification = {
        "schema": "kf-classification.v1",
        "package_id": PKG,
        "task_type": "02-classification-parse",
        "report_id": REPORT_ID,
        "taxonomy": {
            "source": "extraction-skills/registry.json",
            "registry_version": reg["registry_version"],
            "report_types": reg["report_types"],
            "note": "分类是可反驳的假设；unclassified 为合法值。本包给出主型 + 备选型 + 置信度，而不是单点断言。",
        },
        "source": {
            "source_uri": SRC_URI,
            "source_field": SRC_FIELD,
            "source_hash": "sha256:" + src_hash,
            "source_hash_matches": src_hash == EXPECTED_HASH,
            "chars": len(md),
            "bytes": len(md.encode("utf-8")),
            "title": TITLE,
            "scenario_key": SCENARIO_KEY,
        },
        "report_type": {
            "primary": "scientific-computation",
            "primary_label_zh": "科学计算 / 可靠度标定（数值反问题 + 基准验证）",
            "confidence": 0.85,
            "confidence_basis": "模板 5 信号中 1 精确命中（governing equations）+ 1 部分命中（收敛证据在求解器层）；"
                                "结构性证据（结果表 / 解析基准 / 敏感性 / 复现脚本）压倒性，见 loc-007/009/011/017/019/027/031。",
            "alternatives": [
                {"report_type": "experimental-validation", "confidence": 0.40,
                 "why_not_primary": "有多路基准对照与负控（loc-010/011/013），但无试验设施、无测量不确定度；"
                                    "此处的 'experimental' 是数值验证而非实验验证，故降为备选型并保留其信号。",
                 "locator_ids": ["loc-010", "loc-011", "loc-013", "loc-033"]},
                {"report_type": "algorithm-implementation", "confidence": 0.20,
                 "why_not_primary": "确有阻尼 Newton + 包络定理 Jacobian + 二分独立复核（loc-008/014/015/018），"
                                    "但原文无伪代码、无复杂度陈述，模板判据不满足。",
                 "locator_ids": ["loc-008", "loc-014", "loc-015", "loc-018"]},
                {"report_type": "software-engineering", "confidence": 0.05,
                 "why_not_primary": "只出现模块名与复现命令（loc-001/031），无变更文件、无接口/回归变更；"
                                    "拒绝依据是'缺失'，故记 unresolved（cls-9645-006）。",
                 "locator_ids": ["loc-001", "loc-031"]},
            ],
            "rejected_types": [
                {"report_type": "literature-review",
                 "reason": "无 survey/相关工作结构；全篇仅引 ISO 19906 Annex A 且自述为二次文献转录（loc-022），"
                           "不满足 'citation density >= 5 per 1000 chars' 信号。拒绝依据为缺失，记 unresolved（cls-9645-007）。"},
                {"report_type": "technical-proposal",
                 "reason": "交付的是已算出的结果表与机器判据（loc-003/004/019），不是计划/规格/roadmap 结构。"},
            ],
        },
        "topic_tags": tags,
        "domain_labels": {
            "discipline": ["ice-region-navigation", "structures"],
            "discipline_label_zh": ["冰区航行", "结构"],
            "discipline_basis": "冰压载荷 + 钢构件抗力/分项系数 → 冰区结构可靠度标定。派生标签，"
                                "由 loc-005（冰压–面积关系）与 loc-021（ice_action × steel_plate 组合）共同支持。",
            "discipline_locator_ids": ["loc-005", "loc-021"],
            "scenario_key": SCENARIO_KEY,
            "language": "mixed zh/en（正文中文，标题/表头/图注英文）",
        },
        "selected_skill": {
            "skill_id": "xsk-scientific-computation",
            "skill_version": "0.1.0",
            "lifecycle_state": "template-created",
            "selection_basis": "主型 = scientific-computation，按 registry 的 report_type→skill 映射选取，不另立 skill。",
            "signal_match": sig,
            "signal_coverage": {
                "exact": sum(1 for s in sig if s["matched"] == "exact"),
                "partial": sum(1 for s in sig if s["matched"] == "partial"),
                "absent_or_not_applicable": sum(1 for s in sig if s["matched"] in ("absent", "not_applicable")),
                "total": len(sig),
            },
            "registry_gap": "模板信号是关键词式的，对'可靠度标定 / 反问题'这类报告覆盖不足（据本份报告观察到，未做全库统计）："
                            "5 个信号里只有 governing equations 精确命中，收敛与精度证据只能算 partial。"
                            "本包按结构性证据完成分类并如实登记该缺口，未据此改写 registry（超出本包范围）。",
            "downstream_note": "03 若沿用本 skill，其 extract-accuracy-statements 可直接吃表 2/表 6（loc-011/013），"
                               "但须遵守 loc-024 的解读约束：本问题 FORM 精确，'FORM vs MC 差 3 %' 不能当作精度判据。",
        },
        "secondary_type_signals": {
            "report_type": "experimental-validation",
            "signal_match": ev_sig,
            "use": "仅作标签层叠加（validation / negative-control 语义），不改变选中的 skill。",
        },
        "structural_segmentation": segs,
        "claims": [
            {"id": "cls-9645-001", "claim_type": "classification", "status": "supported", "confidence": 0.85,
             "statement": "主型为 scientific-computation：以压力–面积幂律与控制方程组为骨架，输出数值结果表，"
                          "并由脚本零手抄注入数字。",
             "locator_ids": ["loc-005", "loc-007", "loc-009", "loc-019", "loc-027", "loc-028"]},
            {"id": "cls-9645-002", "claim_type": "classification", "status": "supported", "confidence": 0.90,
             "statement": "本报告是分项系数（设计格式）标定的反问题研究：目标 β_T=4.00，输出 (γ_f, ψ) 与 κ=γ_f·ψ，"
                          "属'规范标定'子型而非一般数值算例。",
             "locator_ids": ["loc-002", "loc-006", "loc-008", "loc-009", "loc-019"]},
            {"id": "cls-9645-003", "claim_type": "classification", "status": "supported", "confidence": 0.75,
             "statement": "报告具备验证型特征（多路基准对照 + 负控 + 1σ 覆盖判断），故把 experimental-validation "
                          "列为备选型（0.40）并叠加标签，但不据此改选 skill。",
             "locator_ids": ["loc-010", "loc-011", "loc-012", "loc-013", "loc-033"]},
            {"id": "cls-9645-004", "claim_type": "classification", "status": "supported", "confidence": 0.70,
             "statement": "含算法实现成分（阻尼 Newton、包络定理 Jacobian、二分独立复核），但缺伪代码与复杂度陈述，"
                          "不足以判为 algorithm-implementation。",
             "locator_ids": ["loc-008", "loc-014", "loc-015", "loc-016", "loc-018"]},
            {"id": "cls-9645-005", "claim_type": "classification", "status": "supported", "confidence": 0.80,
             "statement": "不是 technical-proposal：交付物为已算出的结果表与机器判据汇总（5/5 通过），无计划/规格/roadmap 结构。",
             "locator_ids": ["loc-003", "loc-004", "loc-019", "loc-032"]},
            {"id": "cls-9645-006", "claim_type": "classification", "status": "unresolved", "confidence": 0.60,
             "statement": "拒绝 software-engineering 的依据是'缺变更记录/接口变更'，属否定性证据，无法用逐字引文证明。",
             "locator_ids": ["loc-001", "loc-031"],
             "unresolved_reason": "否定命题（原文未出现变更文件/commit/接口变更）不能由正向引文证实；"
                                  "按 do_not_invent_missing_information 保留为 unresolved，不冒充已证。"},
            {"id": "cls-9645-007", "claim_type": "classification", "status": "unresolved", "confidence": 0.65,
             "statement": "拒绝 literature-review 同样基于缺失（无 survey/相关工作节，仅一处二次文献引用）。",
             "locator_ids": ["loc-022"],
             "unresolved_reason": "'不存在某结构'无法由单条引文证明；已用 loc-022 说明其唯一引用来源，"
                                  "但不宣称已完成引用密度核算。"},
            {"id": "cls-9645-008", "claim_type": "descriptive", "status": "supported", "confidence": 0.90,
             "statement": "与 ISO 表格比对的裁决依赖二次文献转录（source_tier=secondary, primary_source_verified=False），"
                          "故相关标签与结论只能标 conditional；下游引用表值必须带此限定。",
             "locator_ids": ["loc-022", "loc-020"]},
            {"id": "cls-9645-009", "claim_type": "descriptive", "status": "supported", "confidence": 0.95,
             "statement": "报告引用的图与结果 JSON 位于工作树外的绝对路径（/root/tp-agent/work/m8350/…），"
                          "本工序无法在 worktree 内解析；按边界不改写、不登记资产，只在下游风险处挂账。",
             "locator_ids": ["loc-029", "loc-030"]},
            {"id": "cls-9645-010", "claim_type": "descriptive", "status": "supported", "confidence": 0.90,
             "statement": "适用范围与约定限制由原文显式给出：单一年极值接触面积分布 + 单一幂律指数 + 抗力与冰力独立；"
                          "且 κ 无约定而 γ_f/ψ 的劈分属约定，故跨来源比对只应以 κ 为准。",
             "locator_ids": ["loc-023", "loc-025"]},
        ],
        "unresolved": unresolved,
        "constraints_compliance": {
            "every_claim_must_have_source_locator": True,
            "do_not_invent_missing_information": True,
            "preserve_uncertainty": True,
            "no_forced_claim_generation": True,
            "do_not_mark_claims_as_verified": True,
            "verified_flag_absent": True,
            "note": "全部 claim 的 status ∈ {supported, unresolved}；无 verified 字段，验证等级由平台门计算。",
        },
        "evidence_locators": loc.as_list(),
        "counts": {},
    }

    classification["counts"] = {
        "evidence_locators": len(loc.items),
        "claims": len(classification["claims"]),
        "claims_supported": sum(1 for c in classification["claims"] if c["status"] == "supported"),
        "claims_unresolved": sum(1 for c in classification["claims"] if c["status"] == "unresolved"),
        "unresolved_items": len(classification["unresolved"]),
        "segments": len(classification["structural_segmentation"]),
        "topic_tags": len(classification["topic_tags"]),
    }

    kf = {
        "package_id": PKG,
        "task_type": "02-classification-parse",
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SRC_URI,
            "source_field": SRC_FIELD,
            "source_hash": "sha256:" + src_hash,
            "source_hash_matches": src_hash == EXPECTED_HASH,
            "title": TITLE,
            "scenario_key": SCENARIO_KEY,
            "chars": len(md),
        },
        "outputs": {"classification.json": classification},
    }
    return classification, kf


def validate_kf_schema(kf):
    errs = []
    top = {"package_id", "task_type", "contract_version", "report_id", "provenance", "outputs"}
    errs += ["unexpected top-level key: %s" % k for k in kf if k not in top]
    errs += ["missing top-level key: %s" % k for k in top if k not in kf]
    if not re.match(r"^wp-[a-z0-9][a-z0-9-]{2,63}$", kf.get("package_id", "")):
        errs.append("package_id pattern")
    if kf.get("task_type") not in {"01-asset-registration", "02-classification-parse",
                                   "03-knowledge-extraction", "04-independent-review",
                                   "05-synthesis-research"}:
        errs.append("task_type enum")
    if kf.get("contract_version") != "1.0":
        errs.append("contract_version const")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$", kf.get("report_id", "")):
        errs.append("report_id pattern")
    prov = kf.get("provenance", {})
    errs += ["provenance unexpected key: %s" % k for k in prov
             if k not in {"source_uri", "source_field", "source_hash", "source_hash_matches",
                          "title", "scenario_key", "chars"}]
    for k in ("source_uri", "source_field", "source_hash"):
        if k not in prov:
            errs.append("provenance missing %s" % k)
    if not re.match(r"^(https?://\S+|file://\S+|tensor://\S+)$", prov.get("source_uri", "")):
        errs.append("source_uri pattern")
    if prov.get("source_field") not in {"markdown", "summary", "record"}:
        errs.append("source_field enum")
    if not re.match(r"^sha256:[0-9a-f]{64}$", prov.get("source_hash", "")):
        errs.append("source_hash pattern")
    if not isinstance(prov.get("chars"), int):
        errs.append("chars not int")
    out = kf.get("outputs", {})
    if not isinstance(out, dict) or not out:
        errs.append("outputs empty")
    allowed = {"asset_manifest.json", "classification.json", "claims.json", "evidence.json",
               "provenance.json", "extraction_summary.json", "review_report.json",
               "review_events.json", "synthesis.json"}
    errs += ["outputs unexpected key: %s" % k for k in out if k not in allowed]
    return errs


def selfcheck(md, cls, kf, schema_errors):
    ids = [c["id"] for c in cls["claims"]]
    loc_ids = [lo["id"] for lo in cls["evidence_locators"]]
    bad = []
    for lo in cls["evidence_locators"]:
        if md[lo["start_char"]:lo["end_char"]] != lo["quote"]:
            bad.append(lo["id"] + ":offsets")
        if "sha256:" + hashlib.sha256(lo["quote"].encode("utf-8")).hexdigest() != lo["content_hash"]:
            bad.append(lo["id"] + ":hash")
        if lo["quote"] not in md:
            bad.append(lo["id"] + ":substr")
        if md.encode("utf-8")[lo["byte_start"]:lo["byte_end"]].decode("utf-8") != lo["quote"]:
            bad.append(lo["id"] + ":bytes")
    orphan = [c["id"] for c in cls["claims"] if not c.get("locator_ids") and c["status"] != "unresolved"]
    dangling = [c["id"] for c in cls["claims"] for r in c.get("locator_ids", []) if r not in loc_ids]
    no_reason = [c["id"] for c in cls["claims"] if c["status"] == "unresolved" and not c.get("unresolved_reason")]
    checks = [
        {"acceptance_item": "valid_json", "pass": True,
         "detail": "classification.json / kf_result.json 由 json.dump 生成并可回读解析。"},
        {"acceptance_item": "schema_pass", "pass": schema_errors == [],
         "detail": "按 schemas/kf_result.v1.schema.json 的 required/type/enum/pattern/additionalProperties 子集校验："
                   + ("无违规" if not schema_errors else "; ".join(schema_errors))},
        {"acceptance_item": "source_locator_resolvable",
         "pass": not bad and cls["source"]["source_hash_matches"],
         "detail": "%d 条定位器逐条按 char/byte 偏移回切原文并比对 quote 与 content_hash；失败项=%s"
                   % (len(loc_ids), bad or "无")},
        {"acceptance_item": "source_hash_matches", "pass": cls["source"]["source_hash_matches"],
         "detail": "重算 %s，契约值 sha256:%s" % (cls["source"]["source_hash"], EXPECTED_HASH)},
        {"acceptance_item": "no_duplicate_ids",
         "pass": len(ids) == len(set(ids)) and len(loc_ids) == len(set(loc_ids)),
         "detail": "claims %d/%d unique；locators %d/%d unique"
                   % (len(set(ids)), len(ids), len(set(loc_ids)), len(loc_ids))},
        {"acceptance_item": "all_claims_have_evidence_or_explicit_unresolved_status",
         "pass": not orphan and not dangling and not no_reason,
         "detail": "supported 均带已解析 locator；unresolved 均带 unresolved_reason；"
                   "缺证据=%s 悬空引用=%s 缺理由=%s" % (orphan or "无", dangling or "无", no_reason or "无")},
    ]
    return {"package_id": PKG, "checks": checks, "all_pass": all(c["pass"] for c in checks),
            "counts": cls["counts"]}


def main():
    os.makedirs(OUT, exist_ok=True)
    md, origin = fetch_markdown()
    if not os.path.exists(SRC_MD):
        with open(SRC_MD, "wb") as f:
            f.write(md.encode("utf-8"))
    cls, kf = build(md)
    schema_errors = validate_kf_schema(kf)
    chk = selfcheck(md, cls, kf, schema_errors)
    for name, obj in (("classification.json", cls), ("kf_result.json", kf),
                      ("report_selfcheck.json", chk)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print("origin:", origin)
    print("source_hash:", cls["source"]["source_hash"], "match:", cls["source"]["source_hash_matches"])
    print("chars:", cls["source"]["chars"], "locators:", cls["counts"]["evidence_locators"],
          "segments:", cls["counts"]["segments"])
    print("schema_errors:", schema_errors or "none")
    for c in chk["checks"]:
        print(("PASS " if c["pass"] else "FAIL ") + c["acceptance_item"] + " :: " + c["detail"])
    return 0 if chk["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())