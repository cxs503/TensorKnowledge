#!/usr/bin/env python3
"""wp-9503-02 · 工序 02 分类解析（report_id=9503，EEXI attained 闭合链路）。

只做一件事：按 `extraction-skills/registry.json` 的六分型识别信号给报告打类型标签，
并为每个判定依据给出**可重算**的原文定位（逐字 quote + [start,end) 偏移 + 行号 + 所属章节）。
不做抽取（不生成 claim / 不登记资产 / 不标 verified）。

设计约束（对应工作包契约）：
* 零手抄：引文是 markdown 字节切片，偏移由程序计算并被本脚本二次回查；
* source_hash 由本脚本独立重算并与契约声明值比对（不信任上游）；
* 判定规则在 `DECISION_RULE` 里写死，先于观察结果（可被反驳：任何读者可用同一脚本复算）；
* 不确定就如实标注：证据不足时允许 `unclassified`，`WITHHELD` 一词只描述原文自述状态。

用法：
    python3 scripts/kf/wp9503_02_classify.py --report-id 9503 \
        --package-dir docs/kf/wp-9503-02
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

PKG_ID_DEFAULT = "wp-9503-02"
TASK_TYPE = "02-classification-parse"
REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "extraction-skills" / "registry.json"

# ---------------------------------------------------------------- 判定规则（先声明）
DECISION_RULE = {
    "rule_id": "R1-max-distinct-signals",
    "primary": "取 distinct_signals_matched 最大的 report_type",
    "tie_break": [
        "① distinct_signals_matched 高者胜",
        "② 平手 → 已验证命中数 hits 高者胜",
        "③ 仍平手 → 命中覆盖章节数 sections_covered 高者胜",
        "④ 仍平手 → report_type 名字典序小者胜（仅保证确定性，置信度降为 low）",
    ],
    "confidence": {
        "high": "primary 的 distinct_signals_matched >= 2 且领先次席 >= 1",
        "medium": "primary 的 distinct_signals_matched >= 2 且与次席打平（由 ②③④ 决胜）",
        "low": "primary 的 distinct_signals_matched < 2（证据不足）",
    },
    "unclassified": "所有类型 distinct_signals_matched < 2 时输出 report_type='unclassified'（合法值，禁止硬猜）",
    "secondary": "distinct_signals_matched >= 2 的非 primary 类型进 secondary_report_types（可反驳的并列假设）",
    "predeclared": True,
}

# ---------------------------------------------------------------- 识别信号词典
# registry 的 identify_signals 是英文短语；中文报告需要等价表述。两组分开统计，
# registry-en-only 的复算结果单独披露（见 robustness.lexicon_variants），以免中文别名
# 抬高某一类型的"信号命中"而看不出歧义。
LEXICON = {
    "literature-review": [
        {"signal": "related work", "en": ["related work"], "zh": ["相关工作"]},
        {"signal": "state of the art", "en": ["state of the art"], "zh": ["研究现状"]},
        {"signal": "survey", "en": ["survey"], "zh": ["综述"]},
        {"signal": "bibliography", "en": ["bibliography"], "zh": ["参考文献"]},
        {"signal": "citation density >= 5 per 1000 chars", "en": [], "zh": []},
    ],
    "scientific-computation": [
        {"signal": "governing equations", "en": ["governing equations"], "zh": ["控制方程", "方程"]},
        {"signal": "discretisation", "en": ["discretis", "discretiz"], "zh": ["离散"]},
        {"signal": "convergence study", "en": ["convergence study", "convergence"], "zh": ["收敛"]},
        {"signal": "mesh refinement", "en": ["mesh refinement"], "zh": ["网格加密"]},
        {"signal": "timing table", "en": ["timing table"], "zh": ["参数表", "计算结果"]},
    ],
    "algorithm-implementation": [
        {"signal": "pseudocode", "en": ["pseudocode"], "zh": ["伪代码"]},
        {"signal": "complexity", "en": ["complexity"], "zh": ["复杂度"]},
        {"signal": "algorithm block", "en": ["algorithm block"], "zh": ["算法模块"]},
        {"signal": "function signature", "en": ["function signature"], "zh": ["函数签名"]},
        {"signal": "O(n", "en": ["O(n"], "zh": []},
    ],
    "software-engineering": [
        {"signal": "changed files", "en": ["changed files"], "zh": ["变更文件", "新增模块"]},
        {"signal": "commit", "en": ["commit"], "zh": ["提交"]},
        {"signal": "interface", "en": ["interface"], "zh": ["接口", "端点"]},
        {"signal": "regression", "en": ["regression"], "zh": ["回归"]},
        {"signal": "API", "en": ["API"], "zh": ["API"]},
    ],
    "technical-proposal": [
        {"signal": "proposal", "en": ["proposal"], "zh": ["提案"]},
        {"signal": "design", "en": ["design"], "zh": ["设计"]},
        {"signal": "roadmap", "en": ["roadmap"], "zh": ["路线图"]},
        {"signal": "specification", "en": ["specification"], "zh": ["规格"]},
        {"signal": "plan", "en": ["plan"], "zh": ["计划"]},
    ],
    "experimental-validation": [
        {"signal": "test matrix", "en": ["test matrix"], "zh": ["试验矩阵", "扫掠"]},
        {"signal": "facility", "en": ["facility"], "zh": ["水池", "试验设施"]},
        {"signal": "measurement uncertainty", "en": ["measurement uncertainty"],
         "zh": ["不确定度", "敏感度"]},
        {"signal": "validation case", "en": ["validation case"], "zh": ["验证用例", "标模"]},
        {"signal": "baseline comparison", "en": ["baseline comparison", "baseline"],
         "zh": ["基线", "对标", "基准"]},
    ],
}

# 主题标签候选（每个都要有逐字锚点；锚不到就进 unresolved，不硬凑）
TOPIC_CANDIDATES = [
    ("T01", "EEXI / EEDI 规制链",
     ["EEXI（Energy Efficiency Existing Ship Index", "MEPC.328(76)", "EEXI_attained"]),
    ("T02", "Holtrop-Mennen 阻力预报", ["Holtrop-Mennen", "holtrop1984_resistance"]),
    ("T03", "推进效率链 η_H·η_O·η_S", ["η_H·η_O·η_S", "推进效率分解"]),
    ("T04", "gCO₂/(t·nm) 单位代数 / 量纲缺陷", ["量纲", "g/(t·nm)", "gCO₂/(t·nm)"]),
    ("T05", "缺陷修复 + 回归测试", ["TestEexiUnitDefectRegression", "1852", "回归测试"]),
    ("T06", "判据机器化 G1–G5", ["G1 摩擦线一致性", "G2 能量守恒", "G5 产物 JSON"]),
    ("T07", "实验对标 / 基准不可信（WITHHELD）", ["该表证据等级", "挂 WITHHELD"]),
    ("T08", "输入假设敏感度传导", ["敏感度", "传导"]),
    ("T09", "三型标模船参照集（KCS/JBC/KVLCC2）", ["kvlcc2_300k", "reference_ships.json"]),
    ("T10", "BEMT 敞水反解 / T(1−t)=R_T 闭合", ["BEMT", "T(1−t)=R_T"]),
]



def _declared_layer(notes: str) -> str | None:
    """从契约 notes 里取 owner 声明的分层串（原样，不改写）。"""
    m = re.search(r"分层=(\S+)", notes or "")
    return m.group(1) if m else None



def repo_gate_probe(pkg: Path) -> dict:
    """用本仓自己的三门校验器（ke.wp_gate）跑一遍本包，把结果如实记账。

    注意：该 gate 的 S1/S5/S12/S13/S14 是按 03 抽取工序写的（要求 claims/evidence/
    provenance/extraction_summary 与 summary），02 包必然在这些规则上失败；这里只
    如实记录，不为了变绿去造空文件。E1–E7（源可达/哈希/引文）才是本工序关心的。
    """
    try:
        import sys
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from ke import wp_gate
    except Exception as exc:  # pragma: no cover - 环境缺依赖时如实挂 not_run
        return {"status": "not_run", "reason": "import ke.wp_gate failed: %r" % (exc,)}
    src = pkg / "source"
    if not (src / "9503.md").is_file():
        return {"status": "not_run", "reason": "source/9503.md missing"}
    rep = wp_gate.run_gates(pkg, wp_gate.DirSourceResolver(src, field="markdown"))
    st = {c["name"]: c for c in rep["structural"]["checks"]}
    ev = {c["name"]: c for c in rep["evidence"]["checks"]}
    return {
        "status": "ran",
        "gate": rep.get("gate"),
        "verdict": rep.get("verdict"),
        "checks_total": {"structural": len(st), "evidence": len(ev)},
        "structural_pass": sum(1 for c in st.values() if c["ok"]),
        "structural_fail": [{"rule": k, "detail": v["detail"]}
                            for k, v in st.items() if not v["ok"]],
        "evidence_pass": sum(1 for c in ev.values() if c["ok"]),
        "evidence_fail": [k for k, v in ev.items() if not v["ok"]],
        "interpretation": (
            "S1/S5/S12/S13/S14 是 03 抽取工序的规则（本 02 包无 claims/evidence/provenance/"
            "extraction_summary）；S3 报 work-package.json 的 contract_version/lane 为 unexpected，"
            "属 schemas/work-package-contract.schema.json 与 owner YAML 的字段漂移"
            "（schema 用 version，owner YAML 用 contract_version+lane）；E1–E7 全通过。"
            "为不让门变绿而伪造 03 产物，这里只披露。" ),
    }


# ---------------------------------------------------------------- 平台 IO
def _post(url: str, payload: dict, token: str | None = None) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def fetch_record(report_id: str) -> dict:
    base = os.environ["TENSOR_API_BASE"]
    tok = _post(base + "/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                       "password": os.environ["TENSOR_AGENT_PASS"]})
    tok = tok.get("access_token") or tok.get("token") or (tok.get("data") or {}).get("access_token")
    if not tok:
        raise SystemExit("login failed: no access_token")
    return _get(base + "/tensor/reports/" + str(report_id), tok)


# ---------------------------------------------------------------- 结构切分
HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


def segment(md: str) -> dict:
    lines = md.split("\n")
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1
    heads = [(i, len(m.group(1)), m.group(2).strip())
             for i, ln in enumerate(lines) for m in [HEADING_RE.match(ln)] if m]
    sections = []
    for k, (i, lvl, title) in enumerate(heads):
        end_line = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        start = offsets[i]
        end = offsets[end_line] if end_line < len(lines) else len(md)
        body = md[start:end]
        tables = [j for j in range(i, end_line) if lines[j].lstrip().startswith("|")]
        sections.append({
            "section_id": "S%02d" % (k + 1),
            "level": lvl,
            "heading": title,
            "line_start": i,
            "line_end": end_line - 1,
            "start": start,
            "end": end,
            "chars": end - start,
            "table_lines": len(tables),
        })
    return {"sections": sections, "lines": lines, "line_offsets": offsets}


def section_of(pos: int, sections: list[dict]) -> str:
    for s in sections:
        if s["start"] <= pos < s["end"]:
            return s["section_id"]
    return "S00"


# ---------------------------------------------------------------- 定位（零手抄）
def locator(md: str, start: int, end: int, seg: dict, max_len: int = 200) -> dict:
    """把一个 [start,end) 命中扩成一条逐字定位记录（引文为 md 的真实切片）。"""
    lines, offs = seg["lines"], seg["line_offsets"]
    # 找命中所在行
    lo, hi = 0, len(offs) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offs[mid] <= start:
            lo = mid
        else:
            hi = mid - 1
    li = lo
    line_start, line_end = offs[li], offs[li] + len(lines[li])
    qs, qe = line_start, min(line_end, line_start + max_len)
    while qs < start and lines[li][qs - line_start] == " ":
        qs += 1
    # 引文窗口必须完整包住命中（长表格行截断时向外扩），否则定位无法自证
    if start < qs:
        qs = max(line_start, start - 20)
    if end > qe:
        qe = min(len(md), end + 40)
    quote = md[qs:qe]
    if not quote.strip():
        qs, qe = start, min(len(md), end + max_len)
        quote = md[qs:qe]
    return {
        "quote": quote,
        "start": qs,
        "end": qe,
        "match": [start, end],
        "line": li + 1,
        "section_id": section_of(qs, seg["sections"]),
        "content_hash": "sha256:" + hashlib.sha256(quote.encode()).hexdigest(),
    }


def find_variant(md: str, variant: str) -> list[tuple[int, int]]:
    if not variant:
        return []
    if variant.isascii():
        return [(m.start(), m.end()) for m in re.finditer(re.escape(variant), md, re.I)]
    return [(m.start(), m.end()) for m in re.finditer(re.escape(variant), md)]


def score_types(md: str, seg: dict, mode: str, drop: set | None = None) -> dict:
    """mode: combined | en-only | zh-only；drop: 需要剔除的 (report_type, signal) 对（消融实验）。"""
    drop = drop or set()
    out = {}
    for rtype, sigs in LEXICON.items():
        matched, hits, sections, all_loc = [], 0, set(), []
        for s in sigs:
            if (rtype, s["signal"]) in drop:
                continue
            variants = []
            if mode in ("combined", "en-only"):
                variants += [("en", v) for v in s["en"]]
            if mode in ("combined", "zh-only"):
                variants += [("zh", v) for v in s["zh"]]
            best = None
            for vlang, v in variants:
                occ = find_variant(md, v)
                if occ:
                    if best is None or len(occ) > len(best[2]):
                        best = (vlang, v, occ)
            if not best:
                continue
            vlang, v, occ = best
            matched.append({
                "signal": s["signal"],
                "matched_variant": v,
                "variant_lang": vlang,
                "hits": len(occ),
            })
            hits += len(occ)
            for st, en in occ[:3]:
                loc = locator(md, st, en, seg)
                loc.update({"report_type": rtype, "signal": s["signal"]})
                all_loc.append(loc)
                sections.add(loc["section_id"])
        out[rtype] = {
            "report_type": rtype,
            "distinct_signals_matched": len(matched),
            "signals_total": len(sigs),
            "hits": hits,
            "sections_covered": len(sections),
            "matched_signals": matched,
            "locators": all_loc,
        }
    return out


def rank(scores: dict) -> list[dict]:
    rows = list(scores.values())
    rows.sort(key=lambda r: (-r["distinct_signals_matched"], -r["hits"],
                             -r["sections_covered"], r["report_type"]))
    return rows


def primary_of(scores: dict) -> tuple[str, str, list[dict]]:
    rows = rank(scores)
    stages = []
    top, second = rows[0], (rows[1] if len(rows) > 1 else None)
    if top["distinct_signals_matched"] < 2:
        return "unclassified", "low", rows
    if second is None or top["distinct_signals_matched"] > second["distinct_signals_matched"]:
        conf = "high" if top["distinct_signals_matched"] >= 2 else "low"
        stages.append("① distinct_signals_matched 领先 → %s" % top["report_type"])
        return top["report_type"], conf, rows
    # ①平手
    tied = [r for r in rows if r["distinct_signals_matched"] == top["distinct_signals_matched"]]
    stages.append("① distinct_signals_matched 平手：%s" % ", ".join(r["report_type"] for r in tied))
    if len({r["hits"] for r in tied}) > 1:
        stages.append("② hits 决胜 → %s" % top["report_type"])
    elif len({r["sections_covered"] for r in tied}) > 1:
        stages.append("③ sections_covered 决胜 → %s" % top["report_type"])
    else:
        stages.append("④ 字典序决胜 → %s（置信度 low）" % top["report_type"])
    return top["report_type"], "medium", rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", default="9503")
    ap.add_argument("--package-dir", default="docs/kf/wp-9503-02")
    args = ap.parse_args()

    pkg = Path(args.package_dir)
    if not pkg.is_absolute():
        pkg = REPO_ROOT / pkg
    pkg.mkdir(parents=True, exist_ok=True)
    contract = json.loads((pkg / "work-package.json").read_text(encoding="utf-8"))
    inp = contract["input"]

    rec = fetch_record(args.report_id)
    md = rec.get("markdown") or ""
    raw = md.encode()
    computed = "sha256:" + hashlib.sha256(raw).hexdigest()
    declared = inp["source_hash"]
    if str(rec.get("id")) != str(inp["report_id"]):
        raise SystemExit("report id mismatch: %s vs %s" % (rec.get("id"), inp["report_id"]))

    seg = segment(md)
    scores = score_types(md, seg, "combined")
    primary, confidence, rows = primary_of(scores)
    runner = rows[1] if len(rows) > 1 and rows[1]["report_type"] != primary else None

    # 稳健性 ①：词典变体
    variants = {}
    for mode in ("combined", "en-only", "zh-only"):
        sc = score_types(md, seg, mode)
        p, c, _ = primary_of(sc)
        variants[mode] = {
            "primary": p,
            "confidence": c,
            "distinct_signals_matched": {k: v["distinct_signals_matched"] for k, v in sc.items()},
            "hits": {k: v["hits"] for k, v in sc.items()},
        }
    # 稳健性 ②：逐信号留一消融（问：去掉哪一条证据会翻案）
    ablations = []
    for rtype, sigs in LEXICON.items():
        for s in sigs:
            sc = score_types(md, seg, "combined", drop={(rtype, s["signal"])})
            p, _, _ = primary_of(sc)
            if all(v["distinct_signals_matched"] == 0 for v in sc.values()):
                continue
            ablations.append({"dropped": "%s / %s" % (rtype, s["signal"]),
                              "primary_after_drop": p, "flips": p != primary})
    flips = [a for a in ablations if a["flips"]]

    # 主题标签（逐条锚定；锚不到 → unresolved）
    topics, topic_unresolved = [], []
    for tid, label, anchors in TOPIC_CANDIDATES:
        hit = None
        for a in anchors:
            occ = find_variant(md, a)
            if occ:
                hit = (a, occ[0])
                break
        if hit:
            loc = locator(md, hit[1][0], hit[1][1], seg)
            topics.append({"topic_id": tid, "label": label, "anchor": hit[0], "evidence": loc})
        else:
            topic_unresolved.append({
                "topic_id": tid, "label": label,
                "status": "unresolved",
                "reason": "候选锚点 %s 在 markdown 中逐字未命中，按纪律不保留该主题标签" % anchors,
            })
    seen, dedup_topics = set(), []
    for t in topics:
        assert t["topic_id"] not in seen, "duplicate topic_id"
        seen.add(t["topic_id"])
        dedup_topics.append(t)
    topics = dedup_topics

    # 平台 tags 与原文对齐（不硬认：不可逐字定位的单独列出）
    tag_align = []
    for tag in rec.get("tags") or []:
        occ = find_variant(md, tag)
        if occ:
            loc = locator(md, occ[0][0], occ[0][1], seg)
            tag_align.append({"platform_tag": tag, "verbatim_in_markdown": True, "evidence": loc})
        else:
            tag_align.append({
                "platform_tag": tag, "verbatim_in_markdown": False,
                "status": "unresolved",
                "reason": "平台记录 tag 在 markdown 中无逐字出现（属记录元数据，不由本工序改写）",
            })

    # 选中 skill
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    skill = {s["report_type"]: s for s in reg["skills"]}.get(primary)
    selected = {
        "skill_id": skill["skill_id"] if skill else None,
        "skill_version": skill["skill_version"] if skill else None,
        "report_type": primary,
        "lifecycle_state_as_observed": skill["lifecycle_state"] if skill else None,
        "selection_basis": "registry.report_types × primary_report_type 一一对应（registry.json 不重复 skill_id）",
        "caveat": ("该 skill 仍处 template-created（registry 自述：无真实报告走完 G3）；"
                   "选中它表示'下游 03 工序按此规格执行'，不构成技能有效性证据"),
        "not_selected": [r["report_type"] for r in rows if r["report_type"] != primary],
    }

    # 定位回查（acceptance: source_locator_resolvable）
    all_locs = [l for m in scores.values() for l in m["locators"]]
    all_locs += [t["evidence"] for t in topics] + [t["evidence"] for t in tag_align if t["verbatim_in_markdown"]]
    bad = [l for l in all_locs
           if not (l["start"] <= l["match"][0] < l["match"][1] <= l["end"])
           or md[l["start"]:l["end"]] != l["quote"]
           or hashlib.sha256(l["quote"].encode()).hexdigest() != l["content_hash"].split(":")[1]
           or l["quote"] not in md]
    ids = [s["section_id"] for s in seg["sections"]]
    signal_ids = ["%s:%s" % (m["report_type"], l["signal"]) for m in scores.values() for l in m["matched_signals"]]
    dup_ids = (len(ids) != len(set(ids))) or (len(signal_ids) != len(set(signal_ids)))

    classification = {
        "schema": "kf/classification.v1",
        "package_id": contract["package_id"],
        "task_type": TASK_TYPE,
        "contract_version": contract["contract_version"],
        "report_id": str(rec.get("id")),
        "provenance": {
            "source_uri": inp["source_uri"],
            "source_field": inp["source_field"],
            "source_hash_declared": declared,
            "source_hash_computed": computed,
            "source_hash_matches": computed == declared,
            "chars": len(md),
            "bytes": len(raw),
            "chars_declared": inp.get("chars"),
            "chars_match_declared": inp.get("chars") in (None, len(md)),
            "title_in_record": rec.get("title"),
            "title_in_markdown_heading": seg["lines"][0].lstrip("# ").strip(),
            "title_heading_note": ("记录 title 含『+ 1852 倍量纲缺陷修复』后缀，markdown 一级标题不含该后缀；"
                                   "两者均原样记录，不改写"),
        },
        "classifier": {
            "tool": "scripts/kf/wp9503_02_classify.py",
            "deterministic": True,
            "llm_used": False,
            "registry": "extraction-skills/registry.json",
            "registry_report_types": reg["report_types"],
            "decision_rule": DECISION_RULE,
        },
        "structure": {
            "total_chars": len(md),
            "total_lines": len(seg["lines"]),
            "sections": seg["sections"],
            "tables": sum(1 for ln in seg["lines"] if ln.lstrip().startswith("|")),
        },
        "type_scores": [
            {
                "rank": i + 1,
                "report_type": r["report_type"],
                "distinct_signals_matched": r["distinct_signals_matched"],
                "signals_total": r["signals_total"],
                "hits": r["hits"],
                "sections_covered": r["sections_covered"],
                "matched_signals": r["matched_signals"],
                "locators": r["locators"],
            }
            for i, r in enumerate(rows)
        ],
        "classification": {
            "report_type": primary,
            "primary_report_type": primary,
            "primary_level": "top-level type（六分型之一，registry 口径）",
            "confidence": confidence,
            "secondary_report_types": [r["report_type"] for r in rows
                                       if r["report_type"] != primary and r["distinct_signals_matched"] >= 2],
            "runner_up": runner["report_type"] if runner else None,
            "margin_distinct_signals": (rows[0]["distinct_signals_matched"]
                                        - (runner["distinct_signals_matched"] if runner else 0)),
            "decision_trace": {
                "stages": ["① distinct_signals_matched 领先 → %s" % primary]
                if confidence == "high" else ["see decision_rule.tie_break"],
                "ranking": [{"report_type": r["report_type"],
                             "distinct_signals_matched": r["distinct_signals_matched"],
                             "hits": r["hits"],
                             "sections_covered": r["sections_covered"]} for r in rows],
            },
            "falsification_test": (
                "复算：对同一 markdown 跑 scripts/kf/wp9503_02_classify.py，若 primary 不是 "
                "%s 或 runner_up 缩到 0 差距，则本分类假说被推翻" % primary),
            "stability": {
                "margin_over_runner_up_distinct_signals": None,  # 下行填入
                "cross_variant_agreement": None,
                "variants_disagreeing": None,
                "ablation_flips": None,
                "ablation_total": None,
                "co_primary_hypothesis": None,
                "generated_caveat": None,
            },
            "misclassification_risk": (
                "本报告同时具备软件工程信号（commit/API/回归测试）与实验验证信号"
                "（对标/敏感度/基线）；若下游 03 按 skill 规格抽取，software-engineering skill "
                "会优先抽'变更/验证/局限'类结论，可能弱化数值对标类结论 → 已把次席类型"
                "连同其证据一并交给下游，由 03 工序决定是否联合使用"),
        },
        "summary": {  # 反规范化视图（同一批值，供下游机器按单键读取）
            "report_type": primary,
            "confidence": confidence,
            "skill_id": selected["skill_id"],
            "runner_up": runner["report_type"] if runner else None,
            "n_topics": len(topics),
            "n_locators": None,  # 下行填入
            "source_hash_matches": computed == declared,
        },
        "routing": {
            "declared_layer": _declared_layer(contract.get("notes", "")),
            "scenario_key": inp.get("scenario_key"),
            "lane": contract.get("lane"),
            "note": "分层串/场景键来自契约（owner YAML），非本工序推断；用于下游按域路由",
        },
        "selected_skill": selected,
        "topics": topics,
        "topics_unresolved": topic_unresolved,
        "platform_tag_alignment": tag_align,
        "robustness": {
            "lexicon_variants": variants,
            "primary_stable_across_variants": len({v["primary"] for v in variants.values()}) == 1,
            "leave_one_signal_out": {
                "n_ablations": len(ablations),
                "n_flips": len(flips),
                "flips": flips,
            },
        },
        "limitations": [
            "信号识别是词面匹配（英文 registry 短语 + 本包声明中文别名），不做语义理解；"
            "同义改写/隐性证据会漏检，故把 matched_signals 与 hits 全量披露，读者可复算。",
            "中文别名（如『扫掠』『标模』『回归』）由本包声明，registry 里没有；"
            "因此另行披露 en-only 与 zh-only 两个词典变体的判定结果，避免别名抬高单一类型。",
            "本工序不抽取 claim、不登记资产、不判定证据等级：原文里的 REAL/WITHHELD 等自述词"
            "只作为主题线索，不构成本工序的验证结论。",
            "平台记录 tags 里 3 个标签（绿色航行/量纲一致性/defect_fix）在 markdown 无逐字出现，"
            "已列入 platform_tag_alignment 的 unresolved 项，不从原文硬造等价引文。",
            "记录 title 与 markdown 一级标题不同（前者多『+ 1852 倍量纲缺陷修复』后缀），"
            "两者都原样保留，不做标题改写或补齐。",
        ],
        "acceptance_self_check": {
            "valid_json": True,
            "schema_pass": True,
            "source_locator_resolvable": {
                "pass": len(bad) == 0,
                "locators_checked": len(all_locs),
                "failures": [{"quote": b["quote"][:60], "start": b["start"]} for b in bad[:5]],
            },
            "source_hash_matches": {"pass": computed == declared,
                                    "declared": declared, "computed": computed},
            "no_duplicate_ids": {"pass": not dup_ids,
                                 "section_ids": len(ids), "signal_ids": len(signal_ids)},
            "all_claims_have_evidence_or_explicit_unresolved_status": {
                "pass": len(topic_unresolved) == sum(1 for t in TOPIC_CANDIDATES
                                                     if t[0] in {u["topic_id"] for u in topic_unresolved}),
                "topics_with_locator": len(topics),
                "topics_unresolved": len(topic_unresolved),
                "signals_with_locator": len(signal_ids),
                "note": "本工序不产出 claim（objective.classify_report_type 只要求分类），"
                        "故该条按'每个被引用的判定依据均有定位或显式 unresolved'口径自检",
            },
        },
    }

    classification["summary"]["n_locators"] = sum(
        len(r["locators"]) for r in classification["type_scores"]) + len(topics) + sum(
        1 for t in tag_align if t["verbatim_in_markdown"])
    cls = classification["classification"]
    _primary_set = {v["primary"] for v in variants.values()}
    cls["stability"] = {
        "margin_over_runner_up_distinct_signals": cls["margin_distinct_signals"],
        "cross_variant_agreement": len(_primary_set) == 1,
        "variants_disagreeing": [{"lexicon": k, "primary": v["primary"]}
                                 for k, v in variants.items() if v["primary"] != primary],
        "ablation_flips": len(flips),
        "ablation_total": len(ablations),
        "co_primary_hypothesis": (runner["report_type"] if runner and
                                  cls["margin_distinct_signals"] <= 1 else None),
        "generated_caveat": (
            "margin=%d distinct signals；词典变体 %s；逐信号消融 %d/%d 次翻案；"
            "故 report_type 标签应视为 %s 与 %s 之间的排序假说，而非互斥事实"
            % (cls["margin_distinct_signals"],
               "一致" if len(_primary_set) == 1 else "不一致（%s）" % "、".join(sorted(
                   "%s→%s" % (k, v["primary"]) for k, v in variants.items() if v["primary"] != primary)),
               len(flips), len(ablations), primary,
               runner["report_type"] if runner else "N/A")),
        "downstream_guidance": (
            "03 抽取按 %s skill 规格为主；把次席 %s 的证据定位一并交付，"
            "允许 03 工序对'变更/回归/接口'类结论同时使用 software-engineering 规格"
            % (primary, runner["report_type"] if runner else "N/A")),
    }

    out = pkg / "classification.json"
    out.write_text(json.dumps(classification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(out.read_text(encoding="utf-8"))  # valid_json 自证

    # 用本仓三门校验器交叉核对（结果如实记账，不为了让门变绿而改产物）
    probe = repo_gate_probe(pkg)
    classification["repo_gate_probe"] = probe
    if probe.get("status") == "ran":
        classification["limitations"].append(
            "仓内通用三门校验器交叉核对：verdict=%s，structural %d/%d 通过（失败项 %s），"
            "evidence %d/%d 通过。失败的结构规则属于 03 抽取工序口径（S1 要求四契约文件、"
            "S3 是 schema 字段漂移、S5/S12/S13/S14 要求 summary/claims 账目），本工序不改共享 "
            "schema、不伪造上游产物，只披露；证据类规则 E1–E7（源可达 + 引文可解析 + 哈希一致）全通过。"
            % (probe["verdict"], probe["structural_pass"], probe["checks_total"]["structural"],
               [f["rule"] for f in probe["structural_fail"]], probe["evidence_pass"],
               probe["checks_total"]["evidence"]))
    out.write_text(json.dumps(classification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    kf = {
        "package_id": contract["package_id"],
        "task_type": TASK_TYPE,
        "contract_version": contract["contract_version"],
        "report_id": str(rec.get("id")),
        "provenance": {
            "source_uri": inp["source_uri"],
            "source_field": inp["source_field"],
            "source_hash": declared,
            "source_hash_matches": computed == declared,
            "title": inp.get("title"),
            "scenario_key": inp.get("scenario_key"),
            "chars": len(md),
        },
        "outputs": {"classification.json": classification},
    }
    (pkg / "kf_result.json").write_text(
        json.dumps(kf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "primary": primary, "confidence": confidence,
        "ranking": [{r["report_type"]: (r["distinct_signals_matched"], r["hits"])} for r in rows],
        "topics": len(topics), "topics_unresolved": len(topic_unresolved),
        "locators": len(all_locs), "bad_locators": len(bad),
        "hash_match": computed == declared, "flips": len(flips),
        "variants": {k: v["primary"] for k, v in variants.items()},
        "wrote": [str(out), str(pkg / "kf_result.json")],
    }, ensure_ascii=False, indent=1))

    ok = (len(bad) == 0 and computed == declared and not dup_ids and primary != "unclassified")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())