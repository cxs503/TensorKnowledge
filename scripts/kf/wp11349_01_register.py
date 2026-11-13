#!/usr/bin/env python3
"""wp-11349-01 (task_type=01-asset-registration) — build the asset manifest for report 11349.

Scope (verbatim from the work-package contract):
    "登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的附件/工件，不做抽取。
     claims 允许为空数组。"

So this script only:
  * fetches the report markdown (or reuses the byte snapshot) and pins its sha256,
  * inventories the artefacts the report references (files, symbols, endpoints, tests,
    cross-report reference, in-report evidence table),
  * records for each one a verbatim locator (char span + line span + uniqueness proof),
  * emits claims: []  — no extraction, no report_type classification, no verified stamp.

Usage:  python3 scripts/kf/wp11349_01_register.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

REPORT_ID = "11349"
PACKAGE_ID = "wp-11349-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_HASH = "e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"
SOURCE_URI = "tensor://reports/11349"
CONTRACT_TITLE = "P266W1-N10 补记：能力台账 API 接线缺陷修复（capability_audit 路由 404）"
SCENARIO_KEY = "platform_governance_capability_ledger_semantics"
CONTRACT_CHARS = 1029

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "kf", PACKAGE_ID)
SRC = os.path.join(OUT, "source")
SNAP = os.path.join(SRC, f"report_{REPORT_ID}.md")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def fetch_markdown() -> tuple[str, dict]:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010").rstrip("/")
    user, pw = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": pw}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.loads(r.read())["access_token"]
    req = urllib.request.Request(
        f"{base}/tensor/reports/{REPORT_ID}", headers={"Authorization": "Bearer " + tok}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        rec = json.loads(r.read())
    return rec.pop("markdown"), rec


def load_markdown() -> tuple[str, dict, str]:
    if os.path.exists(SNAP):
        md = open(SNAP, encoding="utf-8").read()
        meta = {}
        mpath = os.path.join(SRC, f"record_{REPORT_ID}.json")
        if os.path.exists(mpath):
            meta = json.load(open(mpath, encoding="utf-8"))
        return md, meta, "byte snapshot (docs/kf/%s/source/report_%s.md)" % (PACKAGE_ID, REPORT_ID)
    md, meta = fetch_markdown()
    os.makedirs(SRC, exist_ok=True)
    return md, meta, "GET /tensor/reports/%s (platform API)" % REPORT_ID


def line_of(md: str, pos: int) -> int:
    return md.count("\n", 0, pos) + 1


def span_for(md: str, anchor: str, span_end: str | None = None) -> dict:
    """Locate `anchor` (optionally extended to `span_end`), widening until the quote is unique."""
    if anchor not in md:
        raise SystemExit(f"anchor not found verbatim in markdown: {anchor!r}")
    start = md.find(anchor)
    end = md.find(span_end, start) + len(span_end) if span_end else start + len(anchor)
    # widen symmetrically until the quote occurs exactly once
    quote = md[start:end]
    while md.count(quote) > 1:
        if start > 0:
            start -= 1
        elif end < len(md):
            end += 1
        else:
            break
        quote = md[start:end]
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": line_of(md, start),
        "end_line": line_of(md, end - 1),
        "quote": quote,
        "unique": md.count(quote) == 1,
    }


def worktree_path_state(rel: str) -> dict:
    """Is the referenced path resolvable inside *this* worktree (TensorKnowledge)?"""
    abs_ = os.path.join(ROOT, rel)
    exists = os.path.exists(abs_)
    grep = subprocess.run(
        ["grep", "-rIl", "--", rel, "--include=*.py", "--include=*.md", ROOT],
        capture_output=True, text=True,
    ).stdout.strip().splitlines()
    return {"in_this_worktree": exists, "grep_hits_in_this_worktree": len(grep)}


def main() -> int:
    md, rec, how = load_markdown()
    got = sha256_text(md)
    if got != CONTRACT_HASH:
        sys.exit(f"FATAL source_hash mismatch: {got} != {CONTRACT_HASH}")
    os.makedirs(SRC, exist_ok=True)
    with open(SNAP, "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(SRC, f"record_{REPORT_ID}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)

    repo_head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout.strip()
    repo_branch = subprocess.run(["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"],
                                 capture_output=True, text=True).stdout.strip()

    # ---- asset inventory (no extraction: locators + resolvability only) -------------
    specs = [
        dict(
            asset_id="A00", asset_class="report_document", kind="report_document",
            label=f"报告正文 markdown（{REPORT_ID}，来源资产本体）",
            resolution="resolved_in_source",
            resolution_check={"check": "sha256(utf-8 bytes) == contract source_hash",
                              "result": "resolved"},
            locator={"method": "document", "start_char": 0, "end_char": len(md),
                     "start_line": 1, "end_line": line_of(md, len(md) - 1),
                     "quote": md.splitlines()[0], "unique": md.count(md.splitlines()[0]) == 1},
            note="字节哈希已钉扎；本条为本工序的被登记对象本体。",
        ),
        dict(
            asset_id="A01", asset_class="source_file", kind="source_file_under_review",
            label="backend/api/capability_audit.py（缺陷所在的 21 能力证据等级矩阵端点模块）",
            anchor="backend/api/capability_audit.py",
            resolution="referenced_unresolved",
            note="属 TensorPlatform 仓，不在本工作树（TensorKnowledge）内 → 本包只登记引用与定位，"
                 "不解引用、不复制代码。",
        ),
        dict(
            asset_id="A02", asset_class="source_file", kind="source_file_under_review",
            label="backend/main.py（未 include router 的装配点）",
            anchor="`backend/main.py` **从未 include 该 router**",
            resolution="referenced_unresolved",
            note="同上。quote 因唯一性扩窗而带上了报告对它的缺陷陈述（未 include）；"
                 "该陈述属报告结论，本包只登记位置，不重算、不判真伪。",
        ),
        dict(
            asset_id="A03", asset_class="source_symbol", kind="router_symbol",
            label="api.capability_audit.router（待挂载的 APIRouter 对象）",
            anchor="api.capability_audit.router",
            resolution="referenced_unresolved",
            note="符号级引用；所在模块在 TensorPlatform 仓。",
        ),
        dict(
            asset_id="A04", asset_class="source_symbol", kind="router_symbol",
            label="api.capability_semantics.router（本次并列新建的 router）",
            anchor="api.capability_semantics.router",
            resolution="referenced_unresolved",
            note="符号级引用；所在模块在 TensorPlatform 仓。",
        ),
        dict(
            asset_id="A05", asset_class="api_endpoint", kind="http_endpoint",
            label="GET /tensor/capabilities/audit（21 能力证据矩阵端点，缺陷路径）",
            anchor="`GET /tensor/capabilities/audit`",
            resolution="referenced_unresolved",
            note="线上 :8010 的服务端点，非本仓文件资产；本工序不做执行/重放探针。",
        ),
        dict(
            asset_id="A06", asset_class="api_endpoint", kind="http_endpoint",
            label="/audit/summary（同一 router 的汇总子路径）",
            anchor="/audit/summary",
            resolution="referenced_unresolved",
            note="与 A05 同 router 的另一端点；仅引用登记。",
        ),
        dict(
            asset_id="A07", asset_class="api_endpoint", kind="http_endpoint",
            label="GET /api/v1/tensor/capabilities/semantics（新端点，分支未部署）",
            anchor="/api/v1/tensor/capabilities/semantics",
            resolution="referenced_unresolved",
            note="报告记录其带 token 探针结果为 404；本包不重放。",
        ),
        dict(
            asset_id="A08", asset_class="test_case", kind="regression_test",
            label="backend/tests/test_capability_semantics_api.py::"
                  "test_routers_wired_in_main_and_route_shapes（源码级接线回归）",
            anchor="test_capability_semantics_api.py::test_routers_wired_in_main_and_route_shapes",
            resolution="referenced_unresolved",
            note="测试文件在 TensorPlatform 仓；本仓无法执行该测试，故只登记不判绿。",
        ),
        dict(
            asset_id="A09", asset_class="cross_report_reference", kind="report_cross_reference",
            label="主报告 id=11344（本补记不改变其判据数字）",
            anchor="id=11344",
            resolution="referenced_unresolved",
            note="跨报告引用。按产线边界（只碰 report_id=11349）本包**不解引用** 11344，"
                 "故其存在性与内容状态为未解，不可判 verified。",
        ),
        dict(
            asset_id="A10", asset_class="evidence_table", kind="in_report_probe_table",
            label="复现探针表（带 JWT 打 :8010，2026-11-10，三行请求/结果）",
            anchor="| 请求 | 结果 |",
            span_end="符合预期） |",
            resolution="resolved_in_source",
            note="表格在报告 markdown 内逐字可解析；作为下游工序的定位脚手架登记，不复制数字结论。",
        ),
    ]

    assets = []
    for s in specs:
        loc = s.get("locator") or span_for(md, s["anchor"], s.get("span_end"))
        check = s.get("resolution_check")
        if check is None:
            rel = s["anchor"].strip("`").split("::")[0]
            st = worktree_path_state(rel) if "/" in rel or rel.endswith(".py") else \
                {"in_this_worktree": False, "grep_hits_in_this_worktree": 0}
            check = {
                "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@"
                         f"{repo_head[:8]} (grep hits={st['grep_hits_in_this_worktree']}, "
                         f"exists={st['in_this_worktree']})",
                "result": "present" if (s.get("resolution") == "resolved_in_source")
                          else "unresolved",
            }
        assets.append({
            "asset_id": s["asset_id"],
            "asset_class": s["asset_class"],
            "kind": s["kind"],
            "label": s["label"],
            "in_report_section": "",
            "locator": loc,
            "resolution": s["resolution"],
            "resolution_check": check,
            "note": s["note"],
            "quote_verbatim_in_markdown": md.count(loc["quote"]) == 1 if loc["method"] == "char_span"
                                          else loc["quote"] in md,
        })

    # section attribution from the nearest preceding heading (locator scaffolding only)
    headings = []
    for ln, line in enumerate(md.splitlines(), start=1):
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            headings.append({"level": level, "text": line.lstrip("#").strip(), "line_no": ln})
    for a in assets:
        prev = [h for h in headings if h["line_no"] <= a["locator"]["start_line"]]
        a["in_report_section"] = (prev[-1]["text"] if prev else "preamble")

    by_class: dict[str, int] = {}
    by_resolution: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_resolution[a["resolution"]] = by_resolution.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "objective": {"register_assets": True, "classify_report_type": False},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": CONTRACT_HASH,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "lines": len(md.splitlines()),
            "title": CONTRACT_TITLE,
            "record_title": rec.get("title", ""),
            "scenario_key": SCENARIO_KEY,
            "record_scenario_key": rec.get("scenario_key", ""),
            "record_status": rec.get("status", ""),
            "record_mission_id": rec.get("mission_id"),
            "record_created_at": rec.get("created_at", ""),
            "record_tags": rec.get("tags", []),
            "platform_figures": rec.get("figures", []) or [],
            "fetched_via": how,
        },
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + CONTRACT_HASH,
            "contract_source_hash": "sha256:" + CONTRACT_HASH,
            "source_hash_matches_contract": True,
            "contract_chars": CONTRACT_CHARS,
            "contract_title": CONTRACT_TITLE,
            "title_matches_contract": rec.get("title", CONTRACT_TITLE) == CONTRACT_TITLE,
            "hashed_bytes": "markdown encoded as utf-8",
            "worktree_repo": "TensorKnowledge",
            "worktree_head": repo_head,
            "worktree_branch": repo_branch,
            "generator": "scripts/kf/wp11349_01_register.py",
            "contract_version": "1.0",
        },
        "resolution_vocabulary": {
            "resolved_in_source": "字节/引文在报告 markdown 内逐字定位（本包唯一可自证的一类）",
            "referenced_unresolved": "报告引用的目标在本包作用域外（他仓文件/线上端点/跨报告），"
                                     "只登记定位，不解引用、不判真伪",
            "declared_absent": "报告声明存在的产物在源内不存在（本报告无此情形，故计数为 0）",
        },
        "locator_convention": {
            "char_span": "start_char/end_char 为 UTF-8 解码后 markdown 字符串的字符下标，"
                         "md[start_char:end_char] == quote 逐字成立",
            "document": "method=document 的条目（仅 A00 本体）跨越整篇 [0, len)；其 quote 取首行标题，"
                        "字节完整性由 sha256 而非切片保证",
            "widening": "若锚点字符串在源内多次出现，则向左右扩窗直到 quote 唯一；"
                        "因此 quote 可能含有锚点之外的上下文语境，只作定位用，不构成抽取",
            "line_numbers": "start_line/end_line 为 1 基行号，由字符下标重算",
        },
        "structure_index": {
            "note": "仅标题行与字符偏移，作为下游工序的定位脚手架；不抽取任何内容",
            "headings": headings,
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_resolution,
            "resolved_in_source": by_resolution.get("resolved_in_source", 0),
            "referenced_unresolved": by_resolution.get("referenced_unresolved", 0),
            "declared_absent": by_resolution.get("declared_absent", 0),
            "claims": 0,
        },
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": "每条 locator.quote 在源 markdown 中出现恰好 1 次（A00 为标题行）",
            "hash_recomputed_locally": True,
            "hash_matches_contract": True,
            "verification_stamp": None,
            "verified": False,
        },
        "scope_statement": {
            "did": ["读取 report 11349 的 markdown 并重算 sha256",
                    "枚举报告引用的文件/符号/端点/测试/跨报告引用/证据表并给出 verbatim locator",
                    "输出 asset_manifest.json + kf_result.v1 信封"],
            "did_not": ["抽取知识对象（claims 为空数组）",
                        "做报告类型分类（objective.classify_report_type=false）",
                        "重放线上探针 / 执行他仓测试",
                        "解引用 report 11344（产线边界：只碰 11349）",
                        "打 verified 戳（verification 由平台门计算）"],
        },
    }

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "asset_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    kf_result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + CONTRACT_HASH,
            "source_field": "markdown",
            "source_uri": SOURCE_URI,
            "producer": f"agent/m15696 (TensorKnowledge) · package {PACKAGE_ID}",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": "01-asset-registration: hash-pinned inventory of report 11349; "
                     "claims intentionally empty; no extraction, no report_type classification, "
                     "no verification stamp",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    with open(os.path.join(OUT, "kf_result.json"), "w", encoding="utf-8") as f:
        json.dump(kf_result, f, ensure_ascii=False, indent=2)

    print(f"source hash ok: sha256:{CONTRACT_HASH}")
    print(f"chars={len(md)} bytes={len(md.encode())} lines={len(md.splitlines())}")
    print(f"assets={len(assets)} by_class={by_class}")
    print(f"by_resolution={by_resolution}")
    for a in assets:
        print(f"  {a['asset_id']} {a['asset_class']:<24} L{a['locator']['start_line']}-"
              f"{a['locator']['end_line']} uniq={a['locator']['unique']} {a['resolution']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())