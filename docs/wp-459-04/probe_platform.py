#!/usr/bin/env python3
"""wp-459-04: re-probe the ship platform resistance API for the numbers quoted in
report 459 (sections 5 and 6). Records raw responses + derived deviations so the
review's counter-evidence is reproducible instead of asserted.

Usage: python3 docs/wp-459-04/probe_platform.py [--base http://127.0.0.1:8001]
Writes platform_probe.json next to this script.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

RHO_M, NU_M = 998.2, 1.0040e-06
RHO_S, NU_S = 1025.9, 1.1883e-06

SHIP = {"length": 230.0, "beam": 32.2, "draft": 10.8, "displacement": 52030.0,
        "cb": 0.6505, "speed": 24.0, "speed_unit": "kn",
        "water_density": RHO_S, "kinematic_viscosity": NU_S, "wetted_surface": 9424.0}
MODEL = {"length": 7.2786, "beam": 1.019, "draft": 0.3418, "displacement": 1.6489,
         "cb": 0.6505, "speed": 2.1966, "speed_unit": "m/s",
         "water_density": RHO_M, "kinematic_viscosity": NU_M, "wetted_surface": 9.4376}
MODEL_KS0 = dict(MODEL, ks=0)
SHIP_KS0 = dict(SHIP, ks=0)

PROBES = {
    "P1_ship_24kn_as_declared": SHIP,
    "P2_model_Fr026_as_declared": MODEL,
    "P3_model_Fr026_ks0": MODEL_KS0,
    "P4_ship_24kn_ks0": SHIP_KS0,
}


def post(base: str, body: dict) -> dict:
    req = urllib.request.Request(base.rstrip("/") + "/api/v1/calculations/resistance",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as fh:
            payload = json.load(fh)
    except urllib.error.HTTPError as exc:            # keep the body, it is evidence
        return {"http_error": exc.code, "body": exc.read().decode()[:2000]}
    return {"port": payload.get("port"), "data": payload.get("data", payload)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("SHIP_API_BASE", "http://127.0.0.1:8001"))
    args = ap.parse_args()
    out = {"base": args.base, "requests": {}, "derived": {}}
    for name, body in PROBES.items():
        out["requests"][name] = {"request": body, "response": post(args.base, body)}

    def num(probe, key):
        d = out["requests"][probe]["response"].get("data") or {}
        return d.get(key)

    ship_rt_kN = num("P1_ship_24kn_as_declared", "rt")
    ship_rt_ks0_kN = num("P4_ship_24kn_ks0", "rt")
    mod_rt_kN = num("P2_model_Fr026_as_declared", "rt")
    mod_rt_ks0_kN = num("P3_model_Fr026_ks0", "rt")
    import math
    q_model = 0.5 * RHO_M * 9.4376 * 2.1966 ** 2
    q_ship = 0.5 * RHO_S * 9424.0 * (24.0 / 1.943844) ** 2
    out["derived"] = {
        "q_model_N_per_C": round(q_model, 1),
        "q_ship_kN_per_C": round(q_ship / 1e3, 1),
        "model_R_TM_N_as_declared": None if mod_rt_kN is None else round(mod_rt_kN * 1e3, 2),
        "model_R_TM_N_ks0": None if mod_rt_ks0_kN is None else round(mod_rt_ks0_kN * 1e3, 2),
        "model_C_TM_as_declared": None if mod_rt_kN is None else round(mod_rt_kN * 1e3 / q_model, 6),
        "report_model_R_TM_N": 171.6,
        "report_anchor_R_TM_N": 88.8,
        "dev_live_model_vs_report_model_pct":
            None if mod_rt_kN is None else round((mod_rt_kN * 1e3) / 171.6 * 100 - 100, 2),
        "dev_live_model_vs_anchor_pct":
            None if mod_rt_kN is None else round((mod_rt_kN * 1e3) / 88.8 * 100 - 100, 2),
        "report_dev_vs_anchor_pct": 93.3,
        "ship_R_T_kN_as_declared": ship_rt_kN,
        "ship_R_T_kN_ks0": ship_rt_ks0_kN,
        "report_ship_platform_kN": 4536.0,
        "report_ship_simplified_kN": 7407.0,
        "library_ship_R_T_kN": 1850.0,
        "dev_live_ship_vs_library_pct":
            None if ship_rt_kN is None else round(ship_rt_kN / 1850.0 * 100 - 100, 2),
        "report_dev_ship_vs_library_pct": 145.2,
        "report_dev_simplified_vs_library_pct": 300.4,
        "report_claimed_simplified_range_pct": [283, 311],
    }
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform_probe.json"), "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(json.dumps(out["derived"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
