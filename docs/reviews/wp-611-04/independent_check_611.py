#!/usr/bin/env python3
"""Independent red-team re-computation for KF work package wp-611-04 (report 611).

Scope: ONLY report_id=611, markdown field.  Nothing is written outside this
directory.  Every number below is recomputed from the parameters that are
verbatim present in the report itself:

    R=0.5m, rho_i=917 kg/m3, rho_w=1025 kg/m3, g=9.81 m/s2, wave A=0.1m, lambda=10m, T=2.5s

Two independent reference paths are used on purpose:

  * closed form  (circular segment / spherical cap)
  * numerical    (fine quadrature over horizontal slices, and Monte-Carlo)

so that the *discriminative power* of the producer's verification can be
measured: an error of 2.19e-16 (machine epsilon) can only arise when the
"reference" is the same algebraic expression as the "result".

Usage:
    python3 independent_check_611.py --md /tmp/r611.md --out independent_check_results.json
    # token optional; with --fetch the markdown is pulled from the platform API
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

R = 0.5
RHO_I = 917.0
RHO_W = 1025.0
G = 9.81
WAVE_A = 0.1
WAVE_LAMBDA = 10.0
WAVE_T = 2.5
EXPECTED_SHA = "72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88"

# ---------------------------------------------------------------- geometry ---
# h = depth of the body centre below the free surface (h>0 == centre submerged).


def _arc(u: float, r: float = R) -> float:
    """Antiderivative of 2*sqrt(r^2-u^2)."""
    u = max(-r, min(r, u))
    return u * math.sqrt(max(r * r - u * u, 0.0)) + r * r * math.asin(u / r)


def area_2d(h: float, r: float = R) -> float:
    """Submerged area of a 2-D circular disk (per unit length), centre at depth h."""
    if h >= r:
        return math.pi * r * r
    if h <= -r:
        return 0.0
    return _arc(h, r) - _arc(-r, r)


def fsub_2d(h: float, r: float = R) -> float:
    return area_2d(h, r) / (math.pi * r * r)


def vol_3d(h: float, r: float = R) -> float:
    """Submerged volume of a sphere, centre at depth h (spherical cap from bottom)."""
    if h >= r:
        return 4.0 / 3.0 * math.pi * r ** 3
    if h <= -r:
        return 0.0
    hc = r + h                      # cap height
    return math.pi * hc ** 2 * (3 * r - hc) / 3.0


def fsub_3d(h: float, r: float = R) -> float:
    return vol_3d(h, r) / (4.0 / 3.0 * math.pi * r ** 3)


def slice_quadrature(f, h: float, n: int) -> float:
    """Independent reference: midpoint quadrature over horizontal slices (numpy)."""
    import numpy as np

    lo, hi = -R, min(h, R)
    if hi <= lo:
        return 0.0
    u = np.linspace(lo, hi, n, endpoint=False) + 0.5 * (hi - lo) / n
    return float(np.sum(f(u)) * (hi - lo) / n)


def mc_fraction_3d(h: float, n: int = 400_000, seed: int = 20261112) -> float:
    """Monte-Carlo submerged volume fraction of a sphere, centre at depth h."""
    import numpy as np

    rng = np.random.default_rng(seed)
    pts = rng.uniform(-R, R, size=(n, 3))
    sphere = np.einsum("ij,ij->i", pts, pts) <= R * R
    inside = sphere & (pts[:, 1] <= h)
    return float(inside.sum() / max(sphere.sum(), 1))   # fraction OF THE SPHERE


def bisect_fsub(target: float, f, lo: float = -R, hi: float = R, tol: float = 1e-15) -> float:
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) < target:
            lo = mid
        else:
            hi = mid
        if abs(hi - lo) < tol:
            break
    return 0.5 * (lo + hi)


def centroid_depth_2d(h: float, n: int = 200_001) -> float:
    """Centroid of the submerged 2-D region, measured from the centre (numeric)."""
    import numpy as np

    lo, hi = -R, min(h, R)
    if hi <= lo:
        return 0.0
    d = (hi - lo) / n
    u = np.linspace(lo, hi, n, endpoint=False) + 0.5 * d
    w = 2.0 * np.sqrt(np.clip(R * R - u * u, 0.0, None)) * d
    return float(np.sum(w * u) / np.sum(w))


def centroid_depth_3d(h: float, n: int = 200_001) -> float:
    """Centroid of the submerged 3-D region, measured from the centre (numeric)."""
    import numpy as np

    lo, hi = -R, min(h, R)
    if hi <= lo:
        return 0.0
    d = (hi - lo) / n
    u = np.linspace(lo, hi, n, endpoint=False) + 0.5 * d
    w = np.pi * np.clip(R * R - u * u, 0.0, None) * d
    return float(np.sum(w * u) / np.sum(w))


def stability(h: float, dim: int) -> dict:
    """Heave stiffness k = rho_w g A_wp, BM, BG, GM (G at the centre: homogeneous)."""
    c2 = max(R * R - h * h, 0.0)
    if dim == 2:
        a_sub = area_2d(h)
        a_wp = 2.0 * math.sqrt(c2)            # waterplane width (per unit length)
        i_wp = 2.0 / 3.0 * c2 ** 1.5          # 2*c^3/3
        zg = centroid_depth_2d(h)
    else:
        a_sub = vol_3d(h)
        a_wp = math.pi * c2                   # waterplane area
        i_wp = math.pi * c2 ** 2 / 4.0        # pi*c^4/4
        zg = centroid_depth_3d(h)
    bm = i_wp / a_sub if a_sub > 0 else float("inf")
    bg = abs(zg)                              # KG-KB with G at the centre
    return {
        "h": h,
        "A_sub": a_sub,
        "A_waterplane": a_wp,
        "I_waterplane": i_wp,
        "k_heave": RHO_W * G * a_wp,
        "KB_from_centre": zg,
        "BM": bm,
        "BG": bg,
        "GM": bm - bg,
    }


def gm_scan(dim: int, n: int = 81) -> list[dict]:
    rows = []
    for i in range(n):
        f = 0.30 + 0.68 * i / (n - 1)
        ffun = fsub_2d if dim == 2 else fsub_3d
        h = bisect_fsub(f, ffun)
        s = stability(h, dim)
        rows.append({"f_sub": f, "h": h, "GM": s["GM"]})
    return rows


def gm_identity_proof() -> dict:
    """Symbolic check: BM - BG == 0 identically for a homogeneous sphere."""
    try:
        import sympy as sp
    except Exception as exc:                                  # pragma: no cover
        return {"symbolic_ok": None, "error": repr(exc)}
    Rs, hc = sp.symbols("R hc", positive=True)
    c2 = hc * (2 * Rs - hc)
    bm = sp.simplify((sp.pi * c2 ** 2 / 4) / (sp.pi * hc ** 2 * (3 * Rs - hc) / 3))
    z_flat = hc * (4 * Rs - hc) / (4 * (3 * Rs - hc))
    bg = sp.simplify(-((hc - Rs) - z_flat))
    resid = sp.simplify(bm - bg)
    return {
        "BM": str(sp.factor(bm)),
        "BG": str(sp.factor(bg)),
        "BM_minus_BG": str(resid),
        "symbolic_ok": resid == 0,
        "reading": "GM = BM - BG identically 0 for a homogeneous sphere at ANY draught",
    }


def gm_zero_crossing(dim: int) -> float | None:
    rows = gm_scan(dim, 201)
    prev = rows[0]
    for row in rows[1:]:
        if (prev["GM"] < 0.0) != (row["GM"] < 0.0):
            return 0.5 * (prev["f_sub"] + row["f_sub"])
        prev = row
    return None


# ------------------------------------------------------------------ checks ---

QUOTES = [
    "**Parameters:** R=0.5m, ρ_i=917 kg/m³, ρ_w=1025 kg/m³, g=9.81 m/s², wave A=0.1m, λ=10m, T=2.5s.",
    "- **Buoyancy:** Archimedes principle: F_b = ρ_w·g·V_sub",
    "- **Stability:** Heave restoring stiffness k_heave = ρ_w·g·V_total·|df_sub/dh| > 0",
    "- **Wave force:** Morison equation with Airy wave theory (deep-water decay)",
    "| Buoyancy max rel error | 2.15e-16 | 2.19e-16 |",
    "| Equilibrium h_eq (m) | -0.3378 | -0.2986 |",
    "| f_sub at equilibrium | 0.8946 | 0.8946 |",
    "| Heave stiffness (N/m) | 7414 | 5081 |",
    "| GM (m) | ≈0 (neutral) | -0.115 (unstable) |",
    "- 2-D disk GM≈0 and 3-D sphere GM<0 are known analytical results; roll stability in ice fields comes from inter-particle contacts.",
    "- Morison equation valid for D/λ < ~0.1; at D/λ=0.1 we are at the upper limit.",
    "| Buoyancy force | Archimedes | 2.19e-16 | YES |",
    "| Equilibrium f_sub | ρ_i/ρ_w | 7.18e-13 | YES |",
    "| Heave stability | k>0 | k=5081 N/m | YES |",
    "**All acceptance criteria PASS.**",
    "See attached figures (6 total): submerged fraction, buoyancy force, wetted area, equilibrium diagram, heave stiffness, wave force time series.",
]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", help="path to cached markdown of report 611")
    ap.add_argument("--fetch", action="store_true", help="pull markdown from platform API")
    ap.add_argument("--out", default="independent_check_results.json")
    args = ap.parse_args(argv)

    if args.fetch:
        import urllib.request

        base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
        user = os.environ["TENSOR_AGENT_USER"]
        pwd = os.environ["TENSOR_AGENT_PASS"]
        req = urllib.request.Request(
            base + "/auth/login",
            data=json.dumps({"username": user, "password": pwd}).encode(),
            headers={"Content-Type": "application/json"},
        )
        tok = json.load(urllib.request.urlopen(req))["access_token"]
        req = urllib.request.Request(
            base + "/tensor/reports/611", headers={"Authorization": "Bearer " + tok}
        )
        markdown = json.load(urllib.request.urlopen(req))["markdown"]
    else:
        with open(args.md, encoding="utf-8") as fh:
            markdown = fh.read()

    import numpy as np

    sha = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    # ---- quote resolution (byte exact, with offsets) ----
    quote_rows = []
    for q in QUOTES:
        pos = markdown.find(q)
        quote_rows.append(
            {
                "quote": q,
                "start_offset": pos,
                "end_offset": pos + len(q) if pos >= 0 else -1,
                "found": pos >= 0,
            }
        )

    # ---- independent physics ----
    target_f = RHO_I / RHO_W
    h2 = bisect_fsub(target_f, fsub_2d)
    h3 = bisect_fsub(target_f, fsub_3d)
    st2 = stability(h2, 2)
    st3 = stability(h3, 3)

    # analytic buoyancy at equilibrium (per unit length / per particle)
    fb2 = RHO_W * G * area_2d(h2)
    fb3 = RHO_W * G * vol_3d(h3)
    w2 = RHO_I * G * math.pi * R * R
    w3 = RHO_I * G * (4.0 / 3.0 * math.pi * R ** 3)

    # independent references for the submerged volume (quadrature / Monte-Carlo)
    ref = {}
    for n in (2000, 50_000):
        a_q2 = slice_quadrature(lambda u: 2.0 * np.sqrt(np.clip(R * R - u * u, 0.0, None)), h2, n)
        v_q3 = slice_quadrature(lambda u: math.pi * np.clip(R * R - u * u, 0.0, None), h3, n)
        ref[f"quadrature_n{n}"] = {
            "rel_err_2d": abs(a_q2 - area_2d(h2)) / area_2d(h2),
            "rel_err_3d": abs(v_q3 - vol_3d(h3)) / vol_3d(h3),
        }
    # closed-form vs closed-form recomputation of F_b (what a tautological check yields)
    fb2_alt = RHO_W * G * (area_2d(h2))
    ref["closed_form_same_expression"] = {
        "rel_err_2d": abs(fb2 - fb2_alt) / fb2,
        "rel_err_3d": abs(fb3 - RHO_W * G * vol_3d(h3)) / fb3,
    }
    mc3 = mc_fraction_3d(h3, n=200_000)
    ref["monte_carlo_3d"] = {"f_sub_ref": mc3, "rel_err_3d": abs(mc3 - fsub_3d(h3)) / fsub_3d(h3)}

    wave = {
        "lambda_from_T_deepwater": G * WAVE_T ** 2 / (2 * math.pi),
        "T_from_lambda_deepwater": math.sqrt(2 * math.pi * WAVE_LAMBDA / G),
        "g_implied_by_lambda_T": (2 * math.pi / WAVE_T) ** 2 * WAVE_LAMBDA / (2 * math.pi),
        "depth_required_for_deep_water": WAVE_LAMBDA / 2.0,
        "D_over_lambda": 2 * R / WAVE_LAMBDA,
        "D_over_lambda_from_T": 2 * R / (G * WAVE_T ** 2 / (2 * math.pi)),
        "wave_steepness_A_over_lambda": WAVE_A / WAVE_LAMBDA,
    }

    # reproducible abortive hypothesis: which GM convention could give -0.115?
    hyps = {
        "GM_at_equilibrium (BM=I/A_sub, BG=|zB|, G=centre)": st3["GM"],
        "GM_half_draught (=-R/8)": -R / 8.0,
        "GM=I_full_circle/A_sub - BG": (math.pi * R ** 4 / 4) / vol_3d(h3) - abs(st3["KB_from_centre"]),
        "GM=I/A_total - BG": (math.pi * R ** 4 / 4) / (4.0 / 3.0 * math.pi * R ** 3) - abs(st3["KB_from_centre"]),
        "GM_half_draught_with_BG_from_keel_mis_set": -0.125,
        "reported_by_producer": -0.115,
        "nearest_standard_variant_gap": abs(-0.125 - (-0.115)),
    }

    out = {
        "report_id": "611",
        "source_sha256": "sha256:" + sha,
        "source_sha256_matches_contract": sha == EXPECTED_SHA,
        "parameters_recomputed_from_report": {
            "R": R, "rho_i": RHO_I, "rho_w": RHO_W, "g": G,
            "wave_A": WAVE_A, "wave_lambda": WAVE_LAMBDA, "wave_T": WAVE_T,
        },
        "quotes": quote_rows,
        "quotes_all_found": all(q["found"] for q in quote_rows),
        "geometry_and_equilibrium": {
            "target_f_sub": target_f,
            "h_eq_2d": h2,
            "h_eq_3d": h3,
            "f_sub_at_h2": fsub_2d(h2),
            "f_sub_at_h3": fsub_3d(h3),
            "report_h_eq_2d": -0.3378,
            "report_h_eq_3d": -0.2986,
            "report_f_sub": 0.8946,
            "h_eq_2d_rel_diff": abs(abs(h2) - 0.3378) / abs(h2),
            "h_eq_3d_rel_diff": abs(abs(h3) - 0.2986) / abs(h3),
            "sign_convention": "report quotes h_eq as a negative centre height (below waterline); recomputation uses depth>0",
        },
        "buoyancy": {
            "Fb_2d_N_per_m": fb2,
            "Fb_3d_N": fb3,
            "weight_2d_N_per_m": w2,
            "weight_3d_N": w3,
            "equilibrium_residual_2d": abs(fb2 - w2) / w2,
            "equilibrium_residual_3d": abs(fb3 - w3) / w3,
            "report_buoyancy_rel_error": {"2d": 2.15e-16, "3d": 2.19e-16},
            "independent_reference_rel_errors": ref,
        },
        "stability": {
            "2d": {**st2, "report_k_heave": 7414.0, "report_GM": 0.0},
            "3d": {**st3, "report_k_heave": 5081.0, "report_GM": -0.115},
            "k_heave_rel_diff_2d": abs(st2["k_heave"] - 7414.0) / 7414.0,
            "k_heave_rel_diff_3d": abs(st3["k_heave"] - 5081.0) / 5081.0,
            "GM_abs_diff_2d": abs(st2["GM"] - 0.0),
            "GM_abs_diff_3d": abs(st3["GM"] - (-0.115)),
            "GM_max_abs_over_draught_grid_2d": max(abs(r["GM"]) for r in gm_scan(2, 121)),
            "GM_max_abs_over_draught_grid_3d": max(abs(r["GM"]) for r in gm_scan(3, 121)),
            "GM_hypotheses_3d": hyps,
        },
        "GM_identity": gm_identity_proof(),
        "wave_consistency": wave,
        "verdict_inputs": {},
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(json.dumps({k: out[k] for k in (
        "source_sha256_matches_contract", "quotes_all_found",
        "geometry_and_equilibrium", "stability", "wave_consistency")},
        indent=2, ensure_ascii=False)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))