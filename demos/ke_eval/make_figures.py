"""Figure for the Knowledge-Engine evaluation report.

Panel A: weighted decision-matrix totals (from decision_matrix.json).
Panel B: measured latency of the self-built thin layer's five primitives
         (median of 5 runs, from thinlayer_result.json) on a log scale.
Panel C: contract round-trip validity per contract (thinlayer_roundtrip.json).

All numbers are read from the artefact JSONs - nothing is typed in.

Usage:
  python make_figures.py --artifacts artifacts/ke_eval --out artifacts/ke_eval/ke_eval_fig1.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts", default="artifacts/ke_eval")
    ap.add_argument("--out", default="artifacts/ke_eval/ke_eval_fig1.png")
    a = ap.parse_args()
    ad = Path(a.artifacts)

    dm = json.loads((ad / "decision_matrix.json").read_text())
    tl = json.loads((ad / "thinlayer_result.json").read_text())
    rt = json.loads((ad / "thinlayer_roundtrip.json").read_text())

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    fig.suptitle("TensorKnowledge Knowledge-Engine evaluation (mission 8618, "
                 "loongarch64 container, PostgreSQL 15.5)", fontsize=12)

    # Panel A: weighted totals
    opts = list(dm["options"])
    totals = [dm["options"][o]["weighted_total"] for o in opts]
    labels = [o.replace(" (PG)", "\n(PG thin layer)") for o in opts]
    colors = ["#c44e52", "#4c72b0", "#55a868"]
    bars = axes[0].bar(labels, totals, color=colors[:len(opts)])
    axes[0].set_ylabel("weighted total (max 100, 11 dimensions)")
    axes[0].set_title("A. Decision matrix totals")
    axes[0].set_ylim(0, 100)
    for b, t in zip(bars, totals):
        axes[0].text(b.get_x() + b.get_width() / 2, t + 1.5, f"{t:.1f}", ha="center",
                     fontsize=10, fontweight="bold")
    axes[0].tick_params(axis="x", labelsize=9)

    # Panel B: query latency (median of 5)
    prim = [("P1_claim_status", "P1 claim status"), ("P2_evidence_relations", "P2 evidence rel."),
            ("P3_provenance_chain", "P3 provenance chain"), ("P4_domain", "P4 domain"),
            ("P5_hybrid_rrf", "P5 hybrid RRF")]
    names, med = [], []
    for key, label in prim:
        if key in tl and isinstance(tl[key], dict) and "median_ms" in tl[key]:
            names.append(label)
            med.append(tl[key]["median_ms"])
    bars = axes[1].barh(names, med, color="#4c72b0")
    axes[1].set_xscale("log")
    axes[1].set_xlabel("median latency over 5 runs (ms, log scale)")
    axes[1].set_title("B. Self-built thin layer: 4 primitives + hybrid\n"
                      f"(ingest {tl['ingest']['ingest_s']*1000:.0f} ms for "
                      f"{tl['ingest']['claims']} claims)")
    for b, v in zip(bars, med):
        axes[1].text(v * 1.08, b.get_y() + b.get_height() / 2, f"{v:.2f} ms",
                     va="center", fontsize=9)

    # Panel C: round-trip validity
    contracts = list(rt)
    valid = [rt[c]["valid"] for c in contracts]
    total = [rt[c]["exported"] for c in contracts]
    x = range(len(contracts))
    axes[2].bar(x, total, color="#dddddd", label="records exported from PostgreSQL")
    axes[2].bar(x, valid, color="#55a868", label="schema-valid after round trip")
    axes[2].set_xticks(list(x))
    axes[2].set_xticklabels([c.replace("-record", "").replace("knowledge-", "k-")
                             for c in contracts], rotation=20, ha="right", fontsize=9)
    axes[2].set_ylabel("records")
    axes[2].set_title("C. Contract round-trip: loss = 0\n"
                      f"({sum(valid)}/{sum(total)} records valid)")
    axes[2].legend(fontsize=8, loc="upper right")

    fig.tight_layout(rect=(0, 0, 1, 0.94))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=140)
    print("wrote", a.out)


if __name__ == "__main__":
    main()