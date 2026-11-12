"""wp-1610-01 (01-asset-registration, report 1610) acceptance tests.

Offline: everything is checked against the artifacts committed in this worktree, so the
gate can be re-run without platform credentials. Re-fetching the source (and thus
re-proving that the artifacts were produced from the live record) is
`python3 scripts/kf_wp1610_01_register.py`.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-1610-01")
EXPECTED_HASH = "sha256:c426979905fa50a5cd372e8e7b300ad931596c437ea1cbabb79df59c7aaa41de"
REPORT_MD = os.path.join(ROOT, "docs", "kf_result_wp-1610-01.md")


def load(name: str):
    with open(os.path.join(PKG, name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def source() -> str:
    with open(os.path.join(PKG, "source.md"), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load("asset_manifest.json")


@pytest.fixture(scope="module")
def locator() -> dict:
    return load("locator_check.json")


@pytest.fixture(scope="module")
def result() -> dict:
    with open(os.path.join(ROOT, "docs", "kf", "wp-1610-01", "kf_result.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_source_hash_matches_contract(source: str) -> None:
    digest = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == EXPECTED_HASH


def test_manifest_identity_fields(manifest: dict, source: str) -> None:
    assert manifest["package_id"] == "wp-1610-01"
    assert manifest["report_id"] == "1610"
    assert manifest["source_uri"] == "tensor://reports/1610"
    assert manifest["source_field"] == "markdown"
    assert manifest["source_hash"] == EXPECTED_HASH
    assert manifest["source_hash_expected"] == EXPECTED_HASH
    assert manifest["source_hash_matches"] is True
    assert manifest["chars"] == len(source) == 5883
    assert manifest["bytes_utf8"] == len(source.encode("utf-8"))


def test_manifest_registers_no_extraction(manifest: dict) -> None:
    assert manifest["claims"] == []  # no forced claim generation
    assert manifest["attachments"] and all(a.get("name") and a.get("caption") for a in manifest["attachments"])
    assert all(a["resolvable_from_platform_record"] is False for a in manifest["artifacts"])


def test_every_locator_resolves_verbatim(source: str, locator: dict) -> None:
    assert locator["source_hash"] == EXPECTED_HASH
    assert locator["quotes_checked"] == len(locator["checks"])
    assert locator["unresolved"] == []
    for chk in locator["checks"]:
        pos = source.find(chk["quote"])
        assert pos >= 0, f"quote not verbatim in source: {chk['locator_id']}"
        assert pos == chk["char_offset"], f"offset drift for {chk['locator_id']}"


def test_declared_artifacts_are_quoted_from_source(source: str, manifest: dict) -> None:
    for art in manifest["artifacts"]:
        assert art["path"] in source, art["path"]


def test_kf_result_envelope_schema(result: dict) -> None:
    with open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"), encoding="utf-8") as fh:
        schema = json.load(fh)
    jsonschema.Draft202012Validator(schema).validate(result)


def test_envelope_agrees_with_manifest(result: dict, manifest: dict) -> None:
    assert result["package_id"] == "wp-1610-01"
    assert result["task_type"] == "01-asset-registration"
    assert result["report_id"] == "1610"
    assert result["provenance"]["source_hash"] == EXPECTED_HASH
    assert result["provenance"]["source_field"] == "markdown"
    assert list(result["outputs"]) == ["asset_manifest.json"]
    assert result["outputs"]["asset_manifest.json"] == manifest
    assert "verification_status" not in json.dumps(result["outputs"])


def test_report_has_exactly_one_json_block_matching_envelope(result: dict) -> None:
    with open(REPORT_MD, encoding="utf-8") as fh:
        md = fh.read()
    assert md.splitlines()[0].strip() == "# KF-RESULT wp-1610-01"
    assert "kf-wp:wp-1610-01" in md
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    assert len(blocks) == 1, f"expected a single json block, found {len(blocks)}"
    assert json.loads(blocks[0]) == result
    for section in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6."):
        assert section in md


def test_report_contains_no_reproducible_secret() -> None:
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not pwd:
        pytest.skip("no credential in env to compare against")
    for path in ("docs/kf_result_wp-1610-01.md", "scripts/kf_wp1610_01_register.py",
                 "scripts/kf_wp1610_01_result.py", "docs/kf/wp-1610-01/asset_manifest.json"):
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            assert pwd not in fh.read(), f"credential leaked into {path}"