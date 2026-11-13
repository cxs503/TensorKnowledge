#!/usr/bin/env python3
"""Figures for the wp-14214-01 report: everything is read from the emitted
asset_manifest.json (no hand-typed numbers) and written as PNG + sha256 manifest.

    python3 scripts/kf_wp14214_01_figures.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-14214-01"
FIGDIR = ROOT / "docs" / "kf" / "figures" / "wp-14214-01"


def main() -> int:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    man = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    obs = {o["obs_id"]: o for o in man["integrity_observations"]}

    # ---------------- fig 1: asset classes split by resolution ----------------
    classes = sorted(man["counts"]["by_class"])
    res_names = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    counts = {r: [sum(1 for a in man["assets"]
                      if a["asset_class"] == c and a["resolution"] == r) for c in classes]
              for r in res_names}
    fig, ax = plt.subplots(figsize=(9, 4.8))
    left = [0] * len(classes)
    colors = {"resolved_in_source": "#2f6f4f", "referenced_unresolved": "#c8862a",
              "declared_absent": "#8c8c8c"}
    for r in res_names:
        ax.barh(classes, counts[r], left=left, color=colors[r], label=r)
        left = [a + b for a, b in zip(left, counts[r])]
    for i, c in enumerate(classes):
        ax.text(left[i] + 0.05, i, str(left[i]), va="center", fontsize=8)
    ax.set_xlabel("assets")
    ax.set_title("wp-14214-01 asset registration: %d assets by class and resolution"
                 % man["counts"]["assets"])
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    f1 = FIGDIR / "fig1_asset_landscape.png"
    fig.savefig(f1, dpi=150)
    plt.close(fig)

    # ---------------- fig 2: integrity observations (programmatic) -------------
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.0))
    c1 = obs["O1"]["computed"]
    ax = axes[0]
    ax.bar(["PASS", "FAIL", "WITHHELD"], [c1["PASS"], c1["FAIL"], c1["WITHHELD"]],
           color=["#2f6f4f", "#a33", "#c8862a"])
    ax.axhline(c1["window_reports"], color="k", ls="--",
               label="window reports = %d" % c1["window_reports"])
    ax.set_title("O1: verdict tiers sum to %d\n(difference %d unaccounted)"
                 % (c1["sum"], c1["difference"]), fontsize=10)
    ax.legend(fontsize=8)
    ax.set_ylabel("reports")

    c2 = obs["O2"]["computed"]
    ax = axes[1]
    ax.bar(["body ③", "record title"], [c2["body_blocked"], c2["record_title_blocked"]],
           color=["#a33", "#444"])
    for i, v in enumerate([c2["body_blocked"], c2["record_title_blocked"]]):
        ax.text(i, v + 0.2, str(v), ha="center", fontsize=10)
    ax.set_ylim(0, max(c2["body_blocked"], c2["record_title_blocked"]) + 3)
    ax.set_title("O2: blocked cases, body vs record title\n(difference %d, unresolved)"
                 % c2["difference"], fontsize=10)
    ax.set_ylabel("cases")

    c3 = obs["O3"]["computed"]
    ax = axes[2]
    ax.bar(["table rows", "distinct task_key", "rows with mission"],
           [c3["table_rows"], c3["distinct_task_keys"], c3["rows_with_numeric_mission"]],
           color=["#3a6fa8", "#2f6f4f", "#7a4fa3"])
    for i, v in enumerate([c3["table_rows"], c3["distinct_task_keys"],
                           c3["rows_with_numeric_mission"]]):
        ax.text(i, v + 0.3, str(v), ha="center", fontsize=9)
    ax.set_title("O3: dispatch receipt, mission %s-%s\n(contiguous=%s, stated units=%s)"
                 % (c3["mission_range"][0], c3["mission_range"][1],
                    c3["missions_contiguous"], c3["title_stated_units"]), fontsize=9)
    ax.set_xticks([0, 1, 2], ["rows", "task_key", "with mission"], fontsize=8)
    ax.set_ylabel("count")

    fig.suptitle("wp-14214-01: arithmetic / cross-field observations (registered, not verified)",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    f2 = FIGDIR / "fig2_integrity_observations.png"
    fig.savefig(f2, dpi=150)
    plt.close(fig)

    out = {}
    for f in (f1, f2):
        b = f.read_bytes()
        out[f.name] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
    (FIGDIR / "figures.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"figures": out}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
