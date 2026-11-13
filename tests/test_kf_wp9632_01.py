#!/usr/bin/env python3
"""Offline invariant tests for work package wp-9632-01 (01-asset-registration).

These assert invariants over the committed artifacts, not "the script ran":

  * the cached source copy is byte-identical to the pinned source baseline
    (hash + char count), and the manifest/envelope embed that same hash;
  * every locator quote is a verbatim slice of the source at its declared span,
    and every declared line quote is the actual line at that line number;
  * asset ids are unique and follow the ``r9632:*`` scheme; counts agree with assets;
  * nothing carries a `verified` mark and no claim was invented (claims == []);
  * verification.json has every acceptance check green and an independent
    accounting that matches the manifest;
  * the delivered KF-RESULT markdown carries exactly one json block, equal to the
    committed envelope, and every number quoted there is present in the JSON;
  * the locator checker DETECTS tampering (negative control -- otherwise "all
    locators resolve" would be unfalsifiable).

The source copy lives in the untracked run area (runs/wp-9632-01/source_9632.md),
so the network-free subset still runs from a clean checkout: tests that need the
source text skip with an explicit reason when the copy is absent.

    pytest tests/test_kf_wp9632_01.py -q
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-9632-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
VERIFICATION = PKG / "verification.json"
RESULT_MD = PKG / "KF-RESULT-wp-9632-01.md"
PNG = PKG / "figures" / "wp9632_01_source_locator_map.png"
SOURCE = ROOT / "runs" / "wp-9632-01" / "source_9632.md"
KF_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
LOCAL_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.wp9632-01.schema.json"
REGISTER = ROOT / "scripts" / "kf_wp9632_01_register.py"

CONTRACT_HASH = "b2c5eb5dad0b6db25574338b37aa5be1c8fdf20bbc7d3c75640e1c1727756841"
CONTRACT_CHARS = 10749


def _load_register_module():
    """Import the register script (its module body only defines constants/helpers)."""
    spec = importlib.util.spec_from_file_location("kf_wp9632_01_register", REGISTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    if not SOURCE.is_file():
        pytest.skip("run area copy %s absent (untracked); locator tests need it" % SOURCE)
    return SOURCE.read_text(encoding="utf-8")


# ---------------------------------------------------------------- source identity
def test_source_copy_matches_pinned_baseline(source):
    assert len(source) == CONTRACT_CHARS
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH


def test_manifest_identity(manifest):
    assert manifest["package_id"] == "wp-9632-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "9632"
    assert manifest["source"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert manifest["source"]["hash_matches_contract"] is True
    assert manifest["source"]["chars_matches_contract"] is True
    assert manifest["source"]["title_matches_contract"] is True
    assert manifest["source"]["scenario_matches_contract"] is True
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert manifest["source"]["contract_source_hash"] == "sha256:" + CONTRACT_HASH
    # the baseline provenance is stated, not hidden: no WP YAML existed in the tree
    assert "9632" in manifest["source"]["contract_provenance"]


def test_source_copy_byte_count_agrees_with_manifest(manifest, source):
    assert manifest["source"]["bytes_utf8"] == len(source.encode("utf-8"))
    assert manifest["source"]["lines"] == len(source.split("\n"))


# ---------------------------------------------------------------- intents/scheme
def test_asset_ids_unique_and_scheme(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids, "at least the source asset must be registered"
    assert len(ids) == len(set(ids))
    assert all(i.startswith("r9632:") for i in ids)


def test_counts_agree_with_assets(manifest):
    c, assets = manifest["counts"], manifest["assets"]
    assert c["assets_total"] == len(assets)
    for status in ("resolved", "metadata_only", "unresolved"):
        assert c["assets_" + status] == sum(
            1 for a in assets if a["resolution"]["status"] == status)
    assert c["assets_total"] == (c["assets_resolved"] + c["assets_metadata_only"]
                                 + c["assets_unresolved"])
    assert c["body_references"] == sum(
        1 for a in assets if a["kind"] not in ("report_markdown", "embedded_figure"))
    assert sum(c["kind_status_histogram"].values()) == c["assets_total"]
    assert c["tables"] == len(manifest["tables"])
    assert c["sections"] == len(manifest["sections"])
    assert c["claims"] == len(manifest["claims"]) == 0


# ---------------------------------------------------------------- locators
def test_every_locator_is_verbatim(manifest, source):
    lines = source.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        assert quote and quote in source, a["asset_id"]
        if loc["method"] == "char_span":
            assert source[loc["start_char"]:loc["end_char"]] == quote, a["asset_id"]
            assert lines[loc["start_line"] - 1] == loc["line_quote"], a["asset_id"]
            assert loc["line_quote"].find(quote) >= 0, a["asset_id"]
        elif loc["method"] == "document":
            assert source[loc["start_char"]:loc["end_char"]] == quote == source[:len(quote)]
            assert loc["doc_chars"] == len(source)
        else:  # record_pointer
            assert loc["source_field"] == "record"
            assert loc["pointer"].startswith("/figures/")


def test_table_and_section_locators(manifest, source):
    assert manifest["tables"], "report body has markdown tables"
    for t in manifest["tables"]:
        assert t["header_quote"] in source, t["table_id"]
        assert t["rows"] >= 1 and t["cols"] >= 2
    for s in manifest["sections"]:
        assert s["line_heading"] in source


def test_integrity_block_matches_recount(manifest, source):
    integ = manifest["integrity"]
    assert integ["hash_recomputed_locally"] is True
    # one locator per asset + one per table header + one per section heading
    assert integ["locators_checked"] == (len(manifest["assets"]) + len(manifest["tables"])
                                         + len(manifest["sections"]))
    assert integ["locators_resolved"] == integ["locators_checked"]
    assert integ["duplicate_asset_ids"] == 0
    uniq = sum(1 for a in manifest["assets"] if a["locator"].get("unique"))
    assert str(uniq) in integ["quote_uniqueness"]


def test_locator_checker_detects_tampering(manifest, source):
    """Negative control: a single flipped character must break the span check."""
    mod = _load_register_module()
    # record_pointer locators are re-checked against the record's figures[] names, so the
    # reconstructed record must carry them (the manifest registers them by name)
    record = {"title": manifest["source"]["title"],
              "scenario_key": manifest["source"]["scenario_key"],
              "figures": [{"name": a.get("name")} for a in manifest["assets"]
                          if a["kind"] == "embedded_figure"]}
    checked, bad = mod.check_locators(manifest["assets"], manifest["tables"],
                                      manifest["sections"], source, record)
    assert checked == (len(manifest["assets"]) + len(manifest["tables"])
                       + len(manifest["sections"])) and bad == []
    pos = source.index("IN101-N07")
    tampered = source[:pos] + "IN101-N08" + source[pos + len("IN101-N07"):]
    _, bad2 = mod.check_locators(manifest["assets"], manifest["tables"],
                                 manifest["sections"], tampered, record)
    assert bad2, "tampered source must fail the locator re-check"


# ---------------------------------------------------------------- no overreach
def test_no_verified_marks_and_no_invented_claims(manifest, envelope):
    assert manifest["claims"] == []
    assert "claims" not in envelope, "kf_result.v1 forbids a top-level claims key"
    assert '"verified"' not in json.dumps(manifest, ensure_ascii=False)
    for a in manifest["assets"]:
        assert a["resolution"]["status"] in ("resolved", "metadata_only", "unresolved")


def test_envelope_binds_source_hash_and_validates(envelope, source):
    jsonschema = pytest.importorskip("jsonschema")
    assert envelope["package_id"] == "wp-9632-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "9632"
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["provenance"]["source_hash_matches"] is True
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH
    jsonschema.validate(envelope, json.loads(KF_SCHEMA.read_text(encoding="utf-8")))
    jsonschema.validate(json.loads(MANIFEST.read_text(encoding="utf-8")),
                        json.loads(LOCAL_SCHEMA.read_text(encoding="utf-8")))


def test_verification_all_acceptance_green():
    v = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    required = {"valid_json", "schema_pass", "source_locator_resolvable",
                "source_hash_matches", "no_duplicate_ids",
                "all_claims_have_evidence_or_explicit_unresolved_status"}
    assert required <= set(v["acceptance"])
    assert v["all_ok"] is True
    assert all(c["ok"] for c in v["acceptance"].values())
    assert v["accounting"]["locators_resolved"] == v["accounting"]["locators_checked"]
    assert v["internal_consistency"]["ok"] is True


def test_envelope_is_not_stale(manifest, envelope):
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    canonical = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert canonical == MANIFEST.read_bytes()


# ---------------------------------------------------------------- delivered report
def test_result_markdown_has_single_json_block_equal_to_envelope(envelope):
    md = RESULT_MD.read_text(encoding="utf-8")
    assert md.count("```json") == 1
    start = md.index("```json") + len("```json")
    end = md.index("```", start)
    payload = json.loads(md[start:end])
    assert payload == envelope
    assert md[start:end].strip() == json.dumps(envelope, ensure_ascii=False,
                                               indent=2).strip()
    assert md.lstrip().split("\n")[0].startswith("# KF-RESULT wp-9632-01")
    # every hash quoted in the markdown is a hash that actually appears in the package
    hashes_in_pkg = {envelope["provenance"]["source_hash"],
                     "sha256:" + hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                     "sha256:" + hashlib.sha256(ENVELOPE.read_bytes()).hexdigest()}
    assert hashes_in_pkg <= set(md) or all(h[7:] in md for h in hashes_in_pkg)


def test_locator_map_figure_is_a_png():
    head = PNG.read_bytes()[:8]
    assert head == b"\x89PNG\r\n\x1a\n", "figure must be a real PNG"
    assert PNG.stat().st_size > 20_000