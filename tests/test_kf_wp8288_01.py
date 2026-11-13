"""wp-8288-01 (01-asset-registration) — independent re-checks of the committed artifacts.

No network: everything is recomputed from the byte-exact local copy of the source
markdown (docs/kf/wp-8288-01/source.md) and the committed JSON artifacts.

Run: python3 -m pytest tests/test_kf_wp8288_01.py -q
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "kf" / "wp-8288-01"
SOURCE = OUT / "source.md"
MANIFEST = OUT / "asset_manifest.json"
LOCAL_SCHEMA = OUT / "asset_manifest.schema.json"
RESULT = OUT / "kf_result.json"
ENVELOPE_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"

CONTRACT_HASH = "2c35fbe3fa027f083b82f15238f3db797f087df0c435a1c536b176280e053f19"
CONTRACT_CHARS = 9660


@pytest.fixture(scope="module")
def md() -> str:
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_source_copy_is_byte_exact(md):
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert raw == md.encode("utf-8")
    assert len(md) == CONTRACT_CHARS


def test_manifest_declares_the_same_source(manifest):
    assert manifest["schema"] == "asset_manifest.v1"
    assert manifest["package_id"] == "wp-8288-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "8288"
    assert manifest["source"]["uri"] == "tensor://reports/8288"
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert manifest["integrity"]["hash_matches_contract"] is True


def test_every_locator_quote_is_reproducible_from_the_source(manifest, md):
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            # document-level locator: the span is the whole markdown, the quote pins its head
            assert (loc["start_char"], loc["end_char"]) == (0, len(md)), a["asset_id"]
            assert loc["quote"] in md, a["asset_id"]
        else:
            assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert loc["quote"].strip(), a["asset_id"]
        assert md.count(loc["quote"]) == 1, a["asset_id"]
        assert loc["unique"] is True, a["asset_id"]


def test_line_numbers_agree_with_char_spans(manifest, md):
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] != "char_span":
            continue
        first_line = md[: loc["start_char"]].count("\n") + 1
        assert first_line == loc["start_line"], a["asset_id"]


def test_no_duplicate_or_malformed_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids)
    assert all(len(i) == 3 and i[0] == "A" and i[1:].isdigit() for i in ids)


def test_resolution_states_are_consistent(manifest):
    pairs = {
        "resolved_in_source": {"resolved", "present"},
        "referenced_unresolved": {"unresolved"},
        "declared_absent": {"absent"},
    }
    for a in manifest["assets"]:
        assert a["resolution"] in pairs, a["asset_id"]
        assert a["resolution_check"]["result"] in pairs[a["resolution"]], a["asset_id"]


def test_counts_match_assets(manifest):
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    assert sum(c["by_class"].values()) == c["assets"]
    assert sum(c["by_resolution"].values()) == c["assets"]
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert c[res] == c["by_resolution"].get(res, 0)


def test_claims_are_empty_but_explained(manifest):
    assert manifest["claims"] == []
    assert manifest["claims_empty_reason"].strip()


def test_manifest_validates_against_projected_schema(manifest):
    jsonschema.validate(manifest, json.loads(LOCAL_SCHEMA.read_text(encoding="utf-8")))


def test_result_envelope_validates_against_platform_schema():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    jsonschema.validate(result, json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8")))
    assert result["package_id"] == "wp-8288-01"
    assert result["task_type"] == "01-asset-registration"
    assert result["report_id"] == "8288"
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert result["provenance"]["source_field"] == "markdown"
    assert "asset_manifest.json" in result["outputs"]
    assert result["outputs"]["asset_manifest.json"] == json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_result_carries_no_verified_marks():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert all(c.get("status") != "verified" for c in result.get("claims", []))
    # the only 'verified' strings allowed are the manifest's own boolean provenance flags
    blob = json.dumps(result["outputs"]["asset_manifest.json"])
    assert blob.count('"verified"') == 0
    assert '"verified' not in blob.replace('"verification"', '"verificationX"').replace(
        '"verification.json"', '"verificationX.json"')


def test_scope_guard_only_report_8288_is_referenced():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    blob = json.dumps(manifest)
    for other in ("tensor://reports/542", "tensor://reports/623", "tensor://reports/1610",
                  "tensor://reports/448"):
        assert other not in blob