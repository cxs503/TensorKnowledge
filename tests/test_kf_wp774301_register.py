"""Acceptance tests for KF work package wp-7743-01 (task_type 01-asset-registration).

Two layers:

  * offline invariants (always run): JSON validity, schema conformance (kf_result.v1 envelope +
    asset_manifest.v1.pattern), id uniqueness, empty-claims discipline. These are the invariants
    the local `verify` sub-command asserts, re-checked here so a regression cannot pass silently.
  * live locator re-resolution (needs the platform API): every asset locator quote must still be
    a byte-exact slice of the *live* report markdown at the recorded char span, and the live
    sha256 must equal the contract hash. Skipped with an explicit reason when the API is
    unreachable -- skipped is reported as not_run, never as passed.

A negative control (`test_negative_control_*`) proves the locator check is not vacuous: shifting
one span by a single character must be detected.
"""
from __future__ import annotations

import json
import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "docs" / "kf" / "wp-7743-01"
MANIFEST_PATH = PKG_DIR / "asset_manifest.json"
ENVELOPE_PATH = PKG_DIR / "kf_result.json"
MANIFEST_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.pattern.json"
RESULT_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"

CONTRACT_SOURCE_HASH = "sha256:2db8e0192df29ddfed091f81cdf35c5f128166ab8966c45298f354dd9a15e21a"
CONTRACT_CHARS = 6520
REPORT_ID = "7743"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE_PATH.read_text())


# ----------------------------------------------------------------- offline layer
def test_files_exist_and_parse(manifest, envelope):
    assert manifest["package_id"] == "wp-7743-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert envelope["package_id"] == manifest["package_id"]
    assert envelope["report_id"] == manifest["report_id"] == REPORT_ID


def test_kf_result_envelope_conforms_to_schema(envelope):
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(json.loads(RESULT_SCHEMA.read_text()))
    errors = sorted(validator.iter_errors(envelope), key=lambda e: list(e.path))
    assert not errors, [e.message for e in errors]


def test_manifest_conforms_to_schema(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft7Validator(json.loads(MANIFEST_SCHEMA.read_text()))
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))
    assert not errors, [e.message for e in errors]


def test_contract_identity_bindings(manifest, envelope):
    src = manifest["source"]
    assert manifest["report_id"] == REPORT_ID
    assert src["source_hash"] == CONTRACT_SOURCE_HASH
    assert envelope["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH
    assert src["contract_source_hash"] == CONTRACT_SOURCE_HASH
    assert src["hash_matches_contract"] is True
    assert src["chars"] == CONTRACT_CHARS and src["chars_matches_contract"] is True
    assert src["scenario_matches_contract"] is True
    assert src["title_matches_contract"] is True
    assert len(src["hash"]) == 64 and all(c in "0123456789abcdef" for c in src["hash"])


def test_no_duplicate_asset_ids_or_keys(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    keys = [(a["asset_class"], a["ref_key"]) for a in manifest["assets"]]
    assert len(set(ids)) == len(ids), [i for i in ids if ids.count(i) > 1]
    assert len(set(keys)) == len(keys), [k for k in keys if keys.count(k) > 1]


def test_every_asset_is_discriminated(manifest):
    """A registration asset must either resolve, or say why not, or be declared absent."""
    for a in manifest["assets"]:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved",
                                   "declared_absent"}
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent", "present"}
        assert a["resolution_check"]["check"], a["asset_id"]
        if a["resolution"] != "resolved_in_source":
            assert a["note"], "unresolved/absent asset must carry a note: %s" % a["asset_id"]


def test_claims_discipline(manifest, envelope):
    """objective.classify_report_type=false -> no forced claims, but the empty array is explained."""
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert manifest["claims_empty_reason"].strip()
    for c in manifest["claims"] + envelope["claims"]:
        assert c.get("evidence") or c.get("unresolved_reason") or c.get("status")


# ---------------------------------------------------- locator re-resolution layer
def _live_markdown() -> str:
    import urllib.request

    base = os.environ.get("TENSOR_API_BASE")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        pytest.skip("not_run: TENSOR_API_BASE/TENSOR_AGENT_USER/TENSOR_AGENT_PASS absent")
    try:
        req = urllib.request.Request(
            base.rstrip("/") + "/auth/login",
            data=json.dumps({"username": user, "password": pwd}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode())["access_token"]
        req = urllib.request.Request(
            base.rstrip("/") + "/tensor/reports/" + REPORT_ID,
            headers={"Authorization": "Bearer " + tok})
        with urllib.request.urlopen(req, timeout=30) as r:
            rec = json.loads(r.read().decode())
    except Exception as exc:  # network/permission trouble is not_run, not a pass
        pytest.skip("not_run: platform API unreachable (%s)" % exc)
    return (rec.get("data") or rec).get("markdown") or ""


def _check_locators(md: str, assets) -> list[str]:
    bad = []
    for a in assets:
        loc = a["locator"]
        if loc["method"] == "document":
            if (loc["start_char"], loc["end_char"]) != (0, len(md)):
                bad.append(a["asset_id"] + ":document-span")
        elif md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            bad.append(a["asset_id"])
        for k, o in enumerate(a["occurrences"]):
            if md[o["start_char"]:o["end_char"]] != o["quote"]:
                bad.append("%s:occurrence%d" % (a["asset_id"], k))
    return bad


def test_locators_resolve_against_live_markdown(manifest):
    import hashlib

    md = _live_markdown()
    assert "sha256:" + hashlib.sha256(md.encode()).hexdigest() == CONTRACT_SOURCE_HASH
    assert len(md) == CONTRACT_CHARS
    assert _check_locators(md, manifest["assets"]) == []


def test_negative_control_shifted_span_is_detected(manifest):
    """Corrupting a locator must be caught -- otherwise the check above is vacuous."""
    import copy

    md = "prefix " + "A" * 20 + " suffix"
    assets = [{"asset_id": "N01",
               "locator": {"method": "char_span", "start_char": 7, "end_char": 27,
                           "quote": "A" * 20},
               "occurrences": []}]
    assert _check_locators(md, assets) == []
    broken = copy.deepcopy(assets)
    broken[0]["locator"]["start_char"] += 1
    assert _check_locators(md, broken) == ["N01"]
    quotes_ok = copy.deepcopy(assets)
    quotes_ok[0]["locator"]["quote"] = "A" * 19 + "B"
    assert _check_locators(md, quotes_ok) == ["N01"]