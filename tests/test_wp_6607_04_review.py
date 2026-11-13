"""Regression tests for the wp-6607-04 review deliverable (offline, no network).

These assert the shipped artefacts are self-consistent and traceable to the pinned
source snapshot — they do NOT re-judge the upstream package (that is
scripts/kf/wp_6607_04_review.py) and they do NOT mark anything as verified.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import jsonschema
import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
DOCS = REPO / "docs" / "kf" / "wp-6607-04"
SRC = REPO / "work" / "wp-6607-04" / "source" / "report_6607.md"
CONTRACT_HASH = ("sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1")
PKG = "wp-6607-04"


def load(name):
    return json.loads((DOCS / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def env():
    return load("kf_result.json")


@pytest.fixture(scope="module")
def review():
    return load("review_report.json")


@pytest.fixture(scope="module")
def md():
    return SRC.read_text(encoding="utf-8")


def walk_quotes(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "quote" and isinstance(v, str):
                yield f"{path}.{k}", v
            yield from walk_quotes(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_quotes(v, f"{path}[{i}]")


def test_source_snapshot_hash_matches_contract(env):
    digest = "sha256:" + hashlib.sha256(SRC.read_bytes()).hexdigest()
    assert digest == CONTRACT_HASH
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert env["provenance"]["source_field"] == "markdown"
    assert env["report_id"] == "6607"
    assert env["package_id"] == PKG


def test_envelope_validates_against_kf_result_schema(env):
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.validate(env, schema)
    assert "review_report.json" in env["outputs"]


def test_every_report_quote_is_verbatim(review, md):
    quotes = list(walk_quotes(review))
    assert quotes, "review report must cite the source at least once"
    bad = [p for p, q in quotes if q not in md]
    assert not bad, f"non-verbatim quotes: {bad}"


def test_report_markdown_has_exactly_one_json_block_equal_to_envelope(md, env):
    body = (DOCS / "report_markdown.md").read_text(encoding="utf-8")
    assert body.startswith(f"# KF-RESULT {PKG}")
    assert f"kf-wp:{PKG}" in body
    blocks = re.findall(r"```json\s*\n(.*?)```", body, flags=re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == env


def test_verdict_is_derived_from_checks_not_asserted(review):
    checks = review["checks"]
    fails = [c["check_id"] for c in checks if c["verdict"] == "fail"]
    assert review["verdict"] == ("pass" if not fails else "needs-fix")
    assert fails == ["body_path_reference_census"]
    assert review["blocking"] is False
    # the only failing check must be the one the blocking-free findings explain
    assert any(f["finding_id"].startswith("F1") for f in review["findings"])
    # independence + honesty surface
    assert review["reviewer_independent"] is True
    assert review["do_not_mark_claims_as_verified"] is True
    assert review["independence"]["reviewer_context_excluded"]


def test_claims_are_not_marked_verified(review):
    statuses = {c["status"] for c in review["claims_reviewed"]}
    assert statuses <= {"supported", "partially-supported", "unresolved", "refuted"}
    blob = json.dumps(review, ensure_ascii=False)
    assert not re.search(r'"status"\s*:\s*"verified"', blob)
    assert not re.search(r'"verified"\s*:\s*true', blob)