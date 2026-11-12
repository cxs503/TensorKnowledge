"""Acceptance tests for KF work package wp-1561-01 (task 01-asset-registration).

These tests do not re-derive the report's science. They assert exactly the contract's
acceptance list for an asset-registration工序:

  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

plus the包-specific boundaries: only report 1561 is touched, nothing is stamped verified,
and every non-resolved asset carries an explicit unresolved status instead of silence.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import kf_wp1561_01_asset_manifest as kf  # noqa: E402

OUT = os.path.join(ROOT, "docs", "kf", "wp-1561-01")
SOURCE = os.path.join(OUT, "source", "report_1561.md")
CONTRACT_HASH = "sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620"


def _load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def markdown() -> str:
    with open(SOURCE, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def manifest():
    return _load("asset_manifest.json")


@pytest.fixture(scope="module")
def result():
    return _load("kf_result.json")


@pytest.fixture(scope="module")
def record():
    return _load("report_record.json")


# --------------------------------------------------------------- schema / json
def test_outputs_are_valid_json_on_disk():
    for name in ("asset_manifest.json", "kf_result.json", "figure_fetch.json", "report_record.json"):
        _load(name)  # raises on malformed JSON


def test_envelope_passes_declared_schema(result):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.load(open(kf.ENVELOPE_SCHEMA, encoding="utf-8"))
    jsonschema.validate(result, schema)


def test_envelope_identity_fields(result):
    assert result["package_id"] == "wp-1561-01"
    assert result["task_type"] == "01-asset-registration"
    assert result["report_id"] == "1561"
    assert result["provenance"]["source_field"] == "markdown"
    assert "asset_manifest.json" in result["outputs"]


def test_embedded_manifest_equals_file(result, manifest):
    assert result["outputs"]["asset_manifest.json"] == manifest


# ------------------------------------------------------------------ hash pinning
def test_source_hash_matches_contract_and_snapshot(result, manifest, markdown):
    computed = "sha256:" + hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    assert computed == CONTRACT_HASH
    assert result["provenance"]["source_hash"] == CONTRACT_HASH
    assert manifest["report"]["source_hash"] == CONTRACT_HASH
    assert manifest["report"]["source_hash_matches_contract"] is True


def test_source_size_and_title_pinned(manifest, markdown):
    assert manifest["report"]["utf8_bytes"] == len(markdown.encode("utf-8"))
    assert manifest["report"]["characters"] == len(markdown)
    assert manifest["report"]["title_matches_contract"] is True


# ------------------------------------------------------------------- id hygiene
def test_no_duplicate_ids_and_pattern(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids)
    for aid in ids:
        assert aid.startswith("1561-a")
        assert len(aid) == len("1561-a000")


def test_only_report_1561_is_touched(manifest):
    assert manifest["report"]["report_id"] == "1561"
    assert manifest["report"]["source_uri"] == "tensor://reports/1561"
    for asset in manifest["assets"]:
        assert asset["asset_id"].startswith("1561-")
        assert "reports/1561" in asset["locator"]["anchor"]


# -------------------------------------------------------------- locator quality
def test_every_quote_is_verbatim_and_line_locator_resolves(manifest, markdown):
    lines = markdown.split("\n")
    for asset in manifest["assets"]:
        quote = asset["quote"]
        assert quote and quote in markdown, asset["asset_id"]
        assert asset["quote_verbatim_in_markdown"] is True, asset["asset_id"]
        loc = asset["locator"]
        ln = loc.get("line") or loc.get("markdown_reference_line")
        assert isinstance(ln, int) and 1 <= ln <= len(lines), asset["asset_id"]
        start, end = (loc.get("line_range") or [ln, ln])[:2]
        span = "\n".join(lines[start - 1 : end])
        assert quote in span, f"{asset['asset_id']} quote not on stated lines {start}-{end}"


def test_line_numbers_are_tight_not_smeared(manifest, markdown):
    """A locator must point at the quote, not at an arbitrary earlier line."""
    lines = markdown.split("\n")
    for asset in manifest["assets"]:
        if "\n" in asset["quote"]:
            continue
        loc = asset["locator"]
        ln = loc.get("line") or loc.get("markdown_reference_line")
        assert asset["quote"] in lines[ln - 1]


def test_kinds_are_known_and_counted(manifest):
    kinds = {}
    for asset in manifest["assets"]:
        kinds[asset["kind"]] = kinds.get(asset["kind"], 0) + 1
    assert manifest["counts"]["total"] == len(manifest["assets"])
    assert manifest["counts"]["by_kind"] == dict(sorted(kinds.items()))
    assert set(kinds) <= {
        "report_document", "section", "code_block", "table", "figure", "api_endpoint",
        "code_path", "test_path", "artifact_path", "command", "run_output_token",
        "citation_reference", "report_cross_reference", "api_contract_field_list",
        "gate_predicate",
    }


def test_required_kinds_present(manifest):
    kinds = {a["kind"] for a in manifest["assets"]}
    # a 01 package on a report with 6 sections / 3 tables / 3 fences / 5 figures must index them
    for required in ("report_document", "section", "table", "code_block", "figure"):
        assert required in kinds


# ------------------------------------------------------- claims / verification
def test_claims_empty_by_contract(manifest, result):
    assert manifest["claims"] == []
    assert result["claims"] == []
    assert manifest["counts"]["claims_registered"] == 0
    assert "no_forced_claim_generation" in manifest["claims_note"]


def test_nothing_is_stamped_verified(manifest, result):
    for claim in manifest["claims"] + result["claims"]:
        assert claim["status"] not in ("verified", "verified-strong")
        assert claim.get("status") in ("supported", "partially-supported", "unresolved", "refuted")
    assert "no verification stamp" in manifest["report"]["registration_scope"]


def test_every_unresolved_item_states_why(manifest):
    for asset in manifest["assets"]:
        if asset["resolvability"] in ("resolved_in_markdown", "resolved_in_markdown_and_served_by_api"):
            continue
        explained = (
            asset.get("note")
            or asset.get("binary_probe")
            or asset["kind"]
            in (
                "code_path", "test_path", "artifact_path", "command",
                "citation_reference", "report_cross_reference", "gate_predicate", "api_endpoint",
            )
        )
        assert explained, asset["asset_id"]
    for obs in manifest["observations"]:
        assert obs["assigned_status"] == "unresolved"
        assert obs["unresolved_reason"].strip()


# ----------------------------------------------------------------- figure probes
def record_caption_text(record, name):
    for fig in record["figures"]:
        if fig["name"] == name:
            return fig["caption"]
    return ""


def test_all_declared_figures_registered_with_probe(manifest, record):
    declared = [f["name"] for f in record["figures"]]
    registered = [a for a in manifest["assets"] if a["kind"] == "figure"]
    assert sorted(declared) == sorted(a["locator"]["name"] for a in registered)
    for asset in registered:
        probe = asset["binary_probe"]
        assert probe["method"] == "GET"
        assert probe["http_status"] == 404
        assert probe["resolvable"] is False
        assert asset["resolvability"] == "declared_and_markdown_referenced_binary_not_served"
        assert asset["record_caption"] in record_caption_text(record, asset["locator"]["name"])


def test_figure_names_really_appear_in_markdown(manifest, markdown):
    for asset in manifest["assets"]:
        if asset["kind"] == "figure":
            assert asset["locator"]["name"] in markdown


# ------------------------------------------------------------------- verify API
def test_verify_function_passes(manifest, markdown, record):
    checks = kf.verify_manifest(manifest, markdown, record)
    failed = {k: v for k, v in checks.items() if not v["ok"]}
    assert not failed, failed


def test_verify_detects_tampering(manifest, markdown, record):
    """Negative control: the verifier must fail on a mutated quote and on a bad hash."""
    import copy

    bad = copy.deepcopy(manifest)
    bad["assets"][1]["quote"] = bad["assets"][1]["quote"] + "（篡改）"
    checks = kf.verify_manifest(bad, markdown, record)
    assert not checks["source_locator_resolvable"]["ok"]

    bad2 = copy.deepcopy(manifest)
    bad2["report"]["source_hash"] = "sha256:" + "0" * 64
    checks2 = kf.verify_manifest(bad2, markdown, record)
    assert not checks2["source_hash_matches_contract"]["ok"]

    bad3 = copy.deepcopy(manifest)
    bad3["assets"].append(copy.deepcopy(bad3["assets"][1]))
    checks3 = kf.verify_manifest(bad3, markdown, record)
    assert not checks3["no_duplicate_ids"]["ok"]

def test_regeneration_is_deterministic(manifest, markdown, record):
    """Re-running the inventory over the same bytes must reproduce the committed assets."""
    figfetch = kf.load_json(kf.FIGFETCH, {})
    regen = kf.build_manifest(markdown, record, figfetch, manifest["generated_at"])
    assert regen["assets"] == manifest["assets"]
    assert regen["observations"] == manifest["observations"]
    assert regen["counts"] == manifest["counts"]
    assert regen["report"]["source_hash"] == manifest["report"]["source_hash"]


def test_package_touches_only_report_1561(manifest, result, markdown):
    """Boundary: no other report_id may appear as the subject of this package."""
    assert result["report_id"] == "1561" == manifest["report"]["report_id"]
    for blob in (json.dumps(result["provenance"], ensure_ascii=False),
                 json.dumps(manifest["report"]["source_uri"], ensure_ascii=False)):
        assert "reports/1561" in blob
    # cross references to other missions are inventory entries only, never subjects
    for asset in manifest["assets"]:
        if asset["kind"] == "report_cross_reference":
            assert asset["resolvability"] == "named_no_locator"
