"""Offline re-verification of the wp-8037-01 asset manifest (report 8037).

These tests are the machine-checkable form of the work-package acceptance items:
they do NOT touch the network -- they read the committed byte-identical copy of the
report markdown (docs/kf/wp-8037-01/source_8037.md) and re-resolve every locator.

Run: python3 -m pytest tests/test_kf_wp8037_01_manifest.py -q
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-8037-01"
MANIFEST = OUT / "asset_manifest.json"
ENVELOPE = OUT / "kf_result.json"
SOURCE = OUT / "source_8037.md"
SCHEMA_LOCAL = ROOT / "schemas" / "asset_manifest.wp-8037-01.schema.json"
SCHEMA_ENVELOPE = ROOT / "schemas" / "kf_result.v1.schema.json"
CONTRACT_HASH = "sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0"
CONTRACT_CHARS = 1223

pytestmark = pytest.mark.skipif(
    not (MANIFEST.exists() and SOURCE.exists()),
    reason="wp-8037-01 artefacts not built (run scripts/kf_wp8037_01_register.py all)")


def _md() -> str:
    return SOURCE.read_bytes().decode("utf-8")


def _man() -> dict:
    return json.loads(MANIFEST.read_text("utf-8"))


def test_source_hash_matches_contract_and_manifest():
    live = "sha256:" + hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert live == CONTRACT_HASH
    assert _man()["source"]["hash"] == CONTRACT_HASH
    assert json.loads(ENVELOPE.read_text("utf-8"))["provenance"]["source_hash"] == CONTRACT_HASH
    assert len(_md()) == CONTRACT_CHARS


@pytest.mark.parametrize("asset_id", ["A%02d" % i for i in range(1, 23)])
def test_every_locator_resolves_verbatim(asset_id):
    md = _md()
    lines = md.split("\n")
    asset = next(a for a in _man()["assets"] if a["asset_id"] == asset_id)
    loc = asset["locator"]
    assert loc["quote"] in md, asset_id
    assert md.count(loc["quote"]) == 1, "%s quote is not unique" % asset_id
    if loc["method"] == "char_span":
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"]
        assert "\n".join(lines[loc["start_line"] - 1:loc["end_line"]]) == loc["quote"]
    else:
        assert loc["start_char"] == 0 and loc["end_char"] == len(md)
        assert loc["start_line"] == 1 and loc["end_line"] == len(lines)


def test_ids_unique_and_no_foreign_report_id():
    man = _man()
    ids = [a["asset_id"] for a in man["assets"]]
    assert len(ids) == len(set(ids))
    assert all(len(i) == 3 and i[0] == "A" and i[1:].isdigit() for i in ids)
    assert "tensor://reports/8037" in json.dumps(man)
    assert "tensor://reports/8038" not in json.dumps(man)


def test_claims_empty_with_explicit_reason():
    man = _man()
    assert man["claims"] == []
    assert man["claims_empty_reason"].strip()
    assert man["integrity"]["verification_status"] == "not_verified"


def test_resolution_classes_are_consistent_with_probes():
    """A resolved locator must not claim a failed probe, and an unresolved one must show it."""
    for a in _man()["assets"]:
        probe = a["resolution_check"].get("probe")
        if a["resolution"] == "referenced_unresolved":
            assert probe and probe["exists"] is False, a["asset_id"]
        if a["resolution"] == "declared_absent":
            assert a["resolution_check"]["result"] == "absent", a["asset_id"]


def test_schemas_validate():
    jsonschema = pytest.importorskip("jsonschema")
    man = _man()
    env = json.loads(ENVELOPE.read_text("utf-8"))
    jsonschema.validate(man, json.loads(SCHEMA_LOCAL.read_text("utf-8")))
    jsonschema.validate(env, json.loads(SCHEMA_ENVELOPE.read_text("utf-8")))
    assert "asset_manifest.json" in env["outputs"]


def test_result_report_carries_exactly_one_json_block():
    md = (OUT / "KF-RESULT-wp-8037-01.md").read_text("utf-8")
    assert md.count("```json") == 1
    body = md.split("```json", 1)[1].split("```", 1)[0]
    parsed = json.loads(body)
    assert parsed["package_id"] == "wp-8037-01"
    assert parsed["report_id"] == "8037"
    assert parsed["provenance"]["source_hash"] == CONTRACT_HASH