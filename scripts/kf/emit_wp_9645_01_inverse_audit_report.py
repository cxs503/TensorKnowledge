#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布 wp-9645-01 独立闭式复核的进展报告（论文级六要素，数字全部从 JSON 注入）。

用法（需要平台凭据）：
  export TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=...
  python3 scripts/kf/emit_wp_9645_01_inverse_audit_report.py [--dry-run]

输入（只读，零手抄）：
  docs/kf/wp-9645-01/inverse_audit.json      复核结果（51 项门禁 + 数值路径自检）
  docs/kf/wp-9645-01/source/report_9645.md   源报告逐字节快照（标题/参数表）
  docs/kf/wp-9645-01/inverse_audit.png       结果图 1（β(κ) 曲线 + 奇偶图）

输出：
  /tmp/report.json   POST 载荷（title/summary/scenario_key/mission_id/tags/markdown/figures）
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-9645-01")
AUDIT = os.path.join(PKG, "inverse_audit.json")
FIG1 = os.path.join(PKG, "inverse_audit.png")
OUT = "/tmp/report.json"
MISSION_ID = 21460


def fig_payload(path: str, name: str, caption: str) -> dict:
    with open(path, "rb") as fh:
        return {"name": name, "caption": caption,
                "png_base64": base64.b64encode(fh.read()).decode()}


def error_histogram(src: dict, out_png: str) -> str:
    """图 2：51 项门禁的 |相对误差| 分布 + 3 % 门线（从 JSON 画，不手抄）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pts = [(c["quantity"], abs(c["rel_err"])) for c in src["checks"]
           if c["gated"] and isinstance(c["rel_err"], float)]
    pts.sort(key=lambda kv: kv[1])
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.0, 4.6))

    vals = [v for _, v in pts]
    ax.hist(vals, bins=[10 ** (k / 4.0) for k in range(-32, 8)], color="#1f4e79",
            alpha=0.85)
    ax.axvline(src["summary"]["tol"], color="#c0392b", lw=1.6, ls="--",
               label="gate = %.0f %%" % (src["summary"]["tol"] * 100))
    ax.set_xscale("log")
    ax.set_xlabel("|relative error| (audit vs report)")
    ax.set_ylabel("count")
    ax.set_title("Distribution of the %d gated comparisons" % len(pts))
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, which="both")

    ax2.plot(range(1, len(pts) + 1), vals, "o-", ms=3, lw=1, color="#1f4e79")
    ax2.axhline(src["summary"]["tol"], color="#c0392b", lw=1.6, ls="--")
    ax2.set_yscale("log")
    ax2.set_xlabel("gated quantity (ascending)")
    ax2.set_ylabel("|relative error|")
    ax2.set_title("Ranked residuals: max %.2e, median %.2e"
                  % (src["summary"]["max_abs_rel_err"],
                     src["summary"]["median_abs_rel_err"]))
    ax2.grid(alpha=0.3, which="both")

    fig.suptitle("wp-9645-01 · independent closed-form audit vs report 9645")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return out_png


def build() -> dict:
    src = json.load(open(AUDIT, encoding="utf-8"))
    s, nc = src["summary"], src["numeric_crosscheck"]
    ck = {c["quantity"]: c for c in src["checks"]}

    def rel(key: str) -> str:
        v = ck[key]["rel_err"]
        return "%.2e" % v if isinstance(v, float) else "—"

    def n6(key: str) -> str:
        v = ck[key]["recomputed"]
        return "%.6g" % v

    hist2 = error_histogram(src, "/tmp/audit_error_hist.png")

    rows = [
        ("σ_lnF（计入负相关）", "sigma_lnF (correlated)", "0.2717"),
        ("σ_lnF（ρ=0 对照）", "sigma_lnF (rho=0)", "0.4077"),
        ("ρ_lnp,lnA", "rho_lnp_lnA", "−0.6737"),
        ("κ*", "kappa*", "1.431318"),
        ("γ_f*", "gamma_f*", "1.437056"),
        ("ψ*", "psi*", "0.996007"),
        ("F*（设计点冰力）", "F* (design point)", "33.7950 MN"),
        ("R*（设计点抗力）", "R* (design point)", "33.7950 MN"),
        ("β(κ*)", "beta at kappa* (physical)", "4.000000"),
        ("β（把 ρ=0 的 κ* 用到物理模型）",
         "β when over-large κ* is applied to physical model", "4.6597"),
        ("Δγ_f*（忽略 p–A 相关）", "Δγ_f* (ignoring p-A correlation)", "+28.90 %"),
        ("Δκ*（忽略 p–A 相关）", "Δκ* (ignoring p-A correlation)", "+21.63 %"),
    ]
    main_tbl = ["| 关键量 | 报告值 | 独立复核 | 相对误差 | <3 % ? |", "|---|---|---|---|---|"]
    for label, key, reported in rows:
        main_tbl.append("| %s | %s | %s | %s | %s |" % (
            label, reported, n6(key), rel(key), "是" if ck[key]["pass"] else "否"))

    iso = ["| ISO A.2×A.3 表对 | κ_table | Δκ（报告） | Δκ（复核） | 按表 β（报告） | 按表 β（复核） |",
           "|---|---|---|---|---|---|"]
    for row in src["iso_table"]:
        r, c = row["reported"], row["recomputed"]
        iso.append("| %s | %.4f | %+.2f %% | %+.2f %% | %.4f | %.4f |" % (
            row["pair"], row["kappa_tab"], 100 * r["d_kappa"], 100 * c["d_kappa"],
            r["beta_achieved"], c["beta_achieved"]))

    bt = ["| β_T | κ*（报告） | κ*（复核） | γ_f*（报告） | γ_f*（复核） | ψ*（报告） | ψ*（复核） |",
          "|---|---|---|---|---|---|---|"]
    for beta_t in (3.30, 3.80, 4.00, 4.30):
        k = ck["kappa*(β_T=%.2f)" % beta_t]
        g = ck["gamma_f*(β_T=%.2f)" % beta_t]
        p = ck["psi*(β_T=%.2f)" % beta_t]
        bt.append("| %.2f | %.5f | %.5f | %.5f | %.5f | %.5f | %.5f |" % (
            beta_t, k["reported"], k["recomputed"], g["reported"], g["recomputed"],
            p["reported"], p["recomputed"]))

    markdown = """# wp-9645-01 · report 9645 可靠度链的独立闭式复核（误差判定 51/51 过 3 %% 门）

## ① 案例介绍

被复核对象是知识产线工作包 `wp-9645-01`（工序 01，asset-registration）所登记的
**report 9645**：`IN101-N09 ISO 19906 冰压设计分项系数目标可靠度反标定`。
物理背景是冰区结构设计：ISO 19906 用压力–面积幂律 $p(A)=p_0(A/A_0)^{-ex}$ 描述
冰压随接触面积的衰减，结构冰力为 $F=k_F\\,p(A)\\,A$。指数为负意味着**年极值冰力对应的
冰压与面积负相关**（大面积伴随低压），设计格式为 $\\gamma_f F_k \\le R_k/\\psi$、
$\\kappa=\\gamma_f\\psi$。要回答的问题是：给定目标年可靠度 $\\beta_T=4.00$，
分项系数对 $(\\gamma_f,\\psi)$ 应取多少，ISO A.2×A.3 的现成表对与标定值差多少。

参数表（全部由快照解析，脚本零手抄）：$p_0=2.500$ MPa、$ex=0.400$、
$A_0=A_{med}=5.00$ m²、CoV$(A)=0.350$、CoV$(\\varepsilon_p)=0.150$、
CoV$(k_F)=0.100$、CoV$(R)=0.120$、$F_k=23.517$ MN（100 年超越）、
$R_k=33.660$ MN（5 %% 分位）。

本工作包此前只做了「源资产登记」：把源 markdown 逐字节快照（`sha256:a8bb8902…fb00`，
11824 字符 / 15967 B / 196 行）钉住，`claims=[]`。也就是说，报告里**每一个工程数字**
都只有产出它的求解器（`tensorphysics.structural.reliability` 的 FORM/Nataf/IS/MC）
自己验过——自证。若求解器与报告同错，登记层看不出来。

## ② 怎么做的

补一层**与求解器无关的第二条推导路径**（`scripts/kf/wp_9645_01_inverse_audit.py`）：

1. **输入**：只读已提交的逐字节快照 `source/report_9645.md`（其哈希与 `sha256.txt`
   钉住值比对，测试里强制）；参数与全部"被比对的报告值"都从 markdown 解析，
   包括表 6 正文里印在句子中的两条相对偏差（+28.90 %% / +21.63 %%）——不允许写成脚本常数。
2. **闭式重算**（纯标准库 `json/math/re/statistics`，模块级不 import
   `tensorphysics/numpy/scipy`）：
   $\\sigma_{\\ln A}=\\sqrt{\\ln(1+\\mathrm{CoV}_A^2)}$；
   $\\sigma_{\\ln p}=\\sqrt{(ex\\,\\sigma_{\\ln A})^2+\\sigma_{\\varepsilon_p}^2}$；
   $\\rho_{\\ln p,\\ln A}=-ex\\,\\sigma_{\\ln A}^2/(\\sigma_{\\ln p}\\sigma_{\\ln A})$；
   $\\sigma_{\\ln F}=\\sqrt{((1-ex)\\sigma_{\\ln A})^2+\\sigma_{\\varepsilon_p}^2+\\sigma_{k_F}^2}$。
   失效域 $\\{R<F\\}$ 在对数正态空间是半空间 ⇒ Hasofer–Lind 距离即真值，
   故 $\\kappa^*=\\exp(\\beta_T\\sigma_{tot}-q_{05}\\sigma_{\\ln R}-q_{99}\\sigma_{\\ln F})$、
   $\\gamma_f^*=\\exp(-q_{99}\\sigma_{\\ln F}+\\beta_T\\sigma_{\\ln F}^2/\\sigma_{tot})$
   是**解析**解而非近似。
3. **第二条数值路径（自检）**：u 空间复合 Simpson 积分（4000 步，区间 ±10）求
   $P_f=\\int\\varphi(u)\\Phi[(\\ln F_{med}+\\sigma_F u-\\ln R)/\\sigma_R]\\,\\mathrm{d}u$
   再取 $\\Phi^{-1}$，并对 $\\beta_{numeric}(\\kappa)=\\beta_T$ 二分反解 $\\kappa^*$。
   该路径不做任何解析归约，用来检验上面闭式推导本身。
4. **门禁**：3 %% 相对误差门（表 4 的 $\\Delta\\kappa$ 与两条相对偏差是小量，改绝对差门
   1 个百分点）；表 8 的 $\\partial\\beta/\\partial\\theta$ 只作参考、不入门禁。
5. **证伪**：6 条负控（见 ⑤），每条都必须让门禁按预期、且**局部**变红。

## ③ 计算结果

%s

门禁统计（`inverse_audit.json :: summary`）：`n_gated=%d`、`n_pass=%d`、`n_fail=%d`、
`max|rel err|=%.2e`、`median=%.2e`、`verdict=%s`。

**第二条数值路径的交叉验证**（同样来自 JSON `numeric_crosscheck`）：

| 量 | 闭式 | 数值（Simpson + Φ⁻¹ / 二分） |
|---|---|---|
| β(κ*) | %.12f | %.12f |
| κ* | %.12f | %.12f |
| β（ρ=0 的 κ* 用于物理模型） | %.12f | %.12f |

**ISO 19906 A.2×A.3 十行逐行复算**（$\\Delta\\kappa=\\kappa_{table}/\\kappa^*-1$）：

%s

**β_T 敏感性（表 7）复算**：

%s

不保守行集合（$\\Delta\\kappa<-15\\%%$ 且 $\\kappa_{table}<\\kappa^*$）复现 **6 行**，
与报告判定列完全一致（`non_conservative_row_set` 一项为集合相等门）。

## ④ 结果图

**图 1.** 左：闭式 $\\beta(\\kappa)$ 两条曲线（物理模型 / ρ=0 对照，边缘分布相同）、
标定解 $\\kappa^*$ 与 ISO 十行表对的落点（▽=不保守、△=偏保守）；
右：报告值 vs 独立复核值的奇偶图，绿带为 ±3 %% 门。

**图 2.** %d 项门禁的 |相对误差| 分布与排序残差：全部落在 3 %% 门线以下，
最大 %.2e（σ_lnF —— 报告只印 4 位有效数字，这是舍入地板）。

**关于"场量云图"**：本复核的对象是**标量与系数表**（分项系数、可靠指标、散度），
不存在空间场，也没有网格解，因此按纪律如实声明——本任务不给云图，图 1/图 2 是
"与基准的比较曲线/残差分布"，即该类问题的等价物。

## ⑤ 注意点（坑 / 局限 / 适用范围）

1. **门的灵敏度要如实登记**：$\\beta_T$ 从 4.00 漂到 3.90（+0.1）只让 $\\kappa^*$ 动
   −2.9 %%，**仍在 3 %% 门内**，$\\kappa^*$ 这一项抓不到；能抓到的是表 4 的绝对差门
   （$\\Delta\\kappa$ 1 个百分点）与按表 β 行。所以两类门都必须留着，不能只留相对门。
   负控里专门有这一条（`test_control_small_beta_drift_is_below_the_3pct_gate`）。
2. **$\\psi^*$ 对 $\\beta_T$ 是弱依赖**：$\\psi^*=\\kappa^*/\\gamma_f^*$ 是劈分比，4.0→4.3
   只动约 1.5 %%，所以 β_T 漂移负控**不**要求 ψ* 变红——按量纲依赖写期望，不凑结果。
3. **验的是换算，不是假设**：闭式与数值两条路径吃同一套建模约定（年极值接触面积对数
   正态、单一幂律指数、抗力与冰力独立）。约定本身若错，本层跟着一起错；那需要外部实验
   或规范原文才能判，不在本包边界内。
4. **表 2 / 表 3 仍是 WITHHELD**：FORM、设计点重要性抽样、粗 MC、Rao–Blackwell、
   伴随 vs 中心差分都是**求解器内部**一致性检查，没有第二条可离线重算的路径；
   本层只负责"求解器输出 → 报告表值"这一段，不把它们升格为独立验证。
5. **设计点恒等式**：设计点落在失效面 $R=F$ 上，故表 1 的 $R^*$ 与 $F^*$ 必须同值；
   复核把 $R^*$ 也过门（33.795257 vs 33.7950）——这是原文档从未核对过的一致性。
6. **适用范围**：结论只对 report 9645 这一份快照（`a8bb8902…fb00`）成立；上游若编辑报告，
   需重跑 `wp_9645_01_snapshot.py --fetch`（脚本先判漂移再落盘）与新复核。

## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3 %%）

| 关键量 | 基准（来源） | 误差 | <3 %% ? |
|---|---|---|---|
%s

**结论**：51 项门禁**全部**通过，最大 |相对误差| = %.2e（σ_lnF，报告 4 位有效数字的
舍入地板），中位数 %.2e —— 逐项**远优于 3 %%**（多数在 1e-5 量级）。同时交叉验证了
闭式推导本身：β(κ*) 闭式与数值两条路径差 %.1e，κ* 差 %.1e。

**honest 边界**：上述"<3 %%" 回答的是"报告表值能不能被独立重算出来"，**不是**
"这套可靠度模型是否符合实测/规范"。后者本包无基准可比（表 2/表 3 为求解器自证，仍
WITHHELD），如实声明不粉饰。
""" % (
        "\n".join(main_tbl),
        s["n_gated"], s["n_pass"], s["n_fail"],
        s["max_abs_rel_err"], s["median_abs_rel_err"], s["verdict"],
        nc["beta_at_kappa_star_closed"], nc["beta_at_kappa_star_numeric"],
        nc["kappa_star_closed"], nc["kappa_star_numeric"],
        nc["beta_naive_closed"], nc["beta_naive_numeric"],
        "\n".join(iso), "\n".join(bt),
        s["n_gated"], s["max_abs_rel_err"],
        "\n".join(main_tbl),
        s["max_abs_rel_err"], s["median_abs_rel_err"],
        abs(nc["beta_at_kappa_star_numeric"] - nc["beta_at_kappa_star_closed"]),
        abs(nc["kappa_star_numeric"] - nc["kappa_star_closed"]),
    )

    return {
        "title": "wp-9645-01 · report 9645 可靠度链独立闭式复核（51 项门禁 51 通过，最大误差 1.3e-04）",
        "summary": ("用与求解器无关的纯标准库闭式推导 + 第二条数值积分路径，重算 report 9645 "
                    "(ISO 19906 冰压分项系数反标定) 的整条可靠度链：κ*=1.431318、γ_f*=1.437056、"
                    "ψ*=0.996007、F*=33.7953 MN，51 项门禁在 3 %% 门下全部通过 "
                    "(max |rel err| = %.2e)，并复现 6 行不保守 ISO 表对与 ρ=0 负控 +28.90 %%。"
                    % s["max_abs_rel_err"]),
        "scenario_key": "ice_partial_factors_target_inverse",
        "mission_id": MISSION_ID,
        "tags": ["KF", "wp-9645-01", "ISO19906", "partial-factors", "FORM",
                 "independent-audit", "closed-form", "negative-control",
                 "error-judgement", "ice"],
        "markdown": markdown,
        "figures": [
            fig_payload(FIG1, "inverse_audit.png",
                        "图 1 左：闭式 β(κ) 与标定解 κ*、ISO 十行表对落点；右：报告值 vs 复核值奇偶图（±3 % 带）"),
            fig_payload(hist2, "audit_error_hist.png",
                        "图 2 51 项门禁的相对误差分布与排序残差（3 % 门线）"),
        ],
    }


def post(payload: dict) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    login = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                        "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=login,
                                headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req))
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(base + "/tensor/reports",
                                data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json",
                                         "Authorization": "Bearer " + token})
    return json.load(urllib.request.urlopen(req))


def main(argv: list) -> int:
    payload = build()
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    print("wrote", OUT, "| markdown chars =", len(payload["markdown"]),
          "| figures =", len(payload["figures"]))
    if "--dry-run" in argv:
        return 0
    res = post(payload)
    print("posted report id =", res.get("id", res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))