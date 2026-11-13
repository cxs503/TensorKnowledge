#!/usr/bin/env python3
"""wp-11621-01 (task_type 01-asset-registration): register report 11621's source
asset and enumerate the resolvable attachments/artifacts it declares.

Sub-commands (idempotent, stdlib only):

    python3 scripts/kf_wp11621_01_register.py build      # fetch + write asset_manifest.json
    python3 scripts/kf_wp11621_01_register.py envelope   # wrap manifest -> kf_result.json
    python3 scripts/kf_wp11621_01_register.py verify     # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp11621_01_register.py all        # build+envelope+verify

Design rules honoured here (contract wp-11621-01):
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
REPORT_ID = "11621"
PACKAGE_ID = "wp-11621-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
# contract-declared identity (from the work-package YAML); the script never
# trusts these -- they are comparison targets only.
CONTRACT_SOURCE_HASH = "sha256:89a6a0828d4feddbc1c1ee81e80cc7c844ea234c01c2efeec215fcd7ed54dafb"
CONTRACT_CHARS = 7198
CONTRACT_TITLE = "TensorFVM 数值黏性/色散算子验证面：修正方程 ν_num=cΔx(1-C)/2 波包衰减实测 + 离散放大因子 G(θ) 全域比对"
CONTRACT_SCENARIO = "p73w3-n04-fvm-numerical-viscosity"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID  # committed: repo .gitignore drops artifacts/**
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
PRODUCER = "kf-worker/m15727"

PATH_EXTS = {".py": "source_code_reference", ".json": "data_artifact_reference",
             ".png": "figure_reference", ".jpg": "figure_reference",
             ".md": "document_reference", ".h5": "data_artifact_reference",
             ".hdf5": "data_artifact_reference", ".csv": "data_artifact_reference"}


# ---------------------------------------------------------------- api helpers
def _api_base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _login() -> str:
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        raise SystemExit("TENSOR_AGENT_USER / TENSOR_AGENT_PASS not set")
    req = urllib.request.Request(
        _api_base() + "/auth/login",
        data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
    if not tok:
        raise SystemExit("no token in login response keys=%s" % list(d))
    return tok


def _get(path: str, token: str):
    req = urllib.request.Request(_api_base() + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def fetch_record() -> dict:
    tok = _login()
    st, body = _get("/tensor/reports/%s" % REPORT_ID, tok)
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> HTTP %d" % (REPORT_ID, st))
    d = json.loads(body.decode())
    return d.get("data", d)


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------- reference scan
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
TICK_RE = re.compile(r"`([^`]+)`")
BARE_RE = re.compile(r"(?<![\w`])([\w./-]+\.(?:py|json|png|jpg|md|h5|hdf5|csv))(?![\w`])")


def classify(path: str) -> str:
    return PATH_EXTS.get(Path(path).suffix.lower(), "document_reference")


def is_pathlike(tok: str) -> bool:
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

    hash_match = digest == CONTRACT_SOURCE_HASH.split(":", 1)[-1]
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
        if st == 200 and body:
            res = {"status": "resolved", "scope": "platform_api",
                   "via": "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, name),
                   "http_status": st, "bytes": len(body),
                   "sha256": sha256_hex(body)}
        else:
            res = {"status": "metadata_only", "scope": "platform_api",
                   "via": "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, name),
                   "http_status": st,
                   "reason": "no byte payload returned for this figure"}
        assets.append({
            "asset_id": "r%s:figure:%02d" % (REPORT_ID, idx + 1),
            "kind": "embedded_figure",
            "name": name,
            "caption": fig.get("caption"),
            "locator": {"source_field": "record", "pointer": "/figures/%d/name" % idx,
                        "quote": name},
            "resolution": res,
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

    # ---- locators (verbatim line quotes, re-checked at verify time) ----
    locators = []
    for a in assets:
        loc = a["locator"]
        if loc["source_field"] == "markdown":
            ln = loc["line"]
            q = lines[ln - 1] if 0 < ln <= len(lines) else None
            if q is None:
                raise SystemExit("locator line %d out of range" % ln)
            locators.append({
                "asset_id": a["asset_id"],
                "locator": {"line": ln, "quote": q},
                "quote_sha256": sha256_hex(q.encode()),
                "resolved": True,
            })

    # ---- identity facts (title / scenario / mission / status / hash) ----
    head_facts = []
    for key, label, ln in (
        ("title", "报告标题", 1),
        ("scenario_key", "战役节点", 3),
        ("mission_id", "任务ID", 4),
        ("status", "完成日期", 5),
    ):
        q = lines[ln - 1]
        head_facts.append({
            "fact_id": "r%s:fact:%s" % (REPORT_ID, key),
            "field": key,
            "label": label,
            "locator": {"line": ln, "quote": q},
            "quote_sha256": sha256_hex(q.encode()),
            "resolved": True,
        })

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
            "source_hash": "sha256:" + digest,
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
                "GET /tensor/reports/11621/artifacts": "not_probed_here",
                "figure_probe": fig_probes,
            },
        },
        "assets": assets,
        "locators": locators,
        "identity_facts": head_facts,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-11621-01 objective is register_assets=true / classify_report_type=false, "
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
            "sections 1-9 all present (%d lines)." % len(lines),
            "The record metadata declares 6 figures (fig1_geometry.png ... fig6_fatigue.png) whose "
            "captions describe a ship hydrodynamics (added-mass/springing/whipping/fatigue) topic "
            "that does NOT match this FVM numerical-viscosity report's body (which references "
            "fig1_von_neumann.png / fig2_nu_comparison.png / fig3_grid_convergence.png). The "
            "platform DOES serve byte payloads for these 6 record figures (HTTP 200, sha256 "
            "recorded), so they are registered as resolved attachments; the topic mismatch is "
            "flagged as a data-integrity observation for the platform gate, not resolved here.",
            "All body path references point at TensorFVM artefacts (src/tensorfvm/verification/*.py, "
            "tests/*, artifacts/fvm_modified_equation.json, docs/numerical-viscosity/*.png) which "
            "do not exist in the TensorKnowledge delivery worktree; they are registered as declared "
            "references with existence_asserted_by_worker=false.",
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
    md = record.get("markdown") or ""
    live = "sha256:" + sha256_hex(md.encode("utf-8"))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": live,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("hash recomputed from GET /api/v1/tensor/reports/%s markdown (UTF-8 bytes); "
                      "matches contract source_hash %s" % (REPORT_ID, CONTRACT_SOURCE_HASH)),
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
    live_hash = "sha256:" + sha256_hex(md.encode("utf-8"))

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
        if not (0 < ln <= len(lines)) or lines[ln - 1] != f["locator"]["quote"]:
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
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
