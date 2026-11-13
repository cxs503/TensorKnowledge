"""wp-9777-01 (01-asset-registration, report 9777) acceptance tests.

Offline: everything is checked against artefacts committed in this worktree, so the gate can be
re-run without platform credentials. The suite deliberately recomputes the hash / locators with
its own code instead of importing the producer's ``verify()`` -- otherwise a bug in that function
would certify itself.

Producing/refreshing the artefacts from the live record:
    python3 scripts/kf_wp9777_01_register.py all
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-9777-01")
EXPECTED_HASH = "sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7"
EXPECTED_CHARS = 4341
EXPECTED_TITLE = ("精确 DSM Timoshenko 梁模态验收审计：7/7 判据 PASS、dsbeam 三处缺陷修复、"
                  "m6117 6.28% 归因闭环")
EXPECTED_SCENARIO = "structural-dynamics/dsm-beam-modal"


def load(name: str):
    with open(os.path.join(PKG, name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def source() -> str:
    with open(os.path.join(PKG, "source.md"), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load("asset_manifest.json")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return load("kf_result.json")


def sha(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------- 1. identity/hash
def test_source_bytes_bind_to_contract_hash(source: str) -> None:
    assert sha(source.encode("utf-8")) == EXPECTED_HASH
    assert len(source) == EXPECTED_CHARS


def test_envelope_provenance_matches_source(source: str, envelope: dict) -> None:
    assert envelope["package_id"] == "wp-9777-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "9777"
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == sha(source.encode("utf-8")) == EXPECTED_HASH


def test_manifest_source_identity(manifest: dict) -> None:
    src = manifest["source"]
    assert manifest["schema"] == "asset_manifest.v1"
    assert manifest["report_id"] == "9777"
    assert src["uri"] == src["source_uri"] == "tensor://reports/9777"  # boundary: only 9777
    assert src["field"] == src["source_field"] == "markdown"
    assert "sha256:" + src["hash"] == src["source_hash"] == EXPECTED_HASH
    assert src["contract_source_hash"] == EXPECTED_HASH and src["hash_match"] is True
    assert src["chars"] == src["contract_chars"] == EXPECTED_CHARS
    assert src["bytes_utf8"] == len(open(os.path.join(PKG, "source.md"), "rb").read())
    # record-level identity as declared by the platform (contract title/scenario)
    assert src["title"] == EXPECTED_TITLE and src["title_matches_contract"] is True
    assert src["scenario_key"] == EXPECTED_SCENARIO and src["scenario_matches_contract"] is True


# ------------------------------------------------------------- 2. schema validity
def test_envelope_validates_against_kf_result_v1(envelope: dict) -> None:
    schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"),
                            encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(envelope)


def test_manifest_mirrors_asset_manifest_v1_shape(manifest: dict) -> None:
    """schemas/asset_manifest.v1.schema.json pins package_id/report_id/uri to another package;
    relax only those three consts and keep every other constraint."""
    schema = json.load(open(os.path.join(ROOT, "schemas", "asset_manifest.v1.schema.json"),
                            encoding="utf-8"))
    for obj, key in ((schema["properties"], "package_id"),
                     (schema["properties"], "report_id")):
        obj[key].pop("const", None)
    schema["properties"]["source"]["properties"]["uri"].pop("const", None)
    jsonschema.Draft202012Validator(schema).validate(manifest)


# --------------------------------------------------------- 3. locator resolvability
@pytest.mark.parametrize("asset_id", ["A%02d" % i for i in range(1, 10)])
def test_asset_locator_resolves_verbatim_and_uniquely(manifest: dict, source: str,
                                                      asset_id: str) -> None:
    a = next(x for x in manifest["assets"] if x["asset_id"] == asset_id)
    loc = a["locator"]
    q = loc["quote"]
    lines = source.rstrip("\n").split("\n")
    assert q and q in source, "quote not verbatim in source"
    assert source.count(q) == 1, "quote is not unique in source"
    assert source.find(q) == loc["start_char"], "char offset drift"
    assert 0 < loc["start_line"] <= loc["end_line"] <= len(lines)
    if loc["method"] == "document":
        # document-scoped locator: span = whole document, quote anchors its identity line
        assert a["asset_id"] == "A01" and (loc["start_char"], loc["end_char"]) == (0, len(source))
        assert q == lines[0]
    else:
        assert loc["end_char"] == loc["start_char"] + len(q)
        assert q in lines[loc["start_line"] - 1], "quote not on the declared line"
        assert loc["unique"] is True


def test_every_locator_is_reproducible_from_source(manifest: dict, source: str) -> None:
    lines = source.rstrip("\n").split("\n")
    for loc in manifest["locators"]:
        q = loc["quote"]
        assert q in source and source.count(q) == 1
        assert sha(q.encode("utf-8")) == loc["quote_sha256"]
        if loc["asset_id"] != "A01":
            assert q in lines[loc["locator"]["line"] - 1]
    for f in manifest["identity_facts"]:
        assert lines[f["locator"]["line"] - 1] == f["quote"]
        assert sha(f["quote"].encode("utf-8")) == f["quote_sha256"]


def test_symbol_references_resolve(manifest: dict, source: str) -> None:
    lines = source.rstrip("\n").split("\n")
    assert manifest["symbol_references"], "report declares inline code symbols"
    for s in manifest["symbol_references"]:
        assert s["quote"] in source
        assert s["quote"] in lines[s["locator"]["line"] - 1]


# ---------------------------------------------------------------- 4. id integrity
def test_no_duplicate_asset_ids(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids == sorted(set(ids)), "asset ids must be present and unique"
    assert manifest["id_integrity"]["unique"] is True
    assert manifest["id_integrity"]["duplicates"] == []


def test_counts_are_derived_not_asserted(manifest: dict) -> None:
    res = [a["resolution"] for a in manifest["assets"]]
    c = manifest["counts"]
    assert c["assets"] == len(res)
    assert c["resolved_in_source"] == res.count("resolved_in_source")
    assert c["referenced_unresolved"] == res.count("referenced_unresolved")
    assert sum(c["by_resolution"].values()) == len(res)
    assert manifest["integrity"]["quote_uniqueness"]["all_unique"] is True
    assert manifest["integrity"]["hash_matches_contract"] is True


# --------------------------------------------------------------- 5. claim discipline
def test_claims_empty_is_legal_and_reasoned(manifest: dict, envelope: dict) -> None:
    assert envelope["claims"] == []
    assert manifest["claims"] == []
    assert len(manifest["claims_empty_reason"]) > 40
    blob = json.dumps(envelope, ensure_ascii=False)
    assert not re.search(r'"(?:status)"\s*:\s*"verified"', blob)


def test_unresolved_assets_are_declared_not_hidden(manifest: dict) -> None:
    """Registration must not silently drop what it cannot resolve."""
    unresolved = [a for a in manifest["assets"] if a["resolution"] != "resolved_in_source"]
    assert {u["asset_id"] for u in unresolved} == {u["asset_id"] for u in manifest["unresolved"]}
    for u in unresolved:
        assert u["resolution_check"]["result"] in {"unresolved", "absent", "present"}
        assert u["note"]
    fig = [a for a in manifest["assets"] if a["asset_class"] == "figure_reference"]
    assert len(fig) == manifest["counts"]["figures_declared_in_record"] == 5
    assert manifest["counts"]["figures_with_bytes"] == 0