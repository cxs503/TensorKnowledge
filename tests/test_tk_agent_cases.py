"""TK agent cases — generator + verifier (``docs/ke/tk-agent-cases/``).

A *TK agent case* pins one question that a TensorKnowledge agent may answer from
the knowledge base, and pins **where every number comes from** (repo-relative
JSON file + JSON pointer), so that:

* the answer is reproducible (``pytest`` re-loads each pointer and fails on drift);
* acceptance is mechanical (deviation vs the 3 % criterion, convergence-order
  floor, machine-epsilon class, quoted-vs-reproduced separation);
* honest failures stay visible — a measurement over the criterion *must* be
  registered in ``scope.out_of_scope`` instead of being averaged away;
* provenance claims stay at the layer actually supported (structural complete is
  not the same as upstream source verified).

Usage
-----
``pytest tests/test_tk_agent_cases.py -q``        verify committed cases vs artefacts
``python tests/test_tk_agent_cases.py --regen``   rebuild cases + figures from artefacts
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CASES = ROOT / "docs" / "ke" / "tk-agent-cases"
RUN = "runs/oss-lbm-kruger-8676/validation_summary.json"
BENCH = "runs/oss-lbm-kruger-8676/kruger_bench_results.json"
CLAIM = "knowledge/oss-lbm/claims/tkc-oss-lbm-kruger-taylor-green-decay.json"
EVID = "knowledge/oss-lbm/evidence/tke-oss-lbm-kruger-tg-decay.json"
PKG = ROOT / "knowledge" / "oss-lbm"

TOL_PCT = 3.0
ORDER_FLOOR = 1.8
MACHINE_EPS = 1e-12
TG_CLAIM = "tkc:oss-lbm:kruger-taylor-green-decay"
CASE_FILES = ("case-a-taylor-green.json", "case-b-provenance.json",
              "case-c-exactness-scope.json")
QUOTE_PATTERN = r"实测误差\s*([0-9.]+)%"


# --------------------------------------------------------------------------- io
def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def at(rel: str, pointer: str):
    """Resolve a JSON pointer (``/a/b/0/c``) inside a repo-relative JSON file."""
    node = load(rel)
    for tok in [t for t in pointer.split("/") if t]:
        node = node[int(tok)] if isinstance(node, list) else node[tok]
    return node


def committed() -> dict:
    return {name: json.loads((CASES / name).read_text()) for name in CASE_FILES}


# ------------------------------------------------------------------ case build
def _meas(mid, label, rel, pointer, kind, threshold, note=""):
    return {
        "id": mid,
        "label": label,
        "value": at(rel, pointer),
        "unit": "pct" if ("pct" in kind or "err" in kind) else "1",
        "source": {"path": rel, "pointer": pointer},
        "acceptance": {"kind": kind, "threshold": threshold},
        "note": note,
    }


def _quoted(mid, label, rel, pointer, pattern, note=""):
    text = at(rel, pointer)
    value = float(re.search(pattern, text).group(1))
    return {
        "id": mid,
        "label": label,
        "value": value,
        "unit": "pct",
        "source": {"path": rel, "pointer": pointer, "pattern": pattern},
        "acceptance": {"kind": "quoted_value", "threshold": None},
        "note": note,
    }


def _ke_q(mid, label, op, claim_id, expected, note=""):
    return {
        "id": mid,
        "label": label,
        "value": expected,
        "unit": "count",
        "source": {"ke_query": {"op": op, "claim_id": claim_id,
                                "package": "knowledge/oss-lbm"}},
        "acceptance": {"kind": "exact_match", "threshold": expected},
        "note": note,
    }


def _measurements_a():
    return [
        _meas("tg_dev_nx32", "Taylor-Green 能量衰减相对偏差 NX=32",
              RUN, "/taylor_green/runs/0/E_rel_dev_pct", "rel_err_pct_le", TOL_PCT,
              "E/E0 measured vs exp(-2t/t_d)"),
        _meas("tg_dev_nx64", "Taylor-Green 能量衰减相对偏差 NX=64",
              RUN, "/taylor_green/runs/1/E_rel_dev_pct", "rel_err_pct_le", TOL_PCT),
        _meas("tg_dev_nx128", "Taylor-Green 能量衰减相对偏差 NX=128",
              RUN, "/taylor_green/runs/2/E_rel_dev_pct", "rel_err_pct_le", TOL_PCT),
        _meas("tg_order_nx64", "L2(u_x) 收敛阶 32→64",
              RUN, "/taylor_green/runs/1/observed_order", "order_ge", ORDER_FLOOR,
              "二阶格式名义阶 2，实测拟合阶"),
        _meas("tg_order_nx128", "L2(u_x) 收敛阶 64→128",
              RUN, "/taylor_green/runs/2/observed_order", "order_ge", ORDER_FLOOR),
        _meas("poiseuille_port_l2", "Poiseuille(BB) 剖面 L2 相对误差（本仓 NumPy 端口）",
              BENCH, "/runs/0/L2", "machine_eps_le", MACHINE_EPS,
              "tau 由 u_max 反解，稳态判据 |mean(u)/mean(u_old)-1|<1e-12"),
        _meas("ib_lbm_centreline_err", "IB-LBM Poiseuille 中心线速度相对误差",
              RUN, "/ib_lbm_poiseuille/centreline_error_pct", "rel_err_pct_le", TOL_PCT,
              "沉浸边界算例：19x20 格分辨率过低，超出 3% 判据"),
    ]


def _measurements_b():
    return [
        _ke_q("tg_evidence_count", "claim 直连证据条数", "evidence_count", TG_CLAIM, 1),
        _ke_q("tg_dangling_refs", "claim 悬空 evidence_ref 条数", "dangling_refs", TG_CLAIM, 0,
              "悬空引用必须显式可见，不能被静默吞掉"),
        _ke_q("tg_claim_level_prov", "claim 级 PROV 记录条数", "provenance_records", TG_CLAIM, 0,
              "0 = 本包只为部分 claim 落了 tkp 记录；lineage 只能主张到 citation 级"),
    ]


def _measurements_c():
    return [
        _quoted("tg_quoted_err", "claim 正文引用的误差（Krüger 原文）",
                CLAIM, "/statement", QUOTE_PATTERN,
                "引用值来自教科书原文，不是本仓复现值"),
        _meas("tg_repro_nx32", "本仓复现 |偏差| NX=32",
              RUN, "/taylor_green/runs/0/E_rel_dev_pct", "rel_err_pct_le", TOL_PCT),
        _meas("tg_repro_nx64", "本仓复现 |偏差| NX=64",
              RUN, "/taylor_green/runs/1/E_rel_dev_pct", "rel_err_pct_le", TOL_PCT),
        _meas("tg_repro_nx128", "本仓复现 |偏差| NX=128",
              RUN, "/taylor_green/runs/2/E_rel_dev_pct", "rel_err_pct_le", TOL_PCT),
    ]


def build_cases() -> dict:
    claim_doc, evid_doc = load(CLAIM), load(EVID)
    tg = load(RUN)["taylor_green"]["runs"]
    port = [r for r in load(BENCH)["runs"] if r["case"] == "poiseuille_BB"][0]
    ib = load(RUN)["ib_lbm_poiseuille"]
    ma, mb, mc = _measurements_a(), _measurements_b(), _measurements_c()

    case_a = {
        "schema": "tk-agent-case/1",
        "case_id": "case-a-taylor-green",
        "title": "Taylor-Green 涡衰减：知识卡上的精度主张能否被复现？",
        "dimension_focus": "D2(类型) → 可复现数值：claim 的精度主张必须落到一条被记录的运行工件上",
        "question": ("LBM D2Q9 的 Taylor-Green 涡衰减验证里，能量衰减相对理论值的偏差是多少？"
                     "是否满足 <3% 判据？"),
        "answer_summary": (
            "复现运行（3 个分辨率）的能量衰减相对偏差全部 <3%：NX=32 {a:+.3f}%、NX=64 {b:+.3f}%、"
            "NX=128 {c:+.3f}%；L2(u_x) 实测收敛阶 {o1:.3f}/{o2:.3f}（二阶格式名义阶 2）。"
            "同一知识包内的 Poiseuille(BB) 端口算例达机器精度（L2={l2:.2e}），"
            "而 IB-LBM Poiseuille 中心线偏差 {ib:+.2f}% 超判据，必须排除在结论之外。"
        ).format(a=tg[0]["E_rel_dev_pct"], b=tg[1]["E_rel_dev_pct"], c=tg[2]["E_rel_dev_pct"],
                 o1=tg[1]["observed_order"], o2=tg[2]["observed_order"], l2=port["L2"],
                 ib=ib["centreline_error_pct"]),
        "verdict": "pass_with_scope_exclusion",
        "knowledge": {
            "claim_id": claim_doc["id"],
            "claim_statement": claim_doc["statement"],
            "epistemic_status": claim_doc["epistemic_status"],
            "domain": claim_doc["scope"]["domain"],
            "evidence_ids": claim_doc["evidence_refs"],
            "claim_file": CLAIM,
            "evidence_file": EVID,
            "source_citation": evid_doc["source"]["citation"],
            "source_locator": evid_doc["locator"]["value"],
        },
        "retrieval": {
            "ke_endpoints": [
                "/query/by-domain?domain=lattice%20Boltzmann%20multiphase%2Fmulticomponent%20methods",
                "/query/by-evidence-relation?relation=supports",
                f"/query/chain?claim_id={claim_doc['id']}",
                f"/query/claim-evidence?claim_id={claim_doc['id']}",
                "/search?q=Taylor-Green",
            ],
            "filters_used": {"domain": claim_doc["scope"]["domain"], "kind": "claim",
                             "axis": "evidence", "status": "established"},
            "expected_hits": 1,
        },
        "measurements": ma,
        "figures": [
            {"file": "fig-taylor-green.png",
             "caption": ("左：三分辨率能量衰减相对偏差 vs 3% 判据与教科书引用值；"
                         "右：L2(u_x) 收敛（log-log，斜率→实测阶 2）。")},
            {"file": "fig-poiseuille.png",
             "caption": ("左：Poiseuille(BB) 数值剖面与解析抛物线重合（L2~1e-16）；"
                         "右：IB-LBM 算例中心线欠预测，作为出界样本登记。")},
        ],
        "scope": {
            "in_scope": [
                "D2Q9 单相 Taylor-Green 涡，周期边界，E(t)/E(0)=exp(-2t/t_d)",
                "指标：能量衰减率、L2(u_x) 收敛阶",
                "判据来源：runs/oss-lbm-kruger-8676 记录的分辨率扫描",
            ],
            "out_of_scope": [{
                "measurement_ids": ["ib_lbm_centreline_err"],
                "reason": ("IB-LBM（沉浸边界）Poiseuille 在 19x20 格上中心线欠预测 "
                           f"{ib['centreline_error_pct']:+.2f}%，未过 3% 判据；本 case 不把它算作 "
                           "Taylor-Green 的佐证，也不把它升级为「KB 已验证」结论。"),
            }],
            "withheld": [
                "高 Re / 三维 Taylor-Green 的精度主张：仓内无运行工件 → WITHHELD",
                "其他指标（涡量极值、压力场）未记录基准 → WITHHELD",
            ],
        },
        "agent_rules": [
            "引用 claim 的数字时必须同时给出 run 工件路径 + JSON pointer。",
            "claim 正文的教科书引用值不得当作本仓复现值使用（见 case-c）。",
            "任一测量超判据时，必须显式列入 out_of_scope 并报告 honest-FAIL，不得静默取平均。",
        ],
        "known_gaps": ["无三维/高 Re 复现数据", "无压力场与涡量极值基准"],
    }

    case_b = {
        "schema": "tk-agent-case/1",
        "case_id": "case-b-provenance",
        "title": "溯源：这张卡引用的误差数字到底从哪来？链到哪一层为止？",
        "dimension_focus": "D4(溯源定位) → 结构化完整性与活性的区分",
        "question": ("知识卡 tkc:oss-lbm:kruger-taylor-green-decay 的证据链是否结构完整？"
                     "外部源定位符能否在本工作树内落地（liveness）？"),
        "answer_summary": (
            f"claim {claim_doc['id']} → 1 条 supports 证据（{evid_doc['id']}）→ 定位符 "
            f"{evid_doc['locator']['value']}（{evid_doc['locator']['locator_type']}，"
            f"{evid_doc['extraction_method']}）。结构完整：无悬空 evidence_ref；"
            "但 claim 级 PROV 记录为 0（包内只有部分 claim 落 tkp），"
            "且上游仓库 lbm-principles-practice/code 未 vendor 进本工作树 → 活性=WITHHELD。"
        ),
        "verdict": "structural_complete_liveness_withheld",
        "knowledge": {
            "claim_id": claim_doc["id"],
            "claim_file": CLAIM,
            "evidence_ids": [evid_doc["id"]],
            "evidence_file": EVID,
            "evidence_relation": evid_doc["relation"],
            "evidence_assessment_status": evid_doc["assessment_status"],
            "source_type": evid_doc["source"]["source_type"],
            "source_citation": evid_doc["source"]["citation"],
            "locator_type": evid_doc["locator"]["locator_type"],
            "locator_value": evid_doc["locator"]["value"],
            "extraction_method": evid_doc["extraction_method"],
        },
        "retrieval": {
            "ke_endpoints": [
                f"/query/chain?claim_id={claim_doc['id']}",
                f"/query/claim-evidence?claim_id={claim_doc['id']}",
                "/query/stats",
            ],
            "filters_used": {"kind": "provenance", "claim_id": claim_doc["id"]},
            "expected_hits": 1,
        },
        "measurements": mb,
        "figures": [],
        "liveness": {
            "external_source": {
                "citation": evid_doc["source"]["citation"],
                "locator": evid_doc["locator"]["value"],
                "resolvable_in_worktree": False,
                "reason": ("上游 lbm-principles-practice/code 未 vendor 到 TensorKnowledge 工作树；"
                           "仓内只有本仓复现运行（runs/oss-lbm-kruger-8676）"),
            },
            "in_repo_artifacts": [
                {"path": RUN, "role": "本仓复现运行记录（可落地）"},
                {"path": BENCH, "role": "NumPy 端口剖面/误差记录（可落地）"},
            ],
        },
        "scope": {
            "in_scope": [
                "claim→evidence→locator 的结构完整性（id 可解析、无悬空引用）",
                "证据的抽取方式与评估状态（direct-quotation / unassessed）",
            ],
            "out_of_scope": [],
            "withheld": [
                "上游源码行的逐字活性校验（需 vendor 上游仓库或网络）",
                "claim 级活动溯源（谁在何时抽取）：仓内缺 tkp 记录",
            ],
        },
        "agent_rules": [
            "只允许主张「结构完整 + 外部定位符已知」，禁止主张「已逐字核验上游源码」。",
            "claim 级 PROV 缺失时必须报告缺口，不能用包级 provenance 冒充。",
            "evidence assessment_status=unassessed 时，输出必须带未评估标签。",
        ],
        "known_gaps": [
            "taylor-green claim 缺 claim 级 tkp 记录（包内 provenance 覆盖不全）",
            "上游仓库未 vendor，locator 无法在本树内解析",
        ],
    }

    quoted_val = mc[0]["value"]
    case_c = {
        "schema": "tk-agent-case/1",
        "case_id": "case-c-exactness-scope",
        "title": "精确性边界：引用误差能否被当成「分辨率无关」的结论？",
        "dimension_focus": "D3(信任) × 精确性粒度：引用值 / 复现值 / 判据三层必须分开陈述",
        "question": (f"claim 正文引用「实测误差 {quoted_val:.3f}%」，本仓复现给出不同分辨率下的偏差；"
                     "agent 应如何陈述该数字的适用范围？"),
        "answer_summary": (
            f"引用值 {quoted_val:.3f}% 是教科书原文的单一网格结果；本仓复现为 "
            f"NX=32 {mc[1]['value']:+.3f}%、NX=64 {mc[2]['value']:+.3f}%、"
            f"NX=128 {mc[3]['value']:+.3f}% —— 全部 <3% 判据，但随分辨率单调改善，"
            "因此禁止把引用值当作分辨率无关常量。"
        ),
        "verdict": "pass_with_granularity_constraint",
        "knowledge": {
            "claim_id": claim_doc["id"],
            "claim_file": CLAIM,
            "evidence_file": EVID,
            "claim_statement": claim_doc["statement"],
        },
        "retrieval": {
            "ke_endpoints": [
                "/search?q=%E8%A1%B0%E5%87%8F%E7%8E%87",
                f"/query/chain?claim_id={claim_doc['id']}",
                "/query/by-status?axis=evidence&status=established&kind=claim",
            ],
            "filters_used": {"axis": "evidence", "status": "established"},
            "expected_hits": 1,
        },
        "measurements": mc,
        "figures": [{
            "file": "fig-exactness-scope.png",
            "caption": ("各量 |偏差| 与 3% 判据的对数刻度对照 + 精确性等级计数"
                        "（机器精度 / <3% / >3% 出界 / WITHHELD）。"),
        }],
        "granularity": {
            "statement": ("同一物理量的精度主张按来源分三层：引用(quoted) / 复现(reproduced) / "
                          "判据(tolerance)；三层不得混用。"),
            "cited_value_pct": quoted_val,
            "cited_source": {"path": CLAIM, "pointer": "/statement", "pattern": QUOTE_PATTERN},
            "reproduced": [
                {"resolution": "NX=32", "value_pct": mc[1]["value"], "source": mc[1]["source"]},
                {"resolution": "NX=64", "value_pct": mc[2]["value"], "source": mc[2]["source"]},
                {"resolution": "NX=128", "value_pct": mc[3]["value"], "source": mc[3]["source"]},
            ],
            "monotone_in_resolution": True,
        },
        "scope": {
            "in_scope": [
                "引用值与其出处（教科书 chapter13 vortexdecay.m）",
                "本仓复现值与其 run 工件",
                "3% 判据（平台精度标准）",
            ],
            "out_of_scope": [],
            "withheld": [
                "把引用值推广到其他分辨率/几何：无数据支撑",
                "低于 0.05% 的精度主张：记录分辨率为 2 位有效数字，无法支撑",
            ],
        },
        "agent_rules": [
            "引用值与复现值必须分别标注来源，不得合并成单一数字。",
            "精度主张必须带分辨率标签（NX/格距）。",
            "超出记录分辨率的精度断言 → WITHHELD，不得四舍五入升级。",
        ],
        "known_gaps": ["仓内无 256^2 及以上分辨率运行，无法给出渐近精度"],
    }
    return {CASE_FILES[0]: case_a, CASE_FILES[1]: case_b, CASE_FILES[2]: case_c}


def measurement_verdict(m: dict) -> str:
    """Mechanical re-computation of one measurement's verdict."""
    kind, th, v = m["acceptance"]["kind"], m["acceptance"]["threshold"], m["value"]
    if kind in ("rel_err_pct_le", "abs_le", "machine_eps_le"):
        return "pass" if abs(v) <= th else "fail"
    if kind == "order_ge":
        return "pass" if v >= th else "fail"
    if kind == "exact_match":
        return "match" if v == th else "fail"
    if kind == "quoted_value":
        return "quoted"
    raise AssertionError(f"unknown acceptance kind {kind!r}")


def ke_count(conn, op: str, claim_id: str) -> int:
    """Execute one ``ke_query`` measurement op against a KE store."""
    from ke import queries

    if op == "evidence_count":
        return len(queries.evidence_for_claim(conn, claim_id))
    if op == "provenance_records":
        return sum(1 for p in queries.all_provenance(conn)
                   if p.get("generated_entity_id") == claim_id)
    if op == "dangling_refs":
        row = conn.execute("SELECT evidence_refs_json FROM claims WHERE id = ?",
                           (claim_id,)).fetchone()
        refs = json.loads((row["evidence_refs_json"] if row else None) or "[]")
        have = {e["id"] for e in queries.all_evidence(conn)}
        return len([r for r in refs if r not in have])
    raise AssertionError(f"unknown ke_query op {op!r}")


def _ke_store():
    """In-memory KE store with the real ``knowledge/oss-lbm`` package ingested."""
    from ke import contract, store

    conn = store.connect(":memory:")
    conn.scripts(contract.SCHEMA)
    counts = contract.ingest_source(str(PKG), conn, strict=False)
    return conn, counts


def at_ke_count(op: str, claim_id: str) -> int:
    conn, _ = _ke_store()
    try:
        return ke_count(conn, op, claim_id)
    finally:
        conn.close()


def build_summary(cases: dict) -> dict:
    docs = [cases[name] for name in CASE_FILES]
    tot = {"pass": 0, "fail": 0, "quoted": 0, "match": 0}
    for doc in docs:
        for m in doc["measurements"]:
            tot[measurement_verdict(m)] += 1
    ma = docs[0]["measurements"]
    return {
        "schema": "tk-agent-cases-summary/1",
        "mission": 19445,
        "generated_from": {
            "runs": [RUN, BENCH],
            "package": "knowledge/oss-lbm",
            "generator": "python tests/test_tk_agent_cases.py --regen",
        },
        "acceptance": {
            "tolerance_pct": TOL_PCT,
            "basis": "平台精度标准：对标实验/参考值误差 >15% 不可接受；本项目收紧到 3%",
            "machine_eps_threshold": MACHINE_EPS,
            "convergence_order_floor": ORDER_FLOOR,
        },
        "cases": [
            {
                "case_id": doc["case_id"],
                "file": name,
                "verdict": doc["verdict"],
                "dimension_focus": doc["dimension_focus"],
                "measurements": len(doc["measurements"]),
                "failures": [m["id"] for m in doc["measurements"]
                             if measurement_verdict(m) == "fail"],
                "figures": [f["file"] for f in doc["figures"]],
            }
            for name, doc in zip(CASE_FILES, docs)
        ],
        "totals": tot,
        "exactness_classes": {
            "machine_precision": [m["id"] for m in ma
                                  if m["acceptance"]["kind"] == "machine_eps_le"],
            "within_tolerance": [m["id"] for m in ma
                                 if measurement_verdict(m) == "pass"
                                 and m["acceptance"]["kind"] != "order_ge"],
            "out_of_scope": [m["id"] for m in ma if measurement_verdict(m) == "fail"],
            "withheld": ["high_Re_3d_taylor_green", "pressure_field",
                         "external_source_liveness", "asymptotic_precision_above_128"],
        },
        "retrieval_dimensions": [
            {"id": "D1", "key": "domain", "column": "claims.domain / knowledge_base.domain",
             "surface": "GET /query/by-domain?domain=&exact=  |  GET /kb/search?domain="},
            {"id": "D2", "key": "ktype",
             "column": "kind (claim/evidence/provenance/review) / knowledge_base.ktype",
             "surface": "GET /ko?kind=  |  GET /kb/search?ktype="},
            {"id": "D3", "key": "status",
             "column": ("epistemic_status / review_status / publication_status / "
                        "knowledge_base.status"),
             "surface": "GET /query/by-status?axis=&status=  |  GET /kb/search?status="},
            {"id": "D4", "key": "locator", "column": "evidence.locator_* / provenance record",
             "surface": "GET /query/chain?claim_id=  |  GET /query/claim-evidence?claim_id="},
        ],
        "provenance_state": {
            "structural": "complete",
            "claim_level_records": at_ke_count("provenance_records", TG_CLAIM),
            "external_liveness": "withheld",
        },
        "honest_failures": [{
            "id": "ib_lbm_centreline_err",
            "detail": (f"IB-LBM Poiseuille 中心线偏差 "
                       f"{at(RUN, '/ib_lbm_poiseuille/centreline_error_pct'):+.2f}% > 3% → "
                       "明确排除，不参与 Taylor-Green 佐证"),
        }],
        "one_line": (f"3 个 agent case，{sum(len(d['measurements']) for d in docs)} 条可复算测量："
                     f"{tot['pass']} 过判据 / {tot['fail']} 出界（如实登记）/ "
                     f"{tot['quoted']} 引用值 / {tot['match']} 结构事实"),
    }


def write_summary_md(cases: dict) -> str:
    a, b, c = (cases[n] for n in CASE_FILES)
    rows = ["| case | 问题 | 维度 | 判定 | 失败项 |", "|---|---|---|---|---|"]
    for doc in (a, b, c):
        fails = ", ".join(m["id"] for m in doc["measurements"]
                          if measurement_verdict(m) == "fail") or "—"
        rows.append(f"| {doc['case_id']} | {doc['title']} | {doc['dimension_focus']} | "
                    f"`{doc['verdict']}` | {fails} |")
    tg = load(RUN)["taylor_green"]["runs"]
    return f"""# TK agent cases — 知识 ↔ 数值的对接面（m19445）

机器可读判据：`summary.json`；逐案：`case-a-taylor-green.json`、`case-b-provenance.json`、
`case-c-exactness-scope.json`。所有数字由 `{RUN}` / `{BENCH}` 程序化注入，
`pytest tests/test_tk_agent_cases.py` 逐条回读校验（零手抄）。

{chr(10).join(rows)}

## 关键数字（判据 3%）

| 量 | 值 | 来源 |
|---|---|---|
| TG 能量衰减偏差 NX=32/64/128 | {tg[0]['E_rel_dev_pct']:+.3f}% / {tg[1]['E_rel_dev_pct']:+.3f}% / {tg[2]['E_rel_dev_pct']:+.3f}% | `{RUN}` |
| L2(u_x) 实测收敛阶（32→64 / 64→128） | {tg[1]['observed_order']:.3f} / {tg[2]['observed_order']:.3f} | 同上 |
| Poiseuille(BB) 剖面 L2 | {at(BENCH, '/runs/0/L2'):.2e} | `{BENCH}` |
| IB-LBM 中心线偏差 | {at(RUN, '/ib_lbm_poiseuille/centreline_error_pct'):+.2f}%（出界，登记为 honest-FAIL） | `{RUN}` |

图：`fig-taylor-green.png`（衰减 + 收敛）、`fig-poiseuille.png`（端口 vs IB-LBM）、
`fig-exactness-scope.png`（精确性等级）。

## 未闭合项（如实）

- claim `{TG_CLAIM}` 无 claim 级 PROV 记录（包内 provenance 未覆盖全部 claim）→ lineage 只能主张 citation 级。
- 上游 `lbm-principles-practice/code` 未 vendor → 定位符活性 WITHHELD。
- 无 256² 以上分辨率运行 → 渐近精度断言 WITHHELD。

## 复现

```bash
pytest tests/test_tk_agent_cases.py -q          # 校验 JSON↔工件、图与判据
python tests/test_tk_agent_cases.py --regen     # 由工件重生成 case/图（数据不再手抄）
```
"""

# ------------------------------------------------------------------- figures
def regen_figures(cases: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                         "figure.dpi": 130, "savefig.bbox": "tight"})

    tg = load(RUN)["taylor_green"]["runs"]
    nx = [r["NX"] for r in tg]
    dev = [abs(r["E_rel_dev_pct"]) for r in tg]
    l2 = [r["L2_ux"] for r in tg]
    order = [r["observed_order"] for r in tg[1:]]  # scale-1 run has no coarser neighbour
    quoted = cases[CASE_FILES[2]]["granularity"]["cited_value_pct"]

    fig, (a, b) = plt.subplots(1, 2, figsize=(9.2, 3.6))
    a.plot(nx, dev, "o-", color="#1f77b4", label="measured |dE/E| (reproduced)")
    a.axhline(TOL_PCT, ls="--", color="#d62728", label=f"{TOL_PCT:.0f} % acceptance")
    a.axhline(quoted, ls=":", color="#2ca02c", label=f"textbook quote {quoted:.3f} %")
    a.set_xscale("log", base=2)
    a.set_yscale("log")
    a.set_xlabel("grid NX")
    a.set_ylabel("|dE/E0|  [%]")
    a.set_title("Taylor-Green energy decay: reproduced vs criteria")
    for x, y in zip(nx, dev):
        a.annotate(f"{y:.3f}%", (x, y), textcoords="offset points", xytext=(4, 6))
    a.legend(loc="lower left", fontsize=7)
    b.loglog(nx[1:], l2[1:], "s-", color="#ff7f0e", label="L2(u_x)")
    b.loglog(nx[1:], np.array(l2[1:]) * (np.array(nx[1:]) / nx[1]) ** -2.0, "k--", lw=1,
             label="slope -2 reference")
    b.set_xlabel("grid NX")
    b.set_ylabel("L2 error of u_x")
    b.set_title(f"convergence: measured order {order[0]:.2f} / {order[1]:.2f}")
    for x, y in zip(nx[1:], l2[1:]):
        b.annotate(f"{y:.2e}", (x, y), textcoords="offset points", xytext=(4, -12), fontsize=7)
    b.legend(fontsize=7)
    fig.suptitle("TK agent case A - Taylor-Green (data: runs/oss-lbm-kruger-8676)", fontsize=10)
    f1 = CASES / "fig-taylor-green.png"
    fig.savefig(f1)
    plt.close(fig)

    port = [r for r in load(BENCH)["runs"] if r["case"] == "poiseuille_BB"][0]
    ib = load(RUN)["ib_lbm_poiseuille"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.2, 3.6))
    a.plot(port["profile_u"], port["profile_y"], "o", color="#1f77b4", label="numerical (port)")
    a.plot(port["profile_u_analytic"], port["profile_y"], "k--", lw=1.2,
           label="analytic parabola")
    a.set_xlabel("u_x")
    a.set_ylabel("y")
    a.set_title(f"Poiseuille + bounce-back: L2 = {port['L2']:.2e}")
    a.legend(fontsize=7)
    b.plot(ib["profile_u"], range(len(ib["profile_u"])), "s-", color="#d62728", ms=3,
           label="IB-LBM reproduced")
    b.axvline(ib["u_max_expected"], ls="--", color="k",
              label=f"expected u_max {ib['u_max_expected']:.5f}")
    b.set_xlabel("u_x")
    b.set_ylabel("lattice row")
    b.set_title(f"IB-LBM Poiseuille: centreline {ib['centreline_error_pct']:+.2f} % (>3 %)")
    b.legend(fontsize=7)
    fig.suptitle("TK agent case A/C - Poiseuille exactness: machine-precision vs out-of-scope",
                 fontsize=10)
    f2 = CASES / "fig-poiseuille.png"
    fig.savefig(f2)
    plt.close(fig)

    ma = cases[CASE_FILES[0]]["measurements"]
    labels, vals, colors = [], [], []
    for m in ma:
        if m["acceptance"]["kind"] == "order_ge":
            continue
        labels.append(m["id"].replace("_", " "))
        v = abs(m["value"])
        vals.append(v if v > 0 else 1e-16)
        colors.append("#d62728" if measurement_verdict(m) == "fail" else "#2ca02c")
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.7),
                               gridspec_kw={"width_ratios": [1.55, 1]})
    ypos = list(range(len(labels)))[::-1]
    a.barh(ypos, vals, color=colors, alpha=0.85)
    a.set_yticks(ypos)
    a.set_yticklabels(labels, fontsize=7)
    a.set_xscale("log")
    a.axvline(TOL_PCT, ls="--", color="#d62728")
    a.axvline(MACHINE_EPS, ls=":", color="#1f77b4")
    a.set_xlabel("|deviation|  [%] (log)")
    a.set_title("per-quantity exactness vs 3 % line / machine eps")
    for y, v in zip(ypos, vals):
        a.annotate(f"{v:.2e}" if v < 1e-6 else f"{v:.3f}%", (v, y),
                   textcoords="offset points", xytext=(4, -2), fontsize=7)
    counts = {"machine eps\n(<=1e-12)": 0, "within 3 %": 0, "out of scope\n(>3 %)": 0,
              "WITHHELD": len(cases[CASE_FILES[2]]["scope"]["withheld"])}
    for m in ma:
        kind = m["acceptance"]["kind"]
        if kind == "machine_eps_le":
            counts["machine eps\n(<=1e-12)"] += 1
        elif kind == "rel_err_pct_le":
            counts["within 3 %" if measurement_verdict(m) == "pass"
                   else "out of scope\n(>3 %)"] += 1
    b.bar(list(counts), list(counts.values()),
          color=["#1f77b4", "#2ca02c", "#d62728", "#7f7f7f"])
    b.set_ylabel("count")
    b.set_title("exactness classes")
    for i, v in enumerate(counts.values()):
        b.annotate(str(v), (i, v), textcoords="offset points", xytext=(0, 3), ha="center",
                   fontsize=8)
    b.tick_params(axis="x", labelsize=7)
    fig.suptitle("TK agent case C - exactness scope map", fontsize=10)
    f3 = CASES / "fig-exactness-scope.png"
    fig.savefig(f3)
    plt.close(fig)
    return [f1, f2, f3]


def regen() -> dict:
    CASES.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    out = {}
    for name, doc in cases.items():
        path = CASES / name
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        out[name] = path
    sp = CASES / "summary.json"
    sp.write_text(json.dumps(build_summary(cases), ensure_ascii=False, indent=2) + "\n")
    out["summary.json"] = sp
    mp = CASES / "summary.md"
    mp.write_text(write_summary_md(cases))
    out["summary.md"] = mp
    for p in regen_figures(cases):
        out[p.name] = p
    return out


# ---------------------------------------------------------------------- tests
@pytest.fixture(scope="module")
def cases() -> dict:
    missing = [n for n in CASE_FILES if not (CASES / n).is_file()]
    assert not missing, f"missing case files: {missing}"
    return committed()


@pytest.fixture(scope="module")
def ke_store():
    conn, counts = _ke_store()
    yield conn, counts
    conn.close()


def test_case_files_are_schema_conformant(cases):
    for name, doc in cases.items():
        assert doc["schema"] == "tk-agent-case/1", name
        for key in ("case_id", "title", "dimension_focus", "question", "answer_summary",
                    "verdict", "knowledge", "retrieval", "measurements", "scope",
                    "agent_rules"):
            assert key in doc, f"{name}: missing {key}"
        assert doc["case_id"] == name[:-5], f"{name}: case_id mismatch"
        ids = [m["id"] for m in doc["measurements"]]
        assert len(ids) == len(set(ids)), f"{name}: duplicate measurement ids"
        for m in doc["measurements"]:
            assert set(m) >= {"id", "label", "value", "source", "acceptance"}
            assert m["acceptance"]["kind"] in {
                "rel_err_pct_le", "abs_le", "machine_eps_le", "order_ge",
                "exact_match", "quoted_value"}


def test_every_number_matches_its_recorded_artefact(cases):
    """Zero hand-copy: every float is re-read from the file + pointer it names."""
    checked = 0
    for name, doc in cases.items():
        for m in doc["measurements"]:
            src = m["source"]
            if "path" in src:
                got = at(src["path"], src["pointer"])
                if m["acceptance"]["kind"] == "quoted_value":
                    got = float(re.search(src["pattern"], got).group(1))
                assert got == m["value"], (
                    f"{name}/{m['id']}: drift {got!r} != {m['value']!r} "
                    f"({src['path']}#{src['pointer']})")
                checked += 1
            else:
                assert "ke_query" in src, f"{name}/{m['id']}: no source"
    assert checked >= 11


def test_verdicts_recomputed_from_thresholds(cases):
    for name, doc in cases.items():
        for m in doc["measurements"]:
            v = measurement_verdict(m)
            if v == "fail":
                # honest failure must be registered as out-of-scope, never hidden
                oos = {mid for e in doc["scope"]["out_of_scope"]
                       for mid in e["measurement_ids"]}
                assert m["id"] in oos, f"{name}/{m['id']}: failure not declared out_of_scope"
            if m["acceptance"]["kind"] == "order_ge":
                assert v == "pass", f"{name}/{m['id']}: convergence order below floor"


def test_taylor_green_deviation_within_three_percent(cases):
    ma = {m["id"]: m for m in cases[CASE_FILES[0]]["measurements"]}
    for mid in ("tg_dev_nx32", "tg_dev_nx64", "tg_dev_nx128"):
        assert abs(ma[mid]["value"]) < TOL_PCT
    assert ma["tg_order_nx64"]["value"] >= ORDER_FLOOR
    assert ma["tg_order_nx128"]["value"] >= ORDER_FLOOR


def test_poiseuille_port_exact_and_ib_lbm_fail_is_visible(cases):
    ma = {m["id"]: m for m in cases[CASE_FILES[0]]["measurements"]}
    assert abs(ma["poiseuille_port_l2"]["value"]) <= MACHINE_EPS
    ib = ma["ib_lbm_centreline_err"]
    assert abs(ib["value"]) > TOL_PCT, "IB-LBM must stay flagged as out-of-tolerance"
    assert measurement_verdict(ib) == "fail"


def test_quoted_value_is_separated_from_reproduced(cases):
    mc = {m["id"]: m for m in cases[CASE_FILES[2]]["measurements"]}
    assert mc["tg_quoted_err"]["value"] != mc["tg_repro_nx128"]["value"], \
        "quoted and reproduced values must stay distinct"
    assert measurement_verdict(mc["tg_quoted_err"]) == "quoted"
    assert all(measurement_verdict(mc[k]) == "pass"
               for k in ("tg_repro_nx32", "tg_repro_nx64", "tg_repro_nx128"))
    gran = cases[CASE_FILES[2]]["granularity"]
    assert gran["cited_source"]["path"] == CLAIM
    assert [r["value_pct"] for r in gran["reproduced"]] == [
        mc["tg_repro_nx32"]["value"], mc["tg_repro_nx64"]["value"],
        mc["tg_repro_nx128"]["value"]]
    # tighter grids sit closer to the analytic decay law
    assert abs(gran["reproduced"][0]["value_pct"]) > abs(gran["reproduced"][2]["value_pct"])


def test_oss_lbm_claim_and_evidence_records_resolve(cases):
    claim_doc, evid_doc = load(CLAIM), load(EVID)
    ka = cases[CASE_FILES[0]]["knowledge"]
    assert ka["claim_id"] == claim_doc["id"] == TG_CLAIM
    assert ka["evidence_ids"] == claim_doc["evidence_refs"] == [evid_doc["id"]]
    assert evid_doc["claim_refs"] == [claim_doc["id"]]
    assert ka["source_locator"] == evid_doc["locator"]["value"]
    assert ka["domain"] == claim_doc["scope"]["domain"]
    kb = cases[CASE_FILES[1]]["knowledge"]
    assert kb["locator_type"] == evid_doc["locator"]["locator_type"]
    assert kb["evidence_assessment_status"] == evid_doc["assessment_status"]
    assert cases[CASE_FILES[1]]["liveness"]["external_source"]["resolvable_in_worktree"] is False


def test_ke_query_measurements_hold_on_real_package(cases, ke_store):
    conn, counts = ke_store
    assert counts["claims"] >= 100 and counts["evidence"] >= 100
    for m in cases[CASE_FILES[1]]["measurements"]:
        q = m["source"]["ke_query"]
        assert ke_count(conn, q["op"], q["claim_id"]) == m["value"], m["id"]


def test_provenance_chain_shape_from_ke_store(ke_store):
    from ke import queries

    conn, _ = ke_store
    chain = queries.provenance_chain(conn, TG_CLAIM)
    assert chain["claim"]["epistemic_status"] == "established"
    assert len(chain["links"]) == 1
    link = chain["links"][0]
    assert link["relation"] == "supports"
    assert link["locator"]["locator_type"] == "code-location"
    assert link["source"]["citation"] == "lbm-principles-practice source code"
    assert link["evidence_source_file"].startswith("evidence/")


def test_claim_is_retrievable_by_domain_and_status(ke_store):
    from ke import queries

    conn, _ = ke_store
    domain = load(CLAIM)["scope"]["domain"]
    assert TG_CLAIM in [h["id"] for h in queries.claims_by_domain(conn, domain)]
    assert TG_CLAIM in [c["id"] for c in queries.claims_by_status(conn, "established")]
    assert TG_CLAIM not in [c["id"] for c in queries.claims_by_status(conn, "contested")]


def test_retrieval_dimensions_are_filters_not_weights():
    """D1 domain / D2 ktype / D3 status are hard filters on the KB read path."""
    from ke import consume as C

    conn = C.connect("sqlite::memory:")
    C.ensure_schema(conn)
    rows = [
        ("card:lbm:tg", "claim", "oss-lbm", "Taylor-Green 涡衰减验证",
         "Taylor-Green decay 0.077%", "active"),
        ("card:lbm:poiseuille", "claim", "oss-lbm", "Poiseuille 剖面误差",
         "Poiseuille L2 1e-16", "active"),
        ("card:ops:gate", "ops", "controls", "推送门禁",
         "artifacts 目录被门禁滤除 Taylor-Green", "active"),
        ("card:lbm:old", "claim", "oss-lbm", "Taylor-Green 旧结论",
         "Taylor-Green refuted", "deprecated"),
    ]
    for kb_key, ktype, domain, title, content, status in rows:
        conn.execute("INSERT INTO knowledge_base (kb_key,ktype,domain,title,content,status) "
                     "VALUES (?,?,?,?,?,?)", (kb_key, ktype, domain, title, content, status))
    conn.commit()

    def keys(**kw):
        return [c["kb_key"] for c in C.retrieve(conn, "Taylor-Green", log=False, **kw)["cards"]]

    # D1 is a *supplied* filter, not an inferred one: an unfiltered read path can
    # surface cross-domain noise (ops card whose text mentions Taylor-Green).
    assert "card:ops:gate" in keys(), "unfiltered read path does mix domains"
    assert keys(domain="oss-lbm") == ["card:lbm:tg"]      # D1 supplied -> noise excluded
    assert keys(domain="oss-lbm", ktype="ops") == []      # D1 ∧ D2 intersection is empty
    assert "card:lbm:old" not in keys()                   # D3: refuted card leaves the surface
    assert keys(status="deprecated") == ["card:lbm:old"]
    assert keys(ktype="ops", domain="controls") == ["card:ops:gate"]   # D2
    conn.close()


def test_figures_exist_and_are_png(cases):
    fig_names = [f["file"] for doc in cases.values() for f in doc["figures"]]
    assert len(fig_names) == 3
    for name in fig_names:
        p = CASES / name
        assert p.is_file(), name
        assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", f"{name} is not a PNG"
        assert p.stat().st_size > 8000, f"{name} suspiciously small"


def test_summary_matches_case_files(cases):
    summary = json.loads((CASES / "summary.json").read_text())
    assert summary["schema"] == "tk-agent-cases-summary/1"
    assert summary["mission"] == 19445
    assert [c["file"] for c in summary["cases"]] == list(CASE_FILES)
    assert [c["measurements"] for c in summary["cases"]] == [
        len(cases[n]["measurements"]) for n in CASE_FILES]
    recomputed = {"pass": 0, "fail": 0, "quoted": 0, "match": 0}
    for name in CASE_FILES:
        for m in cases[name]["measurements"]:
            recomputed[measurement_verdict(m)] += 1
    assert summary["totals"] == recomputed
    assert summary["totals"]["fail"] == 1          # exactly the IB-LBM honest failure
    assert summary["exactness_classes"]["out_of_scope"] == ["ib_lbm_centreline_err"]
    assert summary["provenance_state"]["claim_level_records"] == 0
    assert len(summary["retrieval_dimensions"]) == 4
    for d in summary["retrieval_dimensions"]:
        assert d["id"] in {"D1", "D2", "D3", "D4"}


# ------------------------------------------------------------------------ main
if __name__ == "__main__":
    if "--regen" in sys.argv:
        paths = regen()
        for name, p in sorted(paths.items()):
            print(f"{name:32s} {p.stat().st_size:>8d} bytes")
    else:
        print(__doc__)
