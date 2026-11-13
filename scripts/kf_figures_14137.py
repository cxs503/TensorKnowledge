"""Figures for wp-14137-01, generated from the manifest (no hand-typed numbers).

fig_asset_manifest.png
  left  : asset count by class, split by resolution verdict
  right : locator map -- where each registered asset sits in the 7569-char source markdown

Usage: python3 scripts/kf_figures_14137.py
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/wp-14137-01"
MANIFEST = ART / "asset_manifest.json"
OUT = ART / "fig_asset_manifest.png"

COLORS = {"resolved_in_source": "#2b8a3e", "referenced_unresolved": "#c92a2a",
          "declared_absent": "#868e96"}


def main() -> int:
    m = json.loads(MANIFEST.read_text())
    assets = m["assets"]
    md_chars = m["source"]["chars"]

    by_class = defaultdict(Counter)
    for a in assets:
        by_class[a["asset_class"]][a["resolution"]] += 1
    classes = sorted(by_class, key=lambda c: (-sum(by_class[c].values()), c))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 7.4),
                                   gridspec_kw={"width_ratios": [1.05, 1.45]})

    cum = [0] * len(classes)
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        vals = [by_class[c].get(res, 0) for c in classes]
        if not any(vals):
            continue
        ax1.barh(range(len(classes)), vals, left=cum, color=COLORS[res],
                 label=f"{res} (n={sum(vals)})", height=0.72, edgecolor="white")
        cum = [c + v for c, v in zip(cum, vals)]
    for i, c in enumerate(classes):
        ax1.text(cum[i] + 0.15, i, str(cum[i]), va="center", fontsize=9, color="#333")
    ax1.set_yticks(range(len(classes)))
    ax1.set_yticklabels(classes, fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("registered assets (n)")
    ax1.set_title(f"wp-14137-01 · {len(assets)} assets by class and resolution verdict", fontsize=11)
    ax1.legend(fontsize=9, loc="lower right", frameon=True)
    ax1.grid(axis="x", alpha=0.25)
    ax1.set_xlim(0, max(cum) + 1.6 if cum else 1)

    for i, a in enumerate(assets):
        loc = a["locator"]
        ax2.plot([loc["start_char"], loc["end_char"]], [i, i], lw=5,
                 color=COLORS[a["resolution"]], solid_capstyle="butt", alpha=0.85)
        ax2.text(loc["end_char"] + 60, i, a["asset_id"], va="center", fontsize=7.5, color="#444")
    ax2.set_ylim(len(assets) - 0.4, -0.6)
    ax2.set_xlim(0, md_chars * 1.03)
    ax2.set_xlabel(f"character offset in report 14137 markdown (total {md_chars} chars)")
    ax2.set_title("locator map: char span of every registered asset\n"
                  "(green = resolved in source, red = referenced but unresolved here)", fontsize=11)
    ax2.grid(axis="x", alpha=0.25)
    ax2.set_yticks([])
    handles = [plt.Line2D([0], [0], lw=5, color=COLORS[r],
                          label=f"{r} (n={m['counts']['by_resolution'].get(r, 0)})")
               for r in COLORS if m["counts"]["by_resolution"].get(r, 0)]
    ax2.legend(handles=handles, fontsize=9, loc="lower right")

    fig.suptitle("Report 14137 (DEM clump shape effect, round 2) — asset registration manifest, "
                 f"source sha256 {m['source']['hash'][:12]}…", fontsize=10.5)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    mirror = ROOT / "docs/wp-14137-01" / OUT.name   # artifacts/ is gitignored -> committed copy
    mirror.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(mirror, dpi=150)
    print("wrote", OUT, "and", mirror)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())