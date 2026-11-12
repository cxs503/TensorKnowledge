#!/usr/bin/env python3
"""Render the gate matrix / verification-ladder figure for the m15494 report.

Runs the three-gate validator over every offline fixture package and draws:

* left panel — rule × package outcome matrix (every G1/G2 rule, PASS vs FAIL);
* right panel — verification level reached per package, with the ceiling reason.

Every number in the figure comes from ``ke.wp_gate.run_gates`` (no hand-typed
values). Usage:

    python scripts/figures_wp_gate.py --out runs/m15494
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ke import wp_gate  # noqa: E402

FIXTURES = ("ok-basic", "ok-verified", "ok-zero-claim", "bad-no-evidence",
            "bad-source-hash", "bad-quote-offset", "bad-verified", "bad-self-review")
LEVEL_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}


def collect(fix_dir: Path) -> list[dict]:
    sources = fix_dir / "sources"
    return [wp_gate.run_gates(fix_dir / name, wp_gate.DirSourceResolver(sources),
                              review_ledger_dir=fix_dir / "ledgers",
                              tickets_dir=fix_dir / "tickets")
            for name in FIXTURES]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix-dir", default=str(REPO_ROOT / "tests" / "fixtures" / "extraction"))
    ap.add_argument("--out", default=str(REPO_ROOT / "runs" / "m15494"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    reports = collect(Path(args.fix_dir))
    (out / "gate-report.json").write_text(
        json.dumps({"gate": wp_gate.GATE_VERSION, "packages": reports}, indent=2,
                   ensure_ascii=False) + "\n", encoding="utf-8")

    # rule list in a stable order: all structural rules, then evidence rules
    rules = [c["name"] for c in reports[0]["structural"]["checks"]] + \
            [c["name"] for c in reports[0]["evidence"]["checks"]]
    matrix = []
    for rule in rules:
        row = []
        for rep in reports:
            ok = None
            for gate in ("structural", "evidence"):
                for c in rep[gate]["checks"]:
                    if c["name"] == rule:
                        ok = c["ok"]
            row.append(1 if ok else 0)
        matrix.append(row)

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(15, 8.5), gridspec_kw={"width_ratios": [3.0, 1.15]}
    )
    cmap = ListedColormap(["#d9584a", "#3f9c62"])
    ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(reports)))
    ax.set_xticklabels([r["package_id"].replace("wp-", "") for r in reports],
                       rotation=35, ha="right", fontsize=9)
    ax.set_yticks(range(len(rules)))
    ax.set_yticklabels(rules, fontsize=8)
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            ax.text(j, i, "P" if val else "F", ha="center", va="center",
                    fontsize=7, color="white", fontweight="bold")
    for i, name in enumerate(rules):
        if i and name.split(".")[0][0] != rules[i - 1].split(".")[0][0]:
            ax.axhline(i - 0.5, color="black", lw=1.2)
    ax.set_title("G1+G2 rule outcomes on the seven fixture packages\n"
                 f"({len(rules)} programmatic rules; P=pass, F=fail)", fontsize=11)

    levels = [r["verification"]["level"] for r in reports]
    reasons = [r["verification"]["ceiling_reason"] for r in reports]
    colors = {"L0": "#b03a2e", "L1": "#d68910", "L2": "#2e86c1", "L3": "#1e8449"}
    bars = ax2.bar(range(len(reports)), [LEVEL_ORDER[lv] for lv in levels],
                   color=[colors[lv] for lv in levels], width=0.62)
    ax2.set_xticks(range(len(reports)))
    ax2.set_xticklabels([r["package_id"].replace("wp-", "") for r in reports],
                        rotation=35, ha="right", fontsize=9)
    ax2.set_yticks(range(4))
    ax2.set_yticklabels(["L0 declared", "L1 structural", "L2 evidence", "L3 verified"], fontsize=9)
    ax2.set_ylim(0, 3.6)
    for bar, level, reason in zip(bars, levels, reasons):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.08, level,
                 ha="center", fontsize=9, fontweight="bold")
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2, reason,
                 ha="center", va="center", fontsize=6, color="white", rotation=90)
    ax2.set_title("verification_status ladder (computed, never authored)\n"
                  "L3 requires a confirmed platform ticket", fontsize=11)
    fig.suptitle("Report-to-knowledge production line v1 — three-gate validator, offline evidence "
                 "(m15494)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    target = out / "gate_matrix.png"
    fig.savefig(target, dpi=170)
    print("wrote", target)
    print("levels:", dict(zip(FIXTURES, levels)))
    print("verdicts:", sorted({r["verdict"] for r in reports}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())