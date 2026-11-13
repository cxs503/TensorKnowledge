"""Review figure for wp-7473-04: force-injection measurement vs the report's fit.

Data source: work/wp-7473-04/probe_2026-11-12.json (own measurement, module
API re-run on 2026-11-12), never hand-typed.
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = "work/wp-7473-04"
probe = json.load(open(f"{HERE}/probe_2026-11-12.json", encoding="utf-8"))

rows = probe["remeasure"]["truth_table"] + probe["remeasure"]["campaign_and_A_prime"]
guo = [(r["s_plus"], r["dU_dt_over_a"]) for r in rows if r["scheme"] == "guo_sp" and r["nu"] >= 0.002]
guo.sort()
camp = [r for r in rows if r["scheme"] == "guo_sp" and r["nu"] < 0.002]
camp.sort(key=lambda r: r["s_plus"])

fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=130)
sx = [s for s, _ in guo]
sy = [v for _, v in guo]
ax.plot(sx, sy, "o-", color="#1f4e79", label="measured guo_sp (own re-run, nu>=0.002)")
ax.plot(sx, [2.11 - 1.045 * s for s in sx], "--", color="#c00000",
        label="report's fit 2.11 - 1.045 s+")
ax.plot([r["s_plus"] for r in camp], [r["dU_dt_over_a"] for r in camp], "D", color="#2e7d32",
        markersize=9, label="measured guo_sp at nu=2.22e-3 (A' row)")
cx = probe["campaign_identity"]["s_plus_campaign"]
cy = [r["dU_dt_over_a"] for r in camp if abs(r["nu"] - 4.4444e-4) < 1e-6]
ax.plot([cx], cy, "*", color="black", markersize=15,
        label=f"measured guo_sp at campaign nu=4.44e-4 (s+={cx:.4f}) = {cy[0]:.4f} a")
ax.axhline(1.0, color="0.5", lw=0.8)
ax.set_xlabel("s+ = 1/(0.5 + 3 nu)")
ax.set_ylabel("(dU/dt)/a")
ax.set_title("Review check: guo_sp force injection, independent re-measurement")
ax.set_xlim(0.85, 2.05)
ax.grid(alpha=0.3)
ax.legend(fontsize=7.5, loc="upper right")
fig.tight_layout()
fig.savefig(f"{HERE}/fig_review_force_injection.png")
print("wrote", f"{HERE}/fig_review_force_injection.png")
print("guo points", guo)
print("camp", [(r["nu"], r["tau_plus"], r["s_plus"], r["dU_dt_over_a"]) for r in camp])