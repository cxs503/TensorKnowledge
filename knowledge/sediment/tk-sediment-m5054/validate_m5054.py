#!/usr/bin/env python3
"""Verify the m5054 sediment package (entry point kept next to the package).

    python3 knowledge/sediment/tk-sediment-m5054/validate_m5054.py
    python3 knowledge/sediment/tk-sediment-m5054/validate_m5054.py --source-repo /path/to/TensorSPH

Exit codes: 0 all checks passed, 1 a check failed, 3 the pinned commit is not
available locally (source-dependent checks were NOT run, not silently skipped).
Writes ``runs/m5054/validate/validate_report.json`` by default.
"""
from __future__ import annotations

import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
ROOT = PKG.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ke.sediment_verify import main as verify_main  # noqa: E402

DEFAULT_REPORT = (ROOT / "docs" / "sediment" / "tk-sediment-m5054" / "runs"
                  / "validate" / "validate_report.json")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--package" not in argv:
        argv += ["--package", str(PKG)]
    if "--spec" not in argv:
        argv += ["--spec", str(PKG / "spec.json")]
    if "--schemas" not in argv:
        argv += ["--schemas", str(ROOT / "schemas")]
    if "--report" not in argv and "--no-report" not in argv:
        argv += ["--report", str(DEFAULT_REPORT)]
    return verify_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())