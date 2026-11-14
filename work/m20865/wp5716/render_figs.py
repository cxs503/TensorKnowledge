#!/usr/bin/env python3
"""Render the two review figures from the check engine. NOT committed."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import checks_5716 as E

FIG = E.PKG / "figures"
FIG.mkdir(parents=True, exist_ok=True)
C = {c["id"]: c for c in E.checks}
MAXA = E.summary["arithmetic_checks"]["max_rel_dev_pct"]

VERDICT_COLOR = {
    "reproduced": "#1b7f3b",
    "self_consistent": "#2f6fb0",
    "contradicted": "#b22222",
    "gap": "#d98324",
    "withheld": "#6a6a6a",
}


def fig_errors():
    items = E.section6
    num = [i for i in items if i["value"] is not None]
    absd = [i for i in items if i["value"] is None]

    fig, axes = plt.subplots(1, 2, figsize=(15.4, 6.6))
    ax = axes[0]
    ys = list(range(len(num)))[::-1]
    vals = [max(i["value"], 1e-4) for i in num]
    colors = ["#1b7f3b" if v < 3 else "#d98324" if v < 15 else "#b22222" for v in vals]
    ax.barh(ys, vals, color=colors, height=0.62)
    for y, i in zip(ys, num):
        ax.text(max(i["value"], 1e-4) * 1.18, y, f"{i['value']:g}%", va="center", fontsize=8.5)
    ax.set_yticks(ys)
    ax.set_yticklabels([i["label_en"][:38] for i in num], fontsize=8)
    ax.set_xscale("log")
    ax.set_xlim(5e-5, 5e2)
    ax.axvline(3, color="#2f6fb0", ls="--", lw=1.3)
    ax.axvline(15, color="#b22222", ls="--", lw=1.3)
    ax.text(3.3, len(num) - 0.45, "3% owner line", color="#2f6fb0", fontsize=8)
    ax.text(16.5, len(num) - 0.45, "15% platform line", color="#b22222", fontsize=8)
    ax.set_xlabel("error declared in report 5716 / %  (log scale)")
    ax.set_title("A. what report 5716 declares in its own error table\n"
                 f"({len(num)} percent rows; {len(absd)} absolute-value rows not on a log axis: "
                 + ", ".join(i["label_en"][:20] for i in absd) + ")", fontsize=9.5)
    ax.grid(axis="x", alpha=0.25)

    ax = axes[1]
    arith = [c for c in E.checks if c["dev_kind"] == "recompute_vs_claim" and c["rel_dev_pct"] is not None]
    incons = [c for c in E.checks
              if c["verdict"] in ("contradicted", "gap") and c["rel_dev_pct"] is not None]
    rows = [(f"{c['id']} recompute-vs-claim", max(c["rel_dev_pct"], 1e-4), "#1b7f3b") for c in arith] + \
           [(f"{c['id']} in-report inconsistency", max(c["rel_dev_pct"], 1e-4), "#b22222") for c in incons]
    ys = list(range(len(rows)))[::-1]
    ax.barh(ys, [r[1] for r in rows], color=[r[2] for r in rows], height=0.62)
    for y, r in zip(ys, rows):
        ax.text(r[1] * 1.18, y, f"{r[1]:.2f}%", va="center", fontsize=7.8)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=7.6)
    ax.set_xscale("log")
    ax.set_xlim(4e-5, 3e2)
    ax.axvline(3, color="#2f6fb0", ls="--", lw=1.3)
    ax.axvline(15, color="#b22222", ls="--", lw=1.3)
    ax.set_xlabel("deviation measured by this review / %  (log scale)")
    ax.set_title("B. this package's own deviations\n"
                 f"green = recomputation vs claim (n={len(arith)}, max {MAXA:.2f}%, all <3%) | "
                 f"red = document-level inconsistency (n={len(incons)})", fontsize=9.5)
    ax.grid(axis="x", alpha=0.25)

    fig.suptitle("wp-5716-04 independent review — error audit of report 5716 (IN10-G1 ice-navigation "
                 "campaign acceptance gate)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = FIG / "fig_review_errors.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote", out)


def fig_closure():
    fig = plt.figure(figsize=(15.4, 7.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[2.9, 2.0], width_ratios=[2.2, 1.0])

    ax = fig.add_subplot(gs[0, :])
    per_row = 6
    rows_n = (len(E.checks) + per_row - 1) // per_row
    for n, c in enumerate(E.checks):
        r, col = divmod(n, per_row)
        y = rows_n - r
        ax.add_patch(Rectangle((col, y), 0.94, 0.82, facecolor=VERDICT_COLOR[c["verdict"]],
                               alpha=0.9, ec="white"))
        ax.text(col + 0.47, y + 0.56, c["id"], ha="center", va="center", color="white",
                fontsize=10, fontweight="bold")
        ax.text(col + 0.47, y + 0.22, c["verdict"].replace("_", " "), ha="center", va="center",
                color="white", fontsize=6.4)
    ax.set_xlim(-0.05, per_row)
    ax.set_ylim(0.6, rows_n + 1.05)
    ax.axis("off")
    ax.set_title(f"A. all {len(E.checks)} independent checks, coloured by verdict", fontsize=10)
    handles = [Rectangle((0, 0), 1, 1, facecolor=v, alpha=0.9) for v in VERDICT_COLOR.values()]
    ax.legend(handles, list(VERDICT_COLOR), loc="lower right", ncol=5, fontsize=8, frameon=False)

    ax = fig.add_subplot(gs[1, 0])
    order = ["reproduced", "self_consistent", "contradicted", "gap", "withheld"]
    counts = [E.summary["by_verdict"].get(k, {"n": 0})["n"] for k in order]
    ax.barh(order[::-1], counts[::-1], color=[VERDICT_COLOR[k] for k in order[::-1]], height=0.6)
    for i, v in enumerate(counts[::-1]):
        ax.text(v + 0.08, i, str(v), va="center", fontsize=9)
    ax.set_xlabel("number of checks")
    ax.set_title("B. verdict census", fontsize=10)
    ax.set_xlim(0, max(counts) + 1.2)
    ax.grid(axis="x", alpha=0.25)

    ax = fig.add_subplot(gs[1, 1])
    ax.axis("off")
    lines = [
        "disposition: approve_with_notes",
        "blocking issues: 0",
        "must fix before downstream use: F1 F2 F4",
        "",
        f"recompute-vs-claim checks : {E.summary['arithmetic_checks']['n']}"
        f"   max {MAXA:.2f}%  (<3%: {E.summary['arithmetic_checks']['all_under_3pct']})",
        f"document inconsistencies : {E.summary['document_inconsistencies']['n']}"
        f"   ({len(E.summary['document_inconsistencies']['ids_over_3pct'])} at or over 3%)",
        f"honest FAILs confirmed   : {', '.join(E.summary['honest_fails_confirmed'])}",
        f"withheld (not pass)      : {', '.join(E.summary['withheld_ids'])}",
        "",
        f"source sha256 {E.SHA[:20]}...",
        f"           == wp-5716-01 registration: {E.SHA == E.REG_HASH}",
    ]
    ax.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=8.4, family="monospace")
    ax.set_title("C. closure ledger", fontsize=10)

    fig.suptitle("wp-5716-04 closure — 6 reproduced · 7 self-consistent · 5 contradicted · 4 gap · "
                 "2 withheld", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = FIG / "fig_review_closure.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    fig_errors()
    fig_closure()