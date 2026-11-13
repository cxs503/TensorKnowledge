#!/usr/bin/env python3
"""wp-8288-01 figures: source locator map + resolution inventory.

Both figures are rendered from docs/kf/wp-8288-01/asset_manifest.json only, so the
pixels cannot disagree with the registered manifest (programmatic, zero hand-copy).

Output: docs/kf/wp-8288-01/figures/*.png
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / "wp-8288-01"
FIGS = OUT / "figures"

COLORS = {
    "resolved_in_source": "#2f7d32",
    "referenced_unresolved": "#c77700",
    "declared_absent": "#9e9e9e",
}
NICE = {
    "resolved_in_source": "resolved in source",
    "referenced_unresolved": "referenced, unresolved",
    "declared_absent": "declared absent (by the report)",
}


def locator_map(manifest: dict, md_chars: int) -> Path:
    assets = manifest["assets"]
    order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    fig, ax = plt.subplots(figsize=(11, 6.2))
    rows = {r: i for i, r in enumerate(order)}
    counts = {r: 0 for r in order}
    for a in sorted(assets, key=lambda x: (x["resolution"], x["locator"]["start_char"])):
        r = a["resolution"]
        counts[r] += 1
        y = rows[r] + (counts[r] - 1) * 0.055
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        ax.barh(y, max(e - s, md_chars * 0.002), left=s, height=0.045,
                color=COLORS[r], edgecolor="black", linewidth=0.3)
        ax.text(min(e + md_chars * 0.005, md_chars * 0.985), y, a["asset_id"],
                va="center", ha="left", fontsize=7.5)
    ax.set_yticks(list(rows.values()))
    ax.set_yticklabels([NICE[r] for r in order])
    ax.set_xlabel("character offset in report 8288 markdown (0 … %d chars)" % md_chars)
    ax.set_title("Source locator map — 40 registered assets of wp-8288-01\n"
                 "(each bar = one verbatim char-span locator; label = asset_id)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(handles=[Patch(color=COLORS[r], label=NICE[r]) for r in order],
              loc="lower right", fontsize=8)
    ax.set_xlim(0, md_chars * 1.02)
    fig.tight_layout()
    p = FIGS / "wp8288_01_locator_map.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def inventory(manifest: dict) -> Path:
    by_class = manifest["counts"]["by_class"]
    by_res = manifest["counts"]["by_resolution"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
    classes = sorted(by_class, key=lambda k: -by_class[k])
    a1.barh(classes[::-1], [by_class[c] for c in classes[::-1]], color="#37474f")
    for i, c in enumerate(classes[::-1]):
        a1.text(by_class[c] + 0.15, i, str(by_class[c]), va="center", fontsize=8)
    a1.set_xlabel("assets")
    a1.set_title("by asset_class (n=%d)" % manifest["counts"]["assets"])
    a1.grid(axis="x", alpha=0.3)

    order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    a2.bar([NICE[r] for r in order], [by_res.get(r, 0) for r in order],
           color=[COLORS[r] for r in order], edgecolor="black", linewidth=0.4)
    for i, r in enumerate(order):
        a2.text(i, by_res.get(r, 0) + 0.3, str(by_res.get(r, 0)), ha="center", fontsize=9)
    a2.set_ylabel("assets")
    a2.set_title("by resolution state")
    a2.tick_params(axis="x", labelsize=8)
    a2.grid(axis="y", alpha=0.3)
    fig.suptitle("wp-8288-01 asset inventory (report 8288 · sha256 %s…)"
                 % manifest["source"]["hash"][:16], fontsize=10)
    fig.tight_layout()
    p = FIGS / "wp8288_01_inventory.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    md_chars = manifest["source"]["chars"]
    p1 = locator_map(manifest, md_chars)
    p2 = inventory(manifest)
    manifest_out = {
        "package_id": manifest["package_id"],
        "source_hash": "sha256:" + manifest["source"]["hash"],
        "figures": [
            {"name": "wp8288_01_locator_map", "file": str(p1.relative_to(REPO)),
             "caption": "Source locator map: 40 verbatim char-span locators of report 8288, "
                        "coloured by resolution state.",
             "png_base64": b64(p1)},
            {"name": "wp8288_01_inventory", "file": str(p2.relative_to(REPO)),
             "caption": "Asset inventory by class and by resolution state (counts copied from "
                        "asset_manifest.json counts block).",
             "png_base64": b64(p2)},
        ],
    }
    (OUT / "figures_manifest.json").write_text(
        json.dumps(manifest_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s, %s, figures_manifest.json" % (p1.relative_to(REPO), p2.relative_to(REPO)))


if __name__ == "__main__":
    main()