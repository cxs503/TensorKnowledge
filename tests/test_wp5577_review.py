#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-5577-04 审核脚本的回归测试（含负对照）。

覆盖：引文逐字守门（含篡改负对照）、源哈希守门、上游 locator 回解（含平移负对照）、
判定阶梯、信封 schema、复算闭合与"不标 verified"纪律。
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import wp5577_review as R          # noqa: E402
import wp5577_review_data as D     # noqa: E402

MD = open(os.path.join(R.SRC_DIR, "report_5577.md"), encoding="utf-8").read()
REC = json.load(open(os.path.join(R.SRC_DIR, "report_5577_record.json"), encoding="utf-8"))
UP = json.load(open(os.path.join(R.SRC_DIR, "upstream_report_14783_wp-5577-01.json"), encoding="utf-8"))
MAN = R.extract_single_json_block(UP["markdown"])["outputs"]["asset_manifest.json"]


@pytest.fixture(scope="module")
def review():
    rev, env = R.build_review(MD, REC, UP)
    return rev, env


# ---------------------------------------------------------------- 源/引文守门
def test_source_hash_matches_contract():
    assert R.sha256_text(MD) == R.CONTRACT_HASH
    assert len(MD) == R.EXPECTED_CHARS


def test_all_quotes_are_verbatim_substrings():
    missing = [k for k, q in D.QUOTES.items() if q not in MD]
    assert missing == []


def test_negative_control_tampered_quote_is_detected(monkeypatch):
    """负对照：把一条引文改一个字符，守门必须 SystemExit。"""
    bad = dict(D.QUOTES)
    bad["q_geom_row"] = bad["q_geom_row"].replace("0.0617", "0.0618")
    monkeypatch.setattr(D, "QUOTES", bad, raising=True)
    with pytest.raises(SystemExit):
        R.assert_quotes(MD)


def test_negative_control_empty_quote_rejected(monkeypatch):
    bad = dict(D.QUOTES)
    bad["q_figures"] = "本报告不存在的字符串"
    monkeypatch.setattr(D, "QUOTES", bad, raising=True)
    with pytest.raises(SystemExit):
        R.assert_quotes(MD)


# ---------------------------------------------------------------- 上游 locator 回解
def test_upstream_locators_all_resolve():
    n_loc, n_md, n_rec, n_bad = R.resolve_locators(MD, MAN["assets"])
    assert (n_loc, n_md, n_rec) == (26, 17, 9)
    assert n_bad == 0


def test_negative_control_shifted_locator_is_detected():
    """负对照：把某条 markdown locator 的 char_start 平移 1，回解必须记账为 bad。"""
    assets = copy.deepcopy(MAN["assets"])
    for a in assets:
        for loc in a["locators"]:
            if loc["source_field"] == "markdown":
                loc["char_start"] = int(loc["char_start"]) + 1
                break
        else:
            continue
        break
    _, _, _, n_bad = R.resolve_locators(MD, assets)
    assert n_bad == 1


def test_negative_control_tampered_quote_in_locator_is_detected():
    assets = copy.deepcopy(MAN["assets"])
    for a in assets:
        for loc in a["locators"]:
            if loc["source_field"] == "markdown":
                loc["quote"] = loc["quote"][:-1]          # 少一个字，char 区间不变
                break
        else:
            continue
        break
    _, _, _, n_bad = R.resolve_locators(MD, assets)
    assert n_bad == 1


def test_upstream_envelope_structure_and_hash():
    env = R.extract_single_json_block(UP["markdown"])
    assert env["package_id"] == "wp-5577-01"
    assert env["provenance"]["source_hash"] == R.CONTRACT_HASH
    assert env["claims"] == []                            # 01 契约：不抽 claim
    assert len(env["outputs"]["asset_manifest.json"]["assets"]) == 21


# ---------------------------------------------------------------- 判定阶梯
def test_verdict_ladder():
    assert R.decide_verdict([{"severity": "medium", "blocking": True}]) == "fail"
    assert R.decide_verdict([{"severity": "low", "blocking": True}]) == "fail"
    assert R.decide_verdict([{"severity": "medium", "blocking": False}]) == "needs-fix"
    assert R.decide_verdict([{"severity": "low", "blocking": False},
                             {"severity": "info", "blocking": False}]) == "pass"
    assert R.decide_verdict([]) == "pass"


# ---------------------------------------------------------------- 复算闭合
def test_numeric_closure_at_declared_precision(review):
    rev, _ = review
    mx = rev["numeric_recomputation"]["max_abs_dev"]
    assert mx["Fn_dev_pct"] < 0.05          # Fn 由 V/Lpp 闭式复算
    assert mx["Cf_dev_pct"] < 0.5           # Cf 为 ITTC-57 闭式，表列 5 位小数舍入
    assert mx["RT_dev_kN"] <= 0.1           # RT = Rf + Rw 逐行成立
    assert mx["Ct_dev_pct"] < 0.5


def test_rw_closure_flags_only_12kn_row(review):
    """12 kn 行的 Rw 偏差来自 Cr 的 5 位小数舍入（F5），其余 4 行必须闭合。"""
    rev, _ = review
    rows = rev["numeric_recomputation"]["rows"]
    assert abs(rows[0]["Rw_dev_pct"]) > 20
    assert max(abs(r["Rw_dev_pct"]) for r in rows[1:]) < 3


def test_geometry_and_cwp_regressions(review):
    rev, _ = review
    g = rev["numeric_recomputation"]["geometry"]
    assert g["Cb_dev_pct"] == pytest.approx(0.0617, abs=5e-4)
    assert g["Cwp_default_old_KCS"] == pytest.approx(0.913, abs=1e-3)
    assert g["Cwp_default_new_KCS"] == pytest.approx(0.767, abs=1e-3)
    assert g["Cwp_default_new_KVLCC2"] == pytest.approx(0.873, abs=1e-3)


def test_deviation_arithmetic(review):
    rev, _ = review
    d = rev["numeric_recomputation"]["deviations"]
    assert d["V2_dev_pct_recomputed"] == pytest.approx(0.280, abs=0.001)
    assert d["V3_dev_pct_recomputed"] == pytest.approx(243.102, abs=0.01)
    assert d["V4_dev_pct_recomputed"] == pytest.approx(-17.262, abs=0.01)
    assert d["tbl2_row3_dev_vs_base"] == pytest.approx(268.96, abs=0.01)
    assert d["deployed_over_mock_Cr_ratio"] > 1.05     # 两个"修复前"数字不同源（F3）


# ---------------------------------------------------------------- 结论纪律
def _walk(obj):
    yield obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def test_no_claim_marked_verified(review):
    """纪律：审核方不得把任何 claim 标成 verified（verification 由平台门计算）。"""
    rev, env = review
    assert rev["verified_marking"]["claims_marked_verified"] == 0
    statuses = {c["status"] for c in rev["claim_judgements"]}
    assert statuses <= {"supported", "partially-supported", "unresolved", "refuted"}
    for node in _walk(rev):
        if isinstance(node, dict):
            assert not (node.get("verified") is True), "不得出现 verified=true 标记"
            if "status" in node:
                assert node["status"] != "verified"


def test_claim_evidence_quotes_are_grounded(review):
    rev, _ = review
    for c in rev["claim_judgements"]:
        for key in c["evidence"]:
            assert key in D.QUOTES, key
            assert D.QUOTES[key] in MD


def test_findings_ids_unique_and_severities_known(review):
    rev, _ = review
    ids = [f["finding_id"] for f in rev["findings"]]
    assert len(ids) == len(set(ids))
    assert {f["severity"] for f in rev["findings"]} <= {"blocking", "medium", "low", "info"}
    assert rev["verdict"] == R.decide_verdict(rev["findings"])


def test_acceptance_flags(review):
    rev, env = review
    acc = rev["acceptance_selfcheck"]
    assert acc["valid_json"] is True
    assert acc["reviewer_independent"] is True
    assert acc["upstream_packages_completed"] is True


def test_envelope_passes_schema(review):
    import jsonschema
    _, env = review
    schema = json.load(open(R.SCHEMA_PATH, encoding="utf-8"))
    env = copy.deepcopy(env)
    env["provenance"]["emitted_at"] = env["provenance"]["emitted_at"] or "2026-11-12T00:00:00+00:00"
    jsonschema.validate(env, schema)
    assert env["package_id"] == "wp-5577-04"
    assert env["task_type"] == "04-independent-review"
    assert env["report_id"] == "5577"
    assert "review_report.json" in env["outputs"]


def test_negative_control_envelope_with_bad_hash_fails_schema(review):
    import jsonschema
    _, env = review
    schema = json.load(open(R.SCHEMA_PATH, encoding="utf-8"))
    bad = copy.deepcopy(env)
    bad["provenance"]["source_hash"] = "sha256:deadbeef"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_checked_source_snapshot_hash_file():
    p = os.path.join(R.SRC_DIR, "report_5577.md.sha256")
    assert open(p, encoding="utf-8").read().strip() == hashlib.sha256(MD.encode("utf-8")).hexdigest()