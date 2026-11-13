"""Acceptance tests for work package wp-9503-01 (task_type=01-asset-registration, report 9503).

These tests are the machine-checkable half of the package's self-check: they re-derive every
acceptance item from the committed artefacts (offline, no platform call), so a later edit that
breaks a locator, the hash or the envelope fails here instead of silently passing a report.

Run: python3 -m pytest tests/test_kf_wp9503_01_register.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-9503-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
VERIFICATION = PKG / "verification.json"
RESULT_MD = PKG / "KF-RESULT-wp-9503-01.md"
SOURCE = PKG / "source_9503.md"
FIG = PKG / "figures" / "locator_map.png"

# contract constants (work-package YAML) -- hard-coded on purpose: the test must fail if the
# contract identity and the artefact drift apart.
CONTRACT_HASH = "sha256:195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c"
CONTRACT_CHARS = 8176
PACKAGE_ID = "wp-9503-01"


@pytest.fixture(scope="module")
def md() -> str:
    assert SOURCE.exists(), "source snapshot missing -- run the register script (build)"
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- source identity
def test_source_hash_matches_contract(md: str) -> None:
    got = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert got == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_provenance_hash_agrees_with_live_bytes(md: str, envelope: dict, manifest: dict) -> None:
    live = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert envelope["provenance"]["source_hash"] == live
    assert "sha256:" + manifest["source"]["hash"] == live
    assert manifest["source"]["hash_matches_contract"] is True
    assert manifest["source"]["chars"] == CONTRACT_CHARS


# ---------------------------------------------------------------- schema
def test_envelope_matches_kf_result_schema(envelope: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(envelope)


def test_manifest_matches_v2_schema(manifest: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "asset_manifest.v2.schema.json").read_text())
    jsonschema.Draft7Validator(schema).validate(manifest)


# ---------------------------------------------------------------- locators
def test_every_locator_resolves_and_is_unique(md: str, manifest: dict) -> None:
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        assert loc["start_char"] < loc["end_char"], a["asset_id"]
        assert md[loc["start_char"]:loc["end_char"]] == quote, a["asset_id"]
        if loc["method"] == "document":
            assert quote == md
            continue
        assert md.count(quote) == 1, "%s quote not unique" % a["asset_id"]
        lines = md.rstrip("\n").split("\n")
        assert "\n".join(lines[loc["start_line"] - 1:loc["end_line"]]) == quote, a["asset_id"]
        assert loc["start_line"] <= loc["end_line"]


def test_no_duplicate_ids_and_counts_consistent(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["counts"]["assets"] == len(ids)
    hist: dict[str, int] = {}
    for a in manifest["assets"]:
        hist[a["resolution"]] = hist.get(a["resolution"], 0) + 1
    assert hist == manifest["counts"]["by_resolution"]
    assert all(a["resolution"] in
               {"resolved_in_source", "referenced_unresolved", "declared_absent"}
               for a in manifest["assets"])


def test_unresolved_assets_carry_a_probed_target(manifest: dict) -> None:
    """No invented addresses: anything not resolvable in the source must name its address and
    record whether that address exists in this worktree (probed, not assumed)."""
    for a in manifest["assets"]:
        if a["resolution"] == "resolved_in_source":
            continue
        target = a.get("target")
        assert target, a["asset_id"]
        assert "exists_in_worktree" in target
        if target["kind"] != "git_commit" and target.get("address_as_written"):
            if "*" not in target["address_as_written"]:
                assert target["exists_in_worktree"] is False, a["asset_id"]


# ---------------------------------------------------------------- registration only
def test_claims_empty_and_reasoned(manifest: dict) -> None:
    assert manifest["claims"] == []
    assert manifest["claims_empty_reason"].strip()
    assert manifest["objective"]["classify_report_type"] is False
    assert manifest["objective"]["extraction_performed"] is False


def test_nothing_is_marked_verified(manifest: dict, envelope: dict) -> None:
    blob = json.dumps([manifest, envelope], ensure_ascii=False).lower()
    assert '"verified"' not in blob
    assert "verified_by" not in blob


def test_single_report_scope(manifest: dict, envelope: dict) -> None:
    assert manifest["report_id"] == "9503"
    assert envelope["report_id"] == "9503"
    text = json.dumps([manifest, envelope], ensure_ascii=False)
    for other in ("448", "542", "623", "1202", "1610"):
        assert "reports/%s" % other not in text


# ---------------------------------------------------------------- delivery format
def test_result_markdown_has_exactly_one_json_block_equal_to_envelope(envelope: dict) -> None:
    text = RESULT_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
    assert len(blocks) == 1, "result markdown must carry exactly one json code block"
    assert json.loads(blocks[0]) == envelope
    assert text.split("\n")[0].strip() == "# KF-RESULT %s" % PACKAGE_ID
    for section in ("①", "②", "③", "④", "⑤", "⑥"):
        assert section in text
    assert "repro_cmd" in text


def test_verification_json_all_acceptance_pass() -> None:
    ver = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    assert ver["all_acceptance_pass"] is True, ver["acceptance_summary"]
    for item, val in ver["acceptance_summary"].items():
        assert val["pass"] is True, item


def test_locator_map_figure_exists() -> None:
    assert FIG.exists() and FIG.stat().st_size > 10_000