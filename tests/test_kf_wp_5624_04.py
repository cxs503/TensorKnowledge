#!/usr/bin/env python3
"""Invariant tests for wp-5624-04 (independent review of wp-5624-01).

These assert properties, not that code runs:
  * the contract is schema-clean for the 04 branch and its declared artefact exists;
  * the review's source identity equals the sha256 of the snapshot it ships, and
    equals the hash registered by the reviewed package;
  * every ledger check is classified (pass / fail-with-finding / declared not_run) —
    an unexplained failure or an undeclared not_run fails the test;
  * the verdict follows the declared rule (blocking or package-attributed major
    finding => request-changes), so the verdict cannot drift from the findings;
  * the products are exactly what the generator emits (no hand-edited numbers);
  * the review event validates against schemas/review-event.schema.json and agrees
    with the review report;
  * nothing is marked verified and only report 5624 is referenced.

Run: pytest -q tests/test_kf_wp_5624_04.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-5624-04"
UP = ROOT / "docs" / "kf" / "wp-5624-01"
SNAP = OUT / "source" / "report_5624.md"
FORBIDDEN = ("verified", "verification_status", "verification_level",
             "is_verified", "gate_confirmed")

CONTRACT = json.loads((OUT / "work-package.json").read_text(encoding="utf-8"))
RECHECK = json.loads((OUT / "upstream_recheck.json").read_text(encoding="utf-8"))
REVIEW = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
EVENTS = json.loads((OUT / "review_events.json").read_text(encoding="utf-8"))
MD = (OUT / "kf_result_wp-5624-04.md").read_text(encoding="utf-8")
MANIFEST = json.loads((UP / "asset_manifest.json").read_text(encoding="utf-8"))
KF_UP = json.loads((UP / "kf_result.json").read_text(encoding="utf-8"))


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_contract_is_schema_clean_and_declares_present_artefact():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "work-package-contract.schema.json")
                        .read_text(encoding="utf-8"))
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(CONTRACT)) == []
    assert CONTRACT["task_type"] == "04-independent-review"
    assert set(CONTRACT["output"]) == {"review_report.json"}
    assert CONTRACT["review"] == {"required": True, "independent_reviewer": True,
                                  "reviewer_role": "red-team-reviewer", "sample_rate": 1.0}
    for name in CONTRACT["output"]:
        assert (OUT / name).is_file(), name
    # upstream status is not asserted without a gate report (declared deviation)
    assert "upstream_packages" not in CONTRACT["input"]


def test_source_identity_reproduces_from_the_shipped_snapshot():
    md = SNAP.read_text(encoding="utf-8")
    assert "sha256:" + sha256_text(md) == CONTRACT["input"]["source_hash"]
    assert CONTRACT["input"]["source_hash"] == MANIFEST["source_asset"]["hash"]["value"]
    assert CONTRACT["input"]["source_hash"] == KF_UP["provenance"]["source_hash"]
    assert RECHECK["source"]["sha256"] == CONTRACT["input"]["source_hash"]
    assert REVIEW["source_identity"]["sha256"] == CONTRACT["input"]["source_hash"]
    size = MANIFEST["source_asset"]["size"]
    assert (len(md), len(md.encode("utf-8")), len(md.rstrip("\n").split("\n"))) == \
        (size["chars"], size["bytes_utf8"], size["lines"])


def test_reviewed_artefact_digests_still_match_the_shipped_bytes():
    pinned = {a["name"]: a["sha256"] for a in REVIEW["reviewed_package"]["artifacts"]}
    assert pinned, "review must pin the bytes it reviewed"
    on_disk = {p.name for p in UP.iterdir() if p.is_file()}
    assert set(pinned) == on_disk, "reviewed artefact set drifted"
    for name, digest in pinned.items():
        assert "sha256:" + hashlib.sha256((UP / name).read_bytes()).hexdigest() == digest


def test_every_ledger_check_is_classified_not_silently_trusted():
    checks = RECHECK["checks"]
    findings = RECHECK["findings"]
    by_check = {f["check_id"]: f for f in findings}
    failed = [c for c in checks if c["status"] == "fail"]
    not_run = [c for c in checks if c["status"] == "not_run"]
    assert failed, "a review with zero failed checks on this package is implausible"
    for c in failed:
        assert c["id"] in by_check, f"{c['id']} fails without a finding"
        assert by_check[c["id"]]["severity"] in ("blocking", "major", "minor", "informational")
        assert by_check[c["id"]].get("attributed_to"), f"{c['id']} finding has no attribution"
        assert by_check[c["id"]]["evidence"] == c["detail"]
    reasons = tuple(RECHECK["not_run"].values())
    assert not_run and all(c["detail"].startswith(reasons) for c in not_run), \
        "every not_run check must carry a declared reason"
    for c in checks:
        if c["status"] == "pass":
            assert c["ok"] is True and c["id"] not in by_check
    summary = RECHECK["summary"]
    assert summary["total"] == len(checks)
    assert summary["passed"] == sum(c["status"] == "pass" for c in checks)
    assert summary["failed"] == len(failed)
    assert summary["not_run"] == len(not_run)


def test_verdict_follows_the_declared_rule():
    findings = REVIEW["findings"]
    blocking = [f for f in findings if f["severity"] == "blocking"]
    package_major = [f for f in findings
                     if f["severity"] == "major" and f["attributed_to"].startswith("wp-")]
    expected = "request-changes" if (blocking or package_major) else "approve"
    assert REVIEW["verdict"] == expected
    assert EVENTS[0]["decision"] == REVIEW["verdict"]
    assert REVIEW["checks_performed"] == RECHECK["checks"]
    assert REVIEW["findings"] == [{**f, "status": "open"} for f in RECHECK["findings"]]


def test_review_products_are_exactly_what_the_generator_emits(tmp_path):
    """Regenerate into a scratch dir: the committed products must be byte-identical.

    The generator is not run in place, so a failing test cannot repair (or
    further corrupt) the tree it is judging.
    """
    proc = subprocess.run([sys.executable, str(OUT / "make_review_report.py"),
                           "--out-dir", str(tmp_path)],
                          capture_output=True, text=True, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    names = ("review_report.json", "review_events.json", "kf_result_wp-5624-04.md")
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), \
            f"{name} was hand-edited or the generator drifted"


def test_review_event_is_schema_valid_and_auditable():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "review-event.schema.json")
                        .read_text(encoding="utf-8"))
    assert len(EVENTS) == 1
    event = EVENTS[0]
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(event)) == []
    assert event["object_ref"] == REVIEW["reviewed_package"]["package_id"]
    assert event["reviewer"]["id"] == REVIEW["reviewer"]["id"]
    assert event["reviewer"]["id"].split("/")[-1] != REVIEW["reviewed_package"]["producer"]
    assert {f["severity"] for f in event["findings"]} == \
        {f["severity"] for f in REVIEW["findings"]}
    assert len(event["findings"]) == len(REVIEW["findings"])
    assert event["conditions"] == REVIEW["conditions"]


def test_nothing_is_marked_verified_and_scope_is_one_report():
    assert REVIEW["claim_state"]["claims_marked_verified_here"] == 0
    assert REVIEW["claim_state"]["claims_in_reviewed_package"] == len(KF_UP["claims"]) == 0

    def walk(obj, path="", hits=None):
        hits = [] if hits is None else hits
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in FORBIDDEN:
                    hits.append(path + "/" + k)
                walk(v, path + "/" + k, hits)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]", hits)
        return hits

    assert walk(REVIEW) == [], "review product must not carry self-verification fields"
    text = json.dumps(REVIEW)
    ids = set(re.findall(r"reports/(\d+)", text)) | \
        set(re.findall(r'"report_id":\s*"(\d+)"', text))
    assert REVIEW["report_id"] == "5624"
    assert ids and ids <= {"5624"}, f"review touched other reports: {ids - {'5624'}}"
    assert REVIEW["reviewed_package"]["package_id"] == "wp-5624-01"


def test_markdown_carries_the_machine_numbers_of_the_report():
    blocks = re.findall(r"```json\n(.*?)```", MD, flags=re.S)
    assert len(blocks) == 1, "exactly one machine-readable block"
    block = json.loads(blocks[0])
    assert block["verdict"] == REVIEW["verdict"]
    assert block["checks_summary"] == REVIEW["checks_summary"]
    assert block["source_sha256"] == REVIEW["source_identity"]["sha256"]
    assert [f["id"] for f in block["findings"]] == [f["id"] for f in REVIEW["findings"]]
    summary = REVIEW["checks_summary"]
    assert f"pass {summary['passed']} / fail {summary['failed']} / not_run {summary['not_run']}" in MD
    assert REVIEW["source_identity"]["sha256"].strip("sha256:") in MD
    # honest-FAIL must be stated, not glossed over
    assert "honest FAIL" in MD and "不通过" in MD
    headline, ledger = summary["headline_groups"], summary["ledger_groups"]
    # every key quantity reproduces from the snapshot ...
    assert headline["failed"] == 0, "a key-quantity mismatch must not be glossed as approve"
    assert f"{headline['failed']} / {headline['total']}" in MD
    # ... and every remaining failure is one of the recorded findings, nothing hidden
    assert ledger["failed"] == len(REVIEW["findings"]), "unexplained ledger failure"
    assert f"{ledger['failed']} / {ledger['total']}" in MD