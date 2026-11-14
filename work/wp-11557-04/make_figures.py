#!/usr/bin/env python3
"""Figures for wp-11557-04: what the report's own formulas actually imply."""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIGS = ROOT / "docs/kf/wp-11557-04/figures"
FIGS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, "/root/tp-agent/work/m19513/src")
from tensordem import ice_mixed_mode as mm  # noqa: E402

cfg = mm.IceMixedModeConfig()
p1 = json.loads((HERE / "probe_results.json").read_text())
b1 = p1["B1_closed_form"]
Vc = mm.compute_critical_velocity(cfg)

# ---------------- Fig 1: resistances vs velocity, hardcoded weight bands
V = np.linspace(0.0, 5.0, 501)
Rc = np.array([mm.compute_crushing_resistance(cfg, v) for v in V]) / 1e6
Rb = np.array([mm.compute_bending_resistance(cfg, v) for v in V]) / 1e6
Rs = np.array([mm.compute_splitting_resistance(cfg, v) for v in V]) / 1e6
Rt = np.array([mm.compute_total_resistance(cfg, v)[0] for v in V]) / 1e6

fig, ax = plt.subplots(figsize=(8.2, 5.0))
ax.semilogy(V, Rc, lw=2, label="R_crush = 2.5·σc·h·D·f(V)")
ax.semilogy(V, Rb, lw=2, label="R_bend = 0.7·σf·h²·L_b·(1+0.1V)")
ax.semilogy(V, Rs, lw=2, ls="--", label="R_split = 1.5·σt·h·D·g(D/L_b)")
ax.semilogy(V, Rt, lw=2.6, color="k",
            label="R_total = 0.7/0.1/0.2 · (crush,bend,split) blend")
for x, txt in ((0.5 * Vc, "0.5·Vc = %.2f m/s\nclassifier: crushing→other" % (0.5 * Vc)),
               (2.0 * Vc, "2.0·Vc = %.2f m/s\nclassifier: →bending" % (2.0 * Vc))):
    ax.axvline(x, color="tab:red", lw=1.2, ls=":")
    ax.text(x + 0.05, 1.2, txt, fontsize=8, color="tab:red", rotation=90, va="bottom")
ax.axvspan(0, 0.5 * Vc, color="tab:blue", alpha=0.06)
ax.axvspan(0.5 * Vc, 2.0 * Vc, color="tab:orange", alpha=0.06)
ax.axvspan(2.0 * Vc, 5.0, color="tab:green", alpha=0.06)
ax.annotate("crossover R_bend = min(R_crush) needs V ≈ %.0f m/s\n(far outside the 0–5 m/s window)"
            % b1["V_needed_for_bend_to_reach_crush_min_m_s"],
            xy=(4.2, 7.2), xytext=(1.5, 250), fontsize=8,
            arrowprops=dict(arrowstyle="->", lw=1))
ax.set_xlabel("ice drift velocity V [m/s]")
ax.set_ylabel("resistance [MN]")
ax.set_ylim(1, 400)
ax.set_title("Report 11557 / C5–C6: the 'mixed mode' is a fixed weight blend,\n"
             "and mode selection is the hardcoded 0.5·Vc / 2·Vc branch")
ax.grid(alpha=0.3, which="both")
ax.legend(fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIGS / "fig1_resistance_modes.png", dpi=150)
plt.close(fig)

# ---------------- Fig 2: claimed verdict vs measured deviation
labels = ["C1 repose\n(10% band)", "C4 V_c\n(<30%)", "C5 Lindqvist\n(<20%)", "C8 energy\n(<5%)"]
measured = [b1["C1_band_to_reported_range_ratio"][1], b1["C4_deviation_pct"],
            b1["C5_deviation_pct_vs_reference"], b1["C8_abs_change_over_KE_1m_s_pct"]]
thresh = [10.0, 30.0, 20.0, 5.0]
fig, ax = plt.subplots(figsize=(8.2, 4.6))
x = np.arange(len(labels))
bars = ax.bar(x - 0.2, measured, 0.4, label="measured deviation (report's own numbers)", color="tab:red")
ax.bar(x + 0.2, thresh, 0.4, label="declared threshold", color="tab:blue")
ax.set_yscale("log")
for xi, mv in zip(x, measured):
    ax.text(xi - 0.2, mv * 1.15, ("%.1f×" % mv) if mv < 100 else ("%.0f×" % mv),
            ha="center", fontsize=8, color="tab:red")
ax.set_xticks(x, labels)
ax.set_ylabel("relative deviation over threshold [% of threshold, log]")
ax.set_title("All four rows are labelled PASS in section 3 of the report;\n"
             "every one of them exceeds its own threshold")
ax.legend(fontsize=8)
ax.grid(alpha=0.3, axis="y", which="both")
fig.tight_layout()
fig.savefig(FIGS / "fig2_pass_vs_threshold.png", dpi=150)
plt.close(fig)

# ---------------- Fig 3: "Timco reference" is the model's own formula
rho = np.linspace(200, 4500, 400)
Vc_of_rho = 0.1 * np.sqrt(cfg.sigma_f / (rho * cfg.h))
fig, ax = plt.subplots(figsize=(8.2, 4.4))
ax.plot(rho, Vc_of_rho, lw=2, label="0.1·√(σf/(ρ·h))  (one closed form, two labels)")
ax.plot([917], [Vc], "o", ms=8, color="tab:red")
ax.annotate("ρ_ice = 917 → V = %.3f m/s\ncalled 'V_c_timco' in the report" % Vc,
            xy=(917, Vc), xytext=(1250, 3.4), fontsize=8,
            arrowprops=dict(arrowstyle="->"))
ax.plot([b1["rho_needed_for_reported_Vc_model"]], [1.3], "s", ms=8, color="tab:purple")
ax.annotate("ρ ≈ %.0f kg/m³ (not ice) → V = 1.3 m/s\ncalled 'V_c_model'"
            % b1["rho_needed_for_reported_Vc_model"],
            xy=(b1["rho_needed_for_reported_Vc_model"], 1.3), xytext=(2300, 1.0), fontsize=8,
            arrowprops=dict(arrowstyle="->"))
ax.axhline(2.763, ls=":", color="tab:red", lw=1)
ax.set_xlabel("density substituted into the same formula [kg/m³]")
ax.set_ylabel("V_c [m/s]")
ax.set_title("C4's 53% 'error vs Timco' is one formula compared with itself:\n"
             "the reference is compute_critical_velocity(config)")
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(FIGS / "fig3_vc_circularity.png", dpi=150)
plt.close(fig)

print(json.dumps({f.name: f.stat().st_size for f in sorted(FIGS.glob("*.png"))},
                 ensure_ascii=False, indent=2))