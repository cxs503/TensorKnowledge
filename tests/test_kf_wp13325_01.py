#!/usr/bin/env python3
"""Offline re-verification of KF package wp-13325-01 (report 13325).

These tests re-check the *registration* claims of the package without any network
access: the byte-identical markdown snapshot is the ground truth, and every
locator in asset_manifest.json must resolve inside it. They assert invariants
(quote is a unique substring, span matches the quote, hash matches the contract),
not merely that the generator ran.

Run:  pytest -q tests/test_kf_wp13325_01.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import jsonschema
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "docs", "kf", "wp-13325-01")  # tracked mirror (artifacts/ is gitignored)
MANIFEST = os.path.join(OUT, "asset_manifest.json")
RESULT = os.path.join(OUT, "kf_result.json")
SNAPSHOT = os.path.join(OUT, "source_markdown.md")
CONTRACT_HASH = "f7a7270b3721cd37011bb6ab66ebba8a0cb6e031b7e971c9a900b4c22acb1fe9"


@pytest.fixture(scope="module")
def md() -> str:
    with open(SNAPSHOT, "rb") as fh:
        return fh.read().decode("utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def result() -> dict:
    with open(RESULT, encoding="utf-8") as fh:
        return json.load(fh)


def test_source_hash_matches_contract(md):
    got = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert got == CONTRACT_HASH
    assert len(md) == 2078


def test_manifest_and_result_are_schema_valid(manifest, result):
    with open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"), encoding="utf-8") as fh:
        jsonschema.validate(result, json.load(fh))
    with open(os.path.join(ROOT, "schemas", "asset_manifest.v1.kf-package.schema.json"),
              encoding="utf-8") as fh:
        jsonschema.validate(manifest, json.load(fh))


def test_provenance_hash_equals_snapshot_hash(result, md):
    assert result["provenance"]["source_hash"] == "sha256:" + hashlib.sha256(
        md.encode("utf-8")).hexdigest()
    assert result["provenance"]["source_field"] == "markdown"
    assert result["report_id"] == "13325"


def test_every_locator_resolves_and_is_unique(manifest, md):
    for asset in manifest["assets"]:
        loc = asset["locator"]
        quote = loc["quote"]
        assert quote in md, f"{asset['asset_id']}: quote not in source"
        assert md.count(quote) == 1, f"{asset['asset_id']}: quote not unique"
        assert md[loc["start_char"]:loc["end_char"]] == quote, \
            f"{asset['asset_id']}: char span does not reproduce the quote"
        assert loc["start_line"] <= loc["end_line"] >= 1


def test_line_numbers_agree_with_char_offsets(manifest, md):
    lines = md.split("\n")
    starts = [0]
    for line in lines[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    for asset in manifest["assets"]:
        loc = asset["locator"]
        first = lines[loc["start_line"] - 1]
        assert first and (loc["quote"].split("\n")[0] in first), asset["asset_id"]
        assert starts[loc["start_line"] - 1] <= loc["start_char"] < starts[loc["start_line"] - 1] + len(first) + 1


def test_no_duplicate_asset_ids_and_count_consistency(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["counts"]["assets"] == len(ids)
    by_res = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert by_res == manifest["counts"]["by_resolution"]
    for key in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert manifest["counts"][key] == by_res.get(key, 0)


def test_no_claims_and_nothing_marked_verified(manifest, result):
    # registration package: claims=[] is the contract-sanctioned outcome
    assert manifest["claims"] == []
    assert result.get("claims", []) == []
    blob = json.dumps(manifest, ensure_ascii=False)
    assert "verified" not in blob.replace("unverified", "")


def test_declared_absent_is_backed_by_a_negative_scan(manifest, md):
    scan = manifest["counts"]["declared_absent_scan"]
    assert all(v["matches"] == 0 for v in scan.values())
    # the scan really is negative on this document
    assert re.search(r"\.(py|csv|dat|json|npz|nc|h5|hdf5|zip|tar|png|fig|xlsx)\b", md, re.I) is None


def test_encoding_damage_finding_is_reproducible(manifest, md):
    f1 = next(f for f in manifest["integrity_findings"] if f["id"] == "F1")
    assets = {a["asset_id"]: a for a in manifest["assets"]}
    quote = assets["A03"]["locator"]["quote"]
    seq = [ord(c) for c in quote if ord(c) < 32 and c != "\n"]
    assert seq == f1["observed"]["control_sequence"] == [12, 9, 9, 9]
    assert sorted(set(seq)) == f1["observed"]["control_codepoints"] == [9, 12]
    assert quote.count("2239218") == 2


def test_parameter_crosscheck_is_reproducible(manifest):
    f3 = next(f for f in manifest["integrity_findings"] if f["id"] == "F3")
    rv = f3["reported_vs_recomputed"]
    # D = E t^3 / (12 (1 - nu^2)) with E=9.0e9, t=0.5, nu=0.33
    d = 9.0e9 * 0.5 ** 3 / (12 * (1 - 0.33 ** 2))
    assert abs(d - rv["D_Nm"]["reported"]) / rv["D_Nm"]["reported"] < 1e-3
    w = 1.0e5 / (8 * (d * 1.0e4) ** 0.5)
    assert abs(w - rv["w0_m"]["reported"]) / rv["w0_m"]["reported"] < 1e-3
    assert rv["w0_m"]["rel_dev"] < 1e-3


def test_figure_payload_pinned_when_resolved(manifest):
    a10 = next(a for a in manifest["assets"] if a["asset_id"] == "A10")
    pl = a10.get("payload_locator")
    assert pl, "resolved figure must pin its payload"
    assert pl["http_status"] == 200 and pl["bytes"] > 0
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", pl["sha256"])