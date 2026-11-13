"""Independent review probe for report 7473 (wp-7473-01 review, wp-7473-04).

Does NOT reuse the producer's artifacts/run_probe.py. Two independent layers:
  1) pure-arithmetic audit of the report's own tables (no LBM involved);
  2) a minimal re-measurement of the force-impulse anchor through the public
     module API (TurbulentChannel3D._step_once / _equilibrium), i.e. the same
     observable the report's Table 1/Table 3 claim, with our own code.

Run:
    PYTHONPATH=/root/tensor-ecosystem/TensorLBM/src OMP_NUM_THREADS=1 \
        python3 work/wp-7473-04/independent_probe.py
"""
from __future__ import annotations

import json
import math
import sys

import torch

from tensorlbm.turbulence.turbulent_channel3d import (
    TurbulentChannel3D,
    TurbulentChannel3DConfig,
)

NX, NZ, NY = 8, 8, 18
HALF_HEIGHT = (NY - 2) / 2.0  # h = 8
ACCEL = 1e-4
CS = 1.0 / math.sqrt(3.0)

out: dict = {}


# ---------------------------------------------------------------- layer 1: arithmetic
def table1_arithmetic() -> dict:
    rows = [
        # (nu, tau+_reported, s+_reported, trt_reported, guo_reported)
        (0.0020, 0.5060, 1.9763, 1.0001, 0.0277),
        (0.0200, 0.5600, 1.7857, 1.0000, 0.2451),
        (0.0400, 0.6200, 1.6129, 1.0000, 0.4359),
        (0.1200, 0.8600, 1.1628, 0.9998, 0.9083),
        (0.2000, 1.1000, 0.9091, 0.9994, 1.1601),
        (2.22e-3, 0.5067, 1.9947, 1.0000, 0.0063),
    ]
    checks = []
    for nu, tau_rep, s_rep, trt, guo in rows:
        tau_exact = 0.5 + 3.0 * nu
        s_exact = 1.0 / tau_exact
        checks.append(
            {
                "nu": nu,
                "tau_plus_reported": tau_rep,
                "tau_plus_from_0.5+3nu": round(tau_exact, 6),
                "tau_plus_abs_dev": abs(tau_exact - tau_rep),
                "s_plus_reported": s_rep,
                "s_plus_from_1/tau_plus": round(s_exact, 6),
                "s_plus_abs_dev": abs(s_exact - s_rep),
                "trt_split_reported": trt,
                "guo_sp_reported": guo,
                "guo_fit_2.11-1.045s": round(2.11 - 1.045 * s_rep, 5),
                "guo_fit_abs_dev_vs_reported": abs((2.11 - 1.045 * s_rep) - guo),
                "guo_fit_rel_dev_pct": round(100 * abs((2.11 - 1.045 * s_rep) - guo) / guo, 2),
            }
        )
    return {"rows": checks}


def table2_arithmetic() -> dict:
    def rel(a, b):
        return round(100 * abs(a - b) / abs(b), 4)

    return {
        "nu_eff_vs_0.04_pct": rel(0.039939, 0.04),
        "peak_ratio_0.99065_vs_1_pct": rel(0.99065, 1.0),
        "wall_origin_halfway_0.4725_vs_0.5_abs": round(abs(0.4725 - 0.5), 4),
        "wall_origin_halfway_0.4725_vs_0.5_pct": rel(0.4725, 0.5),
        "wall_origin_interp_0.495_vs_0.375_pct": rel(0.495, 0.375),
        "u_tau_exchange_0.03556_vs_0.025_pct": rel(0.03556, 0.025),
        "tau_w_ratio_exchange_over_body_force": round((0.03556 / 0.025) ** 2, 4),
        "l2_halfway_6.76e-3_as_pct_if_norm_1.0": round(100 * 6.76e-3, 3),
        "l2_interp_2.46e-2_as_pct_if_norm_1.0": round(100 * 2.46e-2, 3),
        "l2_interp_2.46e-2_over_u_max_0.0498_pct": round(100 * 2.46e-2 / 0.0498, 2),
        "l2_halfway_6.76e-3_over_u_max_0.0498_pct": round(100 * 6.76e-3 / 0.0498, 2),
    }


def campaign_identity() -> dict:
    u_tau, re_tau, h = 0.01, 180.0, HALF_HEIGHT
    nu = u_tau * h / re_tau
    u_max_identity = u_tau * re_tau / 2.0
    return {
        "h": h,
        "nu_campaign_from_u_tau_h_over_re_tau": nu,
        "tau_plus_campaign": 0.5 + 3 * nu,
        "s_plus_campaign": 1.0 / (0.5 + 3 * nu),
        "u_max_identity_u_tau*re/2": u_max_identity,
        "u_max_reported_in_table3": 0.896,
        "u_max_identity_abs_dev": abs(u_max_identity - 0.896),
        "Ma_identity": u_max_identity / CS,
        "Ma_at_reported_u_max": 0.896 / CS,
        "nu_A_prime_hypothesis_u_tau_0.05": 0.05 * h / re_tau,
        "nu_for_tau_plus_0.5067": (0.5067 - 0.5) / 3,
    }


# ---------------------------------------------------------------- layer 2: re-measure
def _nu_to_config(nu: float, **kwargs) -> TurbulentChannel3DConfig:
    u_tau = 0.01
    return TurbulentChannel3DConfig(
        nx=NX, nz=NZ, ny=NY, u_tau=u_tau, re_tau=u_tau * HALF_HEIGHT / nu, **kwargs
    )


def _interior_ux(sim: TurbulentChannel3D) -> float:
    m = torch.mm(sim.A, sim.f.view(19, sim.N))
    ux = (m[1] / m[0]).view(sim.nz, sim.ny, sim.nx)
    return float(ux[:, 6:12, :].mean())


def measure_rate(nu: float, scheme: str, steps: int = 12) -> dict:
    cfg = _nu_to_config(nu, steps=steps, warmup_steps=0, body_force=ACCEL, force_scheme=scheme)
    sim = TurbulentChannel3D(cfg)
    ones = torch.ones(1, sim.N)
    zeros = torch.zeros(3, sim.N)
    sim.f = sim._equilibrium(ones, zeros).reshape(19, sim.nz, sim.ny, sim.nx)
    u0 = _interior_ux(sim)
    for _ in range(steps):
        sim._step_once()
    rate = (_interior_ux(sim) - u0) / steps / ACCEL
    return {
        "nu": nu,
        "tau_plus": round(cfg.tau_plus, 6),
        "s_plus": round(1.0 / cfg.tau_plus, 6),
        "scheme": scheme,
        "dU_dt_over_a": round(rate, 6),
    }


def remeasure() -> dict:
    torch.set_num_threads(1)
    nus = [0.002, 0.02, 0.04, 0.12, 0.2]
    rows = [measure_rate(nu, s) for nu in nus for s in ("trt_split", "guo_sp")]
    nu_campaign = 0.01 * HALF_HEIGHT / 180.0  # 4.444e-4
    nu_a_prime = 2.22e-3
    extra = [
        measure_rate(nu_campaign, "trt_split"),
        measure_rate(nu_campaign, "guo_sp"),
        measure_rate(nu_a_prime, "guo_sp"),
        measure_rate(nu_a_prime, "trt_split"),
    ]
    # longest-run check at the campaign viscosity to expose transient drift
    long_run = [measure_rate(nu_campaign, s, steps=120) for s in ("trt_split", "guo_sp")]
    return {"truth_table": rows, "campaign_and_A_prime": extra, "steps_120": long_run}


if __name__ == "__main__":
    payload = {
        "table1_arithmetic": table1_arithmetic(),
        "table2_arithmetic": table2_arithmetic(),
        "campaign_identity": campaign_identity(),
        "remeasure": remeasure(),
    }
    json.dump(payload, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
    print(json.dumps(payload["table1_arithmetic"], indent=1, ensure_ascii=False))
    print(json.dumps(payload["campaign_identity"], indent=1, ensure_ascii=False))
    print(json.dumps(payload["remeasure"], indent=1, ensure_ascii=False))