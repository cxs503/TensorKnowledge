#!/usr/bin/env python3
"""Fetch a tensor report markdown via platform API (creds from env, never on argv)."""
import json
import os
import sys
import urllib.request

BASE = os.environ["TENSOR_API_BASE"]
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def post(url, payload, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    d = post(BASE + "/auth/login", {"username": USER, "password": PASS})
    tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
    if not tok:
        raise SystemExit("no token in login response keys=%s" % list(d))
    return tok


if __name__ == "__main__":
    tok = login()
    rid = sys.argv[1] if len(sys.argv) > 1 else "5347"
    rep = get(BASE + "/tensor/reports/" + rid, tok)
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/r%s.json" % rid
    with open(out, "w") as f:
        json.dump(rep, f, ensure_ascii=False)
    md = rep.get("markdown", "")
    with open(out.replace(".json", ".md"), "w") as f:
        f.write(md)
    print(json.dumps({k: v for k, v in rep.items() if k != "markdown"}, ensure_ascii=False)[:1200])
    print("markdown bytes:", len(md.encode()))