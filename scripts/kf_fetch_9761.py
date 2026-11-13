#!/usr/bin/env python3
"""Fetch report 9761 from the platform API and store the raw payload + markdown.

Usage: python3 scripts/kf_fetch_9761.py
Env: TENSOR_API_BASE, TENSOR_AGENT_USER, TENSOR_AGENT_PASS
Writes: runs/wp-9761-01/report_9761.json  (raw API payload)
        runs/wp-9761-01/report_9761.md    (markdown field, byte-exact)
"""
from __future__ import annotations

import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

RUN_DIR = pathlib.Path("runs/wp-9761-01")


def post(path: str, body: dict, token: str | None = None) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def get(path: str, token: str) -> dict:
    req = urllib.request.Request(BASE + path, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    auth = post("/auth/login", {"username": USER, "password": PASS})
    token = auth.get("access_token") or auth.get("token")
    if not token:
        raise SystemExit("login failed: no token in response keys %s" % sorted(auth))
    payload = get("/tensor/reports/9761", token)
    if isinstance(payload, dict) and "id" not in payload and "report" in payload:
        payload = payload["report"]
    md = payload["markdown"]
    (RUN_DIR / "report_9761.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / "report_9761.md").write_text(md, encoding="utf-8")
    import hashlib
    print("id:", payload.get("id"))
    print("title:", payload.get("title"))
    print("scenario_key:", payload.get("scenario_key"))
    print("chars:", len(md), "bytes_utf8:", len(md.encode()))
    print("sha256:", hashlib.sha256(md.encode()).hexdigest())
    print("figures:", len(payload.get("figures") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())