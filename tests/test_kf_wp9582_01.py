"""Acceptance gate for KF work package wp-9582-01 (report 9582, asset registration).

These tests re-derive every acceptance item from bytes on disk, so the manifest cannot
silently drift from the source it describes. They assert invariants (identity, resolvability,
uniqueness), not merely that the scripts ran.

Run:  pytest -q tests/test_kf_wp9582_01.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-9582-01"
SOURCE = ROOT / "runs" / "wp-9582-01" / "source_9582.md"
CONTRACT_HASH = "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f"
CONTRACT_CHARS = 11293


@pytest.fixture(scope="module")
def md() -> str:
    return SOURCE.read_bytes().decode("utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))


def test_source_hash_and_chars_match_contract(md):
    raw = SOURCE.read_bytes()
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_source_report_id_is_9582(manifest):
    assert manifest["report_id"] == "9582"
    assert manifest["source"]["uri"] == "tensor://reports/9582"
    assert manifest["source"]["field"] == "markdown"


def test_manifest_validates_against_pinned_schema(manifest):
    schema = json.loads((PKG / "asset_manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(manifest)


def test_envelope_validates_against_canonical_schema(envelope):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(envelope)


def test_envelope_wraps_the_same_manifest(envelope, manifest):
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["report_id"] == "9582"
    assert envelope["package_id"] == "wp-9582-01"


def test_every_locator_resolves_and_is_unique(md, manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "char_span":
            assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        else:
            assert (loc["start_char"], loc["end_char"]) == (0, len(md)), a["asset_id"]
        assert md.count(loc["quote"]) == 1, "%s: quote not unique" % a["asset_id"]
        assert md.count("\n", 0, loc["start_char"]) + 1 == loc["start_line"], a["asset_id"]
        assert loc["start_line"] <= loc["end_line"], a["asset_id"]


def test_asset_ids_unique_and_contiguous(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(set(ids)) == len(ids)
    assert ids == ["A%02d" % (i + 1) for i in range(len(ids))]


def test_counts_are_consistent_with_assets(manifest):
    c = manifest["counts"]
    assets = manifest["assets"]
    assert c["assets"] == len(assets)
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert c[res] == sum(1 for a in assets if a["resolution"] == res)
    for cls, n in c["by_class"].items():
        assert n == sum(1 for a in assets if a["asset_class"] == cls)


def test_figures_are_not_claimed_resolved_when_pixels_absent(manifest):
    """Honesty invariant: a figure whose png bytes are absent must not be resolved_in_source."""
    absent = {f["name"] for f in manifest["source"]["platform_figures"] if not f["png_bytes_present"]}
    for a in manifest["assets"]:
        if a["asset_class"] == "figure_reference" and a["label"].split("（")[0] in absent:
            assert a["resolution"] == "referenced_unresolved", a["asset_id"]


def test_claims_empty_or_evidenced(manifest):
    for c in manifest["claims"]:
        assert c.get("evidence_locator") or c.get("status") in (
            "supported", "partially-supported", "unresolved", "refuted")


def test_report_has_exactly_one_json_block_holding_the_envelope(manifest):
    body = (PKG / "KF-RESULT-wp-9582-01.md").read_text(encoding="utf-8")
    assert body.startswith("# KF-RESULT wp-9582-01")
    blocks = re.findall(r"```json\n(.*?)\n```", body, re.S)
    assert len(blocks) == 1
    env = json.loads(blocks[0])
    # the delivered block is the artifact itself, not a paraphrase of it
    assert env == json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    assert env["provenance"]["source_hash"] == "sha256:" + manifest["source"]["hash"]
    assert "kf-wp:wp-9582-01" in body


def test_rebuild_is_idempotent():
    """A rebuild must not re-stamp timestamps or otherwise move the delivered bytes."""
    before = {p.name: p.read_bytes() for p in PKG.glob("*") if p.is_file()}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "kf_wp9582_01_build.py")],
                   cwd=str(ROOT), check=True, capture_output=True)
    after = {p.name: p.read_bytes() for p in PKG.glob("*") if p.is_file()}
    changed = sorted(k for k in before if before[k] != after.get(k))
    assert not changed, "rebuild changed delivered bytes: %s" % changed


def test_report_does_not_self_certify_verification():
    """The contract forbids marking results verified; verification is platform-computed."""
    body = (PKG / "KF-RESULT-wp-9582-01.md").read_text(encoding="utf-8")
    assert "by platform" in body or "平台门" in body
    assert not re.search(r'"status"\s*:\s*"verified"', body)