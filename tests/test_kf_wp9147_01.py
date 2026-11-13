"""Delivery tests for work package wp-9147-01 (asset registration of report 9147).

These tests are the guard against silently-broken deliverables: they re-derive everything from the
committed artifacts in docs/kf/wp-9147-01/ and never touch the network (so they also run in CI
without credentials). They assert *invariants*, not just "the file loads":

  * the pinned sha256 equals the contract hash and the committed source.md bytes
  * every asset quote slices back to itself at its declared char span, is unique, and its line span
    matches the same slice (so a locator cannot drift away from its quote)
  * ids are unique, resolution enum values are legal, and the counts agree with the assets
  * the report carries exactly one fenced json block and it equals kf_result.json
  * no claim is marked verified (out of scope for this task type)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs/kf/wp-9147-01"
CONTRACT_HASH = "754d613193b8da4880f56371095812b6865d4d376bdca5edb8ab4f4ceb6d0ff6"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return (PKG / "source.md").read_bytes().decode("utf-8")


def test_source_hash_matches_contract(manifest, source):
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert hashlib.sha256((PKG / "source.md").read_bytes()).hexdigest() == CONTRACT_HASH
    assert manifest["source"]["chars"] == len(source)
    assert manifest["source"]["bytes_utf8"] == len(source.encode("utf-8"))
    assert manifest["source"]["hash_matches_contract"] is True


def test_manifest_matches_pinned_schema(manifest):
    schema = json.loads((PKG / "asset_manifest.wp-9147-01.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_envelope_matches_kf_result_schema():
    envelope = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert list(envelope["outputs"]) == ["asset_manifest.json"]


def test_every_locator_slices_back_verbatim(manifest, source):
    lines = source.splitlines()
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        assert source[loc["start_char"]:loc["end_char"]] == q, a["asset_id"]
        assert source.count(q) == 1, a["asset_id"]
        assert loc["unique"] is True
        if loc["method"] == "document":
            assert q == source
        else:
            assert q == "\n".join(lines[loc["start_line"]:loc["end_line"] + 1]), a["asset_id"]
            assert 0 <= loc["start_line"] <= loc["end_line"] < len(lines)


def test_ids_unique_and_counts_consistent(manifest):
    assets = manifest["assets"]
    ids = [a["asset_id"] for a in assets]
    assert len(ids) == len(set(ids))
    assert manifest["counts"]["assets"] == len(assets)
    by_res = {}
    by_cls = {}
    for a in assets:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved", "declared_absent"}
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
        by_cls[a["asset_class"]] = by_cls.get(a["asset_class"], 0) + 1
    assert manifest["counts"]["by_resolution"] == by_res
    assert manifest["counts"]["by_class"] == by_cls
    # the PNG is declared in the text but the record carries no attachment -> absent, not "resolved"
    assert manifest["counts"]["declared_absent"] == 1
    assert [f for f in manifest["source"]["platform_figures"]] == []


def test_no_claim_is_marked_verified(manifest):
    assert manifest["claims"] == []
    envelope = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    assert envelope["claims"] == []
    blob = json.dumps(envelope, ensure_ascii=False)
    assert "\"verified\"" not in blob


def test_report_has_exactly_one_json_block_equal_to_envelope():
    report = (ROOT / "docs/kf_result_wp-9147-01.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", report, re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))


def test_acceptance_check_all_pass():
    acc = json.loads((PKG / "acceptance_check.json").read_text(encoding="utf-8"))
    assert acc["all_pass"] is True
    assert acc["passed"] == acc["total"] == 6
    assert {i["item"] for i in acc["items"]} == {
        "valid_json",
        "schema_pass",
        "source_locator_resolvable",
        "source_hash_matches",
        "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status",
    }