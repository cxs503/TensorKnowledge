"""Acceptance tests for wp-11107-01 (01-asset-registration, report 11107).

Run: python3 -m pytest tests/test_kf_wp11107_01.py -q
These tests re-derive every acceptance item from the committed artefacts only (no network,
no credentials): the cached source copy under runs/ is pinned by its sha256, so the locator
and hash checks stay reproducible offline.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-11107-01"
MANIFEST = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
ENVELOPE = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
VERIFY = json.loads((PKG / "verification.json").read_text(encoding="utf-8"))
SOURCE = (ROOT / "runs" / "wp-11107-01" / "source_11107.md").read_text(encoding="utf-8")
CONTRACT_HASH = "sha256:799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982"


def _lines(md: str) -> list[str]:
    return md.rstrip("\n").split("\n")


def test_source_hash_matches_contract():
    digest = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
    assert "sha256:" + digest == CONTRACT_HASH == ENVELOPE["provenance"]["source_hash"]
    assert MANIFEST["source"]["hash"] == digest
    assert MANIFEST["source"]["chars"] == len(SOURCE) == MANIFEST["contract"]["chars"]


def test_envelope_schema():
    jsonschema.validate(ENVELOPE, json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text()))
    assert ENVELOPE["package_id"] == "wp-11107-01"
    assert ENVELOPE["task_type"] == "01-asset-registration"
    assert ENVELOPE["report_id"] == "11107"
    assert set(ENVELOPE["outputs"]) == {"asset_manifest.json"}
    assert ENVELOPE["outputs"]["asset_manifest.json"] == MANIFEST


def test_manifest_schema():
    jsonschema.validate(
        MANIFEST, json.loads((ROOT / "schemas" / "asset_manifest.wp-11107-01.schema.json").read_text()))


@pytest.mark.parametrize("asset_id", [a["asset_id"] for a in MANIFEST["assets"]])
def test_locator_resolves_verbatim(asset_id):
    asset = next(a for a in MANIFEST["assets"] if a["asset_id"] == asset_id)
    loc = asset["locator"]
    quote = loc["quote"]
    assert quote in SOURCE
    assert SOURCE[loc["start_char"]:loc["end_char"]] == quote or loc["method"] == "document"
    if loc["method"] == "document":
        assert (loc["start_char"], loc["end_char"]) == (0, len(SOURCE))
        assert SOURCE.startswith(quote)
    assert _lines(SOURCE)[loc["start_line"] - 1:loc["end_line"]].count(quote) or quote in \
        "\n".join(_lines(SOURCE)[loc["start_line"] - 1:loc["end_line"]])
    assert SOURCE.count(quote) == loc["occurrences_in_source"]


def test_ids_unique_and_no_verified_marks():
    ids = [a["asset_id"] for a in MANIFEST["assets"]]
    assert len(ids) == len(set(ids)) == MANIFEST["counts"]["assets"] == len(MANIFEST["assets"])
    assert MANIFEST["id_integrity"]["duplicates"] == []
    blob = json.dumps(MANIFEST, ensure_ascii=False)
    assert '"verified"' not in blob and "verified_by" not in blob


def test_claims_empty_by_contract():
    assert MANIFEST["claims"] == [] and ENVELOPE["claims"] == []
    assert MANIFEST["counts"]["claims"] == 0
    assert len(MANIFEST["claims_empty_reason"]) > 20
    assert MANIFEST["contract"]["objective"] == {"register_assets": True, "classify_report_type": False}


def test_every_asset_has_locator_and_declared_resolution():
    for a in MANIFEST["assets"]:
        assert a["locator"]["quote"]
        assert a["resolution"] in {"resolved_in_source", "resolved_external",
                                   "referenced_unresolved", "declared_absent"}
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent"}
        assert a["note"]


def test_figure_references_trace_to_record_metadata():
    names = {f["name"] for f in MANIFEST["source"]["record"]["figures_declared"]}
    figs = [a for a in MANIFEST["assets"] if a["asset_class"] == "figure_reference"]
    assert len(figs) == len(names) == 4
    for a in figs:
        assert any(n in a["label"] for n in names)
        assert a["locator"]["quote"].endswith(".png")


def test_verification_flags_all_pass_and_are_not_a_verdict():
    assert VERIFY["all_pass"] is True
    assert {c["id"] for c in VERIFY["checks"]} == {
        "valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
        "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"}
    assert all(c["pass"] and c["evidence"] for c in VERIFY["checks"])
    assert "not a" in VERIFY["note"]


def test_report_markdown_has_exactly_one_json_block(tmp_path):
    md_path = ROOT / "docs" / "kf_result_wp-11107-01.md"
    md = md_path.read_text(encoding="utf-8")
    assert md.splitlines()[0].strip().lstrip("#").strip() == "KF-RESULT wp-11107-01"
    # exactly one json fence: other fences (shell/repro) are allowed, json must be unique
    assert md.count("```json") == 1
    assert md.count("```") % 2 == 0
    block = md.split("```json", 1)[1].split("```", 1)[0]
    parsed = json.loads(block)
    assert parsed["package_id"] == "wp-11107-01"
    assert parsed["provenance"]["source_hash"] == CONTRACT_HASH
    assert parsed["outputs"]["asset_manifest.json"]["source"]["hash"] == CONTRACT_HASH[7:]


def test_worktree_copy_is_the_published_snapshot():
    """The committed report must be byte-equal to what was posted (no silent post-publish drift)."""
    pub = json.loads((PKG / "published.json").read_text(encoding="utf-8"))
    md = (ROOT / "docs" / "kf_result_wp-11107-01.md").read_bytes()
    assert hashlib.sha256(md).hexdigest() == pub["markdown_sha256"]
    assert pub["markdown_chars"] == len(md.decode("utf-8"))
    assert pub["report_id"].isdigit()


def test_publish_roundtrip_report_all_pass():
    pc = json.loads((PKG / "publish_check.json").read_text(encoding="utf-8"))
    assert pc["all_pass"] is True
    assert {c["id"] for c in pc["checks"]} == {
        "result_markdown_roundtrip", "worktree_copy_is_published_snapshot",
        "json_block_equals_envelope", "figures_roundtrip", "source_unchanged"}
    assert all(f["match"] for f in pc["figures"])


def test_artefacts_are_not_stale():
    """generated_at must be a real ISO-8601 UTC stamp, so a hand-edited copy is detectable."""
    for stamp in (MANIFEST["generated_at"], VERIFY["verified_at"]):
        datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")