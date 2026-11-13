#!/usr/bin/env python3
"""Publish the wp-7545-04 delivery report to the Tensor platform.

Payload: /tmp/report_7545_04.json (built by scripts/kf_build_wp7545_04.py).
Prints the created report id; the new report is a *different* report_id from 7545
(the reviewed one is never written to).
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010").rstrip("/")
PAYLOAD = sys.argv[1] if len(sys.argv) > 1 else "/tmp/report_7545_04.json"


def post(path, body, token=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


tok = None
for body in ({"username": os.environ.get("TENSOR_AGENT_USER", ""),
              "password": os.environ.get("TENSOR_AGENT_PASS", "")},
             {"grant_type": "password", "username": os.environ.get("TENSOR_AGENT_USER", ""),
              "password": os.environ.get("TENSOR_AGENT_PASS", "")}):
    try:
        d = post("/auth/login", body)
        tok = d.get("access_token") or d.get("token")
        if tok:
            break
    except Exception as e:  # noqa: BLE001
        print("login:", e, file=sys.stderr)
if not tok:
    print("LOGIN_FAILED", file=sys.stderr)
    sys.exit(2)

payload = json.load(open(PAYLOAD, encoding="utf-8"))
md = payload["markdown"]
assert md.count("```json") == 1, "delivery markdown must carry exactly one json block"
out = post("/tensor/reports", payload, tok)
print(json.dumps({"id": out.get("id"), "title": out.get("title"),
                  "tags": out.get("tags"), "figures": [f.get("name") for f in (out.get("figures") or [])],
                  "chars": len(md)}, ensure_ascii=False))