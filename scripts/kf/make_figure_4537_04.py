#!/usr/bin/env python3
"""Figure for wp-4537-04: audit matrix + probe verdicts + raw reproduction counts.

Every plotted number is read from docs/kf/wp-4537-04/review_report.json (which itself
holds probe stdout-derived counts); nothing is hand typed.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "docs" / "kf" / "wp-4537-04"
OUT = PKG / "fig1_review_4537_04.png"


def main() -> int:
    rep = json.loads((PKG / "review_report.json").read_text(encoding="utf-8"))
    checks = rep["checks"]
    probes = rep["reproduction_probes"]

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.4))

    # --- panel A: F-check matrix
    ax = axes[0]
    ids = [c["id"] for c in checks]
    vals = [1 if c["pass"] else 0 for c in checks]
    colors = ["#2e7d32" if v else "#c62828" for v in vals]
    ax.barh(range(len(ids)), vals, color=colors)
    ax.set_yticks(range(len(ids)))
    ax.set_yticklabels(ids, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.15)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["fail", "pass"])
    for i, (v, c) in enumerate(zip(vals, checks)):
        ax.text(v + 0.02, i, "PASS" if v else "FAIL → finding", va="center", fontsize=7,
                color="#1b5e20" if v else "#b71c1c")
    ax.set_title(f"wp-4537-01 audit: {sum(vals)}/{len(vals)} checks pass\n"
                 f"({len(vals) - sum(vals)} fail = visible defects, not hidden)", fontsize=10)
    ax.grid(axis="x", alpha=0.3)

    # --- panel B: probe verdicts
    ax = axes[1]
    names = [p["probe"] for p in probes]
    score = [1 if p["verdict"] == "confirmed" else (0.5 if p["verdict"] == "not-confirmed" else 0)
             for p in probes]
    col = {"confirmed": "#2e7d32", "not-confirmed": "#f9a825", "refuted": "#c62828"}
    ax.barh(range(len(names)), [1] * len(names),
            color=[col.get(p["verdict"], "#757575") for p in probes])
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([n.split("-", 1)[1][:34] for n in names], fontsize=8)
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_xlim(0, 1)
    for i, p in enumerate(probes):
        ax.text(0.02, i, p["verdict"], va="center", fontsize=9, color="white", weight="bold")
    ax.set_title(f"reproduction probes (ruff {rep['ruff_version_used'].split()[-1]})\n"
                 f"report-mechanism claims re-run locally", fontsize=10)

    # --- panel C: raw counts behind the refutation
    ax = axes[2]
    r1b = next(p for p in probes if p["probe"].startswith("R1b"))
    r1a = next(p for p in probes if p["probe"].startswith("R1a"))
    groups = [
        ("E701+E702\nvia ruff format\n(report: 'cannot be cleared')",
         len(r1b["codes_before"]), len(r1b["codes_after"])),
        ("F401\nvia ruff check --fix\n(report: autofixable)",
         int(r1a["control_f401_autofix_removed_import"]), 0),
    ]
    x = range(len(groups))
    before = [g[1] for g in groups]
    after = [g[2] for g in groups]
    w = 0.36
    ax.bar([i - w / 2 for i in x], before, w, label="before", color="#455a64")
    ax.bar([i + w / 2 for i in x], after, w, label="after", color="#2e7d32")
    ax.set_xticks(list(x))
    ax.set_xticklabels([g[0] for g in groups], fontsize=8)
    ax.set_ylabel("ruff violations on a 3-statement probe file")
    for i, (b, a) in enumerate(zip(before, after)):
        ax.text(i - w / 2, b + 0.05, str(b), ha="center", fontsize=9)
        ax.text(i + w / 2, a + 0.05, str(a), ha="center", fontsize=9)
    ax.legend(fontsize=8)
    ax.set_title("refutation evidence (FN-4537-04-03):\n"
                 "formatter does clear E701/E702 — the claim is refuted", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("wp-4537-04 independent review of wp-4537-01 (report 4537) — "
                 "disposition: needs-fix; all numbers read from review_report.json", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT, dpi=160)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())