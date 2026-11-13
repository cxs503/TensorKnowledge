"""Invariant tests for KF work package wp-12025-01 (asset registration of report 12025).

These assert *invariants a wrong product would violate*, not merely that code ran:
  * the registered source hash equals the contract literal and the local markdown copy;
  * every locator.quote is a unique sub-string of the source markdown AND equals the slice at
    (start_char, end_char) — so a retyped/altered quote fails, not just a missing one;
  * asset ids are unique and counts are internally consistent;
  * nothing in the product claims `verified` (the gate, not the producer, decides verification);
  * the result envelope validates against schemas/kf_result.v1.schema.json.

Skips (not fails) the platform round-trip when no credentials are present; when credentials exist the
source hash is re-derived from a fresh API fetch.

Run: python3 -m pytest tests/test_kf_wp12025_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = "wp-12025-01"
CONTRACT_HASH = "6ebcceb70d4aa23bd429e13496cfa2ac2fc933c83461eef0a0c58a29321df0ed"
MANIFEST = ROOT / "artifacts" / PKG / "asset_manifest.json"
MD = ROOT / "runs" / PKG / "report_12025.md"
RESULT = ROOT / "runs" / PKG / f"kf_result.{PKG}.json"
BLOCK = ROOT / "runs" / PKG / f"kf_result_block.{PKG}.json"
SCHEMA = ROOT / "schemas" / "asset_manifest.v2.schema.json"
ENVELOPE = ROOT / "schemas" / "kf_result.v1.schema.json"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def md():
    return MD.read_text()


def test_manifest_matches_schema(manifest):
    jsonschema.Draft7Validator(json.loads(SCHEMA.read_text())).validate(manifest)


def test_source_hash_is_contract_hash(manifest, md):
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert manifest["source"]["chars"] == len(md)
    assert manifest["source"]["bytes_utf8"] == len(md.encode())
    assert manifest["source"]["uri"] == "tensor://reports/12025"


def test_every_locator_is_a_unique_verbatim_slice(manifest, md):
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        assert md[loc["start_char"]:loc["end_char"]] == q, f"{a['asset_id']}: slice != quote"
        assert md.count(q) == 1, f"{a['asset_id']}: quote not unique"
        assert loc["unique"] is True


def test_no_duplicate_ids_and_counts_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    c = manifest["counts"]
    assert c["assets"] == len(ids)
    assert c["resolved_in_source"] + c["referenced_unresolved"] + c["declared_absent"] == len(ids)
    by_class = {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
    assert by_class == c["by_class"]


def test_claims_are_empty_or_evidenced(manifest):
    for c in manifest["claims"]:
        assert c.get("evidence_locator") or c.get("status"), c.get("claim_id")


def test_declared_absence_resolution_check_is_machine_result(manifest):
    """declared_absent assets must carry a computed check result, not an assertion."""
    for a in manifest["assets"]:
        if a["resolution"] == "declared_absent":
            assert a["resolution_check"]["result"] == "absent"
            assert a["resolution_check"]["check"]
        if a["resolution"] == "referenced_unresolved":
            assert a["resolution_check"]["result"] == "unresolved"


def test_no_verified_marker_in_product():
    blob = MANIFEST.read_text()
    assert '"verified"' not in blob
    env = json.loads(RESULT.read_text())
    assert env["provenance"]["verification_status"] == "not_verified"


def test_envelope_validates_and_matches_manifest():
    env = json.loads(RESULT.read_text())
    jsonschema.Draft7Validator(json.loads(ENVELOPE.read_text())).validate(env)
    assert env["package_id"] == PKG
    assert env["report_id"] == "12025"
    assert env["task_type"] == "01-asset-registration"
    assert env["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert json.loads(BLOCK.read_text()) == env
    out = env["outputs"]["asset_manifest.json"]
    assert out == json.loads(MANIFEST.read_text())          # envelope carries the file content verbatim
    assert out["source"]["hash"] == CONTRACT_HASH
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == env["provenance"]["artifact_sha256"]


def test_platform_hash_roundtrip(manifest):
    """Independent re-fetch: the platform's current markdown must still hash to the contract value."""
    import urllib.request

    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        pytest.skip("no platform credentials in env")
    req = urllib.request.Request(base + "/auth/login",
                                 data=json.dumps({"username": u, "password": p}).encode(),
                                 headers={"Content-Type": "application/json"})
    tok = json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]
    req = urllib.request.Request(base + "/tensor/reports/12025",
                                 headers={"Authorization": "Bearer " + tok})
    live = json.loads(urllib.request.urlopen(req, timeout=30).read())["markdown"]
    assert hashlib.sha256(live.encode()).hexdigest() == manifest["source"]["hash"]