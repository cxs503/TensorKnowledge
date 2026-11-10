#!/usr/bin/env python3
"""Faithful NumPy port of two benchmark codes from lbm-principles-practice/code.

Ported from (verbatim algorithm, only the language changes):
  * chapter5/poiseuille_BB.m  -- Poiseuille flow with half-way bounce-back walls
  * chapter5/couette_BB.m     -- Couette flow with a moving half-way bounce-back wall

Purpose (mission m8676): the port is the *verification surface* for the
GAP-LBM-BENCH-METHODOLOGY anchor. It is NOT upstream code and is not offered as
such: it exists so that the benchmark claims extracted from the repository
(e.g. "tau = sqrt(3/16)+0.5 gives the exact Poiseuille solution") can be tested
by execution instead of being accepted from source comments.

MATLAB -> NumPy mapping notes (why the port is faithful):
  * 1-based MATLAB population index 1..9, zero direction last; here 0-based
    with the same ordering: w=[1/9 1/9 1/9 1/9 1/36 1/36 1/36 1/36 4/9]
  * streaming `newx = 1+mod(i-1+cx+NX,NX)` == np.roll(field, shift=cx, axis=0)
  * wall rows are overwritten after streaming, exactly as in the .m files
  * the L2 error excludes the first/last x layers and is normalised/averaged
    exactly as in the .m files (error(i)=||u(i,:)-u_analy||/||u_analy||, L2=1/NX*sum)

Outputs (JSON + PNG) go to the directory given by --out.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

# Lattice parameters; note zero direction is last (same ordering as the .m files)
W = np.array([1 / 9, 1 / 9, 1 / 9, 1 / 9, 1 / 36, 1 / 36, 1 / 36, 1 / 36, 4 / 9])
CX = np.array([1, 0, -1, 0, 1, -1, -1, 1, 0], dtype=int)
CY = np.array([0, 1, 0, -1, 1, 1, -1, -1, 0], dtype=int)

# opposite directions (0-based): 1<->3, 2<->4, 5<->7, 6<->8
OPP = np.array([8, 3, 4, 1, 2, 7, 8, 5, 6], dtype=int)


def _stream(f: np.ndarray) -> np.ndarray:
    """Periodic streaming of the whole domain (both directions), as in the .m code."""
    fprop = np.empty_like(f)
    for k in range(9):
        fprop[:, :, k] = np.roll(np.roll(f[:, :, k], CX[k], axis=0), CY[k], axis=1)
    return fprop


def _l2(u: np.ndarray, u_analy: np.ndarray) -> float:
    NX = u.shape[0]
    error = np.zeros(NX)
    for i in range(1, NX - 1):
        error[i] = math.sqrt(np.sum((u[i, :] - u_analy) ** 2)) / math.sqrt(np.sum(u_analy ** 2))
    return float(error.sum() / NX)


def poiseuille_bb(scale: float = 1.0, tau: float | None = None,
                  tol: float = 1e-12, teval: int = 100, max_steps: int | None = None,
                  verbose: bool = False) -> dict:
    """Port of chapter5/poiseuille_BB.m (BGK, linear equilibrium, PBBC inlet/outlet)."""
    NX = int(5 * scale)
    NY = int(5 * scale)
    NSTEPS = int(1e4 * scale ** 2) if max_steps is None else max_steps
    tau = (math.sqrt(3 / 16) + 0.5) if tau is None else tau
    omega = 1 / tau
    u_max = 0.1 / scale
    nu = (2 * tau - 1) / 6

    y = (np.arange(1, NY + 1) - 0.5)
    ybottom, ytop = 0.0, float(NY)
    gradP = 8 * nu * u_max / NY ** 2
    rho_outlet = 1.0
    rho_inlet = 3 * (NX - 1) * gradP + rho_outlet
    u_analy_1d = -4 * u_max / NY ** 2 * (y - ybottom) * (y - ytop)
    u_analy = np.tile(u_analy_1d, (NX, 1))

    f = np.tile(W, (NX, NY, 1))
    fprop = f.copy()
    u_old = np.zeros((NX, NY))
    u = np.zeros((NX, NY))

    steps = 0
    for t in range(1, NSTEPS + 1):
        steps = t
        rho = fprop.sum(axis=2)
        # note: the .m codes do NOT divide by rho (linear equilibrium, rho ~ 1)
        u = fprop[:, :, [0, 4, 7]].sum(axis=2) - fprop[:, :, [2, 5, 6]].sum(axis=2)
        v = fprop[:, :, [1, 4, 5]].sum(axis=2) - fprop[:, :, [3, 6, 7]].sum(axis=2)

        if t % teval == 1:
            denom = np.mean(u_old)
            conv = abs(np.mean(u) / denom - 1) if denom != 0 else float("inf")
            if np.isfinite(conv) and conv < tol:
                break
            u_old = u

        feq = W[None, None, :] * (rho[:, :, None] + 3 * (u[:, :, None] * CX + v[:, :, None] * CY))
        f = (1 - omega) * fprop + omega * feq

        # Inlet/Outlet BC: PBBC (w/ i=1 and i=NX outside layers)
        f[0, :, :] = W[None, :] * (rho_inlet + 3 * (CX * u[NX - 2, :][:, None] + CY * v[NX - 2, :][:, None])) \
            + (f[NX - 2, :, :] - feq[NX - 2, :, :])
        f[NX - 1, :, :] = W[None, :] * (rho_outlet + 3 * (CX * u[1, :][:, None] + CY * v[1, :][:, None])) \
            + (f[1, :, :] - feq[1, :, :])

        fprop = _stream(f)

        # Boundary condition (bounce-back); top and bottom walls at rest
        fprop[:, NY - 1, 3] = f[:, NY - 1, 1]
        fprop[:, NY - 1, 6] = f[:, NY - 1, 4]
        fprop[:, NY - 1, 7] = f[:, NY - 1, 5]
        fprop[:, 0, 1] = f[:, 0, 3]
        fprop[:, 0, 4] = f[:, 0, 6]
        fprop[:, 0, 5] = f[:, 0, 7]

        if verbose and t % (teval * 10) == 0:
            print(f"  step {t:6d}  L2={_l2(u, u_analy):.3e}  umax={u.max():.6f}", flush=True)

    return {
        "case": "poiseuille_BB",
        "NX": NX, "NY": NY, "tau": tau, "omega": omega, "nu": nu, "u_max": u_max,
        "gradP": gradP, "steps": steps,
        "L2": _l2(u, u_analy),
        "u_center_num": float(u[NX // 2, NY // 2]),
        "u_center_analytic": float(u_analy_1d[NY // 2]),
        "u_max_num": float(u.max()),
        "profile_y": y.tolist(),
        "profile_u": u[NX // 2, :].tolist(),
        "profile_u_analytic": u_analy_1d.tolist(),
    }


def couette_bb(scale: float = 1.0, tau: float = 0.9,
               tol: float = 1e-12, teval: int = 100, max_steps: int | None = None) -> dict:
    """Port of chapter5/couette_BB.m (top wall moving with u_max, bottom wall at rest)."""
    NX = int(3 * scale)
    NY = int(5 * scale)
    NSTEPS = int(1e4 * scale ** 2) if max_steps is None else max_steps
    omega = 1 / tau
    u_max = 0.1 / scale
    nu = (2 * tau - 1) / 6

    y = (np.arange(1, NY + 1) - 0.5)
    u_analy_1d = u_max / NY * y
    u_analy = np.tile(u_analy_1d, (NX, 1))

    f = np.tile(W, (NX, NY, 1))
    fprop = f.copy()
    u_old = np.zeros((NX, NY))
    u = np.zeros((NX, NY))

    steps = 0
    for t in range(1, NSTEPS + 1):
        steps = t
        rho = fprop.sum(axis=2)
        # note: the .m codes do NOT divide by rho (linear equilibrium, rho ~ 1)
        u = fprop[:, :, [0, 4, 7]].sum(axis=2) - fprop[:, :, [2, 5, 6]].sum(axis=2)
        v = fprop[:, :, [1, 4, 5]].sum(axis=2) - fprop[:, :, [3, 6, 7]].sum(axis=2)

        if t % teval == 1:
            denom = np.mean(u_old)
            conv = abs(np.mean(u) / denom - 1) if denom != 0 else float("inf")
            if np.isfinite(conv) and conv < tol:
                break
            u_old = u

        feq = W[None, None, :] * (rho[:, :, None] + 3 * (u[:, :, None] * CX + v[:, :, None] * CY))
        f = (1 - omega) * fprop + omega * feq

        fprop = _stream(f)

        # Top wall (moving with tangential velocity u_max)
        fprop[:, NY - 1, 3] = f[:, NY - 1, 1]
        fprop[:, NY - 1, 6] = f[:, NY - 1, 4] - (1 / 6) * u_max
        fprop[:, NY - 1, 7] = f[:, NY - 1, 5] + (1 / 6) * u_max
        # Bottom wall (rest)
        fprop[:, 0, 1] = f[:, 0, 3]
        fprop[:, 0, 4] = f[:, 0, 6]
        fprop[:, 0, 5] = f[:, 0, 7]

    return {
        "case": "couette_BB",
        "NX": NX, "NY": NY, "tau": tau, "nu": nu, "u_max": u_max, "steps": steps,
        "L2": _l2(u, u_analy),
        "u_top_num": float(u[NX // 2, NY - 1]),
        "u_top_analytic": float(u_analy_1d[NY - 1]),
        "profile_y": y.tolist(),
        "profile_u": u[NX // 2, :].tolist(),
        "profile_u_analytic": u_analy_1d.tolist(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".", help="output directory for JSON/PNG")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results: dict = {"note": "NumPy port of chapter5/*.m from lbm-principles-practice/code; "
                             "port used as verification surface, not upstream code",
                     "runs": []}

    t0 = time.time()
    pois = poiseuille_bb(scale=1)
    results["runs"].append(pois)
    print(f"poiseuille_BB tau={pois['tau']:.6f} steps={pois['steps']} L2={pois['L2']:.3e} "
          f"u_center={pois['u_center_num']:.12f} (analytic {pois['u_center_analytic']:.12f})", flush=True)

    cou = couette_bb(scale=1)
    results["runs"].append(cou)
    print(f"couette_BB tau={cou['tau']} steps={cou['steps']} L2={cou['L2']:.3e} "
          f"u_top={cou['u_top_num']:.12f} (analytic {cou['u_top_analytic']:.12f})", flush=True)

    # tau sweep: does the documented "exact solution" relaxation time minimise the L2 error?
    sweep = []
    for tau in [0.6, 0.7, 0.8, 0.85, 0.9, math.sqrt(3 / 16) + 0.5, 0.95, 1.0, 1.1, 1.3]:
        r = poiseuille_bb(scale=1, tau=tau)
        sweep.append({"tau": r["tau"], "L2": r["L2"], "steps": r["steps"]})
        print(f"  tau={tau:.6f}  L2={r['L2']:.3e}  steps={r['steps']}", flush=True)
    results["tau_sweep"] = sweep

    # resolution study at the documented relaxation time
    res = []
    for scale in [1, 2, 3, 4]:
        r = poiseuille_bb(scale=scale)
        res.append({"scale": scale, "NX": r["NX"], "NY": r["NY"], "L2": r["L2"], "steps": r["steps"]})
        print(f"  scale={scale} NX={r['NX']} NY={r['NY']} L2={r['L2']:.3e} steps={r['steps']}", flush=True)
    results["resolution_study"] = res
    results["wall_time_s"] = time.time() - t0

    (out / "kruger_bench_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    # figure: profile comparison + tau sweep
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
        ax[0].plot(pois["profile_u_analytic"], pois["profile_y"], "k-", label="analytic parabola")
        ax[0].plot(pois["profile_u"], pois["profile_y"], "o", ms=5, mfc="none", label="port (tau = 1/2+sqrt(3/16))")
        ax[0].set_xlabel("$u_x$ [lattice]"); ax[0].set_ylabel("$y$ [lattice]")
        ax[0].set_title("Poiseuille, half-way bounce-back")
        ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)

        ax[1].plot(cou["profile_u_analytic"], cou["profile_y"], "k-", label="analytic line")
        ax[1].plot(cou["profile_u"], cou["profile_y"], "s", ms=5, mfc="none", label="port (tau=0.9)")
        ax[1].set_xlabel("$u_x$ [lattice]"); ax[1].set_ylabel("$y$ [lattice]")
        ax[1].set_title("Couette, moving bounce-back wall")
        ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)

        taus = [s["tau"] for s in sweep]
        l2s = [max(s["L2"], 1e-18) for s in sweep]
        ax[2].semilogy(taus, l2s, "o-")
        ax[2].axvline(math.sqrt(3 / 16) + 0.5, color="r", ls="--", label="tau = 1/2+sqrt(3/16)")
        ax[2].set_xlabel("$\\tau$"); ax[2].set_ylabel("$L_2(u)$")
        ax[2].set_title("Poiseuille L2 error vs relaxation time")
        ax[2].legend(fontsize=8); ax[2].grid(alpha=.3, which="both")
        fig.tight_layout()
        fig.savefig(out / "kruger_bench_profiles.png", dpi=140)
    except Exception as exc:  # pragma: no cover - figure is auxiliary
        print(f"figure skipped: {exc}")

    print(f"done in {results['wall_time_s']:.1f}s -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())