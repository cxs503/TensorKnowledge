#!/usr/bin/env python3
"""Invariant tests for the wp-11180-04 independent review.

These assert facts, not mere execution: byte-level source pinning, zero-hand-copy
quote binding, exact char_span re-slicing of the upstream package, envelope
schema conformance, and decision/blocking-finding consistency.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "docs/kf/wp-11180-04")
SNAP = os.path.join(D, "source/report_11180.md")
CHECKS = os.path.join(D, "review_checks.json")
REVIEW = os.path.join(D, "review_report.json")
MD = os.path.join(D, "review_report.md")
UPSTREAM = os.path.join(ROOT, "docs/report_wp11180_01.md")
SCHEMA = os.path.join(ROOT, "schemas/kf_result.v1.schema.json")

CONTRACT_HASH = "9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292"


def load(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def test_source_snapshot_is_byte_pinned():
    raw = open(SNAP, "rb").read()
    assert hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert len(raw.decode("utf-8")) == 490
    assert len(raw) == 670


def test_all_quotes_are_verbatim_substrings():
    md = load(SNAP)
    res = json.loads(load(CHECKS))
    assert res["quote_binding"], "no quotes bound"
    for key, v in res["quote_binding"].items():
        assert v["found"], key
        assert v["quote"] in md, key
        assert md.count(v["quote"]) == 1, f"{key} not unique"
        assert md[v["start_char"]:v["end_char"]] == v["quote"], key


def test_finding_evidence_quotes_are_verbatim():
    md = load(SNAP)
    env = json.loads(load(REVIEW))
    review = env["outputs"]["review_report.json"]
    n_checked = 0
    for f in review["findings"]:
        for ev in f["evidence"]:
            q = ev["quote"]
            if q.startswith("schemas/"):
                assert os.path.exists(SCHEMA)
                continue
            assert q in md, f"{f['id']} quote not in source: {q!r}"
            n_checked += 1
    assert n_checked >= 10, n_checked


def test_upstream_char_spans_reslice_exactly():
    md = load(SNAP)
    res = json.loads(load(CHECKS))
    spans = res["upstream"]["asset_spans"]
    assert len(spans) == 4
    for s in spans:
        start, end = s["declared_span"]
        assert md[start:end] == s["recomputed"]
        assert s["byte_exact"], s["asset_id"]
        assert s["unique"], s["asset_id"]


def test_markdown_has_exactly_one_json_block_and_it_round_trips():
    doc = load(MD)
    blocks = re.findall(r"```json\n(.*?)```", doc, re.S)
    assert len(blocks) == 1, len(blocks)
    block = json.loads(blocks[0])
    env = json.loads(load(REVIEW))
    assert block == env
    assert "KF-RESULT wp-11180-04" in doc.splitlines()[0]


def test_envelope_conforms_to_kf_result_schema():
    schema = json.loads(load(SCHEMA))
    env = json.loads(load(REVIEW))
    assert set(schema["required"]) <= set(env)
    if schema.get("additionalProperties") is False:
        assert set(env) <= set(schema["properties"])
    assert env["package_id"] == "wp-11180-04"
    assert env["task_type"] == "04-independent-review"
    assert env["contract_version"] == "1.0"
    assert re.match(schema["properties"]["package_id"]["pattern"], env["package_id"])
    assert re.match(schema["properties"]["report_id"]["pattern"], env["report_id"])
    prov_schema = schema["properties"]["provenance"]
    assert set(prov_schema["required"]) <= set(env["provenance"])
    assert set(env["provenance"]) <= set(prov_schema["properties"])
    assert env["provenance"]["source_field"] == "markdown"
    assert re.match(prov_schema["properties"]["source_uri"]["pattern"], env["provenance"]["source_uri"])
    assert re.match(prov_schema["properties"]["source_hash"]["pattern"], env["provenance"]["source_hash"])
    assert env["provenance"]["source_hash"] == f"sha256:{CONTRACT_HASH}"
    outs = env["outputs"]
    assert outs and set(outs) <= set(schema["properties"]["outputs"]["properties"])
    assert isinstance(outs["review_report.json"], dict)
    assert isinstance(outs["review_events.json"], list)


def test_decision_consistent_with_blocking_findings():
    env = json.loads(load(REVIEW))
    review = env["outputs"]["review_report.json"]
    blocking = [f["id"] for f in review["findings"] if f["blocking"]]
    assert blocking, "a needs-fix decision must carry blocking findings"
    assert review["decision"]["disposition"] == "needs-fix"
    assert review["decision"]["claims_marked_verified"] == 0
    assert review["counts"]["blocking_findings"] == len(blocking)
    # severities are from the declared vocabulary and ranked
    order = ["high", "medium", "low", "info"]
    sev = [order.index(f["severity"]) for f in review["findings"]]
    assert sev == sorted(sev), "findings must be severity-ranked"


def test_nothing_marked_verified():
    raw = load(REVIEW)
    assert '"verified": true' not in raw
    assert "claims_marked_verified\": 0" in raw
    env = json.loads(raw)
    for ev in env["outputs"]["review_events.json"]:
        assert ev.get("claims_marked_verified", 0) == 0


def test_check_inventory_and_no_silent_pass():
    res = json.loads(load(CHECKS))
    ids = [c["id"] for c in res["checks"]]
    assert len(ids) == len(set(ids)) == 18
    statuses = {c["status"] for c in res["checks"]}
    assert statuses <= {"pass", "fail", "not_run"}
    for c in res["checks"]:
        if c["status"] != "pass":
            assert c["detail"], f"{c['id']} must justify a non-pass verdict"
    fails = [c["id"] for c in res["checks"] if c["status"] == "fail"]
    assert "C11" in fails and "C10" in fails and "C16" in fails
    assert res["source"]["sha256"] == f"sha256:{CONTRACT_HASH}"


def test_upstream_envelope_deviation_is_reported_not_hidden():
    env_up = json.loads(re.findall(r"```json\n(.*?)```", load(UPSTREAM), re.S)[0])
    assert "claims" in env_up  # the deviation really exists in the upstream envelope
    dev = json.loads(load(REVIEW))["outputs"]["review_report.json"]["reviewed_package"]["schema_deviations"]
    assert any(d.get("kind") == "additional_property" and "claims" in d.get("keys", []) for d in dev)