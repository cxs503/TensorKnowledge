"""Offline self-consistency tests for KF work package wp-14179-01 artifacts.

No network: everything is checked against the committed source snapshot
(docs/kf/wp-14179-01/source.md) and the committed JSON deliverables. The network
re-fetch + live hash identity check lives in scripts/kf_wp14179_01_verify.py.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/kf/wp-14179-01"
ART = ROOT / "artifacts/wp-14179-01"
CONTRACT_HASH = "2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315"


@pytest.fixture(scope="module")
def source() -> str:
    return (DOC / "source.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((ART / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((DOC / "kf_result.json").read_text(encoding="utf-8"))


def test_source_hash_matches_contract(source):
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(source) == 5506


def test_envelope_validates_against_kf_result_schema(envelope):
    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(envelope)
    assert envelope["package_id"] == "wp-14179-01"
    assert envelope["report_id"] == "14179"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["provenance"]["verification_status"] == "not_verified"


def test_manifest_validates_against_pinned_schema(manifest):
    schema = json.loads((DOC / "asset_manifest.v1.wp-14179-01.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(manifest)


def test_every_locator_resolves_verbatim_and_uniquely(source, manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        assert source[loc["start_char"]:loc["end_char"]] == quote, a["asset_id"]
        assert source.count(quote) == 1, a["asset_id"]
        assert source[: loc["start_char"]].count("\n") == loc["start_line"], a["asset_id"]


def test_asset_ids_unique_and_counts_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)
    by_res = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert manifest["counts"]["assets"] == len(ids)
    assert manifest["counts"]["by_resolution"] == by_res
    assert manifest["counts"]["resolved_in_source"] == by_res.get("resolved_in_source", 0)
    assert manifest["counts"]["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)


def test_claims_empty_and_nothing_marked_verified(manifest, envelope):
    assert manifest["claims"] == [] and envelope.get("claims", []) == []
    blob = json.dumps(manifest, ensure_ascii=False) + json.dumps(envelope, ensure_ascii=False)
    assert '"status": "verified"' not in blob
    assert manifest["boundary"]["only_report_id"] == "14179"
    assert manifest["boundary"]["marked_verified"] is False


def test_registered_figures_exist_in_record_metadata(manifest):
    figs = manifest["source"]["platform_figures"]
    for a in manifest["assets"]:
        if a["asset_class"] == "figure":
            assert a["resolution_check"]["figure_name"] in figs
            assert a["resolution_check"]["result"] == "present"


def test_report_body_has_exactly_one_json_block_equal_to_envelope(envelope):
    body = (DOC / "report_body.md").read_text(encoding="utf-8")
    assert body.startswith("# KF-RESULT wp-14179-01")
    assert "kf-wp:wp-14179-01" in body
    blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == envelope


def test_durable_mirror_is_byte_identical(manifest):
    assert (ART / "asset_manifest.json").read_bytes() == (DOC / "asset_manifest.json").read_bytes()
