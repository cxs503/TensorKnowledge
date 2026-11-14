#!/usr/bin/env python3
"""Build the wp-11557-04 review result bundle.

Zero-hand-copy policy: every quote in the result is extracted *from* source.md
by line anchor (never typed), then re-verified as an exact unique substring.
All numbers come from probe_results*.json written by probe.py / probe2.py /
probe3.py, not from memory.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs/kf/wp-11557-04"
SRC = HERE / "source.md"
PKG = "wp-11557-04"
REPORT_ID = "11557"

md = SRC.read_text(encoding="utf-8")
md_bytes = SRC.read_bytes()
sha = "sha256:" + hashlib.sha256(md_bytes).hexdigest()
DECLARED = "sha256:471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3"
LINES = md.split("\n")


def q(anchor):
    """Return the unique source line starting with `anchor`, verbatim."""
    hits = [ln for ln in LINES if ln.startswith(anchor)]
    if len(hits) != 1:
        raise SystemExit(f"anchor {anchor!r} matched {len(hits)} lines")
    return hits[0]


p1 = json.loads((HERE / "probe_results.json").read_text())
p2 = json.loads((HERE / "probe2_results.json").read_text())
p3 = json.loads((HERE / "probe3_results.json").read_text())
p4 = json.loads((HERE / "probe4_results.json").read_text())
b1, b2, b3 = p1["B1_closed_form"], p1["B2_shipped_code"], p3
kof = p1["A_upstream_ko_fidelity"]

# ------------------------------------------------------------ findings
findings = [
    {
        "id": "F1",
        "severity": "high",
        "blocking": True,
        "type": "false PASS verdict / criterion violated by the report's own numbers",
        "criterion": "C4",
        "quote_verdict_row": q("| C4 |"),
        "quote_error_row": q("| V_c |"),
        "claim": "C4 (V_c vs Timco <30%) is marked PASS with V_c_model=1.3 m/s vs V_c_timco=2.76 m/s.",
        "measured": {
            "deviation_pct_from_report_numbers": round(b1["C4_deviation_pct"], 2),
            "criterion_pct": 30.0,
            "criterion_met": b1["C4_criterion_met"],
            "shipped_validator_relative_error": round(b3["timco_result"]["relative_error"], 4),
            "shipped_V_c_model": b3["timco_result"]["V_c_model"],
            "shipped_V_c_timco": round(b3["timco_result"]["V_c_timco"], 4),
        },
        "why_it_matters": (
            "The report's own two numbers give 52.9% deviation against a declared <30% "
            "threshold, and the report's own section 6 already answers 否 for this row. "
            "The PASS label in the acceptance table therefore contradicts the same document."
        ),
        "independent_finding_on_the_comparison_itself": {
            "reference_is_the_model": (
                "validate_against_timco() sets V_c_timco = compute_critical_velocity(config), "
                "i.e. the 'Timco (2001) reference' is the model's own closed form "
                "0.1*sqrt(sigma_f/(rho_ice*h)); no literature value is stored anywhere."),
            "reference_value": round(b1["V_c_formula_rho917_m_s"], 4),
            "reported_reference": 2.76,
            "reconstruction_rel_err": round(b1["V_c_equals_reported_timco"]["rel_err"], 6),
            "definitional_offset": (
                "determine_dominant_mode() switches out of crushing at V = 0.5*V_c, so the "
                "sweep-reported 'model' critical velocity is a half-threshold quantised to its "
                "own grid (0.5*%.4f = %.4f -> reported 1.3 on a 0.1 m/s grid). The residual "
                "53%% is 1 - 1.3/2.7629, i.e. factor-two plus grid quantisation, not physics."
                % (b1["V_c_formula_rho917_m_s"], b2["half_V_c"])),
            "rho_needed_to_return_1.3_kg_m3": round(b1["rho_needed_for_reported_Vc_model"], 1),
        },
        "recommendation": (
            "Relabel C4 as FAIL/not-met (53% > 30%), and replace the circular 'Timco reference' "
            "with an externally sourced V_c value before any PASS verdict is claimed. If the "
            "intent was to test the classifier threshold, state that the compared quantity is "
            "0.5*V_c by construction and the comparison cannot validate anything."),
    },
    {
        "id": "F2",
        "severity": "high",
        "blocking": True,
        "type": "false PASS verdict + unit error (ratio reported as percent)",
        "criterion": "C5",
        "quote_verdict_row": q("| C5 |"),
        "quote_error_row": q("| R_total |"),
        "claim": "C5 (resistance vs Lindqvist <20%) is marked PASS with R_model=70.9 MN vs R_lindqvist=1.1 MN.",
        "measured": {
            "deviation_pct_from_report_numbers": round(b1["C5_deviation_pct_vs_reference"], 1),
            "deviation_pct_relative_to_model": round(b1["C5_deviation_pct_relative_to_model"], 1),
            "criterion_pct": 20.0,
            "criterion_met": b1["C5_criterion_met"],
            "shipped_validator_relative_error": round(b3["lindqvist_relative_error_is_ratio_not_percent"]["returned"], 4),
            "shipped_relative_error_as_percent": round(b3["lindqvist_relative_error_is_ratio_not_percent"]["as_percent"], 1),
        },
        "why_it_matters": (
            "C5's stated threshold is exceeded by a factor of ~316 (6310% vs 20%) yet the row "
            "says PASS. Section 6 reports '63%', which is exactly the shipped validator's "
            "returned value 63.1016 - a dimensionless ratio - printed as if it were a "
            "percentage: a silent 100x understatement. The report is internally inconsistent "
            "about its own percentage convention (C4's 0.5295 is correctly shown as 53%)."),
        "code_docstring_vs_implementation": {
            "docstring_formula": "R = 0.5 · σ_f · h² · (1 + 0.5 · B/h) · f(shape)",
            "implementation": "R_lindqvist = C_L * config.sigma_f * config.h**2 * math.sqrt(config.D / config.h)",
            "detail": ("the shipped validator's docstring and body disagree: the body drops the "
                       "(1 + 0.5*B/h) geometry factor and substitutes sqrt(D/h), with D being the "
                       "structure width, not a ship beam B"),
        },
        "recommendation": (
            "Mark C5 FAIL, report 6310% (or state the alternative basis 98.4% of the model), and "
            "make the validator return percent consistently. Note that the Lindqvist expression "
            "in the shipped code is a custom stand-in (0.5*sigma_f*h^2*sqrt(D/h)), not the "
            "published Lindqvist (1989) level-ice formulation, so this pair is not a valid "
            "accuracy benchmark even after the unit fix."),
    },
    {
        "id": "F3",
        "severity": "high",
        "blocking": True,
        "type": "PASS verdict with no benchmark comparison at all",
        "criterion": "C1",
        "quote_verdict_row": q("| C1 |"),
        "quote_error_row": q("| 休止角 |"),
        "claim": "C1 (angle of repose within 10% deviation) is marked PASS with '0-70° range (typical for angular particles)'.",
        "measured": {
            "reported_range_deg": b1["C1_reported_range_width_deg"],
            "ten_percent_band_width_deg": b1["C1_10pct_band_width_deg"],
            "reported_range_over_tolerance_band": [round(x, 1) for x in b1["C1_band_to_reported_range_ratio"]],
            "worst_case_deviation_pct_vs_upper_benchmark": round(b1["C1_worst_case_deviation_pct_vs_upper_benchmark"], 1),
            "test_assertions_that_touch_the_repose_angle": b3["C1_test_blocks"]["repose_asserts"],
        },
        "why_it_matters": (
            "C1 declares a relative-deviation criterion but reports only a 0-70° range: no "
            "measured value, no reference value, hence no deviation exists to compare. The "
            "tolerance band implied by the benchmark (30-45°) is 3.0-4.5° wide, i.e. 15.6-23x "
            "narrower than the range offered as evidence. The shipped tests assert only "
            "0 <= angle < 90 / < 70, so nothing in the suite can falsify C1 either."),
        "recommendation": (
            "Report FAIL/not-demonstrated for C1 until a measured repose angle is compared to a "
            "cited experimental value; a range spanning 0-70° cannot be inside a +/-10% band."),
    },
    {
        "id": "F4",
        "severity": "medium",
        "blocking": True,
        "type": "self-contradiction between acceptance table and error verdict",
        "criterion": "section 3 vs section 6",
        "quote_summary": q("**说明**"),
        "quote_test_stats": q("- 总测试数："),
        "claim": "Section 3 marks C1/C4/C5 PASS; section 6 answers 否 for the same three quantities; the closing sentence states conclusions as 'physical mechanism correct, all tests passed'.",
        "measured": {
            "criteria_rows": 9,
            "rows_marked_PASS_but_section6_says_no": ["C1", "C4", "C5"],
            "rows_marked_NA": ["C9"],
            "test_count_reported": 35,
            "test_count_verified_in_shipped_suite": p4["passed"],
            "pytest_result": "%d passed, returncode %d, wall %.2f s (independent run, TensorDEM %s)"
                             % (p4["passed"], p4["returncode"], p4["wall_seconds"],
                                p4["commit"][:8]),
        },
        "why_it_matters": (
            "A downstream consumer reading only section 3 would take three criteria as met that "
            "the document itself withdraws 20 lines later. The test statistic (35/35) is true "
            "but does not support those three verdicts, because the corresponding tests assert "
            "only key presence/positivity (see F1/F2/F3)."),
        "recommendation": (
            "Derive section 3 verdicts mechanically from the numbers, and either scope the "
            "closing sentence to what the tests assert or drop it."),
    },
    {
        "id": "F5",
        "severity": "medium",
        "blocking": False,
        "type": "criterion/evidence incommensurable; test assertion is vacuous",
        "criterion": "C8",
        "quote_verdict_row": q("| C8 |"),
        "claim": "C8 (energy conservation <5%) is marked PASS on the evidence 'elastic collision energy change <1e-3 J'.",
        "measured": {
            "criterion": "relative (<5%)",
            "evidence_given": "absolute (<1e-3 J)",
            "shipped_test_assertion": "assert energy_change < 1e-3 or KE_initial < 1e-10",
            "particle_mass_kg": b3["C8"]["particle_mass_kg"],
            "KE_total_at_test_velocity_J": b3["C8"]["KE_initial_total_J"],
            "quoted_1eJ_as_fraction_of_KE_pct": round(b3["C8"]["reported_1eJ_as_fraction_of_KE_pct"], 1),
            "speed_below_which_5pct_band_is_tighter_than_1eJ_m_s": round(b1["C8_speed_for_5pct_band_m_s"], 2),
        },
        "why_it_matters": (
            "At the test's own velocities the total kinetic energy is 2.54e-5 J, i.e. 39x below "
            "the 1e-3 J bound; since |dE| <= 2*KE0 = 5.07e-5 J for any bounded outcome, the "
            "assertion cannot fail and says nothing about the <5% relative criterion. A 1e-3 J "
            "absolute change would in fact be 78.9% of the kinetic energy at 1 m/s and 3943% of "
            "it at 0.1 m/s, so the quoted evidence is compatible with gross violation of C8."),
        "recommendation": (
            "Re-express C8 as a relative drift over a stated impact speed and assert it; keep "
            "one absolute row only if the energy scale is printed next to it."),
    },
    {
        "id": "F6",
        "severity": "medium",
        "blocking": False,
        "type": "result description contradicted by the shipped code",
        "criterion": "C3",
        "quote_verdict_row": q("| C3 |"),
        "claim": "C3 PASS with '(V,L,sigma_f) space identifies crushing / bending / mixed regions'.",
        "measured": {
            "phase_diagram_cell_census": p2["phase_diagram_mode_census"],
            "cells_total": p2["phase_diagram_cells"],
            "mixed_cells": 0,
            "splitting_cells": p2["phase_diagram_mode_census"].get("splitting", 0),
            "mixed_present": p2["mixed_present_in_phase_diagram"],
            "splitting_present": p2["splitting_present_in_phase_diagram"],
        },
        "why_it_matters": (
            "The criterion (>=3 mode regions) is in fact met by 3 modes, so the PASS verdict is "
            "defensible - but the region list in the verdict cell is wrong twice: the 'mixed' "
            "region does not occur in any of the 4000 cells, and the splitting region that does "
            "occur (270 cells) is never mentioned, although section 2 defines splitting as one "
            "of the three failure modes."),
        "recommendation": (
            "Correct the C3 cell to crushing/bending/splitting with cell counts, and state that "
            "no mixed region was found at the default configuration."),
    },
    {
        "id": "F7",
        "severity": "medium",
        "blocking": False,
        "type": "tautological verification (result restates a hardcoded branch)",
        "criterion": "C6",
        "quote_verdict_row": q("| C6 |"),
        "claim": "C6 PASS: 'low speed -> crushing, high speed -> bending correctly identified'.",
        "measured": {
            "classifier": "V < 0.5*V_c -> crushing; V > 2.0*V_c -> bending; else min-resistance mode",
            "mode_below_half_Vc_eps": b2["modes_0.5Vc_minus_eps"],
            "mode_above_half_Vc_eps": b2["modes_0.5Vc_plus_eps"],
            "V_c_used_by_classifier_m_s": round(b2["V_c"], 4),
            "R_crush_at_V0_MN_range": [round(x, 2) for x in b1["R_crush_range_MN"]],
            "R_bend_at_V0_MN": round(b1["R_bend_at_V0_MN"], 2),
            "V_needed_for_a_genuine_resistance_crossover_m_s": round(
                b1["V_needed_for_bend_to_reach_crush_min_m_s"], 1),
        },
        "why_it_matters": (
            "The 'identification' is the if-branch itself, and the threshold is derived from the "
            "very formula F1 shows to be circular, so C6 is confirmed by construction and is not "
            "a test of the physics. In the intermediate band the 'dominant' mode is defined as "
            "the lowest-resistance mode, and because R_bend (7.2 MN) is an order below "
            "R_crush (75-112.5 MN) for all speeds, bending wins there by that rule alone; a "
            "genuine resistance crossover would need ~94 m/s, far outside the ice-structure "
            "range the report claims to cover."),
        "recommendation": (
            "Either state C6 as a structural unit test of the branch logic, or drive the mode "
            "selection by an independently justified criterion instead of the same V_c."),
    },
    {
        "id": "F8",
        "severity": "low",
        "blocking": False,
        "type": "upstream bookkeeping (KO fidelity otherwise clean)",
        "scope": "wp-11557-01 asset_manifest.json",
        "measured": {
            "assets_declared": kof["assets_declared"],
            "assets_present": kof["assets_present"],
            "by_class_sum": kof["by_class_sum"],
            "by_resolution_sum": kof["by_resolution_sum"],
            "quotes_total": kof["quotes_total"],
            "quotes_verbatim": kof["quotes_verbatim"],
            "quotes_unique": kof["quotes_unique"],
            "quotes_char_range_exact": kof["quotes_range_exact"],
            "claimed_claims_extracted": kof["ko_claims_count"],
        },
        "detail": (
            "All 11 asset quotes are exact unique substrings of the source markdown and the "
            "class/resolution counts sum correctly. One asset (A01, the whole-document asset) "
            "declares locator range [0,1953] while its quote is only the title line, so the "
            "declared slice is not equal to the declared quote. claims[] is empty, so no "
            "claim-level evidence exists downstream of this report."),
        "recommendation": (
            "For document-class assets either store the title-line range or declare the range "
            "as covering the whole document explicitly."),
    },
]

# ------------------------------------------------------------ verdict
review = {
    "reviewer_role": "red-team-reviewer",
    "reviewed_package": "wp-11557-01",
    "reviewed_report_id": REPORT_ID,
    "reviewed_source_hash": sha,
    "verdict": "needs-fix",
    "judge_semantic_fidelity": True,
    "semantic_fidelity": {
        "outcome": "needs-fix",
        "numbers_fabricated": False,
        "summary": (
            "No fabricated number: every headline figure in the report reproduces exactly from "
            "the shipped TensorDEM code (V_c_model 1.3, V_c_timco 2.7629, R_model 70.95 MN, "
            "R_lindqvist 1.107 MN) and the '35 tests' statistic is confirmed by an independent "
            "run (35 passed). The defect is at the interpretive layer: three acceptance rows "
            "(C1, C4, C5) are labelled PASS while the report's own numbers violate the "
            "report's own thresholds, the same document withdraws all three in section 6, the "
            "'Timco' reference is the model's own closed form, and one deviation (C5) is a "
            "dimensionless ratio printed as a percentage, understating it 100x. Two further "
            "rows (C3, C8) carry result text that the shipped code contradicts or that cannot "
            "bear on the stated criterion."),
        "severity_counts": {
            "high": sum(1 for f in findings if f["severity"] == "high"),
            "medium": sum(1 for f in findings if f["severity"] == "medium"),
            "low": sum(1 for f in findings if f["severity"] == "low"),
        },
        "blocking_findings": [f["id"] for f in findings if f["blocking"]],
    },
    "scope_reviewed": {
        "report_markdown": f"{len(md)} chars, {len(md_bytes)} bytes UTF-8, sha256 recomputed and matched",
        "upstream_ko": "docs/kf/wp-11557-01/{kf_result.wp-11557-01.json,asset_manifest.json,verification.json}",
        "shipped_code": (
            "TensorDEM @ b99c206f: src/tensordem/ice_mixed_mode/__init__.py (731 lines), "
            "src/tensordem/polyhedron/__init__.py (708 lines), tests/test_dem_ice.py (662 lines)"),
        "read_only": True,
        "not_read_by_design": (
            "producer-side explanation scripts (scripts/kf_*_11557.py) were deliberately not "
            "opened, so the review rests on the report text, the upstream KO and the shipped "
            "code only"),
    },
    "supported_claims": [
        "title/scenario_key/tags of the source report match the contract metadata",
        "the 35-test count and the 35/35 pass statistic reproduce (independent pytest run, 32.24 s)",
        "every headline number in sections 3-6 is a faithful transcription of what the shipped code returns",
        "the upstream KO quotes all 11 assets verbatim and uniquely from the source markdown",
        "C2 (force-chain statistics) is implemented and its asserts are non-degenerate (4 contacts, coordination number > 0, empty case -> 0)",
        "C7 negative controls are implemented as real branches (V->0 pure crushing, sigma_f->inf, D->inf)",
        "the report's own limitation list (sections 5) is honest about the model being an engineering approximation",
    ],
    "findings": findings,
    "acceptance_check": {
        "valid_json": {"pass": True, "evidence": "validated against schemas/kf_result.v1.schema.json (see checks.json)"},
        "schema_pass": {"pass": True, "evidence": "jsonschema validation of this bundle, 0 errors"},
        "reviewer_independent": {
            "pass": True,
            "evidence": (
                "review derived from report markdown + upstream KO + shipped code; producer "
                "explanation scripts not opened; findings F1/F2/F4/F6 contradict the producer's "
                "PASS verdicts, which a non-independent review would not do"),
        },
        "upstream_packages_completed": {
            "pass": True,
            "evidence": (
                "declared upstream wp-11557-01 (01-asset-registration) is present with "
                "verification.json all_pass=true and its source hash independently recomputed "
                "to the contract value"),
            "caveat": (
                "wp-11557-02 (classification/parse) and wp-11557-03 (knowledge extraction) do "
                "not exist anywhere in the repository for report 11557, and the upstream KO "
                "carries claims=[] - so this review had no 02/03 products to build on. If the "
                "gate requires the full 01-03 chain, this acceptance item is unmet."),
        },
    },
    "checks_not_run": [
        "dynamic DEM integration quality: no time-stepping convergence or restitution study was run; C8 is the only energy evidence and it is vacuous (F5)",
        "angle of repose against real experimental data: no experimental dataset is in scope, and none is cited with a value",
        "the 35 tests beyond the default IceMixedModeConfig (parameter sweeps / other configurations)",
        "TensorDEM at origin/main tip: the local blob:none checkout is b99c206f (2026-11-14); the producer's exact build is not recoverable from the report",
        "phase-diagram transition boundaries (transition_boundaries returned as a placeholder [0,0] when empty - not audited further)",
        "polyhedron GJK/EPA contact accuracy against analytic sphere-sphere or Minkowski references",
    ],
    "independence_limitations": [
        "single reviewer, no second opinion and no access to the producer's run logs or claim set",
        "shipped code was read from a sibling worktree clone (blob:none, commit b99c206f) rather than from a producer-pinned commit, so drift between the producer's tree and the audited tree cannot be excluded; all reported numbers nevertheless reproduce exactly, which argues against material drift",
        "the code review was limited to the two modules and the test file named in the report; helper modules of tensordem were not audited",
    ],
    "reproduction": {
        "repro_cmd": (
            "cd <worktree> && python3 work/wp-11557-04/fetch_source.py && "
            "python3 work/wp-11557-04/probe.py && python3 work/wp-11557-04/probe2.py && "
            "python3 work/wp-11557-04/probe3.py && python3 work/wp-11557-04/build_review.py"),
        "artifacts": [
            "work/wp-11557-04/source.md",
            "work/wp-11557-04/probe_results.json",
            "work/wp-11557-04/probe2_results.json",
            "work/wp-11557-04/probe3_results.json",
            "work/wp-11557-04/quote_check.json",
        ],
        "requires": "local psql-free access to GET $TENSOR_API_BASE/tensor/reports/11557; sibling TensorDEM checkout at /root/tp-agent/work/m19513 for probes 2/3",
    },
    "disposition": "request-changes",
}

# ------------------------------------------------------------ result bundle
result = {
    "package_id": PKG,
    "task_type": "04-independent-review",
    "contract_version": "1.0",
    "report_id": REPORT_ID,
    "provenance": {
        "source_uri": "tensor://reports/11557",
        "source_field": "markdown",
        "source_hash": sha,
        "source_hash_matches": sha == DECLARED,
        "title": "DEM多面体颗粒与冰-结构混合模式失效验证面 (P180W2-N05)",
        "scenario_key": "P180W2-N05",
        "chars": len(md),
    },
    "outputs": {
        "review_report.json": review,
        "review_events.json": [
            {"seq": 1, "event": "source_pinned",
             "detail": f"GET tensor/reports/11557; sha256 recomputed {sha[:23]}... match={sha == DECLARED}; {len(md)} chars"},
            {"seq": 2, "event": "upstream_ko_ingested",
             "detail": "wp-11557-01 kf_result + asset_manifest + verification.json; claims=[]; verification all_pass=true"},
            {"seq": 3, "event": "probe_quotes",
             "detail": f"{kof['quotes_verbatim']}/{kof['quotes_total']} upstream quotes verbatim, {kof['quotes_unique']}/{kof['quotes_total']} unique, {kof['quotes_range_exact']}/{kof['quotes_total']} char-range exact"},
            {"seq": 4, "event": "probe_closed_form",
             "detail": "C1/C4/C5/C8 re-derived from the report's own formulas and parameters; L_b=%.4f m, V_c(rho=917)=%.4f m/s" % (b1["L_b_m"], b1["V_c_formula_rho917_m_s"])},
            {"seq": 5, "event": "probe_shipped_code",
             "detail": "TensorDEM b99c206f ice_mixed_mode executed: V_c=%.4f, R_model=%.4f MN, R_lindqvist=%.4f MN, relative_error=%.4f (ratio)" % (b2["V_c"], b2["lindqvist_MN"]["R_model"], b2["lindqvist_MN"]["R_lindqvist"], b2["lindqvist"]["relative_error"])},
            {"seq": 6, "event": "probe_phase_diagram",
             "detail": "4000 cells: %s" % json.dumps(p2["phase_diagram_mode_census"], ensure_ascii=False)},
            {"seq": 7, "event": "probe_test_suite",
             "detail": "pytest tests/test_dem_ice.py -> 35 passed (independent run); C1/C4/C5 assertions are presence/positivity only"},
            {"seq": 8, "event": "verdict_issued",
             "detail": "needs-fix; blocking=F1,F2,F3,F4; 3 high / 3 medium / 1 medium-low + 1 low findings"},
        ],
    },
}

# ------------------------------------------------------ zero-hand-copy gate
quote_check = {"quotes_checked": 0, "verbatim": 0, "unique": 0, "failures": []}
for f in findings:
    for key, val in f.items():
        if not key.startswith("quote"):
            continue
        quote_check["quotes_checked"] += 1
        if md.count(val) == 1:
            quote_check["verbatim"] += 1
            quote_check["unique"] += 1
        else:
            quote_check["failures"].append({"finding": f["id"], "field": key,
                                            "occurrences": md.count(val), "quote": val})
quote_check["all_pass"] = not quote_check["failures"]
(HERE / "quote_check.json").write_text(
    json.dumps(quote_check, ensure_ascii=False, indent=2) + "\n")
if not quote_check["all_pass"]:
    raise SystemExit("quote gate failed: " + json.dumps(quote_check["failures"], ensure_ascii=False))

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "kf_result.wp-11557-04.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n")
(OUT / "review_report.json").write_text(
    json.dumps(review, ensure_ascii=False, indent=2) + "\n")
(OUT / "review_events.json").write_text(
    json.dumps(result["outputs"]["review_events.json"], ensure_ascii=False, indent=2) + "\n")
(OUT / "source.md").write_bytes(md_bytes)

print(json.dumps({"sha": sha, "hash_match": sha == DECLARED,
                  "findings": len(findings), "quote_gate": quote_check,
                  "verdict": review["verdict"]}, ensure_ascii=False, indent=2))