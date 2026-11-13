#!/usr/bin/env python3
"""Fetch a tensor report markdown by id via platform API (no secrets on cmdline).

Usage: python3 scripts/kf_fetch_report.py <report_id> <out_path>
Env: TENSOR_API_BASE, TENSOR_AGENT_USER, TENSOR_AGENT_PASS
"""
import hashlib
import json
import os
import sys
import urllib.request


def _post_json(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get_json(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    report_id = sys.argv[1]
    out = sys.argv[2]
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user = os.environ["TENSOR_AGENT_USER"]
    pw = os.environ["TENSOR_AGENT_PASS"]
    tok = _post_json(base + "/auth/login",
                     {"username": user, "password": pw})
    token = tok.get("access_token") or tok.get("token")
    if not token:
        print("LOGIN_RESP_KEYS", list(tok), file=sys.stderr)
        sys.exit(2)
    rec = _get_json(base + "/tensor/reports/" + report_id, token)
    md = rec.get("markdown", "")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    raw = md.encode("utf-8")
    print(json.dumps({
        "report_id": report_id,
        "chars": len(md),
        "bytes": len(raw),
        "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "title": rec.get("title"),
        "keys": sorted(rec.keys()),
        "out": out,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()