#!/usr/bin/env python3
"""Pytest suite for the `knowledge/oss-lbm/fingering` package.

Three layers:

* structural/epistemic - the package validator (schema, cross-refs, GAP anchors,
  quote hygiene, no self-approval) plus optional verbatim re-extraction;
* claim verification - the two *established* mathematical claims are re-checked
  numerically/symbolically here, so "established" is backed by a validation
  surface and not by source reading alone;
* defect reproduction - the one-sided initial perturbation is reproduced with
  plain numpy (no repository code needed).

Run:  python3 -m pytest knowledge/oss-lbm/fingering -q
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import validate_oss_lbm_fingering as V  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. package integrity
# --------------------------------------------------------------------------- #
def test_package_passes_validator_with_snapshot():
    """Full validator run (verbatim re-extraction used when a snapshot is present)."""
    errors = V.validate()
    assert errors == [], "validator errors:\n" + "\n".join(errors)


def test_validator_main_reports_pass(capsys):
    assert V.main([]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out


def test_claim_volume_and_id_uniqueness():
    claims, evidence, provenance = V.load_package()
    assert len(claims) >= V.MIN_CLAIMS
    assert len(evidence) >= len(claims)
    assert len({c["id"] for c in claims}) == len(claims)
    assert provenance[0]["agents"][0]["id"] == "agent-m8691"
    # the snapshot commit must be traceable in provenance
    assert "150a5739e" in json.dumps(provenance)


def test_every_claim_is_gap_anchored():
    claims, _, _ = V.load_package()
    for c in claims:
        conditions = c["scope"]["conditions"]
        assert any(G.startswith("gap-anchor:") for G in conditions), c["id"]
        assert any(V.GAP_NAMED in G for G in conditions), c["id"]


def test_epistemic_status_is_conservative():
    """No self-approval and no 'established' pathology claim without runtime evidence."""
    claims, evidence, _ = V.load_package()
    for c in claims:
        assert c["epistemic_status"] in {
            "established", "well-supported", "provisional", "contested", "speculative",
        }, c["id"]
        assert c["epistemic_status"] != "not-assessed", c["id"]
        # epistemic_status is a claim-level field; nothing may be marked reviewed
        assert not any(k.startswith("review") for k in c), c["id"]
    for e in evidence:
        assert e["assessment_status"] == "unassessed", e["id"]
    established = {c["id"] for c in claims if c["epistemic_status"] == "established"}
    assert established == {
        "tkc:oss-lbm:fing-free-energy-calibration",
        "tkc:oss-lbm:fing-chemical-potential-sign-equivalence",
        "tkc:oss-lbm:fing-one-sided-initial-perturbation",
    }, "established set changed - add runtime evidence in this file before promoting a claim"


def test_quotes_are_verbatim_against_snapshot():
    snapshot = V.find_snapshot()
    if snapshot is None:
        pytest.skip("no Fingering_dynamics snapshot available (set FINGERING_SRC)")
    _, evidence, _ = V.load_package()
    checked = 0
    for e in evidence:
        m = V.LOCATOR.match(e["locator"]["value"])
        assert m, e["id"]
        path = snapshot / m["path"]
        assert path.is_file(), f"{e['id']}: {m['path']} missing"
        lines = path.read_text(encoding="utf-8").splitlines()
        first, last = int(m["start"]), int(m["end"])
        assert "\n".join(lines[first - 1:last]) == e["locator"]["quote"], e["id"]
        assert len(e["locator"]["quote"].splitlines()) <= 3, e["id"]
        assert e["locator"]["content_hash"] == hashlib.sha256(
            e["locator"]["quote"].encode()).hexdigest()
        checked += 1
    assert checked == len(evidence)


# --------------------------------------------------------------------------- #
# 2. verification of the two established mathematical claims
# --------------------------------------------------------------------------- #
def test_calibration_triple_reproduces_sigma():
    """Claim tkc:oss-lbm:fing-free-energy-calibration.

    With kappa = 0.75*xi*sigma and a = -2*kappa/xi^2 (fingering.py:40-42) the equilibrium
    interface psi = tanh(x/xi) must (i) be a zero of the chemical potential and (ii) carry the
    interfacial tension sigma in the free-energy sense sigma = ∫ kappa*(dpsi/dx)^2 dx.
    """
    import numpy as np

    sigma_declared = 0.045          # R_sigma, fingering.py:32 (any positive value scales linearly)
    xi = 2.0                        # fingering.py:40
    kappa = 0.75 * xi * sigma_declared
    a = -2.0 * kappa / (xi ** 2)

    # (i) chemical potential of the tanh profile vanishes identically
    x = np.linspace(-40 * xi, 40 * xi, 400001)
    psi = np.tanh(x / xi)
    d1 = (1.0 - psi ** 2) / xi
    d2 = -2.0 * psi * (1.0 - psi ** 2) / xi ** 2
    mu = a * psi * (1.0 - psi ** 2) - kappa * d2
    assert np.max(np.abs(mu)) < 1e-12

    # (ii) free-energy surface tension integral
    sigma_calc = np.trapezoid(kappa * d1 ** 2, x) if hasattr(np, "trapezoid") else np.trapz(kappa * d1 ** 2, x)
    rel_err = abs(sigma_calc - sigma_declared) / sigma_declared
    assert rel_err < 1e-4, f"sigma_calc={sigma_calc:.6f} vs declared {sigma_declared} ({rel_err:.2e})"

    # and the closed form sigma = 4*kappa/(3*xi) is what the code implies
    assert abs(4 * kappa / (3 * xi) - sigma_declared) < 1e-15


def test_chemical_potential_spellings_equivalent():
    """Claim tkc:oss-lbm:fing-chemical-potential-sign-equivalence (symbolic check)."""
    sympy = pytest.importorskip("sympy")
    psi, kappa, xi = sympy.symbols("psi kappa xi", positive=True)

    a_fing = -2 * kappa / xi ** 2          # fingering.py:42
    a_val = +2 * kappa / xi ** 2           # validation.py:36
    mu_fing = a_fing * psi * (1 - psi ** 2)   # fingering.py:149
    mu_val = a_val * psi * (psi ** 2 - 1)     # validation.py:118
    assert sympy.simplify(mu_fing - mu_val) == 0


# --------------------------------------------------------------------------- #
# 3. defect reproduction (no repository code required)
# --------------------------------------------------------------------------- #
def test_randint_seed_is_one_sided():
    """Claim tkc:oss-lbm:fing-one-sided-initial-perturbation (fingering.py:106-107)."""
    import numpy as np

    rng = np.random.default_rng(20261109)
    my_number = rng.integers(0, 1, size=(64, 64)) * 2 - 1.0   # same semantics as np.random.randint(0, 1)
    assert np.all(my_number == -1.0), "randint(0, 1) must be identically zero"
    delta = rng.random((64, 64)) * 0.001 * my_number
    assert delta.max() <= 0.0 and delta.min() >= -0.001
    assert delta.mean() < 0.0, "perturbation carries a non-zero mean -> one-sided compression"

    # the intended symmetric version
    symmetric = (rng.integers(0, 2, size=(64, 64)) * 2 - 1.0) * rng.random((64, 64)) * 0.001
    assert abs(symmetric.mean()) < 5e-5

    # legacy numpy API behaves the same way as the generator used above
    legacy = np.random.randint(0, 1, size=(8, 8))
    assert legacy.sum() == 0