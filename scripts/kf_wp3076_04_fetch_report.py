#!/usr/bin/env python3
"""Fetch report 3076 markdown from the Tensor platform API and verify its hash.

Usage: python3 scripts/kf_wp3076_04_fetch_report.py [--out DIR]
Credentials: env TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS.
Writes <out>/source.md, <out>/source.record.json  (record = full API payload for
report 3076 only; no other report_id is read or written).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

EXPECTED_SHA = "9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1"


def _post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/wp-3076-04")
    args = ap.parse_args()

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user = os.environ["TENSOR_AGENT_USER"]
    pwd = os.environ["TENSOR_AGENT_PASS"]

    tok = _post_json(f"{base}/auth/login", {"username": user, "password": pwd})
    token = tok.get("access_token") or tok.get("token")
    if not token:
        print(f"login failed: keys={list(tok)}", file=sys.stderr)
        return 2

    payload = _get_json(f"{base}/tensor/reports/3076", token)
    rec = payload.get("data", payload)
    md = rec["markdown"]

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "source.md").write_text(md, encoding="utf-8")
    (out / "source.record.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    print(f"title      : {rec.get('title')}")
    print(f"chars      : {len(md)}")
    print(f"sha256     : {digest}")
    print(f"expected   : {EXPECTED_SHA}")
    print(f"hash_match : {digest == EXPECTED_SHA}")
    print(f"tags       : {rec.get('tags')}")
    print(f"record keys: {sorted(rec)}")
    return 0 if digest == EXPECTED_SHA else 3


if __name__ == "__main__":
    raise SystemExit(main())