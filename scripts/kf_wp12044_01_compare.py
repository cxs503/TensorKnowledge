#!/usr/bin/env python3
"""Compare the local report body with the stored markdown of the published report.

Also probes whether the platform supports updating a report in place (PUT), so a body
regenerated after publication can be synced instead of leaving a stale copy. This never
touches report 12044 (the upstream source); it only reads it.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-12044-01"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def call(path, body=None, tok=None, method=None, timeout=120):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers,
                                 method=method or ("POST" if body is not None else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main() -> int:
    rc = json.loads((PKG / "publish_receipt.json").read_text(encoding="utf-8"))
    rid = rc["created_report_id"]
    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    tok = json.loads(body)["access_token"]
    st, back = call("/tensor/reports/%s" % rid, None, tok)
    rec = json.loads(back)
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    stored = rec.get("markdown") or ""
    local = (PKG / "report_body.md").read_text(encoding="utf-8")
    same = stored == local
    print("published report id:", rid)
    print("stored chars:", len(stored), "local chars:", len(local), "identical:", same)
    if not same:
        import difflib

        diff = list(difflib.unified_diff(stored.splitlines(), local.splitlines(),
                                         "published", "local", lineterm="", n=1))
        print("\n".join(diff[:40]))
    st2, upd = call("/tensor/reports/%s" % rid, {"markdown": local}, tok, method="PUT")
    print("PUT support probe:", st2, upd[:200])
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())