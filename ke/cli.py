"""KE prototype — CLI.

Usage:
    python -m ke.cli ingest   <pilot_dir> --db <path>
    python -m ke.cli query    <pilot_dir> --db <path> --type status --value contested
    python -m ke.cli query    <pilot_dir> --db <path> --type relation --value supports
    python -m ke.cli query    <pilot_dir> --db <path> --type domain   --value "research data stewardship principles"
    python -m ke.cli query    <pilot_dir> --db <path> --type chain    --value tkc:prov-o:wasattributedto-signature
    python -m ke.cli query    <pilot_dir> --db <path> --type claim    --value tkc:fair:requires-open-access
    python -m ke.cli query    <pilot_dir> --db <path> --type stats
    python -m ke.cli validate <pilot_dir> --db <path>
    python -m ke.cli demo     <pilot_dir> [--db <path>]

    python -m ke.cli assets list              --db <path>
    python -m ke.cli assets show <ko_id>      --db <path> [--lineage]
    python -m ke.cli assets deprecate <vid>   --db <path> [--reviewer <id>] [--rationale <text>]
    python -m ke.cli assets report            --db <path> [--stale-days N]
    python -m ke.cli assets export-index      --db <path> [--output <path>]
    python -m ke.cli assets register-dataset  --db <path> --asset-id <id> --type <sft|eval|triples>
                                              --version <ver> --count <N> --sha256 <hash>

``demo`` runs the full closed loop (ingest -> all query classes -> xref
validation) and prints deterministic JSON; exit code 0 iff all invariants
hold.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import queries as q
from . import store, validate
from . import assets as asset_mgr


def _print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def _run_query(conn, qtype: str, value: str | None) -> object:
    if qtype == "status":
        return q.claims_by_status(conn, value)
    if qtype == "relation":
        return q.evidence_by_relation(conn, value)
    if qtype == "domain":
        return q.claims_by_domain(conn, value)
    if qtype == "chain":
        return q.provenance_chain(conn, value)
    if qtype == "claim":
        return q.evidence_for_claim(conn, value)
    if qtype == "stats":
        return q.stats(conn)
    raise SystemExit(f"unknown query type: {qtype}")


def cmd_ingest(args) -> int:
    conn = store.connect(args.db)
    counts = store.ingest_pilot(args.pilot, conn)
    conn.commit()
    _print_json({"ingested": counts, "db": str(Path(args.db).resolve())})
    return 0


def cmd_query(args) -> int:
    conn = store.connect(args.db)
    _print_json(_run_query(conn, args.type, args.value))
    return 0


def cmd_validate(args) -> int:
    conn = store.connect(args.db)
    lines = validate.validate_package(args.pilot, conn)
    fails = [n for n, ok, _ in lines if not ok]
    for name, ok, detail in lines:
        print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail and not ok else ""))
    print(
        f"\n== ke validation: {'ALL PASS' if not fails else str(len(fails)) + ' FAILURES: ' + '; '.join(fails)}"
    )
    return 1 if fails else 0


def cmd_demo(args) -> int:
    db = args.db or tempfile.mktemp(suffix=".ke.db")
    conn = store.connect(db)
    counts = store.ingest_pilot(args.pilot, conn)
    print(f"# ingest: {json.dumps(counts, sort_keys=True)}")

    demo = {
        "ingest": counts,
        "Q1_claims_by_status": {
            s: [c["id"] for c in q.claims_by_status(conn, s)]
            for s in ("established", "well-supported", "contested", "not-assessed")
        },
        "Q2_evidence_by_relation": {
            r: [e["id"] for e in q.evidence_by_relation(conn, r)]
            for r in ("supports", "refutes", "qualifies", "contextualizes", "mentions")
        },
        "Q3_provenance_chain": {
            cid: {
                "claim": chain["claim"]["id"],
                "status": chain["claim"]["epistemic_status"],
                "links": [
                    {
                        "evidence": l["evidence_id"],
                        "relation": l["relation"],
                        "source_url": l["source"]["url"],
                        "locator": l["locator"]["value"],
                    }
                    for l in chain["links"]
                ],
            }
            for cid, chain in (
                (c["id"], q.provenance_chain(conn, c["id"]))
                for c in q.all_claims(conn)
            )
        },
        "Q4_claims_by_domain": {
            d: [c["id"] for c in q.claims_by_domain(conn, d)]
            for d in (
                "research data stewardship principles",
                "provenance standards / ontology specification text",
            )
        },
        "Q5_evidence_for_claim": {
            "tkc:fair:requires-open-access": [
                {"evidence": e["id"], "relation": e["relation"]}
                for e in q.evidence_for_claim(conn, "tkc:fair:requires-open-access")
            ]
        },
        "Q6_stats": q.stats(conn),
    }
    _print_json(demo)

    lines = validate.validate_package(args.pilot, conn)
    fails = [n for n, ok, _ in lines if not ok]
    for name, ok, detail in lines:
        print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail and not ok else ""))
    print(f"\n== ke demo: {'ALL PASS' if not fails else str(len(fails)) + ' FAILURES: ' + '; '.join(fails)}")
    if args.db is None:
        Path(db).unlink(missing_ok=True)
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# Assets subcommands
# ---------------------------------------------------------------------------

def cmd_assets_list(args) -> int:
    """List all registered KO versions."""
    conn = store.connect(args.db)
    rows = conn.execute(
        """SELECT id, ko_id, version, state, title, object_type, created_at
           FROM ko_versions ORDER BY ko_id, created_at"""
    ).fetchall()
    if not rows:
        print("No KO versions registered.")
        return 0
    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "ko_id": r["ko_id"],
            "version": r["version"],
            "state": r["state"],
            "title": r["title"] or "",
            "object_type": r["object_type"] or "",
            "created_at": r["created_at"],
        })
    _print_json({"total": len(items), "ko_versions": items})
    return 0


def cmd_assets_show(args) -> int:
    """Show a KO version details, optionally with full lineage."""
    conn = store.connect(args.db)
    ko_id = args.ko_id

    if args.lineage:
        lineage = asset_mgr.get_ko_lineage(conn, ko_id)
        if not lineage:
            print(f"KO not found: {ko_id}")
            return 1
        _print_json({"ko_id": ko_id, "lineage": lineage})
    else:
        latest = asset_mgr.get_ko_latest(conn, ko_id)
        if not latest:
            print(f"KO not found: {ko_id}")
            return 1
        _print_json(latest)
    return 0


def cmd_assets_deprecate(args) -> int:
    """Deprecate a KO version."""
    conn = store.connect(args.db)
    vid = args.vid
    reviewer = getattr(args, "reviewer", "") or "agent-m8811"
    rationale = getattr(args, "rationale", "") or "deprecated via CLI"
    try:
        event_id = asset_mgr.deprecate_ko(conn, vid, reviewer=reviewer, rationale=rationale)
        conn.commit()
        _print_json({"deprecated": vid, "review_event": event_id})
    except (KeyError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_assets_report(args) -> int:
    """Generate asset health report."""
    conn = store.connect(args.db)
    stale_days = getattr(args, "stale_days", 30) or 30
    report = asset_mgr.get_quality_report(conn, stale_days=stale_days)
    _print_json(report)
    return 0


def cmd_assets_export_index(args) -> int:
    """Export ASSET-INDEX compatible JSON."""
    conn = store.connect(args.db)
    output = asset_mgr.export_asset_index_json(conn)
    output_path = getattr(args, "output", None)
    if output_path:
        Path(output_path).write_text(output, encoding="utf-8")
        print(f"Written to {output_path}")
    else:
        print(output)
    return 0


def cmd_assets_register_dataset(args) -> int:
    """Register a dataset-level asset."""
    conn = store.connect(args.db)
    try:
        asset_id = asset_mgr.register_dataset_asset(
            conn,
            asset_id=args.asset_id,
            asset_type=args.type,
            version=args.version,
            record_count=args.count,
            sha256=args.sha256,
            created_by=getattr(args, "created_by", "") or "agent-m8811",
        )
        conn.commit()
        _print_json({"registered": asset_id})
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ke", description="TensorKnowledge Knowledge Engine prototype")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest", help="ingest a pilot package into SQLite")
    p.add_argument("pilot")
    p.add_argument("--db", required=True)
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("query", help="run one query class")
    p.add_argument("pilot")
    p.add_argument("--db", required=True)
    p.add_argument("--type", required=True,
                   choices=["status", "relation", "domain", "chain", "claim", "stats"])
    p.add_argument("--value", default=None)
    p.set_defaults(fn=cmd_query)

    p = sub.add_parser("validate", help="schema + xref validation (validate_pilot.py semantics)")
    p.add_argument("pilot")
    p.add_argument("--db", required=True)
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("demo", help="full closed loop: ingest + queries + validation")
    p.add_argument("pilot")
    p.add_argument("--db", default=None)
    p.set_defaults(fn=cmd_demo)

    # --- assets subcommand group ---
    assets_p = sub.add_parser("assets", help="knowledge asset management")
    assets_sub = assets_p.add_subparsers(dest="assets_cmd", required=True)

    # assets list
    p = assets_sub.add_parser("list", help="list all registered KO versions")
    p.add_argument("--db", required=True)
    p.set_defaults(fn=cmd_assets_list)

    # assets show
    p = assets_sub.add_parser("show", help="show KO version details")
    p.add_argument("ko_id", help="KO identifier (e.g. tko:oss-lbm:pylbm)")
    p.add_argument("--db", required=True)
    p.add_argument("--lineage", action="store_true", help="show full version chain")
    p.set_defaults(fn=cmd_assets_show)

    # assets deprecate
    p = assets_sub.add_parser("deprecate", help="deprecate a KO version")
    p.add_argument("vid", help="version id (e.g. tko:oss-lbm:pylbm:v1.0.0)")
    p.add_argument("--db", required=True)
    p.add_argument("--reviewer", default="agent-m8811")
    p.add_argument("--rationale", default="deprecated via CLI")
    p.set_defaults(fn=cmd_assets_deprecate)

    # assets report
    p = assets_sub.add_parser("report", help="generate asset health report")
    p.add_argument("--db", required=True)
    p.add_argument("--stale-days", type=int, default=30)
    p.set_defaults(fn=cmd_assets_report)

    # assets export-index
    p = assets_sub.add_parser("export-index", help="export ASSET-INDEX compatible JSON")
    p.add_argument("--db", required=True)
    p.add_argument("--output", default=None, help="output file path")
    p.set_defaults(fn=cmd_assets_export_index)

    # assets register-dataset
    p = assets_sub.add_parser("register-dataset", help="register a dataset-level asset")
    p.add_argument("--db", required=True)
    p.add_argument("--asset-id", required=True)
    p.add_argument("--type", required=True, choices=["sft", "eval", "triples"])
    p.add_argument("--version", required=True)
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--created-by", default="agent-m8811")
    p.set_defaults(fn=cmd_assets_register_dataset)

    args = ap.parse_args(argv)
    if args.cmd == "query" and args.type != "stats" and not args.value:
        raise SystemExit(f"--value is required for query type {args.type}")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
