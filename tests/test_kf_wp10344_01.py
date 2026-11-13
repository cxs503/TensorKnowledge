"""wp-10344-01 acceptance tests (offline; no platform calls).

They re-run scripts/kf_wp10344_01_check.py against the artefacts in the tree, so the
contract acceptance items are machine-checked rather than asserted in prose.
"""
from __future__ import annotations

import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-10344-01")


def _load_checker():
    path = os.path.join(ROOT, "scripts", "kf_wp10344_01_check.py")
    spec = importlib.util.spec_from_file_location("kf_wp10344_01_check", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def checker():
    return _load_checker()


@pytest.fixture(scope="module")
def manifest():
    with open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def kf():
    with open(os.path.join(PKG, "kf_result.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_acceptance_all_pass(checker):
    res = checker.check_all()
    assert res["all_pass"], res["failed_items"]


@pytest.mark.parametrize("item", [
    "source_locator_resolvable",
    "source_hash_matches",
    "no_duplicate_ids",
    "all_claims_have_evidence_or_explicit_unresolved_status",
])
def test_acceptance_item(checker, item):
    assert checker.check_all()["items"][item]["pass"]


def test_envelope_matches_contract(kf):
    assert kf["package_id"] == "wp-10344-01"
    assert kf["task_type"] == "01-asset-registration"
    assert kf["report_id"] == "10344"
    assert kf["provenance"]["source_field"] == "markdown"
    assert kf["provenance"]["source_hash"].startswith("sha256:")
    assert "asset_manifest.json" in kf["outputs"]
    assert kf["outputs"]["asset_manifest.json"]["report_id"] == "10344"


def test_single_report_scope(manifest):
    # scope guard: the package must not reach any report other than 10344
    assert manifest["source_uri"] == "tensor://reports/10344"
    blob = json.dumps(manifest, ensure_ascii=False)
    assert "tensor://reports/" in blob
    assert blob.count("tensor://reports/10344") >= 1
    for other in ("tensor://reports/1610", "tensor://reports/448", "tensor://reports/623"):
        assert other not in blob


def test_claims_not_marked_verified(manifest, kf):
    assert manifest["claims"] == []
    assert kf.get("claims", []) == []
    blob = json.dumps({"m": manifest, "k": kf}, ensure_ascii=False).lower()
    assert '"status": "verified"' not in blob
    assert '"verified": true' not in blob


def test_every_asset_has_locator_and_resolution(manifest):
    for a in manifest["assets"]:
        assert a["locator"]["quote"], a["asset_id"]
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved", "declared_absent"}
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent", "present"}
    counts = manifest["counts"]
    assert counts["assets"] == len(manifest["assets"])
    assert sum(counts["by_resolution"].values()) == counts["assets"]


def test_hash_pinned_to_contract(manifest):
    h = "sha256:a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900"
    assert manifest["source_hash"] == h
    assert manifest["source_hash_expected"] == h
    assert manifest["source_hash_matches"] is True
    assert manifest["chars"] == 2888
    assert manifest["chars_match_contract"] is True