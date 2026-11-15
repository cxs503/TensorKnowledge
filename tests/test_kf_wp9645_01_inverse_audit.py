#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-9645-01 · 独立闭式复核（inverse audit）的验收回归。

被验对象：`scripts/kf/wp_9645_01_inverse_audit.py` 与它产出的
`docs/kf/wp-9645-01/inverse_audit.{json,png}`。

本测试文件只做一件事：证明这份复核**不是自证**——
  * 输入是已注册资产的逐字节快照（哈希与 `sha256.txt` 钉住值比对）；
  * 复核路径不 import 任何平台求解器（纯标准库 + 闭式/数值积分）；
  * 结果对报告的 46+ 项关键量在 3 % 门内（逐项）；
  * 四条负控：动 β_T / 动 ISO 表格 κ / 动参数表 σ_lnF / 动 F_k，
    必须各自按预期变红，且只有该动的项变红（局部性）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "kf"))

import wp_9645_01_inverse_audit as inv  # noqa: E402

PKG = os.path.join(ROOT, "docs", "kf", "wp-9645-01")
SNAP = os.path.join(PKG, "source", "report_9645.md")
JSON_PATH = os.path.join(PKG, "inverse_audit.json")
PNG_PATH = os.path.join(PKG, "inverse_audit.png")
SHA_PATH = os.path.join(PKG, "sha256.txt")


# ------------------------------------------------------------------ fixtures
@pytest.fixture(scope="module")
def markdown() -> str:
    with open(SNAP, encoding="utf-8", newline="") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def result(markdown: str) -> dict:
    return inv.audit(markdown, plot=False, write_json=False)


def failed_names(res: dict) -> list:
    return [c["quantity"] for c in res["checks"] if c["gated"] and not c["pass"]]


# ------------------------------------------------------- 1. 输入是注册资产本体
def test_snapshot_is_the_registered_asset() -> None:
    """复核读的字节必须就是 asset 登记时钉住的那份（否则复核对象被掉包）。"""
    with open(SHA_PATH, encoding="utf-8") as fh:
        pin = re.search(r"source_markdown: sha256:([0-9a-f]{64})", fh.read()).group(1)
    with open(SNAP, "rb") as fh:
        got = hashlib.sha256(fh.read()).hexdigest()
    assert got == pin


def test_no_solver_import() -> None:
    """复核必须与产出数字的求解器无关：不得 import 平台/第三方数值栈。"""
    src = open(os.path.join(ROOT, "scripts", "kf", "wp_9645_01_inverse_audit.py"),
               encoding="utf-8").read()
    # 只看模块级 import（函数内的 matplotlib 仅用于出图，不参与计算）
    top = "\n".join(line for line in src.split("\n")
                    if line[:1] in ("i", "f") and not line.startswith((" ", "\t")))
    for banned in ("tensorphysics", "numpy", "scipy", "matplotlib", "urllib"):
        assert banned not in top, banned
    assert "statistics" in top  # Φ / Φ⁻¹ 来自标准库


# ------------------------------------------------------------- 2. 门禁全绿
def test_every_gated_quantity_within_gate(result: dict) -> None:
    s = result["summary"]
    assert s["all_pass"], s["failed"]
    assert s["n_gated"] >= 50
    assert s["max_abs_rel_err"] < 0.03
    assert s["tol"] == 0.03


def test_key_solution_numbers(result: dict) -> None:
    """κ*/γ_f*/ψ*/F* 与报告表 1 的 6 位有效数字一致（<0.1 %）。"""
    d = result["derived"]
    for got, reported in ((d["kappa_star"], 1.431318),
                          (d["gamma_f_star"], 1.437056),
                          (d["psi_star"], 0.996007),
                          (d["F_design"], 33.7950)):
        assert abs(got - reported) <= 1e-3 * abs(reported), (got, reported)
    assert d["beta_at_kappa_star"] == pytest.approx(4.0, abs=1e-9)


def test_negative_control_is_detected(result: dict) -> None:
    """忽略 p–A 负相关使 γ_f* 膨胀 +28.90 %（报告正文），复核须复现该检出量。"""
    d = result["derived"]
    assert d["d_gamma_f_negative_control"] == pytest.approx(0.2890, abs=5e-4)
    assert d["d_kappa_negative_control"] == pytest.approx(0.2163, abs=5e-4)
    assert d["beta_naive_physical"] == pytest.approx(4.6597, abs=1e-3)


def test_non_conservative_rows_reproduced(result: dict) -> None:
    nc = [row["pair"] for row in result["iso_table"]
          if row["recomputed"]["non_conservative"]]
    assert len(nc) == 6
    assert all(pair.split(" x ")[0] in ("ice_action_abnormal", "ice_action_frequent")
               for pair in nc)


# ------------------------------------------------ 3. 数值路径与闭式互相独立
def test_numeric_quadrature_matches_closed_form(result: dict) -> None:
    """闭式 β=Δμ/σ 与「u 空间 Simpson 积分 + Φ⁻¹」两条路径须一致到 1e-6。"""
    nc = result["numeric_crosscheck"]
    assert nc["beta_at_kappa_star_numeric"] == pytest.approx(
        nc["beta_at_kappa_star_closed"], abs=1e-6)
    assert nc["beta_naive_numeric"] == pytest.approx(
        nc["beta_naive_closed"], abs=1e-6)
    assert nc["kappa_star_numeric"] == pytest.approx(
        nc["kappa_star_closed"], rel=1e-4)


def test_numeric_path_is_a_real_integration(markdown: str) -> None:
    """数值路径退化检查：把 β_T 目标换成 3.3，数值二分仍须解出报告的 κ(3.30)。"""
    parsed = inv.parse(markdown)
    P = parsed["params"]
    m = inv.Model(P)
    F_med = P["F_k"] * pow(2.718281828459045, -inv.Q99 * m.s_F)
    k = inv.kappa_star_numeric(F_med, P["F_k"], m, 3.3)
    assert k == pytest.approx(1.16279, rel=1e-3)


# ------------------------------------------------------- 4. 产物与可复现性
def test_committed_json_is_reproducible(result: dict) -> None:
    committed = json.load(open(JSON_PATH, encoding="utf-8"))
    assert committed == result            # 无墙钟字段，重跑须逐字段相同
    assert committed["summary"]["all_pass"] is True


def test_figure_is_real_matplotlib_png() -> None:
    raw = open(PNG_PATH, "rb").read()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert (w, h) == (1820, 728)          # 不是 1×1 的缺省占位


def test_claims_are_parsed_not_typed(markdown: str) -> None:
    """表 6 正文的两条相对偏差必须从快照正文解析（零手抄），不是脚本里的常数。"""
    parsed = inv.parse(markdown)
    assert parsed["d_gamma_claim"] == pytest.approx(0.2890)
    assert parsed["d_kappa_claim"] == pytest.approx(0.2163)
    assert parsed["beta_naive_claim"] == pytest.approx(4.6597)


# ------------------------------------------------------------- 5. 负控（证伪）
def test_control_beta_target_drift_breaks_solution(markdown: str) -> None:
    """β_T 4.0 → 4.3：κ*/γ_f* 与全部按表 β 必须变红。

    注：ψ*=κ/γ_f 是劈分比，对 β_T 只有弱依赖（报告表 7 里 3.3→4.3 只动 ±2.4 %），
    故本负控不要求 ψ* 变红——如实按量纲依赖登记，不凑期望。
    """
    tampered = markdown.replace("| 达到的 $\\beta$ | 4.000000000000 |",
                               "| 达到的 $\\beta$ | 4.300000000000 |")
    assert tampered != markdown
    res = inv.audit(tampered, plot=False, write_json=False)
    bad = failed_names(res)
    assert "kappa*" in bad and "gamma_f*" in bad, bad
    assert "psi*" not in bad   # 劈分比对 β_T 弱依赖，见 docstring


def test_control_small_beta_drift_is_below_the_3pct_gate(markdown: str) -> None:
    """如实登记门的灵敏度：β_T 漂 +0.1 只让 κ* 变 -2.9 %，仍在 3 % 门内。

    这类漂移**不能**靠 κ* 的相对门抓到，只能靠表 4 的绝对差门（Δκ, 1 个百分点）
    与 β_table 行抓到——所以两类门都必须留着。
    """
    tampered = markdown.replace("| 达到的 $\\beta$ | 4.000000000000 |",
                               "| 达到的 $\\beta$ | 3.900000000000 |")
    res = inv.audit(tampered, plot=False, write_json=False)
    bad = failed_names(res)
    kappa_rel = abs(res["derived"]["kappa_star"] / 1.431318 - 1.0)
    assert kappa_rel < 0.03          # κ* 自己看不出来
    assert any(b.startswith("Δκ [") for b in bad), bad   # 但表 4 的行看出来了


def test_control_iso_kappa_poison_is_local(markdown: str) -> None:
    tampered = markdown.replace("| (1.35, 1.10) | 1.4850 |", "| (1.35, 1.10) | 1.5500 |")
    assert tampered != markdown
    res = inv.audit(tampered, plot=False, write_json=False)
    bad = failed_names(res)
    assert len(bad) == 2, bad
    assert all("ice_action_extreme x steel_plate_yielding" in b for b in bad)


def test_control_sigma_lnF_poison_is_local(markdown: str) -> None:
    tampered = markdown.replace(
        "| $\\sigma_{\\ln F}$ | 0.2717 | 计入负相关 |",
        "| $\\sigma_{\\ln F}$ | 0.3000 | 计入负相关 |")
    assert tampered != markdown
    res = inv.audit(tampered, plot=False, write_json=False)
    assert failed_names(res) == ["sigma_lnF (correlated)"]


def test_control_characteristic_force_drift_is_local(markdown: str) -> None:
    """F_k 只进设计点强度：漂移后只该 F*/R* 两项红，κ* 与 β 不受影响。"""
    tampered = markdown.replace("| 特征冰力 $F_k$ | 23.517 MN |",
                               "| 特征冰力 $F_k$ | 25.000 MN |")
    assert tampered != markdown
    res = inv.audit(tampered, plot=False, write_json=False)
    assert failed_names(res) == ["F* (design point)", "R* (design point)"]
    assert res["derived"]["kappa_star"] == pytest.approx(
        1.4313180739218063, rel=1e-12)


def test_control_dropped_table_raises(markdown: str) -> None:
    """参数表被整体删掉时必须报错，而不是悄悄用默认值算出一份绿表。"""
    broken = "\n".join(line for line in markdown.split("\n")
                       if not line.startswith("| CoV("))
    with pytest.raises((KeyError, ValueError)):
        inv.audit(broken, plot=False, write_json=False)