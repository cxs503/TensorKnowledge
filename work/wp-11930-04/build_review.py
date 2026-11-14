#!/usr/bin/env python3
"""Build the wp-11930-04 independent-review deliverables.

Inputs (all reviewer-side, no producer explanation):
  work/wp-11930-04/source_report.md        markdown fetched fresh from GET /tensor/reports/11930
  work/wp-11930-04/verify_wp-11930-04.json recomputed check ledger
  docs/kf/wp-11930-01/kf_result.wp-11930-01.json   upstream KO under review (wp-11930-01)

Outputs:
  docs/kf/wp-11930-04/review_report.json
  docs/kf/wp-11930-04/review_events.json
  docs/kf/wp-11930-04/kf_result.wp-11930-04.json

Every quote in the review is sliced out of the source markdown by exact substring match and
stored with its char offsets, so the review can be re-verified byte-for-byte.
"""
import hashlib
import json
import os

REPO = "/root/tp-agent/work/m19840"
SRC = os.path.join(REPO, "work/wp-11930-04/source_report.md")
VERIFY = os.path.join(REPO, "work/wp-11930-04/verify_wp-11930-04.json")
UPSTREAM = os.path.join(REPO, "docs/kf/wp-11930-01/kf_result.wp-11930-01.json")
OUTDIR = os.path.join(REPO, "docs/kf/wp-11930-04")
REPORT_ID = "11930"
PACKAGE_ID = "wp-11930-04"
REVIEWED_PACKAGE = "wp-11930-01"
REVIEWED_AT = "2026-11-12T04:20:00+00:00"
POLICY = "kf-review/v1.0"


def sha_file(path):
    return "sha256:" + hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    md = open(SRC, encoding="utf-8").read()
    ver = json.load(open(VERIFY, encoding="utf-8"))
    up = json.load(open(UPSTREAM, encoding="utf-8"))
    os.makedirs(OUTDIR, exist_ok=True)

    def loc(text):
        n = md.count(text)
        if n != 1:
            raise SystemExit(f"quote not uniquely locatable ({n}): {text[:80]!r}")
        s = md.index(text)
        return {"start_char": s, "end_char": s + len(text),
                "start_line": md[:s].count("\n") + 1, "quote": text}

    Q = {
        "brun": "最坏参数对 ['k_c', 'k_p']：Brun γ = 6.71，相关系数 0.978；全 6 列 γ = inf",
        "localm_row": "| 0.05 | 0.397 | 0.376 | -5.4% | 0.080 | 是 |",
        "localm_text": "端点局部 m：t=0.05 → 0.080、t=0.8 → 0.045，方向一致性 是",
        "ac5_row": "| 巴西中心主应力比 | Hondros −3.0（解析）| 最优 -2.705（相对 9.8%）| 否（差两个量级，honest FAIL）|",
        "ac6_method": "200 组随机 θ 只跑 UCS（AC6，验证“随机参数几乎不可能落进文献带”）",
        "ac6_result": "违反比例 83.5%（n = 200；UCS 中位 2.546 MPa）",
        "hd_row": "UCS 试件：H/D = 2.000（ASTM D7012 带 [1.5, 2.5]）→ PASS，颗粒数 144",
        "ac7_row": "两次独立进程 UCS = 1.01e+06 / 1.01e+06 Pa，相对差 0.000（门 1e-3）",
        "ac3_row": "| AC3 三分支可行性 | (a)/(b)/(c) 之一 + 证据 | 参考 θ 落 **分支 (c)**：UCS 1.010 MPa、σc/σt 2.688、m CI [24.916, 746.453] （伪真值 6.000）；33 个设计点分支计数 a/b/c = 0/0/33 | 见 §3.3 |",
        "fit_text": "拟合得到 m = 262.976（bootstrap 95% CI [24.916, 746.453]，CI 宽度 721.537），σ_ref = 3.71e+05 Pa",
        "proxy_m_row": "| m | 0.8092 | 0.0904 | 0.5689 | 26/28 | n/a |",
        "jac_row": "- cond(J) = **9.063**；奇异值 5.848、2.151、0.645；rank(J) = 3/6，非零奇异值给出的结构零空间维数 3",
        "ac5_sec": "判定：PASS（容差 15%，按**中心区**读数判定）；但跨 9 个（分辨率 × 区域）配置的偏差范围 10–788%，**稳健性 FAIL**",
    }
    findings = [
        {
            "id": "F1",
            "severity": "major",
            "blocking": False,
            "scope": "§3.2 AC2 diagnostic: Brun collinearity index of the worst parameter pair",
            "finding": "Published γ=6.71 for pair ['k_c','k_p'] is not reproducible from the published correlation ρ=0.978 "
                       "under either standard definition: Brun γ=1/√(1−R²)=4.796, Belsley 2-column index √((1+ρ)/(1−ρ))=9.486. "
                       "Only the non-standard 1/√(1−ρ)=6.745 lands near 6.71, which suggests a missing square / undeclared formula. "
                       "The report never states the γ formula, so the 'worst pair' ranking is not independently auditable.",
            "evidence_locator": loc(Q["brun"]),
            "reproduction": "verify_wp-11930-04.py N2.5: ρ recomputed from the published Jacobian JᵀJ (0.97802) → γ_brun=4.796, γ_belsley=9.486, 1/√(1−ρ)=6.745.",
            "impact": "Does not change the structural conclusion: J has rank 3/6 (recomputed N2.3) and any column is exactly representable by the others → γ=inf for the full 6-column set (recomputed N2.6).",
            "remedy": "State the Brun formula in the report (and in the code docstring) and republish γ for the pair; if the 1/√(1−ρ) form was used, fix the implementation.",
        },
        {
            "id": "F2",
            "severity": "major",
            "blocking": False,
            "scope": "§3.4 AC4 table column '局部 m' and the direction-consistency sentence",
            "finding": "The '局部 m' column reports 0.080 (t=0.05) and 0.045 (t=0.80), i.e. 3–4 orders of magnitude below the global "
                       "m=262.976 fitted in the same paragraph. If read literally as Weibull moduli, the local values contradict the "
                       "global fit and would falsify AC4; the numbers are only consistent with the local exponent 1/m (→ m≈12.5 / 22.2). "
                       "The label/quantity is wrong or at least ambiguous, while AC4 PASS hinges on 'end m direction consistency'.",
            "evidence_locator": loc(Q["localm_text"]),
            "table_locator": loc(Q["localm_row"]),
            "reproduction": "verify_wp-11930-04.py N3.5: 0.080 vs global 262.976 → ratio 3287; 1/0.080=12.5, 1/0.045=22.2.",
            "impact": "Direction consistency is a sign test on the local exponent, so the AC4 verdict survives; but a reader comparing 0.080 to 263 would conclude catastrophic heterogeneity that the report does not discuss.",
            "remedy": "Rename the column to 'local exponent 1/m (local m in brackets)' or publish local m = 12.5 / 22.2 and explain the difference from the global fit.",
        },
        {
            "id": "F3",
            "severity": "minor",
            "blocking": False,
            "scope": "§5 error table, Brazilian centre stress-ratio row",
            "finding": "The same row states a 9.8% relative difference and then qualifies it as '差两个量级' (two orders of magnitude). "
                       "9.8% (and even the worst configuration, 788%) is not a two-order-of-magnitude gap; the qualitative clause contradicts "
                       "the quantitative cell it annotates.",
            "evidence_locator": loc(Q["ac5_row"]),
            "reproduction": "verify_wp-11930-04.py N4.1 recomputes all six AC5 deviations (9.8/16.0/39.3/130.2/205.2/788.1%); none is 10².",
            "impact": "Wording only; the honest FAIL verdict and §3.5 robustness FAIL are unaffected.",
            "remedy": "Delete or correct the '差两个量级' clause (e.g. '定性不符：多配置下中心横向拉应力缺失').",
        },
        {
            "id": "F4",
            "severity": "major",
            "blocking": False,
            "scope": "§2 method item 7 (negative control) vs §3.6 measured result",
            "finding": "The method text says the 200-random-θ control 'verifies that random parameters can hardly land in the literature band', "
                       "but the measured violation ratio is 83.5%, i.e. 33/200 ≈ 16.5% (about one in six) random parameter sets DO land in "
                       "[5,15] MPa. That is the opposite of 'almost impossible' and is precisely why AC6 is recorded FAIL.",
            "evidence_locator": loc(Q["ac6_method"]),
            "result_locator": loc(Q["ac6_result"]),
            "reproduction": "verify_wp-11930-04.py N6.1: 167/200=83.5% ⇒ 33/200=16.5% inside band; N6.2.",
            "impact": "The FAIL is honestly recorded, but the method paragraph overstates the control's strength; downstream readers may cite the control as evidence the band is discriminative, which it is not.",
            "remedy": "Rewrite §2 item 7 to 'quantifies how often random θ lands in the band (16.5%, n=200) — the control FAILED its ≥95% target'.",
        },
        {
            "id": "F5",
            "severity": "minor",
            "blocking": False,
            "scope": "§0/§3.1 AC1 UCS aspect-ratio sub-item",
            "finding": "H/D=2.000 mixes endpoints: H=0.2 m is the gauge (8 lattice spacings, centre-to-centre of the driven end layers) while "
                       "D=0.1 m is the bounding-box diameter (3 spacings + 2 radii). Under uniform conventions the same lattice gives H/D=2.25 "
                       "(extent/extent, still inside ASTM [1.5,2.5]) or 2.667 (centre-to-centre/centre-to-centre, outside the band). "
                       "The convention is not stated, so the AC1 PASS is convention-dependent.",
            "evidence_locator": loc(Q["hd_row"]),
            "reproduction": "verify_wp-11930-04.py N1.1/N1.2 (D=3·0.025+2·0.0125=0.1; H_gauge=8·0.025=0.2; H_extent=0.225).",
            "impact": "Verdict survives under the physical convention (2.25 ∈ [1.5,2.5]) but not under a pure centre-to-centre convention (2.667).",
            "remedy": "State the convention explicitly and report both numbers (physical 2.25, gauge/D 2.00).",
        },
        {
            "id": "F6",
            "severity": "minor",
            "blocking": False,
            "scope": "§3.3/§3.4 numbers that cannot be re-derived from the report text",
            "finding": "The fitted-thickness tensile strengths (t=0.1/0.2/0.4, the fit inputs) are never printed, so the published σc/σt=2.688 "
                       "and m=262.976 cannot be recomputed from the report alone; only the two holdout predictions are reproducible from the "
                       "published (m, σ_ref). The three-target feasibility matrix (AC3) therefore contains one number (2.688) with no in-report derivation.",
            "evidence_locator": loc(Q["fit_text"]),
            "recomputed_locator": loc(Q["ac3_row"]),
            "reproduction": "verify_wp-11930-04.py N3.1/N3.2 reproduce 0.3753 MPa and 0.3713 MPa at t=0.05/0.80 from (m, σ_ref); N8.1 records the missing fit inputs.",
            "impact": "Fidelity of the holdout chain recomputes clean; the ratio target's provenance is not.",
            "remedy": "Add the five-thickness σ_t table (fit inputs + repeats) to §3.4.",
        },
        {
            "id": "F7",
            "severity": "informational",
            "blocking": False,
            "scope": "§0/§3.6 AC7 reproducibility",
            "finding": "'relative difference 0.000' is asserted from two values printed to three significant figures (1.01e+06 Pa each); "
                       "the displayed evidence cannot support an exact-zero claim (it only bounds the difference by ~1e-3 relative).",
            "evidence_locator": loc(Q["ac7_row"]),
            "reproduction": "Reading of the published precision; not a numerical contradiction.",
            "impact": "Cosmetic, and the gate (1e-3) is comfortably met either way.",
            "remedy": "Print at least 6 significant figures (or raw Pa integers) for the two runs.",
        },
        {
            "id": "F8",
            "severity": "informational",
            "blocking": False,
            "scope": "review limitation inherited from upstream wp-11930-01",
            "finding": "7/14 registered assets (module, 3 scripts, test suite, records.jsonl, artifacts report.json) are referenced_unresolved and "
                       "live only in the TensorDEM checkout; 1 is declared absent. The 42-test suite, the 747-task campaign, the NSGA-II run and the "
                       "KE/work gate therefore cannot be re-executed from this repo — they are reviewed for internal consistency only.",
            "evidence_locator": None,
            "reproduction": "docs/kf/wp-11930-01 asset_manifest counts.by_resolution {referenced_unresolved:7, resolved_in_source:6, declared_absent:1} (recomputed in R3.1).",
            "impact": "Sets the ceiling of this review: no independent reproduction of DEM physics.",
            "remedy": "None on the reviewer side; the upstream registration is correct to declare these unresolved.",
        },
        {
            "id": "F9",
            "severity": "informational",
            "blocking": False,
            "scope": "§3.3 proxy accuracy table → use of the Pareto front as AC3 evidence",
            "finding": "The quadratic surrogate for m has LOO R²=0.0904 (in-sample 0.8092), i.e. essentially no out-of-sample predictive power. "
                       "The report discloses this and states the (c) branch rests on DEM design points plus the proxy only as direction evidence; "
                       "downstream consumers must not quote frontier m values as calibrated.",
            "evidence_locator": loc(Q["proxy_m_row"]),
            "reproduction": "Reported table read verbatim; not re-runnable (surrogate data absent).",
            "impact": "Consistent with the report's own caveat (§4 item 7) — recorded so the caveat is not lost downstream.",
            "remedy": "None required; keep the caveat in any derived KO.",
        },
        {
            "id": "F10",
            "severity": "minor",
            "blocking": False,
            "scope": "§0 acceptance table, AC3 row",
            "finding": "The AC3 verdict cell reads '见 §3.3' instead of PASS/FAIL, breaking the table's own per-AC verdict format. The content of §3.3 "
                       "(branch (c) with evidence) satisfies AC3's stated criterion, so the intended verdict is PASS but is never stated.",
            "evidence_locator": loc(Q["ac3_row"]),
            "reproduction": "Direct read of the §0 table.",
            "impact": "Audit-traceability only.",
            "remedy": "Write 'PASS（分支 (c) + 证据）' in the AC3 verdict cell.",
        },
    ]

    checks_performed = [dict(c) for c in ver["checks"]]
    verdicts = {
        "upstream_package_wp-11930-01": {
            "verdict": "pass",
            "basis": "fresh hash == contract == manifest; 14/14 locators span-exact, unique, path token inside quote; counts recomputed; "
                     "6/6 figure bytes fetched from the platform match manifest platform_sha256/bytes and captions match the record figures[].",
        },
        "report_semantic_fidelity": {
            "verdict": "needs-fix",
            "basis": "all recomputable headline numbers reproduce (Jacobian spectrum/cond/rank, 24-entry correlation matrix exactly, power-law holdout "
                     "predictions, AC5/AC4b deviations, CI width, packing/density/geometry), and the report's honest FAILs are consistent with its "
                     "own numbers; but 7 findings (F1,F2,F3,F4,F5,F6,F10) require text/number corrections before the report can be cited.",
        },
        "overall": "needs-fix",
    }

    review_report = {
        "package_id": PACKAGE_ID,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "review_type": "adversarial-independent-review",
        "reviewed_package": REVIEWED_PACKAGE,
        "reviewed_artifacts": {
            "report_markdown": {"uri": "tensor://reports/11930", "sha256": ver["source"]["sha256"],
                                "chars": ver["source"]["chars"], "bytes_utf8": ver["source"]["bytes_utf8"]},
            "upstream_kf_result": {"path": "docs/kf/wp-11930-01/kf_result.wp-11930-01.json", "sha256": sha_file(UPSTREAM)},
        },
        "independence": {
            "statement": "Reviewer fetched report 11930 markdown fresh from GET /api/v1/tensor/reports/11930 and read only that markdown plus the "
                         "upstream wp-11930-01 asset manifest. No producer explanation, chat log, commit message or upstream narrative was consulted; "
                         "the reviewer did not read the producer's scripts beyond their registration entries.",
            "limitations": [
                "The TensorDEM checkout (module, scripts, test suite, records.jsonl, artifacts report.json) is not present in this repository, so DEM "
                "physics, the 42-item pytest suite, the 747-task campaign, the NSGA-II run and the KE/work gate were NOT re-executed.",
                "Six figure PNGs were byte-hashed against the manifest hashes but NOT visually compared against their caption claims.",
                "Mathematics was re-derived from the numbers printed in the report, so any mistake shared between the report text and the underlying "
                "pipeline would not be caught by this review (no primary-source model audit).",
            ],
        },
        "scope": [
            "semantic fidelity of every recomputable number in the report (geometry, packing, Jacobian spectrum/cond/rank, correlation matrix, "
            "Brun index, Weibull power-law holdout, AC4b protocol refinement, AC5 stress-ratio deviations, AC6/AC7 percentages)",
            "internal consistency of tables, verdicts and cross-references",
            "claim–evidence binding and severity of overstatements",
            "upstream asset-registration fidelity (hash, locators, counts, figure bytes)",
        ],
        "method": {
            "tool": "work/wp-11930-04/verify_wp-11930-04.py (fresh fetch + 35-machine-check ledger)",
            "ledger": "work/wp-11930-04/verify_wp-11930-04.json",
            "summary": ver["summary"],
            "quote_policy": "every quote in this review is a substring of the fresh markdown, stored with start/end char offsets (build_review.py asserts uniqueness)",
        },
        "checks_performed": checks_performed,
        "checks_not_run": [
            "pytest tests/test_bpm_calibration_feasibility.py (42 items) — TensorDEM checkout absent",
            "DEM campaign replay (747 tasks) and runs/p270w2c_n08/records.jsonl audit — asset referenced_unresolved",
            "NSGA-II / surrogate LOO R² recomputation — artifacts/p270w2c_n08/report.json absent (also declared absent in report §4 item 1b for the JSONL)",
            "KE/work quasi-static gate recomputation — raw traces absent",
            "visual inspection of the six PNG figures",
            "primary-source check against Schulson & Duval UCS band and Hondros solution — no文献 bytes in workspace",
        ],
        "key_verifications": [
            {"item": "source hash", "result": "sha256:5adb132d…dbf325 == contract == upstream manifest (fresh fetch, 13121 chars / 22324 bytes)"},
            {"item": "Jacobian spectrum from published J", "claim_locator": loc(Q["jac_row"]), "result": "5.8499 / 2.1483 / 0.6458, cond=9.0588 vs published 9.063 (0.05% rounding), rank=3"},
            {"item": "parameter correlation matrix", "result": "24 published entries reproduced exactly from JᵀJ (max |Δ|=0.000); mu_s/mu_d columns identically zero as claimed"},
            {"item": "Weibull holdout", "result": "from (m=262.976, σ_ref=3.71e5): 0.3753 MPa @t=0.05 (pub 0.376), 0.3713 MPa @t=0.80 (pub 0.372); errors -5.5% / +2.6% (pub -5.4% / +2.6%)"},
            {"item": "AC5 deviations", "claim_locator": loc(Q["ac5_sec"]), "result": "9.8 / 16.0 / 39.3 / 130.2 / 205.2 / 788.1% all recomputed exactly against Hondros −3.0"},
            {"item": "AC4b protocol refinement", "result": "0.8559 and 0.6728 MPa reproduce -15.2% / -33.4% vs 1.0098 MPa; t=0.4 m ±0.2% / +7.5%"},
            {"item": "AC6 count", "result": "83.5% of n=200 == 167/200 (integral); implies 33/200 inside band"},
            {"item": "upstream locators", "result": "14/14 span-exact, unique, path token inside quote"},
            {"item": "upstream figures", "result": "6/6 HTTP 200 image/png; sha256 and byte count equal manifest platform_sha256/platform_bytes; captions byte-identical to record figures[]"},
        ],
        "verdicts": verdicts,
        "findings": findings,
        "overstated_claims": [
            {"claim": loc(Q["ac6_method"]), "problem": "negative control described as showing random θ 'almost never' lands in the band; measured 16.5% do (AC6 itself FAILs)"},
            {"claim": loc(Q["ac5_row"]), "problem": "'差两个量级' contradicts the 9.8% in the same cell"},
            {"claim": loc(Q["localm_text"]), "problem": "'局部 m' values 0.080/0.045 are 1/m-like, not moduli comparable to m=262.976"},
            {"claim": loc(Q["ac7_row"]), "problem": "'相对差 0.000' exceeds the displayed 3-significant-figure precision"},
            {"claim": loc(Q["hd_row"]), "problem": "H/D=2.000 mixes gauge H with bounding-box D; uniform conventions give 2.25 or 2.667"},
            {"claim": loc(Q["ac3_row"]), "problem": "AC3 verdict cell gives no PASS/FAIL"},
        ],
        "disposition": {
            "decision": "request-changes",
            "label": "needs-fix",
            "blocking_issues": [],
            "rationale": "No finding invalidates the report's core conclusions (structural under-determination rank 3/6 with a 3-dim null space; "
                         "branch (c) infeasibility; honest FAILs on AC5 robustness, AC6, AC7 quasi-static gate). All recomputable headline numbers "
                         "reproduce. Seven corrections are required before the report is quoted downstream (major: F1 Brun index, F2 'local m' label, "
                         "F4 negative-control narrative; minor: F3 wording, F5 UCS H/D convention, F6 unpublished fit inputs, F10 AC3 "
                         "verdict cell); nothing warrants fail/reject. Upstream package wp-11930-01 passes every reviewer-side check.",
            "not_marked_verified": "This review does not mark any claim as verified; it records reviewer-side checks only.",
        },
        "repro_cmd": "bash work/wp-11930-04/repro.sh",
    }

    events = [
        {
            "id": "tkr:package:wp-11930-01",
            "object_ref": "tensor://packages/wp-11930-01",
            "object_version": sha_file(UPSTREAM),
            "decision": "approve",
            "reviewer": {"id": "agent/m19840", "reviewer_type": "agent", "role": "red-team-reviewer"},
            "reviewed_at": REVIEWED_AT,
            "policy_version": POLICY,
            "rationale": "Asset registration recomputed from fresh bytes: hash/chars/bytes match contract, 14/14 locator spans exact and unique, "
                         "counts recomputed, 6/6 figure assets return HTTP 200 image/png with manifest-matching sha256 and byte counts.",
            "findings": [
                {"severity": "informational", "finding": "7/14 assets are referenced_unresolved and 1 declared_absent — correct declarations; they cap what an independent review can re-execute."},
            ],
        },
        {
            "id": "tkr:report:11930",
            "object_ref": "tensor://reports/11930",
            "object_version": ver["source"]["sha256"],
            "decision": "request-changes",
            "reviewer": {"id": "agent/m19840", "reviewer_type": "agent", "role": "red-team-reviewer"},
            "reviewed_at": REVIEWED_AT,
            "policy_version": POLICY,
            "rationale": "Semantic fidelity: all recomputable headline numbers reproduce and the honest FAILs are internally consistent, but the Brun "
                         "index is unreproducible as published, the 'local m' column is mislabelled by 3 orders of magnitude, the AC5 error row "
                         "contradicts itself, the AC6 negative-control narrative overstates an 83.5% result, the UCS H/D mixes conventions, and the "
                         "AC3 verdict cell omits PASS/FAIL.",
            "findings": [{"severity": f["severity"], "finding": f"{f['id']}: {f['finding']}"} for f in findings],
        },
    ]

    kf_result = {
        "package_id": PACKAGE_ID,
        "task_type": "04-independent-review",
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": "tensor://reports/11930",
            "source_field": "markdown",
            "source_hash": ver["source"]["sha256"],
            "source_hash_matches": ver["source"]["sha256"] == "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
            "title": "BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）",
            "scenario_key": "p270w2c-n08-bpm-calibration-feasibility",
            "chars": ver["source"]["chars"],
        },
        "outputs": {
            "review_report.json": review_report,
            "review_events.json": events,
        },
    }

    for name, obj in (("review_report.json", review_report), ("review_events.json", events),
                      ("kf_result.wp-11930-04.json", kf_result)):
        with open(os.path.join(OUTDIR, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print(json.dumps({"out": OUTDIR, "findings": len(findings), "events": len(events),
                      "verdicts": {k: v.get("verdict", v) if isinstance(v, dict) else v for k, v in verdicts.items()}},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()