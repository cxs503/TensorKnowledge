"""Offline regression for work package wp-10647-01 (asset registration of report 10647).

These tests do not touch the network: the source markdown snapshot under runs/ is used as the
reference byte stream, exactly like the verifier's offline mode. Anything that is *not* checked
here is stated at the bottom of this docstring -- silence is not a pass.

Checks
  * envelope / manifest validate against their JSON Schemas;
  * source hash and char count match the contract-declared constants;
  * every locator re-resolves by character slice and is a unique substring;
  * asset ids and quotes are unique; counts agree with the recomputed distribution;
  * resolution_check.result is consistent with resolution (resolved/unresolved/absent);
  * claims is empty and no asset carries a "verified" status;
  * the envelope's outputs.asset_manifest.json is byte-identical to the artifact, and the
    "single json block" file is identical to the envelope.

Not checked here (needs network / external repos): fresh API re-fetch independence, the existence of
TensorPlatform files referenced by the report, platform-side figure bytes, and any recomputation of the
upstream numbers themselves.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/wp-10647-01"
ART = ROOT / "artifacts/wp-10647-01"
EXPECTED_HASH = "aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31"
EXPECTED_CHARS = 10814


@pytest.fixture(scope="module")
def md() -> str:
    return (RUN / "report_10647.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((ART / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((RUN / "kf_result.wp-10647-01.json").read_text(encoding="utf-8"))


def test_source_snapshot_matches_contract(md):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
    assert len(md) == EXPECTED_CHARS


def test_manifest_schema(manifest):
    schema = json.loads((ROOT / "schemas/asset_manifest.v2.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(manifest)


def test_envelope_schema(envelope):
    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)


def test_locators_resolve(md, manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) == 1, a["asset_id"]
        assert loc["end_char"] > loc["start_char"]
        assert loc["start_line"] <= loc["end_line"]


def test_section_is_a_real_heading(md, manifest):
    for a in manifest["assets"]:
        assert a["in_report_section"].startswith("#"), a["asset_id"]
        assert a["in_report_section"] in md, a["asset_id"]


def test_ids_and_quotes_unique(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    quotes = [a["locator"]["quote"] for a in manifest["assets"]]
    assert len(set(ids)) == len(ids)
    assert len(set(quotes)) == len(quotes)
    for i in ids:
        assert len(i) == 3 and i[0] == "A" and i[1:].isdigit()


def test_counts_consistent(manifest):
    by_res, by_cls = {}, {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
        by_cls[a["asset_class"]] = by_cls.get(a["asset_class"], 0) + 1
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    assert c["by_resolution"] == dict(sorted(by_res.items()))
    assert c["by_class"] == dict(sorted(by_cls.items()))
    assert c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
    assert c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
    assert c["declared_absent"] == by_res.get("declared_absent", 0)


def test_resolution_check_consistent(manifest):
    mapping = {"resolved_in_source": "resolved", "referenced_unresolved": "unresolved",
               "declared_absent": "absent"}
    for a in manifest["assets"]:
        assert a["resolution_check"]["result"] == mapping[a["resolution"]], a["asset_id"]


def test_claims_empty_and_no_verified(manifest, envelope):
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert all(a["resolution"] != "verified" for a in manifest["assets"])
    assert manifest["integrity"]["hash_matches_contract"] is True


def test_envelope_identity(manifest, envelope):
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    assert envelope["package_id"] == manifest["package_id"] == "wp-10647-01"
    assert envelope["report_id"] == manifest["report_id"] == "10647"
    assert envelope["provenance"]["source_hash"] == "sha256:" + manifest["source"]["hash"]
    block = json.loads((RUN / "kf_result_block.wp-10647-01.json").read_text(encoding="utf-8"))
    assert block == envelope


def test_no_nested_spans_except_design_table(manifest):
    allowed = {("A10", "A05"), ("A10", "A06"), ("A10", "A07"), ("A10", "A08")}
    spans = sorted((a["locator"]["start_char"], a["locator"]["end_char"], a["asset_id"])
                   for a in manifest["assets"])
    prev = None
    for s, e, i in spans:
        if prev and s < prev[1]:
            assert (prev[2], i) in allowed, (prev[2], i)
        prev = (s, e, i)
