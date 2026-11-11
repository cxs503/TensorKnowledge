#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge per-record ingress JSON files into the canonical aggregate files.

Context: the OSS-LBM knowledge package carries two layouts that coexisted in
two generations of the tree:

  * generation-1 (main):  one aggregate list per record type
        claims/claims.json, evidence/evidence.json, provenance/provenance.json
  * generation-2 (agent/m8634): one file per record
        claims/tkc-oss-lbm-*.json, evidence/tke-oss-lbm-*.json,
        provenance/tkp-oss-lbm-*.json

This tool performs the *additive* merge (generation-2 -> generation-1) that the
FEAT-TK-OSS-LANDING re-landing needs: every per-record file is inserted into the
aggregate list keyed by its ``id``.  It is idempotent and refuses to silently
overwrite an existing record with different content.

Rules
-----
1. Records are keyed by ``id``.  An id already present in the aggregate with
   byte-identical JSON content is skipped (idempotent re-run).
2. An id already present with *different* content is a hard error: the caller
   must resolve the conflict manually.  Nothing is written in that case.
3. Existing aggregate order is preserved; new records are appended sorted by id
   so repeated runs are deterministic.
4. No record is ever dropped: the tool only appends.

Usage
-----
    python3 knowledge/oss-lbm/tools/merge_record_files.py            # merge
    python3 knowledge/oss-lbm/tools/merge_record_files.py --check    # dry run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent

# (record kind, aggregate file, per-record glob)
SPECS = (
    ("claim", PKG / "claims" / "claims.json", "claims/tkc-*.json"),
    ("evidence", PKG / "evidence" / "evidence.json", "evidence/tke-*.json"),
    ("provenance", PKG / "provenance" / "provenance.json", "provenance/tkp-*.json"),
)


def load_list(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"FAIL: {path} is not a JSON array")
    return data


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def merge_kind(kind: str, agg_path: Path, pattern: str, check_only: bool) -> tuple[int, list[str], list[str]]:
    agg = load_list(agg_path)
    by_id = {rec["id"]: rec for rec in agg}
    if len(by_id) != len(agg):
        raise SystemExit(f"FAIL: duplicate ids already present in {agg_path}")

    added: list[str] = []
    identical: list[str] = []
    conflicts: list[str] = []

    for rec_path in sorted(PKG.glob(pattern)):
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        rid = rec["id"]
        existing = by_id.get(rid)
        if existing is None:
            by_id[rid] = rec
            agg.append(rec)
            added.append(rid)
        elif canonical(existing) == canonical(rec):
            identical.append(rid)
        else:
            conflicts.append(f"{kind} {rid}: {rec_path.name} differs from aggregate entry")

    if conflicts:
        print(f"FAIL {kind}: {len(conflicts)} conflict(s), nothing written")
        for c in conflicts:
            print(f"  - {c}")
        raise SystemExit(1)

    if added and not check_only:
        agg_sorted_new = agg[len(agg) - len(added):]
        agg_sorted_new.sort(key=lambda r: r["id"])
        agg[len(agg) - len(added):] = agg_sorted_new
        agg_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        f"PASS {kind}: {len(agg)} records in aggregate "
        f"(+{len(added)} merged, {len(identical)} already present)"
        + (" [check-only, not written]" if check_only else "")
    )
    return len(agg), added, identical


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="dry run: report what would be merged")
    args = ap.parse_args(argv)

    for kind, agg_path, pattern in SPECS:
        if not agg_path.exists():
            print(f"FAIL: missing aggregate {agg_path}")
            return 1
        before = len(load_list(agg_path))
        after, added, _ = merge_kind(kind, agg_path, pattern, args.check)
        print(f"  {kind}: {before} -> {after}")
        if added:
            print(f"    merged ids: {', '.join(added)}")

    print("ALL PASS: per-record ingress files are represented in the aggregate arrays")
    return 0


if __name__ == "__main__":
    sys.exit(main())