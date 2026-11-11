#!/usr/bin/env python3
"""pytest suite for the Kruger (OSS-LBM A-line) knowledge package.

The suite is deliberately split into two tiers:

* offline tier (always runs) — schema/identifier/cross-reference/GAP-anchor discipline,
  and verbatim re-checking of every quotation against the committed source index
  (artifacts/oss-lbm-kruger/kruger_source_index.json);
* live tier (runs when an upstream checkout is available via KRUGER_REPO, else skips) —
  re-slices every anchor from the real files and requires byte equality with the stored
  quotes, and requires the builder to be deterministic.

Run from anywhere:  pytest -q knowledge/oss-lbm/kruger/tests
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
ROOT = PKG.parents[2]
CLAIMS = json.loads((PKG / "claims" / "claims.json").read_text(encoding="utf-8"))
EVIDENCE = json.loads((PKG / "evidence" / "evidence.json").read_text(encoding="utf-8"))
PROVENANCE = json.loads((PKG / "provenance" / "provenance.json").read_text(encoding="utf-8"))
INDEX = json.loads((ROOT / "artifacts" / "oss-lbm-kruger" / "kruger_source_index.json").read_text(encoding="utf-8"))

sys.path.insert(0, str(PKG))
import validate_kruger  # noqa: E402  (local module)


# --------------------------------------------------------------------------- offline
def test_validator_passes():
    assert validate_kruger.main([]) == 0


def test_minimum_claim_count():
    assert len(CLAIMS) >= 8


def test_claim_ids_unique_and_prefixed():
    ids = [c["id"] for c in CLAIMS]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("tkc:oss-lbm:kruger-") for i in ids)


def test_bidirectional_cross_references():
    ev = {e["id"]: e for e in EVIDENCE}
    for c in CLAIMS:
        assert c["evidence_refs"], c["id"]
        for ref in c["evidence_refs"]:
            assert ref in ev, f"{c['id']} -> {ref}"
            assert c["id"] in ev[ref]["claim_refs"]
    for e in EVIDENCE:
        assert e["claim_refs"], e["id"]
        for ref in e["claim_refs"]:
            owner = next(c for c in CLAIMS if c["id"] == ref)
            assert e["id"] in owner["evidence_refs"]


def test_quotes_are_verbatim_against_source_index():
    files = INDEX["files"]
    checked = 0
    for e in EVIDENCE:
        loc = e["locator"]
        if loc["locator_type"] != "code-location":
            continue
        repo, commit, path, rng = loc["value"].split(" ", 1)[0], None, None, None
        value = loc["value"]
        spec = value.split(" ", 1)[1]
        path, rng = spec.rsplit(":", 1)
        l0, l1 = (int(x) for x in rng.split("-"))
        span = next((s for s in files[path]["quoted_spans"]
                     if s["line_start"] == l0 and s["line_end"] == l1), None)
        assert span is not None, f"{e['id']} span {path}:{l0}-{l1} missing from index"
        assert span["quote"] == loc["quote"], f"{e['id']} quote drifted from upstream span"
        assert len(loc["quote"].splitlines()) <= 3
        checked += 1
    assert checked >= 20, "expected at least 20 code-location quotes"


def test_epistemic_discipline_is_draft_only():
    assert all(e["assessment_status"] == "unassessed" for e in EVIDENCE)
    assert not (PKG / "review-events").exists()
    statuses = {c["epistemic_status"] for c in CLAIMS}
    assert statuses <= {"established", "well-supported", "provisional", "contested",
                        "speculative", "superseded", "not-assessed"}
    # every non-established claim must say why it is held back
    for c in CLAIMS:
        if c["epistemic_status"] in {"provisional", "contested", "speculative"}:
            joined = " ".join(c["notes"])
            assert ("保守定级理由" in joined) or ("诚实的负面结果" in joined) or ("GAP" in joined), c["id"]


def test_every_claim_has_gap_anchor():
    registry = (PKG / "GAP-ANCHORS.md").read_text(encoding="utf-8")
    assert "GAP-LBM-BENCH-METHODOLOGY" in registry
    for c in CLAIMS:
        joined = " ".join(c["notes"])
        assert "GAP-LBM-BENCH-METHODOLOGY" in joined, c["id"]


def test_provenance_pins_commit_and_cache_status():
    prov = PROVENANCE[0]
    assert prov["generated_entity"]["id"] == "knowledge/oss-lbm/kruger"
    assert INDEX["commit"] in " ".join(prov["activity"]["used_entities"])
    assert INDEX["commit_short"] == INDEX["commit"][:7]
    ext = prov["extensions"]
    assert "GAP-LBM-BENCH-METHODOLOGY" in ext["gap_anchors"]
    assert "insufficient" in ext["source_cache_status"]  # cache miss must be recorded, not hidden
    # provenance record must state that the quotes are machine-sliced, not transcribed
    assert "machine-sliced" in prov["activity"]["description"]


def test_run_evidence_matches_run_artifacts():
    summary_path = ROOT / "runs" / "oss-lbm-kruger-8676" / "validation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    tg = summary["taylor_green"]["runs"]
    l2 = [c["L2_ux"] for c in tg]
    assert l2 == sorted(l2, reverse=True), "Taylor-Green L2 must decrease with resolution"
    orders = [c["observed_order"] for c in tg if "observed_order" in c]
    assert orders and all(1.8 <= o <= 2.2 for o in orders), f"second order expected, got {orders}"
    yl = summary["young_laplace"]
    assert yl["gamma_rel_diff_pct"] < 15
    assert summary["ib_lbm_poiseuille"]["centreline_error_pct"] < 0  # below the analytic value
    # the quotes embedded in the run evidence must be reproducible from the summary
    ev = {e["id"]: e for e in EVIDENCE}
    for c in tg:
        assert f"NX={c['NX']} L2(ux)={c['L2_ux']:.3e}" in ev["tke:oss-lbm:kruger-run-taylor-green"]["locator"]["quote"]


# ------------------------------------------------------------------------------ live
def _repo() -> Path | None:
    for cand in [os.environ.get("KRUGER_REPO"), "/root/oss-cache/lbm-principles-practice-code",
                 "/root/oss-cache/code"]:
        if not cand:
            continue
        try:
            if Path(cand, "chapter5").is_dir():
                return Path(cand)
        except OSError:
            # unreadable parent (e.g. hosted runners cannot traverse /root):
            # treat as absent so the live tier skips instead of erroring out
            continue
    return None


@pytest.mark.skipif(_repo() is None, reason="no upstream checkout (set KRUGER_REPO=...)")
def test_quotes_match_live_checkout():
    import build_claims
    repo = _repo()
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    assert commit == INDEX["commit"], "checkout commit differs from the pinned commit"
    pkg = build_claims.build(repo, commit, verify_only=True)
    assert pkg["claims"] == CLAIMS, "claims.json is stale; re-run build_claims.py"
    assert pkg["evidence"] == EVIDENCE, "evidence.json is stale; re-run build_claims.py"
    assert pkg["provenance"] == PROVENANCE, "provenance.json is stale; re-run build_claims.py"


@pytest.mark.skipif(_repo() is None, reason="no upstream checkout (set KRUGER_REPO=...)")
def test_builder_anchor_uniqueness_live():
    """Each anchor must match exactly one line, otherwise the quote would be ambiguous."""
    import build_claims
    repo = _repo()
    for _eid, rel, anchor, _n, _rel in build_claims.EVIDENCE_SPECS:
        text = (repo / rel).read_text(encoding="utf-8", errors="replace")
        assert text.count(anchor) >= 1, f"{rel}: anchor {anchor!r} not found"
        assert sum(1 for ln in text.splitlines() if anchor in ln) == 1, \
            f"{rel}: anchor {anchor!r} is ambiguous"