#!/usr/bin/env python3
"""RCI-S1 sensitivity: duplicate-cluster count vs the Jaccard verification gate.

Uses the frozen shard features (gram_hashes + minhash signatures) so no report
text is re-read; only the verification threshold moves.  Also reports the
"LSH-band-only" (gate = 0) upper bound, which quantifies how much the exact
Jaccard recomputation prunes.

Usage: python3 sensitivity.py --shards DIR --out out/sensitivity.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rp", os.path.join(HERE, "rci_pipeline.py"))
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)


def load(shards):
    feats = []
    for fn in sorted(os.listdir(shards)):
        if fn.startswith("shard_") and fn.endswith(".jsonl"):
            feats.extend(json.loads(l) for l in open(os.path.join(shards, fn), encoding="utf-8"))
    feats.sort(key=lambda r: r["id"])
    return feats


def lsh_pairs(feats):
    cand = set()
    for b in range(rp.BANDS):
        buckets = defaultdict(list)
        for r in feats:
            buckets[tuple(r["minhash"][b * rp.ROWS:(b + 1) * rp.ROWS])].append(r["id"])
        for grp in buckets.values():
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    x, y = grp[i], grp[j]
                    cand.add((x, y) if x < y else (y, x))
    return sorted(cand)


def clusters(feats, pairs, gate):
    dsu = rp.DSU()
    by_id = {r["id"]: r for r in feats}
    # structural links are gate-independent (exact sha / title / skeleton)
    for key in ("md_sha256", "title_norm", "skeleton_sha256"):
        grp = defaultdict(list)
        for r in feats:
            if r[key]:
                grp[r[key]].append(r["id"])
        for g in grp.values():
            for x in g[1:]:
                dsu.union(g[0], x)
    used = 0
    for a, b in pairs:
        sa, sb = set(by_id[a]["gram_hashes"]), set(by_id[b]["gram_hashes"])
        if not sa or not sb:
            continue
        inter = len(sa & sb)
        jac = inter / (len(sa) + len(sb) - inter)
        if gate == 0 or jac >= gate:
            dsu.union(a, b)
            used += 1
    comp = defaultdict(list)
    for r in feats:
        comp[dsu.find(r["id"])].append(r["id"])
    multi = {k: v for k, v in comp.items() if len(v) >= 2}
    rows = sum(len(v) for v in multi.values())
    return {"gate": gate, "lsh_pairs": len(pairs), "pairs_accepted": used,
            "dup_clusters": len(multi), "dup_reports": rows,
            "dup_excess": rows - len(multi),
            "largest_cluster": max((len(v) for v in multi.values()), default=0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gates", default="0.4,0.5,0.7")
    a = ap.parse_args()
    feats = load(a.shards)
    pairs = lsh_pairs(feats)
    res = [clusters(feats, pairs, float(g)) for g in a.gates.split(",")]
    res.append(clusters(feats, pairs, 0.0))
    out = {"n_reports": len(feats), "params": rp.PARAMS,
           "note": "gate=0.0 == LSH-band-only upper bound (no exact Jaccard pruning)",
           "sweep": res}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out["sweep"], ensure_ascii=False))


if __name__ == "__main__":
    main()