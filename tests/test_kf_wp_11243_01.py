"""Offline invariants for KF package wp-11243-01 (asset registration, report 11243).

These assertions re-derive the acceptance items from artifacts on disk, so the
manifest cannot silently drift from the source snapshot or the contract.

Run: pytest -q tests/test_kf_wp_11243_01.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "knowledge" / "kf" / "wp-11243-01"
SNAPSHOT = PKG_DIR / "source_report_11243.md"
MANIFEST = json.loads((PKG_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
RESULT = json.loads((PKG_DIR / "result.json").read_text(encoding="utf-8"))
CONTRACT_HASH = "sha256:d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598"
CONTRACT_CHARS = 2701


@pytest.fixture(scope="module")
def source() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


def test_source_hash_and_length_match_contract(source):
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert "sha256:" + digest == CONTRACT_HASH
    assert MANIFEST["source"]["hash"] == digest
    assert len(source) == CONTRACT_CHARS == MANIFEST["source"]["chars"]


def test_every_markdown_quote_is_a_verbatim_unique_substring(source):
    checked = 0
    for asset in MANIFEST["assets"] + MANIFEST["unresolved_references"]:
        loc = asset["locator"]
        if loc["source_field"] != "markdown":
            continue
        assert loc["quote"] in source, asset["asset_id"]
        assert source.count(loc["quote"]) == 1, asset["asset_id"]
        if loc["method"] == "char_span":
            assert source[loc["start_char"]:loc["end_char"]] == loc["quote"]
            assert source.count("\n", 0, loc["start_char"]) == loc["start_line"]
        checked += 1
    # A01 + 7 markdown blocks; the 5 figure locators point at record fields instead
    assert checked == 8


def test_record_quotes_are_substrings_of_the_carried_summary():
    summary = MANIFEST["source"]["record_summary"]
    assert hashlib.sha256(summary["text"].encode("utf-8")).hexdigest() == summary["sha256"]
    for ref in MANIFEST["unresolved_references"]:
        assert ref["locator"]["source_field"] == "record"
        assert ref["locator"]["quote"] in summary["text"]


def test_record_quotes_are_flagged_unresolved_with_a_reason():
    for ref in MANIFEST["unresolved_references"]:
        assert ref["resolution"] == "referenced_unresolved"
        assert ref["resolution_check"]["result"] == "absent"
        assert ref["note"]


def test_ids_unique_and_figures_carried_with_hashes():
    ids = [a["asset_id"] for a in MANIFEST["assets"] + MANIFEST["unresolved_references"]]
    assert len(ids) == len(set(ids))
    figs = [a for a in MANIFEST["assets"] if a["asset_class"] == "figure_attachment"]
    assert len(figs) == MANIFEST["counts"]["figure_attachments_declared"] == 5
    for fig in figs:
        blob = (PKG_DIR / "figures" / f"{fig['label']}.png").read_bytes()
        assert hashlib.sha256(blob).hexdigest() == fig["sha256"]
        assert len(blob) == fig["resolution_check"]["bytes"]


def test_claims_empty_and_nothing_marked_verified():
    assert MANIFEST["claims"] == []
    assert RESULT["claims"] == []
    text = json.dumps(MANIFEST, ensure_ascii=False)
    assert '"status": "verified"' not in text
    assert '"verified": true' not in text


def test_envelope_validates_against_platform_schema():
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.validate(RESULT, schema)
    assert RESULT["provenance"]["source_hash"] == CONTRACT_HASH
    assert RESULT["report_id"] == "11243"
    assert RESULT["package_id"] == "wp-11243-01"
    assert RESULT["outputs"]["asset_manifest.json"] == MANIFEST


def test_manifest_validates_against_pinned_schema():
    schema = json.loads(
        (ROOT / "schemas" / "asset_manifest.v1.wp-11243-01.schema.json").read_text()
    )
    jsonschema.validate(MANIFEST, schema)


def test_integrity_checks_all_true():
    assert all(MANIFEST["integrity"]["checks"].values())
    assert MANIFEST["integrity"]["duplicate_ids"] == []


def test_table_structure_matches_block_content(source):
    tables = [a for a in MANIFEST["assets"] if a["asset_class"] == "data_table"]
    assert {t["label"] for t in tables} == {"Scaling Rule Table", "Failure Boundaries"}
    for table in tables:
        rows = [
            ln
            for ln in source[table["locator"]["start_char"]:table["locator"]["end_char"]].splitlines()
            if ln.strip().startswith("|")
        ]
        assert table["structure"]["pipe_rows_total"] == len(rows)
        assert table["structure"]["data_rows"] == len(rows) - 2