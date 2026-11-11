"""Kruger textbook reference implementations — analytical solutions and reference values.

This module provides the *executable* form of the knowledge claims in
``knowledge/oss-lbm/kruger/claims/claims.json``.  Each function implements a
reference solution from Krüger et al. (2017), *The Lattice Boltzmann Method:
Principles and Practice*, Springer.

Source: lbm-principles-practice/code@6e2c592fdc3592c14dfd52f860fc1ceea930bcb0
Mission: m8676 (FEAT-TK-OSS-LANDING)
"""

# Support both package import and direct file load
try:
    from .poiseuille import poiseuille_analytic, poiseuille_max_velocity
    from .couette import couette_analytic
    from .taylor_green import (
        taylor_green_analytic_velocity,
        taylor_green_decay_time,
        taylor_green_energy_ratio,
    )
    from .young_laplace import young_laplace_gamma, young_laplace_pressure_jump
    from .trt import trt_omega_plus, trt_magic_lambda
except ImportError:
    import sys
    from pathlib import Path
    _pkg = Path(__file__).resolve().parent
    sys.path.insert(0, str(_pkg))
    from poiseuille import poiseuille_analytic, poiseuille_max_velocity
    from couette import couette_analytic
    from taylor_green import (
        taylor_green_analytic_velocity,
        taylor_green_decay_time,
        taylor_green_energy_ratio,
    )
    from young_laplace import young_laplace_gamma, young_laplace_pressure_jump
    from trt import trt_omega_plus, trt_magic_lambda

__all__ = [
    "poiseuille_analytic",
    "poiseuille_max_velocity",
    "couette_analytic",
    "taylor_green_analytic_velocity",
    "taylor_green_decay_time",
    "taylor_green_energy_ratio",
    "young_laplace_gamma",
    "young_laplace_pressure_jump",
    "trt_omega_plus",
    "trt_magic_lambda",
]
