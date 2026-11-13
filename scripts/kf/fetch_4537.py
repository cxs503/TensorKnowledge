#!/usr/bin/env python3
"""Fetch report 4537 markdown from the platform and save to runs cache.

Usage:
    python3 scripts/kf/fetch_4537.py              # live fetch
    python3 scripts/kf/fetch_4537.py --out <dir>  # custom output dir

Outputs:
    <out>/source_report_4537.md   byte-exact markdown
    <out>/report_record_4537.json  platform record metadata
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

REPORT_ID = "4537"


def fetch_report() -> tuple:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user = os.environ["TENSOR_AGENT_USER"]
    password = os.environ["TENSOR_AGENT_PASS"]

    def call(path, payload=None, token=None):
        req = urllib.request.Request(
            base + path,
            data=json.dumps(payload).encode() if payload else None,
            method="POST" if payload else "GET",
        )
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    token = call("/auth/login", {"username": user, "password": password})["access_token"]
    report = call(f"/tensor/reports/{REPORT_ID}", token=token)
    return report["markdown"], report


def main():
    parser = argparse.ArgumentParser(description="Fetch report 4537")
    parser.add_argument("--out", default="runs/m15537_wp4537_01", help="output directory")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    md, record = fetch_report()
    md_path = out / "source_report_4537.md"
    md_path.write_text(md, encoding="utf-8")

    record_path = out / "report_record_4537.json"
    # Remove markdown from record to keep it small
    record_light = {k: v for k, v in record.items() if k != "markdown"}
    record_path.write_text(json.dumps(record_light, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    sha = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    print(f"Fetched report {REPORT_ID}")
    print(f"  markdown: {len(md)} chars, {len(md.encode('utf-8'))} bytes")
    print(f"  sha256: {sha}")
    print(f"  saved to: {md_path}")
    print(f"  record saved to: {record_path}")


if __name__ == "__main__":
    main()
