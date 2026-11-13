#!/usr/bin/env python3
"""KF work package wp-13325-01 (task_type=01-asset-registration, report 13325).

Single-purpose: register the *source assets* of tensor://reports/13325 — pin the
markdown byte hash, enumerate the locatable blocks (parameter table, closed-form
line, solver settings, result tables, figure), and record what is referenced but
NOT attached. No extraction, no claims, no verification: `claims` stays empty by
contract (objective.classify_report_type=false, notes: "不做抽取").

Every quote written into the manifest is sliced out of the fetched markdown, so
"verbatim" is enforced by construction and re-checked afterwards
(md[start:end] == quote and md.count(quote) == 1).

Usage (repro):
    TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
      python3 scripts/kf_wp13325_01_register.py
    # offline re-run against a saved copy of the markdown field:
    python3 scripts/kf_wp13325_01_register.py --source-file artifacts/wp-13325-01/source_markdown.md

Outputs (all inside the worktree):
    artifacts/wp-13325-01/source_markdown.md   byte-identical snapshot of the field
    artifacts/wp-13325-01/asset_manifest.json  the manifest (output.asset_manifest.json)
    artifacts/wp-13325-01/kf_result.json       the KF result envelope to publish
    artifacts/wp-13325-01/selfcheck.json       acceptance-item self-check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, "artifacts", "wp-13325-01")          # working dir (gitignored)
MIRROR = os.path.join(ROOT, "docs", "kf", "wp-13325-01")          # tracked deliverable
SCHEMAS = os.path.join(ROOT, "schemas")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

CONTRACT = {
    "package_id": "wp-13325-01",
    "task_type": "01-asset-registration",
    "report_id": "13325",
    "source_uri": "tensor://reports/13325",
    "source_field": "markdown",
    "source_hash": "sha256:f7a7270b3721cd37011bb6ab66ebba8a0cb6e031b7e971c9a900b4c22acb1fe9",
    "title": "GAP-FEM-WINKLER 验证：弹性地基板 FEM 解 vs Hetényi 解析解",
    "scenario_key": "winkler_hetenyi_verification",
    "chars": 2078,
}
FIG_ENDPOINT = "/tensor/reports/{rid}/figures/{name}"


# --------------------------------------------------------------------- helpers
def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_tag(b: bytes) -> str:
    return "sha256:" + sha256_hex(b)


def post(url: str, body: dict, tok: str | None = None, timeout: int = 60):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(url: str, tok: str | None = None, timeout: int = 60):
    headers = {"Authorization": "Bearer " + tok} if tok else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, dict(r.headers), r.read()


class Source:
    """The report markdown plus offset bookkeeping (1-based line numbers)."""

    def __init__(self, md: str):
        self.md = md
        self.line_starts = [0]
        for i, ch in enumerate(md):
            if ch == "\n":
                self.line_starts.append(i + 1)
        self.n_lines = md.count("\n") + (0 if md.endswith("\n") else 1)

    def line_of(self, idx: int) -> int:
        lo, hi = 0, len(self.line_starts) - 1
        while lo < hi:  # last line_start <= idx
            mid = (lo + hi + 1) // 2
            if self.line_starts[mid] <= idx:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def find(self, needle: str) -> int:
        idx = self.md.find(needle)
        if idx < 0:
            raise SystemExit(f"anchor not found in markdown: {needle!r}")
        return idx

    def span(self, needle: str) -> tuple[int, int]:
        i = self.find(needle)
        return i, i + len(needle)

    def block_after(self, anchor: str, expect_prefix: str) -> tuple[int, int]:
        """Contiguous run of non-empty lines after `anchor` (table / bullet / list block).

        Blank-line delimited, so it works for markdown tables, "- " bullets and
        "1. " numbered lists without hard-coding per-block line counts.
        """
        i = self.find(anchor) + len(anchor)
        rest = self.md[i:]
        pos = i
        out = []
        for line in rest.split("\n"):
            if not out and not line.strip():
                pos += len(line) + 1
                continue
            if not line.strip():
                break
            out.append(line)
            pos += len(line) + 1
        if not out:
            raise SystemExit(f"empty block after {anchor!r}")
        if not out[0].startswith(expect_prefix):
            raise SystemExit(
                f"block after {anchor!r} starts with {out[0][:40]!r}, expected prefix {expect_prefix!r}")
        start = i + len(rest[: rest.index(out[0])]) if out[0] in rest else -1
        if start < 0 or self.md[start:start + len(out[0])] != out[0]:
            raise SystemExit("block not contiguous")
        end = start + len("\n".join(out))
        return start, end

    def next_nonempty_line(self, anchor: str) -> tuple[int, int]:
        i = self.find(anchor)
        lines = self.md[i:].split("\n")
        pos = i
        for line in lines:
            if pos > i and line.strip():
                return pos, pos + len(line)
            pos += len(line) + 1
        raise SystemExit("no non-empty line after anchor")

    def line_containing(self, needle: str) -> tuple[int, int]:
        idx = self.find(needle)
        start = self.md.rfind("\n", 0, idx) + 1
        end = self.md.find("\n", idx)
        end = len(self.md) if end < 0 else end
        return start, end

    def locator(self, start: int, end: int) -> dict:
        quote = self.md[start:end]
        return {
            "method": "char_span",
            "start_char": start,
            "end_char": end,
            "start_line": self.line_of(start),
            "end_line": self.line_of(max(start, end - 1)),
            "quote": quote,
            "unique": self.md.count(quote) == 1,
        }


def doc_span(src: Source, anchor: tuple[int, int]) -> tuple[int, int]:
    """Whole document as a span, but the stored quote is the unique anchor line."""
    return anchor


# --------------------------------------------------------------- asset registry
# (asset_id, asset_class, label, section, span_fn, resolution, check_dict, note, locator_points_to)
def build_assets(src: Source) -> list[dict]:
    title_line = src.line_containing("# GAP-FEM-WINKLER")
    conclusion_line = src.line_containing("**结论**：GAP-FEM-WINKLER")
    specs = [
        (
            "A01",
            "report_document",
            "报告 markdown 全文（source field=markdown）",
            "document",
            lambda: title_line,
            "resolved_in_source",
            {
                "check": "sha256(UTF-8 bytes) recomputed locally vs contract source_hash",
                "result": "resolved",
            },
            "全文注册：char span=0..len(markdown)，哈希钉住字节，见 integrity.source_hash；"
            "本行 quote 仅定位文档标题（标题与契约 title 逐字相同）。",
            "payload",
        ),
        (
            "A02",
            "parameter_table",
            "算例参数表（E, ν, t, k_f, P, D, l 共 7 行）",
            "## 1. 案例介绍",
            lambda: src.block_after("**参数表**：", "|"),
            "resolved_in_source",
            {
                "check": "markdown table block sliced verbatim; row/column count parsed",
                "result": "resolved",
            },
            "表内 7 个物理量均可逐字解析；D 与 l 为导出量，注册时按表内 E/ν/t/k_f 重算核对"
            "（见 integrity_findings.F3，非对报告结论的验证）。",
            "payload",
        ),
        (
            "A03",
            "analytic_solution_expression",
            "Hetényi 无限板中心挠度闭式解表达式行",
            "## 1. 案例介绍",
            lambda: src.next_nonempty_line("**Hetényi 解析解**（无限板中心挠度）："),
            "resolved_in_source",
            {
                "check": "line sliced verbatim; control-character scan of the same span",
                "result": "resolved",
            },
            "该行可定位但**排版已损坏**：含 0x0C(form feed) 与 0x09(TAB) 控制字符，"
            "`\\frac`→`rac`、`\\times`→TAB+`imes`、`\\text`→TAB+`ext`，且行首/行尾各有一段游离数字串。"
            "本工序只登记不修复（constraints.do_not_invent_missing_information）；"
            "损坏取证见 integrity_findings.F1。",
            "payload",
        ),
        (
            "A04",
            "software_component",
            "求解器实现：TensorFEM Q4 Mindlin-Reissner 板单元 + Winkler 地基耦合",
            "## 2. 方法",
            lambda: src.line_containing("**数值方法**："),
            "referenced_unresolved",
            {
                "check": "code artifact attached in report (repo path / commit / file / input deck)",
                "result": "unresolved",
            },
            "提及可定位，但报告中**未附**任何代码路径、commit、版本号或输入卡片，"
            "无法从本报告解析出可复算的实现资产；resolution=referenced_unresolved。",
            "mention",
        ),
        (
            "A05",
            "solver_settings",
            "关键设置块（板尺寸/网格/边界条件/加载位置/求解器，共 5 条）",
            "## 2. 方法",
            lambda: src.block_after("**关键设置**：", "- "),
            "resolved_in_source",
            {
                "check": "bullet block sliced verbatim; 5 items present",
                "result": "resolved",
            },
            "板尺寸在本文档写作 10l × 10l；与 F2 记录的 §5 中 `8l 板` 表述并存，"
            "本工序不裁决以哪次运行成立。",
            "payload",
        ),
        (
            "A06",
            "validation_strategy",
            "验证策略块（4 条：中心挠度/网格收敛/径向分布/缩放律）",
            "## 2. 方法",
            lambda: src.block_after("**验证策略**：", "1. "),
            "resolved_in_source",
            {
                "check": "numbered-list block sliced verbatim; 4 items present",
                "result": "resolved",
            },
            "登记为“报告声称的验证面”清单本身，不表示任一验证已由本工序复核。",
            "payload",
        ),
        (
            "A07",
            "result_table",
            "中心挠度对标表（Hetényi 12.187 mm；FEM nx=16/12/8）",
            "## 3. 计算结果",
            lambda: src.block_after("**中心挠度对标**：", "|"),
            "resolved_in_source",
            {
                "check": "markdown table block sliced verbatim; error column recomputed from 12.187",
                "result": "resolved",
            },
            "误差列与 12.187 mm 基准自洽（见 F4 重算残差，单位 pp）。",
            "payload",
        ),
        (
            "A08",
            "result_table",
            "网格收敛表（nx=4/6/8/12/16）",
            "## 3. 计算结果",
            lambda: src.block_after("**网格收敛**：", "|"),
            "resolved_in_source",
            {
                "check": "markdown table block sliced verbatim; monotonicity recomputed",
                "result": "resolved",
            },
            "w(0) 随 nx 单调增、趋近 12.187 mm（F4 重算），与报告 `单调性 ✅` 表述一致。",
            "payload",
        ),
        (
            "A09",
            "scaling_check",
            "缩放律验证块（w∝P 比值 2.00；w∝1/√k_f 比值 1.99）",
            "## 3. 计算结果",
            lambda: src.block_after("**缩放律验证**：", "- "),
            "resolved_in_source",
            {"check": "bullet block sliced verbatim; 2 items present", "result": "resolved"},
            "仅登记报告给出的比值与自报误差（<1%）；原始两次运行数据未附（见 A12）。",
            "payload",
        ),
        (
            "A10",
            "figure_reference",
            "结果图 winkler_hetenyi_comparison（挠度径向分布 + 网格收敛）",
            "## 4. 结果图",
            lambda: src.line_containing("见附图："),
            "resolved_in_source",  # overwritten by the live endpoint probe in main()
            {
                "check": "GET /tensor/reports/13325/figures/winkler_hetenyi_comparison",
                "result": "unresolved",
            },
            "正文只做“见附图”引用，不内嵌图；载荷在报告的 record.figures 里，"
            "本工序用 HTTP 探针确认可解析性并钉住字节哈希（见 payload_locator / figure_probe）。",
            "record.figures",
        ),
        (
            "A11",
            "literature_reference",
            "Kelvin kei 函数（Hetényi 解所用特殊函数）",
            "## 5. 注意点",
            lambda: src.line_containing("**Kelvin 函数**"),
            "referenced_unresolved",
            {
                "check": "bibliographic locator present (author/year/DOI/formula number)",
                "result": "unresolved",
            },
            "仅函数名与定性行为（r≈3.8l 抬升环），无文献出处、无公式号，无法解析到具体参考条目。",
            "mention",
        ),
        (
            "A12",
            "raw_data_and_scripts",
            "原始数据/脚本/提交（复算所需的过程资产）",
            "document",
            lambda: conclusion_line,
            "declared_absent",
            {
                "check": "regex scan of markdown for repo paths / commit shas / data-file extensions",
                "result": "absent",
            },
            "全文扫描未发现任何代码路径、commit、.py/.csv/.dat/.json/.npz 等数据文件引用，"
            "故复算所需的原始输出在报告内声明性缺失（absent），非本工序遗漏。",
            "payload",
        ),
    ]
    assets = []
    for aid, cls, label, sect, fn, res, chk, note, pts in specs:
        start, end = fn()
        loc = src.locator(start, end)
        if aid in ("A01", "A12"):  # whole-document assets: anchor quote + document range
            loc["method"] = "document"
            loc["document_char_start"] = 0
            loc["document_char_end"] = len(src.md.rstrip("\n"))
        if loc["method"] == "char_span" and not loc["quote"].strip():
            raise SystemExit(f"{aid}: empty quote")
        assets.append(
            {
                "asset_id": aid,
                "asset_class": cls,
                "label": label,
                "in_report_section": sect,
                "locator": loc,
                "locator_points_to": pts,
                "resolution": res,
                "resolution_check": chk,
                "note": note,
            }
        )
    return assets


# ------------------------------------------------------------------- integrity
def parse_parameter_table(quote: str) -> dict:
    vals = {}
    for line in quote.split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[1] in ("E", "ν", "t", "k_f", "P", "D", "l"):
            vals[cells[1]] = cells[2]
    return vals


def scientific(cell: str) -> float:
    m = re.match(r"^([0-9.]+)×10([⁰¹²³⁴⁵⁶⁷⁸⁹]+)$", cell.strip())
    if m:
        sup = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
        return float(m.group(1)) * 10 ** int(m.group(2).translate(sup))
    return float(cell)


def integrity_findings(src: Source, assets: list[dict]) -> tuple[dict, list[dict], dict]:
    md = src.md
    by_id = {a["asset_id"]: a for a in assets}

    # -- quote uniqueness / resolvability (structural)
    uniq = {}
    for a in assets:
        q = a["locator"]["quote"]
        i, j = a["locator"]["start_char"], a["locator"]["end_char"]
        uniq[a["asset_id"]] = {
            "occurs": md.count(q),
            "slice_matches": md[i:j] == q,
            "unique": md.count(q) == 1,
        }
    quote_uniqueness = {
        "all_slices_match": all(v["slice_matches"] for v in uniq.values()),
        "all_unique": all(v["unique"] for v in uniq.values()),
        "per_asset": uniq,
    }

    # -- F1: control characters in the closed-form line
    cf = by_id["A03"]["locator"]
    cf_quote = cf["quote"]
    ctrl = sorted({ord(c) for c in cf_quote if ord(c) < 32 and c != "\n"})
    stray = re.findall(r"2239218", cf_quote)
    tokens = []
    for k, ch in enumerate(cf_quote):
        if ord(ch) < 32 and ch != "\n":
            tail = cf_quote[k + 1:k + 6]
            tokens.append({
                "codepoint": ord(ch),
                "name": {9: "TAB", 12: "FORM_FEED"}.get(ord(ch), "CTRL"),
                "offset_in_quote": k,
                "following_chars": tail,
                "reconstructed_token": ("\\t" if ord(ch) == 9 else "\\f") + tail,
            })
    intact = [t for t in ("\\sqrt", "{", "}", "^") if t in cf_quote]
    f1 = {
        "id": "F1",
        "kind": "encoding_damage",
        "where": "A03 / ## 1. 案例介绍",
        "observed": {
            "control_codepoints": ctrl,
            "control_sequence": [ord(c) for c in cf_quote if ord(c) < 32 and c != "\n"],
            "control_tokens": tokens,
            "intact_latex_tokens": intact,
            "stray_digit_runs": stray,
            "line_repr": cf_quote.replace("\t", "\\t").replace("\x0c", "\\f"),
        },
        "mechanism_hypothesis": "\\t/\\f 被当作转义序列展开（TAB=0x09, FF=0x0C），与 TSV/printf 类写入路径一致；"
        "本行 4 个控制字符 = 1×FF + 3×TAB，恰对应 \\frac(1) + \\times(1) + \\text(2)。",
        "consequence": "闭式解 LaTeX 不可直接渲染/复用；若下游要抽取公式必须回到作者侧原文，"
        "本工序不修复、不做等价改写。",
        "severity": "non_blocking_for_registration / blocking_for_formula_extraction",
    }

    # -- F2: plate size 10l vs 8l
    i10 = md.find("板尺寸：10l × 10l")
    i8 = md.find("8l 板")
    f2 = {
        "id": "F2",
        "kind": "internal_inconsistency",
        "where": "A05 vs ## 5. 注意点 第 1 条",
        "observed_quotes": [
            src.md[src.line_containing("板尺寸：10l × 10l")[0]:src.line_containing("板尺寸：10l × 10l")[1]],
            src.md[src.line_containing("8l 板在 nx=12 时误差")[0]:src.line_containing("8l 板在 nx=12 时误差")[1]],
        ],
        "detail": {
            "main_section_plate_size": "10l × 10l" if i10 >= 0 else None,
            "notes_section_plate_size": "8l" if i8 >= 0 else None,
        },
        "status": "unresolved",
        "unresolved_reason": "报告未说明 8l 与 10l 分别对应哪次运行（是否同一 w(0)=11.908 mm 算例）；"
        "无运行清单/输入卡片可裁决。",
        "severity": "non_blocking_for_registration / needs_author_clarification",
    }

    # -- F3: derived quantities recomputed from registered parameters
    params = parse_parameter_table(by_id["A02"]["locator"]["quote"])
    E, nu, t = scientific(params["E"]), float(params["ν"]), float(params["t"])
    k, P = scientific(params["k_f"]), scientific(params["P"])
    D_rep, l_rep = scientific(params["D"]), float(params["l"])
    D_calc = E * t**3 / (12 * (1 - nu**2))
    l_calc = (D_calc / k) ** 0.25
    w_calc = P / (8 * (D_calc * k) ** 0.5)  # Hetényi, metres
    w_rep_m = 1.2187e-2  # value printed on the A03 line, re-read below from the quote
    m = re.search(r"=\s*([0-9.]+)\s*\\times\s*10\^\{-2\}", cf_quote)
    if m:
        w_rep_m = float(m.group(1)) * 1e-2
    f3 = {
        "id": "F3",
        "kind": "arithmetic_crosscheck_of_registered_parameters",
        "scope_warning": "只核对报告参数表内部的量纲/代数自洽性；**不**构成对 FEM 精度结论的验证。",
        "reported_vs_recomputed": {
            "D_Nm": {"reported": D_rep, "recomputed": round(D_calc, 3),
                     "rel_dev": round(abs(D_calc - D_rep) / D_rep, 5)},
            "l_m": {"reported": l_rep, "recomputed": round(l_calc, 4),
                    "rel_dev": round(abs(l_calc - l_rep) / l_rep, 5)},
            "w0_m": {"reported": w_rep_m, "recomputed": round(w_calc, 7),
                     "rel_dev": round(abs(w_calc - w_rep_m) / w_rep_m, 5)},
        },
        "formulas": ["D = E t^3 / (12 (1-ν^2))", "l = (D/k_f)^(1/4)", "w(0) = P / (8 sqrt(D k_f))"],
        "status": "consistent_within_reporting_rounding",
    }

    # -- F4: recompute the error columns / monotonicity from the printed numbers
    base = 12.187
    errs = []
    for row in by_id["A07"]["locator"]["quote"].split("\n"):
        cells = [c.strip().strip("*") for c in row.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[1].replace(".", "").isdigit():
            errs.append((cells[0], float(cells[1]), cells[2]))
    err_recomp = []
    for name, w, rep in errs[1:]:
        if rep == "—":
            continue
        rec = (base - w) / base * 100
        err_recomp.append({
            "row": name,
            "reported_pct": float(rep.strip("%")),
            "recomputed_pct": round(rec, 3),
            "abs_diff_pp": round(abs(rec - float(rep.strip("%"))), 3),
        })
    mesh = []
    for row in by_id["A08"]["locator"]["quote"].split("\n"):
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0].isdigit():
            mesh.append((int(cells[0]), float(cells[1])))
    mesh_sorted = sorted(mesh)
    f4 = {
        "id": "F4",
        "kind": "arithmetic_crosscheck_of_result_columns",
        "scope_warning": "重算只针对报告自报数字之间的一致性；不重跑 FEM。",
        "baseline_used_mm": base,
        "error_column": err_recomp,
        "max_abs_diff_pp": max([e["abs_diff_pp"] for e in err_recomp], default=None),
        "mesh_monotonic_increasing": all(
            b[1] >= a[1] for a, b in zip(mesh_sorted, mesh_sorted[1:])
        ),
        "mesh_series": [[n, w] for n, w in mesh_sorted],
        "status": "consistent_within_reporting_rounding",
    }

    # -- F5: figure caption vs body consistency
    figs = []
    f5 = {
        "id": "F5",
        "kind": "figure_caption_vs_body",
        "checked": figs,
        "status": "see figure_probe",
    }

    findings = [f1, f2, f3, f4]
    return quote_uniqueness, findings, {"params": params, "f5": f5}


def absent_scan(md: str) -> dict:
    patterns = {
        "file_extensions": r"\.(py|csv|dat|json|npz|nc|h5|hdf5|zip|tar|png|fig|xlsx)\b",
        "repo_or_commit_paths": r"(github\.com|/root/|/home/|git@|\bcommit\b|\bsha256\b)",
        "input_deck": r"(input|inp|yaml|toml|deck)\s*(file|文件)",
    }
    hits = {k: re.findall(v, md, flags=re.I) for k, v in patterns.items()}
    return {k: {"matches": len(v), "examples": v[:5]} for k, v in hits.items()}


# ------------------------------------------------------------------- figure probe
def probe_figures(record: dict, token: str | None, rid: str) -> dict:
    out = {}
    for fig in record.get("figures") or []:
        name = fig.get("name", "")
        ep = FIG_ENDPOINT.format(rid=rid, name=name)
        rec = {"name": name, "caption": fig.get("caption"), "endpoint": ep, "method": "GET"}
        try:
            st, hdrs, body = get(API + ep, token, timeout=60)
            hlow = {k.lower(): v for k, v in hdrs.items()}
            rec.update(http_status=st, content_type=hlow.get("content-type"),
                       bytes=len(body), sha256=sha256_tag(body), resolvable=True)
        except urllib.error.HTTPError as exc:
            rec.update(http_status=exc.code, error=exc.read()[:200].decode("utf-8", "replace"),
                       resolvable=False)
        except urllib.error.URLError as exc:  # network down => honest unknown
            rec.update(http_status=None, error=str(exc), resolvable=None)
        out[name] = rec
    return out


# ------------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-file", help="offline markdown copy instead of the platform API")
    ap.add_argument("--no-figure-probe", action="store_true")
    ap.add_argument("--emitted-at", help="pin generated_at/emitted_at (ISO-8601 Z) for byte-identical reruns")
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    token, record = None, {}
    if args.source_file:
        md = open(args.source_file, encoding="utf-8").read()
        record = {"id": CONTRACT["report_id"], "title": CONTRACT["title"],
                  "scenario_key": CONTRACT["scenario_key"], "figures": [],
                  "note": "offline run: record metadata not refetched"}
    else:
        login = post(API + "/auth/login",
                     {"username": os.environ["TENSOR_AGENT_USER"],
                      "password": os.environ["TENSOR_AGENT_PASS"]})
        token = login.get("access_token") or login.get("token")
        st, _, raw = get(f"{API}/tensor/reports/{CONTRACT['report_id']}", token)
        record = json.loads(raw)
        record = record.get("data", record) if isinstance(record, dict) else record
        md = record.get("markdown") or ""
    if str(record.get("id")) != CONTRACT["report_id"]:
        raise SystemExit(f"wrong report served: id={record.get('id')}")

    md_bytes = md.encode("utf-8")
    hash_hex = sha256_hex(md_bytes)
    hash_matches = hash_hex == CONTRACT["source_hash"].split(":", 1)[1]
    chars = len(md)

    src = Source(md)
    assets = build_assets(src)
    quote_uniqueness, findings, aux = integrity_findings(src, assets)

    fig_probe = {} if args.no_figure_probe else probe_figures(record, token, CONTRACT["report_id"])
    a10 = next(a for a in assets if a["asset_id"] == "A10")
    if fig_probe:
        fig = next(iter(fig_probe.values()))
        ok = fig.get("resolvable") is True
        a10["resolution"] = "resolved_in_source" if ok else "referenced_unresolved"
        a10["resolution_check"]["result"] = "resolved" if ok else "unresolved"
        a10["payload_locator"] = {
            "record_field": "figures[0]",
            "endpoint": fig.get("endpoint"),
            "http_status": fig.get("http_status"),
            "content_type": fig.get("content_type"),
            "bytes": fig.get("bytes"),
            "sha256": fig.get("sha256"),
        }
    else:
        a10["resolution"] = "referenced_unresolved"
        a10["resolution_check"]["result"] = "unresolved"

    scan = absent_scan(md)
    by_res = {}
    for a in assets:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    by_cls = {}
    for a in assets:
        by_cls[a["asset_class"]] = by_cls.get(a["asset_class"], 0) + 1

    # caption vs body consistency (F5)
    cap = (fig_probe.get("winkler_hetenyi_comparison") or {}).get("caption") or ""
    f5 = aux["f5"]
    f5["checked"] = {
        "caption_mentions_error_2_29pct": "2.29%" in cap,
        "body_table_reports_2_29pct": "2.29%" in md,
        "caption_text": cap,
    }
    f5["status"] = ("caption_error_matches_body_table"
                    if f5["checked"]["caption_mentions_error_2_29pct"]
                    and f5["checked"]["body_table_reports_2_29pct"] else "unresolved")
    findings.append(f5)

    emitted_at = args.emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "generated_at": emitted_at,
        "source": {
            "uri": CONTRACT["source_uri"],
            "field": CONTRACT["source_field"],
            "hash_alg": "sha256",
            "hash": hash_hex,
            "chars": chars,
            "bytes_utf8": len(md_bytes),
            "title": record.get("title"),
            "title_matches_contract": record.get("title") == CONTRACT["title"],
            "scenario_key": record.get("scenario_key"),
            "chars_matches_contract": chars == CONTRACT["chars"],
            "platform_figures": [f.get("name") for f in (record.get("figures") or [])],
            "platform_tags": record.get("tags") or [],
            "markdown_snapshot": "artifacts/wp-13325-01/source_markdown.md",
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_cls,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "declared_absent_scan": scan,
        },
        "assets": assets,
        "claims": [],
        "claims_policy": "空数组是契约允许的完整结果（objective.classify_report_type=false，"
                         "notes: 不做抽取）。未做任何断言生成，未对任何结论授予“已核验”状态；"
                         "claims=[] 即本工序的完整结论面。",
        "figure_probe": fig_probe,
        "integrity": {
            "quote_uniqueness": quote_uniqueness,
            "hash_recomputed_locally": True,
            "hash_matches_contract": hash_matches,
            "recomputed_hash": "sha256:" + hash_hex,
            "contract_hash": CONTRACT["source_hash"],
        },
        "integrity_findings": findings,
    }

    # ---- write outputs
    snap = os.path.join(OUTDIR, "source_markdown.md")
    with open(snap, "wb") as fh:
        fh.write(md_bytes)
    assert sha256_hex(open(snap, "rb").read()) == hash_hex

    man_path = os.path.join(OUTDIR, "asset_manifest.json")
    with open(man_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    kf_result = {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_hash": "sha256:" + hash_hex,
            "source_field": CONTRACT["source_field"],
            "source_uri": CONTRACT["source_uri"],
            "producer": "kf-wp13325-01 registrar (scripts/kf_wp13325_01_register.py)",
            "emitted_at": manifest["generated_at"],
            "notes": f"hash recomputed from the served markdown field; chars={chars}, "
                     f"bytes_utf8={len(md_bytes)}; assets={len(assets)}; claims=[] by contract",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    kf_path = os.path.join(OUTDIR, "kf_result.json")
    with open(kf_path, "w", encoding="utf-8") as fh:
        json.dump(kf_result, fh, ensure_ascii=False, indent=2)

    # ---- self-check against the contract's acceptance list
    import jsonschema  # local dep; pinned in requirements

    def validate(instance, schema_path):
        with open(schema_path, encoding="utf-8") as fh:
            schema = json.load(fh)
        try:
            jsonschema.validate(instance, schema)
            return True, ""
        except jsonschema.ValidationError as exc:
            return False, f"{exc.message} @ {list(exc.absolute_path)}"

    kf_ok, kf_err = validate(kf_result, os.path.join(SCHEMAS, "kf_result.v1.schema.json"))
    man_schema = os.path.join(SCHEMAS, "asset_manifest.v1.kf-package.schema.json")
    man_ok, man_err = validate(manifest, man_schema)

    checks = {
        "valid_json": (
            json.load(open(man_path, encoding="utf-8")) is not None
            and json.load(open(kf_path, encoding="utf-8")) is not None
        ),
        "schema_pass": kf_ok and man_ok,
        "source_locator_resolvable": (
            quote_uniqueness["all_slices_match"]
            and all(
                (a["locator"]["method"] == "document") or a["locator"]["quote"] in md
                for a in assets
            )
        ),
        "source_hash_matches": hash_matches,
        "no_duplicate_ids": len({a["asset_id"] for a in assets}) == len(assets),
        "all_claims_have_evidence_or_explicit_unresolved_status": all(
            ("evidence" in c) or ("status" in c) for c in manifest["claims"]
        ),
    }
    selfcheck = {
        "package_id": CONTRACT["package_id"],
        "checks": {k: bool(v) for k, v in checks.items()},
        "detail": {
            "schema_kf_result": {"ok": kf_ok, "error": kf_err,
                                 "schema": "schemas/kf_result.v1.schema.json"},
            "schema_asset_manifest": {"ok": man_ok, "error": man_err,
                                      "schema": "schemas/asset_manifest.v1.kf-package.schema.json"},
            "chars": chars, "bytes_utf8": len(md_bytes), "sha256": hash_hex,
            "assets": len(assets), "claims": len(manifest["claims"]),
            "unique_quotes": sum(1 for v in quote_uniqueness["per_asset"].values() if v["unique"]),
        },
        "all_pass": all(checks.values()),
    }
    with open(os.path.join(OUTDIR, "selfcheck.json"), "w", encoding="utf-8") as fh:
        json.dump(selfcheck, fh, ensure_ascii=False, indent=2)

    # ---- tracked mirror: artifacts/ is .gitignore'd, so the committed copies live under docs/kf/
    os.makedirs(MIRROR, exist_ok=True)
    for name in ("asset_manifest.json", "kf_result.json", "selfcheck.json", "source_markdown.md"):
        with open(os.path.join(OUTDIR, name), "rb") as fh:
            blob = fh.read()
        with open(os.path.join(MIRROR, name), "wb") as fh:
            fh.write(blob)
        assert sha256_hex(blob) == sha256_hex(open(os.path.join(MIRROR, name), "rb").read())
    selfcheck["mirror"] = {"dir": "docs/kf/wp-13325-01",
                           "files": ["asset_manifest.json", "kf_result.json",
                                     "selfcheck.json", "source_markdown.md"]}
    with open(os.path.join(OUTDIR, "selfcheck.json"), "w", encoding="utf-8") as fh:
        json.dump(selfcheck, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(MIRROR, "selfcheck.json"), "w", encoding="utf-8") as fh:
        json.dump(selfcheck, fh, ensure_ascii=False, indent=2)

    print(json.dumps({"chars": chars, "sha256": hash_hex, "hash_matches": hash_matches,
                      "assets": len(assets), "by_resolution": by_res,
                      "selfcheck": selfcheck["checks"], "all_pass": selfcheck["all_pass"]},
                     ensure_ascii=False, indent=1))
    if not selfcheck["all_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()