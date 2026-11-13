#!/usr/bin/env python3
"""KBM-RCI-S2-SCHEMA 第 2 轮 —— 现网 L3 凭据作用域审计（只读，零手抄）。

做什么：对 ``ko_v1`` 库执行 v1.1 硬化后的对账视图 ``ko_l3_unbound`` 与票源聚合，
输出 JSON 工件，供 docs/rci/l3-gate-scope-audit.md 逐条引用。

判定口径（与 v1.1 G1/G2 对齐）:
  binding='bound'                          → 票已按对象内容摘要绑定（合规）
  binding='legacy_ticket_without_subject_digest' → 历史票，无内容绑定（需平台重出票）
  binding='subject_digest_mismatch'        → 摘要不一致（内容在裁定后被改，重疑）
  binding='no_confirmed_ticket'            → L3 但无 confirmed 票（严重）

用法:
    python scripts/ko_v1_l3_scope_audit.py --out runs/rci/l3_scope_audit
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _connect(dsn: str):
    try:
        import psycopg  # noqa: PLC0415

        return psycopg.connect(dsn, autocommit=True)
    except ImportError:
        import psycopg2  # noqa: PLC0415

        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        return conn


def _rows(conn, sql: str) -> list[dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.environ.get("KE_PG_DSN") or "dbname=tensorknowledge")
    ap.add_argument("--schema", default="ko_v1")
    ap.add_argument("--out", default=str(ROOT / "runs" / "rci" / "l3_scope_audit"))
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    conn = _connect(args.dsn)
    try:
        conn.cursor().execute(f"SET search_path TO {args.schema};")
        unbound = _rows(conn, "SELECT * FROM ko_l3_unbound ORDER BY knowledge_id")
        tickets = _rows(conn, """
            SELECT ticket_id, source, gate_state, gate_level, maturity_verdict_id, mission_id,
                   subject_sha256 IS NOT NULL AS has_digest, verdict_by,
                   (SELECT count(*) FROM ko_verification x WHERE x.maturity_verdict_id = v.maturity_verdict_id
                      AND v.maturity_verdict_id IS NOT NULL) AS reuse_count
              FROM ko_verification v ORDER BY ticket_id
        """)
        objs = _rows(conn, """
            SELECT knowledge_id, type, verification_status, storage_level,
                   NULLIF(provenance->>'mission_id','')::BIGINT AS mission_id,
                   producer, content_sha256
              FROM ko_object ORDER BY knowledge_id
        """)
        dist = _rows(conn, "SELECT * FROM ko_state_distribution")
    finally:
        conn.close()

    l3 = [o for o in objs if o["storage_level"] == "L3"]
    verdict_reuse: dict[Any, int] = defaultdict(int)
    for t in tickets:
        if t["maturity_verdict_id"] is not None:
            verdict_reuse[t["maturity_verdict_id"]] += 1

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dsn_schema": f"{args.schema}",
        "counts": {
            "objects": len(objs),
            "l3_objects": len(l3),
            "tickets": len(tickets),
            "tickets_with_subject_digest": sum(1 for t in tickets if t["has_digest"]),
            "unbound_l3": len(unbound),
        },
        "binding_distribution": dict(Counter(u["binding"] for u in unbound)),
        "distinct_verdicts_used": len(verdict_reuse),
        "max_ticket_reuse_per_verdict": max(verdict_reuse.values()) if verdict_reuse else 0,
        "verdict_reuse": {str(k): v for k, v in sorted(verdict_reuse.items())},
        "l3_object_mission_ids": sorted({o["mission_id"] for o in l3 if o["mission_id"]}),
        "ticket_mission_ids": sorted({t["mission_id"] for t in tickets if t["mission_id"]}),
        "producers": dict(Counter(o["producer"] for o in objs)),
        "unbound_rows": unbound,
        "tickets": tickets,
        "state_distribution": dist,
    }

    (out / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str))
    print(json.dumps({k: report[k] for k in (
        "counts", "binding_distribution", "distinct_verdicts_used",
        "max_ticket_reuse_per_verdict", "l3_object_mission_ids", "ticket_mission_ids",
        "producers")}, ensure_ascii=False, indent=1, default=str))
    print(f"wrote {out/'audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())