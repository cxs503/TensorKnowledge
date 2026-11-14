#!/usr/bin/env python3
"""Gate the wp-11557-04 bundle: JSON schema validity + numeric provenance.

numeric provenance: every literal number that appears in the review prose must be
re-derivable from probe_results*.json (or be an input constant), so nothing is
restated from memory.
"""
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs/kf/wp-11557-04"
res = json.loads((OUT / "kf_result.wp-11557-04.json").read_text())

# ---------------------------------------------------------- 1. schema
import jsonschema  # noqa: E402

schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text())
errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(res),
                key=lambda e: list(e.path))
schema_report = {"valid": not errors,
                 "errors": [f"{list(e.path)}: {e.message}" for e in errors]}

# ------------------------------------------- 2. numeric provenance table
p1 = json.loads((HERE / "probe_results.json").read_text())
p2 = json.loads((HERE / "probe2_results.json").read_text())
p3 = json.loads((HERE / "probe3_results.json").read_text())
p4 = json.loads((HERE / "probe4_results.json").read_text())
b1, b2, b3 = p1["B1_closed_form"], p1["B2_shipped_code"], p3
kof = p1["A_upstream_ko_fidelity"]

claims = [
    ("F1 52.9%", 52.9, b1["C4_deviation_pct"], 0.05),
    ("F1 reference 2.7629", 2.7629, b1["V_c_formula_rho917_m_s"], 1e-3),
    ("F1 half threshold 1.3814", 1.3814, b2["half_V_c"], 1e-3),
    ("F1 validator rel err 0.5295", 0.5295, b3["timco_result"]["relative_error"], 1e-3),
    ("F1 rho needed 4142", 4142.0, b1["rho_needed_for_reported_Vc_model"], 1.0),
    ("F2 deviation 6310%", 6310.0,
     100 * b3["lindqvist_relative_error_is_ratio_not_percent"]["returned"], 1.0),
    ("F2 factor 316", 316.0,
     100 * b3["lindqvist_relative_error_is_ratio_not_percent"]["returned"] / 20.0, 1.0),
    ("F2 ratio 63.1016", 63.1016, b3["lindqvist_relative_error_is_ratio_not_percent"]["returned"], 1e-3),
    ("F2 alternative basis 98.4%", 98.4, b1["C5_deviation_pct_relative_to_model"], 0.05),
    ("F3 band 3.0deg", 3.0, b1["C1_10pct_band_width_deg"][0], 1e-9),
    ("F3 band 4.5deg", 4.5, b1["C1_10pct_band_width_deg"][1], 1e-9),
    ("F3 ratio 23x", 23.0, b1["C1_band_to_reported_range_ratio"][0], 0.4),
    ("F3 ratio 15.6x", 15.6, b1["C1_band_to_reported_range_ratio"][1], 0.05),
    ("F5 KE 2.54e-5 J", 2.54e-5, b3["C8"]["KE_initial_total_J"], 1e-7),
    ("F5 bound/KE ratio 39x", 39.0, 1e-3 / b3["C8"]["KE_initial_total_J"], 0.5),
    ("F5 max change 5.07e-5 J", 5.07e-5, 2 * b3["C8"]["KE_initial_total_J"], 1e-7),
    ("F5 78.9% of KE at 1 m/s", 78.9, b1["C8_abs_change_over_KE_1m_s_pct"], 0.05),
    ("F5 3943% at 0.1 m/s", 3943.0, b3["C8"]["reported_1eJ_as_fraction_of_KE_pct"], 1.0),
    ("F7 R_bend 7.2 MN", 7.2, b1["R_bend_at_V0_MN"], 0.01),
    ("F7 R_crush 75 MN", 75.0, b1["R_crush_range_MN"][0], 1e-6),
    ("F7 R_crush 112.5 MN", 112.5, b1["R_crush_range_MN"][1], 1e-6),
    ("F7 crossover 94 m/s", 94.0, b1["V_needed_for_bend_to_reach_crush_min_m_s"], 0.3),
    ("F6 cells 4000", 4000, p2["phase_diagram_cells"], 0),
    ("F6 splitting 270", 270, p2["phase_diagram_mode_census"].get("splitting"), 0),
    ("F6 mixed 0", 0, p2["phase_diagram_mode_census"].get("mixed", 0), 0),
    ("F4 tests 35", 35, p4["passed"], 0),
    ("F8 quotes 11", 11, kof["quotes_total"], 0),
    ("F8 range exact 10", 10, kof["quotes_range_exact"], 0),
]
checks = []
for name, claimed, got, tol in claims:
    ok = got is not None and abs(float(got) - claimed) <= tol
    checks.append({"claim": name, "stated": claimed,
                   "recomputed": round(float(got), 6) if got is not None else None,
                   "ok": bool(ok)})

# ------------------------------------------------- 3. quote gate re-check
src = (HERE / "source.md").read_text(encoding="utf-8")
qcheck = {"checked": 0, "verbatim_unique": 0, "bad": []}
for f in res["outputs"]["review_report.json"]["findings"]:
    for k, v in f.items():
        if k.startswith("quote"):
            qcheck["checked"] += 1
            if src.count(v) == 1:
                qcheck["verbatim_unique"] += 1
            else:
                qcheck["bad"].append({"finding": f["id"], "field": k})

# --------------------------------------------- 4. code-quote verification
tensordem = pathlib.Path("/root/tp-agent/work/m19513")
code_src = (tensordem / "src/tensordem/ice_mixed_mode/__init__.py").read_text()
code_quotes = {
    "reference_is_model": "V_c_timco = compute_critical_velocity(config)",
    "docstring_formula": "R = 0.5 · σ_f · h² · (1 + 0.5 · B/h) · f(shape)",
    "implementation": "R_lindqvist = C_L * config.sigma_f * config.h**2 * math.sqrt(config.D / config.h)",
    "half_threshold": "if V < 0.5 * V_c:",
    "double_threshold": "elif V > 2.0 * V_c:",
    "hardcoded_weights": "w_crush = 0.7",
}
code_check = {k: (v in code_src) for k, v in code_quotes.items()}
code_check["all_present"] = all(code_check.values())
code_check["quotes"] = code_quotes

tests_src = (tensordem / "tests/test_dem_ice.py").read_text()
code_check["c8_assertion_present"] = "assert energy_change < 1e-3 or KE_initial < 1e-10" in tests_src

report = {
    "schema": schema_report,
    "numeric_provenance": {"all_ok": all(c["ok"] for c in checks), "checks": checks},
    "quote_gate": {**qcheck, "all_ok": not qcheck["bad"]},
    "code_quote_gate": code_check,
}
(HERE / "checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"schema_valid": schema_report["valid"], "schema_errors": schema_report["errors"],
                  "numeric_all_ok": report["numeric_provenance"]["all_ok"],
                  "numeric_failures": [c for c in checks if not c["ok"]],
                  "quote_gate_ok": report["quote_gate"]["all_ok"],
                  "code_quotes_ok": code_check["all_present"],
                  "c8_assert_in_code": code_check["c8_assertion_present"]},
                 ensure_ascii=False, indent=2))