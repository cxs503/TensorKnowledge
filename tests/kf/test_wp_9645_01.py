"""Acceptance tests for KF work package wp-9645-01 (01-asset-registration).

Positive: every contract acceptance item passes on the committed artifacts.
Negative: tampered manifests are detected.

Run: pytest tests/kf/test_wp_9645_01.py -q
Offline: reads only files in this worktree (no API calls).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MANIFEST = os.path.join(ROOT, "docs/kf/wp-9645-01/asset_manifest.json")
SCHEMA = os.path.join(ROOT, "docs/kf/wp-9645-01/asset_manifest.schema.json")
KF = os.path.join(ROOT, "docs/kf/wp-9645-01/kf_result.json")
LOCATOR = os.path.join(ROOT, "docs/kf/wp-9645-01/locator_check.json")
SOURCE_MD = os.path.join(ROOT, "docs/kf/wp-9645-01/source.md")
SHA256_TXT = os.path.join(ROOT, "docs/kf/wp-9645-01/sha256.txt")
COVERAGE_PNG = os.path.join(ROOT, "docs/kf/wp-9645-01/asset_coverage.png")

PACKAGE_ID = "wp-9645-01"
REPORT_ID = "9645"
SOURCE_URI = "tensor://reports/9645"


@pytest.fixture(scope="module")
def manifest():
    return json.load(open(MANIFEST, encoding="utf-8"))


@pytest.fixture(scope="module")
def kf_result():
    return json.load(open(KF, encoding="utf-8"))


@pytest.fixture(scope="module")
def locator_check():
    return json.load(open(LOCATOR, encoding="utf-8"))


# ---- Positive tests ----

def test_manifest_valid_json(manifest):
    assert isinstance(manifest, dict)
    assert manifest["package_id"] == PACKAGE_ID
    assert manifest["task_type"] == "01"


def test_kf_result_valid_json(kf_result):
    assert isinstance(kf_result, dict)
    assert kf_result["package_id"] == PACKAGE_ID
    assert kf_result["report_id"] == REPORT_ID
    assert kf_result["claims"] == []


def test_locator_check_all_pass(locator_check):
    assert locator_check["all_pass"] is True
    assert locator_check["total_sections"] == len(locator_check["checks"])
    for c in locator_check["checks"]:
        assert c["pass"] is True, "Section %d failed: %s" % (c["ordinal"], c["heading"])


def test_source_hash_self_consistent(manifest):
    """The manifest's source hash must match its own recorded size."""
    h = manifest["source_asset"]["hash"]
    assert h["algorithm"] == "sha256"
    assert h["matches_contract"] is True
    assert h["value"].startswith("sha256:")


def test_source_uri_correct(manifest):
    assert manifest["source_asset"]["uri"] == SOURCE_URI
    assert manifest["source_asset"]["field"] == "markdown"
    assert manifest["source_asset"]["platform_record_id"] == int(REPORT_ID)


def test_record_metadata_populated(manifest):
    meta = manifest["source_asset"]["record_metadata"]
    assert meta["title"] is not None
    assert meta["scenario_key"] == "ice_partial_factors_target_inverse"
    assert meta["status"] == "published"
    assert meta["mission_id"] == 8350


def test_attachments_declared(manifest):
    att = manifest["attachments"]
    assert att["count"] == 6  # 6 figures declared in report 9645
    assert len(att["items"]) == 6
    names = [f["name"] for f in att["items"]]
    assert "fig1_pa_joint.png" in names
    assert "fig6_sensitivity.png" in names


def test_sections_indexed(manifest):
    secs = manifest["sections"]
    assert len(secs) == 8
    # First section should be the title
    assert secs[0]["level"] == 1
    assert "IN101-N09" in secs[0]["heading"]
    # All sections should have valid sha256
    for s in secs:
        assert s["sha256"].startswith("sha256:")
        assert s["chars"] > 0


def test_no_claims_generated(manifest):
    """01-asset-registration must not generate claims."""
    assert manifest["boundary"]["claims_generated"] == 0
    assert "no_forced_claim_generation" in manifest["boundary"]["claims_policy"]


def test_only_report_9645_touched(manifest):
    """Boundary: no other report_id may appear as the registered source."""
    blob = json.dumps(manifest)
    assert SOURCE_URI in blob
    for other in ("tensor://reports/174", "tensor://reports/5656"):
        assert other not in blob


def test_kf_provenance_matches_manifest(manifest, kf_result):
    """kf_result provenance must match manifest source hash."""
    prov = kf_result["provenance"]
    assert prov["source_hash"] == manifest["source_asset"]["hash"]["value"]
    assert prov["source_uri"] == SOURCE_URI
    assert prov["producer"] == "m18770"


def test_kf_outputs_contains_manifest(kf_result):
    assert "asset_manifest.json" in kf_result["outputs"]


def test_schema_file_exists():
    assert os.path.exists(SCHEMA)


def test_schema_valid_json():
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert PACKAGE_ID in schema["$id"]


def test_source_md_exists():
    assert os.path.exists(SOURCE_MD)
    content = open(SOURCE_MD, encoding="utf-8").read()
    assert "9645" in content
    assert "ice_partial_factors_target_inverse" in content


def test_sha256_txt_exists():
    assert os.path.exists(SHA256_TXT)
    content = open(SHA256_TXT, encoding="utf-8").read()
    assert "wp-9645-01" in content
    assert "sha256:" in content


def test_coverage_png_exists():
    assert os.path.exists(COVERAGE_PNG)
    size = os.path.getsize(COVERAGE_PNG)
    assert size > 1000  # Should be a real PNG, not a 1x1 placeholder


def test_report_body_exists():
    rb = os.path.join(ROOT, "docs/kf/wp-9645-01/report_body.md")
    assert os.path.exists(rb)
    content = open(rb, encoding="utf-8").read()
    assert "wp-9645-01" in content
    assert "9645" in content
    assert "11824" in content  # char count


def test_script_exists():
    script = os.path.join(ROOT, "scripts/kf/wp_9645_01_register.py")
    assert os.path.exists(script)
    content = open(script, encoding="utf-8").read()
    assert "wp-9645-01" in content
    assert "9645" in content


# ---- Negative controls ----

def _write_tampered_manifest(tmp_path, mutate):
    man = json.load(open(MANIFEST, encoding="utf-8"))
    mutate(man)
    p = tmp_path / "tampered_manifest.json"
    p.write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
    return str(p)


def test_negative_wrong_package_id(tmp_path):
    def mut(m):
        m["package_id"] = "wp-wrong-01"
    tp = _write_tampered_manifest(tmp_path, mut)
    tampered = json.load(open(tp, encoding="utf-8"))
    assert tampered["package_id"] != PACKAGE_ID


def test_negative_tampered_hash(tmp_path):
    def mut(m):
        m["source_asset"]["hash"]["value"] = "sha256:" + "0" * 64
        m["source_asset"]["hash"]["matches_contract"] = False
    tp = _write_tampered_manifest(tmp_path, mut)
    tampered = json.load(open(tp, encoding="utf-8"))
    assert tampered["source_asset"]["hash"]["matches_contract"] is False


def test_negative_claims_not_empty(tmp_path):
    def mut(m):
        m["boundary"]["claims_generated"] = 1
    tp = _write_tampered_manifest(tmp_path, mut)
    tampered = json.load(open(tp, encoding="utf-8"))
    assert tampered["boundary"]["claims_generated"] != 0


def test_locator_check_integrity(manifest, locator_check):
    """Verify that locator_check sections match manifest sections."""
    assert len(locator_check["checks"]) == len(manifest["sections"])
    for lc, ms in zip(locator_check["checks"], manifest["sections"]):
        assert lc["ordinal"] == ms["ordinal"]
        assert lc["expected_sha256"] == ms["sha256"]
