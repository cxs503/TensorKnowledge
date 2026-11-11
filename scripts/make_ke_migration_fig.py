#!/usr/bin/env python3
"""Render the KE migration parity figure from the reconciliation artefact (m8800).

Every number in the figure is read from ``artifacts/ke/migration-reconcile.json``
(produced by ``python -m ke.migrate``) — nothing is hand-typed, so the figure
cannot drift away from the machine-checked reconciliation.

Usage::

    python -m ke.migrate                                   # refresh the artefact
    python scripts/make_ke_migration_fig.py                # render the figure
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEFAULT_JSON = REPO / "docs" / "ke" / "migration-reconcile.json"
DEFAULT_PNG = REPO / "docs" / "ke" / "figures" / "m8800-migration-parity.png"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    ap.add_argument("--png", default=str(DEFAULT_PNG))
    args = ap.parse_args(argv)

    rep = json.loads(Path(args.json).read_text(encoding="utf-8"))
    rows = rep["rows"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2))

    # --- panel A: per-table row counts, SQLite staging vs PostgreSQL ---------
    labels = [r["table"] for r in rows]
    src = [r["source_rows"] for r in rows]
    dst = [r["target_rows"] for r in rows]
    x = range(len(labels))
    w = 0.38
    b1 = ax1.bar([i - w / 2 for i in x], src, w, label="SQLite staging", color="#8fb8de")
    b2 = ax1.bar([i + w / 2 for i in x], dst, w, label="PostgreSQL (authoritative)",
                 color="#1f4e79")
    ax1.bar_label(b1, fontsize=8)
    ax1.bar_label(b2, fontsize=8)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax1.set_ylabel("rows")
    ax1.set_title("A. Migration reconciliation: rows per table (row-level sha256 compared)", fontsize=10)
    ax1.legend(fontsize=8, frameon=False)
    ok = all(r["rows_match"] and r["digest_match"] for r in rows)
    ax1.text(0.02, 0.95, f"rows&digest match: {'ALL OK' if ok else 'MISMATCH'}",
             transform=ax1.transAxes, fontsize=9, va="top",
             color="#1a7f37" if ok else "#b42318")
    ax1.grid(axis="y", alpha=0.3)

    # --- panel B: distribution parity (claims_by_status) ---------------------
    stats = rep["assertions"]["stats"]
    dist = stats["claims_by_status"]
    keys = sorted(dist)
    ax2.barh(keys, [dist[k] for k in keys], color="#1f4e79", label="PostgreSQL (target)")
    ax2.barh(keys, [dist[k] for k in keys], height=0.35, color="#8fb8de",
             label="SQLite staging (source)")
    for i, k in enumerate(keys):
        ax2.text(dist[k] + 0.6, i, str(dist[k]), va="center", fontsize=8)
    ax2.set_xlabel("claims")
    ax2.set_title(f"B. Assertion distribution parity (claims={stats['claims']}, "
                  f"evidence={stats['evidence']}; source == target)", fontsize=10)
    ax2.legend(fontsize=8, frameon=False)
    ax2.set_xlim(0, max(dist.values()) * 1.18)
    ax2.grid(axis="x", alpha=0.3)

    fig.suptitle(
        "KE storage unification (m8800): SQLite staging -> PostgreSQL authoritative | "
        f"objects {rep['totals']['objects_source']}->{rep['totals']['objects_target']}, "
        f"relations {rep['totals']['relations_source']}->{rep['totals']['relations_target']}, "
        f"verdict={rep['verdict']}",
        fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    png = Path(args.png)
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png, dpi=150)
    print(f"wrote {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())