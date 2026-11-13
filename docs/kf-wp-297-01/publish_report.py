#!/usr/bin/env python3
"""Publish the wp-297-01 report (single json block = kf_result) to the platform."""
import json
import os
import urllib.request

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")


def post(path: str, payload: dict, token: str | None = None) -> dict:
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


auth = post("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]})
token = auth.get("access_token") or auth.get("token") or (auth.get("data") or {}).get("access_token")
if not token:
    raise SystemExit(f"no token, keys={sorted(auth)}")
payload = json.loads(open("/tmp/report_wp29701.json", encoding="utf-8").read())
res = post("/tensor/reports", payload, token)
print(json.dumps({k: res.get(k) for k in ("id", "title", "scenario_key", "tags", "mission_id")}, ensure_ascii=False))