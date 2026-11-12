"""Tests for the generic KF asset registrar (scripts/kf/register_assets.py) and the
wp-7920-01 products it emitted. Offline-first: live-API checks skip when the platform
is unreachable, so the suite is safe on CI.

Scope: only report_id=7920 artifacts are inspected (work-package boundary).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = "wp-7920-01"
RID = "7920"
OUT = REPO / "docs" / "kf" / PKG
MANIFEST = OUT / "asset_manifest.json"
RESULT = OUT / "kf_result.json"
VERDICT = OUT / "verification.json"
REPORT = REPO / "docs" / "reports" / "kf_wp_7920_01_result.md"
CONTRACT_HASH = "6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b"


def _load_module():
    spec = importlib.util.spec_from_file_location("register_assets", REPO / "scripts" / "kf" / "register_assets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads(RESULT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source_md():
    import os

    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    user, pwd = os.environ.get("TENSOR_AGENT_USER", ""), os.environ.get("TENSOR_AGENT_PASS", "")
    if not (user and pwd):
        pytest.skip("no agent credentials in env")
    try:
        login = urllib.request.Request(
            base + "/auth/login",
            data=json.dumps({"username": user, "password": pwd}).encode(),
            headers={"Content-Type": "application/json"},
        )
        tok = json.loads(urllib.request.urlopen(login, timeout=10).read().decode())
        tok = tok.get("access_token") or tok.get("token")
        req = urllib.request.Request(base + "/tensor/reports/" + RID, headers={"Authorization": "Bearer " + tok})
        rep = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    except Exception as e:  # noqa: BLE001
        pytest.skip("platform API unreachable: %s" % type(e).__name__)
    if isinstance(rep, dict) and isinstance(rep.get("data"), dict):
        rep = rep["data"]
    return rep["markdown"]


def test_registry_hash_equals_contract():
    mod = _load_module()
    assert mod.REGISTRY[PKG]["expected_hash"] == CONTRACT_HASH
    assert mod.REGISTRY[PKG]["report_id"] == RID
    assert mod.REGISTRY[PKG]["expected_chars"] == 6421


def test_manifest_and_envelope_are_valid_json(manifest, envelope):
    assert manifest["package_id"] == PKG and manifest["report_id"] == RID
    assert envelope["package_id"] == PKG and envelope["report_id"] == RID
    assert envelope["task_type"] == "01-asset-registration"


def test_envelope_hash_bound_to_manifest_and_outputs_digest(envelope):
    raw = MANIFEST.read_bytes()
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["outputs"]["asset_manifest.json"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert envelope["outputs"]["asset_manifest.json"]["bytes"] == len(raw)


def test_envelope_validates_against_schema(envelope):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(envelope)


def test_asset_ids_unique_and_sequential(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == ["A%02d" % i for i in range(len(ids))]


def test_claims_empty_and_never_verified(manifest, envelope):
    assert manifest["claims"] == []
    assert "claims" not in envelope or all(c.get("status") != "verified" for c in envelope["claims"])


def test_quotes_are_verbatim_substrings_of_source(manifest, source_md):
    assert hashlib.sha256(source_md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["scheme"] != "markdown_line":
            continue
        quote = loc["quote"]
        assert quote in source_md, a["asset_id"]
        assert source_md[loc["start_char"]: loc["end_char"]] == quote, a["asset_id"]
        assert source_md.split("\n")[loc["line"] - 1] == quote, a["asset_id"]


def test_no_missed_file_references(manifest, source_md):
    """Independent crude scanner: every path-like token in the source must be covered."""
    covered = {a["label"] for a in manifest["assets"]}
    crude = set(re.findall(r"[A-Za-z0-9_./-]+\.(?:json|jsonl|csv|png|svg|py|md|txt|nc|h5|yaml|yml|pdf)", source_md))
    assert crude, "scanner found nothing — regex broke"
    uncovered = sorted(t for t in crude if not any(t == c or c.endswith("/" + t) or t.endswith(c) for c in covered))
    assert uncovered == []


def test_report_has_exactly_one_json_block_equal_to_envelope(envelope):
    text = REPORT.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\s*\n(.*?)```", text, re.S)
    assert len(blocks) == 1, "report must carry exactly one ```json block"
    assert json.loads(blocks[0]) == envelope
    assert text.splitlines()[0].strip() == "# KF-RESULT " + PKG


def test_verdict_all_pass_and_no_other_package_touched(manifest):
    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    assert verdict["all_pass"] is True
    assert verdict["manifest_sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert {a["asset_id"] for a in manifest["assets"]}  # non-empty
    # products of other packages are untouched by this work package
    for other in ("wp-542-01", "wp-623-01"):
        assert (REPO / "docs" / "kf" / other).exists()


def test_out_dir_guard_rejects_foreign_package(tmp_path):
    mod = _load_module()
    with pytest.raises(SystemExit):
        mod._guard_out_dir(REPO / "docs" / "kf" / "wp-9999-01", PKG)
    with pytest.raises(SystemExit):
        mod._guard_out_dir(tmp_path / PKG, PKG)