"""Offline self-checks for the wp-5949-04 independent-review deliverables.

These tests never touch the network: they re-derive the review from the frozen source copy
in this worktree and assert that the shipped artifacts still agree with it.  The point is
not "the files exist" -- it is that no number in the delivered review was hand-copied, that
no red check was left unclaimed, and that the build is reproducible byte for byte.

Run: python3 -m pytest tests/test_kf_wp5949_review.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-5949-04"
WORK = REPO / "work" / "wp-5949-04"
SOURCE = PKG / "source_5949.md"
REVIEW = PKG / "review_report.json"
KF_RESULT = PKG / "kf_result.json"
MARKDOWN = PKG / "KF-RESULT-wp-5949-04.md"
FIGURE = PKG / "figures" / "wp-5949-04_checks.png"
CHECKS = WORK / "checks.json"
UPSTREAM = REPO / "docs" / "kf" / "wp-5949-01"

CONTRACT_HASH = "c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002"
CONTRACT_CHARS = 12605
CONTRACT_BYTES = 17867

sys.dont_write_bytecode = True
sys.path.insert(0, str(WORK))
import review_checks as rc  # noqa: E402


@pytest.fixture(scope="module")
def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def checks() -> dict:
    return json.loads(CHECKS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review() -> dict:
    return json.loads(REVIEW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf() -> dict:
    return json.loads(KF_RESULT.read_text(encoding="utf-8"))


def test_deliverables_exist():
    for p in (SOURCE, REVIEW, KF_RESULT, MARKDOWN, FIGURE, CHECKS,
              WORK / "review_checks.py", WORK / "build_review.py"):
        assert p.is_file(), p
    assert FIGURE.stat().st_size > 20_000, "figure looks empty"


def test_source_copy_is_the_contract_bytes(source):
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(source) == CONTRACT_CHARS
    assert len(source.encode("utf-8")) == CONTRACT_BYTES
    # the frozen copy must be identical to the upstream 01 registration copy
    up = (UPSTREAM / "source_5949.md").read_text(encoding="utf-8")
    assert up == source
    manifest = json.loads((UPSTREAM / "asset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == CONTRACT_CHARS


def test_checks_are_not_stale(checks):
    """Re-running the checker must reproduce checks.json byte for byte."""
    assert rc.run_checks() == checks
    on_disk = json.loads(CHECKS.read_text(encoding="utf-8"))
    assert json.dumps(rc.run_checks(), ensure_ascii=False, indent=1) + "\n" == \
        CHECKS.read_text(encoding="utf-8")
    assert on_disk["checks_summary"]["n_checks"] == len(on_disk["checks"])


def test_every_anchor_is_a_verbatim_substring_at_the_declared_line(checks, source):
    lines = source.splitlines()
    for c in checks["checks"]:
        assert c["anchor"] in source, c["check_id"]
        assert lines[c["anchor_line"] - 1].strip(), c["check_id"]
        # the anchor must actually sit on the declared line
        assert c["anchor"] in lines[c["anchor_line"] - 1], c["check_id"]


def test_declared_values_are_parsed_from_the_source_not_typed(checks, source):
    """A hand-copied 'declared' value would drift; a parsed one cannot."""
    blind = rc.parse_blind(source)
    c5 = {c["check_id"]: c for c in checks["checks"]}["C5_hit_recount"]
    assert c5["declared"]["declared_hits"] == sum(
        1 for r in blind if r["declared_verdict"] == "命中")
    c3 = {c["check_id"]: c for c in checks["checks"]}["C3_seat_arithmetic"]
    assert c3["declared"]["seats"] == int(re.search(r"席位数（族×框架×角色）\s*\|\s*\*\*(\d+)\*\*",
                                                    source).group(1))
    c13 = {c["check_id"]: c for c in checks["checks"]}["C13_population_table"]
    assert c13["declared"]["shares"] == {f: s for f, _, s in rc.parse_population(source)}


def test_recomputed_numbers_are_really_recomputed(checks, source):
    """Spot-check two red findings against an independent re-derivation in this test."""
    blind = rc.parse_blind(source)
    hits = sum(1 for r in blind if r["lo"] <= r["value"] <= r["hi"])
    byid = {c["check_id"]: c for c in checks["checks"]}
    assert byid["C5_hit_recount"]["recomputed"]["recomputed_hits"] == hits
    assert byid["C6_hit_rate"]["recomputed"]["hit_rate"] == pytest.approx(hits / len(blind))
    # the flip row is the only disagreement between printed verdict and containment
    flips = [(r["seat"], r["declared_verdict"]) for r in blind
             if (r["declared_verdict"] == "命中") != (r["lo"] <= r["value"] <= r["hi"])]
    assert len(flips) == 1
    assert byid["C5_hit_recount"]["recomputed"]["flipped_rows"][0]["seat"] == flips[0][0]
    # null-model arithmetic is exact binomial, not a normal approximation
    c8 = byid["C8_null_model_sensitivity"]["recomputed"]
    nb = c8["null_B_uniform_in_observed_band"]
    assert nb["p_value_ge_observed"] == pytest.approx(
        rc.binom_sf(hits, len(blind), nb["p0"]), rel=1e-4)
    # the band null is *more* permissive than U(0,1) here: the printed intervals almost span
    # the observed value band, so p0 rises from 0.1575 to ~0.20
    assert nb["p0"] > c8["null_A_uniform_0_1"]["p0"]
    # and both nulls leave the observed count inside chance -- the report's quantitative
    # clause holds; only the "no leakage" inference fails
    assert c8["null_A_uniform_0_1"]["p_value_ge_observed"] > 0.05
    assert nb["p_value_ge_observed"] > 0.05
    assert c8["first_clause_holds_under_both_nulls"] is True


def test_review_envelope_binds_to_the_contract(review):
    assert review["package_id"] == "wp-5949-04"
    assert review["task_type"] == "04-independent-review"
    assert review["review_type"] == "04-independent-review"
    assert review["report_id"] == "5949"
    assert review["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert review["provenance"]["source_hash_matches"] is True
    assert review["provenance"]["chars"] == CONTRACT_CHARS
    assert review["provenance"]["bytes_utf8"] == CONTRACT_BYTES
    assert review["provenance"]["frozen_copy"] == "docs/kf/wp-5949-04/source_5949.md"
    ind = review["reviewer"]["independence"]
    assert ind["independent"] is True and ind["reviewer_is_producer"] is False
    assert ind["context_excludes_producer_explanation"] is True
    assert ind["review_prompt_copied_from_producer"] is False


def test_every_red_or_withheld_check_is_claimed_by_a_finding(review):
    byid = {c["check_id"] for c in review["checks"]}
    claimed = {cid for f in review["findings"] for cid in f["evidence_check_ids"]}
    must = set(review["checks_summary"]["failed"]) | set(review["checks_summary"]["unverifiable"])
    assert must <= claimed, sorted(must - claimed)
    assert claimed <= byid, sorted(claimed - byid)
    for f in review["findings"]:
        assert f["severity"] in {"critical", "high", "medium", "low", "info"}
        assert isinstance(f["blocking"], bool)
        assert f["anchor"] and f["recommended_fix"]
        assert f["anchor_line"] >= 1
    # the pass/fail counts are internally consistent
    statuses = [c["status"] for c in review["checks"]]
    s = review["checks_summary"]
    assert s["n_checks"] == len(statuses)
    assert s["n_pass"] == statuses.count("pass")
    assert s["n_fail"] == statuses.count("fail")
    assert s["n_unverifiable"] == statuses.count("unverifiable")


def test_review_checks_mirror_checks_json_without_drift(review, checks):
    shipped = {c["check_id"]: c for c in review["checks"]}
    source = {c["check_id"]: c for c in checks["checks"]}
    assert set(shipped) == set(source)
    for cid, c in source.items():
        assert shipped[cid]["status"] == c["status"]
        assert shipped[cid]["declared"] == c["declared"]
        assert shipped[cid]["recomputed"] == c["recomputed"]
        assert shipped[cid]["anchor_line"] == c["anchor_line"]


def test_no_verification_or_self_certification_is_written(review):
    blob = json.dumps(review, ensure_ascii=False)
    assert '"verification"' not in blob
    assert '"verified": true' not in blob
    assert review["acceptance_selfcheck"]["no_verification_field_written"] is True
    for c in review["checks"]:
        assert c["status"] in {"pass", "fail", "unverifiable"}


def test_honest_failures_are_kept_as_failures(review):
    """The two >3% items must not have been quietly promoted to pass."""
    byid = {c["check_id"]: c for c in review["checks"]}
    assert byid["C5_hit_recount"]["status"] == "fail"
    assert byid["C6_hit_rate"]["status"] == "fail"
    # C8 passes on its numbers but still carries a finding: the inference, not the arithmetic
    assert byid["C8_null_model_sensitivity"]["status"] == "pass"
    assert byid["C8_null_model_sensitivity"]["recomputed"]["second_clause_is_a_non_sequitur"] is True
    assert review["decision"]["blocking_findings"] == 0
    assert review["decision"]["verdict"] == "approve_with_notes"
    severities = {f["severity"] for f in review["findings"]}
    assert "medium" in severities


def test_kf_result_digests_recompute(kf):
    assert kf["package_id"] == "wp-5949-04"
    assert kf["task_type"] == "04-independent-review"
    assert kf["report_id"] == "5949"
    assert kf["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert kf["provenance"]["source_hash_matches"] is True
    assert kf["outputs"], "no outputs declared"
    for label, out in kf["outputs"].items():
        path = REPO / out["path"]
        assert path.is_file(), (label, out["path"])
        raw = path.read_bytes()
        assert out["bytes"] == len(raw), label
        assert out["sha256"] == hashlib.sha256(raw).hexdigest(), label
    assert kf["decision"]["verdict"] == "approve_with_notes"
    assert kf["decision"]["checks"]["n_fail"] >= 1


def test_markdown_reports_all_six_sections_and_injects_numbers(checks):
    md = MARKDOWN.read_text(encoding="utf-8")
    for head in ("① 案例介绍", "② 怎么做的", "③ 计算结果", "④ 图", "⑤ 注意点", "⑥ 误差判定"):
        assert head in md, head
    byid = {c["check_id"]: c for c in checks["checks"]}
    hits = byid["C5_hit_recount"]["recomputed"]["recomputed_hits"]
    rate = byid["C6_hit_rate"]["recomputed"]["hit_rate"]
    # numbers are injected from checks.json, so these strings must appear verbatim
    assert f"| 盲预测命中数 | {byid['C5_hit_recount']['declared']['declared_hits']} | {hits} |" in md
    assert f"| hit_rate | {byid['C6_hit_rate']['declared']['hit_rate']} | {rate} |" in md
    assert "是否 <3%" in md or "<3%？" in md
    assert "不适用" in md  # the physics criterion is declared not applicable, with a reason
    assert "figures/wp-5949-04_checks.png" in md
    assert "复算" in md
    assert "build_review.py" in md


def test_build_is_reproducible():
    """Rebuilding must not change a single byte of the shipped artifacts."""
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (REVIEW, MARKDOWN, KF_RESULT, CHECKS, FIGURE)}
    subprocess.run([sys.executable, str(WORK / "build_review.py")],
                   cwd=REPO, check=True, capture_output=True)
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
    assert before == after


def test_no_bytecode_is_shipped():
    for root in (PKG, WORK):
        assert not list(root.rglob("*.pyc")), root
        assert not list(root.rglob("__pycache__")), root