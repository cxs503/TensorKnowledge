"""Invariant tests for work package wp-9947-01 (asset registration of report 9947).

Every acceptance item is asserted on the real artifact; each locator/hash/id check additionally gets a
negative control on a tampered deep copy, so the test proves the check can fail rather than merely
executing code. Schema tests also pin the cross-package guarantee: the generalized
schemas/asset_manifest.v1.schema.json must keep validating the committed wp-448-01 manifest.

Run: pytest -q tests/test_kf_wp9947.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import re
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kf_verify_9947 as kv  # noqa: E402

MANIFEST_PATH = ROOT / "artifacts/wp-9947-01/asset_manifest.json"
MIRROR_PATH = ROOT / "docs/wp-9947-01/asset_manifest.json"
SCHEMA_PATH = ROOT / "schemas/asset_manifest.v1.schema.json"
RESULT_PATH = ROOT / "runs/wp-9947-01/kf_result.wp-9947-01.json"
MD_PATH = ROOT / "runs/wp-9947-01/report_9947.md"
CONTRACT_HASH = "c9857b84a9ea71ea174f3392d34e8e61403202ee154fdab059c4e9abd83fc0bf"


@pytest.fixture(scope="module")
def md() -> str:
    return MD_PATH.read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


# ---------------------------------------------------------------- source identity
def test_source_hash_matches_contract_and_local_copy(md, manifest):
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == len(md) == 616
    assert manifest["source"]["bytes_utf8"] == len(md.encode())


def test_result_provenance_hash_matches_markdown(manifest):
    result = json.loads(RESULT_PATH.read_text())
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert result["report_id"] == "9947" and result["package_id"] == "wp-9947-01"
    assert result["task_type"] == "01-asset-registration"


def test_envelope_forbids_verified_claims():
    result = json.loads(RESULT_PATH.read_text())
    assert result["provenance"]["verification_status"] == "not_verified"
    assert result["claims"] == []


# ---------------------------------------------------------------- schema gate
def test_manifest_validates_against_local_schema(manifest, schema):
    jsonschema.validate(manifest, schema)


def test_schema_still_validates_wp448_manifest(schema):
    """Generalizing const->pattern must not break the previously accepted package."""
    other = ROOT / "docs/wp-448-01/asset_manifest.json"
    if not other.exists():  # pragma: no cover - only when docs mirror is absent from the checkout
        pytest.skip("wp-448-01 mirror not present")
    jsonschema.validate(json.loads(other.read_text()), schema)


def test_schema_rejects_wrong_package_and_report_ids(schema, manifest):
    for field, bad in (("package_id", "wp-9947"), ("report_id", 9947),
                       ("report_id", "wp-9947-01")):
        broken = copy.deepcopy(manifest)
        broken[field] = bad
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(broken, schema)


def test_schema_rejects_wrong_source_uri(schema, manifest):
    broken = copy.deepcopy(manifest)
    broken["source"]["uri"] = "tensor://reports/999999x"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(broken, schema)


# ---------------------------------------------------------------- locators
def test_every_locator_reresolves_uniquely(md, manifest):
    assert kv.check_locators(md, manifest) == []


def test_every_quote_is_a_verbatim_substring_of_the_markdown(md, manifest):
    for a in manifest["assets"]:
        assert a["locator"]["quote"] in md, a["asset_id"]


def test_locator_check_detects_tampered_quote(md, manifest):
    tampered = copy.deepcopy(manifest)
    target = next(a for a in tampered["assets"] if a["asset_id"] == "A07")
    target["locator"]["quote"] = target["locator"]["quote"].replace("<5%", "<4%")
    bad = kv.check_locators(md, tampered)
    assert any(asset == "A07" for asset, _ in bad)


def test_locator_check_detects_shifted_span(md, manifest):
    tampered = copy.deepcopy(manifest)
    target = next(a for a in tampered["assets"] if a["asset_id"] == "A09")
    target["locator"]["start_char"] += 1
    assert any(asset == "A09" for asset, _ in kv.check_locators(md, tampered))


def test_locator_check_detects_resolution_mismatch(md, manifest):
    tampered = copy.deepcopy(manifest)
    target = next(a for a in tampered["assets"] if a["asset_id"] == "A03")
    target["resolution"] = "resolved_in_source"
    assert any(asset == "A03" and why.startswith("resolution_check_mismatch")
               for asset, why in kv.check_locators(md, tampered))


# ---------------------------------------------------------------- ids / counts / claims
def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))


def test_asset_id_shape(manifest):
    assert all(re.fullmatch(r"A[0-9]{2}", a["asset_id"]) for a in manifest["assets"])


def test_counts_consistent(manifest):
    c = manifest["counts"]
    assets = manifest["assets"]
    assert c["assets"] == len(assets)
    assert sum(c["by_class"].values()) == len(assets)
    for status, key in (("resolved_in_source", "resolved_in_source"),
                        ("referenced_unresolved", "referenced_unresolved"),
                        ("declared_absent", "declared_absent")):
        assert c[key] == sum(1 for a in assets if a["resolution"] == status)


def test_claims_all_have_evidence_or_status(manifest):
    for c in manifest["claims"]:
        assert ("evidence" in c) or ("unresolved_reason" in c) or ("status" in c)


def test_no_asset_claims_verified(manifest):
    assert not any(isinstance(v, str) and v.strip().lower() == "verified"
                   for a in manifest["assets"] for v in a.values())


# ---------------------------------------------------------------- artifact integrity
def test_artifact_matches_envelope_hash():
    result = json.loads(RESULT_PATH.read_text())
    assert hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest() == \
        result["outputs"]["asset_manifest.json"]["artifact_sha256"]


def test_durable_mirror_is_byte_identical():
    assert MIRROR_PATH.read_bytes() == MANIFEST_PATH.read_bytes()


def test_notices_bound_to_registered_assets(manifest):
    ids = {a["asset_id"] for a in manifest["assets"]}
    assert manifest["notices"], "at least the placeholder-table notice must be recorded"
    assert all(n["evidence_asset"] in ids for n in manifest["notices"])


def test_declared_absent_figure_asset_matches_platform_metadata(manifest):
    a = next(a for a in manifest["assets"] if a["asset_id"] == "A12")
    assert a["resolution"] == "declared_absent"
    assert a["resolution_check"]["result"] == "absent"
    assert a["resolution_check"]["platform_figures_count"] == 0
    assert manifest["source"]["platform_figures"] == []


def test_placeholder_table_is_registered_verbatim(md, manifest):
    """The results table in report 9947 carries no numbers; the registration must say so, not invent any."""
    a = next(a for a in manifest["assets"] if a["asset_id"] == "A06")
    quote = a["locator"]["quote"]
    assert quote == md[206:385]
    assert "| a-dev | m- | - |  | - |" in quote
    assert not re.search(r"\d+\.\d+%", quote), "no numeric result may be attributed to the table shell"
    assert any("占位" in n["text"] for n in manifest["notices"])

# ---------------------------------------------------------------- deliverable report
def test_report_has_single_json_block_equal_to_envelope():
    """The delivery channel is the report markdown: exactly one fenced json block, byte-identical to
    runs/wp-9947-01/kf_result.wp-9947-01.json (no hand-editing of the envelope is possible)."""
    report = ROOT / "docs/wp-9947-01/KF-RESULT-wp-9947-01.md"
    if not report.exists():  # pragma: no cover
        pytest.skip("report not built yet (python3 scripts/kf_report_9947.py)")
    text = report.read_text()
    assert text.count("```json") == 1, "exactly one json block is allowed"
    block = text.split("```json", 1)[1].split("```", 1)[0].strip()
    assert json.loads(block) == json.loads(RESULT_PATH.read_text())
    assert text.startswith("# KF-RESULT wp-9947-01")


def test_report_cites_every_source_quote_verbatim(md):
    """Every quote shown in the evidence table must be a literal slice of the source markdown."""
    report = (ROOT / "docs/wp-9947-01/KF-RESULT-wp-9947-01.md").read_text()
    manifest = json.loads(MANIFEST_PATH.read_text())
    for a in manifest["assets"]:
        first = a["locator"]["quote"].split("\n")[0]
        head = first[:20]
        assert head in md and head.replace("|", "\\|") in report, a["asset_id"]
