#!/usr/bin/env python3
"""Fetch a tensor report's markdown + metadata from the platform API.

Usage: python3 scripts/kf/fetch_report.py <report_id> <out_json>

Writes a JSON blob {id, title, scenario_key, tags, figures, markdown, chars,
bytes_utf8, sha256, fetched_via} so downstream steps hash the *exact* bytes
that the platform gate will independently re-hash (markdown encoded utf-8).
"""
import hashlib
import json
import os
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def post_json(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get_json(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    for path in ("/tensor/auth/login", "/auth/login"):
        try:
            d = post_json(BASE + path, {"username": USER, "password": PASS})
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("login %s failed: %s\n" % (path, e))
            continue
        tok = d.get("access_token") or d.get("token")
        if tok:
            return tok
    raise SystemExit("login failed")


def main():
    rid = sys.argv[1]
    out = sys.argv[2]
    tok = login()
    d = get_json("%s/tensor/reports/%s" % (BASE, rid), tok)
    md = d.get("markdown") or ""
    raw = md.encode("utf-8")
    blob = {
        "id": str(d.get("id", rid)),
        "title": d.get("title"),
        "scenario_key": d.get("scenario_key"),
        "mission_id": d.get("mission_id"),
        "tags": d.get("tags") or [],
        "figures": d.get("figures") or [],
        "markdown": md,
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "fetched_via": "GET /api/v1/tensor/reports/%s" % rid,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(blob, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: blob[k] for k in ("id", "title", "scenario_key", "chars", "bytes_utf8", "sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()