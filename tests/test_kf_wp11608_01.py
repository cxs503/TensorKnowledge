"""Acceptance tests for work package wp-11608-01 (asset registration on report 11608).

These tests assert invariants, not just execution: every locator quote is
re-resolved against the pinned markdown bytes, ids are unique, the envelope hash
equals the contract hash, and nothing is labelled verified.

Run: python3 -m pytest tests/test_kf_wp11608_01.py -q
Fixtures on disk (no network needed): runs/wp-11608-01/report_11608.md is the
byte-exact markdown fetched by scripts/kf_fetch_11608.py.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-11608-01"
SRC_MD = ROOT / "runs" / "wp-11608-01" / "report_11608.md"

CONTRACT_HASH = "8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62"
CONTRACT_CHARS = 7342
REPORT_ID = "11608"


@pytest.fixture(scope="module")
def md() -> str:
    return SRC_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf_result() -> dict:
    return json.loads((PKG / "kf_result.wp-11608-01.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- source hash
def test_source_hash_matches_contract(md):
    got = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert got == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_manifest_records_the_same_hash(manifest, md):
    assert manifest["source"]["hash"] == hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert manifest["integrity"]["hash_matches_contract"] is True
    assert manifest["integrity"]["hash_recomputed_locally"] == manifest["source"]["hash"]
    assert manifest["source"]["chars"] == len(md)
    assert manifest["source"]["bytes_utf8"] == len(md.encode("utf-8"))


# ---------------------------------------------------------------- schema pass
def test_kf_result_validates_against_platform_schema(kf_result):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(kf_result, schema)


def test_manifest_validates_against_pinned_schema(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((PKG / "asset_manifest.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_envelope_identity_fields(kf_result):
    assert kf_result["package_id"] == "wp-11608-01"
    assert kf_result["task_type"] == "01-asset-registration"
    assert kf_result["report_id"] == REPORT_ID
    assert kf_result["provenance"]["source_field"] == "markdown"
    assert kf_result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert list(kf_result["outputs"]) == ["asset_manifest.json"]


# ---------------------------------------------------------------- ids / counts
def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)


def test_counts_are_consistent(manifest):
    assets = manifest["assets"]
    c = manifest["counts"]
    assert c["assets"] == len(assets)
    by_res: dict[str, int] = {}
    by_cls: dict[str, int] = {}
    for a in assets:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
        by_cls[a["asset_class"]] = by_cls.get(a["asset_class"], 0) + 1
    assert by_res == c["by_resolution"]
    assert by_cls == c["by_class"]
    assert sum(by_res.values()) == c["assets"]
    for key in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert c[key] == by_res.get(key, 0)


# ------------------------------------------------- locator resolvability (核心)
def test_every_locator_resolves_verbatim(manifest, md):
    """Gate-safety: EVERY asset locator quote must be a unique verbatim markdown substring."""
    checked = 0
    for a in manifest["assets"]:
        q = a["locator"]["quote"]
        assert q in md, "quote not verbatim in markdown: %s" % a["asset_id"]
        start = a["locator"]["start_char"]
        end = a["locator"]["end_char"]
        assert md[start:end] == q, "char span mismatch for %s" % a["asset_id"]
        assert end - start == len(q)
        assert a["locator"]["start_line"] == md.count("\n", 0, start) + 1
        checked += 1
    assert checked == 25  # A01-A15, A16-A21 (anchor), A22-A25
    assert manifest["integrity"]["locator_quote_is_markdown_substring_for_all_assets"] is True


def test_quotes_are_unique(manifest, md):
    for a in manifest["assets"]:
        assert md.count(a["locator"]["quote"]) == 1, a["asset_id"]
        assert a["locator"]["unique"] is True


def test_declared_absent_assets_really_absent(manifest, md):
    absent = [a for a in manifest["assets"] if a["resolution"] == "declared_absent"]
    assert len(absent) == 6
    for a in absent:
        assert a["resolution_check"]["result"] == "absent"
        assert a["locator_source"] == "record"
        assert a["locator_semantics"] == "anchor_where_expected"
        # the DECLARED name is absent from the body ...
        assert a["record_name"] == a["label"]
        assert a["record_name"] not in md, a["asset_id"]
        # ... while the locator stays a real, resolvable markdown anchor
        assert md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]


def test_resolution_values_and_check_evidence_agree(manifest):
    for a in manifest["assets"]:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved", "declared_absent"}
        res, chk = a["resolution"], a["resolution_check"]["result"]
        pair_ok = {
            "resolved_in_source": {"resolved", "present"},
            "referenced_unresolved": {"unresolved"},
            "declared_absent": {"absent"},
        }
        assert chk in pair_ok[res], (a["asset_id"], res, chk)
        assert a["resolution_check"]["check"].strip()
        assert a["locator_semantics"] in {"verbatim_asset_reference", "anchor_where_expected"}


# ---------------------------------------------------------------- claims policy
def test_claims_empty_by_contract(manifest, kf_result):
    assert manifest["claims"] == []
    assert kf_result["claims"] == []
    assert "no_forced_claim_generation" in manifest["claims_note"]


def test_nothing_is_marked_verified(manifest, kf_result):
    """constraints.do_not_mark_claims_as_verified: no 'verified' status anywhere."""
    blob = json.dumps([manifest, kf_result], ensure_ascii=False)
    assert not re.search(r'"(status|resolution)"\s*:\s*"verified"', blob)
    gate = json.loads((PKG / "verification.json").read_text(encoding="utf-8"))["gate"]
    assert gate == "pending_platform_verification"
    decl = manifest["declared_verification_status"]
    assert decl["treated_as"] == "author_declaration_not_a_platform_verdict"
    assert decl["quote"] in SRC_MD.read_text(encoding="utf-8")


# ---------------------------------------------------------------- deliverables
def test_result_report_has_exactly_one_json_block(kf_result):
    md = (PKG / "KF-RESULT-wp-11608-01.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    assert len(blocks) == 1, "the result channel must be a single json block"
    assert json.loads(blocks[0]) == kf_result
    assert md.splitlines()[0].strip() == "# KF-RESULT wp-11608-01"


def test_report_mentions_tag_and_repro(kf_result):
    md = (PKG / "KF-RESULT-wp-11608-01.md").read_text(encoding="utf-8")
    assert "kf-wp:wp-11608-01" in md
    assert "python3 scripts/kf_fetch_11608.py" in md
    assert "python3 scripts/kf_wp11608_01_register.py" in md


def test_only_report_11608_is_touched(manifest):
    """边界: the package must not reach another report_id."""
    blob = json.dumps(manifest, ensure_ascii=False)
    ids = set(re.findall(r"tensor://reports/(\d+)", blob))
    assert ids == {REPORT_ID}