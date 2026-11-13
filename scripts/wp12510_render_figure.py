#!/usr/bin/env python3
"""wp-12510-01 · 从 asset_manifest.json 渲染资产解析状态图（零手抄：全部读自 manifest）。"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(REPO, "docs", "kf", "wp-12510-01")


def main() -> None:
    man = json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))
    assets = man["assets"]
    labels = [f'{a["asset_id"][-2:]}\n{a["kind"]}' for a in assets]
    resolved = [1 if a["status"] == "resolved" else 0 for a in assets]
    unresolved = [1 - r for r in resolved]

    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    x = range(len(assets))
    ax.bar(x, resolved, color="#2e7d32", label="resolved")
    ax.bar(x, unresolved, bottom=resolved, color="#c62828", label="unresolved")
    for i, a in enumerate(assets):
        ax.text(i, 0.5, a["name"].split("/")[-1][:22], ha="center", va="center",
                fontsize=7, color="white" if resolved[i] else "black")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylim(0, 1.25)
    ax.set_yticks([0, 1])
    ax.set_ylabel("resolution status")
    ax.set_title(
        f"wp-12510-01 asset registration: {man['asset_counts']['total']} assets, "
        f"{man['asset_counts']['by_status']['resolved']} resolved / "
        f"{man['asset_counts']['by_status']['unresolved']} unresolved\n"
        f"source sha256={man['source']['sha256'][7:19]}… (contract match="
        f"{man['integrity']['hash_matches_contract']})"
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = os.path.join(PKG, "fig1_asset_resolution.png")
    fig.savefig(out)
    print(out)


if __name__ == "__main__":
    main()
