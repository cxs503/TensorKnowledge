#!/usr/bin/env python3
"""Invariant tests for the RA publication (m23257).

These assert *rules*, not today's snapshot: the RA row must stay consistent with
the measured evidence bundle, and the mission's requested value
(scenario_validated=true) must be rejected by the canonical validator while the
recorded verdict is changes_requested. Run:

    python3 -m pytest docs/m23257/test_status_publication.py -q
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
EVIDENCE = json.loads((HERE / "status_evidence.json").read_text(encoding="utf-8"))
PROPOSED = json.loads((HERE / "products_STATUS.proposed.json").read_text(encoding="utf-8"))
TENSORBENCH = Path("/srv/tensor/workspace/TensorBench")
CANONICAL = TENSORBENCH / "products/STATUS.json"

if TENSORBENCH.is_dir():
    sys.path.insert(0, str(TENSORBENCH))
    from tensorbench import contracts  # type: ignore
else:  # pragma: no cover
    contracts = None

pytestmark = pytest.mark.skipif(contracts is None, reason="TensorBench validators absent")


def ra_row(payload: dict) -> dict:
    return [p for p in payload["products"] if p["id"] == "RA"][0]


def test_proposed_payload_passes_canonical_validation():
    assert contracts.validate_payload("status", PROPOSED) == []


def test_ra_row_matches_measured_evidence():
    ra = ra_row(PROPOSED)
    assert ra["code_implemented"] is True
    ev = ra["acceptance_evidence"]
    assert ev["verdict"] == EVIDENCE["six_checks_recorded"]["review_receipt_verdict"]
    assert ev["reviewed_commit"] == EVIDENCE["pr511_merge"]["stdout_tail"].splitlines()[0]
    assert EVIDENCE["pr511_merge"]["in_head"] is True
    assert EVIDENCE["fix_identity"]["matches_r5_reviewed_fix"] is True
    assert EVIDENCE["entry_point"]["cold_exit_code"] == 0


def test_cited_refs_exist_in_this_checkout():
    ra = ra_row(PROPOSED)
    for ref in (ra["acceptance_evidence"]["validation_report_ref"],
                ra["acceptance_evidence"]["review_receipt_ref"]):
        rel = ref.split(":", 1)[1]
        assert (REPO / rel).is_file(), rel


def test_scenario_validated_follows_locator_residual():
    """If locators do not resolve cold, the row may not claim scenario validation."""
    loc = EVIDENCE["r5_1_locators"]
    ra = ra_row(PROPOSED)
    cold_clean = loc["pure_path_resolved_cold"] == loc["pure_path_fields"]
    if not cold_clean:
        assert ra["scenario_validated"] is False
        assert "R5-1" in ra["next_gate"]
        assert any("R5-1" in s for s in ra["not_implemented_or_unverified"])
    else:  # a future repair must be reflected, not silently ignored
        assert ra["scenario_validated"] is (ra["acceptance_evidence"]["verdict"] == "pass")


def test_mission_requested_true_is_rejected_by_canonical_contract():
    """The brief asks for scenario_validated=true; the validator must refuse it."""
    mutated = json.loads(json.dumps(PROPOSED))
    ra_row(mutated)["scenario_validated"] = True
    errors = contracts.validate_payload("status", mutated)
    assert any("verdict=pass" in e for e in errors), errors


def test_control_pass_verdict_does_admit_true():
    """Guard against a validator that simply always fails."""
    control = json.loads(json.dumps(PROPOSED))
    ra = ra_row(control)
    ra["scenario_validated"] = True
    ra["acceptance_evidence"]["verdict"] = "pass"
    assert contracts.validate_payload("status", control) == []


def test_ledger_reading_is_declared_honestly():
    ledger = EVIDENCE["verdict_ledger"]
    assert isinstance(ledger["read_ok"], bool)
    if not ledger["read_ok"]:
        assert "WITHHELD" in ledger["evidence_level"]
        assert ledger["in_repo_quotations"], "unreadable ledger must fall back to file:line citations"


def test_apply_patch_on_copy(tmp_path: Path):
    if not CANONICAL.is_file():
        pytest.skip("canonical STATUS.json not reachable")
    copy = tmp_path / "STATUS.json"
    copy.write_bytes(CANONICAL.read_bytes())
    proc = subprocess.run([sys.executable, str(HERE / "apply_status_patch.py"),
                           "--path", str(copy), "--write"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = json.loads(copy.read_text(encoding="utf-8"))
    assert contracts.validate_payload("status", after) == []
    assert ra_row(after) == ra_row(PROPOSED)
    # canonical file orders lines AE, BE, RA, PV; the patch must not reorder them
    assert [p["id"] for p in after["products"]] == ["AE", "BE", "RA", "PV"]


def test_apply_refuses_drifted_target(tmp_path: Path):
    drifted = tmp_path / "STATUS.json"
    drifted.write_text(json.dumps({"schema_version": "2.0.0", "products": []}), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(HERE / "apply_status_patch.py"),
                           "--path", str(drifted), "--write"],
                          capture_output=True, text=True)
    assert proc.returncode == 3, proc.stdout
    assert json.loads(drifted.read_text(encoding="utf-8"))["products"] == []