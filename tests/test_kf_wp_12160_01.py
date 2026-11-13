#!/usr/bin/env python3
"""Tests for work package wp-12160-01 (01-asset-registration of report 12160).

Runs completely offline (the byte copy of the report markdown kept next to the
package is the source of record; its sha256 is compared to the contract).

    pytest -q tests/test_kf_wp_12160_01.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(ROOT, "docs", "kf", "wp-12160-01")
SOURCE = os.path.join(PKG_DIR, "source_markdown.md")
RECORD = os.path.join(PKG_DIR, "source_record.json")
CONTRACT = os.path.join(ROOT, "contracts", "wp-12160-01.yaml")
REGISTER = os.path.join(ROOT, "scripts", "kf_register_12160.py")
SELFCHECK = os.path.join(ROOT, "scripts", "kf_selfcheck_12160.py")


def contract_hash() -> str:
    for line in open(CONTRACT, encoding="utf-8"):
        if line.strip().startswith("source_hash:"):
            return line.split("source_hash:", 1)[1].strip()
    raise AssertionError("source_hash missing from contract")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)


def register_and_check(out_dir: str, source: str, tamper=None) -> dict:
    r = run([sys.executable, REGISTER, "--out", out_dir, "--source-file", source])
    assert r.returncode == 0, r.stdout + r.stderr
    if tamper is not None:
        keep = os.path.join(out_dir, "source_markdown.md")
        md = open(keep, encoding="utf-8").read()
        with open(keep, "w", encoding="utf-8") as fh:
            fh.write(tamper(md))
    r = run([sys.executable, SELFCHECK, "--out", out_dir])
    payload = json.load(open(os.path.join(out_dir, "selfcheck.json"), encoding="utf-8"))
    payload["_returncode"] = r.returncode
    payload["_stdout"] = r.stdout
    return payload


@pytest.fixture()
def workdir(tmp_path):
    shutil.copy(SOURCE, tmp_path / "source_markdown.md")
    shutil.copy(RECORD, tmp_path / "source_record.json")
    return tmp_path


def test_source_bytes_match_contract():
    digest = "sha256:" + hashlib.sha256(open(SOURCE, "rb").read()).hexdigest()
    assert digest == contract_hash()
    assert len(open(SOURCE, encoding="utf-8").read()) == 9351


def test_registration_passes_all_acceptance(workdir):
    payload = register_and_check(str(workdir), str(workdir / "source_markdown.md"))
    assert payload["_returncode"] == 0, payload["_stdout"]
    assert payload["all_pass"] is True
    for item, result in payload["acceptance"].items():
        assert result["result"] == "PASS", (item, result)


def test_manifest_quotes_resolve_and_are_unique(workdir):
    register_and_check(str(workdir), str(workdir / "source_markdown.md"))
    md = open(workdir / "source_markdown.md", encoding="utf-8").read()
    manifest = json.load(open(workdir / "asset_manifest.json", encoding="utf-8"))
    assert manifest["claims"] == []  # contract: no forced claim generation
    assert manifest["counts"]["assets"] == len(manifest["assets"])
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    for asset in manifest["assets"]:
        loc = asset["locator"]
        if loc["method"] == "document":
            assert md.startswith(loc["quote"])
            assert (loc["start_char"], loc["end_char"]) == (0, len(md))
            continue
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"]
        if loc["unique"]:
            assert md.count(loc["quote"]) == 1, asset["asset_id"]


def test_hash_tamper_is_detected(workdir):
    """Negative control: one appended newline in the stored byte copy must fail
    source_hash_matches (the manifest hash no longer equals the contract hash)."""
    payload = register_and_check(str(workdir / "out"), str(workdir / "source_markdown.md"),
                                 tamper=lambda md: md + "\n")
    assert payload["_returncode"] != 0
    assert payload["acceptance"]["source_hash_matches"]["result"] == "FAIL"
    assert payload["all_pass"] is False


def test_locator_tamper_is_detected(workdir):
    """Negative control: shifting the stored text must break char-span locators."""
    payload = register_and_check(str(workdir / "out2"), str(workdir / "source_markdown.md"),
                                 tamper=lambda md: "X" * 7 + md)
    assert payload["_returncode"] != 0
    assert payload["acceptance"]["source_hash_matches"]["result"] == "FAIL"
    loc = payload["acceptance"]["source_locator_resolvable"]
    assert loc["result"] == "FAIL" and loc["evidence"]["failures"]


def test_no_verification_language_in_manifest():
    manifest = json.load(open(os.path.join(PKG_DIR, "asset_manifest.json"), encoding="utf-8"))
    blob = json.dumps(manifest["assets"], ensure_ascii=False)
    assert "verified" not in blob
    assert manifest["integrity"]["hash_matches_contract"] is True
    assert manifest["integrity"]["contract_cross_checks"]["chars_match"] is True