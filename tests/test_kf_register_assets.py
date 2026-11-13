"""wp-7920-01 (01-asset-registration, report 7920) acceptance tests.

The generic lane tools are exercised end-to-end offline: the report record is committed
as ``docs/kf/wp-7920-01/source_7920.json`` (byte-identical to ``GET /tensor/reports/7920``),
so registration, verification and rendering can be re-run with no platform credentials.

What is asserted
----------------
* genericity/determinism: re-running ``register_assets.build_manifest`` on the snapshot
  reproduces the committed manifest byte for byte, with no report-459 residue;
* the committed artefacts validate against the shared gate schemas;
* every locator re-resolves on the source bytes (span + verbatim quote + line + hash);
* the published receipt is honest (real report id, round-trip envelope match);
* the result report is in sync with the artefacts (re-rendered bytes are identical);
* negative controls: a tampered manifest / wrong record must make verification FAIL, so
  the gate is falsifiable rather than vacuously green.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-7920-01")
RECORD = os.path.join(PKG, "source_7920.json")
REPORT_MD = os.path.join(ROOT, "docs", "reports", "kf_wp_7920_01_result.md")

sys.path.insert(0, os.path.join(ROOT, "scripts", "kf"))

import publish_report as pr  # noqa: E402
import register_assets as ra  # noqa: E402


def load(path, *more):
    with open(os.path.join(path, *more), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def record() -> dict:
    return load(RECORD)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load(PKG, "asset_manifest.json")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return load(PKG, "kf_result.json")


@pytest.fixture(scope="module")
def verification() -> dict:
    return load(PKG, "verification.json")


@pytest.fixture(scope="module")
def receipt() -> dict:
    return load(PKG, "publish_receipt.json")


# --------------------------------------------------------------------------- #
# registration: generic + deterministic + zero hand-copy
# --------------------------------------------------------------------------- #
def test_builder_is_generic_and_reproduces_committed_manifest(record, manifest):
    rebuilt = ra.build_manifest(
        record,
        package_id="wp-7920-01",
        expect_chars=None,
        repo_root=__import__("pathlib").Path(ROOT),
        lane="C",
    )
    assert rebuilt == manifest
    blob = json.dumps(rebuilt, ensure_ascii=False)
    assert "wp-459" not in blob and "asset-459" not in blob
    assert "reports/459" not in blob


def test_builder_is_deterministic(record, manifest):
    """No wall clock: two builds of the same record give identical bytes."""
    a = json.dumps(ra.build_manifest(record, package_id="wp-7920-01",
                                     repo_root=__import__("pathlib").Path(ROOT)),
                   ensure_ascii=False)
    b = json.dumps(ra.build_manifest(record, package_id="wp-7920-01",
                                     repo_root=__import__("pathlib").Path(ROOT)),
                   ensure_ascii=False)
    assert a == b
    assert "generated_at" not in a and "emitted_at" not in a


def test_source_hash_is_recomputed_from_bytes(record, manifest, envelope):
    digest = hashlib.sha256(record["markdown"].encode("utf-8")).hexdigest()
    assert manifest["source"]["hash"] == digest
    assert manifest["source"]["chars"] == len(record["markdown"])
    assert manifest["source"]["bytes_utf8"] == len(record["markdown"].encode("utf-8"))
    assert manifest["integrity"]["hash_recomputed_locally"] is True
    assert manifest["integrity"]["hash_matches_contract"] is True
    assert envelope["provenance"]["source_hash"] == "sha256:" + digest
    assert envelope["provenance"]["source_hash_matches"] is True


def test_envelope_embeds_the_manifest_verbatim(manifest, envelope):
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    assert envelope["package_id"] == manifest["package_id"] == "wp-7920-01"
    assert envelope["report_id"] == manifest["report_id"] == "7920"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["contract_version"] == "1.0"


# --------------------------------------------------------------------------- #
# schemas
# --------------------------------------------------------------------------- #
def test_manifest_validates_against_shared_schema(manifest):
    schema = load(os.path.join(ROOT, "schemas"), "asset_manifest.v1.schema.json")
    jsonschema.validate(manifest, schema)


def test_envelope_validates_against_shared_schema(envelope):
    schema = load(os.path.join(ROOT, "schemas"), "kf_result.v1.schema.json")
    jsonschema.validate(envelope, schema)


# --------------------------------------------------------------------------- #
# locators + counts
# --------------------------------------------------------------------------- #
def test_every_locator_resolves_on_source_bytes(record, manifest):
    md = record["markdown"]
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids)) >= 2
    for asset in manifest["assets"]:
        loc = asset["locator"]
        quote = loc["quote"]
        assert quote and quote in md, asset["asset_id"]
        if loc["method"] == "document":
            assert loc["start_char"] == 0 and loc["end_char"] == len(md)
        else:
            assert md[loc["start_char"]: loc["end_char"]] == quote
            assert md[: loc["start_char"]].count("\n") + 1 == loc["start_line"]
            assert loc["occurrences"] == md.count(quote)
        assert hashlib.sha256(quote.encode("utf-8")).hexdigest() == loc["quote_sha256"]


def test_counts_match_assets(manifest):
    counts = manifest["counts"]
    assets = manifest["assets"]
    assert counts["assets"] == len(assets)
    assert sum(counts["by_class"].values()) == len(assets)
    assert sum(counts["by_resolution"].values()) == len(assets)
    assert counts["markdown_locators"] == sum(
        1 for a in assets if a["locator"]["method"] == "char_span"
    )
    for status in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert counts[status] == counts["by_resolution"].get(status, 0)


def test_registration_never_claims_verification(manifest):
    assert manifest["claims"] == []
    assert "no extraction" in manifest["claims_note"]
    assert "no asset is marked verified" in manifest["integrity"]["verified_logic"]
    blob = json.dumps(manifest, ensure_ascii=False).lower()
    assert '"verified": true' not in blob


def test_figure_payloads_are_not_invented(manifest, record):
    """Record ships figure names/captions only -> registration must say unresolved."""
    payloads = [f.get("png_base64") or "" for f in record.get("figures") or []]
    assert payloads and not any(payloads)
    figures = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    assert len(figures) == len(record["figures"])
    for asset in figures:
        assert asset["resolution"] == "referenced_unresolved"
        assert asset["resolution_check"]["result"] == "unresolved"


# --------------------------------------------------------------------------- #
# verification stage
# --------------------------------------------------------------------------- #
def test_verify_iteration_passes_and_matches_committed(record, manifest, verification):
    fresh = pr.verify_package(__import__("pathlib").Path(PKG), record)
    assert fresh["all_ok"] is True
    assert verification["all_ok"] is True
    for key in ("package_id", "report_id", "live_source_hash", "assets",
                "locators_rechecked", "acceptance"):
        assert fresh[key] == verification[key], key
    items = [a["item"] for a in fresh["acceptance"]]
    assert items == [
        "valid_json",
        "schema_pass",
        "source_hash_matches",
        "source_locator_resolvable",
        "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status",
        "envelope_matches_manifest",
        "counts_consistent",
    ]


def test_verify_fails_on_tampered_span(record, tmp_path):
    """Negative control: a shifted char span must be caught."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    manifest = load(PKG, "asset_manifest.json")
    bad = copy.deepcopy(manifest)
    asset = next(a for a in bad["assets"] if a["locator"]["method"] == "char_span")
    asset["locator"]["start_char"] += 1
    asset["locator"]["end_char"] += 1
    (pkg / "asset_manifest.json").write_text(json.dumps(bad), encoding="utf-8")
    (pkg / "kf_result.json").write_text(json.dumps(load(PKG, "kf_result.json")),
                                        encoding="utf-8")
    out = pr.verify_package(pkg, record)
    assert out["all_ok"] is False
    item = next(a for a in out["acceptance"] if a["item"] == "source_locator_resolvable")
    assert item["pass"] is False and item["failures"]


def test_verify_fails_on_wrong_record(tmp_path):
    """Negative control: verifying against another report's bytes must be red."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "asset_manifest.json").write_text(
        json.dumps(load(PKG, "asset_manifest.json")), encoding="utf-8")
    (pkg / "kf_result.json").write_text(json.dumps(load(PKG, "kf_result.json")),
                                       encoding="utf-8")
    other = {"id": "7920", "markdown": "# different bytes\n"}
    out = pr.verify_package(pkg, other)
    assert out["all_ok"] is False
    hash_item = next(a for a in out["acceptance"] if a["item"] == "source_hash_matches")
    assert hash_item["pass"] is False


# --------------------------------------------------------------------------- #
# render + publish
# --------------------------------------------------------------------------- #
def test_report_is_in_sync_with_artefacts(verification):
    rendered = pr.render_report(__import__("pathlib").Path(PKG), verification)
    with open(REPORT_MD, encoding="utf-8") as fh:
        committed = fh.read()
    assert rendered == committed
    assert "6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b" in committed


def test_publish_receipt_is_honest(receipt, envelope):
    assert isinstance(receipt["published_report_id"], int)
    assert receipt["published_report_id"] > 0
    assert receipt["package_id"] == "wp-7920-01"
    assert receipt["report_id"] == "7920"
    assert receipt["hash_roundtrip_match"] is True
    assert receipt["envelope_source_hash"] == envelope["provenance"]["source_hash"]
    assert receipt["result_json_parses"] is True
    assert receipt["json_blocks_in_markdown"] == 1
    assert all(receipt["checks"].values())
    assert "kf-wp:wp-7920-01" in receipt["published_tags"]