"""Machine checks for KF work package wp-9083-01 (asset registration, report 9083).

Offline: reads only artifacts/, runs/, docs/ and the byte-exact source snapshot,
so the upstream markdown hash is re-verified without the network or the DB.

Run: python3 -m pytest tests/test_kf_wp_9083_01.py -q
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import re

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "artifacts" / "kf" / "wp-9083-01"
RUN = ROOT / "runs" / "kf" / "wp-9083-01"
DOC = ROOT / "docs" / "kf" / "wp-9083-01"

CONTRACT_HASH = "345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8"
CONTRACT_CHARS = 258


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads((PKG / "kf_result.json").read_text())


@pytest.fixture(scope="module")
def manifest(result) -> dict:
    return result["outputs"]["asset_manifest.json"]


@pytest.fixture(scope="module")
def runlog() -> dict:
    return json.loads((RUN / "registration_run.json").read_text())


@pytest.fixture(scope="module")
def md() -> str:
    return (RUN / "source_markdown.snapshot.md").read_text()


# ------------------------------------------------------------- envelopes ----
def test_kf_result_envelope_schema(result):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.validate(result, schema)
    assert result["package_id"] == "wp-9083-01"
    assert result["task_type"] == "01-asset-registration"
    assert result["report_id"] == "9083"
    assert set(result["outputs"]) == {"asset_manifest.json"}


def test_asset_manifest_schema(manifest):
    schema = json.loads((ROOT / "schemas" / "asset_manifest.v1.schema.json").read_text())
    schema = copy.deepcopy(schema)
    # upstream file pins another package's consts; rebind to this package
    schema["properties"]["package_id"]["const"] = "wp-9083-01"
    schema["properties"]["report_id"]["const"] = "9083"
    schema["properties"]["task_type"]["const"] = "01-asset-registration"
    schema["properties"]["source"]["properties"]["uri"]["const"] = "tensor://reports/9083"
    jsonschema.validate(manifest, schema)


# ------------------------------------------------------------ hash / size ---
def test_source_hash_matches_contract(manifest, result, md):
    local = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert local == CONTRACT_HASH, "snapshot is not the contracted markdown bytes"
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["hash_alg"] == "sha256"
    assert result["provenance"]["source_hash"] == f"sha256:{CONTRACT_HASH}"
    assert manifest["integrity"]["hash_matches_contract"] is True


def test_source_size_matches_contract(manifest, md):
    assert len(md) == CONTRACT_CHARS == manifest["source"]["chars"]
    assert len(md.encode("utf-8")) == manifest["source"]["bytes_utf8"]
    assert manifest["source"]["field"] == "markdown"
    assert manifest["source"]["uri"] == "tensor://reports/9083"


# --------------------------------------------------------------- locators ---
def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids)) == manifest["counts"]["assets"]


def test_every_locator_resolves_once(manifest, md):
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        assert quote, a["asset_id"]
        assert md.count(quote) == 1, f"{a['asset_id']} quote not unique in markdown"
        assert md[loc["start_char"]:loc["end_char"]] == quote, a["asset_id"]
        assert loc["start_line"] == md.count("\n", 0, loc["start_char"]) + 1
        assert loc["end_line"] == md.count("\n", 0, loc["end_char"] - 1) + 1
        assert loc["unique"] is True


def test_every_asset_has_resolution_and_check(manifest):
    for a in manifest["assets"]:
        assert a["resolution"] in {
            "resolved_in_source",
            "referenced_unresolved",
            "declared_absent",
        }
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent", "present"}
        assert a["resolution_check"]["check"]


# ------------------------------------------------- declarations vs bytes -----
def test_declared_figures_are_registered_unresolved(manifest, runlog, md):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "declared_figure"]
    declared = manifest["source"]["platform_figures"]
    assert len(figs) == len(declared) == manifest["counts"]["figures_declared"] == 5
    probes = {p["figure_name"]: p for p in runlog["figure_probes"]}
    for fig, decl in zip(figs, declared):
        assert fig["label"] == decl["name"]
        assert fig["resolution"] == "referenced_unresolved"
        # no bytes: platform figure endpoint answered 404 and the name is not in the markdown
        assert probes[decl["name"]]["retrievable"] is False
        assert probes[decl["name"]]["http_status"] == 404
        assert fig["declaration_source"]["verbatim"]["name"] == decl["name"]
        assert fig["declaration_source"]["in_markdown"] is False
        assert decl["name"] not in md
    assert manifest["counts"]["figures_retrievable"] == 0
    assert manifest["counts"]["referenced_unresolved"] == len(figs)


def test_no_claims_and_nothing_marked_verified(result, manifest):
    assert result["claims"] == []
    assert manifest["claims"] == []
    blob = json.dumps(result).lower()
    assert '"verified"' not in blob
    assert manifest["integrity"]["no_claim_verification"]


def test_only_report_9083_is_touched(manifest, result, runlog):
    assert manifest["report_id"] == result["report_id"] == runlog["report_id"] == "9083"
    assert manifest["source"]["uri"].endswith("/9083")


# ------------------------------------------------------- delivery channel ---
def test_report_has_single_json_block_equal_to_result(result):
    text = (DOC / "REPORT.md").read_text()
    assert text.count("```") == 2, "report must contain exactly one fenced block"
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == result
    assert text.splitlines()[0] == "# KF-RESULT wp-9083-01 — 资产登记（report_id=9083）"
    assert "kf-wp:wp-9083-01" in text


def test_tracked_copies_match_artifacts(result, manifest):
    """artifacts/ is gitignored, so git-tracked copies live in docs/; they must not drift."""
    assert json.loads((DOC / "kf_result.json").read_text()) == result
    assert json.loads((DOC / "asset_manifest.json").read_text()) == manifest


def test_report_has_six_sections_and_repro_cmd():
    text = (DOC / "REPORT.md").read_text()
    for marker in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert marker in text, marker
    assert "scripts/kf_register_9083.py" in text
    assert "{{" not in text, "unsubstituted template placeholder"