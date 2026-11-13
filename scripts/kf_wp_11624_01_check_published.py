#!/usr/bin/env python3
"""Check the *published* copy of KF-RESULT wp-11624-01 against the local artifacts.

The platform (and an independent auditor) re-reads the report from the API, so the
result block must survive the round trip unchanged. This script re-fetches the
published report by id and asserts:

  * exactly one ```json fenced block in the body;
  * that block is byte-equal (as JSON) to knowledge/kf/wp-11624-01/kf_result.json;
  * provenance.source_hash == sha256(UTF-8 bytes of the local source snapshot)
    == the contract source_hash;
  * every markdown-side quote in the block is a verbatim, unique substring of the
    source report markdown (second confirmation, independent of the local manifest);
  * tags carry `kf-wp:wp-11624-01`, mission_id is 15728, title is `KF-RESULT wp-11624-01`.

Uses the platform API only (psql is denied). Exit 0 iff every check passes.
Usage: python3 scripts/kf_wp_11624_01_check_published.py [--id 14836]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

PKG = "wp-11624-01"
REPORT_ID = "11624"
MISSION_ID = 15728
CONTRACT_SOURCE_HASH = (
    "sha256:a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33"
)
DEFAULT_PUBLISHED_ID = 14836

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "knowledge" / "kf" / PKG
DOC = ROOT / "docs" / PKG
SNAPSHOT = OUT / "source_report_11624.md"
RESULT = OUT / "kf_result.json"


def _token() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req))
    return d.get("access_token") or d.get("token")


def get_report(rid: int) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + "/tensor/reports/%d" % rid,
                                 headers={"Authorization": "Bearer " + _token()})
    d = json.loads(urllib.request.urlopen(req).read())
    return d.get("data", d)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, default=DEFAULT_PUBLISHED_ID)
    args = ap.parse_args(argv)

    src = SNAPSHOT.read_text(encoding="utf-8")
    local = json.loads(RESULT.read_text(encoding="utf-8"))
    pub = get_report(args.id)
    md = pub["markdown"]
    checks = {}

    checks["single_json_fence"] = md.count("```json") == 1
    block = json.loads(md.split("```json", 1)[1].split("```", 1)[0]) \
        if checks["single_json_fence"] else {}
    checks["block_equals_local_result"] = block == local
    snap_hash = "sha256:" + hashlib.sha256(src.encode("utf-8")).hexdigest()
    checks["provenance_hash_matches_snapshot"] = (
        block.get("provenance", {}).get("source_hash") == snap_hash)
    checks["snapshot_hash_matches_contract"] = snap_hash == CONTRACT_SOURCE_HASH
    quotes = [a["locator"]["quote"] for a in
              block.get("outputs", {}).get("asset_manifest.json", {}).get("assets", [])
              if a["locator"]["source_field"] == "markdown"]
    checks["quotes_verbatim_and_unique"] = bool(quotes) and all(
        q in src and src.count(q) == 1 for q in quotes)
    checks["tags_carry_kf_wp"] = ("kf-wp:%s" % PKG) in (pub.get("tags") or [])
    checks["mission_and_title"] = (pub.get("mission_id") == MISSION_ID
                                   and pub.get("title") == "KF-RESULT %s" % PKG)
    checks["report_id_untouched"] = str(block.get("report_id")) == REPORT_ID

    out = {"package_id": PKG, "published_report_id": args.id,
           "published_title": pub.get("title"), "published_tags": pub.get("tags"),
           "source_hash": snap_hash, "markdown_quotes_checked": len(quotes),
           "checks": checks, "all_pass": all(checks.values())}
    blob = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    (OUT / "published_check.json").write_text(blob, encoding="utf-8")
    (DOC / "published_check.json").write_text(blob, encoding="utf-8")

    for k, v in checks.items():
        print("%-40s %s" % (k, "PASS" if v else "FAIL"))
    print("ALL:", "PASS" if out["all_pass"] else "FAIL")
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())