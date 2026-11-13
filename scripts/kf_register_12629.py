"""Register the source assets of report 12629 (work package wp-12629-01, task_type 01-asset-registration).

Design rules enforced here:
  * No hand transcription. Every ``quote`` is sliced out of the report markdown at run time; the
    slicing is driven by *structural* selectors (line numbers, in-line delimiters and keyword pickers
    that use field names such as ``rel_dev`` / ``coupled_maneuvering`` -- never literal numbers of the
    physics results). Each quote is re-checked to be a unique substring of the markdown before write.
  * Registration only. The contract sets objective.register_assets=true, classify_report_type=false,
    so ``claims`` is empty by design (filling it would fabricate task_type-03 knowledge objects).
  * Nothing is marked verified. ``resolution`` only says whether a locator resolves; verification of
    the underlying physics claims is the platform gate's job.
  * Missing/unresolvable things stay visible: an item that cannot be resolved is recorded as
    referenced_unresolved / declared_absent with the check that produced that verdict.

Inputs (produced by scripts/kf_fetch_12629.py):
  runs/wp-12629-01/report_12629.md    (markdown payload)
  runs/wp-12629-01/report_12629.json  (raw API payload: id/title/scenario_key/figures/...)

Outputs:
  artifacts/wp-12629-01/asset_manifest.json
  runs/wp-12629-01/kf_result.wp-12629-01.json
  docs/wp-12629-01/asset_manifest.json          (durable mirror: push gate drops artifacts/**+runs/**)
  docs/wp-12629-01/KF-RESULT-wp-12629-01.md     (report body with the single ```json block)

Usage: python3 scripts/kf_fetch_12629.py && python3 scripts/kf_register_12629.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

REPORT_ID = "12629"
PACKAGE_ID = "wp-12629-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/12629"
CONTRACT_HASH = "6cbf559cfaec918c26cf69c0081a2a3dcdceee4f7870797b35a27af8ca7e10eb"
CONTRACT_CHARS = 1899
CONTRACT_TITLE = "P333W2-N07 动力定位时域闭环与单点失效漂移：降额因子场与解析漂移锚"
CONTRACT_SCENARIO = "dp_timedomain"

RUN_DIR = pathlib.Path("runs/wp-12629-01")
ART_DIR = pathlib.Path("artifacts/wp-12629-01")
DOC_DIR = pathlib.Path("docs/wp-12629-01")


# ---------------------------------------------------------------- source loading
def load():
    md = (RUN_DIR / ("report_%s.md" % REPORT_ID)).read_text()
    rec = json.loads((RUN_DIR / ("report_%s.json" % REPORT_ID)).read_text())
    return md, rec


def line_offsets(md: str) -> dict[int, tuple[int, int]]:
    """1-based line number -> (start, end) char offsets of the line body (no trailing newline)."""
    out, pos, n = {}, 0, 1
    for line in md.split("\n"):
        out[n] = (pos, pos + len(line))
        pos += len(line) + 1
        n += 1
    return out


def segments(md: str, span: tuple[int, int], delims: list[str]) -> list[tuple[int, int]]:
    """Split [start,end) on any of ``delims`` (literal strings), returning trimmed sub-spans."""
    start, end = span
    text = md[start:end]
    parts, cur, i = [], 0, 0
    while i < len(text):
        for d in delims:
            if d and text.startswith(d, i):
                if i > cur:
                    parts.append((start + cur, start + i))
                i += len(d)
                cur = i
                break
        else:
            i += 1
    if cur < len(text):
        parts.append((start + cur, start + len(text)))
    return [(s, e) for s, e in parts if md[s:e].strip()]


def pick(md: str, parts, keyword: str, what: str = "") -> tuple[int, int]:
    hits = [(s, e) for s, e in parts if keyword in md[s:e]]
    if len(hits) != 1:
        raise SystemExit(
            "selector keyword %r for %s matched %d spans (expected exactly 1)" % (keyword, what or "?", len(hits)))
    return hits[0]


def find_all(md: str, fragment: str) -> list[int]:
    out, i = [], md.find(fragment)
    while i >= 0:
        out.append(i)
        i = md.find(fragment, i + 1)
    return out


def enclosing_clause(md: str, idx: int) -> tuple[int, int]:
    """Expand ``idx`` to the enclosing full-width parenthesis on its own line, else to the
    surrounding “，/；” clause. Keeps cross-reference quotes readable and verbatim."""
    ls = md.rfind("\n", 0, idx) + 1
    le = md.find("\n", idx)
    le = len(md) if le < 0 else le
    op = md.rfind("（", ls, idx)
    cl = md.find("）", idx, le)
    if op >= 0 and cl >= 0:
        return (op, cl + 1)
    start = max(md.rfind("，", ls, idx), md.rfind("；", ls, idx)) + 1
    ends = [x for x in (md.find("，", idx, le), md.find("；", idx, le), md.find("。", idx, le)) if x >= 0]
    return (start, min(ends) if ends else le)


# ---------------------------------------------------------------- main
def main() -> int:
    md, rec = load()
    h = hashlib.sha256(md.encode("utf-8")).hexdigest()
    if h != CONTRACT_HASH:
        raise SystemExit("FATAL: source hash mismatch: %s != contract %s" % (h, CONTRACT_HASH))
    if len(md) != CONTRACT_CHARS:
        raise SystemExit("FATAL: chars %d != contract %d" % (len(md), CONTRACT_CHARS))
    if rec.get("title") != CONTRACT_TITLE:
        raise SystemExit("FATAL: record.title differs from contract title")
    if rec.get("scenario_key") != CONTRACT_SCENARIO:
        raise SystemExit("FATAL: record.scenario_key differs from contract scenario_key")

    L = line_offsets(md)
    last_line = max(L)
    head: dict[int, int] = {}
    for ln, (hs, he) in L.items():
        mm = re.match(r"^##\s+(\d+)\s", md[hs:he])
        if mm:
            head[int(mm.group(1))] = ln

    def body_start(n: int) -> int:
        ln = head[n] + 1
        while ln <= last_line and not md[L[ln][0]:L[ln][1]].strip():
            ln += 1
        return ln
    raw: list[dict] = []   # (start, end, class, label, section, resolution, check, result, note)

    def add(span, asset_class, label, section, resolution, check, result, note):
        start, end = span
        quote = md[start:end]
        raw.append(dict(start=start, end=end, asset_class=asset_class, label=label,
                        in_report_section=section, resolution=resolution,
                        resolution_check={"check": check, "result": result}, note=note, quote=quote))

    # ---- A: the document itself
    add((0, len(md)), "document", "报告正文（markdown 全文）", "全文", "resolved_in_source",
        "sha256(markdown utf-8) 与契约 source_hash 重算比对", "resolved",
        "整篇 markdown 即源资产；locator method=document 覆盖 0..%d 字符；hash=%s" % (len(md), h))

    # ---- section 1: case, geometry, environment, companion case
    add(L[head[1]], "heading", "章节标题 §1 案例介绍", "§1", "resolved_in_source",
        "行 1 全文唯一出现", "resolved", "一级章节标题行，供下游按节定位")

    p = segments(md, L[2], ["。"])
    p0 = pick(md, p, "供应船", "船型/主尺度段")
    add(p0, "case_declaration", "船型与主尺度参数（L/B/T/Cb/Δ）", "§1", "resolved_in_source",
        "§1 首句按“。”切分后取含“供应船”的片段；片段在全文唯一", "resolved",
        "数值仅登记不换算；几何一致性判据见下一条")
    add(pick(md, segments(md, p0, ["），"]), "侧推", "推进配置"),
        "actuator_set", "推进器配置（2×尾全回转 + 2×艏侧推，总推力）", "§1", "resolved_in_source",
        "同片段按“），”切分后取含“侧推”的子片段", "resolved",
        "执行器配置声明；推力分配器实现体见 §2 分配器条目")
    q0 = segments(md, p0, ["），"])[0]
    add(pick(md, segments(md, q0, ["，"]), "rel_dev"), "geometry_declaration",
        "几何自校验结果（rel_dev）", "§1", "resolved_in_source",
        "同片段按“，”切分后取含字段名 rel_dev 的子片段", "resolved",
        "船型几何自校验条款原文；是否达标不在本工序判定")
    add(pick(md, p, "环境基准"), "environment_baseline", "环境基准参数（Hs/Tp/流速/来向数）", "§1",
        "resolved_in_source", "§1 按“。”切分后取含“环境基准”的片段", "resolved",
        "环境工况声明；分布实现（JONSWAP）见 §2")
    add(pick(md, p, "附算例"), "companion_case", "附算例：穿梭油船漂移锚", "§1", "resolved_in_source",
        "§1 按“。”切分后取含“附算例”的片段", "resolved", "附加算例声明，与主算例分属不同船型")

    # ---- section 2: method stack (one packed line -> split into components)
    add(L[head[2]], "heading", "章节标题 §2 怎么做的", "§2", "resolved_in_source", "行 4 全文唯一出现", "resolved",
        "方法章节标题行")
    m = segments(md, L[5], ["；"])
    add(pick(md, m, "v̇", "运动方程"), "governing_equation", "运动方程（低速水平面三自由度）", "§2",
        "resolved_in_source", "§2 按“；”切分后取含状态导数符号 v̇ 的片段", "resolved",
        "支配方程原文；自由度声明随片段一并登记")
    add(pick(md, m, "coupled_maneuvering", "系数来源"), "code_pointer", "风/流系数来源（平台单一源，代码引用）",
        "§2", "referenced_unresolved",
        "grep -rIl 'coupled_maneuvering' 全树：命中仅 knowledge/kb10k 的 claims/evidence JSON（数据记录），"
        "无同名 .py 代码文件 → 代码工件本体不在本工作树",
        "unresolved",
        "报告指向平台仓模块 backend.api.coupled_maneuvering；本仓只有 kb10k 代码指针记录提及该文件，"
        "代码本体不可解析，故登记为未解析、不臆造地址（kb10k 指针记录见 checks.code_pointer_target_in_worktree）")
    add(pick(md, m, "Newman", "二阶漂移力"), "model_component", "二阶定常/慢漂力模型（含标定口径）", "§2",
        "resolved_in_source", "§2 按“；”切分后取含 Newman 的片段", "resolved",
        "标定目标与慢漂模型原文；一致性由报告自述“测试钉住”，测试工件未在本仓")
    add(pick(md, m, "RAO", "一阶波频力"), "model_component", "一阶波频力（声明式简化 RAO）", "§2",
        "resolved_in_source", "§2 按“；”切分后取含 RAO 的片段", "resolved",
        "声明式简化模型，非试验 RAO：精度结论只到趋势/量级（与 §5 第 1 条一致）")
    add(pick(md, m, "QP", "推力分配"), "model_component", "推力分配（迭代 QP + 饱和冻结）", "§2",
        "resolved_in_source", "§2 按“；”切分后取含 QP 的片段", "resolved",
        "分配器实现方式原文；其边界性质见 §5 第 2 条")
    add(pick(md, m, "PD", "控制器"), "model_component", "控制器（PD + 积分 + 波滤 + 抗饱和）", "§2",
        "resolved_in_source", "§2 按“；”切分后取含 PD 的片段", "resolved", "控制器结构与波滤环节原文")
    add(pick(md, m, "RK4", "积分器"), "model_component", "时间推进（RK4）", "§2", "resolved_in_source",
        "§2 按“；”切分后取含 RK4 的片段", "resolved", "积分格式原文；步长未在该片段声明")
    add(pick(md, m, "注入", "失效注入"), "experiment_setup", "单点失效注入时刻", "§2", "resolved_in_source",
        "§2 按“；”切分后取含“注入”的片段", "resolved", "失效工况注入时刻原文")

    # ---- section 3: results (one bullet per line)
    add(L[head[3]], "heading", "章节标题 §3 计算结果", "§3", "resolved_in_source", "行 7 全文唯一出现", "resolved",
        "结果章节标题行")
    result_labels = [
        "能力包线条目（静力/时域均值、降额因子、失效叠加）",
        "结果 (a) 静力一致性",
        "结果 (b) 包含关系",
        "结果 (c) 解析漂移锚",
        "结果 (d) 漂移线性区",
        "结果 (e) 分层可证伪混淆矩阵",
        "单点失效漂移事件条目（稳态漂移速度与漂移距离）",
    ]
    r0 = body_start(3)
    result_lines = [ln for ln in range(r0, last_line + 1)
                    if md[L[ln][0]:L[ln][1]].strip().startswith("*")]
    if len(result_lines) != len(result_labels):
        raise SystemExit("FATAL: §3 bullet count %d != expected %d" % (len(result_lines), len(result_labels)))
    for ln, label in zip(result_lines, result_labels):
        add(L[ln], "result_block", label, "§3", "resolved_in_source",
            "§3 第 %d 行整行（项目符号行）在全文唯一" % ln, "resolved",
            "整行登记：内含多个数值，仅登记不改写、不判定精度")

    # ---- section 4: figures
    add(L[head[4]], "heading", "章节标题 §4 图", "§4", "resolved_in_source", "行 16 全文唯一出现", "resolved",
        "图目录章节标题行")
    fig_line = L[body_start(4)]
    add(fig_line, "figure_index", "图目录（图1–图7 声明）", "§4", "resolved_in_source",
        "§4 整行；正则 图\\d+ 计数与平台 record.figures 长度比对", "resolved",
        "仅图序号与用途文字，非图件本体；图件登记见下一条")
    figs = rec.get("figures") or []
    add(fig_line, "figure_asset_set", "平台 record.figures 图件（%d 项）" % len(figs), "§4",
        "referenced_unresolved",
        "record.figures 每项仅含 name/caption，无内联图片数据、base64 或可下载 URI", "unresolved",
        "图件二进制在本报告中不可解析：文件名=%s；同名 figN 序号与图号存在错位（见 checks.figure_name_caption_permutation）"
        % ("; ".join(f.get("name", "") for f in figs)))

    # ---- section 5: limitations
    add(L[head[5]], "heading", "章节标题 §5 注意点（局限）", "§5", "resolved_in_source", "行 19 全文唯一出现",
        "resolved", "局限章节标题行")
    lim_span = L[body_start(5)]
    lim = segments(md, lim_span, ["；"])
    add(lim_span, "limitation_block", "局限条目（%d 条，声明式模型/包线性质/broaching/未建模项）" % len(lim), "§5",
        "resolved_in_source", "§5 整行按“；”切分得 %d 条" % len(lim), "resolved",
        "局限原文：适用于下游判断结论适用范围")
    add(pick(md, lim, "非试验 RAO", "试验 RAO 缺失声明"), "dataset", "试验/公开 RAO 数据集", "§5",
        "declared_absent",
        "§5 第 1 条显式声明“非试验 RAO”；全文检索无试验 RAO 数据表/文件引用", "absent",
        "报告自述该数据资产不存在：登记为 declared_absent，不得由本工序补造")

    # ---- section 6: error table
    add(L[head[6]], "heading", "章节标题 §6 误差判定", "§6", "resolved_in_source", "行 22 全文唯一出现", "resolved",
        "误差判定章节标题行")
    t0 = body_start(6)
    row_lines = [ln for ln in range(t0, last_line + 1) if md[L[ln][0]:L[ln][1]].strip().startswith("|")]
    table_span = (L[row_lines[0]][0], L[row_lines[-1]][1])
    n_rows = len(row_lines) - 2  # header + separator row
    add(table_span, "table", "误差判定表（表头+分隔行+%d 行数据）" % n_rows, "§6", "resolved_in_source",
        "§6 行 %d–%d 连续切片；逐行以 '|' 起始的行计数=%d" % (row_lines[0], row_lines[-1], len(row_lines)),
        "resolved", "表格逐行原文登记；误差数值与其“<3%?”判定仅登记，复算/裁量属平台门")

    # ---- dangling cross references (real defects, kept visible)
    idx64 = find_all(md, "§6.4")
    headings = [md[s:e].strip() for s, e in L.values() if md[s:e].lstrip().startswith("#")]
    has_64 = any(re.match(r"^#+\s*6\.4", x) for x in headings)
    if len(idx64) == 1 and not has_64:
        add(enclosing_clause(md, idx64[0]), "cross_reference", "被引小节 §6.4（口径偏差声明）", "§3 (d)", "referenced_unresolved",
            "全文检索 '§6.4' 命中 1 处；章节标题列表中不存在 6.4 小节", "unresolved",
            "指向的小节在本 markdown 中不存在：登记为断链引用，供 report 修订方补齐或改指")
    idx_tab = find_all(md, "报告表")
    if len(idx_tab) == 1 and not any("|" in md[L[ln][0]:L[ln][1]] and "阻尼比" in md[L[ln][0]:L[ln][1]]
                                    for ln in row_lines):
        add(enclosing_clause(md, idx_tab[0]), "cross_reference", "被引“报告表”（阻尼比 r 分布）", "§3 (c)",
            "referenced_unresolved",
            "全文检索 '报告表' 命中 1 处；§6 误差表内无含“阻尼比/r”的数据行", "unresolved",
            "所指的 r 分布表在本 markdown 中不存在：引用不可解析，未臆造转向其它来源")

    # ---------------------------------------------------------------- assemble
    raw.sort(key=lambda a: (0 if a["asset_class"] == "document" else 1, a["start"], a["end"]))
    assets = []
    seen_quotes: dict[str, int] = {}
    for i, a in enumerate(raw, start=1):
        a = dict(a)
        a["asset_id"] = "A%02d" % i
        start, end = a.pop("start"), a.pop("end")
        quote = a.pop("quote")  # single source of truth: locator.quote (no top-level duplicate)
        unique = md.count(quote) == 1
        prev = seen_quotes.get(quote)
        a["locator"] = {
            "method": "document" if a["asset_class"] == "document" else "char_span",
            "start_char": start,
            "end_char": end,
            "start_line": md.count("\n", 0, start) + 1,
            "end_line": md.count("\n", 0, max(end - 1, start)) + 1,
            "quote": quote,
            "unique": unique,
            "duplicate_quote_of": prev,
        }
        if unique:
            seen_quotes[quote] = a["asset_id"]
        assets.append(a)

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("FATAL: duplicate asset ids")
    non_unique = [a["asset_id"] for a in assets if not a["locator"]["unique"]]
    if non_unique:
        raise SystemExit("FATAL: non-unique quotes: %s" % non_unique)

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    # ---------------------------------------------------------------- cross checks
    summary = rec.get("summary") or ""
    nums = re.findall(r"\d+(?:\.\d+)?%?", summary)
    num_hits = {n: (n in md) for n in nums}
    fig_refs = re.findall(r"图(\d+)", md[L[body_start(4)][0]:L[body_start(4)][1]])
    fig_perm = []
    for f in figs:
        mnum = re.search(r"fig(\d+)", f.get("name", ""))
        cnum = re.search(r"图(\d+)", f.get("caption", ""))
        if mnum and cnum and mnum.group(1) != cnum.group(1):
            fig_perm.append({"name": f["name"], "name_index": int(mnum.group(1)),
                             "caption_index": int(cnum.group(1))})
    own = ("kf_register_12629", "kf_verify_12629", "wp-12629", "report_12629")
    try:
        grep = subprocess.run(["grep", "-rIl", "--exclude-dir=.git", "coupled_maneuvering", "."],
                              capture_output=True, text=True)
        cm_hits = sorted(x for x in grep.stdout.split() if not any(o in x for o in own))
    except FileNotFoundError:  # pragma: no cover
        cm_hits = ["<grep unavailable>"]
    cm_code = [x for x in cm_hits if x.endswith((".py", ".pyi", ".pyx"))]

    checks = {
        "source_hash_matches": h == CONTRACT_HASH,
        "chars_match_contract": len(md) == CONTRACT_CHARS,
        "title_matches_contract": rec.get("title") == CONTRACT_TITLE,
        "scenario_key_matches_contract": rec.get("scenario_key") == CONTRACT_SCENARIO,
        "all_quotes_unique": all(a["locator"]["unique"] for a in assets),
        "all_locators_slice_back": all(md[a["locator"]["start_char"]:a["locator"]["end_char"]]
                                       == a["locator"]["quote"] for a in assets),
        "record_summary_numbers_present_in_markdown": {
            "tokens": nums, "present": num_hits,
            "all_present": all(num_hits.values()),
        },
        "figure_count": {"record_figures": len(figs), "markdown_figure_refs": len(fig_refs),
                         "figure_refs": fig_refs, "consistent": len(figs) == len(fig_refs)},
        "figure_name_caption_permutation": {"count": len(fig_perm), "items": fig_perm},
        "code_pointer_target_in_worktree": {
            "command": "grep -rIl --exclude-dir=.git coupled_maneuvering . (this package's own outputs excluded)",
            "hits_total": cm_hits, "hits_python_code": cm_code,
            "code_artifact_present": len(cm_code) > 0,
            "reading": "hits are knowledge/kb10k claim+evidence JSON (code-pointer records naming "
                       "backend/api/coupled_maneuvering.py); no .py module in this worktree",
        },
        "dangling_reference_6_4": {"headings": headings, "has_6_4_heading": has_64},
    }

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "objective": {"register_assets": True, "classify_report_type": False},
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": h,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "contract_chars": CONTRACT_CHARS,
            "lines": md.count("\n") + 1,
            "title": rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "platform_mission_id": rec.get("mission_id"),
            "platform_status": rec.get("status"),
            "platform_created_at": rec.get("created_at"),
            "platform_tags": rec.get("tags", []),
            "platform_figures": figs,
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "claims": 0,
        },
        "assets": assets,
        "claims": [],
        "claims_note": ("claims intentionally empty: contract objective = asset registration only "
                        "(register_assets=true, classify_report_type=false, no extraction). Emitting claims "
                        "here would fabricate task_type-03 knowledge objects."),
        "checks": checks,
        "integrity": {
            "quote_uniqueness": "every quote occurs exactly once in the markdown (checked in-script)",
            "hash_recomputed_locally": True,
            "hash_matches_contract": True,
            "no_claim_marked_verified": True,
            "verified_by": "scripts/kf_verify_12629.py (independent re-fetch + locator re-resolution)",
        },
        "boundaries": {
            "only_report_id": REPORT_ID,
            "other_reports_read_or_written": False,
            "upstream_work_package_artifacts_rewritten": False,
            "claims_marked_verified": 0,
        },
    }

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + CONTRACT_HASH,
            "producer": "TensorKnowledge scripts/kf_register_12629.py (asset registration, no extraction)",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": ("source_hash recomputed from the exact UTF-8 bytes of the report markdown field; "
                      "quotes are runtime slices, re-resolved by scripts/kf_verify_12629.py"),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    (ART_DIR / "asset_manifest.json").write_text(text)
    (DOC_DIR / "asset_manifest.json").write_text(text)
    (RUN_DIR / ("kf_result.%s.json" % PACKAGE_ID)).write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2))
    (DOC_DIR / ("kf_result.%s.json" % PACKAGE_ID)).write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2))

    print("assets:", len(assets), "by_class:", by_class)
    print("by_resolution:", by_res)
    print("checks:", json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items()
                                                                     if kk != "tokens"})
                                 for k, v in checks.items()}, ensure_ascii=False)[:900])
    print("wrote:", ART_DIR / "asset_manifest.json", DOC_DIR / "asset_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())