"""Offline verification tests for work package wp-5949-01 (01-asset-registration).

These tests never touch the network: they re-check the delivered artifacts in this worktree.
The live-source re-fetch (hash binding to the platform) lives in
`scripts/kf/build_asset_manifest_5949.py verify`, whose output is committed as
docs/kf/wp-5949-01/verification.json.

Run: python3 -m pytest tests/test_kf_wp5949.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-5949-01"
MANIFEST = PKG_DIR / "asset_manifest.json"
RESULT = PKG_DIR / "kf_result.json"
REPORT = PKG_DIR / "report.md"
SCHEMA = REPO / "schemas" / "asset_manifest.v1.wp-5949-01.schema.json"

CONTRACT_HASH = "c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002"
CONTRACT_CHARS = 12605


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result():
    return json.loads(RESULT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source_md():
    """The report markdown is materialised locally next to the manifest by the builder."""
    p = PKG_DIR / "source_5949.md"
    return p.read_text(encoding="utf-8")


def test_outputs_exist():
    for p in (MANIFEST, RESULT, REPORT, SCHEMA):
        assert p.is_file(), p
    assert (PKG_DIR / "source_5949.md").is_file()


def test_schema_pass(manifest):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(manifest)


def test_package_identity(manifest, result):
    for doc in (manifest, result):
        assert doc["package_id"] == "wp-5949-01"
        assert doc["task_type"] == "01-asset-registration"
        assert doc["report_id"] == "5949"


def test_source_hash_and_chars_match_contract(manifest, source_md):
    digest = hashlib.sha256(source_md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert digest == manifest["source"]["hash"]
    assert manifest["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert len(source_md) == CONTRACT_CHARS == manifest["source"]["chars"]
    assert len(source_md.encode("utf-8")) == manifest["source"]["bytes_utf8"]
    assert manifest["integrity"]["hash_matches_contract"] is True
    assert manifest["integrity"]["chars_match_contract"] is True


def test_kf_result_hash_binds_to_source(result):
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert result["provenance"]["source_chars"] == CONTRACT_CHARS


def test_kf_result_output_digest_recomputes(result):
    out = result["outputs"]["asset_manifest.json"]
    raw = MANIFEST.read_bytes()
    assert out["sha256"] == hashlib.sha256(raw).hexdigest()
    assert out["bytes"] == len(raw)


def test_locators_are_verbatim_char_spans(manifest, source_md):
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] != "char_span":
            continue
        q = loc["quote"]
        if source_md[loc["start_char"]:loc["end_char"]] != q:
            bad.append((a["asset_id"], "span"))
        elif q not in source_md:
            bad.append((a["asset_id"], "substring"))
        elif not loc["unique"] and source_md.count(q) != 1:
            bad.append((a["asset_id"], "uniqueness_flag"))
    assert bad == []
    assert manifest["integrity"]["quotes_are_verbatim_substrings"] is True


def test_locators_stay_inside_source(manifest, source_md):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert 0 <= loc["start_char"] < loc["end_char"] <= len(source_md), a["asset_id"]


def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A\d{2}", i) for i in ids)
    assert ids == sorted(ids)


def test_claims_are_empty_or_evidenced_and_never_verified(manifest):
    claims = manifest["claims"]
    assert claims == [], "this package registers assets only; no extraction is performed"
    for c in claims:  # keeps the invariant honest if a future revision adds claims
        assert c.get("evidence_locator") or c.get("status")
        assert c.get("status") != "verified"


def test_resolution_vocabulary_and_counts(manifest):
    allowed = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
    assert {a["resolution"] for a in manifest["assets"]} <= allowed
    counts = manifest["counts"]
    assert counts["assets"] == len(manifest["assets"])
    for key in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert counts[key] == sum(1 for a in manifest["assets"] if a["resolution"] == key)
    assert sum(counts["by_class"].values()) == counts["assets"]
    assert sum(counts["by_resolution"].values()) == counts["assets"]


def test_scope_is_single_report(manifest, result):
    blob = json.dumps([manifest, result], ensure_ascii=False)
    assert set(re.findall(r"tensor://reports/(\d+)", blob)) == {"5949"}
    assert set(re.findall(r"report_id\"?:\s*\"?(\d+)", blob)) == {"5949"}


def test_declared_digests_are_marked_truncated(manifest):
    d = manifest["declared_digests"]
    assert d["count"] == len(d["items"]) == 7
    assert d["verifiable"] == 0
    for it in d["items"]:
        assert it["declared_hex_chars"] < 64 and it["truncated"] is True
        assert it["verifiable"] is False


def test_report_has_exactly_one_json_block_and_it_is_the_result():
    md = REPORT.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    assert len(blocks) == 1
    assert md.count("```json") == 1
    assert json.loads(blocks[0]) == json.loads(RESULT.read_text(encoding="utf-8"))
    assert "kf-wp:wp-5949-01" in md
    assert md.splitlines()[0].strip() == "# KF-RESULT wp-5949-01"


def test_report_sections_present():
    md = REPORT.read_text(encoding="utf-8")
    for marker in ("①", "②", "③", "④", "⑤", "⑥"):
        assert marker in md
    assert "repro_cmd" in md or "复跑" in md


def test_figure_artifact_exists():
    figs = sorted((PKG_DIR / "figures").glob("*.png"))
    assert figs, "expected the inventory figure to be rendered"
    for f in figs:
        raw = f.read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(raw) > 1000