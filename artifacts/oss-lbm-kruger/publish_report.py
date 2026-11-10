#!/usr/bin/env python3
"""Publish the m8676 report to the platform report API (no secrets on the command line)."""
import json
import os
import sys
import urllib.request

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def post(path: str, payload: dict, token: str | None = None) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    try:
        auth = post("/auth/login", {"username": USER, "password": PASS})
    except Exception as exc:
        print("login failed:", exc)
        return 2
    token = auth.get("access_token") or auth.get("token") or (auth.get("data") or {}).get("access_token")
    if not token:
        print("login response keys:", list(auth))
        return 2
    report = json.loads(open("/tmp/report.json", encoding="utf-8").read())
    try:
        res = post("/tensor/reports", report, token)
    except Exception as exc:
        print("report post failed:", exc)
        return 3
    print(json.dumps(res, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())