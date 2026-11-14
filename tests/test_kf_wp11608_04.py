"""wp-11608-04 acceptance invariants (independent review of report 11608).

Every assertion here is a mechanical check that can fail; nothing is asserted about the
producer's honesty, only about internal consistency of the delivered review and its
binding to the verbatim source.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-11608-04"
RUNS = ROOT / "runs" / PKG
DOCS = ROOT / "docs" / "kf" / PKG
SOURCE_HASH = "sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62"
REPORT_MD = DOCS / "KF-RESULT-wp-11608-04.md"


@pytest.fixture(scope="module")
def kf_result() -> dict:
    return json.loads((RUNS / "kf_result.wp-11608-04.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review(kf_result) -> dict:
    return kf_result["outputs"]["review_report.json"]


@pytest.fixture(scope="module")
def checks() -> dict:
    return json.loads((RUNS / "checks.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return (RUNS / "source_report_11608.md").read_text(encoding="utf-8")


def test_kf_result_validates_against_schema(kf_result):
    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(kf_result)
    assert kf_result["package_id"] == PKG
    assert kf_result["task_type"] == "04-independent-review"
    assert kf_result["report_id"] == "11608"
    assert kf_result["contract_version"] == "1.0"


def test_source_hash_matches_contract(kf_result):
    raw = (RUNS / "source_report_11608.md").read_bytes()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    assert digest == SOURCE_HASH
    assert kf_result["provenance"]["source_hash"] == SOURCE_HASH
    assert kf_result["provenance"]["source_hash_matches"] is True
    assert kf_result["provenance"]["chars"] == len(raw.decode("utf-8")) == 7342


def _iter_locators(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("quote"), str) and "start_char" in obj:
            yield obj
        for value in obj.values():
            yield from _iter_locators(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_locators(value)


def test_every_quote_is_verbatim_and_span_exact(review, source):
    locators = list(_iter_locators(review))
    assert len(locators) >= 9
    for loc in locators:
        quote = loc["quote"]
        assert quote in source, quote
        assert source[loc["start_char"] : loc["end_char"]] == quote
        assert source.count(quote) >= loc["occurrences"]
        assert loc["verbatim_in_source"] is True


def test_reviewer_independence_declared_and_bounded(review):
    ind = review["independence"]
    assert ind["producer_code_read"] is False
    assert ind["producer_tests_read"] is False
    assert ind["producer_artifacts_read"] is False
    assert ind["producer_explanations_read"] is False
    assert review["scope"]["report_ids_touched"] == ["11608"]


def test_no_claim_is_marked_verified(review):
    assert review["disposition"]["claims_marked_verified_by_this_review"] == 0
    blob = json.dumps(review, ensure_ascii=False)
    assert '"verified"' not in blob
    for item in review["reproduced_consistent_items"]:
        assert item["status"] == "reproduced_consistent"


def test_disposition_is_complete_and_consistent(review):
    disp = review["disposition"]
    assert disp["verdict"] in {"pass", "fail", "needs-fix"}
    assert disp["verdict"] == "needs-fix"
    assert disp["remediation"], "needs-fix must come with remediation"
    by_sev = {}
    for f in review["findings"]:
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1
        assert f["disposition"], f["id"]
        assert f["repro"], f["id"]
        assert f["impact"], f["id"]
    assert by_sev == review["severity_counts"]
    assert by_sev["major"] >= 1


def test_acceptance_self_check_covers_contract_keys(review):
    acc = review["acceptance_self_check"]
    for key in (
        "valid_json",
        "schema_pass",
        "reviewer_independent",
        "upstream_packages_completed",
        "do_not_mark_claims_as_verified",
        "review_prompt_not_copied_from_producer",
    ):
        assert key in acc and acc[key]["ok"] is True


def test_upstream_package_present_and_hash_agrees(review):
    up = review["reviewed_upstream"]
    assert up["package_id"] == "wp-11608-01"
    manifest = json.loads((ROOT / "docs/kf/wp-11608-01/asset_manifest.json").read_text(encoding="utf-8"))
    assert "sha256:" + manifest["integrity"]["hash_recomputed_locally"] == SOURCE_HASH
    assert (ROOT / "docs/kf/wp-11608-01/publish.json").exists()
    assert up["upstream_packages_absent"] == ["wp-11608-02", "wp-11608-03"]


def test_review_numbers_trace_back_to_checks(review, checks):
    r = review["outputs"] if "outputs" in review else review
    findings = {f["id"]: f for f in review["findings"]}
    assert findings["R1"]["reviewer_recomputation"]["max_dev_pct_reviewer"] == round(
        checks["a_upwind"]["max_dev_pct_reviewer"], 4
    )
    assert findings["R1"]["reviewer_recomputation"]["sign_contradictions"] == (
        checks["a_upwind"]["sign_contradictions"]
    )
    assert findings["R3"]["reviewer_recomputation"]["max_nu_reviewer"] == round(
        checks["c_lax_wendroff"]["max_nu_reviewer"], 6
    )
    assert findings["R5"]["reviewer_recomputation"]["cases_below_report_band"] == (
        checks["d_cd2"]["cases_below_report_band"]
    )
    assert findings["R6"]["reviewer_recomputation"]["reviewer_ratios"] == [
        round(x, 5) for x in checks["e_grid_convergence"]["reviewer_ratios"]
    ]
    assert r is not None


def test_physical_conclusions_recomputed_not_asserted(checks):
    # (a) the surviving upwind claim
    assert checks["a_upwind"]["max_dev_pct_reviewer"] < 1.0
    # (c) the surviving Lax-Wendroff bound, with the true margin
    assert checks["c_lax_wendroff"]["bound_holds"] is True
    assert 1e-2 / checks["c_lax_wendroff"]["max_nu_reviewer"] < 14.0
    # (d) |G| at pi/2 reproduced
    assert abs(checks["d_cd2"]["G_at_pi_over_2"]["C=0.5"] - 1.118034) < 1e-6
    # (e) halving reproduced inside the 5% tolerance
    assert checks["e_grid_convergence"]["max_ratio_dev_pct"] < 5.0
    # (f) the QUICK formula is refuted by its own symbol
    for row in checks["f_quick"]["comparisons"].values():
        assert row["ratio_exact_over_report_formula"] > 5.0
        assert abs(row["ratio_exact_over_reviewer_derived"] - 1.0) < 1e-3


def test_figures_present_and_nonempty():
    for name in (
        "fig1_upwind_deviation.png",
        "fig2_criterion_power.png",
        "fig3_quick_and_lw.png",
        "fig4_cd2_and_grid.png",
    ):
        p = DOCS / name
        assert p.exists() and p.stat().st_size > 10_000, name


def test_report_markdown_has_exactly_one_json_block():
    md = REPORT_MD.read_text(encoding="utf-8")
    assert md.count("```json") == 1
    assert md.count("```") == 2
    assert md.splitlines()[0].strip() == "KF-RESULT wp-11608-04"
    body = md.split("```json", 1)[1].split("```", 1)[0]
    payload = json.loads(body)
    staged = json.loads((DOCS / "kf_result.wp-11608-04.json").read_text(encoding="utf-8"))
    assert payload == staged
    # six mandated sections
    for marker in ("①", "②", "③", "④", "⑤", "⑥"):
        assert marker in md, marker


def test_boundary_only_report_11608_is_referenced():
    review = json.loads((RUNS / "review_report.json").read_text(encoding="utf-8"))
    assert review["scope"]["report_ids_touched"] == ["11608"]
    for f in review["findings"]:
        assert "report_id" not in f or f.get("report_id") == "11608"