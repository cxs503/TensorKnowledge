#!/usr/bin/env python3
"""wp-459-04 independent re-computation harness (report_id=459).

Reviewer-side only: re-derive every numeric claim of the source report from the
principal particulars that literally appear in that report, then compare with the
quoted numbers. Nothing is taken from the producer's tooling; the only inputs are
numbers quoted in the markdown, transcribed below.

Run:  python3 docs/wp-459-04/verify_numbers.py
Writes verify_results.json next to this script and prints a table.
"""
from __future__ import annotations

import json
import math
import os

RHO_M = 998.2      # kg/m3, fresh water 20 C        (report 2, key settings)
NU_M = 1.0040e-06  # m2/s                          (report 2)
RHO_S = 1025.9     # kg/m3, sea water 15 C         (report 2)
NU_S = 1.1883e-06  # m2/s                          (report 2)
G = 9.81
KN = 1.943844      # m/s -> kn

L_S, B_S, T_S = 230.000, 32.200, 10.800
VOL_S, S_S = 52030.0, 9424.0
LAM = 31.6

# report 3 speed matrix: (Fr, V_m, V_S_kn, Re_M)
MATRIX = [
    (0.10, 0.8449, 9.23, 6.125e06),
    (0.12, 1.0138, 11.08, 7.350e06),
    (0.14, 1.1828, 12.92, 8.575e06),
    (0.16, 1.3518, 14.77, 9.800e06),
    (0.18, 1.5207, 16.62, 1.102e07),
    (0.20, 1.6897, 18.46, 1.225e07),
    (0.22, 1.8587, 20.31, 1.347e07),
    (0.24, 2.0277, 22.16, 1.470e07),
    (0.25, 2.1121, 23.08, 1.531e07),
    (0.26, 2.1966, 24.00, 1.592e07),
    (0.27, 2.2811, 24.93, 1.654e07),
    (0.28, 2.3656, 25.85, 1.715e07),
    (0.30, 2.5346, 27.70, 1.837e07),
]

# report 3 sealed table: (Fr, R_TM_anchor_N, C_TM_anchor, R_TM_platform_N, platform_dev_pct, R_TM_opt_N)
SEALED = [
    (0.10, 11.6, 0.00344, 20.1, 73.3, 11.2),
    (0.12, 15.8, 0.00325, 29.3, 85.9, 15.3),
    (0.14, 20.7, 0.00315, 40.6, 95.8, 20.1),
    (0.16, 26.8, 0.00311, 54.0, 102.0, 25.9),
    (0.18, 34.2, 0.00314, 69.8, 104.1, 33.2),
    (0.20, 43.5, 0.00324, 88.0, 102.2, 42.2),
    (0.22, 55.3, 0.00340, 111.8, 102.2, 53.6),
    (0.24, 70.1, 0.00362, 139.6, 99.0, 68.0),
    (0.25, 78.9, 0.00376, 155.0, 96.4, 76.5),
    (0.26, 88.8, 0.00391, 171.6, 93.3, 86.1),
    (0.27, 99.8, 0.00407, 189.3, 89.7, 96.8),
    (0.28, 112.1, 0.00425, 208.1, 85.7, 108.7),
    (0.30, 141.0, 0.00466, 249.5, 77.0, 136.8),
]

# report 6 quoted rows we can re-derive
Q = {
    "lambda": 31.5995,
    "C_B": 0.6505,
    "L_over_B_model": 7.1430,
    "B_over_T_model": 2.9815,
    "Fr_24kn": 0.25997,
    "R_ship24_platform_kN": 4536.0,
    "R_ship24_library_kN": 1850.0,
    "R_ship24_simplified_kN": 7407.0,
    "R_F_library_kN": 610.0,
    "R_F_ittc57_kN": 1015.0,
    "C_R_platform_design": 4.1e-03,
    "C_W_library_ship": 5.3e-04,
    "form_factor": 1.15,
    "dCF": 4.0e-04,
    "cw_fit_residual": 1.24e-06,
}

OUT = {"checks": [], "derived": {}, "summary": {}}


def cf_ittc57(re):
    return 0.075 / (math.log10(re) - 2.0) ** 2


def q(coefficient, v, rho=RHO_M, s=None):
    """0.5*rho*S*v^2 for coefficient = 1 -> N"""
    return 0.5 * rho * (S_S if s is None else s) * v * v


def chk(cid, claim, reported, recomputed, tol_pct, unit="", note=""):
    rel = None
    ok = None
    if reported is not None and recomputed not in (None, 0):
        rel = (reported - recomputed) / recomputed * 100.0
        ok = abs(rel) <= tol_pct
    OUT["checks"].append({
        "id": cid, "claim": claim, "reported": reported, "recomputed": recomputed,
        "rel_dev_pct": None if rel is None else round(rel, 4), "tolerance_pct": tol_pct,
        "pass": ok, "unit": unit, "note": note,
    })
    return ok


def chk_bound(cid, claim, measured, bound, unit="", note=""):
    """Residual/rounded-quantity check: measured worst deviation must sit inside bound."""
    ok = measured is not None and measured <= bound
    OUT["checks"].append({
        "id": cid, "claim": claim, "reported": bound, "recomputed": measured,
        "rel_dev_pct": None, "tolerance_pct": bound, "pass": ok,
        "unit": unit, "note": note, "mode": "bound",
    })
    return ok


# 1) geometry / scale ------------------------------------------------------
L_m, B_m, T_m = L_S / LAM, B_S / LAM, T_S / LAM
vol_m, S_m = VOL_S / LAM ** 3, S_S / LAM ** 2
cb_s = VOL_S / (L_S * B_S * T_S)
OUT["derived"].update({
    "L_m": round(L_m, 4), "B_m": round(B_m, 4), "T_m": round(T_m, 4),
    "vol_m": round(vol_m, 4), "S_m": round(S_m, 4),
    "mass_m_kg": round(RHO_M * vol_m, 1), "cb_ship": round(cb_s, 4),
})
chk("G1", "lambda = L_pp/L_m (recomputed vs quoted)", Q["lambda"], round(L_S / 7.2786, 4), 0.01, "-")
chk("G2", "C_B = grad/(L*B*T) ship", Q["C_B"], round(cb_s, 4), 0.1, "-")
chk("G3", "B_m = B/lambda", 1.0190, round(B_m, 4), 0.01, "m")
chk("G4", "T_m = T/lambda", 0.3418, round(T_m, 4), 0.01, "m")
chk("G5", "grad_m = grad/lambda^3", 1.6489, round(vol_m, 4), 0.01, "m3")
chk("G6", "S_m = S/lambda^2", 9.4376, round(S_m, 4), 0.01, "m2")
chk("G7", "m_m = rho_m*grad_m", 1645.9, round(RHO_M * vol_m, 1), 0.05, "kg")
chk("G8", "L/B model", Q["L_over_B_model"], round(L_m / B_m, 4), 0.01, "-")
chk("G9", "B/T model", Q["B_over_T_model"], round(B_m / T_m, 4), 0.01, "-")

# 2) speed matrix ----------------------------------------------------------
w_vm = w_vs = w_re = 0.0
mono = True
prev = -1.0
for fr, vm, vs, re in MATRIX:
    vm_rec = fr * math.sqrt(G * L_m)
    vs_rec = vm_rec * math.sqrt(LAM) * KN
    re_rec = vm_rec * L_m / NU_M
    w_vm = max(w_vm, abs(vm - vm_rec) / vm_rec * 100)
    w_vs = max(w_vs, abs(vs - vs_rec) / vs_rec * 100)
    w_re = max(w_re, abs(re - re_rec) / re_rec * 100)
    if vm <= prev:
        mono = False
    prev = vm
chk_bound("M1", "worst |dV_m| over 13 points (V_m = Fr sqrt(g L_m)) [%]", round(w_vm, 5), 0.05, "%",
          "4-decimal rounding of V_m alone gives <=0.012%; report quotes residual 4.76e-05 m/s")
chk_bound("M2", "worst |dV_S| (V_S = V_m sqrt(lambda)) [%]", round(w_vs, 5), 0.3, "%",
          "2-decimal rounding of knot column gives <=0.05%")
chk_bound("M3", "worst |dRe_M| (Re = V_m L_m/nu_m) [%]", round(w_re, 5), 1.0, "%",
          "4-sig-fig rounding of Re column gives <=0.05%")
OUT["summary"].update({
    "matrix_monotone_Vm_13pt": mono,
    "Re_min": MATRIX[0][3], "Re_min_gt_5e6": MATRIX[0][3] > 5e6,
    "V_m_max": max(m[1] for m in MATRIX), "V_m_max_lt_12_ms": max(m[1] for m in MATRIX) < 12.0,
    "n_points": len(MATRIX),
    "has_design_point_0p26": any(abs(m[0] - 0.26) < 1e-9 for m in MATRIX),
})
fr24 = (24.0 / KN) / math.sqrt(G * L_S)
chk("M4", "Fr at 24 kn full scale", Q["Fr_24kn"], round(fr24, 5), 0.05, "-")

# 3) sealed table internal consistency ------------------------------------
w_anchor = 0.0
for fr, rtm, ctm, rplat, dev, ropt in SEALED:
    vm = fr * math.sqrt(G * L_m)
    rec = ctm * q(1.0, vm, RHO_M, S_m)
    w_anchor = max(w_anchor, abs(rtm - rec) / rec * 100)
chk_bound("P1", "worst |R_TM - C_TM*0.5*rho_m*S_m*V_m^2| over 13 points [%]", round(w_anchor, 5), 0.5, "%",
          "C_TM given to 3 s.f. -> <=0.5% quantisation")
w_dev = max(abs(dev - (rplat / rtm * 100 - 100)) for fr, rtm, ctm, rplat, dev, ropt in SEALED)
chk_bound("P2", "worst |dev - (R_platform/R_anchor-1)| over 13 points [pp]", round(w_dev, 5), 0.6, "pp",
          "0.1 N rounding of R_TM moves the ratio by <=0.4 pp")
w_opt = max(abs(ropt - 0.97 * rtm) / (0.97 * rtm) * 100 for fr, rtm, ctm, rplat, dev, ropt in SEALED)
chk_bound("P3", "worst |R_opt - 0.97*R_anchor| (declared 3% saving) [%]", round(w_opt, 5), 0.5, "%",
          "0.1 N rounding")

# 4) anchor derivation from library R_T (ship 24 kn = 1850 kN) -----------
vs24 = 24.0 / KN
qp_ship = q(1.0, vs24, RHO_S, S_S)          # N per unit C_T (ship)
cf_m = cf_ittc57(2.1966 * L_m / NU_M)      # Re_M at Fr 0.26 (from matrix)
cf_s = cf_ittc57(vs24 * L_S / NU_S)
out = {"cf_m_design": round(cf_m, 6), "cf_s_24kn": round(cf_s, 6),
       "Re_S_24kn": round(vs24 * L_S / NU_S, 0), "q_ship_per_unit_C": round(qp_ship, 0)}
FK, dcf = Q["form_factor"], Q["dCF"]   # FK = (1+k) = 1.15 as declared in report 2
c_ts_lib = Q["R_ship24_library_kN"] * 1e3 / qp_ship
out["C_TS_library_24kn"] = round(c_ts_lib, 6)
forms = {
    "A_plain_3D (as stated in report 2: C_TM = C_TS - C_FS + C_FM)": c_ts_lib - cf_s + cf_m,
    "B_with_(1+k)": c_ts_lib + FK * (cf_m - cf_s),
    "C_with_(1+k)_and_dCF": c_ts_lib + FK * (cf_m - cf_s) - dcf,
    "D_naive_Froude (C_TM = C_TS)": c_ts_lib,
}
for name, ctm in forms.items():
    out[name] = {"C_TM": round(ctm, 6), "R_TM_N": round(ctm * q(1.0, 2.1966, RHO_M, S_m), 2)}
OUT["derived"]["anchor_forms_design_point"] = out
chk("P4", "sealed C_TM(0.26)=0.00391 vs form A (plain 3-D)", 0.00391, out["A_plain_3D (as stated in report 2: C_TM = C_TS - C_FS + C_FM)"]["C_TM"], 0.5, "-",
    "PASS => the sealed anchor is reproducible only with the unit-form-factor form")
spread = {n: out[n]["R_TM_N"] for n in forms}
OUT["summary"]["anchor_R_TM_spread_N"] = spread
rmin, rmax = min(spread.values()), max(spread.values())
OUT["summary"]["anchor_spread_pct_of_sealed"] = [round((rmin / 88.8 - 1) * 100, 2), round((rmax / 88.8 - 1) * 100, 2)]

# 5) platform full-scale and simplified numbers --------------------------
c_tm_plat = 171.6 / q(1.0, 2.1966, RHO_M, S_m)
out["C_TM_platform_design"] = round(c_tm_plat, 6)
r_ship_plat_plain = c_tm_plat - (cf_m - cf_s)
out["R_ship_platform_plain_kN"] = round(r_ship_plat_plain * qp_ship / 1e3, 1)
out["R_ship_platform_k"] = round((c_tm_plat + FK * (cf_m - cf_s) - dcf) * qp_ship / 1e3, 1)
OUT["derived"]["platform_full_scale_reconstruction"] = out
chk("X1", "platform ship 24 kn = 4536 kN reproducible as C_TS = C_TM-(C_FM-C_FS)", Q["R_ship24_platform_kN"],
    out["R_ship_platform_plain_kN"], 1.0, "kN", "no (1+k), no dC_F")
chk("X2", "same number with declared (1+k)=1.15 & dC_F=4e-4", Q["R_ship24_platform_kN"],
    out["R_ship_platform_k"], 1.0, "kN", "would change the quoted +145.2%")
chk("X3", "platform/6 dev vs library: +145.2%", 145.2, round(Q["R_ship24_platform_kN"] / Q["R_ship24_library_kN"] * 100 - 100, 2), 0.1, "%")
chk("X4", "simplified/6 dev vs library: +300.4%", 300.4, round(Q["R_ship24_simplified_kN"] / Q["R_ship24_library_kN"] * 100 - 100, 2), 0.1, "%")

# 6) library friction self-consistency claim ------------------------------
rf_ittc = cf_s * qp_ship / 1e3
chk("F1", "R_F(24 kn) by ITTC-57 with S=9424 m2", Q["R_F_ittc57_kN"], round(rf_ittc, 1), 1.0, "kN")
chk("F2", "library R_F vs ITTC-57: -39.9%", -39.9, round((Q["R_F_library_kN"] - rf_ittc) / rf_ittc * 100, 2), 1.0, "%")

# 7) C_R / C_W cross-check ------------------------------------------------
cr_plat = c_tm_plat - FK * cf_m
cr_plat_dcf = c_tm_plat - FK * cf_m - dcf
OUT["derived"]["C_R_platform_design"] = {"with_dCF": round(cr_plat_dcf, 6), "without_dCF": round(cr_plat, 6)}
chk("W1", "platform C_R(0.26) ~ 4.1e-03 (report 5)", Q["C_R_platform_design"],
    round(cr_plat_dcf, 6), 6.0, "-", "with declared (1+k), dC_F")
cw_ship = c_ts_lib - FK * cf_s - dcf
OUT["derived"]["C_W_library_ship"] = round(cw_ship, 6)
chk("W2", "library-derived C_W ~ 5.3e-04 (report 5)", Q["C_W_library_ship"], round(cw_ship, 6), 3.0, "-")

# 8) budget / schedule arithmetic ----------------------------------------
a_budget, b_budget = 47.8, 65.8
a_days, b_days = 72, 117
chk("B1", "budget gap B-A = 18.0 wan", 18.0, round(b_budget - a_budget, 2), 0.1, "wan")
chk("B2", "schedule gap B-A = 45 d (baseline model manufacture)", 45, b_days - a_days, 0.0, "d")

# summary
checks = OUT["checks"]
OUT["summary"].update({
    "n_checks": len(checks),
    "n_pass": sum(1 for c in checks if c["pass"] is True),
    "n_fail": sum(1 for c in checks if c["pass"] is False),
    "n_not_computable": sum(1 for c in checks if c["pass"] is None),
    "failed_ids": [c["id"] for c in checks if c["pass"] is False],
})

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "verify_results.json"), "w") as fh:
        json.dump(OUT, fh, indent=2, ensure_ascii=False)
    print(f"{'id':4s} {'reported':>12s} {'recomputed':>12s} {'dev%':>9s}  pass  claim")
    for c in checks:
        rp = "" if c["reported"] is None else f"{c['reported']}"
        rc = "" if c["recomputed"] is None else f"{c['recomputed']}"
        dv = "" if c["rel_dev_pct"] is None else f"{c['rel_dev_pct']}"
        print(f"{c['id']:4s} {rp:>12s} {rc:>12s} {dv:>9s}  {str(c['pass']):5s} {c['claim']}")
    s = OUT["summary"]
    print(f"\n{ s['n_pass'] }/{s['n_checks']} checks pass, {s['n_fail']} fail, {s['n_not_computable']} not computable; failed={s['failed_ids']}")
    print("anchor R_TM forms @Fr0.26 [N]:", s["anchor_R_TM_spread_N"])
