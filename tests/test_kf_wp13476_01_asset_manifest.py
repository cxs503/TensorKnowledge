"""Offline checks for work package wp-13476-01 (report 13476 asset registration).

These tests never touch the network: they verify the committed artefacts against the
committed verbatim markdown copy, so CI can reproduce the gate-relevant invariants
without platform credentials.
"""
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-13476-01"
CONTRACT_HASH = "sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0"


@pytest.fixture(scope="module")
def manifest():
    return json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source_md():
    return (OUT / "source_markdown.md").read_text(encoding="utf-8")


def test_source_hash_matches_contract_and_provenance(source_md, manifest, envelope):
    live = "sha256:" + hashlib.sha256(source_md.encode("utf-8")).hexdigest()
    assert live == CONTRACT_HASH
    assert manifest["source"]["hash"] == live
    assert envelope["provenance"]["source_hash"] == live
    assert len(source_md) == manifest["source"]["chars"] == 12871


def test_schemas_pass(manifest, envelope):
    env_schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    man_schema = json.loads((OUT / "asset_manifest.schema.json").read_text())
    jsonschema.validate(envelope, env_schema)
    jsonschema.validate(manifest, man_schema)


def test_envelope_shape(manifest, envelope):
    assert envelope["package_id"] == "wp-13476-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "13476"
    assert list(envelope["outputs"]) == ["asset_manifest.json"]
    assert envelope["outputs"]["asset_manifest.json"]["counts"] == manifest["counts"]


def test_every_locator_resolves(manifest, source_md):
    for loc in manifest["locators"]:
        q = loc["quote"]
        assert q, loc["asset_id"]
        if loc["source_field"] == "record":
            # metadata-only asset: must be anchored on the record field, not invented
            assert loc["record_path"].startswith("figures[")
            assert loc["quote_in_source"] is True
        elif loc["method"] == "document":
            assert loc["start_char"] == 0
            assert loc["end_char"] == len(source_md)
            assert source_md.startswith(q)
        else:
            assert source_md[loc["start_char"]:loc["end_char"]] == q, loc["asset_id"]
            assert q in source_md


def test_asset_ids_unique_and_formatted(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(len(i) == 3 and i[0] == "A" and i[1:].isdigit() for i in ids)
    assert manifest["id_integrity"]["unique"] is True
    assert manifest["id_integrity"]["duplicates"] == []


def test_claims_empty_with_explicit_reason(manifest, envelope):
    assert envelope["claims"] == []
    assert manifest["claims"] == []
    reason = manifest["claims_empty_reason"]
    assert "classify_report_type=false" in reason
    assert "empty claims array is the complete result" in reason


def test_no_verified_marks(manifest, envelope):
    blob = json.dumps(envelope, ensure_ascii=False).lower()
    for banned in ('"verified": true', '"status": "verified"', '"verified"'):
        assert banned not in blob


def test_resolution_accounting(manifest):
    counts = manifest["counts"]
    assert counts["assets"] == len(manifest["assets"])
    assert counts["resolved_in_source"] + counts["referenced_unresolved"] + \
        counts["declared_absent"] == counts["assets"]
    assert len(manifest["unresolved"]) == counts["referenced_unresolved"]
