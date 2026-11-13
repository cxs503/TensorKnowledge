#!/usr/bin/env python3
"""Publish the m15908 board-audit report to the tensor platform."""
import json
import os
import urllib.request

BASE = os.environ["TENSOR_API_BASE"]
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def api(method, path, payload=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(req, data=data, timeout=60) as r:
        return r.status, json.loads(r.read() or b"{}")


c, d = api("POST", "/auth/login", {"username": USER, "password": PASS})
tok = d.get("access_token")
print("login:", c, "token_len:", len(tok or ""))

rep = json.load(open("/tmp/report.json"))
c2, d2 = api("POST", "/tensor/reports", rep, tok)
print("publish:", c2)
print(json.dumps(d2, ensure_ascii=False)[:600])
