"""Hermetic acceptance tests for KF work package wp-771-04 (report 771 independent review).

No network: every assertion is re-derived from the committed package artifacts
(`docs/kf/wp-771-04/evidence/{review_report.json,kf_result.json,review_checks.json,selfcheck.json}`).
The source copy is a byte-exact snapshot of report 771's markdown, so locator
resolution can be re-checked offline and independently of the platform.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-771-04" / "evidence"
REPORT_ID = "771"
EXPECTED_HASH = "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559"


@pytest.fixture(scope="module")
def review_report() -> dict:
    return json.loads((PKG / "review_report.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((PKG.parent.parent / "kf_result.json" if (PKG.parent.parent / "kf_result.json").exists()
                       else PKG / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review_checks() -> dict:
    return json.loads((PKG / "review_checks.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def selfcheck() -> dict:
    return json.loads((PKG / "selfcheck.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source_text() -> str:
    return (PKG / "source" / "report_771.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads((PKG / "review_report.v1.schema.json").read_text(encoding="utf-8"))


def test_envelope_matches_basic(envelope):
    assert envelope["package_id"] == "wp-771-04"
    assert envelope["task_type"] == "04-independent-review"
    assert envelope["report_id"] == REPORT_ID


def test_provenance_hash_matches_source_bytes(envelope, source_text):
    recomputed = "sha256:" + hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    assert envelope["provenance"]["source_hash"] == recomputed == EXPECTED_HASH
    assert envelope["provenance"]["source_field"] == "markdown"


def test_review_report_conforms_to_schema(review_report, schema):
    jsonschema.validate(review_report, schema)


def test_review_report_basic_fields(review_report):
    assert review_report["package_id"] == "wp-771-04"
    assert review_report["task_type"] == "04-independent-review"
    assert review_report["report_id"] == REPORT_ID
    assert review_report["reviewed_package"] == "wp-771-01"
    assert review_report["verdict"] == "needs-fix"


def test_reviewer_independence(review_report):
    reviewer = review_report["reviewer"]
    assert reviewer["independence_of_producer"] is True
    assert reviewer["producer_explanation_used"] is False
    assert reviewer["review_prompt_copied_from_producer"] is False


def test_findings_severity_ranked(review_report):
    severity_order = {"blocker": 0, "major": 1, "minor": 2, "cosmetic": 3}
    severities = [severity_order[f["severity"]] for f in review_report["findings"]]
    assert severities == sorted(severities), "Findings must be sorted by severity"


def test_findings_have_required_fields(review_report):
    for f in review_report["findings"]:
        assert "id" in f
        assert "severity" in f
        assert "category" in f
        assert "statement" in f
        assert "evidence" in f
        assert "analysis" in f
        assert "remediation" in f
        assert len(f["evidence"]) >= 1, f"Finding {f['id']} must have at least one evidence item"


def test_findings_evidence_quotes_in_source(review_report, source_text):
    for f in review_report["findings"]:
        for ev in f["evidence"]:
            if "quote" in ev:
                assert ev["quote"] in source_text, f"Finding {f['id']} quote not found in source"


def test_claims_use_valid_judgements(review_report):
    valid_judgements = {"supports", "qualifies", "refutes", "insufficient"}
    for c in review_report["claims"]:
        assert c["judgement"] in valid_judgements, f"Claim {c['claim_id']} has invalid judgement: {c['judgement']}"


def test_no_self_verified_claims(review_report):
    """No claim should be marked as verified by the reviewer."""
    for c in review_report["claims"]:
        assert c["judgement"] != "verified", f"Claim {c['claim_id']} must not be self-verified"


def test_checks_not_run_declared(review_report):
    assert len(review_report["checks_not_run"]) >= 1, "Must declare at least one check not run"


def test_independence_limitations_declared(review_report):
    assert len(review_report["independence_limitations"]) >= 1, "Must declare independence limitations"


def test_review_checks_all_pass(review_checks):
    for check in review_checks["checks"]:
        assert check["status"] == "pass", f"Check {check['check_id']} ({check['name']}) failed: {check.get('detail', '')}"
    assert review_checks["summary"]["failed"] == 0


def test_selfcheck_accepted(selfcheck):
    assert selfcheck["accepted"] is True
    assert selfcheck["failed"] == []


def test_verdict_consistent_with_blocker_findings(review_report):
    """If there are blocker findings, verdict must be needs-fix or escalate."""
    blockers = [f for f in review_report["findings"] if f["severity"] == "blocker"]
    if blockers:
        assert review_report["verdict"] in ("needs-fix", "escalate")


def test_source_hash_in_review_matches_envelope(review_report, envelope):
    assert review_report["source"]["sha256"] == envelope["provenance"]["source_hash"]


def test_figure_probe_exists():
    probe_path = PKG / "source" / "figure_probe.json"
    assert probe_path.exists(), "figure_probe.json must exist"
    probe = json.loads(probe_path.read_text())
    assert probe["figures_list_http_status"] == 404
    assert all(status == 404 for status in probe["binary_status"].values())


def test_kf_result_output_consistency(envelope, review_report, review_checks, selfcheck):
    """kf_result.json outputs must be consistent with the actual files."""
    outputs = envelope["outputs"]
    assert "review_report.json" in outputs
    assert outputs["review_report.json"]["verdict"] == review_report["verdict"]
    assert outputs["review_report.json"]["findings_count"] == len(review_report["findings"])
    assert outputs["review_checks.json"]["total_checks"] == review_checks["summary"]["total_checks"]
    assert outputs["selfcheck.json"]["accepted"] == selfcheck["accepted"]
