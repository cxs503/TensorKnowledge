"""pytest wrapper for wp-12690-01 (report 12690 asset registration).

Two kinds of tests:
  1. acceptance: the shipped artefacts pass every contract acceptance item (scripts/kf_verify_12690.py).
  2. negative controls: the verifier actually *detects* tampering -- a mutated quote, a mutated hash
     and a duplicated asset_id must each fail. Without these, "schema_pass" would only prove the
     code executed, not that it checks anything.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = "wp-12690-01"
ART = ROOT / "artifacts" / PKG
RUN = ROOT / "runs" / PKG


def _load_verifier():
    spec = importlib.util.spec_from_file_location("kf_verify_12690", ROOT / "scripts" / "kf_verify_12690.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def verifier(tmp_path, monkeypatch):
    """Verifier pointed at an isolated copy of the artefacts (so tampering never touches the tree)."""
    mod = _load_verifier()
    art, run, doc = tmp_path / "artifacts", tmp_path / "runs", tmp_path / "docs"
    for d in (art, run, doc):
        d.mkdir()
    for f in ART.glob("*"):
        shutil.copy(f, art / f.name)
    for f in RUN.glob("*"):
        shutil.copy(f, run / f.name)
    monkeypatch.setattr(mod, "ART_DIR", art)
    monkeypatch.setattr(mod, "RUN_DIR", run)
    monkeypatch.setattr(mod, "DOC_DIR", doc)
    return mod


def _mutate(mod, fn):
    p = mod.ART_DIR / "asset_manifest.json"
    m = json.loads(p.read_text())
    fn(m)
    p.write_text(json.dumps(m, ensure_ascii=False, indent=2))


def test_acceptance_all_pass(verifier):
    res = verifier.verify()
    failed = {k: v for k, v in res["checks"].items() if not v["pass_"]}
    assert not failed, failed
    assert res["all_pass"] is True


def test_manifest_identity(verifier):
    m = json.loads((verifier.ART_DIR / "asset_manifest.json").read_text())
    assert m["schema"] == "asset_manifest.v1"
    assert m["package_id"] == PKG
    assert m["report_id"] == "12690"
    assert m["counts"]["assets"] == len(m["assets"]) == 26
    assert m["counts"]["by_resolution"] == {
        "resolved_in_source": 20, "referenced_unresolved": 1, "declared_absent": 5}
    assert m["claims"] == []  # registration-only package


def test_source_hash_pinned(verifier):
    m = json.loads((verifier.ART_DIR / "asset_manifest.json").read_text())
    env = json.loads((verifier.RUN_DIR / f"kf_result.{PKG}.json").read_text())
    assert m["source"]["hash"] == verifier.CONTRACT_HASH
    assert env["provenance"]["source_hash"] == "sha256:" + verifier.CONTRACT_HASH
    assert env["provenance"]["source_field"] == "markdown"


def test_negative_control_tampered_quote(verifier):
    def tamper(m):
        m["assets"][3]["locator"]["quote"] = m["assets"][3]["locator"]["quote"] + " (edited)"
    _mutate(verifier, tamper)
    res = verifier.verify()
    assert res["checks"]["source_locator_resolvable"]["pass_"] is False


def test_negative_control_tampered_span(verifier):
    def tamper(m):
        m["assets"][5]["locator"]["start_char"] += 1
    _mutate(verifier, tamper)
    res = verifier.verify()
    assert res["checks"]["source_locator_resolvable"]["pass_"] is False


def test_negative_control_tampered_hash(verifier):
    def tamper(m):
        m["source"]["hash"] = "0" * 64
    _mutate(verifier, tamper)
    res = verifier.verify()
    assert res["checks"]["source_hash_matches"]["pass_"] is False


def test_negative_control_duplicate_id(verifier):
    def tamper(m):
        m["assets"][1]["asset_id"] = m["assets"][0]["asset_id"]
    _mutate(verifier, tamper)
    res = verifier.verify()
    assert res["checks"]["no_duplicate_ids"]["pass_"] is False


def test_negative_control_fake_verified(verifier):
    def tamper(m):
        m["assets"][0]["resolution"] = "verified"
    _mutate(verifier, tamper)
    res = verifier.verify()
    assert res["checks"]["schema_pass"]["pass_"] is False  # enum rejects it
    assert res["checks"]["no_asset_marked_verified"]["pass_"] is False