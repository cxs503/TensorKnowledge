#!/usr/bin/env python3
"""wp-9632-01 (task_type 01-asset-registration): register the source asset of
report 9632 and enumerate every attachment / artifact / code path that the
report *declares*.

Contract wp-9632-01 (lane B, repo TensorKnowledge, status draft):
  report_id 9632 | source_uri tensor://reports/9632 | source_field markdown
  source_hash sha256:b2c5eb5dad0b6db25574338b37aa5be1c8fdf20bbc7d3c75640e1c1727756841
  chars 10749 | scenario ice_ridge_consolidation
  objective: register_assets=true, classify_report_type=false

Sub-commands (idempotent; stdlib only, `figure` additionally needs matplotlib):

    python3 scripts/kf_wp9632_01_register.py build      # fetch + write asset_manifest.json
    python3 scripts/kf_wp9632_01_register.py envelope   # wrap manifest -> kf_result.json
    python3 scripts/kf_wp9632_01_register.py verify     # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp9632_01_register.py figure     # locator map png
    python3 scripts/kf_wp9632_01_register.py all        # build+envelope+verify+figure

Design rules honoured here:
  * registration only -- NO claim extraction, NO "verified" marks (verification
    is the platform gate's job); claims[] is legitimately empty;
  * zero manual transcription -- every number in the artefacts is measured by
    this script, never retyped from the report prose;
  * every declared asset carries a resolver-checked locator: verbatim quote +
    char span + line numbers inside the *live* markdown;
  * an asset is only marked resolved when the bytes/object is actually reachable
    in the delivery worktree; everything owned by another repo stays
    referenced_unresolved with the reason recorded;
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
REPORT_ID = "9632"
PACKAGE_ID = "wp-9632-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
LANE = "B"

# Contract-declared identity (work-package YAML). Compared against, never trusted.
CONTRACT_SOURCE_HASH = "sha256:b2c5eb5dad0b6db25574338b37aa5be1c8fdf20bbc7d3c75640e1c1727756841"
CONTRACT_CHARS = 10749
CONTRACT_TITLE = "IN101-N07 冰脊固结热力学：龙骨大孔隙再冻结与固结度-阻力耦合"
CONTRACT_SCENARIO = "ice_ridge_consolidation"

OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID           # committed (gitignore drops artifacts/)
FIG_DIR = OUT_DIR / "figures"
RUN_DIR = ROOT / "runs" / PACKAGE_ID                  # committed: run worksheet + byte copy
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
PRODUCER = "kf-worker/m15662"

MANIFEST_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.wp9632-01.schema.json"
ENVELOPE_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"

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
    try:
        with urllib.request.urlopen(req) as r:
            tok = json.load(r).get("access_token")
    except urllib.error.HTTPError as e:
        raise SystemExit("login failed: %s %r" % (e.code, e.read()[:200]))
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
REPO_RE = re.compile(r"^Tensor[A-Z][A-Za-z0-9]+$")
SYMBOL_RE = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)+$")


def classify(path: str) -> str:
    if path.endswith("/"):
        return "source_directory_reference"
    return PATH_EXTS.get(Path(path).suffix.lower(), "referenced_artifact")


def path_like_tokens(piece: str):
    """Pull path-like pieces out of a backticked token (may be a command line)."""
    out = []
    for part in piece.split():
        part = part.strip("`'\".,;:")
        if not part or part.startswith("http"):
            continue
        ext = Path(part).suffix.lower()
        if ext in PATH_EXTS or ("/" in part and not part.startswith("-")):
            out.append(part)
    return out


def scan_refs(lines):
    """Path-like references: markdown images first, then backticked tokens."""
    refs, seen = [], {}

    def add(token, form, line_no):
        if token in seen:
            return
        seen[token] = True
        refs.append({"token": token, "form": form, "line": line_no,
                     "kind": classify(token)})

    for n, line in enumerate(lines, start=1):
        for m in IMG_RE.finditer(line):
            add(m.group(2), "markdown_image", n)
        for m in TICK_RE.finditer(line):
            for tok in path_like_tokens(m.group(1)):
                add(tok, "backticked_path", n)
    return refs


def scan_symbols(lines):
    """Dotted lowercase identifiers named in backticks: modules and functions."""
    out, seen = [], set()
    for n, line in enumerate(lines, start=1):
        for m in TICK_RE.finditer(line):
            for tok in m.group(1).split():
                tok = tok.strip("`'\".,;:()")
                if not SYMBOL_RE.match(tok) or tok in seen:
                    continue
                if Path(tok).suffix.lower() in PATH_EXTS:
                    continue  # a filename, already handled by scan_refs
                if tok.split(".")[0] in ("numpy", "scipy", "matplotlib", "math",
                                         "json", "os", "sys", "pathlib"):
                    continue  # stdlib / third-party, not a report artifact
                seen.add(tok)
                kind = "module_reference" if "." in tok and m.group(1).strip() == tok \
                    and tok.count(".") >= 1 and tok.split(".")[0] in ("tensorphysics",) \
                    else "symbol_reference"
                out.append({"token": tok, "kind": kind, "line": n})
    return out


def scan_repos(lines):
    out, seen = [], set()
    for n, line in enumerate(lines, start=1):
        for m in TICK_RE.finditer(line):
            tok = m.group(1).strip()
            if REPO_RE.match(tok) and tok not in seen:
                seen.add(tok)
                out.append({"token": tok, "kind": "repository_reference", "line": n})
    return out


# ------------------------------------------------------------------ resolvers
def resolve_in_worktree(path: str) -> dict:
    """Is this declared path present in the delivery worktree (TensorKnowledge)?"""
    clean = path.lstrip("./")
    cand = ROOT / clean
    if cand.exists():
        return {"status": "resolved", "scope": "delivery_worktree",
                "via": "filesystem: %s" % clean,
                "bytes": cand.stat().st_size if cand.is_file() else None,
                "is_dir": cand.is_dir()}
    hits = []
    base = Path(clean).name
    if base:
        for p in ROOT.rglob(base):
            if ".git/" in str(p) or p.is_dir():
                continue
            hits.append(str(p.relative_to(ROOT)))
            if len(hits) >= 5:
                break
    return {"status": "unresolved", "scope": "delivery_worktree",
            "via": "filesystem probe under %s" % ROOT.name,
            "reason": "path not present in delivery worktree %s; the report "
                      "declares it inside another repo (see repo_reference assets)"
                      % ROOT.name,
            "same_basename_hits": hits}


def locate(md: str, token: str, line_no: int | None, lines) -> dict:
    """Pick the most precise quote for `token` and measure its span in `md`."""
    candidates = []
    if line_no and 1 <= line_no <= len(lines) and token in lines[line_no - 1]:
        candidates.append(("line", lines[line_no - 1]))
    candidates.append(("token", token))
    chosen = None
    for form, quote in candidates:
        if quote in md:
            n = md.count(quote)
            chosen = {"form": form, "quote": quote, "occurrences": n}
            if n == 1:
                break
    if chosen is None:
        raise SystemExit("locator not found in markdown: %r" % token)
    start = md.index(chosen["quote"])
    end = start + len(chosen["quote"])
    return {"method": "char_span",
            "start_char": start,
            "end_char": end,
            "start_line": md.count("\n", 0, start) + 1,
            "end_line": md.count("\n", 0, end - 1) + 1,
            "quote": chosen["quote"],
            "unique": chosen["occurrences"] == 1,
            "quote_form": chosen["form"],
            "occurrences_in_source": chosen["occurrences"]}


# ------------------------------------------------------------------- manifest
def build_manifest(record: dict) -> dict:
    md = record.get("markdown") or ""
    raw = md.encode("utf-8")
    lines = md.rstrip("\n").split("\n")
    digest = sha256_hex(raw)

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_bytes(raw)

    hash_match = digest == CONTRACT_SOURCE_HASH
    if not hash_match:
        raise SystemExit("source hash mismatch: %s != contract %s"
                         % (digest, CONTRACT_SOURCE_HASH))
    chars_match = len(md) == CONTRACT_CHARS
    if not chars_match:
        raise SystemExit("source char count mismatch: %d != contract %d"
                         % (len(md), CONTRACT_CHARS))

    assets = []

    def push(asset_class, label, section, locator, resolution, check, note):
        assets.append({
            "asset_id": "A%02d" % (len(assets) + 1),
            "asset_class": asset_class,
            "label": label,
            "in_report_section": section,
            "locator": locator,
            "resolution": resolution,
            "resolution_check": check,
            "note": note,
        })

    # ---- A01 the source asset itself (this is what the contract asks to pin)
    push("report_markdown", "report-%s-markdown" % REPORT_ID,
         "document (whole markdown field)",
         {"method": "document", "start_char": 0, "end_char": len(md),
          "start_line": 1, "end_line": len(lines),
          "quote": lines[0], "unique": md.count(lines[0]) == 1},
         "resolved_in_source",
         {"check": "sha256(UTF-8 bytes) of GET /api/v1/tensor/reports/%s markdown "
                   "== contract source_hash, and len(markdown) == contract chars"
                   % REPORT_ID, "result": "resolved"},
         "hash %s, %d chars / %d bytes / %d lines; byte copy runs/%s/source_%s.md"
         % (digest, len(md), len(raw), len(lines), PACKAGE_ID, REPORT_ID))

    # ---- platform-side figure metadata (names/captions only; no payload exposed)
    for fig in record.get("figures") or []:
        name = fig.get("name") or ""
        st, body = _get("/tensor/reports/%s/figures/%s" % (REPORT_ID, name), _login())
        img_line = next((i for i, ln in enumerate(lines, start=1)
                         if "![%s]" % name in ln and IMG_RE.search(ln)), None)
        loc = locate(md, name, img_line, lines) if name in md else None
        push("platform_figure", name,
             "section 4 (结果图) + record.figures",
             loc or {"method": "document", "start_char": 0, "end_char": len(md),
                     "start_line": 1, "end_line": len(lines),
                     "quote": lines[0], "unique": md.count(lines[0]) == 1},
             "referenced_unresolved",
             {"check": "GET /api/v1/tensor/reports/%s/figures/%s -> http_status %d "
                       "(%d bytes)" % (REPORT_ID, name, st, len(body)),
              "result": "unresolved" if st != 200 else "present"},
             "caption: %s" % (fig.get("caption") or "").replace("\n", " ")[:200]
             + "; same figure also declared as an on-disk relative path in section 4 "
               "(separate asset row: platform metadata vs filesystem reference)"
             + ("; figure endpoint returned no byte payload, so no figure hash is claimed"
                if st != 200 else ""))

    # ---- body-declared artifacts: figures on disk, results.json, scripts, tests
    for ref in scan_refs(lines):
        loc = locate(md, ref["token"], ref["line"], lines)
        res = resolve_in_worktree(ref["token"])
        push(ref["kind"], ref["token"],
             "line %d" % loc["start_line"],
             loc,
             "resolved_in_source" if res["status"] == "resolved" else "referenced_unresolved",
             {"check": res["via"], "result": "present" if res["status"] == "resolved"
                                             else "unresolved"},
             ("reference form %s; %s" % (ref["form"],
              "present in worktree" if res["status"] == "resolved"
              else res["reason"] + ("; same basename elsewhere: %s"
                                    % res["same_basename_hits"]
                                    if res["same_basename_hits"] else ""))))

    # ---- repos and dotted symbols are registered, not opened
    for ref in scan_repos(lines) + scan_symbols(lines):
        loc = locate(md, ref["token"], ref["line"], lines)
        push(ref["kind"], ref["token"], "line %d" % loc["start_line"], loc,
             "referenced_unresolved",
             {"check": "named in report prose only; registration step does not open "
                       "the owning repository/module", "result": "unresolved"},
             "declared_only: existence is not asserted by this package")

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise SystemExit("duplicate asset ids: %s" % dupes)

    by_class, by_resolution = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_resolution[a["resolution"]] = by_resolution.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "source": {
            "report_id": REPORT_ID,
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest[len("sha256:"):],
            "source_hash": digest,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_match": hash_match,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": chars_match,
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "has_trailing_newline": md.endswith("\n"),
            "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
            "fetched_via": "GET /api/v1/tensor/reports/%s (Authorization: Bearer)"
                           % REPORT_ID,
            "title": record.get("title"),
            "contract_title": CONTRACT_TITLE,
            "title_matches_contract": record.get("title") == CONTRACT_TITLE,
            "scenario_key": record.get("scenario_key"),
            "contract_scenario_key": CONTRACT_SCENARIO,
            "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            "platform_mission_id": record.get("mission_id"),
            "platform_status": record.get("status"),
            "platform_tags": record.get("tags") or [],
            "platform_figures": record.get("figures") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_resolution,
            "resolved_in_source": by_resolution.get("resolved_in_source", 0),
            "referenced_unresolved": by_resolution.get("referenced_unresolved", 0),
            "declared_absent": by_resolution.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "claims_note": ("empty by contract: objective.classify_report_type=false and "
                        "this work package is registration only -- no extraction, no "
                        "verified marks"),
        "integrity": {
            "quote_uniqueness": all(a["locator"]["unique"] for a in assets),
            "non_unique_quotes": [a["asset_id"] for a in assets if not a["locator"]["unique"]],
            "hash_recomputed_locally": True,
            "hash_matches_contract": hash_match,
            "ids_unique": not dupes,
            "no_writes_outside_worktree": True,
            "no_verified_marks": True,
        },
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


# ------------------------------------------------------------------- envelope
def build_envelope() -> dict:
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
            "notes": ("hash recomputed from GET /api/v1/tensor/reports/%s markdown "
                      "(UTF-8 bytes) and matched byte-for-byte against contract "
                      "source_hash %s" % (REPORT_ID, CONTRACT_SOURCE_HASH)),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n")
    return env


# ------------------------------------------------------------------- verify
def verify() -> dict:
    from jsonschema import Draft7Validator, Draft202012Validator

    checks = []
    manifest = json.loads(MANIFEST.read_text())
    envelope = json.loads(ENVELOPE.read_text())
    record = fetch_record()
    md = record["markdown"]
    digest = sha256_hex(md.encode("utf-8"))

    def add(cid, desc, ok, evidence):
        checks.append({"check_id": cid, "description": desc,
                       "result": "pass" if ok else "fail", "evidence": evidence})

    # 1 valid_json
    parsed = 0
    for p in (MANIFEST, ENVELOPE):
        json.loads(p.read_text())
        parsed += 1
    add("valid_json", "every emitted artefact parses as JSON",
        parsed == 2, {"files": [str(MANIFEST.relative_to(ROOT)),
                                str(ENVELOPE.relative_to(ROOT))], "parsed": parsed})

    # 2 schema_pass (manifest vs pinned schema, envelope vs platform schema)
    m_err = sorted(Draft7Validator(json.loads(MANIFEST_SCHEMA.read_text()))
                   .iter_errors(manifest), key=lambda e: list(e.path))
    e_err = sorted(Draft202012Validator(json.loads(ENVELOPE_SCHEMA.read_text()))
                   .iter_errors(envelope), key=lambda e: list(e.path))
    add("schema_pass", "asset_manifest validates against the pinned schema; the "
                       "result envelope validates against schemas/kf_result.v1.schema.json",
        not m_err and not e_err,
        {"manifest_schema": str(MANIFEST_SCHEMA.relative_to(ROOT)),
         "manifest_errors": ["%s: %s" % ("/".join(map(str, e.path)), e.message)
                             for e in m_err[:10]],
         "envelope_schema": str(ENVELOPE_SCHEMA.relative_to(ROOT)),
         "envelope_errors": ["%s: %s" % ("/".join(map(str, e.path)), e.message)
                             for e in e_err[:10]]})

    # 3 source_locator_resolvable: re-resolve every locator against the live text
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        if loc["method"] == "document":
            # a document locator covers the whole markdown field; its end_line is the
            # logical line count (md.rstrip("\n")), not the raw newline count
            ok = (s == 0 and e == len(md) and loc["quote"] in md
                  and loc["start_line"] == 1
                  and loc["end_line"] == md.rstrip("\n").count("\n") + 1)
        else:
            ok = (0 <= s < e <= len(md) and md[s:e] == loc["quote"]
                  and loc["start_line"] == md.count("\n", 0, s) + 1
                  and loc["end_line"] == md.count("\n", 0, e - 1) + 1)
        if not ok:
            bad.append(a["asset_id"])
    add("source_locator_resolvable",
        "every asset locator re-resolves on the live markdown: md[start:end] == quote "
        "and the declared line numbers match", not bad,
        {"assets_checked": len(manifest["assets"]), "failures": bad,
         "method": "re-fetch /tensor/reports/9632 and slice md[start_char:end_char]"})

    # 4 source_hash_matches
    add("source_hash_matches",
        "sha256 of the live markdown UTF-8 bytes equals the contract source_hash",
        digest == CONTRACT_SOURCE_HASH and manifest["source"]["hash_match"]
        and envelope["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH,
        {"recomputed": digest, "contract": CONTRACT_SOURCE_HASH,
         "chars": len(md), "contract_chars": CONTRACT_CHARS,
         "chars_match": len(md) == CONTRACT_CHARS,
         "envelope_hash": envelope["provenance"]["source_hash"],
         "local_copy_matches_live": SOURCE_COPY.read_bytes() == md.encode("utf-8")})

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    labels = [a["label"] for a in manifest["assets"]]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    dup_labels = sorted({i for i in labels if labels.count(i) > 1})
    add("no_duplicate_ids", "asset_id values (and asset labels) are unique",
        not dup_ids and not dup_labels and len(set(ids)) == len(ids),
        {"assets": len(ids), "unique_ids": len(set(ids)),
         "duplicate_ids": dup_ids, "duplicate_labels": dup_labels})

    # 6 claims carry evidence or explicit status (empty list = legitimate here)
    claims = manifest["claims"] + envelope.get("claims", [])
    offenders = [c.get("claim_id") for c in claims
                 if not (c.get("evidence") or c.get("status"))]
    add("all_claims_have_evidence_or_explicit_unresolved_status",
        "each claim carries an evidence locator or an explicit status; an empty "
        "claims array is a complete result for a registration package",
        not offenders, {"claims": len(claims), "offenders": offenders,
                        "note": "claims=[] by contract (classify_report_type=false)"})

    summary = {
        "package_id": PACKAGE_ID, "report_id": REPORT_ID,
        "generated_at": utcnow(), "producer": PRODUCER,
        "checks": checks,
        "passed": sum(1 for c in checks if c["result"] == "pass"),
        "failed": sum(1 for c in checks if c["result"] == "fail"),
        "total": len(checks),
        "assets_registered": len(manifest["assets"]),
        "verification_authority": "platform gate (this file is a worker self-check only, "
                                  "no claim is marked verified)",
    }
    VERIFICATION.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    if summary["failed"]:
        raise SystemExit("verification failed: %s"
                         % [c["check_id"] for c in checks if c["result"] == "fail"])
    return summary


# --------------------------------------------------------------------- figure
def figure() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text())
    md = SOURCE_COPY.read_text(encoding="utf-8")
    total = len(md)
    colors = {"resolved_in_source": "#1b7837", "referenced_unresolved": "#c05800",
              "declared_absent": "#888888"}
    fig, ax = plt.subplots(figsize=(11, max(4.0, 0.32 * len(manifest["assets"]) + 1.6)))
    for i, a in enumerate(manifest["assets"]):
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        ax.barh(i, max(e - s, total * 0.004), left=s, height=0.6,
                color=colors[a["resolution"]], alpha=0.85,
                edgecolor="black", linewidth=0.4)
        ax.text(total * 1.005, i, a["asset_class"], va="center", fontsize=7)
    ax.set_yticks(range(len(manifest["assets"])))
    ax.set_yticklabels([a["label"][:52] for a in manifest["assets"]], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("character offset in report 9632 markdown (%d chars)" % total)
    ax.set_title("wp-9632-01 asset registration: locator spans, %d assets, "
                 "color = resolution" % len(manifest["assets"]), fontsize=10)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.85)
               for c in colors.values()]
    ax.legend(handles, list(colors), fontsize=7, loc="lower right")
    ax.set_xlim(0, total * 1.18)
    ax.text(0.0, -1.6, "source sha256 %s  (contract match: %s)"
            % (manifest["source"]["hash"][:16] + "...", manifest["source"]["hash_match"]),
            fontsize=7, family="monospace")
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "wp9632_01_source_locator_map.png"
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return str(out.relative_to(ROOT))


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("build", "all"):
        m = build_manifest(fetch_record())
        print("manifest: %s assets, hash_match=%s"
              % (m["counts"]["assets"], m["source"]["hash_match"]))
    if cmd in ("envelope", "all"):
        build_envelope()
        print("envelope: %s" % ENVELOPE.relative_to(ROOT))
    if cmd in ("verify", "all"):
        s = verify()
        print("verify: %d/%d pass" % (s["passed"], s["total"]))
    if cmd in ("figure", "all"):
        print("figure: %s" % figure())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))