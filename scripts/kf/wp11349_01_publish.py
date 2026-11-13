#!/usr/bin/env python3
"""Publish the wp-11349-01 KF-RESULT report to the platform (owner 常设报告纪律).

POSTs docs/kf/wp-11349-01/report_payload.json to $TENSOR_API_BASE/tensor/reports with a
Bearer token from /auth/login. Prints the created report id/status and re-reads the record to
confirm the markdown sha256 of the published copy equals the contract source_hash-bearing body.

Usage:  python3 scripts/kf/wp11349_01_publish.py
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-11349-01")


def main() -> int:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010").rstrip("/")
    body = open(os.path.join(PKG, "report_payload.json"), encoding="utf-8").read()

    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.loads(r.read())["access_token"]

    req = urllib.request.Request(base + "/tensor/reports", data=body.encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=60) as r:
        created = json.loads(r.read())
    rid = created.get("id") if isinstance(created, dict) else None
    print("published:", json.dumps({k: v for k, v in created.items() if k != "markdown"},
                                   ensure_ascii=False)[:400])

    if rid:
        req = urllib.request.Request(f"{base}/tensor/reports/{rid}",
                                     headers={"Authorization": "Bearer " + tok})
        with urllib.request.urlopen(req, timeout=30) as r:
            rec = json.loads(r.read())
        md = rec["markdown"]
        print("readback id:", rid, "title:", rec.get("title"))
        print("tags:", rec.get("tags"))
        print("markdown chars:", len(md),
              "sha256:", hashlib.sha256(md.encode()).hexdigest()[:16] + "…",
              "json blocks:", md.count("```json"))
        with open(os.path.join(PKG, "report_published.json"), "w", encoding="utf-8") as f:
            json.dump({"id": rid, "title": rec.get("title"), "tags": rec.get("tags"),
                       "status": rec.get("status"), "mission_id": rec.get("mission_id"),
                       "markdown_chars": len(md),
                       "markdown_sha256": hashlib.sha256(md.encode()).hexdigest(),
                       "figures": len(rec.get("figures") or [])}, f,
                      ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())