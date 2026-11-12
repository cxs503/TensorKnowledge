"""Invariant tests for KF work package wp-5559-01 (asset registration, report 5559).

These tests assert the *contract* of the delivered manifest, not merely that the
script ran: hash identity with the source report, locator resolvability of every
registered asset, id uniqueness, an empty-but-legal claims array, absence of any
verification mark, and byte-identity between the committed envelope payload and
the committed manifest file.

Run: python3 -m pytest tests/test_kf_wp_5559_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "knowledge" / "kf" / "wp-5559-01"
MANIFEST = PKG_DIR / "asset_manifest.json"
ENVELOPE = PKG_DIR / "kf_result.json"
SNAPSHOT = PKG_DIR / "source_report_5559.md"
SCHEMA_CANONICAL = PKG_DIR / "schema" / "kf_result.v1.schema.json"
SCHEMA_STRICT = PKG_DIR / "schema" / "kf_result.v1.strict.schema.json"

CONTRACT_SOURCE_HASH = (
    "sha256:3b04e96a056a9d8ba1b7861452dd5c2b3ce74777654154c7cc91e41f4e0b74ed"
)
CONTRACT_CHARS = 9257
CONTRACT_TITLE = "IN10-A1 · 四态冰场合成器成熟化（field_synth）：可复现冰情场 + 判据全过"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def markdown() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


# --------------------------------------------------------------- source identity
def test_snapshot_hash_and_chars_match_contract(markdown: str) -> None:
    digest = "sha256:" + hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_SOURCE_HASH
    assert len(markdown) == CONTRACT_CHARS


def test_manifest_records_the_same_hash(manifest: dict) -> None:
    src = manifest["source"]
    assert src["source_hash"] == CONTRACT_SOURCE_HASH
    assert src["hash_match"] is True
    assert src["chars"] == CONTRACT_CHARS
    assert src["chars_match_contract"] is True
    assert src["report_id"] == "5559"


def test_envelope_provenance_hash_matches_contract(envelope: dict) -> None:
    prov = envelope["provenance"]
    assert prov["source_hash"] == CONTRACT_SOURCE_HASH
    assert prov["source_field"] == "markdown"
    assert envelope["report_id"] == "5559"
    assert envelope["package_id"] == "wp-5559-01"
    assert envelope["task_type"] == "01-asset-registration"


# --------------------------------------------------------------- schema
@pytest.mark.parametrize("schema_path", [SCHEMA_CANONICAL, SCHEMA_STRICT],
                         ids=["canonical", "strict"])
def test_envelope_validates_against_schema(envelope: dict, schema_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=envelope, schema=schema)


def test_envelope_wraps_the_committed_manifest(envelope: dict, manifest: dict) -> None:
    """The report block and the repo file must not drift apart."""
    assert envelope["outputs"]["asset_manifest.json"] == manifest


# --------------------------------------------------------------- locators
def test_every_locator_resolves(manifest: dict, markdown: str) -> None:
    locators = manifest["locators"]
    assert len(locators) == manifest["counts"]["assets_total"]
    unresolved = [x["id"] for x in locators if not x["resolved"]]
    assert unresolved == []


def test_markdown_quotes_are_verbatim_slices(markdown: str, manifest: dict) -> None:
    for a in manifest["assets"]:
        lc = a["locator"]
        if lc["source_field"] != "markdown":
            continue
        assert lc["quote"] in markdown, a["asset_id"]
        assert markdown[lc["char_start"]:lc["char_end"]] == lc["quote"], a["asset_id"]
        # the quote must sit on the declared 1-based line
        lines = markdown.rstrip("\n").split("\n")
        assert lines[lc["line"] - 1] == lc["quote"], a["asset_id"]
        # the discriminating token must be present on that line
        assert lc["matched_token"] in lc["quote"], a["asset_id"]
        assert markdown[lc["token_char_start"]:lc["token_char_end"]] == lc["matched_token"]


def test_record_quotes_equal_values_at_pointer(manifest: dict, envelope: dict) -> None:
    for loc in manifest["locators"]:
        if loc["locator"]["source_field"] != "record":
            continue
        assert loc["pointer_resolved"] is True
        assert loc["value_equals_quote"] is True
    # spot check the three contract-critical record fields
    by_id = {a["asset_id"]: a for a in manifest["assets"]}
    assert by_id["r5559:record-id"]["locator"]["quote"] == 5559
    assert by_id["r5559:record-title"]["locator"]["quote"] == CONTRACT_TITLE
    assert by_id["r5559:record-scenario"]["locator"]["quote"] == "ice_nav_campaign"


# --------------------------------------------------------------- contract discipline
def test_ids_unique(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["id_integrity"]["unique"] is True
    assert manifest["id_integrity"]["duplicates"] == []


def test_claims_array_is_empty_and_justified(manifest: dict, envelope: dict) -> None:
    assert manifest["claims"] == []
    assert envelope.get("claims", []) == []
    assert manifest["claims_empty_reason"]
    assert manifest["objective"] == {"register_assets": True, "classify_report_type": False}


def test_no_verification_marks(manifest: dict, envelope: dict) -> None:
    """Verification is computed by the platform gate; this worker must not claim it."""
    for blob in (json.dumps(manifest, ensure_ascii=False),
                 json.dumps(envelope, ensure_ascii=False)):
        assert not re.search(r'[:"]\s*verified', blob, re.I)
        assert "status\":\"verified" not in blob.replace(" ", "")


def test_only_report_5559_is_referenced(manifest: dict) -> None:
    refs = {a["source_uri"] for a in manifest["assets"]}
    assert refs == {"tensor://reports/5559"}
    text = json.dumps(manifest, ensure_ascii=False)
    assert "tensor://reports/4129" not in text  # no bleed from a sibling package


# --------------------------------------------------------------- evidence claims
def test_declared_artifacts_are_registered_without_claiming_bytes(manifest: dict) -> None:
    arts = [a for a in manifest["assets"]
            if a["kind"] in {"figure_file_reference", "data_artifact_reference"}]
    assert len(arts) == 6
    for a in arts:
        assert a["resolution"]["status"] == "unresolved"
        assert a["existence_asserted_by_worker"] is False
    assert manifest["counts"]["artifact_bytes_retrieved"] == 0
    assert manifest["counts"]["figures_with_bytes"] == 0


def test_embedded_criteria_json_parses_and_is_consistent(markdown: str, manifest: dict) -> None:
    block = re.search(r"```json\n(.*?)\n```", markdown, re.S)
    assert block is not None
    embedded = json.loads(block.group(1))
    assert re.fullmatch(r"[0-9a-f]{64}", embedded["digest"])
    checks = {c["check"]: c for c in manifest["ref_consistency_checks"]}
    for name in ("grid_cells_equal_N", "coverage_from_count_control",
                 "coverage_relative_error", "coverage_quantization_bound",
                 "frazil_window_hours", "digest_prefix_header", "digest_prefix_table",
                 "record_captions_located_in_markdown",
                 "declared_png_sha_prefixes_shape"):
        assert checks[name]["consistent"] is True, name


def test_figure_set_mismatch_is_registered_not_hidden(manifest: dict) -> None:
    """Body links fig3, the record does not: the manifest must record this, not fix it."""
    checks = {c["check"]: c for c in manifest["ref_consistency_checks"]}
    figs = checks["body_vs_record_figure_sets"]
    assert figs["consistent"] is False
    assert figs["in_body_not_in_record"] == ["fig3_ridges.png"]
    assert figs["in_record_not_in_body"] == []
    obs = " ".join(manifest["observations"])
    assert "fig3_ridges.png" in obs

def test_offline_rebuild_reproduces_the_committed_manifest() -> None:
    """A verification run must reproduce the artefact and must not rewrite it."""
    import subprocess
    import sys

    before = MANIFEST.read_bytes()
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "kf_wp_5559_01_register.py"), "--offline"],
        capture_output=True, text=True, cwd=str(ROOT), check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SELF-CHECK PASS" in proc.stdout
    report = json.loads(proc.stdout[:proc.stdout.index("SELF-CHECK")].strip())
    assert report["offline_reproduction"]["reproduced"] is True
    assert report["offline_reproduction"]["differing_top_level_keys"] == []
    assert MANIFEST.read_bytes() == before, "offline verify must not mutate the artefact"
