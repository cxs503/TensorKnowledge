"""Regression tests for work package wp-9447-01 (01-asset-registration, report 9447).

Two layers:
  * offline: the committed artifacts must be schema-valid and internally consistent;
  * online (skipped when the platform API is unreachable): the declared source_hash
    and every recorded locator must re-resolve against the live markdown bytes.

Run: pytest -q tests/test_wp_9447_01_asset_registration.py
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "runs" / "wp-9447-01" / "asset_manifest.json"
ENVELOPE = ROOT / "runs" / "wp-9447-01" / "kf_result.json"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
CONTRACT_HASH = "a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666"
STATUS_VOCAB = {"present_hash_verified", "declared_only", "declared_unrecoverable", "reference_only"}


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text())


def test_artifacts_exist() -> None:
    assert MANIFEST.is_file(), f"missing {MANIFEST}"
    assert ENVELOPE.is_file(), f"missing {ENVELOPE}"


def test_envelope_matches_schema(envelope: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text())
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(envelope),
                    key=lambda e: list(e.path))
    assert not errors, [f"{list(e.path)}: {e.message}" for e in errors]


def test_envelope_envelope_fields(envelope: dict) -> None:
    assert envelope["package_id"] == "wp-9447-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "9447"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert "asset_manifest.json" in envelope["outputs"]
    # asset registration performs no extraction: zero claims is a complete result
    assert envelope["claims"] == []


def test_manifest_identity(manifest: dict) -> None:
    assert manifest["report_id"] == "9447"
    assert manifest["source"]["sha256"] == "sha256:" + CONTRACT_HASH
    assert manifest["source"]["hash_matches_contract"] is True
    assert manifest["source"]["chars"] == 7241
    assert manifest["scope"] == {
        "register_assets": True,
        "classify_report_type": False,
        "extraction_performed": False,
        "claims_generated": 0,
    }


def test_no_duplicate_ids_or_paths(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    paths = [a["path"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert len(paths) == len(set(paths))
    assert manifest["duplicate_asset_ids"] == []
    assert manifest["duplicate_paths"] == []


def test_every_asset_has_resolvable_locator_shape(manifest: dict) -> None:
    for a in manifest["assets"]:
        assert a["status"] in STATUS_VOCAB, a
        assert a["evidence"], f"{a['asset_id']} has no evidence"
        for ev in a["evidence"]:
            loc = ev["locator"]
            assert ev["quote"], a["asset_id"]
            assert ev["source_field"] == "markdown"
            assert loc["line"] >= 1
            assert 0 <= loc["char_start"] < loc["char_end"] <= manifest["source"]["chars"]
            assert loc["char_end"] - loc["char_start"] == len(ev["quote"])
            assert loc["sha256_of_quote"] == hashlib.sha256(ev["quote"].encode()).hexdigest()


def test_counts_consistent(manifest: dict) -> None:
    assets = manifest["assets"]
    assert manifest["counts"]["assets"] == len(assets)
    assert sum(manifest["counts"]["by_status"].values()) == len(assets)
    assert sum(manifest["counts"]["by_kind"].values()) == len(assets)
    assert manifest["counts"]["record_figures_with_payload"] == 0


def test_record_figures_declared_without_payload(manifest: dict) -> None:
    figs = manifest["record_level_figures"]
    assert len(figs) == manifest["counts"]["record_figures"] == 3
    for f in figs:
        assert f["png_base64_present"] is False
        assert f["markdown_mention"] is True


def test_validation_block_all_green(manifest: dict) -> None:
    v = manifest["validation"]
    for key in ("valid_json", "source_hash_matches", "source_locator_resolvable",
                "no_duplicate_ids", "no_duplicate_paths", "claims_empty_as_declared",
                "schema_pass"):
        assert v[key] is True, f"{key} -> {v[key]}"
    assert v["locator_failures"] == []
    assert v["schema_problems"] == []


# --------------------------------------------------------------------------- #
# live re-resolution (independent confirmation of the committed locators)
# --------------------------------------------------------------------------- #
def _live_markdown() -> str:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        pytest.skip("no TENSOR_AGENT_USER/PASS in env")
    try:
        req = urllib.request.Request(
            base + "/auth/login",
            data=json.dumps({"username": user, "password": pwd}).encode(),
            headers={"Content-Type": "application/json"},
        )
        token = json.load(urllib.request.urlopen(req, timeout=15))["access_token"]
        req = urllib.request.Request(f"{base}/tensor/reports/9447",
                                     headers={"Authorization": "Bearer " + token})
        return json.load(urllib.request.urlopen(req, timeout=20))["markdown"]
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"platform API unreachable: {exc}")


def test_live_source_hash_and_locators(manifest: dict) -> None:
    md = _live_markdown()
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert len(md) == manifest["source"]["chars"]
    bad = []
    for a in manifest["assets"]:
        for ev in a["evidence"]:
            loc = ev["locator"]
            if md[loc["char_start"]:loc["char_end"]] != ev["quote"]:
                bad.append(a["asset_id"])
    for an in manifest["source_annotations"]:
        for ev in an["evidence"]:
            loc = ev["locator"]
            if md[loc["char_start"]:loc["char_end"]] != ev["quote"]:
                bad.append(an["annotation_id"])
    assert not bad, f"locators do not re-resolve: {bad}"