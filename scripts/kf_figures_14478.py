#!/usr/bin/env python3
"""Render the three figures of the wp-14478-01 delivery report from the machine artifacts.

Inputs : docs/wp-14478-01/asset_manifest.json, docs/wp-14478-01/verification.json
Outputs: docs/wp-14478-01/fig_locator_map.png, fig_payload_status.png, fig_acceptance_matrix.png
All labels are ASCII on purpose (no CJK font is installed in this image).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wp-14478-01"


def main() -> int:
    manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    verification = json.loads((OUT / "verification.json").read_text(encoding="utf-8"))
    total = manifest["source"]["chars"]

    # ---- 1. locator map: where in the markdown each registered asset sits
    assets = manifest["assets"]
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(assets) + 1.6))
    order = {status: i for i, status in enumerate(sorted(manifest["counts"]["by_payload_status"]))}
    colors = {"in_report_record": "#1b5e20", "external_url_declared": "#0d47a1",
              "external_repo_path_declared": "#5e35b1", "declared_payload_missing": "#c62828",
              "declared_in_source_only": "#ef6c00"}
    for row, asset in enumerate(assets):
        loc = asset["locator"]
        ax.barh(row, loc["end_char"] - loc["start_char"], left=loc["start_char"], height=0.62,
                color=colors.get(asset["payload"]["status"], "#555555"))
        ax.text(loc["end_char"] + total * 0.004, row, f"{asset['asset_id']} L{loc['start_line']}",
                va="center", fontsize=7)
    ax.set_yticks(range(len(assets)))
    ax.set_yticklabels([a["asset_id"] for a in assets], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel(f"character offset in report 14478 markdown (total {total} chars)")
    ax.set_title("wp-14478-01 locator map: 20 registered assets, 1 bar = 1 char_span locator")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
    ax.legend(handles, list(colors), fontsize=6, loc="lower right", framealpha=0.9)
    ax.set_xlim(0, total * 1.12)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_locator_map.png", dpi=150)
    plt.close(fig)

    # ---- 2. payload status counts
    counts = manifest["counts"]["by_payload_status"]
    keys = list(counts)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bars = ax.bar(range(len(keys)), [counts[k] for k in keys], color=[colors.get(k, "#555555") for k in keys])
    for bar, k in zip(bars, keys):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1, str(counts[k]),
                ha="center", fontsize=9)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([k.replace("_", "\n") for k in keys], fontsize=7)
    ax.set_ylabel("assets")
    ax.set_title("wp-14478-01 payload status (20 assets, claims = 0)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_payload_status.png", dpi=150)
    plt.close(fig)

    # ---- 3. acceptance matrix
    checks = verification["checks"]
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(checks) + 1.4))
    palette = {"PASS": "#2e7d32", "FAIL": "#c62828", "NOT_RUN": "#9e9e9e"}
    for row, check in enumerate(checks):
        ax.barh(row, 1, color=palette.get(check["result"], "#555555"), height=0.7)
        ax.text(1.02, row, check["result"], va="center", fontsize=8)
    ax.set_yticks(range(len(checks)))
    ax.set_yticklabels([c["acceptance_item"] for c in checks], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.35)
    ax.set_xticks([])
    ok = sum(1 for c in checks if c["result"] == "PASS")
    ax.set_title(f"wp-14478-01 acceptance matrix: {ok}/{len(checks)} PASS "
                 f"(mode: {verification['mode'].split()[0]})")
    fig.tight_layout()
    fig.savefig(OUT / "fig_acceptance_matrix.png", dpi=150)
    plt.close(fig)

    print("wrote fig_locator_map.png, fig_payload_status.png, fig_acceptance_matrix.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())