"""KO Schema v1 一致性 benchmark：ref（规格）× got（实现）逐条对照。

产出 ``docs/rci/m15858/bench.json``（提交进仓，因为推送门禁滤 runs/ 与 artifacts/）。

判据（全部数值化，机器可复核）：
  C1 文档级一致性：got 的 accept/reject 与 ref 一致 → accuracy = 1.0（FP=FN=0）
  C2 状态机一致性：同上
  C3 证据可追溯率口径：|got − ref| ≤ 1e-4（ref 为闭式解析值）
  C4 吞吐（信息性，不设裁据）：validations/s

repro_cmd: python3 scripts/ko_v1.py bench
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import cases as C  # noqa: E402  (同目录语料)
from scripts import validate_ko_v1 as V  # noqa: E402

OUT = REPO / "docs" / "rci" / "m15858" / "bench.json"
REPRO = "python3 scripts/ko_v1.py bench"


def _doc_verdict(factory) -> dict:
    doc = factory()
    try:
        V.validate_document(doc)
    except V.KOError as exc:
        return {"accept": False, "errors": exc.errors}
    return {"accept": True, "errors": []}


def _trans_verdict(case_id: str, builder) -> dict:
    case = builder()
    new_doc = _resolve_target(case_id)
    try:
        V.check_transition(case["prev"], new_doc, actor_role=case["actor_role"])
    except V.KOError as exc:
        return {"accept": False, "errors": exc.errors}
    return {"accept": True, "errors": []}


def _resolve_target(case_id: str) -> dict:
    """按 case_id 取该 case 的目标文档（构造器返回值里只有 prev；目标态在闭包里）。"""
    if case_id == "trans.agent.report_claimed":
        return C.base_ko()
    if case_id == "trans.reopen_ok":
        return C.base_ko(verification_status="report_claimed")
    if case_id == "trans.back_to_unverified_refused":
        return C.base_ko(verification_status="unverified")
    if case_id == "trans.agent.to_l3_refused":
        return C._l3_doc()
    return C._l3_doc()


def run() -> dict:
    doc_rows, trans_rows = [], []
    for case_id, ref_accept, ref_err, rule, factory in C.DOC_CASES:
        got = _doc_verdict(factory)
        ok = got["accept"] == ref_accept and (
            ref_err is None or any(ref_err in e for e in got["errors"]))
        doc_rows.append({"case_id": case_id, "rule": rule, "ref_accept": ref_accept,
                         "got_accept": got["accept"], "expect_error_contains": ref_err,
                         "match": ok, "got_errors": got["errors"][:3]})
    for case_id, ref_accept, rule, builder in C.TRANS_CASES:
        got = _trans_verdict(case_id, builder)
        trans_rows.append({"case_id": case_id, "rule": rule, "ref_accept": ref_accept,
                           "got_accept": got["accept"], "match": got["accept"] == ref_accept,
                           "got_errors": got["errors"][:3]})

    etr_rows = []
    for case in C.etr_cases():
        resolved = [V.resolve_evidence(ev, reports=C.REPORTS, repo_roots=[REPO])
                    for ev in case["evidence"]]
        got = V.evidence_traceability(resolved)
        ref = case["ref"]
        etr_rows.append({
            "case_id": case["case_id"], "rule": case["rule"],
            "ref": ref,
            "got": {"e_tr": got["e_tr"], "r1": got["r1_report_resolvable"],
                    "r2": got["r2_section_resolvable"], "r3": got["r3_artifact_resolvable"]},
            "abs_err": {k: round(abs(got[gk] - ref[rk]), 6) for k, gk, rk in (
                ("e_tr", "e_tr", "e_tr"), ("r1", "r1_report_resolvable", "r1"),
                ("r2", "r2_section_resolvable", "r2"), ("r3", "r3_artifact_resolvable", "r3"))},
        })
    for row in etr_rows:
        row["match"] = max(row["abs_err"].values()) <= 1e-4

    # C4 吞吐（信息性）
    docs = [f() for _, _, _, _, f in C.DOC_CASES]
    t0 = time.perf_counter()
    for _ in range(50):
        for doc in docs:
            try:
                V.validate_document(doc)
            except V.KOError:
                continue
    elapsed = time.perf_counter() - t0
    throughput = round(50 * len(docs) / elapsed, 1)

    doc_acc = round(sum(r["match"] for r in doc_rows) / len(doc_rows), 4)
    trans_acc = round(sum(r["match"] for r in trans_rows) / len(trans_rows), 4)
    etr_ok = all(r["match"] for r in etr_rows)
    return {
        "benchmark_id": "ko_v1_conformance",
        "anchor": "KBM-RCI-S2-SCHEMA",
        "mission_id": 15858,
        "generated_by": "benchmarks/ko_v1_conformance/run_benchmark.py",
        "repro_cmd": REPRO,
        "spec_ref": "docs/rci/schema-v1.md + schemas/knowledge-object-v1.schema.json",
        "criteria": {
            "C1_doc_conformance_accuracy": {"ref": 1.0, "got": doc_acc, "limit": 1.0,
                                            "pass": doc_acc == 1.0},
            "C2_transition_accuracy": {"ref": 1.0, "got": trans_acc, "limit": 1.0,
                                       "pass": trans_acc == 1.0},
            "C3_etr_abs_error_max": {"ref": 0.0,
                                     "got": max(max(r["abs_err"].values()) for r in etr_rows),
                                     "limit": 1e-4, "pass": etr_ok},
            "C4_throughput_per_s": {"ref": None, "got": throughput, "limit": None, "pass": True},
        },
        "doc_cases": doc_rows,
        "transition_cases": trans_rows,
        "etr_cases": etr_rows,
        "verdict": "PASS" if (doc_acc == 1.0 and trans_acc == 1.0 and etr_ok) else "FAIL",
    }


def main() -> int:
    rep = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": rep["verdict"], "criteria": rep["criteria"],
                      "out": str(OUT.relative_to(REPO))}, ensure_ascii=False, indent=2))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())