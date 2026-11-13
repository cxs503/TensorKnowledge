#!/usr/bin/env python3
"""Work package wp-9645-01 (task_type 01-asset-registration): register the source assets of
report 9645 -- "IN101-N09 ISO 19906 ice-pressure partial-factor back-calibration at beta_T=4.0".

Scope guard (contract of work package wp-9645-01):
  * touches ONLY report_id=9645 -- no other report is read or written;
  * registration only: NO claim extraction, NO report-type classification, NO `verified`
    marks (verification is computed by the platform gate, not here);
  * zero manual transcription -- every number, table row and quote in every artifact below is
    measured from the markdown bytes served by GET /api/v1/tensor/reports/9645 (cached verbatim
    as docs/kf/wp-9645-01/source.md) and re-checked as an exact character slice at verify time;
  * missing information stays missing: an artifact whose bytes were not read is registered as
    `referenced_unresolved` / `declared_absent` with a reason -- no hash is ever invented;
  * the source hash is pinned (CONTRACT). A re-fetch that disagrees aborts the build instead of
    silently re-registering a drifted source.

Sub-commands (idempotent: no timestamps, so re-runs are byte-identical):
    fetch      GET report 9645 (id-guarded), cache the markdown bytes -> source.md
    build      measure source.md -> asset_manifest.json (+ embedded registered-value audit)
    schema     derive asset_manifest.schema.json from schemas/asset_manifest.v1.schema.json
    locators   independent second pass over every locator -> locator_check.json
    envelope   kf_result.v1 envelope embedding the manifest -> kf_result.json
    figure     asset_coverage.png
    report     six-element report, numbers injected from the JSON -> report_body.md
    sha        sha256.txt
    verify     offline re-derivation of every committed artifact; exit 1 on any mismatch
    all        fetch build schema locators envelope figure report sha verify

Offline contract: after source.md exists, build/verify need no network. Only `fetch` needs
platform credentials (TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_ID = "9645"
PACKAGE_ID = "wp-9645-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
SOURCE_FIELD = "markdown"
PRODUCER = "kf-worker/m18776"

OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID     # committed: repo .gitignore drops artifacts/**
SOURCE_MD = OUT_DIR / "source.md"               # verbatim cache of the markdown field
MANIFEST = OUT_DIR / "asset_manifest.json"
LOCAL_SCHEMA = OUT_DIR / "asset_manifest.schema.json"
ENVELOPE = OUT_DIR / "kf_result.json"
LOCATOR = OUT_DIR / "locator_check.json"
REPORT_BODY = OUT_DIR / "report_body.md"
SHA_TXT = OUT_DIR / "sha256.txt"
COVERAGE = OUT_DIR / "asset_coverage.png"
SHARED_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.schema.json"
KF_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"

# Pinned at first registration (report 9645, status=published). A later re-fetch whose bytes or
# counts differ means the source drifted: abort rather than silently re-pin.
CONTRACT = {
    "source_hash": "sha256:a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00",
    "chars": 11824,
    "lines": 196,
    "title_prefix": "IN101-N09 ISO 19906 冰压设计分项系数目标可靠度反标定",
    "scenario_key": "ice_partial_factors_target_inverse",
    "report_mission_id": 8350,
}

# Tolerances of the registered-value audit. Display rounding dominates on a report table, so
# each family carries an explicit budget instead of a single global epsilon.
TOL = {
    "kappa_product": 5e-6,        # relative: kappa = gamma_f * psi on 6-decimal inputs
    "kappa_vs_ratio": 2e-4,       # relative: kappa* vs R_k/F_k on 5-/3-significant-digit inputs
    "phi": 5e-3,                  # relative: P_f = Phi(-beta) with beta printed to 6 decimals
    "percent_pp": 0.011,          # absolute, percentage points: 2-decimal printed deviation
    "abs_small": 1e-4,            # absolute: Delta-beta printed to 4 decimals
    "multiple": 2e-4,             # relative: P_f multiples printed as "9.39x"
    "derivative": 5e-4,           # absolute: central-difference derivative printed to 4 decimals
    "cross_table": 2e-3,          # relative: the same quantity quoted in two sections
}

NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)\)")
CODE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
SEP_RE = re.compile(r"^\|[\s:\-|]+$")


# --------------------------------------------------------------------- small helpers
def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def _sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def _line_of(md: str, pos: int) -> int:
    return md.count("\n", 0, pos) + 1


def _offsets(md: str) -> list[int]:
    """Char offset of the start of every line (1-based line n -> offsets[n-1])."""
    off = [0]
    for i, ch in enumerate(md):
        if ch == "\n":
            off.append(i + 1)
    return off


def _span_of_lines(md: str, off: list[int], start_line: int, end_line: int) -> tuple[int, int]:
    start = off[start_line - 1]
    end = off[end_line] - 1 if end_line < len(off) else len(md)
    return start, end


def _num(text: str):
    """First number of a table cell (markdown emphasis and thousands separators stripped)."""
    m = NUM_RE.search(text.replace("**", "").replace(",", ""))
    return float(m.group(0)) if m else None


def _nums(text: str) -> list[float]:
    return [float(x) for x in NUM_RE.findall(text.replace("**", "").replace(",", ""))]


def _decimals(text: str) -> int:
    m = re.search(r"\.(\d+)", text)
    return len(m.group(1)) if m else 0


def _ulp(text: str) -> float:
    """Half a unit in the last printed digit: the rounding budget of a displayed value."""
    d = _decimals(text)
    return 0.5 * 10 ** (-d) if d else 0.5


def _rel_err(declared: float, recomputed: float) -> float:
    if recomputed == 0:
        return abs(declared)
    return abs(declared - recomputed) / abs(recomputed)


def phi(x: float) -> float:
    """Standard normal CDF via the complementary error function (no scipy dependency)."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


# --------------------------------------------------------------------- markdown parsing
def split_cells(row: str) -> list[str]:
    """Split a markdown table row on '|' while ignoring pipes inside inline math ($...$)."""
    s = row.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    cells, buf, in_math = [], "", False
    for ch in s:
        if ch == "$":
            in_math = not in_math
        if ch == "|" and not in_math:
            cells.append(buf.strip())
            buf = ""
        else:
            buf += ch
    cells.append(buf.strip())
    return cells


def table_semantic(header: str) -> str:
    h = header
    # LaTeX markup is normalised away so that a header can be matched without depending on
    # whether the author wrote \kappa_{table} or kappa_table (both occur across reports)
    flat = re.sub(r"[\\${}\s]", "", h).replace("mathrm", "")
    if "机器判据" in h:
        return "machine_criteria"
    if h.strip().startswith("| 参数 | 取值 | 说明"):
        return "param_table"
    if h.strip().startswith("| 量 | 值 |"):
        return "t1_inverse"
    if "与 FORM 相对误差" in h:
        return "t2_form_verify"
    if "解析（伴随）" in h:
        return "t3_derivatives"
    if "表格值" in h and "kappa_table" in flat:
        return "t4_iso_deviation"
    if "P_f/P_f,T" in flat:
        return "t5_nonconservative"
    if "sigma_lnF" in flat:
        return "t6_negative_control"
    if "dgamma_f/dbeta_T" in flat:
        return "t7_beta_t_sensitivity"
    if "partialbeta/partialtheta" in flat:
        return "t8_param_sensitivity"
    if "关键量 | 基准 | 误差" in h:
        return "error_judgement"
    return "unknown"


def parse_tables(md: str, off: list[int]) -> list[dict]:
    lines = md.split("\n")
    tables = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("|") and i + 1 < len(lines) and SEP_RE.match(lines[i + 1].strip()):
            start, j = i, i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            rows = [{"line": k + 1, "cells": split_cells(lines[k]), "text": lines[k]}
                    for k in range(start + 2, j)]
            label = None
            if start > 0:
                m = re.search(r"\*\*(表\s*\d+[^*]*)\*\*", lines[start - 1])
                if m:
                    label = m.group(1).strip()
            s_char, e_char = _span_of_lines(md, off, start + 1, j)
            tables.append({
                "table_id": "T%02d" % (len(tables) + 1),
                "semantic": table_semantic(lines[start]),
                "author_label": label,
                "header": lines[start],
                "header_block": lines[start] + "\n" + lines[start + 1],
                "start_line": start + 1,
                "end_line": j,
                "start_char": s_char,
                "end_char": e_char,
                "n_rows": len(rows),
                "rows": rows,
            })
            i = j
        else:
            i += 1
    return tables


def parse_sections(md: str, off: list[int]) -> list[dict]:
    lines = md.split("\n")
    idx = [k for k, ln in enumerate(lines) if ln.startswith("#")]
    sections = []
    for n, k in enumerate(idx):
        end = (idx[n + 1] - 1) if n + 1 < len(idx) else len(lines) - 1
        heading = lines[k]
        s_char, e_char = _span_of_lines(md, off, k + 1, k + 1)
        sections.append({
            "section_id": "S%02d" % (n + 1),
            "level": len(heading) - len(heading.lstrip("#")),
            "heading": heading,
            "start_line": k + 1,
            "end_line": end + 1,
            "start_char": s_char,
            "end_char": e_char,
            "chars": off[end] - off[k] if end < len(off) else len(md) - off[k],
        })
    return sections


def section_of_line(sections: list[dict], line: int) -> str:
    for s in sections:
        if s["start_line"] <= line <= s["end_line"]:
            return s["heading"].lstrip("# ").strip()
    return "preamble"


def scan_references(md: str, off: list[int]) -> list[dict]:
    """Every image/link target and every path-like inline code span, with a line locator."""
    refs = []

    def push(hint, path, via, alt, pos):
        ln = _line_of(md, pos)
        s_char, e_char = _span_of_lines(md, off, ln, ln)
        refs.append({"kind_hint": hint, "path": path, "via": via, "alt": alt, "line": ln,
                     "start_char": s_char, "end_char": e_char, "quote": md[s_char:e_char]})

    for m in IMG_RE.finditer(md):
        push("image", m.group(2), "markdown_image", m.group(1), m.start())
    linked = {m.group(2) for m in IMG_RE.finditer(md)}
    for m in LINK_RE.finditer(md):
        if m.group(2) in linked:
            continue
        push("link", m.group(2), "markdown_link", m.group(1), m.start())
    for m in CODE_RE.finditer(md):
        span = m.group(1).strip()
        pm = re.search(r"(\S+\.(?:py|json|csv|txt|md|png|jpg))", span)
        if pm:
            push("code_path", pm.group(1), "inline_code", span, m.start())
        elif re.match(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*){2,}$", span):
            push("module", span, "inline_code", span, m.start())
    refs.sort(key=lambda r: r["start_char"])
    return refs


def kind_of(ref: dict) -> str:
    if ref["kind_hint"] == "module":
        return "library_reference"
    suffix = Path(ref["path"]).suffix
    if suffix in (".png", ".jpg", ".jpeg"):
        return "figure_reference"
    if suffix in (".json", ".csv"):
        return "data_artifact_reference"
    if suffix == ".py":
        return "source_code_reference"
    return "document_reference"


# --------------------------------------------------------------------- platform I/O
def _api_base() -> str:
    return os.environ["TENSOR_API_BASE"].rstrip("/")


def _req(url: str, token: str | None = None, data: bytes | None = None,
         ctype: str = "application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def login() -> str:
    base = _api_base()
    user, pw = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    try:
        d = _req(base + "/auth/login", data=json.dumps({"username": user, "password": pw}).encode())
    except urllib.error.HTTPError:
        d = _req(base + "/auth/login",
                 data=urllib.parse.urlencode({"username": user, "password": pw}).encode(),
                 ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_record() -> dict:
    """GET report 9645 with a hard id guard; cache the markdown bytes verbatim."""
    d = _req("%s/tensor/reports/%s" % (_api_base(), REPORT_ID), login())
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    if str(d.get("id")) != REPORT_ID:
        raise SystemExit("scope violation: served report id %r != %s" % (d.get("id"), REPORT_ID))
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s carries no markdown field" % REPORT_ID)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_MD.write_text(md, encoding="utf-8")
    return d


def platform_record_meta(record: dict) -> dict:
    """Record metadata minus any payload bytes (a caption is metadata, a png is not)."""
    figs = [{"name": f.get("name"), "caption": f.get("caption"),
             "has_payload": bool(f.get("png_base64"))} for f in record.get("figures") or []]
    return {
        "id": str(record.get("id")),
        "title": record.get("title"),
        "summary": record.get("summary"),
        "scenario_key": record.get("scenario_key"),
        "mission_id": record.get("mission_id"),
        "status": record.get("status"),
        "stage": record.get("stage"),
        "tags": record.get("tags") or [],
        "created_at": record.get("created_at"),
        "created_by": record.get("created_by"),
        "figures": figs,
    }

# --------------------------------------------------------------------- registered-value audit
def _check(cid: str, family: str, quantity: str, declared, recomputed, tol: float,
           kind: str = "relative", where: str = "") -> dict:
    if kind == "relative":
        err = _rel_err(float(declared), float(recomputed))
    else:
        err = abs(float(declared) - float(recomputed))
    return {
        "check_id": cid,
        "family": family,
        "quantity": quantity,
        "declared": declared,
        "recomputed": round(float(recomputed), 12),
        "error": err,
        "error_kind": kind,
        "tolerance": tol,
        "verdict": "PASS" if err <= tol else "FAIL",
        "locator": where,
    }


def _after(text: str, anchor: str):
    """First number appearing after a literal anchor string (None if the anchor is absent)."""
    i = text.find(anchor)
    if i < 0:
        return None
    m = NUM_RE.search(text[i + len(anchor):])
    return float(m.group(0)) if m else None


def number_audit(md: str, tables: list[dict]) -> dict:
    """Arithmetically re-derive the numbers this report publishes about itself.

    ADDITIVE registration self-check (the 01 contract only asks for assets): every quantity
    below is recomputed from other published numbers of the same source, so a transcription
    error or an internally inconsistent number is caught at registration time instead of being
    inherited by downstream knowledge objects. No physics is re-derived: solver outputs
    (FORM/IS/MC estimates, Jacobian, adjoint derivatives) are never reconstructed here, only
    cross-checked against the second place the report quotes them.
    """
    T = {t["semantic"]: t for t in tables}
    checks: list[dict] = []
    not_audited: list[dict] = []
    families: dict[str, dict] = {}

    def add(chk: dict) -> None:
        checks.append(chk)
        fam = families.setdefault(chk["family"], {"checks": 0, "passed": 0, "max_error": 0.0})
        fam["checks"] += 1
        fam["passed"] += 1 if chk["verdict"] == "PASS" else 0
        fam["max_error"] = max(fam["max_error"], chk["error"])

    def rows_of(sem: str, eid: str) -> list[dict]:
        t = T.get(sem)
        if t is None:
            not_audited.append({"id": eid, "reason": "table %s not found in source" % sem})
            return []
        return t["rows"]

    # published scalars, parsed out of 表1 (反问题解) -- never hand copied
    t1 = T.get("t1_inverse")
    if t1 is None:
        raise SystemExit("cannot audit: table 表1 (反问题解) not found")
    scalar = {r["cells"][0]: (_num(r["cells"][1]) if len(r["cells"]) > 1 else None)
              for r in t1["rows"]}
    g_gamma = scalar.get(r"$\gamma_f^*$")
    g_psi = scalar.get(r"$\psi^*$")
    g_kappa = scalar.get(r"$\kappa^*=\gamma_f^*\psi^*$")
    g_fstar = scalar.get(r"$F^*$ (设计点冰力)")
    g_rstar = scalar.get(r"$R^*$ (设计点抗力)")
    g_beta = scalar.get(r"达到的 $\beta$")
    if None in (g_gamma, g_psi, g_kappa):
        raise SystemExit("cannot audit: gamma_f/psi/kappa rows of 表1 unparsed")

    head = "\n".join(md.split("\n")[:10])   # headline block: title line + 目标/判据 lines
    m_bt = re.search(r"beta_T\$?\s*=\s*([0-9.]+)", head)
    m_pf = re.search(r"\$P_f\$\s*=\s*([0-9.eE+-]+)", head)
    if not (m_bt and m_pf):
        raise SystemExit("cannot audit: beta_T / P_f target not parsed from the headline")
    beta_target = float(m_bt.group(1))
    pf_target = float(m_pf.group(1))

    # F1: kappa = gamma_f * psi  (表1, 表6 x2, 表7 x4)
    add(_check("F1.1", "F1_kappa_product", "kappa* = gamma_f* * psi*", g_kappa,
               g_gamma * g_psi, TOL["kappa_product"], where="表1 反问题解"))
    for r in rows_of("t6_negative_control", "F1.2")[:2]:
        k, gf, ps = _num(r["cells"][1]), _num(r["cells"][2]), _num(r["cells"][3])
        add(_check("F1.2.%d" % len(checks), "F1_kappa_product",
                   "kappa = gamma_f * psi (%s)" % r["cells"][0][:26], k, gf * ps,
                   TOL["kappa_product"], where="表6 行 %d" % r["line"]))
    for r in rows_of("t7_beta_t_sensitivity", "F1.3")[:4]:
        gf, ps, k = _num(r["cells"][2]), _num(r["cells"][3]), _num(r["cells"][4])
        # 表7 prints 5 decimals, so the product inherits the rounding of three displayed values
        tol7 = (_ulp(r["cells"][2]) / abs(gf) + _ulp(r["cells"][3]) / abs(ps)
                + _ulp(r["cells"][4]) / abs(k) + 1e-9)
        add(_check("F1.3.%d" % len(checks), "F1_kappa_product",
                   "kappa*(beta_T=%s) = gamma_f * psi" % r["cells"][0], k, gf * ps,
                   tol7, where="表7 行 %d" % r["line"]))

    # F2: the calibrated factor product is the characteristic action/resistance ratio
    Fk = Rk = None
    for r in rows_of("param_table", "F2.1"):
        if len(r["cells"]) > 1:
            if "F_k" in r["cells"][0]:
                Fk = _num(r["cells"][1])
            elif "R_k" in r["cells"][0]:
                Rk = _num(r["cells"][1])
    if Fk and Rk:
        add(_check("F2.1", "F2_kappa_vs_ratio", "kappa* = R_k / F_k", g_kappa, Rk / Fk,
                   TOL["kappa_vs_ratio"], where="表1 反问题解 + 参数表"))
    else:
        not_audited.append({"id": "F2.1", "reason": "F_k / R_k rows not parsed from 参数表"})

    # F3: P_f = Phi(-beta), for the target and for every beta_T row of 表7
    add(_check("F3.1", "F3_phi", "P_f(beta_T=%.2f) = Phi(-beta_T)" % beta_target,
               pf_target, phi(-beta_target), TOL["phi"], where="H1 目标行"))
    for r in rows_of("t7_beta_t_sensitivity", "F3.2")[:4]:
        bt, pf = _num(r["cells"][0]), _num(r["cells"][1])
        add(_check("F3.2.%d" % len(checks), "F3_phi",
                   "P_f,T(beta_T=%s) = Phi(-beta_T)" % r["cells"][0], pf, phi(-bt),
                   TOL["phi"], where="表7 行 %d" % r["line"]))

    # F4: 表4 -- table factor pairs, their product, and their deviation from the calibrated pair
    for n, r in enumerate(rows_of("t4_iso_deviation", "F4.1")):
        c = r["cells"]
        pair = _nums(c[1])
        if len(pair) < 2:
            not_audited.append({"id": "F4.%d" % n, "reason": "factor pair unparsed"})
            continue
        gF, gM, ktab = pair[0], pair[1], _num(c[2])
        where = "表4 行 %d" % r["line"]
        tag = c[0][:30]
        add(_check("F4.%d.1" % n, "F4_iso_table", "kappa_table = gamma_F * gamma_M (%s)" % tag,
                   ktab, gF * gM, TOL["kappa_product"], where=where))
        add(_check("F4.%d.2" % n, "F4_iso_table", "Delta kappa (%s)" % tag, _num(c[5]),
                   (ktab / g_kappa - 1.0) * 100.0, TOL["percent_pp"], kind="absolute", where=where))
        add(_check("F4.%d.3" % n, "F4_iso_table", "Delta gamma_f (%s)" % tag, _num(c[3]),
                   (gF / g_gamma - 1.0) * 100.0, TOL["percent_pp"], kind="absolute", where=where))
        add(_check("F4.%d.4" % n, "F4_iso_table", "Delta psi (%s)" % tag, _num(c[4]),
                   (gM / g_psi - 1.0) * 100.0, TOL["percent_pp"], kind="absolute", where=where))

    # F5: 表5 -- achieved beta deficit and the P_f multiple of the non-conservative rows
    pf_t = phi(-beta_target)
    for n, r in enumerate(rows_of("t5_nonconservative", "F5.1")):
        c = r["cells"]
        beta_row, mult = _num(c[2]), _num(c[4])
        where = "表5 行 %d" % r["line"]
        add(_check("F5.%d.1" % n, "F5_nonconservative", "Delta beta = beta_T - beta (%s)" % c[0][:30],
                   _num(c[3]), beta_target - beta_row, TOL["abs_small"], kind="absolute", where=where))
        if mult:
            # tolerance = display rounding of the printed multiple (e.g. "1.76x" -> 2.8e-3)
            tol_mult = 1.05 * _ulp(c[4]) / abs(mult)
            add(_check("F5.%d.2" % n, "F5_nonconservative", "P_f/P_f,T (%s)" % c[0][:30],
                       mult, phi(-beta_row) / pf_t, tol_mult, where=where))
        not_audited.append({"id": "F5.%d.3" % n,
                            "reason": "column 'required R_k / calibrated R_k' needs the run_study() "
                                      "results JSON, which this package registers as unresolved; "
                                      "not reconstructed"})

    # F6: 表6 -- the negative-control deltas quoted in the paragraph under the table
    t6 = T.get("t6_negative_control")
    if t6 is not None and len(t6["rows"]) >= 2:
        tail = md[t6["end_char"]:t6["end_char"] + 600]
        d_gamma = _after(tail, r"\Delta\gamma_f^*$ = +")
        d_kappa = _after(tail, r"\Delta\kappa^*$ = +")
        g_in = [_num(t6["rows"][0]["cells"][i]) for i in (1, 2)]
        g_out = [_num(t6["rows"][1]["cells"][i]) for i in (1, 2)]
        if d_gamma is not None:
            add(_check("F6.1", "F6_negative_control", "Delta gamma_f*, percent", d_gamma,
                       (g_out[1] / g_in[1] - 1.0) * 100.0, TOL["percent_pp"], kind="absolute",
                       where="表6 下方结论段"))
        if d_kappa is not None:
            add(_check("F6.2", "F6_negative_control", "Delta kappa*, percent", d_kappa,
                       (g_out[0] / g_in[0] - 1.0) * 100.0, TOL["percent_pp"], kind="absolute",
                       where="表6 下方结论段"))
        not_audited.append({"id": "F6.3",
                            "reason": "the over-design beta=4.6597 quoted in the same paragraph "
                                      "needs the FORM solve; solver output is not re-derived here"})
    else:
        not_audited.append({"id": "F6.1", "reason": "negative-control rows unparsed"})

    # F7: 表7 -- central-difference derivative of gamma_f in beta_T
    t7 = T.get("t7_beta_t_sensitivity")
    if t7 is not None:
        rr = t7["rows"]
        for i in range(1, len(rr) - 1):
            b0, b1 = _num(rr[i - 1]["cells"][0]), _num(rr[i + 1]["cells"][0])
            g0, g1 = _num(rr[i - 1]["cells"][2]), _num(rr[i + 1]["cells"][2])
            decl = _num(rr[i]["cells"][5])
            if None in (b0, b1, g0, g1, decl) or b1 == b0:
                continue
            add(_check("F7.%d" % i, "F7_derivative",
                       "d gamma_f/d beta_T at beta_T=%s" % rr[i]["cells"][0], decl,
                       (g1 - g0) / (b1 - b0), TOL["derivative"], kind="absolute",
                       where="表7 行 %d" % rr[i]["line"]))
        not_audited.append({"id": "F7.edge",
                            "reason": "the two edge rows of 表7 have no neighbour to difference"})

    # F8: 表2 -- the FORM cross-validation table's own relative-error column
    t2 = T.get("t2_form_verify")
    if t2 is not None:
        for n, r in enumerate(t2["rows"]):
            c = r["cells"]
            if len(c) < 4:
                continue
            beta_row, decl = _num(c[1]), _num(c[3])
            if decl is None or beta_row is None or g_beta is None:
                continue
            if "重要性抽样" in c[0] or "Monte Carlo" in c[0] or "抗力解析积分" in c[0]:
                add(_check("F8.%d" % n, "F8_form_table", "rel. error vs FORM (%s)" % c[0][:24],
                           decl, (beta_row - g_beta) / g_beta, TOL["cross_table"],
                           where="表2 行 %d" % r["line"]))
        not_audited.append({"id": "F8.analytic",
                            "reason": "the closed-form beta_ln row prints only its 2-digit error "
                                      "(6.46e-09), not the value it was computed from"})

    # F9: 表3 -- adjoint derivative vs central difference, with a display-rounding budget
    t3 = T.get("t3_derivatives")
    if t3 is not None:
        for r in t3["rows"]:
            c = r["cells"]
            if len(c) < 4 or c[0].startswith("最大"):
                continue
            an, fd, decl = _num(c[1]), _num(c[2]), _num(c[3])
            if None in (an, fd, decl) or not an:
                continue
            # the audited quantity IS a relative error (~1e-7): compare it absolutely, with a
            # budget equal to the propagated display rounding of the two printed derivatives
            tol = _ulp(c[1]) / abs(an) + _ulp(c[2]) / abs(fd) + 1e-9
            add(_check("F9.%d" % len(checks), "F9_adjoint_table",
                       "rel. error adjoint vs central difference (%s)" % c[0][:26], decl,
                       (an - fd) / an, max(tol, 1e-7), kind="absolute",
                       where="表3 行 %d" % r["line"]))
        not_audited.append({"id": "F9.max",
                            "reason": "表3 '最大相对误差' row is the maximum of the rows above"})

    # F10: design-point equality and the achieved index in 表1
    if g_fstar and g_rstar:
        add(_check("F10.1", "F10_inverse_consistency", "F* = R* at the design point", g_fstar,
                   g_rstar, TOL["abs_small"], kind="absolute", where="表1 反问题解"))
    if g_beta is not None:
        add(_check("F10.2", "F10_inverse_consistency", "achieved beta = beta_T", g_beta,
                   beta_target, TOL["abs_small"], kind="absolute", where="表1 反问题解"))
    not_audited.append({"id": "F10.3",
                        "reason": "Jacobian condition number, three-start spread and the "
                                  "bisection value are solver outputs, not re-derived here"})

    # F11: the 机器判据 table vs the "5/5 通过" summary line
    tmc = T.get("machine_criteria")
    if tmc is not None:
        verdicts = [r["cells"][1].strip() for r in tmc["rows"] if len(r["cells"]) > 1]
        n_pass = sum(1 for v in verdicts if v.upper().startswith("PASS"))
        m_sum = re.search(r"判据汇总\*\*\s*(\d+)/(\d+)\s*通过", md)
        if m_sum:
            add(_check("F11.1", "F11_criteria_summary", "declared PASS count vs criteria table",
                       float(m_sum.group(1)), float(n_pass), 0.0, kind="absolute",
                       where="机器判据表 + 判据汇总行"))
            add(_check("F11.2", "F11_criteria_summary", "declared total vs criteria table rows",
                       float(m_sum.group(2)), float(len(verdicts)), 0.0, kind="absolute",
                       where="机器判据表 + 判据汇总行"))

    # F12: the same quantity quoted twice (section 6 vs the tables it summarises)
    tej = T.get("error_judgement")
    if tej is not None and t2 is not None:
        # ⑥ and 表2 name the same estimators differently: map (section 6 label, table 2 label)
        for key, token, token_two in (("粗 MC", "粗 MC", "粗 Monte Carlo"),
                                      ("重要性抽样", "重要性抽样", "重要性抽样"),
                                      ("闭式", "闭式", "闭式")):
            row_six = next((r for r in tej["rows"]
                            if (token in r["cells"][0] and "FORM" in r["cells"][1])
                            or ("FORM" in r["cells"][0] and token in r["cells"][1])), None)
            row_two = next((r for r in t2["rows"] if token_two in r["cells"][0]), None)
            if row_six is None or row_two is None or len(row_two["cells"]) < 4:
                continue
            six_val = abs(_num(row_six["cells"][2]) or 0.0)
            two_val = abs(_num(row_two["cells"][3]) or 0.0)
            if not two_val:
                continue
            add(_check("F12.%s" % key, "F12_cross_section", "error quoted in ⑥ vs 表2 (%s)" % key,
                       six_val, two_val, TOL["cross_table"], where="⑥ 行 %d" % row_six["line"]))
    if tej is not None and t3 is not None:
        for r in t3["rows"]:
            if len(r["cells"]) < 4 or r["cells"][0].startswith("最大"):
                continue
            token = r["cells"][0].replace("$", "").split("partial")[-1].strip("\\{} ").strip()
            row_six = next((x for x in tej["rows"] if "伴随" in x["cells"][0] and token in
                            x["cells"][0].replace("$", "").replace("\\", "")), None)
            if row_six is None:
                continue
            add(_check("F12.adj.%s" % token, "F12_cross_section",
                       "adjoint error quoted in ⑥ vs 表3 (%s)" % token,
                       abs(_num(row_six["cells"][2]) or 0.0), abs(_num(r["cells"][3]) or 0.0),
                       1e-9, kind="absolute", where="⑥ 行 %d" % row_six["line"]))
    if tej is not None:
        row_iso = next((r for r in tej["rows"] if "ISO" in r["cells"][0]), None)
        t4 = T.get("t4_iso_deviation")
        if row_iso is not None and t4 is not None and t4["rows"]:
            dk = abs(_num(row_iso["cells"][2]) or 0.0)
            tab = abs((_num(t4["rows"][0]["cells"][5]) or 0.0) / 100.0)
            add(_check("F12.iso", "F12_cross_section", "ISO pair kappa deviation ⑥ vs 表4",
                       dk, tab, 1e-4, kind="absolute",
                       where="⑥ 行 %d" % row_iso["line"]))

    n_pass = sum(1 for c in checks if c["verdict"] == "PASS")
    return {
        "purpose": "recompute every number this source publishes about itself from other "
                   "published numbers of the same source; no solver output is re-derived",
        "families": families,
        "checks": checks,
        "not_audited": not_audited,
        "summary": {
            "checks": len(checks),
            "passed": n_pass,
            "failed": len(checks) - n_pass,
            "all_passed": n_pass == len(checks),
            "not_audited": len(not_audited),
        },
    }


# --------------------------------------------------------------------- manifest
def _locator(md: str, start: int, end: int, start_line: int, end_line: int) -> dict:
    quote = md[start:end]
    return {"method": "char_span", "start_char": start, "end_char": end,
            "start_line": start_line, "end_line": end_line, "quote": quote,
            "unique": md.count(quote) == 1}


def _resolution_of(ref: dict) -> tuple[str, str, str]:
    p = ref["path"]
    if p.startswith("/"):
        return ("referenced_unresolved", "unresolved",
                "absolute host path outside this worktree and not served as a platform "
                "attachment, so neither bytes nor a hash can be registered")
    if ref["kind_hint"] == "module":
        return ("referenced_unresolved", "unresolved",
                "cross-repository Python package (TensorPhysics); its content is not in this "
                "worktree and is not fetched by an asset-registration package")
    return ("referenced_unresolved", "unresolved",
            "cross-repository path (TensorPhysics); its content is not in this worktree")


def build_manifest(md: str, rec: dict) -> dict:
    off = _offsets(md)
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    tables = parse_tables(md, off)
    sections = parse_sections(md, off)
    refs = scan_references(md, off)
    audit = number_audit(md, tables)
    title_line = md.split("\n")[0]
    fig_by_name = {f.get("name"): f for f in rec.get("figures") or []}

    assets: list[dict] = []
    seen: set[str] = set()

    def add(a: dict) -> None:
        if a["asset_id"] in seen:
            raise SystemExit("duplicate asset_id %r" % a["asset_id"])
        seen.add(a["asset_id"])
        assets.append(a)

    # A01 -- the source markdown itself (document-level locator on the title line)
    t_start = 0
    t_end = len(title_line)
    add({
        "asset_id": "A01",
        "asset_class": "report_markdown",
        "label": "report %s markdown (the registered source)" % REPORT_ID,
        "in_report_section": "document",
        "resolution": "resolved_in_source",
        "resolution_check": {
            "check": "sha256 of the cached UTF-8 bytes equals the pinned contract hash and the "
                     "served report id equals %s" % REPORT_ID,
            "result": "resolved",
        },
        "locator": {"method": "document", "start_char": t_start, "end_char": t_end,
                    "start_line": 1, "end_line": 1, "quote": title_line,
                    "unique": md.count(title_line) == 1,
                    "doc_chars": len(md), "doc_bytes_utf8": len(raw),
                    "doc_lines": md.count("\n") + 1},
        "note": "Source of record for every locator in this manifest; cached verbatim as %s, "
                "so all quotes below can be re-sliced offline." % _rel(SOURCE_MD),
    })

    # A02.. -- every path-like reference in the body, in order of appearance
    for ref in refs:
        cls = kind_of(ref)
        res, res_result, reason = _resolution_of(ref)
        loc = _locator(md, ref["start_char"], ref["end_char"], ref["line"], ref["line"])
        name = Path(ref["path"]).name
        meta = fig_by_name.get(name)
        note = reason
        if cls == "figure_reference" and meta is not None:
            note = ("platform record lists this figure as name+caption only (png_base64 empty: "
                    "has_payload=%s); %s" % (bool(meta.get("has_payload")), reason))
        add({
            "asset_id": "A%02d" % (len(assets) + 1),
            "asset_class": cls,
            "label": ref["path"],
            "in_report_section": section_of_line(sections, ref["line"]),
            "resolution": res,
            "resolution_check": {"check": "attempt to read the referenced bytes from this "
                                          "worktree", "result": res_result},
            "locator": loc,
            "reference": {"path_reference": ref["path"], "via": ref["via"], "alt": ref["alt"],
                          "platform_figure_name": name if meta is not None else None,
                          "platform_caption": (meta or {}).get("caption")},
            "note": note,
        })

    # declared_absent: a normative table the report itself says it cannot verify
    iso_line = next((k for k, ln in enumerate(md.split("\n"), 1)
                     if "ISO 19906 Annex A 正文不在工作树内" in ln), None)
    if iso_line:
        s_char, e_char = _span_of_lines(md, off, iso_line, iso_line)
        add({
            "asset_id": "A%02d" % (len(assets) + 1),
            "asset_class": "standard_table_reference",
            "label": "ISO 19906 Annex A.2 (load factors) x A.3 (resistance factors)",
            "in_report_section": section_of_line(sections, iso_line),
            "resolution": "declared_absent",
            "resolution_check": {
                "check": "the report states the Annex A primary text is not in the worktree and "
                         "that A.2/A.3 were transcribed from secondary literature",
                "result": "absent",
            },
            "locator": _locator(md, s_char, e_char, iso_line, iso_line),
            "note": "Registered as declared_absent on the report's own authority "
                    "(source_tier=secondary, primary_source_verified=False in the results JSON). "
                    "No table value is copied into this manifest.",
        })

    # locator self-check (first pass; the second, independent pass lives in locator_check())
    resolved = sum(1 for a in assets if a["locator"]["quote"] in md)
    uniqueness = sum(1 for a in assets if a["locator"].get("unique"))
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    return {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "producer": PRODUCER,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": hashlib.sha256(raw).hexdigest(),
            "hash_scope": "UTF-8 bytes of the `markdown` field served by "
                          "GET /api/v1/tensor/reports/%s (byte-identical to %s)"
                          % (REPORT_ID, _rel(SOURCE_MD)),
            "chars": len(md),
            "bytes_utf8": len(raw),
            "lines": md.count("\n") + 1,
            "title": rec.get("title") or title_line,
            "scenario_key": rec.get("scenario_key") or "",
            "platform_figures": [f.get("name") for f in rec.get("figures") or []],
            "platform_tags": rec.get("tags") or [],
            "contract_hash": CONTRACT["source_hash"],
            "contract_chars": CONTRACT["chars"],
            "hash_matches_contract": "sha256:" + hashlib.sha256(raw).hexdigest()
                                     == CONTRACT["source_hash"],
            "chars_matches_contract": len(md) == CONTRACT["chars"],
            "title_matches_contract": (rec.get("title") or title_line)
                                      .startswith(CONTRACT["title_prefix"]),
            "scenario_matches_contract": (rec.get("scenario_key") or "")
                                          == CONTRACT["scenario_key"],
            "platform_record": rec,
        },
        "outline": {"sections": sections, "chars": len(md), "lines": md.count("\n") + 1},
        "tables": [{
            "table_id": t["table_id"],
            "semantic": t["semantic"],
            "author_label": t["author_label"],
            "header": t["header"],
            "header_quote": t["header_block"],
            "start_line": t["start_line"],
            "end_line": t["end_line"],
            "start_char": t["start_char"],
            "end_char": t["end_char"],
            "n_rows": t["n_rows"],
            "locator": _locator(md, t["start_char"], t["end_char"], t["start_line"], t["end_line"]),
        } for t in tables],
        "assets": assets,
        "number_audit": audit,
        "claims": [],
        "claims_empty_reason": "task_type=01-asset-registration carries no extraction duty "
                               "(no claim generation, no classification, no verification); an "
                               "empty claim list is the complete result for this package",
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "tables": len(tables),
            "sections": len(sections),
            "references_scanned": len(refs),
        },
        "integrity": {
            "quote_uniqueness": "%d/%d asset quotes occur exactly once in the source markdown; "
                                "every locator stays unambiguous because it is an exact "
                                "character slice re-checked at verify time"
                                % (uniqueness, len(assets)),
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == CONTRACT["source_hash"],
            "locators_checked": len(assets),
            "locators_resolved": resolved,
            "duplicate_asset_ids": 0,
            "source_copy": _rel(SOURCE_MD),
        },
    }


# --------------------------------------------------------------------- locator ledger
def locator_check(md: str, manifest: dict) -> dict:
    """Second, independent pass over every locator (re-reads the file, not the build state)."""
    off = _offsets(md)
    entries = []
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        q = loc["quote"]
        slice_ok = md[s:e] == q
        line_ok = (_line_of(md, s) == loc["start_line"]
                   and _line_of(md, max(s, e - 1)) == loc["end_line"])
        ok = slice_ok and line_ok
        entries.append({
            "asset_id": a["asset_id"],
            "asset_class": a["asset_class"],
            "method": loc["method"],
            "start_char": s, "end_char": e,
            "start_line": loc["start_line"], "end_line": loc["end_line"],
            "chars": len(q),
            "quote_head": q.split("\n")[0][:90],
            "slice_ok": slice_ok,
            "line_ok": line_ok,
            "unique": loc.get("unique"),
            "at_expected_offset": off[loc["start_line"] - 1] == s if loc["start_line"] - 1 < len(off) else False,
        })
        if not ok:
            bad.append({"asset_id": a["asset_id"], "slice_ok": slice_ok, "line_ok": line_ok})
    tables = []
    for t in manifest["tables"]:
        loc = t["locator"]
        slice_ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"]
        tables.append({"table_id": t["table_id"], "semantic": t["semantic"],
                       "start_line": t["start_line"], "end_line": t["end_line"],
                       "n_rows": t["n_rows"], "slice_ok": slice_ok,
                       "header_present": t["header"] in md})
        if not slice_ok or t["header"] not in md:
            bad.append({"table_id": t["table_id"], "slice_ok": slice_ok})
    sections = []
    for s in manifest["outline"]["sections"]:
        present = md[s["start_char"]:s["end_char"]] == s["heading"]
        sections.append({"section_id": s["section_id"], "heading": s["heading"],
                         "start_line": s["start_line"], "end_line": s["end_line"],
                         "heading_at_span": present})
        if not present:
            bad.append({"section_id": s["section_id"], "heading_at_span": present})
    return {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "source_sha256": _sha256_bytes(md.encode("utf-8")),
        "definition": "a locator is (start_char, end_char, start_line, end_line, quote) with "
                      "quote == source[start_char:end_char] and start_line == line(start_char); "
                      "re-checked here by re-reading source.md, not by trusting the build state",
        "counts": {
            "assets": len(entries),
            "assets_ok": sum(1 for e in entries if e["slice_ok"] and e["line_ok"]),
            "asset_quotes_unique": sum(1 for e in entries if e["unique"]),
            "tables": len(tables),
            "tables_ok": sum(1 for t in tables if t["slice_ok"] and t["header_present"]),
            "sections": len(sections),
            "sections_ok": sum(1 for s in sections if s["heading_at_span"]),
        },
        "assets": entries,
        "tables": tables,
        "sections": sections,
        "mismatches": bad,
        "all_ok": not bad,
    }


# --------------------------------------------------------------------- envelope / schema
def build_envelope(md: str, manifest: dict) -> dict:
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_hash_matches": manifest["source"]["hash_matches_contract"],
            "title": manifest["source"]["title"],
            "scenario_key": manifest["source"]["scenario_key"],
            "chars": manifest["source"]["chars"],
        },
        "outputs": {"asset_manifest.json": manifest},
    }


def build_local_schema() -> dict:
    """Derive this package's schema from the shared one, redirecting only the pinned consts.

    The shared schemas/asset_manifest.v1.schema.json pins package_id/report_id to another
    package, so it cannot validate this one; per the repo KF notes the shared schema is never
    edited -- a local instantiation is derived instead.
    """
    shared = json.loads(SHARED_SCHEMA.read_text(encoding="utf-8"))
    s = copy.deepcopy(shared)
    s["$id"] = "https://tensorplatform.local/schemas/asset_manifest.v1.%s.schema.json" % PACKAGE_ID
    s["title"] = "asset_manifest.v1 instantiated for KF work package %s" % PACKAGE_ID
    s["description"] = (
        "Derived from schemas/asset_manifest.v1.schema.json (never edited): only the pinned "
        "identity consts and the additive blocks introduced by this package (outline, tables, "
        "number_audit) differ. Field names and enums of the shared contract are unchanged, so a "
        "manifest valid here is valid against the shared shape except for the identity consts."
    )
    p = s["properties"]
    p["package_id"]["const"] = PACKAGE_ID
    p["report_id"]["const"] = REPORT_ID
    p["source"]["properties"]["uri"]["const"] = SOURCE_URI
    p["source"]["properties"].update({
        "contract_hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        "contract_chars": {"type": "integer", "minimum": 1},
        "hash_matches_contract": {"type": "boolean"},
        "chars_matches_contract": {"type": "boolean"},
        "title_matches_contract": {"type": "boolean"},
        "scenario_matches_contract": {"type": "boolean"},
        "platform_record": {"type": "object"},
    })
    p["outline"] = {"type": "object", "required": ["sections"],
                    "properties": {"sections": {"type": "array", "minItems": 1},
                                   "chars": {"type": "integer"},
                                   "lines": {"type": "integer"}}}
    p["tables"] = {"type": "array", "items": {
        "type": "object",
        "required": ["table_id", "header", "start_line", "end_line", "locator"],
        "properties": {"table_id": {"type": "string", "pattern": "^T[0-9]{2}$"},
                       "semantic": {"type": "string"},
                       "start_line": {"type": "integer", "minimum": 1},
                       "end_line": {"type": "integer", "minimum": 1},
                       "n_rows": {"type": "integer", "minimum": 0},
                       "locator": p["assets"]["items"]["properties"]["locator"]}}}
    p["number_audit"] = {
        "type": "object",
        "required": ["checks", "not_audited", "summary"],
        "properties": {
            "checks": {"type": "array", "items": {
                "type": "object",
                "required": ["check_id", "family", "quantity", "declared", "recomputed",
                             "error", "tolerance", "verdict"],
                "properties": {"verdict": {"enum": ["PASS", "FAIL"]},
                               "error_kind": {"enum": ["relative", "absolute"]}}}},
            "families": {"type": "object"},
            "not_audited": {"type": "array"},
            "summary": {"type": "object",
                        "required": ["checks", "passed", "failed", "all_passed"]},
        },
    }
    s["required"] = sorted(set(s["required"]) | {"outline", "tables", "number_audit"})
    return s


# --------------------------------------------------------------------- figure
def figure(manifest: dict, ledger: dict) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md = SOURCE_MD.read_text(encoding="utf-8")
    lines = md.split("\n")
    audit = manifest["number_audit"]

    class_color = {
        "report_markdown": "#2f4b7c",
        "figure_reference": "#a05195",
        "data_artifact_reference": "#2e8b57",
        "source_code_reference": "#c44e52",
        "library_reference": "#8c6d31",
        "standard_table_reference": "#7f7f7f",
    }
    res_hatch = {"resolved_in_source": None, "referenced_unresolved": "//",
                 "declared_absent": "xx"}

    fig = plt.figure(figsize=(13.2, 9.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0], width_ratios=[1.35, 1.0],
                          hspace=0.34, wspace=0.26)

    # panel A: locator map over the source document
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(range(1, len(lines) + 1), [len(x) for x in lines], color="0.72", lw=0.8,
             label="line length (chars)")
    for t in manifest["tables"]:
        ax1.axvspan(t["start_line"], t["end_line"], color="#f0c419", alpha=0.16, lw=0)
    ymax = max(len(x) for x in lines)
    for s in manifest["outline"]["sections"]:
        ax1.axvline(s["start_line"], color="0.55", lw=0.6, ls=":")
        # no CJK font is installed here, so section marks are labelled by id + ASCII stub
        stub = re.sub(r"[^\x20-\x7e]", "", s["heading"].lstrip("# "))
        ax1.text(s["start_line"] + 1.0, ymax * 0.97, s["section_id"] + " " + stub[:10].strip(),
                 fontsize=6.5, rotation=90, va="top", color="0.35")
    for a in manifest["assets"]:
        y = len(lines[a["locator"]["start_line"] - 1])
        col = class_color.get(a["asset_class"], "k")
        ax1.plot(a["locator"]["start_line"], y, "o", ms=6.5, color=col,
                 mfc=col if a["resolution"] == "resolved_in_source" else "white", mew=1.4)
        ax1.annotate(a["asset_id"], (a["locator"]["start_line"], y), textcoords="offset points",
                     xytext=(4, 5), fontsize=6.5, color=col)
    handles = [Line2D([], [], marker="o", ls="", color=v, label=k)
               for k, v in class_color.items()
               if any(a["asset_class"] == k for a in manifest["assets"])]
    handles.append(Line2D([], [], marker="o", ls="", mfc="white", mec="0.3",
                          label="registered but unresolved"))
    handles.append(Patch(color="#f0c419", alpha=0.4, label="table span"))
    ax1.legend(handles=handles, fontsize=6.8, loc="upper right", ncol=2)
    ax1.set_xlim(0.5, len(lines) + 0.5)
    ax1.set_xlabel("source.md line number")
    ax1.set_ylabel("line length (chars)")
    ax1.set_title("A. report 9645 registration map: %d assets over %d lines / %d chars "
                  "(source sha256 %s..., contract match %s)"
                  % (manifest["counts"]["assets"], len(lines), manifest["source"]["chars"],
                     manifest["source"]["hash"][:16], manifest["source"]["hash_matches_contract"]),
                  fontsize=9.5, loc="left")
    ax1.grid(alpha=0.22)

    # panel B: assets by class and resolution
    ax2 = fig.add_subplot(gs[1, 0])
    classes = sorted(manifest["counts"]["by_class"])
    for yi, cls in enumerate(classes):
        left = 0
        for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
            n = sum(1 for a in manifest["assets"]
                    if a["asset_class"] == cls and a["resolution"] == res)
            if not n:
                continue
            ax2.barh(yi, n, left=left, color=class_color.get(cls, "0.5"), alpha=0.55,
                     hatch=res_hatch[res], edgecolor="0.25", lw=0.6)
            ax2.text(left + n / 2.0, yi, str(n), ha="center", va="center", fontsize=8)
            left += n
    ax2.set_yticks(range(len(classes)))
    ax2.set_yticklabels(classes, fontsize=8)
    ax2.set_xlabel("assets")
    ax2.set_title("B. assets by class x resolution\n(solid = resolved, // = referenced_unresolved, "
                  "xx = declared_absent)", fontsize=9, loc="left")
    ax2.legend(handles=[Patch(facecolor="0.75", hatch=res_hatch[k], edgecolor="0.25", label=k)
                        for k in res_hatch], fontsize=7, loc="lower right")
    ax2.grid(alpha=0.22, axis="x")
    ax2.set_xlim(0, max(manifest["counts"]["by_class"].values()) + 2.5)

    # panel C: registered-value audit per family
    ax3 = fig.add_subplot(gs[1, 1])
    fams = sorted(audit["families"])
    sizes = [audit["families"][f]["checks"] for f in fams]
    passa = [audit["families"][f]["passed"] for f in fams]
    ax3.barh(range(len(fams)), sizes, color="#c44e52", alpha=0.45, edgecolor="0.25", lw=0.6)
    ax3.barh(range(len(fams)), passa, color="#55a868", alpha=0.85, edgecolor="0.25", lw=0.6)
    for i, f in enumerate(fams):
        ax3.text(sizes[i] + 0.15, i, "%d/%d  max err %.1e"
                 % (passa[i], sizes[i], audit["families"][f]["max_error"]),
                 va="center", fontsize=6.6)
    ax3.set_yticks(range(len(fams)))
    ax3.set_yticklabels(fams, fontsize=7)
    ax3.set_xlabel("registered-value checks (green = PASS)")
    ax3.set_title("C. registered-value arithmetic audit: %d/%d PASS\n(%d quantities quarantined "
                  "as not_audited, see report body 3.3-b)"
                  % (audit["summary"]["passed"], audit["summary"]["checks"],
                     audit["summary"]["not_audited"]), fontsize=9, loc="left")
    ax3.grid(alpha=0.22, axis="x")
    ax3.set_xlim(0, max(sizes) + 7)

    fig.suptitle("wp-9645-01 asset coverage -- report 9645 (IN101-N09, ISO 19906 ice partial "
                 "factors), locators %d/%d verified"
                 % (ledger["counts"]["assets_ok"], ledger["counts"]["assets"]),
                 fontsize=11, y=0.995)
    fig.savefig(COVERAGE, dpi=165, bbox_inches="tight")
    plt.close(fig)
    print("figure ->", _rel(COVERAGE))
    return COVERAGE


# --------------------------------------------------------------------- report body
def render_report(manifest: dict, ledger: dict) -> str:
    """Six-element report; every number is injected from the JSON artifacts, none is typed."""
    md = SOURCE_MD.read_text(encoding="utf-8")
    tables = parse_tables(md, _offsets(md))
    T = {t["semantic"]: t for t in tables}
    audit = manifest["number_audit"]
    src = manifest["source"]
    rec = src["platform_record"]
    counts = manifest["counts"]
    fam = audit["families"]
    L: list[str] = []
    w = L.append

    def verbatim(t):
        return [r["text"] for r in t["rows"]] if t else []

    digests = {}
    for p in (SOURCE_MD, MANIFEST, LOCAL_SCHEMA, ENVELOPE, LOCATOR, REPORT_BODY, COVERAGE):
        if p.exists():
            digests[p.name] = _sha256_bytes(p.read_bytes())
    max_err = max((f["max_error"] for f in fam.values()), default=0.0)
    worst = max(audit["checks"], key=lambda c: (c["error"] / c["tolerance"]) if c["tolerance"] else 0.0)

    w("# KF 工序 01 · wp-9645-01 资产登记 —— report 9645（IN101-N09 ISO 19906 冰压分项系数目标可靠度反标定）")
    w("")
    w("**工作包** `%s` ｜ **task_type** `%s` ｜ **report_id** `%s` ｜ **源 mission** %s ｜ **生产者** `%s`"
      % (PACKAGE_ID, TASK_TYPE, REPORT_ID, rec.get("mission_id"), PRODUCER))
    w("")
    w("**源** `%s`（`sha256:%s`，%d 字符 / %d 行 / %d UTF-8 字节） ｜ **产物落点** `%s`"
      % (SOURCE_URI, src["hash"], src["chars"], src["lines"], src["bytes_utf8"], _rel(OUT_DIR)))
    w("")
    w("| 机器自检 | 结果 |")
    w("|---|---|")
    w("| 源哈希 vs 契约（`%s…`）| %s |"
      % (src["contract_hash"][7:23], "PASS" if src["hash_matches_contract"] else "FAIL"))
    w("| 源字符数 vs 契约（%d）| %s |"
      % (src["contract_chars"], "PASS" if src["chars_matches_contract"] else "FAIL"))
    w("| 标题前缀 / scenario_key vs 契约 | %s / %s |"
      % ("PASS" if src["title_matches_contract"] else "FAIL",
         "PASS" if src["scenario_matches_contract"] else "FAIL"))
    w("| 定位器逐字切片（%d 资产 / %d 表 / %d 节）| %d/%d · %d/%d · %d/%d |"
      % (ledger["counts"]["assets"], ledger["counts"]["tables"], ledger["counts"]["sections"],
         ledger["counts"]["assets_ok"], ledger["counts"]["assets"],
         ledger["counts"]["tables_ok"], ledger["counts"]["tables"],
         ledger["counts"]["sections_ok"], ledger["counts"]["sections"]))
    w("| 注册值算术自审 | %d/%d PASS（未审 %d 项，逐项写明原因）|"
      % (audit["summary"]["passed"], audit["summary"]["checks"], audit["summary"]["not_audited"]))
    w("| claims（01 工序无抽取职责）| 空数组 + `claims_empty_reason`（见 §3.5）|")
    w("")
    w("---")
    w("")

    # ---------------- section 1
    w("## ① 案例介绍（物理背景 / 参数表）")
    w("")
    w("被登记的源报告是 **%s**（平台 report_id `%s`，`scenario_key` = `%s`，`status` = %s，"
      "%s 由 mission %s 产出；平台 tags：%s）。"
      % (rec.get("title"), REPORT_ID, rec.get("scenario_key"), rec.get("status"),
         rec.get("created_at"), rec.get("mission_id"),
         ", ".join("`%s`" % t for t in (src["platform_tags"] or []))))
    w("")
    w("**物理背景**（源报告 §① 的登记摘要，不改写任何数值）：ISO 19906 用压力–面积关系描述冰载荷，"
      "作用于接触（或整体）面积 A 上的冰压随面积下降，p(A) = p0·(A/A0)^(−ex)；结构承受的冰力是 "
      "F = k_F·p(A)·A。指数为负意味着**产生年极值冰力的冰压与面积负相关**（大面积伴随低压），"
      "于是「冰压年极值分布 → 抗力分布 → 极限状态」构成一个反问题：求设计格式 γ_f·F_k ≤ R_k/ψ "
      "的分项系数对 (γ_f, ψ)，使按该格式定尺的构件恰好达到目标年可靠度 β_T = 4.0。本工作包登记的是"
      "这条链条的**证据层**：源报告本体、6 张结果图、结果 JSON、求解器与复现脚本、以及 ISO 19906 "
      "Annex A 的表格出处。")
    w("")
    w("**表 ①-a 源报告的机器判据（逐行取自 source.md，未手抄）**")
    w("")
    w("| 判据 | 结果 |")
    w("|---|---|")
    for line in verbatim(T.get("machine_criteria")):
        w(line)
    w("")
    w("**表 ①-b 源报告的参数表（逐行取自 source.md，未手抄）**")
    w("")
    w("| 参数 | 取值 | 说明 |")
    w("|---|---|---|")
    for line in verbatim(T.get("param_table")):
        w(line)
    w("")
    w("**表 ①-c 登记对象的载体（平台侧事实，逐字段量测）**")
    w("")
    w("| 字段 | 值 |")
    w("|---|---|")
    w("| report_id | `%s` |" % REPORT_ID)
    w("| title | %s |" % src["title"])
    w("| scenario_key | `%s` |" % src["scenario_key"])
    w("| mission_id | %s |" % rec.get("mission_id"))
    w("| status / stage | %s / %s |" % (rec.get("status"), rec.get("stage")))
    w("| platform figures | %d 条（仅 name+caption，`has_payload` 集合 = %s）|"
      % (len(rec.get("figures") or []),
         sorted({str(f.get("has_payload")) for f in (rec.get("figures") or [])})))
    w("| markdown 载体 | %d 字符 / %d 行 / %d 字节 / `sha256:%s` |"
      % (src["chars"], src["lines"], src["bytes_utf8"], src["hash"]))
    w("| 节 / 表 | %d 节 / %d 张表（全部带定位器）|" % (counts["sections"], counts["tables"]))
    w("")

    # ---------------- section 2
    w("## ② 怎么做的（方法 / 流程 / 关键设置 / 工具链）")
    w("")
    w("01 工序的职责是**登记证据、不生产知识**，因此每一步都围绕「可复核」而不是「可读性」设计：")
    w("")
    w("1. **抓取 + 范围守卫**（`register.py fetch`）。`GET /api/v1/tensor/reports/9645` 取回记录后先校验返回 "
      "`id`，不等即 `SystemExit`；markdown 按原字节写入 `source.md`，成为后续全部工件的唯一源。工作包只碰"
      "这一个 report_id。")
    w("2. **源指纹钉死**（`CONTRACT` 常量）。首次登记时把 `sha256`、字符数、标题前缀、`scenario_key` 写进脚本；"
      "此后任何重跑若与常量不符即中止 —— 源漂移必须由人重新裁定，脚本不自我重钉。")
    w("3. **资产枚举而非「挑资产」**。解析三类位置：markdown 图片/链接目标、行内代码里的路径（含 `复现` 命令中的 "
      "`.py`）、行内代码里的点分模块名；再补一条**按名引用**的规范表格（ISO 19906 Annex A.2/A.3）。"
      "%d 个资产 = %d resolved（源本体）+ %d referenced_unresolved + %d declared_absent。"
      % (counts["assets"], counts["resolved_in_source"], counts["referenced_unresolved"],
         counts["declared_absent"]))
    w("4. **单一定义的定位器**。定位器 = `(start_char, end_char, start_line, end_line, quote)`，满足 "
      "`quote == source[start_char:end_char]` 且 `start_line == line(start_char)`：引文是**切片**而不是"
      "「照抄一遍」，三者自洽即平台子串校验必过。表与节同样带定位器（%d 张表 + %d 节）。"
      % (counts["tables"], counts["sections"]))
    w("5. **可达性判定保守化**。绝对宿主路径（`/root/tp-agent/work/...`）、跨仓路径、跨仓模块一律 "
      "`referenced_unresolved` 并写明原因；平台 `figures` 只有 name+caption、`png_base64` 为空，因此"
      "**不生成任何图片哈希**（不猜、不用 caption 冒充字节）。")
    w("6. **注册值算术自审**（对 01 契约的**附加**自检 `number_audit()`）。源报告里同一个量常在多处出现"
      "（表 1 与表 6/表 7、表 2 与 §⑥、表 3 与 §⑥、表 4 与 §⑥），于是把报告自述的数字互为基准重算："
      "κ = γ_f·ψ、κ* = R_k/F_k、P_f = Φ(−β)、表 4 的分项系数乘积与三项偏差、表 5 的 Δβ 与 P_f 倍数、"
      "表 7 的中心差分导数、表 3 的伴随导数相对误差（含显示舍入预算）等共 %d 项；"
      "**重构不了的量（求解器输出）显式进 `not_audited` 清单**，不假装审过。"
      % audit["summary"]["checks"])
    w("7. **定位器台账二次独立复核**（`locators`）。`locator_check.json` 重新读 `source.md`（不信任构建期状态），"
      "逐条比对切片、行号、行首偏移与唯一性；`mismatches` 必须为空。")
    w("8. **信封 / 本地 schema / 图 / 报告 / 哈希**。`kf_result.json` 严格按 "
      "`schemas/kf_result.v1.schema.json`（`provenance.source_hash` 与平台独立重算的 markdown 字节哈希一致）；"
      "`asset_manifest.schema.json` 由共享 schema **派生**（只重定向 const，共享 schema 一字未改）；"
      "`asset_coverage.png` 由 matplotlib 生成；本报告数字全部从 JSON 注入；`sha256.txt` 覆盖 7 个交付文件。")
    w("")
    w("**工具链**：纯标准库（`urllib` / `hashlib` / `math.erfc`）+ `matplotlib`（仅出图）+ `pytest` 离网不变量自检；"
      "`build` / `verify` 无网络依赖，`fetch` 才需要平台凭据。")
    w("")

    # ---------------- section 3
    w("## ③ 计算结果（登记结果；数字表全部程序化注入）")
    w("")
    w("### 3.1 资产清单与解析状态")
    w("")
    w("| 汇总 | 计数 |")
    w("|---|---|")
    for k in sorted(counts["by_class"]):
        w("| class `%s` | %d |" % (k, counts["by_class"][k]))
    for k in sorted(counts["by_resolution"]):
        w("| resolution `%s` | %d |" % (k, counts["by_resolution"][k]))
    w("| **assets 合计** | **%d** |" % counts["assets"])
    w("| tables / sections / 扫描到的引用 | %d / %d / %d |"
      % (counts["tables"], counts["sections"], counts["references_scanned"]))
    w("")
    w("**表 3.1-b 逐个资产（主表见 `asset_manifest.json`）**")
    w("")
    w("| id | class | 行 | resolution | 引用目标 |")
    w("|---|---|---|---|---|")
    for a in manifest["assets"]:
        target = (a.get("reference") or {}).get("path_reference") or a["label"]
        w("| `%s` | `%s` | %d | `%s` | `%s` |"
          % (a["asset_id"], a["asset_class"], a["locator"]["start_line"], a["resolution"],
             str(target)[:78]))
    w("")
    w("### 3.2 定位器台账（`locator_check.json`）")
    w("")
    w("定义：`quote == source[start_char:end_char]` 且 `start_line == line(start_char)`；二次独立复核结果：")
    w("")
    w("| 对象 | 通过 / 总数 |")
    w("|---|---|")
    w("| 资产定位器（切片 + 行号 + 行首偏移）| %d / %d |"
      % (ledger["counts"]["assets_ok"], ledger["counts"]["assets"]))
    w("| 表定位器（切片 + 表头在场）| %d / %d |"
      % (ledger["counts"]["tables_ok"], ledger["counts"]["tables"]))
    w("| 节定位器（标题落在声明的字符区间）| %d / %d |"
      % (ledger["counts"]["sections_ok"], ledger["counts"]["sections"]))
    w("| 资产引文在源中唯一出现 | %d / %d |"
      % (ledger["counts"]["asset_quotes_unique"], ledger["counts"]["assets"]))
    w("| `mismatches` | %d |" % len(ledger["mismatches"]))
    w("")
    w("### 3.3 注册值算术自审（`asset_manifest.json` → `number_audit`）")
    w("")
    w("| 家族 | 检查项 | 通过 | 最大误差 | 误差类别 |")
    w("|---|---|---|---|---|")
    for f in sorted(fam):
        kinds = sorted({c["error_kind"] for c in audit["checks"] if c["family"] == f})
        w("| `%s` | %d | %d | %.2e | %s |"
          % (f, fam[f]["checks"], fam[f]["passed"], fam[f]["max_error"], "/".join(kinds)))
    w("| **合计** | **%d** | **%d** | %.2e | — |"
      % (audit["summary"]["checks"], audit["summary"]["passed"], max_err))
    w("")
    w("**表 3.3-b 未审（`not_audited`）清单 —— 全部是求解器输出或分辨率不足，逐项写明原因**")
    w("")
    w("| id | 原因 |")
    w("|---|---|")
    for na in audit["not_audited"]:
        w("| `%s` | %s |" % (na["id"], na["reason"]))
    w("")
    w("### 3.4 源 → 契约对上")
    w("")
    w("| 量 | 契约（首次登记时钉死）| 本次量测 | 一致 |")
    w("|---|---|---|---|")
    w("| `sha256(markdown 字节)` | `%s` | `sha256:%s` | %s |"
      % (src["contract_hash"][7:], src["hash"], src["hash_matches_contract"]))
    w("| chars | %d | %d | %s |"
      % (src["contract_chars"], src["chars"], src["chars_matches_contract"]))
    w("| title 前缀 | `%s…` | `%s…` | %s |"
      % (CONTRACT["title_prefix"][:40], src["title"][:40], src["title_matches_contract"]))
    w("| scenario_key | `%s` | `%s` | %s |"
      % (CONTRACT["scenario_key"], src["scenario_key"], src["scenario_matches_contract"]))
    w("")
    w("### 3.5 claims 为空的原因")
    w("")
    w("`claims` = `[]`；`claims_empty_reason` = 「%s」。01 工序无抽取职责：造 claim 反而违反 "
      "`no_forced_claim_generation`；`verified` 标记一律不写 —— 验证属于平台门。" % manifest["claims_empty_reason"])
    w("")
    w("### 3.6 交付文件指纹（`sha256.txt` 同源）")
    w("")
    w("| 文件 | bytes | sha256 |")
    w("|---|---|---|")
    for name in sorted(digests):
        w("| `%s` | %d | `%s` |" % (name, (OUT_DIR / name).stat().st_size, digests[name]))
    w("")
    w("`sha256.txt` 覆盖除自身外的全部 7 个交付文件；本报告的自身指纹只能记录在其中（报告不能自引用）。")
    w("")

    w("### 3.7 源报告核心结果表（逐行取自 source.md，本包不重算）")
    w("")
    w("为让下游工序不必先解析整篇源文即可核对「登记了哪几张数字表」，把 §③ 的四张核心表原样注入"
      "（每张表的定位器在 `asset_manifest.json → tables[]`，可回切到 `source.md` 对应行）：")
    w("")
    for sem, title in (("t1_inverse", "表 3.7-a 反问题解（源报告 表 1）"),
                       ("t2_form_verify", "表 3.7-b FORM 的四条独立验证（源报告 表 2）"),
                       ("t6_negative_control", "表 3.7-c 负控：忽略 p–A 负相关（源报告 表 6）"),
                       ("t7_beta_t_sensitivity", "表 3.7-d 目标可靠度敏感性（源报告 表 7）")):
        t = T.get(sem)
        if not t:
            w("（源中未找到 %s）" % sem)
            w("")
            continue
        w("**%s** —— 源行 %d–%d，%d 行数据" % (title, t["start_line"], t["end_line"], t["n_rows"]))
        w("")
        w(t["header"])
        w("|---|" + "---|" * (len(split_cells(t["header"])) - 1))
        for line in verbatim(t):
            w(line)
        w("")
    w("注：源报告 表 1 的 `$|\\beta-\\beta_T|$` 一行含绝对值竖线，在 markdown 表格里会被当成列分隔符"
      "（源报告本身即如此）。本包按原文**逐字注入、不做任何改动** —— 纯文本视图与 `source.md` 完全等价，"
      "渲染差异属于源报告的排版问题，登记层不予修饰。")
    w("")

    # ---------------- section 4
    w("## ④ 结果图")
    w("")
    w("**图 1.** `asset_coverage.png` —— 三联图，全部由 `asset_manifest.json` + `locator_check.json` 直接绘制："
      "(A) 源文档行剖面 + 每个资产定位器在源中的位置（实心点 = resolved，空心点 = 已登记但未解析）、"
      "表跨度阴影与节边界，一眼可判证据分布在哪几节；(B) 资产 class × resolution 堆叠条；"
      "(C) 注册值算术自审各家族的通过数与最大误差（绿 = PASS）。")
    w("")
    w("![asset coverage](asset_coverage.png)")
    w("")
    w("**关于源报告的 6 张结果图**：源报告 §④ 以绝对宿主路径引用 `fig1_pa_joint.png` … `fig6_sensitivity.png`"
      "（`/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/`）。该路径在本工作树内不存在，平台记录的 "
      "`figures` 只有 name+caption、`png_base64` 为空 —— 因此这 6 张图一律登记为 `referenced_unresolved`，"
      "**不复制、不重绘、不伪造哈希**。它们承载的物理场量（联合 p–A 状态、β(κ) 曲线、Newton 残差收敛、"
      "ISO 偏差图、负控、敏感性）在本报告中只能以文字与数字转述：这是 01 工序的边界而非遗漏，图字节的取得"
      "属于源 mission 的交付责任。")
    w("")

    w("**表 ④-a 源报告 6 张结果图的登记状态（caption 取自平台记录，字节未取得）**")
    w("")
    w("| asset | 文件 | resolution | has_payload | caption（平台记录原文，截断）|")
    w("|---|---|---|---|---|")
    for a in manifest["assets"]:
        ref = a.get("reference") or {}
        if a["asset_class"] != "figure_reference":
            continue
        cap = (ref.get("platform_caption") or "").replace("|", "\\|")
        w("| `%s` | `%s` | `%s` | %s | %s |"
          % (a["asset_id"], ref.get("platform_figure_name"), a["resolution"],
             next((str(f.get("has_payload")) for f in (rec.get("figures") or [])
                   if f.get("name") == ref.get("platform_figure_name")), "n/a"),
             cap[:96]))
    w("")

    # ---------------- section 5
    w("## ⑤ 注意点（坑 / 局限 / 适用范围）")
    w("")
    w("1. **绝对宿主路径是 01 工序最常见的坑**。源报告的 6 图 + 结果 JSON 都是 `/root/tp-agent/work/m8350/...`，"
      "换一个 worktree 就根本不存在。把它们「按名登记为 resolved」最省事也最危险 —— 本次全部落 "
      "`referenced_unresolved`，并在 `note` 里写明「平台亦无字节」。")
    w("2. **平台 `figures` 的 name+caption 不等于图片字节**。记录里 6 条 figure 元数据齐全，`png_base64` 却为空；"
      "本包只用 caption 做交叉引用（`platform_figure_name` / `platform_caption`），绝不据此生成哈希。")
    w("3. **表 5 的「按表所需 R_k / 标定所需 R_k」列不可审**。该列来自 `run_study()` 的结果 JSON（本身 "
      "unresolved），重算需要 FORM / 设计点求解；本包把它列入 `not_audited` 并写明原因，而不是用 Δκ 硬凑近似。")
    w("4. **ISO 19906 Annex A 只能记 `declared_absent`**。源报告 §⑤ 自述 A.2/A.3 为二次文献转录、"
      "`primary_source_verified=False`，由此得出的表格裁决一律 `conditional`；本包据报告自述登记缺席，"
      "不把任何表格分项系数抄进 manifest 冒充「已核」。")
    w("5. **哈希钉死是「失败即停」而非「自动追平」**。源一旦漂移 `build` 就中止 —— 这是刻意的：下游知识对象"
      "以 `provenance.source_hash` 为准，静默重钉会让引用方无从察觉。")
    w("6. **算术自审不是物理审核**。它只证明「报告自述的数字彼此自洽」，不证明 β=4.0 的标定正确。该问题的 "
      "FORM 在数学上是精确的（失效域在半空间，见源 §⑤-2），所以「FORM vs MC 差 3 %」在此只能检验实现一致性 ——"
      "该解读来自源报告，本包不重复推导，只登记。")
    w("7. **适用范围**：年极值接触面积对数正态、冰压单一幂律指数、抗力与冰力独立（源 §⑤-6）。任何把本包资产"
      "用于不同建模假设的下游工序，都必须重走源 mission 的收敛与判据流程。")
    w("")

    # ---------------- section 6
    w("## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3 %）")
    w("")
    w("基准的选取遵循 01 工序的性质：**登记层的基准是「字节与切片」而不是物理量**，因此绝大多数项误差恒为 0；"
      "唯一有非零误差的是注册值算术自审（显示舍入 + 少量口径），逐项列出：")
    w("")
    w("| 关键量 | 基准 | 误差 | <3 % ? |")
    w("|---|---|---|---|")
    w("| 源 markdown 字节哈希 | 契约 `%s…` | 0（等值比较）| 是（精确相等）|" % src["contract_hash"][7:23])
    w("| 源字符数 | 契约 %d | 0 | 是（精确相等）|" % src["contract_chars"])
    w("| 资产定位器切片 | `source[start:end]` | 0 处不等 / %d 项 | 是（精确相等）|"
      % ledger["counts"]["assets"])
    w("| 表 / 节定位器 | 表头在场 + 标题落在声明区间 | 0 处不等 / %d 项 | 是（精确相等）|"
      % (ledger["counts"]["tables"] + ledger["counts"]["sections"]))
    w("| 注册值自审最紧的一项 `%s` | 声明 %s vs 重算 %s | %.3e（容差 %s，用掉容差 %.1f%%）| 是 |"
      % (worst["check_id"], worst["declared"], worst["recomputed"], worst["error"],
         worst["tolerance"],
         100.0 * worst["error"] / worst["tolerance"] if worst["tolerance"] else 0.0))
    w("| 注册值自审整体 | 逐家族容差（见 §3.3）| 最大 %.2e（绝对百分点制，0.0047 pp）| 是 |" % max_err)
    w("| 源报告本体的物理精度（FORM vs 解析/IS/MC、伴随 vs 差分）| 见源报告 §⑥ | **本包不复算** | 不适用（见下）|")
    w("")
    w("**显式回答**：登记层全部关键量 **误差为 0（精确相等）**，满足 <3 %% ；注册值算术自审 %d/%d 项 PASS，"
      "最大误差 %.2e，全部落在为「显示舍入」设定的容差内，同样满足 <3 %% 。"
      % (audit["summary"]["passed"], audit["summary"]["checks"], max_err))
    w("")
    w("**为什么源报告本体的物理误差不复算**：01 工序不做抽取也不做复核，其基准是字节；重跑 FORM/IS/MC 需要 "
      "`tensorphysics.structural` 与结果 JSON（本包已登记 unresolved），在本仓重现等于在无源的情况下自造证据。"
      "源报告 §⑥ 自述：FORM vs 闭式解析 6.46e-09、vs 设计点重要性抽样 6.37e-04、粗 MC 5.93e-03，唯一超 3 % 量级"
      "的是粗 MC 统计噪声。这些数字本包只做**跨节一致性核对**（F8/F12 家族，全部 PASS），不声称独立验证其"
      "物理正确性。")
    w("")
    w("## 审计链")
    w("")
    w("- 源：`%s`（`sha256:%s`，缓存 `%s`）" % (SOURCE_URI, src["hash"], _rel(SOURCE_MD)))
    w("- 登记清单：`%s`（assets %d / tables %d / sections %d）"
      % (_rel(MANIFEST), counts["assets"], counts["tables"], counts["sections"]))
    w("- 定位器台账：`%s`（`all_ok` = %s）" % (_rel(LOCATOR), ledger["all_ok"]))
    w("- 结果信封：`%s`（kf_result.v1，`provenance.source_hash` = `sha256:%s`）"
      % (_rel(ENVELOPE), src["hash"]))
    w("- 本地 schema：`%s`（由共享 `schemas/asset_manifest.v1.schema.json` 派生，共享文件未改）"
      % _rel(LOCAL_SCHEMA))
    w("- 覆盖图：`%s` ｜ 指纹：`%s`" % (_rel(COVERAGE), _rel(SHA_TXT)))
    w("- 一键复跑：`python3 scripts/kf/wp_9645_01_register.py all`（`fetch` 需平台凭据，`build`/`verify` 离网可跑）")
    w("- 离网不变量自检：`pytest tests/test_kf_wp9645_01.py -q`")
    w("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------- sha / verify
DELIVERABLES = (SOURCE_MD, MANIFEST, LOCAL_SCHEMA, ENVELOPE, LOCATOR, REPORT_BODY, COVERAGE)


def write_sha() -> Path:
    rows = []
    for p in DELIVERABLES:
        if not p.exists():
            raise SystemExit("cannot hash missing deliverable %s" % _rel(p))
        rows.append("%s  %s" % (hashlib.sha256(p.read_bytes()).hexdigest(), _rel(p)))
    SHA_TXT.write_text("\n".join(sorted(rows)) + "\n", encoding="utf-8")
    print("sha256.txt ->", _rel(SHA_TXT), "|", len(rows), "files")
    return SHA_TXT


def _has_verified_mark(obj) -> bool:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "verified" or _has_verified_mark(v):
                return True
    elif isinstance(obj, list):
        return any(_has_verified_mark(v) for v in obj)
    elif isinstance(obj, str) and obj.strip().lower() == "verified":
        return True
    return False


def _sha_matches() -> bool:
    if not SHA_TXT.exists():
        return False
    rows = {}
    for line in SHA_TXT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, path = line.split("  ", 1)
        rows[path] = digest
    if set(rows) != {_rel(p) for p in DELIVERABLES}:
        return False
    return all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == d for p, d in rows.items())


def _report_matches(manifest: dict, ledger: dict) -> bool:
    """The report body must carry the numbers it claims to inject (no hand-typed drift)."""
    if not REPORT_BODY.exists():
        return False
    body = REPORT_BODY.read_text(encoding="utf-8")
    needles = [
        manifest["source"]["hash"],
        str(manifest["counts"]["assets"]),
        str(manifest["number_audit"]["summary"]["checks"]),
        str(manifest["number_audit"]["summary"]["passed"]),
        "%d/%d" % (ledger["counts"]["assets_ok"], ledger["counts"]["assets"]),
        manifest["assets"][-1]["asset_id"],
    ]
    return all(n in body for n in needles)


def verify() -> dict:
    """Re-derive every committed artifact from source.md; no network, no build state trusted."""
    md = SOURCE_MD.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ledger = json.loads(LOCATOR.read_text(encoding="utf-8"))
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    schema = json.loads(LOCAL_SCHEMA.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}

    checks["source_hash_matches_contract"] = (
        _sha256_bytes(md.encode("utf-8")) == CONTRACT["source_hash"])
    checks["source_chars_matches_contract"] = len(md) == CONTRACT["chars"]
    checks["manifest_reproducible_offline"] = (
        build_manifest(md, manifest["source"]["platform_record"]) == manifest)
    checks["locator_ledger_reproducible"] = locator_check(md, manifest) == ledger
    checks["locator_ledger_all_ok"] = ledger["all_ok"]
    checks["number_audit_all_passed"] = manifest["number_audit"]["summary"]["all_passed"]
    checks["envelope_embeds_manifest"] = envelope["outputs"]["asset_manifest.json"] == manifest
    checks["envelope_provenance_hash"] = ("sha256:" + manifest["source"]["hash"]
                                          == envelope["provenance"]["source_hash"])
    checks["claims_empty_with_reason"] = (manifest["claims"] == []
                                          and bool(manifest["claims_empty_reason"]))
    checks["no_verified_marks"] = not _has_verified_mark(manifest)
    checks["asset_ids_unique"] = (len({a["asset_id"] for a in manifest["assets"]})
                                  == len(manifest["assets"]))
    checks["unresolved_carry_reason"] = all(
        bool(a.get("note")) for a in manifest["assets"]
        if a["resolution"] != "resolved_in_source")
    checks["sha256_txt_matches_files"] = _sha_matches()
    checks["report_body_matches_json"] = _report_matches(manifest, ledger)

    try:
        import jsonschema
    except ImportError:
        jsonschema = None
        print("note: jsonschema unavailable -- schema validation skipped, not counted as pass/fail")
    if jsonschema is not None:
        try:
            jsonschema.validate(manifest, schema)
            checks["manifest_valid_against_local_schema"] = True
        except Exception as exc:  # noqa: BLE001
            print("schema validation failed:", exc)
            checks["manifest_valid_against_local_schema"] = False
        try:
            jsonschema.validate(envelope, json.loads(KF_SCHEMA.read_text(encoding="utf-8")))
            checks["envelope_valid_against_kf_result_v1"] = True
        except Exception as exc:  # noqa: BLE001
            print("envelope validation failed:", exc)
            checks["envelope_valid_against_kf_result_v1"] = False

    ok = all(checks.values())
    print("verify:", "OK" if ok else "FAILED")
    for k, v in checks.items():
        print("  %-40s %s" % (k, "PASS" if v else "FAIL"))
    if not ok:
        raise SystemExit(1)
    return {"ok": ok, "checks": checks}


# --------------------------------------------------------------------- CLI
def _load(name: Path) -> dict:
    return json.loads(name.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if cmd in ("fetch", "all"):
        rec = fetch_record()
        print("fetched report %s ->" % REPORT_ID, _rel(SOURCE_MD),
              "| chars", len(rec.get("markdown") or ""))
    if cmd in ("build", "all"):
        md = SOURCE_MD.read_text(encoding="utf-8")
        actual = _sha256_bytes(md.encode("utf-8"))
        if actual != CONTRACT["source_hash"]:
            raise SystemExit("SOURCE HASH MISMATCH vs pinned contract: %s != %s"
                             % (actual, CONTRACT["source_hash"]))
        if cmd == "all":
            rec = platform_record_meta(fetch_record())
        elif MANIFEST.exists():
            rec = _load(MANIFEST)["source"]["platform_record"]
        else:
            raise SystemExit("build: no manifest yet -> run `fetch` and `build` once online first")
        manifest = build_manifest(md, rec)
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print("manifest ->", _rel(MANIFEST), "| assets", manifest["counts"]["assets"],
              "| audit", manifest["number_audit"]["summary"])
    if cmd in ("schema", "all"):
        LOCAL_SCHEMA.write_text(json.dumps(build_local_schema(), ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
        print("schema ->", _rel(LOCAL_SCHEMA))
    if cmd in ("locators", "all"):
        md = SOURCE_MD.read_text(encoding="utf-8")
        ledger = locator_check(md, _load(MANIFEST))
        LOCATOR.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("locator_check ->", _rel(LOCATOR), "|", ledger["counts"], "| all_ok", ledger["all_ok"])
    if cmd in ("envelope", "all"):
        md = SOURCE_MD.read_text(encoding="utf-8")
        ENVELOPE.write_text(json.dumps(build_envelope(md, _load(MANIFEST)), ensure_ascii=False,
                                       indent=2) + "\n", encoding="utf-8")
        print("envelope ->", _rel(ENVELOPE))
    if cmd in ("figure", "all"):
        figure(_load(MANIFEST), _load(LOCATOR))
    if cmd in ("report", "all"):
        REPORT_BODY.write_text(render_report(_load(MANIFEST), _load(LOCATOR)), encoding="utf-8")
        print("report_body ->", _rel(REPORT_BODY))
    if cmd in ("sha", "all"):
        write_sha()
    if cmd in ("verify",) or cmd == "all":
        verify()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
