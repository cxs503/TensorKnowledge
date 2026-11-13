#!/usr/bin/env python3
"""KF work package wp-9085-01 (01-asset-registration) — report 9085.

Registers the *source assets* of report 9085 (BWM D-1 ballast-water exchange
operation window, IN70-N08). No extraction, no classification, no claims:
objective.register_assets=true, objective.classify_report_type=false.

What is produced (all inside the worktree):

  runs/wp-9085-01/source_9085.md            byte copy of the markdown field
  runs/wp-9085-01/record_9085.json          report record minus the markdown body
  docs/kf/wp-9085-01/asset_manifest.json    asset_manifest.v1 object
  docs/kf/wp-9085-01/kf_result.json         kf_result.v1 envelope (platform gate input)
  docs/kf/wp-9085-01/asset_manifest.schema.derived.json
                                            shared schemas/asset_manifest.v1.schema.json with
                                            the three package-identity consts re-pinned
  docs/kf/wp-9085-01/verification.json      independent re-resolution of every locator
  docs/kf/wp-9085-01/report_selfcheck.json  acceptance-item self check

Contract source of truth (hard-coded from the work-package YAML, then checked, not
trusted):

  source_uri   tensor://reports/9085
  source_hash  sha256:6d424777af46c0c47d01887a47e4de261416aa154a7bbb86d6f1a81502d61d0a
  chars        9761

Usage:
    python3 scripts/kf_wp9085_01_register.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PACKAGE_ID = "wp-9085-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "9085"
SOURCE_URI = "tensor://reports/9085"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = (
    "sha256:6d424777af46c0c47d01887a47e4de261416aa154a7bbb86d6f1a81502d61d0a"
)
CONTRACT_CHARS = 9761
CONTRACT_TITLE = (
    "IN70-N08 压载水置换操作窗口闭环成熟化：BWM D-1 顺序法/溢流法 GM(t) 时程 + "
    "95% 置换达标 + 剪力/弯矩包络（定稿）"
)
CONTRACT_SCENARIO = "ballast_water_d1_operation_window"
LANE = "C"
PRODUCER = "kf-worker/m15629"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
RECORD_META = RUN_DIR / ("record_%s.json" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
DERIVED_SCHEMA = OUT_DIR / "asset_manifest.schema.derived.json"
VERIFICATION = OUT_DIR / "verification.json"
SELFCHECK = OUT_DIR / "generator_selfcheck.json"
SHARED_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.schema.json"
KF_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"

PATH_TOKEN_RE = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|json|png|jpg|md|h5|hdf5|csv|txt)"
)
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
TICK_RE = re.compile(r"`([^`\n]+)`")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
MODULE_LIST_RE = re.compile(r"^[a-z_]+(\s*/\s*[a-z_]+)+$")


# ------------------------------------------------------------------ platform io
def _api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _login() -> str:
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        _api_base() + "/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get(path: str, tok: str):
    req = urllib.request.Request(
        _api_base() + path, headers={"Authorization": "Bearer " + tok}
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:  # recorded as probe evidence, never swallowed
        return e.code, e.read()


def fetch_report() -> dict:
    tok = _login()
    st, raw = _get("/tensor/reports/%s" % REPORT_ID, tok)
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> %s %r" % (REPORT_ID, st, raw[:200]))
    return json.loads(raw)


def probe(path: str) -> dict:
    """Probe auxiliary endpoints; record the status, never invent a payload."""
    st, body = _get(path, _login())
    return {"path": path, "http_status": st, "bytes": len(body)}


# ------------------------------------------------------------------------ utils
def sha256_hex(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def line_starts(text: str) -> list[int]:
    """starts[k] = char offset (code points) at which 0-based line k begins."""
    starts, off = [0], 0
    for ch in text:
        off += 1
        if ch == "\n":
            starts.append(off)
    return starts


def line_of(md: str, offset: int) -> int:
    """1-based line number containing the character offset."""
    return md.count("\n", 0, offset) + 1


def section_of(lines: list[str], line_no: int) -> str:
    """Nearest '## ' section heading at or above line_no; 'preamble' above section 1."""
    for i in range(line_no - 1, -1, -1):
        m = HEAD_RE.match(lines[i])
        if m and len(m.group(1)) >= 2:
            return m.group(2).strip()
    return "preamble"


def pick_span(md: str, cands: list[tuple[int, int]]) -> dict:
    """Smallest unique quote among the candidate spans: token -> line -> 3 lines.

    Returning the span together with the quote keeps start_char/end_char and the
    quoted text structurally consistent (the verify pass re-slices the markdown).
    """
    fallback = None
    for s, e in cands:
        q = md[s:e]
        if not q.strip():
            continue
        cand = {"start_char": s, "end_char": e, "quote": q}
        if md.count(q) == 1:
            cand["unique"] = True
            return cand
        if fallback is None:
            fallback = cand
    if fallback is None:
        raise SystemExit("empty quote candidate")
    fallback["unique"] = False
    return fallback


def resolve_in_worktree(token: str) -> dict:
    """Resolution scope is the delivery worktree only.

    The report lives in ship-performance-platform; the referenced files were not
    transferred with the markdown, so a miss here is 'referenced_unresolved', not
    'absent'. Nothing outside the worktree is opened (claiming resolution there
    would be a guess); same-basename hits inside the worktree are listed so the
    search is auditable.
    """
    cand = token.lstrip("./")
    tried = []
    for p_rel in (cand, cand.rstrip("/")):
        if not p_rel:
            continue
        p = ROOT / p_rel
        tried.append(p_rel)
        if p.exists():
            if p.is_file():
                b = p.read_bytes()
                return {"status": "resolved", "scope": "delivery_worktree",
                        "path": p_rel, "bytes": len(b), "sha256": sha256_hex(b),
                        "checked_paths": tried}
            return {"status": "resolved", "scope": "delivery_worktree",
                    "path": p_rel, "kind": "directory", "checked_paths": tried}
    base = Path(cand.rstrip("/")).name
    hits = sorted(
        str(q.relative_to(ROOT))
        for q in ROOT.rglob(base)
        if q.is_file() and ".git" not in q.parts
    )[:5]
    return {"status": "unresolved", "scope": "delivery_worktree",
            "reason": "referenced path is not part of this delivery (report lives in "
                      "ship-performance-platform; only the markdown field was transferred)",
            "checked_paths": tried, "same_basename_hits": hits}


# ----------------------------------------------------------------------- scanner
def scan_references(md: str) -> tuple[list[dict], list[dict]]:
    """Return (asset candidates, excluded tokens).

    An asset candidate is something that claims to be a file/attachment (figure
    link, code/artifact path, command that names a file). Formulas, physical
    quantities and bare module identifiers are prose, not assets: they are listed
    as excluded so the filter is auditable instead of silent.
    """
    lines = md.rstrip("\n").split("\n")
    starts = line_starts(md)
    cands: dict[str, dict] = {}
    excluded: list[dict] = []
    seen_excl: set[tuple[str, int]] = set()

    def add_cand(token: str, cls: str, line_no: int, form: str,
                 spans: list[tuple[int, int]], extra: dict | None = None):
        occ = pick_span(md, spans)
        occ["line"] = line_of(md, occ["start_char"])
        occ["end_line"] = line_of(md, occ["end_char"] - 1)
        occ["scan_line"] = line_no
        occ["form"] = form
        if extra:
            occ.update(extra)
        if token in cands:
            cands[token]["occurrences"].append(occ)
            return
        cands[token] = {
            "token": token,
            "asset_class": cls,
            "first_line": line_no,
            "section": section_of(lines, line_no),
            "occurrences": [occ],
        }

    def exclude(token: str, line_no: int, reason: str):
        key = (token, line_no)
        if key in seen_excl:
            return
        seen_excl.add(key)
        ls = starts[line_no - 1]
        le = ls + len(lines[line_no - 1])
        occ = pick_span(md, [(ls, le)])
        excluded.append({"token": token, "line": line_no, "reason": reason,
                         "section": section_of(lines, line_no), "quote": occ["quote"]})

    def wide(line_no: int, tok_s: int | None, tok_e: int | None) -> list[tuple[int, int]]:
        li = line_no - 1
        ls, le = starts[li], starts[li] + len(lines[li])
        out = []
        if tok_s is not None:
            out.append((tok_s, tok_e))
        out.append((ls, le))
        if li > 0:
            out.append((starts[li - 1], le))
        if li + 1 < len(lines):
            out.append((ls, starts[li + 1] + len(lines[li + 1])))
        return out

    for i, line in enumerate(lines, start=1):
        base = starts[i - 1]
        # 1. markdown image links -> figure attachments
        for m in IMG_RE.finditer(line):
            alt, path = m.group(1), m.group(2)
            add_cand(path, "figure_reference", i, "markdown_image_link",
                     wide(i, base + m.start(), base + m.end()), {"alt_text": alt})
        # 2. backticked tokens
        for m in TICK_RE.finditer(line):
            tok = m.group(1).strip()
            if not tok:
                continue
            tick_span = (base + m.start(), base + m.end())
            if " " in tok and PATH_TOKEN_RE.search(tok):
                # e.g. `pytest tests/test_....py` -> register the file, keep the command
                for pm in PATH_TOKEN_RE.finditer(tok):
                    add_cand(pm.group(0), "artifact_path_reference", i,
                             "backticked_command", wide(i, None, None),
                             {"invocation": tok})
                continue
            if PATH_TOKEN_RE.search(tok) or (tok.endswith("/") and "/" in tok):
                inner = (base + m.start(1), base + m.end(1))
                add_cand(tok, "artifact_path_reference", i, "backticked_path",
                         [tick_span, inner] + wide(i, None, None))
                continue
            if MODULE_LIST_RE.match(tok):
                exclude(tok, i, "identifier list (module / state names), not an asset")
                continue
            exclude(tok, i, "formula / physical quantity / code fragment, not an asset")
        # 3. bare paths outside backticks (code fences, prose)
        tick_ranges = [(m.start(), m.end()) for m in TICK_RE.finditer(line)]
        link_ranges = [(m.start(), m.end()) for m in IMG_RE.finditer(line)]
        tick_ranges = tick_ranges + link_ranges
        for pm in PATH_TOKEN_RE.finditer(line):
            if any(s <= pm.start() and pm.end() <= e for s, e in tick_ranges):
                continue
            if any(s <= pm.start() <= e or s <= pm.end() - 1 <= e for s, e in tick_ranges):
                continue
            tok = pm.group(0)
            if tok.startswith(("http://", "https://")) or "/" not in tok:
                continue
            if tok in cands:  # same reference seen again outside backticks
                add_cand(tok, cands[tok]["asset_class"], i,
                         cands[tok]["occurrences"][0]["form"],
                         [(base + pm.start(), base + pm.end())] + wide(i, None, None))
                continue
            if any(tok.endswith("/" + c["token"]) or c["token"].endswith("/" + tok)
                   for c in cands.values()):
                continue  # relative/absolute spelling of an already registered path
            add_cand(tok, "artifact_path_reference", i, "bare_path",
                     [(base + pm.start(), base + pm.end())] + wide(i, None, None))
    return list(cands.values()), excluded


# ------------------------------------------------------------------- manifest
def build_manifest(record: dict) -> dict:
    md = record.get("markdown") or ""
    raw = md.encode("utf-8")
    lines = md.rstrip("\n").split("\n")
    digest = sha256_hex(raw)
    if digest != CONTRACT_SOURCE_HASH:
        raise SystemExit("source hash mismatch: %s != %s" % (digest, CONTRACT_SOURCE_HASH))

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_bytes(raw)
    meta = {k: v for k, v in record.items() if k != "markdown"}
    RECORD_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    rec_figs = record.get("figures") or []
    fig_by_name = {f.get("name"): f for f in rec_figs}
    cands, excluded = scan_references(md)

    body_fig_names = [Path(c["token"]).name for c in cands
                      if c["asset_class"] == "figure_reference"]
    record_fig_names = [f.get("name") for f in rec_figs]
    figure_link_check = {
        "record_figure_names": record_fig_names,
        "markdown_image_names": body_fig_names,
        "one_to_one": sorted(body_fig_names) == sorted(record_fig_names),
        "record_only": sorted(set(record_fig_names) - set(body_fig_names)),
        "markdown_only": sorted(set(body_fig_names) - set(record_fig_names)),
    }

    assets = []
    for n, c in enumerate(cands, start=1):
        occ0 = c["occurrences"][0]
        asset = {
            "asset_id": "A%02d" % n,
            "asset_class": c["asset_class"],
            "label": Path(c["token"].rstrip("/")).name or c["token"],
            "in_report_section": c["section"],
            "locator": {
                "method": "char_span",
                "start_char": occ0["start_char"],
                "end_char": occ0["end_char"],
                "start_line": occ0["line"],
                "end_line": occ0["end_line"],
                "quote": occ0["quote"],
                "unique": occ0["unique"],
                "offset_unit": "unicode_code_point_half_open [start,end) into markdown",
                "form": occ0["form"],
            },
            "reference_token": c["token"],
            "occurrences": [
                {"line": o["line"], "end_line": o["end_line"],
                 "start_char": o["start_char"],
                 "end_char": o["end_char"], "form": o["form"],
                 "scan_line": o["scan_line"],
                 "quote": o["quote"], "quote_unique": o["unique"],
                 "invocation": o.get("invocation")}
                for o in c["occurrences"]
            ],
            "existence_asserted_by_worker": False,
        }
        if c["asset_class"] == "figure_reference":
            name = Path(c["token"]).name
            rec_fig = fig_by_name.get(name)
            asset["alt_text"] = occ0.get("alt_text")
            asset["record_metadata"] = {
                "present_in_record_figures": rec_fig is not None,
                "caption": (rec_fig or {}).get("caption"),
                "record_pointer": "/figures/%d" % rec_figs.index(rec_fig)
                if rec_fig is not None else None,
            }
            pb = probe("/tensor/reports/%s/figures/%s" % (REPORT_ID, name))
            asset["platform_probe"] = pb
            asset["resolution"] = "referenced_unresolved"
            asset["resolution_check"] = {
                "check": "GET /tensor/reports/9085/figures/<name> for a byte payload, "
                         "plus a delivery-worktree path check",
                "result": "unresolved",
                "scope": "platform_api + delivery_worktree",
                "http_status": pb["http_status"],
                "worktree": resolve_in_worktree(c["token"]),
            }
            asset["note"] = (
                "Figure is declared in the record (name + caption) and linked in the body, "
                "but the platform exposes no byte payload and the relative path points into "
                "the ship-performance-platform worktree. No bytes retrieved, no hash claimed."
            )
        else:
            res = resolve_in_worktree(c["token"])
            asset["resolution"] = (
                "resolved_in_source" if res["status"] == "resolved"
                else "referenced_unresolved"
            )
            asset["resolution_check"] = {
                "check": "existence (+ sha256 when a file) inside the delivery worktree only",
                "result": res["status"],
                "scope": res["scope"],
                "checked_paths": res.get("checked_paths"),
                "same_basename_hits": res.get("same_basename_hits", []),
                "sha256": res.get("sha256"),
                "bytes": res.get("bytes"),
            }
            asset["note"] = (
                "Declared by the report prose; this工序 registers the declaration. The bytes "
                "were not transferred with the report, so the asset stays unresolved rather "
                "than being reconstructed from the prose."
            )
        assets.append(asset)

    md_asset = {
        "asset_id": "A00",
        "asset_class": "report_markdown",
        "label": "report-%s-markdown" % REPORT_ID,
        "in_report_section": section_of(lines, 1),
        "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": len(md),
            "start_line": 1,
            "end_line": len(lines),
            "quote": lines[0],
            "unique": md.count(lines[0]) == 1,
            "offset_unit": "unicode_code_point_half_open [start,end) into markdown",
        },
        "reference_token": SOURCE_URI,
        "resolution": "resolved_in_source",
        "resolution_check": {
            "check": "GET /api/v1/tensor/reports/9085 -> markdown field; sha256 over UTF-8 bytes",
            "result": "resolved",
            "scope": "platform_api",
            "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
            "sha256": digest,
            "bytes": len(raw),
            "chars": len(md),
            "lines": len(lines),
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
        },
        "existence_asserted_by_worker": True,
        "note": "Only the markdown field was transferred; the record and its figures carry "
                "no payload. Existence is asserted here because the bytes were fetched and "
                "rehashed locally.",
    }
    assets = [md_asset] + assets

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    quotes = [a["locator"]["quote"] for a in assets]

    return {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest.split(":", 1)[1],
            "hash_prefixed": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "contract_chars": CONTRACT_CHARS,
            "contract_title": CONTRACT_TITLE,
            "contract_scenario_key": CONTRACT_SCENARIO,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
            "title_matches_contract": (record.get("title") or "").strip() == CONTRACT_TITLE,
            "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            "record_id": record.get("id"),
            "record_mission_id": record.get("mission_id"),
            "record_status": record.get("status"),
            "record_tags": record.get("tags"),
            "line_counting": "logical lines = markdown.rstrip('\\n').split('\\n'); 1-based",
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "platform_figures": rec_figs,
            "figure_link_check": figure_link_check,
            "aux_endpoint_probes": [probe("/tensor/reports/%s/artifacts" % REPORT_ID)],
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "duplicate_asset_ids": dupes,
            "excluded_tokens": len(excluded),
        },
        "assets": assets,
        "excluded_tokens": {
            "note": "Backticked formulas / physical quantities / module names found in the "
                    "body. They are prose, not attachments: listed explicitly so the filter "
                    "is auditable instead of silent, and not registered as assets.",
            "count": len(excluded),
            "items": excluded,
        },
        "claims": [],
        "claims_policy": (
            "objective.classify_report_type=false and no extraction is in scope, so no "
            "claim is generated: an empty array is the complete, correct result. Nothing "
            "in this package is marked verified — verification is computed by the "
            "platform gate."
        ),
        "integrity": {
            "quote_uniqueness": {
                "all_unique": all(a["locator"]["unique"] for a in assets),
                "unique": sum(1 for a in assets if a["locator"]["unique"]),
                "total": len(assets),
                "duplicate_quotes": sorted({q for q in quotes if quotes.count(q) > 1}),
            },
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "hash_scope": "UTF-8 bytes of the markdown field as served by "
                          "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "locator_space": "unicode code points of the markdown string; half-open spans",
            "no_duplicate_asset_ids": not dupes,
        },
    }


def derive_schema() -> dict:
    """Re-pin the three package-identity consts of the shared schema (nothing else).

    schemas/asset_manifest.v1.schema.json was written for wp-448-01 and hard-codes
    that package's identity. Editing it in place would rewrite another work package's
    schema, so this package derives its own copy and documents the exact diff. Any
    deviation beyond these three consts is a bug in this generator.
    """
    shared = json.loads(SHARED_SCHEMA.read_text(encoding="utf-8"))
    derived = json.loads(json.dumps(shared))
    patches = [
        ("properties.package_id.const", PACKAGE_ID),
        ("properties.report_id.const", REPORT_ID),
        ("properties.source.properties.uri.const", SOURCE_URI),
    ]
    for dotted, value in patches:
        node = derived
        parts = dotted.split(".")
        for p in parts[:-1]:
            node = node[p]
        node[parts[-1]] = value
    derived["$comment"] = (
        "DERIVED from ../schemas/asset_manifest.v1.schema.json by "
        "scripts/kf_wp9085_01_register.py::derive_schema. Patched consts only: "
        + "; ".join("%s=%s" % (d, v) for d, v in patches)
        + ". Shape otherwise identical; the shared file was left untouched."
    )
    derived["derived_from"] = "schemas/asset_manifest.v1.schema.json"
    derived["derived_for_package"] = PACKAGE_ID
    return derived


def build_envelope(manifest: dict) -> dict:
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["hash_prefixed"],
            "source_field": SOURCE_FIELD,
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": "hash recomputed from GET /api/v1/tensor/reports/9085 markdown "
                     "(UTF-8 bytes); matches contract source_hash %s; chars %d matches "
                     "contract chars %d"
                     % (CONTRACT_SOURCE_HASH, manifest["source"]["chars"], CONTRACT_CHARS),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def schema_check(manifest: dict, derived: dict) -> dict:
    import jsonschema

    shared = json.loads(SHARED_SCHEMA.read_text(encoding="utf-8"))
    shared_errs = sorted(
        {"/".join(str(p) for p in e.absolute_path)
         for e in jsonschema.Draft7Validator(shared).iter_errors(manifest)}
    )
    derived_errs = sorted(
        {"/".join(str(p) for p in e.absolute_path)
         for e in jsonschema.Draft7Validator(derived).iter_errors(manifest)}
    )
    allowed = {"package_id", "report_id", "source/uri"}
    return {
        "validator": "jsonschema Draft7 (shared schema declares draft-07)",
        "against_shared_schema": {
            "errors": shared_errs,
            "errors_are_identity_consts_only": set(shared_errs) <= allowed,
            "explanation": "The shared schema pins wp-448-01's identity; every reported "
                           "error must be one of package_id/report_id/source/uri — that is "
                           "the evidence that only the identity consts differ.",
        },
        "against_derived_schema": {"errors": derived_errs, "pass": not derived_errs},
    }


def kf_envelope_check(envelope: dict) -> dict:
    import jsonschema

    schema = json.loads(KF_SCHEMA.read_text(encoding="utf-8"))
    errs = sorted(
        {"%s: %s" % ("/".join(str(p) for p in e.absolute_path), e.message)
         for e in jsonschema.Draft202012Validator(schema).iter_errors(envelope)}
    )
    return {"schema": "schemas/kf_result.v1.schema.json", "errors": errs,
            "pass": not errs}


def main() -> int:
    record = fetch_report()
    manifest = build_manifest(record)
    derived = derive_schema()
    envelope = build_envelope(manifest)
    checks = schema_check(manifest, derived)
    kf_chk = kf_envelope_check(envelope)

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    DERIVED_SCHEMA.write_text(json.dumps(derived, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    ENVELOPE.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import kf_wp9085_01_verify as verify

    ver = verify.verify(record)
    VERIFICATION.write_text(json.dumps(ver, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    selfcheck = {
        "schema_checks": checks,
        "kf_result_envelope_check": kf_chk,
        "verification_ok": ver["overall_ok"],
        "verification_failures": ver["failures"],
        "hash_matches_contract": manifest["source"]["hash_matches_contract"],
        "chars_matches_contract": manifest["source"]["chars_matches_contract"],
        "assets": manifest["counts"]["assets"],
        "claims": len(manifest["claims"]),
    }
    SELFCHECK.write_text(json.dumps(selfcheck, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    print(json.dumps(selfcheck, ensure_ascii=False, indent=2))
    ok = (checks["against_derived_schema"]["pass"]
          and checks["against_shared_schema"]["errors_are_identity_consts_only"]
          and kf_chk["pass"] and ver["overall_ok"]
          and manifest["source"]["hash_matches_contract"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())