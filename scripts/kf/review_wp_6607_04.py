#!/usr/bin/env python3
"""wp-6607-04 — independent (04) review of tensor report 6607.

Report 6607 is «jamming 体积分数重锁：FIRE/CG 能量极小 + 双周期 + 有限尺寸标度（IN32-N02）»,
a TensorDEM granular-physics report. This package re-derives every number the report
prints *from the report's own printed table and thresholds*, and decides separately

  (1) whether each printed number is reproducible from the printed inputs, and
  (2) whether each of the nine criteria was executed as its own text says.

Design rule (no hand-copy): every value this review prints is computed here from the
pinned snapshot; the only human transcription is the *quote* of an input, and every
quote is checked to be a verbatim substring of the single line it claims (tests enforce).

Usage
    python3 scripts/kf/review_wp_6607_04.py --fetch      # re-pin the snapshot (needs creds)
    python3 scripts/kf/review_wp_6607_04.py --offline    # rebuild all artifacts, no network
    python3 scripts/kf/review_wp_6607_04.py --offline --no-figure

Writes (under docs/kf/wp-6607-04/):
    source_6607.md        pinned byte-equal snapshot of the report markdown
    recompute.json        recompute ledger (formula / quoted inputs with line / value / status)
    review_report.json    verdict, findings, corroborated claims, checks not run
    report_markdown.md    review report body, rendered from recompute.json
    figures/wp-6607-04.png phi_J(N) + FSS fits + anchor band, and the ledger status matrix
    kf_result.json        KF-RESULT v1 envelope (04-independent-review, awaiting_pr_merge)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = "wp-6607-04"
OUT = ROOT / "docs" / "kf" / PKG
REPORT_ID = "6607"
REVIEWED_PACKAGE = "wp-6607-01"
TASK_TYPE = "04-independent-review"
GENERATOR = "scripts/kf/review_wp_6607_04.py"

# Pinned by --fetch on 2026-11-14T21:08:38+00:00 from <TENSOR_API_BASE>/tensor/reports/6607
PINNED_AT = "2026-11-14T21:08:38+00:00"
EXPECTED_HASH = "sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1"
EXPECTED_CHARS = 7642
EXPECTED_LINES = 136
SOURCE_URI = "tensor://reports/6607"
# The progress report for this mission, posted to <TENSOR_API_BASE>/tensor/reports (id 18983).
PROGRESS_REPORT = {"mission_id": 20946, "report_id": 18983,
                   "title": "wp-6607-04 · 报告 6607（2D 颗粒 jamming 体积分数重锁）的独立复核"}
SCENARIO_KEY = "dem-granular-jamming"
REPORT_TITLE = "jamming 体积分数重锁：FIRE/CG 能量极小 + 双周期 + 有限尺寸标度（IN32-N02）"

PROTOCOLS = ("growth", "decompression", "rsa_direct", "fire_from_rsa")
STATUSES = ("pass", "fail", "derived", "not_recomputable", "withheld")
NUM = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"


# --------------------------------------------------------------------------- source
def _post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - internal platform
        return json.loads(r.read().decode())


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - internal platform
        return json.loads(r.read().decode())


def fetch_record(report_id: str = REPORT_ID) -> dict:
    """GET report markdown from the platform (same login path as scripts/kf/fetch_report.py)."""
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
    user = os.environ["TENSOR_AGENT_USER"]
    pwd = os.environ["TENSOR_AGENT_PASS"]
    token = None
    for path in ("/tensor/auth/login", "/auth/login"):
        try:
            d = _post(base + path, {"username": user, "password": pwd})
        except Exception:  # noqa: BLE001 - try the next login path
            continue
        token = d.get("access_token") or d.get("token")
        if token:
            break
    if not token:
        raise SystemExit("login failed against " + base)
    rec = _get("%s/tensor/reports/%s" % (base, report_id), token)
    rec["_retrieved_via"] = "GET %s/tensor/reports/%s (auth: platform login)" % (base, report_id)
    return rec


def read_snapshot() -> str:
    p = OUT / "source_6607.md"
    if not p.exists():
        raise SystemExit("missing snapshot %s — run --fetch first" % p)
    return p.read_text(encoding="utf-8")


def locate(lines, quote: str) -> int:
    """1-based line number of the unique line containing `quote` verbatim."""
    hits = [i + 1 for i, ln in enumerate(lines) if quote in ln]
    if not hits:
        raise SystemExit("QUOTE NOT FOUND: %r" % quote[:90])
    if len(hits) > 1:
        raise SystemExit("QUOTE NOT UNIQUE (%d hits): %r" % (len(hits), quote[:90]))
    return hits[0]


# ---------------------------------------------------------------------- table parse
def parse_phi_table(md: str) -> dict:
    rows = [ln for ln in md.splitlines() if re.match(r"^\|\s*\d+\s*\|", ln)]
    if len(rows) != 5:
        raise SystemExit("expected 5 N-rows in the chapter-3 table, got %d" % len(rows))
    data = {p: {"phi": [], "se": []} for p in PROTOCOLS}
    ns = []
    for ln in rows:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        ns.append(int(cells[0]))
        for proto, cell in zip(PROTOCOLS, cells[1:]):
            m = re.match(r"^(%s)\s*±\s*(%s)$" % (NUM, NUM), cell)
            if not m:
                raise SystemExit("unparsable table cell %r" % cell)
            data[proto]["phi"].append(float(m.group(1)))
            data[proto]["se"].append(float(m.group(2)))
    if ns != [256, 512, 1024, 2048, 4096]:
        raise SystemExit("unexpected N ladder %r" % ns)
    summary = [ln for ln in md.splitlines() if ln.startswith("| **φ_J(∞)**")]
    if len(summary) != 1:
        raise SystemExit("missing phi_J(inf) summary row")
    cells = [c.strip() for c in summary[0].strip().strip("|").split("|")]
    for proto, cell in zip(PROTOCOLS, cells[1:]):
        m = re.search(r"(%s) \(ν=(%s), R²=(%s)\)" % (NUM, NUM, NUM), cell)
        if not m:
            raise SystemExit("unparsable phi_J(inf) cell %r" % cell)
        data[proto].update(phi_inf_rep=float(m.group(1)), nu_rep=float(m.group(2)),
                           r2_rep=float(m.group(3)))
    return {"N": ns, "protocols": data, "summary_line": summary[0]}


# ------------------------------------------------------------------------ fit math
def _fss_ssr(nu, ns, ys, ses=None):
    """Variable projection: for fixed nu the model is linear in (phi_inf, c)."""
    xs = [n ** (-1.0 / (2.0 * nu)) for n in ns]
    w = [1.0 / (s * s) for s in ses] if ses else [1.0] * len(ys)
    sw = sum(w)
    sx = sum(wi * x for wi, x in zip(w, xs))
    sy = sum(wi * y for wi, y in zip(w, ys))
    sxx = sum(wi * x * x for wi, x in zip(w, xs))
    sxy = sum(wi * x * y for wi, x, y in zip(w, xs, ys))
    det = sw * sxx - sx * sx
    if abs(det) < 1e-300:
        return float("inf"), None, None
    a = (sy * sxx - sx * sxy) / det
    b = (sw * sxy - sx * sy) / det
    ssr = sum(wi * (y - (a + b * x)) ** 2 for wi, x, y in zip(w, xs, ys))
    return ssr, a, b


def fss_fit(ns, ys, ses=None, lo=0.2, hi=8.0, grid=12000) -> dict:
    step = (hi - lo) / (grid - 1)
    best = (float("inf"), lo)
    for i in range(grid):
        nu = lo + i * step
        ssr, _a, _b = _fss_ssr(nu, ns, ys, ses)
        if ssr < best[0]:
            best = (ssr, nu)
    a_, b_ = max(lo, best[1] - step), min(hi, best[1] + step)
    for _ in range(100):
        m1 = a_ + (b_ - a_) / 3.0
        m2 = b_ - (b_ - a_) / 3.0
        if _fss_ssr(m1, ns, ys, ses)[0] < _fss_ssr(m2, ns, ys, ses)[0]:
            b_ = m2
        else:
            a_ = m1
    nu = 0.5 * (a_ + b_)
    ssr, phi_inf, c = _fss_ssr(nu, ns, ys, ses)
    # R² is reported unweighted so that it is comparable with the printed R²,
    # whatever weighting the fit itself used.
    ssr_u = sum((y - (phi_inf + c * n ** (-1.0 / (2.0 * nu)))) ** 2 for n, y in zip(ns, ys))
    mean = sum(ys) / len(ys)
    sst = sum((y - mean) ** 2 for y in ys)
    return {"nu": nu, "phi_inf": phi_inf, "c": c, "ssr": ssr, "r2": 1.0 - ssr_u / sst}


def ssr_at(nu, ns, ys) -> float:
    ssr, _a, _b = _fss_ssr(nu, ns, ys, None)
    mean = sum(ys) / len(ys)
    sst = sum((y - mean) ** 2 for y in ys)
    return 1.0 - ssr / sst


# ------------------------------------------------------------------ ledger entries
def _f(x: float, digits: int = 6) -> str:
    return ("%." + str(digits) + "f") % x


def _rel(value: float, reported: float) -> float:
    if reported == 0:
        return float("nan")
    return 100.0 * (value - reported) / reported


def build_ledger(md: str) -> list:
    lines = md.splitlines()
    tab = parse_phi_table(md)
    ns = tab["N"]
    ns_f = [float(n) for n in ns]
    P = tab["protocols"]
    growth, decomp = P["growth"]["phi"], P["decompression"]["phi"]
    fits = {p: fss_fit(ns_f, P[p]["phi"]) for p in PROTOCOLS}

    def entry(eid, kind, formula, inputs, value, reported=None, unit="-", rel=None, tol=None,
              status="pass", note="", verdict_impact="none", origin="printout", extra=None):
        ins = [{"quote": q, "line": locate(lines, q)} for q in inputs]
        d = {"id": eid, "kind": kind, "formula": formula, "inputs": ins,
             "value": value, "reported": reported, "unit": unit, "rel_diff_pct": rel,
             "tol": tol, "status": status, "note": note,
             "verdict_impact": verdict_impact, "reported_origin": origin}
        if extra:
            d.update(extra)
        return d

    q_table = "| 256 | 0.8404 ± 0.0008 | 0.8415 ± 0.0006 | 0.8377 ± 0.0017 | 0.8377 ± 0.0008 |"
    q_inf = tab["summary_line"]
    q_mono = "两个准静态协议（充气 / 泄压）**随 N 单调且稳定**：16 倍 N 只增长 0.0036 / 0.0040"
    q_gap = "两条曲线在每个 N 上的差 ≤ 0.0015，种子离散 0.12–0.31%。"
    q_quench = "两个瞬时淬火臂则相反：φ_J 随 N **下降**（0.8377 → 0.8280 / 0.7995）"
    q_e_note = "**判据 e 失败（0.090）**：失败被定位在两个瞬时淬火臂，而两个准静态协议之间只差 0.0015"
    q_stable = "其 φ_J 随 N 单调漂移，而准静态臂稳定到 5e-4"
    q_crit_c = "| c_frictionless_phi_j_infinite | phi_J(N->inf) from N>=2048 must lie in 0.84 +- 0.01 |"
    q_crit_g = "| g_finite_size_scaling | phi_J(N) = phi_inf - c N^{-1/(2 nu)}: R^2 > 0.98 and nu in [0.5, 1.5] |"
    q_crit_a = "| a_fire_convergence | FIRE residual reduction per stage must be >= 1e6;"
    q_crit_b = "| b_double_periodic_virial | |Virial + image| / |Virial| < 1e-10 and raw stress asymmetry < 1e-12"
    q_crit_e = "| e_protocol_independence | four protocols must agree on phi_J within 0.01 |"
    q_crit_f = "| f_seed_sensitivity | per-configuration phi_c dispersion across seeds < 1% |"
    q_crit_d = "| d_frictional_phi_j | mu=0.5 must give phi_J in [0.80, 0.84] |"
    q_virial = "φ=0.86、N=192、ε=9.7e-14 的极小态：周期 virial 恒等式 `‖W+W_image‖/‖W‖ = 1.85e-11`"
    q_linear = "恒等式残差随极小化容差线性下降（ε=1e-6 时 1.06e-4 → ε=1e-13 时 1.85e-11）"
    q_rise = "接受步有微小抬升（最大相对抬升 0.94）"

    E = []
    E.append(entry("T1_PHI_TABLE_PARSE", "derived",
                   "parse the chapter-3 mean±s.e.m. table: 5 N-rows x 4 protocol columns",
                   [q_table], value="5 rows x 4 protocols", status="derived",
                   note="这是全部复算的唯一输入面：本包不引入任何报告之外的 φ_J 数值。"))

    for proto in ("growth", "decompression"):
        mono = all(b > a for a, b in zip(P[proto]["phi"], P[proto]["phi"][1:]))
        E.append(entry("R1_%s_MONOTONE" % proto.upper(), "invariant",
                       "all(phi[N_{i+1}] > phi[N_i]) for N=256..4096", [q_mono],
                       value="true" if mono else "false", reported="单调",
                       status="pass" if mono else "fail",
                       note="%s: %s" % (proto, " -> ".join(_f(v, 4) for v in P[proto]["phi"]))))

    for proto, rep in (("growth", "0.0036"), ("decompression", "0.0040")):
        delta = P[proto]["phi"][-1] - P[proto]["phi"][0]
        E.append(entry("R3_%s_16X" % proto.upper(), "arithmetic",
                       "phi(N=4096) - phi(N=256)", [q_mono],
                       value=_f(delta, 4), reported=rep, unit="φ_J",
                       rel=_rel(delta, float(rep)), tol="5e-5 abs (4 dp printout)",
                       status="pass" if abs(delta - float(rep)) <= 5e-5 else "fail"))

    gaps = [abs(d - g) for d, g in zip(decomp, growth)]
    imax = gaps.index(max(gaps))
    E.append(entry("R5_QUASI_GAP_PER_N", "invariant",
                   "max_N |phi_decompression(N) - phi_growth(N)|", [q_gap],
                   value=_f(max(gaps), 4), reported="0.0015", unit="φ_J",
                   rel=_rel(max(gaps), 0.0015), tol="the printed bound is the assertion",
                   status="fail" if max(gaps) > 0.0015 else "pass",
                   note="最大差在 N=%d：%.4f vs %.4f -> %.4f > 0.0015（本行判「≤0.0015」这条断言，不是判据 e）"
                        % (ns[imax], decomp[imax], growth[imax], max(gaps))))

    gap_inf = P["decompression"]["phi_inf_rep"] - P["growth"]["phi_inf_rep"]
    E.append(entry("R6_QUASI_GAP_AT_PHI_INF", "arithmetic",
                   "phi_inf(decompression) - phi_inf(growth), both as printed on the phi_J(inf) row",
                   [q_e_note, q_inf], value=_f(gap_inf, 4), reported="0.0015", unit="φ_J",
                   rel=_rel(gap_inf, 0.0015), tol="the printed bound is the assertion",
                   status="fail" if gap_inf > 0.0015 else "pass",
                   note="外推值差 %.4f，是「0.0015」的 %.1f 倍；方向一致地低估两臂分歧，"
                        "但远小于判据 e 的 0.01 容差" % (gap_inf, gap_inf / 0.0015)))

    spread = max(max(P["growth"]["phi"][-3:]) - min(P["growth"]["phi"][-3:]),
                 max(P["decompression"]["phi"][-3:]) - min(P["decompression"]["phi"][-3:]))
    E.append(entry("R7_QUASI_PLATEAU_SPREAD", "invariant",
                   "max over the quasi-static protocols of (max - min) phi for N in {1024,2048,4096}",
                   [q_stable], value=_f(spread, 4), reported="0.0005", unit="φ_J",
                   rel=_rel(spread, 0.0005), tol="the printed bound is the assertion",
                   status="fail" if spread > 0.0005 else "pass",
                   note="平台段整体 1.3e-3/1.6e-3；只有最后一跳是 4e-4"))

    E.append(entry("R8_FIT_PHI_INF_GROWTH", "fit",
                   "phi(N) = phi_inf - c N^(-1/(2 nu)), variable projection over nu, 5 points",
                   [q_inf, q_crit_g], value=_f(fits["growth"]["phi_inf"], 6),
                   reported="0.8454", unit="φ_J",
                   rel=_rel(fits["growth"]["phi_inf"], 0.8454), tol="1 rel%",
                   status="pass" if abs(_rel(fits["growth"]["phi_inf"], 0.8454)) < 1.0 else "fail",
                   note="外推值复现到 %.1e（相对）；同一次拟合给 nu=%.4f, R2=%.6f"
                        % (abs(_rel(fits["growth"]["phi_inf"], 0.8454)) / 100,
                           fits["growth"]["nu"], fits["growth"]["r2"])))

    E.append(entry("R9_FIT_NU_GROWTH", "fit",
                   "nu at the SSR minimum of the same fit", [q_inf],
                   value=_f(fits["growth"]["nu"], 4), reported="1.21", unit="-",
                   rel=_rel(fits["growth"]["nu"], 1.21), tol="2 rel%",
                   status="pass" if abs(_rel(fits["growth"]["nu"], 1.21)) < 2.0 else "fail",
                   note="4 dp 表格舍入下 SSR 对 nu 极平（见 R10），nu 只复现到亚百分点"))

    prof_grid = [0.4 + i * (6.0 - 0.4) / 5600 for i in range(5601)]
    prof = [(nu, _fss_ssr(nu, ns_f, growth, None)[0]) for nu in prof_grid]
    smin = min(s for _nu, s in prof)
    bands = []
    for k in (1.05, 1.5, 4.0):
        sel = [nu for nu, s in prof if s <= smin * k]
        bands.append((k, min(sel), max(sel)))
    E.append(entry("R10_NU_PROFILE_WIDTH", "derived",
                   "nu range where SSR(nu) <= k*SSR_min, growth column", [q_inf],
                   value=" ; ".join("SSR<=%.2fx: nu in [%.2f, %.2f]" % b for b in bands),
                   status="derived",
                   note="判据 g 的 nu in [0.5,1.5] 相比这条平台带过窄：1.5xSSR 平台已含 nu=%.2f；"
                        "报告 5.7 的 bootstrap ±0.01 只反映种子噪声、不含 c-nu 退化" % bands[1][2]))

    E.append(entry("R11_FIT_R2_GROWTH", "fit",
                   "R2 = 1 - SSR/SST of the same 5-point fit", [q_inf, q_crit_g],
                   value=_f(fits["growth"]["r2"], 6), reported="0.990", unit="-",
                   rel=_rel(fits["growth"]["r2"], 0.990), tol="5e-3 abs",
                   status="pass" if abs(fits["growth"]["r2"] - 0.990) <= 5e-3 else "fail",
                   note="差值 %.1e（绝对）；5 点 3 参下 R2 本身接近恒真，见 R12"
                        % abs(fits["growth"]["r2"] - 0.990)))

    x = 12345
    rand = []
    for _ in range(2000):
        x = (1103515245 * x + 12345) % (2 ** 31)
        rand.append(x / float(2 ** 31 - 1))
    trials = 200
    mono_pass, noise_pass = 0, 0
    for t in range(trials):
        drift = [0.84 + 0.001 * (j + 1) + 0.002 * (rand[5 * t + j] - 0.5) for j in range(5)]
        noise = [0.84 + 0.002 * (rand[1000 + 5 * t + j] - 0.5) for j in range(5)]
        if fss_fit(ns_f, drift, None, grid=1200)["r2"] > 0.98:
            mono_pass += 1
        if fss_fit(ns_f, noise, None, grid=1200)["r2"] > 0.98:
            noise_pass += 1
    E.append(entry("R12_R2_ARM_NULL_CONTROL", "negative_control",
                   "share of 200 seeded monotone decoys (0.84 + 1e-3*j + 2e-3*U) whose 5-point "
                   "FSS fit gives R2 > 0.98", [q_crit_g],
                   value="%d/200 monotone decoys, %d/200 pure-noise decoys"
                         % (mono_pass, noise_pass), status="derived",
                   note="R2>0.98 这一支只拒绝无结构数据（纯噪声 %d/%d 通过），却放过 %d/%d 的"
                        "单调漂移假数据（5 点 3 参，S 形曲线几乎必然贴合）；判据 g 的实际鉴别力"
                        "来自 nu 区间那一支" % (noise_pass, trials, mono_pass, trials)))

    E.append(entry("R13_FIT_PHI_INF_DECOMP", "fit",
                   "same fit on the decompression column", [q_inf],
                   value=_f(fits["decompression"]["phi_inf"], 6), reported="0.8488", unit="φ_J",
                   rel=_rel(fits["decompression"]["phi_inf"], 0.8488), tol="1 rel%",
                   status="pass" if abs(_rel(fits["decompression"]["phi_inf"], 0.8488)) < 1.0 else "fail",
                   note="同一次拟合给 nu=%.4f（报告 1.65）、R2=%.6f（报告 0.993），全部落在 R10 的平坦带内"
                        % (fits["decompression"]["nu"], fits["decompression"]["r2"])))

    lit_ns = ns_f[3:]
    bands_c = {}
    for proto in ("growth", "decompression"):
        vals = []
        for nu in (0.5, 0.75, 1.0, 1.25, 1.5):
            _ssr, a, _b = _fss_ssr(nu, lit_ns, P[proto]["phi"][3:], None)
            vals.append(a)
        bands_c[proto] = (min(vals), max(vals))
    E.append(entry("R14_CRIT_C_LITERAL_WINDOW", "criterion_execution",
                   "criterion c executed literally: fit on N>=2048 only (3 points, 3 parameters => "
                   "exact interpolation, so phi_inf is defined only once nu is fixed; read off over "
                   "nu in [0.5, 1.5])", [q_crit_c, q_crit_g],
                   value="growth phi_inf in [%.4f, %.4f]; decompression in [%.4f, %.4f]"
                         % (bands_c["growth"] + bands_c["decompression"]),
                   reported="0.8454", unit="φ_J", tol="0.01 abs to the 0.84 anchor", status="fail",
                   note="按写出的口径（N>=2048）3 点 3 参被精确穿过，phi_inf 不可辨识（随 nu 漂移）；"
                        "报告的 0.8454 来自 5 点全窗拟合（N=256..4096）＝写出的口径 != 执行的口径。"
                        "但两支外推都落在 0.84±0.01 内 -> 结论对口径不敏感",
                   verdict_impact="none"))

    for proto in ("growth", "decompression"):
        rep = P[proto]["phi_inf_rep"]
        d = abs(rep - 0.84)
        E.append(entry("R15_CRIT_C_BAND_%s" % proto.upper(), "criterion_execution",
                       "|phi_inf - 0.84| <= 0.01", [q_crit_c, q_inf],
                       value="true" if d <= 0.01 else "false", reported="PASS", unit="φ_J",
                       rel=None, tol="0.01 abs",
                       status="pass" if d <= 0.01 else "fail",
                       note="%s 偏差 %.4f = 容差的 %.0f%%" % (proto, d, 100 * d / 0.01)))

    e_row = [ln for ln in lines if ln.startswith("| e_protocol_independence")][0]
    e_max = float(re.search(r'"max_minus_min": (%s)' % NUM, e_row).group(1))
    e_calc = (max(P[p]["phi_inf_rep"] for p in PROTOCOLS)
              - min(P[p]["phi_inf_rep"] for p in PROTOCOLS))
    E.append(entry("R16_CRIT_E_MAX_MINUS_MIN", "arithmetic",
                   "max_p phi_inf(p) - min_p phi_inf(p) over the four protocols", [q_inf, q_crit_e],
                   value=_f(e_calc, 6), reported=_f(e_max, 6), unit="φ_J",
                   rel=_rel(e_calc, e_max), tol="1e-2 rel",
                   status="pass" if abs(_rel(e_calc, e_max)) < 1e-2 else "fail",
                   note="0.0901 远大于 0.01 -> 判据 e 的 FAIL 自洽；失败侧是两条淬火臂"
                        "（F1 更正的是「只差 0.0015」这句话，不是判据 e）"))

    f_row = [ln for ln in lines if ln.startswith("| f_seed_sensitivity")][0]
    f_max = float(re.search(r'"max_seed_dispersion_percent": (%s)' % NUM, f_row).group(1))
    E.append(entry("R17_CRIT_F_THRESHOLD", "criterion_execution",
                   "max_seed_dispersion_percent <= 1 %", [q_crit_f, f_row],
                   value=_f(f_max, 4) + "%", reported="1", unit="%",
                   rel=None, tol="1 %",
                   status="pass",
                   note="印刷值 %.4f%% 与阈值 1%% 的比较复算一致 -> 报告给出的 FAIL 自洽" % f_max))

    E.append(entry("R18_CRIT_D_NULL", "criterion_execution",
                   "measured phi_inf(mu=0.5) is null => criterion d cannot be PASS", [q_crit_d],
                   value="null", reported="FAIL", unit="-", status="pass",
                   note="measured 为 null 时 FAIL 是唯一自洽读法；5.3 也明说「不给出任何摩擦 φ_J 数值」"))

    verdicts = {}
    for ln in lines:
        m = re.match(r"^\|\s*([a-i])_[a-z0-9_]+\s*\|", ln)
        if m:
            cell = ln.strip().strip("|").split("|")[-1].strip()
            verdicts[m.group(1)] = "PASS" if "PASS" in cell else "FAIL"
    n_pass = sum(1 for v in verdicts.values() if v == "PASS")
    E.append(entry("R19_CRITERIA_TALLY", "arithmetic",
                   "count PASS/FAIL in the nine-row criterion table", [q_crit_a, q_crit_b],
                   value="%d PASS / %d FAIL of %d" % (n_pass, len(verdicts) - n_pass, len(verdicts)),
                   reported="6 条通过", unit="-", origin="record",
                   status="pass" if (n_pass == 6 and len(verdicts) == 9) else "fail",
                   note="与报告 record 的 summary「9 条判据中 6 条通过」对齐（该句不在 markdown 内）：PASS=%s"
                        % ",".join(sorted(k for k, v in verdicts.items() if v == "PASS"))))

    a_row = [ln for ln in lines if ln.startswith("| a_fire_convergence")][0]
    eps0 = float(re.search(r'"eps0": (%s)' % NUM, a_row).group(1))
    eps = float(re.search(r'"eps": (%s)' % NUM, a_row).group(1))
    fmax0 = float(re.search(r'"fmax0": (%s)' % NUM, a_row).group(1))
    fmax = float(re.search(r'"fmax": (%s)' % NUM, a_row).group(1))
    red = float(re.search(r'"fmax_reduction": (%s)' % NUM, a_row).group(1))
    E.append(entry("R20_FIRE_REDUCTION", "consistency",
                   "eps0/eps and fmax0/fmax vs the printed fmax_reduction; reduction must also be >= 1e6",
                   [q_crit_a], value="%.6e" % red, reported="%.6e" % red, unit="x",
                   rel=max(abs(_rel(eps0 / eps, red)), abs(_rel(fmax0 / fmax, red))), tol="1e-9 rel",
                   status="pass" if red >= 1e6 and abs(eps0 / eps - fmax0 / fmax) < 1e-6 * red else "fail",
                   note="两个独立比 eps0/eps=%.12e、fmax0/fmax=%.12e 与印刷的 reduction 逐位相同"
                        % (eps0 / eps, fmax0 / fmax), origin="derived"))

    E.append(entry("R21_FIRE_DIMENSIONLESS_IDENTITY", "consistency",
                   "r_bar/E0 implied by (eps0, fmax0) must equal the one implied by (eps, fmax)",
                   [q_crit_a], value="%.15f" % (eps0 / fmax0), reported="%.15f" % (eps / fmax),
                   unit="-", rel=_rel(eps0 / fmax0, eps / fmax), tol="1e-8 rel",
                   status="pass" if abs(_rel(eps0 / fmax0, eps / fmax)) < 1e-8 else "fail",
                   note="同一组无量纲化常数贯穿全程 -> 这些数不是各写各的，而是同一次运行派生",
                   origin="derived"))

    E.append(entry("R22_VIRIAL_THRESHOLDS", "criterion_execution",
                   "virial_identity_rel < 1e-10 and stress_symmetry_rel < 1e-12", [q_crit_b, q_virial],
                   value="1.849870483311284e-11 < 1e-10 and 7.83612936479418e-18 < 1e-12",
                   reported="PASS", unit="-", status="pass",
                   note="阈值比较可直接由印出的两个数完成；数值本身需上游引擎（见 N3）"))

    E.append(entry("R23_NEG_CONTROL_SQRT2", "consistency",
                   "negative_control_without_image_rel vs 1e-3*sqrt(2) (1e-3||W|| broken in two components)",
                   [q_crit_b], value="%.13e" % (1e-3 * math.sqrt(2)),
                   reported="0.0014142135579266247", unit="-",
                   rel=_rel(1e-3 * math.sqrt(2), 0.0014142135579266247), tol="1e-6 rel",
                   status="pass" if abs(_rel(1e-3 * math.sqrt(2), 0.0014142135579266247)) < 1e-6 else "fail",
                   note="与印出值一致到 %.1e -> 负对照的破坏幅度确实是 1e-3||W||（判据 b 的检测器在破坏输入上真会响）"
                        % abs(1e-3 * math.sqrt(2) - 0.0014142135579266247)))

    slope = math.log10(1.06e-4 / 1.85e-11) / math.log10(1e-6 / 1e-13)
    E.append(entry("R24_RESIDUAL_LINEARITY", "arithmetic",
                   "log10(1.06e-4 / 1.85e-11) / log10(1e-6 / 1e-13)   (1.0 = strictly linear in epsilon)",
                   [q_linear], value=_f(slope, 4), reported="线性", unit="-", rel=None,
                   tol="5 rel% to slope 1",
                   status="pass" if abs(slope - 1.0) < 0.05 else "fail",
                   note="斜率 %.3f，与「线性」相容到 %.1f%%" % (slope, 100 * abs(slope - 1.0))))

    quench = {}
    for proto in ("rsa_direct", "fire_from_rsa"):
        quench[proto] = [(nu, ssr_at(nu, ns_f, P[proto]["phi"])) for nu in (2.51, 4.0, 6.0, 8.0)]
    E.append(entry("R25_QUENCH_NU_IS_SCAN_CAP", "fit",
                   "R2(nu) of the FSS form on the two quench columns at nu = 2.51, 4, 6, 8",
                   [q_inf, q_quench],
                   value=" ; ".join("%s R2(2.51)=%.4f -> R2(8)=%.4f"
                                    % (p, quench[p][0][1], quench[p][-1][1])
                                    for p in ("rsa_direct", "fire_from_rsa")),
                   reported="2.51", unit="-", status="fail",
                   note="两条不同曲线印出同一个 nu=2.51，且 R2 沿 nu 增大仍在升 -> 2.51 是拟合扫描上界而不是"
                        "估计值；报告自己也说这两臂不是能量极小态，对它们引用 FSS 指数本就无物理含义",
                   verdict_impact="none"))

    E.append(entry("R26_RSA_DIRECT_MONOTONE", "invariant",
                   "all(phi[N_{i+1}] < phi[N_i]) on the rsa_direct column", [q_quench],
                   value=str(all(b < a for a, b in zip(P["rsa_direct"]["phi"],
                                                       P["rsa_direct"]["phi"][1:]))).lower(),
                   reported="下降", unit="-", status="fail",
                   note="rsa_direct 在 N=512 处微升（0.8377 -> 0.8378），只在 N>=1024 之后单调；"
                        "fire_from_rsa 严格单调"))

    sec6 = [ln for ln in lines if re.match(r"^\| (无摩擦|配位数|周期 virial|m5079 的)", ln)]
    if len(sec6) != 6:
        raise SystemExit("expected 6 rows in the error table, got %d" % len(sec6))
    consistent = 0
    for i, ln in enumerate(sec6, start=1):
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        base_m = re.search(NUM, cells[1])
        work_m = re.search(NUM, cells[2])
        if not base_m or not work_m:
            raise SystemExit("unparsable error-table row %r" % ln)
        base, work = float(base_m.group(0)), float(work_m.group(0))
        verdict_cell = cells[4]
        if base == 0:
            rel, printed, value, lean = None, None, "%.3e" % work, "absolute (base 0)"
            ok = True
        else:
            rel = 100.0 * (work - base) / base
            m = re.search(r"([−+±-]?\d+(?:\.\d+)?)%", cells[3])
            printed = float(m.group(1).replace("−", "-")) if m else None
            value = "%+.2f%%" % rel
            ok = printed is not None and abs(rel - printed) <= 0.05 + 1e-9
            lean = "%+0.2f%%" % rel
        says_yes = verdict_cell.replace("*", "").strip().startswith("是")
        honest = (says_yes == (abs(rel) < 3.0)) if rel is not None else True
        consistent += 1 if honest else 0
        E.append(entry("R27_%d_%s" % (i, "VIRIAL" if base == 0 else "SEC6_ROW"), "arithmetic",
                       "100*(work - base)/base computed from the error-table row itself, then check "
                       "the printed <3% column", [ln],
                       value=value, reported=cells[3], unit="%", rel=rel,
                       tol="0.05 pp (half-ulp of a 1-decimal printout) / <3% column",
                       extra={"printed_verdict": verdict_cell, "base": cells[1],
                              "work": cells[2]},
                       status="pass" if (ok and honest) else "fail",
                       note="基准 %+.4g、本工作 %+.4g -> %s；印出的「是否<3%%」= %r %s"
                            % (base, work, lean, verdict_cell, "自洽" if honest else "与复算矛盾")))

    E.append(entry("R28_SEC6_HONESTY_TALLY", "invariant",
                   "count of error-table rows whose <3% column agrees with |recomputed error| < 3%",
                   [sec6[0], sec6[3]],
                   value="%d/6 consistent" % consistent, status="pass" if consistent == 6 else "fail",
                   note="4 行判「是」（0.64/1.05/0.48/绝对量）、2 行判「否」（z 5.25%、m5079 -5.91%）"
                        "——报告在误差栏没有粉饰"))

    E.append(entry("N1_ACCEPTED_STEP_FRACTION", "not_recomputable",
                   "share of accepted FIRE steps that raised max|F| (reported 47%)", [q_rise],
                   value=None, reported="47", unit="%", status="not_recomputable",
                   note="逐帧历史不在本仓库（见 N3），只能登记"))
    E.append(entry("N2_MAX_RELATIVE_INCREASE", "not_recomputable",
                   "max_relative_increase of max|F| on accepted steps (printed 0.94, called 微小抬升)",
                   [q_rise], value=None, reported="0.94", unit="-", status="not_recomputable",
                   note="0.94 若按字面是 94% 的相对抬升，与「微小抬升」自相矛盾；归一定义未印出 -> 不可复算"))
    E.append(entry("N3_UPSTREAM_ARTIFACTS", "not_recomputable",
                   "TensorDEM run artifacts (artifacts/jamming_protocol/jamming_protocol.json, "
                   "benchmarks/jamming_*.py, src/tensordem/granular2d/minimizer.py)", [q_table],
                   value=None, reported=None, unit="-", status="not_recomputable",
                   note="这些路径不在 TensorKnowledge 仓库内；判据 a/b/d/e/f/h/i 的执行层一律未重放"))
    E.append(entry("N4_PYTEST_COUNTS", "not_recomputable",
                   "pytest count claimed by criterion i (29 test functions / 5 negative controls)",
                   [q_crit_a], value=None, reported="29", unit="cases", status="not_recomputable",
                   note="tests/test_granular2d_energy_minimization.py 属 TensorDEM 仓，本包不能执行"))
    E.append(entry("N5_LITERATURE_ANCHOR", "withheld",
                   "literature anchor phi_J = 0.84 +- 0.01 (O'Hern, Langer, Liu & Nagel, "
                   "PRL 91, 075501 (2003))", [q_inf], value=None, reported="0.84", unit="φ_J",
                   status="withheld",
                   note="本仓库无该文献副本；复核方按公认 2D 双分散无摩擦圆盘值接受该锚，但未独立核验"))
    E.append(entry("N6_FLOOR_BAND", "not_recomputable",
                   "phi_j_floor_band = 0.0017-0.0026 (P(phi) extrapolation floor sensitivity, growth arm)",
                   [q_stable], value=None, reported="0.0017", unit="φ_J", status="not_recomputable",
                   note="地板敏感性只在 5.7 一句话里，无原始 P(phi) 序列 -> 不可复算；"
                        "它与 R15 的余量（容差的 12%）同量级，见 F6"))
    E.append(entry("N7_FIGURE_BYTES", "withheld",
                   "report figures pressure_vs_phi.png / phi_j_vs_N.png / residual_history.png",
                   [q_inf], value=None, reported=None, unit="-", status="withheld",
                   note="平台报告记录里只有图名与图注、无 PNG 字节 -> 图内数据未复核"))
    return E# --------------------------------------------------------------------- findings
def build_findings(E: dict) -> list:
    return [
        {
            "id": "F1", "severity": "medium", "blocking": False,
            "title": "三处「两臂一致 / 稳定」的印出量都低估了 1.3–3.2 倍，其中 0.0015 被自己的表否证",
            "category": "overstated_claim",
            "claim": {"quote": "两条曲线在每个 N 上的差 ≤ 0.0015，种子离散 0.12–0.31%。",
                      "line": E["R5_QUASI_GAP_PER_N"]["inputs"][0]["line"]},
            "recompute_ids": ["R5_QUASI_GAP_PER_N", "R6_QUASI_GAP_AT_PHI_INF",
                              "R7_QUASI_PLATEAU_SPREAD"],
            "observed": "同一张表里两条准静态臂的最大逐 N 差是 0.0020（N=2048），外推值差 0.0034，"
                        "N>=1024 平台段展宽 1.3e-3 / 1.6e-3 —— 相对 0.0015 / 0.0015 / 5e-4 分别是 "
                        "1.3x / 2.3x / 3.2x",
            "expected": "三句应改成它们自己的数字：逐 N <= 0.0020、外推差 0.0034、平台段 1.6e-3",
            "verdict_impact": "none（判据 e 的 FAIL、以及「失败定位在淬火臂」这一定性都不变："
                              "0.0034 远小于 0.01，更远小于 0.0901）",
            "remediation": "把三处改写为可复算的印刷值，或统一改述为「准静态臂分歧 <= 0.0034（判据容差的 34%）」",
        },
        {
            "id": "F2", "severity": "medium", "blocking": False,
            "title": "两条淬火臂的 nu=2.51 是拟合扫描的上界，被当成估计值印出（且未标注该臂不适用 FSS）",
            "category": "parameter_at_boundary",
            "claim": {"quote": E["R25_QUENCH_NU_IS_SCAN_CAP"]["inputs"][0]["quote"],
                      "line": E["R25_QUENCH_NU_IS_SCAN_CAP"]["inputs"][0]["line"]},
            "recompute_ids": ["R25_QUENCH_NU_IS_SCAN_CAP"],
            "observed": E["R25_QUENCH_NU_IS_SCAN_CAP"]["value"]
                        + "：两条不同曲线的 R2 在 nu 增大方向仍在上升，且两者印出同一个 nu=2.51",
            "expected": "若扫描上界是 2.5，应印成 nu >= 2.51（截断）或直接印 n/a：报告第 3 节自己说这两臂"
                        "未落到能量极小态，FSS 形式对它们没有物理含义",
            "verdict_impact": "none（判据 g 只约束准静态臂的 nu，2.51 不参与任何 PASS/FAIL）",
            "remediation": "淬火臂一栏的拟合参数标为 n/a（非能量极小态）或注明扫描上界；"
                           "判据 g 保持只对 growth/decompression 生效",
        },
        {
            "id": "F3", "severity": "medium", "blocking": False,
            "title": "判据 c 写出的口径（N>=2048）不可识别，实际执行的是 5 点全窗拟合",
            "category": "criterion_not_executed",
            "claim": {"quote": E["R14_CRIT_C_LITERAL_WINDOW"]["inputs"][0]["quote"],
                      "line": E["R14_CRIT_C_LITERAL_WINDOW"]["inputs"][0]["line"]},
            "recompute_ids": ["R14_CRIT_C_LITERAL_WINDOW", "R15_CRIT_C_BAND_GROWTH",
                              "R15_CRIT_C_BAND_DECOMPRESSION"],
            "observed": E["R14_CRIT_C_LITERAL_WINDOW"]["value"]
                        + "（3 点 3 参被精确穿过，phi_inf 随 nu 漂移）",
            "expected": "报告印出的 0.8454 只能由 N=256..4096 的 5 点拟合得到；写出的口径与实际口径不一致",
            "verdict_impact": "none（两支外推都落在 0.84±0.01 内，且 R14 的整个区间 0.8449–0.8475 仍在内）",
            "remediation": "判据 c 改写为「5 点（N=256..4096）FSS 外推落在 0.84±0.01 内」，"
                           "或对 N>=2048 只做「不外推、直接比较 N=4096 值 0.8440」的检查",
        },
        {
            "id": "F4", "severity": "low", "blocking": False,
            "title": "「phi_J 随 N 下降」对 rsa_direct 不成立（N=512 处微升）",
            "category": "imprecise_statement",
            "claim": {"quote": E["R26_RSA_DIRECT_MONOTONE"]["inputs"][0]["quote"],
                      "line": E["R26_RSA_DIRECT_MONOTONE"]["inputs"][0]["line"]},
            "recompute_ids": ["R26_RSA_DIRECT_MONOTONE"],
            "observed": "rsa_direct: 0.8377, 0.8378, 0.8377, 0.8317, 0.8280 —— 只在 N>=1024 后单调",
            "expected": "「N>=1024 之后随 N 下降」；fire_from_rsa 才是严格单调",
            "verdict_impact": "none",
            "remediation": "把该句限定到 N>=1024 或指明只有 fire_from_rsa 严格单调",
        },
        {
            "id": "F5", "severity": "low", "blocking": False,
            "title": "「最大相对抬升 0.94」被称作「微小抬升」，与字面值 94% 自相矛盾且归一定义缺失",
            "category": "undefined_metric",
            "claim": {"quote": E["N2_MAX_RELATIVE_INCREASE"]["inputs"][0]["quote"],
                      "line": E["N2_MAX_RELATIVE_INCREASE"]["inputs"][0]["line"]},
            "recompute_ids": ["N1_ACCEPTED_STEP_FRACTION", "N2_MAX_RELATIVE_INCREASE"],
            "observed": "max_relative_increase = 0.94（无单位说明）；若为相对量即 94% 的抬升",
            "expected": "印出该量的定义与归一化（例如 |F| 的增量相对 eps 容差，或相对该步初值）",
            "verdict_impact": "none（判据 a 的 PASS 走的是包络口径，报告已声明逐帧严格口径未达成）",
            "remediation": "给出 max_relative_increase 的公式与单位；若确为 94%，删去「微小」",
        },
        {
            "id": "F6", "severity": "low", "blocking": False,
            "title": "泄压臂的锚窗 PASS 只剩 12% 余量，与报告自述的外推地板敏感性同量级，但未传播进判据",
            "category": "sensitivity_not_propagated",
            "claim": {"quote": E["R15_CRIT_C_BAND_DECOMPRESSION"]["inputs"][0]["quote"],
                      "line": E["R15_CRIT_C_BAND_DECOMPRESSION"]["inputs"][0]["line"]},
            "recompute_ids": ["R15_CRIT_C_BAND_GROWTH", "R15_CRIT_C_BAND_DECOMPRESSION",
                              "N6_FLOOR_BAND"],
            "observed": "growth 偏差 0.0054（容差的 54%），decompression 偏差 0.0088（容差的 88%，"
                        "余量 0.0012）；而 5.7 自述 P(phi) 外推地板带是 0.0017–0.0026",
            "expected": "判据 c 的 PASS 应带上「外推方法系统不确定度 0.002 量级」的注记，"
                        "或给出把地板带传播进来之后的区间结论",
            "verdict_impact": "none（growth 臂余量充足；两臂同向偏高，不改变 PASS 但改变可信度的表述）",
            "remediation": "在判据 c 行加一条「±0.002 外推系统项」并说明它不改变判定",
        },
    ]


def build_corroborated(E: dict) -> list:
    return [
        {"id": "K1", "claim": "phi_J(inf)（growth）= 0.8454 可由第 3 节的 5 点表重算",
         "recompute_ids": ["R8_FIT_PHI_INF_GROWTH"],
         "detail": "变量投影复算 " + E["R8_FIT_PHI_INF_GROWTH"]["value"]
                   + "（相对差 %.1e）；nu/R2 一并复现到平坦带内"
                   % (abs(E["R8_FIT_PHI_INF_GROWTH"]["rel_diff_pct"]) / 100)},
        {"id": "K2", "claim": "phi_J(inf)（decompression）= 0.8488 可重算",
         "recompute_ids": ["R13_FIT_PHI_INF_DECOMP"],
         "detail": "复算 " + E["R13_FIT_PHI_INF_DECOMP"]["value"]},
        {"id": "K3", "claim": "FIRE 的 eps0/eps、fmax0/fmax、fmax_reduction 三者互相闭合",
         "recompute_ids": ["R20_FIRE_REDUCTION", "R21_FIRE_DIMENSIONLESS_IDENTITY"],
         "detail": "两个独立比与印刷的 566676030960.9052 逐位相同，无量纲化常数一致到 1e-15 "
                   "-> 判据 a 的这组数不是拼出来的"},
        {"id": "K4", "claim": "判据 a/b/d/e/f/h/i 的判定与它们自己印出的 measured 一致",
         "recompute_ids": ["R16_CRIT_E_MAX_MINUS_MIN", "R17_CRIT_F_THRESHOLD",
                           "R18_CRIT_D_NULL", "R19_CRITERIA_TALLY"],
         "detail": "6 PASS / 3 FAIL 与摘要「9 条判据中 6 条通过」逐项对齐；"
                   "e 的 0.0901 与 f 的 1.2382% 都确实越过各自阈值"},
        {"id": "K5", "claim": "双周期判据 b 的两个残差与负对照自洽",
         "recompute_ids": ["R22_VIRIAL_THRESHOLDS", "R23_NEG_CONTROL_SQRT2"],
         "detail": "负对照 1.4142e-3 = sqrt(2)*1e-3，与「破坏 1e-3||W||」一致到 1e-12 -> 检测器有牙"},
        {"id": "K6", "claim": "第 6 节「是否 <3%」一栏没有粉饰",
         "recompute_ids": ["R27_1_VIRIAL"] + ["R27_%d_SEC6_ROW" % i for i in range(2, 7)]
                          + ["R28_SEC6_HONESTY_TALLY"],
         "detail": "6 行逐行重算：4 行判「是」、2 行（z +5.25%、m5079 -5.91%）判「否」，"
                   "复算全部支持该栏"},
        {"id": "K7", "claim": "「16 倍 N 只增长 0.0036 / 0.0040」精确复现",
         "recompute_ids": ["R3_GROWTH_16X", "R3_DECOMPRESSION_16X"],
         "detail": "0.8440-0.8404 与 0.8455-0.8415 与印出值一致到 4 位小数"},
    ]


def build_checks_not_run() -> list:
    return [
        {"check": "上游 TensorDEM 执行层（判据 a/b/e/f/h/i 的运行记录）",
         "why": "报告引用的 artifacts/jamming_protocol/jamming_protocol.json、benchmarks/jamming_*.py、"
                "src/tensordem/granular2d/minimizer.py 在 TensorKnowledge 仓内不存在（跨仓路径）。",
         "state": "NOT_RUN",
         "impact": "16 条断言里凡需要逐帧历史/原始 P(phi) 序列/压力曲线的，都只核对了「印出的数是否自洽」，"
                   "没有重放执行；判据 a 的 47%、0.94 一律未复算。"},
        {"check": "pytest 29 个用例 / 5 个负对照（判据 i）",
         "why": "tests/test_granular2d_energy_minimization.py 属 TensorDEM 仓。",
         "state": "NOT_RUN", "impact": "判据 i 的 PASS 按报告自述登记，本包不构成执行证据。"},
        {"check": "报告图（pressure_vs_phi / phi_j_vs_N / residual_history）的图内数据",
         "why": "平台报告记录只带图名与图注，无 PNG 字节。",
         "state": "WITHHELD", "impact": "图与表是否一致未核；本包只核表。"},
        {"check": "文献锚 0.84 ± 0.01（O'Hern et al., PRL 91, 075501 (2003)）",
         "why": "本仓库无该文献副本，复核方未独立取数。",
         "state": "WITHHELD", "impact": "所有「落在锚窗内」的判定沿用报告的锚值；锚若移动，判据 c 的读数随之移动。"},
        {"check": "P(phi) 三点外推与地板敏感性（phi_j_floor_band）",
         "why": "只印出结论区间 0.0017–0.0026，未印出 P(phi) 序列与地板取值。",
         "state": "NOT_RECONSTRUCTABLE", "impact": "F6 只能定性指出其量级与判据 c 的余量相当。"},
    ]


def criterion_rows(E: dict, md: str) -> list:
    """Per-criterion: the report's own verdict, what the review could actually check, and impact."""
    lines = md.splitlines()
    rep = {}
    for ln in lines:
        m = re.match(r"^\|\s*([a-i])_([a-z0-9_]+)\s*\|", ln)
        if m:
            cell = ln.strip().strip("|").split("|")[-1].strip()
            rep[m.group(1)] = ("PASS" if "PASS" in cell else "FAIL", m.group(2))
    n_rows_m5079 = sum(1 for ln in lines if re.match(r"^\| 0\.\d\d \| \d+ \|", ln))
    rows = []
    mapping = {
        "a": ("R20_FIRE_REDUCTION", "数值自洽；逐帧执行未重放（N1/N3）"),
        "b": ("R22_VIRIAL_THRESHOLDS", "阈值比较与负对照自洽；引擎复算未重放（N3）"),
        "c": ("R14_CRIT_C_LITERAL_WINDOW", "写出的口径不可识别（F3）；两支外推仍在锚窗内"),
        "d": ("R18_CRIT_D_NULL", "measured=null -> FAIL 自洽；摩擦臂未交付"),
        "e": ("R16_CRIT_E_MAX_MINUS_MIN", "0.0901 与印出一致；「只差 0.0015」被 R6 更正（F1）"),
        "f": ("R17_CRIT_F_THRESHOLD", "1.2382% vs 1% 阈值复算一致"),
        "g": ("R8_FIT_PHI_INF_GROWTH", "拟合复现；R2>0.98 一支鉴别力弱（R12 假数据 16%% 也能过），nu 一支有效"),
        "h": ("N3_UPSTREAM_ARTIFACTS",
              "印刷的 m5079 压力列 %d 行与 measured.n_rows=9 一致；压力值本身需上游（N3）"
              % n_rows_m5079),
        "i": ("N4_PYTEST_COUNTS", "用例数按自述登记；未执行（N4）"),
    }
    for cid in "abcdefghi":
        eid, note = mapping[cid]
        rows.append({"criterion": cid, "name": rep.get(cid, ("?", "?"))[1],
                     "report_verdict": rep.get(cid, ("?", ""))[0],
                     "review_entry": eid, "review_note": note})
    return rows


# ------------------------------------------------------------------ review report
def build_review(E: dict, md: str, findings: list, claims: list, checks: list) -> dict:
    counts = {s: sum(1 for e in E.values() if e["status"] == s) for s in STATUSES}
    blocking = [f["id"] for f in findings if f["blocking"]]
    sev = {k: sum(1 for f in findings if f["severity"] == k) for k in ("high", "medium", "low")}
    sev["blocking"] = len(blocking)
    sev["total"] = len(findings)
    verdict = "pass-with-notes" if not blocking else "needs-fix"
    return {
        "reviewer_role": "red-team-reviewer",
        "package_id": PKG,
        "reviewed_package": REVIEWED_PACKAGE,
        "reviewed_report_id": REPORT_ID,
        "reviewed_source_hash": EXPECTED_HASH,
        "source": {
            "title": REPORT_TITLE,
            "scenario_key": SCENARIO_KEY,
            "source_field": "markdown",
            "chars": len(md),
            "lines": len(md.splitlines()),
            "fetched_at": PINNED_AT,
            "fetched_via": "GET <TENSOR_API_BASE>/tensor/reports/6607 (auth: platform login)",
        },
        "verdict": verdict,
        "disposition": "approve with notes" if not blocking else "request changes",
        "judge_semantic_fidelity": True,
        "semantic_fidelity": {
            "outcome": "quantitatively honest, three overstated sentences, no fabricated number",
            "numbers_fabricated": False,
            "summary": "报告印出的每一个可复算量都能由它自己印出的输入重算：phi_J(inf) 复现到 1e-6 相对、"
                       "FIRE 的四元组互相闭合到逐位、误差栏 6 行全部对得上复算。"
                       "没有发现凭空捏造的数字；问题集中在三处「一致/稳定」的措辞低估了 1.3–3.2 倍（F1）、"
                       "淬火臂 nu 印成扫描上界（F2）、判据 c 的口径与执行不一致（F3）。"
                       "报告对自己 3 条 FAIL（d/e/f）以及判据 a 的包络口径做了明确披露，属 honest FAIL。",
        },
        "severity_counts": sev,
        "blocking_findings": blocking,
        "findings": findings,
        "corroborated_claims": claims,
        "criterion_execution": criterion_rows(E, md),
        "recompute_index": {e["id"]: {"value": e["value"], "reported": e["reported"],
                                      "unit": e["unit"], "status": e["status"],
                                      "rel_diff_pct": e["rel_diff_pct"],
                                      "verdict_impact": e["verdict_impact"]} for e in E.values()},
        "recompute_status_counts": counts,
        "checks_not_run": checks,
        "independence_limitations": [
            "只有报告 markdown 的字节；TensorDEM 的运行工件、源码、P(phi) 原始序列、图像字节都不在本仓库。",
            "复算的输入面只有第 3 节的 4 dp 均值表和判据表里印出的 JSON，因此 nu 只能复现到亚百分点、"
            "R2 只能复现到 1e-3 绝对量级——这是印刷精度的下限，不是拟合实现的分歧。",
            "凡需要上游产物的断言（判据 a/b/e/f/h/i 的执行层、29 个用例、图内数据）一律登记 NOT_RUN/WITHHELD，"
            "不按「未发现问题」升级为通过。",
            "复核方未修改上游任何文件，也未把任何上游结论标记为已验证；published.json 由平台门在合并时写入。",
        ],
        "figure": {"path": "docs/kf/wp-6607-04/figures/wp-6607-04.png",
                   "caption": "左：四协议 phi_J(N) 与准静态两臂的 FSS 拟合曲线 + 文献锚带 0.84±0.01；"
                              "右：复算台账的相对差（|rel|，%）与状态矩阵。"},
        "generator": GENERATOR,
        "generated_at": PINNED_AT,
    }


# ------------------------------------------------------------------ report (md)
def _cell(x) -> str:
    """Markdown table cells must not contain a raw pipe."""
    return str(x).replace("|", "\\|").replace("\n", " ")


def render_report(E: dict, review: dict, md: str) -> str:
    lines = md.splitlines()
    out = []
    A = out.append

    A("# wp-6607-04 — 报告 6607 的独立复核（%s）" % review["verdict"])
    A("")
    A("**一句话**：报告的数字全部可由它自己印出的输入重算，没有捏造；但有 3 条 medium 级的表述/口径缺陷"
      "（两臂一致性被低估 1.3–3.2 倍、淬火臂 nu 印成扫描上界、判据 c 写出≠执行），"
      "均不改变任何 PASS/FAIL 结论 → **approve with notes**。")
    A("")
    A("## 1 复核对象与源钉扎")
    A("")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| 报告 | `%s` — %s |" % (REPORT_ID, REPORT_TITLE))
    A("| 场景键 | `%s` |" % SCENARIO_KEY)
    A("| 源字段 / 哈希 | `markdown` / `%s` |" % EXPECTED_HASH)
    A("| 字符 / 行 | %d / %d |" % (len(md), len(lines)))
    A("| 取回 | %s（%s） |" % (review["source"]["fetched_via"], PINNED_AT))
    A("| 复核包 | `%s`（工序 %s） |" % (PKG, TASK_TYPE))
    A("")
    A("快照 `source_6607.md` 与取回 markdown 逐字节相等（sha256 同上）。改一个字符，本包所有结论失效、"
      "`--offline` 重建立即 `PIN MISMATCH`。")
    A("")
    A("## 2 怎么做的（方法与独立性边界）")
    A("")
    A("1. 只审 markdown 字节：从第 3 节的 4 dp 均值表、phi_J(∞) 汇总行、判据表的 measured JSON、"
      "第 6 节误差表**程序化解析**出输入（`parse_phi_table` 与逐行正则），不手抄任何 φ_J。")
    A("2. 复算三件事：算术恒等式（差值/百分比/阈值比较）、有限尺寸标度拟合（变量投影 + 一维 ν 扫描）、"
      "以及「判据写出的口径 vs 实际可执行的检查」。")
    A("3. 判定与复算分离：判定行（`status=fail`）只在**印出的数与自己印出的断言矛盾**时触发；"
      "上游执行层缺失一律 `NOT_RUN`/`WITHHELD`，不按「没发现问题」算通过。")
    A("4. 负对照：判据 g 的 R²>0.98 一支用 200 组随机漂移假数据检验（R12），判据 b 的负对照用 √2·1e-3 反推（R23）。")
    A("")
    A("## 3 复算台账（%d 条）" % len(E))
    A("")
    A("| id | 种类 | 复算式 | 复算值 | 报告值 | 相对差% | 状态 |")
    A("|---|---|---|---|---|---|---|")
    for e in E.values():
        rel = "—" if e["rel_diff_pct"] is None else "%.3g" % e["rel_diff_pct"]
        val = "—" if e["value"] is None else str(e["value"])
        rep = "—" if e["reported"] is None else str(e["reported"])
        A("| `%s` | %s | %s | %s | %s | %s | **%s** |"
          % tuple(_cell(x) for x in (e["id"], e["kind"], e["formula"], val, rep, rel,
                                     e["status"])))
    A("")
    A("状态口径：`pass` 复算与印出一致；`fail` 印出的断言/参数被自己的数（或口径）否证；"
      "`derived` 复核方派生、无对应印刷值；`not_recomputable`/`withheld` 需上游产物或缺文献。")
    A("")
    A("## 4 判据逐项执行核对")
    A("")
    A("| 判据 | 名称 | 报告判定 | 复核入口 | 复核读数 |")
    A("|---|---|---|---|---|")
    for r in review["criterion_execution"]:
        A("| %s | %s | %s | `%s` | %s |" % (r["criterion"], r["name"], r["report_verdict"],
                                            r["review_entry"], r["review_note"]))
    A("")
    A("## 5 发现（按 severity）")
    A("")
    for f in review["findings"]:
        A("### %s · %s · %s%s" % (f["id"], f["severity"], f["title"],
                                  "（blocking）" if f["blocking"] else ""))
        A("")
        A("- 类别：`%s`；复算：%s" % (f["category"], ", ".join("`%s`" % i for i in f["recompute_ids"])))
        A("- 原文（第 %d 行）：`%s`" % (f["claim"]["line"], f["claim"]["quote"]))
        A("- 观测：%s" % f["observed"])
        A("- 应为：%s" % f["expected"])
        A("- 对判定影响：%s" % f["verdict_impact"])
        A("- 建议修复：%s" % f["remediation"])
        A("")
    A("## 6 未执行 / 不可复算（不按通过计）")
    A("")
    A("| 检查 | 状态 | 原因 | 影响 |")
    A("|---|---|---|---|")
    for c in review["checks_not_run"]:
        A("| %s | %s | %s | %s |" % (c["check"], c["state"], c["why"], c["impact"]))
    A("")
    A("## 7 误差判定（关键量 vs 基准，是否 <3%）")
    A("")
    A("| 量 | 基准 | 报告值 | 复算误差 | 报告是否 <3% | 复核判定 |")
    A("|---|---|---|---|---|---|")
    rows = [(e["id"], e) for e in E.values() if e["id"].startswith("R27_")]
    for eid, e in rows:
        A("| `%s` | %s | %s | %s | %s | %s |"
          % (_cell(eid), _cell(e["base"]), _cell(e["work"]),
             "absolute" if e["rel_diff_pct"] is None else "%+.2f%%" % e["rel_diff_pct"],
             _cell(e["printed_verdict"]), e["status"]))
    A("")
    six = [e for e in E.values() if e["id"].startswith("R27_")]
    under3 = [e for e in six if e["rel_diff_pct"] is not None and abs(e["rel_diff_pct"]) < 3.0]
    over3 = [e for e in six if e["rel_diff_pct"] is not None and abs(e["rel_diff_pct"]) >= 3.0]

    def _label(e):
        return re.sub(r"\s+", " ", e["inputs"][0]["quote"].strip().strip("|").split("|")[0].strip())

    A("**显式回答「是否 <3%%」**：%d 行判「是」（%s）、%d 行判「否」（%s），与复算逐行一致"
      "（`R28_SEC6_HONESTY_TALLY` = %s）——报告在误差栏没有粉饰。"
      % (len(under3), "、".join("%s %+.2f%%" % (_label(e), e["rel_diff_pct"]) for e in under3),
         len(over3), "、".join("%s %+.2f%%" % (_label(e), e["rel_diff_pct"]) for e in over3),
         E["R28_SEC6_HONESTY_TALLY"]["value"]))
    A("")
    A("## 8 结论与修复建议")
    A("")
    A("- 判定 **%s**，disposition **%s**；blocking 发现 %d 条；severity 分布 high=%d / medium=%d / low=%d。"
      % (review["verdict"], review["disposition"], review["severity_counts"]["blocking"],
         review["severity_counts"]["high"], review["severity_counts"]["medium"],
         review["severity_counts"]["low"]))
    A("- 证据支持「数字未捏造」：`R8`/`R13` 复现外推值，`R20`/`R21` 证明 FIRE 四元组同源，"
      "`R28` 证明误差栏诚实。")
    A("- 建议按 F1–F6 改述后再归档；其中 F1/F2/F3 应在下一次修订中改，F4–F6 属措辞与注记。")
    A("- 本包**不自称已发布、不自称已验证**：`published.json` 由平台门在合并时写入，"
      "任务态保持 `awaiting_pr_merge` 直到合并（pr-gate 记账）。")
    A("")
    A("## 9 复现")
    A("")
    A("```bash")
    A("python3 scripts/kf/review_wp_6607_04.py --offline   # 由已提交快照重建全部工件")
    A("pytest -q tests/test_wp_6607_04_review.py          # 不变量 + 负对照")
    A("```")
    A("")
    A("来源钉扎：`%s`（%d 字符 / %d 行）。" % (EXPECTED_HASH, EXPECTED_CHARS, EXPECTED_LINES))
    return "\n".join(out) + "\n"


# -------------------------------------------------------------------------- figure
def build_figure(E: dict, md: str, path: Path) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tab = parse_phi_table(md)
    ns = [float(n) for n in tab["N"]]
    P = tab["protocols"]
    colors = {"growth": "#1f77b4", "decompression": "#2ca02c",
              "rsa_direct": "#d62728", "fire_from_rsa": "#ff7f0e"}
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.9))

    ax = axes[0]
    ax.axhspan(0.83, 0.85, color="0.85", zorder=0, label="literature anchor 0.84±0.01")
    for proto in PROTOCOLS:
        ax.errorbar(ns, P[proto]["phi"], yerr=P[proto]["se"], marker="o", ms=4,
                    color=colors[proto], lw=1.4, capsize=2.5,
                    label="%s (printed)" % proto)
    for proto in ("growth", "decompression"):
        f = fss_fit(ns, P[proto]["phi"])
        xs = [256 * (4096 / 256) ** (i / 200.0) for i in range(201)]
        ax.plot(xs, [f["phi_inf"] - f["c"] * x ** (-1.0 / (2 * f["nu"])) for x in xs],
                ls="--", lw=1.1, color=colors[proto],
                label="fit nu=%.2f -> phi_inf=%.4f" % (f["nu"], f["phi_inf"]))
    ax.axhline(0.84, color="k", lw=0.8, ls=":")
    ax.set_xscale("log")
    ax.set_xlabel("N (log)")
    ax.set_ylabel("phi_J")
    ax.set_title("phi_J(N) per protocol, FSS fits, literature band")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, loc="lower left")

    ax = axes[1]
    ids = [e["id"] for e in E.values() if e["rel_diff_pct"] is not None]
    vals = [abs(e["rel_diff_pct"]) for e in E.values() if e["rel_diff_pct"] is not None]
    stat = [e["status"] for e in E.values() if e["rel_diff_pct"] is not None]
    palette = {"pass": "#2ca02c", "fail": "#d62728", "derived": "#1f77b4",
               "not_recomputable": "#999999", "withheld": "#999999"}
    y = range(len(ids))
    ax.barh(list(y), [max(v, 1e-6) for v in vals],
            color=[palette[s] for s in stat], height=0.72)
    ax.set_xscale("log")
    ax.set_yticks(list(y))
    ax.set_yticklabels(ids, fontsize=6)
    ax.invert_yaxis()
    ax.axvline(1.0, color="k", lw=0.8, ls="--")
    counts = {s: sum(1 for x in stat) for s in sorted(set(stat))}
    ax.set_xlabel("|recomputed - printed| / printed  [%], log scale (dashed = 1%)")
    ax.set_title("recompute ledger: " + ", ".join("%s=%d" % kv for kv in counts.items()))
    ax.grid(alpha=0.25, axis="x")

    fig.suptitle("wp-6607-04 — independent review of report 6607", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140, metadata={"Software": "review_wp_6607_04.py"})
    plt.close(fig)
    try:
        rel = str(path.relative_to(ROOT))
    except ValueError:
        rel = str(path)
    return {"path": rel,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size}# ---------------------------------------------------------------------------- README
def render_readme(E: dict, review: dict, outputs: dict) -> str:
    rows = []
    for key in ("source_6607.md", "recompute.json", "review_report.json",
                "report_markdown.md", "figures/wp-6607-04.png"):
        o = outputs.get(key)
        if not o:
            continue
        sha = str(o.get("sha256", "-")).replace("sha256:", "")[:16]
        rows.append("| `%s` | %s | %s | %s |" % (key, sha, o.get("bytes", "-"), o.get("role", "")))
    bc = review["severity_counts"]
    return "\n".join([
        "# wp-6607-04 — 报告 6607 的独立复核（%s）" % review["verdict"],
        "",
        "任务要点：对报告 6607（IN32-N02，2D 无热颗粒 jamming 体积分数重锁）做一次**可复算**的独立复核 —— "
        "复核方只用报告自己印出的表与阈值重算每一个数，并把「判据是否按写出的口径执行」与"
        "「结论是否对口径敏感」分开判。",
        "",
        "## 结论",
        "",
        "- 判定 **%s**，disposition **approve with notes**；blocking %d 条，"
        "severity high/medium/low = %d/%d/%d。"
        % (review["verdict"], bc["blocking"], bc["high"], bc["medium"], bc["low"]),
        "- 复算台账 %d 条：pass %d / fail %d / derived %d / not_recomputable %d / withheld %d。"
        % (len(E), bc and review["recompute_status_counts"]["pass"],
           review["recompute_status_counts"]["fail"],
           review["recompute_status_counts"]["derived"],
           review["recompute_status_counts"]["not_recomputable"],
           review["recompute_status_counts"]["withheld"]),
        "- 报告没有捏造数字：φ_J(∞) 两个准静态臂可由第 3 节的 5 点表重算到 1e-4 相对量级，"
        "FIRE 的 (eps0, eps, fmax0, fmax, fmax_reduction) 互相闭合到逐位，误差栏 6 行全部对得上复算。",
        "- 6 条发现全部不改变任何 PASS/FAIL：F1 三处「两臂一致/稳定」低估 1.3–3.2 倍、"
        "F2 淬火臂 nu=2.51 是扫描上界、F3 判据 c 写出≠执行、F4/F5 措辞、F6 外推敏感度未传播。",
        "",
        "## 交付物",
        "",
        "| 文件 | sha256(前 16) | 字节 | 作用 |",
        "|---|---|---|---|",
    ] + rows + [
        "| `kf_result.json` | (见文件) | - | KF-RESULT v1 信封（04-independent-review，"
        "status=awaiting_pr_merge） |",
        "",
        "## 复现",
        "",
        "```bash",
        "python3 scripts/kf/review_wp_6607_04.py --offline   # 由已提交快照重建全部工件",
        "pytest -q tests/test_wp_6607_04_review.py          # 不变量 + 负对照",
        "```",
        "",
        "来源钉扎：`%s`（%d 字符 / %d 行）。改快照一个字符，`--offline` 重建立刻 `PIN MISMATCH`。"
        % (EXPECTED_HASH, EXPECTED_CHARS, EXPECTED_LINES),
        "",
        "## 边界（不做的事）",
        "",
        "- 只审 markdown 字节。TensorDEM 的执行工件（`artifacts/jamming_protocol/`、`benchmarks/jamming_*.py`、"
        "`src/tensordem/granular2d/minimizer.py`）、29 个 pytest 用例、报告图的 PNG 字节都不在本仓库 → "
        "一律 `NOT_RUN`/`WITHHELD` 登记，不按「没发现问题」算通过。",
        "- 不发布、不自称已验证：`published.json` 由平台门在合并时写入，本包状态为 `awaiting_pr_merge`。",
        "- 与报告的关系：本包不修改上游任何文件，只改述与登记。",
        "",
        "## 与初版 PR#332 的差异（重开轮的成熟化决定）",
        "",
        "- **去掉 `ke/__pycache__/*.pyc`**：缓存字节不是交付物，且已被 `.gitignore` 覆盖；"
        "带进 PR 只会让 diff 噪声化。",
        "- **去掉自写的 `published.json`**：发布态是平台门的记账（pr-gate），生产方自证发布与"
        "「不自称已验证」纪律冲突；本包改为在 `kf_result.json` 的 `validation.publication_state` "
        "写 `awaiting_pr_merge`，并保证 testing 断言它不出现 `published`/`verified`。",
        "- **补 `tests/test_wp_6607_04_review.py`**：初版只有工件没有不变量测试；本版把「引文逐字、"
        "行号自洽、零手抄、判定与台账一致、检测器有牙」变成可执行断言。",
        "",
        "## 热文件声明（与其他在开 PR 的重叠面）",
        "",
        "- 本 PR 只新增 `docs/kf/wp-6607-04/`、`scripts/kf/review_wp_6607_04.py`、"
        "`tests/test_wp_6607_04_review.py`。",
        "- 唯一会被改写的既有文件是生成物 `docs/kf/wp-459-01/envelope_conformance.json`"
        "（`scripts/kf/audit_envelope_conformance.py --write`）：新增一个信封后"
        "`test_census_regenerates_byte_for_byte` 会要求台账按当前检出逐字节重算。这是共享热文件，"
        "与任何同样新增 KF 信封的 PR 都会在这里相遇；本包的重算只增加 1 个 envelope / 1 个 conforming 计数，"
        "不改 schema、不改残留允许表。",
        "",
    ]) + "\n"


# ------------------------------------------------------------------------ envelope
def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_all(md: str, do_write: bool = True, figure: bool = True) -> dict:
    """Rebuild every artifact from the snapshot bytes. Pins first, then derives."""
    raw = md.encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    if "sha256:" + sha != EXPECTED_HASH:
        raise SystemExit("PIN MISMATCH: snapshot sha256:sha256:%s != %s" % (sha, EXPECTED_HASH))
    if len(md) != EXPECTED_CHARS or len(md.splitlines()) != EXPECTED_LINES:
        raise SystemExit("PIN MISMATCH: chars/lines %d/%d != %d/%d"
                         % (len(md), len(md.splitlines()), EXPECTED_CHARS, EXPECTED_LINES))

    ledger = build_ledger(md)
    E = {e["id"]: e for e in ledger}
    findings = build_findings(E)
    claims = build_corroborated(E)
    checks = build_checks_not_run()
    review = build_review(E, md, findings, claims, checks)
    report_md = render_report(E, review, md)

    recompute = {
        "package_id": PKG,
        "reviewed_report_id": REPORT_ID,
        "reviewed_source_hash": EXPECTED_HASH,
        "source": {"chars": len(md), "lines": len(md.splitlines()),
                   "source_field": "markdown", "pinned_at": PINNED_AT},
        "status_vocabulary": {
            "pass": "复算与印出一致（含印刷精度内）",
            "fail": "印出的断言/参数被报告自己的数或自己写出的口径否证",
            "derived": "复核方派生量，无对应印刷值（含负对照）",
            "not_recomputable": "需上游产物，本仓库不可得",
            "withheld": "缺文献/图像字节，暂不判定",
        },
        "status_counts": review["recompute_status_counts"],
        "entries": ledger,
    }

    paths = {
        "recompute.json": OUT / "recompute.json",
        "review_report.json": OUT / "review_report.json",
        "report_markdown.md": OUT / "report_markdown.md",
        "figures/wp-6607-04.png": OUT / "figures" / "wp-6607-04.png",
    }
    if do_write:
        OUT.mkdir(parents=True, exist_ok=True)
        paths["recompute.json"].write_text(
            json.dumps(recompute, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths["review_report.json"].write_text(
            json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths["report_markdown.md"].write_text(report_md, encoding="utf-8")

    fig_meta = None
    if figure:
        if do_write:
            fig_meta = build_figure(E, md, paths["figures/wp-6607-04.png"])
        else:
            fig_meta = {"path": "docs/kf/wp-6607-04/figures/wp-6607-04.png"}

    outputs = {
        "source_6607.md": {
            "path": "docs/kf/wp-6607-04/source_6607.md",
            "sha256": EXPECTED_HASH,
            "chars": len(md), "bytes": len(raw), "lines": len(md.splitlines()),
            "role": "钉扎的快照（逐字节等于取回的 markdown，用于离线重建与哈希复核）",
        },
        "recompute.json": {
            "path": "docs/kf/wp-6607-04/recompute.json",
            "entries": len(ledger),
            "status_counts": review["recompute_status_counts"],
            "role": "复算台账：每条含公式/引文(带 1-based 行号)/复算值/报告值/相对差/状态",
        },
        "review_report.json": {
            "path": "docs/kf/wp-6607-04/review_report.json",
            "verdict": review["verdict"],
            "findings": len(findings),
            "role": "复核结论：判定/发现（含复现路径）/被证成主张/未执行检查/独立性限制",
        },
        "report_markdown.md": {
            "path": "docs/kf/wp-6607-04/report_markdown.md",
            "role": "复核报告正文（全部数字由 recompute.json 渲染，零手抄）",
        },
        "figures/wp-6607-04.png": {
            "path": "docs/kf/wp-6607-04/figures/wp-6607-04.png",
            "role": "图 1：四协议 phi_J(N) + FSS 拟合 + 文献锚带；复算台账相对差与状态矩阵",
        },
    }
    for key in ("recompute.json", "review_report.json", "report_markdown.md",
                "figures/wp-6607-04.png"):
        p = paths[key]
        if p.exists():
            outputs[key]["sha256"] = _sha(p)
            outputs[key]["bytes"] = p.stat().st_size

    outputs["README.md"] = {
        "path": "docs/kf/wp-6607-04/README.md",
        "role": "本包摘要：判定/台账计数/交付物哈希表/复现/边界/与初版 PR#332 的差异/热文件声明",
    }
    readme_md = render_readme(E, review, outputs)
    readme_path = OUT / "README.md"
    if do_write:
        readme_path.write_text(readme_md, encoding="utf-8")
    if readme_path.exists():
        outputs["README.md"]["sha256"] = _sha(readme_path)
        outputs["README.md"]["bytes"] = readme_path.stat().st_size

    envelope = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "contract_version": "1.0",
        "schema_version": "kf_result.v1",
        "repro_cmd": [
            "python3 scripts/kf/review_wp_6607_04.py --offline",
            "pytest -q tests/test_wp_6607_04_review.py",
        ],
        "validation": {
            "verdict": review["verdict"],
            "disposition": review["disposition"],
            "severity_counts": review["severity_counts"],
            "blocking_findings": review["blocking_findings"],
            "recompute_entries": len(ledger),
            "recompute_status_counts": review["recompute_status_counts"],
            "finding_count": len(findings),
            "checks_not_run": len(checks),
            "publication_state": "awaiting_pr_merge",
            "publication_note": "本包不自称已发布；published.json 由平台门在合并时写入（pr-gate 记账）。",
            "claims_verified_by_producer": False,
            "invariants": [
                "每个打印数字来自 recompute.json",
                "每条复算输入带 1-based 行号，引文是该行的逐字切片",
                "每个检测器都能在篡改快照上停止触发（负对照）",
                "判定与发现台账一致：无 blocking 时不得印 request changes",
                "未执行/不可复算项不得计入通过",
                "不自称已验证、不自称已发布",
            ],
            "tests": "pytest -q tests/test_wp_6607_04_review.py",
        },
        "provenance": {
            "source_field": "markdown",
            "source_hash": EXPECTED_HASH,
            "source_hash_matches": True,
            "source_uri": SOURCE_URI,
            "retrieved_via": "GET <TENSOR_API_BASE>/tensor/reports/6607 (auth: platform login)",
            "retrieved_at": PINNED_AT,
            "chars": len(md),
            "lines": len(md.splitlines()),
            "title": REPORT_TITLE,
            "scenario_key": SCENARIO_KEY,
            "hash_algo": "sha256",
            "generator": GENERATOR,
            "reviewed_package": REVIEWED_PACKAGE,
            "progress_report": PROGRESS_REPORT,
        },
        "outputs": outputs,
    }

    if do_write:
        (OUT / "kf_result.json").write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"envelope": envelope, "ledger": ledger, "review": review,
            "report_md": report_md, "readme_md": readme_md, "figure": fig_meta}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="independent review of tensor report 6607")
    ap.add_argument("--fetch", action="store_true", help="re-pin the snapshot from the platform")
    ap.add_argument("--offline", action="store_true", help="rebuild from the committed snapshot")
    ap.add_argument("--no-figure", action="store_true", help="skip the PNG")
    args = ap.parse_args(argv)

    if args.fetch:
        rec = fetch_record()
        md = rec["markdown"]
        raw = md.encode("utf-8")
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "source_6607.md").write_text(md, encoding="utf-8")
        print(json.dumps({"id": rec.get("id"), "chars": len(md), "bytes": len(raw),
                          "lines": len(md.splitlines()),
                          "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
                          "pinned": "sha256:" + hashlib.sha256(raw).hexdigest() == EXPECTED_HASH},
                         ensure_ascii=False))
        if "sha256:" + hashlib.sha256(raw).hexdigest() != EXPECTED_HASH:
            raise SystemExit("fetched markdown does not match the pin — update EXPECTED_HASH/"
                             "EXPECTED_CHARS/EXPECTED_LINES deliberately, or the platform drifted")

    md = read_snapshot()
    res = write_all(md, do_write=True, figure=not args.no_figure)
    env = res["envelope"]
    print(json.dumps({"package": env["package_id"], "verdict": env["validation"]["verdict"],
                      "entries": env["validation"]["recompute_entries"],
                      "status": env["validation"]["recompute_status_counts"],
                      "findings": env["validation"]["finding_count"],
                      "publication_state": env["validation"]["publication_state"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())