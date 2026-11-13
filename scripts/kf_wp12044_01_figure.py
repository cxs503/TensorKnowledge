#!/usr/bin/env python3
"""Figure for wp-12044-01: where the 4 registered assets sit inside the 57-char source.

The figure is generated from docs/kf/wp-12044-01/asset_manifest.json (no hand-typed
numbers): each asset is drawn as a span over the source character axis, coloured by its
resolution status. ASCII labels only, so the render is font-independent.

Usage: python3 scripts/kf_wp12044_01_figure.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-12044-01"
PNG = PKG / "fig1_asset_spans.png"

COLOR = {
    "resolved_in_source": "#2b7a2b",
    "referenced_unresolved": "#c05000",
    "declared_absent": "#7a7a7a",
}


def main() -> int:
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    md = (PKG / "source.md").read_text(encoding="utf-8")
    n = len(md)
    assets = manifest["assets"]

    fig, (ax0, ax1) = plt.subplots(
        2, 1, figsize=(10.5, 4.6), gridspec_kw={"height_ratios": [1, 2.4]}
    )

    # --- top: the source text itself, character axis -------------------------
    ax0.set_xlim(0, n)
    ax0.set_ylim(0, 1)
    ax0.set_yticks([])
    ax0.axvspan(0, n, color="#f2f2f2")
    # No CJK font in this environment: ASCII is drawn literally, non-ASCII (CJK)
    # characters are drawn as a filled marker so the render never contains tofu boxes.
    n_cjk = 0
    for i, ch in enumerate(md):
        if ch == "\n":
            continue
        if ord(ch) < 128:
            ax0.text(i + 0.5, 0.5, ch, fontsize=7, ha="center", va="center", color="#222")
        else:
            n_cjk += 1
            ax0.text(i + 0.5, 0.5, "\\u25aa", fontsize=7, ha="center", va="center",
                     color="#c05000")
    ax0.set_xlabel(f"source markdown character offset (0..{n}, sha256 {manifest['source']['hash'][:12]}...)")
    ax0.set_title(
        "report 12044 source text: ASCII glyphs literal, %d CJK chars as filled markers "
        "(no CJK font in env)" % n_cjk, fontsize=9)

    # --- bottom: asset spans -------------------------------------------------
    labels = []
    for k, a in enumerate(reversed(assets)):
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        ax1.barh(k, max(e - s, 0.8), left=s, height=0.55,
                 color=COLOR.get(a["resolution"], "#333"), alpha=0.85)
        if s == 0 and e >= n:  # whole-document locator: draw as a frame
            ax1.barh(k, n, left=0, height=0.55, color="none",
                     edgecolor=COLOR.get(a["resolution"], "#333"), linewidth=1.6, hatch="//")
        labels.append(f"{a['asset_id']} {a['asset_class']} [{a['resolution']}]")
    ax1.set_yticks(range(len(assets)))
    ax1.set_yticklabels(labels, fontsize=8)
    ax1.set_xlim(0, n)
    ax1.set_xlabel("character offset")
    ax1.grid(axis="x", linestyle=":", alpha=0.5)
    ax1.set_title("asset locators: verbatim span + resolution status", fontsize=9)
    ax1.legend(
        handles=[Patch(color=c, label=k) for k, c in COLOR.items() if
                 any(a["resolution"] == k for a in assets)],
        fontsize=7, loc="lower right", framealpha=0.9,
    )
    fig.tight_layout()
    fig.savefig(PNG, dpi=150)
    plt.close(fig)

    h = hashlib.sha256(PNG.read_bytes()).hexdigest()
    meta = {
        "figure": "fig1_asset_spans.png",
        "bytes": PNG.stat().st_size,
        "sha256": h,
        "generator": "scripts/kf_wp12044_01_figure.py",
        "data_source": "docs/kf/wp-12044-01/asset_manifest.json + source.md",
        "caption": (
            "report 12044: source text on a character axis (top) and the 4 registered asset "
            "locator spans coloured by resolution status (bottom); A01 spans the whole document, "
            "A04 stays unresolved (no figure path/URL/digest in the record)."
        ),
    }
    (PKG / "figures.json").write_text(json.dumps([meta], ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())