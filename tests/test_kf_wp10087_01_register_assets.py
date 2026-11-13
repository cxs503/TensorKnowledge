#!/usr/bin/env python3
"""Regression tests for wp-10087-01 (01-asset-registration, report 10087).

Hermetic: everything comes from the emitted artefacts under docs/kf/wp-10087-01/
(source.md verbatim copy + asset_manifest.json + kf_result.json), so the suite needs no
network. The last two tests are *negative controls*: they mutate the source copy and the
manifest in memory and assert that the acceptance checks actually catch the damage —
otherwise a green suite would only prove that the assertions never run.

Run: python3 -m pytest tests/test_kf_wp10087_01_register_assets.py -q
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-10087-01")
MANIFEST = os.path.join(PKG, "asset_manifest.json")
KF_RESULT = os.path.join(PKG, "kf_result.json")
SOURCE = os.path.join(PKG, "source.md")
SCHEMA = os.path.join(ROOT, "schemas", "kf_result.v1.schema.json")
REPORT = os.path.join(ROOT, "docs", "kf_result_wp-10087-01.md")

EXPECTED_HASH = "sha256:6ed122a8092e41f05bebbb099ce1406a77ae3504f97785c7501c220f79310f72"
PACKAGE_ID = "wp-10087-01"
REPORT_ID = "10087"


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def md() -> str:
    with open(SOURCE, encoding="utf-8", newline="") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load_json(MANIFEST)


@pytest.fixture(scope="module")
def kf() -> dict:
    return load_json(KF_RESULT)


# ---------------------------------------------------------------------------
# identity / provenance
# ---------------------------------------------------------------------------
def test_source_hash_matches_contract(md):
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == EXPECTED_HASH


def test_source_copy_is_byte_identical_to_contract_length(md):
    assert len(md) == 3454
    assert len(md.encode("utf-8")) == 5341


def test_envelope_identity(kf, manifest):
    assert kf["package_id"] == PACKAGE_ID == manifest["package_id"]
    assert kf["task_type"] == "01-asset-registration"
    assert kf["report_id"] == REPORT_ID == manifest["report_id"]
    assert kf["provenance"]["source_field"] == "markdown"
    assert list(kf["outputs"]) == ["asset_manifest.json"]
    assert kf["outputs"]["asset_manifest.json"] == manifest


def test_envelope_validates_against_kf_result_v1(kf):
    jsonschema.validate(kf, load_json(SCHEMA))


def test_envelope_source_hash_equals_recomputed(kf, md):
    recomputed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert kf["provenance"]["source_hash"] == recomputed
    assert manifest_hash_equals(load_json(MANIFEST), recomputed)


def manifest_hash_equals(manifest: dict, digest: str) -> bool:
    return "sha256:" + manifest["source"]["hash"] == digest


# ---------------------------------------------------------------------------
# locators
# ---------------------------------------------------------------------------
def test_every_locator_is_an_exact_unique_slice(md, manifest):
    for asset in manifest["assets"]:
        loc = asset["locator"]
        span = md[loc["start_char"]:loc["end_char"]]
        assert span.rstrip("\n") == loc["quote"], asset["asset_id"]
        assert span.startswith(loc["quote"].splitlines()[0]), asset["asset_id"]
        assert md.count(loc["quote"]) == 1, asset["asset_id"]
        assert md.find(loc["quote"]) == loc["start_char"], asset["asset_id"]
        assert loc["start_line"] <= loc["end_line"]
        # reported line range must contain the quoted text
        head = md[:loc["start_char"]].count("\n") + 1
        assert head == loc["start_line"], asset["asset_id"]


def test_no_duplicate_ids_and_id_shape(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)


def test_counts_are_derived_from_assets(manifest):
    assets = manifest["assets"]
    counts = manifest["counts"]
    assert counts["assets"] == len(assets) == 24
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert counts["by_class"] == by_class
    assert counts["by_resolution"] == by_res
    assert (counts["resolved_in_source"] + counts["referenced_unresolved"]
            + counts["declared_absent"] == counts["assets"])


def test_unresolved_assets_are_explicit_not_silently_ok(manifest):
    unresolved = [a for a in manifest["assets"] if a["resolution"] == "referenced_unresolved"]
    assert {a["asset_id"] for a in unresolved} == {"A11", "A12"}
    for a in unresolved:
        assert a["resolution_check"]["result"] == "unresolved"
        assert "note" in a and a["note"]
        # the quote still has to resolve: we register the statement, not the file
        assert a["locator"]["quote"]


def test_figures_are_bound_to_platform_record(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    assert len(figs) == 4
    names = [f["platform_figure"]["name"] for f in figs]
    assert names == ["fig1_weibull_size_effect", "fig2_gaudin_spectrum",
                     "fig3_conservation_ledger", "fig4_strain_rate_study"]
    assert [f["platform_figure"]["index"] for f in figs] == [0, 1, 2, 3]
    assert len(manifest["source"]["platform_figures"]) == 4


# ---------------------------------------------------------------------------
# claims discipline
# ---------------------------------------------------------------------------
def test_claims_empty_and_nothing_marked_verified(manifest, kf):
    assert manifest["claims"] == [] == kf["claims"]
    assert '"verified"' not in json.dumps(manifest, ensure_ascii=False)


# ---------------------------------------------------------------------------
# rendered report
# ---------------------------------------------------------------------------
def test_report_has_exactly_one_json_block_equal_to_kf_result(kf):
    body = open(REPORT, encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == kf
    assert body.splitlines()[0].strip() == f"# KF-RESULT {PACKAGE_ID}"
    assert "kf-wp:" + PACKAGE_ID in body


# ---------------------------------------------------------------------------
# negative controls: the checks must fail on damaged input
# ---------------------------------------------------------------------------
def test_negative_control_tampered_source_breaks_hash(md):
    tampered = md.replace("R² = 0.9998", "R² = 1.0000", 1)
    assert tampered != md
    digest = "sha256:" + hashlib.sha256(tampered.encode("utf-8")).hexdigest()
    assert digest != EXPECTED_HASH


def test_negative_control_shifted_locator_is_detected(md, manifest):
    bad = copy.deepcopy(manifest)
    loc = bad["assets"][0]["locator"]
    loc["start_char"] += 1  # shift the recorded offset by one char
    span = md[loc["start_char"]:loc["end_char"]]
    assert span.rstrip("\n") != loc["quote"]  # the invariant would fire


def test_negative_control_duplicate_id_is_detected(manifest):
    bad = copy.deepcopy(manifest)
    bad["assets"][1]["asset_id"] = bad["assets"][0]["asset_id"]
    ids = [a["asset_id"] for a in bad["assets"]]
    assert len(ids) != len(set(ids))


def test_negative_control_schema_rejects_wrong_source_hash(kf):
    bad = copy.deepcopy(kf)
    bad["provenance"]["source_hash"] = "sha256:" + "0" * 64
    schema = load_json(SCHEMA)
    jsonschema.validate(bad, schema)  # pattern only: shape is fine
    assert bad["provenance"]["source_hash"] != EXPECTED_HASH  # value check fires
    broken = copy.deepcopy(kf)
    broken["provenance"]["source_hash"] = "deadbeef"  # not sha256:<64 hex>
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(broken, schema)