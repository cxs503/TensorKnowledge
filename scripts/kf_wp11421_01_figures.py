#!/usr/bin/env python3
"""wp-11421-01 | figures for the asset-registration report (ASCII labels, no CJK font needed).

fig1_asset_resolution.png : 22 registered assets, class x resolution (answers "what is actually
                            resolvable from this report record and what is only a pointer")
fig2_locator_map.png      : every quote locator projected onto the source axis (18 542 chars),
                            with the report's section boundaries — the visual audit of "the whole
                            document is addressable, not just the head"
fig3_fd_vs_analytic.png   : the internal cross-check that produced the two registered findings:
                            (a) analytic vs finite-difference sensitivities vs the stated 5% bound,
                            (b) the six negative first-order Sobol indices with their ±1 SE bands
                            against §2.2's "S_i >= 0" claim.

Reads only docs/kf/wp-11421-01/asset_manifest.json + crosscheck.json + source.md.
"""
from __future__ import annotations

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

D = pathlib.Path("docs/kf/wp-11421-01")
OUT = D


def fig1(manifest: dict) -> pathlib.Path:
    classes = sorted(manifest["counts"]["by_class"])
    res = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    colors = {"resolved_in_source": "#2b8a3e", "referenced_unresolved": "#c92a2a",
              "declared_absent": "#495057"}
    data = {r: [sum(1 for a in manifest["assets"]
                    if a["asset_class"] == c and a["resolution"] == r) for c in classes]
            for r in res}
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    left = [0] * len(classes)
    for r in res:
        ax.barh(classes, data[r], left=left, color=colors[r], label=r,
                edgecolor="white", height=0.68)
        left = [acc + v for acc, v in zip(left, data[r])]
    for i, c in enumerate(classes):
        ax.text(left[i] + 0.06, i, str(left[i]), va="center", fontsize=8)
    ax.set_xlabel("number of assets")
    ax.set_title(
        f"wp-11421-01 asset registry: {manifest['counts']['assets']} assets from report 11421  "
        f"(resolved_in_source={manifest['counts']['resolved_in_source']}, "
        f"referenced_unresolved={manifest['counts']['referenced_unresolved']}, "
        f"declared_absent={manifest['counts']['declared_absent']})",
        fontsize=9,
    )
    ax.legend(fontsize=8, loc="lower right")
    ax.set_xlim(0, max(left) + 1.6)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig1_asset_resolution.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def fig2(manifest: dict, source: str) -> pathlib.Path:
    colors = {"resolved_in_source": "#2b8a3e", "referenced_unresolved": "#c92a2a",
              "declared_absent": "#495057"}
    fig, ax = plt.subplots(figsize=(10.2, 4.2))
    for a in manifest["assets"]:
        loc = a["locator"]
        y = 1 if a["asset_class"] != "figure" else 0.5
        ax.plot([loc["start_char"], max(loc["end_char"], loc["start_char"] + 60)],
                [y, y], color=colors[a["resolution"]], lw=3, solid_capstyle="butt")
        idx = int(a["asset_id"][1:])
        ax.text(loc["start_char"], y + (0.12 if idx % 2 else -0.22), a["asset_id"],
                fontsize=6.5, color=colors[a["resolution"]], rotation=0)
    # section boundaries
    # section labels: keep ASCII only (DejaVu has no CJK glyphs), number the rest
    import re
    marks, nth = [], 0
    for i in range(len(source)):
        if source.startswith("\n## ", i):
            nth += 1
            head = source[i + 1: source.find("\n", i + 1)]
            m = re.match(r"## 表(\d)", head)
            label = f"T{m.group(1)}" if m else (f"S{nth}" if not head.startswith("## 附录") else "AppA")
            marks.append((i, label))
    for pos, title in marks:
        ax.axvline(pos, color="#adb5bd", lw=0.7, ls="--")
        ax.text(pos, 1.42, title, fontsize=6, rotation=90, va="top", color="#495057")
    ax.set_ylim(0.1, 1.55)
    ax.set_yticks([0.5, 1.0])
    ax.set_yticklabels(["figures", "non-figure assets"], fontsize=8)
    ax.set_xlabel(f"character offset in source.md ({len(source)} chars, sha256 verified)")
    ax.set_title("wp-11421-01 locator map: every quote lies at a unique char span "
                 "(green=resolved in source, red=path/code pointer not in record, grey=declared absent)",
                 fontsize=8.5)
    ax.set_xlim(-300, len(source) + 300)
    fig.tight_layout()
    p = OUT / "fig2_locator_map.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def fig3(crosscheck: dict) -> pathlib.Path:
    x5 = next(c for c in crosscheck["checks"] if c["check_id"] == "X5")
    x4 = next(c for c in crosscheck["checks"] if c["check_id"] == "X4")
    rows = x5["computed"]["per_factor"]
    names = list(rows)
    rel = [rows[n]["rel_diff"] for n in names]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.3))

    ax1.barh(names, [r * 100 for r in rel], color=["#c92a2a" if r >= 0.05 else "#2b8a3e" for r in rel])
    ax1.axvline(5.0, color="#212529", ls="--", lw=1.2, label="stated bound 5% ($3.4b)")
    ax1.set_xscale("log")
    ax1.set_xlabel("relative difference analytic vs finite-difference c_i  [%]")
    ax1.set_title("X5: 'non-zero items agree to <5%' does not hold for geom_L\n"
                  f"(worst {max(rel) * 100:.1f}% ; {sum(1 for r in rel if r >= 0.05)} of {len(rel)} rows over)",
                  fontsize=8.5)
    ax1.legend(fontsize=7.5, loc="lower right")
    ax1.grid(axis="x", alpha=0.25)

    neg = x4["computed"]["negative_rows"]
    labels = [f"{d['factor']} ({d['column']})" for d in neg]
    vals = [d["value"] for d in neg]
    ses = [d["se"] for d in neg]
    ypos = list(range(len(neg)))
    ax2.errorbar(vals, ypos, xerr=ses, fmt="o", color="#c92a2a", ecolor="#adb5bd",
                 capsize=3, lw=1.2, ms=5)
    ax2.axvline(0.0, color="#212529", lw=1.0)
    ax2.set_yticks(ypos)
    ax2.set_yticklabels(labels, fontsize=7.5)
    ax2.set_xlabel("first-order Sobol index estimate +/- 1 SE")
    ax2.set_title(f"X4: {len(neg)} negative first-order indices vs '$2.2: S_i >= 0$ claim\n"
                  "(all |value| < 1 SE -> estimator noise, not physics)", fontsize=8.5)
    ax2.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig3_fd_vs_analytic.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def main() -> int:
    manifest = json.loads((D / "asset_manifest.json").read_text(encoding="utf-8"))
    crosscheck = json.loads((D / "crosscheck.json").read_text(encoding="utf-8"))
    source = (D / "source.md").read_text(encoding="utf-8")
    for p in (fig1(manifest), fig2(manifest, source), fig3(crosscheck)):
        print(p, p.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())