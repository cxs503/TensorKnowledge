#!/usr/bin/env python3
"""wp-459-04 figures: reviewer-side parity + sensitivity, no hand-copied numbers
(every reported value is read from verify_results.json / platform_probe.json,
which are themselves produced by the two scripts in this directory)."""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
V = json.load(open(os.path.join(HERE, "verify_results.json")))
P = json.load(open(os.path.join(HERE, "platform_probe.json")))

SEALED = [  # (Fr, R_anchor, C_TM_anchor, R_platform, dev, R_opt) — transcribed once from report 3
    (0.10, 11.6, 0.00344, 20.1, 73.3, 11.2), (0.12, 15.8, 0.00325, 29.3, 85.9, 15.3),
    (0.14, 20.7, 0.00315, 40.6, 95.8, 20.1), (0.16, 26.8, 0.00311, 54.0, 102.0, 25.9),
    (0.18, 34.2, 0.00314, 69.8, 104.1, 33.2), (0.20, 43.5, 0.00324, 88.0, 102.2, 42.2),
    (0.22, 55.3, 0.00340, 111.8, 102.2, 53.6), (0.24, 70.1, 0.00362, 139.6, 99.0, 68.0),
    (0.25, 78.9, 0.00376, 155.0, 96.4, 76.5), (0.26, 88.8, 0.00391, 171.6, 93.3, 86.1),
    (0.27, 99.8, 0.00407, 189.3, 89.7, 96.8), (0.28, 112.1, 0.00425, 208.1, 85.7, 108.7),
    (0.30, 141.0, 0.00466, 249.5, 77.0, 136.8),
]
RHO_M, S_M, G, L_M = 998.2, 9.4376, 9.81, 7.2786

fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.0))

# --- panel 1: parity reported vs recomputed R_TM = C_TM*0.5 rho S V^2 --------
ax = axes[0]
x = [r[1] for r in SEALED]
y = [r[2] * 0.5 * RHO_M * S_M * (r[0] * (G * L_M) ** 0.5) ** 2 for r in SEALED]
ax.plot([10, 160], [10, 160], "k--", lw=1, label="1:1")
ax.scatter(x, y, c="#1f77b4", zorder=3, label="13 sealed points")
CHK = {c["id"]: c for c in V["checks"]}
for fr, xa, _c, _p, _d, _o in SEALED:
    if abs(fr - 0.26) < 1e-9:
        ax.annotate(f"Fr=0.26: {xa} N vs {[round(v, 1) for v in y if abs(v - xa) < 3][0]} N",
                    (xa, y[-4]), textcoords="offset points", xytext=(-75, 18), fontsize=8)
ax.set_xlabel("reported R_TM anchor [N] (report §③)")
ax.set_ylabel("recomputed C_TM·½ρSV² [N]")
ax.set_title(f"(a) sealed table internal consistency\nworst dev {CHK['P1']['recomputed']:.3f}% (tolerance {CHK['P1']['tolerance_pct']}%)", fontsize=10)
ax.legend(fontsize=8, loc="upper left")
ax.grid(alpha=0.3)

# --- panel 2: anchor sensitivity to the scale-conversion form ---------------
ax = axes[1]
forms = V["derived"]["anchor_forms_design_point"]
labels = ["A: C_F only\n(as written in §②)", "B: (1+k)=1.15", "C: (1+k)+ΔC_F",
          "live platform\nmodel call", "platform value\nquoted in §③"]
vals = [forms["A_plain_3D (as stated in report 2: C_TM = C_TS - C_FS + C_FM)"]["R_TM_N"],
        forms["B_with_(1+k)"]["R_TM_N"],
        forms["C_with_(1+k)_and_dCF"]["R_TM_N"],
        P["derived"]["model_R_TM_N_as_declared"],
        171.6]
colors = ["#1f77b4", "#1f77b4", "#1f77b4", "#ff7f0e", "#d62728"]
ax.bar(range(len(vals)), vals, color=colors)
ax.axhline(88.8, color="k", ls="--", lw=1, label="sealed anchor 88.8 N")
ax.axhspan(88.8 * 0.85, 88.8 * 1.15, color="green", alpha=0.10, label="±15% band")
for i, v in enumerate(vals):
    ax.annotate(f"{v:.1f}", (i, v), ha="center", va="bottom", fontsize=8)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, fontsize=7.5)
ax.set_ylabel("R_TM at Fr = 0.26 [N]")
ax.set_title("(b) same library R_T(24 kn)=1850 kN,\nfive conversion conventions", fontsize=10)
ax.legend(fontsize=8)
ax.grid(axis="y", alpha=0.3)

# --- panel 3: full-scale numbers, report vs live platform ------------------
ax = axes[2]
d = P["derived"]
names = ["library KCS\n(quoted §⑥)", "LIVE 24 kn\n(this review)", "report: platform\n§⑥", "report: simplified\n§⑥"]
vals3 = [d["library_ship_R_T_kN"], d["ship_R_T_kN_as_declared"],
         d["report_ship_platform_kN"], d["report_ship_simplified_kN"]]
bars = ax.bar(range(4), vals3, color=["#2ca02c", "#ff7f0e", "#d62728", "#8c564b"])
for i, v in enumerate(vals3):
    ax.annotate(f"{v:,.0f} kN", (i, v), ha="center", va="bottom", fontsize=8)
ax.set_xticks(range(4))
ax.set_xticklabels(names, fontsize=7.5)
ax.set_ylabel("R_T full scale at 24 kn [kN]")
ax.set_title("(c) totals at 24 kn: live API reproduces\nneither 4536 kN nor 7407 kN", fontsize=10)
ax.grid(axis="y", alpha=0.3)

fig.suptitle("wp-459-04 independent review of report 459 (EX-1 v2 KCS task book): reproduction of quoted numbers",
             fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.95])
out = os.path.join(HERE, "fig_wp45904_review.png")
fig.savefig(out, dpi=150)
print("wrote", out)
