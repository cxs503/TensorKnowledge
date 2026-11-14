#!/usr/bin/env python3
"""Figure for the wp-11415-04 independent review.

Four panels, all data read from runs/wp-11415-04/*.json (no hand typing):
  A  per-check verdict matrix of the independent reviewer (C1..C10)
  B  asset-class inventory of the reviewed package (wp-11415-01)
  C  estate-wide kf_result.v1 conformance (context for finding F2)
  D  source-table internal arithmetic residuals (C10)

Run: python3 scripts/kf_figure_wp-11415-04.py
"""
from __future__ import annotations

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RUN = pathlib.Path("runs/wp-11415-04")
FIG = pathlib.Path("docs/kf/wp-11415-04/fig1_review_dashboard.png")


def main() -> int:
    checks = json.loads((RUN / "independent_checks.json").read_text())["checks"]
    man = json.loads((RUN / "upstream_asset_manifest_wp-11415-01.json").read_text())
    review = json.loads(pathlib.Path("docs/kf/wp-11415-04/review_report.json").read_text())
    md = (RUN / "report_11415.md").read_text(encoding="utf-8")

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("wp-11415-04 independent review of wp-11415-01 (report 11415, IS Code 2008 §2.3 weather criterion)",
                 fontsize=11)

    # ---- A: reviewer verdict matrix -------------------------------------
    ax = axes[0][0]
    ids = list(checks)
    ok = [checks[i]["status"] == "pass" for i in ids]
    ax.barh(range(len(ids)), [1] * len(ids),
            color=["#2e7d32" if o else "#c62828" for o in ok], edgecolor="white")
    ax.set_yticks(range(len(ids)))
    ax.set_yticklabels([i.split("_", 1)[0] for i in ids], fontsize=8)
    ax.set_xticks([])
    ax.set_xlim(0, 1)
    ax.invert_yaxis()
    for k, i in enumerate(ids):
        ax.text(0.02, k, "PASS" if ok[k] else "FAIL", va="center", ha="left",
                color="white", fontsize=8, fontweight="bold")
        ax.text(0.98, k, i.split("_", 1)[1].replace("_", " "), va="center", ha="right",
                color="white", fontsize=7)
    ax.set_title(f"A  reviewer checks: {sum(ok)}/{len(ids)} pass", fontsize=10)

    # ---- B: asset inventory --------------------------------------------
    ax = axes[0][1]
    by_class = man["counts"]["by_class"]
    items = sorted(by_class.items(), key=lambda kv: -kv[1])
    ax.barh(range(len(items)), [v for _, v in items], color="#1565c0")
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([k for k, _ in items], fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("assets")
    ax.set_title(f"B  reviewed package: {len(man['assets'])} assets in {len(items)} classes", fontsize=10)

    # ---- C: estate schema conformance ----------------------------------
    ax = axes[1][0]
    ev = [e for f in review["findings"] if f["id"] == "F2" for e in f["evidence"]
          if e["what"] == "estate-wide scan"][0]
    invalid = ev["packages_invalid"]
    valid = ev["packages_checked"] - invalid
    ax.bar(["kf_result.v1\nnon-conforming", "conforming"], [invalid, valid],
           color=["#c62828", "#2e7d32"])
    for k, v in enumerate([invalid, valid]):
        ax.text(k, v + 0.5, str(v), ha="center", fontsize=9)
    ax.set_ylabel("published KF-RESULT packages")
    ax.set_ylim(0, max(invalid, valid) * 1.18)
    ax.set_title(f"C  estate envelope conformance: {invalid}/{ev['packages_checked']} "
                 f"({ev['share_invalid']*100:.1f}%) fail schemas/kf_result.v1\n"
                 f"with top-level 'claims': {ev['envelopes_with_top_level_claims']} "
                 f"(reviewed package: non-conforming)", fontsize=9)

    # ---- D: source-table arithmetic residuals (recomputed here) ---------
    ax = axes[1][1]
    names, devs = [], []
    for line in md.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 14 and c[0].startswith("S") and "_" in c[0] and c[10].replace(".", "").isdigit():
            a, b, ratio = float(c[10]), float(c[11]), float(c[12])
            if a == 0:
                continue
            names.append(c[0])
            devs.append(abs(b / a - ratio) / ratio)
    ax.bar(range(len(names)), devs, color="#6a1b9a")
    ax.axhline(2e-3, color="black", ls="--", lw=1, label="contradiction threshold 2e-3")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("|b/a(table) - b/a(areas)| / b/a")
    ax.set_title("D  source self-consistency: residuals are 4-decimal rounding only", fontsize=10)
    ax.legend(fontsize=7)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150)
    print(f"wrote {FIG} ({FIG.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())