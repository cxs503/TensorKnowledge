#!/usr/bin/env python3
"""Single resolver for the pinned source snapshot of report 4537 (wp-4537-01).

Why this module exists
----------------------
The wp-4537-01 pack pins the sha256 of the report-4537 markdown and slices every
locator/quote span out of those exact bytes.  Originally those bytes only lived
in ``runs/m15537_wp4537_01/`` — a git-ignored run cache.  A clean checkout
therefore could not re-verify the pinned hash, the span resolution or the
builder determinism: the register/report scripts crashed with FileNotFoundError
and the gate test silently skipped.

The snapshot is now tracked next to the deliverables
(``docs/kf/wp-4537-01/source_report_4537.md``) and this module is the one place
that answers "where is the source?".  Resolution order:

1. tracked snapshot in ``docs/kf/wp-4537-01/`` (offline, reproducible, primary);
2. legacy run cache ``runs/m15537_wp4537_01/`` (kept for old worktrees).

Nothing here re-writes the snapshot: refreshing it is an explicit fetch
(``python3 scripts/kf/fetch_4537.py --out docs/kf/wp-4537-01``), so a stale copy
fails loudly on the hash instead of being silently updated.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG_DIR = ROOT / "docs" / "kf" / "wp-4537-01"

TRACKED_MD = PKG_DIR / "source_report_4537.md"
TRACKED_RECORD = PKG_DIR / "report_record_4537.json"
LEGACY_MD = ROOT / "runs" / "m15537_wp4537_01" / "source_report_4537.md"
LEGACY_RECORD = ROOT / "runs" / "m15537_wp4537_01" / "report_record_4537.json"

# Contract (report 4537, field `markdown`): UTF-8 bytes of tensor_reports.markdown.
PINNED_SHA256 = "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08"
PINNED_CHARS = 7931
PINNED_BYTES = 12973


def sha256_text(text: str) -> str:
    """sha256 of the UTF-8 bytes of ``text`` (the contract's hash scope)."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def md_path() -> Path:
    """Path of the source markdown snapshot (tracked first, then legacy cache)."""
    for cand in (TRACKED_MD, LEGACY_MD):
        if cand.exists():
            return cand
    raise FileNotFoundError(
        "no report-4537 source snapshot found; expected "
        f"{TRACKED_MD} (tracked) — refresh with "
        "`python3 scripts/kf/fetch_4537.py --out docs/kf/wp-4537-01`"
    )


def record_path() -> Path:
    """Path of the matching platform record metadata (markdown field stripped)."""
    for cand in (TRACKED_RECORD, LEGACY_RECORD):
        if cand.exists():
            return cand
    raise FileNotFoundError(f"no report-4537 record metadata found; expected {TRACKED_RECORD}")


def load_markdown() -> str:
    """Read the snapshot and verify it against the pinned contract hash."""
    path = md_path()
    md = path.read_text(encoding="utf-8")
    got = sha256_text(md)
    if got != PINNED_SHA256 or len(md) != PINNED_CHARS:
        raise ValueError(
            f"source snapshot {path} drifted from the pinned contract: "
            f"{got} / {len(md)} chars (expected {PINNED_SHA256} / {PINNED_CHARS})"
        )
    return md


def load_record() -> dict:
    """Read the pinned platform record metadata for report 4537."""
    return json.loads(record_path().read_text(encoding="utf-8"))


def load() -> tuple:
    """(markdown, record) — the exact pair the builder is deterministic on."""
    return load_markdown(), load_record()


if __name__ == "__main__":  # tiny CLI: print where the bytes come from
    md, _ = load()
    print(
        json.dumps(
            {
                "source_md": str(md_path().relative_to(ROOT)),
                "record": str(record_path().relative_to(ROOT)),
                "sha256": sha256_text(md),
                "chars": len(md),
                "bytes_utf8": len(md.encode("utf-8")),
            },
            ensure_ascii=False,
            indent=2,
        )
    )