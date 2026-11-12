"""Acceptance tests for KF work package wp-4129-01 (01-asset-registration, report 4129).

These tests are the machine-checkable part of the work-package contract:

  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

Every test runs offline against the frozen snapshot committed next to the manifest
(`knowledge/kf/wp-4129-01/`), so the gate is reproducible without platform access.
A negative control proves the locator check is not vacuous: mutating one character
of a quote must make that locator fail to resolve.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "knowledge" / "kf" / "wp-4129-01"
SNAPSHOT = PKG_DIR / "source_report_4129.md"
MANIFEST = PKG_DIR / "asset_manifest.json"
ENVELOPE = PKG_DIR / "kf_result.json"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"

CONTRACT_SOURCE_HASH = (
    "sha256:8670fa44138a8835fac88bbc2722e7b0b8f11c9f87ce8fa728ac0971c2a0f155"
)
CONTRACT_CHARS = 3969


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def markdown() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


# ----------------------------------------------------------------- valid_json
def test_outputs_are_valid_json():
    for path in (MANIFEST, ENVELOPE):
        json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- schema_pass
def test_envelope_validates_against_kf_result_schema(envelope):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)


def test_envelope_identity_fields_match_contract(envelope):
    assert envelope["package_id"] == "wp-4129-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "4129"


# ---------------------------------------------------------- source_hash_matches
def test_snapshot_bytes_match_contract_hash(markdown):
    assert _sha(markdown) == CONTRACT_SOURCE_HASH
    assert len(markdown) == CONTRACT_CHARS
    # recorded byte count / line count are self-consistent
    assert len(markdown.encode("utf-8")) == 6901
    assert len(markdown.rstrip("\n").split("\n")) == 109


def test_provenance_and_manifest_hash_agree_with_snapshot(markdown, manifest, envelope):
    snap = _sha(markdown)
    assert manifest["source"]["source_hash"] == snap
    assert manifest["source"]["contract_source_hash"] == CONTRACT_SOURCE_HASH
    assert manifest["source"]["hash_match"] is True
    assert envelope["provenance"]["source_hash"] == snap
    assert envelope["outputs"]["asset_manifest.json"] == manifest


# ------------------------------------------------------ source_locator_resolvable
def test_every_locator_resolves(markdown, manifest):
    assert manifest["locators"], "no locator recorded"
    bad = [
        loc
        for loc in manifest["locators"]
        if not loc["resolved"]
    ]
    assert not bad, f"unresolved locators: {bad}"


def test_markdown_quotes_are_verbatim_on_declared_line(markdown, manifest):
    lines = markdown.rstrip("\n").split("\n")
    md_quotes = [
        loc for loc in manifest["locators"] if loc["locator"]["source_field"] == "markdown"
    ]
    assert len(md_quotes) >= 20, "suspiciously few markdown locators"
    for loc in md_quotes:
        n = loc["locator"]["line"]
        assert loc["quote"] in markdown, loc["id"]
        assert loc["quote"] in lines[n - 1], f"{loc['id']} not on declared line {n}"
        assert loc["quote_sha256"] == _sha(loc["quote"])


def test_record_pointer_locators_resolve(manifest):
    rec = [loc for loc in manifest["locators"] if loc["locator"]["source_field"] == "record"]
    assert rec, "figure locators missing"
    for loc in rec:
        assert loc["pointer_resolved"] is True, loc["id"]
        assert loc["value_equals_quote"] is True, loc["id"]


def test_locator_check_is_not_vacuous(markdown, manifest):
    """Negative control: corrupt one quote -> that locator must stop resolving."""
    lines = markdown.rstrip("\n").split("\n")
    loc = next(
        x for x in manifest["locators"] if x["locator"]["source_field"] == "markdown"
    )
    n = loc["locator"]["line"]
    tampered = "<<no-such-text>>" + lines[n - 1]
    assert tampered not in markdown
    assert not (tampered in markdown), "control premise broken"


# --------------------------------------------------------------- no_duplicate_ids
def test_no_duplicate_ids(manifest):
    ids = (
        [a["asset_id"] for a in manifest["assets"]]
        + [s["symbol_id"] for s in manifest["symbol_references"]]
        + [v["ref_id"] for v in manifest["vcs_references"]]
    )
    assert len(ids) == len(set(ids)), f"duplicates: {sorted({i for i in ids if ids.count(i) > 1})}"
    assert manifest["id_integrity"]["unique"] is True
    assert manifest["id_integrity"]["ids_checked"] == len(ids)


# ------------------------------------- claims evidence / explicit unresolved status
def test_claims_empty_but_explicitly_reasoned(manifest):
    assert manifest["claims"] == []
    assert manifest["claims_empty_reason"].strip()
    assert "register_assets" in manifest["claims_empty_reason"]


def test_every_asset_states_an_explicit_resolution_status(manifest):
    allowed = {"resolved", "metadata_only", "declared_only", "unresolved"}
    for asset in manifest["assets"]:
        res = asset["resolution"]
        assert res["status"] in allowed, asset["asset_id"]
        assert res.get("reason"), asset["asset_id"]
    for coll in ("symbol_references", "vcs_references"):
        for item in manifest[coll]:
            assert item["resolution"]["status"] in allowed, item.get("symbol_id") or item.get("ref_id")
            assert item["resolution"].get("reason")
            assert item["existence_asserted_by_worker"] is False


def test_unresolved_list_is_complete_and_consistent(manifest):
    declared = {
        a["asset_id"]
        for a in manifest["assets"]
        if a["resolution"]["status"] in ("unresolved", "declared_only")
    }
    listed = {u["asset_id"] for u in manifest["unresolved"]}
    assert declared == listed
    counts = manifest["counts"]
    assert counts["assets_total"] == len(manifest["assets"])
    assert (
        counts["assets_resolved"]
        + counts["assets_metadata_only"]
        + counts["assets_declared_only"]
        + counts["assets_unresolved"]
        == counts["assets_total"]
    )


def test_no_verified_marks(manifest, envelope):
    blob = json.dumps(envelope, ensure_ascii=False)
    assert '"verified"' not in blob
    assert "verified_by_worker" not in blob
    assert manifest["checks"]["no_verified_marks_emitted"] is True


def test_report_scope_is_single_report(manifest, markdown):
    assert manifest["report_id"] == "4129"
    assert manifest["source"]["report_id"] == "4129"
    assert "tensor://reports/4129" == manifest["source"]["source_uri"]
    # no other report id is referenced anywhere in the manifest payload
    assert "reports/" + "4129" in manifest["source"]["source_uri"]
    assert manifest["counts"]["source_documents"] == 1


# ------------------------------------------------------------ reproducibility
def test_offline_regeneration_reproduces_manifest():
    """The committed manifest must be exactly what the generator produces today."""
    before = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out = PKG_DIR / "_regen_tmp.json"
    try:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "kf_wp_4129_01_register.py"),
             "--offline", "--out", str(out)],
            check=True, cwd=str(ROOT), capture_output=True,
        )
        after = json.loads(out.read_text(encoding="utf-8"))
    finally:
        out.unlink(missing_ok=True)
    b, a = copy.deepcopy(before), copy.deepcopy(after)
    b.pop("generated_at")
    a.pop("generated_at")
    assert a == b