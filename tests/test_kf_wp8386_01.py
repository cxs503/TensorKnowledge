"""Invariant tests for work package wp-8386-01 (task_type 01-asset-registration).

These assert the *contract* invariants, not merely that the script ran:

  * the manifest validates against the locally pinned shape schema;
  * every locator re-resolves to a unique verbatim slice of the live markdown;
  * the declared hash equals the contract hash, recomputed from the raw bytes;
  * ids are unique and the resolution bookkeeping adds up;
  * registration-only is respected (empty claims, no `verified` marks);
  * the manifest is byte-deterministic across rebuilds.

Four negative controls tamper with a copy of the manifest and assert that the
checkers actually go red -- otherwise "PASS" would prove nothing.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "docs" / "kf" / "wp-8386-01"
MANIFEST_PATH = PKG_DIR / "asset_manifest.json"
ENVELOPE_PATH = PKG_DIR / "kf_result.json"
SCHEMA_PATH = ROOT / "schemas" / "asset_manifest.v1.1.schema.json"
KFRESULT_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
MD_PATH = ROOT / "runs" / "wp-8386-01" / "report_8386.md"
CONTRACT_HASH = "sha256:4104143f4653a88fd9df9c12b93d3d05d42592aca5c835749a34f21ad85761af"

_spec = importlib.util.spec_from_file_location(
    "kf_wp8386_01_register", ROOT / "scripts" / "kf_wp8386_01_register.py")
kv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kv)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def md() -> str:
    return MD_PATH.read_text(encoding="utf-8")


def test_source_copy_hash_matches_contract(md):
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH


def test_manifest_validates_against_local_schema(manifest):
    jsonschema.validate(manifest, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_envelope_validates_against_kf_result_schema():
    jsonschema.validate(json.loads(ENVELOPE_PATH.read_text(encoding="utf-8")),
                        json.loads(KFRESULT_SCHEMA.read_text(encoding="utf-8")))


def test_envelope_provenance_hash_equals_contract_and_manifest(manifest):
    env = json.loads(ENVELOPE_PATH.read_text(encoding="utf-8"))
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert env["outputs"]["asset_manifest.json"]["source"]["hash"] == CONTRACT_HASH.split(":")[1]
    assert env["report_id"] == "8386" and env["package_id"] == "wp-8386-01"
    assert env["task_type"] == "01-asset-registration"


def test_every_locator_reresolves_uniquely(md, manifest):
    assert kv.check_locators(md, manifest) == []


def test_locator_check_detects_tampered_quote(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = next(x for x in tampered["assets"] if x["asset_id"] == "A10")
    a["locator"]["quote"] = a["locator"]["quote"].replace("6.42e-04", "6.42e-03")
    assert any(asset == "A10" for asset, _ in kv.check_locators(md, tampered))


def test_locator_check_detects_shifted_span(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = next(x for x in tampered["assets"] if x["asset_id"] == "A16")
    a["locator"]["start_char"] += 1
    assert any(asset == "A16" and why == "slice_mismatch"
               for asset, why in kv.check_locators(md, tampered))


def test_locator_check_detects_invented_resolution(manifest):
    """A21's PNG is genuinely absent from this worktree; relabelling it
    resolved_in_source must be caught."""
    tampered = copy.deepcopy(manifest)
    a = next(x for x in tampered["assets"] if x["asset_id"] == "A21")
    assert a["resolution"] == "referenced_unresolved"
    a["resolution"] = "resolved_in_source"
    assert any(p["asset_id"] == "A21" for p in kv.check_resolution_consistency(tampered))


def test_duplicate_id_detector_works(manifest):
    assert kv.check_duplicate_ids(manifest) == []
    tampered = copy.deepcopy(manifest)
    tampered["assets"][3]["asset_id"] = tampered["assets"][2]["asset_id"]
    assert kv.check_duplicate_ids(tampered) == [tampered["assets"][2]["asset_id"]]


def test_counts_are_consistent(manifest):
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    assert (c["resolved_in_source"] + c["referenced_unresolved"] + c["declared_absent"]
            == c["assets"])
    assert sum(c["by_class"].values()) == c["assets"]


def test_registration_only_no_claims_no_verified(manifest):
    assert manifest["claims"] == []          # no forced claim generation
    assert kv.check_claims(manifest) == []
    assert kv.check_forbidden_verified(manifest) == []


def test_nothing_marked_verified_in_report_markdown(md):
    # the report body may *discuss* the platform's verified gate, but must not
    # claim its own outputs are verified; assert no result table says so.
    for line in md.split("\n"):
        low = line.lower()
        if "verified" in low:
            assert "citation_verification" in low or "verified 门" in low or "verified（" in low


def test_manifest_is_byte_deterministic(manifest):
    again = kv.build_manifest({"markdown": MD_PATH.read_text(encoding="utf-8"),
                               "title": manifest["source"]["title"],
                               "scenario_key": manifest["source"]["scenario_key"],
                               "figures": [{"name": n} for n in manifest["source"]["platform_figures"]],
                               "tags": manifest["source"]["platform_tags"]})
    assert json.dumps(again, ensure_ascii=False, indent=2) == MANIFEST_PATH.read_text(encoding="utf-8")


def test_every_asset_quote_is_verbatim(md, manifest):
    """Zero manual transcription: each quote must be a raw slice, byte for byte."""
    for a in manifest["assets"]:
        assert a["locator"]["quote"] in md
        if a["locator"]["method"] == "char_span":
            assert md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]