#!/usr/bin/env python3
"""Offline acceptance tests for wp-5760-04 (independent review of wp-5760-01).

No network: everything runs on the committed snapshot + delivered JSON artefacts.
The locator recheck below is a third, standalone implementation (the verifier is the
second; the producer's own test was the first) so agreement is not self-referential.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import jsonschema
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PKG = os.path.join(ROOT, "docs/kf/wp-5760-04")
SUBJECT = os.path.join(ROOT, "docs/kf/wp-5760-01/asset_manifest.json")
SNAP = os.path.join(ROOT, "runs/wp-5760-04/source_report_5760.md")
CONTRACT_HASH = "sha256:95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe"


def _load(name: str) -> dict:
    return json.load(open(os.path.join(PKG, name), encoding="utf-8"))


@pytest.fixture(scope="module")
def md() -> str:
    return open(SNAP, encoding="utf-8").read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.load(open(SUBJECT, encoding="utf-8"))


def test_source_snapshot_matches_contract(md):
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == 6808


def test_envelope_validates_against_repo_schema():
    env = _load("kf_result.json")
    schema = json.load(open(os.path.join(ROOT, "schemas/kf_result.v1.schema.json"),
                            encoding="utf-8"))
    jsonschema.validate(env, schema)  # raises on failure
    assert env["package_id"] == "wp-5760-04"
    assert env["task_type"] == "04-independent-review"
    assert env["report_id"] == "5760"
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert env["provenance"]["source_field"] == "markdown"
    assert set(env["outputs"]) == {"review_report.json", "review_events.json"}


def test_review_event_is_schema_valid():
    events = json.load(open(os.path.join(PKG, "review_events.json"), encoding="utf-8"))
    schema = json.load(open(os.path.join(ROOT, "schemas/review-event.schema.json"),
                            encoding="utf-8"))
    assert isinstance(events, list) and len(events) == 1
    jsonschema.validate(events[0], schema)
    assert events[0]["object_ref"].endswith("wp-5760-01/asset_manifest.json")


def test_verdict_shape_and_no_self_verification():
    r = _load("review_report.json")
    assert r["verdict"] in {"pass", "needs-fix", "fail"}
    assert r["disposition"] in {"approve", "approve-with-notes", "request-changes", "escalate"}
    # a pass verdict may not hide a blocking defect
    blocking = [f for f in r["findings"] if f["blocking"]]
    if r["verdict"] == "pass":
        assert blocking == []
    assert r["verification_marking"]["upstream_claims_marked_verified"] == 0
    assert r["verification_marking"]["platform_verification_untouched"] is True
    # nothing in the subject may carry a locally asserted verification state
    subject = json.load(open(SUBJECT, encoding="utf-8"))
    assert all(a.get("resolution") != "verified" and a.get("verified") is not True
               for a in subject["assets"])
    assert subject.get("claims") == []


def test_subject_hash_is_the_delivered_bytes():
    r = _load("review_report.json")
    actual = "sha256:" + hashlib.sha256(open(SUBJECT, "rb").read()).hexdigest()
    assert r["subject"]["artifact_sha256"] == actual
    assert r["subject"]["package_id"] == "wp-5760-01"
    assert _load("kf_result.json")["outputs"]["review_report.json"][
        "subject_artifact_sha256"] == actual


def test_all_52_locators_resolve_verbatim(manifest, md):
    starts, off = [0], 0
    for ln in md.split("\n")[:-1]:
        off += len(ln) + 1
        starts.append(off)
    bad, prefix_only = [], []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        if md[s:e] != loc["quote"]:
            # documented exception: method=document pins the H1 title inside the whole-doc span
            if loc.get("method") == "document" and md[s:e].startswith(loc["quote"]):
                prefix_only.append(a["asset_id"])
            else:
                bad.append((a["asset_id"], "quote"))
            continue
        # line number of start_char, by direct counting (independent of bisect)
        line = md.count("\n", 0, s) + 1
        if line != loc["start_line"]:
            bad.append((a["asset_id"], f"line {loc['start_line']} != {line}"))
    assert bad == []
    assert prefix_only == ["A01"]  # exactly one documented exception, see finding F5


def test_class_census_reproduced(manifest, md):
    by_class = {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
    headings = len([ln for ln in md.split("\n") if re.match(r"^#{2,3} ", ln)])
    blocks, prev = 0, False
    for ln in md.split("\n"):
        cur = ln.lstrip().startswith("|")
        if cur and not prev:
            blocks += 1
        prev = cur
    assert by_class["section"] == headings == 11
    assert by_class["table"] == blocks == 7
    assert by_class["figure_reference"] == len(re.findall(r"!\[[^\]]*\]\([^)]+\)", md)) == 1
    assert sum(by_class.values()) == manifest["counts"]["assets"] == 52


def test_review_report_checks_are_all_bound_to_findings_or_pass():
    r = _load("review_report.json")
    ids = {c["id"] for c in r["checks"]}
    assert len(r["checks"]) == r["checks_summary"]["n_checks"] == 19
    failed = {c["id"] for c in r["checks"] if not c["ok"]}
    assert failed == set(r["checks_summary"]["failed"])
    for f in r["findings"]:
        assert f["evidence"]["check"] in ids
        assert f["severity"] in {"blocking", "major", "minor", "info"}
    # every failing check must be accounted for by a finding
    covered = {f["evidence"]["check"] for f in r["findings"]}
    assert failed <= covered


def test_figure_present():
    p = os.path.join(PKG, "figures/review_gate_matrix.png")
    assert os.path.isfile(p) and os.path.getsize(p) > 5000