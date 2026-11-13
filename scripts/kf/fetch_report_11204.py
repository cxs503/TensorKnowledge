#!/usr/bin/env python3
"""Fetch report 11204 markdown+record from the platform and store the exact bytes.

Writes:
  work/wp-11204-01/source_markdown.md   (exact markdown bytes, UTF-8)
  work/wp-11204-01/record.json          (full platform record JSON)
  work/wp-11204-01/source_meta.json     (sha256 / chars / bytes / title ...)

Hash gate: the SHA-256 of the UTF-8 encoded markdown must equal the contract
declared hash (d22a30cc...); otherwise exit non-zero and write nothing else.
"""
import hashlib
import json
import os
import sys
import urllib.request

CONTRACT_HASH = "d22a30cc692b82f2acf6ea669fd898a330143436344e4091c4a39c06a5292f86"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   "work", "wp-11204-01")


def post_json(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get_json(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    token = None
    for path in ("/auth/login", "/tensor/auth/login"):
        try:
            d = post_json(API + path, {"username": USER, "password": PASS})
        except Exception as e:  # noqa: BLE001
            print("login via %s failed: %s" % (path, e))
            continue
        token = d.get("access_token") or d.get("token")
        if token:
            print("login ok via", path)
            break
    if not token:
        print("FATAL: no token")
        return 2

    rec = get_json(API + "/tensor/reports/11204", token)
    md = rec.get("markdown")
    if not isinstance(md, str):
        print("FATAL: no markdown field")
        return 3
    raw = md.encode("utf-8")
    h = hashlib.sha256(raw).hexdigest()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "source_markdown.md"), "wb") as f:
        f.write(raw)
    with open(os.path.join(OUT, "record.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    meta = {
        "report_id": "11204",
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "mission_id": rec.get("mission_id"),
        "status": rec.get("status"),
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": h,
        "contract_sha256": CONTRACT_HASH,
        "hash_matches_contract": h == CONTRACT_HASH,
        "record_keys": sorted(rec.keys()),
        "figures": rec.get("figures"),
        "tags": rec.get("tags"),
    }
    with open(os.path.join(OUT, "source_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1))
    if h != CONTRACT_HASH:
        print("FATAL: hash mismatch")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())