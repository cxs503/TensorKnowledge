"""Offline acceptance tests for KF work package wp-9645-01 (report_id=9645).

Deliberately independent of scripts/kf/wp_9645_01_register.py: the checks below
re-implement span/quote/hash verification from scratch so that a bug in the
builder cannot hide behind the same helper it used. No network access.
"""
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-9645-01"
SOURCE = PKG_DIR / "source.md"
MANIFEST = PKG_DIR / "asset_manifest.json"
RESULT = PKG_DIR / "kf_result.json"
LOCAL_SCHEMA = PKG_DIR / "asset_manifest.schema.json"
ENVELOPE_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"

EXPECTED_HASH = "a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00"
EXPECTED_CHARS = 11824


@pytest.fixture(scope="module")
def md():
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_source_hash_and_size(md):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
    assert len(md) == EXPECTED_CHARS


def test_envelope_schema(result):
    jsonschema.validate(result, json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8")))


def test_manifest_schema(manifest):
    jsonschema.validate(manifest, json.loads(LOCAL_SCHEMA.read_text(encoding="utf-8")))


def test_provenance_hash_matches_contract(result, md):
    live = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert result["provenance"]["source_hash"] == live
    assert result["provenance"]["source_field"] == "markdown"


def test_every_locator_resolves_verbatim_and_uniquely(manifest, md):
    assert manifest["assets"], "manifest must register at least one asset"
    for asset in manifest["assets"]:
        loc = asset["locator"]
        quote = loc["quote"]
        if loc["method"] == "document":
            assert loc["start_char"] == 0 and loc["end_char"] == len(md)
            assert md.startswith(quote)
            continue
        assert md[loc["start_char"]:loc["end_char"]] == quote, asset["asset_id"]
        assert md.count(quote) == 1, asset["asset_id"]
        assert loc["unique"] is True
        # line numbers must agree with the char span
        assert md[: loc["start_char"]].count("\n") + 1 == loc["start_line"], asset["asset_id"]
        assert md[: loc["end_char"] - 1].count("\n") + 1 == loc["end_line"], asset["asset_id"]
        assert hashlib.sha256(quote.encode("utf-8")).hexdigest() == loc["quote_sha256"]


def test_quote_spans_are_discriminating(manifest):
    spans = [(a["locator"]["start_char"], a["locator"]["end_char"]) for a in manifest["assets"]]
    doc_span = (0, max(s[1] for s in spans))
    dupes = {s for s in spans if spans.count(s) > 1 and s != doc_span}
    assert not dupes, "two assets sharing one locator span is a precision defect: %s" % dupes


def test_no_duplicate_ids(manifest, result):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == ["A%02d" % i for i in range(1, len(ids) + 1)]
    assert list(result["outputs"]) == ["asset_manifest.json"]


def test_outputs_carry_the_manifest(manifest, result):
    assert result["outputs"]["asset_manifest.json"] == manifest


def test_claims_empty_and_unverified(result):
    assert result["claims"] == []
    assert manifest_claims_ok(result)


def manifest_claims_ok(result):
    for claim in result.get("claims") or []:
        if not (claim.get("evidence") or claim.get("status")):
            return False
        if claim.get("verified"):
            return False
    return True


def test_resolution_accounting_is_consistent(manifest):
    counts = manifest["counts"]
    by_res = counts["by_resolution"]
    assert counts["assets"] == len(manifest["assets"]) == sum(by_res.values())
    assert counts["resolved_in_source"] == by_res.get("resolved_in_source", 0)
    assert counts["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
    assert counts["declared_absent"] == by_res.get("declared_absent", 0)


def test_reference_coverage_has_no_residue(manifest):
    cov = manifest["coverage"]
    assert cov["unregistered_inline_code_tokens"] == []
    assert cov["unregistered_markdown_images"] == []
    assert manifest["counts"]["markdown_images"] == manifest["counts"]["markdown_images_registered"]


def test_figures_are_declared_not_claimed(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure_reference"]
    assert len(figs) == 6
    for a in figs:
        assert a["resolution"] == "referenced_unresolved"
        assert a["resolution_check"]["result"] == "unresolved"
        assert a["resolution_check"]["detail"].startswith("record_entry_found=True")
        assert "payload_in_record=False" in a["resolution_check"]["detail"]
    assert manifest["source"]["platform_figures_payload_present"] is False


def test_declared_absent_matches_report_self_statement(manifest, md):
    absent = [a for a in manifest["assets"] if a["resolution"] == "declared_absent"]
    assert len(absent) == 1
    quote = absent[0]["locator"]["quote"]
    assert "不在工作树内" in quote
    assert quote in md


def test_scope_is_report_9645_only(manifest, result):
    assert manifest["report_id"] == result["report_id"] == "9645"
    assert manifest["source"]["uri"] == "tensor://reports/9645"
    assert result["package_id"] == "wp-9645-01"
    assert result["task_type"] == "01-asset-registration"
