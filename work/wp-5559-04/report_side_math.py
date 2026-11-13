#!/usr/bin/env python3
"""wp-5559-04 · reviewer-side re-derivation of the numbers the report declares.

Nothing here trusts the upstream manifest or the producer's scripts: every value is
recomputed from the report markdown / embedded machine-criteria JSON that the reviewer
fetched independently, using physics relations the report itself states.

Usage: python3 work/wp-5559-04/report_side_math.py [--source ...] [--out ...]
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


def embedded_json(text: str) -> dict:
    m = re.search(r"```json\n(.*?)\n```", text, re.S)
    return json.loads(m.group(1))


def table_rows(text: str, header_token: str) -> list[list[str]]:
    """Return the markdown table rows of the table whose header contains header_token."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if header_token in ln and ln.lstrip().startswith("|"):
            rows = []
            for ln2 in lines[i + 1:]:
                if not ln2.lstrip().startswith("|"):
                    break
                rows.append([c.strip() for c in ln2.strip().strip("|").split("|")])
            return rows
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="work/wp-5559-04/source_5559.md")
    ap.add_argument("--out", default="work/wp-5559-04/report_side_math.json")
    a = ap.parse_args()
    text = Path(a.source).read_text(encoding="utf-8")
    j = embedded_json(text)
    crit = j["criteria"]
    st = j["stats_selected"]

    N = 1024 * 1024
    C = 0.62
    res: dict[str, object] = {"derivations": [], "inconsistencies": []}

    def rec(name, reviewer, stated, rel_tol, note=""):
        ok = stated is None or (reviewer is not None and abs(reviewer - stated) <= rel_tol * max(1.0, abs(stated)))
        res["derivations"].append(
            {"name": name, "reviewer_value": reviewer, "stated_value": stated,
             "rel_tol": rel_tol, "agrees": ok, "note": note}
        )

    # --- pure arithmetic identities -------------------------------------------------
    rec("grid_cells", N, 1048576, 0)
    rec("domain_extent_km", 1024 * 2.0 / 1000.0, 2.05, 0.005, "stated to 2 dp")
    n_t = round(C * N)
    cov = n_t / N
    rec("coverage_from_count_control", cov, crit["G2_coverage_rel_error_lt_1e_6"]["measured"], 0)
    rec("coverage_rel_error", (C - cov) / C, crit["G2_coverage_rel_error_lt_1e_6"]["value"], 1e-6)
    rec("coverage_quantization_bound", 1.0 / (2 * N * C), crit["G2_coverage_rel_error_lt_1e_6"]["quantization_bound"], 1e-9)
    w0, w1 = crit["G4_four_states_present"]["frazil_window_s"]
    rec("frazil_window_hours", (w1 - w0) / 3600.0, 17.10, 5e-4, "report states 17.10 h")
    rec("frazil_window_start_h", w0 / 3600.0, 99.23, 1e-4)
    rec("frazil_window_end_h", w1 / 3600.0, 116.32, 1e-4)
    rec("ridge_mean_spacing_from_count", 120000.0 / 804.0, 150.0 * (1 - st["ridge_spacing_rel_error"]), 1e-6,
        "120 km / 804 ridges vs reported 148.84 m mean spacing")

    # --- physics relations the report states --------------------------------------
    rho_i, rho_w = 917.0, 1025.0  # standard sea-ice / sea-water densities (not declared in report)
    k_max_iso = rho_i / (rho_w - rho_i)
    rec("isostatic_k_max", k_max_iso, 8.49, 1e-3, "report section 5.3 states 8.49")
    k = 4.4
    p_implied = ((1 + k) * rho_i - k * rho_w) / (k * rho_i)
    rec("keel_porosity_implied", p_implied, st["ridge_keel_porosity_implied"], 1e-4,
        "p solved from k = rho_i/(rho_w - rho_i(1-p)) with rho_i=917, rho_w=1025")
    phi_max, alpha = 0.35, 1.7
    nu = st["frazil_nu_peak"]
    phi_from_nu = phi_max * (1 - nu ** (-1 / alpha))
    rec("frazil_phi_L_from_nu_peak", phi_from_nu, 0.1277, 2e-3,
        "invert nu/nu_w = (1-phi_L/phi_max)^-alpha")
    rec("frazil_nu_from_phi_L", (1 - 0.1277 / phi_max) ** (-alpha), nu, 2e-3, "forward check")

    # --- display-vs-derivation consistency of the verification table --------------
    rows = table_rows(text, "基准（解析/经验）")
    parsed = []
    for r in rows:
        if len(r) >= 5:
            parsed.append(r)
    def num(s):
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", s.replace("−", "-"))
        return float(m.group(0)) if m else None

    checks = {
        "相关长度 L": None, "磨道宽度 W": None, "浮冰谱斜率（抽样端）": None,
        "浮冰谱斜率（场反测）": None, "间距均值 λ": None, "帆高均值 0.3+λ_s": None,
        "龙骨-帆比 k": None, "黏度峰 ν/ν_w": None,
    }
    for r in parsed:
        for key in checks:
            if r[1] == key or r[1].startswith(key):
                base, meas, err = num(r[2]), num(r[3]), num(r[4])
                derived = None
                if base not in (None, 0) and meas is not None:
                    derived = abs(base - meas) / abs(base)
                checks[key] = {"row": r, "base": base, "measured": meas, "stated_rel_err": err,
                               "reviewer_rel_err_from_displayed": derived}
    res["verification_table_recheck"] = checks
    for key, c in checks.items():
        if c and c["stated_rel_err"] is not None and c["reviewer_rel_err_from_displayed"] is not None:
            diff = abs(c["stated_rel_err"] - c["reviewer_rel_err_from_displayed"])
            if diff > 1e-3:
                res["inconsistencies"].append(
                    {"quantity": key, "displayed_base": c["base"], "displayed_measured": c["measured"],
                     "stated_rel_err": c["stated_rel_err"],
                     "reviewer_rel_err_from_displayed": c["reviewer_rel_err_from_displayed"],
                     "abs_gap": diff,
                     "implied_measured_from_stated_err": (
                         c["base"] * (1 + c["stated_rel_err"]) if c["measured"] > c["base"]
                         else c["base"] * (1 - c["stated_rel_err"])),
                     "note": "the two displayed numbers do not reproduce the displayed relative error; "
                             "the stated error implies the value in implied_measured_from_stated_err"})

    # --- G3 applicability coverage -------------------------------------------------
    g3 = crit["G3_out_of_domain_marked_unknown"]
    frac = g3["in_domain_fraction"]
    res["g3_applicability"] = {
        "evidence_per_state": g3["evidence"],
        "in_domain_fraction_per_state": frac,
        "states_with_null_fraction_but_REAL_evidence": [s for s, v in frac.items() if v is None and g3["evidence"].get(s) == "REAL"],
        "states_checked": [s for s, v in frac.items() if v is not None],
        "pass_flag": g3["pass"],
        "minimum_fraction_checked": min([v for v in frac.values() if v is not None], default=None),
    }

    # --- range check of the four declared states against the stated applicability domain
    domain = {"floe_slope_b": (1.5, 3.0), "floe_D_max": 200.0, "sail": (0.3, 4.0), "supercooling": 0.2}
    res["domain_parameter_check"] = {
        "declared": {"b": 2.05, "D_max_m": 90.0, "sail_range_m": [0.3, 4.0], "deltaT_K": 0.18},
        "domain": domain,
        "b_in_domain": domain["floe_slope_b"][0] <= 2.05 <= domain["floe_slope_b"][1],
        "D_max_in_domain": 90.0 <= domain["floe_D_max"],
        "deltaT_in_domain": 0.18 <= domain["supercooling"],
        "ridge_sail_violations_declared": j["applicability"]["pressure_ridge"]["violations"],
        "keel_porosity_inside_measured_band_0.1_0.3": 0.1 <= st["ridge_keel_porosity_implied"] <= 0.3,
    }

    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "derivations"}, ensure_ascii=False, indent=1)[:4000])
    print("\nDERIVATIONS:")
    for d in res["derivations"]:
        print(f"  {'OK ' if d['agrees'] else 'BAD'} {d['name']:34s} reviewer={d['reviewer_value']!r:22} stated={d['stated_value']!r}")
    return 0 if not res["inconsistencies"] else 1


if __name__ == "__main__":
    raise SystemExit(main())