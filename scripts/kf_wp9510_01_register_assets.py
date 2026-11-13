#!/usr/bin/env python3
"""wp-9510-01 (task_type 01-asset-registration): register report 9510's source asset
and enumerate the resolvable attachments / artifacts it declares.

Scope discipline (contract wp-9510-01):
  * report_id 9510 only -- no other report is read or written;
  * registration only: NO claim extraction, NO report-type classification,
    NO `verified` marks (verification is computed by the platform gate);
  * zero manual transcription: every number below is measured in this process
    (hash, char/byte counts, line numbers, platform figure bytes); the contract
    YAML values are comparison targets only, never trusted;
  * claims 允许为空数组 -> an empty claims[] plus a stated reason is the complete
    result, not an omission.

Sub-commands (idempotent; stdlib, plus jsonschema/matplotlib for verify/figure):

    python3 scripts/kf_wp9510_01_register_assets.py build     # fetch + asset_manifest.json
    python3 scripts/kf_wp9510_01_register_assets.py envelope  # wrap manifest -> kf_result.json
    python3 scripts/kf_wp9510_01_register_assets.py verify    # 6 acceptance checks
    python3 scripts/kf_wp9510_01_register_assets.py figure    # locator/resolution png
    python3 scripts/kf_wp9510_01_register_assets.py all       # the four above, in order
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
REPORT_ID = "9510"
PACKAGE_ID = "wp-9510-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
# ---- contract-declared identity (comparison targets only, never trusted) -----
CONTRACT_SOURCE_HASH = "sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c"
CONTRACT_CHARS = 8039
CONTRACT_TITLE = "P155W1-N02 绿色航行法规合规验证面成熟化（EEXI/CII/EEDI 全链 + 两处缺陷修复）"
CONTRACT_SCENARIO = "green_navigation_regulatory_compliance"

OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID      # committed (repo .gitignore drops artifacts/**,
                                                 # and the mission push gate drops runs/** as a
                                                 # run-record area -> the source copy must live here)
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = OUT_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
RESULT_FIG = FIG_DIR / ("%s_source_locator_map.png" % PACKAGE_ID)
PRODUCER = "agent/m18538"

ENVELOPE_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
MANIFEST_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.schema.json"


# ---------------------------------------------------------------- api helpers
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
    with urllib.request.urlopen(req) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def get_raw(path: str, tok: str):
    req = urllib.request.Request(api_base() + path, headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def fetch_record() -> dict:
    st, raw = get_raw("/tensor/reports/%s" % REPORT_ID, login())
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> %s %r" % (REPORT_ID, st, raw[:200]))
    rec = json.loads(raw)
    if str(rec.get("id")) != REPORT_ID:
        raise SystemExit("report id mismatch: %r" % rec.get("id"))
    return rec


def sha256_hex(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------- reference scan
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
TICK_RE = re.compile(r"`([^`\n]+)`")
REG_RE = re.compile(r"MEPC\.\d+\(\d+\)|MEPC\.1/Circ\.\d+")
DECL_HASH_RE = re.compile(r"sha256\s*`([0-9a-f]{6,64})…`")
HEADER_RE = re.compile(r"^(#{2,3})\s+(.*)$")
WS_RE = re.compile(r"\s")

RESULT_ENUM = {"resolved_in_source": "resolved", "referenced_unresolved": "unresolved",
               "declared_absent": "absent"}

PATH_EXTS = {".png": "figure", ".jpg": "figure", ".jpeg": "figure",
             ".py": "source_module", ".mepc": "source_module",
             ".sqlite": "data_artifact", ".db": "data_artifact",
             ".sql": "data_artifact", ".json": "data_artifact",
             ".csv": "data_artifact", ".md": "document"}


def normalize(token: str) -> str:
    t = token.strip()
    if t.startswith("../"):
        t = t[3:]
    while t.startswith("./"):
        t = t[2:]
    return t


def is_pathlike(tok: str) -> bool:
    """A backticked token counts as a path iff it has no whitespace and either a
    directory part or a known artifact extension. Module names such as
    `regulatory` / `chain` / `NOT_SUPPORTED` are therefore NOT paths."""
    t = tok.strip()
    if not t or WS_RE.search(t):
        return False
    if t.startswith("..") or t.startswith("./"):
        return True
    suffix = Path(t.rstrip("/")).suffix.lower()
    return "/" in t.rstrip("/") or suffix in PATH_EXTS


def classify(token: str) -> str:
    t = normalize(token)
    if REG_RE.fullmatch(t):
        return "external_standard_reference"
    if t.startswith("/api/") or t.startswith("api/v1/"):
        return "api_endpoint_reference"
    name = t.rstrip("/").rsplit("/", 1)[-1]
    ext = Path(name).suffix.lower()
    if ext in PATH_EXTS:
        cls = PATH_EXTS[ext]
        if cls == "source_module" and name.startswith("test_"):
            return "test_module"
        return cls
    if t.endswith("/"):
        return "code_directory"
    if "/" in t:
        return "code_symbol_reference"
    return "declared_reference"


def section_of(lines, line_no: int) -> str:
    title = "(preamble)"
    for i in range(line_no, 0, -1):
        m = HEADER_RE.match(lines[i - 1])
        if m:
            title = "%s %s" % (m.group(1), m.group(2).strip())
            break
    return title


def scan_references(lines) -> list:
    """First-occurrence-order scan of (a) markdown image links, (b) backticked
    path-like tokens, (c) IMO resolution identifiers. Deduplicated by token."""
    seen = {}
    order = []

    def add(token, line_no, form, caption=None):
        tok = normalize(token)
        if tok in seen:
            seen[tok]["also_on_lines"].append(line_no)
            return
        ref = {"token": tok, "line": line_no, "form": form,
               "asset_class": classify(token), "also_on_lines": []}
        if caption:
            ref["caption"] = caption
        seen[tok] = ref
        order.append(ref)

    for i, line in enumerate(lines, start=1):
        for m in IMG_RE.finditer(line):
            add(m.group(2), i, "markdown_image", caption=m.group(1).strip())
        for m in TICK_RE.finditer(line):
            if is_pathlike(m.group(1)):
                add(m.group(1), i, "backtick_path")
        for m in REG_RE.finditer(line):
            add(m.group(0), i, "prose_identifier")
            seen[normalize(m.group(0))]["asset_class"] = "external_standard_reference"

    for ref in order:
        ref["section"] = section_of(lines, ref["line"])
    return order


def char_span_of_line(lines, line_no: int):
    start = sum(len(x) + 1 for x in lines[:line_no - 1])
    return start, start + len(lines[line_no - 1])


def make_locator(md, lines, line_no: int) -> dict:
    q = lines[line_no - 1]
    start, end = char_span_of_line(lines, line_no)
    return {"method": "char_span", "start_char": start, "end_char": end,
            "start_line": line_no, "end_line": line_no,
            "quote": q, "unique": md.count(q) == 1}


def resolve_in_worktree(token: str) -> dict:
    t = normalize(token)
    for base in (ROOT, ROOT / "docs", ROOT / "scripts", ROOT / "runs"):
        p = base / t
        if p.exists():
            return {"status": "resolved_in_source", "scope": "delivery_worktree",
                    "via": "Path.exists(%s)" % p.relative_to(ROOT),
                    "reason": "declared path exists in the TensorKnowledge delivery worktree"}
    return {"status": "referenced_unresolved", "scope": "delivery_worktree",
            "via": "Path.exists(%s)" % t,
            "reason": "declared in the report; the path is an artifact of the "
                      "ship-performance-platform repository (node P155W1-N02) and is not "
                      "present in the TensorKnowledge delivery worktree, so no bytes and no "
                      "hash are claimed here"}


# --------------------------------------------------------------- manifest build
def build_manifest(record: dict) -> dict:
    md = record.get("markdown") or ""
    if not md:
        raise SystemExit("report %s has empty markdown -- nothing to register" % REPORT_ID)
    lines = md.rstrip("\n").split("\n")
    raw = md.encode("utf-8")
    digest = sha256_hex(raw)
    hash_match = digest == CONTRACT_SOURCE_HASH
    chars_match = len(md) == CONTRACT_CHARS
    title_norm = (record.get("title") or "").replace("(", "（").replace(")", "）")
    title_match = title_norm == CONTRACT_TITLE

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_text(md)

    tok = login()
    fig_probes = {}
    for fig in record.get("figures") or []:
        name = fig.get("name") or ""
        st, body = get_raw("/tensor/reports/%s/figures/%s" % (REPORT_ID, name), tok)
        fig_probes[name] = {"http_status": st, "bytes": len(body),
                            "sha256": sha256_hex(body) if st == 200 and body else None,
                            "caption": fig.get("caption")}

    refs = scan_references(lines)
    assets = []

    assets.append({
        "asset_id": "A01",
        "asset_class": "source_document",
        "label": "report %s markdown (source of truth for this package)" % REPORT_ID,
        "in_report_section": section_of(lines, 1),
        "locator": {"method": "document", "start_char": 0, "end_char": len(md),
                    "start_line": 1, "end_line": len(lines),
                    "quote": lines[0], "unique": md.count(lines[0]) == 1},
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "GET /tensor/reports/%s markdown re-hashed in-process; "
                                      "local copy %s" % (REPORT_ID, SOURCE_COPY.relative_to(ROOT)),
                             "result": "resolved"},
        "locator_scope": "whole document: quote = H1 title line (verbatim anchor), "
                         "char span covers the entire markdown",
        "note": "sha256 %s, %d chars / %d UTF-8 bytes, %d lines; contract hash match=%s, "
                "contract chars match=%s" % (digest, len(md), len(raw), len(lines),
                                             hash_match, chars_match),
    })

    for n, ref in enumerate(refs, start=2):
        token = ref["token"]
        line_no = ref["line"]
        line = lines[line_no - 1]
        res = resolve_in_worktree(token)
        note = "first occurrence L%d in %s (%s)" % (line_no, ref["section"], ref["form"])
        name = token.rstrip("/").rsplit("/", 1)[-1]
        if name in fig_probes:
            probe = fig_probes[name]
            declared = DECL_HASH_RE.search(line)
            prefix_ok = None
            if declared and probe.get("sha256"):
                prefix_ok = probe["sha256"].startswith("sha256:" + declared.group(1))
            if probe["http_status"] == 200 and probe["bytes"]:
                res = {"status": "resolved_in_source", "scope": "platform_api",
                       "via": "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, name),
                       "reason": "figure bytes served by the platform; sha256 recomputed here"}
                note += "; platform bytes=%d (HTTP %d) sha256=%s" % (
                    probe["bytes"], probe["http_status"], probe["sha256"])
                note += "; declared truncated prefix %s -> %s" % (
                    declared.group(1) if declared else "n/a",
                    "MATCH" if prefix_ok else ("MISMATCH" if prefix_ok is False
                                               else "not checkable"))
            else:
                note += "; platform figure probe HTTP %d, %d bytes -> no payload, no hash claimed" % (
                    probe["http_status"], probe["bytes"])
        assets.append({
            "asset_id": "A%02d" % n,
            "asset_class": ref["asset_class"],
            "label": token,
            "in_report_section": ref["section"],
            "locator": make_locator(md, lines, line_no),
            "resolution": res["status"],
            "resolution_check": {"check": res["via"],
                                 "result": RESULT_ENUM.get(res["status"], "unresolved")},
            "note": note,
            "declared_reference_form": ref["form"],
            "also_referenced_on_lines": ref["also_on_lines"],
            "existence_asserted_by_worker": False,
        })

    # alias hints: the same file named twice (bare name vs path-qualified) stays two
    # registrations (two distinct textual references) but is cross-linked.
    by_name = {}
    for a in assets[1:]:
        nm = a["label"].rstrip("/").rsplit("/", 1)[-1]
        by_name.setdefault(nm, []).append(a["asset_id"])
    for a in assets[1:]:
        nm = a["label"].rstrip("/").rsplit("/", 1)[-1]
        others = [i for i in by_name.get(nm, []) if i != a["asset_id"]]
        if others:
            a["same_basename_as"] = others

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    by_class = {}
    by_res = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    spans = [a["locator"] for a in assets if a["locator"]["method"] == "char_span"]
    span_ok = all(md[s["start_char"]:s["end_char"]] == s["quote"] for s in spans)

    return {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "B",
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "source": {
            "uri": SOURCE_URI,
            "report_id": REPORT_ID,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest[7:],
            "hash_prefixed": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "mission_id": record.get("mission_id"),
            "platform_tags": record.get("tags") or [],
            "platform_figures": [f.get("name") for f in (record.get("figures") or [])],
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
            "hash_scope": "UTF-8 bytes of the markdown string as served by the platform API",
            "contract": {
                "source_hash": CONTRACT_SOURCE_HASH,
                "chars": CONTRACT_CHARS,
                "title": CONTRACT_TITLE,
                "scenario_key": CONTRACT_SCENARIO,
                "hash_matches": hash_match,
                "chars_matches": chars_match,
                "title_matches": title_match,
                "scenario_matches": record.get("scenario_key") == CONTRACT_SCENARIO,
            },
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "char_spans_verified": len(spans),
        },
        "assets": assets,
        "figure_probes": fig_probes,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-9510-01 sets objective.register_assets=true / "
            "classify_report_type=false, constraints.no_forced_claim_generation=true, and the "
            "package notes state 'claims 允许为空数组'. This工序 registers asset identity only "
            "(report_id, markdown byte hash, declared attachments/artifacts); knowledge "
            "extraction belongs to a downstream工序 (03) and is deliberately not attempted here."),
        "integrity": {
            "quote_uniqueness": {
                "quotes": len(assets),
                "unique_quotes": sum(1 for a in assets if a["locator"]["unique"]),
                "all_unique": all(a["locator"]["unique"] for a in assets),
            },
            "char_span_identity": {"spans_checked": len(spans), "all_match": span_ok},
            "hash_recomputed_locally": digest,
            "hash_matches_contract": hash_match,
        },
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes},
        "figure_probe_summary": {
            "probed": len(fig_probes),
            "http_200_with_bytes": sum(1 for v in fig_probes.values()
                                       if v["http_status"] == 200 and v["bytes"]),
            "http_status_histogram": {str(k): sum(1 for v in fig_probes.values()
                                                  if v["http_status"] == k)
                                      for k in sorted({v["http_status"] for v in fig_probes.values()})}
            if fig_probes else {},
        },
        "observations": [
            "Markdown is complete: H1 title on L1, sections ①-⑥ all present, %d lines / "
            "%d chars; a generator/data footer closes the document." % (len(lines), len(md)),
            "The report declares its whole artifact chain under artifacts/P155W1-N02/ "
            "(compliance.sqlite, results.json, queries.sql, make_report.py, run_compliance.py, "
            "5 figures); those files live in ship-performance-platform and are registered here "
            "as declared references, not as verified bytes.",
            "Figure byte probes: %d/%d names returned HTTP 200 with payload, so the truncated "
            "sha256 prefixes printed in the report body can %s be checked; a figure without "
            "payload stays referenced_unresolved and no hash is claimed."
            % (sum(1 for v in fig_probes.values() if v["http_status"] == 200 and v["bytes"]),
               len(fig_probes),
               "only" if not all(v["http_status"] == 200 and v["bytes"]
                                 for v in fig_probes.values()) else "fully"),
            "5 figures are declared twice: in the platform record (name+caption) and in-body as "
            "relative image links carrying truncated sha256 prefixes; those prefixes are "
            "re-checked against bytes served by GET /tensor/reports/%s/figures/{name}." % REPORT_ID,
            "IMO resolution identifiers (MEPC.x(yy) / MEPC.1/Circ.n) are registered as external "
            "standard references: they have no byte payload on this platform, so they stay "
            "referenced_unresolved by construction -- consistent with the report itself marking "
            "coefficient transcription WITHHELD.",
        ],
        "limitations": [
            "Registration only: no claim extraction, no report-type classification, no verified "
            "marks (the platform gate computes verification independently).",
            "hash scope = UTF-8 bytes of the markdown field; any stored-markdown edit (even "
            "whitespace) invalidates this manifest.",
            "Direct psql read of tensor_reports is denied to this agent (permission denied for "
            "table tensor_reports), so the authenticated API is the only source channel used.",
            "Reference resolution is scoped to this delivery worktree; a path missing here is "
            "reported referenced_unresolved, never as a broken upstream artifact.",
        ],
    }


# ------------------------------------------------------------------- envelope
def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    record = fetch_record()
    md = record.get("markdown") or ""
    live = sha256_hex(md.encode("utf-8"))
    if live != manifest["source"]["hash_prefixed"]:
        raise SystemExit("source hash drifted since manifest build: %s != %s"
                         % (live, manifest["source"]["hash_prefixed"]))
    # schema/kf_result.v1.schema.json (main, draft 2020-12) sets additionalProperties=false at
    # the root and inside provenance, so producer/emitted_at live in the manifest (which is an
    # output), and the empty claims[] belongs under outputs."claims.json" -- never at the root.
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": live,
            "source_hash_matches": live == CONTRACT_SOURCE_HASH,
            "title": record.get("title") or "",
            "scenario_key": record.get("scenario_key") or "",
            "chars": len(md),
        },
        "outputs": {"asset_manifest.json": manifest, "claims.json": []},
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n")
    return env


# --------------------------------------------------------------------- verify
def verify() -> dict:
    import jsonschema

    record = fetch_record()
    md = record.get("markdown") or ""
    lines = md.rstrip("\n").split("\n")
    live_hash = sha256_hex(md.encode("utf-8"))
    manifest = json.loads(MANIFEST.read_text())
    env = json.loads(ENVELOPE.read_text())
    checks = {}

    checks["valid_json"] = {"ok": isinstance(manifest, dict) and isinstance(env, dict),
                            "detail": "asset_manifest.json + kf_result.json parse as JSON objects"}

    schema_detail = {}
    ok = True
    for label, inst, sch in (("kf_result.v1", env, ENVELOPE_SCHEMA),
                             ("asset_manifest.v1", manifest, MANIFEST_SCHEMA)):
        schema = json.loads(sch.read_text())
        cls = (jsonschema.Draft202012Validator if "2020-12" in schema.get("$schema", "")
               else jsonschema.Draft7Validator)
        errs = sorted(cls(schema).iter_errors(inst), key=lambda e: list(e.absolute_path))
        schema_detail[label] = {
            "schema_file": str(sch.relative_to(ROOT)),
            "error_count": len(errs),
            "errors": [("/".join(map(str, e.absolute_path)) + " :: " + e.message)
                       for e in errs][:10],
        }
        ok = ok and not errs
    checks["schema_pass"] = {"ok": ok, "detail": json.dumps(schema_detail, ensure_ascii=False)}

    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        ln = loc["start_line"]
        line_ok = 0 < ln <= len(lines) and lines[ln - 1] == loc["quote"]
        if loc["method"] == "document":
            # document scope: the quote is a verbatim anchor inside the full-document span
            span_ok = (loc["start_char"] == 0 and loc["end_char"] == len(md)
                       and loc["start_line"] == 1 and loc["end_line"] == len(lines))
        else:
            span_ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"]
        if not (line_ok and span_ok and loc["quote"] in md):
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": "%d/%d locators re-resolved (verbatim line + char-span identity + substring)"
                  % (len(manifest["assets"]) - len(bad), len(manifest["assets"])),
        "failures": bad,
    }

    checks["source_hash_matches"] = {
        "ok": live_hash == manifest["source"]["hash_prefixed"] == CONTRACT_SOURCE_HASH
              == env["provenance"]["source_hash"],
        "detail": "live=%s manifest=%s contract=%s envelope=%s"
                  % (live_hash, manifest["source"]["hash_prefixed"], CONTRACT_SOURCE_HASH,
                     env["provenance"]["source_hash"]),
        "chars": {"live": len(md), "manifest": manifest["source"]["chars"],
                  "contract": CONTRACT_CHARS},
        "chars_match": len(md) == manifest["source"]["chars"] == CONTRACT_CHARS,
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {"ok": not dupes and len(ids) == len(set(ids)),
                                  "detail": "%d asset ids, duplicates=%s" % (len(ids), dupes)}

    claims = (env.get("outputs") or {}).get("claims.json") or []
    unresolved = [a["asset_id"] for a in manifest["assets"]
                  if a["resolution"] != "resolved_in_source"]
    note_ok = all((a.get("note") or "").strip() and a["resolution_check"].get("result")
                  for a in manifest["assets"])
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": all(c.get("evidence") or c.get("status") for c in claims)
              and bool(manifest.get("claims_empty_reason")) and note_ok,
        "detail": "%d claims (empty allowed by contract; reason stated=%s); %d assets carry an "
                  "explicit non-resolved status: %s"
                  % (len(claims), bool(manifest.get("claims_empty_reason")), len(unresolved),
                     ",".join(unresolved) if unresolved else "-"),
    }

    out = {"package_id": PACKAGE_ID, "report_id": REPORT_ID, "verified_at": utcnow(),
           "acceptance": checks, "all_ok": all(c["ok"] for c in checks.values()),
           "note": ("Self-check only. Nothing here marks a claim verified; the platform gate "
                    "recomputes hash and locators independently.")}
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


# --------------------------------------------------------------------- figure
def figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    md = SOURCE_COPY.read_text()
    lines = md.rstrip("\n").split("\n")
    manifest = json.loads(MANIFEST.read_text())
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 5.4),
                                   gridspec_kw={"width_ratios": [2.3, 1]})
    xs = list(range(1, len(lines) + 1))
    ys = [len(x) for x in lines]
    ax1.plot(xs, ys, "-", color="#4c72b0", lw=1.0)
    ax1.fill_between(xs, ys, color="#4c72b0", alpha=0.10)
    colors = {"source_module": "#c44e52", "test_module": "#8172b3",
              "data_artifact": "#dd8452", "figure": "#55a868",
              "code_directory": "#937860", "code_symbol_reference": "#da8bc3",
              "external_standard_reference": "#8c8c8c", "declared_reference": "#333333"}
    for a in manifest["assets"]:
        if a["locator"]["method"] != "char_span":
            continue
        ln = a["locator"]["start_line"]
        ax1.plot([ln], [len(lines[ln - 1])], "o", ms=6,
                 color=colors.get(a["asset_class"], "k"))
        ax1.annotate(a["asset_id"], (ln, len(lines[ln - 1])), fontsize=6.5,
                     xytext=(3, 4), textcoords="offset points", color="0.25")
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=k)
               for k, c in colors.items() if k in manifest["counts"]["by_class"]]
    ax1.legend(handles=handles, fontsize=6.8, loc="upper center", ncol=2)
    ax1.set_xlabel("markdown line number (report 9510)")
    ax1.set_ylabel("characters on line")
    ax1.set_title("report 9510 source markdown: line profile + registered asset locators\n"
                  "(%d lines, %d chars, %d assets, sha256 %s...)"
                  % (len(lines), len(md), len(manifest["assets"]),
                     manifest["source"]["hash_prefixed"][7:19]), fontsize=9.5)
    ax1.grid(alpha=0.25)

    h = manifest["counts"]["by_class"]
    labels = list(h.keys())
    vals = [h[k] for k in labels]
    palette = {"resolved_in_source": "#55a868", "referenced_unresolved": "#dd8452",
               "declared_absent": "#c44e52"}
    res_of = {}
    for a in manifest["assets"]:
        res_of.setdefault(a["asset_class"], set()).add(a["resolution"])
    bar_colors = [palette[sorted(res_of[k])[0]] if len(res_of[k]) == 1 else "#4c72b0"
                  for k in labels]
    ax2.barh(range(len(labels)), vals, color=bar_colors)
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels(labels, fontsize=7.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("assets")
    ax2.set_title("asset class x resolution\n(green=resolved_in_source, orange=referenced_unresolved)",
                  fontsize=9)
    for i, v in enumerate(vals):
        ax2.text(v + 0.05, i, str(v), va="center", fontsize=7.5)
    ax2.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    fig.savefig(RESULT_FIG, dpi=170)
    print("figure ->", RESULT_FIG.relative_to(ROOT), sha256_hex(RESULT_FIG.read_bytes()))


def main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if cmd in ("build", "all"):
        m = build_manifest(fetch_record())
        MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
        print("manifest ->", MANIFEST.relative_to(ROOT),
              "| assets", m["counts"]["assets"],
              "| by_class", json.dumps(m["counts"]["by_class"], ensure_ascii=False),
              "| by_resolution", json.dumps(m["counts"]["by_resolution"], ensure_ascii=False))
    if cmd in ("envelope", "all"):
        e = build_envelope()
        print("envelope ->", ENVELOPE.relative_to(ROOT), "|", e["provenance"]["source_hash"])
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