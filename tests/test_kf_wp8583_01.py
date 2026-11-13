"""Invariants for work package wp-8583-01 (report 8583 asset registration).

Offline: every assertion runs against committed artefacts only (no network, no DB), so the
test pins the delivered bytes rather than the state of the platform at run time.

  * the registered source copy hashes to the contract value;
  * every locator quote is a verbatim, unique substring of that source copy, on the declared
    line, and every char span slices back to its quote;
  * ids are unique, every entry carries an explicit resolution status, unresolved entries
    carry a reason, and no claim is emitted (contract: no_forced_claim_generation);
  * the result envelope validates against schemas/kf_result.v1.schema.json and its
    provenance.source_hash equals both the contract hash and the manifest hash;
  * the KF-RESULT report contains exactly one json block, and that block is the envelope.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-8583-01"
SOURCE = ROOT / "runs" / "wp-8583-01" / "report_8583.md"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.wp-8583-01.json"
REPORT = PKG / "KF-RESULT-wp-8583-01.md"
CONTRACT_HASH = "2dae949f5c82c8f0e931f5280c0ea5c565bd188e05b0c109e49763d47a4fdfa4"
CONTRACT_CHARS = 4087
ALLOWED = {"resolved", "resolved_in_source", "resolved_in_worktree", "referenced_unresolved",
           "unresolved", "declared_absent", "metadata_only", "declared_only"}


@pytest.fixture(scope="module")
def source() -> str:
    assert SOURCE.exists(), "committed source copy missing: %s" % SOURCE
    return SOURCE.read_bytes().decode("utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


def test_source_copy_matches_contract(source):
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(source) == CONTRACT_CHARS


def test_every_locator_quote_is_verbatim_and_unique(source, manifest):
    lines = source.rstrip("\n").split("\n")
    spans = {a["asset_id"]: a["locator"] for a in manifest["assets"]
             if a["locator"].get("method") == "char_span"}
    assert len(manifest["locators"]) >= 30
    for loc in manifest["locators"]:
        if loc["asset_id"] in spans:
            sl = spans[loc["asset_id"]]
            quote = "\n".join(lines[sl["start_line"] - 1:sl["end_line"]])
        else:
            quote = lines[loc["line"] - 1]
        assert quote in source, loc["asset_id"]
        assert source.count(quote) == 1, "quote not unique: %s" % loc["asset_id"]
        assert hashlib.sha256(quote.encode("utf-8")).hexdigest() == loc["quote_sha256"]
        assert loc["resolved"] is True


def test_char_spans_slice_back_to_quotes(source, manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc.get("method") == "char_span":
            assert source[loc["char_start"]:loc["char_end"]] == loc["quote"], a["asset_id"]


def test_ids_unique_and_statuses_explicit(manifest):
    entries = (manifest["assets"] + manifest["references"] + manifest["regulation_references"])
    ids = [e["asset_id"] for e in entries]
    assert len(ids) == len(set(ids))
    for e in entries:
        st = e["resolution"]["status"]
        assert st in ALLOWED, "%s -> %r" % (e["asset_id"], st)
        if st in ("unresolved", "metadata_only"):
            assert e["resolution"].get("reason"), "missing reason: %s" % e["asset_id"]


def test_no_claims_are_emitted(manifest, envelope):
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert manifest["claims_empty_reason"]


def test_no_entry_is_marked_verified(manifest):
    blob = json.dumps(manifest, ensure_ascii=False)
    assert '"verified": true' not in blob
    assert '"status": "verified"' not in blob


def test_figures_registered_as_metadata_only(manifest):
    figs = [a for a in manifest["assets"] if a.get("kind") == "declared_figure"]
    assert len(figs) == manifest["counts"]["figures_declared_in_record"] == 6
    for f in figs:
        assert f["resolution"]["status"] == "metadata_only"
        assert "sha256" not in f


def test_envelope_schema_and_hash(envelope, manifest):
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    assert [e.message for e in Draft202012Validator(schema).iter_errors(envelope)] == []
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert manifest["source"]["sha256"] == CONTRACT_HASH
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    assert envelope["package_id"] == "wp-8583-01"
    assert envelope["report_id"] == "8583"


def test_report_has_single_json_block_equal_to_envelope(envelope):
    text = REPORT.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
    assert len(blocks) == 1, "expected exactly one json block, got %d" % len(blocks)
    assert json.loads(blocks[0]) == envelope
    assert text.split("\n")[0] == "# KF-RESULT wp-8583-01"
    for sec in ("①", "②", "③", "④", "⑤", "⑥"):
        assert sec in text
    assert "kf-wp:wp-8583-01" in text or "kf-wp:wp-8583-01" in json.dumps(envelope)