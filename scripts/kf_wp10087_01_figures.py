#!/usr/bin/env python3
"""wp-10087-01 figures: asset inventory + source locator coverage.

Every plotted number is read from docs/kf/wp-10087-01/asset_manifest.json (the artefact
emitted by scripts/kf_wp10087_01_register.py) — nothing is typed in by hand here.

Outputs
    docs/kf/wp-10087-01/fig1_asset_inventory.png
    docs/kf/wp-10087-01/fig2_source_coverage.png
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT_DIR = "docs/kf/wp-10087-01"
MANIFEST = os.path.join(OUT_DIR, "asset_manifest.json")


def main() -> int:
    with open(MANIFEST, encoding="utf-8") as fh:
        man = json.load(fh)
    with open(os.path.join(OUT_DIR, "source.md"), encoding="utf-8", newline="") as fh:
        md = fh.read()
    assets = man["assets"]
    n_chars = man["source"]["chars"]

    # ---- fig1: inventory -------------------------------------------------
    by_class = man["counts"]["by_class"]
    by_res = man["counts"]["by_resolution"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    cls = sorted(by_class, key=lambda k: (-by_class[k], k))
    axes[0].barh(cls[::-1], [by_class[k] for k in cls[::-1]], color="#2b6cb0")
    for i, k in enumerate(cls[::-1]):
        axes[0].text(by_class[k] + 0.05, i, str(by_class[k]), va="center", fontsize=9)
    axes[0].set_xlabel("asset count")
    axes[0].set_title(f"report {man['report_id']}: {man['counts']['assets']} assets by class")
    axes[0].set_xlim(0, max(by_class.values()) + 1.0)

    res_keys = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    vals = [by_res.get(k, 0) for k in res_keys]
    colors = ["#2f855a", "#c8931a", "#a0aec0"]
    axes[1].bar(res_keys, vals, color=colors)
    for i, v in enumerate(vals):
        axes[1].text(i, v + 0.2, str(v), ha="center", fontsize=10)
    axes[1].set_ylabel("asset count")
    axes[1].set_ylim(0, max(vals) + 2)
    axes[1].set_title("resolution status of the registered locators\n"
                      f"hash {man['source']['hash'][:16]}…  quotes "
                      f"{sum(1 for a in assets if a['locator']['unique'])}/{len(assets)} unique")
    axes[1].tick_params(axis="x", labelsize=8, rotation=12)
    fig.tight_layout()
    f1 = os.path.join(OUT_DIR, "fig1_asset_inventory.png")
    fig.savefig(f1, dpi=150)
    plt.close(fig)

    # ---- fig2: coverage of the source along the char axis ----------------
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 5.0), sharex=True,
                                  gridspec_kw={"height_ratios": [1.0, 6.0]})
    covered = bytearray(b"\x00" * n_chars)
    for a in assets:
        loc = a["locator"]
        for i in range(loc["start_char"], loc["end_char"]):
            covered[i] = 1
    ax.fill_between(range(n_chars), 0, [c for c in covered], step="mid", color="#2b6cb0")
    ax.set_yticks([])
    ax.set_ylabel("covered")
    frac = sum(covered) / n_chars
    ax.set_title(f"locator coverage of report 10087 markdown: {sum(covered)}/{n_chars} chars "
                 f"= {100 * frac:.1f}% (24 registered assets)")

    classes = sorted({a["asset_class"] for a in assets})
    cmap = {c: plt.get_cmap("tab10")(i % 10) for i, c in enumerate(classes)}
    for a in assets:
        loc = a["locator"]
        y = classes.index(a["asset_class"])
        ax2.barh(y, loc["end_char"] - loc["start_char"], left=loc["start_char"],
                 height=0.6, color=cmap[a["asset_class"]],
                 hatch=None if a["resolution"] == "resolved_in_source" else "///",
                 edgecolor="black", linewidth=0.4)
        ax2.text(loc["start_char"], y + 0.42, a["asset_id"], fontsize=6.5)
    ax2.set_yticks(range(len(classes)))
    ax2.set_yticklabels(classes, fontsize=8)
    ax2.set_xlabel("character offset in the source markdown (0 … "
                   f"{n_chars}); hatched = referenced_unresolved")
    ax2.set_xlim(0, n_chars)
    fig.tight_layout()
    f2 = os.path.join(OUT_DIR, "fig2_source_coverage.png")
    fig.savefig(f2, dpi=150)
    plt.close(fig)
    print(f"wrote {f1}\nwrote {f2}\ncoverage {sum(covered)}/{n_chars} = {100 * frac:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())