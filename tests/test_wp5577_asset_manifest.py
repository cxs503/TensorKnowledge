"""wp-5577-01 acceptance tests (01-asset-registration, report_id=5577).

Run:  python3 -m pytest tests/test_wp5577_asset_manifest.py -q
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-5577-01"
MD = (PKG / "source" / "report_5577.md").read_text(encoding="utf-8")
CONTRACT_HASH = "sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8"
CONTRACT_CHARS = 3702


@pytest.fixture(scope="module")
def manifest():
    return json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def acceptance():
    return json.loads((PKG / "acceptance.json").read_text(encoding="utf-8"))


def test_source_hash_and_chars():
    h = hashlib.sha256(MD.encode("utf-8")).hexdigest()
    assert f"sha256:{h}" == CONTRACT_HASH
    assert len(MD) == CONTRACT_CHARS


def test_envelope_passes_schema(envelope):
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(envelope)
    assert envelope["package_id"] == "wp-5577-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "5577"
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert "asset_manifest.json" in envelope["outputs"]
    assert envelope["claims"] == []


def test_all_markdown_locators_verbatim(manifest):
    checked = 0
    for a in manifest["assets"]:
        for loc in a.get("locators", []):
            if loc.get("source_field") != "markdown":
                continue
            checked += 1
            assert MD[loc["char_start"]:loc["char_end"]] == loc["quote"], a["asset_id"]
    assert checked >= 17  # 1 source line + 16 declared-reference needles


def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids)) == manifest["asset_counts"]["total"]


def test_counts_consistent(manifest):
    by = {}
    for a in manifest["assets"]:
        by[a["status"]] = by.get(a["status"], 0) + 1
    assert manifest["asset_counts"]["by_status"] == by
    assert manifest["asset_counts"]["resolved"] == by.get("resolved", 0)
    assert manifest["asset_counts"]["unresolved"] == by.get("unresolved", 0)


def test_unresolved_have_reason(manifest):
    for a in manifest["assets"]:
        if a["status"] == "unresolved":
            assert a.get("unresolved_reason"), a["asset_id"]


def test_claims_empty_with_policy_reason(manifest, envelope):
    assert envelope["claims"] == []
    assert len(manifest["claims_policy"]["reason"]) >= 20


def test_scope_single_report(manifest):
    assert manifest["scope"]["reports_touched"] == ["5577"]
    assert manifest["scope"]["registers_assets_only"] is True
    assert manifest["scope"]["extracts_claims"] is False
    assert manifest["scope"]["classifies_report_type"] is False


def test_acceptance_all_pass(acceptance):
    assert acceptance["ok"] is True
    for name, ok in acceptance["summary"].items():
        assert ok is True, name


def test_negative_control_tampered_quote_detected():
    """A tampered quote or shifted offset must be detected (gate is not vacuous)."""
    m = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    a = next(x for x in m["assets"] if x["asset_id"] == "ast-5577-06")
    loc = a["locators"][0]
    bad = copy.deepcopy(loc)
    bad["quote"] = bad["quote"] + "X"
    assert MD[bad["char_start"]:bad["char_end"]] != bad["quote"]
    bad2 = copy.deepcopy(loc)
    bad2["char_start"] += 1
    bad2["char_end"] += 1
    assert MD[bad2["char_start"]:bad2["char_end"]] != bad2["quote"]


def test_negative_control_missing_needle_refused():
    """The register script must refuse to run when a needle is not verbatim."""
    code = (
        "import sys; sys.path.insert(0, %r)\n"
        "import scripts.wp5577_register_assets as R\n"
        "rec = R.fetch_offline()\n"
        "R.ASSET_PLAN = R.ASSET_PLAN + [('ast-5577-99','declared_artifact','x','nope','THIS_NEEDLE_DOES_NOT_EXIST_5577','n')]\n"
        "try:\n"
        "    R.build(rec, 'offline')\n"
        "    raise SystemExit('expected SystemExit')\n"
        "except SystemExit as e:\n"
        "    assert 'needle not found' in str(e)\n" % str(REPO)
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_offline_rerun_byte_identical():
    """Offline rerun reproduces asset_manifest.json byte-for-byte."""
    before = (PKG / "asset_manifest.json").read_bytes()
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "wp5577_register_assets.py"), "--offline"],
        capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    after = (PKG / "asset_manifest.json").read_bytes()
    assert before == after
