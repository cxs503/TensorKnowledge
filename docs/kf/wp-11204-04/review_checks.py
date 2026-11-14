#!/usr/bin/env python3
"""wp-11204-04 · independent review checks for report 11204.

Red-team recomputation over the frozen source copy (`source/report_11204.md`) and the
upstream registration package (`source/upstream_wp-11204-01.kf_result.json`).

Nothing here reads the producer's explanation: the only inputs are the report markdown
(byte-frozen, hash pinned to the work-package contract) and the upstream 01 artefact.
Every check is a pure function of those bytes, so the recorded pass/fail map can be
reproduced with `python docs/kf/wp-11204-04/review_checks.py`.

Emits `checks/independent_checks.json`.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

PKG = Path(__file__).resolve().parent
SOURCE = PKG / "source" / "report_11204.md"
UPSTREAM = PKG / "source" / "upstream_wp-11204-01.kf_result.json"
OUT = PKG / "checks" / "independent_checks.json"

CONTRACT_HASH = "sha256:d22a30cc692b82f2acf6ea669fd898a330143436344e4091c4a39c06a5292f86"
CONTRACT_CHARS = 5999
REPORT_ID = "11204"

# geometry / material constants as stated in the report (SI, verbatim-sourced in checks)
CT = dict(W=0.050, B=0.025, a_over_W=0.50, E=200e9, nu=0.3, P_report=34725.0)
SEB = dict(W=0.025, B=0.025, a_over_W=0.50, S=0.100, E=200e9, nu=0.3, P_report=7782.0)
COH = dict(K_n=1e16, t_n0=600e6, G_Ic=2000.0)


# --------------------------------------------------------------------------- helpers
def sha256_text(t: str) -> str:
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


def line_of(md: str, needle: str) -> int:
    """1-based line number of the first line containing `needle` (0 if absent)."""
    for i, ln in enumerate(md.split("\n"), 1):
        if needle in ln:
            return i
    return 0


def cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def find_row(md: str, prefix: str) -> list[str]:
    for ln in md.split("\n"):
        if ln.strip().startswith("|") and prefix in ln:
            return cells(ln)
    raise KeyError(prefix)


def pct(ours: float, ref: float) -> float:
    return (ours - ref) / ref * 100.0


def rel_pct(p: float) -> str:
    return f"{p:+.3f}%"


# ------------------------------------------------------------------ reference physics
def ct_f(alpha: float) -> float:
    """ASTM E399 compact-tension geometry factor f(a/W)."""
    num = 2.0 + alpha
    den = (1.0 - alpha) ** 1.5
    poly = (0.886 + 4.64 * alpha - 13.32 * alpha**2 + 14.72 * alpha**3 - 5.6 * alpha**4)
    return num / den * poly


def seb_f(alpha: float) -> float:
    """ASTM E399 single-edge-notched bend geometry factor f(a/W)."""
    poly = 1.99 - alpha * (1.0 - alpha) * (2.15 - 3.93 * alpha + 2.7 * alpha**2)
    return 3.0 * alpha**0.5 / (2.0 * (1.0 + 2.0 * alpha) * (1.0 - alpha) ** 1.5) * poly


def ct_K(P: float, g=CT) -> float:
    return P / (g["B"] * math.sqrt(g["W"])) * ct_f(g["a_over_W"])


def seb_K(P: float, g=SEB) -> float:
    # ASTM E399 SE(B), S = 4W:  K = P S / (B W^{3/2}) * f(a/W)
    return P * g["S"] / (g["B"] * g["W"] ** 1.5) * seb_f(g["a_over_W"])


def lefm_J(K: float, E: float, nu: float) -> float:
    return K * K * (1.0 - nu**2) / E


def implied_load(J: float, which: str) -> float:
    """Back out the load level at which a reported elastic J was evaluated."""
    K = math.sqrt(J * CT["E"] / (1.0 - CT["nu"] ** 2))
    g = CT if which == "CT" else SEB
    f = ct_f(g["a_over_W"]) if which == "CT" else seb_f(g["a_over_W"])
    if which == "CT":
        return K * g["B"] * math.sqrt(g["W"]) / f
    return K * g["B"] * g["W"] ** 1.5 / (g["S"] * f)


def bk_Gc(phase_deg: float) -> float:
    """Extended BK with the parameters the report's own table encodes
    (G_Ic=200, G_shear,c=600 at 90 deg, eta=1.5)."""
    s2 = math.sin(math.radians(phase_deg)) ** 2
    return 200.0 + (600.0 - 200.0) * s2**1.5


# --------------------------------------------------------------------------- checks
def run() -> dict:
    md = SOURCE.read_text(encoding="utf-8")
    lines = md.split("\n")
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    checks: dict[str, dict] = {}

    def rec(cid, title, ok, detail, **extra):
        checks[cid] = {"title": title, "pass": bool(ok), "detail": detail, **extra}

    # C1 — the bytes under review are the contracted bytes
    h = sha256_text(md)
    rec("C1_source_hash", "source markdown hash == work-package contract hash",
        h == CONTRACT_HASH and len(md) == CONTRACT_CHARS,
        f"recomputed {h} chars={len(md)} vs contract {CONTRACT_HASH} chars={CONTRACT_CHARS}",
        recomputed=h)

    # C2 — upstream 01 registration exists and pins the same bytes
    up_hash = upstream.get("provenance", {}).get("source_hash")
    ok_up = (upstream.get("package_id") == "wp-11204-01"
             and upstream.get("task_type") == "01-asset-registration"
             and upstream.get("report_id") == REPORT_ID
             and up_hash == h)
    rec("C2_upstream_pinned", "upstream wp-11204-01 registered the same source bytes",
        ok_up,
        f"package={upstream.get('package_id')} producer={upstream.get('provenance',{}).get('producer')} hash={up_hash}")

    # C3 — every quoted numeric token is a verbatim substring of the markdown
    anchors = {
        "ct_peak": "P_fem=34689 N vs ASTM P_Q=34725 N",
        "ct_peak_row": "| CT 峰值载荷 [N] | 34689 | ASTM E399 P_Q = 34725 | -0.104% |",
        "ct_J_el_row": "| CT 弹性 J [J/m²] | 1957.7 | K²(1−ν²)/E = 1956.1 | +0.081% |",
        "ct_J_pl_row": "| CT 弹塑性 J [J/m²] | 60485 | E1820 η 法 = 57036 | +6.047% |",
        "seb_J_row": "| SE(B) J [J/m²] | 136.34 | K²(1−ν²)/E = 132.11 | +3.202% |",
        "seb_peak_row": "| SE(B) 粘聚区峰值载荷 [N] | 7674 | LEFM = 7782 | -1.385% |",
        "eta_pl": "eta_pl = 2 + 0.522(1-a/W)",
        "delta_ratio": "delta_0/delta_f = 0.009",
        "ligament": "约 0.5 mm，远小于韧带 12.5 mm",
        "bk_row45": "| 45 | 341.42 | 341.42 | 340.45 | -0.283% |",
        "jpl_ratio": "J_pl/J = 0.191",
        "half_model": "实测 J 偏小 50%（CT）/ 82%（SE(B)）",
        "kn_init": "初版取 K_n = 1e14 时峰值载荷偏低 58%",
        "pytest_s": "pytest 40 项 19 s 全绿",
    }
    missing = {k: v for k, v in anchors.items() if v not in md}
    rec("C3_anchors_verbatim", "all review anchors are verbatim substrings of the source",
        not missing, f"missing={sorted(missing)}", anchors=anchors,
        anchor_lines={k: line_of(md, v) for k, v in anchors.items()})

    # C4 — the paired numbers reproduce the declared relative errors
    pairs = [
        ("ct_peak_load", 34689.0, 34725.0, -0.104),
        ("ct_J_elastic", 1957.7, 1956.1, +0.081),
        ("ct_J_elastoplastic", 60485.0, 57036.0, +6.047),
        ("seb_J", 136.34, 132.11, +3.202),
        ("seb_peak_load", 7674.0, 7782.0, -1.385),
    ]
    arith = {}
    worst = 0.0
    for name, ours, ref, declared in pairs:
        got = pct(ours, ref)
        arith[name] = {"recomputed_pct": round(got, 4), "declared_pct": declared,
                       "gap_pp": round(got - declared, 4)}
        worst = max(worst, abs(got - declared))
    rec("C4_table_arithmetic", "declared relative errors == (ours-ref)/ref within 0.005 pp",
        worst <= 0.005, f"worst gap {worst:.4f} pp", table=arith)

    # C5 — extended BK law reproduces the report's analytic column
    bk = {}
    bk_ok = True
    for ph in (0, 15, 30, 45, 60, 75, 90):
        row = find_row(md, f"| {ph} |")
        analytic = float(row[1])
        got = bk_Gc(ph)
        ok = abs(got - analytic) <= 0.05
        bk_ok &= ok
        bk[str(ph)] = {"declared": analytic, "recomputed": round(got, 4), "ok": ok}
    rec("C5_bk_law", "extended-BK analytic column reproduces with eta=1.5, G_IIc=600, G_IIIc=800",
        bk_ok, "recomputed 0..90 deg from G_Ic=200, G_shear,c=600, eta=1.5", series=bk)

    # C6 — cohesive input self-consistency (delta_0/delta_f and K >> sigma^2/2G)
    d0 = COH["t_n0"] / COH["K_n"]
    df = 2.0 * COH["G_Ic"] / COH["t_n0"]
    ratio = d0 / df
    stiffness_margin = COH["K_n"] / (COH["t_n0"] ** 2 / (2.0 * COH["G_Ic"]))
    rec("C6_cohesive_selfconsistent",
        "cohesive inputs satisfy the report's own delta_0/delta_f = 0.009 and K >> sigma^2/2G",
        abs(ratio - 0.009) < 5e-4 and stiffness_margin > 100,
        f"delta_0/delta_f={ratio:.5f} (declared 0.009); K/(sigma^2/2G_Ic)={stiffness_margin:.1f}x")

    # C7 — LEFM recomputation at the *stated* peak loads vs the reported elastic J
    #      (this is the probe that exposes the unstated evaluation load)
    P_impl_ct = implied_load(1957.7, "CT")
    P_impl_seb = implied_load(132.11, "SEB")
    J_ct_at_peak = lefm_J(ct_K(CT["P_report"]), CT["E"], CT["nu"])
    J_seb_at_baseline = lefm_J(seb_K(SEB["P_report"]), SEB["E"], SEB["nu"])
    ratios = {"CT": P_impl_ct / CT["P_report"], "SEB": P_impl_seb / SEB["P_report"]}
    consistent = all(0.8 < r < 1.25 for r in ratios.values())
    rec("C7_elastic_J_load_level",
        "reported elastic J corresponds to the stated peak load (ASTM E399 K + J=K^2(1-nu^2)/E)",
        consistent,
        ("reported J is not attainable at the documented peak load: implied P is "
         f"{P_impl_ct:,.0f} N (CT, {ratios['CT']:.3f}x of P_Q={CT['P_report']:,.0f} N) and "
         f"{P_impl_seb:,.0f} N (SE(B), {ratios['SEB']:.3f}x of LEFM peak={SEB['P_report']:,.0f} N)"),
        implied_load_N={"CT": round(P_impl_ct, 1), "SEB": round(P_impl_seb, 1)},
        lefm_J_at_stated_peak={"CT": round(J_ct_at_peak, 1), "SEB": round(J_seb_at_baseline, 1)},
        reported_J={"CT_elastic": 1957.7, "SEB": 132.11},
        geometry_factors={"CT_f(0.5)": round(ct_f(0.5), 4), "SEB_f(0.5)": round(seb_f(0.5), 4)})

    # C8 — the same quantity must carry the same sign in every place it appears
    signs = {}
    for label, pat in (("C1_CT_peak", r"\+0\.104%"), ("C1b_SEB_peak", r"\+1\.385%")):
        signs[label] = {"plus_hits": len(re.findall(pat, md)),
                        "minus_hits": len(re.findall(pat.replace("\\+", "-"), md))}
    rec("C8_sign_consistency",
        "error signs agree between the criterion table and the data tables",
        all(v["plus_hits"] == 0 or v["minus_hits"] == 0 for v in signs.values()),
        "+0.104% (criterion table) coexists with -0.104% (data tables); "
        "+1.385% with -1.385%/-1.38%", occurrences=signs)

    # C9 — criterion table: every row's verdict follows from value vs threshold
    crit = {}
    crit_ok = True
    for ln in md.split("\n"):
        if not ln.strip().startswith("| C"):
            continue
        c = cells(ln)
        if len(c) < 5 or not re.fullmatch(r"\|*\s*[+-]?[\d.]+%?", c[1]):
            continue
        val = float(c[1].replace("%", "").replace("+", ""))
        thr = float(c[2].strip("<>% "))
        verdict = c[3]
        ok = (verdict == "PASS") == (abs(val) < thr)
        crit_ok &= ok
        crit[c[0]] = {"value_pct": val, "threshold_pct": thr, "declared": verdict, "ok": ok}
    rec("C9_criterion_verdicts", "each PASS verdict follows from |value| < threshold",
        crit_ok and len(crit) == 6, f"{len(crit)} criterion rows", rows=crit, n_rows=len(crit))

    # C10 — mesh-convergence table: monotone decrease claimed for SE(B)
    seb_err, ct_err, n_rows = [], [], 0
    for ln in md.split("\n"):
        if re.match(r"^\| \d+ \| \d+ \| [+-]?[\d.]+% \| \d+×\d+ \| \d+ \| [+-]?[\d.]+% \|$", ln.strip()):
            c = cells(ln)
            n_rows += 1
            ct_err.append(float(c[2].rstrip("%")))
            seb_err.append(float(c[5].rstrip("%")))
    mono = all(b < a for a, b in zip(seb_err, seb_err[1:]))
    rec("C10_mesh_monotonicity", "SE(B) J error decreases monotonically over the reported mesh ladder",
        mono and n_rows == 5, f"SE(B) series {seb_err}; CT series {ct_err}")

    # C11 — no verification assertion anywhere in the review payload
    forbidden = {"verified", "verification_status", "verification_level", "is_verified"}
    bag = []
    for p in (PKG / "review_report.json", PKG / "kf_result.json"):
        if p.exists():
            txt = p.read_text(encoding="utf-8")
            bag += [k for k in forbidden if f'"{k}"' in txt]
    rec("C11_no_self_verification", "review payload sets no verification field",
        not bag, f"offending keys {sorted(set(bag))}")

    # C12 — process-anecdote numbers have no backing table (evidence gap, not error)
    tokens = ["50%", "82%", "58%"]
    table_rows = [ln for ln in md.split("\n") if ln.strip().startswith("|")]
    in_table = {t: sum(1 for ln in table_rows if t in ln) for t in tokens}
    rec("C12_anecdote_evidence", "process-anecdote numbers (-50%/-82%/58%) carry a results table",
        any(in_table.values()),
        "prose-only percentages: " + ", ".join(sorted(t for t, n in in_table.items() if n == 0)),
        occurrences_in_table_rows=in_table)

    # C13 — the honest-FAIL table (section 6) must agree with the arithmetic
    sec6 = {}
    sec6_ok = True
    for ln in md.split("\n"):
        if not ln.strip().startswith("| ") or "%" not in ln:
            continue
        c = cells(ln)
        if len(c) != 4 or not re.fullmatch(r"[+-][\d.]+%", c[2]):
            continue
        val = abs(float(c[2].rstrip("%")))
        yes = c[3] == "是"
        ok = (abs(val) < 3.0) == yes
        sec6_ok &= ok
        sec6[c[0]] = {"abs_pct": val, "declared_lt3pct": c[3], "ok": ok}
    rec("C13_lt3pct_verdicts", "section-6 '<3%?' answers agree with the quoted percentages",
        sec6_ok and len(sec6) == 6, f"{len(sec6)} rows adjudicated", rows=sec6, n_rows=len(sec6))

    passed = sum(1 for c in checks.values() if c["pass"])
    out = {
        "package_id": "wp-11204-04",
        "report_id": REPORT_ID,
        "source_hash_recomputed": h,
        "generated_by": "docs/kf/wp-11204-04/review_checks.py",
        "checks": checks,
        "summary": {"n_checks": len(checks), "n_pass": passed,
                    "n_finding": len(checks) - passed,
                    "failing": sorted(k for k, v in checks.items() if not v["pass"])},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    res = run()
    s = res["summary"]
    print(f"wp-11204-04 checks: {s['n_pass']}/{s['n_checks']} pass; failing={s['failing']}")
    for cid, c in res["checks"].items():
        print(f"  [{'PASS' if c['pass'] else 'FIND'}] {cid}: {c['detail']}")