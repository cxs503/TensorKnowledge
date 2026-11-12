"""Hermetic acceptance tests for KF work package wp-771-01 (report 771 asset registration).

No network: every assertion is re-derived from the committed package artifacts
(`{artifacts,docs}/kf/wp-771-01/{kf_result.json,asset_manifest.json,source_771.md}`).
The source copy is a byte-exact snapshot of report 771's markdown, so locator
resolution can be re-checked offline and independently of the platform.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
# Generation lands in artifacts/ (gitignored run area, dropped by the push gate);
# the committed canonical copy under docs/ is the one that survives a fresh checkout.
PKG = next(
    p
    for p in (ROOT / "artifacts" / "kf" / "wp-771-01", ROOT / "docs" / "kf" / "wp-771-01")
    if (p / "kf_result.json").exists()
)
REPORT_ID = "771"
EXPECTED_HASH = "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559"


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(envelope: dict) -> dict:
    return envelope["outputs"]["asset_manifest.json"]


@pytest.fixture(scope="module")
def source_text() -> str:
    return (PKG / "source_771.md").read_text(encoding="utf-8")


def test_envelope_matches_schema(envelope):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["package_id"] == "wp-771-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == REPORT_ID


def test_provenance_hash_matches_source_bytes(envelope, source_text):
    recomputed = "sha256:" + hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    assert envelope["provenance"]["source_hash"] == recomputed == EXPECTED_HASH
    assert envelope["provenance"]["source_field"] == "markdown"


def test_source_len_reported_consistently(manifest, source_text):
    assert manifest["source"]["chars"] == len(source_text)
    assert manifest["source"]["byte_length_utf8"] == len(source_text.encode("utf-8"))
    assert manifest["source"]["hash_check"]["match"] is True


def test_markdown_locators_resolve_verbatim(manifest, source_text):
    checked = 0
    for asset in manifest["assets"]:
        for loc in asset["locators"]:
            if loc["source_field"] != "markdown":
                continue
            span = source_text[loc["char_start"]:loc["char_end"]]
            assert span == loc["quote"], asset["asset_id"]
            assert loc["quote"] in source_text, asset["asset_id"]
            checked += 1
    assert checked >= 5, "expected several markdown locators"


def test_asset_ids_unique_and_every_asset_locatable(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    for asset in manifest["assets"]:
        assert asset["locators"], asset["asset_id"]
        if not asset["resolvable"]:
            assert asset.get("unresolved_reason"), asset["asset_id"]


def test_scope_is_single_report(manifest):
    assert manifest["scope"]["reports_touched"] == [REPORT_ID]
    blob = json.dumps(manifest, ensure_ascii=False)
    assert "tensor://reports/" not in blob.replace("tensor://reports/771", "")


def _walk(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def test_no_extraction_and_no_self_verification(envelope, manifest):
    assert envelope["claims"] == []
    assert manifest["claims_registered"] == 0
    assert manifest["extraction"]["performed"] is False
    assert manifest["verification"]["performed"] is False
    # no node may assert a verification outcome: no key/value named "verified"/true pair
    assert not [k for k, _ in _walk(manifest) if k == "verified"]
    assert not [v for _, v in _walk(manifest) if isinstance(v, str) and v.strip() == "verified"]
    assert not [v for _, v in _walk(manifest) if isinstance(v, str) and v.strip() == "pass"]


def test_locators_are_self_consistent_without_byte_offsets(manifest, source_text):
    """Offsets are code-point based, but the quote must resolve as a plain substring
    too, so a checker that ignores offsets still lands on the same text."""
    for asset in manifest["assets"]:
        for loc in asset["locators"]:
            if loc["source_field"] == "markdown":
                assert source_text.count(loc["quote"]) >= 1
                assert loc["char_end"] - loc["char_start"] == len(loc["quote"])


def test_declared_figures_are_registered_but_unresolved(manifest):
    figs = [a for a in manifest["assets"] if a["kind"] == "figure"]
    assert [f["name"] for f in figs] == [
        "fig1_beverloo_qbc.png",
        "fig2_beverloo_linearity.png",
        "fig3_rate_series.png",
    ]
    for fig in figs:
        assert fig["resolvable"] is False
        assert fig["status"] == "unresolved"
        assert fig["locators"][0]["field"].startswith("figures[")