#!/usr/bin/env python3
"""Check whether the published report can be updated in place (avoids a duplicate package report).

  python3 scripts/kf/check_report_update.py 14684
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def login():
    data = json.dumps({"username": USER, "password": PASS}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())["access_token"]


def main(rid: str) -> None:
    tok = login()
    # OPTIONS / OpenAPI discovery first: never guess at endpoints blindly
    for path in ("/openapi.json",):
        try:
            req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + tok})
            with urllib.request.urlopen(req, timeout=30) as r:
                spec = json.loads(r.read().decode())
            paths = {p: sorted(m.upper() for m in v) for p, v in (spec.get("paths") or {}).items()
                     if "reports" in p}
            print(json.dumps(paths, ensure_ascii=False, indent=1))
        except Exception as e:  # noqa: BLE001
            print("openapi probe failed:", type(e).__name__, e)
    # method probe
    for method in ("PATCH", "PUT", "DELETE"):
        req = urllib.request.Request(BASE + "/tensor/reports/%s" % rid, method=method,
                                     data=b"{}" if method != "DELETE" else None)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Bearer " + tok)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                print(method, r.status, r.read().decode()[:200])
        except urllib.error.HTTPError as e:
            print(method, "http_%s" % e.code, e.read().decode()[:120])
        except Exception as e:  # noqa: BLE001
            print(method, type(e).__name__, e)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "14684")