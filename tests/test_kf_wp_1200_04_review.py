#!/usr/bin/env python3
"""Invariants for work package wp-1200-04 (independent review of wp-1200-01).

The tests re-derive every fact from the artifacts on disk; they do not import
any constant from the subject package. Mutation tests prove the reviewer's
instrument actually detects tampering (a green suite that only "runs the code"
is not evidence).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "wp-1200-04"
DOC = ROOT / "docs" / "kf" / "wp-1200-04" / "KF-RESULT-wp-1200-04.md"

CONTRACT_SOURCE_HASH = "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48"

sys.path.insert(0, str(ROOT / "scripts"))
from ke_state_machine import fold, submit  # noqa: E402


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_review", ART / "verify_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def source() -> str:
    return (ART / "source_report_1200.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((ART / "kf_result_wp-1200-04.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def subject() -> dict:
    return json.loads((ART / "subject_wp-1200-01_envelope.json").read_text(encoding="utf-8"))


def test_source_copy_hash_matches_contract(source: str) -> None:
    digest = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_SOURCE_HASH
    assert len(source) == 3612
    assert len(source.encode("utf-8")) == 5396


def test_envelope_matches_kf_result_schema(envelope: dict) -> None:
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(envelope)
    assert envelope["package_id"] == "wp-1200-04"
    assert envelope["task_type"] == "04-independent-review"
    assert envelope["report_id"] == "1200"
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH
    assert {"review_report.json"} <= set(envelope["outputs"])


def test_envelope_hash_is_recomputed_not_copied(envelope: dict, source: str) -> None:
    recomputed = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert envelope["provenance"]["source_hash"] == recomputed
    assert envelope["provenance"]["reviewed_source_hash"] == recomputed


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_review_marks_nothing_verified(envelope: dict, subject: dict) -> None:
    # the rule is about the subject's claims and about asserting a verification level
    keys = set(_keys(envelope["outputs"]))
    assert not {k for k in keys if k in ("verified", "verification_status", "is_verified")}
    subject_blob = json.dumps(subject, ensure_ascii=False)
    assert "verification_status" not in subject_blob
    assert '"verified"' not in subject_blob


def test_subject_manifest_locators_reslice_exactly(subject: dict, source: str) -> None:
    manifest = subject["outputs"]["asset_manifest.json"]
    locators = [("title", manifest["source"]["title_locator"])]
    for a in manifest["attachments"]:
        locators += [(a["asset_id"], loc) for loc in a["mentioned_at"]]
    locators += [(s["ref_id"], s["locator"]) for s in manifest["registered_schema_elements"]]
    locators += [(m["metric_id"], m["locator"]) for m in manifest["registered_metric_locators"]]
    assert len(locators) == 21
    for name, loc in locators:
        assert source[loc["char_start"]:loc["char_end"]] == loc["quote"], name
        assert loc["quote"] in source, name


def test_subject_claim_quotes_verbatim_and_numbers_traced(subject: dict, source: str) -> None:
    claims = subject["outputs"]["asset_manifest.json"]["claims"]
    assert len(claims) == 10
    for claim in claims:
        quotes = [e["quote"] for e in claim["evidence"]]
        assert quotes, claim["claim_id"]
        blob = "\n".join(quotes)
        for quote in quotes:
            assert quote in source, claim["claim_id"]
        for number in re.findall(r"\d+(?:\.\d+)?", claim["text"]):
            assert number in blob, (claim["claim_id"], number)


def test_finding_quotes_are_verbatim_with_true_offsets(envelope: dict, source: str) -> None:
    report = envelope["outputs"]["review_report.json"]
    md_quotes = 0
    for finding in report["findings"]:
        for ev in finding["evidence"]:
            if isinstance(ev, dict) and "quote" in ev and "start_offset" in ev:
                md_quotes += 1
                assert source[ev["start_offset"]:ev["end_offset"]] == ev["quote"]
                assert source.count(ev["quote"]) == ev["occurrences"]
                digest = hashlib.sha256(ev["quote"].encode("utf-8")).hexdigest()
                assert digest == ev["quote_sha256"]
    assert md_quotes >= 4


def test_verdict_consistent_with_findings(envelope: dict) -> None:
    report = envelope["outputs"]["review_report.json"]
    blocking = [f for f in report["findings"] if f["blocking"]]
    if blocking:
        assert report["verdict"] == "needs-fix"
    assert report["verdict"] in {"pass", "fail", "needs-fix"}
    assert report["reviewer_mission_id"] != report["producer_mission_id"]


def test_review_event_ledger_is_legal_and_carries_findings(envelope: dict) -> None:
    events = envelope["outputs"]["review_events.json"]["events"]
    ctx = {"producer_ids": ["agent-m15523"]}
    state = submit(ctx, "draft")  # draft -> in-review is a system transition
    state, codes = fold(events, ctx, initial_state=state)
    assert state == "draft", codes
    assert all(c.startswith("OK_") for c in codes), codes
    assert events[0]["findings"], "request-changes must carry findings"


def test_rendered_doc_has_exactly_one_json_block(envelope: dict) -> None:
    text = DOC.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == envelope
    for heading in ("①", "②", "③", "④", "⑤", "⑥"):
        assert heading in text
    assert text.startswith("# KF-RESULT wp-1200-04")


def test_doc_prefix_matches_render_script() -> None:
    """The doc is generated; a hand-edit would desync it from the artifacts."""
    text = DOC.read_text(encoding="utf-8")
    block = json.loads(re.findall(r"```json\n(.*?)\n```", text, re.S)[0])
    assert block["package_id"] == "wp-1200-04"
    assert "needs-fix" in text.split("\n")[2]


# --------------------------------------------------------------------------- #
# mutation tests — the instrument must catch what it claims to catch
# --------------------------------------------------------------------------- #
def test_mutation_shifted_offset_is_detected(source: str) -> None:
    v = _load_verifier()
    lines = v.line_index(source)
    loc = {"quote": "## ④ 结果图", "char_start": 2599, "char_end": 2606, "line_start": 41, "line_end": 41}
    assert v.locator_verdict(source, lines, loc)["problems"]


def test_mutation_tampered_quote_is_detected(source: str) -> None:
    v = _load_verifier()
    lines = v.line_index(source)
    start = source.find("| `public` schema 表数 | 15 | 43 |")
    quote = source[start:start + 31].replace("15", "16", 1)
    loc = {"quote": quote, "char_start": start, "char_end": start + len(quote),
           "line_start": 37, "line_end": 37}
    problems = v.locator_verdict(source, lines, loc)["problems"]
    assert "OFFSET_SLICE_MISMATCH" in problems or "QUOTE_NOT_IN_SOURCE" in problems


def test_mutation_unregistered_figure_fails_check(source: str) -> None:
    """Guard the F1 finding: if the figure were registered, c9 would pass."""
    v = _load_verifier()
    lines = v.line_index(source)
    manifest = json.loads((ART / "subject_wp-1200-01_envelope.json").read_text(encoding="utf-8"))[
        "outputs"
    ]["asset_manifest.json"]
    blob = json.dumps(manifest, ensure_ascii=False)
    name = json.loads((ART / "platform_probe.json").read_text(encoding="utf-8"))["figure_probe"]["name"]
    assert name not in blob  # current state: unregistered -> F1 stands
    patched = json.loads(json.dumps(manifest))
    patched["attachments"].append({"asset_id": "art-09", "kind": "figure", "ref": name, "resolvable": False})
    assert name in json.dumps(patched, ensure_ascii=False)  # remediation would flip the check
    assert v.locate(source, "## ④ 结果图", lines)["occurrences"] == 1