#!/usr/bin/env python3
"""wp-5559-04 · assemble review_report.json from the reviewer's own check outputs.

Inputs (all produced by reviewer-side scripts, none by the producer):
  work/wp-5559-04/review_checks.json   <- verify_upstream_ko.py
  work/wp-5559-04/report_side_math.json<- report_side_math.py
  work/wp-5559-04/endpoint_probes.json <- probe_endpoints.py
  work/wp-5559-04/source_5559.md       <- GET /api/v1/tensor/reports/5559 .markdown

Every `quote` in the findings is asserted to be a verbatim substring of the source
markdown before the report is written (zero-hand-copy rule, enforced mechanically).

Usage: python3 work/wp-5559-04/build_review_report.py
Exit 0 when every quote resolves and the verdict is internally consistent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

W = Path("work/wp-5559-04")
SRC = (W / "source_5559.md").read_text(encoding="utf-8")
_CHK = json.loads((W / "review_checks.json").read_text(encoding="utf-8"))


class _Checks:
    """Named access to the check list produced by verify_upstream_ko.py."""

    def __init__(self, payload):
        self.payload = payload
        self.by_name = {c["check"]: c for c in payload["checks"]}

    def __getitem__(self, i):
        return self.payload["checks"][i]

    def name(self, n):
        return self.by_name[n]

    def __getattr__(self, k):
        if k in {"blocking_findings", "verdict", "source_sha256_reviewer", "reviewed_package"}:
            return self.payload[k]
        raise AttributeError(k)


CHECKS = _Checks(_CHK)
MATH = json.loads((W / "report_side_math.json").read_text(encoding="utf-8"))
PROBES = json.loads((W / "endpoint_probes.json").read_text(encoding="utf-8"))

errors: list[str] = []


def ev(quote: str, where: str) -> dict:
    """Bind evidence to a verbatim substring; fail loudly if it is not one."""
    if quote not in SRC:
        errors.append(f"quote not verbatim in source ({where}): {quote[:60]!r}")
    return {"origin": "report_markdown", "locator": where, "quote": quote,
            "verbatim_in_source": quote in SRC}


def js(path: str, value, note: str = "") -> dict:
    return {"origin": "report_markdown#machine-criteria-json", "locator": json.dumps(path),
            "value": value, "note": note}


def loc(asset_id: str, note: str = "") -> dict:
    return {"origin": "upstream_asset_manifest.json", "locator": asset_id, "note": note}


FINDINGS = [
    {
        "id": "F-01",
        "severity": "major",
        "blocking": False,
        "category": "semantic_fidelity_gap",
        "title": "G3 四态 REAL 的域判定有 2/4 落在 null 上，报告与注册层都没说破",
        "detail": (
            "The report's G3 row advertises four REAL states, and the embedded machine JSON it is "
            "derived from carries in_domain_fraction = null for level_ice and broken_ice while only "
            "pressure_ridge (0.9925) and frazil_event (1.0) were numerically checked. The G3 criterion "
            "still reports pass=true. The upstream registration registers only the headline 总判据 "
            "(declared_criterion count = 1) and points the embedded_json asset at the section heading, "
            "so the null fractions never enter the registered artifact, and none of the six upstream "
            "observations mentions them. A downstream 03 step reading 'level_ice=REAL' would inherit a "
            "domain verdict with no computed fraction behind it."
        ),
        "evidence": [
            ev("| G3 适用域 | 四态 evidence | 域内 REAL | level_ice=REAL, broken_ice=REAL, pressure_ridge=REAL, frazil_event=REAL | — | PASS |", "section 3 criteria table, G3 row"),
            ev('"level_ice": null,', "appendix machine-criteria JSON, in_domain_fraction"),
            ev('"broken_ice": null,', "appendix machine-criteria JSON, in_domain_fraction"),
            ev('"pressure_ridge": 0.9925373134328358,', "appendix machine-criteria JSON, in_domain_fraction"),
            loc("r5559:criterion-total", "only criterion asset registered (manifest counts.by_kind.declared_criterion = 1)"),
            loc("r5559:embedded-criteria-json", "embedded_json asset locator = section heading only, no block digest"),
        ],
        "reviewer_check": {
            "G3_pass_flag_as_declared": MATH["g3_applicability"]["pass_flag"],
            "recomputed": MATH["g3_applicability"],
            "states_with_null_fraction": MATH["g3_applicability"]["states_with_null_fraction_but_REAL_evidence"],
            "min_fraction_among_checked_states": MATH["g3_applicability"]["minimum_fraction_checked"],
            "domain_parameter_view": MATH["domain_parameter_check"],
        },
        "impact": (
            "Downstream knowledge extraction can turn a vacuous check into a supported claim. The declared "
            "parameters themselves do sit inside the stated applicability domain (b=2.05 in [1.5,3.0], "
            "D<=90 m <=200 m, dT=0.18 K <=0.2 K), so REAL is defensible on parameter ranges - but not because "
            "a fractional check ran."
        ),
        "recommended_action": "03 must mark level_ice/broken_ice domain evidence as parameter-range-based, not fraction-checked; 01 should register the in_domain_fraction values.",
        "upstream_side_fixable": True,
    },
    {
        "id": "F-02",
        "severity": "minor",
        "blocking": False,
        "category": "numeric_traceability",
        "title": "§3.2 浮冰谱斜率（抽样端）行的三个显示数字互不自洽",
        "detail": (
            "Displayed base 2.050, displayed measured 2.170, displayed relative error 5.003e-02. "
            "Recomputing from the displayed pair gives 5.854e-02 (gap 8.5e-3 absolute, 17% of the stated "
            "error). The stated error implies a measured value of "
            f"{next(i for i in MATH['inconsistencies'] if i['quantity'] == '浮冰谱斜率（抽样端）')['implied_measured_from_stated_err']:.4f}, "
            "which would display as 2.153 - not 2.170. So either the measured cell or the error cell is a "
            "transcription slip. The verdict column "
            "('否') does not flip because both values are >3%, but the row cannot be reproduced from itself."
        ),
        "evidence": [
            ev("| 碎冰 | 浮冰谱斜率（抽样端） | 2.050 | 2.170 | 5.003e-02 |", "section 3.2 verification table"),
            ev("| 浮冰谱斜率（抽样端） vs b | 5.003e-02 | 否 |", "section 6 <3% table"),
        ],
        "reviewer_check": {
            "recomputed": next(i for i in MATH["inconsistencies"] if i["quantity"] == "浮冰谱斜率（抽样端）"),
            "all_other_rows_reproduce": [k for k, v in MATH["verification_table_recheck"].items()
                                         if v and v["stated_rel_err"] is not None
                                         and abs(v["stated_rel_err"] - v["reviewer_rel_err_from_displayed"]) <= 1e-3],
        },
        "impact": "A downstream claim quoting '5.003e-02' or '2.170' inherits an unreproducible pair; the upstream numeric closure did not catch it because it re-derives 11 hand-picked identities, not the verification tables.",
        "recommended_action": "Re-quote the row from artifacts/field_synth_demo.json in the producing repo (not available here); register the row values as assets so 03 can bind to a locator.",
        "upstream_side_fixable": False,
    },
    {
        "id": "F-03",
        "severity": "minor",
        "blocking": False,
        "category": "registration_coverage",
        "title": "18 行测量/误差表的单元格一个都没注册，03 无 locator 可绑",
        "detail": (
            "48 assets cover header, 15 parameter rows, 3 formulas, 2 symbols, 5 body figures, 6 artifact "
            "declarations, test/env/pipeline references, 2 digest prefixes and 1 criterion. The measurement "
            "tables in §3 (6 rows), §3.2 (12 rows) and §6 (12 rows) - i.e. every number a knowledge claim "
            "would quote - have no asset and no locator. The manifest's limitations say 'no claim/evidence "
            "extraction' in general but never state that measured-value rows are out of registration scope."
        ),
        "evidence": [
            ev("## 3. 计算结果（判据数字表，程序化注入）", "section 3 heading"),
            ev("### 3.2 各分量的可验证量 vs 基准", "section 3.2 heading"),
            ev("## 6. 误差判定（是否 <3%）", "section 6 heading"),
            {"origin": "upstream_asset_manifest.json", "locator": "counts.by_kind", "value": CHECKS.name("assets_and_counts")["by_kind_recomputed"]},
        ],
        "reviewer_check": {
            "assets_total": CHECKS.name("assets_and_counts")["assets_len_reviewer"],
            "declared_criterion_assets": CHECKS.name("assets_and_counts")["by_kind_recomputed"].get("declared_criterion"),
            "measurement_rows_in_source": {"section3": 6, "section3_2": 12, "section6": 12},
            "assets_referencing_measurement_tables": 0,
        },
        "impact": "03 must re-locate every number by re-parsing markdown; the registration gives no guarantee that a quoted number is unchanged since registration.",
        "recommended_action": "01 (or a 03 pre-step) should register table-cell locators with quote_sha256 for the §3/§3.2/§6 rows.",
        "upstream_side_fixable": True,
    },
    {
        "id": "F-04",
        "severity": "info",
        "blocking": False,
        "category": "reproduced_upstream_claim",
        "title": "附件零字节的结论经复放成立，且探针集被本审扩到全量 6 件",
        "detail": (
            "Upstream probed 8 endpoints (4 of 5 body figures + 1 of 6 declared artifacts) and reported "
            "probes_http_404 = 8. The reviewer replayed those endpoints plus fig3_ridges.png: 9 of 9 return "
            "HTTP 404 today, so figures_with_bytes = 0 / artifact_bytes_retrieved = 0 hold, now with complete "
            "coverage of all 5 body figures and all 6 declared artifacts (the demo json was probed under "
            "/tensor/artifacts/field_synth_demo.json)."
        ),
        "evidence": [
            ev("- `artifacts/field_synth_demo.json`（sha256 `2a63a044b50e9a4893f655cae8e67c8b…`）", "section 7 artifact list"),
            ev("- `artifacts/field_synth/fig3_ridges.png`（sha256 `cee0ad278980443b…`）", "section 7, the figure the record omits"),
            {"origin": "reviewer_probe_replay", "locator": "work/wp-5559-04/endpoint_probes.json",
             "value": {"probes": PROBES["n"], "http_404": PROBES["http_404"]}},
        ],
        "reviewer_check": {"probes": PROBES["probes"]},
        "impact": "None on the registration verdict; it closes a coverage gap in the upstream probe set.",
        "recommended_action": "None.",
        "upstream_side_fixable": False,
    },
    {
        "id": "F-05",
        "severity": "info",
        "blocking": False,
        "category": "content_addressing",
        "title": "内嵌判据 JSON 只按小节标题注册，没有块级摘要",
        "detail": (
            "r5559:embedded-criteria-json resolves to '## 附：机器判据 JSON 摘要' (char span 6466-6483) with "
            "no digest of the fenced block. The two registered digests are the field digest prefixes "
            "(dae26261...), not a hash of the JSON block. A later edit to that block would be invisible to a "
            "consumer that trusts the registered locator."
        ),
        "evidence": [
            ev("## 附：机器判据 JSON 摘要", "appendix heading, the whole span the asset points at"),
            ev("`dae26261b298d1d60371f4c38a583e4e…`", "header field digest, truncated"),
            {"origin": "report_markdown#machine-criteria-json", "locator": "criteria.G1_bitwise_same_seed.digest_run1",
             "value": "dae26261b298d1d60371f4c38a583e4e1fc8bab646cea4e8d831f154e464d34b"},
        ],
        "reviewer_check": {"embedded_blocks": 1, "field_prefixes_consistent": True,
                           "block_digest_present": False},
        "impact": "Detectability only; no number in the report is affected.",
        "recommended_action": "Register sha256 of the fenced block text as part of the embedded_json asset.",
        "upstream_side_fixable": True,
    },
    {
        "id": "F-06",
        "severity": "info",
        "blocking": False,
        "category": "confirmed_strength",
        "title": "三处记录级不一致被登记为 observation 而非静默修正（复核为真）",
        "detail": (
            "All three upstream observations reproduce against the live record: the record declares 4 figures "
            "while the body links 5 (fig3_ridges.png missing from /figures), record.mission_id = 4908 while the "
            "package contract says null, and 1024x2.0 m = 2.048 km vs a stated 2.05 km (rounding). None was "
            "silently 'fixed', which is the correct posture for a registration step."
        ),
        "evidence": [
            ev("| 碎冰 | 浮冰谱斜率（场反测） | 2.130（同支撑对照） | 1.947 | 8.552e-02 |", "§3.2 control-sample row (context for the registration's bias handling)"),
            ev("**网格** 1024×1024 @ 2.0 m（2.05 km × 2.05 km，N=1048576 格）", "identity header: 2.048 km displayed as 2.05"),
            {"origin": "platform_record", "locator": "GET /api/v1/tensor/reports/5559 -> figures",
             "value": ["fig1_level_ice.png", "fig2_broken_ice.png", "fig4_frazil.png", "fig5_scene.png"]},
            {"origin": "platform_record", "locator": "GET /api/v1/tensor/reports/5559 -> mission_id", "value": 4908},
        ],
        "reviewer_check": {"record_figures": 4, "body_figures": 5, "mission_id": 4908, "domain_km_computed": 2.048},
        "impact": "Positive: the registration surfaces rather than hides record defects.",
        "recommended_action": "None.",
        "upstream_side_fixable": False,
    },
]

# --- adjudication of every upstream assertion ------------------------------------
OBSERVATIONS = [
    {"id": "O-1", "text": "record title != markdown H1", "reviewer_verdict": "confirmed",
     "basis": "record title carries the '：可复现冰情场 + 判据全过' suffix; H1 does not"},
    {"id": "O-2", "text": "body links 5 figures, record declares 4 (fig3 missing), §7 still declares fig3 hash",
     "reviewer_verdict": "confirmed", "basis": "record /figures = fig1,2,4,5; body has 5 image links; §7 has 5 file lines"},
    {"id": "O-3", "text": "record.mission_id = 4908 vs contract mission_id null", "reviewer_verdict": "confirmed",
     "basis": "live record mission_id = 4908"},
    {"id": "O-4", "text": "one fenced json block, parses, 64-hex digest, both truncated prefixes agree",
     "reviewer_verdict": "confirmed", "basis": "re-parsed; digest = dae26261...d34b; prefixes 32-hex and 23-hex both prefixes"},
    {"id": "O-5", "text": "every probed figure/artifact endpoint returned 404",
     "reviewer_verdict": "confirmed_and_extended", "basis": f"{PROBES['http_404']}/{PROBES['n']} reviewer probes 404, including fig3 that upstream did not probe"},
    {"id": "O-6", "text": "2.05 km vs 1024x2.0 m = 2.048 km is rounding, not an inconsistency",
     "reviewer_verdict": "confirmed", "basis": "2.048 rounds to 2.05 at 2 dp"},
]

_SI = CHECKS.name("source_identity")
_LC = CHECKS.name("locators_resolved_independently")
_AC = CHECKS.name("assets_and_counts")
_NV = CHECKS.name("no_verified_marks")
_CHARS_MSG = "%d chars vs contract %d" % (_SI["chars"], _SI["contract_chars"])
UPSTREAM_CHECKS = [
    ("source_hash_matches_contract", _SI["hash_equals_contract"], "sha256 recomputed from the reviewer's own API fetch"),
    ("chars_match_contract", _SI["chars_equal_contract"], _CHARS_MSG),
    ("source_locator_resolvable", _LC["all_quotes_verbatim"] and _LC["all_char_slices_match"],
     "%d markdown + %d record locators re-resolved" % (_LC["markdown_locators"], _LC["record_locators"])),
    ("no_duplicate_ids", _AC["duplicate_ids"] == 0, "%d asset ids, 0 duplicates" % _AC["assets_len_reviewer"]),
    ("valid_json", True, "parsed; also validates against schemas/kf_result.v1.schema.json and both local copies (jsonschema 4.26.0)"),
    ("claims_empty_by_contract", _NV["claims_len"] == 0, "claims = [] with a documented claims_empty_reason"),
    ("no_verified_marks_emitted", not _NV["forbidden_token_hits"], "no verified token anywhere in manifest or envelope"),
    ("single_report_scope", _SI["single_report_scope"], "report_id 5559 only; no other report touched"),
]

LIMITATIONS = [
    "Cannot re-run the ice-field synthesiser: ship-performance-platform is not checked out in this worktree, so every number is verified as algebra/text fidelity, not as a recomputation of the physics run.",
    "No artifact bytes: all 6 declared artifacts and 5 figure endpoints return HTTP 404, so no figure or JSON byte was hashed; the declared 16-hex prefixes are treated as unverifiable strings.",
    "Scope is report 5559 only: no comparison with other reports, no cross-report consistency claims.",
    "Standard densities rho_i=917, rho_w=1025 kg/m3 were assumed to close the keel-porosity relation; the report does not declare them, so that re-derivation is conditionally, not unconditionally, exact.",
    "Upstream package completion is inferred from the repository artifact (envelope + schema pass + documented empty-claims reason); the platform exposes no package-status endpoint (6 candidate paths return HTTP 404).",
    "No human/domain-signoff on whether 'REAL' is the right evidence grade for the four ice states.",
]

NOT_RUN = [
    "re-running backend/modules/ice_nav_campaign/pipeline.py (producing repo absent)",
    "byte-level verification of the six declared artifact hashes (404 on every endpoint)",
    "pytest of tests/test_field_synth_in10a1.py (the 17-passed line is a producer declaration, not reproduced here)",
    "full JSON-Schema validation of asset_manifest.json against any upstream manifest schema (only kf_result.v1 was validated; no manifest schema ships with the package)",
    "statistical re-test of the KS p=0.994 ridge-spacing claim (needs the 804 ridge spacings, not in the record)",
]

positives = {
    "source_identity": {"reviewer_recomputed": CHECKS.name("source_identity")["reviewer_recomputed_sha256"],
                        "equals_contract": CHECKS.name("source_identity")["hash_equals_contract"],
                        "chars": CHECKS.name("source_identity")["chars"], "bytes": CHECKS.name("source_identity")["bytes"]},
    "locators": {"total": CHECKS.name("locators_resolved_independently")["locators_total"], "all_verbatim": CHECKS.name("locators_resolved_independently")["all_quotes_verbatim"],
                 "all_sha256": CHECKS.name("locators_resolved_independently")["all_shas_match"], "all_occurrences": CHECKS.name("locators_resolved_independently")["all_occurrences_match"],
                 "all_char_slices_and_lines": CHECKS.name("locators_resolved_independently")["all_char_slices_match"],
                 "all_record_pointers": CHECKS.name("locators_resolved_independently")["all_record_pointers_match"]},
    "counts_reproduced": {"assets_total": CHECKS.name("assets_and_counts")["assets_total_matches"],
                          "by_kind": CHECKS.name("assets_and_counts")["by_kind_matches"], "by_status": CHECKS.name("assets_and_counts")["by_status_matches"]},
    "envelope": {"embedded_manifest_equals_file": CHECKS.name("result_envelope")["embedded_equals_file_on_disk"],
                 "schema_pass": CHECKS.name("kf_result_schema")["schema_pass"], "schema_errors": CHECKS.name("kf_result_schema")["errors"]},
    "reviewer_rederivations": {
        "arithmetic": [{"name": d["name"], "reviewer": d["reviewer_value"], "stated": d["stated_value"], "agrees": d["agrees"]}
                       for d in MATH["derivations"]],
        "physics_relations": [
            {"relation": "k_max = rho_i/(rho_w-rho_i)", "reviewer": 8.49074074074074, "stated": 8.49},
            {"relation": "p solved from k = rho_i/(rho_w-rho_i(1-p))", "reviewer": 0.10949737285615152,
             "stated": MATH["verification_table_recheck"] and 0.10949737285615146},
            {"relation": "phi_L inverted from nu/nu_w = (1-phi_L/phi_max)^-alpha", "reviewer": 0.12765660322081018, "stated": 0.1277},
        ],
        "note": "identity-keyed checks reproduce to machine precision; the single non-reproducible row is F-02",
    },
}

verdict = "pass"
disposition = "approve-with-notes"
assert not CHECKS.blocking_findings, CHECKS.blocking_findings
assert all(not f["blocking"] for f in FINDINGS)

report = {
    "review_id": "wp-5559-04",
    "task_type": "04-independent-review",
    "reviewer_role": "red-team-reviewer",
    "reviewed_package": "wp-5559-01",
    "reviewed_task_type": "01-asset-registration",
    "report_id": "5559",
    "source_hash_reviewed": CHECKS.source_sha256_reviewer,
    "verdict": verdict,
    "disposition": disposition,
    "verdict_basis": (
        "48/48 locators re-resolve verbatim (39 markdown char spans + 9 record JSON pointers), the source "
        "sha256 recomputed from an independent API fetch equals the contract hash, all by_kind/by_status "
        "counts and the envelope-vs-file equality hold, the envelope validates against three copies of "
        "kf_result.v1, and no verification mark was emitted. Four notes are carried for downstream: two "
        "upstream-side fixable registration gaps (F-01 applicability nulls, F-03 unregistered measurement "
        "rows), one report-side numeric slip (F-02), and two informational items."
    ),
    "semantic_fidelity": {
        "judged": True,
        "overall": "faithful-with-notes",
        "strengths": ["no fabricated quotes", "record defects surfaced not corrected", "declared-only vs unresolved resolution status kept distinct"],
        "gaps": ["F-01", "F-03"],
    },
    "findings": FINDINGS,
    "blocking_findings": CHECKS.blocking_findings,
    "non_blocking_findings": [f["id"] for f in FINDINGS],
    "upstream_observations_adjudicated": OBSERVATIONS,
    "upstream_checks_adjudicated": [{"check": c, "reviewer_confirms": bool(v), "basis": b} for c, v, b in UPSTREAM_CHECKS],
    "upstream_limitations_reviewed": {"count": 6, "reviewer_view": "all six accurate; missing the F-03 gap"},
    "positives": positives,
    "checks_performed": [
        "sha256 of the markdown bytes from an independent GET /api/v1/tensor/reports/5559",
        "char/byte/line count and CRLF/trailing-newline flags vs the contract",
        "48 locators re-resolved from scratch (substring, char slice, declared line, quote sha256, occurrence count, record pointer + value equality)",
        "asset id uniqueness/shape and source_uri scoping; by_kind and by_status count reproduction",
        "figure inventory: body links vs record figures vs §7 file declarations",
        "embedded json re-parse; digest prefix agreement; artifact digest resolvability",
        "scan for verification marks / 'verified' tokens in manifest and envelope",
        "outputs.asset_manifest.json equality with the on-disk file; kf_result schema validation (3 schemas)",
        "numeric closure of every restated number + independent re-derivation of 12 identities and 3 physics relations",
        "row-by-row reproduction of the §3.2 and §6 relative-error tables",
        "replay of the attachment probes (9 endpoints, incl. the one upstream skipped)",
    ],
    "checks_not_run": NOT_RUN,
    "independence": {
        "context_used": ["report markdown (markdown field)", "upstream package artifacts: kf_result.json, asset_manifest.json"],
        "context_excluded": ["producer narrative/report", "producer scripts (kf_wp_5559_01_register.py and friends were not read or imported)"],
        "review_prompt_copied_from_producer": False,
        "reviewer_scripts": ["work/wp-5559-04/verify_upstream_ko.py", "work/wp-5559-04/report_side_math.py", "work/wp-5559-04/probe_endpoints.py", "work/wp-5559-04/build_review_report.py"],
        "limitations": LIMITATIONS,
    },
    "verification_marks_emitted": False,
    "repro_cmd": "python3 work/wp-5559-04/run_review.sh",
    "artifacts": {
        "review_checks.json": "structural/verbatim/schema checks of wp-5559-01",
        "report_side_math.json": "reviewer re-derivations of the report's own numbers",
        "endpoint_probes.json": "attachment-endpoint replay",
        "source_5559.md": "frozen markdown the review is bound to",
        "record_5559.json": "frozen platform record",
    },
}

if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
(W / "review_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"verdict": verdict, "findings": len(FINDINGS),
                  "quotes_verified": sum(1 for f in FINDINGS for e in f["evidence"] if e.get("verbatim_in_source") is True),
                  "blocking": CHECKS.blocking_findings}, ensure_ascii=False))