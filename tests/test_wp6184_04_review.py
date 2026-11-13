"""Acceptance tests for wp-6184-04 (independent review of wp-6184-01, report 6184).

Offline by construction: every assertion runs against the committed source
snapshot, the committed read-only copy of the upstream package, and the emitted
review_report.json. Only test_rerun_is_structurally_deterministic touches the
review script, and it forces --no-api so no network is needed.

    python -m pytest tests/test_wp6184_04_review.py -q
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs/kf/wp-6184-04"
REVIEW = PKG / "review_report.json"
SNAPSHOT = PKG / "source_snapshot.md"
UPSTREAM = PKG / "upstream_snapshot/kf_result.json"
SCHEMA = PKG / "review_report.schema.json"
CONTRACT_HASH = "sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c"
CONTRACT_CHARS = 2406
SELF_ATTEST_KEYS = {"verified", "verification_status", "verification_level",
                    "is_verified", "gate_confirmed"}


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def md() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def review() -> dict:
    return load(REVIEW)


def test_review_report_is_valid_json(review):
    assert isinstance(review, dict)
    assert review["review_id"] == "wp-6184-04"
    assert review["report_id"] == "6184"
    assert review["verdict"] in {"pass", "fail", "needs-fix"}


def test_review_report_schema_pass(review):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(review, load(SCHEMA))


def test_source_snapshot_matches_contract_hash(md):
    got = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert got == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    assert review_hash_matches(md)


def review_hash_matches(md):
    r = load(REVIEW)
    return r["provenance"]["source_hash"] == CONTRACT_HASH and r["provenance"]["source_chars"] == len(md)


def test_upstream_snapshot_is_the_reviewed_package(review):
    up = load(UPSTREAM)
    assert up["package_id"] == "wp-6184-01"
    assert up["provenance"]["source_hash"] == CONTRACT_HASH
    assert review["reviewed_package"]["source_hash"] == CONTRACT_HASH
    digest = "sha256:" + hashlib.sha256(UPSTREAM.read_bytes()).hexdigest()
    assert review["provenance"]["upstream_kf_result_sha256"] == digest


def test_every_upstream_locator_is_byte_exact(md):
    up = load(UPSTREAM)
    assets = up["outputs"]["asset_manifest.json"]["assets"]
    assert len(assets) == 10
    for a in assets:
        loc = a["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) == 1, a["asset_id"]
        assert md.count("\n", 0, loc["start_char"]) + 1 == loc["start_line"], a["asset_id"]


def test_verdict_follows_the_blocking_rule(review):
    counts = review["summary_counts"]
    failed = sum(1 for c in review["checks"] if c["status"] == "fail")
    blocking = sum(1 for c in review["checks"] if c["status"] == "fail" and c.get("blocking"))
    assert counts["fail_blocking"] == blocking
    assert counts["fail_non_blocking"] == failed - blocking
    assert review["verdict"] == ("pass" if blocking == 0 else "fail")
    assert counts["checks"] == len(review["checks"])


def test_no_self_attestation_fields_anywhere(review):
    """S9 analogue: the reviewer may judge, but may not mint gate fields."""

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                assert k not in SELF_ATTEST_KEYS, k
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(review)


def test_every_finding_quote_is_verbatim_in_the_source(review, md):
    for f in review["findings"]:
        q = f.get("source_quote")
        assert q, f["id"]
        assert q in md, f"[{f['id']}] quote not found verbatim: {q!r}"


def test_published_margin_column_reproduces(md):
    rows = []
    for line in md.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or cells[0] == "船型" or set(cells[0]) <= {"-"}:
            continue
        try:
            rows.append((cells[0], float(cells[1]), float(cells[2]), float(cells[3])))
        except ValueError:
            pass
    assert len(rows) == 11
    for ship, eexi, req, margin in rows:
        a = (req - 5e-4 - (eexi + 5e-4)) / (req - 5e-4) * 100
        b = (req + 5e-4 - (eexi - 5e-4)) / (req + 5e-4) * 100
        lo, hi = min(a, b) - 0.05, max(a, b) + 0.05
        assert lo <= margin <= hi, f"{ship}: published {margin} outside [{lo:.3f},{hi:.3f}]"
    compliant = [s for s, e, r, _ in rows if e <= r]
    assert compliant == ["feeder_1700teu", "lng_174k"]


def test_completeness_gap_is_surfaced_not_hidden(review, md):
    r10 = next(c for c in review["checks"] if c["id"].startswith("R10"))
    assert r10["status"] == "fail" and r10["blocking"] is False
    assert "backend/api/green_shipping.py" in r10["evidence"]["unregistered"]
    assert "backend/api/green_shipping.py" in md
    assert any("green_shipping.py" in f["statement"] for f in review["findings"])


def test_unverifiable_claims_are_marked_not_run(review):
    ids = {c["id"] for c in review["checks"] if c["status"] == "not_run"}
    assert any(i.startswith("R9") for i in ids)
    why = {n["id"] for n in review["checks_not_run"]}
    assert {"R9"} <= why and len(why) >= 3


def test_rerun_is_structurally_deterministic(tmp_path):
    subprocess.run([sys.executable, "scripts/kf/wp6184_review.py",
                    "--no-api", "--out", str(tmp_path)],
                   cwd=ROOT, check=True, capture_output=True)
    fresh = load(tmp_path / "review_report.json")
    committed = load(REVIEW)
    strip = lambda r: json.dumps([{k: c[k] for k in ("id", "status", "blocking", "detail")}
                                  for c in r["checks"]], ensure_ascii=False)
    assert strip(fresh) == strip(committed)
    assert [{k: f[k] for k in ("id", "severity", "blocking")} for f in fresh["findings"]] == \
           [{k: f[k] for k in ("id", "severity", "blocking")} for f in committed["findings"]]
    assert fresh["verdict"] == committed["verdict"]
    assert (tmp_path / "source_snapshot.md").read_text(encoding="utf-8") == \
           SNAPSHOT.read_text(encoding="utf-8")

def test_checks_artifact_matches_the_report(review):
    """The figure/publish pipelines read review_checks.json; it must not drift."""
    art = load(PKG / "review_checks.json")
    assert art["source_hash"] == review["provenance"]["source_hash"]
    got = [(c["id"], c["status"], c["blocking"]) for c in art["checks"]]
    want = [(c["id"], c["status"], c["blocking"]) for c in review["checks"]]
    assert got == want
    assert art["completeness"]["unregistered"] == ["backend/api/green_shipping.py"]


def test_evidence_figure_is_shipped():
    png = PKG / "figures/review_6184_evidence.png"
    assert png.is_file() and png.stat().st_size > 20_000
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
