#!/usr/bin/env python3
"""Offline acceptance tests for work package wp-8163-01 (01-asset-registration).

These re-derive the acceptance verdict from the committed artefacts without touching
the network, so CI (and any reviewer) can reproduce the checks the work package
claims to have passed:

    python3 scripts/kf/kf_wp8163_01_register.py all      # rebuild artefacts
    python3 scripts/kf/kf_wp8163_01_publish.py render     # re-render report.md
    pytest -q tests/test_kf_wp8163_01.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-8163-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
SOURCE = PKG / "source.md"
REPORT = PKG / "report.md"
VERIFICATION = PKG / "verification.json"

CONTRACT_HASH = "sha256:7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7"
CONTRACT_CHARS = 7785


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_source_identity_matches_contract(source: str) -> None:
    assert len(source) == CONTRACT_CHARS
    assert "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH


def test_envelope_is_schema_valid_and_hash_matches() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text())
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(env)
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert env["report_id"] == "8163"
    assert env["outputs"]["asset_manifest.json"] == json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_every_locator_resolves_uniquely_in_source(manifest: dict, source: str) -> None:
    for asset in manifest["assets"]:
        loc = asset["locator"]
        quote = loc["quote"]
        assert source.count(quote) == 1, "quote not unique: %s" % asset["asset_id"]
        if loc["method"] == "char_span":
            assert source[loc["start_char"] : loc["end_char"]] == quote
            assert source.count("\n", 0, loc["start_char"]) + 1 == loc["start_line"]
        else:
            assert (loc["start_char"], loc["end_char"]) == (0, len(source))
            assert source.startswith(quote)


def test_ids_unique_and_counts_consistent(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    counts = manifest["counts"]
    assert counts["assets"] == len(manifest["assets"])
    assert sum(counts["by_class"].values()) == counts["assets"]
    assert sum(counts["by_resolution"].values()) == counts["assets"]
    assert counts["by_resolution"].get("resolved_in_source", 0) == counts["resolved_in_source"]
    assert counts["by_resolution"].get("referenced_unresolved", 0) == counts["referenced_unresolved"]
    # every asset carries an explicit resolution + a locator method the schema allows
    for a in manifest["assets"]:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved", "declared_absent"}
        assert a["locator"]["method"] in {"char_span", "document"}
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent", "present"}


def test_no_asset_claims_verified_and_claims_are_empty(manifest: dict) -> None:
    assert manifest["claims"] == []
    flat = json.dumps(manifest, ensure_ascii=False)
    assert '"verified"' not in flat
    assert manifest["integrity"]["hash_matches_contract"] is True


def test_all_declared_paths_are_registered(manifest: dict, source: str) -> None:
    """Coverage: every path/embed/symbol the report declares has exactly one asset."""
    labels = {a["label"] for a in manifest["assets"]}
    labels |= {a["platform_figure_name"] for a in manifest["assets"] if a.get("platform_figure_name")}
    import re

    declared = set(re.findall(r"`([^`]+?\.(?:py|png|json|csv|h5|md))`", source))
    declared |= set(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", source))
    declared |= set(re.findall(r"`(artifacts/[^`]*/)`", source))
    assert declared, "enumeration must find the report's declared paths"
    assert declared <= labels, sorted(declared - labels)


def test_report_block_is_single_and_equal_to_envelope() -> None:
    body = REPORT.read_text(encoding="utf-8")
    assert body.count("```json") == 1
    assert body.count("```") == 2
    block = body.split("```json", 1)[1].rsplit("```", 1)[0]
    # order matters: `register.py all` refreshes the envelope timestamps, so report.md
    # must be re-rendered afterwards (`publish.py render`) before this can hold.
    assert json.loads(block) == json.loads(ENVELOPE.read_text(encoding="utf-8")), (
        "embedded result block drifted from kf_result.json -- re-run "
        "`python3 scripts/kf/kf_wp8163_01_register.py all && "
        "python3 scripts/kf/kf_wp8163_01_publish.py render`"
    )
    assert body.startswith("#")  # six-section body precedes the block


def test_verification_record_reports_all_pass() -> None:
    v = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    assert v["all_pass"] is True
    expected = {
        "valid_json",
        "schema_pass",
        "source_locator_resolvable",
        "source_hash_matches",
        "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status",
    }
    assert expected <= set(v["checks"])
    assert all(c["pass"] for c in v["checks"].values())
    assert v["coverage"]["pass"] is True