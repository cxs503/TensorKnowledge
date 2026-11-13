"""Tests for the wp-611-04 independent review (report 611, KF production line, lane C).

These assert the *invariants of the review* rather than merely executing it:
  * the KF envelope / ledger / quote-locator gate passes (verify_deliverables)
  * GM = BM - BG vanishes identically for a homogeneous sphere (the finding F1 basis)
  * the reported GM = -0.115 is therefore refuted, not just "not reproduced"
  * the producer's buoyancy error (2.19e-16) is not attainable by any independent reference
  * the numbers that do reproduce reproduce to the stated tolerance (so the review is not
    a blanket rejection)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(HERE, "..", "docs", "reviews", "wp-611-04")
sys.path.insert(0, os.path.abspath(REVIEW))

import independent_check_611 as ic  # noqa: E402

SOURCE_HASH = "sha256:72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88"


@pytest.fixture(scope="module")
def results():
    return json.load(open(os.path.join(REVIEW, "independent_check_results.json"), encoding="utf-8"))


def test_source_hash_is_the_reviewed_one():
    md = open(os.path.join(REVIEW, "_source_611.md"), encoding="utf-8").read()
    assert "sha256:" + hashlib.sha256(md.encode()).hexdigest() == SOURCE_HASH
    assert len(md) == 1974          # chars=1974 in the contract


def test_gm_identity_is_exact_for_a_homogeneous_sphere():
    proof = ic.gm_identity_proof()
    assert proof["symbolic_ok"] is True
    assert proof["BM_minus_BG"] == "0"


def test_reported_gm_is_refuted_not_merely_imprecise(results):
    st = results["stability"]
    assert abs(st["3d"]["GM"]) < 1e-9                  # exact identity -> 0
    assert abs(st["3d"]["GM"] - (-0.115)) > 0.1        # the report's value is 0.115 m away
    # and no draught reproduces a negative GM
    assert st["GM_max_abs_over_draught_grid_3d"] < 1e-9
    assert st["GM_max_abs_over_draught_grid_2d"] < 1e-8


def test_reported_gm_matches_no_standard_variant(results):
    hyp = results["stability"]["GM_hypotheses_3d"]
    assert abs(hyp["reported_by_producer"] - (-0.115)) == 0.0
    for name, value in hyp.items():
        if name in ("reported_by_producer", "nearest_standard_variant_gap"):
            continue
        assert abs(value - (-0.115)) > 5e-3, f"{name} unexpectedly reproduces -0.115"


def test_buoyancy_error_is_machine_epsilon_hence_not_discriminative(results):
    ref = results["buoyancy"]["independent_reference_rel_errors"]
    assert ref["closed_form_same_expression"]["rel_err_3d"] == 0.0      # tautology
    assert min(ref["quadrature_n50000"]["rel_err_2d"],
               ref["quadrature_n50000"]["rel_err_3d"]) > 1e-11           # independent floor
    assert ref["monte_carlo_3d"]["rel_err_3d"] > 1e-4


def test_geometry_and_heave_do_reproduce(results):
    g, st = results["geometry_and_equilibrium"], results["stability"]
    assert abs(abs(g["h_eq_2d"]) - 0.3378) / 0.3378 < 2e-4
    assert abs(abs(g["h_eq_3d"]) - 0.2986) / 0.2986 < 2e-4
    assert st["k_heave_rel_diff_2d"] < 1e-4
    assert st["k_heave_rel_diff_3d"] < 1e-4


def test_equilibrium_force_balance_closes(results):
    b = results["buoyancy"]
    assert b["equilibrium_residual_2d"] < 1e-12
    assert b["equilibrium_residual_3d"] < 1e-12


def test_wave_pair_is_inconsistent(results):
    w = results["wave_consistency"]
    assert abs(w["lambda_from_T_deepwater"] - 10.0) / 10.0 > 0.02      # 9.758 m, not 10 m
    assert w["D_over_lambda_from_T"] > 0.1                              # outside its own validity bound


def test_deliverable_gate_passes():
    import verify_deliverables

    assert verify_deliverables.main() == 0