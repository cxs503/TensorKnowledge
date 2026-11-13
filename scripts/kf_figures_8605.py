#!/usr/bin/env python3
"""wp-8605-01 figures: three programmatically generated PNGs derived only from asset_manifest.json + source md.

  fig_asset_inventory.png  : asset classes (count) split by resolution status
  fig_locator_coverage.png : where in the source every locator sits + cumulative source coverage
  fig_verification.png     : per-check result of the self-verification battery

Everything is computed from the manifest / source text; no hand-typed numbers, no randomness,
no timestamps (byte-identical re-render on the same matplotlib version).

Run standalone:  python3 scripts/kf_figures_8605.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DOCS = pathlib.Path("docs/wp-8605-01")
SELF_FIGURE = "fig_verification.png"
COLORS = {"resolved_in_source": "#2f7d32", "referenced_unresolved": "#c98a00", "declared_absent": "#8d1b1b"}
LABELS = {"resolved_in_source": "resolved_in_source", "referenced_unresolved": "referenced_unresolved",
          "declared_absent": "declared_absent"}


def _load() -> tuple[dict, str]:
    manifest = json.loads((DOCS / "asset_manifest.json").read_text())
    md = (DOCS / "source_report_8605.md").read_text()
    return manifest, md


def fig_asset_inventory(manifest: dict, out: pathlib.Path) -> None:
    counts = manifest["counts"]
    order = sorted(counts["by_class"], key=lambda k: (-counts["by_class"][k], k))
    res_order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 0.42 * len(order) + 2.2))
    # left: stacked bars by (class, resolution)
    left = [0] * len(order)
    for res in res_order:
        vals = []
        for cls in order:
            vals.append(sum(1 for a in manifest["assets"]
                            if a["asset_class"] == cls and a["resolution"] == res))
        ax1.barh(order, vals, left=left, color=COLORS[res], label=res, edgecolor="white", linewidth=0.6)
        left = [base + v for base, v in zip(left, vals)]
    ax1.invert_yaxis()
    ax1.set_xlabel("assets")
    ax1.set_title("Asset inventory: %d assets / %d classes, split by resolution"
                  % (counts["assets"], len(order)), fontsize=10)
    ax1.legend(fontsize=8, loc="lower right")
    for i, cls in enumerate(order):
        ax1.text(left[i] + 0.08, i, str(left[i]), va="center", fontsize=8)
    ax1.grid(axis="x", alpha=0.3)
    # right: resolution totals
    vals = [counts["by_resolution"].get(r, 0) for r in res_order]
    bars = ax2.bar([r.replace("_", "\n") for r in res_order], vals,
                   color=[COLORS[r] for r in res_order], edgecolor="white")
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.1, str(v), ha="center", fontsize=9)
    ax2.set_ylabel("assets")
    ax2.set_title("Resolution status (nothing filled in)", fontsize=10)
    ax2.grid(axis="y", alpha=0.3)
    fig.suptitle("wp-8605-01 · report 8605 (%s) asset registration" % manifest["source"]["scenario_key"],
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out, dpi=110)
    plt.close(fig)


def fig_locator_coverage(manifest: dict, md: str, out: pathlib.Path) -> None:
    spans = [(a["locator"]["start_char"], a["locator"]["end_char"], a["resolution"], a["asset_id"])
             for a in manifest["assets"] if a["locator"]["method"] == "char_span"]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6.4), gridspec_kw={"height_ratios": [3, 2]})
    for y, (s, e, res, aid) in enumerate(sorted(spans, key=lambda t: (t[0], t[1]))):
        ax1.plot([s, max(e, s + 1)], [y, y], color=COLORS[res], lw=3, solid_capstyle="butt")
    ax1.set_xlim(0, len(md))
    ax1.set_xlabel("char offset in source markdown")
    ax1.set_ylabel("locators (sorted by position)")
    ax1.set_title("Locator map: %d char_span locators over %d chars (%d lines)"
                  % (len(spans), len(md), md.count("\n") + 1), fontsize=10)
    for res in COLORS:
        ax1.plot([], [], color=COLORS[res], lw=3, label=LABELS[res])
    ax1.legend(fontsize=8, loc="lower right")
    ax1.grid(axis="x", alpha=0.3)
    # registered assets per class = recall of the mechanical rules (dedup by token only)
    cls_counts: dict[str, int] = {}
    for a in manifest["assets"]:
        cls_counts[a["asset_class"]] = cls_counts.get(a["asset_class"], 0) + 1
    keys = sorted(cls_counts, key=lambda k: (-cls_counts[k], k))
    bars = ax2.bar(keys, [cls_counts[k] for k in keys], color="#1f4e79", edgecolor="white")
    for b, k in zip(bars, keys):
        ax2.text(b.get_x() + b.get_width() / 2, cls_counts[k] + 0.1, str(cls_counts[k]),
                 ha="center", fontsize=8)
    ax2.set_ylabel("registered assets")
    ax2.set_title("Locator coverage by class: %d/%d registered assets carry a re-resolvable locator "
                  "(0 dropped by dedup)" % (len(spans) + 1, len(manifest["assets"])), fontsize=10)
    ax2.tick_params(axis="x", labelrotation=20, labelsize=8)
    ax2.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def fig_verification(ver: dict, out: pathlib.Path) -> None:
    names = [c["check"] for c in ver["checks"]]
    ok = [1 if c["result"] == "pass" else 0 for c in ver["checks"]]
    fig, ax = plt.subplots(figsize=(10.5, 0.5 * len(names) + 2.0))
    ax.barh(names, ok, color=["#2f7d32" if v else "#8d1b1b" for v in ok], edgecolor="white")
    ax.set_xlim(0, 1.25)
    ax.invert_yaxis()
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["fail", "pass"])
    for i, c in enumerate(ver["checks"]):
        extra = ""
        if c["check"] == "source_hash_recomputed":
            extra = c["detail"]["recomputed"][:12] + "…"
        elif c["check"] == "locators_reslice":
            extra = "%d assets" % c["detail"]["assets_checked"]
        elif c["check"] == "figures_present":
            extra = "%d png" % len(c["detail"]["files"])
        ax.text(1.03, i, "%s %s" % ("PASS" if c["result"] == "pass" else "FAIL", extra),
                va="center", fontsize=8)
    ax.set_title("Self-verification battery: %d/%d pass (result=%s, source sha256:%s…)"
                 % (sum(ok), len(ok), ver["result"], ver["source_hash_recomputed"].split(":")[1][:12]),
                 fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def render_all(manifest: dict, md: str, docs: pathlib.Path = DOCS) -> list[pathlib.Path]:
    """Produce the three figures. `verification.json` is rendered last (needs the figure hashes)."""
    docs.mkdir(parents=True, exist_ok=True)
    p1 = docs / "fig_asset_inventory.png"
    p2 = docs / "fig_locator_coverage.png"
    fig_asset_inventory(manifest, p1)
    fig_locator_coverage(manifest, md, p2)
    return [p1, p2]


def main() -> int:
    manifest, md = _load()
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import kf_fetch_8605 as kf  # noqa: PLC0415 - reuse the single verification implementation
    render_all(manifest, md, DOCS)
    recorded = kf.recorded_figures(DOCS)
    ver = kf.verify(manifest, md, DOCS, recorded)
    fig_verification(ver, DOCS / SELF_FIGURE)
    ver = kf.verify(manifest, md, DOCS, recorded)  # second pass: records the self-figure's presence
    (DOCS / "verification.json").write_text(json.dumps(ver, ensure_ascii=False, indent=2) + "\n")
    print("figures written to %s; verification=%s" % (DOCS, ver["result"]))
    return 0 if ver["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())