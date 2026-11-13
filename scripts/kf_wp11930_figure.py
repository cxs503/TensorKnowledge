"""Render the wp-11930-01 result figure and the evidence table from the manifest.

All plotted numbers are read from docs/kf/wp-11930-01/asset_manifest.json
(itself generated from the fetched markdown), so nothing is hand-copied.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "kf" / "wp-11930-01"
MANIFEST = ART / "asset_manifest.json"
SOURCE = ART / "source_11930.md"
FIG = ART / "fig_asset_registration_summary.png"
TABLE = ART / "evidence_table.md"


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = m["assets"]
    classes = sorted(m["counts"]["by_class"])
    resolutions = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    colors = {"resolved_in_source": "#2b8cbe", "referenced_unresolved": "#fdae6b", "declared_absent": "#756bb1"}

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.15, 1]})

    # left: stacked bar per asset class, split by resolution
    bottoms = [0] * len(classes)
    for res in resolutions:
        vals = [
            sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == res) for c in classes
        ]
        ax0.barh(classes, vals, left=bottoms, color=colors[res], label=res)
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    for i, total in enumerate(bottoms):
        ax0.text(total + 0.08, i, str(total), va="center", fontsize=9)
    ax0.set_xlabel("registered assets (count)")
    ax0.set_title("wp-11930-01: assets by class x resolution")
    ax0.legend(fontsize=8, loc="lower right")
    ax0.set_xlim(0, max(bottoms) + 1)

    # right: locator resolution quality — quote length vs source char position
    for res in resolutions:
        sel = [a for a in assets if a["resolution"] == res]
        ax1.scatter(
            [a["locator"]["start_char"] for a in sel],
            [len(a["locator"]["quote"]) for a in sel],
            s=46,
            color=colors[res],
            label=res,
            edgecolor="k",
            linewidth=0.4,
        )
    for a in assets:
        ax1.annotate(
            a["asset_id"],
            (a["locator"]["start_char"], len(a["locator"]["quote"])),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
        )
    ax1.set_xlabel("locator start_char in source markdown (chars = %d)" % m["source"]["chars"])
    ax1.set_ylabel("quote length (chars)")
    ax1.set_title("locators: all unique = %s" % m["integrity"]["all_quotes_unique"])
    ax1.legend(fontsize=8)

    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    fig.suptitle(
        "report 11930 asset registration · sha256 %s…%s · %d assets"
        % (digest[:10], digest[-6:], len(assets)),
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(FIG, dpi=150)
    print("figure:", FIG.relative_to(ROOT), FIG.stat().st_size, "bytes")

    lines = [
        "# Evidence locators (generated from asset_manifest.json)",
        "",
        "Report 11930 · package wp-11930-01 · source `tensor://reports/11930` · sha256 `%s`" % digest,
        "",
        "| asset_id | class | section | resolution | line(s) | quote (verbatim, unique) |",
        "|---|---|---|---|---|---|",
    ]
    for a in assets:
        q = a["locator"]["quote"].replace("|", "\\|")
        lines.append(
            "| %s | %s | %s | %s | %d–%d | “%s” |"
            % (
                a["asset_id"],
                a["asset_class"],
                a["in_report_section"],
                a["resolution"],
                a["locator"]["start_line"],
                a["locator"]["end_line"],
                q,
            )
        )
    lines += [
        "",
        "Source metadata: title=%s；scenario_key=%s；chars=%d；bytes_utf8=%d。"
        % (m["source"]["title"], m["source"]["scenario_key"], m["source"]["chars"], m["source"]["bytes_utf8"]),
        "",
        "Platform figure index (%d): %s"
        % (len(m["source"]["platform_figures"]), ", ".join(f["name"] for f in m["source"]["platform_figures"])),
    ]
    TABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("table:", TABLE.relative_to(ROOT))


if __name__ == "__main__":
    main()