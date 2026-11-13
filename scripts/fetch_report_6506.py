#!/usr/bin/env python3
"""Fetch report markdown for report_id=6506 from the platform API.

Read-only. Writes the raw markdown bytes to the given output path and prints
sha256 so the reviewer can compare with the work-package contract's
provenance.source_hash. Credentials come from the environment
(TENSOR_AGENT_USER / TENSOR_AGENT_PASS), never from the source tree.

Usage:
    python3 scripts/fetch_report_6506.py [--report-id 6506] [--out work/wp-6506-04/report.md]
"""
import argparse
import hashlib
import json
import os
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


def _req(path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, headers=headers,
                                 method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    d = _req("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                             "password": os.environ["TENSOR_AGENT_PASS"]})
    return d.get("access_token") or d.get("token") or d.get("data", {}).get("access_token")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", default="6506")
    ap.add_argument("--out", default="work/wp-6506-04/report_6506.md")
    a = ap.parse_args()

    tok = login()
    rec = _req("/tensor/reports/" + a.report_id, token=tok)
    md = rec.get("markdown") if isinstance(rec, dict) else None
    if md is None and isinstance(rec, dict) and isinstance(rec.get("data"), dict):
        md = rec["data"].get("markdown")
    if md is None:
        raise SystemExit("no markdown field: " + json.dumps(rec)[:400])

    raw = md.encode("utf-8")
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(raw)
    print("bytes=%d" % len(raw))
    print("chars=%d" % len(md))
    print("sha256=%s" % hashlib.sha256(raw).hexdigest())
    print("title=%r" % (rec.get("title") if isinstance(rec, dict) else None))
    print("scenario_key=%r" % (rec.get("scenario_key") if isinstance(rec, dict) else None))


if __name__ == "__main__":
    main()