"""Offline regression tests for KF work package wp-9632-01 (asset registration).

These tests need no network: they re-check the committed artefacts against the
committed byte copy of the source markdown (runs/wp-9632-01/source_9632.md), so
CI can prove the registration invariants after the fact. The live-API check is
`python3 scripts/kf_wp9632_01_register.py verify` (same six acceptance items,
plus a fresh GET of /tensor/reports/9632).
"""
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-9632-01"
MANIFEST = OUT / "asset_manifest.json"
ENVELOPE = OUT / "kf_result.json"
VERIFICATION = OUT / "verification.json"
SOURCE = ROOT / "runs" / "wp-9632-01" / "source_9632.md"

CONTRACT_SOURCE_HASH = "sha256:b2c5eb5dad0b6db25574338b37aa5be1c8fdf20bbc7d3c75640e1c1727756841"
CONTRACT_CHARS = 10749
CONTRACT_TITLE = "IN101-N07 冰脊固结热力学：龙骨大孔隙再冻结与固结度-阻力耦合"
CONTRACT_SCENARIO = "ice_ridge_consolidation"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source():
    return SOURCE.read_text(encoding="utf-8")


def test_contract_identity(manifest):
    src = manifest["source"]
    assert manifest["report_id"] == "9632"
    assert manifest["package_id"] == "wp-9632-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert src["uri"] == "tensor://reports/9632"
    assert src["field"] == "markdown"
    assert src["source_hash"] == CONTRACT_SOURCE_HASH
    assert src["hash_match"] is True
    assert src["chars"] == CONTRACT_CHARS
    assert src["title"] == CONTRACT_TITLE
    assert src["scenario_key"] == CONTRACT_SCENARIO


def test_source_copy_matches_contract_hash(source):
    import hashlib
    digest = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_SOURCE_HASH
    assert len(source) == CONTRACT_CHARS


def test_manifest_schema(manifest):
    schema = json.loads((ROOT / "schemas" /
                         "asset_manifest.v1.wp9632-01.schema.json").read_text())
    errors = sorted(Draft7Validator(schema).iter_errors(manifest), key=lambda e: list(e.path))
    assert not errors, ["/".join(map(str, e.path)) + ": " + e.message for e in errors]


def test_envelope_schema(envelope):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(envelope),
                    key=lambda e: list(e.path))
    assert not errors, ["/".join(map(str, e.path)) + ": " + e.message for e in errors]
    assert envelope["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert set(envelope["outputs"]) == {"asset_manifest.json"}
    # the envelope must carry the very manifest that lives on disk
    assert envelope["outputs"]["asset_manifest.json"] == json.loads(MANIFEST.read_text())


def test_locators_resolve_against_byte_copy(manifest, source):
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        if loc["method"] == "document":
            ok = (s == 0 and e == len(source) and loc["quote"] in source
                  and loc["start_line"] == 1
                  and loc["end_line"] == source.rstrip("\n").count("\n") + 1)
        else:
            ok = (0 <= s < e <= len(source) and source[s:e] == loc["quote"]
                  and loc["start_line"] == source.count("\n", 0, s) + 1
                  and loc["end_line"] == source.count("\n", 0, e - 1) + 1)
        if not ok:
            bad.append(a["asset_id"])
    assert not bad, bad


def test_no_duplicate_ids_and_unique_quotes(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    labels = [a["label"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert len(labels) == len(set(labels))
    assert all(a["locator"]["unique"] for a in manifest["assets"])


def test_claims_honest(manifest, envelope):
    # registration package: empty claims is the complete result, and nothing is
    # allowed to be marked verified (verification belongs to the platform gate)
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert manifest["integrity"]["no_verified_marks"] is True
    blob = MANIFEST.read_text() + ENVELOPE.read_text()
    assert '"verified"' not in blob


def test_resolution_classes_are_honest(manifest, source):
    """Only the source markdown itself may claim resolution in this worktree."""
    resolved = [a for a in manifest["assets"] if a["resolution"] == "resolved_in_source"]
    assert [a["asset_class"] for a in resolved] == ["report_markdown"]
    for a in manifest["assets"]:
        if a["resolution"] == "referenced_unresolved":
            assert a["resolution_check"]["result"] in ("unresolved", "absent")
            assert a["note"].strip()


def test_verification_recorded_six_passes():
    v = json.loads(VERIFICATION.read_text())
    assert v["total"] == 6 and v["passed"] == 6 and v["failed"] == 0
    assert {c["check_id"] for c in v["checks"]} == {
        "valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
        "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"}