"""Machine gates for work package wp-13980-01 (report 13980, task 01-asset-registration).

The tests execute the contract's acceptance block through scripts/kf_verify_13980.py and
additionally tamper with inputs to prove the checks are discriminating rather than
vacuous (a gate that cannot fail is not a gate).

Run: pytest tests/test_wp_13980_01.py -q
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import kf_verify_13980 as v  # noqa: E402

ART = pathlib.Path("artifacts/wp-13980-01")
MANIFEST = ART / "asset_manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def _md() -> str:
    return (ART / "source_markdown.md").read_text()


def test_acceptance_checks_all_pass():
    rep = v.run_checks()
    assert rep["checks"] == {
        "valid_json": True,
        "schema_pass": True,
        "source_hash_matches": True,
        "source_locator_resolvable": True,
        "no_duplicate_ids": True,
        "all_claims_have_evidence_or_explicit_unresolved_status": True,
        "not_marked_verified": True,
    }, rep["detail"]
    assert rep["all_pass"] is True


def test_contract_hash_and_chars_match_source():
    md = _md()
    assert v.hashlib.sha256(md.encode()).hexdigest() == v.CONTRACT_HASH
    assert len(md) == v.CONTRACT_CHARS
    assert _manifest()["source"]["hash"] == v.CONTRACT_HASH


def test_every_quote_is_verbatim_and_unique():
    md = _md()
    for a in _manifest()["assets"]:
        q = a["locator"]["quote"]
        assert q and md.count(q) == 1, a["asset_id"]
        if a["locator"]["method"] == "char_span":
            assert md[a["locator"]["start_char"]:a["locator"]["end_char"]] == q


def test_locator_check_detects_shifted_offsets():
    """Negative control: shifting a locator by one char must be caught."""
    md, m = _md(), _manifest()
    tampered = copy.deepcopy(m["assets"])
    tampered[1]["locator"]["start_char"] += 1
    assert v.locator_failures(md, tampered) == [tampered[1]["asset_id"]]


def test_locator_check_detects_edited_quote():
    """Negative control: a quote not present verbatim in the source must be caught."""
    md, m = _md(), _manifest()
    tampered = copy.deepcopy(m["assets"])
    tampered[3]["locator"]["quote"] = tampered[3]["locator"]["quote"] + "（手抄增补）"
    assert v.locator_failures(md, tampered) == [tampered[3]["asset_id"]]


def test_hash_gate_rejects_altered_markdown():
    md = _md()
    assert v.hashlib.sha256((md + " ").encode()).hexdigest() != v.CONTRACT_HASH


def test_claims_empty_is_legal_and_nothing_verified():
    m = _manifest()
    env = json.loads((pathlib.Path("runs/wp-13980-01") /
                      "kf_result.wp-13980-01.json").read_text())
    assert m["claims"] == [] and env["claims"] == []
    assert env["provenance"]["verification_status"] == "not_verified"
    assert env["provenance"]["source_hash"] == "sha256:" + v.CONTRACT_HASH
    assert env["package_id"] == "wp-13980-01" and env["report_id"] == "13980"


def test_resolution_statuses_are_declared_with_a_check():
    m = _manifest()
    for a in m["assets"]:
        assert a["resolution"] in ("resolved_in_source", "referenced_unresolved",
                                   "declared_absent")
        assert a["resolution_check"]["result"] in ("resolved", "unresolved", "absent", "present")
        assert a["note"].strip()


def test_durable_mirror_is_byte_identical():
    mirror = pathlib.Path("docs/kf/wp-13980-01/asset_manifest.json")
    assert mirror.read_bytes() == MANIFEST.read_bytes()