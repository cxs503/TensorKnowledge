#!/usr/bin/env python3
"""Closed-form / re-derivation helpers for the sloshing-impact sediment package.

Everything here is **pure standard library** and deliberately independent of the
source implementation (``TensorLBM`` ``src/tensorlbm/sloshing_impact_calibration.py``):
the source is only ever read as a *record* (blob at a pinned sha), never imported.
That separation is what makes the numbers in the sediment package reproducible
without a torch/LBM environment.

Recipes are addressed by name from ``number_checks`` items, so the sediment
package carries a declarative plan while this module carries the executable
re-derivation:

  omega_exact      linear dispersion ``sqrt(g k tanh(k h))``, ``k = pi / L``
  omega_swe        shallow-water dispersion ``k sqrt(g h)``
  swe_ratio        ``omega_swe / omega_exact = sqrt(kh / tanh(kh))``
  kh_of            ``k h``
  kh_for_ratio     largest ``kh`` with ``swe_ratio(kh) <= target`` (bisection)
  bore_reflection  reflected depth ``h_r`` with ``u_r = 0`` from the
                   Saint-Venant shock (Rankine-Hugoniot) condition
  peak_omega       spectral peak of a sampled wall signal (two-stage DFT +
                   parabolic refinement; no FFT library, no numpy)
  series_max       ``max(y)``
  series_last      ``y[-1]``

Usage as a CLI (shows the derivations for the IN48-N07 anchor)::

    python3 scripts/sloshing_reference.py
"""

from __future__ import annotations

import math
from typing import Callable, Iterable, Sequence

__all__ = [
    "omega_exact",
    "omega_swe",
    "swe_ratio",
    "kh_of",
    "kh_for_ratio",
    "bore_reflection_depth",
    "shock_velocity",
    "peak_omega",
    "series_max",
    "series_last",
    "series_last_abs",
    "moving_max",
    "peak_omega_ratio",
    "u_front",
    "bore_reflection_ratio",
    "swe_ratio_percent",
    "anchor_table",
    "RECIPES",
]

# IN48-N07 tank / fluid anchors (also the defaults of the source TankAnchor).
ANCHOR = {
    "length": 20.0,
    "breadth": 12.0,
    "height": 8.0,
    "depth": 4.0,
    "rho": 1025.0,
    "g": 9.80665,
}


def omega_exact(length: float, depth: float, g: float = 9.80665) -> float:
    """Exact first sloshing mode ``sqrt(g k tanh(k h))`` with ``k = pi / L`` [rad/s]."""
    k = math.pi / length
    return math.sqrt(g * k * math.tanh(k * depth))


def omega_swe(length: float, depth: float, g: float = 9.80665) -> float:
    """First mode of the shallow-water equations ``k sqrt(g h)`` [rad/s]."""
    return (math.pi / length) * math.sqrt(g * depth)


def swe_ratio(kh: float) -> float:
    """``omega_SWE / omega_exact = sqrt(kh / tanh(kh))`` (>= 1, -> 1 as ``kh -> 0``)."""
    if kh <= 0.0:
        return 1.0
    return math.sqrt(kh / math.tanh(kh))


def kh_of(length: float, depth: float) -> float:
    return (math.pi / length) * depth


def kh_for_ratio(target: float, hi: float = 50.0, iters: int = 200) -> float:
    """Largest relative depth with ``swe_ratio(kh) <= target`` (monotone bisection).

    ``swe_ratio`` is strictly increasing, so the bisection bracket is unique; the
    returned value is the upper end of the final bracket (conservative bound).
    """
    if target < 1.0:
        raise ValueError("target ratio must be >= 1")
    lo = 0.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if swe_ratio(mid) <= target:
            lo = mid
        else:
            hi = mid
    return lo


def shock_velocity(h_i: float, h_r: float, g: float = 9.80665) -> float:
    """Rankine-Hugoniot velocity of a bore stepping from ``h_i`` to ``h_r`` [m/s].

    ``u_i = (h_r - h_i) sqrt( g (h_r + h_i) / (2 h_r h_i) )``
    """
    if h_i <= 0.0 or h_r <= 0.0 or h_r < h_i:
        raise ValueError("need 0 < h_i <= h_r")
    return (h_r - h_i) * math.sqrt(g * (h_r + h_i) / (2.0 * h_r * h_i))


def bore_reflection_depth(
    h_i: float, u_i: float, g: float = 9.80665, iters: int = 200, hi_factor: float = 50.0
) -> float:
    """Reflected depth ``h_r`` of a uniform stream ``(h_i, u_i)`` stopped by a wall.

    Same physics as the source (Saint-Venant shock condition with ``u_r = 0``) but
    an independent solver: the source bisects the residual itself, this one
    bisects the *inverse* function ``shock_velocity(h_i, h_r) - u_i`` over a
    bracket that is grown until it changes sign (so an unreachable ``u_i`` raises
    instead of returning a silent bracket edge).
    """
    if h_i <= 0.0 or u_i < 0.0:
        raise ValueError("need h_i > 0 and u_i >= 0")
    if u_i == 0.0:
        return h_i
    lo, hi = h_i, h_i
    for _ in range(64):
        hi *= 2.0
        if shock_velocity(h_i, hi, g) >= u_i:
            break
    else:  # pragma: no cover - only reachable for absurd inputs
        raise ValueError(f"u_i={u_i} not reachable from h_i={h_i} (hi_factor={hi_factor})")
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if shock_velocity(h_i, mid, g) < u_i:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _hann(n: int) -> list[float]:
    if n < 2:
        return [1.0] * n
    return [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (n - 1)) for i in range(n)]


def _magnitude(windowed: Sequence[float], dt: float, omega: float) -> float:
    """``|sum_k y_k exp(-i omega t_k)|`` evaluated with a rotation recurrence."""
    step = omega * dt
    c, s = math.cos(step), math.sin(step)
    cr, sr = 1.0, 0.0
    re = im = 0.0
    for v in windowed:
        re += v * cr
        im += v * sr
        cr, sr = cr * c - sr * s, sr * c + cr * s
    return math.hypot(re, im)


def peak_omega(
    t: Sequence[float],
    y: Sequence[float],
    band: tuple[float, float],
    coarse_step: float = 2.0e-4,
    fine_step: float = 1.0e-5,
) -> dict:
    """Spectral peak of ``y(t)`` inside ``band`` (rad/s), mean-removed, Hann-windowed.

    Two stages: a coarse scan over ``band``, then a fine scan of ``+-3`` coarse
    cells around the coarse maximum, then one parabolic refinement on the fine
    grid.  Deliberately *not* the source's estimator (it takes the first FFT bin
    maximum and refines there), so a match between the two is evidence and a
    mismatch is measurable rather than hidden by a shared code path.
    """
    n = len(y)
    if n != len(t) or n < 8:
        raise ValueError("need len(y) == len(t) >= 8")
    dt = (t[-1] - t[0]) / (n - 1)
    mean = sum(y) / n
    win = _hann(n)
    windowed = [(y[i] - mean) * win[i] for i in range(n)]

    def scan(lo: float, hi: float, step: float) -> tuple[float, float]:
        count = max(2, int(round((hi - lo) / step)) + 1)
        grid = [lo + (hi - lo) * i / (count - 1) for i in range(count)]
        mags = [_magnitude(windowed, dt, w) for w in grid]
        k = max(range(count), key=lambda i: mags[i])
        delta = 0.0
        if 0 < k < count - 1:
            a, b, c = mags[k - 1], mags[k], mags[k + 1]
            den = a - 2.0 * b + c
            if den != 0.0:
                delta = 0.5 * (a - c) / den
        step_used = (hi - lo) / (count - 1)
        return grid[k] + delta * step_used, mags[k]

    coarse_omega, _ = scan(band[0], band[1], coarse_step)
    lo = max(band[0], coarse_omega - 3.0 * coarse_step)
    hi = min(band[1], coarse_omega + 3.0 * coarse_step)
    fine_omega, _ = scan(lo, hi, fine_step)
    return {
        "omega": fine_omega,
        "coarse_omega": coarse_omega,
        "dt": dt,
        "band": list(band),
        "coarse_step": coarse_step,
        "fine_step": fine_step,
        "n": n,
    }


def series_max(values: Iterable[float]) -> float:
    return max(values)


def series_last(values: Sequence[float]) -> float:
    return values[-1]


def u_front(depth: float, g: float = 9.80665) -> float:
    """Ritter (1892) surge front speed on a dry bed ``2 sqrt(g h)`` [m/s]."""
    return 2.0 * math.sqrt(g * depth)


def bore_reflection_ratio(h_i: float, u_i: float | None = None, g: float = 9.80665) -> float:
    """``h_r / h_i`` for a uniform stream stopped by a wall (``u_i`` defaults to Ritter)."""
    if u_i is None:
        u_i = u_front(h_i, g)
    return bore_reflection_depth(h_i, u_i, g) / h_i


def swe_ratio_percent(kh: float) -> float:
    """Frequency excess of the SWE chain over exact dispersion, in percent."""
    return (swe_ratio(kh) - 1.0) * 100.0


def series_last_abs(values: Sequence[float]) -> float:
    return abs(values[-1])


def moving_max(values: Sequence[float], window: int) -> float:
    """Max of a **trailing** moving average of width ``window`` samples.

    Trailing (not centred) on purpose: that is the filter the source calibration
    applies to the wall-pressure history (``filter_samples = 6``), and reproducing
    it exactly is what makes the filtered peak a checkable number.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    running = 0.0
    best = -math.inf
    for i, v in enumerate(values):
        running += v
        if i >= window:
            running -= values[i - window]
        if i >= window - 1:
            best = max(best, running / window)
    if best == -math.inf:
        raise ValueError("series shorter than the window")
    return best


def peak_omega_ratio(
    t: Sequence[float],
    y: Sequence[float],
    band: tuple[float, float],
    length: float,
    depth: float,
    g: float = 9.80665,
) -> float:
    """``peak_omega(y) / omega_exact`` - the LBM-vs-exact frequency ratio."""
    return peak_omega(t, y, band)["omega"] / omega_exact(length, depth, g)


#: name -> (callable, ordered argument names).  ``number_checks`` items address
#: these by name; ``args`` maps argument names to values (numbers or other
#: recipe ids already evaluated).
RECIPES: dict[str, tuple[Callable[..., float], tuple[str, ...]]] = {
    "omega_exact": (omega_exact, ("length", "depth", "g")),
    "omega_swe": (omega_swe, ("length", "depth", "g")),
    "swe_ratio": (swe_ratio, ("kh",)),
    "swe_ratio_percent": (swe_ratio_percent, ("kh",)),
    "kh_of": (kh_of, ("length", "depth")),
    "kh_for_ratio": (kh_for_ratio, ("target",)),
    "u_front": (u_front, ("depth", "g")),
    "bore_reflection_depth": (bore_reflection_depth, ("h_i", "u_i", "g")),
    "bore_reflection_ratio": (bore_reflection_ratio, ("h_i", "u_i", "g")),
    "peak_omega": (lambda t, y, band: peak_omega(t, y, tuple(band))["omega"], ("t", "y", "band")),
    "peak_omega_ratio": (
        lambda t, y, band, length, depth, g: peak_omega_ratio(t, y, tuple(band), length, depth, g),
        ("t", "y", "band", "length", "depth", "g"),
    ),
    "series_max": (series_max, ("values",)),
    "series_last": (series_last, ("values",)),
    "series_last_abs": (series_last_abs, ("values",)),
    "moving_max": (moving_max, ("values", "window")),
}


def anchor_table(anchor: dict | None = None) -> dict:
    """All closed-form anchors of the IN48-N07 case (used by the CLI and the docs)."""
    a = dict(ANCHOR if anchor is None else anchor)
    k = math.pi / a["length"]
    kh = kh_of(a["length"], a["depth"])
    u_front = 2.0 * math.sqrt(a["g"] * a["depth"])
    h_r = bore_reflection_depth(a["depth"], u_front, a["g"])
    return {
        "k1": k,
        "kh": kh,
        "omega1": omega_exact(a["length"], a["depth"], a["g"]),
        "period1": 2.0 * math.pi / omega_exact(a["length"], a["depth"], a["g"]),
        "omega1_swe": omega_swe(a["length"], a["depth"], a["g"]),
        "swe_ratio": swe_ratio(kh),
        "u_front": u_front,
        "p_hydrostatic": a["rho"] * a["g"] * a["depth"],
        "h_r": h_r,
        "h_r_over_h_l": h_r / a["depth"],
        "p_bore_over_rho_g_h": h_r / a["depth"],
        "kh_3pct": kh_for_ratio(1.03),
        "kh_5pct": kh_for_ratio(1.05),
        "kh_10pct": kh_for_ratio(1.10),
    }


def main() -> int:
    table = anchor_table()
    print("IN48-N07 closed-form anchors (L=20 m, B=12 m, H=8 m, h_l=4 m, rho=1025, g=9.80665)")
    for key, value in table.items():
        print(f"  {key:22s} {value!r}")
    kh = table["kh"]
    print(f"  h/L at 3% bound          {table['kh_3pct'] / (math.pi / 20.0) / 20.0:.6f}"
          f"  (kh={kh:.6f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())