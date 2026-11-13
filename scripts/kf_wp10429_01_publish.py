#!/usr/bin/env python3
"""Publish the KF-RESULT report of wp-10429-01 to the platform.

Pre-flight (aborts on any failure, so a broken manuscript never reaches the gate):
  1. the manuscript carries exactly ONE ```json block and it parses;
  2. that block equals runs/wp-10429-01/kf_result.wp-10429-01.json byte-for-byte
     (after json normalisation) — the committed envelope and the posted envelope
     cannot diverge;
  3. provenance.source_hash in the block equals the contract hash of report 10429.

Credentials come from the environment; nothing secret is written to the tree.
Usage: python3 scripts/kf_wp10429_01_publish.py [--dry-run]
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PACKAGE_ID = "wp-10429-01"
REPORT_ID = "10429"
MISSION_ID = 15682
CONTRACT_HASH = "sha256:6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d"
MD = "docs/kf_result_wp-10429-01.md"
ENVELOPE = "runs/wp-10429-01/kf_result.wp-10429-01.json"


def call(path, body, tok=None, timeout=180):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def preflight() -> dict:
    md = open(MD, encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    assert len(blocks) == 1, f"expected exactly one json block, found {len(blocks)}"
    posted = json.loads(blocks[0])
    committed = json.loads(open(ENVELOPE, encoding="utf-8").read())
    assert posted == committed, "posted block differs from the committed envelope"
    assert posted["provenance"]["source_hash"] == CONTRACT_HASH, "source_hash != contract hash"
    assert posted["package_id"] == PACKAGE_ID and posted["report_id"] == REPORT_ID
    return posted


def main() -> int:
    env = preflight()
    manifest = env["outputs"]["asset_manifest.json"]
    creds = {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    st, body = call("/auth/login", creds)
    assert st == 200, (st, body[:300])
    tok = json.loads(body)["access_token"]

    md = open(MD, encoding="utf-8").read()
    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (f"{PACKAGE_ID} (01-asset-registration, report {REPORT_ID}): markdown sha256 recomputed = "
                    f"contract hash; {manifest['counts']['assets']} assets registered "
                    f"({manifest['counts']['resolved_in_source']} resolved_in_source, "
                    f"{manifest['counts']['referenced_unresolved']} referenced_unresolved, "
                    f"{manifest['counts']['declared_absent']} declared_absent); every char_span quote re-resolved "
                    f"verbatim and unique; 6/6 contract acceptance items pass plus 1 extra envelope check; "
                    f"7 negative controls prove the gate goes red when evidence is broken; claims=[] by contract."),
        "scenario_key": "fsi_lbm_strong_coupling",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + REPORT_ID,
                 "lane:C", "draft", "knowledge-factory"],
        "markdown": md,
        "figures": [],  # asset registration produces no field quantities; reason stated in the body (§⑥)
    }
    if "--dry-run" in sys.argv:
        print("dry-run ok:", payload["title"], len(md), "chars")
        return 0
    st, resp = call("/tensor/reports", payload, tok)
    print(st, resp[:500])
    if st not in (200, 201):
        return 1
    try:
        rid = json.loads(resp).get("id")
    except Exception:
        rid = None
    print("published report id:", rid)
    return 0


if __name__ == "__main__":
    sys.exit(main())