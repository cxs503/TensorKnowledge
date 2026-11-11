"""Plane Poiseuille flow — analytical solution (Krüger ch.5).

Reference: Krüger et al. (2017), ch.5, ``chapter5/poiseuille_BB.m``.

The pressure-driven plane Poiseuille flow between two parallel plates has the
parabolic velocity profile::

    u(y) = 4 * u_max / H^2 * (y - y_bottom) * (y_top - y)

where ``H = y_top - y_bottom`` is the channel height and ``u_max`` is the
centre-line velocity.

The maximum velocity relates to the pressure gradient and kinematic viscosity as::

    u_max = gradP * H^2 / (8 * nu)

The BGK relaxation time that yields the exact solution (documented in the
source) is::

    tau = 0.5 + sqrt(3/16)  ≈ 0.9330127018922193

This is the "magic" tau for half-way bounce-back on a D2Q9 lattice.
"""

from __future__ import annotations

import math
from typing import Tuple

# The magic relaxation time documented in chapter5/poiseuille_BB.m:
#   tau = sqrt(3/16) + 0.5  (gives the exact solution)
TAU_EXACT = math.sqrt(3.0 / 16.0) + 0.5


def poiseuille_max_velocity(gradP: float, H: float, nu: float) -> float:
    """Compute the centre-line (maximum) velocity for plane Poiseuille flow.

    Parameters
    ----------
    gradP : float
        Pressure gradient (force per unit volume divided by density).
    H : float
        Channel height (y_top - y_bottom).
    nu : float
        Kinematic viscosity.

    Returns
    -------
    float
        Maximum velocity at the channel centre.

    Reference: Krüger ch.5, ``gradP = 8*nu*u_max/(ytop-ybottom)^2`` inverted.
    """
    return gradP * H ** 2 / (8.0 * nu)


def poiseuille_analytic(
    y: float,
    u_max: float,
    y_bottom: float = 0.0,
    y_top: float = 1.0,
) -> float:
    """Analytical velocity profile for plane Poiseuille flow.

    Parameters
    ----------
    y : float
        Wall-normal coordinate.
    u_max : float
        Centre-line velocity.
    y_bottom : float
        Bottom wall position (default 0).
    y_top : float
        Top wall position (default 1).

    Returns
    -------
    float
        Velocity u(y) at the given position.

    Reference: Krüger ch.5, ``u_analy = -4*u_max/(NY^2)*(y-ybottom)*(y-ytop)``.
    Note: the source uses NY as the channel height in lattice units.
    """
    H = y_top - y_bottom
    if H == 0:
        return 0.0
    return 4.0 * u_max / (H ** 2) * (y - y_bottom) * (y_top - y)


def poiseuille_profile(
    ny: int,
    u_max: float,
    y_bottom: float = 0.0,
    y_top: float = 1.0,
) -> Tuple[list[float], list[float]]:
    """Compute the full velocity profile on a uniform grid.

    Parameters
    ----------
    ny : int
        Number of grid points in the wall-normal direction.
    u_max : float
        Centre-line velocity.
    y_bottom : float
        Bottom wall position.
    y_top : float
        Top wall position.

    Returns
    -------
    tuple (y_vals, u_vals)
        Lists of wall-normal positions and corresponding velocities.
    """
    H = y_top - y_bottom
    y_vals = [y_bottom + i * H / (ny - 1) for i in range(ny)]
    u_vals = [poiseuille_analytic(y, u_max, y_bottom, y_top) for y in y_vals]
    return y_vals, u_vals
