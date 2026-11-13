#!/usr/bin/env python3
"""Mirror the wp-297-01 deliverables into a committed path.

Why: this repository's `.gitignore` drops `artifacts/**` (run-record area), so the
working products would never reach the pushed branch.  This script copies the
byte-identical set into `docs/kf-wp-297-01/` (committed) and verifies the copies
hash-equal to the originals.  It does not touch `asset_manifest.json`, the report
markdown or anything else, so a mirror refresh cannot invalidate the published
report.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
MIRROR = REPO / "docs" / "kf-wp-297-01"

DATA = [
    "asset_manifest.json",
    "kf_result.wp-297-01.json",
    "checks.json",
    "verify_delivery.json",
    "readback.json",
    "README.md",
    "source_report_297.md",
    "build_manifest.py",
    "build_report.py",
    "verify_delivery.py",
    "publish_report.py",
    "sync_mirror.py",
]
FIGURES = ["figures/asset_locator_map.png"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    MIRROR.mkdir(parents=True, exist_ok=True)
    (MIRROR / "figures").mkdir(exist_ok=True)
    manifest = []
    for rel in DATA + FIGURES:
        src = OUT / rel
        if not src.exists():
            manifest.append({"path": rel, "status": "missing_at_source"})
            continue
        dst = MIRROR / rel
        shutil.copy2(src, dst)
        a, b = sha(src), sha(dst)
        manifest.append({"path": f"docs/kf-wp-297-01/{rel}", "sha256": a, "identical": a == b, "bytes": src.stat().st_size})
    ok = all(m.get("identical") for m in manifest)
    (MIRROR / "mirror_manifest.json").write_text(
        json.dumps({"source_dir": "artifacts/kf-wp-297-01", "all_identical": ok, "files": manifest}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    for m in manifest:
        print(("OK   " if m.get("identical") else "FAIL ") + m["path"])
    print(f"mirror_all_identical={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())