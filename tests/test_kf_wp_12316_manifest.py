"""Offline regression tests for the wp-12316-01 asset registration (report 12316).

What these tests assert is *invariants*, not "the script ran":
  * the committed manifest validates against the schema copy pinned to this package/report;
  * the result envelope validates against schemas/kf_result.v1.schema.json;
  * asset ids are unique and counts agree with the array length;
  * the manifest's source hash equals the hash pinned by the work-package contract (and the
    report's char count), so a re-registration against a mutated report fails loudly;
  * claims are empty *and* flagged as legitimate-or-not by the policy field (no forced claims);
  * if the fetched markdown is available under runs/wp-12316-01/, every locator must re-slice
    to its quote and every unique quote must occur exactly once. Without the cached markdown the
    locator test skips (offline CI) instead of pretending to pass.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = "wp-12316-01"
CONTRACT_HASH = "a38be5c7ec3bc9250f3d1a53fb75491d66489da695b121134a761e93bdba7f87"
CONTRACT_CHARS = 9610

manifest = json.loads((ROOT / "docs" / PKG / "asset_manifest.json").read_text())
schema = json.loads((ROOT / "docs" / PKG / "asset_manifest.v1.schema.json").read_text())
md_path = ROOT / "runs" / PKG / "report_12316.md"


def test_schema_pinned_to_this_package_and_validates():
    jsonschema = pytest.importorskip("jsonschema")
    assert schema["properties"]["package_id"]["const"] == PKG
    assert schema["properties"]["report_id"]["const"] == "12316"
    jsonschema.validate(manifest, schema)


def test_envelope_validates():
    jsonschema = pytest.importorskip("jsonschema")
    eschema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    env = json.loads((ROOT / "runs" / PKG / "kf_result.wp-12316-01.json").read_text())
    jsonschema.validate(env, eschema)
    assert env["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert env["outputs"]["asset_manifest.json"]["package_id"] == PKG


def test_ids_unique_and_counts_consistent():
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["counts"]["assets"] == len(ids)
    assert manifest["counts"]["by_resolution"]["declared_absent"] == 1


def test_source_hash_pinned_by_contract():
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert manifest["integrity"]["hash_matches_contract"] is True


def test_claims_empty_is_explicitly_legitimate():
    assert manifest["claims"] == []
    assert manifest["objective"] == {"register_assets": True, "classify_report_type": False}
    assert "空数组是完整结果" in manifest["claims_note"]


def test_no_asset_claims_to_be_verified():
    blob = json.dumps(manifest, ensure_ascii=False).replace('"not_verified"', "")
    assert '"verified"' not in blob
    assert manifest["integrity"]["verification_status"] == "not_verified"


def test_external_paths_are_classified_not_dropped():
    ext = [a for a in manifest["assets"] if a["resolution"] == "referenced_unresolved"]
    assert len(ext) == manifest["counts"]["referenced_unresolved"] == 24
    for a in ext:
        assert a["resolution_check"]["result"] in ("resolved", "unresolved", "absent", "present")
        assert a["payload"]["status"] in (
            "external_resolved_at_reported_path", "external_not_found", "platform_record_field")


@pytest.mark.skipif(not md_path.exists(), reason="cached source markdown not in this checkout")
def test_markdown_hash_and_locators_resolve():
    md = md_path.read_text()
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            # documented convention: span = whole markdown, quote = its first line
            assert (loc["start_char"], loc["end_char"]) == (0, len(md)), a["asset_id"]
            assert loc["quote"] == md.split("\n")[0], a["asset_id"]
        else:
            assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        if loc["unique"]:
            assert md.count(loc["quote"]) == 1, a["asset_id"]