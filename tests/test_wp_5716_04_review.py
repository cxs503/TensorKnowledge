"""wp-5716-04 review invariants (worker-side).

These tests assert *mechanisms*, not vibes:
  * the verifier would actually catch quote drift (negative control);
  * every finding's evidence resolves to a verbatim substring of the frozen snapshot;
  * the recomputation is deterministic and the envelope matches the report block.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "kf"))

import review_wp_5716_04 as rv  # noqa: E402

SNAP = os.path.join(ROOT, rv.SNAP)
ENV = os.path.join(ROOT, "docs/kf/wp-5716-04/kf_result.json")
REP = os.path.join(ROOT, "docs/kf/wp-5716-04/report.md")
SCHEMA = os.path.join(ROOT, "schemas/kf_result.v1.schema.json")


@pytest.fixture(scope="module")
def md() -> str:
    return open(SNAP, "rb").read().decode("utf-8")


def test_source_hash_matches_contract() -> None:
    raw = open(SNAP, "rb").read()
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == rv.CONTRACT_HASH


def test_gate_would_catch_quote_drift(md: str) -> None:
    """Negative control: a mutated quote must NOT be found (the check has teeth)."""
    assert rv.Q["c3_totals"] in md
    mutated = rv.Q["c3_totals"].replace("63.3 h", "63.4 h")
    assert mutated not in md


def test_every_finding_evidence_is_verbatim(md: str) -> None:
    rec = rv.recompute(md)
    for f in rv.findings(rec) + rv.corroborated(rec):
        assert f["quote_keys"], f["id"]
        for k in f["quote_keys"]:
            assert k in rv.Q, f"{f['id']} cites unknown quote key {k}"
            assert rv.Q[k] in md, f"{f['id']} quote {k} drifted"


def test_recompute_is_deterministic(md: str) -> None:
    assert rv.recompute(md) == rv.recompute(md)


def test_recompute_key_numbers() -> None:
    rec = rv.recompute(open(SNAP, encoding="utf-8").read())
    # literal formula (no density) breaks G01's own 2% tolerance
    assert rec["a1_cb_literal_no_density"]["cb"] == pytest.approx(0.840577, abs=1e-6)
    assert rec["a1_cb_literal_no_density"]["rel_diff_pct_vs_0.82"] > 2.0
    # with rho = 1.025 t/m3 the reported Cb reproduces
    assert rec["a2_cb_with_rho_1p025"]["cb"] == pytest.approx(0.82007, abs=5e-5)
    # B2 12.4 reproduces at S-N slope m=3
    assert rec["a4_b2_beta_correction"]["utilization_after_correction"]["SN_slope_m=3"] == pytest.approx(12.4, abs=0.1)
    # disclosure enumeration gap
    assert rec["a10_disclosure_enumeration"]["named_n"] == 4
    assert rec["a10_disclosure_enumeration"]["gap"] == 3
    # time/energy reconstruction stays above the design point
    ice = rec["a6_ice_segment_speed_reconstruction"]["implied_mean_ice_kn"]
    assert ice["D1@54.5h"] > rec["a6_ice_segment_speed_reconstruction"]["reported_design_point_kn"]


def test_envelope_schema_and_single_block() -> None:
    env = json.load(open(ENV, encoding="utf-8"))
    jsonschema.validate(env, json.load(open(SCHEMA, encoding="utf-8")))
    assert env["package_id"] == "wp-5716-04"
    assert env["report_id"] == "5716"
    assert env["provenance"]["source_hash"] == rv.CONTRACT_HASH
    body = open(REP, encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)\n```", body, re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == env
    assert "kf-wp:wp-5716-04" not in body  # tag lives on the platform record, not in the body


def test_no_verified_marking() -> None:
    env = json.load(open(ENV, encoding="utf-8"))
    rev = env["outputs"]["review_report.json"]
    assert rev["verification_status"].startswith("NOT_VERIFIED")
    assert "verified" not in json.dumps(rev.get("outputs", {})).lower()
    assert rev["disposition"] in {"pass", "needs-fix", "fail"}


def test_review_only_touches_report_5716() -> None:
    env = json.load(open(ENV, encoding="utf-8"))
    blob = json.dumps(env, ensure_ascii=False)
    assert "tensor://reports/5716" in blob
    assert not re.search(r"tensor://reports/(?!5716)\d+", blob)