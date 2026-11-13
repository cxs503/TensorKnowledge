#!/usr/bin/env python3
"""wp-9756-01 | offline self-check for the asset-registration package (report_id=9756).

Every assertion is recomputed from files in this worktree; nothing is taken from the
manifest on trust. Run:  python -m pytest tests/test_kf_wp9756_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import jsonschema
import pytest

PKG_DIR = "docs/kf/wp-9756-01"
CONTRACT_HASH = "sha256:66c02e91e7ffcc3d81b24465112b94ac481ebc351584c13d01d978c16be4316b"
CONTRACT_CHARS = 8293
ENVELOPE_SCHEMA = "schemas/kf_result.v1.schema.json"


def _load(name: str):
    with open(os.path.join(PKG_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def source_md() -> str:
    with open(os.path.join(PKG_DIR, "source.md"), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _load("asset_manifest.json")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return _load("kf_result.json")


@pytest.fixture(scope="module")
def locators() -> dict:
    return _load("locator_check.json")


# ---------------------------------------------------------------- hash identity
def test_source_hash_matches_contract(source_md: str, manifest: dict) -> None:
    got = "sha256:" + hashlib.sha256(source_md.encode("utf-8")).hexdigest()
    assert got == CONTRACT_HASH, got
    assert manifest["source"]["hash"] == got == manifest["source"]["hash_expected"]
    assert manifest["source"]["hash_matches_contract"] is True


def test_chars_match_contract(source_md: str, manifest: dict) -> None:
    assert len(source_md) == CONTRACT_CHARS == manifest["source"]["chars"]
    assert len(source_md.encode("utf-8")) == manifest["source"]["bytes_utf8"]
    assert manifest["source"]["chars_matches_contract"] is True


def test_envelope_provenance_hash_is_the_same_hash(envelope: dict, source_md: str) -> None:
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == (
        "sha256:" + hashlib.sha256(source_md.encode("utf-8")).hexdigest())


# ------------------------------------------------------------ locator integrity
def test_every_locator_resolves_verbatim(source_md: str, manifest: dict) -> None:
    bad = []
    for loc in manifest["locators"]:
        if loc["source_field"] != "markdown":
            continue
        pos = source_md.find(loc["quote"])
        if pos < 0:
            bad.append((loc["locator_id"], "missing"))
            continue
        if pos != loc["char_start"] or pos + len(loc["quote"]) != loc["char_end"]:
            bad.append((loc["locator_id"], "offset"))
        line = source_md.count("\n", 0, pos) + 1
        if line != loc["line"]:
            bad.append((loc["locator_id"], "line"))
        if source_md.count(loc["quote"]) != loc["occurrences"]:
            bad.append((loc["locator_id"], "occurrences"))
    assert bad == [], bad


def test_asset_locators_are_the_same_as_locator_check(manifest: dict, locators: dict) -> None:
    by_id = {loc["locator_id"]: loc for loc in locators["checks"]}
    for asset in manifest["assets"]:
        lid = asset["locator"].get("locator_id")
        if lid is None:            # record-sourced figure metadata / whole-document asset
            assert asset["locator"]["source_field"] in ("record", "markdown")
            assert asset["kind"] in ("embedded_figure_metadata", "report_markdown")
            continue
        assert by_id[lid]["quote"] == asset["locator"]["quote"]
        assert by_id[lid]["asset_id"] == asset["asset_id"]


def test_locator_check_report_is_complete(locators: dict, manifest: dict) -> None:
    assert locators["quotes_checked"] == locators["quotes_resolvable"] == len(manifest["locators"])
    assert locators["unresolved"] == [] and locators["non_unique"] == []
    assert locators["source_hash"] == CONTRACT_HASH


# --------------------------------------------------------------- schema / shape
def test_envelope_schema_pass(envelope: dict) -> None:
    schema = json.load(open(ENVELOPE_SCHEMA, encoding="utf-8"))
    jsonschema.validate(envelope, schema)


def test_manifest_schema_pass(manifest: dict) -> None:
    schema = json.load(open(os.path.join(PKG_DIR, "asset_manifest.schema.json"), encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_envelope_keys_and_outputs(envelope: dict, manifest: dict) -> None:
    assert set(envelope) <= {"package_id", "task_type", "report_id", "provenance", "outputs", "claims"}
    assert envelope["package_id"] == "wp-9756-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "9756"
    assert list(envelope["outputs"]) == ["asset_manifest.json"]
    assert envelope["outputs"]["asset_manifest.json"] == manifest


def test_no_duplicate_ids(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("r9756:") for i in ids)
    lids = [loc["locator_id"] for loc in manifest["locators"]]
    assert len(lids) == len(set(lids))
    assert manifest["id_integrity"]["duplicate_asset_ids"] == []


def test_claims_empty_with_explicit_reason(envelope: dict, manifest: dict) -> None:
    assert envelope["claims"] == [] and manifest["claims"] == []
    assert manifest["claims_empty_reason"].strip()
    # no claim anywhere is marked verified by this package
    blob = json.dumps(manifest, ensure_ascii=False) + json.dumps(envelope, ensure_ascii=False)
    assert '"verified"' not in blob and "verified: true" not in blob


# ------------------------------------------------------------- scope confinement
def test_only_report_9756_is_referenced(manifest: dict, envelope: dict) -> None:
    assert manifest["report_id"] == "9756" and envelope["report_id"] == "9756"
    assert manifest["source"]["uri"] == "tensor://reports/9756"
    assert manifest["id_integrity"]["reports_other_than_9756_touched"] == []
    other = re.findall(r"reports/(\d+)", json.dumps(manifest, ensure_ascii=False))
    assert set(other) <= {"9756"}, other


def test_asset_resolution_ledger(manifest: dict) -> None:
    counts = manifest["counts"]
    by_res = counts["by_resolution"]
    assert sum(by_res.values()) == counts["assets_total"] == len(manifest["assets"])
    assert by_res["resolved_in_source"] == 1                      # the markdown itself
    assert counts["figures_with_bytes"] == 0                      # no png payload in the record
    assert counts["figures_declared_in_record"] == 4
    kinds = counts["by_kind"]
    assert kinds["embedded_figure_metadata"] == 4 and kinds["figure_reference"] == 4


def test_figure_metadata_matches_platform_record_shape(manifest: dict) -> None:
    figs = [a for a in manifest["assets"] if a["kind"] == "embedded_figure_metadata"]
    names = [a["name"] for a in figs]
    assert names == ["fig1_eexi_vs_dwt.png", "fig2_cii_rating_bands.png",
                     "fig3_power_limit.png", "fig4_grade_vs_year.png"]
    for a in figs:
        assert a["caption"] and a["resolution"] == "metadata_only"
        assert a["locator"]["source_field"] == "record"


def test_figure_png_hash_recorded(manifest: dict, source_md: str) -> None:
    png = os.path.join(PKG_DIR, "figures", "asset_manifest_coverage.png")
    assert os.path.exists(png)
    digest = "sha256:" + hashlib.sha256(open(png, "rb").read()).hexdigest()
    txt = open(os.path.join(PKG_DIR, "sha256.txt"), encoding="utf-8").read()
    assert digest in txt
    assert CONTRACT_HASH in txt