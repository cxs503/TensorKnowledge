"""KE service client — push a knowledge package into the HTTP API.

Reads a package laid out like ``knowledge/oss-lbm`` (real repo data):

    <pkg>/claims/*.json | <pkg>/claims/claims.json          (list or per-file)
    <pkg>/evidence/*.json | <pkg>/evidence/evidence.json
    <pkg>/provenance/*.json | <pkg>/provenance/provenance.json
    <pkg>/<subpkg>/...                                      (recursive)

and POSTs every record to ``POST /ko``.  Idempotent in the sense that a
duplicate id returns 409 and is counted as ``exists`` — re-running an import
never duplicates data.  Nothing is invented: record bytes are sent verbatim.

Usage:
    python -m ke.ingest_client --base-url http://127.0.0.1:8021 \
        --token "$KE_API_TOKEN" --package knowledge/oss-lbm \
        --producer agent-m8801 [--strict]

Exit code 0 iff no record failed for a reason other than "already exists".
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator

import httpx

KIND_BY_DIR = {"claims": "claim", "evidence": "evidence", "provenance": "provenance"}


def _records(path: Path) -> Iterator[dict]:
    """Yield records from a *.json file (a list, or a single record)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for rec in data:
            if isinstance(rec, dict):
                yield rec
    elif isinstance(data, dict):
        for key in ("records", "items"):
            if isinstance(data.get(key), list):
                for rec in data[key]:
                    if isinstance(rec, dict):
                        yield rec
                return
        yield data


def package_records(pkg: Path) -> Iterator[tuple[str, dict, str]]:
    """Yield (kind, record, source_path) for a whole package tree."""
    if not pkg.is_dir():
        raise FileNotFoundError(pkg)
    for kind_dir, kind in KIND_BY_DIR.items():
        for d in [pkg] + sorted(p for p in pkg.rglob("*") if p.is_dir()):
            sub = d / kind_dir
            if not sub.is_dir():
                continue
            for f in sorted(sub.glob("*.json")):
                for rec in _records(f):
                    yield kind, rec, str(f)


def producer_of(rec: dict, default: str) -> str:
    for key in ("created_by", "captured_by"):
        if isinstance(rec.get(key), str) and rec[key]:
            return rec[key]
    agents = rec.get("agents")
    if isinstance(agents, list):
        for a in agents:
            if isinstance(a, dict) and isinstance(a.get("id"), str) and a["id"]:
                return a["id"]
    return default


def ingest_package(
    base_url: str,
    token: str,
    pkg: Path,
    producer: str,
    *,
    strict: bool = False,
    timeout: float = 30.0,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """POST every record in ``pkg``. Returns per-outcome counters + failures."""
    counts = {"created": 0, "exists": 0, "failed": 0, "total": 0}
    failures: list[dict] = []
    owned = client is None
    client = client or httpx.Client(base_url=base_url, timeout=timeout)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        for kind, rec, src in package_records(pkg):
            counts["total"] += 1
            body = {"kind": kind, "producer": producer_of(rec, producer), "doc": rec}
            if strict:
                body["strict"] = True
            res = client.post("/ko", json=body, headers=headers)
            if res.status_code == 201:
                counts["created"] += 1
            elif res.status_code == 409:
                counts["exists"] += 1
            else:
                counts["failed"] += 1
                failures.append({
                    "id": rec.get("id"),
                    "kind": kind,
                    "status": res.status_code,
                    "detail": res.text[:400],
                    "source": src,
                })
    finally:
        if owned:
            client.close()
    return {"counts": counts, "failures": failures}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest a knowledge package into the KE API")
    ap.add_argument("--base-url", default="http://127.0.0.1:8021")
    ap.add_argument("--token", default=None, help="bearer token (default: $KE_API_TOKEN)")
    ap.add_argument("--package", required=True, type=Path)
    ap.add_argument("--producer", default="ke-ingest-client")
    ap.add_argument("--strict", action="store_true", help="validate against schemas/*.schema.json")
    args = ap.parse_args(argv)

    import os

    token = args.token or os.environ.get("KE_API_TOKEN", "")
    if not token:
        print("error: no token (pass --token or set KE_API_TOKEN)", file=sys.stderr)
        return 2
    out = ingest_package(args.base_url, token, args.package, args.producer, strict=args.strict)
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if out["counts"]["failed"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())