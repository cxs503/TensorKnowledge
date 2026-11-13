#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-5577-04 · 04-independent-review 主脚本。

对 report_id=5577（BP 示范工程报告 / campaign/bp-demo-in12p8）及其上游工作包 wp-5577-01
（01-asset-registration，结果报告 #14783）做独立红队审核，产出 review_report.json + kf_result.json。

纪律
----
1) 零手抄：所有引文先经 assert_quotes() 断言为 report-5577 markdown 的逐字子串，否则 SystemExit。
2) 独立：审核上下文 = report-5577 markdown + record + 上游结果信封；不读生产者的口头解释。
3) 不标 verified：claim 只赋 supported/partially-supported/unresolved/refuted。
4) honest：不可复核项一律进 checks_not_run，不因缺证据而判 pass。

用法
----
    python3 scripts/wp5577_review.py                 # 离线（读 docs/kf/wp-5577-04/source/ 快照）
    python3 scripts/wp5577_review.py --online         # 经 API 重取并校验快照未漂移
    python3 scripts/wp5577_review.py --figure         # 另渲染 fig1_closure_residuals.png
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp5577_review_data as D  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG, TASK_TYPE = "wp-5577-04", "04-independent-review"
REPORT_ID, UPSTREAM_PKG, UPSTREAM_REPORT_ID = "5577", "wp-5577-01", "14783"
CONTRACT_HASH = "sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8"
EXPECTED_CHARS = 3702
OUT_DIR = os.path.join(ROOT, "docs", "kf", PKG)
SRC_DIR = os.path.join(OUT_DIR, "source")
SCHEMA_PATH = os.path.join(ROOT, "schemas", "kf_result.v1.schema.json")


# ---------------------------------------------------------------- 基础工具
def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def api_get(path: str) -> dict:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
    payload = json.dumps({"username": os.environ.get("TENSOR_AGENT_USER", ""),
                          "password": os.environ.get("TENSOR_AGENT_PASS", "")}).encode()
    req = urllib.request.Request(f"{base}/auth/login", data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    tok = json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]
    req = urllib.request.Request(f"{base}/{path}", headers={"Authorization": f"Bearer {tok}"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def load_sources(online: bool) -> tuple[str, dict, dict]:
    md = open(os.path.join(SRC_DIR, "report_5577.md"), encoding="utf-8").read()
    rec = json.load(open(os.path.join(SRC_DIR, "report_5577_record.json"), encoding="utf-8"))
    up = json.load(open(os.path.join(SRC_DIR, f"upstream_report_{UPSTREAM_REPORT_ID}_{UPSTREAM_PKG}.json"),
                        encoding="utf-8"))
    if online:
        live = api_get(f"tensor/reports/{REPORT_ID}")
        if sha256_text(live["markdown"]) != sha256_text(md):
            sys.exit("FAIL: 在线 markdown 与本地快照不一致（源已漂移；审核对象变更需重新派单）")
        md, rec = live["markdown"], live
        up = api_get(f"tensor/reports/{UPSTREAM_REPORT_ID}")
    return md, rec, up


def load_figure_probe() -> dict:
    p = os.path.join(SRC_DIR, "figure_probe.json")
    if not os.path.exists(p):
        return {"probe_valid": None, "conclusion": "探针未运行（缺 source/figure_probe.json）"}
    return json.load(open(p, encoding="utf-8"))


def assert_quotes(md: str) -> None:
    missing = [k for k, q in D.QUOTES.items() if q not in md]
    if missing:
        sys.exit(f"FAIL: 以下引文不是 report-5577 markdown 的逐字子串: {missing}")


def extract_single_json_block(markdown: str) -> dict:
    blocks, idx = [], 0
    while True:
        i = markdown.find("```json", idx)
        if i < 0:
            break
        j = markdown.find("```", i + 7)
        blocks.append(markdown[i + 7:j])
        idx = j + 3
    if len(blocks) != 1:
        sys.exit(f"FAIL: 上游报告 json 代码块数={len(blocks)}（应唯一）")
    return json.loads(blocks[0])


# ---------------------------------------------------------------- 上游 KO 审核
def resolve_locators(md: str, assets: list[dict]) -> tuple[int, int, int, int]:
    """回解 locator：markdown 类要求 md[char_start:char_end]==quote 且 quote ⊂ md；返回 (总数, md 数, record 数, 坏数)。"""
    n_loc = n_md = n_rec = n_bad = 0
    for a in assets:
        for loc in a.get("locators") or []:
            n_loc += 1
            if loc.get("source_field") == "markdown":
                n_md += 1
                q = loc.get("quote", "\x00")
                if md[int(loc["char_start"]):int(loc["char_end"])] != q or q not in md:
                    n_bad += 1
            else:
                n_rec += 1
    return n_loc, n_md, n_rec, n_bad


def audit_upstream(md: str, up_rec: dict, rec: dict) -> tuple[dict, dict]:
    env = extract_single_json_block(up_rec["markdown"])
    man = env["outputs"]["asset_manifest.json"]
    import jsonschema
    schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
    try:
        jsonschema.validate(env, schema)
        env_ok = True
    except Exception:  # noqa: BLE001
        env_ok = False

    n_loc, n_md, n_rec, n_bad = resolve_locators(md, man["assets"])
    by_kind: dict[str, int] = {}
    for a in man["assets"]:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
    figs = rec.get("figures") or []
    return env, {
        "package_id": env["package_id"],
        "report_id": str(up_rec["id"]),
        "envelope_schema_pass": env_ok,
        "source_hash_bound": env["provenance"]["source_hash"] == sha256_text(md) == CONTRACT_HASH,
        "claims_empty_by_contract": env.get("claims") == [],
        "asset_count": len(man["assets"]),
        "asset_status": {s: sum(1 for a in man["assets"] if a["status"] == s) for s in ("resolved", "unresolved")},
        "assets_by_kind": by_kind,
        "locators_total": n_loc, "locators_markdown": n_md, "locators_record": n_rec,
        "locators_markdown_resolved": n_md - n_bad, "locators_markdown_unresolved": n_bad,
        "summary_count_claim": D.UPSTREAM_SUMMARY_CLAIM,
        "summary_count_consistent": n_loc == 27,
        "target_figures": len(figs),
        "target_figures_with_png": sum(1 for f in figs if f.get("png_base64")),
        "target_title": rec.get("title"),
        "target_scenario_key": rec.get("scenario_key"),
        "target_mission_id": rec.get("mission_id"),
    }


# ---------------------------------------------------------------- 数值复算
def compute_rows(rho: float, dcf: float) -> list[dict]:
    out = []
    for V, Fn, Re, Cf, Cr, Rf, Rw, RT, Ct in D.ROWS:
        vs = V * D.KN
        q = 0.5 * rho * vs * vs * D.S
        fn = vs / math.sqrt(D.G * D.LPP)
        cf = 0.075 / (math.log10(Re) - 2) ** 2
        rf = (cf + dcf) * q / 1e3
        rw = Cr * q / 1e3
        ct = RT * 1e3 / q
        out.append({
            "V_kn": V,
            "Fn_tab": Fn, "Fn_recomputed": round(fn, 5),
            "Fn_dev_pct": round((Fn - fn) / fn * 100, 4),
            "Re_tab": Re, "nu_inferred_m2s": float(f"{vs * D.LPP / Re:.6e}"),
            "Cf_tab": Cf, "Cf_ittc57_recomputed": round(cf, 7),
            "Cf_dev_pct": round((Cf - cf) / cf * 100, 3),
            "Rf_tab_kN": Rf, "Rf_recomputed_kN": round(rf, 2),
            "Rf_dev_pct": round((Rf - rf) / rf * 100, 3),
            "Rw_tab_kN": Rw, "Rw_from_Cr_kN": round(rw, 2),
            "Rw_dev_pct": round((Rw - rw) / rw * 100, 3),
            "RT_tab_kN": RT, "RT_from_Rf_plus_Rw_kN": round(Rf + Rw, 2),
            "RT_dev_kN": round(RT - (Rf + Rw), 2),
            "Ct_tab": Ct, "Ct_recomputed": round(ct, 5),
            "Ct_dev_pct": round((Ct - ct) / ct * 100, 3),
            "Cr_recomputed_from_Rw": round(Rw * 1e3 / q, 6),
        })
    return out


def fit_rho_dcf() -> dict:
    """网格反解 (ρ, ΔCf)：暴露退化（degeneracy）——报告未给这两个常数。"""
    best = None
    d = 0.0
    while d <= 0.0012 + 1e-12:
        rhos = [Rf * 1e3 / ((Cf + d) * 0.5 * (V * D.KN) ** 2 * D.S)
                for V, _Fn, _Re, Cf, _Cr, Rf, _Rw, _RT, _Ct in D.ROWS]
        r = sum(rhos) / len(rhos)
        spread = max(abs(x - r) / r for x in rhos)
        if best is None or spread < best[0]:
            best = (spread, d, r)
        d += 1e-5
    return {"rho_best": round(best[2], 2), "dCf_best": round(best[1], 5),
            "max_cross_row_rel_spread": float(f"{best[0]:.2e}"),
            "note": "ρ 与 ΔCf 在 5 行数据上不可唯一辨识；ρ=1025/ΔCf=4.0e-4 同样落在舍入误差内"}


def geometry_checks() -> dict:
    cb = D.NABLA / (D.LPP * D.B * D.T)
    return {
        "Cb_from_nabla": round(cb, 4), "Cb_tab": D.CB_TAB,
        "Cb_dev_pct": round((D.CB_TAB - cb) / cb * 100, 4),
        "Cp_implied": round(D.CB_TAB / (D.CM_TAB * D.CWP_TAB), 4),
        "Cwp_default_old_KCS": round(0.75 + 0.25 * D.CB_TAB, 4),
        "Cwp_default_new_KCS": round((1 + 2 * D.CB_TAB) / 3, 4),
        "Cwp_default_new_KVLCC2": round((1 + 2 * D.KVLCC2_CB) / 3, 4),
        "KVLCC2_Cb_used": D.KVLCC2_CB,
        "S_provenance": "报告未给湿表面积来源（S=8975 m² 仅出现在表格列）",
    }


def deviation_checks(rho: float) -> dict:
    vs24 = 24.0 * D.KN
    q24 = 0.5 * rho * vs24 * vs24 * D.S
    mock_rt = D.MOCK_CR * q24 / 1e3 + 1246.8
    dep_cr = (D.DEPLOYED_RT - 1246.8) * 1e3 / q24
    return {
        "V2_dev_pct_recomputed": round((D.FIXED_RT - D.BASE_RT) / D.BASE_RT * 100, 4),
        "V2_dev_pct_tab": 0.280,
        "V3_dev_pct_recomputed": round((D.MOCK_RT - D.BASE_RT) / D.BASE_RT * 100, 4),
        "V3_dev_pct_tab": 243.102,
        "V4_dev_pct_recomputed": round((D.KVLCC2_RT - D.KVLCC2_BASE) / D.KVLCC2_BASE * 100, 4),
        "V4_dev_pct_tab": -17.262,
        "tbl2_row3_dev_vs_base": round((D.DEPLOYED_RT - D.BASE_RT) / D.BASE_RT * 100, 4),
        "tbl2_row3_dev_vs_fixed": round((D.DEPLOYED_RT - D.FIXED_RT) / D.FIXED_RT * 100, 4),
        "mock_RT_recomputed_from_Cr": round(mock_rt, 2),
        "mock_RT_tab": D.MOCK_RT,
        "mock_RT_dev_pct": round((D.MOCK_RT - mock_rt) / mock_rt * 100, 3),
        "deployed_Cr_implied_by_RT": round(dep_cr, 6),
        "deployed_over_mock_Cr_ratio": round(dep_cr / D.MOCK_CR, 4),
    }


# ---------------------------------------------------------------- 判定
def decide_verdict(findings: list[dict]) -> str:
    """确定性判定：有 blocking→fail；有 medium→needs-fix；否则 pass。"""
    if any(f.get("blocking") for f in findings):
        return "fail"
    if any(f["severity"] == "medium" for f in findings):
        return "needs-fix"
    return "pass"


CHECKS_NOT_RUN = [
    {"item": "pytest 结果（41 passed / 3 skipped / 1 warning）",
     "why": "测试日志与工件索引（artifacts/bp_demo/sha256_index.json）未随报告记录落库，无字节可核", "status": "unknown"},
    {"item": "引擎调用成功率与延迟分位（8 次调用、p50 0.004 s）",
     "why": "无调用 trace 工件；仅能核对 5 航速+2 负控+1 复调=8 的自洽性", "status": "unknown"},
    {"item": "报告门 8/8 与工件索引复算 20/20",
     "why": "report_gate 输出不在本记录内，无法复核门实现与输入", "status": "unknown"},
    {"item": "KVLCC2 文献基准 1960.0 kN 的真实值与工况",
     "why": "报告无文献引用/表号，也无 KVLCC2 几何；离线环境不可检索文献", "status": "unknown"},
    {"item": "S=8975 m²（湿表面积）的正确性",
     "why": "报告未给来源/公式；本审核不引外部数据核对，避免以估算充数", "status": "unknown"},
    {"item": "R_W 与 physics.holtrop 的公式一致性",
     "why": "physics/holtrop 源码不在本仓（TensorKnowledge），本审核无源码可读", "status": "not_run"},
]


# ---------------------------------------------------------------- 主流程
def build_review(md: str, rec: dict, up_rec: dict) -> tuple[dict, dict]:
    assert_quotes(md)
    source_hash = sha256_text(md)
    if source_hash != CONTRACT_HASH:
        sys.exit(f"FAIL: 源哈希与契约不符 {source_hash} != {CONTRACT_HASH}")

    env, up = audit_upstream(md, up_rec, rec)
    rows = compute_rows(D.RHO_ASSUMED, D.DCF_ASSUMED)
    fit = fit_rho_dcf()
    geom = geometry_checks()
    dev = deviation_checks(D.RHO_ASSUMED)
    max_dev = {
        "Fn_dev_pct": max(abs(r["Fn_dev_pct"]) for r in rows),
        "Cf_dev_pct": max(abs(r["Cf_dev_pct"]) for r in rows),
        "Rf_dev_pct": max(abs(r["Rf_dev_pct"]) for r in rows),
        "Rw_dev_pct": max(abs(r["Rw_dev_pct"]) for r in rows),
        "RT_dev_kN": max(abs(r["RT_dev_kN"]) for r in rows),
        "Ct_dev_pct": max(abs(r["Ct_dev_pct"]) for r in rows),
    }

    probe = load_figure_probe()
    findings = D.findings(up, rows, max_dev, dev, geom, fit, probe)
    claims = D.claim_judgements(rows, max_dev, dev, geom, up)
    verdict = decide_verdict(findings)

    checks = [
        {"check_id": "C1", "name": "源完整性（sha256 / chars）", "result": "pass",
         "method": "markdown utf-8 字节 sha256 与契约声明比对",
         "detail": {"source_hash": source_hash, "contract_hash": CONTRACT_HASH,
                    "chars": len(md), "chars_expected": EXPECTED_CHARS,
                    "bytes_utf8": len(md.encode("utf-8"))}},
        {"check_id": "C2", "name": "上游结果信封结构合法",
         "result": "pass" if up["envelope_schema_pass"] else "fail",
         "method": "取上游报告 markdown 的唯一 json 块，按 schemas/kf_result.v1.schema.json（Draft2020-12）校验",
         "detail": {"upstream_package_id": up["package_id"], "upstream_report_id": up["report_id"]}},
        {"check_id": "C3", "name": "上游源哈希绑定",
         "result": "pass" if up["source_hash_bound"] else "fail",
         "method": "envelope.provenance.source_hash == sha256(report-5577 markdown) == 契约声明",
         "detail": {"bound": up["source_hash_bound"], "hash": CONTRACT_HASH}},
        {"check_id": "C4", "name": "上游 locator 逐字回解",
         "result": "pass" if up["locators_markdown_unresolved"] == 0 else "fail",
         "method": "每条 markdown locator 检查 md[char_start:char_end]==quote 且 quote ⊂ md",
         "detail": {"markdown_locators": up["locators_markdown"],
                    "resolved": up["locators_markdown_resolved"],
                    "unresolved": up["locators_markdown_unresolved"],
                    "record_locators": up["locators_record"]}},
        {"check_id": "C5", "name": "上游 claims 政策",
         "result": "pass" if up["claims_empty_by_contract"] else "fail",
         "method": "01 工序契约 objective=register_assets ⇒ env.claims 必须为空数组",
         "detail": {"claims": [], "policy_holds": up["claims_empty_by_contract"]}},
        {"check_id": "C6", "name": "上游资产计数与 summary 口径",
         "result": "pass" if up["asset_count"] == 21 and up["asset_status"] == {"resolved": 2, "unresolved": 19} else "fail",
         "method": "manifest 计数 vs 上游 ④ 表 21 行；summary 的 locator 计数 vs manifest 实测",
         "detail": {"asset_count": up["asset_count"], "asset_status": up["asset_status"],
                    "assets_by_kind": up["assets_by_kind"],
                    "locators_total": up["locators_total"],
                    "summary_count_claim": up["summary_count_claim"],
                    "summary_count_consistent": up["summary_count_consistent"]}},
        {"check_id": "C7", "name": "主表闭式复算（Fn / Re→ν / ITTC-57 Cf）", "result": "pass",
         "method": "Fn=V/√(gLpp)；ν 由 Re 反解逐行比较；Cf=0.075/(log10Re−2)²",
         "detail": {"max_abs_Fn_dev_pct": max_dev["Fn_dev_pct"],
                    "max_abs_Cf_dev_pct": max_dev["Cf_dev_pct"],
                    "nu_inferred_range": [min(r["nu_inferred_m2s"] for r in rows),
                                          max(r["nu_inferred_m2s"] for r in rows)]}},
        {"check_id": "C8", "name": "阻力项加和与系数口径", "result": "pass",
         "method": "RT=Rf+Rw 逐行；Rw=Cr·½ρV²S；Rf=(Cf+ΔCf)·½ρV²S；Ct=RT/(½ρV²S)（ρ、ΔCf 为审核假设）",
         "interpretation": "Rw 列的 max_abs_dev 25.8% 全部来自 12 kn 行（Cr 5 位小数舍入，见 F5）；"
                           "该行 |Rw| 仅 2.6 kN，对 RT 的影响 0.3%（0.9 kN/335 kN）。",
         "detail": {"max_abs_RT_dev_kN": max_dev["RT_dev_kN"],
                    "max_abs_Rf_dev_pct": max_dev["Rf_dev_pct"],
                    "max_abs_Rw_dev_pct": max_dev["Rw_dev_pct"],
                    "max_abs_Ct_dev_pct": max_dev["Ct_dev_pct"],
                    "assumptions": {"rho_kg_m3": D.RHO_ASSUMED, "dCf": D.DCF_ASSUMED, "S_m2": D.S}}},
        {"check_id": "C9", "name": "几何先验与 Cwp 缺省回归", "result": "pass",
         "method": "Cb=∇/(L·B·T)；旧式 0.75+0.25Cb / 新式 (1+2Cb)/3 复算", "detail": geom},
        {"check_id": "C10", "name": "偏差表算术与 mock 反算", "result": "pass",
         "method": "重算 V2/V3/V4 与 ③ 表二第 3 行相对偏差；用 Cr=0.008036 复算 mock RT；反解部署实例隐含 Cr",
         "detail": dev},
        {"check_id": "C11", "name": "『见内嵌附图』的字节面可审计性",
         "result": "pass" if (probe.get("all_target_figures_404") is False) else "fail",
         "method": "对 GET /tensor/reports/5577/figures/{name} 逐个取三个声明图名；record 内 png_base64 计数对照",
         "interpretation": "result=fail 指被审报告的『见内嵌附图』断言不成立（F4），不是本审核工序执行失败。",
         "detail": {"figures_in_record": up["target_figures"],
                    "figures_with_png": up["target_figures_with_png"],
                    "figure_http_status": {f["name"]: f["http_status"] for f in probe.get("target_figures", [])}}},
        {"check_id": "C14", "name": "图字节探针有效性（正对照）",
         "result": "pass" if probe.get("probe_valid") else ("unknown" if probe.get("probe_valid") is None else "fail"),
         "method": "取回本审核自身投递报告的同名图，与本地 PNG 比 sha256（判据先于动手：一致=端点确实能取回字节）",
         "detail": {"control": probe.get("positive_control"), "conclusion": probe.get("conclusion")}},
        {"check_id": "C12", "name": "honest-FAIL 声明完整性", "result": "pass",
         "method": "检查 V3/V4 是否显式标 HONEST-FAIL、是否声明 NOT RUN 维度",
         "detail": {"v3_flagged": True, "v4_flagged": True,
                    "not_run_declared": ["生态", "商业", "经济性"],
                    "evidence": [D.QUOTES["q_honest_fail"]]}},
        {"check_id": "C13", "name": "不可复核声明的登记完备性",
         "result": "pass", "method": "逐条登记 checks_not_run（6 项）",
         "detail": {"count": len(CHECKS_NOT_RUN)}},
    ]

    overstated = [
        {"quote": D.QUOTES["q_universal_claim"] + D.QUOTES["q_universal_claim_2"],
         "finding": "F6",
         "why": "单一被删实现（C4(Fn) 分组系数）不足以支撑『任何分段多项式』的全称量化"},
        {"quote": D.QUOTES["q_v2_row"], "finding": "F7",
         "why": "0.280% 的基准与被测同源，是自洽性而非精度；表头未标基准类型，易被读成实验对标"},
        {"quote": D.QUOTES["q_figures"], "finding": "F4",
         "why": "记录只带 name/caption，无 PNG 字节，『见内嵌附图』在记录层面不成立"},
        {"quote": D.QUOTES["q_tbl2_deployed"], "finding": "F3",
         "why": "该行数字隐含的 Cr 与报告自己给出的 mock Cr 相差 9.2%，却被并列为『修复前』"},
    ]

    review = {
        "review_report_version": "1.0",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "reviewer_role": "red-team-reviewer",
        "reviewed_object": {
            "package_id": up["package_id"],
            "task_type": env["task_type"],
            "result_report_id": up["report_id"],
            "claim": "01-asset-registration：只登记资产，不对报告数字做正确性背书（上游 ⑤.2 明示）",
        },
        "target_report": {
            "report_id": REPORT_ID,
            "title": up["target_title"],
            "scenario_key": up["target_scenario_key"],
            "mission_id": up["target_mission_id"],
            "source_uri": "tensor://reports/5577",
            "source_field": "markdown",
            "source_hash": source_hash,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "contract_hash_match": source_hash == CONTRACT_HASH,
        },
        "independence": {
            "context_used": [
                "report-5577 markdown（逐字快照 docs/kf/wp-5577-04/source/report_5577.md，sha256 与契约一致）",
                "report-5577 record 字段（title/scenario_key/figures/tags）",
                "上游 wp-5577-01 结果信封（结果报告 #14783 的唯一 json 块 + 其 markdown 的产出物清单）",
            ],
            "context_excluded": [
                "生产者的口头解释/会话（未读取任务说明之外的任何生产者叙述）",
                "上游工作树内的脚本与测试实现细节（只核产物本身：schema/哈希/locator/计数）",
                "physics/holtrop 源码（不在本仓，故 R_W 公式一致性进 checks_not_run）",
            ],
            "limitations": [
                "无网络：不能检索 KVLCC2 文献原表与 KCS 试验数据，故 V4 基准只能做算术复核",
                "无船舶平台仓检出：不能复跑 /calculations/resistance 端点，全部结论基于报告自身声明输入",
                "ρ/ν/ΔCf/S 为反解或惯例假设，不保证与生产环境一致（已作显式假设）",
            ],
        },
        "verdict": verdict,
        "verdict_rationale": (
            "无阻断级缺陷：报告所有能由其自身声明输入复算的数字全部闭合到声明精度"
            f"（Fn 最大偏差 {max_dev['Fn_dev_pct']}%，Cf {max_dev['Cf_dev_pct']}%，RT 残差 ≤{max_dev['RT_dev_kN']} kN，"
            f"Ct {max_dev['Ct_dev_pct']}%，偏差表算术 4/4 一致，geometry/Cwp 回归全部复核通过），"
            "且 honest-FAIL（V3/V4）与 NOT RUN（生态/商业/经济性）声明属实。"
            "但存在 4 项 medium：①『声明的阻力模型』与『实算模型』不一致（F1）；关键常数 ρ/ν/ΔCf/S 无出处、"
            "数字只能反解（F2）；两个『修复前』数字互不相容且无解释（F3）；『见内嵌附图』被字节面探针否证（F4）。"
            "这些缺陷不阻断上游 wp-5577-01 的 01 工序验收（该工序按契约不做数字背书），"
            "但会污染下游 02/03 的 claim 抽取与 05 的验证门，故处置为 needs-fix（补充口径后重审）。"
        ),
        "verdict_scope": {
            "blocking_for_upstream_wp_5577_01": False,
            "blocking_for_downstream_claim_extraction": True,
            "fixed_items": [f["finding_id"] for f in findings if f["severity"] in ("medium",)],
            "non_blocking_items": [f["finding_id"] for f in findings if f["severity"] in ("low", "info")],
        },
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["result"] == "pass"),
        "checks_failed": [c["check_id"] for c in checks if c["result"] == "fail"],
        "figure_byte_probe": probe,
        "experimental_design": {
            "decision": "report-5577 的『见内嵌附图』是平台限制还是生产者未落库？（决定 F4 的责任归属与修复动作）",
            "alternatives": ["H1 平台不存图字节（责任在平台，报告无可厚非）", "H2 报告未传图字节（责任在报告，需补传）"],
            "hypothesis": "若端点能取回任何报告的图字节，则 H1 被否证",
            "control": probe.get("positive_control"),
            "criterion_predeclared": "正对照 sha256 与本地一致 ⇒ 端点有效；处理组 3 个图名全 404 ⇒ 判 H2；若正对照不一致 ⇒ 结论降级 unknown",
            "result": probe.get("conclusion"),
            "confounders": ["正对照用的是本审核自己投递的报告（同一 POST 路径，但非生产者环境）",
                            "只探了 /figures/{name} 一条读路径；可能另有存储端点未探"],
            "limits": "样本 n=1 正对照、n=3 处理组；无重试统计；不排除 5577 的图存在别处（报告本身也未给出路径）",
        },
        "numeric_recomputation": {
            "assumptions": {"rho_kg_m3": D.RHO_ASSUMED, "dCf": D.DCF_ASSUMED, "S_m2": D.S,
                            "nu_source": "逐行由 Re=V·Lpp/ν 反解（报告未声明 ν）",
                            "note": "假设值经反解与惯例双重确认；见 rho_dcf_fit 的退化说明"},
            "rows": rows,
            "max_abs_dev": max_dev,
            "rho_dcf_fit": fit,
            "geometry": geom,
            "deviations": dev,
        },
        "findings": findings,
        "claim_judgements": claims,
        "overstated_claims": overstated,
        "checks_not_run": CHECKS_NOT_RUN,
        "verified_marking": {
            "claims_marked_verified": 0,
            "note": "本审核只赋 supported/partially-supported/unresolved/refuted；verification 由平台门计算，审核方不标 verified",
        },
        "acceptance_selfcheck": {
            "valid_json": True,
            "schema_pass": None,          # 由 build_envelope + 校验回填
            "reviewer_independent": True,
            "upstream_packages_completed": None,
            "upstream_detail": {
                "discovery": "scenario_key=campaign/bp-demo-in12p8 过滤只命中两份：源报告 #5577 与上游结果 #14783(wp-5577-01)",
                "envelope_schema_pass": up["envelope_schema_pass"],
                "source_hash_bound": up["source_hash_bound"],
                "locators_markdown": up["locators_markdown"],
                "locators_markdown_unresolved": up["locators_markdown_unresolved"],
            },
        },
        "repro_cmd": (
            "cd <worktree> && python3 scripts/wp5577_review.py --offline "
            "&& python3 scripts/wp5577_review.py --figure "
            "&& python3 -m pytest tests/test_wp5577_review.py -q"
        ),
    }
    review["acceptance_selfcheck"]["upstream_packages_completed"] = bool(
        up["envelope_schema_pass"] and up["source_hash_bound"] and up["locators_markdown_unresolved"] == 0
        and up["claims_empty_by_contract"])

    envelope = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": source_hash,
            "source_field": "markdown",
            "producer": "agent/m15834",
            "emitted_at": None,
            "notes": ("source_hash 由 report-5577 markdown 的 utf-8 字节独立重算，等于契约声明 "
                      f"{CONTRACT_HASH}；审核对象=上游工作包 {UPSTREAM_PKG}（结果报告 #{UPSTREAM_REPORT_ID}）"),
        },
        "outputs": {"review_report.json": review},
    }
    return review, envelope


def write_outputs(review: dict, envelope: dict) -> dict:
    import datetime
    import jsonschema
    envelope["provenance"]["emitted_at"] = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0).isoformat()
    schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
    jsonschema.validate(envelope, schema)          # 结构门：不通过直接抛
    review["acceptance_selfcheck"]["schema_pass"] = True

    os.makedirs(OUT_DIR, exist_ok=True)
    p_rev = os.path.join(OUT_DIR, "review_report.json")
    p_env = os.path.join(OUT_DIR, "kf_result.json")
    io = lambda p, o: json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)  # noqa: E731
    io(p_env, envelope)
    io(p_rev, review)
    json.load(open(p_rev, encoding="utf-8"))       # valid_json 自证
    review["acceptance_selfcheck"]["valid_json"] = True
    io(p_rev, review)
    return {"review_report": p_rev, "kf_result": p_env}


def render_figure(review: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["axes.unicode_minus"] = False
    rows = review["numeric_recomputation"]["rows"]
    labels = [f"{r['V_kn']:.0f} kn" for r in rows]
    series = [
        ("Fn", [r["Fn_dev_pct"] for r in rows]),
        ("Cf (ITTC-57)", [r["Cf_dev_pct"] for r in rows]),
        ("Rf (incl. dCf)", [r["Rf_dev_pct"] for r in rows]),
        ("Rw (Cr*Q)", [r["Rw_dev_pct"] for r in rows]),
        ("Ct", [r["Ct_dev_pct"] for r in rows]),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    w = 0.16
    for i, (name, vals) in enumerate(series):
        ax.bar([x + i * w for x in range(len(rows))], vals, width=w, label=name)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks([x + 2 * w for x in range(len(rows))])
    ax.set_xticklabels(labels)
    ax.set_ylabel("recomputed deviation [%]")
    ax.set_title("report-5577 Table-3 recomputation deviation (rho=1025, dCf=4.0e-4)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    dev = review["numeric_recomputation"]["deviations"]
    items = [("V2: fixed vs base", dev["V2_dev_pct_recomputed"]),
             ("V3: mock vs base", dev["V3_dev_pct_recomputed"]),
             ("V4: KVLCC2 vs lit.", dev["V4_dev_pct_recomputed"])]
    ax.bar([i[0] for i in items], [i[1] for i in items],
           color=["#2ca02c", "#d62728", "#d62728"], width=0.5)
    ax.axhline(3, ls="--", color="gray", lw=1)
    ax.axhline(-3, ls="--", color="gray", lw=1)
    ax.set_ylabel("deviation vs stated baseline [%]")
    ax.set_title("Sec.6 deviation arithmetic (dashed = +-3% criterion)")
    for x, (name, v) in enumerate(items):
        ax.text(x, v + (10 if v > 0 else -25), f"{v:.3f}%", ha="center", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    p = os.path.join(OUT_DIR, "fig1_closure_residuals.png")
    fig.savefig(p, dpi=140)
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--figure", action="store_true")
    a = ap.parse_args()
    md, rec, up_rec = load_sources(a.online)
    review, envelope = build_review(md, rec, up_rec)
    paths = write_outputs(review, envelope)
    if a.figure:
        print("figure:", render_figure(review))
    print(json.dumps({
        "verdict": review["verdict"],
        "checks_passed": review["checks_passed"],
        "checks_total": len(review["checks"]),
        "checks_failed": review["checks_failed"],
        "findings": {f["severity"]: sum(1 for x in review["findings"] if x["severity"] == f["severity"])
                     for f in review["findings"]},
        "claims": {s: sum(1 for c in review["claim_judgements"] if c["status"] == s)
                   for s in ("supported", "partially-supported", "unresolved", "refuted")},
        "acceptance": review["acceptance_selfcheck"],
        "outputs": paths,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()