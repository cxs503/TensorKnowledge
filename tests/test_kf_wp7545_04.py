"""Invariants of the wp-7545-04 independent-review package (report 7545).

These tests re-derive the reviewer's own claims from the sources instead of trusting the
products: envelope schema, review-event schema + state machine, verbatim-quote closure
against the report markdown, and the "exactly one ```json block" delivery rule.

Run: python -m pytest tests/test_kf_wp7545_04.py -q
The upstream product path defaults to the producer worktree; override with $UPSTREAM_PKG.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from ke_state_machine import fold, submit  # noqa: E402

PKG_DIR = os.path.join(ROOT, "docs", "kf", "wp-7545-04")
SRC = os.path.join(ROOT, "work", "kf_wp7545", "report_7545.md")
SNAPSHOT = os.path.join(ROOT, "work", "kf_wp7545", "upstream")
UP = os.environ.get("UPSTREAM_PKG") or (SNAPSHOT if os.path.isdir(SNAPSHOT)
                                        else "/root/tp-agent/work/m15597/docs/kf/wp-7545-01")
CONTRACT_HASH = "sha256:84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60"


def _load(name):
    with open(os.path.join(PKG_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _src():
    if not os.path.isfile(SRC):
        pytest.skip("source snapshot missing; run scripts/kf_fetch_7545.py")
    return open(SRC, encoding="utf-8").read()


def test_envelope_matches_schema():
    env = _load("kf_result.json")
    schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"), encoding="utf-8"))
    jsonschema.validate(env, schema)
    assert env["package_id"] == "wp-7545-04"
    assert env["task_type"] == "04-independent-review"
    assert env["report_id"] == "7545"
    assert env["provenance"]["source_field"] == "markdown"
    assert "review_report.json" in env["outputs"] and "review_events.json" in env["outputs"]


def test_source_hash_is_byte_exact():
    env = _load("kf_result.json")
    src = _src()
    assert "sha256:" + hashlib.sha256(src.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert env["provenance"]["source_hash"] == CONTRACT_HASH


def test_review_event_schema_and_state_machine():
    ledger = _load("review_events.json")
    schema = json.load(open(os.path.join(ROOT, "schemas", "review-event.schema.json"), encoding="utf-8"))
    for ev in ledger:
        jsonschema.validate(ev, schema)
    state = submit({"producer_ids": ["agent/m15597"]})
    final, codes = fold(ledger, {"producer_ids": ["agent/m15597"]}, initial_state=state)
    assert final == "draft"
    assert codes == ["OK_CHANGES_REQUESTED"]
    assert ledger[0]["reviewer"]["id"] != "agent/m15597"


def test_review_events_do_not_self_approve():
    ledger = _load("review_events.json")
    assert all(e["decision"] != "approve" for e in ledger)


def test_every_product_quote_is_verbatim_in_source():
    src = _src()
    rr = _load("review_report.json")
    for row in rr["asset_review"]:
        assert row["quote_verbatim"] in src, row["asset_id"]
        s, e = row["span"]
        if row["quote_at_declared_span"]:
            assert src[s:e] == row["quote_verbatim"], row["asset_id"]
    for f in rr["findings"]:
        for ev in f["evidence"]:
            if ev.get("artifact") == "tensor://reports/7545":
                assert ev["quote"] in src, (f["finding_id"], ev["quote"])


def test_finding_counts_match_product():
    rr = _load("review_report.json")
    sev = [f["severity"] for f in rr["findings"]]
    assert rr["counts"]["findings"] == {
        "minor": sev.count("minor"), "informational": sev.count("informational"),
        "major": sev.count("major"), "blocking": sev.count("blocking"),
    }
    assert all(f["blocking"] is False for f in rr["findings"])
    assert rr["verdict"] == "needs-fix"


def test_markdown_has_exactly_one_json_block_equal_to_envelope():
    md = open(os.path.join(PKG_DIR, "review_report.md"), encoding="utf-8").read()
    assert md.count("```json") == 1
    block = re.search(r"```json\n(.*?)\n```", md, re.S).group(1)
    assert json.loads(block) == _load("kf_result.json")


def test_markdown_carries_all_six_sections():
    md = open(os.path.join(PKG_DIR, "review_report.md"), encoding="utf-8").read()
    for head in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert head in md, head
    assert md.lstrip().startswith("# KF-RESULT wp-7545-04")


def test_upstream_product_is_the_one_reviewed():
    if not os.path.isdir(UP):
        pytest.skip("upstream package not present in this worktree")
    man = json.load(open(os.path.join(UP, "asset_manifest.json"), "rb"))
    rr = _load("review_report.json")
    digest = "sha256:" + hashlib.sha256(
        open(os.path.join(UP, "asset_manifest.json"), "rb").read()).hexdigest()
    assert rr["package_reviewed"] == man["package_id"] == "wp-7545-01"
    assert rr["source"]["product_sha256"] == digest


def test_reviewer_is_independent_and_prompt_is_not_copied():
    rr = _load("review_report.json")
    ind = rr["independence"]
    assert ind["is_independent"] is True
    assert ind["reviewer_id"] not in ind["producer_ids"]
    j = ind["prompt_jaccard_5gram_vs_producer_report"]
    assert j is None or j < 0.5
    assert ind["producer_explanation_used_in_judgement"] is False


def test_no_claim_is_marked_verified_by_the_reviewer():
    env = _load("kf_result.json")
    markers = ("verified", "verification_status", "verification_level", "is_verified", "gate_confirmed")
    blob = json.dumps(env["outputs"], ensure_ascii=False)
    for m in markers:
        assert f'"{m}"' not in blob, m
    assert env["claims"] == []