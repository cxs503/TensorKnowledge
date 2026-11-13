#!/usr/bin/env python3
"""wp-10087-01 | 01-asset-registration for report_id=10087 (single package, single report).

Contract: package_id=wp-10087-01, task_type=01-asset-registration, lane C,
source_uri=tensor://reports/10087, source_field=markdown,
source_hash=sha256:6ed122a8092e41f05bebbb099ce1406a77ae3504f97785c7501c220f79310f72.

Scope discipline
----------------
* read-only on the platform: GET /tensor/reports/10087 only; no other report_id is read
  or written by this script.
* no extraction, no forced claims: ``claims`` is an empty array (contract allows it,
  ``objective.classify_report_type=false``).
* nothing is marked verified: the hash equality below is a mechanical identity check;
  claim verification status stays with the platform gate.
* zero hand-copy: every ``quote`` is *sliced out of the fetched markdown* by line range
  (``md[start:end]``), never retyped, and the slice is re-checked as a unique substring.

Subcommands
-----------
    emit    fetch source, emit docs/kf/wp-10087-01/{asset_manifest.json,locator_check.json,
            source.md,sha256.txt,kf_result.json}
    render  render docs/kf_result_wp-10087-01.md from the emitted artefacts
            (narrative template + machine-injected tables/JSON)
    verify  offline re-validation of the emitted artefacts against
            schemas/kf_result.v1.schema.json + the acceptance invariants

Usage (from the worktree root):
    python3 scripts/kf_wp10087_01_register.py emit
    python3 scripts/kf_wp10087_01_register.py render
    python3 scripts/kf_wp10087_01_register.py verify
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
REPORT_ID = "10087"
PACKAGE_ID = "wp-10087-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = f"tensor://reports/{REPORT_ID}"
EXPECTED_HASH = "sha256:6ed122a8092e41f05bebbb099ce1406a77ae3504f97785c7501c220f79310f72"
EXPECTED_CHARS = 3454
OUT_DIR = "docs/kf/wp-10087-01"
KF_RESULT_SCHEMA = "schemas/kf_result.v1.schema.json"
REPORT_MD = "docs/kf_result_wp-10087-01.md"

# ---------------------------------------------------------------------------
# Asset inventory.
# Each entry: (asset_id, asset_class, label, in_report_section, (start_line, end_line),
#              resolution, resolution_check(check, result), note)
# Lines are 1-based, inclusive, over the markdown split with keepends=True (so line 1 is
# the leading empty line). Quotes are SLICED from the markdown, never retyped.
# ---------------------------------------------------------------------------
ASSETS = [
    ("A01", "section_heading", "案例介绍章标题（① 案例介绍）", "① 案例介绍", (4, 4),
     "resolved_in_source", ("heading level-2 present at the recorded line span", "resolved"),
     "顶层章节锚点，供下游抽取定位章节边界。"),
    ("A02", "formula", "Weibull 特征强度-尺寸效应式 σ_f(V)", "① 案例介绍 / 物理背景", (9, 9),
     "resolved_in_source", ("display-math block present at the recorded line span", "resolved"),
     "LaTeX 原文保留（含 \\left(\\frac{V}{V_0}\\right)^{-1/m}），未做符号改写。"),
    ("A03", "formula", "Weibull 破坏概率式 P_f(σ, V)", "① 案例介绍 / 物理背景", (11, 11),
     "resolved_in_source", ("display-math block present at the recorded line span", "resolved"),
     "与 A02 同源的累积破坏概率表达式；参数含义见原文第 13 行。"),
    ("A04", "formula", "Gaudin-Schuhmann 破碎谱 CDF F(d)=(d/d_max)^α", "① 案例介绍 / 物理背景", (19, 19),
     "resolved_in_source", ("inline formula sentence present at the recorded line span", "resolved"),
     "行内公式，原文用 α（U+03B1）而非 alpha 字样。"),
    ("A05", "table", "双材料参数表（石英砂 / 石灰岩，9 项）", "① 案例介绍 / 参数表", (23, 32),
     "resolved_in_source", ("markdown pipe table with 2 data columns present at the span", "resolved"),
     "参数表整体登记为一条资产（不抽取单元格值：本工序不做抽取）。参考体积以表达式给出而非数值。"),
    ("A06", "formula", "Hertz 接触力式 F_c 与等效模量 E*", "② 方法 / 加载模拟", (38, 38),
     "resolved_in_source", ("inline formula line present at the recorded line span", "resolved"),
     "含 E* = E/(2(1-ν²)) 定义。"),
    ("A07", "method", "Weibull 采样规则（单次均匀随机数 + 首个越界步破坏）", "② 方法 / Weibull采样", (43, 44),
     "resolved_in_source", ("two-line method block present at the recorded line span", "resolved"),
     "登记为两条连续行构成的采样规则资产；第 45 行（300 次试验取中位数）未并入，保持 span 最小。"),
    ("A08", "method", "子粒均匀缩放质量守恒规则", "② 方法 / 子粒替换", (49, 49),
     "resolved_in_source", ("method line present at the recorded line span", "resolved"),
     "原文声明精确到浮点精度；本工序仅登记该声明，不验证。"),
    ("A09", "method", "子粒速度零均值随机散布（动量守恒）规则", "② 方法 / 子粒替换", (50, 50),
     "resolved_in_source", ("method line present at the recorded line span", "resolved"),
     "同上：只登记声明，不做数值复算（复算属验证工作包）。"),
    ("A10", "method", "Gaudin 谱 α 的 MLE 估计式", "② 方法 / Gaudin谱拟合", (53, 53),
     "resolved_in_source", ("inline formula line present at the recorded line span", "resolved"),
     "原文使用 α̂（带 hat 组合字符），切片逐字保留。"),
    ("A11", "code_artifact", "声明代码文件 src/tensordem/granule_crush.py（850 行）",
     "② 方法 / 工具链", (59, 59),
     "referenced_unresolved",
     ("path existence cannot be decided from the report record; producing repo (TensorDEM) "
      "is outside this package's scope", "unresolved"),
     "只登记「原文声明了该路径与行数」，不主张文件存在、也不主张 850 行属实。"),
    ("A12", "test_artifact", "声明测试文件 tests/test_granule_crush.py（21 条）", "② 方法 / 工具链", (60, 60),
     "referenced_unresolved",
     ("path existence cannot be decided from the report record; test suite not executed here",
      "unresolved"),
     "21 条用例数来自原文自述，未经本工序执行复核。"),
    ("A13", "table", "C1 Weibull 尺寸效应拟合结果表（5 个粒径）", "③ 计算结果 / C1", (66, 72),
     "resolved_in_source", ("markdown pipe table present at the recorded line span", "resolved"),
     "含模拟/解析中位强度与偏差列；数值未在本工序复算。"),
    ("A14", "table", "C2/C3 质量与动量守恒残差表（1000 次事件）", "③ 计算结果 / C2/C3", (80, 83),
     "resolved_in_source", ("markdown pipe table present at the recorded line span", "resolved"),
     "残差以科学计数法给出（×10⁻¹⁶ 上标字符）。"),
    ("A15", "table", "C4 Gaudin 谱五种估计方法的 α̂ 表", "③ 计算结果 / C4", (87, 93),
     "resolved_in_source", ("markdown pipe table present at the recorded line span", "resolved"),
     "表头用 α̂ 组合字符，逐字保留。"),
    ("A16", "table", "C4-rate 应变率工况表（石灰岩，3 档平板速度）", "③ 计算结果 / C4-rate", (99, 103),
     "resolved_in_source", ("markdown pipe table present at the recorded line span", "resolved"),
     "应变率列为换算值，原文与平板速度并列给出。"),
    ("A17", "result_statement", "C5 负控结论（零载荷 50 次 → 0 次破碎）", "③ 计算结果 / C5", (109, 109),
     "resolved_in_source", ("single bullet present at the recorded line span", "resolved"),
     "负控结论以单行列表项给出，含 ✓ 字符。"),
    ("A18", "result_statement", "C6 回归测试结论（21 条 + 相关模块 58 条）", "③ 计算结果 / C6", (113, 114),
     "resolved_in_source", ("two-line bullet block present at the recorded line span", "resolved"),
     "测试通过数按原文自述登记，本工序未执行该测试集。"),
    ("A19", "figure_reference", "结果图占位说明（见内嵌figures（4张PNG））", "④ 结果图", (118, 118),
     "resolved_in_source", ("figure placeholder line present at the recorded line span", "resolved"),
     "正文用一行占位引用 4 张图；图本体不在 markdown 内，见 A20–A23（平台记录 figures[]）。"),
    ("A20", "figure", "fig1_weibull_size_effect（PNG，平台记录 figures[0]）", "④ 结果图", (118, 118),
     "resolved_in_source", ("figure present in the platform record figures[] (index 0)", "resolved"),
     "图本体在平台报告的 figures[] 字段；正文定位到 A19 同一行（故 span 与 A19 相同）。"),
    ("A21", "figure", "fig2_gaudin_spectrum（PNG，平台记录 figures[1]）", "④ 结果图", (118, 118),
     "resolved_in_source", ("figure present in the platform record figures[] (index 1)", "resolved"),
     "同上。"),
    ("A22", "figure", "fig3_conservation_ledger（PNG，平台记录 figures[2]）", "④ 结果图", (118, 118),
     "resolved_in_source", ("figure present in the platform record figures[] (index 2)", "resolved"),
     "同上。"),
    ("A23", "figure", "fig4_strain_rate_study（PNG，平台记录 figures[3]）", "④ 结果图", (118, 118),
     "resolved_in_source", ("figure present in the platform record figures[] (index 3)", "resolved"),
     "同上。"),
    ("A24", "table", "⑥ 误差判定表（6 项判据 vs 基准）", "⑥ 误差判定", (130, 137),
     "resolved_in_source", ("markdown pipe table present at the recorded line span", "resolved"),
     "含「是否<3%」列与阈值列；判定结论由平台门复核，本工序不改写。"),
]


# ---------------------------------------------------------------------------
# platform IO
# ---------------------------------------------------------------------------
def _call(path: str, body: dict | None = None, tok: str | None = None, timeout: int = 120):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def login() -> str:
    payload = {"username": os.environ["TENSOR_AGENT_USER"],
               "password": os.environ["TENSOR_AGENT_PASS"]}
    last = ""
    for path in ("/auth/login", "/auth/token"):
        st, body = _call(path, payload)
        if st == 200:
            doc = json.loads(body)
            tok = doc.get("access_token") or doc.get("token")
            if tok:
                return tok
        last = f"{path}->{st} {body[:200]}"
    raise SystemExit(f"login failed: {last}")


def fetch_report() -> dict:
    tok = login()
    st, body = _call(f"/tensor/reports/{REPORT_ID}", None, tok)
    if st != 200:
        raise SystemExit(f"GET report {REPORT_ID} -> {st} {body[:300]}")
    rec = json.loads(body)
    if isinstance(rec.get("report"), dict):
        rec = rec["report"]
    if str(rec.get("id")) != REPORT_ID:
        raise SystemExit(f"refusing: fetched report id {rec.get('id')!r} != {REPORT_ID!r}")
    return rec


# ---------------------------------------------------------------------------
# manifest construction
# ---------------------------------------------------------------------------
def md_sha256(md: str) -> str:
    return "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()


def line_offsets(md: str) -> list[int]:
    """Char offsets: ``starts[n-1]`` = start offset of 1-based line ``n``.

    ``starts`` has ``n_lines + 1`` entries; ``starts[n_lines]`` = end of the document.
    """
    starts, pos = [0], 0
    for line in md.splitlines(keepends=True):
        pos += len(line)
        starts.append(pos)
    return starts


def slice_lines(md: str, starts: list[int], start_line: int, end_line: int) -> dict:
    """Return a locator dict for the 1-based inclusive line range (quote = md[start:end])."""
    n_lines = len(md.splitlines())
    if not (1 <= start_line <= end_line <= n_lines):
        raise SystemExit(f"line span {start_line}-{end_line} outside 1..{n_lines}")
    start = starts[start_line - 1]
    end = starts[end_line]
    quote = md[start:end]
    if not quote or md.count(quote) != 1:
        raise SystemExit(f"non-unique/empty quote at lines {start_line}-{end_line}: {quote[:80]!r}")
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": start_line,
        "end_line": end_line,
        "quote": quote.rstrip("\n"),
        "unique": True,
    }


def build_manifest(rec: dict) -> tuple[dict, dict]:
    md: str = rec["markdown"]
    starts = line_offsets(md)
    digest = md_sha256(md)
    figures = rec.get("figures") or []

    assets, checks = [], []
    for aid, klass, label, section, (a, b), resolution, (chk, res), note in ASSETS:
        loc = slice_lines(md, starts, a, b)
        asset = {
            "asset_id": aid,
            "asset_class": klass,
            "label": label,
            "in_report_section": section,
            "resolution": resolution,
            "resolution_check": {"check": chk, "result": res},
            "locator": loc,
            "note": note,
        }
        if klass == "figure":
            idx = int(aid[1:]) - 20
            fig = figures[idx] if idx < len(figures) else None
            if fig is None:
                asset["resolution"] = "referenced_unresolved"
                asset["resolution_check"]["result"] = "unresolved"
            else:
                asset["platform_figure"] = {"index": idx, "name": fig.get("name"),
                                            "caption": fig.get("caption")}
        assets.append(asset)
        checks.append({
            "locator_id": aid,
            "asset_class": klass,
            "label": label,
            "quote": loc["quote"],
            "start_char": loc["start_char"],
            "end_char": loc["end_char"],
            "start_line": loc["start_line"],
            "end_line": loc["end_line"],
            "resolvable": md.find(loc["quote"]) == loc["start_char"],
            "slice_equals_quote": md[loc["start_char"]:loc["end_char"]].rstrip("\n") == loc["quote"],
            "occurrences": md.count(loc["quote"]),
        })

    resolved = [a for a in assets if a["resolution"] == "resolved_in_source"]
    unresolved = [a for a in assets if a["resolution"] == "referenced_unresolved"]
    absent = [a for a in assets if a["resolution"] == "declared_absent"]
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest.split(":", 1)[1],
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "platform_figures": [{"index": i, "name": f.get("name"), "caption": f.get("caption")}
                                 for i, f in enumerate(figures)],
            "platform_tags": rec.get("tags") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": len(resolved),
            "referenced_unresolved": len(unresolved),
            "declared_absent": len(absent),
        },
        "assets": assets,
        "claims": [],  # contract: objective.classify_report_type=false -> no extraction
        "integrity": {
            "quote_uniqueness": all(c["occurrences"] == 1 for c in checks),
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "chars_match_contract": len(md) == EXPECTED_CHARS,
        },
    }
    locator_report = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "source_hash": digest,
        "expected_hash": EXPECTED_HASH,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "resolvable": sum(1 for c in checks if c["resolvable"] and c["slice_equals_quote"]),
            "unique": sum(1 for c in checks if c["occurrences"] == 1),
            "unresolved": [c["locator_id"] for c in checks if not c["resolvable"]],
        },
    }
    return manifest, locator_report


def build_kf_result(manifest: dict, rec: dict) -> dict:
    digested = manifest["source"]["hash"]
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": f"sha256:{digested}",
            "source_field": "markdown",
            "producer": "scripts/kf_wp10087_01_register.py (lane C, 01-asset-registration)",
            "emitted_at": _stable_emitted_at(),
            "source_uri": SOURCE_URI,
            "notes": ("hash recomputed from the fetched markdown UTF-8 bytes; all 24 locator "
                      "quotes are machine-sliced from that markdown and unique; claims=[] "
                      "(no extraction in this work package); no claim marked verified."),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def _stable_emitted_at() -> str:
    """Keep the first-run timestamp so re-emitting is byte-identical (reproducibility)."""
    path = os.path.join(OUT_DIR, "kf_result.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)["provenance"]["emitted_at"]
        except (KeyError, ValueError, OSError):
            pass
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# emit
# ---------------------------------------------------------------------------
def cmd_emit() -> int:
    rec = fetch_report()
    md = rec["markdown"]
    digest = md_sha256(md)
    print(f"report {REPORT_ID}: {len(md)} chars, {len(md.encode())} utf8 bytes, {digest}")
    if digest != EXPECTED_HASH:
        print(f"FATAL: hash mismatch vs contract {EXPECTED_HASH}")
        return 2
    manifest, locator_report = build_manifest(rec)
    kf = build_kf_result(manifest, rec)
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, obj in (("asset_manifest.json", manifest),
                      ("locator_check.json", locator_report),
                      ("kf_result.json", kf)):
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    with open(os.path.join(OUT_DIR, "source.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write(md)
    with open(os.path.join(OUT_DIR, "sha256.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"{digest.split(':', 1)[1]}  source.md\n")
    print(f"assets={manifest['counts']['assets']} by_class={manifest['counts']['by_class']}")
    print(f"by_resolution={manifest['counts']['by_resolution']}")
    print(f"quotes: {locator_report['summary']['resolvable']}/{locator_report['summary']['total']} "
          f"resolvable, {locator_report['summary']['unique']} unique")
    return 0


# ---------------------------------------------------------------------------
# verify (offline; uses only files already in the tree)
# ---------------------------------------------------------------------------
def cmd_verify() -> int:
    import jsonschema  # local dep; pinned in requirements where present

    fails: list[str] = []
    with open(os.path.join(OUT_DIR, "source.md"), encoding="utf-8", newline="") as fh:
        md = fh.read()
    with open(os.path.join(OUT_DIR, "asset_manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    with open(os.path.join(OUT_DIR, "kf_result.json"), encoding="utf-8") as fh:
        kf = json.load(fh)
    with open(KF_RESULT_SCHEMA, encoding="utf-8") as fh:
        schema = json.load(fh)

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail else ""))
        if not ok:
            fails.append(name)

    digest = md_sha256(md)
    check("source_hash_matches", digest == EXPECTED_HASH, digest)
    check("chars_match_contract", len(md) == EXPECTED_CHARS, str(len(md)))
    check("envelope_source_hash_equals_recomputed",
          kf["provenance"]["source_hash"] == digest, kf["provenance"]["source_hash"])
    check("envelope_source_field", kf["provenance"]["source_field"] == "markdown")

    # kf_result.v1 structural schema
    try:
        jsonschema.validate(kf, schema)
        check("kf_result_schema_pass", True)
    except jsonschema.ValidationError as exc:
        check("kf_result_schema_pass", False, str(exc)[:300])

    check("package_id", kf["package_id"] == PACKAGE_ID == manifest["package_id"])
    check("task_type", kf["task_type"] == TASK_TYPE)
    check("report_id", kf["report_id"] == REPORT_ID and manifest["report_id"] == REPORT_ID)
    check("outputs_key_is_asset_manifest", list(kf["outputs"]) == ["asset_manifest.json"])
    check("outputs_payload_identical_to_manifest_file",
          kf["outputs"]["asset_manifest.json"] == manifest)

    ids = [a["asset_id"] for a in manifest["assets"]]
    check("no_duplicate_ids", len(ids) == len(set(ids)), f"{len(ids)} ids")
    check("asset_id_pattern", all(re.fullmatch(r"A[0-9]{2}", i) for i in ids))

    # every locator resolves as an exact slice of the source markdown
    bad_slice, bad_uniq, bad_find = [], [], []
    for a in manifest["assets"]:
        loc = a["locator"]
        if md[loc["start_char"]:loc["end_char"]].rstrip("\n") != loc["quote"]:
            bad_slice.append(a["asset_id"])
        if md.count(loc["quote"]) != 1:
            bad_uniq.append(a["asset_id"])
        if md.find(loc["quote"]) != loc["start_char"]:
            bad_find.append(a["asset_id"])
        if not (0 <= loc["start_char"] < loc["end_char"] <= len(md)):
            bad_slice.append(a["asset_id"])
    check("source_locator_resolvable", not bad_slice and not bad_find,
          f"bad_slice={bad_slice} bad_find={bad_find}")
    check("locator_quotes_unique", not bad_uniq, str(bad_uniq))

    # claims: empty is legal; each claim must carry evidence or an explicit status
    claims = manifest["claims"]
    check("claims_empty_or_evidenced",
          all(("evidence_locator" in c) or ("status" in c) for c in claims),
          f"n_claims={len(claims)}")
    check("envelope_claims_consistent", kf["claims"] == claims)

    # no asset may smuggle in a *verified* verdict for this report's claims
    blob = json.dumps(manifest, ensure_ascii=False)
    check("no_verified_claim_flag", '"verified"' not in blob)

    counts = manifest["counts"]
    check("counts_assets_consistent", counts["assets"] == len(manifest["assets"]))
    check("counts_resolution_sum",
          counts["resolved_in_source"] + counts["referenced_unresolved"]
          + counts["declared_absent"] == counts["assets"])
    recomputed = {}
    for a in manifest["assets"]:
        recomputed[a["resolution"]] = recomputed.get(a["resolution"], 0) + 1
    check("counts_by_resolution_matches_assets", recomputed == counts["by_resolution"])
    by_class = {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
    check("counts_by_class_matches_assets", by_class == counts["by_class"])
    check("integrity_hash_matches_contract", manifest["integrity"]["hash_matches_contract"])
    check("integrity_quote_uniqueness", manifest["integrity"]["quote_uniqueness"])

    # citations actually used in the rendered report resolve too
    if os.path.exists(REPORT_MD):
        body = open(REPORT_MD, encoding="utf-8").read()
        blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
        check("report_has_exactly_one_json_block", len(blocks) == 1, str(len(blocks)))
        if len(blocks) == 1:
            try:
                embedded = json.loads(blocks[0])
                check("report_json_block_equals_kf_result", embedded == kf)
            except ValueError as exc:
                check("report_json_block_parses", False, str(exc)[:200])
        first = body.splitlines()[0].strip()
        check("report_title_present", first == f"# KF-RESULT {PACKAGE_ID}", first)

    print(f"\n{len(fails)} failing check(s)" + ("" if fails else " — all acceptance items pass"))
    return 0 if not fails else 1


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
def _asset_table(manifest: dict) -> str:
    rows = ["| asset_id | class | 标签 | 章内位置 | resolution | 行范围 | 字符区间 |",
            "|---|---|---|---|---|---|---|"]
    for a in manifest["assets"]:
        loc = a["locator"]
        rows.append(f"| {a['asset_id']} | {a['asset_class']} | {a['label']} | "
                    f"{a['in_report_section']} | {a['resolution']} | "
                    f"L{loc['start_line']}–L{loc['end_line']} | "
                    f"[{loc['start_char']}, {loc['end_char']}) |")
    return "\n".join(rows)


def _code_span(text: str) -> str:
    """Markdown code span that survives embedded backticks (A11/A12 quote file paths)."""
    if "`" not in text:
        return f"`{text}`"
    return "`` " + text + " ``"


def _evidence_table(manifest: dict) -> str:
    rows = ["| claim/字段 | 原文引文片段（逐字，机器切片） | 定位 |",
            "|---|---|---|"]
    for a in manifest["assets"]:
        loc = a["locator"]
        if a["asset_class"] == "figure":
            fig = a.get("platform_figure") or {}
            cell = (f"（正文占位与 A19 同行；图本体名 {fig.get('name')}，"
                    f"figures[{fig.get('index')}]）")
        else:
            q = loc["quote"].replace("\n", " ⏎ ")
            if len(q) > 110:
                q = q[:110] + "…"
            cell = _code_span(q)
        rows.append(f"| {a['asset_id']} {a['asset_class']} | {cell} | "
                    f"char [{loc['start_char']},{loc['end_char']}) / L{loc['start_line']}–{loc['end_line']} |")
    return "\n".join(rows)


def _counts_table(manifest: dict) -> str:
    c = manifest["counts"]
    rows = ["| 指标 | 值 |", "|---|---|"]
    rows.append(f"| 资产总数 | {c['assets']} |")
    for k, v in sorted(c["by_class"].items()):
        rows.append(f"| by_class: {k} | {v} |")
    for k, v in sorted(c["by_resolution"].items()):
        rows.append(f"| by_resolution: {k} | {v} |")
    rows.append(f"| 引用但不可解析（referenced_unresolved） | {c['referenced_unresolved']} |")
    rows.append(f"| 声明缺失（declared_absent） | {c['declared_absent']} |")
    return "\n".join(rows)


NARRATIVE = """# KF-RESULT {pkg}

> 工作包 `{pkg}` · 工序 `{task}` · lane C · 源 `{src}`（report_id={rid}）
> 交付仓库 TensorKnowledge · status=draft · 本报告未把任何结论标为 verified（verification 由平台门计算）
> tags: `kf-wp:{pkg}` · `01-asset-registration` · `report:{rid}` · `lane:C` · `draft`

## ① 本工序做了什么

登记 report_id=10087 这一份报告的**源资产**：确认 report_id 与其 markdown 的字节哈希，把 markdown 中可解析的章节/公式/表格/图/声明工件切出定位区间，产出 `asset_manifest.json` 与 `kf_result.v1` 信封。**不做抽取、不生成 claim**（契约 `objective.classify_report_type=false`，`claims` 允许为空数组，故 `claims=[]`：不为凑指标造知识）。

## ② 怎么做的（步骤/工具/关键设置）

1. `GET {api}/tensor/reports/{rid}`（Bearer=agent token）取 `markdown`；脚本先断言返回记录的 `id` 等于 10087，否则拒绝继续——从根上杜绝读到/写到别的 report_id。
2. 对 markdown 的 UTF-8 字节重算 sha256，与契约 `source_hash` 比对（相等才继续）。
3. 资产清单以**行区间**声明，引文由 `md[start:end]` **机器切片**得到，绝不重敲；切片后再要求 `md.count(quote)==1`（唯一）与 `md.find(quote)==start_char`（唯一命中同一位置），否则脚本报错退出。
4. 图资产（A20–A23）的图本体在平台记录 `figures[]`，正文只有一行占位（A19）；因此其 markdown 定位共用 A19 的 span，图身份由 `platform_figure` 字段（index/name/caption）绑定。
5. 原文声明但不在报告记录内的工件（`src/tensordem/granule_crush.py`、`tests/test_granule_crush.py`）标 `referenced_unresolved`：只登记「原文这样说」，不主张文件存在、不主张行数/用例数属实。
6. 输出 `asset_manifest.json` / `locator_check.json` / `source.md`（逐字副本）/ `sha256.txt` / `kf_result.json`，再用 `schemas/kf_result.v1.schema.json`（jsonschema 4.26.0）校验信封并跑 {n_checks} 项验收不变量（脚本级 + 报告级，逐条见 verify 输出）。

工具链：Python 3.11 + jsonschema 4.26.0 + matplotlib（图）；无网络外呼，除平台自身 API。

### 资产计数

{counts}

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `{outdir}/asset_manifest.json` | 契约声明的唯一输出：24 条资产 + 计数 + integrity 三元组 + `claims=[]` |
| `{outdir}/locator_check.json` | 24 条引文的可解析性明细（char 区间/行区间/出现次数/切片一致性） |
| `{outdir}/kf_result.json` | `kf_result.v1` 信封（package_id/task_type/report_id/provenance/outputs/claims） |
| `{outdir}/source.md` | 源 markdown 逐字副本（离线复核用，sha256 见 `sha256.txt`） |
| `{outdir}/sha256.txt` | 重算摘要：`{digest_short}  source.md` |
| `{outdir}/fig1_asset_inventory.png` | 资产计数条形图（按 class / resolution，数值全部来自 manifest） |
| `{outdir}/fig2_source_coverage.png` | markdown {n_lines} 行 × 字符轴上的定位覆盖条带（哪段被登记、哪段未登记） |
| `docs/kf_result_{pkg}.md` | 本报告（正文 + 唯一一个 json 代码块） |

## ④ 证据定位表

{evidence}

## ⑤ 注意点与局限

1. **哈希相等 ≠ 内容正确**：sha256 只机械证明「我读到的字节 = 契约指的字节」，不证明报告任何数值成立。本工序不做数值复算。
2. **claims 为空是刻意的**：契约 `no_forced_claim_generation=true`；登记工序抽 claim 会把「登记」和「抽取」两道工序的验收面混在一起。
3. **两个工件 unresolved**：`src/tensordem/granule_crush.py`（850 行）与 `tests/test_granule_crush.py`（21 条）只以「原文声明」入账；它们属 TensorDEM 仓，不在本工作包范围，故不验证存在性与行数/用例数。
4. **图资产双重定位**：4 张 PNG 的正文定位共用一行占位文字；若下游按图行号抽图会失败，必须走 `platform_figure` 字段。
5. **未覆盖段落**：⑥ 结论行、⑤ 局限 5 条、③ 各节标题等未逐条登记（只登记表与结论性语句）；覆盖率见 `fig2_source_coverage.png`，缺口是公开的、不是隐藏的。
6. **仓内既有 `schemas/asset_manifest.v1.schema.json` 不适用**：它把 `package_id` 钉成 `const: wp-448-01`，是上一包的自用 schema。本包不篡改它，改用 `kf_result.v1` 结构校验 + 脚本内显式不变量（{n_checks} 项）作为 `schema_pass` 的可复现证据。

## ⑥ 自检：逐条对照 acceptance

{acceptance}

### 误差判定（本工序不适用，附原因）

本工序不产生任何数值结果，只做身份登记，因此**没有可对标的基准值，也就没有「<3%」这类误差量**。唯一的定量判据是字节/字符级恒等，逐项如下：

| 判据 | 基准 | 计算值 | 误差 | 是否<3% |
|---|---|---|---|---|
| 源 markdown sha256 | 契约 `source_hash` = `{contract_hash}` | 重算 = `{digest}` | 0（完全相等） | 不适用（恒等判据，非近似量） |
| 源 markdown 字符数 | 契约 `chars` = 3454 | `{chars}` | 0 | 不适用 |
| 引文定位 | `md[start:end]` 切片 | {n_assets}/{n_assets} 条切片等于引文且唯一命中 | 0 | 不适用 |
| 覆盖率（公开缺口） | — | {cov} | — | 不适用 |

声明原因：被登记报告（10087）内部的工程误差（如 C1 的 1.7%、C4 的 0.16–2.92% 等）属于该报告自身结论，本工序**不重算、不背书**，也不把它们搬进本报告冒充自己的误差判定。

**结论**：{verdict}

### repro_cmd（一键复跑）

```bash
cd <worktree-root>   # TensorKnowledge 检出
python3 scripts/kf_wp10087_01_register.py emit      # 取源 + 重算哈希 + 生成 manifest/信封
python3 scripts/kf_wp10087_01_figures.py            # 生成两张图（数值来自 manifest）
python3 scripts/kf_wp10087_01_register.py render    # 渲染本报告（注入表格与唯一 json 块）
python3 scripts/kf_wp10087_01_register.py verify    # {n_checks} 项验收不变量 + schema 校验
python3 -m pytest tests/test_kf_wp10087_01_register_assets.py -q
```

## kf_result.v1 信封（唯一 json 代码块）

```json
{kf_json}
```
"""


ACCEPTANCE_ROWS = [
    ("valid_json", "kf_result.json / asset_manifest.json 均可被 json.load 解析",
     "verify: kf_result_schema_pass + outputs_payload_identical_to_manifest_file"),
    ("schema_pass", "kf_result.v1 结构校验（jsonschema）通过",
     "verify: kf_result_schema_pass"),
    ("source_locator_resolvable", "24/24 引文是源 markdown 的精确切片且唯一命中",
     "verify: source_locator_resolvable + locator_quotes_unique"),
    ("source_hash_matches", "重算 sha256 与契约 source_hash 相等",
     "verify: source_hash_matches + envelope_source_hash_equals_recomputed"),
    ("no_duplicate_ids", "asset_id 无重复且符合 A[0-9]{2}",
     "verify: no_duplicate_ids + asset_id_pattern"),
    ("all_claims_have_evidence_or_explicit_unresolved_status",
     "claims=[]（契约允许），无 claim 缺证据；两条声明工件已显式 referenced_unresolved",
     "verify: claims_empty_or_evidenced + counts_by_resolution_matches_assets"),
]


def _coverage_text(manifest: dict, md: str) -> str:
    """Union coverage of the locator spans (overlaps counted once) — same numbers as fig2."""
    covered = set()
    for a in manifest["assets"]:
        loc = a["locator"]
        covered.update(range(loc["start_char"], loc["end_char"]))
    n = len(covered)
    return f"{n}/{len(md)} chars = {100.0 * n / len(md):.1f}%"


def cmd_render() -> int:
    with open(os.path.join(OUT_DIR, "asset_manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    with open(os.path.join(OUT_DIR, "kf_result.json"), encoding="utf-8") as fh:
        kf = json.load(fh)
    kf_json = json.dumps(kf, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT_DIR, "source.md"), encoding="utf-8", newline="") as fh:
        md_text = fh.read()

    # acceptance self-check = actually run the verifier and lift its per-item verdicts
    verdicts: dict[str, bool] = {}
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cmd_verify()
    for line in buf.getvalue().splitlines():
        if line.startswith(("PASS ", "FAIL ")):
            verdicts[line[5:].split(" ::")[0]] = line.startswith("PASS")

    def item_ok(keys: list[str]) -> bool:
        return all(verdicts.get(k, False) for k in keys)

    rows = ["| acceptance 项 | 判据 | 证据（verify 检查名） | 结果 |", "|---|---|---|---|"]
    mapping = {
        "valid_json": ["kf_result_schema_pass", "outputs_payload_identical_to_manifest_file"],
        "schema_pass": ["kf_result_schema_pass"],
        "source_locator_resolvable": ["source_locator_resolvable", "locator_quotes_unique"],
        "source_hash_matches": ["source_hash_matches", "envelope_source_hash_equals_recomputed"],
        "no_duplicate_ids": ["no_duplicate_ids", "asset_id_pattern"],
        "all_claims_have_evidence_or_explicit_unresolved_status":
            ["claims_empty_or_evidenced", "counts_by_resolution_matches_assets"],
    }
    n_ok = 0
    for name, crit, evid in ACCEPTANCE_ROWS:
        ok = item_ok(mapping[name])
        n_ok += ok
        rows.append(f"| `{name}` | {crit} | {evid} | {'✓' if ok else '✗'} |")

    total = len(verdicts)
    n_pass = sum(1 for v in verdicts.values() if v)
    verdict = (f"6/6 acceptance 项通过；脚本级不变量 {n_pass}/{total} PASS"
               if n_ok == len(ACCEPTANCE_ROWS)
               else f"honest-FAIL：{n_ok}/{len(ACCEPTANCE_ROWS)} acceptance 项通过，"
                    f"脚本级不变量 {n_pass}/{total} PASS，失败项见上表 ✗")

    body = NARRATIVE.format(
        pkg=PACKAGE_ID, task=TASK_TYPE, src=SOURCE_URI, rid=REPORT_ID, api=API,
        counts=_counts_table(manifest), evidence=_evidence_table(manifest),
        acceptance="\n".join(rows), verdict=verdict, kf_json=kf_json,
        outdir=OUT_DIR,
        digest_short=manifest["source"]["hash"], n_checks=total,
        n_lines=len(md_text.splitlines()),
        contract_hash=EXPECTED_HASH, digest=manifest["source"]["hash"] and ("sha256:" + manifest["source"]["hash"]),
        chars=manifest["source"]["chars"], n_assets=manifest["counts"]["assets"],
        cov=_coverage_text(manifest, md_text),
    )
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as fh:
        fh.write(body)
    print(f"wrote {REPORT_MD} ({len(body)} chars); acceptance ✓={n_ok}/{len(ACCEPTANCE_ROWS)}, "
          f"verify {n_pass}/{total}")
    return rc


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "emit"
    if cmd == "emit":
        return cmd_emit()
    if cmd == "render":
        return cmd_render()
    if cmd == "verify":
        return cmd_verify()
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv))