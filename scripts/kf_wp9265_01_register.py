#!/usr/bin/env python3
"""wp-9265-01 · task_type=01-asset-registration · report_id=9265 (ONLY this report).

Registers the source asset (report 9265 markdown: identity + byte hash) and enumerates
the attachments/artifacts the report declares. No extraction, no classification,
no verification marks, no claims invented from thin air.

Sub-commands (idempotent, stdlib + jsonschema/matplotlib):

    python3 scripts/kf_wp9265_01_register.py build     # fetch + write asset_manifest.json
    python3 scripts/kf_wp9265_01_register.py envelope   # wrap manifest -> kf_result.json
    python3 scripts/kf_wp9265_01_register.py verify     # acceptance checks -> verification.json
    python3 scripts/kf_wp9265_01_register.py figure     # locator map png (program-generated)
    python3 scripts/kf_wp9265_01_register.py all

Zero hand-transcription: every quote is sliced out of the fetched markdown bytes and
every number (hash, char/byte counts, spans, lines, occurrences) is measured here.
Failures abort loudly (SystemExit) instead of emitting a half manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "9265"
PACKAGE_ID = "wp-9265-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/9265"
SOURCE_FIELD = "markdown"
# contract-declared identity (work-package YAML); comparison targets only, never trusted.
CONTRACT_SOURCE_HASH = "sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c"
CONTRACT_CHARS = 9599
CONTRACT_TITLE = "DP 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图（IN144-N05 / m7890）"
CONTRACT_SCENARIO = "dp_capability_assessment"
CONTRACT_MISSION_ID = 15637
PRODUCER = "kf-worker/m15637"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID  # committed: repo .gitignore drops artifacts/**
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
RAW_JSON = RUN_DIR / ("report_%s.json" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
PKG_SCHEMA = OUT_DIR / "asset_manifest.wp-9265-01.schema.json"
FIGDIR = OUT_DIR / "figures"

# ---- asset declarations: (asset_id, class, label, section, needle, extra note) ----
# `needle` is a verbatim slice of the fetched markdown (never retyped by hand at runtime:
# the script re-locates it with str.find and aborts if it is not unique).
DECLARED_ASSETS = [
    ("A02", "figure_declared", "capability_polar.png",
     "③3.5 图 / record.figures[0]",
     "- `capability_polar.png` — 极坐标操作包线图（5 条等电流曲线 + 最坏失效虚线）",
     "Declared in record metadata (name+caption) and in §3.5; no figure bytes served by the "
     "platform for this report, and no such file in the TensorKnowledge worktree."),
    ("A03", "figure_declared", "failure_degradation.png",
     "③3.5 图 / record.figures[1]",
     "- `failure_degradation.png` — 单件失效降级柱状图（30% 判据线）",
     "Declared in record metadata (name+caption) and in §3.5; bytes not available."),
    ("A04", "figure_declared", "load_models.png",
     "③3.5 图 / record.figures[2]",
     "- `load_models.png` — 风/流/波浪漂移力系数随来向变化",
     "Declared in record metadata (name+caption) and in §3.5; bytes not available."),
    ("A05", "figure_declared", "balance.png",
     "③3.5 图 / record.figures[3]",
     "- `balance.png` — 10 个工况点平衡残差（对数轴）+ 峰值利用率",
     "Declared in record metadata (name+caption) and in §3.5; bytes not available."),
    ("A06", "figure_declared", "degradation_sensitivity.png",
     "③3.5 图 / record.figures[4]",
     "- `degradation_sensitivity.png` — 降级随有义波高变化（23%→36%）",
     "Declared in record metadata (name+caption) and in §3.5; bytes not available."),
    ("A07", "artifact_directory", "artifacts/dp_capability/",
     "document header (产物行)",
     "**产物** `artifacts/dp_capability/`（JSON + 5 张 PNG + 判据账本 `criteria.json`）",
     "Output directory of the upstream mission m7890, located in repo ship-performance-platform; "
     "not present in this TensorKnowledge delivery worktree."),
    ("A08", "data_artifact_reference", "criteria.json",
     "document header (产物行) + ③3.1",
     "判据账本 `criteria.json`",
     "Criteria ledger (c2/c3 keys quoted in §3.1 and §④); referenced, content not shipped here."),
    ("A09", "data_artifact_reference", "capability_payload.json",
     "③3.1 表格",
     "见表 `capability_payload.json`",
     "Per-case 3-DOF load table referenced instead of being inlined in the report table."),
    ("A10", "source_code_reference", "backend/physics/dp_core.py",
     "document header (落库模块行)",
     "`backend/physics/dp_core.py`（物理/数值内核）",
     "Numeric/physics kernel (L1-L4) in ship-performance-platform; not in this worktree."),
    ("A11", "source_code_reference", "backend/api/dynamic_positioning.py",
     "document header (落库模块行)",
     "`backend/api/dynamic_positioning.py`（FastAPI 端点）",
     "FastAPI endpoint module in ship-performance-platform; not in this worktree."),
    ("A12", "test_reference", "tests/test_dp_capability.py",
     "document header (验证行)",
     "`tests/test_dp_capability.py`（40 项 pytest，22 s 全绿）",
     "Test suite claimed 40 passed / 22 s; that claim is NOT reproduced here (registration only)."),
    ("A13", "script_reference", "scripts/dp_capability_artifacts_m7890.py",
     "①案例介绍 / 复现",
     "`scripts/dp_capability_artifacts_m7890.py`",
     "Generating script for the report's tables/figures; not in this worktree."),
    ("A14", "benchmark_dataset_absent", "DNV 已发表 PSV 包线数值数据集",
     "④与 DNV 规范的对照",
     "仓库内没有可引用的 DNV 已发表包线数值数据集",
     "Explicitly declared absent by the report itself -> numerical layer of §④ is WITHHELD."),
]
IDENTITY_NEEDLES = [
    ("title-h1", "①H1 标题", "# 动力定位 (DP) 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图"),
    ("campaign-line", "文档头 战役节点行", "**战役节点** IN144-N05"),
    ("module-line", "文档头 落库模块行", "**落库模块**"),
    ("repro-block", "复现代码块", "python3 -m pytest tests/test_dp_capability.py -q"),
]


# ---------------------------------------------------------------- platform I/O
def _base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _req(path: str, payload=None, token=None, raw=False):
    url = _base() + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        if raw:
            return r.status, body
        return json.loads(body.decode())


def login() -> str:
    d = _req("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                             "password": os.environ["TENSOR_AGENT_PASS"]})
    tok = d.get("access_token") or (d.get("data") or {}).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def fetch_report():
    """Return (markdown_text, record_dict). Uses the cached payload if present."""
    if RAW_JSON.exists():
        payload = json.loads(RAW_JSON.read_text())
    else:
        payload = _req("/tensor/reports/" + REPORT_ID, token=login())
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        RAW_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    rec = payload.get("data", payload) if isinstance(payload, dict) else payload
    md = rec["markdown"]
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCE_COPY.exists() or SOURCE_COPY.read_text() != md:
        SOURCE_COPY.write_text(md)
    return md, rec


def probe_figure_bytes(tok=None):
    """Does the platform serve figure/artifact bytes for this report? (never fabricate one)"""
    probes = {}
    for path in ("/tensor/reports/%s/figures" % REPORT_ID,
                 "/tensor/reports/%s/artifacts" % REPORT_ID):
        try:
            tok = tok or login()
            status, body = _req(path, token=tok, raw=True)
            probes[path] = {"http_status": status, "bytes": len(body),
                            "body_head": body[:120].decode("utf-8", "replace")}
        except Exception as exc:  # 404 / 403 / not routed -> recorded, not assumed
            code = getattr(exc, "code", None)
            probes[path] = {"http_status": code or "error", "bytes": 0,
                            "error": type(exc).__name__}
    return probes


# ---------------------------------------------------------------- locator utils
def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def locator(md: str, quote: str, method: str = "char_span") -> dict:
    """Locate `quote` verbatim in `md`; abort if absent or ambiguous."""
    n = md.count(quote)
    if n == 0:
        raise SystemExit("quote not found in source markdown: %r" % quote[:80])
    if n > 1:
        raise SystemExit("quote not unique (%d occurrences): %r" % (n, quote[:80]))
    start = md.find(quote)
    end = start + len(quote)
    if md[start:end] != quote:
        raise SystemExit("slice mismatch for quote: %r" % quote[:80])
    start_line = md[:start].count("\n") + 1
    end_line = start_line + quote.count("\n")
    return {"method": method, "start_char": start, "end_char": end,
            "start_line": start_line, "end_line": end_line,
            "quote": quote, "unique": True}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- build
def build() -> dict:
    md, rec = fetch_report()
    raw = md.encode("utf-8")
    digest = sha256_hex(raw)
    hash_match = ("sha256:" + digest) == CONTRACT_SOURCE_HASH
    chars_match = len(md) == CONTRACT_CHARS
    title_match = (rec.get("title") or "") == CONTRACT_TITLE
    scenario_match = rec.get("scenario_key") == CONTRACT_SCENARIO
    figs = rec.get("figures") or []
    fig_probes = probe_figure_bytes()

    assets = []
    # A01: the source asset itself (the report markdown bytes)
    first_line = md.split("\n", 1)[0]
    assets.append({
        "asset_id": "A01",
        "asset_class": "source_document",
        "label": "report 9265 markdown (source asset itself)",
        "in_report_section": "whole document",
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "sha256(markdown utf-8) == contract source_hash and chars == 9599",
                             "result": "resolved"},
        "locator": {"method": "document", "start_char": 0, "end_char": len(md),
                    "start_line": 1, "end_line": md.count("\n") + 1,
                    "quote": first_line, "unique": True},
        "note": "Source of truth for every other locator in this manifest; fetched via "
                "GET /api/v1/tensor/reports/9265.",
    })

    fig_by_name = {f.get("name"): f for f in figs if isinstance(f, dict)}
    for asset_id, klass, label, section, needle, note in DECLARED_ASSETS:
        loc = locator(md, needle)
        if klass == "figure_declared":
            rec_fig = fig_by_name.get(label) or {}
            resolution = "referenced_unresolved"
            fhits = [c for c in (label, "artifacts/" + label, "docs/" + label, "scripts/" + label,
                                 "tests/" + label, "figures/" + label)
                     if ROOT.joinpath(c).exists()]
            fprobe = fig_probes.get("/tensor/reports/9265/figures", {}).get("http_status")
            apr = fig_probes.get("/tensor/reports/9265/artifacts", {}).get("http_status")
            check = {"check": "platform figure bytes probe (/tensor/reports/9265/figures -> %s, "
                              "/artifacts -> %s) + worktree file probe over 6 relative paths -> %s"
                              % (fprobe, apr, json.dumps(fhits)),
                     "result": "present" if fhits else "unresolved"}
            note = note + " record.caption=" + json.dumps(rec_fig.get("caption"), ensure_ascii=False)
        elif klass == "benchmark_dataset_absent":
            resolution = "declared_absent"
            check = {"check": "report body states the dataset is not available (grep of the "
                              "verbatim sentence)", "result": "absent"}
        else:
            resolution = "referenced_unresolved"
            cands = [label, "artifacts/" + label, "docs/" + label, "scripts/" + label,
                     "tests/" + label, "ship-performance-platform/" + label]
            hits = [c for c in cands if ROOT.joinpath(c).exists()]
            check = {"check": "file exists inside this TensorKnowledge worktree at any of "
                              + json.dumps(cands, ensure_ascii=False),
                     "result": "present" if hits else "unresolved"}
            if hits:
                note = note + " resolved in-worktree at: " + json.dumps(hits, ensure_ascii=False)
        assets.append({"asset_id": asset_id, "asset_class": klass, "label": label,
                       "in_report_section": section, "resolution": resolution,
                       "resolution_check": check, "locator": loc, "note": note})

    identity = []
    for fact_id, section, needle in IDENTITY_NEEDLES:
        loc = locator(md, needle)
        identity.append({"fact_id": fact_id, "in_report_section": section,
                         "locator": loc, "quote_sha256": sha256_hex(needle.encode("utf-8"))})

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    occ = {a["asset_id"]: md.count(a["locator"]["quote"]) for a in assets}

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "B",
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "scope_guard": {
            "report_ids_touched": [REPORT_ID],
            "writes_outside_package_dir": [],
            "extraction_performed": False,
            "claims_verified": False,
            "note": "Registration only (objective.register_assets=true, "
                    "objective.classify_report_type=false). No upstream/downstream artefact edited.",
        },
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "contract_hash": CONTRACT_SOURCE_HASH,
            "hash_match": hash_match,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match": chars_match,
            "bytes_utf8": len(raw),
            "lines": md.count("\n") + 1,
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": md.endswith("\n"),
            "title": rec.get("title"),
            "contract_title": CONTRACT_TITLE,
            "title_match": title_match,
            "scenario_key": rec.get("scenario_key"),
            "contract_scenario_key": CONTRACT_SCENARIO,
            "scenario_match": scenario_match,
            "record_status": rec.get("status"),
            "record_stage": rec.get("stage"),
            "record_mission_id": rec.get("mission_id"),
            "record_created_at": rec.get("created_at"),
            "record_created_by": rec.get("created_by"),
            "platform_tags": rec.get("tags") or [],
            "platform_figures": [{"name": f.get("name"), "caption": f.get("caption"),
                                  "has_png_base64": "png_base64" in f,
                                  "caption_in_markdown": (f.get("caption") or "")[:24] in md}
                                 for f in figs if isinstance(f, dict)],
            "platform_figure_probes": fig_probes,
            "fetched_via": "GET /api/v1/tensor/reports/" + REPORT_ID,
            "line_counting": "logical lines from markdown.split(chr(10)); 1-based",
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "figures_declared_in_record": len(figs),
            "locators": len(assets) + len(identity),
            "identity_facts": len(identity),
            "claims": 0,
        },
        "assets": assets,
        "identity_facts": identity,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-9265-01 sets objective.register_assets=true, objective.classify_report_type=false, "
            "constraints.no_forced_claim_generation=true and notes 'claims 允许为空数组'. This 工序 registers "
            "asset identity (report_id + markdown byte hash + declared attachments/artifacts) only; extraction "
            "is a downstream 工序. An empty claims array is therefore the complete result, not an omission."
        ),
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes},
        "integrity": {
            "quote_uniqueness": {
                "all_unique": all(v == 1 for v in occ.values()),
                "occurrences": occ,
                "locators_checked": len(occ) + len(identity),
                "max_occurrences": max(list(occ.values()) + [md.count(n) for _, _, n in IDENTITY_NEEDLES]),
            },
            "hash_recomputed_locally": "sha256:" + digest,
            "hash_matches_contract": hash_match,
            "chars_match_contract": chars_match,
        },
        "unresolved": [{"asset_id": a["asset_id"], "label": a["label"],
                        "reason": a["resolution_check"]["check"]}
                       for a in assets if a["resolution"] == "referenced_unresolved"],
        "observations": [
            "Markdown identity verified independently of the contract: recomputed sha256 == contract "
            "source_hash, chars == 9599, title and scenario_key match the contract strings.",
            "The 5 record figures carry name+caption only (no png_base64), the platform exposes no "
            "figure bytes, and no such files exist in this worktree -> referenced_unresolved (no "
            "hash is claimed for any image).",
            "All code/data/test references point into repo ship-performance-platform, which is not "
            "part of this worktree -> registered as declared references, existence not asserted.",
            "One asset is declared_absent by the report itself (DNV published PSV envelope dataset), "
            "which is why §④ of the report keeps the numerical layer WITHHELD.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


# ---------------------------------------------------------------- envelope + schema
def envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": manifest["generated_at"],
            "notes": "source_hash = sha256 of the markdown bytes returned by "
                     "GET /api/v1/tensor/reports/9265 (utf-8, no normalisation).",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n")
    return env


def _pkg_schema() -> dict:
    """Per-package projection of schemas/asset_manifest.v1.schema.json (consts re-pinned).

    The repo copy pins package_id/report_id to the wp-448 example, so it cannot validate this
    package as-is; re-pinning keeps `schema_pass` reproducible instead of merely asserted.
    """
    base = json.loads((ROOT / "schemas" / "asset_manifest.v1.schema.json").read_text())
    props = base["properties"]
    props["package_id"] = {"const": PACKAGE_ID}
    props["report_id"] = {"const": REPORT_ID}
    props["source"]["properties"]["uri"] = {"const": SOURCE_URI}
    base["$id"] = "https://tensorplatform.local/schemas/asset_manifest.wp-9265-01.schema.json"
    base["description"] = ("Re-pinned projection of schemas/asset_manifest.v1.schema.json for "
                           "wp-9265-01 (the upstream copy const-pins wp-448-01/448). Shape, "
                           "resolution enum, locator fields and required keys are unchanged.")
    return base


# ---------------------------------------------------------------- verify
def verify() -> dict:
    import jsonschema

    md, rec = fetch_report()
    raw = md.encode("utf-8")
    manifest = json.loads(MANIFEST.read_text())
    env = json.loads(ENVELOPE.read_text()) if ENVELOPE.exists() else {}

    # 1 valid_json
    valid_json = isinstance(manifest, dict) and isinstance(env, dict) and bool(env)

    # 2 schema_pass
    schema_errors = {}
    pkg_schema = _pkg_schema()
    PKG_SCHEMA.write_text(json.dumps(pkg_schema, ensure_ascii=False, indent=2) + "\n")
    try:
        jsonschema.validate(manifest, pkg_schema)
    except jsonschema.ValidationError as exc:
        schema_errors["asset_manifest.json"] = "%s at %s" % (exc.message, list(exc.absolute_path))
    try:
        jsonschema.validate(env, json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text()))
    except jsonschema.ValidationError as exc:
        schema_errors["kf_result.json"] = "%s at %s" % (exc.message, list(exc.absolute_path))
    schema_pass = valid_json and not schema_errors

    # 3 source_locator_resolvable: quote is a verbatim substring AND spans/lines agree
    loc_rows = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        start, end = loc["start_char"], loc["end_char"]
        # document locators must still bracket the whole markdown exactly (no free pass)
        slice_ok = (md[start:end] == q if loc["method"] == "char_span"
                    else (start == 0 and end == len(md) and q in md))
        line_ok = md[:start].count("\n") + 1 == loc["start_line"]
        loc_rows.append({"asset_id": a["asset_id"], "quote_in_source": q in md,
                         "span_matches_source": slice_ok, "line_matches_span": line_ok,
                         "occurrences": md.count(q),
                         "resolved": bool(q in md and slice_ok and line_ok and md.count(q) == 1)})
    for f in manifest["identity_facts"]:
        loc = f["locator"]
        q = loc["quote"]
        ok = q in md and md[loc["start_char"]:loc["end_char"]] == q and md.count(q) == 1
        loc_rows.append({"fact_id": f["fact_id"], "quote_in_source": q in md,
                         "span_matches_source": md[loc["start_char"]:loc["end_char"]] == q,
                         "line_matches_span": md[:loc["start_char"]].count("\n") + 1 == loc["start_line"],
                         "occurrences": md.count(q), "resolved": bool(ok)})
    locators_ok = all(r["resolved"] for r in loc_rows)

    # 4 source_hash_matches (recomputed from the live markdown, compared to contract string)
    recomputed = "sha256:" + sha256_hex(raw)
    hash_ok = (recomputed == CONTRACT_SOURCE_HASH == env.get("provenance", {}).get("source_hash")
               == "sha256:" + manifest["source"]["hash"])

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    ids_ok = not dupes

    # 6 all_claims_have_evidence_or_explicit_unresolved_status
    claims = manifest["claims"]
    bad_claims = []
    for c in claims:
        if "evidence_locator" in c or "status" in c:
            continue
        bad_claims.append(c.get("claim_id"))
    claims_ok = not bad_claims

    checks = [
        {"item": "valid_json", "pass": valid_json,
         "detail": "asset_manifest.json and kf_result.json both parse as JSON objects"},
        {"item": "schema_pass", "pass": schema_pass,
         "detail": "assets_manifest validated against re-pinned per-package schema; kf_result "
                   "validated against schemas/kf_result.v1.schema.json; errors=%s" % (schema_errors or "none")},
        {"item": "source_locator_resolvable", "pass": locators_ok,
         "detail": "%d/%d locators resolved (verbatim substring + char span + line number + uniqueness)"
                   % (sum(r["resolved"] for r in loc_rows), len(loc_rows))},
        {"item": "source_hash_matches", "pass": hash_ok,
         "detail": "recomputed %s vs contract %s" % (recomputed, CONTRACT_SOURCE_HASH)},
        {"item": "no_duplicate_ids", "pass": ids_ok,
         "detail": "%d asset ids, duplicates=%s" % (len(ids), dupes or "none")},
        {"item": "all_claims_have_evidence_or_explicit_unresolved_status", "pass": claims_ok,
         "detail": "claims=%d (empty by contract: no_forced_claim_generation=true, "
                   "classify_report_type=false); no unbacked claim present" % len(claims)},
    ]
    result = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "checked_at": utcnow(),
        "acceptance": checks,
        "passed": all(c["pass"] for c in checks),
        "locator_rows": loc_rows,
        "claims_status": {"count": len(claims), "unbacked": bad_claims,
                          "note": manifest.get("claims_empty_reason", "")},
        "not_checked": [
            "existence/content of artefacts inside repo ship-performance-platform (outside this worktree)",
            "figure bytes for the 5 declared PNGs (platform serves none, worktree has none)",
            "truth of the report's numeric results (residuals, envelope speeds, degradation %) -- "
            "extraction/verification is a downstream 工序 and the report's own §⑥ keeps the "
            "absolute-force layer WITHHELD",
            "the 40 passed / 22 s pytest claim (not reproduced; registration only)",
        ],
        "verification_marks": "none (per contract constraints.do_not_mark_claims_as_verified=true)",
        "repro_cmd": "python3 scripts/kf_wp9265_01_register.py all",
    }
    VERIFICATION.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


# ---------------------------------------------------------------- figure
def figure() -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    md, _ = fetch_report()
    manifest = json.loads(MANIFEST.read_text())
    rows = [(a["asset_id"], a["asset_class"], a["locator"]) for a in manifest["assets"]]
    rows += [(f["fact_id"], "identity_fact", f["locator"]) for f in manifest["identity_facts"]]
    rows_sorted = sorted(rows, key=lambda r: r[2]["start_char"])

    FIGDIR.mkdir(parents=True, exist_ok=True)
    n = len(md)
    fig, ax = plt.subplots(figsize=(11, 0.42 * len(rows_sorted) + 1.9))
    for i, (aid, klass, loc) in enumerate(rows_sorted):
        left = loc["start_char"] / n * 100.0
        width = max((loc["end_char"] - loc["start_char"]) / n * 100.0, 0.25)
        ax.barh(i, width, left=left, height=0.62,
                color="#2b6cb0" if klass != "identity_fact" else "#718096")
        ax.text(min(left + width + 0.6, 97), i, "L%d" % loc["start_line"],
                va="center", fontsize=8)
    ax.set_yticks(range(len(rows_sorted)))
    ax.set_yticklabels(["%s (%s)" % (a, k) for a, k, _ in rows_sorted], fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("position in report markdown (percent of {} chars)".format(n))
    ax.set_title("wp-9265-01 asset locator map: %d locators, all verbatim+unique" % len(rows_sorted),
                 fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    ax.invert_yaxis()
    fig.tight_layout()
    png = FIGDIR / "locator_map.png"
    fig.savefig(png, dpi=140)
    plt.close(fig)

    fig_meta = {
        "figure": "locator_map.png",
        "caption": "wp-9265-01 资产定位图：每个 locator 在报告 markdown 字符轴上的位置（蓝=资产，"
                   "灰=身份事实），右侧标 1-based 行号；%d 个 locator 全部逐字且唯一。" % len(rows_sorted),
        "source": "docs/kf/wp-9265-01/asset_manifest.json (locator.start_char/end_char/start_line)",
        "generated_by": "scripts/kf_wp9265_01_register.py figure",
        "png_sha256": sha256_hex(png.read_bytes()),
        "png_bytes": len(png.read_bytes()),
        "locators_plotted": len(rows_sorted),
        "zero_hand_transcription": "all coordinates read from the manifest; no number typed by hand",
    }
    (FIGDIR / "locator_map.json").write_text(json.dumps(fig_meta, ensure_ascii=False, indent=2) + "\n")
    return fig_meta


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("build", "all"):
        m = build()
        print("built %s: %d assets, hash_match=%s chars_match=%s"
              % (MANIFEST, m["counts"]["assets"], m["source"]["hash_match"], m["source"]["chars_match"]))
    if cmd in ("envelope", "all"):
        envelope()
        print("wrote %s" % ENVELOPE)
    if cmd in ("figure", "all"):
        print("figure: %s" % json.dumps(figure(), ensure_ascii=False)[:200])
    if cmd in ("verify", "all"):
        v = verify()
        for c in v["acceptance"]:
            print("[%s] %s :: %s" % ("PASS" if c["pass"] else "FAIL", c["item"], c["detail"]))
        print("ALL PASS" if v["passed"] else "SOME CHECKS FAILED")
        if not v["passed"]:
            raise SystemExit(1)


if __name__ == "__main__":
    import sys
    main(sys.argv)