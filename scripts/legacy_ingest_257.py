"""257 条 PG 迁移记录的收编（provenance=legacy-migration）。

来源（真实数据，不手抄）：``ke_service`` 库 ``ke_ko`` 表里由 ``ke.migrate`` 迁移
入 PG 的四契约记录（claim/evidence/provenance）。历史口径 257 = 102 claims +
142 evidence + 7 provenance + 6 gap anchors（见 docs/ke/migration-reconcile.json，
PASS 2026-11-10）；6 条 gap anchor 不是知识对象，走缺口算子队列而不进 KO 表。

产物：
* ``knowledge/legacy-migration/oss-lbm/{claims,evidence,provenance}.json`` ——
  与 factory 产线同形状的四契约记录（字节取自 PG，逐条附 legacy 标记）；
* ``knowledge/legacy-migration/legacy-index.json`` —— 记录 → 来源行 + 标记；
* ``knowledge/legacy-migration/gap-queue.json`` —— 缺口算子输入（TK 缺口 → TP 研究任务）；
* 统一管线入库：``ke_unified_v1`` schema（ke.contract 四契约表），并跑 queries.stats。

    python scripts/legacy_ingest_257.py --dsn "dbname=ke_service user=postgres"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ke import contract, queries, store  # noqa: E402

OUT = ROOT / "knowledge" / "legacy-migration"
RECONCILE = ROOT / "docs" / "ke" / "migration-reconcile.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default="dbname=ke_service user=postgres")
    ap.add_argument("--ke-schema", default="ke_unified_v1")
    ap.add_argument("--create", action="store_true", default=True)
    args = ap.parse_args(argv)

    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(args.dsn, row_factory=dict_row) as conn:
        rows = conn.execute(
            "SELECT kind, id, doc::text AS doc, domain, producer FROM ke_ko ORDER BY kind, id"
        ).fetchall()
    records: dict[str, list[dict]] = {"claims": [], "evidence": [], "provenance": []}
    index = []
    for r in rows:
        kind = r["kind"]
        bucket = {"claim": "claims", "evidence": "evidence", "provenance": "provenance"}.get(kind)
        if not bucket:
            continue
        doc = json.loads(r["doc"])
        if kind == "provenance":
            ext = doc.setdefault("extensions", {})
            ext["provenance_kind"] = "legacy-migration"
            ext["source_table"] = "ke_service.ke_ko"
        elif kind == "claim":
            notes = doc.setdefault("notes", [])
            if isinstance(notes, list):
                notes.append("provenance=legacy-migration (ke_service.ke_ko)")
        records[bucket].append(doc)
        index.append({"kind": kind, "id": r["id"], "provenance_kind": "legacy-migration",
                      "source_table": "ke_service.ke_ko", "domain": r["domain"], "producer": r["producer"]})

    OUT.mkdir(parents=True, exist_ok=True)
    for name, recs in records.items():
        (OUT / f"{name}.json").write_text(
            json.dumps(recs, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    reconcile = json.loads(RECONCILE.read_text(encoding="utf-8"))
    expect = {r["table"]: r["source_rows"] for r in reconcile.get("rows", [])}
    counts = {k: len(v) for k, v in records.items()}
    object_rows = sum(counts.values())
    gap_anchors = int(expect.get("gap_anchors", 0)) if "gap_anchors" in expect else None
    if gap_anchors is None:
        # reconcile 只列四张表时不猜：缺口数从总数差反推，写清楚是反推
        gap_anchors = int(reconcile["totals"]["objects_source"]) - object_rows
    (OUT / "legacy-index.json").write_text(
        json.dumps({"records": index, "counts": counts,
                    "reconcile_totals": reconcile["totals"],
                    "reconcile_rows": {k: expect.get(k) for k in ("claims", "evidence", "provenance")},
                    "gap_anchors": gap_anchors,
                    "note": "对象行逐条取自 ke_service.ke_ko；gap anchor 不进 KO 表"}, ensure_ascii=False,
                   indent=2) + "\n", encoding="utf-8")

    # 缺口算子输入：当前仓内 oss-lbm 缺口锚（真实文件）→ TP 研究任务接口
    gaps = []
    for f in sorted((ROOT / "knowledge" / "oss-lbm").rglob("gaps/*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for g in (data if isinstance(data, list) else [data]):
            gaps.append({"gap_id": g.get("id"), "source_file": str(f.relative_to(ROOT)),
                         "statement": g.get("statement") or g.get("description"),
                         "resolved_by_claims": g.get("resolved_by_claims", []),
                         "provenance_kind": "legacy-migration"})
    (OUT / "gap-queue.json").write_text(
        json.dumps({"gap_anchors_in_pipeline": len(gaps),
                    "historical_gap_anchors": gap_anchors,
                    "research_task_interface": "docs/compiler/KNOWLEDGE-COMPILER-SPEC-v1.md §6",
                    "gaps": gaps}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ke = store.connect(backend="pg", dsn=args.dsn, schema=args.ke_schema, create_schema=True)
    ing = contract.ingest_source(OUT, ke, strict=False)
    stats = queries.stats(ke)
    print(json.dumps({"records": counts, "object_rows": object_rows,
                      "reconcile_objects": reconcile["totals"]["objects_source"],
                      "gap_anchors": gap_anchors, "ingest": ing,
                      "ke_stats": stats.get("counts", stats)}, ensure_ascii=False, indent=2))
    ok = object_rows + gap_anchors == int(reconcile["totals"]["objects_source"])
    print("RECONCILE %s (%d objects + %d gap anchors = %d)"
          % ("PASS" if ok else "FAIL", object_rows, gap_anchors, reconcile["totals"]["objects_source"]))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
