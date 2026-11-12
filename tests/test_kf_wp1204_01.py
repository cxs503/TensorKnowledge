"""wp-1204-01 acceptance invariants, checked offline against the frozen snapshot.

These tests assert *invariants over the delivered artifacts* (hash identity,
locator verbatim-ness, schema conformance, id uniqueness, claim policy) rather
than merely executing the generator: every assertion can fail independently.

Run: python3 -m pytest tests/test_kf_wp1204_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = "wp-1204-01"
CONTRACT_HASH = "437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef"
SNAP = ROOT / "runs/wp-1204-01/source_1204.md"
MAN = ROOT / "docs/kf/wp-1204-01/asset_manifest.json"
ENV = ROOT / "docs/kf/wp-1204-01/kf_result.json"
SCHEMA = ROOT / "schemas/kf_result.v1.schema.json"


@pytest.fixture(scope="module")
def md() -> str:
    return SNAP.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MAN.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENV.read_text(encoding="utf-8"))


def test_source_snapshot_matches_contract_hash(md):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == 5853
    assert len(md.encode("utf-8")) == 9016


def test_envelope_conforms_to_schema(envelope):
    jsonschema.validate(instance=envelope, schema=json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert envelope["package_id"] == PKG
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "1204"
    assert "asset_manifest.json" in envelope["outputs"]


def test_source_hash_consistent_across_envelope_and_manifest(envelope, manifest):
    want = "sha256:" + CONTRACT_HASH
    assert envelope["provenance"]["source_hash"] == want
    assert manifest["provenance"]["source_hash"] == want


def test_every_text_locator_is_verbatim(md, manifest):
    checked = 0
    for asset in manifest["assets"]:
        loc = asset["locator"]
        if loc["scheme"] != "text_quote":
            continue
        checked += 1
        assert loc["quote"] in md, f"{asset['asset_id']} locator not verbatim"
        assert len(loc["quote"]) >= 8
    assert checked >= 10


def test_figure_locators_point_at_report_record_indices(manifest):
    figs = [a for a in manifest["assets"] if a["kind"] == "embedded_figure"]
    assert [f["locator"]["index"] for f in figs] == list(range(len(figs)))
    for f in figs:
        assert f["name"].endswith(".png")
        # no payload in the platform record -> hash must stay null (no invention)
        assert f["sha256"] is None and f["resolution"]["has_payload"] is False


def test_asset_ids_unique_and_counts_match(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    c = manifest["counts"]
    assert c["assets_total"] == len(ids)
    assert c["resolved"] + c["unresolved"] + c["metadata_only"] == len(ids)
    for key, status in (("resolved", "resolved"), ("unresolved", "unresolved"),
                        ("metadata_only", "metadata_only")):
        assert c[key] == sum(1 for a in manifest["assets"] if a["resolution"]["status"] == status)


def test_unresolved_assets_state_a_reason_and_are_not_overclaimed(manifest):
    for a in manifest["assets"]:
        res = a["resolution"]
        if res["status"] == "resolved":
            continue
        assert res.get("reason"), a["asset_id"]
        if "external_copy_observed" in a:
            obs = a["external_copy_observed"]
            assert obs["used_to_resolve"] is False
            assert res["status"] == "unresolved"


def test_declared_md5_anchors_are_not_presented_as_confirmed(manifest):
    anchors = [a for a in manifest["assets"] if a["kind"] == "declared_hash_anchor"]
    assert len(anchors) == 2
    for a in anchors:
        assert a["resolution"]["recomputed"] is False
        assert a["resolution"]["status"] == "unresolved"


def test_claims_policy_no_forced_generation_and_nothing_verified(envelope):
    assert envelope["claims"] == []
    assert all(c.get("status") != "verified" for c in envelope["claims"])


def test_manifest_on_disk_equals_envelope_output(manifest, envelope):
    assert envelope["outputs"]["asset_manifest.json"] == manifest