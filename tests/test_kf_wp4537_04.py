#!/usr/bin/env python3
"""Tests for wp-4537-04 independent review package.

Run: python3 -m pytest tests/test_kf_wp4537_04.py -v
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "docs" / "kf" / "wp-4537-04"
REVIEW_PATH = PKG_DIR / "review_report.json"
ENVELOPE_PATH = PKG_DIR / "kf_result.json"
EVENTS_PATH = PKG_DIR / "review_events.json"
SNAPSHOT_PATH = PKG_DIR / "source_snapshot.md"
FIGURE_PATH = PKG_DIR / "fig1_review_4537_04.png"
UPSTREAM_MANIFEST = ROOT / "docs" / "kf" / "wp-4537-01" / "asset_manifest.json"

CONTRACT_SOURCE_HASH = "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08"
CONTRACT_CHARS = 7931
REPORT_ID = "4537"
PACKAGE_ID = "wp-4537-04"
UPSTREAM_PACKAGE = "wp-4537-01"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def review():
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def envelope():
    return json.loads(ENVELOPE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def events():
    return json.loads(EVENTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def snapshot():
    if not SNAPSHOT_PATH.exists():
        pytest.skip("source_snapshot.md not present (live-fetch mode)")
    return SNAPSHOT_PATH.read_text(encoding="utf-8")


@pytest.fixture
def upstream_manifest():
    return json.loads(UPSTREAM_MANIFEST.read_text(encoding="utf-8"))


# ---- Basic structure tests ----

def test_review_has_required_fields(review):
    assert review["package_id"] == PACKAGE_ID
    assert review["task_type"] == "04-independent-review"
    assert review["report_id"] == REPORT_ID
    assert review["reviewed_package"] == UPSTREAM_PACKAGE
    assert review["reviewer_role"] == "red-team-reviewer"
    assert review["verdict"] in ("pass", "fail")
    assert "verdict_scope" in review
    assert "verdict_rationale" in review


def test_envelope_validates(envelope):
    assert envelope["package_id"] == PACKAGE_ID
    assert envelope["task_type"] == "04-independent-review"
    assert envelope["report_id"] == REPORT_ID
    assert "provenance" in envelope
    assert "outputs" in envelope
    prov = envelope["provenance"]
    assert prov["source_hash"] == CONTRACT_SOURCE_HASH
    assert prov["source_chars"] == CONTRACT_CHARS


def test_events_structure(events):
    assert isinstance(events, list)
    assert len(events) > 0
    # Should have check events, finding events, and a verdict event
    check_events = [e for e in events if e.get("event") == "check"]
    finding_events = [e for e in events if e.get("event") == "finding"]
    verdict_events = [e for e in events if e.get("event") == "verdict"]
    assert len(check_events) >= 8
    assert len(verdict_events) == 1


# ---- Source integrity tests ----

def test_snapshot_hash_matches_contract(snapshot):
    assert len(snapshot) == CONTRACT_CHARS
    got_hash = "sha256:" + _sha256(snapshot)
    assert got_hash == CONTRACT_SOURCE_HASH


def test_review_source_hash_matches(review):
    src = review["source"]
    assert src["hash_recomputed"] == CONTRACT_SOURCE_HASH
    assert src["hash_declared"] == CONTRACT_SOURCE_HASH
    assert src["chars"] == CONTRACT_CHARS


# ---- Check result tests ----

def test_all_checks_pass(review):
    """All 9 checks should pass for a valid review."""
    checks = review["checks"]
    assert len(checks) == 9
    for c in checks:
        assert c["result"] == "pass", f"Check {c['id']} ({c['name']}) failed: {c['detail']}"


def test_verdict_is_pass(review):
    assert review["verdict"] == "pass"


def test_findings_are_non_blocking(review):
    """Findings should be low or medium severity, not blocking."""
    for f in review["findings"]:
        assert f["severity"] in ("low", "medium", "high")
        # High severity findings would typically block, but our review passes
        # so there should be no high-severity findings
        assert f["severity"] != "high", f"High severity finding should block: {f}"


# ---- Independence tests ----

def test_independence_declaration(review):
    indep = review["reviewer_independence"]
    assert indep["producer_explanation_consumed"] is False
    assert indep["upstream_self_verification_adopted_as_verdict"] is False
    assert indep["checks_recomputed_from_scratch"] is True


# ---- Upstream artifact tests ----

def test_reviewed_artifacts_hashed(review):
    artifacts = review["reviewed_artifacts"]
    assert len(artifacts) >= 2  # manifest + kf_result
    for a in artifacts:
        assert "path" in a
        assert "sha256" in a
        assert "bytes" in a
        # Verify the hash matches the actual file
        actual_path = ROOT / a["path"]
        if actual_path.exists():
            actual_hash = hashlib.sha256(actual_path.read_bytes()).hexdigest()
            assert a["sha256"] == actual_hash, f"Hash mismatch for {a['path']}"


# ---- Figure test ----

def test_figure_exists():
    assert FIGURE_PATH.exists()
    assert FIGURE_PATH.stat().st_size > 1000  # Should be a real PNG


# ---- Reproducibility test ----

def test_reviewer_is_recorded(review):
    assert review.get("reviewer") == "agent/m17509"


def test_upstream_gate_not_adopted(review):
    assert review["upstream_gate_record"]["adopted_as_verdict"] is False


# ---- Consistency between review and envelope ----

def test_envelope_matches_review(review, envelope):
    out = envelope["outputs"]["review_report.json"]
    assert out["package_id"] == PACKAGE_ID
    assert out["verdict"] == review["verdict"]
    assert out["checks_count"] == len(review["checks"])
    assert out["findings_count"] == len(review["findings"])
