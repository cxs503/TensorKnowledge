#!/usr/bin/env python3
"""KF work package wp-7840-01 (task_type=01-asset-registration) — register source assets of report 7840.

Scope guard (hard boundaries of the work package):
  * touches ONLY report_id=7840 — no other report is read or written;
  * registration only: no text extraction, no claim generation, no `verified` marks
    (verification is computed by the platform gate, never asserted here);
  * every locator quotes bytes taken verbatim from the fetched markdown (never retyped),
    so `quote` is guaranteed to be a substring of the source and `line` its 1-based line.

Usage:
  python3 scripts/kf/build_asset_manifest_7840.py build
  python3 scripts/kf/build_asset_manifest_7840.py verify
  python3 scripts/kf/build_asset_manifest_7840.py result      # kf_result envelope
  python3 scripts/kf/build_asset_manifest_7840.py build verify result
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

PKG = "wp-7840-01"
REPORT_ID = "7840"
SOURCE_URI = "tensor://reports/7840"
SOURCE_FIELD = "markdown"
# Pinned by the work-package contract (input.source_hash / input.chars).
EXPECTED_HASH = "eaf940b5a606c4b1ad613ea2283219434fb88265bee60999953e2f33d35a2a3d"
EXPECTED_CHARS = 6896

REPO = Path(__file__).resolve().parents[2]
# .gitignore drops artifacts/**, so package outputs live under docs/kf/ to survive the push gate.
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
VERDICT = OUT_DIR / "verification.json"
RESULT = OUT_DIR / "kf_result.json"

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
        d = _req(BASE + "/auth/login",
                 data=json.dumps({"username": USER, "password": PASS}).encode())
    except urllib.error.HTTPError:
        body = urllib.parse.urlencode({"username": USER, "password": PASS}).encode()
        d = _req(BASE + "/auth/login", data=body, ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: keys=%s" % sorted(d))
    return tok


def fetch_report(token):
    d = _req(BASE + "/tensor/reports/%s" % REPORT_ID, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


def probe_artifact_endpoints(token):
    """Best-effort discovery of an attachment listing. Records status, never fabricates data."""
    probes = {}
    for path in ("/tensor/reports/%s/artifacts" % REPORT_ID,
                 "/tensor/artifacts?report_id=%s" % REPORT_ID):
        try:
            d = _req(BASE + path, token)
            probes[path] = {"status": "ok", "shape": type(d).__name__,
                            "n_items": len(d) if isinstance(d, (list, dict)) else None}
        except urllib.error.HTTPError as e:
            probes[path] = {"status": "http_%s" % e.code}
        except Exception as e:  # noqa: BLE001 - record, never guess
            probes[path] = {"status": "error", "detail": type(e).__name__}
    return probes


# ---------------------------------------------------------------- reference scanning

IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)\s]+)\)")
CODE_EXT = r"(?:json|png|py|md|txt|csv|ya?ml|sql|sh)"
PATH_RE = re.compile(
    r"(?<![\w/`.\-])(?P<path>[A-Za-z0-9_][A-Za-z0-9_./*-]*\." + CODE_EXT + r")(?::(?P<pin>\d+(?:-\d+)?))?(?![\w`])"
)
BACKTICK_PATH_RE = re.compile(r"`(?P<path>[^`\s]+?)`")
# a path segment must be >=2 chars so math fragments such as "V/√(g L_c)" are not read as directories
DIR_RE = re.compile(r"(?<![\w/`.\-])(?P<path>(?:[A-Za-z0-9_][A-Za-z0-9_.\-]+/)+)(?![\w`])")


def classify(path: str) -> str:
    p = path.lower()
    if p.endswith(".png"):
        return "figure_reference"
    if p.endswith(".py"):
        return "source_code_reference"
    if p.endswith(".md"):
        return "document_reference"
    if p.endswith((".json", ".csv", ".txt", ".ya ml".replace(" ", ""), ".yaml", ".yml")):
        return "data_artifact_reference"
    if p.endswith("/"):
        return "directory_reference"
    return "reference"


def scan_references(lines):
    """Ordered occurrence-level (line_no, quote, path, via, pin) for path-like references."""
    found, seen = [], set()
    for i, line in enumerate(lines, start=1):
        hits = []
        for m in IMG_RE.finditer(line):
            hits.append((m.group("path"), "markdown_image", None))
        for m in BACKTICK_PATH_RE.finditer(line):
            inner = m.group("path")
            mm = re.fullmatch(r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./*-]*\." + CODE_EXT + r")(?::(?P<pin>\d+(?:-\d+)?))?", inner)
            if mm:
                hits.append((mm.group("path"), "backticked_ref", mm.group("pin")))
            elif inner.endswith("/"):
                hits.append((inner, "backticked_dir_ref", None))
        for m in PATH_RE.finditer(line):
            hits.append((m.group("path"), "bare_ref", m.group("pin")))
        for m in DIR_RE.finditer(line):
            hits.append((m.group("path"), "bare_dir_ref", None))
        # a bare filename on a line that also cites a directory is relative to that directory
        line_dirs = [p for p, via, _ in hits if via in ("backticked_dir_ref", "bare_dir_ref")]
        for path, via, pin in hits:
            key = (path, i)
            if key in seen:
                continue
            seen.add(key)
            joined = None
            if via in ("bare_ref", "backticked_ref") and "/" not in path and line_dirs:
                joined = line_dirs[0] + path
            found.append({"line": i, "quote": line, "path": joined or path, "literal": path,
                          "via": via, "pin": pin,
                          "joined_with_directory_on_same_line": bool(joined)})
    return found


def resolve_local(path: str):
    """Resolve inside the delivery worktree only (no cross-repo guessing, no bare-name search)."""
    if path.endswith("/"):
        for cand in (REPO / path, REPO / path.lstrip("./")):
            try:
                cand = cand.resolve()
            except OSError:
                continue
            if str(cand).startswith(str(REPO)) and cand.is_dir():
                return {"status": "resolved", "scope": "delivery_worktree",
                        "resolved_path": str(cand.relative_to(REPO)), "kind": "directory"}
    else:
        import glob as _glob
        for pat in (str(REPO / path), str(REPO / path.lstrip("./"))):
            for hit in sorted(_glob.glob(pat)):
                hp = Path(hit).resolve()
                if hp.is_file() and str(hp).startswith(str(REPO)):
                    raw = hp.read_bytes()
                    return {"status": "resolved", "scope": "delivery_worktree",
                            "resolved_path": str(hp.relative_to(REPO)),
                            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return {
        "status": "unresolved",
        "scope": "delivery_worktree",
        "reason": "path referenced by the report body is not present in the TensorKnowledge "
                  "delivery worktree (the report declares its own repository=ship-performance-platform, "
                  "which is outside this work package's boundary)",
        "glob_expanded": bool("*" in path),
    }



SWEEP_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./*-]*\." + CODE_EXT + r"(?::\d+(?:-\d+)?)?")


def coverage_sweep(md, assets):
    """Second, independently written scanner: any path token it finds that no asset records = a gap.

    Deliberately dumber than scan_references (no directory join, no in-image parsing) so that the two
    implementations disagree when the primary scanner over- or under-collects.
    """
    registered = {a.get("path_reference_literal") for a in assets if "path_reference_literal" in a}
    tokens = set()
    for line in md.split("\n"):
        for m in SWEEP_RE.finditer(line):
            tok = m.group(0)
            tok = re.sub(r":\d+(?:-\d+)?$", "", tok)
            seg = tok.split("/")[0]
            if not seg:
                continue
            tokens.add(tok)
    # a token counts as covered when it is registered verbatim or as the basename of a joined path
    basenames = {t.rsplit("/", 1)[-1] for t in registered}
    missing = sorted(t for t in tokens if t not in registered and t.rsplit("/", 1)[-1] not in basenames)
    return {"sweep_token_count": len(tokens), "registered_literal_count": len(registered),
            "unregistered_tokens": missing}

# ---------------------------------------------------------------- build


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

    # A1 — the source asset itself: registration存在的意义就是把 report 的字节身份钉住
    add({
        "asset_id": "r7840:source",
        "kind": "report_markdown",
        "uri": SOURCE_URI,
        "source_field": SOURCE_FIELD,
        "title": meta.get("title"),
        "scenario_key": meta.get("scenario_key"),
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": digest,
        "locator": {"scheme": "report_field", "field": "markdown"},
        "resolution": {"status": "resolved", "scope": "platform_api",
                       "via": "GET /api/v1/tensor/reports/7840"},
        "note": "sha256 matches the work-package contract input.source_hash; chars matches input.chars.",
    })

    # A2 — figures[] listed on the report record (metadata inventory only)
    for n, fig in enumerate(meta.get("figures") or [], start=1):
        b64 = fig.get("png_base64") or ""
        try:
            blob = base64.b64decode(b64) if b64 else b""
        except Exception:  # noqa: BLE001
            blob = b""
        add({
            "asset_id": "r7840:figure:%02d" % n,
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
                "reason": "report record carries this figure as name+caption only; figures[] stores no "
                          "png_base64 payload, so no figure bytes/hash can be claimed here",
            },
        })

    # A3 — every path-like reference occurrence in the markdown body
    for n, ref in enumerate(scan_references(lines), start=1):
        uniq = md.count(ref["quote"]) == 1
        add({
            "asset_id": "r7840:ref:%02d" % n,
            "kind": classify(ref["path"]),
            "uri": "%s#line=%d" % (SOURCE_URI, ref["line"]),
            "path_reference": ref["path"],
            "path_reference_literal": ref["literal"],
            "path_reference_constructed": ref["path"] != ref["literal"],
            "line_pin": ref["pin"],
            "via": ref["via"],
            "declared_sha256": None,
            "locator": {"scheme": "markdown_line", "line": ref["line"], "quote": ref["quote"]},
            "resolution": resolve_local(ref["path"]),
            "note": "; ".join(filter(None, [
                ("filename quoted bare; resolved against the directory cited on the same source line"
                 if ref.get("joined_with_directory_on_same_line") else None),
                ("source line is unique in the markdown" if uniq
                 else "source line text occurs more than once; locator pins (line, quote) together"),
            ])),
        })

    by_kind, by_class = {}, {}
    for a in assets:
        by_kind["%s/%s" % (a["kind"], a["resolution"]["status"])] = \
            by_kind.get("%s/%s" % (a["kind"], a["resolution"]["status"]), 0) + 1
        by_class[a["kind"]] = by_class.get(a["kind"], 0) + 1

    manifest = {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
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
            "fetched_via": "GET /api/v1/tensor/reports/7840",
            "generator": "scripts/kf/build_asset_manifest_7840.py",
            "contract_version": "1.0",
        },
        "resolution_status_vocabulary": {
            "resolved": "bytes located and hashed (source markdown, or a file present in this worktree)",
            "unresolved": "reference parsed verbatim from the report, target outside this package's reachable scope",
            "metadata_only": "platform lists the asset but stores no byte payload, so no hash is claimable",
        },
        "counts": {
            "assets": len(assets),
            "by_kind": by_kind,
            "by_resolution": {
                s: sum(1 for a in assets if a["resolution"]["status"] == s)
                for s in ("resolved", "unresolved", "metadata_only")
            },
        },
        "assets": assets,
        "claims": [],
        "claims_note": ("Empty claims array is legitimate for task_type 01-asset-registration "
                        "(objective.register_assets=true, no extraction). No forced claim generation; "
                        "no claim is marked verified."),
        "summary": {
            "asset_count": len(assets),
            "by_class": by_class,
            "resolved": sum(1 for a in assets if a["resolution"]["status"] == "resolved"),
            "unresolved": sum(1 for a in assets if a["resolution"]["status"] == "unresolved"),
            "metadata_only": sum(1 for a in assets if a["resolution"]["status"] == "metadata_only"),
            "claims": 0,
            "distinct_referenced_paths": len({a["path_reference"] for a in assets if "path_reference" in a}),
        },
        "identity_granularity": (
            "Reference assets are occurrence-level: identity is (path_reference, markdown_line), so the same "
            "file cited on two lines yields two asset_ids each carrying its own verbatim quote; "
            "summary.distinct_referenced_paths reports the deduplicated view."
        ),
        "coverage_sweep": coverage_sweep(md, assets),
        "artifact_endpoint_probe": probe_artifact_endpoints(token),
        "limitations": [
            "Registration only: no extraction, no claim generation, no verified marks (verification is platform-gated).",
            "Referenced paths are resolved strictly inside the TensorKnowledge delivery worktree. The report "
            "declares repository=ship-performance-platform, whose tree is outside this work package's boundary, "
            "so its source/artifact references stay unresolved by design rather than being assumed present.",
            "Report figures are inventoried as metadata (name/caption) only; no figure bytes are stored on the "
            "report record, so no figure hash is claimed.",
            "No cross-report access: only report_id=7840 was fetched.",
            "Outputs live under docs/kf/wp-7840-01/ because .gitignore drops artifacts/** from the push gate.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets)" % (MANIFEST.relative_to(REPO), len(assets)))
    return manifest


# ---------------------------------------------------------------- verify


def verify():
    """Independently re-run every acceptance item from the contract (no reuse of build-time state)."""
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    lines = md.split("\n")
    checks = {}

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "json.loads OK on %s" % MANIFEST.name}
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"valid_json": {"pass": False, "detail": str(e)}}))
        return 1

    # schema_pass: the kf_result envelope shape + the manifest's own required keys
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    env_required = {"package_id", "task_type", "report_id", "provenance", "outputs"}
    env_missing = sorted(env_required - set(result))
    allowed_top = env_required | {"claims"}
    extra_top = sorted(set(result) - allowed_top)          # kf_result.v1 is additionalProperties=false
    prov_ok = {"source_hash", "source_field"} <= set(result.get("provenance", {}))
    pkg_pat = re.fullmatch(r"wp-[A-Za-z0-9][A-Za-z0-9_.:-]*-[0-9]{2}", result.get("package_id", ""))
    tt_pat = re.fullmatch(r"[0-9]{2}(-[a-z0-9-]+)?", result.get("task_type", ""))
    hash_pat = re.fullmatch(r"sha256:[0-9a-f]{64}", result.get("provenance", {}).get("source_hash", ""))
    man_required = {"manifest_version", "package_id", "task_type", "report_id",
                    "provenance", "counts", "assets", "claims", "summary"}
    man_missing = sorted(man_required - set(manifest))
    asset_required = {"asset_id", "kind", "locator", "resolution"}
    bad_assets = [a.get("asset_id") for a in manifest.get("assets", []) if asset_required - set(a)]
    checks["schema_pass"] = {
        "pass": (not env_missing and not extra_top and prov_ok and bool(pkg_pat) and bool(tt_pat)
                 and bool(hash_pat) and result["package_id"] == PKG and result["report_id"] == REPORT_ID
                 and result["task_type"] == "01-asset-registration"
                 and not man_missing and not bad_assets
                 and "asset_manifest.json" in result["outputs"]),
        "detail": ("envelope_missing=%s envelope_extra=%s provenance_ok=%s manifest_missing=%s "
                   "assets_missing_fields=%s" % (env_missing, extra_top, prov_ok, man_missing, bad_assets)),
    }

    # source_locator_resolvable: every locator re-resolves against the live source
    bad_loc, n_loc = [], 0
    for a in manifest["assets"]:
        loc = a.get("locator", {})
        n_loc += 1
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
        "detail": "checked %d locators against live markdown (%d lines); unresolvable=%s"
                  % (n_loc, len(lines), bad_loc),
    }

    actual = hashlib.sha256(raw).hexdigest()
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    env_hash = result["provenance"]["source_hash"].split("sha256:")[-1]
    checks["source_hash_matches"] = {
        "pass": actual == declared == env_hash == EXPECTED_HASH and len(md) == EXPECTED_CHARS,
        "detail": "recomputed=%s manifest=%s envelope=%s contract=%s chars=%d/%d"
                  % (actual, declared, env_hash, EXPECTED_HASH, len(md), EXPECTED_CHARS),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)) and all(ids),
        "detail": "assets=%d unique=%d" % (len(ids), len(set(ids))),
    }

    sweep = coverage_sweep(md, manifest["assets"])
    recorded = manifest.get("coverage_sweep", {})
    checks["coverage_sweep_gap_free"] = {
        "pass": not sweep["unregistered_tokens"] and sweep == recorded,
        "detail": "independent sweep tokens=%d unregistered=%s recorded==recomputed=%s"
                  % (sweep["sweep_token_count"], sweep["unregistered_tokens"], sweep == recorded),
    }

    claims = manifest.get("claims", [])
    bad_claims = [c for c in claims if not c.get("evidence") and c.get("status") != "unresolved"]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad_claims,
        "detail": "claims=%d violating=%d (empty array: vacuously satisfied per contract notes)"
                  % (len(claims), len(bad_claims)),
    }

    # boundary self-checks (not contract acceptance items, but they guard the "no fabrication" rules)
    extra = {}
    extra["no_verified_marks"] = {
        "pass": all(c.get("status") != "verified" for c in claims + result.get("claims", [])),
        "detail": "neither manifest.claims nor envelope.claims carries a 'verified' status",
    }
    extra["single_report_scope"] = {
        "pass": {manifest["report_id"], result["report_id"]} == {REPORT_ID},
        "detail": "every report_id field in the package outputs equals %s" % REPORT_ID,
    }
    extra["constructed_paths_flagged"] = {
        "pass": all(("path_reference_literal" in a) for a in manifest["assets"] if "path_reference" in a),
        "detail": "%d constructed path(s) carry both literal and joined forms"
                  % sum(1 for a in manifest["assets"] if a.get("path_reference_constructed")),
    }
    extra["no_forced_claims"] = {
        "pass": manifest["summary"]["claims"] == len(claims) == 0,
        "detail": "claims array empty by contract note; no synthesis to hit a metric",
    }

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "note": "self-check only; the authoritative verification is the platform gate.",
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "acceptance": checks,
        "boundary_self_checks": extra,
        "all_pass": all(c["pass"] for c in checks.values()) and all(c["pass"] for c in extra.values()),
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["all_pass"] else 1


# ---------------------------------------------------------------- kf_result envelope


def emit_result():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mraw = MANIFEST.read_bytes()
    token = login()
    _meta, live_md = fetch_report(token)
    live_digest = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    if live_digest != manifest["provenance"]["source_hash"].split("sha256:")[-1]:
        raise SystemExit("live source drifted from manifest — rebuild required")
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
            "producer": "scripts/kf/build_asset_manifest_7840.py",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "notes": "asset registration only; no extraction performed; no claim status asserted here (verification is platform-gated)",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str(MANIFEST.relative_to(REPO)),
                "sha256": hashlib.sha256(mraw).hexdigest(),
                "bytes": len(mraw),
                "asset_count": manifest["summary"]["asset_count"],
                "by_kind": manifest["summary"]["by_class"],
                "by_resolution": manifest["counts"]["by_resolution"],
                "claims": len(manifest["claims"]),
            }
        },
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % RESULT.relative_to(REPO))
    return result


if __name__ == "__main__":
    acts = sys.argv[1:] or ["build", "result", "verify"]
    if "build" in acts:
        build()
    if "result" in acts:
        emit_result()
    if "verify" in acts:
        sys.exit(verify())