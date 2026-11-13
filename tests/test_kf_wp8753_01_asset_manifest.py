"""Acceptance invariants for work package wp-8753-01 (report 8753 asset registration).

Offline checks always run. The live check (re-fetch report 8753 and re-resolve every
locator against the real markdown bytes) runs when TENSOR_API_BASE is reachable.
"""
import hashlib
import json
import os
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "kf" / "wp-8753-01"
MANIFEST = OUT / "asset_manifest.json"
ENVELOPE = OUT / "kf_result.json"
EXPECTED_HASH = "sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1"
REPORT_ID = "8753"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


def test_manifest_json_and_identity(manifest):
    assert manifest["schema"] == "asset_manifest.v1"
    assert manifest["package_id"] == "wp-8753-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == REPORT_ID
    assert manifest["source"]["uri"] == "tensor://reports/" + REPORT_ID


def test_scope_is_single_report(manifest):
    """No other report id may appear as a registered source (cross-references are declared, not fetched)."""
    blobs = [json.dumps(a, ensure_ascii=False) for a in manifest["assets"]
             if a["asset_class"] != "cross_report_reference"]
    assert all("tensor://reports/" not in b for b in blobs)
    assert manifest["source"]["report_id"] == REPORT_ID


def test_declared_hash_matches_contract(manifest, envelope):
    assert manifest["source"]["source_hash"] == EXPECTED_HASH
    assert envelope["provenance"]["source_hash"] == EXPECTED_HASH
    assert manifest["source"]["hash_matches_contract"] is True
    assert manifest["source"]["chars_match_contract"] is True


def test_envelope_schema_fields(envelope):
    import jsonschema
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.validate(envelope, schema)
    assert envelope["outputs"]["asset_manifest.json"]["report_id"] == REPORT_ID
    assert envelope["provenance"]["source_field"] == "markdown"


def test_manifest_schema(manifest):
    import jsonschema
    schema = json.loads((OUT / "asset_manifest.schema.json").read_text())
    jsonschema.validate(manifest, schema)


def test_asset_ids_unique_and_counts_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids and len(ids) == len(set(ids))
    c = manifest["counts"]
    assert c["assets"] == len(ids)
    assert sum(c["by_class"].values()) == len(ids)
    assert c["resolved_in_source"] == sum(1 for a in manifest["assets"]
                                         if a["resolution"] == "resolved_in_source")
    assert c["referenced_unresolved"] == sum(1 for a in manifest["assets"]
                                             if a["resolution"] == "referenced_unresolved")


def test_every_locator_has_verbatim_quote_and_span(manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["quote"].strip(), a["asset_id"]
        assert loc["end_char"] > loc["start_char"] >= 0, a["asset_id"]
        assert 1 <= loc["start_line"] <= loc["end_line"], a["asset_id"]
        if loc["method"] == "char_span":
            assert loc["unique"] is (loc["occurrences"] == 1), a["asset_id"]


def test_quotes_resolve_inside_archived_source_copy(manifest):
    """Offline resolution: the archived byte copy in runs/ must contain every quote at its span."""
    src = REPO / "runs" / "wp-8753-01" / ("source_%s.md" % REPORT_ID)
    md = src.read_text(encoding="utf-8")
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["quote"] in md, a["asset_id"]
        if loc["method"] == "char_span":
            assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]


def test_no_claim_marked_verified_and_claims_policy(manifest, envelope):
    assert envelope["claims"] == []
    assert all(c.get("status") != "verified" for c in manifest["claims"])
    assert manifest["claims_empty_reason"]


def test_each_asset_declares_resolution_evidence(manifest):
    for a in manifest["assets"]:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved", "declared_absent"}
        assert a["resolution_check"]["check"]
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent", "present"}


def test_figures_declared_count_matches_platform_record(manifest):
    assert manifest["counts"]["figures_declared"] == len(manifest["source"]["platform_figures"])
    fig_assets = [a for a in manifest["assets"] if a["asset_class"] == "figure_declared"]
    assert {a["label"] for a in fig_assets} == set(manifest["source"]["platform_figures"])


@pytest.mark.skipif(not os.environ.get("TENSOR_API_BASE"), reason="platform API not configured")
def test_live_source_hash_and_locators(manifest):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    login = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(login, timeout=30) as r:
        tok = json.load(r)["access_token"]
    req = urllib.request.Request(base + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=60) as r:
        rec = json.load(r)
    md = rec.get("data", rec)["markdown"]
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
    for a in manifest["assets"]:
        assert a["locator"]["quote"] in md, a["asset_id"]