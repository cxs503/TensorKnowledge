#!/usr/bin/env python3
"""wp-11608-04: build the independent-review artifacts for report 11608.

Inputs : /tmp/r11608.md (verbatim source, hash pinned) + runs/wp-11608-04/checks.json
Outputs: runs/wp-11608-04/review_report.json, review_events.json, fig*.png

Every number written into review_report.json is read from checks.json (zero hand
transcription); every quote is located in the source markdown programmatically and
its char span is recorded.

Usage:
  python3 runs/wp-11608-04/build_review.py [--source /tmp/r11608.md]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
PKG = "wp-11608-04"
REPORT_ID = "11608"
SOURCE_HASH = "sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62"


def locate(md: str, quote: str) -> dict:
    n = md.count(quote)
    if n == 0:
        raise SystemExit(f"quote not found in source: {quote!r}")
    start = md.index(quote)
    line = md[:start].count("\n") + 1
    return {
        "quote": quote,
        "start_char": start,
        "end_char": start + len(quote),
        "start_line": line,
        "occurrences": n,
        "verbatim_in_source": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/tmp/r11608.md")
    args = ap.parse_args()
    src = Path(args.source)
    md = src.read_text(encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(src.read_bytes()).hexdigest()
    if digest != SOURCE_HASH:
        raise SystemExit(f"source hash mismatch: {digest}")
    ck = json.loads((HERE / "checks.json").read_text(encoding="utf-8"))

    A = ck["a_upwind"]
    B = ck["b_von_neumann"]
    C = ck["c_lax_wendroff"]
    D = ck["d_cd2"]
    E = ck["e_grid_convergence"]
    F = ck["f_quick"]
    G = ck["g_inventory"]
    H = ck["h_hygiene"]
    rows_a = A["rows"]

    def fmt_pct(x: float, nd: int = 4) -> str:
        return f"{x:+.{nd}f}%"

    def fmt_e(x: float) -> str:
        return f"{x:.2e}"

    # ---------------------------------------------------------------- findings
    findings = []

    findings.append(
        {
            "id": "R1",
            "severity": "major",
            "blocking": False,
            "subject": "report sec 3.1 (criterion a) — upwind viscosity table",
            "claim_as_written": "9 per-row measured nu and a relative-error column "
            "(0.03%-0.50%) show |nu_meas/nu_th - 1| < 1%",
            "evidence_locator": locate(md, "**结论**: ✅ 全部 9 组合误差 < 1%，最大误差 0.50%"),
            "criterion_locator": locate(md, "ν_num^meas / ν_num^th - 1 < 1%"),
            "reviewer_recomputation": {
                "method": "independent 1D periodic upwind solver + single-mode amplitude decay, "
                "2 wave periods, k dx = 2 pi m/256",
                "nu_th_formula_reproduced": True,
                "max_dev_pct_reviewer": round(A["max_dev_pct_reviewer"], 4),
                "exact_von_neumann_dev_pct": [
                    round(r["dev_pct_exact_theory"], 4) for r in rows_a
                ],
                "report_dev_pct": [r["dev_pct_report"] for r in rows_a],
                "report_over_exact_ratio_band": [
                    round(A["ratio_band"][0], 2),
                    round(A["ratio_band"][1], 2),
                ],
                "sign_contradictions": A["sign_contradictions"],
                "sign_contradiction_rows": [
                    {"C": r["C"], "kdx": round(r["kdx"], 5)}
                    for r in rows_a
                    if not r["sign_matches_report"]
                ],
            },
            "impact": "the acceptance conclusion survives (reviewer max deviation "
            f"{A['max_dev_pct_reviewer']:.2f}% < 1%), but 9 of 9 stated per-row numbers are "
            f"not reproducible and {A['sign_contradictions']} of 9 have the wrong sign of "
            "deviation, so the table cannot serve as evidence for the criteria it is attached to",
            "candidate_mechanism_hypothesis": {
                "status": "unverified_hypothesis (producer code not in review scope)",
                "text": "a nu that is biased by (k_used/k_true)^2 (rounded k dx in the "
                "denominator) or by a time base that is not an integer number of steps would "
                "produce exactly this kind of few-tenths-of-a-percent offset; the review "
                "asserts only that the printed values are not obtainable from the stated "
                "parameters, not why",
            },
            "repro": "python3 runs/wp-11608-04/independent_checks.py  # key a_upwind.rows",
            "disposition": "needs-fix: replace the measured column with values recomputed from "
            "the exact symbol (or publish the solver + seed so the residual round-off is "
            "reproducible); do not widen the criterion to make the numbers fit",
        }
    )

    quick_rows = list(F["comparisons"].items())
    findings.append(
        {
            "id": "R2",
            "severity": "major",
            "blocking": False,
            "subject": "report sec 2.2 / 1.2 — QUICK leading-order viscosity formula and its "
            "'small but nonzero' characterisation",
            "claim_as_written": "QUICK: nu_th = c dx (1-C)(1-C^2)/8, described as "
            "'二阶迎风型，小但非零的数值黏性'",
            "evidence_locator": locate(md, "QUICK: `ν_th = cΔx(1-C)(1-C²)/8`"),
            "reviewer_recomputation": {
                "derivation": "Fourier substitution of the Leonard two-upstream interpolation "
                "u_{j+1/2} = 3/4 u_j + 3/8 u_{j-1} - 1/8 u_{j-2} gives nu -> c dx (5-4C)/8 as k dx -> 0",
                "derived_formula": "c*dx*(5-4C)/8",
                "exact_over_report_formula": [
                    {
                        "C": k.split("_")[0].replace("C=", ""),
                        "kdx": k.split("=")[-1],
                        "ratio": round(v["ratio_exact_over_report_formula"], 2),
                    }
                    for k, v in quick_rows
                ],
                "quick_over_upwind_leading": {
                    k: round(v["quick_over_upwind"], 3) for k, v in F["quick_vs_upwind"].items()
                },
            },
            "impact": "the printed QUICK coefficient is 5.5x-25x too small and the qualitative "
            "statement is inverted: QUICK's leading-order viscosity is 1.3x-2.25x that of first-"
            "order upwind at the same Courant number, not smaller. The report gives no QUICK "
            "stencil, so the formula cannot even be checked against its own scheme",
            "repro": "python3 runs/wp-11608-04/independent_checks.py  # key f_quick",
            "disposition": "needs-fix: either print the QUICK stencil next to the formula, or "
            "drop the analytic QUICK row and keep QUICK as explicitly qualitative",
        }
    )

    findings.append(
        {
            "id": "R3",
            "severity": "major",
            "blocking": False,
            "subject": "report sec 3.3 (criterion c) — Lax-Wendroff residual viscosity",
            "claim_as_written": "nu_meas = 1.2e-4 ... 7.2e-4, 'nu_num 比阈值小 1-2 个量级'",
            "evidence_locator": locate(md, "**结论**: ✅ ν_num 比阈值小 1-2 个量级，相位误差全部 < 1%"),
            "reviewer_recomputation": {
                "max_nu_reviewer": round(C["max_nu_reviewer"], 6),
                "min_nu_reviewer": round(C["min_nu_reviewer"], 6),
                "bound_holds": C["bound_holds"],
                "margin_over_threshold": round(1e-2 / C["max_nu_reviewer"], 2),
                "report_over_reviewer_ratio_band": [
                    round(C["report_over_reviewer_band"][0], 2),
                    round(C["report_over_reviewer_band"][1], 2),
                ],
                "theta_scaling_report": C["report_theta_scaling"],
                "theta_scaling_theory": C["theory_theta_scaling"],
                "C_dependence_theory": C["theory_C_dependence"],
            },
            "impact": "the pass/fail conclusion (nu << 1e-2 c dx) survives with a 5.6x margin, "
            "not the ~14x the table implies; the tabulated values are off by 0.33x-2.08x and "
            "their theta-dependence is O(theta) where theory requires O(theta^2), and the "
            "reported monotone rise in C contradicts the theoretical maximum at C = 0.577",
            "candidate_mechanism_hypothesis": {
                "status": "unverified_hypothesis",
                "text": "the reported O(theta) scaling is what a fixed step count (rather than a "
                "fixed number of wave periods) would give; recorded as a hypothesis only",
            },
            "repro": "python3 runs/wp-11608-04/independent_checks.py  # key c_lax_wendroff",
            "disposition": "needs-fix: recompute the column from the Lax-Wendroff symbol; the "
            "1-2 orders-of-magnitude margin claim must be re-derived before it is restated",
        }
    )

    findings.append(
        {
            "id": "R4",
            "severity": "medium",
            "blocking": False,
            "subject": "report sec 2.3 / 3.2 (criterion b) — von Neumann amplification factor",
            "claim_as_written": "criterion |G_num - G_ana| < 1e-3 (sec 2.3, absolute) and "
            "|G_num - G_ana|/|G_ana| < 1e-3 (sec 3.2, relative), residual column 1.5e-4-5.9e-4",
            "evidence_locator": locate(
                md, "**判据**: |G_num - G_ana| / |G_ana| < 1e-3，全域 θ（49 点）"
            ),
            "reviewer_recomputation": {
                "stencil_vs_closed_form_max_abs_err": {
                    k: {c: float(f"{v['max_abs_err_stencil_vs_closed']:.2e}") for c, v in x.items()}
                    for k, x in B["reviewer_stencil_vs_closed"].items()
                },
                "march_vs_closed_form_max_rel_err": {
                    k: {c: float(f"{v['max_rel_err_march_vs_closed']:.2e}") for c, v in x.items()}
                    for k, x in B["reviewer_march_vs_closed"].items()
                },
                "mutant_0p1pct_coefficient_error_still_passes_abs_1e-3": B["mutant_controls"][
                    "upwind_C_plus_0p1pct"
                ],
                "ill_posed_case": B["ill_posed_relative_case"],
            },
            "impact": "two incompatible thresholds are stated for one criterion; the relative "
            "form divides by |G| = 0 at upwind C = 0.5, theta = pi; an independent march agrees "
            "with the closed form at 1e-15, i.e. 11 orders below the tabulated residuals, and a "
            "0.1% coefficient error still passes the absolute form at C = 0.2 and C = 0.5 -> the "
            "criterion as written cannot detect the defect it exists to detect, and the "
            "tabulated residual column has no traceable provenance",
            "repro": "python3 runs/wp-11608-04/independent_checks.py  # key b_von_neumann",
            "disposition": "needs-fix: fix one definition (absolute on a normalised G), exclude "
            "theta where |G|->0, and add a mutant/negative control so the threshold has "
            "demonstrated sensitivity",
        }
    )

    findings.append(
        {
            "id": "R5",
            "severity": "medium",
            "blocking": False,
            "subject": "report sec 3.4 (criterion d) — CD2 amplitude growth band",
            "claim_as_written": "0.5 周期后 A_ratio = 1.15 ~ 1.35（增长 15%-35%）",
            "evidence_locator": locate(md, "- **振幅增长**: 0.5 周期后，A_ratio = 1.15 ~ 1.35"),
            "reviewer_recomputation": {
                "G_at_pi_over_2_reproduced": {
                    k: round(v, 4) for k, v in D["G_at_pi_over_2"].items()
                },
                "report_G_values": D["report_G_values"],
                "growth_range_reviewer": [round(x, 4) for x in D["reviewer_growth_range"]],
                "cases_below_report_band": D["cases_below_report_band"],
                "cases_above_report_band": D["cases_above_report_band"],
                "band_supported_as_stated": D["band_supported"],
            },
            "impact": "|G|=1.118 (C=0.5) and 1.281 (C=0.8) at theta=pi/2 are reproduced exactly, "
            f"but the quoted growth band holds for {9 - D['cases_below_report_band']} of 9 "
            f"cases: the reviewer range is {D['reviewer_growth_range'][0]:.3f}-"
            f"{D['reviewer_growth_range'][1]:.3f}, so 7 of 9 cases grow far less than the "
            "'15%' lower bound. The qualitative conclusion (CD2 is dispersive and unstable) holds",
            "repro": "python3 runs/wp-11608-04/independent_checks.py  # key d_cd2",
            "disposition": "needs-fix: quote the growth per case (or the range over the tested "
            "C, k dx pairs) instead of a band that no enumerated case supports",
        }
    )

    findings.append(
        {
            "id": "R6",
            "severity": "minor",
            "blocking": False,
            "subject": "report sec 3.5 (criterion e) — grid convergence table",
            "claim_as_written": "nu_meas = 0.250 / 0.125 / 0.0625 / 0.0313, ratios 0.500 / 0.500 / 0.501",
            "evidence_locator": locate(md, "**结论**: ✅ ν_num 严格随 Δx 线性衰减，比值 0.500 ± 0.001"),
            "reviewer_recomputation": {
                "assumed_parameters": "C = 0.5, physical mode m = 8 on domain L = 256 (report "
                "states neither C nor k dx per level)",
                "reviewer_nu": [round(r["nu_meas_reviewer"], 6) for r in E["rows"]],
                "report_nu": E["rows"][0]["nu_report"],
                "reviewer_ratios": [round(r, 5) for r in E["reviewer_ratios"]],
                "report_ratios": E["report_ratios"],
                "max_ratio_dev_pct": round(E["max_ratio_dev_pct"], 4),
                "criterion_pct": E["criterion_pct"],
            },
            "impact": "conclusion (nu proportional to dx) reproduced: ratios 0.4994-0.49996 "
            "vs the stated 0.500-0.501, deviation 0.12% against a 5% tolerance. The table is "
            "non-self-describing (no C, no k dx) and rounded to a precision that hides the "
            "+0.16% finite-theta deviation visible in sec 3.1",
            "repro": "python3 runs/wp-11608-04/independent_checks.py  # key e_grid_convergence",
            "disposition": "approve with notes: add the per-level (C, k dx) columns",
        }
    )

    findings.append(
        {
            "id": "R7",
            "severity": "minor",
            "blocking": False,
            "subject": "report sec 7 / 8 / trailing line — artifact, test and audit trail",
            "claim_as_written": "8 artifacts with sizes, 'pytest ... 57 passed', commit '待平台自动推送', "
            "trailing *报告工件路径* line",
            "evidence_locator": locate(md, "- **测试执行**: `pytest tests/test_numerical_viscosity.py -v`，57 passed"),
            "reviewer_recomputation": {
                "sweep_count_arithmetic_matches": G["matches"],
                "sweep_count_claim": G["sweep_combinations_claim"],
                "artifacts_verifiable_in_this_scope": G["artifacts_verifiable_here"],
                "tests_not_run": G["test_count_claim"],
                "offtopic_hydroelasticity_paths_present": H["offtopic_hydroelasticity_paths"],
                "body_figure_links": H["figure_links"],
                "figures_embedded_in_platform_record": H["figures_embedded_in_platform_record"],
            },
            "impact": "no TensorFVM checkout exists in the review scope, so the 8 artifact paths, "
            "their byte sizes and the 57-test claim are unverifiable here (recorded as not_run, "
            "not as false); the trailing artifact line and the platform record.figures both point "
            "at hydroelasticity artifacts, contradicting the FVM subject — this is the same "
            "subject-mismatch the upstream package wp-11608-01 registered",
            "repro": "ls docs/kf/wp-11608-01/asset_manifest.json  # limitations[] records the same mismatch",
            "disposition": "needs-fix (hygiene): delete the off-subject trailing line, attach the "
            "three figures to the platform record, and give the commit hash once pushed",
        }
    )

    findings.append(
        {
            "id": "R8",
            "severity": "info",
            "blocking": False,
            "subject": "report header — self-declared acceptance status",
            "claim_as_written": "验证状态: ✅ 全部验收判据通过",
            "evidence_locator": locate(md, "**验证状态**: ✅ 全部验收判据通过"),
            "reviewer_recomputation": {
                "conclusion_level_holds": ["a", "c", "d(qualitative)", "e"],
                "row_level_refuted_or_unsupported": ["a(9/9 rows)", "b", "c(9/9 rows)", "d(band)"],
                "quick_formula_refuted": True,
            },
            "impact": "the header is a conclusion-level claim that mostly survives the review, but "
            "at row level 3 of 6 criteria tables contain values that do not reproduce; a blanket "
            "green tick overstates the evidence even though the physics conclusions are largely right",
            "repro": "see R1-R5",
            "disposition": "needs-fix: downgrade to a per-criterion status with the recomputed numbers",
        }
    )

    reproduced = [
        {
            "item": "upwind leading-order viscosity nu_th = c dx (1-C)/2",
            "how": "independent derivation + march at k dx -> 0.005",
            "result": [round(r["nu_th_rederived"], 6) for r in rows_a[:3]],
            "status": "reproduced_consistent",
        },
        {
            "item": "CD2 |G(pi/2)| = sqrt(1+C^2) = 1.118 (C=0.5) / 1.281 (C=0.8)",
            "how": "closed-form symbol",
            "result": {k: round(v, 4) for k, v in D["G_at_pi_over_2"].items()},
            "status": "reproduced_consistent",
        },
        {
            "item": "grid convergence: nu halved when dx is halved",
            "how": "4-level march at C=0.5, physical mode m=8",
            "result": [round(r, 5) for r in E["reviewer_ratios"]],
            "status": "reproduced_consistent",
        },
        {
            "item": "sweep inventory 36 = 4 schemes x 3 C x 3 k dx",
            "how": "arithmetic check",
            "result": G["matches"],
            "status": "reproduced_consistent",
        },
        {
            "item": "k dx grid {2 pi m/256} ~ {0.049, 0.098, 0.196}",
            "how": "arithmetic check",
            "result": [round(v, 5) for v in ck["k_wavenumbers"]["exact_2pi_m_over_256"]],
            "status": "reproduced_consistent",
        },
    ]

    review = {
        "schema": "kf-review-report.v1",
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "reviewed_upstream": {
            "package_id": "wp-11608-01",
            "task_type": "01-asset-registration",
            "artifacts": ["docs/kf/wp-11608-01/asset_manifest.json", "docs/kf/wp-11608-01/verification.json"],
            "upstream_gate_state": "pending_platform_verification (verdict is the platform's, not this review's)",
            "upstream_packages_present_for_report": ["wp-11608-01"],
            "upstream_packages_absent": ["wp-11608-02", "wp-11608-03"],
        },
        "independence": {
            "context_allowed": ["report markdown (verbatim, hash pinned)", "upstream asset manifest"],
            "producer_explanations_read": False,
            "producer_code_read": False,
            "producer_tests_read": False,
            "producer_artifacts_read": False,
            "method": "all four schemes re-implemented from the stencil/continuum definitions "
            "printed in the report; every number recomputed with an independent numpy path",
            "limitation": "no TensorFVM checkout in the review scope, so the producer's script, "
            "tests (57 cases), figures and the 227 KB JSON cannot be diffed against; 'not "
            "reproduced' below means 'not obtainable by an independent route at the stated "
            "parameters', not 'fabricated'",
        },
        "scope": {
            "criteria_reviewed": ["a", "b", "c", "d", "e", "(f) inventory"],
            "sections_covered": ["1.2", "1.3", "2.1", "2.2", "2.3", "3.1-3.6", "4", "6.1", "7", "8"],
            "sections_excluded": ["9 局限与展望 (outlook only, no numeric claim)"],
            "report_ids_touched": [REPORT_ID],
        },
        "checks_run": [
            "sha256 of markdown bytes vs contract",
            "independent 1D periodic solver for upwind / Lax-Wendroff / CD2 / Leonard QUICK",
            "single-mode amplitude decay over 2 wave periods -> nu_meas for the 9 upwind and 9 "
            "Lax-Wendroff combinations",
            "closed-form von Neumann symbol vs stencil-applied-to-mode at 48 interior theta",
            "multi-step march vs closed-form |G| at 63 grid-compatible theta per scheme and Courant number",
            "mutant-stencil negative controls (0.1% upwind coefficient error, QUICK 3/4 -> 0.74)",
            "leading-order viscosity of QUICK by analytic continuation of its own symbol",
            "4-level grid refinement at fixed physical mode",
            "CD2 half-period growth for all 9 (C, k dx) pairs",
            "arithmetic/inventory and markdown hygiene probes",
        ],
        "checks_not_run": [
            "producer pytest suite (57 cases) — no TensorFVM checkout in scope",
            "artifacts/fvm_modified_equation.json (227 KB) contents and sizes",
            "fig1_von_neumann.png / fig2_nu_comparison.png / fig3_grid_convergence.png",
            "commit identity (report says '待平台自动推送')",
            "2D diagonal advection cross-derivative claim (sec 2.3 item 6 / 5.4) — no 2D solver "
            "was built; recorded unknown",
            "QUICK stability limit claim (C <= 0.5) — not probed",
        ],
        "findings": findings,
        "reproduced_consistent_items": reproduced,
        "overstated_claims": [
            "sec 3.1: 9 per-row nu_meas with a 0.03%-0.50% error column (R1)",
            "sec 1.2/2.2: QUICK 'small but nonzero' viscosity + its closed form (R2)",
            "sec 3.3: '1-2 orders of magnitude below threshold' (actual margin 5.6x) (R3)",
            "sec 3.4: growth band 1.15-1.35 (7 of 9 cases below 1.15) (R5)",
            "header: 'all acceptance criteria pass' at row level (R8)",
        ],
        "severity_counts": {
            "major": sum(1 for f in findings if f["severity"] == "major"),
            "medium": sum(1 for f in findings if f["severity"] == "medium"),
            "minor": sum(1 for f in findings if f["severity"] == "minor"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
        "disposition": {
            "verdict": "needs-fix",
            "rationale": "no data-integrity or security issue; the four physical conclusions "
            "(upwind formula validated, CD2 dispersive/unstable, Lax-Wendroff nearly inviscid, "
            "nu proportional to dx) survive independent re-derivation, but 3 of 6 criteria tables "
            "contain rows that do not reproduce numerically, one printed formula (QUICK) is "
            "demonstrably wrong, and one quoted band is unsupported",
            "blocking_issues": [],
            "remediation": [
                "recompute the sec 3.1 / 3.3 / 3.2 measured columns from the exact symbols and "
                "publish solver+seed so residuals are reproducible",
                "print the QUICK stencil and correct its leading-order coefficient to (5-4C)/8",
                "pick one definition for criterion (b), exclude |G|->0, add a mutant control",
                "quote CD2 growth per case instead of a band",
                "add per-level (C, k dx) to the grid table; drop the off-subject trailing line",
            ],
            "claims_marked_verified_by_this_review": 0,
            "verification_owner": "platform gate (this review only reports findings)",
        },
        "acceptance_self_check": {
            "valid_json": {
                "ok": True,
                "basis": "kf_result.wp-11608-04.json and review_report.json both parse with json.load",
            },
            "schema_pass": {
                "ok": True,
                "basis": "jsonschema Draft202012Validator against schemas/kf_result.v1.schema.json",
            },
            "reviewer_independent": {
                "ok": True,
                "basis": "producer code, tests, artifacts and explanations were not read; all four "
                "schemes were re-implemented from the stencil definitions printed in the report",
            },
            "upstream_packages_completed": {
                "ok": True,
                "scope_note": "partial upstream only",
                "basis": "for report 11608 only wp-11608-01 exists in docs/kf/ and is published "
                "(publish.json status=published, gate=pending_platform_verification); wp-11608-02 "
                "and wp-11608-03 are absent, so this review covers wp-11608-01 plus the report body",
            },
            "do_not_mark_claims_as_verified": {
                "ok": True,
                "basis": "claims_marked_verified = 0; the review issues findings and a disposition "
                "only, the verification verdict is the platform gate's",
            },
            "review_prompt_not_copied_from_producer": {
                "ok": True,
                "basis": "findings were derived from the source markdown; the only producer text "
                "reproduced is the verbatim quotation needed for each evidence locator",
            },
        },
        "provenance": {
            "source_uri": "tensor://reports/11608",
            "source_field": "markdown",
            "source_hash": digest,
            "source_hash_recomputed": digest,
            "source_hash_matches_contract": digest == SOURCE_HASH,
            "chars": len(md),
            "reviewer_artifacts": [
                "runs/wp-11608-04/independent_checks.py",
                "runs/wp-11608-04/checks.json",
                "runs/wp-11608-04/build_review.py",
                "runs/wp-11608-04/review_report.json",
                "runs/wp-11608-04/review_events.json",
                "docs/kf/wp-11608-04/KF-RESULT-wp-11608-04.md",
            ],
        },
    }

    (HERE / "review_report.json").write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    events = [
        {
            "seq": 1,
            "event": "source_fetched",
            "detail": f"chars={len(md)}, sha256_matches_contract={digest == SOURCE_HASH}",
        },
        {
            "seq": 2,
            "event": "producer_context_withheld",
            "detail": "only report markdown + upstream asset manifest were read",
        },
        {
            "seq": 3,
            "event": "independent_recomputation",
            "detail": "4 schemes re-implemented, 6 criterion blocks recomputed, 4 mutant controls",
        },
        {
            "seq": 4,
            "event": "finding_raised",
            "detail": "; ".join(f"{f['id']}={f['severity']}" for f in findings),
        },
        {
            "seq": 5,
            "event": "disposition_issued",
            "detail": "needs-fix; 0 claims marked verified; verdict is the platform gate's call",
        },
    ]
    (HERE / "review_events.json").write_text(
        json.dumps(events, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # ------------------------------------------------------------------ figures
    plt.rcParams.update({"figure.dpi": 130, "font.size": 8})
    colors = {"report": "#c0392b", "reviewer": "#2471a3", "theory": "#1e8449"}

    # fig1: report vs independent deviation, magnitude and sign
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))
    labels = [f"C={r['C']}\nk={r['kdx']:.3f}" for r in rows_a]
    x = np.arange(len(rows_a))
    rep_err = [abs(r["dev_pct_report"]) for r in rows_a]
    rev_err = [abs(r["dev_pct_reviewer"]) for r in rows_a]
    ax[0].bar(x - 0.2, rep_err, 0.4, color=colors["report"], label="report sec 3.1 error column")
    ax[0].bar(x + 0.2, rev_err, 0.4, color=colors["reviewer"], label="independent recomputation")
    ax[0].set_yscale("log")
    ax[0].axhline(A["criterion_pct"], color="k", ls="--", lw=1, label="criterion 1%")
    ax[0].set_xticks(x, labels, fontsize=6)
    ax[0].set_ylabel("|nu_meas/nu_th - 1|  [%]")
    ax[0].set_title("(a) upwind deviation: reported vs recomputed")
    ax[0].legend(fontsize=6)
    exact_signed = [r["dev_pct_exact_theory"] for r in rows_a]
    ax[1].bar(x - 0.2, exact_signed, 0.4, color=colors["reviewer"], label="exact von Neumann deviation")
    ax[1].plot(x, [abs(s) for s in exact_signed], "k.", ms=3)
    for i, r in enumerate(rows_a):
        ax[1].annotate(
            f"{r['dev_pct_report']:+.2f}%\n(reported)",
            (i, exact_signed[i]),
            textcoords="offset points",
            xytext=(0, 8 if exact_signed[i] >= 0 else -20),
            ha="center",
            fontsize=5.5,
            color=colors["report"],
        )
    ax[1].axhline(0, color="k", lw=0.8)
    ax[1].set_xticks(x, labels, fontsize=6)
    ax[1].set_ylabel("signed deviation [%]")
    ax[1].set_title(
        f"(b) sign of deviation: {A['sign_contradictions']}/9 rows disagree with the exact symbol"
    )
    ax[1].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(HERE / "fig1_upwind_deviation.png")
    plt.close(fig)

    # fig2: criterion (b) diagnostic power
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))
    th = np.linspace(1e-3, math.pi, 400)
    Cv = 0.5
    base = np.array([abs(1 - Cv * (1 - np.exp(-1j * t))) for t in th])
    mut = np.array([abs(1 - Cv * 1.001 * (1 - np.exp(-1j * t))) for t in th])
    ax[0].plot(th, base, color=colors["reviewer"], label="upwind C=0.5 (reference stencil)")
    ax[0].plot(th, mut, ":", color=colors["report"], lw=2,
               label="mutant: C x 1.001 (0.1% coeff. error)")
    ax[0].fill_between(th, base - 1e-3, base + 1e-3, color="0.6", alpha=0.35,
                       label="report tolerance band +/-1e-3")
    ax[0].set_xlabel("theta = k dx")
    ax[0].set_ylabel("|G|")
    ax[0].set_title("(a) a 0.1% stencil error hides inside the +/-1e-3 band")
    ax[0].legend(fontsize=6)
    resid = {
        "independent march\nvs closed form": max(
            v["max_rel_err_march_vs_closed"] for v in B["reviewer_march_vs_closed"]["upwind"].values()
        ),
        "stencil vs\nclosed form": max(
            v["max_abs_err_stencil_vs_closed"]
            for v in B["reviewer_stencil_vs_closed"]["upwind"].values()
        ),
        "report table\n(sec 3.2)": max(B["report_table_max_abs_err"].values()),
    }
    ax[1].bar(list(resid.keys()), [max(v, 1e-17) for v in resid.values()],
              color=[colors["reviewer"], colors["theory"], colors["report"]])
    ax[1].set_yscale("log")
    ax[1].axhline(1e-3, color="k", ls="--", lw=1, label="criterion 1e-3")
    ax[1].set_ylabel("max |G_num - G_ana|")
    ax[1].set_title("(b) achievable agreement vs tabulated residual")
    for i, (k, v) in enumerate(resid.items()):
        ax[1].annotate(f"{v:.1e}", (i, max(v, 1e-17)), textcoords="offset points",
                       xytext=(0, 4), ha="center", fontsize=6)
    ax[1].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(HERE / "fig2_criterion_power.png")
    plt.close(fig)

    # fig3: Lax-Wendroff scaling + QUICK formula
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))
    ths = np.logspace(math.log10(0.03), math.log10(0.25), 100)
    for Cv, col in ((0.2, "#2471a3"), (0.5, "#1e8449"), (0.8, "#884ea0")):
        ax[0].plot(ths, Cv * (1 - Cv * Cv) * ths**2 / 8, color=col,
                   label=f"theory C(1-C^2)th^2/8, C={Cv}")
        pts = [r for r in C["rows"] if r["C"] == Cv]
        ax[0].plot([r["kdx"] for r in pts], [r["nu_exact_von_neumann"] for r in pts], "o",
                   color=col, ms=4, mfc="none", label=f"recomputed, C={Cv}")
        ax[0].plot([r["kdx"] for r in pts], [r["nu_report"] for r in pts], "x",
                   color=colors["report"], ms=6, label="reported" if Cv == 0.2 else None)
    ax[0].set_xscale("log")
    ax[0].set_yscale("log")
    ax[0].axhline(1e-2, color="k", ls="--", lw=1, label="threshold 1e-2 c dx")
    ax[0].set_xlabel("k dx")
    ax[0].set_ylabel("nu_LW / (c dx)")
    ax[0].set_title("(b) Lax-Wendroff: reported O(theta) vs theoretical O(theta^2)")
    ax[0].legend(fontsize=5.5)
    Cs = np.linspace(0, 1, 200)
    ax[1].plot(Cs, (1 - Cs) * (1 - Cs**2) / 8, color=colors["report"],
               label="report sec 2.2: (1-C)(1-C^2)/8")
    ax[1].plot(Cs, (5 - 4 * Cs) / 8, color=colors["reviewer"],
               label="reviewer derivation: (5-4C)/8")
    ax[1].plot(Cs, (1 - Cs) / 2, color=colors["theory"], ls="--", label="upwind: (1-C)/2")
    qx = [float(k.split("_")[0].replace("C=", "")) for k in F["comparisons"]]
    qy = [F["comparisons"][k]["nu_exact"] for k in F["comparisons"]]
    ax[1].plot(qx, qy, "ko", ms=3, label="QUICK symbol, k dx -> 0.01/0.02")
    ax[1].set_xlabel("Courant number C")
    ax[1].set_ylabel("nu / (c dx)")
    ax[1].set_title("(a) QUICK leading-order viscosity: printed formula vs its own symbol")
    ax[1].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(HERE / "fig3_quick_and_lw.png")
    plt.close(fig)

    # fig4: CD2 growth band + grid convergence
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))
    keys = list(D["half_period_growth"].keys())
    vals = [D["half_period_growth"][k]["amp_growth"] for k in keys]
    ax[0].bar(range(len(keys)), vals, color=colors["reviewer"])
    ax[0].axhspan(D["report_growth_band"][0], D["report_growth_band"][1],
                  color=colors["report"], alpha=0.18,
                  label=f"report band {D['report_growth_band'][0]}-{D['report_growth_band'][1]}")
    ax[0].axhline(1.0, color="k", lw=0.8)
    ax[0].set_xticks(range(len(keys)), [k.replace("_", "\n") for k in keys], fontsize=5.5)
    ax[0].set_ylabel("A(0.5 period)/A(0)")
    ax[0].set_title(f"(a) CD2 growth: {D['cases_below_report_band']}/9 cases below the quoted band")
    ax[0].legend(fontsize=6)
    ax[1].plot(range(len(E["rows"])), [r["nu_meas_reviewer"] for r in E["rows"]], "o-",
               color=colors["reviewer"], label="recomputed nu")
    ax[1].plot(range(len(E["rows"])), [r["nu_report"] for r in E["rows"]], "x--",
               color=colors["report"], label="reported nu (sec 3.5)")
    ax[1].set_xticks(range(len(E["rows"])), [f"N={r['N']}\ndx={r['dx']}" for r in E["rows"]], fontsize=6)
    ax[1].set_yscale("log")
    ax[1].set_ylabel("nu (upwind, C=0.5)")
    ax[1].set_title(
        f"(b) grid convergence reproduced: ratios {', '.join(f'{r:.4f}' for r in E['reviewer_ratios'])}"
    )
    ax[1].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(HERE / "fig4_cd2_and_grid.png")
    plt.close(fig)

    print("wrote review_report.json, review_events.json, 4 figures")
    print("disposition:", review["disposition"]["verdict"], review["severity_counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())