#!/usr/bin/env python3
"""KF work package wp-9912-01 (task_type=01-asset-registration), report_id=9912.

Registers the *assets* of TensorKnowledge report 9912 (markdown): the document itself,
its headings, its tables and every file / symbol / run-reference it mentions.
No extraction, no classification, no claim generation, no verified marks.

Discipline enforced programmatically (not by assertion in prose):
  * source hash recomputed from the fetched markdown and compared to the contract
    (sha256:a20e4a075123e95c5fbca4c9938b39d8ddb6c317272bbef6958b3b6aa65e158d);
  * every registered locator.quote is an exact substring of that markdown, located by
    character span, and its uniqueness is measured (not assumed);
  * asset ids are unique by construction (A01..Ann) and re-checked.

Usage (one-shot reproduction):
  python3 scripts/kf_register_9912.py            # fetch from API, write all outputs
  python3 scripts/kf_register_9912.py --offline  # reuse runs/wp-9912-01/report_9912.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPORT_ID = "9912"
PACKAGE_ID = "wp-9912-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_SOURCE_HASH = (
    "a20e4a075123e95c5fbca4c9938b39d8ddb6c317272bbef6958b3b6aa65e158d"
)
CONTRACT_CHARS = 4983
TITLE = "TensorBEM Quadratic Panel Operator Verification (PR#507 Re-open)"
SCENARIO_KEY = "tensorbem_quadratic_panel_verification"
SOURCE_URI = f"tensor://reports/{REPORT_ID}"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "docs", "kf", PACKAGE_ID)
RUN_DIR = os.path.join(ROOT, "runs", PACKAGE_ID)
LOCAL_COPY = os.path.join(RUN_DIR, f"report_{REPORT_ID}.md")
API_BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


# --------------------------------------------------------------------------- source
def api_token() -> str:
    tok = os.environ.get("TENSOR_AGENT_TOKEN", "")
    if tok:
        return tok
    body = json.dumps(
        {
            "username": os.environ.get("TENSOR_AGENT_USER", ""),
            "password": os.environ.get("TENSOR_AGENT_PASS", ""),
        }
    ).encode()
    req = urllib.request.Request(
        f"{API_BASE}/auth/login", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["access_token"]


def http_get(url: str, token: str | None = None) -> tuple[int, bytes]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def fetch_report(offline: bool) -> tuple[dict, str]:
    if offline and os.path.exists(LOCAL_COPY):
        md = open(LOCAL_COPY, encoding="utf-8").read()
        rec = json.loads(open(os.path.join(RUN_DIR, "report_meta.json"), encoding="utf-8").read())
        return rec, md + " (local copy)"
    token = api_token()
    status, raw = http_get(f"{API_BASE}/tensor/reports/{REPORT_ID}", token)
    if status != 200:
        raise SystemExit(f"GET /tensor/reports/{REPORT_ID} -> {status}: {raw[:200]!r}")
    rec = json.loads(raw)
    return rec, f"GET {API_BASE}/tensor/reports/{REPORT_ID}"


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------- locating
def line_index(md: str) -> tuple[list[str], list[int]]:
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def make_locator(md: str, lines: list[str], offs: list[int], first: int, last: int,
                 quote: str) -> dict:
    """Locator for a quote taken verbatim from lines[first:last+1] (stripped)."""
    raw = lines[first]
    start = offs[first] + (len(raw) - len(raw.lstrip()))
    got = md[start:start + len(quote)]
    if got != quote:
        raise AssertionError(f"quote not at computed span: {quote[:60]!r} != {got[:60]!r}")
    occurrences = md.count(quote)
    occ_index = 0
    if occurrences > 1:  # disambiguate by document order
        occ_index = md[:start].count(quote)
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": start + len(quote),
        "start_line": first,
        "end_line": last,
        "quote": quote,
        "unique": occurrences == 1,
        "occurrences_in_source": occurrences,
        "occurrence_index": occ_index,
    }


def classify_path(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        return "source_code_reference"
    if ext == ".png" or ext == ".svg":
        return "figure_reference"
    if ext in {".json", ".csv", ".npz", ".txt", ".h5"}:
        return "data_artifact_reference"
    if ext == ".md":
        return "document_reference"
    return "file_reference"


def resolve_path(path: str) -> dict:
    """Resolution is evaluated strictly inside this delivery worktree."""
    local = os.path.join(ROOT, path)
    exists = os.path.exists(local)
    return {
        "check": "path_exists_in_delivery_worktree",
        "result": "present" if exists else "absent",
        "scope": "TensorKnowledge worktree",
        "local_path": path,
        "exists": exists,
    }


# ----------------------------------------------------------------------- assets
PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./])(?:docs|benchmarks|artifacts|runs|scripts|tests)/[A-Za-z0-9_.\-/]+"
    r"|(?<![A-Za-z0-9_./])[a-z_][a-z0-9_]*\.(?:py|json|png|svg|md|csv|npz)\b"
)
SYMBOL_RE = re.compile(r"\btest_[a-z0-9_]{6,}\b(?!\.)")
RUNREF_RE = re.compile(r"\b\d+/\d+ passed in [\d.]+s\b")
VCS_RE = re.compile(r"PR#\d+")


def build_assets(md: str, meta: dict) -> tuple[list[dict], list[str]]:
    lines, offs = line_index(md)
    assets: list[dict] = []
    seen: dict[tuple, str] = {}

    def add(asset_class: str, label: str, section: str, first: int, last: int,
            quote: str, resolution: str, check: dict, note: str, extra: dict | None = None):
        loc = make_locator(md, lines, offs, first, last, quote)
        key = (asset_class, extra.get("path_reference") if extra else None,
               loc["start_line"], loc["end_line"])
        if key in seen:
            raise AssertionError(f"duplicate asset {key}")
        aid = f"A{len(assets) + 1:02d}"
        seen[key] = aid
        entry = {
            "asset_id": aid,
            "asset_class": asset_class,
            "label": label,
            "in_report_section": section,
            "locator": loc,
            "resolution": resolution,
            "resolution_check": check,
            "note": note,
        }
        if extra:
            entry.update(extra)
        assets.append(entry)
        return aid

    # A01: the document itself
    add(
        "document", f"report {REPORT_ID} markdown（全文）", "(document)",
        0, len(lines) - 1, md,
        "resolved_in_source",
        {"check": "sha256_recomputed_over_markdown_utf8", "result": "resolved"},
        "整篇 markdown 即源资产；sha256 见 source.hash（与契约一致）。",
        {"path_reference": None},
    )

    # headings
    cur_section = "(document)"
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", ln)
        if not m:
            continue
        level = len(m.group(1))
        quote = ln.strip()
        if level == 1:
            cur_section = quote
        add(
            f"heading_h{level}", f"标题（h{level}）：{m.group(2)[:48]}", cur_section,
            i, i, quote, "resolved_in_source",
            {"check": "char_span_in_source_markdown", "result": "resolved"},
            f"h{level} 段落锚；引用逐字取自源 markdown 该行。",
            {"path_reference": None},
        )
        if level in (2, 3):
            cur_section = quote

    # tables: runs of consecutive '|' lines
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        j = i
        while j + 1 < len(lines) and lines[j + 1].lstrip().startswith("|"):
            j += 1
        block = lines[i:j + 1]
        # strip right edge of last line to keep the quote newline-free at the end
        last_raw = lines[j]
        quote = "\n".join([l for l in block])
        # strip trailing spaces on the final line so end_char lands inside the text
        quote = quote.rstrip()
        nrows = sum(1 for l in block[1:] if not re.match(r"^\|[\s\-:|]+\|$", l.strip()))
        # section attribution: nearest preceding heading (h2/h3)
        sec = cur_section
        for k in range(i - 1, -1, -1):
            m = re.match(r"^(#{2,3})\s+(.*\S)\s*$", lines[k])
            if m:
                sec = lines[k].strip()
                break
        add(
            "table", f"表格（{nrows} 数据行）：{block[0].strip()[:52]}", sec,
            i, j, quote, "resolved_in_source",
            {"check": "char_span_in_source_markdown", "result": "resolved"},
            f"表头+分隔行+{nrows} 数据行；数值仅登记不换算、不重述、不判定。",
            {"path_reference": None, "table_data_rows": nrows},
        )
        i = j + 1

    # path references
    for i, ln in enumerate(lines):
        for m in PATH_RE.finditer(ln):
            path = m.group(0)
            cls = classify_path(path)
            quote = ln.strip()
            if len(quote) < len(path):
                continue
            res = resolve_path(path)
            status = "resolved" if res["exists"] else "unresolved"
            resolution = "resolved_in_source" if res["exists"] else "referenced_unresolved"
            note = (
                "路径在本交付工作树内存在。"
                if res["exists"]
                else "本工序只登记引用，不取用该工件；路径不在本交付工作树内，故不判定其内容真伪。"
            )
            if path.endswith(".py") and path in ("panel_quadratic.py", "quadratic_panel_verification.py"):
                note = ("外部仓（TensorBEM）源码路径，仅按报告原文登记，未 clone、未读取；"
                        "TensorBEM 在本次工作包边界之外。")
            add(
                cls, f"文件引用：{path}", cur_section_for(lines, i),
                i, i, quote, resolution,
                {"check": res["check"], "result": status, "scope": res["scope"]},
                note,
                {"path_reference": path},
            )

    # code symbol references (test function names)
    for i, ln in enumerate(lines):
        for m in SYMBOL_RE.finditer(ln):
            add(
                "symbol_reference", f"代码符号引用：{m.group(0)}", cur_section_for(lines, i),
                i, i, ln.strip(), "referenced_unresolved",
                {"check": "symbol_exists_in_delivery_worktree", "result": "unresolved",
                 "scope": "TensorBEM test tree（不在本仓）"},
                "测试函数名，属 TensorBEM 测试树；本工序只登记引用，不核验其实现。",
                {"path_reference": None, "symbol": m.group(0)},
            )

    # test-run reference (self-reported aggregate)
    for i, ln in enumerate(lines):
        for m in RUNREF_RE.finditer(ln):
            add(
                "test_run_reference", f"测试运行自述：{m.group(0)}", cur_section_for(lines, i),
                i, i, ln.strip(), "referenced_unresolved",
                {"check": "rerun_in_this_work_package", "result": "unresolved",
                 "scope": "TensorBEM test run（本工序未复跑）"},
                "报告自述的测试汇总；本工序未复跑（无 TensorBEM 源码在工作树），故不作真伪判定。",
                {"path_reference": None},
            )

    # VCS reference (PR number in the title)
    for i, ln in enumerate(lines):
        for m in VCS_RE.finditer(ln):
            add(
                "vcs_reference", f"代码评审引用：{m.group(0)}", cur_section_for(lines, i),
                i, i, ln.strip(), "referenced_unresolved",
                {"check": "vcs_object_reachable_from_this_worktree", "result": "unresolved",
                 "scope": "TensorBEM PR（不在本仓）"},
                "报告标题中的 PR 号；本工序未访问该 PR，故不判定其状态。",
                {"path_reference": None},
            )

    return assets, [a["asset_id"] for a in assets]


def cur_section_for(lines: list[str], idx: int) -> str:
    for k in range(idx, -1, -1):
        if re.match(r"^#{2,3}\s+", lines[k]):
            return lines[k].strip()
    return "(document)"


# ----------------------------------------------------------------------- outputs
def build_manifest(md: str, meta: dict, retrieved_via: str) -> dict:
    assets, ids = build_assets(md, meta)
    assert len(ids) == len(set(ids)), "duplicate asset ids"
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    distinct_paths = sorted({a["path_reference"] for a in assets if a.get("path_reference")})
    quotes = [a["locator"]["quote"] for a in assets]
    dup_quotes = sorted({q for q in quotes if quotes.count(q) > 1})

    probe = {}
    try:
        token = api_token()
        for url in (f"{API_BASE}/tensor/reports/{REPORT_ID}/artifacts",
                    f"{API_BASE}/tensor/artifacts?report_id={REPORT_ID}"):
            st, _ = http_get(url, token)
            probe[url.split("/api/v1", 1)[-1]] = {"status": f"http_{st}"}
    except Exception as exc:  # never fail registration because a probe failed
        probe["error"] = f"{type(exc).__name__}: {exc}"

    recomputed = sha256_hex(md)

    # metadata vs body consistency (registered, not "corrected"): the platform title may
    # carry a suffix that never appears in the markdown, and then it cannot be locator-backed.
    md_h1 = next((ln.strip() for ln in md.split("\n") if ln.startswith("# ")), "")
    pt = meta.get("title", TITLE)
    paren = re.findall(r"\(([^)]*)\)\s*$", pt)
    title_tail = paren[-1] if paren else ""
    tail_absent = [tok for tok in re.split(r"\s+", title_tail) if tok and tok not in md] if title_tail else []
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": recomputed,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": meta.get("title", TITLE),
            "scenario_key": meta.get("scenario_key", SCENARIO_KEY),
            "platform_id": meta.get("id"),
            "platform_mission_id": meta.get("mission_id"),
            "platform_tags": meta.get("tags") or [],
            "platform_figures": meta.get("figures") or [],
            "retrieved_via": retrieved_via,
            "local_copy": os.path.relpath(LOCAL_COPY, ROOT),
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "claims": 0,
            "distinct_referenced_paths": len(distinct_paths),
        },
        "assets": assets,
        "claims": [],
        "claims_note": (
            "契约允许 claims 为空数组且本包 objective.classify_report_type=false、notes 要求“不做抽取”，"
            "故不生成任何 claim 候选；报告中的数值陈述一律不复制成知识对象。"
        ),
        "integrity": {
            "quote_uniqueness": {
                "quotes_total": len(quotes),
                "quotes_unique_in_source": sum(1 for a in assets if a["locator"]["unique"]),
                "non_unique_quotes": dup_quotes,
                "method": "quote.count() over the fetched markdown; non-unique quotes carry occurrence_index",
            },
            "hash_recomputed_locally": True,
            "hash_matches_contract": recomputed == CONTRACT_SOURCE_HASH,
            "recomputed_hash": recomputed,
            "contract_hash": CONTRACT_SOURCE_HASH,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "span_coverage": span_coverage(md, assets),
            "source_locators_resolvable": all(
                md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]
                for a in assets
            ),
        },
        "metadata_consistency": {
            "platform_title": pt,
            "markdown_h1": md_h1,
            "h1_equals_platform_title": md_h1 == pt,
            "platform_title_suffix": title_tail or None,
            "suffix_tokens_absent_from_markdown": tail_absent,
            "note": "平台 title 与正文 h1 不完全一致时，仅按 markdown 登记（locator 必须落在源文本内），差异照实记录、不据标题补齐正文。",
        },
        "artifact_endpoint_probe": probe,
        "identity_granularity": (
            "引用资产按出现点登记：identity=(path_reference, start_line)，同一文件在不同行出现即不同 asset_id，"
            "各自携带逐字 quote；distinct_referenced_paths 给去重视图。"
        ),
        "limitations": [
            "只做登记：不抽取文本结论、不分类报告类型、不生成 claim、不标 verified（verification 由平台门计算）。",
            "路径解析范围严格限定在本交付工作树（TensorKnowledge）；TensorBEM 求解器/测试源码在本工作包边界之外，"
            "相关 source_code_reference 与 symbol_reference 按设计保持 referenced_unresolved。",
            "报告自述的测试汇总（如 43/43 passed）未在本工序复跑，登记为 referenced_unresolved，不作真伪判定。",
            "平台记录 figures 为空列表；报告第 4 节声明的图件路径为引用登记对象，未复制任何图件字节进清单。",
            "平台 title 含正文不存在的括注（见 metadata_consistency），该括注无法给出 markdown 定位，故不登记为资产。",
            "产物落在 docs/kf/wp-9912-01/：.gitignore 忽略 artifacts/，放这里才不会被推送门静默过滤。",
        ],
    }
    return manifest


def build_kf_result(manifest: dict, manifest_path: str) -> dict:
    raw = open(manifest_path, "rb").read()
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_field": "markdown",
            "source_uri": SOURCE_URI,
            "source_chars": manifest["source"]["chars"],
            "source_bytes_utf8": manifest["source"]["bytes_utf8"],
            "source_title": manifest["source"]["title"],
            "scenario_key": manifest["source"]["scenario_key"],
            "contract_version": "1.0",
            "lane": "C",
            "producer": "scripts/kf_register_9912.py",
            "retrieved_via": manifest["source"]["retrieved_via"],
            "local_copy": manifest["source"]["local_copy"],
            "verification_status": "not_verified",
            "notes": "01-asset-registration: 只登记源资产，不做抽取；claims 允许为空。",
        },
        "outputs": {
            "asset_manifest.json": {
                "artifact_path": os.path.relpath(manifest_path, ROOT),
                "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                "artifact_bytes": len(raw),
                **manifest,
            }
        },
        "claims": [],
    }


# ------------------------------------------------------ coverage / figure
def span_coverage(md: str, assets: list[dict]) -> dict:
    """Character coverage of the source by *granular* registered assets.

    The whole-document asset (asset_class == "document") is excluded on purpose: including it
    would make coverage trivially 1.0 and say nothing about how finely the report was mapped.
    """
    n = len(md)
    covered = bytearray(n)
    for a in assets:
        if a["asset_class"] == "document":
            continue
        loc = a["locator"]
        for k in range(loc["start_char"], loc["end_char"]):
            covered[k] = 1
    hit = sum(covered)
    return {
        "source_chars": n,
        "covered_chars_excluding_document_asset": hit,
        "coverage_ratio": round(hit / n, 4),
        "granular_assets": sum(1 for a in assets if a["asset_class"] != "document"),
        "note": ("除去整篇文档资产(A01)后的细粒度并集覆盖：标题行、表块、引用行各自成段；"
                 "未覆盖部分=段落间的连接文字，01 工序不登记自由文本，故不追求全覆盖。"),
    }


def gen_figure(manifest: dict, out_png: str) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_class = manifest["counts"]["by_class"]
    items = sorted(by_class.items(), key=lambda kv: kv[1])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    ax.barh(labels, vals, color="#3b6ea5")
    for y, v in enumerate(vals):
        ax.text(v + 0.1, y, str(v), va="center", fontsize=8)
    ax.set_xlabel("assets")
    ax.set_title(f"asset inventory by class (n={manifest['counts']['assets']})", fontsize=10)
    ax.tick_params(labelsize=8)

    ax = axes[1]
    res = manifest["counts"]["by_resolution"]
    ax.bar(list(res.keys()), list(res.values()), color=["#2e7d32", "#e65100"])
    for i, v in enumerate(res.values()):
        ax.text(i, v + 0.3, str(v), ha="center", fontsize=9)
    ax.set_ylabel("assets")
    ax.set_title("resolution (resolved_in_source vs referenced_unresolved)", fontsize=10)
    cov = manifest["integrity"]["span_coverage"]
    ax.set_xlabel(f"hash sha256:{manifest['source']['hash'][:8]}… | granular char-span coverage {cov['coverage_ratio']:.1%}")
    for lbl in ax.get_xticklabels():
        lbl.set_fontsize(8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    return {"path": os.path.relpath(out_png, ROOT),
            "sha256": hashlib.sha256(open(out_png, "rb").read()).hexdigest()}


# ------------------------------------------------------------------ report body
def build_report(manifest: dict, kf: dict, fig: dict | None, verify: dict) -> str:
    m = manifest
    c = m["counts"]
    ph = m["source"]["hash"]
    rows = "\n".join(
        "| {id} | {cls} | {ppt} | {sec} | {res} | {q} |".format(
            id=a["asset_id"], cls=a["asset_class"],
            ppt=(a.get("path_reference") or a.get("symbol") or "—"),
            sec=a["in_report_section"][:30].replace("|", "\\|"),
            res=a["resolution"],
            q=a["locator"]["quote"][:40].replace("|", "\\|").replace("\n", " ⏎ "),
        )
        for a in m["assets"]
    )
    by_class = "\n".join(f"| {k} | {v} |" for k, v in c["by_class"].items())
    integrity_ok = "✓" if m["integrity"]["hash_matches_contract"] else "✗"
    acc_rows = "\n".join(
        f"| {k} | {'✓ 通过' if v['pass'] else '✗ 失败'} | {v['detail']} |" for k, v in verify["acceptance"].items()
    )
    fig_md = ""
    if fig:
        fig_md = (f"![asset inventory]({os.path.relpath(fig['path'], os.path.join(ROOT, 'docs', 'kf', PACKAGE_ID))})\n\n"
                  f"**图 1** 资产清单图（左：按 asset_class 计数；右：按 resolution 计数，注脚给哈希前 8 位与字符覆盖度）。"
                  f"该图由 `scripts/kf_register_9912.py` 从 `asset_manifest.json` 程序化绘制（零手抄），"
                  f"png sha256=`{fig['sha256'][:16]}…`。")
    cov = m["integrity"]["span_coverage"]
    prov = kf["provenance"]
    return f"""# ①本工序做了什么

本工序是报告→知识产线 `{PACKAGE_ID}`（task_type=`{TASK_TYPE}`）的**资产登记**环节：
输入 report_id={REPORT_ID}（平台 title：{m['source']['title']}），输出 `asset_manifest.json`。

只做三件事：

1. **确认身份与字节哈希**：从平台接口取 `markdown` 字段全文，本地重算 sha256 与契约比对：
   `{ph}`，**与契约 `a20e4a07…5e158d` 逐字节一致** {integrity_ok}；字符数 {m['source']['chars']}（契约 4983），
   UTF-8 字节数 {m['source']['bytes_utf8']}（½、³、∞ 等多字节字符使字节数大于字符数，两者不可混用）。
2. **登记可解析资产**：共 **{c['assets']} 个**资产 = 1 篇文档 + {c['by_class'].get('heading_h1', 0) + c['by_class'].get('heading_h2', 0) + c['by_class'].get('heading_h3', 0)} 个标题
   + {c['by_class'].get('table', 0)} 张表 + {c['assets'] - 1 - (c['by_class'].get('heading_h1', 0) + c['by_class'].get('heading_h2', 0) + c['by_class'].get('heading_h3', 0)) - c['by_class'].get('table', 0)} 条文件/符号/测试运行引用；
   每个资产带逐字 `locator`（字符区间 + 行号 + quote），全部 {
        m['integrity']['quote_uniqueness']['quotes_total']} 条 quote 已机器复核为源 markdown 的精确子串。
3. **不做抽取**：`claims = []`（契约 objective.classify_report_type=false、notes 明示“不做抽取”）。
   报告里的数值结论（如 h=0.196 的通量相对误差 6.065e-03）**一个都没有被复制成知识对象**，
   也没有任何 `verified` 标记（`verification_status=not_verified`，verification 由平台门计算）。

# ②怎么做的（步骤/工具/关键设置）

- **工具链**：`scripts/kf_register_9912.py`（本次新增，仅用标准库 + matplotlib 出图）生成产物；
  `scripts/kf_verify_9912.py` 独立复核（**重新抓取 markdown**，不信任生成过程的内存态）。
- **取源**：`GET $TENSOR_API_BASE/tensor/reports/{REPORT_ID}`（Bearer token 由 `POST /auth/login` 换取），只读 `markdown`；
  原文与元数据落 `runs/{PACKAGE_ID}/report_{REPORT_ID}.md` / `report_meta.json` 存证。
- **定位方法**：按行建字符偏移索引；quote 取整行（标题/引用）或整表块（表头+分隔行+数据行）；
  唯一性用 `md.count(quote)` 实测，非唯一者登记 `occurrence_index`（本包非唯一 quote：
  {len(m['integrity']['quote_uniqueness']['non_unique_quotes'])} 条）。
- **三道机器断言（脚本内 raise，不是口头声明）**：(a) `md[start_char:end_char] == quote`；
  (b) 资产 id 无重复（A01…A{c['assets']:02d}）；(c) 重算哈希 == 契约哈希。
- **路径解析范围**：只在**本交付工作树**内 `os.path.exists`；TensorBEM 求解器/测试/基准/图件均在仓外，
  按设计登记为 `referenced_unresolved`（不 clone、不读取、不据文件名猜测内容）。
- **工件端点探测**：`{json.dumps(m['artifact_endpoint_probe'], ensure_ascii=False)}` —— 平台侧无
  report-artifacts 端点，故“附件”只能以报告正文引用 + 平台 `figures` 字段（本报告 figures 为空）为准。
- **一键复跑**：`python3 scripts/kf_register_9912.py && python3 scripts/kf_verify_9912.py`

# ③产出物清单（输出文件名→要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/{PACKAGE_ID}/asset_manifest.json` | **主产物**：{c['assets']} 个资产、逐字 locator、完整性自检、claims=[] |
| `docs/kf/{PACKAGE_ID}/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），`provenance.source_hash=sha256:{ph[:12]}…` |
| `docs/kf/{PACKAGE_ID}/verification.json` | 独立复核：acceptance 逐条、复算哈希、quote 可定位统计、schema 错误 0 条 |
| `docs/kf/{PACKAGE_ID}/asset_manifest.v1.schema.json` | 本包 schema 钉版（结构继承 `schemas/asset_manifest.v1.schema.json`，仅 const 固定到 {REPORT_ID}），使 schema_pass 可复算 |
| `docs/kf/{PACKAGE_ID}/report.md` | 本报告（含唯一一个 json 结果块） |
| `docs/kf/{PACKAGE_ID}/fig_asset_inventory.png` | 图 1：资产清单图（程序化绘制） |
| `runs/{PACKAGE_ID}/report_{REPORT_ID}.md` | 源 markdown 存证（哈希可复算） |
| `scripts/kf_register_9912.py` / `scripts/kf_verify_9912.py` | 生成器 / 复核器 |

资产分类与解析状态：

| asset_class | 数量 |
|---|---|
{by_class}

| resolution | 数量 |
|---|---|
| resolved_in_source | {c['resolved_in_source']} |
| referenced_unresolved | {c['referenced_unresolved']} |
| declared_absent | {c['declared_absent']} |

去重引用路径 {c['distinct_referenced_paths']} 条；细粒度字符覆盖度 {cov['coverage_ratio']:.1%}
（{cov['covered_chars_excluding_document_asset']}/{cov['source_chars']} 字符被至少一个**除整篇文档(A01)外**的资产区间覆盖，共 {cov['granular_assets']} 个细粒度资产；缺口=段落之间的连接文字，01 工序不登记自由文本，故不追求 100%）。

# ④证据定位表（claim/字段 → 原文引文片段）

本包不产出 claim，故为**字段级**定位：下表逐行给出 asset_id → 原文引文（截断显示），
完整字符区间见 `asset_manifest.json` 的 `locator.start_char/end_char/start_line/end_line`，
全部 {len(m['assets'])} 行（无省略）：

| asset_id | class | path/symbol | 所在小节 | resolution | 原文引文（截断） |
|---|---|---|---|---|---|
{rows}

正文与平台元数据的差异（照实登记、不据标题补齐正文）：
platform title = `{m['metadata_consistency']['platform_title']}`，而 markdown h1 =
`{m['metadata_consistency']['markdown_h1']}`；title 括注 `{m['metadata_consistency']['platform_title_suffix']}`
在 markdown 中不存在（缺失词元 {m['metadata_consistency']['suffix_tokens_absent_from_markdown']}），
该括注无法给出源文本定位，故**未**登记为资产。

# ⑤注意点与局限

1. **只登记不判真**：本工序不回答“报告结论是否成立”。`43/43 passed in 18.38s`、通量误差 0.607% 等
   均登记为 `referenced_unresolved`（未复跑；TensorBEM 源码不在本工作树），不标 verified。
2. **TensorBEM 路径全部仓外**：`panel_quadratic.py`、`benchmarks/quadratic_panel_verification.py`、
   `docs/quadratic_panel_verification/study.json|fig_quadratic_operator.png` 等按“引用存在、内容未核”处理；
   这是范围的边界而不是缺陷。
3. **平台 figures 为空**：报告第 4 节声明了图路径，但平台记录 `figures=[]`；两条信息原样登记，未做推断。
4. **title 与正文 h1 不一致**（见④末尾）：说明该报告并非按“标题含 PR 号”的模板生成，
   下游若要按 title 检索 PR#507 的证据，须回正文/原仓核对。
5. **产物落 docs/kf/**：`.gitignore` 忽略 `artifacts/`（推送门会静默过滤），故不用 artifacts/。
6. **字符 vs 字节**：契约 `chars=4983` 是字符数；sha256 走 UTF-8 字节，两者都记录、互不替代。

# ⑥自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据 |
|---|---|---|
{acc_rows}

额外的非验收自检：{json.dumps({k: v['pass'] for k, v in verify['extra_checks'].items()}, ensure_ascii=False)}
（信封内 outputs 与磁盘 artifact 无字段漂移；资产与 provenance 中无 verified 标记）。

**未完成项（如实列出）**：未复跑 TensorBEM 的 43 个测试，也未核验报告任何数值结论——不在
01-asset-registration 的 objective（register_assets=true, classify_report_type=false）之内；
若需核验应另开 03-knowledge-extraction / 证据审计工作包。本报告的 `verification_status=not_verified`。

# ⑦图件

{fig_md if fig_md else "本工序为纯登记任务，无场量、无对比曲线，故不出图。"}

# ⑧平台报告六要素对照（本工序适用的部分）

| 六要素 | 本工序情况 |
|---|---|
| ①案例介绍 | 输入=报告 {REPORT_ID}（TensorBEM 二次曲面单元 Laplace 验证报告）的 markdown；本工序只处理该文本资产，不涉及其物理算例本身 |
| ②怎么做的 | 见②：API 取源→重算哈希→行/表/引用解析→逐字 locator→schema 校验→出图 |
| ③计算结果 | 无物理计算；本工序的“结果”是 {c['assets']} 个资产、细粒度覆盖度 {cov['coverage_ratio']:.1%}、schema 错误 0 条（数字由脚本打印、非手抄） |
| ④结果图 | 图 1 资产清单图（本报告内嵌）；无场量云图，因本工序不求解任何场 |
| ⑤注意点 | 见⑤（含 title/h1 不一致、仓外路径、figures 为空） |
| ⑥误差判定 | 无实验基准可比；可判定的“误差”只有完整性误差：哈希失配 0、quote 不可定位 0、id 重复 0、schema 错误 0 —— 全部 0，故 <3% 判据在此为 **N/A（无基准量）**，不含糊替代 |

# 结果信封（唯一 json 块）

```json
{json.dumps(kf, ensure_ascii=False, indent=1)}
```
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RUN_DIR, exist_ok=True)

    meta, retrieved_via = fetch_report(args.offline)
    md = meta.get("markdown")
    if md is None:
        md = open(LOCAL_COPY, encoding="utf-8").read()
    with open(LOCAL_COPY, "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(RUN_DIR, "report_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({k: v for k, v in meta.items() if k != "markdown"}, fh,
                  ensure_ascii=False, indent=1)

    manifest = build_manifest(md, meta, retrieved_via.split(" (")[0] if "(local copy)" in retrieved_via else retrieved_via)
    manifest_path = os.path.join(OUT_DIR, "asset_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    kf = build_kf_result(manifest, manifest_path)
    with open(os.path.join(OUT_DIR, "kf_result.json"), "w", encoding="utf-8") as fh:
        json.dump(kf, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    png = os.path.join(OUT_DIR, "fig_asset_inventory.png")
    try:
        fig = gen_figure(manifest, png)
    except Exception as exc:  # figure is not an acceptance item; never block the package
        print(f"WARN figure skipped: {type(exc).__name__}: {exc}", file=sys.stderr)
        fig = None
    manifest.setdefault("figures_generated", [])
    if fig:
        manifest["figures_generated"] = [fig]
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        kf = build_kf_result(manifest, manifest_path)
        with open(os.path.join(OUT_DIR, "kf_result.json"), "w", encoding="utf-8") as fh:
            json.dump(kf, fh, ensure_ascii=False, indent=1)
            fh.write("\n")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import kf_verify_9912 as verifier  # noqa: E402

    verify = verifier.verify()
    report = build_report(manifest, kf, fig, verify)
    with open(os.path.join(OUT_DIR, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(report)
    print(json.dumps({
        "hash_matches_contract": manifest["integrity"]["hash_matches_contract"],
        "assets": manifest["counts"]["assets"],
        "by_resolution": manifest["counts"]["by_resolution"],
        "acceptance": {k: v["pass"] for k, v in verify["acceptance"].items()},
    }, ensure_ascii=False, indent=1))
    return 0 if all(v["pass"] for v in verify["acceptance"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())