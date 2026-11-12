#!/usr/bin/env python3
"""Fetch report 7743 (markdown) from the platform API and pin its sha256.

Usage: python3 scripts/kf_fetch_7743.py
Outputs (not committed): runs/wp-7743-01/report_7743.json, runs/wp-7743-01/report_7743.md
Credentials come from env (TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE);
nothing secret is written into the worktree.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "7743"
OUT = pathlib.Path("runs/wp-7743-01")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())


def login():
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        raise SystemExit("TENSOR_AGENT_USER/TENSOR_AGENT_PASS not set")
    d = _req(BASE + "/auth/login", {"username": user, "password": pwd})
    tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
    if not tok:
        raise SystemExit("login returned no token; keys=%s" % list(d))
    return tok


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    payload = _req(BASE + "/tensor/reports/" + REPORT_ID, token=tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    (OUT / ("report_%s.json" % REPORT_ID)).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2))
    md = payload.get("markdown") or ""
    if not md:
        print("ERROR: empty markdown; keys=%s" % list(payload))
        return 1
    (OUT / ("report_%s.md" % REPORT_ID)).write_text(md)
    h = hashlib.sha256(md.encode()).hexdigest()
    print("report_id:", payload.get("id"))
    print("title:", payload.get("title"))
    print("scenario_key:", payload.get("scenario_key"))
    print("chars:", len(md), "bytes_utf8:", len(md.encode()))
    print("sha256:", h)
    print("contract:", "sha256:2db8e0192df29ddfed091f81cdf35c5f128166ab8966c45298f354dd9a15e21a")
    print("MATCH:", h == "2db8e0192df29ddfed091f81cdf35c5f128166ab8966c45298f354dd9a15e21a")
    return 0


if __name__ == "__main__":
    sys.exit(main())