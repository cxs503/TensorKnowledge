"""KF work package wp-13272-01 (01-asset-registration) artifact invariants.

Self-contained and offline: the manifest stores the whole pinned markdown as the quote of
the ``document`` asset, so every other locator can be re-resolved without the network.
Run:  python -m pytest tests/test_kf_wp13272_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-13272-01"
REPORT_ID = "13272"
CONTRACT_HASH = "sha256:75ed781cefac9fee890f493c256dec8aea2e70795eca9d7a8bbfef1af1bcce90"
CONTRACT_CHARS = 4537
CONTRACT_BYTES = 6829
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _load(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _load("asset_manifest.json")


@pytest.fixture(scope="module")
def acceptance() -> dict:
    return _load("acceptance.json")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return _load("kf_result.json")


@pytest.fixture(scope="module")
def source_md(manifest) -> str:
    docs = [a for a in manifest["assets"] if a["locator"]["method"] == "document"]
    assert len(docs) == 1
    return docs[0]["locator"]["quote"]


@pytest.fixture(scope="module")
def pinned_md() -> str:
    return (OUT / "source" / "report_13272.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ schemas & envelope
def test_manifest_matches_kf_asset_manifest_schema(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "asset_manifest_kf.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_envelope_matches_kf_result_schema(envelope):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["package_id"] == "wp-13272-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == REPORT_ID
    assert envelope["claims"] == []
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_hash_matches"] is True


def test_envelope_outputs_are_consistent_with_files(envelope, manifest, acceptance):
    outputs = envelope["outputs"]
    assert set(outputs) >= {"asset_manifest.json", "acceptance.json", "fig1_asset_resolution.png"}
    assert outputs["asset_manifest.json"] == manifest
    assert outputs["acceptance.json"] == acceptance
    fig = outputs["fig1_asset_resolution.png"]
    blob = (ROOT / fig["path"]).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == fig["sha256"]
    assert len(blob) == fig["bytes"]


# ------------------------------------------------------------------ source pinning
def test_source_hash_and_size_match_contract(source_md, pinned_md, manifest):
    assert source_md == pinned_md
    assert "sha256:" + hashlib.sha256(source_md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(source_md) == CONTRACT_CHARS
    assert len(source_md.encode("utf-8")) == CONTRACT_BYTES
    src = manifest["source"]
    assert src["source_hash"] == CONTRACT_HASH
    assert src["hash_match"] is True
    assert (src["chars"], src["bytes"]) == (CONTRACT_CHARS, CONTRACT_BYTES)
    assert src["report_id"] == REPORT_ID and src["source_uri"] == "tensor://reports/13272"


def test_record_snapshot_matches_pinned_markdown():
    record = _load("source/report_13272.record.json")
    assert record["markdown_sha256"] == CONTRACT_HASH[7:]
    assert (record["markdown_chars"], record["markdown_bytes_utf8"]) == (CONTRACT_CHARS, CONTRACT_BYTES)
    assert record["id"] == int(REPORT_ID) and record["status"] == "published"
    assert "markdown" not in record


# ------------------------------------------------------------------ locators
def test_every_markdown_locator_resolves_inside_the_source(manifest, source_md):
    bad = []
    for asset in manifest["assets"]:
        loc = asset["locator"]
        if loc["method"] != "char_span":
            continue
        if source_md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            bad.append(asset["asset_id"])
        if hashlib.sha256(loc["quote"].encode("utf-8")).hexdigest() != loc["quote_sha256"]:
            bad.append(asset["asset_id"])
    assert bad == []


def test_locator_line_numbers_match_char_offsets(manifest, source_md):
    starts = [0] + [i + 1 for i, ch in enumerate(source_md) if ch == "\n"]

    def line_of(offset: int) -> int:
        return max(i for i, s in enumerate(starts) if s <= offset) + 1

    for asset in manifest["assets"]:
        loc = asset["locator"]
        if loc["method"] != "char_span":
            continue
        assert (loc["start_line"], loc["end_line"]) == (
            line_of(loc["start_char"]), line_of(max(loc["start_char"], loc["end_char"] - 1)))


def test_every_locator_is_unique_and_quotes_are_not_empty(manifest, source_md):
    ids = set()
    for asset in manifest["assets"]:
        loc = asset["locator"]
        assert loc["unique"] is True, asset["asset_id"]
        assert loc["occurrences"] >= 1
        assert loc["quote"].strip()
        if loc["method"] == "char_span":
            # the token (or the anchor line) must really be findable at the recorded span
            assert asset["token"] in loc["quote"] or loc["quote"] in source_md
        assert asset["asset_id"] not in ids, "duplicate asset_id %s" % asset["asset_id"]
        ids.add(asset["asset_id"])


# ------------------------------------------------------------------ structure coverage
def test_structural_assets_cover_the_document(manifest, source_md):
    headings = [ln for ln in source_md.split("\n") if ln.startswith("## ")]
    assert len(headings) == 8
    sections = {a["token"] for a in manifest["assets"] if a["asset_class"] == "report_section"}
    for head in headings:
        assert head in sections
    assert any(a["asset_id"].endswith("preamble") for a in manifest["assets"])

    tables = [a for a in manifest["assets"] if a["asset_class"] == "report_table"]
    assert len(tables) == 3
    assert all(t["locator"]["quote"].count("\n") >= 3 for t in tables)

    fences = [a for a in manifest["assets"] if a["asset_class"] == "repro_command_block"]
    assert len(fences) == 1
    assert fences[0]["locator"]["quote"].startswith("```bash")
    assert "pytest" in fences[0]["locator"]["quote"]


# ------------------------------------------------------------------ figure resolution
def test_declared_figure_bytes_are_pinned_and_valid(manifest):
    record = _load("source/report_13272.record.json")
    declared = record["figures"]
    assert len(declared) == 1
    fig_assets = [a for a in manifest["assets"] if a["asset_class"] == "declared_figure"]
    assert len(fig_assets) == 1
    asset = fig_assets[0]
    assert asset["resolution"]["status"] == "resolved"
    pinned = [f for f in record["figure_fetch"] if f["status"] == "resolved_bytes"]
    assert len(pinned) == 1
    blob = (ROOT / pinned[0]["pinned_path"]).read_bytes()
    assert blob.startswith(PNG_MAGIC)
    width, height = struct.unpack(">II", blob[16:24])
    assert (width, height) == tuple(pinned[0]["png_width_height"])
    assert hashlib.sha256(blob).hexdigest() == pinned[0]["sha256"]
    assert manifest["counts"]["figures_with_pinned_bytes"] == manifest["counts"]["figures_declared"] == 1


# ------------------------------------------------------------------ honesty / boundary
def test_cross_repo_referents_are_metadata_only_with_reason(manifest):
    cross = [a for a in manifest["assets"] if a["resolution"]["status"] == "metadata_only"]
    assert cross, "cross-repo referents must not silently count as resolved"
    for asset in cross:
        assert asset["resolution"].get("reason"), asset["asset_id"]
        assert "ship-performance-platform" in asset["resolution"]["reason"]
    classes = {a["asset_class"] for a in cross}
    assert classes <= {"code_or_artifact_path", "test_path", "declared_figure_artifact"}


def test_no_repro_command_was_executed_here(manifest):
    for asset in manifest["assets"]:
        for check in asset["resolution"]["checks"]:
            if check["check"] == "executed_here":
                assert check["result"] == "no"


def test_work_package_boundary_single_report(manifest):
    blob = json.dumps(manifest, ensure_ascii=False)
    uris = {part.split('"')[0] for part in blob.split("tensor://reports/")[1:]}
    assert len(uris) == 1 and all(u.startswith(REPORT_ID) for u in uris)
    assert str(manifest["report_id"]) == REPORT_ID


# ------------------------------------------------------------------ counts & acceptance
def test_counts_recomputed_from_asset_list(manifest):
    counts = manifest["counts"]
    by_class, by_res = {}, {}
    for asset in manifest["assets"]:
        by_class[asset["asset_class"]] = by_class.get(asset["asset_class"], 0) + 1
        by_res[asset["resolution"]["status"]] = by_res.get(asset["resolution"]["status"], 0) + 1
    assert counts["assets"] == len(manifest["assets"]) == sum(by_class.values()) == sum(by_res.values())
    assert counts["by_class"] == dict(sorted(by_class.items()))
    assert counts["by_resolution"] == dict(sorted(by_res.items()))
    assert counts["markdown_locators"] == len(manifest["assets"])
    assert counts["claims"] == 0 and manifest["claims"] == []


def test_acceptance_items_all_pass_and_are_unique(acceptance, manifest):
    assert acceptance["package_id"] == "wp-13272-01"
    ids = [c["id"] for c in acceptance["checks"]]
    assert len(ids) == len(set(ids))
    failed = [c for c in acceptance["checks"] if not c["pass"]]
    assert failed == [], failed
    assert acceptance["summary"]["all_pass"] is True
    assert acceptance["summary"]["failed"] == 0
    assert acceptance["source_hash"] == manifest["source"]["source_hash"]


def test_acceptance_figure_check_matches_the_rendered_png(acceptance):
    check = [c for c in acceptance["checks"] if c["id"] == "AC16"][0]
    assert check["pass"] is True
    blob = (OUT / "fig1_asset_resolution.png").read_bytes()
    assert blob.startswith(PNG_MAGIC) and len(blob) > 10_000
    assert "fig1_asset_resolution.png" in check["observed"]


# ------------------------------------------------------------------ determinism
def test_rebuild_is_byte_identical(manifest, tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    register = pytest.importorskip("wp13272_register_assets")
    # render into a temp dir so the committed PNG is never rewritten by the test run
    rebuilt_manifest, rebuilt_acceptance, rebuilt_envelope = register.build_all(
        manifest["generated_at"], tmp_path / "fig1_asset_resolution.png")
    assert rebuilt_manifest == manifest
    assert rebuilt_acceptance == _load("acceptance.json")
    assert rebuilt_envelope == _load("kf_result.json")