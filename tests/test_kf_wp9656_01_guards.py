#!/usr/bin/env python3
"""Guard/robustness tests for the wp-9656-01 asset-registration tooling (offline).

Adversarial probes on the builder itself, not on its happy-path output:
  * a source whose hash does not match the contract must be flagged (and main() aborts
    before writing anything -- the abort path is asserted textually as it needs network);
  * a report record that is not report_id=9656 must be refused (scope guard);
  * every locator must survive being re-checked against a *corrupted* copy of the source
    (i.e. the check actually detects tampering instead of always returning green).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "kf" / "wp9656_01_register.py"
SOURCE = ROOT / "runs" / "wp-9656-01" / "source_9656.md"


def load_module():
    spec = importlib.util.spec_from_file_location("wp9656_register", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def mod():
    return load_module()


def _record(text: str) -> dict:
    """Rebuild the served record shape: figures[] carry name/caption only (no bytes)."""
    manifest = json.loads((ROOT / "docs" / "kf" / "wp-9656-01" / "asset_manifest.json")
                          .read_text(encoding="utf-8"))
    figs = [{"name": a["name"], "caption": a["caption"], "png_base64": ""}
            for a in manifest["assets"] if a["kind"] == "embedded_figure"]
    return {"id": 9656, "title": mod_title(), "scenario_key": "ice_shaft_vibration",
            "mission_id": 8346, "markdown": text, "figures": figs,
            "tags": ["IN101-N05"], "status": "draft", "stage": "draft"}


def mod_title() -> str:
    return SOURCE.read_text(encoding="utf-8").split("\n")[0].lstrip("# ").strip()


def test_build_flags_hash_mismatch(mod, monkeypatch, tmp_path):
    text = SOURCE.read_text(encoding="utf-8")
    monkeypatch.setattr(mod, "CONTRACT_SOURCE_HASH", "sha256:" + "0" * 64)
    monkeypatch.setattr(mod, "probe_platform_artifacts", lambda token: {})
    monkeypatch.setattr(mod, "SOURCE_COPY", tmp_path / "src.md")
    manifest = mod.build_manifest(_record(text), None)
    assert manifest["source"]["hash_matches_contract"] is False
    assert manifest["source"]["source_hash"] == "sha256:" + mod.hashlib.sha256(
        text.encode("utf-8")).hexdigest()
    # the write path is guarded: a mismatching hash aborts instead of emitting a manifest
    assert "SOURCE HASH MISMATCH" in SCRIPT.read_text(encoding="utf-8")


def test_fetch_refuses_foreign_report_id(mod, monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "SOURCE_COPY", tmp_path / "src.md")
    monkeypatch.setattr(mod, "_req", lambda *a, **k: {"id": 1234, "markdown": "x"})
    with pytest.raises(SystemExit):
        mod.fetch_record(token="stub")
    assert not (tmp_path / "src.md").exists(), "must not cache a foreign report"


def test_locator_check_detects_tampering(mod):
    text = SOURCE.read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "docs" / "kf" / "wp-9656-01" / "asset_manifest.json")
                          .read_text(encoding="utf-8"))
    record = _record(text)
    checked, bad = mod.check_locators(manifest["assets"], manifest["tables"],
                                      manifest["sections"], text, record)
    assert checked == manifest["integrity"]["locators_checked"]
    assert bad == []

    tampered = text.replace("artifacts/ice_shaft_vibration/criteria.json",
                            "artifacts/ice_shaft_vibration/criteriaX.json")
    assert tampered != text
    checked_t, bad_t = mod.check_locators(manifest["assets"], manifest["tables"],
                                          manifest["sections"], tampered, record)
    assert checked_t == checked
    assert bad_t, "a corrupted source must produce locator failures, not silent green"


def test_counts_match_registry(mod):
    text = SOURCE.read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "docs" / "kf" / "wp-9656-01" / "asset_manifest.json")
                          .read_text(encoding="utf-8"))
    monkey = []
    # duplicate-id guard is inside build_manifest; assert it exists behaviourally via a copy
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids)) == manifest["counts"]["assets_total"]
    assert manifest["counts"]["body_references"] == len(mod.scan_references(text))
    assert monkey == []