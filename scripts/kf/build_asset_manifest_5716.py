#!/usr/bin/env python3
"""Work package wp-5716-01 (01-asset-registration) — asset manifest builder + verifier.

Scope guard: touches ONLY report_id=5716 (assertions below refuse any other id).
No extraction, no claims, no verification marks (verification is platform-gated).

Every locator quote is taken verbatim from the fetched markdown bytes (never retyped),
so `quote` is guaranteed to be a substring of the source and `line` is its 1-based line.

Usage:
  python3 scripts/kf/build_asset_manifest_5716.py build
  python3 scripts/kf/build_asset_manifest_5716.py verify
  python3 scripts/kf/build_asset_manifest_5716.py result      # emit kf_result envelope
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

PKG = "wp-5716-01"
REPORT_ID = "5716"
SOURCE_URI = "tensor://reports/5716"
SOURCE_FIELD = "markdown"
# pinned from the work-package contract input.source_hash (platform re-computes it too)
EXPECTED_HASH = "4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377"
EXPECTED_CHARS = 4790

REPO = Path(__file__).resolve().parents[2]
# artifacts/ is gitignored (push gate drops artifacts/**), so outputs live under docs/kf/
# so that the delivered manifest is not silently filtered out of the branch.
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
VERDICT = OUT_DIR / "verification.json"
RESULT = OUT_DIR / "kf_result.json"
LOCAL_COPY = REPO / "runs" / PKG / ("report_%s.md" % REPORT_ID)

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
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login() -> str:
    body = json.dumps({"username": USER, "password": PASS}).encode("utf-8")
    for path in ("/auth/login", "/tensor/auth/login"):
        try:
            d = _req(BASE + path, data=body)
        except urllib.error.HTTPError as e:  # noqa: PERF203
            if e.code in (401, 404, 405) and path == "/auth/login":
                # some deployments expect a form-encoded login
                form = urllib.parse.urlencode({"username": USER, "password": PASS}).encode()
                d = _req(BASE + path, data=form, ctype="application/x-www-form-urlencoded")
            elif e.code in (404, 405):
                continue
            else:
                raise
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    raise SystemExit("login failed: no access_token in response")


def fetch_report(token: str):
    d = _req(BASE + "/tensor/reports/" + REPORT_ID, token=token)
    rec = d.get("data") or d
    if str(rec.get("id")) != REPORT_ID:
        raise SystemExit("scope violation: API returned report id %r" % rec.get("id"))
    md = rec.get("markdown") or ""
    if not isinstance(md, str):
        raise SystemExit("markdown field is not a string")
    return rec, md


# ---------------------------------------------------------------- reference scan

IMG_RE = re.compile(r"!\[[^\]]*\]\((?P<path>[^)\s]+)")
TICK_PATH_RE = re.compile(r"`(?P<path>[A-Za-z0-9_./-]+\.(?:json|png|py|md|txt|csv|ya?ml))(?::(?P<line>\d+(?:-\d+)?))?`")
GLOB_RE = re.compile(r"`(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*\*[A-Za-z0-9_./*-]*\.(?:png|json|csv|txt))(?::(?P<line>\d+))?`")
BARE_PATH_RE = re.compile(
    r"(?<![\w/`.])(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|png|py|md|txt|csv|ya?ml))"
    r"(?::(?P<line>\d+(?:-\d+)?))?(?![\w`])"
)


def classify(path: str) -> str:
    p = path.lower()
    if "*" in p:
        return "figure_set_pattern" if p.endswith(".png") else "data_artifact_pattern"
    if p.endswith(".png"):
        return "figure_reference"
    if p.endswith(".py"):
        return "source_code_reference"
    if p.endswith(".md"):
        return "document_reference"
    if p.endswith((".json", ".csv", ".txt", ".yaml", ".yml")):
        return "data_artifact_reference"
    return "reference"


def scan_references(lines):
    """Return ordered dicts (line_no, quote_line, path, via, pin) for every path-like reference."""
    found, seen = [], set()
    for i, line in enumerate(lines, start=1):
        hits = []
        for m in IMG_RE.finditer(line):
            hits.append((m.group("path"), "markdown_image", None))
        for m in TICK_PATH_RE.finditer(line):
            hits.append((m.group("path"), "backticked_ref", m.group("line")))
        for m in BARE_PATH_RE.finditer(line):
            hits.append((m.group("path"), "bare_ref", m.group("line")))
        for m in GLOB_RE.finditer(line):
            hits.append((m.group("path"), "glob_ref", m.group("line")))
        for path, via, pin in hits:
            key = (path, i)
            if key in seen:
                continue
            seen.add(key)
            found.append({"line": i, "quote": line, "path": path, "via": via, "pin": pin})
    return found


def resolve_local(path: str):
    """Resolve a referenced path inside the delivery worktree only (no cross-repo guessing)."""
    if "*" in path:
        return {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "glob pattern, not a single byte target: no per-file bytes are claimable from this reference",
        }
    clean = path.lstrip("./")
    for cand in (REPO / clean, REPO / path.lstrip("/")):
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


def probe_artifact_endpoints(token):
    """Probe (read-only) whether the platform exposes byte payloads for report artefacts."""
    probe = {}
    for suffix in ("/artifacts", "/files", "/attachments"):
        url = BASE + "/tensor/reports/%s%s" % (REPORT_ID, suffix)
        try:
            d = _req(url, token=token)
            probe[suffix] = {"status": "ok", "payload_keys": sorted(d)[:10] if isinstance(d, dict) else type(d).__name__}
        except urllib.error.HTTPError as e:
            probe[suffix] = {"status": "http_%d" % e.code}
        except Exception as e:  # noqa: BLE001
            probe[suffix] = {"status": "error", "detail": str(e)[:120]}
    return probe


# ---------------------------------------------------------------- inventory observations


def inventory_observations(md, lines, meta):
    """Asset-inventory-level observations only (counts of things the report declares).

    Each observation carries a verbatim markdown line + line number, and a status that is
    never 'verified' (verification is the platform gate's job). No domain claim is derived.
    """
    obs = []

    def find(pattern):
        for i, line in enumerate(lines, start=1):
            m = re.search(pattern, line)
            if m:
                return i, line, m
        return None

    figures_stored = len(meta.get("figures") or [])
    a = find(r"([0-9]+) 张图见 figures 字段")
    b = find(r"报告/([0-9]+) 图齐全")
    if a and b:
        declared_field = int(a[2].group(1))
        declared_total = int(b[2].group(1))
        obs.append({
            "observation_id": "O01-figure-count",
            "topic": "figure_inventory",
            "observation": (
                "The report declares %d figures in the figures field and %d figures overall; the platform "
                "report record stores %d figure entries (metadata only, no bytes). The difference is recorded "
                "as an unresolved inventory discrepancy, not silently reconciled."
                % (declared_field, declared_total, figures_stored)
            ),
            "status": "unresolved_discrepancy",
            "values": {
                "declared_in_figures_field": declared_field,
                "declared_total": declared_total,
                "stored_in_platform_record": figures_stored,
            },
            "evidence": [
                {"line": a[0], "quote": a[1]},
                {"line": b[0], "quote": b[1]},
            ],
            "not_verified_note": "counts only; no figure content inspected, nothing marked verified",
        })
    globbed = [i for i, line in enumerate(lines, start=1) if GLOB_RE.search(line)]
    obs.append({
        "observation_id": "O02-artifact-diagram-set",
        "topic": "artifact_set_reference",
        "observation": (
            "The report cites a figure set by glob (%d glob reference(s) registered as pattern assets); member "
            "files are not enumerable from the report alone, so the set is registered unresolved."
            % len(globbed)
        ),
        "status": "unresolved",
        "values": {"glob_reference_count": len(globbed)},
        "evidence": [{"line": i, "quote": lines[i - 1]} for i in globbed],
        "not_verified_note": "no glob expansion attempted outside the delivery worktree",
    })
    return obs


# ---------------------------------------------------------------- build


def build():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    lines = md.split("\n")

    if digest != EXPECTED_HASH:
        raise SystemExit(
            "source_hash mismatch: live=%s contract=%s — refusing to register drifted bytes"
            % (digest, EXPECTED_HASH)
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_COPY.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_COPY.write_bytes(raw)

    assets = []

    def add(a):
        a["locator"]["quote"] = a["locator"].get("quote")
        if a["locator"].get("scheme") == "markdown_line":
            q = a["locator"]["quote"]
            a["locator"]["quote_count_in_source"] = md.count(q)
        assets.append(a)

    # A1: the report markdown itself = the registered source asset
    add({
        "asset_id": "r5716:source",
        "kind": "report_markdown",
        "uri": SOURCE_URI,
        "declared_sha256": EXPECTED_HASH,
        "chars": len(md),
        "bytes_utf8": len(raw),
        "locator": {"scheme": "report_field", "field": SOURCE_FIELD},
        "resolution": {
            "status": "resolved",
            "scope": "platform_api",
            "via": "GET /tensor/reports/%s" % REPORT_ID,
            "local_copy": str(LOCAL_COPY.relative_to(REPO)),
            "sha256": digest,
        },
    })

    # A2: figures embedded in the report record (parseable binary attachments)
    for n, fig in enumerate(meta.get("figures") or [], start=1):
        b64 = fig.get("png_base64") or ""
        try:
            blob = base64.b64decode(b64) if b64 else b""
        except Exception:  # noqa: BLE001
            blob = b""
        add({
            "asset_id": "r5716:figure:%02d" % n,
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
                "reason": "figure listed by name/caption only; no png_base64 payload stored, no byte hash claimable",
            },
        })

    # A3: path-like references parsed out of the markdown body
    for n, ref in enumerate(scan_references(lines), start=1):
        res = resolve_local(ref["path"])
        add({
            "asset_id": "r5716:ref:%02d" % n,
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

    observations = inventory_observations(md, lines, meta)

    manifest = {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "schema_note": (
            "schemas/kf_result.v1.schema.json is not shipped in this repository (schemas/ has no kf_*.json); "
            "shape follows the wp-5716-01 contract keys (package_id/task_type/report_id/provenance/outputs) "
            "and is self-described here. Platform-side schema wins if it differs."
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
            "fetched_via": "GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
            "local_copy": str(LOCAL_COPY.relative_to(REPO)),
            "generator": "scripts/kf/build_asset_manifest_5716.py",
            "contract_version": "1.0",
            "lane": "C",
        },
        "resolution_status_vocabulary": {
            "resolved": "bytes located and hashed (source markdown, embedded figure payload, or a file inside this worktree)",
            "unresolved": "reference parsed from the report but the target is not present in this package's scope",
            "metadata_only": "platform lists the asset but stores no byte payload, so no hash is claimable",
        },
        "assets": assets,
        "inventory_observations": observations,
        "claims": [],
        "claims_note": (
            "Contract notes for wp-5716-01 allow an empty claims array (objective.classify_report_type=false, "
            "no extraction). Nothing here is marked verified."
        ),
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
            "Reference assets are occurrence-level: identity is (path_reference, markdown_line), so the same "
            "file cited on different lines yields different asset_ids carrying their own quotes. "
            "distinct_referenced_paths reports the deduplicated view."
        ),
        "artifact_endpoint_probe": probe_artifact_endpoints(token),
        "limitations": [
            "Registration only: no text extraction, no claim generation, no verified marks (verification is platform-gated).",
            "Referenced paths resolve strictly inside the TensorKnowledge delivery worktree; other repos are outside this work package's boundary, so cross-repo source references stay unresolved by design.",
            "Absent artefacts are registered as unresolved rather than assumed present; no target was fetched to fill a gap.",
            "Glob references (e.g. figures/*.png) are registered as pattern assets: the referenced set has no single byte target, so its members are not enumerated or hashed here.",
            "inventory_observations records asset-inventory-level discrepancies found while registering (with verbatim quotes and explicit unresolved status). No domain claim is drawn from them and none is marked verified.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets)" % (MANIFEST.relative_to(REPO), len(assets)))
    return manifest


# ---------------------------------------------------------------- verify


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
        verdict = {"checks": {"valid_json": {"pass": False, "detail": str(e)}}, "all_pass": False}
        VERDICT.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(verdict, indent=2))
        return 1

    required = {"manifest_version", "package_id", "task_type", "report_id", "provenance", "assets", "claims", "summary"}
    missing = sorted(required - set(manifest))
    prov_required = {"source_uri", "source_field", "source_hash"}
    checks["schema_pass"] = {
        "pass": bool(not missing and not (prov_required - set(manifest["provenance"]))
                     and manifest["package_id"] == PKG and manifest["report_id"] == REPORT_ID
                     and manifest["task_type"] == "01-asset-registration"),
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
        "detail": "recomputed=%s declared=%s contract=%s" % (actual, declared, EXPECTED_HASH),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)) and all(ids),
        "detail": "assets=%d unique=%d" % (len(ids), len(set(ids))),
    }

    claims = manifest.get("claims", [])
    bad_claims = [c for c in claims if not c.get("evidence") and c.get("status") != "unresolved"]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad_claims,
        "detail": "claims=%d violating=%d (empty array: vacuously satisfied per contract notes)" % (len(claims), len(bad_claims)),
    }

    checks["do_not_mark_claims_as_verified"] = {
        "pass": all(c.get("status") != "verified" for c in claims),
        "detail": "claims carry no 'verified' status",
    }

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "verification_status": "not_platform_verified",
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
        "note": "self-check only; authoritative verification is the platform gate",
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["all_pass"] else 1


def emit_result():
    """Derive the kf_result envelope from the manifest, bound to freshly re-read live bytes."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mraw = MANIFEST.read_bytes()
    token = login()
    _meta, live_md = fetch_report(token)
    live_digest = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    if live_digest != declared or live_digest != EXPECTED_HASH:
        raise SystemExit("live source drifted from manifest: %s != %s" % (live_digest, declared))
    result = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + declared,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": manifest["provenance"]["source_chars"],
            "source_bytes_utf8": manifest["provenance"]["source_bytes_utf8"],
            "fetched_via": manifest["provenance"]["fetched_via"],
            "generator": "scripts/kf/build_asset_manifest_5716.py",
            "contract_version": "1.0",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str(MANIFEST.relative_to(REPO)),
                "sha256": hashlib.sha256(mraw).hexdigest(),
                "bytes": len(mraw),
                "asset_count": manifest["summary"]["asset_count"],
                "claims": 0,
            }
        },
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % RESULT.relative_to(REPO))
    return result


if __name__ == "__main__":
    acts = sys.argv[1:] or ["build", "verify"]
    if "build" in acts:
        build()
    if "result" in acts:
        emit_result()
    if "verify" in acts:
        sys.exit(verify())