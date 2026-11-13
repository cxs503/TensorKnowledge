"""wp-9147-01 figure: asset locator map over the report markdown.

Programmatic: every bar is drawn from docs/kf/wp-9147-01/asset_manifest.json (start_char/end_char),
so the figure carries no hand-typed number. Colors encode the three resolution states.

Output: docs/kf/wp-9147-01/figures/asset_locator_map.png
Usage:  python3 scripts/kf_wp9147_01_figure.py
"""
from __future__ import annotations

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

PKG = pathlib.Path("docs/kf/wp-9147-01")
OUT = PKG / "figures" / "asset_locator_map.png"
COLORS = {
    "resolved_in_source": "#2b8a3e",
    "referenced_unresolved": "#e8590c",
    "declared_absent": "#862e9c",
}
ORDER = list(COLORS)


def main() -> None:
    m = json.loads((PKG / "asset_manifest.json").read_text())
    n = m["source"]["chars"]
    assets = m["assets"]

    fig, ax = plt.subplots(figsize=(12, 0.55 * len(assets) + 1.8))
    for i, a in enumerate(assets):
        y = len(assets) - i - 1
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        ax.barh(y, e - s, left=s, height=0.62, color=COLORS[a["resolution"]], alpha=0.9,
                edgecolor="black", linewidth=0.4)
        ax.text(e + n * 0.006, y, f'{a["asset_id"]} · {e - s} ch', va="center", fontsize=8)
    ax.set_yticks([len(assets) - i - 1 for i in range(len(assets))])
    # English labels on purpose: the default font has no CJK glyphs, and tofu boxes would
    # make the figure unreadable. Labels are (asset_id, asset_class) from the manifest.
    ax.set_yticklabels([f'{a["asset_id"]}  {a["asset_class"]}' for a in assets], fontsize=8)
    ax.set_xlim(0, n * 1.16)
    ax.set_xlabel(f"character offset in markdown (total {n} chars, "
                  f"{m['source']['bytes_utf8']} UTF-8 bytes)", fontsize=9)
    ax.set_title(
        f"wp-9147-01 asset locator map — report 9147, {len(assets)} assets, "
        f"sha256 {m['source']['hash'][:16]}...", fontsize=10)
    ax.grid(axis="x", linestyle=":", linewidth=0.6, alpha=0.6)
    handles = [Patch(facecolor=COLORS[k], edgecolor="black", label=k) for k in ORDER]
    ax.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.95)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print("wrote", OUT, OUT.stat().st_size, "bytes")
    # coverage sanity: resolved spans must be inside the document and non-overlapping per asset
    for a in assets:
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        assert 0 <= s < e <= n, a["asset_id"]
    print("span bounds: OK for all", len(assets), "assets")


if __name__ == "__main__":
    main()