#!/usr/bin/env python3
"""Round-trip check of the delivery channel for wp-9761-01.

The result channel is the markdown of a platform report. This script re-reads that report
from the API and asserts, on the *published* bytes (not the local draft):

  1. title == 'KF-RESULT wp-9761-01'
  2. tags contain 'kf-wp:wp-9761-01'
  3. mission_id and scenario_key as declared
  4. exactly one ```json block, and it parses
  5. the parsed block equals runs/wp-9761-01/kf_result.wp-9761-01.json
  6. provenance.source_hash of the block still matches the source markdown byte hash
  7. figures of the published report == the two local figures (by name)

Writes runs/wp-9761-01/published_check.json and exits non-zero on any failure.
Usage: python3 scripts/kf_check_published_9761.py [report_id]
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PACKAGE_ID = "wp-9761-01"
SOURCE_HASH = "4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a"
CAMPAIGN_MISSION_ID = 15667
RUN = pathlib.Path("runs/wp-9761-01")


def login() -> str:
    u, p = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(BASE + "/auth/login",
                                 data=json.dumps({"username": u, "password": p}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    return d.get("access_token") or d.get("token") or (d.get("data") or {})["access_token"]


def get(path: str, token: str) -> dict:
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode())
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    return d


def main() -> int:
    rid = sys.argv[1] if len(sys.argv) > 1 else json.loads(
        (RUN / "publish.json").read_text())["id"]
    tok = login()
    rep = get("/tensor/reports/%s" % rid, tok)
    md = rep["markdown"]
    expected = json.loads((RUN / "kf_result.wp-9761-01.json").read_text())

    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    checks = []

    def rec(name, ok, detail):
        checks.append(dict(check=name, result="pass" if ok else "fail", detail=detail))

    rec("title", rep.get("title") == "KF-RESULT %s" % PACKAGE_ID, {"title": rep.get("title")})
    tags = rep.get("tags") or []
    rec("tag_kf_wp", ("kf-wp:%s" % PACKAGE_ID) in tags, {"tags": tags})
    rec("mission_id", rep.get("mission_id") == CAMPAIGN_MISSION_ID,
        {"mission_id": rep.get("mission_id")})
    rec("scenario_key", rep.get("scenario_key") == "rigid_contact_energy_ledger_certification",
        {"scenario_key": rep.get("scenario_key")})
    rec("single_json_block", len(blocks) == 1, {"json_blocks": len(blocks)})

    block = None
    try:
        block = json.loads(blocks[0]) if len(blocks) == 1 else None
        ok = block == expected
    except Exception as exc:
        ok = False
        block = {"parse_error": str(exc)}
    rec("json_block_equals_result", ok,
        {"package_id": (block or {}).get("package_id"),
         "report_id": (block or {}).get("report_id"),
         "provenance_source_hash": ((block or {}).get("provenance") or {}).get("source_hash")})
    rec("provenance_hash_is_source_bytes",
        ((block or {}).get("provenance") or {}).get("source_hash") == "sha256:" + SOURCE_HASH,
        {"source_bytes_sha256": SOURCE_HASH})

    figs = rep.get("figures") or []
    local = sorted(p.name for p in (pathlib.Path("docs") / PACKAGE_ID / "figures").glob("*.png"))
    rec("figures_match", sorted(f.get("name") for f in figs) == local,
        {"published": [f.get("name") for f in figs], "local": local})

    overall = "PASS" if all(c["result"] == "pass" for c in checks) else "FAIL"
    out = dict(package_id=PACKAGE_ID, published_report_id=rid, markdown_chars=len(md),
               markdown_sha256=hashlib.sha256(md.encode()).hexdigest(),
               checks=checks, overall=overall)
    (RUN / "published_check.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in checks:
        print("%-5s %s" % (c["result"].upper(), c["check"]))
    print("overall:", overall, "| published report:", rid)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())