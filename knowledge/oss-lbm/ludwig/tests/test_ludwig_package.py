"""pytest suite for the Ludwig OSS-LBM knowledge package (m8669).

Run from this directory:   pytest tests/ -q
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1]
CLAIMS = json.loads((PKG / "claims" / "claims.json").read_text(encoding="utf-8"))
EVIDENCE = json.loads((PKG / "evidence" / "evidence.json").read_text(encoding="utf-8"))
PROVENANCE = json.loads((PKG / "provenance" / "provenance.json").read_text(encoding="utf-8"))
GAPS = json.loads((PKG / "gaps" / "gap-anchors.json").read_text(encoding="utf-8"))


def test_validator_exit_zero():
    """The package validator must be green (it is the in-repo checker)."""
    out = subprocess.run([sys.executable, str(PKG / "validate_ludwig.py")],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "PASS" in out.stdout


def test_claim_floor_and_source_is_ludwig():
    assert len(CLAIMS) >= 8, "mission floor is 8 claims"
    for ev in EVIDENCE:
        assert ev["source"]["repo"] == "ludwig-cf/ludwig"
        assert re.fullmatch(r"[0-9a-f]{40}", ev["source"]["commit"])


def test_every_claim_has_gap_anchor_and_service_note():
    gap_ids = {g["id"] for g in GAPS}
    assert "GAP-LBM-MCMP-POISEUILLE" in gap_ids
    for c in CLAIMS:
        assert c["gap_anchor"] in gap_ids, c["id"]
        assert c["notes"], c["id"]
    # every anchor is reachable from at least one claim
    used = {c["gap_anchor"] for c in CLAIMS}
    assert used == gap_ids, gap_ids - used


def test_quotes_are_short_and_bounded():
    for ev in EVIDENCE:
        loc = ev["locator"]
        if loc["locator_type"] == "code-location":
            q = loc["quote"]
            assert q.strip()
            assert q.count("\n") + 1 <= 3, ev["id"]
            assert loc["line_end"] - loc["line_start"] + 1 == q.count("\n") + 1
        else:
            assert loc["locator_type"] == "code-search"
            assert loc["hits"] == 0, "absence evidence must record zero hits"


def test_absence_claims_are_supported_by_search_evidence():
    absence = [c for c in CLAIMS if c["claim_type"] == "negative"]
    assert absence, "expected at least one negative claim"
    for c in absence:
        refs = [e for e in EVIDENCE if e["id"] in c["evidence_refs"]]
        assert any(e["locator"]["locator_type"] == "code-search" for e in refs), c["id"]
        # the quote-free search evidence still needs a reproducible query
        for e in refs:
            if e["locator"]["locator_type"] == "code-search":
                assert e["locator"]["query"].startswith("grep")


def test_contested_status_is_used_for_interpretive_accuracy_claims():
    contested = {c["id"] for c in CLAIMS if c["epistemic_status"] == "contested"}
    # these four are about discretisation-order consequences, not code facts
    expected = {
        "tkc:oss-lbm:ludwig-ch-flux-first-order-mu",
        "tkc:oss-lbm:ludwig-symm-mu-discrete",
        "tkc:oss-lbm:ludwig-spinodal-smoke-test",
        "tkc:oss-lbm:ludwig-unit-test-ch-scope",
    }
    assert expected <= contested


def test_no_self_approval():
    for ev in EVIDENCE:
        assert ev["assessment_status"] == "unassessed"
        assert "review_events" not in ev or not ev["review_events"]
    for prov in PROVENANCE:
        for key in ("id", "generated_entity", "activity", "agents", "recorded_at", "version"):
            assert key in prov


def test_verification_artifact_is_quantitative_and_honest():
    art = json.loads((PKG / "artifacts" / "shear_wave_verification.json").read_text(encoding="utf-8"))
    by_L = {c["L"]: c for c in art["cases"]}
    assert set(by_L) == {8, 16, 32}
    # converged cases inside the 3% acceptance band
    assert abs(by_L[16]["decay_rate_rel_error"]) < 0.03
    assert abs(by_L[32]["decay_rate_rel_error"]) < 0.03
    # the coarse case is deliberately reported as outside the band (honest FAIL, not hidden)
    assert abs(by_L[8]["decay_rate_rel_error"]) > 0.03
    assert art["summary"]["passes"] is False
    # monotone convergence with resolution
    e = [abs(by_L[L]["decay_rate_rel_error"]) for L in (8, 16, 32)]
    assert e[0] > e[1] > e[2]
    # exact solution is stated and the exponent matches nu k^2
    for c in art["cases"]:
        assert c["decay_rate_exact"] == pytest.approx(c["viscosity_input"] * c["k"] ** 2, rel=1e-12)
        assert c["fit_r2"] > 0.999


def test_figure_exists():
    png = PKG / "artifacts" / "shear_wave_decay.png"
    assert png.is_file() and png.stat().st_size > 10_000


@pytest.mark.skipif(not os.environ.get("LUDWIG_SRC"), reason="needs a local Ludwig checkout")
def test_committed_quotes_match_source_tree():
    """Re-slice every quote from the real sources and compare byte-for-byte."""
    src = Path(os.environ["LUDWIG_SRC"])
    out = subprocess.run(
        [sys.executable, str(PKG / "scripts" / "build_package.py"), "--check"],
        capture_output=True, text=True, env={**os.environ, "LUDWIG_SRC": str(src)},
    )
    assert out.returncode == 0, out.stdout + out.stderr