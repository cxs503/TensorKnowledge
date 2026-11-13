#!/usr/bin/env python3
"""Figure for wp-11363-01: where the registered assets sit in the source markdown.

Left panel  : asset inventory by kind x resolution status.
Right panel : the 6902-char source field as a position axis, with every char-span
              locator drawn at its true offset and section headings marked.

No data is typed in: everything is read from docs/kf/wp-11363-01/asset_manifest.json.
Labels are ASCII on purpose (CJK fonts are not guaranteed in the build image), so
no glyph is silently dropped.

    python3 scripts/kf_wp11363_01_figure.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-11363-01"
OUT = ROOT / "docs" / "kf" / PKG
MANIFEST = OUT / "asset_manifest.json"
FIG = OUT / "figures" / ("wp11363_01_locator_map.png")

STATUS_COLOR = {
    "resolved": "#1b5e20",
    "resolved_with_bytes": "#2e7d32",
    "declared_reference_only": "#e65100",
    "referenced_unresolved": "#8d6e63",
    "unresolved": "#b71c1c",
}
KIND_ORDER = [
    "report_markdown", "embedded_figure", "source_directory_reference",
    "source_code_reference", "data_artifact_reference", "document_reference",
    "api_endpoint_reference", "symbol_reference", "capability_declaration_reference",
    "upstream_dependency_reference",
]


def main() -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    src_asset = next(a for a in man["assets"] if a["kind"] == "report_markdown")
    md = (ROOT / src_asset["local_copy"]).read_text(encoding="utf-8")
    assets = man["assets"]

    tally: dict[str, dict[str, int]] = {}
    for a in assets:
        st = a.get("resolution", {}).get("status", "n/a")
        tally.setdefault(a["kind"], {}).setdefault(st, 0)
        tally[a["kind"]][st] += 1
    kinds = [k for k in KIND_ORDER if k in tally] + [k for k in tally if k not in KIND_ORDER]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11.5, 8.4), gridspec_kw={"height_ratios": [1.0, 1.15]})

    # ---- left: inventory -------------------------------------------------
    y = range(len(kinds))
    left = [0] * len(kinds)
    statuses = [st for st in STATUS_COLOR if any(st in tally[k] for k in kinds)]
    statuses += sorted({st for k in kinds for st in tally[k] if st not in STATUS_COLOR})
    for st in statuses:
        vals = [tally[k].get(st, 0) for k in kinds]
        if not any(vals):
            continue
        ax1.barh(list(y), vals, left=left, color=STATUS_COLOR.get(st, "#455a64"),
                 edgecolor="white", label="%s (%d)" % (st, sum(vals)))
        left = [l + v for l, v in zip(left, vals)]
    for i, k in enumerate(kinds):
        ax1.text(left[i] + 0.12, i, str(sum(tally[k].values())), va="center", fontsize=8)
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(kinds, fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel("assets")
    ax1.set_title("wp-11363-01 asset inventory: %d assets by kind x resolution status"
                  % man["counts"]["assets_total"], fontsize=10, loc="left")
    ax1.legend(fontsize=7, ncol=2, loc="lower right", framealpha=0.95)
    ax1.grid(axis="x", alpha=0.25)
    ax1.set_axisbelow(True)

    # ---- right: locator map over the char axis ---------------------------
    headings = []
    off = 0
    for ln in md.splitlines():
        if ln.startswith("#"):
            headings.append((off, ln.lstrip("# ").strip()))
        off += len(ln) + 1
    spans = [a for a in assets if a["locator"].get("method") == "char_span"]
    for i, a in enumerate(spans):
        loc = a["locator"]
        st = a.get("resolution", {}).get("status", "n/a")
        ax2.plot([loc["start_char"], loc["end_char"]], [i, i],
                 color=STATUS_COLOR.get(st, "#455a64"), lw=4, solid_capstyle="butt")
        ax2.text(loc["end_char"] + 60, i, "%s  L%d" % (a["asset_id"].split(":", 1)[1], loc["line"]),
                 fontsize=6.5, va="center", color="#37474f")
    for hi, (x, _txt) in enumerate(headings, start=1):
        ax2.axvline(x, color="#90a4ae", lw=0.8, ls=":")
        ax2.text(x + 20, len(spans) - 0.2, "H%d" % hi, fontsize=6.5, rotation=90,
                 va="top", color="#546e7a")
    ax2.set_xlim(0, len(md))
    ax2.set_ylim(-0.8, len(spans) + 0.6)
    ax2.invert_yaxis()
    ax2.set_xlabel("character offset in the source markdown field (chars=%d, sha256 %s...)"
                   % (man["source"]["chars"], man["source"]["source_hash"][7:19]))
    ax2.set_title("char-span locators: %d quotes re-verified by substring + offset back-read "
                  "(all_verified=%s)" % (man["locators"]["count"], man["locators"]["all_verified"]),
                  fontsize=10, loc="left")
    ax2.grid(axis="x", alpha=0.2)
    ax2.set_yticks([])

    fig.text(0.01, 0.005,
             "Source: GET /api/v1/tensor/reports/11363 -> markdown, sha256 recomputed = contract hash. "
             "Dotted verticals = heading H1..H%d (H1..H6 = sections 1-6, H7 = audit chain). Red = reference not resolvable inside this worktree "
             "(artefacts live in ship-performance-platform); green = payload/bytes hashed.",
             fontsize=6.5, color="#455a64")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=170)
    print("figure ->", FIG.relative_to(ROOT), FIG.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())