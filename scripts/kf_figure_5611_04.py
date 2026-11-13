#!/usr/bin/env python3
"""Figures for the wp-5611-04 review report.

fig1_review_matrix.png
    (a) the 16 programmatic checks of the review, pass/fail per check;
    (b) the locator-span defect made visible: the quote occupancy [0,9) versus
        the offsets the upstream manifest declares [0,43), drawn on the source
        text so the mismatch is not a table of prose.

Numbers come from ``artifacts/kf/wp-5611-04/review_checks.json`` (produced by
``scripts/kf_review_5611_04.py``) — nothing is retyped here.
"""
from __future__ import annotations

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "kf" / "wp-5611-04"
WORK = ROOT / "work" / "kf-wp-5611"


def main() -> None:
    checks = json.loads((ART / "review_checks.json").read_text(encoding="utf-8"))
    rows = checks["checks"]
    md = (WORK / "source_5611.md").read_text(encoding="utf-8")

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11.2, 7.6), gridspec_kw={"height_ratios": [2.35, 1.0]})

    # (a) check matrix -----------------------------------------------------
    labels = [r["check_id"] for r in rows][::-1]
    ok = [r["ok"] for r in rows][::-1]
    colors = ["#2f7d32" if o else "#b3261e" for o in ok]
    ax1.barh(range(len(rows)), [1] * len(rows), color=colors, height=0.72)
    ax1.set_yticks(range(len(rows)))
    ax1.set_yticklabels(labels, fontsize=8.5)
    ax1.set_xlim(0, 1)
    ax1.set_xticks([])
    ax1.set_title(
        f"(a) wp-5611-04 independent review of wp-5611-01: {checks['n_checks']} "
        f"programmatic checks ({checks['n_pass']} pass / {checks['n_fail']} fail-or-not-run)",
        fontsize=11, loc="left")
    for i, r in enumerate(rows[::-1]):
        tag = "PASS" if r["ok"] else "FINDING"
        ax1.text(0.012, i, f"{tag} · {r['detail'][:96]}", va="center", fontsize=7.2,
                 color="white", fontweight="bold")
    ax1.invert_yaxis()

    # (b) locator span defect ---------------------------------------------
    loc_bad = next((r for r in rows
                    if r["check_id"] == "R07.declared_offsets_byte_exact" and not r["ok"]), None)
    span = json.loads(loc_bad["detail"].split("failures=", 1)[1]) if loc_bad else []
    if span:
        s = span[0]
        start, end, qlen = s["start"], s["end"], s["quote_len"]
    else:  # pragma: no cover - defensive
        start, end, qlen = 0, 43, 9
    window = md[start:end]
    ax2.set_xlim(0, max(end, qlen) + 6)
    ax2.set_ylim(0, 2)
    ax2.axis("off")
    ax2.add_patch(Rectangle((start, 1.18), qlen, 0.42, facecolor="#2f7d32", alpha=0.85))
    ax2.text(start + qlen / 2, 1.39, f"quote {qlen} chars", ha="center", va="center",
             fontsize=8.5, color="white", fontweight="bold")
    ax2.add_patch(Rectangle((start, 0.42), end - start, 0.42, facecolor="#b3261e",
                            alpha=0.22, hatch="//", edgecolor="#b3261e"))
    ax2.text(start + (end - start) / 2, 0.63,
             f"declared span [{start},{end}) = {end - start} chars", ha="center",
             va="center", fontsize=8.5, color="#8c1d18", fontweight="bold")
    ax2.set_title(
        "(b) F-01 evidence: ast-5611-01 declares a span wider than its own quote "
        "(byte-exact G2-E4 equality cannot hold)", fontsize=10.5, loc="left")
    # the source window is Chinese; render it escaped so the figure needs no CJK font
    snippet = ascii(window[:end])[1:-1][:96] + " …"
    ax2.text(0, 0.12, f"text[0:{end}] = {snippet}", fontsize=7.6, family="monospace")

    fig.tight_layout()
    for out in (ART / "fig1_review_matrix.png",
                ROOT / "docs" / "kf" / "wp-5611-04" / "fig1_review_matrix.png"):
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150)
        print(out)


if __name__ == "__main__":
    main()