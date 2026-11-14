#!/usr/bin/env python3
"""Invariant tests for work package wp-11415-04 (04-independent-review).

The tests re-derive facts from the raw artifacts instead of trusting the
generator: the report markdown re-fetched from the platform, the published
envelope of the reviewed package, and the emitted review deliverables.

Run: python3 -m pytest tests/test_kf_wp_11415_04.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import jsonschema
import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = "wp-11415-04"
REPORT_ID = "11415"
EXPECTED_HASH = "d8bc42883f1fa1d274a3ca4808586d2a8773e9d0f464b554c944f5090b0c8c50"
RUN = REPO / "runs" / PACKAGE
ART = REPO / "docs" / "kf" / PACKAGE  # durable mirror (artifacts/ is git-ignored)
DOCS = REPO / "docs/kf" / PACKAGE
FENCE = chr(96) * 3
BLOCK_RE = re.compile(FENCE + r"json\n(.*?)\n" + FENCE, flags=re.S)


@pytest.fixture(scope="module")
def source_md() -> str:
    return (RUN / "report_11415.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads((ART / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review(result) -> dict:
    return result["outputs"]["review_report.json"]


@pytest.fixture(scope="module")
def upstream() -> dict:
    return json.loads((RUN / "upstream_asset_manifest_wp-11415-01.json").read_text(encoding="utf-8"))


def test_source_is_the_contract_document(source_md):
    assert hashlib.sha256(source_md.encode()).hexdigest() == EXPECTED_HASH
    assert len(source_md) == 7903


def test_envelope_matches_kf_result_schema(result):
    schema = json.loads((REPO / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(result, schema)


def test_envelope_identity(result):
    assert result["package_id"] == PACKAGE
    assert result["task_type"] == "04-independent-review"
    assert result["contract_version"] == "1.0"
    assert result["report_id"] == REPORT_ID
    prov = result["provenance"]
    assert prov["source_uri"] == "tensor://reports/11415"
    assert prov["source_field"] == "markdown"
    assert prov["source_hash"] == "sha256:" + EXPECTED_HASH
    assert prov["source_hash_matches"] is True
    assert prov["chars"] == 7903


def test_review_never_marks_anything_verified(result, review, upstream):
    blob = json.dumps([result, review, upstream], ensure_ascii=False)
    assert '"verification_status": "verified"' not in blob
    assert review["no_verified_marking"] is True
    assert review["verification_owner"] == "platform"
    assert upstream["integrity"]["verification_status"] == "not_verified"


def test_every_quote_is_a_unique_verbatim_substring(source_md, review):
    checked = 0
    for f in review["findings"]:
        for e in f["evidence"]:
            q = e.get("quote")
            if q is None:
                continue
            assert source_md.count(q) == 1, f"{f['id']} quote not unique"
            s, t = e["char_span"]
            assert source_md[s:t] == q
            assert source_md[:s].count("\n") + 1 == e["line"]
            assert "sha256:" + hashlib.sha256(q.encode()).hexdigest() == e["sha256"]
            checked += 1
    assert checked >= 8


def test_check_verdicts_are_consistent_with_disposition(review):
    summary = review["check_summary"]
    failed = [c["id"] for c in review["checks"] if c["status"] != "pass"]
    assert summary["total"] == len(review["checks"])
    assert summary["pass"] == summary["total"] - len(failed)
    assert summary["failed_ids"] == failed
    disp = review["disposition"]
    # a failure must never be laundered into a clean pass: the pipeline verdict
    # carries the blockers, and every blocker names a real major finding.
    if failed:
        assert disp["pipeline_verdict"] == "needs-fix"
        major = {f["id"] for f in review["findings"] if f["severity"] == "major"}
        assert set(disp["pipeline_blockers"]) <= major


def test_failed_checks_are_declared_not_hidden(review):
    failed = sorted(c["id"] for c in review["checks"] if c["status"] != "pass")
    assert failed == ["C6_schema", "C8_replay_upstream_verifier"]
    # the two failures must be explained by findings F1 and F2
    ids = {f["id"] for f in review["findings"]}
    assert {"F1", "F2"} <= ids


def test_checks_not_run_are_explicit(review):
    assert review["checks_not_run"], "an honest review must state what it did not run"
    for item in review["checks_not_run"]:
        assert item["status"] == "not_run"
        assert item["reason"]


def test_reviewer_independence_is_declared(review):
    rv = review["reviewer"]
    assert rv["independent"] is True
    assert rv["role"] == "red-team-reviewer"
    assert any("producer" in x for x in rv["context_excluded"])
    assert rv["limitations"]


def test_upstream_evidence_is_bound_to_the_committed_mirror(review):
    mirror = pathlib.Path(review["review_target"]["committed_mirror"])
    assert mirror.exists()
    assert hashlib.sha256(mirror.read_bytes()).hexdigest() == review["review_target"]["committed_mirror_sha256"]


def test_published_report_carries_exactly_one_json_block_matching_the_artifact(result):
    md = (DOCS / f"KF-RESULT-{PACKAGE}.md").read_text(encoding="utf-8")
    assert md.lstrip().startswith(f"# KF-RESULT {PACKAGE}")
    assert f"kf-wp:{PACKAGE}" in md
    blocks = BLOCK_RE.findall(md)
    assert len(blocks) == 1, "the report must carry exactly one fenced json block"
    assert json.loads(blocks[0]) == result
    assert FENCE + "json" not in json.dumps(result, ensure_ascii=False)


def test_report_states_the_six_sections_and_repro_cmd():
    md = (DOCS / f"KF-RESULT-{PACKAGE}.md").read_text(encoding="utf-8")
    for marker in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥", "repro_cmd"):
        assert marker in md


def test_estate_scan_number_in_finding_is_reproducible(review):
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    from kf_scan_estate_envelopes import scan

    claimed = [e for f in review["findings"] if f["id"] == "F2"
               for e in f["evidence"] if e["what"] == "estate-wide scan"][0]
    fresh = scan(REPO / "docs/kf", exclude=PACKAGE)
    assert fresh["packages_checked"] == claimed["packages_checked"]
    assert fresh["packages_invalid"] == claimed["packages_invalid"]
    assert fresh["envelopes_with_top_level_claims"] == claimed["envelopes_with_top_level_claims"]