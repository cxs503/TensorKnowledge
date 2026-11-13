"""Regression tests for the wp-542-04 independent-review harness (report 542).

These assert invariants of the review pipeline, not the review's opinion:
the harness must reproduce the same verifiable facts on every run, must keep
the source hash bound to the reviewed report, and must never mark claims as
verified.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-542-04"
SCRIPT = ROOT / "scripts" / "kf" / "review_wp542_04.py"
UPSTREAM = ROOT / "docs" / "kf" / "wp-542-01"
DECLARED = "sha256:a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40"


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("wp54204")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--offline", "--out", str(out)],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    return out, json.loads((out / "review_report.json").read_text(encoding="utf-8"))


def test_source_snapshot_is_the_reviewed_report(run):
    out, report = run
    import hashlib
    snap = (out / "source_snapshot.md").read_bytes()
    assert "sha256:" + hashlib.sha256(snap).hexdigest() == DECLARED
    assert report["source"]["hash_recomputed"] == DECLARED


def test_inventory_is_complete_and_invented_free(run):
    _, report = run
    inv = report["inventory"]
    assert inv["missing_from_manifest"] == []
    assert inv["extra_in_manifest"] == []
    assert inv["path_tokens_in_source"] == inv["manifest_paths"]


def test_all_markdown_locators_are_verbatim(run):
    _, report = run
    assert report["locator"]["checked"] > 0
    assert report["locator"]["problems"] == []


def test_alias_counting_is_measured_not_assumed(run):
    _, report = run
    ident = report["identity"]
    assert ident["distinct_basenames_files"] < ident["distinct_path_strings"]
    assert ident["distinct_path_strings"] - ident["distinct_basenames_files"] == len(ident["basename_variants"])


def test_no_claim_is_marked_verified(run):
    _, report = run
    for claim in report["claims"]:
        assert claim["status"] in {"supported", "partially-supported", "unresolved", "refuted"}
    assert report["reviewer_independence"]["upstream_self_verification_adopted_as_verdict"] is False


def test_upstream_self_gate_is_not_adopted(run):
    _, report = run
    assert report["upstream_gate_record"]["adopted_as_verdict"] is False
    assert "C16" in report["checks_not_run"]


def test_every_finding_quote_is_verbatim(run):
    out, report = run
    md = (out / "source_snapshot.md").read_text(encoding="utf-8")
    for finding in report["findings"]:
        assert finding["evidence"], finding["id"]
        for ev in finding["evidence"]:
            assert ev["quote"] in md, (finding["id"], ev["quote"][:40])


def test_verdict_matches_blocking_findings(run):
    _, report = run
    blocking = [f for f in report["findings"] if f["blocking"]]
    assert report["verdict"] == ("needs-fix" if blocking else "pass")


def test_delivery_markdown_has_one_json_block_bound_to_the_report(run):
    out, _ = run
    md = (out / "KF-RESULT-wp-542-04.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    assert len(blocks) == 1
    env = json.loads(blocks[0])
    assert env["package_id"] == "wp-542-04"
    assert env["task_type"] == "04-independent-review"
    assert env["report_id"] == "542"
    assert env["provenance"]["source_hash"] == DECLARED
    assert env["provenance"]["source_field"] == "markdown"
    assert env["outputs"]["review_report.json"]["verdict"] in {"pass", "needs-fix"}


def test_upstream_package_untouched(run):
    """The review must not modify upstream artifacts (compare to its own declared hash)."""
    import hashlib
    kf = json.loads((UPSTREAM / "kf_result.json").read_text(encoding="utf-8"))
    declared = kf["outputs"]["asset_manifest.json"]["sha256"]
    got = hashlib.sha256((UPSTREAM / "asset_manifest.json").read_bytes()).hexdigest()
    assert got == declared