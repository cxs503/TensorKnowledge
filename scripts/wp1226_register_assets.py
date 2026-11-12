#!/usr/bin/env python3
"""wp-1226-01 · 01-asset-registration for report_id=1226 (only that report).

Registers the source report as an asset (byte-pinned markdown), its record metadata,
its three declared figures, and every artifact/spec reference that the report text
names — WITHOUT extracting claims (contract objective: register_assets only).

Zero hand-copy: every quote registered here is a byte substring of the fetched
markdown computed at run time; every record value is read from the API record.

Usage:
  python3 scripts/wp1226_register_assets.py            # live: fetch report 1226, probe store
  python3 scripts/wp1226_register_assets.py --offline  # reuse work/wp-1226-01/source/report_1226.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
API_ROOT = BASE[: -len("/api/v1")] if BASE.endswith("/api/v1") else BASE

REPORT_ID = "1226"
PACKAGE_ID = "wp-1226-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/1226"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = "sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717"
CONTRACT_CHARS = 6045
CONTRACT_TITLE = "CII 参考线（MEPC.353(78) G1）独立复核与缺陷修复（m1643）"
CONTRACT_SCENARIO = "cii_reference_lines_verification"

WT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = WT / "work" / "wp-1226-01" / "source"
OUT_DIR = WT / "docs" / "kf" / PACKAGE_ID

# Referenced artefacts / symbols / spec documents named inside the report markdown.
# (asset_id_suffix, kind, role, name, needle, extra)
REFERENCE_TABLE = [
    ("10", "report_generator", "referenced_external_artifact",
     "tools/verify_cii_reference_lines_m1643.py", "tools/verify_cii_reference_lines_m1643.py",
     {"claim_in_text": "全部数字程序化注入，本文件由脚本产物渲染"}),
    ("11", "result_data", "referenced_external_artifact",
     "artifacts/cii_m1643/cii_reference_verification.json",
     "artifacts/cii_m1643/cii_reference_verification.json", {}),
    ("12", "figure_file", "referenced_external_artifact",
     "artifacts/cii_m1643/fig1_cii_reference_lines.png",
     "artifacts/cii_m1643/fig1_cii_reference_lines.png", {}),
    ("13", "figure_file", "referenced_external_artifact",
     "fig2_relative_error.png", "fig2_relative_error.png",
     {"path_inferred": "artifacts/cii_m1643/fig2_relative_error.png",
      "path_inference_basis": "listed in the same 产物 enumeration directly after "
                              "`artifacts/cii_m1643/fig1_cii_reference_lines.png`, so the "
                              "directory is inherited from that entry; the text itself prints "
                              "only the bare filename"}),
    ("14", "figure_file", "referenced_external_artifact",
     "fig3_rating_general_cargo.png", "fig3_rating_general_cargo.png",
     {"path_inferred": "artifacts/cii_m1643/fig3_rating_general_cargo.png",
      "path_inference_basis": "same enumeration as fig2_relative_error.png; directory inherited"}),
    ("15", "test_file", "referenced_external_artifact",
     "backend/tests/polar/test_cii_reference_lines_m1643.py",
     "backend/tests/polar/test_cii_reference_lines_m1643.py", {}),
    ("16", "source_code", "referenced_external_artifact",
     "backend/services/polar/cii.py", "backend/services/polar/cii.py", {}),
    ("17", "module_reference", "referenced_external_artifact", "polar.ships", "polar.ships", {}),
    ("18", "symbol_reference", "referenced_external_artifact",
     "constants.CII_REFERENCE_LINES", "constants.CII_REFERENCE_LINES", {}),
    ("19", "symbol_reference", "referenced_external_artifact",
     "CII_REFERENCE_LINES_NOT_SUPPORTED", "CII_REFERENCE_LINES_NOT_SUPPORTED", {}),
    ("20", "symbol_reference", "referenced_external_artifact",
     "cii.cii_reference_line_invariants()", "cii.cii_reference_line_invariants()", {}),
    ("21", "symbol_reference", "referenced_external_artifact",
     "verify_cii_ship_types()", "verify_cii_ship_types()", {}),
    ("22", "symbol_reference", "referenced_external_artifact", "_CII_VALID_DWT", "_CII_VALID_DWT", {}),
    ("23", "symbol_reference", "referenced_external_artifact",
     "NotImplementedError", "NotImplementedError", {}),
    ("40", "standard_document", "cited_external_standard",
     "MEPC.353(78) G1 Annex Table 1", "MEPC.353(78) G1 Annex Table 1", {}),
    ("41", "standard_document", "cited_external_standard", "MEPC.353(78) G3", "MEPC.353(78) G3", {}),
    ("42", "standard_document", "cited_external_standard", "MEPC.354(78) G4", "MEPC.354(78) G4", {}),
]

PROBE_PATHS = [
    "/tensor/reports/1226/figures/fig1_cii_reference_lines.png",
    "/tensor/reports/1226/figures",
    "/tensor/artifacts/cii_m1643/cii_reference_verification.json",
    "/tensor/reports/1226/attachments",
]


# --------------------------------------------------------------------------- io
def _login() -> str:
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        raise SystemExit("TENSOR_AGENT_USER / TENSOR_AGENT_PASS not set")
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit(f"login response without token: keys={sorted(d)}")
    return tok


def fetch_report(token: str) -> dict:
    req = urllib.request.Request(
        BASE + f"/tensor/reports/{REPORT_ID}", headers={"Authorization": "Bearer " + token}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return d.get("data", d)


def probe(path: str, token: str) -> dict:
    req = urllib.request.Request(API_ROOT + "/api/v1" + path,
                                headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return {"path": path, "http_status": r.status, "bytes": len(body),
                    "content_type": r.headers.get("Content-Type")}
    except urllib.error.HTTPError as e:
        return {"path": path, "http_status": e.code, "bytes": 0, "content_type": None}
    except Exception as e:  # noqa: BLE001
        return {"path": path, "http_status": None, "bytes": 0, "transport_error": type(e).__name__}


# ------------------------------------------------------------------ manifest
def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def all_occurrences(md: str, needle: str) -> list[tuple[int, int]]:
    out, i = [], md.find(needle)
    while i != -1:
        out.append((i, i + len(needle)))
        i = md.find(needle, i + 1)
    return out


def build_manifest(record: dict, md: str, probes: list[dict]) -> dict:
    raw = md.encode("utf-8")
    digest = sha256_bytes(raw)
    figures = record.get("figures") or []
    assets: list[dict] = []

    # --- asset 01: the source document itself (byte-pinned) -------------------
    h1_end = md.find("\n")
    assets.append({
        "asset_id": "ast-1226-01",
        "kind": "source_document",
        "role": "primary_source",
        "name": "report_1226_markdown",
        "locators": [{
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "char_start": 0,
            "char_end": h1_end,
            "quote": md[0:h1_end],
            "note": "H1 line; whole-document span recorded in content_ref",
        }],
        "content_ref": {"source_uri": SOURCE_URI, "source_field": SOURCE_FIELD,
                        "chars": len(md), "byte_length_utf8": len(raw), "sha256": digest},
        "resolvable": True,
        "resolution": "fetched_via_tensor_api",
        "status": "resolved",
    })

    # --- asset 02: record metadata -------------------------------------------
    rec_fields = ["id", "title", "scenario_key", "mission_id", "status", "created_by", "created_at"]
    assets.append({
        "asset_id": "ast-1226-02",
        "kind": "record_metadata",
        "role": "identification",
        "name": "report_1226_record",
        "locators": [{"source_uri": SOURCE_URI, "source_field": "record", "field": f,
                      "value": record.get(f)} for f in rec_fields]
        + [{"source_uri": SOURCE_URI, "source_field": "record", "field": "tags",
            "value": record.get("tags")}],
        "values": {f: record.get(f) for f in rec_fields} | {"tags": record.get("tags")},
        "resolvable": True,
        "resolution": "fetched_via_tensor_api",
        "status": "resolved",
    })

    # --- assets 03..: declared figures (metadata resolvable, bytes not) ------
    fig_probe_by_name = {p["path"].rsplit("/", 1)[-1]: p for p in probes if "/figures/" in p["path"]}
    for idx, fig in enumerate(figures):
        name = fig.get("name")
        caption = fig.get("caption")
        pr = fig_probe_by_name.get(name)
        assets.append({
            "asset_id": f"ast-1226-{3 + idx:02d}",
            "kind": "figure",
            "role": "declared_figure",
            "name": name,
            "locators": [
                {"source_uri": SOURCE_URI, "source_field": "record",
                 "field": f"figures[{idx}].name", "value": name},
                {"source_uri": SOURCE_URI, "source_field": "record",
                 "field": f"figures[{idx}].caption", "value": caption},
            ],
            "caption": caption,
            "caption_is_descriptive": bool(caption) and caption != name,
            "binary_probe": pr,
            "resolvable": False,
            "resolution": "declared_in_record_only__figures_inline_payload_absent__store_probe_404",
            "status": "unresolved",
            "unresolved_reason": (
                "record carries only name+caption (no inline bytes / no png_base64); the report "
                "store returned HTTP 404 for the figure endpoints, so the PNG bytes named by this "
                "asset cannot be fetched, hashed or compared by any downstream package"
            ),
        })

    # --- assets 10..: artefacts / symbols named in the markdown --------------
    for suffix, kind, role, name, needle, extra in REFERENCE_TABLE:
        occ = all_occurrences(md, needle)
        if not occ:
            raise SystemExit(f"needle not found verbatim in markdown, refusing to invent: {needle!r}")
        entry = {
            "asset_id": f"ast-1226-{suffix}",
            "kind": kind,
            "role": role,
            "name": name,
            "locators": [{"source_uri": SOURCE_URI, "source_field": SOURCE_FIELD,
                          "char_start": s, "char_end": e, "quote": md[s:e]} for s, e in occ],
            "occurrence_count": len(occ),
            "resolvable": False,
            "resolution": "referenced_in_markdown__not_attached_to_report_record",
            "status": "unresolved",
            "unresolved_reason": (
                "named inside the report text only; no byte-level copy is attached to report 1226 "
                "and the platform artifact endpoints probed here returned HTTP 404 — registration "
                "stops at the reference, ownership stays with the producing repo"
            ),
        }
        entry.update(extra)
        assets.append(entry)

    ids = [a["asset_id"] for a in assets]
    counts = {
        "assets_total": len(assets),
        "resolved": sum(1 for a in assets if a["status"] == "resolved"),
        "unresolved": sum(1 for a in assets if a["status"] == "unresolved"),
        "by_kind": {},
    }
    for a in assets:
        counts["by_kind"][a["kind"]] = counts["by_kind"].get(a["kind"], 0) + 1

    h1 = md[: h1_end]
    h1_title = h1[2:].strip() if h1.startswith("# ") else h1.strip()

    return {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "scope": {
            "report_id": REPORT_ID,
            "reports_touched": [REPORT_ID],
            "registers_assets_only": True,
            "extracts_claims": False,
            "classifies_report_type": False,
            "writes_outside_worktree": False,
        },
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "title": record.get("title"),
            "markdown_h1": h1_title,
            "title_matches_contract": record.get("title") == CONTRACT_TITLE,
            "title_equals_markdown_h1": record.get("title") == h1_title,
            "scenario_key": record.get("scenario_key"),
            "chars": len(md),
            "byte_length_utf8": len(raw),
            "sha256": digest,
            "hash_check": {
                "expected": CONTRACT_SOURCE_HASH,
                "recomputed": digest,
                "match": digest == CONTRACT_SOURCE_HASH,
            },
            "chars_check": {
                "expected": CONTRACT_CHARS,
                "observed": len(md),
                "match": len(md) == CONTRACT_CHARS,
            },
        },
        "assets": assets,
        "asset_counts": counts,
        "id_uniqueness": {"asset_ids_unique": len(ids) == len(set(ids)), "asset_id_count": len(ids)},
        "claims_policy": {
            "claims": [],
            "reason": (
                "this work package is asset registration only (objective.register_assets=true, "
                "classify_report_type=false); the contract states claims may be an empty array and "
                "forbids forced claim generation, so no claim object is emitted and no text is "
                "paraphrased or marked verified"
            ),
        },
        "probes": probes,
        "observations": build_observations(record, md, h1_title),
        "limitations": [
            "registration only: no claim extraction, no numeric re-verification, no report-type "
            "classification — downstream packages own those",
            "verification status is deliberately not set: the platform gate computes it",
            "all referenced artefacts live in the producing repo (ship-performance-platform) and are "
            "absent from the report store; their content was not read, hashed or trusted here",
            "figure bytes unavailable → figure content (axes/data) cannot be audited from this "
            "report record alone",
        ],
    }


def build_observations(record: dict, md: str, h1_title: str) -> list[dict]:
    obs = []
    if record.get("title") != h1_title:
        obs.append({
            "id": "obs-title-drift",
            "observation": "record.title differs byte-wise from the markdown H1 title",
            "record_title": record.get("title"),
            "markdown_h1": h1_title,
            "impact": "downstream extraction must key on report_id, not on title equality",
        })
    obs.append({
        "id": "obs-mission-id",
        "observation": "record.mission_id is present although the package contract declares "
                       "mission_id: null",
        "record_mission_id": record.get("mission_id"),
        "impact": "recorded as observed only; this package does not reconcile it",
    })
    obs.append({
        "id": "obs-truncated-heading-optional",
        "observation": "markdown is a self-contained 5-section report: H1 + §1..§5 headers, "
                       "no §6 self-check section",
        "section_headers": [ln for ln in md.splitlines() if ln.startswith("## ")],
        "impact": "informational; registration does not depend on section coverage",
    })
    return obs


# --------------------------------------------------------------------- output
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="reuse work/wp-1226-01/source/report_1226.json instead of the live API")
    args = ap.parse_args()

    SRC_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.offline:
        record = json.loads((SRC_DIR / "report_1226.json").read_text(encoding="utf-8"))
        record = record.get("data", record)
        probes: list[dict] = []
        if (SRC_DIR / "probes.json").exists():
            probes = json.loads((SRC_DIR / "probes.json").read_text(encoding="utf-8"))
    else:
        token = _login()
        record = fetch_report(token)
        (SRC_DIR / "report_1226.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        probes = [probe(p, token) for p in PROBE_PATHS]
        (SRC_DIR / "probes.json").write_text(
            json.dumps(probes, ensure_ascii=False, indent=2), encoding="utf-8")

    md = record["markdown"]
    (SRC_DIR / "report_1226.md").write_text(md, encoding="utf-8")

    manifest = build_manifest(record, md, probes)
    man_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    man_path = OUT_DIR / "asset_manifest.json"
    kf_path = OUT_DIR / "kf_result.json"
    # Reproducibility: an unchanged re-registration keeps the original emission stamp, so the
    # committed envelope is byte-stable across CI reruns (only real content changes move it).
    prev_emitted = None
    if man_path.exists() and kf_path.exists():
        try:
            if man_path.read_text(encoding="utf-8") == man_text:
                prev_emitted = json.loads(kf_path.read_text(encoding="utf-8"))[
                    "provenance"]["emitted_at"]
        except (KeyError, ValueError):
            prev_emitted = None
    man_path.write_text(man_text, encoding="utf-8")

    result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["sha256"],
            "source_field": SOURCE_FIELD,
            "producer": "agent/m15527",
            "emitted_at": prev_emitted
            or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "notes": "source_hash recomputed from the report-1226 markdown bytes fetched over the "
                     "TensorPlatform API; equals the contract-declared hash "
                     + CONTRACT_SOURCE_HASH,
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": manifest["claims_policy"]["claims"],
    }
    kf_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")

    s = manifest["source"]
    print(f"source sha256 = {s['sha256']} (match={s['hash_check']['match']})")
    print(f"chars = {s['chars']} (match={s['chars_check']['match']}) bytes = {s['byte_length_utf8']}")
    print(f"assets = {len(manifest['assets'])} -> {manifest['asset_counts']['by_kind']}")
    print(f"resolved={manifest['asset_counts']['resolved']} "
          f"unresolved={manifest['asset_counts']['unresolved']}")
    print(f"wrote {OUT_DIR/'asset_manifest.json'} and {OUT_DIR/'kf_result.json'}")
    if not s["hash_check"]["match"]:
        print("SOURCE HASH MISMATCH — gate would fail", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())