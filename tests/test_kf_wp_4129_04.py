#!/usr/bin/env python3
"""Tests for wp-4129-04 (04-independent-review of wp-4129-01).

Pins the reviewer's own contract:
  * the envelope validates against schemas/kf_result.v1.schema.json
  * provenance.source_hash equals the sha256 of the report markdown bytes
  * every quote in review_report.json is a verbatim substring of that markdown
  * the verdict is internally consistent with the check table
  * the review touches report 4129 only and marks nothing verified
"""
import hashlib
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "work/wp-4129-04/source/report_4129.md"
REVIEW = ROOT / "work/wp-4129-04/review_report.json"
ENVELOPE = ROOT / "work/wp-4129-04/kf_result.json"
UPSTREAM = ROOT / "knowledge/kf/wp-4129-01/kf_result.json"
SCHEMA = ROOT / "schemas/kf_result.v1.schema.json"
DECLARED_HASH = "sha256:8670fa44138a8835fac88bbc2722e7b0b8f11c9f87ce8fa728ac0971c2a0f155"


@pytest.fixture(scope="module")
def md():
    return SRC.read_bytes().decode("utf-8")


@pytest.fixture(scope="module")
def envelope():
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review(envelope):
    return envelope["outputs"]["review_report.json"]


def test_envelope_validates_against_schema(envelope):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(envelope, json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_source_hash_equals_markdown_bytes(envelope, ):
    got = "sha256:" + hashlib.sha256(SRC.read_bytes()).hexdigest()
    assert envelope["provenance"]["source_hash"] == got == DECLARED_HASH


def test_envelope_scoped_to_report_4129(envelope):
    assert envelope["report_id"] == "4129"
    assert envelope["package_id"] == "wp-4129-04"
    assert envelope["task_type"] == "04-independent-review"
    assert envelope["provenance"]["source_field"] == "markdown"


def collect_quotes(obj):
    if isinstance(obj, dict):
        if {"quote", "line", "quote_sha256"} <= set(obj):
            yield obj
        for value in obj.values():
            yield from collect_quotes(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from collect_quotes(item)


def test_every_quote_is_verbatim(review, md):
    quotes = list(collect_quotes(review))
    assert len(quotes) >= 10
    for q in quotes:
        assert q["quote"] in md, q["quote"][:60]
        assert q["quote_sha256"] == "sha256:" + hashlib.sha256(q["quote"].encode()).hexdigest()
        assert q["source_field"] == "markdown"


def test_quote_line_numbers_are_correct(review, md):
    lines = md.rstrip("\n").split("\n")
    for q in collect_quotes(review):
        assert q["quote"] in lines[q["line"] - 1], (q["line"], q["quote"][:40])


def test_certified_checks_match_findings(review):
    cert = review["certified_by_review"]
    assert cert["checks_total"] == len(review["checks"])
    assert cert["checks_passed"] == sum(1 for c in review["checks"] if c["pass"])
    failing = {c["check_id"] for c in review["checks"] if not c["pass"]}
    assert failing == set(cert["failed_check_ids"])
    # the verdict must own every failing check
    assert failing == {"token_inside_locator_quote", "body_path_reference_census"}


def test_verdict_is_needs_fix_and_non_blocking(review):
    assert review["verdict"] == "needs-fix"
    assert all(f["blocking"] is False for f in review["findings"])
    assert len(review["findings"]) == 2


def test_finding_f1_points_at_the_real_token_line(review, md):
    lines = md.rstrip("\n").split("\n")
    f1 = [f for f in review["findings"] if f["finding_id"].startswith("F1")][0]
    assert f1["evidence"]["token"] not in f1["evidence"]["quote"]
    assert f1["evidence"]["token"] in lines[f1["evidence"]["token_actual_lines"][0] - 1]


def test_finding_f2_names_the_unregistered_site(review, md):
    lines = md.rstrip("\n").split("\n")
    f2 = [f for f in review["findings"] if f["finding_id"].startswith("F2")][0]
    missing = f2["evidence"]["missing_sites"]
    assert len(missing) == 1
    assert f2["evidence"]["missing_quote"]["quote"] == lines[missing[0]["line"] - 1]
    assert missing[0]["token"] in f2["evidence"]["missing_quote"]["quote"]


def test_no_verified_marks_anywhere(envelope):
    def strings(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from strings(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from strings(v)

    assert not [s for s in strings(envelope) if s.strip().lower() == "verified"]


def test_review_mentions_no_other_report(envelope):
    import re

    blob = json.dumps(envelope, ensure_ascii=False)
    ids = set(re.findall(r'"report_id"\s*:\s*"([0-9]+)"', blob))
    assert ids == {"4129"}
    uris = set(re.findall(r"tensor://reports/([0-9]+)", blob))
    assert uris <= {"4129"}


def test_delivered_markdown_carries_the_same_envelope(envelope):
    doc = (ROOT / "docs/kf/wp-4129-04.md").read_text(encoding="utf-8")
    assert doc.startswith("# KF-RESULT wp-4129-04")
    assert "kf-wp:wp-4129-04" in doc
    blocks = doc.split("```json")
    assert len(blocks) == 2, "exactly one ```json block expected"
    body = blocks[1].split("```")[0]
    assert json.loads(body) == envelope


def test_reviewed_upstream_hash_is_pinned(review):
    up = "sha256:" + hashlib.sha256(UPSTREAM.read_bytes()).hexdigest()
    pinned = [a for a in review["reviewed_artifacts"] if a["path"].endswith("kf_result.json")]
    assert pinned and pinned[0]["sha256"] == up


def test_review_states_what_it_did_not_check(review):
    assert len(review["checks_not_run"]) >= 3
    assert review["independence"]["review_prompt_not_copied_from_producer"] is True
    assert review["independence"]["no_claim_marked_verified"] is True