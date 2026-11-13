#!/usr/bin/env python3
"""wp-11267-01 (task_type 01-asset-registration): register report 11267's source asset
and enumerate the attachments/artifacts the report declares.

    python3 scripts/kf_wp1126701_register_assets.py build      # fetch + write asset_manifest.json
    python3 scripts/kf_wp1126701_register_assets.py envelope   # manifest -> kf_result.json
    python3 scripts/kf_wp1126701_register_assets.py verify     # acceptance checks -> verification.json
    python3 scripts/kf_wp1126701_register_assets.py all        # build+envelope+verify

Design rules (contract wp-11267-01):
  * registration only -- NO claim extraction, NO verified marks (claims == [] by contract);
  * zero manual transcription -- every number/quote in the artefacts is measured here;
  * every asset carries a locator (char span + line + verbatim quote) re-checked against a
    freshly fetched markdown at verify time;
  * failures abort loudly instead of emitting a half manifest.
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
REPORT_ID = "11267"
PACKAGE_ID = "wp-11267-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID

# contract-declared identity (work-package YAML): comparison targets only, never trusted.
CONTRACT_SOURCE_HASH = "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f"
CONTRACT_CHARS = 7482
CONTRACT_TITLE = ("TensorPhysics: MPI 域分解并行 FEM 基础设施与强/弱扩展验证 "
                  "(p284w3-n04)")
CONTRACT_SCENARIO = "p284w3-n04-fem-mpi-parallel"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID      # committed; .gitignore drops artifacts/**
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
RECORD_COPY = RUN_DIR / ("record_%s.json" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
MANIFEST_SCHEMA = OUT_DIR / "asset_manifest.schema.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
PRODUCER = "kf-worker/m15695"

IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
TICK_RE = re.compile(r"`([^`\n]+)`")
CJ_RE = re.compile(r"\bcj[0-9]{3,}\b")
MODULE_CMD_RE = re.compile(r"^python\s+-m\s+([A-Za-z_][\w.]*)$")
TEST_SYMBOL_RE = re.compile(r"^test_[A-Za-z0-9_]+$")
PATH_RE = re.compile(r"^(?:\./)?(?:[\w.\-]+/)*[\w.\-*]+\.(?:py|json|png|jpg|jpeg|md|csv|h5|hdf5|sh|ya?ml|txt)$")
DIR_RE = re.compile(r"^(?:\./)?(?:[\w.\-]+/)+$")

BARE_IMG_RE = re.compile(r"^[\w.\-]+\.(?:png|jpe?g)$")
PATHSCAN_RE = re.compile(r"(?<![\w/.\-])(?:\./)?(?:[\w.\-]+/)+[\w.\-*]+\.(?:py|json|png|jpe?g|md|csv|h5|hdf5|sh|ya?ml|txt)(?![\w/])")
DIRSCAN_RE = re.compile(r"(?<![\w/.\-])(?:src|scripts|tests|artifacts|figures|docs|data|examples|benchmarks|tools)/[\w.\-/]+/")
MODSCAN_RE = re.compile(r"python\s+-m\s+([A-Za-z_][\w.]*)")
GAP_ROW_RE = re.compile(r"^\|\s*(C[0-9]_[a-z0-9_]+)\s*\|.*(?:not measured|未测量)")
EXT_CLASS = {".py": "code_script", ".json": "data_artifact", ".png": "figure_artifact",
             ".jpg": "figure_artifact", ".jpeg": "figure_artifact",
             ".md": "document_reference", ".csv": "data_artifact",
             ".h5": "data_artifact", ".hdf5": "data_artifact", ".sh": "code_script",
             ".yaml": "config_artifact", ".yml": "config_artifact", ".txt": "data_artifact"}


def classify_path(tok: str) -> str:
    if tok.startswith("tests/"):
        return "test_suite"
    if tok.startswith("src/") or DIR_RE.match(tok):
        return "code_module_path"
    if tok.startswith("figures/"):
        return "figure_artifact"
    return EXT_CLASS.get(Path(tok).suffix.lower(), "referenced_artifact")


def is_pathlike(tok: str) -> bool:
    t = tok.strip()
    if not t or "\n" in t or " " in t or t.startswith("-"):
        return False
    if MODULE_CMD_RE.match(t):
        return True
    return bool(PATH_RE.match(t) or DIR_RE.match(t))


def _api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(_api_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def fetch_record() -> dict:
    st, raw = _get("/tensor/reports/%s" % REPORT_ID, _login())
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> %s %r" % (REPORT_ID, st, raw[:200]))
    rec = json.loads(raw)
    if not isinstance(rec.get("markdown"), str) or not rec["markdown"]:
        raise SystemExit("record has no markdown payload")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_text(rec["markdown"], encoding="utf-8")
    RECORD_COPY.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def sha256_hex(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def line_offsets(lines):
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return offs


def line_of(offs, char: int) -> int:
    lo = 0
    for i in range(len(offs) - 1, -1, -1):
        if offs[i] <= char:
            lo = i
            break
    return lo + 1


def norm_name(tok: str) -> str:
    """Section 4 names the figures bare (`strong_scaling.png`) while the in-body links use
    `figures/strong_scaling.png`; normalise to the link form so both collapse into one asset."""
    t = tok.strip()
    if t.lower().endswith((".png", ".jpg", ".jpeg")) and "/" not in t:
        return "figures/" + t
    return t


def scan_hits(lines, offs):
    hits = []

    def push(cls, name, label, line_no, start, end, quote, form):
        hits.append({"asset_class": cls, "name": name, "label": label, "line": line_no,
                     "start": start, "end": end, "quote": quote, "form": form})

    for idx, line in enumerate(lines):
        base = offs[idx]
        for m in IMG_RE.finditer(line):
            push("figure_artifact", norm_name(m.group(2)), m.group(1).strip(), idx + 1,
                 base + m.start(2), base + m.end(2), m.group(2), "markdown_image_link")
        for m in PATHSCAN_RE.finditer(line):
            tok = m.group(0)
            push(classify_path(norm_name(tok)), norm_name(tok), tok, idx + 1,
                 base + m.start(0), base + m.end(0), tok, "path_token")
        for m in DIRSCAN_RE.finditer(line):
            tok = m.group(0)
            if PATHSCAN_RE.match(tok) or tok.startswith("figures/"):
                continue
            push("code_module_path", tok, tok, idx + 1, base + m.start(0), base + m.end(0),
                 tok, "directory_token")
        for m in MODSCAN_RE.finditer(line):
            mod = m.group(1)
            if "." not in mod:      # top-level tools (python -m pytest) are commands, not artifacts
                continue
            push("run_command", mod, mod, idx + 1, base + m.start(0),
                 base + m.end(0), m.group(0), "module_entrypoint")
        for m in TICK_RE.finditer(line):
            tok = m.group(1).strip()
            if BARE_IMG_RE.match(tok):
                push("figure_artifact", norm_name(tok), tok, idx + 1, base + m.start(1),
                     base + m.end(1), tok, "backticked_filename")
                continue
            if TEST_SYMBOL_RE.match(tok):
                push("test_symbol", tok, tok, idx + 1, base + m.start(1), base + m.end(1),
                     tok, "backticked_symbol")
        for m in CJ_RE.finditer(line):
            push("cluster_job", m.group(0), m.group(0), idx + 1,
                 base + m.start(0), base + m.end(0), m.group(0), "job_id")
        g = GAP_ROW_RE.match(line.strip())
        if g:
            push("declared_measurement_gap", g.group(1), g.group(1), idx + 1,
                 base, base + len(line), line, "criteria_table_row")

    # MPIComm caveat: the backend name and the "not measured here" statement sit on different
    # lines, so look ahead from the first mention instead of requiring a single line.
    caveat = None
    for i, line in enumerate(lines):
        if "MPIComm" not in line or caveat is not None:
            continue
        for j in range(i, min(i + 6, len(lines))):
            if "未在本机实测" in lines[j] or "未实测" in lines[j]:
                caveat = j
                break
    if caveat is not None:
        line = lines[caveat]
        push("declared_measurement_gap", "MPIComm_local_measurement",
             "MPIComm backend, local measurement", caveat + 1,
             offs[caveat], offs[caveat] + len(line), line, "caveat_sentence")

    hits.sort(key=lambda h: (h["line"], h["start"], h["asset_class"]))
    # one locator per (class, name, span); the same span can be found by two scanners
    seen, uniq = set(), []
    for h in hits:
        key = (h["asset_class"], h["name"], h["start"], h["end"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    return uniq


def section_of(lines, line_no: int) -> str:
    title = "(document root)"
    for i in range(line_no - 1, -1, -1):
        s = lines[i].strip()
        if s.startswith("## ") or s.startswith("### "):
            title = s.lstrip("#").strip()
            break
    return title


def probe_worktree(name: str) -> dict:
    if "*" in name:
        matches = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(name))
        return {"check": "glob in TensorKnowledge worktree: %s" % name,
                "result": "resolved" if matches else "unresolved",
                "glob_matches": matches[:10], "glob_match_count": len(matches)}
    p = ROOT / name
    return {"check": "path exists in TensorKnowledge worktree: %s" % name,
            "result": "resolved" if p.exists() else "unresolved", "path": str(p)}


def build_manifest(record: dict) -> dict:
    md = record["markdown"]
    raw = md.encode("utf-8")
    digest = sha256_hex(raw)
    lines = md.split("\n")
    offs = line_offsets(lines)
    hash_match = digest == CONTRACT_SOURCE_HASH
    if not hash_match:
        raise SystemExit("source hash %s != contract %s" % (digest, CONTRACT_SOURCE_HASH))

    tok = _login()
    fig_probes = {}
    for fig in record.get("figures") or []:
        nm = fig.get("name", "")
        st, body = _get("/tensor/reports/%s/figures/%s" % (REPORT_ID, nm), tok)
        fig_probes[nm] = {"http_status": st, "bytes": len(body),
                          "sha256": sha256_hex(body) if st == 200 and body else None,
                          "png_magic": body[:8] == b"\x89PNG\r\n\x1a\n",
                          "looks_like_json_error": body[:1] in (b"{", b"[")}
    st_art, body_art = _get("/tensor/reports/%s/artifacts" % REPORT_ID, tok)
    artifact_probe = {"path": "/tensor/reports/%s/artifacts" % REPORT_ID,
                      "http_status": st_art, "bytes": len(body_art),
                      "body_head": body_art[:200].decode("utf-8", "replace")}

    hits = scan_hits(lines, offs)
    grouped, order = {}, []
    for h in hits:
        key = (h["asset_class"], h["name"])
        loc = {"source_field": "markdown", "line": h["line"], "start_char": h["start"],
               "end_char": h["end"], "quote": h["quote"],
               "quote_sha256": sha256_hex(h["quote"].encode("utf-8")),
               "quote_in_source": h["quote"] in md,
               "on_declared_span": md[h["start"]:h["end"]] == h["quote"]}
        if key not in grouped:
            grouped[key] = {"asset_class": h["asset_class"], "name": h["name"],
                            "label": h["label"], "form": h["form"], "first_line": h["line"],
                            "start": h["start"], "end": h["end"], "quote": h["quote"],
                            "occurrences": []}
            order.append(key)
        grouped[key]["occurrences"].append(loc)

    fig_referenced = {h["name"] for h in hits if h["asset_class"] == "figure_artifact"}
    # a directory token that is just the prefix of a declared file path is not a separate asset
    file_names = [k[1] for k in order if k[0] not in ("code_module_path",)]
    for key in [k for k in order if k[0] == "code_module_path"]:
        if any(n.startswith(key[1]) for n in file_names):
            order.remove(key)
            grouped.pop(key, None)
    assets = []
    for i, key in enumerate(order, start=1):
        g = grouped[key]
        name = g["name"]
        wt = probe_worktree(name)
        if g["asset_class"] == "figure_artifact":
            fp = fig_probes.get(Path(name).name, {})
            served = (fp.get("http_status") == 200 and (fp.get("bytes") or 0) > 0
                      and fp.get("png_magic") is True)
            res = "resolved_in_source" if served else "referenced_unresolved"
            check = {"check": "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, Path(name).name),
                     "result": "resolved" if served else "unresolved",
                     "http_status": fp.get("http_status"), "bytes": fp.get("bytes"),
                     "payload_sha256": fp.get("sha256"), "png_magic": fp.get("png_magic"),
                     "worktree_probe": wt}
            note = ("payload fetched from GET /tensor/reports/11267/figures/<name> (PNG magic "
                    "checked) -> payload_sha256 is the hash of the bytes actually served; the "
                    "caption is also declared in the record metadata")
            if not served:
                note = ("declaration resolves verbatim but no PNG payload could be fetched -> "
                        "referenced_unresolved, no payload hash claimed")
        elif g["asset_class"] in ("cluster_job", "declared_measurement_gap"):
            res = "declared_absent"
            check = {"check": "report itself declares this artefact/measurement absent or "
                              "unmeasured", "result": "absent", "worktree_probe": wt}
            note = ("the report states the artefact is absent/queued/not measured; registered as "
                    "declared_absent -- registration of a declared gap, NOT a claim and NOT a "
                    "verified finding")
        else:
            ok = wt["result"] == "resolved"
            res = "resolved_in_source" if ok else "referenced_unresolved"
            check = dict(wt, result="resolved" if ok else "unresolved")
            note = ("declared path belongs to the delivery repo named at line 3 (TensorPhysics, "
                    "src/tensorphysics/fem_parallel); the payload is outside this工序's worktree "
                    "-> declared reference, unresolvable here")
        assets.append({
            "asset_id": "A%02d" % i, "asset_class": g["asset_class"], "label": g["label"],
            "name": name, "in_report_section": section_of(lines, g["first_line"]),
            "locator": {"method": "char_span", "start_char": g["start"], "end_char": g["end"],
                        "start_line": g["first_line"], "end_line": g["first_line"],
                        "quote": g["quote"], "unique": md.count(g["quote"]) == 1},
            "all_locators": g["occurrences"], "reference_form": g["form"],
            "occurrence_count": len(g["occurrences"]), "resolution": res,
            "resolution_check": check, "note": note})

    src_asset = {
        "asset_id": "A00", "asset_class": "source_document",
        "label": "report 11267 markdown (H1 title line as identity quote)",
        "name": "%s#markdown" % SOURCE_URI, "in_report_section": "(document root)",
        "locator": {"method": "document", "start_char": 0, "end_char": len(md),
                    "start_line": 1, "end_line": len(lines), "quote": lines[0],
                    "unique": md.count(lines[0]) == 1},
        "all_locators": [{"source_field": "markdown", "line": 1, "start_char": 0,
                          "end_char": len(lines[0]), "quote": lines[0],
                          "quote_sha256": sha256_hex(lines[0].encode("utf-8")),
                          "quote_in_source": lines[0] in md, "on_declared_span": True}],
        "reference_form": "document", "occurrence_count": 1,
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "sha256(markdown utf-8 bytes) recomputed locally",
                             "result": "resolved", "algorithm": "sha256",
                             "recomputed": digest, "contract_declared": CONTRACT_SOURCE_HASH,
                             "match": hash_match},
        "note": "the registered asset of this工序 is the report markdown itself; the hash is "
                "recomputed here, not copied from the contract"}
    assets = [src_asset] + assets

    rec_figs = []
    for idx, fig in enumerate(record.get("figures") or []):
        nm = fig.get("name", "")
        rec_figs.append({"index": idx, "name": nm, "caption": fig.get("caption"),
                         "referenced_in_body": nm in {Path(x).name for x in fig_referenced},
                         "api_pointer": "/figures/%d" % idx,
                         "payload_probe": fig_probes.get(nm, {})})

    ids = [a["asset_id"] for a in assets]
    names = [(a["asset_class"], a["name"]) for a in assets]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    dup_names = sorted({n for n in names if names.count(n) > 1})
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    return {
        "schema": "asset_manifest.v1", "manifest_version": "1.0", "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE, "report_id": REPORT_ID, "lane": "C",
        "generated_at": utcnow(), "producer": PRODUCER,
        "scope": {"registers": "source asset identity (report_id + markdown byte hash) and the "
                               "attachments/artifacts the report declares",
                  "does_not": ["claim extraction (claims == [])",
                               "report-type classification (contract: classify_report_type=false)",
                               "verification (the platform gate computes it)",
                               "reading or writing any other report_id"]},
        "source": {
            "report_id": REPORT_ID, "uri": SOURCE_URI, "field": "markdown",
            "hash_alg": "sha256", "hash": digest, "contract_hash": CONTRACT_SOURCE_HASH,
            "hash_matches_contract": hash_match, "chars": len(md),
            "contract_chars": CONTRACT_CHARS, "chars_match_contract": len(md) == CONTRACT_CHARS,
            "bytes_utf8": len(raw), "lines": len(lines),
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "logical lines = markdown.split(chr(10)); 1-based",
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
            "title": record.get("title"), "scenario_key": record.get("scenario_key"),
            "mission_id": record.get("mission_id"), "status": record.get("status"),
            "created_at": record.get("created_at"), "tags": record.get("tags"),
            "contract_title": CONTRACT_TITLE, "contract_scenario_key": CONTRACT_SCENARIO,
            "title_matches_contract": (record.get("title") or "") == CONTRACT_TITLE,
            "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            "record_figures": rec_figs,
            "artifact_endpoint_probe": artifact_probe,
            "figure_endpoint_probes": fig_probes},
        "counts": {
            "assets": len(assets), "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "body_image_links": len([h for h in hits if h["asset_class"] == "figure_artifact"
                                     and h["form"] == "markdown_image_link"]),
            "figure_references_total": len([h for h in hits
                                            if h["asset_class"] == "figure_artifact"]),
            "distinct_referenced_paths": len([k for k in order
                                              if k[0] not in ("cluster_job",
                                                              "declared_measurement_gap")]),
            "claims": 0},
        "assets": assets,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-11267-01 sets objective.register_assets=true and "
            "objective.classify_report_type=false, output=asset_manifest.json only, notes "
            "'claims 允许为空数组', and constraints forbid no_forced_claim_generation and "
            "do_not_mark_claims_as_verified. This工序 registers asset identity only (report_id, "
            "markdown byte hash, declared attachments/artifacts); knowledge extraction is a "
            "downstream工序, so claims=[] is the complete result of this package."),
        "id_integrity": {"ids_checked": len(ids), "duplicate_ids": dup_ids,
                         "names_checked": len(names), "duplicate_names": dup_names,
                         "unique": not dup_ids and not dup_names},
        "unresolved": [{"asset_id": a["asset_id"], "asset_class": a["asset_class"],
                        "name": a["name"], "resolution": a["resolution"],
                        "reason": a["resolution_check"]["check"]}
                       for a in assets if a["resolution"] != "resolved_in_source"],
        "method_notes": [
            "Asset discovery is text-driven over the markdown: image links, backticked paths / "
            "module entrypoints / test symbols, cluster job ids, criteria-table rows stating "
            "'not measured'/'未测量', and the MPIComm caveat sentence.",
            "Repeated references to one path collapse into a single asset whose all_locators "
            "lists every char span, so dedup never drops a locator.",
            "resolution=resolved_in_source: payload/hash obtained here; referenced_unresolved: "
            "declaration verbatim-locatable but payload outside this工序's worktree; "
            "declared_absent: the report itself declares the artefact absent/queued/unmeasured.",
            "Figure names are normalised to the in-body link form (figures/<name>.png): section 4 "
            "refers to them bare, and one asset must keep every literal locator span.",
            "A directory token that only prefixes another declared file path "
            "(artifacts/fem_parallel/ vs artifacts/fem_parallel/verification.json) is folded into "
            "that file asset instead of being counted twice."]}


def manifest_schema() -> dict:
    """Shape actually emitted, pinned locally so schema_pass is reproducible.
    Mirrors schemas/asset_manifest.v1.schema.json without its wp-448 consts."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "asset_manifest for %s (report %s)" % (PACKAGE_ID, REPORT_ID),
        "type": "object",
        "required": ["schema", "package_id", "task_type", "report_id", "source", "counts",
                     "assets", "claims", "id_integrity"],
        "properties": {
            "schema": {"const": "asset_manifest.v1"},
            "package_id": {"const": PACKAGE_ID},
            "task_type": {"const": TASK_TYPE},
            "report_id": {"const": REPORT_ID},
            "source": {
                "type": "object",
                "required": ["uri", "field", "hash_alg", "hash", "chars", "bytes_utf8", "title",
                             "scenario_key", "contract_hash", "hash_matches_contract"],
                "properties": {
                    "uri": {"const": SOURCE_URI},
                    "field": {"const": "markdown"},
                    "hash_alg": {"const": "sha256"},
                    "hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                    "contract_hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                    "hash_matches_contract": {"const": True},
                    "chars": {"type": "integer", "minimum": 1},
                    "bytes_utf8": {"type": "integer", "minimum": 1},
                    "title": {"type": "string", "minLength": 1},
                    "scenario_key": {"type": "string", "minLength": 1}}},
            "counts": {
                "type": "object",
                "required": ["assets", "by_class", "by_resolution", "resolved_in_source",
                             "referenced_unresolved", "declared_absent"],
                "properties": {"assets": {"type": "integer", "minimum": 1},
                               "by_class": {"type": "object"},
                               "by_resolution": {"type": "object"}}},
            "assets": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["asset_id", "asset_class", "label", "in_report_section",
                                 "locator", "resolution", "resolution_check", "note"],
                    "properties": {
                        "asset_id": {"type": "string", "pattern": "^A[0-9]{2}$"},
                        "asset_class": {"type": "string", "minLength": 1},
                        "label": {"type": "string", "minLength": 1},
                        "in_report_section": {"type": "string", "minLength": 1},
                        "resolution": {"enum": ["resolved_in_source", "referenced_unresolved",
                                                "declared_absent"]},
                        "resolution_check": {
                            "type": "object", "required": ["check", "result"],
                            "properties": {"check": {"type": "string"},
                                           "result": {"enum": ["resolved", "unresolved",
                                                               "absent", "present"]}}},
                        "locator": {
                            "type": "object",
                            "required": ["method", "start_char", "end_char", "start_line",
                                         "end_line", "quote", "unique"],
                            "properties": {
                                "method": {"enum": ["char_span", "document"]},
                                "start_char": {"type": "integer", "minimum": 0},
                                "end_char": {"type": "integer", "minimum": 1},
                                "start_line": {"type": "integer", "minimum": 0},
                                "end_line": {"type": "integer", "minimum": 0},
                                "quote": {"type": "string", "minLength": 1},
                                "unique": {"type": "boolean"}}},
                        "note": {"type": "string"}}}},
            "claims": {"type": "array",
                       "description": "empty is legitimate here; any claim must carry evidence "
                                      "or an explicit status",
                       "items": {"type": "object", "required": ["claim_id", "text"],
                                 "anyOf": [{"required": ["evidence"]},
                                           {"required": ["status"]}]}},
            "id_integrity": {"type": "object",
                             "required": ["ids_checked", "duplicate_ids", "unique"],
                             "properties": {"unique": {"const": True}}}}}


def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"package_id": PACKAGE_ID, "task_type": TASK_TYPE, "report_id": REPORT_ID,
            "provenance": {"source_hash": manifest["source"]["hash"],
                           "source_field": "markdown", "producer": PRODUCER,
                           "emitted_at": utcnow(),
                           "notes": "source_hash recomputed from the live markdown bytes "
                                    "fetched via GET /api/v1/tensor/reports/%s; equals the "
                                    "contract-declared hash" % REPORT_ID},
            "outputs": {"asset_manifest.json": manifest}, "claims": []}


def verify() -> dict:
    import jsonschema

    checks = []

    def add(cid, item, ok, detail, metric=None):
        checks.append({"check_id": cid, "acceptance_item": item,
                       "status": "pass" if ok else "fail", "detail": detail, "metric": metric})

    rec = fetch_record()               # fresh: verification never trusts build artefacts
    md = rec["markdown"]
    raw = md.encode("utf-8")
    lines = md.split("\n")
    offs = line_offsets(lines)
    manifest_text = MANIFEST.read_text(encoding="utf-8")
    envelope_text = ENVELOPE.read_text(encoding="utf-8")
    try:
        manifest = json.loads(manifest_text)
        envelope = json.loads(envelope_text)
        add("C1_valid_json", "valid_json", True,
            "asset_manifest.json and kf_result.json both parse with json.loads",
            {"manifest_bytes": len(manifest_text), "envelope_bytes": len(envelope_text)})
    except json.JSONDecodeError as exc:
        add("C1_valid_json", "valid_json", False, "json decode error: %s" % exc)
        return _write_verification(checks, None)

    schema = manifest_schema()
    MANIFEST_SCHEMA.write_text(json.dumps(schema, ensure_ascii=False, indent=1),
                               encoding="utf-8")
    errs = sorted(jsonschema.Draft7Validator(schema).iter_errors(manifest),
                  key=lambda e: list(e.path))
    env_schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json")
                            .read_text(encoding="utf-8"))
    env_errs = sorted(jsonschema.Draft202012Validator(env_schema).iter_errors(envelope),
                      key=lambda e: list(e.path))
    add("C2_schema_pass", "schema_pass", not errs and not env_errs,
        "jsonschema draft-07 on the package-pinned manifest schema "
        "(docs/kf/%s/asset_manifest.schema.json) + draft-2020-12 on "
        "schemas/kf_result.v1.schema.json for the envelope" % PACKAGE_ID,
        {"manifest_errors": ["/%s: %s" % ("/".join(map(str, e.path)), e.message) for e in errs],
         "envelope_errors": ["/%s: %s" % ("/".join(map(str, e.path)), e.message)
                             for e in env_errs]})

    bad, n_loc = [], 0
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            n_loc += 1
            if md[loc["start_char"]:loc["end_char"]] != md:
                bad.append({"asset_id": a["asset_id"],
                            "failure": "document locator does not cover the whole markdown"})
            continue
        for entry in a.get("all_locators") or []:
            n_loc += 1
            s, e, q = entry["start_char"], entry["end_char"], entry.get("quote", loc["quote"])
            rline = line_of(offs, s)
            if not (q in md and md[s:e] == q and entry["line"] == rline):
                bad.append({"asset_id": a["asset_id"], "quote": q[:80], "start_char": s,
                            "end_char": e, "in_source": q in md, "span_equal": md[s:e] == q,
                            "declared_line": entry["line"], "recomputed_line": rline})
    add("C3_source_locator_resolvable", "source_locator_resolvable", not bad,
        "every locator re-resolved against a freshly fetched markdown: quote in source AND "
        "md[start:end] == quote AND recomputed line == declared line",
        {"locators_checked": n_loc, "failures": bad})

    recomputed = sha256_hex(raw)
    disk = sha256_hex(SOURCE_COPY.read_bytes())
    env_hash = envelope["provenance"]["source_hash"]
    hash_ok = (recomputed == CONTRACT_SOURCE_HASH == manifest["source"]["hash"]
               == env_hash == disk)
    add("C4_source_hash_matches", "source_hash_matches", hash_ok,
        "sha256 of the live-fetched markdown bytes compared against the contract hash, the "
        "manifest source.hash, the envelope provenance.source_hash and the on-disk copy",
        {"recomputed": recomputed, "contract": CONTRACT_SOURCE_HASH,
         "manifest": manifest["source"]["hash"], "envelope": env_hash, "disk_copy": disk,
         "chars": len(md), "bytes_utf8": len(raw),
         "chars_match_contract": len(md) == CONTRACT_CHARS})

    ids = [a["asset_id"] for a in manifest["assets"]]
    names = [(a["asset_class"], a["name"]) for a in manifest["assets"]]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    dup_names = sorted({n for n in names if names.count(n) > 1})
    add("C5_no_duplicate_ids", "no_duplicate_ids", not dup_ids and not dup_names,
        "asset_id uniqueness plus (asset_class, name) uniqueness over the manifest",
        {"assets": len(ids), "duplicate_ids": dup_ids, "duplicate_names": dup_names})

    claims = manifest.get("claims", [])
    claim_bad = [c for c in claims if not (c.get("evidence") or c.get("status"))]
    add("C6_claims_evidence_or_status",
        "all_claims_have_evidence_or_explicit_unresolved_status", not claim_bad,
        "claims==[] by contract (classify_report_type=false, no_forced_claim_generation); the "
        "vacuous pass is stated explicitly with the reason recorded in the manifest",
        {"claims": len(claims), "claims_without_evidence_or_status": len(claim_bad),
         "claims_empty_reason_present": bool(manifest.get("claims_empty_reason")),
         "verified_marks_present": "verified" in json.dumps(claims).lower()})

    add("X1_contract_identity", "extra: source identity matches the work-package YAML",
        bool(rec.get("title") == CONTRACT_TITLE and rec.get("scenario_key") == CONTRACT_SCENARIO
             and manifest["source"]["title_matches_contract"]
             and manifest["source"]["scenario_matches_contract"]),
        "live record title/scenario_key compared with the contract constants",
        {"record_title": rec.get("title"), "record_scenario_key": rec.get("scenario_key")})

    fig_rec = manifest["source"]["record_figures"]
    body_basenames = {Path(a["name"]).name for a in manifest["assets"]
                      if a["asset_class"] == "figure_artifact"}
    for f in fig_rec:
        f["referenced_in_body"] = f["name"] in body_basenames
    add("X2_figure_caption_coverage", "extra: every record figure is referenced in body",
        all(f["referenced_in_body"] for f in fig_rec),
        "record /figures captions cross-checked against in-body markdown image links",
        {"record_figures": len(fig_rec),
         "referenced_in_body": sum(1 for f in fig_rec if f["referenced_in_body"]),
         "payload_served": sum(1 for f in fig_rec
                               if (f["payload_probe"] or {}).get("http_status") == 200)})

    add("X3_report_scope", "extra: single report_id touched",
        manifest["report_id"] == REPORT_ID == envelope["report_id"],
        "both artefacts carry report_id 11267 only; REPORT_ID is a single module constant",
        {"manifest_report_id": manifest["report_id"],
         "envelope_report_id": envelope["report_id"], "source_uri": manifest["source"]["uri"]})

    return _write_verification(checks, manifest)


def _write_verification(checks, manifest) -> dict:
    failed = [c for c in checks if c["status"] != "pass"]
    acc = [c for c in checks if not c["acceptance_item"].startswith(("extra:", "(extra)"))]
    out = {"package_id": PACKAGE_ID, "report_id": REPORT_ID, "generated_at": utcnow(),
           "producer": PRODUCER,
           "acceptance_items": ["valid_json", "schema_pass", "source_locator_resolvable",
                                "source_hash_matches", "no_duplicate_ids",
                                "all_claims_have_evidence_or_explicit_unresolved_status"],
           "checks": checks,
           "summary": {"total": len(checks), "pass": len(checks) - len(failed),
                       "fail": len(failed),
                       "acceptance_total": len(acc),
                       "acceptance_pass": sum(1 for c in acc if c["status"] == "pass")},
           "gate_verdict": "pass" if not failed else "fail",
           "scope_note": "checks are mechanical; verification of knowledge claims is the "
                         "platform gate's job, not this工序's"}
    if manifest is not None:
        out["registered_assets"] = manifest["counts"]
        out["source_hash"] = manifest["source"]["hash"]
    VERIFICATION.parent.mkdir(parents=True, exist_ok=True)
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("verification: %s (%d/%d pass) -> %s"
          % (out["gate_verdict"], out["summary"]["pass"], out["summary"]["total"],
             VERIFICATION.relative_to(ROOT)))
    for c in failed:
        print("  FAIL", c["check_id"], c["detail"][:160],
              json.dumps(c.get("metric"), ensure_ascii=False)[:600])
    return out


def main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("build", "all"):
        rec = fetch_record()
        man = build_manifest(rec)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
        print("manifest -> %s  assets=%d  resolutions=%s"
              % (MANIFEST.relative_to(ROOT), man["counts"]["assets"],
                 man["counts"]["by_resolution"]))
    if cmd in ("envelope", "all"):
        env = build_envelope()
        ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=1), encoding="utf-8")
        print("envelope -> %s  source_hash=%s"
              % (ENVELOPE.relative_to(ROOT), env["provenance"]["source_hash"]))
    if cmd in ("verify", "all"):
        out = verify()
        if out["gate_verdict"] != "pass":
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))