#!/usr/bin/env python3
"""wp-5577-01 · 01-asset-registration for report_id=5577.

Single-process work package (lane C, TensorKnowledge):
  1. fetch the report record (online via TensorPlatform API, or offline from
     the snapshot under docs/kf/wp-5577-01/source/);
  2. recompute sha256 over the `markdown` field bytes (utf-8, no newline
     normalization) and compare with the contract-declared source_hash;
  3. register assets: the source document, the record metadata, the 3
     declared figures, and every artifact/endpoint/standard/literature
     reference that appears VERBATIM in the markdown (literal-needle search;
     a missing needle is a hard SystemExit — no invented locators);
  4. emit asset_manifest.json + kf_result.json (envelope per
     schemas/kf_result.v1.schema.json) + acceptance.json (machine checks).

Zero-hand-copy discipline: every quote is a verbatim substring of the
fetched markdown; every offset is computed at runtime; nothing is typed in.

Usage:
    python3 scripts/wp5577_register_assets.py            # online (API)
    python3 scripts/wp5577_register_assets.py --offline  # from snapshot
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-5577-01"
SRC_DIR = PKG_DIR / "source"
SCHEMA_PATH = REPO / "schemas" / "kf_result.v1.schema.json"

# ---------------------------------------------------------------------------
# contract-declared inputs (from the work-package contract YAML, verbatim)
# ---------------------------------------------------------------------------
CONTRACT = {
    "package_id": "wp-5577-01",
    "task_type": "01-asset-registration",
    "report_id": "5577",
    "source_uri": "tensor://reports/5577",
    "source_field": "markdown",
    "source_hash": "sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8",
    "title": "BP 示范工程报告：Agent 科研生产闭环端到端实证（IN12-P8 / m4936）",
    "scenario_key": "campaign/bp-demo-in12p8",
    "chars": 3702,
}

# ---------------------------------------------------------------------------
# asset plan: (asset_id, kind, role, name, needle, note)
# needle must occur verbatim in the markdown; the script refuses to run
# otherwise (no invented locators).
# ---------------------------------------------------------------------------
ASSET_PLAN = [
    ("ast-5577-06", "declared_artifact", "repro_command", "python -m bp_demo.run",
     "python -m bp_demo.run", "one-command four-stage closed-loop rerun"),
    ("ast-5577-07", "declared_artifact", "engine_endpoint", "/api/v1/calculations/resistance",
     "/api/v1/calculations/resistance", "engine endpoint called 8 times (5 speeds + 2 negative controls + 1 deterministic re-call)"),
    ("ast-5577-08", "declared_artifact", "cluster_probe_command", "cluster_exec.py nodes",
     "cluster_exec.py nodes", "702 dual-node loong64 liveness probe"),
    ("ast-5577-09", "declared_artifact", "physics_module", "physics/holtrop",
     "physics/holtrop", "single physics source for residual wave-making resistance"),
    ("ast-5577-10", "declared_artifact", "test_file", "tests/test_resistance_ittc78.py",
     "tests/test_resistance_ittc78.py", "legacy test file; collection fixed this round (41 passed / 3 skipped)"),
    ("ast-5577-11", "declared_artifact", "artifact_index", "artifacts/bp_demo/sha256_index.json",
     "artifacts/bp_demo/sha256_index.json", "sha256 index of the 3 PNGs"),
    ("ast-5577-12", "declared_artifact", "legacy_endpoint", "/calculations/resistance",
     "/calculations/resistance", "legacy mock endpoint (pre-fix)"),
    ("ast-5577-13", "declared_artifact", "mainchain_endpoint", "/resistance/predict",
     "/resistance/predict", "Holtrop main-chain endpoint"),
    ("ast-5577-14", "declared_artifact", "deployed_instance", "http://127.0.0.1:8002",
     "http://127.0.0.1:8002", "resident old-build instance (deployment drift)"),
    ("ast-5577-15", "standard_reference", "friction_standard", "ITTC-57",
     "ITTC-57", "friction coefficient closed-form standard"),
    ("ast-5577-16", "standard_reference", "roughness_standard", "ITTC-1978",
     "ITTC-1978", "roughness allowance standard"),
    ("ast-5577-17", "literature_reference", "wave_making_regression", "Holtrop & Mennen (1982)",
     "Holtrop & Mennen (1982)", "wave-making resistance regression source"),
    ("ast-5577-18", "literature_reference", "wave_making_regression", "Holtrop (1984)",
     "Holtrop (1984)", "wave-making resistance regression source"),
    ("ast-5577-19", "benchmark_reference", "benchmark_ship", "KVLCC2",
     "KVLCC2", "full-scale literature anchor (HONEST-FAIL item V4)"),
    ("ast-5577-20", "mission_reference", "upstream_mission", "m2082",
     "m2082", "mission that merged the two resistance chains"),
    ("ast-5577-21", "gate_reference", "report_gate", "report_gate",
     "report_gate", "six-element report gate (8/8)"),
]


def fetch_online() -> dict:
    import os
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user = os.environ["TENSOR_AGENT_USER"]
    pw = os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": pw}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        token = json.load(r)["access_token"]
    req = urllib.request.Request(
        base + f"/tensor/reports/{CONTRACT['report_id']}",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_offline() -> dict:
    return json.loads((SRC_DIR / "report_5577.json").read_text(encoding="utf-8"))


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def build(record: dict, mode: str) -> tuple[dict, dict]:
    md = record["markdown"]
    h = sha256_hex(md)
    expected = CONTRACT["source_hash"].removeprefix("sha256:")
    if h != expected:
        raise SystemExit(f"source hash mismatch: recomputed {h} != contract {expected}")
    if len(md) != CONTRACT["chars"]:
        raise SystemExit(f"chars mismatch: observed {len(md)} != contract {CONTRACT['chars']}")

    assets = []
    # 1) source document (the markdown itself) — registered, resolvable
    assets.append({
        "asset_id": "ast-5577-01",
        "kind": "source_document",
        "role": "primary_source",
        "name": "report_5577_markdown",
        "locators": [{
            "source_uri": CONTRACT["source_uri"],
            "source_field": "markdown",
            "char_start": 0,
            "char_end": len(md.splitlines()[0]),
            "quote": md.splitlines()[0],
            "note": "first line (no H1 in this report); whole-document span in content_ref",
        }],
        "content_ref": {
            "source_uri": CONTRACT["source_uri"],
            "source_field": "markdown",
            "chars": len(md),
            "byte_length_utf8": len(md.encode("utf-8")),
            "sha256": f"sha256:{h}",
        },
        "resolvable": True,
        "resolution": "fetched_via_tensor_api",
        "status": "resolved",
    })
    # 2) record metadata
    assets.append({
        "asset_id": "ast-5577-02",
        "kind": "record_metadata",
        "role": "identification",
        "name": "report_5577_record",
        "locators": [
            {"source_uri": CONTRACT["source_uri"], "source_field": "record",
             "field": "id", "value": record["id"]},
            {"source_uri": CONTRACT["source_uri"], "source_field": "record",
             "field": "title", "value": record["title"]},
            {"source_uri": CONTRACT["source_uri"], "source_field": "record",
             "field": "scenario_key", "value": record["scenario_key"]},
            {"source_uri": CONTRACT["source_uri"], "source_field": "record",
             "field": "mission_id", "value": record["mission_id"]},
            {"source_uri": CONTRACT["source_uri"], "source_field": "record",
             "field": "status", "value": record["status"]},
            {"source_uri": CONTRACT["source_uri"], "source_field": "record",
             "field": "tags", "value": record["tags"]},
        ],
        "resolvable": True,
        "resolution": "fetched_via_tensor_api",
        "status": "resolved",
    })
    # 3) declared figures (record.figures: name+caption only, no byte payload)
    for i, fig in enumerate(record.get("figures") or []):
        assets.append({
            "asset_id": f"ast-5577-{3 + i:02d}",
            "kind": "figure",
            "role": "declared_figure",
            "name": fig["name"],
            "declared_metadata": {"caption": fig.get("caption")},
            "locators": [{
                "source_uri": CONTRACT["source_uri"],
                "source_field": "record",
                "field": f"figures[{i}].name",
                "value": fig["name"],
            }],
            "payload": {"present": False, "bytes": 0, "sha256": None},
            "resolvable": False,
            "status": "unresolved",
            "unresolved_reason": (
                "record.figures carries name+caption only (no png_base64); "
                "no byte payload in the report record, so the image content "
                "cannot be audited from this source"),
        })
    # 4) declared artifacts / endpoints / standards / literature (verbatim needles)
    for asset_id, kind, role, name, needle, note in ASSET_PLAN:
        start = md.find(needle)
        if start < 0:
            raise SystemExit(f"needle not found verbatim in markdown: {needle!r} "
                             f"(refusing to invent a locator)")
        end = start + len(needle)
        if md[start:end] != needle:
            raise SystemExit(f"locator self-check failed for {needle!r}")
        assets.append({
            "asset_id": asset_id,
            "kind": kind,
            "role": role,
            "name": name,
            "locators": [{
                "source_uri": CONTRACT["source_uri"],
                "source_field": "markdown",
                "char_start": start,
                "char_end": end,
                "quote": md[start:end],
                "note": note,
            }],
            "payload": {"present": False, "bytes": None, "sha256": None},
            "resolvable": False,
            "status": "unresolved",
            "unresolved_reason": (
                "referenced by name in the report markdown; the referenced "
                "object lives in the producing repo (ship-performance-platform) "
                "or on the platform, not in this report record"),
        })

    by_status: dict[str, int] = {}
    for a in assets:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1
    manifest = {
        "manifest_version": "1.0",
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "generated_by": "scripts/wp5577_register_assets.py",
        "scope": {
            "report_id": CONTRACT["report_id"],
            "reports_touched": [CONTRACT["report_id"]],
            "registers_assets_only": True,
            "extracts_claims": False,
            "classifies_report_type": False,
            "writes_outside_worktree": False,
        },
        "source": {
            "report_id": CONTRACT["report_id"],
            "source_uri": CONTRACT["source_uri"],
            "source_field": "markdown",
            "title": record["title"],
            "title_matches_contract": record["title"] == CONTRACT["title"],
            "scenario_key": record["scenario_key"],
            "scenario_key_matches_contract": record["scenario_key"] == CONTRACT["scenario_key"],
            "mission_id": record["mission_id"],
            "status": record["status"],
            "tags": record["tags"],
            "chars": len(md),
            "byte_length_utf8": len(md.encode("utf-8")),
            "sha256": f"sha256:{h}",
            "hash_check": {
                "expected": CONTRACT["source_hash"],
                "recomputed": f"sha256:{h}",
                "match": True,
            },
            "chars_check": {
                "expected": CONTRACT["chars"],
                "observed": len(md),
                "match": True,
            },
            "figures_entries": len(record.get("figures") or []),
        },
        "asset_counts": {
            "total": len(assets),
            "resolved": by_status.get("resolved", 0),
            "unresolved": by_status.get("unresolved", 0),
            "by_status": by_status,
        },
        "claims_policy": {
            "claims": [],
            "reason": (
                "contract objective is register_assets only (classify_report_type=false); "
                "constraints forbid forced claim generation, so claims is an empty array "
                "by design — no knowledge objects are minted in this work package"),
        },
        "assets": assets,
    }
    envelope = {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_hash": f"sha256:{h}",
            "source_field": "markdown",
            "producer": "agent/m15568",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": (
                "source_hash recomputed from the report-5577 markdown bytes fetched over "
                "the TensorPlatform API; equals the contract-declared hash "
                + CONTRACT["source_hash"]),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    return manifest, envelope


def verify_acceptance(manifest: dict, envelope: dict, record: dict) -> dict:
    md = record["markdown"]
    checks: dict = {}

    # valid_json: both artefacts round-trip (they are in memory; re-serialize+parse)
    ok = True
    try:
        json.loads(json.dumps(manifest, ensure_ascii=False))
        json.loads(json.dumps(envelope, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        ok = False
    checks["valid_json"] = {"ok": ok, "files": ["asset_manifest.json", "kf_result.json"]}

    # schema_pass: envelope against schemas/kf_result.v1.schema.json (Draft 2020-12)
    import jsonschema
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(e.message for e in validator.iter_errors(envelope))
    checks["schema_pass"] = {"ok": not errors,
                            "schema": "schemas/kf_result.v1.schema.json",
                            "errors": errors}

    # source_hash_matches
    recomputed = "sha256:" + sha256_hex(md)
    checks["source_hash_matches"] = {
        "ok": (recomputed == CONTRACT["source_hash"]
               == envelope["provenance"]["source_hash"]),
        "contract_declared": CONTRACT["source_hash"],
        "provenance": envelope["provenance"]["source_hash"],
        "recomputed_from_markdown_bytes": recomputed,
        "chars_expected": CONTRACT["chars"],
        "chars_observed": len(md),
        "chars_match": len(md) == CONTRACT["chars"],
    }

    # source_locator_resolvable: every markdown locator quote is a verbatim
    # substring at the recorded offsets
    failures = []
    n_checked = 0
    for a in manifest["assets"]:
        for loc in a.get("locators", []):
            if loc.get("source_field") != "markdown":
                continue
            n_checked += 1
            seg = md[loc["char_start"]:loc["char_end"]]
            if seg != loc["quote"]:
                failures.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "ok": not failures,
        "locators_checked": n_checked,
        "locators_resolved": n_checked - len(failures),
        "failures": failures,
    }

    # no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {
        "ok": not dup,
        "asset_id_count": len(ids),
        "duplicate_asset_ids": dup,
    }

    # all_claims_have_evidence_or_explicit_unresolved_status (vacuous for 01)
    claims = envelope.get("claims", [])
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": len(claims) == 0 and len(manifest["claims_policy"]["reason"]) >= 20,
        "claim_count": len(claims),
        "vacuous": len(claims) == 0,
        "claims_policy_reason_present": len(manifest["claims_policy"]["reason"]) >= 20,
        "failures": [],
    }

    # extra invariants
    missing = [a["asset_id"] for a in manifest["assets"]
               if a["status"] == "unresolved" and not a.get("unresolved_reason")]
    checks["unresolved_assets_have_reason"] = {"ok": not missing, "missing": missing}
    checks["reports_touched_single"] = {
        "ok": manifest["scope"]["reports_touched"] == [CONTRACT["report_id"]],
        "scope": manifest["scope"],
    }

    summary = {k: v["ok"] for k, v in checks.items()}
    return {"checks": checks, "ok": all(summary.values()), "summary": summary}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true",
                    help="read the source snapshot instead of calling the API")
    args = ap.parse_args(argv)
    mode = "offline" if args.offline else "online"
    record = fetch_offline() if args.offline else fetch_online()
    if record["id"] != int(CONTRACT["report_id"]):
        raise SystemExit(f"record id {record['id']} != {CONTRACT['report_id']}")

    manifest, envelope = build(record, mode)
    PKG_DIR.mkdir(parents=True, exist_ok=True)
    (PKG_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PKG_DIR / "kf_result.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    acc = verify_acceptance(manifest, envelope, record)
    acc["fetch_mode"] = mode
    (PKG_DIR / "acceptance.json").write_text(
        json.dumps(acc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(acc["summary"], ensure_ascii=False))
    return 0 if acc["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
