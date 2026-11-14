#!/usr/bin/env python3
"""wp-5716-04 check engine: every reviewed number is recomputed here from the
report text only.  NOT committed (single-PR <=10 files); the package ships the
numbers it produces, each with its inputs and closed-form formula."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path("/root/tp-agent/work/m20865")
PKG = ROOT / "docs/kf/wp-5716-04"
SRC = PKG / "source_5716.md"
UPSTREAM = ROOT / "docs/kf/wp-5716-01/kf_result.json"

SOURCE = SRC.read_text(encoding="utf-8")
LINES = SOURCE.splitlines()
SHA = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
CHARS = len(SOURCE)
BYTES = len(SOURCE.encode("utf-8"))
REG = json.loads(UPSTREAM.read_text(encoding="utf-8"))
REG_HASH = REG["provenance"]["source_hash"].split(":")[1]
PLATFORM = json.loads((ROOT / "work/m20865/wp5716/platform_5716.json").read_text(encoding="utf-8"))

TOL_ARITH = 3.0
TOL_PLATFORM = 15.0
KN = 0.514444

VERDICT_HELP = {
    "reproduced": "closed-form recomputation from disclosed numbers matches the claim within 3%",
    "self_consistent": "boolean/closing claim; an independent recount or closure check confirms it",
    "contradicted": "independent recomputation or an in-report cross-reference disagrees beyond tolerance",
    "gap": "the report relies on a quantity or census it never discloses; the gap is measured",
    "withheld": "not recomputable from the disclosed text; recorded as unknown, never as pass",
}


def locator(anchor: str):
    n = SOURCE.count(anchor)
    assert n == 1, f"anchor not unique ({n}): {anchor!r}"
    idx = SOURCE[: SOURCE.index(anchor)].count("\n")
    return idx + 1, LINES[idx].strip()


def rel_dev(claimed, recomputed):
    return abs(recomputed - claimed) / abs(claimed) * 100.0


# ---------------------------------------------------------------- case inputs
L, B, T = 190.0, 30.0, 11.5
CB_DECL, CB_STATED = 0.82, 0.82007
DWT_T, DWT_OVER_DISP = 45000.0, 0.8167
RHO_SEA = 1.025
V_SERVICE = 13.0
ROUTE_NM = 684.1
T_D1_H, T_C3_H = 54.5, 63.3
T_D1_ALT_H, T_C3_ALT_H = 54.4, 68.2
E_C3_KWH = 203388.0
ICE_FRAC = 0.27
V_DESIGN_KN, R_ICE_KN = 4.50, 464.7
WALL_SEC, WALL_SEC_ALT = 50.7, 41.5
BETA_THEORY, BETA_DEV_PCT = 0.2874, 75.8
UTIL_20Y, UTIL_CORR_STATED = 67.58, 12.4
A2_SKILL, A2_RMSE, A2_REF_RMSE = 0.505, 0.1145, 0.1444

disp_t = DWT_T / DWT_OVER_DISP
nabla = disp_t / RHO_SEA
lbt = L * B * T
cb_calc = nabla / lbt
rho_implied = disp_t / (CB_STATED * lbt)
cb_fw = disp_t / lbt
cb_resid = abs(CB_STATED - CB_DECL) / CB_DECL * 100.0

energy_per_h = E_C3_KWH / T_C3_H
v_d1 = ROUTE_NM / T_D1_H
v_c3 = ROUTE_NM / T_C3_H
v_c3_alt = ROUTE_NM / T_C3_ALT_H
p_ice_kw = R_ICE_KN * 1000.0 * (V_DESIGN_KN * KN) / 1000.0
v_ow_from_time = (v_c3 - ICE_FRAC * V_DESIGN_KN) / (1.0 - ICE_FRAC)
d_ice_b = ICE_FRAC * ROUTE_NM
t_ice_b = d_ice_b / V_DESIGN_KN
t_ow_b = (ROUTE_NM - d_ice_b) / v_ow_from_time
t_total_b = t_ice_b + t_ow_b
t_ice_a = ICE_FRAC * T_C3_H
d_ice_a = t_ice_a * V_DESIGN_KN
frac_time_a = t_ice_a / T_C3_H * 100.0
frac_dist_a = d_ice_a / ROUTE_NM * 100.0
e_ice = ICE_FRAC * E_C3_KWH
t_ice_c = e_ice / p_ice_kw
frac_time_c = t_ice_c / T_C3_H * 100.0

skill_linear = 1.0 - A2_RMSE / A2_REF_RMSE
skill_murphy = 1.0 - (A2_RMSE / A2_REF_RMSE) ** 2

beta_b2 = BETA_THEORY * (1.0 + BETA_DEV_PCT / 100.0)
ratio_beta = beta_b2 / BETA_THEORY
util_corr = UTIL_20Y / ratio_beta ** 3
m_implied = math.log(UTIL_20Y / UTIL_CORR_STATED) / math.log(ratio_beta)

c3_gap_pct = abs(T_C3_ALT_H - T_C3_H) / T_C3_H * 100.0
d1_gap_pct = abs(T_D1_ALT_H - T_D1_H) / T_D1_H * 100.0
wall_gap_pct = abs(WALL_SEC_ALT - WALL_SEC) / WALL_SEC * 100.0
fig_declared = 7
fig_recorded = len(PLATFORM.get("figures") or [])
fig_gap_pct = (fig_declared - fig_recorded) / fig_declared * 100.0
disc_declared, disc_enumerated = 7, 4
disc_gap_pct = (disc_declared - disc_enumerated) / disc_declared * 100.0
detail_declared, detail_disclosed = 3, 2
detail_gap_pct = (detail_declared - detail_disclosed) / detail_declared * 100.0

checks = []


def add(cid, topic, title, *, anchor, inputs, formula, verdict, dev_kind,
        claimed=None, recomputed=None, dev=None, note="", extra=None):
    line, quote = locator(anchor) if anchor else (None, None)
    rec = {
        "id": cid, "topic": topic, "title": title, "anchor": anchor,
        "inputs": inputs, "formula": formula,
        "claimed": claimed, "recomputed": recomputed,
        "rel_dev_pct": None if dev is None else round(dev, 6),
        "dev_kind": dev_kind, "verdict": verdict,
        "under_3pct": None if dev is None else dev < TOL_ARITH,
        "under_15pct": None if dev is None else dev < TOL_PLATFORM,
        "note": note, "quote": quote, "line": line,
    }
    assert verdict in VERDICT_HELP, verdict
    # the stored deviation must follow from the stored (rounded) numbers alone
    if (dev is not None and isinstance(claimed, (int, float))
            and isinstance(recomputed, (int, float)) and claimed != 0):
        d = rel_dev(claimed, recomputed)
        rec["rel_dev_pct"] = round(d, 6)
        rec["under_3pct"] = d < TOL_ARITH
        rec["under_15pct"] = d < TOL_PLATFORM
    if extra:
        rec.update(extra)
    checks.append(rec)


add("R01", "geometry",
    "Declaration-level Cb inversion: deadweight ratio -> displacement -> volume -> block coefficient",
    anchor="反算 Cb=0.82007",
    inputs={"DWT_t": DWT_T, "displacement_over_DWT": DWT_OVER_DISP, "rho_t_per_m3": RHO_SEA,
            "L_m": L, "B_m": B, "T_m": T, "Cb_declared": CB_DECL},
    formula="Cb = (DWT / 0.8167) / rho / (L*B*T)",
    claimed=CB_STATED, recomputed=round(cb_calc, 7), dev=rel_dev(CB_STATED, cb_calc),
    verdict="reproduced", dev_kind="recompute_vs_claim",
    note=(f"displacement {disp_t:.2f} t -> volume {nabla:.2f} m3 -> Cb {cb_calc:.6f}. "
          f"The stated 0.82007 implies rho = {rho_implied:.6f} t/m3 (sea water 1.025); against the "
          f"declared Cb=0.82 the residual is {cb_resid:.3e} %, which is the 8.5e-5 the report quotes."))

add("R02", "geometry",
    "Hull-form ratios L/B and B/T from the declared main dimensions",
    anchor="L/B=6.333、B/T=2.609",
    inputs={"L_m": L, "B_m": B, "T_m": T},
    formula="L/B ; B/T",
    claimed={"L/B": 6.333, "B/T": 2.609},
    recomputed={"L/B": round(L / B, 4), "B/T": round(B / T, 4)},
    dev=max(rel_dev(6.333, L / B), rel_dev(2.609, B / T)),
    verdict="reproduced", dev_kind="recompute_vs_claim",
    note="Both ratios close on the declared dimensions; the 3-decimal rounding in the report is exact.")

add("R03", "gate-integrity",
    "G01 (Cb within 2%) is certifiable only under an undeclared sea-water density",
    anchor="L1 船型几何自洽 (Cb = ∇/(L·B·T), 2% 容差)",
    inputs={"DWT_t": DWT_T, "displacement_over_DWT": DWT_OVER_DISP, "L*B*T_m3": lbt,
            "rho_literal_t_per_m3": 1.0, "Cb_declared": CB_DECL, "gate_tolerance_pct": 2.0,
            "rho_implied_t_per_m3": round(rho_implied, 6)},
    formula="Cb(rho=1.0) = (DWT/0.8167)/(1.0*L*B*T) ; dev = |Cb-Cb_declared|/Cb_declared",
    claimed=CB_DECL, recomputed=round(cb_fw, 6), dev=rel_dev(CB_DECL, cb_fw),
    verdict="contradicted", dev_kind="reading_sensitivity",
    note=("The report writes Cb = nabla/(L*B*T) but states no density. With rho=1.025 G01 passes (R01); "
          f"with the equally literal reading '0.8167 already gives the volume in m3' (rho=1.0) Cb = "
          f"{cb_fw:.6f}, i.e. {rel_dev(CB_DECL, cb_fw):.2f}% off the declared 0.82 - OUTSIDE the gate's own "
          "2% tolerance, so G01 would FAIL. The PASS is conditional on an assumption the gate does not cite."),
    extra={"gate_id": "G01-GEOM-CB", "gate_tolerance_pct": 2.0})

add("R04", "a2-forecast",
    "A2 skill 0.505 is not reproducible from the two RMSEs the same bullet discloses",
    anchor="72 h 技能（vs 持续性）0.505",
    inputs={"skill_claimed": A2_SKILL, "rmse_a2_m": A2_RMSE, "rmse_reference_m": A2_REF_RMSE},
    formula="skill_linear = 1 - RMSE_A2/RMSE_ref ; skill_murphy = 1 - (RMSE_A2/RMSE_ref)^2",
    claimed=A2_SKILL, recomputed={"linear": round(skill_linear, 4), "murphy": round(skill_murphy, 4)},
    verdict="withheld", dev_kind="none",
    note=("Under the two standard RMSE-skill definitions the disclosed pair (0.1145 m vs 0.1444 m) gives "
          f"{skill_linear:.4f} / {skill_murphy:.4f}, neither of which is 0.505. The definition (reference "
          "climatology? lead-time window? persistence?) is not disclosed, so G03's headline number is "
          "unverifiable - unknown, not pass. It is the only quantitative support quoted for G03."),
    extra={"skill_definitions_tried": {"linear": round(skill_linear, 4), "murphy": round(skill_murphy, 4)}})

add("R05", "a2-forecast",
    "A2 mass-conservation error is stated twice and both statements are machine zero",
    anchor="质量误差 0.0e+00",
    inputs={"stated_section3": 0.0, "stated_section6": 2.6e-14},
    formula="compare the two statements of the same quantity",
    claimed=0.0, recomputed=2.6e-14,
    verdict="self_consistent", dev_kind="closure",
    note="0.0e+00 (section 3) and 2.6e-14 (section 6) are the same number at double precision.")

add("R06", "a2-forecast",
    "A2->D1 verification coverage closes with its complement",
    anchor="A2→D1：冰量守恒 2.6e-14",
    inputs={"verified_fraction_pct": 20.4},
    formula="climate-filled = 100 - verified",
    claimed=20.4, recomputed=20.4, dev=0.0,
    verdict="self_consistent", dev_kind="closure",
    note=("Section 5.7 says the A2 window covers 20.4% of the D1 domain with the rest climate-filled: the "
          "complement is 79.6%, i.e. ~4/5 of the routed domain is NOT verified by the forecast. The "
          "headline in section 3 reads as coverage, which over-reads it."),
    extra={"climate_filled_pct": 79.6})

add("R07", "contract",
    "Conservative-remap mass defect quoted identically in sections 3 and 6",
    anchor="冰量守恒 2.6e-14",
    inputs={"stated_section3": 2.6e-14, "stated_section6": 2.6e-14},
    formula="|sum(a*h)_out - sum(a*h)_in| / sum(a*h)_in",
    claimed=2.6e-14, recomputed=2.6e-14, dev=0.0,
    verdict="self_consistent", dev_kind="closure",
    note="Identical to the last digit in both places; the defect is at double-precision noise level.")

add("R08", "contract",
    "Coordinate-orientation probe value 5.3e-05 cannot be rebuilt from the report",
    anchor="方向探针 5.3e-05",
    inputs={"stated_probe": 5.3e-05},
    formula="probe = |d(field)/d(lat) - analytic slope| / analytic slope (grid spacing / latitude band not disclosed)",
    claimed=5.3e-05,
    verdict="withheld", dev_kind="none",
    note=("No grid spacing, latitude band or denominator is disclosed, so the probe can be neither "
          "recomputed nor bounded. G05's PASS rests on a quoted but non-reproducible number: recorded as "
          "unknown, not as pass."))

add("R09", "route",
    "Route-length identity between D1 and C3, and the mean speeds they imply",
    anchor="主航线 684.1 nm / 54.5 h",
    inputs={"route_nm_D1": ROUTE_NM, "route_nm_C3": ROUTE_NM, "t_D1_h": T_D1_H, "t_C3_h": T_C3_H},
    formula="v = d/t ; identity d_D1 == d_C3",
    claimed=ROUTE_NM, recomputed=ROUTE_NM, dev=0.0,
    verdict="reproduced", dev_kind="cross_reference",
    note=(f"D1 and C3 quote the same 684.1 nm (no-go 0 nm), so the chain is consistent in distance. "
          f"Implied whole-voyage mean speeds: D1 {v_d1:.3f} kn, C3 {v_c3:.3f} kn (spread "
          f"{rel_dev(v_d1, v_c3):.2f}%), against a 13 kn service speed."),
    extra={"v_D1_kn": round(v_d1, 4), "v_C3_kn": round(v_c3, 4),
           "mean_speed_spread_pct": round(rel_dev(v_d1, v_c3), 4)})

add("R10", "speed-profile",
    "C3 energy/time closure and the open-water speed implied by the time reading",
    anchor="C3：总航程 684.1 nm / 63.3 h / 203388 kWh",
    inputs={"route_nm": ROUTE_NM, "t_h": T_C3_H, "energy_kwh": E_C3_KWH, "ice_fraction": ICE_FRAC,
            "v_design_kn": V_DESIGN_KN, "v_service_kn": V_SERVICE},
    formula="P_mean = E/t ; v = d/t ; v_ow = (v_mean - f_ice*v_design)/(1 - f_ice)",
    claimed=V_SERVICE, recomputed=round(v_ow_from_time, 4), dev=rel_dev(V_SERVICE, v_ow_from_time),
    verdict="self_consistent", dev_kind="closure",
    note=(f"Mean power {energy_per_h:.1f} kW over 63.3 h; mean speed {v_c3:.4f} kn. Under the time reading "
          f"of 27.0% the implied open-water speed is {v_ow_from_time:.4f} kn vs the 13 kn service speed "
          f"({rel_dev(V_SERVICE, v_ow_from_time):.2f}%), so the energy/time/distance triple closes only if "
          f"'27.0%' means ice TIME. The ice design point draws {p_ice_kw:.1f} kW = "
          f"{p_ice_kw/energy_per_h*100:.1f}% of the mean power."),
    extra={"mean_power_kW": round(energy_per_h, 2), "v_ow_kn": round(v_ow_from_time, 4),
           "P_ice_design_kW": round(p_ice_kw, 2),
           "P_ice_share_of_mean_pct": round(p_ice_kw / energy_per_h * 100, 2)})

add("R11", "speed-profile",
    "'Ice fraction 27.0%' has no denominator: the distance reading is infeasible by ~25%",
    anchor="冰区占比 27.0%",
    inputs={"ice_fraction": ICE_FRAC, "route_nm": ROUTE_NM, "t_total_h": T_C3_H,
            "v_design_kn": V_DESIGN_KN, "R_ice_kN": R_ICE_KN, "energy_kwh": E_C3_KWH,
            "v_ow_kn": round(v_ow_from_time, 4)},
    formula=("time reading: d_ice = f*t*v_design ; distance reading: t = f*d/v_design + (1-f)*d/v_ow ; "
             "energy reading: t_ice = f*E/P_ice"),
    claimed=round(ICE_FRAC * 100.0, 4), recomputed=round(frac_dist_a, 4),
    dev=rel_dev(ICE_FRAC * 100.0, frac_dist_a),
    verdict="contradicted", dev_kind="undefined_denominator",
    note=(f"Three readings. (A) time: t_ice {t_ice_a:.2f} h, ice distance {d_ice_a:.2f} nm = "
          f"{frac_dist_a:.2f}% of the route, open water {v_ow_from_time:.3f} kn -> closes on 63.3 h. "
          f"(B) distance: t = {t_total_b:.2f} h, {(t_total_b/T_C3_H-1)*100:.2f}% over 63.3 h -> infeasible. "
          f"(C) energy: t_ice = {t_ice_c:.2f} h = {frac_time_c:.1f}% of the voyage time, contradicting 27%. "
          "Only (A) closes, and the report must say so."),
    extra={"reading_time": {"t_ice_h": round(t_ice_a, 3), "d_ice_nm": round(d_ice_a, 3),
                            "ice_distance_pct": round(frac_dist_a, 3)},
           "reading_distance": {"t_total_h": round(t_total_b, 3),
                                "excess_over_stated_pct": round((t_total_b / T_C3_H - 1) * 100, 3)},
           "reading_energy": {"t_ice_h": round(t_ice_c, 3), "ice_time_pct": round(frac_time_c, 3)}})

add("R12", "digital-twin",
    "E1 closed-loop errors are honestly declared FAIL against the owner 3% line",
    anchor="E1：闭环误差 F 5.43%",
    inputs={"F_pct": 5.43, "u_pct": 3.01, "R_ice_pct": 3.82, "GM_pct": 0.09,
            "owner_line_pct": TOL_ARITH, "platform_line_pct": TOL_PLATFORM},
    formula="declare FAIL when error > 3%",
    claimed={"F": "否", "u": "否", "R_ice": "否"},
    recomputed={"F": True, "u": True, "R_ice": True, "GM": False},
    verdict="self_consistent", dev_kind="threshold_comparison",
    note=("All three load/speed quantities exceed 3% -> FAIL, exactly as the report's section 6 table says: "
          "no laundering. All four stay under the platform 15% line, so the honest reading is 'inside the "
          "platform band, outside the owner 3% band'. GM (0.09%) passes both."),
    extra={"exceeds_3pct": {"F": True, "u": True, "R_ice": True, "GM": False},
           "all_under_15pct": True, "direction_honest": True})

add("R13", "digital-twin",
    "GM closed-loop error is reported in section 3 but dropped from the section 6 table",
    anchor="闭环误差 F 5.43% / u 3.01% / R_ice 3.82% / GM 0.09%",
    inputs={"quantities_in_section3": 4, "quantities_in_section6": 3, "missing": ["GM"]},
    formula="census: |section3 - section6| / |section3|",
    claimed=3, recomputed=3,
    verdict="gap", dev_kind="census",
    note=("Four E1 quantities are disclosed in section 3; only three appear in the section 6 error table. "
          "The omitted one is the only quantity that passes (GM 0.09%) - an incomplete error table, in the "
          "conservative direction."),
    extra={"census_missing_pct": 25.0})

add("R14", "structure",
    "B2 panel coefficient back-solved from the 75.8% deviation, then the beta-corrected utilisation",
    anchor="B2 板格系数 vs 简支板理论 β",
    inputs={"beta_theory": BETA_THEORY, "deviation_pct": BETA_DEV_PCT, "util_20y": UTIL_20Y,
            "sn_slope_m": 3.0},
    formula="beta_B2 = beta_theory*(1+dev) ; util_corr = util_20y / (beta_B2/beta_theory)^m",
    claimed=UTIL_CORR_STATED, recomputed=round(util_corr, 4), dev=rel_dev(UTIL_CORR_STATED, util_corr),
    verdict="reproduced", dev_kind="recompute_vs_claim",
    note=(f"beta_B2 = {beta_b2:.5f}; stress ratio {ratio_beta:.4f}; Miner damage scales as ratio^3 -> "
          f"{util_corr:.3f} vs the stated 12.4. The arithmetic behind the report's own 'even after the beta "
          "correction it is still 12.4' holds, and either way the 20-year utilisation is >1."),
    extra={"beta_B2": round(beta_b2, 5), "beta_ratio": round(ratio_beta, 5)})

add("R15", "structure",
    "The S-N slope the report silently uses for that correction is never stated",
    anchor="即便按简支 β 修正仍为 12.4",
    inputs={"util_20y": UTIL_20Y, "util_corrected": UTIL_CORR_STATED, "beta_ratio": round(ratio_beta, 5)},
    formula="m = ln(util_20y/util_corrected) / ln(beta_ratio)",
    recomputed=round(m_implied, 4),
    verdict="gap", dev_kind="none",
    note=(f"The two utilisation figures imply an S-N slope m = {m_implied:.4f} (m=3, the usual "
          "steel-in-seawater value), but the report never states the slope, so a reader cannot tell whether "
          "the correction used the same fatigue curve as the 67.58 figure. Section 6 also has no row for "
          "the corrected utilisation."),
    extra={"implied_sn_slope": round(m_implied, 4)})

add("R16", "speed-profile",
    "C3 voyage time is quoted as 63.3 h in section 3 and 68.2 h in the conclusion",
    anchor="航线时间 54.4 h vs 剖面 68.2 h",
    inputs={"t_section3_h": T_C3_H, "t_conclusion_h": T_C3_ALT_H,
            "t_D1_section3_h": T_D1_H, "t_D1_conclusion_h": T_D1_ALT_H},
    formula="dev = |t_alt - t| / t",
    claimed=T_C3_H, recomputed=T_C3_ALT_H, dev=c3_gap_pct,
    verdict="contradicted", dev_kind="cross_reference",
    note=(f"C3: 63.3 h (section 3) vs 68.2 h (conclusion) = {c3_gap_pct:.2f}%; D1: 54.5 h vs 54.4 h = "
          f"{d1_gap_pct:.2f}%. Mean speed follows: {v_c3:.3f} kn vs {v_c3_alt:.3f} kn. Because GAP-INT-07 is "
          "precisely the D1-vs-C3 divergence, quoting two C3 times makes that divergence (40-66% band vs "
          "65.6% headline) ambiguous."),
    extra={"d1_gap_pct": round(d1_gap_pct, 4), "v_C3_alt_kn": round(v_c3_alt, 4),
           "over_3pct": True, "over_15pct": c3_gap_pct > TOL_PLATFORM})

add("R17", "provenance",
    "Total-chain wall clock is quoted twice with an 18% disagreement",
    anchor="总链墙钟约 41.5 s",
    inputs={"section2_s": WALL_SEC, "section5_9_s": WALL_SEC_ALT},
    formula="dev = |t_alt - t| / t",
    claimed=WALL_SEC, recomputed=WALL_SEC_ALT, dev=wall_gap_pct,
    verdict="contradicted", dev_kind="cross_reference",
    note=(f"Section 2 'one command, 50.7 s' vs section 5.9 '{WALL_SEC_ALT} s single core, no GPU' = "
          f"{wall_gap_pct:.2f}%. Only the second is scoped (single core); the first is unscoped, so neither "
          "the machine nor the run is identifiable from the report - a run identity that cannot be pinned "
          "is not evidence."),
    extra={"over_15pct": wall_gap_pct > TOL_PLATFORM})

add("R18", "gate-integrity",
    "Gate-table census: 16 assertions, 16 PASS, acceptance requires >=8",
    anchor="门判据 **16/16 通过**（要求 ≥8）",
    inputs={"rows_in_table": 16, "rows_passing": 16, "requirement": 8},
    formula="count table rows and PASS cells",
    claimed=16, recomputed=16, dev=0.0,
    verdict="reproduced", dev_kind="census",
    note=("The table has exactly 16 rows (G01..G16) and all 16 read PASS. Note the acceptance rule is >=8 of "
          "16, i.e. the gate may formally pass with half its assertions failing; what carries this "
          "acceptance is the 16/16 margin, not the rule."),
    extra={"gate_ids": ["G%02d" % i for i in range(1, 17)], "margin_over_requirement": 8})

add("R19", "anchor",
    "MT Uikku benchmark MAPE 36.23% vs the pre-registered 25% line: honest FAIL",
    anchor="C1 MT Uikku 链 vs Hu&Zhou 2016（MAPE）",
    inputs={"mape_pct": 36.23, "pre_registered_pct": 25.0, "platform_line_pct": TOL_PLATFORM,
            "thin_ice_mape_pct": 55.5},
    formula="FAIL if MAPE > 25%",
    claimed=25.0, recomputed=36.23,
    verdict="self_consistent", dev_kind="threshold_comparison",
    note=("36.23% > 25% -> D01 FAIL, thin-ice band worse (55.5%). Against the platform 15% line it is 2.4x "
          "over, so it is not acceptable as a validated resistance model - and the report says so itself. "
          "Direction correct: no laundering."),
    extra={"over_line_pp": round(36.23 - 25.0, 2),
           "over_platform_line_x": round(36.23 / TOL_PLATFORM, 3), "direction_honest": True})

add("R20", "anchor",
    "D1-vs-C3 in-ice divergence 65.6% sits inside the quoted 40-66% band, 4.4x over the 15% line",
    anchor="D1 vs C3 冰中航速（独立实现）",
    inputs={"stated_pct": 65.6, "band_pct": [40, 66], "line_pct": TOL_PLATFORM},
    formula="40 <= 65.6 <= 66 ; ratio = 65.6/15",
    claimed=65.6, recomputed=65.6,
    verdict="self_consistent", dev_kind="threshold_comparison",
    note=("The headline is consistent with the 40-66% range in the conclusion, i.e. the report does not "
          "cherry-pick the low end. 65.6% is 4.37x the platform 15% line -> D07 FAIL, declared. What cannot "
          "be checked is the divergence itself (both models live in another repository)."),
    extra={"ratio_to_15pct_line": round(65.6 / TOL_PLATFORM, 3), "direction_honest": True})

add("R21", "inventory",
    "Figure inventory: 4 recorded figure objects vs '7 图齐全'",
    anchor="（4 张图见 figures 字段",
    inputs={"figure_records": fig_recorded, "claimed_figures": fig_declared,
            "figure_names": [f.get("name") for f in (PLATFORM.get("figures") or [])]},
    formula="missing = (claimed - recorded)/claimed",
    claimed=fig_declared, recomputed=fig_recorded, dev=fig_gap_pct,
    verdict="contradicted", dev_kind="census",
    note=("The platform record carries 4 figure objects (name+caption only, no bytes: not reviewable). "
          "'7 图齐全' is therefore unsupported for 3 of 7 (42.86%): either three figures were never published "
          "or they exist only inside the campaign artefact directory, which is absent here."),
    extra={"figure_bytes_present": False})

add("R22", "provenance",
    "Source bytes of report 5716 match the hash registered by wp-5716-01",
    anchor=None,
    inputs={"sha256_recomputed": SHA, "sha256_registered": REG_HASH, "chars": CHARS, "bytes_utf8": BYTES},
    formula="sha256(markdown as utf-8)",
    claimed=REG_HASH, recomputed=SHA, dev=0.0,
    verdict="reproduced", dev_kind="recompute_vs_claim",
    note=("Byte-identical: the review is bound to the bytes the 01 package registered, so it cannot be "
          "reviewing a drifted revision. chars 4790 / bytes 8108."))

add("R23", "disclosure",
    "7 disclosure assertions are declared, 4 are enumerated, 2 IDs never appear",
    anchor="16 项门断言 + 7 项披露",
    inputs={"disclosure_declared": disc_declared, "disclosure_enumerated": disc_enumerated,
            "ids_referenced": ["D01-UIKKU-ANCHOR", "D02-PLATE-MINDLIN", "D05",
                               "D06-STRUCTURAL-VERDICT", "D07-SPEED-MODEL-DIVERGENCE"]},
    formula="undisclosed = declared - enumerated",
    claimed=disc_declared, recomputed=disc_enumerated, dev=disc_gap_pct,
    verdict="gap", dev_kind="census",
    note=("Section 2 says assertions.py carries '16 gate assertions + 7 disclosures', but the conclusion "
          "enumerates only 4 (D01, D02, D06, D07). D05 is referenced in 5.5 without a result and 2 "
          "disclosure IDs never appear at all, so whether they passed is unknown - exactly the silent-pass "
          "hole a disclosure set exists to prevent."),
    extra={"undisclosed_pct": round(disc_gap_pct, 2)})

add("R24", "structure",
    "D06 requires three structural details; two are disclosed",
    anchor="三个结构细节 20 年利用率均 ≤1",
    inputs={"details_required": detail_declared, "details_disclosed": detail_disclosed,
            "detail_values": {"plate_panel": UTIL_20Y, "longitudinal_girder": 1.68e-05}},
    formula="undisclosed = required - disclosed",
    claimed=detail_declared, recomputed=detail_disclosed, dev=detail_gap_pct,
    verdict="gap", dev_kind="census",
    note=("The D06 criterion is 'all three structural details <= 1 over 20 years'. Two values are given "
          "(plate panel 67.58, longitudinal girder 1.68e-05); the third detail is never named or valued. "
          "The disclosure verdict FAILs on the plate panel regardless, so this is an inventory gap, not a "
          "verdict flip."),
    extra={"undisclosed_pct": round(detail_gap_pct, 2)})

# --------------------------------------------------------------------- summary
by_verdict = {}
for c in checks:
    by_verdict.setdefault(c["verdict"], []).append(c["id"])
arith = [c for c in checks if c["dev_kind"] == "recompute_vs_claim" and c["rel_dev_pct"] is not None]
# a "document inconsistency" is a contradicted/gap verdict that carries a measured gap
incons = [c for c in checks if c["verdict"] in ("contradicted", "gap") and c["rel_dev_pct"] is not None]
max_arith = max(arith, key=lambda c: c["rel_dev_pct"])
max_incons = max(incons, key=lambda c: c["rel_dev_pct"])

SECTION6 = [
    ("Cb 几何反算 vs 声明值", "Cb inversion vs declared value", 0.0085, "%", "解析几何", True),
    ("A2 复现上游工件（同配置）", "A2 repro of upstream artefact", 0.0, "%", "artifacts/ice_da_forecast_a2/metrics.json", True),
    ("B2 复现上游工件（同输入）", "B2 repro of upstream artefact", 0.0, "%", "artifacts/fatigue_pc6.json", True),
    ("D1 基准场 vs 上游工件", "D1 baseline vs upstream artefact", None, "abs<=1e-9", "artifacts/ice_route_opt/summary.json", True),
    ("A2→D1 冰量守恒", "A2->D1 mass conservation", None, "abs 2.6e-14", "面积加权守恒（解析恒等）", True),
    ("A2→D1 方向探针", "A2->D1 orientation probe", None, "abs 5.3e-05", "解析 m/deg 斜率", True),
    ("E1 冰载荷闭环", "E1 ice-load closed loop", 5.43, "%", "注入真值（闭环）", False),
    ("E1 航速闭环", "E1 speed closed loop", 3.01, "%", "注入真值（闭环）", False),
    ("E1 冰阻力闭环", "E1 ice-resistance closed loop", 3.82, "%", "注入真值（闭环）", False),
    ("C1 MT Uikku 链 vs Hu&Zhou 2016（MAPE）", "C1 MT Uikku MAPE vs Hu&Zhou 2016", 36.23, "%", "实冰实验锚（代理几何、系数已标定）", False),
    ("B2 板格系数 vs 简支板理论 β", "B2 panel coeff vs plate theory beta", 75.8, "%", "Navier 级数 0.2874", False),
    ("TensorFEM Mindlin Q4 vs 闭式 Mindlin", "TensorFEM Mindlin Q4 vs closed form", 0.211, "%", "tensorfem.plate 闭式解", True),
    ("D1 vs C3 冰中航速（独立实现）", "D1 vs C3 in-ice speed (independent)", 65.6, "%", "两套生产模型互比", False),
]
section6 = [{"item": i, "label_en": le, "value": v, "unit": u, "basis": b,
             "declared_under_3pct": d,
             "review_under_3pct": None if v is None else v < TOL_ARITH,
             "review_under_15pct": None if v is None else v < TOL_PLATFORM}
            for i, le, v, u, b, d in SECTION6]

summary = {
    "n_checks": len(checks),
    "by_verdict": {k: {"n": len(v), "ids": v} for k, v in by_verdict.items()},
    "n_numeric": len([c for c in checks if c["rel_dev_pct"] is not None]),
    "arithmetic_checks": {"n": len(arith), "ids": [c["id"] for c in arith],
                          "max_rel_dev_pct": max_arith["rel_dev_pct"], "max_id": max_arith["id"],
                          "all_under_3pct": all(c["rel_dev_pct"] < TOL_ARITH for c in arith),
                          "all_under_15pct": all(c["rel_dev_pct"] < TOL_PLATFORM for c in arith)},
    "document_inconsistencies": {"n": len(incons), "ids": [c["id"] for c in incons],
                                 "max_rel_dev_pct": max_incons["rel_dev_pct"],
                                 "max_id": max_incons["id"],
                                 "ids_over_3pct": [c["id"] for c in incons
                                                   if c["rel_dev_pct"] >= TOL_ARITH]},
    "honest_fails_confirmed": [c["id"] for c in checks if c.get("direction_honest")],
    "withheld_ids": by_verdict.get("withheld", []),
    "gap_ids": by_verdict.get("gap", []),
}
assert sum(summary["by_verdict"][k]["n"] for k in summary["by_verdict"]) == len(checks)
assert len(arith) + len(incons) <= len(checks)

recompute = {
    "package_id": "wp-5716-04",
    "task_type": "04-independent-review",
    "report_id": "5716",
    "method": {
        "what": "independent recomputation from the published report text only",
        "inputs_allowed": "numbers disclosed in report 5716 markdown + the platform record's figure inventory",
        "inputs_forbidden": "campaign artefacts (absent in this worktree); the upstream -01 package is used "
                            "only as the provenance anchor (registered source hash)",
        "verdict_semantics": VERDICT_HELP,
        "dev_kind_semantics": {
            "recompute_vs_claim": "my closed-form recomputation vs the number the report states",
            "closure": "a derived quantity that must close on another disclosed quantity",
            "cross_reference": "relative gap between two statements of the same quantity inside the report",
            "census": "counted inventory (figures, disclosure IDs, structural details) vs what is claimed",
            "undefined_denominator": "the claim admits several readings that do not agree",
            "reading_sensitivity": "a gate result that flips under an equally literal reading",
            "threshold_comparison": "claim vs a pre-registered / owner / platform threshold (no recompute)",
        },
    },
    "tolerance": {
        "arithmetic_tolerance_pct": TOL_ARITH,
        "platform_line_pct": TOL_PLATFORM,
        "note": "3% is applied to recompute-vs-claim arithmetic; the physical lines the report owns "
                "(25% MAPE, 15% divergence, <=1 utilisation) are audited as claim direction, not re-derived",
    },
    "source": {"uri": "tensor://reports/5716", "field": "markdown", "sha256_recomputed": SHA,
               "sha256_registered": REG_HASH, "hash_matches": SHA == REG_HASH,
               "chars": CHARS, "bytes_utf8": BYTES, "line_count": len(LINES),
               "registered_by": "docs/kf/wp-5716-01/kf_result.json", "snapshot_file": "source_5716.md"},
    "platform_record": {"id": PLATFORM.get("id"), "title": PLATFORM.get("title"),
                        "scenario_key": PLATFORM.get("scenario_key"),
                        "mission_id": PLATFORM.get("mission_id"), "status": PLATFORM.get("status"),
                        "created_at": PLATFORM.get("created_at"),
                        "figure_records": fig_recorded,
                        "figure_names": [f.get("name") for f in (PLATFORM.get("figures") or [])],
                        "figure_bytes_present": False},
    "checks": checks,
    "summary": summary,
    "report_section6_claimed_errors": section6,
    "independence_limitations": [
        "Campaign artefacts are absent from this worktree (wp-5716-01 resolved 5 of 18 references): the "
        "chain itself, the gate code and the upstream reproductions were NOT re-executed.",
        "Figures are metadata only (name + caption, no bytes) -> no figure in report 5716 was audited.",
        "Both ice-speed models (D1 vectorised chain, C3 thrust-balance) live in other repositories; the "
        "40-66% divergence is audited for internal consistency only.",
        "The A2 forecast, E1 twin and C1 resistance chain are not re-derived: their numbers are audited for "
        "closure and declaration, not for physical correctness.",
        "Single reviewer (agent/m20865); not double-blind, and no second pair of eyes on the verdict calls.",
    ],
    "artifacts_absent": ["artifacts/campaign_ice_nav/campaign_acceptance.json",
                         "docs/campaign/ice_nav_campaign_report.md",
                         "artifacts/campaign_ice_nav/figures/*.png",
                         "backend/tests/test_campaign_ice_nav.py",
                         "TensorFEM / TensorDEM / TensorPhysics checkouts"],
}

if __name__ == "__main__":
    print(json.dumps(summary, ensure_ascii=False, indent=2))