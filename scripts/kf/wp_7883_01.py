#!/usr/bin/env python3
"""Work package wp-7883-01 (01-asset-registration) for report_id=7883.

Scope guard: touches ONLY report_id=7883. Registration only -- no text extraction,
no claim generation, no `verified` marks (verification is platform-gated).

Zero hand-copy: every locator quote is a verbatim slice of the fetched markdown
(nothing retyped), and every number in the manifest is computed from those bytes.

Usage:
  python3 scripts/kf/wp_7883_01.py build      # -> docs/kf/wp-7883-01/asset_manifest.json
  python3 scripts/kf/wp_7883_01.py result     # -> docs/kf/wp-7883-01/kf_result.json
  python3 scripts/kf/wp_7883_01.py verify     # -> docs/kf/wp-7883-01/verification.json
  python3 scripts/kf/wp_7883_01.py figure     # -> docs/kf/wp-7883-01/fig1_asset_coverage_map.png
  python3 scripts/kf/wp_7883_01.py all
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

PKG = "wp-7883-01"
REPORT_ID = "7883"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/7883"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "fc4d21ec4e30740b8596ea5b2892c877444ab58e274d5d301638322ae5fd77f5"
EXPECTED_CHARS = 7585
CONTRACT_SCENARIO = "green_compliance_eedi_eexi_cii"
CONTRACT_TITLE = "P151-N04 · EEDI/EEXI/CII 合规计算链成熟化：IMO 公式锚 + 三船型裁决面 + 减排技术折减"

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
RESULT = OUT_DIR / "kf_result.json"
VERDICT = OUT_DIR / "verification.json"
FIGURE = OUT_DIR / "fig1_asset_coverage_map.png"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
TIMEOUT = 60

# --------------------------------------------------------------- platform I/O


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
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
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


def probe_artifact_endpoints(token):
    """Best-effort discovery of a platform attachment listing (never guessed)."""
    probes = {}
    for path in ("/tensor/reports/%s/artifacts" % REPORT_ID, "/tensor/artifacts?report_id=%s" % REPORT_ID):
        try:
            d = _req(BASE + path, token)
            probes[path] = {"status": "ok", "shape": type(d).__name__,
                            "n_items": len(d) if isinstance(d, (list, dict)) else None}
        except urllib.error.HTTPError as e:
            probes[path] = {"status": "http_%s" % e.code}
        except Exception as e:  # noqa: BLE001 - record, never fabricate
            probes[path] = {"status": "error", "detail": type(e).__name__}
    return probes


# --------------------------------------------------------------- parsing


def headings(lines):
    """(line_no_1based, text) for every '## ' section heading."""
    out = []
    for i, ln in enumerate(lines, start=1):
        if ln.startswith("## "):
            out.append((i, ln))
    return out


def table_blocks(lines):
    """Contiguous pipe-table blocks: (line_start, line_end, data_row_count)."""
    blocks, run = [], []
    for i, ln in enumerate(lines, start=1):
        if ln.strip().startswith("|"):
            run.append((i, ln))
            continue
        if run:
            blocks.append(run)
            run = []
    if run:
        blocks.append(run)
    out = []
    for run in blocks:
        start, end = run[0][0], run[-1][0]
        # header row + '---' separator are not data rows
        n_data = max(len(run) - 2, 0)
        out.append((start, end, n_data))
    return out


BACKTICK = re.compile(r"`([^`\n]+)`")
PATHLIKE = re.compile(r"^(?:[\w.-]+/)*[\w.*-]+\.(?:py|json|png|jsonl|csv|md|txt|ya?ml)$")


def scan_references(lines):
    """Backtick-quoted path-like tokens, occurrence level, with verbatim line quote."""
    refs, seen = [], set()
    for i, ln in enumerate(lines, start=1):
        for m in BACKTICK.finditer(ln):
            tok = m.group(1).strip()
            route = tok.startswith("/api/") or tok.startswith("api/")
            if route or PATHLIKE.match(tok) or ("/" in tok and "." in tok.split("/")[-1] and " " not in tok):
                key = (tok, i)
                if key in seen:
                    continue
                seen.add(key)
                refs.append({"path": tok, "line": i, "quote": ln})
    return refs


def classify(path):
    if path.startswith("/api/") or path.startswith("api/"):
        return "api_route_reference"
    if path.endswith(".png"):
        return "figure_file_reference"
    if path.endswith(".py"):
        return "source_code_reference"
    if path.endswith(".json"):
        return "artifact_file_reference"
    return "file_reference"


def resolve_local(path):
    """Locate the referenced path inside this delivery worktree; never assume."""
    if path.startswith("/api/") or path.startswith("api/"):
        return {"status": "unresolved", "scope": "platform_api_route",
                "reason": "HTTP route declared in the source, not a file asset; no bytes to hash in this work package"}
    cand = REPO / path
    if "*" in path:
        hits = sorted(str(p.relative_to(REPO)) for p in REPO.glob(path) if p.is_file())
        if hits:
            blob = (REPO / hits[0]).read_bytes()
            return {"status": "resolved", "scope": "delivery_worktree", "glob_hits": hits,
                    "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
        return {"status": "unresolved", "scope": "delivery_worktree",
                "reason": "glob reference has no match in the TensorKnowledge delivery worktree"}
    if cand.is_file():
        blob = cand.read_bytes()
        return {"status": "resolved", "scope": "delivery_worktree",
                "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
    return {"status": "unresolved", "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree "
                      "(producer artefact lives in another repository, outside this package's boundary)"}


# --------------------------------------------------------------- build


def build():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit("SOURCE HASH MISMATCH: contract=%s actual=%s" % (EXPECTED_HASH, digest))
    if len(md) != EXPECTED_CHARS:
        raise SystemExit("SOURCE CHAR COUNT MISMATCH: contract=%d actual=%d" % (EXPECTED_CHARS, len(md)))
    if meta.get("scenario_key") != CONTRACT_SCENARIO:
        raise SystemExit("scenario_key mismatch: %s" % meta.get("scenario_key"))

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
        "asset_id": "r7883:source",
        "kind": "report_markdown",
        "uri": SOURCE_URI,
        "source_field": SOURCE_FIELD,
        "title": meta.get("title"),
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": digest,
        "locator": {"scheme": "report_field", "field": "markdown"},
        "resolution": {"status": "resolved", "scope": "platform_api",
                       "via": "GET /api/v1/tensor/reports/7883"},
    })

    # A2: sections (heading + verbatim heading quote + line span)
    hs = headings(lines)
    for n, (ln_no, text) in enumerate(hs, start=1):
        end = (hs[n][0] - 1) if n < len(hs) else len(lines)
        add({
            "asset_id": "r7883:sec:%02d" % n,
            "kind": "markdown_section",
            "uri": "%s#line=%d" % (SOURCE_URI, ln_no),
            "heading": text.lstrip("# ").strip(),
            "line_start": ln_no,
            "line_end": end,
            "n_lines": end - ln_no + 1,
            "locator": {"scheme": "markdown_line", "line": ln_no, "quote": text,
                        "line_start": ln_no, "line_end": end},
            "resolution": {"status": "resolved", "scope": "source_markdown"},
        })

    # A3: pipe tables (verbatim block slice, exact line span)
    for n, (start, end, n_data) in enumerate(table_blocks(lines), start=1):
        quote = "\n".join(lines[start - 1:end])
        add({
            "asset_id": "r7883:tbl:%02d" % n,
            "kind": "markdown_table",
            "uri": "%s#line=%d-%d" % (SOURCE_URI, start, end),
            "line_start": start,
            "line_end": end,
            "n_data_rows": n_data,
            "n_columns": lines[start - 1].count("|") - 1,
            "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            "locator": {"scheme": "markdown_line_range", "line": start, "line_start": start,
                        "line_end": end, "quote": quote},
            "resolution": {"status": "resolved", "scope": "source_markdown"},
        })

    # A4: figures carried by the report record
    for n, fig in enumerate(meta.get("figures") or [], start=1):
        b64 = fig.get("png_base64") or ""
        try:
            blob = base64.b64decode(b64) if b64 else b""
        except Exception:  # noqa: BLE001
            blob = b""
        add({
            "asset_id": "r7883:fig:%02d" % n,
            "kind": "embedded_figure",
            "uri": "%s#figures[%d]" % (SOURCE_URI, n - 1),
            "name": fig.get("name"),
            "caption": fig.get("caption"),
            "bytes": len(blob) or None,
            "sha256": hashlib.sha256(blob).hexdigest() if blob else None,
            "locator": {"scheme": "report_field", "field": "figures", "index": n - 1},
            "resolution": ({"status": "resolved", "scope": "platform_api", "has_payload": True}
                           if blob else
                           {"status": "metadata_only", "scope": "platform_api", "has_payload": False,
                            "reason": "record lists name+caption only; no png_base64 payload stored, "
                                      "so no byte hash is claimable"}),
        })

    # A5: path-like references cited in the body (occurrence level)
    for n, ref in enumerate(scan_references(lines), start=1):
        add({
            "asset_id": "r7883:ref:%02d" % n,
            "kind": classify(ref["path"]),
            "uri": "%s#line=%d" % (SOURCE_URI, ref["line"]),
            "path_reference": ref["path"],
            "locator": {"scheme": "markdown_line", "line": ref["line"], "quote": ref["quote"]},
            "resolution": resolve_local(ref["path"]),
        })

    # A6: record-level metadata with no byte payload
    add({
        "asset_id": "r7883:meta:record",
        "kind": "report_metadata",
        "uri": "%s#record" % SOURCE_URI,
        "scenario_key": meta.get("scenario_key"),
        "mission_id": meta.get("mission_id"),
        "tags": meta.get("tags"),
        "created_at": meta.get("created_at"),
        "status": meta.get("status"),
        "locator": {"scheme": "report_field", "field": "record"},
        "resolution": {"status": "metadata_only", "scope": "platform_api", "has_payload": False,
                       "reason": "platform stores these fields as record metadata; no byte payload to hash "
                                 "(the hashable payload of this package is the markdown field)"},
    })

    counts = {}
    for a in assets:
        k = "%s/%s" % (a["kind"], a["resolution"]["status"])
        counts[k] = counts.get(k, 0) + 1

    manifest = {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "schema_note": (
            "Envelope follows schemas/kf_result.v1.schema.json (task_type '01-asset-registration' matches "
            "the schema's '^[0-9]{2}(-[a-z0-9-]+)?$'; claims present as an empty array, which the schema "
            "allows). The asset_manifest body is self-described below."
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
            "contract_declared_hash": "sha256:" + EXPECTED_HASH,
            "contract_declared_chars": EXPECTED_CHARS,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "chars_matches_contract": len(md) == EXPECTED_CHARS,
            "report_title": meta.get("title"),
            "report_title_matches_contract": meta.get("title") == CONTRACT_TITLE,
            "report_scenario_key": meta.get("scenario_key"),
            "report_mission_id": meta.get("mission_id"),
            "report_created_at": meta.get("created_at"),
            "report_tags": meta.get("tags"),
            "fetched_via": "GET /api/v1/tensor/reports/7883",
            "generator": "scripts/kf/wp_7883_01.py",
            "contract_version": "1.0",
        },
        "resolution_status_vocabulary": {
            "resolved": "bytes located and hashed (source markdown, source slice, or a file inside this worktree)",
            "unresolved": "reference parsed from the report but the target is outside this package's scope",
            "metadata_only": "platform lists the asset but stores no byte payload, so no hash is claimable",
        },
        "assets": assets,
        "claims": [],
        "claims_note": (
            "Contract: 'claims 允许为空数组' and 03-extraction is out of scope for task_type "
            "01-asset-registration; no knowledge object was generated (no_forced_claim_generation)."
        ),
        "summary": {
            "asset_count": len(assets),
            "by_kind_and_status": counts,
            "resolved": sum(1 for a in assets if a["resolution"]["status"] == "resolved"),
            "unresolved": sum(1 for a in assets if a["resolution"]["status"] == "unresolved"),
            "metadata_only": sum(1 for a in assets if a["resolution"]["status"] == "metadata_only"),
            "sections": len(hs),
            "tables": len([a for a in assets if a["kind"] == "markdown_table"]),
            "figures_in_record": len(meta.get("figures") or []),
            "claims": 0,
            "distinct_referenced_paths": len({a["path_reference"] for a in assets if "path_reference" in a}),
        },
        "identity_granularity": (
            "Reference assets are occurrence-level: identity is (path_reference, markdown_line), so the same "
            "file cited on different lines yields distinct asset_ids carrying their own quotes; "
            "distinct_referenced_paths is the deduplicated view."
        ),
        "artifact_endpoint_probe": probe_artifact_endpoints(token),
        "limitations": [
            "Registration only: no text extraction, no claim generation, no 'verified' marks (verification is platform-gated).",
            "Referenced paths are resolved strictly inside the TensorKnowledge delivery worktree; the producer tree "
            "(ship-performance-platform: backend/ + artifacts/green_compliance_m6650/) is outside this package's boundary, "
            "so those references stay unresolved by design rather than being assumed present.",
            "Report metadata 'figures' is inventoried as-is; where the record stores no payload the entry is metadata_only.",
            "markdown_table quotes are verbatim multi-line slices; n_data_rows excludes the header and '---' separator rows.",
            "Output location: docs/kf/wp-7883-01/ (not artifacts/), because .gitignore drops artifacts/** at the push gate.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets)" % (MANIFEST.relative_to(REPO), len(assets)))
    return manifest


def emit_result():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mraw = MANIFEST.read_bytes()
    token = login()
    _meta, live_md = fetch_report(token)
    live_digest = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    if live_digest != declared:
        raise SystemExit("live source drifted from manifest: %s != %s" % (live_digest, declared))
    result = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + live_digest,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(live_md),
            "source_bytes_utf8": len(live_md.encode("utf-8")),
            "fetched_via": "GET /api/v1/tensor/reports/7883",
            "generator": "scripts/kf/wp_7883_01.py",
            "contract_version": "1.0",
            "outputs_binding": {
                "asset_manifest.json": {
                    "path": str(MANIFEST.relative_to(REPO)),
                    "sha256": hashlib.sha256(mraw).hexdigest(),
                    "bytes": len(mraw),
                }
            },
        },
        # contract: outputs value = the declared output file's content object -> embed the manifest verbatim
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % RESULT.relative_to(REPO))
    return result


# --------------------------------------------------------------- verify


def verify():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    lines = md.split("\n")
    checks = {}

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "json.loads OK (manifest); envelope checked under schema_pass"}
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"valid_json": {"pass": False, "detail": str(e)}}, ensure_ascii=False))
        return 1

    # schema_pass: envelope validated against the shipped schema, if the validator is installed
    schema_path = REPO / "schemas" / "kf_result.v1.schema.json"
    env = json.loads(RESULT.read_text(encoding="utf-8"))
    schema_detail = {}
    try:
        import jsonschema  # noqa: PLC0415

        jsonschema.validate(env, json.loads(schema_path.read_text(encoding="utf-8")))
        schema_ok = True
        schema_detail["envelope"] = "jsonschema.validate OK against schemas/kf_result.v1.schema.json"
    except ImportError:
        schema_ok = None
        schema_detail["envelope"] = "jsonschema not installed: envelope checked structurally instead"
    except Exception as e:  # noqa: BLE001
        schema_ok = False
        schema_detail["envelope"] = "schema violation: %s" % e
    required = {"package_id", "task_type", "report_id", "provenance", "outputs"}
    prov_required = {"source_hash", "source_field"}
    structural = (not (required - set(env)) and not (prov_required - set(env["provenance"]))
                  and env["package_id"] == PKG and env["report_id"] == REPORT_ID
                  and re.match(r"^sha256:[0-9a-f]{64}$", env["provenance"]["source_hash"]) is not None
                  and isinstance(env["outputs"].get("asset_manifest.json"), dict))
    man_required = {"manifest_version", "package_id", "task_type", "report_id", "provenance",
                    "assets", "claims", "summary"}
    man_ok = (not (man_required - set(manifest)) and manifest["package_id"] == PKG
              and manifest["report_id"] == REPORT_ID and manifest["task_type"] == TASK_TYPE)
    checks["schema_pass"] = {
        "pass": bool(structural and man_ok and (schema_ok is not False)),
        "detail": {"envelope_structurally_valid": structural, "manifest_required_keys": man_ok, **schema_detail},
    }

    # source_locator_resolvable: every quote must be a verbatim substring at its declared position
    bad = []
    checked = 0
    for a in manifest["assets"]:
        loc = a.get("locator", {})
        scheme, q = loc.get("scheme"), loc.get("quote")
        checked += 1
        if scheme == "report_field":
            field = loc.get("field")
            if field == "markdown" and not md:
                bad.append(a["asset_id"])
            elif field == "figures":
                figs = meta.get("figures") or []
                if not (isinstance(loc.get("index"), int) and 0 <= loc["index"] < len(figs)):
                    bad.append(a["asset_id"])
            elif field == "record":
                if not meta:
                    bad.append(a["asset_id"])
        elif scheme == "markdown_line":
            ln = loc.get("line")
            if not isinstance(ln, int) or not (1 <= ln <= len(lines)) or lines[ln - 1] != q or q not in md:
                bad.append(a["asset_id"])
        elif scheme == "markdown_line_range":
            s, e = loc.get("line_start"), loc.get("line_end")
            if not (isinstance(s, int) and isinstance(e, int) and 1 <= s <= e <= len(lines)):
                bad.append(a["asset_id"])
            elif "\n".join(lines[s - 1:e]) != q or q not in md:
                bad.append(a["asset_id"])
        else:
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": "checked %d locators, unresolvable=%s" % (checked, bad),
    }

    actual = hashlib.sha256(raw).hexdigest()
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    env_declared = env["provenance"]["source_hash"].split("sha256:")[-1]
    checks["source_hash_matches"] = {
        "pass": actual == declared == env_declared == EXPECTED_HASH,
        "detail": "recomputed=%s manifest=%s envelope=%s contract=%s" % (actual, declared, env_declared, EXPECTED_HASH),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)) and all(ids),
        "detail": "asset_ids=%d unique=%d" % (len(ids), len(set(ids))),
    }

    claims = manifest.get("claims", [])
    bad_claims = [c for c in claims if not c.get("evidence") and c.get("status") != "unresolved"]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad_claims,
        "detail": "claims=%d violating=%d (empty array: vacuously satisfied, contract allows empty claims)" % (
            len(claims), len(bad_claims)),
    }
    checks["do_not_mark_claims_as_verified"] = {
        "pass": all(c.get("status") != "verified" for c in claims),
        "detail": "no claim carries status='verified'",
    }

    # outputs fidelity: embedded object must equal the on-disk output file, byte-for-byte after parse
    disk = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bind = env["provenance"].get("outputs_binding", {}).get("asset_manifest.json", {})
    checks["outputs_match_declared_file"] = {
        "pass": env["outputs"]["asset_manifest.json"] == disk
        and bind.get("sha256") == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
        and bind.get("bytes") == MANIFEST.stat().st_size,
        "detail": "embedded==disk:%s binding_sha256_ok:%s binding_bytes_ok:%s" % (
            env["outputs"]["asset_manifest.json"] == disk,
            bind.get("sha256") == hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            bind.get("bytes") == MANIFEST.stat().st_size),
    }

    # scope guard: nothing in the outputs may point at another report_id
    blob = json.dumps([manifest, env], ensure_ascii=False)
    foreign = sorted({m for m in re.findall(r"reports/(\d+)", blob) if m != REPORT_ID})
    checks["scope_single_report_only"] = {
        "pass": not foreign,
        "detail": "report_id references found: %s" % (sorted(set(re.findall(r"reports/(\d+)", blob)))),
    }

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "envelope_sha256": hashlib.sha256(RESULT.read_bytes()).hexdigest(),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["all_pass"] else 1


# --------------------------------------------------------------- figure


def figure():
    """Asset coverage map: where each registered asset sits in the source document."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = None
    for a in manifest["assets"]:
        if a["asset_id"] == "r7883:source":
            md = a
    rows = [a for a in manifest["assets"] if a["locator"].get("scheme", "").startswith("markdown_line")]
    n_lines = None
    for a in manifest["assets"]:
        if a.get("line_end"):
            n_lines = max(n_lines or 0, a["line_end"])
    labels, spans, kinds = [], [], []
    order = {"markdown_section": 0, "markdown_table": 1, "source_code_reference": 2,
             "artifact_file_reference": 3, "figure_file_reference": 4, "api_route_reference": 5}
    rows.sort(key=lambda a: (order.get(a["kind"], 9), a["locator"]["line"]))
    for a in rows:
        loc = a["locator"]
        s = loc.get("line_start", loc.get("line"))
        e = loc.get("line_end", loc.get("line"))
        labels.append("%s %s" % (a["asset_id"].replace("r7883:", ""), a["kind"].replace("_", " ")))
        spans.append((s, e))
        kinds.append(a["kind"])

    palette = {"markdown_section": "#1f4e79", "markdown_table": "#2e7d32",
               "source_code_reference": "#b26a00", "artifact_file_reference": "#7b1fa2",
               "figure_file_reference": "#c62828", "api_route_reference": "#455a64"}
    fig, ax = plt.subplots(figsize=(11, 0.32 * len(rows) + 1.8), dpi=150)
    for i, ((s, e), k) in enumerate(zip(spans, kinds)):
        ax.barh(i, e - s + 1, left=s, height=0.62, color=palette.get(k, "#607d8b"),
                alpha=0.9, edgecolor="black", linewidth=0.3)
        ax.text(e + max(2, 0.004 * (n_lines or 0)), i, "L%d-%d" % (s, e), va="center", fontsize=6.5, color="#333333")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlim(0, (n_lines or 200) * 1.13)
    ax.set_xlabel("line number in tensor://reports/7883#markdown  (total %s lines)" % n_lines)
    ax.set_title("wp-7883-01 asset coverage map — %d assets registered, quotes verbatim\n"
                 "source sha256 %s…, %s chars" % (len(manifest["assets"]),
                                                  manifest["provenance"]["source_hash"].split(":")[1][:16],
                                                  manifest["provenance"]["source_chars"]),
                 fontsize=9)
    ax.grid(axis="x", alpha=0.25, linestyle=":")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in palette.values()]
    ax.legend(handles, [k.replace("_", " ") for k in palette], fontsize=6.5, loc="lower right", ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURE)
    print("wrote %s (%d bytes)" % (FIGURE.relative_to(REPO), FIGURE.stat().st_size))
    return FIGURE


if __name__ == "__main__":
    acts = sys.argv[1:] or ["all"]
    if "all" in acts:
        acts = ["build", "result", "figure", "verify"]
    rc = 0
    for a in acts:
        if a == "build":
            build()
        elif a == "result":
            emit_result()
        elif a == "figure":
            figure()
        elif a == "verify":
            rc = verify()
    sys.exit(rc)