"""Fetch report 5690 from the platform API (work package wp-5690-01, step 1: evidence capture).

Writes:
  runs/wp-5690-01/report_5690.md    (markdown payload)
  runs/wp-5690-01/report_5690.json  (raw API payload)

Usage: python3 scripts/kf_fetch_5690.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "5690"
EXPECTED_HASH = "a1e3f5faa1f969bcdfb759f7357adb8cc7474194e44a2c02ae4370f1db1b29a1"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
RUN_DIR = pathlib.Path("runs/wp-5690-01")


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        req = urllib.request.Request(BASE + path,
                                     data=json.dumps({"username": u, "password": p}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main() -> int:
    tok = login()
    req = urllib.request.Request(BASE + "/tensor/reports/%s" % REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok} if tok else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    if "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    md = d.get("markdown", "")
    h = hashlib.sha256(md.encode()).hexdigest()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "report_5690.md").write_text(md)
    (RUN_DIR / "report_5690.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    print("chars:", len(md), "bytes_utf8:", len(md.encode()), "sha256:", h,
          "MATCH" if h == EXPECTED_HASH else "MISMATCH")
    return 0 if h == EXPECTED_HASH else 2


if __name__ == "__main__":
    sys.exit(main())
