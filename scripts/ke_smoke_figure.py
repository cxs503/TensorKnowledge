"""Render the KE API smoke figure from the raw artifacts (no hand-copied numbers).

Every value is read from ``artifacts/ke_smoke/*.json`` (the exact HTTP
responses saved by ``scripts/ke_smoke_oss_lbm.py``), so the figure and the
report tables cannot drift from the service output.

Usage: python3 scripts/ke_smoke_figure.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "ke_smoke"


def load(name: str):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def main() -> int:
    final = load("final_stats.json")
    summary = load("summary.json")
    q1a = load("q1_by_status_review_unreviewed.json")
    q1b = load("q1_by_status_evidence_established.json")
    q2 = load("q2_by_evidence_relation_supports.json")
    q3 = load("q3_chain.json")
    q4 = load("q4_by_domain.json")
    q5 = load("q5_claim_evidence.json")
    search = load("search_lattice.json")

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.6))

    # (a) objects by contract kind + edges
    ax = axes[0]
    kinds = list(final["by_kind"].keys())
    vals = [final["by_kind"][k] for k in kinds]
    bars = ax.bar(kinds + ["edges\n(claim↔evidence)"], vals + [final["edges"]],
                  color=["#2b6cb0", "#2f855a", "#805ad5", "#718096"])
    ax.set_title(f"real package ingested: {final['objects']} objects, "
                 f"{final['review_events']} review event(s)")
    ax.set_ylabel("count")
    for b, v in zip(bars, vals + [final["edges"]]):
        ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=9)

    # (b) evidence_status distribution (real data)
    ax = axes[1]
    dist = dict(sorted(final["evidence_status"].items(), key=lambda kv: -kv[1]))
    ax.barh(list(dist.keys()), list(dist.values()), color="#2b6cb0")
    ax.set_title("evidence_status axis (claim α / evidence assessment)")
    ax.set_xlabel("objects")
    ax.invert_yaxis()
    for i, v in enumerate(dist.values()):
        ax.text(v, i, f" {v}", va="center", fontsize=9)

    # (c) response size per query class
    ax = axes[2]
    labels = ["Q1 review\nunreviewed", "Q1 evidence\nestablished", "Q2 supports",
              "Q3 chain\nlinks", "Q3 package\nprov.", "Q4 by-domain", "Q5 claim→ev.",
              "search\n'lattice'"]
    counts = [q1a["count"], q1b["count"], q2["count"], len(q3["links"]),
              len(q3["package_provenance"]), q4["count"], q5["count"], search["count"]]
    cols = ["#a0aec0", "#2b6cb0", "#2f855a", "#2f855a", "#805ad5", "#2b6cb0",
            "#2b6cb0", "#d69e2e"]
    bars = ax.bar(range(len(labels)), counts, color=cols)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7.5, rotation=30, ha="right")
    ax.set_title("items returned per query endpoint")
    ax.set_ylabel("items")
    for b, v in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=8)

    fig.suptitle("TensorKnowledge KE HTTP API — live smoke run on knowledge/oss-lbm "
                 "(Postgres driver)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = ART / "ke_api_smoke.png"
    fig.savefig(out, dpi=150)
    print(json.dumps({"figure": str(out), "objects": final["objects"],
                      "edges": final["edges"],
                      "by_kind": final["by_kind"],
                      "anchor_claim": summary.get("anchor_claim")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())