"""Figure for wp-10459-01: locator coverage of the registered assets over the report markdown.

Left panel  : char-offset span map of all assets (y = asset_id), coloured by resolution; section
              headings as vertical guides -> makes gaps and overlaps in registration visible.
Right panel : asset count by class, stacked by resolution.

Everything is read from docs/kf/wp-10459-01/asset_manifest.json (no numbers retyped here), and the
markdown char length comes from the manifest's source.chars.

Usage: python3 scripts/kf_wp10459_figures.py
Output: docs/kf/wp-10459-01/fig_asset_coverage.png
"""
from __future__ import annotations

import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
PKG = "wp-10459-01"
MAN = REPO / "docs/kf" / PKG / "asset_manifest.json"
OUT = REPO / "docs/kf" / PKG / "fig_asset_coverage.png"

COLORS = {"resolved_in_source": "#2f6fdb", "referenced_unresolved": "#e07b1f", "declared_absent": "#b03030"}


def main() -> None:
    man = json.loads(MAN.read_text(encoding="utf-8"))
    assets = man["assets"]
    n = len(assets)
    total = man["source"]["chars"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 8.2), gridspec_kw={"width_ratios": [2.15, 1]})

    # ---- left: span map
    for i, a in enumerate(assets):
        loc = a["locator"]
        y = n - i
        col = COLORS[a["resolution"]]
        x0, x1 = loc["start_char"], loc["end_char"]
        if loc["method"] == "document":
            x1 = min(x1, total)
        ax1.barh(y, max(x1 - x0, 8), left=x0, height=0.62, color=col,
                 alpha=0.92 if loc["method"] == "char_span" else 0.55,
                 edgecolor="none")
        ax1.plot([x1], [y], marker="|", color=col, ms=7)

    ax1.set_yticks([n - i for i in range(n)])
    ax1.set_yticklabels([a["asset_id"] for a in assets], fontsize=8)

    # section guides: earliest asset char offset per report section
    sees = {}
    for a in assets:
        s = a["in_report_section"]
        if s not in sees or a["locator"]["start_char"] < sees[s]:
            sees[s] = a["locator"]["start_char"]
    for s, x in sorted(sees.items(), key=lambda kv: kv[1]):
        ax1.axvline(x, color="#888888", lw=0.8, ls=":", zorder=0)
        ax1.text(x + 8, 0.55, s.split(" ")[0], rotation=90, va="bottom", fontsize=7, color="#444444")

    ax1.set_xlim(0, total)
    ax1.set_ylim(0.3, n + 0.9)
    ax1.set_xlabel("character offset in report 10459 markdown (chars = %d)" % total, fontsize=9)
    ax1.set_title("Asset locator spans over the source markdown\n(%d assets; bar = char span, tick = span end)"
                  % n, fontsize=10)
    ax1.grid(axis="x", lw=0.3, alpha=0.4)
    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)

    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[k]) for k in COLORS]
    ax1.legend(handles, ["%s (%d)" % (k, man["counts"]["by_resolution"].get(k, 0)) for k in COLORS],
               fontsize=8, loc="upper right", frameon=True)

    # ---- right: class x resolution stacked bars
    classes = sorted(man["counts"]["by_class"])
    ys = range(len(classes))
    left = [0] * len(classes)
    for res in COLORS:
        vals = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == res) for c in classes]
        ax2.barh(list(ys), vals, left=left, color=COLORS[res], label=res, height=0.7)
        left = [l + v for l, v in zip(left, vals)]
    ax2.set_yticks(list(ys))
    ax2.set_yticklabels(classes, fontsize=7.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("assets", fontsize=9)
    ax2.set_title("Registered assets by class, stacked by resolution\n(resolved=%d, unresolved=%d, absent=%d)"
                  % (man["counts"]["resolved_in_source"], man["counts"]["referenced_unresolved"],
                     man["counts"]["declared_absent"]), fontsize=10)
    ax2.grid(axis="x", lw=0.3, alpha=0.4)
    for spine in ("top", "right"):
        ax2.spines[spine].set_visible(False)

    fig.suptitle("wp-10459-01 asset registration -- report 10459 (sha256 %s..., %d chars)"
                 % (man["source"]["hash"][:16], total), fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print("wrote %s (%d bytes)" % (OUT.relative_to(REPO), OUT.stat().st_size))


if __name__ == "__main__":
    main()