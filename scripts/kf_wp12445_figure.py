"""Figure for wp-12445-01: asset registration overview (data-driven, zero hand-copy).

Panel A: asset counts by class, stacked by resolution status.
Panel B: locator map -- each asset's verified char span on the markdown axis.

Usage: python3 scripts/kf_wp12445_figure.py
Output: docs/kf/wp-12445-01/figures/asset_registration_overview.png
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import re
import matplotlib.pyplot as plt  # noqa: E402

PKG = "wp-12445-01"
KF = pathlib.Path("docs/kf") / PKG
FIGDIR = KF / "figures"
COLORS = {"resolved_in_source": "#2a9d8f", "referenced_unresolved": "#e9c46a",
          "declared_absent": "#a8a8a8"}


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    man = json.loads((KF / "asset_manifest.json").read_text(encoding="utf-8"))
    assets = man["assets"]
    src = man["source"]

    classes = sorted({a["asset_class"] for a in assets})
    res_order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 6.4),
                                   gridspec_kw={"width_ratios": [1, 1.35]})

    # ---- Panel A
    left = [0] * len(classes)
    for res in res_order:
        vals = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == res)
                for c in classes]
        if not any(vals):
            continue
        ax1.barh(classes, vals, left=left, color=COLORS[res], edgecolor="white",
                 label="%s (%d)" % (res, sum(vals)))
        left = [l + v for l, v in zip(left, vals)]
    for i, c in enumerate(classes):
        ax1.text(left[i] + 0.05, i, str(left[i]), va="center", fontsize=9)
    ax1.set_xlabel("assets")
    ax1.set_title("A) %d registered assets / %d classes (by resolution)"
                  % (man["counts"]["assets"], len(classes)), fontsize=11)
    ax1.legend(fontsize=8, loc="lower right")
    ax1.invert_yaxis()
    ax1.set_xlim(0, max(left) + 0.7)

    # ---- Panel B
    for i, a in enumerate(assets):
        loc = a["locator"]
        ax2.plot([loc["start_char"], loc["end_char"]], [i, i], lw=7,
                 color=COLORS[a["resolution"]], solid_capstyle="butt")
        # no CJK font is installed on this host -> render an ASCII-safe label
        lab = re.sub(r"[^\x20-\x7e]", "", a["label"]).strip() or a["asset_class"]
        if re.search(r"[^\x20-\x7e]", a["label"]):
            lab = "%s (%s): %s" % (a["asset_id"], a["asset_class"], lab[:38])
        ax2.text(loc["end_char"] + 25, i, "L%d  %s" % (loc["start_line"], lab),
                 va="center", fontsize=7.5)
    for an in man.get("anchors", []):
        ax2.plot([an["start_char"]], [-0.9], marker="|", ms=12, color="#264653")
    ax2.set_yticks([])
    ax2.set_xlim(-40, src["chars"] * 1.02)
    ax2.set_ylim(len(assets) + 2.2, -1.9)
    ax2.set_xlabel("character offset in markdown (chars=%d, bytes_utf8=%d)"
                   % (src["chars"], src["bytes_utf8"]))
    ax2.set_title("B) locator map: exact char span per asset (ticks on top row = %d body anchors)"
                  % man["counts"]["anchors"], fontsize=11)
    ax2.grid(axis="x", ls=":", alpha=0.5)
    ax2.text(0.01, 0.02,
             "sha256 recomputed = %s...%s\n== contract source_hash: %s"
             % (src["hash"][:16], src["hash"][-8:], man["integrity"]["hash_matches_contract"]),
             transform=ax2.transAxes, fontsize=8, family="monospace",
             bbox=dict(fc="#f4f1de", ec="#bdb7a6"))
    for res, c in COLORS.items():
        ax2.plot([], [], lw=5, color=c, label=res)
    ax2.legend(fontsize=8, loc="upper right", ncol=3)

    fig.suptitle("wp-12445-01 · report 12445 asset registration (no extraction, claims=[])",
                 fontsize=12.5)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = FIGDIR / "asset_registration_overview.png"
    fig.savefig(out, dpi=150)
    print("wrote", out, out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()