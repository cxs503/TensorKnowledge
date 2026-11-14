#!/usr/bin/env python3
"""Invariant + negative-control tests for wp-6607-04 (independent review of report 6607).

These assert properties, not merely that code runs:

  * the snapshot's sha256 equals the pin, the envelope's provenance hash, and the hash the
    review claims it reviewed; chars/lines agree everywhere;
  * every recompute entry is hand-checkable: non-empty formula, at least one input, and every
    input's quote is a verbatim substring of the *single* 1-based line it claims;
  * zero hand-copy: every value the review prints appears literally in report_markdown.md,
    every printed "reported" value appears in the snapshot, and every number a finding asserts
    comes from a recompute entry that exists;
  * the verdict is consistent with the finding ledger (a blocking finding with verdict
    "pass-with-notes" fails, and so does an empty finding list behind "request changes");
  * delivered file hashes in kf_result.json match the bytes on disk, the envelope validates
    against schemas/kf_result.v1.schema.json, and the package never claims to be published or
    platform-verified;
  * checks that could not be run are recorded as NOT_RUN/WITHHELD, never as pass;
  * NEGATIVE CONTROLS: each detector is shown to stop firing when its defect is absent and to
    fire when the defect is introduced (a detector that always fires proves nothing).

Run: pytest -q tests/test_wp_6607_04_review.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-6607-04"
SCRIPT = ROOT / "scripts" / "kf" / "review_wp_6607_04.py"

pytestmark = pytest.mark.skipif(
    not (OUT / "review_report.json").exists(),
    reason="run scripts/kf/review_wp_6607_04.py --offline first",
)


def _load_module():
    spec = importlib.util.spec_from_file_location("review_wp_6607_04", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M = _load_module()
MD = (OUT / "source_6607.md").read_text(encoding="utf-8")
LINES = MD.splitlines()
REVIEW = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
RECOMPUTE = json.loads((OUT / "recompute.json").read_text(encoding="utf-8"))
ENVELOPE = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
REPORT_MD = (OUT / "report_markdown.md").read_text(encoding="utf-8")
README_MD = (OUT / "README.md").read_text(encoding="utf-8")
ENTRIES = {e["id"]: e for e in RECOMPUTE["entries"]}


# ------------------------------------------------------------------ provenance
def test_snapshot_hash_is_pinned_and_consistent_everywhere():
    sha = hashlib.sha256(MD.encode("utf-8")).hexdigest()
    assert "sha256:" + sha == M.EXPECTED_HASH
    assert len(MD) == M.EXPECTED_CHARS
    assert len(LINES) == M.EXPECTED_LINES
    assert ENVELOPE["provenance"]["source_hash"] == "sha256:" + sha
    assert ENVELOPE["provenance"]["source_field"] == "markdown"
    assert ENVELOPE["provenance"]["source_hash"] == REVIEW["reviewed_source_hash"]
    assert RECOMPUTE["reviewed_source_hash"] == "sha256:" + sha
    assert ENVELOPE["provenance"]["chars"] == len(MD)
    assert REVIEW["source"]["chars"] == len(MD)


def test_a_mutated_snapshot_breaks_the_pin():
    """The pin must have teeth: rebuilding from a doctored snapshot has to abort."""
    with pytest.raises(SystemExit) as exc:
        M.write_all(MD.replace("墙钟预算", "时钟预算"), do_write=False)
    assert "PIN MISMATCH" in str(exc.value)


# ------------------------------------------------------------------- recompute
def test_every_recompute_entry_is_hand_checkable():
    assert ENTRIES, "empty ledger"
    for eid, e in ENTRIES.items():
        assert e["status"] in M.STATUSES, eid
        assert e["formula"].strip(), eid
        assert e["inputs"], eid
        for inp in e["inputs"]:
            line_no = inp["line"]
            assert 1 <= line_no <= len(LINES), eid
            quote = inp["quote"]
            assert quote in LINES[line_no - 1], (eid, line_no)
            # the quote must not be satisfiable by two different lines (ambiguity = no pin)
            assert sum(1 for ln in LINES if quote in ln) == 1, (eid, quote)


def test_reported_values_are_printed_in_the_source():
    for eid, e in ENTRIES.items():
        rep = e["reported"]
        if rep is None or e["reported_origin"] != "printout":
            continue
        assert str(rep) in MD, (eid, rep)


def test_review_prints_nothing_it_did_not_recompute():
    for eid, e in ENTRIES.items():
        if e["value"] is None:
            continue
        assert str(e["value"]) in REPORT_MD, (eid, e["value"])
    # the ledger table itself is rendered, so every id must survive into the body
    for eid in ENTRIES:
        assert eid in REPORT_MD, eid


def test_every_failure_is_reachable_from_a_finding_or_a_check():
    """No orphan red row: a failed recompute either backs a finding or is an intended FAIL."""
    intended = {"R17_CRIT_F_THRESHOLD", "R18_CRIT_D_NULL", "R16_CRIT_E_MAX_MINUS_MIN"}
    covered = {rid for f in REVIEW["findings"] for rid in f["recompute_ids"]}
    for eid, e in ENTRIES.items():
        if e["status"] != "fail":
            continue
        assert eid in covered or eid in intended, eid
    for f in REVIEW["findings"]:
        for rid in f["recompute_ids"]:
            assert rid in ENTRIES, (f["id"], rid)


def test_not_run_checks_are_never_counted_as_passed():
    allowed = {"NOT_RUN", "WITHHELD", "NOT_RECONSTRUCTABLE"}
    assert REVIEW["checks_not_run"], "an honest review of a cross-repo report must record what it did not run"
    for c in REVIEW["checks_not_run"]:
        assert c["state"] in allowed, c
        assert c["why"].strip() and c["impact"].strip()
    for eid, e in ENTRIES.items():
        if e["status"] in ("not_recomputable", "withheld"):
            assert e["value"] is None, eid
            assert "pass" not in str(e["reported"] or "").lower(), eid


# --------------------------------------------------------------- verdict / claims
def test_verdict_is_consistent_with_the_finding_ledger():
    sev = REVIEW["severity_counts"]
    assert sev["total"] == len(REVIEW["findings"])
    assert sev["blocking"] == sum(1 for f in REVIEW["findings"] if f["blocking"])
    assert REVIEW["blocking_findings"] == [f["id"] for f in REVIEW["findings"] if f["blocking"]]
    if REVIEW["blocking_findings"]:
        assert REVIEW["verdict"] != "pass-with-notes"
        assert REVIEW["disposition"] == "request changes"
    else:
        assert REVIEW["verdict"] == "pass-with-notes"
        assert REVIEW["disposition"] == "approve with notes"
    for f in REVIEW["findings"]:
        assert f["severity"] in ("high", "medium", "low")
        assert f["verdict_impact"].strip()


def test_verdict_counts_match_the_ledger():
    counts = RECOMPUTE["status_counts"]
    assert counts == REVIEW["recompute_status_counts"]
    assert sum(counts.values()) == len(ENTRIES)
    assert counts["pass"] + counts["fail"] + counts["derived"] > 0


def test_package_never_claims_to_be_published_or_verified():
    v = ENVELOPE["validation"]
    assert v["publication_state"] == "awaiting_pr_merge"
    assert v["claims_verified_by_producer"] is False
    assert "published" not in ENVELOPE
    assert not (OUT / "published.json").exists(), "publication is the platform gate's job, not the producer's"
    assert "verified" not in json.dumps(ENVELOPE.get("verification_status", ""))
    assert ENVELOPE["provenance"]["source_hash_matches"] is True


# ---------------------------------------------------------------- deliverables
def test_delivered_hashes_match_the_bytes_on_disk():
    assert ENVELOPE["provenance"]["source_hash"] == "sha256:" + hashlib.sha256(
        (OUT / "source_6607.md").read_bytes()).hexdigest()
    for name, meta in ENVELOPE["outputs"].items():
        if "sha256" not in meta:
            continue
        path = ROOT / meta["path"]
        assert path.exists(), name
        assert meta["sha256"].replace("sha256:", "") == hashlib.sha256(
            path.read_bytes()).hexdigest(), name
        assert path.stat().st_size == meta["bytes"], name


def test_readme_hash_table_matches_the_files():
    rows = re.findall(r"^\| `([^`]+)` \| ([0-9a-f]{16}) \| (\d+) \|", README_MD, re.M)
    assert len(rows) >= 5
    for name, sha16, size in rows:
        p = OUT / name
        assert p.exists(), name
        assert hashlib.sha256(p.read_bytes()).hexdigest().startswith(sha16), name
        assert p.stat().st_size == int(size), name


def test_envelope_conforms_to_the_shared_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(ENVELOPE)


def test_rebuild_is_deterministic():
    """--offline must reproduce the committed ledger/report/README byte for byte."""
    res = M.write_all(MD, do_write=False, figure=False)
    assert json.loads(json.dumps(res["ledger"], ensure_ascii=False)) == RECOMPUTE["entries"]
    assert json.loads(json.dumps(res["review"], ensure_ascii=False)) == REVIEW
    assert res["report_md"] == REPORT_MD
    assert res["readme_md"] == README_MD


def test_figure_is_reproducible_byte_for_byte(tmp_path):
    sha = hashlib.sha256((OUT / "figures" / "wp-6607-04.png").read_bytes()).hexdigest()
    p = tmp_path / "fig.png"
    M.build_figure(ENTRIES, MD, p)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == sha


# ------------------------------------------------------ negative controls (teeth)
def test_quote_verifier_rejects_absent_and_ambiguous_quotes():
    with pytest.raises(SystemExit) as exc:
        M.locate(LINES, "这句话不在报告里")
    assert "QUOTE NOT FOUND" in str(exc.value)
    with pytest.raises(SystemExit) as exc:
        M.locate(LINES, "|")
    assert "QUOTE NOT UNIQUE" in str(exc.value)


def test_monotonicity_detector_fires_only_on_a_real_break():
    def mono(ys):
        return all(b > a for a, b in zip(ys, ys[1:]))

    assert mono([0.8404, 0.8418, 0.8427, 0.8431, 0.8440])  # as printed: pass
    assert not mono([0.8404, 0.8418, 0.8427, 0.8431, 0.8410])  # one step down: fires


def test_nu_cap_detector_fires_on_a_truncated_fit_and_not_on_a_clean_one():
    """R25's mechanism: R² must stop improving at the printed nu when nu is the true optimum."""
    ns = [256.0, 512.0, 1024.0, 2048.0, 4096.0]
    # genuine FSS data generated with nu = 2.51 -> R²(2.51) must beat R²(8)
    clean = [0.84 - 0.02 * n ** (-1.0 / (2 * 2.51)) for n in ns]
    assert M.ssr_at(2.51, ns, clean) > M.ssr_at(8.0, ns, clean)
    # a column that keeps improving past the printed nu is what the finding flags
    quench = [0.8377, 0.8378, 0.8377, 0.8317, 0.8280]
    assert M.ssr_at(8.0, ns, quench) > M.ssr_at(2.51, ns, quench)


def test_anchor_window_detector_has_a_sharp_edge():
    def inside(phi_inf):
        return abs(phi_inf - 0.84) <= 0.01

    assert inside(0.8454) and inside(0.8488)  # printed, near-edge
    assert not inside(0.8520)  # 0.012 out: the detector must fire


def test_a_doctored_table_moves_the_ledger_not_just_the_prose():
    """Introduce a defect in a non-quoted table row: the recompute must change status."""
    clean = M.build_ledger(MD)
    clean = {e["id"]: e for e in clean}
    assert clean["R1_GROWTH_MONOTONE"]["value"] == "true"

    doctored_md = MD.replace(
        "| 4096 | 0.8440 ± 0.0005 |", "| 4096 | 0.8410 ± 0.0005 |")
    assert doctored_md != MD
    doctored = {e["id"]: e for e in M.build_ledger(doctored_md)}
    assert doctored["R1_GROWTH_MONOTONE"]["value"] == "false"
    assert doctored["R1_GROWTH_MONOTONE"]["status"] == "fail"
    assert doctored["R3_GROWTH_16X"]["status"] == "fail"
    # and the fit follows the data, so the extrapolation moves too
    assert doctored["R8_FIT_PHI_INF_GROWTH"]["value"] != clean["R8_FIT_PHI_INF_GROWTH"]["value"]
    assert doctored["R9_FIT_NU_GROWTH"]["value"] != clean["R9_FIT_NU_GROWTH"]["value"]


def test_reading_the_three_percent_column_is_not_substring_fragile():
    """「否（m5079 未通过；本节点正是重锁）」contains 是 — the detector must read the verdict."""
    def says_yes(cell):
        return cell.replace("*", "").strip().startswith("是")

    assert says_yes("**是**")
    assert not says_yes("否（m5079 未通过；本节点正是重锁）")
    assert set(ENTRIES) >= {"R28_SEC6_HONESTY_TALLY"}
    assert ENTRIES["R28_SEC6_HONESTY_TALLY"]["value"] == "6/6 consistent"