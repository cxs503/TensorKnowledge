#!/usr/bin/env python3
"""Figure for wp-14351-02: classification score + located-evidence map.

Both panels are rendered from ``classification.json`` only (no hand-typed
numbers): the left panel is the declared selection score, the right panel maps
every located signal onto the character span of the report it was found in.

Labels are ASCII because the default matplotlib font (Noto Sans) carries no CJK
glyphs in this image; section headings are therefore shown by id + role, and the
quotes themselves stay verbatim in the JSON artefact.

Usage: python scripts/figures_wp14351_02.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = REPO_ROOT / "docs" / "kf" / "wp-14351-02"
CLASSIFICATION = PKG_DIR / "classification.json"
OUT = PKG_DIR / "figures" / "classification_evidence_map.png"


def main() -> int:
    doc = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
    scores = doc["report_type"]["scores"]
    primary = doc["report_type"]["value"]
    signals = doc["signals"]
    sections = doc["structure"]["sections"]
    n_chars = doc["structure"]["chars"]

    fig, (ax0, ax1) = plt.subplots(
        2, 1, figsize=(12.0, 7.2), gridspec_kw={"height_ratios": [1.0, 1.25]}
    )

    # ---- panel A: declared selection score -------------------------------
    order = sorted(scores, key=lambda k: scores[k])
    colors = ["#c62828" if k == primary else "#90a4ae" for k in order]
    bars = ax0.barh(order, [scores[k] for k in order], color=colors, height=0.6)
    for bar, k in zip(bars, order):
        ax0.text(bar.get_width() + 0.08, bar.get_y() + bar.get_height() / 2,
                 f"{scores[k]}", va="center", fontsize=10)
        core = sum(1 for s in signals if s["report_type"] == k and s["strength"] == "core")
        sup = sum(1 for s in signals if s["report_type"] == k and s["strength"] == "supporting")
        ax0.text(0.1, bar.get_y() + bar.get_height() / 2, f"core {core} / support {sup}",
                 va="center", fontsize=8, color="white")
    zero = [t for t in doc["report_type"]["excluded"]]
    ax0.set_xlim(0, max(scores.values()) + 1.5)
    ax0.set_xlabel("declared score = sum over distinct registry signals of 2*core + 1*supporting")
    ax0.set_title(
        f"report 14351 -> report_type '{primary}' (hypothesis, confidence "
        f"{doc['report_type']['confidence']}, margin {doc['report_type']['margin_over_runner_up']})"
        f" | zero-signal types excluded: {', '.join(zero)}",
        fontsize=10,
    )
    ax0.grid(axis="x", alpha=0.3)

    # ---- panel B: located evidence map -----------------------------------
    type_rows = {t: i for i, t in enumerate(sorted({s["report_type"] for s in signals}))}
    for sec in sections:
        ax1.add_patch(
            Rectangle((sec["start_offset"], -1.2), sec["end_offset"] - sec["start_offset"], len(type_rows) + 0.2,
                      facecolor="#eceff1" if int(sec["id"].split("-")[1]) % 2 else "#fafafa",
                      edgecolor="#b0bec5", linewidth=0.6, zorder=0)
        )
        ax1.text(sec["start_offset"] + 25, -0.95,
                 f"{sec['id']} " + ("/".join(sec["role_keywords_hit"]) or "unmapped")[:26],
                 fontsize=7, rotation=0, color="#37474f")
    for s in signals:
        row = type_rows[s["report_type"]]
        loc = s["locator"]
        ax1.scatter([loc["start_offset"]], [row], s=140 if s["strength"] == "core" else 60,
                    marker="o" if s["strength"] == "core" else "s",
                    color="#c62828" if s["strength"] == "core" else "#1565c0",
                    zorder=3)
        ax1.annotate(s["registry_signal"], (loc["start_offset"], row),
                     textcoords="offset points", xytext=(0, 10), fontsize=7, ha="center")
    ax1.set_yticks(list(type_rows.values()))
    ax1.set_yticklabels(list(type_rows), fontsize=9)
    ax1.set_ylim(-1.3, len(type_rows) - 0.2)
    ax1.set_xlim(0, n_chars)
    ax1.set_xlabel(f"character offset in report markdown (total {n_chars} chars, "
                   f"sha256-verified snapshot)")
    ax1.set_title("located signal evidence per report_type (circle = core: heading/table, "
                  "square = supporting: inline); bands = structural sections", fontsize=10)
    ax1.grid(axis="x", alpha=0.25, zorder=0)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())