"""Offline acceptance tests for work package wp-9912-01 (report_id=9912).

These tests do not touch the network: they recompute everything from the stored copy of the
source markdown (runs/wp-9912-01/report_9912.md) plus the delivered artifacts, so that
`pytest tests/test_kf_register_9912.py -q` is a self-contained reproduction of the six
acceptance items in the work-package contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "kf", "wp-9912-01")
SOURCE_COPY = os.path.join(ROOT, "runs", "wp-9912-01", "report_9912.md")
CONTRACT_HASH = "a20e4a075123e95c5fbca4c9938b39d8ddb6c317272bbef6958b3b6aa65e158d"
CONTRACT_CHARS = 4983


@pytest.fixture(scope="module")
def md() -> str:
    return open(SOURCE_COPY, encoding="utf-8").read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.load(open(os.path.join(OUT, "asset_manifest.json"), encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))


def test_source_hash_and_length_match_contract(md, manifest, envelope):
    recomputed = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert recomputed == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["integrity"]["hash_matches_contract"] is True
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH


def test_every_locator_quote_resolves_to_its_char_span(md, manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert len(loc["quote"]) > 0
        # start_line must point at a line that begins the quote
        lines = md.split("\n")
        assert loc["quote"].split("\n")[0] in lines[loc["start_line"]], a["asset_id"]
        # uniqueness claim must equal the measured occurrence count
        assert md.count(loc["quote"]) == loc["occurrences_in_source"], a["asset_id"]
        assert loc["unique"] == (loc["occurrences_in_source"] == 1), a["asset_id"]


def test_asset_ids_and_spans_are_distinct(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == [f"A{i:02d}" for i in range(1, len(ids) + 1)]
    spans = {(a["locator"]["start_line"], a["locator"]["end_line"], a["asset_class"]) for a in manifest["assets"]}
    assert len(spans) == len(ids)


def test_manifest_and_envelope_validate_against_schemas(manifest, envelope):
    pin = json.load(open(os.path.join(OUT, "asset_manifest.v1.schema.json"), encoding="utf-8"))
    kf_schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"), encoding="utf-8"))
    jsonschema.Draft7Validator(pin).validate(manifest)
    jsonschema.Draft202012Validator(kf_schema).validate(envelope)
    assert manifest["package_id"] == "wp-9912-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "9912"


def test_claims_are_empty_and_nothing_is_marked_verified(manifest, envelope):
    assert manifest["claims"] == [] and envelope["claims"] == []
    assert envelope["provenance"]["verification_status"] == "not_verified"
    blob = json.dumps(manifest, ensure_ascii=False)
    assert '"verified"' not in blob and "verified_" not in blob


def test_report_markdown_has_exactly_one_json_block_that_round_trips(envelope):
    report = open(os.path.join(OUT, "report.md"), encoding="utf-8").read()
    assert len(re.findall(r"```", report)) == 2, "exactly one fenced block (the result envelope)"
    blocks = re.findall(r"```json\n(.*?)\n```", report, re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == envelope
    assert "asset_manifest.json" in envelope["outputs"]


def test_envelope_payload_matches_artifact_on_disk(manifest, envelope):
    inline = envelope["outputs"]["asset_manifest.json"]
    for key in ("source", "counts", "assets", "claims", "integrity"):
        assert inline[key] == manifest[key], key


def test_no_invented_numbers_in_prose(manifest, md):
    """Every reference path the manifest registers must literally occur in the source."""
    for a in manifest["assets"]:
        path = a.get("path_reference")
        if path:
            assert path in md, (a["asset_id"], path)
        symbol = a.get("symbol")
        if symbol:
            assert symbol in md, (a["asset_id"], symbol)