#!/usr/bin/env python3
"""Acceptance tests for work package wp-13612-01 (task_type 01-asset-registration).

Read-only: everything is asserted against the committed artifacts, so the test never
mutates the worktree and runs offline (no API calls).

Covers the contract's acceptance list one item at a time:
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
plus the two invariants this package adds for 工序-01 hygiene: quotes must be
verbatim AND unique in the report markdown, and nothing may be stamped ``verified``.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(HERE, "docs", "kf", "wp-13612-01")
SNAPSHOT = os.path.join(OUTDIR, "source", "report_13612.md")
MANIFEST = os.path.join(OUTDIR, "asset_manifest.json")
RESULT = os.path.join(OUTDIR, "kf_result.json")
ENVELOPE_SCHEMA = os.path.join(HERE, "schemas", "kf_result.v1.schema.json")

CONTRACT_HASH = "85bbae874e9babb342a5d216c19e00265dcc108115d6dcb53f1991af48846888"
CONTRACT_CHARS = 5526


@pytest.fixture(scope="module")
def md() -> str:
    with open(SNAPSHOT, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def envelope() -> dict:
    with open(RESULT, encoding="utf-8") as fh:
        return json.load(fh)


# --- acceptance: valid_json / source_hash_matches / report_id --------------------
def test_artifacts_are_valid_json(manifest, envelope):
    assert manifest["schema"] == "asset_manifest.v1"
    assert envelope["outputs"]["asset_manifest.json"] == manifest


def test_source_hash_matches_contract(md):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_envelope_identity(manifest, envelope):
    assert envelope["package_id"] == "wp-13612-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "13612"
    assert manifest["report_id"] == "13612"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"


# --- acceptance: schema_pass -----------------------------------------------------
def test_envelope_passes_canonical_schema(envelope):
    schema = json.load(open(ENVELOPE_SCHEMA, encoding="utf-8"))
    errs = list(Draft202012Validator(schema).iter_errors(envelope))
    assert not errs, [f"{list(e.path)}: {e.message}" for e in errs]


def test_manifest_required_keys(manifest):
    for key in ("schema", "package_id", "task_type", "report_id", "source", "assets",
                "counts", "claims", "integrity"):
        assert key in manifest


# --- acceptance: source_locator_resolvable --------------------------------------
def test_every_asset_locator_resolves_to_its_quote(md, manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert loc["start_char"] < loc["end_char"]
        assert 1 <= loc["start_line"] <= loc["end_line"]


def test_every_quote_is_verbatim_and_unique(md, manifest):
    for a in manifest["assets"]:
        q = a["locator"]["quote"]
        assert q in md, a["asset_id"]
        assert md.count(q) == 1, a["asset_id"]
    for o in manifest["observations"]:
        for q in o.get("quotes", []):
            assert q in md, o["observation_id"]
            assert md.count(q) == 1, o["observation_id"]


def test_locator_line_numbers_are_consistent(md, manifest):
    lines = md.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["quote"] in lines[loc["start_line"] - 1], a["asset_id"]


# --- acceptance: no_duplicate_ids ----------------------------------------------
def test_asset_ids_unique_and_patterned(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(len(i) == 3 and i[0] == "A" and i[1:].isdigit() for i in ids)


# --- acceptance: claims evidence-or-unresolved ---------------------------------
def test_claims_empty_is_the_contract_permitted_result(manifest, envelope):
    # objective.classify_report_type=false and "不做抽取" => zero claims, not a gap
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert manifest["counts"]["claims_registered"] == 0


def test_unresolved_assets_carry_a_note(manifest):
    for a in manifest["assets"]:
        if a["resolution"] == "referenced_unresolved":
            assert a["note"].strip(), a["asset_id"]
            assert a["resolution_check"]["result"] in ("unresolved", "absent")


# --- package-specific harm guards ----------------------------------------------
def test_nothing_marked_verified(envelope):
    blob = json.dumps(envelope, ensure_ascii=False)
    assert '"verified"' not in blob
    assert '"status": "verified"' not in blob
    assert envelope["outputs"]["asset_manifest.json"]["integrity"]["nothing_marked_verified"] is True


def test_source_declared_fails_are_preserved(md, manifest):
    # the source's own FAIL rows must survive registration unchanged
    quotes = {a["asset_id"]: a["locator"]["quote"] for a in manifest["assets"]}
    assert "FAIL" in quotes["A20"] and "FAIL" in quotes["A21"]
    assert "**否**" in quotes["A28"]
    assert "honest FAIL" in quotes["A29"]
    assert "弱通过" in quotes["A30"]


def test_figure_payloads_rehash_and_are_resolvable(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    assert len(figs) == 5
    for a in figs:
        rc = a["resolution_check"]
        assert rc["result"] == "resolved"
        assert rc["http_status"] == 200
        assert rc["png_magic_ok"] is True
        path = os.path.join(HERE, rc["local_copy"])
        payload = open(path, "rb").read()
        assert payload[:8] == b"\x89PNG\r\n\x1a\n"
        assert "sha256:" + hashlib.sha256(payload).hexdigest() == rc["payload_sha256"]


def test_counts_are_consistent(manifest):
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    assert c["assets"] == sum(c["by_resolution"].values())
    assert c["assets"] == sum(c["by_class"].values())
    assert c["resolved_in_source"] + c["referenced_unresolved"] + c["declared_absent"] == c["assets"]


def test_verify_mode_passes():
    """The shipped verifier must agree with these tests (single source of truth)."""
    proc = subprocess.run([sys.executable,
                           os.path.join(HERE, "scripts", "kf_wp13612_01_asset_manifest.py"),
                           "--verify"],
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    checks = json.load(open(os.path.join(OUTDIR, "selfcheck.json"), encoding="utf-8"))
    assert checks["ok"] is True
    for key in ("source_hash_matches_contract", "schema_pass", "source_locator_resolvable",
                "no_duplicate_ids", "all_quotes_verbatim", "all_quotes_unique",
                "figures_all_resolvable", "counts_consistent"):
        assert checks[key] is True, key