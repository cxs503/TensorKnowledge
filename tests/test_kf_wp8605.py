"""Invariant tests for work package wp-8605-01 (asset registration of report 8605).

Every acceptance item is asserted on the real committed artifacts, and each check is paired with a
negative control (tampered manifest / tampered figure) so the test proves the check can fail rather
than merely executing code.

Run: pytest -q tests/test_kf_wp8605.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import shutil
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kf_fetch_8605 as kf  # noqa: E402

DOCS = ROOT / "docs/wp-8605-01"
MD_PATH = DOCS / "source_report_8605.md"
MANIFEST_PATH = DOCS / "asset_manifest.json"
VERIFICATION_PATH = DOCS / "verification.json"
SCHEMA_PATH = ROOT / "schemas/asset_manifest.v1.generic.schema.json"
# sha256 of the frozen source copy; changing it means the registered source changed (re-register).
SOURCE_SHA256 = "a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36"


@pytest.fixture(scope="module")
def md() -> str:
    return MD_PATH.read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="module")
def verification() -> dict:
    return json.loads(VERIFICATION_PATH.read_text())


# --------------------------------------------------------------------------- source identity
def test_source_frozen_copy_hash(md, manifest):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == SOURCE_SHA256
    assert manifest["source"]["hash"] == SOURCE_SHA256
    assert manifest["source"]["chars"] == len(md) == 8006
    assert manifest["source"]["bytes_utf8"] == len(md.encode("utf-8"))
    assert manifest["source"]["uri"] == "tensor://reports/8605"
    assert manifest["report_id"] == "8605" and manifest["package_id"] == "wp-8605-01"
    assert manifest["task_type"] == "01-asset-registration"


def test_source_hash_check_detects_tampered_source(md, manifest):
    tampered = md.replace("2.3390", "2.3391", 1)
    assert tampered != md
    assert kf.sha256(tampered) != manifest["source"]["hash"]
    assert any(c["check"] == "source_hash_recomputed" and c["result"] == "fail"
               for c in kf.verify(manifest, tampered, DOCS)["checks"])


def test_manifest_validates_against_generic_schema(manifest):
    jsonschema.validate(manifest, json.loads(SCHEMA_PATH.read_text()))


def test_schema_gate_can_fail(manifest):
    broken = copy.deepcopy(manifest)
    broken["task_type"] = "02-extraction"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(broken, json.loads(SCHEMA_PATH.read_text()))


# --------------------------------------------------------------------------- locators
def test_every_locator_reresolves(md, manifest):
    assert kf.check_locators(md, manifest) == []


def test_locator_negative_control_tampered_quote(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = next(x for x in tampered["assets"] if x["locator"]["method"] == "char_span")
    a["locator"]["quote"] = a["locator"]["quote"] + "X"
    assert any(asset == a["asset_id"] for asset, _ in kf.check_locators(md, tampered))


def test_locator_negative_control_shifted_span(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = next(x for x in tampered["assets"] if x["asset_class"] == "standard_reference")
    a["locator"]["start_char"] += 1
    assert any(asset == a["asset_id"] and why == "slice_mismatch"
               for asset, why in kf.check_locators(md, tampered))


def test_locator_negative_control_wrong_section(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = next(x for x in tampered["assets"] if x["asset_class"] == "figure_reference")
    a["in_report_section"] = "§1 案例介绍（物理背景 / 几何 / 参数表）"
    assert any(asset == a["asset_id"] and why == "section_mismatch"
               for asset, why in kf.check_locators(md, tampered))


def test_document_locator_covers_whole_source(md, manifest):
    doc = next(a for a in manifest["assets"] if a["locator"]["method"] == "document")
    assert doc["locator"]["start_char"] == 0 and doc["locator"]["end_char"] == len(md)
    assert doc["locator"]["quote"] == md and doc["resolution"] == "resolved_in_source"


# --------------------------------------------------------------------------- honesty / counts
def test_no_asset_is_filled_in(md, manifest):
    """resolved_in_source only for the document itself; nothing else claims bytes it does not have."""
    assert kf.check_resolution_honesty(md, manifest) == []
    resolved = [a for a in manifest["assets"] if a["resolution"] == "resolved_in_source"]
    assert [a["asset_id"] for a in resolved] == ["A01"]


def test_resolution_honesty_negative_control(md, manifest):
    tampered = copy.deepcopy(manifest)
    a = next(x for x in tampered["assets"] if x["asset_class"] == "data_artifact")
    a["resolution"] = "resolved_in_source"  # claims local bytes it does not have
    a["resolution_check"]["result"] = "resolved"
    assert any(asset == a["asset_id"] for asset, _ in kf.check_resolution_honesty(md, tampered))


def test_declared_absent_are_self_declared_by_report(md, manifest):
    absent = [a for a in manifest["assets"] if a["resolution"] == "declared_absent"]
    assert len(absent) == 3
    for a in absent:
        assert a["locator"]["quote"] in md
        assert a["asset_id"] in json.dumps(manifest["claims"], ensure_ascii=False)


def test_counts_consistent_and_negative_control(manifest):
    assert kf.check_counts(manifest) == []
    tampered = copy.deepcopy(manifest)
    tampered["counts"]["referenced_unresolved"] -= 1
    assert ("counts", "referenced_unresolved") in kf.check_counts(tampered)


def test_asset_ids_unique_and_well_formed(manifest):
    assert kf.check_ids(manifest) == []
    tampered = copy.deepcopy(manifest)
    tampered["assets"].append(copy.deepcopy(tampered["assets"][1]))
    assert any(why.startswith("duplicate") for _, why in kf.check_ids(tampered))


def test_rule_recall_no_reference_dropped(md, manifest):
    """Every distinct token matched by the 6 mechanical rules must be registered."""
    registered = {(a["asset_class"], a["label"]) for a in manifest["assets"]}
    missing = {(cls, m.group(0)) for cls, rx in kf.RULES for m in rx.finditer(md)
               if (cls, m.group(0)) not in registered}
    assert missing == set()
    tampered = {"assets": [a for a in manifest["assets"] if a["asset_class"] != "figure_reference"]}
    missing = {(cls, m.group(0)) for cls, rx in kf.RULES for m in rx.finditer(md)
               if (cls, m.group(0)) not in {(a["asset_class"], a["label"]) for a in tampered["assets"]}}
    assert len(missing) == manifest["counts"]["by_class"]["figure_reference"]


def test_claims_carry_evidence(manifest, md):
    for claim in manifest["claims"]:
        assert any(k in claim for k in ("evidence", "evidence_locator", "status"))
    c01 = manifest["claims"][0]
    assert c01["evidence"]["hash"] == manifest["source"]["hash"]
    assert c01["evidence"]["chars"] == len(md)
    fig_names = [f["name"] for f in manifest["source"]["platform_figures"]]
    assert manifest["claims"][1]["evidence"]["figure_names"] == fig_names
    assert manifest["claims"][1]["evidence"]["png_bytes_present"] is False


# --------------------------------------------------------------------------- verification.json
EXPECTED_CHECKS = ["source_hash_recomputed", "locators_reslice", "resolution_honesty",
                   "counts_consistent", "asset_ids", "figures_present", "rule_recall",
                   "claims_have_evidence", "schema_pass"]


def test_verification_all_pass_and_complete(verification, manifest):
    assert [c["check"] for c in verification["checks"]] == EXPECTED_CHECKS
    assert all(c["result"] == "pass" for c in verification["checks"])
    assert verification["result"] == "pass"
    assert verification["source_hash_recomputed"] == "sha256:" + manifest["source"]["hash"]
    assert verification["package_id"] == "wp-8605-01"


def test_verification_is_reproducible(md, manifest, verification):
    recorded = next(c for c in verification["checks"] if c["check"] == "figures_present")["detail"]["sha256"]
    assert kf.verify(manifest, md, DOCS, recorded) == verification
    assert kf.recorded_figures(DOCS) == recorded


def test_figure_hashes_match_recorded(verification):
    recorded = next(c for c in verification["checks"] if c["check"] == "figures_present")["detail"]["sha256"]
    assert set(recorded) == {"fig_asset_inventory.png", "fig_locator_coverage.png"}
    for name, digest in recorded.items():
        raw = (DOCS / name).read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(raw) > 10_000
        assert hashlib.sha256(raw).hexdigest() == digest
    assert (DOCS / "fig_verification.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_tampered_figure_is_detected(tmp_path, md, manifest):
    for p in DOCS.glob("*.png"):
        shutil.copy(p, tmp_path / p.name)
    target = tmp_path / "fig_asset_inventory.png"
    raw = bytearray(target.read_bytes())
    raw[-1] ^= 0xFF  # flip one byte inside the PNG tail
    target.write_bytes(bytes(raw))
    recorded = next(c for c in json.loads(VERIFICATION_PATH.read_text())["checks"]
                    if c["check"] == "figures_present")["detail"]["sha256"]
    ver = kf.verify(manifest, md, tmp_path, recorded)
    check = next(c for c in ver["checks"] if c["check"] == "figures_present")
    assert check["result"] == "fail" and ver["result"] == "fail"


def test_non_png_figure_is_detected(tmp_path, md, manifest):
    for p in DOCS.glob("*.png"):
        shutil.copy(p, tmp_path / p.name)
    (tmp_path / "fig_asset_inventory.png").write_bytes(b"not a png at all")
    ver = kf.verify(manifest, md, tmp_path)
    assert ("fig_asset_inventory.png", "not_png") in [
        tuple(x) for c in ver["checks"] if c["check"] == "figures_present" for x in c["detail"]["failures"]]


def test_missing_figure_is_detected(tmp_path, md, manifest):
    for p in DOCS.glob("*.png"):
        shutil.copy(p, tmp_path / p.name)
    (tmp_path / "fig_locator_coverage.png").unlink()
    recorded = next(c for c in json.loads(VERIFICATION_PATH.read_text())["checks"]
                    if c["check"] == "figures_present")["detail"]["sha256"]
    ver = kf.verify(manifest, md, tmp_path, recorded)
    assert next(c for c in ver["checks"] if c["check"] == "figures_present")["result"] == "fail"


# --------------------------------------------------------------------------- determinism
def test_scan_is_deterministic_and_dedups(manifest, md):
    again = kf.scan_assets(md)
    assert [(a["asset_id"], a["label"], a["resolution"]) for a in again] == \
           [(a["asset_id"], a["label"], a["resolution"]) for a in manifest["assets"]]
    labels = [a["label"] for a in again]
    assert len(labels) == len(set(labels))


def test_manifest_rebuilds_from_frozen_source(manifest, md):
    payload = dict(manifest["source"])
    rebuilt = kf.build_manifest(payload, md)
    assert rebuilt["assets"] == manifest["assets"]
    assert rebuilt["counts"] == manifest["counts"]


def test_scope_is_single_report(manifest):
    """Nothing outside report 8605 may be referenced by the registration."""
    assert {a["resolution"] for a in manifest["assets"]} <= {
        "resolved_in_source", "referenced_unresolved", "declared_absent"}
    assert manifest["source"]["platform_id"] == 8605
    assert all("reports/" not in a["label"] for a in manifest["assets"])