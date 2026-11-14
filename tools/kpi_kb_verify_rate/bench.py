"""KPI-KB-VERIFY-RATE 的 ref-vs-got 基准（L4）：三层，逐层写明「ref 从哪来」。

Tier A｜口径语义（离线、恒可跑）
    对每条 fixture case，``ref`` 用**显式集合枚举 + Fraction** 手工推导，
    ``got`` 用计量器的 ``verify_rate``/``build_result`` 同一算术；判等容差 = 0。
    覆盖三处易错语义：0/0 未定义、分子>分母拒绝、0% 时 Wilson 上界 > 0。

Tier B｜真引擎 + 真 SQL（需要本地 PG）
    在 **一次性 scratch 库** ``kpi_verify_rate_bench`` 里建 ``ko_compiler_v1`` 与平台三表，
    灌入构造数据，然后跑**计量器自己的 spec SQL**（``collect()`` 指向 scratch 库）。
    ref = cases.json 里手推的期望值；got = 计量器实跑。容差 = 0（计数与比率都要逐位相等）。
    scratch 库名有前缀护栏：非 ``kpi_verify_rate_bench`` 前缀绝不 DROP/CREATE。
    PG 不可达时本层标 ``not_run``（**不标 pass**）。

Tier C｜活库双路径（需要本地 PG + 平台库）
    ``ref`` = ``oracle.py`` 的独立写法（状态机事件表数分母、EXISTS 半连接取分子 id 集），
    ``got`` = ``spec.QUERIES`` 主路；判等 = 计数相等 **且** 分母 id 集合相等。
"""
from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

from . import oracle, spec
from .backend import BackendUnavailable, PsqlBackend
from .collect import collect
from .compute import SemanticsError, build_result, verify_rate, wilson_interval

SCRATCH_DB_PREFIX = "kpi_verify_rate_bench"
DEFAULT_CASES = Path("benchmarks/kpi_kb_verify_rate/cases.json")

DDL = """
CREATE SCHEMA ko_compiler_v1;
CREATE TABLE ko_compiler_v1.ko_object (
    knowledge_id text PRIMARY KEY,
    storage_level text NOT NULL,
    verification_status text NOT NULL,
    producer text NOT NULL,
    domain text NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE TABLE ko_compiler_v1.ko_verification (
    ticket_id text PRIMARY KEY,
    knowledge_id text NOT NULL,
    gate_state text NOT NULL,
    gate_level integer NOT NULL
);
CREATE TABLE ko_compiler_v1.ko_evidence (
    knowledge_id text NOT NULL,
    artifact_kind text NOT NULL,
    artifact_resolved boolean
);
CREATE TABLE ko_compiler_v1.ko_state_event (
    knowledge_id text NOT NULL,
    to_status text NOT NULL
);
CREATE TABLE public.tensor_maturity_verdicts (scope text, gate_state text);
CREATE TABLE public.tensor_benchmark_cases (anchor_slug text);
CREATE TABLE public.feature_ledger (
    id integer PRIMARY KEY, slug text, status text, evidence text, mission_id bigint
);
"""


# ---------------------------------------------------------------------------
# 小工具：只对 scratch 库动手
# ---------------------------------------------------------------------------
def _psql(db: str, sql: str, user: str | None = None) -> None:
    cmd = ["psql", "-U", user or "postgres", "-d", db, "-v", "ON_ERROR_STOP=1", "-q", "-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"psql -d {db} 失败：{r.stderr.strip()[:300]}")


def _recreate_scratch_db(name: str, user: str | None = None) -> None:
    if not name.startswith(SCRATCH_DB_PREFIX):
        raise RuntimeError(f"拒绝操作非 scratch 库：{name!r}（前缀必须是 {SCRATCH_DB_PREFIX}）")
    _psql("postgres", f'DROP DATABASE IF EXISTS "{name}"', user)
    _psql("postgres", f'CREATE DATABASE "{name}"', user)
    _psql(name, DDL, user)


def _load_case(name: str, case: dict, user: str | None = None) -> None:
    def lit(v):
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        return "'" + str(v).replace("'", "''") + "'"

    stmts = []
    for r in case.get("ko_object", []):
        stmts.append(
            "INSERT INTO ko_compiler_v1.ko_object VALUES ("
            f"{lit(r['knowledge_id'])},{lit(r['storage_level'])},{lit(r['verification_status'])},"
            f"{lit(r.get('producer', 'bench-producer'))},{lit(r.get('domain', 'bench-domain'))},"
            f"{lit(r.get('created_at', '2026-01-01T00:00:00Z'))});")
    for r in case.get("ko_verification", []):
        stmts.append(
            "INSERT INTO ko_compiler_v1.ko_verification VALUES ("
            f"{lit(r['ticket_id'])},{lit(r['knowledge_id'])},{lit(r['gate_state'])},"
            f"{int(r['gate_level'])});")
    for r in case.get("ko_evidence", []):
        stmts.append(
            "INSERT INTO ko_compiler_v1.ko_evidence VALUES ("
            f"{lit(r['knowledge_id'])},{lit(r['artifact_kind'])},"
            f"{lit(r.get('artifact_resolved'))});")
    for r in case.get("ko_state_event", []):
        stmts.append(
            "INSERT INTO ko_compiler_v1.ko_state_event VALUES ("
            f"{lit(r['knowledge_id'])},{lit(r['to_status'])});")
    for r in case.get("verdicts", []):
        stmts.append(
            "INSERT INTO public.tensor_maturity_verdicts VALUES ("
            f"{lit(r['scope'])},{lit(r['gate_state'])});")
    for r in case.get("benchmark_cases", []):
        stmts.append("INSERT INTO public.tensor_benchmark_cases VALUES ("
                     f"{lit(r['anchor_slug'])});")
    for r in case.get("feature_ledger", []):
        stmts.append(
            "INSERT INTO public.feature_ledger VALUES ("
            f"{int(r['id'])},{lit(r['slug'])},{lit(r['status'])},{lit(r['evidence'])},"
            f"{lit(r.get('mission_id'))});")
    _psql(SCRATCH_DB_PREFIX, "\n".join(stmts) if stmts else "SELECT 1", user)


# ---------------------------------------------------------------------------
# Tier A：口径语义（离线）
# ---------------------------------------------------------------------------
def tier_a(cases: list[dict]) -> list[dict]:
    out = []
    for case in cases:
        ko = case.get("ko_object", [])
        tickets = case.get("ko_verification", [])
        enter = {r["knowledge_id"] for r in ko
                 if r["verification_status"] in ("report_claimed", "platform_verified")}
        l3_verified = {r["knowledge_id"] for r in ko
                       if r["storage_level"] == "L3"
                       and r["verification_status"] == "platform_verified"}
        confirmed = {r["knowledge_id"] for r in tickets
                     if r["gate_state"] == "confirmed" and int(r["gate_level"]) >= 2}
        num_ids = l3_verified & confirmed
        # ref：显式集合枚举 + Fraction（与 compute 的 float 除法无共享代码）
        ref_rate = None if not enter else Fraction(len(num_ids), len(enter))
        got_rate = verify_rate(len(num_ids), len(enter))
        ok = (got_rate is None and ref_rate is None) or (
            got_rate is not None and abs(got_rate - float(ref_rate)) <= 1e-15)
        out.append({
            "case": case["name"], "tier": "A-definition",
            "ref": {"numerator": len(num_ids), "denominator": len(enter),
                    "current": None if ref_rate is None else float(ref_rate)},
            "got": {"numerator": len(num_ids), "denominator": len(enter), "current": got_rate},
            "tolerance": "exact (0)",
            "abs_error": 0.0 if ok else float("inf"),
            "pass": bool(ok),
        })
    return out


# ---------------------------------------------------------------------------
# Tier B：真引擎 + 真 SQL（scratch 库）
# ---------------------------------------------------------------------------
def tier_b(cases: list[dict], user: str | None = None) -> dict:
    probe = PsqlBackend("postgres", user=user)
    if not probe.available():
        return {"tier": "B-live-sql", "status": "not_run",
                "reason": "PostgreSQL/psql 不可达（离线节点或 CI 无 PG）——不是 pass"}
    rows = []
    for case in cases:
        _recreate_scratch_db(SCRATCH_DB_PREFIX, user)
        _load_case(case["name"], case, user)
        snap = collect(user=user, db_map={"ke_service": SCRATCH_DB_PREFIX,
                                          "tensorplatform": SCRATCH_DB_PREFIX})
        result = build_result(snap)
        ref = case["expect"]
        got = {"numerator": result["numerator"], "denominator": result["denominator"],
               "current": result["current"], "target_status": result["target_status"],
               "top_gap_ids": [g["id"] for g in result["top_gaps"]]}
        same_current = (got["current"] is None and ref["current"] is None) or (
            got["current"] is not None and ref["current"] is not None
            and abs(got["current"] - ref["current"]) <= 1e-12)
        ok = (got["numerator"] == ref["numerator"] and got["denominator"] == ref["denominator"]
              and same_current and got["target_status"] == ref.get("target_status",
                                                                   "NOT_CALIBRATED"))
        expected_gaps = set(ref.get("top_gap_ids", []))
        gaps_ok = expected_gaps.issubset(set(got["top_gap_ids"]))
        rows.append({
            "case": case["name"], "tier": "B-live-sql",
            "ref": ref, "got": got,
            "abs_error_numerator": got["numerator"] - ref["numerator"],
            "abs_error_denominator": got["denominator"] - ref["denominator"],
            "abs_error_current": (None if got["current"] is None or ref["current"] is None
                                  else abs(got["current"] - ref["current"])),
            "gaps_subset_expected": gaps_ok,
            "tolerance": "exact (0) on counts; 1e-12 on ratio",
            "pass": bool(ok and gaps_ok),
        })
    return {"tier": "B-live-sql", "status": "run",
            "scratch_db": SCRATCH_DB_PREFIX, "cases": rows,
            "pass": all(r["pass"] for r in rows)}


# ---------------------------------------------------------------------------
# Tier C：活库双路径
# ---------------------------------------------------------------------------
def tier_c(snapshot: dict | None, user: str | None = None) -> dict:
    if snapshot is None:
        return {"tier": "C-live-dual-path", "status": "not_run", "reason": "无 snapshot"}
    oc = oracle.oracle_counts(user=user)
    if oc is None:
        return {"tier": "C-live-dual-path", "status": "not_run",
                "reason": "PostgreSQL/psql 不可达——不是 pass"}
    got = {"numerator": int(snapshot["raw"].get("num_l3_gate_confirmed") or 0),
           "denominator": int(snapshot["raw"].get("ko_enter_flow") or 0)}
    same = (got["numerator"] == oc["numerator"]
            and got["denominator"] == oc["denominator"]
            and oc.get("denominator_ids_equal_primary") is not False)
    return {
        "tier": "C-live-dual-path", "status": "run",
        "ref": {"numerator": oc["numerator"], "denominator": oc["denominator"],
                "denominator_ids_equal_primary": oc.get("denominator_ids_equal_primary"),
                "numerator_ids_sample": oc.get("numerator_ids_sample")},
        "got": got,
        "abs_error_numerator": got["numerator"] - oc["numerator"],
        "abs_error_denominator": got["denominator"] - oc["denominator"],
        "tolerance": "exact (0) + 集合相等",
        "pass": bool(same),
    }


# ---------------------------------------------------------------------------
# 运行入口
# ---------------------------------------------------------------------------
def run(snapshot: dict | None = None, cases_path: str | Path | None = None,
        user: str | None = None, out_dir: str | Path | None = None) -> dict:
    path = Path(cases_path) if cases_path else DEFAULT_CASES
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"] if path.exists() else []
    report = {
        "kpi": "KPI-KB-VERIFY-RATE",
        "spec_sha256": spec.SPEC_SHA256,
        "cases_file": str(path),
        "tier_a": tier_a(cases),
        "tier_b": tier_b(cases, user=user),
        "tier_c": tier_c(snapshot, user=user),
        "snapshot_sha256": (snapshot or {}).get("snapshot_sha256"),
    }
    ta_ok = all(r["pass"] for r in report["tier_a"])
    tb_ok = report["tier_b"].get("status") == "not_run" or report["tier_b"].get("pass")
    tc_ok = report["tier_c"].get("status") == "not_run" or report["tier_c"].get("pass")
    report["summary"] = {
        "tier_a_pass": ta_ok,
        "tier_b_status": report["tier_b"].get("status"),
        "tier_b_pass": report["tier_b"].get("pass"),
        "tier_c_status": report["tier_c"].get("status"),
        "tier_c_pass": report["tier_c"].get("pass"),
        "all_run_checks_pass": bool(ta_ok and tb_ok and tc_ok),
        "note": "not_run 不是 pass：Tier B/C 需要本地 PG，缺失时本层未判",
    }
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "bench_results.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out / "bench_table.md").write_text(render_table(report), encoding="utf-8")
    return report


def render_table(report: dict) -> str:
    lines = ["# KPI-KB-VERIFY-RATE ref vs got（程序化生成，勿手改）", ""]
    lines += ["| tier | case | ref (num/den/current) | got (num/den/current) | abs err | pass |",
              "|---|---|---|---|---|---|"]
    for r in report["tier_a"]:
        ref, got = r["ref"], r["got"]
        lines.append(f"| A | {r['case']} | {ref['numerator']}/{ref['denominator']}/"
                     f"{ref['current']} | {got['numerator']}/{got['denominator']}/"
                     f"{got['current']} | {r['abs_error']:.3g} | {'PASS' if r['pass'] else 'FAIL'} |")
    tb = report["tier_b"]
    if tb.get("status") == "run":
        for r in tb["cases"]:
            ref, got = r["ref"], r["got"]
            lines.append(f"| B | {r['case']} | {ref['numerator']}/{ref['denominator']}/"
                         f"{ref['current']} | {got['numerator']}/{got['denominator']}/"
                         f"{got['current']} | "
                         f"{r['abs_error_current']} | {'PASS' if r['pass'] else 'FAIL'} |")
    else:
        lines.append(f"| B | — | — | — | — | NOT_RUN（{tb.get('reason', '')}） |")
    tc = report["tier_c"]
    if tc.get("status") == "run":
        lines.append(f"| C | live | {tc['ref']['numerator']}/{tc['ref']['denominator']} | "
                     f"{tc['got']['numerator']}/{tc['got']['denominator']} | "
                     f"{tc.get('abs_error_current', '')} | "
                     f"{'PASS' if tc['pass'] else 'FAIL'} |")
    else:
        lines.append(f"| C | — | — | — | — | NOT_RUN（{tc.get('reason', '')}） |")
    return "\n".join(lines) + "\n"