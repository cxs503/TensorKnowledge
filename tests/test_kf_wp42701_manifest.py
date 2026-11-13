"""Offline contract gate for work package wp-427-01 (report_id=427, task 01).

The packaged artefacts (``runs/wp-427-01/``) must stand on their own: everything
the platform gate re-checks — JSON validity, envelope schema, source hash,
locator resolvability, id uniqueness — is re-checked here **without any network
access**, against the committed pinned copy of the source markdown. A pass here
means the envelope is internally consistent; the platform still recomputes the
hash against its own record (that is the only thing this test cannot prove).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "runs" / "wp-427-01"
MANIFEST = RUN / "asset_manifest.json"
ENVELOPE = RUN / "kf_result_envelope.json"
SOURCE = RUN / "source_427.md"
SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"

CONTRACT_SOURCE_HASH = (
    "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846")
CONTRACT_CHARS = 2732


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return SOURCE.read_bytes().decode("utf-8")


def test_package_identity(manifest: dict) -> None:
    assert manifest["package_id"] == "wp-427-01"
    assert manifest["report_id"] == "427"
    assert manifest["source"]["source_uri"] == "tensor://reports/427"
    assert manifest["source"]["source_field"] == "markdown"


def test_pinned_source_hash_matches_contract(source: str) -> None:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert "sha256:" + digest == CONTRACT_SOURCE_HASH
    assert len(source) == CONTRACT_CHARS


def test_envelope_passes_result_schema(envelope: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = [e.message
              for e in jsonschema.Draft202012Validator(schema).iter_errors(envelope)]
    assert errors == []
    assert set(envelope["outputs"]) == {"asset_manifest.json"}


def test_envelope_hash_is_the_source_hash(envelope: dict, source: str) -> None:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert envelope["provenance"]["source_hash"] == "sha256:" + digest
    assert envelope["provenance"]["source_field"] == "markdown"


def test_outputs_are_the_manifest(envelope: dict, manifest: dict) -> None:
    assert envelope["outputs"]["asset_manifest.json"] == manifest


def test_every_locator_resolves_verbatim_in_pinned_source(manifest: dict,
                                                          source: str) -> None:
    lines = source.split("\n")
    assert manifest["locators"], "a registration with zero locators proves nothing"
    for loc in manifest["locators"]:
        line_no = loc["locator"]["line"]
        assert 1 <= line_no <= len(lines), loc["fact_id"]
        assert loc["quote"] in lines[line_no - 1], (
            f"{loc['fact_id']}: quote not on declared line {line_no}")
        assert loc["quote"] in source, loc["fact_id"]
        assert loc["resolved"] is True


def test_asset_ids_unique_across_manifest(manifest: dict) -> None:
    ids = ([a["asset_id"] for a in manifest["assets"]]
           + [d["asset_id"] for d in manifest["derived_artifacts"]])
    assert len(ids) == len(set(ids))
    assert manifest["id_integrity"]["unique"] is True
    assert manifest["id_integrity"]["duplicates"] == []


def test_claims_empty_is_declared_not_silent(manifest: dict) -> None:
    # task 01 registers assets only; an empty claim set must carry a reason.
    assert manifest["claims"] == []
    assert len(manifest["claims_empty_reason"]) > 20


def test_unresolved_assets_carry_their_error(manifest: dict) -> None:
    for asset in manifest["assets"]:
        if asset["resolvable"]:
            assert asset["sha256"], asset["asset_id"]
        else:
            assert asset.get("resolution_error"), asset["asset_id"]
            assert asset["bytes"] == 0
    # every unresolved entry surfaces in the manifest's own unresolved list
    unresolved = {u["item"] for u in manifest["unresolved"]}
    missing = {a["name"] for a in manifest["assets"] if not a["resolvable"]}
    assert missing == unresolved


def test_declared_counts_agree_with_content(manifest: dict) -> None:
    counts = manifest["counts"]
    assert counts["figures_declared"] == sum(
        1 for a in manifest["assets"] if a["kind"] == "figure")
    assert counts["figures_resolved"] == sum(
        1 for a in manifest["assets"] if a["kind"] == "figure" and a["resolvable"])
    assert counts["locators"] == len(manifest["locators"])
    assert counts["locators_resolved"] == sum(
        1 for loc in manifest["locators"] if loc["resolved"])
    assert counts["claims"] == len(manifest["claims"])


def test_declared_local_copies_exist(manifest: dict) -> None:
    for asset in manifest["assets"]:
        copy = asset.get("local_copy")
        if copy:
            assert (REPO / copy).is_file(), copy