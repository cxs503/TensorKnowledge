"""KE migration: SQLite fixture -> PostgreSQL (authoritative), with reconcile.

The Knowledge Engine has exactly one authoritative store: PostgreSQL.  The
existing package data (``knowledge/oss-lbm/`` — claims, evidence, provenance,
gap anchors) is loaded into a SQLite staging store by the shared contract and
then migrated row-for-row into PostgreSQL.  The migration is

* **idempotent** — every KE table is emptied and repopulated inside one
  transaction, so re-running it converges to the same state;
* **auditable** — a reconciliation table is emitted with object, relation and
  assertion counts plus a per-table SHA-256 of the canonical row dump, so
  "before == after" is a machine check and not a claim.

Usage::

    python -m ke.migrate                       # knowledge/oss-lbm -> KE_PG_DSN
    python -m ke.migrate --source knowledge/oss-lbm --pg-schema ke
    python -m ke.migrate --source-db /tmp/x.db  # migrate an existing SQLite KE
    python -m ke.migrate --check                # reconcile only, no writes

Exit code 0 iff every object/relation/assertion count and digest matches.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import tempfile
from pathlib import Path

from . import contract, queries, store, validate

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "knowledge" / "oss-lbm"
# NOTE: the artefacts live under docs/ (not artifacts/) because the mission-push
# gate drops `artifacts/**` as run-record; the reconciliation table is a
# deliverable that must reach GitHub (see docs/ops/filter-audit.md).
DEFAULT_OUT = REPO_ROOT / "docs" / "ke" / "migration-reconcile.json"
DEFAULT_MD = REPO_ROOT / "docs" / "ke" / "migration-reconcile.md"

#: tables reported as "objects" (records) vs "relations" (cross-reference edges)
OBJECT_TABLES = ("claims", "evidence", "provenance", "gap_anchors")
RELATION_TABLES = ("claim_evidence", "evidence_claims", "gap_claims")

_FRIENDLY = {
    "claims": "claims (claim-record)",
    "evidence": "evidence (evidence-record)",
    "provenance": "provenance (provenance-record)",
    "gap_anchors": "gap anchors (gap-anchor)",
    "claim_evidence": "claim → evidence 边",
    "evidence_claims": "evidence → claim 边",
    "gap_claims": "gap → claim 边",
    "ingest_meta": "ingest 元数据",
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def mask_dsn(dsn: str) -> str:
    """Never write credentials into migration artefacts."""
    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", dsn)


def build_source_store(source: str | Path, source_db: str | Path | None = None) -> store.Store:
    """SQLite staging store holding the source package (or an existing DB)."""
    if source_db is not None and Path(source_db).exists():
        return store.connect(str(source_db))
    tmp = Path(tempfile.mkdtemp(prefix="ke-migrate-")) / "source.db"
    st = store.connect(tmp)
    contract.ingest_source(source, st)
    return st


def snapshot(st: store.Store) -> dict:
    """Objects / relations / assertions inventory of one store."""
    digests = contract.digests(st)
    objects = {
        t: {"rows": digests[t]["rows"], "sha256": digests[t]["sha256"]} for t in OBJECT_TABLES
    }
    relations = {
        t: {"rows": digests[t]["rows"], "sha256": digests[t]["sha256"]} for t in RELATION_TABLES
    }
    xrep = validate.xref_report(st)
    checks = {
        "unresolved_claim_refs": len(xrep["unresolved_claim_refs"]),
        "unresolved_evidence_refs": len(xrep["unresolved_evidence_refs"]),
        "unresolved_gap_refs": len(xrep["unresolved_gap_refs"]),
        "orphan_evidence": len(xrep["orphan_evidence"]),
        "claims_without_evidence": len(xrep["claims_without_evidence"]),
    }
    return {
        "objects": objects,
        "relations": relations,
        "assertions": {
            "checks": checks,
            "violations_total": sum(checks.values()),
            "stats": queries.stats(st),
        },
        "digests": digests,
    }


def copy_all(src: store.Store, dst: store.Store) -> dict[str, int]:
    """Mirror every KE table from ``src`` into ``dst`` in one transaction."""
    counts: dict[str, int] = {}
    with dst:
        for table in contract.TABLE_ORDER:
            dst.execute(f"DELETE FROM {table}")
            cols = contract.table_columns(table)
            rows = list(contract.dump_table(src, table))
            counts[table] = len(rows)
            if rows:
                sql = (f"INSERT INTO {table} ({', '.join(cols)}) "
                       f"VALUES ({', '.join('?' for _ in cols)})")
                dst.executemany(sql, rows)
    return counts


def reconcile(src: store.Store, dst: store.Store) -> dict:
    """Compare source and target inventories; return the reconciliation table."""
    s_snap, d_snap = snapshot(src), snapshot(dst)
    rows = []
    for group, tables in (("object", OBJECT_TABLES), ("relation", RELATION_TABLES)):
        for t in tables:
            s, d = s_snap["objects"].get(t) or s_snap["relations"][t], \
                   d_snap["objects"].get(t) or d_snap["relations"][t]
            rows.append({
                "group": group,
                "table": t,
                "label": _FRIENDLY.get(t, t),
                "source_rows": s["rows"],
                "target_rows": d["rows"],
                "rows_match": s["rows"] == d["rows"],
                "source_sha256": s["sha256"],
                "target_sha256": d["sha256"],
                "digest_match": s["sha256"] == d["sha256"],
            })
    s_assert, d_assert = s_snap["assertions"], d_snap["assertions"]
    assertions = {
        "source": s_assert["checks"],
        "target": d_assert["checks"],
        "source_violations_total": s_assert["violations_total"],
        "target_violations_total": d_assert["violations_total"],
        "match": s_assert["checks"] == d_assert["checks"],
        "stats_match": s_assert["stats"] == d_assert["stats"],
        "stats": s_assert["stats"],
    }
    totals = {
        "objects_source": sum(v["rows"] for v in s_snap["objects"].values()),
        "objects_target": sum(v["rows"] for v in d_snap["objects"].values()),
        "relations_source": sum(v["rows"] for v in s_snap["relations"].values()),
        "relations_target": sum(v["rows"] for v in d_snap["relations"].values()),
        "assertion_violations_source": s_assert["violations_total"],
        "assertion_violations_target": d_assert["violations_total"],
    }
    ok = (
        all(r["rows_match"] and r["digest_match"] for r in rows)
        and assertions["match"]
        and assertions["stats_match"]
        and totals["objects_source"] == totals["objects_target"]
        and totals["relations_source"] == totals["relations_target"]
        and totals["assertion_violations_source"] == totals["assertion_violations_target"]
    )
    return {"rows": rows, "assertions": assertions, "totals": totals,
            "verdict": "PASS" if ok else "FAIL"}


def render_markdown(report: dict) -> str:
    head = (
        f"<!-- generated by python -m ke.migrate at {report['generated_at']} -->\n"
        f"# KE 迁移对账表（SQLite 暂存 → PostgreSQL 权威）\n\n"
        f"- 数据源: `{report['source']}`\n"
        f"- 源（SQLite fixture）: `{report['source_db']}`\n"
        f"- 目标（PostgreSQL 权威）: `{report['pg_schema']}` @ `{report['pg_dsn']}`\n"
        f"- 判定: **{report['verdict']}**\n\n"
        f"## 对象数 / 关系数（逐表，含行级摘要）\n\n"
        f"| 分组 | 表 | 源行数 | 目标行数 | 行数一致 | 摘要一致 | sha256（前 12） |\n"
        f"|---|---|---:|---:|:--:|:--:|---|\n"
    )
    lines = []
    for r in report["rows"]:
        lines.append(
            f"| {r['group']} | {r['label']} | {r['source_rows']} | {r['target_rows']} | "
            f"{'✅' if r['rows_match'] else '❌'} | {'✅' if r['digest_match'] else '❌'} | "
            f"`{r['source_sha256'][:12]}` / `{r['target_sha256'][:12]}` |"
        )
    a = report["assertions"]
    tail = (
        f"\n**合计**：对象数 {report['totals']['objects_source']} → "
        f"{report['totals']['objects_target']}；关系数 {report['totals']['relations_source']} → "
        f"{report['totals']['relations_target']}。\n\n"
        f"## 断言数（xref 不变量，源 vs 目标）\n\n"
        f"| 断言 | 源违例数 | 目标违例数 |\n|---|---:|---:|\n"
        + "".join(f"| {k} | {v} | {a['target'][k]} |\n" for k, v in a["source"].items())
        + f"\n断言违例合计 {a['source_violations_total']} → {a['target_violations_total']}"
          f"（{'一致' if a['match'] else '不一致'}）；"
          f"分布统计一致：{'是' if a['stats_match'] else '否'}。\n"
    )
    return head + "\n".join(lines) + tail


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ke.migrate", description=__doc__.splitlines()[0])
    ap.add_argument("--source", default=str(DEFAULT_SOURCE),
                    help="package directory to migrate (default: knowledge/oss-lbm)")
    ap.add_argument("--source-db", default=None,
                    help="existing SQLite KE database to migrate instead of re-ingesting --source")
    ap.add_argument("--pg-dsn", default=None, help="PostgreSQL DSN (default: $KE_PG_DSN)")
    ap.add_argument("--pg-schema", default="ke", help="target schema in the PG database (default: ke)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="reconciliation JSON output path")
    ap.add_argument("--md", default=str(DEFAULT_MD), help="reconciliation Markdown output path")
    ap.add_argument("--check", action="store_true", help="reconcile only; do not write to PostgreSQL")
    args = ap.parse_args(argv)

    dsn = args.pg_dsn or store.default_pg_dsn()
    src = build_source_store(args.source, args.source_db)
    source_db_label = src.db_path or "<in-memory>"
    try:
        dst = store.connect(backend="pg", dsn=dsn, schema=args.pg_schema, create_schema=True)
        try:
            if not args.check:
                copy_all(src, dst)
            report = reconcile(src, dst)
        finally:
            dst.close()
    finally:
        src.close()

    report.update({
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": str(Path(args.source)),
        "source_db": source_db_label,
        "pg_dsn": mask_dsn(dsn),
        "pg_schema": args.pg_schema,
        "check_only": bool(args.check),
        "tool": "ke.migrate",
    })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    md = Path(args.md)
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(render_markdown(report), encoding="utf-8")

    print(render_markdown(report))
    print(f"\nreconciliation written to {out} and {md}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())