#!/usr/bin/env python3
"""pytest suite for KF work package wp-14478-01 (asset registration of report 14478).

Positive checks prove the shipped artifacts satisfy the acceptance items offline; the negative
controls prove the checker actually rejects tampering (a green suite that cannot fail is worthless).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wp-14478-01"
sys.path.insert(0, str(ROOT / "scripts"))

import kf_verify_14478 as verify  # noqa: E402

CONTRACT_HASH = "8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0"


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return (OUT / "source.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load("asset_manifest.json")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return load("kf_result.wp-14478-01.json")


def test_pinned_source_hash_and_chars(source: str) -> None:
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(source) == 6156


def test_envelope_schema(envelope: dict) -> None:
    schema = load("kf_result.v1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(envelope)
    assert envelope["report_id"] == "14478"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH


def test_manifest_schema(manifest: dict) -> None:
    schema = load("asset_manifest.v1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(manifest)


def test_locators_resolve_offline(source: str, manifest: dict) -> None:
    assert verify.check_locators(source, manifest["assets"]) == []


def test_claims_empty_and_explained(manifest: dict, envelope: dict) -> None:
    assert manifest["claims"] == [] and envelope["claims"] == []
    assert "task_type 03" in manifest["claims_note"]


def test_ids_unique(manifest: dict, envelope: dict) -> None:
    assert verify.check_unique_ids(manifest, envelope) == []


def test_boundaries(manifest: dict, envelope: dict) -> None:
    assert verify.check_boundaries(manifest, envelope) == []
    assert manifest["boundaries"]["only_report_id"] == "14478"


def test_missing_payloads_not_upgraded(manifest: dict) -> None:
    """The source states runs/ and analysis/ were never produced; the manifest must keep them missing."""
    by_id = {a["asset_id"]: a for a in manifest["assets"]}
    for aid in ("A11", "A12", "A13", "A18", "A19"):
        assert by_id[aid]["payload"]["status"] == "declared_payload_missing", aid
    assert [a["asset_id"] for a in manifest["assets"] if a["payload"]["status"] == "in_report_record"] == ["A01"]


def test_counts_consistent(manifest: dict) -> None:
    assets = manifest["assets"]
    assert manifest["counts"]["assets"] == len(assets) == 20
    by_status: dict[str, int] = {}
    for a in assets:
        by_status[a["payload"]["status"]] = by_status.get(a["payload"]["status"], 0) + 1
    assert by_status == manifest["counts"]["by_payload_status"]


def test_source_hash_matches_contract_integrity(manifest: dict) -> None:
    assert verify.sha256_hex((OUT / "source.md").read_text(encoding="utf-8")) == CONTRACT_HASH
    assert manifest["integrity"]["hash_matches_contract"] is True
    assert manifest["source"]["hash"] == CONTRACT_HASH


# ---------------------------------------------------------------- negative controls

def test_negative_tampered_quote_is_rejected(source: str, manifest: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["assets"][3]["locator"]["quote"] = broken["assets"][3]["locator"]["quote"] + "X"
    assert verify.check_locators(source, broken["assets"]) != []


def test_negative_shifted_span_is_rejected(source: str, manifest: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["assets"][5]["locator"]["start_char"] += 1
    broken["assets"][5]["locator"]["end_char"] += 1
    assert verify.check_locators(source, broken["assets"]) != []


def test_negative_wrong_line_numbers_rejected(source: str, manifest: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["assets"][7]["locator"]["start_line"] += 1
    assert any("line span" in e for e in verify.check_locators(source, broken["assets"]))


def test_negative_duplicate_asset_id_rejected(manifest: dict, envelope: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["assets"][1]["asset_id"] = broken["assets"][0]["asset_id"]
    assert verify.check_unique_ids(broken, envelope) != []


def test_negative_source_drift_rejected(source: str, manifest: dict) -> None:
    drifted = source.replace("honest-FAIL", "PASS", 1)
    assert verify.sha256_hex(drifted) != CONTRACT_HASH
    # a drifted document also breaks locator resolution for downstream offsets
    assert verify.check_locators(drifted, manifest["assets"]) != []


def test_negative_self_verified_status_rejected(manifest: dict, envelope: dict) -> None:
    broken = copy.deepcopy(envelope)
    broken["claims"] = [{"claim_id": "c1", "text": "x", "status": "verified"}]
    assert verify.check_claim_policy(manifest, broken) != []


def test_negative_wrong_report_id_rejected(manifest: dict, envelope: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["report_id"] = "14479"
    assert verify.check_boundaries(broken, envelope) != []


def test_negative_envelope_manifest_mismatch_rejected(manifest: dict, envelope: dict) -> None:
    broken = copy.deepcopy(envelope)
    broken["outputs"]["asset_manifest.json"] = copy.deepcopy(manifest)
    broken["outputs"]["asset_manifest.json"]["counts"]["assets"] = 19
    assert any("byte-equal" in e for e in verify.check_unique_ids(manifest, broken))


def test_negative_schema_rejects_bad_status(manifest: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["assets"][10]["payload"]["status"] = "present_but_unverified"
    schema = load("asset_manifest.v1.schema.json")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(broken)