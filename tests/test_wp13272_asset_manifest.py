"""wp-13272-01 · acceptance tests for the 01-asset-registration package.

Run:  python3 -m pytest tests/test_wp13272_asset_manifest.py -q
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib

import jsonschema
import pytest

WT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = WT / "docs" / "kf" / "wp-13272-01"
SRC_DIR = WT / "work" / "wp-13272-01" / "source"
SCHEMA = WT / "schemas" / "kf_result.v1.schema.json"

CONTRACT_HASH = "sha256:75ed781cefac9fee890f493c256dec8aea2e70795eca9d7a8bbfef1af1bcce90"
CONTRACT_CHARS = 4537


@pytest.fixture(scope="module")
def md() -> str:
    return (SRC_DIR / "report_13272.md").read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((OUT_DIR / "asset_manifest.json").read_text())


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((OUT_DIR / "kf_result.json").read_text())


def _locator_failures(assets: list[dict], md: str) -> list[tuple]:
    bad = []
    for a in assets:
        for loc in a["locators"]:
            if loc.get("source_field") != "markdown":
                continue
            seg = md[loc["char_start"]:loc["char_end"]]
            if seg != loc["quote"] or md.find(loc["quote"]) != loc["char_start"]:
                bad.append((a["asset_id"], loc["quote"][:40]))
    return bad


def test_valid_json_and_schema(envelope):
    schema = json.loads(SCHEMA.read_text())
    jsonschema.validate(envelope, schema, format_checker=jsonschema.FormatChecker())
    assert envelope["package_id"] == "wp-13272-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "13272"
    assert "asset_manifest.json" in envelope["outputs"]


def test_source_hash_and_chars(md, manifest, envelope):
    recomputed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert recomputed == CONTRACT_HASH
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == CONTRACT_CHARS == len(md)
    assert manifest["source"]["hash_check"]["match"] is True


def test_all_markdown_locators_resolvable(md, manifest):
    assert _locator_failures(manifest["assets"], md) == []
    n = sum(1 for a in manifest["assets"] for l in a["locators"] if l.get("source_field") == "markdown")
    assert n >= 30, f"expected a full reference table, got {n} markdown locators"


def test_no_duplicate_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    for a in manifest["assets"]:
        assert a["status"] in ("resolved", "unresolved")
        if a["status"] == "unresolved":
            assert a.get("unresolved_reason"), a["asset_id"]


def test_negative_control_tampered_quote(md, manifest):
    """A tampered quote must be detected by the same check the acceptance gate uses."""
    tampered = copy.deepcopy(manifest)
    for a in tampered["assets"]:
        for loc in a["locators"]:
            if loc.get("source_field") == "markdown":
                loc["quote"] = loc["quote"][:-1] + ("X" if loc["quote"][-1] != "X" else "Y")
                break
        else:
            continue
        break
    assert _locator_failures(tampered["assets"], md), "tamper not detected — check is vacuous"


def test_negative_control_shifted_span(md, manifest):
    """A shifted char span (same quote, wrong offset) must be detected."""
    tampered = copy.deepcopy(manifest)
    for a in tampered["assets"]:
        for loc in a["locators"]:
            if loc.get("source_field") == "markdown":
                loc["char_start"] += 1
                loc["char_end"] += 1
                break
        else:
            continue
        break
    assert _locator_failures(tampered["assets"], md), "shift not detected — check is vacuous"


def test_manifest_reproducible_from_snapshot():
    """Offline re-run of the registration script must reproduce the manifest byte-for-byte."""
    import subprocess
    import sys

    before = (OUT_DIR / "asset_manifest.json").read_bytes()
    r = subprocess.run(
        [sys.executable, str(WT / "scripts" / "wp13272_register_assets.py"), "--offline"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    after = (OUT_DIR / "asset_manifest.json").read_bytes()
    assert before == after, "offline re-run changed the manifest"


def test_single_report_touched_and_claims_policy(manifest, envelope):
    assert manifest["scope"]["reports_touched"] == ["13272"]
    assert manifest["scope"]["registers_assets_only"] is True
    assert manifest["scope"]["extracts_claims"] is False
    assert envelope.get("claims", []) == []
    assert manifest["claims_policy"]["reason"].strip()
