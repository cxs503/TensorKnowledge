"""Plane Couette flow — analytical solution (Krüger ch.5).

Reference: Krüger et al. (2017), ch.5, ``chapter5/couette_BB.m``.

The plane Couette flow between a stationary bottom wall and a top wall moving
with tangential velocity ``u_max`` has the linear velocity profile::

    u(y) = u_max * y / H

where ``H`` is the channel height.

This is the simplest shear-driven flow and serves as a baseline for validating
bounce-back boundary conditions with moving walls.
"""

from __future__ import annotations


def couette_analytic(
    y: float,
    u_max: float,
    y_bottom: float = 0.0,
    y_top: float = 1.0,
) -> float:
    """Analytical velocity profile for plane Couette flow.

    Parameters
    ----------
    y : float
        Wall-normal coordinate.
    u_max : float
        Top wall tangential velocity.
    y_bottom : float
        Bottom wall position (default 0, stationary).
    y_top : float
        Top wall position (default 1, moving at u_max).

    Returns
    -------
    float
        Velocity u(y) at the given position.

    Reference: Krüger ch.5, ``u_analy = u_max/NY * y``.
    """
    H = y_top - y_bottom
    if H == 0:
        return 0.0
    return u_max * (y - y_bottom) / H


def couette_profile(
    ny: int,
    u_max: float,
    y_bottom: float = 0.0,
    y_top: float = 1.0,
) -> tuple[list[float], list[float]]:
    """Compute the full velocity profile on a uniform grid.

    Parameters
    ----------
    ny : int
        Number of grid points in the wall-normal direction.
    u_max : float
        Top wall tangential velocity.
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
    u_vals = [couette_analytic(y, u_max, y_bottom, y_top) for y in y_vals]
    return y_vals, u_vals
