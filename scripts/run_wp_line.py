#!/usr/bin/env python3
"""Platform-facing entry point for the production line (five processes).

The platform dispatches shell commands, so this wrapper is the stable command
name; the logic lives in :mod:`ke.wp_line` (one implementation, two surfaces).

    python scripts/run_wp_line.py run --root <packages> --sources <dir> \
        --review-ledger-dir <dir> --tickets-dir <dir> --json <out.json>

Exit codes are the line's: 0 clean, 2 a package failed its exit gate,
3 the benchmark is below a declared threshold.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ke.wp_line import main  # noqa: E402  (same entry as ``python -m ke.wp_line``)

if __name__ == "__main__":
    raise SystemExit(main())