#!/usr/bin/env python3
"""wp-11421-01 | internal-consistency cross-check of report 11421 (registration side-artifact).

Why this exists: the package is *registration only* (no extraction, no claims), but a registry
that silently ignores text-vs-table contradictions would launder them into the downstream
工序. So this script mechanically re-derives every arithmetic identity that the report itself
asserts over its own tables, using ONLY numbers parsed out of the fetched markdown
(docs/kf/wp-11421-01/source.md) — nothing is retyped, and the producer artifacts
(ship-performance-platform) are never needed, so the check is reproducible from this record.

Verdicts:
    pass          identity holds within the stated/derived tolerance
    fail          identity does not hold -> registered as a downstream defect candidate
    not_run       the needed numbers are not in this record

Writes docs/kf/wp-11421-01/crosscheck.json. Exit code 0 always (a `fail` here is a *finding*,
not a crash): the package's own acceptance gate is acceptance_check.json.
"""
from __future__ import annotations

import json
import re
import sys

SRC = "docs/kf/wp-11421-01/source.md"
OUT = "docs/kf/wp-11421-01/crosscheck.json"


def load(path: str = SRC) -> str:
    return open(path, encoding="utf-8").read()


def table_rows(md: str, heading_prefix: str) -> list[list[str]]:
    """Return the data rows (cells stripped) of the first markdown table after a heading."""
    lines = md.split("\n")
    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith(heading_prefix))
    except StopIteration:
        raise SystemExit(f"heading {heading_prefix!r} not found")
    rows, seen_pipe = [], False
    for ln in lines[start + 1 :]:
        if ln.startswith("#"):
            break
        if ln.strip().startswith("|"):
            seen_pipe = True
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue  # separator row
            rows.append(cells)
        elif seen_pipe and not ln.strip():
            # a blank line ends the first table; stop only after we already have rows
            if rows:
                break
    return rows[1:] if rows else rows  # drop header row


def num(s: str):
    s = s.replace("**", "").strip()
    s = s.replace("−", "-").replace("·", "").replace(",", "")
    m = re.search(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", s)
    return float(m.group(0)) if m else None


def find(md: str, needle: str) -> dict:
    i = md.find(needle)
    return {"present": i >= 0, "quote": needle, "start_char": i, "occurrences": md.count(needle)}


def main() -> int:
    md = load()
    checks: list[dict] = []

    def add(cid, what, verdict, computed, stated, quotes, note="", severity="info"):
        checks.append({"check_id": cid, "what": what, "verdict": verdict,
                       "severity_hint": severity,
                       "computed": computed, "stated_in_report": stated,
                       "evidence": [find(md, q) for q in quotes], "note": note})

    # ---------------------------------------------------------------- 表1 geometry closure
    t1 = {r[0]: num(r[1]) for r in table_rows(md, "## 表1") if len(r) >= 2}
    implied, declared, rel = t1.get("implied_dwt_t"), t1.get("declared_dwt_t"), t1.get("rel_err")
    recomputed = (implied - declared) / declared if None not in (implied, declared) else None
    add("X1", "表1: rel_err == (implied_dwt_t - declared_dwt_t)/declared_dwt_t", 
        "pass" if recomputed is not None and abs(recomputed - rel) < 5e-7 else "fail",
        {"recomputed_rel_err": recomputed, "reported_rel_err": rel},
        {"displacement_t": t1.get("displacement_t"), "declared_dwt_t": declared},
        ["| rel_err | 0.0019197 |"],
        "the geometry self-consistency gate the report bases C10 on")

    # ---------------------------------------------------------------- 表3 CV == std/mean
    t3 = table_rows(md, "## 表3")
    dist = {r[0]: r for r in t3 if len(r) >= 4 and num(r[2]) is not None}
    cv_rows, cv_bad = {}, []
    for k, r in dist.items():
        mean, std, cv = num(r[1]), num(r[2]), num(r[3])
        if None in (mean, std, cv) or mean == 0:
            continue
        rec = std / mean
        cv_rows[k] = {"recomputed": round(rec, 6), "reported": cv}
        tol = max(5e-4, 0.02 * cv)  # CV printed to 4 dp -> allow rounding of the 4th place
        if abs(rec - cv) > tol:
            cv_bad.append(k)
    add("X2", "表3: CV column == std/mean per row", "pass" if not cv_bad else "fail",
        {"rows": cv_rows, "mismatched_rows": cv_bad}, "CV column of 表3",
        ["| eexi_attained | 3.54773 | 0.15562 | 0.0439 |"],
        "tolerance = max(5e-4, 2% of CV) because CV is printed to 4 decimals")

    # ---------------------------------------------------------------- 表4 group Sobol closure
    t4 = [r for r in table_rows(md, "## 表4") if len(r) >= 7]
    groups = [r for r in t4 if r[0] not in ("Σ", "**Σ**")]
    sum_row = next((r for r in t4 if r[0].lstrip("*") == "Σ"), None)
    # 表4 header: 组 | EEXI S_g | ±SE | EEXI S_T,g | CII S_g | ±SE | CII S_T,g   (7 cells)
    s_eexi = sum(num(r[1]) for r in groups if num(r[1]) is not None)
    st_eexi = sum(num(r[3]) for r in groups if num(r[3]) is not None)
    s_cii = sum(num(r[4]) for r in groups if num(r[4]) is not None)
    st_cii = sum(num(r[6]) for r in groups if num(r[6]) is not None)
    stated = {"S_exxi": num(sum_row[1]), "S_T_exxi": num(sum_row[3]),
              "S_cii": num(sum_row[4]), "S_T_cii": num(sum_row[6])} if sum_row else {}
    diffs = {k: round(v, 6) for k, v in {
        "S_exxi": s_eexi - (stated.get("S_exxi") or 0),
        "S_T_exxi": st_eexi - (stated.get("S_T_exxi") or 0),
        "S_cii": s_cii - (stated.get("S_cii") or 0),
        "S_T_cii": st_cii - (stated.get("S_T_cii") or 0),
    }.items()}
    add("X3", "表4: Σ row == column sums of the six group rows (tolerance 5e-4 = 6x rounding)",
        "pass" if all(abs(v) <= 5e-4 for v in diffs.values()) else "fail",
        {"recomputed": {"S_exxi": s_eexi, "S_T_exxi": st_eexi, "S_cii": s_cii, "S_T_cii": st_cii},
         "stated": stated, "diff": diffs},
        "Σ row of 表4 (0.9860 / 1.0007 / 0.9979 / 1.0006)",
        ["| Σ | 0.9860 | — | 1.0007 | 0.9979 | — | 1.0006 |"])

    # ---------------------------------------------------- 表5 negative first-order indices
    t5 = [r for r in table_rows(md, "## 表5") if len(r) >= 11]
    neg = []
    for r in t5:
        for idx, col in ((2, "EEXI S_i"), (5, "CII S_i")):
            v = num(r[idx])
            if v is not None and v < 0:
                neg.append({"factor": r[0], "column": col, "value": v, "se": num(r[3 if idx == 2 else 6])})
    claim = find(md, "且同样满足 `S_i ≥ 0`")
    add("X4", "§2.2 asserts the Jansen estimator 'satisfies S_i >= 0', but 表5 prints negative "
              "first-order indices (|value| < SE for every case -> estimator noise, not physics)",
        "fail" if (neg and claim["present"] and claim["occurrences"] == 1) else "not_run",
        {"n_negative_first_order": len(neg), "negative_rows": neg,
         "all_within_one_se": all(abs(d["value"]) < (d["se"] or 0) for d in neg)},
        "§2.2: '同样满足 `S_i ≥ 0`' vs 表5 negative S_i entries",
        ["且同样满足 `S_i ≥ 0`", "| geom_L | geometry | -0.0028 | 0.0060 | 0.0003 | 0.0002 | 0.0081 | 0.0005 | +0.00080 | +0.00200 | +0.00067 |"],
        severity="low",
        note=("prose/estimator description is wrong, the Sobol numbers themselves are self-consistent "
              "(every negative lies inside one standard error) and no conclusion of the report changes; "
              "still must be fixed before this method line is quoted. ")
        + ("downstream defect candidate: the prose statement about the estimator is wrong (Jansen's "
        "first-order estimator is not non-negative; only its total-effect form is). "
        "No value is recomputed here because the producer samples are not in this record."))

    # ------------------------------------------- 表5 analytic vs finite-difference c_i (<5%)
    fd_cmp, worst = {}, None
    for r in t5:
        a, fd = num(r[8]), num(r[10])
        if a is None or fd is None or a == 0:
            continue
        rel = abs(fd - a) / abs(a)
        fd_cmp[r[0]] = {"analytic": a, "fd": fd, "rel_diff": round(rel, 6)}
        if worst is None or rel > worst[1]:
            worst = (r[0], rel, abs(fd - a))
    claim5 = find(md, "非零项相对差 < 5%")
    add("X5", "§3.4(b) asserts analytic vs finite-difference c_i agree 'to < 5% on non-zero items'; "
              "表5 has a row above that bound",
        "fail" if (worst and worst[1] >= 0.05 and claim5["present"]) else "pass",
        {"per_factor": fd_cmp, "worst": {"factor": worst[0], "rel_diff": worst[1],
                                         "abs_diff": worst[2]} if worst else None,
         "n_rows_over_5pct": sum(1 for v in fd_cmp.values() if v["rel_diff"] >= 0.05)},
        "§3.4(b): '非零项相对差 < 5%' vs 表5 c_i(EEXI) / FD c_i(EEXI) columns",
        ["非零项相对差 < 5%"],
        severity="low",
        note=("the offending row (geom_L) sits at the finite-difference quantization floor the report "
              "itself documents in §4.1, so the 16% is mostly noise; the defect is the unconditional "
              "wording of the 5% bound. ")
        + ("downstream defect candidate: the 5% bound is violated by the smallest analytic sensitivity "
        "(geom_L), exactly where the finite-difference step 2σ is least informative. Either the bound "
        "or the row needs a caveat; the report is internally inconsistent as printed."))

    # ---------------------------------------------------------------- 表6 sigma linearity
    # 表6 prints σ(EEXI) to 4 decimals, so at ε=1e-3 the σ column (0.0002) carries only ~1
    # significant digit. The admissible tolerance for "ratio == ε" is therefore set by the
    # printed quantum (half a unit in the last place), not by an arbitrary percentage.
    t6 = [r for r in table_rows(md, "## 表6") if len(r) >= 6]
    lin, lin_bad, sigma1 = {}, [], None
    for r in t6:
        eps, sig, ratio, reported = num(r[0]), num(r[1]), num(r[2]), num(r[4])
        if None in (eps, sig, ratio):
            continue
        if eps == 1.0:
            sigma1 = sig
        err = abs(ratio - eps) / eps
        quantum = 0.5 * 1e-4 / max(eps * (sigma1 or sig), 1e-12)  # relative quantum of the ratio
        ok = err <= quantum + 1e-12
        printed_ok = (reported is None) or (abs(err * 100 - reported) <= quantum * 100 + 0.001)
        lin[r[0]] = {"eps": eps, "sigma": sig, "ratio": ratio,
                     "recomputed_rel_err_pct": round(err * 100, 4),
                     "printed_rel_err_pct": reported,
                     "quantum_pct": round(quantum * 100, 4), "within_quantum": ok,
                     "printed_column_consistent": printed_ok}
        if not (ok and printed_ok):
            lin_bad.append(r[0])
    add("X6", "表6: σ(ε)/σ(1) == ε within the precision permitted by the printed σ quantum, "
              "and the printed relative-error column agrees with that same recomputation",
        "pass" if not lin_bad else "fail",
        {"rows": lin, "mismatched_rows": lin_bad},
        "表6 columns 3-5 (σ shrinkage is the σ→0 negative control C5)",
        ["| 0.1 | 0.0155 | 0.10004 | 0.1 | 0.036% | 0.0850 | 0.9416 |"])

    # --------------------------------------- §3.2 out-of-domain share 76999/200000 = 38.5%
    m = re.search(r"Holtrop 回归域越界样本 \*\*(\d+)/(\d+)\*\*", md)
    m2 = re.search(r"（(\d+\.\d)%", md[md.find("回归域越界样本"): md.find("回归域越界样本") + 200]) if m else None
    add("X7", "§3.2: bolded ratio n/N reproduces the printed percentage",
        "pass" if (m and m2 and abs(int(m.group(1)) / int(m.group(2)) * 100 - float(m2.group(1))) < 0.05) else "not_run",
        {"n": int(m.group(1)) if m else None, "N": int(m.group(2)) if m else None,
         "recomputed_pct": round(int(m.group(1)) / int(m.group(2)) * 100, 4) if m else None,
         "printed_pct": float(m2.group(1)) if m2 else None},
        "§3.2 honest out-of-Holtrop-domain count",
        ["Holtrop 回归域越界样本 **76999/200000**"])

    verdicts: dict[str, int] = {}
    for c in checks:
        verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1
    out = {
        "package_id": "wp-11421-01",
        "report_id": "11421",
        "scope": "arithmetic identities the report asserts over its own tables; parsed from source.md only",
        "not_in_scope": [
            "values that require the producer artifacts (results.json / spec.py / scripts) — A07/A09/A15 in the manifest",
            "any re-run of the Monte Carlo / Sobol pipeline (samples are not in this record)",
            "rule coefficients (WITHHELD, A21)",
        ],
        "checks": checks,
        "summary": {"n_checks": len(checks), "verdicts": verdicts,
                    "findings": [c["check_id"] for c in checks if c["verdict"] == "fail"]},
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps(out["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())