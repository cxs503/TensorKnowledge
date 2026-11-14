#!/usr/bin/env python3
"""wp-12595-01 · acceptance figure (data from fig_data.json, zero hand-typed numbers).

Left: referenced artifacts by kind (bar chart).
Right: acceptance self-check items (pass/fail markers).
"""
from __future__ import annotations

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
OUT = REPO / "docs" / "kf" / "wp-12595-01"


def main():
    d = json.loads((OUT / "fig_data.json").read_text(encoding="utf-8"))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=140)

    kinds = ["path", "glob", "field", "worktree", "branch"]
    vals = [d["by_kind"].get(k, 0) for k in kinds]
    bars = ax1.bar(kinds, vals, color="#4878a8")
    for b, v in zip(bars, vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.15, str(v), ha="center", fontsize=9)
    ax1.set_title(f"referenced artifacts by kind (n={d['n_refs']})")
    ax1.set_ylabel("count")
    ax1.set_ylim(0, max(vals) + 1.5)
    ax1.grid(axis="y", alpha=0.3)

    items = list(d["checks"].items())
    labels = [k for k, _ in items]
    ok = [v for _, v in items]
    y = list(range(len(items)))
    colors = ["#2e8b57" if v else "#c0392b" for v in ok]
    ax2.barh(y, [1] * len(items), color=colors, height=0.6)
    for i, v in enumerate(ok):
        ax2.text(1.02, i, "PASS" if v else "FAIL", va="center", fontsize=8,
                 color="#2e8b57" if v else "#c0392b", fontweight="bold")
    ax2.set_yticks(y, labels, fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 1.6)
    ax2.set_xticks([])
    ax2.set_title(f"acceptance self-check ({sum(ok)}/{len(items)} pass)")

    fig.suptitle(
        f"wp-12595-01 asset registration · report 12595 · "
        f"locators {d['n_resolved']}/{d['n_locators']} · sections {d['n_sections']} · "
        f"attachments {d['n_attachments']} · obs {d['n_obs']} ({d['n_unresolved']} unresolved)",
        fontsize=10,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    out = OUT / "fig_acceptance.png"
    fig.savefig(out, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
