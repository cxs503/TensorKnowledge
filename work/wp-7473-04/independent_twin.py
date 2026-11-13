"""Independent reproduction of report 7473 Table 2 / Table 3 twin rows.

Calls the public entry point run_laminar_poiseuille directly (own script, own
arguments) and prints the fields the report tabulates.

Run:
    PYTHONPATH=/root/tensor-ecosystem/TensorLBM/src OMP_NUM_THREADS=1 \
        python3 work/wp-7473-04/independent_twin.py
"""
from __future__ import annotations

import json

import torch

from tensorlbm.turbulence.turbulent_channel3d import (
    TurbulentChannel3DConfig,
    run_laminar_poiseuille,
)

torch.set_num_threads(1)

CAMPAIGN = TurbulentChannel3DConfig(nx=8, nz=8, ny=18, re_tau=180.0, u_tau=0.01)
INTERP = TurbulentChannel3DConfig(
    nx=8, nz=8, ny=18, re_tau=180.0, u_tau=0.01, wall_origin=0.375, wall_scheme="interpolated"
)

KEYS = [
    "re_tau",
    "u_tau",
    "nu",
    "tau_plus",
    "u_max_mean",
    "u_max_analytic",
    "relative_l2_error",
    "wall_origin_measured",
    "wall_origin_shift",
    "u_tau_body_force",
    "u_tau_wall_exchange",
]


def pick(res: dict) -> dict:
    out = {k: res["config"].get(k) for k in ("re_tau", "u_tau", "nu", "tau_plus")}
    out.update({k: res[k] for k in KEYS if k in res})
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in out.items()}


if __name__ == "__main__":
    rows = {}
    rows["halfway_recalibrated_800"] = pick(run_laminar_poiseuille(CAMPAIGN, steps=800))
    rows["interpolated_q0.375_800"] = pick(run_laminar_poiseuille(INTERP, steps=800))
    rows["halfway_recalibrated_2000"] = pick(run_laminar_poiseuille(CAMPAIGN, steps=2000))
    rows["interpolated_q0.375_2000"] = pick(run_laminar_poiseuille(INTERP, steps=2000))
    legacy = run_laminar_poiseuille(CAMPAIGN, steps=800, u_max_target=None)
    rows["legacy_u_max_target_None_800"] = pick(legacy)
    print(json.dumps(rows, indent=1, ensure_ascii=False))
    json.dump(rows, open("work/wp-7473-04/twin_repro.json", "w"), indent=1, ensure_ascii=False)