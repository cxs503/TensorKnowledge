"""Figures for the wp-331-04 review report.

fig1  error/budget ratios for the four reported metrics (numbers taken from
      review_report.json derived_metrics, which are computed from the source table)
fig2  illustration for finding F3: the two power laws F ~ delta^1.5 (Hertz) and
      F ~ delta^1.4108 (reported fit), normalised, over the stroke the report
      actually used (delta/R from 0 to 0.5)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "kf" / "wp-331-04"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

rev = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
d = rev["derived_metrics"]

# ---- fig1: error / budget ratio -------------------------------------------------
labels = [
    "Hertz exponent\n(|Δ|={:.4f} / ±{:.2f})".format(d["exponent_abs_deviation"], d["exponent_tolerance"]),
    "Hertz stiffness\n({:.1f}% / ≤{:.0f}%)".format(d["stiffness_error_pct"], d["stiffness_target_pct"]),
    "Energy drift\n({:.1f}% / ≤{:.0f}%)".format(d["energy_drift_pct"], d["energy_target_pct"]),
    "Beam stiffness\n({:.4f}% / ≤{:.0f}%)".format(d["beam_error_pct"], d["stiffness_target_pct"]),
]
ratios = [
    d["exponent_tolerance_overshoot_factor"],
    d["stiffness_budget_overshoot_factor"],
    d["energy_budget_overshoot_factor"],
    1.0 / d["beam_budget_margin_factor"],
]
colors = ["#c62828" if r > 1 else "#2e7d32" for r in ratios]

fig, ax = plt.subplots(figsize=(7.2, 4.0))
bars = ax.bar(range(4), ratios, color=colors, width=0.6)
ax.axhline(1.0, color="black", ls="--", lw=1.2, label="acceptance budget (=1)")
ax.set_yscale("log")
ax.set_ylabel("reported error / acceptance budget  (log)")
ax.set_xticks(range(4))
ax.set_xticklabels(labels, fontsize=8)
ax.set_title("wp-331-04 review: every reported metric vs its own acceptance budget", fontsize=10)
for b, r in zip(bars, ratios):
    ax.annotate(f"{r:.4g}×", (b.get_x() + b.get_width() / 2, r), ha="center", va="bottom", fontsize=9)
ax.legend(fontsize=8)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
p1 = FIG / "error_budget_ratio.png"
fig.savefig(p1, dpi=150)
plt.close(fig)

# ---- fig2: F3 validity-range illustration ---------------------------------------
r_ratio = np.linspace(1e-3, d["indent_over_R"], 400)
f_hertz = r_ratio ** 1.5
f_fit = r_ratio ** d["exponent_reported"]
fig, ax = plt.subplots(figsize=(7.2, 3.6))
ax.plot(r_ratio, f_hertz, "k-", lw=2, label=r"Hertz: $F \propto \delta^{1.5}$")
ax.plot(r_ratio, f_fit, "r--", lw=2,
        label=r"reported fit: $F \propto \delta^{%.4f}$" % d["exponent_reported"])
ax.axvspan(0.05, d["indent_over_R"], color="#ffcdd2", alpha=0.6,
           label=r"beyond small-strain guide $(\delta/R \gtrsim 0.05)$")
ax.set_xlabel(r"normalised indentation $\delta/R$  (stroke ends at %.2f)" % d["indent_over_R"])
ax.set_ylabel("normalised contact force F/F_max")
ax.set_title("finding F3: the fit window runs far outside Hertz's validity range", fontsize=10)
ax.legend(fontsize=8, loc="upper left")
ax.grid(alpha=0.3)
fig.tight_layout()
p2 = FIG / "hertz_validity_window.png"
fig.savefig(p2, dpi=150)
plt.close(fig)


figures = [
    {
        "name": "error_budget_ratio.png",
        "caption": ("Number taken from the source results table: every metric expressed as its ratio to "
                    "its own acceptance budget (dashed line = 1). Hertz exponent 1.78x, stiffness 14.7x, "
                    "energy drift 58.6x over budget; beam 0.0042x (the only PASS). Red = over budget."),
        "file": p1.name,
        "sha256": hashlib.sha256(p1.read_bytes()).hexdigest(),
    },
    {
        "name": "hertz_validity_window.png",
        "caption": (r"Illustration for finding F3: the two power laws over the stroke the report actually "
                    r"used ($\delta/R$ up to %.2f, from max_indent/R). The normalised curves are drawn "
                    r"from the reported exponent only - this is a validity-range argument, not a claim "
                    r"about the DEM solution itself." % d["indent_over_R"]),
        "file": p2.name,
        "sha256": hashlib.sha256(p2.read_bytes()).hexdigest(),
    },
]
(FIG / "figures.json").write_text(json.dumps(figures, ensure_ascii=False), encoding="utf-8")
for f in figures:
    print(f["name"], f["sha256"][:16])