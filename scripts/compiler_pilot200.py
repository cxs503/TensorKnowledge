"""Knowledge Compiler 试点批全链跑（真实报告，非样例）。

链条：tensor_reports（真实正文）→ Compiler S1–S7 → KO v1 校验 → 证据三闸复核
（verify_kobject）→ PG ko_* 入库（ko_compiler_v1 schema）→ 检索回查。

验收口径（本单 ④）：200 试点批中「走通全链」份数 ≥ 50。走通 = 每份报告满足
compile(claims>0) ∧ 全部 KO 过 schema ∧ 全部 KO 过证据三闸 ∧ 全部 KO 入库 ∧
按 knowledge_id 可取回 ∧ 该报告至少 1 条 KO 可被文本检索命中。

    python scripts/compiler_pilot200.py --manifest <sample.json> --out runs/compiler-v1
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ke import ko_store  # noqa: E402
from ke.compiler import compile_report, verify_kobject  # noqa: E402


def collect_ids(obj) -> list[int]:
    out: list[int] = []
    if isinstance(obj, int) and not isinstance(obj, bool):
        out.append(obj)
    elif isinstance(obj, str) and obj.isdigit():
        out.append(int(obj))
    elif isinstance(obj, dict):
        for k in ("selected", "report_ids", "id", "report_id"):
            if k in obj:
                out.extend(collect_ids(obj[k]))
        for k, v in obj.items():
            if k not in ("selected", "report_ids", "id", "report_id") and isinstance(v, (list, dict)):
                out.extend(collect_ids(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(collect_ids(v))
    return out


def facet_of(scenario: str | None) -> str:
    head = (scenario or "").split("/")[0].strip().lower()
    head = re.sub(r"[^a-z0-9._-]+", "-", head).strip("-")
    return head or "tensorplatform"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="/root/tp-agent/work/m15462/artifacts/rci/pilot200/sample.json")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--out", default=str(ROOT / "runs" / "compiler-v1"))
    ap.add_argument("--schema", default=ko_store.DEFAULT_SCHEMA)
    ap.add_argument("--dsn", default=None)
    ap.add_argument("--min-full", type=int, default=50)
    args = ap.parse_args(argv)

    # 试点批来源：factory 自己的产线批次 = tk_work_packages 里的报告集合
    # （每份报告对应 01/02/03/04 工作包；200 试点批 = 200 份真实报告）。
    import psycopg
    from psycopg.rows import dict_row

    dsn = "dbname=tensorplatform user=postgres"
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        rows = conn.execute(
            "SELECT DISTINCT report_id FROM tk_work_packages "
            "WHERE report_id IS NOT NULL ORDER BY report_id LIMIT %s", (args.limit,)
        ).fetchall()
    batch = [int(r["report_id"]) for r in rows]
    manifest_note = {"manifest": args.manifest, "mode": "tk_work_packages"}
    if Path(args.manifest).exists():
        import hashlib
        manifest_note["manifest_sha256"] = hashlib.sha256(
            Path(args.manifest).read_bytes()).hexdigest()

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        rows = conn.execute(
            "SELECT id, markdown, scenario_key FROM tensor_reports WHERE id = ANY(%s)", (batch,)
        ).fetchall()
    by_id = {int(r["id"]): r for r in rows}

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    kconn = ko_store.connect(args.dsn, schema=args.schema)

    chain, objects = [], []
    totals = {"reports": 0, "compiled": 0, "verification_failed": 0,
              "kobjects": 0, "inserted": 0, "exists": 0, "retrievable_by_id": 0,
              "search_hits": 0, "full": 0, "missing_report": 0, "empty_claims": 0,
              "duplicate_claim": 0}

    for rid in batch:
        rec = by_id.get(rid)
        if not rec or not (rec["markdown"] or "").strip():
            totals["missing_report"] += 1
            chain.append({"report_id": rid, "status": "missing_report"})
            continue
        md = rec["markdown"]
        scenario = rec.get("scenario_key") or ""
        res = compile_report(md, report_id=rid, domain=scenario or "unclassified",
                             facet=facet_of(scenario))
        totals["reports"] += 1
        ok_ver = sum(1 for d in res.kobjects if verify_kobject(d, md, report_id=rid)["ok"])
        if ok_ver != len(res.kobjects):
            totals["verification_failed"] += 1
        ing = ko_store.ingest_documents(kconn, res.kobjects)
        totals["inserted"] += ing["inserted"]
        totals["exists"] += ing["exists"]
        totals["duplicate_claim"] += ing["duplicate_claim"]
        totals["kobjects"] += len(res.kobjects)
        retr = 0
        for d in res.kobjects:
            if ko_store.get(kconn, d["knowledge_id"]) is not None:
                retr += 1
        totals["retrievable_by_id"] += retr
        hit = 0
        if res.kobjects:
            probe = res.kobjects[0]["claim"][:40]
            hit = sum(1 for r in ko_store.search(kconn, probe, limit=50)
                      if r["report_id"] == rid)
        totals["search_hits"] += 1 if hit else 0
        if not res.claims:
            totals["empty_claims"] += 1
        full = (bool(res.claims) and ok_ver == len(res.kobjects) and retr == len(res.kobjects)
                and ing["rejected"] == 0 and hit > 0)
        totals["full"] += 1 if full else 0
        totals["compiled"] += 1
        chain.append({
            "report_id": rid, "scenario_key": scenario, "claims": len(res.claims),
            "kobjects": len(res.kobjects), "verified": ok_ver, "retrievable": retr,
            "search_hit": hit, "inserted": ing["inserted"], "rejected": ing["rejected"],
            "duplicate_claim": ing["duplicate_claim"],
            "contradictions": len(res.contradictions), "duplicates": len(res.duplicates),
            "source_hash": res.source_hash, "status": "full" if full else "partial",
        })
        for d in res.kobjects:
            objects.append({"knowledge_id": d["knowledge_id"], "report_id": rid,
                            "domain": d["domain"], "type": d["type"],
                            "storage_level": d["provenance"]["storage_level"],
                            "verification_status": d["verification_status"],
                            "claim": d["claim"]})
        print("r%-6d claims=%-3d ko=%-3d ver=%-3d retr=%-3d %s"
              % (rid, len(res.claims), len(res.kobjects), ok_ver, retr,
                 "FULL" if full else "partial"), flush=True)

    totals["batch_source"] = manifest_note
    totals["batch_size"] = len(batch)
    totals["acceptance_target"] = args.min_full
    totals["acceptance_met"] = totals["full"] >= args.min_full
    totals["ko_store"] = ko_store.stats(kconn)
    (out_dir / "chain.json").write_text(
        json.dumps({"totals": totals, "per_report": chain}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    with (out_dir / "objects.jsonl").open("w", encoding="utf-8") as fh:
        for o in objects:
            fh.write(json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in totals.items() if k != "ko_store"}, ensure_ascii=False, indent=2))
    return 0 if totals["acceptance_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
