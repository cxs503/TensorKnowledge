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
    python -m ke.cli export   <pilot_dir> --kind sft|eval|triples --out DIR [--db <path>]
    python -m ke.cli assets   list|show|register-ko|review|deprecate|report|register-mission \
                              --db <path> [subcommand args]

``demo`` runs the full closed loop (ingest -> all query classes -> xref
validation) and prints deterministic JSON; exit code 0 iff all invariants
hold.

``export`` produces training/eval/triple artifacts for physical-AI training
with epistemic hard gates and manifests.

Backend selection (same code path for both, see docs/ke/backends.md)::

    ke ingest <pilot> --db /tmp/ke.db                  # sqlite fixture
    ke ingest <pilot> --backend pg --schema ke         # PostgreSQL (KE_PG_DSN)
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import assets as asset_mgr
from . import mission_assets as mission_mgr
from . import export as exp
from . import queries as q
from . import store, validate


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
    if qtype == "gaps":
        return q.gap_anchors(conn)
    if qtype == "stats":
        return q.stats(conn)
    raise SystemExit(f"unknown query type: {qtype}")


def _connect(args):
    """Open the store selected by --backend/--db/--dsn/--schema."""
    return store.connect(args.db, backend=args.backend, dsn=args.dsn,
                         schema=args.schema, create_schema=bool(args.schema))


def cmd_ingest(args) -> int:
    conn = _connect(args)
    counts = store.ingest_pilot(args.pilot, conn)
    _print_json({"ingested": counts, "db": str(Path(args.db).resolve())})
    return 0


def cmd_query(args) -> int:
    conn = _connect(args)
    _print_json(_run_query(conn, args.type, args.value))
    return 0


def cmd_validate(args) -> int:
    conn = _connect(args)
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
    conn = _connect(args)
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
                        "evidence": link["evidence_id"],
                        "relation": link["relation"],
                        "source_url": link["source"]["url"],
                        "locator": link["locator"]["value"],
                    }
                    for link in chain["links"]
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


def cmd_export(args) -> int:
    """Export knowledge artifacts for physical-AI training."""
    out_dir = Path(args.out)
    pilot = Path(args.pilot).resolve()
    db_path = args.db if args.db else None

    manifest = exp.export(
        kind=args.kind,
        pilot_dir=pilot,
        db_path=db_path,
        out_dir=out_dir,
    )
    _print_json(manifest)
    return 0


# ---------------------------------------------------------------------------
# assets: knowledge asset life-cycle (see ke/assets.py + docs/ASSET-MANAGEMENT.md)
# ---------------------------------------------------------------------------
def _assets_store(args):
    return _connect(args)


def cmd_assets_list(args) -> int:
    conn = _assets_store(args)
    try:
        versions = asset_mgr.list_ko_versions(conn, args.ko_id)
    finally:
        conn.close()
    _print_json({"total": len(versions), "ko_versions": versions})
    return 0


def cmd_assets_show(args) -> int:
    conn = _assets_store(args)
    try:
        payload = (asset_mgr.get_ko_lineage(conn, args.ko_id) if args.lineage
                   else asset_mgr.get_ko_latest(conn, args.ko_id))
    finally:
        conn.close()
    if not payload:
        print(f"KO not found: {args.ko_id}", file=sys.stderr)
        return 1
    _print_json({"ko_id": args.ko_id, "lineage": payload} if args.lineage else payload)
    return 0


def cmd_assets_register_ko(args) -> int:
    conn = _assets_store(args)
    try:
        content = json.loads(args.content) if args.content else None
        vid = asset_mgr.register_ko_version(
            conn, args.ko_id, args.version, title=args.title,
            object_type=args.object_type, summary=args.summary, content=content,
            state=args.state, created_by=args.created_by, source_file=args.source_file,
        )
        conn.commit()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    _print_json({"registered": vid})
    return 0


def cmd_assets_review(args) -> int:
    conn = _assets_store(args)
    try:
        event_id = asset_mgr.record_review(
            conn, args.object_ref, args.decision,
            reviewer={"kind": args.reviewer_kind, "id": args.reviewer},
            policy_version=args.policy_version, rationale=args.rationale,
            findings=args.finding, supersedes_event=args.supersedes_event,
        )
        conn.commit()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    _print_json({"review_event": event_id, "decision": args.decision})
    return 0


def cmd_assets_deprecate(args) -> int:
    conn = _assets_store(args)
    try:
        event_id = asset_mgr.deprecate_ko(
            conn, args.object_ref,
            reviewer={"kind": args.reviewer_kind, "id": args.reviewer},
            rationale=args.rationale,
        )
        conn.commit()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    _print_json({"deprecated": args.object_ref, "review_event": event_id})
    return 0


def cmd_assets_register_dataset(args) -> int:
    conn = _assets_store(args)
    try:
        asset_id = asset_mgr.register_dataset_asset(
            conn, args.asset_id, args.type, args.version, args.count, args.sha256,
            status_dist=json.loads(args.status_dist) if args.status_dist else None,
            gen_params=json.loads(args.gen_params) if args.gen_params else None,
            upstream_commit=args.upstream_commit, created_by=args.created_by,
        )
        conn.commit()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    _print_json({"registered": asset_id})
    return 0


def cmd_assets_datasets(args) -> int:
    conn = _assets_store(args)
    try:
        assets = asset_mgr.list_dataset_assets(conn)
    finally:
        conn.close()
    _print_json({"total": len(assets), "dataset_assets": assets})
    return 0


def cmd_assets_report(args) -> int:
    conn = _assets_store(args)
    try:
        report = asset_mgr.get_quality_report(conn, stale_days=args.stale_days)
        conn.commit()
    finally:
        conn.close()
    _print_json(report)
    return 0


def cmd_assets_export_index(args) -> int:
    conn = _assets_store(args)
    try:
        text = asset_mgr.export_asset_index_json(conn)
    finally:
        conn.close()
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"written: {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def cmd_assets_register_mission(args) -> int:
    specs = json.loads(Path(args.deliverables).read_text(encoding="utf-8"))
    if isinstance(specs, dict):
        specs = specs.get("deliverables", [])
    conn = _assets_store(args)
    try:
        report = mission_mgr.register_matured_deliverables(
            conn, args.mission_id, specs,
            base_dir=Path(args.base_dir), version=args.version,
            created_by=args.created_by, state=args.state,
        )
        conn.commit()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    _print_json(report)
    return 0


def cmd_assets_mission_report(args) -> int:
    conn = _assets_store(args)
    try:
        report = mission_mgr.mission_deliverable_report(conn, args.mission_id)
    finally:
        conn.close()
    _print_json(report)
    return 0


def cmd_assets_verify_mission(args) -> int:
    conn = _assets_store(args)
    try:
        report = mission_mgr.verify_mission_deliverables(
            conn, args.mission_id, base_dir=Path(args.base_dir)
        )
    finally:
        conn.close()
    _print_json(report)
    return 0 if report["ok"] else 1


def _add_backend_args(p) -> None:
    p.add_argument("--backend", default=None, choices=list(store.BACKENDS),
                   help="storage backend (default: inferred from --db)")
    p.add_argument("--dsn", default=None,
                   help="PostgreSQL DSN (default: $KE_PG_DSN)")
    p.add_argument("--schema", default=None,
                   help="PostgreSQL schema to create/use (default: search_path)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ke", description="TensorKnowledge Knowledge Engine prototype")
    sub = ap.add_subparsers(dest="cmd", required=True)

    parsers = []

    p = sub.add_parser("ingest", help="ingest a pilot package")
    parsers.append(p)
    p.add_argument("pilot")
    p.add_argument("--db", required=True)
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("query", help="run one query class")
    parsers.append(p)
    p.add_argument("pilot")
    p.add_argument("--db", required=True)
    p.add_argument("--type", required=True,
                   choices=["status", "relation", "domain", "chain", "claim", "gaps", "stats"])
    p.add_argument("--value", default=None)
    p.set_defaults(fn=cmd_query)

    p = sub.add_parser("validate", help="schema + xref validation (validate_pilot.py semantics)")
    parsers.append(p)
    p.add_argument("pilot")
    p.add_argument("--db", required=True)
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("demo", help="full closed loop: ingest + queries + validation")
    parsers.append(p)
    p.add_argument("pilot")
    p.add_argument("--db", default=None)
    p.set_defaults(fn=cmd_demo)

    p = sub.add_parser("export", help="export knowledge artifacts for physical-AI training")
    p.add_argument("pilot")
    p.add_argument("--kind", required=True, choices=["sft", "eval", "triples"],
                   help="Export type: sft (training corpus), eval (benchmark set), triples (KG triples)")
    p.add_argument("--out", required=True, help="Output directory for JSONL + manifest")
    p.add_argument("--db", default=None, help="Optional existing KE database path")
    p.set_defaults(fn=cmd_export)

    # --- assets subcommand group (knowledge asset life-cycle) ---
    assets_p = sub.add_parser("assets", help="knowledge asset management "
                              "(KO versions, review gate, quality ledger)")
    assets_sub = assets_p.add_subparsers(dest="assets_cmd", required=True)

    p = assets_sub.add_parser("list", help="list registered KO versions")
    p.add_argument("--ko-id", default=None, help="restrict to one KO")
    p.set_defaults(fn=cmd_assets_list)

    p = assets_sub.add_parser("show", help="show the latest version (or --lineage)")
    p.add_argument("ko_id")
    p.add_argument("--lineage", action="store_true", help="show the full version chain")
    p.set_defaults(fn=cmd_assets_show)

    p = assets_sub.add_parser("register-ko", help="register a new immutable KO version")
    p.add_argument("ko_id")
    p.add_argument("--version", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--object-type", default="")
    p.add_argument("--summary", default="")
    p.add_argument("--content", default=None, help="JSON payload (domains, ...)")
    p.add_argument("--state", default="draft",
                   choices=["draft", "in_review", "published"])
    p.add_argument("--created-by", default="")
    p.add_argument("--source-file", default="")
    p.set_defaults(fn=cmd_assets_register_ko)

    p = assets_sub.add_parser("review", help="append a review decision (audited gate)")
    p.add_argument("object_ref", help="version id (<ko_id>:v<semver>) or ko_id")
    p.add_argument("--decision", required=True, choices=list(asset_mgr.DECISIONS))
    p.add_argument("--rationale", default="")
    p.add_argument("--reviewer", default="unattributed")
    p.add_argument("--reviewer-kind", default="human", choices=["human", "agent", "org"])
    p.add_argument("--policy-version", default="review-policy-v1")
    p.add_argument("--finding", action="append", default=None)
    p.add_argument("--supersedes-event", default=None)
    p.set_defaults(fn=cmd_assets_review)

    p = assets_sub.add_parser("deprecate", help="deprecate a version (audited)")
    p.add_argument("object_ref")
    p.add_argument("--rationale", default="deprecated")
    p.add_argument("--reviewer", default="unattributed")
    p.add_argument("--reviewer-kind", default="human", choices=["human", "agent", "org"])
    p.set_defaults(fn=cmd_assets_deprecate)

    p = assets_sub.add_parser("register-dataset", help="register a versioned dataset asset")
    p.add_argument("--asset-id", required=True)
    p.add_argument("--type", required=True, choices=["sft", "eval", "triples"])
    p.add_argument("--version", required=True)
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--status-dist", default=None, help="JSON {\"train\": N, ...}")
    p.add_argument("--gen-params", default=None, help="JSON generation parameters")
    p.add_argument("--upstream-commit", default="")
    p.add_argument("--created-by", default="")
    p.set_defaults(fn=cmd_assets_register_dataset)

    p = assets_sub.add_parser("datasets", help="list dataset assets")
    p.set_defaults(fn=cmd_assets_datasets)

    p = assets_sub.add_parser("report", help="quality ledger + health summary")
    p.add_argument("--stale-days", type=int, default=30)
    p.set_defaults(fn=cmd_assets_report)

    p = assets_sub.add_parser("export-index", help="export asset-index-v1 JSON")
    p.add_argument("--output", default=None, help="write to file instead of stdout")
    p.set_defaults(fn=cmd_assets_export_index)

    p = assets_sub.add_parser("register-mission",
                               help="register a matured mission's deliverables as "
                                    "immutable KO versions (in_review)")
    p.add_argument("mission_id")
    p.add_argument("--deliverables", required=True,
                   help="JSON file: list of {deliverable_id,title,path,evidence_grade,acceptance}")
    p.add_argument("--base-dir", required=True,
                   help="directory the deliverable paths are resolved against")
    p.add_argument("--version", default="1.0.0")
    p.add_argument("--state", default="in_review", choices=list(mission_mgr.ALLOWED_BIRTH_STATES))
    p.add_argument("--created-by", default="mission-registrar")
    p.set_defaults(fn=cmd_assets_register_mission)

    p = assets_sub.add_parser("mission-report",
                              help="registered deliverables of a mission (+ states)")
    p.add_argument("mission_id")
    p.set_defaults(fn=cmd_assets_mission_report)

    p = assets_sub.add_parser("verify-mission",
                              help="re-hash mission deliverables against the registry")
    p.add_argument("mission_id")
    p.add_argument("--base-dir", required=True)
    p.set_defaults(fn=cmd_assets_verify_mission)

    assets_leaves = [sp for name, sp in assets_sub.choices.items()]
    for sp in assets_leaves:
        sp.add_argument("--db", required=True, help="KE sqlite path or PostgreSQL DSN")
        parsers.append(sp)

    for p in parsers:
        _add_backend_args(p)

    args = ap.parse_args(argv)
    if args.cmd == "query" and args.type != "stats" and not args.value:
        raise SystemExit(f"--value is required for query type {args.type}")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
