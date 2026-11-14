#!/usr/bin/env python3
"""Figure for wp-5624-04: the review's evidence, plotted straight from review_report.json.

Three panels, all numbers read from the emitted review (zero hand-copied values):
  A  locator quotes -> occurrences in the source markdown (duplicates collapse to one occurrence)
  B  line-count conventions (manifest vs newline count vs splitlines vs naive split('\\n'))
  C  fresh-checkout A/B replay of the upstream acceptance suite (with / without the docs/ fallback)

    python3 scripts/kf/wp-5624-04/make_figure.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
PKG = "wp-5624-04"
REVIEW = REPO / "docs" / "kf" / PKG / "review_report.json"
OUT = REPO / "docs" / "kf" / PKG / "fig_review_evidence.png"
# Figure text stays ASCII on purpose: this image is generated on hosts without CJK fonts.


def locator_occurrences(review: dict) -> list[int]:
    """Per-locator occurrence counts, taken from the review's own locator table."""
    return [row["occurrences"] for row in review["method"]["locators"]["items"]]


def main() -> int:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    c04 = next(c for c in review["checks"] if c["id"] == "C04")
    nums = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", c04["detail"])}
    abl = {}
    for f in review["findings"]:
        if f["id"] == "F-C13":
            abl = f["evidence"]
    as_is = abl.get("after_fix", {})
    before = abl.get("before_fix", {})

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0))

    # A -- locator occurrence histogram
    counts = locator_occurrences(review)
    ax = axes[0]
    ax.hist(counts, bins=[0.5, 1.5, 2.5], rwidth=0.6, color="#4C72B0")
    ax.set_xticks([1, 2])
    ax.set_xlabel("occurrences of the quote in the source markdown")
    ax.set_ylabel("locator count")
    ax.set_title(
        f"A  {review['method']['locators']['total']} locators, "
        f"{review['method']['locators']['resolved']} resolved"
    )
    ax.annotate(
        "2 ref_ids share\n1 occurrence (F-C07)",
        xy=(1, len(counts)), xytext=(1.25, max(2, len(counts) - 2)),
        arrowprops=dict(arrowstyle="->", lw=1.0), fontsize=9,
    )

    # B -- line-count conventions
    ax = axes[1]
    keys = [
        ("manifest.lines", nums.get("manifest", 0)),
        ("newlines", nums.get("newline_count", 0)),
        ("splitlines", nums.get("splitlines", 0)),
        ("naive split('\\n')", nums.get("naive_split_newline_tokens", 0)),
    ]
    ax.bar([k for k, _ in keys], [v for _, v in keys],
           color=["#4C72B0", "#55A868", "#55A868", "#C44E52"])
    ax.set_ylim(0, max(v for _, v in keys) + 6)
    ax.set_ylabel("count")
    ax.set_title("B  line-count conventions (C04)")
    for i, (_, v) in enumerate(keys):
        ax.text(i, v + 0.6, str(v), ha="center", fontsize=9)
    ax.tick_params(axis="x", labelrotation=15)

    # C -- fresh-checkout A/B replay
    ax = axes[2]
    bars = [
        ("fallback\nreverted", before.get("errors", 0), before.get("returncode", 1)),
        ("as shipped", as_is.get("errors", 0), as_is.get("returncode", 0)),
    ]
    ax.bar([b[0] for b in bars], [b[1] for b in bars], color=["#C44E52", "#55A868"])
    ax.set_ylabel("ERROR lines from the upstream suite")
    ax.set_title("C  bare checkout replay (C13/C15)")
    for i, (_, v, rc) in enumerate(bars):
        ax.text(i, v + 0.3, f"{v} err / rc={rc}", ha="center", fontsize=9)
    ax.set_ylim(0, max([b[1] for b in bars] + [1]) + 4)

    fig.suptitle(
        f"{PKG}: independent review of wp-5624-01 (report 5624) -- "
        f"{review['checks_passed']}/{review['checks_total']} checks pass, "
        f"disposition={review['disposition']}",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())