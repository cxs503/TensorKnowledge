#!/usr/bin/env python3
"""Work package wp-8288-01 (01-asset-registration) — asset manifest builder + verifier.

Scope guard: touches ONLY report_id=8288. Registration only: no extraction, no
claim generation, no `verified` marks (verification is platform-gated).

Zero hand-copy discipline: every locator quote is sliced out of the fetched
markdown bytes by character offsets (never retyped), so `quote` is provably a
substring of the source and `start_char/end_char` reproduce it exactly.

Usage:
  python3 scripts/kf/wp8288_01_register.py build
  python3 scripts/kf/wp8288_01_register.py build verify result
"""
from __future__ import annotations

import base64
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

PKG = "wp-8288-01"
REPORT_ID = "8288"
SOURCE_URI = "tensor://reports/8288"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "2c35fbe3fa027f083b82f15238f3db797f087df0c435a1c536b176280e053f19"
EXPECTED_CHARS = 9660

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
SCHEMA_LOCAL = OUT_DIR / "asset_manifest.schema.json"
SRC = OUT_DIR / "source.md"
VERDICT = OUT_DIR / "verification.json"
RESULT = OUT_DIR / "kf_result.json"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASSWORD = os.environ["TENSOR_AGENT_PASS"]

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
    payload = {"username": USER, "password": PASSWORD}
    try:
        d = _req(BASE + "/auth/login", data=json.dumps(payload).encode())
    except urllib.error.HTTPError:
        d = _req(BASE + "/auth/login", data=urllib.parse.urlencode(payload).encode(),
                 ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_report(token):
    d = _req(BASE + "/tensor/reports/" + REPORT_ID, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


def probe_artifact_endpoints(token):
    probes = {}
    for path in ("/tensor/reports/%s/artifacts" % REPORT_ID,
                 "/tensor/artifacts?report_id=%s" % REPORT_ID):
        try:
            _req(BASE + path, token)
            probes[path] = {"status": "ok"}
        except urllib.error.HTTPError as e:
            probes[path] = {"status": "http_%s" % e.code}
        except Exception as e:  # noqa: BLE001 - record, never fabricate
            probes[path] = {"status": "error", "detail": type(e).__name__}
    return probes


# ---------------------------------------------------------------- locator helpers


def offsets(md: str):
    """1-based line number -> character offset of the line start."""
    starts, pos = [0], 0
    for line in md.split("\n"):
        pos += len(line) + 1
        starts.append(pos)
    return starts


def heading_index(lines):
    """For each 1-based line number, the enclosing (nearest preceding) heading text."""
    out, cur = {}, "(preamble)"
    for i, line in enumerate(lines, start=1):
        if line.startswith("#"):
            cur = line.lstrip("#").strip()
        out[i] = cur
    return out


def char_span_locator(md: str, lines, line_start: int, line_end: int, heads):
    """Build a char_span locator from a 1-based inclusive line range, verbatim slice."""
    starts = offsets(md)
    s, e = starts[line_start - 1], starts[line_end - 1] + len(lines[line_end - 1])
    quote = md[s:e]
    # widen upward (never retyping anything) until the slice identifies one location
    while line_start > 1 and md.count(quote) != 1:
        line_start -= 1
        s = starts[line_start - 1]
        quote = md[s:e]
    return {
        "method": "char_span",
        "start_char": s,
        "end_char": e,
        "start_line": line_start,
        "end_line": line_end,
        "quote": quote,
        "unique": md.count(quote) == 1,
        "in_report_section": heads[line_start],
    }, quote


IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)\s]+)\)")
TICK_PATH_RE = re.compile(
    r"`(?P<path>[A-Za-z0-9_./-]+\.(?:json|png|py|md|txt|csv))(?::(?P<line>\d+(?:-\d+)?))?`")
BARE_PATH_RE = re.compile(
    r"(?<![\w/`.])(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|png|py|md|txt|csv))\b"
    r"(?::(?P<line>\d+(?:-\d+)?))?(?![\w`])")
CITE_RE = re.compile(r"(?P<author>[A-Z][A-Za-z\-]+) et al\. \((?P<year>\d{4})\)")


def classify_path(path: str) -> str:
    p = path.lower()
    if p.endswith(".png"):
        return "figure_reference"
    if p.endswith(".py"):
        return "source_code_reference"
    if p.endswith(".md"):
        return "document_reference"
    if p.endswith((".json", ".csv", ".txt")):
        return "data_artifact_reference"
    return "reference"


def resolve_in_worktree(path: str):
    """Resolve a referenced path inside this delivery worktree only (no cross-repo guessing)."""
    for cand in (REPO / path, REPO / path.lstrip("./")):
        try:
            cand = cand.resolve()
        except OSError:
            continue
        if not str(cand).startswith(str(REPO)):
            continue
        if cand.is_file():
            raw = cand.read_bytes()
            return {"check": "delivery_worktree_file_lookup", "result": "resolved",
                    "resolved_path": str(cand.relative_to(REPO)),
                    "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return {"check": "delivery_worktree_file_lookup", "result": "unresolved",
            "reason": "path is not present in the TensorKnowledge delivery worktree; "
                      "the owning tree (TensorDEM) is outside this work package's boundary"}


def scan_path_refs(lines):
    """Ordered, de-duplicated (path, line) path-like references."""
    found, seen = [], set()
    for i, line in enumerate(lines, start=1):
        hits = []
        for m in IMG_RE.finditer(line):
            hits.append((m.group("path"), "markdown_image", None, m.group("alt")))
        for m in TICK_PATH_RE.finditer(line):
            hits.append((m.group("path"), "backticked_ref", m.group("line"), None))
        for m in BARE_PATH_RE.finditer(line):
            hits.append((m.group("path"), "bare_ref", m.group("line"), None))
        for path, via, pin, alt in hits:
            if (path, i) in seen:
                continue
            seen.add((path, i))
            found.append({"line": i, "path": path, "via": via, "pin": pin, "alt": alt})
    return found


def scan_tables(lines):
    """Contiguous markdown pipe tables -> (start_line, end_line, n_data_rows, header)."""
    tables, i, n = [], 1, len(lines)
    while i <= n:
        if lines[i - 1].lstrip().startswith("|"):
            j = i
            while j <= n and lines[j - 1].lstrip().startswith("|"):
                j += 1
            block = [lines[k - 1] for k in range(i, j)]
            header = [c.strip() for c in block[0].strip().strip("|").split("|")]
            sep = block[1] if len(block) > 1 else ""
            data_rows = max(0, len(block) - 2) if set(sep.replace("|", "").replace(" ", "")) <= set("-:") else len(block) - 1
            tables.append({"start": i, "end": j - 1, "header": header, "data_rows": data_rows})
            i = j
        else:
            i += 1
    return tables


def scan_code_blocks(lines):
    """Fenced blocks -> (start_line, end_line, info_string)."""
    blocks, open_at = [], None
    for i, line in enumerate(lines, start=1):
        if line.startswith("```"):
            if open_at is None:
                open_at = i
                info = line[3:].strip() or "none"
            else:
                blocks.append({"start": open_at, "end": i, "info": info})
                open_at = None
    return blocks


# ---------------------------------------------------------------- build


def build():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit("SOURCE HASH MISMATCH: contract=%s actual=%s" % (EXPECTED_HASH, digest))
    if len(md) != EXPECTED_CHARS:
        raise SystemExit("SOURCE CHAR COUNT MISMATCH: contract=%d actual=%d" % (EXPECTED_CHARS, len(md)))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SRC.write_bytes(raw)
    lines = md.split("\n")
    heads = heading_index(lines)
    assets, ids = [], set()

    def add(asset_id, asset_class, label, locator, resolution, note, extra=None):
        if asset_id in ids:
            raise SystemExit("duplicate asset_id %s" % asset_id)
        ids.add(asset_id)
        extra = dict(extra or {})
        check = extra.pop("_check")
        a = {
            "asset_id": asset_id,
            "asset_class": asset_class,
            "label": label,
            "in_report_section": locator["in_report_section"],
            "locator": locator,
            "resolution": resolution,
            "resolution_check": check,
            "note": note,
        }
        a.update(extra)
        assets.append(a)

    # A01 — the source asset itself (whole document)
    title_line = next((l for l in lines if l.startswith("# ")), lines[0])
    add("A01", "report_markdown", "IN61-N07 report markdown (source of record)",
        {"method": "document", "start_char": 0, "end_char": len(md), "start_line": 1,
         "end_line": len(lines), "quote": title_line, "unique": md.count(title_line) == 1,
         "in_report_section": "(document root)"},
        "resolved_in_source", "Byte-identical copy stored at docs/kf/wp-8288-01/source.md; sha256 matches the contract source_hash.",
        {"_check": {"check": "recomputed sha256 of markdown bytes == contract", "result": "resolved"},
         "uri": SOURCE_URI, "source_field": SOURCE_FIELD, "chars": len(md), "bytes_utf8": len(raw),
         "lines": len(lines), "sha256": "sha256:" + digest,
         "local_copy": "docs/kf/wp-8288-01/source.md"})

    # A02.. — figures carried in the report record (payload hashed only if bytes exist)
    n = 2
    figs = meta.get("figures") or []
    for idx, fig in enumerate(figs):
        b64 = fig.get("png_base64") or ""
        try:
            blob = base64.b64decode(b64) if b64 else b""
        except Exception:  # noqa: BLE001 - record absence, never fabricate
            blob = b""
        loc = {"method": "document", "start_char": 0, "end_char": len(md), "start_line": 1,
               "end_line": len(lines), "quote": title_line, "unique": md.count(title_line) == 1,
               "in_report_section": "(report record field: figures)"}
        add("A%02d" % n, "embedded_figure_record", "record figure[%d]: %s" % (idx, fig.get("name")),
            dict(loc),
            "resolved_in_source" if blob else "declared_absent",
            ("Figure object stored in the report record with a decodable png payload; byte hash computed locally."
             if blob else
             "Report record lists the figure by name+caption only (no png_base64 payload), so no image bytes exist to hash."),
            {"record_field": "figures[%d]" % idx,
             "figure_name": fig.get("name"), "caption": fig.get("caption"),
             "bytes": len(blob) or None,
             "sha256": "sha256:" + hashlib.sha256(blob).hexdigest() if blob else None,
             "_check": {"check": "base64-decode figures[i].png_base64", "result": "resolved" if blob else "absent"}})
        n += 1

    # A.. — path-like references (occurrence-level identity: path + line)
    refs = scan_path_refs(lines)
    for ref in refs:
        loc, _q = char_span_locator(md, lines, ref["line"], ref["line"], heads)
        res = resolve_in_worktree(ref["path"])
        add("A%02d" % n, classify_path(ref["path"]), ref["path"], loc,
            "referenced_unresolved" if res["result"] == "unresolved" else "resolved_in_source",
            "Referenced by the report body; %s." % (
                "not resolvable inside this worktree, so it stays an unresolved reference (no assumed content)"
                if res["result"] == "unresolved" else "resolved to a file inside this worktree"),
            {"path_reference": ref["path"], "via": ref["via"], "line_pin": ref["pin"],
             "_check": res})
        n += 1

    # A.. — markdown tables (parseable structures, registered not extracted)
    for t in scan_tables(lines):
        loc, _q = char_span_locator(md, lines, t["start"], t["end"], heads)
        add("A%02d" % n, "markdown_table", "table: %s" % " | ".join(t["header"][:3]), loc,
            "resolved_in_source", "Pipe table parsed as a structure only (header + row count); cell values are not extracted in this work package.",
            {"header": t["header"], "data_rows": t["data_rows"],
             "_check": {"check": "contiguous pipe-table scan", "result": "resolved"}})
        n += 1

    # A.. — fenced code/formula blocks
    for b in scan_code_blocks(lines):
        loc, _q = char_span_locator(md, lines, b["start"], b["end"], heads)
        add("A%02d" % n, "code_or_formula_block", "fenced block (info: %s)" % b["info"], loc,
            "resolved_in_source", "Fenced block registered as a locatable structure; the report uses it for derivation formulas and one API snippet.",
            {"info_string": b["info"], "block_lines": b["end"] - b["start"] + 1,
             "_check": {"check": "fenced-block scan", "result": "resolved"}})
        n += 1

    # A.. — literature citations without a bibliography entry in the source
    for m in CITE_RE.finditer(md):
        line_no = md[:m.start()].count("\n") + 1
        loc, _q = char_span_locator(md, lines, line_no, line_no, heads)
        add("A%02d" % n, "citation_reference", "%s et al. (%s)" % (m.group("author"), m.group("year")),
            loc, "referenced_unresolved",
            "In-text citation only: the source markdown carries no reference list, so the cited work cannot be resolved from this report alone.",
            {"citation": m.group(0), "year": m.group("year"),
             "_check": {"check": "bibliography entry lookup in source markdown", "result": "unresolved"}})
        n += 1

    # A.. — assets the report itself declares not yet produced (explicit absence, not failure)
    # One registry entry per pending macro-anchor row, plus one span entry for the k=8 cluster deferral.
    rows = ("| Repose angle |", "| Beverloo discharge |", "| Shear box |")
    absent_specs = [
        (rows[0], "macro-anchor result: repose angle (k=1,2,4)",
         "Report marks the run as pending, so no result artifact exists to register."),
        (rows[1], "macro-anchor result: Beverloo discharge (k=1,2,4)",
         "Report marks the run as pending, so no result artifact exists to register."),
        (rows[2], "macro-anchor result: shear box (k=1,2,4)",
         "Report marks the run as pending, so no result artifact exists to register."),
        (rows[0] + ".." + rows[2], "k=8 macro-anchor runs (repose / Beverloo / shear, cluster)",
         "Report defers k=8 to cluster execution; registered as declared-absent, not as a failed run."),
    ]
    for marker, label, note in absent_specs:
        if ".." in marker:
            first_m, last_m = marker.split("..")
            first = next((i for i, l in enumerate(lines, start=1) if first_m in l), None)
            last = next((i for i, l in enumerate(lines, start=1) if last_m in l), None)
            if first is None or last is None or last < first:
                continue
            span = (first, last)
            abs_marker = "row-block with k=8 column = Cluster"
        else:
            hit = next((i for i, l in enumerate(lines, start=1) if marker in l), None)
            if hit is None:
                continue
            span = (hit, hit)
            abs_marker = marker
        loc, _q = char_span_locator(md, lines, span[0], span[1], heads)
        add("A%02d" % n, "declared_absent_result", label, loc, "declared_absent", note,
            {"absence_marker": abs_marker,
             "_check": {"check": "artifact existence for declared-pending runs", "result": "absent"}})
        n += 1

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "producer": "scripts/kf/wp8288_01_register.py",
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "hash_scope": "UTF-8 bytes of the markdown field as served by GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
            "chars": len(md),
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "mission_id": meta.get("mission_id"),
            "platform_tags": meta.get("tags"),
            "platform_figures": [{"name": f.get("name"), "caption": f.get("caption"),
                                  "has_png_payload": bool(f.get("png_base64"))} for f in figs],
            "local_copy": "docs/kf/wp-8288-01/source.md",
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "distinct_referenced_paths": len({a["path_reference"] for a in assets if "path_reference" in a}),
            "distinct_citations": len({a["citation"] for a in assets if "citation" in a}),
        },
        "identity_granularity": "Path references are occurrence-level: identity is (path_reference, markdown line), so two citations of the same file on different lines are two assets with their own quotes.",
        "artifact_endpoint_probe": probe_artifact_endpoints(token),
        "assets": assets,
        "claims": [],
        "claims_empty_reason": "Contract objective is register_assets=true / classify_report_type=false with no extraction step, and notes explicitly allow an empty claims array; emitting claims here would be unforced claim generation.",
        "integrity": {
            "quote_uniqueness": {"quotes": len(assets),
                                 "unique_in_source": sum(1 for a in assets if a["locator"]["unique"]),
                                 "non_unique": [a["asset_id"] for a in assets if not a["locator"]["unique"]]},
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "locator_reproducible": "every locator quote is sliced from source.md by [start_char, end_char) and re-checked by the verifier",
        },
        "limitations": [
            "Registration only: no text extraction, no claim generation, no verified marks (verification is platform-gated).",
            "Referenced .py/.json/.md paths belong to the TensorDEM tree, which is outside this work package's boundary; they are registered as unresolved rather than assumed present.",
            "Tables and fenced blocks are registered as structures (header + row count, info string) without transcribing their values.",
            "Report-record figures are hashed only when a png payload is stored; metadata-only figures are recorded as absent, not invented.",
            "No characterisation of report type is performed (objective.classify_report_type=false).",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets)" % (MANIFEST.relative_to(REPO), len(assets)))
    return manifest


# ---------------------------------------------------------------- local schema
LOCAL_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://tensorplatform.local/schemas/asset_manifest.wp-8288-01.json",
    "title": "asset_manifest.v1 projected onto wp-8288-01 (no const renaming of fields)",
    "description": "Derived from TensorKnowledge schemas/asset_manifest.v1.schema.json (pinned to wp-448-01 via const) by keeping every field/type/enum and replacing only the per-package consts (package_id/report_id/task_type/uri) with the wp-8288-01 values. No other work package's files are modified.",
    "type": "object",
    "required": ["schema", "package_id", "task_type", "report_id", "source", "counts", "assets", "claims", "integrity"],
    "properties": {
        "schema": {"const": "asset_manifest.v1"},
        "package_id": {"const": PKG},
        "task_type": {"const": "01-asset-registration"},
        "report_id": {"const": REPORT_ID},
        "lane": {"type": "string"},
        "generated_at": {"type": "string"},
        "producer": {"type": "string"},
        "source": {
            "type": "object",
            "required": ["uri", "field", "hash_alg", "hash", "chars", "bytes_utf8", "title", "scenario_key"],
            "properties": {
                "uri": {"const": SOURCE_URI},
                "field": {"const": "markdown"},
                "hash_alg": {"const": "sha256"},
                "hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "hash_scope": {"type": "string"},
                "chars": {"type": "integer", "minimum": 1},
                "bytes_utf8": {"type": "integer", "minimum": 1},
                "lines": {"type": "integer", "minimum": 1},
                "title": {"type": "string", "minLength": 1},
                "scenario_key": {"type": "string", "minLength": 1},
                "mission_id": {},
                "platform_tags": {"type": "array"},
                "platform_figures": {"type": "array"},
                "local_copy": {"type": "string"},
            },
        },
        "counts": {
            "type": "object",
            "required": ["assets", "by_class", "by_resolution", "resolved_in_source",
                         "referenced_unresolved", "declared_absent"],
            "properties": {
                "assets": {"type": "integer", "minimum": 1},
                "by_class": {"type": "object"},
                "by_resolution": {"type": "object"},
                "resolved_in_source": {"type": "integer", "minimum": 0},
                "referenced_unresolved": {"type": "integer", "minimum": 0},
                "declared_absent": {"type": "integer", "minimum": 0},
            },
        },
        "identity_granularity": {"type": "string"},
        "artifact_endpoint_probe": {"type": "object"},
        "assets": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["asset_id", "asset_class", "label", "in_report_section", "locator",
                             "resolution", "resolution_check", "note"],
                "properties": {
                    "asset_id": {"type": "string", "pattern": "^A[0-9]{2}$"},
                    "asset_class": {"type": "string", "minLength": 1},
                    "label": {"type": "string", "minLength": 1},
                    "in_report_section": {"type": "string", "minLength": 1},
                    "resolution": {"enum": ["resolved_in_source", "referenced_unresolved", "declared_absent"]},
                    "resolution_check": {
                        "type": "object",
                        "required": ["check", "result"],
                        "properties": {
                            "check": {"type": "string"},
                            "result": {"enum": ["resolved", "unresolved", "absent", "present"]},
                        },
                    },
                    "locator": {
                        "type": "object",
                        "required": ["method", "start_char", "end_char", "start_line", "end_line", "quote", "unique"],
                        "properties": {
                            "method": {"enum": ["char_span", "document"]},
                            "start_char": {"type": "integer", "minimum": 0},
                            "end_char": {"type": "integer", "minimum": 1},
                            "start_line": {"type": "integer", "minimum": 1},
                            "end_line": {"type": "integer", "minimum": 1},
                            "quote": {"type": "string", "minLength": 1},
                            "unique": {"type": "boolean"},
                        },
                    },
                    "note": {"type": "string"},
                },
            },
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["claim_id", "text"],
                "anyOf": [{"required": ["evidence_locator"]}, {"required": ["status"]}],
            },
        },
        "claims_empty_reason": {"type": "string"},
        "integrity": {
            "type": "object",
            "required": ["quote_uniqueness", "hash_recomputed_locally", "hash_matches_contract"],
        },
        "limitations": {"type": "array"},
    },
}


def write_schema():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SCHEMA_LOCAL.write_text(json.dumps(LOCAL_SCHEMA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % SCHEMA_LOCAL.relative_to(REPO))


# ---------------------------------------------------------------- verify


def verify():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    checks = {}
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "json.loads OK"}
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"valid_json": {"pass": False, "detail": str(e)}}))
        return 1

    import jsonschema  # local dependency check happens here
    write_schema()
    schema = json.loads(SCHEMA_LOCAL.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(manifest, schema)
        checks["schema_pass"] = {"pass": True,
                                 "detail": "jsonschema draft2020-12 validate against projected schema %s (consts retargeted to %s/%s)"
                                           % (SCHEMA_LOCAL.relative_to(REPO), PKG, REPORT_ID)}
    except jsonschema.ValidationError as e:
        checks["schema_pass"] = {"pass": False, "detail": str(e).splitlines()[0][:400]}

    # locator resolvability: every quote must be re-derivable from the live source bytes
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        try:
            slice_ = md[loc["start_char"]:loc["end_char"]]
        except Exception:  # noqa: BLE001
            bad.append((a["asset_id"], "bad span"))
            continue
        if loc["method"] == "document":
            ok = loc["start_char"] == 0 and loc["end_char"] == len(md) and loc["quote"] in md
        else:
            ok = slice_ == loc["quote"]
        if not ok:
            bad.append((a["asset_id"], "quote != md[start:end]"))
        if loc["unique"] is not (md.count(loc["quote"]) == 1):
            bad.append((a["asset_id"], "unique flag disagrees with source count"))
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": "checked %d locators by re-slicing the live markdown; failures=%s" % (len(manifest["assets"]), bad),
    }

    actual = hashlib.sha256(raw).hexdigest()
    checks["source_hash_matches"] = {
        "pass": actual == manifest["source"]["hash"] == EXPECTED_HASH
        and len(md) == manifest["source"]["chars"] == EXPECTED_CHARS,
        "detail": "recomputed=%s manifest=%s contract=%s chars=%d/%d"
                  % (actual, manifest["source"]["hash"], EXPECTED_HASH, len(md), EXPECTED_CHARS),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)) and all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)
        and ids == sorted(ids),
        "detail": "assets=%d unique=%d pattern_ok=%s sorted=%s"
                  % (len(ids), len(set(ids)),
                     all(re.fullmatch(r"A[0-9]{2}", i) for i in ids), ids == sorted(ids)),
    }

    claims = manifest.get("claims", [])
    viol = [c for c in claims if not (c.get("evidence_locator") or c.get("status"))]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not viol,
        "detail": "claims=%d violating=%d (empty array satisfies the item vacuously; reason recorded in claims_empty_reason)"
                  % (len(claims), len(viol)),
    }

    checks["no_claims_marked_verified"] = {
        "pass": all(c.get("status") != "verified" for c in claims),
        "detail": "no claim carries a verified status; verification is left to the platform gate",
    }
    checks["counts_consistent_with_assets"] = {
        "pass": manifest["counts"]["assets"] == len(manifest["assets"])
        and sum(manifest["counts"]["by_resolution"].values()) == len(manifest["assets"]),
        "detail": "counts.assets=%d len(assets)=%d by_resolution sum=%d"
                  % (manifest["counts"]["assets"], len(manifest["assets"]),
                     sum(manifest["counts"]["by_resolution"].values())),
    }

    acceptance = ["valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
                  "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"]
    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "acceptance_items": {k: checks[k] for k in acceptance},
        "extra_checks": {k: v for k, v in checks.items() if k not in acceptance},
        "all_acceptance_pass": all(checks[k]["pass"] for k in acceptance),
        "gate_scope_note": "Self-check only: the platform gate independently recomputes the source hash and substring-tests every quote; this file is evidence of the author's own run, not a verification mark.",
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["pass"] for k, v in verdict["acceptance_items"].items()}, indent=2))
    print("all_acceptance_pass=%s" % verdict["all_acceptance_pass"])
    return 0 if verdict["all_acceptance_pass"] else 1


# ---------------------------------------------------------------- result envelope


def emit_result():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    token = login()
    _meta, live_md = fetch_report(token)
    live = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    if live != manifest["source"]["hash"] or live != EXPECTED_HASH:
        raise SystemExit("live source drifted: %s" % live)
    result = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + live,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(live_md),
            "source_bytes_utf8": len(live_md.encode("utf-8")),
            "fetched_via": "GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
            "generator": "scripts/kf/wp8288_01_register.py",
            "contract_version": "1.0",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
        },
        "outputs": {
            "asset_manifest.json": manifest,
            "verification.json": verdict,
        },
        "claims": [],
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%.1f KB)" % (RESULT.relative_to(REPO), len(RESULT.read_bytes()) / 1024))
    return result


if __name__ == "__main__":
    acts = sys.argv[1:] or ["build", "verify", "result"]
    if "build" in acts:
        build()
    if "verify" in acts:
        rc = verify()
        if rc:
            sys.exit(rc)
    if "result" in acts:
        emit_result()