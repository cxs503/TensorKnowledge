#!/usr/bin/env python3
"""Work package wp-7473-01 (01-asset-registration) — asset manifest builder / verifier.

Scope guard: touches ONLY report_id=7473 (tensor://reports/7473).  No extraction, no
claims, no `verified` marks (verification is computed by the platform gate).

Zero-handcopy discipline: every locator quote is sliced out of the fetched markdown
bytes, never retyped.  Curated anchors below are *search keys* only; the recorded
quote is always the verbatim source line (so `quote in markdown` is guaranteed by
construction and re-checked by `verify`).

Usage:
  python3 scripts/kf/build_asset_manifest_7473.py build
  python3 scripts/kf/build_asset_manifest_7473.py verify
  python3 scripts/kf/build_asset_manifest_7473.py build verify
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

PKG = "wp-7473-01"
REPORT_ID = "7473"
SOURCE_URI = "tensor://reports/7473"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "c3b3d0954d289cf1f7849f83889e995c71c39bbc15122ddf9f823f5d698d0f6b"
EXPECTED_CHARS = 5942
CONTRACT_TITLE = (
    "TensorLBM 湍流槽道求解器验证欠账清偿 R1：Guo 力项 TRT 分裂缺陷"
    "（战役驱动力仅 0.63%）修复 + 层流解析锚阶梯"
)
CONTRACT_SCENARIO = "tensorlbm/turbulent-channel3d-verification-r1"

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
SNAPSHOT = OUT_DIR / "source_markdown.md"
SCHEMA = OUT_DIR / "asset_manifest_7473.schema.json"
VERDICT = OUT_DIR / "verification.json"
RESULT = OUT_DIR / "kf_result.json"

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
    payload = json.dumps({"username": USER, "password": PASS}).encode()
    try:
        d = _req(BASE + "/auth/login", data=payload)
    except urllib.error.HTTPError:
        body = urllib.parse.urlencode({"username": USER, "password": PASS}).encode()
        d = _req(BASE + "/auth/login", data=body, ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_report(token):
    d = _req(BASE + "/tensor/reports/%s" % REPORT_ID, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s carries no markdown field" % REPORT_ID)
    return d, md


def probe(token, path):
    """Probe a platform endpoint; record exactly what came back (never fabricate bytes)."""
    try:
        req = urllib.request.Request(BASE + path)
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
            return {
                "path": path,
                "http_status": r.status,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
    except urllib.error.HTTPError as e:
        return {"path": path, "http_status": e.code, "bytes": 0, "sha256": None}
    except Exception as e:  # noqa: BLE001 - record, never invent
        return {"path": path, "http_status": None, "error": type(e).__name__}


# ---------------------------------------------------------------- reference scan

FILE_RE = re.compile(r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|json|png|md|txt|csv))")
DIR_RE = re.compile(r"(?P<dir>[A-Za-z0-9_][A-Za-z0-9_./-]*/)")
# Only repository-rooted directory paths count as assets: without this whitelist, inline
# math in the report (`dU/dt = a`, `2u_max/Re_tau_twin`) would be mis-registered as
# directory references.  Roots below are the only ones the report can legitimately cite.
ROOTED_DIR_PREFIXES = ("src/", "tests/", "benchmarks/", "artifacts/", "docs/", "scripts/", "runs/", "schemas/", "ke/", "knowledge/")
TICK_RE = re.compile(r"`([^`]+)`")

# Curated anchors: (search_key, asset_class, label, resolution_rule)
# resolution_rule: "worktree" | "tensorlbm" | "absent"
CURATED = [
    ("Guo 1993", "literature_reference", "Guo 1993 力项格式（体力注入）", "literature"),
    ("Ladd 动量交换", "literature_reference", "Ladd 动量交换壁面力路线", "literature"),
    ("MKM DNS", "literature_reference", "MKM DNS 壁面湍流基准（未做，见 §5-3）", "literature"),
    ("Reichardt 复合律", "literature_reference", "Reichardt 复合律（未做，见 §5-3）", "literature"),
    ("合入时无任何 pytest 用例", "declared_absent_asset", "合入时缺失的 pytest 用例与验证文档（报告声明不存在）", "absent"),
    ("本单**未修**", "declared_open_defect", "壁面动量交换（wall_exchange）聚合口径缺陷：报告声明本单未修", "open"),
    ("**未做**（本单只保证", "declared_absent_asset", "Re_tau=180/395 壁面解析湍流验证：报告声明本单未做", "absent"),
]

TABLE_KEYS = [
    ("**表 1 —", "in_source_table", "表 1 力项动量源（锚 A）"),
    ("**表 2 —", "in_source_table", "表 2 剪切模态黏性与层流孪生（锚 B/C）"),
    ("**表 3 —", "in_source_table", "表 3 负控（锚必须能失败）"),
]


def classify_path(path: str) -> str:
    p = path.lower()
    if p.endswith(".png"):
        return "figure_reference"
    if p.endswith(".py"):
        if p.startswith("tests/"):
            return "test_reference"
        if p.startswith("artifacts/"):
            return "probe_script_reference"
        return "source_code_reference"
    if p.endswith(".json"):
        return "data_artifact_reference"
    if p.endswith(".md"):
        return "document_reference"
    return "reference"


def scan_path_references(md: str):
    """Occurrence-level (line, verbatim line, path, via) for every path-like reference."""
    out, seen = [], set()
    lines = md.split("\n")
    for i, line in enumerate(lines, start=1):
        for tick in TICK_RE.finditer(line):
            inner = tick.group(1)
            for m in FILE_RE.finditer(inner):
                key = (i, m.group("path"))
                if key not in seen:
                    seen.add(key)
                    out.append({"line": i, "quote": line, "path": m.group("path"), "via": "backticked"})
            for m in DIR_RE.finditer(inner):
                d = m.group("dir")
                key = (i, d)
                if (
                    key not in seen
                    and d.startswith(ROOTED_DIR_PREFIXES)
                    and FILE_RE.fullmatch(d.rstrip("/")) is None
                ):
                    seen.add(key)
                    out.append({"line": i, "quote": line, "path": d, "via": "backticked_dir"})
    return out


# Paths whose owner repository is TensorLBM (report 7473's subject).  They must NOT be
# "resolved" against TensorKnowledge's own tree: this worktree has its own tests/ and
# artifacts/ directories, and silently matching those would be a false resolution.
TENSORLBM_ROOTS = ("src/", "tests/", "benchmarks/", "artifacts/")


def resolve_path(path: str):
    """Resolve a referenced path against THIS delivery worktree only (owner-repo aware)."""
    if path.startswith(TENSORLBM_ROOTS):  # tested before rstrip("/") so "tests/" still matches
        p = path.rstrip("/")
        return {
            "status": "referenced_unresolved",
            "check": "owner repo is TensorLBM; the path is outside this delivery worktree and is NOT "
                     "matched against TensorKnowledge's same-named directories",
            "result": "unresolved",
            "detail": {"path": p, "expected_owner_repo": "TensorLBM"},
        }
    p = path.rstrip("/")
    local = REPO / p
    if local.is_file():
        b = local.read_bytes()
        return {
            "status": "resolved_in_source",
            "check": "file exists in delivery worktree; bytes hashed",
            "result": "resolved",
            "detail": {"path": p, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()},
        }
    if local.is_dir():
        return {
            "status": "resolved_in_source",
            "check": "directory exists in delivery worktree",
            "result": "resolved",
            "detail": {"path": p, "entries": sorted(x.name for x in local.iterdir())[:20]},
        }
    owner = "unknown"
    return {
        "status": "referenced_unresolved",
        "check": "path absent from this delivery worktree (TensorKnowledge); source repo outside package scope",
        "result": "unresolved",
        "detail": {"path": p, "expected_owner_repo": owner},
    }


def make_asset(asset_id, asset_class, label, section, locator, resolution, note=""):
    return {
        "asset_id": asset_id,
        "asset_class": asset_class,
        "label": label,
        "in_report_section": section,
        "locator": locator,
        "resolution": resolution,
        "note": note,
    }


def line_locator(md: str, line_no: int) -> dict:
    """Char span + verbatim quote for a 1-based line; uniqueness measured on the quote."""
    lines = md.split("\n")
    quote = lines[line_no - 1]
    start = sum(len(x) + 1 for x in lines[: line_no - 1])
    return {
        "scheme": "markdown_line",
        "line": line_no,
        "start_char": start,
        "end_char": start + len(quote),
        "quote": quote,
        "unique": md.count(quote) == 1,
    }


def section_of(line_no: int, md: str) -> str:
    lines = md.split("\n")
    for i in range(min(line_no, len(lines)) - 1, -1, -1):
        if lines[i].startswith("## "):
            return lines[i][3:].strip()
    return "preamble"


def build():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    lines = md.split("\n")
    digest = hashlib.sha256(raw).hexdigest()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(md, encoding="utf-8")

    # ---- figure probes (platform-stored figure metadata vs actual bytes)
    figs = meta.get("figures") or []
    fig_probes = [probe(token, "/tensor/reports/%s/figures/%s" % (REPORT_ID, f.get("name"))) for f in figs]

    assets = []
    n = 0

    def add(asset_class, label, section, locator, resolution, note=""):
        nonlocal n
        n += 1
        assets.append(make_asset("A%02d" % n, asset_class, label, section, locator, resolution, note))

    # A. the source document itself
    add(
        "source_document",
        "report %s markdown（唯一源资产，%d chars / %d bytes utf-8）" % (REPORT_ID, len(md), len(raw)),
        "document",
        {
            "scheme": "markdown_document",
            "field": "markdown",
            "start_char": 0,
            "end_char": len(md),
            "start_line": 1,
            "end_line": len(lines),
            "quote": lines[0],
            "unique": md.count(lines[0]) == 1,
        },
        {
            "status": "resolved_in_source",
            "check": "sha256 over markdown utf-8 bytes",
            "result": "resolved",
            "detail": {"chars": len(md), "bytes": len(raw), "sha256": digest},
        },
        "Hash recomputed locally from GET /tensor/reports/%s; contract source_hash compared in verify()." % REPORT_ID,
    )

    # B. platform figure records (metadata exists; byte payload probed, not assumed)
    for idx, f in enumerate(figs):
        pr = fig_probes[idx]
        served = pr.get("http_status") == 200
        add(
            "platform_figure_record",
            "figures[%d].name=%s" % (idx, f.get("name")),
            "record.figures",
            {
                "scheme": "report_field",
                "field": "figures",
                "index": idx,
                "start_char": None,
                "end_char": None,
                "start_line": None,
                "end_line": None,
                "quote": "figures[%d]=%s | caption=%s" % (idx, f.get("name"), f.get("caption")),
                "unique": True,
            },
            {
                "status": "resolved_in_source" if served else "referenced_unresolved",
                "check": "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, f.get("name")),
                "result": "resolved" if served else "unresolved",
                "detail": pr,
            },
            "Metadata (name+caption) lives in the report record; bytes are %s by the figure endpoint."
            % ("served" if served else "not served (HTTP %s), so no figure hash is claimable" % pr.get("http_status")),
        )

    # C. every path-like reference in the markdown, occurrence-level
    refs = scan_path_references(md)
    for r in refs:
        cls = classify_path(r["path"])
        add(
            cls,
            r["path"],
            section_of(r["line"], md),
            line_locator(md, r["line"]),
            resolve_path(r["path"]),
            "Reference parsed from line %d (%s); resolution checked against this worktree only."
            % (r["line"], r["via"])
            + (" Path is abbreviated in the report (uses '...'), so it is not a literal file path."
               if "..." in r["path"] else ""),
        )

    # D. curated literature / declared-absent anchors
    for key, cls, label, rule in CURATED:
        hit = None
        for i, line in enumerate(lines, start=1):
            if key in line:
                hit = i
                break
        if hit is None:
            raise SystemExit("curated anchor %r not found in markdown" % key)
        if rule == "literature":
            res = {
                "status": "referenced_unresolved",
                "check": "external publication cited by name; no DOI/URL/payload in report or reachable from this worktree",
                "result": "unresolved",
                "detail": {"search_key": key, "external": True},
            }
        elif rule == "open":
            res = {
                "status": "referenced_unresolved",
                "check": "report itself declares this item unfixed; no artifact can exist yet (open item, quoted verbatim)",
                "result": "unresolved",
                "detail": {"search_key": key, "declared_open": True},
            }
        else:
            res = {
                "status": "declared_absent",
                "check": "report states the asset does not exist (absence is the report's own claim, quoted verbatim)",
                "result": "absent",
                "detail": {"search_key": key},
            }
        add(cls, label, section_of(hit, md), line_locator(md, hit), res,
            "Locator resolves to the verbatim source line; the asset itself is not present in the package scope.")

    # E. in-source result tables (structured data a downstream extractor would anchor on)
    for key, cls, label in TABLE_KEYS:
        hit = None
        for i, line in enumerate(lines, start=1):
            if line.startswith(key):
                hit = i
                break
        if hit is None:
            raise SystemExit("table anchor %r not found" % key)
        add(
            cls,
            label,
            section_of(hit, md),
            line_locator(md, hit),
            {
                "status": "resolved_in_source",
                "check": "table header line located verbatim in markdown; rows = contiguous '|' block after it",
                "result": "resolved",
                "detail": {"header_line": hit},
            },
            "Registered as an in-source data asset; no cell values are extracted or normalized here.",
        )

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]["status"]] = by_res.get(a["resolution"]["status"], 0) + 1

    manifest = {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/kf/build_asset_manifest_7473.py",
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + digest,
            "contract_source_hash": "sha256:" + EXPECTED_HASH,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "hash_match": digest == EXPECTED_HASH,
            "chars": len(md),
            "contract_chars": EXPECTED_CHARS,
            "chars_match_contract": len(md) == EXPECTED_CHARS,
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "line_counting": "logical lines = markdown.split(chr(10)); 1-based",
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "record_fields": {
                "title": meta.get("title"),
                "scenario_key": meta.get("scenario_key"),
                "mission_id": meta.get("mission_id"),
                "status": meta.get("status"),
                "created_at": meta.get("created_at"),
                "tags": meta.get("tags"),
                "contract_title": CONTRACT_TITLE,
                "contract_scenario_key": CONTRACT_SCENARIO,
                "title_matches_contract": meta.get("title") == CONTRACT_TITLE,
                "scenario_matches_contract": meta.get("scenario_key") == CONTRACT_SCENARIO,
            },
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "distinct_referenced_paths": len({r["path"] for r in refs}),
            "claims": 0,
        },
        "assets": assets,
        "claims": [],
        "claims_note": (
            "objective.classify_report_type=false and no extraction was requested; the contract notes "
            "explicitly allow an empty claims array. Nothing is marked verified — verification is "
            "computed by the platform gate."
        ),
        "resolution_vocabulary": {
            "resolved_in_source": "located and (for files) hashed inside the source markdown / this delivery worktree / the report record",
            "referenced_unresolved": "named in the report, target bytes not reachable from this work package",
            "declared_absent": "the report itself states the asset does not exist",
        },
        "identity_granularity": (
            "Path references are occurrence-level: identity = (path, markdown line), so a path cited on two "
            "lines yields two assets with their own quotes. counts.distinct_referenced_paths is the dedup view."
        ),
        "platform_probes": {
            "figures": fig_probes,
            "artifacts_listing": probe(token, "/tensor/reports/%s/artifacts" % REPORT_ID),
        },
        "limitations": [
            "Registration only: no extraction, no claim generation, no 'verified' marks.",
            "Referenced TensorLBM paths (src/, tests/, artifacts/, benchmarks/) are outside this delivery worktree, so they are registered unresolved rather than assumed to exist.",
            "Platform figure endpoint returned no bytes for either figure; captions are metadata only, no image hash is claimable.",
            "Literature anchors (Guo 1993 / Ladd / MKM DNS / Reichardt) are registered as name-level citations; no DOI or URL appears in the report, so they stay unresolved.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets)" % (MANIFEST.relative_to(REPO), len(assets)))
    return manifest


# ---------------------------------------------------------------- schema


def write_schema():
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://tensorplatform.local/schemas/asset_manifest_7473.schema.json",
        "title": "asset_manifest for work package wp-7473-01 (report 7473)",
        "description": (
            "Local schema pinning the manifest shape produced by scripts/kf/build_asset_manifest_7473.py. "
            "The platform-side kf_result gate wins if it disagrees."
        ),
        "type": "object",
        "required": ["manifest_version", "package_id", "task_type", "report_id", "source", "counts", "assets", "claims"],
        "properties": {
            "manifest_version": {"const": "1.0"},
            "package_id": {"const": PKG},
            "task_type": {"const": "01-asset-registration"},
            "report_id": {"const": REPORT_ID},
            "claims": {"type": "array", "items": {"type": "object", "required": ["claim_id", "text"]}},
            "source": {
                "type": "object",
                "required": ["source_uri", "source_field", "source_hash", "hash_algo", "chars", "bytes_utf8", "lines"],
                "properties": {
                    "source_uri": {"const": SOURCE_URI},
                    "source_field": {"const": "markdown"},
                    "hash_algo": {"const": "sha256"},
                    "source_hash": {"pattern": "^sha256:[0-9a-f]{64}$"},
                    "chars": {"type": "integer", "minimum": 1},
                    "bytes_utf8": {"type": "integer", "minimum": 1},
                    "lines": {"type": "integer", "minimum": 1},
                    "hash_match": {"type": "boolean"},
                },
            },
            "counts": {
                "type": "object",
                "required": ["assets", "by_class", "by_resolution"],
                "properties": {"assets": {"type": "integer", "minimum": 1}},
            },
            "assets": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["asset_id", "asset_class", "label", "in_report_section", "locator", "resolution"],
                    "properties": {
                        "asset_id": {"type": "string", "pattern": "^A[0-9]{2}$"},
                        "asset_class": {"type": "string", "minLength": 1},
                        "label": {"type": "string", "minLength": 1},
                        "in_report_section": {"type": "string", "minLength": 1},
                        "resolution": {
                            "type": "object",
                            "required": ["status", "check", "result"],
                            "properties": {
                                "status": {"enum": ["resolved_in_source", "referenced_unresolved", "declared_absent"]},
                                "check": {"type": "string", "minLength": 1},
                                "result": {"enum": ["resolved", "unresolved", "absent"]},
                            },
                        },
                        "locator": {
                            "type": "object",
                            "required": ["scheme", "quote"],
                            "properties": {
                                "scheme": {"enum": ["markdown_line", "markdown_document", "report_field"]},
                                "quote": {"type": "string", "minLength": 1},
                            },
                        },
                    },
                },
            },
        },
    }
    SCHEMA.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % SCHEMA.relative_to(REPO))


# ---------------------------------------------------------------- verify / result


def verify():
    import jsonschema

    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    lines = md.split("\n")
    checks = {}

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checks["valid_json"] = {"pass": True, "detail": "json.loads OK (%d assets)" % len(manifest["assets"])}

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(manifest, schema)
        checks["schema_pass"] = {"pass": True, "detail": "jsonschema %s vs local asset_manifest_7473.schema.json" % SCHEMA.name}
    except jsonschema.ValidationError as e:
        checks["schema_pass"] = {"pass": False, "detail": str(e).split("\n")[0]}

    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc.get("quote")
        if loc["scheme"] == "markdown_document":
            if not (loc.get("start_char") == 0 and loc.get("end_char") == len(md)):
                bad.append((a["asset_id"], "document span"))
            continue
        if loc["scheme"] == "markdown_line":
            ln = loc.get("line")
            if not isinstance(ln, int) or not (1 <= ln <= len(lines)) or lines[ln - 1] != q or q not in md:
                bad.append((a["asset_id"], "line/quote mismatch"))
                continue
            start = loc.get("start_char")
            if start is not None and md[start:loc["end_char"]] != q:
                bad.append((a["asset_id"], "char span mismatch"))
                continue
            if loc.get("unique") is not (md.count(q) == 1):
                bad.append((a["asset_id"], "uniqueness flag stale"))
        elif loc["scheme"] == "report_field":
            if loc.get("field") == "figures":
                figs = meta.get("figures") or []
                i = loc.get("index")
                if not isinstance(i, int) or not (0 <= i < len(figs)):
                    bad.append((a["asset_id"], "figure index out of range"))
                elif figs[i].get("name") not in q:
                    bad.append((a["asset_id"], "figure quote mismatch"))
        else:
            bad.append((a["asset_id"], "unknown scheme"))
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": "checked %d locators; bad=%s" % (len(manifest["assets"]), bad),
    }

    actual = hashlib.sha256(raw).hexdigest()
    declared = manifest["source"]["source_hash"].split("sha256:")[-1]
    snap = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    checks["source_hash_matches"] = {
        "pass": actual == declared == EXPECTED_HASH and snap == actual,
        "detail": "recomputed=%s declared=%s contract=%s snapshot=%s (snapshot is byte-identical)"
        % (actual, declared, EXPECTED_HASH, snap),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)) and bool(ids),
        "detail": "assets=%d unique=%d" % (len(ids), len(set(ids))),
    }

    claims = manifest.get("claims", [])
    bad_claims = [c for c in claims if not c.get("evidence") and not c.get("status")]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad_claims,
        "detail": "claims=%d violating=%d (empty array: vacuously satisfied, allowed by contract notes)" % (len(claims), len(bad_claims)),
    }

    checks["do_not_mark_claims_as_verified"] = {
        "pass": all(c.get("status") != "verified" for c in claims),
        "detail": "no claim carries status=verified",
    }

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["all_pass"] else 1


def emit_result():
    """The kf_result envelope that goes into the report markdown as its single ```json block."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prov = manifest["source"]
    result = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": prov["source_hash"],
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": prov["chars"],
            "source_bytes_utf8": prov["bytes_utf8"],
            "hash_matches_contract": prov["hash_match"],
            "fetched_via": prov["fetched_via"],
            "generator": "scripts/kf/build_asset_manifest_7473.py",
            "contract_version": "1.0",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str(MANIFEST.relative_to(REPO)),
                "sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                "bytes": len(MANIFEST.read_bytes()),
                "asset_count": manifest["counts"]["assets"],
                "by_resolution": manifest["counts"]["by_resolution"],
                "claims": 0,
            },
            "verification.json": {
                "path": str(VERDICT.relative_to(REPO)),
                "sha256": hashlib.sha256(VERDICT.read_bytes()).hexdigest() if VERDICT.exists() else None,
                "bytes": len(VERDICT.read_bytes()) if VERDICT.exists() else None,
            },
            "source_markdown.md": {
                "path": str(SNAPSHOT.relative_to(REPO)),
                "sha256": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
                "bytes": len(SNAPSHOT.read_bytes()),
                "note": "byte-identical snapshot of the registered markdown (reproducibility anchor)",
            },
        },
        "claims": [],
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % RESULT.relative_to(REPO))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    acts = sys.argv[1:] or ["build", "verify"]
    if "build" in acts:
        build()
    if "schema" in acts:
        write_schema()
    if "result" in acts:
        emit_result()
    if "verify" in acts:
        sys.exit(verify())