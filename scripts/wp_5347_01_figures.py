#!/usr/bin/env python3
"""Figures for wp-5347-01 — inventory and gate evidence, drawn from artefacts.

Two figures, both pure projections of the emitted JSON (no hand-typed numbers):

  1. ``asset_inventory.png``   assets per kind, stacked by reachability; the
     ``resolved`` share is drawn as zero on purpose — process 01 ships no bytes
     for the referenced TensorDEM artefacts.
  2. ``gate_evidence.png``     local acceptance lines A1..A10 and the platform
     gate results g1..g7, coloured by status (passed / vacuous / failed).

Usage: python3 scripts/wp_5347_01_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "artifacts" / "wp-5347-01"
if not PKG.is_dir():  # committed snapshot: artifacts/** is git-ignored
    PKG = REPO / "docs" / "production" / "wp-5347-01"
FIG = PKG / "figures"

COLORS = {"passed": "#2e7d32", "vacuous": "#f9a825", "failed": "#c62828",
          "not_run": "#616161", "metadata_only": "#6a1b9a", "external_repo_artifact": "#1565c0",
          "environment_layout": "#00838f", "ephemeral_sandbox": "#8d6e63",
          "environment_dependency": "#5d4037"}


def fig_inventory(manifest: dict) -> Path:
    by_kind = manifest["counts"]["by_kind"]
    kinds = sorted(by_kind)
    reach_by_kind: dict[str, dict[str, int]] = {k: {} for k in kinds}
    for a in manifest["assets"]:
        reach_by_kind[a["kind"]][a["reachability"]] = \
            reach_by_kind[a["kind"]].get(a["reachability"], 0) + 1

    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=140)
    left = [0] * len(kinds)
    for reach in sorted({a["reachability"] for a in manifest["assets"]}):
        vals = [reach_by_kind[k].get(reach, 0) for k in kinds]
        if not any(vals):
            continue
        ax.barh(kinds, vals, left=left, label=reach, color=COLORS.get(reach, "#90a4ae"))
        left = [l + v for l, v in zip(left, vals)]
    for i, k in enumerate(kinds):
        ax.text(left[i] + 0.08, i, str(by_kind[k]), va="center", fontsize=8)
    ax.set_xlabel("assets (report 5347, process 01)")
    ax.set_title(f"asset inventory: {manifest['counts']['assets']} assets, "
                 f"{manifest['counts']['resolved']} resolved", fontsize=10)
    ax.legend(fontsize=7, loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=0.3)
    out = FIG / "asset_inventory.png"
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_gates(checks: dict, platform: dict) -> Path:
    rows = [(c["check"], c["status"]) for c in checks["checks"]]
    prows = [(g["gate"], "passed" if g["ok"] else "failed") for g in platform.get("evidence", [])]
    prows += [(g["gate"], "passed" if g["ok"] else "failed") for g in platform.get("structure", [])]
    rows = prows + [("", "not_run")] + rows
    fig, ax = plt.subplots(figsize=(7.6, 5.2), dpi=140)
    ys = list(range(len(rows)))[::-1]
    for y, (name, status) in zip(ys, rows):
        ax.barh(y, 1, color=COLORS.get(status, "#bdbdbd"))
        ax.text(0.02, y, name or "— local acceptance (A*) —", va="center", fontsize=7,
                color="white")
        ax.text(1.02, y, status, va="center", fontsize=7)
    ax.set_xlim(0, 1.35)
    ax.set_yticks([])
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("platform gates (top) and local acceptance lines (bottom)\n"
                 f"platform ok={platform.get('ok')}; local failed={checks['counts']['failed']}, "
                 f"vacuous={checks['counts']['vacuous']}", fontsize=9)
    out = FIG / "gate_evidence.png"
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    checks = json.loads((PKG / "checks.json").read_text(encoding="utf-8"))
    platform = json.loads((PKG / "platform_gate.json").read_text(encoding="utf-8"))
    paths = [fig_inventory(manifest), fig_gates(checks, platform)]
    print(json.dumps([{"path": str(p.relative_to(REPO)), "bytes": p.stat().st_size}
                      for p in paths], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())