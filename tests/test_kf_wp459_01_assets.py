"""Acceptance tests for KF work package wp-459-01 (01-asset-registration).

These tests are the machine-readable form of the package contract's
``acceptance`` block:

* valid_json                -> both JSON artefacts parse
* schema_pass               -> kf_result.json validates against schemas/kf_result.v1.schema.json
* source_locator_resolvable -> every quote is a verbatim substring at its stated line
* source_hash_matches       -> recomputed sha256 of the report markdown == contract hash
* no_duplicate_ids          -> asset_id / (kind, name) uniqueness
* all_claims_have_evidence_or_explicit_unresolved_status -> claims array is empty (legal)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "docs" / "kf" / "wp-459-01"
MANIFEST_PATH = PKG_DIR / "asset_manifest.json"
RESULT_PATH = PKG_DIR / "kf_result.json"
SNAPSHOT_PATH = PKG_DIR / "source_459.json"
SCHEMA_PATH = ROOT / "schemas" / "kf_result.v1.schema.json"

CONTRACT_SHA256 = "333ea7e4c7b908bc9701a34c72960d0e0e8ed728798758fd68f830a75507f6b9"
CONTRACT_CHARS = 7586


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def markdown() -> str:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))["markdown"]


def test_manifest_and_result_are_valid_json():
    assert isinstance(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")), dict)
    assert isinstance(json.loads(RESULT_PATH.read_text(encoding="utf-8")), dict)


def test_result_matches_envelope_schema(result):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(result)


def test_report_identity_and_scope(manifest, result):
    assert manifest["source"]["report_id"] == "459"
    assert result["report_id"] == "459"
    assert manifest["package_id"] == result["package_id"] == "wp-459-01"
    assert result["task_type"] == "01-asset-registration"


def test_source_hash_matches_contract(manifest, result, markdown):
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_SHA256
    assert manifest["source"]["sha256"] == digest
    assert manifest["source"]["source_hash_matches"] is True
    assert result["provenance"]["source_hash"] == "sha256:" + digest
    assert result["provenance"]["source_field"] == "markdown"


def test_source_length_matches_contract(manifest, markdown):
    assert len(markdown) == CONTRACT_CHARS
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert manifest["source"]["chars_match"] is True
    assert manifest["source"]["bytes_utf8"] == len(markdown.encode("utf-8"))


def test_result_embeds_the_committed_manifest(result, manifest):
    assert result["outputs"]["asset_manifest.json"] == manifest


def _quotes(asset: dict) -> list[dict]:
    locs = list(asset.get("locators") or [])
    if asset.get("locator"):
        locs.append(asset["locator"])
    return [loc for loc in locs if loc.get("source_field") == "markdown" and loc.get("quote")]


def test_every_markdown_locator_resolves(manifest, markdown):
    lines = markdown.split("\n")
    checked = 0
    for asset in manifest["assets"]:
        for loc in _quotes(asset):
            quote = loc["quote"]
            assert quote, f"{asset['asset_id']}: empty quote"
            assert quote in markdown, f"{asset['asset_id']}: quote not verbatim in markdown"
            if "line" in loc:
                assert loc["line"] >= 1
                assert quote in lines[loc["line"] - 1], (
                    f"{asset['asset_id']}: quote not on declared line {loc['line']}"
                )
            checked += 1
    assert checked >= 20, "too few resolvable locators to be meaningful"


def test_no_duplicate_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    keys = [(a["kind"], a["name"]) for a in manifest["assets"]]
    assert len(keys) == len(set(keys))


def test_offset_locator_resolves(manifest, markdown):
    text_assets = [a for a in manifest["assets"] if a["kind"] == "source_text"]
    loc = text_assets[0]["locator"]
    assert loc["source_field"] == "markdown"
    assert loc["offset"] == 0 and loc["length"] == len(markdown)
    assert markdown[loc["offset"]: loc["offset"] + loc["length"]] == markdown


def test_registered_text_asset_carries_real_bytes(manifest, markdown):
    text_assets = [a for a in manifest["assets"] if a["kind"] == "source_text"]
    assert len(text_assets) == 1
    asset = text_assets[0]
    assert asset["payload"]["present"] is True
    assert asset["payload"]["sha256"] == CONTRACT_SHA256
    assert asset["payload"]["chars"] == len(markdown)
    assert asset["payload"]["bytes_utf8"] == len(markdown.encode("utf-8"))


def test_figures_without_payload_are_registered_as_unresolved(manifest):
    figures = [a for a in manifest["assets"] if a["kind"] == "figure"]
    assert len(figures) == manifest["source"]["figures_entries"] >= 1
    unresolved_items = {u["item"] for u in manifest["unresolved"]}
    for fig in figures:
        assert fig["payload"]["present"] is False
        assert fig["payload"]["sha256"] is None
        assert fig["status"] == "declared_metadata_only"
        assert not fig["resolvable"]
        assert any(u.endswith(":" + fig["name"]) for u in unresolved_items)


def test_declared_artifacts_are_not_overclaimed(manifest):
    declared = [a for a in manifest["assets"] if a["kind"] == "declared_artifact"]
    assert declared, "report declares deliverables"
    for asset in declared:
        assert asset["resolvable"] is False
        assert asset["payload"]["present"] is False
        assert asset["payload"]["sha256"] is None
        assert asset["status"] in {"declared_only", "declared_shorthand"}
        if asset.get("existence_check"):
            assert "existence_check_all_absent" in asset


def test_claims_are_empty_or_evidenced(result):
    """01 registers assets; zero claims is a legal complete result."""
    claims = result.get("claims", [])
    assert claims == []
    for claim in claims:  # defensive: if a later revision adds claims
        assert claim.get("evidence") or claim.get("unresolved_reason")


def test_manifest_is_deterministic(manifest):
    """No wall-clock fields -> re-running the generator reproduces identical bytes."""
    serialised = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    assert serialised == MANIFEST_PATH.read_text(encoding="utf-8")