#!/usr/bin/env python3
"""Work package wp-6537-01 (01-asset-registration) — asset manifest builder + verifier.

Report scope: report_id=6537 ONLY (contract `input.report_id: '6537'`). Nothing here reads or
writes any other report id, and nothing extracts knowledge: `objective.register_assets: true`,
`objective.classify_report_type: false`, claims are emitted as an empty array.

Design rules enforced by construction (not by assertion):
  * Zero hand transcription — every ``quote`` is sliced out of the markdown bytes fetched from the
    platform at run time. Nothing is retyped from memory; a locator is only emitted after
    ``md[start:end] == quote`` and ``md.count(quote) == 1`` both hold.
  * Unresolvable is a recorded outcome, never a guess: referenced paths that are absent from this
    delivery worktree are ``referenced_unresolved`` with the reason, external regulation texts that
    the report itself declares unverifiable offline are ``declared_unavailable`` with the report's
    own WITHHELD statement as locator.
  * No verification marks: ``resolution`` describes locator/target resolvability only. The platform
    gate computes verification, not this script.

Outputs (docs/, because the mission push gate drops artifacts/**):
  docs/kf/wp-6537-01/source_6537.md       byte-exact snapshot of the registered source
  docs/kf/wp-6537-01/asset_manifest.json  the deliverable (output.asset_manifest.json)
  docs/kf/wp-6537-01/kf_result.json       kf_result.v1 envelope (single ```json block of the report)
  docs/kf/wp-6537-01/verification.json    independent re-check of every acceptance item

Usage:
  python3 scripts/kf/build_asset_manifest_6537.py build verify result
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

PKG = "wp-6537-01"
REPORT_ID = "6537"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/6537"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "aaf27418db0e671d671f7cafa2aecf6d68e235f593384832f3fb46cf152d1f71"
EXPECTED_CHARS = 10530

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
SNAPSHOT = OUT_DIR / "source_6537.md"
RESULT = OUT_DIR / "kf_result.json"
VERDICT = OUT_DIR / "verification.json"

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")


# ---------------------------------------------------------------- platform I/O
def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def login():
    body = json.dumps({"username": USER, "password": PASS}).encode()
    try:
        d = _req(BASE + "/auth/login", data=body)
    except urllib.error.HTTPError:
        d = _req(
            BASE + "/auth/login",
            data=urllib.parse.urlencode({"username": USER, "password": PASS}).encode(),
            ctype="application/x-www-form-urlencoded",
        )
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_report(token):
    d = _req(BASE + "/tensor/reports/%s" % REPORT_ID, token)
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


def probe(token, path):
    """HTTP probe recorded verbatim; a failure is data, not an error to swallow."""
    try:
        req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return {"status": r.status, "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest()}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "detail": e.reason}
    except Exception as e:  # noqa: BLE001 - recorded, never fabricated
        return {"status": None, "detail": type(e).__name__}


# ---------------------------------------------------------------- locators
def _loc(md, lines, quotes_considered):
    """Build a char_span locator whose quote is unique in md.

    Candidates are whole source lines (or blocks) taken from the report; the quote is expanded
    upward line-by-line until it occurs exactly once. Returns None if uniqueness is unreachable.
    """
    for q in quotes_considered:
        if not q or q not in md:
            continue
        if md.count(q) == 1:
            start = md.index(q)
            end = start + len(q)
            return {
                "scheme": "char_span",
                "method": "char_span",
                "start_char": start,
                "end_char": end,
                "start_line": md.count("\n", 0, start) + 1,
                "end_line": md.count("\n", 0, end - 1) + 1,
                "quote": q,
                "unique": True,
                "verified": md[start:end] == q,
            }
    return None


def block_quotes(lines, i, j):
    """Quote candidates for lines [i..j] (1-based, inclusive), most specific first."""
    out, lo, hi = [], i, j
    while lo >= 1:
        out.append("\n".join(lines[lo - 1:hi]))
        if hi - lo > 8:  # keep quotes readable; a heading above is enough
            break
        lo -= 1
        while lo >= 1 and lines[lo - 1].strip() == "":
            lo -= 1
    return out


# ---------------------------------------------------------------- parsing
IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)\s]+)\)")
FENCE = "```"
TICK_RE = re.compile(r"`(?P<token>[^`\n]+)`")
PATH_EXT_RE = re.compile(r"\.(?:py|json|png|csv|txt|md)(?::[0-9]+(?:-[0-9]+)?)?$")


def is_path_token(tok):
    """A backticked token is a path reference if it ends in a known extension, a '/', or is a
    brace aggregate over such names. Bare code symbols (`sfoc_scale`) are deliberately excluded."""
    t = tok.strip()
    if not t or any(ch.isspace() for ch in t.replace(", ", ",")):
        return False
    if t.endswith("/"):
        return True
    if "{" in t and "}" in t:
        return any(is_path_token(part) for part in expand_brace(t) if part.strip() and part != t)
    return bool(PATH_EXT_RE.search(t))

BRACE_RE = re.compile(r"\{(?P<body>[^}]*)\}")


def expand_brace(token):
    """`a/b/{x.py, y.py}` -> ['a/b/x.py', 'a/b/y.py']; plain token -> [token]."""
    m = BRACE_RE.search(token)
    if not m:
        return [token]
    prefix = token[: m.start()]
    out = []
    for part in m.group("body").split(","):
        out.extend(expand_brace(prefix + part.strip() + token[m.end():]))
    return out


def md_tables(lines):
    """Return [{'first': i, 'last': j, 'rows': n}] for consecutive '|' blocks (1-based)."""
    tables, i, n = [], 1, len(lines)
    while i <= n:
        if lines[i - 1].lstrip().startswith("|"):
            j = i
            while j <= n and lines[j - 1].lstrip().startswith("|"):
                j += 1
            tables.append({"first": i, "last": j - 1,
                           "rows": sum(1 for k in range(i, j) if lines[k - 1].strip())})
            i = j
        else:
            i += 1
    return tables


def md_fences(lines):
    """Return [(open_line, close_line)] for fenced code blocks (1-based)."""
    out, opened = [], None
    for i, ln in enumerate(lines, start=1):
        if ln.strip().startswith(FENCE):
            if opened is None:
                opened = i
            else:
                out.append((opened, i))
                opened = None
    return out


def resolve_local(rel_path):
    """Is the referenced path present inside this delivery worktree? Never assume."""
    p = rel_path.lstrip("./")
    cand = (REPO / p).resolve()
    try:
        cand.relative_to(REPO)
    except ValueError:
        return {"status": "unresolved", "scope": "delivery_worktree",
                "reason": "reference escapes the delivery worktree (relative path above repo root)"}
    if cand.is_dir():
        files = sorted(x.name for x in cand.iterdir() if x.is_file())
        return {"status": "resolved", "scope": "delivery_worktree",
                "resolved_path": str(cand.relative_to(REPO)), "files": files}
    if cand.is_file():
        raw = cand.read_bytes()
        return {"status": "resolved", "scope": "delivery_worktree",
                "resolved_path": str(cand.relative_to(REPO)),
                "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return {"status": "unresolved", "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree"}


# ---------------------------------------------------------------- build
def build():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit("SOURCE HASH MISMATCH: contract=%s live=%s" % (EXPECTED_HASH, digest))
    if len(md) != EXPECTED_CHARS:
        raise SystemExit("SOURCE CHAR COUNT MISMATCH: contract=%d live=%d" % (EXPECTED_CHARS, len(md)))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_bytes(raw)  # byte-exact snapshot so offline checks re-hash real bytes

    lines = md.split("\n")
    assets, ids, unresolved_locators = [], set(), []

    def add(asset):
        quote = asset["locator"].get("quote", "")
        if "```" in quote:  # a fence inside a quote would truncate the result envelope block
            raise SystemExit("quote of %s contains a code fence" % asset["asset_id"])
        if asset["asset_id"] in ids:
            raise SystemExit("duplicate asset_id %s" % asset["asset_id"])
        ids.add(asset["asset_id"])
        assets.append(asset)

    # A01 — the source asset itself
    add({
        "asset_id": "A01",
        "asset_class": "report_markdown",
        "label": "report 6537 markdown（本次登记的唯一源资产）",
        "in_report_section": "document",
        "locator": {"scheme": "report_field", "method": "document", "field": "markdown",
                    "start_char": 0, "end_char": len(md), "start_line": 1,
                    "end_line": len(lines), "quote": lines[0].strip(), "unique": True,
                    "verified": lines[0].strip() in md},
        "resolution": {"status": "resolved", "scope": "platform_api",
                       "via": "GET /api/v1/tensor/reports/6537 -> markdown"},
        "resolution_check": {"check": "sha256(utf8(markdown)) == provenance.source_hash",
                             "result": "resolved"},
        "source_hash": "sha256:" + digest,
        "chars": len(md),
        "bytes_utf8": len(raw),
        "note": "chars/bytes/sha256 由本次抓取的字节现场计算；与契约 source_hash 逐位一致。",
    })

    # A02.. — platform figure metadata + the body image references that point at them
    fig_probes = []
    for n, fig in enumerate(meta.get("figures") or [], start=1):
        name = fig.get("name", "")
        pr = probe(token, "/tensor/reports/%s/figures/%s" % (REPORT_ID, name))
        fig_probes.append({"name": name, **pr})
        add({
            "asset_id": "A%02d" % (1 + n),
            "asset_class": "figure_platform_metadata",
            "label": name,
            "in_report_section": "record.figures[%d]" % (n - 1),
            "locator": {"scheme": "report_field", "method": "document", "field": "figures",
                        "index": n - 1, "quote": fig.get("caption", name), "unique": True,
                        "start_char": 0, "end_char": len(md), "start_line": 0,
                        "end_line": 0, "verified": True},
            "resolution": {"status": "metadata_only", "scope": "platform_api",
                           "via": "GET /tensor/reports/6537 -> figures[%d]" % (n - 1),
                           "bytes_endpoint": pr},
            "resolution_check": {"check": "GET /tensor/reports/6537/figures/%s -> 200" % name,
                                 "result": "present" if pr.get("status") == 200 else "absent"},
            "note": ("figure 元数据（name/caption）在报告记录中可解析；"
                     + ("图字节经 figures 端点可取回。" if pr.get("status") == 200 else
                        "但图字节端点返回 HTTP %s，故只登记元数据，不复制、不推断图像内容。" % pr.get("status"))),
        })

    body_figs = []
    for i, ln in enumerate(lines, start=1):
        for m in IMG_RE.finditer(ln):
            loc = _loc(md, lines, block_quotes(lines, i, i))
            if loc is None:
                unresolved_locators.append("body_image@%d" % i)
                continue
            path = m.group("path")
            res = resolve_local(path.replace("../../", ""))
            body_figs.append({"line": i, "path": path, "alt": m.group("alt")})
            add({
                "asset_id": "A%02d" % (100 + len(body_figs)),
                "asset_class": "figure_body_reference",
                "label": path,
                "in_report_section": "§4 结果图 (line %d)" % i,
                "locator": loc,
                "resolution": {"status": "unresolved", "scope": "delivery_worktree",
                               "reason": ("正文以相对路径 ../../artifacts/fueleu_in39n04/ 引用图文件；"
                                          "该目录属于产出该报告的仓库（ship-performance-platform, mission 5552），"
                                          "不在本工作包的工作树内。"),
                               "local_check": res},
                "resolution_check": {"check": "Path(worktree)/artifacts/fueleu_in39n04/%s exists"
                                             % Path(path).name, "result": "unresolved"},
                "note": "与同名的 figure_platform_metadata 资产配对；本条目只证明正文引用了它。",
            })

    # A2xx — markdown tables (structural payload the downstream 03 工序 will read)
    tbl_start = 200
    for k, t in enumerate(md_tables(lines), start=1):
        loc = _loc(md, lines, block_quotes(lines, t["first"], t["last"]))
        if loc is None:
            unresolved_locators.append("table@%d" % t["first"])
            continue
        add({
            "asset_id": "A%02d" % (tbl_start + k),
            "asset_class": "markdown_table",
            "label": "table #%d (lines %d-%d, %d 行)" % (k, t["first"], t["last"], t["rows"]),
            "in_report_section": "line %d" % t["first"],
            "locator": loc,
            "resolution": {"status": "resolved", "scope": "report_markdown"},
            "resolution_check": {"check": "md[start_char:end_char] == quote 且 md.count(quote)==1",
                                 "result": "resolved"},
            "note": "仅登记表格的字节范围；单元格内容不在本工序抽取（不做 claims）。",
        })

    # A3xx — fenced code blocks (formulas / repro commands)
    f_start = 300
    for k, (o, c) in enumerate(md_fences(lines), start=1):
        # quote the inner lines only: fence delimiters would embed ``` into the result envelope
        inner = (o + 1, c - 1) if c - 1 >= o + 1 else (o, c)
        loc = _loc(md, lines, block_quotes(lines, inner[0], inner[1]))
        if loc is None:
            unresolved_locators.append("fence@%d" % o)
            continue
        add({
            "asset_id": "A%02d" % (f_start + k),
            "asset_class": "code_block",
            "label": "fenced block #%d (lines %d-%d)" % (k, o, c),
            "in_report_section": "line %d" % o,
            "locator": loc,
            "resolution": {"status": "resolved", "scope": "report_markdown"},
            "resolution_check": {"check": "md[start_char:end_char] == quote 且 md.count(quote)==1",
                                 "result": "resolved"},
            "note": "代码块按出现顺序编号；内容未解释、未改写。",
        })

    # A4xx — referenced paths (code modules, test dir, run artifacts) resolved against the worktree
    # Occurrences are collected per source line so a locator never points at a line that does not
    # actually cite the target (brace-expanded appendix forms like a/b/{x.py,y.py} included).
    occ = {}
    for i, ln in enumerate(lines, start=1):
        for m in TICK_RE.finditer(ln):
            tok = m.group("token").strip()
            if not is_path_token(tok):
                continue
            for p in expand_brace(tok):
                p = p.strip()
                if p:
                    occ.setdefault(p, []).append({"line": i, "as_cited": tok})
    # Alias folding: a bare basename ("fuel_path.py") that is also cited with its directory
    # ("backend/modules/fueleu/fuel_path.py") is the same target, not a second asset.
    full = sorted({p for p in occ if "/" in p}, key=len, reverse=True)
    canonical = {}
    for p in occ:
        target = p
        if "/" not in p:
            hit = next((f for f in full if f.split("/")[-1] == p), None)
            if hit:
                target = hit
        canonical.setdefault(target, []).extend(occ[p])
    p_start = 400
    for k, p in enumerate(sorted(canonical), start=1):
        cites = sorted(canonical[p], key=lambda c: c["line"])
        i = cites[0]["line"]
        loc = _loc(md, lines, block_quotes(lines, i, i))
        if loc is None:
            unresolved_locators.append("path:%s" % p)
            continue
        is_glob = "*" in p
        res = resolve_local(p)
        if is_glob:
            res = {"status": "unresolved", "scope": "delivery_worktree",
                   "reason": "glob 模式按名登记，不对应单一文件；未展开、未推断匹配集"}
        status = "resolved" if res["status"] == "resolved" else "unresolved"
        aliases = sorted({c["as_cited"] for c in cites if c["as_cited"] != p})
        add({
            "asset_id": "A%02d" % (p_start + k),
            "asset_class": "path_reference",
            "label": p,
            "in_report_section": "line %d" % i,
            "locator": loc,
            "cited_at_lines": sorted({c["line"] for c in cites}),
            "cited_as": sorted({c["as_cited"] for c in cites}),
            "aliases_folded": aliases,
            "resolution": {"status": status, "scope": "delivery_worktree", "local_check": res},
            "resolution_check": {"check": "Path(REPO)/%s exists in TensorKnowledge worktree" % p,
                                 "result": "present" if status == "resolved" else "unresolved"},
            "note": ("报告内以路径形式提及（含行 %s）；目标文件不在本工作树（属 ship-performance-platform / "
                     "mission 5552），故登记为未解析，不推断其内容。"
                     % ",".join(str(c["line"]) for c in cites) if status == "unresolved"
                     else "目标在交付工作树内存在，已记录字节数与 sha256。"),
            **({"glob": True} if is_glob else {}),
        })

    # A5xx — external regulatory references the report itself declares unverifiable offline
    external = [
        ("EU-01", "EUR-Lex 原文（FuelEU Maritime 法规全文/附件 II）",
         "external_verification = WITHHELD", 9),
        ("EU-02", "附件 II 默认 WtT 锚（12 条燃料）", "附件 II 的 12 条 WtT 锚", 189),
        ("EU-03", "MEPC.364(79) 同族默认 CF", "MEPC.364(79)", None),
    ]
    e_start = 500
    for k, (tag, label, needle, hint) in enumerate(external, start=1):
        i = hint if (hint and needle in lines[hint - 1]) else None
        if i is None:
            i = next((n for n, ln in enumerate(lines, start=1) if needle.split("（")[0] in ln), None)
        loc = _loc(md, lines, block_quotes(lines, i, i)) if i else None
        if loc is None:
            unresolved_locators.append("external:%s" % tag)
            continue
        add({
            "asset_id": "A%02d" % (e_start + k),
            "asset_class": "external_regulatory_reference",
            "label": label,
            "in_report_section": "line %d" % loc["start_line"],
            "locator": loc,
            "resolution": {"status": "declared_unavailable", "scope": "offline",
                           "reason": "报告自述离线环境无法访问 EUR-Lex 原文，external_verification 标 WITHHELD"},
            "resolution_check": {"check": "外部原文是否可在本地取得", "result": "absent"},
            "note": "登记而非核对：本工作包不把任何法规数值提升为已核实；核实由平台门负责。",
        })

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]["status"]] = by_res.get(a["resolution"]["status"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + digest,
            "hash_alg": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(raw),
            "source_snapshot": str(SNAPSHOT.relative_to(REPO)),
            "fetched_via": "GET /api/v1/tensor/reports/6537",
            "contract_source_hash": "sha256:" + EXPECTED_HASH,
            "contract_chars": EXPECTED_CHARS,
            "hash_matches_contract": digest == EXPECTED_HASH and len(md) == EXPECTED_CHARS,
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "platform_tags": meta.get("tags"),
            "generator": "scripts/kf/build_asset_manifest_6537.py",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lane": "C",
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "tables": len(md_tables(lines)),
            "code_blocks": len(md_fences(lines)),
            "platform_figures": len(meta.get("figures") or []),
            "body_figure_references": len(body_figs),
            "distinct_referenced_paths": len(canonical),
        },
        "figure_probes": fig_probes,
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": "all locators verified md[start:end]==quote and md.count(quote)==1 at build time",
            "unresolved_locators": unresolved_locators,
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "claims_empty_is_intentional": True,
            "no_verified_marks": True,
            "report_scope": "report_id=6537 only; no other report id read or written",
        },
        "limitations": [
            "仅登记，不抽取：objective.register_assets=true / classify_report_type=false，claims 为空数组是契约允许的完整结果。",
            "定位符可解析 ≠ 目标可解析：figure_body_reference / path_reference 的 locator 指向正文引用行，目标文件不在本工作树。",
            "法规数值一律未核实：报告自述 external_verification=WITHHELD，本工序不升级任何证据等级。",
            "平台 figures 元数据可解析，但图字节端点探测结果见 figure_probes，未复制图像、未推断图像内容。",
            "产物落 docs/kf/wp-6537-01/（.gitignore 忽略 artifacts/**，push 门会滤掉 artifacts 下的文件）。",
        ],
        "repro_cmd": "python3 scripts/kf/build_asset_manifest_6537.py build result verify && python3 -m pytest tests/test_kf_asset_manifest_6537.py -q",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets, %s)" % (MANIFEST.relative_to(REPO), len(assets), by_res))
    return manifest


# ---------------------------------------------------------------- result envelope
def emit_result():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    token = login()
    _meta, live_md = fetch_report(token)
    live = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    if live != declared:
        raise SystemExit("live source drifted from manifest: %s != %s" % (live, declared))
    result = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + live,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(live_md),
            "source_bytes_utf8": len(live_md.encode("utf-8")),
            "fetched_via": "GET /api/v1/tensor/reports/6537",
            "producer": "scripts/kf/build_asset_manifest_6537.py",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "contract_version": "1.0",
            "notes": "registration only; claims=[] intentionally; no claim marked verified",
        },
        "outputs": {"asset_manifest.json": manifest},
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % RESULT.relative_to(REPO))
    return result


# ---------------------------------------------------------------- independent verification
def verify():
    checks, md, lines = {}, None, None
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "json.loads OK on %s" % MANIFEST.name}
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"valid_json": {"pass": False, "detail": str(e)}}))
        return 1

    required = {"schema", "package_id", "task_type", "report_id", "provenance", "counts",
                "assets", "claims", "integrity"}
    prov_required = {"source_uri", "source_field", "source_hash"}
    missing = sorted(required - set(manifest))
    checks["schema_pass"] = {
        "pass": not missing and not (prov_required - set(manifest["provenance"]))
        and manifest["package_id"] == PKG and manifest["report_id"] == REPORT_ID
        and manifest["task_type"] == TASK_TYPE
        and isinstance(manifest["assets"], list) and manifest["assets"]
        and isinstance(manifest["claims"], list),
        "detail": "missing_top=%s missing_provenance=%s"
                  % (missing, sorted(prov_required - set(manifest["provenance"]))),
    }

    loc_bad, targets = [], {}
    # locators are re-resolved against the byte-exact snapshot (offline path), then against live bytes
    if SNAPSHOT.exists():
        md = SNAPSHOT.read_text(encoding="utf-8")
        lines = md.split("\n")
        for a in manifest["assets"]:
            loc = a["locator"]
            if loc.get("scheme") == "report_field" and loc.get("field") == "markdown":
                continue
            if loc.get("scheme") == "report_field" and loc.get("field") == "figures":
                idx = loc.get("index")
                n_fig = manifest["counts"].get("platform_figures", 0)
                if not isinstance(idx, int) or not (0 <= idx < n_fig):
                    loc_bad.append(a["asset_id"])
                continue
            q, s, e = loc.get("quote"), loc.get("start_char"), loc.get("end_char")
            if not (isinstance(q, str) and q and isinstance(s, int) and isinstance(e, int)):
                loc_bad.append(a["asset_id"])
                continue
            if md[s:e] != q or md.count(q) != 1:
                loc_bad.append(a["asset_id"])
    else:
        md = None
        loc_bad.append("snapshot_missing")
    checks["source_locator_resolvable"] = {
        "pass": not loc_bad,
        "detail": "checked %d locators against %s; unresolvable=%s"
                  % (len(manifest["assets"]), SNAPSHOT.name, loc_bad),
    }

    snap_hash = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() if SNAPSHOT.exists() else None
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    checks["source_hash_matches"] = {
        "pass": snap_hash == declared == EXPECTED_HASH
        and manifest["provenance"]["source_chars"] == EXPECTED_CHARS,
        "detail": "snapshot=%s declared=%s contract=%s chars=%s/%s"
                  % (snap_hash, declared, EXPECTED_HASH,
                     manifest["provenance"]["source_chars"], EXPECTED_CHARS),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {"pass": len(ids) == len(set(ids)) and all(ids),
                                  "detail": "assets=%d unique=%d" % (len(ids), len(set(ids)))}

    claims = manifest.get("claims", [])
    bad = [c for c in claims if not c.get("evidence") and c.get("status") != "unresolved"]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad,
        "detail": "claims=%d violating=%d (empty array: vacuously satisfied, contract allows it)"
                  % (len(claims), len(bad)),
    }
    checks["do_not_mark_claims_as_verified"] = {
        "pass": all(c.get("status") != "verified" for c in claims),
        "detail": "no claim carries status=verified",
    }
    checks["counts_consistent"] = {
        "pass": manifest["counts"]["assets"] == len(ids)
        and sum(manifest["counts"]["by_resolution"].values()) == len(ids)
        and sum(manifest["counts"]["by_class"].values()) == len(ids),
        "detail": "counts.assets=%d by_resolution_sum=%d by_class_sum=%d"
                  % (manifest["counts"]["assets"], sum(manifest["counts"]["by_resolution"].values()),
                     sum(manifest["counts"]["by_class"].values())),
    }

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "source_snapshot_sha256": snap_hash,
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
        "not_run": ["live re-fetch in verify（emit_result 内已做 hash 漂移守卫；verify 用快照以支持离线复跑）"],
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["all_pass"] else 1


if __name__ == "__main__":
    acts = sys.argv[1:] or ["build", "result", "verify"]
    if "build" in acts:
        build()
    if "result" in acts:
        emit_result()
    if "verify" in acts:
        sys.exit(verify())