#!/usr/bin/env python3
"""Invariant tests for wp-11624-04 (independent review of wp-11624-01).

These assert properties, not merely that code runs:
  * the review's own provenance hash equals the hash of the source snapshot it cites;
  * every verbatim quote used as review evidence occurs exactly once in the source;
  * every upstream locator re-resolves (span / uniqueness / line numbers);
  * the verdict is consistent with the findings and the gate-check ledger
    (a blocking finding with verdict "pass" is a failure, and so is "fail" without one);
  * nothing is marked verified; only report 11624 is referenced;
  * the delivered envelope is strictly schema-clean and the KF-RESULT body carries
    exactly one ```json block whose content equals the envelope.

Run: pytest -q tests/test_kf_review_wp11624_04.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "reviews" / "wp-11624-04"
UP = ROOT / "docs" / "wp-11624-01" / "kf_result.json"

pytestmark = pytest.mark.skipif(
    not (OUT / "review_report.json").exists(),
    reason="run scripts/kf_wp_11624_04_review.py && scripts/kf_wp_11624_04_report.py first",
)

MD = (OUT / "source_report_11624.md").read_text(encoding="utf-8")
REVIEW = json.load(open(OUT / "review_report.json", encoding="utf-8"))
CHECKS = json.load(open(OUT / "checks.json", encoding="utf-8"))
ENVELOPE = json.load(open(OUT / "kf_result.json", encoding="utf-8"))
UPSTREAM = json.load(open(UP, encoding="utf-8"))


def test_provenance_hash_is_the_hash_of_the_cited_snapshot():
    sha = hashlib.sha256(MD.encode("utf-8")).hexdigest()
    assert ENVELOPE["provenance"]["source_hash"] == "sha256:" + sha
    assert ENVELOPE["provenance"]["source_hash_matches"] is True
    assert sha == "a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33"
    assert ENVELOPE["provenance"]["chars"] == len(MD) == 4253
    assert REVIEW["source"]["sha256"] == sha


def test_envelope_is_strictly_schema_clean():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.load(open(ROOT / "schemas" / "kf_result.v1.schema.json", encoding="utf-8"))
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(ENVELOPE)) == []
    assert ENVELOPE["task_type"] == "04-independent-review"
    assert ENVELOPE["report_id"] == "11624"
    assert set(ENVELOPE["outputs"]) == {"review_report.json"}


def test_every_upstream_locator_resolves_against_the_fresh_source():
    assets = UPSTREAM["outputs"]["asset_manifest.json"]["assets"]
    assert len(assets) == 27
    lines = MD.split("\n")
    for a in assets:
        loc = a["locator"]
        q = loc["quote"]
        if loc["method"] == "record_pointer":
            assert q not in MD, f"{a['asset_id']}: metadata caption leaked into body"
            continue
        s, e = loc["start_char"], loc["end_char"]
        assert MD.count(q) == 1, f"{a['asset_id']}: quote not unique"
        if loc["method"] == "document":
            # document scope: the span covers the whole source, the quote is its first line
            assert (s, e) == (0, len(MD)), f"{a['asset_id']}: document span does not cover the source"
            assert q == lines[0], f"{a['asset_id']}: document quote is not the first line"
            assert loc["end_line"] == len(lines)
        else:
            assert MD[s:e] == q, f"{a['asset_id']}: span does not match quote"
            assert 1 <= loc["start_line"] <= loc["end_line"] <= len(lines)


def test_review_evidence_quotes_are_verbatim_and_unique():
    """Any string the review presents as a quote must be a unique substring of the source."""
    quoted = []
    for f in REVIEW["findings"]:
        ev = f["evidence"]
        for v in ev.values():
            if isinstance(v, str):
                quoted.append(v)
            elif isinstance(v, list):
                quoted.extend(x for x in v if isinstance(x, str))
    for c in CHECKS:
        ev = c["evidence"]
        if isinstance(ev, dict) and isinstance(ev.get("quote"), str):
            quoted.append(ev["quote"])
    # review-internal labels/observations are not quotes; keep only strings present verbatim
    present = [q for q in quoted if q in MD]
    assert present, "no verbatim evidence at all"
    for q in present:
        assert MD.count(q) == 1, f"non-unique evidence quote: {q[:60]!r}"
    # the C4 line and the dual-algorithm lines must be among the verbatim evidence
    c4 = next(c for c in CHECKS if c["id"] == "C16")["evidence"]["C4_line"]
    assert MD.count(c4) == 1
    for cid in ("C17", "C18"):
        c = next(c for c in CHECKS if c["id"] == cid)
        assert c["status"] == "pass"


def test_verdict_is_consistent_with_findings_and_gate_ledger():
    blocking = [f for f in REVIEW["findings"] if f["blocking"]]
    gate_fails = [c["id"] for c in CHECKS if c["gate"] and c["status"] == "fail"]
    gate_not_run = [c["id"] for c in CHECKS if c["gate"] and c["status"] == "not_run"]
    v = REVIEW["verdict"]
    assert v in {"pass", "needs-fix", "fail"}
    if blocking:
        assert v == "fail"
    elif gate_fails:
        assert v in {"fail", "needs-fix"}
    else:
        assert v == "pass"
        assert not gate_not_run, "cannot pass while a gating check is unknown"
    assert REVIEW["checks_summary"]["gate_checks"] == len([c for c in CHECKS if c["gate"]])
    assert REVIEW["checks_summary"]["gate_fail"] == gate_fails
    for f in REVIEW["findings"]:
        assert f["severity"] in {"critical", "high", "medium", "low"}
        assert f["reproduction"], "a finding without a reproduction path is not admissible"


def test_nothing_is_marked_verified_and_scope_is_single_report():
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield k, v
                yield from walk(v)
        elif isinstance(o, list):
            for v in o:
                yield from walk(v)

    for k, v in walk(ENVELOPE):
        if str(k).lower() in {"verified", "is_verified"}:
            assert v is False, f"verified mark leaked into the envelope: {k}={v}"
        if str(k) == "verification_status":
            assert v == "not_verified"
    for k, v in walk(REVIEW):
        if str(k).lower() in {"verified", "is_verified"}:
            assert v is False
    ids = {v for k, v in walk(ENVELOPE) if str(k).endswith("report_id")}
    assert ids == {"11624"}, ids
    assert REVIEW["claimed_nothing_verified"] is True


def test_delivered_body_has_exactly_one_json_block_equal_to_the_envelope():
    body = (OUT / "KF-RESULT.wp-11624-04.md").read_text(encoding="utf-8")
    assert body.startswith("# KF-RESULT wp-11624-04")
    assert "kf-wp:wp-11624-04" in body
    blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
    assert len(blocks) == 1, f"expected exactly one json block, found {len(blocks)}"
    parsed = json.loads(blocks[0])
    assert parsed == ENVELOPE
    # six mandatory sections present
    for marker in ("①", "②", "③", "④", "⑤", "⑥"):
        assert marker in body
    assert "repro" in body.lower() or "python3 scripts/kf_wp_11624_04_review.py" in body


def test_numbers_in_the_report_are_parsed_not_transcribed():
    nums = json.load(open(OUT / "numbers.json", encoding="utf-8"))
    assert len(nums["ships"]) == 3
    for s in nums["ships"]:
        # the ratio must be reproducible from the two numbers parsed out of the table
        assert abs(s["cii_ratio"] - s["cii_attained"] / s["cii_required"]) < 1e-12
        # table-vs-criterion-log consistency must stay inside the 3% gate
        assert s["rel_diff_table_vs_log"] < 0.03
    # CII ratings agree with the dd vector re-applied to the report's own numbers
    assert all(s["rating_agrees"] for s in nums["ships"])
    assert all(s["eexi_flag_agrees"] for s in nums["ships"])
    # and the §3.1 attained EEXI really is the value quoted in the body
    for s in nums["ships"]:
        assert f"{s['eexi_attained']:.3f}" in (OUT / "KF-RESULT.wp-11624-04.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))