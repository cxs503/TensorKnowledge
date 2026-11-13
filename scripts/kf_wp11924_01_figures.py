"""Figures for work package wp-11924-01 — every number is read from the artifacts, nothing is typed in.

  fig1 fig_asset_inventory.png   asset_class x resolution inventory (42 assets, 22 classes)
  fig2 fig_locator_coverage.png  locator map: char offsets of every asset on the 13138-char markdown
  fig3 fig_verification.png      acceptance self-check board

Labels are English on purpose: no CJK font is installed in this worktree image, so Chinese labels would
render as tofu boxes. The Chinese wording lives in the report body and in the manifest labels.

Usage: python3 scripts/kf_wp11924_01_figures.py
"""
from __future__ import annotations

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ART = pathlib.Path("artifacts/wp-11924-01")
DOCS = pathlib.Path("docs/wp-11924-01")
M = json.loads((ART / "asset_manifest.json").read_text())
V = json.loads((ART / "verification.json").read_text())

COL = {"resolved_in_source": "#2c7fb8", "referenced_unresolved": "#e6843a", "declared_absent": "#9e9e9e"}


def fig_inventory() -> pathlib.Path:
    classes, agg = [], {}
    for a in M["assets"]:
        agg.setdefault(a["asset_class"], {})
        agg[a["asset_class"]][a["resolution"]] = agg[a["asset_class"]].get(a["resolution"], 0) + 1
    classes = sorted(agg, key=lambda c: (sum(agg[c].values()), c))
    fig, ax = plt.subplots(figsize=(9, 0.30 * len(classes) + 1.6))
    left = [0] * len(classes)
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        vals = [agg[c].get(res, 0) for c in classes]
        if not any(vals):
            continue
        ax.barh(classes, vals, left=left, color=COL[res], height=0.72,
                label="%s (%d)" % (res, M["counts"].get(res, 0)))
        left = [l + v for l, v in zip(left, vals)]
    ax.set_xlabel("assets")
    ax.set_title("wp-11924-01 · asset inventory — %d assets in %d classes (report 11924)"
                 % (M["counts"]["assets"], len(classes)), fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    out = ART / "fig_asset_inventory.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_coverage() -> pathlib.Path:
    assets = [a for a in M["assets"] if a["locator"]["method"] == "char_span"]
    n = len(M["assets"])
    fig, ax = plt.subplots(figsize=(11, 0.20 * n + 1.8))
    for row, a in enumerate(M["assets"]):
        loc = a["locator"]
        if loc["method"] == "document":
            ax.barh(row, loc["end_char"], left=0, height=0.62, color="#c9d9ea", alpha=0.55)
            ax.text(loc["end_char"] * 0.5, row, "document (full markdown)", fontsize=6,
                    ha="center", va="center", color="#31536e")
        else:
            ax.barh(row, loc["end_char"] - loc["start_char"], left=loc["start_char"], height=0.62,
                    color=COL[a["resolution"]])
    ax.set_yticks(range(n))
    ax.set_yticklabels(["%s %s" % (a["asset_id"], a["asset_class"][:22]) for a in M["assets"]], fontsize=6)
    ax.invert_yaxis()
    ax.set_xlim(0, M["source"]["chars"])
    ax.set_xlabel("character offset in report 11924 markdown (len = %d chars, sha256 = %s…)"
                  % (M["source"]["chars"], M["source"]["hash"][:12]))
    ax.set_title("wp-11924-01 · locator map — %d/%d assets carry a unique char_span quote; "
                 "coverage %.2f%% of the source"
                 % (len(assets), n, 100 * M["counts"]["coverage_fraction"]), fontsize=10)
    ax.legend(handles=[Patch(color=COL[k], label=k) for k in COL], fontsize=7, loc="lower right")
    ax.grid(axis="x", ls=":", lw=0.5, alpha=0.6)
    fig.tight_layout()
    out = ART / "fig_locator_coverage.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_verification() -> pathlib.Path:
    checks = V["checks"]
    fig, ax = plt.subplots(figsize=(10, 0.32 * len(checks) + 1.4))
    colors = {"pass": "#2c7fb8", "fail": "#d7301f", "unknown": "#9e9e9e"}
    ys = range(len(checks))
    ax.barh(list(ys), [1] * len(checks), color=[colors[c["result"]] for c in checks], height=0.7)
    for y, c in zip(ys, checks):
        ax.text(0.01, y, "%-6s %s" % (c["result"].upper(), c["check"]), va="center", ha="left",
                fontsize=8, color="white", fontweight="bold")
    ax.set_yticks([])
    ax.set_xticks([])
    ax.invert_yaxis()
    ax.set_title("wp-11924-01 · acceptance self-check (%d checks, overall %s) — platform gate is authoritative"
                 % (len(checks), V["overall"]), fontsize=10)
    fig.tight_layout()
    out = ART / "fig_verification.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    for fn in (fig_inventory, fig_coverage, fig_verification):
        p = fn()
        mirror = DOCS / p.name
        mirror.write_bytes(p.read_bytes())
        print("%-28s %7d bytes -> %s" % (p.name, p.stat().st_size, mirror))


if __name__ == "__main__":
    main()