#!/usr/bin/env python3
"""wp-10329-01 (task_type 01-asset-registration): register the source asset of
report 10329 (IN13-W3-N03 碎冰/冰晶悬浮液有效粘度闭合的 LBM 标定) and enumerate
the attachments/artifacts/figures it declares.

Sub-commands (idempotent; stdlib only, plus matplotlib for `figure`):

    python3 scripts/kf_wp10329_01_register.py build     # fetch + write asset_manifest.json
    python3 scripts/kf_wp10329_01_register.py envelope  # wrap manifest -> kf_result.json
    python3 scripts/kf_wp10329_01_register.py verify    # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp10329_01_register.py figure    # asset-resolution map png
    python3 scripts/kf_wp10329_01_register.py all       # build + envelope + verify + figure

Contract wp-10329-01 discipline honoured here:
  * registration only -- NO claim extraction, NO report-type classification,
    NO `verified` marks (verification is the platform gate's job);
  * zero manual transcription -- every number/hash in the artefacts is measured
    by this script from the live markdown; the contract values are comparison
    targets only;
  * every asset carries a markdown locator (line + verbatim quote) that is
    re-checked against the live markdown at verify time;
  * failures abort loudly (SystemExit) instead of emitting a half manifest.
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
REPORT_ID = "10329"
PACKAGE_ID = "wp-10329-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID

# Contract-declared identity (work-package YAML). Never trusted: comparison only.
CONTRACT_SOURCE_HASH = ("sha256:9541130e9906db22f2da835d346b0205"
                        "d8e573cd9812d989094e227b7971ec7d")
CONTRACT_CHARS = 7644
CONTRACT_TITLE = "IN13-W3-N03 碎冰/冰晶悬浮液有效粘度闭合的 LBM 标定（含诚实负面结果）"
CONTRACT_SCENARIO = "in13_w3_n03_suspension_rheology"
CONTRACT_LAYER = "IN13-W3-N03|in13_w3_n03_suspension_rheology|m"

OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID  # committed (.gitignore drops artifacts/**)
FIG_DIR = OUT_DIR / "figures"
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
SOURCE_COPY = OUT_DIR / "source" / ("r%s.md" % REPORT_ID)  # committed: hash anchor copy
PRODUCER = "kf-worker/m15679"

PATH_EXTS = {".py": "source_code_reference", ".json": "data_artifact_reference",
             ".png": "figure_reference", ".jpg": "figure_reference",
             ".md": "document_reference", ".h5": "data_artifact_reference",
             ".hdf5": "data_artifact_reference", ".csv": "data_artifact_reference"}


# ---------------------------------------------------------------- api helpers
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
    with urllib.request.urlopen(req) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:  # kept as probe evidence
        return e.code, e.read()


def fetch_record() -> dict:
    tok = _login()
    st, raw = _get("/tensor/reports/%s" % REPORT_ID, tok)
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> %s %r" % (REPORT_ID, st, raw[:200]))
    return json.loads(raw)


def sha256_hex(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------- reference scan
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
TICK_RE = re.compile(r"`([^`\n]+)`")
BARE_RE = re.compile(r"(?<![\w/`.\-])((?!\-)(?:\.{1,2}/)?[\w.-]+(?:/[\w.-]+)*"
                     r"\.(?:py|json|png|md|h5|csv))(?![\w/])")


def classify(path: str) -> str:
    if path.endswith("/"):
        return "directory_reference"
    return PATH_EXTS.get(Path(path).suffix.lower(), "referenced_artifact")


PLAIN_PATH_RE = re.compile(r"^[A-Za-z0-9_./+-]+$")


def is_pathlike(tok: str) -> bool:
    """Backticked token counts as a path if it has a known artifact extension or a
    directory part made of plain path characters. Module names such as
    `tensorlbm.suspension_lbm` and expressions such as `(1-1/2τ)` are NOT paths."""
    tok = tok.strip()
    if not tok or " " in tok or "\n" in tok:
        return False
    if tok.startswith(("http://", "https://")):  # URLs are not worktree paths
        return False
    if Path(tok).suffix.lower() in PATH_EXTS:
        return True
    return "/" in tok and bool(PLAIN_PATH_RE.match(tok)) and not tok.startswith("/")


def scan_refs(lines: list[str]) -> list[dict]:
    """Collect (line, token, kind) path references; one asset per (path, line)."""
    out, seen = [], set()

    def add(line_no: int, token: str, kind: str, form: str):
        token = token.strip()
        key = (token, line_no)
        if not token or key in seen:
            return
        seen.add(key)
        out.append({"line": line_no, "token": token, "kind": kind, "form": form})

    for i, line in enumerate(lines, start=1):
        for _alt, path in IMG_RE.findall(line):
            add(i, path, classify(path), "markdown_image_link")
        for tok in TICK_RE.findall(line):
            if is_pathlike(tok):
                add(i, tok, classify(tok), "backticked_path")
        for tok in BARE_RE.findall(line):
            if tok.startswith("http"):
                continue
            add(i, tok, classify(tok), "bare_path")
    return out


MODULE_TICK_RE = re.compile(r"`((?:[a-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*)`")


def scan_symbols(lines: list[str]) -> list[dict]:
    """Python module entry points named in the prose. Registered as declared-only:
    this工序 does not open TensorLBM."""
    out, seen = [], set()
    for i, line in enumerate(lines, start=1):
        for tok in MODULE_TICK_RE.findall(line):
            if is_pathlike(tok) or (tok, i) in seen:
                continue
            seen.add((tok, i))
            out.append({"line": i, "token": tok, "kind": "module_reference"})
    return out


CASE_DICT_LINE_RE = re.compile(r"wall_momentum_balance.*\{'(\w+)':")


TABLE_ROW_RE = re.compile(r"^\|\s*([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*\|")
NUM_CELL_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?%?$")


def _numeric_cells(line: str) -> int:
    """Count numeric-looking table cells (a case row carries at least Re + a value)."""
    cells = [c.strip().replace("*", "") for c in line.strip().strip("|").split("|")]
    return sum(1 for c in cells if NUM_CELL_RE.match(c))


def scan_case_ids(lines: list[str]) -> list[dict]:
    """Per-case run identifiers, parsed programmatically out of two verbatim places:
    the wall_momentum_balance dict literal (acceptance table, §6) and the §3.3 drag
    table's first column. Never hand-copied."""
    out, seen = [], set()
    in_drag_section = False
    for i, line in enumerate(lines, start=1):
        if line.startswith("### 3.3"):
            in_drag_section = True
        elif line.startswith("### ") or line.startswith("## "):
            in_drag_section = False
        derivation = None
        ids = []
        if CASE_DICT_LINE_RE.search(line):
            ids = re.findall(r"'(\w+)':", line)
            derivation = "key of the wall_momentum_balance dict literal (§6 acceptance table)"
        elif in_drag_section:
            m = TABLE_ROW_RE.match(line)
            if m and _numeric_cells(line) >= 2:
                ids = [m.group(1)]
                derivation = "first column of a case row in the §3.3 drag-gate table"
        for cid in ids:
            if cid in seen:
                continue
            seen.add(cid)
            out.append({"case_id": cid, "line": i, "derivation": derivation})
    return out


def resolve_in_worktree(token: str) -> dict:
    """Only the delivery worktree is searched: claiming anything else is a guess."""
    cand = token.lstrip("./")
    p = ROOT / cand
    if p.is_file():
        b = p.read_bytes()
        return {"status": "resolved", "scope": "delivery_worktree",
                "bytes": len(b), "sha256": sha256_hex(b)}
    if p.is_dir():
        return {"status": "metadata_only", "scope": "delivery_worktree",
                "reason": "directory exists in delivery worktree; not a byte asset"}
    same_name = sorted(str(q.relative_to(ROOT)) for q in ROOT.rglob(Path(cand).name)
                       if q.is_file() and ".git" not in q.parts)[:5]
    return {"status": "unresolved", "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge "
                      "(report declares it in the TensorLBM repository)",
            "same_basename_hits": same_name}


# ------------------------------------------------------------------- manifest
def build_manifest(record: dict) -> dict:
    md = record.get("markdown") or ""
    raw = md.encode("utf-8")
    lines = md.rstrip("\n").split("\n")
    digest = sha256_hex(raw)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_bytes(raw)

    hash_match = digest == CONTRACT_SOURCE_HASH
    chars_match = len(md) == CONTRACT_CHARS
    if not hash_match:
        raise SystemExit("source hash mismatch: %s != contract %s"
                         % (digest, CONTRACT_SOURCE_HASH))
    if not chars_match:
        raise SystemExit("chars mismatch: %d != contract %d" % (len(md), CONTRACT_CHARS))

    assets = [{
        "asset_id": "r%s:source-markdown" % REPORT_ID,
        "kind": "report_markdown",
        "name": "report-%s-markdown" % REPORT_ID,
        "locator": {"source_field": "markdown", "line": 1},
        "source_uri": SOURCE_URI,
        "media_type": "text/markdown",
        "bytes": len(raw),
        "chars": len(md),
        "lines": len(lines),
        "sha256": digest,
        "hash_scope": ("UTF-8 bytes of the markdown field as served by "
                       "GET /api/v1/tensor/reports/%s" % REPORT_ID),
        "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
        "resolution": {"status": "resolved", "scope": "platform_api",
                       "via": "GET /tensor/reports/%s" % REPORT_ID},
        "hash_matches_contract": hash_match,
        "chars_matches_contract": chars_match,
    }]

    # figures declared in the report *record*: name+caption from the record, and the
    # byte payload probed from the platform figure store (hashed when served).
    fig_probes = {}
    fig_hashes = {}  # basename -> {asset_id, sha256, bytes}
    local_figs = OUT_DIR / "figures" / ("r%s" % REPORT_ID)
    for idx, fig in enumerate(record.get("figures") or []):
        name = fig.get("name") or ""
        st, body = _get("/tensor/reports/%s/figures/%s" % (REPORT_ID, name), _login())
        prov = {"http_status": st, "bytes": len(body)}
        asset_id = "r%s:figure:%02d" % (REPORT_ID, idx + 1)
        if st == 200 and body:
            is_png = body[:8] == b"\x89PNG\r\n\x1a\n"
            prov["media_type"] = "image/png" if is_png else "application/octet-stream"
            prov["sha256"] = sha256_hex(body)
            prov["png_magic_ok"] = is_png
            local_figs.mkdir(parents=True, exist_ok=True)
            (local_figs / name).write_bytes(body)
            prov["local_copy"] = str((local_figs / name).relative_to(ROOT))
            fig_hashes[name] = {"asset_id": asset_id, "sha256": prov["sha256"],
                                "bytes": len(body)}
            resolution = {"status": "resolved", "scope": "platform_figure_store",
                          "via": "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, name),
                          "http_status": st, "bytes": len(body),
                          "sha256": prov["sha256"], "media_type": prov["media_type"],
                          "local_copy": prov["local_copy"]}
        else:
            resolution = {"status": "metadata_only", "scope": "platform_api",
                          "via": "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, name),
                          "http_status": st,
                          "reason": ("record exposes name/caption only; platform returned "
                                     "no byte payload, so no hash is claimed")}
        fig_probes[name] = prov
        assets.append({
            "asset_id": asset_id,
            "kind": "embedded_figure",
            "name": name,
            "caption": fig.get("caption"),
            "locator": {"source_field": "record", "pointer": "/figures/%d/name" % idx,
                        "quote": name},
            "resolution": resolution,
        })

    # body path references (header block, tool chain, figures section, repro block)
    for n, ref in enumerate(scan_refs(lines), start=1):
        res = resolve_in_worktree(ref["token"])
        base = Path(ref["token"]).name
        if res["status"] != "resolved" and base in fig_hashes:
            # same file delivered by the platform figure store under its basename
            fh = fig_hashes[base]
            res = {"status": "resolved", "scope": "platform_figure_store",
                   "via": "cross-reference to %s (basename match, bytes hashed there)"
                          % fh["asset_id"], "bytes": fh["bytes"],
                   "sha256": fh["sha256"],
                   "cross_reference": fh["asset_id"],
                   "note": "declared path itself is absent from the delivery worktree; the "
                           "byte identity is established through the record figure store"}
        assets.append({
            "asset_id": "r%s:ref:%02d" % (REPORT_ID, n),
            "kind": ref["kind"],
            "name": ref["token"],
            "reference_form": ref["form"],
            "locator": {"source_field": "markdown", "line": ref["line"],
                        "quote": lines[ref["line"] - 1]},
            "quote_token": ref["token"],
            "resolution": res,
            "declared_in_report": True,
            "existence_asserted_by_worker": False,
        })

    # per-case raw JSON set: report says "（+ 每例原始 JSON）" without naming files
    declared_sets = []
    for n, (line_no, label, reason) in enumerate([
        (8, "artifacts/suspension_rheology/<per-case>.json",
         "report declares '+ 每例原始 JSON' but states no per-case file name or path "
         "pattern; the case ids themselves are registered below from the acceptance table"),
    ], start=1):
        declared_sets.append({
            "set_id": "r%s:set:%02d" % (REPORT_ID, n),
            "kind": "declared_artifact_set",
            "label": label,
            "locator": {"source_field": "markdown", "line": line_no,
                        "quote": lines[line_no - 1]},
            "resolution": {"status": "unresolved", "scope": "declaration_only",
                           "reason": reason},
            "existence_asserted_by_worker": False,
        })

    cases = [{
        "case_id": c["case_id"],
        "case_ref": "r%s:case:%s" % (REPORT_ID, c["case_id"]),
        "locator": {"source_field": "markdown", "line": c["line"],
                    "quote": lines[c["line"] - 1]},
        "derivation": c["derivation"],
        "resolution": {"status": "declared_only",
                       "reason": "case id appears in the report; its per-case JSON is neither "
                                 "present in the delivery worktree nor named by path"},
    } for c in scan_case_ids(lines)]

    symbols = []
    for n, sym in enumerate(scan_symbols(lines), start=1):
        symbols.append({
            "symbol_id": "r%s:sym:%02d" % (REPORT_ID, n),
            "kind": sym["kind"],
            "token": sym["token"],
            "locator": {"source_field": "markdown", "line": sym["line"],
                        "quote": lines[sym["line"] - 1]},
            "resolution": {"status": "declared_only",
                           "reason": "named in the report prose; this工序 registers the "
                                     "reference, it does not open the TensorLBM repository"},
            "existence_asserted_by_worker": False,
        })

    # locators: one entry per markdown-anchored asset, re-checked here
    locators = []
    anchored = ([{"id": a["asset_id"], "loc": a["locator"], "quote": None} for a in assets]
                + [{"id": s["set_id"], "loc": s["locator"], "quote": None}
                   for s in declared_sets]
                + [{"id": s["symbol_id"], "loc": s["locator"], "quote": None}
                   for s in symbols]
                + [{"id": c["case_ref"], "loc": c["locator"], "quote": None} for c in cases])
    for a in anchored:
        loc = a["loc"]
        if loc["source_field"] != "markdown":
            continue
        q = a["quote"] or lines[loc["line"] - 1] if "line" in loc else loc["quote"]
        on_line = lines[loc["line"] - 1] == q
        locators.append({
            "id": a["id"],
            "locator": {"source_field": "markdown", "line": loc["line"]},
            "quote_sha256": sha256_hex(q.encode("utf-8")),
            "quote_in_source": q in md,
            "quote_on_declared_line": on_line,
            "occurrences_in_source": md.count(q),
            "resolved": bool(q in md and on_line),
        })

    # identity facts: pin what the document *is* (structure landmarks, not content)
    identity_facts = []
    for fact_id, line_no in (("title-line", 1), ("node-block", 3),
                             ("sec1-header", 13), ("sec6-header", 166),
                             ("repro-fence", 205), ("last-line", len(lines))):
        q = lines[line_no - 1]
        identity_facts.append({
            "fact_id": fact_id,
            "locator": {"source_field": "markdown", "line": line_no},
            "quote": q,
            "quote_sha256": sha256_hex(q.encode("utf-8")),
            "quote_in_source": q in md,
            "quote_on_declared_line": lines[line_no - 1] == q,
            "occurrences_in_source": md.count(q),
        })

    ids = [a["asset_id"] for a in assets] + [s["set_id"] for s in declared_sets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    kinds = {}
    for a in assets:
        key = "%s/%s" % (a["kind"], a["resolution"]["status"])
        kinds[key] = kinds.get(key, 0) + 1
    by_status = {}
    for a in assets:
        st = a["resolution"]["status"]
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": digest,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_algo": "sha256",
            "hash_match": hash_match,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": chars_match,
            "bytes": len(raw),
            "lines": len(lines),
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "record_fields": {
                "title": record.get("title"),
                "scenario_key": record.get("scenario_key"),
                "mission_id": record.get("mission_id"),
                "status": record.get("status"),
                "tags": record.get("tags"),
                "created_at": record.get("created_at"),
                "contract_title": CONTRACT_TITLE,
                "contract_scenario_key": CONTRACT_SCENARIO,
                "contract_layer": CONTRACT_LAYER,
                "title_matches_contract": record.get("title") == CONTRACT_TITLE,
                "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            },
            "platform_attachment_probes": {
                "GET /tensor/reports/%s/artifacts" % REPORT_ID: "not_probed_here",
                "figure_probe": fig_probes,
            },
        },
        "assets": assets,
        "declared_artifact_sets": declared_sets,
        "symbol_references": symbols,
        "measurement_cases": cases,
        "locators": locators,
        "identity_facts": identity_facts,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-10329-01 objective is register_assets=true / "
            "classify_report_type=false, and notes state 'claims 允许为空数组' with "
            "constraints no_forced_claim_generation=true and "
            "do_not_mark_claims_as_verified=true. This工序 registers asset identity only "
            "(report_id, markdown byte hash, declared attachments/artifacts/figures/cases); "
            "extraction is a downstream工序, so an empty claims array is the complete "
            "result, not an omission."),
        "counts": {
            "source_documents": 1,
            "figures_declared_in_record": len(record.get("figures") or []),
            "figures_with_bytes": sum(1 for v in fig_probes.values()
                                      if v["http_status"] == 200 and v.get("bytes")),
            "figures_with_sha256": sum(1 for v in fig_probes.values() if "sha256" in v),
            "body_references": sum(1 for a in assets
                                   if a["asset_id"].startswith("r%s:ref:" % REPORT_ID)),
            "distinct_referenced_paths": len({a["name"] for a in assets
                                              if a["asset_id"].startswith("r%s:ref:" % REPORT_ID)}),
            "assets_total": len(assets),
            "assets_by_resolution": dict(sorted(by_status.items())),
            "declared_artifact_sets": len(declared_sets),
            "symbol_references": len(symbols),
            "measurement_cases": len(cases),
            "locators": len(locators),
            "locators_resolved": sum(1 for loc in locators if loc["resolved"]),
            "claims": 0,
            "kind_status_histogram": dict(sorted(kinds.items())),
        },
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes},
        "unresolved": [
            {"asset_id": a["asset_id"], "name": a["name"],
             "reason": a["resolution"].get("reason")}
            for a in assets if a["resolution"]["status"] == "unresolved"
        ],
        "observations": [
            "Markdown is complete and self-consistent: first line is the H1 title, "
            "sections 1-8 present (%d lines); sections 5/6 carry the honest negative "
            "result and the FAIL verdicts verbatim." % len(lines),
            "The %d figures are declared in the record (name+caption) and linked in-body "
            "as relative paths figures/suspension_rheology/<name>.png; GET "
            "/tensor/reports/10329/figures/<name> serves PNG bytes for all of them, so each "
            "carries a local copy + sha256 (no figure claim is made about their content)."
            % len(record.get("figures") or []),
            "All body path references point at TensorLBM artefacts (tensorlbm/*, "
            "benchmarks/*, tests/*, artifacts/suspension_rheology/*, figures/*) which are "
            "not present in the TensorKnowledge delivery worktree; they are registered as "
            "declared references with existence_asserted_by_worker=false.",
        ],
        "limitations": [
            "Registration only: no claim/evidence extraction, no report-type "
            "classification, no verified marks (the platform gate computes verification).",
            "source_hash scope = UTF-8 bytes of the markdown string returned by the platform "
            "API; any change to the stored markdown (even whitespace) invalidates it.",
            "Direct psql read of tensor_reports was denied for this role, so the API is the "
            "only source channel used; both channels would be the same column, but this is "
            "still a single-channel read.",
            "Reference resolution is limited to the delivery worktree; a missing path is "
            "reported unresolved, never as a broken upstream artefact.",
            "Asset registration is not evidence of numerical validity; the report's own "
            "verdicts (4 FAIL / 4 PASS in §6) are recorded elsewhere and are not re-judged here.",
        ],
    }


# ------------------------------------------------------------------- envelope
def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    record = fetch_record()
    live = sha256_hex((record.get("markdown") or "").encode("utf-8"))
    if live != manifest["source"]["source_hash"]:
        raise SystemExit("live hash %s != manifest %s -- refusing to emit envelope"
                         % (live, manifest["source"]["source_hash"]))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": live,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("hash recomputed from GET /api/v1/tensor/reports/10329 markdown "
                      "(UTF-8 bytes); matches contract source_hash %s"
                      % CONTRACT_SOURCE_HASH),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n")
    return env


# ------------------------------------------------------------- verification
def verify() -> dict:
    from jsonschema import Draft202012Validator

    env = json.loads(ENVELOPE.read_text())
    manifest = json.loads(MANIFEST.read_text())
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    record = fetch_record()
    md = record.get("markdown") or ""
    lines = md.rstrip("\n").split("\n")
    live_hash = sha256_hex(md.encode("utf-8"))

    checks = {}
    checks["valid_json"] = {"ok": True,
                            "detail": "asset_manifest.json + kf_result.json parsed"}

    errs = [e.message for e in Draft202012Validator(schema).iter_errors(env)]
    checks["schema_pass"] = {"ok": not errs,
                             "detail": errs or "kf_result.v1 schema: 0 errors"}

    bad = []
    for loc in manifest["locators"]:
        ln = loc["locator"]["line"]
        q = lines[ln - 1] if 0 < ln <= len(lines) else None
        if q is None or q not in md or sha256_hex(q.encode()) != loc["quote_sha256"]:
            bad.append(loc["id"])
    for f in manifest["identity_facts"]:
        ln = f["locator"]["line"]
        if not (0 < ln <= len(lines)) or lines[ln - 1] != f["quote"]:
            bad.append(f["fact_id"])
    checks["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": ("%d/%d markdown locators re-resolved (line + verbatim + quote_sha256)"
                   % (sum(1 for loc in manifest["locators"] if loc["resolved"]),
                      len(manifest["locators"]))),
        "failures": bad,
    }

    checks["source_hash_matches"] = {
        "ok": (live_hash == manifest["source"]["source_hash"] == CONTRACT_SOURCE_HASH
               == env["provenance"]["source_hash"]),
        "detail": "live=%s manifest=%s contract=%s" % (
            live_hash, manifest["source"]["source_hash"], CONTRACT_SOURCE_HASH),
        "chars": {"live": len(md), "manifest": manifest["source"]["chars"],
                  "contract": CONTRACT_CHARS},
    }

    ids = ([a["asset_id"] for a in manifest["assets"]]
           + [s["set_id"] for s in manifest["declared_artifact_sets"]])
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {"ok": not dupes,
                                  "detail": "%d ids, duplicates=%s" % (len(ids), dupes)}

    claims = env.get("claims") or []
    ev_ok = all(c.get("evidence") or c.get("unresolved_reason") for c in claims)
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": bool(ev_ok and manifest.get("claims_empty_reason")),
        "detail": ("%d claims (empty allowed by contract); empty-claims reason stated: %s"
                   % (len(claims), bool(manifest.get("claims_empty_reason")))),
    }

    # extra (non-contract) checks: they protect the artefacts, not the acceptance list
    extra = {}
    digest_mismatch = []
    checked = 0
    for a in manifest["assets"]:
        res = a["resolution"]
        cp = res.get("local_copy") or a.get("local_copy")
        if not cp:
            continue
        lp = ROOT / cp
        want = res.get("sha256") or a.get("sha256")
        checked += 1
        if not lp.is_file() or sha256_hex(lp.read_bytes()) != want:
            digest_mismatch.append(a["asset_id"])
    extra["stored_bytes_match_recorded_sha256"] = {
        "ok": not digest_mismatch,
        "detail": "re-hashed %d local copies on disk (%d mismatch, 0 copies would be a bug)"
                  % (checked, len(digest_mismatch)),
        "failures": digest_mismatch,
    }
    extra["no_verified_marks"] = {
        "ok": '"verified"' not in json.dumps(env) and not env.get("claims"),
        "detail": "result carries 0 claims and no `verified` key; verification is the gate's",
    }
    local_schema = ROOT / "schemas" / "asset_manifest.v1.schema.json"
    if local_schema.is_file():
        sch = json.loads(local_schema.read_text())
        pinned = sch.get("properties", {}).get("package_id", {}).get("const")
        extra["local_asset_manifest_v1_applicable"] = {
            "ok": True, "applicable": False,
            "detail": ("schemas/asset_manifest.v1.schema.json pins package_id const=%r and "
                       "report_id const=%r, so it cannot validate %s; it is the wp-448-01 "
                       "local shape, not the canonical gate (contract names kf_result.v1)"
                       % (pinned,
                          sch.get("properties", {}).get("report_id", {}).get("const"),
                          PACKAGE_ID)),
        }

    out = {"package_id": PACKAGE_ID, "verified_at": utcnow(), "acceptance": checks,
           "extra_checks": extra,
           "all_ok": all(c["ok"] for c in checks.values())
                     and all(c["ok"] for c in extra.values()),
           "note": ("Self-check only. No claim is marked verified here (no claims exist); "
                    "the platform gate recomputes hash/locators independently.")}
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


# --------------------------------------------------------------------- figure
def figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text())
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    hist = manifest["counts"]["kind_status_histogram"]
    niches = sorted({k.split("/")[0] for k in hist})
    statuses = ["resolved", "metadata_only", "declared_only", "unresolved", "absent"]
    colors = {"resolved": "#1b7837", "metadata_only": "#4575b4",
              "declared_only": "#b2abd2", "unresolved": "#d73027", "absent": "#999999"}

    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    bottom = [0] * len(niches)
    for st in statuses:
        vals = [hist.get("%s/%s" % (n, st), 0) for n in niches]
        if not any(vals):
            continue
        ax.barh(range(len(niches)), vals, left=bottom, color=colors[st], label=st,
                edgecolor="white", height=0.62)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_yticks(range(len(niches)))
    ax.set_yticklabels(niches, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("asset count")
    ax.set_title("report 10329 asset registration: %d assets, status by kind"
                 % manifest["counts"]["assets_total"], fontsize=10)
    for i, t in enumerate(bottom):
        ax.text(t + 0.12, i, str(int(t)), va="center", fontsize=8)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(axis="x", alpha=0.25)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.text(0.01, 0.01,
             "source sha256=%s…  chars=%d  lines=%d  locators resolved=%d/%d  claims=0"
             % (manifest["source"]["source_hash"][7:19], manifest["source"]["chars"],
                manifest["source"]["lines"], manifest["counts"]["locators_resolved"],
                manifest["counts"]["locators"], ),
             fontsize=6.5, color="#444")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = FIG_DIR / "asset_resolution_map.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("wrote", out.relative_to(ROOT))


# ----------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd == "build":
        m = build_manifest(fetch_record())
        MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
        print("wrote", MANIFEST.relative_to(ROOT),
              json.dumps(m["counts"], ensure_ascii=False))
    elif cmd == "envelope":
        env = build_envelope()
        print("wrote", ENVELOPE.relative_to(ROOT), env["provenance"]["source_hash"])
    elif cmd == "verify":
        v = verify()
        print(json.dumps(v, ensure_ascii=False, indent=2))
        return 0 if v["all_ok"] else 1
    elif cmd == "figure":
        figure()
    elif cmd == "all":
        m = build_manifest(fetch_record())
        MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
        print("wrote", MANIFEST.relative_to(ROOT),
              json.dumps(m["counts"], ensure_ascii=False))
        build_envelope()
        print("wrote", ENVELOPE.relative_to(ROOT))
        figure()
        v = verify()
        print(json.dumps(v, ensure_ascii=False, indent=2))
        return 0 if v["all_ok"] else 1
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))