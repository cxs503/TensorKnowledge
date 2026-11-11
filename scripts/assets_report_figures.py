#!/usr/bin/env python3
"""Figures for the asset-management report (programmatic, zero hand-copying).

Reads the *artefacts* (``artifacts/asset-index.json``) and a KE store, and
writes two PNGs:

1. ``fig1_registry_snapshot.png`` — per-package record counts (claims /
   evidence / provenance / gaps) exactly as pinned in the asset index;
2. ``fig2_evidence_attribution.png`` — left: the closed prototype's substring
   rule vs the exact-linkage rule on the KE fixture package; right: the
   domain-roll-up of the real ``knowledge/oss-lbm`` store (per-KO counts vs
   the number of distinct evidence records, i.e. the documented granularity
   limit).

Usage::

    python scripts/assets_report_figures.py --db /tmp/ke_assets.db --out /tmp/figs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ke import assets, store  # noqa: E402

KINDS = ("claims", "evidence", "provenance", "gaps")


def fig_registry(index_path: Path, out: Path) -> Path:
    doc = json.loads(index_path.read_text(encoding="utf-8"))
    entries = [e for e in doc["entries"] if e["asset_type"] == "knowledge_object"]
    labels = [e["metadata"]["ko_id"].replace("tko:", "") for e in entries]
    counts = {k: [max(0, (e["metadata"].get("counts") or {}).get(k, 0)) for e in entries]
              for k in KINDS}

    fig, ax = plt.subplots(figsize=(10, 4.8))
    bottom = [0] * len(labels)
    colors = {"claims": "#2c6fbb", "evidence": "#e08a1e", "provenance": "#4c9f70", "gaps": "#b4453b"}
    for kind in KINDS:
        ax.bar(labels, counts[kind], bottom=bottom, label=kind, color=colors[kind])
        bottom = [b + c for b, c in zip(bottom, counts[kind])]
    ax.set_ylabel("records")
    ax.set_title(f"Asset registry snapshot — {len(entries)} knowledge-object assets "
                 f"(records pinned by content digest)")
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.legend(frameon=False, ncol=4, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.text(0.01, 0.01, f"source: {index_path.name}  index_sha256="
             f"{doc['index_sha256'][:16]}…", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_attribution(db_path: str, fixture: Path, out: Path) -> Path:
    # left: fixture package (old substring rule vs exact linkage)
    fconn = store.connect(":memory:")
    store.ingest_pilot(fixture, fconn)
    fixture_domain = "research data stewardship principles"
    kos = ["tko:fixture", "tko:fair", "tko:ke-pilot"]
    old = [fconn.execute("SELECT COUNT(*) FROM evidence WHERE id LIKE ?",
                         (f"%{ko.split(':')[-1]}%",)).fetchone()[0] for ko in kos]
    exact = [assets.ko_evidence_count(fconn, ko) for ko in kos]
    rollup = assets.ko_evidence_count(fconn, "tko:fixture", domains=[fixture_domain])
    n_evidence = fconn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
    fconn.close()

    # right: real store, per-KO domain roll-up vs distinct evidence
    rconn = store.connect(db_path)
    ledger = assets.compute_quality_ledger(rconn)
    rconn.close()
    labels = [e["ko_id"].replace("tko:oss-lbm", ".") or "." for e in ledger]
    values = [e["evidence_count"] for e in ledger]
    distinct = max(values) if values else 0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    width = 0.38
    xs = range(len(kos))
    ax1.bar([x - width / 2 for x in xs], old, width, label="prototype substring rule", color="#b4453b")
    ax1.bar([x + width / 2 for x in xs], exact, width, label="exact linkage (this PR)", color="#2c6fbb")
    ax1.set_xticks(list(xs))
    ax1.set_xticklabels(kos, rotation=15, fontsize=8)
    ax1.set_ylabel("evidence records attributed")
    ax1.set_title(f"False attribution, fixture package ({n_evidence} evidence, 4 claims)")
    ax1.axhline(rollup, ls="--", lw=1, color="#4c9f70")
    ax1.annotate(f"declared-domain roll-up = {rollup}", (0.05, rollup + 0.15),
                 fontsize=8, color="#4c9f70")
    ax1.legend(frameon=False, fontsize=8)
    ax1.grid(axis="y", alpha=0.3)

    ax2.bar(labels, values, color="#2c6fbb")
    ax2.axhline(distinct, ls="--", lw=1, color="#b4453b")
    ax2.annotate(f"distinct evidence in store = {distinct}", (0.02, distinct * 0.94),
                 fontsize=8, color="#b4453b")
    ax2.set_ylabel("evidence records (domain roll-up)")
    ax2.set_title(f"Domain roll-up, knowledge/oss-lbm — sum={sum(values)} vs distinct={distinct}")
    ax2.tick_params(axis="x", rotation=30, labelsize=8)
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("Evidence attribution: exact contract linkage vs prototype substring matching", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default="/tmp/ke_assets.db")
    ap.add_argument("--index", default="artifacts/asset-index.json")
    ap.add_argument("--fixture", default="tests/fixtures/ke-pilot")
    ap.add_argument("--out", default="artifacts/figures")
    args = ap.parse_args(argv)
    out = Path(args.out)
    made = [
        fig_registry(Path(args.index), out / "fig1_registry_snapshot.png"),
        fig_attribution(args.db, Path(args.fixture), out / "fig2_evidence_attribution.png"),
    ]
    for p in made:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())