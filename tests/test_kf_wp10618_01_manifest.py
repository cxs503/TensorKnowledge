"""Regression tests for work package wp-10618-01 (01-asset-registration, report 10618).

These tests are offline: they pin the committed artefacts under
docs/kf/wp-10618-01/ and the frozen source snapshot under runs/wp-10618-01/ and
re-verify every claim the package makes, without touching the platform API.

    python3 -m pytest tests/test_kf_wp10618_01_manifest.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-10618-01"
OUT = ROOT / "docs" / "kf" / PKG
SOURCE = ROOT / "runs" / PKG / "source_10618.md"

CONTRACT_HASH = "sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01"
CONTRACT_CHARS = 7463


@pytest.fixture(scope="module")
def md() -> str:
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


def test_source_snapshot_hash_and_size(md):
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_manifest_identity(manifest):
    assert manifest["package_id"] == PKG
    assert manifest["report_id"] == "10618"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["source"]["source_hash"] == CONTRACT_HASH
    assert manifest["source"]["hash_matches_contract"] is True
    assert manifest["source"]["chars"] == CONTRACT_CHARS


def test_asset_ids_unique_and_well_formed(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)


def test_every_locator_resolves_verbatim_and_uniquely(manifest, md):
    for a in manifest["assets"]:
        loc = a["locator"]
        q, s, e = loc["quote"], loc["start_char"], loc["end_char"]
        assert md.count(q) == 1, a["asset_id"]
        if loc["method"] == "document":
            assert (s, e) == (0, len(md)), a["asset_id"]
        else:
            assert md[s:e] == q, a["asset_id"]
            assert md.find(q) == s, a["asset_id"]
        assert loc["unique"] is True, a["asset_id"]


def test_counts_agree_with_asset_list(manifest):
    assets = manifest["assets"]
    counts = manifest["counts"]
    assert counts["assets"] == len(assets)
    by_res = {}
    for a in assets:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert counts["by_resolution"] == by_res
    assert counts["resolved_in_source"] == by_res.get("resolved_in_source", 0)


def test_resolution_states_declared_consistently(manifest):
    for a in manifest["assets"]:
        res, chk = a["resolution"], a["resolution_check"]["result"]
        assert res in {"resolved_in_source", "referenced_unresolved", "declared_absent"}
        if res == "resolved_in_source":
            assert chk in {"resolved", "present"}, a["asset_id"]
        elif res == "referenced_unresolved":
            assert chk in {"absent", "unresolved"}, a["asset_id"]


def test_no_claims_and_nothing_marked_verified(manifest, envelope):
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert manifest["integrity"]["claim_extraction_performed"] is False
    assert manifest["integrity"]["verified_marks_emitted"] is False
    assert "verified" not in json.dumps(envelope["claims"])


def test_envelope_matches_schema_and_manifest(envelope, manifest):
    import jsonschema

    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(envelope)
    assert envelope["provenance"]["source_hash"] == manifest["source"]["source_hash"] == CONTRACT_HASH
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    assert envelope["package_id"] == PKG and envelope["report_id"] == "10618"


def test_manifest_matches_rebound_local_schema(manifest):
    """schemas/asset_manifest.v1.schema.json pins wp-448-01; rebind identity, keep the rest."""
    import copy

    import jsonschema

    schema = copy.deepcopy(json.loads(
        (ROOT / "schemas" / "asset_manifest.v1.schema.json").read_text(encoding="utf-8")))

    def walk(node, key=None):
        if isinstance(node, dict):
            if "const" in node and isinstance(node["const"], str):
                c = node["const"]
                if c == "wp-448-01":
                    node["const"] = PKG
                elif c == "448":
                    node["const"] = "10618"
                elif c.startswith("tensor://reports/"):
                    node["const"] = "tensor://reports/10618"
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)

    walk(schema)
    jsonschema.Draft7Validator(schema).validate(manifest)


def test_build_timestamp_is_deterministic_policy(manifest, envelope):
    """Reruns must be byte-identical: emitted_at is pinned, not wall-clock."""
    assert manifest["generated_at"].endswith("+00:00") or manifest["generated_at"].endswith("Z")
    assert "created_at" in manifest["generated_at_policy"]
    assert envelope["provenance"]["emitted_at"] == manifest["generated_at"]
    assert "deterministic" in envelope["provenance"]["emitted_at_policy"]


def test_result_markdown_has_exactly_one_json_block():
    md = (OUT / "result.md").read_text(encoding="utf-8")
    assert len(re.findall(r"```json\n", md)) == 1
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    env = json.loads(blocks[0])
    assert env["package_id"] == PKG
    assert md.startswith("# KF-RESULT %s" % PKG)


def test_figures_from_source_are_registered_unresolved(manifest, md):
    refs = re.findall(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", md, re.M)
    assert len(refs) == 4
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure_reference"]
    assert len(figs) == 4
    assert all(a["resolution"] == "referenced_unresolved" for a in figs)
    assert [a["locator"]["quote"] for a in figs] == [
        line for line in md.split("\n") if re.match(r"^!\[", line)]