#!/usr/bin/env python3
"""m15858 证据生产者：一次跑齐 L2/L3/L4 的可核工件（零手抄，全部落到 docs/rci/m15858/）。

产出的工件（推送门禁滤 runs/ 与 artifacts/，故一律落 docs/）：
  bench.json           一致性 benchmark（ref vs got）
  ingest_run.json      真 PostgreSQL 入库（schema=ko_v1）＋票据晋级 L3 全链
  etr_live.json        库内三闸事实复算 E-TR
  ke_api_live_call.json  KE 服务 ASGI 层真调用（POST /ko/v1/ingest → GET traceability）
  gate_selfcheck.json  按达标判断方案六键复核自检（镜像 maturity_gate.judge）
  pytest_junit.xml     pytest 全量（另由 shell 生成）

同时刷新 docs/rci/m15858-evidence.json（审计可直接引用，路径=仓库相对）。
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks" / "ko_v1_conformance"))

import cases as C  # noqa: E402
from ke import ko_ingest as KI  # noqa: E402
from scripts import ko_v1 as CLI  # noqa: E402
from scripts import validate_ko_v1 as V  # noqa: E402

OUT = REPO / "docs" / "rci" / "m15858"


def _dump(name: str, obj) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p.relative_to(REPO))


def hashed_doc(**over) -> dict:
    doc = C.base_ko(**over)
    doc["provenance"]["content_sha256"] = V.content_sha256(doc)
    return doc


def db_run() -> dict:
    schema = "ko_v1"
    conn = KI.connect()
    KI.ensure_schema(conn, schema)
    sfx = uuid.uuid4().hex[:6]
    doc = hashed_doc(knowledge_id=f"ko:tensorkbm:lbm-d2q9-strouhal-{sfx}",
                     subject=f"LBM D2Q9 圆柱绕流 ({sfx})")
    rep = KI.ingest(conn, doc, schema=schema, reports=C.REPORTS, repo_roots=[REPO],
                    on_conflict="skip")
    kid = doc["knowledge_id"]
    etr_before = KI.traceability(conn, kid, schema=schema)
    # 三闸未全绿的对照组：证明 L3 不是"写了就升"
    blocked = None
    try:
        KI.add_ticket(conn, kid, f"mv:15858:{kid}:l1", schema=schema, gate_level=1)
    except Exception as exc:
        blocked = f"{type(exc).__name__}: {str(exc).strip()[:160]}"
    tk = f"mv:15858:{kid.split(':')[-1]}"
    KI.add_ticket(conn, kid, tk, schema=schema, gate_level=3,
                  maturity_verdict_id=286, mission_id=15858)
    try:
        promo = KI.promote(conn, kid, schema=schema)
    except Exception as exc:
        promo = {"error": f"{type(exc).__name__}: {str(exc).strip()[:200]}"}
    etr_after = KI.traceability(conn, kid, schema=schema)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
        cur.execute("SELECT count(*) FROM ko_object")
        n_obj = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM ko_evidence")
        n_ev = cur.fetchone()[0]
        cur.execute("SELECT from_status, to_status, actor_role, ticket_id FROM ko_state_event "
                    "ORDER BY event_id")
        events = [{"from": r[0], "to": r[1], "actor_role": r[2], "ticket_id": r[3]} for r in cur.fetchall()]
    conn.close()
    return {"schema": schema, "dsn": os.environ.get("KO_DSN") or "dbname=tensorknowledge",
            "ingest": rep, "promote": promo,
            "gate_level_1_ticket_rejected": blocked,
            "etr_before_promotion": etr_before, "etr_after_promotion": etr_after,
            "ko_object_rows": n_obj, "ko_evidence_rows": n_ev,
            "state_events": events}


def api_run() -> dict:
    """ASGI 层真调用：走 FastAPI 路由 → ke.ko_ingest → PostgreSQL。逐调用记 status+body。"""
    import uuid as _u
    os.environ.setdefault("KE_API_TOKEN", "ev-" + _u.uuid4().hex[:8])
    os.environ.setdefault("KO_DSN", os.environ.get("KO_DSN") or "dbname=tensorknowledge")
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from ke.api import app  # noqa: PLC0415
    import ke.api as _apimod  # noqa: PLC0415

    client = TestClient(app, raise_server_exceptions=False)
    sfx = _u.uuid4().hex[:6]
    doc = hashed_doc(knowledge_id=f"ko:tensorkbm:ke-api-{sfx}", subject=f"KE API probe {sfx}")
    h = {"Authorization": "Bearer " + os.environ["KE_API_TOKEN"]}

    def call(method: str, url: str, tag: str, **kw) -> dict:
        try:
            r = client.request(method, url, **kw)
            return {"call": f"{method} {url}", "tag": tag, "status": r.status_code,
                    "body": (r.text or "")[:600]}
        except Exception as exc:  # 端点异常如实记录
            return {"call": f"{method} {url}", "tag": tag, "status": 599,
                    "body": f"{type(exc).__name__}: {exc}"}

    kid = doc["knowledge_id"]
    rows = [
        call("POST", "/ko/v1/ingest", "ingest", json={"doc": doc, "reports": C.REPORTS}, headers=h),
        call("GET", f"/ko/v1/{kid}/traceability", "traceability"),
        call("POST", f"/ko/v1/{kid}/promote", "promote",
             json={"ticket_id": f"mv:15858:{sfx}", "gate_level": 3}, headers=h),
        call("POST", "/ko/v1/ingest", "ingest_without_token", json={"doc": doc}),
        call("POST", "/ko/v1/ingest", "ingest_invalid_doc", json={"doc": {"knowledge_id": "bad"}}, headers=h),
    ]
    return {"endpoint": "POST /ko/v1/ingest → GET /ko/v1/{id}/traceability → POST /ko/v1/{id}/promote",
            "router_mounted": not hasattr(_apimod, "_KO_V1_ROUTER_ERROR"),
            "calls": rows,
            "caller_module": "ke/api.py + ke/ko_v1_api.py → ke/ko_ingest.py"}


def main() -> int:
    bench = json.loads((OUT / "bench.json").read_text(encoding="utf-8")) \
        if (OUT / "bench.json").exists() else {}
    files = {}
    files["ingest_run"] = _dump("ingest_run.json", db_run())
    files["ke_api_live_call"] = _dump("ke_api_live_call.json", api_run())
    live = json.loads((OUT / "ingest_run.json").read_text(encoding="utf-8"))
    files["etr_live"] = _dump("etr_live.json", {
        "knowledge_id": live["ingest"]["knowledge_id"],
        "etr_before_promotion": live["etr_before_promotion"],
        "etr_after_promotion": live["etr_after_promotion"],
        "rule": "单条证据可追溯 := 报告闸∧小节闸∧工件闸；E-TR = 全绿条数/总条数"})

    evidence = {
        "anchor": "KBM-RCI-S2-SCHEMA",
        "mission_id": 15858,
        "repo": "TensorKnowledge",
        "level_declared": 4,
        "impl_files": [
            "ke/ko_ingest.py",
            "ke/ko_v1_api.py",
            "scripts/validate_ko_v1.py",
            "scripts/ko_v1.py",
            "schemas/knowledge-object-v1.schema.json",
            "schemas/sql/knowledge_object_v1.sql",
            "benchmarks/ko_v1_conformance/cases.py",
            "benchmarks/ko_v1_conformance/run_benchmark.py",
        ],
        "entry": "scripts/ko_v1.py",
        "run_artifacts": [
            "docs/rci/m15858/bench.json",
            "docs/rci/m15858/ingest_run.json",
            "docs/rci/m15858/etr_live.json",
            "docs/rci/m15858/ke_api_live_call.json",
            "docs/rci/m15858/pytest_junit.xml",
        ],
        "tests": [
            "tests/test_ko_v1_schema.py",
            "tests/test_ko_v1_ingest.py",
        ],
        "integration_callers": [
            "ke/api.py:app.include_router(ke.ko_v1_api.router) → POST /ko/v1/ingest → ke.ko_ingest.ingest",
            "scripts/ko_v1.py: ingest/promote/etr CLI 入口调用 ke.ko_ingest",
        ],
        "benchmark": {
            "file": "docs/rci/m15858/bench.json",
            "ref_vs_got": {
                "C1_doc_conformance_accuracy": {"ref": 1.0, "got": bench.get("criteria", {}).get(
                    "C1_doc_conformance_accuracy", {}).get("got")},
                "C2_transition_accuracy": {"ref": 1.0, "got": bench.get("criteria", {}).get(
                    "C2_transition_accuracy", {}).get("got")},
                "C3_etr_abs_error_max": {"ref": 0.0, "got": bench.get("criteria", {}).get(
                    "C3_etr_abs_error_max", {}).get("got")},
                "C4_throughput_per_s": {"ref": None, "got": bench.get("criteria", {}).get(
                    "C4_throughput_per_s", {}).get("got")},
            },
            "verdict": bench.get("verdict"),
            "n_cases": {"doc": len(bench.get("doc_cases") or []),
                        "transition": len(bench.get("transition_cases") or []),
                        "etr": len(bench.get("etr_cases") or [])},
        },
        "repro_cmd": ("python3 -m pytest tests/test_ko_v1_schema.py tests/test_ko_v1_ingest.py -q "
                      "&& python3 scripts/ko_v1.py bench && python3 scripts/ko_v1_evidence_run.py"),
        "notes": ("L3 晋级不经 Agent 自宣布：ko_verification 票据 gate_level>=2 + 三闸全绿由 DDL "
                  "触发器复核；L0 原件仍归 TensorData（本库只存引用）。"),
    }
    ev_path = REPO / "docs" / "rci" / "m15858-evidence.json"
    ev_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    lv, why = CLI.gatecheck(evidence, 4)
    files["gate_selfcheck"] = _dump("gate_selfcheck.json", {
        "declared": 4, "gate_level": lv, "why": why,
        "evidence_file": str(ev_path.relative_to(REPO)),
        "note": "镜像 maturity_gate.judge 六键复核（权威裁定在平台守护进程）"})
    print(json.dumps({"files": files, "gate_level": lv, "why": why}, ensure_ascii=False, indent=2))
    return 0 if lv >= 4 else 1


if __name__ == "__main__":
    sys.exit(main())