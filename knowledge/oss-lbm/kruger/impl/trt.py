"""TRT (Two-Relaxation-Time) magic parameter (Krüger ch.8).

Reference: Krüger et al. (2017), ch.8, ``chapter8/gaussian_1d_magic6.cpp``,
``chapter8/gaussian_1d_magic12.cpp``, ``chapter8/cylinder.cpp``.

The TRT collision operator uses two relaxation rates:
- omega (ω) for the symmetric (even) moments
- omega_plus (ω⁺) for the anti-symmetric (odd) moments

The "magic" parameter Λ relates them::

    Λ = (1/ω - 0.5) * (1/ω⁺ - 0.5)

Given Λ and ω, the complementary relaxation rate is::

    ω⁺ = 1 / (Λ / (1/ω - 0.5) + 0.5)

Common magic values:
- Λ = 1/6: optimal for diffusion-type problems (Gaussian pulse)
- Λ = 1/12: alternative tuning
- Λ = 1/4: used for cylinder cross-flow (Kármán vortex street)

Reference: Krüger ch.8, ``omega_plus_phase = 1.0/(magic/(1.0/omega-0.5)+0.5)``.
"""

from __future__ import annotations

# Standard magic parameter values from Krüger ch.8
MAGIC_6 = 1.0 / 6.0    # Gaussian pulse, diffusion-optimal
MAGIC_12 = 1.0 / 12.0  # Alternative tuning
MAGIC_4 = 1.0 / 4.0    # Cylinder cross-flow


def trt_omega_plus(omega: float, magic: float) -> float:
    """Compute the complementary TRT relaxation rate.

    Parameters
    ----------
    omega : float
        Primary relaxation rate (for symmetric moments).
    magic : float
        Magic parameter Λ.

    Returns
    -------
    float
        Complementary relaxation rate ω⁺.

    Reference: Krüger ch.8,
    ``omega_plus_phase = 1.0/(magic/(1.0/omega-0.5)+0.5)``.
    """
    tau_minus_05 = 1.0 / omega - 0.5
    if tau_minus_05 == 0:
        # omega = 2, singular case
        return 2.0
    return 1.0 / (magic / tau_minus_05 + 0.5)


def trt_magic_lambda(omega: float, omega_plus: float) -> float:
    """Compute the magic parameter Λ from two relaxation rates.

    Parameters
    ----------
    omega : float
        Primary relaxation rate.
    omega_plus : float
        Complementary relaxation rate.

    Returns
    -------
    float
        Magic parameter Λ = (1/ω - 0.5) * (1/ω⁺ - 0.5).
    """
    return (1.0 / omega - 0.5) * (1.0 / omega_plus - 0.5)


def trt_cylinder_params(re_target: float = 100.0) -> dict:
    """TRT parameters for the cylinder cross-flow case (Krüger ch.8).

    The cylinder case uses Λ = 1/4 with specific omega values.

    Parameters
    ----------
    re_target : float
        Target Reynolds number (informational; the actual Re is set by
        the lattice parameters).

    Returns
    -------
    dict
        Dictionary with omega, omega_plus, omega_minus, and magic values.

    Reference: Krüger ch.8, ``chapter8/cylinder.cpp``:
    ``omega = 1.0/(0.5+0.5/32.0)``, ``omega_plus = 2.0 - omega``.
    """
    omega = 1.0 / (0.5 + 0.5 / 32.0)  # ≈ 1.939
    omega_plus = 2.0 - omega
    omega_minus = omega
    magic = trt_magic_lambda(omega, omega_plus)
    return {
        "omega": omega,
        "omega_plus": omega_plus,
        "omega_minus": omega_minus,
        "magic": magic,
        "re_target": re_target,
    }
