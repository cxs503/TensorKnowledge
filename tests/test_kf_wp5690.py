"""Invariant tests for work package wp-5690-01 (asset registration of report 5690).

Each acceptance criterion is asserted on the real artifact, and every locator/hash/duplicate check is
additionally given a negative control (tampered copy) so the test proves the check can fail rather
than merely executing code.

Run: pytest -q tests/test_kf_wp5690.py
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

import kf_verify_5690 as kv  # noqa: E402

MANIFEST_PATH = ROOT / "artifacts/wp-5690-01/asset_manifest.json"
SCHEMA_PATH = ROOT / "schemas/asset_manifest.v1.schema.json"
RESULT_PATH = ROOT / "runs/wp-5690-01/kf_result.wp-5690-01.json"
BLOCK_PATH = ROOT / "runs/wp-5690-01/kf_result_block.wp-5690-01.json"
MD_PATH = ROOT / "runs/wp-5690-01/report_5690.md"
CONTRACT_HASH = "a1e3f5faa1f969bcdfb759f7357adb8cc7474194e44a2c02ae4370f1db1b29a1"


@pytest.fixture(scope="module")
def md() -> str:
    return MD_PATH.read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads(RESULT_PATH.read_text())


def test_source_hash_matches_contract_and_local_copy(md, manifest):
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == len(md) == 5390
    assert manifest["source"]["bytes_utf8"] == len(md.encode()) == 8513


def test_manifest_validates_against_local_schema(manifest):
    jsonschema.validate(manifest, json.loads(SCHEMA_PATH.read_text()))


def test_generalized_schema_still_covers_wp448():
    """Regression guard: the schema generalization (const -> pattern) must not break wp-448-01."""
    schema = json.loads(SCHEMA_PATH.read_text())
    m448 = json.loads((ROOT / "docs/wp-448-01/asset_manifest.json").read_text())
    jsonschema.validate(m448, schema)


def test_every_locator_reresolves_uniquely(md, manifest):
    assert kv.check_locators(md, manifest) == []


def test_locator_check_detects_tampered_quote(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = tampered["assets"][4]  # A05 XC table
    assert "1.118" in a["locator"]["quote"]
    a["locator"]["quote"] = a["locator"]["quote"].replace("1.118", "1.119")
    assert any(asset == a["asset_id"] for asset, _ in kv.check_locators(md, tampered))


def test_locator_check_detects_shifted_span(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = tampered["assets"][3]  # A04 upstream table
    a["locator"]["start_char"] += 1
    a["locator"]["end_char"] += 1
    assert any(asset == a["asset_id"] for asset, _ in kv.check_locators(md, tampered))


def test_locator_check_detects_false_resolution_claim(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = next(x for x in tampered["assets"] if x["asset_id"] == "A08")
    a["resolution"] = "resolved_in_source"  # lie: external path is not in this worktree
    assert any(asset == a["asset_id"] for asset, _ in kv.check_locators(md, tampered))


def test_duplicate_id_detection(manifest):
    tampered = copy.deepcopy(manifest)
    tampered["assets"][1]["asset_id"] = tampered["assets"][0]["asset_id"]
    assert kv.check_duplicate_ids(tampered) == [tampered["assets"][0]["asset_id"]]
    assert kv.check_duplicate_ids(manifest) == []


def test_claims_policy(manifest):
    assert manifest["claims"] == []
    assert kv.check_claims(manifest["claims"]) == []
    bad = [{"claim_id": "C1", "text": "no evidence, no status"}]
    assert kv.check_claims(bad) == ["C1"]


def test_no_verified_markers_structural(manifest, result):
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
    assert result["provenance"]["verification_status"] == "not_verified"


def test_counts_consistent(manifest):
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"]) == 17
    assert c["resolved_in_source"] == sum(1 for a in manifest["assets"] if a["resolution"] == "resolved_in_source") == 7
    assert c["referenced_unresolved"] == sum(1 for a in manifest["assets"] if a["resolution"] == "referenced_unresolved") == 10
    assert c["declared_absent"] == 0
    assert c["by_resolution"] == {"resolved_in_source": 7, "referenced_unresolved": 10}


def test_result_envelope_shape_and_ids(result):
    assert {"package_id", "task_type", "report_id", "provenance", "outputs"}.issubset(result)
    assert result["package_id"] == "wp-5690-01"
    assert result["task_type"] == "01-asset-registration"
    assert str(result["report_id"]) == "5690"
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert result["provenance"]["source_uri"] == "tensor://reports/5690"
    assert "asset_manifest.json" in result["outputs"]


def test_block_equals_result(result):
    block = json.loads(BLOCK_PATH.read_text())
    assert block == result


def test_artifact_hash_matches_envelope(result):
    art = MANIFEST_PATH.read_bytes()
    assert hashlib.sha256(art).hexdigest() == result["outputs"]["asset_manifest.json"]["artifact_sha256"]
    assert len(art) == result["outputs"]["asset_manifest.json"]["artifact_bytes"]


def test_durable_mirror_identical(result):
    mirror = ROOT / "docs/wp-5690-01/asset_manifest.json"
    assert mirror.exists()
    assert hashlib.sha256(mirror.read_bytes()).hexdigest() == result["outputs"]["asset_manifest.json"]["artifact_sha256"]


def test_no_report_id_contamination():
    """Boundary discipline: this package must only touch report 5690 files."""
    import re
    offenders = []
    for p in (MANIFEST_PATH, RESULT_PATH, BLOCK_PATH):
        txt = p.read_text()
        for m in re.finditer(r"reports/(\d+)", txt):
            if m.group(1) != "5690":
                offenders.append((str(p), m.group(1)))
    assert offenders == []
