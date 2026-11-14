#!/usr/bin/env python3
"""wp-11608-04: fetch report 11608 verbatim and verify the contract hash.

Only report_id=11608 is requested (work-package boundary).  Writes a byte-exact copy
next to this script and refuses to continue if the hash does not match the contract.

Usage:
  TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... TENSOR_API_BASE=... \
    python3 runs/wp-11608-04/fetch_source.py [--out runs/wp-11608-04/source_report_11608.md]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from pathlib import Path

REPORT_ID = "11608"
SOURCE_HASH = "sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent / "source_report_11608.md"),
    )
    ap.add_argument("--api-base", default=os.environ.get("TENSOR_API_BASE", ""))
    args = ap.parse_args()
    base = args.api_base.rstrip("/")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    user = os.environ.get("TENSOR_AGENT_USER")
    pw = os.environ.get("TENSOR_AGENT_PASS")
    if not (user and pw):
        raise SystemExit("TENSOR_AGENT_USER / TENSOR_AGENT_PASS not set")
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": pw}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req, timeout=30))["access_token"]
    req = urllib.request.Request(
        f"{base}/tensor/reports/{REPORT_ID}", headers={"Authorization": "Bearer " + tok}
    )
    payload = json.load(urllib.request.urlopen(req, timeout=30))
    md = payload["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    out = Path(args.out)
    out.write_bytes(raw)
    print(f"report_id={REPORT_ID} chars={len(md)} bytes={len(raw)} sha256={digest}")
    if digest != SOURCE_HASH:
        raise SystemExit(f"hash mismatch: {digest} != {SOURCE_HASH}")
    print("hash matches contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())