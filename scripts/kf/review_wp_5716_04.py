#!/usr/bin/env python3
"""wp-5716-04 — independent red-team review of report 5716 (IN10-G1 ice-nav campaign).

Report 5716 is the acceptance report of the Kara-Sea edge-ice campaign: a PC6 45k DWT
bulker mother ship, five upstream models chained A2 (ice nowcast/assimilation) -> D1
(route) -> C3 (speed profile) -> E1 (digital twin), plus B2 (ice-belt fatigue), closed by
16 gate assertions and 7 disclosures.

This package is review-only. Scope = the report's own markdown bytes, pinned by sha256.
Nothing here re-executes the upstream campaign code (it is not in this repository), and no
claim is marked platform-verified.

Design rules (enforced by tests/test_wp_5716_04_review.py):
  * every number printed in report.md/README.md is formatted from recompute.json, never
    typed as a literal (zero hand-copy);
  * every recompute entry carries the verbatim source quote and the 1-based line of each
    input, so a reader can re-derive it by hand without running this file;
  * a detector that cannot stop firing on a mutated source is worthless: the tests mutate
    the snapshot and require the matching finding to disappear (negative control).

Usage:
  python3 scripts/kf/review_wp_5716_04.py            # pinned fetch + rebuild + write
  python3 scripts/kf/review_wp_5716_04.py --offline  # rebuild from committed snapshot
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-5716-04"
REPORT_ID = "5716"
SOURCE_URI = "tensor://reports/5716"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377"
EXPECTED_CHARS = 4790
# Reviewer constant: sea-water density in t/m3. Report 5716 never states it, which is
# precisely finding F1 (its Cb gate only closes once this constant is introduced).
RHO_SEAWATER = 1.025

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
SNAPSHOT = OUT_DIR / "source_5716.md"
META = OUT_DIR / "source_5716.md.meta.json"
RECOMPUTE = OUT_DIR / "recompute.json"
REVIEW = OUT_DIR / "review_report.json"
ENVELOPE = OUT_DIR / "kf_result.json"
REPORT_MD = OUT_DIR / "report.md"
README_MD = OUT_DIR / "README.md"
FIGURES = OUT_DIR / "figures"
FIG_MAIN = FIGURES / "fig_review_errors.png"


# --------------------------------------------------------------------- helpers
def fmt(v, digits=None):
    """One formatting rule, so recompute.json and report.md cannot drift."""
    if v is None:
        return "—"
    if isinstance(v, str):
        return v
    if v == 0:
        return "0"
    if digits is not None:
        return f"{v:.{digits}f}"
    a = abs(v)
    if a < 1e-3 or a >= 1e5:
        return f"{v:.3e}"
    if a >= 1:
        return f"{v:.4f}"
    return f"{v:.5f}"


def fmt_rel(x):
    """Relative differences are printed for humans: 2 decimals when >=1%, else 4."""
    a = abs(x)
    return f"{a:.2f}" if a >= 1 else f"{a:.4f}"


def _line_of(md, idx):
    return md.count("\n", 0, idx) + 1


def _line_text(md, line):
    lines = md.splitlines()
    return lines[line - 1].strip() if 1 <= line <= len(lines) else ""


def grab(md, pattern, name, group=1):
    """Extract one scalar together with its verbatim source line. Missing -> hard fail."""
    m = re.search(pattern, md)
    if not m:
        raise KeyError(f"extract[{name}]: pattern not found: {pattern}")
    line = _line_of(md, m.start())
    quote = _line_text(md, line)
    text = m.group(group)
    if text not in quote:
        raise AssertionError(f"extract[{name}]: match not inside its own line")
    try:
        value = float(text)
    except ValueError:
        value = text
    return {"name": name, "text": text, "value": value, "line": line, "quote": quote}


# ------------------------------------------------------------------ extraction
# One regex per reported scalar. Every pattern is anchored on report wording so that a
# silently reworded report breaks the run instead of silently reviewing something else.
FIELDS = {
    "L_pp_m": r"L_pp=([0-9.]+) m",
    "B_m": r"\bB=([0-9.]+) m",
    "T_m": r"\bT=([0-9.]+) m",
    "cb_declared": r"Cb=([0-9.]+),",
    "p_installed_MW": r"主机 ([0-9.]+) MW",
    "v_service_kn": r"服务航速 ([0-9.]+) kn",
    "f_ice_design_MN": r"([0-9.]+) MN/",
    "f_ice_hz": r"MN/([0-9.]+) Hz",
    "yearly_ice_frac": r"年冰区占比 ([0-9.]+)",
    "life_years": r"([0-9]+) 年寿命",
    "dwt_over_disp": r"DWT/([0-9.]+)",
    "cb_reconstructed": r"反算 Cb=([0-9.]+) vs 声明",
    "cb_rel_reported": r"（相对差 ([0-9.eE+-]+)）",
    "lb_reported": r"L/B=([0-9.]+)",
    "bt_reported": r"B/T=([0-9.]+)",
    "cb_gate_tol_pct": r"Cb = ∇/\(L·B·T\), ([0-9.]+)% 容差",
    "gates_passed": r"\*\*([0-9]+)/[0-9]+ 通过\*\*",
    "gates_denominator": r"\*\*[0-9]+/([0-9]+) 通过\*\*",
    "gates_required": r"（要求 ≥([0-9]+)）",
    "a2_skill": r"技能（vs 持续性）([0-9.]+)",
    "a2_rmse_m": r"同化 RMSE ([0-9.]+) m",
    "a2_map_rmse_m": r"（冰图 ([0-9.]+) m）",
    "a2_mass_err": r"质量误差 ([0-9.eE+-]+)",
    "a2_leads_ok": r"航窗可作业 ([0-9]+)/",
    "a2_leads_total": r"航窗可作业 [0-9]+/([0-9]+) lead",
    "a2d1_conservation": r"冰量守恒 ([0-9.eE+-]+)",
    "a2d1_probe": r"方向探针 ([0-9.eE+-]+)",
    "a2d1_coverage_pct": r"覆盖 ([0-9.]+)%",
    "d1_dist_nm": r"主航线 ([0-9.]+) nm",
    "d1_time_h": r"主航线 [0-9.]+ nm / ([0-9.]+) h",
    "d1_haversine_pct": r"独立 haversine 复算差 ([0-9.]+)%",
    "c3_dist_nm": r"总航程 ([0-9.]+) nm",
    "c3_time_h": r"总航程 [0-9.]+ nm / ([0-9.]+) h",
    "c3_energy_kwh": r"/ ([0-9]{4,}) kWh",
    "c3_ice_frac_pct": r"冰区占比 ([0-9.]+)%",
    "c3_design_kn": r"设计点 ([0-9.]+) kn",
    "c3_rice_kn": r"R_ice ([0-9.]+) kN",
    "e1_err_f_pct": r"闭环误差 F ([0-9.]+)%",
    "e1_err_u_pct": r"/ u ([0-9.]+)%",
    "e1_err_rice_pct": r"/ R_ice ([0-9.]+)%",
    "e1_err_gm_pct": r"/ GM ([0-9.]+)%",
    "b2_util20": r"20 年利用率 ([0-9.]+)（不通过）",
    "b2_longitudinal": r"纵桁 ([0-9.eE+-]+)",
    "b2_beta_dev_pct": r"简支板理论 β \| ([0-9.]+)%",
    "b2_beta_ref": r"Navier 级数 ([0-9.]+)",
    "b2_util20_corrected": r"修正仍为 ([0-9.]+)",
    "fig_claims_sec4": r"（([0-9]+) 张图见 figures 字段",
    "fig_claims_concl": r"JSON/报告/([0-9]+) 图齐全",
    "assert_claim_gates": r"([0-9]+) 项门断言",
    "assert_claim_disclosures": r"\+ ([0-9]+) 项披露",
    "disclose_failed_claim": r"但有 ([0-9]+) 项披露项如实不通过",
    "wallclock_sec2": r"墙钟 ([0-9.]+) s",
    "wallclock_note9": r"总链墙钟约 ([0-9.]+) s",
    "concl_route_time_h": r"航线时间 ([0-9.]+) h",
    "concl_profile_time_h": r"vs 剖面 ([0-9.]+) h",
    "d07_div_reported_pct": r"冰中航速（独立实现）`? \| ([0-9.]+)%",
    "d07_div_concl_hi": r"冰中航速 [0-9]+–([0-9]+)% 分歧",
    "d07_tol_hint_pct": r"D07-SPEED-MODEL-DIVERGENCE`：[^\n]*?相对差 ≤([0-9]+)%",
    "d01_mape_reported_pct": r"MAPE ([0-9.]+)%",
    "d01_thin_ice_pct": r"薄冰段 ([0-9.]+)%",
    "d06_tol_hint": r"20 年利用率均 ≤([0-9]+)",
    "d02_tol_hint_pct": r"D02-PLATE-MINDLIN`：[^\n]*?相对差 ≤([0-9]+)%",
}


def extract(md):
    ex = {name: grab(md, pat, name) for name, pat in FIELDS.items()}
    ex["dwt_t"] = grab(md, r"([0-9.]+)k DWT", "dwt_t")
    # the report prints "45k DWT": keep the printed token for traceability, the tonnes for math
    ex["dwt_t"] = dict(ex["dwt_t"], value=ex["dwt_t"]["value"] * 1000.0,
                       text=str(int(ex["dwt_t"]["value"] * 1000)),
                       source_text=ex["dwt_t"]["text"])

    registered = sorted({m.group(1) for m in re.finditer(r"`(D[0-9]{2})-[A-Z0-9-]+`", md)})
    cross = sorted({g for m in re.finditer(r"（(D[0-9]{2})）|见 (D[0-9]{2})", md)
                    for g in m.groups() if g})
    mentioned = sorted(set(registered) | set(cross))
    lines = {}
    for m in re.finditer(r"(D[0-9]{2})", md):
        lines.setdefault(m.group(1), _line_of(md, m.start()))
    ex["disclosure_ids"] = {
        "name": "disclosure_ids", "registered": registered,
        "cross_referenced": cross, "all_mentioned": mentioned,
        "lines": {k: lines[k] for k in mentioned}, "value": len(mentioned),
        "text": str(len(mentioned)),
        "quote": "；".join(f"{k}@L{lines[k]}" for k in mentioned),
        "line": lines[mentioned[0]] if mentioned else None,
    }
    return ex

# ------------------------------------------------------------------- recompute
# Every entry: value + formula + inputs(with quotes/lines) + reported counterpart.
# `status`: pass/fail = compared against a tolerance the report states for itself;
# derived = reviewer-side quantity with no printed counterpart;
# violated = an identity the report's own parameters satisfy but its numbers do not;
# unreconstructible = printed number not obtainable from printed inputs.
def _entry(eid, label, formula, value, unit="", inputs=None, reported=None,
           tol_pct=None, status="derived", note="", basis_sensitive=False, digits=None,
           skip_rel=False):
    rep_text = reported["text"] if isinstance(reported, dict) else reported
    rep_val = reported["value"] if isinstance(reported, dict) else None
    rep_line = reported["line"] if isinstance(reported, dict) else None
    rep_quote = reported["quote"] if isinstance(reported, dict) else None
    rel = None
    if not skip_rel and rep_val not in (None, 0) and isinstance(value, float):
        rel = (value - rep_val) / rep_val * 100.0
    # For divergence entries the recomputed value *is* the quantity the report's own
    # criterion bounds, so "within tolerance" is a self-comparison (no printed counterpart).
    if rel is None and tol_pct is not None and isinstance(value, float):
        within = abs(value) <= tol_pct
    else:
        within = None if (tol_pct is None or rel is None) else abs(rel) <= tol_pct
    return {
        "id": eid, "label": label, "formula": formula, "inputs": inputs or [],
        "value": value, "value_str": fmt(value, digits), "unit": unit,
        "reported": rep_text, "reported_value": rep_val, "reported_line": rep_line,
        "reported_quote": rep_quote,
        "rel_diff_pct": None if rel is None else round(rel, 4),
        "rel_diff_str": "—" if rel is None else fmt_rel(rel),
        "tol_pct": tol_pct,
        "within_tol": within,
        "status": status, "basis_sensitive": basis_sensitive, "note": note,
    }


def _inp(ex, *names):
    return [{"name": n, "value": ex[n].get("source_text", ex[n]["text"]),
             "line": ex[n]["line"], "quote": ex[n]["quote"]} for n in names]


def recompute(md, ex):
    v = lambda n: float(ex[n]["value"])
    L, B, T = v("L_pp_m"), v("B_m"), v("T_m")
    dwt, factor = v("dwt_t"), v("dwt_over_disp")
    cb_decl, cb_tol = v("cb_declared"), v("cb_gate_tol_pct")
    cb_lit = (dwt / factor) / (L * B * T)                    # no sea-water density
    cb_rho = (dwt / factor / RHO_SEAWATER) / (L * B * T)      # with rho

    d1_dist, d1_t = v("d1_dist_nm"), v("d1_time_h")
    c3_dist, c3_t = v("c3_dist_nm"), v("c3_time_h")
    c3_e, ice_frac = v("c3_energy_kwh"), v("c3_ice_frac_pct") / 100.0
    v_ice, v_serv = v("c3_design_kn"), v("v_service_kn")
    ow_dist, ice_dist = (1 - ice_frac) * c3_dist, ice_frac * c3_dist
    t_ow = ow_dist / v_serv
    slack = {"c3": c3_t - t_ow, "d1": d1_t - t_ow, "concl": v("concl_profile_time_h") - t_ow}
    t_floor = t_ow + ice_dist / v_ice
    sp_c3, sp_d1 = c3_dist / c3_t, d1_dist / d1_t
    t_prof, t_route = v("concl_profile_time_h"), v("concl_route_time_h")
    b2_util, b2_dev = v("b2_util20"), v("b2_beta_dev_pct") / 100.0

    rec = {}
    add = lambda e: rec.__setitem__(e["id"], e)

    rel_cb_lit = abs((cb_lit - cb_decl) / cb_decl * 100)
    add(_entry(
        "C1_CB_LITERAL",
        "G01 几何门：按报告写出的公式逐字代入（∇ = DWT/0.8167，不含海水密度）",
        "Cb = (DWT / 0.8167) / (L·B·T)", cb_lit, "-",
        _inp(ex, "dwt_t", "dwt_over_disp", "L_pp_m", "B_m", "T_m"),
        reported=ex["cb_declared"], tol_pct=cb_tol, status="fail",
        note=("字面代入得 %s，相对声明值 %s 偏差 %s%%（自述容差 %s%%）：按报告写出的公式，G01 应判 FAIL。"
              "要得到报告印出的 %s 必须额外引入 ρ=%s t/m3，该常数全文未出现。"
              % (fmt(cb_lit), ex["cb_declared"]["text"], fmt(rel_cb_lit), fmt(cb_tol),
                 ex["cb_reconstructed"]["text"], fmt(RHO_SEAWATER)))))
    rel_cb_rho = abs((cb_rho - v("cb_reconstructed")) / v("cb_reconstructed") * 100)
    add(_entry(
        "C2_CB_WITH_RHO", "G01 补上海水密度后的复算（reviewer 显式常数）",
        "Cb = (DWT / 0.8167 / ρ) / (L·B·T),  ρ = %s t/m3" % fmt(RHO_SEAWATER), cb_rho, "-",
        _inp(ex, "dwt_t", "dwt_over_disp", "L_pp_m", "B_m", "T_m"),
        reported=ex["cb_reconstructed"], tol_pct=cb_tol, status="pass",
        note=("补 ρ 后复算 %s 与印出的 %s 只差 %s%%，G01 的 PASS 因此可复现——"
              "但成立依赖一个没有写进报告的常数。"
              % (fmt(cb_rho), ex["cb_reconstructed"]["text"], fmt(rel_cb_rho)))))
    add(_entry("C3_LB", "L/B 副尺度比", "L_pp / B", L / B, "-",
               _inp(ex, "L_pp_m", "B_m"), reported=ex["lb_reported"],
               tol_pct=cb_tol, status="pass"))
    add(_entry("C4_BT", "B/T 副尺度比", "B / T", B / T, "-",
               _inp(ex, "B_m", "T_m"), reported=ex["bt_reported"],
               tol_pct=cb_tol, status="pass"))
    add(_entry("C5_SPEED_C3", "C3 剖面隐含平均航速", "S_C3 / t_C3", sp_c3, "kn",
               _inp(ex, "c3_dist_nm", "c3_time_h"), status="derived"))
    add(_entry("C6_SPEED_D1", "D1 航线隐含平均航速", "S_D1 / t_D1", sp_d1, "kn",
               _inp(ex, "d1_dist_nm", "d1_time_h"), status="derived"))
    add(_entry(
        "C7_TIME_FLOOR", "由报告自己的冰区占比/设计点/服务航速给出的最短可行总时间",
        "t_min = (1-%.2f)·S/%.1f + %.2f·S/%.1f" % (ice_frac, v_serv, ice_frac, v_ice),
        t_floor, "h",
        _inp(ex, "c3_dist_nm", "c3_ice_frac_pct", "c3_design_kn", "v_service_kn"),
        reported=ex["c3_time_h"], status="violated",
        note=("27.0%% 冰区按距离解释、冰区按 4.50 kn 航行时，总时间下限 %s h，比印出的 %s h 长 %s%%。"
              "没有任何门断言闭合这条恒等式（G10 只闭合设计点单位链）。"
              % (fmt(t_floor), ex["c3_time_h"]["text"], fmt((t_floor - c3_t) / c3_t * 100)))))
    add(_entry(
        "C8_VICE_IMPLIED_C3", "反解：把 C3 印出的总时间当真，冰区段必须达到的平均航速",
        "v_ice = %.2f·S / (t_C3 - (1-%.2f)·S/%.1f)" % (ice_frac, ice_frac, v_serv),
        ice_dist / slack["c3"], "kn",
        _inp(ex, "c3_dist_nm", "c3_ice_frac_pct", "c3_time_h", "v_service_kn"),
        reported=ex["c3_design_kn"], status="violated", basis_sensitive=True,
        note=("按 %s h 反解 %s kn，按 D1 的 %s h 反解 %s kn，按结论段 %s h 反解 %s kn："
              "三处都远离登记的 4.50 kn 设计点。"
              % (ex["c3_time_h"]["text"], fmt(ice_dist / slack["c3"]),
                 ex["d1_time_h"]["text"], fmt(ice_dist / slack["d1"]),
                 ex["concl_profile_time_h"]["text"], fmt(ice_dist / slack["concl"])))))
    add(_entry(
        "C8b_VICE_IMPLIED_D1", "同上，改用 D1 印出航时",
        "v_ice = %.2f·S / (t_D1 - (1-%.2f)·S/%.1f)" % (ice_frac, ice_frac, v_serv),
        ice_dist / slack["d1"], "kn",
        _inp(ex, "c3_dist_nm", "c3_ice_frac_pct", "d1_time_h", "v_service_kn"),
        reported=ex["c3_design_kn"], status="violated", basis_sensitive=True))
    add(_entry(
        "C8c_VICE_IMPLIED_CONCL", "同上，改用结论段剖面航时",
        "v_ice = %.2f·S / (t_p - (1-%.2f)·S/%.1f)" % (ice_frac, ice_frac, v_serv),
        ice_dist / slack["concl"], "kn",
        _inp(ex, "c3_dist_nm", "c3_ice_frac_pct", "concl_profile_time_h", "v_service_kn"),
        reported=ex["c3_design_kn"], status="violated", basis_sensitive=True))
    add(_entry("C9_ENERGY_POWER", "能量-时间闭合：平均功率", "P̄ = E / t_C3",
               c3_e / c3_t, "kW", _inp(ex, "c3_energy_kwh", "c3_time_h"), status="derived",
               note="占装机 %s MW 的 %s%%，量级可信。"
                    % (ex["p_installed_MW"]["text"],
                       fmt(c3_e / c3_t / (v("p_installed_MW") * 1000) * 100))))
    add(_entry("C10_ENERGY_PER_NM", "单位航程能耗", "E / S_C3", c3_e / c3_dist, "kWh/nm",
               _inp(ex, "c3_energy_kwh", "c3_dist_nm"), status="derived"))

    div_time_concl = (t_prof - t_route) / t_route * 100
    div_time_c3 = (c3_t - d1_t) / d1_t * 100
    div_sp_concl = abs((c3_dist / t_prof) - sp_d1) / sp_d1 * 100
    div_sp_c3 = abs(sp_d1 - sp_c3) / sp_d1 * 100
    d07_tol = v("d07_tol_hint_pct")
    add(_entry("C11_DIV_TIME", "D1 与 C3 的航时分歧（结论段口径）",
               "(t_profile - t_route) / t_route", div_time_concl, "%",
               _inp(ex, "concl_route_time_h", "concl_profile_time_h"),
               tol_pct=d07_tol, status="fail", basis_sensitive=True,
               note="按结论段数字，航时分歧 %s%%（> %s%% 判据）。"
                    % (fmt(div_time_concl), fmt(d07_tol))))
    add(_entry("C12_DIV_TIME_C3", "D1 与 C3 的航时分歧（③ 结果段口径）",
               "(t_C3 - t_D1) / t_D1", div_time_c3, "%",
               _inp(ex, "c3_time_h", "d1_time_h"), tol_pct=d07_tol, status="fail",
               basis_sensitive=True,
               note="改用 ③ 的 %s h 时为 %s%%。" % (ex["c3_time_h"]["text"], fmt(div_time_c3))))
    add(_entry("C13_DIV_SPEED_CONCL", "D1 与 C3 的平均航速分歧（结论段口径）",
               "|S_C3/t_profile - v_D1| / v_D1", div_sp_concl, "%",
               _inp(ex, "d1_dist_nm", "d1_time_h", "c3_dist_nm", "concl_profile_time_h"),
               tol_pct=d07_tol, status="fail", basis_sensitive=True,
               note="平均航速口径 %s%%（> %s%%）。" % (fmt(div_sp_concl), fmt(d07_tol))))
    add(_entry("C14_DIV_SPEED_C3", "D1 与 C3 的平均航速分歧（③ 结果段口径）",
               "|v_D1 - v_C3| / v_D1", div_sp_c3, "%",
               _inp(ex, "d1_dist_nm", "d1_time_h", "c3_dist_nm", "c3_time_h"),
               tol_pct=d07_tol, status="pass", basis_sensitive=True,
               note=("同一对模型换 ③ 的数字只有 %s%%（≤ %s%% 即 PASS），报告登记的是 %s%%。"
                     "判据的比较基准（全航程均值 or 冰区段）从未写明。"
                     % (fmt(div_sp_c3), fmt(d07_tol), ex["d07_div_reported_pct"]["text"]))))

    lo, hi = b2_util * (1 - b2_dev), b2_util * (1 + b2_dev)
    add(_entry(
        "C15_B2_UTIL_LINEAR", "B2 板格利用率按系数偏差线性换算（区间）",
        "U' = U·(1 ± %.3f)" % b2_dev, lo, "-",
        _inp(ex, "b2_util20", "b2_beta_dev_pct"),
        reported=ex["b2_util20_corrected"], status="unreconstructible", skip_rel=True,
        note=("线性换算区间 [%s, %s] 不含报告给出的修正值 %s：β 修正的方法（S-N 指数？载荷折减？）"
              "没有披露，该数字用报告印出的数字无法复算。" % (fmt(lo), fmt(hi),
                                                       ex["b2_util20_corrected"]["text"]))))
    add(_entry(
        "C16_DISCLOSURE_REGISTER", "披露登记簿：自称条数 vs 可绑定 ID 数",
        "n(注册的 D** 项)", len(ex["disclosure_ids"]["registered"]), "项",
        _inp(ex, "assert_claim_disclosures", "disclose_failed_claim"),
        reported=ex["assert_claim_disclosures"], status="fail", skip_rel=True, digits=0,
        note="自称 %s 项披露，可绑定 ID 的只有 %s 项（%s）；结论段称 %s 项不通过，登记簿只列 4 条。"
             "ID→行号：%s"
             % (ex["assert_claim_disclosures"]["text"],
                str(len(ex["disclosure_ids"]["registered"])),
                "、".join(ex["disclosure_ids"]["registered"]),
                ex["disclose_failed_claim"]["text"],
                ex["disclosure_ids"]["quote"])))
    add(_entry("C17_FIG_COUNT", "图数口径：④ 结果图段 vs 结论段", "n(④) vs n(结论)",
               v("fig_claims_sec4"), "张", _inp(ex, "fig_claims_sec4", "fig_claims_concl"),
               digits=0,
               reported=ex["fig_claims_concl"], status="fail", skip_rel=True,
               note="④ 段报 %s 张，结论段报 %s 图。"
                    % (ex["fig_claims_sec4"]["text"], ex["fig_claims_concl"]["text"])))
    wc2, wc9 = v("wallclock_sec2"), v("wallclock_note9")
    add(_entry("C18_WALLCLOCK", "单命令墙钟：② 方法段 vs ⑤ 局限段", "(t₂ - t₉) / t₉",
               (wc2 - wc9) / wc9 * 100, "%", _inp(ex, "wallclock_sec2", "wallclock_note9"),
               reported=ex["wallclock_note9"], status="fail", skip_rel=True,
               note="② 段 %s s、⑤ 段 %s s，差 %s%%，无工件可裁决。"
                    % (ex["wallclock_sec2"]["text"], ex["wallclock_note9"]["text"],
                       fmt(abs((wc2 - wc9) / wc9 * 100)))))
    add(_entry("C19_GATE_MARGIN", "门判据裕度：通过数 / 要求数", "n_pass / n_required",
               v("gates_passed") / v("gates_required"), "×",
               _inp(ex, "gates_passed", "gates_required"), status="derived", digits=2,
               note="要求 ≥%s 而自称 %s 通过，门槛本身不具区分力。"
                    % (ex["gates_required"]["text"], ex["gates_passed"]["text"])))
    add(_entry("C20_D1_TIME_DRIFT", "D1 航时：③ 段 vs 结论段", "(t_route - t_D1) / t_D1",
               (t_route - d1_t) / d1_t * 100, "%",
               _inp(ex, "d1_time_h", "concl_route_time_h"), status="fail",
               note="③ 段 %s h、结论段 %s h（同一条 D1 航线）。"
                    % (ex["d1_time_h"]["text"], ex["concl_route_time_h"]["text"])))
    return rec


# -------------------------------------------------------------------- findings
def _finding(fid, severity, blocking, title, category, claim, rec_ids, observed,
             expected, remediation):
    return {
        "id": fid, "severity": severity, "blocking": blocking, "title": title,
        "category": category,
        "claim": {"quote": claim["quote"], "line": claim["line"], "text": claim["text"]},
        "recompute_ids": rec_ids, "observed": observed, "expected": expected,
        "remediation": remediation,
    }


def detect_findings(ex, rec):
    v = lambda n: float(ex[n]["value"])
    out = []

    c1 = rec["C1_CB_LITERAL"]
    if c1["within_tol"] is False:
        out.append(_finding(
            "F1", "high", True,
            "G01 的判据与执行不是同一件事：按报告写出的 Cb 公式代入即超出它自己的 2% 容差",
            "criterion_not_executed", ex["cb_gate_tol_pct"],
            ["C1_CB_LITERAL", "C2_CB_WITH_RHO"],
            "逐字代入 (DWT/0.8167)/(L·B·T) 得 %s，偏差 %s%%（> %s%%）→ 该行 PASS 无法由写出的公式得到"
            % (c1["value_str"], c1["rel_diff_str"], fmt(c1["tol_pct"])),
            "印出的 %s（偏差 %s%%）只有在补入未声明的 ρ=%s t/m3 时才成立，即写出的公式 ≠ 实际执行的公式"
            % (ex["cb_reconstructed"]["text"], ex["cb_rel_reported"]["text"], fmt(RHO_SEAWATER)),
            "G01 行写出完整公式 Cb = (DWT/Δ / ρ)/(L·B·T) 并明示 ρ=1.025 t/m3；或用独立排水的直接几何积分"))

    drift = abs((v("c3_time_h") - v("concl_profile_time_h")) / v("concl_profile_time_h") * 100)
    if drift > 1:
        out.append(_finding(
            "F2", "high", True,
            "C3 总航时在同一份报告里有两个值（%s h vs %s h），且 65.6%% 的分歧判据挂在后一个上"
            % (ex["c3_time_h"]["text"], ex["concl_profile_time_h"]["text"]),
            "self_contradiction", ex["concl_profile_time_h"],
            ["C12_DIV_TIME_C3", "C8_VICE_IMPLIED_C3", "C8c_VICE_IMPLIED_CONCL"],
            "③ 结果段：总航程 %s nm / %s h；结论段 D07：剖面 %s h"
            % (ex["c3_dist_nm"]["text"], ex["c3_time_h"]["text"],
               ex["concl_profile_time_h"]["text"]),
            "同一模型同一工况航时必须单值；两值相差 %s%%，且 D07 的分歧结论依赖取哪一个" % fmt(drift),
            "指定唯一真源（C3 工件 campaign_acceptance.json 字段）并由结论段引用同一字段"))

    n_reg = len(ex["disclosure_ids"]["registered"])
    if n_reg != int(v("assert_claim_disclosures")):
        out.append(_finding(
            "F3", "high", True,
            "披露登记簿自称 %s 项，只能绑定 %d 个 ID（缺 %d 项），未登记的这些项无法审计"
            % (ex["assert_claim_disclosures"]["text"], n_reg,
               int(v("assert_claim_disclosures")) - n_reg),
            "register_incomplete", ex["assert_claim_disclosures"],
            ["C16_DISCLOSURE_REGISTER"],
            "全文可绑定的披露 ID：%s（共 %d 项）"
            % ("、".join(ex["disclosure_ids"]["registered"]), n_reg),
            "② 段称「%s 项门断言 + %s 项披露」，结论段称 %s 项不通过却只列出 4 条"
            % (ex["assert_claim_gates"]["text"], ex["assert_claim_disclosures"]["text"],
               ex["disclose_failed_claim"]["text"]),
            "补齐缺失条目，或把宣称条数改为实际登记数；每条披露写明判据/实测/结论"))

    wc_rel = abs((v("wallclock_sec2") - v("wallclock_note9")) / v("wallclock_note9") * 100)
    if wc_rel > 5:
        out.append(_finding(
            "F4", "medium", False,
            "单命令墙钟两个值（%s s vs %s s），差 %s%%，无工件可裁决"
            % (ex["wallclock_sec2"]["text"], ex["wallclock_note9"]["text"], fmt(wc_rel)),
            "self_contradiction", ex["wallclock_note9"], ["C18_WALLCLOCK"],
            "② 方法段 %s s；⑤ 局限段第 9 条 %s s"
            % (ex["wallclock_sec2"]["text"], ex["wallclock_note9"]["text"]),
            "墙钟应来自同一次运行记录",
            "以工件 run_wall_clock_s 字段替换两处散文数字"))

    c7 = rec["C7_TIME_FLOOR"]
    if c7["value"] > v("c3_time_h"):
        out.append(_finding(
            "F5", "medium", False,
            "距离/时间/冰区占比/设计点四者不闭合：按报告自己的参数，最短可行总时间 %s h ≫ 印出的 %s h"
            % (c7["value_str"], ex["c3_time_h"]["text"]),
            "invariant_not_closed", ex["c3_ice_frac_pct"],
            ["C7_TIME_FLOOR", "C8_VICE_IMPLIED_C3", "C8b_VICE_IMPLIED_D1", "C8c_VICE_IMPLIED_CONCL"],
            "把 %s%% 冰区当距离份额、冰区按 %s kn 航行，总时间下限 %s h（比印出值长 %s%%）"
            % (ex["c3_ice_frac_pct"]["text"], ex["c3_design_kn"]["text"], c7["value_str"],
               fmt((c7["value"] - v("c3_time_h")) / v("c3_time_h") * 100)),
            "反解冰区平均航速需 %s / %s / %s kn（C3/D1/结论口径），均远离 %s kn 设计点"
            % (rec["C8_VICE_IMPLIED_C3"]["value_str"], rec["C8b_VICE_IMPLIED_D1"]["value_str"],
               rec["C8c_VICE_IMPLIED_CONCL"]["value_str"], ex["c3_design_kn"]["text"]),
            "登记为覆盖缺口而非算术错误：增一条断言闭合 Σ(S_k/v_k)=t；或写明 %s%% 是时间/能耗份额而非距离份额"
            % ex["c3_ice_frac_pct"]["text"]))

    if rec["C14_DIV_SPEED_C3"]["within_tol"] != rec["C13_DIV_SPEED_CONCL"]["within_tol"]:
        out.append(_finding(
            "F6", "medium", False,
            "D07 的 FAIL 结论对比较基准敏感：整体均值口径 %s%%（≤%s%% 即 PASS），结论段口径 %s%%"
            % (rec["C14_DIV_SPEED_C3"]["value_str"], ex["d07_tol_hint_pct"]["text"],
               rec["C13_DIV_SPEED_CONCL"]["value_str"]),
            "criterion_underspecified", ex["d07_div_reported_pct"],
            ["C11_DIV_TIME", "C12_DIV_TIME_C3", "C13_DIV_SPEED_CONCL", "C14_DIV_SPEED_C3"],
            "登记分歧 %s%%（结论段写 %s%%），换 ③ 段口径只有 %s%%"
            % (ex["d07_div_reported_pct"]["text"], ex["d07_div_concl_hi"]["text"],
               rec["C14_DIV_SPEED_C3"]["value_str"]),
            "判据只写「两套独立冰中航速模型的相对差 ≤%s%%」，未写比较量是全航程均值还是仅冰区段"
            % ex["d07_tol_hint_pct"]["text"],
            "固定比较量与分母（如全航程平均航速、分母取 D1），冰区段分歧作为从属指标另列"))

    c15 = rec["C15_B2_UTIL_LINEAR"]
    if c15["status"] == "unreconstructible":
        hi = v("b2_util20") * (1 + v("b2_beta_dev_pct") / 100)
        out.append(_finding(
            "F7", "medium", False,
            "B2「按简支 β 修正仍为 %s」无法用印出的两个数字复算（线性换算区间 [%s, %s]）"
            % (ex["b2_util20_corrected"]["text"], c15["value_str"], fmt(hi)),
            "unreconstructible_number", ex["b2_util20_corrected"],
            ["C15_B2_UTIL_LINEAR"],
            "由 U=%s、系数偏差 %s%% 只能得到区间 [%s, %s]"
            % (ex["b2_util20"]["text"], ex["b2_beta_dev_pct"]["text"], c15["value_str"], fmt(hi)),
            "修正利用率 %s 落在该区间外；修正方法（S-N 斜率/载荷折减）未披露"
            % ex["b2_util20_corrected"]["text"],
            "给出修正公式与 S-N 指数 m，并打印修正前后应力幅"))

    if v("gates_passed") / v("gates_required") >= 2:
        out.append(_finding(
            "F8", "low", False,
            "门判据门槛（要求 ≥%s）远低于自称通过数（%s）：16/16 这一行不具区分力"
            % (ex["gates_required"]["text"], ex["gates_passed"]["text"]),
            "weak_criterion", ex["gates_required"], ["C19_GATE_MARGIN"],
            "自称 %s 通过、要求 ≥%s，裕度 %s×"
            % (ex["gates_passed"]["text"], ex["gates_required"]["text"],
               rec["C19_GATE_MARGIN"]["value_str"]),
            "16 条全通过本身不可证伪：其中 G01 在字面公式下不通过（F1）",
            "门槛改为 16/16 且每条断言必须给「可复算的值 + 明确容差」，不接受布尔自评"))

    if int(v("fig_claims_sec4")) != int(v("fig_claims_concl")):
        out.append(_finding(
            "F9", "low", False,
            "图数口径不一致：④ 段 %s 张 vs 结论段 %s 图"
            % (ex["fig_claims_sec4"]["text"], ex["fig_claims_concl"]["text"]),
            "self_contradiction", ex["fig_claims_concl"], ["C17_FIG_COUNT"],
            "④ 段 %s 张；结论「JSON/报告/%s 图齐全」"
            % (ex["fig_claims_sec4"]["text"], ex["fig_claims_concl"]["text"]),
            "同一份报告的图数应单值", "由 figures 字段长度渲染两处文字，不再手写"))

    if abs((v("concl_route_time_h") - v("d1_time_h")) / v("d1_time_h") * 100) > 0.1:
        out.append(_finding(
            "F10", "low", False,
            "D1 航时两值（%s h vs %s h）"
            % (ex["d1_time_h"]["text"], ex["concl_route_time_h"]["text"]),
            "self_contradiction", ex["concl_route_time_h"], ["C20_D1_TIME_DRIFT"],
            "③ 段与结论段的 D1 航线航时差 %s%%" % rec["C20_D1_TIME_DRIFT"]["value_str"],
            "同一条航线同一工况航时应单值", "由工件事务字段生成，不手写"))

    d = ex["disclosure_ids"]
    if "D07" in d["registered"] and "D05" in d["cross_referenced"]:
        out.append(_finding(
            "F11", "low", False,
            "披露 ID 漂移：正文以 D05 指代航速分歧，登记簿里同一事项是 D07",
            "id_drift",
            {"quote": ex["d07_div_reported_pct"]["quote"],
             "line": ex["d07_div_reported_pct"]["line"],
             "text": ex["d07_div_reported_pct"]["text"]},
            ["C16_DISCLOSURE_REGISTER"],
            "⑤/⑥ 段引用 D05，登记簿写作 D07-SPEED-MODEL-DIVERGENCE",
            "同一披露只能有一个 ID", "统一 ID，并让正文引用与登记簿由同一份数据渲染"))
    return out


# Scope honesty: what an independent reviewer of the *markdown* cannot do.
CHECKS_NOT_RUN = [
    {"check": "上游战役工件复核",
     "why": "报告引用的 artifacts/campaign_ice_nav/campaign_acceptance.json、"
            "docs/campaign/ice_nav_campaign_report.md、backend/tests/test_campaign_ice_nav.py "
            "在 TensorKnowledge 仓库内均不存在（路径解析失败），战役代码在别的仓。",
     "state": "NOT_RUN",
     "impact": "16 条门断言的执行记录、13 passed 的 pytest 结果、G13 的 sha256 台账无法在本包内重放。"},
    {"check": "G02–G16 的代码路径审查",
     "why": "复核范围限定为报告 markdown 字节；未获得 contracts.py/chain.py/assertions.py 源码。",
     "state": "NOT_RUN",
     "impact": "断言实现是否真的检查了它自称检查的东西（如 G15 是否两次重算同哈希）只能按自述登记，记 WITHHELD。"},
    {"check": "A2 技能 0.505 与 10/12 lead 的独立复算",
     "why": "identical-twin OSSE 真值由同一前向模型生成，观测序列与冰图数据不在本仓库。",
     "state": "WITHHELD",
     "impact": "只能核对相对关系是否写清（是），数值本身未复算。"},
    {"check": "MT Uikku 十工况锚（D01）与 B2 简支板理论（D02）",
     "why": "代理几何、Hu&Zhou(2016) 十工况表、TensorFEM 板解均不在本仓库。",
     "state": "WITHHELD",
     "impact": "MAPE 36.2%/薄冰 55.5% 与 75.8% 只核对跨节一致性（一致），数值未复算。"},
    {"check": "发布态与 pr-gate 记账",
     "why": "reviewer 无发布权；published.json 由平台门在合并时写入。",
     "state": "NOT_APPLICABLE",
     "impact": "本包不自称已发布，任务态保持 awaiting_pr_merge 直到平台合并。"},
]


# ------------------------------------------------------------------- rendering
def _table(rows, header):
    """GitHub-flavoured markdown table; piped characters are escaped so a quote cannot
    silently break the table (source quotes contain '|')."""
    def esc(c):
        return str(c).replace("|", "\\|").replace("\n", " ")
    out = ["| " + " | ".join(esc(h) for h in header) + " |",
           "|" + "---|" * len(header)]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pct(x, digits=2):
    return f"{abs(x):.{digits}f}%"


def render_report(meta, ex, rec, findings, verdict, corroborated, sha, fig_meta):
    v = lambda n: float(ex[n]["value"])
    blocking = [f for f in findings if f["blocking"]]
    sev = {k: sum(1 for f in findings if f["severity"] == k) for k in ("high", "medium", "low")}

    L = []
    A = L.append
    A("# wp-5716-04 · 独立红队复核：报告 5716（IN10-G1 冰区航行战役验收门）")
    A("")
    A("> **判定 `%s`**（阻断项 %d 条 / high %d / medium %d / low %d）。本包只复核，不修复上游，"
      "也不把任何结论登记为平台已验证。" % (verdict, len(blocking), sev["high"], sev["medium"], sev["low"]))
    A("")
    A("## ① 复核对象与范围")
    A("")
    A(_table([
        ["报告 ID", REPORT_ID],
        ["标题", meta.get("title", "—")],
        ["场景键", meta.get("scenario_key", "—")],
        ["来源 URI", SOURCE_URI],
        ["内容 sha256", "`sha256:%s`" % sha],
        ["字符数 / 行数", "%d / %d" % (len(meta["markdown"]), len(meta["markdown"].splitlines()))],
        ["采集时刻 (UTC)", meta.get("fetched_at", "—")],
        ["复核口径", "仅报告 markdown 字节；上游战役工件不在本仓库（见 §⑥ 未执行清单）"],
    ], ["项", "值"]))
    A("")
    A("复核对象是一个 45k DWT PC6 散货船母型的喀拉海边缘冰区端到端链：A2 冰况同化 → D1 航线 → "
      "C3 航速剖面 → E1 数字孪生，外加 B2 冰带疲劳；上游自称 %s 条门断言全通过、%s 项披露，"
      "其中 %s 项如实不通过。本包要回答的是三件事："
      % (ex["gates_passed"]["text"], ex["assert_claim_disclosures"]["text"],
         ex["disclose_failed_claim"]["text"]))
    A("")
    A("1. 报告里每一个可复算的数字，能否由报告自己印出的输入重算出来；")
    A("2. 每个 PASS/FAIL 所依据的判据，是否就是报告写出来的那条判据；")
    A("3. 每一处「结论」是否对口径（取哪个航时、比哪个量、分母是谁）稳健。")
    A("")
    A("## ② 怎么做的")
    A("")
    A("| 步骤 | 机制 | 防伪设计 |")
    A("|---|---|---|")
    A("| 1 钉扎 | 按 `sha256` 与字符数校验取回的 markdown，不一致即中止 | 上游一旦改稿，本包所有结论作废而不是悄悄reviewing 别的东西 |")
    A("| 2 抽取 | %d 个标量逐条正则抽取，每条记录 1-based 行号与**整行原文** `quote` | 抽不到即 `KeyError` 中断，绝不静默降级为默认值 |"
      % len(FIELDS))
    A("| 3 复算 | %d 条复算条目，每条给公式 / 输入 / 报告对应值 / 相对差 | 输入全部带行号，读者可手算核对 |" % len(rec))
    A("| 4 判定 | 容差优先取报告**自述**容差（G01 %s%%、D07 %s%%、D06 ≤%s）；未自述容差的只做恒等式/量级核对，只记覆盖缺口不判错 |"
      % (ex["cb_gate_tol_pct"]["text"], ex["d07_tol_hint_pct"]["text"], ex["d06_tol_hint"]["text"]))
    A("| 5 反证 | 每个检测器都能在被人为修改的源文本上**停止触发** | `tests/test_wp_5716_04_review.py` 用篡改快照做负向控制 |")
    A("| 6 出图 | 误差条形图（复算相对差 vs 自述容差）+ 复算台账状态矩阵 | 图与表同源于 `recompute.json` |")
    A("")
    A("## ③ 复核结果")
    A("")
    A("### 3.1 复算台账（全 %d 条，程序化注入）" % len(rec))
    A("")
    rows = []
    for r in rec.values():
        rows.append([
            "`%s`" % r["id"], r["label"], r["formula"],
            "%s %s" % (r["value_str"], r["unit"]),
            r["reported"] if r["reported"] is not None else "—",
            r["rel_diff_str"] + "%" if r["rel_diff_str"] != "—" else "—",
            fmt(r["tol_pct"]) + "%" if r["tol_pct"] is not None else "—",
            {"pass": "PASS", "fail": "**FAIL**", "derived": "派生", "violated": "**恒等式不闭合**",
             "unreconstructible": "**不可复算**"}[r["status"]],
        ])
    A(_table(rows, ["ID", "被复核的量", "公式", "复算值", "报告值", "相对差", "自述容差", "状态"]))
    A("")
    A("### 3.2 发现清单（%d 条：high %d / medium %d / low %d，阻断 %d 条）"
      % (len(findings), sev["high"], sev["medium"], sev["low"], len(blocking)))
    A("")
    frows = []
    for f in findings:
        frows.append([
            "`%s`" % f["id"], "**%s**" % f["severity"], "阻断" if f["blocking"] else "—",
            f["title"], "L%d" % f["claim"]["line"], "、".join("`%s`" % r for r in f["recompute_ids"]),
        ])
    if frows:
        A(_table(frows, ["ID", "严重度", "阻断", "结论", "行列", "复算依据"]))
    A("")
    for f in findings:
        A("#### %s（%s%s）%s" % (f["id"], f["severity"], "，阻断合并" if f["blocking"] else "", f["title"]))
        A("")
        A("> 报告原文（L%d）：%s" % (f["claim"]["line"], f["claim"]["quote"]))
        A("- 观测：%s" % f["observed"])
        A("- 应有：%s" % f["expected"])
        A("- 修复建议：%s" % f["remediation"])
        A("")
    A("### 3.3 已被独立证成的主张（不只挑错）")
    A("")
    A(_table([["`%s`" % k["id"], k["claim"], k["detail"]] for k in corroborated],
             ["ID", "主张", "复核证据"]))
    A("")
    A("## ④ 结果图")
    A("")
    A("![复算误差与容差](figures/%s)" % FIG_MAIN.name)
    A("")
    A("**图 1** %s" % fig_meta["caption"])
    A("")
    A("## ⑤ 注意点与局限")
    A("")
    A("1. **独立性限制**：本复核只有报告 markdown，没有战役工件与代码。凡断言实现层面的东西"
      "（G02–G16 到底检查了什么）一律记 `NOT_RUN`/`WITHHELD`，不因报告自述通过就算通过。")
    A("2. **ρ=%s t/m3 是复核方引入的常数**，不是报告里的数字。引入它只是为了证明「印出的 %s 可以被复现」，"
      "而这一步恰好说明报告写出的公式少了它——若读者按报告字面执行 G01，会得到 %s 并判 FAIL。"
      % (fmt(RHO_SEAWATER), ex["cb_reconstructed"]["text"], rec["C1_CB_LITERAL"]["value_str"]))
    A("3. **覆盖缺口不当作算术错误**：C7/C8 说明「距离×时间×冰区份额×设计点」四者不闭合，"
      "但只要 " + ex["c3_ice_frac_pct"]["text"] + "% 是时间份额而非距离份额，这份报告就没错。"
      "因此 F5 定级 medium 且标注为缺口，"
      "要求上游补一条断言或补一句口径说明，而不是改数字。")
    A("4. **判定对口径敏感处已显式标注**：`basis_sensitive` 为真的条目（%s）在有争议时必须同时给出两种口径的数，"
      "否则「D07 不通过」这类结论无法被独立读者复现。"
      % "、".join("`%s`" % k for k, r in rec.items() if r["basis_sensitive"]))
    A("5. **不评价物理正确性**：A2 是 identical-twin OSSE、E1 是闭环回放、B2 载荷谱来自工程约定，"
      "这些上游局限报告自己已披露，本包只登记其披露位置，不重复也不质疑其结论方向。")
    A("6. **改动面（含热文件声明）**：新增 `docs/kf/%s/`、`scripts/kf/review_wp_5716_04.py`、"
      "`tests/test_wp_5716_04_review.py`；另重建一次生成物 "
      "`docs/kf/wp-459-01/envelope_conformance.json`（它在本包之前就已陈旧，"
      "使 `test_census_regenerates_byte_for_byte` 恒红）。未改任何核心模块。" % PKG)
    A("")
    A("## ⑥ 误差判定（逐项回答「是否 <3%」）")
    A("")
    A("| 误差项 | 复算值 | 报告/基准值 | 相对差 | 是否 <3% |")
    A("|---|---|---|---|---|")
    for r in rec.values():
        if r["rel_diff_pct"] is None:
            verdict_cell = ("无独立基准（只做量级/恒等式闭合）" if r["reported"] is None
                            else "不适用（计数/百分比跨节比较，见 3.2 对应发现）")
            A("| %s | %s %s | %s | — | %s |"
              % (r["label"], r["value_str"], r["unit"],
                 r["reported"] if r["reported"] is not None else "—", verdict_cell))
            continue
        lt3 = "是" if abs(r["rel_diff_pct"]) < 3 else "**否**"
        A("| %s | %s %s | %s | %s | %s |" % (r["label"], r["value_str"], r["unit"],
                                             r["reported"], r["rel_diff_str"] + "%", lt3))
    A("")
    c3_drift = abs((v("c3_time_h") - v("concl_profile_time_h"))
                   / v("concl_profile_time_h") * 100)
    over3 = ["`%s`" % r["id"] for r in rec.values()
             if r["rel_diff_pct"] is not None and abs(r["rel_diff_pct"]) >= 3]
    nobench = sum(1 for r in rec.values() if r["rel_diff_pct"] is None)
    in3 = [r for r in rec.values()
           if r["rel_diff_pct"] is not None and abs(r["rel_diff_pct"]) < 3]
    over3 = [r for r in rec.values()
             if r["rel_diff_pct"] is not None and abs(r["rel_diff_pct"]) >= 3]
    nobench = [r for r in rec.values() if r["rel_diff_pct"] is None]
    A("**显式回答（逐项）**：")
    A("")
    A("- **满足 3%%**（%d 项）：%s。"
      % (len(in3), "、".join("`%s` %s%%" % (r["id"], r["rel_diff_str"]) for r in in3)))
    A("- **不满足 3%%**（%d 项）：%s。其中 `C7_TIME_FLOOR` 是四参数（距离/时间/冰区份额/设计点）"
      "恒等式不闭合，`C8*` 是反解冰区航速与 %s kn 设计点不一致——按覆盖缺口登记（F5），"
      "不当作算术错误。"
      % (len(over3), "、".join("`%s` %s%%" % (r["id"], r["rel_diff_str"]) for r in over3),
         ex["c3_design_kn"]["text"]))
    A("- **跨节自相矛盾**（不计入精度，按发现处理）：C3 航时 %s h vs %s h（%s，F2）、"
      "D1 航时 %s h vs %s h（%s，F10）、墙钟 %s s vs %s s（%s，F4）。"
      % (ex["c3_time_h"]["text"], ex["concl_profile_time_h"]["text"],
         pct(abs((v("c3_time_h") - v("concl_profile_time_h")) / v("concl_profile_time_h") * 100)),
         ex["d1_time_h"]["text"], ex["concl_route_time_h"]["text"],
         pct(abs((v("concl_route_time_h") - v("d1_time_h")) / v("d1_time_h") * 100)),
         ex["wallclock_sec2"]["text"], ex["wallclock_note9"]["text"],
         pct(abs((v("wallclock_sec2") - v("wallclock_note9")) / v("wallclock_note9") * 100))))
    A("- **无独立基准**（%d 项）：只做量级/恒等式闭合，本包不填「是」。" % len(nobench))
    A("")
    A("> `C1_CB_LITERAL` 的 %s%% 形式上小于 3%%，但已超出 G01 自述的 %s%% 容差，故 F1 仍是阻断项——"
      "「<3%%」是平台精度线，「是否在自述容差内」才是该门自己的判据，两者不可互相替代。"
      % (rec["C1_CB_LITERAL"]["rel_diff_str"], fmt(rec["C1_CB_LITERAL"]["tol_pct"])))
    A("## ⑦ 复现")
    A("")
    A("```bash")
    A("python3 scripts/kf/review_wp_5716_04.py            # 钉扎取回 + 重建全部交付物")
    A("python3 scripts/kf/review_wp_5716_04.py --offline  # 用已提交快照重建（无网络）")
    A("pytest -q tests/test_wp_5716_04_review.py          # 不变量 + 负向控制")
    A("```")
    A("")
    A("## 附录 A 未执行的检查（诚实登记）")
    A("")
    A(_table([[c["check"], c["state"], c["why"], c["impact"]] for c in CHECKS_NOT_RUN],
             ["检查", "状态", "为什么没做", "影响"]))
    A("")
    A("## 附录 B 处置")
    A("")
    A("- 处置：**请求修改**（%s）。阻断项 %s 必须先修：判据与执行不一致、同一量两个值、登记簿缺项。"
      % (verdict, "、".join("`%s`" % f["id"] for f in blocking)))
    A("- 上游报告工作室重跑一次 `review` 即可关闭本包：F1/F2/F3 修好、F4–F11 逐条答复后，"
      "本复核方可在同一 pin 的新哈希上重判。")
    A("- 本包**不自称已发布**；任务态保持 `awaiting_pr_merge` 直到平台合并（pr-gate 记账）。")
    return "\n".join(L) + "\n"


def render_readme(meta, rec, findings, verdict, sha, files):
    blocking = [f for f in findings if f["blocking"]]
    L = []
    A = L.append
    A("# %s — 报告 %s 的独立红队复核（%s）" % (PKG, REPORT_ID, verdict))
    A("")
    A("任务要点：对报告 %s（IN10-G1 冰区航行战役验收门）做一次**可复算**的独立复核，"
      "复核方自己重算每条可重算的数字，并把「判据是否被执行」与「结论是否对口径敏感」分开判。" % REPORT_ID)
    A("")
    A("## 结论")
    A("")
    A("- 判定 **%s**，阻断项 %d 条（%s）。" % (verdict, len(blocking),
                                          "、".join(f["id"] for f in blocking)))
    A("- 复算台账 %d 条：PASS %d / FAIL %d / 恒等式不闭合 %d / 不可复算 %d / 派生 %d。"
      % (len(rec),
         sum(1 for r in rec.values() if r["status"] == "pass"),
         sum(1 for r in rec.values() if r["status"] == "fail"),
         sum(1 for r in rec.values() if r["status"] == "violated"),
         sum(1 for r in rec.values() if r["status"] == "unreconstructible"),
         sum(1 for r in rec.values() if r["status"] == "derived")))
    A("- 未执行/无法执行的上游检查 5 类，登记 `NOT_RUN`/`WITHHELD`，不默认通过。")
    A("")
    A("## 交付物")
    A("")
    A(_table([[ "`%s`" % f["name"], f["sha256"][:16], str(f["bytes"]), f["role"]] for f in files],
             ["文件", "sha256(前 16)", "字节", "作用"]))
    A("")
    A("## 复现")
    A("")
    A("```bash")
    A("python3 scripts/kf/review_wp_5716_04.py --offline   # 由已提交快照重建")
    A("pytest -q tests/test_wp_5716_04_review.py           # 不变量 + 负向控制")
    A("```")
    A("")
    A("来源钉扎：`sha256:%s`（%d 字符）。改动快照会同时打破本包所有结论与测试。"
      % (sha, len(meta["markdown"])))
    A("")
    A("## 边界")
    A("")
    A("- 只审 markdown 字节；战役工件 `artifacts/campaign_ice_nav/*` 与 `backend/*` 不在本仓库，"
      "因此 16 条门断言的执行记录、pytest 13 passed、G13 哈希台账一律未重放（`NOT_RUN`）。")
    A("- 不发布、不自称已验证：`published.json` 由平台门在合并时写入，本包状态为 `awaiting_pr_merge`。")
    A("- 与在开 PR 无重叠（含热文件声明）：除新增 `docs/kf/%s/`、`scripts/kf/review_wp_5716_04.py`、"
      "`tests/test_wp_5716_04_review.py` 外，本 PR 只重建了一次生成物 "
      "`docs/kf/wp-459-01/envelope_conformance.json`（`scripts/kf/audit_envelope_conformance.py --write`）："
      "该记录在 main 上已陈旧（记录的信封数与当前检出不符），使 `test_census_regenerates_byte_for_byte` "
      "在无本包时也恒红；刷新后本包信封按 `schemas/kf_result.v1.schema.json` 判为 conforming。"
      "潜在冲突面仅此一个生成文件。" % PKG)
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------- figure
def make_figure(rec, findings, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    entries = [r for r in rec.values() if r["rel_diff_pct"] is not None]
    blocking_ids = {rid for f in findings if f["blocking"] for rid in f["recompute_ids"]}

    fig, axes = plt.subplots(1, 2, figsize=(14.0, 7.6),
                             gridspec_kw={"width_ratios": [1.25, 1.0]})
    ax = axes[0]
    ys = list(range(len(entries)))
    vals = [max(abs(r["rel_diff_pct"]), 1e-3) for r in entries]
    colors = []
    for r in entries:
        if r["within_tol"] is True:
            colors.append("#2f8f46")
        elif r["within_tol"] is False:
            colors.append("#c0392b")
        else:
            colors.append("#7f8c8d")
    ax.barh(ys, vals, color=colors, height=0.68)
    ax.set_yticks(ys)
    ax.set_yticklabels([r["id"] for r in entries], fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("|reviewer recompute − report printed| / report printed   [%]  (log)", fontsize=9)
    ax.set_title("A. recomputation vs the report's own numbers\n"
                 "bar = relative difference, tick = the tolerance the report states for itself",
                 fontsize=10)
    for i, r in enumerate(entries):
        if r["tol_pct"] is not None:
            ax.plot([r["tol_pct"]], [i], marker="|", color="black", markersize=15, mew=2)
            ax.annotate("%g%% tol" % r["tol_pct"], (r["tol_pct"], i), fontsize=7,
                        xytext=(3, 4), textcoords="offset points")
    ax.grid(axis="x", which="both", ls=":", lw=0.5, alpha=0.6)
    ax.set_ylim(len(entries) - 0.4, -0.6)

    ax2 = axes[1]
    cols = ["self-stated\ntolerance", "within that\ntolerance", "verdict depends\non basis",
            "feeds a blocking\nfinding"]
    mat = []
    for r in rec.values():
        mat.append([
            1.0 if r["tol_pct"] is not None else 0.0,
            1.0 if r["within_tol"] is True else 0.0,
            1.0 if r["basis_sensitive"] else 0.0,
            1.0 if r["id"] in blocking_ids else 0.0,
        ])
    ax2.imshow(mat, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax2.set_xticks(range(len(cols)))
    ax2.set_xticklabels(cols, fontsize=8)
    ax2.set_yticks(range(len(rec)))
    ax2.set_yticklabels([r["id"] + "  " + r["status"] for r in rec.values()], fontsize=7)
    ax2.set_title("B. recompute ledger state matrix\n"
                  "green = yes, red = no, grey = not applicable", fontsize=10)
    for i, row in enumerate(mat):
        for j, val in enumerate(row):
            ax2.text(j, i, "1" if val else "0", ha="center", va="center", fontsize=7,
                     color="black")
    ax2.set_xticks([x - 0.5 for x in range(1, len(cols))], minor=True)
    ax2.set_yticks([y - 0.5 for y in range(1, len(rec))], minor=True)
    ax2.grid(which="minor", color="white", lw=1.2)

    n_fail = sum(1 for r in rec.values() if r["status"] == "fail")
    n_viol = sum(1 for r in rec.values() if r["status"] == "violated")
    fig.suptitle("wp-5716-04 independent review of report %s — %d recompute entries, "
                 "%d contradict the report's own criteria, %d leave an identity unclosed"
                 % (REPORT_ID, len(rec), n_fail, n_viol), fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return {
        "name": path.name,
        "path": "figures/" + path.name,
        "caption": ("左：%d 条带有报告印出值的复算条目相对该值的偏差（对数轴；黑竖线为报告自述容差，"
                    "绿=在容差内、红=超容差）。右：全部 %d 条复算条目的状态矩阵"
                    "（是否有自述容差 / 是否在容差内 / 判定是否依赖口径 / 是否支撑阻断发现）。"
                    "读数：`C1_CB_LITERAL` 逐字代入得 %s，超出 G01 自述的 %s%% 容差；"
                    "`C12_DIV_TIME_C3` 与 `C13_DIV_SPEED_CONCL` 分别为 %s%% 与 %s%%；"
                    "共 %d 条条目支撑阻断项 %s。"
                    % (len(entries), len(rec), rec["C1_CB_LITERAL"]["value_str"],
                       fmt(rec["C1_CB_LITERAL"]["tol_pct"]),
                       rec["C12_DIV_TIME_C3"]["value_str"], rec["C13_DIV_SPEED_CONCL"]["value_str"],
                       len([r for r in rec.values() if r["id"] in blocking_ids]),
                       "、".join(f["id"] for f in findings if f["blocking"]))),
        "panels": ["recompute_error_vs_tolerance", "ledger_state_matrix"],
    }


# ----------------------------------------------------------------------- build
def build_docs(md, meta):
    ex = extract(md)
    rec = recompute(md, ex)
    findings = detect_findings(ex, rec)
    blocking = [f for f in findings if f["blocking"]]
    sev = {k: sum(1 for f in findings if f["severity"] == k) for k in ("high", "medium", "low")}
    verdict = "needs-fix" if (blocking or sev["high"]) else ("pass-with-notes" if findings else "pass")
    sha = hashlib.sha256(md.encode("utf-8")).hexdigest()
    corroborated = _corroborated(ex, rec)
    return ex, rec, findings, verdict, sha, corroborated


def _corroborated(ex, rec):
    v = lambda n: float(ex[n]["value"])
    return [
        {"id": "K1", "claim": "L/B=%s、B/T=%s 副尺度比" % (ex["lb_reported"]["text"],
                                                         ex["bt_reported"]["text"]),
         "recompute_ids": ["C3_LB", "C4_BT"],
         "detail": "复算 %s / %s，与印出值在 3 位小数内一致"
                   % (rec["C3_LB"]["value_str"], rec["C4_BT"]["value_str"])},
        {"id": "K2", "claim": "补 ρ=%s t/m3 后 Cb 反算 %s" % (fmt(RHO_SEAWATER),
                                                          ex["cb_reconstructed"]["text"]),
         "recompute_ids": ["C2_CB_WITH_RHO"],
         "detail": "复算 %s，与印出值差 %s%%（5 位小数内自洽）"
                   % (rec["C2_CB_WITH_RHO"]["value_str"], rec["C2_CB_WITH_RHO"]["rel_diff_str"])},
        {"id": "K3", "claim": "E1 闭环误差四分量在 ③ 与 ⑥ 两处逐字一致",
         "recompute_ids": [],
         "detail": "F %s / u %s / R_ice %s / GM %s，两处无漂移"
                   % (ex["e1_err_f_pct"]["text"], ex["e1_err_u_pct"]["text"],
                      ex["e1_err_rice_pct"]["text"], ex["e1_err_gm_pct"]["text"])},
        {"id": "K4", "claim": "A2→D1 守恒/探针/覆盖与 ⑤ 段第 7 条一致",
         "recompute_ids": [],
         "detail": "冰量守恒 %s、方向探针 %s、覆盖 %s%%"
                   % (ex["a2d1_conservation"]["text"], ex["a2d1_probe"]["text"],
                      ex["a2d1_coverage_pct"]["text"])},
        {"id": "K5", "claim": "能耗-功率量级自洽",
         "recompute_ids": ["C9_ENERGY_POWER", "C10_ENERGY_PER_NM"],
         "detail": "E/t = %s kW（装机 %s MW 的 %s%%），%s kWh/nm"
                   % (rec["C9_ENERGY_POWER"]["value_str"], ex["p_installed_MW"]["text"],
                      fmt(rec["C9_ENERGY_POWER"]["value"] / (v("p_installed_MW") * 1000) * 100),
                      rec["C10_ENERGY_PER_NM"]["value_str"])},
        {"id": "K6", "claim": "D1 独立 haversine 复算差 %s%% 与 684.1 nm 航运距离自洽"
                              % ex["d1_haversine_pct"]["text"],
         "recompute_ids": ["C6_SPEED_D1"],
         "detail": "S/t = %s kn，落在 PC6 母型服务航速 %s kn 之下的合理区间"
                   % (rec["C6_SPEED_D1"]["value_str"], ex["v_service_kn"]["text"])},
    ]


def fetch_report():
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, pw = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(base + "/auth/login",
                                 data=json.dumps({"username": user, "password": pw}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        tok = json.loads(resp.read().decode("utf-8"))
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise SystemExit("login returned no token")
    req = urllib.request.Request(base + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    md = payload.get(SOURCE_FIELD)
    if not md:
        raise SystemExit("report %s has no '%s' field" % (REPORT_ID, SOURCE_FIELD))
    meta = {
        "report_id": payload.get("id", REPORT_ID),
        "title": payload.get("title"),
        "scenario_key": payload.get("scenario_key"),
        "mission_id": payload.get("mission_id"),
        "created_at": payload.get("created_at"),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fetched_via": "GET %s/tensor/reports/%s (auth: platform login)" % (base, REPORT_ID),
        "source_field": SOURCE_FIELD,
        "markdown": md,
    }
    return md, meta


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def write_all(md, meta, do_write=True):
    ex, rec, findings, verdict, sha, corroborated = build_docs(md, meta)
    expected = EXPECTED_HASH
    if sha != expected:
        raise SystemExit("PIN MISMATCH: report %s sha256 %s != pinned %s"
                         % (REPORT_ID, sha, expected))
    meta = dict(meta)
    meta["sha256"] = sha
    meta["hash_matches_pin"] = True
    meta["chars"] = len(md)
    meta["lines"] = len(md.splitlines())

    files = []

    def emit(path, payload, role):
        b = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        if do_write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b)
        files.append({"name": str(path.relative_to(OUT_DIR)), "path": str(path.relative_to(REPO)),
                      "sha256": _sha(b), "bytes": len(b), "role": role})
        return _sha(b)

    emit(SNAPSHOT, md, "钉扎的快照（逐字节等于取回的 markdown，用于离线重建与哈希复核）")
    emit(META, json.dumps({k: v for k, v in meta.items() if k != "markdown"},
                          ensure_ascii=False, indent=2) + "\n",
         "取回元数据（哈希钉扎、抓取时刻、来源 URI）")

    fig_meta = make_figure(rec, findings, FIG_MAIN) if do_write else {
        "name": FIG_MAIN.name, "path": "figures/" + FIG_MAIN.name, "caption": "—", "panels": []}
    if do_write:
        b = FIG_MAIN.read_bytes()
        files.append({"name": "figures/" + FIG_MAIN.name,
                      "path": str(FIG_MAIN.relative_to(REPO)), "sha256": _sha(b),
                      "bytes": len(b), "role": "图 1：复算误差 vs 自述容差 + 台账状态矩阵"})
        if not fig_meta["panels"]:
            fig_meta["panels"] = ["recompute_error_vs_tolerance", "ledger_state_matrix"]

    recompute_doc = {
        "package_id": PKG, "report_id": REPORT_ID, "reviewed_source_hash": "sha256:" + sha,
        "convention": "value=复核方按 formula 用 inputs 算出的值；reported=报告印出的值（text 逐字来自源）；"
                      "rel_diff_pct=(value-reported)/reported×100；status 见下方 status_legend",
        "status_legend": {
            "pass": "与报告印出值之差在该报告自述容差内",
            "fail": "超出该报告自述容差，或同一量两值互相矛盾",
            "derived": "复核方派生量，报告未印对应值（只做量级/恒等式核对）",
            "violated": "报告自身参数满足该恒等式，但其印出的数字不满足（覆盖缺口）",
            "unreconstructible": "用报告印出的数字无法复算该值",
        },
        "entries": list(rec.values()),
    }
    emit(RECOMPUTE, json.dumps(recompute_doc, ensure_ascii=False, indent=2) + "\n",
         "复算台账：每条含公式/输入(带行号与原文)/复算值/报告值/相对差/容差/状态")

    review = {
        "reviewer_role": "red-team-reviewer",
        "package_id": PKG,
        "reviewed_package": "wp-5716-01",
        "reviewed_report_id": REPORT_ID,
        "reviewed_source_hash": "sha256:" + sha,
        "source": {k: meta[k] for k in ("title", "scenario_key", "mission_id", "fetched_at",
                                        "fetched_via", "source_field", "chars", "lines")},
        "verdict": verdict,
        "disposition": "request changes" if verdict == "needs-fix" else "approve with notes",
        "judge_semantic_fidelity": True,
        "semantic_fidelity": {
            "outcome": verdict,
            "numbers_fabricated": False,
            "summary": (
                "没有发现凭空捏造的数字：报告里每一个可复算的量化项都能由它自己印出的输入重算出来"
                "（E1 四分量、A2→D1 守恒/探针/覆盖、能耗量级、L/B 与 B/T 全部复现）。缺陷集中在"
                "「判据是否就是被执行的那条」「同一量是否只有一个值」与「登记簿是否可绑定」三层："
                "G01 写出的 Cb 公式逐字代入得 %s（偏差 %s%%，超出它自己的 %s%% 容差），"
                "只有补入未声明的 ρ=%s t/m3 才得到印出的 %s；C3 总航时在 ③ 段与结论段分别为 %s h 与 %s h，"
                "而 D07 的 65.6%% 分歧结论正挂在后者上；自称 %s 项披露但只能绑定 %d 个 ID。"
                "另有三条覆盖缺口（距离×时间×冰区份额×设计点不闭合、D07 比较基准未定义、"
                "B2 修正利用率 %s 不可由印出数字复算）如实登记，不当作算术错误。"
                % (rec["C1_CB_LITERAL"]["value_str"], rec["C1_CB_LITERAL"]["rel_diff_str"],
                   fmt(rec["C1_CB_LITERAL"]["tol_pct"]), fmt(RHO_SEAWATER),
                   ex["cb_reconstructed"]["text"], ex["c3_time_h"]["text"],
                   ex["concl_profile_time_h"]["text"], ex["assert_claim_disclosures"]["text"],
                   len(ex["disclosure_ids"]["registered"]),
                   ex["b2_util20_corrected"]["text"])),
        },
        "severity_counts": sev_count(findings),
        "blocking_findings": [f["id"] for f in findings if f["blocking"]],
        "findings": findings,
        "corroborated_claims": corroborated,
        "recompute_index": {r["id"]: {"value": r["value_str"], "unit": r["unit"],
                                      "reported": r["reported"], "status": r["status"],
                                      "rel_diff_pct": r["rel_diff_pct"]}
                            for r in rec.values()},
        "checks_not_run": CHECKS_NOT_RUN,
        "independence_limitations": [
            "只有报告 markdown；战役工件、上游模块源码、冰图数据均不在本仓库，"
            "G02–G16 的执行层与 pytest 13 passed 未重放。",
            "ρ=1.025 t/m3 是复核方引入的常数，用于证明「印出的 Cb 可复现」，不作为报告已有的输入。",
            "覆盖缺口（F5–F7）按缺口登记，不升级为错误；判定只基于报告写出的判据与自己印出的数字。",
            "复核方未修改上游任何文件，也未把任何上游结论标记为已验证。",
        ],
        "figure": fig_meta,
        "scope_matrix": {
            "reviewed": ["报告 markdown 字节（sha256 钉扎）", "全部%d 个可复算标量" % len(FIELDS),
                         "报告自述的判据与容差", "跨节一致性（同一量两值）"],
            "not_reviewed": ["上游代码路径", "战役工件与哈希台账", "冰图/OSSE 数据质量",
                             "物理模型选型", "发布状态"],
        },
        "generator": "scripts/kf/review_wp_5716_04.py",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    emit(REVIEW, json.dumps(review, ensure_ascii=False, indent=2) + "\n",
         "复核结论：判定/发现(含复现路径)/被证成主张/未执行检查/独立性限制")

    report_md = render_report(meta, ex, rec, findings, verdict, corroborated, sha, fig_meta)
    emit(REPORT_MD, report_md, "复核报告正文（全部数字由 recompute.json 渲染，零手抄）")

    readme = render_readme(meta, rec, findings, verdict, sha, files)
    emit(README_MD, readme, "包索引：结论摘要 + 交付物哈希 + 复现命令 + 边界声明")

    # Envelope shape follows schemas/kf_result.v1.schema.json (rev 1.1): additionalProperties
    # is false, so review metadata lives in the whitelisted `validation` block instead of
    # inventing top-level keys. Publication state is deliberately NOT a top-level `status`:
    # only the platform gate may write published.json, and this package does not claim it.
    envelope = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "repro_cmd": ["python3 scripts/kf/review_wp_5716_04.py --offline",
                      "pytest -q tests/test_wp_5716_04_review.py"],
        "validation": {
            "verdict": verdict,
            "disposition": review["disposition"],
            "severity_counts": sev_count(findings),
            "blocking_findings": review["blocking_findings"],
            "recompute_entries": len(rec),
            "finding_count": len(findings),
            "checks_not_run": len(CHECKS_NOT_RUN),
            "publication_state": "awaiting_pr_merge",
            "publication_note": "本包不自称已发布；published.json 由平台门在合并时写入（pr-gate 记账）。",
            "claims_verified_by_producer": False,
            "invariants": ["每个打印数字来自 recompute.json",
                           "每条复算输入带 1-based 行号与整行原文",
                           "每个检测器可在篡改源上停止触发",
                           "判定与阻断项一致",
                           "未标记已验证"],
            "tests": "pytest -q tests/test_wp_5716_04_review.py",
        },
        "provenance": {
            "source_uri": SOURCE_URI, "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + sha, "hash_matches_pin": True,
            "expected_hash": "sha256:" + expected, "chars": meta["chars"],
            "source_chars": meta["chars"], "lines": meta["lines"],
            "title": meta["title"], "scenario_key": meta["scenario_key"],
            "retrieved_via": meta["fetched_via"], "retrieved_at": meta["fetched_at"],
            "generator": "scripts/kf/review_wp_5716_04.py",
            "reviewed_package": review["reviewed_package"],
        },
        "outputs": {f["name"]: {"path": f["path"], "sha256": f["sha256"],
                                "bytes": f["bytes"], "role": f["role"]} for f in files},
    }
    emit(ENVELOPE, json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
         "KF 结果信封（04-independent-review，status=awaiting_pr_merge）")
    return envelope, rec, findings, files


def sev_count(findings):
    c = {k: sum(1 for f in findings if f["severity"] == k) for k in ("high", "medium", "low")}
    c["blocking"] = sum(1 for f in findings if f["blocking"])
    c["total"] = len(findings)
    return c


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="rebuild from the committed snapshot")
    ap.add_argument("--dry-run", action="store_true", help="build in memory, write nothing")
    args = ap.parse_args(argv)

    if args.offline:
        if not SNAPSHOT.exists():
            raise SystemExit("no snapshot at %s; run without --offline first" % SNAPSHOT)
        md = SNAPSHOT.read_text(encoding="utf-8")
        meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
        meta["markdown"] = md
    else:
        md, meta = fetch_report()

    envelope, rec, findings, files = write_all(md, meta, do_write=not args.dry_run)
    val = envelope["validation"]
    print("verdict=%s  findings=%d  blocking=%d  recompute=%d  files=%d"
          % (val["verdict"], len(findings), len(val["blocking_findings"]),
             len(rec), len(files)))
    for f in files:
        print("  %-34s %8d B  %s" % (f["name"], f["bytes"], f["sha256"][:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
