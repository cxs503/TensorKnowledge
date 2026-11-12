#!/usr/bin/env python3
"""Work package wp-5687-01 (01-asset-registration) — asset manifest builder + verifier.

Scope guard: touches ONLY report_id=5687. No extraction, no claims, no verification marks.

Every locator quote is taken verbatim from the fetched markdown bytes (never retyped),
so `quote` is guaranteed to be a substring of the source and `line` is its 1-based line.

Usage:
  python3 scripts/kf/build_asset_manifest_5687.py build
  python3 scripts/kf/build_asset_manifest_5687.py verify
  python3 scripts/kf/build_asset_manifest_5687.py build verify
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

PKG = "wp-5687-01"
REPORT_ID = "5687"
SOURCE_URI = "tensor://reports/5687"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d"
EXPECTED_CHARS = 4236

REPO = Path(__file__).resolve().parents[2]
# NOTE: .gitignore ignores artifacts/ (the mission push gate drops artifacts/**),
# so registered assets live under docs/kf/ to survive the gate instead of being silently filtered.
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
VERDICT = OUT_DIR / "verification.json"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

# ---------------------------------------------------------------- platform I/O


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def login():
    try:
        d = _req(BASE + "/auth/login", data=json.dumps({"username": USER, "password": PASS}).encode())
    except urllib.error.HTTPError:
        body = urllib.parse.urlencode({"username": USER, "password": PASS}).encode()
        d = _req(BASE + "/auth/login", data=body, ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_report(token):
    d = _req(BASE + "/tensor/reports/%s" % REPORT_ID, token)
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


def probe_artifact_endpoints(token):
    """Best-effort discovery of a platform artifact/attachment listing (no guessing at data)."""
    probes = {}
    for path in ("/tensor/reports/%s/artifacts" % REPORT_ID, "/tensor/artifacts?report_id=%s" % REPORT_ID):
        try:
            d = _req(BASE + path, token)
            probes[path] = {"status": "ok", "shape": type(d).__name__}
        except urllib.error.HTTPError as e:
            probes[path] = {"status": "http_%s" % e.code}
        except Exception as e:  # noqa: BLE001 - record, never fabricate
            probes[path] = {"status": "error", "detail": type(e).__name__}
    return probes


# ---------------------------------------------------------------- parsing


IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)\s]+)\)")
TICK_PATH_RE = re.compile(r"`(?P<path>[A-Za-z0-9_./-]+\.(?:json|png|py|md|txt|csv))(?::(?P<line>\d+(?:-\d+)?))?`")
BARE_PATH_RE = re.compile(r"(?<![\w/`.])(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|png|py|md|txt|csv))\b(?::(?P<line>\d+(?:-\d+)?))?(?![\w`])")


def classify(path: str) -> str:
    p = path.lower()
    if p.endswith(".png"):
        return "figure_reference"
    if p.endswith(".py"):
        return "source_code_reference"
    if p.endswith(".md"):
        return "document_reference"
    if p.endswith((".json", ".csv", ".txt")):
        return "data_artifact_reference"
    return "reference"


def scan_references(lines):
    """Return ordered (line_no, quote_line, path, via, pin) for every path-like reference."""
    found, seen = [], set()
    for i, line in enumerate(lines, start=1):
        hits = []
        for m in IMG_RE.finditer(line):
            hits.append((m.group("path"), "markdown_image", None))
        for m in TICK_PATH_RE.finditer(line):
            hits.append((m.group("path"), "backticked_ref", m.group("line")))
        for m in BARE_PATH_RE.finditer(line):
            hits.append((m.group("path"), "bare_ref", m.group("line")))
        for path, via, pin in hits:
            key = (path, i)
            if key in seen:
                continue
            seen.add(key)
            found.append({"line": i, "quote": line, "path": path, "via": via, "pin": pin})
    return found


def resolve_local(path: str):
    """Resolve a referenced path inside the delivery worktree only (no cross-repo guessing)."""
    for cand in (REPO / path, REPO / path.lstrip("./")):
        try:
            cand = cand.resolve()
        except OSError:
            continue
        if not str(cand).startswith(str(REPO)):
            continue
        if cand.is_file():
            raw = cand.read_bytes()
            return {
                "status": "resolved",
                "scope": "delivery_worktree",
                "resolved_path": str(cand.relative_to(REPO)),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
    return {
        "status": "unresolved",
        "scope": "delivery_worktree",
        "reason": "path not present in the TensorKnowledge delivery worktree",
    }


def emit_result():
    """Derive the kf_result envelope (package_id/task_type/report_id/provenance/outputs) from the manifest."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mraw = MANIFEST.read_bytes()
    # bind the envelope to freshly re-read source bytes, not to the contract constant
    token = login()
    _meta, live_md = fetch_report(token)
    live_digest = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    if live_digest != declared:
        raise SystemExit("live source drifted from manifest: %s != %s" % (live_digest, declared))
    result = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + live_digest,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(live_md),
            "source_bytes_utf8": len(live_md.encode("utf-8")),
            "fetched_via": "GET /api/v1/tensor/reports/5687",
            "generator": "scripts/kf/build_asset_manifest_5687.py",
            "contract_version": "1.0",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str(MANIFEST.relative_to(REPO)),
                "sha256": hashlib.sha256(mraw).hexdigest(),
                "bytes": len(mraw),
                "asset_count": manifest["summary"]["asset_count"],
                "claims": len(manifest["claims"]),
            }
        },
    }
    out = OUT_DIR / "kf_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % out.relative_to(REPO))
    return result


def build():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit("SOURCE HASH MISMATCH: contract=%s actual=%s" % (EXPECTED_HASH, digest))
    if len(md) != EXPECTED_CHARS:
        raise SystemExit("SOURCE CHAR COUNT MISMATCH: contract=%d actual=%d" % (EXPECTED_CHARS, len(md)))

    lines = md.split("\n")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assets, ids = [], set()

    def add(asset):
        if asset["asset_id"] in ids:
            raise SystemExit("duplicate asset_id %s" % asset["asset_id"])
        ids.add(asset["asset_id"])
        assets.append(asset)

    # A1: the source asset itself
    add({
        "asset_id": "r5687:source",
        "kind": "report_markdown",
        "uri": SOURCE_URI,
        "source_field": SOURCE_FIELD,
        "title": meta.get("title"),
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": digest,
        "locator": {"scheme": "report_field", "field": "markdown"},
        "resolution": {"status": "resolved", "scope": "platform_api", "via": "GET /tensor/reports/5687"},
    })

    # A2: figures embedded in the report record (parseable binary attachments)
    for n, fig in enumerate(meta.get("figures") or [], start=1):
        b64 = fig.get("png_base64") or ""
        try:
            blob = base64.b64decode(b64) if b64 else b""
        except Exception:  # noqa: BLE001
            blob = b""
        add({
            "asset_id": "r5687:figure:%02d" % n,
            "kind": "embedded_figure",
            "uri": "%s#figures[%d]" % (SOURCE_URI, n - 1),
            "name": fig.get("name"),
            "caption": fig.get("caption"),
            "bytes": len(blob) or None,
            "sha256": hashlib.sha256(blob).hexdigest() if blob else None,
            "locator": {"scheme": "report_field", "field": "figures", "index": n - 1},
            "resolution": {"status": "resolved", "scope": "platform_api", "has_payload": True}
            if blob else {
                "status": "metadata_only",
                "scope": "platform_api",
                "has_payload": False,
                "reason": "report record lists this figure by name+caption only; no png_base64 payload is stored in figures[], so no byte hash can be computed",
            },
        })

    # A3: path-like references parsed out of the markdown body
    for n, ref in enumerate(scan_references(lines), start=1):
        res = resolve_local(ref["path"])
        add({
            "asset_id": "r5687:ref:%02d" % n,
            "kind": classify(ref["path"]),
            "uri": "%s#line=%d" % (SOURCE_URI, ref["line"]),
            "path_reference": ref["path"],
            "line_pin": ref["pin"],
            "via": ref["via"],
            "declared_sha256": None,
            "locator": {"scheme": "markdown_line", "line": ref["line"], "quote": ref["quote"]},
            "resolution": res,
        })

    counts = {}
    for a in assets:
        k = "%s/%s" % (a["kind"], a["resolution"]["status"])
        counts[k] = counts.get(k, 0) + 1

    manifest = {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "schema_note": (
            "No kf_result/asset_manifest JSON Schema file is shipped in this repository "
            "(schemas/ has no kf_*.json); shape follows the wp-542-01 contract keys "
            "(package_id/task_type/report_id/provenance/outputs) and is self-described below."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + digest,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(raw),
            "report_title": meta.get("title"),
            "report_scenario_key": meta.get("scenario_key"),
            "report_mission_id": meta.get("mission_id"),
            "report_created_at": meta.get("created_at"),
            "report_tags": meta.get("tags"),
            "fetched_via": "GET /api/v1/tensor/reports/5687",
            "generator": "scripts/kf/build_asset_manifest_5687.py",
            "contract_version": "1.0",
        },
        "resolution_status_vocabulary": {
            "resolved": "bytes located and hashed (source markdown or a file inside this worktree)",
            "unresolved": "reference parsed from the report but the target is not present in this package's scope",
            "metadata_only": "platform lists the asset but stores no byte payload, so no hash is claimable",
        },
        "assets": assets,
        "claims": [],
        "claims_note": "Contract notes allow an empty claims array for task_type 01-asset-registration; no extraction performed.",
        "summary": {
            "asset_count": len(assets),
            "by_kind": counts,
            "resolved": sum(1 for a in assets if a["resolution"]["status"] == "resolved"),
            "unresolved": sum(1 for a in assets if a["resolution"]["status"] == "unresolved"),
            "metadata_only": sum(1 for a in assets if a["resolution"]["status"] == "metadata_only"),
            "claims": 0,
            "distinct_referenced_paths": len({a["path_reference"] for a in assets if "path_reference" in a}),
        },
        "identity_granularity": (
            "Reference assets are occurrence-level: identity is (path_reference, markdown_line), "
            "so the same file cited on different lines yields different asset_ids carrying their own quotes. "
            "distinct_referenced_paths reports the deduplicated view."
        ),
        "artifact_endpoint_probe": probe_artifact_endpoints(token),
        "limitations": [
            "Registration only: no text extraction, no claim generation, no verified marks (verification is platform-gated).",
            "Referenced paths are resolved strictly inside the TensorKnowledge delivery worktree; source trees of other repos are outside this work package's boundary, so such entries stay unresolved by design.",
            "Report metadata 'figures' is inventoried as-is; no figure bytes are copied into the manifest.",
            "Output location: .gitignore ignores artifacts/ and docs/ops/filter-audit.md documents that the push gate drops artifacts/**; outputs therefore live under docs/kf/wp-5687-01/ so they are not silently filtered.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets)" % (MANIFEST.relative_to(REPO), len(assets)))
    return manifest


def verify():
    """Re-run every acceptance item independently of the build step."""
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    lines = md.split("\n")
    checks = {}

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "json.loads OK"}
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"valid_json": {"pass": False, "detail": str(e)}}))
        return 1

    required = {"manifest_version", "package_id", "task_type", "report_id", "provenance", "assets", "claims", "summary"}
    missing = sorted(required - set(manifest))
    prov_required = {"source_uri", "source_field", "source_hash"}
    checks["schema_pass"] = {
        "pass": not missing and not (prov_required - set(manifest["provenance"]))
        and manifest["package_id"] == PKG and manifest["report_id"] == REPORT_ID
        and manifest["task_type"] == "01-asset-registration",
        "detail": "missing_top=%s missing_provenance=%s" % (missing, sorted(prov_required - set(manifest["provenance"]))),
    }

    bad_loc = []
    for a in manifest["assets"]:
        loc = a.get("locator", {})
        if loc.get("scheme") == "markdown_line":
            ln, q = loc.get("line"), loc.get("quote")
            if not isinstance(ln, int) or not (1 <= ln <= len(lines)) or lines[ln - 1] != q or q not in md:
                bad_loc.append(a["asset_id"])
        elif loc.get("scheme") == "report_field":
            field = loc.get("field")
            if field == "markdown" and not md:
                bad_loc.append(a["asset_id"])
            elif field == "figures":
                figs = meta.get("figures") or []
                idx = loc.get("index")
                if not isinstance(idx, int) or not (0 <= idx < len(figs)):
                    bad_loc.append(a["asset_id"])
        else:
            bad_loc.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "pass": not bad_loc,
        "detail": "checked %d locators; unresolvable=%s" % (len(manifest["assets"]), bad_loc),
    }

    actual = hashlib.sha256(raw).hexdigest()
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    checks["source_hash_matches"] = {
        "pass": actual == declared == EXPECTED_HASH,
        "detail": "actual=%s declared=%s contract=%s" % (actual, declared, EXPECTED_HASH),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)),
        "detail": "%d asset ids, %d distinct" % (len(ids), len(set(ids))),
    }

    bad_claims = [
        c.get("claim_id", "?")
        for c in manifest["claims"]
        if not (c.get("evidence_locator") or c.get("status"))
    ]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad_claims,
        "detail": "%d claims; bad=%s" % (len(manifest["claims"]), bad_claims),
    }

    ok = all(c["pass"] for c in checks.values())
    VERDICT.write_text(json.dumps({"package_id": PKG, "checks": checks, "all_pass": ok}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    rc = 0
    for step in sys.argv[1:] or ["build", "verify"]:
        if step == "build":
            build()
        elif step == "verify":
            rc = verify()
        else:
            print("unknown step %s" % step)
            rc = 2
    sys.exit(rc)
