#!/usr/bin/env python3
"""Fetch report 5716 markdown from the platform API (no hardcoded secrets).

Usage: python3 scripts/kf/fetch_report_5716.py --out docs/kf/wp-5716-04/source_5716.md
Env: TENSOR_API_BASE, TENSOR_AGENT_USER, TENSOR_AGENT_PASS
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request


def _call(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def get_token(base):
    j = _call(base + "/auth/login", {
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    })
    return j.get("access_token") or j.get("token")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", default="5716")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = get_token(base)
    rep = _call(base + "/tensor/reports/" + a.report_id, token=tok)
    if isinstance(rep, dict) and "data" in rep and isinstance(rep["data"], dict):
        rep = rep["data"]
    md = rep["markdown"]
    raw = md.encode("utf-8")
    d = os.path.dirname(a.out)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(raw)
    print("report_id:", rep.get("id"))
    print("title:", rep.get("title"))
    print("chars:", len(md))
    print("sha256:", "sha256:" + hashlib.sha256(raw).hexdigest())
    meta = {k: v for k, v in rep.items() if k != "markdown"}
    with open(a.out + ".meta.json", "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False, default=str)
    print("meta_keys:", sorted(meta.keys()))
    return 0


if __name__ == "__main__":
    sys.exit(main())