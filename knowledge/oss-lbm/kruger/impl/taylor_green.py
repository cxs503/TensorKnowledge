"""Taylor-Green vortex decay — analytical solution (Krüger ch.13).

Reference: Krüger et al. (2017), ch.13, ``chapter13/python3/vortexdecay.py``.

The 2D Taylor-Green vortex is an exact solution of the incompressible Navier-Stokes
equations that decays exponentially in time.  The velocity field is::

    u_x(x,y,t) = -u_max * sqrt(ky/kx) * cos(kx*x) * sin(ky*y) * exp(-t/t_d)
    u_y(x,y,t) =  u_max * sqrt(kx/ky) * sin(kx*x) * cos(ky*y) * exp(-t/t_d)

where the decay time is::

    t_d = 1 / (nu * (kx^2 + ky^2))

The kinetic energy ratio decays as::

    E(t) / E(0) = exp(-2 * t / t_d)

This case is used to verify second-order convergence of LBM schemes.
"""

from __future__ import annotations

import math


def taylor_green_decay_time(nu: float, kx: float, ky: float) -> float:
    """Compute the Taylor-Green decay time.

    Parameters
    ----------
    nu : float
        Kinematic viscosity.
    kx : float
        Wavenumber in x.
    ky : float
        Wavenumber in y.

    Returns
    -------
    float
        Decay time t_d = 1 / (nu * (kx^2 + ky^2)).

    Reference: Krüger ch.13, ``td = 1/(nu*(kx*kx+ky*ky))``.
    """
    return 1.0 / (nu * (kx ** 2 + ky ** 2))


def taylor_green_analytic_velocity(
    x: float,
    y: float,
    t: float,
    u_max: float,
    nu: float,
    kx: float = 1.0,
    ky: float = 1.0,
) -> tuple[float, float]:
    """Analytical velocity field for the 2D Taylor-Green vortex.

    Parameters
    ----------
    x, y : float
        Spatial coordinates.
    t : float
        Time.
    u_max : float
        Initial velocity amplitude.
    nu : float
        Kinematic viscosity.
    kx, ky : float
        Wavenumbers (default 1.0 each for the standard case).

    Returns
    -------
    tuple (ux, uy)
        Velocity components at (x, y, t).

    Reference: Krüger ch.13, ``vortexdecay.py`` lines 55-58.
    """
    td = taylor_green_decay_time(nu, kx, ky)
    decay = math.exp(-t / td)
    sqrt_ratio = math.sqrt(ky / kx)
    ux = -u_max * sqrt_ratio * math.cos(kx * x) * math.sin(ky * y) * decay
    uy = u_max * math.sqrt(kx / ky) * math.sin(kx * x) * math.cos(ky * y) * decay
    return ux, uy


def taylor_green_energy_ratio(t: float, nu: float, kx: float = 1.0, ky: float = 1.0) -> float:
    """Analytical kinetic energy ratio E(t)/E(0).

    Parameters
    ----------
    t : float
        Time.
    nu : float
        Kinematic viscosity.
    kx, ky : float
        Wavenumbers.

    Returns
    -------
    float
        E(t)/E(0) = exp(-2*t/t_d).

    Reference: Krüger ch.13, analytic energy decay.
    """
    td = taylor_green_decay_time(nu, kx, ky)
    return math.exp(-2.0 * t / td)
