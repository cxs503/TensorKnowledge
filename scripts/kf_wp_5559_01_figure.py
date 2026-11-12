#!/usr/bin/env python3
"""Figure for KF work package wp-5559-01: asset-registration overview of report 5559.

Every number drawn here is read out of the committed asset_manifest.json at runtime
(programmatic injection, zero hand transcription).

Output: artifacts/kf/wp-5559-01/asset_registration_overview.png
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "knowledge" / "kf" / "wp-5559-01"
MANIFEST = PKG_DIR / "asset_manifest.json"
OUT = ROOT / "artifacts" / "kf" / "wp-5559-01" / "asset_registration_overview.png"
# artifacts/ is dropped by the mission-push gate, so the figure that has to survive in the
# repository also gets a copy under knowledge/
OUT_COMMITTED = PKG_DIR / "figures" / "asset_registration_overview.png"

STATUS_COLORS = {
    "resolved": "#1b7f3a",
    "metadata_only": "#2f6fb5",
    "declared_only": "#c98a08",
    "unresolved": "#b3312c",
}


def main() -> int:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = m["assets"]
    counts = m["counts"]

    kinds = sorted({a["kind"] for a in assets})
    stacked = {
        s: [sum(1 for a in assets if a["kind"] == k and a["resolution"]["status"] == s)
            for k in kinds]
        for s in STATUS_COLORS
    }

    fig, (ax0, ax1, ax2) = plt.subplots(
        1, 3, figsize=(17.5, 7.2), gridspec_kw={"width_ratios": [1.5, 1.0, 1.15]}
    )

    # --- panel A: registered assets by kind, stacked by resolution status
    left = [0] * len(kinds)
    for status, vals in stacked.items():
        ax0.barh(kinds, vals, left=left, color=STATUS_COLORS[status], label=status,
                 edgecolor="white", linewidth=0.6)
        left = [a + b for a, b in zip(left, vals)]
    for i, total in enumerate(left):
        ax0.text(total + 0.12, i, str(total), va="center", fontsize=9)
    ax0.set_xlabel("number of registered assets")
    ax0.set_title(
        f"A. {counts['assets_total']} assets of report {m['report_id']}\nby kind and resolution status",
        fontsize=11,
    )
    ax0.legend(fontsize=8.5, loc="lower right", frameon=False)
    ax0.invert_yaxis()
    ax0.grid(axis="x", alpha=0.25)
    ax0.set_axisbelow(True)

    # --- panel B: locator resolvability (the acceptance gate that can actually fail)
    tot = counts["locators"]
    res = counts["locators_resolved"]
    ax1.bar(["resolved", "unresolved"], [res, tot - res],
            color=[STATUS_COLORS["resolved"], STATUS_COLORS["unresolved"]])
    ax1.set_ylim(0, max(tot, 1) * 1.25)
    for x, v in zip([0, 1], [res, tot - res]):
        ax1.text(x, v + tot * 0.03, str(v), ha="center", fontsize=11)
    ax1.set_ylabel("locators")
    ax1.set_title(
        f"B. source_locator_resolvable\n{res}/{tot} locators re-resolved against the source",
        fontsize=11,
    )
    ax1.grid(axis="y", alpha=0.25)
    ax1.set_axisbelow(True)

    # --- panel C: declared-vs-located figure sets (the one honest mismatch)
    checks = {c["check"]: c for c in m["ref_consistency_checks"]}
    fs = checks["body_vs_record_figure_sets"]
    names = sorted(set(fs["body_figures"]) | set(fs["record_figures"]),
                   key=lambda n: n[:4])
    in_body = [1 if n in fs["body_figures"] else 0 for n in names]
    in_rec = [1 if n in fs["record_figures"] else 0 for n in names]
    ys = range(len(names))
    ax2.barh([y + 0.19 for y in ys], in_body, height=0.36, color="#2f6fb5",
             label="linked in body (§4)")
    ax2.barh([y - 0.19 for y in ys], in_rec, height=0.36, color="#c98a08",
             label="declared in record")
    for y, n in enumerate(names):
        if n in fs["in_body_not_in_record"]:
            ax2.text(1.04, y, "body only — record defect", va="center", fontsize=9,
                     color=STATUS_COLORS["unresolved"])
    ax2.set_yticks(list(ys))
    ax2.set_yticklabels(names, fontsize=9)
    ax2.set_xlim(0, 1.9)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["absent", "present"])
    ax2.invert_yaxis()
    ax2.set_title(
        "C. figure sets: body vs record\n"
        f"{len(fs['body_figures'])} linked, {len(fs['record_figures'])} declared",
        fontsize=11,
    )
    ax2.legend(fontsize=8.5, loc="lower right", frameon=False)
    ax2.grid(axis="x", alpha=0.25)
    ax2.set_axisbelow(True)

    fig.suptitle(
        f"KF wp-5559-01 · asset registration · report {m['report_id']} · "
        f"source sha256 {m['source']['source_hash'][7:23]}… · "
        f"chars {m['source']['chars']}",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    OUT_COMMITTED.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_COMMITTED, dpi=150)
    print(OUT)
    print(OUT_COMMITTED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())