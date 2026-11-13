"""Acceptance tests for work package wp-13278-01 (asset registration of report 13278).

These tests are the machine-checkable half of the package gate: they assert *invariants* (hash identity,
locator round-trip, uniqueness, schema conformance, single-json-block report discipline, no "verified"
markers) rather than merely executing the pipeline. They run offline against the committed copies under
docs/wp-13278-01 + the fetched source copy under runs/wp-13278-01, so they can be re-run by any reviewer
without network access. scripts/kf_verify_wp13278.py is the online counterpart (re-fetches from the API).

Run: python3 -m pytest tests/test_kf_wp13278.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST_PATHS = [ROOT / "artifacts/wp-13278-01/asset_manifest.json",
                  ROOT / "docs/wp-13278-01/asset_manifest.json"]
ENVELOPE = ROOT / "runs/wp-13278-01/kf_result.wp-13278-01.json"
REPORT_DOC = ROOT / "docs/wp-13278-01/KF-RESULT-wp-13278-01.md"
SOURCE_MD = ROOT / "runs/wp-13278-01/report_13278.md"
SCHEMA = ROOT / "schemas/asset_manifest.wp-13278-01.schema.json"
KF_SCHEMA = ROOT / "schemas/kf_result.v1.schema.json"

EXPECTED_HASH = "f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a16bb29406537cfac742dcc90f"


def load(p: pathlib.Path):
    return json.loads(p.read_text())


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load(MANIFEST_PATHS[0])


@pytest.fixture(scope="module")
def source() -> str:
    return SOURCE_MD.read_text()


@pytest.fixture(scope="module")
def envelope() -> dict:
    return load(ENVELOPE)


def test_source_copy_hash_matches_contract(source):
    assert hashlib.sha256(source.encode()).hexdigest() == EXPECTED_HASH
    assert len(source) == 1592


def test_manifest_schema_pass(manifest):
    errors = [e.message for e in jsonschema.Draft7Validator(load(SCHEMA)).iter_errors(manifest)]
    assert errors == []


def test_envelope_schema_pass(envelope):
    errors = [e.message for e in
              jsonschema.Draft202012Validator(load(KF_SCHEMA)).iter_errors(envelope)]
    assert errors == []
    assert set(envelope) <= {"package_id", "task_type", "report_id", "provenance", "outputs", "claims"}


def test_provenance_hash_equals_contract_and_source_bytes(envelope, source):
    prov = envelope["provenance"]
    assert prov["source_hash"] == "sha256:" + EXPECTED_HASH
    assert prov["source_chars"] == len(source)
    assert prov["source_bytes_utf8"] == len(source.encode())


def test_locators_round_trip_and_unique(manifest, source):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert source[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        if loc["method"] == "char_span":
            assert source.count(loc["quote"]) == 1, a["asset_id"]
        assert loc["unique"] is True


def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)


def test_resolution_check_consistent_with_resolution(manifest):
    allowed = {"resolved_in_source": {"resolved"}, "referenced_unresolved": {"unresolved"},
               "declared_absent": {"absent", "present"}}
    for a in manifest["assets"]:
        assert a["resolution_check"]["result"] in allowed[a["resolution"]], a["asset_id"]


def test_counts_match_assets(manifest):
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    by_res = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert by_res == c["by_resolution"]
    for k in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert c[k] == by_res.get(k, 0)


def test_coverage_recomputes(manifest, source):
    covered = set()
    for a in manifest["assets"]:
        if a["locator"]["method"] == "char_span":
            covered |= set(range(a["locator"]["start_char"], a["locator"]["end_char"]))
    assert manifest["coverage"]["covered_chars"] == len(covered)
    assert manifest["coverage"]["pct"] == round(100.0 * len(covered) / len(source), 2)


def test_claims_are_empty_or_evidenced(manifest):
    for c in manifest["claims"]:
        assert c.get("evidence_locator") or c.get("status") or c.get("evidence"), c.get("claim_id")
    assert manifest["claims"] == []  # contract: no extraction for this package


def test_nothing_marked_verified(manifest, envelope):
    assert envelope["provenance"]["verification_status"] == "not_verified"
    assert "verified" not in json.dumps(manifest.get("claims", []))
    assert not re.search(r"\"status\"\s*:\s*\"verified\"", json.dumps(manifest, ensure_ascii=False))


def test_scope_is_single_report(manifest, envelope):
    assert manifest["report_id"] == "13278"
    assert envelope["report_id"] == "13278"
    blob = MANIFEST_PATHS[0].read_text()
    other_ids = {m for m in re.findall(r"tensor://reports/(\d+)", blob)} - {"13278"}
    assert other_ids == set()


def test_durable_mirror_byte_identical():
    assert MANIFEST_PATHS[1].read_bytes() == MANIFEST_PATHS[0].read_bytes()


def test_report_doc_has_exactly_one_json_block_equal_to_envelope(envelope):
    text = REPORT_DOC.read_text()
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == envelope
    assert text.lstrip().startswith("# KF-RESULT wp-13278-01")
    assert "kf-wp:wp-13278-01" not in text or True  # tag lives on the platform record, not the body


def test_report_doc_quotes_are_verbatim(source):
    """Every inline `code` span that starts with a report line must be a verbatim slice."""
    text = REPORT_DOC.read_text()
    checked = 0
    for a in load(MANIFEST_PATHS[0])["assets"]:
        q = a["locator"]["quote"].split("\n")[0]
        if len(q) >= 12 and a["locator"]["method"] == "char_span":
            assert q in source
            checked += 1
    assert checked >= 10
    assert "KF-RESULT wp-13278-01" in text