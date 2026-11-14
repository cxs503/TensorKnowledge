#!/usr/bin/env python3
"""wp-444-04 · independent re-derivation of the numbers printed by report 444.

The reviewed report prints, in its §③/§⑥ tables, four "基准 / 实际" pairs and a
15/15 pass tally, and the governance block prints an "原始长度: N 字符".  This
script re-derives every one of them from closed forms and from the source bytes:
the table cells are *parsed* out of the markdown, never transcribed, so a reader
can diff "what the report prints" against "what the named formula gives".

Anchors:
  ITTC-1957      Cf = 0.075 / (log10 Re - 2)^2
  Blasius (mean) Cf = 1.328 / sqrt(Re_L)
  Prandtl-Schlichting  Cf = 0.455 / (log10 Re_L)^2.58      (with -1700/Re variant)
  Holtrop-Mennen 1+k needs (L, B, T, Cp, nabla); Cb alone under-determines it.

Emitted: --out JSON (default /tmp/wp-444-04/observations.json) and the review
figure (--figure, default docs/kf/wp-444-04/fig_wp444_04_recompute.png).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs/kf/wp-444-04/source/report_444.md"
DEFAULT_OUT = Path("/tmp/wp-444-04/observations.json")
DEFAULT_FIGURE = ROOT / "docs/kf/wp-444-04/fig_wp444_04_recompute.png"

NUM = r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"


# ---------------------------------------------------------------- closed forms
def ittc1957(re: float) -> float:
    return 0.075 / (math.log10(re) - 2.0) ** 2


def blasius_mean(re: float) -> float:
    return 1.328 / math.sqrt(re)


def prandtl_schlichting(re: float) -> float:
    return 0.455 / (math.log10(re) ** 2.58)


def prandtl_schlichting_rough(re: float) -> float:
    return prandtl_schlichting(re) - 1700.0 / re


def holtrop_form_factor(L: float, B: float, T: float, cb: float, cm: float,
                        c_stern: float = 0.0) -> float:
    """Holtrop & Mennen (1982) form factor, as printed in the review report.

    c14 = 1 + 0.011 c_stern; nabla = cb L B T; Cp = cb / Cm.
    """
    nabla = cb * L * B * T
    cp = cb / cm
    c14 = 1.0 + 0.011 * c_stern
    return (0.93 + 0.487118 * c14
            * (B / L) ** 1.06806
            * (T / L) ** 0.46106
            * (L / nabla ** (1.0 / 3.0)) ** 0.121563
            * (L ** 3 / nabla) ** 0.36486
            * (1.0 - cp) ** (-0.604247))


def implied_re(value: float, forward) -> float:
    """Re at which `forward` returns `value` (bisection: monotone decreasing in Re)."""
    lo, hi = 1e4, 1e11
    for _ in range(400):
        mid = math.sqrt(lo * hi)
        if forward(mid) > value:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


# --------------------------------------------------------------------- parsing
def table_after(md_lines: list[str], heading_prefix: str) -> list[list[str]]:
    """First GFM table under the level-2 heading that starts with `heading_prefix`."""
    for i, line in enumerate(md_lines):
        if line.startswith("## ") and heading_prefix in line:
            j = i + 1
            while j < len(md_lines) and not md_lines[j].startswith("|"):
                if md_lines[j].startswith("## "):
                    return []
                j += 1
            rows = []
            while j < len(md_lines) and md_lines[j].startswith("|"):
                if not re.match(r"^\|[-|: ]+\|$", md_lines[j]):
                    rows.append([c.strip().strip("*").strip()
                                 for c in md_lines[j].strip().strip("|").split("|")])
                j += 1
            return rows
    return []


def parse_report(md: str) -> dict:
    lines = md.split("\n")
    results = []
    for row in table_after(lines, "计算结果"):
        if len(row) < 5 or not re.fullmatch(NUM, row[1]):
            continue
        results.append({"category": row[0], "questions": int(float(row[1])),
                        "passed": int(float(row[2])),
                        "max_deviation": float(row[3]), "tolerance": row[4]})
    errors = []
    for row in table_after(lines, "误差判定"):
        if len(row) < 5:
            continue
        if not (re.search(NUM, row[1]) and re.search(NUM, row[2])):
            continue
        label = row[0]
        re_m = re.search(r"Re[_L]*\s*=\s*(" + NUM + ")", label)
        errors.append({"label": label, "reported_baseline": float(row[1]),
                       "reported_actual": float(row[2]), "reported_deviation": row[3],
                       "reported_within_3pct": "YES" in row[4].upper(),
                       "re": float(re_m.group(1)) if re_m else None,
                       "cb": float(re.search(r"Cb\s*=\s*(" + NUM + ")", label).group(1))
                       if re.search(r"Cb\s*=\s*(" + NUM + ")", label) else None})
    gov = re.search(r"原始长度:\s*(\d+)\s*字符", md)
    return {
        "results_table": results,
        "errors_table": errors,
        "governance_original_chars": int(gov.group(1)) if gov else None,
    }


# ------------------------------------------------------------------ prediction
FORMULA = {
    "ITTC-1957": ittc1957,
    "Blasius": blasius_mean,
    "P-S": prandtl_schlichting,
}


def predict(row: dict) -> dict:
    label = row["label"]
    key = next((k for k in FORMULA if label.startswith(k)), None)
    if key is not None:
        f = FORMULA[key]
        val = f(row["re"])
        dev = (row["reported_baseline"] - val) / val * 100.0
        variant = prandtl_schlichting_rough(row["re"]) if key == "P-S" else None
        return {
            "status": "recomputed", "formula": key, "re": row["re"],
            "recomputed": val, "reported": row["reported_baseline"],
            "deviation_pct": dev, "abs_deviation_pct": abs(dev),
            "within_3pct": abs(dev) < 3.0,
            "variant_value": variant,
            "variant_deviation_pct": (row["reported_baseline"] - variant) / variant * 100.0
            if variant is not None else None,
            "implied_re": implied_re(row["reported_baseline"], f),
        }
    return {"status": "withheld", "formula": None, "reported": row["reported_baseline"],
            "recomputed": None, "deviation_pct": None, "within_3pct": None,
            "reason": "Holtrop-Mennen 1+k needs (L, B, T, Cp, nabla); the row states Cb only, "
                      "and the report's own parameter table lists Cb, L, B, T — under-determined"}


def holtrop_family(cb: float) -> dict:
    vals = []
    for L in (80.0, 100.0, 150.0, 200.0, 280.0, 320.0):
        for bl in (0.11, 0.14, 0.16, 0.18, 0.20):
            for tl in (0.030, 0.040, 0.050, 0.060):
                for cm in (0.96, 0.98, 0.995):
                    vals.append(holtrop_form_factor(L, bl * L, tl * L, cb, cm))
    vals.sort()
    return {"samples": len(vals), "min": vals[0], "p10": vals[len(vals) // 10],
            "median": vals[len(vals) // 2], "p90": vals[len(vals) * 9 // 10],
            "max": vals[-1], "values": vals}


def curve_crossover() -> float:
    """Re where the ITTC-1957 line and the P-S line cross (both decrease in Re)."""
    lo, hi = 1e5, 1e9
    for _ in range(300):
        mid = math.sqrt(lo * hi)
        if ittc1957(mid) - prandtl_schlichting(mid) > 0:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def ordering_check(re: float) -> dict:
    """At a fixed Re, does ITTC-1957 sit below / above the P-S line?"""
    return {"re": re, "ittc1957": ittc1957(re), "prandtl_schlichting": prandtl_schlichting(re),
            "ittc_below_ps": ittc1957(re) < prandtl_schlichting(re),
            "crossover_re": curve_crossover()}


# ---------------------------------------------------------------------- figure
def make_figure(md: str, obs: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    preds = obs["predictions"]
    deriv = [(r["label"], p) for r, p in zip(obs["errors_table"], preds)
             if p["status"] == "recomputed"]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4))
    ax = axes[0]
    names = [n.split(" (")[0] for n, _ in deriv]
    devs = [p["deviation_pct"] for _, p in deriv]
    colors = ["#c0392b" if abs(d) > 3 else "#27ae60" for d in devs]
    ax.bar(names, devs, color=colors, width=0.55)
    ax.axhline(0, color="k", lw=0.8)
    ax.axhline(3, color="k", ls="--", lw=0.9)
    ax.axhline(-3, color="k", ls="--", lw=0.9)
    ax.text(0.02, 3.15, "+3% acceptable band", fontsize=8, transform=ax.get_yaxis_transform())
    for i, (n, p) in enumerate(deriv):
        ax.annotate(f"reported {p['reported']:.6f}\nformula {p['recomputed']:.6f}",
                    (i, devs[i]), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=7)
    ax.set_ylabel("§6 基准 column vs named formula  [%]")
    ax.set_title("A. Report 444 §6 baselines re-derived\n(dashed = ±3% acceptance band)")
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    res = [r for r in obs["re"] if 1e5 <= r <= 1e9]
    ax.plot(res, [ittc1957(r) for r in res], label="ITTC-1957  0.075/(log10Re-2)^2")
    ax.plot(res, [prandtl_schlichting(r) for r in res], label="Prandtl-Schlichting 0.455/(log10Re)^2.58")
    ax.plot(res, [blasius_mean(r) for r in res], label="Blasius 1.328/sqrt(Re)")
    for _, p in deriv:
        ax.plot([p["re"]], [p["recomputed"]], "o", ms=6, mfc="none", mec="k")
        ax.annotate("", xy=(p["re"], p["recomputed"]),
                    xytext=(p["re"], p["reported"]),
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.4))
        ax.plot([p["re"]], [p["reported"]], "x", color="#c0392b", ms=9)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Re")
    ax.set_ylabel("Cf")
    ax.set_title("B. Reported points (x) vs their own named curves (o)\nred arrows = the gap this review found")
    ax.legend(fontsize=7, loc="lower left")
    ax.grid(alpha=0.3, which="both")

    ax = axes[2]
    fam = obs["holtrop"]["family"]
    ax.hist(fam["values"], bins=24, color="#7f8c8d", alpha=0.85)
    ax.axvline(obs["holtrop"]["reported"], color="#c0392b", lw=1.6,
               label=f"report 444 prints {obs['holtrop']['reported']:.4f}")
    ax.axvline(fam["median"], color="#2980b9", lw=1.2, ls="--",
               label=f"family median {fam['median']:.4f}")
    ax.set_xlabel("1+k  (Holtrop-Mennen, Cb = 0.6 family)")
    ax.set_ylabel("count of plausible (L, B/L, T/L, Cm) tuples")
    ax.set_title(f"C. 1+k is not determined by Cb alone\n({fam['samples']} tuples, "
                 f"{fam['min']:.3f}–{fam['max']:.3f})")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)

    fig.suptitle("wp-444-04 independent re-derivation of report 444 numbers "
                 "(source sha256 4068f881…57af2)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    print("figure ->", path.relative_to(ROOT))


# ------------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(SNAPSHOT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--figure", default=str(DEFAULT_FIGURE))
    args = ap.parse_args(argv)

    md = Path(args.source).read_text(encoding="utf-8")
    parsed = parse_report(md)
    preds = [predict(r) for r in parsed["errors_table"]]

    cats = [r for r in parsed["results_table"] if "合计" not in r["category"]]
    total = next((r for r in parsed["results_table"] if "合计" in r["category"]), None)
    asked = sum(r["questions"] for r in cats)
    passed = sum(r["passed"] for r in cats)

    # governance block arithmetic: "原始长度: N 字符" must equal a real prefix length
    gov_chars = parsed["governance_original_chars"]
    prefix_boundary = None
    if gov_chars:
        lines = md.split("\n")
        for k in range(1, len(lines) + 1):
            if len("\n".join(lines[:k])) == gov_chars:
                prefix_boundary = {"lines": k, "last_line": lines[k - 1][:40]}
                break

    obs = {
        "package_id": "wp-444-04", "report_id": "444",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(Path(args.source).relative_to(ROOT)),
        **parsed,
        "predictions": preds,
        "re": [10 ** (5 + i / 40) for i in range(0, 161)],
        "tally_arithmetic": {
            "questions": asked, "passed": passed,
            "declared_questions": [r["questions"] for r in cats],
            "declared_passed": [r["passed"] for r in cats],
            "printed_total": {"questions": total["questions"], "passed": total["passed"]}
            if total else None,
            "sum_matches_printed_total": bool(total) and asked == total["questions"]
            and passed == total["passed"]},
        "governance_original_chars": gov_chars,
        "governance_prefix_boundary": prefix_boundary,
        "ordering_at_1e8": ordering_check(1e8),
        "holtrop": {"reported": next(p["reported"] for p in preds
                                     if p["status"] == "withheld"),
                    "cb": next(r["cb"] for r in parsed["errors_table"] if r["cb"] is not None),
                    "family": holtrop_family(0.6)},
    }
    obs["holtrop"]["reported_in_family"] = (
        obs["holtrop"]["family"]["min"] <= obs["holtrop"]["reported"]
        <= obs["holtrop"]["family"]["max"])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obs, ensure_ascii=False, indent=1), encoding="utf-8")

    make_figure(md, obs, Path(args.figure))
    print(json.dumps({
        "predictions": [{k: (round(v, 8) if isinstance(v, float) else v)
                         for k, v in p.items() if k in
                         ("formula", "re", "recomputed", "reported", "deviation_pct",
                          "within_3pct", "implied_re", "status")} for p in preds],
        "tally_arithmetic": obs["tally_arithmetic"],
        "governance_original_chars": gov_chars,
        "governance_prefix_boundary": prefix_boundary,
        "ordering_at_1e8": obs["ordering_at_1e8"],
        "holtrop_family": {k: round(v, 4) for k, v in obs["holtrop"]["family"].items()
                           if k != "values"},
        "holtrop_reported": obs["holtrop"]["reported"],
        "holtrop_reported_in_family": obs["holtrop"]["reported_in_family"],
    }, ensure_ascii=False, indent=1))
    print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())