"""wp-766-04 · 04-independent-review self-check (offline, hermetic).

Locks the review of wp-766-01 against the committed artefacts in ``runs/wp-766-04/``:

  * the review envelope validates against ``schemas/kf_result.v1.schema.json``;
  * ``provenance.source_hash`` is recomputed from the stored source markdown and equals
    the upstream package's pinned hash (the review is about the same bytes);
  * every finding anchor is a >=12-char verbatim substring on its declared line;
  * findings are typed (severity/blocking), and a ``pass`` verdict carries no blocking
    finding (no verdict inflation in the safe direction either: blocking flag is explicit);
  * the review never writes a verification field (``verified``/``verification_level``…);
  * the reviewed artefact hashes recorded in the review match the bytes of the reviewed
    copy, and the reviewer identity differs from the producer identity;
  * re-running ``review_checks.py`` reproduces the same pass/fail map (the review is a
    recomputation, not prose).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "runs" / "wp-766-04"
SOURCE = PKG / "source" / "report_766.md"
REVIEW = PKG / "review_report.json"
KF = PKG / "kf_result.json"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
UPSTREAM = PKG / "reviewed_wp766_01"
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


def test_envelope_valid_json_and_schema(kf):
    jsonschema.validate(instance=kf, schema=json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert kf["package_id"] == "wp-766-04"
    assert kf["task_type"] == "04-independent-review"
    assert kf["report_id"] == "766"
    assert list(kf["outputs"]) == ["review_report.json"]
    # the envelope embeds the same object as the standalone deliverable
    assert kf["outputs"]["review_report.json"] == json.loads(REVIEW.read_text(encoding="utf-8"))
    # a review package registers no knowledge claims of its own
    assert kf["claims"] == []


def test_source_hash_is_recomputed_not_copied(md, kf, review):
    h = sha256_bytes(md.encode("utf-8"))
    assert kf["provenance"]["source_hash"] == h
    assert review["evidence_summary"]["source_hash_recomputed"] == h
    up = json.loads((UPSTREAM / "kf_result.json").read_text(encoding="utf-8"))
    assert up["provenance"]["source_hash"] == h, "review must be about the same bytes"
    assert h == "sha256:6b45972f5b6e61c7c832dd5aec54236b254dd20b56556190ecb0d86ac5b36407"


def test_every_anchor_is_verbatim_on_its_line(md, review):
    lines = md.split("\n")
    for f in review["findings"]:
        a = f.get("anchor")
        if a is None:
            assert f.get("no_report_anchor_reason")
            continue
        assert len(a) >= MIN_QUOTE, f["finding_id"]
        assert a in md, f["finding_id"]
        ln = f["anchor_line"]
        assert 1 <= ln <= len(lines)
        assert a in lines[ln - 1], f["finding_id"]


def test_findings_typed_and_verdict_consistent(review):
    seen = set()
    for f in review["findings"]:
        for key in ("finding_id", "severity", "blocking", "title", "detail", "impact",
                    "recommended_fix", "evidence_check_ids"):
            assert key in f, (f.get("finding_id"), key)
        assert f["severity"] in {"info", "low", "medium", "high", "critical"}
        assert isinstance(f["blocking"], bool)
        assert f["evidence_check_ids"]
        assert f["finding_id"] not in seen
        seen.add(f["finding_id"])
    counts = review["finding_counts"]
    assert counts["blocking"] == sum(1 for f in review["findings"] if f["blocking"])
    assert counts["non_blocking"] == len(review["findings"]) - counts["blocking"]
    if review["decision"]["verdict"] == "pass":
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
    # the reviewer explicitly declines to assert verification level
    assert any("平台" in s for s in review["decision"]["not_asserted"])


def test_reviewer_is_not_the_producer(review):
    rev = review["reviewer"]
    assert rev["independence"]["independent"] is True
    assert "m15801" in rev["identity"]
    assert "m15517" in rev["producer_identity"]
    assert "m15801" not in rev["producer_identity"]


def test_reviewed_artefact_hashes_match_bytes(review):
    for name, declared in review["reviewed_package"]["artifacts_used"].items():
        assert sha256_bytes((UPSTREAM / name).read_bytes()) == declared, name


def test_recorded_check_map_matches_rerun(tmp_path):
    """The review must be reproducible: re-run the checks and compare the pass map."""
    res = subprocess.run([sys.executable, str(PKG / "review_checks.py")],
                         capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0, res.stdout + res.stderr
    fresh = json.loads((PKG / "checks" / "independent_checks.json").read_text(encoding="utf-8"))
    recorded = json.loads(REVIEW.read_text(encoding="utf-8"))
    fresh_map = {k: v.get("pass") for k, v in fresh["checks"].items() if "pass" in v}
    rec_map = {c["check_id"]: (c["status"] == "pass")
               for c in recorded["checks"] if c["status"] != "observation"}
    assert fresh_map == rec_map
    # the fidelity-critical invariants
    assert fresh_map["C2_source_hash"] and fresh_map["C3_quote_locator_verbatim"]
    assert fresh_map["C5_counts_consistent"] and fresh_map["C8_no_self_verification"]
    assert recorded["evidence_summary"]["n_fabricated_or_misplaced_quotes"] == 0


def test_tamper_probe_claim_is_reproducible(md, review):
    """The report claims the quote layer misses cell edits and the document hash catches
    them; recompute one probe so the claim cannot rot."""
    pinned = review["evidence_summary"]["source_hash_recomputed"]
    mut = md.replace("| 100 | D/40 | 1.3223 | 0.0007 |", "| 100 | D/40 | 9.9999 | 0.0007 |")
    assert mut != md
    assert sha256_bytes(mut.encode()) != pinned
    probes = json.loads((PKG / "checks" / "independent_checks.json").read_text(encoding="utf-8"))
    probes = probes["checks"]["C10_tamper_probes"]["probes"]
    assert probes["P1_results_table_cell_C_D_D40"]["caught_by_document_hash"] is True
    assert probes["P1_results_table_cell_C_D_D40"]["caught_by_quote_layer"] == []


def test_repro_commands_are_present(review):
    cmd = review["method"]["repro_cmd"]
    for script in ("fetch_source.py", "review_checks.py", "build_review_report.py"):
        assert script in cmd
    assert re.search(r"pytest tests/test_wp766_04_independent_review\.py", cmd)