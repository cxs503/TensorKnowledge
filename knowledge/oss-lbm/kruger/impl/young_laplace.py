"""Young-Laplace pressure — surface tension from droplet simulation (Krüger ch.9).

Reference: Krüger et al. (2017), ch.9, ``chapter9/shanchen.cpp``.

For a circular droplet in 2D, the Young-Laplace equation gives the pressure
jump across the interface::

    dp = gamma / r

where ``gamma`` is the surface tension and ``r`` is the droplet radius.

In the Shan-Chen pseudopotential model, the surface tension can be measured
from simulations at different radii.  If the model is consistent, ``gamma``
should be independent of ``r``.

The surface tension is computed as::

    gamma = dp * r

where ``dp = rho_liquid - rho_gas`` is the density difference (in lattice
units, this serves as the pressure difference proxy).
"""

from __future__ import annotations


def young_laplace_gamma(delta_p: float, radius: float) -> float:
    """Compute surface tension from pressure jump and radius.

    Parameters
    ----------
    delta_p : float
        Pressure (density) jump across the interface.
    radius : float
        Droplet radius.

    Returns
    -------
    float
        Surface tension gamma = delta_p * radius.

    Reference: Krüger ch.9, ``const double gamma = delta_press * rad;``.
    """
    return delta_p * radius


def young_laplace_pressure_jump(gamma: float, radius: float) -> float:
    """Compute the pressure jump from surface tension and radius.

    Parameters
    ----------
    gamma : float
        Surface tension.
    radius : float
        Droplet radius.

    Returns
    -------
    float
        Pressure jump dp = gamma / radius.
    """
    if radius == 0:
        return float("inf")
    return gamma / radius


def young_laplace_consistency_check(
    gamma_r1: float, gamma_r2: float, threshold_pct: float = 3.0
) -> tuple[bool, float]:
    """Check if surface tension is consistent between two droplet radii.

    Parameters
    ----------
    gamma_r1 : float
        Surface tension measured at radius r1.
    gamma_r2 : float
        Surface tension measured at radius r2.
    threshold_pct : float
        Maximum acceptable relative difference in percent.

    Returns
    -------
    tuple (passed, rel_diff_pct)
        Whether the consistency check passed and the relative difference.

    Reference: Krüger ch.9 validation — gamma should be radius-independent.
    """
    avg = (gamma_r1 + gamma_r2) / 2.0
    if avg == 0:
        return True, 0.0
    rel_diff = abs(gamma_r1 - gamma_r2) / avg * 100.0
    return rel_diff < threshold_pct, rel_diff
