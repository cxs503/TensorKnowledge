"""KPI-KB-VERIFY-RATE 计量器的回归测试（离线优先；PG 相关层缺库时 skip 而不是假通过）。

判据分层与 SKILL experimental-design 一致：
  * 语义层（恒可跑）：0/0 未定义、分子>分母拒绝、目标未定标不编造、指纹绑值；
  * 入口层（恒可跑）：CLI measure/verify 在夹具快照上端到端，退回码契约可判；
  * 真引擎层：Tier B（scratch 库真 SQL）与 Tier C（活库双路径）——**无 PG 时 skip**，
    报告里对应写 not_run，不允许把「没跑」当「通过」。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.kpi_kb_verify_rate import bench as B  # noqa: E402
from tools.kpi_kb_verify_rate import cli as CLI  # noqa: E402
from tools.kpi_kb_verify_rate import compute as C  # noqa: E402
from tools.kpi_kb_verify_rate import spec  # noqa: E402
from tools.kpi_kb_verify_rate.backend import (PsqlBackend, ReadOnlyViolation,  # noqa: E402
                                              validate_readonly)

PG_OK = PsqlBackend("postgres").available()


def fixture_snapshot(numerator: int = 3, denominator: int = 10) -> dict:
    raw = {
        "ko_total": denominator, "ko_enter_flow": denominator,
        "ko_enter_flow_events": denominator,
        "ko_l3_candidates": numerator, "ko_platform_verified": numerator,
        "num_l3_gate_confirmed": numerator,
        "verification_tickets": numerator, "verification_tickets_confirmed": numerator,
        "verification_ko_distinct": denominator, "num_confirmed_any_level": numerator,
        "evidence_total": denominator, "evidence_artifact_none": 0,
        "ko_with_artifact_evidence": denominator, "ko_with_verified_artifact": denominator,
        "ko_state_events": denominator * 2,
        "ko_by_status": {"report_claimed": denominator},
        "ko_by_level": {"L3": numerator, "L2": denominator - numerator},
        "evidence_kinds": {"artifact": denominator},
        "verdicts_total": 5, "verdicts_confirmed": 3, "verdicts_ko_scope": 1,
        "verdicts_knowledge_scope_confirmed": 1,
        "verdict_gate_states": {"confirmed": 3, "pending": 2},
        "benchmark_cases_for_anchor": 1,
        "feature_ledger_anchor": [["164", "KPI-KB-VERIFY-RATE", "open", "(empty)", "(null)"]],
        "ko_producer_profile": {"producers": 3, "domains": 4, "n": denominator,
                                "span_seconds": 86400, "first_at": "2026-01-01T00:00:00Z",
                                "last_at": "2026-01-02T00:00:00Z"},
    }
    snap = {
        "schema": "kpi-kb-verify-rate/snapshot@1",
        "spec_version": spec.SPEC_VERSION, "spec_sha256": spec.SPEC_SHA256,
        "collected_at_utc": "2026-01-01T00:00:00Z",
        "db_fingerprints": {"ke_service": {"database": "fixture", "readonly": True, "queries": 26}},
        "raw": raw, "sql": {k: v["sql"] for k, v in spec.QUERIES.items()}, "errors": {},
    }
    snap["snapshot_sha256"] = C.snapshot_fingerprint(snap)
    return snap


# ---------------------------------------------------------------- 语义层
@pytest.mark.parametrize("num,den,expected", [
    (0, 5338, 0.0), (3, 10, 0.3), (10, 10, 1.0), (1, 3, 1 / 3),
])
def test_verify_rate_arithmetic(num, den, expected):
    assert C.verify_rate(num, den) == pytest.approx(expected)


def test_zero_denominator_is_undefined_not_zero():
    assert C.verify_rate(0, 0) is None
    res = C.build_result(fixture_snapshot(0, 0))
    assert res["current"] is None and res["current_display"].startswith("未定义")


@pytest.mark.parametrize("num,den", [(4, 3), (-1, 5), (1, -5)])
def test_rejects_impossible_counts(num, den):
    with pytest.raises(C.SemanticsError):
        C.verify_rate(num, den)


def test_target_never_fabricated_and_gap_not_zeroed():
    res = C.build_result(fixture_snapshot())
    assert res["target"] is None
    assert res["target_status"] == "NOT_CALIBRATED"
    assert res["gap"] is None and "未定标" in res["gap_reason"]


def test_result_contract_keys_present():
    res = C.build_result(fixture_snapshot())
    for key in ("current", "unit", "target", "gap", "data_sources", "top_gaps",
                "proposed_anchors", "numerator", "denominator", "repro_cmd",
                "snapshot_sha256", "spec_sha256"):
        assert key in res, key
    assert isinstance(res["data_sources"], list) and len(res["data_sources"]) == len(spec.QUERIES)
    assert all("sql" in d and d["db"] in ("ke_service", "tensorplatform")
               for d in res["data_sources"])
    # 每条 data_source 都必须是可复算的只读 SQL
    for d in res["data_sources"]:
        validate_readonly(d["sql"])


def test_sensitivity_covers_undefined_case():
    sens = C.sensitivity({"ko_total": 0, "ko_enter_flow": 0, "num_l3_gate_confirmed": 0,
                          "verification_ko_distinct": 0})
    ticket = [s for s in sens if s["scope"].startswith("TICKET-ONLY")][0]
    assert ticket["current"] is None and "未定义" in ticket["current_display"]


def test_0_percent_wilson_upper_bound_positive():
    ci = C.wilson_interval(0, 5338)
    assert ci["low"] == 0.0 and 0 < ci["high"] < 0.001


def test_snapshot_fingerprint_ignores_clock_but_pins_values():
    a = fixture_snapshot()
    b = dict(a, collected_at_utc="2027-01-01T00:00:00Z")
    assert C.snapshot_fingerprint(a) == C.snapshot_fingerprint(b)
    c = fixture_snapshot(numerator=4, denominator=10)
    assert C.snapshot_fingerprint(a) != C.snapshot_fingerprint(c)


def test_spec_mismatch_snapshot_rejected():
    snap = fixture_snapshot()
    snap["spec_sha256"] = "0" * 64
    with pytest.raises(C.SemanticsError):
        C.build_result(snap)


def test_gaps_are_derived_from_numbers_not_hardcoded():
    empty = fixture_snapshot(0, 0)
    empty["raw"].update({"verification_tickets": 0, "ko_total": 0, "ko_enter_flow": 0,
                         "ko_l3_candidates": 0, "benchmark_cases_for_anchor": 0,
                         "verdicts_ko_scope": 0, "ko_producer_profile": {}})
    ids = {g["id"] for g in C.build_result(empty)["top_gaps"]}
    assert "GAP-KO-VERIFY-TICKET-ZERO" in ids
    healthy = C.build_result(fixture_snapshot())
    assert "GAP-KO-VERIFY-TICKET-ZERO" not in {g["id"] for g in healthy["top_gaps"]}


# ---------------------------------------------------------------- 只读护栏
@pytest.mark.parametrize("sql", ["UPDATE ko_compiler_v1.ko_object SET storage_level='L3'",
                                 "DELETE FROM ko_compiler_v1.ko_verification",
                                 "SELECT 1; DROP TABLE ko_compiler_v1.ko_object"])
def test_readonly_guard_rejects_writes(sql):
    with pytest.raises(ReadOnlyViolation):
        validate_readonly(sql)


def test_all_spec_queries_are_readonly():
    for q in spec.QUERIES.values():
        validate_readonly(q["sql"])


# ---------------------------------------------------------------- 入口层（CLI）
def test_cli_measure_and_verify_roundtrip(tmp_path):
    snap = fixture_snapshot()
    sp = tmp_path / "snapshot.json"
    sp.write_text(json.dumps(snap), encoding="utf-8")
    assert CLI.main(["measure", "--snapshot", str(sp), "--out", str(tmp_path)]) == 0
    res = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert res["current"] == pytest.approx(0.3)
    assert CLI.main(["verify", "--snapshot", str(sp), "--no-oracle"]) == 0


def test_cli_rejects_tampered_snapshot(tmp_path):
    snap = fixture_snapshot()
    snap["raw"]["num_l3_gate_confirmed"] = 7  # 改值但保留旧指纹
    sp = tmp_path / "snapshot.json"
    sp.write_text(json.dumps(snap), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        CLI.main(["measure", "--snapshot", str(sp), "--out", str(tmp_path)])
    assert exc.value.code == 2


def test_cli_selftest_passes(capsys):
    assert CLI.main(["selftest"]) == 0
    assert json.loads(capsys.readouterr().out)["n_fail"] == 0


# ---------------------------------------------------------------- 基准层
def test_bench_tier_a_matches_hand_derived_expectations():
    cases = json.loads((REPO / "benchmarks/kpi_kb_verify_rate/cases.json")
                       .read_text(encoding="utf-8"))["cases"]
    rows = B.tier_a(cases)
    assert rows and all(r["pass"] for r in rows)
    assert [r["cases"] if "cases" in r else r["case"] for r in rows]
    by_case = {r["case"]: r for r in rows}
    assert by_case["mixed-10ko"]["got"]["current"] == pytest.approx(0.125)
    assert by_case["two-of-three"]["got"]["current"] == pytest.approx(2 / 3)
    assert by_case["empty-db"]["got"]["current"] is None


@pytest.mark.skipif(not PG_OK, reason="PG/psql 不可达：Tier B 未运行（not_run != pass）")
def test_bench_tier_b_real_sql_on_scratch_db():
    cases = json.loads((REPO / "benchmarks/kpi_kb_verify_rate/cases.json")
                       .read_text(encoding="utf-8"))["cases"]
    rep = B.tier_b(cases)
    assert rep["status"] == "run"
    failures = [r for r in rep["cases"] if not r["pass"]]
    assert not failures, failures


@pytest.mark.skipif(not PG_OK, reason="PG/psql 不可达：Tier C 未运行（not_run != pass）")
def test_bench_tier_c_live_dual_path():
    live = REPO / "runs/kpi_kb_verify_rate/snapshot.json"
    if not live.exists():
        pytest.skip("无活库快照 runs/kpi_kb_verify_rate/snapshot.json：Tier C 未运行")
    rep = B.tier_c(json.loads(live.read_text(encoding="utf-8")))
    if rep["status"] != "run":
        pytest.skip(rep.get("reason", "oracle 不可用"))
    assert rep["pass"], rep
    assert rep["abs_error_numerator"] == 0 and rep["abs_error_denominator"] == 0


def test_repro_cmd_paths_exist():
    res = C.build_result(fixture_snapshot())
    assert any("collect" in c for c in res["repro_cmd"])
    assert (REPO / "benchmarks/kpi_kb_verify_rate/cases.json").exists()
    assert (REPO / "tools/kpi_kb_verify_rate/__main__.py").exists()