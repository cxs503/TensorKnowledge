"""Offline acceptance tests for KF work package wp-11267-01 (report 11267 asset registration).

These tests need no network: they re-check the committed artefacts against the committed
source snapshot (runs/wp-11267-01/source_11267.md) and against the work-package contract
constants. Run with:

    python3 -m pytest tests/test_kf_wp1126701_asset_manifest.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-11267-01"
MANIFEST = PKG / "asset_manifest.json"
SCHEMA = PKG / "asset_manifest.schema.json"
ENVELOPE = PKG / "kf_result.json"
VERIFICATION = PKG / "verification.json"
SOURCE = ROOT / "runs" / "wp-11267-01" / "source_11267.md"
REPORT_MD = ROOT / "docs" / "kf_result_wp-11267-01.md"

CONTRACT_HASH = "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f"
CONTRACT_CHARS = 7482
CONTRACT_TITLE = ("TensorPhysics: MPI 域分解并行 FEM 基础设施与强/弱扩展验证 "
                  "(p284w3-n04)")
CONTRACT_SCENARIO = "p284w3-n04-fem-mpi-parallel"


def _load(p: Path):
    assert p.exists(), "missing artefact: %s" % p
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest():
    return _load(MANIFEST)


@pytest.fixture(scope="module")
def envelope():
    return _load(ENVELOPE)


@pytest.fixture(scope="module")
def source():
    assert SOURCE.exists(), "source snapshot missing: %s" % SOURCE
    return SOURCE.read_text(encoding="utf-8")


def test_source_hash_and_length_match_contract(source):
    digest = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert len(source) == CONTRACT_CHARS


def test_manifest_source_block_matches_contract(manifest):
    src = manifest["source"]
    assert manifest["package_id"] == "wp-11267-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "11267"
    assert src["uri"] == "tensor://reports/11267"
    assert src["field"] == "markdown"
    assert src["hash"] == CONTRACT_HASH == src["contract_hash"]
    assert src["hash_matches_contract"] is True
    assert src["chars"] == CONTRACT_CHARS
    assert src["title"] == CONTRACT_TITLE
    assert src["scenario_key"] == CONTRACT_SCENARIO


def test_manifest_validates_against_committed_schema(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMA)
    jsonschema.Draft7Validator(schema).validate(manifest)


def test_envelope_validates_against_repo_schema_and_carries_manifest(envelope, manifest):
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(ROOT / "schemas" / "kf_result.v1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(envelope)
    assert envelope["report_id"] == "11267"
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["outputs"]["asset_manifest.json"] == manifest


def test_every_locator_resolves_verbatim(manifest, source):
    checked = 0
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            assert source[loc["start_char"]:loc["end_char"]] == source
        for entry in a.get("all_locators") or []:
            checked += 1
            q = entry["quote"]
            assert q in source, "%s: quote not in source" % a["asset_id"]
            assert source[entry["start_char"]:entry["end_char"]] == q, (
                "%s: char span does not equal the quote" % a["asset_id"])
            assert entry["start_line"] if "start_line" in entry else entry["line"] >= 1
    assert checked >= len(manifest["assets"]), "fewer locators than assets"


def test_locator_line_numbers_are_consistent(manifest, source):
    lines = source.split("\n")
    for a in manifest["assets"]:
        if a["locator"]["method"] != "char_span":
            continue
        start = a["locator"]["start_char"]
        recomputed = source.count("\n", 0, start) + 1
        assert recomputed == a["locator"]["start_line"], a["asset_id"]
        q = a["locator"]["quote"]
        assert q in lines[recomputed - 1], "%s: quote not on its declared line" % a["asset_id"]


def test_asset_ids_and_names_are_unique(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    names = [(a["asset_class"], a["name"]) for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert len(names) == len(set(names))
    assert manifest["id_integrity"]["unique"] is True
    assert all(re.match(r"^A[0-9]{2}$", i) for i in ids)


def test_claims_are_empty_and_reason_recorded(manifest):
    assert manifest["claims"] == []
    assert manifest["claims_empty_reason"].strip()
    assert "verified" not in json.dumps(manifest["claims"]).lower()


def test_counts_are_self_consistent(manifest):
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    assert sum(c["by_resolution"].values()) == c["assets"]
    assert sum(c["by_class"].values()) == c["assets"]
    assert (c["resolved_in_source"] + c["referenced_unresolved"] + c["declared_absent"]
            == c["assets"])
    assert len(manifest["unresolved"]) == (c["referenced_unresolved"] + c["declared_absent"])


def test_declared_absent_assets_carry_no_payload_claim(manifest):
    for a in manifest["assets"]:
        if a["resolution"] == "declared_absent":
            assert a["resolution_check"]["result"] == "absent"
            assert "NOT a claim" in a["note"]


def test_figure_assets_record_payload_hash_when_resolved(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure_artifact"]
    assert figs
    for a in figs:
        if a["resolution"] == "resolved_in_source":
            assert re.match(r"^sha256:[0-9a-f]{64}$", a["resolution_check"]["payload_sha256"])
            assert a["resolution_check"]["png_magic"] is True


def test_verification_report_is_all_pass(manifest):
    ver = _load(VERIFICATION)
    assert ver["gate_verdict"] == "pass"
    assert ver["summary"]["fail"] == 0
    assert ver["summary"]["acceptance_pass"] == ver["summary"]["acceptance_total"] == 6


def test_report_markdown_has_exactly_one_json_block_that_is_the_envelope(envelope):
    md = REPORT_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\s*(.*?)```", md, re.S)
    assert len(blocks) == 1, "the KF result block must be the only json block"
    assert json.loads(blocks[0]) == envelope
    assert md.splitlines()[0].lstrip("# ").strip() == "KF-RESULT wp-11267-01"


def test_no_other_report_id_is_referenced(manifest):
    blob = json.dumps(manifest, ensure_ascii=False)
    ids = set(re.findall(r"tensor://reports/(\d+)", blob))
    assert ids <= {"11267"}, "only report 11267 may be registered by this package"