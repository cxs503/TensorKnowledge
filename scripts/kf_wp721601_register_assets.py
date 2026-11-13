#!/usr/bin/env python3
"""wp-7216-01 (task_type 01-asset-registration): register report 7216's source asset
and enumerate the resolvable attachments / artifacts / code pointers it declares.

Sub-commands (idempotent; stdlib only except `figure` which needs matplotlib):

    python3 scripts/kf_wp721601_register_assets.py build      # fetch + write asset_manifest.json
    python3 scripts/kf_wp721601_register_assets.py envelope   # wrap manifest -> kf_result.json
    python3 scripts/kf_wp721601_register_assets.py verify     # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp721601_register_assets.py figure     # locator-map png
    python3 scripts/kf_wp721601_register_assets.py probe      # ecosystem presence probe (non-contract)
    python3 scripts/kf_wp721601_register_assets.py all        # build+envelope+verify+figure

Design rules honoured here (contract wp-7216-01):
  * registration only -- NO claim extraction, NO verified marks, NO classification;
  * zero manual transcription -- every number in the artefacts is measured here from
    the live markdown bytes served by GET /api/v1/tensor/reports/7216;
  * every declared asset carries a locator (char span + 1-based line range + the
    verbatim line) that verify() re-resolves against the live markdown;
  * uncertainty is preserved: an asset is only `resolved_in_source` when its bytes
    are actually in hand; everything else is `referenced_unresolved` with the probe
    that failed recorded next to it;
  * manifest regeneration is deterministic (no timestamps inside `assets`), so a
    second run cannot silently drift the registered identity.
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
REPORT_ID = "7216"
PACKAGE_ID = "wp-7216-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
# contract-declared identity (work-package YAML); comparison targets only -- the
# script never trusts them, it recomputes and reports the comparison.
CONTRACT_SOURCE_HASH = "sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b"
CONTRACT_CHARS = 11338
CONTRACT_TITLE = ("IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase "
                  "lambda/rho decoupling and Hadamard-Rybczynski comparison")
CONTRACT_SCENARIO = "lbm_rb_hr_validation"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
RECORD_COPY = RUN_DIR / ("record_%s.json" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
MANIFEST_SCHEMA = OUT_DIR / "asset_manifest.schema.json"
ECOSYSTEM_PROBE = OUT_DIR / "ecosystem_presence_probe.json"
ENVELOPE_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
PRODUCER = "kf-worker/m15594"

PATH_EXTS = {".py", ".json", ".png", ".jpg", ".md", ".csv", ".h5", ".hdf5", ".yaml", ".yml"}


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
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
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


# ------------------------------------------------------------- source geometry
def line_starts(md: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(md):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def span_of_line(md: str, starts: list[int], line_no: int) -> tuple[int, int]:
    """char span of 1-based line_no WITHOUT its trailing newline."""
    s = starts[line_no - 1]
    e = md.find("\n", s)
    return s, (len(md) if e < 0 else e)


# ------------------------------------------------------- declared-token scan
TICK_RE = re.compile(r"`([^`\n]+)`")
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
DOTTED_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
CALL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\(.*\)$")
PLAIN_RE = re.compile(r"^[a-z_][a-z0-9_]{3,}$")
HEADING_RE = re.compile(r"^(#{2,3})\s+(.*)$")

# Tokens that look like identifiers but are prose/parameter names, not code
# pointers. Rule: a plain (undotted, non-path) backticked identifier is only a
# code pointer if it is snake_case AND not a physical quantity name. The
# exclusions below are the measured leftovers of that rule (see report §5).
PLAIN_EXCLUDE = {
    "u_eq", "g_12", "t_hot", "rho_d", "rho_c", "tau_d", "tau_c", "mu_d", "mu_c",
    "lambda_measured", "pytest", "float64", "python3", "numpy", "matplotlib",
    "json", "self", "mixture", "xx", "yy", "zz",
}
MARKDOWN_IMAGE_EXCLUDE = {"png_base64"}


PATH_CHARSET_RE = re.compile(r"^[A-Za-z0-9_./*\-]+$")


def is_path_token(tok: str) -> bool:
    """A backticked token is a path reference iff it is a plain POSIX-ish path or a
    glob. Expressions (`Jv≈(F(x0+εv)−F(x0))/ε`), shell commands with arguments and
    prose are rejected by the charset test rather than by a hand list."""
    tok = tok.strip()
    if not tok or " " in tok or tok.startswith(("http://", "https://")):
        return False
    if not PATH_CHARSET_RE.match(tok):
        return False
    if "*" in tok:
        return "/" in tok
    suf = Path(tok.lstrip("./")).suffix.lower()
    if suf in PATH_EXTS:
        return True
    return "/" in tok and suf == ""


def split_command(tok: str) -> list[str]:
    """`pytest -q tests/a.py tests/b.py` carries two path declarations inside one
    backticked span; shell-style split keeps them registrable."""
    return [t for t in re.split(r"\s+", tok.strip()) if t]


def classify_path(tok: str) -> tuple[str, str]:
    """-> (asset_class, label_kind)"""
    t = tok.lstrip("./")
    if t.startswith("agent/"):
        return "git_branch_reference", "branch"
    suf = Path(t).suffix.lower()
    if suf in (".png", ".jpg") or t.endswith("*.png"):
        return "figure_reference", "figure_glob" if "*" in t else "figure"
    if suf == ".py":
        if t.startswith("tests/"):
            return "test_reference", "test"
        if t.startswith("benchmarks/"):
            return "benchmark_script_reference", "benchmark_script"
        if t.startswith("src/"):
            return "source_code_reference", "source_module"
        return "source_code_reference", "script"
    if suf in (".json", ".csv", ".h5", ".hdf5"):
        return "data_artifact_reference", "data_artifact"
    if suf in (".md", ".yaml", ".yml"):
        return "document_reference", "document"
    return "directory_reference", "directory"


def scan_declarations(md: str) -> list[dict]:
    """Deterministic scan: one declaration per unique token, locator = first
    occurrence. Occurrence lines are all recorded so a reviewer can see spread."""
    starts = line_starts(md)
    lines = md.rstrip("\n").split("\n")
    decls: dict[str, dict] = {}
    section = "(before first ## heading)"

    def add(token: str, form: str, asset_class: str, label_kind: str,
            line_no: int, s: int, e: int):
        d = decls.get(token)
        if d is None:
            d = decls[token] = {"token": token, "form": form, "asset_class": asset_class,
                                "label_kind": label_kind, "first_line": line_no,
                                "char_start": s, "char_end": e,
                                "in_report_section": section, "occurrence_lines": []}
        if line_no not in d["occurrence_lines"]:
            d["occurrence_lines"].append(line_no)

    for i, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            section = line.strip()
        for alt, path in IMG_RE.findall(line):
            if path in MARKDOWN_IMAGE_EXCLUDE:
                continue
            s, e = span_of_line(md, starts, i)
            cls, kind = classify_path(path)
            add(path, "markdown_image_link", cls, kind, i, s, e)
        for tok in TICK_RE.findall(line):
            tok = tok.strip()
            s, e = span_of_line(md, starts, i)
            if not tok:
                continue
            if is_path_token(tok):
                cls, kind = classify_path(tok)
                add(tok, "backticked_path", cls, kind, i, s, e)
                continue
            if " " in tok:  # shell command: register every path argument it carries
                parts = [t for t in split_command(tok)
                         if is_path_token(t) and (Path(t).suffix.lower() in PATH_EXTS
                                                  or t.endswith("*.png"))]
                if parts:
                    for part in parts:
                        cls, kind = classify_path(part)
                        add(part, "path_in_backticked_command", cls, kind, i, s, e)
                    continue
            mcall = CALL_RE.match(tok)
            if mcall and ("_" in mcall.group(1) or "." in mcall.group(1)):
                add(tok, "backticked_call", "api_symbol_reference", "callable", i, s, e)
                continue
            if DOTTED_RE.match(tok):
                add(tok, "backticked_dotted", "api_symbol_reference", "dotted_symbol", i, s, e)
                continue
            if PLAIN_RE.match(tok) and "_" in tok and tok not in PLAIN_EXCLUDE:
                add(tok, "backticked_identifier", "api_symbol_reference",
                    "identifier", i, s, e)
    return sorted(decls.values(), key=lambda d: (d["char_start"], d["token"]))


def symbol_key(token: str) -> str:
    m = CALL_RE.match(token)
    return m.group(1) if m else token


# ----------------------------------------------------------------- resolution
def resolve_in_worktree(token: str) -> dict:
    """Contract scope = delivery worktree (TensorKnowledge). Nothing outside it is
    searched here: declaring anything else 'resolved' would be a guess about which
    revision of the producing repo (TensorLBM, branch `agent/m5628`) was used."""
    if token.endswith("*"):
        pat = token.lstrip("./")
        hits = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(pat)
                      if p.is_file() and ".git" not in p.parts)[:5]
        return {"status": "resolved" if hits else "unresolved",
                "scope": "delivery_worktree", "glob": pat, "hits": hits,
                "reason": None if hits else "glob matched nothing in TensorKnowledge"}
    cand = token.lstrip("./")
    p = ROOT / cand
    if p.is_file() and ".git" not in p.parts:
        b = p.read_bytes()
        return {"status": "resolved", "scope": "delivery_worktree",
                "bytes": len(b), "sha256": sha256_hex(b)}
    base = Path(cand).name
    same = sorted(str(q.relative_to(ROOT)) for q in ROOT.rglob(base)
                  if q.is_file() and ".git" not in q.parts)[:5]
    return {"status": "unresolved", "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge "
                      "(report %s is a TensorLBM asset, repo layering=LBM|research|A)" % REPORT_ID,
            "same_basename_hits": same}


def probe_platform_figures(record: dict, tok: str) -> dict:
    """Does the platform serve the bytes of a figure the record declares?"""
    if "*" in tok:
        return {"check": "glob_reference_no_single_file", "result": "unresolved",
                "detail": "glob pattern; no single file to hash or fetch"}
    name = Path(tok.split("*")[0]).name
    declared = [f.get("name") for f in (record.get("figures") or [])]
    if name not in declared:
        return {"check": "platform_figure_endpoint", "result": "absent",
                "http_status": None, "detail": "not in record.figures"}
    st, body = _get("/tensor/reports/%s/figures/%s" % (REPORT_ID, name), _login())
    if st == 200:
        return {"check": "platform_figure_endpoint", "result": "present",
                "http_status": st, "bytes": len(body), "sha256": sha256_hex(body)}
    return {"check": "platform_figure_endpoint", "result": "unresolved",
            "http_status": st, "detail": body[:80].decode("utf-8", "replace"),
            "endpoint": "GET /api/v1/tensor/reports/%s/figures/%s" % (REPORT_ID, name),
            "note": "declared in record.figures, bytes not served by the platform"}


# ------------------------------------------------------------------- manifest
def build_manifest(record: dict) -> dict:
    md = record.get("markdown") or ""
    raw = md.encode("utf-8")
    starts = line_starts(md)
    lines = md.rstrip("\n").split("\n")
    digest = sha256_hex(raw)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_bytes(raw)
    RECORD_COPY.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")

    hash_match = digest == CONTRACT_SOURCE_HASH
    if not hash_match:
        raise SystemExit("source hash mismatch: computed %s != contract %s"
                         % (digest, CONTRACT_SOURCE_HASH))
    title = record.get("title") or ""
    record_figures = [f.get("name") for f in (record.get("figures") or [])]

    # ---- asset A01: the source markdown itself (the only byte-resolved asset)
    s0, e0 = span_of_line(md, starts, 1)
    quote0 = md[s0:e0]
    assets = [{
        "asset_id": "A01",
        "asset_key": "report-%s:source-markdown" % REPORT_ID,
        "asset_class": "report_markdown",
        "label": "report-%s-markdown" % REPORT_ID,
        "in_report_section": lines[0].strip(),
        "locator": {"method": "document", "source_field": "markdown",
                    "char_start": 0, "char_end": len(md),
                    "line_start": 1, "line_end": len(lines),
                    "quote": quote0, "quote_sha256": sha256_hex(quote0.encode()),
                    "unique": md.count(quote0) == 1},
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "sha256(UTF-8 bytes) == contract source_hash",
                             "result": "resolved"},
        "bytes": len(raw), "chars": len(md), "lines": len(lines),
        "sha256": digest,
        "hash_scope": "UTF-8 bytes of the `markdown` field served by GET /api/v1/tensor/reports/%s"
                      % REPORT_ID,
        "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
        "note": "source asset; hash recomputed locally and compared to the contract value",
    }]

    # ---- declared references A02..Ann
    decls = scan_declarations(md)
    figure_decls = [d for d in decls if d["asset_class"] == "figure_reference"]
    other_decls = [d for d in decls if d["asset_class"] != "figure_reference"]
    order = []
    for d in decls:
        order.append(d)
    # record figures that the prose never names still get registered (no quote ->
    # document locator on line 1, explicitly flagged)
    named = {Path(d["token"].split("*")[0]).name for d in figure_decls}
    for fname in record_figures:
        if fname not in named:
            order.append({"token": fname, "form": "record_figures_only",
                          "asset_class": "figure_reference", "label_kind": "figure",
                          "first_line": 1, "char_start": s0, "char_end": e0,
                          "in_report_section": lines[0].strip(),
                          "occurrence_lines": []})

    for n, d in enumerate(order, start=2):
        aid = "A%02d" % n
        tok = d["token"]
        quote = md[d["char_start"]:d["char_end"]]
        if d["form"] == "record_figures_only":
            resolution = "referenced_unresolved"
            check = probe_platform_figures(record, tok)
        elif d["asset_class"] == "figure_reference":
            check = probe_platform_figures(record, tok)
            resolution = ("resolved_in_source" if check["result"] == "present"
                          else "referenced_unresolved")
        elif d["asset_class"] == "git_branch_reference":
            check = {"check": "git_branch_named_in_prose", "result": "unresolved",
                     "note": "producing branch name only; this工序 does not query the LBM "
                             "repository refs (out of contract scope)"}
            resolution = "referenced_unresolved"
        elif d["asset_class"] == "api_symbol_reference":
            check = {"check": "symbol_declared_in_markdown_no_byte_asset",
                     "result": "unresolved",
                     "note": "library symbol named in prose; registration does not open "
                             "the producing repo (out of contract scope)"}
            resolution = "referenced_unresolved"
        else:
            r = resolve_in_worktree(tok)
            check = {"check": "file_exists_in_delivery_worktree", "result": r["status"],
                     "scope": r["scope"], "reason": r.get("reason"),
                     "same_basename_hits": r.get("same_basename_hits")}
            if r["status"] == "resolved":
                check["bytes"] = r["bytes"]
                check["sha256"] = r["sha256"]
                resolution = "resolved_in_source"
            else:
                resolution = "referenced_unresolved"
        assets.append({
            "asset_id": aid,
            "asset_key": "report-%s:ref:%s" % (REPORT_ID, symbol_key(tok)),
            "asset_class": d["asset_class"],
            "label": d["label_kind"],
            "token": tok,
            "symbol_key": symbol_key(tok) if d["asset_class"] == "api_symbol_reference" else None,
            "form": d["form"],
            "in_report_section": d["in_report_section"],
            "locator": {"method": "char_span", "source_field": "markdown",
                        "char_start": d["char_start"], "char_end": d["char_end"],
                        "line_start": d["first_line"], "line_end": d["first_line"],
                        "quote": quote,
                        "quote_sha256": sha256_hex(quote.encode()),
                        "unique": md.count(quote) == 1},
            "occurrence_lines": sorted(d["occurrence_lines"]),
            "resolution": resolution,
            "resolution_check": check,
            "note": _note_for(d, tok),
        })

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "C",
        "producer": PRODUCER,
        "generated_at": utcnow(),
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "hash_alg": "sha256",
            "hash": digest[7:],
            "source_hash": digest,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_match": hash_match,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "has_crlf": "\r" in md,
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "1-based; logical lines = markdown.rstrip(chr(10)).split(chr(10)); "
                             "char spans index the full markdown string",
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "title": title,
            "scenario_key": record.get("scenario_key"),
            "mission_id": record.get("mission_id"),
            "status": record.get("status"),
            "created_at": record.get("created_at"),
            "tags": record.get("tags") or [],
            "contract_title": CONTRACT_TITLE,
            "contract_scenario_key": CONTRACT_SCENARIO,
            "title_matches_contract": title == CONTRACT_TITLE,
            "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            "platform_figures": record_figures,
            "platform_tags": record.get("tags") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "figure_declarations_in_prose": len(figure_decls),
            "record_figures": len(record_figures),
        },
        "assets": assets,
        "claims": [],
        "claims_empty_reason": (
            "objective.classify_report_type=false and this package is registration-only "
            "(no extraction): claims are legitimately empty per contract.output.asset_manifest.json "
            "+ constraints.no_forced_claim_generation. Report 7216's own numeric claims are NOT "
            "re-stated here; they stay in the source markdown and are untouched (no verified marks)."),
        "integrity": {
            "quote_uniqueness": {
                "locators": len(assets),
                "unique_quotes": sum(1 for a in assets if a["locator"]["unique"]),
                "note": "non-unique quotes are still exactly resolvable via their char span; "
                        "uniqueness is reported, not forced",
            },
            "hash_recomputed_locally": digest,
            "hash_matches_contract": hash_match,
            "assets_with_locator": len(assets),
            "assets_without_locator": 0,
            "verified_marks_emitted": 0,
        },
    }
    return manifest


def _note_for(d: dict, tok: str) -> str:
    if d["asset_class"] == "figure_reference":
        return ("figure bytes are not served by the platform figure endpoint; identity is the "
                "record.figures declaration plus the prose reference (probe recorded in "
                "resolution_check)")
    if d["asset_class"] == "api_symbol_reference":
        return ("declared library symbol / callable; this工序 registers the pointer only and "
                "does not read the producing repository")
    if d["asset_class"] == "data_artifact_reference":
        return ("artifact produced outside this repository (evidence chain §6 of the report); "
                "bytes unavailable in the delivery worktree")
    if d["asset_class"] == "directory_reference":
        return "directory/glob reference; no single file to hash"
    return "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"


# ------------------------------------------------------------------- envelope
def build_envelope() -> dict:
    if not MANIFEST.exists():
        raise SystemExit("run `build` first")
    manifest = json.loads(MANIFEST.read_text())
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["source_hash"],
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("hash recomputed locally from the UTF-8 bytes of the `markdown` field of "
                      "GET /api/v1/tensor/reports/%s; equals the contract value %s"
                      % (REPORT_ID, CONTRACT_SOURCE_HASH)),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n")
    return env


# --------------------------------------------------------- cross-channel check
def db_cross_channel(md: str) -> dict:
    """Second, independent source channel: the platform DB row. Reported as
    informational evidence -- never as a substitute for the API contract hash, and
    honestly `not_run` if psql/DB access is unavailable in the re-run environment."""
    db = os.environ.get("TP_PG_DB", "tensorplatform")
    sql = "select markdown from tensor_reports where id=%s" % REPORT_ID
    try:
        r = subprocess.run(["psql", "-d", db, "-tA", "-c", sql],
                           capture_output=True, timeout=120)
    except Exception as e:  # psql missing / timeout
        return {"status": "not_run", "detail": "%s: %s" % (type(e).__name__, e)}
    if r.returncode != 0:
        return {"status": "not_run", "detail": r.stderr.decode("utf-8", "replace")[:200]}
    api_raw = md.encode("utf-8")
    out = r.stdout
    variants = {"as_returned": out,
                "minus_one_trailing_newline": out[:-1] if out.endswith(b"\n") else out,
                "minus_two_trailing_newlines": out.rstrip(b"\n")}
    match = [k for k, v in variants.items() if v == api_raw]
    return {
        "status": "match" if match else "mismatch",
        "channel": "psql -d %s -tA -c \"%s\"" % (db, sql),
        "api_sha256": sha256_hex(api_raw),
        "db_sha256_as_returned": sha256_hex(out),
        "db_bytes_returned": len(out),
        "matched_variants": match,
        "note": ("psql -tA appends a newline per row, so the DB bytes are compared to the API "
                 "bytes with that suffix accounted for; a mismatch here means the two channels "
                 "disagree and the platform hash is authoritative"),
    }


# ------------------------------------------------------------------- verify
def verify() -> dict:
    checks: dict[str, dict] = {}
    manifest = json.loads(MANIFEST.read_text())
    env = json.loads(ENVELOPE.read_text())

    # 1 valid_json
    checks["valid_json"] = {"ok": True,
                            "detail": "asset_manifest.json + kf_result.json parsed by json.loads"}

    # 2 schema_pass
    try:
        import jsonschema
        v_env = jsonschema.Draft202012Validator(json.loads(ENVELOPE_SCHEMA.read_text()))
        e_errs = ["%s: %s" % ("/".join(map(str, e.absolute_path)), e.message)
                  for e in sorted(v_env.iter_errors(env), key=lambda e: list(map(str, e.absolute_path)))]
        v_man = jsonschema.Draft7Validator(json.loads(MANIFEST_SCHEMA.read_text()))
        m_errs = ["%s: %s" % ("/".join(map(str, e.absolute_path)), e.message)
                  for e in sorted(v_man.iter_errors(manifest), key=lambda e: list(map(str, e.absolute_path)))]
        checks["schema_pass"] = {
            "ok": not e_errs and not m_errs,
            "detail": "kf_result.v1.schema.json (Draft2020-12) errors=%d; "
                      "local asset_manifest.schema.json (Draft-07) errors=%d" % (len(e_errs), len(m_errs)),
            "envelope_errors": e_errs[:10], "manifest_errors": m_errs[:10],
            "schemas": [str(ENVELOPE_SCHEMA.relative_to(ROOT)), str(MANIFEST_SCHEMA.relative_to(ROOT))],
        }
    except ImportError as e:  # honest not_run instead of a green tick
        checks["schema_pass"] = {"ok": False, "status": "not_run",
                                 "detail": "jsonschema unavailable: %s" % e}

    # 3 source_locator_resolvable (against the LIVE markdown, not the local copy)
    record = fetch_record()
    md = record.get("markdown") or ""
    starts = line_starts(md)
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if loc["method"] == "document":
            ok = (loc["char_start"] == 0 and loc["char_end"] == len(md)
                  and q in md
                  and hashlib.sha256(q.encode()).hexdigest() == loc["quote_sha256"].split(":")[-1])
        else:
            ok = (md[loc["char_start"]:loc["char_end"]] == q
                  and hashlib.sha256(q.encode()).hexdigest() == loc["quote_sha256"].split(":")[-1])
        if ok and loc["method"] == "char_span":
            ok = (md[starts[loc["line_start"] - 1]:starts[loc["line_start"] - 1] + len(q)] == q)
        if not ok:
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": "%d/%d locators re-resolved on the live markdown (char span + verbatim + quote sha256)"
                  % (len(manifest["assets"]) - len(bad), len(manifest["assets"])),
        "failures": bad,
        "unique_quotes": sum(1 for a in manifest["assets"] if a["locator"]["unique"]),
    }

    # 4 source_hash_matches
    live_hash = sha256_hex(md.encode("utf-8"))
    checks["source_hash_matches"] = {
        "ok": live_hash == manifest["source"]["source_hash"] == CONTRACT_SOURCE_HASH
              == env["provenance"]["source_hash"],
        "detail": "live=%s manifest=%s contract=%s" % (live_hash, manifest["source"]["source_hash"],
                                                       CONTRACT_SOURCE_HASH),
        "chars": {"live": len(md), "manifest": manifest["source"]["chars"],
                  "contract": CONTRACT_CHARS},
    }

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    keys = [a["asset_key"] for a in manifest["assets"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    dupkeys = sorted({k for k in keys if keys.count(k) > 1})
    checks["no_duplicate_ids"] = {"ok": not dupes and not dupkeys,
                                  "detail": "%d ids / %d keys; duplicate ids=%s duplicate keys=%s"
                                            % (len(ids), len(keys), dupes, dupkeys)}

    # 6 all_claims_have_evidence_or_explicit_unresolved_status
    claims = env.get("claims") or []
    ev_ok = all(c.get("evidence") or c.get("unresolved_reason") for c in claims)
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": bool(ev_ok and manifest.get("claims_empty_reason")),
        "detail": "%d claims; every claim with evidence/unresolved: %s; empty-claims reason stated: %s"
                  % (len(claims), ev_ok, bool(manifest.get("claims_empty_reason"))),
    }

    out = {"package_id": PACKAGE_ID, "verified_at": utcnow(),
           "extra_checks": {"db_cross_channel": db_cross_channel(md)},
           "acceptance": checks,
           "all_ok": all(c["ok"] for c in checks.values()),
           "note": ("Self-check only -- nothing here is a platform verification. No claim is marked "
                    "verified; the platform gate recomputes hash/locators/taxonomy independently.")}
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


# ------------------------------------------------------------------ ecosystem
def ecosystem_probe() -> dict:
    """NON-CONTRACT probe: does the producing repo's content exist anywhere in the
    local ecosystem checkouts? Presence only -- it cannot establish the producing
    revision (report 7216 names branch `agent/m5628`), so it never flips an asset
    to resolved."""
    if not MANIFEST.exists():
        raise SystemExit("run `build` first")
    manifest = json.loads(MANIFEST.read_text())
    work = Path("/root/tp-agent/work")
    patterns = [a["token"] for a in manifest["assets"]
                if a["asset_class"] in ("source_code_reference", "test_reference",
                                        "benchmark_script_reference", "data_artifact_reference")]
    hits: dict[str, dict] = {}
    for tok in patterns:
        t = tok.lstrip("./")
        found = []
        for p in work.glob("*/" + t):
            if p.is_file():
                try:
                    head = subprocess.run(["git", "-C", str(p.parent), "rev-parse", "HEAD"],
                                          capture_output=True, text=True, timeout=10)
                    h = head.stdout.strip() or None
                except Exception:
                    h = None
                found.append({"worktree": p.relative_to(work).parts[0],
                              "sha256": sha256_hex(p.read_bytes()), "git_head": h})
        digest_set = sorted({f["sha256"] for f in found})
        hits[tok] = {"checkouts_with_file": len(found),
                     "distinct_contents": len(digest_set),
                     "example": found[:3]}
    out = {
        "package_id": PACKAGE_ID, "report_id": REPORT_ID, "probed_at": utcnow(),
        "status": "non_contract_probe",
        "caveat": ("presence in local mission worktrees does NOT establish the producing revision; "
                   "resolve() therefore keeps these assets referenced_unresolved"),
        "probe_root": str(work), "probe_glob": "*/<declared path>",
        "declared_paths": len(patterns),
        "paths_found_somewhere": sum(1 for v in hits.values() if v["checkouts_with_file"]),
        "hits": hits,
    }
    ECOSYSTEM_PROBE.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


# --------------------------------------------------------------------- figure
def figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text())
    md = SOURCE_COPY.read_text()
    lines = md.rstrip("\n").split("\n")
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.2),
                                   gridspec_kw={"width_ratios": [2.15, 1]})
    xs = list(range(1, len(lines) + 1))
    ys = [len(l) for l in lines]
    ax1.plot(xs, ys, "-", color="#4c72b0", lw=0.9)
    ax1.fill_between(xs, ys, color="#4c72b0", alpha=0.12)
    colors = {"figure_reference": "#55a868", "source_code_reference": "#c44e52",
              "test_reference": "#8172b3", "benchmark_script_reference": "#dd8452",
              "data_artifact_reference": "#937860", "api_symbol_reference": "#4c72b0",
              "directory_reference": "#666666"}
    by_class: dict[str, list[int]] = {}
    for a in manifest["assets"]:
        by_class.setdefault(a["asset_class"], []).append(a["locator"]["line_start"])
    for cls, lns in sorted(by_class.items()):
        ln_ok = [l for l in lns if 1 <= l <= len(lines)]
        ax1.vlines(ln_ok, 0, [len(lines[l - 1]) for l in ln_ok],
                   color=colors.get(cls, "k"), lw=2.2,
                   label="%s (n=%d)" % (cls, len(lns)))
    for a in manifest["assets"]:
        if a["asset_class"] == "report_markdown":
            continue
    for hdr in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6."):
        for i, l in enumerate(lines, start=1):
            if l.startswith(hdr):
                ax1.axvline(i, color="0.6", ls=":", lw=0.8)
                ax1.annotate(hdr.strip(), (i, max(ys) * 0.97), fontsize=7, color="0.35",
                             rotation=90, ha="right", va="top")
                break
    ax1.set_xlabel("markdown line number (report %s, %d lines)" % (REPORT_ID, len(lines)))
    ax1.set_ylabel("characters on line")
    ax1.set_title("report %s source markdown: line profile + %d registered asset locators\n"
                  "sha256 %s… · %d chars · %d resolved / %d unresolved"
                  % (REPORT_ID, manifest["counts"]["assets"], manifest["source"]["source_hash"][7:19],
                     manifest["source"]["chars"], manifest["counts"]["resolved_in_source"],
                     manifest["counts"]["referenced_unresolved"]), fontsize=10)
    ax1.legend(fontsize=6.5, loc="upper center", ncol=2)
    ax1.grid(alpha=0.25)

    labels = list(manifest["counts"]["by_class"].keys())
    vals = [manifest["counts"]["by_class"][k] for k in labels]
    ax2.barh(range(len(labels)), vals, color=[colors.get(k, "k") for k in labels])
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels(labels, fontsize=7)
    ax2.invert_yaxis()
    ax2.set_xlabel("assets")
    ax2.set_title("registered assets by class\n(claims extracted: %d -- registration only)"
                  % len(manifest["claims"]), fontsize=10)
    for i, v in enumerate(vals):
        ax2.text(v + 0.05, i, str(v), va="center", fontsize=7)
    ax2.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    out = FIG_DIR / "wp721601_source_locator_map.png"
    fig.savefig(out, dpi=170)
    print("figure ->", out.relative_to(ROOT))


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if cmd in ("build", "all"):
        record = fetch_record()
        manifest = build_manifest(record)
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print("manifest ->", MANIFEST.relative_to(ROOT),
              "| assets", manifest["counts"]["assets"],
              "| resolved", manifest["counts"]["resolved_in_source"],
              "| unresolved", manifest["counts"]["referenced_unresolved"])
    if cmd in ("envelope", "all"):
        env = build_envelope()
        print("envelope ->", ENVELOPE.relative_to(ROOT), "|", env["provenance"]["source_hash"])
    if cmd in ("verify", "all"):
        v = verify()
        for k, c in v["acceptance"].items():
            print("   [%s] %-58s %s" % ("PASS" if c["ok"] else "FAIL", k, c["detail"][:110]))
        print("verify -> all_ok", v["all_ok"])
    if cmd in ("probe", "all"):
        p = ecosystem_probe()
        print("probe ->", ECOSYSTEM_PROBE.relative_to(ROOT),
              "| found somewhere %d/%d" % (p["paths_found_somewhere"], p["declared_paths"]))
    if cmd in ("figure", "all"):
        figure()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))