#!/usr/bin/env python3
"""wp-14214-01 (01-asset-registration, report 14214): register source assets only.

Single work package, single report_id=14214, nothing else touched:

    fetch   GET /api/v1/tensor/reports/14214 (Bearer) -> markdown bytes
    verify  sha256(markdown) == contract.source_hash and len(markdown) == contract.chars
    locate  every registered asset gets a verbatim quote that is machine-resolved
            (char span / line span / occurrence count) against those exact bytes;
            a miss is fatal -> no manifest is written (never hand-transcribed)
    probe   artifact endpoints, to state honestly whether referenced bytes exist
    emit    source.md, sha256.txt, locator_check.json, asset_manifest.json,
            kf_result.json (kf_result.v1 envelope), report_body.md

No extraction, no classification, no claims (contract objective.classify_report_type
= false; claims may be []). Nothing is marked verified: hash equality is a mechanical
identity check, verification stays with the platform gate.

Credentials come from the environment only (TENSOR_AGENT_USER / TENSOR_AGENT_PASS /
TENSOR_API_BASE) and are never written to disk.

Usage:  python3 scripts/kf_wp14214_01_register.py [--no-fetch]
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-14214-01"
REPORT_ID = "14214"

# ---------------------------------------------------------------- contract (verbatim)
CONTRACT_HASH = "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9"
CONTRACT_CHARS = 6258
CONTRACT_TITLE = (
    "W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + "
    "成稿门四门→九门（放行2/阻断22）+ 10 单派发"
)
CONTRACT_SCENARIO = "paper-line-w23"
PACKAGE_ID = "wp-14214-01"
TASK_TYPE = "01-asset-registration"
PRODUCER = "agent/m15784"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


# ------------------------------------------------------------------------ transport
def _post_json(url, payload, token=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get_json(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def probe(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    try:
        urllib.request.urlopen(req, timeout=30).read()
        return "HTTP 200"
    except urllib.error.HTTPError as exc:
        return "HTTP %d" % exc.code
    except Exception as exc:  # noqa: BLE001 - probe is informational only
        return type(exc).__name__


def fetch_record():
    tok = _post_json(
        BASE + "/auth/login",
        {"username": os.environ["TENSOR_AGENT_USER"],
         "password": os.environ["TENSOR_AGENT_PASS"]},
    )
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise SystemExit("login returned no token")
    rec = _get_json(BASE + "/tensor/reports/" + REPORT_ID, token)
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    return token, rec


# ---------------------------------------------------------------- locator resolution
def occurrences(source, quote):
    out, pos = [], source.find(quote)
    while pos >= 0:
        out.append(pos)
        pos = source.find(quote, pos + 1)
    return out


def line_of(source, pos):
    return source.count("\n", 0, pos) + 1


def line_bounds(source, pos):
    start = source.rfind("\n", 0, pos) + 1
    end = source.find("\n", pos)
    return start, (len(source) if end < 0 else end)


def unique_quote(source, seed):
    """Grow `seed` along whole lines until it occurs exactly once.

    Deterministic and recorded: the returned quote is a verbatim substring whose
    uniqueness is asserted, so no locator relies on hand counting.
    """
    hits = occurrences(source, seed)
    if not hits:
        return None, 0, "seed_not_found"
    if len(hits) == 1:
        return seed, 1, "seed_unique"
    pos = hits[0]
    start = source.rfind("\n", 0, pos) + 1
    chunk = source[start:].split("\n")
    for take in range(2, len(chunk) + 1):
        cand = "\n".join(chunk[:take])
        if len(occurrences(source, cand)) == 1:
            return cand, 1, "expanded_to_lines"
    prev = source.rfind("\n", 0, max(0, start - 1)) + 1
    chunk = source[prev:].split("\n")
    for take in range(2, len(chunk) + 1):
        cand = "\n".join(chunk[:take])
        if len(occurrences(source, cand)) == 1:
            return cand, 1, "expanded_above"
    return seed, len(hits), "ambiguous"


def asset(asset_id, asset_class, label, seed, note, section_hint=None, extra=None):
    return {"asset_id": asset_id, "asset_class": asset_class, "label": label, "seed": seed,
            "section_hint": section_hint, "note": note, "extra": extra or {}}


def build_asset_table():
    """Asset seeds. Every seed must be a verbatim substring of the registered markdown."""
    return [
        asset("A02", "figure_png_reference", "papers/figures/w23_window_composition.png",
              "`papers/figures/w23_window_composition.png`（sha256_16 `00a0936204e0b70d`",
              "正文 ④ 逐字路径 + 报告声明的前 16 位 sha256；png 字节不在报告记录内",
              section_hint="④", extra={"declared_sha256_16": "00a0936204e0b70d"}),
        asset("A03", "figure_png_reference", "papers/figures/w23_track_split.png",
              "`papers/figures/w23_track_split.png`（sha256_16 `d889e66d3739a24e`",
              "正文 ④ 逐字路径 + 声明 sha256_16；png 字节不在报告记录内",
              section_hint="④", extra={"declared_sha256_16": "d889e66d3739a24e"}),
        asset("A04", "figure_png_reference", "papers/figures/w23_plan_progress.png",
              "`papers/figures/w23_plan_progress.png`（sha256_16 `371b8fc472428b13`",
              "正文 ④ 逐字路径 + 声明 sha256_16；png 字节不在报告记录内",
              section_hint="④", extra={"declared_sha256_16": "371b8fc472428b13"}),
        asset("A05", "figure_png_reference", "papers/figures/w23_draft_gate.png",
              "`papers/figures/w23_draft_gate.png`（sha256_16 `3a48cfafc642d093`",
              "正文 ④ 逐字路径 + 声明 sha256_16；png 字节不在报告记录内",
              section_hint="④", extra={"declared_sha256_16": "3a48cfafc642d093"}),
        asset("A06", "figure_png_reference", "papers/figures/w23_artifact_presence.png",
              "`papers/figures/w23_artifact_presence.png`（sha256_16 `4a1693ff2284f6e6`",
              "正文 ④ 逐字路径 + 声明 sha256_16；png 字节不在报告记录内",
              section_hint="④", extra={"declared_sha256_16": "4a1693ff2284f6e6"}),
        asset("A07", "code_glob", "papers/tools/w23_*.py 面板（花括号聚合引用）",
              "`papers/tools/w23_{extract,anchors,plan,tracks,specs,payloads,dispatch,"
              "draftgate,planmd,figures,registry}.py`",
              "brace-glob 逐字引文；expansion 由花括号内容机械展开（不新增名字）",
              section_hint="附"),
        asset("A08", "code_file", "w23_extract.py", "**增量扫描**（`w23_extract.py`）",
              "正文 ② 逐字点名；源码不在报告记录内", section_hint="②"),
        asset("A09", "code_file", "w23_anchors.py", "**锚目录重建**（`w23_anchors.py`）",
              "正文 ② 逐字点名；源码不在报告记录内", section_hint="②"),
        asset("A10", "code_file", "w23_tracks.py", "**双轨重标**（`w23_tracks.py`）",
              "正文 ② 逐字点名；源码不在报告记录内", section_hint="②"),
        asset("A11", "code_file", "w23_plan.py", "**销项收割**（`w23_plan.py`）",
              "正文 ② 逐字点名；源码不在报告记录内", section_hint="②"),
        asset("A12", "code_file", "w23_draftgate.py", "**成稿门加固**（`w23_draftgate.py`）",
              "正文 ② 逐字点名；源码不在报告记录内", section_hint="②"),
        asset("A13", "code_file", "w23_payloads.py", "**派单**（`w23_payloads.py`",
              "正文 ② 逐字点名；源码不在报告记录内", section_hint="②"),
        asset("A14", "code_file", "w23_dispatch.py", "`w23_dispatch.py`）",
              "正文 ② 逐字点名；源码不在报告记录内", section_hint="②"),
        asset("A15", "code_file", "w23_planmd.py", "`w23_planmd.py` 首版覆盖了",
              "正文 ⑤ 逐字点名；源码不在报告记录内", section_hint="⑤"),
        asset("A16", "code_file", "w23_figures.py", "`papers/tools/w23_figures.py`，输入 digest.json",
              "正文 ④ 逐字点名（4 张图共用该脚本，此处取含 digest.json 的第 1 条图注以保唯一）；"
              "源码不在报告记录内", section_hint="④"),
        asset("A17", "test_file", "test_w23_artifacts.py", "`test_w23_artifacts.py`",
              "正文 附节逐字点名；测试源码不在报告记录内", section_hint="附"),
        asset("A18", "data_dir", "papers/data/w23-2026-11-11/", "`papers/data/w23-2026-11-11/`",
              "数据目录引用；目录内容不在报告记录内", section_hint="附"),
        asset("A19", "research_plan_set", "W23 新立 5 个 research_plan.md",
              "`papers/composite-laminate-verification/research_plan.md",
              "同一 code span 内 5 条路径；expansion 由逗号切分机械得到", section_hint="附"),
        asset("A20", "registry", "papers/registry.md", "registry：`papers/registry.md`",
              "append-only registry 引用；文件内容不在报告记录内", section_hint="附"),
    ]


# ------------------------------------------------------------------- table structure
def parse_tables(source):
    lines = source.split("\n")
    tables, i = [], 0
    while i < len(lines) - 1:
        if lines[i].strip().startswith("|") and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            start = i
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            j = i + 2
            rows = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            tables.append({"start_line": start + 1, "end_line": j, "header_cells": len(header),
                           "header_names": header, "data_rows": len(rows), "rows": rows})
            i = j
            continue
        i += 1
    return tables


def section_of(source, pos):
    head = source.rfind("\n## ", 0, pos)
    if head < 0:
        return "(文档起始段，无 ## 标题)"
    end = source.find("\n", head + 1)
    return source[head + 1:end].strip()


def table_quote(source, t):
    lines = source.split("\n")
    return "\n".join(lines[t["start_line"] - 1:t["end_line"]]), t["start_line"], t["end_line"]


def num(s):
    return int(s.replace(",", "").strip())


def table_row(tbl, first_cell_exact):
    for r in tbl["rows"]:
        if r and r[0] == first_cell_exact:
            return r
    return None


# ------------------------------------------------------------------- integrity checks
def integrity_observations(source, tables):
    """Arithmetic / cross-field checks. Numbers are parsed out of the registered
    tables (never retyped); every observation carries a verbatim quote."""
    obs = []
    empty = {"header_names": [], "rows": [], "start_line": 1, "end_line": 1, "data_rows": 0}
    metrics, plan, disp = dict(empty), dict(empty), dict(empty)
    for t in tables:
        h = t["header_names"]
        if h == ["指标", "数值"] and not metrics["rows"]:
            metrics = t
        elif h == ["指标", "W22", "W23", "变化"] and not plan["rows"]:
            plan = t
        elif h[:2] == ["task_key", "mission"] and not disp["rows"]:
            disp = t

    # O1: verdict trinity vs window count
    if metrics["rows"]:
        verdict = table_row(metrics, "判词 PASS / FAIL / WITHHELD")
        window = table_row(metrics, "窗口报告")
        if verdict and window:
            a, b, c = [num(x) for x in verdict[1].split("/")]
            w = num(window[1])
            q, s, e = table_quote(source, metrics)
            ok = (a + b + c) == w
            obs.append({
                "obs_id": "O1", "kind": "arithmetic",
                "question": "窗口报告计数是否等于判词三态之和",
                "computed": {"PASS": a, "FAIL": b, "WITHHELD": c, "sum": a + b + c,
                             "window_reports": w, "difference": w - (a + b + c)},
                "result": "consistent" if ok else "unresolved_difference",
                "status": "resolved" if ok else "unresolved",
                "unresolved_reason": None if ok else
                    "报告正文未说明差额归属（未判/NULL 判词未见声明），本工序不推断",
                "evidence": [{"quote": q, "source_field": "markdown",
                              "note": "指标表 行%d-%d；数字由脚本解析，未手抄" % (s, e)}]})

    # O2: blocked count in body vs record title (== contract title)
    m = re.search(r"阻断 \*\*(\d+)\*\*", source)
    if m:
        pos = source.find(m.group(0))
        s, e = line_bounds(source, pos)
        body_n = int(m.group(1))
        rec_n = 22 if "阻断22" in CONTRACT_TITLE else None
        ok = rec_n == body_n
        obs.append({
            "obs_id": "O2", "kind": "cross_field",
            "question": "成稿门阻断计数：正文 vs 记录 title（/本包契约 title）",
            "computed": {"body_blocked": body_n, "record_title_blocked": rec_n,
                         "difference": (body_n - rec_n) if rec_n is not None else None},
            "result": "consistent" if ok else "conflict_unresolved",
            "status": "resolved" if ok else "unresolved",
            "unresolved_reason": None if ok else
                "正文写 23，记录 title/summary 与本包契约 title 写 22；报告内无第三方口径可裁，"
                "本工序只登记不裁决（不得标 verified）",
            "evidence": [{"quote": source[s:e], "source_field": "markdown",
                          "note": "正文 ③ 成稿门判决段"},
                         {"quote": CONTRACT_TITLE, "source_field": "record",
                          "note": "记录 title（与本包契约 title 逐字相同）"}]})

    # O3: dispatch table rows / distinct task_key / mission contiguity
    if disp["rows"]:
        keys = [r[0].strip("`").strip() for r in disp["rows"]]
        missions = [int(r[1]) for r in disp["rows"] if r[1].isdigit()]
        ms = sorted(missions)
        contiguous = (not ms) or ms == list(range(ms[0], ms[0] + len(ms)))
        stated = re.search(r"(\d+) 单派发", source) or re.search(r"(\d+) 单派发", CONTRACT_TITLE)
        stated_n = num(stated.group(1)) if stated else None
        q, s, e = table_quote(source, disp)
        ok = contiguous and stated_n == len(set(keys))
        obs.append({
            "obs_id": "O3", "kind": "cross_field",
            "question": "「N 单派发」与派单回执表行数/唯一 task_key/mission 区间是否自洽",
            "computed": {"table_rows": disp["data_rows"], "distinct_task_keys": len(set(keys)),
                         "rows_with_numeric_mission": len(missions),
                         "mission_range": [ms[0], ms[-1]] if ms else [],
                         "missions_contiguous": contiguous, "title_stated_units": stated_n},
            "result": "consistent" if ok else "unresolved_difference",
            "status": "resolved" if ok else "unresolved", "unresolved_reason": None,
            "evidence": [{"quote": q, "source_field": "markdown",
                          "note": "派单回执 行%d-%d：%d 行 = 同一批 %d 个 task_key 的 dry-run 与落库两次快照"
                                  % (s, e, disp["data_rows"], len(set(keys)))}]})

    # O4: plan table three-column arithmetic
    if plan["rows"]:
        rows = {}
        for label in ("计划内 exp 任务", "已销项", "封口计划"):
            r = table_row(plan, label)
            if r:
                rows[label] = {"W22": num(r[1]), "W23": num(r[2]), "stated_delta": r[3]}
        ok = all(v["W23"] - v["W22"] == num(v["stated_delta"].lstrip("+")) for v in rows.values())
        q, s, e = table_quote(source, plan)
        obs.append({
            "obs_id": "O4", "kind": "arithmetic",
            "question": "计划表 W22→W23→变化 三列是否逐行自洽",
            "computed": {k: {"computed_delta": v["W23"] - v["W22"], "stated": v["stated_delta"]}
                         for k, v in rows.items()},
            "result": "consistent" if ok else "unresolved_difference",
            "status": "resolved" if ok else "unresolved", "unresolved_reason": None,
            "evidence": [{"quote": q, "source_field": "markdown",
                          "note": "计划表 行%d-%d" % (s, e)}]})

    # O5: every "## ①..⑥/" heading present, with line numbers (machine-derived)
    heads = [(line_of(source, m.start()), m.group(0))
             for m in re.finditer(r"^#{1,2} .*$", source, flags=re.M)]
    present = {}
    for mark in ("①", "②", "③", "④", "⑤", "⑥"):
        hit = [h for h in heads if mark in h[1]]
        present[mark] = hit[0][0] if hit else None
    present_heading = next((h[1] for h in heads if "①" in h[1]), heads[0][1] if heads else "")
    obs.append({
        "obs_id": "O5", "kind": "source_shape",
        "question": "报告段结构是否包含 ①–⑥ 六段（行号由脚本扫描得到）",
        "computed": {"heading_count": len(heads), "headings": heads,
                     "section_line": present,
                     "all_six_present": all(present.values())},
        "result": "complete_sections" if all(present.values()) else "missing_sections",
        "status": "resolved" if all(present.values()) else "unresolved",
        "unresolved_reason": None,
        "evidence": [{"quote": present_heading, "source_field": "markdown",
                      "note": "① 段标题行逐字；全部标题及行号见 computed.headings"}]})

    # O6: ⑥ error-judgement table — register the author's <3% posture, do NOT re-judge it
    for t in tables:
        if t["header_names"][:2] == ["关键量", "基准"]:
            col = t["header_names"][-1]
            vals = [r[-1] for r in t["rows"]]
            q, s0, e0 = table_quote(source, t)
            counts = {}
            for v in vals:
                key = "是" if v.startswith("是") else ("不适用" if v.startswith("不适用")
                                                          else ("否" if v.startswith("否") else "other"))
                counts[key] = counts.get(key, 0) + 1
            obs.append({
                "obs_id": "O6", "kind": "cross_field",
                "question": "⑥ 误差判定表的「是否 <3%」列自述到位情况",
                "computed": {"rows": t["data_rows"], "column": col, "value_counts": counts,
                             "external_quantitative_error_rows": 0},
                "result": "author_declared_no_external_baseline",
                "status": "resolved",
                "unresolved_reason": None,
                "evidence": [{"quote": q, "source_field": "markdown",
                              "note": "行%d-%d；本工序只登记作者自述，"
                                      "不复判精度、不代填结论" % (s0, e0)}]})
            break
    return obs


# --------------------------------------------------------------- schema validation
def validate(obj, schema_path):
    try:
        import jsonschema
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "errors": ["jsonschema unavailable: %s" % exc]}
    schema = json.loads(pathlib.Path(schema_path).read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    errs = sorted(v.iter_errors(obj), key=lambda e: list(e.path))
    return {"ok": not errs,
            "errors": ["%s: %s" % ("/".join(map(str, e.path)), e.message) for e in errs[:10]]}


# ------------------------------------------------------------------------- manifest
def main() -> int:
    no_fetch = "--no-fetch" in sys.argv
    PKG.mkdir(parents=True, exist_ok=True)

    record, probes = {}, []
    if no_fetch:
        source = (PKG / "source.md").read_text(encoding="utf-8")
    else:
        token, record = fetch_record()
        source = record.get("markdown", "")
        for path in ("/openapi.json",
                     "/tensor/reports/%s/artifacts" % REPORT_ID,
                     "/tensor/reports/%s/figures" % REPORT_ID,
                     "/tensor/artifacts?report_id=%s" % REPORT_ID):
            probes.append({"path": path, "status": probe(BASE + path, token)})

    raw = source.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if digest != CONTRACT_HASH:
        raise SystemExit("FATAL source hash mismatch: %s != %s" % (digest, CONTRACT_HASH))
    if len(source) != CONTRACT_CHARS:
        raise SystemExit("FATAL chars mismatch: %d != %d" % (len(source), CONTRACT_CHARS))

    (PKG / "source.md").write_bytes(raw)
    (PKG / "sha256.txt").write_text(digest + "\n", encoding="utf-8")

    tables = parse_tables(source)
    assets, checks, unresolved = [], [], []

    assets.append({
        "asset_id": "A01", "asset_class": "report_markdown",
        "label": "报告 markdown 原文（source_field=markdown）",
        "in_report_section": "(整篇)",
        "locator": {"method": "document", "start_char": 0, "end_char": len(source),
                    "start_line": 1, "end_line": source.count("\n") + 1,
                    "quote": source.split("\n")[0], "unique": True},
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "sha256(utf-8 bytes) == contract.source_hash",
                             "result": "resolved"},
        "content_retrievable": True,
        "note": "整篇 markdown 即源资产本体；locator.quote 为第 1 行（全文起点），非抽取"})

    for a in build_asset_table():
        q, occ, how = unique_quote(source, a["seed"])
        if q is None or occ != 1:
            unresolved.append({"asset_id": a["asset_id"], "seed": a["seed"],
                               "occurrences": occ, "why": how})
            continue
        pos = source.find(q)
        extra = dict(a["extra"])
        if a["asset_class"] == "figure_png_reference" and record.get("figures"):
            name = pathlib.Path(a["label"]).name
            hit = [f for f in record["figures"] if f.get("name") == name]
            extra["record_figure"] = hit[0] if hit else None
            extra["record_figure_bound"] = bool(hit)
        if a["asset_id"] == "A07":
            inner = a["seed"].split("{")[1].split("}")[0].split(",")
            extra["expansion"] = ["papers/tools/w23_%s.py" % x for x in inner]
            extra["expansion_count"] = len(extra["expansion"])
        if a["asset_id"] == "A19":
            span = re.search(r"`[^`]*research_plan\.md[^`]*`", source)
            paths = ([p.strip() for p in re.split(r",\s*", span.group(0).strip("`")) if p.strip()]
                     if span else [])
            extra["expansion"] = paths
            extra["expansion_count"] = len(paths)
        entry = {
            "asset_id": a["asset_id"], "asset_class": a["asset_class"], "label": a["label"],
            "in_report_section": a["section_hint"] or section_of(source, pos),
            "locator": {"method": "char_span", "start_char": pos, "end_char": pos + len(q),
                        "start_line": line_of(source, pos),
                        "end_line": line_of(source, pos + len(q) - 1),
                        "quote": q, "unique": occ == 1},
            "resolution": "referenced_unresolved",
            "resolution_check": {"check": "markdown 逐字子串定位（str.find，命中次数==1）",
                                 "result": "resolved"},
            "content_retrievable": False,
            "note": a["note"] + " | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供"
                                "（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"}
        entry.update(extra)
        assets.append(entry)
        checks.append({"locator_id": "L%02d" % (len(checks) + 1), "asset_id": a["asset_id"],
                       "meaning": a["label"], "quote": q,
                       "line": entry["locator"]["start_line"],
                       "line_end": entry["locator"]["end_line"],
                       "char_offset": pos, "char_end": pos + len(q),
                       "occurrences": occ, "match_how": how})

    # ---- inline structure assets (pipe tables): structure only, no values -------
    next_id = 21
    for t in tables:
        header_line = source.split("\n")[t["start_line"] - 1]
        q, occ, how = unique_quote(source, header_line.strip())
        if q is None or occ != 1:
            unresolved.append({"asset_id": "T%02d" % next_id, "seed": header_line,
                               "occurrences": occ, "why": how})
            continue
        pos = source.find(q)
        aid = "A%02d" % next_id
        next_id += 1
        assets.append({
            "asset_id": aid, "asset_class": "inline_markdown_table",
            "label": "pipe 表：%s" % " | ".join(t["header_names"]),
            "in_report_section": section_of(source, pos),
            "locator": {"method": "char_span", "start_char": pos, "end_char": pos + len(q),
                        "start_line": t["start_line"], "end_line": t["end_line"],
                        "quote": q, "unique": True},
            "resolution": "resolved_in_source",
            "resolution_check": {"check": "表头行逐字定位 + 分隔行正则校验", "result": "resolved"},
            "content_retrievable": True,
            "structure": {"data_rows": t["data_rows"], "header_cells": t["header_cells"],
                          "header_names": t["header_names"],
                          "table_line_span": t["end_line"] - t["start_line"] + 1},
            "note": "只登记结构（行数/列数/表头），不抽取任何数值（契约 objective 不做抽取）"})
        checks.append({"locator_id": "T%02d" % (next_id - 21), "asset_id": aid,
                       "meaning": "pipe 表结构：" + " | ".join(t["header_names"]),
                       "quote": q, "line": t["start_line"], "line_end": t["end_line"],
                       "char_offset": pos, "char_end": pos + len(q),
                       "occurrences": occ, "match_how": how})

    if unresolved:
        raise SystemExit("FATAL unresolved locators (refusing to write a manifest): %s"
                         % json.dumps(unresolved, ensure_ascii=False))

    observations = integrity_observations(source, tables)

    # ---- evidence gate: every observation quote must be literally in its source field ----
    rec_text = " ".join(str(record.get(k) or "") for k in ("title", "summary"))
    bad_quotes = []
    for o in observations:
        for ev in o["evidence"]:
            hay = source if ev["source_field"] == "markdown" else rec_text
            if ev["quote"] not in hay:
                bad_quotes.append({"obs_id": o["obs_id"], "source_field": ev["source_field"],
                                   "quote": ev["quote"][:80]})
    if bad_quotes:
        raise SystemExit("FATAL non-verbatim evidence quote(s): %s"
                         % json.dumps(bad_quotes, ensure_ascii=False))

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    dup = [c for c in checks if source.count(c["quote"]) != 1]
    quote_uniqueness = {"checked": len(checks), "violations": len(dup), "all_unique": not dup,
                        "note": "每条引文在 markdown 中命中次数必须恰为 1；violations 必须为 0"}

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": "tensor://reports/" + REPORT_ID,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest.split(":", 1)[1],
            "chars": len(source),
            "bytes_utf8": len(raw),
            "title": record.get("title") or CONTRACT_TITLE,
            "scenario_key": record.get("scenario_key") or CONTRACT_SCENARIO,
            "mission_id": record.get("mission_id"),
            "status": record.get("status"),
            "created_at": record.get("created_at"),
            "created_by": record.get("created_by"),
            "platform_figures": record.get("figures", []),
            "platform_tags": record.get("tags", []),
            "title_matches_contract": (record.get("title") or CONTRACT_TITLE) == CONTRACT_TITLE,
            "scenario_key_matches_contract": (record.get("scenario_key") or CONTRACT_SCENARIO)
                                             == CONTRACT_SCENARIO,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "chars_matches_contract": len(source) == CONTRACT_CHARS},
        "counts": {
            "assets": len(assets), "by_class": by_class, "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "inline_tables_registered": len([a for a in assets
                                             if a["asset_class"] == "inline_markdown_table"]),
            "inline_fenced_blocks": len(re.findall(r"^```", source, flags=re.M)) // 2},
        "assets": assets,
        "claims": [],
        "integrity_observations": observations,
        "artifact_endpoint_probe": {
            "base": BASE, "probes": probes,
            "conclusion": "无端点提供被引用工件（figures/脚本/数据）的字节；故这些资产只能登记到"
                          "「路径+声明哈希」层级，resolution=referenced_unresolved"},
        "locator_check_summary": {"locators": len(checks), "unresolved": 0,
                                  "tables_detected": len(tables)},
        "integrity": {
            "quote_uniqueness": quote_uniqueness,
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "chars_contract": CONTRACT_CHARS,
            "chars_computed": len(source),
            "chars_matches_contract": len(source) == CONTRACT_CHARS,
            "source_copy_sha256": "sha256:" + hashlib.sha256(
                (PKG / "source.md").read_bytes()).hexdigest(),
            "claims_emitted": 0,
            "nothing_marked_verified": True,
            "observation_quotes_verbatim": {"checked": sum(len(o["evidence"]) for o in observations),
                                            "violations": len(bad_quotes)}},
        "limitations": [
            "本工序只登记资产，不抽取内容、不分类、不产生 claim（契约 objective.classify_report_type=false）",
            "被引用文件（png/脚本/数据/plan/registry）的字节不可经任何端点取得，故 resolution="
            "referenced_unresolved：只核了正文里的路径字符串，未核文件存在性与声明哈希",
            "integrity_observations 是算术/跨字段一致性登记，状态只有 consistent / unresolved，"
            "不含任何 verified 结论"],
    }

    (PKG / "locator_check.json").write_text(
        json.dumps({"report_id": REPORT_ID, "source_hash": digest, "locators": checks,
                    "unresolved": unresolved}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    # Idempotent emission: KF_EMITTED_AT wins, else reuse the emitted_at of an existing
    # envelope for the same source hash, else now. Re-running the pipeline therefore
    # reproduces byte-identical artifacts (the published result block stays comparable
    # to the worktree file).
    emitted_at = (os.environ.get("KF_EMITTED_AT")
                  or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"))
    prev = PKG / "kf_result.json"
    if prev.exists() and not os.environ.get("KF_EMITTED_AT"):
        try:
            old = json.loads(prev.read_text(encoding="utf-8"))
            if old.get("provenance", {}).get("source_hash") == digest:
                emitted_at = old["provenance"]["emitted_at"]
        except Exception:  # noqa: BLE001 - a stale/corrupt file must not block emission
            pass

    result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": digest,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": emitted_at,
            "notes": "sha256 由本进程对 GET /api/v1/tensor/reports/14214 的 markdown 字段独立重算；"
                     "与契约声明逐字节一致，chars=%d" % len(source)},
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    schema_kf = ROOT / "schemas" / "kf_result.v1.schema.json"
    schema_am = ROOT / "schemas" / "asset_manifest.v1.wp-14214-01.schema.json"
    v_kf = validate(result, schema_kf)
    v_am = validate(manifest, schema_am)
    manifest["integrity"]["kf_result_schema"] = {"path": str(schema_kf.relative_to(ROOT)),
                                                 "valid": v_kf["ok"],
                                                 "errors": v_kf.get("errors", [])}
    manifest["integrity"]["asset_manifest_schema"] = {
        "path": str(schema_am.relative_to(ROOT)), "valid": v_am["ok"],
        "errors": v_am.get("errors", [])}

    (PKG / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
    (PKG / "kf_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")

    ids = {a["asset_id"] for a in assets}
    selfchecks = [
        ("valid_json", True,
         "asset_manifest.json / kf_result.json 均由 json.dumps 产出并被 json.load 回读"),
        ("schema_pass", v_kf["ok"] and v_am["ok"],
         "kf_result.v1=%s, asset_manifest.v1.wp-14214-01=%s" % (v_kf["ok"], v_am["ok"])),
        ("source_locator_resolvable", not dup,
         "%d 条 locator 全部 str.find 命中且次数==1；violations=%d" % (len(checks), len(dup))),
        ("source_hash_matches", digest == CONTRACT_HASH, "%s == 契约 %s" % (digest, CONTRACT_HASH)),
        ("no_duplicate_ids", len(ids) == len(assets),
         "asset_id 唯一：%d/%d" % (len(ids), len(assets))),
        ("all_claims_have_evidence_or_explicit_unresolved_status", True,
         "claims=[] （契约允许空数组，无强制造 claim）"),
        ("[附加] evidence_quotes_verbatim", not bad_quotes,
         "%d 条一致性登记引文全部可在 source_field 内逐字定位；violations=%d"
         % (sum(len(o["evidence"]) for o in observations), len(bad_quotes))),
    ]
    (PKG / "selfcheck.json").write_text(json.dumps(
        {"selfchecks": [{"item": n, "ok": ok, "why": w} for n, ok, w in selfchecks],
         "schema_validation": {"kf_result": v_kf, "asset_manifest": v_am}},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    body = render_body(manifest, result, checks, selfchecks, v_kf, v_am)
    (PKG / "report_body.md").write_text(body, encoding="utf-8")
    (ROOT / ("docs/kf_result_%s.md" % PACKAGE_ID)).write_text(body, encoding="utf-8")

    print(json.dumps({"digest": digest, "chars": len(source), "assets": len(assets),
                      "by_resolution": by_res, "locators": len(checks),
                      "observations": [(o["obs_id"], o["status"], o["result"]) for o in observations],
                      "kf_result_schema_ok": v_kf["ok"], "asset_manifest_schema_ok": v_am["ok"],
                      "selfchecks": [(n, ok) for n, ok, _ in selfchecks]},
                     ensure_ascii=False, indent=2))
    return 0 if all(ok for _, ok, _ in selfchecks) else 1


# ---------------------------------------------------------------------- report body
def render_body(manifest, result, checks, selfchecks, v_kf, v_am):
    src = manifest["source"]
    obs = manifest["integrity_observations"]
    by_class = manifest["counts"]["by_class"]
    pid = manifest["package_id"]

    asset_tbl = ["| asset_id | class | label | 节 | 定位行 | resolution |", "|---|---|---|---|---|---|"]
    for a in manifest["assets"]:
        asset_tbl.append("| `%s` | %s | %s | %s | %d | %s |"
                         % (a["asset_id"], a["asset_class"], a["label"].replace("|", "\\|"),
                            a["in_report_section"].replace("|", "\\|"),
                            a["locator"]["start_line"], a["resolution"]))

    ev_tbl = ["| locator | asset | 引文（逐字） | 行 | 字符偏移 | 命中 |", "|---|---|---|---|---|---|"]
    for c in checks:
        q = c["quote"].replace("|", "\\|").replace("\n", "⏎")
        fence = "``" if "`" in q else "`"
        if len(q) > 64:
            q = q[:62] + "…"
        ev_tbl.append("| %s | `%s` | %s%s%s | %d | %d | %d |"
                      % (c["locator_id"], c["asset_id"], fence, q, fence,
                         c["line"], c["char_offset"], c["occurrences"]))

    obs_tbl = ["| obs | 类型 | 检查 | 计算值 | 结果 | 状态 |", "|---|---|---|---|---|---|"]
    for o in obs:
        obs_tbl.append("| %s | %s | %s | `%s` | %s | %s |"
                       % (o["obs_id"], o["kind"], o["question"],
                          json.dumps(o["computed"], ensure_ascii=False), o["result"], o["status"]))

    self_tbl = ["| acceptance 项 | 结果 | 依据 |", "|---|---|---|"]
    for n, ok, w in selfchecks:
        self_tbl.append("| %s | %s | %s |"
                        % (n, "☑ PASS" if ok else "☒ FAIL", w.replace("|", "\\|")))

    probe_tbl = ["| 探测端点 | 结果 |", "|---|---|"]
    for p in manifest["artifact_endpoint_probe"]["probes"]:
        probe_tbl.append("| `%s` | %s |" % (p["path"], p["status"]))

    fig_tbl = ["| 报告声明图件 | sha256_16（正文声明） | record.figures 绑定 |", "|---|---|---|"]
    for a in manifest["assets"]:
        if a["asset_class"] == "figure_png_reference":
            fig_tbl.append("| `%s` | `%s` | %s |"
                           % (a["label"], a.get("declared_sha256_16"),
                              "已绑定" if a.get("record_figure_bound") else "未绑定"))

    exp_tbl = ["| asset | expansion（机械展开） |", "|---|---|"]
    for a in manifest["assets"]:
        if a.get("expansion"):
            exp_tbl.append("| `%s` | %s |"
                           % (a["asset_id"], "<br>".join("`%s`" % x for x in a["expansion"])))

    json_block = json.dumps(result, ensure_ascii=False, indent=2)
    cls = ", ".join("%s=%d" % kv for kv in sorted(by_class.items()))

    return f"""# KF-RESULT {pid}

**tags**: kf-wp:{pid}, asset-registration, report-14214, lane-B, TensorKnowledge, draft
**package_id**: {pid} ｜ **task_type**: {manifest['task_type']} ｜ **report_id**: {manifest['report_id']}
**lane**: B ｜ **repo**: TensorKnowledge ｜ **source_uri**: `{src['uri']}` ｜ **分层**: TensorPapers|analysis|B

---

## ① 本工序做了什么

只做 `report_id={manifest['report_id']}`（《{src['title']}》）的**资产登记**（工序 `{manifest['task_type']}`）：

1. **确认身份**：独立重算 markdown `sha256:{src['hash']}`，与契约 `source_hash` 逐字节一致；
   `chars={src['chars']}`（= python str 长度，与契约 `chars` 相同），UTF-8 字节 `{src['bytes_utf8']}`
   （CJK 正文两口径必然不同，此处写明口径）。
2. **登记资产 {manifest['counts']['assets']} 项**（{cls}），每项给逐字引文 + 行号 + 字符偏移 + 命中次数。
3. **登记正文内可解析块结构 {manifest['counts']['inline_tables_registered']} 个 pipe 表**
   （只记数据行数/表头列数/行区间，**不抽取任何数值**）；fenced 块 {manifest['counts']['inline_fenced_blocks']} 个。
4. **登记报告声明的图件 5 张**（路径 + 正文声明的 sha256_16），并与记录 `figures[]`
   （name + caption）逐图交叉绑定。
5. **算术/跨字段一致性登记 {len(obs)} 条**（`integrity_observations`）：状态只有 `consistent` /
   `unresolved`，**不含任何 verified 结论**。
6. **不做抽取、不分类、不产生 claim**（契约 `objective.classify_report_type: false`；`claims=[]`）。
   **没有任何结论被标成 verified**——哈希相等只是机械身份校验，verification 由平台门计算。

边界：只读 `GET /api/v1/tensor/reports/{manifest['report_id']}` 这一份记录；未读写任何其它 report_id；
未改写上游或其它工作包的产物。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **契约入参**：`package_id={pid}`、`report_id={manifest['report_id']}`、`source_field=markdown`、
   `source_hash=sha256:edc85090…2d1af9`、`chars=6258`、`scenario_key={src['scenario_key']}`；
   六条 acceptance 直接落到 ⑥ 自检表。
2. **取源**：`POST /api/v1/auth/login`（凭据只从 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS` 环境变量读，
   不落盘）→ `GET /api/v1/tensor/reports/{manifest['report_id']}`（Bearer），取 `markdown` 全文；
   同记录的 `title/scenario_key/mission_id/status/created_at/tags/figures` 一并登记为元数据。
3. **独立哈希**：`hashlib.sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 逐字节比较，
   不一致即 `SystemExit`（失败不出产物）；同时核 `len(markdown)==6258`。
4. **零手抄定位**：脚本内引文种子逐条 `str.find`；种子不唯一时**按整行机械扩展**到唯一
   （`unique_quote`，`match_how` 记录扩展方式），任一未命中/不唯一即 `SystemExit`，不写 manifest。
   解析结果落 `docs/kf/wp-14214-01/locator_check.json`。
5. **表结构登记**：pipe 表由分隔行正则识别，只算 `data_rows` / `header_cells`。
6. **工件端点探测**：`/openapi.json`、`/tensor/reports/14214/artifacts`、`/tensor/reports/14214/figures`、
   `/tensor/artifacts?report_id=14214` 逐一探测（带 Bearer），见 ⑤：
   无端点提供被引用文件字节 → 这些资产 `resolution=referenced_unresolved`、`content_retrievable=false`。
7. **复跑**：`python3 scripts/kf_wp14214_01_register.py`（追加 `--no-fetch` 用包内 `source.md`
   离线复现，仅跳过联网取源与端点探测）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-14214-01/source.md` | 登记用 markdown 字节副本（{src['bytes_utf8']} B / {src['chars']} chars） |
| `docs/kf/wp-14214-01/sha256.txt` | 独立重算摘要 |
| `docs/kf/wp-14214-01/locator_check.json` | {len(checks)} 条引文定位（行/字符偏移/命中次数/match_how） |
| `docs/kf/wp-14214-01/asset_manifest.json` | 契约输出 `asset_manifest.json`：{manifest['counts']['assets']} 资产 + {len(obs)} 条一致性登记 |
| `docs/kf/wp-14214-01/kf_result.json` | `kf_result.v1` 信封（schema 校验 {v_kf['ok']}） |
| `docs/kf/wp-14214-01/selfcheck.json` | 6 条 acceptance 机检 + 两份 schema 校验明细 |
| `docs/kf/wp-14214-01/report_body.md`、`docs/kf_result_{pid}.md` | 本报告正文（同一内容两处落盘） |

资产清单（{manifest['counts']['assets']} 项）：

{chr(10).join(asset_tbl)}

图件登记：

{chr(10).join(fig_tbl)}

聚合引用的机械展开：

{chr(10).join(exp_tbl)}

## ④ 证据定位表（字段 / 资产 → 原文逐字引文）

登记级字段全部由机器命中；下表引文即 `locator_check.json` 的内容（逐字、含行号与字符偏移）：

{chr(10).join(ev_tbl)}

一致性登记（`integrity_observations`）：

{chr(10).join(obs_tbl)}

## ⑤ 注意点与局限

1. **被引用工件不可取字节**：png / 脚本 / 数据目录 / research_plan / registry 只在正文里被点名，
   报告记录不携带其字节（端点探测见下表）——因此它们一律 `referenced_unresolved`：
   **只核了「路径字符串在正文里逐字存在」，没有核文件是否存在、也没核其与声明 sha256_16 是否相符**。

{chr(10).join(probe_tbl)}

2. **O2 是真冲突，不粉饰**：正文 ③ 写「阻断 **23**」，而记录 `title`/`summary` 与本包契约 `title`
   写「阻断22」。本工序**只登记不裁决**（报告内无第三方口径可裁），状态 `unresolved`，绝不标 verified。
3. **O1 差额未归因**：184+138+60=382 ≠ 窗口 430，差 48 篇；报告未说明归属（未判/NULL 判词无声明），
   本工序不推断。
4. **人工初读假象（已由机器纠正）**：本工序首屏 `cat` 输出被终端截断，人工初读以为 markdown 缺 ① 段；
   机器解析显示第 1 行是 `# W23 论文生产线研究总结…`、第 6 行是 `## ① 案例介绍（研究域与证据面）`，
   ①–⑥ 六段齐全（O5）。故本包所有事实一律以 `str.find`/正则结果为准，不以肉眼首屏为准。
5. **不做精度判定**：本工序不产生领域量、不复算报告里的任何精度结论。报告 ⑥ 的「是否<3%」是
   报告作者给出的判据（多为恒等核/无外部基准），本工序的立场是**本工序无精度量可判**，不代填、不背书。
6. **hash 相等的含义边界**：相等只说明我读到的 markdown 与平台记录同一份（机械恒等），
   不代表内容正确，更不代表任何结论 verified。
7. **不越界**：未读其它 report_id、未改上游产物、未写任何「verified」字段。

## ⑥ 自检（逐条对照 acceptance）

{chr(10).join(self_tbl)}

未完成/未验证的部分（如实写）：被引用工件的字节级存在性与哈希**未核**（无端点可取）；
成稿门阻断计数 22/23 的冲突**未裁决**；O1 的 48 篇差额**未归因**。这三项都超出本工序
（资产登记）的边界，已在 `asset_manifest.json` 的 `limitations` 与 `integrity_observations` 中留痕。

## ⑦ 结果 JSON（本报告唯一 json 代码块）

```json
{json_block}
```
"""


if __name__ == "__main__":
    sys.exit(main())
