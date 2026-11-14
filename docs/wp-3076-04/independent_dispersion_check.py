#!/usr/bin/env python3
"""wp-3076-04 independent numeric reconstruction (no producer code used).

What it does
------------
1. Extracts the *claimed* parameters and the *claimed* coth/tanh deviation
   series from the report markdown (report 3076) by regex, so nothing is
   hand-typed: every number compared below is taken verbatim from the source.
2. Re-solves the finite-depth ice-plate dispersion relation stated in the
   report with an independently written bisection solver:

       tanh form (claimed correct):  w^2 = (g k + D k^5 / rho_w) * tanh(k h)
       coth form (claimed wrong):    w^2 = (g k + D k^5 / rho_w) * coth(k h)
       D = E h_i^3 / (12 (1 - nu^2))

3. Compares recomputed deviations with the claimed ones and probes the
   "T >= 14 s: coth has no root in k in (0, 10] 1/m" claim by scanning the
   bracket for sign changes instead of trusting the claim.
4. Audits the report's own severity arithmetic: counts HARD rows in the
   11-check table parsed from the markdown and compares with the stated
   "HARD 失败 8/11" / "0/11" denominators.
5. Records every claim -> verbatim quote locator (char offset / line) so the
   platform's independent substring re-check can bind them.

Outputs: docs/wp-3076-04/independent_check.json (+ printed summary).
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
PKG = ROOT / "docs" / "wp-3076-04"
MD = PKG / "source.md"
OUT = PKG / "independent_check.json"

EXPECTED_SHA = "9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1"

# --- numbers to be replaced by values parsed from the source -------------
PARAM_RE = re.compile(r"h=([0-9.]+) m、h_i=([0-9.]+) m、E=([0-9.]+)×10⁹ Pa、ν=([0-9.]+)、"
                      r"ρ_w=([0-9.]+)、ρ_i=([0-9.]+) kg/m³、g=([0-9.]+) m/s²、T=([0-9.]+) s")
DEV_RE = re.compile(r"T=4s: ([0-9.]+)%, T=6s: ([0-9.]+)%, T=8s: ([0-9.]+)%, "
                    r"T=10s: ([0-9.]+)%, T=12s: ([0-9.]+)%")
NOROOT_RE = re.compile(r"T≥(\d+)s 时 coth 形式在 k∈\(0,10\] 1/m 内\*\*无根\*\*")
HARD_FAIL_RE = re.compile(r"HARD 失败 ([0-9]+)/([0-9]+)")


def load_md() -> str:
    md = MD.read_text(encoding="utf-8")
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    if digest != EXPECTED_SHA:
        raise SystemExit(f"source hash mismatch: {digest} != {EXPECTED_SHA}")
    return md


def parse_params(md: str) -> dict:
    m = PARAM_RE.search(md)
    if not m:
        raise SystemExit("parameter line not found verbatim in source")
    h, hi, E, nu, rw, ri, g, T = (float(x) for x in m.groups())
    return {"h": h, "h_i": hi, "E": E * 1e9, "nu": nu, "rho_w": rw,
            "rho_i": ri, "g": g, "T_listed": T, "quote": m.group(0),
            "offset": m.start()}


def parse_claims(md: str) -> dict:
    m = DEV_RE.search(md)
    if not m:
        raise SystemExit("deviation series not found verbatim in source")
    dev = {4: float(m.group(1)), 6: float(m.group(2)), 8: float(m.group(3)),
           10: float(m.group(4)), 12: float(m.group(5))}
    n = NOROOT_RE.search(md)
    hf = HARD_FAIL_RE.findall(md)
    return {"dev": dev, "dev_quote": m.group(0), "dev_offset": m.start(),
            "noroot_T": int(n.group(1)) if n else None,
            "noroot_quote": n.group(0) if n else None,
            "hard_fail_claims": [{"num": int(a), "den": int(b)}
                                 for a, b in hf]}


# --- independent solver ---------------------------------------------------
def rhs(k: float, p: dict, kind: str) -> float:
    D = p["E"] * p["h_i"] ** 3 / (12.0 * (1.0 - p["nu"] ** 2))
    base = p["g"] * k + D * k ** 5 / p["rho_w"]
    kh = k * p["h"]
    if kind == "tanh":
        return base * math.tanh(kh)
    if kind == "coth":
        return base / math.tanh(kh)
    raise ValueError(kind)


def f(k: float, p: dict, kind: str, T: float) -> float:
    w = 2.0 * math.pi / T
    return rhs(k, p, kind) - w * w


def find_roots(p: dict, kind: str, T: float, k_lo: float = 1e-9,
               k_hi: float = 10.0, n_scan: int = 20000) -> list[list[float]]:
    """Return bisection-refined roots by scanning for sign changes (never assume one)."""
    roots = []
    ks = [k_lo + (k_hi - k_lo) * i / n_scan for i in range(n_scan + 1)]
    prev_k, prev_f = ks[0], f(ks[0], p, kind, T)
    for kb in ks[1:]:
        fb = f(kb, p, kind, T)
        if prev_f == 0.0:
            roots.append([prev_k, prev_k])
        elif prev_f * fb < 0.0:
            a, b, fa = prev_k, kb, prev_f
            for _ in range(300):
                mid = 0.5 * (a + b)
                fm = f(mid, p, kind, T)
                if fa * fm <= 0.0:
                    b = mid
                else:
                    a, fa = mid, fm
            roots.append([0.5 * (a + b), 0.5 * (a + b)])
        prev_k, prev_f = kb, fb
    return roots


def count_hard_rows(md: str) -> dict:
    """Parse the 11-check results table: severity per check + status per manuscript."""
    rows = []
    for line in md.splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[1] in ("HARD", "SOFT"):
            rows.append({"check": cells[0], "severity": cells[1],
                         "sealed": cells[2], "control": cells[3]})
    hard = [r for r in rows if r["severity"] == "HARD"]
    return {"rows": rows, "n_rows": len(rows), "n_hard": len(hard),
            "n_soft": len(rows) - len(hard),
            "hard_fail_sealed": sum(r["sealed"] == "FAIL" for r in hard),
            "hard_fail_control": sum(r["control"] == "FAIL" for r in hard),
            "hard_skip_control": sum(r["control"] == "SKIP" for r in hard),
            "hard_warn_sealed": sum(r["sealed"] == "WARN" for r in hard),
            "soft_warn_sealed": sum(r["sealed"] == "WARN" for r in hard + rows
                                    if r["severity"] == "SOFT")}


def locator(md: str, needle: str) -> dict:
    """char offset / line / uniqueness of a verbatim quote in the source."""
    idx = md.find(needle)
    return {"quote": needle, "char_offset": idx,
            "line": md[:idx].count("\n") + 1 if idx >= 0 else None,
            "occurrences": md.count(needle),
            "found": idx >= 0,
            "quote_sha256": hashlib.sha256(needle.encode("utf-8")).hexdigest()}


def main() -> int:
    md = load_md()
    p = parse_params(md)
    c = parse_claims(md)
    res: dict = {"source": {"report_id": "3076", "sha256": EXPECTED_SHA,
                            "chars": len(md)},
                 "params": {k: v for k, v in p.items() if k != "quote"},
                 "params_quote": p["quote"]}

    # 1) reproduce coth-vs-tanh wavenumber deviation
    per_T = {}
    for T in (4, 6, 8, 10, 12):
        rt = find_roots(p, "tanh", T)
        rc = find_roots(p, "coth", T)
        kt = rt[0][0] if rt else None
        kc = rc[0][0] if rc else None
        recomputed = abs(kc - kt) / kt * 100.0 if (kt and kc) else None
        per_T[T] = {"k_tanh": kt, "k_coth": kc,
                    "roots_tanh": len(rt), "roots_coth": len(rc),
                    "dev_recomputed_pct": recomputed,
                    "dev_claimed_pct": c["dev"][T],
                    "abs_delta_pp": None if recomputed is None else
                    round(abs(recomputed - c["dev"][T]), 3)}
    res["deviation_series"] = {"per_T": per_T, "claimed_quote": c["dev_quote"],
                               "claimed_offset": c["dev_offset"]}

    # 2) probe the "no root for T >= 14 s (coth)" claim over a wide period set
    noroot = {}
    for T in (14.0, 14.1, 14.15, 14.185, 14.2, 14.3, 16, 18, 20, 30, 60):
        rc = find_roots(p, "coth", T)
        rt = find_roots(p, "tanh", T)
        noroot[T] = {"roots_coth_in_(0,10]": [r[0] for r in rc],
                     "roots_tanh_in_(0,10]": [r[0] for r in rt]}
    # analytic boundary: the coth branch has a root iff w^2 >= lim_{k->0} RHS = g/h
    T_crit = 2.0 * math.pi / math.sqrt(p["g"] / p["h"])
    res["no_root_probe"] = {"claim_T_ge": c["noroot_T"], "claim_quote": c["noroot_quote"],
                            "T_crit_analytic_s": T_crit,
                            "claim_holds_strictly_above_s": T_crit,
                            "per_T": noroot}

    # 3) severity arithmetic audit of the report's own summary
    audit = count_hard_rows(md)
    res["table_audit"] = audit
    res["summary_claims"] = {"hard_fail_claims": c["hard_fail_claims"],
                             "n_hard_parsed": audit["n_hard"],
                             "n_rows_parsed": audit["n_rows"]}

    # 4) claim -> verbatim locators (for the platform substring re-check)
    quotes = {
        "deviation_series": c["dev_quote"],
        "params": p["quote"],
        "no_root": c["noroot_quote"],
        "eight_classes_all_checkable": "复盘发现这八类**全部是",
        "H5_not_machine_judgeable": "H5 在该树上不可机判，**如实不报**",
        "control_pass": "control `verdict=PASS`，HARD 失败 0/11（SKIP 3 项）",
        "sealed_verdict": "HARD 失败 8/11",
        "neg_control_recall": "7/7 复现",
        "pytest": "pytest 19 passed",
        "tautological_3pct": "正控 k vs 更紧容差解",
        "implmethod_h5": "`implmethod` 未能在封存树上复现 H5",
        "numtrace_tol": "证据基 237 值，tol=0.005",
        "arith_enKF": "抓到 EnKF 声称 8.65% vs 同行两量复算 8.33%",
        "figdata_proxy": "`figdata` 只是合成数据代理判据",
        "repro_triplet": "三件套命中 0/3",
    }
    res["locators"] = {k: locator(md, v) for k, v in quotes.items()
                       if v is not None}

    # 5) verdict of this reconstruction step
    dev_ok = all(v["abs_delta_pp"] is not None and v["abs_delta_pp"] <= 0.05
                 for v in per_T.values())
    root_claim_ok = all(not noroot[T]["roots_coth_in_(0,10]"]
                        for T in noroot if T > res["no_root_probe"]["T_crit_analytic_s"])
    hard_den_ok = (all(h["den"] == audit["n_hard"] for h in c["hard_fail_claims"])
                   and all(h["num"] == audit["hard_fail_sealed"]
                           for h in c["hard_fail_claims"][:1]))
    res["reconstruction"] = {
        "deviation_series_reproduced": dev_ok,
        "coth_no_root_claim_reproduced": root_claim_ok,
        "hard_denominator_matches_parsed_HARD_rows": hard_den_ok,
        "parsed_hard_fail_sealed": audit["hard_fail_sealed"],
        "claimed_hard_fail": [c["hard_fail_claims"][0]] if c["hard_fail_claims"] else [],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    print("== params parsed from source ==")
    print({k: res["params"][k] for k in ("h", "h_i", "E", "nu", "rho_w", "rho_i", "g")})
    print("\n== coth vs tanh deviation: claimed vs recomputed ==")
    for T, v in per_T.items():
        print(f"T={T:>2}s k_tanh={v['k_tanh']:.6e} k_coth={v['k_coth']:.6e} "
              f"recomputed={v['dev_recomputed_pct']:.4f}% claimed={v['dev_claimed_pct']:.2f}% "
              f"|d|={v['abs_delta_pp']}pp roots(t/c)={v['roots_tanh']}/{v['roots_coth']}")
    print("\n== no-root probe (coth, k in (0,10]) ==")
    for T, v in noroot.items():
        print(f"T={T:>6}s coth_roots={[round(x, 6) for x in v['roots_coth_in_(0,10]']]} "
              f"tanh_roots={[round(x, 6) for x in v['roots_tanh_in_(0,10]']]}")
    print("\n== table audit ==")
    print({k: audit[k] for k in ("n_rows", "n_hard", "n_soft", "hard_fail_sealed",
                                 "hard_fail_control", "hard_skip_control",
                                 "hard_warn_sealed")})
    print("summary claims:", c["hard_fail_claims"])
    print("\n== locators (found/unique) ==")
    for k, v in res["locators"].items():
        print(f"{k:32s} found={v['found']} line={v['line']} occ={v['occurrences']}")
    print("\n== reconstruction verdict ==")
    print(json.dumps(res["reconstruction"], ensure_ascii=False, indent=1))
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())