#!/usr/bin/env python3
"""Emit ``knowledge/assets/wp-5406-01/kf_result.json`` — the KF-RESULT payload of
work package wp-5406-01 (01-asset-registration, report 5406).

Every hash and count is read from the artifacts on disk, so none of them is
hand-copied into the report. ``provenance.source_hash`` is recomputed from the
report's markdown bytes at emission time and asserted against the contract.

    python scripts/wp5406_kf_result.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "knowledge" / "assets" / "wp-5406-01"
CONTRACT_HASH = ("sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc"
                 "2732ede8a")


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    checks = json.loads((PKG / "self_checks.json").read_text(encoding="utf-8"))
    platform = json.loads((PKG / "platform_resolver_check.json").read_text(encoding="utf-8"))
    snapshot = PKG / "source_snapshot.md"
    body_hash = "sha256:" + hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert body_hash == CONTRACT_HASH, f"snapshot hash drifted: {body_hash}"
    assert manifest["source"]["computed_source_hash"] == CONTRACT_HASH

    result = {
        "package_id": "wp-5406-01",
        "task_type": "01-asset-registration",
        "report_id": "5406",
        "provenance": {
            "source_uri": "tensor://reports/5406",
            "source_field": "markdown",
            "source_hash": body_hash,
            "source_chars": manifest["source"]["chars"],
            "source_bytes": manifest["source"]["bytes"],
            "hash_recomputed_by": "scripts/wp5406_kf_result.py (sha256 of the fetched markdown bytes)",
            "platform_cross_check": {
                "library": "ke.wp_gate.ApiSourceResolver",
                "platform_sha256": platform["platform_sha256"],
                "agrees": platform["hash_agrees_with_contract"],
            },
            "pipeline": "KBM-RCI-F1-FACTORY",
            "work_package": "wp-5406-01",
            "lane": "C",
            "report_snapshot": "knowledge/assets/wp-5406-01/source_snapshot.md",
            "record_snapshot": "knowledge/assets/wp-5406-01/report_record.json",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": "knowledge/assets/wp-5406-01/asset_manifest.json",
                "sha256": sha(PKG / "asset_manifest.json"),
                "attachments": manifest["counts"]["attachments"],
                "figures": manifest["counts"]["figures"],
                "unresolved": manifest["counts"]["unresolved"],
                "with_bytes_available": manifest["counts"]["with_bytes_available"],
                "checks_passed": checks["all_pass"],
            },
            "self_checks.json": {
                "path": "knowledge/assets/wp-5406-01/self_checks.json",
                "sha256": sha(PKG / "self_checks.json"),
                "checks": len(checks["checks"]),
                "failed": [c["name"] for c in checks["checks"] if not c["pass"]],
            },
            "platform_resolver_check.json": {
                "path": "knowledge/assets/wp-5406-01/platform_resolver_check.json",
                "sha256": sha(PKG / "platform_resolver_check.json"),
                "hash_agrees_with_contract": platform["hash_agrees_with_contract"],
            },
            "source_snapshot.md": {
                "path": "knowledge/assets/wp-5406-01/source_snapshot.md",
                "sha256": sha(snapshot),
            },
            "asset_reachability.png": {
                "path": "knowledge/assets/wp-5406-01/asset_reachability.png",
                "sha256": sha(PKG / "asset_reachability.png"),
            },
        },
        "repro_cmd": ("python scripts/wp5406_asset_manifest.py --offline-from "
                      "knowledge/assets/wp-5406-01/report_record.json && python "
                      "scripts/wp5406_asset_figure.py && python scripts/wp5406_kf_result.py"),
    }
    out = PKG / "kf_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    print(json.dumps(result["outputs"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())