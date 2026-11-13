#!/usr/bin/env python3
"""KO Schema v1 单一入口（entry）：validate / ingest / promote / etr / ddl / bench / gatecheck。

这是本能力的**入口工件**（docs/rci/schema-v1.md §6 引用）：所有操作从这一条命令进，
不需要调用方知道内部模块布局。

    python3 scripts/ko_v1.py validate --doc ko.json [--transition-from unverified --actor-role agent]
    python3 scripts/ko_v1.py ddl      --schema ko_v1
    python3 scripts/ko_v1.py ingest   --doc ko.json [--schema ko_v1] [--reports reports.json] [--out r.json]
    python3 scripts/ko_v1.py ticket   --knowledge-id ko:x:y --ticket mv:1 --gate-level 3
    python3 scripts/ko_v1.py promote  --knowledge-id ko:x:y [--schema ko_v1]
    python3 scripts/ko_v1.py etr      --knowledge-id ko:x:y [--schema ko_v1]
    python3 scripts/ko_v1.py bench
    python3 scripts/ko_v1.py gatecheck --evidence docs/rci/m15858-evidence.json

退出码：0 成功/合规；1 判据不过（校验失败、benchmark FAIL、gatecheck 未达声明级）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import ko_ingest  # noqa: E402
from scripts import validate_ko_v1 as V  # noqa: E402

SCHEME = {  # 与 /root/tp-agent/maturity_gate.py 的 JUDGE_SCHEME 同构（本脚本是镜像，不是权威）
    2: ["impl_files", "entry", "run_artifacts"],
    3: ["impl_files", "entry", "run_artifacts", "integration_callers"],
    4: ["impl_files", "entry", "run_artifacts", "integration_callers", "benchmark", "repro_cmd"],
}


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_validate(a) -> int:
    doc = _load(a.doc)
    try:
        V.validate_document(doc)
        if a.transition_from:
            V.check_transition({"verification_status": a.transition_from,
                                "claim": doc.get("claim")}, doc, actor_role=a.actor_role)
    except V.KOError as exc:
        _dump({"ok": False, "errors": exc.errors})
        return 1
    _dump({"ok": True, "knowledge_id": doc.get("knowledge_id"),
           "transition_checked": bool(a.transition_from)})
    return 0


def cmd_ddl(a) -> int:
    conn = ko_ingest.connect(a.dsn)
    ko_ingest.ensure_schema(conn, a.schema)
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema=%s ORDER BY 1", (a.schema,))
        tables = [r[0] for r in cur.fetchall()]
    conn.close()
    _dump({"ok": True, "schema": a.schema, "tables": tables,
           "ddl": str(ko_ingest.DDL_PATH.relative_to(REPO))})
    return 0


def cmd_ingest(a) -> int:
    doc = _load(a.doc)
    reports = _load(a.reports) if a.reports else None
    conn = ko_ingest.connect(a.dsn)
    ko_ingest.ensure_schema(conn, a.schema)
    try:
        rep = ko_ingest.ingest(conn, doc, schema=a.schema, reports=reports,
                               repo_roots=[REPO], on_conflict="skip")
    except (ko_ingest.KoIngestError, V.KOError) as exc:
        _dump({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return 1
    finally:
        conn.close()
    rep["ok"] = True
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    _dump(rep)
    return 0


def cmd_ticket(a) -> int:
    conn = ko_ingest.connect(a.dsn)
    ko_ingest.ensure_schema(conn, a.schema)
    rep = ko_ingest.add_ticket(conn, a.knowledge_id, a.ticket, schema=a.schema,
                               gate_level=a.gate_level, gate_state=a.gate_state,
                               source=a.source)
    conn.close()
    _dump({"ok": True, **rep})
    return 0


def cmd_promote(a) -> int:
    conn = ko_ingest.connect(a.dsn)
    ko_ingest.ensure_schema(conn, a.schema)
    try:
        rep = ko_ingest.promote(conn, a.knowledge_id, schema=a.schema)
    except Exception as exc:  # 数据库触发器拒绝也是合法结果，如实回报
        _dump({"ok": False, "error": f"{type(exc).__name__}: {str(exc).strip()[:300]}"})
        return 1
    finally:
        conn.close()
    _dump({"ok": True, **rep})
    return 0


def cmd_etr(a) -> int:
    conn = ko_ingest.connect(a.dsn)
    ko_ingest.ensure_schema(conn, a.schema)
    rep = ko_ingest.traceability(conn, a.knowledge_id, schema=a.schema)
    conn.close()
    _dump({"ok": True, "knowledge_id": a.knowledge_id, "traceability": rep})
    return 0


def cmd_bench(a) -> int:
    return subprocess.call([sys.executable, str(REPO / "benchmarks" / "ko_v1_conformance"
                                               / "run_benchmark.py")])


def _exists(paths) -> bool:
    return all((REPO / str(p)).exists() for p in paths)


def gatecheck(evidence: dict, declared: int) -> tuple[int, list[str]]:
    """镜像 maturity_gate.judge 的六键复核（相对路径按仓库根解析）。"""
    reasons: list[str] = []
    for lv in range(min(declared, 4), 1, -1):
        miss = []
        for key in SCHEME[lv]:
            val = evidence.get(key)
            if val in (None, "", [], {}):
                miss.append(key)
            elif key == "impl_files" and not _exists(val):
                miss.append(key + "(缺失)")
            elif key in ("entry", "run_artifacts") and not _exists(
                    val if isinstance(val, list) else [val]):
                miss.append(key + "(工件缺失)")
            elif key == "integration_callers":
                caller = str((val if isinstance(val, list) else [val])[0]).split(":")[0]
                hit = subprocess.run(["grep", "-rl", "--include=*.py", "-F", caller[:60], str(REPO)],
                                     capture_output=True, text=True)
                if not hit.stdout.strip():
                    miss.append(key + "(grep 无引用)")
            elif key == "benchmark" and not isinstance(val, (dict, list)):
                miss.append(key + "(无数值对照)")
            elif key == "repro_cmd" and not (isinstance(val, str) and len(val) > 5):
                miss.append(key + "(不可复现)")
        if not miss:
            return lv, reasons
        reasons.append(f"L{lv} 缺: {','.join(miss)}")
    return 1, reasons


def cmd_gatecheck(a) -> int:
    ev = _load(a.evidence)
    lv, why = gatecheck(ev, a.declared)
    _dump({"declared": a.declared, "gate_level": lv, "why": why,
           "evidence_file": a.evidence,
           "note": "镜像 maturity_gate.judge；权威裁定在平台守护进程"})
    return 0 if lv >= 2 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate")
    p.add_argument("--doc", required=True)
    p.add_argument("--transition-from", choices=V.STATUSES)
    p.add_argument("--actor-role", default="agent", choices=("agent", "human", "platform"))
    p.set_defaults(fn=cmd_validate)

    for name, fn, extra in (("ddl", cmd_ddl, ()), ("ingest", cmd_ingest, ()),
                            ("promote", cmd_promote, ()), ("etr", cmd_etr, ())):
        p = sub.add_parser(name)
        p.add_argument("--schema", default="ko_v1")
        p.add_argument("--dsn", default=None)
        if name in ("ingest",):
            p.add_argument("--doc", required=True)
            p.add_argument("--reports", default=None)
            p.add_argument("--out", default=None)
        if name in ("promote", "etr"):
            p.add_argument("--knowledge-id", required=True)
        p.set_defaults(fn=fn)

    p = sub.add_parser("ticket")
    p.add_argument("--knowledge-id", required=True)
    p.add_argument("--ticket", required=True)
    p.add_argument("--gate-level", type=int, default=3)
    p.add_argument("--gate-state", default="confirmed", choices=("confirmed", "reopened"))
    p.add_argument("--source", default="maturity_gate",
                   choices=("maturity_gate", "benchmark_gate", "xval_gate", "repro_gate"))
    p.add_argument("--schema", default="ko_v1")
    p.add_argument("--dsn", default=None)
    p.set_defaults(fn=cmd_ticket)

    p = sub.add_parser("bench")
    p.set_defaults(fn=cmd_bench)

    p = sub.add_parser("gatecheck")
    p.add_argument("--evidence", required=True)
    p.add_argument("--declared", type=int, default=4)
    p.set_defaults(fn=cmd_gatecheck)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())