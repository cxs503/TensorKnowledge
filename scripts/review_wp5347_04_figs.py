#!/usr/bin/env python3
"""Figures for the wp-5347-04 review: check matrix + per-asset locator outcome.

Numbers are read from docs/kf/wp-5347-04/review_evidence.json (programmatic, no hand-copy).
"""
import collections
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "docs", "kf", "wp-5347-04", "review_evidence.json")
OUT = os.path.join(ROOT, "docs", "kf", "wp-5347-04", "figures")


def main():
    ev = json.load(open(EV, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)

    checks = ev["checks"]
    # ---- fig 1: reviewer check matrix -------------------------------------
    names = [c["check"].split(".")[0] + "\n" + c["check"].split(".", 1)[1] for c in checks]
    vals = [1 if c["ok"] else 0 for c in checks]
    blocking = [c["blocking"] for c in checks]
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    colors = ["#2e7d32" if v else "#c62828" for v in vals]
    bars = ax.bar(range(len(checks)), vals, color=colors, width=0.62)
    for i, (b, c) in enumerate(zip(bars, checks)):
        ax.text(b.get_x() + b.get_width() / 2, 0.5, "PASS" if c["ok"] else "FAIL",
                ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        if not c["blocking"]:
            ax.text(b.get_x() + b.get_width() / 2, 1.06, "advisory", ha="center",
                    fontsize=7, color="#555555")
    ax.set_xticks(range(len(checks)))
    ax.set_xticklabels(names, fontsize=7)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["fail", "pass"])
    ax.set_ylim(0, 1.15)
    ax.set_title("wp-5347-04 reviewer recomputation matrix (source=%s)" % ev["source_hash"][:19],
                 fontsize=9)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    p1 = os.path.join(OUT, "review_check_matrix.png")
    fig.savefig(p1, dpi=150)
    plt.close(fig)

    # ---- fig 2: per-asset locator outcome --------------------------------
    man = json.load(open(ev["upstream_manifest"], encoding="utf-8"))
    kinds = collections.Counter((a["kind"], a["locator"]["locator_type"]) for a in man["assets"])
    bad = {a["asset_id"] for c in checks if not c["ok"]
           for a in c["detail"].get("violations", []) if "asset_id" in a}
    labels, okv, badv = [], [], []
    for (kind, ltype) in sorted(kinds):
        labels.append("%s\n(%s)" % (kind, ltype))
        tot = kinds[(kind, ltype)]
        nbad = sum(1 for a in man["assets"]
                   if (a["kind"], a["locator"]["locator_type"]) == (kind, ltype)
                   and a["asset_id"] in bad)
        badv.append(nbad)
        okv.append(tot - nbad)
    fig, ax = plt.subplots(figsize=(9.2, 4.0))
    x = range(len(labels))
    ax.bar(x, okv, color="#2e7d32", label="locator byte-exact")
    ax.bar(x, badv, bottom=okv, color="#c62828", label="quote not verbatim")
    for i in x:
        ax.text(i, okv[i] + badv[i] + 0.08, "%d" % (okv[i] + badv[i]), ha="center", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("assets")
    ax.set_title("registered assets %d: %d byte-exact, %d substituted (%s)"
                 % (len(man["assets"]), len(man["assets"]) - len(bad), len(bad),
                    ", ".join(sorted(bad))), fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    p2 = os.path.join(OUT, "asset_locator_outcome.png")
    fig.savefig(p2, dpi=150)
    plt.close(fig)
    print(json.dumps({"figures": [p1, p2], "assets": len(man["assets"]),
                      "bad_assets": sorted(bad)}, ensure_ascii=False))


if __name__ == "__main__":
    main()