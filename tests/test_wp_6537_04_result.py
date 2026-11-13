#!/usr/bin/env python3
"""Tests for the wp-6537-04 independent-review deliverable (report 6537 only).

Each test pins one property a machine gate or a downstream extractor depends on:
  * the result envelope is the single machine-readable block in the report,
  * its provenance hash equals the source bytes this worktree actually fetched,
  * every quoted fragment is a verbatim substring of the source (zero hand-copy),
  * the review ledger is schema-legal and folds in the KE state machine,
  * no axis is crossed (no producer-style verification field, no self-approval),
  * the pipeline touches report_id=6537 and nothing else.

Run: python3 -m pytest tests/test_wp_6537_04_result.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

import jsonschema
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PKG = os.path.join(ROOT, "docs", "kf", "wp-6537-04")
RUNS = os.path.join(ROOT, "runs", "wp-6537-04")
MD_PATH = os.path.join(PKG, "KF-RESULT-wp-6537-04.md")
REVIEW_PATH = os.path.join(PKG, "review_report.json")
EVENTS_PATH = os.path.join(PKG, "review_events.json")
SOURCE_PATH = os.path.join(RUNS, "report_6537.markdown")
CONTRACT_HASH = "sha256:aaf27418db0e671d671f7cafa2aecf6d68e235f593384832f3fb46cf152d1f71"
UPSTREAM = "/root/tp-agent/work/m15590/docs/kf/wp-6537-01"

sys.path.insert(0, os.path.join(ROOT, "scripts"))


def _md():
    return open(MD_PATH, encoding="utf-8").read()


def _source():
    return open(SOURCE_PATH, encoding="utf-8").read()


def _envelope():
    blocks = _md().split("```json")
    assert len(blocks) == 2, "the report must hold exactly one ```json result block"
    return json.loads(blocks[1].split("```")[0])


def _walk_quotes(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "quote" and isinstance(v, str):
                yield path + ".quote", v
            else:
                yield from _walk_quotes(v, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_quotes(v, "%s[%d]" % (path, i))


def _walk_keys(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + "." + str(k), k, v
            yield from _walk_keys(v, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_keys(v, "%s[%d]" % (path, i))


# ------------------------------------------------------------------ structure
def test_source_snapshot_matches_contract_hash():
    raw = open(SOURCE_PATH, "rb").read()
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert len(raw.decode("utf-8")) == 10530


def test_envelope_passes_kf_result_schema():
    env = _envelope()
    schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"),
                            encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(env)
    assert env["package_id"] == "wp-6537-04"
    assert env["task_type"] == "04-independent-review"
    assert env["report_id"] == "6537"


def test_envelope_provenance_hash_is_the_source_bytes():
    env = _envelope()
    assert env["provenance"]["source_field"] == "markdown"
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert env["provenance"]["source_uri"] == "tensor://reports/6537"


def test_report_title_and_tags_are_contract_shaped():
    md = _md()
    assert md.startswith("# KF-RESULT wp-6537-04\n")
    # the delivery contract asks for the tag on the platform record; the report
    # itself must at least carry the same identifier in its heading.
    assert "wp-6537-04" in md.splitlines()[0]


def test_review_report_output_is_complete():
    rr = _envelope()["outputs"]["review_report.json"]
    assert rr["verdict"] in {"pass", "fail", "needs-fix"}
    assert rr["disposition"] in {"approve", "approve-with-notes", "request-changes", "escalate"}
    assert len(rr["checks_performed"]) >= 20
    assert len(rr["numeric_recomputation"]) >= 10
    assert rr["findings"] and all({"finding_id", "severity", "title"} <= set(f)
                                   for f in rr["findings"])
    assert rr["required_fixes"] and rr["carry_forward_constraints"]
    assert rr["decisions_not_made"], "the report must say what it did NOT decide"
    assert rr["upstream_packages_completed"]["wp-6537-01"]["present"] is True
    # verdict and disposition must agree (needs-fix -> request-changes)
    assert (rr["verdict"] == "needs-fix") == (rr["disposition"] == "request-changes")


def test_review_report_json_on_disk_equals_the_embedded_block():
    rr = _envelope()["outputs"]["review_report.json"]
    assert json.load(open(REVIEW_PATH, encoding="utf-8")) == rr


# --------------------------------------------------------------- no hand-copy
def test_every_quote_is_verbatim_in_the_source():
    src = _source()
    rr = json.load(open(REVIEW_PATH, encoding="utf-8"))
    quotes = [q for p, q in _walk_quotes(rr)
              if not p.startswith("$.provenance")]  # provenance holds no source quote
    assert quotes, "expected evidence quotes in the review report"
    missing = [q for q in quotes if q not in src]
    assert not missing, "quotes not found verbatim in the source: %r" % missing[:3]


def test_evidence_table_quotes_are_verbatim_in_the_source():
    src = _source()
    section = _md().split("## ④")[1].split("## ⑤")[0]
    for line in section.splitlines():
        if not line.startswith("| ") or "原文引文" in line or line.startswith("|---"):
            continue
        m = re.findall(r"``(\|.*?)``|`(\|.*?)`", line)
        for pair in m:
            q = pair[0] or pair[1]
            assert q in src, "evidence-table quote not verbatim: %r" % q[:60]


# ------------------------------------------------------------ axis separation
def test_no_self_verification_field_anywhere():
    forbidden = {"verification_status", "verification_level", "is_verified", "gate_confirmed"}
    env = _envelope()
    hits = [(p, k) for p, k, _ in _walk_keys(env) if k in forbidden]
    assert not hits, hits
    for f in env["outputs"]["review_report.json"].get("findings", []):
        assert f.get("severity") != "verified"


def test_claims_are_never_marked_verified():
    for name in ("review_report.json",):
        doc = json.load(open(os.path.join(PKG, name), encoding="utf-8"))
        for _, _, v in _walk_keys(doc):
            if isinstance(v, str):
                assert v.strip().lower() not in {"verified", "platform-confirmed"}


# --------------------------------------------------------------- review ledger
def test_review_events_is_schema_legal():
    events = json.load(open(EVENTS_PATH, encoding="utf-8"))
    schema = json.load(open(os.path.join(ROOT, "schemas", "review-event.schema.json"),
                            encoding="utf-8"))
    for ev in events:
        jsonschema.Draft202012Validator(schema).validate(ev)


def test_review_ledger_folds_in_the_ke_state_machine():
    from ke_state_machine import fold  # scripts/ke_state_machine.py

    events = json.load(open(EVENTS_PATH, encoding="utf-8"))
    ctx = {"producer_ids": ["scripts/kf/build_asset_manifest_6537.py", "agent/m15590"]}
    state, codes = fold(events, ctx, initial_state="in-review")
    assert state == "draft"
    assert codes == ["OK_CHANGES_REQUESTED"]


def test_reviewer_is_not_the_producer():
    ev = json.load(open(EVENTS_PATH, encoding="utf-8"))[0]
    reviewer = ev["reviewer"]["id"]
    assert reviewer == "agent/m15847"
    # upstream package lives in a different agent worktree: different tenant id
    assert UPSTREAM.split("/work/")[1].split("/")[0] != reviewer.split("/")[1]


def test_review_events_decision_carries_findings():
    ev = json.load(open(EVENTS_PATH, encoding="utf-8"))[0]
    assert ev["decision"] == "request-changes"
    assert ev["findings"], "request-changes must explain itself"
    assert all(f["severity"] in {"blocking", "major", "minor", "informational"}
               for f in ev["findings"])


# ------------------------------------------------------------------ scope/hygiene
def test_only_report_6537_is_referenced():
    ids = set()
    for base, _, files in os.walk(PKG):
        for f in files:
            if f.endswith(".json") or f.endswith(".md"):
                txt = open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()
                ids |= set(re.findall(r"reports/(\d{2,7})", txt))
    assert ids <= {"6537"}, ids


def test_upstream_package_untouched_by_this_worktree():
    # the review only reads the upstream artifact; its manifest bytes must still be
    # the ones this review pinned.
    env = _envelope()
    pinned = env["outputs"]["review_report.json"]["provenance"]["reviewed_artifacts"]
    if not os.path.isdir(UPSTREAM):  # pragma: no cover - other worktree may be gone
        pytest.skip("upstream worktree not available")
    for name, want in pinned.items():
        got = "sha256:" + hashlib.sha256(open(os.path.join(UPSTREAM, name), "rb").read()).hexdigest()
        assert got == want, "%s changed since the review" % name


# ------------------------------------------------------------- numeric ledger
def test_numeric_findings_are_the_expected_ones():
    """Guard against silent drift: the penalty table must recompute, and the four
    cross-consistency mismatches must stay exactly the ones reported."""
    audit = json.load(open(os.path.join(RUNS, "audit.json"), encoding="utf-8"))
    results = {n["id"]: n["result"] for n in audit["numeric_recomputation"]}
    assert results["N02"] == "PASS"   # WtW = WtT + TtW
    assert results["N04"] == "PASS"   # slip-sensitivity table
    assert results["N05"] == "PASS"   # analytic slope / crossover
    assert results["N06"] == "PASS"   # penalty table back-substitution
    mismatched = {k for k, v in results.items() if v != "PASS"}
    assert mismatched == {"N01", "N08", "N09", "N10", "N11"}, mismatched


def test_structural_failures_are_only_the_offset_semantics():
    audit = json.load(open(os.path.join(RUNS, "audit.json"), encoding="utf-8"))
    bad = {c["id"] for c in audit["structural_evidence_checks"] if c["result"] != "PASS"}
    assert bad == {"C15", "C16"}, bad
    assert audit["counts"]["blocking"] == 0


def test_source_report_claims_used_in_findings_are_locatable():
    """Every number quoted in a finding's evidence must appear in the source table."""
    src = _source()
    audit = json.load(open(os.path.join(RUNS, "audit.json"), encoding="utf-8"))
    for f in audit["findings"]:
        q = (f.get("evidence") or {}).get("quote")
        if q:
            assert q in src, "%s quote not verbatim: %r" % (f["finding_id"], q[:60])


def test_figure_exists_and_is_embedded_by_the_pipeline():
    fig = os.path.join(PKG, "fig_review_6537_04.png")
    assert os.path.getsize(fig) > 20_000
    rr = json.load(open(REVIEW_PATH, encoding="utf-8"))
    want = rr["provenance"]["figure"]["sha256"]
    assert "sha256:" + hashlib.sha256(open(fig, "rb").read()).hexdigest() == "sha256:" + want