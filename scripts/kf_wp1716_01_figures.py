#!/usr/bin/env python3
"""Figure for KF wp-1716-01: locator map of the registered assets on the
report-1716 markdown axis, plus the status breakdown.

Deterministic: reads docs/kf/wp-1716-01/asset_manifest.json, writes
docs/kf/wp-1716-01/figures/asset_locator_map.png. No wall-clock, no RNG.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "kf" / "wp-1716-01"
MANIFEST = OUT / "asset_manifest.json"
FIGDIR = OUT / "figures"

COLOR = {"registered": "#1b7f3b", "declared_not_fetched": "#c47f00"}


def main() -> int:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md_len = m["source"]["size"]["chars"]
    assets = m["assets"]

    fig, (ax, bx) = plt.subplots(
        1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [3.3, 1.0]}
    )

    ys = list(range(len(assets)))[::-1]
    for y, a in zip(ys, assets):
        loc = a["locator"]
        st = a["status"]
        allpos = [o["char_start"] for o in a.get("occurrences", [])] or [loc["char_start"]]
        ax.scatter(allpos, [y] * len(allpos), s=26,
                   color=COLOR.get(st, "#555"), zorder=3)
        ax.plot([allpos[0], allpos[0]], [y - 0.35, y + 0.35],
                color=COLOR.get(st, "#555"), lw=1.2, zorder=2)
        label = a["asset_id"].replace(f"ast-{m['report_id']}-", "")
        if len(label) > 46:
            label = label[:44] + "…"
        ax.text(md_len * 1.015, y, f"{label}  [{st}]", va="center", fontsize=7.4,
                color=COLOR.get(st, "#555"))

    ax.axvspan(0, md_len, color="#f2f4f7", zorder=0)
    ax.set_xlim(0, md_len * 1.55)
    ax.set_ylim(-0.8, len(assets) - 0.2)
    ax.set_yticks([])
    ax.set_xlabel(f"character offset in tensor_reports.markdown (id={m['report_id']}, "
                  f"{md_len} chars)")
    ax.set_title("A. Locator map — every asset pinned to a verbatim char range "
                 "(dots = all occurrences)", fontsize=9.5, loc="left")
    ax.grid(axis="x", ls=":", lw=0.6, color="#999")

    kinds: dict[str, dict[str, int]] = {}
    for a in assets:
        kinds.setdefault(a["kind"], {}).setdefault(a["status"], 0)
        kinds[a["kind"]][a["status"]] += 1
    names = list(kinds)
    bottom = [0] * len(names)
    for st in ("registered", "declared_not_fetched"):
        vals = [kinds[n].get(st, 0) for n in names]
        if not any(vals):
            continue
        bx.bar(range(len(names)), vals, bottom=bottom,
               color=COLOR[st], label=st)
        bottom = [b + v for b, v in zip(bottom, vals)]
    bx.set_xticks(range(len(names)))
    bx.set_xticklabels([n.replace("_", "\n") for n in names], fontsize=7.5)
    bx.set_ylabel("assets")
    bx.set_title("B. Assets by kind / status", fontsize=9.5, loc="left")
    bx.legend(handles=[Patch(color=COLOR[k], label=k) for k in COLOR], fontsize=7.5)
    bx.grid(axis="y", ls=":", lw=0.6, color="#999")

    fig.suptitle(
        f"KF {m['package_id']} — asset registration for report {m['report_id']} "
        f"({len(assets)} assets, claims={len(m['claims'])}, nothing verified)",
        fontsize=10.5,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    FIGDIR.mkdir(parents=True, exist_ok=True)
    out = FIGDIR / "asset_locator_map.png"
    fig.savefig(out, dpi=160)
    print("wrote", out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())