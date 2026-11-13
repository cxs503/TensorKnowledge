"""Invariant tests for work package wp-11924-01 (asset registration of report 11924).

Every check the acceptance list names is exercised twice: once on the real artifact (must pass) and at
least once on a deliberately mutated copy (must fail). Without the negative controls these tests would
only prove "the script ran", not that the gate is real.

Run: python3 -m pytest tests/test_kf_wp11924.py -q
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts/wp-11924-01/asset_manifest.json"
RESULT = ROOT / "runs/wp-11924-01/kf_result.wp-11924-01.json"
SCHEMA = ROOT / "schemas/asset_manifest.v1.generic.schema.json"
KF_SCHEMA = ROOT / "schemas/kf_result.v1.schema.json"
MD = ROOT / "runs/wp-11924-01/report_11924.md"
EXPECTED_HASH = "21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73"


def _load_verify():
    spec = importlib.util.spec_from_file_location("kf_verify_11924", ROOT / "scripts/kf_wp11924_01_verify.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V = _load_verify()


@pytest.fixture(scope="module")
def md() -> str:
    return MD.read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads(RESULT.read_text())


# --------------------------------------------------------------- positive direction
def test_source_hash_is_contract_hash(md):
    assert hashlib.sha256(md.encode()).hexdigest() == EXPECTED_HASH
    assert len(md) == 13138


def test_manifest_hash_and_envelope_agree(md, manifest, result):
    h = hashlib.sha256(md.encode()).hexdigest()
    assert manifest["source"]["hash"] == h
    assert result["provenance"]["source_hash"] == "sha256:" + h
    assert manifest["source"]["bytes_utf8"] == len(md.encode())


def test_all_locators_resolve(md, manifest):
    assert V.check_locators(md, manifest) == []


def test_asset_ids_unique_and_shaped(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(len(i) == 3 and i[0] == "A" and i[1:].isdigit() for i in ids)


def test_resolution_check_matches_declared_resolution(manifest):
    assert V.check_resolution_consistency(manifest) == []


def test_counts_are_derived_not_asserted(manifest):
    assert V.check_counts(manifest) == []


def test_claims_empty_and_policy_stated(manifest):
    assert manifest["claims"] == []
    assert "claim" in manifest["claims_note"]


def test_schema_validates(manifest, result):
    import jsonschema
    jsonschema.validate(manifest, json.loads(SCHEMA.read_text()))
    jsonschema.validate(result, json.loads(KF_SCHEMA.read_text()))


def test_envelope_has_no_verified_marker(manifest, result):
    assert V.check_verified_markers(manifest) == []
    assert V.check_verified_markers(result) == []
    assert manifest["integrity"]["verification_status"] == "not_verified"


def test_scope_is_report_11924_only(manifest, result):
    assert V.check_scope_isolation(manifest, result) == []


def test_artifact_hash_matches_envelope(result):
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == \
        result["outputs"]["asset_manifest.json"]["artifact_sha256"]


def test_every_asset_carries_a_locator_quote_from_source(md, manifest):
    for a in manifest["assets"]:
        assert a["locator"]["quote"]
        assert a["locator"]["quote"] in md            # verbatim substring of the source
        assert a["note"] and a["label"] and a["asset_class"]


# --------------------------------------------------------------- negative controls
def test_negative_tampered_quote_is_caught(md, manifest):
    m = copy.deepcopy(manifest)
    a = next(x for x in m["assets"] if x["asset_id"] == "A09")   # quote carries cond(J) = 9.063
    a["locator"]["quote"] = a["locator"]["quote"].replace("9.063", "9.064")
    bad = V.check_locators(md, m)
    assert ("A09", "slice != quote") in bad


def test_negative_shifted_span_is_caught(md, manifest):
    m = copy.deepcopy(manifest)
    a = next(x for x in m["assets"] if x["asset_id"] == "A16")
    a["locator"]["start_char"] += 1
    bad = dict(V.check_locators(md, m))
    assert "A16" in bad


def test_negative_non_unique_quote_is_caught(md, manifest):
    m = copy.deepcopy(manifest)
    a = next(x for x in m["assets"] if x["asset_id"] == "A02")
    frag = "|---|---|"                                 # table separator, occurs many times
    idx = md.index(frag)
    a["locator"].update(start_char=idx, end_char=idx + len(frag), quote=frag, unique=True,
                        start_line=md.count("\n", 0, idx), end_line=md.count("\n", 0, idx + len(frag)))
    bad = dict(V.check_locators(md, m))
    assert "A02" in bad and "occurs" in bad["A02"]


def test_negative_false_line_number_is_caught(md, manifest):
    m = copy.deepcopy(manifest)
    a = next(x for x in m["assets"] if x["asset_id"] == "A19")
    a["locator"]["start_line"] += 3
    bad = dict(V.check_locators(md, m))
    assert "A19" in bad and "start_line" in bad["A19"]


def test_negative_lying_resolution_is_caught(manifest):
    m = copy.deepcopy(manifest)
    a = next(x for x in m["assets"] if x["asset_id"] == "A36")   # external module, unresolved
    a["resolution"] = "resolved_in_source"                        # lie: claim it resolved in source
    bad = V.check_resolution_consistency(m)
    assert any(b[0] == "A36" for b in bad)


def test_negative_duplicate_asset_id_is_caught(manifest):
    m = copy.deepcopy(manifest)
    m["assets"][1]["asset_id"] = m["assets"][0]["asset_id"]
    assert V.check_duplicate_ids(m)


def test_negative_counts_mutation_is_caught(manifest):
    m = copy.deepcopy(manifest)
    m["counts"]["assets"] += 1
    assert V.check_counts(m)


def test_negative_claim_without_evidence_is_caught(manifest):
    m = copy.deepcopy(manifest)
    m["claims"] = [{"claim_id": "C01", "text": "an unsupported assertion"}]
    assert V.check_claims(m["claims"]) == ["C01"]


def test_negative_verified_marker_is_caught(manifest):
    m = copy.deepcopy(manifest)
    m["integrity"]["verified"] = True
    assert V.check_verified_markers(m)


def test_negative_wrong_report_id_is_caught(manifest, result):
    m, r = copy.deepcopy(manifest), copy.deepcopy(result)
    m["report_id"] = "11925"
    assert V.check_scope_isolation(m, r)


def test_negative_schema_rejects_bad_resolution(manifest):
    import jsonschema
    m = copy.deepcopy(manifest)
    m["assets"][0]["resolution"] = "maybe"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(m, json.loads(SCHEMA.read_text()))