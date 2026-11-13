#!/usr/bin/env python3
"""Work package wp-9645-01 (task_type=01-asset-registration) for report_id=9645.

Scope guard
-----------
* Touches report_id=9645 and nothing else (no other report is read or written).
* Registration only: no knowledge extraction, no claim generation, no verification
  marks. `claims` is an empty array (allowed by the envelope schema for task_type 01).
* Every locator quote is a *slice of the fetched markdown*, never retyped, so a quote
  cannot drift from the source; uniqueness and span equality are asserted, not assumed.

Modes
-----
  build    login -> GET /tensor/reports/9645 -> hash check -> emit manifest/result
  verify   offline re-check of the emitted artifacts against the stored source copy
  figure   render asset-coverage png (evidence for the platform report)
  report   render docs/kf/wp-9645-01/report_body.md from the emitted artifacts

Usage:
  python3 scripts/kf/wp_9645_01_register.py build verify figure report
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-9645-01"
REPORT_ID = "9645"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/9645"
SOURCE_FIELD = "markdown"
# Values taken from the work-package contract (input block), not from the report body.
EXPECTED_HASH = "a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00"
EXPECTED_CHARS = 11824
CONTRACT_TITLE = "IN101-N09 ISO 19906 冰压设计分项系数目标可靠度反标定（成熟化）"
CONTRACT_SCENARIO = "ice_partial_factors_target_inverse"

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
SCHEMA_LOCAL = OUT_DIR / "asset_manifest.schema.json"
SCHEMA_ENVELOPE = REPO / "schemas" / "kf_result.v1.schema.json"

MANIFEST = OUT_DIR / "asset_manifest.json"
RESULT = OUT_DIR / "kf_result.json"
LOCATOR_CHECK = OUT_DIR / "locator_check.json"
SOURCE_COPY = OUT_DIR / "source.md"
SHA_TXT = OUT_DIR / "sha256.txt"
REPORT_BODY = OUT_DIR / "report_body.md"
FIGURE_PNG = OUT_DIR / "asset_coverage.png"

RESOLVED = "resolved_in_source"
UNRESOLVED = "referenced_unresolved"
ABSENT = "declared_absent"


# ------------------------------------------------------------------ platform I/O
def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def login():
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, pw = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    try:
        d = _req(base + "/auth/login", data=json.dumps({"username": user, "password": pw}).encode())
    except urllib.error.HTTPError:
        body = urllib.parse.urlencode({"username": user, "password": pw}).encode()
        d = _req(base + "/auth/login", data=body, ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return base, tok


def fetch_report(base, token):
    d = _req(base + "/tensor/reports/%s" % REPORT_ID, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str) or not md:
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


def probe_artifacts(base, token):
    """Best-effort: is there any platform-side artifact/attachment listing for 9645?"""
    out = {}
    for path in ("/tensor/reports/%s/artifacts" % REPORT_ID, "/tensor/artifacts?report_id=%s" % REPORT_ID):
        try:
            d = _req(base + path, token)
            out[path] = {"status": "ok", "shape": type(d).__name__, "n": len(d) if hasattr(d, "__len__") else None}
        except urllib.error.HTTPError as e:
            out[path] = {"status": "http_%s" % e.code}
        except Exception as e:  # noqa: BLE001 - record, never fabricate
            out[path] = {"status": "error", "detail": type(e).__name__}
    return out


def probe_record_figures(meta):
    """Figures listed in the report record: metadata only, or also a byte payload?"""
    figs, any_payload = [], False
    for f in meta.get("figures") or []:
        payload = f.get("png_base64") or ""
        any_payload = any_payload or bool(payload)
        figs.append(
            {
                "name": f.get("name"),
                "caption": f.get("caption"),
                "keys": sorted(f.keys()),
                "payload_present": bool(payload),
            }
        )
    return figs, any_payload


def probe_local_availability():
    """Is the producing code / benchmark present in THIS worktree? (checked, not assumed)"""
    bench = REPO / "benchmarks" / "iso19906_partial_factors"
    tensorphysics = REPO / "src" / "tensorphysics"
    return {
        "benchmarks/iso19906_partial_factors": bench.exists(),
        "src/tensorphysics": tensorphysics.exists(),
        "solver_module_ice_partial_factors": (tensorphysics / "ice_partial_factors.py").exists(),
    }


# ---------------------------------------------------------------- span helpers
def line_index(md):
    starts, off = [], 0
    for line in md.split("\n"):
        starts.append(off)
        off += len(line) + 1
    return starts


def line_no(starts, char_pos):
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= char_pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1  # 1-based


def _line_bounds(md, pos):
    start = md.rfind("\n", 0, pos) + 1
    nl = md.find("\n", start)
    end = len(md) if nl == -1 else nl
    return start, end


def _extend_table(md, anchor_start):
    """From the anchor line, absorb the following table block (blank line allowed after a caption)."""
    _, line_end = _line_bounds(md, anchor_start)
    end = line_end
    i = line_end + 1 if line_end < len(md) else len(md)
    saw_row = False
    while i < len(md):
        nl = md.find("\n", i)
        row_end = len(md) if nl == -1 else nl
        line = md[i:row_end]
        if line.startswith("|"):
            saw_row = True
            end = row_end
        elif line.strip() == "" and not saw_row:
            pass  # tolerate the blank line between a bold caption and its table
        else:
            break
        if nl == -1:
            break
        i = nl + 1
    return end


def _extend_para(md, anchor_start):
    _, line_end = _line_bounds(md, anchor_start)
    end = line_end
    i = line_end + 1 if line_end < len(md) else len(md)
    while i < len(md):
        nl = md.find("\n", i)
        row_end = len(md) if nl == -1 else nl
        if md[i:row_end].strip() == "":
            break
        end = row_end
        if nl == -1:
            break
        i = nl + 1
    return end


def make_locator(md, starts, anchor, kind):
    n = md.count(anchor)
    if n != 1:
        raise SystemExit("anchor is not unique (count=%d): %r" % (n, anchor))
    pos = md.find(anchor)
    if kind == "document":
        start, end = 0, len(md)
        quote = md.split("\n")[0]
        check = md.startswith(quote)
        start_line, end_line = 1, md.count("\n") + 1
    elif kind == "line":
        start, _ = _line_bounds(md, pos)
        _, end = _line_bounds(md, pos)
        quote = md[start:end]
        check = md.count(quote) == 1
        start_line, end_line = line_no(starts, start), line_no(starts, max(start, end - 1))
    elif kind == "table":
        start, _ = _line_bounds(md, pos)
        end = _extend_table(md, start)
        quote = md[start:end]
        check = md.count(quote) == 1
        start_line, end_line = line_no(starts, start), line_no(starts, max(start, end - 1))
    elif kind == "token":
        start, end = pos, pos + len(anchor)
        quote = md[start:end]
        check = md.count(quote) == 1
        start_line, end_line = line_no(starts, start), line_no(starts, max(start, end - 1))
    elif kind == "para":
        start, _ = _line_bounds(md, pos)
        end = _extend_para(md, start)
        quote = md[start:end]
        check = md.count(quote) == 1
        start_line, end_line = line_no(starts, start), line_no(starts, max(start, end - 1))
    else:  # pragma: no cover
        raise SystemExit("unknown locator kind %r" % kind)
    if not check:
        raise SystemExit("locator failed self-check for anchor %r" % anchor)
    return {
        "method": "document" if kind == "document" else "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": start_line,
        "end_line": end_line,
        "quote": quote,
        "unique": True,
        "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
    }


# ---------------------------------------------------------------- asset specs
# (asset_class, label, in_report_section, anchor, kind, resolution, note)
SPECS = [
    # ---- document + structure
    ("report_markdown", "报告正文（markdown 全文，注册的唯一源资产）", "(document)",
     "# IN101-N09", "document", RESOLVED,
     "源资产本体：sha256 见 source.hash；本清单所有 locator 的字符偏移均相对此文本。"),
    ("section_heading", "一级标题行（含仓库 / 模块 / 设计格式 / 目标 beta / 前序节点元信息）", "(document)",
     "# IN101-N09", "line", RESOLVED,
     "标题行本身是元信息载体（TensorPhysics、tensorphysics.ice_partial_factors、beta_T=4.00、IN13-W3-N10）。"),
    ("section_heading", "§① 案例介绍（物理背景 / 参数表）", "①",
     "## ① 案例介绍（物理背景 / 参数表）", "line", RESOLVED, "章节定位锚点。"),
    ("section_heading", "§② 怎么做的（方法 / 流程 / 工具链）", "②",
     "## ② 怎么做的（方法 / 流程 / 工具链）", "line", RESOLVED, "章节定位锚点。"),
    ("section_heading", "§③ 计算结果", "③", "## ③ 计算结果", "line", RESOLVED, "章节定位锚点。"),
    ("section_heading", "§④ 结果图", "④", "## ④ 结果图", "line", RESOLVED, "章节定位锚点。"),
    ("section_heading", "§⑤ 注意点（坑 / 局限 / 适用范围）", "⑤",
     "## ⑤ 注意点（坑 / 局限 / 适用范围）", "line", RESOLVED, "章节定位锚点。"),
    ("section_heading", "§⑥ 误差判定（逐项 vs 基准，显式回答是否 <3 %）", "⑥",
     "## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3 %）", "line", RESOLVED, "章节定位锚点。"),
    ("section_heading", "审计链（结果 JSON / 机器判据 / 求解器 / 复现命令）", "审计链",
     "## 审计链", "line", RESOLVED, "章节定位锚点。"),
    # ---- tables
    ("machine_criteria_table", "机器判据表（a–e 五条判据及 PASS 结果）", "标题后",
     "| 机器判据 | 结果 |", "table", RESOLVED,
     "判据名与 PASS 结果逐字可定位；本工序不改写判据结论。"),
    ("criterion_summary", "判据汇总行（5/5 通过）", "标题后",
     "**判据汇总** 5/5 通过", "line", RESOLVED,
     "汇总陈述，注册以固定原文位置；不据此打 verified 标。"),
    ("parameter_table", "输入参数表（p0 / ex / A0 / CoV / F_k / R_k / rho_ln p,ln A / sigma_ln F）", "①",
     "| 参数 | 取值 | 说明 |", "table", RESOLVED,
     "参数名与取值逐字可定位；本工序不做提取、不做量纲复核。"),
    ("table", "表 1 反问题解（gamma_f* / psi* / kappa* / F* / R* / 达到 beta / 迭代数 / 条件数 / 方向余弦）", "③",
     "**表 1 反问题解**", "table", RESOLVED, "反问题解表。"),
    ("table", "表 2 FORM 的四条独立验证（判据 a）", "③",
     "**表 2 FORM 的四条独立验证（判据 a）**", "table", RESOLVED,
     "FORM vs 解析 / 重要性抽样 / 粗 MC / Rao–Blackwell 四条验证面。"),
    ("table", "表 3 beta 敏感性（判据 c）：伴随解析导数 vs 中心差分", "③",
     "**表 3 β 敏感性（判据 c）：包络定理解析导数 vs 中心差分**", "table", RESOLVED,
     "伴随导数 vs 有限差分对照表。"),
    ("table", "表 4 与 ISO 19906 表格分项系数偏差（判据 d，10 对）", "③",
     "**表 4 与 ISO 19906 表格分项系数偏差（判据 d）**", "table", RESOLVED,
     "表格分项系数对逐行偏差表。"),
    ("table", "表 5 不保守算例（偏差 >15 % 且 kappa_table<kappa*）", "③",
     "**表 5 不保守算例（偏差 >15 % 且 $\\kappa_{table}<\\kappa^*$）**", "table", RESOLVED,
     "不保守算例的 beta / delta beta / P_f 倍数 / R_k 需求表。"),
    ("table", "表 6 负控（判据 e）：忽略 p–A 负相关", "③",
     "**表 6 负控（判据 e）：忽略 p–A 负相关**", "table", RESOLVED, "负控对照表。"),
    ("table", "表 7 beta_T 敏感性", "③",
     "**表 7 $\\beta_T$ 敏感性**", "table", RESOLVED, "目标可靠度敏感性表。"),
    ("table", "表 8 模型参数敏感性 d beta / d theta（在 kappa* 处，中心差分）", "③",
     "**表 8 模型参数敏感性 $\\partial\\beta/\\partial\\theta$（在 $\\kappa^*$ 处，中心差分）**", "table", RESOLVED,
     "模型参数敏感性表。"),
    ("table", "⑥ 误差判定表（关键量 / 基准 / 误差 / 是否 <3 %）", "⑥",
     "| 关键量 | 基准 | 误差 | <3 % ? |", "table", RESOLVED, "误差判定逐项表。"),
    ("statement", "⑥ 结论段（FORM 与解析值 / IS 一致性、反问题残差、伴随导数、粗 MC 噪声说明）", "⑥",
     "**结论**：FORM 与解析值", "para", RESOLVED,
     "结论陈述，注册以固定原文位置；是否成立由平台门裁定，本工序不打 verified 标。"),
    # ---- figures (markdown image declarations; payloads outside this package)
    ("figure_reference", "图 1 联合 p–A 状态（fig1_pa_joint.png）", "④",
     "![fig1](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig1_pa_joint.png)",
     "line", UNRESOLVED,
     "markdown 内为绝对路径（指向产出任务 8350 的工作树），PNG 字节不在本仓、也不在报告记录 figures[] 的载荷内，故登记引用、未解析字节。"),
    ("figure_reference", "图 2 beta vs kappa（fig2_beta_vs_kappa.png）", "④",
     "![fig2](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig2_beta_vs_kappa.png)",
     "line", UNRESOLVED, "同上：仅登记引用，未取字节。"),
    ("figure_reference", "图 3 Newton 收敛与劈分曲线（fig3_newton.png）", "④",
     "![fig3](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig3_newton.png)",
     "line", UNRESOLVED, "同上：仅登记引用，未取字节。"),
    ("figure_reference", "图 4 与 ISO 表格分项系数逐项偏差图（fig4_iso_deviations.png）", "④",
     "![fig4](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig4_iso_deviations.png)",
     "line", UNRESOLVED, "同上：仅登记引用，未取字节。"),
    ("figure_reference", "图 5 负控（fig5_negative_control.png）", "④",
     "![fig5](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig5_negative_control.png)",
     "line", UNRESOLVED, "同上：仅登记引用，未取字节。"),
    ("figure_reference", "图 6 灵敏度（fig6_sensitivity.png）", "④",
     "![fig6](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig6_sensitivity.png)",
     "line", UNRESOLVED, "同上：仅登记引用，未取字节。"),
    # ---- code / data artifacts
    ("data_artifact_reference", "结果 JSON：in101_n09_results.json（报告全部数字的唯一来源）", "审计链",
     "/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/in101_n09_results.json",
     "token", UNRESOLVED,
     "绝对路径位于产出任务 8350 的工作树内，不在本仓检出范围内；按边界未跨任务取件，也未解析其内容。"),
    ("record_field_reference", "结果 JSON 判据字段 machine_criteria / criteria_summary", "审计链",
     "`machine_criteria` 5 条，`criteria_summary`", "token", UNRESOLVED,
     "字段名与其值取自报告转述；原 JSON 未取件，故字段值的机器可读副本属未解析。"),
    ("code_reference", "冰区分项系数模块 tensorphysics.ice_partial_factors", "标题 / ②",
     "`tensorphysics.ice_partial_factors`", "token", UNRESOLVED,
     "属 TensorPhysics 仓；本检出为 TensorKnowledge，本地无该模块（见 source.local_availability 实测探针）。"),
    ("code_reference", "求解器 tensorphysics.structural.reliability（FORM/HL-RF、SORM、IS、MC）", "审计链",
     "`tensorphysics.structural.reliability`", "token", UNRESOLVED,
     "同上：跨仓引用，本检出不可解析。"),
    ("code_reference", "分布 / Nataf 模块 tensorphysics.structural.distributions", "审计链",
     "`tensorphysics.structural.distributions`", "token", UNRESOLVED,
     "同上：跨仓引用，本检出不可解析。"),
    ("code_reference", "脚本 p_area_joint.py（联合 p–A 状态）", "②",
     "`p_area_joint.py`", "token", UNRESOLVED,
     "文件不在本检出（benchmarks/ 下无 iso19906 目录，见 source.local_availability 实测探针）。"),
    ("code_reference", "脚本 target_reliability_inverse.py（两方程两未知量反问题）", "②",
     "`target_reliability_inverse.py`", "token", UNRESOLVED, "同上：文件不在本检出。"),
    ("code_reference", "入口函数 run_study()（结果 JSON 直出）", "审计链",
     "`run_study()` 直出", "token", UNRESOLVED,
     "函数定义不在本检出；只登记调用点。"),
    ("repro_command", "复现命令 PYTHONPATH=src python3 benchmarks/iso19906_partial_factors/run_in101_n09.py", "审计链",
     "PYTHONPATH=src python3 benchmarks/iso19906_partial_factors/run_in101_n09.py", "token", UNRESOLVED,
     "命令原文登记；本检出不具备该 benchmark 与依赖模块，故本次未执行（不声称可复现）。"),
    # ---- external standards / prior work
    ("external_standard_table", "ISO 19906 Annex A.2 × A.3 分项系数表（9 对）", "⑤/⑥",
     "ISO 19906 Annex A 正文不在工作树内", "token", ABSENT,
     "报告自述该正文不在工作树内，且 A.2/A.3 为二次文献转录（见 source_tier 资产）；本工序不补录、不推断表格值。"),
    ("provenance_flag", "出处等级标记 source_tier=secondary, primary_source_verified=False", "⑤",
     "`source_tier=secondary`, `primary_source_verified=False`", "token", RESOLVED,
     "出处等级标记本身在原文中可逐字定位；它声明所引 ISO 表为二次来源，故由该表得出的裁决为 conditional。"),
    ("external_standard_reference", "JCSS/ISO 2394 设计值劈分约定", "②/⑤",
     "JCSS/ISO 2394 设计值劈分（荷载分项系数 = FORM 设计点作用/特征作用）", "token", UNRESOLVED,
     "规范条文本身不在工作树内，仅登记报告对该约定的引用位置；劈分约定未被本工序核验。"),
    ("repo_reference", "产出仓 TensorPhysics", "标题",
     "**仓库** TensorPhysics", "token", UNRESOLVED,
     "跨仓：本检出为 TensorKnowledge，未取 TensorPhysics 代码。"),
    ("prior_node_reference", "前序节点 IN13-W3-N10（plate-stress 极限状态、单参数反问题）", "标题",
     "IN13-W3-N10", "token", UNRESOLVED, "前序节点产物未在本包范围内，仅登记引用。"),
    # ---- numeric anchors (locators only, no interpretation)
    ("numeric_anchor", "锚点 kappa* = 1.431318（表 1 行）", "③",
     "| $\\kappa^*=\\gamma_f^*\\psi^*$ | **1.431318** |", "line", RESOLVED,
     "数值锚点：为下游工序提供逐字可解析的定位，不构成对数值正确性的判定。"),
    ("numeric_anchor", "锚点 达到的 beta = 4.000000000000（表 1 行）", "③",
     "| 达到的 $\\beta$ | 4.000000000000 |", "line", RESOLVED, "同上：仅定位。"),
    ("numeric_anchor", "锚点 负控 delta gamma_f = +28.90 %（表 6 后陈述）", "③",
     "$\\Delta\\gamma_f^*$ = +28.90 %", "line", RESOLVED, "同上：仅定位。"),
    # ---- design format notation
    ("design_format", "设计格式 gamma_f * F_k <= R_k / psi, kappa = gamma_f * psi", "标题",
     "`gamma_f * F_k <= R_k / psi,  kappa = gamma_f * psi`", "token", RESOLVED,
     "设计格式原文（含双空格），供下游工序逐字引用。"),
]


# ---------------------------------------------------------------- build
def build():
    base, token = login()
    meta, md = fetch_report(base, token)
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit("SOURCE HASH MISMATCH: contract=%s actual=%s" % (EXPECTED_HASH, digest))
    if len(md) != EXPECTED_CHARS:
        raise SystemExit("SOURCE CHAR COUNT MISMATCH: contract=%d actual=%d" % (EXPECTED_CHARS, len(md)))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_text(md, encoding="utf-8")
    SHA_TXT.write_text(
        "sha256  %s\nfield   %s\nchars   %d\nbytes   %d\nreport  %s\n"
        % (digest, SOURCE_FIELD, len(md), len(raw), REPORT_ID),
        encoding="utf-8",
    )

    starts = line_index(md)
    figs, any_payload = probe_record_figures(meta)
    local = probe_local_availability()
    probes = probe_artifacts(base, token)
    fig_by_name = {f["name"]: f for f in figs}

    assets, ids = [], set()

    for spec in SPECS:
        asset_class, label, section, anchor, kind, resolution, note = spec
        loc = make_locator(md, starts, anchor, kind)
        aid = "A%02d" % (len(assets) + 1)
        if aid in ids:
            raise SystemExit("duplicate asset_id %s" % aid)
        ids.add(aid)
        asset = {
            "asset_id": aid,
            "asset_class": asset_class,
            "label": label,
            "in_report_section": section,
            "locator": loc,
            "resolution": resolution,
            "resolution_check": {"check": "", "result": ""},
            "note": note,
        }
        if asset_class == "figure_reference":
            rel = loc["quote"].split("](")[1].rstrip(")")
            base_name = rel.rsplit("/", 1)[-1]
            rec = fig_by_name.get(base_name)
            asset["resolution_check"] = {
                "check": "record.figures[] entry with matching filename + png payload present?",
                "result": "unresolved",
                "detail": "record_entry_found=%s payload_in_record=%s local_copy_in_worktree=%s"
                % (bool(rec), bool(rec and rec["payload_present"]), (REPO / base_name).exists()),
                "record_figure": rec["name"] if rec else None,
            }
            asset["note"] = note + (
                " 报告记录 figures[] 以 name+caption 登记该图，但整份记录任一 figure 都不含 png 载荷（payload_present=%s）。"
                % any_payload
            )
        elif resolution == RESOLVED:
            asset["resolution_check"] = {
                "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
                "result": "present" if kind == "document" else "resolved",
            }
        elif resolution == ABSENT:
            asset["resolution_check"] = {
                "check": "report body declares the material unavailable in the work tree",
                "result": "absent",
                "detail": "declaration quoted verbatim at locator; not supplemented by this package",
            }
        else:  # referenced_unresolved
            if "tensorphysics" in anchor:
                det = "local probe src/tensorphysics=%s (producing repo is TensorPhysics, this checkout is TensorKnowledge)" % local["src/tensorphysics"]
            elif "benchmarks/" in anchor or "p_area_joint" in anchor or "target_reliability_inverse" in anchor:
                det = "local probe benchmarks/iso19906_partial_factors=%s" % local["benchmarks/iso19906_partial_factors"]
            elif "in101_n09_results.json" in anchor:
                det = "target path is outside this worktree; not fetched (scope: report 9645 only)"
            elif "machine_criteria" in anchor:
                det = "field names quoted from the report's own restatement; source JSON not fetched"
            elif "ISO 2394" in anchor:
                det = "standard text is not in the worktree; no primary copy taken"
            else:
                det = "reference registered at its mention; target bytes out of this package's scope"
            asset["resolution_check"] = {
                "check": "reference parsed from markdown; target bytes present in this package's scope?",
                "result": "unresolved",
                "detail": det,
            }
        assets.append(asset)

    # ---- coverage: every markdown image / inline-code token is inside an asset span or exempted
    covered = [(a["locator"]["start_char"], a["locator"]["end_char"]) for a in assets]

    def is_covered(pos, end):
        return any(s <= pos and end <= e for s, e in covered)

    image_refs = list(re.finditer(r"!\[[^\]]*\]\([^)\s]+\)", md))
    tick_tokens = [(m.group(1), m.start(), m.end()) for m in re.finditer(r"`([^`\n]+)`", md)]
    exempt = {
        "a_form_vs_simulation": "criterion id inside the machine-criteria table asset (A10)",
        "b_inverse_solved_unique": "criterion id inside the machine-criteria table asset (A10)",
        "c_beta_sensitivity_vs_finite_difference": "criterion id inside the machine-criteria table asset (A10)",
        "d_iso_table_deviation_map": "criterion id inside the machine-criteria table asset (A10)",
        "e_negative_control_pa_correlation": "criterion id inside the machine-criteria table asset (A10)",
        "rho0": "symbol name used in prose; no independent material to register",
        "matplotlib": "third-party library name; report pins no version, so nothing to hash or resolve",
        "tensorphysics.structural": "package prefix of two already-registered module assets",
        "criterion_interpretation": "JSON field name of the results record; no independent material",
        "conditional": "verdict label produced by the producer; not an asset",
    }
    residue = []
    for tok, s0, e0 in tick_tokens:
        if is_covered(s0, e0) or tok in exempt:
            continue
        residue.append({"token": tok, "line": line_no(starts, s0)})
    img_uncovered = [
        {"quote": m.group(0), "line": line_no(starts, m.start())}
        for m in image_refs
        if not is_covered(m.start(), m.end())
    ]

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/kf/wp_9645_01_register.py",
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "hash_expected_from_contract": EXPECTED_HASH,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "hashed_bytes": "markdown field encoded as UTF-8",
            "chars": len(md),
            "chars_expected_from_contract": EXPECTED_CHARS,
            "bytes_utf8": len(raw),
            "lines": md.count("\n") + 1,
            "title": meta.get("title"),
            "title_matches_contract": meta.get("title") == CONTRACT_TITLE,
            "scenario_key": meta.get("scenario_key"),
            "scenario_key_matches_contract": meta.get("scenario_key") == CONTRACT_SCENARIO,
            "platform_report_id": meta.get("id"),
            "platform_mission_id": meta.get("mission_id"),
            "platform_status": meta.get("status"),
            "platform_tags": meta.get("tags"),
            "platform_figures": [f["name"] for f in figs],
            "platform_figures_payload_present": any_payload,
            "retrieved_via": "GET %s/tensor/reports/%s" % (base, REPORT_ID),
            "local_copy": str(SOURCE_COPY.relative_to(REPO)),
            "local_availability": local,
        },
        "objective": {
            "register_assets": True,
            "classify_report_type": False,
            "extraction_performed": False,
            "claims_generated": False,
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get(RESOLVED, 0),
            "referenced_unresolved": by_res.get(UNRESOLVED, 0),
            "declared_absent": by_res.get(ABSENT, 0),
            "markdown_images": len(image_refs),
            "markdown_images_registered": len(image_refs) - len(img_uncovered),
            "inline_code_tokens": len(tick_tokens),
            "inline_code_tokens_covered_or_exempt": len(tick_tokens) - len(residue),
        },
        "resolution_vocabulary": {
            RESOLVED: "引用与字节都在本包范围内：quote 是源 markdown 的唯一逐字切片",
            UNRESOLVED: "引用在原文中可定位，但目标字节不在本包范围（跨仓 / 跨任务 / 未取件），登记而不解析",
            ABSENT: "报告自述该材料不在工作树内，本工序不补录、不推断",
        },
        "assets": assets,
        "claims": [],
        "claims_note": "契约 notes 允许空 claims 数组：本工序只登记资产，不做抽取；未生成任何知识对象，也未把任何结论标为 verified。",
        "coverage": {
            "unregistered_inline_code_tokens": residue,
            "unregistered_markdown_images": img_uncovered,
            "exempt_tokens": exempt,
            "note": "inline code token / markdown 图片必须落在某个 asset 的字符区间内，或在此显式豁免并给出理由。",
        },
        "integrity": {
            "quote_uniqueness": all(a["locator"]["unique"] for a in assets),
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "locator_span_equality": all(
                md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]
                for a in assets
                if a["locator"]["method"] == "char_span"
            ),
            "asset_ids_unique": len(ids) == len(assets),
        },
        "platform_probe": probes,
    }

    mraw = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    MANIFEST.write_text(mraw, encoding="utf-8")

    result = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + digest,
            "source_field": SOURCE_FIELD,
            "producer": "agent/m15663",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "notes": (
                "source_hash 由本工序对 GET %s/tensor/reports/9645 返回的 markdown 取 UTF-8 字节重算，"
                "与契约声明值一致；哈希相等是机械恒等检查，不构成对报告内容正确性的判定，"
                "任何结论都未被标为 verified（verification 归平台门）。" % base
            ),
        },
        "outputs": {"asset_manifest.json": json.loads(mraw)},
        "claims": [],
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("hash   %s (contract match=%s)" % (digest, digest == EXPECTED_HASH))
    print("chars  %d / bytes %d" % (len(md), len(raw)))
    print("assets %d  by_resolution=%s" % (len(assets), json.dumps(by_res, ensure_ascii=False)))
    print("residue inline tokens=%d  unregistered images=%d" % (len(residue), len(img_uncovered)))
    print("wrote  %s" % MANIFEST.relative_to(REPO))
    print("wrote  %s" % RESULT.relative_to(REPO))
    return manifest


# ---------------------------------------------------------------- verification
def verify():
    """Offline acceptance re-check of the emitted artifacts (no network)."""
    import jsonschema

    checks, detail = {}, {}

    def rec(name, ok, info=""):
        checks[name] = bool(ok)
        detail[name] = info
        return ok

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        rec("valid_json", True, "asset_manifest.json + kf_result.json 均解析成功（strict JSON，无尾逗号/注释）")
    except Exception as e:  # noqa: BLE001
        rec("valid_json", False, "json parse failed: %r" % e)
        manifest, result = {}, {}

    schema_ok, schema_info = False, ""
    try:
        env_schema = json.loads(SCHEMA_ENVELOPE.read_text(encoding="utf-8"))
        local_schema = json.loads(SCHEMA_LOCAL.read_text(encoding="utf-8"))
        jsonschema.validate(result, env_schema)
        jsonschema.validate(manifest, local_schema)
        schema_ok = True
        schema_info = (
            "envelope vs schemas/kf_result.v1.schema.json (sha256 %s...); manifest vs docs/kf/%s/asset_manifest.schema.json (sha256 %s...)"
            % (
                hashlib.sha256(SCHEMA_ENVELOPE.read_bytes()).hexdigest()[:16],
                PKG,
                hashlib.sha256(SCHEMA_LOCAL.read_bytes()).hexdigest()[:16],
            )
        )
    except Exception as e:  # noqa: BLE001
        schema_info = "schema validation failed: %r" % e
    rec("schema_pass", schema_ok, schema_info)

    md = SOURCE_COPY.read_text(encoding="utf-8") if SOURCE_COPY.exists() else ""
    bad_loc, n_loc = [], 0
    for a in manifest.get("assets", []):
        loc = a.get("locator") or {}
        n_loc += 1
        if loc.get("method") == "document":
            ok = (
                loc.get("start_char") == 0
                and loc.get("end_char") == len(md)
                and md.startswith(loc.get("quote", ""))
            )
        else:
            ok = (
                md[loc.get("start_char", 0):loc.get("end_char", 0)] == loc.get("quote")
                and md.count(loc.get("quote", "")) == 1
                and loc.get("unique") is True
            )
        if not ok:
            bad_loc.append(a.get("asset_id"))
    rec(
        "source_locator_resolvable",
        n_loc > 0 and not bad_loc,
        "逐个重解析 %d 个 locator（char_span 用 md[start:end]==quote 且全文字符串计数=1；document 用 hash+长度+首行前缀），不可解析=%s"
        % (n_loc, bad_loc),
    )

    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    hash_ok = (
        digest == EXPECTED_HASH
        and manifest.get("source", {}).get("hash") == EXPECTED_HASH
        and result.get("provenance", {}).get("source_hash") == "sha256:" + EXPECTED_HASH
        and len(md) == EXPECTED_CHARS
    )
    rec(
        "source_hash_matches",
        hash_ok,
        "本地重算 sha256=%s；契约=%s；信封=%s；字符数=%d"
        % (digest, EXPECTED_HASH, result.get("provenance", {}).get("source_hash"), len(md)),
    )

    ids = [a.get("asset_id") for a in manifest.get("assets", [])]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    out_keys = list(result.get("outputs", {}).keys())
    rec(
        "no_duplicate_ids",
        not dup and len(out_keys) == len(set(out_keys)) and len(ids) == len(set(ids)),
        "%d 个 asset_id，重复=%s，outputs 键=%s" % (len(ids), dup, out_keys),
    )

    claims = result.get("claims") or []
    bad_claims = [c for c in claims if not (c.get("evidence") or c.get("status"))]
    rec(
        "all_claims_have_evidence_or_explicit_unresolved_status",
        not bad_claims,
        "claims=%d（task_type 01 的空数组是完整结果）；缺证据/缺状态的条数=%d" % (len(claims), len(bad_claims)),
    )

    cov = manifest.get("coverage", {})
    rec(
        "reference_coverage",
        not cov.get("unregistered_inline_code_tokens") and not cov.get("unregistered_markdown_images"),
        "未归类 inline code token=%s；未登记 markdown 图片=%s"
        % (cov.get("unregistered_inline_code_tokens"), cov.get("unregistered_markdown_images")),
    )
    integ = manifest.get("integrity", {})
    rec(
        "manifest_integrity_flags",
        bool(integ) and all(v is True for v in integ.values() if isinstance(v, bool)),
        json.dumps(integ, ensure_ascii=False),
    )
    rec(
        "no_verification_marks",
        all("verified" not in json.dumps(c) for c in claims),
        "claims 为空；结果内无 claim 级 verification 标记（verification 由平台门计算）",
    )
    src = manifest.get("source", {})
    rec(
        "contract_metadata_matches",
        bool(src.get("title_matches_contract")) and bool(src.get("scenario_key_matches_contract")),
        "title 与契约一致=%s；scenario_key 与契约一致=%s"
        % (src.get("title_matches_contract"), src.get("scenario_key_matches_contract")),
    )

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_copy": str(SOURCE_COPY.relative_to(REPO)),
        "source_sha256": digest,
        "acceptance": checks,
        "detail": detail,
        "all_pass": all(checks.values()),
        "scope_note": "本文件是工序自检记录，不是平台门结论；platform gate 独立重算哈希与子串后以其判定为准。",
    }
    LOCATOR_CHECK.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    if not verdict["all_pass"]:
        raise SystemExit("VERIFY FAILED")
    return verdict


# ---------------------------------------------------------------- figure
def figure():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    verdict = json.loads(LOCATOR_CHECK.read_text(encoding="utf-8"))
    by_res = manifest["counts"]["by_resolution"]
    by_cls = manifest["counts"]["by_class"]

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.8))
    order = [RESOLVED, UNRESOLVED, ABSENT]
    vals = [by_res.get(k, 0) for k in order]
    axes[0].barh(order, vals, color=["#2c7fb8", "#f0a202", "#bdbdbd"])
    for i, v in enumerate(vals):
        axes[0].text(v + 0.3, i, str(v), va="center", fontsize=9)
    axes[0].set_title("assets by resolution (n=%d)" % manifest["counts"]["assets"], fontsize=10)
    axes[0].set_xlabel("count")
    axes[0].set_xlim(0, max(vals) * 1.3)

    names = sorted(by_cls, key=lambda k: (-by_cls[k], k))
    axes[1].barh(names, [by_cls[k] for k in names], color="#4c72b0")
    for i, k in enumerate(names):
        axes[1].text(by_cls[k] + 0.05, i, str(by_cls[k]), va="center", fontsize=8)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("count")
    axes[1].set_title("assets by class", fontsize=10)
    axes[1].tick_params(axis="y", labelsize=7)

    ok = sum(1 for v in verdict["acceptance"].values() if v)
    fig.suptitle(
        "wp-9645-01 asset registration - report 9645, sha256 %s..., acceptance %d/%d"
        % (verdict["source_sha256"][:12], ok, len(verdict["acceptance"])),
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURE_PNG, dpi=150)
    print("wrote %s" % FIGURE_PNG.relative_to(REPO))


# ---------------------------------------------------------------- report body
def report():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    verdict = json.loads(LOCATOR_CHECK.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    src = manifest["source"]
    counts = manifest["counts"]
    acc = verdict["acceptance"]

    def tick(ok):
        return "✓" if ok else "✗"

    rows = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"].replace("\n", " ⏎ ")
        if len(q) > 80:
            q = q[:80] + "…"
        q = q.replace("|", "\\|")
        q = ("`` %s ``" % q) if "`" in q else ("`%s`" % q)
        rows.append(
            "| %s | `%s` | %s | L%d–L%d | %d–%d | %s |"
            % (
                a["asset_id"],
                a["asset_class"],
                a["resolution"],
                loc["start_line"],
                loc["end_line"],
                loc["start_char"],
                loc["end_char"],
                q,
            )
        )
    asset_table = "\n".join(rows)

    cls_rows = "\n".join(
        "| `%s` | %d |" % (k, v)
        for k, v in sorted(counts["by_class"].items(), key=lambda kv: (-kv[1], kv[0]))
    )
    acc_rows = "\n".join(
        "| %s | %s | %s |" % (tick(v), k, verdict["detail"].get(k, "").replace("|", "\\|"))
        for k, v in acc.items()
    )

    unresolved = [a for a in manifest["assets"] if a["resolution"] != RESOLVED]
    unres_rows = "\n".join(
        "| %s | `%s` | %s | %s |"
        % (a["asset_id"], a["asset_class"], a["resolution"], a["resolution_check"].get("detail", "").replace("|", "\\|"))
        for a in unresolved
    )

    body = """# KF-RESULT {pkg}

**工序** {task} ｜ **report_id** {rid} ｜ **契约** contract_version 1.0 ｜ **lane** B ｜ **status** draft

| 项 | 值 |
|---|---|
| 源资产 URI | `{uri}`（field=`{field}`） |
| 源 sha256（本工序重算） | `{digest}` |
| 源 sha256（契约声明） | `{digest_c}` |
| 一致 | {hash_match} |
| 字符数 / UTF-8 字节 / 行数 | {chars} / {bytes} / {lines} |
| 报告标题（平台记录） | {title} |
| scenario_key | `{scenario}` |
| 平台 mission_id / status | {mission} / {status} |
| 注册资产数 | {n_assets}（resolved {n_res} / unresolved {n_unres} / absent {n_abs}） |
| claims | 0 条（`claims: []`，契约允许；本工序不做抽取） |
| 输出文件名 | `asset_manifest.json` |

## ① 本工序做了什么

按合同 `objective.register_assets=true`、`objective.classify_report_type=false`，对 report_id=9645 的 markdown 做**资产登记**：

1. 取回 `tensor://reports/9645` 的 `markdown` 字段，本地重算 sha256 并核对契约声明值 `{digest_c}` 与字符数 {chars_c}。
2. 把该 markdown 内的可解析材料登记为 {n_assets} 条资产：文档本体与章节锚点、机器判据表与判据汇总行、输入参数表、表 1–表 8、⑥ 误差判定表与结论段、6 张图（markdown 图片声明）、结果 JSON / 求解器模块 / 脚本 / 复现命令等代码与数据引用、ISO 19906 Annex A 表格（报告自述缺失）与出处等级标记、JCSS/ISO 2394 劈分约定、产出仓与前序节点、3 个数值锚点、设计格式原文。
3. 每条资产给出**逐字字符区间 locator**（`start_char/end_char/start_line/end_line/quote/quote_sha256`），并对每个 quote 断言「是源文本的唯一子串且 `md[start:end]==quote`」。
4. **未做**：知识抽取、结论判定、report_type 分类、任何 `verified` 标记；`claims` 为空数组。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 做法 | 产物 / 证据 |
|---|---|---|
| 取源 | `GET $TENSOR_API_BASE/tensor/reports/9645`（Bearer 登录 token），只读该 report_id | `source.md`（源副本）+ `sha256.txt` |
| 校验 | `hashlib.sha256(markdown.encode('utf-8'))` 对比契约哈希；字符数对比 {chars_c}；`source.title_matches_contract` / `scenario_key_matches_contract` 位记录 | `asset_manifest.json` → `source.*` |
| 定位 | 每条资产先给一个**唯一锚串**，程序断言 `md.count(anchor)==1`，再按 `token / line / table / para / document` 五种方式扩成区段，quote 一律取 `md[start:end]` 切片（**不手抄**） | `assets[].locator` |
| 解析状态 | 三档：`resolved_in_source`（引用与字节都在包内）/ `referenced_unresolved`（引用可定位、目标字节不在包内）/ `declared_absent`（报告自述不在工作树） | `assets[].resolution` + `resolution_check` |
| 覆盖检查 | 扫全部 inline-code token 与 markdown 图片，逐个判定是否落在某资产字符区间内；否则必须显式豁免并给理由 | `coverage.*` |
| 结构校验 | 信封 `jsonschema.validate(kf_result, schemas/kf_result.v1.schema.json)`；清单 `jsonschema.validate(manifest, docs/kf/{pkg}/asset_manifest.schema.json)` | `locator_check.json` |
| 自检 | `verify` 模式离线重跑 6 项 acceptance + 4 项附加检查，输出 `locator_check.json` | `report_body.md`（本文件） |

工具链：Python 3 标准库（`hashlib`/`json`/`urllib`）+ `jsonschema` + `matplotlib`；脚本 `scripts/kf/wp_9645_01_register.py`（`build`/`verify`/`figure`/`report` 四模式）。

**一键复跑**（工作树根）：

```
python3 scripts/kf/wp_9645_01_register.py build && \\
python3 scripts/kf/wp_9645_01_register.py verify && \\
python3 scripts/kf/wp_9645_01_register.py figure && \\
python3 scripts/kf/wp_9645_01_register.py report
```

离线复检（无需网络，仅用仓内 `source.md`）：

```
python3 scripts/kf/wp_9645_01_register.py verify
python3 -m pytest tests/test_wp_9645_01_assets.py -q
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/{pkg}/asset_manifest.json` | 资产清单主体：source 元信息 + {n_assets} 条资产 + counts + coverage + integrity + platform_probe；`claims` 空 |
| `docs/kf/{pkg}/kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs / claims），`outputs.asset_manifest.json` 内嵌清单全文 |
| `docs/kf/{pkg}/source.md` | 报告 markdown 逐字节副本（所有 locator 的解析底本） |
| `docs/kf/{pkg}/sha256.txt` | sha256 / field / chars / bytes / report_id 一行事实 |
| `docs/kf/{pkg}/locator_check.json` | 离线自检记录：6 项 acceptance + 4 项附加检查逐项 pass/fail 与证据串 |
| `docs/kf/{pkg}/asset_manifest.schema.json` | 本包清单形状约束（可机器裁的 `schema_pass`，`asset_manifest.v1` 的 pattern 版） |
| `docs/kf/{pkg}/asset_coverage.png` | 覆盖图：按解析状态的资产计数 + 按资产类别计数（见 ④ 图说明） |

按资产类别分布：

| asset_class | 数量 |
|---|---|
{cls_rows}

## ④ 证据定位表（claim / 字段 → 原文引文片段）

**图说明（本工序唯一图件 `asset_coverage.png`）**：本工序是登记型（无物理场、无数值求解），因此没有场量云图与解析解/基线比较曲线可画；图件改为**登记覆盖图**——左栏按解析状态计数（resolved_in_source 27 / referenced_unresolved 18 / declared_absent 1），右栏按资产类别计数，标题行给出源 sha256 前 12 位与自检 10/10 结果。图中每个数字都直接取自 `asset_manifest.json` 的 `counts`（程序化注入，非手抄）。

本工序无 claim（`claims: []`），下表是**字段级**证据定位：`asset_id → 原文逐字片段`，全部可由 `md[start:end]==quote` 机械复算。

| asset_id | asset_class | resolution | 行 | 字符区间 | 原文片段（逐字切片） |
|---|---|---|---|---|---|
{asset_table}

未能解析（`referenced_unresolved` / `declared_absent`）的条目及原因：

| asset_id | asset_class | resolution | 原因（实测） |
|---|---|---|---|
{unres_rows}

## ⑤ 注意点与局限

1. **6 张图只有引用、没有字节**。报告 markdown 用绝对路径（`/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig*.png`）引用图，指向产出任务 8350 的工作树；平台记录 `figures[]` 只存 name+caption、无 png 载荷（`platform_figures_payload_present=false`，实测）。故 6 条图资产全部 `referenced_unresolved`：登记位置与文件名，不声称持有图件、不对图内容作任何断言。按边界也未跨任务取件。
2. **结果 JSON 与求解器代码不在本包范围内**。`in101_n09_results.json`、`tensorphysics.*`、`p_area_joint.py`、`target_reliability_inverse.py`、复现命令均属 TensorPhysics 仓/产出任务 8350；本检出为 TensorKnowledge，`src/tensorphysics` 与 `benchmarks/iso19906_partial_factors` 实测不存在（`source.local_availability`），因此这些条目是引用登记，不是可解析资产。
3. **ISO 19906 Annex A.2/A.3 表格值本工序不持有、不补录**。报告自述「ISO 19906 Annex A 正文不在工作树内」且标记 `source_tier=secondary`, `primary_source_verified=False`；表 4/表 5 中的表格分项系数只能从报告转述登记，无法回溯到规范正文。这是本报告最大的外部证据缺口，下游若要用表 4/表 5 的偏差结论，必须自行取得规范正文。
4. **哈希一致 ≠ 内容正确**。`source_hash_matches` 只证明我读到的字节与契约声明同源；本工序没有任何判据复核 β、κ*、偏差等数值是否算对，也不把任何结论标成 `verified`（verification 归平台门）。
5. **会计口径（会计而非评价）**：`resolved_in_source` 计 {n_res} 条、`referenced_unresolved` {n_unres} 条、`declared_absent` {n_abs} 条；前者是「引文可逐字解析」，不等于「结论成立」。
6. **清单 schema 是本地约束**。`schemas/kf_result.v1.schema.json` 在仓内存在并按它校验信封；清单侧无仓内 canonical schema（`schemas/asset_manifest.v1.schema.json` 是 wp-448-01 的 const 版，package_id/report_id 写死为 448），故本包补 `docs/kf/{pkg}/asset_manifest.schema.json`（同形状、const 改 pattern）。**若平台侧 schema 与此不符，以平台为准、本包接受返修。**

## ⑥ 自检：逐条对照 acceptance

| 结果 | acceptance 项 | 证据 |
|---|---|---|
{acc_rows}

附加检查（非 acceptance，但本包断言）：`reference_coverage`、`manifest_integrity_flags`、`no_verification_marks`、`contract_metadata_matches` 全绿；全部 10 项见 `locator_check.json` 的 `all_pass` 字段（当前 `all_pass={all_pass}`）。

**未跑/未验的项（如实声明）**：报告的数值结论（β=4.0 精度、κ 唯一性、ISO 表格偏差、负控）**未**在本工序复核——不属本工序接口；报告 markdown 引用的 6 张图件与结果 JSON **未**取回，故对图与 JSON 的内容未作任何验证。

```json
{envelope}
```
""".format(
        pkg=PKG,
        task=TASK_TYPE,
        rid=REPORT_ID,
        uri=SOURCE_URI,
        field=SOURCE_FIELD,
        digest=verdict["source_sha256"],
        digest_c=EXPECTED_HASH,
        hash_match="✓" if src["hash_matches_contract"] else "✗",
        chars=src["chars"],
        chars_c=EXPECTED_CHARS,
        bytes=src["bytes_utf8"],
        lines=src["lines"],
        title=src["title"],
        scenario=src["scenario_key"],
        mission=src["platform_mission_id"],
        status=src["platform_status"],
        n_assets=counts["assets"],
        n_res=counts["resolved_in_source"],
        n_unres=counts["referenced_unresolved"],
        n_abs=counts["declared_absent"],
        cls_rows=cls_rows,
        asset_table=asset_table,
        unres_rows=unres_rows,
        acc_rows=acc_rows,
        all_pass=verdict["all_pass"],
        envelope=json.dumps(result, ensure_ascii=False, indent=2),
    )
    REPORT_BODY.write_text(body, encoding="utf-8")
    print("wrote %s (%d chars)" % (REPORT_BODY.relative_to(REPO), len(body)))


MODES = {"build": build, "verify": verify, "figure": figure, "report": report}


def main(argv):
    if not argv:
        raise SystemExit("usage: %s [build] [verify] [figure] [report]" % __file__)
    for m in argv:
        if m not in MODES:
            raise SystemExit("unknown mode %r (choose from %s)" % (m, sorted(MODES)))
        MODES[m]()


if __name__ == "__main__":
    main(sys.argv[1:])
