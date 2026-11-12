"""Acceptance tests for KF work package wp-7808-01 (task_type 01-asset-registration).

These tests are offline: they read the byte-exact copy of the report markdown stored at
docs/kf/wp-7808-01/source_markdown.md (sha256 == the contract source_hash) together with
the committed outputs under docs/kf/wp-7808-01/. They assert the invariants the platform
gate checks, so a regression (edited quote, renumbered asset, drift in the hash) fails here
instead of at the gate.

Run: python3 -m pytest tests/test_kf_register_7808.py -q
"""
from __future__ import annotations

import hashlib
import json
import os

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "kf", "wp-7808-01")
SRC = os.path.join(OUT, "source_markdown.md")
CONTRACT = os.path.join(OUT, "work_package_contract.json")
MANIFEST_SCHEMA = os.path.join(OUT, "asset_manifest.schema.json")
ENVELOPE_SCHEMA = os.path.join(ROOT, "schemas", "kf_result.v1.schema.json")


@pytest.fixture(scope="module")
def md() -> str:
    with open(SRC, encoding="utf-8", newline="") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def contract() -> dict:
    return json.load(open(CONTRACT, encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.load(open(os.path.join(OUT, "asset_manifest.json"), encoding="utf-8"))


@pytest.fixture(scope="module")
def result() -> dict:
    return json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))


def test_source_hash_matches_contract(md, contract):
    """acceptance: source_hash_matches — contract hash, stored copy and provenance agree."""
    h = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert h == contract["input"]["source_hash"]
    assert len(md) == contract["input"]["chars"]
    res = json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))
    assert res["provenance"]["source_hash"] == h


def test_source_copy_provenance(md):
    """the offline copy must stay byte-identical to what was fetched."""
    prov = json.load(open(os.path.join(OUT, "source_markdown.provenance.json"), encoding="utf-8"))
    assert prov["sha256"] == "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert prov["chars"] == len(md)


def test_envelope_schema(result):
    jsonschema.validate(result, json.load(open(ENVELOPE_SCHEMA, encoding="utf-8")))


def test_manifest_schema(manifest):
    jsonschema.validate(manifest, json.load(open(MANIFEST_SCHEMA, encoding="utf-8")))


def test_quotes_resolve_verbatim(md, manifest):
    """acceptance: source_locator_resolvable — every quote is a real, unique char span."""
    assert manifest["assets"], "asset list must not be empty"
    for a in manifest["assets"]:
        loc = a["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) >= 1, a["asset_id"]
        assert loc["start_line"] == md.count("\n", 0, loc["start_char"]) + 1, a["asset_id"]
        assert loc["quote_sha256"] == "sha256:" + hashlib.sha256(
            loc["quote"].encode("utf-8")).hexdigest(), a["asset_id"]


def test_no_duplicate_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("A") and i[1:].isdigit() and len(i) == 3 for i in ids)
    assert manifest["id_integrity"]["duplicates"] == []


def test_claims_empty_and_never_verified(result, manifest):
    """acceptance: all_claims_have_evidence_or_explicit_unresolved_status (vacuous, claims==[])."""
    assert result["claims"] == []
    assert manifest["claims"] == []
    blob = json.dumps(result, ensure_ascii=False).lower()
    assert '"verified"' not in blob and "verified_true" not in blob


def test_body_path_token_coverage(md, manifest):
    """every file-like token in the body is attributable to some registered asset."""
    assert manifest["coverage"]["full_coverage"] is True
    assert manifest["coverage"]["unmapped_tokens"] == []
    assert manifest["coverage"]["distinct_tokens"] == len(manifest["coverage"]["tokens"])


def test_counts_consistent(manifest):
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    assert c["resolved_in_source"] + c["referenced_unresolved"] + c["declared_absent"] == c["assets"]
    assert sum(c["by_class"].values()) == c["assets"]
    assert len(manifest["unresolved"]) == c["referenced_unresolved"]


def test_report_scope_is_only_7808(manifest, result, contract):
    """hard boundary of the work package: one report id, nothing else."""
    assert contract["input"]["report_id"] == "7808"
    assert manifest["report_id"] == result["report_id"] == "7808"
    assert manifest["source"]["source_uri"] == "tensor://reports/7808"
    assert manifest["source"]["record_fields"]["title"] == contract["input"]["title"]
    assert manifest["source"]["record_fields"]["scenario_key"] == contract["input"]["scenario_key"]


def test_unresolved_entries_are_reasons_not_silence(manifest):
    for u in manifest["unresolved"]:
        assert u["reason"].strip(), u["asset_id"]
        assert any(a["asset_id"] == u["asset_id"] and a["resolution"] == "referenced_unresolved"
                   for a in manifest["assets"])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))