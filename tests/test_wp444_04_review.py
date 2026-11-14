"""wp-444-04 · invariants of the independent-review package for report 444 / wp-444-01.

Design rule of this file: wherever a fact can be re-derived cheaply, it *is*
re-derived here instead of being read back out of the emitted JSON.  The
review's own numbers are therefore not trusted by the review's tests.

Offline: no network.  Record-level checks (C04/C12/C20) are declared not_run /
online-only by the report itself and are not silently treated as passed.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs/kf/wp-444-04"
SNAPSHOT = PKG / "source/report_444.md"
KF_MD = PKG / "KF-RESULT-wp-444-04.md"
FIGURE = PKG / "fig_wp444_04_recompute.png"
UPSTREAM_DOC = ROOT / "docs/kf_result_wp-444-01.md"
EVENTS = PKG / "review_events.json"
REVIEW = PKG / "review_report.json"
KF_SCHEMA = ROOT / "schemas/kf_result.v1.schema.json"

sys.path.insert(0, str(ROOT / "scripts"))
import ke_state_machine as sm  # noqa: E402

FORBIDDEN = ("verified", "verification_status", "verification_level", "is_verified",
             "gate_confirmed")
NUM = r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"


def _json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def md() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def review() -> dict:
    return _json(REVIEW)


@pytest.fixture(scope="module")
def events() -> dict:
    return _json(EVENTS)


# ------------------------------------------------------------------ artefacts
def test_package_artifacts_exist():
    for p in (SNAPSHOT, REVIEW, EVENTS, KF_MD, FIGURE):
        assert p.is_file(), p


def test_snapshot_hash_matches_the_hash_the_upstream_package_quotes(md):
    declared = re.findall(r"\b[0-9a-f]{64}\b", UPSTREAM_DOC.read_text(encoding="utf-8"))
    assert declared, "the upstream document must quote the digest it registered"
    assert "sha256:" + hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == "sha256:" + declared[0]


def test_review_source_identity_is_consistent(review, md):
    src = review["source"]
    assert src["sha256"] == "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert src["chars"] == len(md)
    assert review["reviewed_package"]["source_hash"] == src["sha256"]
    assert review["reviewed_package"]["document"]["sha256"] == "sha256:" + hashlib.sha256(
        UPSTREAM_DOC.read_bytes()).hexdigest()


# ---------------------------------------------------------------- quote binding
def _tool_evidence(e: dict, md: str) -> str:
    """Return the text a piece of evidence claims to quote, from its declared source."""
    src = e.get("source", "")
    if src.endswith("report_444.md"):
        return md
    if src.endswith("kf_result_wp-444-01.md"):
        return UPSTREAM_DOC.read_text(encoding="utf-8")
    if src.startswith("schemas/"):
        return (ROOT / src).read_text(encoding="utf-8")
    return ""


def test_every_review_quote_is_verbatim_in_its_declared_source(md, review):
    quoted = 0
    for f in review["findings"]:
        for e in f["evidence"]:
            if "quote" not in e:
                continue
            haystack = _tool_evidence(e, md)
            if not haystack:                       # recomputation evidence, not a quotation
                continue
            quoted += 1
            assert e["quote"] in haystack, (f["id"], e["quote"])
    assert quoted >= 8, f"the review must bind its findings to raw text; only {quoted} quotes"


def test_sliced_quotes_carry_a_true_char_span(md, review):
    slices = [(f["id"], e) for f in review["findings"] for e in f["evidence"]
              if e.get("source", "").endswith("report_444.md") and "char_span" in e]
    assert slices
    for _, e in slices:
        a, b = e["char_span"]
        assert md[a:b] == e["quote"]
        assert md[:a].count("\n") + 1 == e["start_line"]


# ------------------------------------------------------------- numeric anchors
def _ittc(re):
    return 0.075 / (math.log10(re) - 2.0) ** 2


def _blasius(re):
    return 1.328 / math.sqrt(re)


def _ps(re):
    return 0.455 / (math.log10(re) ** 2.58)


def test_report_table_is_parsed_not_transcribed(md, review):
    """The §6 rows the review asserts must be the bytes in the markdown."""
    for row in review["recomputation"]["rows"]:
        label = row["label"]
        assert f"| {label} |" in md, label
        line = next(ln for ln in md.split("\n") if ln.startswith(f"| {label} |"))
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        assert float(cells[1]) == pytest.approx(row["reported_baseline"])
        assert float(cells[2]) == pytest.approx(row["reported_actual"])


def test_friction_baselines_rederived_from_the_named_formulas(review):
    rows = {r["label"]: r for r in review["recomputation"]["rows"]}
    ittc = rows["ITTC-1957 Cf (Re=1e8)"]
    blas = rows["Blasius Cf (Re_L=1e6)"]
    ps = rows["P-S Cf (Re_L=1e8)"]

    assert _ittc(1e8) == pytest.approx(0.0020833333333333, rel=1e-12)
    assert ittc["recomputed"] == pytest.approx(_ittc(1e8), rel=1e-9)
    assert ittc["deviation_pct"] == pytest.approx((0.002170 - _ittc(1e8)) / _ittc(1e8) * 100, rel=1e-6)
    assert abs(ittc["deviation_pct"]) > 3.0 and ittc["within_3pct"] is False

    assert blas["recomputed"] == pytest.approx(_blasius(1e6), rel=1e-12)
    assert abs(blas["deviation_pct"]) < 1e-6 and blas["within_3pct"] is True

    assert ps["recomputed"] == pytest.approx(_ps(1e8), rel=1e-9)
    assert abs(ps["deviation_pct"]) > 3.0 and ps["within_3pct"] is False
    # the customary -1700/Re term must not rescue the printed value either
    variant = _ps(1e8) - 1700.0 / 1e8
    assert abs((0.002012 - variant) / variant * 100) > 3.0


def test_holtrop_row_is_withheld_not_passed(review):
    rows = {r["label"]: r for r in review["recomputation"]["rows"]}
    hm = rows["HM 1+k (Cb=0.6)"]
    assert hm["status"] == "withheld"
    assert hm["recomputed"] is None and hm["deviation_pct"] is None
    fam = review["recomputation"]["holtrop_family"]
    assert fam["samples"] >= 100
    assert fam["min"] <= fam["median"] <= fam["max"]
    # the printed value sits outside the standard-formula envelope for Cb = 0.6
    assert not (fam["min"] <= hm["reported_baseline"] <= fam["max"])


def test_holtrop_family_rederived_independently(review):
    """A second implementation of the same closed form must reproduce the envelope."""
    def k(L, B, T, cb, cm):
        nabla, cp = cb * L * B * T, cb / cm
        return (0.93 + 0.487118 * 1.0 * (B / L) ** 1.06806 * (T / L) ** 0.46106
                * (L / nabla ** (1 / 3)) ** 0.121563 * (L ** 3 / nabla) ** 0.36486
                * (1 - cp) ** (-0.604247))
    vals = [k(L, bl * L, tl * L, 0.6, cm)
            for L in (80.0, 100.0, 150.0, 200.0, 280.0, 320.0)
            for bl in (0.11, 0.14, 0.16, 0.18, 0.20)
            for tl in (0.030, 0.040, 0.050, 0.060)
            for cm in (0.96, 0.98, 0.995)]
    fam = review["recomputation"]["holtrop_family"]
    assert len(vals) == fam["samples"]
    assert min(vals) == pytest.approx(fam["min"], abs=5e-5)
    assert max(vals) == pytest.approx(fam["max"], abs=5e-5)
    assert sorted(vals)[len(vals) // 2] == pytest.approx(fam["median"], abs=5e-5)


def test_ordering_invariant_is_the_reason_for_f05(md, review):
    cross = review["recomputation"]["ordering_at_1e8"]
    assert _ittc(1e8) < _ps(1e8)                       # formulas: ITTC below P-S at 1e8
    assert cross["ittc_below_ps"] is True
    assert cross["crossover_re"] < 1e7                 # they do cross, well below 1e8
    # the report prints the opposite order
    assert 0.002170 > 0.002012
    assert any(f["id"] == "F-05" for f in review["findings"])


def test_tally_and_governance_arithmetic(md, review):
    rec = review["recomputation"]
    ta = rec["tally_arithmetic"]
    assert ta["questions"] == sum(ta["declared_questions"]) == ta["printed_total"]["questions"]
    assert ta["passed"] == sum(ta["declared_passed"]) == ta["printed_total"]["passed"]
    assert ta["sum_matches_printed_total"] is True
    # "原始长度: N 字符" must be the length of a real prefix of the current text
    n = rec["governance_original_chars"]
    prefix = "\n".join(md.split("\n")[:rec["governance_prefix_boundary"]["lines"]])
    assert len(prefix) == n


# --------------------------------------------------------------------- checks
def test_check_statuses_counts_and_reasons(review):
    checks = review["checks"]
    ids = [c["id"] for c in checks]
    assert len(ids) == len(set(ids))
    for c in checks:
        assert c["status"] in {"pass", "fail", "not_run"}
        if c["status"] == "not_run":
            assert c["basis"].startswith("not_run:")
    counts = review["counts"]
    assert counts["checks"] == len(checks)
    for k in ("pass", "fail", "not_run"):
        assert counts[k] == sum(1 for c in checks if c["status"] == k)
    assert counts["pass"] + counts["fail"] + counts["not_run"] == counts["checks"]


def test_every_failure_is_carried_by_a_finding(review):
    failed = {c["id"] for c in review["checks"] if c["status"] == "fail"}
    covered = {cid for f in review["findings"] for cid in f["check_ids"]}
    assert failed <= covered, failed - covered
    not_run = {c["id"] for c in review["checks"] if c["status"] == "not_run"}
    assert not_run == {"C12", "C18", "C20"}
    assert review["offline_reproducibility"]["online_only_checks"] == ["C04", "C12", "C20"]


def test_disposition_follows_the_evidence(review):
    blocking = [f["id"] for f in review["findings"] if f["blocking"]]
    assert review["blocking_findings"] == blocking
    if not blocking:
        assert review["disposition"] in {"approve", "approve-with-notes"}
        assert review["ledger_decision"] == "approve"
    assert review["ledger_decision"] == ("approve" if review["disposition"].startswith("approve")
                                         else "request-changes")
    # a high finding must be escalated rather than dropped
    for f in review["findings"]:
        if f["severity"] == "high":
            assert f.get("escalate"), f["id"]
    assert [e["id"] for e in review["escalations"]] == ["E-01"]


# ---------------------------------------------------------------------- ledger
def test_ledger_folds_to_approved_with_an_independent_reviewer(events, review):
    ctx = {"producer_ids": events["producer_ids"]}
    state, codes = sm.fold(events["events"], ctx, initial_state=sm.submit(ctx))
    assert (state, codes) == ("approved", ["OK_APPROVED"])
    assert events["fold"]["state"] == state and events["fold"]["outcome_codes"] == codes
    assert events["events"][0]["decision"] == review["ledger_decision"]
    reviewer = events["events"][0]["reviewer"]["id"]
    assert sm.canonical_identity(reviewer) not in {sm.canonical_identity(p)
                                                  for p in events["producer_ids"]}
    assert events["events"][0]["independence_basis"] == "distinct-identity"
    assert events["system_transitions"][0]["to"] == "in-review"


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_review_writes_no_self_verification_field(review, events):
    """No *field* may be named like a verification verdict (prose may mention the word)."""
    for payload in (review, events):
        bad = sorted({k for k in _keys(payload) if k in FORBIDDEN})
        assert bad == [], bad
    assert review["self_audit"]["forbidden_verification_fields_present"] == []


# -------------------------------------------------------------------- rendered md
def test_kf_result_envelope_is_valid_and_matches_the_source(md):
    text = KF_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
    assert len(blocks) == 1, "the rendered result must carry exactly one json block"
    env = json.loads(blocks[0])
    jsonschema.Draft202012Validator(_json(KF_SCHEMA)).validate(env)
    assert env["package_id"] == "wp-444-04"
    assert env["task_type"] == "04-independent-review"
    assert env["report_id"] == "444"
    assert env["provenance"]["source_hash"] == "sha256:" + hashlib.sha256(
        SNAPSHOT.read_bytes()).hexdigest()
    assert env["provenance"]["source_hash_matches"] is True
    assert set(env["outputs"]) == {"review_report.json", "review_events.json"}
    assert isinstance(env["outputs"]["review_events.json"], list)


def test_rendered_report_quotes_the_source_verbatim(md):
    text = KF_MD.read_text(encoding="utf-8")
    for quote in re.findall(r"\| `(.+?)` \| char_span=", text):
        assert quote.replace("\\|", "|") in md


def test_figure_is_a_png_and_is_referenced(review):
    assert FIGURE.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert FIGURE.stat().st_size > 20_000
    assert FIGURE.name in review["recomputation"]["figure"]
    assert FIGURE.name in KF_MD.read_text(encoding="utf-8")
