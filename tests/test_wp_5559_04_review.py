"""wp-5559-04 · acceptance tests for the independent review of wp-5559-01.

These assert the review's own invariants (not the upstream's): the envelope is
schema-valid, the source hash is the one the contract names, every quoted piece of
evidence really is a verbatim substring of the report markdown, the verdict is
consistent with the findings, and no claim is marked verified.

Run: python3 -m pytest tests/test_wp_5559_04_review.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

W = Path("work/wp-5559-04")
CONTRACT_HASH = "sha256:3b04e96a056a9d8ba1b7861452dd5c2b3ce74777654154c7cc91e41f4e0b74ed"


@pytest.fixture(scope="module")
def source_text() -> str:
    return (W / "source_5559.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads((W / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review(result) -> dict:
    return result["outputs"]["review_report.json"]


def test_source_hash_matches_contract() -> None:
    raw = (W / "source_5559.md").read_bytes()
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == CONTRACT_HASH


def test_envelope_provenance_hash_equals_contract(result) -> None:
    assert result["provenance"]["source_hash"] == CONTRACT_HASH
    assert result["provenance"]["source_field"] == "markdown"
    assert result["report_id"] == "5559"
    assert result["package_id"] == "wp-5559-04"
    assert result["task_type"] == "04-independent-review"


def test_envelope_validates_against_schema(result) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(Path("schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(result)


def test_envelope_has_single_result_block_output(result) -> None:
    assert list(result["outputs"].keys()) == ["review_report.json"]
    assert isinstance(result["outputs"]["review_report.json"], dict)


def test_every_evidence_quote_is_verbatim(source_text, review) -> None:
    checked = 0
    for finding in review["findings"]:
        for e in finding["evidence"]:
            if e.get("origin") != "report_markdown":
                continue
            assert e["quote"] in source_text, f"{finding['id']}: not verbatim -> {e['quote'][:50]!r}"
            assert e["verbatim_in_source"] is True
            checked += 1
    assert checked >= 10, checked


def test_no_verified_marks(review) -> None:
    blob = json.dumps(review, ensure_ascii=False)
    assert '"verified": true' not in blob
    assert review["verification_marks_emitted"] is False
    assert all(f.get("verified") is not True for f in review["findings"])


def test_verdict_consistent_with_findings(review) -> None:
    assert review["verdict"] in {"pass", "needs-fix", "fail"}
    blocking = [f["id"] for f in review["findings"] if f["blocking"]]
    if blocking:
        assert review["verdict"] != "pass"
    else:
        assert review["blocking_findings"] == []
    assert review["disposition"] == "approve-with-notes"


def test_review_covers_the_upstream_artifact_set(review) -> None:
    # the review must adjudicate the upstream's own assertions, not just restate them
    assert len(review["upstream_observations_adjudicated"]) == 6
    assert len(review["upstream_checks_adjudicated"]) == 8
    assert all(c["reviewer_confirms"] for c in review["upstream_checks_adjudicated"])
    assert review["reviewed_package"] == "wp-5559-01"


def test_locator_replay_is_complete() -> None:
    checks = json.loads((W / "review_checks.json").read_text(encoding="utf-8"))
    lc = next(c for c in checks["checks"] if c["check"] == "locators_resolved_independently")
    assert lc["locators_total"] == 48
    assert lc["markdown_locators"] == 39 and lc["record_locators"] == 9
    for k in ("all_quotes_verbatim", "all_shas_match", "all_occurrences_match",
              "all_char_slices_match", "all_record_pointers_match"):
        assert lc[k] is True, k


def test_findings_are_bound_to_recomputed_numbers() -> None:
    math = json.loads((W / "report_side_math.json").read_text(encoding="utf-8"))
    g3 = math["g3_applicability"]
    # F-01: two REAL states carry a null in-domain fraction
    assert set(g3["states_with_null_fraction_but_REAL_evidence"]) == {"level_ice", "broken_ice"}
    assert g3["pass_flag"] is True
    # F-02: exactly one §3.2 row cannot be reproduced from its own displayed numbers
    assert len(math["inconsistencies"]) == 1
    assert math["inconsistencies"][0]["quantity"] == "浮冰谱斜率（抽样端）"
    # the reviewer's independent physics re-derivations reproduce the declared values
    by = {d["name"]: d for d in math["derivations"]}
    assert by["keel_porosity_implied"]["agrees"] is True
    assert by["isostatic_k_max"]["agrees"] is True
    assert by["frazil_phi_L_from_nu_peak"]["agrees"] is True


def test_probe_replay_covers_every_declared_artifact() -> None:
    probes = json.loads((W / "endpoint_probes.json").read_text(encoding="utf-8"))
    assert probes["n"] == 9
    assert probes["http_404"] == probes["n"]
    paths = {p["path"] for p in probes["probes"]}
    for fig in ("fig1_level_ice", "fig2_broken_ice", "fig3_ridges", "fig4_frazil", "fig5_scene"):
        assert any(fig in p for p in paths), fig
    assert "/tensor/artifacts/field_synth_demo.json" in paths


def test_review_stays_inside_its_report_scope(result) -> None:
    assert result["report_id"] == "5559"
    blob = json.dumps(result, ensure_ascii=False)
    other_ids = set(re.findall(r"tensor://reports/(\d+)", blob))
    assert other_ids <= {"5559"}, other_ids