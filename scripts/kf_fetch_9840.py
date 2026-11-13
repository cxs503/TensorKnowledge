#!/usr/bin/env python3
"""Fetch report 9840 (markdown + metadata) from the platform API and freeze a local copy.

Used by wp-9840-01 (01-asset-registration). No invention: everything comes from the API.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")
REPORT_ID = "9840"
RUN_DIR = pathlib.Path("runs/wp-9840-01")
EXPECTED_HASH = "159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524"


def call(path, data=None, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, body, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    tok = call("/auth/login", {"username": USER, "password": PASS}).get("access_token")
    if not tok:
        print("FATAL: no access_token")
        return 2
    payload = call("/tensor/reports/" + REPORT_ID, token=tok)
    md = payload["markdown"]
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / ("report_%s.json" % REPORT_ID)).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / ("report_%s.md" % REPORT_ID)).write_text(md)
    h = hashlib.sha256(md.encode()).hexdigest()
    print("title:", payload.get("title"))
    print("scenario_key:", payload.get("scenario_key"))
    print("tags:", payload.get("tags"))
    print("figures:", len(payload.get("figures") or []))
    print("chars:", len(md), "bytes:", len(md.encode()))
    print("sha256:", h, "MATCH" if h == EXPECTED_HASH else "MISMATCH")
    return 0


if __name__ == "__main__":
    sys.exit(main())