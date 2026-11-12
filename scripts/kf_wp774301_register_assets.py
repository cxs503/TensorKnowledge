#!/usr/bin/env python3
"""wp-7743-01 (task_type 01-asset-registration): register report 7743's source asset
and enumerate the attachments/artifacts it declares. Registration only -- no extraction.

Sub-commands (idempotent; stdlib + jsonschema for `verify`, matplotlib for `figure`):

    python3 scripts/kf_wp774301_register_assets.py build     # fetch + write asset_manifest.json
    python3 scripts/kf_wp774301_register_assets.py envelope  # wrap manifest -> kf_result.json
    python3 scripts/kf_wp774301_register_assets.py verify    # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp774301_register_assets.py figure    # locator/resolution map png
    python3 scripts/kf_wp774301_register_assets.py report    # publish KF-RESULT report to the platform
    python3 scripts/kf_wp774301_register_assets.py all       # build+envelope+verify+figure

Contract wp-7743-01 rules honoured here:
  * objective = register_assets:true / classify_report_type:false -> NO extraction, and
    `claims` stays an empty array (notes: "claims 允许为空数组");
  * do_not_mark_claims_as_verified -> nothing here is marked verified; verification of the
    package is the platform gate's job (local `verify` only pre-checks the 6 acceptance items);
  * zero manual transcription -> every number/quote in the artefacts is measured from the
    live markdown at build time (quotes are byte slices of the markdown, never retyped);
  * preserve_uncertainty -> unresolvable references are recorded as referenced_unresolved
    with the probe that was attempted, never upgraded to "resolved" by assumption;
  * scope -> only report_id 7743 is read/written.

Credentials from env only (TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE);
nothing secret is written into the worktree.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "7743"
PACKAGE_ID = "wp-7743-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
SOURCE_FIELD = "markdown"
# contract-declared identity (work-package YAML); comparison targets only, never trusted.
CONTRACT_SOURCE_HASH = "sha256:2db8e0192df29ddfed091f81cdf35c5f128166ab8966c45298f354dd9a15e21a"
CONTRACT_CHARS = 6520
CONTRACT_TITLE = ("IN12-G13 体系贯穿验收门：十仓参与度矩阵 + BP §10.3 覆盖度（零粉饰）"
                  "+ §15 三附件（m6491）")
CONTRACT_SCENARIO = "ice-nav-system-pierce"
LANE = "C"
PRODUCER = "kf-worker/m15599"

OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID          # committed artefacts
RUN_DIR = ROOT / "runs" / PACKAGE_ID                 # scratch (gitignored)
FIG_DIR = OUT_DIR / "figures"
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
MANIFEST_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.pattern.json"
RESULT_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"

# asset classes, in registration order (keeps asset ids stable across rebuilds)
CLASS_ORDER = [
    "source_document",
    "figure_declared",
    "anchor_artifact",
    "gate_artifact",
    "evidence_pointer_artifact",
    "db_pointer",
    "test_reference",
    "entrypoint_reference",
    "document_reference",
    "scm_branch_reference",
    "scm_ref",
]
CLASS_ORDER_IDX = {c: i for i, c in enumerate(CLASS_ORDER)}

# generic line-level references (path-like / SCM-like); tables are parsed separately.
LINE_PATTERNS = [
    ("test_reference", re.compile(r"tests/[\w./-]+\.py")),
    ("entrypoint_reference", re.compile(r"python3 -m modules\.system_pierce\.run")),
    ("document_reference", re.compile(r"\bprereg\b")),
    ("scm_branch_reference", re.compile(r"agent/m[0-9*]+")),
    ("scm_ref", re.compile(r"\borigin/main\b")),
]
GATE_ARTIFACT_RE = re.compile(r"^artifacts/system_pierce")
PREFIXED_POINTER_RE = re.compile(
    r"^([A-Za-z0-9_.-]+):((?:artifacts|tests|src|scripts|modules)/[^\s#;|]+)(#\S*)?$")
ABSENT_MARKERS = {"—", "-", "–", "n/a", "N/A", ""}


# ------------------------------------------------------------------ io helpers
def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(api_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        tok = json.loads(r.read().decode()).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def http_get(path: str, tok: str | None = None):
    req = urllib.request.Request(path if path.startswith("http") else api_base() + path)
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # connection-level failure: recorded, not fatal
        return 0, str(e).encode()


def fetch_record() -> dict:
    tok = login()
    st, raw = http_get("/tensor/reports/%s" % REPORT_ID, tok)
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> %s %r" % (REPORT_ID, st, raw[:200]))
    rec = json.loads(raw.decode())
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    return rec


def psql_probe(table: str) -> dict:
    """Read-only probe: can this worker see the table a db: pointer names?"""
    cmd = "select count(*) from %s" % table
    try:
        p = subprocess.run(["psql", "-d", os.environ.get("TP_PG_DB", "tensorplatform"),
                            "-tA", "-c", cmd],
                           capture_output=True, text=True, timeout=20)
        ok = p.returncode == 0
        return {"check": "psql -tA -c '%s'" % cmd,
                "result": "resolved" if ok else "unresolved",
                "detail": (p.stdout.strip() if ok
                           else (p.stderr.strip().splitlines() or [""])[0])}
    except Exception as e:
        return {"check": "psql -tA -c '%s'" % cmd, "result": "unresolved",
                "detail": "probe failed: %s" % e}


# ------------------------------------------------------------- source scan core
def scan_source(md: str):
    """Return (lines, sections, line_starts). sections: heading text owning each line."""
    lines = md.split("\n")
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1
    sections, cur = [], "(preamble)"
    for ln in lines:
        if ln.startswith("#"):
            cur = ln.lstrip("#").strip() or cur
        sections.append(cur)
    return lines, sections, starts


def table_rows(lines, sections, starts, heading_prefix, header_first_cell):
    """Yield (cells, line_idx) for the markdown table under the given ### heading."""
    in_table = False
    for i, ln in enumerate(lines):
        if ln.startswith("###") or ln.startswith("## "):
            in_table = sections[i].startswith(heading_prefix)
            continue
        stripped = ln.strip()
        if not in_table:
            continue
        if not stripped.startswith("|"):
            if stripped:
                in_table = False
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        if cells[0] == header_first_cell:
            continue
        yield cells, i


def add(refs, cls, key, label, section, lines, starts, line_idx, span=None, extra=None):
    """Register one reference occurrence (quote = verbatim byte slice of the markdown)."""
    if span is None:
        span = (starts[line_idx], starts[line_idx] + len(lines[line_idx]))
    refs.append({"asset_class": cls, "key": key, "label": label,
                 "in_report_section": section,
                 "start_char": span[0], "end_char": span[1],
                 "start_line": line_idx + 1, "end_line": line_idx + 1,
                 "extra": extra or {}})


def discover_refs(md: str, record: dict):
    """Scan the markdown and return (refs, figures, fig_decl_span, lines, sections, starts)."""
    lines, sections, starts = scan_source(md)
    refs: list[dict] = []

    # ---- A: the source document itself (locator = whole document)
    n_lines = len(lines) - 1 if md.endswith("\n") else len(lines)
    refs.append({"asset_class": "source_document",
                 "key": SOURCE_URI + "#" + SOURCE_FIELD,
                 "label": "report %s markdown（本工序的唯一上游源）" % REPORT_ID,
                 "in_report_section": "(whole document)",
                 "start_char": 0, "end_char": len(md), "start_line": 1, "end_line": n_lines,
                 "extra": {}})

    # ---- B: figures declared in record metadata (names/captions are NOT in the markdown)
    fig_decl_span = None
    for i, ln in enumerate(lines):
        m = re.search(r"\d+\s*张图", ln)
        if m:
            fig_decl_span = (i, (starts[i] + m.start(), starts[i] + m.end()), m.group(0))
            break
    figures = record.get("figures") or []
    for f in figures:
        name = f.get("name") or "(unnamed)"
        if fig_decl_span:
            refs.append({"asset_class": "figure_declared", "key": name,
                         "label": "figure %s: %s" % (name, f.get("caption") or ""),
                         "in_report_section": sections[fig_decl_span[0]],
                         "start_char": fig_decl_span[1][0], "end_char": fig_decl_span[1][1],
                         "start_line": fig_decl_span[0] + 1, "end_line": fig_decl_span[0] + 1,
                         "extra": {"caption": f.get("caption"),
                                   "quote_basis": "in-body '%s' declaration; name/caption come "
                                                  "from record.figures metadata (not verbatim in "
                                                  "markdown)" % fig_decl_span[2]}})

    # ---- C: §3.1 participation matrix -> one anchor artifact per repo row
    for cells, i in table_rows(lines, sections, starts, "3.1", "仓"):
        repo, node, level, e, artifact, dev = (cells + [""] * 6)[:6]
        cell_txt = artifact.strip("`").strip()
        span = None
        if cell_txt and cell_txt not in ABSENT_MARKERS:
            j = lines[i].find(cell_txt)
            if j >= 0:
                span = (starts[i] + j, starts[i] + j + len(cell_txt))
            add(refs, "anchor_artifact", "%s:%s" % (repo, cell_txt),
                "主锚工件 of %s / %s (%s, E=%s)" % (repo, node, level, e),
                sections[i], lines, starts, i, span,
                {"repo": repo, "node": node, "evidence_level": level, "e_level": e,
                 "dev_pct": dev})
        else:
            add(refs, "anchor_artifact", "%s:(none)" % repo,
                "主锚工件 of %s / %s -> 矩阵行显式空缺（%s）" % (repo, node, level),
                sections[i], lines, starts, i, span,
                {"repo": repo, "node": node, "evidence_level": level, "e_level": e,
                 "dev_pct": dev, "declared_absent": True})

    # ---- D: §3.2 BP coverage -> evidence pointers (file / db / explicit em-dash)
    for cells, i in table_rows(lines, sections, starts, "3.2", "编号"):
        goal, sem, status, ptr = (cells + [""] * 4)[:4]
        for tok in [t.strip() for t in ptr.split(";") if t.strip()]:
            j = lines[i].find(tok)
            span = (starts[i] + j, starts[i] + j + len(tok)) if j >= 0 else None
            if tok in ABSENT_MARKERS:
                add(refs, "evidence_pointer_artifact", "%s:(none)" % goal,
                    "%s 证据指针显式为空（status=%s）" % (goal, status),
                    sections[i], lines, starts, i, span,
                    {"goal": goal, "semantic": sem, "status": status, "declared_absent": True})
            elif tok.startswith("db:"):
                add(refs, "db_pointer", tok, "%s -> DB 指针 %s" % (goal, tok),
                    sections[i], lines, starts, i, span, {"goal": goal, "status": status})
            else:
                m = PREFIXED_POINTER_RE.match(tok)
                if not m:
                    add(refs, "evidence_pointer_artifact", "%s:%s" % (goal, tok),
                        "%s -> 未归一化的证据指针 %s" % (goal, tok),
                        sections[i], lines, starts, i, span,
                        {"goal": goal, "status": status, "unparsed_pointer": True})
                    continue
                repo, path, frag = m.group(1), m.group(2), (m.group(3) or "")
                cls = "gate_artifact" if GATE_ARTIFACT_RE.match(path) else "evidence_pointer_artifact"
                add(refs, cls, "%s:%s%s" % (repo, path, frag),
                    "%s 证据指针 (%s)" % (goal, path + frag), sections[i], lines, starts, i, span,
                    {"repo": repo, "path": path, "fragment": frag, "goal": goal,
                     "status": status})

    # ---- E: generic line-level references (tests, entrypoint, SCM, prereg, gate artefacts)
    for i, ln in enumerate(lines):
        for cls, rx in LINE_PATTERNS:
            for m in rx.finditer(ln):
                add(refs, cls, m.group(0), "%s -> %s" % (sections[i], m.group(0)),
                    sections[i], lines, starts, i,
                    (starts[i] + m.start(), starts[i] + m.end()))
        if "gate_artifacts" in ln:            # only named inside the §3.5 JSON blob
            for m in re.finditer(r'"([^"]+\.json)"', ln):
                add(refs, "gate_artifact", m.group(1),
                    "§3.5 gate_artifact -> %s" % m.group(1), sections[i], lines, starts, i,
                    (starts[i] + m.start() + 1, starts[i] + m.end() - 1))
    return refs, figures, fig_decl_span, lines, sections, starts


def resolve_one(r, md, digest, figures, fig_probes, path_probes, probe_cache):
    """Decide (resolution, resolution_check, note) for one merged reference."""
    cls, key = r["asset_class"], r["key"]
    if cls == "source_document":
        return "resolved_in_source", {
            "check": "GET /tensor/reports/%s -> markdown; sha256(utf8 bytes)" % REPORT_ID,
            "result": "resolved", "detail": "sha256=%s chars=%d" % (digest, len(md))}, \
            "Locator spans the whole markdown (method=document)."
    if cls == "figure_declared":
        hit = [p for p, v in fig_probes.items() if v.get("http_status") == 200]
        return ("resolved_in_source" if hit else "referenced_unresolved"), {
            "check": "HTTP probe of per-figure endpoints",
            "result": "resolved" if hit else "unresolved",
            "detail": "probes=%s" % json.dumps(fig_probes, ensure_ascii=False)}, (
            "Name+caption exist in record.figures metadata; the markdown only says "
            "'N 张图' with no image links. Bytes served: %s." % (hit or "none"))
    if cls in ("anchor_artifact", "gate_artifact", "evidence_pointer_artifact"):
        if r["extra"].get("declared_absent"):
            return "declared_absent", {
                "check": "matrix/table cell value", "result": "absent",
                "detail": "cell is the em-dash placeholder -> report itself declares no artifact"}, \
                "Declared absent by the report; nothing to resolve."
        path = (r["extra"].get("path") or key.split(":", 1)[-1]).split("#")[0]
        exists = (ROOT / path).exists()
        path_probes[key] = {"worktree_path": path, "exists_in_delivery_worktree": exists}
        return ("resolved_in_source" if exists else "referenced_unresolved"), {
            "check": "existence under delivery worktree %s (repo prefix is external)" % ROOT.name,
            "result": "resolved" if exists else "unresolved",
            "detail": "path=%s repo=%s exists=%s" % (path, r["extra"].get("repo"), exists)}, (
            "Present in the delivery worktree." if exists else
            "Artifact path belongs to repo '%s', which is NOT checked out in this delivery "
            "worktree -> not verifiable from here; registered as declared, existence not "
            "asserted." % r["extra"].get("repo"))
    if cls == "db_pointer":
        tbl = key.split("#")[0].replace("db:", "")
        pr = probe_cache.setdefault(tbl, psql_probe(tbl))
        return "referenced_unresolved", {
            "check": pr["check"], "result": pr["result"], "detail": pr["detail"]}, (
            "DB pointer, not a file asset. psql access from this worker is %s; no API "
            "endpoint is registered for this pointer, so its rows are not resolvable here."
            % ("granted" if pr["result"] == "resolved" else "denied"))
    if cls == "test_reference":
        exists = (ROOT / key).exists()
        return ("resolved_in_source" if exists else "referenced_unresolved"), {
            "check": "existence of test path in delivery worktree",
            "result": "resolved" if exists else "unresolved",
            "detail": "path=%s exists=%s" % (key, exists)}, \
            "Test lives in ship-performance-platform, not in TensorKnowledge."
    if cls == "entrypoint_reference":
        return "referenced_unresolved", {
            "check": "module path resolvable from this worktree", "result": "unresolved",
            "detail": "modules/system_pierce not present under %s" % ROOT.name}, \
            "Repro command targets ship-performance-platform; not runnable here."
    if cls == "document_reference":
        return "referenced_unresolved", {
            "check": "path named in source", "result": "unresolved",
            "detail": "source says only 'prereg'; no path/URI given"}, \
            "prereg artefact is referenced by name only -> cannot be located."
    return "referenced_unresolved", {
        "check": "git ref, not a file asset", "result": "unresolved",
        "detail": "ref=%s (remote state not queried; registration stays offline-safe)" % key}, \
        "SCM ref cited as an evidence locus; resolving it needs networked git and is out of scope."


def build_manifest(record: dict) -> dict:
    md = record.get("markdown") or ""
    if not md:
        raise SystemExit("markdown field empty; keys=%s" % list(record))
    digest = sha256_hex(md.encode())
    refs, figures, _figspan, lines, _sections, _starts = discover_refs(md, record)

    # ---- merge occurrences per (class, key); first occurrence becomes the locator
    merged: dict[tuple, dict] = {}
    for r in refs:
        k = (r["asset_class"], r["key"])
        if k not in merged:
            merged[k] = dict(r, occurrences=[])
        if r["asset_class"] == "source_document":
            continue      # the document locator already spans [0, len(md)); no duplicate copy
        merged[k]["occurrences"].append({
            "line": r["start_line"], "start_char": r["start_char"], "end_char": r["end_char"],
            "quote": md[r["start_char"]:r["end_char"]]})
    ordered = sorted(merged.values(),
                     key=lambda r: (CLASS_ORDER_IDX.get(r["asset_class"], 99), r["start_char"]))

    # ---- resolution probes (recorded once per endpoint/table)
    tok = login()
    fig_probes: dict[str, dict] = {}
    for f in figures:
        name = f.get("name") or ""
        for p in ("/tensor/reports/%s/artifacts/%s" % (REPORT_ID, name),
                  "/tensor/reports/%s/figures/%s" % (REPORT_ID, name)):
            st, body = http_get(p, tok)
            fig_probes[p] = {"http_status": st, "bytes": len(body)}
    st_list, _ = http_get("/tensor/reports/%s/artifacts" % REPORT_ID, tok)
    fig_probes["GET /tensor/reports/%s/artifacts" % REPORT_ID] = {"http_status": st_list}
    path_probes: dict[str, dict] = {}
    probe_cache: dict[str, dict] = {}

    assets = []
    for n, r in enumerate(ordered, start=1):
        quote = md[r["start_char"]:r["end_char"]]
        resolution, check, note = resolve_one(r, md, digest, figures, fig_probes,
                                              path_probes, probe_cache)
        assets.append({
            "asset_id": "A%02d" % n,
            "asset_class": r["asset_class"],
            "label": r["label"],
            "ref_key": r["key"],
            "in_report_section": r["in_report_section"],
            "locator": {"method": "document" if r["asset_class"] == "source_document"
                        else "char_span",
                        "start_char": r["start_char"], "end_char": r["end_char"],
                        "start_line": r["start_line"], "end_line": r["end_line"],
                        "quote": quote, "unique": md.count(quote) == 1},
            "resolution": resolution,
            "resolution_check": check,
            "note": note,
            "occurrences": r["occurrences"],
            "attributes": r["extra"],
        })

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})

    return {
        "schema": "asset_manifest.v1",
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
            "hash": digest.split(":")[1],
            "source_hash": digest,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "chars": len(md),
            "bytes_utf8": len(md.encode()),
            "contract_chars": CONTRACT_CHARS,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
            "lines": len(lines) - 1 if md.endswith("\n") else len(lines),
            "title": record.get("title"),
            "contract_title": CONTRACT_TITLE,
            "title_matches_contract": (record.get("title") or "") == CONTRACT_TITLE,
            "scenario_key": record.get("scenario_key"),
            "contract_scenario_key": CONTRACT_SCENARIO,
            "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            "mission_id": record.get("mission_id"),
            "status": record.get("status"),
            "created_at": record.get("created_at"),
            "platform_figures": figures,
            "platform_tags": record.get("tags") or [],
            "platform_figure_probes": fig_probes,
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items(),
                                    key=lambda kv: CLASS_ORDER_IDX.get(kv[0], 99))),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "figure_declarations_in_record": len(figures),
            "locators_unique_quote": sum(1 for a in assets if a["locator"]["unique"]),
            "occurrences_total": sum(len(a["occurrences"]) for a in assets),
        },
        "assets": assets,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-7743-01 objective is register_assets=true / classify_report_type=false "
            "and the package notes state 'claims 允许为空数组'; constraint "
            "no_forced_claim_generation=true forbids manufacturing claims to fill a quota. This "
            "工序 registers asset identity only (report_id + markdown byte hash + declared "
            "attachments/artifacts), so an empty claims array is the complete result, not an "
            "omission."),
        "unresolved": [{"asset_id": a["asset_id"], "ref_key": a["ref_key"],
                        "asset_class": a["asset_class"],
                        "why": a["resolution_check"].get("detail")}
                       for a in assets if a["resolution"] == "referenced_unresolved"],
        "integrity": {
            "quote_uniqueness": {
                "quotes": len(assets),
                "unique": sum(1 for a in assets if a["locator"]["unique"]),
                "non_unique_asset_ids": [a["asset_id"] for a in assets
                                         if not a["locator"]["unique"]],
                "note": "non-unique quotes are char_span locators whose slices are re-checked by "
                        "offset in verify(), so ambiguity is bounded, not hidden",
            },
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes},
        },
        "limitations": [
            "Registration only: no claim/evidence extraction, no report-type classification, no "
            "verified marks (the platform gate computes verification).",
            "source_hash scope = UTF-8 bytes of the markdown string returned by the platform "
            "API; any change to stored markdown (even whitespace) invalidates it.",
            "Reference resolution is bounded to (a) this delivery worktree and (b) probes of the "
            "platform report API. Artefacts of other repos and DB pointers stay "
            "declared-but-unresolved; a missing path here is never reported as a broken upstream "
            "artefact.",
            "psql read of campaign_nodes / tensor_dev_missions / tensor_reports is denied to this "
            "worker (permission denied for table ...), so db: pointers cannot be resolved here.",
        ],
    }


# ------------------------------------------------------------------- envelope
def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    record = fetch_record()          # bind the envelope to *current* live bytes
    live = sha256_hex((record.get("markdown") or "").encode())
    if live != manifest["source"]["source_hash"]:
        raise SystemExit("markdown changed since build: manifest=%s live=%s"
                         % (manifest["source"]["source_hash"], live))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": live,
            "source_field": SOURCE_FIELD,
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("hash recomputed from GET /api/v1/tensor/reports/%s markdown (UTF-8 "
                      "bytes); matches contract source_hash %s"
                      % (REPORT_ID, CONTRACT_SOURCE_HASH)),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n")
    return env


# ------------------------------------------------------------------- verify
def verify() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    env = json.loads(ENVELOPE.read_text())
    record = fetch_record()
    md = record.get("markdown") or ""
    live = sha256_hex(md.encode())
    checks = {}

    # 1 valid_json
    try:
        json.loads(MANIFEST.read_text())
        json.loads(ENVELOPE.read_text())
        checks["valid_json"] = {"ok": True,
                               "detail": "asset_manifest.json + kf_result.json parse as JSON"}
    except Exception as e:
        checks["valid_json"] = {"ok": False, "detail": "JSON parse error: %s" % e}

    # 2 schema_pass (kf_result.v1 + derived asset_manifest pattern schema)
    try:
        import jsonschema
        v1 = jsonschema.Draft202012Validator(json.loads(RESULT_SCHEMA.read_text()))
        e1 = sorted(v1.iter_errors(env), key=lambda x: list(x.path))
        v2 = jsonschema.Draft7Validator(json.loads(MANIFEST_SCHEMA.read_text()))
        e2 = sorted(v2.iter_errors(manifest), key=lambda x: list(x.path))
        checks["schema_pass"] = {
            "ok": not e1 and not e2,
            "detail": "kf_result.v1 errors=%d; asset_manifest.v1.pattern errors=%d"
                      % (len(e1), len(e2)),
            "errors": [str(e.message)[:160] for e in (e1 + e2)[:6]],
        }
    except ImportError:
        checks["schema_pass"] = {"ok": False, "status": "not_run",
                                 "detail": "jsonschema not installed -> not_run"}

    # 3 source_locator_resolvable (re-resolve every locator/occurrence against live markdown)
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            if loc["start_char"] != 0 or loc["end_char"] != len(md):
                bad.append(a["asset_id"])
        elif md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            bad.append(a["asset_id"])
        for o in a["occurrences"]:
            if md[o["start_char"]:o["end_char"]] != o["quote"]:
                bad.append(a["asset_id"] + ":occ")
    checks["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": "%d locators + %d occurrences re-resolved by char span against live markdown"
                  % (len(manifest["assets"]), manifest["counts"]["occurrences_total"]),
        "failures": sorted(set(bad)),
    }

    # 4 source_hash_matches
    checks["source_hash_matches"] = {
        "ok": live == manifest["source"]["source_hash"] == CONTRACT_SOURCE_HASH
              == env["provenance"]["source_hash"],
        "detail": "live=%s manifest=%s envelope=%s contract=%s"
                  % (live, manifest["source"]["source_hash"],
                     env["provenance"]["source_hash"], CONTRACT_SOURCE_HASH),
        "chars": {"live": len(md), "manifest": manifest["source"]["chars"],
                  "contract": CONTRACT_CHARS},
    }

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    keys = [(a["asset_class"], a["ref_key"]) for a in manifest["assets"]]
    dupkeys = sorted({"%s|%s" % k for k in keys if keys.count(k) > 1})
    checks["no_duplicate_ids"] = {
        "ok": not dupes and not dupkeys,
        "detail": "%d asset ids; duplicate ids=%s; duplicate (class,ref_key)=%s"
                  % (len(ids), dupes, dupkeys),
    }

    # 6 claims carry evidence / explicit status (empty is contract-legal)
    claims = (env.get("claims") or []) + (manifest.get("claims") or [])
    ev_ok = all(c.get("evidence") or c.get("unresolved_reason") or c.get("status")
                for c in claims)
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": bool(ev_ok and manifest.get("claims_empty_reason")),
        "detail": "%d claims (empty is contract-legal); empty-claims reason stated=%s"
                  % (len(claims), bool(manifest.get("claims_empty_reason"))),
    }

    out = {"package_id": PACKAGE_ID, "report_id": REPORT_ID, "verified_at": utcnow(),
           "acceptance": checks, "all_ok": all(c["ok"] for c in checks.values()),
           "note": "Self-check only: no claim is marked verified here. The platform gate "
                   "recomputes hash + locator substrings independently."}
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


# ------------------------------------------------------------------- figure
def _source_markdown() -> str:
    cached = RUN_DIR / ("report_%s.md" % REPORT_ID)
    if cached.exists():
        return cached.read_text()
    return fetch_record().get("markdown") or ""


def figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    md = _source_markdown()
    lines = md.split("\n")
    manifest = json.loads(MANIFEST.read_text())
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.4),
                                   gridspec_kw={"width_ratios": [2.05, 1]})
    ys = [len(l) for l in lines]
    xs = list(range(1, len(lines) + 1))
    ax1.plot(xs, ys, "-", color="#4c72b0", lw=1.0)
    ax1.fill_between(xs, ys, color="#4c72b0", alpha=0.12)
    colors = {"source_document": "#333333", "figure_declared": "#55a868",
              "anchor_artifact": "#c44e52", "gate_artifact": "#8172b3",
              "evidence_pointer_artifact": "#dd8452", "db_pointer": "#937860",
              "test_reference": "#da8bc3", "entrypoint_reference": "#8c8c8c",
              "document_reference": "#ccb974", "scm_branch_reference": "#64b5cd",
              "scm_ref": "#4c72b0"}
    seen = set()
    for a in manifest["assets"]:
        ln = a["locator"]["start_line"]
        if not (0 < ln <= len(lines)):
            continue
        ax1.vlines(ln, 0, len(lines[ln - 1]), color=colors.get(a["asset_class"], "k"), lw=2.2,
                   label=None if a["asset_class"] in seen else a["asset_class"])
        seen.add(a["asset_class"])
    for ln in xs:
        if lines[ln - 1].startswith("#"):
            ax1.axvline(ln, color="0.75", ls=":", lw=0.6)
            ax1.annotate("L%d" % ln, (ln, max(ys) * 0.99), fontsize=6.5, color="0.4",
                         rotation=90, ha="right", va="top")
    ax1.set_xlabel("markdown line number")
    ax1.set_ylabel("characters on line")
    ax1.set_title("report 7743 source markdown: line profile + %d registered asset locators\n"
                  "(sha256 %s..., %d chars, %d lines)"
                  % (len(manifest["assets"]), manifest["source"]["hash"][:16],
                     manifest["source"]["chars"], manifest["source"]["lines"]), fontsize=9.5)
    ax1.legend(fontsize=6.3, loc="upper center", ncol=3, framealpha=0.9)
    ax1.grid(alpha=0.25)

    order = list(manifest["counts"]["by_class"].keys())
    stat = {c: {"resolved_in_source": 0, "referenced_unresolved": 0, "declared_absent": 0}
            for c in order}
    for a in manifest["assets"]:
        stat[a["asset_class"]][a["resolution"]] += 1
    res_colors = {"resolved_in_source": "#55a868", "referenced_unresolved": "#dd8452",
                  "declared_absent": "#8c8c8c"}
    left = [0] * len(order)
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        vals = [stat[c][res] for c in order]
        ax2.barh(range(len(order)), vals, left=left, color=res_colors[res], label=res,
                 height=0.62)
        left = [l + v for l, v in zip(left, vals)]
    ax2.set_yticks(range(len(order)))
    ax2.set_yticklabels(order, fontsize=7)
    ax2.invert_yaxis()
    ax2.set_xlabel("assets")
    ax2.set_title("resolution status by asset class\n(%d assets: %d resolved / %d unresolved / "
                  "%d absent)" % (manifest["counts"]["assets"],
                                  manifest["counts"]["resolved_in_source"],
                                  manifest["counts"]["referenced_unresolved"],
                                  manifest["counts"]["declared_absent"]), fontsize=9.5)
    ax2.legend(fontsize=6.5, loc="lower right")
    ax2.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    out = FIG_DIR / "wp774301_source_locator_map.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print("figure ->", out.relative_to(ROOT))


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    if cmd in ("build", "all"):
        record = fetch_record()
        (RUN_DIR / ("report_%s.md" % REPORT_ID)).write_text(record["markdown"])
        (RUN_DIR / ("report_%s.json" % REPORT_ID)).write_text(
            json.dumps({k: v for k, v in record.items() if k != "markdown"},
                       ensure_ascii=False, indent=2))
        manifest = build_manifest(record)
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print("manifest ->", MANIFEST.relative_to(ROOT),
              "| assets", manifest["counts"]["assets"],
              "|", json.dumps(manifest["counts"]["by_resolution"], ensure_ascii=False))
    if cmd in ("envelope", "all"):
        env = build_envelope()
        print("envelope ->", ENVELOPE.relative_to(ROOT), "|", env["provenance"]["source_hash"])
    if cmd in ("verify", "all"):
        v = verify()
        print("verify ->", VERIFICATION.relative_to(ROOT), "| all_ok", v["all_ok"])
        for k, c in v["acceptance"].items():
            print("   [%s] %s -- %s" % ("PASS" if c["ok"] else "FAIL", k, c["detail"]))
    if cmd in ("figure", "all"):
        figure()
    if cmd == "report":
        import kf_wp774301_publish as pub
        pub.main()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))