#!/usr/bin/env python3
"""Figures for the wp-3076-01 progress report — generated from the artefacts, not typed by hand.

fig_locator_map.png       every registered asset's char span inside the 3712-char markdown
fig_payload_status.png    how each asset's payload resolved (present / external / 404 / out of scope)
fig_acceptance_matrix.png acceptance items of the contract vs the machine verification result

All labels are ASCII so the PNGs render without a CJK font; the Chinese content stays in the report.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "wp-3076-01"

STATUS_COLORS = {
    "in_report_record": "#2e7d32",
    "external_not_in_record": "#ef6c00",
    "cross_report_out_of_scope": "#6a1b9a",
    "declared_in_source_only": "#0277bd",
    "declared_payload_missing": "#c62828",
}


def fig_locator_map(manifest: dict, source: str, path: Path) -> None:
    assets = manifest["assets"]
    n = len(assets)
    fig, ax = plt.subplots(figsize=(11, 0.42 * n + 1.6))
    for i, asset in enumerate(assets):
        loc = asset["locator"]
        color = STATUS_COLORS[asset["payload"]["status"]]
        ax.add_patch(
            Rectangle((loc["start_char"], i - 0.32), max(loc["end_char"] - loc["start_char"], 6), 0.64,
                      color=color, alpha=0.85)
        )
        ax.text(loc["end_char"] + 20, i, f"{asset['asset_id']} L{loc['start_line']}", va="center", fontsize=7)
    headings = [i for i, line in enumerate(source.splitlines(), 1) if line.startswith("## ")]
    offset = 0
    for line_no in headings:
        idx = source.find(source.splitlines()[line_no - 1])
        offset = idx
        ax.axvline(idx, color="#555555", lw=0.8, ls=":")
        ax.text(idx + 6, n - 0.2, f"\u00a7{headings.index(line_no) + 1}", rotation=90, fontsize=7, color="#555555")
    ax.set_xlim(0, len(source) * 1.06)
    ax.set_ylim(-0.8, n + 0.4)
    ax.set_yticks(range(n))
    ax.set_yticklabels([a["asset_id"] for a in assets], fontsize=7)
    ax.set_xlabel(f"char offset in report 3076 markdown (len={len(source)})")
    ax.set_title("wp-3076-01: 19 asset locators resolved in the pinned source (color = payload status)", fontsize=10)
    handles = [Rectangle((0, 0), 1, 1, color=c) for c in STATUS_COLORS.values()]
    ax.legend(handles, list(STATUS_COLORS), fontsize=6, loc="lower right", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_payload_status(manifest: dict, path: Path) -> None:
    counts = manifest["counts"]["by_payload_status"]
    order = [k for k in STATUS_COLORS if k in counts] + [k for k in counts if k not in STATUS_COLORS]
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    bars = ax.bar(range(len(order)), [counts[k] for k in order],
                  color=[STATUS_COLORS.get(k, "#777777") for k in order])
    for bar, key in zip(bars, order):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1, str(counts[key]),
                ha="center", fontsize=10)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([k.replace("_", "\n", 1) for k in order], fontsize=7)
    ax.set_ylabel("assets")
    ax.set_title("Payload resolution of the 19 registered assets (0 upgraded to 'verified')", fontsize=10)
    ax.set_ylim(0, max(counts.values()) + 1.2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_acceptance(verification: dict, path: Path) -> None:
    checks = verification["checks"]
    n = len(checks)
    fig, ax = plt.subplots(figsize=(9.5, 0.48 * n + 1.4))
    for i, check in enumerate(checks):
        color = {"PASS": "#2e7d32", "FAIL": "#c62828", "NOT_RUN": "#9e9e9e"}[check["result"]]
        ax.add_patch(Rectangle((0, n - i - 0.45), 1.0, 0.9, color=color, alpha=0.85))
        ax.text(1.03, n - i - 0.01, f"{check['result']}", va="center", fontsize=8, color=color, weight="bold")
        ax.text(-0.03, n - i - 0.01, check["acceptance_item"], va="center", ha="right", fontsize=8)
    ax.set_xlim(0, 1.5)
    ax.set_ylim(0, n)
    ax.axis("off")
    ax.set_title(f"wp-3076-01 acceptance matrix ({verification['mode']})\nall_pass={verification['acceptance_all_pass']}",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> int:
    manifest = json.loads((DOCS / "asset_manifest.json").read_text(encoding="utf-8"))
    verification = json.loads((DOCS / "verification.json").read_text(encoding="utf-8"))
    source = (DOCS / "source.md").read_text(encoding="utf-8")
    fig_locator_map(manifest, source, DOCS / "fig_locator_map.png")
    fig_payload_status(manifest, DOCS / "fig_payload_status.png")
    fig_acceptance(verification, DOCS / "fig_acceptance_matrix.png")
    for name in ("fig_locator_map.png", "fig_payload_status.png", "fig_acceptance_matrix.png"):
        print(name, (DOCS / name).stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())