"""wp-766-01 · 01-asset-registration self-check (offline, hermetic).

Locks the acceptance conditions of the work package against the committed
artefacts in ``runs/wp-766-01/`` — no network, no database:

  * envelope validates against ``schemas/kf_result.v1.schema.json``;
  * ``provenance.source_hash`` equals sha256 of the stored source markdown
    (and of the API snapshot's ``markdown`` field);
  * every asset quote is a verbatim substring of the source markdown, and sits
    on the line the locator declares;
  * asset ids are unique;
  * claims are empty or each carries evidence / an explicit unresolved status;
  * re-running ``register_assets.py`` on the stored source reproduces the
    committed manifest byte-for-byte (modulo the ``generated_at`` stamp).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "runs" / "wp-766-01"
MANIFEST_PATH = PKG / "asset_manifest.json"
KF_PATH = PKG / "kf_result.json"
SRC_MD = PKG / "source" / "report_766.markdown"
API_SNAP = PKG / "source" / "report_766.api.json"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
EXPECTED_HASH = "sha256:6b45972f5b6e61c7c832dd5aec54236b254dd20b56556190ecb0d86ac5b36407"


@pytest.fixture(scope="module")
def markdown() -> str:
    return SRC_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf() -> dict:
    return json.loads(KF_PATH.read_text(encoding="utf-8"))


def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_envelope_is_valid_json_and_schema(kf):
    jsonschema.validate(instance=kf, schema=json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert kf["package_id"] == "wp-766-01"
    assert kf["task_type"] == "01-asset-registration"
    assert kf["report_id"] == "766"
    assert "asset_manifest.json" in kf["outputs"]


def test_source_hash_matches_contract_and_api_snapshot(markdown):
    assert sha256_text(markdown) == EXPECTED_HASH
    snap = json.loads(API_SNAP.read_text(encoding="utf-8"))
    assert snap["id"] == 766
    assert sha256_text(snap["markdown"]) == EXPECTED_HASH
    # the contract's declared character count
    assert len(markdown) == 4427
    # the stored copy is byte-identical to what the API served (no re-wrapping)
    assert markdown == snap["markdown"]


def test_manifest_source_hash_agrees(markdown, manifest):
    assert manifest["report"]["source_hash"] == sha256_text(markdown) == EXPECTED_HASH
    assert manifest["report"]["source_field"] == "markdown"
    assert manifest["report"]["report_id"] == "766"
    assert manifest["report"]["utf8_bytes"] == len(markdown.encode("utf-8"))


def test_ids_unique(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["counts"]["total"] == len(ids)


def test_every_quote_is_verbatim_and_locator_resolves(markdown, manifest):
    lines = markdown.split("\n")
    for a in manifest["assets"]:
        quote = a.get("quote")
        assert quote, f"{a['asset_id']}: missing quote"
        loc = a["locator"]
        if a["quote_verbatim_in_markdown"]:
            assert quote in markdown, f"{a['asset_id']}: quote not verbatim"
            if "line" in loc:
                assert quote in lines[loc["line"] - 1], (
                    f"{a['asset_id']}: quote not on declared line {loc['line']}")
            for ln in loc.get("all_lines", []):
                assert 1 <= ln <= len(lines)
        else:
            # record-sourced assets must say so explicitly and be resolvable
            assert loc["type"] == "report_record_field"
            assert a["resolvability"] == "resolved_in_record"


def test_table_locators_span_their_block(markdown, manifest):
    lines = markdown.split("\n")
    for a in manifest["assets"]:
        if a["kind"] != "table":
            continue
        start, end = a["locator"]["line_range"]
        block = lines[start - 1:end]
        assert all(ln.strip().startswith("|") for ln in block), a["asset_id"]
        assert len(block) == a["table_rows_including_header_and_rule"]


def test_figures_registered_from_record(manifest):
    figs = [a for a in manifest["assets"] if a["kind"] == "figure"]
    snap = json.loads(API_SNAP.read_text(encoding="utf-8"))
    assert len(figs) == len(snap["figures"]) == 3
    for a, fig in zip(figs, snap["figures"]):
        assert a["locator"]["name"] == fig["name"]
        assert a["quote"] == fig["caption"]
        # the API serves name+caption only -> image bytes are NOT in the bundle
        assert set(fig) == {"name", "caption"}
        assert a["payload_status"] == "served_as_name_and_caption_only"
        assert a["asset_class"] == "record_attachment"


def test_no_asset_overstates_payload_availability(manifest):
    """External references must never claim their bytes are in the report."""
    expected = {
        "text_block": "embedded_in_markdown",
        "record_attachment": "served_as_name_and_caption_only",
        "external_reference": "referenced_only_payload_absent",
    }
    for a in manifest["assets"]:
        assert a["payload_status"] == expected[a["asset_class"]], a["asset_id"]
        if a["asset_class"] == "external_reference":
            # bare path/digest tokens: no hash claim, no download claim
            assert "sha256" not in a
            assert a["registration_action"] == "registered_locator_only_no_extraction"
    counts = manifest["counts"]["by_asset_class"]
    assert sum(counts.values()) == manifest["counts"]["total"]
    assert counts["external_reference"] >= 1


def test_claims_empty_or_evidenced(kf):
    claims = kf.get("claims") or []
    assert isinstance(claims, list)
    for c in claims:
        assert c.get("evidence") or c.get("status") in {
            "unresolved", "partially-supported", "refuted"}
    # this work package registers no knowledge claims (no forced generation)
    assert claims == []


def test_not_marked_verified(manifest, kf):
    blob = json.dumps([manifest, kf], ensure_ascii=False)
    assert '"verified"' not in blob
    assert manifest["report"]["registration_scope"].startswith("inventory")


def test_rerun_reproduces_manifest(tmp_path, manifest):
    script = PKG / "register_assets.py"
    res = subprocess.run(
        [sys.executable, str(script),
         "--report-json", str(API_SNAP),
         "--expect-source-hash", EXPECTED_HASH,
         "--schema", str(SCHEMA),
         "--out-dir", str(tmp_path)],
        capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0, res.stdout + res.stderr
    fresh = json.loads((tmp_path / "asset_manifest.json").read_text(encoding="utf-8"))
    for m in (fresh, manifest):
        m.pop("generated_at", None)
    assert fresh == manifest