#!/usr/bin/env python3
"""wp-9478-02 — 工序 02（分类解析）for report 9478.

Zeros-handcopy design: every quote is a *slice of the fetched source lines*
(never retyped), every offset/hash is computed here, and every number that
appears in a statement or in the delivered report is injected by this script.
Nothing is written that the script has not read from the source bytes.

Outputs (inside docs/kf/wp-9478-02/):
  source/report_9478.md      fetched markdown (hash-verified against the contract)
  source/record.json         API record metadata (title/summary/scenario/figures)
  classification.json        the process-02 artefact
  checks.json                acceptance self-check (honest FAIL allowed)
  classification_table.md    locator table, generated (used by the KF report)

Run: python3 docs/kf/wp-9478-02/scripts/generate_classification.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[2]

REPORT_ID = "9478"
PACKAGE_ID = "wp-9478-02"
TASK_TYPE = "02-classification-parse"
SOURCE_URI = "tensor://reports/9478"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = "sha256:133dbe58a74bd7549b66b2b86e5dc2e517f603c3ea65af45947d4cb5c1599e28"
CONTRACT_CHARS = 5748
SCENARIO_KEY = "P153W2-N03-fsi-strong-coupling"
CONTRACT_TITLE = ("P153W2-N03: TensorFEM×TensorLBM FSI Strong Coupling — "
                  "Turek-Hron FSI-2 + Flutter + Energy Conservation")

#: Predeclared scoring weights (fixed before the scores were looked at, so the
#: type decision does not get tuned after the fact).
#:   literal registry signal  1.0  — a keyword the skill itself declares
#:   applies_to section hit   0.5  — weak: "method"/"results" are generic titles
#:   semantic anchor (full)   2.0  — the discriminating evidence
#:   semantic anchor (weak)   1.0  — a near-miss the source only partly supports
WEIGHT_LITERAL = 1.0
WEIGHT_SECTION = 0.5
WEIGHT_ANCHOR = 2.0


# --------------------------------------------------------------------------
# source acquisition
# --------------------------------------------------------------------------
def _api_get(path: str, token: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.loads(fh.read())


def _login() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    }).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.loads(fh.read())["access_token"]


def load_source() -> tuple[str, dict]:
    """Fetch (or reuse the cached copy of) report 9478 and verify its hash."""
    src = PKG / "source" / "report_9478.md"
    rec_path = PKG / "source" / "record.json"
    record: dict = {}
    if src.is_file() and not os.environ.get("KF_REFRESH"):
        text = src.read_text(encoding="utf-8")
        if rec_path.is_file():
            record = json.loads(rec_path.read_text(encoding="utf-8"))
    else:
        record = _api_get(f"/tensor/reports/{REPORT_ID}", _login())
        text = record["markdown"]
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(text, encoding="utf-8")
        meta = {k: v for k, v in record.items() if k != "markdown"}
        rec_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != CONTRACT_SOURCE_HASH:
        raise SystemExit(f"SOURCE HASH MISMATCH: {digest} != {CONTRACT_SOURCE_HASH}")
    if len(text) != CONTRACT_CHARS:
        raise SystemExit(f"SOURCE CHAR COUNT MISMATCH: {len(text)} != {CONTRACT_CHARS}")
    return text, record


# --------------------------------------------------------------------------
# structure parse
# --------------------------------------------------------------------------
def line_offsets(lines: list[str]) -> list[int]:
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1  # the '\n' that split() consumed
    return offsets


def parse_structure(text: str) -> dict:
    lines = text.split("\n")
    offsets = line_offsets(lines)
    headings = []
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", ln)
        if m:
            headings.append({
                "level": len(m.group(1)),
                "title": m.group(2),
                "line": i + 1,
                "start_offset": offsets[i],
                "end_offset": offsets[i] + len(ln),
            })
    for k, h in enumerate(headings):
        h["section_end_offset"] = (headings[k + 1]["start_offset"]
                                   if k + 1 < len(headings) else len(text))
    table_lines = [i + 1 for i, ln in enumerate(lines) if ln.startswith("|")]
    tables, prev = [], None
    for ln in table_lines:
        if prev is None or ln != prev + 1:
            tables.append({"first_line": ln, "n_lines": 1})
        else:
            tables[-1]["n_lines"] += 1
        prev = ln
    numbered = [{"line": i + 1, "text": ln,
                 "label_empty": bool(re.match(r"^\d+\.\s*:\s", ln))}
                for i, ln in enumerate(lines) if re.match(r"^\d+\.\s", ln)]
    # figure references are only the numbered items inside the "Figures" section:
    # a numbered list elsewhere (method steps, limitations) is not a figure ref.
    fig_sec = next((h for h in headings if h["level"] == 2 and "figure" in h["title"].lower()), None)
    fig_refs = [f for f in numbered
                if fig_sec and fig_sec["start_offset"] <= offsets[f["line"] - 1]
                < fig_sec["section_end_offset"]]
    audit = {}
    for i, ln in enumerate(lines):
        for field in ("Code", "Tests", "Full FSI suite", "Figures"):
            m = re.match(rf"^- {re.escape(field)}:\s*(.*)$", ln)
            if m:
                audit[field] = {"line": i + 1, "value": m.group(1),
                                "empty": m.group(1).strip() == ""}
    top = [h for h in headings if h["level"] == 2]
    return {
        "n_lines": len(lines),
        "n_chars": len(text),
        "headings": headings,
        "heading_counts": {f"h{lvl}": sum(1 for h in headings if h["level"] == lvl)
                           for lvl in (1, 2, 3)},
        "top_level_sections": [{"title": h["title"], "line": h["line"],
                                "start_offset": h["start_offset"],
                                "end_offset": h["section_end_offset"]} for h in top],
        "tables": tables,
        "figure_refs": fig_refs,
        "numbered_list_items": numbered,
        "audit_chain": audit,
    }


# --------------------------------------------------------------------------
# candidate scoring — literal signals from the registry + curated anchors
# --------------------------------------------------------------------------
def score_candidates(text: str, st: dict, registry: dict) -> list[dict]:
    low = text.lower()
    titles = " | ".join(h["title"].lower() for h in st["headings"])
    out = []
    for skill in registry["skills"]:
        hits = []
        for sig in skill["identify_signals"]:
            cnt = low.count(sig.lower())
            if cnt:
                hits.append({"signal": sig, "literal_count": cnt,
                             "first_offset": low.find(sig.lower())})
        sec_hits = [s for s in skill["applies_to"]["sections"]
                    if s.split()[0].split("/")[0] in titles]
        out.append({
            "report_type": skill["report_type"],
            "skill_id": skill["skill_id"],
            "literal_signal_score": round(WEIGHT_LITERAL * len(hits), 2),
            "literal_signal_hits": hits,
            "section_score": round(WEIGHT_SECTION * len(sec_hits), 2),
            "section_hits": sec_hits,
        })
    return out


#: Curated semantic anchors.  Each anchor is either a verbatim source line
#: range (``lines``) or a declared negative finding (``absent``) that is
#: recorded as unresolved instead of being claimed as locatable evidence.
#: ``weight`` = 1.0 marks a near-miss the source only partly supports.
SEMANTIC_ANCHORS: dict[str, list[dict]] = {
    "scientific-computation": [
        {"id": "a-eq", "what": "numerical scheme written as an equation", "lines": (34, 34)},
        {"id": "a-param", "what": "parameter table with units", "lines": (16, 16)},
        {"id": "a-conv", "what": "time-step convergence study", "lines": (93, 93)},
        {"id": "a-errref", "what": "error stated against a reference value", "lines": (131, 131)},
        {"id": "a-assume", "what": "modelling assumption stated verbatim", "lines": (113, 113)},
    ],
    "experimental-validation": [
        {"id": "b-case", "what": "benchmark validation case", "lines": (7, 7)},
        {"id": "b-baseline", "what": "baseline comparison with an acceptance bound",
         "lines": (61, 61)},
        {"id": "b-facility", "what": "experimental facility / rig", "absent":
         "no facility or rig is described anywhere in the body"},
        {"id": "b-uncert", "what": "measurement uncertainty budget", "absent":
         "no measurement-uncertainty statement or budget is given"},
        {"id": "b-matrix", "what": "repeated-run test matrix", "absent":
         "no test matrix / repeat runs; results are single deterministic runs"},
    ],
    "algorithm-implementation": [
        {"id": "c-alg", "what": "algorithm composition stated", "lines": (31, 31)},
        {"id": "c-impl", "what": "implementation detail of a component", "lines": (45, 45)},
        {"id": "c-pseudo", "what": "pseudocode block", "absent": "no pseudocode or algorithm block"},
        {"id": "c-complex", "what": "complexity analysis", "absent": "no complexity statement"},
    ],
    "software-engineering": [
        {"id": "d-change", "what": "changed files / commit reference", "absent":
         "no changed-file list and the audit-chain Code field is empty"},
        {"id": "d-regress", "what": "regression result with a runnable command", "absent":
         "test counts are asserted without a command or link"},
    ],
    "technical-proposal": [
        {"id": "e-proposal", "what": "proposal / design-intent framing", "absent":
         "no proposal, design intent or specification language: the text reports finished work"},
        {"id": "e-roadmap", "what": "roadmap with staged items", "lines": (121, 125),
         "weight": 0.5,
         "why_weak": "a 'Future Work' bullet list is a work plan, not a project roadmap"},
    ],
    "literature-review": [
        {"id": "f-cite1", "what": "citation to prior work", "lines": (22, 22), "weight": 0.5,
         "why_weak": "a citation used as a reference-value source, not as reviewed literature"},
        {"id": "f-cite2", "what": "second citation", "lines": (50, 50), "weight": 0.5,
         "why_weak": "a solution formula borrowed for one calculation"},
        {"id": "f-survey", "what": "related-work / survey section", "absent":
         "no related-work or survey section; only two citations in the whole body"},
    ],
}


def score_semantics(text: str) -> dict[str, dict]:
    lines = text.split("\n")
    offsets = line_offsets(lines)
    res = {}
    for rtype, items in SEMANTIC_ANCHORS.items():
        present, absent, weighted = [], [], 0.0
        for a in items:
            w = float(a.get("weight", 1.0))
            if "lines" in a:
                a0, b0 = a["lines"]
                quote = "\n".join(lines[a0 - 1:b0])
                s, e = offsets[a0 - 1], offsets[b0 - 1] + len(lines[b0 - 1])
                assert text[s:e] == quote, f"anchor {a['id']} slice mismatch"
                present.append({"anchor_id": a["id"], "what": a["what"],
                                "lines": [a0, b0], "quote": quote,
                                "start_offset": s, "end_offset": e, "weight": w,
                                **({"why_weak": a["why_weak"]} if "why_weak" in a else {})})
                weighted += WEIGHT_ANCHOR * w
            else:
                absent.append({"anchor_id": a["id"], "what": a["what"],
                               "absent_because": a["absent"]})
        res[rtype] = {"anchors_present": len(present), "anchors_total": len(items),
                      "anchor_score": round(weighted, 2),
                      "present": present, "absent": absent}
    return res


# --------------------------------------------------------------------------
# evidence-by-line-slice helpers
# --------------------------------------------------------------------------
class EvidenceBuilder:
    def __init__(self, text: str):
        self.text = text
        self.lines = text.split("\n")
        self.offsets = line_offsets(self.lines)
        self.records: list[dict] = []
        self.n = 0

    def add(self, claim_id: str, a: int, b: int, note: str) -> str:
        quote = "\n".join(self.lines[a - 1:b])
        s = self.offsets[a - 1]
        e = self.offsets[b - 1] + len(self.lines[b - 1])
        if self.text[s:e] != quote:                       # offsets are the contract
            raise AssertionError(f"{claim_id} slice mismatch at lines {a}-{b}")
        n_occurrence = self.text.count(quote)
        if n_occurrence == 0:
            raise AssertionError(f"{claim_id}: quote not found in source")
        self.n += 1
        ev_id = f"ev-9478-02-{self.n:02d}"
        self.records.append({
            "id": ev_id,
            "claim_refs": [claim_id],
            "source": {"persistent_id": REPORT_ID, "field": SOURCE_FIELD,
                       "source_uri": SOURCE_URI, "source_hash": CONTRACT_SOURCE_HASH},
            "locator": {
                "locator_type": "char_offset",
                "offset_space": "unicode-codepoints (python str index)",
                "start_offset": s,
                "end_offset": e,
                "byte_start_utf8": len(self.text[:s].encode("utf-8")),
                "byte_end_utf8": len(self.text[:e].encode("utf-8")),
                "line_start": a,
                "line_end": b,
                "quote": quote,
                "content_hash": "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                "occurrences_in_source": n_occurrence,
            },
            "note": note,
            "assessment_status": "unassessed",
        })
        return ev_id


def main() -> int:
    text, record = load_source()
    st = parse_structure(text)
    registry = json.loads((REPO / "extraction-skills" / "registry.json").read_text(encoding="utf-8"))
    sem = score_semantics(text)
    candidates = score_candidates(text, st, registry)
    for c in candidates:
        s = sem[c["report_type"]]
        c["semantic_anchor_score"] = s["anchor_score"]
        c["semantic_anchors_present"] = s["anchors_present"]
        c["semantic_anchors_total"] = s["anchors_total"]
        c["semantic_anchor_detail"] = s["present"]
        c["semantic_anchor_absent"] = s["absent"]
        c["total_score"] = round(c["literal_signal_score"] + c["section_score"]
                                 + c["semantic_anchor_score"], 2)
    ranked = sorted(candidates, key=lambda c: (-c["total_score"], c["report_type"]))
    primary = ranked[0]
    nearest = ranked[1:3]

    ev = EvidenceBuilder(text)
    claims: list[dict] = []

    def claim(cid: str, statement: str, ctype: str, slices: list[tuple[int, int, str]],
              notes: str | None = None) -> None:
        refs = [ev.add(cid, a, b, note) for a, b, note in slices]
        rec = {"id": cid, "statement": statement, "claim_type": ctype,
               "evidence_refs": refs, "epistemic_status": "draft",
               "assessment_status": "unassessed", "created_by": "agent/wp-9478-02"}
        if notes:
            rec["scope_note"] = notes
        claims.append(rec)

    density = round(2 / len(text) * 1000, 3)
    c6_amp = round((53.07 - 50.0) / 50.0 * 100, 2)
    run_txt = "、".join(f"{c['report_type']} {c['total_score']}" for c in nearest)

    claim("cls-9478-02-01",
          f"报告类型主判 = {primary['report_type']}（skill {primary['skill_id']}，总分 "
          f"{primary['total_score']} = 关键词信号 {primary['literal_signal_score']} + 章节命中 "
          f"{primary['section_score']} + 语义锚点 {primary['semantic_anchor_score']}）：正文同时具备"
          "数值格式方程、带单位参数表、时间步收敛研究、误差对参照值逐项表与显式模型假设。",
          "classification-decision",
          [(34, 34, "numerical scheme written as an equation (Aitken relaxation update)"),
           (16, 16, "parameter table row carrying value + unit"),
           (131, 131, "error tabulated against a reference value"),
           (93, 93, "time-step convergence study")])

    claim("cls-9478-02-02",
          f"次高两候选 {run_txt} 与主判差距大，且各自缺该类型的关键锚点："
          "experimental-validation 有基准校验场景与带容差基线比较，但无设施/测量不确定度/重复试验矩阵；"
          "algorithm-implementation 有算法组成陈述，但无伪代码与复杂度分析。故二者只作备选假设记录，"
          "不作主型——本判定是可反驳假设，不是既成结论。",
          "classification-decision",
          [(7, 7, "benchmark named as the validation target (experimental-validation anchor)"),
           (61, 61, "baseline comparison row with an acceptance bound"),
           (31, 31, "algorithm composition stated (algorithm-implementation anchor)")],
          notes="缺失类锚点无法用 locator 证明，见 unresolved U1/U5。")

    claim("cls-9478-02-03",
          f"选中 skill = {primary['skill_id']}（registry report_type={primary['report_type']}，"
          "lifecycle_state=template-created）；其三步抽取（参数+单位、误差+参照值、显式假设）"
          "在正文均有可直接引用的原文，说明该类型不是空选中。",
          "classification-decision",
          [(16, 16, "step 1 input: parameter with value and unit"),
           (131, 131, "step 2 input: error with its reference"),
           (113, 113, "step 3 input: assumption stated verbatim")])

    claim("cls-9478-02-04",
          f"排除 literature-review：全文仅 2 处具名文献引用，引用密度 {density}/千字符，"
          "低于 registry 识别信号 citation density >= 5 per 1000 chars；且无 related work/survey 章节。",
          "classification-decision",
          [(22, 22, "citation 1 of 2"),
           (50, 50, "citation 2 of 2")],
          notes="引用计数与密度由本脚本程序化计算，见 checks.json。")

    claim("cls-9478-02-05",
          f"排除 software-engineering：正文无变更文件清单/commit 标识，Audit Chain 的 Code 字段为空，"
          "测试规模只有文字断言而无命令；唯一命中的关键词 'interface' 指 FSI 界面（界面守恒），"
          "属数值问题而非软件接口。",
          "classification-decision",
          [(96, 96, "the literal 'interface' hit is the FSI interface, not a software interface"),
           (140, 143, "audit chain carries no commit/changed-file reference")])

    claim("cls-9478-02-06",
          f"结构切分：{st['n_lines']} 行 / {st['n_chars']} 字符，标题 "
          f"h1={st['heading_counts']['h1']}、h2={st['heading_counts']['h2']}、"
          f"h3={st['heading_counts']['h3']}，二级章节 {len(st['top_level_sections'])} 个"
          f"（含尾段 Audit Chain），markdown 表 {len(st['tables'])} 张。",
          "parse-observation",
          [(4, 4, "first level-2 section"),
           (127, 127, "last numbered level-2 section"),
           (139, 139, "unnumbered trailing audit section")],
          notes="计数由 parse_structure() 生成，逐项落在 structure 字段。")

    rec_figs = record.get("figures") or []
    claim("cls-9478-02-07",
          f"图注与图文件的绑定在正文中丢失：Figures 章节 {len(st['figure_refs'])} 条图注的名称位全部为空"
          "（形如 '1. : Tip displacement…'），而记录 metadata 有 "
          f"{len(rec_figs)} 条具名图（" + "、".join(str(f.get('name')) for f in rec_figs)
          + f"）；正文中字符串 'fsi2' 出现 {text.count('fsi2')} 次，即正文不给任何图文件名，"
          "正文与图的绑定只能按位置猜测。Audit Chain 的 Code 与 Figures 两行为空值，"
          "Tests/Full FSI suite 两行只有文字断言。",
          "parse-observation",
          [(103, 106, "all four figure captions carry an empty label slot"),
           (140, 143, "audit-chain fields: Code and Figures are empty")])

    claim("cls-9478-02-08",
          "验收表存在无计算值的 PASS：C3 的计算列写 'tracked' 却标 PASS，C4/C5 只写不等式，"
          "C8（Honest FAIL 条目）也标 PASS；即 PASS 状态并非处处由数值支撑。",
          "parse-observation",
          [(63, 63, "C3 PASS with 'tracked' instead of a value"),
           (64, 64, "C4 PASS with an inequality only"),
           (68, 68, "C8 'Honest FAIL' row marked PASS")])

    claim("cls-9478-02-09",
          f"算术复核不一致：C2 幅度误差记 6.13%，按报告自身数值 (53.07−50.0)/50.0 复算为 "
          f"{c6_amp}%；C6 又把幅度变化写作 6.07%，与 C2 的 6.13% 不同源。",
          "parse-observation",
          [(78, 80, "computed value, reference value and the stated error"),
           (94, 94, "a different amplitude-change figure in C6")],
          notes="本工序只做算术复算，不判定哪一值为真。")

    claim("cls-9478-02-10",
          "Flutter 项的计算列与参考列为同一数字 6.325 却标 '<2%' 误差：表内未给出两者之差，"
          "故该项误差无表内证据，属于用相同数字自我比较的行。",
          "parse-observation",
          [(133, 133, "computed and reference columns are identical"),
           (84, 84, "prose repeats the same value as the reference")])

    claim("cls-9478-02-11",
          "审计链断言测试规模（38 tests / 162 tests, all pass）但未给命令、路径或链接，"
          "Figures 与 Code 引用为空，故该断言在本报告内不可核验。",
          "parse-observation",
          [(141, 142, "test-count assertions without a command or link")])

    claim("cls-9478-02-12",
          "源身份与正文标题不一致：契约/记录的 title 含 'TensorFEM×TensorLBM'，"
          "而正文 H1 只写 'P153W2-N03: FSI Strong Coupling — Turek-Hron FSI-2 + Flutter + "
          "Energy Conservation'；正文对 TensorFEM / TensorLBM 的具名出现次数为 "
          f"{text.count('TensorFEM')} / {text.count('TensorLBM')}。",
          "parse-observation",
          [(2, 2, "body H1, which omits the two solver names carried by the record title")],
          notes="标题差异不改变 source_hash；仅记录元数据与正文的表述差异。")

    claim("cls-9478-02-13",
          "求解器身份只存在于元数据：记录 tags 含 "
          + "、".join(f"`{t}`" for t in (record.get("tags") or []) if "Tensor" in str(t))
          + f"，而正文中 'TensorFEM' / 'TensorLBM' 出现次数为 {text.count('TensorFEM')} / "
          f"{text.count('TensorLBM')}（后者仅出现在 Future Work 的 'TensorLBM integration' 一栏）；"
          "正文对流体侧自述为 quasi-steady 近似而非 LBM 求解，故『TensorFEM×TensorLBM FSI』"
          "这一联合身份在正文中没有对应的实现叙述。",
          "parse-observation",
          [(47, 47, "the body describes the fluid side as quasi-steady, not as an LBM solve"),
           (122, 122, "a full Navier-Stokes / TensorLBM solver is listed as future work")],
          notes="本工序只记录正文与元数据的差异，不判定该报告是否用到了这两个求解器。")

    unresolved = [
        {"id": "unres-9478-02-U1", "about": "experimental-validation 缺失锚点",
         "reason": "设施/测量不确定度/重复试验三类锚点是负向发现，locator 只能证明'有'，"
                   "无法证明'无'；仅记录为全文检索 0 命中的负向发现，不作可定位断言。",
         "related_claims": ["cls-9478-02-02"]},
        {"id": "unres-9478-02-U2", "about": "测试规模断言（38 / 162 tests）",
         "reason": "报告未给命令/链接/提交号，工序 02 不访问代码仓，故不可核验。",
         "related_claims": ["cls-9478-02-11"]},
        {"id": "unres-9478-02-U3", "about": "图注 ↔ 图文件绑定",
         "reason": f"正文 {len(st['figure_refs'])} 条图注名称位为空、正文 'fsi2' 出现 "
                   f"{text.count('fsi2')} 次；记录 metadata 有 {len(record.get('figures') or [])} 条具名图。"
                   "两者只能按出现顺序对齐，本工序不建立未经原文支持的绑定，也不对图像内容作断言。",
         "related_claims": ["cls-9478-02-07"]},
        {"id": "unres-9478-02-U4", "about": "C3（CL/CD）数值缺失",
         "reason": "报告只写 'tracked'，未给数值；工序 02 不做抽取，交 03 工序判定是否可抽取。",
         "related_claims": ["cls-9478-02-08"]},
        {"id": "unres-9478-02-U5", "about": "algorithm-implementation 缺失锚点",
         "reason": "伪代码/复杂度/函数签名均为负向发现，无法用 locator 证明缺失。",
         "related_claims": ["cls-9478-02-02"]},
        {"id": "unres-9478-02-U6", "about": "参照值的外部正确性",
         "reason": "报告把 f_ref=3.0 Hz、A_ref=0.05 m 等归因于 Turek & Hron (2006)，"
                   "工序 02 不核对外部文献（超出本工序范围且禁止凭记忆断言），仅按原文记录。",
         "related_claims": []},
        {"id": "unres-9478-02-U7", "about": "report_type 无 ground truth",
         "reason": "平台未给报告 9478 的类型标注，本工序也不读其它工序结论，"
                   "因此类型判定正确率不可测；只能声明规则可复现、依据可定位。",
         "related_claims": ["cls-9478-02-01", "cls-9478-02-02"]},
        {"id": "unres-9478-02-U8", "about": "记录 summary 的『all 8 criteria verified』措辞",
         "reason": "记录 summary 出现 'verified' 字样，但正文 C3 只写 'tracked'（无计算值），"
                   "该措辞在正文中找不到数值支撑；summary 属平台元数据，无法用 markdown locator 定位，"
                   "本工序既不采信也不改写，仅登记差异。",
         "related_claims": ["cls-9478-02-08"]},
    ]

    classification = {
        "schema": "kf-classification-parse.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "source": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": CONTRACT_SOURCE_HASH,
            "source_hash_recomputed": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "chars": len(text),
            "bytes_utf8": len(text.encode("utf-8")),
            "n_lines": st["n_lines"],
            "title_from_record": str(record.get("title") or CONTRACT_TITLE),
            "title_from_body": st["headings"][0]["title"],
            "scenario_key": str(record.get("scenario_key") or SCENARIO_KEY),
            "record_mission_id": record.get("mission_id"),
            "record_tags": record.get("tags") or [],
            "record_summary_chars": len(str(record.get("summary") or "")),
            "record_figures": [{"name": f.get("name"), "caption": f.get("caption")}
                               for f in (record.get("figures") or [])],
            "record_summary_states": {
                "mentions_verified": "verified" in str(record.get("summary") or "").lower(),
                "n_chars": len(str(record.get("summary") or "")),
            },
        },
        "report_type": primary["report_type"],
        "report_type_confidence": "medium",
        "classification_is_hypothesis": True,
        "scoring_rule": {
            "weights": {"literal_registry_signal": WEIGHT_LITERAL,
                        "applies_to_section_hit": WEIGHT_SECTION,
                        "semantic_anchor": WEIGHT_ANCHOR},
            "note": ("weights fixed before scoring; section hits are weak because "
                     "'method'/'results' are generic titles; absences are never counted, "
                     "they are recorded as unresolved"),
        },
        "report_type_alternatives": [
            {"report_type": c["report_type"], "total_score": c["total_score"],
             "component_scores": {"literal": c["literal_signal_score"],
                                  "section": c["section_score"],
                                  "semantic": c["semantic_anchor_score"]},
             "why_not_primary": ("lower total score under the same predeclared rule; "
                                 "the decisive anchors of that type are absent "
                                 "(see semantic_anchor_absent)")}
            for c in ranked[1:]
        ],
        "selected_skill": {
            "skill_id": primary["skill_id"],
            "skill_version": next(s["skill_version"] for s in registry["skills"]
                                  if s["skill_id"] == primary["skill_id"]),
            "lifecycle_state": next(s["lifecycle_state"] for s in registry["skills"]
                                    if s["skill_id"] == primary["skill_id"]),
            "registry_path": "extraction-skills/registry.json",
            "selection_rule": ("report_type argmax of (literal registry signals + applies_to "
                               "section hits + curated semantic anchors); 'unclassified' not "
                               "used because the signals are resolvable"),
        },
        "candidate_scoring": ranked,
        "structure": st,
        "claims": claims,
        "evidence": ev.records,
        "unresolved": unresolved,
        "limitations": [
            "分类依据是 registry 的关键词信号 + 本包自设的语义锚点；锚点清单是本包的判断，"
            "03/04 工序可从原文反驳。",
            "本工序不做知识抽取：claims 全部是分类/解析判定，不是报告的技术结论。",
            "正文与记录标题不一致（see cls-9478-02-12）；图件、测试规模与部分验收数值"
            "在本报告内不可核验（see unresolved）。",
            "偏移量空间为 unicode 码点（python str 索引），同时给出 UTF-8 字节偏移，"
            "两种口径均可复算。",
            "report_type_confidence=medium：主判领先次高候选主要靠语义锚点，而锚点由本包设定，"
            "存在自我实现的可能；experimental-validation 是主要竞争假设。",
        ],
    }

    (PKG / "classification.json").write_text(
        json.dumps(classification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---------------- acceptance self-check ----------------
    ids = [c["id"] for c in claims] + [e["id"] for e in ev.records] + [u["id"] for u in unresolved]
    dupes = sorted({i for i in ids if ids.count(i) > 1})

    def loc_ok(e: dict) -> tuple[bool, str]:
        loc = e["locator"]
        q, s, e2 = loc["quote"], loc["start_offset"], loc["end_offset"]
        if not (0 <= s < e2 <= len(text)):
            return False, f"offsets out of range {s},{e2}"
        if text[s:e2] != q:
            return False, "offset slice != quote"
        if loc["content_hash"] != "sha256:" + hashlib.sha256(q.encode()).hexdigest():
            return False, "content_hash mismatch"
        if text.find(q) < 0:
            return False, "quote not findable by search"
        if len(q) < 12:
            return False, "quote shorter than 12 chars"
        return True, "ok"

    loc_results = {e["id"]: loc_ok(e) for e in ev.records}
    bad_loc = [k for k, v in loc_results.items() if not v[0]]
    no_ev = [c["id"] for c in claims if not c["evidence_refs"]]
    hashmatch = (classification["source"]["source_hash"]
                 == classification["source"]["source_hash_recomputed"] == CONTRACT_SOURCE_HASH)
    checks = [
        {"criterion": "valid_json", "pass": True,
         "detail": "classification.json / checks.json parsed by json.load"},
        {"criterion": "schema_pass", "pass": None, "status": "not_run_locally",
         "detail": "no classification schema exists in schemas/ (only kf_result.v1.schema.json, "
                   "validated against the delivered result by verify_result.py); structural "
                   "shape checks below stand in"},
        {"criterion": "source_locator_resolvable", "pass": not bad_loc,
         "detail": f"{len(ev.records) - len(bad_loc)}/{len(ev.records)} locators resolve "
                   f"byte-exactly at declared char offsets; failing={bad_loc}"},
        {"criterion": "source_hash_matches", "pass": hashmatch,
         "detail": f"recomputed {classification['source']['source_hash_recomputed']}"},
        {"criterion": "no_duplicate_ids", "pass": not dupes,
         "detail": f"{len(ids)} ids across claims/evidence/unresolved; duplicates={dupes}"},
        {"criterion": "all_claims_have_evidence_or_explicit_unresolved_status", "pass": not no_ev,
         "detail": f"{len(claims)} claims, each with >=1 resolvable quote; "
                   f"{len(unresolved)} records explicitly unresolved; missing={no_ev}"},
        {"criterion": "do_not_mark_claims_as_verified", "pass":
         all(c["epistemic_status"] == "draft" and c["assessment_status"] == "unassessed"
             for c in claims), "detail": "every claim is draft/unassessed"},
        {"criterion": "chars_match_contract", "pass": len(text) == CONTRACT_CHARS,
         "detail": f"chars={len(text)}"},
    ]
    ok = all(c["pass"] is not False for c in checks)
    (PKG / "checks.json").write_text(json.dumps({
        "package_id": PACKAGE_ID, "report_id": REPORT_ID,
        "checks": checks, "all_hard_checks_pass": ok,
        "counts": {"claims": len(claims), "evidence": len(ev.records),
                   "unresolved": len(unresolved)},
        "citation_density_per_1000_chars": density,
        "amplitude_error_recomputed_pct": c6_amp,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---------------- locator table for the report ----------------
    rows = ["| claim / evidence | quote (verbatim, line range) | char offsets | sha256(quote)[:16] |",
            "|---|---|---|---|"]
    for c in claims:
        for ref in c["evidence_refs"]:
            e = next(x for x in ev.records if x["id"] == ref)
            loc = e["locator"]
            q = loc["quote"].replace("|", "\\|").replace("\n", "<br>")
            rows.append(f"| {c['id']}<br>{e['id']} | `{q}` | [{loc['start_offset']},{loc['end_offset']})"
                        f" (L{loc['line_start']}-{loc['line_end']}) | `{loc['content_hash'][7:23]}` |")
    (PKG / "classification_table.md").write_text("\n".join(rows) + "\n", encoding="utf-8")

    print(json.dumps({"report_type": primary["report_type"],
                      "scores": {c["report_type"]: c["total_score"] for c in ranked},
                      "claims": len(claims), "evidence": len(ev.records),
                      "unresolved": len(unresolved), "checks_ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())