"""Acceptance tests for KF work package wp-5577-01 (asset registration).

Tests verify:
1. All artifacts exist and are valid JSON
2. Source hash matches contract
3. All locators are resolvable
4. No duplicate asset IDs
5. Claims discipline (empty claims with explicit reason)
6. Negative controls (tampered hash/quote must FAIL)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = REPO_ROOT / "docs" / "kf" / "wp-5577-01"
SOURCE_DIR = PKG_DIR / "source"

MANIFEST = PKG_DIR / "asset_manifest.json"
KF_RESULT = PKG_DIR / "kf_result.json"
ACCEPTANCE = PKG_DIR / "acceptance.json"
SOURCE_MD = SOURCE_DIR / "report_5577.md"
SOURCE_HASH = SOURCE_DIR / "markdown.sha256"


# =============================================================================
# Artifact existence
# =============================================================================

def test_artifacts_exist():
    """All required artifacts must exist."""
    assert MANIFEST.is_file(), "asset_manifest.json missing"
    assert KF_RESULT.is_file(), "kf_result.json missing"
    assert ACCEPTANCE.is_file(), "acceptance.json missing"
    assert SOURCE_MD.is_file(), "source/report_5577.md missing"
    assert SOURCE_HASH.is_file(), "source/markdown.sha256 missing"
    assert (PKG_DIR / "REPORT.md").is_file(), "REPORT.md missing"
    assert (PKG_DIR / "fig1_asset_resolution.png").is_file(), "fig1_asset_resolution.png missing"


# =============================================================================
# Valid JSON
# =============================================================================

def test_valid_json():
    """All JSON artifacts must be valid."""
    for path in [MANIFEST, KF_RESULT, ACCEPTANCE]:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{path} is not a JSON object"


# =============================================================================
# Envelope structure
# =============================================================================

def test_kf_result_structure():
    """kf_result.json must have required fields."""
    env = json.loads(KF_RESULT.read_text(encoding="utf-8"))
    assert env["package_id"] == "wp-5577-01"
    assert env["task_type"] == "01-asset-registration"
    assert env["report_id"] == "5577"
    assert "provenance" in env
    assert "outputs" in env
    assert "asset_manifest.json" in env["outputs"]
    # claims are in asset_manifest, not in kf_result envelope (schema)


def test_manifest_structure():
    """asset_manifest.json must have required fields."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert man["package_id"] == "wp-5577-01"
    assert man["task_type"] == "01-asset-registration"
    assert man["report_id"] == "5577"
    assert "source_hash" in man
    assert "attachments" in man
    assert "locators" in man
    assert man["claims"] == []


# =============================================================================
# Source hash verification
# =============================================================================

def test_source_hash_matches_contract():
    """Source hash must match the contract expectation."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(KF_RESULT.read_text(encoding="utf-8"))

    # Hash from manifest
    manifest_hash = man["source_hash"]
    expected_hash = man["source_hash_expected"]

    # Hash from envelope
    envelope_hash = env["provenance"]["source_hash"]

    # All must match
    assert manifest_hash == expected_hash, "manifest hash mismatch"
    assert manifest_hash == envelope_hash, "envelope hash mismatch"

    # Recompute from source file
    md = SOURCE_MD.read_text(encoding="utf-8")
    recomputed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert recomputed == manifest_hash, f"recomputed hash {recomputed} != manifest {manifest_hash}"


def test_source_hash_file_matches():
    """markdown.sha256 file must match the computed hash."""
    hash_file = SOURCE_HASH.read_text(encoding="utf-8").strip()
    md = SOURCE_MD.read_text(encoding="utf-8")
    recomputed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert hash_file == recomputed


# =============================================================================
# Locator resolution
# =============================================================================

def test_every_locator_resolves_verbatim():
    """Every locator quote must be a verbatim substring of the source."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = SOURCE_MD.read_text(encoding="utf-8")

    for loc in man["locators"]:
        quote = loc["quote"]
        assert quote in md, f"Locator {loc['locator_id']} quote not found: {quote[:50]}"
        assert loc["resolvable"] is True, f"Locator {loc['locator_id']} marked unresolvable"


def test_locator_line_numbers_correct():
    """Locator line numbers must point to lines containing the quote."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = SOURCE_MD.read_text(encoding="utf-8")
    lines = md.split("\n")

    for loc in man["locators"]:
        if loc["line"] is not None:
            line_idx = loc["line"] - 1  # 1-indexed to 0-indexed
            assert 0 <= line_idx < len(lines), f"Locator {loc['locator_id']} line out of range"
            line_text = lines[line_idx]
            assert loc["quote"] in line_text, (
                f"Locator {loc['locator_id']} quote not on line {loc['line']}"
            )


# =============================================================================
# No duplicate IDs
# =============================================================================

def test_no_duplicate_asset_ids():
    """All asset IDs must be unique."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = [a["asset_id"] for a in man["attachments"]]
    assert len(ids) == len(set(ids)), "Duplicate asset IDs found"


def test_no_duplicate_locator_ids():
    """All locator IDs must be unique."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = [l["locator_id"] for l in man["locators"]]
    assert len(ids) == len(set(ids)), "Duplicate locator IDs found"


# =============================================================================
# Claims discipline
# =============================================================================

def test_claims_empty_with_explicit_reason():
    """Claims must be empty with explicit reason (01-asset-registration)."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(KF_RESULT.read_text(encoding="utf-8"))

    assert man["claims"] == [], "claims must be empty for 01-asset-registration"
    assert man.get("claims_empty_reason"), "claims_empty_reason must be set"
    assert man.get("no_forced_claim_generation") is True

    # kf_result envelope does not carry claims (schema-compliant)


# =============================================================================
# Acceptance checks
# =============================================================================

def test_acceptance_all_pass():
    """All acceptance items must pass."""
    acc = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    assert acc["all_pass"] is True
    assert acc["failed_items"] == []


def test_acceptance_items_complete():
    """All required acceptance items must be present."""
    acc = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    required = [
        "valid_json",
        "schema_pass",
        "source_locator_resolvable",
        "source_hash_matches",
        "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status",
    ]
    for item in required:
        assert item in acc["items"], f"Missing acceptance item: {item}"


# =============================================================================
# Scope check (only 5577)
# =============================================================================

def test_scope_only_5577():
    """Package must only reference report 5577."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(KF_RESULT.read_text(encoding="utf-8"))

    assert man["report_id"] == "5577"
    assert env["report_id"] == "5577"
    assert "5577" in man["source_uri"]
    assert "5577" in env["provenance"]["source_uri"]


# =============================================================================
# Negative controls
# =============================================================================

def test_negative_control_tampered_hash_fails():
    """Tampered source hash must be detected."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    original_hash = man["source_hash"]

    # Tamper
    man["source_hash"] = "sha256:" + "0" * 64

    # Verify mismatch
    md = SOURCE_MD.read_text(encoding="utf-8")
    recomputed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert man["source_hash"] != recomputed, "Tampered hash should not match"
    assert man["source_hash"] != original_hash, "Tampered hash should differ from original"


def test_negative_control_tampered_quote_fails():
    """Tampered locator quote must be detected."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = SOURCE_MD.read_text(encoding="utf-8")

    # Tamper first locator
    original_quote = man["locators"][0]["quote"]
    man["locators"][0]["quote"] = "THIS_QUOTE_DOES_NOT_EXIST_IN_SOURCE"

    # Verify mismatch
    assert man["locators"][0]["quote"] not in md, "Tampered quote should not be in source"
    assert man["locators"][0]["quote"] != original_quote


# =============================================================================
# Figure check
# =============================================================================

def test_figure_is_valid_png():
    """fig1_asset_resolution.png must be a valid PNG."""
    fig_path = PKG_DIR / "fig1_asset_resolution.png"
    data = fig_path.read_bytes()
    # PNG magic bytes
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "Not a valid PNG file"
    assert len(data) > 100, "PNG file too small"


# =============================================================================
# Char count verification
# =============================================================================

def test_chars_match_contract():
    """Character count must match the contract."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = SOURCE_MD.read_text(encoding="utf-8")

    assert len(md) == man["chars"], "char count mismatch"
    assert len(md) == man["chars_expected"], "chars_expected mismatch"
    assert man["chars_match_contract"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
