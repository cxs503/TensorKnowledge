#!/usr/bin/env python3
"""Work package wp-9656-01 (task_type 01-asset-registration): register source assets of report 9656.

Scope guard (contract wp-9656-01):
  * touches ONLY report_id=9656 -- no other report is read or written;
  * registration only: NO claim extraction, NO report-type classification,
    NO `verified` marks (verification is computed by the platform gate);
  * zero manual transcription -- every number/quote below is measured from the
    markdown bytes served by GET /api/v1/tensor/reports/9656, and every locator
    quote is a verbatim slice md[start_char:end_char] re-checked at verify time;
  * missing information stays missing (unresolved / metadata_only), never invented.

Sub-commands (idempotent):
    python3 scripts/kf/wp9656_01_register.py build      # fetch + write asset_manifest.json
    python3 scripts/kf/wp9656_01_register.py envelope   # wrap manifest -> kf_result.json
    python3 scripts/kf/wp9656_01_register.py verify     # acceptance checks -> verification.json
    python3 scripts/kf/wp9656_01_register.py figure     # locator map png (report figure)
    python3 scripts/kf/wp9656_01_register.py all        # build + envelope + verify + figure
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

ROOT = Path(__file__).resolve().parents[2]
REPORT_ID = "9656"
PACKAGE_ID = "wp-9656-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
SOURCE_FIELD = "markdown"

# Contract-declared identity (work-package YAML). Comparison targets only --
# the script never copies these into the manifest; it measures and compares.
CONTRACT_SOURCE_HASH = "sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619"
CONTRACT_CHARS = 12470
CONTRACT_TITLE = "IN101-N05 冰区推进轴系横向振动与轴承载荷：六条判据全通过（REAL）"
CONTRACT_SCENARIO = "ice_shaft_vibration"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID   # committed: repo .gitignore drops artifacts/**
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
LOCAL_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.wp9656-01.schema.json"
PRODUCER = "kf-worker/m15664"

# Read-only probes of checkouts that might hold the referenced artifacts. Recorded
# honestly either way; nothing outside this worktree is ever written.
EXTERNAL_PROBES = ("/root/ship-performance-platform",)

EXT_KIND = {
    ".png": "figure_reference",
    ".jpg": "figure_reference",
    ".json": "data_artifact_reference",
    ".csv": "data_artifact_reference",
    ".txt": "document_reference",
    ".md": "document_reference",
    ".py": "source_code_reference",
}


# ---------------------------------------------------------------- platform I/O
def _api_base() -> str:
    return os.environ["TENSOR_API_BASE"].rstrip("/")


def _req(url: str, token: str | None = None, data: bytes | None = None,
         ctype: str = "application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def login() -> str:
    base, user, pw = _api_base(), os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    try:
        d = _req(base + "/auth/login",
                 data=json.dumps({"username": user, "password": pw}).encode())
    except urllib.error.HTTPError:
        d = _req(base + "/auth/login",
                 data=urllib.parse.urlencode({"username": user, "password": pw}).encode(),
                 ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_record(token: str | None = None) -> dict:
    token = token or login()
    d = _req("%s/tensor/reports/%s" % (_api_base(), REPORT_ID), token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    if not isinstance(d.get("markdown"), str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    if str(d.get("id")) != REPORT_ID:
        raise SystemExit("scope violation: served report id %r != %s" % (d.get("id"), REPORT_ID))
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_text(d["markdown"], encoding="utf-8")
    return d


def probe_platform_artifacts(token: str) -> dict:
    """Best-effort discovery of a platform attachment listing; never fabricate data."""
    probes = {}
    for path in ("/tensor/reports/%s/artifacts" % REPORT_ID,
                 "/tensor/artifacts?report_id=%s" % REPORT_ID):
        try:
            d = _req(_api_base() + path, token)
            probes[path] = {"status": "ok", "shape": type(d).__name__,
                            "n_items": len(d) if isinstance(d, (list, dict)) else None}
        except urllib.error.HTTPError as e:
            probes[path] = {"status": "http_%s" % e.code}
        except Exception as e:  # noqa: BLE001 - record, never guess
            probes[path] = {"status": "error", "detail": type(e).__name__}
    return probes


# ---------------------------------------------------------------- scanning
def _rel(path: Path) -> str:
    """Repo-relative path when possible; absolute otherwise (never raises)."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)

IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)\s]+)\)")
TICK_PATH_RE = re.compile(r"`(?P<path>[A-Za-z0-9_./*-]+\.(?:json|png|jpg|py|md|txt|csv))(?::\d+(?:-\d+)?)?`")
TICK_DIR_RE = re.compile(r"`(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*/)`")
BARE_PATH_RE = re.compile(r"(?<![\w/`.*])(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|png|jpg|py|md|txt|csv))(?::\d+(?:-\d+)?)?(?![\w`/.])")


def line_starts(md: str) -> list[int]:
    starts, pos = [0], 0
    for ln in md.split("\n"):
        pos += len(ln) + 1
        starts.append(pos)
    return starts


def scan_references(md: str) -> list[dict]:
    """Ordered path-like references with exact char spans (deduped by span containment)."""
    starts = line_starts(md)
    lines = md.split("\n")
    found = []
    for i, line in enumerate(lines, start=1):
        base = starts[i - 1]
        hits = []
        for m in IMG_RE.finditer(line):
            hits.append((m.start("path"), m.end("path"), m.group("path"), "markdown_image", m.group("alt")))
        for m in TICK_PATH_RE.finditer(line):
            hits.append((m.start("path"), m.end("path"), m.group("path"), "backticked_ref", None))
        for m in TICK_DIR_RE.finditer(line):
            hits.append((m.start("path"), m.end("path"), m.group("path"), "backticked_dir", None))
        for m in BARE_PATH_RE.finditer(line):
            hits.append((m.start("path"), m.end("path"), m.group("path"), "bare_ref", None))
        # prefer backticked/image hits over bare hits that overlap them
        hits.sort(key=lambda h: (0 if h[3] != "bare_ref" else 1, -(h[1] - h[0])))
        taken = []
        for h in hits:
            if any(not (h[1] <= t[0] or h[0] >= t[1]) for t in taken):
                continue
            taken.append(h)
        for s, e, path, via, alt in sorted(taken):
            found.append({"start_char": base + s, "end_char": base + e, "start_line": i,
                          "path": path, "via": via, "alt": alt,
                          "quote": md[base + s: base + e], "line_quote": line})
    return found


def scan_tables(md: str) -> list[dict]:
    """Inventory of markdown tables (registration only -- no cell extraction)."""
    lines = md.split("\n")
    starts = line_starts(md)
    tables, i = [], 0
    sep_re = re.compile(r"^\|[\s:|-]+\|$")
    while i < len(lines) - 1:
        if lines[i].startswith("|") and sep_re.match(lines[i + 1].strip()):
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            header = lines[i]
            tables.append({
                "table_id": "r9656:table:%02d" % (len(tables) + 1),
                "line_start": i + 1,
                "line_end": j,
                "rows": j - i - 2,
                "cols": len([c for c in header.strip().strip("|").split("|")]),
                "header_quote": header,
                "header_unique": md.count(header) == 1,
                "start_char": starts[i],
            })
            i = j
        else:
            i += 1
    return tables


def scan_sections(md: str) -> list[dict]:
    out = []
    for ln in md.split("\n"):
        if ln.startswith("## "):
            out.append({"line_heading": ln, "quote": ln[3:].strip(),
                        "unique": md.count(ln) == 1})
    return out


def kind_of(path: str) -> str:
    p = path.lower()
    if p.endswith("/"):
        return "directory_reference"
    return EXT_KIND.get(Path(p).suffix, "document_reference")


def resolve_local(path: str) -> dict:
    """Worktree-only resolution of a declared path (no cross-repo guessing)."""
    if path.endswith("/"):
        d = (ROOT / path).resolve()
        inside = str(d).startswith(str(ROOT))
        if inside and d.is_dir():
            return {"status": "resolved", "scope": "delivery_worktree",
                    "resolved_path": str(d.relative_to(ROOT)),
                    "entries": sorted(p.name for p in d.iterdir())[:20],
                    "n_entries": sum(1 for _ in d.iterdir())}
        return {"status": "unresolved", "scope": "delivery_worktree",
                "reason": "directory not present in the TensorKnowledge delivery worktree"}
    for cand in (ROOT / path, ROOT / path.lstrip("./")):
        try:
            cand = cand.resolve()
        except OSError:
            continue
        if not str(cand).startswith(str(ROOT)):
            continue
        if cand.is_file():
            raw = cand.read_bytes()
            return {"status": "resolved", "scope": "delivery_worktree",
                    "resolved_path": str(cand.relative_to(ROOT)),
                    "bytes": len(raw), "sha256": "sha256:" + hashlib.sha256(raw).hexdigest()}
    return {"status": "unresolved", "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree"}


def resolve_external(path: str) -> list[dict]:
    """Secondary, read-only probe outside the worktree; reported as-is."""
    out = []
    for root in EXTERNAL_PROBES:
        p = Path(root) / path.lstrip("./")
        try:
            if p.is_file():
                raw = p.read_bytes()
                out.append({"root": root, "status": "resolved", "bytes": len(raw),
                            "sha256": "sha256:" + hashlib.sha256(raw).hexdigest()})
            elif p.is_dir():
                out.append({"root": root, "status": "resolved_dir"})
            else:
                out.append({"root": root, "status": "absent"})
        except OSError:
            out.append({"root": root, "status": "probe_error"})
    return out


# ---------------------------------------------------------------- locator checking
def check_locators(assets, tables, sections, md, record) -> tuple[int, list]:
    """Re-check every declared locator against the given markdown. Returns (n_checked, failures)."""
    lines = md.split("\n")
    bad, checked = [], 0
    for a in assets:
        loc = a["locator"]
        quote = loc.get("quote") or ""
        checked += 1
        if loc["method"] == "char_span":
            ok = md[loc["start_char"]:loc["end_char"]] == quote and quote in md
            line_ok = lines[loc["start_line"] - 1] == loc["line_quote"] and \
                loc["line_quote"].find(quote) >= 0
        elif loc["method"] == "document":
            ok = (md[loc["start_char"]:loc["end_char"]] == quote == md[:len(quote)]
                  and loc.get("doc_chars") == len(md) and loc.get("doc_lines") == len(lines))
            line_ok = lines[loc["start_line"] - 1] == quote
        else:  # record_pointer
            figs = [f.get("name") for f in (record.get("figures") or [])]
            idx = int(loc["pointer"].split("/")[2])
            ok = loc["pointer"].startswith("/figures/") and idx < len(figs) and figs[idx] == quote
            line_ok = (quote in md) if loc.get("markdown_image_line") else True
        if not (ok and line_ok):
            bad.append({"asset_id": a["asset_id"], "quote": quote[:80],
                        "span_ok": bool(ok), "line_ok": bool(line_ok)})
    for t in tables:
        checked += 1
        if t["header_quote"] not in md:
            bad.append({"table_id": t["table_id"], "header": t["header_quote"][:80]})
    for s in sections:
        checked += 1
        if s["line_heading"] not in md:
            bad.append({"section": s["line_heading"][:80]})
    return checked, bad


def quote_uniqueness_text(assets, md) -> str:
    """One definition for all assets: strict string occurrence count in the markdown."""
    uniq = sum(1 for a in assets if md.count(a["locator"].get("quote") or "") == 1)
    rec_uniq = sum(1 for a in assets if a["locator"].get("record_unique"))
    return ("%d/%d asset quotes occur exactly once in the markdown; %d recur (flagged "
            "unique=false; positional locators stay unambiguous via start_line/char_span). "
            "%d assets are additionally unique at record level."
            % (uniq, len(assets), len(assets) - uniq, rec_uniq))


# ---------------------------------------------------------------- build
def build_manifest(record: dict, token: str) -> dict:
    md = record["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    md_lines = md.split("\n")

    assets: list[dict] = []
    ids: set[str] = set()

    def add(a: dict) -> None:
        if a["asset_id"] in ids:
            raise SystemExit("duplicate asset_id %r" % a["asset_id"])
        ids.add(a["asset_id"])
        assets.append(a)

    # A0: the source asset itself (document-level locator)
    head = md_lines[0]
    add({
        "asset_id": "r9656:source-markdown",
        "kind": "report_markdown",
        "name": "report-%s-markdown" % REPORT_ID,
        "source_uri": SOURCE_URI,
        "media_type": "text/markdown",
        "bytes": len(raw),
        "chars": len(md),
        "lines": len(md_lines),
        "sha256": digest,
        "hash_scope": "UTF-8 bytes of the `markdown` field as served by GET /api/v1/tensor/reports/9656",
        "local_copy": _rel(SOURCE_COPY),
        # document-level locator: span = first line (the title), quoted verbatim and
        # re-checked as an exact slice; the whole-document extent is carried separately
        "locator": {"method": "document", "source_field": SOURCE_FIELD,
                    "start_char": 0, "end_char": len(head), "start_line": 1,
                    "end_line": len(md_lines), "quote": head,
                    "unique": md.count(head) == 1,
                    "doc_chars": len(md), "doc_bytes_utf8": len(raw),
                    "doc_lines": len(md_lines)},
        "resolution": {"status": "resolved", "scope": "platform_api",
                       "via": "GET /tensor/reports/9656"},
    })

    # A1..An: figures declared in the report record (metadata only unless bytes exist)
    for n, fig in enumerate(record.get("figures") or [], start=1):
        name = fig.get("name") or ""
        b64 = fig.get("png_base64") or ""
        blob = b""
        if b64:
            try:
                blob = base64.b64decode(b64)
            except Exception:  # noqa: BLE001 - record the failure, do not fabricate
                blob = b""
        # cross-link the figure to its markdown image reference, if present
        img_hits = [r for r in scan_references(md) if r["path"].endswith(Path(name).name)]
        add({
            "asset_id": "r9656:figure:%02d" % n,
            "kind": "embedded_figure",
            "name": name,
            "caption": fig.get("caption"),
            "bytes": len(blob) or None,
            "sha256": ("sha256:" + hashlib.sha256(blob).hexdigest()) if blob else None,
            "locator": {"method": "record_pointer", "source_field": "record",
                        "pointer": "/figures/%d/name" % (n - 1), "quote": name,
                        # `unique` is one strict definition for every asset: does this exact
                        # string occur once in the markdown?  A figure name also occurs inside
                        # its artifact path, so this is usually false; record-level uniqueness
                        # (one figures[] entry per name) is carried separately.
                        "unique": md.count(name) == 1 if name else False,
                        "record_unique": sum(1 for f in (record.get("figures") or [])
                                             if f.get("name") == name) == 1,
                        "markdown_name_occurrences": md.count(name) if name else 0,
                        "markdown_image_line": img_hits[0]["start_line"] if img_hits else None},
            "resolution": (
                {"status": "resolved", "scope": "platform_api",
                 "via": "GET /tensor/reports/9656 figures[%d].png_base64" % (n - 1),
                 "has_payload": True} if blob else
                {"status": "metadata_only", "scope": "platform_api",
                 "via": "GET /tensor/reports/9656 figures[%d]" % (n - 1),
                 "has_payload": False,
                 "reason": "record lists name+caption only; png_base64 is empty, so no image "
                           "bytes exist to hash or resolve in this record"}
            ),
        })

    # An+1..: every path-like reference parsed from the markdown body
    refs = scan_references(md)
    for n, ref in enumerate(refs, start=1):
        res = resolve_local(ref["path"])
        add({
            "asset_id": "r9656:ref:%02d" % n,
            "kind": kind_of(ref["path"]),
            "path_reference": ref["path"],
            "via": ref["via"],
            "markdown_alt": ref["alt"],
            "locator": {"method": "char_span", "source_field": SOURCE_FIELD,
                        "start_char": ref["start_char"], "end_char": ref["end_char"],
                        "start_line": ref["start_line"], "end_line": ref["start_line"],
                        "quote": ref["quote"], "unique": md.count(ref["quote"]) == 1,
                        "line_quote": ref["line_quote"],
                        "line_occurrences": md.count(ref["line_quote"])},
            "resolution": {**res, "external_probe": resolve_external(ref["path"])},
        })

    # inventory of tables / sections (registration, not extraction)
    tables = scan_tables(md)
    sections = scan_sections(md)

    # finalize integrity BEFORE the envelope exists, so kf_result always embeds the
    # committed manifest byte-for-byte (no post-hoc mutation of the manifest)
    _checked, _bad = check_locators(assets, tables, sections, md, record)
    if _bad:
        raise SystemExit("locator check failed at build time: %s" % _bad[:3])

    hist: dict[str, int] = {}
    for a in assets:
        k = "%s/%s" % (a["kind"], a["resolution"]["status"])
        hist[k] = hist.get(k, 0) + 1

    distinct_paths = sorted({r["path"] for r in refs})
    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "B",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "producer": PRODUCER,
        "contract_version": "1.0",
        "schema_ref": str(LOCAL_SCHEMA.relative_to(ROOT)),
        "source": {
            "uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "source_hash": digest,
            "hash_scope": "sha256 over UTF-8 bytes of the markdown field",
            "chars": len(md),
            "bytes_utf8": len(raw),
            "lines": len(md_lines),
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "report_mission_id": record.get("mission_id"),
            "report_status": record.get("status"),
            "report_stage": record.get("stage"),
            "platform_tags": record.get("tags") or [],
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "contract_chars": CONTRACT_CHARS,
            "contract_title": CONTRACT_TITLE,
            "contract_scenario_key": CONTRACT_SCENARIO,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
            "title_matches_contract": (record.get("title") or "") == CONTRACT_TITLE,
            "scenario_matches_contract": (record.get("scenario_key") or "") == CONTRACT_SCENARIO,
        },
        "assets": assets,
        "tables": tables,
        "sections": sections,
        "claims": [],
        "claims_empty_reason": (
            "contract objective is register_assets only (classify_report_type=false, no extraction); "
            "emitting zero claims is the complete, non-invented result for task_type 01"
        ),
        "counts": {
            "assets_total": len(assets),
            "assets_resolved": sum(1 for a in assets if a["resolution"]["status"] == "resolved"),
            "assets_metadata_only": sum(1 for a in assets if a["resolution"]["status"] == "metadata_only"),
            "assets_unresolved": sum(1 for a in assets if a["resolution"]["status"] == "unresolved"),
            "body_references": len(refs),
            "distinct_referenced_paths": len(distinct_paths),
            "declared_figures_in_record": len(record.get("figures") or []),
            "figures_with_bytes": sum(1 for a in assets
                                      if a["kind"] == "embedded_figure"
                                      and a["resolution"]["status"] == "resolved"),
            "tables": len(tables),
            "table_rows": sum(t["rows"] for t in tables),
            "sections": len(sections),
            "claims": 0,
            "kind_status_histogram": hist,
        },
        "distinct_referenced_paths": distinct_paths,
        "platform_probes": probe_platform_artifacts(token),
        "observations": [
            "All %d body path references point at artifacts/ and backend/ of the producing "
            "repository (ship-performance-platform), which is not a checkout in this "
            "TensorKnowledge worktree -- hence unresolved here, by design, not a defect." % len(refs),
            "The report record carries %d figures by name+caption only (png_base64 empty); "
            "image bytes are therefore not hashable from the record."
            % len(record.get("figures") or []),
            "Locator quotes are exact character slices of the served markdown; the full "
            "line is stored alongside as line_quote for human re-checking.",
        ],
        "limitations": [
            "Registration only: no claim is extracted, classified, or marked verified.",
            "Artifact existence is asserted by the report text; this package does not "
            "confirm the referenced files exist upstream (no cross-repo read).",
            "Uniqueness of a quote is a property of this document only; short path "
            "strings that recur are flagged with unique=false and line_occurrences>1.",
        ],
        "integrity": {
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "locators_checked": _checked,
            "locators_resolved": _checked - len(_bad),
            "quote_uniqueness": quote_uniqueness_text(assets, md),
            "duplicate_asset_ids": 0,
        },
    }
    return manifest


# ---------------------------------------------------------------- envelope
def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mraw = MANIFEST.read_bytes()
    # bind envelope to freshly re-read live bytes, not to the contract constant
    record = fetch_record()
    md = record["markdown"]
    live = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    if live != manifest["source"]["source_hash"]:
        raise SystemExit("live source drifted from manifest: %s != %s"
                         % (live, manifest["source"]["source_hash"]))
    if live != CONTRACT_SOURCE_HASH:
        raise SystemExit("live source drifted from contract: %s != %s" % (live, CONTRACT_SOURCE_HASH))
    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": live,
            "hash_algo": "sha256",
            "hash_scope": "UTF-8 bytes of the markdown field as served by GET /api/v1/tensor/reports/9656",
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "source_lines": len(md.split("\n")),
            "fetched_via": "GET /api/v1/tensor/reports/9656",
            "producer": PRODUCER,
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "contract_version": "1.0",
            "notes": "source_hash recomputed from the live markdown bytes and equals the contract "
                     "value %s" % CONTRACT_SOURCE_HASH,
        },
        "outputs": {
            "asset_manifest.json": manifest,
            "asset_manifest.digest.json": {
                "path": str(MANIFEST.relative_to(ROOT)),
                "sha256": "sha256:" + hashlib.sha256(mraw).hexdigest(),
                "bytes": len(mraw),
                "asset_count": manifest["counts"]["assets_total"],
                "claims": len(manifest["claims"]),
            },
        },
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return envelope


# ---------------------------------------------------------------- verify
def verify() -> dict:
    checks: dict[str, dict] = {}

    # 1. valid_json
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
        checks["valid_json"] = {"ok": True, "detail": "both asset_manifest.json and kf_result.json parse"}
    except Exception as e:  # noqa: BLE001
        return {"all_ok": False, "acceptance": {"valid_json": {"ok": False, "detail": str(e)}}}

    # 2. schema_pass (local instantiation of asset_manifest.v1; platform gate wins if different)
    try:
        import jsonschema  # type: ignore
        schema = json.loads(LOCAL_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)
        kf_schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(envelope, kf_schema)
        checks["schema_pass"] = {"ok": True,
                                 "detail": "asset_manifest vs %s; kf_result vs schemas/kf_result.v1.schema.json"
                                           % LOCAL_SCHEMA.relative_to(ROOT)}
    except ImportError:
        need = ["manifest_version", "package_id", "task_type", "report_id", "source", "assets",
                "claims", "counts", "integrity"]
        ok = all(k in manifest for k in need) and all(
            {"asset_id", "kind", "locator", "resolution"} <= set(a) for a in manifest["assets"])
        checks["schema_pass"] = {"ok": ok, "detail": "jsonschema unavailable; structural fallback only"}
    except Exception as e:  # noqa: BLE001
        checks["schema_pass"] = {"ok": False, "detail": "%s: %s" % (type(e).__name__, str(e)[:400])}

    # 3+4. locators resolvable against freshly fetched bytes; hash matches contract
    record = fetch_record()
    md = record["markdown"]
    live = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    checks["source_hash_matches"] = {
        "ok": live == CONTRACT_SOURCE_HASH and manifest["source"]["source_hash"] == CONTRACT_SOURCE_HASH
              and envelope["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH,
        "detail": "live=%s contract=%s chars=%d (contract %d)"
                  % (live, CONTRACT_SOURCE_HASH, len(md), CONTRACT_CHARS),
    }

    checked, bad = check_locators(manifest["assets"], manifest["tables"], manifest["sections"],
                                  md, record)
    checks["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": "%d locators re-checked against live markdown (%d assets, %d tables, %d sections)"
                  % (checked, len(manifest["assets"]), len(manifest["tables"]), len(manifest["sections"])),
        "failures": bad[:10],
    }

    # 5. no duplicate ids
    aids = [a["asset_id"] for a in manifest["assets"]]
    dup = sorted({x for x in aids if aids.count(x) > 1})
    checks["no_duplicate_ids"] = {"ok": not dup, "detail": "%d asset ids, duplicates=%s"
                                                          % (len(aids), dup or "none")}

    # 6. every claim has evidence or explicit unresolved status (vacuously true for 0 claims)
    claims = manifest["claims"] + envelope.get("claims", [])
    unbacked = [c.get("claim_id") for c in claims
                if not c.get("evidence") and not c.get("status")]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": not unbacked,
        "detail": "%d claims (empty by contract: objective.register_assets only, no extraction); "
                  "unbacked=%s" % (len(claims), unbacked or "none"),
    }

    # accounting re-measured here (not copied from build)
    uniq = sum(1 for a in manifest["assets"] if a["locator"].get("unique"))
    rec = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "verifier": "scripts/kf/wp9656_01_register.py verify",
        "independence_limitation": ("self-check by the producing script: it re-fetches the source and "
                                    "re-derives every comparison, but shares code with build(); platform "
                                    "gate recomputation remains the authoritative check"),
        "all_ok": all(c["ok"] for c in checks.values()),
        "acceptance": checks,
        "accounting": {
            "locators_checked": checked,
            "locators_resolved": checked - len(bad),
            "quotes_unique": uniq,
            "quotes_not_unique": len(manifest["assets"]) - uniq,
            "distinct_quotes": len({a["locator"].get("quote") for a in manifest["assets"]}),
            "assets_total": len(manifest["assets"]),
            "assets_resolved": manifest["counts"]["assets_resolved"],
            "assets_metadata_only": manifest["counts"]["assets_metadata_only"],
            "assets_unresolved": manifest["counts"]["assets_unresolved"],
        },
    }
    # internal consistency: the manifest is NOT rewritten here (rewriting after the envelope
    # was built would leave kf_result embedding a stale manifest); mismatches are reported.
    integ = manifest["integrity"]
    expected_digest = envelope["outputs"]["asset_manifest.digest.json"]["sha256"]
    actual_digest = "sha256:" + hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    internal = {
        "integrity_locators_checked_matches": integ["locators_checked"] == checked,
        "integrity_locators_resolved_matches": integ["locators_resolved"] == checked - len(bad),
        "integrity_quote_uniqueness_matches": integ["quote_uniqueness"] == quote_uniqueness_text(
            manifest["assets"], md),
        "integrity_duplicate_ids_matches": integ["duplicate_asset_ids"] == len(dup),
        "envelope_digest_matches_manifest_file": expected_digest == actual_digest,
        "envelope_embeds_manifest_file": envelope["outputs"]["asset_manifest.json"] == manifest,
    }
    rec["internal_consistency"] = {
        "ok": all(internal.values()),
        "detail": internal,
        "expected_manifest_sha256": expected_digest,
        "actual_manifest_sha256": actual_digest,
    }
    rec["all_ok"] = rec["all_ok"] and rec["internal_consistency"]["ok"]
    VERIFICATION.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rec


# ---------------------------------------------------------------- figure
def figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = SOURCE_COPY.read_text(encoding="utf-8")
    lines = md.split("\n")
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.2),
                                   gridspec_kw={"height_ratios": [2, 1]})
    kind_color = {"report_markdown": "#4c72b0", "embedded_figure": "#9467bd",
                  "figure_reference": "#dd8452", "data_artifact_reference": "#55a868",
                  "source_code_reference": "#c44e52", "document_reference": "#8c8c8c",
                  "directory_reference": "#8172b3"}
    ax1.plot(range(1, len(lines) + 1), [len(x) for x in lines], color="0.72", lw=0.8,
             label="line length (chars)")
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc.get("method") != "char_span":
            continue
        ax1.axvline(loc["start_line"], color=kind_color.get(a["kind"], "k"), lw=1.6, alpha=0.85)
    for t in manifest["tables"]:
        ax1.axvspan(t["line_start"], t["line_end"], color="#f0c419", alpha=0.18, lw=0)
    handles = [plt.Line2D([], [], color=v, lw=2, label=k) for k, v in kind_color.items()
               if any(a["kind"] == k for a in manifest["assets"])]
    handles.append(plt.Rectangle((0, 0), 1, 1, color="#f0c419", alpha=0.4, label="table span"))
    ax1.legend(handles=handles, fontsize=7, loc="upper right", ncol=2)
    ax1.set_xlim(1, len(lines))
    ax1.set_ylabel("line length (chars)")
    ax1.set_title("report 9656 source registration: %d locators over %d lines / %d chars\n"
                  "sha256 %s…  (contract match: hash=%s chars=%s)"
                  % (manifest["counts"]["assets_total"], len(lines), manifest["source"]["chars"],
                     manifest["source"]["source_hash"][7:27],
                     manifest["source"]["hash_matches_contract"],
                     manifest["source"]["chars_matches_contract"]), fontsize=10)
    ax1.grid(alpha=0.25)

    h = manifest["counts"]["kind_status_histogram"]
    labels = sorted(h)
    colors = ["#55a868" if k.endswith("resolved") else
              "#dd8452" if k.endswith("metadata_only") else "#c44e52" for k in labels]
    ax2.barh(range(len(labels)), [h[k] for k in labels], color=colors)
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels(labels, fontsize=7)
    ax2.invert_yaxis()
    for i, k in enumerate(labels):
        ax2.text(h[k] + 0.05, i, str(h[k]), va="center", fontsize=7)
    ax2.set_xlabel("assets")
    ax2.set_title("asset kind / resolution status (green=resolved, orange=metadata_only, red=unresolved)",
                  fontsize=9)
    ax2.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    out = FIG_DIR / "wp9656_01_source_locator_map.png"
    fig.savefig(out, dpi=170)
    print("figure ->", out.relative_to(ROOT))


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if cmd in ("build", "all"):
        token = login()
        record = fetch_record(token)
        manifest = build_manifest(record, token)
        if not manifest["source"]["hash_matches_contract"]:
            raise SystemExit("SOURCE HASH MISMATCH: contract=%s actual=%s"
                             % (CONTRACT_SOURCE_HASH, manifest["source"]["source_hash"]))
        if not manifest["source"]["chars_matches_contract"]:
            raise SystemExit("SOURCE CHARS MISMATCH: contract=%d actual=%d"
                             % (CONTRACT_CHARS, manifest["source"]["chars"]))
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print("manifest ->", MANIFEST.relative_to(ROOT),
              "| assets", manifest["counts"]["assets_total"],
              "| resolved", manifest["counts"]["assets_resolved"],
              "| unresolved", manifest["counts"]["assets_unresolved"])
    if cmd in ("envelope", "all"):
        env = build_envelope()
        print("envelope ->", ENVELOPE.relative_to(ROOT), "|", env["provenance"]["source_hash"])
    if cmd in ("verify", "all"):
        v = verify()
        print("verify ->", VERIFICATION.relative_to(ROOT), "| all_ok", v["all_ok"])
        for k, c in v["acceptance"].items():
            print("   [%s] %s" % ("PASS" if c["ok"] else "FAIL", k))
    if cmd in ("figure", "all"):
        figure()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))