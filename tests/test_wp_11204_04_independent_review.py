"""wp-11204-04 · 04-independent-review self-check (offline, hermetic).

Locks the independent review of report 11204 (upstream package wp-11204-01) against the
artefacts in ``docs/kf/wp-11204-04/``:

  * the kf_result envelope validates against ``schemas/kf_result.v1.schema.json`` and the
    embedded review object is byte-identical to the standalone ``review_report.json``;
  * ``provenance.source_hash`` is recomputed from the frozen source copy, equals the
    work-package contract hash, and equals the hash pinned by upstream wp-11204-01
    (the review is about the same bytes the producer registered);
  * every finding anchor is a >=12-char verbatim substring sitting on its declared line;
  * findings are typed and a non-info finding must rest on a red check; an
    ``approve_with_notes`` verdict carries no blocking finding;
  * the review never sets a verification field (it may discuss verification);
  * re-running ``review_checks.py`` reproduces the recorded pass/fail map, so the review is
    a recomputation rather than prose.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-11204-04"
SOURCE = PKG / "source" / "report_11204.md"
UPSTREAM = PKG / "source" / "upstream_wp-11204-01.kf_result.json"
CHECKS = PKG / "checks" / "independent_checks.json"
REVIEW = PKG / "review_report.json"
KF = PKG / "kf_result.json"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
CONTRACT_HASH = "sha256:d22a30cc692b82f2acf6ea669fd898a330143436344e4091c4a39c06a5292f86"
MIN_QUOTE = 12
FORBIDDEN_KEYS = {"verified", "verification_status", "verification_level", "is_verified",
                  "gate_confirmed"}


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


@pytest.fixture(scope="module")
def md() -> str:
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def review() -> dict:
    return json.loads(REVIEW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf() -> dict:
    return json.loads(KF.read_text(encoding="utf-8"))


def test_envelope_valid_json_and_schema(kf, review):
    jsonschema.validate(instance=kf, schema=json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert kf["package_id"] == "wp-11204-04"
    assert kf["task_type"] == "04-independent-review"
    assert kf["contract_version"] == "1.0"
    assert kf["report_id"] == "11204"
    assert list(kf["outputs"]) == ["review_report.json"]
    assert kf["outputs"]["review_report.json"] == review
    assert set(kf) == {"package_id", "task_type", "contract_version", "report_id",
                       "provenance", "outputs"}


def test_source_hash_recomputed_and_matches_upstream(md, kf, review):
    h = sha256_bytes(SOURCE.read_bytes())
    assert h == CONTRACT_HASH == kf["provenance"]["source_hash"]
    assert h == review["evidence_summary"]["source_hash_recomputed"]
    assert kf["provenance"]["source_hash_matches"] is True
    up = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    assert up["package_id"] == "wp-11204-01"
    assert up["provenance"]["source_hash"] == h, "review must be about the same bytes"
    assert review["reviewed_package"]["upstream_pinned_hash_matches"] is True
    assert review["reviewed_package"]["upstream_packages_completed"] is True
    # the frozen copy is the contested 5999-char markdown, not a trimmed variant
    assert len(md) == 5999 == kf["provenance"]["chars"]


def test_every_anchor_is_verbatim_on_its_line(md, review):
    lines = md.split("\n")
    for f in review["findings"]:
        a = f.get("anchor")
        if a is None:
            assert f.get("no_report_anchor_reason")
            assert f["anchor_line"] is None
            continue
        assert len(a) >= MIN_QUOTE, f["finding_id"]
        assert a in md, f["finding_id"]
        ln = f["anchor_line"]
        assert 1 <= ln <= len(lines)
        assert a in lines[ln - 1], f["finding_id"]


def test_findings_typed_and_verdict_consistent(review):
    seen = set()
    for f in review["findings"]:
        for key in ("finding_id", "severity", "blocking", "category", "title", "detail",
                    "impact", "recommended_fix", "evidence_check_ids"):
            assert key in f, (f.get("finding_id"), key)
        assert f["severity"] in {"info", "low", "medium", "high", "critical"}
        assert isinstance(f["blocking"], bool)
        assert f["evidence_check_ids"]
        assert f["finding_id"] not in seen
        seen.add(f["finding_id"])
    counts = review["finding_counts"]
    assert counts["blocking"] == sum(1 for f in review["findings"] if f["blocking"])
    assert counts["non_blocking"] == len(review["findings"]) - counts["blocking"]
    if review["decision"]["verdict"].startswith(("pass", "approve")):
        assert counts["blocking"] == 0
    known = {c["check_id"] for c in review["checks"]}
    failing = {c["check_id"] for c in review["checks"] if c["status"] == "finding"}
    for f in review["findings"]:
        assert set(f["evidence_check_ids"]) <= known, f["finding_id"]
        if f["severity"] != "info":  # a defect claim must rest on a red check
            assert set(f["evidence_check_ids"]) & failing, f["finding_id"]


def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v)


def test_no_verification_fields_anywhere(review, kf):
    """Field names, not prose: the review may *discuss* verification, it may not *set* it."""
    keys = set(_walk_keys([review, kf]))
    assert not (keys & FORBIDDEN_KEYS), sorted(keys & FORBIDDEN_KEYS)
    assert any("平台" in s for s in review["decision"]["not_asserted"])
    assert review["acceptance_selfcheck"]["do_not_mark_claims_as_verified"] is True


def test_reviewer_is_not_the_producer(review):
    rev = review["reviewer"]
    assert rev["independence"]["independent"] is True
    assert rev["independence"]["reviewer_is_producer"] is False
    assert rev["identity"] == "agent/m19783"
    assert rev["producer_identity"] == "agent/m15693"
    assert "m19783" not in rev["producer_identity"]
    assert rev["independence"]["review_prompt_copied_from_producer"] is False
    assert rev["independence"]["context_excludes_producer_explanation"] is True


def test_reviewed_artefact_hashes_match_bytes(review):
    for name, declared in review["reviewed_package"]["artifacts_used"].items():
        assert sha256_bytes((PKG / name).read_bytes()) == declared, name


def test_recorded_check_map_matches_rerun():
    """The review must be reproducible: re-run the checks and compare the pass map."""
    before = json.loads(CHECKS.read_text(encoding="utf-8"))
    res = subprocess.run([sys.executable, str(PKG / "review_checks.py")],
                         capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0, res.stdout + res.stderr
    fresh = json.loads(CHECKS.read_text(encoding="utf-8"))
    recorded = json.loads(REVIEW.read_text(encoding="utf-8"))
    fresh_map = {k: v["pass"] for k, v in fresh["checks"].items()}
    rec_map = {c["check_id"]: (c["status"] == "pass") for c in recorded["checks"]}
    assert fresh_map == rec_map
    assert fresh["checks"].keys() == before["checks"].keys()
    # the fidelity-critical invariants
    assert fresh_map["C1_source_hash"] and fresh_map["C2_upstream_pinned"]
    assert fresh_map["C3_anchors_verbatim"] and fresh_map["C4_table_arithmetic"]
    assert fresh_map["C5_bk_law"] and fresh_map["C11_no_self_verification"]
    assert recorded["evidence_summary"]["n_fabricated_or_misplaced_quotes"] == 0


def test_f1_is_reproducible_from_first_principles():
    """The one substantive finding must not rot: rebuild the implied load level from the
    report's own elastic-J value and the ASTM E399 CT geometry factor."""
    sys.path.insert(0, str(PKG))
    import review_checks as rc  # noqa: E402

    p = rc.implied_load(1957.7, "CT")
    assert 11_900 < p < 12_100, p
    j_peak = rc.lefm_J(rc.ct_K(34725.0), 200e9, 0.3)
    assert j_peak > 1.6e4, j_peak          # ~1.638e4 J/m2 at P_Q, 8.4x the reported value
    assert abs(rc.ct_f(0.5) - 9.659) < 0.01
    seb = rc.implied_load(132.11, "SEB")
    assert 1_950 < seb < 2_050, seb
    # the mixed-mode analytic column the report publishes is the extended BK law
    assert abs(rc.bk_Gc(45.0) - 341.42) < 0.05
    assert abs(rc.bk_Gc(0.0) - 200.0) < 1e-9


def test_repro_commands_are_present(review):
    cmd = review["repro_cmd"]
    for script in ("review_checks.py", "build_review_report.py"):
        assert script in cmd
    assert "pytest tests/test_wp_11204_04_independent_review.py" in cmd