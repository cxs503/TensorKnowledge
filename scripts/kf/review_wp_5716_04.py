#!/usr/bin/env python3
"""wp-5716-04 independent review (red-team) of wp-5716-01 for report 5716.

Design constraints baked into the code (not prose):
  * every quoted string is asserted to be a VERBATIM substring of the fetched
    markdown -> zero hand-copy by construction (script fails if a quote drifts);
  * source_hash is recomputed from bytes and compared with the contract value;
  * every number in the review is either (a) a quoted substring or (b) the
    output of an arithmetic recomputation printed into recompute.json;
  * the script never writes to any report_id, never emits a "verified" flag.

Usage:
  python3 scripts/kf/review_wp_5716_04.py            # fetch + review + write
  python3 scripts/kf/review_wp_5716_04.py --offline  # use runs/ snapshot only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

PKG = "wp-5716-04"
REPORT_ID = "5716"
SOURCE_FIELD = "markdown"
CONTRACT_HASH = "sha256:4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377"
# deliverables live under docs/ because the mission-push gate drops artifacts/** and runs/**
SNAP = "docs/kf/wp-5716-04/source_5716.md"
OUT_DIR = "docs/kf/wp-5716-04"
OUT_REVIEW = OUT_DIR + "/review_report.json"
OUT_RECOMP = OUT_DIR + "/recompute.json"
REVIEWED_PACKAGE = "wp-5716-01"

# ---------------------------------------------------------------- quotes (verbatim)
Q = {
    "wallclock_2": "墙钟 50.7 s",
    "wallclock_9": "总链墙钟约 41.5 s（单核 CPU，无 GPU）",
    "c3_totals": "C3：总航程 684.1 nm / 63.3 h / 203388 kWh；冰区占比 27.0%，设计点 4.50 kn, R_ice 464.7 kN",
    "d1_vs_c3_time": "航线时间 54.4 h vs 剖面 68.2 h",
    "d1_route": "D1：主航线 684.1 nm / 54.5 h，no-go 0 nm",
    "disclosure_count": "16 项门断言 + 7 项披露",
    "disclosure_four": "但有 4 项披露项如实不通过，不覆盖",
    "geom_cb": "几何先验门：由独立排水量（DWT/0.8167）反算 Cb=0.82007 vs 声明 0.82（相对差 8.5e-5）",
    "geom_cb_row": "| Cb 几何反算 vs 声明值 | 0.0085% | 解析几何 | 是 |",
    "b2_correction": "即便按简支 β 修正仍为 12.4",
    "b2_beta_row": "| B2 板格系数 vs 简支板理论 β | 75.8% | Navier 级数 0.2874 | 否 |",
    "e1_gm": "GM 0.09%",
    "a2_line": "A2：72 h 技能（vs 持续性）0.505，同化 RMSE 0.1145 m（冰图 0.1444 m），质量误差 0.0e+00，航窗可作业 10/12 lead。",
    "fem_row": "| TensorFEM Mindlin Q4 vs 闭式 Mindlin | 0.211% | tensorfem.plate 闭式解 | 是 |",
    "withheld_cond": "plan-12 外部仓库（TensorFEM/TensorDEM/TensorPhysics）若未挂载，对账项自动降级为 WITHHELD，不默认通过。",
    "tests": "pytest `backend/tests/test_campaign_ice_nav.py` 13 passed；上游四套测试（ICE_DA 69、route 14、speed_profile 14、ice_belt 19）仍全绿。",
    "gate_threshold": "门判据 **16/16 通过**（要求 ≥8）",
    "d07_row": "| D1 vs C3 冰中航速（独立实现） | 65.6% | 两套生产模型互比 | 否 |",
    "d07_text": "另有 D1↔C3 冰中航速 40–66% 分歧",
    "d01": "`D01-UIKKU-ANCHOR`：C1 MT Uikku 链 vs Hu&Zhou(2016) 十工况实冰锚 — 判据 预登记筛选线 MAPE ≤ 25%",
    "regrid": "- A2→D1：冰量守恒 2.6e-14，方向探针 5.3e-05，覆盖 20.4%。",
    "artifacts": "`artifacts/campaign_ice_nav/campaign_acceptance.json`（含全链 sha256 清单）",
    "honest_fail_scope": "一致性门 16/16 通过、一条命令端到端跑通、JSON/报告/7 图齐全。",
    "geom_params": "（L_pp=190 m, B=30 m, T=11.5 m, Cb=0.82, 主机 18 MW, 服务航速 13 kn",
}

# ---------------------------------------------------------------- recompute


def recompute(md: str) -> dict:
    L, B, T, DWT = 190.0, 30.0, 11.5, 45000.0
    LBT = L * B * T
    delta = DWT / 0.8167                      # displacement [t], as the report says
    cb_literal = delta / LBT                  # literal: volume == tonnes
    cb_rho = (delta / 1.025) / LBT            # with an unstated rho=1.025 t/m3 step
    r = {
        "inputs": {"L_pp_m": L, "B_m": B, "T_m": T, "DWT_t": DWT,
                   "LBT_m3": LBT, "DWT_over_0.8167_t": round(delta, 2),
                   "service_kn": 13.0, "n_ice_fraction": 0.270,
                   "route_nm": 684.1, "energy_kWh": 203388.0},
        "a1_cb_literal_no_density": {
            "cb": round(cb_literal, 6),
            "reported_cb": 0.82007,
            "rel_diff_pct_vs_0.82": round(abs(cb_literal - 0.82) / 0.82 * 100, 4),
            "g01_own_tolerance_pct": 2.0,
            "verdict": ("FAIL of G01's own 2% tolerance if the formula is applied "
                        "literally (no density step)"),
        },
        "a2_cb_with_rho_1p025": {
            "cb": round(cb_rho, 6),
            "reported_cb": 0.82007,
            "rel_diff_pct_vs_0.82": round(abs(cb_rho - 0.82) / 0.82 * 100, 5),
            "reported_rel_diff": 8.5e-05,
            "verdict": ("reported value reproduces to display precision only when an "
                        "unstated rho=1.025 t/m3 conversion is inserted"),
        },
        "a3_geom_ratios": {"LB": round(L / B, 4), "BT": round(B / T, 4),
                           "reported": {"LB": 6.333, "BT": 2.609},
                           "verdict": "consistent"},
        "a4_b2_beta_correction": {
            "beta_theory": 0.2874, "reported_rel_diff": 0.758,
            "beta_implied_B2": round(0.2874 * (1 + 0.758), 4),
            "utilization_20y": 67.58,
            "utilization_after_correction": {
                f"SN_slope_m={m}": round(67.58 * (0.2874 / (0.2874 * 1.758)) ** m, 2)
                for m in (3, 3.5, 4, 5)
            },
            "reported_after_correction": 12.4,
            "verdict": ("12.4 reproduces exactly for S-N slope m=3 and beta_B2 > "
                        "beta_theory; neither assumption is stated in the markdown"),
        },
        "a5_mean_speeds": {
            "D1_mean_kn_54.5h": round(684.1 / 54.5, 2),
            "C3_mean_kn_63.3h": round(684.1 / 63.3, 2),
            "C3_mean_kn_68.2h": round(684.1 / 68.2, 2),
        },
        "a6_ice_segment_speed_reconstruction": {
            "assumption": "ice share 27.0% of 684.1 nm, open-water at the stated 13 kn service speed",
            "ice_nm": round(0.270 * 684.1, 1),
            "open_water_nm": round(0.730 * 684.1, 1),
            "open_water_h": round(0.730 * 684.1 / 13.0, 2),
            "implied_mean_ice_kn": {
                "D1@54.5h": round(0.270 * 684.1 / (54.5 - 0.730 * 684.1 / 13.0), 2),
                "C3@63.3h": round(0.270 * 684.1 / (63.3 - 0.730 * 684.1 / 13.0), 2),
                "C3@68.2h": round(0.270 * 684.1 / (68.2 - 0.730 * 684.1 / 13.0), 2),
            },
            "reported_design_point_kn": 4.50,
            "ratio_vs_design_point": {
                "D1@54.5h": round(0.270 * 684.1 / (54.5 - 0.730 * 684.1 / 13.0) / 4.50, 2),
                "C3@63.3h": round(0.270 * 684.1 / (63.3 - 0.730 * 684.1 / 13.0) / 4.50, 2),
            },
            "verdict": ("first-order closure is NOT satisfied at 11.48 kn (D1) / 7.42 kn "
                        "(C3) vs the reported 4.50 kn design point; the report carries no "
                        "per-leg table, so this cannot be resolved from the markdown"),
        },
        "a7_d07_consistency": {
            "design_point_kn": 4.50, "reported_rel_divergence": 0.656,
            "implied_peer_speed_kn": round(4.50 * 1.656, 3),
            "verdict": "65.6% is consistent with a peer model at ~7.45 kn under the same (h,C)",
        },
        "a8_energy": {
            "avg_power_kW": round(203388 / 63.3, 1),
            "energy_per_nm_kWh": round(203388 / 684.1, 1),
            "main_engine_MW": 18.0,
            "avg_load_pct": round(203388 / 63.3 / 18000 * 100, 1),
        },
        "a9_internal_conflicts": {
            "wallclock_50.7_vs_41.5_pct": round(abs(50.7 - 41.5) / 50.7 * 100, 1),
            "c3_time_63.3_vs_68.2_pct": round(abs(68.2 - 63.3) / 63.3 * 100, 1),
            "d1_time_54.5_vs_54.4_pct": round(abs(54.5 - 54.4) / 54.5 * 100, 2),
        },
        "a10_disclosure_enumeration": {
            "claimed_n": 7,
            "named_D_ids": sorted(set(re.findall(r"`(D0[0-9]-[A-Z0-9-]+)`", md))),
            "named_n": len(set(re.findall(r"`(D0[0-9]-[A-Z0-9-]+)`", md))),
            "gap": 7 - len(set(re.findall(r"`(D0[0-9]-[A-Z0-9-]+)`", md))),
        },
        "a11_assertion_table": {
            "pass_cells": len(re.findall(r"\| PASS \|", md)),
            "rows_declared": 16,
            "gate_threshold": 8,
        },
        "a12_error_table": {
            "rows": len(re.findall(r"^\| [^|]+ \| [^|]+ \| [^|]+ \| (是|否) \|$", md, re.M)),
            "yes": len(re.findall(r"^\| [^|]+ \| [^|]+ \| [^|]+ \| 是 \|$", md, re.M)),
            "no": len(re.findall(r"^\| [^|]+ \| [^|]+ \| [^|]+ \| 否 \|$", md, re.M)),
        },
        "a13_a2_assimilation_gain_vs_ice_chart_pct":
            round((0.1444 - 0.1145) / 0.1444 * 100, 2),
    }
    return r


# ---------------------------------------------------------------- findings


def findings(r: dict) -> list[dict]:
    return [
        {
            "id": "F1-C3-TOTAL-TIME",
            "severity": "high",
            "blocking": True,
            "class": "internal numeric contradiction",
            "title": "C3 total voyage time is reported twice with different values (63.3 h vs 68.2 h)",
            "quote_keys": ["c3_totals", "d1_vs_c3_time", "d07_row"],
            "measurements": {"t_hours_in_section3": 63.3, "t_hours_in_conclusion": 68.2,
                             "rel_gap_pct": r["a9_internal_conflicts"]["c3_time_63.3_vs_68.2_pct"]},
            "reproduction": ("grep -o '63\\.3 h' / '68\\.2 h' on the fetched markdown; the two "
                             "strings coexist and no caveat distinguishes them. Reconstruct "
                             "mean speed: 684.1/63.3=10.81 kn vs 684.1/68.2=10.03 kn."),
            "impact": ("every downstream consumer of C3 duration/energy-per-hour picks a "
                       "different value depending on which section it reads; D07's "
                       "'40–66%' divergence band is stated against an ambiguous basis"),
            "remediation": ("state one authoritative C3 duration (plus the alternative's "
                            "definition, e.g. profile-with-acceleration vs delivered-legs), "
                            "and add an assertion closing C3 total time and kWh against its "
                            "own per-bin speeds"),
        },
        {
            "id": "F2-DISCLOSURE-SET",
            "severity": "high",
            "blocking": True,
            "class": "unsupported claim / non-auditable disclosure set",
            "title": "Report declares '7 项披露' but enumerates only 4 disclosure IDs",
            "quote_keys": ["disclosure_count", "disclosure_four", "d01"],
            "measurements": r["a10_disclosure_enumeration"],
            "reproduction": ("regex `D0[0-9]-[A-Z0-9-]+` over the markdown yields exactly "
                             f"{r['a10_disclosure_enumeration']['named_n']} IDs "
                             "(D06, D01, D02, D07) against a declared 7"),
            "impact": ("the reviewable surface is smaller than claimed: 3 of 7 disclosures "
                       "cannot be located, quoted or graded by any downstream consumer"),
            "remediation": "list all 7 IDs with their predeclared criteria, or correct the count to 4",
        },
        {
            "id": "F3-NO-TIME-ENERGY-CLOSURE-ASSERTION",
            "severity": "high",
            "blocking": False,
            "class": "gate coverage gap (missing assertion)",
            "title": ("none of the 16 assertions closes route time / energy against the "
                      "per-leg speeds, and none reconciles D1 time with C3 time"),
            "quote_keys": ["c3_totals", "d1_route", "regrid", "gate_threshold"],
            "measurements": r["a6_ice_segment_speed_reconstruction"],
            "reproduction": ("back-out the ice-segment speed from the report's own totals "
                             "(684.1 nm, 27.0% ice, 13 kn open water): D1 -> 11.48 kn, "
                             "C3 -> 7.42 kn, against a reported design point of 4.50 kn"),
            "impact": ("G12 re-computes length only and G10 checks units only, so a "
                       "time/energy closure error would pass the gate silently; the 2.55x "
                       "gap between the reconstructed D1 ice speed and the 4.50 kn design "
                       "point is exactly the inconsistency class the gate does not cover"),
            "remediation": ("add G17-TIME-ENERGY-CLOSURE (sum of leg times == total time, "
                            "sum of leg kWh == reported kWh, both <=1e-9 relative) and a "
                            "per-leg table (leg, h_ice, v_kn, t_h, kWh)"),
        },
        {
            "id": "F4-WALLCLOCK-CONFLICT",
            "severity": "medium",
            "blocking": False,
            "class": "internal numeric contradiction",
            "title": "End-to-end wall clock stated as 50.7 s in ② and ~41.5 s in ⑤ note 9",
            "quote_keys": ["wallclock_2", "wallclock_9"],
            "measurements": {"s_section2": 50.7, "s_note9": 41.5,
                             "rel_gap_pct": r["a9_internal_conflicts"]["wallclock_50.7_vs_41.5_pct"]},
            "reproduction": "both literals present in the markdown; 18.1% apart",
            "impact": ("a reproducibility claim is the cheapest thing to keep exact; an "
                       "18% self-disagreement weakens the sha256-ledger credibility"),
            "remediation": "report one measured value with host/cores and the run id",
        },
        {
            "id": "F5-G01-CB-FORMULA-UNDERSPECIFIED",
            "severity": "medium",
            "blocking": False,
            "class": "assertion not reproducible from report text",
            "title": ("G01's Cb formula (Cb = nabla/(L*B*T) from DWT/0.8167) omits the "
                      "seawater-density step; applied literally it gives 2.51% and fails "
                      "G01's own 2% tolerance"),
            "quote_keys": ["geom_cb", "geom_cb_row", "geom_params"],
            "measurements": {"literal": r["a1_cb_literal_no_density"],
                             "with_rho_1.025": r["a2_cb_with_rho_1p025"]},
            "reproduction": ("45000/0.8167=55099.79 t -> /(190*30*11.5)=0.840577 (2.51% "
                             "off 0.82); inserting rho=1.025 t/m3 gives 0.820075, which "
                             "matches the reported 0.82007 to display precision"),
            "impact": ("the geometry prior gate is auditable only by a reader who guesses "
                       "the unstated density; the report's own formula, taken literally, "
                       "contradicts its PASS"),
            "remediation": "write Cb = (DWT/0.8167/1.025)/(L*B*T) and state rho and its source in contracts.py",
        },
        {
            "id": "F6-ERROR-TABLE-SELECTION",
            "severity": "medium",
            "blocking": False,
            "class": "incomplete answer to the mandated 'is it <3%?' question",
            "title": ("⑥ omits quantities stated elsewhere (E1 GM 0.09%) and gives no "
                      "baseline value for A2 skill 0.505, so the '<3%' answer set is not "
                      "complete or auditable"),
            "quote_keys": ["e1_gm", "a2_line", "b2_beta_row"],
            "measurements": r["a12_error_table"],
            "reproduction": ("count rows in ⑥: 13 rows, 7 是 / 6 否; GM 0.09% appears only "
                             "in ③ and never in ⑥; '0.505' has no persistence-baseline number"),
            "impact": ("omissions here are conservative (GM would pass), but a reader "
                       "cannot reconstruct which quantities the author considered key, and "
                       "skill without a baseline number is not interpretable"),
            "remediation": "make ⑥ a complete table over every headline quantity in ③, incl. GM and both skill/baseline",
        },
        {
            "id": "F7-FEM-REAL-VS-WITHHELD",
            "severity": "low",
            "blocking": False,
            "class": "evidence-grade ambiguity",
            "title": ("TensorFEM Q4 0.211% is reported as a passing REAL row while note 8 "
                      "says cross-repo checks auto-downgrade to WITHHELD when the repo is "
                      "unmounted; the report never states which branch ran"),
            "quote_keys": ["fem_row", "withheld_cond"],
            "measurements": {"reported_rel_err_pct": 0.211},
            "reproduction": "both statements coexist; no mount status / repo ref is given",
            "impact": "the only cross-repo numeric binding is not traceable to a code identity",
            "remediation": "state mount status + repo commit for the TensorFEM check, or mark the row WITHHELD",
        },
        {
            "id": "F8-EXACT-ZERO-MASS-ERROR",
            "severity": "low",
            "blocking": False,
            "class": "unqualified exact-zero claim",
            "title": "A2 mass error is reported as exactly 0.0e+00 without norm definition",
            "quote_keys": ["a2_line"],
            "measurements": {"reported": 0.0},
            "reproduction": "literal present; no L1/L2/relative definition, no ulp scale",
            "impact": ("an exact zero in floating point is a strong claim; it is only "
                       "credible for a conservation-by-construction scheme, which should "
                       "be said explicitly"),
            "remediation": "state the norm, the domain, and whether conservation is by construction",
        },
        {
            "id": "F9-TEST-EVIDENCE-UNBOUND",
            "severity": "low",
            "blocking": False,
            "class": "claim without artifact identity",
            "title": ("13 pytest passes plus 116 upstream tests are cited without a log/"
                      "commit/hash pointer"),
            "quote_keys": ["tests", "artifacts"],
            "measurements": {"campaign_tests": 13, "upstream_tests": 69 + 14 + 14 + 19},
            "reproduction": "numbers present; no artifact path or hash accompanies them",
            "impact": ("G13 claims a sha256 ledger, but the cited JSON is outside the "
                       "reviewable surface, so the ledger itself cannot be recomputed here"),
            "remediation": "inline the ledger (stage -> sha256) and the pytest summary line, or attach a run id",
        },
        {
            "id": "F10-GATE-BAR-AND-SCOPE",
            "severity": "low",
            "blocking": False,
            "class": "overstated scope of the headline verdict",
            "title": ("gate threshold is 8/16, and all 16 assertions are self-consistency: "
                      "the only external anchors (D01, D02, D07) all fail, so 'gate PASS' "
                      "must not be read as physics accuracy"),
            "quote_keys": ["gate_threshold", "d07_row", "b2_beta_row", "d01", "honest_fail_scope"],
            "measurements": r["a11_assertion_table"],
            "reproduction": "16 declared rows, 16 PASS cells; threshold ≥8; 3 external anchors fail",
            "impact": ("a 50%-threshold consistency gate plus a 67.6 utilization FAIL in the "
                       "same report means bare 'acceptance gate passed' is misleading"),
            "remediation": "state in the verdict line that the gate certifies plumbing/consistency, not physics accuracy",
        },
    ]


def corroborated(r: dict) -> list[dict]:
    return [
        {"id": "V1-CB-REPRODUCES",
         "quote_keys": ["geom_cb"],
         "measurements": r["a2_cb_with_rho_1p025"],
         "note": "not a defect; the defect (F5) is the unstated density step"},
        {"id": "V2-GEOM-RATIOS",
         "quote_keys": ["geom_cb"],
         "measurements": r["a3_geom_ratios"]},
        {"id": "V3-B2-12.4-REPRODUCES",
         "quote_keys": ["b2_correction", "b2_beta_row"],
         "measurements": r["a4_b2_beta_correction"],
         "note": "reproduces exactly at S-N slope m=3"},
        {"id": "V4-D07-65.6PCT-REPRODUCES",
         "quote_keys": ["d07_row"],
         "measurements": r["a7_d07_consistency"]},
        {"id": "V5-MEAN-SPEEDS-PLAUSIBLE",
         "quote_keys": ["d1_route", "c3_totals"],
         "measurements": r["a5_mean_speeds"]},
        {"id": "V6-ENERGY-SCALE-PLAUSIBLE",
         "quote_keys": ["c3_totals"],
         "measurements": r["a8_energy"]},
        {"id": "V7-A2-ASSIMILATION-GAIN",
         "quote_keys": ["a2_line"],
         "measurements": {"gain_vs_ice_chart_pct": r["a13_a2_assimilation_gain_vs_ice_chart_pct"]}},
    ]


# ---------------------------------------------------------------- main


def load_markdown(offline: bool) -> bytes:
    if offline:
        raw = open(SNAP, "rb").read()
        return raw
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fetch_report_5716 as f  # noqa: E402

    f.main(["--report-id", REPORT_ID, "--out", SNAP])
    return open(SNAP, "rb").read()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)
    raw = load_markdown(a.offline)
    md = raw.decode("utf-8")
    got = "sha256:" + hashlib.sha256(raw).hexdigest()

    missing = [k for k, v in Q.items() if v not in md]
    if missing:
        raise SystemExit("verbatim quote check FAILED for: %s" % missing
                         + "\n" + "\n".join(Q[k] for k in missing))
    if got != CONTRACT_HASH:
        raise SystemExit(f"source hash mismatch: {got} != {CONTRACT_HASH}")

    r = recompute(md)
    f_ = findings(r)
    c_ = corroborated(r)

    review = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "reviewed_package": REVIEWED_PACKAGE,
        "report_id": REPORT_ID,
        "reviewer_role": "red-team-reviewer",
        "reviewer_independence": {
            "context_used": ["report markdown (source_field=markdown)", "own arithmetic recomputation"],
            "context_excluded": [
                "producer explanation / summary / chat",
                "producer code and artifacts under artifacts/campaign_ice_nav (not reachable from this worktree)",
                "any report_id other than 5716",
            ],
            "note": ("The platform record snapshot at docs/kf/wp-5716-04/source_5716.md.meta.json was "
                     "written only to pin provenance (id/title/tags/created_at) and its `summary` "
                     "field was NOT used as review evidence; every finding below cites a verbatim "
                     "substring of the markdown."),
        },
        "scope": {
            "checks_performed": [
                "source hash recomputed from bytes and compared with the contract value",
                "verbatim-substring verification of every quoted fragment",
                "first-order arithmetic closure of Cb, beta correction, speeds, time, energy",
                "cross-section duplicate-quantity conflict scan (time, wall clock)",
                "disclosure-ID enumeration vs declared count",
                "assertion-table and error-table census",
            ],
            "checks_not_run": [
                "re-execution of modules.campaign_ice_nav.run_campaign (code lives in the ship-owners' backend repo, not in this worktree)",
                "verification of artifacts/campaign_ice_nav/campaign_acceptance.json sha256 ledger (not in reviewable surface; G13 not re-derivable)",
                "pytest backend/tests/test_campaign_ice_nav.py (13 claimed) and 116 upstream tests",
                "upstream package completion registry (no packages endpoint on the platform API: /tensor/reports/5716/packages, /tensor/work_packages, /kf/packages all 404)",
                "A2 OSSE skill re-computation (no observation source in the markdown)",
                "TensorFEM Q4 Mindlin 0.211% re-computation (cross-repo mount status unstated)",
            ],
            "unknown_not_passed": ["upstream_packages_completed", "G13 ledger recomputability", "test counts"],
        },
        "provenance": {
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "source_field": SOURCE_FIELD,
            "source_hash_recomputed": got,
            "source_hash_matches_contract": got == CONTRACT_HASH,
            "chars": len(md),
            "evidence_quotes_verified": len(Q),
            "recompute_artifact": OUT_RECOMP,
        },
        "findings": f_,
        "corroborated_claims": c_,
        "overstated_claims": [x["title"] for x in f_ if x["class"].startswith(("unsupported", "overstated", "incomplete"))],
        "blocking_findings": [x["id"] for x in f_ if x["blocking"]],
        "disposition": "needs-fix",
        "disposition_rationale": (
            "The honesty posture is sound: 4 disclosures are stated as failing, external anchors "
            "are not dressed up, and the structural verdict is declared 不通过. The numbers I could "
            "recompute independently reproduce (Cb with rho, B2 12.4 at m=3, D07 65.6%, mean speeds, "
            "energy scale). Blocking defects are transactional rather than physical: the same "
            "quantity carries two values (C3 total time 63.3 vs 68.2 h; wall clock 50.7 vs 41.5 s), "
            "and the declared disclosure count (7) cannot be reconciled with the 4 IDs actually "
            "named. No assertion in the 16-item gate closes time/energy or reconciles D1 vs C3, so "
            "the reconstructed 11.48 kn D1 mean ice speed against the 4.50 kn design point is a "
            "coverage hole, not a proven error. Fix cost is editorial + one assertion; the physics "
            "conclusions do not need to change."
        ),
        "verification_status": "NOT_VERIFIED_BY_REVIEWER -- verification is computed by the platform gate, not asserted here",
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_RECOMP, "w", encoding="utf-8") as fh:
        json.dump({"source_hash": got, "quote_keys": sorted(Q), "recompute": r},
                  fh, indent=2, ensure_ascii=False)
    with open(OUT_REVIEW, "w", encoding="utf-8") as fh:
        json.dump(review, fh, indent=2, ensure_ascii=False)

    print("source_hash", got, "matches_contract", got == CONTRACT_HASH)
    print("quotes verified:", len(Q))
    sev = {}
    for x in f_:
        sev[x["severity"]] = sev.get(x["severity"], 0) + 1
    print("findings:", len(f_), sev, "blocking:", review["blocking_findings"])
    print("disposition:", review["disposition"])
    return 0


if __name__ == "__main__":
    sys.exit(main())