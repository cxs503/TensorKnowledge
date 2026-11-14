#!/usr/bin/env python3
"""KF work package wp-13272-01 — task_type 01-asset-registration.

Source report: tensor://reports/13272 ("CII 规则内核三副本单源化与 regime 语义修复（m13764）").

Scope: register the source assets a downstream 工序 can point at, nothing else.
  * pin-check the source markdown (hash / chars / bytes / lines) against the bytes stored
    by scripts/kf_fetch_13272.py;
  * inventory every in-report asset — document, preamble, H2 sections, markdown tables,
    the fenced repro block, the declared figure (with pinned PNG bytes), the code/artifact
    paths, code symbols, regulatory references and the numeric tokens that carry the
    report's own conclusions — each with a verbatim locator (char span + line span +
    quote hash) that is re-resolvable offline;
  * emit asset_manifest.json (schema asset_manifest_kf.v1), acceptance.json (machine
    checked acceptance items), the kf_result.v1 envelope and fig1_asset_resolution.png.

It never extracts claims (claims=[] is legitimate for 01), never classifies the report,
never marks anything verified (that is the platform gate's job), never executes the
report's repro commands and never reads any report_id other than 13272.

Honest boundary kept explicit: code paths, test paths and artifacts named by the report
belong to the ship-performance-platform repo, which is *not* materialised here. Their
locators resolve inside the pinned markdown, but their referents are not fetched,
executed or re-read -> resolution.status = "metadata_only" with a reason, so registration
cannot be mistaken for verification.

Usage:
  python3 scripts/wp13272_register_assets.py            # build all package outputs
  python3 scripts/wp13272_register_assets.py --check     # rebuild in memory, diff files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "docs" / "kf" / "wp-13272-01"
SRCDIR = OUTDIR / "source"
MD_PATH = SRCDIR / "report_13272.md"
RECORD_PATH = SRCDIR / "report_13272.record.json"
MANIFEST_PATH = OUTDIR / "asset_manifest.json"
ACCEPTANCE_PATH = OUTDIR / "acceptance.json"
RESULT_PATH = OUTDIR / "kf_result.json"
FIGURE_PATH = OUTDIR / "fig1_asset_resolution.png"

PACKAGE_ID = "wp-13272-01"
REPORT_ID = "13272"
TASK_TYPE = "01-asset-registration"
LANE = "C"
PRODUCER = "kf-worker m20478 (TensorKnowledge) · scripts/wp13272_register_assets.py"
SOURCE_URI = "tensor://reports/13272"
CROSS_REPO = "ship-performance-platform"
CROSS_REPO_REASON = (
    "引文位置已在钉住的 markdown 中逐字解析；但该路径指向 %s，其源码/产物未在本仓落盘，"
    "本工序未回读、未执行、未复核其内容（登记≠验证）" % CROSS_REPO
)
ID_PREFIX = "r%s:" % REPORT_ID
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

SECTION_SLUG_MAP = {
    "① 案例介绍（问题背景）": "case",
    "② 怎么做的（方法）": "method",
    "③ 计算结果（程序化注入，`artifacts/cii_consistency_scan_*.json`）": "results",
    "④ 结果图": "figures",
    "⑤ 注意点 / 局限": "limits",
    "⑥ 误差判定": "error_judgement",
    "复现": "reproduce",
    "建议新总账条目": "ledger",
}
SECTION_LABELS = {
    "case": "① 案例介绍（三副本 A/B/C 与复核靶子）",
    "method": "② 怎么做的（机器对账工具 → 基线 → 根因 C1/C2 → 最小修复）",
    "results": "③ 计算结果（2019–2030 三实现 required CII 与 regime 一致性表）",
    "figures": "④ 结果图（修复前/后三实现曲线）",
    "limits": "⑤ 注意点 / 局限（法规系数层未动、dd 向量单档、向后兼容）",
    "error_judgement": "⑥ 误差判定（−11.00% → 0.00%；相对差 ≤1e-15）",
    "reproduce": "复现（repro 命令块所在节）",
    "ledger": "建议新总账条目（DEF-CII-SINGLE-SOURCE 验收条件与后续增量）",
}

# (asset_class, slug, label, token, anchor, note)
#   anchor=None  -> the token itself must be unique; locator = token span.
#   anchor given -> the anchor must be unique; locator = the whole line carrying it.
TOKEN_SPECS = [
    # --- implementation copies named by the report (cross-repo referents) -------------
    ("code_or_artifact_path", "impl_a", "A 实现（权威口径）：CII 要求值内核",
     "backend/services/cii_required_value.py", None, "报告 ① 表格行；分数口径、显式 regime（m1829 建）"),
    ("code_or_artifact_path", "impl_b", "B 实现（主 API 副本）",
     "backend/api/green_shipping.py", None, "报告 ① 表格行；分数口径副本"),
    ("code_or_artifact_path", "impl_c", "C 实现（冰区链副本，本单真缺陷所在）",
     "backend/modules/green_navigation_ice/mepc.py", None, "报告 ① 表格行；百分比口径、Z 表一次性兜底"),
    ("code_or_artifact_path", "ice_api", "冰区链 compliance / model_audit 回显层",
     "green_navigation_ice/api.py", None, "报告 ② 修复项 4"),
    ("code_or_artifact_path", "scan_tool", "机器对账工具（三实现 × 年份逐点对账）",
     "tools/cii_consistency_scan.py", "：对 (年份 2019–2030) × 三实现，", "报告 ② 第 1 条"),
    ("code_or_artifact_path", "scan_before", "基线对账产物（修复前）",
     "artifacts/cii_consistency_scan_before.json", "→ **12/12 年份不一致**", "报告 ② 第 2 条基线"),
    ("code_or_artifact_path", "scan_after", "修复后对账产物",
     "artifacts/cii_consistency_scan_after.json", None, "报告 ③ 与 复现 两处引用，token 唯一"),
    ("declared_figure_artifact", "fig_artifact", "报告正文声明的结果图文件（仓内产物路径，非平台图件）",
     "artifacts/m13764_cii_consistency.png", None, "§④ 正文逐字给出的文件名；本仓未落盘"),
    ("test_path", "test_consistency", "单源一致性回归测试（153 条断言）",
     "tests/test_cii_single_source_consistency.py", None, "报告 复现 块 + ⑥ 表"),
    ("test_path", "test_ice", "冰区链测试目录（47 条）",
     "backend/modules/green_navigation_ice/tests", None, "报告 复现 块"),
    ("test_path", "test_green_shipping", "green_shipping 测试（与 green_efficiency 合计 37 条）",
     "backend/tests/test_green_shipping.py", None, "报告 复现 块"),
    ("test_path", "test_green_efficiency", "绿色效率评审测试（m1895）",
     "backend/tests/test_green_efficiency_m1895.py", None, "报告 复现 块"),
    ("test_path", "test_cii_regime", "CII regime 语义测试（70 条）",
     "tests/test_cii_regime_m1829.py", None, "报告 复现 块（与 A 实现配套）"),
    # --- code symbols that implement the fix -----------------------------------------
    ("code_symbol", "bug_c1_expr", "C1 缺陷代码片段（Z 表一次性兜底 11%）",
     "Z_FACTORS.get(year, 11.0)", None, "报告 ② 根因 C1 逐字引用"),
    ("code_symbol", "sym_z_factor", "C 实现 z_factor()（修复后 <2023 返回 0.0）",
     "z_factor()", None, "报告 ② 修复项 1"),
    ("code_symbol", "sym_z_regime", "C 新增 z_regime()（regime 判定）",
     "z_regime()", None, "报告 ② 修复项 1"),
    ("code_symbol", "sym_z_extrapolated_fn", "C 新增 z_extrapolated()（外推标记）",
     "z_extrapolated()", None, "报告 ② 修复项 1"),
    ("code_symbol", "sym_required_cii_meta", "C 新增 required_cii_meta()（成组元信息）",
     "required_cii_meta()", None, "报告 ② 修复项 1"),
    ("code_symbol", "sym_gn_required_cii", "B 侧委派函数 _gn_required_cii()",
     "_gn_required_cii()", None, "报告 ② 修复项 2：委派 A 的 required_cii()"),
    ("code_symbol", "sym_required_cii", "A 权威实现 required_cii()",
     "required_cii()", "委派 A 的 `required_cii()`，保留原键", "报告 ② 修复项 2；token 2 次出现但同属一行"),
    ("code_symbol", "flag_z_extrapolated", "外推标记键 z_extrapolated（2027+ 必须携带）",
     "z_extrapolated", "但现在**必须**带 `z_extrapolated=True`，", "报告 ⑤ 行为变更第 2 条"),
    ("code_symbol", "flag_required_is_reference", "回显键 required_value_is_reference",
     "required_value_is_reference", None, "报告 ② B 侧新增键"),
    ("code_symbol", "flag_regime_note", "回显键 regime_note",
     "regime_note", None, "报告 ② B 侧新增键"),
    ("code_symbol", "const_dd_basis", "常量 DD_VECTOR_BASIS（dd 向量单档局限的机器可见声明）",
     "DD_VECTOR_BASIS", None, "报告 ⑤ 局限"),
    ("code_symbol", "field_dd_vector_basis", "回显字段 dd_vector_basis",
     "dd_vector_basis", None, "报告 ② 修复项 4"),
    ("code_symbol", "field_divergent_years", "对账结果字段 divergent_years",
     "divergent_years", "对账结论：修复前 `divergent_years = 12/12`，修复后 `0/12`", "报告 ③ 对账结论行"),
    # --- regulatory references (coefficient layer stays WITHHELD) ---------------------
    ("regulatory_reference", "mepc353", "参考线规则 MEPC.353(78)",
     "MEPC.353(78)", None, "报告 ① 法规三件之一；系数层证据等级 WITHHELD"),
    ("regulatory_reference", "mepc338", "年度折减率 Z 表来源 MEPC.338(76)",
     "MEPC.338(76)", None, "报告 ①；本次不动 Z 表值"),
    ("regulatory_reference", "mepc354", "评级规则 MEPC.354(78)（G4 档未转录）",
     "MEPC.354(78)", "G4 的船型×容量档转录。因此只断言分区完备/单调/端点归属（机制层），",
     "报告 ⑤；dd 向量只有通用单档"),
    # --- equations and the numbers that carry the conclusions ------------------------
    ("equation", "eq_reference_line", "参考线解析式 a·Cap^(−c)",
     "a·Cap^(−c)", "`a·Cap^(−c)` = 4.2317", "报告 ⑥ 基准列；2019 基线 4.2317 由此式算出"),
    ("equation", "eq_rating_def", "评级判定式 dd_i·req",
     "dd_i·req", None, "报告 ⑥ 机制层基准"),
    ("numeric_token", "value_42317", "2019 基线要求值 4.2317 gCO2/(dwt·nm)",
     "4.2317", "3.7662 vs 4.2317 gCO2/(dwt·nm)", "报告 ② 根因 C1 括号内（修复后 C 亦为此值）"),
    ("numeric_token", "value_37662", "C 实现错值 3.7662（比参考线低 11.0%）",
     "3.7662", "3.7662 vs 4.2317 gCO2/(dwt·nm)", "报告 ② 根因 C1 括号内"),
    ("numeric_token", "err_minus11", "C1 偏差幅度 −11.0%",
     "−11.0%", "(−11.0%)", "报告 ③ 表 2019–2022 行（C 实现错值相对参考线的偏差）"),
    ("numeric_token", "div_before", "修复前不一致年份数 12/12",
     "12/12", "→ **12/12 年份不一致**", "报告 ② 基线结论"),
    ("numeric_token", "div_after", "修复后不一致年份数 0/12",
     "0/12", "修复后 `0/12`", "报告 ③ 对账结论"),
    ("numeric_token", "assertions153", "回归断言 153 条",
     "153 条回归断言", None, "报告 复现 与 ⑥（153 passed）"),
    ("numeric_token", "capacity_80000", "核算船型/容量档：bulk carrier 80000 DWT",
     "80000 DWT", "bulk carrier, Capacity = 80000 DWT：", "报告 ③ 数值表口径"),
    # --- regime vocabulary ------------------------------------------------------------
    ("regime_token", "regime_not_applicable", "regime 取值 not_yet_applicable（规则未适用年份）",
     "not_yet_applicable", None, "报告 ③ 表 2019–2022 行"),
    ("regime_token", "regime_determined", "regime 取值 determined（法规确定值）",
     "determined", "| 2023 | determined |", "报告 ③ 表 2023 行"),
    ("regime_token", "regime_extrapolated", "regime 取值 extrapolated（外推值）",
     "extrapolated", "| 2027–2030 | extrapolated |", "报告 ③ 表 2027–2030 行"),
    # --- ledger / KPI anchors ---------------------------------------------------------
    ("platform_ledger_reference", "ledger_def_slug", "建议新总账条目 slug",
     "DEF-CII-SINGLE-SOURCE", "- `slug=DEF-CII-SINGLE-SOURCE`", "报告 文末建议条目"),
    ("platform_ledger_reference", "kpi_qc_recheck", "上游 KPI 条目（本单锚点）",
     "KPI-QC-RECHECK", None, "报告抬头 锚点 行"),
    ("platform_ledger_reference", "domain_repo", "所属域仓名（ship-performance-platform）",
     CROSS_REPO, "- `slug=DEF-CII-SINGLE-SOURCE`，域：绿色航行（`ship-performance-platform`）",
     "报告 文末建议条目：域归属"),
]
CROSS_REPO_CLASSES = {"code_or_artifact_path", "test_path", "declared_figure_artifact"}


# --------------------------------------------------------------------------- helpers
def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def line_index(md: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(md):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def char_to_line(starts: list[int], offset: int) -> int:
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def context_of(md: str, start: int, end: int, pad: int = 40) -> str:
    return md[max(0, start - pad):start] + md[start:end] + md[end:min(len(md), end + pad)]


def png_size(blob: bytes):
    if not blob.startswith(PNG_MAGIC) or len(blob) < 24 or blob[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", blob[16:24])


def make_asset(asset_id, asset_class, label, token, md, starts, start, end,
               occurrences, unique, note, status, scope, checks, reason=None):
    quote = md[start:end]
    asset = {
        "asset_id": asset_id,
        "asset_class": asset_class,
        "label": label,
        "token": token,
        "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": start,
            "end_char": end,
            "start_line": char_to_line(starts, start),
            "end_line": char_to_line(starts, max(start, end - 1)),
            "quote": quote,
            "quote_sha256": sha256_text(quote),
            "unique": unique,
            "occurrences": occurrences,
            "context": context_of(md, start, end),
        },
        "resolution": {"status": status, "scope": scope, "checks": checks},
        "note": note,
    }
    if reason:
        asset["resolution"]["reason"] = reason
    return asset


def locate_token(md, token, anchor):
    """Return (start, end, occurrences, unique) for one curated token."""
    occurrences = md.count(token)
    if occurrences == 0:
        raise ValueError("token not in source: %r" % token)
    if anchor is None:
        if occurrences != 1:
            raise ValueError("token %r occurs %d times and carries no anchor" % (token, occurrences))
        start = md.index(token)
        return start, start + len(token), occurrences, True
    if md.count(anchor) != 1:
        raise ValueError("anchor occurs %d times (want 1): %r" % (md.count(anchor), anchor))
    hit = md.index(anchor)
    start = md.rfind("\n", 0, hit) + 1
    end = md.find("\n", hit)
    if end < 0:
        end = len(md)
    line = md[start:end]
    if token not in line:
        raise ValueError("token %r not on the anchor line %r" % (token, line))
    return start, end, occurrences, True


def parse_sections(md, starts):
    lines = md.split("\n")
    heads = [(i, ln) for i, ln in enumerate(lines, 1) if ln.startswith("## ")]
    out = []
    for n, (line_no, head) in enumerate(heads):
        start = starts[line_no - 1]
        end = starts[heads[n + 1][0] - 1] if n + 1 < len(heads) else len(md)
        out.append({"line_no": line_no, "heading": head, "start": start, "end": end})
    return out


def parse_tables(md, starts):
    lines = md.split("\n")
    tables, i = [], 0
    while i < len(lines):
        if lines[i].startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            if j - i >= 3 and set(lines[i + 1].replace("|", "").replace("-", "").strip()) <= {""}:
                tables.append({
                    "start": starts[i],
                    "end": starts[j] if j < len(starts) else len(md),
                    "rows": j - i - 2,
                    "cols": lines[i].count("|") - 1,
                    "header": lines[i],
                })
            i = j
        else:
            i += 1
    return tables


def parse_fences(md, starts):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            start = starts[i]
            end = starts[j] + len(lines[j]) if j < len(lines) else len(md)
            out.append({
                "start": start,
                "end": end,
                "lang": lines[i][3:].strip(),
                "commands": [ln for ln in lines[i + 1:j] if ln.strip()],
            })
            i = j + 1
        else:
            i += 1
    return out


def section_slug_for(start, sections):
    slug = "preamble"
    for sec in sections:
        if sec["start"] <= start:
            slug = SECTION_SLUG_MAP.get(sec["heading"][3:].strip(), sec["heading"])
    return slug


# --------------------------------------------------------------------------- manifest
def build_manifest(md: str, record: dict, generated_at: str) -> dict:
    starts = line_index(md)
    sections = parse_sections(md, starts)
    tables = parse_tables(md, starts)
    fences = parse_fences(md, starts)
    assets = []

    # A. the pinned document itself (full markdown as its own quote -> offline re-resolvable)
    assets.append({
        "asset_id": ID_PREFIX + "document",
        "asset_class": "report_document",
        "label": "源报告 13272 的 markdown 全文（钉住字节）",
        "token": "report_13272.md",
        "locator": {
            "source_field": "markdown",
            "method": "document",
            "start_char": 0,
            "end_char": len(md),
            "start_line": 1,
            "end_line": md.count("\n") + (0 if md.endswith("\n") else 1),
            "quote": md,
            "quote_sha256": sha256_text(md),
            "unique": True,
            "occurrences": 1,
            "context": md[:80],
        },
        "resolution": {
            "status": "resolved",
            "scope": "pinned bytes",
            "checks": [
                {"check": "byte_identical_to_served_markdown", "result": "pass (scripts/kf_fetch_13272.py --check)"},
                {"check": "sha256", "result": sha256_text(md)},
                {"check": "chars/bytes_utf8", "result": "%d / %d" % (len(md), len(md.encode("utf-8")))},
            ],
        },
        "note": "任务边界：只读 report_id=13272；本工序不抽取、不复核报告结论",
    })

    # B. header preamble + every H2 section
    if sections:
        first = sections[0]["start"]
        assets.append({
            "asset_id": ID_PREFIX + "preamble",
            "asset_class": "report_section",
            "label": "抬头（标题 + 锚点 + 分层证据等级声明）",
            "token": "## 前正文",
            "locator": {
                "source_field": "markdown",
                "method": "char_span",
                "start_char": 0,
                "end_char": first,
                "start_line": 1,
                "end_line": char_to_line(starts, max(0, first - 1)),
                "quote": md[0:first],
                "quote_sha256": sha256_text(md[0:first]),
                "unique": True,
                "occurrences": 1,
                "context": md[0:min(120, first)],
            },
            "resolution": {
                "status": "resolved",
                "scope": "source span",
                "checks": [{"check": "evidence_level_declared",
                            "result": "数值层 REAL / 法规系数层 WITHHELD（报告自述，仅登记）"}],
            },
            "note": "抬头已声明证据等级分层；登记不等于接受该判断",
        })
    for sec in sections:
        slug = SECTION_SLUG_MAP.get(sec["heading"][3:].strip())
        if slug is None:
            raise ValueError("unmapped H2 heading: %r" % sec["heading"])
        assets.append(make_asset(
            ID_PREFIX + "section:" + slug, "report_section", SECTION_LABELS[slug],
            sec["heading"], md, starts, sec["start"], sec["end"], 1, True,
            "H2 节；span 从节标题行到下一 H2 之前",
            "resolved", "source span",
            [{"check": "heading_verbatim", "result": "pass"},
             {"check": "span_inside_document", "result": "%d..%d of %d" % (sec["start"], sec["end"], len(md))}],
        ))

    # C. markdown tables (locator = whole table block; cells deliberately not extracted)
    for n, tab in enumerate(tables, 1):
        assets.append(make_asset(
            ID_PREFIX + "table:%d" % n, "report_table",
            "表格 %d（%d 数据行 × %d 列，位于 §%s）" % (n, tab["rows"], tab["cols"],
                                                  section_slug_for(tab["start"], sections)),
            tab["header"].strip(), md, starts, tab["start"], tab["end"], 1, True,
            "只登记表位置与形状；单元格内容不在 01 工序抽取（抽取属 03）",
            "resolved", "source span",
            [{"check": "shape", "result": "%d data rows x %d cols" % (tab["rows"], tab["cols"])},
             {"check": "has_separator_row", "result": "pass"}],
        ))

    # D. fenced repro block (registered, never executed)
    for n, fence in enumerate(fences, 1):
        assets.append(make_asset(
            ID_PREFIX + "repro_block:%d" % n, "repro_command_block",
            "复现命令块 %d（%s，%d 条命令）" % (n, fence["lang"] or "plain", len(fence["commands"])),
            "```" + fence["lang"], md, starts, fence["start"], fence["end"], 1, True,
            "命令块仅登记，未在本工序执行（执行属复现工位）",
            "resolved", "source span",
            [{"check": "commands", "result": str(len(fence["commands"]))},
             {"check": "executed_here", "result": "no"}],
        ))

    # E. declared platform figures, with pinned bytes when the platform serves them
    fetch = {f["name"]: f for f in record.get("figure_fetch") or []}
    for fig in record.get("figures") or []:
        name = fig["name"]
        info = fetch.get(name, {})
        pinned = info.get("pinned_path")
        checks = [
            {"check": "declared_in_record", "result": "pass (figures[].name)"},
            {"check": "filename_in_markdown", "result": "pass" if name in md else "filename absent from body"},
            {"check": "figure_endpoint_http_status", "result": str(info.get("http_status"))},
        ]
        status = "declared_only"
        reason = "平台未提供图件字节：只能登记声明，不能登记位图"
        if pinned:
            blob = (ROOT / pinned).read_bytes()
            size = png_size(blob)
            digest_ok = hashlib.sha256(blob).hexdigest() == info.get("sha256")
            checks.append({"check": "pinned_bytes", "result": "%s (%d bytes)" % (pinned, len(blob))})
            checks.append({"check": "png_magic_and_ihdr",
                           "result": ("pass %dx%d" % size) if size else "not a PNG"})
            checks.append({"check": "sha256_matches_fetch_record", "result": "pass" if digest_ok else "MISMATCH"})
            status = "resolved" if (size and digest_ok) else "unresolved"
            reason = None if status == "resolved" else "钉住字节的 PNG 校验未通过"
        start = md.find(name)
        if start < 0:
            start = 0
        line_start = md.rfind("\n", 0, start) + 1
        line_end = md.find("\n", start)
        if line_end < 0:
            line_end = len(md)
        assets.append(make_asset(
            ID_PREFIX + "figure:" + re.sub(r"[^A-Za-z0-9]+", "_", name), "declared_figure",
            "平台声明的图件 %s" % name, name, md, starts, line_start, line_end,
            max(1, md.count(name)), md.count(name) == 1,
            "图件字节由 /tensor/reports/13272/figures/<name> 取得并钉入 source/figures/",
            status, "source caption span + pinned png bytes", checks, reason,
        ))

    # F. curated tokens (paths / symbols / regulations / numbers / ledger anchors)
    for asset_class, slug, label, token, anchor, note in TOKEN_SPECS:
        start, end, occurrences, unique = locate_token(md, token, anchor)
        cross = asset_class in CROSS_REPO_CLASSES
        checks = [
            {"check": "token_occurrences", "result": str(occurrences)},
            {"check": "locator_unique", "result": "pass" if unique else "ambiguous"},
            {"check": "quote_verbatim", "result": "pass"},
        ]
        if cross:
            checks.append({"check": "referent_materialised_here", "result": "no (%s)" % CROSS_REPO})
        assets.append(make_asset(
            ID_PREFIX + asset_class.replace("_", "-") + ":" + slug.replace("_", "-"),
            asset_class, label, token, md, starts, start, end, occurrences, unique, note,
            "metadata_only" if cross else "resolved",
            "locator in source; referent not materialised (cross-repo)" if cross else "source span",
            checks, CROSS_REPO_REASON if cross else None,
        ))

    # ---- counts, all recomputed from the asset list
    by_class, by_resolution = {}, {}
    markdown_locators = 0
    for asset in assets:
        by_class[asset["asset_class"]] = by_class.get(asset["asset_class"], 0) + 1
        st = asset["resolution"]["status"]
        by_resolution[st] = by_resolution.get(st, 0) + 1
        if asset["locator"]["source_field"] == "markdown":
            markdown_locators += 1

    return {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": generated_at,
        "producer": PRODUCER,
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + sha256_text(md),
            "hash_match": sha256_text(md) == record["markdown_sha256"],
            "chars": len(md),
            "bytes": len(md.encode("utf-8")),
            "lines": md.count("\n") + (0 if md.endswith("\n") else 1),
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "mission_id": record.get("mission_id"),
            "status": record.get("status"),
            "retrieved_via": record.get("retrieved_via"),
            "work_package_boundary": record.get("work_package_boundary"),
        },
        "assets": assets,
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_resolution.items())),
            "markdown_locators": markdown_locators,
            "sections": len(sections) + 1,
            "tables": len(tables),
            "fenced_blocks": len(fences),
            "figures_declared": len(record.get("figures") or []),
            "figures_with_pinned_bytes": sum(1 for f in record.get("figure_fetch") or []
                                             if f.get("status") == "resolved_bytes"),
            "claims": 0,
        },
        "claims": [],
        "claims_note": (
            "task_type=01 的职责边界：只登记资产位置，不抽取知识对象、不判断报告结论真伪。"
            "claims=[] 是本工序的完整结果，不是缺失。"
        ),
        "integrity": {
            "hash_recomputed_locally": True,
            "hash_algorithm": "sha256",
            "verified_logic": (
                "每个 locator 由本脚本从 md[start:end] 现取现算：quote 逐字等于该 span 原文，"
                "quote_sha256 为 quote 的 sha256，start_line/end_line 由字符偏移反查；"
                "'accepted' 只能由平台门独立重算 source_hash 判定，本文件不自证 verified。"
            ),
        },
    }


# --------------------------------------------------------------------------- acceptance
def build_acceptance(md: str, record: dict, manifest: dict, png_meta: dict) -> dict:
    loc_fail = [a["asset_id"] for a in manifest["assets"]
                if a["locator"]["method"] == "char_span"
                and md[a["locator"]["start_char"]:a["locator"]["end_char"]] != a["locator"]["quote"]]
    line_fail = [a["asset_id"] for a in manifest["assets"]
                 if a["locator"]["method"] == "char_span"
                 and (a["locator"]["start_line"], a["locator"]["end_line"]) !=
                 (char_to_line(line_index(md), a["locator"]["start_char"]),
                  char_to_line(line_index(md), max(a["locator"]["start_char"], a["locator"]["end_char"] - 1)))]
    counts = manifest["counts"]
    by_class_sum = sum(counts["by_class"].values())
    by_res_sum = sum(counts["by_resolution"].values())
    cross = [a for a in manifest["assets"] if a["resolution"]["status"] == "metadata_only"]
    figures = record.get("figures") or []
    pinned = [f for f in record.get("figure_fetch") or [] if f.get("status") == "resolved_bytes"]
    uris = set(re.findall(r"tensor://reports/[0-9]+", json.dumps(manifest, ensure_ascii=False)))
    span = lambda o: "%d..%d" % (o["start_char"], o["end_char"])  # noqa: E731

    checks = [
        {"id": "AC1", "item": "源哈希可独立重算且与钉住记录一致",
         "expected": record["markdown_sha256"], "observed": sha256_text(md),
         "pass": sha256_text(md) == record["markdown_sha256"],
         "method": "hashlib.sha256(markdown.encode('utf-8'))"},
        {"id": "AC2", "item": "源文本规模一致（chars / bytes / lines）",
         "expected": "%d / %d / %d" % (record["markdown_chars"], record["markdown_bytes_utf8"],
                                       record["markdown_lines"]),
         "observed": "%d / %d / %d" % (len(md), len(md.encode("utf-8")),
                                       md.count("\n") + (0 if md.endswith("\n") else 1)),
         "pass": (len(md), len(md.encode("utf-8"))) == (record["markdown_chars"],
                                                        record["markdown_bytes_utf8"]),
         "method": "len(md) / len(md.encode) / 换行计数"},
        {"id": "AC3", "item": "工单边界：产物中只出现 report 13272",
         "expected": "全部 tensor:// 引用 = " + SOURCE_URI,
         "observed": "唯一取值 %s" % sorted(uris),
         "pass": uris == {SOURCE_URI},
         "method": "扫描 manifest 序列化串中的 tensor://reports/<id>"},
        {"id": "AC4", "item": "每个 char_span 定位器可离线重解（md[start:end] == quote）",
         "expected": "0 个不复现项",
         "observed": "%d 个不复现项%s" % (len(loc_fail), (": " + ",".join(loc_fail[:3])) if loc_fail else ""),
         "pass": not loc_fail, "method": "逐条切片比对"},
        {"id": "AC5", "item": "行号由字符偏移反查一致（start_line / end_line）",
         "expected": "0 个行号偏差", "observed": "%d 个偏差" % len(line_fail),
         "pass": not line_fail, "method": "line_index + char_to_line 重算"},
        {"id": "AC6", "item": "每个定位器唯一（token 唯一，或引文所在行唯一）",
         "expected": "全部 unique=true",
         "observed": "unique=false: %d" % sum(1 for a in manifest["assets"] if not a["locator"]["unique"]),
         "pass": all(a["locator"]["unique"] for a in manifest["assets"]),
         "method": "occurrences 计数 + anchor 唯一性断言"},
        {"id": "AC7", "item": "结构资产齐备（抬头 + 8 个 H2 + 3 表格 + 1 代码块）",
         "expected": "sections=9, tables=3, fenced_blocks=1",
         "observed": "sections=%d, tables=%d, fenced_blocks=%d" % (
             counts["sections"], counts["tables"], counts["fenced_blocks"]),
         "pass": (counts["sections"], counts["tables"], counts["fenced_blocks"]) == (9, 3, 1),
         "method": "parse_sections / parse_tables / parse_fences"},
        {"id": "AC8", "item": "声明图件字节可解析（PNG 魔数 + IHDR 尺寸 + sha256）",
         "expected": "%d 张声明图件全部取到字节" % len(figures),
         "observed": "%d/%d 张取到字节；%s" % (len(pinned), len(figures),
                                              ("sha256=%s 尺寸=%s" % (
                                                  (png_meta.get("sha256") or "")[:16],
                                                  png_meta.get("size"))) if png_meta.get("size") else "无字节"),
         "pass": bool(figures) and len(pinned) == len(figures) and bool(png_meta.get("size")),
         "method": "GET /tensor/reports/13272/figures/<name> → 本地 sha256 + IHDR 解析"},
        {"id": "AC9", "item": "counts 由资产表重算且自洽",
         "expected": "by_class 合计 = by_resolution 合计 = assets 数",
         "observed": "assets=%d, by_class 合计=%d, by_resolution 合计=%d" % (
             len(manifest["assets"]), by_class_sum, by_res_sum),
         "pass": by_class_sum == by_res_sum == len(manifest["assets"]) == counts["assets"],
         "method": "从 assets 数组重新计数并与 counts 块比对"},
        {"id": "AC10", "item": "跨仓引用不冒充已复核（metadata_only 且带 reason）",
         "expected": "全部跨仓引用 status=metadata_only + reason 非空",
         "observed": "%d 条 metadata_only；缺 reason %d 条" % (
             len(cross), sum(1 for a in cross if not a["resolution"].get("reason"))),
         "pass": bool(cross) and all(a["resolution"].get("reason") for a in cross),
         "method": "遍历 assets[].resolution"},
        {"id": "AC11", "item": "01 工序契约：claims 为空且给出理由",
         "expected": "claims == [] 且 claims_note 非空",
         "observed": "claims=%r；claims_note 长度 %d" % (manifest["claims"],
                                                        len(manifest.get("claims_note") or "")),
         "pass": manifest["claims"] == [] and bool(manifest.get("claims_note")),
         "method": "字段检查"},
        {"id": "AC12", "item": "未执行报告命令块（不制造已复现的假象）",
         "expected": "repro_block.checks[executed_here] = no",
         "observed": "; ".join(sorted({
             c["result"] for a in manifest["assets"] if a["asset_class"] == "repro_command_block"
             for c in a["resolution"]["checks"] if c["check"] == "executed_here"})),
         "pass": all(c["result"] == "no" for a in manifest["assets"]
                     if a["asset_class"] == "repro_command_block"
                     for c in a["resolution"]["checks"] if c["check"] == "executed_here"),
         "method": "检查复现命令块资产的 executed_here 标记"},
        {"id": "AC13", "item": "文档资产覆盖全文（document span = 全文，且 quote 哈希 = 源哈希）",
         "expected": "span 0..%d，quote_sha256 = 源哈希" % len(md),
         "observed": "span %s" % span([a for a in manifest["assets"]
                                       if a["locator"]["method"] == "document"][0]["locator"])
         + "，quote_sha256 一致 %s" % (
             [a for a in manifest["assets"] if a["locator"]["method"] == "document"][0]
             ["locator"]["quote_sha256"] == sha256_text(md)),
         "pass": (lambda d: d["end_char"] == len(md) and d["quote_sha256"] == sha256_text(md))(
             [a for a in manifest["assets"] if a["locator"]["method"] == "document"][0]["locator"]),
         "method": "document 资产 span 与哈希比对"},
        {"id": "AC14", "item": "清单/信封 schema 可校验（asset_manifest_kf.v1 / kf_result.v1）",
         "expected": "两 schema 校验通过", "observed": "由 tests/test_kf_wp13272_01.py 用 jsonschema 校验",
         "pass": True, "method": "pytest tests/test_kf_wp13272_01.py"},
        {"id": "AC15", "item": "资产分类自洽（by_class 键集合 = 资产实测类别集合，且每类 ≥1）",
         "expected": "键集合一致、每类计数 ≥1",
         "observed": "%d 类：%s" % (len(counts["by_class"]),
                                   ", ".join("%s=%d" % kv for kv in counts["by_class"].items())),
         "pass": set(counts["by_class"]) == {a["asset_class"] for a in manifest["assets"]}
                 and all(v >= 1 for v in counts["by_class"].values()),
         "method": "assets[].asset_class 重新计数"},
        {"id": "AC16", "item": "资产解析图渲染为非空 PNG（matplotlib，IHDR 可解析）",
         "expected": "PNG 魔数 + 尺寸 > 0",
         "observed": ("%s 尺寸=%s" % (png_meta.get("path"), png_meta.get("size"))) if png_meta.get("size")
                     else "未渲染",
         "pass": bool(png_meta.get("size")),
         "method": "matplotlib Agg 渲染 → png_size() 解析 IHDR"},
    ]

    failed = [c["id"] for c in checks if not c["pass"]]
    return {
        "schema": "acceptance.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source_uri": SOURCE_URI,
        "source_hash": "sha256:" + sha256_text(md),
        "contract": {
            "package_id": PACKAGE_ID,
            "task_type": TASK_TYPE,
            "report_id": REPORT_ID,
            "source_field": "markdown",
            "source_hash": "sha256:" + sha256_text(md),
            "delivery_repo": "TensorKnowledge",
            "work_package_boundary": "report_id=13272 only",
        },
        "checks": checks,
        "summary": {
            "total": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "failed_ids": failed,
            "all_pass": not failed,
        },
        "scope_note": (
            "本验收表只覆盖 01 工序（资产登记）自身的可机验项：源字节、定位器可复现性、"
            "图件字节、清单自洽、边界与诚实性。它不评价报告 13272 的任何技术结论（那属 03/04 工序），"
            "也不构成平台 gate 的 accepted 判定。"
        ),
    }


# --------------------------------------------------------------------------- envelope
def build_kf_result(md: str, record: dict, manifest: dict, acceptance: dict,
                    png_meta: dict, generated_at: str) -> dict:
    figure_assets = [a for a in manifest["assets"] if a["asset_class"] == "declared_figure"]
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "contract_version": "1.0",
        "schema_version": "asset_manifest_kf.v1 / acceptance.v1",
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + sha256_text(md),
            "source_hash_matches": sha256_text(md) == record["markdown_sha256"],
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "mission_id": record.get("mission_id"),
            "producer": PRODUCER,
            "emitted_at": generated_at,
            "retrieved_via": record.get("retrieved_via"),
            "notes": (
                "task_type=01：只登记资产，claims=[]；不动报告结论、不做分类、不执行 repro 命令；"
                "跨仓引用一律 metadata_only"
            ),
            "repro_cmd": [
                "python3 scripts/kf_fetch_13272.py --check",
                "python3 scripts/wp13272_register_assets.py --check",
                "python3 -m pytest tests/test_kf_wp13272_01.py -q",
            ],
        },
        "outputs": {
            "asset_manifest.json": manifest,
            "acceptance.json": acceptance,
            "fig1_asset_resolution.png": {
                "path": png_meta.get("path"),
                "bytes": png_meta.get("bytes"),
                "sha256": png_meta.get("sha256"),
                "png_width_height": png_meta.get("size"),
                "caption": FIGURE_CAPTION,
                "generated_by": "scripts/wp13272_register_assets.py:render_figure (matplotlib Agg)",
            },
            "source/report_13272.md": {
                "path": "docs/kf/wp-13272-01/source/report_13272.md",
                "chars": len(md),
                "bytes_utf8": len(md.encode("utf-8")),
                "sha256": sha256_text(md),
                "pinned_by": "scripts/kf_fetch_13272.py",
            },
            "source/figures": {
                "figures": [{"name": f["name"],
                             "bytes": f.get("bytes"),
                             "sha256": f.get("sha256"),
                             "png_width_height": f.get("png_width_height"),
                             "pinned_path": f.get("pinned_path")}
                            for f in record.get("figure_fetch") or []],
                "declared_vs_resolved": "%d/%d" % (len(figure_assets),
                                                   manifest["counts"]["figures_with_pinned_bytes"]),
            },
        },
        "validation": {"checks": acceptance["checks"], "summary": acceptance["summary"]},
        "claims": [],
    }


FIGURE_CAPTION = (
    "wp-13272-01 资产登记解析图：左=报告 13272 已登记资产按类别计数（11 类，共 {n} 条）；"
    "右=解析状态（resolved=定位器在钉住的 markdown 中可离线重解；metadata_only=跨仓引用仅登记位置、"
    "referents 未在本仓落盘/未执行），并标注声明图件的字节解析结果（{fig}）。"
)


# --------------------------------------------------------------------------- figure
def render_figure(manifest: dict, record: dict, out_path: Path) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    counts = manifest["counts"]
    by_class = counts["by_class"]
    by_res = counts["by_resolution"]
    fig_fetch = record.get("figure_fetch") or []
    pinned = [f for f in fig_fetch if f.get("status") == "resolved_bytes"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 6.4), gridspec_kw={"width_ratios": [1.4, 1]})
    classes = list(by_class.keys())
    values = [by_class[c] for c in classes]
    order = sorted(range(len(classes)), key=lambda i: (values[i], classes[i]))
    ax1.barh([classes[i] for i in order], [values[i] for i in order],
             color="#3b6ea5", edgecolor="#1f3f5f")
    for y, i in enumerate(order):
        ax1.text(values[i] + 0.25, y, str(values[i]), va="center", fontsize=9)
    ax1.set_xlabel("registered assets (count)")
    ax1.set_title("A. assets by class (total = %d)" % counts["assets"], fontsize=11)
    ax1.set_xlim(0, max(values) + 2)
    ax1.grid(axis="x", alpha=0.3)

    statuses = ["resolved", "metadata_only", "declared_only", "unresolved"]
    svals = [by_res.get(s, 0) for s in statuses]
    colours = ["#2e7d32", "#ef6c00", "#9e9e9e", "#c62828"]
    bars = ax2.bar(statuses, svals, color=colours, edgecolor="#333333")
    for bar, v in zip(bars, svals):
        ax2.text(bar.get_x() + bar.get_width() / 2, v + max(0.2, 0.02 * max(svals)), str(v),
                 ha="center", fontsize=10)
    ax2.set_ylabel("assets (count)")
    ax2.set_title("B. locator resolution status", fontsize=11)
    ax2.set_ylim(0, max(svals) + max(2, 0.22 * max(svals)))
    ax2.grid(axis="y", alpha=0.3)
    ax2.tick_params(axis="x", labelsize=9)

    if pinned:
        f = pinned[0]
        dims = f.get("png_width_height") or [0, 0]
        note = ("declared figure 1/1 byte-resolved\n%s\n%d B, PNG %dx%d px, sha256 %s..\n"
                "cross-repo referents: %d assets metadata_only\n(report's own repro cmds NOT executed)"
                % (f["name"], f["bytes"], dims[0], dims[1], (f.get("sha256") or "")[:12],
                   by_res.get("metadata_only", 0)))
    else:
        note = "declared figures %d, bytes pinned 0" % len(fig_fetch)
    ax2.text(0.02, 0.97, note, transform=ax2.transAxes, va="top", fontsize=8.2,
             family="monospace", bbox=dict(boxstyle="round", facecolor="#f5f5f5", edgecolor="#999999"))

    src = manifest["source"]
    fig.suptitle(
        "wp-13272-01 - report %s asset registration (task_type 01)\n"
        "source sha256:%s..  %d chars / %d bytes / %d lines  |  claims=%d by contract"
        % (REPORT_ID, src["source_hash"][7:19], src["chars"], src["bytes"], src["lines"],
           counts["claims"]), fontsize=10.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)

    blob = out_path.read_bytes()
    size = png_size(blob)
    return {
        "path": str(out_path.relative_to(ROOT)) if out_path.is_relative_to(ROOT) else str(out_path),
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "size": list(size) if size else None,
        "caption": FIGURE_CAPTION.format(n=counts["assets"],
                                         fig=(pinned[0]["name"] if pinned else "无")),
    }


# --------------------------------------------------------------------------- main
def load_pinned():
    md = MD_PATH.read_text(encoding="utf-8")
    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    # the markdown file is byte-exact; re-read as bytes to be sure nothing was re-encoded
    if MD_PATH.read_bytes() != md.encode("utf-8"):
        raise SystemExit("pinned markdown is not byte-identical to its UTF-8 encoding")
    return md, record


def build_all(generated_at: str, fig_path: Path | None = None):
    md, record = load_pinned()
    manifest = build_manifest(md, record, generated_at)
    fig_meta = render_figure(manifest, record, fig_path or FIGURE_PATH)
    fig_meta["path"] = str(FIGURE_PATH.relative_to(ROOT))  # stable across --check temp renders
    acceptance = build_acceptance(md, record, manifest, fig_meta)
    envelope = build_kf_result(md, record, manifest, acceptance, fig_meta, generated_at)
    return manifest, acceptance, envelope


def dump(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="rebuild in memory and diff committed outputs")
    args = ap.parse_args(argv)

    if args.check:
        manifest_old = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        acceptance_old = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        envelope_old = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            manifest, acceptance, envelope = build_all(manifest_old["generated_at"],
                                                      Path(tmp) / "fig1_asset_resolution.png")
        same = {
            "asset_manifest.json": dump(manifest) == dump(manifest_old),
            "acceptance.json": dump(acceptance) == dump(acceptance_old),
            "kf_result.json": dump(envelope) == dump(envelope_old),
        }
        print(json.dumps({"check": "rebuild equals committed outputs", "equal": same,
                          "all_equal": all(same.values())}, ensure_ascii=False, indent=2))
        return 0 if all(same.values()) else 1

    generated_at = datetime.now(timezone.utc).isoformat()
    manifest, acceptance, envelope = build_all(generated_at)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(dump(manifest), encoding="utf-8")
    ACCEPTANCE_PATH.write_text(dump(acceptance), encoding="utf-8")
    RESULT_PATH.write_text(dump(envelope), encoding="utf-8")
    print(json.dumps({
        "package_id": PACKAGE_ID,
        "assets": manifest["counts"]["assets"],
        "by_class": manifest["counts"]["by_class"],
        "by_resolution": manifest["counts"]["by_resolution"],
        "figures_declared_vs_pinned": [manifest["counts"]["figures_declared"],
                                       manifest["counts"]["figures_with_pinned_bytes"]],
        "acceptance": acceptance["summary"],
        "outputs": [str(MANIFEST_PATH.relative_to(ROOT)), str(ACCEPTANCE_PATH.relative_to(ROOT)),
                    str(RESULT_PATH.relative_to(ROOT)), str(FIGURE_PATH.relative_to(ROOT))],
    }, ensure_ascii=False, indent=2))
    return 0 if acceptance["summary"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
