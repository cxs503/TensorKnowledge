#!/usr/bin/env python3
"""Extract the single ```json result block from a KF report, without prose.

The independent reviewer is only allowed the structured upstream knowledge
objects, never the producer's narrative explanation. This script fetches the
report record, keeps the raw markdown for provenance, and prints / stores ONLY
the parsed JSON block (plus its sha256) so downstream review input is
reproducibly scoped to machine-readable output.

Usage:
    python3 scripts/kf_extract_result_block.py --report-id 14673 \
        --out work/wp-6506-04/upstream_wp-6506-01.result.json
"""
import argparse
import hashlib
import json
import os
import re
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


def _req(path, data=None, token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, headers=h,
                               method="POST" if body else "GET")
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tok = _req("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                               "password": os.environ["TENSOR_AGENT_PASS"]})
    tok = tok.get("access_token") or tok.get("token") or tok.get("data", {}).get("access_token")
    rec = _req("/tensor/reports/" + a.report_id, token=tok)
    md = rec.get("markdown") or (rec.get("data") or {}).get("markdown") or ""
    blocks = re.findall(r"```json\s*\n(.*?)\n```", md, re.S)
    out = {"report_id": a.report_id, "markdown_sha256": hashlib.sha256(md.encode()).hexdigest(),
           "n_json_blocks": len(blocks),
           "blocks_sha256": [hashlib.sha256(b.encode()).hexdigest() for b in blocks],
           "blocks": [json.loads(b) for b in blocks]}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("blocks=%d sha=%s -> %s" % (len(blocks), out["markdown_sha256"][:16], a.out))


if __name__ == "__main__":
    main()