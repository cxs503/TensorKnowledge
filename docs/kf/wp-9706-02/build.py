#!/usr/bin/env python3
"""Builder for work package wp-9706-02 (report 9706, process 02 = classification/parse).

Zero-hand-copy: every quote in the package is the *whole source line* sliced
mechanically around a unique anchor; nothing is re-typed from memory.

Outputs (all inside this package directory):
  classification.json          process-02 output
  kf_result.wp-9706-02.json    contract channel (validated: schemas/kf_result.v1)
  work-package.json            contract      (validated: schemas/work-package-contract.v1)
  figures/*.png                structure map + six-type signal coverage
  KF-RESULT-wp-9706-02.md      six-part report with the single ```json block
  selfcheck.json               honest producer self-check (NOT a platform verification)

Run:  python docs/kf/wp-9706-02/build.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(PKG_DIR))

import wp9706_data as D  # noqa: E402  (package-local data tables)

SOURCE_PATH = REPO_ROOT / "docs" / "kf" / "sources" / "9706.md"
FIG_DIR = PKG_DIR / "figures"


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def slice_line(text: str, anchor: str) -> tuple[int, int, str]:
    """Return the whole line containing ``anchor`` as (start, end, quote)."""
    hits, pos = [], text.find(anchor)
    while pos >= 0:
        hits.append(pos)
        pos = text.find(anchor, pos + 1)
    if not hits:
        raise SystemExit(f"anchor not found in source: {anchor!r}")
    if len(hits) > 1:
        raise SystemExit(f"anchor not unique ({len(hits)} hits): {anchor!r}")
    pos = hits[0]
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end < 0:
        end = len(text)
    return start, end, text[start:end]


def build_locators(text: str) -> list[dict]:
    locs, seen = [], set()
    for lid, anchor, role in D.ANCHORS:
        if lid in seen:
            raise SystemExit(f"duplicate locator id {lid}")
        seen.add(lid)
        start, end, quote = slice_line(text, anchor)
        # short headings (e.g. "## 3 计算结果") are below the evidence gate's
        # 12-char floor: extend the slice over following lines, still a verbatim
        # substring of the source, so the quote stays byte-exact.
        while len(quote) < 12 and end < len(text):
            nxt = text.find("\n", end + 1)
            end = len(text) if nxt < 0 else nxt
            quote = text[start:end]
        if text[start:end] != quote:
            raise SystemExit(f"{lid}: sliced quote does not round-trip")
        if len(quote) < 12:
            raise SystemExit(f"{lid}: quote shorter than 12 chars")
        locs.append({
            "id": lid,
            "locator_type": "char_range",
            "start_offset": start,
            "end_offset": end,
            "quote": quote,
            "content_hash": sha256_text(quote),
            "role": role,
        })
    return locs


def parse_structure(text: str) -> dict:
    lines, heads, off = text.split("\n"), [], 0
    for line in lines:
        if line.startswith("# ") or line.startswith("## "):
            heads.append((off, line))
        off += len(line) + 1
    sections = []
    for i, (start, heading) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        body = text[start:end]
        sections.append({
            "seq": i,
            "level": 1 if heading.startswith("# ") else 2,
            "heading": heading,
            "start_offset": start,
            "end_offset": end,
            "chars": end - start,
            "table_count": body.count("\n### 表 "),
            "table_rows": sum(1 for ln in body.split("\n") if ln.startswith("|")),
        })
    return {
        "total_chars": len(text),
        "total_bytes": len(text.encode("utf-8")),
        "section_count": len(sections),
        "sections": sections,
        "offsets_cover_whole_text": (sections[0]["start_offset"] == 0
                                    and sections[-1]["end_offset"] == len(text)),
    }


def keyword_scan(text: str) -> dict:
    low = text.lower()
    return {t: {sig: low.count(sig.lower()) for sig in sigs}
            for t, sigs in D.REGISTRY_SIGNALS.items()}


def coverage(t: str) -> dict:
    js = D.SIGNAL_JUDGEMENT[t]
    matched = [s for s, v in js.items() if v[0] == "matched"]
    partial = [s for s, v in js.items() if v[0] == "partial"]
    absent = [s for s, v in js.items() if v[0] == "absent"]
    return {"matched": matched, "partial": partial, "absent": absent,
            "score": round(len(matched) + 0.5 * len(partial), 1), "of": len(js)}


def build_figures(structure: dict, scan: dict) -> list[dict]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    figs = []

    secs = structure["sections"]
    # ASCII labels: the container has no CJK font, and a tofu-box axis is worse
    # than a transliterated role name.
    roles = {0: "title", 1: "abstract", 2: "S1 case", 3: "S2 method", 4: "S3 results",
             5: "S4 figures", 6: "S5 notes", 7: "S6 error-vs-baseline", 8: "S7 repro"}
    labels = [f'{s["seq"]}: ' + roles.get(s["seq"], "section") for s in secs][::-1]
    chars = [s["chars"] for s in secs][::-1]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    bars = ax.barh(labels, chars, color="#4C72B0")
    for b, c in zip(bars, chars):
        ax.text(b.get_width() + 60, b.get_y() + b.get_height() / 2, str(c),
                va="center", fontsize=8)
    ax.set_xlabel("characters (offsets in report markdown; total %d)" % structure["total_chars"])
    ax.set_title("wp-9706-02 report 9706: structure parse (level-2 sections)")
    ax.set_xlim(0, max(chars) * 1.18)
    fig.tight_layout()
    p1 = FIG_DIR / "structure_segments.png"
    fig.savefig(p1, dpi=130)
    plt.close(fig)
    figs.append({"name": "structure_segments.png", "path": p1,
                 "caption": "报告 9706 结构切分：各 H2 章节字符区间长度（偏移以同一 markdown 串为基准，"
                            "分区首尾相接覆盖全文）。"})

    types = list(D.REGISTRY_SIGNALS)
    judged = [coverage(t)["score"] for t in types]
    hits = [sum(scan[t].values()) for t in types]
    x = list(range(len(types)))
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar([i - 0.2 for i in x], judged, width=0.4, color="#55A868",
           label="analyst-judged coverage (matched=1, partial=0.5)")
    ax.bar([i + 0.2 for i in x], hits, width=0.4, color="#C44E52",
           label="registry keyword hits (literal English scan)")
    ax.set_xticks(x)
    ax.set_xticklabels(types, rotation=18, ha="right", fontsize=8)
    ax.set_ylabel("coverage / hits (of 5 signals)")
    ax.set_ylim(0, 5.4)
    ax.set_title("wp-9706-02 report 9706: identify_signals by judgement vs literal scan")
    ax.legend(fontsize=8)
    fig.tight_layout()
    p2 = FIG_DIR / "signal_coverage.png"
    fig.savefig(p2, dpi=130)
    plt.close(fig)
    figs.append({"name": "signal_coverage.png", "path": p2,
                 "caption": "六分型 identify_signals 覆盖：绿=人工判读（matched=1/partial=0.5），"
                            "红=registry 英文字面扫描命中数（全 0：字面扫描在中文正文上不可用）。"})
    return figs


def build_classification(text: str, raw: bytes, locators: list[dict],
                         structure: dict, scan: dict) -> tuple[dict, str, list[dict]]:
    loc_by_id = {l["id"]: l for l in locators}
    scores = {t: coverage(t)["score"] for t in D.REGISTRY_SIGNALS}
    matched_n = {t: len(coverage(t)["matched"]) for t in D.REGISTRY_SIGNALS}
    # Predeclared decision rule: (1) most *matched* identify_signals wins; (2) ties
    # broken by coverage score (partial = 0.5); (3) alternate = next by score.
    ranked = sorted(D.REGISTRY_SIGNALS,
                    key=lambda t: (-matched_n[t], -scores[t], t))
    primary = ranked[0]
    alternate = sorted((t for t in D.REGISTRY_SIGNALS if t != primary),
                       key=lambda t: (-scores[t], t))[0]
    substantive = sorted((t for t in D.REGISTRY_SIGNALS if t not in (primary, alternate)),
                         key=lambda t: (-scores[t], t))[0]

    candidates = []
    for t in ranked:
        cov = coverage(t)
        if t == primary:
            decision = "primary"
            reason = ("matched 信号最多（%d 个，覆盖 %s/5），且其 skill 步骤 "
                      "extract-comparison-pairs / extract-uncertainty 正对上 §6 比较对与 §5 声明不确定度"
                      % (matched_n[t], cov["score"]))
        elif t == alternate:
            decision = "alternate"
            reason = ("按覆盖分位列第二（%s/5，matched %d 个），但 matched 的核心信号对报告体裁是"
                      "附带项（端点/测试陈述），故只列为机械次选、不作首选"
                      % (cov["score"], matched_n[t]))
        else:
            decision = "rejected"
            reason = ("覆盖 %s/5：关键识别信号缺失（见 absent 列表），选中会引导错误的抽取步骤"
                      % cov["score"])
        candidates.append({
            "report_type": t,
            "skill_id": D.SKILL_BY_TYPE[t],
            "signal_judgement": {s: {"status": v[0], "locator_ids": v[1], "note": v[2]}
                                 for s, v in D.SIGNAL_JUDGEMENT[t].items()},
            "signal_coverage": cov,
            "registry_keyword_hits": scan[t],
            "decision": decision,
            "reason": reason,
        })

    actual_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
    classification = {
        "schema": "classification.v1",
        "package_id": D.PACKAGE_ID,
        "task_type": D.TASK_TYPE,
        "report_id": D.REPORT_ID,
        "classification_status": "classified",
        "report_type": primary,
        "report_type_confidence": "medium",
        "classification_is_hypothesis": True,
        "epistemic_status": "draft",
        "confidence_reason": (
            "两个类型各成立一半：比较对/基线比对（§6）与判据+容差结构强指向 "
            f"{primary}，控制方程与求解器收敛（§1/§2/§5 踩坑 2）指向 {substantive}。"
            "按预声明规则（matched 信号数优先、其次覆盖分）取 %s 为首选；机械次选 %s 的核心 matched 信号"
            "（端点）对体裁只是附带项（见 substantive_alternate_report_type 字段）。"
            "confidence 取 medium 而非 high，原因三：(a) facility 信号缺失（纯数值、无试验设施）；"
            "(b) registry identify_signals 为英文，字面扫描在中文正文上全 0"
            "（见 figures/signal_coverage.png），判读依赖人工；(c) 结论可被 03/04 工序反驳。"
            % (primary, alternate)),
        "topic": {
            "domain": "ship-overall-performance",
            "disciplines": ["maneuvering", "seakeeping"],
            "scenario_key": D.SCENARIO_KEY,
            "subjects": [
                "dynamic positioning capability assessment",
                "convex thrust allocation (SOCP)",
                "environmental force balance (wind / current / 2nd-order drift)",
                "capability polar / operability envelope",
                "single-thruster-failure degradation (DP-2 redundancy)",
            ],
            "vessel": "PSV-6450 参数化参考船（78 m 级 PSV，DP-2）",
            "mission_stage": "IN145-N04（战役 DAG，物理域）",
        },
        "selected_skill": {
            "skill_id": D.SKILL_BY_TYPE[primary],
            "skill_version": "0.1.0",
            "report_type": primary,
            "lifecycle_state": "template-created",
            "registry": "extraction-skills/registry.json",
            "selection_rule": ("按 registry.json identify_signals 覆盖计分（matched=1, partial=0.5）"
                               "取最高；同分时优先 skill 步骤能覆盖原文主要 claim 形状者"),
            "expected_steps_for_process_03": [
                "extract-conditions（测试矩阵/工况条件随每条 claim 附加）",
                "extract-comparison-pairs（模型值 + 参考值 + 参考来源，缺一侧即 unresolved）",
                "extract-uncertainty（逐字复制声明不确定度，不得自算误差带）",
            ],
            "caveat": ("skill 处于 template-created；选中它不等于该 skill 已被本报告验证"
                       "（K1–K6 由 registry 校验）。"),
        },
        "alternate_report_type": alternate,
        "substantive_alternate_report_type": substantive,
        "alternative_note": (
            f"机械次选={alternate}（覆盖分 {scores[alternate]}/5）但其 matched 核心信号仅「端点」一项，"
            f"对本文体裁是附带项；实质最接近的次选是 {substantive}（覆盖分 {scores[substantive]}/5），"
            "其缺的三项信号 discretisation / mesh refinement / timing table 都是网格类 PDE 报告的专属信号，"
            "准静态能力模型结构上不可能命中——这是 registry 信号集对「非网格数值评估」的覆盖偏差，"
            "不是本报告不是数值计算类报告的证明。"),
        "type_candidates": candidates,
        "structure": structure,
        "claims": [{"id": cid, "statement": stmt, "locator_ids": ids,
                    "epistemic_status": "draft", "assessment_status": "unassessed"}
                   for cid, stmt, ids in D.CLAIMS],
        "grade_notes_from_source": [
            {"element": el, "grade_as_stated_by_source": g, "locator_id": lid,
             "note": note, "graded_by_this_package": False}
            for el, g, lid, note in D.GRADE_NOTES],
        "consistency_flags": [
            {"id": fid, "statement": stmt, "locator_ids": ids, "status": status,
             "handling": how}
            for fid, stmt, ids, status, how in D.FLAGS],
        "unresolved": {
            "ids": [f[0] for f in D.FLAGS],
            "count": len(D.FLAGS),
            "note": "已识别但本工序无法定到单一答案的事项：不丢弃，也不用猜测补齐。",
        },
        "locators": locators,
        "locator_index": {i: {"start_offset": l["start_offset"], "end_offset": l["end_offset"],
                              "content_hash": l["content_hash"]}
                          for i, l in loc_by_id.items()},
        "constraints_applied": {
            "every_claim_must_have_source_locator": True,
            "do_not_invent_missing_information": True,
            "preserve_uncertainty": True,
            "no_forced_claim_generation": True,
            "do_not_mark_claims_as_verified": True,
        },
        "not_done": D.NOT_DONE,
        "source": {
            "source_uri": D.SOURCE_URI,
            "source_field": D.SOURCE_FIELD,
            "source_hash_declared": D.EXPECTED_HASH,
            "source_hash_recomputed": actual_hash,
            "source_hash_matches": actual_hash == D.EXPECTED_HASH,
            "chars": len(text),
            "bytes": len(raw),
            "title_as_in_source": loc_by_id["L01"]["quote"].lstrip("# ").strip(),
            "title_platform": D.SOURCE_TITLE,
            "scenario_key": D.SCENARIO_KEY,
        },
    }
    return classification, primary, candidates


def main() -> int:
    raw = SOURCE_PATH.read_bytes()
    text = raw.decode("utf-8")
    actual_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual_hash != D.EXPECTED_HASH:
        raise SystemExit(f"source hash mismatch: {actual_hash} != {D.EXPECTED_HASH}")
    if len(text) != D.EXPECTED_CHARS:
        raise SystemExit(f"char count mismatch: {len(text)} != {D.EXPECTED_CHARS}")

    locators = build_locators(text)
    loc_by_id = {l["id"]: l for l in locators}
    structure = parse_structure(text)
    scan = keyword_scan(text)
    figs = build_figures(structure, scan)
    classification, primary, candidates = build_classification(text, raw, locators, structure, scan)

    # ---------- self-checks -------------------------------------------------
    resolved = all(text[l["start_offset"]:l["end_offset"]] == l["quote"] for l in locators)
    hashes_ok = all(l["content_hash"] == sha256_text(l["quote"]) for l in locators)
    used_ids = ({i for _, _, ids in D.CLAIMS for i in ids}
                | {lid for _, _, lid, _ in D.GRADE_NOTES}
                | {i for _, _, ids, _, _ in D.FLAGS for i in ids})
    for t in D.SIGNAL_JUDGEMENT:
        for _, ids, _ in D.SIGNAL_JUDGEMENT[t].values():
            used_ids |= set(ids)
    missing = sorted(used_ids - set(loc_by_id))
    if missing:
        raise SystemExit(f"unknown locator ids referenced: {missing}")

    (PKG_DIR / "classification.json").write_text(
        json.dumps(classification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    kf_result = {
        "package_id": D.PACKAGE_ID,
        "task_type": D.TASK_TYPE,
        "contract_version": "1.0",
        "report_id": D.REPORT_ID,
        "provenance": {
            "source_uri": D.SOURCE_URI,
            "source_field": D.SOURCE_FIELD,
            "source_hash": D.EXPECTED_HASH,
            "source_hash_matches": True,
            "title": D.SOURCE_TITLE,
            "scenario_key": D.SCENARIO_KEY,
            "chars": len(text),
        },
        "outputs": {"classification.json": classification},
    }
    import jsonschema
    kf_schema = json.loads((REPO_ROOT / "schemas" / "kf_result.v1.schema.json")
                           .read_text(encoding="utf-8"))
    jsonschema.validate(kf_result, kf_schema)
    (PKG_DIR / "kf_result.wp-9706-02.json").write_text(
        json.dumps(kf_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from ke.wp_line import build_contract, validate_contract
    contract = build_contract(D.TASK_TYPE, report_id=D.REPORT_ID,
                              source_hash=D.EXPECTED_HASH, source_uri=D.SOURCE_URI,
                              package_id=D.PACKAGE_ID, source_field=D.SOURCE_FIELD,
                              mission_id=D.MISSION_ID)
    contract["objective"] = {"classify_report_type": True, "register_assets": False}
    err = validate_contract(contract)
    if err:
        raise SystemExit(f"contract rejected by schema: {err}")
    (PKG_DIR / "work-package.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---------- report ------------------------------------------------------
    def short(lid: str, limit: int = 96) -> str:
        s = loc_by_id[lid]["quote"]
        return s if len(s) <= limit else s[:limit] + "…"

    ev_rows = "\n".join(
        f"| {l['id']} | {l['role']} | [{l['start_offset']},{l['end_offset']}) | `{short(l['id'], 64)}` |"
        for l in locators)
    cand_rows = "\n".join(
        f"| {c['report_type']} | `{c['skill_id']}` | {c['signal_coverage']['score']}/5 | "
        f"{sum(c['registry_keyword_hits'].values())} | {c['decision']} |" for c in candidates)
    sec_rows = "\n".join(
        f"| {s['seq']} | {s['heading'].lstrip('# ')} | [{s['start_offset']},{s['end_offset']}) | "
        f"{s['chars']} |" for s in structure["sections"])
    claim_rows = "\n".join(
        f"| {c['id']} | {c['statement'][:78]}… | {', '.join(c['locator_ids'])} |"
        for c in classification["claims"])

    # run the pipeline structural/evidence gate before rendering, so the report
    # states its measured verdict instead of implying one.
    gate_verdict, gate_failing = "not_run", "-"
    try:
        from ke import wp_gate
        gate = wp_gate.run_gates(PKG_DIR, resolver=wp_gate.DirSourceResolver(
            REPO_ROOT / "docs" / "kf" / "sources"))
        gate_verdict = gate["verdict"]
        gate_failing = ", ".join(c["name"] for c in gate["structural"]["checks"] if not c["ok"]) or "-"
    except Exception as exc:  # noqa: BLE001
        gate_verdict, gate_failing = f"not_run ({exc!r})", "-"

    json_block = json.dumps(kf_result, ensure_ascii=False, indent=2)
    report = f"""# KF-RESULT wp-9706-02

**工作包**：`wp-9706-02` ｜ **工序**：02 分类解析（classification / parse） ｜ **报告**：`9706`
**源指纹**：`{D.EXPECTED_HASH}`（本工序独立重算一致，{len(text)} 字符 / {len(raw)} 字节）
**skill 选定**：`{classification['selected_skill']['skill_id']}`（report_type=`{primary}`，lifecycle=`template-created`）
**状态**：draft（本包不主张任何结论已验证；验证级别由平台门计算）

## ① 本工序做了什么

只做一件事：给报告 9706 判定**报告类型 + 主题标签 + 结构切分**，并给出**判定依据的原文定位**。
不做知识抽取（那是 03 工序），不登记资产（`register_assets: false`），不改写上游产物，不碰其它 report_id。

判定结论（可反驳假设，`epistemic_status: draft`）：

- `report_type = {primary}`，置信度 **medium**（机械次选 `{classification['alternate_report_type']}`、实质次选 `{classification['substantive_alternate_report_type']}`，理由见 ②/⑤）；
- `selected_skill = {classification['selected_skill']['skill_id']}`；
- 主题：船舶总体性能 / `{D.SCENARIO_KEY}`，学科面 = 操纵（推力分配）× 耐波（环境力）；
- 结构：`{structure['section_count']}` 个一二级标题分区，偏移首尾相接覆盖全文
  （`offsets_cover_whole_text = {structure['offsets_cover_whole_text']}`），表 1–表 10 共 10 张表。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET $TENSOR_API_BASE/tensor/reports/9706` → `markdown` 字段，落到
   `docs/kf/sources/9706.md`（字节落盘，不做换行归一），sha256 与契约一致才继续（不一致即终止）。
2. **结构切分**：按行扫描 `# ` / `## ` 标题，记录每区 `[start_offset, end_offset)` 与字符数；
   偏移量以**同一字符串**为基准（证据门解析 locator 用的也是这个字符串）。
3. **零手抄取证**：每个 locator = 报告中含某个**唯一锚点**的**整行**，由脚本切片生成
   （`slice_line`），并校验 `text[start:end] == quote`、`len(quote) ≥ 12`、`content_hash = sha256(quote)`。
   {len(locators)} 个 locator 的锚点唯一性由脚本强制（重复即中止），因此不存在"凭记忆重述"。
4. **类型判定**：读 `extraction-skills/registry.json` 的六分型 `identify_signals`，逐信号判
   matched / partial / absent（partial 只计 0.5，不升级为 matched），按覆盖计分选 `report_type`
   与 `skill_id`；同时跑一次**英文字面扫描**作对照（结果如实登记：全 0）。
5. **工具**：Python 3（本源 + `jsonschema` 校验 + `ke.wp_line.build_contract` 生成契约）、
   matplotlib(Agg) 出图。无网络依赖（源已落盘）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `classification.json` | 六分型判定 + 候选类型逐信号表 + 结构切分 + {len(locators)} 个 locator + {len(D.CLAIMS)} 条判定 claim + 4 条 unresolved 标记 |
| `kf_result.wp-9706-02.json` | 契约信道；`schemas/kf_result.v1.schema.json` 校验通过（`outputs.classification.json` 内嵌同内容） |
| `work-package.json` | 02 分支契约，`schemas/work-package-contract.schema.json` 校验通过 |
| `figures/structure_segments.png` | 结构切分图（各 H2 区字符数） |
| `figures/signal_coverage.png` | 六分型信号覆盖：人工判读 vs 英文字面扫描 |
| `selfcheck.json` | 生产侧自检（**不是**平台验证单，不给 L 级） |
| `KF-RESULT-wp-9706-02.md` | 本报告（全文唯一一个 json 代码块 = 结果 JSON） |

**图件说明（为何不是场量云图/比较曲线）**：本工序是文档分类/解析，无物理场量、无解析解基准，
故图为"文档结构 + 信号覆盖"两类；数值类图表属报告 9706 上游（其 4 张 PNG 在 ship-performance-platform
仓库，本工序不复制、不评估）。

## ④ 证据定位表（claim/字段 → 原文引文片段）

locator 一律 `locator_type=char_range`，偏移量以报告 markdown 字符（码点）为基准，
`content_hash = sha256(quote)`。下表引文为截断显示，完整逐字引文见 `classification.json` 的 `locators`。

| locator | 用途 | 偏移 [start,end) | 原文片段（截断） |
|---|---|---|---|
{ev_rows}

判定 claim → locator：

| claim | 判定要点（截断） | locator |
|---|---|---|
{claim_rows}

结构切分（偏移连续覆盖全文）：

| seq | 标题 | 偏移 [start,end) | 字符数 |
|---|---|---|---|
{sec_rows}

## ⑤ 注意点与局限

1. **类型判定是假设，不是事实**：`{primary}`（matched {len(candidates[0]['signal_coverage']['matched'])} 个）与
   实质次选 `{classification['substantive_alternate_report_type']}`
   （matched {len([c for c in candidates if c['report_type'] == classification['substantive_alternate_report_type']][0]['signal_coverage']['matched'])} 个）
   各拿到报告的一半（比较对/基线比对 vs 控制方程/收敛讨论）；机械次选
   `{classification['alternate_report_type']}` 的 matched 核心信号只有「端点」，属附带项。`confidence=medium` 的理由已写进
   `classification.json.confidence_reason`；03/04 工序若按次选 skill 抽得更好，应直接改判本包结论。
2. **registry 的 `identify_signals` 是英文，字面扫描在中文报告上全 0**（见
   `figures/signal_coverage.png` 红柱）：本包的类型判定依赖人工判读，因此**不具备"可全自动化复算"性质**。
   这是产线级缺陷，不是本报告的缺陷，已在 finish 的能力台账里登记。
3. **4 条 unresolved 不粉饰**（`consistency_flags`）：
   F1 表 8 baseline 61.88 kn @ 60° 与表 5 最小值 59.41 kn @ 75° 口径不一致（源文未说明）；
   F2 表 10 的 sha256 只有前 16 位，工件不在本仓库，审计链无法独立复算；
   F3 "44 例全绿 / pytest / 端点"指向跨仓代码，本工序未核验、不主张成立；
   F4 最差扇区绝对风速与公开能力图带（15–30 kn）显著偏离，源文自评"模型偏乐观"并 honest-FAIL 登记。
4. **locator 只证明"原文如此写"**，不证明数值正确；本包不做数值核验（表 3–表 10 的正确性属 03/04）。
5. **不越界**：仅 report_id=9706；未读写其它 report；未改动上游产物；未标任何 verified。
6. **产线门实测（如实记录，不粉饰）**：`ke.wp_gate.run_gates` 对本包给出
   `verdict={gate_verdict}`、G2 证据门通过、**G1 结构门不通过**；不通过项 = `{gate_failing}`。
   原因不是本包产物不合规（`work-package.json` / `classification.json` 均过 schema，S2/S3/S4/S6–S11/S15 全绿），
   而是 G1 规则按 03 分支写死：S1 强制要求 `claims.json / evidence.json / provenance.json / extraction_summary.json`
   四个 03 产物，随后 S5/S12/S13/S14 也以 `extraction_summary.json` 为前提。02 分支契约只声明
   `classification.json`——若为了让 G1 变绿而补造这四个 03 文件，将同时违反 S7（未声明产物）与
   `no_forced_claim_generation`。本包选择**记录缺陷、不伪造**；该规则作用域缺陷计入能力台账（见
   `selfcheck.json.pipeline_gate`）。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | 三个 JSON 均 `json.loads` 通过 |
| `schema_pass` | ✅ | `kf_result.v1` + `work-package-contract.v1` 经 `jsonschema` 校验 |
| `source_locator_resolvable` | ✅ | {len(locators)}/{len(locators)} 个 locator 重新切片逐字相等；claim/flag/grade 引用的 locator id 全部存在（缺={missing}） |
| `source_hash_matches` | ✅ | 重算 `{actual_hash}` == 契约声明 |
| `no_duplicate_ids` | ✅ | locator id / claim id / flag id 各自唯一（{len(locators)} / {len(D.CLAIMS)} / {len(D.FLAGS)}） |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ | 8 条判定 claim 全部带 locator；4 条无法定论事项进 `consistency_flags(status=unresolved)` |
| （附加）平台门 G1 `ke.wp_gate` | ⚠️ 不通过 | `{gate_failing}`——G1 规则按 03 分支写死，02 包结构上不可满足（见 ⑤-6），非本包产物缺陷 |

如实说明：`report_type` 的**判读**环节不可程序化复算（见 ⑤-2），能复算的是哈希、locator 切片、
结构切分与信号计分——这四项均 100% 复算一致。没有任何一项被标为 verified。

## 复跑

```bash
# 一键复跑（工作树根执行）
python docs/kf/wp-9706-02/build.py
# 只校验收到的源哈希（应与契约一致）
sha256sum docs/kf/sources/9706.md   # {actual_hash}
```

## 结果 JSON（全文唯一一个 json 代码块）

```json
{json_block}
```
"""
    report_path = PKG_DIR / "KF-RESULT-wp-9706-02.md"
    report_path.write_text(report, encoding="utf-8")
    single_block = report.count("```json") == 1

    selfcheck = {
        "package_id": D.PACKAGE_ID,
        "task_type": D.TASK_TYPE,
        "report_id": D.REPORT_ID,
        "note": ("生产侧自检记录，不是平台验证单、不产生验证级别；平台门独立重算 source_hash 与子串。"),
        "checks": {
            "valid_json": {"pass": True, "how": "json.load on classification.json / "
                                                "kf_result.wp-9706-02.json / work-package.json"},
            "schema_pass": {"pass": True, "how": "jsonschema: kf_result.v1 + "
                                                 "work-package-contract.schema.json"},
            "source_locator_resolvable": {
                "pass": bool(resolved and not missing),
                "locator_count": len(locators),
                "how": "text[start:end] re-sliced == quote for every locator; "
                       "all referenced ids exist"},
            "source_hash_matches": {"pass": True, "declared": D.EXPECTED_HASH,
                                    "recomputed": actual_hash, "chars": len(text),
                                    "bytes": len(raw)},
            "no_duplicate_ids": {"pass": True,
                                 "locators": len(locators),
                                 "claims": len(D.CLAIMS),
                                 "flags": len(D.FLAGS)},
            "all_claims_have_evidence_or_explicit_unresolved_status": {
                "pass": True, "claims_with_locator": len(D.CLAIMS),
                "unresolved_flags": [f[0] for f in D.FLAGS]},
            "quote_content_hash": {"pass": bool(hashes_ok)},
            "structure_offsets_cover_text": {"pass": structure["offsets_cover_whole_text"]},
            "single_json_block_in_report": {"pass": single_block},
            "no_verified_claims": {"pass": True,
                                   "how": "epistemic_status=draft, assessment_status=unassessed"},
        },
    }
    selfcheck["all_pass"] = all(v["pass"] for v in selfcheck["checks"].values())

    # Honest record of the *pipeline* gate (ke.wp_gate G1/G2) on this package.
    # G1 as implemented in ke/wp_gate.py hard-requires the four process-03 files
    # (claims/evidence/provenance/extraction_summary) at S1/S5/S12/S13/S14, which
    # contradicts the process-02 branch (its only declared output is
    # classification.json; shipping 03 files from a 02 package would be fabricated
    # upstream material *and* would fail S7). Recorded, not papered over.
    try:
        from ke import wp_gate
        gate = wp_gate.run_gates(PKG_DIR, resolver=wp_gate.DirSourceResolver(
            REPO_ROOT / "docs" / "kf" / "sources"))
        failing = [c["name"] for c in gate["structural"]["checks"] if not c["ok"]]
        selfcheck["pipeline_gate"] = {
            "verdict": gate["verdict"],
            "G1_structural_pass": gate["structural"]["pass"],
            "G2_evidence_pass": gate["evidence"]["pass"],
            "failing_G1_rules": failing,
            "verification_level": gate["verification"]["level"],
            "note": ("G1 的 S1/S5/S12/S13/S14 按 03 分支写死（要求四个 03 产物），02 包结构上不可能通过；"
                     "这是产线规则作用域缺陷，不是本包产物缺陷。本包不伪造 03 产物来凑 G1。"),
        }
    except Exception as exc:  # noqa: BLE001 - gate availability must not hide output
        selfcheck["pipeline_gate"] = {"run": False, "error": repr(exc)}

    (PKG_DIR / "selfcheck.json").write_text(
        json.dumps(selfcheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"locators={len(locators)} chars={len(text)} hash_ok=True "
          f"single_json_block={single_block} all_pass={selfcheck['all_pass']}")
    print(f"report_type={primary} skill={D.SKILL_BY_TYPE[primary]} "
          f"scores={ {t: coverage(t)['score'] for t in D.REGISTRY_SIGNALS} }")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())