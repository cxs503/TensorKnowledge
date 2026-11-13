"""Invariants for wp-6939-04 (independent review of report 6939 / wp-6939-01).

These tests do not re-state the review conclusions as prose; they assert the
properties that make the review *checkable*:

* the envelope pins the right source bytes and validates against the schema;
* every quote used as evidence is a byte-exact substring of the frozen source;
* the row accounting and the criterion-coverage adjudication are what the
  deliverable claims (so a silent edit of the deliverable fails here);
* the review emits no verification mark;
* the published markdown carries exactly one ```json block equal to kf_result.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "kf" / "wp-6939-04"
FIXTURE = REPO / "tests" / "fixtures" / "kf" / "6939_markdown.md"
SOURCE_HASH = "8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246"

sys.path.insert(0, str(REPO / "scripts" / "kf"))


@pytest.fixture(scope="module")
def md() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def kf() -> dict:
    return json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review(kf) -> dict:
    return kf["outputs"]["review_report.json"]


def test_fixture_is_the_reviewed_source(md):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == SOURCE_HASH
    assert len(md) == 2002


def test_envelope_pins_source(kf):
    assert kf["package_id"] == "wp-6939-04"
    assert kf["task_type"] == "04-independent-review"
    assert kf["report_id"] == "6939"
    assert kf["provenance"]["source_field"] == "markdown"
    assert kf["provenance"]["source_hash"] == f"sha256:{SOURCE_HASH}"
    assert kf["provenance"]["reviewed_package"] == "wp-6939-01"


def test_envelope_validates_against_schema(kf):
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(kf, schema)


def test_only_report_6939_is_touched(kf, review):
    blob = json.dumps(kf, ensure_ascii=False)
    assert review["report_id"] == "6939"
    assert "report_id\": \"6939" in blob
    # no other report id is claimed anywhere in the envelope keys
    assert kf["report_id"] == "6939"


def test_every_markdown_quote_is_verbatim(md, review):
    n = 0
    for item in review["findings"] + review["positives"]:
        for ev in item.get("evidence", []):
            if ev.get("source_field") != "markdown":
                continue
            n += 1
            assert ev["quote"] in md, f"{item.get('id', item.get('item'))}: quote not found: {ev['quote'][:60]}"
    assert n >= 20, "expected a substantive evidence set"


def test_row_accounting_is_reproducible(md, review):
    import wp6939_04_review as R

    rows = R.check_row_count(md)
    assert rows["table_rows_excluding_header"] == 22
    assert rows["claimed_n"] == 25
    assert rows["delta_claimed_vs_rows"] == 3
    assert rows["rows_result_only_qualitative"] == 6
    assert rows["rows_with_numeric_result"] == 16


def test_declared_criterion_10pct_is_absent_from_results(md):
    import wp6939_04_review as R

    tsh = R.check_threshold_inventory(md)
    assert tsh["c4_declared_10pct_present_in_results"] is False
    assert tsh["twenty_pct_present_in_section1"] is False
    assert "20%" in tsh["thresholds_in_results_table"]


def test_coverage_adjudication_matches_deliverable(md, review):
    import wp6939_04_review as R

    fresh = {c["anchor"]: c["exercised_as_declared"] for c in R.criterion_coverage(md)}
    stored = {c["anchor"]: c["exercised_as_declared"] for c in review["criterion_coverage"]}
    assert fresh == stored
    assert fresh["C1"] is fresh["C2"] is fresh["C7"] is True
    assert fresh["C3"] is False and fresh["C4"] is False
    assert fresh["C5"] is False and fresh["C6"] is False


def test_churchill_chu_inverse_is_stable(review):
    import wp6939_04_review as R

    ra = R.ra_for_nu(5.43, 0.71)
    assert abs(ra - 9977) / 9977 < 0.01, ra
    assert abs(R.churchill_chu_nu(ra) - 5.43) < 1e-6
    stored = review["independent_computations"]["churchill_chu_inverse"]
    assert abs(stored["bracket_half_width_pct_of_measured"] - 28.9) < 0.1


def test_verdict_shape(review):
    assert review["verdict"] in {"pass", "fail", "needs-fix"}
    assert review["verdict"] == "needs-fix"
    sev = review["severity_counts"]
    assert sev.get("BLOCKING", 0) >= 1
    assert sum(sev.values()) == len(review["findings"])
    ids = [f["id"] for f in review["findings"]]
    assert len(ids) == len(set(ids))
    for f in review["findings"]:
        assert f["statement"] and f["independent_check"] and f["remediation"]


def test_no_verification_mark_emitted(review, kf):
    assert review["verification_marks_emitted"] is False
    blob = json.dumps(kf, ensure_ascii=False).lower()
    assert "verified" not in blob
    for f in review["findings"]:
        assert f.get("status") != "verified"


def test_published_markdown_has_one_json_block_equal_to_kf(md, kf):
    text = (OUT / "REVIEW.md").read_text(encoding="utf-8")
    assert text.startswith("# KF-RESULT wp-6939-04")
    assert text.count("```json") == 1
    block = text.split("```json", 1)[1].rsplit("```", 1)[0]
    assert json.loads(block) == kf
    # six-section body required by the work package
    for tag in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert tag in text