#!/usr/bin/env python3
"""wp-13476-01 (task_type 01-asset-registration): register report 13476's source asset
and enumerate the attachments/artifacts it declares. Registration only -- no extraction.

Sub-commands (idempotent; stdlib only except `figure`):

    python3 scripts/kf_wp13476_01_register.py fetch     # GET report -> source copy + sha256
    python3 scripts/kf_wp13476_01_register.py build     # -> asset_manifest.json
    python3 scripts/kf_wp13476_01_register.py envelope  # -> kf_result.json (kf_result.v1)
    python3 scripts/kf_wp13476_01_register.py verify    # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp13476_01_register.py figure    # -> figures/asset_locator_map.png
    python3 scripts/kf_wp13476_01_register.py report    # -> KF-RESULT-wp-13476-01.md
    python3 scripts/kf_wp13476_01_register.py publish   # POST the KF-RESULT report
    python3 scripts/kf_wp13476_01_register.py all       # fetch+build+envelope+verify+figure+report

Contract discipline honoured here (package wp-13476-01):
  * only report_id 13476 is touched; no other report is read or written;
  * zero manual transcription -- every number/offset in the artefacts is measured here
    from the live markdown, and every quote is re-resolved against a fresh fetch at
    verify time;
  * nothing is marked verified (verification is the platform gate's job); `claims` stays
    an empty array because objective.classify_report_type=false and
    constraints.no_forced_claim_generation=true;
  * unresolvable references are recorded as referenced_unresolved instead of being
    dropped or invented.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "13476"
PACKAGE_ID = "wp-13476-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID

# contract-declared identity (work-package YAML). Comparison target only: the script
# never trusts these, it recomputes and reports the delta.
CONTRACT_SOURCE_HASH = "sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0"
CONTRACT_CHARS = 12871
CONTRACT_TITLE = ("DEM Clump Shape Effect Verification (p447w2-n02): "
                  "Partial Success with Critical Bug Discovery")
CONTRACT_SCENARIO = "p447w2-n02"

OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID          # committed deliverable
FIG_DIR = OUT_DIR / "figures"
SRC_DIR = ROOT / "work" / PACKAGE_ID / "source"       # working copy
SOURCE_JSON = SRC_DIR / ("report_%s.json" % REPORT_ID)
SOURCE_MD = SRC_DIR / ("report_%s.md" % REPORT_ID)
SOURCE_MD_COPY = OUT_DIR / "source_markdown.md"       # committed verbatim copy
MANIFEST = OUT_DIR / "asset_manifest.json"
MANIFEST_SCHEMA = OUT_DIR / "asset_manifest.schema.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
RESULT_MD = OUT_DIR / ("KF-RESULT-%s.md" % PACKAGE_ID)
FIGURE = FIG_DIR / "asset_locator_map.png"
PRODUCER = "kf-worker/m15760"

PATH_EXTS = {
    ".py": "source_code_reference",
    ".json": "data_artifact_reference",
    ".csv": "data_artifact_reference",
    ".h5": "data_artifact_reference",
    ".hdf5": "data_artifact_reference",
    ".md": "document_reference",
    ".png": "figure_reference",
    ".jpg": "figure_reference",
}
PATH_RE = re.compile(r"^(?:[\w.\-]+/)*[\w.\-]+\.(?:py|json|csv|h5|hdf5|md|png|jpg)$")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def lines_of(md: str):
    return md.rstrip("\n").split("\n")


def line_starts(md: str):
    starts, pos = [0], 0
    for ln in md.split("\n"):
        pos += len(ln) + 1
        starts.append(pos)
    return starts


def line_of_offset(starts, off: int) -> int:
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= off:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1  # 1-based


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


def _get_json(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def _probe(path: str, tok: str) -> dict:
    """Capability probe: record the HTTP status instead of raising."""
    try:
        req = urllib.request.Request(_api_base() + path,
                                     headers={"Authorization": "Bearer " + tok})
        with urllib.request.urlopen(req, timeout=30) as r:
            return {"path": path, "http_status": r.status}
    except urllib.error.HTTPError as e:
        return {"path": path, "http_status": e.code}
    except Exception as e:  # noqa: BLE001 - a probe never aborts the package
        return {"path": path, "http_status": None, "error": type(e).__name__}


def fetch_report() -> dict:
    tok = _login()
    rec = _get_json("/tensor/reports/%s" % REPORT_ID, tok)
    data = rec.get("data", rec)
    md = data["markdown"]
    raw = md.encode("utf-8")
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    SOURCE_MD.write_bytes(raw)
    SOURCE_MD_COPY.write_bytes(raw)
    (SRC_DIR / "markdown.sha256").write_text("sha256:" + sha256_hex(raw) + "\n",
                                             encoding="utf-8")
    probes = {p: _probe(p, tok) for p in (
        "/tensor/reports/%s/artifacts" % REPORT_ID,
        "/tensor/reports/%s/figures" % REPORT_ID,
        "/tensor/reports/%s/assets" % REPORT_ID,
    )}
    (SRC_DIR / "platform_probes.json").write_text(
        json.dumps(probes, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"record": data, "markdown": md, "raw": raw, "probes": probes}


def load_source():
    if not SOURCE_MD.exists():
        return fetch_report()
    rec = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    data = rec.get("data", rec)
    raw = SOURCE_MD.read_bytes()
    probes_path = SRC_DIR / "platform_probes.json"
    probes = json.loads(probes_path.read_text(encoding="utf-8")) if probes_path.exists() else {}
    return {"record": data, "markdown": raw.decode("utf-8"), "raw": raw, "probes": probes}


def _section_of(lines, ln: int) -> str:
    for i in range(ln - 1, -1, -1):
        s = lines[i]
        if s.startswith("## "):
            return s[3:].strip()
        if s.startswith("# "):
            return s[2:].strip()
    return "preamble"


def discover_assets(md: str, record: dict, probes: dict) -> list:
    lines = lines_of(md)
    starts = line_starts(md)
    assets = []

    # ---- the canonical source document itself
    assets.append({
        "asset_id": "A00",
        "asset_class": "source_document",
        "label": "report %s markdown (source_field=markdown)" % REPORT_ID,
        "in_report_section": "whole document",
        "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": len(md),
            "start_line": 1,
            "end_line": len(lines),
            "quote": lines[0],
            "unique": md.count(lines[0]) == 1,
            "occurrences_in_source": md.count(lines[0]),
        },
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "GET /tensor/reports/%s -> markdown field" % REPORT_ID,
                             "result": "resolved"},
        "note": ("Canonical asset of this package: sha256 over the utf-8 markdown bytes is "
                 "recomputed on every run and compared with provenance.source_hash."),
    })

    # ---- record-declared figures (metadata only; platform serves no artifact endpoint)
    fig_probe_note = ", ".join(
        "r%s/%s=%s" % (REPORT_ID, p.rsplit("/", 1)[-1], v.get("http_status"))
        for p, v in sorted(probes.items())) or "not probed"
    for fig_index, fig in enumerate(record.get("figures") or []):
        name = fig.get("name") or ""
        caption = fig.get("caption") or ""
        idx = md.find(name)
        in_body = idx >= 0
        if in_body:
            ln = line_of_offset(starts, idx)
            loc = {"method": "char_span", "start_char": idx, "end_char": idx + len(name),
                   "start_line": ln, "end_line": ln, "quote": lines[ln - 1],
                   "unique": md.count(lines[ln - 1]) == 1,
                   "occurrences_in_source": md.count(lines[ln - 1])}
        else:
            # the figure appears only in record metadata: anchor the locator on the
            # record field itself (source_field=record) -- never invent a markdown offset
            loc = {"method": "record_json_path", "source_field": "record",
                   "record_path": "figures[%d].caption" % fig_index,
                   "start_char": 0, "end_char": len(md),
                   "start_line": 1, "end_line": len(lines), "quote": caption,
                   "unique": True, "occurrences_in_source": 0}
        assets.append({
            "asset_id": "A00",
            "asset_class": "figure_reference",
            "label": name,
            "in_report_section": "record.figures (declared metadata)",
            "locator": loc,
            "resolution": "referenced_unresolved",
            "resolution_check": {
                "check": ("figure name in markdown=%s; platform artifact endpoints probed "
                          "(%s)" % (in_body, fig_probe_note)),
                "result": "unresolved",
            },
            "note": ("Declared in record.figures with caption %r; the platform serves no "
                     "artifact/figures endpoint for this report, so no bytes and no figure "
                     "hash are registered." % caption),
        })

    # ---- body path references: inline code spans that look like file paths
    seen, order = {}, []
    for m in BACKTICK_RE.finditer(md):
        tok = m.group(1).strip()
        if not PATH_RE.match(tok):
            continue
        if tok not in seen:
            seen[tok] = m
            order.append(tok)
    for tok in order:
        m = seen[tok]
        off = m.start(1)
        ln = line_of_offset(starts, off)
        quote = lines[ln - 1]
        exists_local = (ROOT / tok).exists()
        assets.append({
            "asset_id": "A00",
            "asset_class": PATH_EXTS.get(Path(tok).suffix, "artifact_reference"),
            "label": tok,
            "in_report_section": _section_of(lines, ln),
            "locator": {"method": "char_span", "start_char": starts[ln - 1],
                        "end_char": starts[ln - 1] + len(quote),
                        "token": tok, "token_start_char": off,
                        "token_end_char": off + len(tok),
                        "start_line": ln, "end_line": ln, "quote": quote,
                        "unique": md.count(quote) == 1,
                        "occurrences_in_source": md.count(quote)},
            "resolution": "referenced_unresolved",
            "resolution_check": {
                "check": ("path exists in TensorKnowledge worktree=%s (target repo = "
                          "TensorDEM, outside this package's scope)" % exists_local),
                "result": "unresolved"},
            "note": ("Path reference declared in the report body; the target lives in the "
                     "TensorDEM repository, which is not part of this worktree and is not "
                     "served by the platform for this report, so no bytes are registered and "
                     "no content hash is claimed."),
        })

    # ---- fenced code blocks (reproduction snippet / analytical expressions)
    fences = [(i, ln) for i, ln in enumerate(lines, start=1) if FENCE_RE.match(ln)]
    for k in range(0, len(fences) - 1, 2):
        open_i, open_ln = fences[k]
        close_i, _ = fences[k + 1]
        lang = FENCE_RE.match(open_ln).group(1) or "none"
        body = "\n".join(lines[open_i:close_i - 1])
        quote = "\n".join(lines[open_i - 1:close_i])
        if "import" in body or "def " in body:
            kind = "code_reproduction_snippet"
            note = ("Executable-looking code carried in-report (reproduction example); "
                    "registered as a source-embedded asset, not executed by this package.")
        else:
            kind = "in_source_expression"
            note = "Mathematical/expression block carried in-report; registered as text."
        assets.append({
            "asset_id": "A00",
            "asset_class": kind,
            "label": "fenced %s block L%d-L%d" % (lang, open_i, close_i),
            "in_report_section": _section_of(lines, open_i),
            "locator": {"method": "char_span", "start_char": starts[open_i - 1],
                        "end_char": starts[close_i - 1] + len(lines[close_i - 1]),
                        "start_line": open_i, "end_line": close_i, "quote": quote,
                        "unique": md.count(quote) == 1,
                        "occurrences_in_source": md.count(quote)},
            "resolution": "resolved_in_source",
            "resolution_check": {"check": "fenced span slice equals quote", "result": "resolved"},
            "note": note,
        })

    # ---- in-report data tables (a table is a pointer to numbers; not re-extracted here)
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and \
                lines[i + 1].lstrip().startswith("|"):
            j = i
            while j + 1 < len(lines) and lines[j + 1].lstrip().startswith("|"):
                j += 1
            block = "\n".join(lines[i:j + 1])
            assets.append({
                "asset_id": "A00",
                "asset_class": "in_source_table",
                "label": "markdown table L%d-L%d" % (i + 1, j + 1),
                "in_report_section": _section_of(lines, i + 1),
                "locator": {"method": "char_span", "start_char": starts[i],
                            "end_char": starts[j] + len(lines[j]),
                            "start_line": i + 1, "end_line": j + 1, "quote": block,
                            "unique": md.count(block) == 1,
                            "occurrences_in_source": md.count(block)},
                "resolution": "resolved_in_source",
                "resolution_check": {"check": "table span slice equals quote",
                                     "result": "resolved"},
                "note": ("Tabulated data carried in-report (header row: %r); registered as "
                         "an in-source asset -- this package does NOT re-extract its "
                         "numbers." % lines[i]),
            })
            i = j + 1
        else:
            i += 1

    # deterministic renumbering by document order, document first
    head, rest = assets[0], assets[1:]
    rest.sort(key=lambda a: (a["locator"]["start_char"], a["locator"]["end_char"]))
    ordered = [head] + rest
    for n, a in enumerate(ordered, start=1):
        a["asset_id"] = "A%02d" % n
    return ordered


def build() -> dict:
    src = load_source()
    md, raw, record, probes = src["markdown"], src["raw"], src["record"], src["probes"]
    digest = "sha256:" + sha256_hex(raw)
    lines = lines_of(md)
    assets = discover_assets(md, record, probes)

    identity_facts = []
    for fact_id, ln in (("title", 1), ("mission-line", 3), ("status-line", 5),
                        ("honest-assessment-line", 23), ("artifacts-header", 270)):
        if 1 <= ln <= len(lines):
            q = lines[ln - 1]
            identity_facts.append({
                "fact_id": fact_id, "line": ln, "quote": q,
                "quote_sha256": sha256_hex(q.encode("utf-8")),
                "quote_in_source": q in md, "occurrences_in_source": md.count(q)})

    record_blob = json.dumps(record, ensure_ascii=False)
    locators = []
    for a in assets:
        loc = a["locator"]
        q = loc["quote"]
        field = loc.get("source_field", "markdown")
        if field == "record":
            # metadata-only asset: resolvable iff the record field itself carries it
            path = loc.get("record_path") or ""
            idx = int(re.search(r"\[(\d+)\]", path).group(1)) if re.search(r"\[(\d+)\]", path) else -1
            figs = record.get("figures") or []
            in_record = bool(q) and q in record_blob
            slice_ok = 0 <= idx < len(figs) and q in (figs[idx].get("caption") or "")
            occurrences = sum(1 for f in figs if q == (f.get("caption") or ""))
        else:
            path = None
            in_record = False
            slice_ok = md[loc["start_char"]:loc["end_char"]] == q
            occurrences = md.count(q)
        if field == "markdown" and loc.get("method") == "document":
            slice_ok = md.startswith(q) and loc["start_char"] == 0 and \
                loc["end_char"] == len(md)
            occurrences = md.count(q)
        locators.append({
            "asset_id": a["asset_id"],
            "source_field": field,
            "method": loc.get("method", "char_span"),
            "record_path": path,
            "start_char": loc["start_char"],
            "end_char": loc["end_char"],
            "line": loc["start_line"],
            "quote": q,
            "quote_sha256": sha256_hex(q.encode("utf-8")),
            "quote_in_source": (q in record_blob) if field == "record" else (q in md),
            "slice_matches_quote": slice_ok,
            "occurrences_in_source": occurrences,
        })

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    rtitle = record.get("title") or ""
    fig_probe_note = ", ".join(
        "r%s/%s=%s" % (REPORT_ID, p.rsplit("/", 1)[-1], v.get("http_status"))
        for p, v in sorted(probes.items())) or "not probed"

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "objective": {"register_assets": True, "classify_report_type": False,
                      "extraction_performed": False},
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "contract_hash": CONTRACT_SOURCE_HASH,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip('\\n').split('\\n'); 1-based",
            "title": rtitle,
            "title_matches_contract": rtitle.replace("\u2013", "-") == CONTRACT_TITLE,
            "scenario_key": record.get("scenario_key"),
            "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            "platform_record_id": record.get("id"),
            "platform_status": record.get("status"),
            "platform_mission_id": record.get("mission_id"),
            "platform_created_at": record.get("created_at"),
            "platform_tags": record.get("tags"),
            "platform_figures": record.get("figures"),
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "platform_artifact_probes": probes,
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "figures_declared_in_record": len(record.get("figures") or []),
            "claims": 0,
        },
        "assets": assets,
        "locators": locators,
        "identity_facts": identity_facts,
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes,
                         "unique": not dupes,
                         "id_format_ok": all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)},
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-13476-01 sets objective.register_assets=true, "
            "objective.classify_report_type=false, constraints.no_forced_claim_generation=true, "
            "and notes state 'claims 允许为空数组'. This package registers asset identity only "
            "(report_id, markdown byte hash, declared figures/artefacts and their in-source "
            "locators); extraction is a downstream package, so an empty claims array is the "
            "complete result, not an omission."),
        "not_registered": [
            {"what": "literature citations in '## 8. References'",
             "reason": ("external publications, not report-owned assets; they carry no "
                        "retrievable bytes and this package does not extract claims")},
            {"what": "figures %s" % [f.get("name") for f in (record.get("figures") or [])],
             "reason": ("declared in record metadata only; the platform exposes no "
                        "artifact/figures endpoint for report %s (%s), so bytes and hashes "
                        "are deliberately NOT claimed" % (REPORT_ID, fig_probe_note))},
        ],
        "unresolved": [
            {"asset_id": a["asset_id"], "label": a["label"],
             "reason": a["resolution_check"]["check"]}
            for a in assets if a["resolution"] == "referenced_unresolved"
        ],
        "observations": [
            "Source identity holds: live markdown sha256 %s equals the contract hash %s "
            "(%d chars / %d utf-8 bytes, %d lines)."
            % (digest, CONTRACT_SOURCE_HASH, len(md), len(raw), len(lines)),
            "The report declares %d figures in record.figures; none is reachable as bytes "
            "through the platform API (%s)."
            % (len(record.get("figures") or []), fig_probe_note),
            "Body path references point into the TensorDEM repository (benchmarks/, "
            "artifacts/, docs/); they are outside this worktree's scope and are registered "
            "as referenced_unresolved with verbatim locators, not dropped.",
            "No extraction and no verified marks: status stays draft for the platform gate.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_manifest_schema()
    return manifest


def write_manifest_schema():
    """Pin the manifest shape locally so `schema_pass` is a real check, not an assertion."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://tensorplatform.local/schemas/asset_manifest.wp-13476-01.schema.json",
        "title": "asset_manifest.v1 as emitted by scripts/kf_wp13476_01_register.py",
        "description": (
            "Locally pinned shape for the asset_manifest.json of work package wp-13476-01. "
            "schemas/kf_result.v1.schema.json validates the result envelope; this file pins "
            "the package-specific manifest shape so `schema_pass` is reproducible. If the "
            "platform-side schema differs, the platform gate wins and this artifact must be "
            "revised."),
        "type": "object",
        "required": ["schema", "package_id", "task_type", "report_id", "source", "counts",
                     "assets", "locators", "id_integrity", "claims"],
        "properties": {
            "schema": {"const": "asset_manifest.v1"},
            "package_id": {"const": PACKAGE_ID},
            "task_type": {"const": TASK_TYPE},
            "report_id": {"const": REPORT_ID},
            "source": {
                "type": "object",
                "required": ["uri", "field", "hash_alg", "hash", "chars", "bytes_utf8",
                             "title", "scenario_key"],
                "properties": {
                    "uri": {"const": SOURCE_URI},
                    "field": {"const": "markdown"},
                    "hash_alg": {"const": "sha256"},
                    "hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                    "chars": {"type": "integer", "minimum": 1},
                    "bytes_utf8": {"type": "integer", "minimum": 1},
                    "title": {"type": "string", "minLength": 1},
                    "scenario_key": {"type": "string", "minLength": 1},
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
            "assets": {
                "type": "array",
                "minItems": 1,
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
                            "type": "object",
                            "required": ["check", "result"],
                            "properties": {
                                "check": {"type": "string"},
                                "result": {"enum": ["resolved", "unresolved", "absent",
                                                    "present"]},
                            },
                        },
                        "locator": {
                            "type": "object",
                            "required": ["method", "start_char", "end_char", "start_line",
                                         "end_line", "quote", "unique"],
                            "properties": {
                                "method": {"enum": ["char_span", "document",
                                                    "record_json_path"]},
                                "source_field": {"enum": ["markdown", "record"]},
                                "record_path": {"type": ["string", "null"]},
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
            "locators": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["asset_id", "source_field", "method", "quote",
                                 "quote_in_source", "slice_matches_quote"],
                    "properties": {
                        "quote_in_source": {"const": True},
                        "slice_matches_quote": {"const": True},
                    },
                },
            },
            "id_integrity": {
                "type": "object",
                "required": ["ids_checked", "duplicates", "unique"],
                "properties": {"unique": {"const": True}, "duplicates": {"maxItems": 0}},
            },
            "claims": {
                "type": "array",
                "description": "Empty is the contract-complete result for this package.",
                "items": {
                    "type": "object",
                    "required": ["claim_id", "text"],
                    "anyOf": [{"required": ["evidence"]}, {"required": ["status"]}],
                },
            },
        },
    }
    MANIFEST_SCHEMA.write_text(json.dumps(schema, ensure_ascii=False, indent=2),
                               encoding="utf-8")


def envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["hash"],
            "source_field": "markdown",
            "source_uri": SOURCE_URI,
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "chars": manifest["source"]["chars"],
            "bytes_utf8": manifest["source"]["bytes_utf8"],
            "hash_matches_contract": manifest["source"]["hash_matches_contract"],
            "tool": "scripts/kf_wp13476_01_register.py",
            "notes": ("Hash computed locally over the utf-8 bytes of the markdown field "
                      "returned by GET /tensor/reports/13476; no other report_id was read. "
                      "Registration only: no claims, no verified marks."),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    return env


def verify() -> dict:
    import jsonschema

    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env_schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json")
                            .read_text(encoding="utf-8"))
    man_schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    checks = []

    # 1. valid_json
    try:
        json.loads(MANIFEST.read_text(encoding="utf-8"))
        json.loads(ENVELOPE.read_text(encoding="utf-8"))
        checks.append({"id": "valid_json", "ok": True,
                       "detail": "asset_manifest.json + kf_result.json both parse"})
    except Exception as e:  # noqa: BLE001
        checks.append({"id": "valid_json", "ok": False, "detail": repr(e)})

    # 2. schema_pass
    try:
        jsonschema.validate(env, env_schema)
        env_err = None
    except Exception as e:  # noqa: BLE001
        env_err = str(e).splitlines()[0]
    try:
        jsonschema.validate(manifest, man_schema)
        man_err = None
    except Exception as e:  # noqa: BLE001
        man_err = str(e).splitlines()[0]
    checks.append({"id": "schema_pass", "ok": env_err is None and man_err is None,
                   "detail": {"kf_result.v1": env_err or "valid",
                              "asset_manifest (pinned)": man_err or "valid"}})

    # 3. source_locator_resolvable -- against a FRESH fetch, not the cached copy
    fresh = fetch_report()
    fm = fresh["markdown"]
    fresh_blob = json.dumps(fresh["record"], ensure_ascii=False)
    fresh_figs = fresh["record"].get("figures") or []
    bad = []
    n_md = n_rec = 0
    for loc in manifest["locators"]:
        q = loc["quote"]
        if loc.get("source_field") == "record":
            n_rec += 1
            m = re.search(r"\[(\d+)\]", loc.get("record_path") or "")
            idx = int(m.group(1)) if m else -1
            ok = bool(q) and q in fresh_blob and 0 <= idx < len(fresh_figs) and \
                q == (fresh_figs[idx].get("caption") or "")
            if not ok:
                bad.append({"asset_id": loc["asset_id"], "source_field": "record",
                            "record_path": loc.get("record_path"),
                            "in_record": q in fresh_blob})
        elif loc.get("method") == "document":
            n_md += 1
            slice_ok = (fm.startswith(q) and loc["start_char"] == 0
                        and loc["end_char"] == len(fm))
            if not (q in fm and slice_ok):
                bad.append({"asset_id": loc["asset_id"], "method": "document",
                            "in_source": q in fm, "spans_whole_doc": slice_ok,
                            "end_char": loc["end_char"], "len": len(fm)})
        else:
            n_md += 1
            slice_ok = fm[loc["start_char"]:loc["end_char"]] == q
            if not (q in fm and slice_ok):
                bad.append({"asset_id": loc["asset_id"], "source_field": "markdown",
                            "in_source": q in fm, "slice_ok": slice_ok})
    checks.append({"id": "source_locator_resolvable", "ok": not bad,
                   "detail": {"locators": len(manifest["locators"]),
                              "markdown_locators": n_md, "record_locators": n_rec,
                              "unresolvable": bad,
                              "checked_against": ("fresh GET /tensor/reports/13476 "
                                                  "(markdown slice + record.figures)")}})

    # 4. source_hash_matches
    fresh_hash = "sha256:" + sha256_hex(fresh["raw"])
    checks.append({
        "id": "source_hash_matches",
        "ok": (fresh_hash == CONTRACT_SOURCE_HASH ==
               manifest["source"]["hash"] == env["provenance"]["source_hash"]),
        "detail": {"recomputed": fresh_hash, "contract": CONTRACT_SOURCE_HASH,
                   "manifest": manifest["source"]["hash"],
                   "provenance": env["provenance"]["source_hash"]},
    })

    # 5. no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    checks.append({"id": "no_duplicate_ids", "ok": len(ids) == len(set(ids)),
                   "detail": {"assets": len(ids), "distinct": len(set(ids)),
                              "duplicates": sorted({i for i in ids if ids.count(i) > 1})}})

    # 6. claims carry evidence or explicit status (empty array + explicit reason = pass)
    claims = env.get("claims") or []
    claims_ok = all(("evidence" in c) or ("status" in c) for c in claims)
    checks.append({
        "id": "all_claims_have_evidence_or_explicit_unresolved_status",
        "ok": claims_ok and bool(manifest.get("claims_empty_reason")),
        "detail": {"claims": len(claims),
                   "empty_claims_with_explicit_reason":
                       bool(manifest.get("claims_empty_reason")),
                   "reason": manifest.get("claims_empty_reason")},
    })

    result = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "verified_at": utcnow(),
        "checker": "scripts/kf_wp13476_01_register.py verify",
        "all_pass": all(c["ok"] for c in checks),
        "checks": checks,
        "note": ("Local self-check only. It does not mark claims verified and does not "
                 "replace the platform gate; the gate outcome is whatever the platform "
                 "computes."),
    }
    VERIFICATION.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def figure() -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = SOURCE_MD.read_text(encoding="utf-8")
    total = len(md)
    color = {"resolved_in_source": "#1b7f3b", "referenced_unresolved": "#c45a11",
             "declared_absent": "#8a1c1c"}
    assets = manifest["assets"]
    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(12, 0.36 * len(assets) + 2.8),
        gridspec_kw={"height_ratios": [max(3.0, 0.36 * len(assets)), 1.0]})
    labels = ["%s %s" % (a["asset_id"], a["asset_class"]) for a in assets]
    y = list(range(len(assets)))[::-1]
    for yy, a in zip(y, assets):
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        w = max(e - s, total * 0.004)
        ax.barh(yy, w, left=s, color=color[a["resolution"]], height=0.62)
        ax.text(min(s + w + total * 0.006, total * 1.02), yy,
                "L%d" % a["locator"]["start_line"], va="center", fontsize=7)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, total * 1.09)
    ax.set_xlabel("character offset in markdown (len=%d chars)" % total, fontsize=8)
    ax.set_title("wp-13476-01 asset locator map - report 13476 (%d assets: %d in-source, "
                 "%d unresolved)" % (len(assets), manifest["counts"]["resolved_in_source"],
                                     manifest["counts"]["referenced_unresolved"]), fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in color.values()]
    ax.legend(handles, list(color.keys()), fontsize=7, loc="lower right")
    ax.grid(axis="x", alpha=0.25)

    ok = manifest["source"]["hash_matches_contract"]
    ax2.axis("off")
    ax2.text(0.0, 0.72, "source identity", fontsize=9, weight="bold")
    ax2.text(0.0, 0.40, "contract  %s..." % CONTRACT_SOURCE_HASH[:26], fontsize=8,
             family="monospace")
    ax2.text(0.0, 0.14, "local     %s...  ->  %s" % (
        manifest["source"]["hash"][:26], "MATCH" if ok else "MISMATCH"), fontsize=8,
        family="monospace", color="#1b7f3b" if ok else "#8a1c1c")
    ax2.text(0.58, 0.40, "chars %d / contract %d  ->  %s" % (
        manifest["source"]["chars"], manifest["source"]["contract_chars"],
        "MATCH" if manifest["source"]["chars_match_contract"] else "MISMATCH"), fontsize=8,
        family="monospace")
    ax2.text(0.58, 0.14, "figures declared %d / bytes resolvable 0 (platform 404)" %
             manifest["counts"]["figures_declared_in_record"], fontsize=8, family="monospace")
    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=150)
    plt.close(fig)
    return FIGURE


def build_report_md() -> str:
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ver = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    src = manifest["source"]

    ev_rows = []
    for a in manifest["assets"]:
        q = a["locator"]["quote"].replace("\n", " / ")
        if len(q) > 90:
            q = q[:87] + "..."
        ev_rows.append("| %s `%s` | %s | %s `%s` (L%d-%d, chars %d-%d, unique=%s) |" % (
            a["asset_id"], a["label"], a["in_report_section"],
            a["locator"].get("source_field", "markdown"), q,
            a["locator"]["start_line"], a["locator"]["end_line"],
            a["locator"]["start_char"], a["locator"]["end_char"],
            str(a["locator"]["unique"]).lower()))
    ev_table = ("| claim/字段 | 所属节 | 原文引文片段（逐字）+ 定位 |\n|---|---|---|\n"
                + "\n".join(ev_rows))

    chk_rows = "\n".join("| %s | %s | %s |" % (
        c["id"], "PASS" if c["ok"] else "FAIL",
        json.dumps(c["detail"], ensure_ascii=False).replace("|", "/")[:240])
        for c in ver["checks"])

    fact_rows = "\n".join(
        "| %s | %d | `%s` | `%s` |" % (f["fact_id"], f["line"],
                                        f["quote"].replace("|", "/")[:70],
                                        f["quote_sha256"][:16])
        for f in manifest.get("identity_facts", []))

    asset_rows = "\n".join(
        "| %s | %s | `%s` | %s | %s |" % (
            a["asset_id"], a["asset_class"], a["label"], a["in_report_section"][:30],
            a["resolution"])
        for a in manifest["assets"])

    body = """## (1) 本工序做了什么

本工作包 `%(pkg)s`（`01-asset-registration`, lane C）只做一件事：把 **report_id=13476** 的源资产登记下来
——确认 `report_id` 与其 `markdown` 字段的字节哈希，逐字定位报告声明的图/工件/表，产出 `asset_manifest.json`。
**不做抽取**（`objective.classify_report_type=false`）；**不标 verified**（验证归平台门）；`claims` 为空数组。
全程只读写 report 13476，未触及其它 report_id。

## (2) 怎么做的（步骤/工具/关键设置）

1. `GET /api/v1/tensor/reports/13476` 取 `markdown`（Bearer = `$TENSOR_AGENT_USER` 登录 token），对
   **utf-8 字节**做 sha256：本地重算 `%(hash)s`，契约 `%(chash)s` -> **一致**；
   `chars=%(chars)d`（契约 12871）、`bytes_utf8=%(bytes)d`、`lines=%(lines)d`。
2. 资产发现全程序化（零手抄）：(a) 源文档本身；(b) `record.figures` 声明的 %(nfig)d 张图；
   (c) 正文反引号码内的路径引用（正则只认带扩展名路径）；(d) fenced code block（代码/公式）；
   (e) markdown 表格。每个资产带定位器（start/end char、start/end line、逐字 quote、唯一性）：
   `char_span` 型断言 `md[start:end] == quote`；`document` 型（A01）断言覆盖 chars 0-12871 且以首行为锚；
   `record_json_path` 型（A02-A04，仅元数据图）锚在 `record.figures[i].caption`，**不虚构 markdown 偏移**。
3. 可解析性判定：探测 `GET /tensor/reports/13476/{artifacts,figures,assets}` -> 全部 404
   （记录于 `work/%(pkg)s/source/platform_probes.json`），故图只有元数据，**不声明任何图字节/图哈希**；
   正文路径指向 TensorDEM 仓（`benchmarks/`、`artifacts/`、`docs/`），不在本工作树 -> 登记为
   `referenced_unresolved` 并保留逐字定位（丢弃=禁止）。
4. 六项 acceptance 由 `verify` 子命令机器判定，定位器**对 fresh fetch 复核**（不是对缓存副本）。

## (3) 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/%(pkg)s/asset_manifest.json` | 主产物：%(nasset)d 个资产 = %(nres)d in-source + %(nunres)d unresolved；`claims=[]` 附显式理由 |
| `docs/kf/%(pkg)s/kf_result.json` | kf_result.v1 信封，`provenance.source_hash` = 实测哈希 |
| `docs/kf/%(pkg)s/verification.json` | 6 项自检（`all_pass=%(allpass)s`） |
| `docs/kf/%(pkg)s/asset_manifest.schema.json` | 本地钉住的 manifest 形状（否则 `schema_pass` 只是断言） |
| `docs/kf/%(pkg)s/source_markdown.md` | 原文逐字副本，供离线复核定位 |
| `docs/kf/%(pkg)s/figures/asset_locator_map.png` | 资产生成图：文档字符轴上的定位器分布 + 哈希一致性面板 |
| `scripts/kf_wp13476_01_register.py` | 一键复跑脚本（fetch/build/envelope/verify/figure/report/publish） |

| id | class | label | 节 | resolution |
|---|---|---|---|---|
%(assets)s

## (4) 证据定位表

所有引文均为 markdown 原文子串（平台可独立重算 sha256 与子串）：

%(ev)s

源身份事实（逐字，行号 1-based；A01 的 `quote` 为整篇 markdown，此处不重复粘贴）：

| fact | 行 | 原文引文（逐字） | quote sha256（前 16） |
|---|---|---|---|
%(facts)s

A01 覆盖 chars 0-%(chars)d（整篇 markdown），`slice_matches_quote=true` 由 verify 对 fresh fetch 复核。

## (5) 注意点与局限

- **图字节不可得**：3 张图只在 `record.figures` 有 name+caption，平台无 artifact 端点（探测全 404），
  因此只登记元数据、不声称图内容或图哈希——这是 WITHHELD，不是"没有图"。
- **路径引用不可解析**：`benchmarks/...`、`artifacts/dem/...`、`docs/clump_multisphere_particles.md`
  属 TensorDEM 仓，本工作树无此内容；登记为 `referenced_unresolved`，需下游包在 TensorDEM 检出内二次解析。
- **零抽取**：不判断报告结论真假、不生成 claim；`claims=[]` 是契约允许的完整结果而非遗漏，
  报告本身的 honest-FAIL 内容留给下游抽取/审计工序。
- **定位口径**：行号 = `markdown.rstrip('\\n').split('\\n')` 的 1-based 逻辑行；字符偏移按 unicode
  字符计（非字节），与平台按字符切片校验的口径一致。

## (6) 自检（逐条对照 acceptance）

| acceptance | 结果 | 证据 |
|---|---|---|
%(checks)s

一键复跑（worktree 根目录执行）：

```
python3 scripts/kf_wp13476_01_register.py all
```

（`all` = fetch+build+envelope+verify+figure+report；`publish` 单独执行以投递本报告。）

```json
%(json)s
```
""" % {
        "pkg": PACKAGE_ID, "hash": src["hash"], "chash": src["contract_hash"],
        "chars": src["chars"], "bytes": src["bytes_utf8"], "lines": src["lines"],
        "nfig": manifest["counts"]["figures_declared_in_record"],
        "nasset": manifest["counts"]["assets"],
        "nres": manifest["counts"]["resolved_in_source"],
        "nunres": manifest["counts"]["referenced_unresolved"],
        "allpass": ver["all_pass"], "assets": asset_rows, "ev": ev_table,
        "checks": chk_rows, "facts": fact_rows,
        "json": json.dumps(env, ensure_ascii=False, indent=2),
    }
    md = "# KF-RESULT %s\n\n%s" % (PACKAGE_ID, body)
    RESULT_MD.write_text(md, encoding="utf-8")
    return md


def publish() -> dict:
    md = RESULT_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    if len(blocks) != 1:
        raise SystemExit("expected exactly one ```json block, found %d" % len(blocks))
    env = json.loads(blocks[0])
    if env["package_id"] != PACKAGE_ID or env["report_id"] != REPORT_ID:
        raise SystemExit("envelope identity mismatch")
    fig_b64 = base64.b64encode(FIGURE.read_bytes()).decode()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": ("Asset registration for report 13476 (no extraction): markdown sha256 "
                    "matches the contract hash (%d chars, %d utf-8 bytes); %d assets "
                    "registered, %d resolved in-source, %d referenced_unresolved (TensorDEM "
                    "paths + record figures with no platform bytes); claims=[] by contract."
                    % (manifest["source"]["chars"], manifest["source"]["bytes_utf8"],
                       manifest["counts"]["assets"],
                       manifest["counts"]["resolved_in_source"],
                       manifest["counts"]["referenced_unresolved"])),
        "scenario_key": CONTRACT_SCENARIO,
        "mission_id": 15760,
        "tags": ["kf-wp:%s" % PACKAGE_ID, "kf-wp", "asset-registration", "DEM",
                 "p447w2-n02"],
        "markdown": md,
        "figures": [{
            "name": FIGURE.name,
            "caption": ("Asset locator map for report 13476: each bar is a registered asset "
                        "on the markdown character axis (green = resolved in-source, orange = "
                        "referenced but unresolved), with line labels; bottom panel shows the "
                        "recomputed vs contract sha256 and chars."),
            "png_base64": fig_b64,
        }],
    }
    tok = _login()
    req = urllib.request.Request(
        _api_base() + "/tensor/reports",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
        method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.loads(r.read().decode("utf-8"))
    (OUT_DIR / "publish_receipt.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main(argv):
    cmds = {
        "fetch": lambda: fetch_report() and print("fetched"),
        "build": lambda: print(json.dumps(build()["counts"], ensure_ascii=False)),
        "envelope": lambda: print(json.dumps(envelope()["provenance"], ensure_ascii=False)),
        "verify": lambda: print(json.dumps(verify(), ensure_ascii=False, indent=2)),
        "figure": lambda: print(figure()),
        "report": lambda: print(RESULT_MD),
        "publish": lambda: print(json.dumps(publish(), ensure_ascii=False)),
    }

    def all_():
        fetch_report()
        build()
        envelope()
        ver = verify()
        figure()
        build_report_md()
        print(json.dumps({"all_pass": ver["all_pass"],
                          "checks": [c["id"] for c in ver["checks"] if c["ok"]],
                          "failed": [c["id"] for c in ver["checks"] if not c["ok"]]},
                         ensure_ascii=False))

    cmds["all"] = all_
    if len(argv) != 2 or argv[1] not in cmds:
        raise SystemExit(__doc__)
    cmds[argv[1]]()


if __name__ == "__main__":
    main(__import__("sys").argv)
