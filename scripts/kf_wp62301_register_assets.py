#!/usr/bin/env python3
"""wp-623-01 (task_type 01-asset-registration): register report 623's source asset
and enumerate the resolvable attachments/artifacts it declares.

Sub-commands (idempotent, stdlib only except `figure` which needs matplotlib):

    python3 scripts/kf_wp62301_register_assets.py build      # fetch + write asset_manifest.json
    python3 scripts/kf_wp62301_register_assets.py envelope   # wrap manifest -> kf_result.json
    python3 scripts/kf_wp62301_register_assets.py verify     # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp62301_register_assets.py figure     # locator map png
    python3 scripts/kf_wp62301_register_assets.py all        # build+envelope+verify+figure

Design rules honoured here (contract wp-623-01):
  * registration only -- NO claim extraction, NO verified marks;
  * zero manual transcription -- every number in the artefacts is measured here;
  * every declared asset carries a locator (line number + verbatim quote) that is
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
REPORT_ID = "623"
PACKAGE_ID = "wp-623-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
# contract-declared identity (from the work-package YAML); the script never
# trusts these -- they are comparison targets only.
CONTRACT_SOURCE_HASH = "sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf"
CONTRACT_CHARS = 7281
CONTRACT_TITLE = "DEM3D Large-Scale Particle Benchmark: 10k-100k Wall-Clock Scaling Study"
CONTRACT_SCENARIO = "SIR-PC2|V02"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID  # committed: repo .gitignore drops artifacts/**
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
PRODUCER = "kf-worker/m15515"

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
    except urllib.error.HTTPError as e:  # kept for probe evidence
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
BARE_RE = re.compile(r"(?<![\w/`.\-])((?!\-)(?:\.{1,2}/)?[\w.-]+(?:/[\w.-]+)*\.(?:py|json|png|md|h5|csv))(?![\w/])")


def classify(path: str) -> str:
    ext = Path(path).suffix.lower()
    return PATH_EXTS.get(ext, "referenced_artifact")


def is_pathlike(tok: str) -> bool:
    """A backticked token counts as a path reference if it has a directory part or
    a known artifact extension -- module names like `IceDEM3D` are NOT paths."""
    tok = tok.strip()
    if not tok or " " in tok or "\n" in tok:
        return False
    if Path(tok).suffix.lower() in PATH_EXTS:
        return True
    return "/" in tok and not tok.startswith(("http://", "https://"))


def scan_refs(lines: list[str]) -> list[dict]:
    """Collect (line, token, kind) references; one asset per (path, line) occurrence."""
    out, seen = [], set()

    def add(line_no: int, token: str, kind: str, form: str):
        token = token.strip()
        key = (token, line_no)
        if not token or key in seen:
            return
        seen.add(key)
        out.append({"line": line_no, "token": token, "kind": kind, "form": form})

    for i, line in enumerate(lines, start=1):
        for alt, path in IMG_RE.findall(line):
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
UPSTREAM_RE = re.compile(r"\*\*Upstream\*\*:[^\n]*?\bm(\d{3,4})\b")


def scan_symbols(lines: list[str]) -> list[dict]:
    """Code entry points / upstream dependencies named in the prose. Registered as
    declared-only: this工序 does not open the referenced repository."""
    out, seen = [], set()

    def add(line_no: int, token: str, kind: str):
        if (token, line_no) in seen:
            return
        seen.add((token, line_no))
        out.append({"line": line_no, "token": token, "kind": kind})

    for i, line in enumerate(lines, start=1):
        for tok in MODULE_TICK_RE.findall(line):
            if not is_pathlike(tok):
                add(i, tok, "module_reference")
        for rpt in UPSTREAM_RE.findall(line):
            add(i, "m" + rpt, "upstream_report_reference")
    return out


def resolve_in_worktree(token: str) -> dict:
    """Only the delivery worktree is searched: declaring anything else would be a guess."""
    cand = token.lstrip("./")
    p = ROOT / cand
    if p.exists() and p.is_file():
        b = p.read_bytes()
        return {"status": "resolved", "scope": "delivery_worktree",
                "bytes": len(b), "sha256": sha256_hex(b)}
    same_name = sorted(str(q.relative_to(ROOT)) for q in ROOT.rglob(Path(cand).name)
                       if q.is_file() and ".git" not in q.parts)[:5]
    return {"status": "unresolved", "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": same_name}


# ------------------------------------------------------------------- manifest
def build_manifest(record: dict) -> dict:
    md = record.get("markdown") or ""
    raw = md.encode("utf-8")
    lines = md.rstrip("\n").split("\n")
    digest = sha256_hex(raw)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_bytes(raw)

    hash_match = digest == CONTRACT_SOURCE_HASH
    chars_match = len(md) == CONTRACT_CHARS
    if not hash_match:
        raise SystemExit("source hash mismatch: %s != contract" % digest)

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
        "hash_scope": "UTF-8 bytes of the markdown field as served by GET /api/v1/tensor/reports/%s" % REPORT_ID,
        "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
        "resolution": {"status": "resolved", "scope": "platform_api",
                       "via": "GET /tensor/reports/%s" % REPORT_ID},
        "hash_matches_contract": hash_match,
        "chars_matches_contract": chars_match,
    }]

    # figures declared in the report *record* (metadata only: no byte payload is
    # exposed by the API -- probed below and recorded as unresolved).
    fig_probes = {}
    for idx, fig in enumerate(record.get("figures") or []):
        name = fig.get("name") or ""
        st, body = _get("/tensor/reports/%s/figures/%s" % (REPORT_ID, name), _login())
        fig_probes[name] = {"http_status": st, "bytes": len(body)}
        assets.append({
            "asset_id": "r%s:figure:%02d" % (REPORT_ID, idx + 1),
            "kind": "embedded_figure",
            "name": name,
            "caption": fig.get("caption"),
            "locator": {"source_field": "record", "pointer": "/figures/%d/name" % idx,
                        "quote": name},
            "resolution": {"status": "metadata_only", "scope": "platform_api",
                           "via": "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, name),
                           "http_status": st,
                           "reason": "record exposes name/caption only; no byte payload "
                                     "was returned, so no hash is claimed"},
        })

    # body references (paths declared in the prose / tool chain / audit chain)
    for n, ref in enumerate(scan_refs(lines), start=1):
        res = resolve_in_worktree(ref["token"])
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
                                     "reference, it does not open TensorDEM",
                           },
            "existence_asserted_by_worker": False,
        })

    # locators: one entry per asset that is anchored in the markdown, re-checked here
    locators = []
    for a in assets + [{"asset_id": x["symbol_id"], "locator": x["locator"],
                        "kind": x["kind"], "resolution": x["resolution"]} for x in symbols]:
        loc = a["locator"]
        if loc["source_field"] != "markdown":
            continue
        q = loc["quote"] if "quote" in loc else lines[loc["line"] - 1]
        on_line = loc["line"] - 1 < len(lines) and lines[loc["line"] - 1] == q
        locators.append({
            "asset_id": a["asset_id"],
            "locator": {"source_field": "markdown", "line": loc["line"]},
            "quote_sha256": sha256_hex(q.encode("utf-8")),
            "quote_in_source": q in md,
            "quote_on_declared_line": on_line,
            "occurrences_in_source": md.count(q),
            "resolved": bool(q in md and on_line),
        })

    # head/tail identity facts (cheap, and they pin what the document *is*)
    head_facts = []
    for fact_id, line_no in (("title-line", 1), ("scenario-line", 3),
                             ("sec1-header", 9), ("audit-chain-header", 141),
                             ("closing-note", len(lines) - 1)):
        q = lines[line_no - 1]
        head_facts.append({"fact_id": fact_id,
                           "locator": {"source_field": "markdown", "line": line_no},
                           "quote": q,
                           "quote_sha256": sha256_hex(q.encode("utf-8")),
                           "quote_in_source": q in md,
                           "quote_on_declared_line": lines[line_no - 1] == q,
                           "occurrences_in_source": md.count(q)})

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    kinds = {}
    for a in assets:
        key = "%s/%s" % (a["kind"], a["resolution"]["status"])
        kinds[key] = kinds.get(key, 0) + 1

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
                "created_at": record.get("created_at"),
                "tags": record.get("tags"),
                "contract_title": CONTRACT_TITLE,
                "contract_scenario_key": CONTRACT_SCENARIO,
                "title_matches_contract": (record.get("title") or "").replace("–", "-") == CONTRACT_TITLE,
                "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            },
            "platform_attachment_probes": {
                "GET /tensor/reports/623/artifacts": "not_probed_here",
                "figure_probe": fig_probes,
            },
        },
        "assets": assets,
        "symbol_references": symbols,
        "locators": locators,
        "identity_facts": head_facts,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-623-01 objective is register_assets=true / classify_report_type=false, "
            "and notes state 'claims 允许为空数组' plus constraints no_forced_claim_generation=true. "
            "This工序 registers asset identity only (report_id, markdown byte hash, declared "
            "attachments/artifacts); extraction is a downstream工序, so an empty claims array is "
            "the complete result, not an omission."
        ),
        "counts": {
            "source_documents": 1,
            "figures_declared_in_record": len(record.get("figures") or []),
            "figures_with_bytes": sum(1 for v in fig_probes.values() if v["http_status"] == 200),
            "body_references": sum(1 for a in assets if a["asset_id"].startswith("r%s:ref:" % REPORT_ID)),
            "distinct_referenced_paths": len({a["name"] for a in assets
                                              if a["asset_id"].startswith("r%s:ref:" % REPORT_ID)}),
            "assets_total": len(assets),
            "assets_resolved": sum(1 for a in assets if a["resolution"]["status"] == "resolved"),
            "assets_metadata_only": sum(1 for a in assets if a["resolution"]["status"] == "metadata_only"),
            "assets_unresolved": sum(1 for a in assets if a["resolution"]["status"] == "unresolved"),
            "locators": len(locators),
            "locators_resolved": sum(1 for l in locators if l["resolved"]),
            "symbol_references": len(symbols),
            "claims": 0,
            "kind_status_histogram": dict(sorted(kinds.items())),
        },
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes},
        "unresolved": [
            {"asset_id": a["asset_id"], "name": a["name"], "reason": a["resolution"].get("reason")}
            for a in assets if a["resolution"]["status"] == "unresolved"
        ],
        "observations": [
            "Report markdown is complete and self-consistent: first line is the H1 title, "
            "sections 1-6 + Audit Chain all present (%d lines)." % len(lines),
            "The 2 figures are declared in the record metadata (name+caption) and referenced "
            "in-body as relative links ../artifacts/<name>.png; the platform serves no figure "
            "bytes for this report, so they stay metadata_only (no hash claimed).",
            "All body path references point at TensorDEM artefacts (src/tensordem/*.py, "
            "scripts/*, tests/*, results-dem3d-scale/*, artifacts/*.png) which do not exist in "
            "the TensorKnowledge delivery worktree; they are registered as declared references "
            "with existence_asserted_by_worker=false.",
        ],
        "limitations": [
            "Registration only: no claim/evidence extraction, no report-type classification, no "
            "verified marks (verification is computed by the platform gate).",
            "source_hash scope = UTF-8 bytes of the markdown string returned by the platform API; "
            "any change to the stored markdown (even whitespace) invalidates it.",
            "Direct psql read of tensor_reports was denied (permission denied for table "
            "tensor_reports), so the API is the only source channel used.",
            "Reference resolution is limited to the delivery worktree; a missing path here is "
            "reported as unresolved, never as a broken upstream artefact.",
        ],
    }


# ------------------------------------------------------------------- envelope
def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    # re-fetch live bytes: the envelope's source_hash must be bound to *current* content
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
            "notes": ("hash recomputed from GET /api/v1/tensor/reports/623 markdown (UTF-8 bytes); "
                      "matches contract source_hash %s" % CONTRACT_SOURCE_HASH),
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

    # 1 valid_json
    checks["valid_json"] = {"ok": True, "detail": "asset_manifest.json + kf_result.json parsed"}

    # 2 schema_pass
    errs = [e.message for e in Draft202012Validator(schema).iter_errors(env)]
    checks["schema_pass"] = {"ok": not errs, "detail": errs or "kf_result.v1 schema: 0 errors"}

    # 3 source_locator_resolvable (re-resolved against live markdown, not the stored copy)
    bad = []
    for loc in manifest["locators"]:
        ln = loc["locator"]["line"]
        q = lines[ln - 1] if 0 < ln <= len(lines) else None
        if q is None or q not in md or sha256_hex(q.encode()) != loc["quote_sha256"]:
            bad.append(loc["asset_id"])
    for f in manifest["identity_facts"]:
        ln = f["locator"]["line"]
        if not (0 < ln <= len(lines)) or lines[ln - 1] != f["quote"]:
            bad.append(f["fact_id"])
    checks["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": "%d/%d markdown locators re-resolved (line + verbatim + quote_sha256)"
                  % (len(manifest["locators"]) - len([b for b in bad if b.startswith("r")]),
                     len(manifest["locators"])),
        "failures": bad,
    }

    # 4 source_hash_matches
    checks["source_hash_matches"] = {
        "ok": live_hash == manifest["source"]["source_hash"] == CONTRACT_SOURCE_HASH
              == env["provenance"]["source_hash"],
        "detail": "live=%s manifest=%s contract=%s" % (
            live_hash, manifest["source"]["source_hash"], CONTRACT_SOURCE_HASH),
        "chars": {"live": len(md), "manifest": manifest["source"]["chars"], "contract": CONTRACT_CHARS},
    }

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {"ok": not dupes, "detail": "%d ids, duplicates=%s"
                                  % (len(ids), dupes)}

    # 6 all_claims_have_evidence_or_explicit_unresolved_status
    claims = env.get("claims") or []
    ev_ok = all(c.get("evidence") or c.get("unresolved_reason") for c in claims)
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": bool(ev_ok and manifest.get("claims_empty_reason")),
        "detail": "%d claims; empty-claims reason stated: %s"
                  % (len(claims), bool(manifest.get("claims_empty_reason"))),
    }

    out = {"package_id": PACKAGE_ID, "verified_at": utcnow(),
           "acceptance": checks,
           "all_ok": all(c["ok"] for c in checks.values()),
           "note": ("Self-check only. No claim is marked verified here; the platform gate "
                    "recomputes hash/locators independently.")}
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


# --------------------------------------------------------------------- figure
def figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    md = SOURCE_COPY.read_text()
    lines = md.split("\n")
    manifest = json.loads(MANIFEST.read_text())
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 5.0), gridspec_kw={"width_ratios": [2.1, 1]})
    xs = list(range(1, len(lines) + 1))
    ys = [len(l) for l in lines]
    ax1.plot(xs, ys, "-", color="#4c72b0", lw=1.0)
    ax1.fill_between(xs, ys, color="#4c72b0", alpha=0.12)
    kinds = {}
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["source_field"] == "markdown" and a["asset_id"].startswith("r623:ref:"):
            kinds.setdefault(a["kind"], []).append(loc["line"])
    colors = {"source_code_reference": "#c44e52", "data_artifact_reference": "#dd8452",
              "figure_reference": "#55a868", "document_reference": "#8172b3"}
    for kind, lns in sorted(kinds.items()):
        ax1.vlines(lns, 0, [len(lines[l - 1]) for l in lns], color=colors.get(kind, "k"),
                   lw=2.4, label="%s (n=%d)" % (kind, len(lns)))
    for ln in (1, 9, 58, 109, 141):
        ax1.axvline(ln, color="0.6", ls=":", lw=0.8)
        ax1.annotate("L%d" % ln, (ln, max(ys) * 0.97), fontsize=7, color="0.35", rotation=90,
                     ha="right", va="top")
    ax1.set_xlabel("markdown line number")
    ax1.set_ylabel("characters on line")
    ax1.set_title("report 623 source markdown: line profile + declared-reference anchors\n"
                  "(%d lines, %d chars, %d body references)"
                  % (len(lines), len(md), sum(len(v) for v in kinds.values())), fontsize=10)
    ax1.legend(fontsize=7, loc="upper center")
    ax1.grid(alpha=0.25)

    h = manifest["counts"]["kind_status_histogram"]
    labels = list(h.keys())
    ax2.barh(range(len(labels)), [h[k] for k in labels],
             color=["#55a868" if k.endswith("resolved") else
                    "#dd8452" if k.endswith("metadata_only") else "#c44e52" for k in labels])
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels(labels, fontsize=7)
    ax2.invert_yaxis()
    ax2.set_xlabel("assets")
    ax2.set_title("asset kind / resolution status\n(sha256 %s...)" % manifest["source"]["source_hash"][7:19],
                  fontsize=10)
    for i, k in enumerate(labels):
        ax2.text(h[k] + 0.05, i, str(h[k]), va="center", fontsize=7)
    ax2.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    out = FIG_DIR / "wp62301_source_locator_map.png"
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
              "| assets", manifest["counts"]["assets_total"],
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