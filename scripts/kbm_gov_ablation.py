#!/usr/bin/env python3
"""KBM governance W1 — calibration & sensitivity (controlled experiment).

Anchor: KBM-TKC-GOV-SCALE.  Everything here is computed from the *published*
pilot artefacts (``runs/kbm-gov-w1/``); nothing is re-extracted, so the numbers
are auditable line by line.

Predeclared design (fixed before running, see ``docs/kbm-gov-w1.md`` §3):

* **H1 (recall)** — cloning a real KO with its exact conditions and a value
  multiplied by ``m`` must yield a contradicted pair whenever the induced
  relative difference |1-1/m|/1 exceeds ``contradict_rel`` (15%), and must not
  yield one below ``agree_rel`` (5%).
* **H2 (false positives on real data)** — the untouched corpus is the control:
  its contradiction count is the baseline (observed 0).
* **H3 (dedupe stability)** — the duplicate rate must vary monotonically in the
  wording-similarity threshold; a flat curve would mean the threshold is inert.

Outputs: ``analysis.json`` + four figures (PNG) under ``runs/kbm-gov-w1/``.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import gov  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def load_kos(out: Path) -> list[dict]:
    return [json.loads(l) for l in (out / "ko.jsonl").read_text(encoding="utf-8").splitlines() if l]


def eligible_for_injection(kos: list[dict]) -> list[dict]:
    """Real KOs that can carry an adjudicable cross-source comparison."""
    return [k for k in kos
            if any(name != "geo" for name in k["conditions"])]


def inject(kos: list[dict], multiplier: float) -> list[dict]:
    clones = []
    for i, ko in enumerate(kos):
        c = copy.deepcopy(ko)
        c["id"] = "tkc:gov-inj:" + gov.sha256_text(f"{ko['id']}|{multiplier}")[:16]
        c["value"] = ko["value"] * multiplier
        c["source"] = {**ko["source"], "report_id": 900000 + i}
        c["synthetic"] = True
        clones.append(c)
    return clones


def _own_pair_hits(base: list[dict], clones: list[dict], cv: dict) -> tuple[int, int]:
    """(own-pair detections, collateral detections) for an injection set.

    Own pair = (source KO, its clone): the pair whose divergence we *induced*.
    Collateral pairs = contradicted pairs the injection created between a clone
    and some other real KO; they are reported separately, never counted as
    recall.
    """
    verdict = {(p["a"], p["b"]): p["verdict"] for p in cv["pairs"]}
    own = 0
    for src, cl in zip(base, clones):
        v = verdict.get((src["id"], cl["id"])) or verdict.get((cl["id"], src["id"]))
        own += int(v == "contradicted")
    return own, cv["n_contradiction_pairs"] - own


def recall_experiment(base_kos: list[dict], cfg: dict, multipliers) -> list[dict]:
    rows = []
    for m in multipliers:
        clones = inject(base_kos, m)
        cv = gov.cross_validate(list(base_kos) + clones, cfg)
        own, collateral = _own_pair_hits(base_kos, clones, cv)
        rows.append({
            "multiplier": m,
            "induced_rel_diff": round(abs(1 - 1 / m), 6),
            "n_injected": len(clones),
            "own_pair_detected": own,
            "recall": round(own / len(clones), 4) if clones else 0.0,
            "collateral_pairs": collateral,
            "contradiction_pairs": cv["n_contradiction_pairs"],
            "expected": ("agree" if abs(1 - 1 / m) <= cfg["thresholds"]["agree_rel"]
                         else "divergent" if abs(1 - 1 / m) <= cfg["thresholds"]["contradict_rel"]
                         else "contradicted"),
        })
    return rows


def contradiction_threshold_sweep(base_kos: list[dict], cfg: dict) -> list[dict]:
    """Vary contradict_rel on a 50% injected set: the detection boundary curve."""
    clones = inject(base_kos, 1.5)
    corpus = list(base_kos) + clones
    rows = []
    for thr in (0.05, 0.10, 0.15, 0.20, 0.30, 0.50):
        c = copy.deepcopy(cfg)
        c["thresholds"]["contradict_rel"] = thr
        cv = gov.cross_validate(corpus, c)
        own, collateral = _own_pair_hits(base_kos, clones, cv)
        rows.append({
            "contradict_rel": thr,
            "injected_recall": round(own / len(clones), 4),
            "collateral_pairs": collateral,
            "pairs": cv["n_contradiction_pairs"],
        })
    return rows


def dedupe_sensitivity(kos: list[dict], cfg: dict) -> list[dict]:
    rows = []
    for key, values in (("near_dup_jaccard", (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)),
                        ("near_dup_hamming", (0, 2, 4, 6, 8, 10, 12))):
        for v in values:
            c = copy.deepcopy(cfg)
            c["thresholds"][key] = v
            d = gov.dedupe(kos, c)
            rows.append({"parameter": key, "value": v,
                         "n_clusters": d["n_clusters"],
                         "duplicate_rate": round(d["duplicate_rate"], 6)})
    return rows


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def figures(out: Path, analysis: dict, stats: dict) -> dict:
    figdir = out / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    made = {}
    plt.rcParams.update({"figure.dpi": 130, "font.size": 9})

    # F1 — governance funnel with the three counting buckets
    c = stats["counts"]
    stages = ["B0 raw records\n(reports)", "quantity\ncandidates",
              "B1 KO pending\nreview", "review pass",
              "B2 governed\nobjects"]
    values = [c["raw_records"], c["quantity_statements"], c["ko_pending_review"],
              c["review_pass"], c["governed_objects"]]
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    bars = ax.bar(stages, values, color=["#4c72b0", "#8c8c8c", "#dd8452", "#55a868", "#c44e52"])
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v}", ha="center", va="bottom", fontsize=8)
    ax.set_yscale("log")
    ax.set_ylabel("count (log)")
    ax.set_title("KBM governance funnel — three counting口径 kept apart")
    fig.tight_layout()
    p = figdir / "f1-funnel.png"
    fig.savefig(p)
    plt.close(fig)
    made["f1-funnel"] = p

    # F2 — duplicate cluster sizes + dedupe layers
    d = json.loads((out / "dedup-clusters.json").read_text(encoding="utf-8"))
    hist = d["layer_counts"]["clusters_by_size"]
    sizes = [int(k) for k in hist]
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8))
    axes[0].bar([str(s) for s in sizes], [hist[str(s)] for s in sizes], color="#4c72b0")
    axes[0].set_xlabel("cluster size (KOs with the same claim)")
    axes[0].set_ylabel("clusters")
    axes[0].set_title(f"dedupe clusters (rate={d['duplicate_rate']:.1%})")
    layers = {"exact": d["layer_counts"]["exact"], "semantic": d["layer_counts"]["semantic"]}
    axes[1].bar(list(layers), list(layers.values()), color=["#55a868", "#dd8452"])
    for i, (k, v) in enumerate(layers.items()):
        axes[1].text(i, v, str(v), ha="center", va="bottom", fontsize=8)
    axes[1].set_title("duplicate clusters by layer")
    fig.tight_layout()
    p = figdir / "f2-dedup.png"
    fig.savefig(p)
    plt.close(fig)
    made["f2-dedup"] = p

    # F3 — contradiction detector calibration (recall vs induced divergence)
    rec = analysis["recall_experiment"]
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    ax.plot([r["induced_rel_diff"] for r in rec], [r["recall"] for r in rec], "o-",
            color="#c44e52", label="injected-pair recall")
    ax.axvline(analysis["thresholds"]["agree_rel"], ls="--", color="#55a868",
               label="agree_rel (5%)")
    ax.axvline(analysis["thresholds"]["contradict_rel"], ls="--", color="#8172b3",
               label="contradict_rel (15%)")
    ax.set_xlabel("induced relative difference |Δ|/max")
    ax.set_ylabel("recall on injected contradictions")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Contradiction Detection v1 calibration (real KO corpus + injection)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    p = figdir / "f3-contradiction-calibration.png"
    fig.savefig(p)
    plt.close(fig)
    made["f3-contradiction-calibration"] = p

    # F4 — review pool outcomes by gate lane
    votes = [json.loads(l) for l in
             (out / "review" / "votes.jsonl").read_text(encoding="utf-8").splitlines() if l]
    lanes = sorted({v["lane"] for v in votes})
    codes = sorted({v["code"] for v in votes})
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    bottom = [0] * len(lanes)
    cmap = plt.get_cmap("tab20")
    for i, code in enumerate(codes):
        vals = [sum(1 for v in votes if v["lane"] == ln and v["code"] == code) for ln in lanes]
        ax.bar(lanes, vals, bottom=bottom, label=code, color=cmap(i % 20))
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("votes")
    ax.set_title("Review pool — gate verdicts by lane (dual instances, quorum fold)")
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    p = figdir / "f4-review-lanes.png"
    fig.savefig(p)
    plt.close(fig)
    made["f4-review-lanes"] = p
    return {k: str(v.relative_to(out)) for k, v in made.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="KBM governance W1 calibration")
    ap.add_argument("--out", default="runs/kbm-gov-w1")
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out)
    cfg = gov.load_config(args.config)
    kos = load_kos(out)
    stats = json.loads((out / "stats.json").read_text(encoding="utf-8"))

    base = eligible_for_injection(kos)
    baseline = gov.cross_validate(kos, cfg)
    analysis = {
        "anchor": "KBM-TKC-GOV-SCALE",
        "corpus": {"n_ko": len(kos), "n_eligible_for_injection": len(base),
                   "n_with_numeric_conditions": len(base)},
        "thresholds": cfg["thresholds"],
        "control": {"contradiction_pairs_real_corpus": baseline["n_contradiction_pairs"],
                    "pair_verdicts": baseline["pair_verdicts"],
                    "document_local_subjects": baseline["document_local_subjects"]},
        "recall_experiment": recall_experiment(base, cfg, (1.02, 1.05, 1.10, 1.20, 1.35, 1.50, 2.0)),
        "contradiction_threshold_sweep": contradiction_threshold_sweep(base, cfg),
        "dedupe_sensitivity": dedupe_sensitivity(kos, cfg),
        "figures": figures(out, {"recall_experiment": recall_experiment(
            base, cfg, (1.02, 1.05, 1.10, 1.20, 1.35, 1.50, 2.0)),
            "thresholds": cfg["thresholds"]}, stats),
    }
    gov._dump_json(out / "analysis.json", analysis)
    print(json.dumps({k: analysis[k] for k in
                      ("corpus", "control", "recall_experiment", "figures")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())