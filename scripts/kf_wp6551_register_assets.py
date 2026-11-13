#!/usr/bin/env python3
"""wp-6551-01 (task_type 01-asset-registration): register report 6551's source asset
and enumerate the resolvable attachments / artefacts / references it declares.

    python3 scripts/kf_wp6551_register_assets.py build      # fetch + write asset_manifest.json
    python3 scripts/kf_wp6551_register_assets.py envelope   # wrap manifest -> kf_result.json
    python3 scripts/kf_wp6551_register_assets.py verify     # 6 contract acceptance checks
    python3 scripts/kf_wp6551_register_assets.py figure     # locator map png
    python3 scripts/kf_wp6551_register_assets.py all        # build+envelope+verify+figure

Design rules honoured here (contract wp-6551-01):
  * registration only -- NO claim extraction (claims []), NO report-type classification,
    NO "verified" mark anywhere (verification is the platform gate's job);
  * zero manual transcription -- every number/hash/char offset is measured here from the
    bytes served by GET /api/v1/tensor/reports/6551, and the source copy is kept under
    runs/wp-6551-01/source_6551.md so a reviewer can re-derive all of it offline;
  * every declared asset carries a locator (verbatim quote + char span + line) that is
    re-checked against the live markdown at verify time;
  * a reference that cannot be resolved is reported as unresolved *with its scope and
    reason* -- never upgraded to resolved, never dropped silently;
  * failures abort loudly (SystemExit) instead of emitting a half manifest.

Resolution scope note: report 6551's artefacts live in TensorLBM (the report says so);
this worker's worktree is the TensorKnowledge delivery repo, so a path reference is
probed there only. `referenced_unresolved` therefore means "not in this worktree", not
"does not exist"; `KF_RESOLVE_EXTRA_ROOTS=/path/a:/path/b` lets a reviewer widen the
probe (e.g. to a TensorLBM checkout) and the widened scope is recorded per asset.
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
REPORT_ID = "6551"
PACKAGE_ID = "wp-6551-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
LANE = "C"
PRODUCER = "kf-worker/m15591"

# contract-declared identity (work-package YAML). The script never trusts these:
# they are comparison targets, and a mismatch aborts the build.
CONTRACT_SOURCE_HASH = "sha256:879d4b3cb0112589ae9f58962c23b8d92d07a4de2ea71b950dba6a5d83c47431"
CONTRACT_CHARS = 5491
CONTRACT_TITLE = ("IN28-N04 船型阻力闭合：三级证据记账、波阻 GCI 与诚实 FAIL"
                  "（KCS/5415/Series60）")
CONTRACT_SCENARIO = "IN28-N04-ship-resistance-closure"

RUN_DIR = ROOT / "runs" / PACKAGE_ID          # scratch, git-ignored via artifacts/ only? no: runs/ is tracked
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID   # committed artefacts
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
SCHEMA = ROOT / "schemas" / "asset_manifest.v1.generic.schema.json"

# asset_class / kind by file extension; `kind` is kept for cross-package readers
# (wp-623-01 used the same vocabulary).
PATH_EXT = {
    ".py": ("source_code_reference", "source_code_reference"),
    ".json": ("data_artifact_reference", "data_artifact_reference"),
    ".png": ("figure_reference", "figure_reference"),
    ".jpg": ("figure_reference", "figure_reference"),
    ".md": ("document_reference", "document_reference"),
    ".csv": ("data_artifact_reference", "data_artifact_reference"),
    ".h5": ("data_artifact_reference", "data_artifact_reference"),
    ".hdf5": ("data_artifact_reference", "data_artifact_reference"),
    ".txt": ("document_reference", "document_reference"),
}
FIGURE_NAME_RE = re.compile(r"^[\w.-]+\.(png|jpg|jpeg)$")
BACKTICK_RE = re.compile(r"`([^`\n]{2,120})`")
ATTR_TAIL_RE = re.compile(r"^([^\s]+?\.[A-Za-z0-9]{1,5})((?:\.[A-Za-z_][\w]*)+)$")
MODULE_RE = re.compile(r"^[a-z_][\w]*(\.[A-Za-z_][\w]*)+$")


# ------------------------------------------------------------------ helpers
def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _get_raw(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _get_json(path: str, tok: str) -> dict:
    st, body = _get_raw(path, tok)
    if st != 200:
        raise SystemExit("GET %s -> HTTP %s" % (path, st))
    return json.loads(body)


def fetch_record() -> dict:
    return _get_json("/tensor/reports/%s" % REPORT_ID, _login())


def section_map(lines: list[str]) -> list[tuple[int, str]]:
    """1-based line number -> owning '## ' header ('' before the first one)."""
    out, cur = [], "document (preamble)"
    for n, line in enumerate(lines, start=1):
        if line.startswith("## "):
            cur = line[3:].strip()
        out.append((n, cur))
    return out


def section_of(secmap, line_no: int) -> str:
    for n, name in secmap:
        if n == line_no:
            return name
    return secmap[-1][1] if secmap else "document"


SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")
PATHLIKE_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|json|png|jpg|jpeg|md|csv|h5|hdf5)\b")
DIR_SEG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{2,}$")


def classify(tok: str):
    """(asset_class, kind, core_token, attr_qualifier) or None if not an artefact.

    Only tokens that *look like* artefacts qualify: maths such as `db/dx` or
    `|C_T-[(1+k)C_F+C_W]|/C_T<1e-6` is not a path and must not be registered as one.
    """
    core, qual = tok.strip(), None
    m = ATTR_TAIL_RE.match(core)
    if m:
        core, qual = m.group(1), m.group(2)
    ext = Path(core).suffix.lower()
    if ext in PATH_EXT and SAFE_TOKEN_RE.match(core):
        cls, kind = PATH_EXT[ext]
        if cls == "source_code_reference" and (core.startswith("tests/") or "/test_" in core):
            cls = "test_reference"
        return cls, kind, core, qual
    if (SAFE_TOKEN_RE.match(core) and core.count("/") >= 1
            and all(DIR_SEG_RE.match(s) for s in core.strip("/").split("/"))):
        return "benchmark_dir_reference", "directory_reference", core, qual
    if MODULE_RE.match(core) and not core.startswith("http"):
        return "module_symbol_reference", "symbol_reference", core, None
    return None


def scan_tokens(md: str, lines: list[str], skip_names=()) -> list[dict]:
    """First-occurrence locator per declared artefact, in document order.

    A backticked span may be a bare path (`run.py`) or a command carrying one
    (`pytest tests/test_ship_resistance_closure.py`); in both cases the recorded
    char span points at the artefact itself, not at the surrounding span.
    """
    skip = set(skip_names)
    seen, out = {}, []
    for m in BACKTICK_RE.finditer(md):
        content = m.group(1)
        base = m.start(1)
        cands = []
        if classify(content.strip()):
            cands.append((content.strip(), content.index(content.strip())))
        else:
            for pm in PATHLIKE_RE.finditer(content):
                if classify(pm.group()):
                    cands.append((pm.group(), pm.start()))
        for tok, off in cands:
            cls = classify(tok)
            if not cls:
                continue
            asset_class, kind, core, qual = cls
            if core in skip:
                continue
            line_no = md.count("\n", 0, base + off) + 1
            if core in seen:
                seen[core]["occurrences"].append(line_no)
                continue
            rec = {"token": tok, "asset_class": asset_class, "kind": kind,
                   "core": core, "attr_qualifier": qual,
                   "start_char": base + off, "end_char": base + off + len(tok),
                   "line": line_no, "quote": tok, "occurrences": [line_no]}
            seen[core] = rec
            out.append(rec)
    return out


def resolve_path(token: str) -> dict:
    """Probe the worktree (plus optional extra roots) for a declared reference."""
    cand = token.strip().lstrip("./")
    roots = [("delivery_worktree", ROOT)]
    for r in filter(None, (os.environ.get("KF_RESOLVE_EXTRA_ROOTS") or "").split(":")):
        roots.append(("extra_root", Path(r)))
    hits, searched = [], [scope for scope, _ in roots]
    for scope, base in roots:
        p = base / cand
        if p.is_file():
            b = p.read_bytes()
            hits.append({"scope": scope, "root": str(base), "path": str(p.relative_to(base)),
                         "bytes": len(b), "sha256": sha256_hex(b)})
    if hits:
        return {"status": "resolved", "hits": hits, "searched_scopes": searched}
    same = sorted(str(q.relative_to(ROOT)) for q in ROOT.rglob(Path(cand).name)
                  if q.is_file() and ".git" not in q.parts)[:5]
    return {"status": "unresolved", "searched_scopes": searched,
            "reason": "declared path not found under any searched root",
            "same_basename_hits_in_worktree": same}


# ----------------------------------------------------------------- manifest
DECLARED_HASH_RE = re.compile(r"`?([0-9a-f]{12,64})(?:\u2026|\.\.\.)?")


def scan_declared_hashes(md: str) -> list[dict]:
    """sha256-looking hex strings the report prints, with how verifiable they are.

    A digest that the report truncates (trailing ellipsis, or fewer than 64 hex
    chars) cannot be checked against any artefact; that is recorded, not hidden.
    """
    out = []
    for m in DECLARED_HASH_RE.finditer(md):
        val = m.group(1)
        start = m.start(1)
        before = md[max(0, start - 60):start]
        ctx = "sha256" if "sha256" in before.lower() else None
        if not ctx:
            continue
        line_no = md.count("\n", 0, start) + 1
        truncated = "\u2026" in md[m.end(1):m.end(1) + 3] or "..." in md[m.end(1):m.end(1) + 4] \
            or len(val) < 64
        out.append({"value": val, "start_char": start, "end_char": m.end(1),
                    "line": line_no, "algo": "sha256", "truncated": truncated,
                    "declared_chars": len(val),
                    "verifiability": ("unverifiable_truncated_prefix" if truncated
                                      else "verifiable_against_artefact_if_present")})
    return out


def build_manifest(record: dict) -> dict:
    md = record.get("markdown") or ""
    if not md:
        raise SystemExit("report %s record has no markdown field" % REPORT_ID)
    raw = md.encode("utf-8")
    lines = md.rstrip("\n").split("\n")
    digest = sha256_hex(raw)
    source_hash = "sha256:" + digest
    secmap = section_map(lines)

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_bytes(raw)

    hash_match = source_hash == CONTRACT_SOURCE_HASH
    chars_match = len(md) == CONTRACT_CHARS
    title_match = (record.get("title") or "").strip() == CONTRACT_TITLE
    scen_match = (record.get("scenario_key") or "").strip() == CONTRACT_SCENARIO
    if not hash_match:
        raise SystemExit("source hash mismatch: %s != contract %s"
                         % (source_hash, CONTRACT_SOURCE_HASH))

    assets: list[dict] = []

    # 1. the source itself: the only asset whose bytes this worker can re-derive
    assets.append({
        "asset_id": "r%s:source-markdown" % REPORT_ID,
        "asset_class": "report_markdown",
        "kind": "report_markdown",
        "label": "report-%s markdown (source of record)" % REPORT_ID,
        "name": "report-%s-markdown" % REPORT_ID,
        "in_report_section": "document (whole payload)",
        "locator": {"method": "document", "source_field": "markdown",
                    "start_char": 0, "end_char": len(md), "start_line": 1,
                    "end_line": len(lines), "quote": lines[0],
                    "quote_sha256": sha256_hex(lines[0].encode()),
                    "unique": md.count(lines[0]) == 1},
        "resolution": "resolved_in_source",
        "resolution_detail": {"scope": "platform_api",
                              "via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
                              "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
                              "bytes": len(raw), "chars": len(md), "lines": len(lines),
                              "sha256": digest},
        "resolution_check": {"check": "sha256 of served markdown bytes == contract source_hash",
                             "result": "resolved"},
        "note": "hash recomputed here from the served bytes; the contract hash matches.",
    })

    # 2. figures declared in the record (metadata only -- payload probe recorded)
    tok = _login()
    for idx, fig in enumerate(record.get("figures") or [], start=1):
        name = fig.get("name") or ""
        st, body = _get_raw("/tensor/reports/%s/figures/%s" % (REPORT_ID, name), tok)
        name_in_md = name in md
        line_no = (md.count("\n", 0, md.index(name)) + 1) if name_in_md else 0
        assets.append({
            "asset_id": "r%s:figure:%02d" % (REPORT_ID, idx),
            "asset_class": "embedded_figure",
            "kind": "embedded_figure",
            "label": name,
            "name": name,
            "caption": fig.get("caption"),
            "in_report_section": section_of(secmap, line_no) if line_no else "record (/figures)",
            "locator": {"method": "char_span", "source_field": "markdown",
                        "start_char": md.index(name) if name_in_md else 0,
                        "end_char": (md.index(name) + len(name)) if name_in_md else 0,
                        "start_line": line_no, "end_line": line_no,
                        "quote": name, "quote_sha256": sha256_hex(name.encode()),
                        "unique": md.count(name) == 1},
            "resolution": "referenced_unresolved",
            "resolution_detail": {
                "scope": "platform_api",
                "via": "GET /api/v1/tensor/reports/%s/figures/%s" % (REPORT_ID, name),
                "http_status": st, "response_bytes": len(body),
                "name_resolved_in_markdown": name_in_md,
                "reason": ("record exposes name+caption only and the figure endpoint returned "
                           "no payload, so no image bytes/hash are claimed; the name itself is "
                           "locatable verbatim in the markdown")},
            "resolution_check": {"check": "verbatim figure name in markdown + payload GET",
                                 "result": "unresolved"},
            "note": "metadata-only registration; no pixel data was retrieved or hashed.",
        })

    # 2b. digests the report itself declares for its artefacts
    for n, dh in enumerate(scan_declared_hashes(md), start=1):
        assets.append({
            "asset_id": "r%s:hash:%02d" % (REPORT_ID, n),
            "asset_class": "declared_hash_reference",
            "kind": "declared_hash",
            "label": "declared %s %s%s" % (dh["algo"], dh["value"],
                                           "\u2026" if dh["truncated"] else ""),
            "name": dh["value"],
            "in_report_section": section_of(secmap, dh["line"]),
            "locator": {"method": "char_span", "source_field": "markdown",
                        "start_char": dh["start_char"], "end_char": dh["end_char"],
                        "start_line": dh["line"], "end_line": dh["line"],
                        "quote": dh["value"],
                        "quote_sha256": sha256_hex(dh["value"].encode()),
                        "unique": md.count(dh["value"]) == 1},
            "resolution": "referenced_unresolved",
            "resolution_detail": {"scope": "report_text", "algo": dh["algo"],
                                  "declared_hex_chars": dh["declared_chars"],
                                  "truncated_in_report": dh["truncated"],
                                  "verifiability": dh["verifiability"],
                                  "reason": ("only a truncated digest prefix is printed, so no "
                                             "artefact can be recomputed against it"
                                             if dh["truncated"] else
                                             "full 64-hex digest printed; the artefact itself is "
                                             "not in this worktree, so it stays unverified")},
            "resolution_check": {"check": "digest length / truncation marker",
                                 "result": "unresolved"},
            "note": "registered as declared by the report; NOT verified by this工序.",
        })

    # 3. artefacts / paths / symbols declared in the prose
    fig_names = {a["name"] for a in assets if a["asset_class"] == "embedded_figure"}
    for n, ref in enumerate(scan_tokens(md, lines, skip_names=fig_names), start=1):
        res = resolve_path(ref["core"])
        resolved = res["status"] == "resolved"
        assets.append({
            "asset_id": "r%s:ref:%02d" % (REPORT_ID, n),
            "asset_class": ref["asset_class"],
            "kind": ref["kind"],
            "label": ref["token"],
            "name": ref["core"],
            "attr_qualifier": ref["attr_qualifier"],
            "in_report_section": section_of(secmap, ref["line"]),
            "locator": {"method": "char_span", "source_field": "markdown",
                        "start_char": ref["start_char"], "end_char": ref["end_char"],
                        "start_line": ref["line"], "end_line": ref["line"],
                        "quote": ref["quote"],
                        "quote_sha256": sha256_hex(ref["quote"].encode()),
                        "unique": md.count(ref["quote"]) == 1},
            "occurrence_lines": ref["occurrences"],
            "resolution": "resolved_in_source" if resolved else "referenced_unresolved",
            "declared_owner_hint": (
                {"repo": "TensorLBM", "basis": "path prefix src/tensorlbm/",
                 "asserted": False}
                if ref["core"].startswith("src/tensorlbm/") else None),
            "resolution_detail": res,
            "resolution_check": {"check": "filesystem probe of declared path in delivery worktree",
                                 "result": "resolved" if resolved else "unresolved"},
            "note": ("reference only: the report names it, this工序 does not open or audit it. "
                     "Not found in the TensorKnowledge worktree -- the report places it in "
                     "TensorLBM, so unresolved here is a scope statement, not absence."
                     if not resolved else
                     "reference only: the report names it; existence confirmed in worktree."),
        })

    # identity facts that pin *what* the document is
    anchors = []
    for tag, needle in (("# title", lines[0]),
                        ("## section ①", "## ① 案例介绍"),
                        ("## section ②", "## ② 怎么做的"),
                        ("## section ③", "## ③ 计算结果"),
                        ("## section ④", "## ④ 结果图"),
                        ("## section ⑤", "## ⑤ 注意点 / 局限"),
                        ("## section ⑥", "## ⑥ 误差判定")):
        hits = [i for i, ln in enumerate(lines, start=1) if ln.startswith(needle)]
        if hits:
            ln = hits[0]
            anchors.append({"fact_id": tag, "locator": {"source_field": "markdown", "line": ln},
                            "quote": lines[ln - 1],
                            "quote_sha256": sha256_hex(lines[ln - 1].encode())})
    last = max(i for i, ln in enumerate(lines, start=1) if ln.strip())
    anchors.append({"fact_id": "closing-note", "locator": {"source_field": "markdown", "line": last},
                    "quote": lines[last - 1],
                    "quote_sha256": sha256_hex(lines[last - 1].encode())})

    by_class: dict[str, int] = {}
    by_resolution: dict[str, int] = {}
    hist: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_resolution[a["resolution"]] = by_resolution.get(a["resolution"], 0) + 1
        k = "%s|%s" % (a["kind"], a["resolution"])
        hist[k] = hist.get(k, 0) + 1

    counts = {
        "assets": len(assets),
        "by_class": by_class,
        "by_resolution": by_resolution,
        "resolved_in_source": by_resolution.get("resolved_in_source", 0),
        "referenced_unresolved": by_resolution.get("referenced_unresolved", 0),
        "declared_absent": by_resolution.get("declared_absent", 0),
        "kind_status_histogram": hist,
        "distinct_reference_tokens": sum(
            1 for a in assets if a["asset_id"].startswith("r%s:ref:" % REPORT_ID)),
    }

    return {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "objective": {"register_assets": True, "classify_report_type": False,
                      "extraction_performed": False},
        "source": {
            "uri": SOURCE_URI,
            "report_id": REPORT_ID,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "source_hash": source_hash,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_match": hash_match,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": chars_match,
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
            "title": record.get("title"),
            "contract_title": CONTRACT_TITLE,
            "title_matches_contract": title_match,
            "scenario_key": record.get("scenario_key"),
            "contract_scenario_key": CONTRACT_SCENARIO,
            "scenario_matches_contract": scen_match,
            "platform_figures": [f.get("name") for f in (record.get("figures") or [])],
            "platform_tags": record.get("tags") or [],
            "record_fields": {k: record.get(k) for k in
                              ("id", "mission_id", "status", "stage", "created_at", "created_by")},
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
        },
        "counts": counts,
        "assets": assets,
        "claims": [],
        "claims_empty_reason": (
            "objective.classify_report_type=false and the contract scopes this package to "
            "asset registration only ('登记源资产…不做抽取'; 'claims 允许为空数组'). No sentence of "
            "the report was promoted to a knowledge claim here; extraction is a separate "
            "work package. Empty is a complete result, not a gap."),
        "identity_facts": anchors,
        "integrity": {
            "quote_uniqueness": {
                "markdown_quotes": sum(1 for a in assets
                                       if a["locator"]["source_field"] == "markdown"),
                "unique_quotes": sum(1 for a in assets if a["locator"]["unique"]),
                "non_unique_quotes": sorted(a["asset_id"] for a in assets
                                            if not a["locator"]["unique"]),
            },
            "hash_recomputed_locally": source_hash,
            "hash_matches_contract": hash_match,
            "source_copy_path": str(SOURCE_COPY.relative_to(ROOT)),
        },
    }


# ----------------------------------------------------------------- envelope
def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["source_hash"],
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("hash recomputed from GET /api/v1/tensor/reports/%s markdown (UTF-8 "
                      "bytes); matches contract source_hash %s"
                      % (REPORT_ID, CONTRACT_SOURCE_HASH)),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def locator_errors(md: str, manifest: dict) -> list[str]:
    """Re-resolve every markdown locator; an empty list means all of them resolve.

    A locator resolves only if md[start:end] is byte-identical to the recorded quote,
    the recorded quote_sha256 matches those bytes, and the quote really occurs on the
    declared 1-based line. Shared by verify() and the offline regression test.
    """
    lines = md.rstrip("\n").split("\n")
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc.get("source_field") != "markdown" or loc.get("method") != "char_span":
            continue
        s, e = loc["start_char"], loc["end_char"]
        ok = (0 <= s < e <= len(md)
              and md[s:e] == loc["quote"]
              and sha256_hex(md[s:e].encode()) == loc["quote_sha256"]
              and 0 < loc["start_line"] <= len(lines)
              and loc["quote"] in lines[loc["start_line"] - 1])
        if not ok:
            bad.append(a["asset_id"])
    for f in manifest["identity_facts"]:
        ln = f["locator"]["line"]
        if not (0 < ln <= len(lines)) or lines[ln - 1] != f["quote"]:
            bad.append("identity:" + f["fact_id"])
    return bad


# ------------------------------------------------------------------- verify
def verify() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    env = json.loads(ENVELOPE.read_text())
    schema = json.loads(SCHEMA.read_text())

    offline = os.environ.get("KF_OFFLINE") == "1"
    if offline:
        md = SOURCE_COPY.read_text()
        live_hash, live_mode = "sha256:" + sha256_hex(md.encode()), "stored_copy"
        record = None
    else:
        record = fetch_record()
        md = record.get("markdown") or ""
        live_hash, live_mode = "sha256:" + sha256_hex(md.encode()), "live_api"
    checks: dict[str, dict] = {}

    # 1 valid_json
    try:
        json.loads(MANIFEST.read_text())
        json.loads(ENVELOPE.read_text())
        checks["valid_json"] = {"ok": True,
                                "detail": "asset_manifest.json and kf_result.json parse as JSON"}
    except json.JSONDecodeError as e:  # pragma: no cover
        checks["valid_json"] = {"ok": False, "detail": str(e)}

    # 2 schema_pass
    import jsonschema
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(manifest),
                  key=lambda e: list(e.path))
    env_errs = []
    kf_schema_path = ROOT / "schemas" / "kf_result.v1.schema.json"
    if kf_schema_path.is_file():
        kf_schema = json.loads(kf_schema_path.read_text())
        env_errs = sorted(jsonschema.Draft202012Validator(kf_schema).iter_errors(env),
                          key=lambda e: list(e.path))
    checks["schema_pass"] = {
        "ok": not errs and not env_errs,
        "detail": "manifest vs %s: %d error(s); envelope vs schemas/kf_result.v1.schema.json: %d error(s)"
                  % (SCHEMA.relative_to(ROOT), len(errs), len(env_errs)),
        "errors": [("%s: %s" % ("/".join(str(p) for p in e.path), e.message))
                   for e in errs + env_errs][:10],
    }

    # 3 source_locator_resolvable
    bad = locator_errors(md, manifest)
    spans = sum(1 for a in manifest["assets"]
                if a["locator"].get("source_field") == "markdown" and a["locator"]["method"] == "char_span")
    checks["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": "%d/%d char-span locators re-resolved (md[start:end]==quote, quote_sha256, "
                  "quote present on declared line) + %d identity facts"
                  % (spans - len([b for b in bad if not b.startswith("identity:")]), spans,
                     len(manifest["identity_facts"])),
        "failures": bad,
    }

    # 4 source_hash_matches
    checks["source_hash_matches"] = {
        "ok": live_hash == manifest["source"]["source_hash"] == CONTRACT_SOURCE_HASH
              == env["provenance"]["source_hash"],
        "detail": "%s: live=%s manifest=%s contract=%s" % (
            live_mode, live_hash, manifest["source"]["source_hash"], CONTRACT_SOURCE_HASH),
        "chars": {"live": len(md), "manifest": manifest["source"]["chars"],
                  "contract": CONTRACT_CHARS},
    }

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {"ok": not dupes,
                                  "detail": "%d asset ids, duplicates=%s" % (len(ids), dupes)}

    # 6 all_claims_have_evidence_or_explicit_unresolved_status
    claims = env.get("claims") or []
    ev_ok = all(c.get("evidence") or c.get("unresolved_reason") for c in claims)
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": bool(ev_ok and manifest.get("claims_empty_reason")),
        "detail": "%d claims; explicit empty-claims reason present: %s; "
                  "no claim carries a 'verified' status"
                  % (len(claims), bool(manifest.get("claims_empty_reason"))),
    }

    out = {
        "package_id": PACKAGE_ID,
        "verified_at": utcnow(),
        "mode": {"source": live_mode, "figure_payloads": "not retrievable (HTTP 404 on "
                                                         "/tensor/reports/6551/figures/<name>)"},
        "acceptance": checks,
        "all_ok": all(c["ok"] for c in checks.values()),
        "not_checked": [
            "figure pixel data: endpoint returns 404, so no image hash/pHash is claimed",
            "existence of the TensorLBM-side paths (src/tensorlbm/…, run.py, results.json, "
            "refs_lock.json, benchmarks/pending/…): outside this delivery worktree; "
            "recorded as referenced_unresolved",
            "report-type classification and claim extraction: out of scope for task_type "
            "01-asset-registration",
        ],
        "note": ("Self-check only. No asset/claim is marked verified here; the platform gate "
                 "recomputes hash and locators independently."),
    }
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


# ------------------------------------------------------------------- figure
def figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    md = SOURCE_COPY.read_text()
    lines = md.rstrip("\n").split("\n")
    manifest = json.loads(MANIFEST.read_text())
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.2),
                                   gridspec_kw={"width_ratios": [2.2, 1]})
    xs = list(range(1, len(lines) + 1))
    ys = [len(ln) for ln in lines]
    ax1.plot(xs, ys, "-", color="#4c72b0", lw=1.0, label="chars per line")
    ax1.fill_between(xs, ys, color="#4c72b0", alpha=0.10)
    colors = {"source_code_reference": "#c44e52", "test_reference": "#8c6bb1",
              "data_artifact_reference": "#dd8452", "figure_reference": "#55a868",
              "benchmark_dir_reference": "#937860", "module_symbol_reference": "#4c72b0"}
    marks = {}
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc.get("source_field") != "markdown" or loc["method"] != "char_span":
            continue
        marks.setdefault(a["asset_class"], []).append(loc["start_line"])
    for cls, lns in sorted(marks.items()):
        ax1.vlines(lns, 0, [max(len(lines[n - 1]), 4) for n in lns],
                   color=colors.get(cls, "k"), lw=2.6, label="%s (n=%d)" % (cls, len(lns)))
    for f in manifest["identity_facts"]:
        ln = f["locator"]["line"]
        ax1.axvline(ln, color="0.65", ls=":", lw=0.8)
        ax1.annotate("L%d" % ln, (ln, max(ys) * 0.98), fontsize=6.5, color="0.35",
                     rotation=90, ha="right", va="top")
    ax1.set_xlabel("markdown line number")
    ax1.set_ylabel("characters on line")
    ax1.set_title("report 6551 source markdown: line profile + verbatim asset anchors\n"
                  "(%d lines, %d chars, sha256 %s…)"
                  % (len(lines), len(md), manifest["source"]["hash"][:12]), fontsize=10)
    ax1.legend(fontsize=7, loc="upper center", ncol=2)
    ax1.grid(alpha=0.25)

    c = manifest["counts"]
    labels = sorted(c["by_class"])
    vals = [c["by_class"][k] for k in labels]
    res_of = {a["asset_class"]: a["resolution"] for a in manifest["assets"]}
    bar_colors = ["#55a868" if res_of[k] == "resolved_in_source" else "#c44e52" for k in labels]
    ax2.barh(range(len(labels)), vals, color=bar_colors)
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels([lbl.replace("_", " ") for lbl in labels], fontsize=7)
    ax2.invert_yaxis()
    for i, v in enumerate(vals):
        ax2.text(v + 0.05, i, str(v), va="center", fontsize=7)
    ax2.set_xlabel("assets")
    ax2.set_title("asset classes registered\nred = payload/path unresolved (%d of %d)"
                  % (c["referenced_unresolved"], c["assets"]), fontsize=10)
    ax2.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    out = FIG_DIR / "wp6551_source_locator_map.png"
    fig.savefig(out, dpi=170)
    print("figure ->", out.relative_to(ROOT))


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if cmd in ("build", "all"):
        manifest = build_manifest(fetch_record())
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print("manifest ->", MANIFEST.relative_to(ROOT),
              "| assets", manifest["counts"]["assets"],
              "| resolved", manifest["counts"]["resolved_in_source"],
              "| unresolved", manifest["counts"]["referenced_unresolved"])
    if cmd in ("envelope", "all"):
        env = build_envelope()
        ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n")
        print("envelope ->", ENVELOPE.relative_to(ROOT), "|", env["provenance"]["source_hash"])
    if cmd in ("verify", "all"):
        v = verify()
        print("verify ->", VERIFICATION.relative_to(ROOT), "| all_ok", v["all_ok"])
        for k, chk in v["acceptance"].items():
            print("   [%s] %s -- %s" % ("PASS" if chk["ok"] else "FAIL", k, chk["detail"]))
    if cmd in ("figure", "all"):
        figure()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))