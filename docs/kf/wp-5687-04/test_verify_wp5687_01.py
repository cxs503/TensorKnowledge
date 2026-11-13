#!/usr/bin/env python3
"""Acceptance test for the wp-5687-04 review package.

Asserts the review's own invariants rather than merely executing the checker:
  * offline re-run (snapshot bytes only, no network) reproduces the same verdict
  * the reviewed envelope still validates against schemas/kf_result.v1.schema.json
  * every gate check is green and every finding is explicitly non-blocking
  * the review never claims a verified mark and pins the exact upstream bytes
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

PKG = Path(__file__).resolve().parent
REPO = PKG.parents[2]


def load(name):
    return json.loads((PKG / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def offline_run(tmp_path_factory):
    """Re-run the checker offline into a scratch dir so the committed artefacts are not clobbered."""
    out = tmp_path_factory.mktemp("wp5687-04-offline")
    subprocess.run([sys.executable, str(PKG / "verify_wp5687_01.py"),
                    "--offline", "--write-dir", str(out)],
                   check=True, capture_output=True, cwd=REPO)
    return json.loads((out / "review_report.json").read_text(encoding="utf-8"))


def test_offline_rerun_verdict_is_pass(offline_run):
    assert offline_run["decision"]["verdict"] == "pass"
    assert offline_run["decision"]["blocking_findings"] == 0


def test_all_gate_checks_pass(offline_run):
    gate = {"C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13"}
    results = {c["id"]: c["result"] for c in offline_run["checks"]}
    assert {i: results[i] for i in gate} == dict.fromkeys(gate, "pass")


def test_envelope_conforms_to_repo_schema():
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.validate(load("kf_result.json"), schema)


def test_source_hash_pinned_to_report_bytes():
    md = (PKG / "upstream_snapshot" / "source_markdown_5687.md").read_text(encoding="utf-8")
    h = hashlib.sha256(md.encode()).hexdigest()
    env = load("kf_result.json")
    assert env["provenance"]["source_hash"] == "sha256:" + h
    assert env["provenance"]["source_field"] == "markdown"
    assert env["report_id"] == "5687"


def test_reviewed_artifacts_hashes_match_snapshot():
    rev = load("review_report.json")
    for name, declared in rev["provenance"]["reviewed_artifacts"].items():
        if name == "upstream_worktree_package_dir":
            continue
        actual = hashlib.sha256((PKG / "upstream_snapshot" / name).read_bytes()).hexdigest()
        assert declared == "sha256:" + actual, name


def _walk(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path + "." + k, k, v
            yield from _walk(v, path + "." + k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def test_no_verified_mark_asserted(offline_run):
    """The word may appear in negations/definitions only: no key may *assert* verified."""
    assert offline_run["decision"]["verdict_is_advisory"] is True
    assert offline_run["decision"]["not_a_verified_mark"] is True
    banned_keys = {"verified", "is_verified", "verification_status"}
    offenders = [(p, k, v) for p, k, v in _walk(load("kf_result.json"))
                 if k in banned_keys and v not in (None, False, "false")]
    assert offenders == [], offenders


def test_findings_are_classified_with_evidence(offline_run):
    for f in offline_run["findings"]:
        assert f["severity"] in {"low", "medium"}
        assert f["blocking"] is False
        assert f["evidence"] and f["reproduction"], f["id"]


def test_locator_quotes_are_verbatim_in_report():
    md = (PKG / "upstream_snapshot" / "source_markdown_5687.md").read_text(encoding="utf-8")
    lines = md.split("\n")
    for loc in load("checks.json")["locators"]:
        assert loc["quote"] in md
        assert loc["quote"] in lines[loc["line"] - 1], loc["asset_id"]