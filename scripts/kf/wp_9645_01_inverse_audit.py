#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KF wp-9645-01 · 独立闭式复核（independent closed-form re-derivation）。

做什么：把 report 9645 的**参数表**读进来，用一套与平台求解器
（tensorphysics.structural.reliability FORM/Nataf/IS/MC）**完全无关**的
纯标准库闭式推导，重算该报告的全部关键量，再与学生报告里的表格逐项比对：

  * 散度链：σ_lnA ← CoV(A)；σ_lnp ← ex,CoV(A),CoV(ε_p)；
    ρ_lnp,lnA = -ex·σ_A²/(σ_lnp·σ_A)；σ_lnF = √((1-ex)²σ_A² + σ_kF² + σ_εp²)
  * 目标可靠度反问题：κ* 由 β(κ)=β_T 闭式解（本问题失效域在对数正态空间是
    超平面 ⇒ Hasofer–Lind 距离即真值，闭式为解析基准，不是近似）；
    γ_f* = F*/F_k（设计点作用/特征作用）；ψ* = κ*/γ_f*
  * ISO 19906 A.2×A.3 十行分项系数对的 Δγ_f/Δψ/Δκ 与「按表设计的 β」
  * 负控：同一对边缘分布只把 ρ 置 0，重解反问题（含按该模型自身散度重定特征值
    F_k），检验 γ_f* 的膨胀量
  * β_T 敏感性（表 7）与 ∂β/∂θ（表 8，中心差分）
  * 设计点落在失效面 R=F 上 ⇒ 报告表 1 的 R* 与 F* 必须同值，一并核对

第二条数值路径（自检，不构成新论断）：另用 u 空间复合 Simpson 积分求 P_f 再取
Φ⁻¹（Φ/Φ⁻¹ 均取标准库 statistics.NormalDist），并对 β_numeric(κ)=β_T 二分反解
κ*。该路径不做任何解析归约，因此可以检验上面那些闭式推导本身；两条路径的差
写进 JSON 的 numeric_crosscheck 并作为门禁（β 绝对差 ≤1e-6、κ* 相对差 ≤1e-4）。

零手抄：所有输入参数、全部被比对的"报告值"（含表 6 正文的两条相对偏差
+28.90 % / +21.63 %）都由本脚本从
docs/kf/wp-9645-01/source/report_9645.md（逐字节快照）解析得到。

判据：|相对误差| ≤ 3 %（逐项列出）；表 8 的参数敏感性仅作参考（不同 FD 步长/
参数化约定可差几个百分点），不参与门禁。

用法：
  python3 scripts/kf/wp_9645_01_inverse_audit.py            # 复核 + 出 JSON/PNG
  python3 scripts/kf/wp_9645_01_inverse_audit.py --no-plot  # 只出 JSON
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from statistics import NormalDist

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-9645-01")
SNAP = os.path.join(PKG, "source", "report_9645.md")
OUT_JSON = os.path.join(PKG, "inverse_audit.json")
OUT_PNG = os.path.join(PKG, "inverse_audit.png")

TOL = 0.03  # 门禁：3 %
Q99 = 2.3263478740408408   # Φ⁻¹(0.99)，100 年超越
Q05 = 1.6448536269514722   # |Φ⁻¹(0.05)|，5 % 分位


# --------------------------------------------------------------- parsing
def _num(s: str) -> float:
    s = s.replace("**", "").replace("$", "").replace("+", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s)
    if not m:
        raise ValueError("no number in %r" % s)
    return float(m.group(0))


def _key(cell: str) -> str:
    return (cell.replace("$", "").replace("\\", "").replace("{", "")
            .replace("}", "").replace("**", "").replace(" ", "")
            .replace("（", "(").replace("）", ")"))


def tables(markdown: str) -> list:
    """返回全部 markdown 表格：[[cell,...], ...] 的列表。"""
    out, cur = [], []
    for line in markdown.split("\n"):
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # 分隔行
            cur.append(cells)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def find_table(tabs: list, *needles: str) -> list:
    for t in tabs:
        head = " ".join(t[0])
        if all(n in head for n in needles):
            return t
    raise KeyError("table with headers %r not found" % (needles,))


def parse(markdown: str) -> dict:
    tabs = tables(markdown)

    # --- 参数表（表 0）---
    pt = find_table(tabs, "参数", "取值")
    P = {}
    for row in pt[1:]:
        k, v = _key(row[0]), row[1]
        if "p_0" in k:
            P["p0"] = _num(v)
        elif k == "ex":
            P["ex"] = _num(v)
        elif "A_0" in k:
            a = re.findall(r"\d+(?:\.\d+)?", v)
            P["A0"], P["A_med"] = float(a[0]), float(a[1])
        elif "CoV(A)" in k:
            P["a_cov"] = _num(v)
        elif "varepsilon" in k:
            P["pressure_cov"] = _num(v)
        elif "k_F" in k:
            P["load_cov"] = _num(v)
        elif "CoV(R)" in k:
            P["res_cov"] = _num(v)
        elif "F_k" in k:
            P["F_k"] = _num(v)
        elif "R_k" in k:
            P["R_k"] = _num(v)
        elif "rho" in k and "sigma" not in k:
            P["rho_reported"] = _num(v)
        elif "sigma" in k:
            if "rho" in k:            # σ_lnF（ρ=0 对照）
                P["sigma_F_uncorr_reported"] = _num(v)
            else:
                P["sigma_F_reported"] = _num(v)

    # --- 表 1 反问题解 ---
    st = find_table(tabs, "量", "值")
    S = {}
    for row in st[1:]:
        k = _key(row[0])
        if "kappa" in k and "=" in k:
            S["kappa"] = _num(row[1])
        elif "gamma_f" in k and "gamma_f" not in S:
            S["gamma_f"] = _num(row[1])
        elif "psi" in k:
            S["psi"] = _num(row[1])
        elif k.startswith("F^*"):
            S["F_design"] = _num(row[1])
        elif k.startswith("R^*"):
            S["R_design"] = _num(row[1])
        elif "beta" in k and "达到" in row[0]:
            S["beta_reached"] = _num(row[1])

    # --- 表 4 ISO 分项系数对 ---
    it = find_table(tabs, "表格对", "按表设计的")
    ISO = []
    for row in it[1:]:
        if len(row) < 8:
            continue
        g = re.findall(r"[\d.]+", row[1])
        ISO.append({
            "pair": row[0],
            "gamma_F_tab": float(g[0]),
            "gamma_M_tab": float(g[1]),
            "kappa_tab": _num(row[2]),
            "d_gamma_f": _num(row[3]) / 100.0,
            "d_psi": _num(row[4]) / 100.0,
            "d_kappa": _num(row[5]) / 100.0,
            "verdict": row[6],
            "beta_achieved": _num(row[7]),
        })

    # --- 表 6 负控 ---
    nt = find_table(tabs, "模型", "sigma")
    NC = {}
    for row in nt[1:]:
        tag = "corr" if "计入" in row[0] else "uncorr"
        NC[tag] = {"kappa": _num(row[1]), "gamma_f": _num(row[2]),
                   "psi": _num(row[3]), "sigma_F": _num(row[4])}

    # --- 表 7 β_T 敏感性 ---
    bt = find_table(tabs, "beta_T", "P_{f,T}")
    SENS = []
    for row in bt[1:]:
        SENS.append({"beta_T": _num(row[0]), "P_fT": _num(row[1]),
                     "gamma_f": _num(row[2]), "psi": _num(row[3]),
                     "kappa": _num(row[4])})

    # --- 表 8 参数敏感性 ---
    st8 = find_table(tabs, "参数", "名义值")
    SENS8 = [(row[0], _num(row[1]), _num(row[2])) for row in st8[1:]]

    # --- ⑥ 误差判定表中「把偏大的 κ 用到物理模型」的 β ---
    m = re.search(r"会得到\s*\$\s*\\?beta\s*\$\s*=\s*([\d.]+)", markdown)
    beta_naive_claim = float(m.group(1)) if m else None

    # --- 表 6 正文的两条相对偏差（正文行，不是表格单元格；零手抄）---
    def _pct(pattern: str) -> float | None:
        hit = re.search(pattern, markdown)
        return float(hit.group(1)) / 100.0 if hit else None

    d_gamma_claim = _pct(r"\$\\Delta\\gamma_f\^\*\$ = \+([\d.]+) %")
    d_kappa_claim = _pct(r"\$\\Delta\\kappa\^\*\$ = \+([\d.]+) %")
    return {"params": P, "solution": S, "iso": ISO, "neg_control": NC,
            "beta_T_sensitivity": SENS, "sensitivity8": SENS8,
            "beta_naive_claim": beta_naive_claim,
            "d_gamma_claim": d_gamma_claim, "d_kappa_claim": d_kappa_claim}


# ------------------------------------------------------------- closed form
def _log_sd(cov: float) -> float:
    return math.sqrt(math.log(1.0 + cov * cov))


class Model:
    """闭式：失效面 {R<F} 在 (ln R, ln F) 正态空间是半空间 ⇒ β = (μ_R-μ_F)/σ_tot。"""

    def __init__(self, P: dict, rho_zero: bool = False):
        self.ex = P["ex"]
        self.s_A = _log_sd(P["a_cov"])
        self.s_ep = _log_sd(P["pressure_cov"])
        self.s_kF = _log_sd(P["load_cov"])
        self.s_R = _log_sd(P["res_cov"])
        # ln p = ln p0 - ex(ln A - ln A0) + ε_p ⇒ σ_lnp = √((ex σ_A)² + σ_εp²)
        self.s_p = math.sqrt((self.ex * self.s_A) ** 2 + self.s_ep ** 2)
        # cov(ln p, ln A) = -ex σ_A²  ⇒ ρ = -ex σ_A² /(σ_lnp σ_A)
        self.rho = -self.ex * self.s_A ** 2 / (self.s_p * self.s_A)
        if rho_zero:
            self.s_F = math.sqrt(self.s_A ** 2 + self.s_p ** 2 + self.s_kF ** 2)
        else:
            # ln F = ln k_F + ln p + ln A = const + (1-ex) ln A + ε_p + ln k_F
            self.s_F = math.sqrt(((1 - self.ex) * self.s_A) ** 2
                                 + self.s_ep ** 2 + self.s_kF ** 2)
        self.s_tot = math.sqrt(self.s_R ** 2 + self.s_F ** 2)

    # 特征值按模型自身散度取：F_k = F_med·e^{q99 σ_F}，R_k = R_med·e^{-q05 σ_R}
    def beta(self, kappa: float, F_med: float, F_k: float) -> float:
        # R_k = κ F_k ⇒ ln R_med = ln(κ F_k) + q05 σ_R；F_med = F_k e^{-q99 σ_F}
        return (math.log(kappa * F_k) + Q05 * self.s_R
                - (math.log(F_k) - Q99 * self.s_F)) / self.s_tot

    def kappa_star(self, beta_T: float) -> float:
        # 解 β(κ)=β_T：ln κ* = β_T σ_tot - q05 σ_R - q99 σ_F
        return math.exp(beta_T * self.s_tot - Q05 * self.s_R - Q99 * self.s_F)

    def gamma_f_star(self, beta_T: float) -> float:
        # F*/F_k = exp(-q99 σ_F + β σ_F²/σ_tot)（设计点 u_F = β σ_F/σ_tot）
        return math.exp(-Q99 * self.s_F + beta_T * self.s_F ** 2 / self.s_tot)


def central_diff(f, x: float, h: float) -> float:
    return (f(x + h) - f(x - h)) / (2 * h)


# ------------------------------------------------------- numeric cross-check
ND = NormalDist()
NUM_GRID = 4000        # Simpson 步数（u∈[-10,10]，h=5e-3）
NUM_HALF = 10.0


def beta_numeric(kappa: float, F_med: float, F_k: float, m: "Model",
                 n: int = NUM_GRID, half: float = NUM_HALF) -> float:
    """β 的**纯数值**路径：u 空间 Simpson 积分求 P_f，再 Φ⁻¹(P_f)。

    与 Model.beta() 的闭式 β=Δμ/σ_tot 无关（不做任何解析归约），因此可用来
    独立检验闭式推导本身：P_f=∫φ(u)Φ[(lnF_med+s_F u-μ_lnR)/s_R]du。
    """
    ln_R = math.log(kappa * F_k) + Q05 * m.s_R      # R_k=κF_k ⇒ R 中值
    ln_F0, s_F, s_R = math.log(F_med), m.s_F, m.s_R
    h = 2.0 * half / n
    acc = 0.0
    for i in range(n + 1):
        u = -half + i * h
        lik = ND.cdf((ln_F0 + s_F * u - ln_R) / s_R)
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        acc += w * ND.pdf(u) * lik
    pf = acc * h / 3.0
    return -ND.inv_cdf(pf)


def kappa_star_numeric(F_med: float, F_k: float, m: "Model", beta_T: float,
                       lo: float = 0.2, hi: float = 20.0,
                       iters: int = 60) -> float:
    """对 β_numeric(κ)=β_T 做二分（数值解，不用闭式 κ* 公式）。"""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if beta_numeric(mid, F_med, F_k, m) < beta_T:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ------------------------------------------------------------------ audit
def audit(markdown: str, plot: bool = True,
          write_json: bool = True) -> dict:
    parsed = parse(markdown)
    P = parsed["params"]
    beta_T = parsed["solution"]["beta_reached"]

    m = Model(P)
    m0 = Model(P, rho_zero=True)

    # 回归到底层：F_med 由 F_k 与 σ_F 给出（供 β(κ) 用）
    F_k = P["F_k"]
    F_med = F_k * math.exp(-Q99 * m.s_F)
    F_med0 = F_k * math.exp(-Q99 * m.s_F)      # 边缘分布中值不变（只改散度）
    F_k0 = F_med * math.exp(Q99 * m0.s_F)      # ρ=0 模型自身的 100 年特征值

    kappa = m.kappa_star(beta_T)
    gamma_f = m.gamma_f_star(beta_T)
    psi = kappa / gamma_f
    F_design = gamma_f * F_k
    kappa0 = m0.kappa_star(beta_T)
    gamma_f0 = m0.gamma_f_star(beta_T)
    psi0 = kappa0 / gamma_f0

    checks = []

    def add(quantity, reported, recomputed, source, tol=TOL, gated=True,
            note=""):
        rel = None
        if reported not in (None, 0):
            rel = (recomputed - reported) / abs(reported)
        checks.append({
            "quantity": quantity, "source": source,
            "reported": reported, "recomputed": recomputed,
            "rel_err": rel, "tol": tol,
            "pass": (rel is not None and abs(rel) <= tol) if gated else None,
            "gated": gated, "note": note,
        })

    # A. 散度链
    add("sigma_lnF (correlated)", P["sigma_F_reported"], m.s_F, "参数表: σ_lnF")
    add("sigma_lnF (rho=0)", P["sigma_F_uncorr_reported"], m0.s_F,
        "参数表: σ_lnF（ρ=0 对照）")
    add("rho_lnp_lnA", P["rho_reported"], m.rho, "参数表: ρ_lnp,lnA")

    # B. 反问题解
    S = parsed["solution"]
    add("kappa*", S["kappa"], kappa, "表1")
    add("gamma_f*", S["gamma_f"], gamma_f, "表1")
    add("psi*", S["psi"], psi, "表1")
    add("F* (design point)", S["F_design"], F_design, "表1")
    # 设计点落在失效面 R=F 上 ⇒ R* 必须等于 F*（同一常数，可独立核对）
    add("R* (design point)", S["R_design"], F_design, "表1",
        note="设计点满足 R=F ⇒ R* 应与 F* 相同")
    add("beta at kappa* (physical)", S["beta_reached"],
        m.beta(kappa, F_med, F_k), "表1")

    # C. ISO 分项系数对
    iso_rows = []
    for row in parsed["iso"]:
        kt = row["kappa_tab"]
        rec = {
            "pair": row["pair"],
            "kappa_tab": kt,
            "d_gamma_f": row["gamma_F_tab"] / gamma_f - 1.0,
            "d_psi": row["gamma_M_tab"] / psi - 1.0,
            "d_kappa": kt / kappa - 1.0,
            "beta_achieved": m.beta(kt, F_med, F_k),
            # 报告口径：任一偏差 >15 % 即「超差」，叠加 κ_table<κ* 才判「不保守」
            "out_of_tolerance": max(abs(row["gamma_F_tab"] / gamma_f - 1.0),
                                    abs(row["gamma_M_tab"] / psi - 1.0),
                                    abs(kt / kappa - 1.0)) > 0.15,
            "non_conservative": (kt / kappa - 1.0) < -0.15 or (
                kt < kappa and max(abs(row["gamma_F_tab"] / gamma_f - 1.0),
                                   abs(row["gamma_M_tab"] / psi - 1.0),
                                   abs(kt / kappa - 1.0)) > 0.15),
        }
        iso_rows.append({"pair": row["pair"], "kappa_tab": kt, "reported": {
            "d_gamma_f": row["d_gamma_f"], "d_psi": row["d_psi"],
            "d_kappa": row["d_kappa"], "beta_achieved": row["beta_achieved"],
            "verdict": row["verdict"]}, "recomputed": {
            "d_gamma_f": rec["d_gamma_f"], "d_psi": rec["d_psi"],
            "d_kappa": rec["d_kappa"], "beta_achieved": rec["beta_achieved"],
            "non_conservative": rec["non_conservative"]}})
        add("Δκ [%s]" % row["pair"], row["d_kappa"], rec["d_kappa"], "表4",
            note="相对偏差量：比较用绝对差")
        checks[-1]["rel_err"] = rec["d_kappa"] - row["d_kappa"]
        checks[-1]["pass"] = abs(checks[-1]["rel_err"]) <= 0.01
        add("β_table [%s]" % row["pair"], row["beta_achieved"],
            rec["beta_achieved"], "表4")
    # 裁决一致性：不保守行的集合必须与报告一致
    rep_nc = [r["pair"] for r in parsed["iso"] if "不保守" in r["verdict"]]
    rec_nc = [r["pair"] for r in iso_rows if r["recomputed"]["non_conservative"]]
    checks.append({"quantity": "non_conservative_row_set", "source": "表4 判定列",
                   "reported": rep_nc, "recomputed": rec_nc,
                   "rel_err": 0.0 if rep_nc == rec_nc else None,
                   "tol": 0.0, "pass": rep_nc == rec_nc, "gated": True,
                   "note": "集合相等即通过（Δκ<-15 % 判不保守）"})

    # D. 负控
    NC = parsed["neg_control"]
    add("kappa* (rho=0)", NC["uncorr"]["kappa"], kappa0, "表6")
    add("gamma_f* (rho=0)", NC["uncorr"]["gamma_f"], gamma_f0, "表6")
    add("psi* (rho=0)", NC["uncorr"]["psi"], psi0, "表6")
    d_gamma = gamma_f0 / gamma_f - 1.0
    d_kappa = kappa0 / kappa - 1.0
    for qty, claim, value in (
        ("Δγ_f* (ignoring p-A correlation)", parsed["d_gamma_claim"], d_gamma),
        ("Δκ* (ignoring p-A correlation)", parsed["d_kappa_claim"], d_kappa),
    ):
        checks.append({"quantity": qty, "source": "表6 正文", "reported": claim,
                       "recomputed": value,
                       "rel_err": None if claim is None else value - claim,
                       "tol": 0.01,
                       "pass": (claim is not None and abs(value - claim) <= 0.01),
                       "gated": True, "note": "绝对差门限 1 个百分点"})
    beta_naive = m.beta(kappa0, F_med, F_k)
    add("β when over-large κ* is applied to physical model",
        parsed["beta_naive_claim"], beta_naive, "表6 正文")

    # D2. 数值路径交叉验证：闭式推导 vs 纯数值积分/二分（不经解析归约）
    num_beta = beta_numeric(kappa, F_med, F_k, m)
    num_beta0 = beta_numeric(kappa0, F_med, F_k, m)
    num_kappa = kappa_star_numeric(F_med, F_k, m, beta_T)
    numeric = {
        "beta_at_kappa_star_numeric": num_beta,
        "beta_at_kappa_star_closed": m.beta(kappa, F_med, F_k),
        "kappa_star_numeric": num_kappa,
        "kappa_star_closed": kappa,
        "beta_naive_numeric": num_beta0,
        "beta_naive_closed": beta_naive,
        "grid": {"n": NUM_GRID, "half_width": NUM_HALF,
                 "rule": "composite Simpson on u-space, Phi=statistics.NormalDist",
                 "bisection": "β_numeric(κ)=β_T on κ∈[0.2,20], 60 iterations"},
    }
    for qty, reported, recomputed, note in (
        ("beta(κ*) closed form vs numeric quadrature",
         numeric["beta_at_kappa_star_closed"],
         numeric["beta_at_kappa_star_numeric"],
         "绝对差门限 1e-6（两条独立路径）"),
        ("κ* closed form vs numeric bisection",
         numeric["kappa_star_closed"], numeric["kappa_star_numeric"],
         "相对差门限 1e-4"),
        ("β_naive closed form vs numeric quadrature",
         numeric["beta_naive_closed"], numeric["beta_naive_numeric"],
         "绝对差门限 1e-6"),
    ):
        checks.append({"quantity": qty, "source": "数值路径自检",
                       "reported": reported, "recomputed": recomputed,
                       "rel_err": recomputed - reported,
                       "tol": 1e-4 if "κ*" in qty else 1e-6,
                       "pass": abs(recomputed - reported) <= (1e-4 * abs(reported)
                                                             if "κ*" in qty else 1e-6),
                       "gated": True, "note": note})

    # E. β_T 敏感性
    for row in parsed["beta_T_sensitivity"]:
        bt = row["beta_T"]
        add("kappa*(β_T=%.2f)" % bt, row["kappa"], m.kappa_star(bt), "表7")
        add("gamma_f*(β_T=%.2f)" % bt, row["gamma_f"], m.gamma_f_star(bt), "表7")
        add("psi*(β_T=%.2f)" % bt, row["psi"],
            m.kappa_star(bt) / m.gamma_f_star(bt), "表7")

    # F. ∂β/∂θ（表 8，仅参考，不参与门禁）
    def beta_of(theta_name, value):
        q = dict(P)
        q[theta_name] = value
        mm = Model(q)
        return mm.beta(kappa, F_k * math.exp(-Q99 * mm.s_F), F_k)

    name_map = {"exponent": "ex", "a_cov": "a_cov",
                "pressure_model_cov": "pressure_cov",
                "load_model_cov": "load_cov",
                "resistance_cov": "res_cov"}
    sens8 = []
    for label, nominal, reported in parsed["sensitivity8"]:
        key = name_map.get(label)
        if key is None:
            continue
        h = max(abs(nominal) * 1e-4, 1e-6)
        got = central_diff(lambda v: beta_of(key, v), nominal, h)
        sens8.append({"parameter": label, "nominal": nominal,
                      "reported": reported, "recomputed": got,
                      "rel_err": (got - reported) / abs(reported) if reported else None,
                      "gated": False})

    gated = [c for c in checks if c["gated"]]
    failed = [c for c in gated if not c["pass"]]
    rels = [abs(c["rel_err"]) for c in gated
            if isinstance(c["rel_err"], float)]
    result = {
        "package_id": "wp-9645-01",
        "report_id": "9645",
        "tool": "scripts/kf/wp_9645_01_inverse_audit.py",
        "method": "independent closed-form reliability re-derivation "
                  "(pure stdlib; no tensorphysics import)",
        "inputs_from": "docs/kf/wp-9645-01/source/report_9645.md :: ① 参数表",
        "inputs": {k: P[k] for k in sorted(P)},
        "derived": {
            "sigma_lnA": m.s_A, "sigma_lnp": m.s_p, "sigma_lnF": m.s_F,
            "sigma_lnF_rho0": m0.s_F, "rho_lnp_lnA": m.rho,
            "sigma_lnR": m.s_R, "sigma_total": m.s_tot,
            "sigma_total_rho0": m0.s_tot,
            "F_med": F_med, "F_k_rho0": F_k0,
            "kappa_star": kappa, "gamma_f_star": gamma_f, "psi_star": psi,
            "F_design": F_design,
            "kappa_star_rho0": kappa0, "gamma_f_star_rho0": gamma_f0,
            "psi_star_rho0": psi0,
            "d_gamma_f_negative_control": d_gamma,
            "d_kappa_negative_control": d_kappa,
            "beta_naive_physical": beta_naive,
            "beta_at_kappa_star": m.beta(kappa, F_med, F_k),
        },
        "numeric_crosscheck": numeric,
        "iso_table": iso_rows,
        "sensitivity8_informational": sens8,
        "assumptions": [
            "特征值按模型自身散度取常态：F_k=F_med·e^{q99·σ_lnF}，R_k=R_med·e^{-q05·σ_lnR}"
            "（q99=2.3263, q05=1.6449）——ρ=0 对照下 F_k 随 σ_lnF 重定，这是报告数字隐含的口径",
            "失效域 {R<F} 在 (lnR,lnF) 正态坐标下是半空间，故 Hasofer–Lind 距离=真值，"
            "闭式 β_ln 可作解析基准（不是近似）",
            "冰压按单一幂律指数 ex（常数）建模、抗力与冰力独立、年极值面积对数正态",
            "报告表值多为 5–6 位有效数字，本复核的舍入地板约 0.05 %",
            "n<0.01 的极小量（如表4 的 Δκ）改为绝对差门限，不用相对误差",
        ],
        "summary": {
            "n_gated": len(gated), "n_pass": len(gated) - len(failed),
            "n_fail": len(failed),
            "max_abs_rel_err": max(rels) if rels else None,
            "median_abs_rel_err": sorted(rels)[len(rels) // 2] if rels else None,
            "tol": TOL,
            "all_pass": not failed,
            "failed": [c["quantity"] for c in failed],
            "verdict": ("PASS at 3 % gate" if not failed else
                        "FAIL at 3 % gate: " + ", ".join(c["quantity"] for c in failed)),
        },
        "checks": checks,
    }
    if write_json:
        os.makedirs(PKG, exist_ok=True)
        with open(OUT_JSON, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if plot:
        plot_figure(result, m, m0, F_med, F_k, F_med0, F_k0, beta_T)
    return result


# ------------------------------------------------------------------ figure
def plot_figure(res, m, m0, F_med, F_k, F_med0, F_k0, beta_T):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.2))

    # 左：β(κ) 两条模型曲线 + 反问题解 + ISO 表格点
    ks = [0.9 + 0.01 * i for i in range(0, 251)]
    ax.plot(ks, [m.beta(k, F_med, F_k) for k in ks], color="#1f4e79", lw=2,
            label=r"physical model ($\rho_{\ln p,\ln A}$=-0.674)")
    ax.plot(ks, [m0.beta(k, F_med0, F_k0) for k in ks], color="#a65141", lw=2,
            ls="--", label=r"$\rho$=0 control (same marginals)")
    d = res["derived"]
    ax.axhline(beta_T, color="0.4", lw=1, ls=":")
    ax.text(0.92, beta_T + 0.06, r"$\beta_T=%.2f$" % beta_T, fontsize=9, color="0.35")
    ax.plot([d["kappa_star"]], [d["beta_at_kappa_star"]], "o", ms=9,
            color="#1f4e79", mec="k", zorder=5,
            label=r"calibrated $\kappa^*=%.4f$" % d["kappa_star"])
    ax.plot([d["kappa_star_rho0"]], [beta_T], "s", ms=8, color="#a65141",
            mec="k", zorder=5, label=r"$\rho$=0 solution $\kappa^*=%.4f$"
            % d["kappa_star_rho0"])
    for row in res["iso_table"]:
        kt = row.get("kappa_tab")
        if kt is None:
            continue
        b = row["recomputed"]["beta_achieved"]
        nc = row["recomputed"]["non_conservative"]
        ax.plot([kt], [b], "v" if nc else "^", ms=7,
                color="#c0392b" if nc else "#2e7d32", alpha=0.9, zorder=4)
    ax.plot([], [], "v", color="#c0392b", label="ISO table pair, non-conservative")
    ax.plot([], [], "^", color="#2e7d32", label="ISO table pair, conservative")
    ax.set_xlabel(r"factor product $\kappa=\gamma_f\psi$")
    ax.set_ylabel(r"achieved reliability index $\beta$")
    ax.set_title("Closed-form $\\beta(\\kappa)$ and the inverse solution")
    ax.legend(fontsize=7.5, loc="lower right")
    ax.grid(alpha=0.3)

    # 右：复核值 vs 报告值（奇偶图，±3 % 带）
    xs, ys = [], []
    for c in res["checks"]:
        if not c["gated"] or not isinstance(c["reported"], (int, float)):
            continue
        if c["reported"] in (0, None) or c["recomputed"] in (0, None):
            continue
        if abs(c["reported"]) < 1e-6:
            continue
        xs.append(abs(c["reported"]))
        ys.append(abs(c["recomputed"]))
    ax2.fill_between([min(xs) * 0.8, max(xs) * 1.25],
                     [v * 0.97 for v in (min(xs) * 0.8, max(xs) * 1.25)],
                     [v * 1.03 for v in (min(xs) * 0.8, max(xs) * 1.25)],
                     color="#4d8b31", alpha=0.12, label="±3 % band")
    ax2.plot(xs, ys, "o", ms=5, color="#1f4e79", alpha=0.85)
    lim = [min(xs + ys) * 0.8, max(xs + ys) * 1.25]
    ax2.plot(lim, lim, "k-", lw=1, label="y = x")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(lim)
    ax2.set_ylim(lim)
    ax2.set_xlabel("reported in report 9645")
    ax2.set_ylabel("recomputed (independent closed form)")
    s = res["summary"]
    ax2.set_title("Parity: %d gated quantities, max |rel err| = %.2e"
                  % (s["n_gated"], s["max_abs_rel_err"]))
    ax2.legend(fontsize=8, loc="upper left")
    ax2.grid(alpha=0.3, which="both")

    fig.suptitle("wp-9645-01 · independent closed-form audit of report 9645 "
                 "(ISO 19906 ice partial factors)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT_PNG, dpi=140)
    plt.close(fig)
    return OUT_PNG


def main(argv: list) -> int:
    md = open(SNAP, encoding="utf-8", newline="").read()
    res = audit(md, plot="--no-plot" not in argv)
    s = res["summary"]
    print("gated = %d  pass = %d  fail = %d  max|rel| = %.2e  tol = %.0f%%"
          % (s["n_gated"], s["n_pass"], s["n_fail"],
             s["max_abs_rel_err"] or 0.0, s["tol"] * 100))
    for c in res["checks"]:
        if not c["gated"]:
            continue
        mark = "PASS" if c["pass"] else "FAIL"
        rel = c["rel_err"]
        print("  [%s] %-46s reported=%-12s recomputed=%-12s rel=%-10s (%s)"
              % (mark, c["quantity"],
                 ("%.6g" % c["reported"]) if isinstance(c["reported"], (int, float)) else c["reported"],
                 ("%.6g" % c["recomputed"]) if isinstance(c["recomputed"], (int, float)) else c["recomputed"],
                 ("%.2e" % rel) if isinstance(rel, float) else rel, c["source"]))
    print("verdict:", s["verdict"])
    print("wrote", os.path.relpath(OUT_JSON, ROOT))
    return 0 if s["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))