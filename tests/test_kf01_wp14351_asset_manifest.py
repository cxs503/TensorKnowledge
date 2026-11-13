"""KF work package wp-14351-01 (01-asset-registration) artifact invariants.

Self-contained: the manifest carries the full source markdown as asset A01's
quote, so the source can be reconstructed and every other locator re-resolved
without network access. Run:  python -m pytest tests/test_kf01_wp14351_asset_manifest.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-14351-01"
CONTRACT_HASH = "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558"
CONTRACT_CHARS = 4190


@pytest.fixture(scope="module")
def manifest():
    return json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source_md(manifest):
    doc = [a for a in manifest["assets"] if a["locator"]["method"] == "document"]
    assert len(doc) == 1
    return doc[0]["locator"]["quote"]


def test_manifest_matches_pinned_schema(manifest):
    schema = json.loads((OUT / "asset_manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_envelope_matches_kf_result_schema(envelope):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["outputs"]["asset_manifest.json"]["package_id"] == "wp-14351-01"
    assert envelope["report_id"] == "14351"
    assert envelope["task_type"] == "01-asset-registration"


def test_source_hash_and_chars_match_contract(source_md, manifest):
    h = "sha256:" + hashlib.sha256(source_md.encode()).hexdigest()
    assert h == CONTRACT_HASH == manifest["source"]["sha256"]
    assert len(source_md) == CONTRACT_CHARS == manifest["source"]["chars"]
    assert manifest["source"]["source_hash_matches"] is True


def test_every_locator_resolves_inside_source(manifest, source_md):
    checked = 0
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            continue
        assert source_md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert source_md.count(loc["quote"]) == 1, a["asset_id"]
        quote_hash = "sha256:" + hashlib.sha256(loc["quote"].encode()).hexdigest()
        assert quote_hash == loc["quote_sha256"], a["asset_id"]
        checked += 1
    assert checked == len(manifest["assets"]) - 1


def test_ids_unique_and_counts_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    by_res = {"resolved_in_source": 0, "referenced_unresolved": 0, "declared_absent": 0}
    for a in manifest["assets"]:
        by_res[a["resolution"]] += 1
    assert by_res == manifest["counts"]["by_resolution"]
    assert manifest["counts"]["assets"] == len(ids)


def test_no_claims_no_verified(manifest, envelope):
    assert manifest["claims"] == [] and envelope["claims"] == []
    assert manifest["integrity"]["claims_marked_verified"] == 0
    blob = json.dumps(manifest["assets"], ensure_ascii=False)
    assert '"verified"' not in blob


def test_unresolved_assets_carry_machine_check(manifest):
    for a in manifest["assets"]:
        chk = a["resolution_check"]
        assert chk["check"] and chk["result"] in {"resolved", "unresolved", "absent", "present"}
        if a["resolution"] == "referenced_unresolved":
            assert chk["result"] == "unresolved"
            assert "detail" in chk