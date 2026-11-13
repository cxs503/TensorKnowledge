"""Offline acceptance tests for work package wp-9840-01 (01-asset-registration, report 9840).

These tests need no network: they run against the durable evidence under docs/wp-9840-01/
(mirrored byte-identically by scripts/kf_9840_durable.py), and they assert *invariants*
rather than merely exercising code:

  1. the frozen source markdown still hashes to the contract source_hash;
  2. every registered locator re-slices to its recorded quote and is unique in the source;
  3. the manifest and the result envelope satisfy their schemas;
  4. counts / ids / resolution bookkeeping is self-consistent (no duplicates, no orphans);
  5. the published report body carries exactly one fenced block and it parses to the envelope
     (so no source code fence leaks into the envelope and creates a second ```json);
  6. no claim is marked verified (the platform gate computes verification, not this package).
"""
import hashlib
import json
import pathlib
import re

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/wp-9840-01"
MANIFEST = DOC / "asset_manifest.json"
SOURCE = DOC / "source_report_9840.md"
ENVELOPE = DOC / "kf_result.wp-9840-01.json"
REPORT_MD = DOC / "KF-RESULT-wp-9840-01.md"
EXPECTED_HASH = "159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524"

pytestmark = pytest.mark.skipif(not MANIFEST.exists(), reason="wp-9840-01 artifacts not present")


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def source():
    return SOURCE.read_text()


@pytest.fixture(scope="module")
def envelope():
    return json.loads(ENVELOPE.read_text())


def test_source_hash_matches_contract(source):
    assert hashlib.sha256(source.encode()).hexdigest() == EXPECTED_HASH
    assert len(source) == 14740


def test_manifest_schema(manifest):
    schema = json.loads((ROOT / "schemas/asset_manifest.wp-9840-01.schema.json").read_text())
    jsonschema.validate(manifest, schema)


def test_envelope_schema(envelope):
    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text())
    jsonschema.validate(envelope, schema)


def test_envelope_provenance_hash(envelope):
    assert envelope["provenance"]["source_hash"] == "sha256:" + EXPECTED_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["package_id"] == "wp-9840-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "9840"


def test_every_locator_resolves_and_is_unique(manifest, source):
    failures = []
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["method"] == "char_span", (a["asset_id"], "no document-level asset by design")
        sliced = source[loc["start_char"]:loc["end_char"]]
        if sliced != loc["quote"]:
            failures.append((a["asset_id"], "re-slice != quote"))
        elif source.count(loc["quote"]) != 1:
            failures.append((a["asset_id"], "quote not unique"))
        elif not loc["unique"]:
            failures.append((a["asset_id"], "unique flag false"))
    assert failures == []


def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))


def test_counts_are_self_consistent(manifest):
    c, assets = manifest["counts"], manifest["assets"]
    assert c["assets"] == len(assets)
    for key in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert c[key] == sum(1 for a in assets if a["resolution"] == key), key
    assert sum(c["by_class"].values()) == len(assets)
    assert sum(c["by_resolution"].values()) == len(assets)


def test_claims_empty_but_every_asset_has_explicit_status(manifest):
    assert manifest["claims"] == []          # contract scope: register_assets only
    for a in manifest["assets"]:
        assert a["resolution"] in ("resolved_in_source", "referenced_unresolved", "declared_absent")
        assert a["resolution_check"]["result"] in ("resolved", "unresolved", "absent", "present")
    # task objective: report-type classification is out of scope -> no classification payload
    assert "report_type" not in manifest
    assert all(a["asset_class"] != "report_type" for a in manifest["assets"])


def test_no_verified_marker_in_manifest(manifest):
    blob = json.dumps(manifest, ensure_ascii=False)
    assert '"verified"' not in blob


def test_report_has_exactly_one_fenced_json_block_equal_to_envelope(envelope):
    md = REPORT_MD.read_text()
    assert md.startswith("# KF-RESULT wp-9840-01")
    assert md.count("```") == 2, "envelope must not leak the source's own code fences"
    blocks = re.findall(r"```(\w*)\n(.*?)```", md, re.S)
    assert [b[0] for b in blocks] == ["json"]
    assert json.loads(blocks[0][1]) == envelope


def test_report_is_six_section_and_tagged(manifest):
    md = REPORT_MD.read_text()
    sections = [ln for ln in md.split("\n") if ln.startswith("## ")]
    assert len(sections) == 6
    receipt = json.loads((DOC / "postcheck_publish.json").read_text())
    assert "kf-wp:wp-9840-01" in receipt["tags"]
    assert receipt["report_id"] == 14752 and receipt["verdict"] == "PASS"


def test_only_report_9840_is_referenced(manifest):
    assert manifest["report_id"] == "9840"
    assert manifest["source"]["uri"] == "tensor://reports/9840"
    assert manifest["source"]["hash"] == EXPECTED_HASH