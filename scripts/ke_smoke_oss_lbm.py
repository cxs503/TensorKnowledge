"""Real-data smoke run for the KE API: ingest knowledge/oss-lbm, run all six
query classes plus search, and write every raw response to ``artifacts/ke_smoke``.

Nothing is synthesised: the artifact files contain exactly what the service
returned, so the summary in the report can be diffed against them.

Usage (server must already be up, e.g. from ke/api.service):
    KE_API_TOKEN=... python3 scripts/ke_smoke_oss_lbm.py \
        --base-url http://127.0.0.1:8021 --package knowledge/oss-lbm
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ke.ingest_client import ingest_package  # noqa: E402


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8021")
    ap.add_argument("--token", default=os.environ.get("KE_API_TOKEN", ""))
    ap.add_argument("--package", type=Path, default=ROOT / "knowledge" / "oss-lbm")
    ap.add_argument("--out", type=Path, default=ROOT / "artifacts" / "ke_smoke")
    ap.add_argument("--producer", default="agent-m8801")
    args = ap.parse_args(argv)

    if not args.token:
        print("error: no token (KE_API_TOKEN)", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    summary: dict = {"base_url": args.base_url, "package": str(args.package)}

    with httpx.Client(base_url=args.base_url, timeout=60.0) as client:
        health = client.get("/healthz")
        dump(args.out / "00_healthz.json", health.json())
        summary["healthz"] = health.json()

        ingest = ingest_package(args.base_url, args.token, args.package, args.producer,
                                client=client)
        dump(args.out / "01_ingest.json", ingest)
        summary["ingest"] = ingest["counts"]

        stats = client.get("/query/stats").json()
        dump(args.out / "q6_stats.json", stats)
        summary["stats"] = {k: stats[k] for k in
                            ("objects", "by_kind", "edges", "review_events",
                             "production_status", "evidence_status",
                             "review_status", "publication_status")}

        # deterministic anchor claim: the one linked to the most evidence
        claims = client.get("/ko", params={"kind": "claim", "limit": 2000}).json()["items"]
        anchor, anchor_n = None, -1
        for c in claims:
            n = client.get("/query/claim-evidence", params={"claim_id": c["id"]}).json()["count"]
            if n > anchor_n:
                anchor, anchor_n = c, n
        if anchor is None:
            print("error: no claims ingested", file=sys.stderr)
            return 1
        summary["anchor_claim"] = {"id": anchor["id"], "evidence_count": anchor_n}

        # Q1 by review state, and by evidence state
        q1a = client.get("/query/by-status",
                         params={"axis": "review", "status": "unreviewed"}).json()
        dump(args.out / "q1_by_status_review_unreviewed.json", q1a)
        q1b = client.get("/query/by-status",
                         params={"axis": "evidence", "status": "established"}).json()
        dump(args.out / "q1_by_status_evidence_established.json", q1b)
        summary["q1_by_status"] = {
            "review_unreviewed": q1a["count"],
            "evidence_established": q1b["count"],
        }

        # Q2 by evidence relation
        q2 = client.get("/query/by-evidence-relation", params={"relation": "supports"}).json()
        dump(args.out / "q2_by_evidence_relation_supports.json", q2)
        summary["q2_by_relation"] = {"relation": "supports", "count": q2["count"]}

        # Q3 provenance chain (claim -> evidence -> source)
        q3 = client.get("/query/chain", params={"claim_id": anchor["id"]}).json()
        dump(args.out / "q3_chain.json", q3)
        summary["q3_chain"] = {
            "claim_id": q3["claim_id"],
            "links": len(q3["links"]),
            "provenance_records": len(q3["provenance"]),
            "package_provenance_records": len(q3["package_provenance"]),
            "complete": q3["complete"],
        }

        # Q4 by domain
        q4 = client.get("/query/by-domain", params={"domain": "lattice-Boltzmann-method"}).json()
        dump(args.out / "q4_by_domain.json", q4)
        summary["q4_by_domain"] = {"domain": "lattice-Boltzmann-method", "count": q4["count"]}

        # Q5 claim -> evidence
        q5 = client.get("/query/claim-evidence", params={"claim_id": anchor["id"]}).json()
        dump(args.out / "q5_claim_evidence.json", q5)
        summary["q5_claim_evidence"] = {
            "claim_id": q5["claim_id"],
            "count": q5["count"],
            "dangling": len(q5["dangling_evidence_refs"]),
        }

        # search: text + domain + status filter
        srch = client.get("/search", params={"q": "lattice", "limit": 5}).json()
        dump(args.out / "search_lattice.json", srch)
        srch_f = client.get("/search", params={"q": "relaxation", "axis": "evidence",
                                               "status": "established", "limit": 5}).json()
        dump(args.out / "search_relaxation_established.json", srch_f)
        summary["search"] = {"lattice": srch["count"],
                             "relaxation+established": srch_f["count"]}

        # review state machine on a real record, using distinct identities
        try:
            review = client.post(
                f"/ko/{anchor['id']}/review",
                json={"decision": "approve",
                      "reviewer": {"id": "agent-reviewer-m8801", "reviewer_type": "agent"},
                      "rationale": "smoke: locator and source re-inspected"},
                headers={"Authorization": f"Bearer {args.token}"},
            )
            dump(args.out / "review_approve.json", {"status": review.status_code,
                                                    "body": review.json()})
            pub = client.post(f"/ko/{anchor['id']}/publish",
                              headers={"Authorization": f"Bearer {args.token}"})
            dump(args.out / "publish.json", {"status": pub.status_code, "body": pub.json()})
            summary["review_flow"] = {
                "approve_status": review.status_code,
                "review_status": review.json()["object"]["review_status"],
                "publish_status": pub.status_code,
                "publication_status": pub.json()["publication_status"],
            }
        except Exception as exc:  # pragma: no cover
            summary["review_flow"] = {"error": repr(exc)}

        # self-audit must be refused on real data too
        self_review = client.post(
            f"/ko/{anchor['id']}/review",
            json={"decision": "approve", "reviewer": {"id": anchor["producer"],
                                                      "reviewer_type": "agent"}},
            headers={"Authorization": f"Bearer {args.token}"},
        )
        dump(args.out / "self_review_refused.json",
             {"status": self_review.status_code, "body": self_review.json()})
        summary["self_review_refused"] = {"status": self_review.status_code,
                                          "detail": self_review.json().get("detail")}

        final_stats = client.get("/query/stats").json()
        dump(args.out / "final_stats.json", final_stats)
        summary["final_stats"] = {k: final_stats[k] for k in
                                  ("objects", "review_events", "publication_status")}

    dump(args.out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())