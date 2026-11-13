"""Acceptance checks for KF work package wp-11930-01 (asset registration).

Each test maps to one acceptance item of the work-package contract:
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

The source markdown is the byte-for-byte artifact fetched from the platform
(docs/kf/wp-11930-01/source_11930.md); nothing here re-types report content.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "kf" / "wp-11930-01"
MANIFEST = ART / "asset_manifest.json"
ENVELOPE = ART / "kf_result.wp-11930-01.json"
SOURCE = ART / "source_11930.md"
CONTRACT_HASH = "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325"


@pytest.fixture(scope="module")
def md() -> str:
    return SOURCE.read_bytes().decode("utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


def test_artifacts_are_valid_json():
    assert isinstance(json.loads(MANIFEST.read_text(encoding="utf-8")), dict)
    assert isinstance(json.loads(ENVELOPE.read_text(encoding="utf-8")), dict)


def test_manifest_schema_pass(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "schemas" / "asset_manifest.v1.wp-11930-01.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(manifest, schema)


def test_envelope_schema_pass(envelope):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["package_id"] == "wp-11930-01"
    assert envelope["report_id"] == "11930"
    assert "asset_manifest.json" in envelope["outputs"]


def test_source_hash_matches_contract(manifest, envelope, md):
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH.split(":", 1)[1]
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == len(md)
    assert manifest["source"]["bytes_utf8"] == len(md.encode("utf-8"))
    assert manifest["integrity"]["hash_matches_contract"] is True


def test_every_locator_resolves_verbatim(md, manifest):
    for asset in manifest["assets"]:
        loc = asset["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], asset["asset_id"]
        assert md.count(loc["quote"]) == 1, f"{asset['asset_id']} quote not unique"
        assert loc["unique"] is True
        # line numbers must agree with the char span
        assert md.count("\n", 0, loc["start_char"]) + 1 == loc["start_line"]
        # the referenced path itself must appear inside the quoted line
        if asset["resolution"] != "declared_absent":
            assert asset["path_in_report"] in loc["quote"], asset["asset_id"]


def test_no_duplicate_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    paths = [a["path_in_report"] for a in manifest["assets"] if a["resolution"] != "declared_absent"]
    assert len(paths) == len(set(paths))


def test_counts_consistent(manifest):
    assets = manifest["assets"]
    counts = manifest["counts"]
    assert counts["assets"] == len(assets)
    assert sum(counts["by_class"].values()) == len(assets)
    assert sum(counts["by_resolution"].values()) == len(assets)
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert counts[res] == sum(1 for a in assets if a["resolution"] == res)


def test_claims_empty_is_explicit_not_fabricated(manifest, envelope):
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert "no_claims_by_design" in manifest["integrity"]
    assert all(
        a["resolution"] == "resolved_in_source" or a["note"] for a in manifest["assets"]
    ), "unresolved/absent asset must carry an explicit reason"


def test_unresolved_assets_are_not_in_this_worktree(manifest):
    """referenced_unresolved must be honest: the path really is absent locally."""
    for asset in manifest["assets"]:
        if asset["resolution"] != "referenced_unresolved":
            continue
        assert not (ROOT / asset["path_in_report"]).exists(), asset["asset_id"]
        assert asset["resolution_check"]["result"] == "unresolved"
    assert manifest["counts"]["referenced_unresolved"] > 0


def test_figures_carry_platform_bytes_and_hash(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    assert len(figs) == 6
    platform_names = {f["name"] for f in manifest["source"]["platform_figures"]}
    assert len(platform_names) == 6
    for f in figs:
        assert f["resolution"] == "resolved_in_source"
        assert f["platform_bytes"] > 0
        assert len(f["platform_sha256"]) == 64
        assert f["path_in_report"].rsplit("/", 1)[-1] in platform_names