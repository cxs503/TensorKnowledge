"""Knowledge Compiler v1 — 输入 → 待评审知识对象（KO v1）。

规范：``docs/compiler/KNOWLEDGE-COMPILER-SPEC-v1.md``（S1–S7 七段，与 Knowledge
Factory 工序 01–05 对齐）。本模块是**执行面**；契约与治理判据在 TensorKnowledge
``schemas/knowledge-object-v1.schema.json`` + ``scripts/validate_ko_v1.py``。

七段（每段都有可机器裁的产物，不做隐式黑箱）：

==== ====================== ===============================================
段    名称                    产物
==== ====================== ===============================================
S1    输入规范化              source_hash（sha256 字节口径）+ 小节切分
S2    主题与研究问题识别       topic{title, repo, questions[], terms[]}
S3    概念与知识单元拆解       units[{unit_id, section, terms[], n_claims}]
S4    Claim/Evidence 抽取     claims[] + evidence[]（逐字引文 + 偏移 + sha256）
S5    关系与来源              relations[]（derived_from 小节 / contradicts）
S6    重复与矛盾识别           duplicates[] + contradictions[]（含跨报告面）
S7    待评审 KO 产出           kobjects[]（ko/v1，verification_status=report_claimed）
==== ====================== ===============================================

**证据纪律**（缺一条即判该 claim 弃取，计入 ``rejected``）：

* E1 引文是该报告 markdown 的**逐字子串**，且声明的 [start,end) 与子串一致；
* E2 引文落在声明小节的 span 内（小节 anchor/sha256 由 ``iter_sections`` 重算）；
* E3 数值全部能在引文内重算出来（不做四舍五入改写）。

**不做的事**（写进 ``limitations``，不隐藏）：无语义判断、不做跨语言改写、
不判定 claim 真假、不写 verified（L3 只走平台验证单）。0 条 claim 是合法完整
结果（约束 ``no_forced_claim_generation``）。

CLI::

    python -m ke.compiler --report-id 14537 --out-dir runs/compiler-v1/r14537
    python -m ke.compiler --markdown-file /tmp/r.txt --report-id 1 --no-db
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:  # reuse the single section-anchor implementation
    sys.path.insert(0, str(_SCRIPTS))

from validate_ko_v1 import (  # noqa: E402  (reuse: 小节锚 + KO 校验 + 内容哈希)
    KOError,
    content_sha256,
    iter_sections,
    slugify,
    validate_document,
)

COMPILER_VERSION = "1.0.0"
PIPELINE = "knowledge-compiler-v1"

#: 工序 03 的四个输出文件名（与 factory contracts 同键，不另起）
OUTPUT_NAMES = ("claims.json", "evidence.json", "provenance.json", "extraction_summary.json")

# ---------------------------------------------------------------- 规则常数
#: 段落切分：空行为界（单换行是排版折行，不是断言边界）。
PARAGRAPH_RE = re.compile(r"(?:[^\n]|\n(?!\s*\n))+")
#: 句子切分：块内按中英句末标点切（报告普遍中英混排，不做语种判定）。
SENTENCE_RE = re.compile(r"[^。！？；!?;]+[。！？；!?;]?")

#: 数值 + 可选单位（宁可漏抽也不误抽：只认常见单位与符号）
NUMBER_RE = re.compile(
    r"(?<![\w.])"
    r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"
    r"\s*(?:%|‰|kn|m/s|km/h|kg/m3|kg|N·m|Nm|Pa|kPa|MPa|Hz|kHz|dB|mm|cm|km|m|s|K|℃|°C|°|rad|deg)?"
)

#: 判定词（有判定词无数字也收：结论型断言同样值得评审）
VERDICT_RE = re.compile(
    r"误差|偏差|优于|低于|高于|提升|提高|降低|下降|达到|验证|一致|吻合|收敛|满足|"
    r"表明|说明|显示|因此|结论|证明|不支持|失败|局限|"
    r"\berror\b|\bagree|\bwithin\b|\breduce|\bincrease|\bimprov|\bconverg|"
    r"\bvalidat|\bcompared\b|\bresults?\b|\btherefore\b|\bfail",
    re.IGNORECASE,
)

#: 方法/过程句
METHOD_RE = re.compile(
    r"采用|使用|基于|通过|方法|流程|算法|公式|实现|构造|离散|"
    r"\busing\b|\bmethod\b|\bbased on\b|\balgorithm\b|\bimplement|\bformulat",
    re.IGNORECASE,
)

#: 定义句
DEF_RE = re.compile(r"定义|称为|记为|即|指的是|\bdefined as\b|\bdenoted\b|\bmeans\b", re.IGNORECASE)

#: 能力声明句
CAP_RE = re.compile(r"支持|实现|提供|覆盖|\bsupport|\bprovide|\bcapab", re.IGNORECASE)

#: 负知识句（局限/失败/不适用）
NEG_RE = re.compile(r"不支持|无法|失败|局限|不足|失效|误差偏大|\bnot support|\bfail|\blimit", re.IGNORECASE)

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

#: 主题词停用表（领域中立；域词表由域仓注入，不在此硬编码）
STOP_TERMS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "which",
    "结果", "方法", "我们", "可以", "进行", "使用", "通过", "报告", "本节", "如下", "以及",
    "一个", "这个", "因此", "从而", "基于", "采用", "支持", "实现", "提供",
}


# ================================================================ dataclasses
@dataclass
class Claim:
    """S4 产物：一条原子断言 + 它的逐字证据。"""

    claim_id: str
    text: str
    claim_type: str
    modality: str
    section: dict[str, Any]
    quote: str
    char_start: int
    char_end: int
    numbers: list[dict[str, Any]] = field(default_factory=list)
    template: str = ""

    @property
    def norm(self) -> str:
        return normalize_text(self.text)


@dataclass
class CompileResult:
    report_id: int
    source_hash: str
    markdown_len: int
    topic: dict[str, Any]
    units: list[dict[str, Any]]
    claims: list[Claim]
    duplicates: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    kobjects: list[dict[str, Any]]
    domain: str = "unclassified"
    producer: str = "agent-m15720"
    mission_id: int | None = None
    created_at: str = ""

    # ------------------------------------------------------------ 四契约输出
    def claim_records(self) -> list[dict[str, Any]]:
        out = []
        for c in self.claims:
            out.append(
                {
                    "id": c.claim_id,
                    "statement": c.text,
                    "claim_type": c.claim_type,
                    "epistemic_status": "not-assessed",
                    "modality": c.modality,
                    "scope": {
                        "report_id": self.report_id,
                        "section": c.section["heading"],
                        "char_span": [c.char_start, c.char_end],
                    },
                    "evidence_refs": [evidence_id(self.report_id, c.claim_id)],
                    "created_at": self.created_at,
                    "created_by": self.producer,
                    "version": "1.0.0",
                    "notes": ["compiled by %s (rule-level)" % PIPELINE],
                }
            )
        return out

    def evidence_records(self) -> list[dict[str, Any]]:
        out = []
        for c in self.claims:
            out.append(
                {
                    "id": evidence_id(self.report_id, c.claim_id),
                    "claim_refs": [c.claim_id],
                    "source": {
                        "source_type": "other",
                        "citation": "tensor_reports:%d §%s" % (self.report_id, c.section["heading"]),
                        "url": "tensor://reports/%d" % self.report_id,
                    },
                    "relation": "supports",
                    "locator": {
                        "locator_type": "report-section",
                        "value": "report:%d#%s@%d-%d"
                        % (self.report_id, c.section["anchor"], c.char_start, c.char_end),
                        "quote": c.quote,
                        "char_span": [c.char_start, c.char_end],
                        "section_sha256": c.section["section_sha256"],
                        "source_hash": self.source_hash,
                    },
                    "extraction_method": "automated-extraction",
                    "captured_at": self.created_at,
                    "captured_by": self.producer,
                    "assessment_status": "unassessed",
                    "version": "1.0.0",
                }
            )
        return out

    def provenance_records(self) -> list[dict[str, Any]]:
        return [
            {
                "id": provenance_id(self.report_id),
                "generated_entity": {
                    "id": "compile:report:%d" % self.report_id,
                    "entity_type": "knowledge-object-set",
                    "version": "1.0.0",
                },
                "activity": {
                    "id": "compile-report-%d" % self.report_id,
                    "activity_type": "extraction",
                    "description": (
                        "Knowledge Compiler v%s S1–S7 on tensor_reports.id=%d "
                        "(rule-level claim extraction; no semantic judgement)"
                        % (COMPILER_VERSION, self.report_id)
                    ),
                    "started_at": self.created_at,
                    "ended_at": self.created_at,
                    "used_entities": ["tensor_report:%d" % self.report_id],
                    "software": [{"name": "python", "version": "3.11"}],
                },
                "agents": [
                    {
                        "id": self.producer,
                        "agent_type": "software-agent",
                        "name": "Knowledge Compiler (TensorKnowledge)",
                        "role": "knowledge compiler",
                    }
                ],
                "derived_from": ["tensor_report:%d" % self.report_id],
                "attributed_to": ["TensorPlatform tensor_reports"],
                "recorded_at": self.created_at,
                "extensions": {
                    "compiler_version": COMPILER_VERSION,
                    "source_hash": self.source_hash,
                    "provenance_kind": "factory-compile",
                },
                "version": "1.0.0",
            }
        ]

    def summary(self) -> dict[str, Any]:
        return {
            "compiler_version": COMPILER_VERSION,
            "report_id": self.report_id,
            "source_hash": self.source_hash,
            "markdown_chars": self.markdown_len,
            "topic": self.topic,
            "n_sections": len(self.topic.get("sections", [])),
            "n_units": len(self.units),
            "n_claims": len(self.claims),
            "n_kobjects": len(self.kobjects),
            "n_duplicates": len(self.duplicates),
            "n_contradictions": len(self.contradictions),
            "n_rejected": len(self.rejected),
            "rejected_reasons": _counts(r["reason"] for r in self.rejected),
            "claim_types": _counts(c.claim_type for c in self.claims),
            "verification_ceiling": "report_claimed",
            "empty_is_complete": len(self.claims) == 0,
            "created_at": self.created_at,
            "producer": self.producer,
        }


def _counts(values: Iterable[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


# ================================================================ id helpers
def normalize_text(text: str) -> str:
    """归一化（只用于重复/模板判等，不改引文原文）。"""
    return re.sub(r"\s+", "", text.strip().lower())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def claim_id(report_id: int, idx: int) -> str:
    return "tkc:rpt%d:c%03d" % (report_id, idx)


def evidence_id(report_id: int, cid: str) -> str:
    return "tke:" + sha256_text("%d|%s" % (report_id, cid))[:24]


def provenance_id(report_id: int) -> str:
    return "tkp:compile-%d" % report_id


def ko_anchor(anchor: str) -> str:
    """KO v1 锚点字符集（^[a-z0-9\\u4e00-\\u9fff][a-z0-9\\u4e00-\\u9fff-]*$）。

    ``iter_sections`` 的 slug 保留 ``_``（四契约那条线允许），KO schema 不允许；
    在这里做一次显式正交化，不改上游 slug 定义（避免两处锚点口径打架）。
    """
    out = re.sub(r"[^a-z0-9\u4e00-\u9fff-]+", "-", anchor.lower())
    out = re.sub(r"-{2,}", "-", out).strip("-")
    return out or "section"


def ko_id(facet: str, report_id: int, idx: int) -> str:
    return "ko:%s:r%d-c%03d" % (facet, report_id, idx)


def _iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# =========================================================== S1 输入规范化
def mask_fences(markdown: str) -> str:
    """把 ``` 代码块内容替换为等长空白，保证偏移不变而代码行不被当断言。"""

    def blank(m: re.Match[str]) -> str:
        return "".join("\n" if ch == "\n" else " " for ch in m.group(0))

    return FENCE_RE.sub(blank, markdown)


def split_sentences(masked: str, start: int, end: int) -> list[tuple[int, int]]:
    """在 [start,end) 内切句，返回 (s, e) 偏移。

    段落以空行为界（单换行是折行）；表格行（``|`` 开头）与标题行跳过——
    表格是数据行不是原子断言，收进来只会产出不可读的 claim。
    """
    out: list[tuple[int, int]] = []
    for para in PARAGRAPH_RE.finditer(masked, start, end):
        ps, pe = para.start(), para.end()
        chunk = masked[ps:pe]
        first = chunk.lstrip()
        if first.startswith("#") or first.startswith("|"):
            continue
        for m in SENTENCE_RE.finditer(masked, ps, pe):
            s, e = m.start(), m.end()
            seg = masked[s:e]
            if not seg.strip():
                continue
            left = len(seg) - len(seg.lstrip())
            right = len(seg.rstrip())
            s, e = s + left, s + right
            if e <= s or e - s < 8:
                continue
            if masked[s:e].lstrip().startswith("|"):
                continue
            out.append((s, e))
    return out


def extract_numbers(text: str) -> list[dict[str, Any]]:
    nums = []
    for m in NUMBER_RE.finditer(text):
        raw = m.group(0).strip()
        num = re.match(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", raw)
        if not num:
            continue
        unit = raw[len(num.group(0)):].strip() or None
        try:
            value = float(num.group(0))
        except ValueError:  # pragma: no cover - defensive
            continue
        if not math.isfinite(value):  # 溢出/非有限值不进知识对象（JSON 也无法表示）
            continue
        nums.append({"value": value, "raw": raw, "unit": unit})
    return nums


#: 模板掩码专用（无 lookbehind：CJK 紧贴数字时也要掩掉，否则模板不可比）
TEMPLATE_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def template_of(norm_text: str) -> str:
    """数值掩码模板：同模板不同数值 = 潜在矛盾/可比较项。"""
    return TEMPLATE_NUM_RE.sub("<N>", norm_text)


# ====================================================== S2 主题与研究问题
def identify_topic(markdown: str, sections: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    heads = [s for s in sections]
    title = ""
    for s in heads:
        if s["level"] == 1:
            title = s["heading"]
            break
    if not title and heads:
        title = heads[0]["heading"]
    questions: list[dict[str, Any]] = []
    for s in heads:
        h = s["heading"]
        if "?" in h or "？" in h or re.search(r"研究问题|问题|目标|目的|question|objective", h, re.I):
            questions.append({"section": h, "anchor": s["anchor"], "source": "heading-rule"})
    whitespace = mask_fences(markdown)
    for s in heads:
        a, b = s["span"]
        for m in re.finditer(r"[^\n。！？!?]{4,120}[？?]", whitespace[a:b]):
            q = m.group(0).strip()
            if q and all(q != x["section"] for x in questions):
                questions.append({"section": q, "anchor": s["anchor"], "source": "question-mark-rule"})
            if len(questions) >= 12:
                break
        if len(questions) >= 12:
            break
    return {
        "title": title,
        "n_sections": len(heads),
        "sections": [
            {"heading": s["heading"], "anchor": s["anchor"], "level": s["level"], "span": s["span"],
             "section_sha256": s["section_sha256"]}
            for s in heads
        ],
        "questions": questions[:12],
        "terms": top_terms(whitespace, limit=20),
    }


def top_terms(text: str, limit: int = 20) -> list[str]:
    """无词典的主题词统计（CJK 双字 + 拉丁词），领域中立。"""
    latin = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text)
    cjk = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
    counts: dict[str, int] = {}
    for tok in [t.lower() for t in latin] + cjk:
        if tok in STOP_TERMS:
            continue
        counts[tok] = counts.get(tok, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [t for t, n in ranked if n >= 2][:limit]


# ================================================= S4 Claim/Evidence 抽取
def classify_claim(text: str) -> tuple[str, str]:
    """(claim_type, modality)。类型词表来自 claim-record；不写 epistemic 结论。"""
    modality = "conditional" if re.search(r"若|当|如果|\bif\b|\bwhen\b", text, re.I) else "asserted"
    if NEG_RE.search(text):
        return "interpretive", modality
    if DEF_RE.search(text) and not extract_numbers(text):
        return "definition", modality
    if METHOD_RE.search(text) and not extract_numbers(text):
        return "methodological", modality
    if CAP_RE.search(text) and not extract_numbers(text):
        return "descriptive", modality
    if re.search(r"=|≈|~", text) and extract_numbers(text):
        return "mathematical", modality
    if extract_numbers(text):
        return "descriptive", modality
    return "other", modality


def extract_claims(
    markdown: str, sections: Sequence[Mapping[str, Any]], *, report_id: int,
    max_claims: int = 200,
) -> tuple[list[Claim], list[dict[str, Any]]]:
    masked = mask_fences(markdown)
    claims: list[Claim] = []
    rejected: list[dict[str, Any]] = []
    seen: dict[str, str] = {}

    for idx, s in enumerate(sections):
        a, b = s["span"]
        # 小节嵌套：子小节正文归子小节，父节只收自己的正文，避免同一段被判两次
        own_end = b
        for t in sections[idx + 1:]:
            ts = t["span"][0]
            if ts <= a:
                continue
            if ts >= b:
                break
            if t["level"] > s["level"]:
                own_end = min(own_end, ts)
                break
        for (cs, ce) in split_sentences(masked, a, own_end):
            quote = markdown[cs:ce]
            if len(quote) > 600:  # 长段落不当作单条原子断言
                rejected.append({"reason": "too_long", "char_span": [cs, ce]})
                continue
            nums = extract_numbers(quote)
            if not nums and not VERDICT_RE.search(quote):
                continue
            if len(quote.strip()) < 10:
                rejected.append({"reason": "too_short", "char_span": [cs, ce]})
                continue
            # E1：引文必须是逐字子串，且声明的偏移与子串一致
            if markdown[cs:ce] != quote or quote not in markdown:
                rejected.append({"reason": "quote_not_verbatim", "char_span": [cs, ce]})
                continue
            # E2：引文落在小节 span 内
            if not (a <= cs < ce <= own_end):
                rejected.append({"reason": "outside_section", "char_span": [cs, ce]})
                continue
            ctype, modality = classify_claim(quote)
            cid = claim_id(report_id, len(claims) + 1)
            c = Claim(
                claim_id=cid, text=quote.strip(), claim_type=ctype, modality=modality,
                section=dict(s), quote=quote, char_start=cs, char_end=ce,
                numbers=nums, template=template_of(normalize_text(quote)),
            )
            # 报告内精确重复：保留首条，其余登记（不删除证据链事实）
            key = sha256_text(c.norm)
            if key in seen:
                rejected.append({"reason": "duplicate", "claim_id": cid, "duplicate_of": seen[key]})
                continue
            seen[key] = cid
            claims.append(c)
            if len(claims) >= max_claims:
                return claims, rejected
    return claims, rejected


# ===================================================== S5/S6 关系与矛盾
def detect_contradictions(claims: Sequence[Claim]) -> list[dict[str, Any]]:
    """同模板（数值掩码后完全相同）但数值集合不同 → 矛盾候选。

    这是**结构规则**，不是语义判断：登记为待评审矛盾边，由工序 04 独立评审裁定。
    """
    by_tpl: dict[str, list[Claim]] = {}
    for c in claims:
        by_tpl.setdefault(c.template, []).append(c)
    out = []
    for tpl, group in by_tpl.items():
        if len(group) < 2:
            continue
        sigs = {tuple(sorted(round(n["value"], 9) for n in c.numbers)) for c in group}
        if len(sigs) > 1:
            out.append(
                {
                    "template": tpl,
                    "claim_ids": [c.claim_id for c in group],
                    "values": [[n["value"] for n in c.numbers] for c in group],
                    "rule": "same-template-different-numbers",
                    "status": "needs-independent-review",
                }
            )
    return out


def detect_duplicates(claims: Sequence[Claim]) -> list[dict[str, Any]]:
    """模板相同且数值相同 = 近重复（措辞差异不影响判等）。"""
    seen: dict[str, str] = {}
    out = []
    for c in claims:
        key = c.template + "|" + ",".join("%.9g" % n["value"] for n in c.numbers)
        if key in seen:
            out.append({"claim_id": c.claim_id, "duplicate_of": seen[key], "rule": "same-template-same-numbers"})
        else:
            seen[key] = c.claim_id
    return out


def build_relations(claims: Sequence[Claim], contradictions: Sequence[Mapping[str, Any]],
                    report_id: int, facet: str) -> dict[str, list[dict[str, Any]]]:
    by_id = {c.claim_id: c for c in claims}
    rels: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        rels.setdefault(c.claim_id, []).append(
            {
                "type": "derived_from",
                "target_id": "report:%d#%s" % (report_id, ko_anchor(c.section["anchor"])),
                "note": "S5 来源小节锚（span + section_sha256 可复核）",
            }
        )
    for con in contradictions:
        ids = con["claim_ids"]
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if a in by_id and b in by_id:
                    rels.setdefault(a, []).append(
                        {"type": "contradicts", "target_id": b, "note": "S6 同模板异值，待独立评审"}
                    )
    return rels


# ================================================== S7 待评审 KO 产出
KO_TYPE = {
    "descriptive": "measurement",
    "mathematical": "measurement",
    "methodological": "procedure",
    "definition": "definition",
    "interpretive": "negative_result",
    "other": "capability_claim",
}


def build_kobjects(
    result_claims: Sequence[Claim], relations: Mapping[str, list[dict[str, Any]]], *,
    report_id: int, facet: str, domain: str, subject: str, producer: str,
    created_at: str, source_hash: str,
) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for c in result_claims:
        kid = ko_id(facet, report_id, int(c.claim_id.rsplit("c", 1)[1]))
        rels = relations.get(c.claim_id, [])
        doc: dict[str, Any] = {
            "schema_version": "ko/v1",
            "knowledge_id": kid,
            "version": 1,
            "type": KO_TYPE.get(c.claim_type, "capability_claim"),
            "domain": domain,
            "subject": subject,
            "claim": c.text,
            "conditions": {
                "description": "报告 %d §%s（逐字引文见 evidence.section）" % (report_id, c.section["heading"]),
                "assumptions": ["断言语义未由编译面判定（规则级抽取）"],
                "validity_range": {},
            },
            "evidence": [
                {
                    "evidence_id": "ev:" + sha256_text("%s|%d" % (kid, 0))[:16],
                    "report_id": report_id,
                    "report_kind": "tensor_report",
                    "section": {
                        "heading": c.section["heading"],
                        "anchor": ko_anchor(c.section["anchor"]),
                        "span": list(c.section["span"]),
                        "section_sha256": c.section["section_sha256"],
                        "excerpt": c.quote[:2000],
                    },
                    "evidence_type": "documentation",
                    "relation": "supports",
                    "artifact_ref": {"kind": "none", "ref": "report_section"},
                    "resolution": {
                        "report_resolved": True,
                        "section_resolved": True,
                        "artifact_resolved": False,
                        "resolver_version": PIPELINE,
                        "resolved_at": created_at,
                    },
                }
            ],
            "confidence": {
                "level": "low",
                "basis": "unassessed",
                "note": "编译面只保证引文可回链；是否成立由工序 04 独立评审与平台门判定",
            },
            "verification_status": "report_claimed",
            "limitations": [
                "规则级抽取（数值/判定词触发），未做语义判断",
                "单报告面，未与其它报告交叉核对（跨报告矛盾由 S6 批级扫描登记）",
                "不声称已复核；L3 只经平台验证单",
            ],
            "relations": rels,
            "provenance": {
                "producer": producer,
                "producer_role": "agent",
                "created_at": created_at,
                "pipeline": PIPELINE,
                "generator_version": COMPILER_VERSION,
                "derived_from": ["tensor_report:%d" % report_id],
                "storage_level": "L2" if rels else "L1",
            },
            "payload": {
                "claim_type": c.claim_type,
                "char_span": [c.char_start, c.char_end],
                "numbers": c.numbers,
                "template": c.template,
            },
        }
        doc["provenance"]["content_sha256"] = content_sha256(doc)
        docs.append(doc)
    return docs


# ================================================================ 主流程
def compile_report(
    markdown: str, *, report_id: int, domain: str = "unclassified",
    facet: str = "tensorplatform", producer: str = "agent-m15720",
    mission_id: int | None = None, created_at: str | None = None,
    max_claims: int = 200,
) -> CompileResult:
    """S1–S7 全跑一遍，返回带四契约记录与 KO 文档的结果对象。"""
    if not isinstance(markdown, str):
        raise TypeError("markdown must be str")
    created = created_at or _iso_now()
    source_hash = sha256_text(markdown)
    sections = iter_sections(markdown)  # S1
    topic = identify_topic(markdown, sections)  # S2
    claims, rejected = extract_claims(markdown, sections, report_id=report_id, max_claims=max_claims)  # S4
    units = [
        {
            "unit_id": "ku:rpt%d:s%02d" % (report_id, i + 1),
            "section": s["heading"],
            "anchor": s["anchor"],
            "terms": top_terms(markdown[s["span"][0]:s["span"][1]], limit=6),
            "n_claims": sum(1 for c in claims if c.section["anchor"] == s["anchor"]),
        }
        for i, s in enumerate(sections)
    ]  # S3（概念层 = 小节 × 主题词 × 断言计数）
    contradictions = detect_contradictions(claims)  # S6
    duplicates = detect_duplicates(claims)
    relations = build_relations(claims, contradictions, report_id, facet)  # S5
    subject = (topic["title"] or "report-%d" % report_id)[:120]
    kobjects = build_kobjects(
        claims, relations, report_id=report_id, facet=facet, domain=domain,
        subject=subject, producer=producer, created_at=created, source_hash=source_hash,
    )  # S7
    for doc in kobjects:  # 出库前必须过 ko/v1 校验（不通过就是缺陷，不静默降级）
        validate_document(doc)
    return CompileResult(
        report_id=report_id, source_hash=source_hash, markdown_len=len(markdown),
        topic=topic, units=units, claims=claims, duplicates=duplicates,
        contradictions=contradictions, rejected=rejected, kobjects=kobjects,
        domain=domain, producer=producer, mission_id=mission_id, created_at=created,
    )


def kf_result_envelope(res: CompileResult, package_id: str) -> dict[str, Any]:
    """包一层 factory 工序 03 的结果信封（schemas/kf_result.v1.schema.json）。"""
    return {
        "package_id": package_id,
        "task_type": "03",
        "report_id": str(res.report_id),
        "provenance": {
            "source_hash": "sha256:" + res.source_hash,
            "source_field": "markdown",
            "producer": res.producer,
            "emitted_at": res.created_at,
            "notes": "%s v%s S1-S7" % (PIPELINE, COMPILER_VERSION),
        },
        "outputs": {
            "claims.json": res.claim_records(),
            "evidence.json": res.evidence_records(),
            "provenance.json": res.provenance_records(),
            "extraction_summary.json": res.summary(),
        },
        "claims": [
            {
                "claim_id": c.claim_id,
                "text": c.text,
                "status": "supported" if c.numbers or VERDICT_RE.search(c.text) else "unresolved",
                "evidence": [{"quote": c.quote, "source_field": "markdown"}],
            }
            for c in res.claims
        ],
    }


def fetch_report(report_id: int) -> dict[str, Any]:
    """从平台库取真实报告（markdown + 仓储面），只读。"""
    import psycopg
    from psycopg.rows import dict_row

    dsn = os.environ.get("TP_PG_DSN") or "dbname=tensorplatform user=postgres"
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        row = conn.execute(
            "SELECT id, title, markdown, scenario_key, mission_id, tags FROM tensor_reports WHERE id = %s",
            (int(report_id),),
        ).fetchone()
    if not row:
        raise LookupError("tensor_reports.id=%s not found" % report_id)
    return row


def dump_result(res: CompileResult, out_dir: Path) -> dict[str, Any]:
    """落盘：四契约四文件 + kobjects/ + summary.json（可复跑、可 diff）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "claims.json": res.claim_records(),
        "evidence.json": res.evidence_records(),
        "provenance.json": res.provenance_records(),
        "extraction_summary.json": res.summary(),
        "kobjects.json": res.kobjects,
        "units.json": res.units,
        "topic.json": res.topic,
        "duplicates.json": res.duplicates,
        "contradictions.json": res.contradictions,
        "rejected.json": res.rejected,
    }
    digests = {}
    for name, obj in payloads.items():
        text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (out_dir / name).write_text(text, encoding="utf-8")
        digests[name] = sha256_text(text)
    (out_dir / "digests.json").write_text(
        json.dumps(digests, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return digests


# ====================================================================== CLI
def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Knowledge Compiler v1 (S1–S7)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--report-id", type=int, help="tensor_reports.id（真实报告，从平台库读）")
    src.add_argument("--markdown-file", help="本地 markdown 文件（离线/测试）")
    ap.add_argument("--report-id-for-file", type=int, default=0, help="配合 --markdown-file 的伪 id（测试用）")
    ap.add_argument("--domain", default="unclassified")
    ap.add_argument("--facet", default="tensorplatform")
    ap.add_argument("--producer", default="agent-m15720")
    ap.add_argument("--out-dir", help="产物目录")
    args = ap.parse_args(argv)

    if args.report_id:
        rec = fetch_report(args.report_id)
        markdown, rid = rec["markdown"] or "", int(rec["id"])
        domain = args.domain if args.domain != "unclassified" else (
            (rec.get("scenario_key") or "").strip() or "unclassified")
    else:
        markdown = Path(args.markdown_file).read_text(encoding="utf-8")
        rid, domain = args.report_id_for_file, args.domain
    if not markdown.strip():
        raise SystemExit("empty markdown for report %s" % rid)
    res = compile_report(markdown, report_id=rid, domain=domain, facet=args.facet, producer=args.producer)
    if args.out_dir:
        digests = dump_result(res, Path(args.out_dir))
        print(json.dumps({"report_id": rid, "claims": len(res.claims), "digests": digests}, ensure_ascii=False))
    else:
        print(json.dumps(res.summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

# ================================================ 治理闸：编译产物的证据复核
def verify_kobject(doc: Mapping[str, Any], markdown: str, *, report_id: int | None = None) -> dict[str, Any]:
    """对单条 KO 做「证据三闸」复核（G1 结构已在构建时校验，这里只做 G2 证据）。

    闸门（与 ``docs/production/GATE-RULES.md`` 的 E* 同义，不另立判据）：

    * E-report：``report_id`` 与来源报告一致（调用方给定则必须相等）；
    * E-section：``heading/anchor/span/section_sha256`` 能由 markdown 重算命中；
    * E-quote：``excerpt`` 是报告 markdown 的逐字子串且落在小节 span 内。

    返回 ``{ok, checks:{...}, reason}``；不通过即**不得**计入走通全链。
    """
    checks: dict[str, Any] = {}
    reason = ""
    ev = (doc.get("evidence") or [{}])[0]
    rid = ev.get("report_id")
    checks["report_resolved"] = bool(rid) and (report_id is None or int(rid) == int(report_id))
    sec = ev.get("section") or {}
    try:
        sections = iter_sections(markdown)
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "checks": checks, "reason": "section-split-failed: %s" % exc}
    hit = None
    for s in sections:
        if s["heading"] == sec.get("heading"):
            hit = s
            break
    if hit and sec.get("span") and [int(sec["span"][0]), int(sec["span"][1])] != hit["span"]:
        hit = None  # 声明偏移必须精确命中，避免 anchor 相同内容漂移
    if hit and sec.get("section_sha256") and sec["section_sha256"] != hit["section_sha256"]:
        hit = None
    checks["section_resolved"] = hit is not None
    excerpt = sec.get("excerpt") or ""
    quote_ok = bool(excerpt) and excerpt in markdown and hit is not None and (
        hit["span"][0] <= markdown.index(excerpt, hit["span"][0]) < hit["span"][1]
    )
    checks["quote_verbatim"] = quote_ok
    checks["artifact_resolved"] = (ev.get("artifact_ref") or {}).get("kind") == "none"
    ok = checks["report_resolved"] and checks["section_resolved"] and quote_ok
    if not ok:
        reason = ",".join(k for k, v in checks.items() if not v)
    return {"ok": ok, "checks": checks, "reason": reason}
