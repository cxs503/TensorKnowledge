"""Offline contract tests for KF work package wp-6184-01 (01-asset-registration).

These tests re-check the *delivered artifacts* (not the build code path):
  docs/kf/wp-6184-01/asset_manifest.json
  docs/kf/wp-6184-01/kf_result.json
  docs/kf/wp-6184-01/KF-RESULT_wp-6184-01.md
against the pinned source snapshot / platform record, so a broken locator or a drifted
hash fails here without network access.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WP = REPO / "docs" / "kf" / "wp-6184-01"
MANIFEST = json.loads((WP / "asset_manifest.json").read_text(encoding="utf-8"))
RESULT = json.loads((WP / "kf_result.json").read_text(encoding="utf-8"))
VERDICT = json.loads((WP / "verification.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((WP / "asset_manifest.schema.json").read_text(encoding="utf-8"))
SOURCE = (WP / "source_snapshot.md").read_text(encoding="utf-8")

CONTRACT_HASH = "f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c"
CONTRACT_CHARS = 2406


def test_source_hash_and_chars_match_contract():
    assert hashlib.sha256(SOURCE.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(SOURCE) == CONTRACT_CHARS
    assert MANIFEST["source"]["hash"] == CONTRACT_HASH
    assert MANIFEST["source"]["chars"] == CONTRACT_CHARS
    assert RESULT["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH


def test_manifest_validates_against_local_schema():
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(MANIFEST, SCHEMA)


def test_scope_is_report_6184_only():
    assert MANIFEST["report_id"] == "6184"
    assert RESULT["report_id"] == "6184"
    assert MANIFEST["source"]["uri"] == "tensor://reports/6184"
    # only the one report id may appear as a report reference in the deliverables
    ids = set(re.findall(r"tensor://reports/(\d+)", json.dumps(MANIFEST, ensure_ascii=False)))
    assert ids == {"6184"}


def test_every_locator_resolves_to_its_quote_and_is_unique():
    for a in MANIFEST["assets"]:
        loc = a["locator"]
        assert SOURCE[loc["start_char"]: loc["end_char"]] == loc["quote"], a["asset_id"]
        assert SOURCE.count(loc["quote"]) == 1, a["asset_id"]
        assert loc["unique"] is True
        # reported line numbers must point at the span
        assert SOURCE[: loc["start_char"]].count("\n") + 1 == loc["start_line"], a["asset_id"]


def test_asset_ids_unique_and_counts_consistent():
    ids = [a["asset_id"] for a in MANIFEST["assets"]]
    assert len(ids) == len(set(ids))
    assert MANIFEST["counts"]["assets"] == len(ids) == sum(MANIFEST["counts"]["by_resolution"].values())
    assert sum(MANIFEST["counts"]["by_class"].values()) == len(ids)


def test_claims_are_empty_or_evidenced():
    for c in MANIFEST["claims"]:
        assert c.get("evidence_locator") or c.get("status")
    # this package declares register_assets only -> no extraction, so no claims
    assert MANIFEST["claims"] == []
    assert RESULT["claims"] == []


def test_nothing_marked_verified():
    blob = json.dumps(MANIFEST, ensure_ascii=False) + json.dumps(RESULT, ensure_ascii=False)
    assert '"verified": true' not in blob
    assert '"status": "verified"' not in blob


def test_resolution_status_is_honest_about_unavailable_bytes():
    """Codes/JSON/figure assets cannot be fetched (attachment endpoints 404) -> not 'resolved'."""
    probes = MANIFEST["source"]["platform_attachment_probes"]
    assert probes, "attachment probes must be recorded"
    assert all(p.get("http_status", 404) != 200 for p in probes.values())
    for a in MANIFEST["assets"]:
        if a["asset_class"] in {"code_pointer", "code_module", "artifact_file", "figure"}:
            assert a["resolution"] == "referenced_unresolved", a["asset_id"]


def test_kf_result_envelope_shape():
    assert RESULT["package_id"] == "wp-6184-01"
    assert RESULT["task_type"] == "01-asset-registration"
    assert RESULT["provenance"]["source_field"] == "markdown"
    assert "asset_manifest.json" in RESULT["outputs"]
    assert RESULT["outputs"]["asset_manifest.json"]["package_id"] == "wp-6184-01"


def test_report_body_has_exactly_one_json_block_and_it_is_the_envelope():
    md = (WP / "KF-RESULT_wp-6184-01.md").read_text(encoding="utf-8")
    assert md.count("```json") == 1
    assert md.lstrip().startswith("# KF-RESULT wp-6184-01")
    block = json.loads(md.split("```json", 1)[1].rsplit("```", 1)[0])
    assert block["package_id"] == RESULT["package_id"]
    assert block["provenance"]["source_hash"] == RESULT["provenance"]["source_hash"]


def test_verification_all_pass():
    assert VERDICT["all_pass"] is True
    assert {c["check"] for c in VERDICT["acceptance"]} >= {
        "valid_json",
        "schema_pass",
        "source_locator_resolvable",
        "source_hash_matches",
        "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status",
    }