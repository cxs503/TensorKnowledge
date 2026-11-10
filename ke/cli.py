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

``demo`` runs the full closed loop (ingest -> all query classes -> xref
validation) and prints deterministic JSON; exit code 0 iff all invariants
hold.

``export`` produces training/eval/triple artifacts for physical-AI training
with epistemic hard gates and manifests.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

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
    if qtype == "stats":
        return q.stats(conn)
    raise SystemExit(f"unknown query type: {qtype}")


def cmd_ingest(args) -> int:
    conn = store.connect(args.db)
    counts = store.ingest_pilot(args.pilot, conn)
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

    p = sub.add_parser("export", help="export knowledge artifacts for physical-AI training")
    p.add_argument("pilot")
    p.add_argument("--kind", required=True, choices=["sft", "eval", "triples"],
                   help="Export type: sft (training corpus), eval (benchmark set), triples (KG triples)")
    p.add_argument("--out", required=True, help="Output directory for JSONL + manifest")
    p.add_argument("--db", default=None, help="Optional existing KE database path")
    p.set_defaults(fn=cmd_export)

    args = ap.parse_args(argv)
    if args.cmd == "query" and args.type != "stats" and not args.value:
        raise SystemExit(f"--value is required for query type {args.type}")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
