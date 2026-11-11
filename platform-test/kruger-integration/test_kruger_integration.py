"""Integration tests: Krüger knowledge package called from platform-test.

These tests verify that the Krüger OSS-LBM knowledge package can be consumed
by downstream components (TensorLBM, platform validators, etc.) through its
public entry point.

Mission: m8676 (FEAT-TK-OSS-LANDING) — L3 integration_callers requirement.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Direct path imports (oss-lbm has a hyphen, not a valid Python module name)
REPO_ROOT = Path(__file__).resolve().parents[2]
KRUGER_PKG = REPO_ROOT / "knowledge" / "oss-lbm" / "kruger"


def _load_module(name: str, path: Path):
    """Load a module from a file path."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load the kruger package modules
impl_pkg = _load_module("kruger_impl", KRUGER_PKG / "impl" / "__init__.py")
entry_mod = _load_module("kruger_entry", KRUGER_PKG / "entry.py")
benchmark_mod = _load_module("kruger_benchmark", KRUGER_PKG / "benchmark" / "__init__.py")

# Also load poiseuille directly for TAU_EXACT
poiseuille_mod = _load_module("kruger_poiseuille", KRUGER_PKG / "impl" / "poiseuille.py")

KrugerReference = entry_mod.KrugerReference
poiseuille_analytic = impl_pkg.poiseuille_analytic
TAU_EXACT = poiseuille_mod.TAU_EXACT
couette_analytic = impl_pkg.couette_analytic
taylor_green_decay_time = impl_pkg.taylor_green_decay_time
taylor_green_energy_ratio = impl_pkg.taylor_green_energy_ratio
young_laplace_gamma = impl_pkg.young_laplace_gamma
trt_omega_plus = impl_pkg.trt_omega_plus
trt_magic_lambda = impl_pkg.trt_magic_lambda

# Load trt directly for MAGIC_6
trt_mod = _load_module("kruger_trt", KRUGER_PKG / "impl" / "trt.py")
MAGIC_6 = trt_mod.MAGIC_6

run_all_benchmarks = benchmark_mod.run_all_benchmarks


class TestKrugerIntegration:
    """Integration tests for the Krüger knowledge package."""

    @pytest.fixture
    def ref(self):
        return KrugerReference()

    # --- Entry point integration ---

    def test_entry_point_loads(self, ref):
        """Entry point can be instantiated."""
        assert ref is not None
        assert ref.SOURCE_COMMIT == "6e2c592fdc3592c14dfd52f860fc1ceea930bcb0"

    def test_entry_point_returns_claims(self, ref):
        """Entry point returns the full claims list."""
        claims = ref.get_claims()
        assert len(claims) >= 8, f"Expected ≥8 claims, got {len(claims)}"
        # Check a known claim
        claim = ref.get_claim_by_id("tkc:oss-lbm:kruger-poiseuille-bb-tau")
        assert claim is not None
        assert "poiseuille" in claim["statement"].lower()

    def test_entry_point_returns_evidence(self, ref):
        """Entry point returns the full evidence list."""
        evidence = ref.get_evidence()
        assert len(evidence) >= 20, f"Expected ≥20 evidence, got {len(evidence)}"

    def test_entry_point_returns_validation_summary(self, ref):
        """Entry point returns the validation summary from run artifacts."""
        summary = ref.get_validation_summary()
        assert "taylor_green" in summary
        assert "young_laplace" in summary

    # --- Analytical solution integration ---

    def test_poiseuille_parabolic_profile(self):
        """Poiseuille profile is parabolic and zero at walls."""
        u_max = 0.01
        H = 10.0
        # At walls
        assert poiseuille_analytic(0.0, u_max, 0.0, H) == 0.0
        assert poiseuille_analytic(H, u_max, 0.0, H) == 0.0
        # At centre
        u_center = poiseuille_analytic(H / 2, u_max, 0.0, H)
        assert abs(u_center - u_max) < 1e-15

    def test_couette_linear_profile(self):
        """Couette profile is linear."""
        u_max = 0.01
        H = 10.0
        # At stationary wall
        assert couette_analytic(0.0, u_max, 0.0, H) == 0.0
        # At moving wall
        u_top = couette_analytic(H, u_max, 0.0, H)
        assert abs(u_top - u_max) < 1e-15
        # At mid-height
        u_mid = couette_analytic(H / 2, u_max, 0.0, H)
        assert abs(u_mid - u_max / 2) < 1e-15

    def test_taylor_green_decay(self):
        """Taylor-Green energy decays exponentially."""
        nu = 1.0 / 6.0
        td = taylor_green_decay_time(nu, 1.0, 1.0)
        # At t=0, energy ratio should be 1
        assert abs(taylor_green_energy_ratio(0.0, nu) - 1.0) < 1e-15
        # At t=td, energy ratio should be exp(-2) ≈ 0.135
        expected = 0.1353352832366127
        got = taylor_green_energy_ratio(td, nu)
        assert abs(got - expected) < 1e-10

    def test_young_laplace_gamma(self):
        """Young-Laplace surface tension calculation."""
        gamma = young_laplace_gamma(0.00127, 16.32)
        assert abs(gamma - 0.0207264) < 1e-6

    def test_trt_magic_consistency(self):
        """TRT magic parameter round-trip is consistent."""
        omega = 0.3
        omega_plus = trt_omega_plus(omega, MAGIC_6)
        magic_back = trt_magic_lambda(omega, omega_plus)
        assert abs(magic_back - MAGIC_6) < 1e-15

    # --- Benchmark integration ---

    def test_benchmarks_run(self):
        """All benchmarks execute and return results."""
        results = run_all_benchmarks()
        assert "benchmarks" in results
        assert "summary" in results
        assert results["summary"]["total"] >= 5

    def test_benchmark_poiseuille_exact(self):
        """Poiseuille with magic tau passes (machine precision)."""
        results = run_all_benchmarks()
        bm = results["benchmarks"]["poiseuille_bb_exact"]
        assert bm["passed"], f"Poiseuille exactness failed: L2={bm['got_l2']}"

    def test_benchmark_couette_exact(self):
        """Couette with bounce-back passes (machine precision)."""
        results = run_all_benchmarks()
        bm = results["benchmarks"]["couette_bb"]
        assert bm["passed"], f"Couette exactness failed: L2={bm['got_l2']}"

    def test_benchmark_tg_convergence(self):
        """Taylor-Green shows second-order convergence."""
        results = run_all_benchmarks()
        bm = results["benchmarks"]["taylor_green_convergence"]
        assert bm["passed"], f"TG convergence failed: orders={bm.get('got_orders')}"

    def test_benchmark_young_laplace(self):
        """Young-Laplace gamma is consistent between radii."""
        results = run_all_benchmarks()
        bm = results["benchmarks"]["young_laplace_consistency"]
        assert bm["passed"], f"YL consistency failed: rel_diff={bm['got_rel_diff_pct']:.2f}%"

    def test_benchmark_ib_lbm_known_failure(self):
        """IBM-LBM Poiseuille has known ~6.5% deviation (honest negative)."""
        results = run_all_benchmarks()
        bm = results["benchmarks"]["ib_lbm_poiseuille"]
        # This is expected to fail the 3% threshold
        assert not bm["passed"], "IBM-LBM should fail 3% threshold (known ~6.5% deviation)"
        assert abs(bm["rel_error_pct"]) < 10, "Deviation should be ~6.5%, not catastrophic"

    # --- Claims-to-implementation linkage ---

    def test_claim_tau_exact_matches_impl(self, ref):
        """The tau exact claim matches the implementation constant."""
        claim = ref.get_claim_by_id("tkc:oss-lbm:kruger-poiseuille-bb-tau")
        assert claim is not None
        # The claim mentions tau = sqrt(3/16) + 0.5
        assert "sqrt(3/16)" in claim["statement"] or "0.933" in claim["statement"]
        assert abs(TAU_EXACT - 0.9330127018922193) < 1e-15
