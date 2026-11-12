#!/usr/bin/env python3
"""Fetch report 5776 markdown from the platform API and pin its sha256.

Scope: report_id=5776 only. Credentials come from env (TENSOR_AGENT_USER/PASS,
TENSOR_API_BASE) — never hardcoded, never on a command line.

Usage: python3 scripts/kf/fetch_report_5776.py
Outputs: runs/wp-5776-01/report_5776.json (raw API payload), runs/wp-5776-01/report_5776.md
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

REPORT_ID = "5776"
OUT = pathlib.Path(__file__).resolve().parents[2] / "runs" / "wp-5776-01"
BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    try:
        d = _req(BASE + "/auth/login", data=json.dumps({"username": USER, "password": PASS}).encode())
    except urllib.error.HTTPError:
        body = urllib.parse.urlencode({"username": USER, "password": PASS}).encode()
        d = _req(BASE + "/auth/login", data=body, ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: keys=%s" % sorted(d))
    return tok


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    payload = _req(BASE + "/tensor/reports/%s" % REPORT_ID, tok)
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        payload = payload["data"]
    if not isinstance(payload, dict) or not isinstance(payload.get("markdown"), str):
        raise SystemExit("report %s: no markdown field (keys=%s)" % (REPORT_ID, sorted(payload or [])))
    (OUT / "report_5776.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = payload["markdown"]
    raw = md.encode("utf-8")
    (OUT / "report_5776.md").write_bytes(raw)
    print(json.dumps({
        "report_id": REPORT_ID,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "chars": len(md),
        "bytes_utf8": len(raw),
        "title": payload.get("title"),
        "scenario_key": payload.get("scenario_key"),
        "tags": payload.get("tags"),
        "figures": len(payload.get("figures") or []),
        "meta_keys": sorted(payload.keys()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()