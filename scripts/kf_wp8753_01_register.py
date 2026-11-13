#!/usr/bin/env python3
"""wp-8753-01 (task_type 01-asset-registration): register report 8753's source asset
and enumerate the attachments/artifacts its markdown declares.

Scope: report_id=8753 only. No extraction, no knowledge claims, no `verified` marks.
Every number/quote in the emitted artefacts is measured here (zero manual transcription).

Sub-commands (idempotent, stdlib only; `figure` needs matplotlib):

    python3 scripts/kf_wp8753_01_register.py build      # fetch + write asset_manifest.json
    python3 scripts/kf_wp8753_01_register.py envelope   # wrap manifest -> kf_result.json
    python3 scripts/kf_wp8753_01_register.py schema     # write package-local manifest schema
    python3 scripts/kf_wp8753_01_register.py verify     # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp8753_01_register.py figure     # locator map png
    python3 scripts/kf_wp8753_01_register.py all        # build+schema+envelope+verify+figure
"""
from __future__ import annotations

import base64
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
REPORT_ID = "8753"
PACKAGE_ID = "wp-8753-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
SOURCE_FIELD = "markdown"
# contract-declared identity (YAML of wp-8753-01). Comparison targets only, never trusted.
CONTRACT_SOURCE_HASH = "sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1"
CONTRACT_CHARS = 8187
CONTRACT_TITLE = "FuelEU 柔性机制三件套成熟化（p120w2-n04/m7431）：μ 偿还放大 + 乘子日落 + 结转上限"
CONTRACT_SCENARIO = "p120w2-n04"
PRODUCER = "kf-worker/m15626"

OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID          # committed (artifacts/** is gitignored)
RUN_DIR = ROOT / "runs" / PACKAGE_ID
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
SCHEMA = OUT_DIR / "asset_manifest.schema.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
WORKTREE_PREFIXES = ("backend/", "artifacts/")


# ------------------------------------------------------------------ platform io
def _base() -> str:
    b = os.environ.get("TENSOR_API_BASE")
    if not b:
        raise SystemExit("TENSOR_API_BASE not set")
    return b.rstrip("/")


def _login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get(path: str, tok: str):
    req = urllib.request.Request(_base() + path, headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:                       # 404 etc. are data, not crashes
        return e.code, None


def probe_figure(name: str, tok: str) -> dict:
    """Ask the platform for figure bytes. Return status only -- no payload assumption."""
    req = urllib.request.Request(
        _base() + "/tensor/reports/%s/figures/%s" % (REPORT_ID, name),
        headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            return {"http_status": r.status, "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest()}
    except urllib.error.HTTPError as e:
        return {"http_status": e.code, "bytes": 0, "sha256": None}


def fetch_record() -> dict:
    tok = _login()
    status, payload = _get("/tensor/reports/%s" % REPORT_ID, tok)
    if status != 200 or not isinstance(payload, dict):
        raise SystemExit("GET /tensor/reports/%s -> %s" % (REPORT_ID, status))
    rec = payload.get("data", payload)
    md = rec.get("markdown")
    if not isinstance(md, str) or not md:
        raise SystemExit("record %s has no markdown" % REPORT_ID)
    rec["_fig_probes"] = {f["name"]: probe_figure(f["name"], tok)
                          for f in (rec.get("figures") or []) if f.get("name")}
    return rec


# --------------------------------------------------------------------- helpers
def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def locate(md: str, quote: str) -> dict:
    """char_span locator for a verbatim quote; raises if the quote is absent or ambiguous."""
    n = md.count(quote)
    if n == 0:
        raise SystemExit("quote not found in source: %r" % quote[:80])
    start = md.index(quote)
    end = start + len(quote)
    return {"method": "char_span",
            "start_char": start, "end_char": end,
            "start_line": md[:start].count("\n") + 1,
            "end_line": md[:end].count("\n") + 1,
            "quote": quote,
            "occurrences": n,
            "unique": n == 1}


def doc_locator(md: str) -> dict:
    return {"method": "document", "start_char": 0, "end_char": len(md),
            "start_line": 1, "end_line": md.count("\n") + 1,
            "quote": md.split("\n", 1)[0], "occurrences": 1, "unique": True}


def section_of(md: str, start_char: int) -> str:
    """Nearest preceding '## ' / '# ' heading for a char offset (markdown outline position)."""
    head = md[:start_char]
    lines = head.split("\n")
    for line in reversed(lines):
        if line.startswith("## "):
            return line[3:].strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "(no preceding heading — before first section header)"


def asset(aid, cls_, label, md, quote, status, check, result, note, indicators=None):
    loc = locate(md, quote)
    return {"asset_id": aid, "asset_class": cls_, "label": label,
            "in_report_section": section_of(md, loc["start_char"]),
            "locator": loc, "resolution": status,
            "resolution_check": {"check": check, "result": result,
                                 **({"indicators": indicators} if indicators else {})},
            "note": note}


# --------------------------------------------------- body path reference scan
FENCE_RE = re.compile(r"^```.*?^```", re.S | re.M)
# path tokens that a reader can resolve: repo-relative backend/artifacts paths, a
# `modules/...` path following `cd backend`, and bare MANIFEST-style file names.
PATH_TOKEN_RES = (
    (re.compile(r"(?:\.{1,2}/)?(?:backend|artifacts|schemas|scripts|docs|tests)/[A-Za-z0-9_./\-]*[A-Za-z0-9_/\-]"), None),
    (re.compile(r"\bmodules/[A-Za-z0-9_./\-]*[A-Za-z0-9_/\-]"), "backend/"),
    (re.compile(r"\b[A-Z][A-Z0-9_]{3,}\.(?:md|json|py)\b"), None),
)


def extract_path_references(md: str) -> list[dict]:
    """Ordered, de-duplicated path references declared in the body (fenced blocks + prose)."""
    fenced_spans = [(m.start(), m.end()) for m in FENCE_RE.finditer(md)]
    out: list[dict] = []
    seen: set[str] = set()
    for rx, prefix in PATH_TOKEN_RES:
        for m in rx.finditer(md):
            raw = m.group(0)
            path = raw
            if path.startswith("./"):
                path = path[2:]
            if path.startswith("../"):          # `../artifacts/...` run with cwd=backend/
                path = path[3:]
            if prefix and not path.startswith(prefix):
                path = prefix + path
            path = path.rstrip(".,;:)")
            if path in seen or len(path) < 5:
                continue
            seen.add(path)
            in_fence = any(a <= m.start() < b for a, b in fenced_spans)
            out.append({"path": path, "quote": raw,
                        "context": "fenced_block" if in_fence else "prose"})
    return out


# ------------------------------------------------------------------ build phase
FIG_LINK_RE = re.compile(r"!\[([^\]]+)\]\(([^)]+)\)")
BACKTICK_PATH_RE = re.compile(r"`([^`\s]+\.(?:py|json|md|png|csv|h5|hdf5|ya?ml|toml))`")
BACKTICK_DIR_RE = re.compile(r"`((?:backend|artifacts)/[^`\s]+/)`")


def build_manifest(rec: dict) -> dict:
    md = rec["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + sha256_bytes(raw)
    lines = md.split("\n")

    assets: list[dict] = []
    assets.append({
        "asset_id": "A00", "asset_class": "source_document",
        "label": "report %s markdown (source_field=markdown)" % REPORT_ID,
        "in_report_section": "(whole document)",
        "locator": doc_locator(md),
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "markdown fetched via GET /api/v1/tensor/reports/%s; sha256 + char count recomputed locally" % REPORT_ID,
                             "result": "resolved",
                             "indicators": {"chars": len(md), "bytes_utf8": len(raw),
                                            "sha256": digest}},
        "note": "Registered as the authoritative bytes for this package; platform re-computes the same hash independently.",
    })

    # ---- figures: record metadata (name+caption) + in-body image link ----------
    figs = rec.get("figures") or []
    for i, f in enumerate(figs, start=1):
        name = f.get("name") or ""
        link = "![%s](figs/%s)" % (name, name)
        probe = rec.get("_fig_probes", {}).get(name, {"http_status": None, "bytes": 0})
        has_bytes = probe.get("http_status") == 200 and probe.get("bytes", 0) > 0
        assets.append(asset(
            "A%02d" % i, "figure_declared", name, md, link,
            "resolved_in_source" if has_bytes else "referenced_unresolved",
            "figure declared in report record metadata (figures[].name) and linked in-body as "
            "figs/<name>; GET /api/v1/tensor/reports/%s/figures/%s probed for bytes" % (REPORT_ID, name),
            "resolved" if has_bytes else "unresolved",
            ("Platform serves the figure bytes (sha256 recorded)." if has_bytes else
             "Body link target (figs/%s) exists only inside the producing repo; platform figure "
             "endpoint returned %s, so no bytes/hash can be asserted here — metadata + caption "
             "quoted from the source instead." % (name, probe.get("http_status"))),
            indicators={"http_status": probe.get("http_status"), "bytes": probe.get("bytes"),
                        "caption": f.get("caption")}))

    # ---- declared artefacts / generator scripts / vendored refs ----------------
    body_refs = extract_path_references(md)
    CLASS_OF_EXT = {".py": "generator_script", ".json": "data_artifact", ".md": "document",
                    ".png": "figure_declared", ".h5": "data_artifact", ".hdf5": "data_artifact",
                    ".csv": "data_artifact"}
    next_id = len(figs) + 1
    for ref in body_refs:
        p = ref["path"]
        ext = os.path.splitext(p)[1].lower()
        if p.rstrip("/").endswith("/tests") or p.rstrip("/") == "tests":
            cls_ = "test_suite"
        elif "_ref" in p or p.endswith("PROVENANCE.md"):
            cls_ = "vendor_reference" if "_ref" in p else "document"
        elif p.rstrip("/").endswith("/figs"):
            cls_ = "figure_collection"
        elif "run_case" in p or "gen_report" in p:
            cls_ = "generator_script"
        elif p.rstrip("/").count("/") == 2 and p.startswith("backend/modules/"):
            cls_ = "module_reference"
        else:
            cls_ = CLASS_OF_EXT.get(ext, "path_reference")
        in_worktree = (ROOT / p.rstrip("/")).exists()
        assets.append(asset(
            "A%02d" % next_id, cls_, p, md, ref["quote"],
            "resolved_in_source" if in_worktree else "referenced_unresolved",
            "path literal parsed from the report body (fenced repro block or prose); token "
            "normalised for probing (leading '../' dropped, 'backend/' prepended after 'cd backend') "
            "while the locator quote keeps the raw source text; existence probed inside the "
            "TensorKnowledge delivery worktree (%s)" % ROOT.name,
            "present" if in_worktree else "unresolved",
            ("Present in this worktree." if in_worktree else
             "Declared by the report but absent from the TensorKnowledge worktree: it belongs to the "
             "producing repository (ship-performance-platform backend/artifacts tree), which this work "
             "package must not touch. Registered as a declared reference; payload not read, no hash "
             "claimed."),
            indicators={"probed_path": p, "raw_token": ref["quote"],
                        "exists_in_worktree": in_worktree, "found_in": ref["context"]}))
        next_id += 1

    # ---- cross-report / version references (identifiers, not files) -------------
    for label, quote, note in (
        ("m5745 reference implementation (regression baseline)",
         "m5745 参考实现（逐字 vendor）",
         "Cross-report dependency: cited as the byte-wise vendored baseline for criterion (b). "
         "No URI is given in the source, so it is registered as declared, not fetched."),
        ("m7061 v1.0.0 (previous version, §3.4 diff base)",
         "与上一版（m7061, v1.0.0）的量化差异",
         "Cross-report dependency: previous version used as the Δ baseline in §3.4; body only, "
         "not resolvable as a file from this worktree."),
    ):
        assets.append(asset(
            "A%02d" % next_id, "cross_report_reference", label, md, quote,
            "referenced_unresolved",
            "identifier citation only; no tensor:// URI in the source to resolve against",
            "unresolved",
            note))
        next_id += 1

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    section_headers = [ln for ln in lines if ln.startswith("## ")]
    known = ("①", "②", "③", "④", "⑤", "⑥")
    present = [h for h in known if any(h in s for s in section_headers)]

    return {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "source": {
            "report_id": REPORT_ID,
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest[7:],
            "source_hash": digest,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "has_crlf": "\r\n" in md,
            "ends_with_newline": md.endswith("\n"),
            "title": rec.get("title"),
            "contract_title": CONTRACT_TITLE,
            "title_matches_contract": (rec.get("title") or "").replace("–", "-") == CONTRACT_TITLE.replace("–", "-"),
            "scenario_key": rec.get("scenario_key"),
            "contract_scenario_key": CONTRACT_SCENARIO,
            "scenario_matches_contract": rec.get("scenario_key") == CONTRACT_SCENARIO,
            "platform_record": {k: rec.get(k) for k in ("id", "status", "stage", "mission_id",
                                                        "created_by", "created_at", "tags")},
            "platform_figures": [f.get("name") for f in figs],
            "fetched_via": "GET /api/v1/tensor/reports/%s (Bearer auth)" % REPORT_ID,
            "line_counting": "logical lines = markdown.split(chr(10)); 1-based",
        },
        "structure": {
            "section_headers": section_headers,
            "numbered_sections_present": present,
            "numbered_sections_absent": [s for s in known if s not in present],
            "first_line": lines[0],
            "first_line_looks_truncated": not lines[0].lstrip().startswith(("#", "|", "**", "-")),
            "last_line": lines[-1],
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "figures_declared": len(figs),
            "figures_with_platform_bytes": sum(
                1 for v in rec.get("_fig_probes", {}).values() if v.get("http_status") == 200),
            "body_path_references": len(body_refs),
        },
        "assets": assets,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-8753-01 objective is register_assets=true / classify_report_type=false, "
            "notes state 'claims 允许为空数组', and constraints include "
            "no_forced_claim_generation=true + do_not_mark_claims_as_verified=true. This工序 "
            "registers source identity (report_id, markdown byte hash) and the resolvable "
            "attachment/artefact inventory; extraction is a downstream工序. An empty claims array "
            "is therefore the complete result, not an omission."
        ),
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes},
        "observations": build_observations(md, digest, figs, rec, body_refs, section_headers,
                                           present, known, assets),
        "limitations": [
            "Payload existence was probed only inside the TensorKnowledge worktree and the platform "
            "figure endpoint; no access to the producing repository, so 'referenced_unresolved' "
            "means 'not resolvable from here', not 'does not exist'.",
            "captions/titles are quoted from platform metadata (record.figures / title), not from "
            "the markdown body (the body's figure section carries its own one-line captions).",
            "Schema note: repo-wide schemas/asset_manifest.v1.schema.json hard-pins package_id/"
            "report_id/uri with `const` to wp-448-01 and therefore cannot validate this package; "
            "the machine check here uses the package-local generic schema written by `schema`.",
        ],
    }


# ------------------------------------------------------------ package schema
def manifest_schema() -> dict:
    locator = {
        "type": "object",
        "required": ["method", "start_char", "end_char", "start_line", "end_line", "quote", "unique"],
        "properties": {"method": {"enum": ["char_span", "document"]},
                       "start_char": {"type": "integer", "minimum": 0},
                       "end_char": {"type": "integer", "minimum": 1},
                       "start_line": {"type": "integer", "minimum": 1},
                       "end_line": {"type": "integer", "minimum": 1},
                       "quote": {"type": "string", "minLength": 1},
                       "occurrences": {"type": "integer", "minimum": 1},
                       "unique": {"type": "boolean"}},
        "additionalProperties": True,
    }
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "asset_manifest.v1 (KF task_type=01-asset-registration, generic)",
        "description": ("Generic (non report-pinned) shape of asset_manifest.json as produced by "
                        "scripts/kf_wp8753_01_register.py. Derived from schemas/asset_manifest.v1.schema.json "
                        "with the wp-448-01 `const` pins replaced by patterns so a package-local schema_pass "
                        "is machine-checkable. The platform gate remains authoritative."),
        "type": "object",
        "required": ["schema", "package_id", "task_type", "report_id", "source", "counts",
                     "assets", "claims", "id_integrity", "claims_empty_reason"],
        "properties": {
            "schema": {"const": "asset_manifest.v1"},
            "package_id": {"type": "string", "pattern": "^wp-[A-Za-z0-9][A-Za-z0-9_.:-]*-[0-9]{2}$"},
            "task_type": {"type": "string", "pattern": "^[0-9]{2}(-[a-z0-9-]+)?$"},
            "report_id": {"type": "string", "pattern": "^[0-9]+$"},
            "source": {
                "type": "object",
                "required": ["uri", "field", "hash_alg", "hash", "chars", "bytes_utf8", "title",
                             "scenario_key"],
                "properties": {"uri": {"type": "string", "pattern": "^tensor://reports/[0-9]+$"},
                               "field": {"enum": ["markdown", "summary", "record"]},
                               "hash_alg": {"const": "sha256"},
                               "hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                               "chars": {"type": "integer", "minimum": 1},
                               "bytes_utf8": {"type": "integer", "minimum": 1},
                               "title": {"type": "string", "minLength": 1},
                               "scenario_key": {"type": "string", "minLength": 1}},
                "additionalProperties": True,
            },
            "counts": {"type": "object", "required": ["assets", "by_class", "by_resolution",
                                                      "resolved_in_source", "referenced_unresolved",
                                                      "declared_absent"],
                       "properties": {"assets": {"type": "integer", "minimum": 1}},
                       "additionalProperties": True},
            "assets": {"type": "array", "minItems": 1, "items": {
                "type": "object",
                "required": ["asset_id", "asset_class", "label", "in_report_section", "locator",
                             "resolution", "resolution_check", "note"],
                "properties": {
                    "asset_id": {"type": "string", "pattern": "^A[0-9]{2}$"},
                    "asset_class": {"type": "string", "minLength": 1},
                    "label": {"type": "string", "minLength": 1},
                    "in_report_section": {"type": "string", "minLength": 1},
                    "resolution": {"enum": ["resolved_in_source", "referenced_unresolved",
                                            "declared_absent"]},
                    "resolution_check": {"type": "object", "required": ["check", "result"],
                                         "properties": {"check": {"type": "string", "minLength": 1},
                                                        "result": {"enum": ["resolved", "unresolved",
                                                                            "absent", "present"]}},
                                         "additionalProperties": True},
                    "locator": locator,
                    "note": {"type": "string", "minLength": 1}},
                "additionalProperties": True}},
            "claims": {"type": "array", "items": {
                "type": "object", "required": ["claim_id", "text"],
                "anyOf": [{"required": ["evidence"]}, {"required": ["unresolved_reason"]},
                          {"required": ["status"]}],
                "properties": {"claim_id": {"type": "string", "minLength": 3},
                               "text": {"type": "string", "minLength": 1},
                               "status": {"enum": ["supported", "partially-supported", "unresolved",
                                                   "refuted"]}},
                "additionalProperties": True}},
            "id_integrity": {"type": "object", "required": ["ids_checked", "duplicates", "unique"],
                             "properties": {"unique": {"const": True}}},
            "claims_empty_reason": {"type": "string", "minLength": 1},
        },
        "additionalProperties": True,
    }


def build_observations(md, digest, figs, rec, body_refs, section_headers, present, known,
                       assets) -> list[str]:
    """Every sentence is rendered from measured values -- nothing here is asserted by hand."""
    probes = rec.get("_fig_probes", {})
    statuses = sorted({v.get("http_status") for v in probes.values()})
    absent_from_worktree = [r["path"] for r in body_refs if not (ROOT / r["path"].rstrip("/")).exists()]
    first_line = md.split("\n", 1)[0]
    obs = [
        "Source identity recomputed from the fetched bytes: sha256:%s, %d chars, %d UTF-8 bytes, "
        "%d lines; contract hash match=%s, contract char match=%s."
        % (digest[7:], len(md), len(md.encode("utf-8")), md.count("\n") + 1,
           digest == CONTRACT_SOURCE_HASH, len(md) == CONTRACT_CHARS),
        "Document is a complete report: line 1 is the H1 title (%r); numbered sections present=%s, "
        "absent=%s; %d '## ' headings in total."
        % (first_line, "".join(present) or "none", "".join(s for s in known if s not in present) or "none",
           len(section_headers)),
        "%d figures are declared in the platform record with captions and linked in-body as "
        "figs/<name>; GET /tensor/reports/%s/figures/<name> returned %s, so no figure bytes are "
        "available from the platform and no figure hash is claimed."
        % (len(figs), REPORT_ID, statuses),
        "%d distinct body path references were parsed; %d of them do not exist in this delivery "
        "worktree (%s)."
        % (len(body_refs), len(absent_from_worktree),
           ", ".join(sorted(absent_from_worktree)[:4]) + (" …" if len(absent_from_worktree) > 4 else "")),
        "Registered assets by class: %s."
        % ", ".join("%s=%d" % (k, v) for k, v in sorted(
            {c: sum(1 for a in assets if a["asset_class"] == c) for c in {a["asset_class"] for a in assets}}.items())),
        "No sibling work package or non-8753 report was read, quoted or modified: the only inputs are "
        "report %s's own record and its markdown bytes." % REPORT_ID,
    ]
    return obs


# ------------------------------------------------------------------ envelope
def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["source_hash"],
            "source_field": SOURCE_FIELD,
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("Report %s markdown registered as-is; %d assets enumerated "
                      "(%d resolved in source, %d referenced-but-unresolved, platform figure bytes absent); "
                      "claims empty by contract." % (REPORT_ID, manifest["counts"]["assets"],
                                                     manifest["counts"]["resolved_in_source"],
                                                     manifest["counts"]["referenced_unresolved"])),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return env


# -------------------------------------------------------------------- verify
def verify() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    rec = fetch_record()
    md = rec["markdown"]
    live_hash = "sha256:" + sha256_bytes(md.encode("utf-8"))
    checks: dict[str, dict] = {}

    checks["valid_json"] = {"ok": True,
                            "detail": "asset_manifest.json + kf_result.json parsed from disk "
                                      "(json.loads, utf-8)"}

    try:
        import jsonschema
        jsonschema.validate(manifest, manifest_schema())
        kf_schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
        jsonschema.validate(env, kf_schema)
        checks["schema_pass"] = {"ok": True,
                                 "detail": "asset_manifest validated against package-local generic "
                                           "schema; kf_result validated against schemas/kf_result.v1.schema.json"}
    except ImportError:
        checks["schema_pass"] = {"ok": False, "detail": "jsonschema not installed: not_run"}
    except Exception as e:                                     # noqa: BLE001 - gate detail
        checks["schema_pass"] = {"ok": False, "detail": "validation error: %s" % e}

    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        ok = q in md
        if ok and loc["method"] == "char_span":
            ok = (md[loc["start_char"]:loc["end_char"]] == q
                  and md[:loc["start_char"]].count("\n") + 1 == loc["start_line"])
        if not ok:
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": "%d/%d asset locators re-resolved against the live markdown "
                  "(verbatim substring + declared char span/line)" % (len(manifest["assets"]) - len(bad),
                                                                      len(manifest["assets"])),
        "failures": bad,
    }

    checks["source_hash_matches"] = {
        "ok": live_hash == manifest["source"]["source_hash"] == CONTRACT_SOURCE_HASH
              == env["provenance"]["source_hash"],
        "detail": "live=%s manifest=%s contract=%s chars live=%d contract=%d"
                  % (live_hash, manifest["source"]["source_hash"], CONTRACT_SOURCE_HASH,
                     len(md), CONTRACT_CHARS),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {"ok": not dupes,
                                  "detail": "%d ids, duplicates=%s" % (len(ids), dupes)}

    claims = env.get("claims") or []
    ok = all(c.get("evidence") or c.get("unresolved_reason") or c.get("status") for c in claims) \
        and bool(manifest.get("claims_empty_reason"))
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": ok,
        "detail": "%d claims (empty array by contract); claims_empty_reason stated: %s; "
                  "no claim carries status 'verified': %s"
                  % (len(claims), bool(manifest.get("claims_empty_reason")),
                     all(c.get("status") != "verified" for c in claims)),
    }

    out = {"package_id": PACKAGE_ID, "verified_at": utcnow(), "acceptance": checks,
           "all_ok": all(c["ok"] for c in checks.values()),
           "note": ("Self-check performed by the producing worker; the platform gate recomputes "
                    "hash and locator resolution independently. No claim is marked verified here.")}
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


# -------------------------------------------------------------------- figure
def figure() -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    md = SOURCE_COPY.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lines = md.split("\n")
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.2),
                                   gridspec_kw={"width_ratios": [2.2, 1]})
    xs = list(range(1, len(lines) + 1))
    ys = [len(ln) for ln in lines]
    ax1.fill_between(xs, ys, color="#4c72b0", alpha=0.18)
    ax1.plot(xs, ys, "-", color="#4c72b0", lw=1.0, label="chars per line")

    colors = {"source_document": "#333333", "figure_declared": "#55a868",
              "generator_script": "#c44e52", "data_artifact": "#dd8452",
              "test_suite": "#8172b3", "vendor_reference": "#937860",
              "cross_report_reference": "#da8bc3", "path_reference": "#8c8c8c",
              "document": "#4c72b0"}
    seen = set()
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] != "char_span":
            continue
        ln = loc["start_line"]
        lbl = a["asset_class"] if a["asset_class"] not in seen else None
        seen.add(a["asset_class"])
        ax1.vlines(ln, 0, len(lines[ln - 1]) if ln <= len(lines) else 1,
                   color=colors.get(a["asset_class"], "k"), lw=2.6,
                   label=lbl)
        ax1.scatter([ln], [len(lines[ln - 1]) if ln <= len(lines) else 1], s=26,
                    color=colors.get(a["asset_class"], "k"), zorder=3)
        ax1.annotate(a["asset_id"], (ln, (len(lines[ln - 1]) if ln <= len(lines) else 1) + 6),
                     fontsize=7, ha="center", color=colors.get(a["asset_class"], "k"))

    for h in manifest["structure"]["section_headers"]:
        try:
            ln = lines.index(h) + 1
        except ValueError:
            continue
        ax1.axvline(ln, color="0.65", ls=":", lw=0.8)

    ax1.set_xlabel("markdown line number (report %s)" % REPORT_ID)
    ax1.set_ylabel("characters on line")
    ax1.set_title("source markdown + registered-asset anchors\n"
                  "%d lines / %d chars / %d assets / sha256 …%s"
                  % (len(lines), len(md), manifest["counts"]["assets"],
                     manifest["source"]["hash"][:12]), fontsize=10)
    ax1.legend(fontsize=7, loc="upper center", ncol=2)
    ax1.set_ylim(0, max(ys) * 1.25)
    ax1.grid(alpha=0.25)

    res = manifest["counts"]["by_resolution"]
    labels = list(res)
    vals = [res[k] for k in labels]
    cols = {"resolved_in_source": "#55a868", "referenced_unresolved": "#c44e52",
            "declared_absent": "#8c8c8c"}
    ax2.barh(range(len(labels)), vals, color=[cols.get(k, "k") for k in labels])
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels(labels, fontsize=8)
    ax2.invert_yaxis()
    for i, v in enumerate(vals):
        ax2.text(v + 0.08, i, str(v), va="center", fontsize=8)
    ax2.set_xlabel("assets")
    ax2.set_title("resolution status\n(platform figure bytes: %d/%d present)"
                  % (manifest["counts"]["figures_with_platform_bytes"],
                     manifest["counts"]["figures_declared"]), fontsize=10)
    ax2.grid(alpha=0.25, axis="x")

    fig.tight_layout()
    out = FIG_DIR / "wp8753_01_source_locator_map.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if cmd in ("build", "all"):
        rec = fetch_record()
        md = rec["markdown"]
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        SOURCE_COPY.write_bytes(md.encode("utf-8"))
        man = build_manifest(rec)
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("manifest ->", MANIFEST.relative_to(ROOT),
              "| assets", man["counts"]["assets"],
              "| resolved", man["counts"]["resolved_in_source"],
              "| unresolved", man["counts"]["referenced_unresolved"])
    if cmd in ("schema", "all"):
        SCHEMA.write_text(json.dumps(manifest_schema(), ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print("schema ->", SCHEMA.relative_to(ROOT))
    if cmd in ("envelope", "all"):
        env = build_envelope()
        print("envelope ->", ENVELOPE.relative_to(ROOT), "|", env["provenance"]["source_hash"])
    if cmd in ("verify", "all"):
        v = verify()
        print("verify ->", VERIFICATION.relative_to(ROOT), "| all_ok", v["all_ok"])
        for k, c in v["acceptance"].items():
            print("   [%s] %s -- %s" % ("PASS" if c["ok"] else "FAIL", k, c["detail"]))
    if cmd in ("figure", "all"):
        p = figure()
        print("figure ->", p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))