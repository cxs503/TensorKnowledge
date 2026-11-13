"""Offline machine checks for wp-10542-01 (01-asset-registration, report 10542).

These tests never touch the network: the byte-level source of truth is the copy
pulled by the work package (`runs/wp-10542-01/source_10542.md`), whose sha256 is
pinned by the work-package contract. They assert *invariants* (identity, locator
resolvability, schema conformance, no verified marks), not merely that the code
ran.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-10542-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
VERIFICATION = PKG / "verification.json"
SOURCE = ROOT / "runs" / "wp-10542-01" / "source_10542.md"
CONTRACT_HASH = "87ad4490786462c1c9b276ab29a0566caa363a5b211d01f4969fb816f60ce43c"
CONTRACT_CHARS = 12118


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text())


@pytest.fixture(scope="module")
def md() -> str:
    return SOURCE.read_text()


def test_source_hash_matches_contract(manifest, envelope, md):
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert manifest["source"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS == manifest["source"]["chars"]


def test_every_locator_resolves_to_exact_bytes(manifest, md):
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        s0 = loc["start_char"]
        assert md[s0:s0 + len(q)] == q, a["asset_id"]
        occ = []
        i = md.find(q)
        while i >= 0:
            occ.append(i)
            i = md.find(q, i + 1)
        assert s0 in occ, a["asset_id"]
        assert occ.index(s0) == loc["occurrence_index"], a["asset_id"]
        assert len(occ) == loc["occurrences"], a["asset_id"]
        assert loc["unique"] == (len(occ) == 1), a["asset_id"]
        assert md.count("\n", 0, s0) + 1 == loc["start_line"], a["asset_id"]
        assert hashlib.sha256(q.encode("utf-8")).hexdigest() == loc["quote_sha256"]


def test_asset_ids_unique_and_well_formed(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("A") and i[1:].isdigit() and len(i) == 3 for i in ids)
    assert manifest["counts"]["assets"] == len(ids)


def test_resolution_bookkeeping_is_consistent(manifest):
    counts = manifest["counts"]
    hist: dict[str, int] = {}
    for a in manifest["assets"]:
        hist[a["resolution"]] = hist.get(a["resolution"], 0) + 1
    assert counts["by_resolution"] == hist
    for key in ("resolved_in_source", "metadata_only", "referenced_unresolved", "declared_absent"):
        assert counts[key] == hist.get(key, 0), key
    # every asset states *how* it was resolved
    for a in manifest["assets"]:
        assert a["resolution_check"]["check"]
        assert a["note"]


def test_reference_recall_is_complete(manifest):
    rc = manifest["reference_recall"]
    assert rc["recall_complete"] is True
    assert rc["unexplained_tokens"] == []
    assert rc["distinct_paths_registered"] == manifest["counts"]["distinct_referenced_paths"]


def test_schemas_validate(manifest, envelope):
    kf = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.Draft202012Validator(kf).validate(envelope)
    reg = json.loads((ROOT / "schemas" / "asset_manifest.registration.v1.schema.json").read_text())
    jsonschema.Draft202012Validator(reg).validate(manifest)
    assert list(envelope["outputs"]) == ["asset_manifest.json"]
    assert envelope["outputs"]["asset_manifest.json"]["package_id"] == "wp-10542-01"


def test_figure_bytes_are_pinned_and_real(manifest):
    import struct

    figs = [a for a in manifest["assets"] if a.get("figure_bytes")]
    assert len(figs) == 2, "both record-declared figures must carry byte evidence"
    for a in figs:
        fb = a["figure_bytes"]
        p = ROOT / fb["local_copy"]
        b = p.read_bytes()
        assert hashlib.sha256(b).hexdigest() == fb["sha256"], a["asset_id"]
        assert len(b) == fb["bytes"]
        assert b[:8] == b"\x89PNG\r\n\x1a\n"
        w, h = struct.unpack(">II", b[16:24])
        assert (w, h) == (fb["png_size_px"]["width"], fb["png_size_px"]["height"])
        # negative control guarding against a catch-all figure endpoint
        assert fb["control_probe"]["verdict"].startswith("endpoint_is_not_a_catchall")
        assert fb["control_probe"]["http_status"] != 200
        assert fb["control_probe"]["is_png"] is False


def test_no_claim_is_marked_verified(manifest, envelope):
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert manifest["claims_empty_reason"].strip()
    blob = MANIFEST.read_text()
    assert '"verified"' not in blob and "verified_at_claim" not in blob


def test_verification_all_ok_and_acceptance_matches_contract(manifest):
    ver = json.loads(VERIFICATION.read_text())
    assert ver["all_ok"] is True
    expected = {
        "valid_json",
        "schema_pass",
        "source_locator_resolvable",
        "source_hash_matches",
        "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status",
    }
    assert set(ver["acceptance"]) == expected
    assert all(v["ok"] for v in ver["acceptance"].values())
    assert re_prod(ver["repro_cmd"])


def re_prod(cmd: str) -> bool:
    return "scripts/kf_wp10542_01_register.py" in cmd