"""wp-79-04 independent review: invariants asserted by tests (no network needed).

The review claims in docs/kf/wp-79-04/review_report.json must be reproducible from
the frozen source and the programmatic checks. These tests assert that the claims
are *load-bearing*: they would fail if the report's numbers, quotes or criteria
coverage drifted.

Run: python -m pytest tests/test_kf_wp7904_review.py -q
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import kf_wp7904_review as chk  # noqa: E402

OUT = ROOT / "docs/kf/wp-79-04"
SRC = (OUT / "source.md").read_text(encoding="utf-8")
REPORT = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
ENVELOPE = json.loads((OUT / "kf_result.wp-79-04.json").read_text(encoding="utf-8"))
EVENTS = json.loads((OUT / "review_events.json").read_text(encoding="utf-8"))


def test_source_hash_matches_contract():
    got = "sha256:" + hashlib.sha256((OUT / "source.md").read_bytes()).hexdigest()
    assert got == chk.CONTRACT_HASH
    assert ENVELOPE["provenance"]["source_hash"] == got


def test_every_cited_quote_is_verbatim_and_non_trivial():
    checks = chk.check_quotes(SRC)
    assert checks["pass"] is True
    assert checks["quotes_found"] == checks["quotes_total"]
    assert checks["min_chars"] >= 12


def test_finding_quotes_match_source_at_declared_offsets():
    """E3/E4 spirit: text[start:end] == quote for every finding evidence item."""
    n = 0
    for finding in REPORT["findings"]:
        for ev in finding["evidence"]:
            s, e = ev["start_offset"], ev["end_offset"]
            assert SRC[s:e] == ev["quote"], finding["id"]
            assert ev["quote"] in SRC
            n += 1
    assert n >= 10


def test_numeric_pairs_are_rounding_consistent_but_tolerance_readings_diverge():
    c3 = chk.check_numeric(SRC)
    assert c3["pairs"] == 9
    assert c3["pairs_rounding_consistent"] == 9, "report's 9 numeric pairs must round consistently"
    assert c3["pass"] is True
    c4 = c3["C4"]
    # the report's own "±0.01%" must fail under the relative-error reading ...
    assert c4["pass_under_relative_reading"] is False
    assert len(c4["pairs_failing_relative_reading"]) == 4
    # ... while it passes under the absolute percentage-point reading: hence ambiguous
    assert c4["pass_under_absolute_pp_reading"] is True
    assert c3["max_rel_dev_pct"] > 0.01 > c3["max_abs_dev_pct_points"]


def test_declared_criteria_outnumber_recorded_outcomes():
    c5 = chk.check_criteria(SRC)
    assert c5["declared_criteria"] == 6
    assert c5["coverage_ratio"] == "4/6"
    assert set(c5["declared_but_unrecorded"]) == {"structure_five_sections", "no_overclaim"}
    assert c5["pass"] is False


def test_review_prompt_is_not_the_producer_prompt():
    c7 = chk.check_prompts()
    assert c7["jaccard_5gram"] < c7["threshold"]
    assert c7["pass"] is True


def test_verdict_is_needs_fix_and_fidelity_is_not_run():
    assert REPORT["verdict"] == "needs-fix"
    assert REPORT["axes"]["semantic_fidelity"]["status"] == "not_run"
    assert REPORT["axes"]["semantic_fidelity"]["pass"] is None
    assert any(f["severity"] == "blocking" for f in REPORT["findings"])
    assert REPORT["independence"]["producer_explanation_seen"] is False


def test_no_self_asserted_verification_fields():
    """S9 spirit: a reviewer must never stamp a verification label of its own."""
    blob = json.dumps([REPORT, ENVELOPE, EVENTS], ensure_ascii=False).lower()
    for banned in ("verified", "verification_status", "verification_level",
                   "is_verified", "gate_confirmed"):
        assert banned not in blob, banned


def test_envelope_and_review_events_pass_their_schemas():
    jsonschema.validate(ENVELOPE, json.loads(
        (ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8")))
    ev_schema = json.loads((ROOT / "schemas/review-event.schema.json").read_text(encoding="utf-8"))
    for event in EVENTS:
        jsonschema.validate(event, ev_schema)
    assert ENVELOPE["outputs"]["review_report.json"]["package_id"] == "wp-79-04"
    assert ENVELOPE["report_id"] == "79"


def test_upstream_probe_requires_a_positive_control():
    """The probe is only evidence when its control fires (records the bounded scan)."""
    checks = json.loads((ROOT / "runs/wp-79-04/checks.json").read_text(encoding="utf-8"))
    c6 = checks["C6"]
    assert c6["status"] == "run"
    assert c6["positive_control_pass"] is True, "probe void: control not found"
    assert c6["upstream_available"] is False
    assert c6["probe_a_newest_by_id"]["n"] >= 100
    assert c6["target"]["hits"] == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))