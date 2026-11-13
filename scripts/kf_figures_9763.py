"""Figures for wp-9763-01 (asset registration of report 9763).

All numbers plotted are read back from artifacts/wp-9763-01/asset_manifest.json and
verification.json -- nothing is typed in by hand. Labels are ASCII because the container has no CJK
font; the report body carries the Chinese captions.

Outputs: artifacts/wp-9763-01/fig{1,2,3}_*.png (+ docs/kf/wp-9763-01/figures/ mirrors)
Usage:  python3 scripts/kf_figures_9763.py
"""
from __future__ import annotations

import json
import pathlib
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(".")
ART = ROOT / "artifacts/wp-9763-01"
DOC = ROOT / "docs/kf/wp-9763-01/figures"


def main() -> int:
    man = json.loads((ART / "asset_manifest.json").read_text())
    ver = json.loads((ART / "verification.json").read_text())
    ART.mkdir(parents=True, exist_ok=True)
    DOC.mkdir(parents=True, exist_ok=True)

    # --- fig1: asset classes by resolution status ---------------------------
    classes = sorted(man["counts"]["by_class"])
    states = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    colors = {"resolved_in_source": "#2c7fb8", "referenced_unresolved": "#e08214", "declared_absent": "#bdbdbd"}
    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=160)
    left = [0] * len(classes)
    for st in states:
        vals = [sum(1 for a in man["assets"] if a["asset_class"] == c and a["resolution"] == st) for c in classes]
        ax.barh(classes, vals, left=left, color=colors[st], label=st)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_xlabel("asset count")
    ax.set_title(f"wp-9763-01 / report 9763 asset inventory: {man['counts']['assets']} assets, "
                 f"{len(classes)} classes", fontsize=11)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    for i, c in enumerate(classes):
        if man["counts"]["by_class"][c] > 1:
            ax.text(man["counts"]["by_class"][c] + 0.05, i, str(man["counts"]["by_class"][c]),
                    va="center", fontsize=7)
    fig.tight_layout()
    f1 = ART / "fig1_asset_inventory.png"
    fig.savefig(f1)
    plt.close(fig)

    # --- fig2: locator map over the 3884-char source ------------------------
    fig, ax = plt.subplots(figsize=(11, 7.2), dpi=160)
    for i, a in enumerate(man["assets"]):
        loc = a["locator"]
        c = colors[a["resolution"]]
        ax.plot([loc["start_char"], loc["end_char"]], [i, i], lw=5, color=c, solid_capstyle="butt")
    ax.set_yticks(range(len(man["assets"])))
    ax.set_yticklabels([f"{a['asset_id']} {a['asset_class']}" for a in man["assets"]], fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlim(0, man["source"]["chars"])
    ax.set_xlabel("character offset in report 9763 markdown")
    ax.set_title(f"locator coverage: {man['source']['chars']} chars, {man['counts']['assets']} assets, "
                 f"all quotes unique substrings", fontsize=11)
    ax.grid(axis="x", alpha=0.3)
    handles = [plt.Line2D([], [], color=colors[s], lw=5, label=s) for s in states if s != "declared_absent"]
    ax.legend(handles=handles, fontsize=8, loc="lower right")
    fig.tight_layout()
    f2 = ART / "fig2_locator_coverage.png"
    fig.savefig(f2)
    plt.close(fig)

    # --- fig3: self-check + cross-check board ------------------------------
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(13, 6.4), dpi=160,
                                   gridspec_kw={"width_ratios": [1.25, 1]})
    names = [c["check"] for c in ver["checks"]]
    vals = [1 if c["result"] == "pass" else 0 for c in ver["checks"]]
    axa.barh(names, vals, color=["#2c7fb8" if v else "#d7301f" for v in vals])
    axa.set_xlim(0, 1.25)
    axa.set_xticks([0, 1])
    axa.set_xticklabels(["fail", "pass"])
    axa.invert_yaxis()
    axa.set_title(f"acceptance self-check (scripts/kf_verify_9763.py): overall {ver['overall']}", fontsize=10)
    axa.tick_params(axis="y", labelsize=7)

    cc = man["cross_checks"]
    cmap = {"consistent": "#2c7fb8", "inconsistent": "#e08214", "unresolved": "#807dba", "not_adjudicated": "#bdbdbd"}
    xs = [c["check_id"].split("_")[0] for c in cc]
    axb.bar(range(len(cc)), [1] * len(cc), color=[cmap.get(c["result"], "#999999") for c in cc])
    axb.set_xticks(range(len(cc)))
    axb.set_xticklabels([f"{x}\n{c['result']}" for x, c in zip(xs, cc)], fontsize=7, rotation=0)
    axb.set_yticks([])
    axb.set_title("source cross-checks (registered, not adjudicated here)", fontsize=10)
    fig.tight_layout()
    f3 = ART / "fig3_verification_board.png"
    fig.savefig(f3)
    plt.close(fig)

    for f in (f1, f2, f3):
        shutil.copyfile(f, DOC / f.name)
        print(f.name, f.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())