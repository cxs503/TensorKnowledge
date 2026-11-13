"""wp-459-04 acceptance tests: the reviewer's own claims must be machine-checkable.

What is proven here:
  1. source identity      — the snapshot used for every quote hashes to the contract source_hash;
  2. zero hand-copy       — every quote cited in review_report.json is a byte-exact substring of it;
  3. numerics             — the re-derivations in verify_numbers.py reproduce the quoted numbers,
                            and the two negative findings (R-01/R-02) really are misfits, not noise;
  4. envelope legality    — the kf_result envelope (package_id/task_type/report_id/provenance/outputs)
                            validates against schemas/kf_result.v1.schema.json;
  5. no self-verification — the review never marks an upstream claim as verified;
  6. scope containment    — the review touches report_id 459 only.

Run: python3 -m pytest tests/test_wp45904_review.py -q
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "wp-459-04"
SRC = PKG / "source_snapshot.md"
CONTRACT_HASH = "sha256:333ea7e4c7b908bc9701a34c72960d0e0e8ed728798758fd68f830a75507f6b9"


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def source_text() -> str:
    return SRC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def review() -> dict:
    return json.loads((PKG / "review_report.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def verify() -> dict:
    return json.loads((PKG / "verify_results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def probe() -> dict:
    return json.loads((PKG / "platform_probe.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 1. identity
def test_source_snapshot_matches_contract_hash():
    digest = "sha256:" + hashlib.sha256(SRC.read_bytes()).hexdigest()
    assert digest == CONTRACT_HASH


def test_review_declares_the_same_source(review):
    assert review["source"]["source_hash"] == CONTRACT_HASH
    assert review["source"]["report_id"] == "459"
    assert review["report_id"] == "459"


# ---------------------------------------------------------------- 2. quotes
def _all_quotes(node, acc):
    if isinstance(node, dict):
        if "quote" in node and isinstance(node["quote"], str):
            acc.append(node)
        if node.get("evidence"):
            _all_quotes(node["evidence"], acc)
    elif isinstance(node, list):
        for item in node:
            _all_quotes(item, acc)
    return acc


def test_every_cited_quote_is_verbatim_in_source(review, source_text):
    quotes = _all_quotes(review["claims_assessed"] + review["findings"], [])
    quotes += _all_quotes(review["checks"], [])
    assert len(quotes) >= 20, f"only {len(quotes)} quotes cited"
    bad = [q["quote"] for q in quotes if q["quote"] not in source_text]
    assert bad == [], f"not verbatim: {bad}"


def test_quote_locators_are_byte_exact(review, source_text):
    located = [q for q in _all_quotes(review["claims_assessed"] + review["findings"], [])
               if "start_offset" in q]
    assert located, "no quote carries a byte locator"
    for q in located:
        start, end = q["start_offset"], q["end_offset"]
        assert 0 <= start < end <= len(source_text.encode())
        assert source_text[start:end] == q["quote"], q["quote"][:40]


def test_quote_locator_artifact_is_complete():
    loc = json.loads((PKG / "quote_locator.json").read_text(encoding="utf-8"))
    assert loc["missing"] == []
    assert loc["n_found"] == loc["n_quotes"] == len(loc["quotes"])


# ---------------------------------------------------------------- 3. numerics
def test_geometry_recomputes(verify):
    """Every geometric quantity of report 1 must fall out of the principal particulars."""
    derived = verify["derived"]
    assert math.isclose(derived["cb_ship"], 0.6505, rel_tol=1e-3)       # grad/(L B T)
    assert math.isclose(derived["S_m"], 9.4376, rel_tol=1e-4)           # S/lambda^2
    assert math.isclose(derived["vol_m"], 1.6489, rel_tol=1e-4)         # grad/lambda^3
    assert math.isclose(derived["L_m"] / derived["B_m"], 7.1429, rel_tol=1e-4)
    assert math.isclose(derived["B_m"] / derived["T_m"], 2.9815, rel_tol=1e-4)


def test_sealed_table_is_internally_consistent(verify):
    ch = {c["id"]: c for c in verify["checks"]}
    assert ch["P1"]["pass"] and ch["P1"]["recomputed"] < 0.5
    # R_TM = C_TM * 0.5 * rho * S * V^2 at the design point, recomputed here independently
    q = 0.5 * 998.2 * 9.4376 * 2.1966 ** 2
    assert math.isclose(0.00391 * q, 88.8, rel_tol=0.01)


def test_speed_matrix_covers_design_point_and_limits(verify):
    s = verify["summary"]
    assert s["n_points"] == 13 and s["has_design_point_0p26"] is True
    assert s["matrix_monotone_Vm_13pt"] is True
    assert s["Re_min_gt_5e6"] is True and s["V_m_max_lt_12_ms"] is True


def test_conversion_form_spread_is_the_documented_finding(verify):
    """R-02: the sealed anchor is reproducible only under the unit-form-factor form."""
    forms = verify["derived"]["anchor_forms_design_point"]
    plain = forms["A_plain_3D (as stated in report 2: C_TM = C_TS - C_FS + C_FM)"]["R_TM_N"]
    with_k = forms["B_with_(1+k)"]["R_TM_N"]
    with_k_dcf = forms["C_with_(1+k)_and_dCF"]["R_TM_N"]
    assert abs(plain - 88.8) / 88.8 < 0.005      # matches the sealed 88.8 N
    assert abs(with_k - 88.8) / 88.8 > 0.03      # but the declared (1+k) moves it >3%
    assert abs(with_k_dcf - 88.8) / 88.8 > 0.03  # and (1+k)+dC_F moves it the other way
    assert with_k_dcf < 88.8 < with_k


def test_only_the_declared_convention_fails_the_live_probe(verify):
    ch = {c["id"]: c for c in verify["checks"]}
    assert ch["X1"]["pass"] is True               # 4536 kN reproducible without (1+k)/dC_F
    assert ch["X2"]["pass"] is False              # with the declared settings it is not
    assert ch["X2"]["recomputed"] > 1.3 * 4536.0


def test_live_platform_probe_is_recorded_and_differs(probe):
    d = probe["derived"]
    assert d["ship_R_T_kN_as_declared"] is not None
    assert abs(d["dev_live_ship_vs_library_pct"]) < 50      # nowhere near the quoted +145% / +300%
    assert abs(d["report_dev_ship_vs_library_pct"]) > 100
    assert d["ship_R_T_kN_as_declared"] != d["report_ship_platform_kN"]
    # the model-scale probe reproduces neither 171.6 N nor the anchor
    assert abs(d["dev_live_model_vs_report_model_pct"]) > 5


# ---------------------------------------------------------------- 4. envelope
def _envelope(review):
    return {
        "package_id": "wp-459-04",
        "task_type": "04-independent-review",
        "report_id": "459",
        "provenance": {
            "source_hash": CONTRACT_HASH,
            "source_field": "markdown",
            "producer": "m15796/agent-m15796 (red-team reviewer)",
        },
        "outputs": {"review_report.json": review},
    }


def test_envelope_validates_against_kf_result_schema(review):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(_envelope(review), schema)


def test_review_report_is_json_serialisable_and_complete(review):
    assert json.loads(json.dumps(review)) == review
    for key in ("verdict", "checks", "findings", "claims_assessed", "checks_not_run",
                "overstated_claims", "independence_limitations", "acceptance_self_check"):
        assert key in review, key
    assert review["verdict"] in {"pass", "needs-fix", "fail"}
    assert review["checks_not_run"], "an independent review must declare what it did not run"


# ---------------------------------------------------------------- 5. evidence discipline
def test_no_claim_is_marked_verified(review):
    blob = json.dumps(review, ensure_ascii=False)
    for token in ('"verified"', "verification_status", "is_verified", "gate_confirmed"):
        assert token not in blob, token
    statuses = {c["status"] for c in review["claims_assessed"]}
    assert statuses <= {"supported", "partially-supported", "unresolved", "refuted"}
    assert "verified" not in statuses


def test_unresolved_claims_carry_a_reason(review):
    for claim in review["claims_assessed"]:
        if claim["status"] in {"unresolved", "partially-supported"}:
            assert claim.get("unresolved_reason"), claim["claim_id"]


def test_findings_are_severity_ranked_and_actionable(review):
    sev = [f["severity"] for f in review["findings"]]
    order = {"high": 0, "medium": 1, "low": 2}
    assert sev == sorted(sev, key=lambda s: order[s]), sev
    for f in review["findings"]:
        assert f["required_action"] and f["counter_evidence"]
        assert all(e["quote"] for c in f["claims_under_review"] for e in c["evidence"])


# ---------------------------------------------------------------- 6. scope
def test_scope_is_report_459_only(review, probe):
    blob = json.dumps(review, ensure_ascii=False) + json.dumps(probe, ensure_ascii=False)
    import re
    ids = set(re.findall(r"report_id[\"']?\s*[:=]\s*[\"']?(\d+)", blob))
    assert ids <= {"459"}, ids