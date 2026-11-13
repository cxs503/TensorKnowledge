#!/usr/bin/env python3
"""Figures for the wp-9761-01 result report (asset-registration audit view).

fig1_asset_coverage.png : where the 27 registered assets sit on the 8931-char source axis,
                          coloured by resolution, with section boundaries; the union of the
                          spans gives a measurable locator-coverage fraction.
fig2_resolution_checks.png : resolution mix + the verifier check matrix (all PASS/FAIL values
                          read from artifacts/, nothing typed by hand).

All labels are ASCII/English because the node has no CJK font (tofu risk); the Chinese
captions live in the report markdown, not in the raster.

Usage: python3 scripts/kf_figures_9761.py
"""
from __future__ import annotations

import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

RUN_DIR = pathlib.Path("runs/wp-9761-01")
DOC_DIR = pathlib.Path("docs/wp-9761-01")
FIG_DIR = DOC_DIR / "figures"

MD = (RUN_DIR / "report_9761.md").read_text(encoding="utf-8")
MANIFEST = json.loads(pathlib.Path("artifacts/wp-9761-01/asset_manifest.json").read_text(encoding="utf-8"))
VERIF = json.loads(pathlib.Path("artifacts/wp-9761-01/verification.json").read_text(encoding="utf-8"))

COLORS = {"resolved_in_source": "#2b7bba", "referenced_unresolved": "#d1495b",
          "declared_absent": "#8d99ae"}


def coverage_fraction(exclude=("A01",)) -> dict:
    """Union of locator spans / document length.

    A01 is the whole-document asset, so including it makes coverage trivially 1.0;
    the informative number is *targeted* coverage over the per-asset locators, and
    the complement is the stretch of the report that no specific asset pins down
    (gap surface for the downstream extraction package).
    """
    spans = sorted((a["locator"]["start_char"], a["locator"]["end_char"])
                   for a in MANIFEST["assets"] if a["asset_id"] not in exclude)
    merged, cur = [], None
    for s, e in spans:
        if cur and s <= cur[1]:
            cur[1] = max(cur[1], e)
        else:
            if cur:
                merged.append(cur)
            cur = [s, e]
    if cur:
        merged.append(cur)
    covered = sum(e - s for s, e in merged)
    gaps, prev = [], 0
    for s, e in merged:
        if s > prev:
            gaps.append([prev, s])
        prev = max(prev, e)
    if prev < len(MD):
        gaps.append([prev, len(MD)])
    comp = {"blank": 0, "heading": 0, "prose": 0}
    for s0, e0 in gaps:
        for ln in MD[s0:e0].split("\n"):
            if not ln.strip():
                comp["blank"] += 1
            elif ln.startswith("#"):
                comp["heading"] += 1
            else:
                comp["prose"] += 1
    return dict(document_chars=len(MD), covered_chars=covered,
                fraction=covered / len(MD), intervals=len(merged),
                gap_chars=len(MD) - covered, gaps=gaps,
                gap_line_composition=comp,
                gap_prose_lines=[ln for s0, e0 in gaps
                                 for ln in MD[s0:e0].split("\n")
                                 if ln.strip() and not ln.startswith("#")],
                excluded_from_coverage=list(exclude))


def fig_coverage() -> pathlib.Path:
    cov = coverage_fraction()
    n = len(MANIFEST["assets"])
    fig, ax = plt.subplots(figsize=(11, 9.0), dpi=150)
    for x0, x1 in cov["gaps"]:                     # unregistered stretch, shaded
        ax.axvspan(x0, x1, color="#f2c14e", alpha=0.22, zorder=0)
    for i, a in enumerate(MANIFEST["assets"]):
        loc = a["locator"]
        x0, x1 = loc["start_char"], max(loc["end_char"], loc["start_char"] + 12)
        ax.barh(i, x1 - x0, left=x0, height=0.62,
                color=COLORS[a["resolution"]], alpha=0.85,
                edgecolor="black", linewidth=0.4)
        ax.text(x1 + 60, i, a["asset_id"] + "  " + a["asset_class"],
                va="center", fontsize=6.4, family="monospace", color="#333333")
    # section boundaries from the markdown itself
    pos = 0
    for ln in MD.split("\n"):
        if ln.startswith("#"):
            ax.axvline(pos, color="#999999", ls=":", lw=0.7)
            ax.text(pos + 25, n - 0.2, ln.split()[1] if len(ln.split()) > 1 else "#",
                    fontsize=6.6, color="#666666", rotation=90, va="top")
        pos += len(ln) + 1
    ax.set_yticks([])
    ax.set_ylabel("registered asset (A01 .. A%02d)" % n, fontsize=9)
    ax.set_xlabel("char offset in report markdown (len = %d chars)" % len(MD), fontsize=9)
    ax.set_xlim(0, len(MD) * 1.0)
    ax.set_ylim(-0.8, n + 0.4)
    ax.set_title("wp-9761-01 asset locator coverage on report 9761 (sha256 %s...)\n"
                 "targeted coverage (A01 whole-document span excluded) = %d/%d chars "
                 "(%.1f%%), %d intervals, %d chars unregistered (shaded)"
                 % (MANIFEST["source"]["hash"][:16], cov["covered_chars"],
                    cov["document_chars"], 100 * cov["fraction"], cov["intervals"],
                    cov["gap_chars"]),
                 fontsize=9.5)
    ax.legend(handles=[Patch(color=COLORS[k], label=k) for k in COLORS],
              loc="lower right", fontsize=7)
    ax.grid(axis="x", color="#dddddd", lw=0.4)
    fig.tight_layout()
    out = FIG_DIR / "fig1_asset_coverage.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_checks() -> pathlib.Path:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150,
                                 gridspec_kw={"width_ratios": [1, 1.5]})
    by_res = MANIFEST["counts"]["by_resolution"]
    keys = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    vals = [by_res.get(k, 0) for k in keys]
    bars = a1.bar(range(len(keys)), vals, color=[COLORS[k] for k in keys],
                  edgecolor="black", linewidth=0.5)
    for b, v in zip(bars, vals):
        a1.text(b.get_x() + b.get_width() / 2, v + 0.3, str(v), ha="center", fontsize=9)
    a1.set_xticks(range(len(keys)))
    a1.set_xticklabels([k.replace("_", "\n") for k in keys], fontsize=7.5)
    a1.set_ylabel("assets", fontsize=9)
    a1.set_ylim(0, max(vals) + 2.5)
    a1.set_title("%d registered assets by resolution status" % MANIFEST["counts"]["assets"],
                 fontsize=9.5)
    a1.grid(axis="y", color="#dddddd", lw=0.4)

    checks = VERIF["checks"]
    ys = list(range(len(checks)))[::-1]
    for y, c in zip(ys, checks):
        ok = c["result"] == "pass"
        a2.scatter(0.06, y, s=140, marker="o" if ok else "X",
                   color="#2a9d8f" if ok else "#d1495b", zorder=3)
        a2.text(0.13, y, c["check"], fontsize=7.4, family="monospace", va="center")
        a2.text(1.02, y, c["result"].upper(), fontsize=7.4, family="monospace",
                va="center", color="#2a9d8f" if ok else "#d1495b")
    a2.set_xlim(0, 1.18)
    a2.set_ylim(-0.8, len(checks) - 0.2)
    a2.set_yticks([])
    a2.set_xticks([])
    for s in ("top", "right", "bottom"):
        a2.spines[s].set_visible(False)
    a2.set_title("verification of wp-9761-01: overall %s (hash re-fetched, %s checks)"
                 % (VERIF["overall"], len(checks)), fontsize=9.5)
    fig.tight_layout()
    out = FIG_DIR / "fig2_resolution_checks.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    f1, f2 = fig_coverage(), fig_checks()
    cov = coverage_fraction()
    (DOC_DIR / "coverage.json").write_text(
        json.dumps(dict(package_id="wp-9761-01", report_id="9761", **cov),
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("figs:", f1, f2)
    print("coverage:", json.dumps(cov))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())