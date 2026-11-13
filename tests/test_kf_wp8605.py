"""Invariant tests for work package wp-8605-01 (asset registration of report 8605).

Each acceptance criterion is asserted on the real artifact, and every locator/hash/duplicate check is
additionally given a negative control (tampered copy) so the test proves the check can fail rather
than merely executing code.

Run: pytest -q tests/test_kf_wp8605.py
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

import kf_verify_8605 as kv  # noqa: E402

MANIFEST_PATH = ROOT / "artifacts/wp-8605-01/asset_manifest.json"
SCHEMA_PATH = ROOT / "schemas/asset_manifest.wp8605.v1.schema.json"
RESULT_PATH = ROOT / "runs/wp-8605-01/kf_result.wp-8605-01.json"
MD_PATH = ROOT / "runs/wp-8605-01/report_8605.md"
CONTRACT_HASH = "a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36"


@pytest.fixture(scope="module")
def md() -> str:
    return MD_PATH.read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def test_source_hash_matches_contract_and_local_copy(md, manifest):
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == len(md) == 8006


def test_manifest_validates_against_local_schema(manifest):
    jsonschema.validate(manifest, json.loads(SCHEMA_PATH.read_text()))


def test_every_locator_reresolves_uniquely(md, manifest):
    assert kv.check_locators(md, manifest) == []


def test_locator_check_detects_tampered_quote(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = tampered["assets"][3]  # A04 parameter table
    a["locator"]["quote"] = a["locator"]["quote"].replace("320000", "320001")
    assert any(asset == a["asset_id"] for asset, _ in kv.check_locators(md, tampered))


def test_locator_check_detects_shifted_span(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = tampered["assets"][5]  # A06 gate table
    a["locator"]["start_char"] += 1
    assert any(asset == a["asset_id"] and why == "slice_mismatch"
               for asset, why in kv.check_locators(md, tampered))


def test_locator_check_detects_invented_resolution(manifest, md):
    tampered = copy.deepcopy(manifest)
    for a in tampered["assets"]:
        if a["asset_id"] == "A07":  # external anchor, genuinely unresolved
            a["resolution"] = "resolved_in_source"
    assert any(asset == "A07" for asset, _ in kv.check_locators(md, tampered))


def test_no_duplicate_ids_and_duplicate_detector_works(manifest):
    assert kv.check_duplicate_ids(manifest) == []
    tampered = copy.deepcopy(manifest)
    tampered["assets"][0]["asset_id"] = "A02"
    assert kv.check_duplicate_ids(tampered) == ["A02"]


def test_claims_empty_is_legitimate(manifest):
    # contract: objective.register_assets only, claims may be empty
    assert manifest["claims"] == []
    assert kv.check_claims(manifest["claims"]) == []


def test_no_verified_markers_structurally(manifest):
    # contract: do_not_mark_claims_as_verified. Scan structurally (keys/values).
    def walk(node, path=""):
        hits = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in ("verified", "is_verified", "claim_status"):
                    hits.append(path + "/" + k)
                hits += walk(v, path + "/" + k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                hits += walk(v, "%s/%d" % (path, i))
        elif isinstance(node, str) and node.strip().lower() in ("verified", "verified_true", "true_verified"):
            hits.append(path)
        return hits
    assert walk(manifest) == []


def test_no_report_id_contamination():
    # boundary: only report 8605 files are touched; no other report_id in the manifest
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["report_id"] == "8605"
    assert manifest["package_id"] == "wp-8605-01"
    # ensure no other report_id appears in the source uri
    assert manifest["source"]["uri"] == "tensor://reports/8605"


def test_result_envelope_shape():
    result = json.loads(RESULT_PATH.read_text())
    req = {"package_id", "task_type", "report_id", "provenance", "outputs"}
    assert req.issubset(result)
    assert "asset_manifest.json" in result["outputs"]
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert result["provenance"]["source_field"] == "markdown"
