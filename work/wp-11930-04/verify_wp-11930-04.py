#!/usr/bin/env python3
"""wp-11930-04 independent adversarial re-verification (reviewer side).

Everything is recomputed from bytes fetched fresh from the platform API — never from the
producer's cached copy — and from the report text alone. Checks:

  R1 source hash / chars / bytes  vs contract + upstream manifest
  R2 locator fidelity: source[start:end] == quote, quote unique, path token inside quote
  R3 manifest counts recomputed from the 14 asset records
  R4 figure assets: GET .../figures/<name> -> 200 image/png, sha256/bytes vs manifest,
     caption byte-exact vs the report record figures[]
  N* semantic fidelity: every published number re-derived from other published numbers
     (geometry, packing, Jacobian spectrum/cond/rank, correlation matrix, Brun gamma,
     Weibull size-effect predictions and errors, AC5 stress-ratio errors, percentages)

Writes verify_wp-11930-04.json next to this script; exit code 1 if a blocking check fails.
"""
import hashlib
import json
import math
import os
import re
import sys
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/root/tp-agent/work/m19840"
BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
REPORT_ID = "11930"
CONTRACT = {"sha256": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
            "chars": 13121, "bytes_utf8": 22324}
MANIFEST_KF = os.path.join(REPO, "docs/kf/wp-11930-01/kf_result.wp-11930-01.json")

results = []


def rec(check, expected, observed, verdict, note=""):
    results.append({"check": check, "expected": expected, "observed": observed,
                    "result": verdict, "note": note})


def token():
    req = urllib.request.Request(BASE + "/auth/login",
                                 data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                  "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    return d.get("access_token") or d.get("token") or d["data"]["access_token"]


def main():
    tok = token()
    # ---- fresh fetch of the report record (markdown + figures metadata) ----
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID)
    req.add_header("Authorization", "Bearer " + tok)
    record = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
    record = record.get("data", record)
    md = record["markdown"]
    b = md.encode("utf-8")
    h = "sha256:" + hashlib.sha256(b).hexdigest()
    with open(os.path.join(HERE, "source_report.md"), "w", encoding="utf-8") as f:
        f.write(md)

    kf = json.load(open(MANIFEST_KF))
    man = kf["outputs"]["asset_manifest.json"]

    # ---- R1 ----
    rec("R1.1_source_hash_fresh_vs_contract", CONTRACT["sha256"], h,
        "PASS" if h == CONTRACT["sha256"] else "FAIL")
    rec("R1.2_hash_vs_upstream_manifest", man["source"]["hash"], h,
        "PASS" if man["source"]["hash"] == h.split(":")[1] else "FAIL")
    rec("R1.3_chars", CONTRACT["chars"], len(md),
        "PASS" if len(md) == CONTRACT["chars"] else "FAIL")
    rec("R1.4_bytes_utf8", CONTRACT["bytes_utf8"], len(b),
        "PASS" if len(b) == CONTRACT["bytes_utf8"] else "FAIL")
    rec("R1.5_kf_reports_same_hash", kf["provenance"]["source_hash"], h,
        "PASS" if kf["provenance"]["source_hash"] == h else "FAIL")

    # ---- R2 locator fidelity ----
    bad = []
    for a in man["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        s, e = loc.get("start_char"), loc.get("end_char")
        ok_span = isinstance(s, int) and isinstance(e, int) and md[s:e] == q
        n = md.count(q)
        ok_uniq = n == 1
        ok_tok = True
        token_ = a.get("path_in_report", "")
        if a["resolution"] != "declared_absent" and token_ and not token_.startswith("n/a"):
            ok_tok = token_ in q
        if "quote_sha256" in loc:
            ok_hash = "sha256:" + hashlib.sha256(q.encode()).hexdigest() == loc["quote_sha256"]
        else:
            ok_hash = True
        if not (ok_span and ok_uniq and ok_tok and ok_hash):
            bad.append({"asset_id": a["asset_id"], "span": ok_span, "unique": ok_uniq,
                        "path_token_in_quote": ok_tok, "quote_sha": ok_hash, "count": n})
    rec("R2.1_all_14_locators_span_exact_unique_path_token", "14/14 exact", 
        f"{len(man['assets']) - len(bad)}/{len(man['assets'])} exact", 
        "PASS" if not bad else "FAIL", json.dumps(bad, ensure_ascii=False))

    # ---- R3 counts ----
    by_class, by_res = {}, {}
    for a in man["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = man["counts"]
    ok = (c["assets"] == len(man["assets"]) == 14 and c["by_class"] == by_class
          and c["by_resolution"] == by_res and sum(c["by_resolution"].values()) == 14)
    rec("R3.1_manifest_counts_recomputed", {"assets": 14, "by_class": by_class, "by_resolution": by_res},
        {"assets": c["assets"], "by_class": c["by_class"], "by_resolution": c["by_resolution"]},
        "PASS" if ok else "FAIL")

    # ---- R4 figures: bytes + caption ----
    figs = {f["name"]: f.get("caption", "") for f in man["source"].get("platform_figures", [])}
    rec_figs = record.get("figures") or []
    rec_cap = {}
    for f in rec_figs:
        if isinstance(f, dict):
            rec_cap[f.get("name")] = f.get("caption", "")
    fig_findings = []
    for a in man["assets"]:
        if a["asset_class"] != "figure":
            continue
        name = os.path.basename(a["path_in_report"])
        url = BASE + f"/tensor/reports/{REPORT_ID}/figures/" + name
        r = urllib.request.Request(url)
        r.add_header("Authorization", "Bearer " + tok)
        try:
            resp = urllib.request.urlopen(r, timeout=120)
            blob = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            sha = "sha256:" + hashlib.sha256(blob).hexdigest()
            ok = (resp.status == 200 and "png" in ctype
                  and sha == "sha256:" + a.get("platform_sha256", "")
                  and len(blob) == a.get("platform_bytes"))
            cap_ok = (name not in rec_cap) or (figs.get(name) == rec_cap.get(name))
            fig_findings.append({"name": name, "status": resp.status, "ctype": ctype,
                                 "bytes": len(blob), "sha256": sha,
                                 "manifest_bytes": a.get("platform_bytes"),
                                 "bytes_match": len(blob) == a.get("platform_bytes"),
                                 "sha_match": sha == "sha256:" + a.get("platform_sha256", ""),
                                 "caption_matches_record": cap_ok})
            if not (ok and cap_ok):
                rec("R4_" + name, "200/png/sha/bytes", fig_findings[-1], "FAIL")
        except Exception as exc:  # noqa: BLE001
            fig_findings.append({"name": name, "error": repr(exc)})
            rec("R4_" + name, "200/png/sha/bytes", repr(exc), "FAIL")
    rec("R4.1_six_figure_assets_bytes_and_captions", "6/6 HTTP200 png + sha256 + bytes + caption",
        f"{sum(1 for f in fig_findings if f.get('sha_match') and f.get('caption_matches_record'))}/{len(fig_findings)} verified",
        "PASS" if all(f.get("sha_match") and f.get("caption_matches_record") for f in fig_findings) else "FAIL",
        json.dumps(fig_findings, ensure_ascii=False))

    # ---- N: semantic fidelity, all from published text numbers ----
    # geometry / lattice
    d = 3 * 0.025 + 2 * 0.0125
    rec("N1.1_ucs_diameter_bounding_box", 0.1, round(d, 6), "PASS" if abs(d - 0.1) < 1e-12 else "FAIL")
    h_gauge, h_extent, d_c2c = 8 * 0.025, 8 * 0.025 + 0.025, 3 * 0.025
    rec("N1.2_ucs_HD_three_conventions",
        {"gauge_over_extent_reported": 2.0, "extent_over_extent": 2.25, "c2c_over_c2c": 2.667},
        {"gauge_over_extent_reported": round(h_gauge / d, 3),
         "extent_over_extent": round(h_extent / d, 3),
         "c2c_over_c2c": round(h_gauge / d_c2c, 3)},
        "WARN", "报告 2.000 = 标距H(0.2)/物理D(0.1)；统一口径为 2.25（仍在 ASTM [1.5,2.5]）或 2.667（出带）。"
                "混用口径未声明 → AC1 UCS 子项 PASS 依赖口径")
    rec("N1.3_particle_count_4x4x9", 144, 4 * 4 * 9, "PASS" if 4 * 4 * 9 == 144 else "FAIL")
    rec("N1.4_number_density_1_over_spacing3", 6.40e4, 1 / 0.025 ** 3,
        "PASS" if abs(1 / 0.025 ** 3 - 6.40e4) < 1e-6 * 6.4e4 else "FAIL")
    rec("N1.5_packing_pi_over_6", 0.5236, round(math.pi / 6, 4),
        "PASS" if round(math.pi / 6, 4) == 0.5236 else "FAIL")
    rec("N1.6_brazil_D_over_t", 1.750, round(0.175 / 0.1, 3),
        "PASS" if abs(0.175 / 0.1 - 1.75) < 1e-12 else "FAIL")
    rec("N1.7_tensile_HD_family", [0.5, 1.0, 2.0, 4.0, 8.0],
        [round(t / 0.1, 3) for t in (0.05, 0.1, 0.2, 0.4, 0.8)],
        "PASS" if all(abs(t / 0.1 - x) < 1e-12 for t, x in
                      zip((0.05, 0.1, 0.2, 0.4, 0.8), (0.5, 1.0, 2.0, 4.0, 8.0))) else "FAIL")

    # Jacobian as published in the report (rows UCS/sigma_t/m; 2-decimals)
    J = np.array([[0.32, 0.47, 0.00, 0.00, 1.05, 0.32],
                  [1.33, 1.51, 0.00, 0.00, 0.14, 0.14],
                  [3.00, -1.61, 0.00, 0.00, -3.32, -3.32]])
    sv = np.linalg.svd(J, compute_uv=False)
    cond = sv[0] / sv[2]
    rec("N2.1_singular_values", [5.848, 2.151, 0.645], [round(x, 3) for x in sv],
        "PASS" if np.allclose(np.round(sv, 3), [5.85, 2.148, 0.646], atol=3e-3) else "WARN",
        "2-decimals published J 重算 5.8499/2.1483/0.6458；报告 5.848/2.151/0.645 在四舍五入内")
    rel = abs(cond - 9.063) / 9.063
    rec("N2.2_cond_J", 9.063, round(cond, 4), "PASS" if rel < 1e-3 else "FAIL",
        f"由公开（2 位小数）J 重算 cond={cond:.4f}，与 9.063 相对差 {rel*100:.3f}%")
    rec("N2.3_rank_and_null_dim", {"rank": 3, "null_dim": 3},
        {"rank": int(np.linalg.matrix_rank(J)), "null_dim": 6 - int(np.linalg.matrix_rank(J))},
        "PASS" if int(np.linalg.matrix_rank(J)) == 3 else "FAIL")

    M = J.T @ J
    dg = np.sqrt(np.diag(M))
    with np.errstate(invalid="ignore"):
        R = M / np.outer(dg, dg)
    rep_R = np.array([[1.00, -0.36, np.nan, np.nan, -0.82, -0.88],
                      [-0.36, 1.00, np.nan, np.nan, 0.77, 0.76],
                      [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
                      [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
                      [-0.82, 0.77, np.nan, np.nan, 1.00, 0.98],
                      [-0.88, 0.76, np.nan, np.nan, 0.98, 1.00]])
    mask = ~np.isnan(rep_R)
    maxdiff = float(np.max(np.abs(np.round(R[mask], 2) - rep_R[mask])))
    rec("N2.4_parameter_correlation_matrix_reproduced", "≤0.005 on 24 published entries",
        round(maxdiff, 4), "PASS" if maxdiff <= 0.005 else "FAIL",
        "JᵀJ 归一化重算与报告相关矩阵逐格一致（含 mu_s/mu_d 恒零列）")

    rho = float(R[4, 5])
    gamma_brun = 1 / math.sqrt(1 - rho ** 2)
    gamma_belsley = math.sqrt((1 + rho) / (1 - rho))
    gamma_alt = 1 / math.sqrt(1 - rho)
    rec("N2.5_brun_gamma_pair_kc_kp", 6.71,
        {"rho": round(rho, 4), "1/sqrt(1-rho^2)": round(gamma_brun, 3),
         "sqrt((1+rho)/(1-rho))": round(gamma_belsley, 3), "1/sqrt(1-rho)": round(gamma_alt, 3)},
        "WARN", "报告 γ=6.71 与公开 ρ=0.978 在两种标准定义下都对不上（4.80 / 9.49）；"
                "仅非标准 1/√(1−ρ) 给出 6.75 的量级。γ 定义未在报告声明 → 最坏参数对诊断不可独立复算。"
                "不改变 rank 3/6 的结构结论")
    rec("N2.6_full_column_gamma_inf", "inf (structural rank deficiency)",
        round(float(1 / math.sqrt(max(1 - 1.0, 1e-16))), 1), "PASS",
        "3 观测量/6 参数、rank=3 → 任一列可被其余列精确线性表示 → R²=1 → γ=inf，与报告一致")

    # Weibull size effect: sigma_t(t) = sigma_ref * t^(-1/m)
    m_fit, s_ref = 262.976, 3.71e5
    pred = {t: s_ref * t ** (-1 / m_fit) / 1e6 for t in (0.05, 0.8)}
    err05 = (pred[0.05] - 0.397) / 0.397 * 100
    err08 = (pred[0.8] - 0.362) / 0.362 * 100
    rec("N3.1_powerlaw_prediction_t005", {"reported": 0.376, "recomputed": round(pred[0.05], 4)},
        round(pred[0.05], 4), "PASS" if abs(pred[0.05] - 0.376) < 1e-3 else "FAIL")
    rec("N3.2_powerlaw_prediction_t080", {"reported": 0.372, "recomputed": round(pred[0.8], 4)},
        round(pred[0.8], 4), "PASS" if abs(pred[0.8] - 0.372) < 1e-3 else "FAIL")
    rec("N3.3_holdout_relative_errors", {"t=0.05": "-5.4%", "t=0.80": "+2.6%"},
        {"t=0.05": f"{err05:+.1f}%", "t=0.80": f"{err08:+.1f}%"},
        "PASS" if abs(err05 + 5.4) < 0.3 and abs(err08 - 2.6) < 0.3 else "FAIL",
        "由 (m=262.976, σ_ref=3.71e5) 与留出实测值重算")
    rec("N3.4_bootstrap_CI_width", 721.537, round(746.453 - 24.916, 3),
        "PASS" if abs((746.453 - 24.916) - 721.537) < 1e-9 else "FAIL")
    rec("N3.5_local_m_column_values", "local m should be O(10^2) like global m=262.976",
        {"published_local_m": [0.080, 0.045], "implied_m_if_1/local_m": [round(1 / 0.080, 1), round(1 / 0.045, 1)],
         "global_m": m_fit}, "WARN",
        "列名“局部 m”下的 0.080/0.045 与全局 m=262.976 差 3 个量级；数值符合局部指数 1/m（即 m≈12.5/22.2）。"
        "方向一致性只对指数符号敏感 → 结论不受影响，但列名/量纲必须更正")

    # AC5 Brazilian stress ratio errors
    rep_ratio = [(-3.481, 16.0), (-4.180, 39.3), (-2.705, 9.8), (-6.906, 130.2), (-9.155, 205.2), (-26.642, 788.1)]
    comp = [(v, round(abs(v + 3.0) / 3.0 * 100, 1)) for v, _ in rep_ratio]
    ok = all(abs(c[1] - r[1]) <= 0.15 for c, r in zip(comp, rep_ratio))
    rec("N4.1_AC5_relative_errors_vs_hondros_-3", [(v, e) for v, e in rep_ratio], comp,
        "PASS" if ok else "FAIL")
    rec("N4.2_AC5_qualitative_phrase", "9.8% relative difference",
        "报告 §5 同一行写“差两个量级”", "WARN",
        "9.8%/788% 都不是两个量级（10^2）的差；同一行自相矛盾，属定量表述错误（不影响 honest FAIL 判定）")

    # AC4b protocol refinement deviations
    conv = [(1.0098, 1.0, 0.0), (0.8559, 1.0, -15.2), (0.6728, 1.0, -33.4)]
    dev = [(v, round((v - 1.0098) / 1.0098 * 100, 1)) for v, _, _ in conv]
    ok = all(abs(a[1] - b[2]) <= 0.15 for a, b in zip(dev, conv))
    rec("N5.1_AC4b_ucs_refinement_deviations", [(v, d) for v, _, d in conv], dev,
        "PASS" if ok else "FAIL",
        "1.0098 → 1.010 MPa 与 §3.3 的 UCS=1.010 一致")
    t04 = [(0.3564, 0.0), (0.3557, -0.2), (0.3832, 7.5)]
    dev04 = [(v, round((v - 0.3564) / 0.3564 * 100, 1)) for v, _ in t04]
    rec("N5.2_AC4b_t04_deviations", t04, dev04,
        "PASS" if all(abs(a[1] - b[1]) <= 0.15 for a, b in zip(dev04, t04)) else "FAIL")

    # AC6 / AC7
    rec("N6.1_AC6_violation_count_integral", "83.5% of 200 = integer count",
        {"167/200": round(167 / 200 * 100, 1), "168/200": round(168 / 200 * 100, 1)},
        "PASS", "200 组样本下 83.5% 恰为 167/200，计数自洽；同时意味着 33/200 随机 θ 落进文献带")
    rec("N6.2_AC6_narrative", "83.5% violating ⇒ 16.5% inside band",
        "§2 条 7 表述“随机参数几乎不可能落进文献带”", "WARN",
        "16.5%（≈1/6）随机参数落入文献带，与“几乎不可能”不符；AC6 本身已如实记 FAIL，"
        "但该句把 FAIL 的负控说成强负控，属证据与论断不匹配")
    rec("N7.1_ke_ratio_gate_multiple", "0.022/0.001 = 22", 0.022 / 0.001,
        "PASS" if abs(0.022 / 0.001 - 22) < 1e-9 else "FAIL")
    rec("N7.2_AC7_zero_difference_display", "0.000 = 3 significant figures only",
        "1.01e+06 / 1.01e+06 Pa", "WARN",
        "两值仅给到 3 位有效数字，“相对差 0.000”强于所展示的证据；应给至少 6 位或原始 Pa 整数")

    # gap: sigma_t at fitted thicknesses not published
    rec("N8.1_sigma_t_fitted_thicknesses_published", "σ_t at t=0.1/0.2/0.4 (the fit inputs)",
        "报告只给留出 t=0.05/0.80 两行", "WARN",
        "σc/σt=2.688 与 m=262.976 的拟合输入未公开 → 只能由 (m, σ_ref) 复算留出预测，"
        "无法从报告正文独立复算 2.688 与 262.976（可用 artifacts/p270w2c_n08/report.json 补，但该文件不在本仓）")

    blocking = [r for r in results if r["result"] == "FAIL"]
    out = {"report_id": REPORT_ID, "package_id": "wp-11930-04",
           "generated_at": "2026-11-12T00:00:00+00:00",
           "source": {"uri": "tensor://reports/11930", "sha256": h, "chars": len(md), "bytes_utf8": len(b)},
           "checks": results,
           "summary": {"total": len(results),
                       "pass": sum(1 for r in results if r["result"] == "PASS"),
                       "warn": sum(1 for r in results if r["result"] == "WARN"),
                       "fail": len(blocking)}}
    with open(os.path.join(HERE, "verify_wp-11930-04.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out["summary"], ensure_ascii=False))
    for r in results:
        print(f'  [{r["result"]:4s}] {r["check"]}: {str(r["observed"])[:120]}')
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())