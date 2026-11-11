#!/usr/bin/env python3
"""Entry point for mission m5490 knowledge extraction (sediment line).

This is the main entry point that orchestrates the complete knowledge extraction
pipeline from TensorLBM mission m5490 (wave tank benchmark).

Pipeline:
1. Build knowledge entries (claims/evidence/provenance) from source repo
2. Verify all entries against schemas and source
3. Generate run artifacts (figures) from source data

Usage:
    TENSORLBM_REPO=/path/to/TensorLBM python3 scripts/sediment_m5490_entry.py
    
    If TENSORLBM_REPO is not set, defaults to /root/tp-agent/work/m8492/TensorLBM

Exit code 0 iff all stages pass.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"

# Default TensorLBM repo location if not specified
DEFAULT_TENSORLBM = "/root/tp-agent/work/m8492/TensorLBM"


def run_stage(name: str, cmd: list[str], env: dict) -> bool:
    """Run a pipeline stage and report result."""
    print(f"\n{'=' * 70}")
    print(f"Stage: {name}")
    print(f"{'=' * 70}")
    result = subprocess.run(cmd, cwd=REPO_ROOT, env=env)
    if result.returncode != 0:
        print(f"\n✗ {name} FAILED (exit code {result.returncode})")
        return False
    print(f"\n✓ {name} PASSED")
    return True


def main() -> int:
    """Main entry point."""
    print("=" * 70)
    print("Mission m5490 Knowledge Extraction Pipeline")
    print("Source: TensorLBM wave tank benchmark (PR #844)")
    print("Task key: tk-sediment-m5490")
    print("=" * 70)
    
    # Set up environment
    env = os.environ.copy()
    tensorlbm_repo = env.get("TENSORLBM_REPO", DEFAULT_TENSORLBM)
    env["TENSORLBM_REPO"] = tensorlbm_repo
    print(f"TensorLBM repo: {tensorlbm_repo}")
    
    stages = [
        ("Build knowledge entries", [
            sys.executable, str(SCRIPTS / "sediment_m5490_build.py")
        ]),
        ("Verify knowledge entries", [
            sys.executable, str(SCRIPTS / "verify_sediment_m5490.py")
        ]),
        ("Generate run artifacts", [
            sys.executable, str(SCRIPTS / "generate_m5490_artifacts.py")
        ]),
    ]
    
    results = []
    for name, cmd in stages:
        ok = run_stage(name, cmd, env)
        results.append((name, ok))
        if not ok:
            print(f"\n✗ Pipeline aborted at stage: {name}")
            return 1
    
    # Summary
    print("\n" + "=" * 70)
    print("Pipeline Summary")
    print("=" * 70)
    for name, ok in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"{status}: {name}")
    
    # Check deliverables
    pkg = REPO_ROOT / "knowledge" / "sediment" / "m5490"
    claims = len(list(pkg.glob("claim-*.json")))
    evidence = len(list(pkg.glob("evidence-*.json")))
    provenance = len(list(pkg.glob("provenance-*.json")))
    figures = len(list(pkg.glob("fig_*.png")))
    
    print(f"\nDeliverables in {pkg.relative_to(REPO_ROOT)}:")
    print(f"  - {claims} claim records")
    print(f"  - {evidence} evidence records")
    print(f"  - {provenance} provenance records")
    print(f"  - {figures} figure artifacts")
    print(f"  - INDEX.md (knowledge index)")
    print(f"  - review-status.json (review ledger)")
    
    print("\n" + "=" * 70)
    print("✓ All stages completed successfully")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
