#!/usr/bin/env python3
"""Stage-2 probes for the wp-11415-04 review: schema error enumeration,
artifact identity, and an end-to-end replay of the upstream verifier on the
*reconstructed* run inputs.

Reconstruction sources (no producer prose is read):
  report markdown  <- live platform payload (scripts/kf_fetch_11415_04.py)
  kf_result        <- the single ```json block of the published package
  manifest mirror  <- docs/kf/wp-11415-01/asset_manifest.json (committed)

Writes runs/wp-11415-04/stage2_probe.json
Run: python3 scripts/kf_probe_stage2_11415_04.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

import jsonschema

RUN = pathlib.Path("runs/wp-11415-04")
REPLAY = RUN / "replay"
PKG = pathlib.Path("docs/kf/wp-11415-01")
OUT = RUN / "stage2_probe.json"


def main() -> int:
    md = (RUN / "report_11415.md").read_text(encoding="utf-8")
    result = json.loads((RUN / "upstream_kf_result_wp-11415-01.json").read_text())
    man_md = result["outputs"]["asset_manifest.json"]
    report: dict = {"schema_errors": [], "identity": {}, "replay": {}}

    # ---- enumerate every envelope schema violation --------------------------
    schema = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text())
    v = jsonschema.Draft202012Validator(schema)
    report["schema_errors"] = [
        {"path": list(e.absolute_path), "message": e.message[:300]}
        for e in sorted(v.iter_errors(result), key=lambda e: list(e.absolute_path))
    ]

    # ---- artifact identity claims ------------------------------------------
    mirror = PKG / "asset_manifest.json"
    durable = pathlib.Path("artifacts/wp-11415-01/asset_manifest.json")
    blob = mirror.read_bytes()
    report["identity"] = {
        "mirror_path": str(mirror),
        "mirror_sha256": hashlib.sha256(blob).hexdigest(),
        "mirror_bytes": len(blob),
        "declared_artifact_sha256": result["provenance"].get("artifact_sha256"),
        "declared_artifact_bytes": result["provenance"].get("artifact_bytes"),
        "mirror_matches_declared": hashlib.sha256(blob).hexdigest()
        == result["provenance"].get("artifact_sha256"),
        "mirror_json_equals_published_block": json.loads(blob) == man_md,
        "durable_mirror_declared": str(durable),
        "durable_mirror_exists": durable.exists(),
        "run_dir_declared": "runs/wp-11415-01",
        "run_dir_exists": pathlib.Path("runs/wp-11415-01").exists(),
    }

    # ---- replay the upstream verifier in a scratch tree ---------------------
    if REPLAY.exists():
        shutil.rmtree(REPLAY)
    rdir = REPLAY / "runs/wp-11415-01"
    adir = REPLAY / "artifacts/wp-11415-01"
    rdir.mkdir(parents=True)
    adir.mkdir(parents=True)
    payload = json.loads((RUN / "report_11415.json").read_text())
    (rdir / "report_11415.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (rdir / "report_11415.md").write_text(md, encoding="utf-8")
    (rdir / "kf_result.wp-11415-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (adir / "asset_manifest.json").write_bytes(blob)
    mdir = REPLAY / "docs/kf/wp-11415-01"
    mdir.mkdir(parents=True)
    (mdir / "asset_manifest.json").write_bytes(blob)
    for extra in ("report_published.json", "fig_asset_locator_map.png"):
        src_extra = PKG / extra
        if src_extra.exists():
            shutil.copy2(src_extra, mdir / extra)
    (REPLAY / "docs/figures").mkdir(parents=True, exist_ok=True)
    for name in ("schemas", "scripts"):
        src = pathlib.Path(name).resolve()
        dst = REPLAY / name
        if not dst.exists():
            dst.symlink_to(os.path.relpath(src, REPLAY))   # relative -> portable
    proc = subprocess.run(
        [sys.executable, "scripts/kf_verify_11415.py"],
        cwd=REPLAY,
        capture_output=True,
        text=True,
    )
    vr = REPLAY / "runs/wp-11415-01/verify_report.json"
    report["replay"] = {
        "cwd": str(REPLAY),
        "exit": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
        "verify_report_produced": vr.exists(),
        "failed_checks": [],
    }
    if vr.exists():
        vrep = json.loads(vr.read_text())
        checks = vrep.get("checks", {})
        report["replay"]["failed_checks"] = [
            {"name": k, "detail": {kk: vv for kk, vv in val.items() if kk != "pass_"}}
            for k, val in checks.items()
            if isinstance(val, dict) and val.get("pass_") is False
        ]

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())