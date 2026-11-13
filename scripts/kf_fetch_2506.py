#!/usr/bin/env python3
"""Fetch report 2506 markdown from the Tensor platform and verify its sha256.

Zero-hand-copy helper for work package wp-2506-04: every quote used in the
review must be locatable verbatim in the fetched markdown.
"""
import hashlib
import json
import os
import urllib.request

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def _post(path, payload, token=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _get(path, token):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def login():
    d = _post("/auth/login", {"username": USER, "password": PASS})
    tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
    if not tok:
        raise SystemExit("login failed: keys=%s" % list(d))
    return tok


if __name__ == "__main__":
    tok = login()
    rep = _get("/tensor/reports/2506", tok)
    if "markdown" not in rep and "data" in rep:
        rep = rep["data"]
    md = rep["markdown"]
    out = {"markdown": md, "meta": {k: v for k, v in rep.items() if k != "markdown"}}
    with open("/tmp/r2506.json", "w") as f:
        json.dump(out, f, ensure_ascii=False)
    with open("/tmp/r2506.md", "w") as f:
        f.write(md)
    print("keys:", sorted(rep.keys()))
    print("chars:", len(md))
    print("sha256:", "sha256:" + hashlib.sha256(md.encode()).hexdigest())