#!/usr/bin/env python3
"""Independent red-team probes for report 11557 / upstream wp-11557-01.

Two independent evidence channels:
  A. quote verification: every quote in the upstream KO asset manifest must be a
     verbatim substring of the source markdown at the stated char range, and
     must be unique in the document (zero-hand-copy check).
  B. numeric re-derivation: recompute the report's own headline numbers from the
     report's own stated formulas/parameters, and re-run the shipped code so the
     report's numbers can be compared with what the code actually returns.

Everything is written to probe_results.json; no number is typed by hand.
"""
import hashlib
import json
import math
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KO = ROOT / "docs/kf/wp-11557-01/kf_result.wp-11557-01.json"
SRC = HERE / "source.md"
TENSORDEM = pathlib.Path("/root/tp-agent/work/m19513")  # read-only sibling checkout

md = SRC.read_text(encoding="utf-8")
out = {}

# ---------------------------------------------------------------- A. quotes
ko = json.loads(KO.read_text(encoding="utf-8"))
am = ko["outputs"]["asset_manifest.json"]
quotes = []
for a in am["assets"]:
    loc = a.get("locator", {})
    q = loc.get("quote")
    if q is None:
        quotes.append({"asset_id": a["asset_id"], "quote": None, "status": "no_quote_declared"})
        continue
    rec = {
        "asset_id": a["asset_id"],
        "quote": q,
        "in_document": q in md,
        "occurrences_in_source": md.count(q),
        "declared_range": [loc.get("start_char"), loc.get("end_char")],
        "range_slice_matches": None,
    }
    s, e = loc.get("start_char"), loc.get("end_char")
    if isinstance(s, int) and isinstance(e, int):
        rec["range_slice_matches"] = md[s:e] == q
        rec["range_slice_head"] = md[s:e][:40]
    quotes.append(rec)

counts = am["counts"]
out["A_upstream_ko_fidelity"] = {
    "source_sha256": "sha256:" + hashlib.sha256(md.encode()).hexdigest(),
    "ko_declared_source_hash": ko["provenance"]["source_hash"],
    "ko_source_chars_declared": ko["provenance"].get("source_chars"),
    "source_chars_actual": len(md),
    "assets_declared": counts["assets"],
    "assets_present": len(am["assets"]),
    "by_class_sum": sum(counts["by_class"].values()),
    "by_resolution_sum": sum(counts["by_resolution"].values()),
    "quotes_total": len(quotes),
    "quotes_verbatim": sum(1 for r in quotes if r.get("in_document")),
    "quotes_unique": sum(1 for r in quotes if r.get("occurrences_in_source") == 1),
    "quotes_range_exact": sum(1 for r in quotes if r.get("range_slice_matches")),
    "quotes": quotes,
    "ko_claims_count": len(ko.get("claims") or []),
    "ko_verification_all_pass": json.loads(
        (ROOT / "docs/kf/wp-11557-01/verification.json").read_text())["all_pass"],
}

# ------------------------------------------- B1. closed-form re-derivations
sigma_c, sigma_f, sigma_t = 3e6, 0.7e6, 0.7e6
h, D, E, rho_w, nu = 1.0, 10.0, 5e9, 1025.0, 0.33
rho_ice = 917.0
g = 9.81

L_b = (E * h**3 / (12 * (1 - nu**2) * rho_w * g)) ** 0.25
Vc_formula = 0.1 * math.sqrt(sigma_f / (rho_ice * h))
R_crush_0 = 2.5 * sigma_c * h * D * 1.0
R_crush_max = 2.5 * sigma_c * h * D * 1.5
R_bend_0 = 0.7 * sigma_f * h**2 * L_b * 1.0
R_split_0 = 1.5 * sigma_t * h * D * 1.0 / (1 + (D / L_b - 1) ** 2)

# icosahedron particle mass (circumradius 0.01, rho=1000) -> energy scale for C8
R_circ, rho_p = 0.01, 1000.0
a_edge = 4 * R_circ / math.sqrt(10 + 2 * math.sqrt(5))
V_ico = (5 / 12) * (3 + math.sqrt(5)) * a_edge**3
m_particle = rho_p * V_ico
v_for_5pct = math.sqrt(1e-3 / (0.05 * 0.5 * m_particle))


def rel(a, b):
    return abs(a - b) / abs(b)


report = {
    "V_c_model_reported": 1.3,
    "V_c_timco_reported": 2.76,
    "R_model_reported_MN": 70.9,
    "R_lindqvist_reported_MN": 1.1,
    "repose_angle_range_reported_deg": [0, 70],
    "repose_benchmark_reported_deg": [30, 45],
    "energy_change_reported_J": 1e-3,
    "reported_error_pct_S6": {"repose": "not_a_number", "V_c": 53.0, "R_total": 63.0},
    "criteria_pct": {"C1": 10.0, "C4": 30.0, "C5": 20.0, "C8": 5.0},
}

out["B1_closed_form"] = {
    "inputs": {"sigma_c": sigma_c, "sigma_f": sigma_f, "sigma_t": sigma_t, "h": h,
               "D": D, "E": E, "rho_water": rho_w, "nu": nu, "rho_ice": rho_ice},
    "L_b_m": L_b,
    "V_c_formula_rho917_m_s": Vc_formula,
    "V_c_equals_reported_timco": {"value": Vc_formula, "reported": 2.76,
                                  "rel_err": rel(Vc_formula, 2.76)},
    "rho_needed_for_reported_Vc_model": sigma_f / (h * (1.3 / 0.1) ** 2),
    "R_crush_range_MN": [R_crush_0 / 1e6, R_crush_max / 1e6],
    "R_model_below_crush_minimum": 70.9 < R_crush_0 / 1e6,
    "R_model_over_crush_min_ratio": 70.9 / (R_crush_0 / 1e6),
    "R_bend_at_V0_MN": R_bend_0 / 1e6,
    "R_split_at_V0_MN": R_split_0 / 1e6,
    "V_needed_for_bend_to_reach_crush_min_m_s": (R_crush_0 / R_bend_0 - 1) / 0.1,
    "C4_deviation_pct": 100 * rel(1.3, 2.76),
    "C4_criterion_met": rel(1.3, 2.76) < 0.30,
    "C5_deviation_pct_vs_reference": 100 * rel(70.9, 1.1),
    "C5_deviation_pct_vs_model": 100 * rel(70.9, 1.1),
    "C5_deviation_pct_relative_to_model": 100 * abs(70.9 - 1.1) / 70.9,
    "C5_criterion_met": rel(70.9, 1.1) < 0.20,
    "C5_reported_error_63pct_reproducible": any(
        abs(x - 63.0) < 0.5 for x in (100 * rel(70.9, 1.1), 100 * abs(70.9 - 1.1) / 70.9)),
    "C1_reported_range_width_deg": 70.0,
    "C1_10pct_band_width_deg": [0.1 * 30, 0.1 * 45],
    "C1_band_to_reported_range_ratio": [70.0 / 3.0, 70.0 / 4.5],
    "C1_worst_case_deviation_pct_vs_upper_benchmark": 100 * abs(70 - 45) / 45,
    "particle_mass_kg": m_particle,
    "KE_at_1m_s_J": 0.5 * m_particle * 1.0,
    "C8_abs_change_over_KE_1m_s_pct": 100 * 1e-3 / (0.5 * m_particle),
    "C8_speed_for_5pct_band_m_s": v_for_5pct,
}

# --------------------------------- B2. run the shipped code (read-only import)
sys.path.insert(0, str(TENSORDEM / "src"))
code = {}
try:
    from tensordem import ice_mixed_mode as mm

    cfg = mm.IceMixedModeConfig()
    code["config_defaults"] = {k: getattr(cfg, k) for k in
                               ("sigma_c", "sigma_f", "sigma_t", "h", "D", "E",
                                "rho_ice", "rho_water", "nu")}
    code["V_c"] = mm.compute_critical_velocity(cfg)
    code["half_V_c"] = 0.5 * code["V_c"]
    code["modes_0.5Vc_minus_eps"] = mm.determine_dominant_mode(cfg, code["half_V_c"] - 1e-6)
    code["modes_0.5Vc_plus_eps"] = mm.determine_dominant_mode(cfg, code["half_V_c"] + 1e-6)
    tr = mm.compute_mode_transition(cfg)
    code["mode_transition"] = {"V_c_sweep": tr.V_c, "V_c_timco": tr.V_c_timco,
                               "relative_error": tr.relative_error,
                               "mode_sequence_unique": sorted(set(tr.mode_sequence))}
    lq = mm.validate_against_lindqvist(cfg, V=1.0)
    code["lindqvist"] = {k: lq[k] for k in
                         ("R_model", "R_lindqvist", "relative_error", "R_crush",
                          "R_bend", "R_split")}
    code["lindqvist_MN"] = {k: lq[k] / 1e6 for k in ("R_model", "R_lindqvist",
                                                     "R_crush", "R_bend", "R_split")}
    pd = mm.compute_phase_diagram(cfg)
    regions = {}
    for row in pd.regions:
        regions[row.get("mode")] = regions.get(row.get("mode"), 0) + 1
    code["phase_diagram_modes"] = regions
    code["phase_diagram_cells"] = len(pd.regions)
    code["dominant_mode_scan"] = {
        f"{v:.2f}": mm.determine_dominant_mode(cfg, v)
        for v in (0.1, 0.5, 1.0, 1.3, 1.4, 2.0, 2.8, 5.0)
    }
except Exception as exc:  # noqa: BLE001
    code["error"] = f"{type(exc).__name__}: {exc}"

out["B2_shipped_code"] = code
out["B2_tensordem_commit"] = subprocess.run(
    ["git", "-C", str(TENSORDEM), "log", "-1", "--format=%H %ad"],
    capture_output=True, text=True).stdout.strip()

# -------------------------- B3. do the shipped tests assert or just execute?
tests_src = (TENSORDEM / "tests/test_dem_ice.py").read_text(encoding="utf-8")
asserts = tests_src.count("assert ")
out["B3_tests"] = {"test_methods": tests_src.count("    def test_"),
                   "assert_statements": asserts,
                   "file_lines": tests_src.count("\n") + 1}

(HERE / "probe_results.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n")
print(json.dumps({k: v for k, v in out.items() if k != "A_upstream_ko_fidelity"},
                 ensure_ascii=False, indent=2, default=str))
print("A_upstream_ko_fidelity:", json.dumps(
    {k: v for k, v in out["A_upstream_ko_fidelity"].items() if k != "quotes"},
    ensure_ascii=False, indent=2))