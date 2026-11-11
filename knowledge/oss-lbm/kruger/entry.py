"""Entry point for the Kruger OSS-LBM knowledge package.

This module provides the public API for consuming the Krüger textbook
reference implementations and claims from TensorLBM or other downstream
consumers.

Usage::

    from knowledge.oss_lbm.kruger.entry import KrugerReference

    ref = KrugerReference()
    u = ref.poiseuille(y=0.5, u_max=0.01, H=1.0)
    gamma = ref.young_laplace_gamma(delta_p=0.00127, radius=16.32)

Mission: m8676 (FEAT-TK-OSS-LANDING)
Source: lbm-principles-practice/code@6e2c592
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Support both package import (knowledge.oss_lbm.kruger.entry) and direct file load
try:
    from .impl.poiseuille import poiseuille_analytic, poiseuille_max_velocity, TAU_EXACT
    from .impl.couette import couette_analytic
    from .impl.taylor_green import (
        taylor_green_analytic_velocity,
        taylor_green_decay_time,
        taylor_green_energy_ratio,
    )
    from .impl.young_laplace import (
        young_laplace_gamma,
        young_laplace_pressure_jump,
        young_laplace_consistency_check,
    )
    from .impl.trt import trt_omega_plus, trt_magic_lambda, trt_cylinder_params
except ImportError:
    # Fallback for direct file loading (e.g., via importlib.util)
    import sys
    _pkg = Path(__file__).resolve().parent
    sys.path.insert(0, str(_pkg))
    from impl.poiseuille import poiseuille_analytic, poiseuille_max_velocity, TAU_EXACT
    from impl.couette import couette_analytic
    from impl.taylor_green import (
        taylor_green_analytic_velocity,
        taylor_green_decay_time,
        taylor_green_energy_ratio,
    )
    from impl.young_laplace import (
        young_laplace_gamma,
        young_laplace_pressure_jump,
        young_laplace_consistency_check,
    )
    from impl.trt import trt_omega_plus, trt_magic_lambda, trt_cylinder_params

HERE = Path(__file__).resolve().parent
CLAIMS_PATH = HERE / "claims" / "claims.json"
EVIDENCE_PATH = HERE / "evidence" / "evidence.json"
RUNS_SUMMARY = HERE.parents[2] / "runs" / "oss-lbm-kruger-8676" / "validation_summary.json"


class KrugerReference:
    """Unified entry point for Krüger textbook reference solutions.

    Provides analytical solutions and reference values from
    *The Lattice Boltzmann Method: Principles and Practice* (Krüger et al., 2017).
    """

    SOURCE_COMMIT = "6e2c592fdc3592c14dfd52f860fc1ceea930bcb0"
    SOURCE_REPO = "lbm-principles-practice/code"

    # --- Poiseuille ---

    @staticmethod
    def poiseuille_velocity(y: float, u_max: float, y_bottom: float = 0.0, y_top: float = 1.0) -> float:
        """Plane Poiseuille velocity profile u(y)."""
        return poiseuille_analytic(y, u_max, y_bottom, y_top)

    @staticmethod
    def poiseuille_max_velocity(gradP: float, H: float, nu: float) -> float:
        """Centre-line velocity from pressure gradient."""
        return poiseuille_max_velocity(gradP, H, nu)

    @staticmethod
    def poiseuille_tau_exact() -> float:
        """Magic BGK relaxation time for exact Poiseuille solution."""
        return TAU_EXACT

    # --- Couette ---

    @staticmethod
    def couette_velocity(y: float, u_max: float, y_bottom: float = 0.0, y_top: float = 1.0) -> float:
        """Plane Couette velocity profile u(y)."""
        return couette_analytic(y, u_max, y_bottom, y_top)

    # --- Taylor-Green ---

    @staticmethod
    def taylor_green_velocity(x: float, y: float, t: float, u_max: float, nu: float) -> tuple[float, float]:
        """2D Taylor-Green vortex velocity field."""
        return taylor_green_analytic_velocity(x, y, t, u_max, nu)

    @staticmethod
    def taylor_green_decay_time(nu: float) -> float:
        """Decay time for standard TG vortex (kx=ky=1)."""
        return taylor_green_decay_time(nu, 1.0, 1.0)

    @staticmethod
    def taylor_green_energy_ratio(t: float, nu: float) -> float:
        """E(t)/E(0) for standard TG vortex."""
        return taylor_green_energy_ratio(t, nu)

    # --- Young-Laplace ---

    @staticmethod
    def young_laplace_gamma(delta_p: float, radius: float) -> float:
        """Surface tension from pressure jump and radius."""
        return young_laplace_gamma(delta_p, radius)

    @staticmethod
    def young_laplace_pressure_jump(gamma: float, radius: float) -> float:
        """Pressure jump from surface tension and radius."""
        return young_laplace_pressure_jump(gamma, radius)

    @staticmethod
    def young_laplace_consistency(gamma_r1: float, gamma_r2: float, threshold_pct: float = 3.0) -> tuple[bool, float]:
        """Check surface tension consistency between two radii."""
        return young_laplace_consistency_check(gamma_r1, gamma_r2, threshold_pct)

    # --- TRT ---

    @staticmethod
    def trt_omega_plus(omega: float, magic: float) -> float:
        """Complementary TRT relaxation rate."""
        return trt_omega_plus(omega, magic)

    @staticmethod
    def trt_magic_lambda(omega: float, omega_plus: float) -> float:
        """Magic parameter from two relaxation rates."""
        return trt_magic_lambda(omega, omega_plus)

    @staticmethod
    def trt_cylinder_params() -> dict:
        """TRT parameters for cylinder cross-flow case."""
        return trt_cylinder_params()

    # --- Claims & Evidence ---

    def get_claims(self) -> list[dict[str, Any]]:
        """Return all claims from the knowledge package."""
        return json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))

    def get_evidence(self) -> list[dict[str, Any]]:
        """Return all evidence records from the knowledge package."""
        return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def get_validation_summary(self) -> dict[str, Any]:
        """Return the validation summary from run artifacts."""
        if RUNS_SUMMARY.exists():
            return json.loads(RUNS_SUMMARY.read_text(encoding="utf-8"))
        return {}

    def get_claim_by_id(self, claim_id: str) -> dict[str, Any] | None:
        """Look up a single claim by its ID."""
        for c in self.get_claims():
            if c["id"] == claim_id:
                return c
        return None
