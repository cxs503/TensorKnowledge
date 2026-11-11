#!/usr/bin/env python3
"""Build the m5054 sediment package (thin, mission-specific caller).

All extraction logic lives in :mod:`ke.sediment_extract`; this script only pins
the mission arguments so the command is short enough to quote in a report and
stable enough to be the ``repro_cmd`` of the package.

    python3 scripts/sediment_m5054_build.py            # build in place
    python3 scripts/sediment_m5054_build.py --out /tmp/m5054 --run-dir /tmp/run

Environment: ``TENSORSPH_REPO`` overrides the source checkout (default
``/root/tensor-ecosystem/TensorSPH``, which carries commit 82b72a15).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ke.sediment_extract import extract_package  # noqa: E402

SPEC = ROOT / "knowledge" / "sediment" / "tk-sediment-m5054" / "spec.json"
OUT = ROOT / "knowledge" / "sediment" / "tk-sediment-m5054"
RUN_DIR = ROOT / "docs" / "sediment" / "tk-sediment-m5054" / "runs" / "extract"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", default=str(SPEC))
    parser.add_argument("--source-repo",
                        default=os.environ.get("TENSORSPH_REPO",
                                               "/root/tensor-ecosystem/TensorSPH"))
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--run-dir", default=str(RUN_DIR))
    args = parser.parse_args(argv)
    summary = extract_package(args.spec, args.source_repo, args.out, args.run_dir)
    counts = summary["counts"]
    print(f"m5054 package: {counts['claims']} claims, {counts['evidence']} evidence, "
          f"{counts['provenance']} provenance, {counts['benchmark_rows']} benchmark rows")
    print(f"source pin   : {summary['source']['repo']} @ {summary['source']['sha']} "
          f"({summary['source']['commit_time']})")
    print(f"worst row    : {summary['benchmark_summary']['worst_row']} "
          f"{summary['benchmark_summary']['max_abs_rel_error_pct']:.3f}% off reference; "
          f"outside tolerance: {summary['benchmark_summary']['rows_outside_tolerance']}")
    print(f"manifest     : {Path(args.run_dir) / 'run_manifest.json'}")
    print("verify with  : python3 knowledge/sediment/tk-sediment-m5054/validate_m5054.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())