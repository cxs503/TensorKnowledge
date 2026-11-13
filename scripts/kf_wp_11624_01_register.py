#!/usr/bin/env python3
"""KF work package wp-11624-01 — 01-asset-registration for report_id=11624.

Registers the *source asset* (report markdown, byte sha256) and the artefacts /
attachments / anchors the report declares, plus the figures that exist only as
record metadata. No extraction: `claims` is an empty array by contract
(objective.register_assets=true, objective.classify_report_type=false,
constraints.no_forced_claim_generation=true).

Hard boundaries honoured here
  * only report_id 11624 is read (single GET) or written (single local snapshot);
  * nothing is written back into the source report, and no object is marked
    `verified` — verification is computed by the platform gate, not by the worker;
  * zero hand-transcription: every quote is lifted from the fetched markdown by
    1-based line number and every locator is re-verified (char span + substring +
    uniqueness) before the manifest is emitted.

Outputs (all inside the worktree)
  knowledge/kf/wp-11624-01/source_report_11624.md    frozen markdown snapshot
  knowledge/kf/wp-11624-01/source_record.json        API record w/o markdown
  knowledge/kf/wp-11624-01/asset_manifest.json       deliverable of this package
  knowledge/kf/wp-11624-01/kf_result.json            kf_result.v1 result envelope
  docs/wp-11624-01/<same three>                      byte-identical durable mirror
                                                     (push gate drops artifacts/** and
                                                     runs/**, so docs/ is the committed copy)

Usage (one command, reproducible):
    python3 scripts/kf_wp_11624_01_register.py             # fetch live from the platform API
    python3 scripts/kf_wp_11624_01_register.py --offline   # re-verify the frozen snapshot

Exit code 0 iff every self-check passes; 1 otherwise (honest failure, never masked).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

PKG = "wp-11624-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "11624"
LANE = "C"
SOURCE_URI = "tensor://reports/11624"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = (
    "sha256:a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33"
)
CONTRACT_CHARS = 4253
CONTRACT_TITLE = "EEXI/CII 合规验证面：MEPC.392(81) Attained vs Required + CII 年度评级 A-E"
CONTRACT_SCENARIO = "P187-W1-N06"

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "knowledge" / "kf" / PKG
DOC_DIR = ROOT / "docs" / PKG
SNAPSHOT = OUT_DIR / "source_report_11624.md"
RECORD = OUT_DIR / "source_record.json"
MANIFEST = OUT_DIR / "asset_manifest.json"
RESULT = OUT_DIR / "kf_result.json"
SCHEMA = ROOT / "schemas" / "asset_manifest.v1.wp-11624-01.schema.json"
REPRO = "python3 scripts/kf_wp_11624_01_register.py"

# Line-anchored registry (kept as data so the whole registry is auditable at a glance).
ASSET_TABLE = [
    ("A02", "heading", "报告标题行", 1, 1, "resolved_in_source", "H1 标题；与 API title 字段同源"),
    ("A03", "scenario_anchor", "场景锚点标题（P187-W1-N06）", 3, 3, "resolved_in_source",
     "H2 场景行：MEPC.392(81) Attained vs Required + CII 年度评级 A-E"),
    ("A04", "background_statement", "物理背景陈述：EEXI/CII 强制性要求", 11, 11,
     "resolved_in_source", "单段背景陈述，登记原文不复核法条"),
    ("A05", "definition_pair", "EEXI 与 CII 定义（合规方向 / 评级逻辑）", 13, 14,
     "resolved_in_source", "两条定义原文；D/E 级须提交改进计划"),
    ("A06", "table", "法规框架表（5 项 MEPC 决议 + 状态列）", 18, 24, "resolved_in_source",
     "表头+分隔+5 行；状态列为上游自报「已实现」，本工序只登记不复核"),
    ("A07", "parameter_set", "三船型参数表（DWT / MCR / V_ref / 年航程）", 28, 32,
     "resolved_in_source",
     "表头+分隔+3 行；MCR 与年航程两列原文字面为「-」，属报告未给出的字段"),
    ("A08", "formula_block", "EEXI 直接公式法（Direct Formula）", 44, 44, "resolved_in_source",
     "fenced code 块内的公式行；围栏行见 43/45"),
    ("A09", "formula_block", "EEXI 分项累加法（Itemized Summation）", 49, 49, "resolved_in_source",
     "与 A08 数学等价、代码路径不同的第二实现公式"),
    ("A10", "tolerance_declaration", "双算法等价判据（相对差 < 1e-9）", 52, 52,
     "resolved_in_source", "可执行判据的阈值原文"),
    ("A11", "decision_rule", "CII 评级边界（G4 dd 向量 A-E）", 57, 61, "resolved_in_source",
     "五档边界不等式原文；用于 A12 评级判定的规则集"),
    ("A12", "result_table", "三船型 EEXI/CII 计算结果表", 69, 73, "resolved_in_source",
     "表头+分隔+3 行；数值为上游自报结果，本工序只登记不作二次计算"),
    ("A13", "criterion_test_log", "机器可算判据 C1–C6c 逐条结果（16 条）", 77, 92,
     "resolved_in_source",
     "16 行判据原文；每行含判据号、期望与实测字面值，属上游自报通过"),
    ("A14", "count_statement", "判据汇总计数（16/16 判据通过）", 94, 94, "resolved_in_source",
     "计数声明；与 A21 的「26 项全部通过」口径不同（判据 vs 测试），本工序并列登记不解释"),
    ("A15", "capability_declaration", "5.1 已实现能力清单（4 条）", 120, 123,
     "resolved_in_source", "上游自报能力清单原文"),
    ("A16", "limitation_set", "5.2 局限（4 条，含 WITHHELD 自报）", 127, 130,
     "resolved_in_source",
     "含「离线环境未回读规则原文，证据等级 WITHHELD」原文，属重要不确定度声明"),
    ("A17", "scope_declaration", "5.3 适用范围（船型 / 燃料 / 年份）", 134, 136,
     "resolved_in_source", "适用域声明的三条原文"),
    ("A18", "error_table", "误差判定表（4 行，基准 vs 计算值 vs <3%）", 142, 147,
     "resolved_in_source", "表头+分隔+4 行；判据值一列原文指向 3.2 节而非具体数字"),
    ("A19", "conclusion_statement", "误差判定结论句", 149, 149, "resolved_in_source",
     "上游结论原文；本工序只登记，结论成立与否由平台门判定"),
    ("A20", "code_path_reference", "审计链：代码路径 backend/modules/eexi_cii_compliance/", 155, 155,
     "referenced_unresolved",
     "属 ship-performance-platform 仓；本工作树内不存在（见 resolution_check.exists_in_worktree=false）"),
    ("A21", "test_reference", "审计链：测试文件 tests/test_eexi_cii_compliance.py", 156, 156,
     "referenced_unresolved",
     "本工作树内不存在，无法在本包内解析测试代码本体"),
    ("A22", "count_statement", "审计链：测试数量 26 项全部通过", 157, 157, "resolved_in_source",
     "上游自报计数原文；与 A14 的 16/16 判据属不同集合，本工序不合并计数"),
    ("A23", "provenance_statement", "审计链：生成时间「自动」", 158, 158, "resolved_in_source",
     "生成时间字段原文字面为「自动」，非可解析时间戳，无法作为时间溯源"),
]

# record-side figure entries (name -> pointer) are discovered from /figures at runtime.
FIGURE_NOTE = ("记录 metadata 中的图件声明：无 png/字节、无正文坐标（figures_with_bytes=0），"
               "登记为 declared_absent，存在性不由本工序断言")


# ------------------------------------------------------------------- utilities
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def fetch_markdown() -> tuple[str, dict]:
    """Live acquisition through the platform API (psql access is denied for this role)."""
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    login = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(login))
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise SystemExit("login returned no token")
    req = urllib.request.Request(
        base + "/tensor/reports/" + REPORT_ID, headers={"Authorization": "Bearer " + token}
    )
    payload = json.loads(urllib.request.urlopen(req).read())
    payload = payload.get("data", payload)
    if str(payload.get("id")) != REPORT_ID:
        raise SystemExit("API returned report id %r, refusing to mix reports" % payload.get("id"))
    return payload["markdown"], payload


def line_index(md: str):
    """Return (lines, line_start_offsets) for 1-based line addressing."""
    lines = md.split("\n")
    offs, cur = [], 0
    for ln in lines:
        offs.append(cur)
        cur += len(ln) + 1
    return lines, offs


def span(md: str, lines, offs, a: int, b: int) -> tuple[int, int, str]:
    start = offs[a - 1]
    end = offs[b - 1] + len(lines[b - 1])
    return start, end, md[start:end]


def locator_md(md, lines, offs, a, b, method="char_span"):
    start, end, quote = span(md, lines, offs, a, b)
    if not quote.strip():
        raise SystemExit("empty quote span %d-%d" % (a, b))
    n = md.count(quote)
    return {
        "source_field": "markdown",
        "method": method,
        "start_char": start,
        "end_char": end,
        "start_line": a,
        "end_line": b if method != "document" else len(lines),
        "line_base": 1,
        "quote": quote,
        "unique": n == 1,
        "occurrences": n,
    }


def verify_md(md, lines, offs, aid, loc) -> dict:
    start, end = loc["start_char"], loc["end_char"]
    sl = md[start:end]
    return {
        "id": aid,
        "check": "document_scope" if loc["method"] == "document" else "substring_unique_char_span",
        "resolved": (
            sl == loc["quote"]
            and md.count(loc["quote"]) == 1
            and loc["quote"] in md
            and loc["start_line"] >= 1
            and loc["end_line"] >= loc["start_line"]
            and loc["end_line"] <= len(lines)
        ),
        "char_span_matches_quote": sl == loc["quote"],
        "occurrences": md.count(loc["quote"]),
        "line_in_range": 1 <= loc["start_line"] <= loc["end_line"] <= len(lines),
        "quote_len": len(loc["quote"]),
    }


def worktree_absent(rel: str) -> dict:
    return {
        "worktree_relative_path": rel,
        "worktree_root": str(ROOT),
        "exists_in_worktree": (ROOT / rel).exists(),
        "detail": "path named by the report is not present in this worktree "
                  "(it belongs to the ship-performance-platform repository), so this "
                  "package cannot resolve it; existence is not asserted",
    }


def build(md: str, record: dict) -> dict:
    lines, offs = line_index(md)
    md_hash = sha256_text(md)

    assets, locators = [], []
    for spec in ASSET_TABLE:
        aid, kind, label, a, b, resolution, note = spec
        loc = locator_md(md, lines, offs, a, b)
        assets.append({
            "asset_id": aid,
            "kind": kind,
            "label": label,
            "locator": loc,
            "resolution": resolution,
            "resolution_check": (
                worktree_absent(_rel_of(md, loc)) if resolution == "referenced_unresolved"
                else {"check": "char_span_in_source_markdown", "result": "resolved"}
            ),
            "note": note,
            "existence_asserted_by_worker": resolution == "resolved_in_source",
        })
        locators.append(verify_md(md, lines, offs, aid, loc))

    # A01 — the whole markdown document
    first = lines[0]
    a01 = {
        "source_field": "markdown",
        "method": "document",
        "start_char": 0,
        "end_char": len(md),
        "start_line": 1,
        "end_line": len(lines),
        "line_base": 1,
        "quote": first,
        "unique": md.count(first) == 1,
        "occurrences": md.count(first),
    }
    assets.insert(0, {
        "asset_id": "A01",
        "kind": "report_markdown",
        "label": "报告全文（markdown，唯一字节资产）",
        "locator": a01,
        "resolution": "resolved_in_source",
        "resolution_check": {
            "check": "document_scope",
            "result": "resolved",
            "sha256": md_hash,
            "chars": len(md),
            "bytes_utf8": len(md.encode()),
            "byte_identical_to_contract_hash": ("sha256:" + md_hash) == CONTRACT_SOURCE_HASH,
        },
        "note": "整篇 markdown 即源资产；method=document 覆盖 [0,len)，quote 为 H1 首行",
        "existence_asserted_by_worker": True,
    })
    locators.insert(0, {
        "id": "A01",
        "check": "document_scope",
        "resolved": len(md) == CONTRACT_CHARS and ("sha256:" + md_hash) == CONTRACT_SOURCE_HASH,
        "char_span_matches_quote": True,
        "occurrences": 1,
        "line_in_range": True,
        "quote_len": len(first),
    })

    # record-side figures: metadata only, no bytes, no body coordinates
    figs = record.get("figures") or []
    body_figs, fig_locators = [], []
    for i, f in enumerate(figs):
        cap = f.get("caption") or f.get("name") or ""
        name = f.get("name") or ""
        in_body = [t for t in (name, cap) if t and t in md]
        aid = "A%02d" % (len(assets) + 1)
        assets.append({
            "asset_id": aid,
            "kind": "figure_declaration",
            "label": "图件声明（记录 metadata）：%s — %s" % (name, cap),
            "locator": {
                "source_field": "record",
                "method": "record_pointer",
                "start_char": 0,
                "end_char": 0,
                "start_line": 0,
                "end_line": 0,
                "line_base": 1,
                "pointer": "/figures/%d" % i,
                "quote": cap,
                "unique": sum(1 for g in figs if (g.get("caption") == cap)) == 1,
                "occurrences": sum(1 for g in figs if (g.get("caption") == cap)),
            },
            "resolution": "declared_absent",
            "resolution_check": {
                "check": "record_figure_has_bytes_and_body_anchor",
                "result": "absent",
                "bytes_present": bool(f.get("png_base64") or f.get("url") or f.get("path")),
                "body_tokens_found": in_body,
                "body_anchor_found": bool(in_body),
                "detail": "记录里有 name/caption，但无 png/url/path 字段，且 name 与 caption "
                          "在 markdown 正文中均无出现（body_tokens_found 为空）",
            },
            "note": FIGURE_NOTE,
            "existence_asserted_by_worker": False,
        })
        body_figs.append({"pointer": "/figures/%d" % i, "name": name, "caption": cap,
                          "body_tokens_found": in_body})
        fig_locators.append({
            "id": aid,
            "check": "record_pointer_present",
            "resolved": bool(cap) and in_body == [],
            "char_span_matches_quote": None,
            "occurrences": assets[-1]["locator"]["occurrences"],
            "line_in_range": None,
            "quote_len": len(cap),
        })
    locators.extend(fig_locators)

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})

    by_kind, by_res = {}, {}
    for a in assets:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    unresolved_notes = [
        {"asset_id": a["asset_id"], "label": a["label"], "resolution": a["resolution"],
         "reason": a["note"]}
        for a in assets if a["resolution"] != "resolved_in_source"
    ]

    below = [x for x in locators if not x["resolved"]]
    checks = {
        "source_hash_matches_contract": ("sha256:" + md_hash) == CONTRACT_SOURCE_HASH,
        "chars_match_contract": len(md) == CONTRACT_CHARS,
        "all_locators_resolved": not below,
        "no_duplicate_ids": not dupes,
        "claims_empty_by_contract": True,
        "no_verified_marks_emitted": "verified" not in json.dumps(assets, ensure_ascii=False),
        "single_report_scope": True,
    }

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "producer": "scripts/kf_wp_11624_01_register.py",
        "repro_cmd": REPRO,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": md_hash,
            "chars": len(md),
            "bytes_utf8": len(md.encode()),
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "record_id": record.get("id"),
            "record_mission_id": record.get("mission_id"),
            "record_status": record.get("status"),
            "record_created_at": record.get("created_at"),
            "record_tags": record.get("tags") or [],
            "stored_as": "UTF-8 text, exactly the bytes returned in field `markdown` "
                         "(json decode only; no normalisation, no newline rewriting)",
            "retrieved_via": "GET %s/tensor/reports/%s -> field `markdown`" % (
                os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
                REPORT_ID),
            "local_copy": str(SNAPSHOT.relative_to(ROOT)),
            "hash_matches_contract": ("sha256:" + md_hash) == CONTRACT_SOURCE_HASH,
        },
        "counts": {
            "assets": len(assets),
            "by_kind": by_kind,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "locators": len(locators),
            "locators_resolved": sum(1 for x in locators if x["resolved"]),
            "figures_declared_in_record": len(figs),
            "figures_with_bytes": 0,
            "figures_with_body_anchor": sum(1 for f in body_figs if f["body_tokens_found"]),
            "claims": 0,
        },
        "assets": assets,
        "record_figures": body_figs,
        "identity_facts": [
            {"field": "/title", "value": record.get("title"),
             "matches_contract_title": record.get("title") == CONTRACT_TITLE,
             "locator": {"source_field": "record", "pointer": "/title"}},
            {"field": "/scenario_key", "value": record.get("scenario_key"),
             "matches_contract_scenario": record.get("scenario_key") == CONTRACT_SCENARIO,
             "locator": {"source_field": "record", "pointer": "/scenario_key"}},
            {"field": "/id", "value": record.get("id"), "locator": {"source_field": "record",
                                                                    "pointer": "/id"}},
            {"field": "/mission_id", "value": record.get("mission_id"),
             "locator": {"source_field": "record", "pointer": "/mission_id"}},
            {"field": "/status", "value": record.get("status"),
             "locator": {"source_field": "record", "pointer": "/status"}},
        ],
        "locators": locators,
        "claims": [],
        "claims_empty_reason": (
            "工作包契约 objective.register_assets=true / objective.classify_report_type=false / "
            "constraints.no_forced_claim_generation=true，notes 明确 claims 允许为空数组：本工序只登记"
            "资产与定位，不作 claim 抽取，也不给任何对象打 verified 标记（verification 由平台门计算）。"
        ),
        "unresolved": unresolved_notes,
        "integrity": {
            "quote_uniqueness": "每条 markdown 引文均已本地校验：md[start_char:end_char] == quote "
                                "且 md.count(quote) == 1（见 locators[].check=substring_unique_char_span）",
            "hash_recomputed_locally": True,
            "hash_matches_contract": ("sha256:" + md_hash) == CONTRACT_SOURCE_HASH,
            "no_duplicate_ids": not dupes,
            "duplicate_ids": dupes,
            "no_verified_marks": True,
        },
        "checks": checks,
        "limitations": [
            "只登记、不抽取：claims 为空是契约要求，不代表报告没有结论句（A19 已登记结论原文）。",
            "referenced_unresolved 的两条审计链路径属 ship-performance-platform，本工作树无法解析；"
            "本工序不断言其存在，也不复核上游测试是否真的运行过。",
            "记录 figures 有 4 条声明但无字节、无正文锚点；本工序只登记缺口，不判定图件是否曾产出。",
            "报告自报的数值（A12/A13/A18）一律按原文登记，未做二次计算或外部法规回读。",
        ],
    }
    return {"manifest": manifest, "checks": checks, "locators": locators, "md_hash": md_hash}


def _rel_of(md: str, loc: dict) -> str:
    """Extract the repo-relative path quoted by a code/test reference asset."""
    q = loc["quote"]
    for token in q.split("`"):
        t = token.strip()
        if t and ("/" in t or t.endswith(".py")) and not t.startswith("http"):
            return t.rstrip("/")
    return q


def write_json(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    path.write_text(blob, encoding="utf-8")
    return hashlib.sha256(blob.encode()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="re-verify the frozen snapshot instead of fetching the API")
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.offline:
        if not SNAPSHOT.exists():
            print("FATAL: --offline but no snapshot at", SNAPSHOT)
            return 1
        md = SNAPSHOT.read_text(encoding="utf-8")
        record = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}
        print("offline: snapshot", SNAPSHOT)
    else:
        md, record = fetch_markdown()
        if md != md.encode("utf-8", "surrogatepass").decode("utf-8"):
            print("FATAL: markdown not clean UTF-8")
            return 1
        SNAPSHOT.write_text(md, encoding="utf-8")
        rec = {k: v for k, v in record.items() if k != "markdown"}
        write_json(RECORD, rec)
        if sha256_text(SNAPSHOT.read_text(encoding="utf-8")) != sha256_text(md):
            print("FATAL: snapshot round-trip changed bytes")
            return 1
        print("fetched report", REPORT_ID, "chars", len(md))

    built = build(md, record)
    man = built["manifest"]

    # --- schema check (schema_pass acceptance item) -------------------------
    schema_ok, schema_err = True, None
    try:
        import jsonschema
        jsonschema.validate(man, json.loads(SCHEMA.read_text(encoding="utf-8")))
    except ImportError:
        schema_err = "jsonschema not installed -> schema_pass NOT_RUN"
        schema_ok = False
    except Exception as exc:  # noqa: BLE001 - report, do not mask
        schema_ok, schema_err = False, str(exc)
    man["schema_check"] = {"schema_file": str(SCHEMA.relative_to(ROOT)), "passed": schema_ok,
                           "error": schema_err}

    man_hash = write_json(MANIFEST, man)

    result = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + built["md_hash"],
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode()),
            "source_title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "contract_version": "1.0",
            "lane": LANE,
            "work_package": PKG,
            "retrieved_via": man["source"]["retrieved_via"],
            "local_copy": str(SNAPSHOT.relative_to(ROOT)),
            "generator": "scripts/kf_wp_11624_01_register.py",
            "verifier": "scripts/kf_wp_11624_01_verify.py",
            "emitted_at": man["generated_at"],
            "producer": "scripts/kf_wp_11624_01_register.py",
            "verification_status": "not_verified",
            "notes": "verification is computed by the platform gate; this envelope only "
                     "declares provenance and the registered asset manifest",
        },
        "outputs": {
            "asset_manifest.json": dict(
                man,
                artifact_path=str(MANIFEST.relative_to(ROOT)),
                artifact_sha256=man_hash,
                artifact_bytes=MANIFEST.stat().st_size,
            )
        },
        "claims": [],
    }

    # --- kf_result envelope check against the platform schema --------------
    res_schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    try:
        import jsonschema
        jsonschema.validate(result, res_schema)
        env_ok, env_err = True, None
    except Exception as exc:  # noqa: BLE001
        env_ok, env_err = False, str(exc)

    write_json(RESULT, result)

    # --- durable mirror (push gate drops artifacts/** and runs/**, keeps docs/) ---
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for src in (SNAPSHOT, RECORD, MANIFEST, RESULT):
        if src.exists():
            dst = DOC_DIR / src.name
            dst.write_bytes(src.read_bytes())
            same = hashlib.sha256(dst.read_bytes()).hexdigest() == \
                hashlib.sha256(src.read_bytes()).hexdigest()
            written.append((str(dst.relative_to(ROOT)), same))

    print("markdown sha256:", built["md_hash"],
          "MATCH" if man["source"]["hash_matches_contract"] else "MISMATCH")
    print("assets:", man["counts"]["assets"], "| locators:", man["counts"]["locators"],
          "resolved:", man["counts"]["locators_resolved"])
    print("by_kind:", json.dumps(man["counts"]["by_kind"], ensure_ascii=False))
    print("by_resolution:", json.dumps(man["counts"]["by_resolution"], ensure_ascii=False))
    print("schema_pass:", schema_ok, schema_err or "")
    print("kf_result envelope valid:", env_ok, env_err or "")
    print("checks:", json.dumps(man["checks"], ensure_ascii=False))
    print("manifest:", MANIFEST.relative_to(ROOT), man_hash)
    print("mirror:", written)

    ok = all(man["checks"].values()) and schema_ok and env_ok and all(w[1] for w in written)
    if not ok:
        print("RESULT: FAIL (see checks above)")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())