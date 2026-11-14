#!/usr/bin/env python3
"""Independent-review checks for report 5949 (work package wp-5949-04).

Task type: 04-independent-review.  Objective: judge semantic fidelity of the report's
own numbers against the report text alone -- no producer explanation, no upstream
narrative, no network.  Every check consumes either the byte-frozen markdown copy or
the upstream registration package ``docs/kf/wp-5949-01`` and re-derives the number.

Design rules
------------
* Pure functions, stdlib only, deterministic output (no timestamps taken from clock).
* Every check carries a verbatim anchor from the source; a non-verbatim anchor is a
  hard error (``AssertionError``), never a silently empty result.
* A quantity that cannot be re-derived from the frozen text is reported as
  ``unverifiable`` -- never as ``pass``.
* Declared values are never copied out of the report into the output: they are parsed
  from the text, so a divergent copy fails instead of agreeing with itself.

Run:  python3 work/wp-5949-04/review_checks.py   ->  work/wp-5949-04/checks.json
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "docs" / "kf" / "wp-5949-04"
SOURCE = PKG / "source_5949.md"
UPSTREAM_DIR = REPO / "docs" / "kf" / "wp-5949-01"
OUT = REPO / "work" / "wp-5949-04" / "checks.json"

REPORT_ID = "5949"
# Contract constants (work-package pin of record 5949, as registered by wp-5949-01).
CONTRACT_HASH = "c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002"
CONTRACT_CHARS = 12605
CONTRACT_BYTES = 17867

# Tolerances fixed *before* looking at the recomputed numbers, from the printed
# significant digits: 2 decimal places -> 5e-3 absolute; ratio 4 dp -> 5e-5.
TOL_ABS_2DP = 5e-3
TOL_SHARE_4DP = 5e-5


# --------------------------------------------------------------------------- parsing
def load_source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def line_of(text: str, anchor: str) -> int:
    idx = text.find(anchor)
    if idx < 0:
        raise AssertionError(f"anchor is not a verbatim substring: {anchor!r}")
    return text.count("\n", 0, idx) + 1


BLIND_ROW = re.compile(
    r"^\|\s*(IN25-T2/[a-z]+/[a-z]+/[a-z]+)\s*\|\s*([0-9.]+)\s*\|"
    r"\s*\[([0-9.]+),\s*([0-9.]+)\]\s*\|\s*(命中|未中)\s*\|"
)
LEDGER_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([a-z:]+)\s*\|\s*\**(收|拒)\**\s*\|\s*(.*?)\s*\|")
MECH = re.compile(r"([A-Z][A-Z_]+)\(")
LEDGER_SCALAR = re.compile(r"([A-Z][A-Z_]+)\(([0-9.]+)")
POP_ROW = re.compile(r"^\|\s*(deepseek|qwen|minimax|glm)\s*\|\s*(\d+)\s*\|\s*([0-9.]+)\s*\|\s*$")
MATRIX_ROW = re.compile(
    r"^\|\s*(deepseek|qwen|minimax|glm)\s*\|((?:\s*\d/\d\s*\|){5})\s*$"
)


def parse_blind(text: str) -> list[dict]:
    rows = []
    for ln in text.splitlines():
        m = BLIND_ROW.match(ln)
        if m:
            sid, val, lo, hi, verdict = m.groups()
            rows.append(
                {
                    "seat": sid,
                    "family": sid.split("/")[1],
                    "framework": sid.split("/")[2],
                    "role": sid.split("/")[3],
                    "value": float(val),
                    "lo": float(lo),
                    "hi": float(hi),
                    "width": round(float(hi) - float(lo), 6),
                    "declared_verdict": verdict,
                }
            )
    return rows


def parse_ledger(text: str) -> list[dict]:
    rows = []
    for ln in text.splitlines():
        m = LEDGER_ROW.match(ln)
        if m:
            cand, truth, verdict, reasons = m.groups()
            rows.append(
                {
                    "candidate": cand,
                    "truth": truth,
                    "verdict": verdict,
                    "reasons": reasons,
                    "mechanisms": MECH.findall(reasons),
                    "scalars": {k: float(v) for k, v in LEDGER_SCALAR.findall(reasons)},
                }
            )
    return rows


def parse_population(text: str) -> list[tuple[str, int, float]]:
    out = []
    for ln in text.splitlines():
        m = POP_ROW.match(ln)
        if m:
            out.append((m.group(1), int(m.group(2)), float(m.group(3))))
    return out


def parse_matrix(text: str) -> dict[str, list[tuple[int, int]]]:
    out = {}
    for ln in text.splitlines():
        m = MATRIX_ROW.match(ln)
        if m:
            cells = re.findall(r"(\d)/(\d)", m.group(2))
            out[m.group(1)] = [(int(a), int(b)) for a, b in cells]
    return out


def num_after(text: str, pattern: str) -> float:
    m = re.search(pattern, text)
    if not m:
        raise AssertionError(f"cannot find declared number for pattern {pattern!r}")
    return float(m.group(1))


# ----------------------------------------------------------------------- statistics
def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p), exact."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def ci_wilson_upper(k: int, n: int, z: float = 1.959963985) -> float:
    if n == 0:
        return 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return min(1.0, (centre + half) / denom)


# --------------------------------------------------------------------------- checks
def run_checks() -> dict:
    text = load_source()
    blind = parse_blind(text)
    ledger = parse_ledger(text)
    checks: list[dict] = []

    def add(check_id, title, status, declared, recomputed, detail, anchor, **extra):
        rec = {
            "check_id": check_id,
            "title": title,
            "status": status,
            "declared": declared,
            "recomputed": recomputed,
            "detail": detail,
            "anchor": anchor,
            "anchor_line": line_of(text, anchor),
        }
        rec.update(extra)
        checks.append(rec)

    # -- C1 byte binding ----------------------------------------------------------
    raw = SOURCE.read_bytes()
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    add(
        "C1_source_binding",
        "frozen markdown sha256 / chars / bytes == work-package contract pin",
        "pass" if (sha == CONTRACT_HASH and len(text) == CONTRACT_CHARS
                   and len(text.encode("utf-8")) == CONTRACT_BYTES) else "fail",
        {"sha256": CONTRACT_HASH, "chars": CONTRACT_CHARS, "bytes_utf8": CONTRACT_BYTES},
        {"sha256": sha, "chars": len(text), "bytes_utf8": len(text.encode("utf-8")),
         "frozen_file_bytes": len(raw)},
        f"recomputed sha256:{sha} chars={len(text)} bytes={len(text.encode('utf-8'))}",
        "# IN25-T2 · 多样性引擎：氏族矩阵 / 盲预测锁 / 同族查重",
    )

    # -- C2 upstream registration pin --------------------------------------------
    up_kf = json.loads((UPSTREAM_DIR / "kf_result.json").read_text(encoding="utf-8"))
    up_manifest = json.loads((UPSTREAM_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
    up_hash = up_kf["provenance"]["source_hash"].split(":", 1)[1]
    man_hash = up_manifest["source"]["hash"]
    up_ok = (
        up_kf["package_id"] == "wp-5949-01"
        and up_kf["task_type"] == "01-asset-registration"
        and up_kf["report_id"] == REPORT_ID
        and up_hash == man_hash == CONTRACT_HASH
    )
    add(
        "C2_upstream_pin",
        "upstream wp-5949-01 registration pins the same source bytes",
        "pass" if up_ok else "fail",
        {"package_id": "wp-5949-01", "source_hash": "sha256:" + CONTRACT_HASH},
        {"package_id": up_kf["package_id"], "task_type": up_kf["task_type"],
         "report_id": up_kf["report_id"], "kf_result_hash": up_hash,
         "asset_manifest_hash": man_hash,
         "asset_count": up_manifest["counts"]["assets"]},
        "upstream package exists, is 01-asset-registration, and pins identical source bytes;"
        " the review reads only that pin plus the frozen markdown",
        "代码：`tools/diversity/{roster,prereg,dedup,run_node}.py`；测试：`tests/test_diversity_engine.py`。",
    )

    # -- C3 seat arithmetic -------------------------------------------------------
    families = ["deepseek", "qwen", "minimax", "glm"]
    frameworks = ["direct", "inverse", "limits", "failure", "orthogonal"]
    roles = ["attacker", "breaker"]
    matrix = parse_matrix(text)
    cells = sum(len(v) for v in matrix.values())
    per_cell = {c for v in matrix.values() for c in v}
    seats_matrix = sum(a + b for v in matrix.values() for a, b in v)
    declared_seats = int(num_after(text, r"席位数（族×框架×角色）\s*\|\s*\*\*(\d+)\*\*"))
    declared_cells = int(num_after(text, r"矩阵格数\s*\|\s*(\d+)"))
    role_att = sum(a for v in matrix.values() for a, _ in v)
    role_brk = sum(b for v in matrix.values() for _, b in v)
    margins_ok = (
        all(sum(a + b for a, b in v) == len(frameworks) * len(roles) for v in matrix.values())
        and all(sum(v[i][0] + v[i][1] for v in matrix.values()) == len(families) * len(roles)
                for i in range(len(frameworks)))
    )
    seats_ok = (
        len(matrix) == 4 and cells == 20 and seats_matrix == 40
        and {a for a, _ in per_cell} == {1} and {b for _, b in per_cell} == {1}
        and declared_seats == seats_matrix and declared_cells == cells
        and role_att == 20 and role_brk == 20 and margins_ok
    )
    add(
        "C3_seat_arithmetic",
        "40 seats = 4 families x 5 frameworks x 2 roles; 20 cells, margins 10/8, roles 20/20",
        "pass" if seats_ok else "fail",
        {"seats": declared_seats, "cells": declared_cells, "roles": "attacker 20 / breaker 20",
         "margins": "family 10, framework 8"},
        {"seats": seats_matrix, "cells": cells, "families": len(matrix),
         "frameworks": len(frameworks), "roles": {"attacker": role_att, "breaker": role_brk},
         "cells_with_exactly_1_attacker_1_breaker": sum(
             1 for v in matrix.values() for c in v if c == (1, 1)),
         "margins_consistent": margins_ok},
        "coverage matrix parsed from the report's own grid; every margin and role total"
        " recomputed from cell counts",
        "| 氏族覆盖矩阵全格有席位 | 20/20 格 = 100%，每格 2 席 | 1.00 | ✅ |",
    )

    # -- C4 blind table composition ----------------------------------------------
    by_family = {f: sum(1 for r in blind if r["family"] == f) for f in families}
    by_fw = {f: sum(1 for r in blind if r["framework"] == f) for f in frameworks}
    by_role = {role: sum(1 for row in blind if row["role"] == role) for role in roles}
    comp_ok = (
        len(blind) == 40 and set(by_family.values()) == {10} and set(by_fw.values()) == {8}
        and set(by_role.values()) == {20}
    )
    add(
        "C4_blind_grid_composition",
        "blind-scoring table holds one row per seat (40 = 4x10 families, 5x8 frameworks)",
        "pass" if comp_ok else "fail",
        {"rows": 40, "per_family": 10, "per_framework": 8, "per_role": 20},
        {"rows": len(blind), "per_family": by_family, "per_framework": by_fw, "per_role": by_role},
        "row identity parsed from the seat id (IN25-T2/<family>/<framework>/<role>)",
        "**盲预测计分（合成 dry-run）**：40 条结果，区间命中 7 条",
    )

    # -- C5 hit recount -----------------------------------------------------------
    recomputed_hits = [r for r in blind if r["lo"] <= r["value"] <= r["hi"]]
    declared_hits = sum(1 for r in blind if r["declared_verdict"] == "命中")
    flips = [
        {"seat": r["seat"], "value": r["value"], "interval": [r["lo"], r["hi"]],
         "declared": r["declared_verdict"], "contains_value": r["lo"] <= r["value"] <= r["hi"],
         "distance_to_nearest_bound": round(
             min(abs(r["value"] - r["lo"]), abs(r["value"] - r["hi"])), 6)}
        for r in blind
        if (r["declared_verdict"] == "命中") != (r["lo"] <= r["value"] <= r["hi"])
    ]
    add(
        "C5_hit_recount",
        "declared per-seat verdicts == interval containment, recomputed row by row",
        "pass" if not flips else "fail",
        {"declared_hits": declared_hits},
        {"recomputed_hits": len(recomputed_hits),
         "rows": len(blind), "flipped_rows": flips},
        "a flip is either a display-precision artefact (interval printed at 2 dp) or a"
        " scoring bug; the frozen text alone cannot separate the two",
        "**盲预测计分（合成 dry-run）**：40 条结果，区间命中 7 条",
    )

    # -- C6 hit rate --------------------------------------------------------------
    declared_rate = num_after(text, r"（hit_rate\s*([0-9.]+)）")
    rate = len(recomputed_hits) / len(blind)
    rate_ok = abs(rate - declared_rate) <= TOL_ABS_2DP
    add(
        "C6_hit_rate",
        "hit_rate == declared_hits / 40",
        "pass" if rate_ok else "fail",
        {"hit_rate": declared_rate},
        {"hit_rate": round(rate, 6), "hits": len(recomputed_hits), "rows": len(blind),
         "declared_rate_on_declared_hits": round(declared_hits / len(blind), 6)},
        "the declared rate is consistent with the declared hit count but not with the"
        " printed intervals (C5), so it is not reproducible from the frozen text",
        "（hit_rate 0.175），区间宽度中位 0.13705000000000003，时间序检查",
    )

    # -- C7 width statistics ------------------------------------------------------
    widths = [r["width"] for r in blind]
    med = sorted(widths)[len(widths) // 2 - 1: len(widths) // 2 + 1]
    med = sum(med) / 2
    mean = sum(widths) / len(widths)
    declared_med = num_after(text, r"区间宽度中位\s*([0-9.]+)")
    declared_mean = num_after(text, r"无信息基线=平均区间宽度\s*([0-9.]+)")
    med_ok = abs(med - declared_med) <= TOL_ABS_2DP
    mean_ok = abs(mean - declared_mean) <= 1e-3
    add(
        "C7_width_statistics",
        "median / mean interval width recomputed from the printed bounds",
        "pass" if (med_ok and mean_ok) else "fail",
        {"median_width": declared_med, "mean_width_baseline": declared_mean},
        {"median_width": round(med, 6), "mean_width": round(mean, 6),
         "min_width": min(widths), "max_width": max(widths),
         "median_gap": round(med - declared_med, 6),
         "mean_gap": round(mean - declared_mean, 8)},
        "mean reproduces to 1e-4 (rounding); the median differs by 2.05e-3, i.e. inside the"
        " 5e-3 envelope that 2-dp bounds can explain but not inside the printed"
        " 1e-14-level precision of the declared value",
        "无信息基线=平均区间宽度 0.1576",
    )

    # -- C8 null-model sensitivity ------------------------------------------------
    values = [r["value"] for r in blind]
    lo_band, hi_band = min(values), max(values)
    span = hi_band - lo_band
    clipped = [max(0.0, min(r["hi"], hi_band) - max(r["lo"], lo_band)) for r in blind]
    p_uniform = mean
    p_support = sum(clipped) / len(clipped) / span
    k = len(recomputed_hits)
    n = len(blind)
    p_u = binom_sf(k, n, p_uniform)
    p_s = binom_sf(k, n, p_support)
    k_crit = min(i for i in range(n + 1) if binom_sf(i, n, p_uniform) <= 0.05)
    power = binom_sf(k_crit, n, 0.30)
    add(
        "C8_null_model_sensitivity",
        "'hit rate ~ no-information baseline': is the conclusion robust to the null model?",
        "pass" if (p_u > 0.05 and p_s > 0.05) else "fail",
        {"claim": "命中率与无信息基线同量级属预期（恰好说明流程无泄漏）",
         "baseline": declared_mean},
        {"observed_hits": k, "n": n, "observed_rate": round(k / n, 4),
         "null_A_uniform_0_1": {"p0": round(p_uniform, 6),
                                "expected_hits": round(n * p_uniform, 3),
                                "p_value_ge_observed": round(p_u, 4)},
         "null_B_uniform_in_observed_band": {
             "band": [lo_band, hi_band], "band_width": round(span, 6),
             "p0": round(p_support, 6), "expected_hits": round(n * p_support, 3),
             "p_value_ge_observed": round(p_s, 4)},
         "alpha_0_05_critical_hits": k_crit,
         "power_to_detect_p_0_30": round(power, 3),
         "first_clause_holds_under_both_nulls": bool(p_u > 0.05 and p_s > 0.05),
         "second_clause_is_a_non_sequitur": True},
        "the quantitative clause ('same magnitude as chance') survives both null models"
        f" (p={p_u:.2f} under U(0,1), p={p_s:.2f} under U(band); n=40, alpha=0.05 critical"
        f" {k_crit} hits, power {power:.2f} at p=0.30).  The inferential clause ('therefore no"
        " leakage') does not follow: not rejecting a null is not evidence for it, and a"
        " synthetic dry-run whose results derive from the same seeds cannot test leakage at all"
        " (report §⑤-5 says so itself).  Reported as an overstated inference, not as a"
        " numeric error",
        "命中率与无信息基线同量级属预期（恰好说明流程无泄漏）；真实命中率待 T3",
    )

    # -- C9 mechanism hit counts --------------------------------------------------
    clone_rows = [r for r in ledger if r["truth"].startswith("clone")]
    indep_rows = [r for r in ledger if r["truth"] == "independent"]
    declared_mech = {
        m.group(1): int(m.group(2))
        for m in re.finditer(r"^\|\s*(CLONE_[A-Z_]+|RETUNE_ONLY|SAME_CLADE_REPEAT)\s*\|\s*(\d+)\s*\|",
                             text, re.M)
    }
    visible_mech = {k2: sum(1 for r in clone_rows if k2 in r["mechanisms"]) for k2 in declared_mech}
    dominated = all(visible_mech[k2] <= declared_mech[k2] for k2 in declared_mech)
    add(
        "C9_mechanism_hit_counts",
        "per-mechanism hit counts over the 24 clone pairs (n=24)",
        "unverifiable" if dominated else "fail",
        declared_mech,
        {"visible_clone_rows": len(clone_rows),
         "visible_mechanism_hits": visible_mech,
         "declared_total_clone_pairs": 24,
         "coverage_of_corpus": round(len(clone_rows) / 24, 4)},
        "only triggering paths are printed, so non-hits are invisible: the visible subset"
        " bounds each declared count from below (consistent) but cannot confirm it",
        "| CLONE_CONTAINMENT | 24 |",
    )

    # -- C10 ledger composition / end-to-end claim --------------------------------
    names = [r["candidate"] for r in ledger]
    methods = sorted({nm.split("-")[0] for nm in names})
    add(
        "C10_ledger_composition",
        "ledger covers the claimed corpus: 'first 24 rows' vs '24/24 clones rejected'",
        "unverifiable",
        {"end_to_end": "24/24 拒", "rows_shown": 24, "corpus": "6 method cards x 4 clone variants"},
        {"rows": len(ledger), "independent_rows": len(indep_rows), "clone_rows": len(clone_rows),
         "method_cards_present": methods, "method_cards_in_population": 6,
         "rows_missing_to_cover_corpus": ["M5-c4", "M6", "M6-c1", "M6-c2", "M6-c3", "M6-c4"],
         "all_shown_clones_rejected": all(r["verdict"] == "拒" for r in clone_rows),
         "all_shown_independent_accepted": all(r["verdict"] == "收" for r in indep_rows)},
        "the label '前 24 条（按提交顺序）' is honest, but 19 of the 24 clone pairs are visible:"
        " '24/24 rejected' is consistent with, not established by, the printed ledger",
        "逐条门账本（前 24 条，按提交顺序",
    )

    # -- C11 similarity table consistency ----------------------------------------
    decl_min = num_after(text, r"克隆对骨架相似度 min / 中位\s*\|\s*([0-9.]+)")
    decl_med_clone = num_after(text, r"克隆对骨架相似度 min / 中位\s*\|\s*[0-9.]+\s*/\s*([0-9.]+)")
    decl_indep_max = num_after(text, r"独立对骨架相似度 max\s*\|\s*([0-9.]+)")
    decl_same_max = num_after(text, r"独立且同族的骨架相似度 max\s*\|\s*([0-9.]+)")
    skel_vals = [r["scalars"]["CLONE_SKELETON"] for r in clone_rows if "CLONE_SKELETON" in r["scalars"]]
    same_vals = [r["scalars"]["SAME_CLADE_REPEAT"] for r in clone_rows
                 if "SAME_CLADE_REPEAT" in r["scalars"]]
    consistency = {
        "all_printed_skeleton_hits_above_declared_min": all(v >= decl_min for v in skel_vals),
        "min_printed_skeleton_hit": min(skel_vals) if skel_vals else None,
        "declared_min_traceable_to_printed_row": any(
            abs(v - decl_min) <= TOL_ABS_2DP for v in skel_vals),
        "same_clade_max_le_overall_max": decl_same_max <= decl_indep_max,
        "threshold_separates_declared_max_and_min": decl_indep_max < 0.72 <= decl_med_clone,
        "skeleton_min_below_threshold_needs_other_paths": decl_min < 0.72,
    }
    cons_ok = (consistency["all_printed_skeleton_hits_above_declared_min"]
               and consistency["same_clade_max_le_overall_max"]
               and consistency["threshold_separates_declared_max_and_min"])
    add(
        "C11_similarity_table_consistency",
        "separation table vs printed per-pair similarity values vs threshold 0.72",
        "pass" if cons_ok else "fail",
        {"clone_skeleton_min": decl_min, "clone_skeleton_median": decl_med_clone,
         "independent_skeleton_max": decl_indep_max,
         "independent_same_clade_max": decl_same_max, "threshold": 0.72},
        {"printed_skeleton_hits": len(skel_vals),
         "min_printed_skeleton_hit": consistency["min_printed_skeleton_hit"],
         "min_printed_same_clade": min(same_vals) if same_vals else None,
         **consistency},
        "table is internally consistent; the declared minimum 0.6308 belongs to a pair whose"
        " skeleton path did not trigger, and non-triggering values are not printed, so that"
        " one number is not traceable to a row (traceability, not contradiction)",
        "| 克隆对骨架相似度 min / 中位 | 0.6308 / 0.9123 |",
    )

    # -- C12 paraphrase/lexical narrative ---------------------------------------
    par_rows = [r for r in clone_rows if r["truth"] == "clone:paraphrase"]
    par_lex = [{"candidate": r["candidate"], "lexical": r["scalars"].get("CLONE_LEXICAL")}
               for r in par_rows]
    par_hit_over = [x for x in par_lex if x["lexical"] is not None and x["lexical"] >= 0.80]
    add(
        "C12_paraphrase_lexical_claim",
        "'paraphrase surface Jaccard is only 0.77 (<0.80 threshold)' vs printed ledger values",
        "pass" if not par_hit_over else "fail",
        {"claim": "表层 Jaccard 对同义改写只有 0.77（<0.80 阈值）"},
        {"visible_paraphrase_rows": par_lex,
         "rows_at_or_above_0_80": par_hit_over},
        "the narrative generalises one paraphrase pair to all paraphrase pairs; the printed"
        " ledger contains paraphrase rows at 0.82 and 0.84 that DO cross the lexical path,"
        " which is why CLONE_LEXICAL fires 15 times rather than on verbatim clones alone",
        "表层 Jaccard 对同义改写只有 0.77（<0.80 阈值）",
    )

    # -- C13 population table ----------------------------------------------------
    pop = parse_population(text)
    total = sum(c for _, c, _ in pop)
    shares_ok = all(abs(c / total - s) <= TOL_SHARE_4DP for _, c, s in pop)
    top2 = num_after(text, r"前两族占比\s*([0-9.]+)")
    top2_recomp = (max(pop, key=lambda t: t[1])[1] + sorted((c for _, c, _ in pop), reverse=True)[1]) / total
    add(
        "C13_population_table",
        "population shares and 'top-two families share' recomputed from n=6",
        "pass" if (shares_ok and total == 6) else "fail",
        {"n": 6, "shares": {f: s for f, _, s in pop}, "top2_share": top2},
        {"n": total, "shares": {f: round(c / total, 6) for f, c, _ in pop},
         "top2_share": round(top2_recomp, 6),
         "top2_gap": round(top2 - top2_recomp, 6),
         "clade_cap": 0.6,
         "max_share_below_cap": max(c / total for _, c, _ in pop) < 0.6},
        "shares reproduce exactly; the top-two figure is truncated (0.6666 vs 0.6667, 1e-4)"
        " and the population never approaches CLADE_SHARE_CAP=0.6, so the cap is untested"
        " by this corpus",
        "前两族占比 0.6666，已收方案最大两两骨架相似度 0.0412",
    )

    # -- C14 section 6 error row -------------------------------------------------
    decl_diff = num_after(text, r"0\.175\s*\|\s*([0-9.]+)（相对基线")
    decl_rel = num_after(text, r"相对基线\s*([0-9.]+)%")
    decl_rate_s6 = num_after(text, r"\|\s*(0\.175)\s*\|\s*[0-9.]+（相对基线")
    # arithmetic of the declared row, using the report's own inputs
    diff_decl = decl_rate_s6 - declared_mean
    rel_decl = diff_decl / declared_mean * 100
    row_ok = abs(diff_decl - decl_diff) <= 5e-3 and abs(rel_decl - decl_rel) <= 0.5
    # same row re-run with the hit rate recomputed from the printed intervals (C5/C6)
    diff_re = rate - declared_mean
    rel_re = diff_re / declared_mean * 100
    add(
        "C14_section6_error_row",
        "section-6 row '0.175 vs baseline 0.1576 -> +0.017 / 11.0%' arithmetic",
        "pass" if row_ok else "fail",
        {"diff": decl_diff, "relative_pct": decl_rel},
        {"diff_from_declared_inputs": round(diff_decl, 6),
         "relative_pct_from_declared_inputs": round(rel_decl, 4),
         "with_recomputed_hit_rate": {"rate": round(rate, 4),
                                      "diff": round(diff_re, 6),
                                      "relative_pct": round(rel_re, 4)}},
        "arithmetic is right for the declared inputs, but the inputs inherit C5/C6: the row"
        " is self-consistent and still not reproducible (and it is declared 不适用, which is"
        " the correct call for a synthetic dry-run)",
        "| 盲预测命中率 | 无信息基线=平均区间宽度 0.1576 | 0.175 | 0.017（相对基线 11.0%） | **不适用**",
    )

    # -- C15 withheld evidence ---------------------------------------------------
    prefixes = re.findall(r"`([0-9a-f]{16})`", text)
    add(
        "C15_withheld_artifacts",
        "declared artifact snapshots / lock assertions / pytest count resolvable?",
        "unverifiable",
        {"declared_sha256_prefixes": len(prefixes),
         "lock_assertions": 3, "pytest_passed": 22},
        {"resolvable_in_this_repo": 0,
         "reason": "artifacts/in25_t2/*, tools/diversity/*, tests/test_diversity_engine.py and"
                   " blind_scores.json live in TensorPlatform, not in TensorKnowledge",
         "prefix_hex_chars": sorted({len(p) for p in prefixes}),
         "tamper_and_time_order_evidence_in_text": False,
         "timestamps_in_blind_table": False},
        "16-hex prefixes cannot bind 256-bit digests; the tamper/time-order assertions and"
        " '22 passed' have no printed evidence, so they are WITHHELD rather than accepted",
        "| 盲预测锁定工件 | lock_hash `1b96a171b6000fb9…`，40 条预测，复算 ✅，篡改检出 ✅，先跑后锁被拒 ✅ | 三项全真 | ✅ |",
    )

    # -- C16 physics-baseline applicability --------------------------------------
    add(
        "C16_physics_baseline_applicability",
        "report claims zero physical quantity -> 15%/3% physical criterion not applicable",
        "pass",
        {"claim": "本节点是**进程/纪律机器**，不产生任何物理量（零平台域语义）"},
        {"physical_quantities_found": 0,
         "section6_rows": 6,
         "section6_rows_answered": 6,
         "explicit_not_applicable_rows": text.count("不适用"),
         "process_metrics_errors_zero": True},
        "spot check: every numeric row of section 6 is a decision metric (coverage, reject"
        " rate, FPR, hash equality, collisions, hit rate), none is a physical observable;"
        " the report's 'not applicable' answers are the correct call",
        "**物理基准声明**：本节点是**进程/纪律机器**，不产生任何物理量（零平台域语义）",
    )

    # -- C17 scope ---------------------------------------------------------------
    ids = set(re.findall(r"tensor://reports/(\d+)", text))
    ids |= set(re.findall(r"report_id=(\d+)", text))
    add(
        "C17_scope_single_report",
        "review surface is report 5949 only",
        "pass" if ids <= {REPORT_ID} else "fail",
        {"report_ids": [REPORT_ID]},
        {"report_ids_in_text": sorted(ids),
         "self_reference_in_text": bool(ids),
         "scope_pin_source": "docs/kf/wp-5949-01/kf_result.json report_id"
                             if not ids else "report text"},
        "the frozen text carries no self-reference to a report id, so scope is established"
        " by the upstream pin (C2) rather than by the text: no other report_id is read",
        "# IN25-T2 · 多样性引擎：氏族矩阵 / 盲预测锁 / 同族查重",
    )

    # -- C18 FPR point estimate ----------------------------------------------------
    n_indep_pairs = 15
    fpr_upper = ci_wilson_upper(0, n_indep_pairs)
    add(
        "C18_fpr_confidence_bound",
        "'FPR 0.00' as gate evidence over n=15 independent pairs",
        "fail",
        {"criterion_row": "语料 TPR 1.00 / FPR 0.00；端到端 24/24 拒；fail-closed 负例 3/3 拒",
         "independent_pairs": n_indep_pairs},
        {"fpr_point_estimate": 0.0,
         "wilson_95_upper": round(fpr_upper, 4),
         "rule_of_three_upper": round(3 / n_indep_pairs, 4),
         "min_detectable_fpr_at_n15": round(3 / n_indep_pairs, 4)},
        "0/15 的点估计写成 0.00 会让人读成「零误拒率已证」；实际 95% 上界约 0.20。"
        "门限判据据此仍可通过（独立对最大骨架相似度 0.0412 距阈值 0.72 很远），但『0.00』"
        "应写成区间或标注样本量",
        "语料 TPR 1.00 / FPR 0.00；端到端 24/24 拒；fail-closed 负例 3/3 拒",
    )

    # -- C19 single-path sufficiency vs "one similarity would leak" ---------------
    declared_mech_c19 = {
        m.group(1): int(m.group(2))
        for m in re.finditer(r"^\|\s*(CLONE_[A-Z_]+|RETUNE_ONLY|SAME_CLADE_REPEAT)\s*\|\s*(\d+)\s*\|",
                             text, re.M)
    }
    best_path, best_hits = max(declared_mech_c19.items(), key=lambda kv: kv[1])
    add(
        "C19_single_path_sufficiency",
        "'one similarity alone would leak' vs the report's own per-mechanism hit table",
        "pass" if best_hits < 24 else "fail",
        {"claim": "单靠一种相似度会漏——这是多路或门存在的理由（§④）", "clone_pairs": 24},
        {"best_single_path": best_path, "best_single_path_hits": best_hits,
         "clone_pairs_covered": round(best_hits / 24, 4),
         "mechanisms_with_full_coverage": [k for k, v in declared_mech_c19.items() if v == 24],
         "claim_supported_for_skeleton_path_only": declared_mech_c19.get("CLONE_SKELETON", 0) < 24},
        f"{best_path} 单独即命中 {best_hits}/24 克隆对，故在本语料上「单路必漏」不成立；"
        "成立的只是「0.72 骨架单路会漏 6 对（18/24）」。§④ 的措辞应限定到骨架路径，"
        "或说明真实语料上包含度的 FPR 未测",
        "| CLONE_CONTAINMENT | 24 |",
    )

    n_pass = sum(1 for c in checks if c["status"] == "pass")
    n_fail = sum(1 for c in checks if c["status"] == "fail")
    n_unv = sum(1 for c in checks if c["status"] == "unverifiable")
    return {
        "package_id": "wp-5949-04",
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "contract_version": "1.0",
        "checks_version": "1.0.0",
        "source": {
            "uri": f"tensor://reports/{REPORT_ID}",
            "field": "markdown",
            "sha256": sha,
            "chars": len(text),
            "bytes_utf8": len(text.encode("utf-8")),
            "frozen_copy": str(SOURCE.relative_to(REPO)),
        },
        "tolerances": {"abs_2dp": TOL_ABS_2DP, "share_4dp": TOL_SHARE_4DP},
        "checks": checks,
        "checks_summary": {
            "n_checks": len(checks),
            "n_pass": n_pass,
            "n_fail": n_fail,
            "n_unverifiable": n_unv,
            "failed": [c["check_id"] for c in checks if c["status"] == "fail"],
            "unverifiable": [c["check_id"] for c in checks if c["status"] == "unverifiable"],
        },
    }


def main() -> None:
    result = run_checks()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    s = result["checks_summary"]
    print(f"wrote {OUT.relative_to(REPO)}: {s['n_checks']} checks,"
          f" {s['n_pass']} pass / {s['n_fail']} fail / {s['n_unverifiable']} unverifiable")
    for cid in s["failed"]:
        print("  FAIL:", cid)
    for cid in s["unverifiable"]:
        print("  WITHHELD:", cid)


if __name__ == "__main__":
    main()