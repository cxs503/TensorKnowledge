"""Independent recount of ``knowledge/oss-lbm`` vs what the KE API reports.

The point is a *baseline* for the smoke run: the expected object and edge counts
are recomputed directly from the package's JSON files with a tiny standalone
loader (no reuse of ``ke.ingest_client``), then compared against the API's own
``/query/stats``.  Any divergence is reported, not smoothed over.

Usage:
    KE_API_TOKEN=... python3 scripts/ke_smoke_verify.py --base-url http://127.0.0.1:8021
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DIRS = {"claims": "claim", "evidence": "evidence", "provenance": "provenance"}


def _iter_records(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        yield from (r for r in data if isinstance(r, dict))
    elif isinstance(data, dict):
        for key in ("records", "items"):
            if isinstance(data.get(key), list):
                yield from (r for r in data[key] if isinstance(r, dict))
                return
        yield data


def recount(pkg: Path) -> dict:
    counts = {"claim": 0, "evidence": 0, "provenance": 0}
    ids: set[str] = set()
    dupes: list[str] = []
    edges: set[tuple[str, str, str, str]] = set()
    for kind_dir, kind in DIRS.items():
        for sub in [pkg] + [p for p in pkg.rglob("*") if p.is_dir()]:
            d = sub / kind_dir
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.json")):
                for rec in _iter_records(f):
                    rid = rec.get("id")
                    if not rid:
                        continue
                    if rid in ids:
                        dupes.append(rid)
                        continue
                    ids.add(rid)
                    counts[kind] += 1
                    if kind == "claim":
                        for e in rec.get("evidence_refs") or []:
                            if isinstance(e, str):
                                edges.add((rid, e, "refs", "claim_evidence"))
                    elif kind == "evidence":
                        rel = str(rec.get("relation") or "mentions")
                        for c in rec.get("claim_refs") or []:
                            if isinstance(c, str):
                                edges.add((rid, c, rel, "evidence_claim"))
    return {"counts": counts, "unique_ids": len(ids), "duplicate_ids": sorted(set(dupes)),
            "edges": len(edges)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8021")
    ap.add_argument("--package", type=Path, default=ROOT / "knowledge" / "oss-lbm")
    ap.add_argument("--out", type=Path, default=ROOT / "artifacts" / "ke_smoke")
    args = ap.parse_args(argv)

    expected = recount(args.package)
    with httpx.Client(base_url=args.base_url, timeout=60.0) as c:
        stats = c.get("/query/stats").json()
        total = c.get("/ko", params={"limit": 1}).json()["total"]

    checks = {
        "objects": {"expected": expected["unique_ids"], "api": stats["objects"],
                    "match": stats["objects"] == expected["unique_ids"]},
        "edges": {"expected": expected["edges"], "api": stats["edges"],
                  "match": stats["edges"] == expected["edges"]},
    }
    for kind in ("claim", "evidence", "provenance"):
        checks[f"kind:{kind}"] = {
            "expected": expected["counts"][kind],
            "api": stats["by_kind"].get(kind, 0),
            "match": stats["by_kind"].get(kind, 0) == expected["counts"][kind],
        }
    out = {"package": str(args.package), "expected": expected, "api_stats": stats,
           "checks": checks, "all_match": all(v["match"] for v in checks.values()),
           "note": "counts are unique record ids (duplicates in the package are listed "
                   "in expected.duplicate_ids and ingested once)"}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "verify_counts.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"all_match": out["all_match"], "checks": checks,
                      "duplicates": expected["duplicate_ids"][:5]},
                     ensure_ascii=False, indent=1))
    return 0 if out["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())