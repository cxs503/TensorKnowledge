#!/usr/bin/env python3
"""Fetch report 5347 markdown from the platform API (no hardcoded secrets).

Usage: python3 scripts/fetch_report_5347.py --out artifacts/wp-5347-01/report_5347.md
Env: TENSOR_API_BASE, TENSOR_AGENT_USER, TENSOR_AGENT_PASS
"""
import argparse
import hashlib
import json
import os
import urllib.request


def _post(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get(url, token=None):
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get_token(base):
    body = {
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    }
    j = _post(base + "/auth/login", body)
    return j.get("access_token") or j.get("token")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", default="5347")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = get_token(base)
    rep = _get(base + "/tensor/reports/" + args.report_id, tok)
    if "data" in rep and isinstance(rep["data"], dict):
        rep = rep["data"]
    md = rep["markdown"]
    raw = md.encode("utf-8")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(raw)
    print("report_id:", rep.get("id"))
    print("title:", rep.get("title"))
    print("chars:", len(md))
    print("sha256:", hashlib.sha256(raw).hexdigest())
    # keep only non-markdown metadata for provenance
    meta = {k: v for k, v in rep.items() if k != "markdown"}
    with open(args.out + ".meta.json", "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False, default=str)
    print("meta_keys:", sorted(meta.keys()))


if __name__ == "__main__":
    main()