"""Invariant tests for work package wp-448-01 (asset registration of report 448).

Each acceptance criterion is asserted on the real artifact, and every locator/hash/duplicate check is
additionally given a negative control (tampered copy) so the test proves the check can fail rather
than merely executing code.

Run: pytest -q tests/test_kf_wp448.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kf_verify_448 as kv  # noqa: E402

MANIFEST_PATH = ROOT / "artifacts/wp-448-01/asset_manifest.json"
SCHEMA_PATH = ROOT / "schemas/asset_manifest.v1.schema.json"
RESULT_PATH = ROOT / "runs/wp-448-01/kf_result.wp-448-01.json"
MD_PATH = ROOT / "runs/wp-448-01/report_448.md"
CONTRACT_HASH = "a3e7910fbcbe3624805a875ebd9a033c54036a1950cdc2885a6fc739dbcabea8"


@pytest.fixture(scope="module")
def md() -> str:
    return MD_PATH.read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def test_source_hash_matches_contract_and_local_copy(md, manifest):
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == len(md) == 3233


def test_manifest_validates_against_local_schema(manifest):
    jsonschema.validate(manifest, json.loads(SCHEMA_PATH.read_text()))


def test_every_locator_reresolves_uniquely(md, manifest):
    assert kv.check_locators(md, manifest) == []


def test_locator_check_detects_tampered_quote(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = tampered["assets"][2]
    a["locator"]["quote"] = a["locator"]["quote"].replace("142.000", "142.001")
    assert any(asset == a["asset_id"] for asset, _ in kv.check_locators(md, tampered))


def test_locator_check_detects_shifted_span(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = tampered["assets"][4]
    a["locator"]["start_char"] += 1
    assert any(asset == a["asset_id"] and why == "slice_mismatch"
               for asset, why in kv.check_locators(md, tampered))


def test_locator_check_detects_invented_resolution(manifest, md):
    tampered = copy.deepcopy(manifest)
    for a in tampered["assets"]:
        if a["asset_id"] == "A20":  # external git commit, genuinely unresolved
            a["resolution"] = "resolved_in_source"
    assert any(asset == "A20" for asset, _ in kv.check_locators(md, tampered))


def test_no_duplicate_ids_and_duplicate_detector_works(manifest):
    assert kv.check_duplicate_ids(manifest) == []
    tampered = copy.deepcopy(manifest)
    tampered["assets"][1]["asset_id"] = tampered["assets"][0]["asset_id"]
    assert kv.check_duplicate_ids(tampered)


def test_claims_empty_and_claim_checker_works(manifest):
    assert manifest["claims"] == []
    assert kv.check_claims(manifest["claims"]) == []
    assert kv.check_claims([{"claim_id": "C1", "text": "unbacked"}]) == ["C1"]
    assert kv.check_claims([{"claim_id": "C2", "text": "x", "status": "unresolved"}]) == []


def test_resolution_statuses_are_honest(manifest):
    by_id = {a["asset_id"]: a for a in manifest["assets"]}
    # external artifacts of another repository cannot be claimed resolved from this worktree
    assert by_id["A19"]["resolution"] == "referenced_unresolved"
    assert by_id["A19"]["resolution_check"]["missing"]  # concrete missing-file list
    assert by_id["A20"]["resolution"] == "referenced_unresolved"
    assert by_id["A17"]["resolution_check"]["addresses_found"] == []
    assert by_id["A14"]["resolution"] == "declared_absent"
    assert by_id["A14"]["resolution_check"]["platform_figures_count"] == 0


def test_result_envelope_and_artifact_hash(manifest):
    result = json.loads(RESULT_PATH.read_text())
    assert {"package_id", "task_type", "report_id", "provenance", "outputs"} <= set(result)
    assert result["package_id"] == "wp-448-01"
    assert result["task_type"] == "01-asset-registration"
    assert str(result["report_id"]) == "448"
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    art = result["outputs"]["asset_manifest.json"]
    assert art["artifact_sha256"] == hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    assert art["assets"] == manifest["assets"]


def test_durable_commit_mirror_identical():
    """artifacts/ and runs/ are dropped by this repo's push gate, so docs/ holds byte-identical copies."""
    import hashlib
    for name in ("asset_manifest.json", "verification.json"):
        a = ROOT / "artifacts/wp-448-01" / name
        d = ROOT / "docs/wp-448-01" / name
        assert d.exists(), d
        assert hashlib.sha256(a.read_bytes()).hexdigest() == hashlib.sha256(d.read_bytes()).hexdigest(), name
    for png in ("fig_asset_inventory.png", "fig_locator_coverage.png", "fig_verification.png"):
        assert (ROOT / "docs/wp-448-01" / png).exists(), png


def test_no_report_id_contamination(manifest):
    """Boundary: this package only touches report 448."""
    assert str(manifest["report_id"]) == "448"
    assert manifest["source"]["uri"] == "tensor://reports/448"
    blob = json.dumps(manifest, ensure_ascii=False)
    assert "tensor://reports/449" not in blob and "tensor://reports/447" not in blob