"""Run the self-built thin layer (Option C) end-to-end: ingest + 4 primitives +
hybrid retrieval + PROV-O export + lossless round-trip, on real PostgreSQL 15.

Evidence produced (written to artifacts/ke_eval/):
  thinlayer_result.json   counts, latencies, per-primitive result sizes + samples
  thinlayer_roundtrip.json  schema-validation of every record read back out of PG

Usage:
  python run_thinlayer_demo.py --dsn "host=127.0.0.1 port=55433 user=ke dbname=ke_eval" \
      --corpus artifacts/ke_eval/corpus.json --out artifacts/ke_eval
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from thinlayer import ThinLayer  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.environ.get("KE_PG_DSN",
                   "host=127.0.0.1 port=55433 user=ke dbname=ke_eval"))
    ap.add_argument("--corpus", default="artifacts/ke_eval/corpus.json")
    ap.add_argument("--out", default="artifacts/ke_eval")
    ap.add_argument("--schema-dir", default="schemas")
    a = ap.parse_args()

    payload = json.loads(Path(a.corpus).read_text())
    corpus = payload["corpus"]

    tl = ThinLayer(a.dsn)
    tl.init_schema()
    ingest = tl.ingest(corpus)

    res = {"backend": "PostgreSQL 15.5 (127.0.0.1:55433), schema=ke",
           "ingest": {k: v for k, v in ingest.items()}}

    others = tl.q1_claim_status("contested")
    _, t1 = ThinLayer.timeit(lambda: tl.q1_claim_status("provisional"))
    res["P1_claim_status"] = {"contested_claims": len(others),
                              "contested_sample": others[:2], **t1}

    rels = tl.q2_evidence_relations()
    _, t2 = ThinLayer.timeit(lambda: tl.q2_evidence_relations())
    counts = {}
    for cid, by_rel in rels.items():
        for rel in by_rel:
            counts[rel] = counts.get(rel, 0) + len(by_rel[rel])
    res["P2_evidence_relations"] = {"claims_with_evidence": len(rels),
                                    "relation_counts": counts, **t2}

    chain = tl.q3_provenance_chain("tkc:landscape:global-landscape-01")
    _, t3 = ThinLayer.timeit(lambda: tl.q3_provenance_chain("tkc:landscape:global-landscape-01"))
    res["P3_provenance_chain"] = {"nodes": len(chain), "sample": chain[:3], **t3}

    doms = {d: tl.q4_domain(d) for d in ("benchmark-fixtures", "knowledge-engineering", "standards")}
    _, t4 = ThinLayer.timeit(lambda: tl.q4_domain("knowledge-engineering"))
    res["P4_domain"] = {d: {"claims": len(v["claims"]), "objects": len(v["objects"])}
                        for d, v in doms.items()}
    res["P4_domain"].update(t4)

    hy = tl.q5_hybrid("provenance is replaceable backend graph fidelity", k=5)
    _, t5 = ThinLayer.timeit(lambda: tl.q5_hybrid("provenance is replaceable backend", k=5))
    res["P5_hybrid_rrf"] = {**{k: v for k, v in hy.items() if k != "fused"}, **t5,
                            "top5": hy["fused"]}
    hy_dom = tl.q5_hybrid("temporal graph evolving facts", k=5, domain="knowledge-engineering")
    res["P5_hybrid_rrf_domain_scoped"] = {"domain": hy_dom["domain"], "top5": hy_dom["fused"]}

    res["prov_o_export"] = tl.prov_o_export("tkc:landscape:global-landscape-01")

    rt = tl.roundtrip(a.schema_dir)
    res["roundtrip_validation"] = rt

    # governance invariant probe: producer may not review own claim
    self_review_rejected = False
    try:
        with tl.conn.cursor() as cur:
            cur.execute("""INSERT INTO ke.review_event
                (id,object_ref,object_version,decision,reviewer_id,reviewed_at,policy_version,payload)
                VALUES ('tkr:probe:self-approval','tkc:landscape:global-landscape-01','0.1.0',
                        'approve','ke-eval-agent', now(), 'probe','{}')""")
    except Exception as exc:  # expected: trigger fires
        self_review_rejected = "self-approval rejected" in str(exc)
    res["governance_invariant"] = {"self_approval_rejected": self_review_rejected}

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "thinlayer_result.json").write_text(json.dumps(res, indent=1, default=str))
    (out / "thinlayer_roundtrip.json").write_text(json.dumps(rt, indent=1))
    print(json.dumps({k: res[k] for k in ("ingest", "P1_claim_status", "P2_evidence_relations",
                                          "P3_provenance_chain", "P4_domain", "P5_hybrid_rrf",
                                          "governance_invariant")}, indent=1, default=str)[:3000])
    tl.close()


if __name__ == "__main__":
    main()