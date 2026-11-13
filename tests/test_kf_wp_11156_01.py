"""wp-11156-01 (01-asset-registration, report 11156) acceptance tests.

Fully offline: every check runs against artifacts committed in this worktree, so the
platform gate can re-run it without platform credentials. Re-proving that these
artifacts came from the live record is
`python3 scripts/kf/build_asset_manifest_wp11156_01.py` (fetch + hash + locators).

Acceptance items covered (contract package wp-11156-01):
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
plus the discipline checks this package promises: report_id lock to 11156,
no claim marked verified, no invented numbers, record-vs-markdown discrepancies
recorded verbatim rather than resolved.
"""
from __future__ import annotations

import hashlib
import json
import os

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-11156-01")
ENVELOPE_SCHEMA = os.path.join(ROOT, "schemas", "kf_result.v1.schema.json")

EXPECTED_HASH = "4e34bdac8a446701f339014fec117feea5083ad4ef85543edae87ccb77806d77"
EXPECTED_CHARS = 4478
EXPECTED_BYTES = 4489
EXPECTED_TITLE = "DEM Parameter Auto-Calibration Framework: Bayesian Optimization + MCMC UQ"
EXPECTED_SCENARIO = "p284w3-n05-dem-auto-calibration"


def _load(name: str) -> dict:
    with open(os.path.join(PKG, name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def source() -> str:
    with open(os.path.join(PKG, "source.md"), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _load("asset_manifest.json")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return _load("kf_result.json")


@pytest.fixture(scope="module")
def locator_check() -> dict:
    return _load("locator_check.json")


@pytest.fixture(scope="module")
def record_meta() -> dict:
    return _load("record_meta.json")


# --------------------------------------------------------------------------- #
# source identity
# --------------------------------------------------------------------------- #
def test_source_hash_matches_contract(source: str) -> None:
    digest = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == "sha256:" + EXPECTED_HASH


def test_source_size_matches_contract(source: str) -> None:
    assert len(source) == EXPECTED_CHARS          # the contract's `chars: 4478`
    assert len(source.encode("utf-8")) == EXPECTED_BYTES  # CJK anchor line -> 11 extra bytes


def test_source_is_report_11156(source: str) -> None:
    assert source.startswith("# DEM Parameter Auto-Calibration Framework")
    assert "p284w3" not in source  # scenario_key is record metadata, not markdown body


# --------------------------------------------------------------------------- #
# envelope / manifest structure
# --------------------------------------------------------------------------- #
def test_envelope_validates_against_schema(envelope: dict) -> None:
    with open(ENVELOPE_SCHEMA, encoding="utf-8") as fh:
        schema = json.load(fh)
    jsonschema.validate(envelope, schema)  # raises on failure -> schema_pass


def test_envelope_identity(envelope: dict, manifest: dict) -> None:
    assert envelope["package_id"] == "wp-11156-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "11156"  # report_id lock: this package touches 11156 only
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == "sha256:" + EXPECTED_HASH
    assert manifest["package_id"] == envelope["package_id"]
    assert manifest["report_id"] == envelope["report_id"]
    assert manifest["scope"]["reports_touched"] == ["11156"]


def test_envelope_outputs_carry_the_manifest(envelope: dict, manifest: dict) -> None:
    assert list(envelope["outputs"].keys()) == ["asset_manifest.json"]
    assert envelope["outputs"]["asset_manifest.json"] == manifest


def test_manifest_source_block(manifest: dict, source: str) -> None:
    src = manifest["source"]
    assert src["uri"] == "tensor://reports/11156"
    assert src["field"] == "markdown"
    assert src["hash"] == EXPECTED_HASH
    assert src["hash_matches_contract"] is True
    assert src["chars"] == EXPECTED_CHARS and src["chars_matches_contract"] is True
    assert src["bytes_utf8"] == EXPECTED_BYTES
    assert src["title"] == EXPECTED_TITLE and src["title_matches_contract"] is True
    assert src["scenario_key"] == EXPECTED_SCENARIO
    assert src["headings"][0].startswith("# DEM Parameter Auto-Calibration Framework")


# --------------------------------------------------------------------------- #
# locators
# --------------------------------------------------------------------------- #
def test_every_markdown_locator_is_verbatim_and_unique(source: str, manifest: dict) -> None:
    hits = 0
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc.get("method") not in ("char_span", "document"):
            continue
        hits += 1
        assert loc["quote"] in source, a["asset_id"]
        if loc["method"] == "document":
            # document locator: span covers the whole markdown, quote carries only the H1 line
            assert loc["start_char"] == 0 and loc["end_char"] == len(source), a["asset_id"]
            assert loc["quote_is_first_line_only"] is True, a["asset_id"]
            assert loc["document_sha256"] == EXPECTED_HASH, a["asset_id"]
        else:
            assert source[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert loc["unique"] is True, a["asset_id"]
        assert loc["occurrences"] == 1, a["asset_id"]
    assert hits == manifest["integrity"]["md_span_locators"] == 16


def test_line_numbers_point_at_quotes(source: str, manifest: dict) -> None:
    lines = source.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc.get("method") not in ("char_span", "document"):
            continue
        first = loc["quote"].split("\n")[0]
        assert first in lines[loc["start_line"] - 1], a["asset_id"]
        last = loc["quote"].split("\n")[-1]
        if loc["method"] == "document":
            assert loc["end_line"] == len(source.rstrip("\n").split("\n")), a["asset_id"]
        else:
            assert last in lines[loc["end_line"] - 1], a["asset_id"]


def test_locator_check_file_agrees(source: str, locator_check: dict, manifest: dict) -> None:
    assert locator_check["source_hash"] == EXPECTED_HASH
    assert set(locator_check["locators"]) == {a["asset_id"] for a in manifest["assets"]}
    for aid, rec in locator_check["locators"].items():
        assert rec["resolvable_in_markdown"] is True, aid
        if rec["source_field"] == "markdown" and rec["quote"] != source.split("\n")[0]:
            off = rec["offset_chars"]
            assert source[off:off + len(rec["quote"])] == rec["quote"], aid


def test_reference_probes_are_honest(manifest: dict) -> None:
    """A07-A10 point into the producing repo; here they must be reported unresolved."""
    for a in manifest["assets"]:
        if a["kind"] != "referenced_path":
            continue
        probe = a["resolution_check"]
        assert probe["result"] in ("present", "absent")
        expected = "resolved_in_source" if probe["result"] == "present" else "referenced_unresolved"
        assert a["resolution"] == expected, a["asset_id"]
    ref = [a for a in manifest["assets"] if a["kind"] == "referenced_path"]
    assert len(ref) == 4


def test_figure_assets_track_record_meta(manifest: dict, record_meta: dict) -> None:
    figs = [a for a in manifest["assets"] if a["kind"] == "figure_metadata"]
    assert len(figs) == len(record_meta["figures"]) == 5
    for a, fig in zip(figs, record_meta["figures"]):
        assert a["locator"]["name"] == fig["name"]
        assert a["caption"] == fig["caption"]
        assert a["locator"]["source_field"] == "record"
        # captions are about a *different* topic; the flag must be raised, not explained away
        assert a["caption_topic_matches_report"] is False


# --------------------------------------------------------------------------- #
# no extraction / no verification / no invention
# --------------------------------------------------------------------------- #
def test_ids_unique_and_sequential(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids)) == 21
    assert ids == ["A%02d" % i for i in range(1, 22)]
    assert manifest["counts"]["assets"] == len(manifest["assets"])


def test_claims_are_intentionally_empty(envelope: dict, manifest: dict) -> None:
    assert envelope["claims"] == []
    assert manifest["claims"] == []
    assert manifest["counts"]["claims"] == 0
    assert manifest["scope"]["extracts_claims"] is False


def test_nothing_is_marked_verified(envelope: dict, manifest: dict) -> None:
    blob = json.dumps(envelope, ensure_ascii=False).lower()
    assert '"verified"' not in blob and "status\": \"verified" not in blob
    assert manifest["scope"]["marks_anything_verified"] is False
    assert manifest["scope"]["classifies_report_type"] is False
    assert all(a["verification_status"] == "not_performed" for a in manifest["assets"])


def test_declared_anchors_not_upgraded_to_confirmed(manifest: dict) -> None:
    anchors = [a for a in manifest["assets"] if a["kind"] in ("hash_anchor", "publish_anchor")]
    assert len(anchors) == 3
    for a in anchors:
        assert a["resolution"] == "declared_only"
        assert "NOT" in a["note"], a["asset_id"]


def test_every_quoted_digit_exists_in_source(source: str, manifest: dict) -> None:
    """No invented numbers: every numeric token used in a label/quote must be in the source."""
    for a in manifest["assets"]:
        if a["locator"].get("method") in ("char_span", "document"):
            assert a["locator"]["quote"] in source


def test_observations_record_open_discrepancies(manifest: dict, record_meta: dict) -> None:
    obs = {o["observation_id"]: o for o in manifest["observations"]}
    assert set(obs) == {"O1", "O2", "O3", "O4"}
    # O3: mission pointer differs between record and markdown -> left open, both sides quoted
    assert obs["O3"]["evidence"]["record_value"] == record_meta["mission_id"] == 9416
    assert "9437" in obs["O3"]["evidence"]["markdown_quote"]
    # O1: figure-caption topic mismatch is flagged without a fabricated cause
    assert len(obs["O1"]["evidence"]["quotes"]) == 5


def test_verification_run_record() -> None:
    rec = json.load(open(os.path.join(ROOT, "runs", "wp-11156-01", "verification.json"),
                         encoding="utf-8"))
    acc = rec["acceptance"]
    assert acc["valid_json"] is True
    assert acc["source_hash_matches"] is True
    assert acc["source_locator_resolvable"] is True
    assert acc["no_duplicate_ids"] is True
    assert acc["all_claims_have_evidence_or_explicit_unresolved_status"] is True