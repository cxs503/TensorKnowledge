#!/usr/bin/env python3
"""Offline invariant tests for work package wp-9656-01 (01-asset-registration).

These assert invariants over the committed artifacts using the cached source copy
(runs/wp-9656-01/source_9656.md), so they run without platform credentials:

  pytest tests/test_kf_wp9656_01.py -q

What is asserted (all invariants, not just "the script ran"):
  * the cached source is byte-identical to the contract-declared markdown hash;
  * every locator quote is a verbatim slice of that source at the declared span,
    and every declared line quote is the actual line at that number;
  * asset ids are unique and follow the r9656:* scheme; counts agree with assets;
  * the kf_result envelope carries the contract hash and validates against
    schemas/kf_result.v1.schema.json;
  * nothing is marked `verified` and no claim was invented (claims == []).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-9656-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
VERIFICATION = PKG / "verification.json"
SOURCE = ROOT / "runs" / "wp-9656-01" / "source_9656.md"
KF_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
LOCAL_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.wp9656-01.schema.json"

CONTRACT_HASH = "04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619"
CONTRACT_CHARS = 12470


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_source_copy_matches_contract_hash(source):
    assert len(source) == CONTRACT_CHARS
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH


def test_manifest_identity(manifest):
    assert manifest["package_id"] == "wp-9656-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "9656"
    assert manifest["source"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert manifest["source"]["hash_matches_contract"] is True
    assert manifest["source"]["chars_matches_contract"] is True
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert manifest["source"]["bytes_utf8"] == len(
        SOURCE.read_bytes())  # same bytes as served (UTF-8)


def test_asset_ids_unique_and_scheme(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids, "at least the source asset must be registered"
    assert len(ids) == len(set(ids))
    assert all(i.startswith("r9656:") for i in ids)


def test_counts_agree_with_assets(manifest):
    c = manifest["counts"]
    assets = manifest["assets"]
    assert c["assets_total"] == len(assets)
    for status in ("resolved", "metadata_only", "unresolved"):
        assert c["assets_" + status] == sum(1 for a in assets if a["resolution"]["status"] == status)
    assert c["assets_total"] == c["assets_resolved"] + c["assets_metadata_only"] + c["assets_unresolved"]
    assert c["body_references"] == sum(1 for a in assets if a["kind"] != "report_markdown"
                                       and a["kind"] != "embedded_figure")
    assert sum(c["kind_status_histogram"].values()) == c["assets_total"]
    assert c["tables"] == len(manifest["tables"])
    assert c["claims"] == len(manifest["claims"]) == 0


def test_every_locator_is_verbatim(manifest, source):
    lines = source.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        assert quote and quote in source, a["asset_id"]
        if loc["method"] == "char_span":
            assert source[loc["start_char"]:loc["end_char"]] == quote, a["asset_id"]
            assert lines[loc["start_line"] - 1] == loc["line_quote"], a["asset_id"]
            assert loc["line_quote"].find(quote) >= 0, a["asset_id"]
        elif loc["method"] == "document":
            assert source[loc["start_char"]:loc["end_char"]] == quote == source[:len(quote)]
            assert loc["doc_chars"] == len(source)
        else:  # record_pointer
            assert loc["source_field"] == "record"
            assert loc["pointer"].startswith("/figures/")


def test_table_and_section_locators(manifest, source):
    assert manifest["tables"], "report body has markdown tables"
    for t in manifest["tables"]:
        assert t["header_quote"] in source, t["table_id"]
        assert t["rows"] >= 1 and t["cols"] >= 2
    for s in manifest["sections"]:
        assert s["line_heading"] in source


def test_no_verified_marks_and_no_invented_claims(manifest, envelope):
    assert manifest["claims"] == [] and envelope.get("claims") == []
    blob = json.dumps(manifest, ensure_ascii=False)
    assert '"verified"' not in blob
    for a in manifest["assets"]:
        assert a["resolution"]["status"] in ("resolved", "metadata_only", "unresolved")


def test_envelope_binds_source_hash(envelope, source):
    assert envelope["package_id"] == "wp-9656-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "9656"
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert "asset_manifest.json" in envelope["outputs"]
    embedded = envelope["outputs"]["asset_manifest.json"]
    assert embedded["package_id"] == envelope["package_id"]
    assert embedded["report_id"] == envelope["report_id"]


def test_envelope_validates_against_kf_result_schema(envelope):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(envelope, json.loads(KF_SCHEMA.read_text(encoding="utf-8")))
    jsonschema.validate(json.loads(MANIFEST.read_text(encoding="utf-8")),
                        json.loads(LOCAL_SCHEMA.read_text(encoding="utf-8")))


def test_verification_all_acceptance_checked_and_green():
    v = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    required = {
        "valid_json",
        "schema_pass",
        "source_locator_resolvable",
        "source_hash_matches",
        "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status",
    }
    assert required <= set(v["acceptance"])
    assert v["all_ok"] is True
    assert all(c["ok"] for c in v["acceptance"].values())
    assert v["accounting"]["locators_resolved"] == v["accounting"]["locators_checked"]


def test_envelope_is_not_stale(manifest, envelope):
    """verify() must not mutate the manifest after the envelope embeds it."""
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    digest = envelope["outputs"]["asset_manifest.digest.json"]["sha256"]
    assert digest == "sha256:" + hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    v = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    assert v["internal_consistency"]["ok"] is True


def test_report_body_has_single_json_block_at_root():
    """The delivered KF-RESULT markdown must carry exactly one ```json block."""
    cand = sorted(PKG.glob("KF-RESULT*.md"))
    assert cand, "KF-RESULT markdown missing"
    md = cand[0].read_text(encoding="utf-8")
    assert md.count("```json") == 1
    start = md.index("```json") + len("```json")
    end = md.index("```", start)
    payload = json.loads(md[start:end])
    committed = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    assert payload == committed
    # "原样提交": the block is the committed envelope, character for character
    # (modulo the file's single trailing newline)
    assert md[start:end].strip() == json.dumps(committed, ensure_ascii=False, indent=2).strip()
    assert md.lstrip().split("\n")[0].startswith("# KF-RESULT wp-9656-01")