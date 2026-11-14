#!/usr/bin/env python3
"""Invariant + negative-control tests for wp-5716-04 (independent review of report 5716).

These assert properties, not merely that code runs:

  * the snapshot's sha256 equals the pinned hash, the envelope's provenance hash, and the
    hash the review claims it reviewed;
  * every recompute entry is hand-checkable: non-empty formula, and every input's quote is
    a verbatim substring of the source line it claims;
  * zero hand-copy: every recomputed value string is literally present in report.md, and
    every number a finding asserts comes from a recompute entry that exists;
  * the verdict is consistent with the finding ledger (blocking finding with verdict
    "pass" would be a failure, and so would "needs-fix" with nothing blocking);
  * delivered file hashes in kf_result.json match the bytes on disk, and the package never
    claims to be published or platform-verified;
  * NEGATIVE CONTROLS: each detector stops firing when the source is mutated to remove the
    defect (a detector that fires on any input proves nothing), and a mutated snapshot
    breaks the hash pin.

Run: pytest -q tests/test_wp_5716_04_review.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-5716-04"
SCRIPT = ROOT / "scripts" / "kf" / "review_wp_5716_04.py"

pytestmark = pytest.mark.skipif(
    not (OUT / "review_report.json").exists(),
    reason="run scripts/kf/review_wp_5716_04.py first",
)


def _load_module():
    spec = importlib.util.spec_from_file_location("review_wp_5716_04", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M = _load_module()
MD = (OUT / "source_5716.md").read_text(encoding="utf-8")
REVIEW = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
RECOMPUTE = json.loads((OUT / "recompute.json").read_text(encoding="utf-8"))
ENVELOPE = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
REPORT_MD = (OUT / "report.md").read_text(encoding="utf-8")
README_MD = (OUT / "README.md").read_text(encoding="utf-8")
ENTRIES = {e["id"]: e for e in RECOMPUTE["entries"]}


# ------------------------------------------------------------------ provenance
def test_snapshot_hash_is_pinned_and_consistent_everywhere():
    sha = hashlib.sha256(MD.encode("utf-8")).hexdigest()
    assert sha == M.EXPECTED_HASH
    assert len(MD) == M.EXPECTED_CHARS
    assert ENVELOPE["provenance"]["source_hash"] == "sha256:" + sha
    assert ENVELOPE["provenance"]["source_hash"] == REVIEW["reviewed_source_hash"]
    assert RECOMPUTE["reviewed_source_hash"] == "sha256:" + sha
    assert ENVELOPE["provenance"]["chars"] == len(MD)
    assert REVIEW["source"]["chars"] == len(MD)


def test_a_mutated_snapshot_breaks_the_pin():
    """The pin must have teeth: rebuilding from a doctored snapshot has to abort."""
    with pytest.raises(SystemExit) as exc:
        M.write_all(MD.replace("墙钟 50.7 s", "墙钟 41.5 s"), {"markdown": MD}, do_write=False)
    assert "PIN MISMATCH" in str(exc.value)


# ------------------------------------------------------------------- recompute
def test_every_recompute_entry_is_hand_checkable():
    assert len(RECOMPUTE["entries"]) >= 20
    lines = MD.splitlines()
    for e in RECOMPUTE["entries"]:
        assert e["formula"].strip(), e["id"]
        assert e["inputs"], e["id"]
        assert e["status"] in {"pass", "fail", "derived", "violated", "unreconstructible"}
        if e["reported"] is not None:
            assert e["reported_quote"] and e["reported_line"], e["id"]
            assert e["reported_quote"] == lines[e["reported_line"] - 1].strip(), e["id"]
        for i in e["inputs"]:
            assert isinstance(i["line"], int) and i["line"] >= 1, e["id"]
            line = lines[i["line"] - 1].strip()
            assert i["quote"] == line, (e["id"], i["name"])
            assert i["value"] in line, (e["id"], i["name"])


def test_every_printed_value_comes_from_recompute_json():
    """Zero hand-copy: report.md must carry the formatter's own strings."""
    for e in RECOMPUTE["entries"]:
        assert e["value_str"] in REPORT_MD, (e["id"], e["value_str"])
        assert e["id"] in REPORT_MD, e["id"]


def test_recompute_is_deterministic():
    a = M.recompute(MD, M.extract(MD))
    b = M.recompute(MD, M.extract(MD))
    for k in a:
        assert a[k]["value"] == b[k]["value"]
        assert a[k]["status"] == b[k]["status"]


def test_the_two_defining_numbers_of_the_review_reproduce_by_hand():
    """The headline findings must be re-derivable from the printed report alone."""
    ex = M.extract(MD)
    v = lambda n: float(ex[n]["value"])
    cb_literal = (v("dwt_t") / v("dwt_over_disp")) / (v("L_pp_m") * v("B_m") * v("T_m"))
    assert cb_literal == pytest.approx(0.840577, abs=1e-6)
    assert abs((cb_literal - v("cb_declared")) / v("cb_declared") * 100) > v("cb_gate_tol_pct")

    cb_rho = cb_literal / M.RHO_SEAWATER
    assert cb_rho == pytest.approx(v("cb_reconstructed"), abs=1e-4)
    assert "1.025" not in MD, "the report must not state the density (that is finding F1)"


# -------------------------------------------------------------------- findings
def test_findings_bind_to_entries_that_exist_and_to_real_source_lines():
    lines = MD.splitlines()
    assert REVIEW["findings"]
    for f in REVIEW["findings"]:
        assert f["recompute_ids"], f["id"]
        for rid in f["recompute_ids"]:
            assert rid in ENTRIES, (f["id"], rid)
        assert f["claim"]["quote"] == lines[f["claim"]["line"] - 1].strip(), f["id"]
        assert f["severity"] in {"high", "medium", "low"}
        assert f["category"] and f["remediation"] and f["observed"] and f["expected"]


def test_low_severity_findings_are_never_blocking():
    for f in REVIEW["findings"]:
        if f["severity"] == "low":
            assert not f["blocking"], f["id"]
        if f["category"] == "unreconstructible_number":
            assert not f["blocking"], f["id"]


def test_verdict_and_disposition_follow_the_finding_ledger():
    blocking = [f for f in REVIEW["findings"] if f["blocking"]]
    high = [f for f in REVIEW["findings"] if f["severity"] == "high"]
    if blocking or high:
        assert REVIEW["verdict"] == "needs-fix"
        assert REVIEW["disposition"] == "request changes"
    val = ENVELOPE["validation"]
    assert val["blocking_findings"] == [f["id"] for f in blocking]
    assert val["verdict"] == REVIEW["verdict"]
    assert val["severity_counts"]["total"] == len(REVIEW["findings"])
    assert set(REVIEW["blocking_findings"]) == {f["id"] for f in blocking}


def test_checks_that_were_not_run_are_declared_not_passed():
    states = {c["state"] for c in REVIEW["checks_not_run"]}
    assert "NOT_RUN" in states and "WITHHELD" in states
    joined = " ".join(c["why"] for c in REVIEW["checks_not_run"])
    assert "campaign_ice_nav" in joined  # the upstream artifacts really are absent
    assert not (ROOT / "artifacts" / "campaign_ice_nav").exists()


# ------------------------------------------------------- negative controls (6)
def _findings_after(mutation):
    md = MD.replace(*mutation)
    assert md != MD, "mutation did not apply: %r" % (mutation,)
    ex = M.extract(md)
    rec = M.recompute(md, ex)
    return {f["id"] for f in M.detect_findings(ex, rec)}


def test_negative_control_wallclock_contradiction():
    assert "F4" in {f["id"] for f in REVIEW["findings"]}
    assert "F4" not in _findings_after(("墙钟 50.7 s", "墙钟 41.5 s"))


def test_negative_control_c3_voyage_time_contradiction():
    assert "F2" in {f["id"] for f in REVIEW["findings"]}
    assert "F2" not in _findings_after(("总航程 684.1 nm / 63.3 h", "总航程 684.1 nm / 68.2 h"))


def test_negative_control_cb_gate_criterion():
    assert "F1" in {f["id"] for f in REVIEW["findings"]}
    # widen the declared Cb so the literal formula lands inside its own tolerance
    assert "F1" not in _findings_after(("Cb=0.82,", "Cb=0.84,"))


def test_negative_control_disclosure_register():
    assert "F3" in {f["id"] for f in REVIEW["findings"]}
    assert "F3" not in _findings_after(("+ 7 项披露", "+ 4 项披露"))


def test_negative_control_figure_count():
    assert "F9" in {f["id"] for f in REVIEW["findings"]}
    assert "F9" not in _findings_after(("JSON/报告/7 图齐全", "JSON/报告/4 图齐全"))


def test_corroborated_claims_are_not_empty():
    ids = {k["id"] for k in REVIEW["corroborated_claims"]}
    assert {"K1", "K2"}.issubset(ids)
    for k in REVIEW["corroborated_claims"]:
        for rid in k["recompute_ids"]:
            assert rid in ENTRIES, (k["id"], rid)


# ----------------------------------------------------------------- deliverables
def test_delivered_hashes_match_the_bytes_on_disk():
    outs = ENVELOPE["outputs"]
    assert len(outs) >= 7
    for name, meta in outs.items():
        p = ROOT / meta["path"]
        assert p.exists(), name
        b = p.read_bytes()
        assert hashlib.sha256(b).hexdigest() == meta["sha256"], name
        assert len(b) == meta["bytes"], name


def test_package_does_not_claim_publication_or_verification():
    assert ENVELOPE["validation"]["publication_state"] == "awaiting_pr_merge"
    blob = json.dumps([ENVELOPE, REVIEW, RECOMPUTE], ensure_ascii=False)
    assert "platform_verified" not in blob
    assert '"verified": true' not in blob
    assert not (OUT / "published.json").exists()
    assert "awaiting_pr_merge" in REPORT_MD and "awaiting_pr_merge" in README_MD


def test_report_carries_the_required_sections():
    for header in ("① 复核对象与范围", "② 怎么做的", "③ 复核结果",
                   "④ 结果图", "⑤ 注意点与局限", "⑥ 误差判定", "⑦ 复现"):
        assert header in REPORT_MD, header
    assert "是否 <3%" in REPORT_MD
    assert "无独立基准" in REPORT_MD  # never silently implied to pass


def test_figure_is_present_and_not_blank():
    p = OUT / "figures" / "fig_review_errors.png"
    assert p.exists() and p.stat().st_size > 20_000
    import matplotlib.image as image
    im = image.imread(p)
    assert im.shape[0] > 300 and im.shape[1] > 600
    assert float((im[:, :, :3].mean(axis=2) < 250).mean()) > 0.05


def test_envelope_conforms_to_the_shared_schema():
    """The envelope must satisfy schemas/kf_result.v1.schema.json (rev 1.1, closed)."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(ENVELOPE),
                  key=lambda e: list(e.path))
    assert errs == [], [str(e) for e in errs]
    assert ENVELOPE["outputs"]  # a package that produced nothing is not delivered


def test_scope_is_report_5716_only():
    text = REPORT_MD + README_MD + json.dumps(REVIEW, ensure_ascii=False)
    assert REVIEW["reviewed_report_id"] == "5716"
    assert ENVELOPE["report_id"] == "5716"
    # no other report id is reviewed or written by this package
    assert not re.search(r"reviewed_report_id\"\s*:\s*\"(?!5716)", text)