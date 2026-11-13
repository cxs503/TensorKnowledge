#!/usr/bin/env python3
"""Fetch report markdown for report_id=7216 from the platform API (no hardcoded secrets).

Usage:
    python3 scripts/kf_fetch_7216.py --out /tmp/r7216.md
"""
import argparse
import hashlib
import json
import os
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def post_json(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get_json(url, token):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", default="7216")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    tok = post_json(BASE + "/auth/login", {"username": USER, "password": PASS})
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise SystemExit("login failed: keys=%s" % list(tok)[:10])
    rec = get_json(BASE + "/tensor/reports/" + args.report_id, token)
    if isinstance(rec, dict) and "data" in rec and isinstance(rec["data"], dict):
        rec = rec["data"]
    md = rec["markdown"]
    raw = md.encode("utf-8")
    with open(args.out, "wb") as f:
        f.write(raw)
    print(json.dumps({
        "report_id": args.report_id,
        "title": rec.get("title"),
        "chars": len(md),
        "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "out": args.out,
        "keys": sorted(rec.keys()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()